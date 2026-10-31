-- monitor.lua/probe.lua under a deferred (event-loop-like) fake: nothing blocks, at most two probes in flight,
-- the watchdog ends a stuck pass, late ping answers never mutate a published row.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local monitor=require('monitor')
local probe=require('probe')

local function fresh(options)
  local R=t.fake_runner(options)
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  return R,monitor.new(R)
end

t.test('a pass starts the checks and returns at once; the status is published when the answers arrive',function()
  local R,m=fresh()
  R.deferred=true
  local published
  t.truthy(m:start_pass(function(status) published=status end))
  t.eq(published,nil,'nothing published before the answers')
  t.eq(m.passing,true)
  t.eq(m:start_pass(function() end),false,'a pass never overlaps a running one')
  t.eq(R.https_calls,6,'two profiles in flight: 3 HTTPS checks each, started together')
  R.drain()
  t.truthy(published~=nil);t.eq(published.profiles[1].code,canon.null);t.eq(m.passing,false)
  t.eq(canon.number(canon.decode(R.files['/run/hv/status.json']).time),published.time)
end)

t.test('at most two profiles are probed at the same time (agent.py used a pool of two)',function()
  local inv=t.inventory()
  for i=1,3 do
    local iface='wgx'..i
    inv.profiles[#inv.profiles+1]={id='wireguard:peer_'..(20+i),section='peer_'..(20+i),protocol='wireguard',name='N'..i,group_id='1',profile_id=tostring(20+i),
      vendor_profile_group_id='wireguard:1',vendor_tunnel_id='wireguard:'..iface,interface=iface,administrative_state='enabled'}
  end
  inv.servers=canon.array()
  local R=t.fake_runner({inventory=inv})
  for i=1,3 do
    local iface='wgx'..i
    R.interfaces[iface]={up=true,l3_device=iface,proto='wgclient'};R.marks[iface]={mark=0x4000+i,table=tostring(60+i)};R.counters[iface]={ifindex=30+i,rx=1,tx=1}
  end
  local m=monitor.new(R)
  R.deferred=true
  m:start_pass()
  t.eq(R.https_calls,6,'two profiles first')
  local fn=table.remove(R.queue,1);fn()  -- one HTTPS answer: the profile is not finished, nothing new starts
  t.eq(R.https_calls,6)
  for _=1,3 do fn=table.remove(R.queue,1);fn() end  -- the rest of the first profile (2 HTTPS + DNS)
  t.eq(R.https_calls,9,'a finished profile frees one slot')
  R.drain()
  t.eq(#m.status.profiles,6,'five probed plus the OpenVPN entry without a tunnel')
  for _,p in ipairs(m.status.profiles) do if p.interface~=canon.null then t.eq(p.code,canon.null,p.id) end end
end)

t.test('the watchdog ends a pass whose checks never answer: SYSTEM-001 rows, monitor continues',function()
  local R,m=fresh()
  local timers={}
  R.after=function(ms,fn) timers[#timers+1]={ms,fn};return {cancel=function() timers[#timers]=nil end} end
  R.https_get=function() end  -- never calls back
  local published
  m:start_pass(function(s) published=s end)
  t.eq(published,nil)
  t.eq(timers[1][1],monitor.PASS_WATCHDOG*1000)
  timers[1][2]()
  t.truthy(published~=nil)
  t.eq(published.profiles[1].code,'SYSTEM-001');t.eq(published.profiles[2].code,'SYSTEM-001')
  t.eq(m.passing,false)
  t.truthy(#R.logs>0)
end)

t.test('a probe that answers twice or late changes nothing after its verdict',function()
  local R=t.fake_runner()
  local results={}
  local saved
  R.https_get=function(device,address,hostname,path,seconds,cb) saved=saved or {};saved[#saved+1]=cb end
  probe.probe(R,R.inventory_data.profiles[1],function(result) results[#results+1]=result end)
  t.eq(#results,0)
  for _,cb in ipairs(saved) do cb({status=200,body='fl=1\nip=93.184.216.34\nhttp=http/1.1\n'}) end
  t.eq(#results,1,'three HTTPS answers and the DNS answer complete the verdict once')
  t.eq(results[1].https_success,1,'trace valid; dns-json/dns-wire bodies invalid for their kinds')
  for _,cb in ipairs(saved) do pcall(cb,{status=200,body='x'}) end
  t.eq(#results,1)
end)

t.test('a late ping answer fills the cache for the next pass and never mutates the published status',function()
  local R,m=fresh()
  local pending={}
  local datagram=R.datagram
  R.datagram=function(kind,device,host,port,packet,seconds,accept,cb)
    if kind=='icmp' then pending[#pending+1]=function() datagram(kind,device,host,port,packet,seconds,accept,cb) end;return end
    return datagram(kind,device,host,port,packet,seconds,accept,cb)
  end
  m:pass();R.advance(5)  -- the first pass opens the vendor epoch; pings need it SETTLED
  local status=m:pass()
  t.eq(status.profiles[1].ping.state,'checking');t.eq(status.profiles[1].ping.code,'PING-CHECK-PENDING')
  local before=canon.encode(m.status)
  for _,fn in ipairs(pending) do fn() end
  t.eq(canon.encode(m.status),before,'the published table is unchanged')
  R.advance(10)
  status=m:pass()
  t.eq(status.profiles[1].ping.state,'ok');t.eq(status.profiles[1].ping.rtt_ms,12.3);t.eq(status.profiles[1].ping.backend,'nixio-raw')
end)

t.test('datagram answers: only the awaited DNS token / ICMP echo are accepted',function()
  local R=t.fake_runner()
  local token,packet=probe.dns_question(R)
  local seen
  R.datagram=function(kind,device,host,port,p,seconds,accept,cb)
    seen={kind=kind,device=device,host=host,port=port,seconds=seconds}
    t.truthy(not accept('\0\0'..string.sub(t.dns_answer(p),3)),'another token is ignored')
    cb(t.dns_answer(p),nil,1,1)
  end
  t.eq(t.dns_now(R,'wgclient'),true)
  t.eq(seen,{kind='udp',device='wgclient',host='9.9.9.9',port=53,seconds=3})
  local _=token;_=packet
  R=t.fake_runner()
  R.icmp_rtt=1500  -- longer than the 1 s timeout: never a valid sample
  local binding={device='wgclient',mark=4096,table='53',ifindex=20}
  local rtt,kind=t.await(R,function(cb) probe.echo(R,binding,'1.1.1.1',cb) end)
  t.eq(rtt,nil);t.eq(kind,'timeout')
  R.icmp_rtt=nil;R.icmp_kind='unavailable'
  rtt,kind=t.await(R,function(cb) probe.echo(R,binding,'1.1.1.1',cb) end)
  t.eq(rtt,nil);t.eq(kind,'unavailable')
end)

t.test('next_delay follows the probe policy (boost) and never overlaps the pass time',function()
  local R,m=fresh()
  m:pass()
  t.eq(m:next_delay(),10)
  m.booster.state.active=true
  m.settings={interval=30}
  t.eq(m:next_delay(),10,'boost: at most every 10 s')
  m.booster.state.active=false
  t.eq(m:next_delay(),30)
  m.pass_seconds=12
  t.eq(m:next_delay(),18)
end)

t.run()
