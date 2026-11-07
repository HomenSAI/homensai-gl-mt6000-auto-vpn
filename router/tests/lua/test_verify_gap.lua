-- Verification gap: no BLOCKED flicker right after a confirmed pass (MT3000 cut 07.11.2026, alpha8).
-- The owner's page showed BLOCKED without a reason, without an active channel, for 2-3 s about 12 s after COMMITTED and
-- 27 s after the return; then the confirmed state came back by itself. Cause: pair.reapply_missing_policy (and the tick's
-- own diagnostic) published BLOCKED for a pass whose diagnostic() answered only a short vendor wait (VENDOR-WORKER-BUSY:
-- a GL worker holding its lock, at most 2.3 s in the lock study of 05.11.2026). Now such a pass keeps the last confirmed
-- publication with verifying=true while the earlier kernel proof is inside its 15 s validity; a real blocker, or a wait
-- outliving the proof, is still published BLOCKED.
-- Shared cases: ../verify_gap_cases.json; Python twin: tests/test_verify_gap.py (pair_auto, the same sequence).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local DATA=canon.decode(read_file(t.here..'/../verify_gap_cases.json'))
local function clone(v) return canon.decode(canon.encode(v)) end

t.test('verify_gap: the shared cases (verify_gap_cases.json)',function()
  for _,case in ipairs(DATA.cases) do
    local previous=clone(DATA.base)
    if case.previous then for k,v in pairs(case.previous) do previous[k]=v end end
    if case.path then for k,v in pairs(case.path) do previous.channel_path[k]=v end end
    local roles=case.roles or canon.object({source_id=DATA.source,target_id=DATA.target})
    local got=pair.verify_gap(previous,clone(case.blockers),case.now,roles)
    local want=case.expect
    if want==NULL or want==nil then t.eq(got,nil,case.name)
    else
      t.truthy(got,case.name..': kept')
      t.eq({got.state,got.reason},{want.state,want.reason},case.name)
      t.eq({got.source,got.target},{previous.source,previous.target},case.name)
      t.eq(got.blockers,canon.array({}),case.name..': a kept state carries no blocker')
      t.eq(got.verify_blockers,case.blockers,case.name)
      t.eq(got.verifying,true,case.name)
      t.eq(canon.number(got.verifying_since),canon.number(want.since),case.name..': since')
      t.eq({got.readiness_verified,got.kernel_policy_verified},{false,false},case.name..': this pass verified nothing')
      local proof=got.kernel_proof
      t.eq({proof.verified,proof.role,canon.number(proof.time)},{true,want.role,canon.number(want.proof_time)},case.name..': the earlier proof, never renewed')
      t.eq(proof.profile_id,previous.channel_path.active_profile_id,case.name)
      for _,key in ipairs({'time','channel_path','transition_completed','route_changed','transition_outcome'}) do t.eq(got[key],nil,case.name..' '..key) end
    end
  end
end)

-- a running session on the primary (r1 first), the real tick and T.publish with the monitor's from_kernel
local PRIMARY,RESERVE='wireguard:peer_1','openvpn:1_1'
local function session()
  local env=t.env()
  local sel=env.backend.selection
  env.deps.from_kernel=require('monitor_status').from_kernel
  local attest=env.backend.attest_policy
  env.backend.attest_policy=function(s)
    local proof=attest(s)
    if proof.verified==true then proof.profile_id=proof.role=='source' and PRIMARY or RESERVE end
    return proof
  end
  local now=env.run.wall()
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(now),id=string.rep('11',16),request_source='manual'})))
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='0'}),canon.object({['.name']='ovpnclient1',disabled='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function() return false end}
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(now-1000),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)})
  pair.save(env,state)
  sel.source.vendor_changed_at=canon.float(now-1000);sel.target.vendor_changed_at=canon.float(now-1000)
  local logged={}
  local durable=require('durable');local log=durable.log
  durable.log=function(line) logged[#logged+1]=line end
  return env,logged,function() durable.log=log end
end
-- the monitor's samples, fresh at every pass: primary_ok false = three consecutive failures of the primary
local function samples(env,primary_ok)
  local sel=env.backend.selection;local now=env.run.wall();local rows={}
  for _,id in ipairs({PRIMARY,RESERVE}) do
    local ok=id==RESERVE or primary_ok
    for i=0,2 do rows[#rows+1]=canon.object({id=id,time=canon.float(now-i*10),code=ok and NULL or 'VPN-003',dns_ok=ok,https_success=ok and 2 or 0,
      interface=id==PRIMARY and 'wgclient1' or 'ovpnclient1',vendor_tunnel_id=id==PRIMARY and 'wireguard:wgclient1' or 'openvpn:ovpnclient1',
      vendor_generation=id==PRIMARY and sel.source.vendor_generation or sel.target.vendor_generation}) end
  end
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(now),samples=canon.array(rows),profiles=canon.array({})})))
end
local function tick(env,advance,blockers,primary_ok)
  env.run.advance(advance or 2)
  env.backend.blockers=blockers or {}
  samples(env,primary_ok~=false)
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  return t.read(env,env.runtime..'/native-status.json')
end
local function confirmed(status,active,checked,message)
  local path=status.channel_path
  t.eq({path.confirmed,path.kernel_policy_verified,path.active_profile_id},{true,true,active},message)
  t.eq(canon.number(path.checked_at),canon.number(checked),message..': checked_at')
  -- the page's single reading (monitor_status.channel_path_fallback / channel_path.supervisor_kernel) agrees
  local page=require('monitor_status').channel_path_fallback(status,canon.number(status.time))
  t.eq({page.confirmed,page.active_profile_id},{true,active},message..': page projection')
end

t.test('tick: a short vendor wait after a confirmed pass keeps OBSERVING; a long one is BLOCKED',function()
  local env,logged,restore=session()
  local ok,err=pcall(function()
    local status=tick(env,0)
    t.eq({status.state,status.reason},{'OBSERVING','PAIR-WATCHING'})
    confirmed(status,PRIMARY,env.run.wall(),'first pass');local proof=env.run.wall()
    -- the MT3000 rows 210.0 (BLOCKED, reason None, no channel) and 212.0: one or two busy passes
    status=tick(env,2,{'VENDOR-WORKER-BUSY'})
    t.eq({status.state,status.reason,status.blockers},{'OBSERVING','PAIR-WATCHING',canon.array({})},'kept: '..t.show(status))
    t.eq({status.verifying,status.verify_blockers,canon.number(status.verifying_since)},{true,canon.array({'VENDOR-WORKER-BUSY'}),env.run.wall()})
    t.eq({status.kernel_policy_verified,status.readiness_verified},{false,false},'this pass verified nothing')
    confirmed(status,PRIMARY,proof,'gap pass');local since=env.run.wall()
    status=tick(env,2,{'VENDOR-WORKER-BUSY'})
    t.eq({status.state,canon.number(status.verifying_since)},{'OBSERVING',since});confirmed(status,PRIMARY,proof,'second gap pass')
    t.eq(#logged,1,'one log line per gap');t.truthy(string.find(logged[1],'PAIR-VERIFY-GAP: VENDOR-WORKER-BUSY',1,true),logged[1])
    -- the wait ends: the next pass attests again, without the flag
    status=tick(env,2)
    t.eq({status.state,status.reason,status.verifying},{'OBSERVING','PAIR-WATCHING',nil});confirmed(status,PRIMARY,env.run.wall(),'after the gap')
    proof=env.run.wall()
    -- a wait that outlives the 15 s proof validity is published BLOCKED, as before
    local states={}
    for i=1,8 do states[i]=tick(env,2,{'VENDOR-WORKER-BUSY'}).state end
    t.eq(states,{'OBSERVING','OBSERVING','OBSERVING','OBSERVING','OBSERVING','OBSERVING','OBSERVING','BLOCKED'},'kept for 14 s of proof age, BLOCKED at 16 s')
    status=t.read(env,env.runtime..'/native-status.json')
    t.eq(status.blockers,canon.array({'VENDOR-WORKER-BUSY'}));t.eq(status.channel_path.active_profile_id,NULL)
    t.truthy(env.run.wall()-proof>pair.VERIFY_GAP_SECONDS)
    t.eq(tick(env,2,{'VENDOR-WORKER-BUSY'}).state,'BLOCKED','never back to a kept state without a new attestation')
    status=tick(env,2);t.eq(status.state,'OBSERVING');confirmed(status,PRIMARY,env.run.wall(),'recovered')
    -- a real blocker is published at once
    status=tick(env,2,{'TERMS-NOT-ACCEPTED'})
    t.eq({status.state,status.blockers},{'BLOCKED',canon.array({'TERMS-NOT-ACCEPTED'})});t.eq(status.channel_path.confirmed,false)
    tick(env,2)
    t.eq(tick(env,2,{'VENDOR-WORKER-BUSY','VENDOR-CODE-CHANGED'}).state,'BLOCKED')
  end)
  restore()
  if not ok then error(err,0) end
end)

t.test('tick: the MT3000 sequence - failover, COMMITTED, a busy pass 12 s later keeps COMMITTED',function()
  local env,logged,restore=session()
  local ok,err=pcall(function()
    local status=tick(env,0)
    t.eq(status.state,'OBSERVING')
    -- the primary fails (three consecutive failures, a healthy reserve): the own transition
    tick(env,2,nil,false)
    local j=t.journal(env)
    t.eq(j.phase,'COMMITTED','the failover committed');t.eq(env.backend.kernel,{'r2','r1'})
    status=tick(env,2,nil,false)
    t.eq(status.state,'COMMITTED',t.show(status));confirmed(status,RESERVE,env.run.wall(),'committed pass')
    local reason,proof=status.reason,env.run.wall()
    -- 12 s after the commit the pass meets a vendor worker for one pass (row 36.0 of the cut)
    status=tick(env,2,{'VENDOR-WORKER-BUSY'},false)
    t.eq({status.state,status.reason,status.verifying},{'COMMITTED',reason,true},t.show(status))
    t.eq(status.blockers,canon.array({}));confirmed(status,RESERVE,proof,'gap pass on the reserve')
    t.eq(t.journal(env).phase,'COMMITTED','a gap pass decides nothing')
    status=tick(env,2,nil,false)
    t.eq({status.state,status.verifying},{'COMMITTED',nil});confirmed(status,RESERVE,env.run.wall(),'after the gap')
    t.eq(#logged,1)
  end)
  restore()
  if not ok then error(err,0) end
end)

t.run()
