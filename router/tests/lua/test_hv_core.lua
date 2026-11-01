-- hv_core.lua (Lua plan item 8): the Lua monitor and the Lua Auto supervisor in one process.
-- Coroutine-safe pcall, the cooperative Auto task on a (fake) event loop, isolation of a failing monitor pass
-- from the Auto run and back, the watchdog (heartbeat, standby), the fallback after 3 crashes, both locks,
-- the status taken from memory (== decode of the written file), io.popen through RAM files, a real switch
-- transaction run as a task while the monitor keeps ticking.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local H=require('hv_core')
local A=require('auto')
local T=require('transaction')

------------------------------------------------------------------------------------------------------
-- a virtual-time event loop: after(ms, fn) -> {cancel}, clock(), run(seconds)
------------------------------------------------------------------------------------------------------
local function fake_loop()
  local L={now=1000,timers={},seq=0,fired=0}
  function L.clock() return L.now end
  function L.after(ms,fn)
    L.seq=L.seq+1
    local h={at=L.now+math.max(1,ms)/1000,fn=fn,seq=L.seq,live=true}
    h.cancel=function() h.live=false end
    L.timers[#L.timers+1]=h
    return h
  end
  function L.run(seconds)
    local stop=L.now+seconds
    while true do
      local best,index
      for i,h in ipairs(L.timers) do
        if h.live and (not best or h.at<best.at or (h.at==best.at and h.seq<best.seq)) then best,index=h,i end
      end
      if not best or best.at>stop then L.now=math.max(L.now,stop);break end
      table.remove(L.timers,index)
      L.now=math.max(L.now,best.at);best.live=false;L.fired=L.fired+1
      best.fn()
    end
  end
  return L
end

local function memfs()
  local files={}
  return {files=files,read=function(p) return files[p] end,write_atomic=function(p,text) files[p]=text end,
    remove=function(p) files[p]=nil end}
end

-- a core over the fake loop; opts.run(env, core) is the Auto run (default: a pass loop that sleeps 5 s)
local function make_core(opts)
  opts=opts or {}
  local L=opts.loop or fake_loop()
  local fs=opts.fs or memfs()
  local logs,states,fallbacks={},{},{}
  local d={loop=L,wall=function() return 1761830400+L.now end,pid=4242,log=function(text) logs[#logs+1]=text end,
    take_native_lock=opts.take_native_lock or function() return {fd=7} end,
    auto_env=function(core) return {stop=function() return core.stopping end,sleep=function(s) H.real_sleep(s) end} end,
    auto_run=opts.run or function(env) while not env.stop() do coroutine.yield('sleep',5) end;return 'stopped' end,
    record_crash=function(message) return A.record_crash(fs,'/run/hv-core-crashes.json',1761830400+L.now,message) end,
    fall_back=function(count,message) fallbacks[#fallbacks+1]={count=count,message=message} end,
    collect=function() end,
    write_state=function(value) states[#states+1]=value end,
    memory=function() return {VmRSS=9000} end,
    monitor_age=opts.monitor_age,kick_monitor=opts.kick_monitor or function() end}
  local core=H.core(d)
  return core,L,{logs=logs,states=states,fallbacks=fallbacks,fs=fs}
end
local function has(list,pattern)
  for _,line in ipairs(list) do if string.find(line,pattern) then return true end end
  return false
end

------------------------------------------------------------------------------------------------------
-- coroutine-safe pcall
------------------------------------------------------------------------------------------------------
t.test('copcall/coxpcall: results, error values (refusal tables too), and yields through nested calls',function()
  t.eq({H.copcall(function(a,b) return a+b,'x' end,2,3)},{true,5,'x'})
  local refusal=setmetatable({code='CLIENT-STOP'},require('auto_control').Refused)
  local ok,err=H.copcall(function() error(refusal,0) end)
  t.eq(ok,false);t.truthy(err==refusal,'the refusal table passes unchanged')
  local ok2,text=H.coxpcall(function() error('boom') end,function(e) return 'handled: '..e end)
  t.eq(ok2,false);t.truthy(string.find(text,'^handled: .*boom'),text)
  t.truthy(string.find(text,'protected call',1,true),'the place of a plain error is kept')
  -- a sleep three protected calls deep reaches the driver, and the call goes on afterwards
  local co=coroutine.create(function()
    return H.copcall(function()
      return H.coxpcall(function()
        local inner_ok,value=H.copcall(function() coroutine.yield('sleep',2);return 'after' end)
        return inner_ok and value
      end,function(e) return e end)
    end)
  end)
  local r1={coroutine.resume(co)}
  t.eq(r1,{true,'sleep',2})
  local r2={coroutine.resume(co)}
  t.eq(r2,{true,true,true,'after'})
end)

t.test('outside the task pcall/xpcall are the native functions; inside they let a sleep through',function()
  local G={}
  H.install_cooperative(G)
  t.eq({G.pcall(function() return 1 end)},{true,1})
  t.eq(H.in_task,false)
  local co=coroutine.create(function()
    H.in_task=true
    local ok,value=G.pcall(function() coroutine.yield('sleep',1);return 'ok' end)
    return ok,value
  end)
  H.in_task=true
  local r={coroutine.resume(co)};H.in_task=false
  t.eq(r,{true,'sleep',1})
  H.in_task=true;r={coroutine.resume(co)};H.in_task=false
  t.eq(r,{true,true,'ok'})
  -- the native pcall would have refused the yield
  local co2=coroutine.create(function() return pcall(function() coroutine.yield('sleep',1) end) end)
  local n={coroutine.resume(co2)}
  t.eq(n[1],true);t.eq(n[2],false);t.truthy(string.find(n[3],'yield across'),n[3])
end)

-- resume co as the task driver does (in_task, the coroutine chain)
local function in_task(co,...)
  H.in_task=true
  local r={H.resume_in(co,...)}
  H.in_task=false
  return r
end

t.test('cooperative sleep: yields inside the task, really sleeps outside',function()
  local slept={}
  local sys={sleep=function(s) slept[#slept+1]=s end}
  local saved=H.real_sleep;H.real_sleep=nil
  H.cooperative_sleep(sys)
  sys.sleep(0.5);t.eq(slept,{0.5})
  local co=coroutine.create(function() sys.sleep(3);sys.sleep(0);return 'done' end)
  local r=in_task(co)
  t.eq(r,{true,'sleep',3});t.eq(slept,{0.5})
  r=in_task(co)
  t.eq(r,{true,'done'})
  -- under a flock of the supervisor without the lock registry: the old rule, a real sleep (locked_sleeps)
  local control=require('control')
  local saved_inproc=control.inproc;control.inproc=nil
  local held=true
  H.real_sleep=nil;sys.sleep=function(s) slept[#slept+1]=s end
  H.cooperative_sleep(sys,function() return held end)
  local before,yields=H.locked_sleeps,H.locked_yields
  co=coroutine.create(function() sys.sleep(2);held=false;sys.sleep(4);return 'end' end)
  r=in_task(co)
  t.eq(r,{true,'sleep',4},'the sleep under the lock was real, the next one yields')
  t.eq(slept,{0.5,2});t.eq(H.locked_sleeps,before+1)
  -- with the registry installed the sleep under the lock yields too (locked_yields)
  control.inproc=H.lock_registry({})
  held=true
  co=coroutine.create(function() sys.sleep(2);return 'end' end)
  r=in_task(co)
  t.eq(r,{true,'sleep',2});t.eq(slept,{0.5,2},'no real sleep');t.eq(H.locked_yields,yields+1)
  control.inproc=saved_inproc
  H.real_sleep=saved
end)

t.test('yieldable: only from the task, through copcall, never across a C function or a for-iterator',function()
  t.eq(H.yieldable(),false,'outside the task')
  local seen={}
  local co=coroutine.create(function()
    seen.plain=H.yieldable()
    seen.copcall=select(2,H.copcall(function() return H.yieldable() end))
    seen.nested=select(2,H.copcall(function() return select(2,H.coxpcall(function() return H.yieldable() end,function(e) return e end)) end))
    table.sort({3,1,2},function(a,b) if seen.sort==nil then seen.sort=H.yieldable() end;return a<b end)
    seen.native=select(2,H.native_pcall(function() return H.yieldable() end))
    seen.gsub=false;string.gsub('x','x',function() seen.gsub=H.yieldable() end)
    for _ in function(_,c) if c then return nil end;seen.iterator=H.yieldable();return 1 end do end
    seen.under_sort_copcall=nil
    table.sort({2,1},function(a,b)
      if seen.under_sort_copcall==nil then seen.under_sort_copcall=select(2,H.copcall(function() return H.yieldable() end)) end
      return a<b
    end)
    -- a coroutine of its own inside the task: its yields would not reach the driver
    local own=coroutine.create(function() return H.yieldable() end)
    seen.own=select(2,coroutine.resume(own))
    return 'ok'
  end)
  t.eq(in_task(co),{true,'ok'})
  t.eq(seen,{plain=true,copcall=true,nested=true,sort=false,native=false,gsub=false,iterator=false,under_sort_copcall=false,own=false})
  -- a sleep where it may not yield is a real one (counted), not an error
  local slept={}
  local sys={sleep=function(s) slept[#slept+1]=s end}
  local saved=H.real_sleep;H.real_sleep=nil
  H.cooperative_sleep(sys)
  local before=H.unyieldable
  co=coroutine.create(function() table.sort({2,1},function(a,b) sys.sleep(1);return a<b end);return 'sorted' end)
  t.eq(in_task(co),{true,'sorted'});t.eq(slept,{1});t.eq(H.unyieldable,before+1)
  H.real_sleep=saved
end)

t.test('the lock state the router wiring reads: control.lock, try_lock, flock_file',function()
  local ctl=require('auto_control')
  local seen={}
  local dir=os.tmpname();os.remove(dir);os.execute('mkdir -p '..dir)
  if os.execute('command -v flock >/dev/null 2>&1')~=0 then print('  (skipped: no flock)');return end
  ctl.flock_file(dir..'/native-history.lock',function() seen[#seen+1]=ctl.flock_held end)
  t.eq(seen,{1});t.eq(ctl.flock_held,0)
  local control=require('control')
  control.lock(function() seen[#seen+1]=control.held_fd()~=nil end,dir)
  t.eq(seen[2],true);t.eq(control.held_fd(),nil)
  os.execute('rm -rf '..dir)
end)

------------------------------------------------------------------------------------------------------
-- isolation
------------------------------------------------------------------------------------------------------
t.test('a failing monitor pass never stops the Auto run, and a failing Auto run never stops the monitor',function()
  local L=fake_loop()
  local passes,failures,auto_passes=0,0,0
  local reports={}
  local report=function(where,err) reports[#reports+1]=where..': '..tostring(err) end
  -- the monitor: a guarded timer every 2 s whose every third pass fails before it re-arms
  local mtimer
  local function monitor_tick()
    mtimer=L.after(2000,H.guard('timer',monitor_tick,report))
    passes=passes+1
    if passes%3==0 then failures=failures+1;error('monitor pass failed') end
  end
  mtimer=L.after(100,H.guard('timer',monitor_tick,report))
  local runs=0
  local core,_,seen=make_core({loop=L,run=function(env)
    runs=runs+1
    for _=1,4 do auto_passes=auto_passes+1;coroutine.yield('sleep',5) end
    if runs==1 then error('Auto pass bug') end  -- a plain Lua error ends the first run
    while not env.stop() do auto_passes=auto_passes+1;coroutine.yield('sleep',5) end
    return 'stopped'
  end})
  core:start()
  L.run(120)
  t.truthy(failures>=10,'the monitor failed often: '..failures)
  t.truthy(passes>=55,'and kept passing: '..passes)
  t.eq(runs,2,'the crashed Auto run started again')
  t.truthy(auto_passes>=20,'the Auto passes went on during the monitor failures: '..auto_passes)
  t.eq(core.auto_crashes,1);t.eq(core.auto_state,'RUNNING')
  t.truthy(has(seen.logs,'Auto supervisor error: .*Auto pass bug'))
  t.eq(#reports,failures)
  t.eq(#seen.fallbacks,0)
end)

t.test('guarded uloop and ubus object: a failing callback is reported, a failing method answers fallback',function()
  local made={}
  local real={timer=function(fn,ms) made[#made+1]={fn=fn,ms=ms};return {set=function() end} end,
    process=function(path,args,env,fn) made[#made+1]={fn=fn};return {} end,fd_add=function(fd,fn,flags) made[#made+1]={fn=fn};return {} end,
    init=function() return 'init' end}
  local reports={}
  local U=H.guarded_uloop(real,function(where,err) reports[#reports+1]=where end)
  U.timer(function() error('t') end,5);U.process('/bin/true',{},{},function() error('p') end);U.fd_add(3,function() error('f') end,1)
  for _,m in ipairs(made) do m.fn() end
  t.eq(reports,{'timer','process','fd'});t.eq(made[1].ms,5);t.eq(U.init(),'init')
  local replies={}
  local conn={reply=function(self,req,body) replies[#replies+1]=body end}
  local object={['homensai-vpn-lua']={status={function(req,msg) error('bad') end,{}},rpc={function(req,msg) conn:reply(req,{ok=true}) end,{}}}}
  H.guard_object(object,conn,function(where) reports[#reports+1]=where end)
  object['homensai-vpn-lua'].status[1]({},{})
  object['homensai-vpn-lua'].rpc[1]({},{})
  t.eq(replies,{{fallback=true},{ok=true}});t.eq(reports[#reports],'ubus status')
end)

------------------------------------------------------------------------------------------------------
-- the safety net: 3 crashes in 600 s -> separate processes
------------------------------------------------------------------------------------------------------
t.test('the third Auto crash inside 600 s falls back; no restart after it',function()
  local runs=0
  local core,L,seen=make_core({run=function() runs=runs+1;coroutine.yield('sleep',1);error('crash '..runs) end})
  core:start()
  L.run(60)
  t.eq(runs,3);t.eq(#seen.fallbacks,1);t.eq(seen.fallbacks[1].count,3)
  t.truthy(string.find(seen.fallbacks[1].message,'crash 3',1,true))
  t.eq(core.auto_state,'FALLBACK');t.eq(core.auto_task,nil);t.eq(core.auto_retry,nil)
  L.run(600);t.eq(runs,3,'nothing starts after the fallback')
end)

t.test('crashes further apart than the window never fall back; normal ends are not crashes',function()
  local runs=0
  local core,L,seen=make_core({run=function() runs=runs+1;coroutine.yield('sleep',290);if runs%2==0 then return 'exit' end;error('slow crash') end})
  core:start()
  L.run(3000)
  t.truthy(runs>=8,'runs '..runs);t.eq(#seen.fallbacks,0)
  t.truthy(has(seen.logs,'run ended %(exit%)'),'a normal end restarts too')
end)

t.test('an end without a clean stop is counted at the next start (state file of another pid, watchdog record)',function()
  local fs=memfs()
  local recorded={}
  local d={runtime='/run',pid=50,read=fs.read,remove=fs.remove,record=function(m) recorded[#recorded+1]=m;return #recorded end}
  t.eq({H.previous_end(d)},{0,nil},'first start')
  fs.files['/run/hv-core.json']='{"clock":1.5,"pid":50}'
  t.eq({H.previous_end(d)},{0,nil},'own pid: not a crash')
  fs.files['/run/hv-core.json']='{"clock":1.5,"pid":49}'
  local n,message=H.previous_end(d)
  t.eq(n,1);t.truthy(string.find(message,'HV-CORE-UNCLEAN-END: pid 49',1,true))
  t.eq(fs.files['/run/hv-core.json'],nil)
  fs.files['/run/hv-core.json']='{"clock":1.5,"pid":48}'
  fs.files['/run/hv-core-watchdog.json']='{"age":130,"pid":48,"uptime":900}'
  n,message=H.previous_end(d)
  t.eq(n,2,'one crash, not two');t.truthy(string.find(message,'^HV%-CORE%-WATCHDOG'))
  t.eq(fs.files['/run/hv-core-watchdog.json'],nil)
  -- the shared counter: two unclean ends and one Auto error inside the window reach the fallback count
  local mfs=memfs()
  local P='/run/hv-core-crashes.json'
  A.record_crash(mfs,P,1000,'unclean');A.record_crash(mfs,P,1100,'watchdog')
  t.eq(A.record_crash(mfs,P,1200,'auto'),H.FALLBACK_CRASHES)
  t.eq(H.FALLBACK_WINDOW,A.FALLBACK_WINDOW);t.eq(H.FALLBACK_CRASHES,A.FALLBACK_CRASHES)
end)

------------------------------------------------------------------------------------------------------
-- watchdog
------------------------------------------------------------------------------------------------------
t.test('heartbeat: state every 5 s with pid and clock; a late loop and a long Auto step are logged',function()
  local L=fake_loop()
  local core,_,seen=make_core({loop=L,run=function(env)
    coroutine.yield('sleep',20)
    L.now=L.now+12  -- this Auto step holds the loop for 12 s (a blocking command)
    while not env.stop() do coroutine.yield('sleep',5) end
    return 'stopped'
  end})
  core:start()
  L.run(30)
  local last=seen.states[#seen.states]
  t.eq(last.pid,4242);t.truthy(canon.is_float(last.clock));t.eq(last.auto,'RUNNING')
  t.truthy(#seen.states>=4,'beats '..#seen.states)
  t.truthy(has(seen.logs,'HV%-CORE%-AUTO%-STEP: one Auto step held the loop 12%.0 s'))
  t.truthy(has(seen.logs,'HV%-CORE%-LOOP%-LAG'))
  t.truthy(core.max_step>=12 and core.max_lag>=5)
  local text=canon.encode(last)
  t.truthy(string.find(text,'"pid":4242',1,true) and string.find(text,'"clock":',1,true),'the standby parses these')
end)

t.test('heartbeat: a monitor without a pass for 15 minutes is started again',function()
  local kicked=0
  local age=0
  local core,L,seen=make_core({monitor_age=function() return age end,kick_monitor=function() kicked=kicked+1 end})
  core:start()
  L.run(20);t.eq(kicked,0)
  age=1000;L.run(10);t.eq(kicked,1);t.truthy(has(seen.logs,'HV%-CORE%-MONITOR%-STALLED'))
  L.run(60);t.eq(kicked,1,'not again at once')
end)

t.test('standby: watchdog TERM then KILL for a stalled hv-core, nothing for a live or foreign pid; exec on fallback',function()
  local files,kills,logs={},{},{}
  local now=5000
  local d={runtime='/run',clock=function() return now end,log=function(x) logs[#logs+1]=x end,
    exists=function(p) return files[p]~=nil end,read=function(p) return files[p] end,
    write=function(p,x) files[p]=x end,kill=function(pid,sig) kills[#kills+1]={pid,sig} end,
    cmdline=function(pid) if pid==77 then return '/usr/bin/lua /usr/lib/homensai-vpn/lua/hv_core.lua daemon ' end;if pid==88 then return '/bin/sh x ' end end}
  local state={}
  t.eq(H.standby_step(state,d),'wait','no heartbeat yet')
  files['/run/hv-core.json']=canon.encode(canon.object({pid=77,clock=canon.float(4990.5)}))
  t.eq(H.standby_step(state,d),'wait','fresh')
  now=4990.5+H.WATCHDOG_SECONDS+1
  t.eq(H.standby_step(state,d),'term');t.eq(kills,{{77,15}})
  t.truthy(files['/run/hv-core-watchdog.json']);t.truthy(string.find(logs[1],'HV-CORE-WATCHDOG',1,true))
  t.eq(H.standby_step(state,d),'wait','grace')
  now=now+H.KILL_GRACE
  t.eq(H.standby_step(state,d),'kill');t.eq(kills[2],{77,9})
  t.eq(H.standby_step(state,d),'wait');t.eq(#kills,2)
  files['/run/hv-core.json']=canon.encode(canon.object({pid=88,clock=canon.float(1)}))
  t.eq(H.standby_step({},d),'wait','not hv-core: never signalled');t.eq(#kills,2)
  files['/run/hv-core.json']=canon.encode(canon.object({pid=99,clock=canon.float(1)}))
  t.eq(H.standby_step({},d),'wait','gone')
  files['/run/hv-core-fallback.json']='{}'
  t.eq(H.standby_step({},d),'exec')
  t.eq(H.AUTO_DAEMON,{'/usr/bin/lua','/usr/lib/homensai-vpn/lua/auto.lua','daemon'})
  t.eq(H.MONITOR_DAEMON,{'/usr/bin/lua','/usr/lib/homensai-vpn/lua/monitor.lua','daemon'})
end)

------------------------------------------------------------------------------------------------------
-- locks
------------------------------------------------------------------------------------------------------
t.test('Auto waits for native.lock (retry every 5 s) while the monitor runs; then holds it across restarts',function()
  local free=false
  local takes=0
  local core,L,seen=make_core({take_native_lock=function() takes=takes+1;if free then return {fd=9} end end})
  core:start()
  L.run(12)
  t.eq(core.auto_state,'WAITING-LOCK');t.eq(core.auto_runs,0);t.eq(takes,3)
  t.truthy(has(seen.logs,'NATIVE%-SUPERVISOR%-BUSY'))
  free=true;L.run(6)
  t.eq(core.auto_state,'RUNNING');t.eq(core.auto_runs,1);t.eq(core.native_lock.fd,9)
end)

local function have_flock() return os.execute('command -v flock >/dev/null 2>&1')==0 end
t.test('agent.lock and native.lock are two independent flocks; each excludes a second holder',function()
  if not have_flock() then print('  (skipped: no flock)');return end
  local dir=os.tmpname();os.remove(dir);os.execute('mkdir -p '..dir)
  local saved=io.popen
  -- another process (Python agent.py / native_switch.py, or a second Lua daemon) tries the same flock(2)
  local function other_gets(name) return os.execute('flock -xn '..dir..'/'..name..' true')==0 end
  for _,variant in ipairs({'pipe','ram file'}) do
    if variant=='ram file' then io.popen=H.file_popen(dir,function() return require('canon').unique() end) end
    local agent,agent_fd=A.hold_lock(dir,'agent.lock')
    t.truthy(agent and agent_fd,variant..': agent.lock taken')
    t.eq(other_gets('agent.lock'),false,variant..': a second monitor is refused')
    t.eq(other_gets('native.lock'),true,variant..': native.lock is not taken with it')
    local native,native_fd=A.hold_native_lock(dir)
    t.truthy(native and native_fd and native_fd~=agent_fd,variant..': native.lock is separate')
    t.eq(other_gets('native.lock'),false,variant..': a second supervisor (Python or Lua) is refused')
    native:close()
    t.eq(other_gets('native.lock'),true,variant..': free again once released')
    t.eq(other_gets('agent.lock'),false,variant..': the monitor still holds its own')
    agent:close()
    t.eq(other_gets('agent.lock'),true)
  end
  io.popen=saved
  os.execute('rm -rf '..dir)
end)

------------------------------------------------------------------------------------------------------
-- io.popen through RAM files
------------------------------------------------------------------------------------------------------
t.test('file_popen: read output and write input like a pipe, the temporary files are removed',function()
  local dir=os.tmpname();os.remove(dir);os.execute('mkdir -p '..dir)
  local n=0
  local popen=H.file_popen(dir,function() n=n+1;return 'x'..n end)
  local p=popen('printf "a\\nb\\n"; echo "__RC__$?"','r')
  t.eq(p:read('*l'),'a');t.eq(p:read('*a'),'b\n__RC__0\n');p:close()
  local q=popen('exit 3; echo no','r');t.eq(q:read('*a'),'');q:close()
  local w=popen('cat >'..dir..'/out','w')
  w:write('one ');w:write('two',3);t.eq(w:close(),true)
  local f=io.open(dir..'/out','rb');t.eq(f:read('*a'),'one two3');f:close()
  os.remove(dir..'/out')
  local left=os.execute('ls -A '..dir..' | grep -q .')
  t.truthy(left~=0,'no temporary file left')
  os.execute('rm -rf '..dir)
end)

------------------------------------------------------------------------------------------------------
-- the status from memory
------------------------------------------------------------------------------------------------------
t.test('restore(status) is exactly decode_keys(encode(status)) and shares nothing with the monitor',function()
  local ctl=require('auto_control')
  local status=canon.object({time=1761830400.25,error=canon.null,interval=10,
    profiles=canon.array({canon.object({id='wireguard:peer_1',code=canon.null,rtt_ms=23.5,https_success=2,ok=true,country='Україна',
      checks={'dns','https'},extra={a=1,b=canon.float(2)}})}),
    samples={{id='wireguard:peer_1',time=canon.float(1761830399),code='VPN-001',latency=0.125}},
    vendor_observation=canon.object({generation=string.rep('01',16),epochs=canon.array({}),zero=-0.0,big=2^52}),
    uplink_observation=canon.object({state='UP',n=0}),observation_valid_for=canon.float(90),
    accounting=canon.object({huge=string.rep('z',1000)})})
  local text=canon.encode(status)
  local restored=H.restore(status,ctl.STATUS_KEYS)
  local decoded=canon.decode_keys(text,ctl.STATUS_KEYS)
  t.eq(canon.encode(restored),canon.encode(decoded))
  local function same_types(a,b,path)
    t.eq(getmetatable(a),getmetatable(b),'types at '..path)
    if type(a)=='table' and getmetatable(a)~=getmetatable(canon.float(0)) then
      for k,v in pairs(a) do same_types(v,b[k],path..'.'..tostring(k)) end
      for k in pairs(b) do t.truthy(a[k]~=nil,'missing '..path..'.'..tostring(k)) end
    elseif type(a)=='table' then t.eq(a.value,b.value)
    else t.eq(type(a),type(b),path);t.truthy(a==b,path) end
  end
  same_types(restored,decoded,'status')
  t.eq(restored.accounting,nil,'only the supervisor keys')
  status.profiles[1].code='CHANGED';status.samples[1].id='other'
  t.eq(restored.profiles[1].code,canon.null);t.eq(restored.samples[1].id,'wireguard:peer_1')
  t.eq(H.restore(canon.object({time=1,profiles=canon.array({'\255bad'})}),ctl.STATUS_KEYS),nil,'invalid UTF-8: read the file')
  t.eq(H.restore(canon.object({samples=setmetatable({},{})}),ctl.STATUS_KEYS),nil,'unknown table')
end)

t.test('seed_resident: read_json and backend.status take the seeded value without reading the file',function()
  local ctl=require('auto_control')
  local reads=0
  local path='/run/hv-seed/status.json'
  local text='{"time":5}'
  local run={fs={key=function() return 'k1' end,read=function() reads=reads+1;return text end}}
  local value=canon.object({time=5})
  ctl.seed_resident(path,text,'k1',value)
  t.truthy(ctl.read_json(run,path,nil)==value);t.eq(reads,0)
  t.truthy(ctl.decode_resident(path,text)==value,'backend.status: the same text, no parse')
  run.fs.key=function() return 'k2' end
  t.eq(ctl.read_json(run,path,nil).time,5);t.eq(reads,1,'another file version is read again')
end)

------------------------------------------------------------------------------------------------------
-- a real switch transaction as a task: the monitor goes on during it, the result is the synchronous one
------------------------------------------------------------------------------------------------------
local function pair_attempt(env)
  local opts={control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})}
  return T.attempt(env,env.backend.selection,env.run.wall()+3600,false,opts)
end

t.test('a switch transaction run as the Auto task while the monitor ticks: COMMITTED, the same phases',function()
  local L=fake_loop()
  local saved_pcall,saved_xpcall=pcall,xpcall
  H.install_cooperative()
  local env=t.env()
  local monitor_ticks,ticks_during=0,0
  local running=false
  -- every sleep of the transaction yields to the loop; a probe waits in a pcall'ed poll loop too
  env.sleep=function(s) env.slept[#env.slept+1]=s;if H.in_task then coroutine.yield('sleep',s) end;env.run.advance(s) end
  local probe=env.backend.probe
  env.backend.probe=function(profile)
    local ok,value=pcall(function() env.sleep(0.5);return probe(profile) end)
    if not ok then error(value,0) end
    return value
  end
  local mt
  local function tick() monitor_ticks=monitor_ticks+1;if running then ticks_during=ticks_during+1 end;mt=L.after(250,tick) end
  mt=L.after(250,tick)
  local result
  local task=H.task(function() running=true;pair_attempt(env);running=false;return 'done' end,L,function(ok,r) result={ok,r} end)
  task.step()
  L.run(600)
  pcall,xpcall=saved_pcall,saved_xpcall
  t.eq(result,{true,'done'})
  local j=t.journal(env)
  t.eq(j.phase,'COMMITTED')
  local phases={};for _,row in ipairs(j.phase_evidence) do phases[#phases+1]=row.phase end
  t.eq(phases,{'ARMED','APPLYING','WAIT-CLIENT','COMMITTED'})
  t.eq(t.states(env),{'ARMED','APPLYING','WAIT-CLIENT','COMMITTED'})
  t.truthy(#env.slept>0,'the transaction waited')
  t.truthy(ticks_during>0,'the monitor ticked during the switch: '..ticks_during..' (sleeps '..#env.slept..')')
  t.truthy(task.steps>1)
end)

------------------------------------------------------------------------------------------------------
-- responsiveness: the task's commands are loop children, sleeps under its flocks yield (after 2.0.0-alpha16)
------------------------------------------------------------------------------------------------------
local function tmpdir()
  local dir=os.tmpname();os.remove(dir);H.native_execute('mkdir -p '..dir..' && chmod 700 '..dir)
  return dir
end
local unique_n=0
local function unique() unique_n=unique_n+1;return 'u'..unique_n end

t.test('await: resumed by a loop callback, by a callback fired inside start, with a start error, and by block() in a drain',function()
  local L=fake_loop()
  local seen={}
  local task=H.task(function()
    -- 1) a callback 2 s later
    seen[#seen+1]={H.await(function(resume) L.after(2000,function() resume(true,'later') end) end)}
    seen[#seen+1]=L.now
    -- 2) fired at once inside start: still resumed from the loop, not from inside the step
    seen[#seen+1]={H.await(function(resume) resume(true,'at once') end)}
    -- 3) start raises: the awaiting code gets (false, error)
    seen[#seen+1]={H.await(function() error('cannot start',0) end)}
    -- 4) through a copcall, as inside pcall'ed supervisor code
    seen[#seen+1]={H.copcall(function() return H.await(function(resume) L.after(500,function() resume(true,'nested') end) end) end)}
    -- 5) the loop ends before the callback: block() finishes it
    seen[#seen+1]={H.await(function(resume) L.after(60000,function() resume(true,'never') end);return function() return true,'blocked' end end)}
    return 'done'
  end,L,function(ok,r) seen.result={ok,r} end)
  task.step()
  t.eq(seen[1],nil,'waiting')
  L.run(10)
  t.eq(seen[1],{true,'later'});t.eq(seen[2],1002);t.eq(seen[3],{true,'at once'});t.eq(seen[4],{false,'cannot start'})
  t.eq(seen[5],{true,true,'nested'})
  t.truthy(task.waiting,'the fifth waits')
  task.drain(function() error('no sleep expected') end)
  t.eq(seen[6],{true,'blocked'});t.eq(seen.result,{true,'done'})
  t.eq(H.draining,false)
end)

-- a fake child process on the virtual loop: the line runs (really, so its output files are real) when it
-- "exits", seconds(script) virtual seconds after the start
local function fake_spawner(L,seconds,log)
  local real=H.native_execute
  return function(script,on_exit,rc_path)
    log=log or {}
    log[#log+1]=script
    local h=L.after(seconds(script)*1000,function() local st=real(script);on_exit(math.floor(st/256)) end)
    return function() h.cancel();local st=real(script);return true,math.floor(st/256) end
  end
end

-- the A/B of the slow command on the virtual loop: old = the command runs inside the step (the loop clock moves
-- by its duration while nothing else runs); new = cooperative_exec (a loop child)
local function slow_command_run(cooperative)
  local L=fake_loop()
  local dir=tmpdir()
  local saved_popen,saved_native=io.popen,H.native_execute
  io.popen=H.file_popen(dir,unique)
  local function seconds(line) return string.find(line,'slow-command',1,true) and 3 or 0.01 end
  -- the synchronous path costs loop time: what the old hv-core did with a 3 s rtp2.sh/uci/iptables call
  H.native_execute=function(line,...)
    if H.in_task and line then L.now=L.now+seconds(line) end
    return saved_native(line,...)
  end
  if cooperative then
    H.cooperative_exec({directory=dir,unique=unique,clock=L.clock,spawn=fake_spawner(L,seconds)})
  else
    H.restore_execute();os.execute=function(line,...) return H.native_execute(line,...) end
  end
  H.install_cooperative()
  local sys=require('sys')
  -- the monitor: a tick every 250 ms; the page: a status call over the guarded ubus object every 100 ms
  local ticks,ticks_during,calls,max_wait=0,0,0,0
  local during=false
  local function tick() ticks=ticks+1;if during then ticks_during=ticks_during+1 end;L.after(250,tick) end
  L.after(250,tick)
  local conn={reply=function() end}
  local object={['homensai-vpn-lua']={status={function() calls=calls+1;return {ok=true} end,{}}}}
  local observed={}
  H.guard_object(object,conn,function() end,function(name,s) observed[#observed+1]=name end,L.clock)
  local function request()
    local due=L.now+0.1
    L.after(100,function()
      local wait=L.now-due
      if wait>max_wait then max_wait=wait end
      object['homensai-vpn-lua'].status[1]({},{})
      request()
    end)
  end
  request()
  local out
  local core,_,seen=make_core({loop=L,run=function(env)
    during=true
    local rc,body=sys.exec({'sh','-c','echo slow-command; echo done'})
    during=false
    out={rc,body}
    while not env.stop() do coroutine.yield('sleep',5) end
    return 'stopped'
  end})
  core:start()
  L.run(8)
  pcall=H.native_pcall;xpcall=H.native_xpcall
  H.restore_execute();H.native_execute=saved_native;io.popen=saved_popen
  H.native_execute('rm -rf '..dir)
  return {out=out,ticks_during=ticks_during,calls=calls,max_wait=max_wait,max_step=core.max_step,max_lag=core.max_lag,
    late=core.late_ticks,slow=core.slow_steps,logs=seen.logs,observed=#observed,core=core}
end

t.test('a 3 s command of the task is a loop child: the monitor ticks and status calls answer meanwhile (A/B, virtual time)',function()
  local old=slow_command_run(false)
  local new=slow_command_run(true)
  print(string.format('  old: max Auto step %.2f s, max loop lag %.2f s, status wait max %.2f s, ticks during %d',
    old.max_step,old.max_lag,old.max_wait,old.ticks_during))
  print(string.format('  new: max Auto step %.2f s, max loop lag %.2f s, status wait max %.2f s, ticks during %d',
    new.max_step,new.max_lag,new.max_wait,new.ticks_during))
  t.eq(old.out,{0,'slow-command\ndone\n'});t.eq(new.out,{0,'slow-command\ndone\n'},'the same exit status and output')
  t.truthy(old.max_step>=3 and old.max_wait>=2.5 and old.ticks_during==0,'old: the loop stood still for the command')
  t.truthy(has(old.logs,'HV%-CORE%-AUTO%-STEP: one Auto step held the loop 3%.0 s'),'old: logged')
  t.truthy(new.max_step<0.5,'new: no step >= 0.5 s: '..new.max_step)
  t.truthy(new.max_wait<0.3,'new: status answered within 0.3 s: '..new.max_wait)
  t.truthy(new.ticks_during>=10,'new: the monitor ticked during the command: '..new.ticks_during)
  t.eq(new.late,0);t.eq(new.slow,0)
  t.truthy(new.calls>=70 and new.observed==new.calls,'status calls observed: '..new.calls)
  t.truthy(H.async_commands>=1 and H.max_command_s>=3,'counted: '..H.async_commands..' '..H.max_command_s)
  t.truthy(string.find(H.last_slow_command,'slow-command',1,true),H.last_slow_command)
  local snap=canon.encode(new.core:snapshot(1))
  for _,key in ipairs({'"async_commands":','"max_command_s":','"locked_yields":','"slow_auto_steps":','"late_ticks":','"max_rpc_s":','"unyieldable":'}) do
    t.truthy(string.find(snap,key,1,true),'hv-core.json has '..key)
  end
end)

-- a real-time loop: timers on /proc/uptime, children polled through their done files, idle naps of 10 ms
local function real_loop()
  local L={timers={},seq=0,children={}}
  function L.clock()
    local f=io.open('/proc/uptime','r');local text=f:read('*l');f:close()
    return tonumber(string.match(text,'^([0-9.]+)'))
  end
  function L.after(ms,fn)
    L.seq=L.seq+1
    local h={at=L.clock()+math.max(1,ms)/1000,fn=fn,seq=L.seq,live=true}
    h.cancel=function() h.live=false end
    L.timers[#L.timers+1]=h
    return h
  end
  function L.spawn(script,on_exit,rc_path)
    local done=rc_path..'.done'
    H.native_execute('( '..script..'\n: >'..done..' ) </dev/null >/dev/null 2>&1 &')
    L.children[#L.children+1]={done=done,on_exit=on_exit}
  end
  function L.run(seconds)
    local stop=L.clock()+seconds
    while L.clock()<stop do
      local now=L.clock()
      for i=#L.children,1,-1 do
        local c=L.children[i]
        local f=io.open(c.done,'rb')
        if f then f:close();os.remove(c.done);table.remove(L.children,i);c.on_exit(0) end
      end
      local best,index
      for i,h in ipairs(L.timers) do
        if h.live and h.at<=now and (not best or h.at<best.at) then best,index=h,i end
      end
      if best then table.remove(L.timers,index);best.live=false;best.fn()
      else H.native_execute('sleep 0.01') end
      for i=#L.timers,1,-1 do if not L.timers[i].live then table.remove(L.timers,i) end end
    end
  end
  return L
end

t.test('measured in real time: a real 3 s child of the task; the monitor tick and status calls go on',function()
  local function run(cooperative)
    local L=real_loop()
    local dir=tmpdir()
    local saved_popen=io.popen
    io.popen=H.file_popen(dir,unique)
    if cooperative then H.cooperative_exec({directory=dir,unique=unique,clock=L.clock,spawn=L.spawn}) end
    H.install_cooperative()
    local sys=require('sys')
    local ticks,calls,max_wait=0,0,0
    local function tick() ticks=ticks+1;L.after(250,tick) end
    L.after(250,tick)
    local function request()
      local due=L.clock()+0.1
      L.after(100,function() calls=calls+1;local w=L.clock()-due;if w>max_wait then max_wait=w end;request() end)
    end
    request()
    local out,steps,max_step,finished=nil,0,0,nil
    local task=H.task(function()
      local started=L.clock()
      out={sys.exec({'sh','-c','sleep 3; echo slept'})}
      finished=L.clock()-started
      return 'done'
    end,L,function() end,function(s) steps=steps+1;if s>max_step then max_step=s end end)
    task.step()
    while not task.done do L.run(0.5) end
    L.run(0.3)
    pcall=H.native_pcall;xpcall=H.native_xpcall
    H.restore_execute();io.popen=saved_popen
    H.native_execute('rm -rf '..dir)
    return {out=out,ticks=ticks,calls=calls,max_wait=max_wait,max_step=max_step,steps=steps,finished=finished}
  end
  local old=run(false)
  local new=run(true)
  print(string.format('  old (synchronous): command %.2f s, max Auto step %.2f s, status wait max %.2f s, ticks %d, status calls %d',
    old.finished,old.max_step,old.max_wait,old.ticks,old.calls))
  print(string.format('  new (loop child):  command %.2f s, max Auto step %.2f s, status wait max %.2f s, ticks %d, status calls %d',
    new.finished,new.max_step,new.max_wait,new.ticks,new.calls))
  t.eq(old.out,{0,'slept\n'});t.eq(new.out,{0,'slept\n'})
  t.truthy(old.max_step>=2.9,'old: the step held the loop for the command')
  t.truthy(new.max_step<0.5,'new: every step < 0.5 s: '..new.max_step)
  t.truthy(new.max_wait<0.3,'new: status calls waited < 0.3 s: '..new.max_wait)
  t.truthy(new.ticks>=10 and new.calls>=25,'new: the loop ran meanwhile: '..new.ticks..' ticks, '..new.calls..' calls')
end)

t.test('the native os.execute stays: outside the task, where no yield is possible, and while the task is drained',function()
  local L=fake_loop()
  local spawned={}
  H.cooperative_exec({directory='/tmp',unique=unique,clock=L.clock,spawn=fake_spawner(L,function() return 1 end,spawned)})
  t.eq(os.execute('exit 3'),3*256,'outside the task');t.eq(#spawned,0)
  local before=H.sync_task_commands
  local results={}
  local task=H.task(function()
    table.sort({2,1},function(a,b) if not results.sort then results.sort=os.execute('exit 2') end;return a<b end)
    results.async=os.execute('exit 5')
    results.again=os.execute('true')
    return 'done'
  end,L,function() end)
  task.step()
  t.eq(results.sort,2*256,'inside table.sort: synchronous');t.eq(H.sync_task_commands,before+1)
  t.eq(#spawned,1,'the next one is a child');t.eq(results.async,nil)
  -- the loop ends here (stop): the waiting child is finished by its block(), the next command is synchronous
  task.drain(function() end)
  t.eq(results.async,5*256);t.eq(results.again,0);t.eq(#spawned,1);t.eq(H.sync_task_commands,before+1)
  H.restore_execute()
  t.truthy(os.execute==H.native_execute)
end)

t.test('router wiring: router_spawn keeps the uloop child referenced; block() after the loop; environment fallback',function()
  local made={}
  local fake={process=function(path,args,env,cb) local p={path=path,args=args,env=env,cb=cb};made[#made+1]=p;return p end}
  local spawn=H.router_spawn(fake,{'PATH=/bin'})
  local exited={}
  local dir=tmpdir()
  local rc=dir..'/x.rc'
  local block=spawn('true',function(code) exited[#exited+1]=code end,rc)
  t.eq(made[1].path,'/bin/sh');t.eq(made[1].args,{'-c','true'});t.eq(made[1].env,{'PATH=/bin'})
  local live=0;for _ in pairs(H.children) do live=live+1 end
  t.eq(live,1,'referenced until it exits')
  made[1].cb(0);t.eq(exited,{0})
  live=0;for _ in pairs(H.children) do live=live+1 end
  t.eq(live,0)
  -- after the loop (no nixio here): the status file ends the wait
  local f=io.open(rc,'wb');f:write('0\n');f:close()
  local saved=H.real_sleep;H.real_sleep=function() error('no sleep expected') end
  t.eq({block()},{true,nil})
  H.real_sleep=saved
  t.eq(fake.process and type(H.router_child_env({CHILD_ENV={'PATH=/x'}})),'table')
  t.eq(H.router_lock_view().stat,nil,'no nixio.fs: no device/inode view (paths compared)')
  local fail=H.router_spawn({process=function() return nil end},{})
  t.truthy(not pcall(fail,'true',function() end,rc),'a child that cannot start raises (the line then runs here)')
  H.native_execute('rm -rf '..dir)
end)

t.test('a child that cannot start: the line runs here as before (spawn_failures)',function()
  local L=fake_loop()
  H.cooperative_exec({directory='/tmp',unique=unique,clock=L.clock,spawn=function() error('uloop.process',0) end})
  local before=H.spawn_failures
  local got
  local task=H.task(function() got=os.execute('exit 4');return 'done' end,L,function() end)
  task.step();L.run(1)
  H.restore_execute()
  t.eq(got,4*256);t.eq(H.spawn_failures,before+1);t.eq(task.done,true)
end)

local function lua_pid()
  local f=io.open('/proc/self/stat','r');local text=f:read('*l');f:close()
  return string.match(text,'^(%d+)')
end
-- stat/fds of this Lua process through the shell (the router uses nixio.fs)
local function shell_view()
  local pid=lua_pid()
  local function capture(line)
    local path=os.tmpname()
    H.native_execute(line..' >'..path..' 2>/dev/null')
    local f=io.open(path,'rb');local text=f and f:read('*a') or '';if f then f:close() end
    os.remove(path)
    return text
  end
  return {stat=function(path)
      path=string.gsub(path,'^/proc/self/','/proc/'..pid..'/')
      local dev,ino=string.match(capture("stat -L -c '%d %i' "..path),'^(%d+) (%d+)')
      if dev then return {dev=tonumber(dev),ino=tonumber(ino)} end
    end,
    fds=function()
      local out={}
      for n in string.gmatch(capture('ls /proc/'..pid..'/fd'),'%d+') do if tonumber(n)>2 then out[#out+1]=tonumber(n) end end
      return out
    end}
end

t.test('lock registry: while the task waits under the control lock, the loop try_lock is "busy"; after it, taken',function()
  if not have_flock() then print('  (skipped: no flock)');return end
  local control=require('control')
  local mio=require('monitor_io')
  local dir=tmpdir()
  local L=fake_loop()
  local registry=H.lock_registry(shell_view())
  local saved_inproc=control.inproc
  control.inproc=registry
  H.install_cooperative()
  local got={}
  local function other_gets() return H.native_execute('flock -xn '..dir..'/auto-control.lock true')==0 end
  local task=H.task(function()
    control.lock(function()
      got.held=control.held_fd()
      coroutine.yield('sleep',2)  -- a wait of the supervisor under its lock (sys.sleep yields like this)
      got.task_try=mio.try_lock(dir,function() return 'nested' end)
    end,dir)
    return 'done'
  end,L,function() end)
  L.after(500,function()
    got.during={mio.try_lock(dir,function() return 'loop' end)}
    got.other_during=other_gets()
    got.count=registry.count()
    got.fds=registry.held_fds()
  end)
  L.after(3000,function() got.after={mio.try_lock(dir,function() return 'loop' end)};got.other_after=other_gets() end)
  task.step()
  L.run(5)
  pcall=H.native_pcall;xpcall=H.native_xpcall
  t.eq(got.during,{false},'the loop never takes the task descriptor')
  t.eq(got.other_during,false,'another process is excluded as before')
  t.eq(got.count,1)
  t.truthy(got.fds and #got.fds>=1,'the task descriptor is found')
  local found=false
  for _,fd in ipairs(got.fds or {}) do if tostring(fd)==tostring(got.held) then found=true end end
  t.truthy(found,'held_fds has the control lock descriptor '..tostring(got.held))
  t.eq(got.after,{true,'loop'},'free after the task let go');t.eq(got.other_after,true)
  t.eq(registry.count(),0,'nothing stays registered')
  t.eq(task.done,true)
  -- reset(): an ended run leaves nothing open
  H.in_task=true;registry.opened(dir..'/x.lock');H.in_task=false
  t.eq(registry.count(),1);registry.reset();t.eq(registry.count(),0)
  control.inproc=saved_inproc
  H.native_execute('rm -rf '..dir)
end)

t.test('the task commands are started by the driver outside the coroutine and are never wrapped (MT3000, alpha17)',function()
  local started,reports={},{}
  local real={process=function(path,args,env,fn) started[#started+1]={path=path,args=args,fn=fn};return {} end,timer=function() end}
  local fds={7}
  local U=H.guarded_uloop(real,function() end,function() return fds end)
  local spawn=H.router_spawn(H.task_uloop(real,function(where) reports[#reports+1]=where end),{})
  t.eq(H.in_task,false)
  spawn('flock -x 7',function() error('boom') end,'/nonexistent/rc')
  t.eq(started[1].path,'/bin/sh');t.eq(started[1].args,{'-c','flock -x 7'},'the lock helper keeps the task descriptor')
  started[1].fn(0);t.eq(reports,{'process'},'the exit callback stays guarded')
  U.process('/usr/bin/curl',{},{},function() end)
  t.eq(started[2].path,'/bin/sh','a loop child is still wrapped')
end)

t.test('a loop child started while the task holds a flock gets the task descriptors closed (same argv, exec)',function()
  local started={}
  local real={process=function(path,args,env,fn) started[#started+1]={path=path,args=args};return {} end,timer=function() end}
  local fds={7,9}
  local U=H.guarded_uloop(real,function() end,function() return fds end)
  U.process('/usr/bin/curl',{'-s','https://x'},{},function() end)
  t.eq(started[1].path,'/bin/sh')
  t.eq(started[1].args,{'-c','exec "$0" "$@" 7>&- 9>&-','/usr/bin/curl','-s','https://x'})
  H.in_task=true;U.process('/bin/sh',{'-c','x'},{},function() end);H.in_task=false
  t.eq(started[2],{path='/bin/sh',args={'-c','x'}},'the task own children keep them (the flock helpers need them)')
  fds={};U.process('/usr/bin/curl',{'-s'},{},function() end)
  t.eq(started[3],{path='/usr/bin/curl',args={'-s'}},'nothing held: unchanged')
  -- the wrapper really closes the descriptor in the child
  local dir=tmpdir()
  local holder=io.open(dir..'/held','a')
  local shown={}
  for n in string.gmatch((function() local p=io.popen('ls /proc/'..lua_pid()..'/fd');local x=p:read('*a');p:close();return x end)(),'%d+') do shown[#shown+1]=tonumber(n) end
  local view=shell_view()
  local target=view.stat(dir..'/held')
  local fd
  for _,n in ipairs(shown) do local st=view.stat('/proc/self/fd/'..n);if st and st.ino==target.ino and st.dev==target.dev then fd=n end end
  t.truthy(fd,'the descriptor of the held file')
  local function child_sees(wrapped)
    local check="test -e /proc/\\$\\$/fd/"..fd.." && echo open || echo closed"
    local line
    if wrapped then line="/bin/sh -c 'exec \"$0\" \"$@\" "..fd..">&-' /bin/sh -c \""..check.."\""
    else line="/bin/sh -c \""..check.."\"" end
    local out=os.tmpname()
    H.native_execute(line..' >'..out)
    local f=io.open(out,'rb');local text=f:read('*a');f:close();os.remove(out)
    return text
  end
  t.eq(child_sees(false),'open\n');t.eq(child_sees(true),'closed\n')
  holder:close()
  H.native_execute('rm -rf '..dir)
end)

t.test('profiling: a slow step is counted and logged with where it began and ended; the lag probe counts late ticks',function()
  local L=fake_loop()
  local function deep_wait() coroutine.yield('sleep',2) end
  local core,_,seen=make_core({loop=L,run=function(env)
    deep_wait()
    L.now=L.now+0.8   -- 0.8 s of synchronous work in this step
    deep_wait()
    L.now=L.now+0.6
    deep_wait()
    while not env.stop() do coroutine.yield('sleep',5) end
    return 'stopped'
  end})
  core:start()
  L.run(20)
  t.eq(core.slow_steps,2);t.truthy(core.max_step>=0.79)
  t.truthy(string.find(core.last_slow_step,'^0%.60 s: test_hv_core%.lua:%d+'),core.last_slow_step)
  t.truthy(has(seen.logs,'HV%-CORE%-AUTO%-STEP: one Auto step held the loop 0%.8 s %(test_hv_core%.lua:%d+.* %-> test_hv_core%.lua:%d+'),'logged with places')
  t.eq(#(function() local n={};for _,l in ipairs(seen.logs) do if string.find(l,'AUTO-STEP',1,true) then n[#n+1]=l end end;return n end)(),1,'rate limited')
  t.truthy(core.late_ticks>=1,'the 0.8 s step made the lag probe late: '..core.late_ticks)
  core:rpc('status',0.05);core:rpc('rpc',0.2)
  local snap=core:snapshot(L.now)
  t.eq(snap.rpc_calls,2);t.eq(snap.max_rpc_method,'rpc');t.eq(snap.slow_auto_steps,2)
end)

t.test('standby after a fallback: becomes auto.lua only once native.lock is free (no NATIVE-SUPERVISOR-BUSY loop)',function()
  local files,logs={['/run/hv-core-fallback.json']='{}'},{}
  local now=100
  local free=false
  local d={runtime='/run',clock=function() return now end,log=function(x) logs[#logs+1]=x end,
    exists=function(p) return files[p]~=nil end,read=function(p) return files[p] end,
    lock_free=function(path) t.eq(path,'/run/native.lock');return free end}
  local state={}
  t.eq(H.standby_step(state,d),'wait');t.eq(H.standby_step(state,d),'wait');t.eq(#logs,1)
  free=true;t.eq(H.standby_step(state,d),'exec')
  free=false;now=now+H.EXEC_WAIT;t.eq(H.standby_step(state,d),'exec','never waits for ever')
  d.lock_free=nil;t.eq(H.standby_step({},d),'exec','no check available: as before')
end)

t.test('stop: the waiting Auto run sees stop(), ends its pass with real sleeps and shuts down; nothing restarts',function()
  local L=fake_loop()
  local shutdown=false
  local slept={}
  local core=make_core({loop=L,run=function(env)
    while not env.stop() do coroutine.yield('sleep',5) end
    coroutine.yield('sleep',1)  -- the last pass after Stop still waits once
    shutdown=true
    return 'stopped'
  end})
  core:start()
  L.run(12)
  core:stop(function(s) slept[#slept+1]=s;L.now=L.now+s end)
  t.eq(shutdown,true);t.eq(core.auto_state,'STOPPED');t.truthy(#slept>=1)
  L.run(60);t.eq(core.auto_runs,1,'no restart after a stop')
end)

t.run()
