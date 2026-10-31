-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- auto.lua: the hv-auto supervisor (native_switch.serve) in Lua on uloop (2.0.0-lua-alpha2).
--
--   lua auto.lua daemon          procd entry (homensai_vpn.main.lua_auto='1'): sys.lua + backend.lua (the
--                                native_switch.Linux port), holds native.lock, uloop (blocking driver without it)
--   lua auto.lua check           read-only: backend results + timings + memory as one JSON line
--
-- Start: rotate the control revision, read the journal (unreadable -> one timed LAN block, then give_up),
-- fence pair intent, then recover: RELEASE-PENDING -> abandon; ARMED/APPLYING/WAIT-CLIENT/RESTORING ->
-- rollback_counted (ROLLBACK_FAILURE_LIMIT -> give_up); COMMITTED -> guard (manual + confirmed ->
-- HELD-ON-RESERVE); then manual.recover_pending and pair.recover. The loop body is iteration(): one Python
-- loop pass that returns the pause until the next one (the Python sleep); the uloop timer reschedules it and a
-- QUEUED owner click (ubus notify or the pair-manual-control.json poll) ends the pause at once (nap()).
-- Stop: SIGTERM ends uloop.run() after the running pass; then finish_committed('SERVICE-STOPPED') + pair.recover.
local here=(arg and arg[0] and string.match(arg[0],'^(.*)/[^/]*$'))
if here then package.path=here..'/?.lua;'..package.path end
local canon=require('canon')
local ctl=require('auto_control')
local T=require('transaction')
local R=require('rollback')
local pair=require('pair')
local manual=require('manual')

local M={}
local NULL=canon.null
local isnone,num=ctl.isnone,ctl.num
local is_refused=ctl.is_refused
local order_is,getd,merge=T.order_is,T.getd,T.merge

local function fwall(env) return canon.float(env.run.wall()) end
local function restored_order_is(env,active)
  return active.phase=='ROLLED-BACK' and order_is(env,getd(active,'restored_order',active.before),active.hash)
end

-- serve() up to the loop: returns 'stopped' when the daemon must end (give_up / CONTROL-REVISION-STALE),
-- 'ready' otherwise.
function M.recover(env)
  local rok=pcall(ctl.current_revision,env,true)
  local revision_error=not rok
  local jok,value=pcall(T.journal_read,env)
  local paths=T.paths(env)
  if not jok then
    if not is_refused(value) then error(value,0) end
    local aok,alarm=pcall(ctl.read_json,env.run,paths.alarm,nil)
    local first=aok and alarm==nil
    if first then
      pcall(env.backend.guard)
      pcall(ctl.write_json,env.run,paths.alarm,canon.object({first_block=fwall(env),code='JOURNAL-INTEGRITY-FAILED'}))
    end
    R.give_up(env,canon.object({}),'JOURNAL-INTEGRITY-FAILED')
    return 'stopped'
  end
  pcall(env.run.fs.remove or os.remove,paths.alarm)
  T.bind_policy_context(env,value)
  T.PROOF_SCOPE=getd(value,'proof_scope','external-lan')
  if not T.SCOPES[T.PROOF_SCOPE] then ctl.refuse('JOURNAL-INTEGRITY-FAILED') end
  pair.fence_recovery(env)
  if value.phase=='RELEASE-PENDING' then R.abandon(env,value,getd(value,'reason','EXTERNAL-POLICY-CHANGE')) end
  local phase=value.phase
  if phase=='ARMED' or phase=='APPLYING' or phase=='WAIT-CLIENT' or phase=='RESTORING' then
    -- No apply child exists in the Lua line (the steps ran in this process); a recorded pid is a Python child.
    if phase=='APPLYING' and not isnone(value.pid) and env.backend.kill_apply_child then env.backend.kill_apply_child(value.pid,value.tx) end
    local failures=num(getd(value,'rollback_failures',0)) or 0
    if failures>0 and value.rollback_package~=R.recovery_package(env) then
      value.rollback_failures=0;value.rollback_package=R.recovery_package(env);T.journal_write(env,value)
      failures=0
    end
    if failures>=T.ROLLBACK_FAILURE_LIMIT then R.give_up(env,value,'ROLLBACK-GIVEN-UP');return 'stopped' end
    local ok,err=pcall(R.rollback_counted,env,value,'SUPERVISOR-RECOVERY')
    if not ok then
      if (num(getd(value,'rollback_failures',0)) or 0)>=T.ROLLBACK_FAILURE_LIMIT then R.give_up(env,value,'ROLLBACK-GIVEN-UP');return 'stopped' end
      error(err,0)
    end
  elseif phase=='COMMITTED' then
    if not order_is(env,value.after,value.hash) then R.abandon(env,value,'EXTERNAL-POLICY-CHANGE')
    else
      env.backend.guard(env.backend.devices())
      if not isnone(value.manual_request_id) and not isnone(value.confirmed) then
        value.phase='HELD-ON-RESERVE';value.reason='OPERATOR-MANUAL';T.journal_write(env,value)
      end
    end
  end
  manual.recover_pending(env)
  pair.recover(env)
  if revision_error then
    pcall(ctl.stop_latch,env,getd(value,'trial_nonce',NULL))
    T.publish(env,{state='BLOCKED',blockers=canon.array({'CONTROL-REVISION-STALE'}),alarm='CONTROL-REVISION-STALE',original_restored=false})
    return 'stopped'
  end
  return 'ready'
end

-- One pass of the Python `while not STOP` loop. ctx keeps last_return/consumed/last_trial/last_attempt.
-- Returns the pause in seconds before the next pass ('nap' pauses are cut short by a QUEUED owner click).
-- a plain Lua error keeps the place it came from (the refusal tables pass through unchanged)
local function with_trace(e)
  if type(e)=='table' then return e end
  return debug.traceback(tostring(e),2)
end
M.with_trace=with_trace

function M.iteration(env,ctx)
  local paths=T.paths(env)
  local backend=env.backend
  local ok,err=xpcall(function()
    if backend.speed_gate and backend.speed_gate('auto') then return 1 end
    local decision_revision=ctl.current_revision(env)
    local progress_error=nil
    local pok,returned,attempts=pcall(function()
      return T.progress_read(env,paths.return_result,'return'),T.progress_read(env,paths.attempts,'attempts')
    end)
    if not pok then progress_error='NATIVE-PROGRESS-UNVERIFIED'
    else
      ctx.last_return=num(getd(returned,'request',0)) or 0;ctx.consumed=attempts
      ctx.last_trial=getd(attempts,'trial',nil);ctx.last_attempt=num(getd(attempts,'time',0)) or 0
    end
    local data=backend.policy();local settings=data.settings
    if pair.tick(env,settings,decision_revision) then
      local pending=T.journal_read(env)
      if T.RECOVERY_PHASES[pending.phase] then
        pair.fence_recovery(env)
        pair.publish_failure(env,'PAIR-RECOVERY-REQUIRED')
        return 'exit'
      end
      return 'nap'
    end
    local until_=T.deadline(settings.native_until)
    local scope=getd(settings,'native_proof_scope','external-lan')
    if not T.SCOPES[scope] then ctl.refuse('LAN-TRIAL-REQUIRED') end
    if scope=='router-probed-ipv4' and settings.pair_auto_mode~='router-probed-ipv4' then ctl.refuse('PAIR-MODE-NOT-CONFIGURED') end
    T.PROOF_SCOPE=scope
    local active=T.journal_read(env)
    if active.phase=='RELEASE-PENDING' then R.abandon(env,active,getd(active,'reason','EXTERNAL-POLICY-CHANGE'));return 2 end
    local stopped=ctl.read_json(env.run,paths.stop,canon.object({}))
    local enabled,stop_latched=ctl.effective_intent(settings,stopped,ctl.read_json(env.run,env.runtime..'/auto-control.json',canon.object({})),env.run.wall(),T.deadline)
    local lease_error,lease_end=nil,0
    if enabled or active.phase=='COMMITTED' then lease_end,lease_error=T.monotonic_lease(env,settings,until_) end
    if active.phase=='COMMITTED' then
      if isnone(active.lease_monotonic_until) or num(active.lease_monotonic_until)==0 then lease_error='LEGACY-LEASE-RECOVERY'
      else lease_end=math.min(lease_end,num(active.lease_monotonic_until)) end
    end
    local now=env.run.wall()
    local lease_expired=now>=until_ or (lease_end>0 and env.run.clock()>=lease_end) or (active.phase=='COMMITTED' and lease_error~=nil)
    local request=ctl.read_json(env.run,paths.return_request,canon.object({}))
    if canon.is_object(request) and next(request)~=nil then
      local handled,last=T.handle_return(env,active,request,ctx.last_return)
      ctx.last_return=last
      if handled then return 2 end
    end
    if active.phase=='HELD-ON-RESERVE' and (not enabled or stop_latched or settings.native_trial==active.trial_nonce) then
      if not order_is(env,active.after,active.hash) then R.abandon(env,active,'EXTERNAL-POLICY-CHANGE');return 5 end
      if isnone(active.manual_request_id) and pair.recovery_normalized(settings).return_policy=='healthy_primary' and backend.recovery_ready(active.source,settings)==true then
        if T.operator_return(env,active,'PRIMARY-RECOVERED')==nil then
          T.publish(env,{state='ROLLED-BACK',reason='PRIMARY-RECOVERED',source=active.source,target=active.target,original_restored=true,trial=getd(active,'trial',false)})
          return 2
        end
      end
      T.publish(env,{state='STOPPED-ON-RESERVE',reason=getd(active,'reason','SOURCE-NOT-VERIFIED'),source=active.source,target=active.target,expected_exit=getd(active,'expected_exit',NULL),
        original_restored=false,reserve_healthy=getd(active,'reserve_healthy',false),trial=getd(active,'trial',false)})
      return 5
    end
    local preparation=getd(settings,'native_prepare_acceleration','')
    if preparation~='' then
      if active.phase=='ARMED' or active.phase=='APPLYING' or active.phase=='WAIT-CLIENT' or active.phase=='COMMITTED' then ctl.refuse('ACCELERATION-PREPARE-DURING-TRANSACTION') end
      if not backend.disable_acceleration then ctl.refuse('ACCELERATION-PREPARE-UNAVAILABLE') end
      backend.disable_acceleration(preparation)
    end
    if active.phase=='COMMITTED' and (lease_expired or not enabled or stop_latched) then
      if not T.finish_committed(env,active,'TRIAL-ENDED') then return 5 end
      T.publish(env,{state='ROLLED-BACK',reason='TRIAL-ENDED'})
      active=T.journal_read(env);ctx.last_trial=getd(settings,'native_trial',nil)
    end
    local blockers,selection=backend.diagnostic()
    local function unguard_if_restored() if restored_order_is(env,active) then backend.unguard() end end
    if stop_latched then
      if progress_error then blockers[#blockers+1]=progress_error end
      unguard_if_restored()
      T.publish(env,{state='STOPPED',reason='CLIENT-STOP',original_restored=restored_order_is(env,active),blockers=canon.array(blockers),candidates=backend.candidates()})
      return 5
    end
    if not enabled then
      if progress_error then blockers[#blockers+1]=progress_error end
      unguard_if_restored()
      T.publish(env,{state='DISABLED',original_restored=restored_order_is(env,active),blockers=canon.array(blockers),acceleration=backend.acceleration(),
        candidates=backend.candidates(),adapter='experimental-existing-rule-order'})
      return 5
    end
    if until_>0 and lease_expired then
      unguard_if_restored();backend.clear_native_options()
      T.publish(env,{state='EXPIRED',reason='TRIAL-ENDED'});return 5
    end
    if lease_error then blockers[#blockers+1]=lease_error end
    if settings.native_session_loss~='1' then blockers[#blockers+1]='SESSION-LOSS-NOT-ACCEPTED' end
    if not (now<until_ and until_<=now+14400) then blockers[#blockers+1]='BOUNDED-DEADLINE-REQUIRED' end
    if #blockers>0 then
      if now>=until_ then unguard_if_restored() end
      T.publish(env,{state='BLOCKED',blockers=canon.array(blockers)});return 5
    end
    if active.phase=='COMMITTED' then
      local status=ctl.read_json(env.run,paths.status,canon.object({}))
      local decision=T.committed_recovery_decision(env,active,settings,getd(status,'samples',canon.array({})),env.run.wall(),status)
      if decision.action=='RESTORE-PRIMARY' then
        if T.finish_committed(env,active,decision.reason) then
          T.publish(env,{state='ROLLED-BACK',reason=decision.reason,source=active.source,target=active.target,original_restored=true})
        end
      else
        local previous=ctl.read_json_safe(env.run,paths.state,canon.object({}))
        T.publish(env,merge(previous,{state=decision.action=='OBSERVE' and 'COMMITTED' or 'DEGRADED-ON-RESERVE',source=active.source,target=active.target,
          reason=decision.reason,blockers=canon.array({}),reserve_healthy=decision.reserve_healthy==nil and NULL or decision.reserve_healthy,candidates=backend.candidates()}))
      end
      return 5
    end
    if progress_error then T.publish(env,{state='BLOCKED',blockers=canon.array({progress_error})});return 5 end
    local trial=getd(settings,'native_trial','')
    local forced=trial~='' and trial~=ctx.last_trial
    local consumed=ctx.consumed or canon.object({})
    if num(consumed['until'])~=until_ then consumed=canon.object({['until']=canon.float(until_),count=0,trial=ctx.last_trial==nil and NULL or ctx.last_trial,time=canon.float(ctx.last_attempt or 0)}) end
    if (num(getd(consumed,'count',0)) or 0)>=3 then T.publish(env,{state='BLOCKED',blockers=canon.array({'TRIAL-ATTEMPT-LIMIT'})});return 5 end
    local status=ctl.read_json(env.run,paths.status,canon.object({}))
    local diagnosis=env.deps and env.deps.diagnose and env.deps.diagnose(status,selection.source.id,env.run.wall(),settings) or {}
    if diagnosis.suppress_switch then
      T.publish(env,{state='BLOCKED',blockers=canon.array({diagnosis.code}),reason=diagnosis.code,source=selection.source.id,target=selection.target.id,certified=false,next_action=diagnosis.next_action or NULL})
      return 5
    end
    local recovery=pair.recovery_normalized(settings);local age=pair.valid_for(settings)
    local samples=getd(status,'samples',canon.array({}))
    local failures=pair.streak(samples,selection.source.id,recovery.failures,env.run.wall(),age,false,selection.source,env)
    local healthy=pair.streak(samples,selection.target.id,recovery.successes,env.run.wall(),age,true,selection.target,env)
    local certificate=ctl.read_json(env.run,paths.cert,canon.object({}))
    local certified=certificate.hash==selection.hash and certificate.source==selection.source.id and certificate.target==selection.target.id
      and certificate.direction==selection.direction and (num(getd(certificate,'until',0)) or 0)>=until_ and getd(certificate,'settings_hash',NULL)==getd(selection,'settings_hash',NULL)
      and getd(certificate,'vendor_identity',NULL)==getd(selection,'vendor_identity',NULL) and getd(certificate,'proof_scope','external-lan')==getd(selection,'proof_scope','external-lan')
    if env.run.wall()-(ctx.last_attempt or 0)>=math.max(recovery.cooldown,recovery.min_dwell) and (forced or (certified and failures and healthy)) then
      ctx.last_attempt=env.run.wall();ctx.last_trial=trial
      consumed.trial=trial;consumed.time=canon.float(ctx.last_attempt);consumed.count=(num(getd(consumed,'count',0)) or 0)+1
      ctl.write_json(env.run,paths.attempts,consumed)
      T.attempt(env,selection,until_,forced,{probe_evidence=canon.object({source_streak_met=failures,reserve_streak_met=healthy,required_failures=recovery.failures,required_successes=recovery.successes}),
        control_revision=decision_revision})
    else
      T.publish(env,{state=certified and 'OBSERVING' or 'TRIAL-REQUIRED',certified=certified,source=selection.source.id,target=selection.target.id,
        source_generation=getd(selection.source,'vendor_generation',NULL),target_generation=getd(selection.target,'vendor_generation',NULL),
        vendor_identity=getd(selection,'vendor_identity',NULL),source_failures=failures,reserve_healthy=healthy})
    end
    return 5
  end,with_trace)
  if ok then return err end
  if not is_refused(err) then error(err,0) end  -- a plain Lua error is a bug: let procd restart and recover
  local reason=err.code
  local preparation=ctl.read_json_safe(env.run,env.persist..'/acceleration-prepare.json',canon.object({}))
  local failure={state='BLOCKED',blockers=canon.array({reason}),error_type='Refused',acceleration=backend.acceleration(),
    preparation=canon.object({phase=getd(preparation,'phase',NULL),step=getd(preparation,'step',NULL),attempts=getd(preparation,'attempts',NULL)})}
  local pok=pcall(T.publish,env,failure)
  if not pok then ctl.write_json(env.run,paths.state,merge(failure,{history_error='HISTORY-001',time=fwall(env)})) end
  local jok,pending=pcall(T.journal_read,env)
  if string.find(reason,'GUARD-RETAINED',1,true) or (jok and T.RECOVERY_PHASES[pending.phase]) then pair.fence_recovery(env);return 'exit' end
  return 5
end

-- The end of serve(): a Stop while on a committed reserve restores it, then the pair session is cleaned up.
function M.shutdown(env)
  local active=T.journal_read(env)
  if active.phase=='COMMITTED' then
    if T.finish_committed(env,active,'SERVICE-STOPPED') and order_is(env,getd(active,'restored_order',active.before),active.hash) then env.backend.unguard() end
  end
  pair.recover(env)
end

-- Blocking driver for tests and for a router without uloop: runs iterations until stop() or 'exit'.
function M.run_blocking(env,max_iterations)
  if M.recover(env)=='stopped' then return 'stopped' end
  local ctx={last_return=0,consumed=canon.object({}),last_trial=nil,last_attempt=0}
  local count=0
  while not env.stop() do
    local pause=M.iteration(env,ctx)
    if pause=='exit' then return 'exit' end
    count=count+1
    if max_iterations and count>=max_iterations then break end
    if pause=='nap' then M.nap(env,2) else env.sleep(pause) end
  end
  M.shutdown(env)
  return 'stopped'
end

-- nap(): the pause between pair ticks; a QUEUED owner click ends it at once.
function M.nap(env,seconds)
  local end_=env.run.clock()+seconds
  while not env.stop() do
    local left=end_-env.run.clock()
    if left<=0 then return end
    local row=ctl.read_json_safe(env.run,env.runtime..'/pair-manual-control.json',canon.object({}))
    if canon.is_object(row) and row.state=='QUEUED' then T.manual_stamp(env,'woke',row.id);return end
    env.sleep(math.min(0.2,left))
  end
end

------------------------------------------------------------------------------------------------------
-- uloop daemon
------------------------------------------------------------------------------------------------------
-- Diagnostics only: `touch /var/run/homensai-vpn/lua-profile.request` profiles this process for 60 s into
-- lua-profile.json (profiler.lua). Off, it costs one failed open() per pass.
M.PROFILE_SECONDS=60
function M.profile_tick(runtime) return require('profiler').tick(runtime,'lua-profile',M.PROFILE_SECONDS) end

function M.serve(env,on_stop)
  local uloop=require('uloop')
  uloop.init()
  if M.recover(env)=='stopped' then return end
  local ctx={last_return=0,consumed=canon.object({}),last_trial=nil,last_attempt=0}
  local timer
  local finished=false
  local function pass()
    if env.stop() then finished=true;M.shutdown(env);uloop.cancel();return end
    pcall(M.profile_tick,env.runtime)
    local pause=M.iteration(env,ctx)
    if pause=='exit' then finished=true;uloop.cancel();return end
    if pause=='nap' then
      -- poll the owner click every 200 ms for up to 2 s, like nap()
      local waited=0
      local function poll()
        if env.stop() then pass();return end
        local row=ctl.read_json_safe(env.run,env.runtime..'/pair-manual-control.json',canon.object({}))
        waited=waited+0.2
        if (canon.is_object(row) and row.state=='QUEUED') or waited>=2 then pass() else timer:set(200) end
      end
      timer=uloop.timer(poll);timer:set(200)
      return
    end
    timer=uloop.timer(pass);timer:set(math.floor(pause*1000))
  end
  timer=uloop.timer(pass);timer:set(1)
  uloop.run()
  -- uloop.run() also returns on SIGTERM/SIGINT (procd stop): end like serve() after `while not STOP`
  if not finished then
    if on_stop then on_stop() end
    M.shutdown(env)
  end
end

-- native_switch.serve(): one supervisor per router. RUNTIME/native.lock is held with flock(LOCK_EX|LOCK_NB) for the
-- life of the process, so the Lua and the Python supervisor can never run at the same time. Long-lived children
-- (rtp2.sh, ifup, the guard release job, the probe bridge) never inherit it (sys.close_fds).
function M.hold_native_lock(runtime)
  local path=runtime..'/native.lock'
  os.execute('mkdir -p '..runtime..' && chmod 700 '..runtime)
  local file=io.open(path,'a')
  if not file then return nil end
  local p=io.popen('for f in /proc/$$/fd/*; do if [ "$f" -ef '..path..' ]; then flock -xn "${f##*/}" && echo "${f##*/}"; exit 0; fi; done; exit 97','r')
  local out=p and p:read('*a') or ''
  if p then p:close() end
  local fd=tonumber(string.match(out,'^(%d+)\n$'))
  if not fd then file:close();return nil end
  return file,fd
end

-- Safety net of the Lua line: a plain Lua error ends the daemon (procd restarts it and recover() puts the journal
-- right). After FALLBACK_CRASHES such ends within FALLBACK_WINDOW seconds the process releases native.lock and
-- replaces itself with the Python supervisor (same pid, so procd's Stop still reaches it), and says so in the
-- system log and in RUNTIME/lua-auto-fallback.json. The Python supervisor stays until the next service restart.
M.FALLBACK_CRASHES=3
M.FALLBACK_WINDOW=600
M.PYTHON_SUPERVISOR={'/usr/bin/python3','/usr/lib/homensai-vpn/native_switch.py','daemon'}
-- record_crash(path, now, message) -> number of crashes inside the window, this one included
function M.record_crash(fs,path,now,message)
  local times={}
  local text=fs.read(path)
  if text then
    local ok,value=pcall(canon.decode,text)
    if ok and canon.is_object(value) and type(value.times)=='table' then
      for _,x in ipairs(value.times) do
        local t=canon.number(x)
        if t and now-t<M.FALLBACK_WINDOW and t<=now then times[#times+1]=t end
      end
    end
  end
  times[#times+1]=now
  while #times>10 do table.remove(times,1) end
  local floats={};for i,t in ipairs(times) do floats[i]=canon.float(t) end
  fs.write_atomic(path,canon.encode(canon.object({times=canon.array(floats),last_error=string.sub(tostring(message),1,2000)})))
  return #times
end
local function fall_back(run,lockfile,count,message)
  local nixio_ok,nixio=pcall(require,'nixio')
  local line='LUA-AUTO-FALLBACK: '..count..' Lua supervisor errors in '..M.FALLBACK_WINDOW..' s; running the Python supervisor'
  os.execute('logger -t homensai-vpn '.."'"..line.."'")
  pcall(run.fs.write_atomic,run.RUNTIME..'/lua-auto-fallback.json',canon.encode(canon.object({code='LUA-AUTO-FALLBACK',
    time=canon.float(run.wall()),crashes=count,last_error=string.sub(tostring(message),1,2000)})))
  lockfile:close()  -- the flock goes with the last descriptor; Python takes native.lock itself
  if nixio_ok and type(nixio)=='table' and nixio.exec then
    nixio.exec(M.PYTHON_SUPERVISOR[1],M.PYTHON_SUPERVISOR[2],M.PYTHON_SUPERVISOR[3])
  end
  io.stderr:write('LUA-AUTO-FALLBACK-FAILED\n')
  os.exit(1)
end
M.fall_back=fall_back

-- procd entry: `lua /usr/lib/homensai-vpn/lua/auto.lua daemon` (homensai_vpn.main.lua_auto='1').
-- SIGTERM: uloop ends uloop.run() after the running pass; then shutdown() like the end of serve().
function M.daemon()
  local run=require('runner')
  local sys=require('sys')
  local canon_=require('canon')
  if not canon_.safe_directory(run.RUNTIME) then error('runtime directory',0) end
  local lockfile,lockfd=M.hold_native_lock(run.RUNTIME)
  if not lockfile then io.stderr:write('NATIVE-SUPERVISOR-BUSY\n');os.exit(1) end
  sys.close_fds={lockfd}
  local backend=require('backend').new(sys)
  local stop=false
  local env={run=run,backend=backend,runtime=run.RUNTIME,persist='/etc/homensai-vpn',
             stop=function() return stop end,
             sleep=function(s) sys.sleep(s) end,
             history_lock=ctl.flock_file,version=backend.VERSION}
  backend.bind(env)
  local ok,err=xpcall(function()
    if pcall(require,'uloop') then M.serve(env,function() stop=true end)
    else
      -- no libubox-lua: the blocking driver (same passes; SIGTERM then ends the process without shutdown(), and
      -- the next start recovers the journal like after a power cut)
      M.run_blocking(env)
    end
  end,with_trace)
  if not ok then
    local message=type(err)=='table' and ('code '..tostring(err.code)) or tostring(err)
    io.stderr:write(message,'\n')
    local count=1
    pcall(function() count=M.record_crash(run.fs,run.RUNTIME..'/lua-auto-crashes.json',run.wall(),message) end)
    if count>=M.FALLBACK_CRASHES then fall_back(run,lockfile,count,message) end
    lockfile:close()
    os.exit(1)
  end
  lockfile:close()
end

-- `lua auto.lua check`: read-only comparison with native_switch.Linux on the live router (LUA-AUTO-ITEM1 §5).
-- Two passes of diagnostic/order/kernel_fingerprint/attest_policy; prints one JSON line with the results, the
-- time of each call (second pass = cached inputs) and the memory. Takes no lock, writes no state (the sha256
-- pipe of canon.lua uses a temporary RAM file when nixio.crypto has no sha256).
function M.check()
  local run=require('runner')
  local sys=require('sys')
  local backend=require('backend').new(sys)
  local env={run=run,backend=backend,runtime=run.RUNTIME,persist='/etc/homensai-vpn',stop=function() return true end,sleep=function() end}
  backend.bind(env)
  local out=canon.object({version=backend.VERSION,sha256_backend=canon.sha256_backend()})
  local function ms(t0) return canon.float(math.floor((run.wall()-t0)*10000+0.5)/10) end
  local function code(err) return type(err)=='table' and err.code or tostring(err) end
  for pass=1,2 do
    local t0=run.wall()
    local blockers,selection=backend.diagnostic()
    out['diagnostic_ms_'..pass]=ms(t0)
    t0=run.wall();local ok,order,hash=pcall(backend.order);out['order_ms_'..pass]=ms(t0)
    if not ok then order,hash=canon.array({}),code(order) end
    t0=run.wall();local fingerprint=backend.kernel_fingerprint();out['kernel_fingerprint_ms_'..pass]=ms(t0)
    t0=run.wall();local aok,proof=pcall(backend.attest_policy,selection);out['attest_ms_'..pass]=ms(t0)
    if not aok then proof=canon.object({verified=false,code=code(proof)}) end
    if pass==1 then
      out.blockers=canon.array(blockers);out.order=order;out.hash=hash;out.kernel_fingerprint=fingerprint or canon.null
      local s=selection or canon.object({})
      out.selection=canon.object({hash=s.hash or canon.null,vendor_identity=s.vendor_identity or canon.null,settings_hash=s.settings_hash or canon.null,
        process_bindings=s.process_bindings or canon.null,source=s.source and s.source.id or canon.null,target=s.target and s.target.id or canon.null,
        source_binding=s.source and s.source.kernel_binding or canon.null,target_binding=s.target and s.target.kernel_binding or canon.null})
      out.attest=canon.object({verified=proof.verified,role=proof.role or canon.null,kernel_fingerprint=proof.kernel_fingerprint or canon.null,
        repairable_missing=proof.repairable_missing or false,code=proof.code or canon.null})
    end
  end
  out.memory=canon.object(run.memory())
  print(canon.encode(out))
end

local script=arg and arg[0]
if script and (script=='auto.lua' or string.match(script,'/auto%.lua$')) then
  if arg[1]=='daemon' then M.daemon()
  elseif arg[1]=='check' then M.check() end
end

return M
