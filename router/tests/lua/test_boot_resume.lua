-- boot_resume.lua: the owner's Start comes back after a power cut (owner decision 31.10.2026, soak trial).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local M=require('boot_resume')

local FALL={}
local function world(o)
  o=o or {}
  local files={};local clock=o.now or 1000;local mono=o.uptime or 60;local calls={start=0,fallback=0}
  if o.marker~=false then files['/etc/auto-resume.json']=M.marker(o.marker_time or 500) end
  if o.latch then files['/etc/native-stop.json']=canon.encode(canon.object({requested=canon.float(o.latch)})) end
  local intent=canon.object({mode='off'})
  local replies=o.replies or {canon.object({accepted=true,queued=true})}
  local ctx={read=function(p) return files[p] end,exists=function(p) return files[p]~=nil end,
    write_ram=function(p,text) files[p]=text end,now=function() return clock end,uptime=function() return mono end,
    runtime='/run',persist='/etc',FALLBACK=FALL,intent=function() return intent end,revision=function() return string.rep('a',32) end,
    start=function(arguments)
      calls.start=calls.start+1;calls.last=arguments
      local reply=replies[math.min(calls.start,#replies)]
      if canon.is_object(reply) and reply.accepted then intent=canon.object({mode='on'}) end
      return reply
    end,
    fallback=function() calls.fallback=calls.fallback+1 end}
  -- a supervisor restart: its recovery revoked the intent (fence) and then wrote a fresh token
  ctx.supervisor_start=function(id) intent=canon.object({mode='off'});files['/run/supervisor-start.json']=canon.encode(canon.object({id=id,time=canon.float(clock)})) end
  -- advance(s): both clocks; jump(s): the wall clock only (NTP after a boot without RTC)
  return ctx,files,calls,function(s) clock=clock+s;mono=mono+s end,function(s) clock=clock+s end
end
local function state(files) return canon.decode(files['/run/boot-resume.json']) end

t.test('owner Start before the cut: one programmatic Start after the boot, RESUMED',function()
  local ctx,files,calls=world()
  local r=M.new(ctx)
  t.eq(r.tick(),'RESUMED');t.eq(calls.start,1)
  t.eq(calls.last.request_source,'programmatic');t.eq(calls.last.control_revision,string.rep('a',32))
  t.eq(state(files).state,'RESUMED')
  t.eq(r.tick(),'RESUMED');t.eq(calls.start,1)
end)

t.test('Stop after the Start wins: SKIPPED, nothing pressed',function()
  local ctx,files,calls=world({latch=600})
  t.eq(M.new(ctx).tick(),'SKIPPED');t.eq(calls.start,0);t.eq(state(files).code,'AUTO-RESUME-STOPPED')
end)

t.test('an older Stop does not cancel a later Start',function()
  local ctx,files,calls=world({latch=400})
  t.eq(M.new(ctx).tick(),'RESUMED');t.eq(calls.start,1)
end)

t.test('no marker, a damaged marker, an unreadable latch: SKIPPED',function()
  local ctx,files,calls=world({marker=false});t.eq(M.new(ctx).tick(),'SKIPPED');t.eq(state(files).code,'AUTO-RESUME-NOT-REQUESTED')
  ctx,files,calls=world();files['/etc/auto-resume.json']='{broken';t.eq(M.new(ctx).tick(),'SKIPPED');t.eq(state(files).code,'AUTO-RESUME-MARKER-INVALID')
  ctx,files,calls=world();files['/etc/native-stop.json']='{';t.eq(M.new(ctx).tick(),'SKIPPED');t.eq(state(files).code,'AUTO-RESUME-STOP-UNREADABLE')
  t.eq(calls.start,0)
end)

t.test('once per boot and only soon after the boot',function()
  local ctx,files,calls=world({uptime=2000});t.eq(M.new(ctx).tick(),nil);t.eq(calls.start,0);t.eq(files['/run/boot-resume.json'],nil)
  ctx,files,calls=world();files['/run/boot-resume.json']='{}';t.eq(M.new(ctx).tick(),nil);t.eq(calls.start,0)
end)

t.test('a refusal waits and retries every 15 s; Start checks are never bypassed',function()
  local busy=canon.object({accepted=false,blockers=canon.array({'TRANSACTION-IN-PROGRESS'})})
  local ctx,files,calls,advance=world({replies={busy,busy,canon.object({accepted=true})}})
  local r=M.new(ctx)
  t.eq(r.tick(),'WAITING');t.eq(state(files).code,'TRANSACTION-IN-PROGRESS')
  advance(5);t.eq(r.tick(),'WAITING');t.eq(calls.start,1)
  advance(10);t.eq(r.tick(),'WAITING');t.eq(calls.start,2)
  advance(15);t.eq(r.tick(),'RESUMED');t.eq(calls.start,3)
end)

t.test('FALLBACK hands Start to agent.py; the intent turning on ends as RESUMED',function()
  local ctx,files,calls,advance=world({replies={FALL}})
  local r=M.new(ctx)
  t.eq(r.tick(),'WAITING');t.eq(calls.fallback,1);t.eq(state(files).code,'AGENT-START')
  ctx.intent=function() return canon.object({mode='on'}) end
  advance(15);t.eq(r.tick(),'RESUMED');t.eq(calls.start,1)
end)

t.test('a final refusal, or the window (10 min, and never before 15 min of uptime), ends as FAILED',function()
  local bad=canon.object({accepted=false,blockers=canon.array({'JOURNAL-INTEGRITY-FAILED'})})
  local ctx,files=world({replies={bad}});t.eq(M.new(ctx).tick(),'FAILED');t.eq(state(files).code,'JOURNAL-INTEGRITY-FAILED')
  local busy=canon.object({accepted=false,blockers=canon.array({'PAIR-RECOVERY-REQUIRED'})})
  -- first attempt at uptime 60: retried until uptime 900 (840 s), then FAILED
  local ctx2,files2,calls2,advance=world({replies={busy}})
  local r=M.new(ctx2)
  r.tick()
  for _=1,55 do advance(15);r.tick() end  -- uptime 885
  t.eq(state(files2).state,'WAITING','still retrying before 15 min of uptime')
  for _=1,2 do advance(15);r.tick() end   -- uptime 915
  t.eq(state(files2).state,'FAILED');t.eq(state(files2).code,'PAIR-RECOVERY-REQUIRED')
  -- a monitor started late in the boot window still gets the full 10 min
  local ctx3,files3,_,advance3=world({replies={busy},uptime=800})
  local r3=M.new(ctx3)
  r3.tick()
  for _=1,39 do advance3(15);r3.tick() end  -- 585 s after the first attempt
  t.eq(state(files3).state,'WAITING')
  for _=1,2 do advance3(15);r3.tick() end
  t.eq(state(files3).state,'FAILED')
end)

t.test('a forward NTP step of the wall clock right after the boot does not end the window (no RTC)',function()
  local busy=canon.object({accepted=false,blockers=canon.array({'TRANSACTION-IN-PROGRESS'})})
  local ctx,files,calls,advance,jump=world({replies={busy,busy,busy,busy,busy,canon.object({accepted=true})}})
  local r=M.new(ctx)
  t.eq(r.tick(),'WAITING')
  jump(3*3600)          -- chrony: "time sync success" - wall +3 h, uptime unchanged
  t.eq(r.tick(),'WAITING');t.eq(calls.start,1,'the pacing is monotonic too: no extra attempt from the jump')
  for _=1,5 do advance(15);r.tick() end
  t.eq(state(files).state,'RESUMED');t.eq(calls.start,6)
  t.truthy(canon.number(state(files).time)>=1000+3*3600,'the published time is the wall clock')
  -- a backward step does not stall the pacing either
  local ctx2,files2,calls2,advance2,jump2=world({replies={busy,canon.object({accepted=true})}})
  local r2=M.new(ctx2)
  r2.tick();jump2(-3600);advance2(15)
  t.eq(r2.tick(),'RESUMED');t.eq(calls2.start,2)
end)

------------------------------------------------------------------------------------------------------
-- Owner decision extension 31.10.2026: an unintended supervisor restart (kill -9, crash) without a reboot
------------------------------------------------------------------------------------------------------
local T1,T2,T3,T4,T5=string.rep('1',32),string.rep('2',32),string.rep('3',32),string.rep('4',32),string.rep('5',32)

t.test('supervisor killed in idle: its recovery revoked the intent; the monitor resumes once per supervisor start',function()
  local ctx,files,calls,advance=world()
  ctx.supervisor_start(T1)
  local r=M.new(ctx)
  t.eq(r.tick(),'RESUMED');t.eq(calls.start,1);t.eq(state(files).supervisor,T1);t.eq(state(files).trigger,'boot')
  advance(3600)
  t.eq(r.tick(),'RESUMED');t.eq(calls.start,1,'the same supervisor start is never resumed twice')
  ctx.supervisor_start(T2)            -- kill -9 in idle, procd restart, recovery fenced the intent
  t.eq(r.tick(),'RESUMED');t.eq(calls.start,2)
  t.eq(state(files).trigger,'supervisor-restart');t.eq(state(files).supervisor,T2)
  t.eq(calls.last.request_source,'programmatic')
  advance(15);t.eq(r.tick(),'RESUMED');t.eq(calls.start,2)
end)

t.test('supervisor killed after a deliberate Stop: Auto stays off',function()
  local ctx,files,calls,advance=world()
  ctx.supervisor_start(T1)
  local r=M.new(ctx)
  t.eq(r.tick(),'RESUMED')
  advance(60);files['/etc/native-stop.json']=canon.encode(canon.object({requested=canon.float(1060)}))  -- the owner's Stop
  ctx.supervisor_start(T2)
  t.eq(r.tick(),'SKIPPED');t.eq(state(files).code,'AUTO-RESUME-STOPPED');t.eq(calls.start,1)
end)

t.test('a restart long after the boot is resumed too; a refusal retries in the monotonic window',function()
  local busy=canon.object({accepted=false,blockers=canon.array({'PAIR-RECOVERY-REQUIRED'})})
  local ctx,files,calls,advance=world({uptime=50000,replies={busy,canon.object({accepted=true})}})
  local r=M.new(ctx)
  t.eq(r.tick(),nil,'an old boot is not resumed');t.eq(calls.start,0)
  ctx.supervisor_start(T1)
  t.eq(r.tick(),'WAITING');advance(15);t.eq(r.tick(),'RESUMED');t.eq(calls.start,2)
  -- a restart whose Start keeps being refused ends FAILED after WINDOW (no uptime extension after the boot)
  local ctx2,files2,calls2,advance2=world({uptime=50000,replies={busy}})
  local r2=M.new(ctx2);r2.tick();ctx2.supervisor_start(T1);r2.tick()
  for _=1,40 do advance2(15);r2.tick() end
  t.eq(state(files2).state,'WAITING')
  for _=1,2 do advance2(15);r2.tick() end
  t.eq(state(files2).state,'FAILED')
end)

t.test('a restarted monitor: the token its boot decision handled is not resumed again, a newer one is',function()
  local ctx,files,calls=world()
  ctx.supervisor_start(T1)
  files['/run/boot-resume.json']=canon.encode(canon.object({state='RESUMED',supervisor=T1}))
  local r=M.new(ctx)
  ctx.intent=function() return canon.object({mode='on'}) end
  t.eq(r.tick(),nil);t.eq(calls.start,0)
  local ctx2,files2,calls2=world();files2['/run/boot-resume.json']=canon.encode(canon.object({state='RESUMED',supervisor=T1}))
  ctx2.supervisor_start(T2)
  local r2=M.new(ctx2)
  t.eq(r2.tick(),nil)
  t.eq(r2.tick(),'RESUMED');t.eq(calls2.start,1)
end)

t.test('a crash loop is bounded: at most RESTART_LIMIT resumes per RESTART_WINDOW',function()
  local ctx,files,calls,advance=world()
  local r=M.new(ctx)
  t.eq(r.tick(),'RESUMED')
  for i,id in ipairs({T1,T2,T3}) do advance(10);ctx.supervisor_start(id);t.eq(r.tick(),'RESUMED','restart '..i) end
  advance(10);ctx.supervisor_start(T4)
  t.eq(r.tick(),'FAILED');t.eq(state(files).code,'AUTO-RESUME-RESTART-LIMIT');t.eq(calls.start,4)
  advance(M.RESTART_WINDOW);ctx.supervisor_start(T5)
  t.eq(r.tick(),'RESUMED');t.eq(calls.start,5,'the window passed')
end)

t.run()
