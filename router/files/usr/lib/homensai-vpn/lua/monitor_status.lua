-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- monitor_status.lua: the page fields that agent.status_reply() composed from separate Python modules, read
-- from the same files by the Lua monitor (owner plan item 2):
--   switch_timing        switch_timing.read                  /etc/homensai-vpn/switch-timing.json
--   auto_control         auto_control.public_status          auto-control.json, native-stop.json,
--                                                            native-return-result.json, auto-control-revision.json,
--                                                            pair-auto-control.json, pair-auto-state.json
--   manual_switch        pair_manual.public_for_status       pair-manual-control.json, manual-control.json
--   native_history       native_history.read_public          native-history.json (+ backup), cached by file key
--   manual_switch_control: page_controls.lua (pair_manual.controls / manual_control.control_status, no Python);
--   scan: page_controls.scan_public; channel_path: channel_path.lua (plan item 4, no Python)
-- FALLBACK BRIDGE: status_bridge.py (Python, non-blocking child under uloop) is started only when the Lua
-- computation of manual_switch_control fails (Bridge:request, at most every BRIDGE_EVERY seconds, never on a
-- timer). Its answer (RAM file status-bridge.json) is used while it is younger than BRIDGE_VALID seconds; without
-- one the field is fail-safe: manual buttons blocked with PAIR-MANUAL-STATE-UNVERIFIED. Never a false "allowed".
-- (channel_path_fallback below stays for auto_live-style cached projections and the tests.)
local canon=require('canon')

local M={}
local NULL=canon.null
M.BRIDGE_EVERY=10;M.BRIDGE_VALID=30;M.BRIDGE_POLL_WINDOW=60;M.BRIDGE_NAME='status-bridge.json'
local PROFILE=function(s) return type(s)=='string' and (string.find(s,'^openvpn:%d+_%d+$') or string.find(s,'^wireguard:peer_%d+$'))~=nil end
M.PROFILE=PROFILE

local function num(v) return canon.number(v) end
local function finite(v) local x=num(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function none(v) return v==nil or v==NULL end
local function is_dict(v) return canon.is_object(v) end
local function hex(v,n) return type(v)=='string' and #v==n and string.find(v,'^[a-f0-9]+$')~=nil end
local function code_ok(v) return type(v)=='string' and #v>=1 and #v<=96 and string.find(v,'^[A-Z][A-Z0-9_-]*$')~=nil end
local function n0(v) if v==nil then return NULL end;return v end

-- env for the shared Lua modules (pair.lua, auto_control.lua, history.lua): run.fs over the monitor's runner.
function M.env(runner,runtime,persist)
  local fs={read=runner.read_file,write_atomic=runner.write_atomic,unsafe=runner.unsafe}
  return {run={fs=fs,wall=runner.wall,clock=runner.clock},runtime=runtime,persist=persist,runner=runner}
end

local function read_json(env,path,default)
  local text=env.run.fs.read(path)
  if text==nil then return default end
  return canon.decode(text)
end

------------------------------------------------------------------------------------------------------
-- switch_timing.read
------------------------------------------------------------------------------------------------------
function M.switch_timing(env)
  local ok,value=pcall(read_json,env,env.persist..'/switch-timing.json',nil)
  if not ok or not is_dict(value) then return NULL end
  local c,avg=value.count,num(value.avg_seconds)
  if type(c)~='number' or c%1~=0 or c<1 or not avg or not (1<=avg and avg<=600) then return NULL end
  return canon.object({avg_seconds=canon.float(math.floor(avg*10+0.5)/10),count=c,last_seconds=n0(value.last_seconds),updated=n0(value.updated)})
end

------------------------------------------------------------------------------------------------------
-- control revision (auto_control.current_revision): read; created under the control lock only when missing
-- and the lock is free right now (never waits in the event loop).
------------------------------------------------------------------------------------------------------
function M.current_revision(env)
  local path=env.runtime..'/auto-control-revision.json'
  local function valid()
    local ok,record=pcall(read_json,env,path,nil)
    if ok and is_dict(record) then
      local n=0;for _ in pairs(record) do n=n+1 end
      if n==1 and hex(record.revision,32) then return record.revision end
    end
    return nil
  end
  local revision=valid()
  if revision then return revision end
  local runner=env.runner
  if not (runner and runner.try_lock) then return nil end
  local ok,locked,value=pcall(runner.try_lock,env.runtime,function()
    local again=valid()
    if again then return again end
    local fresh=require('auto_control').uuid_hex()
    runner.write_atomic(path,canon.encode(canon.object({revision=fresh})))
    return fresh
  end)
  if ok and locked then return value end
  return nil
end

------------------------------------------------------------------------------------------------------
-- pair_auto.public_phase / auto_control.public_status
------------------------------------------------------------------------------------------------------
local function pair_module() return require('pair') end

-- pair_auto.read_state checks the envelope's sha256 (a sha256sum child on the router): the verdict is reused
-- while the file key (inode, size, mtime) is unchanged, so a status reply never hashes an unchanged file.
local state_cache={}
function M.read_state(env)
  local runner=env.runner
  local path=env.persist..'/pair-auto-state.json'
  local key=runner and runner.file_key and runner.file_key(path) or nil
  if key and state_cache.key==key and state_cache.path==path then
    if state_cache.err~=nil then error(state_cache.err,0) end
    return state_cache.value
  end
  local ok,value=pcall(function() return pair_module().read_state(env) end)
  state_cache={key=key,path=path,value=ok and value or nil,err=(not ok) and value or nil}
  if not ok then error(value,0) end
  return value
end

function M.public_phase(env)
  local ok,requested,state=pcall(function()
    local pair=pair_module()
    return pair.intent(env),M.read_state(env)
  end)
  if not ok then return 'UNKNOWN' end
  if requested.mode=='on' then
    if state.id~=requested.id or state.revision~=requested.revision then return 'STARTING' end
    return state.phase or 'STARTING'
  end
  if requested.mode=='off' and hex(requested.failed_request_id,32) and code_ok(requested.failure_code)
     and (state.phase==nil or state.phase=='STOPPED' or state.phase=='FAILED') then return 'FAILED' end
  if state.phase=='STARTING' or state.phase=='RUNNING' or state.phase=='STOPPING' then return 'STOPPING' end
  return n0(state.phase)
end

function M.auto_control(env,now)
  local valid=true
  local function record(path)
    local ok,row=pcall(read_json,env,path,canon.object())
    if not ok or not is_dict(row) then valid=false;return canon.object() end
    return row
  end
  local function stamp(row,key)
    local value=row[key]
    if value==nil then return 0 end
    if not finite(value) or num(value)<0 then valid=false;return 0 end
    return num(value)
  end
  local request=record(env.runtime..'/auto-control.json')
  local stopped=record(env.persist..'/native-stop.json')
  local requested,stop,until_=stamp(request,'time'),stamp(stopped,'requested'),stamp(request,'until')
  local mode=request.mode;if mode==nil then mode='off' end
  if mode~='on' and mode~='off' then valid=false end
  if stop>=requested then mode='off' end
  local result=record(env.runtime..'/native-return-result.json')
  local return_result=NULL
  if next(result)~=nil then
    local request_stamp,result_stamp,code=stamp(result,'request'),stamp(result,'time'),result.code
    if type(result.ok)~='boolean' or (not none(code) and not code_ok(code)) then valid=false
    else return_result=canon.object({request=request_stamp,ok=result.ok,code=n0(code),time=result_stamp}) end
  end
  local revision=M.current_revision(env)
  if stopped.control_revision_failed==true then revision=nil end
  local pair_ok,pair=pcall(function() return pair_module().intent(env) end)
  if not pair_ok then pair=nil end
  if pair and next(pair)==nil then pair=nil end
  if pair and valid and pair.revision==revision and (num(pair.time) or 0)>stop then
    mode=pair.mode;requested=math.max(requested,num(pair.time));until_=0
  end
  local failure=NULL
  pcall(function()
    if pair and valid and pair.mode=='off' and pair.revision==revision and code_ok(pair.failure_code) then
      failure=canon.object({code=pair.failure_code,time=finite(pair.time) and pair.time or 0})
    else
      local held=M.read_state(env)
      if valid and held.phase=='HELD' and code_ok(held.recovery_error) then
        failure=canon.object({code=held.recovery_error,time=finite(held.started) and held.started or 0})
      end
    end
  end)
  local context=require('auto_control').action_context(env,now)
  local latest=math.max(requested,stop)
  local origin=(valid and context.control_time==latest) and (context.control_source or 'unknown') or 'unknown'
  local action=NULL
  if valid then action=mode=='on' and 'start' or (mode=='off' and 'stop' or NULL) end
  return canon.object({requested=valid and mode or 'unknown',requested_at=latest,request_source=origin,request_action=action,
    activation_source=mode=='on' and origin or 'unknown',pair_phase=M.public_phase(env),failure=failure,
    control_revision=n0(revision),['until']=until_,reboot_autostart=false,return_result=return_result})
end

------------------------------------------------------------------------------------------------------
-- pair_manual.public / manual_control.public_status / pair_manual.public_for_status
------------------------------------------------------------------------------------------------------
function M.pair_manual_public(env)
  local ok,row=pcall(read_json,env,env.runtime..'/pair-manual-control.json',canon.object())
  if ok and is_dict(row) and next(row)==nil then return canon.object({state='IDLE',completed=false}) end
  local valid=ok and is_dict(row)
  if valid then
    local okv,result=pcall(function() return require('manual').valid(row) end)
    valid=okv and result
  end
  if not valid then return canon.object({state='UNCONFIRMED',completed=false,code='PAIR-MANUAL-STATE-UNVERIFIED'}) end
  return canon.object({state=row.state,direction=row.direction,request_id=row.id,requested_at=row.requested,updated_at=row.updated,
    request_source=row.request_source or 'unknown',completed=row.state=='COMPLETED',code=row.code})
end

local LEGACY_FIELDS={'schema','state','direction','request_id','control_revision','requested_at','updated_at','trial','until','source_id',
  'target_id','transaction_id','selection_hash','vendor_identity','settings_hash','code'}
local LEGACY_STATES={QUEUED=true,CLAIMED=true,APPLYING=true,['WAIT-CLIENT']=true,COMPLETED=true,REFUSED=true,CANCELLED=true,UNCONFIRMED=true}
local function stamp_ok(v) return finite(v) and num(v)>0 end
function M.legacy_valid(r)
  if not is_dict(r) then return false end
  local allowed={};for _,k in ipairs(LEGACY_FIELDS) do allowed[k]=true;if r[k]==nil then return false end end
  for k in pairs(r) do if not allowed[k] and k~='request_source' then return false end end
  local rs=r.request_source
  if rs~=nil and rs~='manual' and rs~='test' and rs~='programmatic' and rs~='unknown' then return false end
  if r.schema~=1 or not LEGACY_STATES[r.state] or (r.direction~='reserve' and r.direction~='primary') then return false end
  if not hex(r.request_id,32) or not hex(r.control_revision,32) or not stamp_ok(r.requested_at) or not stamp_ok(r.updated_at) then return false end
  if num(r.updated_at)<num(r.requested_at) or not stamp_ok(r['until']) or num(r['until'])<=num(r.requested_at) then return false end
  if type(r.trial)~='string' or r.trial=='' then return false end
  for _,k in ipairs({'source_id','target_id'}) do if type(r[k])~='string' or #r[k]<1 or #r[k]>128 then return false end end
  if r.source_id==r.target_id or not (none(r.transaction_id) or hex(r.transaction_id,32)) then return false end
  for _,k in ipairs({'selection_hash','vendor_identity','settings_hash'}) do if not hex(r[k],64) then return false end end
  return none(r.code) or code_ok(r.code)
end

function M.legacy_public(env)
  local ok,record=pcall(read_json,env,env.runtime..'/manual-control.json',canon.object())
  if not ok then return canon.object({state='UNCONFIRMED',completed=false,code='MANUAL-STATE-UNVERIFIED'}) end
  if is_dict(record) and next(record)==nil then return canon.object({state='IDLE',completed=false}) end
  if not M.legacy_valid(record) then return canon.object({state='UNCONFIRMED',completed=false,code='MANUAL-STATE-UNVERIFIED'}) end
  local out=canon.object()
  for _,k in ipairs({'state','direction','request_id','requested_at','updated_at','source_id','target_id','transaction_id','code'}) do out[k]=record[k] end
  out.completed=record.state=='COMPLETED';out.request_source=record.request_source or 'unknown'
  return out
end

-- returns use_pair, public
function M.manual_switch(env,native,available)
  local pair_result,legacy=M.pair_manual_public(env),M.legacy_public(env)
  native=is_dict(native) and native or canon.object()
  local function requested(row) local v=row.requested_at;if finite(v) then return num(v) end;return -1 end
  local use_pair=available==true or native.mode=='continuous-pair' or (requested(pair_result)>=0 and requested(pair_result)>=requested(legacy))
  return use_pair,use_pair and pair_result or legacy
end

------------------------------------------------------------------------------------------------------
-- channel_path fallback (channel_path.from_kernel / cached_projection / snapshot({},{},None))
------------------------------------------------------------------------------------------------------
local function fresh(value,now,age) return finite(value) and -5<=now-num(value) and now-num(value)<=age end
function M.from_kernel(kernel,source,target,now)
  local result=canon.object({mode='continuous-pair',selection_proof='fw3-kernel-marking',valid_for=15,time=NULL,checked_at=NULL,
    confirmed=false,kernel_policy_verified=false,active_profile_id=NULL,transitioning=false,
    source_profile_id=PROFILE(source) and source or NULL,target_profile_id=PROFILE(target) and target or NULL,
    code='KERNEL-POLICY-UNVERIFIED',scope='new IPv4 LAN catch-all marking; Internet health is separate; no external-client proof'})
  if type(kernel)~='table' or kernel==NULL then return result end
  local stamp,role=kernel.time,kernel.role
  if finite(stamp) and num(stamp)>=0 and num(stamp)<=now+5 then result.time=stamp;result.checked_at=stamp end
  local expected=role=='source' and source or (role=='target' and target or nil)
  if kernel.verified~=true or (role~='source' and role~='target') or not expected or kernel.profile_id~=expected
     or result.source_profile_id==NULL or result.target_profile_id==NULL or source==target or not fresh(stamp,now,15) then return result end
  result.confirmed=true;result.kernel_policy_verified=true;result.active_profile_id=expected;result.code=NULL
  return result
end
function M.cached_projection(value,now)
  if not is_dict(value) then return M.from_kernel(nil,nil,nil,now) end
  local source,target=value.source_profile_id,value.target_profile_id
  if value.mode~='continuous-pair' or value.selection_proof~='fw3-kernel-marking' then return M.from_kernel(nil,source,target,now) end
  local active=value.active_profile_id
  local role=active==source and 'source' or (active==target and 'target' or nil)
  local kernel={verified=value.confirmed==true and value.kernel_policy_verified==true,time=value.checked_at,role=role,profile_id=active}
  local result=M.from_kernel(kernel,source,target,now)
  result.transitioning=value.transitioning==true
  if result.transitioning then result.confirmed=false;result.kernel_policy_verified=false;result.active_profile_id=NULL end
  return result
end
function M.empty_snapshot(now)
  return canon.object({time=now,confirmed=false,active_profile_id=NULL,source_profile_id=NULL,target_profile_id=NULL,
    transitioning=false,scope='client-confirmed general VPN rule'})
end
function M.channel_path_fallback(native,now)
  native=is_dict(native) and native or canon.object()
  local required=native.mode=='continuous-pair' or native.proof_scope=='router-probed-ipv4'
  if not required then return M.empty_snapshot(now) end
  if native.state=='BLOCKED' or (canon.is_array(native.blockers) and #native.blockers>0) then return M.from_kernel(nil,native.source,native.target,now) end
  if is_dict(native.channel_path) then
    local projected=M.cached_projection(native.channel_path,now)
    if projected.source_profile_id==native.source and projected.target_profile_id==native.target then return projected end
  end
  return M.from_kernel(nil,native.source,native.target,now)
end

-- manual_control.control_status() refusal shape (legacy path without a pair session)
function M.legacy_controls_fallback(now)
  return canon.object({time=now,control_revision=NULL,available=false,blockers=canon.array({'MANUAL-STATE-UNVERIFIED'}),bridge='pending'})
end

function M.controls_fallback(now)
  return canon.object({available=false,mode='continuous-pair',time=now,blockers=canon.array({'PAIR-MANUAL-STATE-UNVERIFIED'}),
    bridge='pending'})
end

------------------------------------------------------------------------------------------------------
-- the fallback bridge to status_bridge.py
------------------------------------------------------------------------------------------------------
local Bridge={};Bridge.__index=Bridge
function M.Bridge(runner,runtime)
  return setmetatable({runner=runner,path=runtime..'/'..M.BRIDGE_NAME,running=false,started=nil,requested=nil,value=nil,key=nil},Bridge)
end
-- The Lua computation failed for this status reply: start a refresh when due (never more than one child; never
-- blocks). Nothing else starts it.
function Bridge:request()
  local runner=self.runner
  local now=runner.clock()
  self.requested=now
  if self.running or not runner.bridge then return end
  if self.started and now-self.started<M.BRIDGE_EVERY then return end
  self.running=true;self.started=now
  local ok=pcall(runner.bridge,self.path,function() self.running=false end)
  if not ok then self.running=false end
end
-- Fresh bridge answer {manual_switch_control=, channel_path=} or nil.
function Bridge:current(wall)
  local runner=self.runner
  local key=runner.file_key and runner.file_key(self.path) or nil
  if key==nil then self.value=nil;self.key=nil;return nil end
  if key~=self.key then
    local ok,value=pcall(function() return canon.decode(runner.read_file(self.path)) end)
    self.key=key;self.value=(ok and is_dict(value)) and value or nil
  end
  local value=self.value
  if not value or not finite(value.time) or wall-num(value.time)>M.BRIDGE_VALID or wall-num(value.time)< -5 then return nil end
  return value
end

------------------------------------------------------------------------------------------------------
-- native_history.read_public, cached in memory by (detail days, hour, file keys)
------------------------------------------------------------------------------------------------------
local history_cache={key=nil,value=nil}
function M.native_history(env,days,now)
  local ok,value=pcall(function()
    local history=require('history')
    local h=history.new(env,env.persist,10000,days)
    local runner=env.runner
    local key=table.concat({tostring(days),tostring(math.floor(now/3600)),tostring(runner.file_key and runner.file_key(h.path)),
      tostring(runner.file_key and runner.file_key(h.backup))},'|')
    if runner.file_key and history_cache.key==key then return history_cache.value end
    local data=h:load()
    h:migrate(data)
    h:prune(data,now)
    local weekly=NULL
    local all=true
    for _,row in ipairs(data.events) do if row.counted_metrics==nil then all=false end end
    if all and (num(data.detail_budget_dropped) or 0)==0 then
      weekly=canon.object()
      for _,metric in ipairs(history.METRICS) do
        local n=0
        for _,row in ipairs(data.events) do
          for _,m in ipairs(canon.is_array(row.counted_metrics) and row.counted_metrics or {}) do if m==metric then n=n+1 end end
        end
        weekly[metric]=n
      end
    end
    local events=data.events
    local tail=canon.array();for i=math.max(1,#events-99),#events do tail[#tail+1]=events[i] end
    local complete=#events==0 or (events[#events].sequence-events[1].sequence+1==#events)
    local available=runner.exists and (runner.exists(h.path) or runner.exists(h.backup)) or false
    local public=canon.object({available=available,restored_from_backup=h.restored,timezone=data.timezone,sequence=data.sequence,
      events=tail,totals=data.totals or canon.object(),counter_accuracy=n0(data.counter_accuracy),returns_since=n0(data.returns_since),
      weekly=weekly,weekly_detail_complete=complete,detail_days=days,retained_events=#events,
      detail_budget_dropped=data.detail_budget_dropped or 0,months=data.months,days=data.days or canon.object(),
      daily_since=n0(data.daily_since),event_history_truncated=data.sequence>math.min(100,#events),
      scope='controller transitions; not LAN availability or router power-loss proof'})
    history_cache.key=key;history_cache.value=public
    return public
  end)
  if ok then return value end
  return canon.object({available=false,error='HISTORY-001'})
end

return M
