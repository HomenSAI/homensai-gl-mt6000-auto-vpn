-- A vendor rebuild of the reserve must not hold Auto on it for ever (finding 7).
-- MT3000, 2.1.0-alpha8, 04.11.2026 14:06-15:33 (this Lua runtime; private/soak-24h cycle 12): the vendor rebuilt the OpenVPN
-- reserve while it carried the traffic, its vendor_generation changed, committed_recovery_decision returned HOLD
-- RESERVE-IDENTITY-UNKNOWN on every pass for over an hour with both tunnels healthy, until the owner's Stop + Start.
-- Python twin: tests/test_reserve_rebuild.py (reserve_rebuild_cases.json, the same decisions and the same replay).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local pair=require('pair')
local ctl=require('auto_control')
local CM=require('channel_model')
local diagnosis=require('diagnosis')
local identity=require('identity')

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local DATA=canon.decode(read_file(t.here..'/../reserve_rebuild_cases.json'))
local PRIMARY,RESERVE='wireguard:peer_2006','openvpn:40354_2029'
local OLD,NEW='eb5934adf3c54f90a1b27fe9215f2402','1b9ca6945c504157b4a0dff608ab2d0b'
local P_OLD,P_NEW='1747efccea1b4be5a1c0fdc527bc3f52','5eea6867210845d086b220343cf919fb'
local GENERATIONS={OLD=OLD,NEW=NEW}
local NULL=canon.null
local function none(v) return v==nil or v==NULL end
local function n(v) return canon.number(v) end
local function proof(id,generation,interface,protocol)
  return canon.object({id=id,protocol=protocol,interface=interface,vendor_tunnel_id=protocol..':'..interface,vendor_generation=generation})
end
local PROOFS={source=proof(PRIMARY,P_OLD,'wgclient1','wireguard'),target=proof(RESERVE,OLD,'ovpnclient1','openvpn')}
local function row_of(base,fields)
  local out=canon.decode(canon.encode(base))
  for k,v in pairs(fields or {}) do out[k]=v end
  return out
end
local function deps(env)
  env.deps.profile_identity=identity.profile_identity
  env.deps.testing_profile=function() return false end
end

t.test('committed_recovery_decision: the shared cases',function()
  local D=DATA.defaults
  local real_failed,real_ready=CM.channel_failed,CM.return_ready
  local ok,err=pcall(function()
    for _,case in ipairs(DATA.cases) do
      local env=t.env();deps(env)
      local now=n(none(case.now) and D.now or case.now)
      local row=row_of(PROOFS.target,{vendor_generation=GENERATIONS[case.generation],vendor_changed_at=canon.float(n(D.changed_at)),time=canon.float(now)})
      if not none(case.live) then for k,v in pairs(case.live) do row[k]=v end end
      local count,generation,code=n(case.samples[1]),case.samples[2],case.samples[3]
      local healthy=none(code)
      local list={}
      -- the samples follow the live profile: only the proof can tell another tunnel from a rebuild
      for i=0,count-1 do
        list[#list+1]=row_of(row,{time=canon.float(now-10*i),code=healthy and NULL or code,dns_ok=healthy,https_success=healthy and 2 or 0,vendor_generation=GENERATIONS[generation]})
      end
      local confirmed=n(none(case.confirmed) and D.confirmed or case.confirmed)
      local value=canon.object({source=PRIMARY,target=RESERVE,confirmed=canon.float(confirmed),vendor_profiles=canon.object({source=PROOFS.source,target=PROOFS.target})})
      local asked={}
      env.backend.recovery_ready=function(id,settings) asked[#asked+1]=pair.stable_seconds(settings);return id==PRIMARY and case.primary_ready==true end
      env.backend.health=function() return true end
      env.deps.resolve_pair=function() return {coordination={state=none(case.coordination) and 'READY' or case.coordination},target=row,source=canon.object({id=PRIMARY})} end
      CM.channel_failed=function() return false end
      CM.return_ready=function() if none(case.model_ready) then return true end;return case.model_ready end
      local settings=row_of(none(case.settings) and D.settings or case.settings)
      local hold=none(case.hold) and nil or n(case.hold)
      local d=T.committed_recovery_decision(env,value,settings,canon.array(list),now,canon.object({}),hold)
      t.eq({d.action,d.reason,d.rebind==true},{case.action,case.reason,case.rebind},case.name)
      t.eq(asked[#asked],none(case.asked) and nil or n(case.asked),case.name..': stability asked')
    end
  end)
  CM.channel_failed,CM.return_ready=real_failed,real_ready
  if not ok then error(err,0) end
end)

-- manual.held_reserve: the same comparison held a manual session for ever (BLOCKED / DEGRADED-ON-RESERVE)
t.test('held_reserve: the shared cases',function()
  local manual=require('manual')
  local D=DATA.defaults
  local real={publish=T.publish,save=pair.save,resume=pair.resume_running,hold=pair.ledger_hold,rebound=pair.reserve_rebound,decide=T.committed_recovery_decision,
    bind=T.bind_policy_context,metadata=pair.policy.metadata,role=pair.policy.current_role,matches=pair.policy.state_order_matches}
  local ok,err=pcall(function()
    for _,case in ipairs(DATA.manual) do
      local env=t.env();deps(env)
      local now=n(D.now);local role=case.hold;local id=role=='target' and RESERVE or PRIMARY
      local recorded=role=='target' and OLD or P_OLD
      local live=role=='target' and GENERATIONS[case.generation] or (case.generation=='NEW' and NEW or recorded)
      local base=PROOFS[role]
      local row=row_of(base,{vendor_generation=live,vendor_changed_at=canon.float(n(D.changed_at)),time=canon.float(now)})
      if not none(case.live) then for k,v in pairs(case.live) do row[k]=v end end
      local count,gen,code=n(case.samples[1]),case.samples[2],case.samples[3]
      local healthy=none(code)
      local list={}
      for i=0,count-1 do
        local generation=role=='target' and GENERATIONS[gen] or ((gen=='NEW') and live or recorded)
        list[#list+1]=row_of(row,{time=canon.float(now-10*i),vendor_generation=generation,code=healthy and NULL or code,dns_ok=healthy,https_success=healthy and 2 or 0})
      end
      local value=canon.object({source=PRIMARY,target=RESERVE,confirmed=canon.float(n(D.confirmed)),phase='COMMITTED',after=canon.array({'b','a'}),hash=string.rep('c',64),
        vendor_profiles=case.no_proof==true and canon.object({}) or canon.object({source=PROOFS.source,target=PROOFS.target})})
      local state=canon.object({manual_hold=role,revision=string.rep('f',32)})
      env.run.wall_now=now
      env.backend.attest_policy=function() return canon.object({verified=true}) end
      local resolved={coordination={state=none(case.coordination) and 'READY' or case.coordination},source=NULL,target=NULL}
      resolved[role]=row
      env.deps.resolve_pair=function() return resolved end
      local published,rebound,asked={},0,false
      T.publish=function(_,v) published[#published+1]=v end
      T.bind_policy_context=function() end
      env.backend.order=function() return canon.array({'b','a'}),string.rep('c',64) end
      pair.save=function() end;pair.resume_running=function() end;pair.ledger_hold=function() return 60 end
      local settled_seen={}
      pair.reserve_rebound=function(_,_,settled) rebound=rebound+1;settled_seen[#settled_seen+1]=tostring(settled);return true end
      T.committed_recovery_decision=function() asked=true;return {action=case.decision,reason='PRIMARY-STABLY-RECOVERED'} end
      pair.policy.metadata=function() if case.branch=='legacy' then return nil end;return canon.object({x=1}) end
      pair.policy.current_role=function() return role end
      pair.policy.state_order_matches=function() return true end
      local returned=manual.held_reserve(env,state,value,row_of(D.settings),canon.object({samples=canon.array(list),profiles=canon.array({row})}))
      t.eq(returned,case.returns,case.name)
      local last=published[#published]
      t.eq(last and last.state or NULL,case.state,case.name);t.eq(last and last.reason or NULL,case.reason,case.name)
      for _,settled in ipairs(settled_seen) do t.eq(settled,'true',case.name..': settled') end  -- the caller wraps the call in pcall
      t.eq(rebound>0,case.rebound,case.name..': rebound');t.eq(state.manual_hold==nil,case.released,case.name..': released');t.eq(asked,case.asked,case.name..': asked')
    end
  end)
  T.publish,pair.save,pair.resume_running,pair.ledger_hold,pair.reserve_rebound,T.committed_recovery_decision=real.publish,real.save,real.resume,real.hold,real.rebound,real.decide
  T.bind_policy_context=real.bind
  pair.policy.metadata,pair.policy.current_role,pair.policy.state_order_matches=real.metadata,real.role,real.matches
  if not ok then error(err,0) end
end)

-- The incident, decision by decision, with the real resolve_pair, streak, return gate and stable_success
local R=DATA.replay
local T0=1793797580
local SETTINGS=canon.object({interval='30',plan_source=PRIMARY,plan_target=RESERVE,plan_source_tunnel='wireguard:wgclient1',plan_target_tunnel='openvpn:ovpnclient1'})
local function changed_of(role) return n(role=='source' and R.primary_rebuilt or R.reserve_rebuilt) end
local function generation_of(role,at)
  if role=='source' then return at>=changed_of(role) and P_NEW or P_OLD end
  return at>=changed_of(role) and NEW or OLD
end
local function status_at(at)
  local now=T0+at
  local rows,groups,samples={},{},{}
  for _,pairing in ipairs({{'source',PRIMARY},{'target',RESERVE}}) do
    local role,id=pairing[1],pairing[2]
    local changed=changed_of(role)
    local after=at>=changed
    local state=(after and at<changed+n(R.pending)) and 'PENDING' or 'SETTLED'
    local stamp=after and T0+changed or T0-1000
    local generation=generation_of(role,at)
    local base=PROOFS[role]
    rows[#rows+1]=row_of(base,{vendor_generation=generation,vendor_state=state,vendor_changed_at=canon.float(stamp),time=canon.float(now),code=NULL,dns_ok=true,https_success=2})
    groups[#groups+1]=canon.object({id=base.vendor_tunnel_id,protocol=base.protocol,current_profile=id,profiles=canon.array({id}),active_profiles=canon.array({id}),
      generation=generation,state=state,stable_samples=2,changed_at=canon.float(stamp),time=canon.float(now)})
    for back=0,30 do
      local when=at-10*back
      local bad=(role=='source' and n(R.cut[1])<=when and when<n(R.cut[2])) or (role=='target' and changed<=when and when<changed+n(R.pending))
      samples[#samples+1]=row_of(base,{time=canon.float(T0+when),vendor_generation=generation_of(role,when),code=bad and 'VPN-003' or NULL,dns_ok=not bad,https_success=bad and 0 or 2})
    end
  end
  return canon.object({time=canon.float(now),profiles=canon.array(rows),samples=canon.array(samples),
    vendor_observation=canon.object({version=1,time=canon.float(now),groups=canon.array(groups)})})
end

t.test('replay of the incident: the proof is rebound once, then the normal return (alpha8: HOLD for ever)',function()
  local env=t.env();deps(env)
  env.deps.resolve_pair=diagnosis.resolve_pair
  env.deps.scoped_samples=nil
  local value=canon.object({source=PRIMARY,target=RESERVE,confirmed=canon.float(T0+n(R.committed)),vendor_profiles=canon.object({source=PROOFS.source,target=PROOFS.target})})
  local current
  env.backend.health=function() return true end
  env.backend.recovery_ready=function(id,settings)
    local policy=pair.recovery_normalized(settings)
    local age=pair.valid_for(settings)
    local now=n(current.time)
    local resolved=diagnosis.resolve_pair(current,settings,canon.float(now),age,pair.settle_for(settings))
    local row=nil
    for _,role in ipairs({'source','target'}) do if not none(resolved[role]) and resolved[role].id==id then row=resolved[role] end end
    return resolved.coordination.state=='READY' and row~=nil
      and pair.stable_success(pair.scoped_samples(env,current.samples,row),id,policy.primary_successes,pair.stable_seconds(settings,policy),now,age)
  end
  local at=n(R.first)
  local log={}
  while at<=n(R.last) do
    current=status_at(at)
    local d=T.committed_recovery_decision(env,value,row_of(SETTINGS),current.samples,n(current.time),current,n(R.hold))
    log[#log+1]={at,d.action,d.reason,d.rebind==true}
    if d.rebind then value.vendor_profiles.target=row_of(PROOFS.target,{vendor_generation=NEW}) end
    if d.action=='RESTORE-PRIMARY' then break end
    at=at+n(R.step)
  end
  -- rebound once, after the vendor went quiet and two new samples passed (a short hold while the vendor rebuilds the
  -- primary too), then the normal return. alpha8: HOLD RESERVE-IDENTITY-UNKNOWN from 230 to the end.
  local steps={}
  for _,row in ipairs(log) do
    local last=steps[#steps]
    if not last or last[2]~=row[2] or last[3]~=row[3] or last[4]~=row[4] then steps[#steps+1]=row end
  end
  local expect={}
  for i,row in ipairs(R.expect) do expect[i]={n(row[1]),row[2],row[3],row[4]} end
  t.eq(#steps,#expect,'steps')
  for i,row in ipairs(expect) do t.eq(steps[i],row,'step '..i) end
end)

-- pair.reserve_rebound on the real journal and the tick's hook, a RUNNING session with a COMMITTED journal
local function committed()
  local env=t.env()
  local B=env.backend
  B.devices=function() return {'ovpnclient1','wgclient1'} end
  B.health=function() return true end
  B.recovery_ready=function() return true end
  env.net={network=function() return canon.array({}) end,identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,
    changed=function() return false end}
  local sel=B.selection
  local id=string.rep('11',16)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=id,request_source='manual'})))
  pair.save(env,canon.object({id=id,phase='RUNNING',ran=true,started=canon.float(env.run.wall()-600),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({'wgclient1','ovpnclient1'}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)}))
  T.attempt(env,sel,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
  t.eq(T.journal_read(env).phase,'COMMITTED')
  return env
end
local function rebuilt(env,fields)
  local sel=env.backend.selection
  sel.source=row_of(sel.source,{vendor_generation=string.rep('d',32)})
  sel.target=row_of(sel.target,fields or {vendor_generation=string.rep('c',32)})
  sel.vendor_identity=string.rep('e',64)
end
local function quiet_log() local durable=require('durable');local log=durable.log;durable.log=function() end;return function() durable.log=log end end

t.test('reserve_rebound: the journal follows both generations, once',function()
  local restore=quiet_log()
  local env=committed();rebuilt(env)
  t.eq(pair.reserve_rebound(env,env.revision),true)
  local j=T.journal_read(env)
  t.eq({j.vendor_profiles.target.vendor_generation,j.vendor_profiles.source.vendor_generation,j.vendor_identity,j.phase},
       {string.rep('c',32),string.rep('d',32),string.rep('e',64),'COMMITTED'})
  t.eq(pair.reserve_rebound(env,env.revision),false,'once')
  restore()
end)

t.test('reserve_rebound: nothing is written without proof',function()
  local restore=quiet_log()
  local function unchanged(env,message)
    local before=canon.encode(T.journal_read(env))
    t.eq(pair.reserve_rebound(env,env.revision),false,message)
    t.eq(canon.encode(T.journal_read(env)),before,message)
  end
  local env=committed();rebuilt(env)
  local busy=env.backend.selection
  env.backend.diagnostic=function() return {'VENDOR-SETTLING'},busy end
  unchanged(env,'the vendor is not quiet')
  env=committed();rebuilt(env,{interface='ovpnclient2',vendor_tunnel_id='openvpn:ovpnclient2'});unchanged(env,'another tunnel')
  env=committed();rebuilt(env);env.backend.selection.vendor_identity=NULL;unchanged(env,'no vendor identity')
  env=committed();rebuilt(env);env.backend.selection.source=row_of(env.backend.selection.source,{id='wireguard:peer_9'});unchanged(env,'another primary')
  restore()
end)

t.test('reserve_rebound: a Stop wins',function()
  local restore=quiet_log()
  local env=committed();rebuilt(env)
  local before=canon.encode(T.journal_read(env))
  ctl.current_revision(env)
  local real=T.require_control_revision
  T.require_control_revision=function() error(setmetatable({code='CLIENT-STOP'},ctl.Refused),0) end
  local ok=pcall(pair.reserve_rebound,env,env.revision)
  T.require_control_revision=real
  t.eq(ok,false);t.eq(canon.encode(T.journal_read(env)),before)
  restore()
end)

t.test('reserve_rebound: a primary hold rebinds a ROLLED-BACK journal, the automatic path does not',function()
  local restore=quiet_log()
  local env=committed();rebuilt(env)
  local j=T.journal_read(env);j.phase='ROLLED-BACK';j.restored_order=j.before;T.journal_write(env,j)
  t.eq(pair.reserve_rebound(env,env.revision),false,'not settled=true')
  t.eq(pair.reserve_rebound(env,env.revision,true),true)
  j=T.journal_read(env)
  t.eq({j.vendor_profiles.target.vendor_generation,j.phase},{string.rep('c',32),'ROLLED-BACK'})
  restore()
end)

t.test('a manual hold on an unknown reserve ends with the guarded return of the tick',function()
  local restore=quiet_log()
  local env=committed();rebuilt(env);deps(env)
  env.backend.selection.target.vendor_changed_at=canon.float(env.run.wall()-200)
  local state=pair.read_state(env);state.manual_hold='target';state.manual_hold_source='manual';pair.save(env,state)
  env.run.advance(120)
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({samples=canon.array({})})))
  env.backend.settings=row_of(env.backend.settings,{failure_model='consecutive'})
  local ok,err=pcall(pair.tick,env,env.backend.settings,env.revision)
  restore()
  assert(ok,tostring(type(err)=='table' and err.code or err))
  local j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'ROLLED-BACK','PRIMARY-STABLY-RECOVERED'});t.eq(pair.read_state(env).manual_hold,nil)
end)

t.test('the tick rebinds on a proven rebuild only',function()
  local restore=quiet_log()
  local real_decide,real_rebound=T.committed_recovery_decision,pair.reserve_rebound
  local calls=0
  local ok,err=pcall(function()
    for _,row in ipairs({{{action='OBSERVE',reason='CLIENT-CONFIRMED',rebind=true},1},{{action='OBSERVE',reason='CLIENT-CONFIRMED'},0},
                         {{action='HOLD',reason='RESERVE-IDENTITY-UNKNOWN',reserve_healthy=NULL},0}}) do
      local env=committed()
      calls=0
      T.committed_recovery_decision=function() return row[1] end
      pair.reserve_rebound=function() calls=calls+1;return true end
      local tok,terr=pcall(pair.tick,env,env.backend.settings,env.revision)
      assert(tok,tostring(type(terr)=='table' and terr.code or terr))
      t.eq(calls,row[2],row[1].reason)
    end
  end)
  T.committed_recovery_decision,pair.reserve_rebound=real_decide,real_rebound
  restore()
  if not ok then error(err,0) end
end)

t.test('the tick: the rebuilt reserve is rebound by the real decision; an unknown one returns through the guarded path',function()
  local restore=quiet_log()
  local env=committed();rebuilt(env)
  deps(env)
  local sel=env.backend.selection
  sel.target.vendor_changed_at=canon.float(env.run.wall()-200);sel.source.vendor_changed_at=canon.float(env.run.wall()-200)
  env.run.advance(120)
  local now=env.run.wall()
  local samples={}
  for i=0,2 do samples[#samples+1]=row_of(sel.target,{time=canon.float(now-10*i),code=NULL,dns_ok=true,https_success=2}) end
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({samples=canon.array(samples)})))
  env.backend.settings=row_of(env.backend.settings,{failure_model='consecutive'})
  env.backend.recovery_ready=function() return false end
  local before=T.journal_read(env).vendor_profiles.target.vendor_generation
  assert(pcall(pair.tick,env,env.backend.settings,env.revision))
  local j=T.journal_read(env)
  t.eq(before==j.vendor_profiles.target.vendor_generation,false,'rebound');t.eq(j.vendor_profiles.target.vendor_generation,string.rep('c',32))
  t.eq(j.phase,'COMMITTED')
  -- no samples of the new generation: unknown; the primary stable: the real finish_committed brings the traffic back
  env=committed();rebuilt(env);deps(env)
  env.backend.selection.target.vendor_changed_at=canon.float(env.run.wall()-200)
  env.run.advance(120)
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({samples=canon.array({})})))
  env.backend.settings=row_of(env.backend.settings,{failure_model='consecutive'})
  assert(pcall(pair.tick,env,env.backend.settings,env.revision))
  restore()
  j=T.journal_read(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.reason,'PRIMARY-STABLY-RECOVERED');t.eq(env.backend.uci,{'r1','r2'})
end)

t.run()
