-- Per-target probe log (docs/architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md): the Lua twin replays every shared case of
-- router/tests/probe_target_log_cases.json (byte-identical lines, the same parsing, argument checks, selection and ring
-- rotation), then the heartbeat counters of fast_detect.lua, the monitor wiring (option, pair channels only, never
-- fails a pass) and the RPC probe_targets. Python twin: tests/test_probe_target_log.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local log=require('probe_target_log')
local fast=require('fast_detect')
local monitor=require('monitor')
local rpc=require('rpc')
local probe=require('probe')
local u16=t.u16

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../probe_target_log_cases.json'))
local NULL=canon.null

-- canon values (null, float boxes, arrays, objects) to plain comparable ones
local function norm(v)
  if v==nil or v==NULL then return '<null>' end
  if canon.is_float(v) then return v.value end
  if type(v)=='table' then local out={};for k,x in pairs(v) do out[k]=norm(x) end;return out end
  return v
end
local function same(a,b)
  a,b=norm(a),norm(b)
  if type(a)~=type(b) then return false end
  if type(a)~='table' then return a==b end
  for k,v in pairs(a) do if not same(v,b[k]) then return false end end
  for k,v in pairs(b) do if a[k]==nil and v~='<null>' then return false end end
  return true
end
local function show(v)
  v=norm(v)
  if type(v)~='table' then return tostring(v) end
  local keys={};for k in pairs(v) do keys[#keys+1]=k end
  table.sort(keys,function(x,y) return tostring(x)<tostring(y) end)
  local parts={};for _,k in ipairs(keys) do parts[#parts+1]=tostring(k)..'='..show(v[k]) end
  return '{'..table.concat(parts,',')..'}'
end
local function check(actual,expected,message)
  if not same(actual,expected) then error((message or 'differs')..': got '..show(actual)..', expected '..show(expected),2) end
end

------------------------------------------------------------------------------------------------------
-- shared cases
------------------------------------------------------------------------------------------------------
t.test('encode: every shared case gives the byte-identical line',function()
  t.truthy(#CASES.encode>=300)
  for i,case in ipairs(CASES.encode) do
    local got=log.encode(case.seq,case.result,case.dense,case.hb,case.now)
    local want=case.expected
    if want==NULL then want=nil end
    if got~=want then error(i..' '..case.name..': got '..tostring(got)..' expected '..tostring(want),0) end
  end
end)

t.test('parse_line: every shared case',function()
  for i,case in ipairs(CASES.parse) do check(log.parse_line(case.line),case.expected,i..' '..case.line) end
end)

t.test('select: every shared case (torn lines, garbage, after, limit)',function()
  for i,case in ipairs(CASES.select) do check(log.select(case.old,case.new,case.after,case.limit),case.expected,i..' '..case.name) end
end)

t.test('arguments: the same accepted and refused requests',function()
  for i,case in ipairs(CASES.arguments) do
    local ok,after,limit=pcall(log.arguments,case.request)
    if type(case.expected)=='string' then
      t.truthy(not ok,i..' must be refused');t.eq(type(after)=='table' and after.code or after,case.expected,tostring(i))
    else
      t.truthy(ok,i..' must be accepted: '..tostring(type(after)=='table' and after.code or after))
      check({after,limit},case.expected,tostring(i))
    end
  end
end)

local function ring_runner()
  local R={files={}}
  function R.read_file(path) return R.files[path] end
  function R.append(path,text) R.files[path]=(R.files[path] or '')..text end
  function R.rename(from,to) R.files[to]=R.files[from];R.files[from]=nil end
  return R
end

t.test('ring: every shared scenario leaves the same two segments after each batch',function()
  for _,scenario in ipairs(CASES.ring) do
    local R=ring_runner()
    local initial=scenario.initial
    if initial.current~=NULL then R.files['/ring/probe-targets.log']=initial.current end
    if initial.previous~=NULL then R.files['/ring/probe-targets.log.1']=initial.previous end
    local writer=log.Writer(R,'/ring',scenario.segment)
    for index,batch in ipairs(scenario.batches) do
      local written=writer:record(batch.results,batch.hb~=NULL and batch.hb or nil,batch.dense,batch.now)
      local state=scenario.states[index]
      check(written,state.written,scenario.name..' batch '..index..' written')
      check(R.files['/ring/probe-targets.log'],state.current,scenario.name..' batch '..index..' current')
      check(R.files['/ring/probe-targets.log.1'],state.previous,scenario.name..' batch '..index..' previous')
    end
  end
end)

------------------------------------------------------------------------------------------------------
-- the ring is bounded
------------------------------------------------------------------------------------------------------
t.test('ring: 50000 lines never hold more than 256 KiB and the newest lines are kept',function()
  local R=ring_runner()
  local writer=log.Writer(R,'/ring')
  local row={id='wireguard:peer_7',time=1762243200,code=NULL,dns_ok=true,probe_checks=canon.array({
    canon.object({target='one.one.one.one',result='ok',elapsed_ms=143.5}),canon.object({target='dns.google',result='ok',elapsed_ms=61.2}),
    canon.object({target='dns.quad9.net',result='ok',elapsed_ms=88.0})})}
  local peak=0
  for i=1,25000 do
    writer:record({row,row},{['wireguard:peer_7']={10,0,10,1,0,0,0,0}},false,1762243200+i)
    local total=#(R.files['/ring/probe-targets.log'] or '')+#(R.files['/ring/probe-targets.log.1'] or '')
    if total>peak then peak=total end
  end
  t.truthy(peak<=256*1024,'peak '..peak)
  t.truthy(peak>200*1024,'the ring really fills: '..peak)
  local reply=log.select(R.files['/ring/probe-targets.log.1'],R.files['/ring/probe-targets.log'],0,5000)
  t.eq(reply.last,50000);t.truthy(reply.first>1);t.truthy(reply.count>=1598 and reply.count<=3200,'two segments of at most 1598 lines of 82 bytes: '..reply.count)
  t.eq(reply.count,50000-reply.first+1,'no gap inside the ring')
end)

------------------------------------------------------------------------------------------------------
-- heartbeat counters of the pulse
------------------------------------------------------------------------------------------------------
local SOURCE,TARGET='wireguard:peer_7','wireguard:peer_8'
local PAIR={source=SOURCE,target=TARGET}
local ON="config main 'main'\n\toption enabled '1'\n\toption lua_fast_detect '1'\n"

local function reply(packet,target)
  local echo='\0\0'..u16(0)..string.sub(packet,5)
  echo='\0\0'..u16(probe.icmp_checksum(echo))..string.sub(echo,5)
  local a,b,c,d=string.match(target,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  return '\69\0'..u16(20+#echo)..u16(1)..u16(0)..'\64\1'..u16(0)..string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d))..'\10\0\0\2'..echo
end
-- R.silent[device][target]=true: that target never answers; R.down[device]='blackhole': nobody answers
local function network(R)
  R.down={};R.silent={};R.sent=0
  function R.beat_socket(device)
    local inbox={}
    local h={}
    function h:send(target,packet)
      R.sent=R.sent+1
      local mode=R.down[device]
      local quiet=R.silent[device] and R.silent[device][target]
      if mode~='blackhole' and not quiet then inbox[#inbox+1]=reply(packet,target) end
      return true
    end
    function h:recv() return table.remove(inbox,1) end
    function h:close() end
    return h
  end
  local https,datagram=R.https_get,R.datagram
  function R.https_get(device,address,hostname,path,seconds,cb,agent)
    if R.down[device] then cb(nil,'timeout');return end
    return https(device,address,hostname,path,seconds,cb,agent)
  end
  function R.datagram(kind,device,host,port,packet,seconds,accept,cb)
    if kind=='udp' and R.down[device] then cb(nil,'timeout');return end
    return datagram(kind,device,host,port,packet,seconds,accept,cb)
  end
  R.append=function(path,text) if R.append_fails then error('disk full',0) end;R.files[path]=(R.files[path] or '')..text end
  R.rename=function(from,to) R.files[to]=R.files[from];R.files[from]=nil end
  return R
end
local function frows()
  return {{id=SOURCE,device='wgclient',mark=0x1000,table='53',ifindex=20},{id=TARGET,device='wgclient2',mark=0x2000,table='54',ifindex=21}}
end

t.test('pulse: every judged echo is counted per target, misses too, and take_heartbeat resets',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),PAIR,'OBSERVING')
  R.silent.wgclient={['8.8.8.8']=true}
  for _=1,10 do R.advance(1);p:tick(R.clock()) end
  t.eq(p:take_heartbeat(SOURCE),{5,0,4,4,0,0,0,0},'1.1.1.1 answered, 8.8.8.8 silent')
  t.eq(p:take_heartbeat(TARGET),{5,0,4,0,0,0,0,0})
  t.eq(p:take_heartbeat(SOURCE),{0,0,0,0,0,0,0,0},'reset')
  t.eq(p:take_heartbeat('wireguard:peer_99'),nil)
end)

t.test('pulse with the quorum option: three targets per beat, other pool targets are the fourth slot',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),PAIR,'OBSERVING',{quorum=true})
  R.silent.wgclient={['1.1.1.1']=true}
  for _=1,6 do R.advance(1);p:tick(R.clock()) end
  local hb=p:take_heartbeat(SOURCE)
  local sent=0;for i=1,8,2 do sent=sent+hb[i] end
  t.eq(sent,15,'5 judged beats of 3 echoes')
  t.truthy(hb[7]>0,'pool targets other than the three named ones');t.truthy(hb[2]>0 or hb[1]==0,'a silent 1.1.1.1 shows as misses')
end)

t.test('pulse: a paused pulse and a dropped channel count nothing and lose nothing',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),PAIR,'OBSERVING')
  for _=1,4 do R.advance(1);p:tick(R.clock()) end
  local before=p:take_heartbeat(SOURCE)
  t.truthy(before[1]>0)
  p:configure(false,frows(),PAIR,'OBSERVING')
  t.eq(p:take_heartbeat(SOURCE),nil)
end)

------------------------------------------------------------------------------------------------------
-- the monitor
------------------------------------------------------------------------------------------------------
local function settings(extra)
  local s={enabled=true,interval=60,probe_level=1,checkpoint=900,probe_limit=16,live_log_limit=2000,history_days=7,
    plan_source=SOURCE,plan_target=TARGET,plan_source_tunnel='wireguard:wgclient',plan_target_tunnel='wireguard:wgclient2',
    failure_model='consecutive'}
  for k,v in pairs(extra or {}) do s[k]=v end
  return s
end
local function fresh(config,extra,servers,third)
  local data=t.inventory({settings=settings(extra)})
  if servers then data.servers=servers end
  if third then  -- a third, really probed channel that is not part of the Auto pair
    data.profiles[#data.profiles+1]={id='wireguard:peer_9',section='peer_9',protocol='wireguard',name='Rome',group_id='1',profile_id='9',
      vendor_profile_group_id='wireguard:1',vendor_tunnel_id='wireguard:wgclient3',interface='wgclient3',administrative_state='enabled'}
  end
  local R=network(t.fake_runner({config=config,inventory=data}))
  if third then
    R.interfaces.wgclient3={up=true,l3_device='wgclient3',proto='wgclient'};R.marks.wgclient3={mark=0x3000,table='55'}
    R.counters.wgclient3={ifindex=22,rx=100,tx=200}
  end
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  local ticks=0
  function R.hires() ticks=ticks+1;R.mono=R.mono+0.04;return R.mono end  -- every HTTPS check takes a visible time
  return R,monitor.new(R)
end
local LOG='/run/hv/probe-targets.log'
local function lines(R) local out={};for line in string.gmatch(R.files[LOG] or '','[^\n]+') do out[#out+1]=log.parse_line(line) end;return out end

t.test('monitor: option on writes one line per Auto channel per pass, from the pass itself',function()
  local R,m=fresh(nil,{probe_target_log=true})
  local status=m:pass()
  local rows=lines(R)
  t.eq(#rows,2);t.eq(rows[1][1],1);t.eq(rows[2][1],2)
  t.eq(rows[1][3],SOURCE);t.eq(rows[2][3],TARGET)
  t.eq(rows[1][2],math.floor(status.profiles[1].time),'the time of the probe')
  t.eq(rows[1][4],0,'verdict ok');t.eq(rows[1][5],0,'not dense');t.eq(rows[1][7],0,'dns answered');t.eq(#rows[1][8],0,'no heartbeat without the pulse')
  for index=1,3 do
    t.eq(rows[1][6][2*index-1],0,'target '..index..' ok')
    t.truthy(rows[1][6][2*index]>=0,'latency in ms')
  end
  R.advance(10);m:pass()
  rows=lines(R);t.eq(#rows,4);t.eq(rows[3][1],3);t.eq(rows[4][1],4)
end)

t.test('monitor: a dense confirmation pass is flagged',function()
  local R,m=fresh(nil,{probe_target_log=true})
  m:pass();R.advance(10)
  m.booster.dense=function() return {reason='heartbeat-lost'} end
  m:pass()
  local rows=lines(R)
  t.eq({rows[1][5],rows[2][5],rows[3][5],rows[4][5]},{0,0,1,1})
end)

t.test('monitor: option off or absent writes nothing',function()
  for _,extra in ipairs({{probe_target_log=false},{}}) do
    local R,m=fresh(nil,extra)
    m:pass();R.advance(10);m:pass()
    t.eq(R.files[LOG],nil)
  end
end)

t.test('monitor: only the two Auto channels are logged',function()
  local servers={{id='cfg1',profile='wireguard:peer_7',name='Main',channel='primary',priority=10,enabled=true},
    {id='cfg2',profile='wireguard:peer_8',name='Reserve',channel='reserve',priority=20,enabled=true},
    {id='cfg3',profile='wireguard:peer_9',name='Rome',channel='default',priority=30,enabled=true}}
  local R,m=fresh(nil,{probe_target_log=true},servers,true)
  local status=m:pass()
  t.eq(#status.profiles,3,'three channels are observed');t.eq(status.profiles[3].id,'wireguard:peer_9')
  t.eq(status.profiles[3].https_success,3,'the third channel was really probed')
  local ids={};for _,row in ipairs(lines(R)) do ids[#ids+1]=row[3] end
  t.eq(ids,{SOURCE,TARGET})
end)

t.test('monitor: a failing channel is logged with its verdict and per-target codes',function()
  local R,m=fresh(nil,{probe_target_log=true})
  R.down.wgclient='blackhole'
  m:pass()
  local row=lines(R)[1]
  t.eq(row[3],SOURCE);t.eq(row[4],2,'VPN-003');t.eq(row[6][1],1,'timeout');t.eq(row[6][3],1);t.eq(row[6][5],1);t.eq(row[7],1,'dns failed')
  t.eq(lines(R)[2][4],0,'the other channel is fine')
end)

t.test('monitor: the heartbeat misses since the previous line ride on the next line',function()
  local R,m=fresh(ON,{probe_target_log=true})
  m:pass()
  R.silent.wgclient={['8.8.8.8']=true}
  for _=1,10 do R.advance(1);m:fast_tick() end
  R.advance(1);m:pass()
  local rows=lines(R)
  t.eq(#rows,4)
  t.eq(rows[3][8],{5,0,4,4,0,0,0,0},'source: 8.8.8.8 never answered');t.eq(rows[4][8],{5,0,4,0,0,0,0,0})
  R.advance(10);m:pass()
  rows=lines(R);t.eq(#rows[5][8],0,'no echo judged since: no heartbeat data')
end)

t.test('monitor: an unwritable ring never fails the pass, is logged once and recovers',function()
  local R,m=fresh(nil,{probe_target_log=true})
  R.append_fails=true
  local status=m:pass();R.advance(10);m:pass();R.advance(10)
  t.eq(status.mode,'monitor');t.eq(status.error,nil)
  local count=0;for _,line in ipairs(R.logs) do if string.find(line,'probe target log',1,true) then count=count+1 end end
  t.eq(count,1,'one log line for the same fault')
  R.append_fails=false;m:pass()
  t.eq(#lines(R),2);t.eq(m.target_log_error,nil)
end)

t.test('monitor: the sequence continues after a restart from the ring',function()
  local R,m=fresh(nil,{probe_target_log=true})
  m:pass();R.advance(10);m:pass()
  local files=R.files
  local R2,m2=fresh(nil,{probe_target_log=true})
  R2.files[LOG]=files[LOG]
  m2:pass()
  local rows=lines(R2);t.eq(#rows,6);t.eq(rows[5][1],5)
end)

------------------------------------------------------------------------------------------------------
-- the RPC
------------------------------------------------------------------------------------------------------
t.test('rpc probe_targets: rows after a cursor, a limit, the codes of refused arguments, FALLBACK without the log reader',function()
  local R,m=fresh(nil,{probe_target_log=true})
  for _=1,3 do m:pass();R.advance(10) end
  local all=m.rpc.handle('probe_targets','{}')
  t.eq(all.count,6);t.eq(all.first,1);t.eq(all.last,6);t.eq(all.truncated,false);t.eq(all.targets,{'one.one.one.one','dns.google','dns.quad9.net'})
  t.eq(all.rows[1][3],SOURCE)
  local part=m.rpc.handle('probe_targets','{"after":2,"limit":3}')
  t.eq(part.count,3);t.eq(part.rows[1][1],3);t.eq(part.truncated,true);t.eq(part.last,6)
  t.eq(m.rpc.handle('probe_targets','{"after":6}').count,0)
  t.eq(m.rpc.handle('probe_targets','{"limit":0}').error,'RPC-INPUT-INVALID')
  t.eq(m.rpc.handle('probe_targets','{"after":-1}').error,'RPC-INPUT-INVALID')
  t.eq(m.rpc.handle('probe_targets','{"x":1}').error,'RPC-UNEXPECTED-ARGS')
  t.eq(m.rpc.handle('probe_targets','[1]').error,'RPC-INPUT-OBJECT')
  t.eq(canon.encode(m.rpc.handle('probe_targets','{"limit":1}')):sub(1,1),'{')
  local bare=rpc.new({version='x',now=function() return 1 end,status=function() return nil end,native_status=function() return canon.object() end,
    inventory=function() return canon.object() end},R)
  t.truthy(bare.handle('probe_targets','{}')==rpc.FALLBACK,'agent.py answers from the same files')
  t.eq(rpc.PROBE_LOG,{'probe_targets'})
end)

t.test('rpc: the ubus object offers probe_targets and the bridge answers it through the reply file',function()
  local R,m=fresh(nil,{probe_target_log=true})
  m:pass()
  local conn={replies={}}
  function conn:reply(req,value) self.replies[#self.replies+1]=value end
  local object=m.rpc.ubus_object(conn,{STRING=1})
  t.truthy(object['homensai-vpn-lua'].probe_targets~=nil)
  object['homensai-vpn-lua'].probe_targets[1]({},'{"limit":1}')
  t.eq(conn.replies[1].count,1)
  local request,out='/run/hv/rpc-in.AbC123','/run/hv/rpc-out.AbC123'
  R.files[request]='{"after":1}'
  t.eq(m.rpc.bridge_call({method='probe_targets',request_file=request,reply_file=out}),{ok=true})
  t.eq(canon.decode(R.files[out]).count,1)
end)

t.run()
