-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- boot_resume.lua: Auto that the owner switched on comes back by itself after a power cut or reboot.
--
-- Owner decision 31.10.2026 (soak trial: after sysrq-b Auto stayed off, the tunnels down and the LAN without
-- internet until somebody pressed Start). The owner's own Start leaves a durable marker on flash
-- (auto-resume.json); Stop and every give-up leave the stop latch native-stop.json, which is newer and wins.
-- After a boot the monitor presses Start once for the owner, with the same request and every check Start has
-- (journal, preparation, pair state): nothing else is bypassed. Programmatic and test starts leave no marker.
--
-- Owner decision extension 31.10.2026 (soak: kill -9 of the idle Lua supervisor; procd restarted it, its
-- recovery revoked the intent and Auto stayed off until somebody pressed Start): an unintended supervisor restart
-- without a reboot is treated like a power cut. Every supervisor start that finished its recovery writes a fresh
-- token (RAM supervisor-start.json); a token this monitor has not handled yet starts the same resume once more -
-- the same marker/stop-latch decision (a deliberate Stop or give-up is newer and wins), every Start check, the
-- monotonic window - bounded to RESTART_LIMIT resumes per RESTART_WINDOW against a crash loop.
--
-- 01.11.2026 (BOOT-RECOVERY-2026-11-01.ru.md, power-cut soak alpha21/alpha24): (1) attempts every EVERY=5 s instead
-- of 15 s - a refused Start is a read under the lock, and the supervisor finishes its recovery at an unknown moment
-- (Start was accepted 12-15 s after it); a Start handed to agent.py still waits FALLBACK_EVERY. (2) The marker and the
-- stop latch are read again before every attempt: a Stop pressed during the boot window wins at once. (3) An accepted
-- Start is watched for START_WATCH s: when the pair start it queued fails (the intent row says failed_request_id =
-- that request, e.g. the vendor still rebuilding right after the boot) the same Start is pressed again, at most
-- START_RETRIES times, inside the same window and with every check. Before, Auto stayed off after such a failure until
-- somebody pressed Start (soak: idle cuts, 495 s with the bench's Start at 240 s).
-- Python counterpart: boot_resume.py (same marker, same decision, same state file).
local canon=require('canon')

local M={}
M.MARKER='auto-resume.json'     -- persist: {enabled=true,time=<owner Start>,request_source='manual'}
M.STATE='boot-resume.json'      -- runtime (RAM): what this boot decided, for the page and the soak bench
M.WINDOW=600                    -- at least this many seconds after the first attempt; later refusals end as FAILED
M.UNTIL_UPTIME=900              -- and never before 15 min of uptime: a held/committed journal after a cut is
                                -- settled by the supervisor's pair cleanup (~1-2 min after the tunnels are up)
M.EVERY=5                       -- seconds between attempts (15 before 01.11.2026)
M.FALLBACK_EVERY=15             -- after a Start handed to agent.py (a Python process; never two at once)
M.START_WATCH=240               -- an accepted Start is watched this long (pair begin: ifup -w + vendor quiet, bounded)
M.START_RETRIES=2               -- accepted Starts whose pair start failed that are pressed again (per resume)
M.BOOT_AGE=900                  -- only a monitor started within 15 min of the boot resumes the boot itself
M.SUPERVISOR='supervisor-start.json'  -- runtime: {id=<hex32>,time=} written by each supervisor start after recovery
M.RESTART_LIMIT=3               -- resumes after supervisor restarts within RESTART_WINDOW (monotonic seconds)
M.RESTART_WINDOW=900
M.RETRY={['TRANSACTION-IN-PROGRESS']=true,['PAIR-RECOVERY-REQUIRED']=true,['START-STATE-UNVERIFIED']=true,
  ['CONTROL-REVISION-STALE']=true,['PAIR-STATE-UNVERIFIED']=true,['JOURNAL-INTEGRITY-FAILED']=false}

function M.marker(now)
  return canon.encode(canon.object({enabled=true,time=canon.float(now),request_source='manual'}))
end

-- read(path) -> text|nil. Returns true, or false and the reason.
function M.wanted(read,persist)
  local text=read(persist..'/'..M.MARKER)
  if text==nil then return false,'AUTO-RESUME-NOT-REQUESTED' end
  local ok,marker=pcall(canon.decode,text)
  local at=ok and canon.is_object(marker) and marker.enabled==true and canon.number(marker.time) or nil
  if not at then return false,'AUTO-RESUME-MARKER-INVALID' end
  local latch=read(persist..'/native-stop.json')
  if latch~=nil then
    local lok,row=pcall(canon.decode,latch)
    if not lok or not canon.is_object(row) then return false,'AUTO-RESUME-STOP-UNREADABLE' end
    local stopped=canon.number(row.requested)
    if stopped==nil or stopped>=at then return false,'AUTO-RESUME-STOPPED' end
  end
  return true
end

-- token(read,runtime) -> the id of the supervisor start that finished its recovery, or nil
function M.token(read,runtime)
  local text=read(runtime..'/'..M.SUPERVISOR)
  if text==nil then return nil end
  local ok,row=pcall(canon.decode,text)
  local id=ok and canon.is_object(row) and row.id or nil
  if type(id)~='string' or not string.find(id,'^[0-9a-f]+$') or #id~=32 then return nil end
  return id
end

-- ctx: read, write_ram(path,text), exists(path), now(), uptime(), runtime, persist, intent() -> pair intent,
--      revision() -> control revision, start(arguments) -> reply | ctx.FALLBACK, fallback(arguments) (agent.py)
--      optional clock() -> monotonic seconds (default: uptime())
-- The window and the pacing run on the monotonic clock: the router has no RTC, NTP steps the wall clock forward
-- right after the boot (power-cut soak 31.10.2026: "time sync success via chrony" ended the old wall-clock window
-- after 4 attempts). now() is only the published time.
function M.new(ctx)
  local self={state=nil,first=nil,next_at=0,done=false,attempts=0,deadline=nil,token=nil,restart=false,restarts={},checked=false,
    watch_until=nil,request=nil,failed_starts=0}
  local source=nil
  local function clock()
    if source==nil then
      -- chosen once: a monotonic source that fails later is never mixed with the wall clock
      local candidate=ctx.clock or ctx.uptime
      local ok,value=pcall(candidate or error)
      source=(ok and type(value)=='number') and candidate or ctx.now
    end
    local ok,value=pcall(source)
    if ok and type(value)=='number' then return value end
    return self.first or 0  -- a failed read never advances the window
  end
  local function current_token() local ok,id=pcall(M.token,ctx.read,ctx.runtime);return ok and id or nil end
  local function publish(state,code)
    self.state=state
    local row=canon.object({state=state,code=code==nil and canon.null or code,attempts=self.attempts,time=canon.float(ctx.now()),
      trigger=self.restart and 'supervisor-restart' or 'boot',supervisor=self.token==nil and canon.null or self.token})
    pcall(ctx.write_ram,ctx.runtime..'/'..M.STATE,canon.encode(row))
  end
  local function finish(state,code) self.watch_until=nil;publish(state,code);self.done=true;return self.state end
  -- an accepted Start: remember the request it queued (the intent row id) and watch it
  local function watch_start(intent)
    self.request=(canon.is_object(intent) and type(intent.id)=='string') and intent.id or nil
    self.watch_until=clock()+M.START_WATCH
    publish('RESUMED',nil)
    return self.state
  end
  -- a state when this tick ends here; nil when the watch is over (done) and the tick goes on as before
  local function watching()
    local iok,intent=pcall(ctx.intent)
    local row=iok and canon.is_object(intent) and intent or nil
    if row and row.mode=='off' and self.request~=nil and row.failed_request_id==self.request then
      -- the pair start of our accepted Start failed: press Start again (bounded, same window, every check)
      self.watch_until=nil;self.request=nil;self.failed_starts=self.failed_starts+1
      self.last_code=type(row.failure_code)=='string' and row.failure_code or 'AUTO-RESUME-START-FAILED'
      if self.failed_starts>M.START_RETRIES then return finish('FAILED',self.last_code) end
      self.next_at=clock()+M.EVERY
      publish('WAITING',self.last_code)
      return self.state
    end
    -- still running (or the intent briefly unreadable) inside the watch: nothing to do
    if (row==nil or row.mode=='on') and clock()<self.watch_until then return self.state end
    finish('RESUMED')  -- ran long enough, or a Stop / supervisor restart (the latter handled below as before)
    return nil
  end
  -- a decision about the boot already exists (a restarted monitor) or the boot is old: watch supervisor restarts only
  local function watch_only(token) self.token=token;self.done=true;return nil end
  function self.tick()
    if not self.done and self.watch_until~=nil then
      local stop=watching()
      if stop~=nil then return stop end
    end
    if self.done then
      local token=current_token()
      if token==nil or token==self.token then return self.state end
      -- a supervisor start this monitor has not handled: the owner's Auto comes back after an unintended restart
      local now=clock()
      local kept={};for _,t in ipairs(self.restarts) do if now-t<M.RESTART_WINDOW then kept[#kept+1]=t end end
      self.restarts=kept
      self.token=token;self.restart=true;self.first=nil;self.attempts=0;self.last_code=nil;self.next_at=0;self.done=false
      self.request=nil;self.failed_starts=0
      if #kept>=M.RESTART_LIMIT then return finish('FAILED','AUTO-RESUME-RESTART-LIMIT') end
      kept[#kept+1]=now
    end
    if self.first==nil then
      if not self.restart then
        -- once per boot: a restarted monitor finds this boot's decision in RAM; an old boot is never resumed
        local uptime=ctx.uptime() or math.huge
        if ctx.exists(ctx.runtime..'/'..M.STATE) then
          local ok,row=pcall(canon.decode,ctx.read(ctx.runtime..'/'..M.STATE) or '')
          local handled=ok and canon.is_object(row) and type(row.supervisor)=='string' and row.supervisor or nil
          return watch_only(handled)
        end
        if uptime>M.BOOT_AGE then return watch_only(current_token()) end
        self.token=current_token()
        local ok,reason=M.wanted(ctx.read,ctx.persist)
        if not ok then return finish('SKIPPED',reason) end
        local now=clock()
        self.first=now
        self.deadline=now+math.max(M.WINDOW,M.UNTIL_UPTIME-uptime)
      else
        local ok,reason=M.wanted(ctx.read,ctx.persist)
        if not ok then return finish('SKIPPED',reason) end
        local now=clock()
        self.first=now
        self.deadline=now+M.WINDOW
      end
    end
    local now=clock()
    if now<self.next_at then return self.state end
    self.next_at=now+M.EVERY
    local token=current_token()
    if token~=nil then self.token=token end  -- a supervisor restart during this run is served by this run
    local iok,intent=pcall(ctx.intent)
    if iok and canon.is_object(intent) and intent.mode=='on' then
      if self.attempts>0 then return watch_start(intent) end  -- e.g. the Start handed to agent.py went through
      return finish('RUNNING')
    end
    if now>self.deadline then return finish('FAILED',self.last_code or 'AUTO-RESUME-TIMEOUT') end
    -- the owner's Stop (or a give-up) during the window is newer than the marker and wins before every attempt
    local wok,wanted,why=pcall(M.wanted,ctx.read,ctx.persist)
    if not wok then wanted,why=false,'AUTO-RESUME-STOP-UNREADABLE' end
    if not wanted then return finish('SKIPPED',why) end
    local rok,revision=pcall(ctx.revision)
    if not rok then self.last_code='CONTROL-REVISION-STALE';publish('WAITING',self.last_code);return self.state end
    local arguments=canon.object({control_revision=revision,request_source='programmatic'})
    self.attempts=self.attempts+1
    local sok,reply=pcall(ctx.start,arguments)
    if sok and reply==ctx.FALLBACK then
      -- Start would first repair the router preparation (or a lock is busy): agent.py does it, as for a click
      self.next_at=now+M.FALLBACK_EVERY
      pcall(ctx.fallback,arguments);publish('WAITING','AGENT-START');return self.state
    end
    if sok and canon.is_object(reply) and reply.accepted==true then
      local rok,row=pcall(ctx.intent)
      return watch_start(rok and row or nil)
    end
    local code=sok and canon.is_object(reply) and type(reply.blockers)=='table' and reply.blockers[1] or 'AUTO-RESUME-UNCONFIRMED'
    self.last_code=code
    if M.RETRY[code]==false then return finish('FAILED',code) end
    publish('WAITING',code)
    return self.state
  end
  return self
end

return M
