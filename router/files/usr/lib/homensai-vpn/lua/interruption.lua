-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- interruption.lua: why the service is starting - one code per start (owner request 01.11.2026: every way the router
-- can be cut off or lose power gets its own code, in the code table, the live log and the events).
--
-- The supervisor (auto.lua recover / native_switch.serve) calls start() once, before its recovery changes anything,
-- and mark_running() when its recovery is finished. The separate monitor process (monitor.lua run / agent.py
-- monitor_loop) calls monitor_start() once. Facts used, all of them existing or tiny:
--   <persist>/service-run.json      {state=starting|running|stopped,time}: 'stopped' is written by the init script's
--                                   stop_service (one small write per stop), 'starting' by a start, 'running' when the
--                                   recovery finished. Written only when the state changes: a crash loop writes nothing.
--   <runtime>/supervisor-run.json   RAM, gone after a boot: absent = the first supervisor start of this boot
--   <runtime>/monitor-run.json      RAM, the same for the monitor process
--   <runtime>/service-stop.flag     mtime: touched by every stop_service (a stop happened since the last start)
--   the journal phase (native-transaction.json), the Auto intent (RAM pair-auto-control.json, or after a boot the
--   owner's auto-resume.json marker unless the stop latch native-stop.json is newer - boot_resume's decision)
--   /proc/uptime                    only reported (the RAM markers tell a fresh boot exactly)
-- Every start writes one 'homensai-vpn' system log line '<CODE>: <text> (...)' and one history event (state = code),
-- so the code shows in "Events and errors" and in the live log. Process restarts are recorded at most LIMIT times
-- per WINDOW seconds of uptime (a crash loop only logs). Python counterpart: interruption.py (same files, decision,
-- lines). Shared cases: router/tests/interruption_cases.json.
local canon=require('canon')

local M={}
M.MARKER='service-run.json'
M.SUPERVISOR='supervisor-run.json'
M.MONITOR='monitor-run.json'
M.STOP_FLAG='service-stop.flag'
M.LIMIT=3
M.WINDOW=600
M.SWITCH={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true}
M.HOLD={['HELD-ON-RESERVE']=true,COMMITTED=true}
M.TEXT={
  ['RESTART-CLEAN']='clean reboot or service stop and start, not an interruption',
  ['RESTART-FIRST-START']='no record of the previous run (first start after install or upgrade), not an interruption',
  ['RESTART-PROCESS']='the process ended without a service stop and procd restarted it (crash or kill)',
  ['RESTART-INTERRUPTED-BOOT']='power lost or the router hung while booting: the previous start never finished its recovery',
  ['RESTART-INTERRUPTED-SWITCH']='power lost during a channel switch; the recovery rolls the switch back',
  ['RESTART-INTERRUPTED-RESERVE-HOLD']='power lost while the reserve channel was held',
  ['RESTART-INTERRUPTED-OPERATION']='power lost during normal operation with Auto on',
  ['RESTART-INTERRUPTED-AUTO-OFF']='power lost while Auto was off',
  -- GL-SENSORS-2026-11-04 item 5 (boot_cause.lua): a reboot by the GL timer and a kernel crash are no power cut
  ['RESTART-PLANNED-REBOOT']='planned reboot by the router timer (gl_timer), not an interruption',
  ['RESTART-KERNEL-CRASH']='the router kernel crashed (a new record in the GL crash log): not a power cut',
}
M.REASONS={reboot=true,['planned-reboot']=true}

local function decode(text)
  if type(text)~='string' then return nil end
  local ok,row=pcall(canon.decode,text)
  if ok and canon.is_object(row) then return row end
  return nil
end
local function int(v) local n=canon.number(v);if n==nil then return nil end;return math.floor(n) end

-- previous(text) -> 'stopped'|'starting'|'running'|nil (no file)|'invalid'
function M.previous(text)
  if text==nil then return nil end
  local row=decode(text)
  local state=row and row.state
  if state=='stopped' or state=='starting' or state=='running' then return state end
  return 'invalid'
end

-- previous_reason(text): the shutdown reason stored with 'stopped' (system shutdown only), else nil
function M.previous_reason(text)
  local row=decode(text)
  if not row or row.state~='stopped' then return nil end
  if type(row.reason)=='string' and M.REASONS[row.reason] then return row.reason end
  return nil
end

-- auto_on(read, runtime, persist): the Auto intent of the run that ended
function M.auto_on(read,runtime,persist)
  local intent=decode(read(runtime..'/pair-auto-control.json'))
  if intent and intent.mode=='on' then return true end
  local marker=decode(read(persist..'/auto-resume.json'))
  local at=marker and marker.enabled==true and canon.number(marker.time) or nil
  if not at then return false end
  local text=read(persist..'/native-stop.json')
  if text~=nil then
    local latch=decode(text)
    local stopped=latch and canon.number(latch.requested)
    if stopped==nil or stopped>=at then return false end
  end
  return true
end

-- classify(facts) -> code. facts: fresh (no RAM marker of this boot), previous, stopped_since (the stop flag changed
-- since the previous start of this boot), phase, auto_on
function M.classify(f)
  if not f.fresh then
    if f.previous=='stopped' or f.stopped_since then return 'RESTART-CLEAN' end
    return 'RESTART-PROCESS'
  end
  if f.previous=='stopped' then
    if f.reason=='planned-reboot' then return 'RESTART-PLANNED-REBOOT' end
    return 'RESTART-CLEAN'
  end
  if f.previous==nil then return 'RESTART-FIRST-START' end
  if f.crash then return 'RESTART-KERNEL-CRASH' end
  if M.SWITCH[f.phase] then return 'RESTART-INTERRUPTED-SWITCH' end
  if f.previous=='starting' then return 'RESTART-INTERRUPTED-BOOT' end
  if M.HOLD[f.phase] then return 'RESTART-INTERRUPTED-RESERVE-HOLD' end
  if f.auto_on then return 'RESTART-INTERRUPTED-OPERATION' end
  return 'RESTART-INTERRUPTED-AUTO-OFF'
end

local function uptime_text(up) return up and string.format('%.0f',up) or 'unknown' end

-- the RAM marker of a process: {time, stop=<stop flag mtime seen at this start>, restarts=[uptimes]}; returns
-- fresh, stopped_since, recorded (inside the process-restart limit), and writes the new marker
local function ram_marker(ctx,path,restart_code_of)
  local text=ctx.read(path)
  local row=decode(text) or canon.object({})
  local stop=int(ctx.mtime(ctx.runtime..'/'..M.STOP_FLAG))
  local fresh=text==nil
  local stopped_since=not fresh and stop~=int(row.stop)
  local code=restart_code_of(fresh,stopped_since)
  local up=ctx.uptime()
  local kept={}
  if type(row.restarts)=='table' then
    for _,t in ipairs(row.restarts) do
      local n=canon.number(t)
      if n and up and up-n<M.WINDOW and n<=up then kept[#kept+1]=canon.float(n) end
    end
  end
  local recorded=true
  if code=='RESTART-PROCESS' then
    if #kept>=M.LIMIT then recorded=false elseif up then kept[#kept+1]=canon.float(up) end
  end
  pcall(ctx.write_ram,path,canon.encode(canon.object({time=canon.float(ctx.now()),stop=stop==nil and canon.null or stop,
    restarts=canon.array(kept)})))
  return code,fresh,stopped_since,recorded,up
end

local function emit(ctx,code,line,recorded)
  if not recorded then line=line..'; not saved to the history (restart limit)' end
  pcall(ctx.log,line)
  if recorded and ctx.record then pcall(ctx.record,code) end
end

-- start(ctx, phase) -> handle {code, persisted, facts}. ctx: read(path)->text|nil, mtime(path)->number|nil,
-- write_ram(path,text), write_persist(path,text), now(), uptime()->number|nil, log(line), record(code), stopping(),
-- runtime, persist
function M.start(ctx,phase)
  local persist_path=ctx.persist..'/'..M.MARKER
  local previous_text=ctx.read(persist_path)
  local previous=M.previous(previous_text)
  local facts={previous=previous,phase=type(phase)=='string' and phase or nil,reason=M.previous_reason(previous_text),crash=false}
  local aok,on=pcall(M.auto_on,ctx.read,ctx.runtime,ctx.persist)
  facts.auto_on=aok and on==true
  local code,fresh,stopped_since,recorded,up=ram_marker(ctx,ctx.runtime..'/'..M.SUPERVISOR,function(fresh,since)
    facts.fresh=fresh;facts.stopped_since=since
    -- the first start of a boot only: the crash verdict of the boot that ended (boot_cause.evaluate)
    if fresh and ctx.crash then
      local ok,verdict=pcall(ctx.crash)
      facts.crash=ok and verdict=='crash'
    end
    return M.classify(facts)
  end)
  facts.uptime=up
  -- 'starting' marks a recovery in progress; a process restart keeps the state of the run it continues
  local persisted=previous
  if not (previous=='starting' or (not fresh and previous=='running')) then
    if pcall(ctx.write_persist,persist_path,canon.encode(canon.object({state='starting',time=canon.float(ctx.now())}))) then persisted='starting' end
  end
  emit(ctx,code,code..': '..M.TEXT[code]..' (journal '..(facts.phase or 'none')..', Auto '..(facts.auto_on and 'on' or 'off')..
    ', uptime '..uptime_text(up)..' s)',recorded)
  return {code=code,persisted=persisted,facts=facts}
end

-- mark_running(ctx, handle): the recovery is finished (steady state); a stop that came meanwhile keeps 'stopped'
function M.mark_running(ctx,handle)
  if type(handle)~='table' or handle.persisted=='running' then return false end
  if ctx.stopping and ctx.stopping() then return false end
  local path=ctx.persist..'/'..M.MARKER
  local ok=pcall(ctx.write_persist,path,canon.encode(canon.object({state='running',time=canon.float(ctx.now())})))
  if ok then handle.persisted='running' end
  -- the init script's stop wrote 'stopped' between the check and the write: put it back
  if ok and ctx.stopping and ctx.stopping() then
    pcall(ctx.write_persist,path,canon.encode(canon.object({state='stopped',time=canon.float(ctx.now())})))
    handle.persisted='stopped'
  end
  return ok
end

-- monitor_start(ctx) -> 'RESTART-PROCESS' when the monitor process was restarted without a service stop, else nil
function M.monitor_start(ctx)
  local code,_,_,recorded,up=ram_marker(ctx,ctx.runtime..'/'..M.MONITOR,function(fresh,since)
    if not fresh and not since then return 'RESTART-PROCESS' end
    return nil
  end)
  if code==nil then return nil end
  emit(ctx,code,code..': the monitor process ended without a service stop and procd restarted it (uptime '..uptime_text(up)..' s)',recorded)
  return recorded and code or nil
end

-- context(runtime, persist, options): the router functions (nixio, durable.lua, /proc/uptime)
function M.context(runtime,persist,options)
  options=options or {}
  local durable=require('durable')
  local ctx={runtime=runtime,persist=persist,record=options.record,stopping=options.stopping}
  function ctx.read(path)
    local f=io.open(path,'rb');if not f then return nil end
    local text=f:read('*a');f:close();return text
  end
  function ctx.mtime(path)
    local ok,fs=pcall(require,'nixio.fs')
    if ok and type(fs)=='table' and fs.stat then local m=fs.stat(path,'mtime');return type(m)=='number' and m or nil end
    local p=io.popen('date -r '..path..' +%s 2>/dev/null');if not p then return nil end
    local out=p:read('*a');p:close();return tonumber(string.match(out or '','^(%d+)'))
  end
  function ctx.write_ram(path,text) durable.write(path,text,{sync=false}) end
  function ctx.write_persist(path,text) durable.write(path,text) end
  ctx.now=options.now or os.time
  function ctx.uptime() local text=ctx.read('/proc/uptime');return text and tonumber(string.match(text,'^(%S+)')) or nil end
  ctx.log=options.log or durable.log
  function ctx.crash()
    local ok,nfs=pcall(require,'nixio.fs')
    return require('boot_cause').evaluate(persist,{write=ctx.write_persist,list_dir=function(path)
      local names={}
      if not (ok and type(nfs)=='table' and nfs.dir) then return names end
      local dok,iterator=pcall(nfs.dir,path)
      if dok and iterator then for name in iterator do names[#names+1]=name end end
      return names
    end})
  end
  return ctx
end

return M
