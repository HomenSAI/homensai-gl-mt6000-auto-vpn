-- CUSUM trigger, RTT watch, RTT log (docs/architecture/CUSUM-TRIGGER-2026-11-04.ru.md): the Lua twins replay every shared case
-- of router/tests/cusum_cases.json (cusum.lua, probe_policy.lua), then the pulse (fast_detect.lua), the monitor wiring and
-- the socket stamps (monitor_io.lua) with fakes. Python twin: tests/test_cusum.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local cusum=require('cusum')
local policy=require('probe_policy')
local fast=require('fast_detect')
local probe=require('probe')
local rtt_log=require('heartbeat_rtt_log')
local monitor=require('monitor')
local u16=t.u16

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../cusum_cases.json'))
local SOURCE,TARGET='wireguard:peer_7','wireguard:peer_8'
local PAIR={source=SOURCE,target=TARGET}
local function plain(v) if v==canon.null then return nil end;if canon.is_float(v) then return v.value end;return v end
local function close(a,b,message)
  a,b=plain(a),plain(b)
  if a==nil and b==nil then return end
  if type(a)~='number' or type(b)~='number' or math.abs(a-b)>1e-9 then error((message or 'differs')..': got '..tostring(a)..', expected '..tostring(b),2) end
end

------------------------------------------------------------------------------------------------------
-- shared cases
------------------------------------------------------------------------------------------------------
t.test('constants equal the Python twin',function()
  local c=CASES.constants
  close(cusum.LOST_STEP,c.lost_step);close(cusum.KEPT_STEP,c.kept_step);t.eq(cusum.H,c.h);t.eq(cusum.CAP,c.cap);t.eq(cusum.GATE,c.gate)
  for _,row in ipairs(CASES.gaps) do t.eq(policy.cusum_gap(row[1]),row[2]) end
end)

t.test('LossCusum: every shared case, beat by beat',function()
  t.truthy(#CASES.loss>=30)
  for _,case in ipairs(CASES.loss) do
    local c=cusum.LossCusum();local fired=canon.array()
    for i,beat in ipairs(case.beats) do
      if c:feed(beat[1]==1,plain(beat[2])) then fired[#fired+1]=i-1 end
      close(c.s,case.trace[i],case.name..' beat '..i)
    end
    t.eq(fired,case.fired,case.name);t.eq(c.gated,case.gated,case.name);t.eq(c.fired,case.count,case.name)
  end
end)

t.test('RttWatch: every shared case, state by state',function()
  for _,case in ipairs(CASES.rtt) do
    local w=cusum.RttWatch();local runs={}
    for _,beat in ipairs(case.beats) do
      local s=w:feed(plain(beat[1]),plain(beat[2]))
      if #runs>0 and runs[#runs][1]==s then runs[#runs][2]=runs[#runs][2]+1 else runs[#runs+1]={s,1} end
    end
    t.eq(#runs,#case.states,case.name)
    for i,run in ipairs(runs) do t.eq(run[1],case.states[i][1],case.name);t.eq(run[2],case.states[i][2],case.name) end
    t.eq(w.raised,case.raised,case.name);t.eq(w.relearned,case.relearned,case.name);t.eq(w.base==nil,case.learning,case.name)
    close(w.z,case.z,case.name);close(w.drift,case.drift,case.name)
  end
end)

local function memory_booster() return policy.Booster('/virtual/run','/virtual/flash',{read_json=function(_,default) return default end,write_json=function() end}) end
local SETTINGS=canon.object({interval=10,probe_level=5})
local function row(profile,good)
  if good then return canon.object({id=profile,code=canon.null,dns_ok=true,https_success=3}) end
  return canon.object({id=profile,code='VPN-003',dns_ok=true,https_success=0})
end
local function snapshot(b,started)
  local state=b.state
  local dense=state.dense
  local rest=canon.is_object(state.suspicion_rest) and state.suspicion_rest[SOURCE] or nil
  local forced=canon.is_object(state.cusum_at) and state.cusum_at[SOURCE] or nil
  local bad=nil
  if dense then bad=dense.bad==true end
  local records=0
  if canon.is_object(state.cusum_at) then for _ in pairs(state.cusum_at) do records=records+1 end end
  return {started=started,records=records,reason=dense and dense.reason or nil,bad=bad,rest_until=rest and rest['until'] or nil,
    alarms=rest and rest.false_alarms or nil,at=forced and forced.at or nil,clean=forced and forced.clean or nil}
end
t.test('Booster: every shared scenario, step by step',function()
  t.truthy(#CASES.booster>=15)
  for _,case in ipairs(CASES.booster) do
    local b=memory_booster()
    for i,step in ipairs(case.steps) do
      local kind,started=step[1],nil
      if kind=='suspect' then
        local models=plain(step[4])
        local evidence=canon.object({losses=0,cause='cusum',other=1})
        started=b:suspect(SETTINGS,{canon.object({profile=SOURCE,reason=step[3],evidence=evidence})},canon.object(PAIR),step[5],plain(step[2]),models)
      elseif kind=='observe' then
        b:observe(SETTINGS,{row(SOURCE,step[3]),row(TARGET,true)},canon.object(PAIR),step[4],plain(step[2]),plain(step[5]))
      else b.state[step[2]]=step[3] end
      local got,expected=snapshot(b,started),case.expected[i]
      local where=case.name..' step '..i
      t.eq(got.started,plain(expected.started),where);t.eq(got.reason,plain(expected.reason),where);t.eq(got.bad,plain(expected.bad),where)
      close(got.rest_until,expected.rest_until,where);t.eq(plain(got.alarms),plain(expected.alarms),where)
      -- a damaged record is left in place until a start rewrites it: only compare what both can read as a record
      local at,clean=plain(expected.at),plain(expected.clean)
      if not string.find(case.name,'damaged',1,true) or expected.started==true then
        close(got.at,at,where);t.eq(plain(got.clean),clean,where);t.eq(got.records,expected.records,where)
      end
    end
  end
end)

t.test('Booster: the CUSUM record survives the end of a boost (state, RAM file)',function()
  local b=memory_booster()
  local settings=SETTINGS
  t.eq(b:suspect(settings,{canon.object({profile=SOURCE,reason='cusum-loss'})},canon.object(PAIR),'OBSERVING',1000),true)
  b:observe(settings,{row(SOURCE,false),row(TARGET,true)},canon.object(PAIR),'OBSERVING',1004)
  t.eq(b:active(),true)
  b:observe(settings,{row(SOURCE,true),row(TARGET,true)},canon.object(PAIR),'OBSERVING',1008)
  b:observe(settings,{row(SOURCE,true),row(TARGET,true)},canon.object(PAIR),'OBSERVING',1012)
  t.eq(b:dense(1012),nil,'the episode ended before the boost does: only CARRIED can keep the record')
  b:observe(settings,{row(SOURCE,true),row(TARGET,true)},canon.object(PAIR),'OBSERVING',1700)
  t.eq(b:active(),false)
  t.truthy(canon.is_object(b.state.cusum_at) and canon.is_object(b.state.cusum_at[SOURCE]),'carried through the boost end')
  t.truthy(canon.encode(b.state),'encodable')
end)

------------------------------------------------------------------------------------------------------
-- the pulse
------------------------------------------------------------------------------------------------------
local function reply(packet,target)
  local echo='\0\0'..u16(0)..string.sub(packet,5)
  echo='\0\0'..u16(probe.icmp_checksum(echo))..string.sub(echo,5)
  local a,b,c,d=string.match(target,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  return '\69\0'..u16(20+#echo)..u16(1)..u16(0)..'\64\1'..u16(0)..string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d))..'\10\0\0\2'..echo
end
-- R.drop(device, target) -> true: this echo gets no reply; 'refused': the send is refused. R.rtt[target]: the arrival stamp.
local function network(R)
  R.sent=0;R.opened=0;R.drop=function() return false end;R.rtt={}
  function R.beat_socket(device)
    R.opened=R.opened+1
    local inbox={}
    local h={}
    function h:send(target,packet)
      R.sent=R.sent+1
      local verdict=R.drop(device,target)
      if verdict=='refused' then return nil,'refused' end
      if not verdict then
        local ms=R.rtt[target]
        inbox[#inbox+1]={reply(packet,target),ms and R.hires()+ms/1000 or nil}
      end
      return true
    end
    function h:recv() local x=table.remove(inbox,1);if x then return x[1],x[2] end;return nil end
    function h:close() end
    return h
  end
  local sysfs=R.sysfs
  function R.sysfs(device,name)
    if name=='operstate' then return 'unknown' end
    if name=='statistics/rx_packets' or name=='statistics/tx_packets' or name=='statistics/rx_bytes' or name=='statistics/tx_bytes' then return tostring(1000+(R.bytes or 0)) end
    return sysfs(device,name)
  end
  return R
end
local function rows()
  return {{id=SOURCE,device='wgclient',mark=0x1000,table='53',ifindex=20},{id=TARGET,device='wgclient2',mark=0x2000,table='54',ifindex=21}}
end
local function pulse(R,options) local p=fast.Pulse(R);p:configure(true,rows(),PAIR,'OBSERVING',options or {cusum=true});return p end
-- pattern per beat for the source channel; returns the reasons of the suspects, one per beat ('' = none)
local function play(p,R,pattern)
  local out={}
  for i=1,#pattern do
    local c=string.sub(pattern,i,i)
    R.drop=function(device,target)
      if device~='wgclient' then return false end
      if c=='x' then return true end
      if c=='r' then return 'refused' end
      return false
    end
    R.advance(1)
    local found=p:tick(R.clock())
    out[i]=''
    if found then for _,ch in ipairs(found) do if ch.id==SOURCE then out[i]=ch.suspect_reason end end end
  end
  return out
end
local function count(list,reason) local n=0;for _,v in ipairs(list) do if v==reason then n=n+1 end end;return n end

t.test('pulse: three of five lost echoes fire a suspect with reason cusum-loss, on the beat that judges the echo',function()
  local R=network(t.fake_runner());local p=pulse(R)
  -- the outcome of the echo of beat n is known at beat n+1
  local out=play(p,R,'....xx.x....')
  t.eq(count(out,'cusum-loss'),1)
  t.eq(p.channels[SOURCE].cusum.fired,1)
  t.eq(out[9],'cusum-loss','judged one beat after the third lost echo was sent')
  t.eq(p.channels[TARGET].cusum.fired,0)
end)

t.test('pulse: off by default, no detector runs and the old rule is exact (same suspects, same packets)',function()
  local function run(options)
    local R=network(t.fake_runner());local p=pulse(R,options)
    local out=play(p,R,string.rep('.',20)..'xx.x.xx...xxxxxx....x.x.x.'..string.rep('.',20))
    return out,R.sent,p
  end
  local off,sent_off,p=run({});t.eq(p.channels[SOURCE].cusum.beat,0,'not fed');t.eq(p.opts.cusum,false)
  local defaulted=fast.Pulse(t.fake_runner());t.eq(defaulted.opts.cusum,false);t.eq(defaulted.opts.rtt,false)
  local on,sent_on=run({cusum=true})
  t.eq(sent_on,sent_off,'not one packet more')
  t.eq(count(off,'cusum-loss'),0);t.truthy(count(on,'cusum-loss')>0)
end)

t.test('pulse: a healthy trace is the same with the detector on (no suspect, no extra packet)',function()
  local function run(options)
    local R=network(t.fake_runner());local p=pulse(R,options)
    return play(p,R,string.rep('.',3600)),R.sent
  end
  local off,sent_off=run({});local on,sent_on=run({cusum=true,rtt=true})
  t.eq(sent_on,sent_off);t.eq(on,off);t.eq(count(on,''),3600)
end)

t.test('pulse: a blackout alone never fires, the heartbeat rule stays the one that sees it',function()
  local R=network(t.fake_runner());local p=pulse(R)
  local out=play(p,R,'...'..string.rep('x',60))
  t.eq(count(out,'cusum-loss'),0);t.truthy(count(out,fast.REASON)>0)
end)

t.test('pulse: one filtered target never fires; both targets lossy do',function()
  local R=network(t.fake_runner());local p=pulse(R)
  R.advance(1);p:tick(R.clock())
  local seen=0
  for i=1,200 do
    R.drop=function(device,target) return device=='wgclient' and target=='8.8.8.8' end
    R.advance(1)
    local found=p:tick(R.clock())
    if found then for _,ch in ipairs(found) do if ch.suspect_reason=='cusum-loss' then seen=seen+1 end end end
  end
  t.eq(seen,0);t.truthy(p.channels[SOURCE].cusum.gated>5,'gated, not unnoticed')
  local R2=network(t.fake_runner());local p2=pulse(R2)
  t.eq(count(play(p2,R2,'...x.xx.'..'..'),'cusum-loss'),1)
end)

t.test('pulse: a vetoed echo keeps its target: one filtered target on a loaded tunnel is gated too',function()
  local R=network(t.fake_runner());local p=pulse(R,{stall=true,veto=true,cusum=true})
  local seen=0
  for i=1,120 do
    if i>6 then R.drop=function(device,target) return device=='wgclient' and target=='8.8.8.8' end end
    R.bytes=(R.bytes or 0)+2000
    R.advance(1)
    local found=p:tick(R.clock())
    if found then for _,ch in ipairs(found) do if ch.suspect_reason=='cusum-loss' then seen=seen+1 end end end
  end
  t.truthy(p.channels[SOURCE].vetoed>10,'the beats were vetoed');t.eq(seen,0);t.truthy(p.channels[SOURCE].cusum.gated>5)
end)

t.test('pulse: a fire needs neither armed nor the end of a hold',function()
  local R=network(t.fake_runner());local p=pulse(R)
  play(p,R,'...')
  p:hold(SOURCE,R.clock()+1000);p:disarm(SOURCE)
  t.eq(count(play(p,R,'.x..x.x..'),'cusum-loss'),1)
  t.truthy(p.channels[SOURCE].hold_until>R.clock(),'the hold of the heartbeat rule stays')
end)

t.test('pulse: an unanswered echo is attributed to the target it was sent to, not to the target of the judging beat',function()
  local R=network(t.fake_runner());local p=pulse(R)
  R.advance(1);p:tick(R.clock())             -- echo to 1.1.1.1 (round 1)
  R.drop=function(device) return device=='wgclient' end
  R.advance(1);p:tick(R.clock())             -- judged the first echo; echo to 8.8.8.8 goes unanswered
  R.drop=function() return false end
  R.advance(1);p:tick(R.clock())             -- round 3 judges the 8.8.8.8 echo
  t.eq(p.channels[SOURCE].cusum.seen['8.8.8.8'],3-1,'the second fed beat');t.eq(p.channels[SOURCE].cusum.seen['1.1.1.1'],nil)
end)

t.test('pulse: a vetoed echo still counts as lost for the detector (traffic does not disprove partial loss)',function()
  local R=network(t.fake_runner());local p=pulse(R,{stall=true,veto=true,cusum=true})
  local function step(c)
    R.bytes=(R.bytes or 0)+2000
    return play(p,R,c)[1]
  end
  local fired=0
  for i=1,6 do step('.') end
  for c in string.gmatch('xx.x....','.') do if step(c)=='cusum-loss' then fired=fired+1 end end
  t.truthy(p.channels[SOURCE].vetoed>=3,'the beats were vetoed');t.eq(fired,1)
  t.eq(p.channels[SOURCE].lost,0,'the old rule saw no lost beat')
end)

t.test('pulse: refused sends have no target and pass the gate; first beat and socket trouble feed nothing',function()
  local R=network(t.fake_runner());local p=pulse(R)
  R.advance(1);p:tick(R.clock());t.eq(p.channels[SOURCE].cusum.beat,0,'the first beat judges nothing')
  -- a refused beat judges nothing of the next one: the second answered beat ends the run
  local out=play(p,R,'.rr..r...')
  t.eq(count(out,'cusum-loss'),1)
  local R2=network(t.fake_runner());local p2=pulse(R2)
  R2.beat_socket=function() return nil,'unavailable' end
  for _=1,5 do R2.advance(1);p2:tick(R2.clock()) end
  t.eq(p2.channels[SOURCE].cusum.beat,0)
end)

t.test('pulse: the speed-test pause empties the sum',function()
  local R=network(t.fake_runner());local paused=false
  local p=fast.Pulse(R,function() return paused end);p:configure(true,rows(),PAIR,'OBSERVING',{cusum=true})
  play(p,R,'..xx.')
  t.truthy(p.channels[SOURCE].cusum.s>0)
  paused=true;R.advance(1);p:tick(R.clock());paused=false
  t.eq(p.channels[SOURCE].cusum.s,0);t.eq(p.channels[SOURCE].cusum.run,0)
end)

t.test('pulse: switched on later, a detector starts empty; a new channel epoch starts empty',function()
  local R=network(t.fake_runner());local p=pulse(R)
  play(p,R,'..xx.')
  local c=p.channels[SOURCE].cusum;t.truthy(c.s>0)
  p:configure(true,rows(),PAIR,'OBSERVING',{});t.truthy(c.s>0,'kept while off')
  p:configure(true,rows(),PAIR,'OBSERVING',{cusum=true});t.eq(c.s,0)
  play(p,R,'..xx.')
  local changed=rows();changed[1].ifindex=33
  p:configure(true,changed,PAIR,'OBSERVING',{cusum=true})
  t.truthy(p.channels[SOURCE].cusum~=c);t.eq(p.channels[SOURCE].cusum.s,0)
end)

t.test('pulse: evidence and status of a fire, encodable, integers only',function()
  local R=network(t.fake_runner());local p=pulse(R)
  local fired
  for c in string.gmatch('....xx.x..','.') do if play(p,R,c)[1]=='cusum-loss' then fired=true;break end end
  t.truthy(fired)
  local ch=p.channels[SOURCE]
  t.eq(p:evidence(ch,R.clock()).cause,'cusum')
  local public=p:public(R.clock(),true)
  t.eq(public.cusum,true);t.eq(public.rtt_watch,false)
  local row1=public.channels[1]
  t.eq(row1.cusum_fired,1);t.eq(row1.congested,false);t.eq(row1.code,canon.null);t.eq(row1.rtt_z_centi,canon.null)
  t.eq(row1.cusum_centi,math.floor(ch.cusum.s*100+0.5))
  t.truthy(canon.encode(public))
end)

t.test('pulse: round trips are taken from the arrival stamp, per target; no stamp, no round trip',function()
  local R=network(t.fake_runner());local p=pulse(R,{})
  R.rtt={['1.1.1.1']=20,['8.8.8.8']=50}
  for _=1,6 do R.advance(1);p:tick(R.clock()) end
  local ch=p.channels[SOURCE]
  t.eq(p:public(R.clock(),true).channels[1].rtt_ms,20,'status shows the newest answer: beat 6 judges the echo to 1.1.1.1');t.eq(p:public(R.clock(),true).channels[1].rtt_age_s,0)
  local got=p:take_rtt(SOURCE)
  t.eq(got['1.1.1.1'],{20,20,20});t.eq(got['8.8.8.8'],{50,50})
  t.eq(next(p:take_rtt(SOURCE)),nil,'taken and emptied');t.eq(p:take_rtt('none'),nil)
  R.rtt={}
  R.advance(1);p:tick(R.clock());p:take_rtt(SOURCE)   -- the echo sent before the stamps stopped
  for _=1,3 do R.advance(1);p:tick(R.clock()) end
  t.eq(next(p:take_rtt(SOURCE)),nil);t.eq(ch.rtt_ms,nil)
  t.eq(p:public(R.clock(),true).channels[1].rtt_ms,50,'the last real answer stays');t.eq(p:public(R.clock(),true).channels[1].rtt_age_s,3)
end)

t.test('pulse: a stamp before the send or too late is no round trip; the list is bounded',function()
  local R=network(t.fake_runner());local p=pulse(R,{})
  local ch=p.channels[SOURCE];local echo={sent_at=100,target='1.1.1.1'}
  p:round_trip(ch,echo,99.9,1);t.eq(ch.rtt_ms,nil)
  p:round_trip(ch,echo,102.5,1);t.eq(ch.rtt_ms,nil)
  p:round_trip(ch,echo,102,1);t.eq(ch.rtt_ms,2000)
  p:round_trip(ch,{target='1.1.1.1'},102,1);t.eq(#ch.rtts['1.1.1.1'],1)
  for _=1,fast.RTT_KEEP+50 do p:round_trip(ch,echo,100.01,1) end
  t.eq(#ch.rtts['1.1.1.1'],fast.RTT_KEEP)
end)

t.test('pulse: the RTT watch raises the soft signal only: status code, a log line, never a suspect',function()
  local R=network(t.fake_runner());local logs={};R.log=function(line) logs[#logs+1]=line end
  local p=pulse(R,{rtt=true})
  local function beat(ms)
    R.rtt={['1.1.1.1']=ms,['8.8.8.8']=ms+25}
    R.advance(1)
    return p:tick(R.clock())
  end
  for i=1,cusum.WARM+40 do t.eq(beat(20+(i%3)),nil) end
  t.eq(p:public(R.clock(),true).channels[1].congested,false);t.eq(p:public(R.clock(),true).channels[1].code,canon.null)
  local raised
  for i=1,200 do
    t.eq(beat(80),nil,'never a suspect')
    if p.channels[SOURCE].congested then raised=i;break end
  end
  t.truthy(raised)
  local row1=p:public(R.clock(),true).channels[1]
  t.eq(row1.code,cusum.CODE);t.eq(row1.congested,true);t.truthy(row1.rtt_z_centi>=400);t.eq(p:public(R.clock(),true).rtt_watch,true)
  local function logged(line) for _,v in ipairs(logs) do if v==line then return true end end;return false end
  t.truthy(logged('rtt watch: '..SOURCE..' CHANNEL-CONGESTED'))
  for _=1,300 do t.eq(beat(20),nil);if not p.channels[SOURCE].congested then break end end
  t.eq(p.channels[SOURCE].congested,false);t.truthy(logged('rtt watch: '..SOURCE..' calm again'))
end)

t.test('pulse: the RTT watch switched off stays silent and is not fed; switched on it learns again',function()
  local R=network(t.fake_runner());local p=pulse(R,{})
  R.rtt={['1.1.1.1']=20,['8.8.8.8']=20}
  for _=1,10 do R.advance(1);p:tick(R.clock()) end
  t.eq(#p.channels[SOURCE].rtt_watch.samples,0)
  p:configure(true,rows(),PAIR,'OBSERVING',{rtt=true})
  for _=1,5 do R.advance(1);p:tick(R.clock()) end
  t.truthy(#p.channels[SOURCE].rtt_watch.samples>0)
  p.channels[SOURCE].congested=true
  p:configure(true,rows(),PAIR,'OBSERVING',{})
  t.truthy(#p.channels[SOURCE].rtt_watch.samples>0,'kept while off')
  p:configure(true,rows(),PAIR,'OBSERVING',{rtt=true})
  t.eq(#p.channels[SOURCE].rtt_watch.samples,0,'old samples are not part of the new start');t.eq(p.channels[SOURCE].congested,false)
end)

------------------------------------------------------------------------------------------------------
-- the per-minute log
------------------------------------------------------------------------------------------------------
t.test('heartbeat_rtt_log: line format, median, groups, refusals',function()
  t.eq(rtt_log.line(1000.7,SOURCE,{['1.1.1.1']={30,10,20,40},['8.8.8.8']={5}}),'[1000,"wireguard:peer_7",4,10,30,40,1,5,5,5,0,0,0,0]\n')
  t.eq(rtt_log.line(1,SOURCE,{['9.9.9.9']={7},['1.0.0.1']={9,8}}),'[1,"wireguard:peer_7",0,0,0,0,0,0,0,0,3,7,8,9]\n')
  t.eq(rtt_log.line(1,SOURCE,{}),nil,'nothing measured: no line');t.eq(rtt_log.line(1,SOURCE,{['1.1.1.1']={}}),nil)
  t.eq(rtt_log.line(1,'bad id"',{['1.1.1.1']={1}}),nil);t.eq(rtt_log.line(1,SOURCE,nil),nil)
  t.truthy(canon.decode(rtt_log.line(1000,SOURCE,{['1.1.1.1']={1}})))
  t.eq(rtt_log.enabled({heartbeat_rtt_log=true}),true);t.eq(rtt_log.enabled({}),false)
end)

t.test('heartbeat_rtt_log: the ring keeps two segments',function()
  local files,renames={},0
  local runner={read_file=function(path) return files[path] end,
    append=function(path,text) files[path]=(files[path] or '')..text end,
    rename=function(from,to) files[to]=files[from];files[from]=nil;renames=renames+1 end}
  local w=rtt_log.Writer(runner,'/run',100)
  t.eq(w:record({{id=SOURCE,targets={}}},1),0);t.eq(files['/run/'..rtt_log.NAME],nil)
  for i=1,4 do t.eq(w:record({{id=SOURCE,targets={['1.1.1.1']={i}}}},i),1) end
  t.truthy(renames>=1,'rotated');t.truthy(#(files['/run/'..rtt_log.NAME])<=100)
  t.truthy(files['/run/'..rtt_log.NAME..'.1'])
  local again=rtt_log.Writer(runner,'/run',1000)
  local before=#(files['/run/'..rtt_log.NAME])
  again:record({{id=SOURCE,targets={['1.1.1.1']={9}}}},9)
  t.truthy(again.size>before,'the size is read after a restart');t.eq(again.size,#(files['/run/'..rtt_log.NAME]))
end)

------------------------------------------------------------------------------------------------------
-- the monitor wiring
------------------------------------------------------------------------------------------------------
local ON="config main 'main'\n\toption enabled '1'\n\toption lua_fast_detect '1'\n"
local function wired(extra)
  local R=network(t.fake_runner())
  R.config_text=function() return ON end
  R.config_mtime=function() return 1 end
  R.files=R.files or {}
  local m=monitor.new(R,{})
  m.settings=canon.object({interval=10,probe_level=5,heartbeat_rtt_log=true,cusum_trigger=true})
  m.fast:configure(true,rows(),PAIR,'OBSERVING',extra or {cusum=true})
  return m,R
end
local function drive(m,R,pattern)
  local out={}
  for c in string.gmatch(pattern,'.') do
    R.drop=function(device) return device=='wgclient' and c=='x' end
    R.advance(1)
    out[#out+1]=m:fast_tick()
  end
  return out
end
local function started(list) local n=0;for _,v in ipairs(list) do if v then n=n+1 end end;return n end

t.test('monitor: both detectors stay off without their options; the options reach the pulse',function()
  local function pass(extra)
    local s={enabled=true,interval=60,probe_level=1,checkpoint=900,probe_limit=16,live_log_limit=2000,history_days=7,plan_source=SOURCE,plan_target=TARGET,
      plan_source_tunnel='wireguard:wgclient',plan_target_tunnel='wireguard:wgclient2'}
    for k,v in pairs(extra) do s[k]=v end
    local R=network(t.fake_runner({config=ON,inventory=t.inventory({settings=s})}))
    R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
    local m=monitor.new(R);m:pass()
    return m
  end
  local off=pass({})
  t.eq(off.fast.active,true);t.eq(off.fast.opts.cusum,false);t.eq(off.fast.opts.rtt,false);t.eq(off.status.fast_detect.cusum,false)
  local on=pass({cusum_trigger=true,rtt_watch=true})
  t.eq(on.fast.opts.cusum,true);t.eq(on.fast.opts.rtt,true)
end)

t.test('monitor: a declined CUSUM fire does not hold the heartbeat rule back',function()
  local m,R=wired()
  m:read_json(m.runtime..'/native-status.json',canon.object())
  m.read_json=function(self,path,default) if string.find(path,'native%-status') then return canon.object({state='BLOCKED'}) end;return default end
  drive(m,R,'...xx.x.')
  t.truthy(m.fast.channels[SOURCE].cusum.fired>=1)
  t.eq(m.fast.channels[SOURCE].hold_until>=R.clock()+0.5 and 'held' or 'free','held','the heartbeat rule offered its own suspect and was declined')
  local m2,R2=wired()
  m2.read_json=m.read_json
  drive(m2,R2,'...x..x.x..')
  t.eq(m2.fast.channels[SOURCE].cusum.fired,1)
  t.eq(m2.fast.channels[SOURCE].hold_until,0,'only a CUSUM fire was declined: no hold')
end)

t.test('monitor: a fire past the suspicion rest starts a dense episode at once; the model that decided stops it',function()
  local m,R=wired()
  m.read_json=function(self,path,default) if string.find(path,'native%-status') then return canon.object({state='OBSERVING'}) end;return default end
  m.booster.state.suspicion_rest=canon.object({[SOURCE]=canon.object({['until']=canon.float(R.wall()+600),false_alarms=5})})
  local out=drive(m,R,'...x..x.x..')
  t.eq(started(out),1);t.eq(m.booster.state.dense.reason,'cusum-loss')
  local m2,R2=wired()
  m2.read_json=m.read_json
  m2.failure_models={[SOURCE]={failed=true}}
  t.eq(started(drive(m2,R2,'...x..x.x..')),0);t.eq(m2.fast.channels[SOURCE].cusum.fired,1)
end)

t.test('monitor: once a minute the round trips reach the RAM log; option off: taken but not written; a write error never reaches the pulse',function()
  local m,R=wired({})
  local written={}
  R.read_file=function(path) return written[path] end
  R.append=function(path,text) written[path]=(written[path] or '')..text end
  R.rtt={['1.1.1.1']=20,['8.8.8.8']=40}
  drive(m,R,string.rep('.',150))
  local text=written[m.runtime..'/'..rtt_log.NAME]
  t.truthy(text,'written');local _,lines=string.gsub(text,'\n','')
  t.eq(lines,4,'two channels, two minutes')
  t.truthy(string.find(text,'"'..SOURCE..'",30,20,20,20,30,40,40,40,0,0,0,0]',1,true) or string.find(text,'"'..SOURCE..'",30,40,40,40,30,20,20,20',1,true) or string.find(text,'"'..SOURCE..'",30,20,20,20,29,40,40,40,0,0,0,0]',1,true) or string.find(text,'"'..SOURCE..'",29,20,20,20,30,40,40,40,0,0,0,0]',1,true) ,text)
  m.settings.heartbeat_rtt_log=false
  written={}
  drive(m,R,string.rep('.',70))
  t.eq(next(written),nil);t.eq(next(m.fast:take_rtt(SOURCE) or {}) ~=nil and #m.fast.channels[SOURCE].rtts or 0,0)
  m.settings.heartbeat_rtt_log=true
  local logs=0
  R.log=function() logs=logs+1 end
  R.append=function() error('disk full') end
  drive(m,R,string.rep('.',130))
  t.eq(logs,1,'logged once');t.truthy(m.fast.active)
end)

------------------------------------------------------------------------------------------------------
-- the socket stamps
------------------------------------------------------------------------------------------------------
t.test('monitor_io.beat_socket: a watched datagram carries its arrival, a flood stops the watch, close removes it',function()
  local inbox,deleted,added={},0,0
  local callback
  local sock={}
  function sock:setopt() return true end
  function sock:setblocking() return true end
  function sock:fileno() return 7 end
  function sock:sendto(packet) return #packet end
  function sock:recvfrom() local d=table.remove(inbox,1);if d then return d end;return false end
  function sock:close() end
  package.loaded['monitor_io']=nil
  package.loaded['nixio']={socket=function() return sock end,gettimeofday=function() return 500,250000 end}
  local ok,err=pcall(function()
    local io_=require('monitor_io')
    -- no loop: no stamp, the old behaviour
    local h0=io_.beat_socket('wgclient1');t.eq(h0:send('1.1.1.1','x'),true)
    inbox={'a'};t.eq({h0:recv()},{'a'})
    io_.attach_loop({fd_add=function(fd,fn) t.eq(fd,7);added=added+1;callback=fn;return {delete=function() deleted=deleted+1 end} end,ULOOP_READ=1})
    local h=io_.beat_socket('wgclient1')
    t.eq(added,0,'no watch before the first send')
    t.eq(h:send('1.1.1.1','x'),true);t.eq(added,1)
    t.eq(h:send('8.8.8.8','x'),true);t.eq(added,1,'one watch for all beats')
    inbox={'one','two'};callback()
    t.eq({h:recv()},{'one',500.25});t.eq({h:recv()},{'two',500.25});t.eq(h:recv(),nil)
    inbox={'late'};t.eq({h:recv()},{'late'},'read without the watch: no stamp')
    t.eq(h:send('8.8.8.8','x'),true)
    -- a flood: the watch stops after BEAT_WAKES wakes and the next send starts it again
    for _=1,io_.BEAT_WAKES do inbox={'noise'};callback() end
    t.eq(deleted,0)
    inbox={'noise'};callback()
    t.eq(deleted,1,'stopped')
    t.eq(h:send('1.1.1.1','x'),true);t.eq(added,2,'started again by the next send')
    -- the queue is bounded
    inbox={}
    for _=1,io_.BEAT_QUEUE*3 do inbox[#inbox+1]='q' end
    callback();callback();callback()
    local n=0
    while h:recv() do n=n+1 end
    t.eq(n,io_.BEAT_QUEUE,'bounded')
    t.eq(h:close(),nil);t.eq(deleted,2,'close removes the watch')
  end)
  package.loaded['nixio']=nil;package.loaded['monitor_io']=nil
  if not ok then error(err,0) end
end)

t.run()
