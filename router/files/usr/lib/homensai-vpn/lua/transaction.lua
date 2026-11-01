-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- transaction.lua: the guarded switch transaction of native_switch.py in Lua (2.0.0-lua-alpha2).
--
-- attempt(): ARMED -> APPLYING (reorder / apply / verify-diagnostic / verify-kernel) -> WAIT-CLIENT
-- (router probes confirm the destination) -> COMMITTED (-> HELD-ON-RESERVE for an owner click); any failure
-- -> rollback.rollback_counted(); ROLLBACK_FAILURE_LIMIT=2 ends in rollback.give_up(). Also finish_committed,
-- committed_recovery_decision, operator_return/handle_return, publish() (native-status.json + history).
--
-- Deviation from Python, by design of the single uloop process: the APPLYING steps run in this process
-- (Python forks `native_switch.py apply <tx>`); journal.pid therefore stays null and recovery never has a
-- child to kill. The journal fields and their order of writes are unchanged, so a crash at any step is
-- recovered by rollback.lua exactly like a dead Python child.
--
-- env: run (runner.lua or fakes: fs/wall/clock/fenced/lock/require_revision/sha256), backend (Linux port:
-- policy/order/diagnostic/attest_policy/reorder/apply/guard/unguard/devices/health/recovery_ready/
-- kernel_fingerprint/guard_exists/candidates/acceleration/use_process_bindings/probe/trace/
-- clear_native_options/write_lease), deps (modules not ported yet, optional: from_kernel, testing_profile,
-- resolve_pair, profile_identity, scoped_samples, diagnose, rtp_boot, rollback_recovery, activation_finalize,
-- validate_delegated), runtime, persist, stop() -> bool, sleep(seconds).
local canon=require('canon')
local journal=require('journal')
local ctl=require('auto_control')

local M={}
local NULL=canon.null
local isnone,num,finite=ctl.isnone,ctl.num,ctl.finite
local refuse,is_refused=ctl.refuse,ctl.is_refused
M.Refused=ctl.Refused
M.refuse=refuse

M.RETURN_CHECKS=6
M.ROLLBACK_FAILURE_LIMIT=2
M.TRANSACTION_SECONDS=120
M.RTP_TIMEOUT=45
M.POST_RTP_SECONDS=30
M.RTP_DISPATCH_RESERVE=M.RTP_TIMEOUT+M.POST_RTP_SECONDS
M.RETURN_PAUSE=10
M.VERIFY_VENDOR_WAIT=20
M.VERIFY_TRANSIENT={['VENDOR-WORKER-BUSY']=true,['VENDOR-SETTLING']=true,['VENDOR-WORKER-QUIET-UNVERIFIED']=true}
M.RECOVERY_PHASES={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true,['RELEASE-PENDING']=true}
M.PROOF_SCOPE='external-lan'
M.SCOPES={['external-lan']=true,['router-hosted-ipv4']=true,['router-probed-ipv4']=true}
M.APPLY_STAGES={reorder=true,apply=true,['rtp-dispatch']=true,['rtp-returned']=true,['verify-diagnostic']=true,['verify-kernel']=true,done=true}

------------------------------------------------------------------------------------------------------
-- small helpers (Python list/dict semantics over canon values)
------------------------------------------------------------------------------------------------------
function M.paths(env)
  return {journal=env.persist..'/native-transaction.json',state=env.runtime..'/native-status.json',
          cert=env.persist..'/native-certificate.json',attempts=env.persist..'/native-attempts.json',
          alarm=env.persist..'/native-journal-alarm.json',stop=env.persist..'/native-stop.json',
          confirm=env.runtime..'/native-confirm.json',status=env.runtime..'/status.json',
          return_request=env.runtime..'/native-return.json',return_result=env.runtime..'/native-return-result.json',
          lease=env.runtime..'/native-lease.json',progress=env.runtime..'/native-apply-progress.json',
          attempt_result=env.runtime..'/native-attempt-result.json',timing=env.runtime..'/pair-manual-timing.json'}
end
local function same_list(a,b)
  if isnone(a) or isnone(b) or type(a)~='table' or type(b)~='table' or #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i] then return false end end
  return true
end
M.same_list=same_list
local function copy_list(a) local out={};for i=1,#a do out[i]=a[i] end;return canon.array(out) end
M.copy_list=copy_list
local function index_of(list,x) for i=1,#list do if list[i]==x then return i end end;return nil end
local function order_is(env,order,hash)  -- backend.order()==(order,hash)
  local live,live_hash=env.backend.order()
  return same_list(live,order) and live_hash==hash
end
M.order_is=order_is
local function in_orders(order,...)  -- `order in (a,b,...)`, skipping None entries
  for _,candidate in ipairs({...}) do if not isnone(candidate) and same_list(order,candidate) then return true end end
  return false
end
M.in_orders=in_orders
function M.code_of(err)
  if is_refused(err) and ctl.code_ok(err.code) then return err.code end
  if is_refused(err) and type(err.code)=='string' and string.find(err.code,'^[A-Z0-9_-]+$') and #err.code<=96 then return err.code end
  return 'NATIVE-SYSTEM-001'
end
local code_of=M.code_of
local function wall(env) return env.run.wall() end
local function mono(env) return env.run.clock() end
local function fwall(env) return canon.float(wall(env)) end
local function getd(t,k,default) local v=t[k];if isnone(v) then return default end;return v end
M.getd=getd

------------------------------------------------------------------------------------------------------
-- journal
------------------------------------------------------------------------------------------------------
function M.journal_read(env)
  return journal.read({fs=env.run.fs,path=M.paths(env).journal,hash=env.run.sha256})
end
-- journal_write(): the delegated records (vendor_profiles, pair_transition, restore_* steps) are checked by
-- deps.validate_delegated when a port exists, else by pair.policy.metadata for pair_transition; the writer then
-- pins the value as its own template (journal.lua rule: never invent a record Python did not validate).
function M.journal_write(env,value)
  if env.deps and env.deps.validate_delegated then env.deps.validate_delegated(value) end
  if not isnone(value.pair_transition) then
    local ok=pcall(require('pair').policy.metadata,value)
    if not ok then refuse('JOURNAL-INTEGRITY-FAILED') end
  end
  return journal.write({fs=env.run.fs,path=M.paths(env).journal,now=env.run.wall,hash=env.run.sha256,template=value},value)
end
function M.note_phase(env,value,phase) journal.note_phase(value,phase,wall(env)) end
function M.require_control_revision(env,expected) env.run.require_revision(expected,env.runtime) end
function M.bind_policy_context(env,record)
  if env.backend.use_process_bindings then env.backend.use_process_bindings(getd(record,'process_bindings',nil)) end
end

------------------------------------------------------------------------------------------------------
-- deadline(): a number, a numeric string or an ISO-8601 time with an offset
------------------------------------------------------------------------------------------------------
local function days_from_civil(y,m,d)
  y=(m<=2) and y-1 or y
  local era=math.floor(y/400)
  local yoe=y-era*400
  local doy=math.floor((153*(m+(m>2 and -3 or 9))+2)/5)+d-1
  local doe=yoe*365+math.floor(yoe/4)-math.floor(yoe/100)+doy
  return era*146097+doe-719468
end
function M.deadline(value)
  if isnone(value) or value=='' then return 0 end
  local result=num(value)
  if result==nil then
    if type(value)~='string' then refuse('BOUNDED-DEADLINE-REQUIRED') end
    result=tonumber(value)
    if result==nil then
      local text=string.gsub(value,'Z$','+00:00')
      local y,mo,d,h,mi,s,frac,sign,oh,om=string.match(text,'^(%d%d%d%d)%-(%d%d)%-(%d%d)[T ](%d%d):(%d%d):?(%d?%d?)%.?(%d*)([+-])(%d%d):(%d%d)$')
      if not y then
        if string.match(text,'^%d%d%d%d%-%d%d%-%d%d[T ]%d%d:%d%d') then refuse('DEADLINE-TIMEZONE-REQUIRED') end
        refuse('BOUNDED-DEADLINE-REQUIRED')
      end
      y,mo,d,h,mi=tonumber(y),tonumber(mo),tonumber(d),tonumber(h),tonumber(mi)
      s=tonumber(s) or 0
      if mo<1 or mo>12 or d<1 or d>31 or h>23 or mi>59 or s>59 then refuse('BOUNDED-DEADLINE-REQUIRED') end
      local offset=(tonumber(oh)*3600+tonumber(om)*60)*(sign=='-' and -1 or 1)
      result=days_from_civil(y,mo,d)*86400+h*3600+mi*60+s-offset
      if frac~='' then result=result+tonumber('0.'..string.sub(frac,1,6)) end
    end
  end
  if result~=result or result==math.huge or result==-math.huge or result<0 then refuse('BOUNDED-DEADLINE-REQUIRED') end
  return result
end

------------------------------------------------------------------------------------------------------
-- progress files, lease, expiry
------------------------------------------------------------------------------------------------------
function M.progress_read(env,path,kind)
  local ok,record=pcall(ctl.read_json,env.run,path,nil)
  if not ok then refuse('NATIVE-PROGRESS-UNVERIFIED') end
  if record==nil then return canon.object({}) end
  local function stamp(v) local x=num(v);return x~=nil and finite(x) and x>=0 end
  local valid=canon.is_object(record)
  if valid and kind=='attempts' then
    local trial=record.trial
    local count=record.count
    valid=record['until']~=nil and count~=nil and record.trial~=nil and record.time~=nil
      and type(count)=='number' and count%1==0 and count>=0 and count<=3
      and stamp(record['until']) and stamp(record.time)
      and ((trial==NULL and count==0) or (type(trial)=='string' and #trial>=1 and #trial<=96 and string.find(trial,'^[A-Za-z0-9_:.%-]+$')~=nil))
  elseif valid and kind=='return' then
    valid=record.request~=nil and record.ok~=nil and record.code~=nil and record.time~=nil
      and stamp(record.request) and num(record.request)>0 and stamp(record.time)
      and type(record.ok)=='boolean' and ctl.code_ok(record.code)
  else valid=false end
  if not valid then refuse('NATIVE-PROGRESS-UNVERIFIED') end
  return record
end

function M.monotonic_lease(env,settings,until_,wall_,mono_)
  wall_=wall_ or wall(env);mono_=mono_ or mono(env)
  local trial=settings.native_trial
  if type(trial)~='string' or trial=='' or not (wall_<until_ and until_<=wall_+14400) then return 0,'BOUNDED-DEADLINE-REQUIRED' end
  local identity=canon.digest(canon.object({trial=trial,['until']=canon.float(until_)}))
  -- Python: digest({'trial':trial,'until':until}) where until is a float from deadline(); an integral until
  -- (e.g. from a JSON int) is encoded as an int there. Keep the Python text: float unless the source was an int.
  if until_%1==0 and env.lease_until_is_int then identity=canon.digest(canon.object({trial=trial,['until']=until_})) end
  local path=M.paths(env).lease
  local ok,record=pcall(ctl.read_json,env.run,path,nil)
  if not ok then return 0,'LEASE-INTEGRITY-FAILED' end
  if record~=nil then
    if not canon.is_object(record) then return 0,'LEASE-INTEGRITY-FAILED' end
    local data=record.data
    if not canon.is_object(data) or record.sha256~=canon.digest(data) then return 0,'LEASE-INTEGRITY-FAILED' end
    local end_,start=num(data.monotonic_until),num(data.monotonic_start)
    if not ctl.hex(data.identity,64) or not end_ or not start or not finite(end_) or not finite(start)
       or not (0<=start and start<=mono_) or not (start<=end_ and end_<=start+14400) then return 0,'LEASE-INTEGRITY-FAILED' end
    if data.identity==identity then return end_,nil end
  end
  local data=canon.object({identity=identity,monotonic_start=canon.float(mono_),monotonic_until=canon.float(mono_+until_-wall_)})
  local wok=pcall(ctl.write_json,env.run,path,canon.object({data=data,sha256=canon.digest(data)}))
  if not wok then return 0,'LEASE-STORAGE-FAILED' end
  return mono_+until_-wall_,nil
end

function M.transaction_expired(env,value,wall_,mono_)
  wall_=wall_ or wall(env);mono_=mono_ or mono(env)
  local md=value.monotonic_deadline
  return wall_>=num(value.deadline) or (not isnone(md) and mono_>=num(md))
end

------------------------------------------------------------------------------------------------------
-- diagnostics files (no command text, no stderr: codes and stages only)
------------------------------------------------------------------------------------------------------
function M.apply_progress(env,tx,stage)
  if not ctl.hex(tx,32) or not M.APPLY_STAGES[stage] then return end
  pcall(ctl.write_json,env.run,M.paths(env).progress,canon.object({tx=tx,stage=stage,time=fwall(env)}))
end
function M.record_attempt_failure(env,tx,stage,err,started)
  local elapsed=mono(env)-started
  local result=canon.object({tx=tx,stage=stage,code=code_of(err),error_type=is_refused(err) and 'Refused' or 'LuaError',
    time=fwall(env),elapsed_ms=canon.float(math.floor(math.max(0,elapsed)*10000+0.5)/10),error_at=canon.array({})})
  local ok,progress=pcall(ctl.read_json,env.run,M.paths(env).progress,canon.object({}))
  if ok and canon.is_object(progress) and progress.tx==tx and M.APPLY_STAGES[progress.stage] then
    local t=num(progress.time)
    if t and finite(t) and 0<=t and t<=num(result.time)+5 then result.worker_stage=progress.stage;result.worker_stage_time=progress.time end
  end
  pcall(ctl.write_json,env.run,M.paths(env).attempt_result,result)
  return result
end
function M.manual_stamp(env,name,request_id)
  pcall(function()
    local path=M.paths(env).timing
    local row=ctl.read_json(env.run,path,canon.object({}))
    if request_id~=nil and (not canon.is_object(row) or row.request_id~=request_id) then row=canon.object({request_id=request_id,stages=canon.array({})}) end
    if not canon.is_object(row) or not canon.is_array(row.stages) or #row.stages>=32 then return end
    row.stages[#row.stages+1]=canon.array({name,canon.float(math.floor(wall(env)*1000+0.5)/1000)})
    ctl.write_json(env.run,path,row)
  end)
end

------------------------------------------------------------------------------------------------------
-- pair event fields / publish
------------------------------------------------------------------------------------------------------
function M.transition_kind(source,target)
  local sp=getd(source,'protocol',nil) or string.match(source.id,'^([^:]*)')
  local tp=getd(target,'protocol',nil) or string.match(target.id,'^([^:]*)')
  if sp~=tp then return 'protocol' end
  if getd(source,'vendor_tunnel_id',nil)~=getd(target,'vendor_tunnel_id',nil) then return 'channel' end
  return 'server'
end

function M.pair_event_fields(value,opts)
  opts=opts or {}
  local policy=require('pair').policy
  local context=policy.metadata(value)
  if context==nil then return {} end
  local before,after
  if opts.restoring then
    before=getd(value,'restore_before_order',value.after)
    after=opts.restore_order or getd(value,'restored_order',getd(value,'restore_target_order',context.primary_order))
  else before,after=value.before,value.after end
  local destination=opts.outcome=='refused' and context.destination_role or policy.role(context,after)
  local result={before_policy_role=policy.role(context,before),destination_role=destination,destination_profile_id=value[destination],
    before_order=copy_list(before),after_order=copy_list(after),session_order=copy_list(context.session_order),
    route_changed=(not same_list(before,after)) and opts.outcome~='refused',transition_completed=opts.completed==true,
    activation_reapply=value.activation_reapply==true and not opts.restoring,transition_metadata_present=true}
  local verified=opts.restoring and value.restore_before_verified or value.kernel_before_verified
  if verified==true then
    local origin=policy.role(context,before)
    result.from_role=origin;result.from_profile_id=value[origin]
    local profiles=getd(value,'vendor_profiles',canon.object({}))
    if origin~=destination and not isnone(profiles[origin]) and not isnone(profiles[destination]) then
      result.transition_kind=M.transition_kind(profiles[origin],profiles[destination])
    end
  end
  if opts.restoring and not isnone(value.restored_order) then result.restored_order=copy_list(value.restored_order) end
  if opts.outcome~=nil then result.transition_outcome=opts.outcome end
  return result
end

-- dict(a,**b): a shallow merge as a canon object
function M.merge(...)
  local out=canon.object({})
  for _,t in ipairs({...}) do if t then for k,v in pairs(t) do out[k]=v end end end
  return out
end
local merge=M.merge

-- native_switch.publish(value): history record first, then native-status.json; HISTORY-001 blocks the status.
function M.publish(env,value)
  value=merge(value);value.time=fwall(env)
  local now=num(value.time)
  if getd(value,'proof_scope',M.PROOF_SCOPE)=='router-probed-ipv4' or value.mode=='continuous-pair' then
    value.mode='continuous-pair';value.transition_metadata_present=true
    if value.route_changed==nil then value.route_changed=false end
    local kernel=value.kernel_proof;value.kernel_proof=nil
    if env.deps and env.deps.from_kernel then
      value.channel_path=env.deps.from_kernel(kernel,value.source,value.target,now)
      local transitioning={BLOCKED=true,ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true}
      if transitioning[value.state] or (not isnone(value.blockers) and #value.blockers>0) then
        value.channel_path=env.deps.from_kernel(NULL,value.source,value.target,now)
        value.channel_path.transitioning=value.state=='ARMED' or value.state=='APPLYING' or value.state=='WAIT-CLIENT' or value.state=='RESTORING'
      end
      if not value.channel_path.confirmed then
        value.kernel_policy_verified=false
        if value.kernel_policy_verified~=true then value.readiness_verified=false end
      end
    end
  end
  value.latency=nil;value.website_response=nil
  local history=require('history')
  local role,identifier=history.transition_destination(value)
  if identifier and env.deps and env.deps.capture_latency then
    pcall(function()
      local current=M.journal_read(env)
      if current.source==value.source and current.target==value.target then
        local snapshot=ctl.read_json_safe(env.run,M.paths(env).status,canon.object({}))
        local binding=getd(getd(current,'vendor_profiles',canon.object({})),role,nil)
        local latency=env.deps.capture_latency(value,snapshot,binding,now)
        if latency~=nil then value.latency=latency end
        if env.deps.capture_website then
          local response=env.deps.capture_website(value,snapshot,binding,now)
          if response~=nil then value.website_response=response end
        end
      end
    end)
  end
  for k,v in pairs(ctl.action_context(env,now)) do value[k]=v end
  if value.reason=='PAIR-STOPPED' and value.control_action=='stop' and value.transition_source==nil then
    value.transition_source=getd(value,'control_source','unknown')
  end
  if value.manual==true or value.reason=='OPERATOR-MANUAL' or value.reason=='OPERATOR-RETURN' then
    if value.transition_source==nil then value.transition_source=ctl.manual_action_source(env,value,now) end
  elseif value.trial==true or value.reason=='OPERATOR-TRIAL' or value.reason=='TRIAL-PASSED' then
    if value.transition_source==nil then value.transition_source='test' end
  elseif value.reason=='SOURCE-FAILED' or value.reason=='PRIMARY-STABLY-RECOVERED' or value.reason=='RESERVE-FAILED-PRIMARY-VERIFIED' then
    local tested=value.reason=='SOURCE-FAILED' and value.source or value.target
    local testing=env.deps and env.deps.testing_profile and not isnone(tested) and env.deps.testing_profile(tested)
    if value.transition_source==nil then value.transition_source=testing and 'test' or 'automatic' end
  end
  if value.proof_scope==nil then value.proof_scope=M.PROOF_SCOPE end
  if value.proof_scope=='router-probed-ipv4' then
    if value.mode==nil then value.mode='continuous-pair' end
    value.external_lan_verified=false
  end
  local ok,err=pcall(function() history.new(env,env.persist,10000):record(value) end)
  if not ok then
    ctl.write_json(env.run,M.paths(env).state,canon.object({state='BLOCKED',blockers=canon.array({'HISTORY-001'})}))
    refuse('HISTORY-001')
  end
  ctl.write_json(env.run,M.paths(env).state,value)
end

------------------------------------------------------------------------------------------------------
-- selection proofs
------------------------------------------------------------------------------------------------------
function M.assert_selection(env,selection)
  local blockers,current=env.backend.diagnostic()
  if #blockers>0 then refuse(blockers[1]) end
  local identity=selection.vendor_identity
  if not ctl.hex(identity,64) or not current or current.vendor_identity~=identity
     or getd(current,'proof_scope','external-lan')~=getd(selection,'proof_scope','external-lan')
     or current.hash~=selection.hash or current.source.id~=selection.source.id or current.target.id~=selection.target.id then
    refuse('PROFILE-IDENTITY-CHANGED')
  end
  return current
end

local function vendor_profiles_of(selection)
  local out=canon.object({})
  for _,role in ipairs({'source','target'}) do
    local row=canon.object({})
    for _,key in ipairs({'id','protocol','interface','vendor_tunnel_id','vendor_generation'}) do
      local v=selection[role][key];row[key]=v==nil and NULL or v
    end
    out[role]=row
  end
  return out
end

------------------------------------------------------------------------------------------------------
-- the APPLYING steps (native_switch.child, in-process)
------------------------------------------------------------------------------------------------------
function M.apply_steps(env,value,selection,tx)
  local revision=value.control_revision
  if M.transaction_expired(env,value) then refuse('TRANSACTION-EXPIRED') end
  M.require_control_revision(env,revision)
  local blockers,current=env.backend.diagnostic()
  if #blockers>0 then refuse(blockers[1]) end
  if not current or isnone(value.vendor_identity) or current.vendor_identity~=value.vendor_identity then refuse('PROFILE-IDENTITY-CHANGED') end
  if canon.encode(getd(current,'process_bindings',NULL))~=canon.encode(getd(value,'process_bindings',NULL)) then refuse('POLICY-IDENTITY-CHANGED') end
  M.bind_policy_context(env,value)
  if not order_is(env,value.before,value.hash) then refuse('POLICY-GENERATION-CHANGED') end
  local pair=not isnone(value.pair_transition)
  if pair then
    local proof=env.backend.attest_policy(current)
    if not (proof.verified==true or proof.repairable_missing==true) or proof.kernel_fingerprint~=value.kernel_before_fingerprint then
      refuse('KERNEL-POLICY-UNVERIFIED')
    end
    if env.deps and env.deps.rtp_boot then env.deps.rtp_boot.prepare(revision) end
  end
  M.require_control_revision(env,revision)
  env.backend.guard(nil,revision)
  local function before_write()
    M.require_control_revision(env,revision)
    M.assert_selection(env,current)
    M.require_control_revision(env,revision)
    if M.transaction_expired(env,value) then refuse('TRANSACTION-EXPIRED') end
    if pair and env.backend.kernel_fingerprint()~=value.kernel_before_fingerprint then refuse('KERNEL-POLICY-UNVERIFIED') end
  end
  -- write(kind): kind is 'uci' (reorder/commit/sync), 'kernel' (iptables-restore or rtp2) - the backend runs the
  -- actual command inside run.fenced(revision).
  local function write_command(kind,fn,detail)
    before_write()
    if kind=='rtp' then
      local md=value.monotonic_deadline
      if isnone(md) or num(md)-mono(env)<M.RTP_DISPATCH_RESERVE then refuse('TRANSACTION-EXPIRED') end
      if env.deps and env.deps.rtp_boot then env.deps.rtp_boot.ready() end
    end
    if pair then
      if kind=='rtp' or kind=='kernel' then value.rtp_dispatched=true else value.forward_policy_touched=true end
      M.journal_write(env,value)
    end
    if kind=='rtp' then M.apply_progress(env,tx,'rtp-dispatch') end
    local result=env.run.fenced(revision,fn)
    -- a command dispatched under the lock is awaited outside it (Python forward_dispatch)
    if type(result)=='function' then result=result() end
    if kind=='rtp' then M.apply_progress(env,tx,'rtp-returned') end
    return result
  end
  M.apply_progress(env,tx,'reorder')
  env.backend.reorder(value.after,nil,write_command)
  M.apply_progress(env,tx,'apply')
  env.backend.apply(write_command)
  if pair then
    M.apply_progress(env,tx,'verify-diagnostic')
    blockers,current=env.backend.diagnostic()
    local waited_until=mono(env)+M.VERIFY_VENDOR_WAIT
    local function transient(list)
      if #list==0 then return false end
      for _,b in ipairs(list) do if not M.VERIFY_TRANSIENT[b] then return false end end
      return true
    end
    while transient(blockers) and mono(env)<waited_until do env.sleep(2);blockers,current=env.backend.diagnostic() end
    if #blockers>0 then refuse(blockers[1]) end
    M.apply_progress(env,tx,'verify-kernel')
    local proof=env.backend.attest_policy(current)
    if proof.verified~=true or proof.role~=value.pair_transition.destination_role then refuse('KERNEL-POLICY-UNVERIFIED') end
  end
  M.apply_progress(env,tx,'done')
end

------------------------------------------------------------------------------------------------------
-- attempt()
------------------------------------------------------------------------------------------------------
-- opts: probe_evidence, control_revision, manual_request_id, request_source, pair_destination,
-- pair_session_order, on_dispatch, pair_reapply, pair_return
function M.attempt(env,selection,until_,trial,opts)
  opts=opts or {}
  local policy=require('pair').policy
  local rollback=require('rollback')
  M.PROOF_SCOPE=getd(selection,'proof_scope','external-lan')
  local scope=M.PROOF_SCOPE
  local manual_request_id,pair_destination,pair_session_order=opts.manual_request_id,opts.pair_destination,opts.pair_session_order
  local pair_reapply,pair_return=opts.pair_reapply==true,opts.pair_return==true
  if manual_request_id~=nil and (trial or not ctl.hex(manual_request_id,32)) then refuse('MANUAL-REQUEST-INVALID') end
  if pair_reapply and (manual_request_id~=nil or pair_destination==nil) then refuse('MANUAL-REQUEST-INVALID') end
  if pair_return and (manual_request_id~=nil or pair_destination~='source' or pair_reapply) then refuse('MANUAL-REQUEST-INVALID') end
  if pair_destination~=nil and ((manual_request_id==nil and not pair_reapply and not pair_return)
     or (pair_destination~='source' and pair_destination~='target') or scope~='router-probed-ipv4') then refuse('MANUAL-REQUEST-INVALID') end
  if pair_session_order~=nil and (trial or scope~='router-probed-ipv4') then refuse('MANUAL-REQUEST-INVALID') end
  local control_revision=opts.control_revision or ctl.current_revision(env)
  M.bind_policy_context(env,selection)
  M.require_control_revision(env,control_revision)
  M.assert_selection(env,selection)
  local transition_source=manual_request_id~=nil and ctl.normalize_request_source(opts.request_source) or (trial and 'test' or 'automatic')
  local cause=trial and 'OPERATOR-TRIAL' or (opts.probe_evidence and opts.probe_evidence.source_streak_met==true and 'SOURCE-FAILED' or 'SOURCE-HEALTH-UNKNOWN')
  if manual_request_id~=nil then cause='OPERATOR-MANUAL' end
  if pair_reapply then cause='KERNEL-POLICY-UNVERIFIED' end
  if pair_return then cause='PRIMARY-STABLY-RECOVERED' end

  local before=copy_list(selection.order);local after=copy_list(before)
  local i,j=index_of(after,selection.source_rule),index_of(after,selection.target_rule)
  if not i or not j then refuse('POLICY-IDENTITY-CHANGED') end
  if pair_destination==nil and ((i>j and selection.direction=='first') or (i<j and selection.direction=='last')) then refuse('SOURCE-ORDER-MISMATCH') end
  local pair_context,kernel_before=nil,nil
  local destination=pair_destination or 'target'
  if pair_session_order~=nil then
    local ok,ctx,desired=pcall(function()
      local ctx=policy.transition(selection,pair_session_order,destination)
      return ctx,policy.desired_order(ctx,before,destination)
    end)
    if not ok then refuse('POLICY-IDENTITY-CHANGED') end
    pair_context=ctx;after=copy_list(desired)
  elseif pair_destination~=nil then refuse('MANUAL-REQUEST-INVALID') end
  if pair_reapply and not same_list(after,before) then refuse('POLICY-IDENTITY-CHANGED') end
  if pair_context~=nil then
    kernel_before=env.backend.attest_policy(selection)
    local fingerprint=kernel_before.kernel_fingerprint
    if not (kernel_before.verified==true or kernel_before.repairable_missing==true) or not ctl.hex(fingerprint,64) then refuse('KERNEL-POLICY-UNVERIFIED') end
    if pair_return and (kernel_before.verified~=true or kernel_before.role~='target'
                        or env.backend.recovery_ready(selection.source.id,env.backend.policy().settings)~=true) then refuse('SOURCE-NOT-HEALTHY') end
    if env.deps and env.deps.rtp_boot then env.deps.rtp_boot.assess();env.deps.rtp_boot.prepare(control_revision) end
  end
  if trial then
    M.require_control_revision(env,control_revision)
    local baseline=env.backend.policy().settings.native_baseline_exit
    if isnone(baseline) or baseline=='' or env.backend.trace(selection.source)~=baseline then refuse('LAN-BASELINE-NOT-SOURCE') end
    M.require_control_revision(env,control_revision)
    if env.backend.trace(selection.target)==baseline then refuse('RESERVE-EXIT-NOT-DISTINCT') end
    M.require_control_revision(env,control_revision)
  end
  M.assert_selection(env,selection)
  M.require_control_revision(env,control_revision)
  if pair_context==nil then after[i],after[j]=after[j],after[i] end
  local tx=ctl.uuid_hex()
  local wall_,mono_=wall(env),mono(env)
  local settings=env.backend.policy().settings
  local lease_end,lease_error=M.monotonic_lease(env,settings,until_,wall_,mono_)
  if lease_error then refuse(lease_error) end
  local value=canon.object({tx=tx,phase='ARMED',before=before,after=after,hash=selection.hash,
    source=selection.source.id,target=selection.target.id,
    deadline=canon.float(math.min(until_,wall_+M.TRANSACTION_SECONDS)),monotonic_deadline=canon.float(math.min(lease_end,mono_+M.TRANSACTION_SECONDS)),
    lease_monotonic_until=canon.float(lease_end),trial=trial and true or false,trial_nonce=getd(settings,'native_trial',NULL),
    pid=NULL,started=fwall(env),vendor_identity=selection.vendor_identity,process_bindings=getd(selection,'process_bindings',NULL),
    proof_scope=scope,control_revision=control_revision,vendor_profiles=vendor_profiles_of(selection)})
  if manual_request_id~=nil then value.manual_request_id=manual_request_id end
  if pair_context~=nil then
    value.pair_transition=pair_context
    value.kernel_before_fingerprint=kernel_before.kernel_fingerprint;value.kernel_before_verified=kernel_before.verified==true
    value.forward_policy_touched=false;value.rtp_dispatched=false
  end
  value.transition_source=transition_source
  if pair_reapply then value.activation_reapply=true end

  local function publish_transition(row)
    if pair_context~=nil then
      row=merge(M.pair_event_fields(value),row)
      if row.from_role==nil then row.transition_kind=nil end
    end
    row=merge(row);row.transition_source=transition_source
    if pair_context~=nil then row.destination_role=destination;row.destination_profile_id=selection[destination].id end
    M.publish(env,row)
  end
  local kernel=nil
  local function publish_committed(row)
    if pair_context~=nil then
      row=merge(M.pair_event_fields(value,{completed=true,outcome=pair_reapply and 'policy-verified' or 'committed'}),row)
      row.readiness_verified=true;row.kernel_policy_verified=true;row.kernel_proof=kernel
    end
    local ok=pcall(publish_transition,row)
    if not ok then ctl.write_json(env.run,M.paths(env).state,merge(row,{time=fwall(env),history_error='HISTORY-001'})) end
  end
  local kind=M.transition_kind(selection.source,selection.target)
  publish_transition({state='ARMED',source=value.source,target=value.target,trial=trial and true or false,reason=cause,
    phase_evidence=getd(value,'phase_evidence',canon.array({})),probe_evidence=opts.probe_evidence or NULL,transition_kind=kind})
  M.require_control_revision(env,control_revision)
  M.journal_write(env,value)
  -- The fenced dispatch of Python (Popen of the apply child under the lock) is here the charge of the budget.
  local dok,derr=pcall(function()
    M.require_control_revision(env,control_revision)
    env.run.lock(function()
      M.require_control_revision(env,control_revision)
      if opts.on_dispatch then opts.on_dispatch() end
    end,env.runtime)
  end)
  if not dok then
    value.failure_detail=M.record_attempt_failure(env,tx,'dispatch',derr,mono_)
    value.phase='ROLLED-BACK';value.reason='FAILED-BEFORE-APPLY';value.finished=fwall(env)
    if pair_context~=nil then value.restored_order=copy_list(before) end
    M.journal_write(env,value)
    if pair_context~=nil then
      value.restore_before_order=copy_list(before);value.restore_before_verified=false
      publish_transition(merge(M.pair_event_fields(value,{completed=true,outcome='refused',restoring=true}),
        {state='ROLLED-BACK',reason='TRANSACTION-FAILED',source=value.source,target=value.target,blockers=canon.array({code_of(derr)})}))
    end
    error(derr,0)
  end
  value.phase='APPLYING'
  local released,stage=false,'arming'
  local ok,err=pcall(function()
    publish_transition({state='APPLYING',source=value.source,target=value.target,trial=trial and true or false,reason=cause,
      phase_evidence=getd(value,'phase_evidence',canon.array({})),probe_evidence=opts.probe_evidence or NULL,transition_kind=kind})
    M.journal_write(env,value);released=true
    stage='worker'
    M.apply_steps(env,value,selection,tx)
    stage='post-apply'
    if not order_is(env,after,selection.hash) then refuse('POLICY-CHANGED-DURING-APPLY') end
    if pair_context~=nil then
      kernel=env.backend.attest_policy(merge(selection,{order=copy_list(after)}))
      if kernel.verified~=true or kernel.role~=destination then refuse('KERNEL-POLICY-UNVERIFIED') end
    end
    if pair_reapply then
      M.assert_selection(env,selection);M.require_control_revision(env,control_revision)
      env.backend.guard(env.backend.devices(),control_revision)
      env.run.lock(function()
        M.require_control_revision(env,control_revision)
        value.phase='ROLLED-BACK';value.restored_order=copy_list(before);value.kernel_confirmed=fwall(env)
        value.finished=fwall(env);value.reason='KERNEL-POLICY-VERIFIED'
        M.journal_write(env,value)
      end,env.runtime)
      publish_committed({state='OBSERVING',source=value.source,target=value.target,reason='KERNEL-POLICY-VERIFIED',policy_reapplied=true,proof_scope=scope})
      return
    end
    stage='trace'
    local target_exit=env.backend.trace(selection[destination])
    M.assert_selection(env,selection)
    M.require_control_revision(env,control_revision)
    env.backend.guard(env.backend.devices(),control_revision)
    value.phase='WAIT-CLIENT';value.expected_exit=target_exit;M.journal_write(env,value)
    publish_transition({state='WAIT-CLIENT',tx=tx,expected_exit=target_exit,deadline=value.deadline,source=value.source,target=value.target,
      trial=trial and true or false,phase_evidence=getd(value,'phase_evidence',canon.array({})),
      requires='LAN client DNS/HTTPS and exit IP confirmation; no confirmation means rollback'})
    stage='confirmation'
    while not M.transaction_expired(env,value) and not env.stop() do
      M.require_control_revision(env,control_revision)
      local stopped=ctl.read_json(env.run,M.paths(env).stop,canon.object({}))
      if (num(stopped.requested) or 0)>=num(value.started) then refuse('CLIENT-STOP') end
      local confirmation=ctl.read_json(env.run,M.paths(env).confirm,canon.object({}))
      if scope=='router-probed-ipv4' then
        -- keep=true: the trace() right below may use this very measurement (backend.probe, within 2 s)
        local measured=env.backend.probe(selection[destination],true)
        M.require_control_revision(env,control_revision)
        if isnone(measured.code) and measured.dns_ok==true and (num(measured.https_success) or 0)>=2 and env.backend.trace(selection[destination])==target_exit then
          confirmation=canon.object({tx=tx,exit_ipv4=target_exit,dns_ok=true,https_ok=true,time=fwall(env),proof_scope=scope})
        end
      end
      local ctime=num(confirmation.time) or 0
      local now=wall(env)
      if confirmation.tx==tx and confirmation.exit_ipv4==target_exit and getd(confirmation,'proof_scope','external-lan')==scope
         and confirmation.dns_ok==true and confirmation.https_ok==true and num(value.started)<=ctime and ctime<=now and now-ctime<=30 then
        if not order_is(env,after,selection.hash) then refuse('EXTERNAL-POLICY-CHANGE') end
        if pair_context~=nil then
          kernel=env.backend.attest_policy(merge(selection,{order=copy_list(after)}))
          if kernel.verified~=true or kernel.role~=destination then refuse('KERNEL-POLICY-UNVERIFIED') end
        end
        if env.backend.trace(selection[destination])~=target_exit then refuse('EXIT-CHANGED') end
        M.assert_selection(env,selection)
        M.require_control_revision(env,control_revision)
        if not order_is(env,after,selection.hash) then refuse('EXTERNAL-POLICY-CHANGE') end
        M.require_control_revision(env,control_revision)
        value.phase='COMMITTED';value.confirmed=fwall(env);M.journal_write(env,value)
        if env.deps and env.deps.record_switch_time then pcall(env.deps.record_switch_time,env,num(value.confirmed)-num(value.started)) end
        if manual_request_id~=nil then
          env.run.lock(function()
            M.require_control_revision(env,control_revision)
            value.phase='HELD-ON-RESERVE';value.reason='OPERATOR-MANUAL';value.reserve_healthy=true;M.journal_write(env,value)
          end,env.runtime)
          publish_committed({state=destination=='source' and 'OBSERVING' or 'STOPPED-ON-RESERVE',reason='OPERATOR-MANUAL',source=value.source,target=value.target,
            original_restored=false,reserve_healthy=true,trial=false,tx=tx})
          return
        end
        if trial and not M.finish_committed(env,value,'TRIAL-PASSED') then return end
        M.require_control_revision(env,control_revision)
        if not pair_return then
          pcall(ctl.write_json,env.run,M.paths(env).cert,canon.object({hash=selection.hash,source=selection.source.id,target=selection.target.id,
            direction=selection.direction,settings_hash=getd(selection,'settings_hash',NULL),vendor_identity=selection.vendor_identity,
            proof_scope=scope,time=fwall(env),['until']=canon.float(until_)}))
        end
        publish_committed({state=trial and 'ARMED' or ((pair_context~=nil and destination=='source') and 'OBSERVING' or 'COMMITTED'),tx=tx,
          source=value.source,target=value.target,['until']=canon.float(until_),trial=trial and true or false,
          phase_evidence=getd(value,'phase_evidence',canon.array({})),transition_kind=kind,
          reason=trial and 'TRIAL-PASSED' or 'CLIENT-CONFIRMED',guard='VPN-only; IPv6 forwarded traffic blocked'})
        return
      end
      env.sleep(1)
    end
    refuse('CLIENT-CONFIRMATION-TIMEOUT')
  end)
  if ok then return end
  local failure_code=code_of(err)
  local failure_detail=M.record_attempt_failure(env,tx,stage,err,mono_)
  if pair_context~=nil then
    local sok,saved=pcall(M.journal_read,env)
    if sok and saved.tx==tx then value=saved end
    value.failure_code=failure_code;value.failure_detail=failure_detail;M.journal_write(env,value)
  end
  if not released and order_is(env,before,selection.hash) then
    value.phase='ROLLED-BACK';value.reason='FAILED-BEFORE-APPLY';M.journal_write(env,value)
  else
    rollback.rollback_counted(env,value,'TRANSACTION-FAILED')
  end
  if pair_context==nil then
    publish_transition({state='ROLLED-BACK',reason='TRANSACTION-FAILED',source=value.source,target=value.target,trial=trial and true or false,
      phase_evidence=getd(value,'phase_evidence',canon.array({})),blockers=canon.array({failure_code})})
  end
  error(err,0)
end

------------------------------------------------------------------------------------------------------
-- committed / return handling
------------------------------------------------------------------------------------------------------
function M.source_ready(env,value,settings,reason)
  if reason~='TRIAL-PASSED' then return env.backend.recovery_ready(value.source,settings)==true end
  for index=1,M.RETURN_CHECKS do
    if env.backend.health(value.source)==true then return true end
    if index<M.RETURN_CHECKS then env.sleep(M.RETURN_PAUSE) end
  end
  return false
end

function M.operator_return(env,value,reason,control_revision)
  reason=reason or 'OPERATOR-RETURN'
  if value.phase~='HELD-ON-RESERVE' and value.phase~='COMMITTED' then return 'RETURN-NOT-APPLICABLE' end
  if env.backend.health(value.source)~=true then return 'SOURCE-NOT-HEALTHY' end
  if control_revision~=nil then M.require_control_revision(env,control_revision) end
  local context=require('pair').policy.metadata(value)
  local rollback=require('rollback')
  if context==nil then rollback.rollback(env,value,reason) else rollback.rollback(env,value,reason,context.primary_order) end
  return nil
end

function M.handle_return(env,value,request,last_time,control_revision)
  local stamp=canon.is_object(request) and num(request.time) or nil
  if not stamp or not finite(stamp) or stamp<=0 then return false,last_time end
  if stamp==last_time then return false,last_time end
  local now=wall(env)
  if type(last_time)~='number' or not finite(last_time) or not (0<=last_time and last_time<=now) then last_time=0 end
  if stamp<=last_time then return false,last_time end
  local code
  if type(request.tx)~='string' or request.tx=='' or request.tx~=value.tx then code='RETURN-TRANSACTION-MISMATCH'
  elseif not ((num(value.started) or 0)<=stamp and stamp<=now) or now-stamp>60 then code='RETURN-REQUEST-EXPIRED'
  else
    local ok,result=pcall(M.operator_return,env,value,nil,control_revision)
    if ok then code=result else if is_refused(result) then code=result.code else error(result,0) end end
  end
  if code==nil then
    local ok=pcall(env.backend.unguard)
    if not ok then code='GUARD-RELEASE-UNCONFIRMED' end
    if code==nil then
      env.backend.clear_native_options()
      pcall(M.publish,env,{state='STOPPED',reason='OPERATOR-RETURN',original_restored=order_is(env,value.before,value.hash),
        source=value.source,target=value.target,trial=getd(value,'trial',false)})
    end
  end
  ctl.write_json(env.run,M.paths(env).return_result,canon.object({request=canon.float(stamp),ok=code==nil,code=code or 'RETURNED',time=fwall(env)}))
  return true,stamp
end

function M.finish_committed(env,value,reason,restore_order)
  local policy=require('pair').policy
  local rollback=require('rollback')
  M.bind_policy_context(env,value)
  local order,fingerprint=env.backend.order()
  if fingerprint~=value.hash or not in_orders(order,value.before,value.after,value.restore_target_order,value.restored_order) then
    rollback.abandon(env,value,'EXTERNAL-POLICY-CHANGE')
    refuse('EXTERNAL-POLICY-CHANGE-RELEASED')
  end
  local settings=env.backend.policy().settings
  local recovery=require('pair').recovery_normalized(settings)
  local context=policy.metadata(value)
  if context~=nil then
    local desired=restore_order or context.primary_order
    if not in_orders(desired,value.before,context.primary_order,context.session_order) then refuse('POLICY-IDENTITY-CHANGED') end
    local wanted=policy.role(context,desired)
    local ready
    if wanted=='source' then ready=M.source_ready(env,value,settings,reason) else ready=env.backend.recovery_ready(value[wanted],settings)==true end
    if not same_list(order,desired) and (not ready or (wanted=='source' and recovery.return_policy=='hold_reserve')) then
      env.backend.guard(env.backend.devices())
      value.phase='HELD-ON-RESERVE';value.reason=wanted=='source' and 'SOURCE-NOT-VERIFIED' or 'RESERVE-NOT-CONNECTED';value.finished=fwall(env)
      M.journal_write(env,value)
      return false
    end
    rollback.rollback(env,value,reason,desired)
    return true
  end
  if same_list(order,value.after) and (recovery.return_policy=='hold_reserve' or not M.source_ready(env,value,settings,reason)) then
    local healthy=env.backend.health(value.target)==true
    env.backend.guard(env.backend.devices())
    value.phase='HELD-ON-RESERVE';value.reason=recovery.return_policy=='hold_reserve' and 'OPERATOR-HOLD-RESERVE' or 'SOURCE-NOT-VERIFIED'
    value.finished=fwall(env);value.reserve_healthy=healthy
    M.journal_write(env,value)
    M.publish(env,{state='STOPPED-ON-RESERVE',reason=value.reason,source=value.source,target=value.target,expected_exit=getd(value,'expected_exit',NULL),
      reserve_healthy=healthy,original_restored=false,trial=getd(value,'trial',false)})
    return false
  end
  value.phase='RESTORING';M.journal_write(env,value)
  rollback.rollback(env,value,reason)
  return true
end

-- committed_recovery_decision(backend,journal,settings,samples,now,status)
function M.committed_recovery_decision(env,value,settings,samples,now,status)
  local pair=require('pair')
  local recovery=pair.recovery_normalized(settings)
  local age=pair.valid_for(settings)
  local selection_settings=merge(settings)
  for _,role in ipairs({'source','target'}) do
    if isnone(selection_settings['plan_'..role]) or selection_settings['plan_'..role]=='' then selection_settings['plan_'..role]=value[role] end
  end
  -- A primary the vendor keeps rebuilding does not make the held reserve's identity unknown.
  local resolved=env.deps.resolve_pair(status,selection_settings,now,age,pair.settle_for(settings),require('diagnosis').flap_window(pair.settle_for(settings)))
  local proofs=getd(value,'vendor_profiles',canon.object({}))
  local target=resolved.target
  local expected=canon.is_object(proofs) and getd(proofs,'target',nil) or nil
  if resolved.coordination.state~='READY' or isnone(target) or target.id~=value.target
     or (expected~=nil and canon.encode(require('pair').profile_identity(env,target) or NULL)~=canon.encode(expected)) then
    return {action='HOLD',reason='RESERVE-IDENTITY-UNKNOWN',reserve_healthy=NULL}
  end
  local failed=pair.streak(samples,target.id,recovery.failures,now,age,false,target)
  local fault_test=failed and env.deps.testing_profile and env.deps.testing_profile(value.target) or false
  if recovery.return_policy=='healthy_primary' or fault_test then
    local dwell=now-(num(value.confirmed) or num(value.started) or now)
    if (failed or dwell>=recovery.min_dwell) and env.backend.recovery_ready(value.source,settings)==true then
      return {action='RESTORE-PRIMARY',reason=failed and 'RESERVE-FAILED-PRIMARY-VERIFIED' or 'PRIMARY-STABLY-RECOVERED'}
    end
  end
  if failed then
    local health=env.backend.health(value.target)
    if health==false then return {action='HOLD',reason='RESERVE-FAILED',reserve_healthy=false} end
    if health==nil then return {action='HOLD',reason='RESERVE-HEALTH-UNKNOWN',reserve_healthy=NULL} end
  end
  return {action='OBSERVE',reason='CLIENT-CONFIRMED'}
end

return M
