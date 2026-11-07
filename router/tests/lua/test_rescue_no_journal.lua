-- Owner decision 07.11.2026 (F-80), the path WITHOUT an open journal: hold_reserve keeps a WORKING reserve only.
-- The session carries traffic on the reserve per selected_policy (after a boot, after an accepted manual selection), no
-- journal is open, so pair.tick decides the return itself. A reserve the detector calls failed is probed once
-- (backend.health); only a FRESH NEGATIVE probe opens the rescue rule (rescue_stable) through the same pair_return
-- attempt and cooldown; an unknown probe holds (RESERVE-HEALTH-UNKNOWN), an alive probe observes.
-- Shared cases: ../rescue_no_journal_cases.json; Python twin: tests/test_rescue_no_journal.py (pair_auto.tick).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local T=require('transaction')

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../rescue_no_journal_cases.json')).cases
local PRIMARY,RESERVE='wireguard:peer_1','openvpn:1_1'

local function run_case(case)
  local env=t.env()
  local sel=env.backend.selection
  -- the kernel order r2,r1 puts the reserve rule first: the session carries traffic on the reserve (role target), no journal
  env.backend.uci={'r2','r1'};env.backend.kernel={'r2','r1'};sel.order=canon.array({'r2','r1'})
  local now=env.run.wall()
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(now),id=string.rep('11',16),request_source='manual'})))
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='0'}),canon.object({['.name']='ovpnclient1',disabled='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function() return false end}
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(now-1000),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r2','r1'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel),selected_policy=canon.object({role='target',order=canon.array({'r2','r1'}),hash=t.HEX64,since=canon.float(now-1000)})})
  pair.save(env,state)
  local events={}
  for i,x in ipairs(case.events or {}) do events[i]=canon.float(now+x) end
  env.run.fs.write_atomic(env.persist..'/pair-auto-budget.json',canon.encode(canon.object({events=canon.array(events)})))
  local good={[PRIMARY]=not case.primary_failed,[RESERVE]=not case.reserve_failed}
  local rows={}
  for _,id in ipairs({PRIMARY,RESERVE}) do
    local ok=good[id]
    for i=0,2 do rows[#rows+1]=canon.object({id=id,time=canon.float(now-i*10),code=ok and canon.null or 'VPN-003',dns_ok=ok,https_success=ok and 2 or 0,
      interface=id==PRIMARY and 'wgclient1' or 'ovpnclient1',vendor_tunnel_id=id==PRIMARY and 'wireguard:wgclient1' or 'openvpn:ovpnclient1',
      vendor_generation=id==PRIMARY and sel.source.vendor_generation or t.GEN2}) end
  end
  sel.source.vendor_changed_at=canon.float(now-1000);sel.target.vendor_changed_at=canon.float(now-1000)
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(now),samples=canon.array(rows),profiles=canon.array({})})))
  local probes,asked,dispatched={},{},{}
  local health={[PRIMARY]=true}
  if case.reserve_health~='unknown' then health[RESERVE]=(case.reserve_health==nil) and true or case.reserve_health end
  env.backend.health=function(id) probes[#probes+1]=id;return health[id] end
  env.backend.recovery_ready=function(id,settings) local s=pair.stable_seconds(settings);asked[#asked+1]=s;return id==PRIMARY and s<=case.ready_upto end
  local attempt=T.attempt
  T.attempt=function(env_,sel_,until_,trial,opts) opts.on_dispatch();dispatched[#dispatched+1]=opts end
  local function count() local n=0;for _,id in ipairs(probes) do if id==RESERVE then n=n+1 end end;return n end
  -- BH-06: steps = {{monotonic seconds, reserve_failed}, ...} ticks of one session; default one tick
  local per_step,reasons={},{}
  local ok,err=pcall(function()
    for _,step in ipairs(case.steps or {{nil,case.reserve_failed}}) do
      if step[1]~=nil then env.run.mono_now=step[1] end
      local failed=step[2]
      local rows2={}
      for _,row in ipairs(rows) do
        local r=canon.decode(canon.encode(row))
        if r.id==RESERVE then r.code=failed and 'VPN-003' or canon.null;r.dns_ok=not failed;r.https_success=failed and 0 or 2 end
        rows2[#rows2+1]=r
      end
      env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(now),samples=canon.array(rows2),profiles=canon.array({})})))
      t.eq(pair.tick(env,t.settings(case.settings),env.revision),true)
      per_step[#per_step+1]=count()
      local st=t.read(env,env.runtime..'/native-status.json')
      reasons[#reasons+1]=st and st.reason or false
    end
  end)
  T.attempt=attempt
  if not ok then error(err,0) end
  return {reserve_probes=count(),per_step=per_step,reasons=reasons,asked=asked,dispatched=dispatched,status=t.read(env,env.runtime..'/native-status.json'),
    ledger=t.read(env,env.persist..'/pair-auto-budget.json'),now=now}
end

t.test('no-journal path: the shared cases (rescue_no_journal_cases.json)',function()
  for _,case in ipairs(CASES) do
    local got=run_case(case)
    t.eq(got.reserve_probes,case.probed and 1 or 0,case.name..': the one fresh probe of the reserve')
    if case.asked==canon.null or case.asked==nil then t.eq(#got.asked,0,case.name..': the primary is not asked')
    else t.eq(got.asked[1],case.asked,case.name..': the stability asked of the primary') end
    t.eq(#got.dispatched,case.dispatch and 1 or 0,case.name..': dispatch '..t.show(got.status))
    if case.dispatch then
      local sent=got.dispatched[1]
      t.eq(sent.pair_return,true,case.name);t.eq(sent.pair_destination,'source',case.name)
      t.eq(sent.pair_session_order,canon.array({'r2','r1'}),case.name)
      local events=got.ledger.events
      t.eq(canon.encode(events[#events]),canon.encode(canon.float(got.now)),case.name..': the return is charged (cooldown spacing)')
    else
      t.eq({got.status.state,got.status.reason},{case.state,case.reason},case.name)
      t.eq(got.status.blockers,canon.array({}),case.name)
    end
  end
end)

t.test('no-journal path: the rescue waits for the cooldown after its own dispatch',function()
  local case=CASES[1]
  t.eq(#run_case(case).dispatched,1)
  local again={};for k,v in pairs(case) do again[k]=v end
  again.events={0}
  local got=run_case(again)
  t.eq(#got.dispatched,0);t.eq(got.reserve_probes,0,'inside the cooldown nothing is probed')
end)

t.test('BH-06: a dead reserve is probed once per interval of one failure episode',function()
  local I=pair.RESCUE_PROBE_INTERVAL
  for _,v in ipairs({{false,'RESERVE-FAILED'},{'unknown','RESERVE-HEALTH-UNKNOWN'}}) do
    local case={name='bh06',settings={recovery_return_policy='hold_reserve'},reserve_failed=true,reserve_health=v[1],ready_upto=0,dispatch=false,
      steps={{1000,true},{1010,true},{1000+I-1,true},{1000+I,true},{1000+I+5,true},{1000+I+10,false},{1000+I+20,true}}}
    local got=run_case(case)
    t.eq(got.per_step,{1,1,1,2,2,2,3},v[2])
    t.eq(#got.dispatched,0,v[2])
    for i,r in ipairs(got.reasons) do if i~=6 then t.eq(r,v[2],v[2]..' step '..i) end end
  end
end)

t.run()
