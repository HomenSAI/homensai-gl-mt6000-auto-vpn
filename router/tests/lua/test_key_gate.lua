-- The directional gate of the server keys (independent review of 71053c32, findings 1 and 2; option server_key_pin 'enforce').
-- Python twin with the reasons: tests/test_key_gate.py. The real backend.key_unaccepted: tests/test_lua_backend.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local A=require('auto')
local pair=require('pair')
local manual=require('manual')
local CODE='SERVER-KEY-UNACCEPTED'
local P1,R1='wireguard:peer_1','openvpn:1_1'

local function keyed(env,...)
  local bad={}
  for _,id in ipairs({...}) do bad[id]=true end
  env.backend.key_unaccepted=function(profiles)
    for _,id in ipairs(profiles) do if bad[id] then return CODE end end
    return nil
  end
  return bad
end

-- a running pair session on the fake router, past (selected) or before its first proof of the route
local function session(env,selected)
  local sel=env.backend.selection
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=string.rep('11',16),request_source='manual'})))
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='0'}),canon.object({['.name']='ovpnclient1',disabled='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function() return false end}
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(env.run.wall()-10),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)})
  if selected then state.selected_policy=canon.object({role='source',order=canon.array({'r1','r2'}),hash=t.HEX64,since=canon.float(env.run.wall()-1000)}) end
  pair.save(env,state)
  env.run.fs.write_atomic(env.runtime..'/status.json','{"samples":[],"profiles":[]}')
end

local function source_dies(env)
  local sel=env.backend.selection
  local now=env.run.wall();local rows={}
  for i=0,2 do rows[#rows+1]=canon.object({id=P1,time=canon.float(now-i*10),code='VPN-001',interface='wgclient1',vendor_tunnel_id=sel.source.vendor_tunnel_id,vendor_generation=sel.source.vendor_generation}) end
  for i=0,1 do rows[#rows+1]=canon.object({id=R1,time=canon.float(now-i*10),code=canon.null,dns_ok=true,https_success=2,interface='ovpnclient1',vendor_tunnel_id=sel.target.vendor_tunnel_id,vendor_generation=sel.target.vendor_generation}) end
  sel.source.vendor_changed_at=canon.float(now-1000);sel.target.vendor_changed_at=canon.float(now-1000)
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({samples=canon.array(rows),profiles=canon.array({})})))
end

local function pass(env) return A.iteration(env,{last_return=0,consumed=canon.object({}),last_attempt=0}) end
local function native(env) return t.read(env,env.runtime..'/native-status.json') end

t.test('finding 2: a changed key on the primary does not keep the pair on it',function()
  local env=t.env();session(env,true);keyed(env,P1);source_dies(env)
  t.eq(pass(env),'nap')
  t.eq(t.journal(env).phase,'COMMITTED');t.eq(env.backend.kernel,{'r2','r1'})
  local ledger=t.read(env,env.persist..'/pair-auto-budget.json')
  t.eq(#ledger.events,1);t.eq(ledger.others,nil,'finding 5: the failover of a tick counts as one')
end)

t.test('a changed key on the reserve keeps the pair off it: refused with its code, nothing prepared',function()
  local env=t.env();session(env,true);keyed(env,R1);source_dies(env)
  t.eq(pass(env),'nap')
  t.eq(next(t.journal(env)),nil,'no transaction');t.eq(env.backend.kernel,{'r1','r2'});t.eq(#env.backend.leases,0)
  local row=native(env);t.eq({row.state,row.reason},{'BLOCKED',CODE});t.eq(row.blockers,canon.array({CODE}))
end)

t.test('a refused failover keeps the owner hold',function()
  local env=t.env();session(env,true);keyed(env,R1);source_dies(env)
  local state=pair.read_state(env);state.manual_hold='source';pair.save(env,state)
  pass(env)
  t.eq(pair.read_state(env).manual_hold,'source')
end)

t.test('a working pair with a changed key goes on watching',function()
  for _,id in ipairs({P1,R1}) do
    local env=t.env();session(env,true);keyed(env,id)
    t.eq(pass(env),'nap');t.eq(native(env).state,'OBSERVING',id)
  end
end)

t.test('a Start waits for the owner on a key of the carrying channel; his word lets it go on by itself',function()
  local env=t.env();session(env,false);local bad=keyed(env,P1)
  t.eq(pass(env),'nap')
  t.eq(native(env).state,'BLOCKED');t.eq(native(env).blockers,canon.array({CODE}));t.eq(pair.read_state(env).selected_policy,nil)
  bad[P1]=nil
  t.eq(pass(env),'nap')
  t.eq(native(env).state,'OBSERVING');t.eq(pair.read_state(env).selected_policy.role,'source')
end)

t.test('a key seen on the other channel while the Start ran leaves no BLOCKED session',function()
  local env=t.env();session(env,false);keyed(env,R1)
  t.eq(pass(env),'nap')
  t.eq(native(env).state,'OBSERVING');t.eq(pair.read_state(env).selected_policy.role,'source')
end)

-- the rule of a Start (owner 05.11.2026): the live order names the channel that must be clean; Python twin: class Carrying
t.test('the live order names the channel; an order that proves no role counts both',function()
  local env=t.env();local sel=env.backend.selection
  keyed(env,R1);t.eq(T.carrying_unaccepted(env,sel),nil,'the source carries')
  keyed(env,P1);t.eq(T.carrying_unaccepted(env,sel),CODE)
  env.backend.uci={'r2','r1'}
  keyed(env,P1);t.eq(T.carrying_unaccepted(env,sel),nil,'the reserve carries')
  keyed(env,R1);t.eq(T.carrying_unaccepted(env,sel),CODE)
  for _,order in ipairs({function() error('no',0) end,function() return {'x','y'},'h' end}) do
    env.backend.order=order
    for _,id in ipairs({P1,R1}) do keyed(env,id);t.eq(T.carrying_unaccepted(env,sel),CODE,id) end
  end
  env.backend.key_unaccepted=nil
  t.eq(T.carrying_unaccepted(env,sel),nil,'no pinning, no gate')
end)

-- Review 05.11.2026: a real Start through the real pair.begin; the fake net counts everything begin would touch.
local function clicked(env,id)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=id,request_source='manual'})))
  local touched={}
  local function touch(name) return function() touched[#touched+1]=name end end
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='1',proto='wgclient',auto='0'}),canon.object({['.name']='ovpnclient1',disabled='1',proto='ovpnclient',auto='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,client_down=function() return false end,
    quiet=touch('quiet'),set_disabled=touch('set_disabled'),ifup=touch('ifup'),static_firewall_digest=function() return string.rep('ab',32) end}
  env.run.fs.write_atomic(env.runtime..'/status.json','{"samples":[],"profiles":[]}')
  return touched
end

t.test('a Start with a key on the carrying channel takes nothing and ends with its code; after the owner\'s word a new Start runs',function()
  for _,row in ipairs({{P1,{'r1','r2'}},{R1,{'r2','r1'}}}) do
    local id=row[1]
    local env=t.env();local bad=keyed(env,id)
    env.backend.uci=row[2];env.backend.kernel=row[2];env.backend.selection.order=canon.array(row[2])
    local request=string.rep('11',16)
    local touched=clicked(env,request)
    t.eq(pass(env),'nap')
    t.eq(#env.backend.guard_calls,0,'no guard');t.eq(env.backend.guarded,false);t.eq(#touched,0,'no client touched')
    t.eq(next(pair.read_state(env)),nil,'no session');t.eq(next(t.journal(env)),nil);t.eq(env.backend.kernel,row[2])
    local intent=pair.intent(env)
    t.eq({intent.mode,intent.failed_request_id,intent.failure_code},{'off',request,CODE})
    t.eq(native(env).state,'BLOCKED');t.eq(native(env).blockers,canon.array({CODE}))
    pass(env)
    t.eq(#env.backend.guard_calls,0,'the next pass begins nothing either')
    bad[id]=nil
    local again=clicked(env,string.rep('22',16))
    pass(env)
    t.eq(pair.read_state(env).phase,'RUNNING');t.truthy(#env.backend.guard_calls>0);t.truthy(#again>0,'this one starts the clients')
  end
end)

t.test('a Start with a key on the channel not carrying runs; a failover onto that channel is still refused',function()
  for _,row in ipairs({{R1,{'r1','r2'}},{P1,{'r2','r1'}}}) do
    local env=t.env();keyed(env,row[1])
    env.backend.uci=row[2];env.backend.kernel=row[2];env.backend.selection.order=canon.array(row[2])
    local touched=clicked(env,string.rep('11',16))
    pass(env)
    t.eq(pair.read_state(env).phase,'RUNNING');t.truthy(#env.backend.guard_calls>0);t.truthy(#touched>0,'the clients start')
    t.eq(pair.intent(env).failure_code,nil)
  end
  local env=t.env();keyed(env,R1)
  clicked(env,string.rep('11',16))
  pass(env)
  source_dies(env)
  pass(env)
  t.eq(next(t.journal(env)),nil,'no transaction');t.eq(env.backend.kernel,{'r1','r2'})
  local row=native(env);t.eq({row.state,row.reason},{'BLOCKED',CODE})
end)

t.test('a Start with clean keys of the pair is not refused for another profile',function()
  local env=t.env();keyed(env,'wireguard:peer_9')
  clicked(env,string.rep('11',16))
  pass(env)
  t.eq(pair.read_state(env).phase,'RUNNING')
end)

t.test('finding 1: a Stop on the reserve with an unaccepted key ends rolled back',function()
  for _,ids in ipairs({{P1},{R1},{P1,R1}}) do
    local env=t.env();session(env,true);source_dies(env)
    t.eq(pass(env),'nap');t.eq(t.journal(env).phase,'COMMITTED')
    keyed(env,unpack(ids))
    env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='off',revision=env.revision,time=canon.float(env.run.wall())})))
    env.net.ifdown=function() end;env.net.quiet=function() end;env.net.set_disabled=function() end;env.net.interface_exists=function() return false end
    t.eq(pass(env),'nap')
    t.eq(t.journal(env).phase,'ROLLED-BACK');t.eq(env.backend.uci,{'r1','r2'});t.eq(pair.read_state(env).phase,'STOPPED')
    t.eq(native(env).state,'STOPPED')
  end
end)

t.test('the committed decision: the reverse of finding 2 and a primary with an unaccepted key',function()
  local env=t.env()
  env.backend.recovery_ready=function() return true end
  local health=false
  env.backend.health=function() return health end
  local failed=true
  local real=pair.streak
  pair.streak=function() return failed end
  local value=canon.object({source=P1,target=R1,confirmed=canon.float(900)})
  local settings=canon.object({failure_model='consecutive'})
  local function decide(seconds) return T.committed_recovery_decision(env,value,settings,canon.array({}),seconds or 1000,canon.object({}),nil) end
  local ok,err=pcall(function()
    keyed(env,R1)   -- on the reserve with a changed key, the reserve dies, a clean primary
    local d=decide();t.eq({d.action,d.reason},{'RESTORE-PRIMARY','RESERVE-FAILED-PRIMARY-VERIFIED'})
    keyed(env,P1)   -- the key of the primary: no return, the reason says why
    d=decide();t.eq({d.action,d.reason},{'HOLD',CODE})
    failed=false;health=true
    d=decide();t.eq({d.action,d.reason},{'OBSERVE',CODE})
    env.backend.recovery_ready=function() return false end
    t.eq(decide().reason,'CLIENT-CONFIRMED','nothing was due: nothing to explain')
  end)
  pair.streak=real
  if not ok then error(err,0) end
end)

t.test('the doors: attempt refuses before any write, a repair of the carrying channel and a move away pass',function()
  local env=t.env();keyed(env,R1)
  local charged=0
  local opts={control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),on_dispatch=function() charged=charged+1 end}
  t.code(CODE,T.attempt,env,env.backend.selection,env.run.wall()+3600,false,opts)
  t.eq(next(t.journal(env)),nil);t.eq(charged,0);t.eq(env.backend.uci,{'r1','r2'})
  keyed(env,P1)
  T.attempt(env,env.backend.selection,env.run.wall()+3600,false,opts)
  t.eq(t.journal(env).phase,'COMMITTED','away from it');t.eq(charged,1)
end)

t.test('the doors: a return onto it and a manual click towards it',function()
  local env=t.env();keyed(env,P1)
  local sel=env.backend.selection
  t.code(CODE,T.attempt,env,sel,env.run.wall()+3600,false,{control_revision=env.revision,pair_destination='source',pair_return=true,pair_session_order=canon.array({'r2','r1'})})
  t.code(CODE,manual.instant_manual,env,sel,env.run.wall()+3600,env.revision,string.rep('a',32),'manual','source',canon.array({'r1','r2'}))
  t.eq(next(t.journal(env)),nil)
end)

t.test('operator_return: the owner asking to move is refused, the end of a Stop is not',function()
  local env=t.env();keyed(env,P1)
  local value=canon.object({phase='HELD-ON-RESERVE',source=P1,target=R1})
  t.eq(T.operator_return(env,value,nil,nil),CODE)
  local rollback=require('rollback')
  local real=rollback.rollback;local called=0
  rollback.rollback=function() called=called+1 end
  env.backend.health=function() return true end
  local ok,err=pcall(function() t.eq(T.operator_return(env,value,'PRIMARY-RECOVERED',nil),nil) end)
  rollback.rollback=real
  if not ok then error(err,0) end
  t.eq(called,1)
end)

t.test('without the backend method (an older fake, a fallback) the gate is open',function()
  local env=t.env();env.backend.key_unaccepted=nil
  t.eq(T.key_unaccepted(env,P1),nil)
  local seen
  env.backend.key_unaccepted=function(list) seen=list end
  T.key_unaccepted(env,P1,nil,canon.null,R1)
  t.eq(seen,{P1,R1},'only real ids reach the gate')
end)

t.run()
