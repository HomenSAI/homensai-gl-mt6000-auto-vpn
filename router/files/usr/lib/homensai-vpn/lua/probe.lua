-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- probe.lua: the router-originated channel checks of agent.py (dns_question/valid_dns/dns_probe, https_probe,
-- route_binding, probe, probe_profiles) and the ICMP echo of icmp_ping.py, ported to Lua 5.1.
-- Every network/system access goes through the injected runner (monitor_io.lua on the router, fakes in tests):
--   runner.wall() / runner.clock() / runner.hires() / runner.random(n)
--   runner.command(name,...)                 -> text | nil,err      (constant allow-listed command lines)
--   runner.datagram(kind,dev,host,port,packet,seconds,accept,cb)    -> cb(data|nil,kind,sent_at,received_at)
--   runner.https_get(dev,address,host,path,seconds,cb)               -> cb({status,body}|nil,kind)
--   runner.sysfs(dev,name)                   -> text | nil
-- All network checks are asynchronous (callbacks): under uloop nothing blocks the loop; the PC fakes may call
-- back at once. Router facts: nixio has no SO_MARK and no TLS, SO_BINDTODEVICE alone routes through the tunnel;
-- DNS/ICMP therefore use device-bound nixio sockets and HTTPS uses `curl --interface <dev>`. The tunnel's fwmark
-- is still part of the route identity compared before and after the measurement (VENDOR-IDENTITY-CHANGED).
-- Verdict rules are unchanged: 2 of 3 HTTPS answers valid else VPN-003; DNS over UDP else DNS-001.
-- Elapsed times of HTTPS checks include the curl process start (about 10-40 ms on the MT3000); Python measured
-- inside its own TLS socket. Health verdicts do not use the elapsed time.
local canon=require('canon')

local M={}
M.HTTP_SECONDS=6
M.TARGETS={{'1.1.1.1','one.one.one.one','/cdn-cgi/trace','trace'},
           {'8.8.8.8','dns.google','/resolve?name=example.com&type=A','dns-json'},
           {'9.9.9.9','dns.quad9.net','/dns-query','dns-wire'}}
M.PING_TARGET='1.1.1.1';M.PING_INTERVAL=60;M.PING_VALID_FOR=45;M.PING_TIMEOUT=1.0
-- icmp_ping.SLACK: a due echo may go up to 2 s early (pass jitter must not turn a 10 s choice into 20 s).
M.PING_SLACK=2

function M.safe(s,limit) return type(s)=='string' and #s>=1 and #s<=(limit or 96) and string.find(s,'^[A-Za-z0-9_.:-]+$')~=nil end
function M.is_number(v) return type(v)=='number' and v==v and v~=math.huge and v~=-math.huge end
function M.is_int(v) return M.is_number(v) and v%1==0 end
local function round1(x) return math.floor(x*10+0.5)/10 end
M.round1=round1

-- big-endian helpers
local function u16(n) return string.char(math.floor(n/256)%256,n%256) end
local function be16(s,i) local a,b=string.byte(s,i,i+1);return a*256+b end
M.u16,M.be16=u16,be16

local function urlsafe_b64(data)
  local alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
  local out={}
  for i=1,#data,3 do
    local a,b,c=string.byte(data,i,i+2)
    local n=a*65536+(b or 0)*256+(c or 0)
    local chars={math.floor(n/262144)%64,math.floor(n/4096)%64,math.floor(n/64)%64,n%64}
    local count=b and (c and 4 or 3) or 2
    for k=1,count do out[#out+1]=string.sub(alphabet,chars[k]+1,chars[k]+1) end
  end
  return table.concat(out)
end
M.urlsafe_b64=urlsafe_b64

------------------------------------------------------------------------------------------------------
-- DNS
------------------------------------------------------------------------------------------------------
function M.dns_question(runner)
  local token=runner.random(2)
  local question='\7example\3com\0'..u16(1)..u16(1)
  return token,token..u16(0x100)..u16(1)..u16(0)..u16(0)..u16(0)..question,question
end

local function band(a,b)
  local result,bit=0,1
  while a>0 and b>0 do
    if a%2==1 and b%2==1 then result=result+bit end
    a=math.floor(a/2);b=math.floor(b/2);bit=bit*2
  end
  return result
end
M.band=band

-- QR set; truncation bit and rcode clear (flags & 0x020F == 0); one question; at least one answer.
function M.valid_dns(data,token)
  if type(data)~='string' or #data<12 then return false end
  local flags,questions,answers=be16(data,3),be16(data,5),be16(data,7)
  return string.sub(data,1,2)==token and band(flags,0x8000)~=0 and band(flags,0x020F)==0 and questions==1 and answers>0
end

local function hires(runner) return runner.hires and runner.hires() or runner.clock() end
M.hires=hires

-- dns_probe: one A question for example.com to 9.9.9.9:53 over UDP, bound to the tunnel device. cb(ok, kind)
function M.dns_probe(runner,device,cb)
  if not M.safe(device,15) then error('invalid socket binding') end
  local token,packet,question=M.dns_question(runner)
  runner.datagram('udp',device,'9.9.9.9',53,packet,3,function(data) return type(data)=='string' and string.sub(data,1,2)==token end,
    function(data,kind)
      if not data then cb(false,kind);return end
      cb(M.valid_dns(data,token) and string.sub(data,13,12+#question)==question)
    end)
end

------------------------------------------------------------------------------------------------------
-- HTTP response parsing (http.client.HTTPResponse subset: status, headers, content-length / chunked / close)
------------------------------------------------------------------------------------------------------
function M.parse_http(raw)
  local head_end=string.find(raw,'\r\n\r\n',1,true)
  if not head_end then return nil,'invalid-response' end
  local head=string.sub(raw,1,head_end-1)
  local status=string.match(head,'^HTTP/1%.[01] (%d%d%d)')
  if not status then return nil,'invalid-response' end
  local headers={}
  for line in string.gmatch(string.sub(head,(string.find(head,'\r\n',1,true) or #head)+2),'[^\r\n]+') do
    local name,value=string.match(line,'^([^:%s]+):%s*(.-)%s*$')
    if name then headers[string.lower(name)]=value end
  end
  local body=string.sub(raw,head_end+4)
  if headers['transfer-encoding'] and string.find(string.lower(headers['transfer-encoding']),'chunked',1,true) then
    local out,pos={},1
    while true do
      local line_end=string.find(body,'\r\n',pos,true)
      if not line_end then return nil,'invalid-response' end
      local hex=string.match(string.sub(body,pos,line_end-1),'^(%x+)')
      local size=hex and tonumber(hex,16)
      if not size then return nil,'invalid-response' end
      if size==0 then break end
      out[#out+1]=string.sub(body,line_end+2,line_end+1+size)
      if #out[#out]<size then return nil,'invalid-response' end
      pos=line_end+2+size+2
    end
    body=table.concat(out)
  elseif headers['content-length'] then
    local length=tonumber(headers['content-length'])
    if not length then return nil,'invalid-response' end
    body=string.sub(body,1,length)
  end
  return {status=tonumber(status),headers=headers,body=body}
end

------------------------------------------------------------------------------------------------------
-- HTTPS probe
------------------------------------------------------------------------------------------------------
local function remember_exit(body,device,sink)
  local country=string.match('\n'..body..'\n','\nloc=([A-Z][A-Z])\r?\n')
  for line in string.gmatch(body,'[^\n]+') do
    if string.sub(line,1,3)=='ip=' then
      local address=string.match(line,'^ip=%s*(%d+%.%d+%.%d+%.%d+)%s*$')
      if not address then return end
      local a,b,c=string.match(address,'^(%d+)%.(%d+)%.(%d+)%.')
      a,b,c=tonumber(a),tonumber(b),tonumber(c)
      for _,octet in ipairs({a,b,c,tonumber(string.match(address,'%.(%d+)$'))}) do if octet>255 then return end end
      -- ipaddress.IPv4Address.is_global: not private/loopback/link-local/multicast/reserved/shared/benchmarking
      local private=a==10 or a==127 or (a==172 and b>=16 and b<=31) or (a==192 and b==168) or (a==169 and b==254)
        or (a==100 and b>=64 and b<=127) or a>=224 or a==0 or (a==192 and b==0 and (c==0 or c==2)) or (a==198 and (b==18 or b==19))
        or (a==198 and b==51 and c==100) or (a==203 and b==0 and c==113) or (a==192 and b==88 and c==99)
      if not private and sink then sink[device]={ip=address,country=country} end
      return
    end
  end
end
M.remember_exit=remember_exit

-- https_probe + https_for_probe: cb(rtt_ms|nil); fills detail {target,result,http_status,elapsed_ms}.
function M.https_probe(runner,device,target,detail,sink,cb)
  local address,hostname,path,kind=target[1],target[2],target[3],target[4]
  detail=detail or {};detail.target=hostname;detail.result='unknown'
  local started=hires(runner)
  local function elapsed() local v=(hires(runner)-started)*1000;return round1(v<0 and 0 or v) end
  local function finish(value) detail.elapsed_ms=elapsed();cb(value) end
  if not M.safe(device,15) then detail.result='transport-error';finish(nil);return end
  local token
  if kind=='dns-wire' then
    local packet;token,packet=M.dns_question(runner)
    path=path..'?dns='..urlsafe_b64(packet)
  end
  runner.https_get(device,address,hostname,path,M.HTTP_SECONDS,function(response,err)
    if not response then detail.result=err or 'transport-error';finish(nil);return end
    detail.http_status=response.status
    if response.status~=200 then
      detail.result=(response.status==426 or response.status==505) and 'http-unsupported' or 'http-error';finish(nil);return
    end
    if type(response.body)~='string' or #response.body>32768 then detail.result='invalid-response';finish(nil);return end
    local body,valid=response.body,false
    if kind=='trace' then
      valid=string.find('\n'..body,'\nip=',1,true)~=nil and string.find('\n'..body,'\nhttp=',1,true)~=nil
      if valid then remember_exit(body,device,sink) end
    elseif kind=='dns-json' then
      local ok,payload=pcall(canon.decode,body)
      valid=ok and canon.is_object(payload) and canon.number(payload.Status)==0 and canon.is_array(payload.Answer) and #payload.Answer>0
    else
      valid=M.valid_dns(body,token)
    end
    detail.result=valid and 'ok' or 'invalid-response'
    local value=valid and elapsed() or nil
    finish(value)
  end)
end

------------------------------------------------------------------------------------------------------
-- route_binding: ubus interface status + ip -j route/rule, exactly the Python checks
------------------------------------------------------------------------------------------------------
local function json_command(runner,name,...)
  local text,err=runner.command(name,...)
  if not text then error(err or ('command failed: '..name)) end
  return canon.plain(canon.decode(text))
end

function M.route_binding(runner,logical)
  if not M.safe(logical,64) then return {code='ROUTE-001'} end
  local status=json_command(runner,'iface_status',logical)
  if not status.up then return {code='VPN-001'} end
  local device=status.l3_device or ''
  if not M.safe(device,15) then return {code='ROUTE-001'} end
  local tables={}
  for _,r in ipairs(json_command(runner,'routes')) do
    if r.dev==device and r.dst=='default' then tables[tostring(r.table or 'main')]=true end
  end
  local seen,candidates={},{}
  for _,rule in ipairs(json_command(runner,'rules')) do
    local fwmark=rule.fwmark
    if tables[tostring(rule.table)] and fwmark and fwmark~=canon.null and fwmark~='' and fwmark~=0 then
      local text=tostring(fwmark)
      local mark=tonumber(text)  -- int(text,0): decimal or 0x-hex; "0x1000/0xf000" is not a number -> SYSTEM-001
      if not mark or mark%1~=0 then error('invalid fwmark '..text) end
      if mark>0 then
        local key=mark..'|'..tostring(rule.table)
        if not seen[key] then seen[key]=true;candidates[#candidates+1]={mark,tostring(rule.table)} end
      end
    end
  end
  if #candidates~=1 then return {code='CHECK-001',device=device} end
  local mark,tbl=candidates[1][1],candidates[1][2]
  for _,target in ipairs(M.TARGETS) do
    local answer=json_command(runner,'route_get',target[1],tostring(mark))
    if #answer~=1 or answer[1].dev~=device or tostring(answer[1].table or 'main')~=tbl then return {code='ROUTE-001',device=device} end
  end
  local ifindex=tonumber(runner.sysfs(device,'ifindex') or '')
  if not ifindex then error('ifindex unreadable') end
  if ifindex<=0 then return {code='CHECK-001',device=device} end
  return {code=nil,device=device,mark=mark,table=tbl,ifindex=ifindex}
end

------------------------------------------------------------------------------------------------------
-- probe(profile)
------------------------------------------------------------------------------------------------------
local BINDING_KEYS={'device','mark','table','ifindex'}
M.BINDING_KEYS=BINDING_KEYS

-- probe(runner, profile, cb[, endpoint]): cb(result) exactly once; the three HTTPS checks and the DNS check run in
-- parallel. endpoint(profile, now) -> server_endpoint row | nil (server_endpoint.lua Observer; agent.probe reads it
-- after the route identity was confirmed again, whatever the health code); its own fault never fails the probe.
function M.probe(runner,profile,cb,endpoint)
  local result={id=profile.id,time=runner.wall(),code='CHECK-001',scope='router-originated',lan_path_verified=false}
  local administrative_state=profile.administrative_state or 'unknown'
  if administrative_state=='enabled' or administrative_state=='disabled' or administrative_state=='unknown' then result.administrative_state=administrative_state end
  local interface=profile.interface
  if interface==canon.null or not interface or interface=='' or administrative_state=='disabled' then result.code='PROFILE-INACTIVE';cb(result);return end
  local done=false
  local function fail(err)
    if done then return end;done=true
    result.code='SYSTEM-001'
    if runner.log then runner.log('probe '..tostring(profile.id)..': '..tostring(err)) end
    cb(result)
  end
  local ok,err=pcall(function()
    local binding=M.route_binding(runner,interface)
    for k,v in pairs(binding) do result[k]=v end
    if binding.code then done=true;cb(result);return end
    local exit_seen,details,times,dns_ok={},{},{},nil
    local pending=#M.TARGETS+1
    local function settle()
      pending=pending-1
      if pending>0 or done then return end
      local okf,ferr=pcall(function()
        local sum=0;for _,v in ipairs(times) do sum=sum+v end
        local checks=canon.array()
        for i=1,#M.TARGETS do checks[#checks+1]=details[i] end
        result.https_success=#times;result.dns_ok=dns_ok==true;result.probe_checks=checks
        result.rtt_ms=#times>0 and round1(sum/#times) or canon.null
        result.code=#times<2 and 'VPN-003' or (dns_ok~=true and 'DNS-001' or nil)
        local after=M.route_binding(runner,interface)
        local changed=after.code~=nil
        for _,key in ipairs(BINDING_KEYS) do if after[key]~=binding[key] then changed=true end end
        if changed then
          for _,key in ipairs({'https_success','dns_ok','rtt_ms','exit_ip','exit_country','probe_checks'}) do result[key]=nil end
          result.code='VENDOR-IDENTITY-CHANGED';return
        end
        local exit=exit_seen[binding.device]
        if exit and not result.code then result.exit_ip=exit.ip;if exit.country then result.exit_country=exit.country end end
        if endpoint then
          local oke,value=pcall(endpoint,profile,runner.wall())
          if oke and type(value)=='table' then result.server_endpoint=value
          elseif not oke and runner.log then runner.log('server endpoint '..tostring(profile.id)..': '..tostring(value)) end
        end
      end)
      if not okf then fail(ferr);return end
      done=true;cb(result)
    end
    for index,target in ipairs(M.TARGETS) do
      local detail={}
      details[index]=detail
      local okp=pcall(M.https_probe,runner,binding.device,target,detail,exit_seen,function(value)
        if value then times[#times+1]=value end
        settle()
      end)
      if not okp then
        if detail.result=='unknown' then detail.result='transport-error' end
        settle()
      end
    end
    local okd=pcall(M.dns_probe,runner,binding.device,function(value) dns_ok=value==true;settle() end)
    if not okd then dns_ok=false;settle() end
  end)
  if not ok then fail(err) end
end

-- probe_profiles: disabled catalogue entries cannot consume a live measurement slot; anchors first.
function M.probe_profiles(profiles,settings)
  local anchors={}
  for _,role in ipairs({'source','target'}) do
    local anchor=settings['plan_'..role..'_tunnel']
    if anchor and anchor~=canon.null and anchor~='' then anchors[anchor]=true end
  end
  local eligible={}
  for index,p in ipairs(profiles) do
    if p.interface and p.interface~=canon.null and p.interface~='' and p.administrative_state~='disabled' then
      eligible[#eligible+1]={p=p,index=index,anchor=anchors[p.vendor_tunnel_id] and 0 or 1,enabled=p.administrative_state=='enabled' and 0 or 1}
    end
  end
  table.sort(eligible,function(a,b)  -- stable sort by (not anchor, not enabled), like Python's key sort
    if a.anchor~=b.anchor then return a.anchor<b.anchor end
    if a.enabled~=b.enabled then return a.enabled<b.enabled end
    return a.index<b.index
  end)
  local limit=tonumber(settings.probe_limit) or 16
  local out={}
  for i=1,math.min(limit,#eligible) do out[i]=eligible[i].p end
  return out
end

------------------------------------------------------------------------------------------------------
-- ICMP echo (icmp_ping.py): packet, reply validation, public row, sampler
------------------------------------------------------------------------------------------------------
function M.icmp_checksum(data)
  if #data%2==1 then data=data..'\0' end
  local total=0
  for i=1,#data,2 do total=total+be16(data,i) end
  while total>=65536 do total=(total%65536)+math.floor(total/65536) end
  return 65535-total
end

function M.icmp_packet(runner)
  local idseq=runner.random(4)
  local identifier,sequence=be16(idseq,1),be16(idseq,3)
  local payload='HV-PING\0'..runner.random(16)
  local head='\8\0'..u16(0)..u16(identifier)..u16(sequence)
  local sum=M.icmp_checksum(head..payload)
  return '\8\0'..u16(sum)..u16(identifier)..u16(sequence)..payload,identifier,sequence,payload
end

local function dotted(s,i) local a,b,c,d=string.byte(s,i,i+3);return a..'.'..b..'.'..c..'.'..d end

function M.valid_reply(data,identifier,sequence,payload,target)
  if type(data)~='string' or #data<28 or math.floor(string.byte(data,1)/16)~=4 then return false end
  local header=(string.byte(data,1)%16)*4
  if header<20 or header>60 or #data<header+8 or string.byte(data,10)~=1 then return false end
  local length=be16(data,3)
  if length~=header+8+#payload or length>#data or band(be16(data,7),0xbfff)~=0 then return false end
  if dotted(data,13)~=(target or M.PING_TARGET) then return false end
  local echo=string.sub(data,header+1,length)
  local kind,code=string.byte(echo,1),string.byte(echo,2)
  return kind==0 and code==0 and be16(echo,5)==identifier and be16(echo,7)==sequence and string.sub(echo,9)==payload and M.icmp_checksum(echo)==0
end

-- Raw-socket echo through the device (no SO_MARK). cb(rtt_ms|nil, kind, backend)
function M.echo(runner,binding,target,cb)
  target=target or M.PING_TARGET
  if not M.binding_valid(binding) then error('PING-IDENTITY-CHANGED') end
  local packet,identifier,sequence,payload=M.icmp_packet(runner)
  runner.datagram('icmp',binding.device,target,0,packet,M.PING_TIMEOUT,function(data,peer)
    return (peer==nil or peer==target) and M.valid_reply(data,identifier,sequence,payload,target)
  end,function(data,kind,sent_at,received_at)
    if not data then cb(nil,kind=='timeout' and 'timeout' or 'unavailable','nixio-raw');return end
    local rtt=(received_at-sent_at)*1000
    if not M.is_number(rtt) or rtt<0 or rtt>M.PING_TIMEOUT*1000 then cb(nil,'timeout','nixio-raw');return end
    cb(round1(rtt),nil,'nixio-raw')
  end)
end

function M.binding_valid(binding)
  return type(binding)=='table' and not binding.code and M.safe(binding.device,15)
    and M.is_int(binding.mark) and binding.mark>0 and binding.mark<=0xffffffff
    and M.is_int(binding.ifindex) and binding.ifindex>0
    and type(binding.table)=='string' and string.find(binding.table,'^%d+$')~=nil
end

function M.ping_public(row,state,code,stamp,rtt,target)
  return {metric='icmp-rtt-ms',target=target or M.PING_TARGET,state=state,code=code==nil and canon.null or code,
    time=stamp==nil and canon.null or stamp,rtt_ms=rtt==nil and canon.null or rtt,valid_for=M.PING_VALID_FOR,
    interface=row.interface==nil and canon.null or row.interface,vendor_tunnel_id=row.vendor_tunnel_id==nil and canon.null or row.vendor_tunnel_id,
    generation=row.vendor_generation==nil and canon.null or row.vendor_generation}
end

local IDENTITY={'id','protocol','interface','vendor_tunnel_id','vendor_generation'}
local function signature(row)
  local binding={};for _,k in ipairs(BINDING_KEYS) do binding[k]=row[k] end
  -- icmp_ping.signature: a SETTLED vendor epoch (vendor.lua) with its 32-hex generation and the kernel binding.
  if not M.binding_valid(binding) or row.administrative_state~='enabled' or row.vendor_state~='SETTLED'
    or (row.protocol~='openvpn' and row.protocol~='wireguard') or type(row.id)~='string'
    or string.sub(row.id,1,#row.protocol+1)~=row.protocol..':' or #row.id>96
    or type(row.interface)~='string' or not string.find(row.interface,'^[A-Za-z0-9_.-]+$') or #row.interface>64
    or type(row.vendor_generation)~='string' or not string.find(row.vendor_generation,'^[a-f0-9]+$') or #row.vendor_generation~=32
    or row.vendor_tunnel_id~=tostring(row.protocol)..':'..tostring(row.interface) then return nil end
  local parts={}
  for _,k in ipairs(IDENTITY) do parts[#parts+1]=tostring(row[k]) end
  for _,k in ipairs(BINDING_KEYS) do parts[#parts+1]=tostring(row[k]) end
  return table.concat(parts,'\31')
end
M.signature=signature

-- PingSampler: one echo per selected channel per interval (<= 2 started per pass), asynchronous, cached results;
-- a row shows the cached answer (icmp_ping.PingSampler's worker cache) or PING-CHECK-PENDING.
local Sampler={};Sampler.__index=Sampler
function M.PingSampler(runner,binding_reader,paused)
  return setmetatable({runner=runner,binding_reader=binding_reader,paused=paused or function() return false end,
    cache={},attempts={},last={},interval=M.PING_INTERVAL,valid_for=M.PING_VALID_FOR,target=M.PING_TARGET,closed=false},Sampler)
end
-- icmp_ping.PingSampler.configure: owner cadence; valid_for from probe_policy.ping_valid_for.
function Sampler:configure(interval,target,valid_for)
  self.interval=interval;self.valid_for=valid_for or math.max(M.PING_VALID_FOR,math.floor(interval*3/2+15))
  if target and target~=self.target then self.target=target;self.cache={} end
end
-- icmp_ping.last_reading: the shared last-ping reading of one answer (only a real reply counts).
function M.last_reading(result)
  if type(result)~='table' or result.state~='ok' then return nil end
  local rtt,stamp=canon.number(result.rtt_ms),canon.number(result.time)
  if not M.is_number(rtt) or not M.is_number(stamp) then return nil end
  return {rtt_ms=result.rtt_ms,time=result.time,target=(type(result.target)=='string' and result.target) or M.PING_TARGET}
end
-- measure(row, cb): binding before, echo, binding after; cb(public) exactly once.
function Sampler:measure(row,cb)
  local runner=self.runner
  if self.closed or self.paused() then cb(M.ping_public(row,'unavailable','PING-UNAVAILABLE',runner.wall()));return end
  local done=false
  local function finish(value) if done then return end;done=true;cb(value) end
  local ok=pcall(function()
    local before=self.binding_reader(row.interface)
    if not M.binding_valid(before) then finish(M.ping_public(row,'unavailable','PING-IDENTITY-CHANGED',runner.wall()));return end
    for _,k in ipairs(BINDING_KEYS) do if before[k]~=row[k] then finish(M.ping_public(row,'unavailable','PING-IDENTITY-CHANGED',runner.wall()));return end end
    M.echo(runner,before,self.target,function(rtt,kind,backend)
      local okr,value=pcall(function()
        local state,code='ok',nil
        if rtt==nil then
          if kind=='timeout' then state,code='failed','PING-FAILED' else state,code='unavailable','PING-UNAVAILABLE' end
        end
        local measured_at=runner.wall()
        local after=self.binding_reader(row.interface)
        if not M.binding_valid(after) then return M.ping_public(row,'unavailable','PING-IDENTITY-CHANGED',runner.wall()) end
        for _,k in ipairs(BINDING_KEYS) do if after[k]~=before[k] then return M.ping_public(row,'unavailable','PING-IDENTITY-CHANGED',runner.wall()) end end
        local public=M.ping_public(row,state,code,measured_at,rtt,self.target)
        if backend then public.backend=backend end
        return public
      end)
      finish(okr and value or M.ping_public(row,'unavailable','PING-UNAVAILABLE',runner.wall()))
    end)
  end)
  if not ok then finish(M.ping_public(row,'unavailable','PING-UNAVAILABLE',runner.wall())) end
end
function Sampler:apply(rows,pair,now)
  local selected={}
  if pair.source then selected[pair.source]=true end
  if pair.target then selected[pair.target]=true end
  local eligible={}
  for _,row in ipairs(rows) do
    local key=selected[row.id] and signature(row)
    if key and M.is_number(row.time) and now-row.time>=-5 and now-row.time<=self.valid_for then eligible[key]=true end
  end
  for key in pairs(self.cache) do if not eligible[key] then self.cache[key]=nil end end
  local live={}
  for _,row in ipairs(rows) do if selected[row.id] then live[row.vendor_tunnel_id or '']=true end end
  local monotonic_now=self.runner.clock()
  for key,value in pairs(self.attempts) do if not live[key] and monotonic_now-value>=self.interval then self.attempts[key]=nil end end
  -- ping_last (icmp_ping.PingSampler.apply): the channel's last real answer, kept only for listed channels.
  local listed={}
  for _,row in ipairs(rows) do if row.id~=nil then listed[row.id]=true end end
  for id in pairs(self.last) do if not listed[id] then self.last[id]=nil end end
  for _,row in ipairs(rows) do
    local last=row.id~=nil and self.last[row.id] or nil
    row.ping_last=last and {rtt_ms=last.rtt_ms,time=last.time,target=last.target} or canon.null
  end
  local sent=0
  for _,row in ipairs(rows) do
    if not selected[row.id] then row.ping=M.ping_public(row,'inactive','PING-NOT-SELECTED')
    else
      local key=signature(row)
      if not key then
        local inactive=row.administrative_state=='disabled' or not row.interface or row.interface==canon.null
        row.ping=M.ping_public(row,inactive and 'inactive' or 'unavailable',inactive and 'PING-INACTIVE' or 'PING-UNAVAILABLE')
      elseif not eligible[key] then row.ping=M.ping_public(row,'stale','PING-DATA-STALE')
      else
        local value=self.cache[key]
        if value then
          local copy={};for k,v in pairs(value) do copy[k]=v end;copy.valid_for=self.valid_for;row.ping=copy
          local stamp=canon.number(value.time)
          if not stamp or now-stamp< -5 or now-stamp>self.valid_for then row.ping=M.ping_public(row,'stale','PING-DATA-STALE',value.time,value.rtt_ms,value.target) end
        else row.ping=M.ping_public(row,'checking','PING-CHECK-PENDING') end
        local last=self.attempts[row.vendor_tunnel_id]
        if not self.closed and not self.paused() and sent<2 and (last==nil or monotonic_now-last>=self.interval-M.PING_SLACK) then
          self.attempts[row.vendor_tunnel_id]=monotonic_now;sent=sent+1
          local snapshot={};for _,k in ipairs(IDENTITY) do snapshot[k]=row[k] end;for _,k in ipairs(BINDING_KEYS) do snapshot[k]=row[k] end
          snapshot.administrative_state=row.administrative_state;snapshot.vendor_state=row.vendor_state
          local target,valid_for=self.target,self.valid_for
          local applying=true
          self.inflight=(self.inflight or 0)+1
          self:measure(snapshot,function(result)
            self.inflight=math.max(0,(self.inflight or 1)-1)
            if self.closed then return end
            result.valid_for=valid_for;result.target=target
            self.cache[key]=result
            local reading=M.last_reading(result)
            if reading and snapshot.id~=nil then self.last[snapshot.id]=reading end
            if self.on_result then pcall(self.on_result,snapshot,result) end
            -- a synchronous answer (fakes, or an immediate failure) is shown in this very pass
            if applying then local copy={};for k,v in pairs(result) do copy[k]=v end;row.ping=copy end
          end)
          applying=false
        end
      end
    end
  end
end
function Sampler:close() self.closed=true;self.cache={};self.last={} end
-- icmp_ping.PingSampler.idle(): no echo in flight (the speed test's quiet window waits for it, speed_pause.gate)
function Sampler:idle() return (self.inflight or 0)==0 end

return M
