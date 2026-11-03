-- Stages 2 and 3 of the best-server pick (2.1.0-alpha2/alpha3): the Auto supervisor changes the idle reserve's server itself, inside
-- its control lock, and re-binds its own session - no PAIR-EXTERNAL-*/SOURCE-ORDER-MISMATCH, no PAIR-READOPTED (MT3000
-- 02.11.2026: a change from outside the pair cost the working channel a 7.1 s LAN stall). Python twin:
-- tests/test_pair_server_pick.py (the same world and decisions).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local S=require('server_pick')
local T=require('transaction')
local P=pair.policy
local NULL=canon.null

local H1,H2=string.rep('ab',32),string.rep('cd',32)
local SID=string.rep('11',16)
local UCI_RULE="route_policy.cfg0456cd=rule\nroute_policy.cfg0456cd.tunnel_id='4192'\nroute_policy.cfg0456cd.via_type='openvpn'\n"..
  "route_policy.cfg0456cd.via='ovpnclient1'\nroute_policy.cfg0456cd.group_id='40354'\nroute_policy.cfg0456cd.client_id='%s'\n"..
  "route_policy.cfg0456cd.profiles='/etc/vpn_profiles.d/profile4192'\nroute_policy.cfg0456cd.mark='0xb000'\n"..
  "route_policy.cfg0123ab=rule\nroute_policy.cfg0123ab.tunnel_id='5841'\nroute_policy.cfg0123ab.via_type='wireguard'\nroute_policy.cfg0123ab.via='wgclient1'\n"..
  "route_policy.cfg0123ab.group_id='10004'\nroute_policy.cfg0123ab.peer_id='%s'\nroute_policy.cfg0123ab.profiles='/etc/vpn_profiles.d/profile5841'\nroute_policy.cfg0123ab.mark='0x1000'\n"

local GEN3=string.rep('03',16)
-- the rule ids, the policy hash and the uci digests of a (reserve client, primary peer) pair of servers
local function rule_of(kind,id) if (kind=='r2' and id=='2020') or (kind=='r1' and id=='2002') then return kind end;return kind..'_'..id end
local function hash_of(client,peer)
  if peer=='2002' then return client=='2020' and H1 or H2 end
  return canon.sha256('policy:'..client..'/'..peer)
end

-- the router: uci of both rules and their interfaces; a commit of route_policy renames the anonymous rule whose server
-- changed (in the uci order and in the kernel order, wherever it is); the monitor sees the new profile
local function world(opts)
  opts=opts or {}
  local sel=t.selection({source=canon.object({id='wireguard:peer_2002',protocol='wireguard',interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',vendor_generation=t.GEN1}),
    target=canon.object({id='openvpn:40354_2020',protocol='openvpn',interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2})})
  local settings=t.settings({server_pick='1',plan_source_tunnel='wireguard:wgclient1',plan_target_tunnel='openvpn:ovpnclient1'})
  local env=t.env({selection=sel,settings=settings})
  local W={client='2020',config='40354_2020',peer='2002',wgconfig='peer_2002',wg_digest=string.rep('0',64),staged={},exec={},logs={},files={},health={},provider={},ready={}}
  local B=env.backend
  B.health=function(id) return W.health[id] end
  B.recovery_ready=function(id) W.ready[#W.ready+1]=id;return W.health[id]==true end
  B.trace_of['wireguard:peer_2002']='198.51.100.1';B.trace_of['openvpn:40354_2020']='203.0.113.5'
  local function rename(list,old,new) local out={};for i,x in ipairs(list) do out[i]=(x==old) and new or x end;return out end
  local function commit_route_policy()
    local before_r1,before_r2=rule_of('r1',W.peer),rule_of('r2',W.client)
    if W.staged.client then W.client=W.staged.client;W.staged.client=nil end
    if W.staged.peer then W.peer=W.staged.peer;W.staged.peer=nil end
    local r1,r2=rule_of('r1',W.peer),rule_of('r2',W.client)
    B.uci=rename(rename(B.uci,before_r1,r1),before_r2,r2);B.kernel=rename(rename(B.kernel,before_r1,r1),before_r2,r2);B.hash=hash_of(W.client,W.peer)
    B.selection.source_rule=r1;B.selection.target_rule=r2;local live={};for i,x in ipairs(B.uci) do live[i]=x end;B.selection.order=canon.array(live)
    B.selection.generic_rules=canon.array({r1,r2});B.selection.hash=B.hash
  end
  local function commit_network()
    if W.staged.config then W.config=W.staged.config;W.staged.config=nil;B.selection.target.id='openvpn:'..W.config end
    if W.staged.wgconfig then
      W.wgconfig=W.staged.wgconfig;W.staged.wgconfig=nil
      B.selection.source.id='wireguard:'..W.wgconfig;B.selection.source.vendor_generation=W.wgconfig=='peer_2002' and t.GEN1 or GEN3
      B.trace_of[B.selection.source.id]='198.51.100.1'
    end
  end
  env.server_io={runtime=env.runtime,
    read=function(path) return W.files[path] end,
    write=function(path,text) W.files[path]=text;return true end,
    alive=function() return false end,
    log=function(line) W.logs[#W.logs+1]=line end,
    exec=function(argv)
      local line=table.concat(argv,' ');W.exec[#W.exec+1]=line
      if line=='uci -q -X show route_policy' then return 0,string.format(UCI_RULE,W.client,W.peer) end
      local client=string.match(line,'^uci set route_policy%.cfg0456cd%.client_id=(%d+)$')
      if client then W.staged.client=client end
      local peer=string.match(line,'^uci set route_policy%.cfg0123ab%.peer_id=(%d+)$')
      if peer then W.staged.peer=peer end
      local config=string.match(line,'^uci set network%.ovpnclient1%.config=([%d_]+)$')
      if config then W.staged.config=config end
      local wgconfig=string.match(line,'^uci set network%.wgclient1%.config=(peer_%d+)$')
      if wgconfig then W.staged.wgconfig=wgconfig end
      if argv[1]=='sh' and argv[4]=='update_provider_config' then
        W.provider[#W.provider+1]=argv[5]..'/'..argv[6]..'/'..argv[7];W.wg_digest=canon.sha256('wg:'..argv[6])  -- GL may rewrite /etc/config/wireguard
      end
      if line=='uci commit route_policy' then if opts.fail_commit then opts.fail_commit=nil;return 1,'' end;commit_route_policy() end
      if line=='uci commit network' then commit_network() end
      return 0,''
    end}
  local function net_digest(c,wg) if wg=='peer_2002' then return canon.sha256('net:'..c) end;return canon.sha256('net:'..c..'/'..wg) end
  W.net_digest=net_digest
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',config=W.wgconfig,disabled='0'}),canon.object({['.name']='ovpnclient1',config=W.config,disabled='0'})}) end,
    identity=function(rows) local c,wg;for _,r in ipairs(rows) do if r['.name']=='ovpnclient1' then c=r.config else wg=r.config end end;return net_digest(c,wg) end,
    configs=function() return canon.object({route_policy=canon.sha256('rp:'..W.client..(W.peer=='2002' and '' or '/'..W.peer)),wireguard=W.wg_digest}) end,
    changed=function() return false end,client_down=function() return false end,forget=function() end}
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=SID,request_source='manual'})))
  local state=canon.object({id=SID,phase='RUNNING',ran=true,started=canon.float(env.run.wall()-1000),revision=env.revision,network_identity=canon.sha256('net:40354_2020'),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({route_policy=canon.sha256('rp:2020'),wireguard=string.rep('0',64)}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=H1,policy_roles=P.proof(sel),
    selected_policy=canon.object({role='source',order=canon.array({'r1','r2'}),hash=H1,since=canon.float(env.run.wall()-900)})})
  pair.save(env,state)
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(env.run.wall()),samples=canon.array({}),profiles=canon.array({})})))
  W.request=function(over)
    local row=canon.object({time=env.run.wall(),tunnel_id=4192,protocol='openvpn',interface='ovpnclient1',section='cfg0456cd',from='40354_2020',to='40354_2016',
      group_id='40354',profile_id='2016',from_ms=48,to_ms=21,from_location='Kyiv',to_location='Berlin'})
    for k,v in pairs(over or {}) do row[k]=v end
    W.files[env.runtime..'/'..S.CHANGE]=canon.encode(row)
  end
  W.status=function() return t.read(env,env.runtime..'/native-status.json') end
  W.writes=function() local n=0;for _,line in ipairs(W.exec) do if string.find(line,'^uci set') or string.find(line,'^ifdown') or string.find(line,'^ifup') then n=n+1 end end;return n end
  return env,W,settings
end

local function no_readopt(env)
  t.eq(t.read(env,env.runtime..'/pair-readopt.json'),nil,'no readopt')
  t.eq(pair.intent(env).id,SID,'the same Auto request (no re-arm)')
  t.eq(pair.read_state(env).id,SID)
end

t.test('the idle reserve gets the new server inside the session: no external change, no readopt',function()
  local env,W,settings=world()
  W.request()
  t.eq(pair.tick(env,settings,env.revision),true)
  t.eq(W.exec,{'uci -q -X show route_policy','uci set route_policy.cfg0456cd.client_id=2016','uci -q delete route_policy.cfg0456cd.peer_id','uci set route_policy.cfg0456cd.group_id=40354',
    'uci set network.ovpnclient1.config=40354_2016','uci set network.ovpnclient1.disabled=0','uci commit route_policy','uci commit network','ifdown ovpnclient1','ifup ovpnclient1'})
  local state=pair.read_state(env)
  t.eq(state.order,{'r1','r2_2016'});t.eq(state.policy_hash,H2);t.eq(state.network_identity,canon.sha256('net:40354_2016'))
  t.eq(state.protected.route_policy,canon.sha256('rp:2016'),'the protected route_policy digest follows');t.eq(state.protected.wireguard,string.rep('0',64))
  t.eq(state.policy_roles.target_rule,'r2_2016');t.eq(state.policy_roles.target_id,'openvpn:40354_2016');t.eq(state.policy_roles.generic_rules,{'r1','r2_2016'})
  t.eq(canon.encode(state.policy_roles),canon.encode(P.proof(env.backend.selection)),'the roles equal a fresh proof of the new selection')
  t.eq(state.selected_policy.order,{'r1','r2_2016'});t.eq(state.selected_policy.hash,H2)
  t.eq(state.server_change.phase,'CONNECTING');t.eq(state.server_change.to.id,'openvpn:40354_2016');t.eq(state.server_change.from,canon.object({group_id='40354',profile_id='2020'}))
  t.eq(W.status().reason,'SERVER-CHANGING');t.eq(W.status().state,'OBSERVING')
  t.eq(canon.decode(W.files[env.runtime..'/'..S.STATE]).changes['4192'],{env.run.wall()},'the attempt counts for the hourly limit')
  no_readopt(env)
  -- the tunnel is not up yet: the pair waits, nothing else is decided, nothing is written
  local before=#W.exec
  env.run.advance(5);t.eq(pair.tick(env,settings,env.revision),true);t.eq(#W.exec,before);t.eq(W.status().reason,'SERVER-CHANGING')
  -- the new server passes the pair's own check through the tunnel: SERVER-PICKED, then the monitor sees the profile
  W.health['openvpn:40354_2016']=true
  env.run.advance(5);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq(pair.read_state(env).server_change.phase,'SETTLING')
  local event=canon.decode(W.files[env.runtime..'/'..S.EVENT]);t.eq(event.tunnels[1].code,'SERVER-PICKED')
  t.eq(W.logs[#W.logs],'SERVER-PICKED: server of the channel changed (tunnel 4192 openvpn): Kyiv -> Berlin, 48 -> 21 ms')
  t.eq(canon.decode(W.files[env.runtime..'/'..S.STATE]).last['4192'].to,'40354_2016')
  env.run.advance(2);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq(pair.read_state(env).server_change,nil,'the diagnostic is clear: the change is finished')
  local status=W.status()
  t.eq({status.state,status.reason,status.target},{'OBSERVING','PAIR-WATCHING','openvpn:40354_2016'},'the normal pass, no EXTERNAL code')
  t.eq(pair.read_state(env).phase,'RUNNING')
  no_readopt(env)
  t.eq(W.writes(),6,'the hand-off is taken once')
end)

t.test('refused while the tunnel carries traffic, while Auto is not at rest, over the limit, with the owner switch off',function()
  -- the requested tunnel carries the traffic (the kernel proves the primary role on the requested interface)
  local env,W,settings=world()
  W.request({interface='wgclient1',protocol='wireguard',section='cfg0123ab',tunnel_id=5841,from='10004_2002',to='10004_2000',group_id='10004',profile_id='2000'})
  t.truthy(S.claim(env.server_io,canon.decode(W.files[env.runtime..'/'..S.CHANGE]),env.run.wall())~=nil,'a live hand-off, refused only as carrying')
  t.eq(pair.tick(env,settings,env.revision),true);t.eq(W.writes(),0);t.eq(W.status().reason,'PAIR-WATCHING')
  -- on the reserve (the kernel role target): the reserve carries
  env,W,settings=world();W.request()
  env.backend.kernel={'r2','r1'};env.backend.uci={'r2','r1'}
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,canon.object({})),false);t.eq(W.writes(),0)
  -- a transaction in progress
  env,W,settings=world();W.request()
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,canon.object({phase='APPLYING'})),false);t.eq(W.writes(),0)
  -- a manual hold
  env,W,settings=world();W.request()
  local state=pair.read_state(env);state.manual_hold='source'
  t.eq(pair.server_start(env,state,settings,env.revision,canon.object({})),false);t.eq(W.writes(),0)
  -- four changes in the last hour: SERVER-PICK-LIMIT once per hand-off
  env,W,settings=world();W.request()
  local now=env.run.wall()
  W.files[env.runtime..'/'..S.STATE]=canon.encode(canon.object({changes=canon.object({['4192']=canon.array({now-100,now-200,now-300,now-400})}),last=canon.object({})}))
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,canon.object({})),false);t.eq(W.writes(),0)
  t.eq(canon.decode(W.files[env.runtime..'/'..S.EVENT]).tunnels[1].code,'SERVER-PICK-LIMIT')
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,canon.object({})),false);t.eq(#W.logs,1,'the same refusal is logged once')
  -- the owner switch off: the hand-off is not even read
  env,W,settings=world();W.request();settings.server_pick='0'
  t.eq(pair.tick(env,settings,env.revision),true);t.eq(#W.exec,0)
  -- the reserve bound by its profile id only (no tunnel anchor): never changed
  env,W,settings=world();W.request();settings.plan_target_tunnel=NULL
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,canon.object({})),false);t.eq(W.writes(),0)
  -- a stale hand-off (the server moved meanwhile)
  env,W,settings=world();W.request({from='40354_2011'})
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,canon.object({})),false);t.eq(W.writes(),0)
end)

t.test('a new server that fails the check is rolled back the same way: SERVER-PICK-FAILED',function()
  local env,W,settings=world()
  W.request()
  t.eq(pair.tick(env,settings,env.revision),true)
  W.health['openvpn:40354_2016']=false
  for _=1,6 do env.run.advance(10);t.eq(pair.tick(env,settings,env.revision),true) end
  local state=pair.read_state(env)
  t.eq(state.server_change.phase,'SETTLING');t.eq(state.server_change.rolled_back,true)
  t.eq(state.order,{'r1','r2'});t.eq(state.policy_hash,H1);t.eq(state.policy_roles.target_id,'openvpn:40354_2020');t.eq(state.network_identity,canon.sha256('net:40354_2020'))
  t.eq(state.protected.route_policy,canon.sha256('rp:2020'))
  t.eq(W.exec[#W.exec-8],'uci set route_policy.cfg0456cd.client_id=2020')
  t.eq(W.logs[#W.logs],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 4192 openvpn): Kyiv -> Berlin, 48 -> 21 ms; rolled back')
  t.eq(canon.decode(W.files[env.runtime..'/'..S.EVENT]).tunnels[1].code,'SERVER-PICK-FAILED')
  env.run.advance(2);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq(pair.read_state(env).server_change,nil);t.eq(W.status().reason,'PAIR-WATCHING')
  no_readopt(env)
end)

t.test('a failed step is undone at once; a ROLLED-BACK journal is renamed with the session',function()
  local env,W,settings=world({fail_commit=true})
  W.request()
  t.eq(pair.tick(env,settings,env.revision),true)
  local state=pair.read_state(env)
  t.eq(state.server_change.rolled_back,true);t.eq(state.order,{'r1','r2'});t.eq(state.policy_hash,H1)
  t.eq(W.logs[#W.logs],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 4192 openvpn): Kyiv -> Berlin, 48 -> 21 ms; rolled back')
  -- a finished return (ROLLED-BACK with its pair context) follows the rename: the cleanup's session check holds
  env,W,settings=world()
  local sel=env.backend.selection
  local ctx=P.transition(sel,canon.array({'r1','r2'}),'target')
  local journal=canon.object({tx=string.rep('cc',16),phase='ROLLED-BACK',before=canon.array({'r1','r2'}),after=canon.array({'r2','r1'}),restored_order=canon.array({'r1','r2'}),
    hash=H1,source=sel.source.id,target=sel.target.id,pair_transition=ctx})
  local value,renamed=S.rebind(pair.read_state(env),journal,canon.array({'r1','r2_2016'}),H2,'openvpn:40354_2016')
  t.eq(P.metadata(renamed).session_order,value.order);t.eq(renamed.hash,value.policy_hash);t.eq(renamed.after,{'r2_2016','r1'})
  t.eq(P.state_order_matches(value,renamed,canon.array({'r1','r2_2016'}),H2),true)
end)

------------------------------------------------------------------------------------------------------
-- stage 3 (2.1.0-alpha3): the failed PRIMARY gets the best live server while the traffic is on the reserve (journal
-- COMMITTED); the normal return rules then bring the traffic back to the primary on its new server
------------------------------------------------------------------------------------------------------
local A=require('auto')

-- the primary fails, Auto moves the traffic to the reserve (a real transaction: journal COMMITTED, kernel r2 first)
local function on_reserve(env,W,settings)
  W.health['wireguard:peer_2002']=false;W.health['openvpn:40354_2020']=true
  local state=pair.read_state(env)
  T.attempt(env,env.backend.selection,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=state.order,
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
  local j=t.journal(env)
  t.eq(j.phase,'COMMITTED');t.eq(env.backend.kernel,{'r2','r1'});t.eq(j.source,'wireguard:peer_2002')
  t.eq(pair.tick(env,settings,env.revision),true)
  t.eq({W.status().state,W.status().reason},{'COMMITTED','CLIENT-CONFIRMED'},'on the reserve, the primary not ready')
  t.eq(pair.read_state(env).selected_policy.role,'target')
end

local function primary_request(W)
  W.request({interface='wgclient1',protocol='wireguard',section='cfg0123ab',tunnel_id=5841,from='10004_2002',to='10004_2000',group_id='10004',profile_id='2000',
    from_ms=NULL,to_ms=35,from_location='Berlin',to_location='Frankfurt'})
end

local function reserve_untouched(W)
  for _,line in ipairs(W.exec) do t.truthy(not string.find(line,'ovpnclient1',1,true) and not string.find(line,'cfg0456cd.',1,true),'the carrying reserve is never touched: '..line) end
end

t.test('stage 3: the failed primary gets the new server while the reserve carries; the return comes back on it',function()
  local env,W,settings=world()
  on_reserve(env,W,settings)
  primary_request(W)
  t.eq(pair.tick(env,settings,env.revision),true)
  t.eq(W.exec,{'uci -q -X show route_policy','uci set route_policy.cfg0123ab.peer_id=2000','uci -q delete route_policy.cfg0123ab.client_id','uci set route_policy.cfg0123ab.group_id=10004',
    'uci set network.wgclient1.config=peer_2000','uci set network.wgclient1.disabled=0','uci commit route_policy','uci commit network',
    'sh -c '..S.PROVIDER_SCRIPT..' update_provider_config 10004 2000 wgclient1','ifdown wgclient1','ifup wgclient1'})
  t.eq(W.provider,{'10004/2000/wgclient1'},'update_provider_config as in tunnel-switch.sh')
  reserve_untouched(W)
  local state=pair.read_state(env)
  local H3=canon.sha256('policy:2020/2000')
  t.eq(state.order,{'r1_2000','r2'});t.eq(state.policy_hash,H3)
  t.eq(state.policy_roles.source_rule,'r1_2000');t.eq(state.policy_roles.source_id,'wireguard:peer_2000');t.eq(state.policy_roles.target_id,'openvpn:40354_2020')
  t.eq(canon.encode(state.policy_roles),canon.encode(P.proof(env.backend.selection)),'the roles equal a fresh proof of the new selection')
  t.eq(state.selected_policy.order,{'r2','r1_2000'});t.eq(state.selected_policy.hash,H3);t.eq(state.selected_policy.role,'target')
  t.eq(state.network_identity,W.net_digest('40354_2020','peer_2000'))
  t.eq(state.protected.route_policy,canon.sha256('rp:2020/2000'));t.eq(state.protected.wireguard,canon.sha256('wg:2000'),'the provider step may rewrite wireguard: re-recorded')
  t.eq(state.server_change.role,'source');t.eq(state.server_change.phase,'CONNECTING');t.eq(state.server_change.to.id,'wireguard:peer_2000')
  local j=t.journal(env)
  t.eq(j.phase,'COMMITTED');t.eq(j.source,'wireguard:peer_2000');t.eq(j.target,'openvpn:40354_2020');t.eq(j.hash,H3)
  t.eq(j.before,{'r1_2000','r2'});t.eq(j.after,{'r2','r1_2000'})
  t.eq(j.pair_transition.source_rule,'r1_2000');t.eq(j.pair_transition.source_id,'wireguard:peer_2000');t.eq(j.pair_transition.primary_order,{'r1_2000','r2'})
  t.eq(j.pair_transition.session_order,{'r1_2000','r2'});t.eq(j.vendor_profiles.source.id,'wireguard:peer_2000');t.eq(j.vendor_profiles.target.id,'openvpn:40354_2020')
  t.eq(P.state_order_matches(state,j,env.backend.uci,env.backend.hash),true,'the session check holds on the reserve')
  t.eq(env.backend.kernel,{'r2','r1_2000'},'the traffic stays on the reserve')
  t.eq({W.status().state,W.status().reason},{'OBSERVING','SERVER-CHANGING'})
  no_readopt(env)
  -- the new server passes the pair's check through its tunnel; the monitor then observes the new profile
  W.health['wireguard:peer_2000']=true
  env.run.advance(5);t.eq(pair.tick(env,settings,env.revision),true);t.eq(pair.read_state(env).server_change.phase,'SETTLING')
  t.eq(W.logs[#W.logs],'SERVER-PICKED: server of the channel changed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms')
  env.run.advance(2);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq(pair.read_state(env).server_change,nil)
  j=t.journal(env)
  t.eq(j.vendor_profiles.source.vendor_generation,GEN3,'the journal records the observed new profile');t.eq(j.phase,'COMMITTED')
  t.eq({W.status().state,W.status().source},{'COMMITTED','wireguard:peer_2000'},'dwell not reached yet: still on the reserve')
  -- the normal return rules: the new primary id is stably ready -> PRIMARY-STABLY-RECOVERED, back to the primary
  local asked=#W.ready
  env.run.advance(120);t.eq(pair.tick(env,settings,env.revision),true)
  j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.restored_order,{'r1_2000','r2'});t.eq(env.backend.uci,{'r1_2000','r2'});t.eq(env.backend.kernel,{'r1_2000','r2'})
  t.eq({W.status().state,W.status().reason,W.status().source},{'ROLLED-BACK','PRIMARY-STABLY-RECOVERED','wireguard:peer_2000'})
  t.truthy(#W.ready>asked,'the return asked the primary');for i=asked+1,#W.ready do t.eq(W.ready[i],'wireguard:peer_2000','the return follows the new id') end
  env.run.advance(10);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq({W.status().state,W.status().reason,W.status().source},{'OBSERVING','PAIR-WATCHING','wireguard:peer_2000'},'no EXTERNAL code after the return')
  state=pair.read_state(env)
  t.eq(state.phase,'RUNNING');t.eq(state.selected_policy.role,'source');t.eq(state.selected_policy.order,{'r1_2000','r2'})
  no_readopt(env)
  reserve_untouched(W)
end)

t.test('stage 3: refused during a transition, a manual switch or hold, held on the reserve, by profile id only; the reserve carries',function()
  local env,W,settings=world()
  on_reserve(env,W,settings)
  primary_request(W)
  local j=t.journal(env)
  local function with(fields) local out=canon.decode(canon.encode(j));for k,v in pairs(fields) do out[k]=v end;return out end
  for _,phase in ipairs({'APPLYING','WAIT-CLIENT','RESTORING','HELD-ON-RESERVE'}) do
    t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,with({phase=phase})),false,phase)
  end
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,with({manual_request_id=string.rep('ab',16)})),false,'a manual switch')
  local state=pair.read_state(env);state.manual_hold='target'
  t.eq(pair.server_start(env,state,settings,env.revision,j),false,'a manual hold')
  settings.plan_source_tunnel=NULL
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,j),false,'the primary bound by profile id only')
  settings.plan_source_tunnel='wireguard:wgclient1'
  W.request()  -- the reserve carries: never
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,j),false,'the carrying reserve')
  t.eq(W.writes(),0)
  -- and the same hand-off on the real COMMITTED journal is taken
  primary_request(W)
  t.eq(pair.server_start(env,pair.read_state(env),settings,env.revision,j),true)
  t.eq(pair.read_state(env).server_change.role,'source')
  reserve_untouched(W)
end)

t.test('stage 3: a new primary server that fails the check is rolled back; session and journal return to the old server',function()
  local env,W,settings=world()
  on_reserve(env,W,settings)
  primary_request(W)
  t.eq(pair.tick(env,settings,env.revision),true)
  W.health['wireguard:peer_2000']=false
  for _=1,6 do env.run.advance(10);t.eq(pair.tick(env,settings,env.revision),true) end
  local state=pair.read_state(env)
  t.eq(state.server_change.rolled_back,true);t.eq(state.order,{'r1','r2'});t.eq(state.policy_hash,H1);t.eq(state.policy_roles.source_id,'wireguard:peer_2002')
  t.eq(state.network_identity,canon.sha256('net:40354_2020'));t.eq(state.protected.wireguard,canon.sha256('wg:2002'))
  local j=t.journal(env)
  t.eq(j.phase,'COMMITTED');t.eq(j.source,'wireguard:peer_2002');t.eq(j.after,{'r2','r1'});t.eq(j.hash,H1);t.eq(j.vendor_profiles.source.id,'wireguard:peer_2002')
  t.eq(W.logs[#W.logs],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms; rolled back')
  t.eq(env.backend.kernel,{'r2','r1'},'the reserve carried the whole time')
  env.run.advance(2);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq(pair.read_state(env).server_change,nil);t.eq({W.status().state,W.status().reason},{'COMMITTED','CLIENT-CONFIRMED'})
  no_readopt(env)
  reserve_untouched(W)
end)

t.test('stage 3: a power cut between the uci commits and the session write; the boot restores the unverified old server',function()
  local env,W,settings=world()
  on_reserve(env,W,settings)
  -- what server_start saved before its first write, then the uci steps ran and the router lost power
  local state=pair.read_state(env)
  local tunnel={tunnel_id=5841,protocol='wireguard',section='cfg0123ab',interface='wgclient1'}
  state.server_change=canon.object({tunnel_id=5841,protocol='wireguard',section='cfg0123ab',interface='wgclient1',phase='APPLYING',role='source',
    from=canon.object({group_id='10004',profile_id='2002'}),to=canon.object({group_id='10004',profile_id='2000',id='wireguard:peer_2000'}),
    started=canon.float(env.run.wall()),deadline=canon.float(env.run.wall()+60),request=env.run.wall(),change=NULL})
  pair.save(env,state)
  t.eq(S.execute(S.switch_plan(tunnel,{group_id='10004',profile_id='2000'},true,true,false,false,1),env.server_io,true),'SERVER-PICKED')
  t.eq(env.backend.uci,{'r2','r1_2000'});t.eq(t.journal(env).after,{'r2','r1'},'the journal still names the old rule')
  W.health['wireguard:peer_2000']=true;W.health['wireguard:peer_2002']=true
  env.net.ifdown=function() end;env.net.quiet=function() end;env.net.set_disabled=function() end;env.net.interface_exists=function() return false end
  W.exec={}
  t.eq(A.recover(env),'ready')
  t.truthy(W.exec[2]=='uci set route_policy.cfg0123ab.peer_id=2002','the old server written back: '..tostring(W.exec[2]))
  local j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK','not abandoned as an external change: the Stop of the power cut returned to the primary on its old server')
  t.eq(j.source,'wireguard:peer_2002');t.eq(j.restored_order,{'r1','r2'});t.eq(env.backend.uci,{'r1','r2'});t.eq(W.peer,'2002')
  state=pair.read_state(env)
  t.eq(state.server_change,nil);t.eq(state.phase,'STOPPED');t.eq(state.order,{'r1','r2'});t.eq(state.policy_roles.source_id,'wireguard:peer_2002')
  reserve_untouched(W)
  -- only route_policy committed (the cut fell between the two commits): not explainable, today's external path
  env,W,settings=world()
  on_reserve(env,W,settings)
  state=pair.read_state(env)
  state.server_change=canon.object({tunnel_id=5841,protocol='wireguard',section='cfg0123ab',interface='wgclient1',phase='APPLYING',role='source',
    from=canon.object({group_id='10004',profile_id='2002'}),to=canon.object({group_id='10004',profile_id='2000',id='wireguard:peer_2000'}),
    started=canon.float(env.run.wall()),deadline=canon.float(env.run.wall()+60),request=env.run.wall(),change=NULL})
  pair.save(env,state)
  for _,line in ipairs({'uci set route_policy.cfg0123ab.peer_id=2000','uci commit route_policy'}) do
    local argv={};for x in string.gmatch(line,'%S+') do argv[#argv+1]=x end;env.server_io.exec(argv)
  end
  t.eq(pair.server_resume(env,pair.read_state(env)),false,'a mixed state is not adopted')
  t.eq(pair.read_state(env).server_change,nil);t.eq(t.journal(env).source,'wireguard:peer_2002')
end)

-- the supervisor start after a power cut: Auto fenced, then the server change resume (auto.recover's first steps)
local function boot(env) pair.fence_recovery(env);return pair.server_resume_boot(env) end
local D=require('durable')
local function logged() local lines={};D.log=function(line) lines[#lines+1]=line end;return lines end

-- the old primary server is live again; the session and the open journal name it; the reserve untouched
local function restored(env,W)
  local state=pair.read_state(env);local j=t.journal(env)
  t.eq(W.peer,'2002');t.eq(W.wgconfig,'peer_2002');t.eq(state.server_change,nil)
  t.eq(state.order,{'r1','r2'});t.eq(state.policy_hash,H1);t.eq(state.policy_roles.source_id,'wireguard:peer_2002')
  t.eq(j.phase,'COMMITTED');t.eq(j.source,'wireguard:peer_2002');t.eq(j.after,{'r2','r1'});t.eq(j.hash,H1)
  t.eq(P.state_order_matches(state,j,env.backend.uci,env.backend.hash),true)
  t.eq(env.backend.kernel,{'r2','r1'},'the traffic stays on the reserve')
  reserve_untouched(W)
end

t.test('stage 3: a power cut while the new server was connecting restores the old one',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  t.eq(pair.tick(env,settings,env.revision),true)
  local state=pair.read_state(env)
  t.eq({state.server_change.phase,state.policy_roles.source_id,W.peer},{'CONNECTING','wireguard:peer_2000','2000'});t.eq(state.server_change.verified,nil)
  W.exec={};local lines=logged()
  t.eq(boot(env),true)
  restored(env,W)
  t.eq({W.exec[2],W.exec[3]},{'uci set route_policy.cfg0123ab.peer_id=2002','uci -q delete route_policy.cfg0123ab.client_id'})
  t.eq(lines[#lines],'SERVER-PICK-RESUMED: adopted the recorded from server (the new one was not verified: restored)')
end)

t.test('stage 3: a power cut after the check passed keeps the new server',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  t.eq(pair.tick(env,settings,env.revision),true)
  W.health['wireguard:peer_2000']=true
  env.run.advance(5);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq({pair.read_state(env).server_change.phase,pair.read_state(env).server_change.verified},{'SETTLING',true})
  W.exec={};local lines=logged()
  t.eq(boot(env),true)
  t.eq(W.peer,'2000');t.eq(W.writes(),0,'nothing written')
  local state=pair.read_state(env);local j=t.journal(env)
  t.eq(state.server_change,nil);t.eq(state.policy_roles.source_id,'wireguard:peer_2000')
  t.eq({j.phase,j.source},{'COMMITTED','wireguard:peer_2000'});t.eq(P.state_order_matches(state,j,env.backend.uci,env.backend.hash),true)
  t.eq(lines[#lines],'SERVER-PICK-RESUMED: adopted the recorded to server')
end)

t.test('stage 3: an unverified new server whose tunnel carries the traffic is never touched',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  t.eq(pair.tick(env,settings,env.revision),true)
  local state=pair.read_state(env);state.server_change.role='target';pair.save(env,state)  -- the kernel proves the traffic on this role
  W.exec={};local lines=logged()
  boot(env)
  t.eq(W.peer,'2000');t.eq(W.writes(),0,'nothing written')
  t.truthy(string.find(lines[#lines],'(not verified; its tunnel carries the traffic)',1,true)~=nil,lines[#lines])
end)

t.test('stage 3: a rollback that raised after its uci writes is resolved by the next tick, no EXTERNAL code',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  t.eq(pair.tick(env,settings,env.revision),true)
  W.health['wireguard:peer_2000']=false;env.run.advance(61)
  local real,calls=T.journal_write,0
  T.journal_write=function(...) calls=calls+1;if calls==1 then require('auto_control').refuse('JOURNAL-WRITE-FAILED') end;return real(...) end
  local ok=pcall(pair.tick,env,settings,env.revision)
  T.journal_write=real
  t.eq(ok,true)
  local state=pair.read_state(env)
  t.eq({state.server_change.phase,state.policy_roles.source_id,W.peer},{'CONNECTING','wireguard:peer_2000','2002'},'uci holds the old server, the session the new one')
  local lines=logged()
  env.run.advance(5);t.eq(pair.tick(env,settings,env.revision),true)
  t.eq({W.status().state,W.status().reason},{'COMMITTED','CLIENT-CONFIRMED'},'no EXTERNAL code')
  restored(env,W);no_readopt(env)
  t.eq(lines[#lines],'SERVER-PICK-RESUMED: adopted the recorded from server')
end)

t.test('stage 3: the boot reads the journal again when the resume re-bound it but its session write failed',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  t.eq(pair.tick(env,settings,env.revision),true)
  W.health['wireguard:peer_2000']=true;W.health['wireguard:peer_2002']=true
  env.net.ifdown=function() end;env.net.quiet=function() end;env.net.set_disabled=function() end;env.net.interface_exists=function() return false end
  -- the restore's journal write lands, the session writes of the resume fail (flash full): the journal is re-bound alone
  local save,writes=pair.save,0
  local function failing(...) writes=writes+1;if writes<=2 then require('auto_control').refuse('STATE-WRITE-FAILED') end;return save(...) end
  local resume=pair.server_resume_boot
  pair.server_resume_boot=function(e) pair.save=failing;local ok,r=pcall(resume,e);pair.save=save;if not ok then error(r,0) end;return r end
  local ok,result=pcall(A.recover,env)
  pair.server_resume_boot=resume;pair.save=save
  t.eq({ok,result},{true,'ready'})
  local j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK','not abandoned (EXTERNAL-POLICY-CHANGE) on the stale journal');t.eq(j.source,'wireguard:peer_2002');t.eq(j.restored_order,{'r1','r2'})
  t.eq(pair.read_state(env).phase,'STOPPED');reserve_untouched(W)
end)

-- MT3000 02.11.2026 23:36 (alpha5, this runtime): the update_provider_config step raised (sys.exec refused its quotes)
-- in the change AND in its rollback; the log said `rollback failed` although uci and the session named peer 2002 again
-- and wgclient1 was never restarted. The rollback restored the old server: say so (test_pair_server_pick_stage3.py).
t.test('stage 3: the provider step failing both ways restores the old server without a restart',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  local exec=env.server_io.exec
  env.server_io.exec=function(argv,seconds)
    if argv[1]=='sh' then W.exec[#W.exec+1]=table.concat(argv,' ');error('sys: unsafe command argument',0) end
    return exec(argv,seconds)
  end
  t.eq(pair.tick(env,settings,env.revision),true)
  local shells=0
  for _,line in ipairs(W.exec) do
    t.truthy(not string.find(line,'^ifdown') and not string.find(line,'^ifup'),'the tunnel was never restarted: '..line)
    if string.find(line,'^sh %-c') then shells=shells+1 end
  end
  t.eq(shells,2,'the change and its rollback')
  t.eq(W.logs[#W.logs],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms; rolled back (the tunnel was not restarted)')
  local state=pair.read_state(env);local j=t.journal(env)
  t.eq({W.peer,W.wgconfig},{'2002','peer_2002'})
  t.eq(state.order,{'r1','r2'});t.eq(state.policy_hash,H1);t.eq(state.policy_roles.source_id,'wireguard:peer_2002')
  t.eq(j.phase,'COMMITTED');t.eq(j.source,'wireguard:peer_2002');t.eq(j.after,{'r2','r1'});t.eq(j.hash,H1)
  t.eq(state.server_change.rolled_back,true)
  reserve_untouched(W);no_readopt(env)
end)

t.test('stage 3: a rollback that cannot write uci is a failed rollback',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  local exec=env.server_io.exec;local seen=0
  env.server_io.exec=function(argv,seconds)
    local line=table.concat(argv,' ')
    if argv[1]=='sh' then W.exec[#W.exec+1]=line;return 1,'' end
    if line=='uci set route_policy.cfg0123ab.peer_id=2002' then seen=seen+1;W.exec[#W.exec+1]=line;return 1,'' end
    return exec(argv,seconds)
  end
  t.eq(pair.tick(env,settings,env.revision),true);t.eq(seen,1)
  t.truthy(string.find(W.logs[#W.logs],'; rollback failed$'),W.logs[#W.logs])
end)

t.test('stage 3: a change whose first write fails changed nothing: no rollback, nothing to wait for',function()
  local env,W,settings=world()
  on_reserve(env,W,settings);primary_request(W)
  local before=pair.read_state(env);local jb=t.journal(env)
  local exec=env.server_io.exec
  env.server_io.exec=function(argv,seconds)
    if argv[1]=='uci' and argv[2]=='set' then W.exec[#W.exec+1]=table.concat(argv,' ');return 1,'' end
    return exec(argv,seconds)
  end
  pair.tick(env,settings,env.revision)
  local writes={};for _,line in ipairs(W.exec) do if line~='uci -q -X show route_policy' then writes[#writes+1]=line end end
  t.eq(writes,{'uci set route_policy.cfg0123ab.peer_id=2000'},'no rollback')
  t.eq(W.logs[#W.logs],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms; not changed')
  local state=pair.read_state(env);local j=t.journal(env)
  t.eq(state.server_change,nil,'nothing to wait for')
  t.eq(state.order,before.order);t.eq(state.policy_hash,before.policy_hash);t.eq(state.policy_roles.source_id,before.policy_roles.source_id)
  t.eq({j.phase,j.source},{jb.phase,jb.source});t.eq(j.after,jb.after)
  t.eq(canon.decode(W.files[env.runtime..'/'..S.EVENT]).tunnels[1].code,S.FAILED)
  env.run.advance(5);pair.tick(env,settings,env.revision)
  local sets=0;for _,line in ipairs(W.exec) do if string.find(line,'^uci set') then sets=sets+1 end end
  t.eq(sets,1,'the hand-off is taken once')
  reserve_untouched(W);no_readopt(env)
end)

t.run()
