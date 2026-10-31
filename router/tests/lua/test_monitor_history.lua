-- monitor.lua + Lua plan item 6: reliability in the status and checkpoint, latency history, early (critical)
-- saves in Diagnostics, the owner's statistics reset applied by the monitor (archive, locks, result file).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local monitor=require('monitor')

local function fresh(options)
  local R=t.fake_runner(options)
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  return R,monitor.new(R)
end
local function request(R,scope,nonce)
  R.files['/run/hv/stats-reset-request.json']=canon.encode(canon.object({scope=scope,time=R.now,nonce=nonce or string.rep('b',32)}))
end
local function archives(R)
  local n=0;for path in pairs(R.files) do if string.find(path,'^/etc/hv/stats%-archive/') then n=n+1 end end;return n
end

t.test('the status carries the reliability view and the checkpoint the reliability model',function()
  local R,m=fresh()
  local status=m:pass()
  t.truthy(canon.is_object(status.accounting.reliability));t.eq(status.accounting.reliability.checkpointed,true)
  t.eq(status.accounting.reliability.totals.checks,2)
  t.truthy(canon.is_object(status.latency_history));t.eq(status.latency_history.technical_history_tail_only,true)
  t.eq(status.latency_history.metric,'https-rtt-ms')
  m:shutdown()
  local saved=canon.decode(R.files['/etc/hv/checkpoint.json'])
  t.eq(saved.data.accounting.reliability.schema,1)
  t.eq(saved.data.accounting.reliability.totals.checks,2)
  t.eq(saved.data.accounting.wan.reliability.sequence,0,'the WAN accounting carries its own (empty) model, as in Python')
  t.truthy(R.files['/etc/hv/latency-history.json']~=nil,'Diagnostics saves the latency history with the checkpoint')
end)

t.test('Diagnostics: an outage edge saves within a minute, not only every checkpoint interval',function()
  local R,m=fresh()
  m:pass()
  local before=R.versions['/etc/hv/checkpoint.json'] or 0
  R.advance(10);R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout'
  m:pass()
  t.eq(R.versions['/etc/hv/checkpoint.json'] or 0,before,'spacing: no save before 60 s')
  R.advance(55);m:pass()
  t.eq((R.versions['/etc/hv/checkpoint.json'] or 0)-before,1,'the critical save after 60 s')
  t.eq(m.accounting.reliability.critical,false)
  R.advance(70);m:pass()
  t.eq((R.versions['/etc/hv/checkpoint.json'] or 0)-before,1,'no further save without a new edge')
end)

t.test('Work mode: no early save, no latency history file',function()
  local R,m=fresh({config="config main 'main'\n\toption stats_mode 'work'\n"})
  m:pass()
  R.advance(10);R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='timeout';m:pass()
  R.advance(120);m:pass()
  t.eq(R.files['/etc/hv/checkpoint.json'],nil,'Work mode saves once a day and at shutdown')
  m:shutdown()
  t.truthy(R.files['/etc/hv/checkpoint.json']~=nil)
  t.eq(R.files['/etc/hv/latency-history.json'],nil)
end)

t.test('a queued statistics reset is applied at the start of a pass: archive, result, checkpoint',function()
  local R,m=fresh()
  m:pass();R.advance(10);R.counters.wgclient.rx=R.counters.wgclient.rx+5000;m:pass()
  t.truthy(next(m.accounting.months)~=nil)
  request(R,'traffic')
  R.advance(10);m:pass()
  t.eq(R.files['/run/hv/stats-reset-request.json'],nil,'the request is consumed')
  local result=canon.decode(R.files['/run/hv/stats-reset-result.json'])
  t.eq(result.done,true);t.eq(result.scope,'traffic');t.eq(result.nonce,string.rep('b',32))
  t.eq(archives(R),1)
  local archive=canon.decode(R.files['/etc/hv/stats-archive/'..result.archive])
  t.eq(archive.sha256,canon.digest(archive.data));t.truthy(archive.data.traffic.months~=nil)
  t.truthy(R.files['/etc/hv/checkpoint.json']~=nil,'the reset is saved at once')
  t.eq(m.accounting.gaps,0)
end)

t.test('a busy native-history lock keeps an auto reset queued; the next pass applies it',function()
  local R,m=fresh()
  m:pass()
  request(R,'auto')
  R.locked['native-history.lock']=true
  R.advance(10);m:pass()
  t.truthy(R.files['/run/hv/stats-reset-request.json']~=nil,'still queued');t.eq(R.files['/run/hv/stats-reset-result.json'],nil)
  R.locked['native-history.lock']=nil
  R.advance(10);m:pass()
  local result=canon.decode(R.files['/run/hv/stats-reset-result.json'])
  t.eq(result.done,true);t.eq(m.accounting.reliability.data.sequence,0,'the reliability model starts again')
  local history=canon.decode(R.files['/etc/hv/native-history.json'])
  t.eq(history.data.counter_accuracy,'reset by the owner')
  t.eq(R.files['/etc/hv/native-history.backup.json'],R.files['/etc/hv/native-history.json'])
end)

t.test('a malformed request is dropped without a result; archives are bounded to ten',function()
  local R,m=fresh()
  R.files['/run/hv/stats-reset-request.json']='{"scope":"nothing"}'
  m:pass()
  t.eq(R.files['/run/hv/stats-reset-request.json'],nil);t.eq(R.files['/run/hv/stats-reset-result.json'],nil)
  for i=1,12 do request(R,'quality',string.rep(string.format('%x',i%16),32));R.advance(1);m:pass() end
  t.eq(archives(R),10)
end)

t.run()
