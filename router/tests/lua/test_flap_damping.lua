-- Flap damping: the attempt limit never blocks leaving a failed primary; it slows the return instead.
-- MT3000 flap test 02.11.2026 (2.1.0-alpha5, primary 60 s down / 120 s up, 10 times): after three failovers the
-- budget refused the outages at ~547/728/906 s (traffic stayed on the dead primary, PAIR-RATE-LIMIT) while every
-- recovery still returned after ~70 s. Python twin: tests/test_flap_damping.py (flap_damping_cases.json).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local T=require('transaction')

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../flap_damping_cases.json')).cases

t.test('return_hold: the shared cases',function()
  for _,case in ipairs(CASES) do
    local got=pair.return_hold(case.events,case.now,pair.recovery_normalized(case.settings))
    t.eq(got,case.hold,case.name)
  end
end)

t.test('charge_attempt: unlimited for a failover, the cooldown spacing still applies',function()
  local env=t.env()
  local path=env.persist..'/pair-auto-budget.json'
  local now=env.run.wall()
  env.run.fs.write_atomic(path,canon.encode(canon.object({events=canon.array({canon.float(now-300),canon.float(now-200),canon.float(now-100)})})))
  t.code('PAIR-RATE-LIMIT',pair.charge_attempt,env,t.settings(),env.revision)
  pair.charge_attempt(env,t.settings(),env.revision,false)
  t.eq(#t.read(env,path).events,4)
  env.run.advance(59)
  t.code('PAIR-RATE-LIMIT',pair.charge_attempt,env,t.settings(),env.revision,false)
  t.eq(#t.read(env,path).events,4)
end)

t.test('ledger_hold: from the ledger; an unreadable ledger holds the longest',function()
  local env=t.env();local now=env.run.wall();local path=env.persist..'/pair-auto-budget.json'
  t.eq(pair.ledger_hold(env,t.settings(),now),120,'default primary_stable 120 s since 03.11.2026')
  t.eq(pair.ledger_hold(env,t.settings({recovery_primary_stable='30'}),now),30)
  env.run.fs.write_atomic(path,canon.encode(canon.object({events=canon.array({canon.float(now-600),canon.float(now-400),canon.float(now-100)})})))
  t.eq(pair.ledger_hold(env,t.settings(),now),240)
  t.eq(pair.ledger_hold(env,t.settings({recovery_primary_stable='30'}),now),60)
  env.run.fs.write_atomic(path,canon.encode(canon.object({events=canon.array({-1})})))
  t.eq(pair.ledger_hold(env,t.settings(),now),pair.HOLD_CAP)
end)

t.test('committed_recovery_decision: damped return, failing reserve, cooldown',function()
  local env=t.env()
  local asked={}
  local ready_upto=60
  env.backend.recovery_ready=function(id,settings) local s=pair.stable_seconds(settings);asked[#asked+1]=s;return s<=ready_upto end
  local reserve_failed=false
  local real_streak=pair.streak
  pair.streak=function(...) return reserve_failed end
  local function decide(hold,now,settings)
    local value=canon.object({source='wireguard:peer_1',target='openvpn:1_1',confirmed=canon.float(900)})
    -- pair.streak is stubbed: the previous rule (failure_model 'consecutive') decides the reserve's failure;
    -- the damping mechanism is checked on its 30 s base (the default before 03.11.2026)
    settings=settings or canon.object({recovery_primary_stable='30'})
    if settings.failure_model==nil then settings.failure_model='consecutive' end
    return T.committed_recovery_decision(env,value,settings,canon.array({}),now or 1000,canon.object({}),hold)
  end
  local ok,err=pcall(function()
    t.eq(decide(30).reason,'PRIMARY-STABLY-RECOVERED')
    t.eq(decide(60).reason,'PRIMARY-STABLY-RECOVERED')
    local d=decide(120);t.eq({d.action,d.reason},{'OBSERVE','PAIR-RATE-LIMIT'});t.eq(asked[#asked],120)
    t.eq(decide(nil).reason,'PRIMARY-STABLY-RECOVERED')
    ready_upto=30;reserve_failed=true
    t.eq(decide(600).reason,'RESERVE-FAILED-PRIMARY-VERIFIED')
    reserve_failed=false;ready_upto=600
    local cool=canon.object({recovery_cooldown='300',recovery_primary_stable='30'})
    t.eq(decide(30,1100,cool).action,'OBSERVE');t.eq(decide(30,1200,cool).action,'RESTORE-PRIMARY')
    t.eq(decide(nil,1100,cool).action,'RESTORE-PRIMARY')
  end)
  pair.streak=real_streak
  if not ok then error(err,0) end
end)

-- pair.tick every 10 s with the real transaction (fake instant switch) and the real committed return: the primary
-- is down 60 s / up 120 s, ten times; the reserve stays healthy.
local DOWN,UP,CYCLES=60,120,10
local function num_time(row) return canon.number(row.time) end
local function flap(settings_over,cycles)
  local CYCLES=cycles or CYCLES
  local env=t.env({settings=t.settings(settings_over)})  -- the transaction reads backend.policy().settings
  local sel=env.backend.selection
  local start=env.run.wall()
  sel.source.vendor_changed_at=canon.float(start-1000);sel.target.vendor_changed_at=canon.float(start-1000)
  local function primary_up(at) local o=at-start-30;return o<0 or o>=(DOWN+UP)*CYCLES or o%(DOWN+UP)>=DOWN end
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(start),id=string.rep('11',16),request_source='manual'})))
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='0'}),canon.object({['.name']='ovpnclient1',disabled='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function() return false end}
  pair.save(env,canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(start-1000),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)}))
  local rows={}
  env.backend.recovery_ready=function(id,settings)
    local policy=pair.recovery_normalized(settings)
    return pair.stable_success(canon.array(rows),id,policy.primary_successes,pair.stable_seconds(settings,policy),env.run.wall(),30)
  end
  local settings=t.settings(settings_over)
  local log={switches={},returns={},reserve={},holds={}}
  local stop=start+30+(DOWN+UP)*CYCLES+300
  while env.run.wall()<stop do
    local now=env.run.wall();local up=primary_up(now)
    rows[#rows+1]=canon.object({id=sel.source.id,time=canon.float(now),code=up and canon.null or 'VPN-003',dns_ok=up,https_success=up and 2 or 0,
      interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',vendor_generation=t.GEN1})
    rows[#rows+1]=canon.object({id=sel.target.id,time=canon.float(now),code=canon.null,dns_ok=true,https_success=2,interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2})
    while #rows>0 and num_time(rows[1])<now-900 do table.remove(rows,1) end  -- the monitor keeps a bounded window
    local profiles=canon.array({canon.object({id=sel.source.id,interface='wgclient1',time=canon.float(now),code=up and canon.null or 'VPN-003',dns_ok=up,https_success=up and 2 or 0,vendor_state='SETTLED'}),
      canon.object({id=sel.target.id,interface='ovpnclient1',time=canon.float(now),code=canon.null,dns_ok=true,https_success=2,vendor_state='SETTLED'})})
    env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(now),samples=canon.array(rows),profiles=profiles})))
    local c1=os.clock()
    local before=env.backend.kernel[1]
    local hold=pair.ledger_hold(env,settings,now)
    t.eq(pair.tick(env,settings,env.revision),true)
    log.tick=(log.tick or 0)+os.clock()-c1
    local after=env.backend.kernel[1]
    if before=='r1' and after=='r2' then log.switches[#log.switches+1]=now-start end
    if before=='r2' and after=='r1' then
      local since=now;while primary_up(since-10) and since-10>=start do since=since-10 end
      log.returns[#log.returns+1]={now-start,now-since,hold}
    end
    log.reserve[now-start]=(after=='r2')
    if os.getenv('FLAP_DEBUG2') then local st=t.read(env,env.runtime..'/native-status.json') or {};io.stderr:write(now-start,' ',tostring(st.state),' ',tostring(st.reason),' ',canon.encode(st.blockers or canon.array({})),' ',tostring((t.journal(env) or {}).phase),'\n') end
    env.run.advance(10)
  end
  if os.getenv('FLAP_DEBUG') then io.stderr:write('tick cpu ',log.tick,' total ',os.clock(),'\n') end
  return log,start
end

local function outages(cycles) local out={};for k=0,(cycles or CYCLES)-1 do out[#out+1]=30+k*(DOWN+UP) end;return out end

local cache={}
local function flap_cached(over,cycles)
  -- the damping mechanism is checked on its 30 s base (the default before 03.11.2026)
  if over.recovery_primary_stable==nil then over.recovery_primary_stable='30' end
  local key=over.recovery_attempt_limit..'/'..cycles..'/'..over.recovery_primary_stable
  cache[key]=cache[key] or flap(over,cycles)
  return cache[key]
end

t.test('flap 60/120 x10: every outage is left for the reserve',function()
  for _,limit in ipairs({'3','1'}) do
    -- the default run is shared with the next test (each simulated tick runs the whole Lua transaction)
    local cycles=limit=='3' and CYCLES or 6
    local log=flap_cached({recovery_attempt_limit=limit},cycles)
    for _,down in ipairs(outages(cycles)) do
      for at=down+40,down+DOWN-10,10 do
        if not log.reserve[at] then error('limit '..limit..': traffic on the dead primary at '..at..' s; switches '..table.concat(log.switches,','),0) end
      end
    end
  end
end)

t.test('flap 60/120 x10: returns wait progressively longer, never faster than the hold, and the hold decays',function()
  local log=flap_cached({recovery_attempt_limit='3'},CYCLES)
  local longest,count=0,0
  for _,r in ipairs(log.returns) do
    count=count+1
    if r[2]<r[3] then error('returned after '..r[2]..' s of primary health, hold '..r[3],0) end
    if r[3]>longest then longest=r[3] end
  end
  t.eq(log.returns[1][3],30)
  t.truthy(longest>=120,'the hold grew: '..longest)
  t.truthy(count<CYCLES,'damping kept the reserve through a recovery: '..count..' returns')
  local last=0;for k in pairs(log.reserve) do if k>last then last=k end end
  t.eq(log.reserve[last],false,'back on the primary once the flaps stop')
end)

t.test('flap 60/120 x4 with the defaults of 03.11.2026 (primary_stable 120 s): one failover, every outage covered',function()
  local cycles=4
  local log=flap(canon.object({recovery_attempt_limit='3'}),cycles)
  for _,down in ipairs(outages(cycles)) do
    for at=down+40,down+DOWN-10,10 do
      if not log.reserve[at] then error('traffic on the dead primary at '..at..' s; switches '..table.concat(log.switches,','),0) end
    end
  end
  t.eq(#log.switches,1,'switches '..table.concat(log.switches,','))
  t.eq(#log.returns,1,'one return once the flaps stop')
  local last=0;for k in pairs(log.reserve) do if k>last then last=k end end
  t.eq(log.reserve[last],false,'back on the primary once the flaps stop')
end)

t.run()
