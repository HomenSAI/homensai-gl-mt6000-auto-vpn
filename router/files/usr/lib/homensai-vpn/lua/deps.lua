-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- deps.lua: env.deps of the Lua supervisor (2.0.0-lua line) - the Python helper modules transaction.lua,
-- pair.lua, rollback.lua and manual.lua call, ported:
--   resolve_pair, diagnose, scoped_samples, profile_identity   failure_diagnosis (diagnosis.lua)
--   rtp_boot {assess, prepare, ready}                          rtp_boot (platform.lua)
--   rollback_recovery (helper table), activation_finalize       rollback_recovery / activation_recovery (recovery.lua)
--   record_switch_time                                          switch_timing.record
--   manual_control {valid_record, publish_result}              manual_control (the legacy one-shot queue)
--   testing_profile                                             fault_control.testing_profile
--   from_kernel                                                 channel_path.from_kernel
--   capture_latency                                             native_history.capture_transition_latency (item 6)
-- Not ported here (optional in transaction.lua, documented in LUA-AUTO-ITEM1): capture_website (the Lua monitor
-- measures no websites, so Python finds no sample either), clean_website_response, validate_delegated (Python's extra check of the
-- delegated journal records; pair.policy.metadata still checks pair_transition before every write).
local canon=require('canon')
local ctl=require('auto_control')
local py=require('py')
local identity=require('identity')
local diagnosis=require('diagnosis')
local platform=require('platform')
local recovery=require('recovery')

local M={}
local NULL=canon.null
local isnone,eq=py.isnone,py.eq

-- channel_path.from_kernel
local function profile_ok(v)
  return type(v)=='string' and (string.find(v,'^openvpn:%d+_%d+$')~=nil or string.find(v,'^wireguard:peer_%d+$')~=nil)
end
local function fresh15(value,now,age)
  local x=canon.number(value)
  if x==nil or type(value)=='boolean' or not py.finite(value) then return false end
  local d=now-x
  return -5<=d and d<=age
end
function M.from_kernel(kernel,source,target,now)
  now=canon.number(now)
  local result=canon.object({mode='continuous-pair',selection_proof='fw3-kernel-marking',valid_for=15,time=NULL,checked_at=NULL,
    confirmed=false,kernel_policy_verified=false,active_profile_id=NULL,transitioning=false,
    source_profile_id=profile_ok(source) and source or NULL,target_profile_id=profile_ok(target) and target or NULL,
    code='KERNEL-POLICY-UNVERIFIED',scope='new IPv4 LAN catch-all marking; Internet health is separate; no external-client proof'})
  if not canon.is_object(kernel) then return result end
  local stamp,role=kernel.time,kernel.role
  local x=canon.number(stamp)
  if x~=nil and type(stamp)~='boolean' and py.finite(stamp) and 0<=x and x<=now+5 then result.time=stamp;result.checked_at=stamp end
  local expected=(role=='source' and source) or (role=='target' and target) or nil
  if kernel.verified~=true or not (role=='source' or role=='target') or not py.truthy(expected) or not eq(kernel.profile_id,expected)
     or isnone(result.source_profile_id) or isnone(result.target_profile_id) or eq(source,target) or not fresh15(stamp,now,15) then return result end
  result.confirmed=true;result.kernel_policy_verified=true;result.active_profile_id=expected;result.code=NULL
  return result
end

-- manual_control.valid_record / publish_result (Lua argument order of manual.lua: id, state, tx, code)
local FIELDS={'schema','state','direction','request_id','control_revision','requested_at','updated_at','trial','until','source_id','target_id',
  'transaction_id','selection_hash','vendor_identity','settings_hash','code'}
local MANUAL_PENDING={QUEUED=true,CLAIMED=true,APPLYING=true,['WAIT-CLIENT']=true}
local MANUAL_STATES={QUEUED=true,CLAIMED=true,APPLYING=true,['WAIT-CLIENT']=true,COMPLETED=true,REFUSED=true,CANCELLED=true,UNCONFIRMED=true}
local function hex(v,n) return ctl.hex(v,n or 32) end
local function stamp_ok(v) local x=canon.number(v);return x~=nil and type(v)~='boolean' and py.finite(v) and x>0 end
function M.valid_record(record)
  if not canon.is_object(record) then return false end
  local allowed={}
  for _,k in ipairs(FIELDS) do allowed[k]=true;if record[k]==nil then return false end end
  allowed.request_source=true
  for k in pairs(record) do if not allowed[k] then return false end end
  if record.request_source~=nil then
    local s=record.request_source
    if not (s=='manual' or s=='test' or s=='programmatic' or s=='unknown') then return false end
  end
  local r=record
  if not (py.is_int(r.schema) and r.schema==1 and type(r.state)=='string' and MANUAL_STATES[r.state] and (r.direction=='reserve' or r.direction=='primary')
     and hex(r.request_id) and hex(r.control_revision) and stamp_ok(r.requested_at) and stamp_ok(r.updated_at)
     and canon.number(r.updated_at)>=canon.number(r.requested_at) and stamp_ok(r['until']) and canon.number(r['until'])>canon.number(r.requested_at)
     and type(r.trial)=='string' and r.trial~='') then return false end
  for _,k in ipairs({'source_id','target_id'}) do if type(r[k])~='string' or #r[k]==0 or #r[k]>128 then return false end end
  if r.source_id==r.target_id then return false end
  if not (r.transaction_id==NULL or hex(r.transaction_id)) then return false end
  for _,k in ipairs({'selection_hash','vendor_identity','settings_hash'}) do if not hex(r[k],64) then return false end end
  return r.code==NULL or ctl.code_ok(r.code)
end
function M.manual_control(env)
  local C={valid_record=M.valid_record}
  function C.publish_result(request_id,state,tx,code)
    if not hex(request_id) or not MANUAL_STATES[state] or state=='QUEUED' then ctl.refuse('MANUAL-RESULT-INVALID') end
    if code~=nil and not ctl.code_ok(code) then ctl.refuse('MANUAL-RESULT-INVALID') end
    if tx~=nil and not hex(tx) then ctl.refuse('MANUAL-RESULT-INVALID') end
    return env.run.lock(function()
      local path=env.runtime..'/manual-control.json'
      local record=ctl.read_json(env.run,path,canon.object({}))
      if not M.valid_record(record) or record.request_id~=request_id then return false end
      if not MANUAL_PENDING[record.state] then return false end
      if state=='COMPLETED' and (record.state=='QUEUED' or tx==nil) then ctl.refuse('MANUAL-COMPLETION-UNVERIFIED') end
      record.state=state;record.updated_at=canon.float(math.max(env.run.wall(),canon.number(record.requested_at)));record.code=code==nil and NULL or code
      if tx~=nil then record.transaction_id=tx end
      ctl.write_json(env.run,path,record)
      return true
    end,env.runtime)
  end
  return C
end

-- switch_timing.record: display-only running average of confirmed switch durations
M.TIMING_NAME='switch-timing.json'
local function round(x,digits) local m=10^digits;return math.floor(x*m+0.5)/m end
function M.record_switch_time(env,seconds)
  local ok,value=pcall(function()
    local x=canon.number(seconds)
    if x==nil or not py.finite(seconds) or x<1 or x>600 then return nil end
    local path=env.persist..'/'..M.TIMING_NAME
    local current=nil
    local rok,row=pcall(ctl.read_json,env.run,path,nil)
    if rok and canon.is_object(row) and py.is_int(row.count) and row.count>=1 then
      local avg=canon.number(row.avg_seconds)
      if avg~=nil and type(row.avg_seconds)~='boolean' and avg>=1 and avg<=600 then current={avg=round(avg,1),count=row.count} end
    end
    local average=current and (current.avg*0.7+x*0.3) or x
    local out=canon.object({avg_seconds=canon.float(round(average,2)),count=(current and current.count or 0)+1,last_seconds=canon.float(round(x,1)),
      updated=canon.float(env.run.wall())})
    ctl.write_json(env.run,path,out)
    return out
  end)
  return ok and value or nil
end

-- fault_control.testing_profile: only the active bounded, revision-fenced fault test relaxes return preference
function M.testing_profile(env,identifier)
  local ok,result=pcall(function()
    local envelope=ctl.read_json(env.run,env.runtime..'/fault-intent.json',canon.object({}))
    if not py.truthy(envelope) then return false end
    local value=envelope.data
    if not canon.is_object(value) or envelope.sha256~=canon.digest(value) then return false end
    local nonce=value.nonce;if nonce==nil then nonce='' end
    if not hex(py.str(nonce)) then return false end
    if value.phase~='ACTIVE' or value.pair_mode~=true then return false end
    -- require_revision
    local marker=ctl.read_json(env.run,env.runtime..'/auto-control-revision.json',canon.object({}))
    local n=0;if canon.is_object(marker) then for _ in pairs(marker) do n=n+1 end end
    if not hex(value.control_revision) or not canon.is_object(marker) or n~=1 or marker.revision~=value.control_revision then return false end
    -- require_auto_on
    local settings=value.control_settings;if settings==nil then settings=canon.object({}) end
    if not canon.is_object(settings) then return false end
    if settings.pair_auto_mode=='router-probed-ipv4' then
      local pair=require('pair')
      local revision=ctl.current_revision(env)
      if not require('manual').active(pair.read_state(env),pair.intent(env),revision) then return false end
    else
      local stopped=ctl.read_json(env.run,env.persist..'/native-stop.json',canon.object({}))
      local request=ctl.read_json(env.run,env.runtime..'/auto-control.json',canon.object({}))
      local active,stop=ctl.effective_intent(settings,stopped,request,env.run.wall(),require('transaction').deadline)
      if not active or stop then return false end
    end
    local until_=canon.number(value.monotonic_until)
    if until_==nil or not (env.run.clock()<until_) then return false end
    local listed=false
    if canon.is_array(value.profiles) then for _,p in ipairs(value.profiles) do if p==identifier then listed=true end end end
    if not listed then return false end
    local result=ctl.read_json(env.run,env.runtime..'/fault-result.json',canon.object({}))
    local cancel=ctl.read_json(env.run,env.runtime..'/fault-cancel.json',canon.object({}))
    return not eq(result.nonce,value.nonce) and not eq(cancel.nonce,value.nonce)
  end)
  return ok and result==true
end

function M.new(env,sys,backend)
  local D={}
  D.resolve_pair=diagnosis.resolve_pair
  D.diagnose=diagnosis.diagnose
  D.scoped_samples=diagnosis.scoped_samples
  D.profile_identity=identity.profile_identity
  D.from_kernel=M.from_kernel
  D.rtp_boot={
    assess=function() local ok,r=pcall(platform.rtp_assess,sys);if not ok then ctl.refuse('RTP-BOOT-PRECONDITION-UNVERIFIED') end;return r end,
    prepare=function(revision) return platform.rtp_prepare(env,sys,revision) end,
    ready=function() if not pcall(platform.rtp_ready,sys) then ctl.refuse('RTP-BOOT-PRECONDITION-UNVERIFIED') end;return true end,
    recovery_prefix=function() if not pcall(platform.rtp_recovery_prefix,sys) then ctl.refuse('RTP-BOOT-PRECONDITION-UNVERIFIED') end;return true end,
  }
  D.rollback_recovery=recovery.helpers()
  D.activation_finalize=function(e,state,value,allow_stopping) return recovery.finalize(e or env,state,value,allow_stopping) end
  D.record_switch_time=function(e,seconds) return M.record_switch_time(e or env,seconds) end
  D.manual_control=M.manual_control(env)
  D.testing_profile=function(identifier) return M.testing_profile(env,identifier) end
  -- native_history.capture_transition_latency (item 6): the event's HTTPS RTT from the Lua monitor's status.json
  D.capture_latency=function(value,status,binding,now) return require('history').capture_transition_latency(value,status,binding,now) end
  return D
end

return M
