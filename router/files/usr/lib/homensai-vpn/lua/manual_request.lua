-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- manual_request.lua: the owner's manual channel click (pair_manual.request, instant path) answered by the Lua
-- monitor without starting Python (plan item 4). Only the request is written here: the supervisor takes it,
-- diagnoses the pair and proves the kernel itself, exactly as with the Python request.
--
-- Same order and codes as pair_manual_reply/request/light_gate:
--   fields -> pair mode -> light gate from RAM (busy, stale supervisor, transaction, target health)
--   -> under the control lock: speed pause, control revision and the running pair -> QUEUED row.
-- Everything this module cannot decide without waiting goes back to agent.py (FALLBACK): 'resume', the fast
-- switch turned off, a held control lock, a speed-test pause file.
local canon=require('canon')

local M={}
M.FALLBACK=setmetatable({},{__tostring=function() return 'FALLBACK' end})
M.MODE='router-probed-ipv4'
local PENDING={QUEUED=true,CLAIMED=true}
local BUSY_NATIVE={ARMED=true,APPLYING=true,WAIT_CLIENT=true,['WAIT-CLIENT']=true,RESTORING=true}
local SOURCES={manual=true,test=true,programmatic=true}
local QUIET={['ROLLED-BACK']=true,COMMITTED=true,['HELD-ON-RESERVE']=true}

local function hex(v,n) return type(v)=='string' and #v==n and string.find(v,'^[a-f0-9]+$')~=nil end
local function num(v) return canon.number(v) end
local function refuse(code) return canon.object({accepted=false,queued=false,completed=false,blockers=canon.array({code})}) end
M.refuse=refuse

-- observation_freshness.valid_for
function M.valid_for(interval)
  local value=interval
  if type(value)=='string' and string.find(value,'^[0-9]+$') and #value<=3 then value=tonumber(value) end
  if type(value)~='number' or value%1~=0 or value<10 or value>300 then return 90 end
  return math.max(30,math.min(900,value*3))
end

-- pair_manual.healthy
function M.healthy(status,identifier,now,valid_for)
  local profiles=canon.is_object(status) and status.profiles or nil
  if type(profiles)~='table' then return false end
  for _,row in ipairs(profiles) do
    if canon.is_object(row) and row.id==identifier then
      local stamp=num(row.time)
      return stamp~=nil and stamp==stamp and now-stamp>=0 and now-stamp<=valid_for and (row.code==nil or row.code==canon.null)
        and row.dns_ok==true and (num(row.https_success) or 0)>=2
    end
  end
  return false
end

-- native_switch.fast_switch_enabled: on unless the config file says option fast_switch '0'
function M.fast_switch_enabled(config_text)
  if type(config_text)~='string' then return false end
  for line in string.gmatch(config_text,'[^\n]+') do
    if string.find(line,"^%s*option%s+fast_switch%s+'?0'?%s*$") then return false end
  end
  return true
end

local function uuid_hex(read)
  local text=read('/proc/sys/kernel/random/uuid')
  local id=text and string.gsub(text,'[^0-9a-f]','') or ''
  if not hex(id,32) then error('PAIR-MANUAL-REQUEST-UNCONFIRMED',0) end
  return id
end

-- deps: read(path)->text|nil, write(path,text), now()->float, try_lock(fn)->(locked, result),
--       runtime, persist, config_text()->text, uci_get(option)->value, status()->monitor status,
--       read_state()->pair state (checked envelope), current_revision()->revision|nil
function M.request(deps,arguments)
  if not canon.is_object(arguments) then return canon.object({accepted=false,blockers=canon.array({'PAIR-MANUAL-FIELDS'})}) end
  for key in pairs(arguments) do
    if key~='direction' and key~='control_revision' and key~='request_source' then
      return canon.object({accepted=false,blockers=canon.array({'PAIR-MANUAL-FIELDS'})})
    end
  end
  if arguments.direction==nil or arguments.control_revision==nil then
    return canon.object({accepted=false,blockers=canon.array({'PAIR-MANUAL-FIELDS'})})
  end
  local direction,revision=arguments.direction,arguments.control_revision
  if (direction~='primary' and direction~='reserve' and direction~='resume') or not hex(revision,32) then return refuse('PAIR-MANUAL-FIELDS') end
  if direction=='resume' then return M.FALLBACK end
  local ok,reply=pcall(function()
    if deps.uci_get('pair_auto_mode')~=M.MODE then return refuse('PAIR-MODE-NOT-CONFIGURED') end
    if not M.fast_switch_enabled(deps.config_text()) then return M.FALLBACK end
    local function read_json(path)
      local text=deps.read(path)
      if text==nil then return canon.object({}) end
      return canon.decode(text)
    end
    local runtime,persist=deps.runtime,deps.persist
    -- light_gate
    local now=deps.now()
    local native=read_json(runtime..'/native-status.json')
    local queued=read_json(runtime..'/pair-manual-control.json')
    if not canon.is_object(native) or not canon.is_object(queued) then return refuse('PAIR-MANUAL-STATE-UNVERIFIED') end
    if PENDING[queued.state] or BUSY_NATIVE[native.state] then return refuse('PAIR-MANUAL-BUSY') end
    local stamp=num(native.time)
    if not (stamp and now-stamp>=0 and now-stamp<=30) then return refuse('PAIR-MANUAL-STALE') end
    local envelope=read_json(persist..'/native-transaction.json')
    local journal=canon.is_object(envelope) and canon.is_object(envelope.data) and envelope.data or canon.object({})
    local phase=journal.phase
    if phase~=nil and phase~=canon.null and not QUIET[phase] then return refuse('TRANSACTION-IN-PROGRESS') end
    local target=direction=='primary' and native.source or native.target
    if not M.healthy(deps.status(),target,now,M.valid_for(deps.uci_get('interval'))) then
      return refuse(direction=='primary' and 'SOURCE-NOT-HEALTHY' or 'PAIR-MANUAL-TARGET-UNHEALTHY')
    end
    local tx=journal.tx
    if not hex(tx,32) then tx=canon.null end
    -- under the control lock (never waited for here)
    local locked,result=deps.try_lock(function()
      if deps.read(runtime..'/speed-pause.json')~=nil then return M.FALLBACK end
      local current=deps.current_revision()
      local state=deps.read_state()
      local intent=read_json(runtime..'/pair-auto-control.json')
      if current~=revision or not canon.is_object(state) or not canon.is_object(intent) or state.phase~='RUNNING' or intent.mode~='on'
         or state.id~=intent.id or state.revision~=intent.revision or intent.revision~=revision then
        return refuse('CONTROL-REVISION-STALE')
      end
      local old=read_json(runtime..'/pair-manual-control.json')
      if canon.is_object(old) and PENDING[old.state] then return refuse('PAIR-MANUAL-BUSY') end
      local id=uuid_hex(deps.read)
      local at=canon.float(deps.now())
      local source=arguments.request_source
      local row=canon.object({id=id,pair=state.id,revision=revision,direction=direction,state='QUEUED',requested=at,updated=at,
        selection=canon.object({tx=tx}),code=canon.null,request_source=SOURCES[source] and source or 'unknown'})
      deps.write(runtime..'/pair-manual-control.json',canon.encode(row))
      return canon.object({accepted=true,queued=true,completed=false,request_id=id,control_revision=revision})
    end)
    if not locked then return M.FALLBACK end
    return result
  end)
  if ok then return reply end
  return refuse('PAIR-MANUAL-REQUEST-UNCONFIRMED')
end

return M
