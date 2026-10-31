-- live_probe.lua (plan item 4): agent.probe / native_switch.trace in Lua for the Auto supervisor, with a scenario
-- driven fake io; sys.probe_io's real shell group with a fake curl and a fake nixio; backend.probe/trace wiring
-- (native first, lua_bridge.py fallback). Same-as-Python checks: tests/test_lua_live_probe.py drives the
-- scenario mode below (`--scenario <json>`, `--ipv4 <json>`) against agent.probe/native_switch.trace.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local live=require('live_probe')
local NULL=canon.null

local function u16(n) return string.char(math.floor(n/256)%256,n%256) end
-- an answer to the DNS question `packet`: ok | bad-rcode | wrong-question | no-answer
local function dns_answer(packet,mode)
  local token=string.sub(packet,1,2);local question=string.sub(packet,13)
  local flags,answers=0x8180,1
  if mode=='bad-rcode' then flags=0x8182 end
  if mode=='no-answer' then answers=0 end
  if mode=='wrong-question' then question='\7example\3org\0'..u16(1)..u16(1) end
  return token..u16(flags)..u16(1)..u16(answers)..u16(0)..u16(0)..question..'\192\12'..u16(1)..u16(1)..'\0\0\0\60'..u16(4)..'\93\184\216\34'
end
local B64='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
local function b64url_decode(text)
  local bits,count,out=0,0,{}
  for i=1,#text do
    local v=string.find(B64,string.sub(text,i,i),1,true)-1
    bits=bits*64+v;count=count+6
    if count>=8 then count=count-8;local byte=math.floor(bits/2^count)%256;out[#out+1]=string.char(byte);bits=bits%(2^count) end
  end
  return table.concat(out)
end

local TRACE_BODY='fl=1\nh=one.one.one.one\nip=93.184.216.34\nts=1761830400.1\nvisit_scheme=https\nuag=curl\ncolo=FRA\nhttp=http/1.1\nloc=DE\ntls=TLSv1.3\n'
local DNS_JSON='{"Status":0,"TC":false,"Question":[{"name":"example.com.","type":1}],"Answer":[{"name":"example.com.","type":1,"TTL":60,"data":"93.184.216.34"}]}'
local BINDING={code=NULL,device='wgclient1',mark=4096,table='1001',ifindex=12}
local function ok_https() return {['one.one.one.one']={{kind='http',status=200,body=TRACE_BODY}},['dns.google']={{kind='http',status=200,body=DNS_JSON}},
  ['dns.quad9.net']={{kind='http',status=200,body='@DNSWIRE'}}} end

-- scenario io: bindings / https responses are consumed in order, the last one repeats
local function scenario_io(sc)
  local io_={calls={probe_io=0,binding=0},clock_now=sc.clock or 1000}
  local queues={}
  for host,list in pairs(sc.https or {}) do local q={};for i,v in ipairs(list) do q[i]=v end;queues[host]=q end
  local bindings={};for i,v in ipairs(sc.bindings or {BINDING}) do bindings[i]=v end
  local function pop(q) if #q>1 then return table.remove(q,1) end;return q[1] end
  local random_n=0
  function io_.wall() return 1761830400.25 end
  function io_.clock() return io_.clock_now end
  function io_.random(n) random_n=random_n+1;return string.rep(string.char(65+random_n%26),n) end
  function io_.route_binding(logical)
    io_.calls.binding=io_.calls.binding+1
    io_.last_logical=logical
    local b=pop(bindings)
    if b.error then error(setmetatable({code=b.error,value_error=true},require('auto_control').Refused),0) end
    if b.fault then error('lua fault in route binding') end
    local out=canon.object({})
    for k,v in pairs(b) do out[k]=v end
    return out
  end
  function io_.probe_io(device,requests,dns)
    io_.calls.probe_io=io_.calls.probe_io+1
    io_.last={device=device,requests=requests,dns=dns}
    local answers={}
    for i,r in ipairs(requests) do
      local spec=pop(queues[r.hostname] or {{kind='transport'}})
      local kinds={timeout='timeout',tls='tls-error',transport='transport-error'}
      if spec.kind=='http' then
        local body=spec.body
        if body=='@DNSWIRE' or body=='@DNSWIRE-BAD' then
          body=dns_answer(b64url_decode(string.match(r.path,'%?dns=(.*)$')),body=='@DNSWIRE' and 'ok' or 'bad-rcode')
        end
        answers[i]={response={status=spec.status,body=body},elapsed=0.25}
      elseif spec.kind=='oversize' then answers[i]={response={status=200,body='',oversize=true},elapsed=0.25}  -- curl exit 63
      else answers[i]={kind=kinds[spec.kind] or 'transport-error',elapsed=0.5} end
    end
    local data,kind=nil,nil
    if dns then
      local mode=sc.dns or 'ok'
      if mode=='timeout' then kind='timeout' elseif mode=='refused' then kind='transport'
      else
        data=dns_answer(dns.packet,mode)
        if not dns.accept(data) then data,kind=nil,'timeout' end
      end
    end
    return answers,data,kind
  end
  return io_
end
local PROFILE={id='wireguard:peer_2002',interface='wgclient1',administrative_state='enabled',protocol='wireguard'}
local function profile(extra) local p=canon.object({});for k,v in pairs(PROFILE) do p[k]=v end;for k,v in pairs(extra or {}) do p[k]=v end;return p end

------------------------------------------------------------------------------------------------------
-- scenario mode for the Python differential
------------------------------------------------------------------------------------------------------
local function read_json(path) local f=assert(io.open(path,'rb'));local text=f:read('*a');f:close();return canon.decode(text) end
local function plainify(v)  -- canon.decode tables -> the scenario shapes used above
  if type(v)~='table' or v==NULL then return v end
  local out={};for k,x in pairs(v) do out[k]=plainify(x) end;return out
end
if arg[1]=='--scenario' then
  local sc=read_json(arg[2])
  local p=sc.profile
  local L=live.new(scenario_io(plainify(sc)))
  local result=L.probe(p)
  local L2=live.new(scenario_io(plainify(sc)))
  local ok,value=pcall(L2.trace,p)
  local trace=ok and canon.object({exit=value}) or canon.object({code=type(value)=='table' and value.code or ('LUA:'..tostring(value))})
  io.write(canon.encode(canon.object({probe=result,trace=trace})),'\n')
  os.exit(0)
elseif arg[1]=='--ipv4' then
  local out=canon.array({})
  for _,text in ipairs(read_json(arg[2])) do
    local o=live.ipv4(text)
    out[#out+1]=canon.array({o~=nil,o~=nil and live.is_global(o) or false})
  end
  io.write(canon.encode(out),'\n')
  os.exit(0)
end

------------------------------------------------------------------------------------------------------
-- probe verdicts
------------------------------------------------------------------------------------------------------
t.test('a passing probe: agent.probe fields, three checks side by side in one probe_io, exit_ip from the trace',function()
  local io_=scenario_io({https=ok_https()})
  local r=live.new(io_).probe(profile())
  t.eq(r.code,NULL);t.eq(r.dns_ok,true);t.eq(r.https_success,3);t.eq(r.exit_ip,'93.184.216.34')
  t.eq(r.scope,'router-originated');t.eq(r.lan_path_verified,false);t.eq(r.administrative_state,'enabled')
  t.eq({r.device,r.mark,r.table,r.ifindex},{'wgclient1',4096,'1001',12})
  t.eq(r.rtt_ms.value,250);t.eq(r.time.value,1761830400.25)
  t.eq(#r.probe_checks,3)
  for i,host in ipairs({'one.one.one.one','dns.google','dns.quad9.net'}) do
    t.eq(r.probe_checks[i].target,host);t.eq(r.probe_checks[i].result,'ok');t.eq(r.probe_checks[i].http_status,200);t.eq(r.probe_checks[i].elapsed_ms.value,250)
  end
  t.eq(r.exit_country,nil,'agent.probe has no exit_country');t.eq(r.server_endpoint,nil)
  t.eq(io_.calls.probe_io,1);t.eq(io_.calls.binding,2,'route binding before and after')
  t.eq(io_.last.device,'wgclient1');t.eq(io_.last.dns.host,'9.9.9.9');t.eq(io_.last.dns.port,53);t.eq(io_.last.dns.seconds,3)
  t.eq(io_.last.requests[1],{address='1.1.1.1',hostname='one.one.one.one',path='/cdn-cgi/trace',seconds=6})
  t.eq(io_.last.requests[2].path,'/resolve?name=example.com&type=A')
  t.truthy(string.find(io_.last.requests[3].path,'^/dns%-query%?dns=[A-Za-z0-9_-]+$'),'dns-wire question in the URL, no padding')
  t.eq(canon.encode(r.probe_checks[1]),canon.encode(canon.object({elapsed_ms=canon.float(250),http_status=200,result='ok',target='one.one.one.one'})))
end)

t.test('inactive profiles, route codes and SYSTEM-001 stop before any network check',function()
  for _,p in ipairs({profile({interface=NULL}),profile({interface=''}),profile({administrative_state='disabled'})}) do
    local io_=scenario_io({https=ok_https()})
    local r=live.new(io_).probe(p)
    t.eq(r.code,'PROFILE-INACTIVE');t.eq(io_.calls.binding,0)
  end
  local r=live.new(scenario_io({})).probe(profile({administrative_state=NULL}))
  t.eq(r.administrative_state,nil,'a null state is not one of enabled/disabled/unknown')
  local missing=profile();missing.administrative_state=nil
  r=live.new(scenario_io({})).probe(missing)
  t.eq(r.administrative_state,'unknown')
  for _,code in ipairs({'VPN-001','ROUTE-001','CHECK-001'}) do
    local io_=scenario_io({bindings={{code=code,device=code~='VPN-001' and 'wgclient1' or nil}},https=ok_https()})
    r=live.new(io_).probe(profile())
    t.eq(r.code,code);t.eq(io_.calls.probe_io,0);t.eq(r.https_success,nil)
  end
  local io_=scenario_io({bindings={{error='POLICY-READ-FAILED'}},https=ok_https()})
  r=live.new(io_).probe(profile())
  t.eq(r.code,'SYSTEM-001');t.eq(io_.calls.probe_io,0)
  -- the after-binding read fails: SYSTEM-001 with the measured fields kept (Python updates result first)
  io_=scenario_io({bindings={BINDING,{error='COMMAND-FAILED'}},https=ok_https()})
  r=live.new(io_).probe(profile())
  t.eq(r.code,'SYSTEM-001');t.eq(r.https_success,3);t.eq(r.exit_ip,nil)
end)

t.test('quorum rules: VPN-003 below two HTTPS answers, DNS-001, per-check results',function()
  local h=ok_https()
  h['one.one.one.one']={{kind='timeout'}};h['dns.google']={{kind='http',status=503,body='busy'}}
  local r=live.new(scenario_io({https=h})).probe(profile())
  t.eq(r.code,'VPN-003');t.eq(r.https_success,1);t.eq(r.exit_ip,nil)
  t.eq(r.probe_checks[1].result,'timeout');t.eq(r.probe_checks[1].http_status,nil)
  t.eq(r.probe_checks[2].result,'http-error');t.eq(r.probe_checks[2].http_status,503)
  h=ok_https();h['dns.google']={{kind='http',status=426,body=''}};h['dns.quad9.net']={{kind='tls'}}
  r=live.new(scenario_io({https=h})).probe(profile())
  t.eq(r.code,'VPN-003');t.eq(r.probe_checks[2].result,'http-unsupported');t.eq(r.probe_checks[3].result,'tls-error')
  for _,mode in ipairs({'timeout','refused','bad-rcode','wrong-question','no-answer'}) do
    r=live.new(scenario_io({https=ok_https(),dns=mode})).probe(profile())
    t.eq(r.code,'DNS-001',mode);t.eq(r.dns_ok,false);t.eq(r.exit_ip,nil,'no exit_ip with a code')
  end
  h=ok_https();h['dns.google']={{kind='http',status=200,body='{"Status":2,"Answer":[]}'}};h['dns.quad9.net']={{kind='http',status=200,body='@DNSWIRE-BAD'}}
  r=live.new(scenario_io({https=h})).probe(profile())
  t.eq(r.code,'VPN-003');t.eq(r.probe_checks[2].result,'invalid-response');t.eq(r.probe_checks[3].result,'invalid-response')
  h=ok_https();h['one.one.one.one']={{kind='http',status=200,body='ip=93.184.216.34\n'}}
  r=live.new(scenario_io({https=h})).probe(profile())
  t.eq(r.probe_checks[1].result,'invalid-response','a trace needs ip= and http= lines');t.eq(r.code,NULL);t.eq(r.exit_ip,nil)
  h=ok_https();h['one.one.one.one']={{kind='http',status=200,body=string.rep('x',32769)}}
  r=live.new(scenario_io({https=h})).probe(profile())
  t.eq(r.probe_checks[1].result,'invalid-response')
end)

t.test('a route or device epoch change during the measurement is VENDOR-IDENTITY-CHANGED without measured fields',function()
  for _,after in ipairs({{code=NULL,device='wgclient1',mark=8192,table='1001',ifindex=12},{code=NULL,device='wgclient1',mark=4096,table='1001',ifindex=13},
                         {code='VPN-001'}}) do
    local r=live.new(scenario_io({bindings={BINDING,after},https=ok_https()})).probe(profile())
    t.eq(r.code,'VENDOR-IDENTITY-CHANGED')
    for _,k in ipairs({'https_success','dns_ok','rtt_ms','exit_ip','probe_checks'}) do t.eq(r[k],nil,k) end
    t.eq(r.device,'wgclient1','the before-binding stays (result.update)')
  end
end)

t.test('a Lua fault is not hidden as SYSTEM-001: it reaches the caller (backend falls back to Python)',function()
  local io_=scenario_io({bindings={{fault=true}},https=ok_https()})
  local err=t.raises(live.new(io_).probe,profile())
  t.truthy(type(err)=='string' and string.find(err,'lua fault',1,true))
end)

------------------------------------------------------------------------------------------------------
-- trace
------------------------------------------------------------------------------------------------------
t.test('trace uses the probe own valid trace answer: one probe_io, same exit as the separate fetch',function()
  local io_=scenario_io({https=ok_https()})
  t.eq(live.new(io_).trace(profile()),'93.184.216.34')
  t.eq(io_.calls.probe_io,1)
end)

t.test('trace refusals follow native_switch.trace and lua_bridge.py',function()
  local h=ok_https();h['dns.google']={{kind='timeout'}};h['dns.quad9.net']={{kind='timeout'}}
  t.code('TARGET-HTTPS-DNS-FAILED',live.new(scenario_io({https=h})).trace,profile())
  t.code('TARGET-HTTPS-DNS-FAILED',live.new(scenario_io({https=ok_https(),dns='timeout'})).trace,profile())
  t.code('TARGET-HTTPS-DNS-FAILED',live.new(scenario_io({bindings={{code='VPN-001'}}})).trace,profile())
  -- the probe's trace target failed, two others passed: the separate fetch decides
  h=ok_https();h['one.one.one.one']={{kind='http',status=503,body='x'},{kind='http',status=200,body=TRACE_BODY}}
  local io_=scenario_io({https=h})
  t.eq(live.new(io_).trace(profile()),'93.184.216.34');t.eq(io_.calls.probe_io,2)
  t.eq(io_.last.dns,nil);t.eq(#io_.last.requests,1);t.eq(io_.last.requests[1].path,'/cdn-cgi/trace')
  h=ok_https();h['one.one.one.one']={{kind='http',status=503,body='x'}}
  t.code('EXIT-TRACE-FAILED',live.new(scenario_io({https=h})).trace,profile())
  for _,kind in ipairs({'timeout','tls','transport'}) do
    h=ok_https();h['one.one.one.one']={{kind=kind}}
    t.code('NATIVE-SYSTEM-001',live.new(scenario_io({https=h})).trace,profile())
  end
  h=ok_https();h['one.one.one.one']={{kind='http',status=200,body='h=x\nip=93.184.216.34\n'},{kind='oversize'}}
  t.code('EXIT-TRACE-FAILED',live.new(scenario_io({https=h})).trace,profile())
  -- a valid trace body (ip= and http=) whose address is not global
  h=ok_https();h['one.one.one.one']={{kind='http',status=200,body='ip=10.1.2.3\nhttp=http/1.1\n'}}
  t.code('EXIT-IP-NOT-GLOBAL',live.new(scenario_io({https=h})).trace,profile())
end)

t.test('exit_of parses like dict(line.split("=",1)) + IPv4Address + is_global',function()
  local function exit(body) return live.exit_of({status=200,body=body}) end
  t.eq(exit('a=1\nip= 93.184.216.34 \r\nhttp=x\n'),'93.184.216.34')
  t.eq(exit('ip=10.0.0.1\nip=93.184.216.34\n'),'93.184.216.34','the last ip key wins')
  t.eq(exit('ip=93.184.216.34\rloc=DE'),'93.184.216.34','\\r is a line break for splitlines')
  t.code('EXIT-TRACE-FAILED',exit,'loc=DE\n')
  t.code('EXIT-TRACE-FAILED',exit,'ip=93.184.216.034\n')
  t.code('EXIT-TRACE-FAILED',exit,'ip=93.184.216\n')
  t.code('EXIT-TRACE-FAILED',exit,'ip=2606:4700::1\n')
  t.code('EXIT-TRACE-FAILED',exit,'ip=93.184.216.34\n\200\n')
  t.code('EXIT-IP-NOT-GLOBAL',exit,'ip=100.64.0.1\n')
  t.code('EXIT-TRACE-FAILED',live.exit_of,{status=404,body='ip=93.184.216.34\n'})
  t.code('EXIT-TRACE-FAILED',live.exit_of,{status=200,body=string.rep('a',32769)})
  t.eq(live.remember_exit('ip=10.0.0.1\nip=93.184.216.34\n'),nil,'remember_exit: the first ip= line decides')
end)

t.test('probe(profile,true) is kept for one trace of the same profile within 2 s (WAIT-CLIENT: probe then trace)',function()
  local io_=scenario_io({https=ok_https()})
  local L=live.new(io_)
  t.eq(L.probe(profile(),true).code,NULL)
  io_.clock_now=io_.clock_now+1.5
  t.eq(L.trace(profile()),'93.184.216.34')
  t.eq(io_.calls.probe_io,1,'the kept measurement answered')
  t.eq(L.trace(profile()),'93.184.216.34');t.eq(io_.calls.probe_io,2,'kept once only')
  L.probe(profile(),true);io_.clock_now=io_.clock_now+2.5
  L.trace(profile());t.eq(io_.calls.probe_io,4,'older than 2 s: probed again')
  L.probe(profile());L.trace(profile());t.eq(io_.calls.probe_io,6,'a probe without keep (health) is never reused')
  L.probe(profile(),true);L.trace(profile({interface='wgclient2'}))
  t.eq(io_.calls.probe_io,8,'another interface: probed again')
  local h=ok_https();h['dns.google']={{kind='timeout'}};h['dns.quad9.net']={{kind='timeout'}}
  io_=scenario_io({https=h});L=live.new(io_)
  L.probe(profile(),true);t.code('TARGET-HTTPS-DNS-FAILED',L.trace,profile());t.eq(io_.calls.probe_io,2,'a failed probe is not kept')
end)

------------------------------------------------------------------------------------------------------
-- sys.probe_io: the real shell group with a fake curl, the DNS loop with a fake nixio
------------------------------------------------------------------------------------------------------
local RUN=(os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp')..'/hv-live-probe-'..tostring(os.time())..'-'..tostring(math.random(1,1e6))
os.execute('mkdir -p '..RUN)
local fake_nixio={sent={},const={EAGAIN=11}}
local dns_script={}
function fake_nixio.socket(family,kind)
  local s={}
  function s:setopt(level,name,value) fake_nixio.bound=value;return true end
  function s:setblocking(v) return true end
  function s:connect(host,port) fake_nixio.peer={host,port};return true end
  function s:send(data) fake_nixio.sent[#fake_nixio.sent+1]=data;return #data end
  function s:recvfrom(n)
    local step=table.remove(dns_script,1)
    if step==nil or step=='wait' then return false,11 end
    if step=='error' then return nil,111 end
    if step=='junk' then return '\0\0junk' end
    return dns_answer(fake_nixio.sent[#fake_nixio.sent],'ok'),'9.9.9.9',53
  end
  function s:close() fake_nixio.closed=(fake_nixio.closed or 0)+1 end
  function s:fileno() return 99 end
  return s
end
function fake_nixio.poll_flags() return 1 end
function fake_nixio.poll(fds,ms_) fake_nixio.polls=(fake_nixio.polls or 0)+1;return 0 end
function fake_nixio.nanosleep(s,ns) os.execute('sleep '..string.format('%.3f',s+ns/1e9)) end
package.loaded['nixio']=fake_nixio
package.loaded['sys']=nil
local runner=require('runner')
runner.configure({runtime=RUN})
local sys=require('sys')
sys.RUNTIME=RUN

-- The offline CI sandbox mounts its tmpfs noexec: the fake programs below cannot run there (exit 126).
local function can_exec(folder)
  local p=folder..'/.exec-probe';local f=io.open(p,'wb');if not f then return false end
  f:write('#!/bin/sh\nexit 0\n');f:close();os.execute('chmod 700 '..p)
  local rc=os.execute(p..' >/dev/null 2>&1');os.remove(p);return rc==0 or rc==true
end
local EXEC=can_exec(RUN)
local CURL=RUN..'/curl'
local f=assert(io.open(CURL,'wb'))
f:write([[#!/bin/sh
# fake curl: -D head -o body -w fmt URL; behaviour by host; sleeps to prove the checks run side by side
head=;body=;url=;iface=
while [ $# -gt 0 ]; do
  case "$1" in
    -D) head=$2; shift;; -o) body=$2; shift;; --interface) iface=$2; shift;;
    -m|--proto|--max-redirs|--resolve|-H|--max-filesize|-w) shift;;
    https://*) url=$1;;
  esac
  shift
done
echo "$iface $url" >>"$(dirname "$head")/curl.log"
sleep 1
case "$url" in
  https://one.one.one.one/*) printf 'HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\n' >"$head"; printf 'ip=1.2.3.4\nhttp=x\n' >"$body"; printf 0.210; exit 0;;
  https://dns.google/*) printf 'HTTP/1.1 503 Busy\r\n\r\n' >"$head"; : >"$body"; printf 0.300; exit 0;;
  https://dns.quad9.net/*) printf 0.000; exit 60;;
esac
exit 6
]]);f:close()
os.execute('chmod 755 '..CURL)

t.test('sys.probe_io: curl children side by side, statuses and files mapped, nothing left in RAM',function()
  if not EXEC then print('  skipped: noexec temporary directory');return end
  sys.CURL=CURL
  local requests={}
  for i,target in ipairs(require('probe').TARGETS) do requests[i]={address=target[1],hostname=target[2],path=target[3],seconds=6} end
  dns_script={'wait','junk','ok'}
  local accepted={}
  local started=os.time()
  local answers,data,kind=sys.probe_io('wgclient1',requests,{host='9.9.9.9',port=53,packet='TK'..string.rep('\0',10)..'q',seconds=3,
    accept=function(d) accepted[#accepted+1]=d;return string.sub(d,1,2)=='TK' end})
  t.truthy(os.time()-started<=2,'three 1 s checks finished together')
  t.eq(answers[1].response.status,200);t.eq(answers[1].response.body,'ip=1.2.3.4\nhttp=x\n');t.eq(answers[1].elapsed,0.21)
  t.eq(answers[2].response.status,503);t.eq(answers[2].elapsed,0.3)
  t.eq(answers[3].response,nil);t.eq(answers[3].kind,'tls-error')
  t.truthy(type(data)=='string' and string.sub(data,1,2)=='TK','the DNS answer');t.eq(kind,nil)
  t.eq(#accepted,2,'a foreign datagram is ignored');t.eq(fake_nixio.bound,'wgclient1');t.eq(fake_nixio.peer,{'9.9.9.9',53})
  t.truthy((fake_nixio.polls or 0)>=1,'waits on poll, no busy loop')
  local log=assert(io.open(RUN..'/curl.log','rb'));local text=log:read('*a');log:close();os.remove(RUN..'/curl.log')
  t.truthy(string.find(text,'wgclient1 https://dns.quad9.net/dns-query',1,true),'--interface <device>')
  local p=io.popen('ls -A '..RUN);local left=p:read('*a');p:close()
  t.eq(left,'curl\n','no probe files left')
end)

t.test('sys.probe_io: DNS timeout and transport error, refused arguments',function()
  sys.CURL=CURL
  dns_script={}
  local answers,data,kind=sys.probe_io('wgclient1',{},{host='9.9.9.9',port=53,packet='TK',seconds=1,accept=function() return true end})
  t.eq(#answers,0);t.eq(data,nil);t.eq(kind,'timeout')
  dns_script={'error'}
  answers,data,kind=sys.probe_io('wgclient1',{},{host='9.9.9.9',port=53,packet='TK',seconds=1,accept=function() return true end})
  t.eq(kind,'transport')
  t.raises(sys.probe_io,"wg'x",{},nil)
  t.raises(sys.probe_io,'wgclient1',{{address='1.1.1.1',hostname='one.one.one.one',path="/x'y",seconds=6}},nil)
  t.raises(sys.probe_io,'wgclient1',{{address='1.1.1.1;reboot',hostname='one.one.one.one',path='/x',seconds=6}},nil)
  t.eq(sys.curl_answer(28),nil);t.eq(select(2,sys.curl_answer(124)),'timeout');t.eq(select(2,sys.curl_answer(63)),'invalid-response')
  t.eq(select(2,sys.curl_answer(7,nil,nil)),'transport-error');t.eq(select(2,sys.curl_answer(0,'garbage','')),'invalid-response')
  t.eq(sys.curl_answer(63,'HTTP/1.1 200 OK\r\n\r\n','xx'),{status=200,body='xx',oversize=true},'oversize keeps the status')
  t.eq(sys.curl_answer(63,nil,nil),nil)
  t.eq(sys.curl_answer(0,'HTTP/1.1 100 Continue\r\n\r\nHTTP/1.1 204 No\r\n\r\n',''),{status=204,body=''})
end)

------------------------------------------------------------------------------------------------------
-- backend.probe/trace: native first, lua_bridge.py as the fallback
------------------------------------------------------------------------------------------------------
local fake=require('backend_fake')
local backend_mod=require('backend')
local function backend_with(native_sc,config)
  local w={files={['/etc/config/homensai_vpn']=config or "config main 'main'\n\toption lua_auto '1'\n"},clock=1000,wall=1761830400}
  local S=fake.new(w)
  local io_=nil
  if native_sc then
    io_=scenario_io(native_sc)
    S.probe_capable=function() return true end
    S.probe_io=function(...) return io_.probe_io(...) end
    S.random=io_.random
  end
  w.handler=function(argv)
    if argv[1]=='python3' then
      if argv[3]=='trace' then return 0,'{"exit":"198.51.100.7"}\n' end
      return 0,canon.encode(canon.object({id='x',code=NULL,dns_ok=true,https_success=3,via='bridge'}))..'\n'
    end
  end
  local B=backend_mod.new(S)
  B.route_binding=function(logical) return io_.route_binding(logical) end
  B.inventory=function() return {profiles={profile()}} end
  return B,S,io_
end

t.test('backend: the native probe answers health and trace without a Python process',function()
  local B,S,io_=backend_with({https=ok_https()})
  t.eq(B.native_probe_enabled(),true)
  t.eq(B.health('wireguard:peer_2002'),true)
  t.eq(B.trace(profile()),'93.184.216.34')
  t.eq(S.calls['exec:python3'],nil,'no Python start')
  t.eq(io_.calls.probe_io,2)
  local r=B.probe(profile(),true);t.eq(r.via,nil);t.eq(B.trace(profile()),'93.184.216.34');t.eq(io_.calls.probe_io,3,'keep reaches live_probe')
  local h=ok_https();h['one.one.one.one']={{kind='timeout'}};h['dns.google']={{kind='timeout'}}
  B=backend_with({https=h})
  t.eq(B.health('wireguard:peer_2002'),false,'VPN-003 is unhealthy')
  B=backend_with({https=ok_https(),bindings={{error='POLICY-READ-FAILED'}}})
  t.eq(B.health('wireguard:peer_2002'),nil,'SYSTEM-001 is unknown')
  B=backend_with({https=ok_https(),bindings={{code='VPN-001'}}})
  t.code('TARGET-HTTPS-DNS-FAILED',B.trace,profile())
end)

t.test('backend: option lua_probe 0, no native primitives, or a Lua fault keep the Python bridge',function()
  local B,S=backend_with({https=ok_https()},"config main 'main'\n\toption lua_probe '0'\n")
  t.eq(B.native_probe_enabled(),false)
  t.eq(B.probe(profile()).via,'bridge');t.eq(B.trace(profile()),'198.51.100.7');t.eq(S.calls['exec:python3'],2)
  B,S=backend_with(nil)
  t.eq(B.native_probe_enabled(),false);t.eq(B.probe(profile()).via,'bridge')
  B,S=backend_with({https=ok_https(),bindings={{fault=true}}})
  local stderr=io.stderr
  io.stderr={write=function() end}
  local r=B.probe(profile());local exit=B.trace(profile())
  io.stderr=stderr
  t.eq(r.via,'bridge');t.eq(exit,'198.51.100.7');t.eq(B.native_faults,2);t.eq(S.calls['exec:python3'],2)
end)

t.test('cleanup of the test RAM directory',function() os.execute('rm -rf '..RUN) end)

t.run()
