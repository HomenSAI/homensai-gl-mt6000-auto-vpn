-- The separate Lua monitor process under a fake event loop whose callbacks run like libubox-lua's: lua_call, no
-- protection, so an error in one ends uloop.run(). 2.1.0-alpha8: one such end in the soak (monitor.lua:1604, text lost),
-- about 37-40 s without decisions. Real here: monitor.run/start, start_pass, the guards, the record. Fake: uloop, ubus,
-- the runner. The router-only file record: lua-monitor-crashes.json (loop_guard.lua).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon

------------------------------------------------------------------------------------------------------
-- fake loop
------------------------------------------------------------------------------------------------------
local L
local fake={ULOOP_READ=1}
function fake.init() end
function fake.cancel() L.cancelled=true end
function fake.timer(fn,ms)
  local entry={fn=fn}
  L.timers[entry]=true
  local object={}
  function object:set(delay)
    if L.frozen and L.frozen(entry) then return end
    entry.at=L.clock+delay
    L.sets[#L.sets+1]=delay
  end
  function object:cancel() entry.at=nil end
  if ms then object:set(ms) end
  return object
end
function fake.process(path,args,env,fn) L.children[#L.children+1]={path=path,fn=fn};return {pid=function() return 4242 end} end
function fake.fd_add(fd,fn,flags)
  local entry={fd=fd,fn=fn}
  L.fds[#L.fds+1]=entry
  return {delete=function() entry.deleted=true end}
end
local function next_timer()
  local best
  for entry in pairs(L.timers) do if entry.at and (not best or entry.at<best.at) then best=entry end end
  return best
end
-- run(R, seconds): the C loop: every callback unprotected. An error leaves it, as it leaves uloop.run() on the router.
local function run_loop(R,seconds)
  local limit=L.clock+seconds*1000
  while not L.cancelled do
    if #R.queue>0 then
      -- a deferred answer of the fake runner is a callback of the loop too: through the uloop the process installed
      local timer=require('uloop').timer(table.remove(R.queue,1))
      timer:set(0)
    else
      local entry=next_timer()
      if not entry or entry.at>limit then
        R.advance((limit-L.clock)/1000);L.clock=limit
        return
      end
      if entry.at>L.clock then R.advance((entry.at-L.clock)/1000);L.clock=entry.at end
      entry.at=nil
      L.fired=L.fired+1
      entry.fn()
    end
  end
end
fake.run=function() L.body() end
package.preload['uloop']=function() return fake end
local conn={}
function conn:add(object) L.object=object end
function conn:close() L.closed=true end
function conn:reply(req,value)
  if type(value)~='table' then error("bad argument #2 to 'reply' (table expected, got "..type(value)..')',2) end
  L.replies[#L.replies+1]=value
end
package.preload['ubus']=function() return {STRING=3,connect=function() return conn end} end

local monitor=require('monitor')
local guard=require('loop_guard')
local real_uloop=fake

local function fresh_loop() L={timers={},children={},fds={},replies={},sets={},clock=0,fired=0} end
local function runner()
  local R=t.fake_runner({})
  R.inventory_data.settings.interval=10
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  R.deferred=true
  function R.live_count() return 0 end
  -- as monitor_io.after: the loop's timer (the guarded one when run() installed it)
  function R.after(ms,fn)
    local timer=require('uloop').timer(fn)
    timer:set(math.max(1,math.floor(ms)))
    return {cancel=function() timer:cancel() end}
  end
  function R.spawn(argv,seconds,cb) R.queue[#R.queue+1]=function() cb(1,nil) end end
  return R
end
-- monitor.run under the fake loop: body(R) runs as uloop.run(); -> exit code (nil = the process went on). monitor.run catches
-- whatever leaves uloop.run(), so a failed assertion in the body would only look like a crash: it is handed to the test
-- here. crash=true: the body is meant to raise, as a callback error leaves the C loop.
local function daemon(R,body,crash)
  fresh_loop()
  package.loaded['uloop']=real_uloop
  local failure
  L.body=crash and function() body(R) end or function()
    local ok,err=xpcall(function() body(R) end,debug.traceback)
    if not ok then failure=err end
  end
  local code
  local exit=os.exit
  os.exit=function(c) code=c end
  local ok,err=pcall(monitor.run,R)
  os.exit=exit
  package.loaded['uloop']=real_uloop
  if not ok then error(err,0) end
  if failure then error(failure,0) end
  return code
end
local function record(R) return canon.decode(R.files['/run/hv/'..guard.RECORD]) end
local function has_log(R,pattern)
  for _,line in ipairs(R.logs) do if string.find(line,pattern,1,true) then return true end end
  return false
end
local function flash_writes(R)
  local out={}
  for _,path in ipairs(R.writes) do if string.sub(path,1,8)~='/run/hv/' then out[#out+1]=path end end
  return out
end
local function published(R) return canon.decode(R.files['/run/hv/status.json']) end
local function published_at(R) return canon.number(published(R).time) end

------------------------------------------------------------------------------------------------------
-- the guards
------------------------------------------------------------------------------------------------------
t.test('a failing timer, child or socket callback is reported with its stack; arguments reach the callback',function()
  local made={}
  local real={timer=function(fn) made[#made+1]=fn;return {} end,process=function(p,a,e,fn) made[#made+1]=fn;return {} end,
    fd_add=function(fd,fn) made[#made+1]=fn;return {} end,ULOOP_READ=1}
  local reports={}
  local U=guard.uloop(real,function(where,err) reports[#reports+1]={where,err} end)
  local seen
  U.timer(function(...) seen={...};local x=nil;return x.field end)
  U.process('/bin/true',{},{},function() error({code='SOME-REFUSAL',secret='hidden'}) end)
  U.fd_add(3,function() error('fd failed') end,1)
  made[1]('a',nil,3);made[2](7);made[3]()
  t.eq(seen[1],'a');t.eq(seen[3],3)
  t.eq(#reports,3)
  t.eq(reports[1][1],'timer');t.truthy(string.find(reports[1][2],'stack traceback',1,true),reports[1][2])
  t.truthy(string.find(reports[1][2],"index local 'x'",1,true),reports[1][2])
  t.eq(reports[2][1],'process');t.truthy(string.find(reports[2][2],'code SOME-REFUSAL',1,true))
  t.truthy(not string.find(reports[2][2],'hidden',1,true),'a refusal gives its code, never its fields')
  t.eq(reports[3][1],'fd');t.eq(U.ULOOP_READ,1)
end)

t.test('every ubus method of the monitor is guarded: a failing method answers fallback, the object lives on',function()
  local R=runner()
  local code=daemon(R,function(R)
    local methods=L.object[require('rpc').OBJECT]
    local real_handle=monitor
    methods.status[1]({},canon.object())  -- a healthy call
    local before=#L.replies
    local reply=conn.reply
    conn.reply=function(self,req,value) if not value.fallback then error('reply failed') end;return reply(self,req,value) end
    methods.status[1]({},canon.object())
    conn.reply=reply
    t.eq(#L.replies,before+1);t.eq(L.replies[#L.replies],{fallback=true})
    methods.status[1]({},canon.object())
    t.eq(#L.replies,before+2)
  end)
  t.eq(code,nil,'the process goes on')
  t.eq(record(R).errors[1].where,'ubus status')
end)

------------------------------------------------------------------------------------------------------
-- the end of the loop: the crash record
------------------------------------------------------------------------------------------------------
t.test('an error out of uloop.run: full stack in the RAM record, exit 1, nothing written to flash',function()
  local R=runner()
  local function failing_callback() local value=nil;return value.field end
  local code=daemon(R,function() R.writes={};failing_callback() end,true)
  t.eq(code,1,'procd restarts it')
  local row=record(R).errors[1]
  t.eq(row.fatal,true);t.eq(row.where,'monitor');t.eq(canon.number(row.count),1)
  t.truthy(string.find(row.text,'stack traceback',1,true),row.text)
  t.truthy(string.find(row.text,'failing_callback',1,true),'the real place, not the main chunk: '..row.text)
  t.truthy(string.find(row.text,"index local 'value'",1,true),'the real error text')
  t.truthy(has_log(R,'MONITOR-LOOP-FATAL'))
  t.eq(flash_writes(R),{},'a crash loop must not wear the flash')
  t.eq(L.closed,true);t.eq(R.files['/run/hv/lua-monitor.ready'],R.files['/run/hv/lua-monitor.ready'])
end)

t.test('a failing start is recorded the same way',function()
  local R=runner()
  R.config_mtime=function() error('config read failed') end
  local code=daemon(R,function() error('never reached') end,true)
  t.eq(code,1)
  t.truthy(string.find(record(R).errors[1].text,'config read failed',1,true))
end)

t.test('a clean end of the loop (procd SIGTERM) writes no record and no exit code',function()
  local R=runner()
  t.eq(daemon(R,function() end),nil)
  t.eq(R.files['/run/hv/'..guard.RECORD],nil)
end)

t.test('the record survives a restart, is shown in status.json, and only then',function()
  local R=runner()
  daemon(R,function() error('first process died') end,true)
  local code=daemon(R,function(R) run_loop(R,1) end)
  t.eq(code,nil)
  local shown=published(R).monitor_loop
  t.eq(shown.errors,1);t.eq(shown.fatal,true);t.eq(shown.last_where,'monitor')
  t.truthy(string.find(shown.last_error,'first process died',1,true))
  t.eq(string.find(shown.last_error,'traceback',1,true),nil,'the stack stays in the record')
  local clean=runner()
  daemon(clean,function(R) run_loop(R,1) end)
  t.eq(published(clean).monitor_loop,nil,'a healthy status keeps its keys')
end)

------------------------------------------------------------------------------------------------------
-- a failing callback: logged, the loop goes on, it does not spin
------------------------------------------------------------------------------------------------------
t.test('an error in a pass callback (the a8 trigger class) ends nothing: logged once, the next pass comes',function()
  local R=runner()
  local failed=0
  local https=R.https_get
  R.https_get=function(...)
    if failed==0 then failed=1;local bad=nil;return bad.answer end  -- pcall(probe.probe): SYSTEM-001 for this profile
    return https(...)
  end
  local spawn=R.spawn
  local armed
  R.spawn=function(argv,seconds,cb)
    R.queue[#R.queue+1]=function()
      if not armed then armed=true;error('child exit callback failed') end
      cb(1,nil)
    end
  end
  local code=daemon(R,function(R)
    local U=require('uloop')
    U.timer(function() error('timer callback failed') end,50)
    run_loop(R,120)
  end)
  t.eq(code,nil,'the process lives')
  t.truthy(published_at(R)>R.now-40,'status stays fresh after the error')
  t.truthy(has_log(R,'timer callback failed'));t.truthy(has_log(R,'child exit callback failed'))
  local wheres={}
  for _,row in ipairs(record(R).errors) do wheres[row.where]=true;t.eq(row.fatal,nil) end
  t.eq(wheres.timer,true)
end)

t.test('the same error for ever: one line and one write a minute, never a line per callback, the loop not busier',function()
  local R=runner()
  local beats=0
  daemon(R,function(R)
    local U=require('uloop')
    local timer
    timer=U.timer(function() timer:set(1000);beats=beats+1;error('always broken') end,1000)
    run_loop(R,600)
  end)
  t.truthy(beats>=590,'it kept firing: '..beats)
  local lines=0
  for _,line in ipairs(R.logs) do if string.find(line,'always broken',1,true) then lines=lines+1 end end
  t.truthy(lines>=9 and lines<=11,'a line per minute: '..lines)
  t.eq(canon.number(record(R).errors[1].count)>=9,true)
end)

t.test('a lost probe callback leaves the pass to the 60 s watchdog; the watchdog is not hidden and the next pass comes',function()
  local R=runner()
  local lost=true
  local https=R.https_get
  R.https_get=function(...) if lost then return end;return https(...) end
  local at
  daemon(R,function(R)
    run_loop(R,59)
    t.eq(has_log(R,'pass watchdog'),false)
    lost=false
    run_loop(R,3)
    t.truthy(has_log(R,'pass watchdog: probes did not finish in 60 s'),'the pass ended at its watchdog')
    at=published_at(R)
    run_loop(R,30)
  end)
  t.truthy(published_at(R)>at,'the next pass came')
  t.eq(has_log(R,'MONITOR-PASS-STUCK'),false)
end)

t.test('a failure while the next delay is computed: the next pass comes after TICK_RETRY: neither a spin nor a lost tick',function()
  local R=runner()
  local stamps={}
  local write=R.write_atomic
  R.write_atomic=function(path,text)
    if path=='/run/hv/status.json' then stamps[#stamps+1]=R.mono end
    return write(path,text)
  end
  daemon(R,function(R)
    run_loop(R,3)
    stamps={};L.sets={}
    local real=R.config_mtime
    R.config_mtime=function() error('stat failed') end
    run_loop(R,35)
    t.truthy(#stamps>=2 and #stamps<=4,'one pass per TICK_RETRY: '..#stamps)
    -- the next pass is armed for exactly TICK_RETRY: the phases of a pass must not be what hides a spin
    local retries,instant=0,0
    for _,delay in ipairs(L.sets) do
      if delay==monitor.TICK_RETRY*1000 then retries=retries+1 elseif delay==1 then instant=instant+1 end
    end
    t.truthy(retries>=2,'armed for TICK_RETRY: '..retries);t.eq(instant,0,'never at once')
    for index=2,#stamps do
      local gap=stamps[index]-stamps[index-1]
      t.truthy(gap>=monitor.TICK_RETRY-0.001 and gap<monitor.TICK_RETRY+monitor.TICK_OVERDUE,'the pass came on its own timer, not by the watcher: '..gap)
    end
    R.config_mtime=real
    run_loop(R,20)
  end)
  t.eq(has_log(R,'MONITOR-TICK-REARMED'),false,'the tick was armed by the pass, the backstop stayed idle')
  t.truthy(published_at(R)>R.now-25,'the passes go on')
end)

------------------------------------------------------------------------------------------------------
-- start_pass: passing=true never outlives a failure
------------------------------------------------------------------------------------------------------
local function start_only()
  local R=t.fake_runner({})
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  return R,monitor.new(R)
end
for _,spec in ipairs({
  {'the diagnosing check',function(R,m) local a=require('accounting');local real=a.stats.diagnostic
    a.stats.diagnostic=function() a.stats.diagnostic=real;error('diagnostic check failed') end end},
  {'the ping history reload',function(R,m) m.diagnosing=not require('accounting').stats.diagnostic(R,R.wall())
    local real=m.load_ping_history;m.load_ping_history=function() m.load_ping_history=real;error('history failed') end end},
  {'the clock',function(R,m) local real=R.clock;R.clock=function() R.clock=real;error('clock failed') end end},
  {'the wall clock',function(R,m) local real=R.wall;R.wall=function() R.wall=real;error('wall failed') end end},
}) do
  t.test('start_pass: '..spec[1]..' fails: the pass ends as a failed pass and the next one runs',function()
    local R,m=start_only()
    spec[2](R,m)
    local done=0
    t.eq(m:start_pass(function() done=done+1 end),true)
    t.eq(m.passing,false,'passes would have stopped for ever')
    t.eq(done,1,'the caller re-arms from done')
    t.eq(published(R).error,'SYSTEM-001')
    t.eq(m:start_pass(function() done=done+1 end),true)
    t.eq(done,2);t.eq(published(R).error,nil)
  end)
end

t.test('finish: publishing the failure itself fails (log, disk): the pass still ends',function()
  local R,m=start_only()
  R.command=function() error('inventory failed') end
  R.log=function() error('log failed') end
  R.write_atomic=function() error('disk full') end
  local done=0
  m:start_pass(function() done=1 end)
  t.eq(m.passing,false);t.eq(done,1)
end)

t.test('the pass watchdog itself fails: the pass still ends',function()
  local R,m=start_only()
  local timers={}
  R.after=function(ms,fn) timers[#timers+1]={ms,fn};return {cancel=function() end} end
  R.https_get=function() end
  R.live_count=function() error('count failed') end
  local done=0
  m:start_pass(function() done=done+1 end)
  t.eq(m.passing,true)
  for _,timer in ipairs(timers) do if timer[1]==monitor.PASS_WATCHDOG*1000 then timer[2]() end end
  t.eq(m.passing,false);t.eq(done,1)
  t.eq(published(R).error,'SYSTEM-001')
end)

------------------------------------------------------------------------------------------------------
-- a dead monitor is not hidden behind a live loop
------------------------------------------------------------------------------------------------------
t.test('loop_check: a pass over its watchdog, a tick over its time; one long blocked callback is not dead',function()
  local R,m=start_only()
  m.passing=true;m.pass_started=100
  t.eq(m:loop_check(100+monitor.PASS_OVERDUE),nil,'exactly at the limit')
  for i=1,monitor.OVERDUE_BEATS-1 do t.eq(m:loop_check(200+i),nil,'beat '..i) end
  m.passing=false;m.tick_due=1000
  t.eq(m:loop_check(1001),nil,'the watchdog fired in the meantime: the count starts again')
  m.passing=true
  for i=1,monitor.OVERDUE_BEATS-1 do t.eq(m:loop_check(2000+i),nil) end
  t.eq(m:loop_check(2100),'pass')
  m.passing=false
  m.tick_due=3000
  t.eq(m:loop_check(3000+monitor.TICK_OVERDUE),nil)
  for i=1,monitor.OVERDUE_BEATS-1 do t.eq(m:loop_check(3016+i),nil) end
  t.eq(m:loop_check(3030),'tick')
end)

t.test('a stuck pass ends the process with a record; procd restarts it (the loop itself still ran)',function()
  local R=runner()
  local code=daemon(R,function(R)
    run_loop(R,20)
    -- what a lost finish would look like: the pass runs, nothing will ever end it
    R.https_get=function() end
    R.spawn=function() end
    R.after=function() return {cancel=function() end} end  -- the pass watchdog never arms
    run_loop(R,200)
  end)
  t.eq(code,1)
  t.eq(L.cancelled,true,'uloop.cancel: run() returns, the object goes')
  t.truthy(string.find(record(R).errors[#record(R).errors].text,'MONITOR-PASS-STUCK',1,true))
  t.eq(record(R).errors[#record(R).errors].fatal,true)
end)

t.test('a lost next pass is armed again; passes go on, the process lives',function()
  local R=runner()
  local lost=false
  local code=daemon(R,function(R)
    run_loop(R,12)
    -- the armed timer is cancelled behind the monitor's back (as an unreferenced libubox-lua object would be)
    for entry in pairs(L.timers) do if entry.at and entry.at-L.clock>1500 then entry.at=nil;lost=true end end
    run_loop(R,60)
  end)
  t.eq(lost,true);t.eq(code,nil)
  t.truthy(has_log(R,'MONITOR-TICK-REARMED'))
  t.truthy(published_at(R)>R.now-25,'the passes came back')
end)

t.test('a tick that cannot be armed at all: re-armed three times, then the process ends with a record',function()
  local R=runner()
  local code=daemon(R,function(R)
    run_loop(R,12)
    local main
    for entry in pairs(L.timers) do if entry.at and entry.at-L.clock>1500 then main=entry;entry.at=nil end end
    L.frozen=function(entry) return entry==main end
    run_loop(R,200)
  end)
  t.eq(code,1)
  t.truthy(string.find(record(R).errors[#record(R).errors].text,'MONITOR-TICK-LOST',1,true))
end)

t.test('a speed test quiet window is not a dead monitor: the tick keeps coming, nothing is overdue',function()
  local R=runner()
  local code=daemon(R,function(R)
    run_loop(R,12)
    R.files['/run/hv/speed-pause.json']=canon.encode(canon.object({state='running'}))
    local gate=getmetatable(monitor.new(runner())).__index
    local real=gate.speed_gate
    gate.speed_gate=function() return true end
    run_loop(R,400)
    gate.speed_gate=real
    R.files['/run/hv/speed-pause.json']=nil
    run_loop(R,12)
  end)
  t.eq(code,nil);t.eq(has_log(R,'MONITOR-TICK'),false)
  t.truthy(published_at(R)>R.now-25,'the passes came back after the window')
  local _,m=start_only()
  t.eq(m:loop_check(1e9),nil,'not armed yet')
end)

------------------------------------------------------------------------------------------------------
-- the record
------------------------------------------------------------------------------------------------------
local function recorder(fs)
  fs=fs or {files={},writes=0,logs={},now=1000,mono=10}
  fs.rec=guard.recorder({path='/run/hv/record.json',read=function(p) return fs.files[p] end,
    write=function(p,text) fs.writes=fs.writes+1;fs.files[p]=text end,wall=function() return fs.now end,clock=function() return fs.mono end,
    log=function(text) fs.logs[#fs.logs+1]=text end})
  return fs
end
t.test('recorder: bounded in rows, in text and in writes; a broken file, disk or log never raises',function()
  local fs=recorder()
  for i=1,3*guard.KEEP do fs.mono=fs.mono+1;fs.rec.report('timer','error number '..i..'\nstack traceback:\n\t'..string.rep('x',5000)) end
  local value=canon.decode(fs.files['/run/hv/record.json'])
  t.eq(#value.errors,guard.KEEP)
  t.truthy(string.find(value.errors[#value.errors].text,'error number '..3*guard.KEEP,1,true),'the newest last')
  for _,row in ipairs(value.errors) do t.truthy(#row.text<=guard.TEXT_LIMIT) end
  t.truthy(#fs.files['/run/hv/record.json']<guard.KEEP*(guard.TEXT_LIMIT+400))
  local writes=fs.writes
  for i=1,1000 do fs.rec.report('timer','error number 15') end
  t.eq(fs.writes,writes,'the same error within a minute writes nothing')
  fs.mono=fs.mono+guard.LOG_EVERY
  fs.rec.report('timer','error number 15')
  t.eq(fs.writes,writes+1)
  t.eq(canon.number(canon.decode(fs.files['/run/hv/record.json']).errors[guard.KEEP].count),1002)
  fs.rec.fatal('timer','error number 15');t.eq(fs.writes,writes+2,'the end of the process is always written')
  local again=recorder({files={['/run/hv/record.json']='not json'},writes=0,logs={},now=1,mono=1})
  again.rec.report('fd','x')
  t.eq(#canon.decode(again.files['/run/hv/record.json']).errors,1)
  local broken=guard.recorder({path='/x',read=function() error('r') end,write=function() error('w') end,
    wall=function() error('t') end,clock=function() error('c') end,log=function() error('l') end})
  broken.report('timer','x');broken.fatal('timer','x');t.eq(broken.summary(),nil)
end)

t.test('secrets never reach the record, the log or the status',function()
  local secrets={'aGVsbG8gd29ybGQgdGhpcyBpcyBhIHdnIGtleSAxMjM0NTY=','123456789:'..string.rep('AAExampleToken',3),'hunter2hunter2',
    'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef','s3cr3tPassw0rdValue','ZXhhbXBsZS1iZWFyZXItdG9rZW4tdmFsdWUtMTIz','93.184.216.34'}
  local text='monitor.lua:12: option private_key \''..secrets[1]..'\' token '..secrets[2]..' password='..secrets[3]..
    ' sha '..secrets[4]..' {"psk":"'..secrets[5]..'"} Authorization: Bearer '..secrets[6]..' endpoint '..secrets[7]..':51820\nstack traceback:\n\tmonitor.lua:12: in function \'x\''
  local fs=recorder()
  fs.rec.report('timer',text)
  local stored=fs.files['/run/hv/record.json']..table.concat(fs.logs,'\n')..canon.encode(fs.rec.summary())
  for _,secret in ipairs(secrets) do t.eq(string.find(stored,secret,1,true),nil,secret) end
  t.truthy(string.find(stored,'monitor.lua:12',1,true),'the place stays')
end)

t.test('the mask runs first: a multi-line dump keeps its line rules, a cut never leaves the start of a secret',function()
  local key='aGVsbG8gd29ybGQgdGhpcyBpcyBhIHdnIGtleSAxMjM0NTY='
  local dump="config dump failed\n  option private_key 'hunter2hunter2'\n\tlist password 's3cr3tPassw0rdValue'\nvpn.peer.preshared_key='fakepresharedvalue'\nnext line"
  local text=guard.clean(dump)
  for _,secret in ipairs({'hunter2hunter2','s3cr3tPassw0rdValue','fakepresharedvalue'}) do t.eq(string.find(text,secret,1,true),nil,secret) end
  t.eq(string.find(text,'\n',1,true),nil,'one line')
  t.truthy(string.find(text,'config dump failed',1,true));t.truthy(string.find(text,'next line',1,true))
  -- every position of a secret across the cut: no start of it survives, whole or partial
  for offset=-50,5 do
    local pad=string.rep('x ',math.floor((guard.MESSAGE_LIMIT+offset)/2))
    for _,secret in ipairs({key,'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'}) do
      local cleaned=guard.clean(pad..secret)
      t.truthy(#cleaned<=guard.MESSAGE_LIMIT,'cut after the mask')
      t.eq(string.find(cleaned,string.sub(secret,1,6),1,true),nil,'offset '..offset)
    end
  end
  local fs=recorder()
  fs.rec.report('timer',dump..'\nstack traceback:\n\tmonitor.lua:12: in function \'x\'')
  t.eq(string.find(fs.files['/run/hv/record.json']..table.concat(fs.logs,'\n'),'hunter2hunter2',1,true),nil)
end)

t.test('forged traceback markers and dynamic chunk names cannot bypass token masking',function()
  local secret=string.rep('q',48) -- synthetic unlabeled token
  for _,text in ipairs({
    'callback failed\nstack traceback:\n'..secret,
    'callback failed\nstack traceback:\n\t[string "'..secret..'"]:1: in main chunk',
    'callback failed\nstack traceback:\n\tmonitor.lua:12: in function x\n'..secret,
  }) do
    local fs=recorder()
    fs.rec.report('timer',text)
    local stored=fs.files['/run/hv/record.json']..table.concat(fs.logs,'\n')..canon.encode(fs.rec.summary())
    t.eq(string.find(stored,secret,1,true),nil,'no token in record, log or status')
  end
  local text=guard.clean('callback failed\nstack traceback:\n\tmonitor.lua:12: in function x')
  t.truthy(string.find(text,'monitor.lua:12',1,true),'ordinary frame remains useful')
end)

t.test('without the masking rules the message is withheld, never written as it is',function()
  local real=package.loaded['diag_bundle']
  local preload=package.preload['diag_bundle']
  package.loaded['diag_bundle']=nil
  package.preload['diag_bundle']=function() error('damaged module') end
  local text=guard.clean('password=hunter2 failed\nstack traceback:\n\tmonitor.lua:12: in function')
  package.preload['diag_bundle']=preload
  package.loaded['diag_bundle']=real
  t.eq(text,guard.WITHHELD)
end)

t.test('the diagnostic bundle collects the record',function()
  local found=false
  for _,item in ipairs(require('diag_bundle').COMMANDS) do
    if item[1]==guard.RECORD then found=item[2][2]=='/var/run/homensai-vpn/'..guard.RECORD end
  end
  t.eq(found,true)
end)

------------------------------------------------------------------------------------------------------
-- every runner primitive failing once, anywhere in a run
------------------------------------------------------------------------------------------------------
t.test('chaos: any primitive raising once: nothing leaves the loop, passes never stop, the process lives',function()
  local WRAP={'read_file','write_atomic','remove','file_size','file_key','exists','sysfs','config_mtime','config_text','package_version',
    'capabilities','command','wall','clock','hires','random','log','try_lock','spawn','after','https_get','live_count'}
  local function one(at)
    local R=runner()
    local count,armed=0,false
    for _,name in ipairs(WRAP) do
      local original=R[name]
      if type(original)=='function' then
        R[name]=function(...)
          count=count+1
          if armed and count==at then error('INJECTED '..name,0) end
          return original(...)
        end
      end
    end
    local code=daemon(R,function(R)
      run_loop(R,2)  -- the start itself may fail: that is 'a failing start', a test of its own
      armed=true;count=0
      run_loop(R,30)
      armed=false
      run_loop(R,90)
    end)
    t.eq(code,nil,'call '..at)
    t.truthy(published_at(R)>R.now-40,'passes go on after call '..at)
  end
  for at=1,160,3 do one(at) end
end)

t.run()
