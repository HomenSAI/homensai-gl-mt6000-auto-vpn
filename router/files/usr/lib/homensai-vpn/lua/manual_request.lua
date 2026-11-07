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

-- F-35: answers already given to caller-supplied request ids (pair_manual.ledger_*; same file and shape).
M.LEDGER_LIMIT=16
local function client_valid(v) return type(v)=='string' and #v>=8 and #v<=64 and string.find(v,'^[A-Za-z0-9_-]+$')~=nil end
M.client_valid=client_valid
local function ledger_path(runtime) return runtime..'/pair-manual-requests.json' end
-- -> entries (newest last); error('PAIR-MANUAL-STATE-UNVERIFIED') on a damaged file
function M.ledger_read(deps)
  local text=deps.read(ledger_path(deps.runtime))
  if text==nil then return {} end
  local ok,data=pcall(canon.decode,text)
  if not ok or not canon.is_object(data) then error('PAIR-MANUAL-STATE-UNVERIFIED',0) end
  local count=0
  for k in pairs(data) do count=count+1;if k~='entries' then error('PAIR-MANUAL-STATE-UNVERIFIED',0) end end
  if count==0 then return {} end
  local entries=data.entries
  if type(entries)~='table' or canon.is_object(entries) and next(entries)~=nil or #entries>M.LEDGER_LIMIT then error('PAIR-MANUAL-STATE-UNVERIFIED',0) end
  for _,e in ipairs(entries) do
    local keys=0
    if canon.is_object(e) then for k in pairs(e) do keys=keys+1;if k~='client' and k~='reply' then keys=-100 end end end
    if keys~=2 or not client_valid(e.client) or not canon.is_object(e.reply) or type(e.reply.accepted)~='boolean' then
      error('PAIR-MANUAL-STATE-UNVERIFIED',0)
    end
  end
  return entries
end
-- BH-07 (bug hunt 07.11.2026): a refusal for a condition that passes by itself is not kept for its id, so the owner's
-- Retry with the same id is decided afresh; accepted answers and lasting refusals are kept and replayed. An older entry
-- of this kind is ignored the same way. Python: pair_manual.TRANSIENT_REFUSALS / transient_refusal.
M.TRANSIENT={['SPEED-BUSY']=true,['PAIR-MANUAL-BUSY']=true,['PAIR-MANUAL-REQUEST-UNCONFIRMED']=true}
function M.transient_refusal(reply)
  local blockers=canon.is_object(reply) and reply.blockers or nil
  return canon.is_object(reply) and reply.accepted==false and type(blockers)=='table' and type(blockers[1])=='string'
    and M.TRANSIENT[blockers[1]]==true
end
function M.ledger_find(deps,client)
  local entries=M.ledger_read(deps)
  for i=#entries,1,-1 do
    if entries[i].client==client then
      if M.transient_refusal(entries[i].reply) then return nil end
      local copy=canon.object({})
      for k,v in pairs(entries[i].reply) do copy[k]=v end
      copy.replayed=true
      return copy
    end
  end
  return nil
end
-- caller holds the control lock
function M.ledger_store_locked(deps,client,reply)
  local kept={}
  for _,e in ipairs(M.ledger_read(deps)) do if e.client~=client then kept[#kept+1]=e end end
  local out={}
  for i=math.max(1,#kept-(M.LEDGER_LIMIT-2)),#kept do out[#out+1]=kept[i] end
  out[#out+1]=canon.object({client=client,reply=reply})
  deps.write(ledger_path(deps.runtime),canon.encode(canon.object({entries=canon.array(out)})))
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
    if key~='direction' and key~='control_revision' and key~='request_source' and key~='client_request_id' then
      return canon.object({accepted=false,blockers=canon.array({'PAIR-MANUAL-FIELDS'})})
    end
  end
  if arguments.direction==nil or arguments.control_revision==nil then
    return canon.object({accepted=false,blockers=canon.array({'PAIR-MANUAL-FIELDS'})})
  end
  local direction,revision=arguments.direction,arguments.control_revision
  if (direction~='primary' and direction~='reserve' and direction~='resume') or not hex(revision,32) then return refuse('PAIR-MANUAL-FIELDS') end
  local client=arguments.client_request_id
  if client~=nil and not client_valid(client) then return refuse('PAIR-MANUAL-FIELDS') end
  if client~=nil then
    local found,stored=pcall(M.ledger_find,deps,client)
    if not found then return refuse('PAIR-MANUAL-STATE-UNVERIFIED') end
    if stored then return stored end
  end
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
      if client~=nil then
        local stored=M.ledger_find(deps,client)  -- the same id raced in meanwhile: its answer, never a second action
        if stored then return stored end
      end
      local old=read_json(runtime..'/pair-manual-control.json')
      if canon.is_object(old) and PENDING[old.state] then return refuse('PAIR-MANUAL-BUSY') end
      local id=uuid_hex(deps.read)
      local at=canon.float(deps.now())
      local source=arguments.request_source
      local row=canon.object({id=id,pair=state.id,revision=revision,direction=direction,state='QUEUED',requested=at,updated=at,
        selection=canon.object({tx=tx}),code=canon.null,request_source=SOURCES[source] and source or 'unknown'})
      deps.write(runtime..'/pair-manual-control.json',canon.encode(row))
      local accepted=canon.object({accepted=true,queued=true,completed=false,request_id=id,control_revision=revision})
      if client~=nil then M.ledger_store_locked(deps,client,accepted) end
      return accepted
    end)
    if not locked then return M.FALLBACK end
    return result
  end)
  if not ok then reply=refuse('PAIR-MANUAL-REQUEST-UNCONFIRMED') end
  if client==nil or reply==M.FALLBACK or reply.accepted==true or reply.replayed==true then return reply end
  -- keep the refusal for this id (pair_manual.request), or let agent.py decide and keep it when the lock is held
  local okl,locked,result=pcall(deps.try_lock,function()
    local stored=M.ledger_find(deps,client)
    if stored then return stored end
    if not M.transient_refusal(reply) then M.ledger_store_locked(deps,client,reply) end  -- BH-07
    return reply
  end)
  if not okl then return reply end
  if not locked then return M.FALLBACK end
  return result
end

return M
