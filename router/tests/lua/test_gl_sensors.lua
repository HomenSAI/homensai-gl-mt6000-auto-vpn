-- GL sensors (docs/architecture/GL-SENSORS-2026-11-04.ru.md): the Lua twins replay every shared case of
-- router/tests/gl_sensors_cases.json (wan_diag, stall, quorum, wg_events, boot_cause, interruption, diag_bundle,
-- diagnosis.diagnose), then the monitor side (gl_sensors.lua) and the pulse options (fast_detect.lua: stall, veto,
-- quorum) with fakes. Python twin: tests/test_gl_sensors.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local wan=require('wan_diag')
local stall=require('stall')
local quorum=require('quorum')
local wg=require('wg_events')
local boot=require('boot_cause')
local interruption=require('interruption')
local bundle=require('diag_bundle')
local gl=require('gl_sensors')
local fast=require('fast_detect')
local probe=require('probe')
local u16=t.u16

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../gl_sensors_cases.json'))
local NULL='<null>'

-- canon values (null, float boxes, arrays, objects) and plain Lua values to one comparable form
local function norm(v)
  if v==nil or v==canon.null then return NULL end
  if canon.is_float(v) then return v.value end
  if type(v)=='table' then local out={};for k,x in pairs(v) do out[k]=norm(x) end;return out end
  return v
end
local function same(a,b)
  a,b=norm(a),norm(b)
  if type(a)~=type(b) then return false end
  if type(a)~='table' then return a==b end
  for k,v in pairs(a) do if not same(v,b[k]) then return false end end
  for k,v in pairs(b) do if a[k]==nil and v~=NULL then return false end end
  return true
end
local function show(v)
  v=norm(v)
  if type(v)~='table' then return tostring(v) end
  local keys={}
  for k in pairs(v) do keys[#keys+1]=k end
  table.sort(keys,function(x,y) return tostring(x)<tostring(y) end)
  local parts={}
  for _,k in ipairs(keys) do parts[#parts+1]=tostring(k)..'='..show(v[k]) end
  return '{'..table.concat(parts,',')..'}'
end
local function check(actual,expected,message)
  if not same(actual,expected) then error((message or 'differs')..': got '..show(actual)..', expected '..show(expected),2) end
end
local function plain(v) if v==canon.null then return nil end;if canon.is_float(v) then return v.value end;return v end

------------------------------------------------------------------------------------------------------
-- shared cases
------------------------------------------------------------------------------------------------------
t.test('wan_diag.diagnose: every shared case (named and 400 combinations)',function()
  t.truthy(#CASES.diagnose>=400)
  for i,case in ipairs(CASES.diagnose) do check(wan.diagnose(case.evidence,case.enabled),case.expected,i..' '..case.name) end
end)

t.test('wan_diag.channel_state / evidence / free verdicts / grace',function()
  for _,case in ipairs(CASES.channel_state) do check(wan.channel_state(case.row,plain(case.now),case.age,canon.null),case.expected,case.name) end
  for _,case in ipairs(CASES.evidence) do
    local sensors={null=canon.null}
    for k,v in pairs(case.sensors) do sensors[k]=v end
    check(wan.evidence(case.rows,case.pair,plain(case.now),case.age,sensors),case.expected,case.name)
  end
  for _,c in ipairs(CASES.simple.kmwan) do check(wan.kmwan_verdict(plain(c[1])),c[2],'kmwan '..tostring(plain(c[1]))) end
  for _,c in ipairs(CASES.simple.portal) do check(wan.portal_verdict(plain(c[1])),c[2],'portal') end
  for _,c in ipairs(CASES.simple.grace) do check(wan.grace_seconds(c[1]),c[2],'grace') end
end)

t.test('wan_diag.Underlay and Tracker sequences',function()
  for _,case in ipairs(CASES.underlay) do
    local u=wan.Underlay();local out={}
    for i,op in ipairs(case.ops) do
      local kind,result=op[1],NULL
      if kind=='bind' then u:bind(op[2])
      elseif kind=='record' then u:record(op[2],op[3],op[4])
      elseif kind=='state' then result=u:state(op[2])
      elseif kind=='due' then result=u:due(op[2],op[3])
      elseif kind=='target' then result=u:target() end
      out[i]=result==nil and NULL or result
    end
    check(out,case.expected,case.name)
  end
  for _,case in ipairs(CASES.tracker) do
    local tr=wan.Tracker();local out={}
    for i,op in ipairs(case.ops) do out[i]=tr:update({hold=op[1],code=plain(op[2])},op[3],plain(op[4]),op[5]) end
    check(out,case.expected,case.name)
  end
end)

t.test('stall.Stall: every shared feed sequence',function()
  for _,case in ipairs(CASES.stall) do
    local s=stall.Stall();local out={}
    for i,f in ipairs(case.feeds) do out[i]=s:feed(f[1],plain(f[2]),plain(f[3])) end
    check(out,case.expected,case.name)
  end
end)

t.test('quorum.Pool: every shared beat sequence',function()
  for _,case in ipairs(CASES.quorum) do
    local p=quorum.Pool(nil,nil,nil,case.start);local out={}
    for i,beat in ipairs(case.beats) do
      local answered={}
      for _,target in ipairs(beat[1]) do answered[target]=true end
      local verdict=p:judge(answered,beat[2])
      out[i]={verdict=verdict,targets=p:targets(),rotations=p.rotations}
    end
    check(out,case.expected,case.name)
  end
end)

t.test('wg_events: parse, latest, reader, suspicions',function()
  local c=CASES.wg
  local parsed=wg.parse(c.text)
  check(parsed,c.parsed,'parse')
  for _,row in ipairs(c.latest) do check(wg.latest(parsed,row[1],plain(row[2]),row[3]),row[4],'latest '..row[1]) end
  local r=wg.Reader()
  for i,row in ipairs(c.reads) do
    local fresh=r:new(wg.parse(row[1]))
    check(fresh,row[2],'read '..i)
    check(wg.suspicions(fresh,{{id='wireguard:peer_1',device='wgclient1'},{id='wireguard:peer_2',device='wgclient2'},{device='wgclient2'}}),row[3],'suspicions '..i)
  end
end)

t.test('boot_cause: fingerprint, crash evidence, planned reboot',function()
  for _,c in ipairs(CASES.boot.fingerprint) do check(boot.fingerprint(plain(c[1])),c[2],'fingerprint') end
  for i,c in ipairs(CASES.boot.evidence) do
    local names={};for _,n in ipairs(c[1]) do names[#names+1]=n end
    local verdict,fp=boot.crash_evidence(names,plain(c[2]),plain(c[3]))
    check({verdict,fp},c[4],'evidence '..i)
  end
  for i,c in ipairs(CASES.boot.planned) do
    local timer=plain(c[1])
    check(boot.planned(timer,c[2],c[3],c[4]),c[5],'planned '..i)
    check(boot.shutdown_reason(timer,c[2],c[3],c[4]),c[6],'reason '..i)
  end
end)

t.test('interruption: planned reboot and kernel crash classification, shutdown reason',function()
  for _,case in ipairs(CASES.interruption.classify) do
    local f={}
    for k,v in pairs(case.facts) do f[k]=plain(v) end
    check(interruption.classify(f),case.expected,case.name)
  end
  for _,c in ipairs(CASES.interruption.reasons) do check(interruption.previous_reason(plain(c[1])),c[2],tostring(plain(c[1]))) end
end)

t.test('interruption.start asks the crash verdict only on the first start of a boot',function()
  local files={['/p/service-run.json']='{"state":"running","time":1}'}
  local asked=0
  local ctx={runtime='/r',persist='/p',read=function(p) return files[p] end,mtime=function() return nil end,
    write_ram=function(p,s) files[p]=s end,write_persist=function(p,s) files[p]=s end,now=function() return 100 end,
    uptime=function() return 30 end,log=function() end,crash=function() asked=asked+1;return 'crash' end}
  t.eq(interruption.start(ctx,nil).code,'RESTART-KERNEL-CRASH');t.eq(asked,1)
  t.eq(interruption.start(ctx,nil).code,'RESTART-PROCESS');t.eq(asked,1,'not fresh: not asked again')
  files={['/p/service-run.json']='{"state":"stopped","time":1,"reason":"planned-reboot"}'}
  t.eq(interruption.start(ctx,nil).code,'RESTART-PLANNED-REBOOT')
end)

t.test('boot_cause.evaluate and refresh with fake files',function()
  local files={}
  local real_open=io.open
  io.open=function(path,mode) if files[path] then return {read=function(_,n) return files[path] end,close=function() end} end;return real_open('/nonexistent/'..path,mode) end
  local ok,err=pcall(function()
    local function write(path,text) files[path]=text end
    local pstore={}
    local options={write=write,list_dir=function() return pstore end,crash_log='/log/crash'}
    t.eq(boot.evaluate('/p',options),'unknown','first boot after install')
    t.eq(boot.evaluate('/p',options),'none')
    files['/log/crash']='Kernel panic\n'
    t.eq(boot.evaluate('/p',options),'crash');t.eq(boot.evaluate('/p',options),'none')
    pstore={'dmesg-ramoops-0'}
    t.eq(boot.evaluate('/p',options),'crash','pstore not merged yet')
    files['/log/crash']='Kernel panic\nmerged later\n'
    t.truthy(boot.refresh('/p',options));t.eq(boot.refresh('/p',options),false)
    pstore={}
    t.eq(boot.evaluate('/p',options),'none','no false crash at the next boot')
  end)
  io.open=real_open
  if not ok then error(err,0) end
end)

t.test('diag_bundle.mask: every shared line',function()
  for _,c in ipairs(CASES.mask) do check(bundle.mask(c[1]),c[2],c[1]) end
end)

t.test('diag_bundle.collect: fresh label salt per bundle, public address never in the archive, salt restored',function()
  local base=os.tmpname();os.remove(base)
  local dir=base..'-diag'
  assert(os.execute('mkdir -p '..dir)==0 or os.execute('mkdir -p '..dir)==true)
  local labels={}
  for index=1,2 do
    local work=dir..'/work'..index
    local out=dir..'/out'..index..'.tar.gz'
    bundle.collect({work=work,output=out,commands={{'r.txt',{'x'}}},run=function() return 'to 187.40.16.19\n' end})
    local ex=dir..'/ex'..index
    os.execute('mkdir -p '..ex..' && tar -xzf '..out..' -C '..ex)
    labels[index]=read_file(ex..'/homensai-vpn-diag/r.txt')
  end
  os.execute('rm -rf '..dir)
  assert(not string.find(labels[1]..labels[2],'187.40.16.19',1,true),'the public address is masked in the archive')
  assert(string.find(labels[1],'pub%-%x%x%x%x%x%x'),'a label stands in its place')
  assert(labels[1]~=labels[2],'the salt differs between bundles')
  assert(bundle.SALT=='','the salt is restored after collect')
end)

t.test('diag_bundle.collect: the stored recipient and token never reach the bundle (F-14, owner 07.11.2026)',function()
  local base=os.tmpname();os.remove(base)
  local dir=base..'-known'
  os.execute('mkdir -p '..dir)
  local token='123456789:'..string.rep('A',35)
  local lines='sendMessage to -1001234567890 ok\nposted @example_channel at 12:00\nurl /bot'..token..'/sendMessage\nplain 1234567 stays\n'
  bundle.collect({work=dir..'/w',output=dir..'/o.tar.gz',commands={{'log.txt',{'x'}}},run=function() return lines end,
    known={'-1001234567890','@example_channel',token,'12','not valid'}})
  os.execute('mkdir -p '..dir..'/ex && tar -xzf '..dir..'/o.tar.gz -C '..dir..'/ex')
  local text=read_file(dir..'/ex/homensai-vpn-diag/log.txt')
  os.execute('rm -rf '..dir)
  for _,secret in ipairs({'1001234567890','example_channel',token,string.rep('A',30)}) do
    assert(not string.find(text,secret,1,true),'masked: '..secret)
  end
  assert(string.find(text,'plain 1234567 stays',1,true),'only the stored values, not every number')
  assert(#bundle.KNOWN==0,'the list is restored after collect')
  local k=bundle.known_values({'-1001234567890\n',' @example_channel ','12','@ab',string.rep('x',40)})
  assert(#k==2 and k[1]=='@example_channel' and k[2]=='-1001234567890','known_values (longest first): '..table.concat(k,','))
end)

t.test('diag_bundle.collect never writes through planted symlinks and leaves nothing behind (R3-01)',function()
  local base=os.tmpname();os.remove(base)
  local dir=base..'-sym'
  assert(os.execute('mkdir -p '..dir)==0 or true)
  local victim=dir..'/victim'
  local f=assert(io.open(victim,'wb'));f:write('keep me\n');f:close()
  local out=dir..'/homensai-vpn-diag.tar.gz'
  os.execute('ln -s '..victim..' '..out..'.new && ln -s '..dir..'/elsewhere '..dir..'/homensai-vpn-diag')
  local seen
  local result=bundle.collect({output=out,commands={{'r.txt',{'x'}}},run=function(argv,private) seen=private;return 'ok\n' end})
  assert(result==out)
  assert(read_file(victim)=='keep me\n','the symlink target is never written')
  assert(os.execute('[ -f '..out..' ] && [ ! -L '..out..' ]')==0,'the bundle is a regular file')
  assert(seen and string.find(seen,out..'.',1,true)==1 and seen~=out..'.new','command output goes to the unique private folder')
  assert(os.execute('[ ! -e '..dir..'/elsewhere ] && [ ! -e '..seen..' ]')==0,'nothing written through the work symlink, private folder removed')
  -- a symlink at the final name is refused, not followed
  os.execute('rm -f '..out..' && ln -s '..victim..' '..out)
  local ok,err=pcall(bundle.collect,{output=out,commands={{'r.txt',{'x'}}},run=function() return 'ok\n' end})
  assert(not ok and string.find(tostring(err),'UNSAFE',1,true),tostring(err))
  assert(read_file(victim)=='keep me\n')
  -- an explicit work folder that already exists (a planted symlink) is an error, never reused
  os.execute('rm -f '..out)
  ok,err=pcall(bundle.collect,{work=dir..'/homensai-vpn-diag',output=out,commands={{'r.txt',{'x'}}},run=function() return 'ok\n' end})
  assert(not ok and string.find(tostring(err),'PRIVATE',1,true),tostring(err))
  -- a failing collector leaves no private folder behind
  ok=pcall(bundle.collect,{output=out,commands={{'r.txt',{'x'}}},run=function() error('collector failed') end})
  assert(not ok)
  local p=io.popen('ls -A '..dir);local listing=p:read('*a');p:close()
  os.execute('rm -rf '..dir)
  assert(listing=='homensai-vpn-diag\nhomensai-vpn-diag.tar.gz.new\nvictim\n',listing)
end)

t.test('diagnosis.diagnose reads the WAN hold exactly as failure_diagnosis.py',function()
  local diagnosis=require('diagnosis')
  for _,case in ipairs(CASES.diagnose_status) do check(diagnosis.diagnose(case.status,'a',case.now),case.expected,case.name) end
end)

------------------------------------------------------------------------------------------------------
-- the monitor side (gl_sensors.lua) with a fake runner
------------------------------------------------------------------------------------------------------
local function reply(packet,target)
  local echo='\0\0'..u16(0)..string.sub(packet,5)
  echo='\0\0'..u16(probe.icmp_checksum(echo))..string.sub(echo,5)
  local a,b,c,d=string.match(target,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  return '\69\0'..u16(20+#echo)..u16(1)..u16(0)..'\64\1'..u16(0)..string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d))..'\10\0\0\2'..echo
end
-- R.down[device]: nil answers, 'blackhole' no answer, 'refused' EPERM, 'missing' device gone
local function network(R)
  R.down={};R.sent={};R.opened=0
  function R.beat_socket(device)
    if R.down[device]=='missing' then return nil,'missing' end
    R.opened=R.opened+1
    local inbox={}
    local h={}
    function h:send(target,packet)
      R.sent[#R.sent+1]={device,target}
      local mode=R.down[device]
      if mode=='refused' then return nil,'refused' end
      -- the kernel counts our own echo (tx) and its reply (rx) on the device, as on the router
      local c=R.counters[device]
      if c then c.tx=c.tx+52 end
      if mode~='blackhole' then inbox[#inbox+1]=reply(packet,target);if c then c.rx=c.rx+52 end end
      return true
    end
    function h:recv() return table.remove(inbox,1) end
    function h:close() end
    return h
  end
  return R
end

local PAIR=canon.object({source='wireguard:peer_1',target='wireguard:peer_2'})
local function rows(now,primary,reserve)
  local function row(id,dev,code)
    local r={id=id,device=dev,time=now-1,code=code==nil and canon.null or code}
    if code==nil then r.dns_ok=true;r.https_success=3 end
    return canon.object(r)
  end
  return canon.array({row('wireguard:peer_1','wgclient1',primary),row('wireguard:peer_2','wgclient2',reserve)})
end

t.test('gl_sensors: underlay echo calibrates, three failures over two targets hold WAN-DOWN, return is WAN-RECOVERING',function()
  local R=network(t.fake_runner())
  local s=gl.new(R,'/run/hv','/etc/hv')
  local settings={wan_sensor=true,wg_events=true,wan_recover_grace=30}
  s:configure(settings,{{device='apcli0'}},rows(R.now,'VPN-003','VPN-003'),PAIR)
  t.eq(R.files['/run/hv/wg-events.on'],nil,'a pass writes nothing')
  s:tick(R.clock());t.eq(R.files['/run/hv/wg-events.on'],'file\n','the 1 s timer keeps the listener flag')
  R.advance(1);s:tick(R.clock())  -- the reply of the first echo: calibrated
  t.eq(s.underlay:state(R.clock()),'ok')
  R.down.apcli0='blackhole';s.alert=true
  for _=1,8 do R.advance(1);s:tick(R.clock()) end
  t.eq(s.underlay:state(R.clock()),'fail')
  local targets={};for _,x in ipairs(R.sent) do targets[#targets+1]=x[2] end
  t.eq(targets[1],'1.1.1.1');t.eq(targets[2],'8.8.8.8');t.eq(targets[3],'9.9.9.9')
  local result=s:pass(rows(R.now,'VPN-003','VPN-003'),PAIR,R.now,90,settings,canon.object({state='LINK-UP',time=R.now}))
  t.eq(result.code,'WAN-DOWN');t.eq(result.hold,true);t.eq(result.evidence.underlay,'fail');t.truthy(canon.encode(result))
  local status=canon.object({time=R.now,profiles=canon.array({canon.object({id='wireguard:peer_1',interface='wgclient1',time=R.now-1,code='VPN-003'})}),wan_diagnosis=result})
  local d=require('diagnosis').diagnose(status,'wireguard:peer_1',R.now)
  t.eq(d.code,'WAN-DOWN');t.eq(d.suppress_switch,true)
  R.down.apcli0=nil
  for _=1,3 do R.advance(1);s:tick(R.clock()) end
  result=s:pass(rows(R.now,'VPN-003','VPN-003'),PAIR,R.now,90,settings,canon.object({state='LINK-UP',time=R.now}))
  t.eq(result.code,'WAN-RECOVERING');t.eq(result.recovering,true);t.eq(s.restored,true)
  R.advance(5)
  result=s:pass(rows(R.now,nil,nil),PAIR,R.now,90,settings,canon.object({state='LINK-UP',time=R.now}))
  t.eq(result.hold,false);t.eq(result.code,canon.null)
end)

t.test('gl_sensors: switched off sends nothing, removes the flag, never holds',function()
  local R=network(t.fake_runner())
  R.files['/run/hv/wg-events.on']='file\n'
  local s=gl.new(R,'/run/hv','/etc/hv')
  local settings={wan_sensor=false,wg_events=false}
  s:configure(settings,{{device='apcli0'}},rows(R.now,'VPN-003','VPN-003'),PAIR)
  for _=1,30 do R.advance(1);s:tick(R.clock()) end
  t.eq(#R.sent,0);t.eq(R.files['/run/hv/wg-events.on'],nil)
  local result=s:pass(rows(R.now,'VPN-003','VPN-003'),PAIR,R.now,90,settings,canon.object({state='DOWN',time=R.now}))
  t.eq(result.hold,false);t.eq(result.enabled,false);t.eq(result.verdict,'WAN')
end)

t.test('gl_sensors: a firewall that never lets the echo out is unknown, not WAN-DOWN',function()
  local R=network(t.fake_runner())
  R.down.apcli0='refused'
  local s=gl.new(R,'/run/hv','/etc/hv')
  s:configure({},{{device='apcli0'}},rows(R.now,'VPN-003','VPN-003'),PAIR)
  s.alert=true
  for _=1,20 do R.advance(1);s:tick(R.clock()) end
  t.eq(s.underlay:state(R.clock()),nil)
  local result=s:pass(rows(R.now,'VPN-003','VPN-003'),PAIR,R.now,90,{},canon.object({state='LINK-UP',time=R.now}))
  t.eq(result.hold,false);t.eq(result.evidence.underlay,nil,'no underlay evidence at all')
end)

t.test('gl_sensors: REKEY of a pair device is a suspicion item; KEYPAIR is evidence only',function()
  local R=network(t.fake_runner())
  local s=gl.new(R,'/run/hv','/etc/hv')
  s:configure({},{},rows(R.now,nil,nil),PAIR)
  R.write_atomic('/run/hv/wg-events.log','5 KEYPAIR-CREATED wgclient1\n')
  t.eq(#s:tick(R.clock()),0,'the first read only marks the position')
  R.write_atomic('/run/hv/wg-events.log','5 KEYPAIR-CREATED wgclient1\n999 REKEY-GIVEUP wgclient1\n999 REKEY-TIMEOUT wgclient9\n')
  local items=s:tick(R.clock())
  t.eq(#items,1);t.eq(items[1].profile,'wireguard:peer_1');t.eq(items[1].reason,'wg-rekey');t.eq(items[1].evidence.event,'giveup')
  t.eq(#s:tick(R.clock()),0,'unchanged file: not read again')
  local result=s:pass(rows(R.now,'VPN-003',nil),PAIR,R.now,90,{},canon.object({state='LINK-UP',time=R.now}))
  t.eq(result.evidence.wg,'giveup')
end)

t.test('gl_sensors: hasten when the WAN is proven up, the reserve answers and the primary just failed',function()
  local R=network(t.fake_runner())
  local s=gl.new(R,'/run/hv','/etc/hv')
  s:configure({},{{device='eth0'}},rows(R.now,'VPN-003',nil),PAIR)
  s:tick(R.clock());R.advance(1);s:tick(R.clock())
  local result=s:pass(rows(R.now,'VPN-003',nil),PAIR,R.now,90,{},canon.object({state='LINK-UP',time=R.now}))
  t.eq(result.hasten,true);t.eq(s.hasten,true);t.eq(result.hold,false)
  result=s:pass(rows(R.now,'VPN-003','VPN-003'),PAIR,R.now,90,{},canon.object({state='LINK-UP',time=R.now}))
  t.eq(result.hasten,false,'reserve failing too: no hasten')
end)

------------------------------------------------------------------------------------------------------
-- fast_detect options: stall, veto, quorum
------------------------------------------------------------------------------------------------------
local SOURCE,TARGET='wireguard:peer_7','wireguard:peer_8'
local FPAIR={source=SOURCE,target=TARGET}
local function frows()
  return {{id=SOURCE,device='wgclient',mark=0x1000,table='53',ifindex=20},{id=TARGET,device='wgclient2',mark=0x2000,table='54',ifindex=21}}
end
local function beats(p,R,n) local found;for _=1,n do R.advance(1);found=p:tick(R.clock()) end;return found end

t.test('fast_detect: without options nothing new runs (the previous rule exactly)',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING')
  t.eq(p.opts.stall,false);t.eq(p.opts.veto,false);t.eq(p.opts.quorum,false)
  beats(p,R,5);t.eq(#R.sent,10,'one echo per channel per beat')
  local public=p:public(R.clock(),true);t.eq(public.stall,false);t.eq(public.quorum,false)
end)

t.test('fast_detect stall: tx grows into a silent tunnel for 3 s -> suspect rx-stall (own echoes do not count)',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING',{stall=true,veto=true})
  beats(p,R,3)
  t.eq(beats(p,R,4),nil,'only our own echoes leave: no stall')
  -- user traffic into the tunnel; the echoes still get answers (rx moves): no stall
  for _=1,4 do R.counters.wgclient.tx=R.counters.wgclient.tx+500;R.advance(1);t.eq(p:tick(R.clock()),nil) end
  -- the peer is dead for the user traffic but rx stays flat; the heartbeat target is filtered so beats are not lost yet
  R.down.wgclient='blackhole'
  local found
  for _=1,4 do R.counters.wgclient.tx=R.counters.wgclient.tx+500;R.advance(1);found=p:tick(R.clock()) or found end
  t.truthy(found,'a suspect');t.eq(found[1].id,SOURCE)
  t.truthy(found[1].suspect_reason=='rx-stall' or found[1].suspect_reason=='heartbeat-lost')
end)

t.test('fast_detect stall alone: no ICMP socket at all (beats unavailable, never lost) -> rx-stall from the counters',function()
  local R=network(t.fake_runner())
  R.beat_socket=function() return nil,'unavailable' end
  local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING',{stall=true,veto=true})
  beats(p,R,3)
  t.eq(p.channels[SOURCE].lost,0)
  R.counters.wgclient.rx=R.counters.wgclient.rx+100;R.advance(1);t.eq(p:tick(R.clock()),nil,'rx moved: the silence starts now')
  local found
  for _=1,2 do R.counters.wgclient.tx=R.counters.wgclient.tx+800;R.advance(1);found=p:tick(R.clock()) or found end
  t.eq(found,nil,'2 s of silence: not yet')
  R.counters.wgclient.tx=R.counters.wgclient.tx+800;R.advance(1);found=p:tick(R.clock())
  t.truthy(found,'3 s of tx into a flat rx');t.eq(found[1].suspect_reason,'rx-stall');t.eq(found[1].id,SOURCE)
  local evidence=p:evidence(found[1],R.clock());t.eq(evidence.cause,'rx-stall');t.eq(evidence.stalled_s,3)
  p:disarm(SOURCE)
  R.counters.wgclient.tx=R.counters.wgclient.tx+800;R.advance(1);t.eq(p:tick(R.clock()),nil,'disarmed until the channel answers')
  -- without the option the counters are not even read for this
  local R2=network(t.fake_runner());R2.beat_socket=R.beat_socket
  local p2=fast.Pulse(R2);p2:configure(true,frows(),FPAIR,'OBSERVING',{stall=false})
  beats(p2,R2,2)
  for _=1,5 do R2.counters.wgclient.tx=R2.counters.wgclient.tx+800;R2.advance(1);t.eq(p2:tick(R2.clock()),nil) end
end)

t.test('fast_detect stall: the pulse\'s own echoes are never traffic into a silence',function()
  local R=network(t.fake_runner())
  local losses=fast.LOSSES
  fast.LOSSES=1000  -- only the stall sensor may speak here
  local ok,err=pcall(function()
    local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING',{stall=true,veto=false})
    R.down.wgclient='blackhole'  -- echoes leave (tx +52 each), nothing comes back
    t.eq(beats(p,R,10),nil,'own echoes only: no stall')
    t.eq(p.channels[SOURCE].own_bytes,52*10)
  end)
  fast.LOSSES=losses
  if not ok then error(err,0) end
end)

t.test('fast_detect veto: lost echoes while rx flows >= 10 kbit/s are vetoed, never a suspect',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING',{stall=true,veto=true})
  beats(p,R,3)
  R.down.wgclient='blackhole'  -- echoes to the heartbeat target get no reply (ICMP filtered)
  local found
  for _=1,10 do R.counters.wgclient.rx=R.counters.wgclient.rx+2000;R.advance(1);found=p:tick(R.clock()) or found end
  t.eq(found,nil,'rx flowing: vetoed')
  t.truthy(p.channels[SOURCE].vetoed>=6);t.eq(p.channels[SOURCE].lost,0)
  -- rx stops: the veto ends and the losses count again
  for _=1,6 do R.advance(1);found=p:tick(R.clock()) or found end
  t.truthy(found,'no rx: suspect as before')
  -- without the veto option the same flow is a suspect
  local R2=network(t.fake_runner())
  local p2=fast.Pulse(R2);p2:configure(true,frows(),FPAIR,'OBSERVING',{stall=true,veto=false})
  beats(p2,R2,3);R2.down.wgclient='blackhole'
  local found2
  for _=1,4 do R2.counters.wgclient.rx=R2.counters.wgclient.rx+2000;R2.advance(1);found2=p2:tick(R2.clock()) or found2 end
  t.truthy(found2,'veto off: the previous rule')
end)

t.test('fast_detect veto never covers a refused send or a missing link',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING',{stall=true,veto=true})
  beats(p,R,3)
  R.down.wgclient='refused'
  local found
  for _=1,3 do R.counters.wgclient.rx=R.counters.wgclient.rx+3000;R.advance(1);found=p:tick(R.clock()) or found end
  t.truthy(found,'refused sends stay losses')
end)

t.test('fast_detect quorum: three targets per beat, 2 of 3 lost is a lost beat, a silent target rotates out',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING',{quorum=true})
  t.truthy(p.channels[SOURCE].pool)
  beats(p,R,3);t.eq(#R.sent,18,'3 echoes per channel per beat')
  -- one target filtered on the source: answered by 2 of 3, never lost, and replaced after 3 misses
  local filtered=p.channels[SOURCE].pool:targets()[1]
  local send=R.beat_socket
  local real_down=R.down
  local h=p.channels[SOURCE].sock
  local original=h.send
  h.send=function(self,target,packet) if target==filtered then R.sent[#R.sent+1]={'wgclient',target};return true end;return original(self,target,packet) end
  t.eq(beats(p,R,5),nil,'one silent target of three: no suspect')
  t.eq(p.channels[SOURCE].lost,0)
  local now_targets=p.channels[SOURCE].pool:targets()
  local still=false;for _,x in ipairs(now_targets) do if x==filtered then still=true end end
  t.eq(still,false,'the silent target rotated out');t.eq(p.channels[SOURCE].pool.rotations,1)
  -- the whole tunnel down: lost beats, suspect after LOSSES
  h.send=function(self,target,packet) R.sent[#R.sent+1]={'wgclient',target};return true end
  local found=beats(p,R,3)
  t.truthy(found);t.eq(found[1].suspect_reason,'heartbeat-lost')
  local public=p:public(R.clock(),true);t.eq(public.quorum,true);t.eq(#public.channels[1].quorum_targets,3)
  local _=send;_=real_down
end)

t.test('fast_detect: switching the quorum option starts every channel again',function()
  local R=network(t.fake_runner())
  local p=fast.Pulse(R);p:configure(true,frows(),FPAIR,'OBSERVING',{})
  beats(p,R,2)
  local before=p.channels[SOURCE]
  p:configure(true,frows(),FPAIR,'OBSERVING',{quorum=true})
  t.truthy(p.channels[SOURCE]~=before);t.truthy(p.channels[SOURCE].pool)
  t.eq(beats(p,R,3),nil)
end)

------------------------------------------------------------------------------------------------------
-- the monitor wiring
------------------------------------------------------------------------------------------------------
t.test('monitor: a pass publishes wan_diagnosis; gl_tick turns a REKEY into a dense episode',function()
  local monitor=require('monitor')
  local R=network(t.fake_runner({config="config main 'main'\n\toption enabled '1'\n"}))
  local m=monitor.new(R)
  local status
  m:start_pass(function(s) status=s end)
  t.truthy(status and status.wan_diagnosis,'published');t.eq(status.wan_diagnosis.enabled,true)
  t.truthy(canon.is_object(status.wan_diagnosis.posterior))
  t.eq(m:gl_tick(),false)
  t.eq(R.files[m.runtime..'/wg-events.on'],'file\n')
end)

t.run()
