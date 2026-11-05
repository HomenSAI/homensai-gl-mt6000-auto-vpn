-- probe_trust.lua: the shared cases of ../probe_trust_cases.json (the same as test_probe_trust.py), the anchor files
-- of the package, the curl codes of an untrusted peer, the cached probe_dns option and the probe.lua wiring
-- (redirect, untrusted certificate, replayed trace, DoH DNS check) through the monitor harness.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local trust=require('probe_trust')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../probe_trust_cases.json'))
local ANCHORS=t.here..'/../../files/usr/lib/homensai-vpn/probe-anchors'
local function val(v) if v==NULL then return nil end return v end
local function num(v) return canon.number(v) or v end

t.test('fresh: the shared cases',function()
  t.truthy(#CASES.fresh>=25)
  for _,c in ipairs(CASES.fresh) do
    local got=trust.fresh(c.body,c.agent,num(c.wall[1]),num(c.wall[2]),num(c.elapsed))
    t.eq(got,val(c.expect),c.name)
  end
end)

t.test('dns_mode, redirect, anchor_file and the untrusted curl codes: the shared cases',function()
  for _,c in ipairs(CASES.dns_mode) do t.eq(trust.dns_mode(val(c.text)),c.expect,tostring(val(c.text))) end
  for _,c in ipairs(CASES.redirect) do t.eq(trust.redirect(num(c[1])),c[2],tostring(num(c[1]))) end
  local saved=trust.ANCHORS;trust.ANCHORS=ANCHORS;trust.reset()
  for _,c in ipairs(CASES.anchor_file) do
    local path=trust.anchor_file(c[1])
    t.eq(path~=nil,c[2],c[1])
    if path then t.eq(path,ANCHORS..'/'..c[1]..'.pem') end
  end
  trust.ANCHORS='/nonexistent';trust.reset()
  t.eq(trust.anchor_file('one.one.one.one'),nil,'no anchor file: nil (the system store is used)')
  trust.ANCHORS=saved;trust.reset()
  for _,c in ipairs(CASES.curl_untrusted) do t.eq(trust.CURL_UNTRUSTED[num(c[1])]==true,c[2],tostring(num(c[1]))) end
  local sys=require('sys')
  t.eq(select(2,sys.curl_answer(60,nil,nil)),'tls-untrusted');t.eq(select(2,sys.curl_answer(90,nil,nil)),'tls-untrusted')
  t.eq(select(2,sys.curl_answer(35,nil,nil)),'tls-error');t.eq(select(2,sys.curl_answer(77,nil,nil)),'tls-error')
end)

t.test('agent: 128-bit nonce, hex, one per call',function()
  local n=0
  local function random(k) n=n+1;return string.rep(string.char(n),k) end
  local a,b=trust.agent(random),trust.agent(random)
  t.eq(a,'HomenSAI-probe/'..string.rep('01',16));t.eq(b,'HomenSAI-probe/'..string.rep('02',16))
  t.truthy(#a<=64 and string.find(a,'^[A-Za-z0-9/_.-]+$'),'passes the curl argument check of sys/monitor_io')
end)

t.test('current_dns_mode: re-read only when the configuration key changes; unreadable is udp',function()
  trust.reset()
  local reads=0
  local text="config main 'main'\n\toption probe_dns 'doh'\n"
  local key='1'
  local function key_fn() return key end
  local function text_fn() reads=reads+1;return text end
  t.eq(trust.current_dns_mode(key_fn,text_fn),'doh');t.eq(trust.current_dns_mode(key_fn,text_fn),'doh');t.eq(reads,1)
  text="config main 'main'\n";key='2'
  t.eq(trust.current_dns_mode(key_fn,text_fn),'udp');t.eq(reads,2)
  t.eq(trust.current_dns_mode(function() return nil end,text_fn),'udp','no file')
  t.eq(trust.current_dns_mode(function() error('x') end,text_fn),'udp','stat fault')
  t.eq(trust.current_dns_mode(nil,nil),'udp','a runner without the configuration')
  trust.reset()
end)

t.test('anchor files: certificates only, one file per probe host, every pinned name present',function()
  local pins=canon.decode(read_file(ANCHORS..'/pins.json'))
  for _,host in ipairs({'one.one.one.one','dns.google','dns.quad9.net'}) do
    local text=read_file(ANCHORS..'/'..host..'.pem')
    t.truthy(not string.find(text,'PRIVATE',1,true),'no key material')
    local count=0;for _ in string.gmatch(text,'%-%-%-%-%-BEGIN CERTIFICATE%-%-%-%-%-') do count=count+1 end
    t.eq(count,#pins.hosts[host],host)
    for _,row in ipairs(pins.hosts[host]) do t.truthy(string.find(text,'# '..row.name..' (',1,true),row.name) end
  end
end)

------------------------------------------------------------------------------------------------------
-- probe.lua (the Lua monitor) through the monitor harness
------------------------------------------------------------------------------------------------------
local mt=dofile(t.here..'/monitor_harness.lua')
local probe=require('probe')
local function run(R)
  local out
  probe.probe(R,R.inventory_data.profiles[1],function(result) out=result end)
  if R.drain then R.drain() end
  return out
end

t.test('probe.lua: nonce per request, a foreign or replayed trace never counts, uag echo makes it fresh',function()
  local R=mt.fake_runner()
  local r=run(R)
  t.eq(r.code,nil);t.eq(r.https_success,3);t.truthy(string.find(R.last_https.agent,'^HomenSAI%-probe/%x+$'))
  local replies={
    ['ip=93.184.216.34\nhttp=x\nuag=curl/7.83.1\n']='stale-response',
    ['ip=93.184.216.34\nhttp=x\n']='stale-response',
    ['ip=93.184.216.34\nhttp=x\nts=1\n']='stale-response'}
  for body,reason in pairs(replies) do
    R=mt.fake_runner()
    local https=R.https_get
    R.https_get=function(device,address,hostname,path,seconds,cb,agent)
      if address=='1.1.1.1' then cb({status=200,body=body});return end
      return https(device,address,hostname,path,seconds,cb,agent)
    end
    r=run(R)
    t.eq(r.code,nil,body);t.eq(r.https_success,2);t.eq(r.probe_checks[1].result,'invalid-response');t.eq(r.probe_checks[1].trust,reason)
    t.eq(r.exit_ip,nil,'no exit from a page that is not this request answer')
  end
end)

t.test('probe.lua: untrusted certificate and portal redirects give VPN-003 with probe_trust; a plain outage does not',function()
  local R=mt.fake_runner()
  R.https_fail['8.8.8.8']='tls-untrusted';R.https_fail['9.9.9.9']='tls-untrusted'
  local r=run(R)
  t.eq(r.code,'VPN-003');t.eq(r.probe_trust,'untrusted')
  t.eq(r.probe_checks[2].result,'tls-error');t.eq(r.probe_checks[2].trust,'untrusted-certificate')
  R=mt.fake_runner()
  R.https_reply=function(address,path,agent) return {status=302,body=''} end
  r=run(R)
  t.eq(r.code,'VPN-003');t.eq(r.probe_trust,'untrusted');t.eq(r.probe_checks[1].trust,'portal-redirect');t.eq(r.probe_checks[1].http_status,302)
  R=mt.fake_runner()
  R.https_fail['8.8.8.8']='timeout';R.https_fail['9.9.9.9']='tls-error'
  r=run(R)
  t.eq(r.code,'VPN-003');t.eq(r.probe_trust,nil);t.eq(r.probe_checks[3].trust,nil)
  -- the status sanitizer keeps the reason (vendor.lua probe_checks / MEASUREMENT_FIELDS)
  local vendor=require('vendor')
  local clean=vendor.probe_checks({{target='dns.google',result='tls-error',trust='untrusted-certificate'},
    {target='dns.quad9.net',result='ok',trust='portal-redirect'},{target='one.one.one.one',result='timeout',trust='other'}})
  t.eq(clean[1].trust,'untrusted-certificate');t.eq(clean[2].trust,nil,'never on a passing check');t.eq(clean[3].trust,nil,'unknown reason dropped')
end)

t.test('probe.lua: option probe_dns doh sends the DNS question to dns.google over HTTPS, not UDP',function()
  trust.reset()
  local R=mt.fake_runner()
  local text="config main 'main'\n\toption probe_dns 'doh'\n"
  R.config_mtime=function() return 'k1' end
  R.config_text=function() return text end
  R.last_udp=nil
  local seen={}
  local https=R.https_get
  R.https_get=function(device,address,hostname,path,seconds,cb,agent)
    seen[#seen+1]=hostname..path
    return https(device,address,hostname,path,seconds,cb,agent)
  end
  local r=run(R)
  t.eq(r.code,nil);t.eq(r.dns_ok,true);t.eq(R.last_udp,nil,'no UDP question');t.eq(#seen,4)
  local doh=false;for _,s in ipairs(seen) do if string.find(s,'^dns%.google/dns%-query%?dns=') then doh=true end end
  t.truthy(doh,'RFC 8484 GET to dns.google')
  R.https_fail['8.8.8.8']='tls-untrusted'
  r=run(R)
  t.eq(r.dns_ok,false,'an untrusted DoH answer is no DNS answer')
  trust.reset()
end)

t.run()
