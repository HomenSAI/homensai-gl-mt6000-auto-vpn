-- setup.lua: setup_probe/setup_response/setup_stats answered natively: codes, UCI keys, guards, fallback.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local setup=require('setup')
local monitor=require('monitor')

local function code(fn,...) local ok,err=pcall(fn,...);if ok then return 'OK' end;return type(err)=='table' and err.code or tostring(err) end
local function args(text) return canon.decode(text) end

t.test('payload validation codes and keys (setup_config.probe_payload/response_payload, stats_mode.payload)',function()
  t.eq(setup.probe_payload(args('{"level":3,"boost":false}')),{probe_level='3',probe_boost='0',interval='20',measure_interval='60'})
  t.eq(setup.probe_payload(args('{"level":1,"boost":false}')),{probe_level='1',probe_boost='1',interval='60',measure_interval='300'},'forced boost')
  t.eq(code(setup.probe_payload,args('{"level":3}')),'PROBE-SETTINGS-FIELDS')
  t.eq(code(setup.probe_payload,args('{"level":3,"boost":1}')),'PROBE-SETTINGS-FIELDS')
  t.eq(code(setup.probe_payload,args('{"level":3,"boost":true,"x":1}')),'PROBE-SETTINGS-FIELDS')
  t.eq(code(setup.probe_payload,args('{"level":6,"boost":true}')),'PROBE-SETTINGS-RANGE')
  t.eq(code(setup.probe_payload,args('{"level":3.0,"boost":true}')),'PROBE-SETTINGS-RANGE','a JSON float is not an int')
  t.eq(code(setup.probe_payload,args('{"level":"3","boost":true}')),'PROBE-SETTINGS-RANGE')
  t.eq(setup.response_payload(args('{"metric":"websites","compare":true,"fast_switch":false}')),{response_metric='websites',response_compare='1',fast_switch='0'})
  t.eq(setup.response_payload(args('{"metric":"icmp-9.9.9.9"}')),{response_metric='icmp-9.9.9.9'})
  t.eq(setup.response_payload(args('{"metric":"icmp-1.1.1.1","ping_interval":10}')),{response_metric='icmp-1.1.1.1',ping_interval='10'})
  t.eq(setup.response_payload(args('{"metric":"websites","ping_interval":300}')),{response_metric='websites',ping_interval='300'})
  for _,bad in ipairs({'0','5','15','301','310','-10','60.0','"60"','true','null','[60]'}) do
    t.eq(code(setup.response_payload,args('{"metric":"icmp-1.1.1.1","ping_interval":'..bad..'}')),'PING-INTERVAL-INVALID',bad)
  end
  t.eq(code(setup.response_payload,args('{"metric":"x","ping_interval":5}')),'RESPONSE-METRIC-INVALID','the metric is checked first')
  for _,bad in ipairs({'{}','{"metric":"icmp-1.1.1.2"}','{"metric":"websites","compare":1}','{"metric":"websites","other":true}','{"metric":5}'}) do
    t.eq(code(setup.response_payload,args(bad)),'RESPONSE-METRIC-INVALID',bad)
  end
  t.eq(setup.stats_payload(args('{"mode":"work"}'),1000.7),{stats_mode='work',stats_until='0'})
  t.eq(setup.stats_payload(args('{"mode":"diagnostic","hours":72}'),1000.7),{stats_mode='diagnostic',stats_until='260200'})
  for _,bad in ipairs({'{}','{"mode":"work","hours":24}','{"mode":"diagnostic"}','{"mode":"diagnostic","hours":48}','{"mode":"diagnostic","hours":24.0}','{"mode":"x"}'}) do
    t.eq(code(setup.stats_payload,args(bad),1),'STATS-SETTINGS-FIELDS',bad)
  end
end)

local function deps(options)
  options=options or {}
  local R=t.fake_runner()
  local store={main={}}
  return {runner=R,runtime='/run/hv',persist='/etc/hv',now=function() return R.now end,
    cursor=t.fake_uci(store,options)},R,store
end

t.test('save: the UCI keys are written, verified and acknowledged like setup_save.lua',function()
  local d,R,store=deps()
  t.eq(setup.save(d,'setup_probe',args('{"level":2,"boost":false}')),{saved=true,mode='monitor',requires_lan_certification=true})
  t.eq(store.main,{probe_level='2',probe_boost='1',interval='30',measure_interval='120'});t.eq(store.commits,1)
  R.advance(3)
  t.eq(setup.save(d,'setup_response',args('{"metric":"icmp-8.8.8.8","fast_switch":true}')).saved,true)
  t.eq(store.main.response_metric,'icmp-8.8.8.8');t.eq(store.main.fast_switch,'1')
  R.advance(3)
  t.eq(setup.save(d,'setup_response',args('{"metric":"icmp-8.8.8.8","ping_interval":120}')).saved,true)
  t.eq(store.main.ping_interval,'120','the owner ping interval is written like setup_save.lua')
  R.advance(3)
  t.eq(setup.save(d,'setup_response',args('{"metric":"icmp-8.8.8.8","ping_interval":7}')),{saved=false,code='PING-INTERVAL-INVALID'})
  t.eq(store.main.ping_interval,'120','a refused value changes nothing')
  t.eq(setup.save(d,'setup_stats',args('{"mode":"diagnostic","hours":24}')).saved,true)
  t.eq(store.main.stats_until,string.format('%d',math.floor(R.now+86400)))
  t.eq(setup.save(d,'setup_probe',args('{"level":9,"boost":true}')),{saved=false,code='PROBE-SETTINGS-RANGE'})
end)

t.test('guards: rate limit, journal phase, refused journal, pending delta, unconfirmed readback, failed write',function()
  local d,R=deps()
  t.eq(setup.save(d,'setup_stats',args('{"mode":"work"}')).saved,true)
  t.eq(setup.save(d,'setup_stats',args('{"mode":"work"}')),{saved=false,code='RPC-RATE-LIMIT'},'2 s per kind (rpc_throttle)')
  t.eq(setup.save(d,'setup_response',args('{"metric":"websites"}')).saved,true,'another kind is not throttled')
  R.advance(2)
  t.eq(setup.save(d,'setup_stats',args('{"mode":"work"}')).saved,true)
  local journal=require('journal')
  local value=canon.object({phase='APPLYING'})
  R.files['/etc/hv/native-transaction.json']=canon.encode(canon.object({schema=1,data=value,sha256='0'}))
  t.eq(setup.save(d,'setup_probe',args('{"level":3,"boost":true}')),{saved=false,code='CONFIG-RECOVERY-UNVERIFIED'},'a journal with a bad digest')
  local orig=journal.read
  journal.read=function() return canon.object({phase='APPLYING'}) end
  t.eq(setup.save(d,'setup_probe',args('{"level":3,"boost":true}')),{saved=false,code='PROBE-SETTINGS-BUSY'})
  journal.read=function() return canon.object({phase='COMMITTED'}) end
  R.advance(3)
  t.eq(setup.save(d,'setup_probe',args('{"level":3,"boost":true}')).saved,true,'a settled journal')
  journal.read=orig
  local d2=deps({fail_set=true})
  t.eq(setup.save(d2,'setup_stats',args('{"mode":"work"}')),{saved=false,code='SETUP-SAVE-FAILED'})
  local d3,_,store3=deps({corrupt_after_commit='stats_mode'})
  t.eq(setup.save(d3,'setup_stats',args('{"mode":"work"}')),{saved=false,code='SETUP-SAVE-UNCONFIRMED'})
  t.eq(store3.commits,1)
  local dir=os.getenv('TMPDIR') or '/tmp'
  local savedir=dir..'/homensai-test-savedir-'..tostring(os.time())
  os.execute('mkdir -p '..savedir)
  local f=io.open(savedir..'/homensai_vpn','w');f:write('homensai_vpn.main.x=1\n');f:close()
  local d4=deps({savedir=savedir})
  t.eq(setup.save(d4,'setup_stats',args('{"mode":"work"}')),{saved=false,code='SETUP-PENDING-DELTA'})
  os.execute('rm -rf '..savedir)
end)

t.test('fallback to agent.py: control lock busy, or a speed test pause (probe only)',function()
  local d,R,store=deps()
  R.locked['auto-control.lock']=true
  t.truthy(setup.save(d,'setup_stats',args('{"mode":"work"}'))==setup.FALLBACK)
  t.eq(store.commits,nil,'nothing written')
  R.locked={}
  R.files['/run/hv/speed-pause.json']='{}'
  t.truthy(setup.save(d,'setup_probe',args('{"level":3,"boost":true}'))==setup.FALLBACK)
  t.eq(setup.save(d,'setup_stats',args('{"mode":"work"}')).saved,true,'only setup_probe waits for the speed test')
end)

t.test('through the monitor rpc: native answer, FALLBACK, input codes',function()
  local R=t.fake_runner()
  local store={main={}}
  local m=monitor.new(R,{cursor=t.fake_uci(store)})
  t.eq(m.rpc.handle('setup_probe','{"level":4,"boost":true,"ubus_rpc_session":"s"}'),{saved=true,mode='monitor',requires_lan_certification=true})
  t.eq(store.main.probe_level,'4')
  t.eq(m.rpc.handle('setup_probe','{"level":4,"level":5,"boost":true}'),{error='RPC-DUPLICATE-FIELD'})
  R.locked['auto-control.lock']=true
  t.truthy(m.rpc.handle('setup_response','{"metric":"websites"}')==require('rpc').FALLBACK)
end)

t.run()
