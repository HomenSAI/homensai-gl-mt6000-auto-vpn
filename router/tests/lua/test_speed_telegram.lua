-- Plan item 7: the speed worker end to end (quiet window, CPU check, curl transfers, history, release) with fake
-- curl and fake daemons; the Lua monitor's gate, speed RPCs and Telegram delivery round with the fake runner.
-- No network: curl, /proc and the Telegram sender are fakes. The differential checks against Python are in
-- tests/test_lua_speed_telegram.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local pause=require('speed_pause')
local speed=require('speed')
local telegram=require('telegram')
local monitor=require('monitor')
local NULL=canon.null
local obj,arr=canon.object,canon.array
local TX=string.rep('a',32)
local REV=string.rep('c',32)

local function stat_line(pid,start)
  local fields={'S'};for _=1,18 do fields[#fields+1]='0' end;fields[#fields+1]=tostring(start)
  return pid..' (x) '..table.concat(fields,' ')..' 0\n'
end

-- in-memory deps of the worker; the two daemons acknowledge when the worker sleeps
local function worker_deps(options)
  options=options or {}
  local files={}
  local d={runtime='/run/hv',persist='/etc/hv',files=files,now=1761825600.5,mono=1000.0,pid=43,log_lines={},curls={},killed={}}
  function d.read(path) return files[path] end
  function d.is_link() return false end
  function d.size(path) return files[path] and #files[path] or nil end
  function d.write(path,text) files[path]=text end
  function d.remove(path) files[path]=nil end
  function d.clock() return d.mono end
  function d.wall() return d.now end
  function d.boot() return 'boot' end
  local starts={[41]=410,[42]=420,[43]=430}
  function d.stat(pid) return starts[pid] and stat_line(pid,starts[pid]) or nil end
  function d.cmdline(pid) if pid==43 then return '/usr/bin/lua\0/usr/lib/homensai-vpn/lua/speed.lua\0run\0'..TX..'\0' end end
  function d.getpid() return d.pid end
  function d.kill(pid,sig) d.killed[#d.killed+1]={pid,sig} end
  function d.sha256(text) return canon.sha256(text) end
  function d.lock(fn) return true,fn() end
  local cpu={'cpu  100 0 100 800 0 0 0 0\n','cpu  110 0 110 980 0 0 0 0\n'}
  local cpu_reads=0
  function d.cpu_text() cpu_reads=cpu_reads+1;return cpu[math.min(cpu_reads,2)] end
  function d.services()
    return obj({['homensai-vpn']=obj({instances=obj({monitor=obj({running=true,pid=42}),native=obj({running=true,pid=41})})})})
  end
  -- participants() checks the daemons' command lines: the Lua monitor and the Lua Auto supervisor
  local base_cmdline=d.cmdline
  function d.cmdline(pid)
    if pid==42 then return '/usr/bin/lua\0/usr/lib/homensai-vpn/lua/monitor.lua\0daemon\0' end
    if pid==41 then return '/usr/bin/lua\0/usr/lib/homensai-vpn/lua/auto.lua\0daemon\0' end
    return base_cmdline(pid)
  end
  function d.pair_state() return obj() end
  function d.pair_intent() return obj({mode='on',revision=REV,time=1}) end
  function d.revision() return REV end
  function d.inventory()
    return obj({profiles=arr({obj({id='wireguard:peer_1',name='Router name',protocol='wireguard',interface='wgclient1'})}),
      servers=arr({obj({profile='wireguard:peer_1',name='Vienna',channel='primary'})}),settings=obj({speed_enabled=true})})
  end
  function d.retention_days() return 7 end
  function d.day(now) return os.date('%Y-%m-%d',math.floor(now)) end
  function d.uuid() return TX end
  function d.route_binding() return {device='wgclient1',mark=4096,table='53'} end
  function d.route_get(address) return {obj({dst=address,dev=options.route_dev or 'wgclient1',table=53})} end
  function d.zero_file(size) return '/run/hv/zero-'..size end
  function d.temp_file() return '/run/hv/body-'..(#d.curls+1) end
  function d.curl_start(argv)
    local url=argv[#argv];local out
    for i,a in ipairs(argv) do if a=='-o' then out=argv[i+1] end end
    local handle={argv=argv,url=url,out=out,polls=0}
    d.curls[#d.curls+1]=handle
    return handle
  end
  function d.curl_poll(handle)
    handle.polls=handle.polls+1
    if handle.polls<2 then return nil end
    local url=handle.url
    if string.find(url,'dns.google',1,true) then
      files[handle.out]='{"Status":0,"Answer":[{"type":5,"data":"x"},{"type":1,"data":"10.0.0.1"},{"type":1,"data":"104.16.248.249"}]}'
      return {exit=0,out='200 120 0 0.050'}
    end
    if options.http and string.find(url,'__',1,true) then return {exit=0,out=options.http..' 0 0 0.010'} end
    local bytes=tonumber(string.match(url,'bytes=(%d+)'))
    if bytes then return {exit=0,out='200 '..bytes..' 0 0.0'..(bytes==0 and '2' or '5')..'0'} end
    local size=0
    for _,a in ipairs(handle.argv) do local n=string.match(a,'^@/run/hv/zero%-(%d+)$');if n then size=tonumber(n) end end
    return {exit=0,out='200 2 '..size..' 0.050'}
  end
  function d.curl_kill(handle) handle.killed=true end
  function d.curl_wait(handle) while true do local r=d.curl_poll(handle);if r then return r end end end
  function d.log(text) d.log_lines[#d.log_lines+1]=text end
  -- every sleep: 0.3 s pass; the monitor (42) and Auto (41) run their gates like their loops do
  function d.sleep(seconds)
    d.mono=d.mono+math.max(seconds,0.3);d.now=d.now+math.max(seconds,0.3)
    if options.silent then return end
    local own=d.pid
    for _,pid in ipairs({42,41}) do d.pid=pid;pause.gate(d,pid==42 and 'monitor' or 'auto',function() return true end) end
    d.pid=own
  end
  -- intents, revision, a measured traffic sample, a queued job
  files['/run/hv/auto-control-revision.json']=canon.encode(obj({revision=REV}))
  files['/run/hv/pair-auto-control.json']='{"mode":"on","revision":"'..REV..'","time":1}'
  files['/run/hv/native-status.json']=canon.encode(obj({state=options.native_state or 'OBSERVING'}))
  files['/run/hv/speed-job.json']=canon.encode(obj({profiles=arr({'wireguard:peer_1'}),budget_mib=1,duration=2,streams=2,state='QUEUED',tx=TX,
    started=canon.float(d.now),deadline=canon.float(d.now+200),monotonic_deadline=canon.float(d.mono+200),quota_reserved_bytes=1048576,
    daily_reserved_bytes=1048576,automatic=false,pid=43}))
  return d
end

local function job_of(d) return canon.decode(d.files['/run/hv/speed-job.json']) end

t.test('worker: quiet window acknowledged by the Lua daemons, measurement, history row, release',function()
  local d=worker_deps()
  speed.run(d,TX)
  local job=job_of(d)
  t.eq(job.state,'DONE');t.eq(job.code,'SPEED-COMPLETE');t.eq(job.completed,1);t.eq(job.preparation,'testing')
  t.eq(canon.number(job.cpu_percent_after_pause),10.0,'busy share of the /proc/stat delta')
  t.eq(job.live[1].phase,'done');t.truthy(#job.live[1].samples>=1,'live samples from completed requests')
  local history=canon.decode(d.files['/etc/hv/speed-history.json'])
  t.eq(history.sha256,canon.digest(history.data))
  local row=history.data.results[1]
  t.eq(row.code,NULL);t.eq(row.name,'Vienna');t.eq(row.channel,'primary');t.eq(row.endpoint,'speed.cloudflare.com')
  t.eq(row.method,'bounded-HTTPS-payload-goodput');t.eq(row.payload_budget_bytes,1048576);t.eq(row.overhead_in_budget,false)
  t.eq(canon.number(row.latency_ms),20.0,'median of the three 0-byte requests')
  t.eq(row.download.payload_bytes,786432);t.eq(row.upload.payload_bytes,262144)
  t.truthy(canon.is_float(row.download.mbps) and canon.is_float(row.download.seconds))
  local pause_row=canon.decode(d.files['/run/hv/speed-pause.json'])
  t.eq(pause_row.phase,'RESUMING','released: the monitor resumes first, Auto waits for its post-test pass')
  t.eq(pause_row.owners.monitor.pid,42);t.eq(pause_row.owners.auto.pid,41)
  -- every transfer was bound to the tunnel device and the fixed address
  for _,h in ipairs(d.curls) do
    local joined=table.concat(h.argv,' ')
    t.truthy(string.find(joined,'--interface wgclient1',1,true),joined)
    if string.find(h.url,'^https://speed%.cloudflare%.com/') then t.truthy(string.find(joined,'speed.cloudflare.com:443:104.16.248.249',1,true),joined) end
  end
end)

t.test('worker: no acknowledgement -> SPEED-PAUSE-TIMEOUT, nothing measured, the pause withdrawn',function()
  local d=worker_deps({silent=true})
  speed.run(d,TX)
  local job=job_of(d)
  t.eq(job.state,'FAILED');t.eq(job.code,'SPEED-PAUSE-TIMEOUT');t.eq(#d.curls,0)
  t.eq(d.files['/etc/hv/speed-history.json'],nil)
  t.eq(canon.decode(d.files['/run/hv/speed-pause.json']).phase,'RESUMING')
end)

t.test('worker: a switch in progress refuses the window; HTTP and route failures give the Python codes',function()
  local d=worker_deps({native_state='APPLYING'})
  speed.run(d,TX)
  t.eq(job_of(d).code,'SPEED-SWITCH-IN-PROGRESS');t.eq(d.files['/run/hv/speed-pause.json'],nil)
  d=worker_deps({http='503'})
  speed.run(d,TX)
  local row=canon.decode(d.files['/etc/hv/speed-history.json']).data.results[1]
  t.eq(row.code,'SPEED-HTTP');t.eq(job_of(d).state,'DONE')
  d=worker_deps({route_dev='eth0'})
  speed.run(d,TX)
  t.eq(canon.decode(d.files['/etc/hv/speed-history.json']).data.results[1].code,'SPEED-ROUTE-UNVERIFIED')
end)

t.test('worker: a cancel request ends the test as CANCELLED',function()
  local d=worker_deps()
  local sleep=d.sleep
  local n=0
  function d.sleep(s) sleep(s);n=n+1;if n==4 then d.files['/run/hv/speed-cancel.json']=canon.encode(obj({tx=TX,time=1})) end end
  speed.run(d,TX)
  local job=job_of(d)
  t.eq(job.state,'CANCELLED');t.eq(job.code,'SPEED-CANCELLED')
end)

t.test('stage: an elapsed window keeps only completed payloads; a failure stops the other transfers',function()
  local d=worker_deps({silent=true})
  local binding={device='wgclient1',mark=4096,table='53'}
  local value=speed.stage(d,binding,'104.16.248.249','download',3*1048576,2,2,function() return false end)
  t.eq(value.payload_bytes,3*1048576)
  d=worker_deps({silent=true,http='500'})
  local err=t.raises(speed.stage,d,binding,'104.16.248.249','download',3*1048576,2,2,function() return false end)
  t.eq(err.code,'SPEED-HTTP')
  t.eq(speed.is_global('100.64.1.1'),false);t.eq(speed.is_global('1.1.1.1'),true);t.eq(speed.is_global('01.1.1.1'),nil)
end)

t.test('curl command lines: device-bound, fixed address, no shell data, token never on a command line',function()
  local d=speed.router({io=t.fake_runner(),runtime='/run/hv',persist='/etc/hv'})
  local argv=speed.curl_argv(d,{device='wgclient1'},{host='speed.cloudflare.com',address='104.16.248.249',path='/__down?bytes=1024',method='GET',amount=1024,seconds=2.5,max=1024})
  local joined=table.concat(argv,' ')
  t.truthy(string.find(joined,'--interface wgclient1 --resolve speed.cloudflare.com:443:104.16.248.249',1,true))
  t.eq(argv[#argv],'https://speed.cloudflare.com/__down?bytes=1024')
  t.truthy(t.raises(speed.quote,"a'b"))
  -- the Telegram sender: URL with the token only in the 0600 curl config file
  local written,ran={},nil
  local td=telegram.router({io=t.fake_runner(),runtime='/run/hv',persist='/etc/hv',overrides={
    write_private=function(path,text) written[path]=text end,
    exec_curl=function(argv,output) ran=argv;written[output]='200';return 0 end,
    read=function(path) if string.find(path,'%.body$') then return '{"ok":true}' end;return written[path] end,
    remove=function(path) written[path]=nil end}})
  telegram.send_message(td,{telegram_token='123:synthetic',telegram_chat='-100'},'hello')
  local line=table.concat(ran,' ')
  t.truthy(not string.find(line,'synthetic',1,true),'token not in argv')
  t.truthy(string.find(line,'-K ',1,true))
  t.eq(next(written),nil,'config, payload, body and code files removed')
  local err=t.raises(telegram.send_message,td,{telegram_token='bad',telegram_chat='-100'},'x')
  t.eq(err.code,'TELEGRAM-CONFIG')
end)

------------------------------------------------------------------------------------------------------
-- the monitor
------------------------------------------------------------------------------------------------------
local function put(R,path,value) R.files[path]=canon.encode(value) end
local function speed_inventory()
  local data=t.inventory()
  data.settings.speed_enabled=true;data.settings.speed_auto_new=false;data.settings.telegram_enabled=true
  return data
end
local proc={stat=function(pid) return stat_line(pid,pid*10) end,getpid=function() return 42 end,boot=function() return 'boot' end,
  is_link=function() return false end,spawn_worker=function() return 777 end,
  cmdline=function(pid) if pid==777 then return '/usr/bin/lua\0/usr/lib/homensai-vpn/lua/speed.lua\0run\0'..string.rep('d',32)..'\0' end end,
  uuid=function() return string.rep('d',32) end}

t.test('monitor: traffic sample, speed_start/live/cancel answered in Lua, FALLBACK when the lock is busy',function()
  local R=t.fake_runner({inventory=speed_inventory()})
  local m=monitor.new(R,{speed_overrides=proc,telegram_run=function() end})
  m:pass()
  local traffic=canon.decode(R.files['/run/hv/speed-traffic.json'])
  t.eq(traffic.scope,'wan');t.eq(traffic.counters.eth0,17000);t.eq(traffic.rate_bps,NULL,'first sample: no rate yet')
  R.advance(10);R.counters.eth0.rx=R.counters.eth0.rx+1000
  m:pass()
  t.eq(canon.number(canon.decode(R.files['/run/hv/speed-traffic.json']).rate_bps),800.0)
  local reply=m.rpc.handle('speed_start','{"profiles":["wireguard:peer_7"],"budget_mib":8,"duration":5,"streams":2}')
  t.eq(reply.accepted,true);t.eq(reply.run_id,string.rep('d',32));t.eq(reply.payload_budget_bytes,8*1048576)
  local job=canon.decode(R.files['/run/hv/speed-job.json'])
  t.eq(job.state,'QUEUED');t.eq(job.pid,777)
  t.eq(m.rpc.handle('speed_start','{"profiles":["wireguard:peer_7"],"budget_mib":8,"duration":5,"streams":2}').code,'SPEED-BUSY')
  t.eq(m.rpc.handle('speed_live','{}').state,'QUEUED')
  t.eq(m.rpc.handle('speed_live','{"x":1}').error,'RPC-UNEXPECTED-ARGS')
  t.eq(m.rpc.handle('speed_cancel','{}'),{queued=true})
  t.eq(canon.decode(R.files['/run/hv/speed-cancel.json']).tx,string.rep('d',32))
  R.locked['auto-control.lock']=true
  t.truthy(m.rpc.handle('speed_cancel','{}')==require('rpc').FALLBACK,'lock busy: agent.py answers')
  R.locked['auto-control.lock']=nil
  local status=m.rpc.handle('status','{}')
  t.eq(status.speed_tests.state,'QUEUED');t.eq(status.speed_tests.live.state,'QUEUED');t.eq(status.speed_pause,{active=false})
  t.truthy(m.rpc.handle('telegram_test','{}')==require('rpc').FALLBACK,'the delivery test is the dispatcher\'s Lua CLI')
end)

t.test('monitor: the quiet-window gate acknowledges only between passes and with no echo in flight',function()
  local R=t.fake_runner({inventory=speed_inventory()})
  local m=monitor.new(R,{speed_overrides=proc,telegram_run=function() end})
  m:pass()
  local intents=obj();for _,name in ipairs(pause.INTENTS) do intents[name]=NULL end
  put(R,'/run/hv/auto-control-revision.json',obj({revision=REV}))
  local row=obj({schema=1,tx=TX,boot='boot',worker=obj({pid=777,start=7770}),owners=obj({monitor=obj({pid=42,start=420})}),acks=obj(),
    revision=REV,intents=intents,phase='PAUSING',deadline=canon.float(R.mono+60),auto_was_on=false})
  put(R,'/run/hv/speed-pause.json',row)
  m.passing=true
  t.eq(m:speed_gate(),true);t.eq(next(canon.decode(R.files['/run/hv/speed-pause.json']).acks),nil,'a pass in flight: no ack')
  m.passing=false;m.ping.inflight=1
  t.eq(m:speed_gate(),true);t.eq(next(canon.decode(R.files['/run/hv/speed-pause.json']).acks),nil,'an echo in flight: no ack')
  m.ping.inflight=0
  t.eq(m:speed_gate(),true)
  local acked=canon.decode(R.files['/run/hv/speed-pause.json'])
  t.eq(acked.acks.monitor.owner,obj({pid=42,start=420}));t.eq(canon.number(acked.acks.monitor.time),R.mono)
  t.eq(m:speed_pause().monitor_paused,true)
  R.files['/run/hv/pair-auto-control.json']='{"mode":"off"}'
  t.eq(m:speed_gate(),false,'a new owner command supersedes the window')
  t.eq(canon.decode(R.files['/run/hv/speed-cancel.json']).tx,TX)
end)

t.test('monitor: Telegram round in a child, state saved by the child, result applied next pass',function()
  local R=t.fake_runner({inventory=speed_inventory()})
  local sent={}
  local runs,jobs=0,{}
  local function child(job,done)
    runs=runs+1;jobs[#jobs+1]=job
    local d=telegram.router({io=R,runtime='/run/hv',persist='/etc/hv',lock=function(fn) return true,fn() end,
      config=function() return {telegram_enabled='1',telegram_token='1:synthetic',telegram_chat='-100',telegram_interval='60'} end,
      send=function(_,text) sent[#sent+1]=text end,overrides={is_link=function() return false end}})
    t.eq(telegram.deliver_files(d,job.input,job.output),true,'the child command of the monitor')
    t.eq(telegram.deliver_files(d,'/tmp/x.in.json',job.output),false,'only the job files of the monitor')
    done()
  end
  local m=monitor.new(R,{speed_overrides=proc,telegram_run=child})
  local status=m:pass()
  t.eq(runs,1);t.eq(status.telegram,{enabled=true})
  t.eq(#sent,1);t.truthy(string.find(sent[1],'^Report id: interval:%d+\nHomenSAI Auto VPN · monitoring'),sent[1])
  t.truthy(string.find(sent[1],'Primary channel · Main · wireguard · OK',1,true),sent[1])
  local saved=canon.decode(R.files['/etc/hv/telegram-state.json'])
  t.eq(saved.sha256,canon.digest(saved.data));t.eq(saved.data.last_code,'TELEGRAM-DELIVERED')
  R.advance(10)
  status=m:pass()
  t.eq(status.telegram.enabled,true);t.eq(status.telegram.interval_minutes,60);t.eq(status.telegram.uncertain_reports,0)
  t.eq(runs,2,'the next round started; not due: nothing sent');t.eq(#sent,1)
  t.eq(R.files[jobs[1].input],nil);t.eq(R.files[jobs[1].output],nil,'the files of the collected round are removed')
end)

t.run()
