-- Large-packet (MTU black hole) check of the Lua monitor probe: mtu_check.lua and its use by probe.probe and Auto.
-- Router finding 02.11.2026 (MT3000, primary-mtu = nft `meta length > 1300 drop`): the HTTPS/DNS probes passed and
-- Auto never left the primary. Python twin: tests/test_mtu_check.py (shared cases tests/mtu_check_cases.json).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local mtu=require('mtu_check')
local probe=require('probe')
local diagnosis=require('diagnosis')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../mtu_check_cases.json'))
local function plain(v) if v==NULL then return nil end;return v end
local function unhex(text) return (string.gsub(text,'%x%x',function(h) return string.char(tonumber(h,16)) end)) end
local function u16(n) return string.char(math.floor(n/256)%256,n%256) end
local function be16(s,i) local a,b=string.byte(s,i,i+1);return a*256+b end
local function quad(text) local a,b,c,d=string.match(text,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$');return string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d)) end
local BINDING={device='wgclient1',mark=4096,table='1001',ifindex=12}

t.test('shared cases: classify',function()
  local r=CASES.classify_request
  local payload=unhex(r.payload_hex)
  for _,case in ipairs(CASES.classify) do
    t.eq(mtu.classify(unhex(case.data_hex),r.identifier,r.sequence,payload,r.target),plain(case.expect),case.name)
  end
end)

t.test('shared cases: parse_mtu and probe_size',function()
  for _,c in ipairs(CASES.parse_mtu) do t.eq(mtu.parse_mtu(plain(c[1])),plain(c[2]),tostring(plain(c[1]))) end
  for _,c in ipairs(CASES.probe_size) do t.eq(mtu.probe_size(plain(c[1])),plain(c[2]),tostring(plain(c[1]))) end
end)

t.test('shared cases: verdict',function()
  for _,case in ipairs(CASES.verdict) do
    local rows={}
    for i,row in ipairs(case.rows) do
      local large={};for k,v in ipairs(row.large) do large[k]=plain(v) or false end
      rows[i]={target=mtu.TARGETS[i],small=plain(row.small),large=large}
    end
    t.eq(mtu.verdict(rows),case.expect,case.name)
  end
end)

t.test('shared cases: schedule',function()
  for _,case in ipairs(CASES.schedule) do
    local schedule=mtu.Schedule()
    for _,step in ipairs(case.steps) do
      local now=canon.number(step[3])
      if step[1]=='due' then t.eq(schedule:due(step[2],now),step[4],case.name..' @'..tostring(now))
      elseif step[1]=='reading' then
        local expect=plain(step[4])
        t.eq(schedule:reading(step[2]),expect and {state=expect.state,size=expect.size,time=expect.time} or nil,case.name..' @'..tostring(now))
      else schedule:record(step[2],step[4],now,plain(step[5]),plain(step[6])) end
    end
  end
end)

t.test('shared cases: apply and sanitize',function()
  for _,case in ipairs(CASES.apply) do
    local result={code=plain(case.result.code)}
    local check=plain(case.check)
    mtu.apply(result,check and {state=check.state,size=check.size,time=check.time} or nil)
    t.eq(result.code,plain(case.code),case.name)
    if check then t.eq(result.mtu_check,{state=check.state,size=check.size,time=check.time},case.name) else t.eq(result.mtu_check,nil,case.name) end
  end
  for _,c in ipairs(CASES.sanitize) do
    local value=plain(c[1])
    if type(value)=='table' then local copy={};for k,v in pairs(value) do copy[k]=canon.is_float(v) and v or v end;value=copy end
    local expect=plain(c[2])
    t.eq(mtu.sanitize(value),expect and {state=expect.state,size=expect.size,time=expect.time} or nil,canon.encode(c[1]))
  end
end)

-- A fake runner: raw ICMP through a path that drops above `limit`, truncates replies, answers PMTU or nothing.
local function runner(options)
  options=options or {}
  local R={mono=0,sent={},mtu=options.mtu or '1350',n=0}
  function R.clock() return R.mono end
  function R.random(n) local out={};for i=1,n do out[i]=string.char((R.n+i)%256) end;R.n=R.n+n;return table.concat(out) end
  function R.sysfs(device,name) if name=='mtu' then return R.mtu end end
  local function ip(source,body) return '\69\0'..u16(20+#body)..u16(1)..u16(0)..'\64\1'..u16(0)..quad(source)..quad('10.2.0.2')..body end
  function R.datagram(kind,device,host,port,packet,seconds,accept,cb)
    t.eq({kind,device,port,seconds},{'icmp','wgclient1',0,mtu.TIMEOUT})
    if options.refuse then cb(nil,'unavailable');return end
    local size=#packet+20
    -- the router's own OUTPUT drop above `firewall` bytes: monitor_io.datagram reports the EPERM send as 'refused'
    if options.firewall and size>options.firewall then cb(nil,'refused');return end
    R.sent[#R.sent+1]={host,size}
    if options.silent then cb(nil,'timeout');return end
    local data
    if options.pmtu and size>options.pmtu then
      local quote='\69\0'..u16(size)..u16(1)..u16(0)..'\64\1'..u16(0)..quad('10.2.0.2')..quad(host)..string.sub(packet,1,8)
      local body='\3\4'..u16(0)..u16(0)..u16(options.pmtu)..quote
      body='\3\4'..u16(probe.icmp_checksum(body))..string.sub(body,5)
      data=ip('10.2.0.1',body)
    elseif options.limit and size>options.limit then cb(nil,'timeout');return
    else
      local payload=string.sub(packet,9)
      if options.truncate then payload=string.sub(payload,1,options.truncate) end
      local echo='\0\0'..u16(0)..string.sub(packet,5,8)..payload
      echo='\0\0'..u16(probe.icmp_checksum(echo))..string.sub(echo,5)
      data=ip(host,echo)
    end
    if accept(data,host) then cb(data,nil,0,0.01) else cb(nil,'timeout') end
  end
  return R
end

local function check(options,size)
  local R=runner(options)
  if size then R.mtu=tostring(size) end
  local got
  mtu.run(R,mtu.Schedule(),'wireguard:peer_1',BINDING,function(value) got=value end)
  return got,R
end

t.test('plan: one small and two large per target, valid checksums',function()
  local R=runner()
  local probes=mtu.plan(1350,R.random)
  local shape={}
  for i,p in ipairs(probes) do
    shape[i]=p.target..' '..p.kind..' '..(#p.packet+20)
    t.eq(probe.icmp_checksum(p.packet),0);t.eq(string.sub(p.payload,1,8),mtu.MAGIC)
  end
  t.eq(shape,{'1.1.1.1 small 64','1.1.1.1 large 1350','1.1.1.1 large 1350','9.9.9.9 small 64','9.9.9.9 large 1350','9.9.9.9 large 1350'})
end)

t.test('the router finding is a black hole; healthy paths pass',function()
  t.eq(check({limit=1300}),{state='black-hole',size=1350})
  t.eq(check({}),{state='ok',size=1350})
  t.eq(check({},1500),{state='ok',size=1500})
  t.eq(check({truncate=64}),{state='ok',size=1350})
  t.eq(check({pmtu=1280}),{state='ok',size=1350})
  t.eq(check({silent=true}),{state='inconclusive',size=1350})
  t.eq(check({refuse=true}),{state='unavailable',size=1350})
end)

t.test('a send refused by the router firewall is a lost echo (MT3000 03.11.2026, alpha7 primary-mtu-long)',function()
  -- `oifname wgclient1 meta length > 1300 drop` on the OUTPUT hook: EPERM for the large sends -> 'refused'
  local got,R=check({firewall=1300})
  t.eq(got,{state='black-hole',size=1350})
  t.eq(#R.sent,2,'only the two small echoes left the router')
  t.eq(check({firewall=60}),{state='inconclusive',size=1350},'every send refused: no small echo either')
  t.eq(check({refuse=true}),{state='unavailable',size=1350},'any other socket failure stays unavailable')
end)

t.test('run: not due, no MTU, a small MTU or an invalid binding give no check',function()
  local R=runner();local schedule=mtu.Schedule();local got='unset'
  R.wall=function() return 5000.7+R.mono end
  mtu.run(R,schedule,'x',BINDING,function(v) got=v end);t.eq(got,{state='ok',size=1350,time=5000})
  -- between checks: the last reading with its own measurement time (status rows always carry the field)
  local sent=#R.sent
  R.mono=10;mtu.run(R,schedule,'x',BINDING,function(v) got=v end);t.eq(got,{state='ok',size=1350,time=5000});t.eq(#R.sent,sent,'nothing sent')
  R.mono=300;mtu.run(R,schedule,'x',BINDING,function(v) got=v end);t.eq(got,{state='ok',size=1350,time=5300})
  got='unset';mtu.run(R,schedule,'other',BINDING,function(v) got=v end);t.eq(got,{state='ok',size=1350,time=5300},'a new channel is due at once')
  R.mtu=nil;got='unset';mtu.run(R,mtu.Schedule(),'x',BINDING,function(v) got=v end);t.eq(got,nil)
  R.mtu='500';got='unset';mtu.run(R,mtu.Schedule(),'x',BINDING,function(v) got=v end);t.eq(got,nil)
  R.mtu='1350';got='unset';mtu.run(R,mtu.Schedule(),'x',{device='wgclient1',mark=0,table='1',ifindex=1},function(v) got=v end);t.eq(got,nil)
  got='unset';mtu.run(R,nil,'x',BINDING,function(v) got=v end);t.eq(got,nil)
end)

t.test('run: a black hole is checked again on every probe until it passes',function()
  local R=runner({limit=1300});local schedule=mtu.Schedule();local got
  mtu.run(R,schedule,'x',BINDING,function(v) got=v end);t.eq(got.state,'black-hole')
  R.mono=10;mtu.run(R,schedule,'x',BINDING,function(v) got=v end);t.eq(got.state,'black-hole')
  local healthy=runner();healthy.mono=20
  mtu.run(healthy,schedule,'x',BINDING,function(v) got=v end);t.eq(got.state,'ok')
  healthy.mono=30;got='unset';mtu.run(healthy,schedule,'x',BINDING,function(v) got=v end);t.eq(got,{state='ok',size=1350},'the remembered reading')
  t.eq(#healthy.sent,6,'nothing sent between checks')
end)

-- probe.probe with the monitor's mtu argument (monitor_harness-like fake)
local function probe_runner(state)
  local R=runner()
  R.wall=function() return 1000 end
  R.hires=function() return 0 end
  R.ifindex=12
  function R.command(name,a,b)
    if name=='iface_status' then return canon.encode(canon.object({up=true,l3_device='wgclient1'})) end
    if name=='routes' then return canon.encode(canon.array({canon.object({dst='default',dev='wgclient1',table=1001})})) end
    if name=='rules' then return canon.encode(canon.array({canon.object({priority=100,fwmark='0x1000',table='1001'})})) end
    if name=='route_get' then return canon.encode(canon.array({canon.object({dst=a,dev='wgclient1',table=1001})})) end
  end
  local sysfs=R.sysfs
  function R.sysfs(device,name) if name=='ifindex' then local v=tostring(R.ifindex);if state.change then R.ifindex=13 end;return v end;return sysfs(device,name) end
  local datagram=R.datagram
  function R.datagram(kind,device,host,port,packet,seconds,accept,cb)
    if kind=='icmp' then return datagram(kind,device,host,port,packet,seconds,accept,cb) end
    local token=string.sub(packet,1,2);local question=string.sub(packet,13)
    local answer=token..u16(0x8180)..u16(1)..u16(1)..u16(0)..u16(0)..question
    if state.dns_fail then cb(nil,'timeout') else cb(answer,nil,0,0) end
  end
  function R.https_get(device,address,hostname,path,seconds,cb,agent)
    if state.https_fail then cb(nil,'timeout');return end
    if address=='1.1.1.1' then cb({status=200,body='ip=93.184.216.34\nhttp=http/1.1\nuag='..tostring(agent)..'\n'})
    elseif address=='8.8.8.8' then cb({status=200,body='{"Status":0,"Answer":[{"data":"93.184.216.34"}]}'})
    else
      local b64='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
      local text=string.match(path,'dns=([A-Za-z0-9_-]+)');local bits,count,out=0,0,{}
      for i=1,#text do bits=bits*64+(string.find(b64,string.sub(text,i,i),1,true)-1);count=count+6
        if count>=8 then count=count-8;out[#out+1]=string.char(math.floor(bits/2^count)%256);bits=bits%(2^count) end end
      local packet=table.concat(out)
      cb({status=200,body=string.sub(packet,1,2)..u16(0x8180)..u16(1)..u16(1)..u16(0)..u16(0)..string.sub(packet,13)})
    end
  end
  return R
end

local function probed(state,with_mtu)
  local R=probe_runner(state)
  local schedule=mtu.Schedule()
  local result
  local function mtu_fn(id,binding,cb) state.calls=(state.calls or 0)+1;mtu.run(R,schedule,id,binding,cb) end
  probe.probe(R,{id='wireguard:peer_1',interface='wgclient1',administrative_state='enabled'},function(r) result=r end,nil,with_mtu~=false and mtu_fn or nil)
  return result
end

t.test('probe.probe: a black hole on a healthy tunnel is VPN-MTU',function()
  local state={}
  local result=probed(state)
  t.eq(result.code,nil);t.eq(result.mtu_check,{state='ok',size=1350,time=1000});t.eq(state.calls,1)
  -- the same probe through a path that drops packets above 1300 bytes
  local hole=probe_runner({})
  local base=hole.datagram
  hole.datagram=function(kind,device,host,port,packet,seconds,accept,cb)
    if kind=='icmp' and #packet+20>1300 then cb(nil,'timeout');return end
    return base(kind,device,host,port,packet,seconds,accept,cb)
  end
  local got
  probe.probe(hole,{id='wireguard:peer_1',interface='wgclient1',administrative_state='enabled'},function(r) got=r end,nil,
    function(id,binding,cb) mtu.run(hole,mtu.Schedule(),id,binding,cb) end)
  t.eq(got.code,'VPN-MTU');t.eq(got.https_success,3);t.eq(got.dns_ok,true);t.eq(got.mtu_check,{state='black-hole',size=1350,time=1000})
end)

t.test('probe.probe: other failures keep their code; no mtu argument, no check; identity change drops it',function()
  local hole=function(state)
    local R=probe_runner(state);local base=R.datagram
    R.datagram=function(kind,device,host,port,packet,seconds,accept,cb)
      if kind=='icmp' and #packet+20>1300 then cb(nil,'timeout');return end
      return base(kind,device,host,port,packet,seconds,accept,cb)
    end
    local got
    probe.probe(R,{id='wireguard:peer_1',interface='wgclient1',administrative_state='enabled'},function(r) got=r end,nil,
      function(id,binding,cb) mtu.run(R,mtu.Schedule(),id,binding,cb) end)
    return got
  end
  t.eq(hole({dns_fail=true}).code,'DNS-001')
  t.eq(hole({https_fail=true}).code,'VPN-003')
  local changed=hole({change=true})
  t.eq(changed.code,'VENDOR-IDENTITY-CHANGED');t.eq(changed.mtu_check,nil)
  local state={}
  local plain_result=probed(state,false)
  t.eq(plain_result.code,nil);t.eq(plain_result.mtu_check,nil);t.eq(state.calls,nil)
end)

t.test('Auto: VPN-MTU is a failure streak and never a ready target; diagnosis allows the switch',function()
  local pair=require('pair')
  local now=1000
  local function s(id,stamp,code) return canon.object({id=id,time=stamp,code=code==nil and NULL or code,dns_ok=true,https_success=3}) end
  local primary={s('p',now,'VPN-MTU'),s('p',now-30,'VPN-MTU'),s('p',now-60,'VPN-MTU')}
  t.eq(pair.streak(primary,'p',3,now,90,false),true)
  t.eq(pair.streak(primary,'p',1,now,90,true),false)
  t.eq(pair.streak({s('r',now),s('r',now-30),s('r',now-60)},'r',3,now,90,true),true)
  t.eq(pair.streak({s('p',now,'VPN-MTU'),s('p',now-30),s('p',now-60,'VPN-MTU')},'p',2,now,90,false),false)
  t.eq(diagnosis.UNSTABLE_CODES['VPN-MTU'],true)
  local status=canon.object({time=now,profiles=canon.array({canon.object({id='p',interface='wgclient1',time=now,code='VPN-MTU',
    vendor_state='SETTLED',dns_ok=true,https_success=3})})})
  local d=diagnosis.diagnose(status,'p',now,canon.object({interval=10}))
  t.eq({d.code,d.suppress_switch},{'LARGE-PACKETS-FAILED',false})
end)

t.run()
