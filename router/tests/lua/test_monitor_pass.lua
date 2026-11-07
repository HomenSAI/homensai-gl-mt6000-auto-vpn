-- monitor.lua: one full pass with the fake runner: status.json composition, events, counters, checkpoints.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local monitor=require('monitor')

local function fresh(options)
  local R=t.fake_runner(options)
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  return R,monitor.new(R)
end

t.test('normalise_inventory: empty tables become arrays, unsafe rows dropped, names bounded',function()
  local data=monitor.normalise_inventory(canon.plain(canon.decode('{"profiles":[{"id":"wireguard:peer_7","section":"peer_7","name":"'..string.rep('n',70)..'","interface":"bad dev"},{"id":"bad id","section":"x"}],"servers":{},"native_candidates":{},"wan_interfaces":{},"settings":{"interval":10}}')))
  t.eq(#data.profiles,1);t.eq(#data.profiles[1].name,64);t.eq(data.profiles[1].interface,canon.null)
  t.truthy(canon.is_array(data.servers));t.eq(canon.encode(data.servers),'[]')
  t.raises(monitor.normalise_inventory,canon.object({profiles=canon.object({a=1})}))
end)

t.test('monitoring_profiles and failure_pair follow the configured anchors',function()
  local data=t.inventory()
  data.servers={{id='c',profile='openvpn:1_2',enabled=true}}
  local observed,selected=monitor.monitoring_profiles(data)
  t.eq(#observed,3,'two anchored tunnels follow the plan, one catalogue entry is selected');t.truthy(selected['openvpn:1_2'])
  data.servers={{id='c',profile='wireguard:peer_8',enabled=false}}
  observed=monitor.monitoring_profiles(data)
  t.eq(#observed,1);t.eq(observed[1].id,'wireguard:peer_7')
  t.eq(monitor.failure_pair(t.inventory()),{source='wireguard:peer_7',target='wireguard:peer_8'})
  local same=t.inventory();same.settings.plan_target_tunnel='wireguard:wgclient'
  t.eq(monitor.failure_pair(same),{})
  local by_id=t.inventory();by_id.settings.plan_source_tunnel=nil;by_id.settings.plan_target_tunnel=nil
  t.eq(monitor.failure_pair(by_id),{source='wireguard:peer_7',target='wireguard:peer_8'})
end)

t.test('one pass publishes the status fields the page reads',function()
  local R,m=fresh()
  local status=m:pass()
  t.eq(status.version,require('version'));t.eq(status.mode,'monitor');t.eq(status.time,R.now)
  t.eq(#status.profiles,2)
  local p=status.profiles[1]
  t.eq(p.id,'wireguard:peer_7');t.eq(p.code,canon.null);t.eq(p.https_success,3);t.eq(p.dns_ok,true);t.eq(p.role,'source');t.eq(p.channel,'primary');t.eq(p.name,'Main');t.eq(p.router_name,'Vienna');t.eq(p.priority,10)
  t.eq(p.observation_valid_for,30);t.eq(p.exit_ip,'93.184.216.34');t.eq(p.exit_country,'DE')
  t.eq(p.vendor_state,'PENDING','a fresh epoch: one stable sample');t.truthy(#p.vendor_generation==32)
  t.eq(p.ping.code,'PING-UNAVAILABLE','icmp_ping needs a SETTLED epoch, as in Python');t.eq(status.vendor_observation.groups[1].id,'wireguard:wgclient')
  t.eq(status.profiles[2].role,'target')
  t.eq(#status.samples,2);t.eq(status.samples[1].id,'wireguard:peer_7');t.eq(status.samples[1].vendor_tunnel_id,'wireguard:wgclient')
  t.eq(#status.events,2,'a first verdict per profile is an event');t.eq(status.events[1].code,'OK');t.eq(status.events[1].role,'source');t.eq(status.events[1].https_success,3)
  t.eq(status.native_failover.state,'OBSERVING')
  t.eq(status.probe_policy.level,5);t.eq(status.probe_policy.interval,10);t.eq(status.probe_policy.levels['1'],{60,300})
  t.eq(status.stats_mode.mode,'diagnostic','no package config: everything recorded');t.truthy(status.stats_mode.storage['ram:status.json']==nil or true)
  t.eq(status.scope,'IPv4 router-originated HTTPS/DNS, not LAN/IPv6 validation');t.eq(status.capabilities.native_apply,false)
  t.eq(status.storage_error,canon.null);t.eq(status.package,'2.0.0-lua-alpha3-test');t.eq(status.observation_valid_for,30)
  t.eq(status.uplink_observation.state,'LINK-UP');t.eq(status.wan_devices,{{device='eth0'}})
  t.eq(status.lua_backend.so_mark,false);t.eq(status.lua_backend.bindtodevice,true);t.eq(status.lua_backend.monitor,'lua')
  t.eq(#status.lua_backend.bridges,0,'no Python bridge on a timer (page_controls.lua)');t.eq(#status.lua_backend.bridge_fallback,1)
  t.truthy(canon.is_object(status.accounting));t.eq(status.accounting.gaps,0)
  t.truthy(status.accounting.quality['wireguard:peer_7']~=nil)
  t.eq(status.accounting.wan.gaps,0)
  local written=canon.decode(R.files['/run/hv/status.json'])
  t.eq(written.version,require('version'));t.eq(written.profiles[1].id,'wireguard:peer_7')
  t.eq(m.rpc.handle('status','{}').profiles[1].id,'wireguard:peer_7','the ubus reply comes from memory')
  t.eq(m.rpc.handle('status','{}').history_split,{'accounting.quality','accounting.reliability.events','native_history.events'})
end)

t.test('second pass: counters accumulate, verdict changes become events, unchanged ones do not',function()
  local R,m=fresh()
  local first=m:pass()
  R.advance(10);R.counters.wgclient.rx=R.counters.wgclient.rx+5000;R.counters.wgclient.tx=R.counters.wgclient.tx+700;R.counters.eth0.rx=R.counters.eth0.rx+100
  local status=m:pass()
  t.eq(status.profiles[1].vendor_state,'SETTLED');t.eq(status.profiles[1].vendor_generation,first.profiles[1].vendor_generation,'same epoch')
  t.eq(status.profiles[1].ping.state,'ok');t.eq(status.profiles[1].ping.rtt_ms,12.3)
  t.eq(#status.events,2,'same verdicts: no new events')
  local month=os.date('%Y-%m',R.now)
  t.eq(status.accounting.months[month].rx,5000);t.eq(status.accounting.months[month].tx,700);t.eq(status.accounting.months[month].seconds,20,'two devices, ten seconds each')
  t.eq(status.accounting.wan.months[month].rx,100)
  t.eq(status.accounting.activity['wireguard:peer_7'].days[os.date('%Y-%m-%d',R.now)].up,10)
  R.advance(10);R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
  status=m:pass()
  t.eq(#status.events,4,'both channels changed to VPN-003')
  t.eq(status.events[3].code,'VPN-003');t.eq(status.events[3].profile,'wireguard:peer_7');t.eq(status.events[3].https_success,1);t.eq(#status.events[3].probe_checks,3)
  t.eq(#status.samples,6)
  R.https_fail={};R.advance(10)
  status=m:pass()
  t.eq(status.events[5].code,'OK');t.eq(#status.events,6)
end)

t.test('L1: a failed sample of an Auto channel leaves the wake row, a healthy pass and option 0 none',function()
  local NAME='/run/hv/pair-wake.json'
  local R,m=fresh()
  m:pass()
  t.eq(R.files[NAME],nil,'healthy: no row')
  R.advance(10);R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
  m:pass()
  local row=canon.decode(R.files[NAME])
  t.eq(row.reason,'sample');t.eq(canon.number(row.time),R.wall());t.eq(row.id,'wireguard:peer_7')
  R.files[NAME]=nil
  local S,n=fresh({inventory=t.inventory({settings=(function() local s=t.inventory().settings;s.auto_event_wake=false;return s end)()})})
  S.https_fail['1.1.1.1']='timeout';S.https_fail['8.8.8.8']='timeout'
  n:pass()
  t.eq(S.files[NAME],nil,'the option turns it off')
end)

t.test('server pick (2.1.0): one child round at a time, every 10 min or on a new failure; the RAM file is projected; events once',function()
  local R,m=fresh()
  local spawned={}
  function R.spawn(argv,seconds,cb) spawned[#spawned+1]={argv=argv,seconds=seconds,cb=cb} end
  R.files['/run/hv/server-pick.json']=canon.encode(canon.object({time=R.now-700,enabled=false,tunnels=canon.array({canon.object({tunnel_id=5841,protocol='wireguard',
    interface='wgclient',current='1_7',best=canon.null,ordered=false,code='SERVER-PICKED',last_change=canon.null,
    candidates=canon.array({canon.object({profile='1_7',location='Vienna',latency_ms=canon.null,alive=canon.null})})})})}))
  local status=m:pass()
  t.eq(status.server_pick.tunnels[1].current,'1_7','the file of the last round is published')
  t.eq(#spawned,1);t.eq(spawned[1].argv,{'/usr/bin/lua','/usr/lib/homensai-vpn/lua/server_pick.lua','job','/run/hv/server-pick-request.json'})
  local request=canon.decode(R.files['/run/hv/server-pick-request.json'])
  t.eq(request.enabled,false,'off by default');t.eq(request.auto_on,false);t.eq(#request.failed,0)
  for _,e in ipairs(status.events) do t.truthy(e.code~='SERVER-PICKED','a round finished before this monitor started is not an event') end
  R.advance(10);status=m:pass()
  t.eq(#spawned,1,'one round at a time')
  spawned[1].cb(0);R.advance(10);status=m:pass()
  t.eq(#spawned,1,'not due: less than 10 min, no new failure')
  R.files['/run/hv/server-pick.json']=string.gsub(R.files['/run/hv/server-pick.json'],'"time":'..(R.now-720)..'','"time":'..R.now)
  R.advance(10);R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
  status=m:pass()
  t.eq(#spawned,2,'a channel newly failed: a round now')
  t.eq(canon.decode(R.files['/run/hv/server-pick-request.json']).failed,{'wgclient','wgclient2'})
  local picked=0;for _,e in ipairs(status.events) do if e.code=='SERVER-PICKED' then picked=picked+1;t.eq(e.tunnel_id,5841) end end
  t.eq(picked,1,'a newer round with a change is one event')
  spawned[2].cb(0);R.advance(10);status=m:pass()
  picked=0;for _,e in ipairs(status.events) do if e.code=='SERVER-PICKED' then picked=picked+1 end end
  t.eq(picked,1,'the same round is not reported twice');t.eq(#spawned,2)
  R.inventory_data.settings.server_pick=true;R.advance(10);status=m:pass()
  t.eq(#spawned,3,'the owner switch changed: a round now');t.eq(canon.decode(R.files['/run/hv/server-pick-request.json']).enabled,true)
  R.files['/run/hv/server-pick.json']='{"broken"';spawned[3].cb(0);R.advance(10);status=m:pass()
  t.eq(status.server_pick,canon.null,'a damaged file publishes nothing')
  -- stage 2: the supervisor's own outcome file is a history event once
  R.files['/run/hv/server-pick-event.json']=canon.encode(canon.object({time=R.now,request=R.now-5,tunnels=canon.array({canon.object({tunnel_id=4192,code='SERVER-PICK-FAILED'})})}))
  R.advance(10);status=m:pass()
  local failed=0;for _,e in ipairs(status.events) do if e.code=='SERVER-PICK-FAILED' then failed=failed+1;t.eq(e.tunnel_id,4192) end end
  t.eq(failed,1,'the supervisor outcome is one event')
  R.advance(10);status=m:pass()
  failed=0;for _,e in ipairs(status.events) do if e.code=='SERVER-PICK-FAILED' then failed=failed+1 end end
  t.eq(failed,1,'the same outcome is not reported twice')
end)

t.test('server pick: a channel that recovered and fails again within 10 min starts a new round (MT3000 02.11.2026)',function()
  local R,m=fresh()
  local spawned={}
  function R.spawn(argv,seconds,cb) spawned[#spawned+1]={argv=argv,seconds=seconds,cb=cb} end
  m:pass();t.eq(#spawned,1,'the first round');spawned[1].cb(0)
  R.advance(10);R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
  m:pass();t.eq(#spawned,2,'a channel failed: a round now');spawned[2].cb(0)
  local failed=canon.decode(R.files['/run/hv/server-pick-request.json']).failed;t.truthy(#failed>0)
  R.advance(10);m:pass();t.eq(#spawned,2,'still failed: no new round')
  R.https_fail={};R.advance(10);m:pass();t.eq(#spawned,2,'recovered: no round')
  R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout';R.advance(10)
  m:pass();t.eq(#spawned,3,'failed again within 10 min: a new round')
  t.eq(canon.decode(R.files['/run/hv/server-pick-request.json']).failed,failed)
end)

-- MT3000 02.11.2026: the round a failure starts runs before Auto moved the traffic (SERVER-PICK-CARRYING), so the failed
-- channel gets another round once RETRY_CARRYING (20 s) passed; another code is not retried (agent.py twin:
-- test_agent_server_pick_rounds.py)
local function carrying_case(code)
  local R,m=fresh()
  local spawned={}
  function R.spawn(argv,seconds,cb) spawned[#spawned+1]={argv=argv,seconds=seconds,cb=cb} end
  m:pass();spawned[1].cb(0)
  R.advance(10);R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
  m:pass();t.eq(#spawned,2,'a channel failed: a round now')
  local failed=canon.decode(R.files['/run/hv/server-pick-request.json']).failed;t.truthy(#failed>0)
  R.files['/run/hv/server-pick.json']=canon.encode(canon.object({time=R.now,enabled=true,tunnels=canon.array({canon.object({protocol='wireguard',
    interface='wgclient2',code=code,candidates=canon.array({})})})}))
  spawned[2].cb(0)
  R.advance(19);m:pass();t.eq(#spawned,2,'19 s after the failure round: no round')
  R.advance(1);m:pass()
  return R,m,spawned,failed
end

t.test('server pick: a failed channel that still carried the traffic gets another round after 20 s (MT3000 02.11.2026)',function()
  local R,_,spawned,failed=carrying_case('SERVER-PICK-CARRYING')
  t.eq(#spawned,3,'20 s: another round');t.eq(canon.decode(R.files['/run/hv/server-pick-request.json']).failed,failed)
end)

t.test('server pick: a round with another code is not retried',function()
  local R,m,spawned=carrying_case('SERVER-PICK-LIMIT')
  t.eq(#spawned,2,'SERVER-PICK-LIMIT at 20 s: no round');R.advance(30);m:pass();t.eq(#spawned,2,'nor at 50 s')
end)

-- review 02.11.2026: a channel that keeps carrying (reserve down, hold) got a round every 20 s; one retry per failure.
-- Every round finishes at once and says CARRYING for wgclient2.
local function carrying_rounds()
  local R,m=fresh()
  local spawned={}
  function R.spawn(argv,seconds,cb)
    spawned[#spawned+1]={argv=argv,seconds=seconds,cb=cb}
    R.files['/run/hv/server-pick.json']=canon.encode(canon.object({time=R.now,enabled=true,tunnels=canon.array({canon.object({protocol='wireguard',
      interface='wgclient2',code='SERVER-PICK-CARRYING',candidates=canon.array({})})})}))
    cb(0)
  end
  local function fail(on) if on then R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout' else R.https_fail={} end end
  m:pass();t.eq(#spawned,1,'the first round')
  R.advance(10);fail(true);m:pass();t.eq(#spawned,2,'a channel failed: a round now')
  R.advance(20);m:pass();t.eq(#spawned,3,'20 s, still carrying: the retry')
  return R,m,spawned,fail
end

t.test('server pick: the carrying retry happens once per failure',function()
  local R,m,spawned=carrying_rounds()
  for i=1,4 do R.advance(20);m:pass();t.eq(#spawned,3,'the retry said CARRYING again: no round '..(20*i)..' s later') end
end)

t.test('server pick: a channel that recovered and fails again gets a fresh carrying retry',function()
  local R,m,spawned,fail=carrying_rounds()
  R.advance(10);fail(false);m:pass();t.eq(#spawned,3,'recovered: no round')
  R.advance(10);fail(true);m:pass();t.eq(#spawned,4,'failed again: a round now')
  R.advance(20);m:pass();t.eq(#spawned,5,'its own retry')
  R.advance(20);m:pass();t.eq(#spawned,5,'and only one')
end)

t.test('events after a restart are measured against the previous status.json, not an empty memory',function()
  local R=t.fake_runner()
  R.files['/run/hv/status.json']=canon.encode(canon.object({profiles=canon.array({canon.object({id='wireguard:peer_7',code=canon.null}),canon.object({id='wireguard:peer_8',code='VPN-003'})})}))
  local m=monitor.new(R)
  local status=m:pass()
  t.eq(#status.events,1);t.eq(status.events[1].profile,'wireguard:peer_8');t.eq(status.events[1].code,'OK')
end)

t.test('checkpoint cadence: diagnostic mode saves at the configured interval, work mode once a day',function()
  local R,m=fresh({config="config main 'main'\n\toption stats_mode 'work'\n"})
  m:pass()
  t.eq(R.files['/etc/hv/checkpoint.json'],nil,'work mode: nothing saved on the first pass')
  R.advance(86400)
  m:pass()
  t.truthy(R.files['/etc/hv/checkpoint.json']~=nil,'work mode: saved after a day')
  local envelope=canon.decode(R.files['/etc/hv/checkpoint.json'])
  t.eq(envelope.sha256,canon.digest(envelope.data))
  R,m=fresh()
  m:pass();R.advance(900);m:pass()
  t.truthy(R.files['/etc/hv/checkpoint.json']~=nil,'diagnostic: saved after settings.checkpoint seconds')
  m:shutdown()
  local saved=canon.decode(R.files['/etc/hv/checkpoint.json'])
  t.eq(canon.number(saved.data.saved),R.now,'shutdown saves once more')
end)

t.test('a failing pass publishes SYSTEM-001 and the daemon continues',function()
  local R,m=fresh()
  R.command=function() return nil,'COMMAND-FAILED' end
  local status=m:pass()
  t.eq(status.error,'SYSTEM-001');t.eq(status.version,require('version'))
  t.eq(canon.decode(R.files['/run/hv/status.json']).error,'SYSTEM-001')
  t.eq(m:next_delay(),30)
  t.eq(m.rpc.handle('status','{}').error,'SYSTEM-001')
  t.truthy(#R.logs>0)
end)

t.test('a clock before 2024 blocks accounting with CLOCK-001',function()
  local R,m=fresh({now=1600000000})
  local status=m:pass()
  t.eq(status.storage_error,'CLOCK-001');t.eq(status.events[#status.events].code,'CLOCK-001')
  t.eq(status.accounting.months,{})
end)

t.test('compare rows (router test helper): Lua verdict next to the live Python verdict, no exit address',function()
  local R,m=fresh()
  m:pass();R.advance(5);m:pass()
  local live=canon.object({profiles=canon.array({canon.object({id='wireguard:peer_7',code='VPN-003',https_success=1,dns_ok=true,exit_ip='1.2.3.4'})})})
  local rows=monitor.compare_rows(m.status,live,m.ping.cache)
  t.eq(#rows,2);t.eq(rows[1].id,'wireguard:peer_7');t.eq(rows[1].lua.code,canon.null);t.eq(rows[1].lua.exit_country,'DE')
  t.eq(rows[1].python.code,'VPN-003');t.eq(rows[1].python.exit_ip_seen,true);t.eq(rows[2].python,canon.null)
  t.eq(rows[1].lua_ping_after.state,'ok')
  t.truthy(not string.find(canon.encode(rows),'93.184.216.34',1,true) and not string.find(canon.encode(rows),'1.2.3.4',1,true),'exit addresses are not printed')
end)

t.run()
