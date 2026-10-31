-- transaction.lua / rollback.lua / auto.lua recovery: happy path, rollback, Stop during the switch, restart.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local R=require('rollback')
local A=require('auto')
local ctl=require('auto_control')

local function pair_attempt(env,extra)
  local opts={control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2}),
    on_dispatch=function() env.dispatched=(env.dispatched or 0)+1 end}
  for k,v in pairs(extra or {}) do opts[k]=v end
  return T.attempt(env,env.backend.selection,env.run.wall()+3600,false,opts)
end

t.test('happy path: ARMED -> APPLYING -> WAIT-CLIENT -> COMMITTED, router probes confirm',function()
  local env=t.env()
  pair_attempt(env)
  local j=t.journal(env)
  t.eq(j.phase,'COMMITTED');t.eq(j.after,canon.array({'r2','r1'}));t.eq(j.before,canon.array({'r1','r2'}))
  t.eq(j.rtp_dispatched,true);t.eq(j.forward_policy_touched,true);t.eq(j.pid,canon.null)
  t.truthy(canon.is_float(j.confirmed) and canon.is_float(j.started))
  t.eq(j.pair_transition.destination_role,'target');t.eq(j.expected_exit,'203.0.113.5')
  t.eq(j.vendor_profiles.source.id,'wireguard:peer_1');t.eq(j.control_revision,env.revision)
  local phases={};for _,row in ipairs(j.phase_evidence) do phases[#phases+1]=row.phase end
  t.eq(phases,{'ARMED','APPLYING','WAIT-CLIENT','COMMITTED'})
  t.eq(env.backend.uci,{'r2','r1'});t.eq(env.backend.kernel,{'r2','r1'})
  t.eq(env.dispatched,1)
  t.eq(t.states(env),{'ARMED','APPLYING','WAIT-CLIENT','COMMITTED'})
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq(status.state,'COMMITTED');t.eq(status.mode,'continuous-pair');t.eq(status.transition_source,'automatic');t.eq(status.kernel_policy_verified,true)
  local cert=t.read(env,env.persist..'/native-certificate.json')
  t.eq(cert.hash,t.HEX64);t.eq(cert.proof_scope,'router-probed-ipv4')
  local hist=t.history(env)
  t.eq(hist.totals.attempts,1);t.eq(hist.totals.committed,1);t.eq(hist.totals.automatic_committed,1);t.eq(hist.totals.protocol_switches,1)
  t.eq(hist.events[4].attempt_id,1);t.eq(hist.active_attempt.terminal,true)
end)

t.test('rollback path: the kernel write fails after the UCI move -> RESTORING -> ROLLED-BACK, failure code kept',function()
  local env=t.env()
  env.backend.fail_apply='VENDOR-APPLY-FAILED'
  t.code('VENDOR-APPLY-FAILED',pair_attempt,env)
  local j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.reason,'TRANSACTION-FAILED');t.eq(j.failure_code,'VENDOR-APPLY-FAILED')
  t.eq(j.restored_order,canon.array({'r1','r2'}));t.eq(j.restore_target_order,canon.array({'r1','r2'}))
  t.eq(j.restore_before_order,canon.array({'r2','r1'}));t.eq(j.restore_before_verified,true)
  t.eq(j.rollback_failures,nil)
  t.truthy(ctl.hex(j.restore_kernel_fingerprint,64))
  t.eq(env.backend.uci,{'r1','r2'});t.eq(env.backend.kernel,{'r1','r2'})
  t.eq(t.states(env),{'ARMED','APPLYING','RESTORING','ROLLED-BACK'})
  local hist=t.history(env)
  t.eq(hist.totals.rollbacks,1);t.eq(hist.totals.committed,0)
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq(status.blockers,canon.array({'VENDOR-APPLY-FAILED'}));t.eq(status.transition_outcome,'restored')
end)

t.test('rollback that itself fails is counted; the limit ends in give_up',function()
  local env=t.env()
  env.backend.fail_apply='VENDOR-APPLY-FAILED'
  -- the restore kernel write fails too: rollback_failures=1
  local original_apply=env.backend.apply
  local calls=0
  env.backend.apply=function(write_command)
    calls=calls+1
    if calls==2 then env.backend.fail_apply='ROLLBACK-KERNEL-FAILED' end
    return original_apply(write_command)
  end
  -- as in Python attempt(): the failed rollback's own error propagates (the forward code stays in the journal)
  t.code('ROLLBACK-KERNEL-FAILED',pair_attempt,env)
  local j=t.journal(env)
  t.eq(j.phase,'RESTORING');t.eq(j.rollback_failures,1);t.eq(j.rollback_package,'2.0.0-lua-alpha2')
  -- a second failing recovery reaches the limit; the third start gives up (journal stays, Auto stops)
  env.backend.fail_apply='ROLLBACK-KERNEL-FAILED'
  t.code('ROLLBACK-KERNEL-FAILED',R.rollback_counted,env,t.journal(env),'SUPERVISOR-RECOVERY')
  t.eq(t.journal(env).rollback_failures,2)
  env.stopped=true  -- give_up publishes once and returns on stop
  t.eq(A.recover(env),'stopped')
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq(status.state,'BLOCKED');t.eq(status.alarm,'ROLLBACK-GIVEN-UP');t.eq(env.backend.guard_calls[#env.backend.guard_calls],'vpn-only')
  local stop=t.read(env,env.persist..'/native-stop.json')
  t.eq(stop.all_trials,true);t.eq(stop.trial,t.HEX32)
end)

t.test('Stop during the switch: the rotated control revision refuses WAIT-CLIENT and the order is restored',function()
  local env=t.env()
  env.backend.probe_ok=false
  env.backend.on_probe=function()
    -- the owner presses Stop while the supervisor waits for the router probes
    env.run.fs.write_atomic(env.runtime..'/auto-control-revision.json',canon.encode(canon.object({revision=string.rep('99',16)})))
  end
  t.code('CLIENT-STOP',pair_attempt,env)
  local j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.failure_code,'CLIENT-STOP');t.eq(j.restored_order,canon.array({'r1','r2'}))
  t.eq(env.backend.uci,{'r1','r2'});t.eq(env.backend.kernel,{'r1','r2'})
  t.eq(t.states(env),{'ARMED','APPLYING','WAIT-CLIENT','RESTORING','ROLLED-BACK'})
  local progress=t.read(env,env.runtime..'/native-attempt-result.json')
  t.eq(progress.stage,'confirmation');t.eq(progress.code,'CLIENT-STOP');t.eq(progress.worker_stage,'done')
end)

t.test('a refused step before any write ends as ROLLED-BACK / FAILED-BEFORE-APPLY',function()
  local env=t.env()
  env.backend.blockers={'VENDOR-WORKER-BUSY'}
  t.code('VENDOR-WORKER-BUSY',pair_attempt,env)
  t.eq(t.journal(env).phase,nil)  -- refused before the ARMED journal: nothing written
  env.backend.blockers={}
  env.backend.diagnostic=function()
    env.diag=(env.diag or 0)+1
    if env.diag==3 then return {'PROFILE-IDENTITY-CHANGED'},nil end  -- the APPLYING step's diagnostic
    return {},env.backend.selection
  end
  t.code('PROFILE-IDENTITY-CHANGED',pair_attempt,env)
  local j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.reason,'SUPERVISOR-RECOVERY'==j.reason and 'x' or j.reason)
  t.eq(j.rtp_dispatched,false);t.eq(j.restored_order,canon.array({'r1','r2'}))
  t.eq(env.backend.uci,{'r1','r2'})
end)

t.test('recovery on restart: APPLYING with UCI moved and no kernel dispatch -> UCI undone, ROLLED-BACK',function()
  local env=t.env()
  -- a crashed supervisor left this journal (as the Python child would after the reorder, before rtp/restore)
  local pair=require('pair')
  local sel=env.backend.selection
  local ctx=pair.policy.transition(sel,canon.array({'r1','r2'}),'target')
  local value=canon.object({tx=string.rep('ee',16),phase='APPLYING',before=canon.array({'r1','r2'}),after=canon.array({'r2','r1'}),hash=t.HEX64,
    source=sel.source.id,target=sel.target.id,deadline=canon.float(env.run.wall()+100),monotonic_deadline=canon.float(env.run.clock()+100),
    lease_monotonic_until=canon.float(env.run.clock()+3600),trial=false,trial_nonce=t.HEX32,pid=canon.null,started=canon.float(env.run.wall()-10),
    vendor_identity=sel.vendor_identity,process_bindings=sel.process_bindings,proof_scope='router-probed-ipv4',control_revision=env.revision,
    pair_transition=ctx,kernel_before_fingerprint=env.backend.kernel_fingerprint(),kernel_before_verified=true,forward_policy_touched=true,rtp_dispatched=false,
    transition_source='automatic'})
  T.journal_write(env,value)
  env.backend.uci={'r2','r1'}
  t.eq(A.recover(env),'ready')
  local j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.reason,'SUPERVISOR-RECOVERY');t.eq(j.restored_order,canon.array({'r1','r2'}))
  t.eq(j.restore_before_order,canon.array({'r2','r1'}));t.eq(j.kernel_policy_verified,false)
  t.eq(env.backend.uci,{'r1','r2'});t.eq(env.backend.guard_calls,{'vpn-only'})
  -- the revision was rotated by the start
  t.truthy(t.read(env,env.runtime..'/auto-control-revision.json').revision~=env.revision)
  t.eq(t.states(env),{'ROLLED-BACK'})
end)

t.test('recovery on restart: WAIT-CLIENT after a kernel dispatch -> full restore; COMMITTED -> guard; manual -> HELD',function()
  local env=t.env()
  pair_attempt(env)
  local j=t.journal(env)
  j.phase='WAIT-CLIENT';j.confirmed=nil;T.journal_write(env,j)
  t.eq(A.recover(env),'ready')
  j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.reason,'SUPERVISOR-RECOVERY');t.eq(env.backend.uci,{'r1','r2'});t.eq(env.backend.kernel,{'r1','r2'})
  -- COMMITTED stays committed, guard installed
  env=t.env();pair_attempt(env);env.backend.guarded=false;env.backend.guard_calls={}
  t.eq(A.recover(env),'ready');t.eq(t.journal(env).phase,'COMMITTED');t.eq(env.backend.guard_calls,{'vpn-only'})
  -- COMMITTED with a manual request and a confirmation becomes HELD-ON-RESERVE
  env=t.env();pair_attempt(env)
  j=t.journal(env);j.manual_request_id=string.rep('ab',16);T.journal_write(env,j)
  t.eq(A.recover(env),'ready');j=t.journal(env);t.eq(j.phase,'HELD-ON-RESERVE');t.eq(j.reason,'OPERATOR-MANUAL')
  -- COMMITTED but the policy was changed outside: abandon -> STOPPED
  env=t.env();pair_attempt(env);env.backend.uci={'r1','r2'}
  t.eq(A.recover(env),'ready');j=t.journal(env);t.eq(j.phase,'ROLLED-BACK');t.eq(j.abandoned,true);t.eq(j.reason,'EXTERNAL-POLICY-CHANGE')
end)

t.test('recovery on restart: an unreadable journal blocks the LAN once and gives up',function()
  local env=t.env()
  env.run.fs.write_atomic(env.persist..'/native-transaction.json','{"schema":1,"data":{},"sha256":"00"}')
  env.stopped=true
  t.eq(A.recover(env),'stopped')
  t.eq(env.backend.guard_calls[1],'full')
  t.truthy(t.read(env,env.persist..'/native-journal-alarm.json').code=='JOURNAL-INTEGRITY-FAILED')
  t.eq(t.read(env,env.runtime..'/native-status.json').alarm,'JOURNAL-INTEGRITY-FAILED')
  env.backend.guard_calls={}
  t.eq(A.recover(env),'stopped');t.eq(env.backend.guard_calls,{'vpn-only'})  -- never a second full block
end)

t.test('manual attempt ends HELD-ON-RESERVE; operator return restores the primary',function()
  local env=t.env()
  local id=string.rep('ab',16)
  pair_attempt(env,{manual_request_id=id,request_source='manual',pair_destination='target'})
  local j=t.journal(env)
  t.eq(j.phase,'HELD-ON-RESERVE');t.eq(j.manual_request_id,id);t.eq(j.reserve_healthy,true);t.eq(j.transition_source,'manual')
  t.eq(t.read(env,env.runtime..'/native-status.json').state,'STOPPED-ON-RESERVE')
  local handled,stamp=T.handle_return(env,j,canon.object({time=canon.float(env.run.wall()),tx=j.tx}),0,nil)
  t.eq(handled,true)
  local result=t.read(env,env.runtime..'/native-return-result.json')
  t.eq(result.ok,true);t.eq(result.code,'RETURNED')
  j=t.journal(env);t.eq(j.phase,'ROLLED-BACK');t.eq(j.reason,'OPERATOR-RETURN');t.eq(env.backend.uci,{'r1','r2'})
  t.eq(env.backend.guarded,false)
  -- wrong tx / expired request
  local h2=T.handle_return(env,j,canon.object({time=canon.float(env.run.wall()+1),tx='other'}),stamp,nil)
  t.eq(h2,true);t.eq(t.read(env,env.runtime..'/native-return-result.json').code,'RETURN-TRANSACTION-MISMATCH')
end)

t.test('request checks and the Refused codes of attempt()',function()
  local env=t.env()
  t.code('MANUAL-REQUEST-INVALID',T.attempt,env,env.backend.selection,env.run.wall()+60,true,{manual_request_id=string.rep('ab',16)})
  t.code('MANUAL-REQUEST-INVALID',T.attempt,env,env.backend.selection,env.run.wall()+60,false,{pair_destination='target'})
  t.code('MANUAL-REQUEST-INVALID',T.attempt,env,env.backend.selection,env.run.wall()+60,false,{pair_reapply=true})
  t.code('SOURCE-ORDER-MISMATCH',T.attempt,env,t.selection({order=canon.array({'r2','r1'}),generic_rules=canon.array({'r1','r2'})}),env.run.wall()+60,false,{control_revision=env.revision})
end)

t.test('deadline(), monotonic_lease(), transaction_expired(), progress_read()',function()
  local env=t.env()
  t.eq(T.deadline(nil),0);t.eq(T.deadline(''),0);t.eq(T.deadline('1761830400'),1761830400);t.eq(T.deadline(canon.float(5.5)),5.5)
  t.eq(T.deadline('2026-10-30T14:00:00+00:00'),1793368800)
  t.eq(T.deadline('2026-10-30T14:00:00Z'),1793368800);t.eq(T.deadline('2026-10-30T16:00:00.5+02:00'),1793368800.5)
  t.code('DEADLINE-TIMEZONE-REQUIRED',T.deadline,'2026-10-30T14:00:00')
  t.code('BOUNDED-DEADLINE-REQUIRED',T.deadline,'soon');t.code('BOUNDED-DEADLINE-REQUIRED',T.deadline,true)
  local settings=t.settings()
  local end_,err=T.monotonic_lease(env,settings,env.run.wall()+3600)
  t.eq(err,nil);t.eq(end_,env.run.clock()+3600)
  local again=T.monotonic_lease(env,settings,env.run.wall()+3600);t.eq(again,end_)
  t.eq(select(2,T.monotonic_lease(env,settings,env.run.wall()+20000)),'BOUNDED-DEADLINE-REQUIRED')
  env.run.fs.write_atomic(env.runtime..'/native-lease.json','{"data":{"identity":"x"},"sha256":"00"}')
  t.eq(select(2,T.monotonic_lease(env,settings,env.run.wall()+3600)),'LEASE-INTEGRITY-FAILED')
  local value=canon.object({deadline=canon.float(env.run.wall()+10),monotonic_deadline=canon.float(env.run.clock()+5)})
  t.eq(T.transaction_expired(env,value),false);env.run.advance(6);t.eq(T.transaction_expired(env,value),true)
  t.eq(T.progress_read(env,env.persist..'/native-attempts.json','attempts'),canon.object({}))
  env.run.fs.write_atomic(env.persist..'/native-attempts.json','{"until":1,"count":1,"trial":"t","time":2}')
  t.eq(T.progress_read(env,env.persist..'/native-attempts.json','attempts').count,1)
  env.run.fs.write_atomic(env.persist..'/native-attempts.json','{"until":1,"count":4,"trial":"t","time":2}')
  t.code('NATIVE-PROGRESS-UNVERIFIED',T.progress_read,env,env.persist..'/native-attempts.json','attempts')
  env.run.fs.write_atomic(env.runtime..'/r.json','{"request":5,"ok":true,"code":"RETURNED","time":6}')
  t.eq(T.progress_read(env,env.runtime..'/r.json','return').code,'RETURNED')
end)

t.test('committed_recovery_decision and finish_committed',function()
  local env=t.env()
  pair_attempt(env)
  local j=t.journal(env)
  local settings=t.settings()
  local now=env.run.wall()
  local samples=canon.array({})
  for i=0,3 do samples[#samples+1]=canon.object({id='openvpn:1_1',time=canon.float(now-i*10),code='VPN-001',interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2}) end
  local target=env.backend.selection.target
  target.vendor_changed_at=canon.float(now-1000)
  -- primary healthy, dwell not reached, reserve failed -> RESTORE-PRIMARY (reserve failed, primary verified)
  local d=T.committed_recovery_decision(env,j,settings,samples,now,canon.object({samples=samples}))
  t.eq(d.action,'RESTORE-PRIMARY');t.eq(d.reason,'RESERVE-FAILED-PRIMARY-VERIFIED')
  -- primary not ready, reserve failed, fresh health false -> HOLD RESERVE-FAILED
  env.backend.health_of['wireguard:peer_1']=false;env.backend.health_of['openvpn:1_1']=false
  d=T.committed_recovery_decision(env,j,settings,samples,now,canon.object({samples=samples}))
  t.eq(d,{action='HOLD',reason='RESERVE-FAILED',reserve_healthy=false})
  -- nothing failed, dwell reached, primary healthy -> PRIMARY-STABLY-RECOVERED
  env.backend.health_of={}
  d=T.committed_recovery_decision(env,j,settings,canon.array({}),now+120,canon.object({}))
  t.eq(d.reason,'PRIMARY-STABLY-RECOVERED')
  d=T.committed_recovery_decision(env,j,settings,canon.array({}),now+10,canon.object({}))
  t.eq(d,{action='OBSERVE',reason='CLIENT-CONFIRMED'})
  -- identity unknown
  env.deps.resolve_pair=function() return {coordination={state='READY'},target=canon.object({id='other'})} end
  t.eq(T.committed_recovery_decision(env,j,settings,canon.array({}),now,canon.object({})).reason,'RESERVE-IDENTITY-UNKNOWN')
  -- finish_committed: source not healthy -> HELD-ON-RESERVE / SOURCE-NOT-VERIFIED
  env.backend.health_of['wireguard:peer_1']=false
  t.eq(T.finish_committed(env,j,'TRIAL-ENDED'),false);t.eq(t.journal(env).phase,'HELD-ON-RESERVE');t.eq(t.journal(env).reason,'SOURCE-NOT-VERIFIED')
  env.backend.health_of={}
  t.eq(T.finish_committed(env,t.journal(env),'PRIMARY-STABLY-RECOVERED'),true);t.eq(t.journal(env).phase,'ROLLED-BACK');t.eq(env.backend.uci,{'r1','r2'})
end)

t.test('publish(): history refusal blocks the status with HISTORY-001; sources and scope defaults',function()
  local env=t.env()
  T.publish(env,{state='OBSERVING',source='wireguard:peer_1',target='openvpn:1_1',proof_scope='router-probed-ipv4',reason='PAIR-WATCHING'})
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq(status.mode,'continuous-pair');t.eq(status.external_lan_verified,false);t.eq(status.route_changed,false);t.eq(status.transition_metadata_present,true)
  T.publish(env,{state='STOPPED',reason='OPERATOR-RETURN',source='wireguard:peer_1',target='openvpn:1_1'})
  t.eq(t.read(env,env.runtime..'/native-status.json').transition_source,'unknown')
  env.run.fs.write_atomic(env.persist..'/native-history.json','{"data":{"events":"x"},"schema":1,"sha256":"0"}')
  env.run.fs.write_atomic(env.persist..'/native-history.backup.json','{"data":{"events":"x"},"schema":1,"sha256":"0"}')
  t.code('HISTORY-001',T.publish,env,{state='OBSERVING'})
  t.eq(t.read(env,env.runtime..'/native-status.json').blockers,canon.array({'HISTORY-001'}))
end)

t.test('auto.iteration: pair tick observing, Stop latch, disabled, blocked',function()
  local env=t.env()
  local pair=require('pair')
  -- a running pair session with a RUNNING state and matching intent
  local sel=env.backend.selection
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=string.rep('11',16),request_source='manual'})))
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='0'}),canon.object({['.name']='ovpnclient1',disabled='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function() return false end}
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(env.run.wall()-10),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)})
  pair.save(env,state)
  env.run.fs.write_atomic(env.runtime..'/status.json','{"samples":[],"profiles":[]}')
  local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  t.eq(A.iteration(env,ctx),'nap')
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq(status.state,'OBSERVING');t.eq(status.reason,'PAIR-WATCHING');t.eq(status.kernel_policy_verified,true)
  t.eq(pair.read_state(env).selected_policy.role,'source')
  -- the source fails three times, the reserve is healthy twice -> the switch happens
  local now=env.run.wall();local rows={}
  for i=0,2 do rows[#rows+1]=canon.object({id='wireguard:peer_1',time=canon.float(now-i*10),code='VPN-001',interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',vendor_generation=t.GEN1}) end
  for i=0,1 do rows[#rows+1]=canon.object({id='openvpn:1_1',time=canon.float(now-i*10),code=canon.null,dns_ok=true,https_success=2,interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2}) end
  sel.source.vendor_changed_at=canon.float(now-1000);sel.target.vendor_changed_at=canon.float(now-1000)
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({samples=canon.array(rows),profiles=canon.array({})})))
  t.eq(A.iteration(env,ctx),'nap')
  local j=t.journal(env)
  t.eq(j.phase,'COMMITTED');t.eq(env.backend.kernel,{'r2','r1'});t.eq(#env.backend.leases,1)
  t.eq(#t.read(env,env.persist..'/pair-auto-budget.json').events,1)
  -- Stop: intent off -> cleanup -> finish_committed(PAIR-STOPPED) -> restore -> STOPPED
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='off',revision=env.revision,time=canon.float(env.run.wall())})))
  env.net.ifdown=function() end;env.net.quiet=function() end;env.net.set_disabled=function() end;env.net.interface_exists=function() return false end
  t.eq(A.iteration(env,ctx),'nap')
  t.eq(t.journal(env).phase,'ROLLED-BACK');t.eq(env.backend.uci,{'r1','r2'})
  t.eq(pair.read_state(env).phase,'STOPPED');t.eq(t.read(env,env.runtime..'/native-status.json').state,'STOPPED')
  -- without pair intent and with a native stop latch: STOPPED / CLIENT-STOP
  env.run.fs.remove(env.runtime..'/pair-auto-control.json')
  env.run.fs.write_atomic(env.persist..'/native-stop.json',canon.encode(canon.object({requested=canon.float(env.run.wall()),trial=env.backend.settings.native_trial})))
  t.eq(A.iteration(env,ctx),5)
  t.eq(t.read(env,env.runtime..'/native-status.json').reason,'CLIENT-STOP')
  env.run.fs.remove(env.persist..'/native-stop.json')
  env.backend.settings.native_enabled='0'
  t.eq(A.iteration(env,ctx),5);t.eq(t.read(env,env.runtime..'/native-status.json').state,'DISABLED')
  env.backend.settings.native_enabled='1';env.backend.settings.native_session_loss='0'
  t.eq(A.iteration(env,ctx),5);local st=t.read(env,env.runtime..'/native-status.json');t.eq({st.state,st.reason or '',st.blockers},{'BLOCKED','',canon.array({'SESSION-LOSS-NOT-ACCEPTED'})})
end)

t.run()
