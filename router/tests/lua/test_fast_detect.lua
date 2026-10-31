-- fast_detect.lua (Lua plan item 5): the owner switch, the pulse (losses, debounce, disarm, link signals, binding
-- epochs, pause), the monitor wiring (off = no socket and no status field) and the acceptance simulation on a
-- virtual clock: four 150 s outages of the primary are confirmed by Auto's unchanged streak rule much sooner than
-- without the pulse, short blips never satisfy it.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local fast=require('fast_detect')
local monitor=require('monitor')
local pair=require('pair')
local probe=require('probe')
local u16,be16=t.u16,t.be16

local ON="config main 'main'\n\toption enabled '1'\n\toption lua_fast_detect '1'\n"
local SOURCE,TARGET='wireguard:peer_7','wireguard:peer_8'
local PAIR={source=SOURCE,target=TARGET}

-- An echo reply to our request, as the kernel hands it to a raw socket (IP header + ICMP).
local function reply(packet,target)
  local echo='\0\0'..u16(0)..string.sub(packet,5)
  echo='\0\0'..u16(probe.icmp_checksum(echo))..string.sub(echo,5)
  local a,b,c,d=string.match(target,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  return '\69\0'..u16(20+#echo)..u16(1)..u16(0)..'\64\1'..u16(0)..string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d))..'\10\0\0\2'..echo
end

-- The network of the fake runner: R.down[device] = nil (answers) | 'blackhole' (no answer) | 'refused' (EPERM of
-- an nft drop) | 'missing' (device gone); probes through a down device fail as on the router.
local function network(R)
  R.down={};R.opened=0;R.closed=0;R.sent=0;R.targets={};R.operstate={}
  function R.beat_socket(device)
    if R.down[device]=='missing' then return nil,'missing' end
    R.opened=R.opened+1
    local inbox={}
    local h={}
    function h:send(target,packet)
      R.sent=R.sent+1;R.targets[#R.targets+1]=target
      local mode=R.down[device]
      if mode=='refused' then return nil,'refused' end
      if mode=='missing' then return nil,'missing' end
      inbox[#inbox+1]='noise: not an ICMP packet of ours'
      if mode~='blackhole' then inbox[#inbox+1]=reply(packet,target) end
      return true
    end
    function h:recv() return table.remove(inbox,1) end
    function h:close() R.closed=R.closed+1 end
    return h
  end
  local sysfs=R.sysfs
  function R.sysfs(device,name)
    if R.down[device]=='missing' then return nil end
    if name=='operstate' then return R.operstate[device] or 'unknown' end
    if name=='statistics/rx_packets' then return R.down[device] and '100' or tostring(100+R.sent) end
    if name=='statistics/tx_packets' then return tostring(200+R.sent) end
    return sysfs(device,name)
  end
  local https,datagram=R.https_get,R.datagram
  function R.https_get(device,address,hostname,path,seconds,cb)
    if R.down[device] then R.https_calls=(R.https_calls or 0)+1;cb(nil,'timeout');return end
    return https(device,address,hostname,path,seconds,cb)
  end
  function R.datagram(kind,device,host,port,packet,seconds,accept,cb)
    if kind=='udp' and R.down[device] then cb(nil,'timeout');return end
    return datagram(kind,device,host,port,packet,seconds,accept,cb)
  end
  return R
end

local function rows()
  return {{id=SOURCE,device='wgclient',mark=0x1000,table='53',ifindex=20},{id=TARGET,device='wgclient2',mark=0x2000,table='54',ifindex=21},
          {id='openvpn:1_2'}}
end
local function pulse(R) local p=fast.Pulse(R);p:configure(true,rows(),PAIR,'OBSERVING');return p end
local function beats(p,R,n) local found;for _=1,n do R.advance(1);found=p:tick(R.clock()) end;return found end

t.test('owner switch: default off; only option lua_fast_detect 1 in config main turns it on',function()
  t.eq(fast.option_enabled(nil),false);t.eq(fast.option_enabled("config main 'main'\n\toption enabled '1'\n"),false)
  t.eq(fast.option_enabled(ON),true)
  t.eq(fast.option_enabled('config main "main"\n  option lua_fast_detect "1"\n'),true,'double quotes')
  t.eq(fast.option_enabled("config main 'main'\n\toption lua_fast_detect 1\n"),true,'unquoted')
  t.eq(fast.option_enabled("config main 'main'\n\toption lua_fast_detect '0'\n"),false)
  t.eq(fast.option_enabled("config main 'main'\n\toption lua_fast_detect 'yes'\n"),false,'only 1 is on')
  t.eq(fast.option_enabled("config server 'office'\n\toption lua_fast_detect '1'\n"),false,'another section')
  t.eq(fast.option_enabled("config main 'main'\n\toption lua_fast_detect '1'\nconfig server\n\toption lua_fast_detect '0'\n"),true,'anonymous section after main')
  t.eq(fast.option_enabled("config main 'main'\n\toption lua_fast_detect '1'\n\toption lua_fast_detect '0'\n"),false,'the last value wins')
  t.eq(fast.option_enabled("config main 'main'\n\toption lua_fast_detect_x '1'\n"),false)
end)

t.test('channels: the pair rows with a complete kernel binding only',function()
  local found=fast.channels(rows(),PAIR)
  t.eq(found[SOURCE].role,'source');t.eq(found[SOURCE].device,'wgclient');t.eq(found[TARGET].role,'target')
  local broken=rows();broken[2].mark=nil
  t.eq(fast.channels(broken,PAIR)[TARGET],nil,'no mark: no channel')
  broken=rows();broken[1].device='wg client'
  t.eq(fast.channels(broken,PAIR)[SOURCE],nil,'unsafe device name')
  t.eq(next(fast.channels(rows(),{})),nil)
end)

t.test('healthy channels: one echo per channel per beat, alternating targets, persistent sockets, no suspect',function()
  local R=network(t.fake_runner())
  local p=pulse(R)
  t.eq(beats(p,R,10),nil)
  t.eq(R.opened,2,'one socket per channel for the whole run');t.eq(R.sent,20)
  t.eq(R.targets[1],'1.1.1.1');t.eq(R.targets[3],'8.8.8.8');t.eq(R.targets[5],'1.1.1.1')
  local public=p:public(R.clock(),true)
  t.eq(public.channels[1].profile,SOURCE);t.eq(public.channels[1].state,'ok');t.eq(public.channels[1].replies,9,'the first beat only sends')
  t.eq(public.channels[1].lost,0);t.eq(public.channels[2].role,'target');t.eq(public.active,true)
  t.truthy(canon.encode(public),'encodable')
end)

t.test('black hole: the third unanswered echo in a row makes a suspect; two do not',function()
  local R=network(t.fake_runner())
  local p=pulse(R)
  beats(p,R,3)
  R.down.wgclient='blackhole'
  t.eq(beats(p,R,2),nil,'the first beat reads the answer of the echo sent before the outage')
  t.eq(p.channels[SOURCE].lost,1)
  R.down.wgclient=nil
  t.eq(beats(p,R,1),nil,'the echo sent into the black hole is the second loss');t.eq(p.channels[SOURCE].lost,2)
  t.eq(beats(p,R,1),nil,'an answer clears the count');t.eq(p.channels[SOURCE].lost,0)
  R.down.wgclient='blackhole'
  t.eq(beats(p,R,3),nil)
  local found=beats(p,R,1)
  t.eq(#found,1);t.eq(found[1].id,SOURCE);t.eq(found[1].lost,3);t.eq(found[1].reason,'timeout')
  t.eq(p.channels[TARGET].lost,0,'the reserve keeps answering')
  local ev=p:evidence(found[1],R.clock())
  t.eq(ev.losses,3);t.eq(ev.cause,'timeout');t.eq(ev.stalled_s,2,'nothing received since the first loss')
end)

t.test('a refused send (nft drop) counts at once and keeps the socket; disarm holds until an answer',function()
  local R=network(t.fake_runner())
  local p=pulse(R)
  beats(p,R,2)
  R.down.wgclient='refused'
  t.eq(beats(p,R,2),nil)
  local found=beats(p,R,1)
  t.eq(found[1].id,SOURCE);t.eq(found[1].reason,'send-refused');t.eq(R.opened,2,'socket kept on EPERM')
  p:disarm(SOURCE)
  t.eq(beats(p,R,20),nil,'disarmed: one episode per outage')
  t.eq(p.channels[SOURCE].lost,23)
  R.down.wgclient=nil
  beats(p,R,2)
  t.eq(p.channels[SOURCE].armed,true,'an answer re-arms')
  R.down.wgclient='refused'
  t.eq(#beats(p,R,3),1,'a new outage is a new suspect')
  p:hold(SOURCE,R.clock()+5)
  t.eq(beats(p,R,4),nil,'held');t.eq(#beats(p,R,1),1,'offered again after the hold')
end)

t.test('link signals: a missing device is a loss, a re-created device and a socket error are not counted',function()
  local R=network(t.fake_runner())
  local p=pulse(R)
  beats(p,R,2)
  R.down.wgclient='missing'
  t.eq(#beats(p,R,3),1);t.eq(p.channels[SOURCE].reason,'link-missing')
  R.down.wgclient=nil;R.counters.wgclient.ifindex=99
  local before=p.channels[SOURCE].lost
  beats(p,R,3)
  t.eq(p.channels[SOURCE].lost,before,'re-created device: not counted until the next pass rebinds');t.eq(p.channels[SOURCE].reason,'link-changed')
  R.counters.wgclient.ifindex=20;R.operstate.wgclient='down'
  p.channels[SOURCE].lost=0
  t.eq(#beats(p,R,3),1);t.eq(p.channels[SOURCE].reason,'link-down')
  R.operstate.wgclient=nil
  R.beat_socket=function() return nil,'unavailable' end
  p:close_socket(p.channels[SOURCE]);p.channels[SOURCE].lost=0
  t.eq(beats(p,R,5),nil,'a local socket problem never counts');t.eq(p.channels[SOURCE].last,'unavailable')
end)

t.test('configure: off, not watching or no pair -> no packet; a new binding starts the evidence again',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R)
  p:configure(false,rows(),PAIR,'OBSERVING');t.eq(beats(p,R,5),nil);t.eq(R.sent,0)
  p:configure(true,rows(),PAIR,'STOPPED');t.eq(beats(p,R,5),nil);t.eq(R.sent,0)
  p:configure(true,rows(),{source=SOURCE},'OBSERVING');t.eq(R.sent,0);t.eq(p.active,false)
  p:configure(true,rows(),PAIR,'COMMITTED');beats(p,R,1);t.eq(R.sent,2)
  R.down.wgclient='blackhole';beats(p,R,3);t.eq(p.channels[SOURCE].lost,2,'the first beat still read the answer sent before')
  p:configure(true,rows(),PAIR,'DEGRADED-ON-RESERVE');t.eq(p.channels[SOURCE].lost,2,'same binding: evidence kept')
  local moved=rows();moved[1].ifindex=33
  p:configure(true,moved,PAIR,'OBSERVING');t.eq(p.channels[SOURCE].lost,0,'new epoch');t.eq(R.closed,1)
  p:configure(true,rows(),PAIR,'ARMED');t.eq(p.active,false);t.eq(next(p.channels),nil)
end)

t.test('a speed test pauses the pulse and clears its evidence',function()
  local R=network(t.fake_runner())
  local paused=false
  local p=fast.Pulse(R,function() return paused end)
  p:configure(true,rows(),PAIR,'OBSERVING')
  R.down.wgclient='blackhole';beats(p,R,3);t.eq(p.channels[SOURCE].lost,2)
  paused=true;local sent=R.sent
  t.eq(beats(p,R,10),nil);t.eq(R.sent,sent,'no packet while paused');t.eq(p.channels[SOURCE].lost,0)
end)

t.test('monitor_io.beat_socket: raw ICMP bound to the device, non-blocking, errno mapping, unsafe names refused',function()
  local log,errors={},{}
  local function sock()
    local s={}
    function s:setopt(level,name,value) log[#log+1]={'setopt',level,name,value};if errors.bind then return nil,errors.bind end;return true end
    function s:setblocking(flag) log[#log+1]={'setblocking',flag};return true end
    -- the router's nixio refuses connect(host,0) ('Unrecognized service'): raw ICMP must use sendto
    function s:connect(host,port) error('connect must not be used for raw ICMP') end
    function s:sendto(packet,host,port) log[#log+1]={'sendto',host,port,#packet};if errors.send then return nil,errors.send end;return #packet end
    function s:recvfrom(n) local v=errors.recv;errors.recv=false;return v end
    function s:close() log[#log+1]={'close'} end
    return s
  end
  package.loaded['monitor_io']=nil
  package.loaded['nixio']={socket=function(family,kind,proto) log[#log+1]={'socket',family,kind,proto};return sock() end}
  local ok,err=pcall(function()
    local io_=require('monitor_io')
    t.eq({io_.beat_socket('wg client')},{nil,'unavailable'})
    local h=io_.beat_socket('wgclient1')
    t.eq(log[1],{'socket','inet','raw','icmp'});t.eq(log[2],{'setopt','socket','bindtodevice','wgclient1'});t.eq(log[3],{'setblocking',false})
    t.eq(h:send('1.1.1.1','x'),true);t.eq(log[4],{'sendto','1.1.1.1',0,1})
    t.eq({h:send('1.1.1.1;id','x')},{nil,'unavailable'})
    errors.send=1;t.eq({h:send('8.8.8.8','x')},{nil,'refused'},'EPERM: firewall drop')
    errors.send=101;t.eq({h:send('8.8.8.8','x')},{nil,'refused'},'ENETUNREACH')
    errors.send=19;t.eq({h:send('8.8.8.8','x')},{nil,'missing'},'ENODEV');errors.send=nil
    errors.send=22;t.eq({h:send('8.8.8.8','x')},{nil,'unavailable'});errors.send=nil
    t.eq(h:recv(),nil,'false (EAGAIN) reads as nothing');errors.recv='data';t.eq(h:recv(),'data')
    h:close();t.eq(log[#log],{'close'})
    errors.bind=19;t.eq({io_.beat_socket('wgclient9')},{nil,'missing'})
    errors.bind=1;t.eq({io_.beat_socket('wgclient9')},{nil,'unavailable'})
    t.eq(io_.sysfs('wg client','ifindex'),nil);t.eq(io_.sysfs('lo','statistics/rx_dropped'),nil,'allow-listed names only')
  end)
  package.loaded['nixio']=nil;package.loaded['monitor_io']=nil
  if not ok then error(err,0) end
end)

------------------------------------------------------------------------------------------------------
-- the monitor wiring
------------------------------------------------------------------------------------------------------
local function settings(extra)
  local s={enabled=true,interval=60,probe_level=1,checkpoint=900,probe_limit=16,live_log_limit=2000,history_days=7,
    plan_source=SOURCE,plan_target=TARGET,plan_source_tunnel='wireguard:wgclient',plan_target_tunnel='wireguard:wgclient2'}
  for k,v in pairs(extra or {}) do s[k]=v end
  return s
end
local function fresh(config)
  local R=network(t.fake_runner({config=config,inventory=t.inventory({settings=settings()})}))
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  return R,monitor.new(R)
end

t.test('monitor, switch off (default): no socket, no beat, no status field',function()
  local R,m=fresh("config main 'main'\n\toption enabled '1'\n")
  m:pass()
  for _=1,10 do R.advance(1);t.eq(m:fast_tick(),false) end
  t.eq(R.opened,0);t.eq(R.sent,0);t.eq(m.status.fast_detect,nil)
  t.eq(canon.decode(R.files['/run/hv/status.json']).fast_detect,nil,'published status unchanged when off')
end)

t.test('monitor, switch on: beats after a pass, a lost primary starts the dense confirmation once',function()
  local R,m=fresh(ON)
  m:pass()
  t.eq(m.status.fast_detect.enabled,true);t.eq(m.status.fast_detect.active,true);t.eq(#m.status.fast_detect.channels,2)
  for _=1,5 do R.advance(1);t.eq(m:fast_tick(),false) end
  R.down.wgclient='refused'
  local started
  for i=1,3 do R.advance(1);started=m:fast_tick();if started then started=i;break end end
  t.eq(started,3,'the third refused beat')
  local dense=m.booster:dense(R.wall())
  t.eq(dense.reason,'heartbeat-lost');t.eq(dense.profile,SOURCE);t.eq(dense.role,'source');t.eq(dense.evidence.losses,3)
  t.eq(dense.evidence.cause,'send-refused')
  t.eq(m:next_delay()<=4,true,'dense cadence')
  local history=canon.decode(R.files['/etc/hv/probe-history.json'])
  t.eq(history[#history].kind,'suspicion-start');t.eq(history[#history].reason,'heartbeat-lost')
  for _=1,10 do R.advance(1);t.eq(m:fast_tick(),false,'disarmed until an answer') end
  -- the switch turned off: sockets closed at the next beat, nothing more is sent
  R.config=ON:gsub("'1'\n$","'0'\n");R.config_version=R.config_version+1
  local sent=R.sent
  R.advance(1);m:fast_tick();R.advance(1);m:fast_tick()
  t.eq(R.sent,sent);t.eq(m.fast.active,false)
end)

t.test('monitor: a suspect while Auto does not watch is declined and offered again after the hold',function()
  local R,m=fresh(ON)
  m:pass()
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='APPLYING'}))
  R.down.wgclient='refused'
  for _=1,8 do R.advance(1);t.eq(m:fast_tick(),false) end
  t.eq(m.booster:dense(R.wall()),nil)
  t.eq(m.fast.channels[SOURCE].armed,true,'not disarmed: nothing was confirmed')
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING'}))
  local started=false
  for _=1,fast.RETRY do R.advance(1);started=started or m:fast_tick() end
  t.eq(started,true)
end)

------------------------------------------------------------------------------------------------------
-- acceptance simulation (virtual clock): owner level 1 (pass every 60 s, boost 10 s), recovery_failures 3.
-- A pass through a failing channel takes FAIL_PASS s (curl -m 6 waits for SYNs the firewall dropped), a
-- healthy pass OK_PASS s. Its samples carry the pass start; Auto sees them when the pass is published and
-- evaluates pair.streak (the unchanged rule: 3 failures of the source, 2 successes of the reserve) every 2 s.
------------------------------------------------------------------------------------------------------
local FAIL_PASS,OK_PASS=7,2
local function simulate(config,faults,mode,total)
  local R,m=fresh(config)
  local start=R.clock()
  local function fault_at(x) for _,f in ipairs(faults) do if x>=f[1] and x<f[1]+f[2] then return true end end;return false end
  local next_pass,busy_until,visible=0,-1,nil
  local pending
  local decided,flagged={},{}
  for second=0,total do
    local down=fault_at(second)
    R.down.wgclient=down and mode or nil
    if pending and second>=pending.at then visible=pending.status;pending=nil end
    if second>=next_pass and second>=busy_until then
      local status=m:pass()
      local d=down and FAIL_PASS or OK_PASS
      m.pass_seconds=d
      pending={at=second+d,status=status}
      busy_until=second+d
      next_pass=second+math.max(d,math.floor(m:next_delay()+d+0.5))
    end
    if m:fast_tick() then flagged[#flagged+1]=second;if second>=busy_until then next_pass=second+1 else next_pass=busy_until end end
    if visible and second%2==0 then
      local valid=monitor.observation_valid_for(settings())
      local failed=pair.streak(visible.samples,SOURCE,3,R.wall(),valid,false)
      local healthy=pair.streak(visible.samples,TARGET,2,R.wall(),valid,true)
      if failed and healthy then decided[#decided+1]=second end
    end
    R.advance(1)
  end
  local results={}
  for i,f in ipairs(faults) do
    local first
    for _,s in ipairs(decided) do if s>=f[1] and s<f[1]+f[2]+60 then first=s;break end end
    results[i]=first and (first-f[1]) or false
  end
  return results,decided,flagged,R.clock()-start
end

local OUTAGES={{100,150},{500,150},{900,150},{1300,150}}
local BLIPS={{100,4},{300,8},{500,12},{700,4},{705,4}}

t.test('acceptance: four 150 s outages (firewall drop and black hole) are confirmed fast; slower without the pulse',function()
  for _,mode in ipairs({'refused','blackhole'}) do
    local with=simulate(ON,OUTAGES,mode,1700)
    local without=simulate("config main 'main'\n",OUTAGES,mode,1700)
    for i=1,4 do
      t.truthy(with[i],mode..' outage '..i..' confirmed with the pulse')
      t.truthy(with[i]<=35,mode..' outage '..i..' confirmed within 35 s, got '..tostring(with[i]))
      t.truthy(without[i],mode..' outage '..i..' confirmed without the pulse too')
      t.truthy(with[i]<without[i],mode..' outage '..i..': faster with the pulse ('..with[i]..' vs '..without[i]..')')
    end
    print(string.format('  %s: Auto streak met after %s s with the pulse, %s s without (level 1)',mode,table.concat(with,'/'),table.concat(without,'/')))
  end
end)

t.test('acceptance: blips of 4-12 s (and two 4 s blips 1 s apart) never satisfy the switch rule',function()
  for _,mode in ipairs({'refused','blackhole'}) do
    local _,decided,flagged=simulate(ON,BLIPS,mode,900)
    t.eq(#decided,0,mode..': no switch decision for blips, got '..table.concat(decided,','))
    t.truthy(#flagged>=1,mode..': the pulse did notice')
  end
end)

t.test('the shortest outage that satisfies the switch rule with the pulse (any phase) is well above a blip',function()
  for _,mode in ipairs({'refused','blackhole'}) do
    local shortest
    for length=4,40,2 do
      for phase=0,9,3 do
        local result=simulate(ON,{{100+phase,length}},mode,260)
        if result[1] and (not shortest or length<shortest) then shortest=length end
      end
      if shortest then break end
    end
    t.truthy(shortest and shortest>=14,mode..': shortest confirmed outage '..tostring(shortest))
    print(string.format('  %s: shortest outage confirmed with the pulse: %s s',mode,tostring(shortest)))
  end
end)

t.run()
