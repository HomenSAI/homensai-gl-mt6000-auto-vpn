-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- hv_core.lua: hv-core, the Lua monitor and the Lua Auto supervisor in ONE process (Lua plan item 8, 2.0.0-lua line).
-- Design and router test: docs/architecture/LUA-HVCORE-ITEM8-2026-10-31.ru.md.
--
--   lua hv_core.lua daemon    procd instance `monitor` (homensai_vpn.main.lua_core_process='1'): monitor.start()
--                             and auto.run_blocking() on one uloop; holds agent.lock (the monitor's own) and
--                             native.lock (the supervisor's), both as the separate daemons do
--   lua hv_core.lua standby   procd instance `native`: a few hundred kB that (1) watch the heartbeat of hv-core
--                             and end a stalled event loop (procd restarts it) and (2) become the separate Lua Auto
--                             supervisor (`exec lua auto.lua daemon`, same pid) when hv-core has fallen back
--
-- One interpreter instead of two: the libraries (canon, pair, manual, sys, uci/ubus/nixio bindings ...) are
-- loaded once, and the supervisor takes the monitor's status.json from memory (no read, no pure-Lua parse).
--
-- The supervisor's pass is synchronous Lua code that sleeps (waits of a transaction up to ~90 s, 200 ms polls of
-- the owner's click). Inside hv-core it runs in a coroutine (a task): every sys.sleep()/env.sleep() yields to
-- uloop, which resumes the task by a timer, so the monitor's passes, probes and ubus answers go on during a
-- switch. Lua 5.1 cannot yield across pcall/xpcall, so while the task runs pcall/xpcall are coroutine-safe
-- versions (copcall/coxpcall: the protected call runs in its own coroutine and passes yields outwards; error
-- values - tables of refusals included - are unchanged). Outside the task they are the native functions.
-- Every command the supervisor still runs synchronously is short and bounded (iptables-save, ip, uci, flock);
-- io.popen is replaced by a RAM-file version: the SIGCHLD of the monitor's uloop children would otherwise
-- interrupt a blocking pipe read (EINTR, a router fact) and turn a good command into a failed one.
--
-- Isolation: every uloop/ubus callback runs under pcall (a failing handler is logged and counted, the loop goes
-- on; a failed ubus method answers {"fallback":true}, so the rpcd dispatcher asks agent.py as when the object is
-- missing). The monitor's tick/watcher re-arm themselves (monitor.start). A plain Lua error that ends the Auto
-- run is a crash: it is counted, the run ends like the separate daemon ended (journal recovery by the next run)
-- and a new run starts after 5 s (procd's respawn delay). Normal ends ('stopped', 'exit') start again the same
-- way, uncounted.
--
-- Safety net (FALLBACK_CRASHES in FALLBACK_WINDOW s, the numbers of auto.lua): crashes are Auto run errors,
-- fatal hv-core errors, and an end without a clean stop found at the next start (kill -9, the watchdog, a
-- segfault). At the third, hv-core writes RUNTIME/hv-core-fallback.json, logs HV-CORE-FALLBACK, saves the
-- accounting, releases both locks and becomes `lua monitor.lua daemon` (same pid: procd's monitor instance);
-- the standby sees the file and becomes `lua auto.lua daemon`. Their own fallbacks stay (auto.lua -> Python after
-- 3 errors). The file lives until the next service stop (init script), so a respawn stays separate.
--
-- Watchdog: hv-core writes RUNTIME/hv-core.json every HEARTBEAT_SECONDS from a uloop timer (pid, uptime clock,
-- counters, memory). A loop that does not write it for WATCHDOG_SECONDS is stalled: the standby logs
-- HV-CORE-WATCHDOG, records it and sends SIGTERM, then SIGKILL after KILL_GRACE s; procd restarts hv-core and the
-- next start counts the crash. (A stalled loop cannot watch itself: uloop's SIGTERM handler only sets a flag.)
--
-- Stop (procd SIGTERM): uloop.run() returns; the Auto run is driven to its end with real sleeps (it sees stop(),
-- finishes its pass and runs auto.shutdown(), as `auto.lua daemon` did after uloop.run()); term_timeout 300.
local here=(arg and arg[0] and string.match(arg[0],'^(.*)/[^/]*$'))
if here then package.path=here..'/?.lua;'..package.path end

local M={}
M.FALLBACK_CRASHES=3
M.FALLBACK_WINDOW=600
M.RESTART_SECONDS=5
M.HEARTBEAT_SECONDS=5
M.WATCHDOG_SECONDS=120
M.KILL_GRACE=10
M.STANDBY_POLL=2
M.LAG_LOG_SECONDS=5
M.MONITOR_STALL_SECONDS=900
M.STATE='hv-core.json'
M.CRASHES='hv-core-crashes.json'
M.FALLBACK='hv-core-fallback.json'
M.WATCHDOG='hv-core-watchdog.json'
M.SCRIPT='/usr/lib/homensai-vpn/lua/hv_core.lua'
M.MONITOR_DAEMON={'/usr/bin/lua','/usr/lib/homensai-vpn/lua/monitor.lua','daemon'}
M.AUTO_DAEMON={'/usr/bin/lua','/usr/lib/homensai-vpn/lua/auto.lua','daemon'}

------------------------------------------------------------------------------------------------------
-- coroutine-safe pcall/xpcall (Lua 5.1 cannot yield across the C functions pcall/xpcall)
------------------------------------------------------------------------------------------------------
local native_pcall,native_xpcall=pcall,xpcall
M.native_pcall,M.native_xpcall=native_pcall,native_xpcall
local co_create,co_resume,co_yield,co_status=coroutine.create,coroutine.resume,coroutine.yield,coroutine.status
M.in_task=false  -- true only while the supervisor task is being resumed

local function settle(co,handler,ok,...)
  if not ok then
    local err=...
    if handler then
      local result=handler(err)
      -- the handler runs after the protected coroutine died: add the place of a plain error from its stack
      if type(err)~='table' and type(result)=='string' then result=result..'\n'..debug.traceback(co,'(protected call)') end
      return false,result
    end
    return false,err
  end
  if co_status(co)=='dead' then return true,... end
  -- the protected function yielded (a sleep of the task): pass it outwards, resume with what comes back
  return settle(co,handler,co_resume(co,co_yield(...)))
end
function M.coxpcall(f,handler,...)
  local co=co_create(function(...) return f(...) end)
  return settle(co,handler,co_resume(co,...))
end
function M.copcall(f,...) return M.coxpcall(f,nil,...) end
function M.pcall(f,...)
  if M.in_task then return M.coxpcall(f,nil,...) end
  return native_pcall(f,...)
end
function M.xpcall(f,handler)
  if M.in_task then return M.coxpcall(f,handler) end
  return native_xpcall(f,handler)
end
-- install_cooperative(G): the global pcall/xpcall every module looks up at call time
function M.install_cooperative(G)
  G=G or _G
  G.pcall=M.pcall;G.xpcall=M.xpcall
end
-- cooperative_sleep(sys, locked): sys.sleep (the bottom of env.sleep, sys.wait, the probe polls,
-- platform.wait_quiet) yields inside the task; elsewhere it is the real sleep. While the supervisor holds one of
-- its flocks (locked() true: the control lock, a try_lock, native-history.lock) it never yields: the monitor's
-- lock helpers find a held descriptor of the same file through /proc/self/fd and would take it as their own,
-- and a blocking lock in the loop would wait for a task that cannot run. That sleep blocks the loop, as the
-- separate supervisor's sleep under the lock blocked the monitor's request for it (counted: locked_sleeps).
M.locked_sleeps=0
function M.cooperative_sleep(sys,locked)
  local real=M.real_sleep or sys.sleep
  M.real_sleep=real
  sys.sleep=function(seconds)
    if M.in_task then
      if type(seconds)~='number' or seconds<=0 then return end
      if locked and locked() then M.locked_sleeps=M.locked_sleeps+1;return real(seconds) end
      co_yield('sleep',seconds)
    else real(seconds) end
  end
end

------------------------------------------------------------------------------------------------------
-- task: one coroutine driven by a loop {after(ms, fn) -> {cancel()}, clock()}
------------------------------------------------------------------------------------------------------
-- on_done(ok, result) once at the end; on_step(seconds) after every resume (its duration = loop blocked).
function M.task(fn,loop,on_done,on_step)
  local t={done=false,draining=false,steps=0}
  t.co=co_create(fn)
  local function step()
    t.handle=nil
    if t.done then return end
    local started=loop.clock()
    M.in_task=true
    local result={co_resume(t.co)}
    M.in_task=false
    t.steps=t.steps+1
    if on_step then on_step(loop.clock()-started) end
    if co_status(t.co)=='dead' then
      t.done=true;t.ok=result[1];t.result=result[2]
      on_done(result[1],result[2])
      return
    end
    local seconds=result[2]=='sleep' and tonumber(result[3]) or 0
    if not seconds or seconds~=seconds or seconds<0 then seconds=0 end
    t.wake_at=loop.clock()+seconds
    if not t.draining then t.handle=loop.after(math.floor(seconds*1000+0.5),step) end
  end
  t.step=step
  -- drain(sleep): runs the task to its end here, with real sleeps (after the loop has ended)
  function t.drain(sleep)
    t.draining=true
    if t.handle then t.handle.cancel();t.handle=nil end
    while not t.done do
      local left=(t.wake_at or 0)-loop.clock()
      while left>0 do sleep(left);left=(t.wake_at or 0)-loop.clock() end
      step()
    end
  end
  return t
end

-- loop adapter over (the guarded) uloop; the handle keeps the timer referenced (libubox-lua cancels in __gc)
function M.loop(uloop,clock)
  return {clock=clock,after=function(ms,fn)
    local h={}
    local timer=uloop.timer(fn)
    h.timer=timer
    timer:set(math.max(1,math.floor(ms)))
    h.cancel=function() native_pcall(function() timer:cancel() end) end
    return h
  end}
end

------------------------------------------------------------------------------------------------------
-- io.popen through RAM files (no pipe read that a SIGCHLD of the monitor's children could interrupt)
------------------------------------------------------------------------------------------------------
-- 'r': the command runs to its end now (system() retries its wait), the returned file is its output;
-- 'w': writes are kept and the command reads them from a file at close(). Same lines, same exit statuses
-- (the callers echo $? themselves: Lua 5.1 popen close() never returned one).
function M.file_popen(directory,unique,execute)
  execute=execute or os.execute
  return function(command,mode)
    mode=mode or 'r'
    local path=directory..'/.popen-'..unique()
    if string.sub(mode,1,1)=='w' then
      local parts={}
      local proxy={}
      function proxy.write(self,...)
        for i=1,select('#',...) do parts[#parts+1]=tostring((select(i,...))) end
        return self
      end
      function proxy.flush(self) return self end
      function proxy.setvbuf() return true end
      function proxy.close(self)
        if self.closed then return nil,'closed' end
        self.closed=true
        local f=io.open(path,'wb')
        if not f then return nil,'popen input' end
        f:write(table.concat(parts));f:close()
        execute('{ '..command..'\n} <'..path)
        os.remove(path)
        return true
      end
      return proxy
    end
    execute('{ '..command..'\n} >'..path)
    local f=io.open(path,'rb')
    os.remove(path)  -- the open file stays readable
    if not f then return nil,'popen output' end
    return f
  end
end
function M.install_file_popen(directory)
  os.execute('mkdir -p '..directory..' && chmod 700 '..directory)
  io.popen=M.file_popen(directory,function() return require('canon').unique() end)
end

------------------------------------------------------------------------------------------------------
-- isolation of callbacks
------------------------------------------------------------------------------------------------------
function M.guard(where,fn,report)
  return function(...)
    local ok,err=native_pcall(fn,...)
    if not ok then report(where,err) end
  end
end
-- guarded_uloop(real, report): uloop whose timer/process/fd callbacks run under pcall (package.loaded.uloop)
function M.guarded_uloop(real,report)
  local proxy=setmetatable({},{__index=real})
  proxy.timer=function(fn,ms)
    if ms~=nil then return real.timer(M.guard('timer',fn,report),ms) end
    return real.timer(M.guard('timer',fn,report))
  end
  proxy.process=function(path,args,env,fn) return real.process(path,args,env,M.guard('process',fn,report)) end
  proxy.fd_add=function(fd,fn,flags) return real.fd_add(fd,M.guard('fd',fn,report),flags) end
  return proxy
end
-- guard_object(object, conn, report): a failing ubus method answers {"fallback":true} (rpcd -> agent.py)
function M.guard_object(object,conn,report)
  for _,methods in pairs(object) do
    for name,spec in pairs(methods) do
      local fn=spec[1]
      if type(fn)=='function' then
        spec[1]=function(req,msg)
          local ok,result=native_pcall(fn,req,msg)
          if ok then return result end
          report('ubus '..tostring(name),result)
          native_pcall(conn.reply,conn,req,{fallback=true})
        end
      end
    end
  end
end

------------------------------------------------------------------------------------------------------
-- the monitor's status from memory: restore(status, keys) == canon.decode_keys(canon.encode(status), keys)
------------------------------------------------------------------------------------------------------
-- The same value types decode() gives (integral numbers plain, other numbers canon.float boxes, null, marked
-- arrays/objects), new tables throughout (the monitor may change its own later). nil when anything is outside
-- what decode() would give back unchanged (invalid UTF-8, a too deep nesting, unknown tables): the caller then
-- reads the file as before.
local TWO53=9007199254740992
function M.restore(value,keys)
  local canon=require('canon')
  local NULL=canon.null
  local FLOAT_MT=getmetatable(canon.float(0))
  local ARRAY_MT=getmetatable(canon.array({}))
  local OBJECT_MT=getmetatable(canon.object({}))
  local function fail() error('restore',0) end
  local copy
  copy=function(v,depth)
    if v==NULL then return NULL end
    local t=type(v)
    if t=='string' then if not canon.valid_utf8(v) then fail() end;return v end
    if t=='boolean' then return v end
    if t=='number' then
      if v~=v or v==math.huge or v==-math.huge then fail() end
      if v%1==0 then if math.abs(v)>TWO53 then fail() end;if v==0 then return 0 end;return v end
      return canon.float(v)
    end
    if t~='table' then fail() end
    if depth>60 then fail() end
    local mt=getmetatable(v)
    if mt==FLOAT_MT then
      local x=v.value
      if type(x)~='number' or x~=x or x==math.huge or x==-math.huge then fail() end
      return canon.float(x)
    end
    local kind
    if mt==ARRAY_MT then kind='array' elseif mt==OBJECT_MT then kind='object'
    elseif mt==nil then
      local count=0
      for _ in pairs(v) do count=count+1 end
      if count==0 then fail() end
      kind=(count==#v) and 'array' or 'object'
    else fail() end
    local out={}
    if kind=='array' then
      for i=1,#v do out[i]=copy(v[i],depth+1) end
      return canon.array(out)
    end
    for k,x in pairs(v) do
      if type(k)~='string' or not canon.valid_utf8(k) then fail() end
      out[k]=copy(x,depth+1)
    end
    return canon.object(out)
  end
  if type(value)~='table' then return nil end
  local ok,result=native_pcall(function()
    local out={}
    for key in pairs(keys) do
      local v=value[key]
      if v~=nil then out[key]=copy(v,1) end
    end
    return canon.object(out)
  end)
  if ok then return result end
  return nil
end

------------------------------------------------------------------------------------------------------
-- crash accounting
------------------------------------------------------------------------------------------------------
-- previous_end(d): the crash of a run that did not stop cleanly, counted at the next start. d: read(path),
-- remove(path), runtime, pid, record(message) -> count. Returns count (0 when nothing to count), message.
function M.previous_end(d)
  local watchdog_path,state_path=d.runtime..'/'..M.WATCHDOG,d.runtime..'/'..M.STATE
  local watchdog=d.read(watchdog_path)
  local state=d.read(state_path)
  local message=nil
  if watchdog then message='HV-CORE-WATCHDOG: '..string.sub(watchdog,1,500)
  elseif state then
    local pid=tonumber(string.match(state,'"pid":(%d+)'))
    if pid and pid~=d.pid then message='HV-CORE-UNCLEAN-END: pid '..pid..' ended without a clean stop' end
  end
  native_pcall(d.remove,watchdog_path);native_pcall(d.remove,state_path)
  if not message then return 0,nil end
  return d.record(message),message
end

------------------------------------------------------------------------------------------------------
-- the core: the Auto run's life, the heartbeat, counters
------------------------------------------------------------------------------------------------------
-- d (deps; tests replace it): loop {after, clock}, wall(), log(text), take_native_lock() -> lock|nil,
-- auto_env(core) -> env, auto_run(env) -> 'stopped'|'exit', record_crash(message) -> count,
-- fall_back(count, message), collect(), write_state(value), memory() -> table, pid,
-- monitor_age() -> seconds since the monitor's last published pass (or nil), kick_monitor().
local Core={}
Core.__index=Core
function M.core(d)
  return setmetatable({d=d,auto_state='STARTING',auto_runs=0,auto_restarts=0,auto_crashes=0,handler_errors=0,
    max_lag=0,max_step=0,stopping=false,started=d.wall(),started_clock=d.loop.clock()},Core)
end
function Core:log(text) self.d.log(text) end
function Core:handler_error(where,err)
  self.handler_errors=self.handler_errors+1
  self.last_handler_error=string.sub(tostring(where)..': '..tostring(err),1,500)
  self:log('handler error ('..tostring(where)..'): '..tostring(err))
end
function Core:start()
  self:beat()
  self:start_auto()
end
function Core:retry_auto()
  self.auto_retry=self.d.loop.after(M.RESTART_SECONDS*1000,function() self.auto_retry=nil;self:start_auto() end)
end
function Core:start_auto()
  if self.stopping or self.falling_back or self.auto_task then return end
  if not self.native_lock then
    local lock=self.d.take_native_lock()
    if not lock then
      if self.auto_state~='WAITING-LOCK' then self:log('NATIVE-SUPERVISOR-BUSY: the Auto supervisor waits for native.lock') end
      self.auto_state='WAITING-LOCK'
      self:retry_auto()
      return
    end
    self.native_lock=lock
  end
  local env=self.d.auto_env(self)
  self.auto_state='RUNNING';self.auto_runs=self.auto_runs+1
  local task
  task=M.task(function() return self.d.auto_run(env) end,self.d.loop,
    function(ok,result) self:auto_done(task,ok,result) end,
    function(seconds)
      if seconds>self.max_step then self.max_step=seconds end
      if seconds>=M.LAG_LOG_SECONDS then self:log(string.format('HV-CORE-AUTO-STEP: one Auto step held the loop %.1f s',seconds)) end
    end)
  self.auto_task=task
  task.step()
end
function Core:auto_done(task,ok,result)
  if task~=self.auto_task then return end
  self.auto_task=nil
  native_pcall(self.d.collect)  -- the ended run's open files (and the flocks they hold) close with it
  if self.stopping then self.auto_state='STOPPED';return end
  if ok then
    self.auto_state='RESTARTING'
    self:log('Auto supervisor run ended ('..tostring(result)..'); it starts again in '..M.RESTART_SECONDS..' s')
  else
    local message=type(result)=='table' and ('code '..tostring(result.code)) or tostring(result)
    self.auto_crashes=self.auto_crashes+1
    self.last_error=string.sub(message,1,2000)
    self:log('Auto supervisor error: '..message)
    local count=1
    local cok,value=native_pcall(self.d.record_crash,message)
    if cok and type(value)=='number' then count=value end
    if count>=M.FALLBACK_CRASHES then
      self.auto_state='FALLBACK';self.falling_back=true
      self.d.fall_back(count,message)
      return
    end
    self.auto_state='RESTARTING'
  end
  self.auto_restarts=self.auto_restarts+1
  self:retry_auto()
end
function Core:snapshot(now)
  local canon=require('canon')
  local mok,memory=native_pcall(self.d.memory)
  return canon.object({pid=self.d.pid,clock=canon.float(now),started=canon.float(self.started),auto=self.auto_state,
    auto_runs=self.auto_runs,auto_restarts=self.auto_restarts,auto_crashes=self.auto_crashes,handler_errors=self.handler_errors,
    last_handler_error=self.last_handler_error or canon.null,last_error=self.last_error or canon.null,
    max_loop_lag_s=canon.float(self.max_lag),max_auto_step_s=canon.float(self.max_step),locked_sleeps=M.locked_sleeps,
    memory=(mok and type(memory)=='table') and canon.object(memory) or canon.null})
end
-- beat(): every HEARTBEAT_SECONDS - the loop's lateness, the monitor's liveness, the state file (the watchdog's input)
function Core:beat()
  self.beat_handle=nil
  if self.stopping then return end
  local now=self.d.loop.clock()
  native_pcall(function()
    if self.expected then
      local lag=now-self.expected
      if lag>self.max_lag then self.max_lag=lag end
      if lag>=M.LAG_LOG_SECONDS then self:log(string.format('HV-CORE-LOOP-LAG: the event loop was %.1f s late',lag)) end
    end
    local age=self.d.monitor_age and self.d.monitor_age()
    if age and age>M.MONITOR_STALL_SECONDS and (not self.kicked or now-self.kicked>M.MONITOR_STALL_SECONDS) then
      self.kicked=now
      self:log(string.format('HV-CORE-MONITOR-STALLED: no monitor pass for %d s; starting one',math.floor(age)))
      self.d.kick_monitor()
    end
  end)
  native_pcall(self.d.write_state,self:snapshot(now))
  self.expected=now+M.HEARTBEAT_SECONDS
  self.beat_handle=self.d.loop.after(M.HEARTBEAT_SECONDS*1000,function() self:beat() end)
end
-- stop(sleep): procd's stop - the Auto run ends its pass and shuts down (real sleeps), nothing restarts
function Core:stop(sleep)
  self.stopping=true
  if self.auto_retry then self.auto_retry.cancel();self.auto_retry=nil end
  if self.beat_handle then self.beat_handle.cancel();self.beat_handle=nil end
  local task=self.auto_task
  if task and not task.done then task.drain(sleep) end
  self.auto_state='STOPPED'
end

------------------------------------------------------------------------------------------------------
-- standby (procd instance `native`): watchdog of hv-core and the separate Auto supervisor after a fallback
------------------------------------------------------------------------------------------------------
-- standby_step(state, d) -> 'exec' | 'wait' | 'term' | 'kill'. d: exists(path), read(path), clock(),
-- cmdline(pid) -> text|nil (NUL as spaces), kill(pid, signal), log(text), write(path, text), runtime.
function M.standby_step(state,d)
  if d.exists(d.runtime..'/'..M.FALLBACK) then return 'exec' end
  local text=d.read(d.runtime..'/'..M.STATE)
  local pid=text and tonumber(string.match(text,'"pid":(%d+)'))
  local clock=text and tonumber(string.match(text,'"clock":([-+%deE.]+)'))
  if not pid or not clock then return 'wait' end
  local now=d.clock()
  local age=now-clock
  if age<=M.WATCHDOG_SECONDS then state.killed=nil;return 'wait' end
  local command=d.cmdline(pid)
  if not command or not string.find(command,M.SCRIPT,1,true) or not string.find(command,'daemon',1,true) then return 'wait' end
  if not state.killed or state.killed.pid~=pid then
    d.log(string.format('HV-CORE-WATCHDOG: the event loop of hv-core pid %d has not run for %d s; ending it (procd restarts it)',pid,math.floor(age)))
    native_pcall(d.write,d.runtime..'/'..M.WATCHDOG,string.format('{"age":%d,"pid":%d,"uptime":%d}',math.floor(age),pid,math.floor(now)))
    d.kill(pid,15)
    state.killed={pid=pid,at=now,hard=false}
    return 'term'
  end
  if not state.killed.hard and now-state.killed.at>=M.KILL_GRACE then
    d.kill(pid,9);state.killed.hard=true
    return 'kill'
  end
  return 'wait'
end

local function uptime()
  local f=io.open('/proc/uptime','r')
  if not f then return os.time() end
  local text=f:read('*l');f:close()
  return tonumber(string.match(text or '','^([0-9.]+)')) or os.time()
end
local function syslog(line) os.execute("logger -t homensai-vpn '"..string.gsub(line,"[^%w%s:._()/,=-]",'').."'") end

function M.standby()
  local okn,nixio=pcall(require,'nixio')
  if not okn or type(nixio)~='table' then nixio=nil end
  local runtime='/var/run/homensai-vpn'
  local d={runtime=runtime,clock=uptime,log=syslog}
  function d.exists(path) local f=io.open(path,'rb');if f then f:close();return true end;return false end
  function d.read(path) local f=io.open(path,'rb');if not f then return nil end;local t=f:read(8192);f:close();return t end
  function d.cmdline(pid)
    local f=io.open('/proc/'..string.format('%d',pid)..'/cmdline','rb');if not f then return nil end
    local t=f:read(8192);f:close()
    return t and (string.gsub(t,'%z',' ')) or nil
  end
  function d.kill(pid,signal)
    if nixio and nixio.kill then nixio.kill(pid,signal) else os.execute('kill -'..string.format('%d',signal)..' '..string.format('%d',pid)) end
  end
  function d.write(path,text)
    local f=io.open(path..'.part','wb');if not f then return end
    f:write(text);f:close();os.rename(path..'.part',path)
  end
  local state={}
  while true do
    local ok,action=pcall(M.standby_step,state,d)
    if ok and action=='exec' then
      syslog('HV-CORE-FALLBACK: the standby becomes the Lua Auto supervisor (auto.lua daemon)')
      if nixio and nixio.exec then nixio.exec(M.AUTO_DAEMON[1],M.AUTO_DAEMON[2],M.AUTO_DAEMON[3]) end
      io.stderr:write('HV-CORE-STANDBY-EXEC-FAILED\n')
      os.exit(1)
    end
    if nixio and nixio.nanosleep then nixio.nanosleep(M.STANDBY_POLL,0) else os.execute('sleep '..M.STANDBY_POLL) end
  end
end

------------------------------------------------------------------------------------------------------
-- the daemon (router only; the PC tests drive M.core / M.task with fakes)
------------------------------------------------------------------------------------------------------
local function write_ram(path,text)
  local part=path..'.part'
  local f=io.open(part,'wb')
  if not f then return false end
  f:write(text);f:close()
  return os.rename(part,path)
end

-- the third crash: write the marker, release everything, become the separate Lua monitor (same pid)
function M.fall_back_exec(runtime,count,message,closers)
  local canon=require('canon')
  syslog('HV-CORE-FALLBACK: '..count..' hv-core errors in '..M.FALLBACK_WINDOW..' s; the Lua monitor and the Lua Auto supervisor run as separate processes')
  native_pcall(write_ram,runtime..'/'..M.FALLBACK,canon.encode(canon.object({code='HV-CORE-FALLBACK',crashes=count,
    last_error=string.sub(tostring(message),1,2000),time=canon.float(require('runner').wall())})))
  M.exec_monitor(runtime,closers)
end
-- exec_monitor(): release the locks and become `lua monitor.lua daemon` (same pid, procd's monitor instance)
function M.exec_monitor(runtime,closers)
  for _,close in ipairs(closers or {}) do native_pcall(close) end
  native_pcall(os.remove,runtime..'/'..M.STATE)
  local okn,nixio=pcall(require,'nixio')
  if okn and type(nixio)=='table' and nixio.exec then nixio.exec(M.MONITOR_DAEMON[1],M.MONITOR_DAEMON[2],M.MONITOR_DAEMON[3]) end
  io.stderr:write('HV-CORE-FALLBACK-FAILED\n')
  os.exit(1)
end

function M.daemon()
  local run=require('runner')
  local canon=require('canon')
  local runtime=run.RUNTIME
  if not canon.safe_directory(runtime) then error('runtime directory',0) end
  local function present(path) local f=io.open(path,'rb');if f then f:close();return true end;return false end
  -- a fallback in force (until the next service stop): the separate Lua monitor runs in this procd instance
  if present(runtime..'/'..M.FALLBACK) then M.exec_monitor(runtime,{}) end
  M.install_file_popen(runtime)
  local A=require('auto')
  local agent_file,agent_fd=A.hold_lock(runtime,'agent.lock')
  if not agent_file then io.stderr:write('HV-CORE-MONITOR-BUSY\n');os.exit(1) end
  local okn,nixio=pcall(require,'nixio')
  local pid=(okn and type(nixio)=='table' and nixio.getpid) and nixio.getpid() or 0
  local crashes=runtime..'/'..M.CRASHES
  local function record(message) return A.record_crash(run.fs,crashes,run.wall(),message) end
  local closers={function() agent_file:close() end}
  local count,message=M.previous_end({runtime=runtime,pid=pid,read=run.fs.read,remove=os.remove,record=record})
  if message then io.stderr:write(message,'\n') end
  if count>=M.FALLBACK_CRASHES then M.fall_back_exec(runtime,count,message,closers) end

  local core,handle
  local ok,err=xpcall(function()
    M.install_cooperative()
    local sys=require('sys')
    local mio=require('monitor_io')
    local ctl=require('auto_control')
    local control=require('control')
    M.cooperative_sleep(sys,function()
      return control.held_fd()~=nil or (mio.held_fd and mio.held_fd()~=nil) or (ctl.flock_held or 0)>0
    end)
    sys.close_fds={agent_fd}
    for _,directory in ipairs({'/etc/homensai-vpn','/etc/homensai-vpn/session-recovery'}) do pcall(sys.sweep_pending,directory) end
    local real=require('uloop')
    local function report(where,e)
      if core then core:handler_error(where,e) else io.stderr:write('hv-core: ',tostring(where),': ',tostring(e),'\n') end
    end
    local uloop=M.guarded_uloop(real,report)
    package.loaded['uloop']=uloop
    if mio.setup_timezone then mio.setup_timezone() end
    real.init()
    handle=require('monitor').start(mio,nil,{object=function(object,conn) M.guard_object(object,conn,report) end})
    local status_path=runtime..'/status.json'
    handle.monitor.on_status=function(status,text)
      if handle.monitor.runtime..'/status.json'~=status_path then return end
      local value=M.restore(status,ctl.STATUS_KEYS)
      if value then ctl.seed_resident(status_path,text,run.fs.key(status_path),value) end
    end
    local loop=M.loop(uloop,run.clock)
    local fallback=nil
    core=M.core({loop=loop,wall=run.wall,pid=pid,log=function(text) io.stderr:write('hv-core: ',text,'\n') end,
      take_native_lock=function()
        local file,fd=A.hold_native_lock(runtime)
        if not file then return nil end
        sys.close_fds={agent_fd,fd}
        closers[#closers+1]=function() file:close() end
        return {file=file,fd=fd}
      end,
      auto_env=function(c)
        pcall(function() require('platform').ALLOWED_STALE_LOCK=nil end)
        local backend=require('backend').new(sys)
        local env={run=run,backend=backend,runtime=runtime,persist='/etc/homensai-vpn',
          stop=function() return c.stopping end,sleep=function(s) sys.sleep(s) end,
          history_lock=ctl.flock_file,version=backend.VERSION}
        backend.bind(env)
        return env
      end,
      auto_run=function(env) return A.run_blocking(env) end,
      record_crash=record,
      fall_back=function(n,text) fallback={count=n,message=text};real.cancel() end,
      collect=function() collectgarbage('collect') end,
      write_state=function(value) write_ram(runtime..'/'..M.STATE,canon.encode(value)) end,
      memory=run.memory,
      monitor_age=function() return run.clock()-(handle.monitor.published_at or core.started_clock) end,
      kick_monitor=function() handle.kick() end})
    core:start()
    real.run()
    if fallback then
      -- the Auto run has ended (it crashed); the monitor saves its accounting, then both halves run separately
      pcall(function() handle.monitor:checkpoint() end)
      pcall(os.remove,handle.ready)
      pcall(function() handle.conn:close() end)
      M.fall_back_exec(runtime,fallback.count,fallback.message,closers)
    end
    -- procd's SIGTERM ended uloop.run(): the Auto run finishes its pass and shuts down, as `auto.lua daemon` did
    core:stop(function(s) M.real_sleep(s) end)
    pcall(os.remove,handle.ready)
    pcall(function() handle.conn:close() end)
  end,function(e) if type(e)=='table' then return e end;return debug.traceback(tostring(e),2) end)
  if not ok then
    local text=type(err)=='table' and ('code '..tostring(err.code)) or tostring(err)
    io.stderr:write('hv-core: ',text,'\n')
    local n=1
    pcall(function() n=record(text) end)
    pcall(os.remove,runtime..'/'..M.STATE)
    if n>=M.FALLBACK_CRASHES then
      if handle then pcall(function() handle.monitor:checkpoint() end);pcall(function() handle.conn:close() end) end
      M.fall_back_exec(runtime,n,text,closers)
    end
    for _,close in ipairs(closers) do pcall(close) end
    os.exit(1)
  end
  pcall(os.remove,runtime..'/'..M.STATE)
  for _,close in ipairs(closers) do pcall(close) end
end

local script=arg and arg[0]
if script and (script=='hv_core.lua' or string.match(script,'/hv_core%.lua$')) then
  if arg[1]=='daemon' then M.daemon()
  elseif arg[1]=='standby' then M.standby() end
end

return M
