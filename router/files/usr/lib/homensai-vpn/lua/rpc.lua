-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- rpc.lua: the page methods answered by the Lua monitor (owner plan item 3).
--   read methods   status / events / history / auto_live / inventory: from the monitor's memory, no Python;
--   setup methods  setup_probe / setup_response / setup_stats: natively in Lua (setup.lua), same codes;
--   button methods pair_manual (manual_request.lua) and native_start / native_stop / fault_start / fault_cancel
--                  (control_request.lua, plan item 4): the request files are written in Lua with Python's checks
--                  and codes; FALLBACK (agent.py answers) when Lua cannot decide without waiting.
--   other methods  (every other setup_*, statistics, speed, telegram, ...): answered by agent.py exactly as
--                  before. The rpcd dispatcher sends them there directly; this module answers FALLBACK for them
--                  so a caller of the bridge method is never left without an answer.
-- Argument validation is rpc_input.decode_request (size, duplicate keys, depth, node count, finite numbers,
-- ubus_rpc_session dropped) applied to the raw request text, so the codes are identical to Python's.
--
-- ubus object 'homensai-vpn-lua' (root only: not in the rpcd ACL; the page keeps calling 'homensai-vpn'):
--   rpc {method, request_file, reply_file}  the rpcd dispatcher's bridge: request text read from a RAM file
--        the dispatcher created, the canonical JSON reply written to the reply file (byte-exact JSON with nulls
--        and floats, like Python's json.dumps output); ubus answers {ok:true} or {fallback:true}.
--   status/events/history/auto_live/inventory/setup_*  direct calls (diagnostics: ubus call homensai-vpn-lua status);
--        libubus-lua drops JSON nulls in these, the page never uses them.
--   checkpoint, shutdown  for the init script (save accounting before procd stops the service).
local canon=require('canon')

local M={}
M.OBJECT='homensai-vpn-lua'
M.READ={'status','events','history','auto_live','inventory'}
M.NATIVE={'setup_probe','setup_response','setup_stats'}
M.MANUAL={'pair_manual'}  -- plan item 4: the click request in Lua (manual_request.lua), agent.py on FALLBACK
M.CONTROL={'native_start','native_stop','fault_start','fault_cancel'}  -- plan item 4: control_request.lua
-- plan item 7: speed test (speed.lua) and Telegram retry (telegram.lua) in the monitor; agent.py on FALLBACK (control
-- lock busy). telegram_test sends synchronously (up to 15 s): the rpcd dispatcher runs `lua telegram.lua call` for it.
M.SPEED={'speed_start','speed_cancel','speed_live','telegram_retry'}
M.FORWARD={'native_return','native_trial_start','native_confirm','setup_monitor','setup_system',
  'setup_telegram','setup_speed','setup_recovery','setup_onboarding','setup_check','stats_reset',
  'statistics','telegram_test','telegram_forget','terms_accept',
  'manual_switch','monitor_control','scan','priority_preview','priority_apply','preparation_preview','preparation_apply'}
M.PAGE_SAMPLE_OMIT={vendor_generation=true,vendor_tunnel_id=true,interface=true}
M.STATUS_DEFAULT=function(version) return canon.object({version=version,mode='monitor',error='SERVICE-STOPPED'}) end
M.FALLBACK=setmetatable({},{__tostring=function() return 'FALLBACK' end})

local function is_set(list) local s={};for _,v in ipairs(list) do s[v]=true end;return s end
local READ_SET,NATIVE_SET,FORWARD_SET,CONTROL_SET,SPEED_SET=is_set(M.READ),is_set(M.NATIVE),is_set(M.FORWARD),is_set(M.CONTROL),is_set(M.SPEED)
M.READ_SET,M.NATIVE_SET,M.FORWARD_SET,M.CONTROL_SET,M.SPEED_SET=READ_SET,NATIVE_SET,FORWARD_SET,CONTROL_SET,SPEED_SET

local function fail(code) error({code=code},0) end
local function code_of(err)
  if type(err)=='table' and type(err.code)=='string' then return err.code end
  local text=tostring(err)
  return string.find(text,'^[A-Z][A-Z0-9_-]*$') and #text<=96 and text or 'SYSTEM-001'
end
M.code_of=code_of

------------------------------------------------------------------------------------------------------
-- rpc_input.decode_request
------------------------------------------------------------------------------------------------------
local function walk(value,depth,counter)
  counter.nodes=counter.nodes+1
  if depth>64 or counter.nodes>10000 then fail('RPC-INPUT-COMPLEXITY') end
  if canon.is_float(value) then
    if value.value~=value.value or value.value==math.huge or value.value==-math.huge then fail('RPC-NONFINITE-NUMBER') end
  elseif type(value)=='number' then
    if value~=value or value==math.huge or value==-math.huge then fail('RPC-NONFINITE-NUMBER') end
  elseif type(value)=='table' and value~=canon.null then
    if canon.is_array(value) or (not canon.is_object(value) and #value>0) then
      for _,item in ipairs(value) do walk(item,depth+1,counter) end
    else
      for _,item in pairs(value) do walk(item,depth+1,counter) end
    end
  end
end

-- request: JSON text (stdin path) or an already parsed table (ubus). Returns the argument object.
function M.decode_request(request)
  local arguments
  if type(request)=='string' then
    if #request>65536 then fail('RPC-INPUT-SIZE') end
    if not string.find(request,'%S') then arguments=canon.object()
    else
      local ok,value=pcall(canon.decode,request)
      if not ok then
        local text=tostring(value)
        if string.find(text,'duplicate field',1,true) then fail('RPC-DUPLICATE-FIELD') end
        if string.find(text,'nesting limit',1,true) then fail('RPC-INPUT-COMPLEXITY') end  -- Python parses 65 levels, its walker refuses
        if string.find(text,'nonfinite',1,true) then fail('RPC-NONFINITE-NUMBER') end
        fail('RPC-INPUT-INVALID')
      end
      arguments=value
    end
  elseif type(request)=='table' and request~=canon.null then arguments=request
  elseif request==nil then arguments=canon.object()
  else fail('RPC-INPUT-OBJECT') end
  if canon.is_array(arguments) or canon.is_float(arguments) or (not canon.is_object(arguments) and #arguments>0) then fail('RPC-INPUT-OBJECT') end
  walk(arguments,0,{nodes=0})
  arguments.ubus_rpc_session=nil
  return canon.object(arguments)
end

------------------------------------------------------------------------------------------------------
-- replies
------------------------------------------------------------------------------------------------------
M.HISTORY_PARTS={{'native_history','events'},{'accounting','quality'}}
local function is_dict(v) return type(v)=='table' and v~=canon.null and not canon.is_array(v) and not canon.is_float(v) end

function M.split_history(status)
  local moved,names={},{}
  for _,part in ipairs(M.HISTORY_PARTS) do
    local parent,key=part[1],part[2]
    local value=status[parent]
    if is_dict(value) and value[key]~=nil then moved[parent..'.'..key]=value[key];value[key]=nil;names[#names+1]=parent..'.'..key end
  end
  local reliability=is_dict(status.accounting) and status.accounting.reliability or nil
  if is_dict(reliability) and reliability.events~=nil then moved['accounting.reliability.events']=reliability.events;reliability.events=nil;names[#names+1]='accounting.reliability.events' end
  table.sort(names)
  status.history_split=canon.array(names)
  return canon.object(moved)
end

-- Reply value for libubus-lua: float boxes unboxed, canon.null dropped (nil), metatables removed.
function M.for_ubus(value)
  if canon.is_float(value) then return value.value end
  if value==canon.null then return nil end
  if type(value)~='table' then return value end
  local out={}
  for k,v in pairs(value) do out[k]=M.for_ubus(v) end
  return out
end

local function shallow(t) local out={};for k,v in pairs(t) do out[k]=v end;return setmetatable(out,getmetatable(t)) end

-- state: {version=, now=function(), status=function() -> published status or nil, native_status=function(),
--   inventory=function(), native_history=function(), extras=function(status) (page fields, mutates the copy),
--   live_extras=function(result,native,clean), setup=function(method,arguments) -> reply | FALLBACK,
--   polled=function() (the page asked: bridge refresh), pair_manual=function(arguments) -> reply | FALLBACK,
--   control=function(method,arguments) -> reply | FALLBACK (native_start/native_stop/fault_start/fault_cancel)}
function M.new(state,runner)
  local self={state=state,runner=runner}
  local runtime=(runner and runner.RUNTIME) or '/var/run/homensai-vpn'
  local bridge_pattern='^'..string.gsub(runtime,'[%-%.]','%%%0')..'/rpc%-[a-z]+%.[A-Za-z0-9]+$'

  local function current_status(default)
    local status=state.status()
    if status==nil then return default end
    local copy=shallow(status)
    if is_dict(copy.accounting) then
      copy.accounting=shallow(copy.accounting)
      -- split_history moves reliability.events out of the reply: never out of the published status
      if is_dict(copy.accounting.reliability) then copy.accounting.reliability=shallow(copy.accounting.reliability) end
    end
    if is_dict(copy.native_history) then copy.native_history=shallow(copy.native_history) end
    return copy
  end

  function self.status_reply()
    if state.polled then pcall(state.polled) end
    local status=current_status(M.STATUS_DEFAULT(state.version))
    if canon.is_array(status.samples) or (type(status.samples)=='table' and #status.samples>0) then
      local samples=canon.array()
      for _,sample in ipairs(status.samples) do
        if is_dict(sample) then
          local row=canon.object()
          for k,v in pairs(sample) do if not M.PAGE_SAMPLE_OMIT[k] then row[k]=v end end
          samples[#samples+1]=row
        else samples[#samples+1]=sample end
      end
      status.samples=samples
    end
    status.native_failover=state.native_status()
    -- the history value is a cached object: split_history must not remove its events from the cache
    if state.native_history then local h=state.native_history();status.native_history=is_dict(h) and shallow(h) or h end
    if state.extras then state.extras(status) end
    status.server_time=state.now()
    M.split_history(status)
    return status
  end

  function self.events_reply()
    local status=current_status(M.STATUS_DEFAULT(state.version))
    return canon.object({events=status.events or canon.array()})
  end

  function self.history_reply()
    local status=current_status(canon.object())
    local history=M.split_history({accounting=is_dict(status.accounting) and status.accounting or nil,
      native_history=state.native_history and (function() local h=state.native_history();return is_dict(h) and shallow(h) or h end)() or nil})
    history.time=state.now()
    return history
  end

  -- auto_live.snapshot: the bounded read-only live view.
  function self.auto_live_reply()
    local now=state.now()
    local native=state.native_status()
    local monitor=state.status() or canon.object()
    local clean=canon.object()
    for _,key in ipairs({'state','reason','source','target','mode','proof_scope','destination_role','destination_profile_id','from_role','from_profile_id'}) do
      local value=native[key]
      if type(value)=='string' and #value<=128 and string.find(value,'^[A-Za-z0-9_:.-]+$') then clean[key]=value end
    end
    for _,key in ipairs({'certified','readiness_verified','original_restored','external_lan_verified','kernel_policy_verified','transition_metadata_present','route_changed','transition_completed','activation_reapply'}) do
      if type(native[key])=='boolean' then clean[key]=native[key] end
    end
    local stamp=canon.number(native.time)
    if stamp and stamp>=0 and stamp<=now+5 then clean.time=stamp end
    stamp=canon.number(monitor.time)
    local result=canon.object({time=(stamp and stamp>=0 and stamp<=now+5) and stamp or canon.null,server_time=now,native_failover=clean})
    local valid_for=canon.number(monitor.observation_valid_for)
    result.observation_valid_for=(valid_for and valid_for%1==0 and valid_for>=30 and valid_for<=900) and valid_for or 90
    if state.live_extras then state.live_extras(result,native,clean) end
    local rows=canon.array()
    local profiles=monitor.profiles
    if type(profiles)=='table' then
      for index,p in ipairs(profiles) do
        if index>8 then break end
        if is_dict(p) and type(p.id)=='string' and #p.id<=96 then
          local row=canon.object({id=p.id,observation_valid_for=result.observation_valid_for})
          for _,key in ipairs({'time','https_success'}) do local n=canon.number(p[key]);if n then row[key]=n end end
          local code=p.code
          row.code=(type(code)=='string' and string.find(code,'^[A-Z][A-Z0-9_-]*$') and #code<=96) and code or canon.null
          row.dns_ok=type(p.dns_ok)=='boolean' and p.dns_ok or canon.null
          rows[#rows+1]=row
        end
      end
    end
    result.profiles=rows
    if state.live_manual then result.manual_switch=state.live_manual(native) end
    local blockers=native.blockers
    if type(blockers)=='table' and blockers~=canon.null then
      local kept=canon.array()
      for index,b in ipairs(blockers) do
        if index>8 then break end
        if type(b)=='string' and string.find(b,'^[A-Z][A-Z0-9_-]*$') and #b<=96 then kept[#kept+1]=b end
      end
      clean.blockers=kept
    end
    if state.speed_pause then result.speed_pause=state.speed_pause() end
    return result
  end

  function self.inventory_reply() return state.inventory() end

  -- One call: a JSON object or M.FALLBACK; never a traceback; input problems become RPC-* codes like agent.call().
  function self.handle(method,request)
    local ok,reply=pcall(function()
      if FORWARD_SET[method] then return M.FALLBACK end
      local arguments=M.decode_request(request)
      if READ_SET[method] then
        if method=='status' then return self.status_reply()
        elseif method=='events' then return self.events_reply()
        elseif method=='history' then return self.history_reply()
        elseif method=='auto_live' then return self.auto_live_reply()
        else return self.inventory_reply() end
      end
      if method=='pair_manual' then
        if not state.pair_manual then return M.FALLBACK end
        return state.pair_manual(arguments)
      end
      if CONTROL_SET[method] then
        if not state.control then return M.FALLBACK end
        return state.control(method,arguments)
      end
      if SPEED_SET[method] then
        if not state.speed then return M.FALLBACK end
        return state.speed(method,arguments)
      end
      if NATIVE_SET[method] and state.setup then return state.setup(method,arguments) end
      if NATIVE_SET[method] then return M.FALLBACK end
      fail('RPC-UNKNOWN-METHOD')
    end)
    if ok then return reply end
    return canon.object({error=code_of(reply)})
  end

  -- The rpcd dispatcher's bridge: paths are the dispatcher's mktemp files in our RAM directory.
  function self.bridge_call(msg)
    local method,request_file,reply_file=msg.method,msg.request_file,msg.reply_file
    if type(method)~='string' or not string.find(method,'^[a-z_]+$') or #method>40 then return {error='RPC-UNKNOWN-METHOD'} end
    if type(request_file)~='string' or type(reply_file)~='string' or not string.find(request_file,bridge_pattern)
       or not string.find(reply_file,bridge_pattern) or string.find(request_file,'..',1,true) or string.find(reply_file,'..',1,true) then
      return {error='RPC-BRIDGE-PATH'}
    end
    local okr,text=pcall(runner.read_file,request_file)
    if not okr or text==nil then return {error='RPC-BRIDGE-PATH'} end
    if #text>65537 then text=string.sub(text,1,65537) end
    local reply=self.handle(method,text)
    if reply==M.FALLBACK then return {fallback=true} end
    local okw=pcall(runner.write_ram,reply_file,canon.encode(reply))
    if not okw then return {error='SYSTEM-001'} end
    return {ok=true}
  end

  -- libubus-lua object table: {['homensai-vpn-lua']={method={handler,policy},...}}; conn:add(object).
  function self.ubus_object(conn,ubus)
    local methods={}
    local function bind(name)
      methods[name]={function(req,msg)
        local reply=self.handle(name,msg)
        if reply==M.FALLBACK then reply={fallback=true} end
        conn:reply(req,M.for_ubus(reply))
      end,{}}
    end
    for _,name in ipairs(M.READ) do bind(name) end
    for _,name in ipairs(M.NATIVE) do bind(name) end
    for _,name in ipairs(M.MANUAL) do bind(name) end
    for _,name in ipairs(M.CONTROL) do bind(name) end
    methods.rpc={function(req,msg) conn:reply(req,self.bridge_call(msg or {})) end,
      {method=ubus.STRING,request_file=ubus.STRING,reply_file=ubus.STRING}}
    return {[M.OBJECT]=methods}
  end

  return self
end

return M
