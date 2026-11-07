-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- forward_resume.lua: after a supervisor restart, finish an interrupted automatic switch to the reserve instead of
-- rolling it back onto the failed primary (03.11.2026). Python: forward_resume.py. Shared cases:
-- tests/forward_resume_cases.json (decide()). Design and evidence: docs/architecture/BOOT-RECOVERY-2026-11-01.ru.md,
-- section "Дополнение 03.11.2026".
--
-- MT3000, 2.1.0-alpha5, 03.11.2026: the Auto process was SIGKILLed ~2.4 s into an automatic switch (journal APPLYING,
-- kernel already on the reserve) while the primary stayed down. procd restarted it; the recovery rolled back onto the
-- dead primary (SUPERVISOR-RECOVERY), the pair cleanup stopped both clients (PAIR-CLEANUP, ~24 s), the monitor's
-- restart resume pressed Start, the new session connected its clients (~28 s) and waited for the vendor (~34 s), then
-- Auto detected the failure again and switched: the LAN had no internet for 128 s (a normal failover ~20 s).
--
-- Now recover() first tries this module. decide() accepts only: journal APPLYING or WAIT-CLIENT of a continuous pair
-- (router-probed-ipv4); an automatic switch to the reserve (no trial, manual request, return or reapply); no rollback
-- started, no failure recorded, no earlier resume of this tx; the same boot (a RAM file of this transaction: the apply
-- progress names its tx, or the monotonic lease is the journal's; and the monotonic deadline is no further than one
-- transaction away: a power cut always rolls back as before); at least MIN_LEFT seconds of the transaction left;
-- the owner's Auto still wanted (resume marker, no newer Stop latch, the service not stopping); the primary failing
-- and the reserve healthy by a fresh live probe. resume() then proves the live state again: the pair session of this
-- switch unchanged, the vendor quiet (MT3000), the diagnostic identity the journal's, the live order exactly before
-- or after, the kernel either the recorded pre-switch graph (untouched: the writes are redone exactly as apply_steps,
-- under the new control revision) or already the reserve's (attested, nothing written). The journal records
-- forward_resumed before any write (one resume per transaction), then the switch ends like attempt(): kernel attested
-- target, VPN-only guard, WAIT-CLIENT, router probes confirm, COMMITTED with reason SUPERVISOR-FORWARD-RESUMED.
-- Any refusal goes to the unchanged rollback (SUPERVISOR-RECOVERY) with the journal as written. The RAM marker FILE
-- lets the pair cleanup hand the reserve over to the monitor's restart Start (variant D) without a boot.
local canon=require('canon')
local ctl=require('auto_control')

local M={}
local NULL=canon.null
local isnone,num=ctl.isnone,ctl.num
local refuse,is_refused=ctl.refuse,ctl.is_refused
M.REASON='SUPERVISOR-FORWARD-RESUMED'
M.FILE='supervisor-forward.json'   -- runtime (RAM): {tx,at=<monotonic>,outcome='committed'|'refused'} of this restart's resume
M.MIN_LEFT=15                      -- seconds of the transaction (wall and monotonic) a resume needs at least
M.SILENT={PHASE=true,['NOT-PAIR']=true}  -- not a continuous-pair switch: the old recovery, nothing to log

local function same_list(a,b)
  if type(a)~='table' or type(b)~='table' or #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i] then return false end end
  return true
end
local function fact(facts,name)
  local v=facts[name]
  if type(v)=='function' then v=v() end
  return v
end
local function getd(t,k,default) local v=t[k];if isnone(v) then return default end;return v end

-- decide(journal, facts) -> nil when the switch may be finished, else the refusal code (log only).
-- facts: same_boot, wall, mono, wanted, stop_requested, stopping, source_health, reserve_health
-- (the two healths may be functions: they are probed only when every other check passed).
function M.decide(j,f)
  if not canon.is_object(j) or (j.phase~='APPLYING' and j.phase~='WAIT-CLIENT') then return 'PHASE' end
  local ctx=j.pair_transition
  if not canon.is_object(ctx) or getd(j,'proof_scope','external-lan')~='router-probed-ipv4' then return 'NOT-PAIR' end
  if j.trial~=false or not isnone(j.manual_request_id) or not isnone(j.activation_reapply) or j.transition_source~='automatic' then
    return 'NOT-AUTOMATIC'
  end
  if ctx.destination_role~='target' or ctx.before_policy_role~='source' or same_list(j.before,j.after) then return 'NOT-FORWARD' end
  for key in pairs(j) do if type(key)=='string' and string.sub(key,1,7)=='restore' then return 'ROLLBACK-STARTED' end end
  if not isnone(j.failure_code) or not isnone(j.failure_detail) or (num(getd(j,'rollback_failures',0)) or 1)~=0
     or not isnone(j.confirmed) or not isnone(j.kernel_confirmed) or not isnone(j.finished) then return 'ROLLBACK-STARTED' end
  if not isnone(j.forward_resumed) then return 'ALREADY-RESUMED' end
  local md,deadline,started=num(j.monotonic_deadline),num(j.deadline),num(j.started)
  local wall,mono=num(f.wall),num(f.mono)
  if type(j.tx)~='string' or f.same_boot~=true or md==nil or mono==nil or md-mono>M.transaction_seconds()+1 then
    return 'OTHER-BOOT'
  end
  if deadline==nil or started==nil or wall==nil or deadline-wall<M.MIN_LEFT or md-mono<M.MIN_LEFT then return 'EXPIRED' end
  if f.stopping==true or f.wanted~=true then return 'OWNER-STOP' end
  if not isnone(f.stop_requested) then
    local stopped=type(f.stop_requested)~='string' and num(f.stop_requested) or nil
    if stopped==nil or stopped>=started then return 'OWNER-STOP' end
  end
  if fact(f,'source_health')~=false then return 'SOURCE-NOT-FAILED' end
  if fact(f,'reserve_health')~=true then return 'RESERVE-NOT-HEALTHY' end
  return nil
end
function M.transaction_seconds() return require('transaction').TRANSACTION_SECONDS end

-- the live facts of decide(); a Stop latch that cannot be read counts as a Stop
function M.facts(env,value)
  local T=require('transaction')
  local paths=T.paths(env)
  local progress=ctl.read_json_safe(env.run,paths.progress,canon.object({}))
  local lease=ctl.read_json_safe(env.run,paths.lease,canon.object({}))
  local data=canon.is_object(lease) and canon.is_object(lease.data) and lease.data or nil
  local until_=num(value.lease_monotonic_until)
  local same_boot=(canon.is_object(progress) and type(value.tx)=='string' and progress.tx==value.tx)
    or (data~=nil and until_~=nil and num(data.monotonic_until)==until_)
  local stop_requested=nil
  local text=env.run.fs.read(paths.stop)
  if text~=nil then
    local ok,row=pcall(canon.decode,text)
    stop_requested=ok and canon.is_object(row) and num(row.requested) or nil
    if stop_requested==nil then stop_requested='UNREADABLE' end
  end
  local br=require('boot_resume')
  local wok,wanted=pcall(br.wanted,function(p) return env.run.fs.read(p) end,env.persist)
  return {same_boot=same_boot==true,wall=env.run.wall(),mono=env.run.clock(),
    wanted=wok and wanted==true,stop_requested=stop_requested,stopping=env.stop()==true,
    source_health=function() return env.backend.health(value.source) end,
    reserve_health=function() return env.backend.health(value.target) end}
end

-- restarted(env, tx): this supervisor's recovery ran the forward resume of tx (finished or refused) within the pair's
-- KEEP_SECONDS (monotonic): a restart without a boot, whose monitor restart resume presses the owner's Start
function M.restarted(env,tx,committed)
  local row=ctl.read_json_safe(env.run,env.runtime..'/'..M.FILE,canon.object({}))
  if type(tx)~='string' or not canon.is_object(row) or row.tx~=tx then return false end
  if committed and not (row.outcome==nil or row.outcome=='committed') then return false end
  local ok,now=pcall(env.run.clock)
  local at=num(row.at)
  return ok and type(now)=='number' and at~=nil and at<=now and now-at<require('pair').KEEP_SECONDS
end
-- marked(env, tx): this supervisor's recovery finished tx forward (COMMITTED) within the pair's KEEP_SECONDS
function M.marked(env,tx) return M.restarted(env,tx,true) end

-- the diagnostic selection, waiting (bounded, like apply_steps' verify) while only the vendor is busy or settling
local function settled_selection(env)
  local T=require('transaction')
  local blockers,current=env.backend.diagnostic()
  local until_=env.run.clock()+T.VERIFY_VENDOR_WAIT
  local function transient(list)
    if #list==0 then return false end
    for _,b in ipairs(list) do if not T.VERIFY_TRANSIENT[b] then return false end end
    return true
  end
  while transient(blockers) and env.run.clock()<until_ and not env.stop() do env.sleep(2);blockers,current=env.backend.diagnostic() end
  if #blockers>0 then refuse(blockers[1]) end
  if not canon.is_object(current) then refuse('PROFILE-IDENTITY-CHANGED') end
  return current
end

-- the selection is the one of the journal: hash, vendor identity, bindings, profiles and the pair's rule roles
local function same_identity(env,value,ctx,current)
  local pair=require('pair')
  if current.hash~=value.hash or isnone(value.vendor_identity) or current.vendor_identity~=value.vendor_identity then return false end
  if canon.encode(getd(current,'process_bindings',NULL))~=canon.encode(getd(value,'process_bindings',NULL)) then return false end
  if getd(getd(current,'source',canon.object({})),'id',nil)~=value.source or getd(getd(current,'target',canon.object({})),'id',nil)~=value.target then return false end
  local ok,proof=pcall(pair.policy.proof,current)
  if not ok then return false end
  for key,item in pairs(proof) do if canon.encode(getd(ctx,key,NULL))~=canon.encode(item) then return false end end
  local profiles=getd(value,'vendor_profiles',nil)
  if not canon.is_object(profiles) then return false end
  for _,role in ipairs({'source','target'}) do
    local id=pair.profile_identity(env,current[role])
    if id==nil or canon.encode(id)~=canon.encode(getd(profiles,role,NULL)) then return false end
  end
  return true
end

-- resume(env, value) -> true when COMMITTED; false and a code when refused before any write; raises (coded) after
function M.resume(env,value)
  local T=require('transaction')
  local pair=require('pair')
  local P=pair.policy
  local backend=env.backend
  local code=M.decide(value,M.facts(env,value))
  if code then return false,code end
  local from_phase=value.phase
  local revision=ctl.current_revision(env)
  T.require_control_revision(env,revision)
  local ctx=P.metadata(value)
  -- the pair session that made this switch, unchanged (fenced by this recovery only)
  local state=pair.read_state(env)
  if not canon.is_object(state) or not (state.phase=='RUNNING' or state.phase=='HELD') or state.id~=value.trial_nonce
     or state.revision~=value.control_revision or not same_list(state.order,ctx.session_order) or state.policy_hash~=value.hash then
    return false,'PAIR-SESSION'
  end
  -- review F-28 (06.11.2026): the session's network identity and protected configuration are this recovery's proof of
  -- ownership, before any write and again before COMMITTED (forward_resume.py owned()); the kernel marking proves nothing
  -- about the configuration. Only the vendor-regenerated firewall sections differ legitimately: the static digest, when
  -- the session has one, must still match.
  local n=env.net
  if not n then return false,'PAIR-CONFIG-UNVERIFIED' end
  local mok,managed=pcall(pair.state_interfaces,state)
  if not mok then return false,'PAIR-SESSION' end
  local function owned()
    if n.identity(n.network(),managed)~=state.network_identity then refuse('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed),{firewall=true}) then refuse('PAIR-EXTERNAL-CONFIG-CHANGE') end
    local static=state.protected_static
    if canon.is_object(static) and type(n.static_firewall_digest)=='function' and n.static_firewall_digest()~=static.firewall then
      refuse('PAIR-EXTERNAL-CONFIG-CHANGE')
    end
  end
  local ook,oerr=pcall(owned)
  if not ook then return false,(is_refused(oerr) and ctl.code_ok(oerr.code)) and oerr.code or 'PAIR-CONFIG-UNVERIFIED' end
  -- an rtp2.sh of the killed process finishes first (MT3000: quiet GL workers, a stable kernel graph; bounded)
  local helpers=env.deps and env.deps.rollback_recovery
  if helpers and helpers.vendor_settled then helpers.vendor_settled(env) end
  local sok,current=pcall(settled_selection,env)
  if not sok then return false,is_refused(current) and current.code or 'DIAGNOSTIC' end
  if not same_identity(env,value,ctx,current) then return false,'IDENTITY' end
  T.bind_policy_context(env,value)
  local order,hash=backend.order()
  if hash~=value.hash then return false,'ORDER' end
  local at_after=same_list(order,value.after)
  if not at_after and not same_list(order,value.before) then return false,'ORDER' end
  local fingerprint=backend.kernel_fingerprint()
  local proof=backend.attest_policy(current)
  local forward=at_after and proof.verified==true and proof.role=='target'
  local untouched=not forward and ctl.hex(fingerprint,64) and fingerprint==value.kernel_before_fingerprint
  if not forward and not untouched then return false,'KERNEL' end
  if env.stop() then return false,'OWNER-STOP' end
  if untouched then
    -- nothing moved yet: finishing would be a new move onto that channel; a kernel already there stays (T.key_unaccepted)
    local pinned=T.key_unaccepted(env,value[ctx.destination_role])
    if pinned then return false,pinned end
  end
  -- one resume per transaction: recorded before the first write
  local progress=ctl.read_json_safe(env.run,T.paths(env).progress,canon.object({}))
  T.require_control_revision(env,revision)
  value.forward_resumed=canon.object({time=canon.float(env.run.wall()),from_phase=from_phase,kernel=forward and 'reserve' or 'untouched',
    stage=(canon.is_object(progress) and type(progress.stage)=='string') and progress.stage or NULL})
  T.journal_write(env,value)
  pcall(function() require('durable').log('SUPERVISOR-FORWARD: resuming '..value.tx..' from '..from_phase..' (kernel '..value.forward_resumed.kernel..')') end)
  if untouched then
    -- the writes of apply_steps, from the recorded pre-switch graph only, fenced by the new revision (Stop wins).
    -- The stock boot prefix of rtp2.sh is checked (and recreated) like the recovery's own rollback does, NOT through
    -- rtp_boot.prepare(): prepare() requires a running owner pair intent of this revision, and recover() has just
    -- rotated the revision and fenced the pair intent off (fence_recovery), so prepare() refused CLIENT-STOP on every
    -- real restart (MT3000 2.1.0-alpha7, 03.11.2026: SIGKILL in APPLYING, kernel untouched -> rollback, 130 s).
    -- The owner's will is proven by decide() (resume marker, no newer Stop latch, service not stopping) and every
    -- write below stays fenced by the new revision, which an owner Stop rotates.
    if env.deps and env.deps.rtp_boot then
      local rb=env.deps.rtp_boot
      env.run.fenced(revision,function() if rb.recovery_prefix then return rb.recovery_prefix() end;return rb.ready() end)
    end
    T.require_control_revision(env,revision)
    backend.guard(nil,revision)
    local function write_command(kind,fn,detail)
      T.require_control_revision(env,revision)
      if env.stop() then refuse('CLIENT-STOP') end
      T.assert_selection(env,current)
      T.require_control_revision(env,revision)
      if T.transaction_expired(env,value) then refuse('TRANSACTION-EXPIRED') end
      if backend.kernel_fingerprint()~=value.kernel_before_fingerprint then refuse('KERNEL-POLICY-UNVERIFIED') end
      if kind=='rtp' then
        local md=num(value.monotonic_deadline)
        if md==nil or md-env.run.clock()<T.RTP_DISPATCH_RESERVE then refuse('TRANSACTION-EXPIRED') end
        if env.deps and env.deps.rtp_boot then env.deps.rtp_boot.ready() end
      end
      if kind=='rtp' or kind=='kernel' then value.rtp_dispatched=true else value.forward_policy_touched=true end
      T.journal_write(env,value)
      if kind=='rtp' then T.apply_progress(env,value.tx,'rtp-dispatch') end
      local result=env.run.fenced(revision,fn)
      if type(result)=='function' then result=result() end
      if kind=='rtp' then T.apply_progress(env,value.tx,'rtp-returned') end
      return result
    end
    if not at_after then backend.reorder(value.after,nil,write_command) end
    backend.apply(write_command)
    current=settled_selection(env)
    if not same_identity(env,value,ctx,current) then refuse('PROFILE-IDENTITY-CHANGED') end
  end
  -- from here exactly the end of attempt(): kernel proof, exit, VPN-only guard, router probes, COMMITTED
  T.require_control_revision(env,revision)
  if not T.order_is(env,value.after,value.hash) then refuse('POLICY-CHANGED-DURING-APPLY') end
  local function kernel_target()
    local kernel=backend.attest_policy(T.merge(current,{order=T.copy_list(value.after)}))
    if kernel.verified~=true or kernel.role~='target' then refuse('KERNEL-POLICY-UNVERIFIED') end
    return kernel
  end
  local kernel=kernel_target()
  local target_exit=backend.trace(current.target)
  T.assert_selection(env,current)
  T.require_control_revision(env,revision)
  backend.guard(backend.devices(),revision)  -- VPN-only on the tunnels: the LAN goes out through the reserve from here
  value.phase='WAIT-CLIENT';value.expected_exit=target_exit;T.journal_write(env,value)
  local kind=T.transition_kind(current.source,current.target)
  local function publish(row)
    row=T.merge(T.pair_event_fields(value,row.completed and {completed=true,outcome='committed'} or nil),row)
    row.completed=nil;row.transition_source='automatic';row.destination_role='target';row.destination_profile_id=value.target
    local ok=pcall(T.publish,env,row)
    if not ok then ctl.write_json(env.run,T.paths(env).state,T.merge(row,{time=canon.float(env.run.wall()),history_error='HISTORY-001'})) end
  end
  publish({state='WAIT-CLIENT',tx=value.tx,expected_exit=target_exit,deadline=value.deadline,source=value.source,target=value.target,trial=false,
    reason=M.REASON,transition_kind=kind})
  while not T.transaction_expired(env,value) and not env.stop() do
    T.require_control_revision(env,revision)
    local stopped=ctl.read_json(env.run,T.paths(env).stop,canon.object({}))
    if (num(stopped.requested) or 0)>=num(value.started) then refuse('CLIENT-STOP') end
    local measured=backend.probe(current.target,true)
    T.require_control_revision(env,revision)
    if isnone(measured.code) and measured.dns_ok==true and (num(measured.https_success) or 0)>=2 and backend.trace(current.target)==target_exit then
      if not T.order_is(env,value.after,value.hash) then refuse('EXTERNAL-POLICY-CHANGE') end
      kernel=kernel_target()
      T.assert_selection(env,current)
      T.require_control_revision(env,revision)
      if not T.order_is(env,value.after,value.hash) then refuse('EXTERNAL-POLICY-CHANGE') end
      -- K5 (formal model 03.11.2026): the revision check and the COMMITTED write under the control lock, as attempt():
      -- a Stop (it rotates the revision under this lock) is before (CLIENT-STOP, rollback) or after the commit
      owned()  -- F-28: the configuration is still the session's at the commit
      env.run.lock(function()
        T.require_control_revision(env,revision)
        -- review F-29 (06.11.2026): the loop checked the deadline before the probe; a probe that crossed it cannot commit
        if env.stop() then refuse('CLIENT-STOP') end
        if T.transaction_expired(env,value) then refuse('TRANSACTION-EXPIRED') end
        value.phase='COMMITTED';value.confirmed=canon.float(env.run.wall());value.reason=M.REASON;T.journal_write(env,value)
      end,env.runtime)
      pcall(ctl.write_json,env.run,env.runtime..'/'..M.FILE,canon.object({tx=value.tx,at=canon.float(env.run.clock()),time=value.confirmed,outcome='committed'}))
      -- as after attempt()'s COMMITTED: end the LAN flows still NATed to the primary (flow_reset.lua; a code, never a failure)
      T.reset_old_flows(env,value,'target')
      publish({state='COMMITTED',completed=true,tx=value.tx,source=value.source,target=value.target,trial=false,transition_kind=kind,reason=M.REASON,
        readiness_verified=true,kernel_policy_verified=true,kernel_proof=kernel,guard='VPN-only; IPv6 forwarded traffic blocked'})
      return true
    end
    env.sleep(1)
  end
  refuse('CLIENT-CONFIRMATION-TIMEOUT')
end

-- restart_of_this_boot(env, value): a restart without a boot - a RAM file of this transaction (facts.same_boot) and the
-- monotonic deadline no further than one transaction away (decide's OTHER-BOOT rule). After a boot the cleanup keeps
-- its own boot window and boot resume state (pair.boot_keep), so no refusal marker is written then.
function M.restart_of_this_boot(env,value)
  local ok,f=pcall(M.facts,env,value)
  local md=num(value.monotonic_deadline)
  local mono=ok and num(f.mono) or nil
  return ok and f.same_boot==true and md~=nil and mono~=nil and md-mono<=M.transaction_seconds()+1
end

-- try(env, value) -> true when the switch was finished; every refusal or error is logged and leaves the rollback
function M.try(env,value)
  local ok,done,code=pcall(M.resume,env,value)
  if ok and done==true then
    pcall(function() require('durable').log('SUPERVISOR-FORWARD-RESUMED: '..value.tx..' committed on the reserve') end)
    return true
  end
  local why=ok and tostring(code) or (is_refused(done) and tostring(done.code) or 'ERROR '..string.sub(tostring(done),1,200))
  if not M.SILENT[why] then
    pcall(function() require('durable').log('SUPERVISOR-FORWARD: rollback ('..why..')') end)
    -- MT3000 2.1.0-alpha7 (03.11.2026): after the refused resume and the rollback, the pair cleanup of this restart
    -- (uptime past the boot window) stopped both clients, the healthy reserve too (~20 s), and the restart Start
    -- brought them up again (~26 s). The marker lets that cleanup keep them up for the restart Start like the boot
    -- cleanup does (variant C, pair.boot_keep: the owner's marker, no newer Stop latch, every client up, the restart
    -- resume of this start not failed or skipped, KEEP_SECONDS; the VPN-only guard stays until then).
    if type(value)=='table' and type(value.tx)=='string' and M.restart_of_this_boot(env,value) then
      pcall(ctl.write_json,env.run,env.runtime..'/'..M.FILE,canon.object({tx=value.tx,at=canon.float(env.run.clock()),outcome='refused',code=why}))
    end
  end
  return false,why
end

return M
