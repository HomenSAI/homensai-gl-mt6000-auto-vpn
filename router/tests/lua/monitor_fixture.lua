-- Driver for tests/test_lua_monitor.py: runs two monitor passes with the fake runner and writes the files the
-- Python validators check. Usage: lua5.1 monitor_fixture.lua <output directory>
-- Also: lua5.1 monitor_fixture.lua encode <json text>  -> canonical text and sha256 of the decoded value.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
if arg[1]=='encode' then
  local value=canon.decode(arg[2])
  print(canon.encode(value));print(canon.digest(value))
  os.exit(0)
end
if arg[1]=='decode_request' then
  local rpc=require('rpc')
  local ok,result=pcall(rpc.decode_request,arg[2])
  if ok then print('OK '..canon.encode(result)) else print('ERR '..(type(result)=='table' and result.code or tostring(result))) end
  os.exit(0)
end
if arg[1]=='setup' then
  -- lua5.1 monitor_fixture.lua setup <method> <json arguments> <now>: the UCI 'main' keys or the refusal code
  local setup=require('setup')
  local kind=setup.KIND[arg[2]]
  local ok,result=pcall(function()
    local arguments=canon.decode(arg[3])
    if kind=='probe' then return setup.probe_payload(arguments)
    elseif kind=='response' then return setup.response_payload(arguments)
    else return setup.stats_payload(arguments,tonumber(arg[4])) end
  end)
  if ok then print('OK '..canon.encode(canon.object(result))) else print('ERR '..(type(result)=='table' and result.code or tostring(result))) end
  os.exit(0)
end
if arg[1]=='vendor' then
  -- lua5.1 monitor_fixture.lua vendor <scenario.json>: VendorObserver steps with a counting uuid source
  local f=assert(io.open(arg[2],'rb'));local scenario=canon.decode(f:read('*a'));f:close()
  local n=0
  local observer=require('vendor').Observer(function() n=n+1;return string.format('%032x',n) end)
  local out=canon.array()
  for _,step in ipairs(scenario.steps) do
    local observation,rows=observer:observe(step.before,step.after,step.measured,canon.number(step.now))
    local list=canon.array();for _,r in ipairs(rows) do list[#list+1]=canon.object(r) end
    out[#out+1]=canon.array({observation,list})
  end
  print(canon.encode(out))
  os.exit(0)
end
if arg[1]=='item2' then
  -- Diagnostics run with a trusted pair: writes the files the Python readers check (test_lua_monitor_item2.py).
  local out=arg[2]
  local monitor=require('monitor')
  local page=require('monitor_status')
  local responses=require('response_history')
  local DIAG="config main 'main'\n\toption stats_mode 'diagnostic'\n\toption stats_until '1761900000'\n"
  local R=t.fake_runner({config=DIAG})
  R.config_version='item2'
  local function native() R.write_atomic('/run/hv/native-status.json',canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',
    proof_scope='router-probed-ipv4',readiness_verified=true,time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))) end
  native()
  R.inventory_data.settings.probe_level='2';R.inventory_data.settings.probe_boost='0'
  R.write_atomic('/etc/hv/switch-timing.json','{"avg_seconds":4.26,"count":3,"last_seconds":3.9,"updated":1761825000.5}')
  local m=monitor.new(R)
  m:pass()
  R.advance(30);native();R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
  m:pass()
  R.advance(900);native();R.https_fail={};R.icmp_rtt=20.25
  m:pass()
  local env=page.env(R,'/run/hv','/etc/hv')
  local history=require('history').new(env,'/etc/hv',10000,7)
  history:record({state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_7',target='wireguard:peer_8',proof_scope='router-probed-ipv4'},R.now-100)
  history:record({state='ARMED',reason='SOURCE-FAILED',source='wireguard:peer_7',target='wireguard:peer_8',proof_scope='router-probed-ipv4',transition_source='automatic'},R.now-50)
  local function save(name,text) local f=assert(io.open(out..'/'..name,'wb'));f:write(text);f:close() end
  for _,name in ipairs({'ping-response-history.json','probe-history.json','checkpoint.json','native-history.json','switch-timing.json'}) do
    if R.files['/etc/hv/'..name] then save(name,R.files['/etc/hv/'..name]) end
  end
  save('probe-boost.json',R.files['/run/hv/probe-boost.json'])
  save('status.json',R.files['/run/hv/status.json'])
  save('status_reply.json',canon.encode(m.rpc.handle('status','{}')))
  local loaded=responses.load(m.io,'/etc/hv/ping-response-history.json')
  save('ping_public.json',canon.encode(loaded:public(R.now)))
  save('native_history_public.json',canon.encode(page.native_history(env,7,R.now)))
  save('booster_public.json',canon.encode(m.booster:public(m.settings,R.now)))
  save('meta.json',canon.encode(canon.object({now=canon.float(R.now),settings=canon.object(m.settings)})))
  print('ok')
  os.exit(0)
end
local out=arg[1]
local monitor=require('monitor')
local R=t.fake_runner()
R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
local m=monitor.new(R)
m:pass()
R.advance(10);R.counters.wgclient.rx=R.counters.wgclient.rx+12345;R.counters.wgclient.tx=R.counters.wgclient.tx+678;R.counters.eth0.rx=R.counters.eth0.rx+999
R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
m:pass()
R.advance(900);R.https_fail={}
m:pass()
m:shutdown()
local function save(name,text) local f=assert(io.open(out..'/'..name,'wb'));f:write(text);f:close() end
save('status.json',R.files['/run/hv/status.json'])
save('checkpoint.json',R.files['/etc/hv/checkpoint.json'])
save('checkpoint.backup.json',R.files['/etc/hv/checkpoint.backup.json'])
save('status_reply.json',canon.encode(m.rpc.handle('status','{}')))
save('auto_live.json',canon.encode(m.rpc.handle('auto_live','{}')))
print('ok')
