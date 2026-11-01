-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- setup.lua: the three page settings answered natively by the Lua monitor (owner plan item 3):
--   setup_probe     setup_config.probe_payload    -> probe_level, probe_boost, interval, measure_interval
--   setup_response  setup_config.response_payload -> response_metric [, response_compare] [, fast_switch] [, ping_interval]
--   setup_stats     stats_mode.payload            -> stats_mode, stats_until
--                   (mode 'retention': retention_settings.payload -> stats_retention_mode/_days/_mb [, history_days])
-- Same validation codes, same guards and the same UCI keys/values as setup_config.save(); the write is the
-- setup_save.lua procedure (refuse a pending delta, set, save, commit, verify with a fresh cursor) done in this
-- process with libuci instead of a child. Answers: {"saved":true,"mode":"monitor","requires_lan_certification":true}
-- or {"saved":false,"code":...}.
-- When a guard cannot be decided here without waiting (the control lock is held by someone else, or a speed
-- test pause file exists: speed_pause.public() needs Python's monotonic lease rules) the call returns
-- FALLBACK and the rpcd dispatcher lets agent.py answer exactly as before. Nothing waits in the event loop.
-- deps: {runner=<monitor runner>, runtime=, persist=, cursor=function() -> uci cursor, now=function()}
local canon=require('canon')

local M={}
M.FALLBACK={}
M.LEVELS={[1]={60,300},[2]={30,120},[3]={20,60},[4]={15,45},[5]={10,30}}
M.FORCED_BOOST={[1]=true,[2]=true}
M.RESPONSE_METRICS={['icmp-1.1.1.1']=true,['icmp-8.8.8.8']=true,['icmp-9.9.9.9']=true,websites=true}
M.PING_MIN,M.PING_MAX,M.PING_STEP=10,300,10  -- probe_policy.PING_INTERVAL_MIN/MAX/STEP
M.HOURS={[24]=true,[72]=true,[168]=true,[336]=true}
M.WRITER_CODES={['SETUP-PENDING-DELTA']=true,['SETUP-DELTA-UNVERIFIED']=true,['SETUP-SAVE-UNCONFIRMED']=true}
local NULL=canon.null

local function fail(code) error({code=code},0) end
local function is_dict(v) return canon.is_object(v) end
local function keys_are(t,list)
  local want={};for _,k in ipairs(list) do want[k]=true end
  local n=0
  for k in pairs(t) do if not want[k] then return false end;n=n+1 end
  return n==#list
end
local function keys_within(t,list)
  local want={};for _,k in ipairs(list) do want[k]=true end
  for k in pairs(t) do if not want[k] then return false end end
  return true
end
-- Python `type(v) is int`: a plain integral Lua number (canon boxes JSON floats like 3.0).
local function pyint(v) return type(v)=='number' and v%1==0 end

------------------------------------------------------------------------------------------------------
-- payloads (validation codes of setup_config.py / stats_mode.py)
------------------------------------------------------------------------------------------------------
function M.probe_payload(arguments)
  if not is_dict(arguments) or not keys_are(arguments,{'level','boost'}) or type(arguments.boost)~='boolean' then fail('PROBE-SETTINGS-FIELDS') end
  local level=arguments.level
  if not pyint(level) or not M.LEVELS[level] then fail('PROBE-SETTINGS-RANGE') end
  local boost=arguments.boost or M.FORCED_BOOST[level]==true
  return {probe_level=tostring(level),probe_boost=boost and '1' or '0',
    interval=tostring(M.LEVELS[level][1]),measure_interval=tostring(M.LEVELS[level][2])}
end

function M.response_payload(arguments)
  if not is_dict(arguments) or arguments.metric==nil or not keys_within(arguments,{'metric','compare','fast_switch','ping_interval'})
     or type(arguments.metric)~='string' or not M.RESPONSE_METRICS[arguments.metric] then fail('RESPONSE-METRIC-INVALID') end
  for _,key in ipairs({'compare','fast_switch'}) do
    if arguments[key]~=nil and type(arguments[key])~='boolean' then fail('RESPONSE-METRIC-INVALID') end
  end
  -- Owner ping cadence: whole seconds 10..300 in steps of 10 (probe_policy.ping_interval reads it back).
  local ping=arguments.ping_interval
  if ping~=nil and (not pyint(ping) or ping<M.PING_MIN or ping>M.PING_MAX or ping%M.PING_STEP~=0) then fail('PING-INTERVAL-INVALID') end
  local main={response_metric=arguments.metric}
  if arguments.compare~=nil then main.response_compare=arguments.compare and '1' or '0' end
  if arguments.fast_switch~=nil then main.fast_switch=arguments.fast_switch and '1' or '0' end
  if ping~=nil then main.ping_interval=string.format('%d',ping) end
  return main
end

function M.stats_payload(arguments,now)
  if is_dict(arguments) and arguments.mode=='retention' then return require('retention').payload(arguments) end
  if not is_dict(arguments) or (arguments.mode~='work' and arguments.mode~='diagnostic') then fail('STATS-SETTINGS-FIELDS') end
  if arguments.mode=='work' then
    if not keys_are(arguments,{'mode'}) then fail('STATS-SETTINGS-FIELDS') end
    return {stats_mode='work',stats_until='0'}
  end
  if not keys_are(arguments,{'mode','hours'}) or not pyint(arguments.hours) or not M.HOURS[arguments.hours] then fail('STATS-SETTINGS-FIELDS') end
  return {stats_mode='diagnostic',stats_until=string.format('%d',math.floor(now+arguments.hours*3600))}
end

M.KIND={setup_probe='probe',setup_response='response',setup_stats='stats'}

------------------------------------------------------------------------------------------------------
-- guards
------------------------------------------------------------------------------------------------------
-- rpc_throttle.allow(key, interval): RAM state under its own flock; any doubt allows the call.
function M.allow(deps,key,interval,now)
  local runner=deps.runner
  local path=deps.runtime..'/rpc-throttle.json'
  local ok,locked,allowed=pcall(runner.try_lock,deps.runtime,function()
    local rows=canon.object()
    local size=runner.file_size(path)
    if size and size<65536 then
      local okr,value=pcall(function() return canon.decode(runner.read_file(path)) end)
      if okr and is_dict(value) then rows=value end
    end
    local last=canon.number(rows[key])
    if last and 0<=now-last and now-last<interval then return false end
    local kept=canon.object()
    for k,v in pairs(rows) do local x=canon.number(v);if x and 0<=now-x and now-x<3600 then kept[k]=v end end
    kept[key]=canon.float(now)
    pcall(runner.write_ram,path,canon.encode(kept))
    return true
  end,'rpc-throttle.lock')
  if not ok or not locked then return true end
  return allowed
end

-- native_switch.journal_read().get('phase'); Refused -> CONFIG-RECOVERY-UNVERIFIED
function M.journal_phase(deps)
  local journal=require('journal')
  local runner=deps.runner
  local ok,value=pcall(journal.read,{fs={read=runner.read_file,unsafe=runner.unsafe},path=deps.persist..'/native-transaction.json'})
  if not ok then return nil,'CONFIG-RECOVERY-UNVERIFIED' end
  return value.phase
end

------------------------------------------------------------------------------------------------------
-- the UCI write (setup_save.lua for 'main' keys)
------------------------------------------------------------------------------------------------------
M.ALLOWED={response_metric=true,response_compare=true,fast_switch=true,stats_mode=true,stats_until=true,probe_level=true,
  stats_retention_mode=true,stats_retention_days=true,stats_retention_mb=true,history_days=true,
  probe_boost=true,interval=true,measure_interval=true,ping_interval=true}

function M.write(deps,main)
  local c=deps.cursor()
  local savedir=type(c.get_savedir)=='function' and c:get_savedir() or nil
  if type(savedir)~='string' or string.sub(savedir,1,1)~='/' then return 'SETUP-DELTA-UNVERIFIED' end
  local pending,_,open_errno=io.open(savedir..'/homensai_vpn','r')
  if pending then
    local byte,read_error=pending:read(1);pending:close()
    if byte then return 'SETUP-PENDING-DELTA' end
    if read_error then return 'SETUP-DELTA-UNVERIFIED' end
  elseif open_errno~=2 then return 'SETUP-DELTA-UNVERIFIED' end
  local committed=false
  local ok=pcall(function()
    for key,value in pairs(main) do
      assert(M.ALLOWED[key] and type(value)=='string')
      assert(c:set('homensai_vpn','main',key,value))
    end
    assert(c:save('homensai_vpn'));assert(c:commit('homensai_vpn'))
    committed=true
  end)
  if not ok then pcall(function() c:revert('homensai_vpn') end);return 'SETUP-SAVE-FAILED' end
  local verified=pcall(function()
    local fresh=deps.cursor()
    for key,value in pairs(main) do assert(fresh:get('homensai_vpn','main',key)==value) end
  end)
  if committed and not verified then return 'SETUP-SAVE-UNCONFIRMED' end
  return nil
end

------------------------------------------------------------------------------------------------------
-- setup_config.save(arguments, kind) for probe/response/stats
------------------------------------------------------------------------------------------------------
-- Returns the reply object, or M.FALLBACK when agent.py must answer.
function M.save(deps,method,arguments)
  local kind=M.KIND[method]
  if not kind then error('SETUP-KIND',0) end
  local now=deps.now()
  local ok,main=pcall(function()
    if kind=='probe' then return M.probe_payload(arguments)
    elseif kind=='response' then return M.response_payload(arguments)
    else return M.stats_payload(arguments,now) end
  end)
  if not ok then
    local code=type(main)=='table' and main.code or 'SETUP-INVALID'
    return canon.object({saved=false,code=code})
  end
  local runner=deps.runner
  if kind=='probe' and runner.exists(deps.runtime..'/speed-pause.json') then return M.FALLBACK end
  local okl,locked,reply=pcall(runner.try_lock,deps.runtime,function()
    if kind=='probe' then
      local phase,refused=M.journal_phase(deps)
      if refused then return canon.object({saved=false,code=refused}) end
      if phase=='ARMED' or phase=='APPLYING' or phase=='WAIT-CLIENT' or phase=='RESTORING' then
        return canon.object({saved=false,code='PROBE-SETTINGS-BUSY'})
      end
    end
    if not M.allow(deps,'setup:'..kind,2,now) then return canon.object({saved=false,code='RPC-RATE-LIMIT'}) end
    local code=M.write(deps,main)
    if code then return canon.object({saved=false,code=M.WRITER_CODES[code] and code or 'SETUP-SAVE-FAILED'}) end
    return canon.object({saved=true,mode='monitor',requires_lan_certification=true})
  end)
  if not okl then error('SYSTEM-001',0) end
  if not locked then return M.FALLBACK end
  return reply
end

return M
