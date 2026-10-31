-- pair.lua (policy, budget, streak, settings, state file) and manual.lua (record validity, light gate,
-- consume on the instant path, cancel on Stop), auto_control.lua (intent, stop latch, revision).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local manual=require('manual')
local ctl=require('auto_control')
local T=require('transaction')
local P=pair.policy

t.test('pair_policy: proof/role/desired_order/transition/metadata and refusals',function()
  local sel=t.selection()
  local proof=P.proof(sel)
  t.eq(proof,canon.object({source_rule='r1',target_rule='r2',direction='first',generic_rules=canon.array({'r1','r2'}),source_id='wireguard:peer_1',target_id='openvpn:1_1'}))
  t.eq(P.role(proof,canon.array({'r1','r2'})),'source');t.eq(P.role(proof,canon.array({'r2','r1'})),'target')
  t.eq(P.desired_order(proof,canon.array({'r1','r2'}),'target'),canon.array({'r2','r1'}))
  t.eq(P.desired_order(proof,canon.array({'r2','r1'}),'target'),canon.array({'r2','r1'}))
  t.code('PAIR-POLICY-UNVERIFIED',P.desired_order,proof,canon.array({'r1','r2'}),'other')
  local ctx=P.transition(sel,canon.array({'r1','r2'}),'target')
  t.eq(ctx.before_policy_role,'source');t.eq(ctx.primary_order,canon.array({'r1','r2'}));t.eq(ctx.destination_role,'target')
  t.code('PAIR-POLICY-UNVERIFIED',P.transition,sel,canon.array({'r1','x'}),'target')
  local value=canon.object({pair_transition=ctx,before=canon.array({'r1','r2'}),after=canon.array({'r2','r1'}),source='wireguard:peer_1',target='openvpn:1_1',phase='COMMITTED'})
  t.eq(P.metadata(value),ctx);t.eq(P.current_role(value),'target')
  value.after=canon.array({'r1','r2'});t.code('PAIR-POLICY-UNVERIFIED',P.metadata,value)
  value.after=canon.array({'r2','r1'});value.restored_order=canon.array({'r2','x'});t.code('PAIR-POLICY-UNVERIFIED',P.metadata,value)
  t.eq(P.metadata(canon.object({})),nil)
  local state=canon.object({order=canon.array({'r1','r2'}),policy_hash=t.HEX64,policy_roles=proof})
  value.restored_order=nil;value.hash=t.HEX64
  t.eq(P.state_order_matches(state,value,canon.array({'r2','r1'}),t.HEX64),true)
  t.eq(P.state_order_matches(state,value,canon.array({'r1','r2'}),t.HEX64),false)
  t.eq(P.state_order_matches(state,canon.object({}),canon.array({'r1','r2'}),t.HEX64),true)
end)

t.test('recovery settings, observation windows, budget, streak, stable_success',function()
  t.eq(pair.recovery_normalized(canon.object({})).failures,3)
  local r=pair.recovery_normalized(canon.object({recovery_failures='7',recovery_cooldown='5',recovery_return_policy='hold_reserve',recovery_attempt_limit='99',recovery_attempt_window='2'}))
  t.eq(r.failures,7);t.eq(r.cooldown,60);t.eq(r.return_policy,'hold_reserve');t.eq(r.attempt_limit,3);t.eq(r.attempt_window,2)
  t.eq(pair.valid_for(canon.object({interval='10'})),30);t.eq(pair.valid_for(canon.object({interval='x'})),90);t.eq(pair.valid_for(canon.object({interval='300'})),900)
  t.eq(pair.settle_for(canon.object({interval='10'})),30);t.eq(pair.settle_for(canon.object({})),60)
  local kept,ok=pair.budget(canon.array({100,200}),950,900,3);t.eq(#kept,2);t.eq(ok,true)
  kept,ok=pair.budget(canon.array({100,200,300}),400,900,3);t.eq(ok,false)
  kept,ok=pair.budget(canon.array({100,200,300}),1150,900,3);t.eq(#kept,1);t.eq(ok,true)
  t.code('PAIR-BUDGET-UNVERIFIED',pair.budget,canon.array({-1}),10)
  t.code('PAIR-BUDGET-UNVERIFIED',pair.budget,canon.array({}),10,30,3)
  local now=1000
  local function sample(id,time,code) return canon.object({id=id,time=canon.float(time),code=code or canon.null,dns_ok=code==nil and true or false,https_success=code==nil and 2 or 0}) end
  local s=canon.array({sample('a',now-5,'VPN-001'),sample('a',now-15,'VPN-001'),sample('a',now-25,'VPN-001'),sample('b',now-5),sample('b',now-15)})
  t.eq(pair.streak(s,'a',3,now,90,false),true);t.eq(pair.streak(s,'a',4,now,90,false),false);t.eq(pair.streak(s,'b',2,now,90,true),true)
  t.eq(pair.streak(s,'a',3,now+200,90,false),false)  -- stale
  t.eq(pair.streak(canon.array({sample('a',now-5,'VPN-001'),sample('a',now-5,'DNS-001')}),'a',1,now,90,false),false)  -- conflicting duplicates
  t.eq(pair.stable_success(canon.array({sample('b',now-5),sample('b',now-25),sample('b',now-45)}),'b',2,30,now,90),true)
  t.eq(pair.stable_success(canon.array({sample('b',now-5),sample('b',now-25)}),'b',2,30,now,90),false)
end)

t.test('pair state file: save/read roundtrip and refusals; intent; stop_locked',function()
  local env=t.env()
  t.eq(pair.read_state(env),canon.object({}))
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',started=canon.float(1),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),owned=canon.array({'wgclient1'}),before_flags=canon.object({wgclient1='1',ovpnclient1='0'}),
    order=canon.array({'r1','r2'}),policy_hash=t.HEX64,policy_roles=P.proof(t.selection())})
  pair.save(env,state)
  local back=pair.read_state(env)
  t.eq(canon.encode(back),canon.encode(state))
  local envelope=t.read(env,env.persist..'/pair-auto-state.json')
  t.eq(envelope.sha256,canon.digest(back))
  state.owned=canon.array({'wgclient9'});pair.save(env,state);t.code('PAIR-STATE-UNVERIFIED',pair.read_state,env)
  state.owned=canon.array({});state.manual_hold='x';pair.save(env,state);t.code('PAIR-MANUAL-HOLD-UNVERIFIED',pair.read_state,env)
  state.manual_hold=nil;pair.save(env,state)
  env.run.fs.write_atomic(env.persist..'/pair-auto-state.json','{"data":{"phase":"RUNNING"},"sha256":"x"}');t.code('PAIR-STATE-UNVERIFIED',pair.read_state,env)
  t.eq(pair.intent(env),canon.object({}))
  pair.stop_locked(env,env.revision,'manual')
  local row=pair.intent(env);t.eq(row.mode,'off');t.eq(row.request_source,'manual')
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json','{"mode":"maybe"}');t.code('PAIR-INTENT-UNVERIFIED',pair.intent,env)
end)

t.test('auto_control: effective_intent, valid_stop, revision, stop_latch, action_context',function()
  local env=t.env()
  local settings=t.settings();local now=env.run.wall()
  t.eq({ctl.effective_intent(settings,canon.object({}),canon.object({}),now,T.deadline)},{true,false})
  local stopped=canon.object({requested=canon.float(now-5),trial=t.HEX32})
  t.eq({ctl.effective_intent(settings,stopped,canon.object({}),now,T.deadline)},{true,true})
  local request=canon.object({mode='on',trial=t.HEX32,['until']=canon.float(T.deadline(settings.native_until)),time=canon.float(now-1)})
  t.eq({ctl.effective_intent(settings,stopped,request,now,T.deadline)},{true,false})
  stopped.requested=canon.float(now);t.eq({ctl.effective_intent(settings,stopped,request,now,T.deadline)},{false,true})
  t.eq({ctl.effective_intent(settings,canon.object({requested=canon.float(now),all_trials=true}),request,now,T.deadline)},{false,true})
  t.eq({ctl.effective_intent(settings,canon.object({requested=canon.float(now-2),all_trials=true}),request,now,T.deadline)},{true,false})
  t.eq(ctl.valid_stop(canon.object({requested=canon.float(1)})),false);t.eq(ctl.valid_stop(canon.object({requested=canon.float(1),all_trials=true})),true)
  t.eq(ctl.current_revision(env),env.revision)
  local rotated=ctl.current_revision(env,true);t.truthy(rotated~=env.revision and ctl.hex(rotated,32))
  t.eq(t.read(env,env.runtime..'/auto-control-revision.json'),canon.object({revision=rotated}))
  ctl.stop_latch(env,'abc')
  local stop=t.read(env,env.persist..'/native-stop.json');t.eq(stop.trial,'abc');t.eq(stop.all_trials,true)
  t.truthy(t.read(env,env.runtime..'/auto-control-revision.json').revision~=rotated)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',time=canon.float(now-3),request_source='manual'})))
  local ctx=ctl.action_context(env,now)
  t.eq(ctx.control_action,'stop')  -- the stop latch is newer
  t.eq(next(ctl.action_context(env,now-4)),nil)
end)

t.test('manual record validity, light_gate, consume on the instant path, Stop cancels',function()
  local env=t.env()
  local now=env.run.wall()
  local row=canon.object({id=string.rep('ab',16),pair=string.rep('11',16),revision=env.revision,direction='reserve',state='QUEUED',requested=canon.float(now),updated=canon.float(now),
    selection=canon.object({tx=canon.null}),code=canon.null,request_source='manual'})
  t.eq(manual.valid(row),true)
  row.direction='sideways';t.eq(manual.valid(row),false);row.direction='reserve'
  row.selection=canon.object({});t.eq(manual.valid(row),false);row.selection=canon.object({tx=canon.null})
  env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json','{"id":"x"}');t.code('PAIR-MANUAL-STATE-UNVERIFIED',manual.read,env)
  -- light gate
  env.run.fs.remove(env.runtime..'/pair-manual-control.json')
  env.run.fs.write_atomic(env.runtime..'/native-status.json',canon.encode(canon.object({state='OBSERVING',time=canon.float(now-5),source='wireguard:peer_1',target='openvpn:1_1'})))
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({profiles=canon.array({canon.object({id='openvpn:1_1',time=canon.float(now-2),code=canon.null,dns_ok=true,https_success=2})})})))
  t.eq(manual.light_gate(env,'reserve',t.settings()),nil)
  t.eq(manual.light_gate(env,'primary',t.settings()),'SOURCE-NOT-HEALTHY')
  env.run.fs.write_atomic(env.runtime..'/native-status.json',canon.encode(canon.object({state='OBSERVING',time=canon.float(now-60)})))
  t.eq(manual.light_gate(env,'reserve',t.settings()),'PAIR-MANUAL-STALE')
  -- consume: a RUNNING pair session, the click queued, instant path -> HELD-ON-RESERVE, state manual_hold=target
  local sel=env.backend.selection
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(now-10),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,policy_roles=P.proof(sel)})
  pair.save(env,state)
  env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json',canon.encode(row))
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  local done=manual.read(env)
  t.eq(done.state,'COMPLETED');t.eq(done.code,canon.null)
  local j=t.journal(env)
  t.eq(j.phase,'HELD-ON-RESERVE');t.eq(j.manual_instant,true);t.eq(j.manual_request_id,row.id);t.eq(j.transition_source,'manual')
  t.eq(env.backend.uci,{'r2','r1'});t.eq(env.backend.kernel,{'r2','r1'})
  local saved=pair.read_state(env)
  t.eq(saved.manual_hold,'target');t.eq(saved.manual_selection.request_id,row.id);t.eq(saved.selected_policy.role,'target')
  t.eq(t.states(env),{'APPLYING','COMMITTED'})
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq(status.manual,true);t.eq(status.switch_seconds,canon.float(0.5));t.eq(status.transition_outcome,'committed')
  t.eq(t.read(env,env.runtime..'/pair-manual-timing.json').stages[1][1],'claimed')
  t.eq(t.read(env,env.persist..'/pair-auto-budget.json'),nil)  -- the owner click is never charged
  -- a click after Stop (revision rotated) is cancelled with CONTROL-REVISION-STALE
  row.id=string.rep('ac',16);row.direction='primary';row.requested=canon.float(env.run.wall());row.updated=row.requested
  env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json',canon.encode(row))
  env.run.fs.write_atomic(env.runtime..'/auto-control-revision.json',canon.encode(canon.object({revision=string.rep('99',16)})))
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  t.eq(manual.read(env).state,'CANCELLED');t.eq(manual.read(env).code,'CONTROL-REVISION-STALE')
  -- an expired click
  env.run.fs.write_atomic(env.runtime..'/auto-control-revision.json',canon.encode(canon.object({revision=env.revision})))
  row.requested=canon.float(env.run.wall()-120);row.updated=row.requested
  env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json',canon.encode(row))
  t.eq(manual.consume(env,state,t.settings(),env.revision),true);t.eq(manual.read(env).code,'PAIR-MANUAL-EXPIRED')
  -- a CLAIMED record seen again is never replayed
  row.state='CLAIMED';row.requested=canon.float(env.run.wall());row.updated=row.requested
  env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json',canon.encode(row))
  t.eq(manual.consume(env,state,t.settings(),env.revision),true);t.eq(manual.read(env).state,'UNCONFIRMED');t.eq(manual.read(env).code,'PAIR-MANUAL-RECOVERED')
  -- instant failure after the UCI write rolls back (rollback_counted) and the click is REFUSED with the code
  env=t.env();pair.save(env,state)
  row.state='QUEUED';row.id=string.rep('ad',16);row.direction='reserve';row.requested=canon.float(env.run.wall());row.updated=row.requested
  env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json',canon.encode(row))
  env.run.fs.write_atomic(env.runtime..'/status.json','{"profiles":[]}')
  env.backend.fail_instant='KERNEL-POLICY-UNVERIFIED'
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  t.eq(manual.read(env).state,'REFUSED');t.eq(manual.read(env).code,'KERNEL-POLICY-UNVERIFIED')
  j=t.journal(env);t.eq(j.phase,'ROLLED-BACK');t.eq(j.failure_code,'KERNEL-POLICY-UNVERIFIED');t.eq(env.backend.uci,{'r1','r2'})
end)

t.test('held_reserve watches a manual hold; a failed held channel releases the hold',function()
  local env=t.env()
  local sel=env.backend.selection
  local now=env.run.wall()
  -- a committed manual reserve journal with a hold on target
  T.attempt(env,sel,now+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),manual_request_id=string.rep('ab',16),pair_destination='target',request_source='manual'})
  local state=canon.object({id=string.rep('11',16),phase='HELD',ran=true,started=canon.float(now-10),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,policy_roles=P.proof(sel),
    manual_hold='target',manual_hold_source='manual'})
  pair.save(env,state)
  local j=t.journal(env)
  t.eq(manual.held_reserve(env,state,j,t.settings(),canon.object({samples=canon.array({}),profiles=canon.array({})})),true)
  t.eq(t.read(env,env.runtime..'/native-status.json').reason,'PAIR-MANUAL-HOLD-RESERVE');t.eq(pair.read_state(env).phase,'RUNNING')
  -- three failures of the held reserve: the hold is released and the tick continues
  local rows={}
  for i=0,2 do rows[#rows+1]=canon.object({id='openvpn:1_1',time=canon.float(env.run.wall()-i*10),code='VPN-001',interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2}) end
  sel.target.vendor_changed_at=canon.float(now-1000)
  local r=manual.held_reserve(env,state,j,t.settings(),canon.object({samples=canon.array(rows),profiles=canon.array({})}));t.eq(r,false)
  t.eq(pair.read_state(env).manual_hold,nil)
end)

t.test('pair.tick: a refused preflight fails the request; transient start keeps it queued; readopt',function()
  local env=t.env()
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=string.rep('11',16)})))
  env.backend.pair_preflight=function() error(setmetatable({code='PAIR-PLATFORM-UNVERIFIED'},ctl.Refused),0) end
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  local row=pair.intent(env);t.eq(row.mode,'off');t.eq(row.failure_code,'PAIR-PLATFORM-UNVERIFIED');t.eq(row.failed_request_id,string.rep('11',16))
  t.eq(t.read(env,env.runtime..'/native-status.json').blockers,canon.array({'PAIR-PLATFORM-UNVERIFIED'}))
  -- transient: the Start stays queued for 90 s
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=string.rep('12',16)})))
  env.backend.pair_preflight=function() error(setmetatable({code='VENDOR-SETTLING'},ctl.Refused),0) end
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  t.eq(pair.intent(env).mode,'on');t.eq(t.read(env,env.runtime..'/native-status.json').reason,'PAIR-WAITING-VENDOR')
  -- mode not configured
  t.eq(pair.tick(env,t.settings({pair_auto_mode='off'}),env.revision),true);t.eq(pair.intent(env).failure_code,'PAIR-MODE-NOT-CONFIGURED')
  -- no intent, no state: nothing to do
  env.run.fs.remove(env.runtime..'/pair-auto-control.json');t.eq(pair.tick(env,t.settings(),env.revision),false)
end)

t.run()
