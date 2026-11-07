-- BH3-03 (bug hunt third pass, 07.11.2026): a backward wall-clock step no longer blocks every failover. Twin of
-- tests/test_budget_clock.py over the same tests/budget_clock_cases.json: pair.charge_clock gives the stamps budget()
-- sees (monotonic age of a charge noted in this boot; a stamp more than CLOCK_SKEW s in the future without a note counts
-- as old as the current uptime); charge_attempt/ledger_charge note the uptime second of each charge in RAM.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local DATA=canon.decode(read_file(t.here..'/../budget_clock_cases.json'))
local BOOT=DATA.boot
local SPACING=canon.number(DATA.spacing)
local function nums(list)
  local out={}
  for i,x in ipairs(list or {}) do local v=canon.number(x);if v==nil then out[i]=x else out[i]=v end end
  return canon.array(out)
end
local function floats(list) local out={};for i,x in ipairs(list) do out[i]=canon.float(x) end;return canon.array(out) end
local function spacing_met(effective,now)
  local events=pair.budget(effective,now,900,3)
  return #events==0 or now-canon.number(events[#events])>=SPACING
end
local function timeline(case,t_)
  local stamp=canon.number(case.stamp)
  local now=stamp-canon.number(case.behind)+t_
  local record,uptime
  if case.mode=='same_boot' then
    record=canon.object({boot=BOOT,at=canon.array({canon.array({canon.float(stamp),canon.float(canon.number(case.start))})})})
    uptime=canon.number(case.start)+t_
  else
    record=canon.object({});uptime=canon.number(case.start)+t_
  end
  return pair.charge_clock(floats({stamp}),record,now,uptime,BOOT),now
end

t.test('constants and the default spacing',function()
  t.eq({pair.CLOCK_SKEW,pair.CLOCK_NAME},{120,'pair-budget-clock.json'})
  local policy=pair.recovery_normalized(t.settings())
  t.eq(math.max(policy.cooldown,policy.min_dwell),SPACING)
end)

t.test('charge_clock: the shared cases',function()
  for _,case in ipairs(DATA.charge_clock) do
    local got=pair.charge_clock(case.events,case.record,canon.number(case.now),canon.number(case.uptime),BOOT)
    t.eq(nums(got),nums(case.expect),case.name)
  end
end)

t.test('timelines: clock 3 h / 1 h / 30 s behind, same boot and after a reboot',function()
  for _,case in ipairs(DATA.timelines) do
    for _,check in ipairs(case.checks) do
      local effective,now=timeline(case,canon.number(check[1]))
      t.eq(spacing_met(effective,now),check[2],case.name..' t='..tostring(canon.number(check[1])))
    end
  end
end)

t.test('the old clamp (raw stamps) still blocks: the fix is the clock note, not the policy',function()
  local case=DATA.timelines[1]
  local now=canon.number(case.stamp)-canon.number(case.behind)+600
  t.eq(spacing_met(floats({canon.number(case.stamp)}),now),false)
  t.eq(spacing_met((timeline(case,600)),now),true)
end)

t.test('no clock: unchanged',function()
  t.eq(nums(pair.charge_clock(floats({9000}),canon.object({}),1000,nil,nil)),{9000})
  t.eq(pair.charge_clock(nil,canon.object({}),1000,5,BOOT),nil)
end)

local function ledger_path(env) return env.persist..'/pair-auto-budget.json' end
local function clock_path(env) return env.runtime..'/'..pair.CLOCK_NAME end
local function booted(env,boot,uptime)
  env.run.fs.files[pair.BOOT_ID]=boot..'\n'
  env.run.mono_now=uptime
end

t.test('charge_attempt: a failover after a 3 h backward step waits one cooldown',function()
  local env=t.env();booted(env,BOOT,5000)
  local S=1800000000;env.run.wall_now=S
  t.eq(pair.charge_attempt(env,t.settings(),env.revision,false),S)
  t.eq(nums(t.read(env,ledger_path(env)).events),{S})
  local note=t.read(env,clock_path(env))
  t.eq(note.boot,BOOT);t.eq(nums(note.at[1]),{S,5000})
  local back=S-3*3600
  for _,dt in ipairs({0,30,59}) do
    env.run.wall_now=back+dt;env.run.mono_now=5000+dt
    t.code('PAIR-RATE-LIMIT',pair.charge_attempt,env,t.settings(),env.revision,false)
  end
  env.run.wall_now=back+60;env.run.mono_now=5060
  t.eq(pair.charge_attempt(env,t.settings(),env.revision,false),back+60)
  for _,x in ipairs(nums(t.read(env,ledger_path(env)).events)) do t.truthy(x<=back+60,'stamp written back on the current clock') end
  local at=t.read(env,clock_path(env)).at
  t.eq(nums(at[#at]),{back+60,5060})
end)

t.test('charge_attempt: after a reboot a future stamp waits at most one cooldown of uptime',function()
  local env=t.env();booted(env,'ffffffff-0000-4000-8000-00000000000a',59)
  local S=1800000000
  env.run.fs.write_atomic(ledger_path(env),canon.encode(canon.object({events=floats({S})})))
  env.run.wall_now=S-3600
  t.code('PAIR-RATE-LIMIT',pair.charge_attempt,env,t.settings(),env.revision,false)
  env.run.wall_now=S-3599;env.run.mono_now=60
  t.eq(pair.charge_attempt(env,t.settings(),env.revision,false),S-3599)
end)

t.test('charge_attempt: a note of another boot is not used; forward steps unchanged',function()
  local env=t.env();booted(env,BOOT,5000)
  local S=1800000000;env.run.wall_now=S
  pair.charge_attempt(env,t.settings(),env.revision,false)
  booted(env,'ffffffff-0000-4000-8000-00000000000a',5100);env.run.wall_now=S-10
  t.code('PAIR-RATE-LIMIT',pair.charge_attempt,env,t.settings(),env.revision,false)
  local fwd=t.env();booted(fwd,BOOT,5000);fwd.run.wall_now=9000
  pair.charge_attempt(fwd,t.settings(),fwd.revision,false)
  fwd.run.wall_now=9059;fwd.run.mono_now=5059
  t.code('PAIR-RATE-LIMIT',pair.charge_attempt,fwd,t.settings(),fwd.revision,false)
  fwd.run.wall_now=9600;fwd.run.mono_now=5001
  t.eq(pair.charge_attempt(fwd,t.settings(),fwd.revision,false),9600)
end)

t.test('abort stamps far in the future are dropped; no boot_id keeps the old path',function()
  t.eq(pair.abort_stamps(floats({1121,1120,990}),1000),{990,1000})
  t.eq(pair.retry_wait(floats({5000}),canon.array({}),1000,pair.recovery_normalized(t.settings())),0)
  local env=t.env()   -- the memory fs has no boot_id: no note, raw stamps as before
  env.run.wall_now=9000;pair.charge_attempt(env,t.settings(),env.revision,false)
  t.eq(t.read(env,clock_path(env)),nil,'no note without a boot id')
  t.eq(nums(pair.effective_events(env,canon.object({events=floats({9000})}),9001)),{9000})
end)

t.test('effective_events reads the note of this boot',function()
  local env=t.env();booted(env,BOOT,545)
  env.run.fs.write_atomic(clock_path(env),canon.encode(canon.object({boot=BOOT,at=canon.array({canon.array({canon.float(11800),canon.float(500)})})})))
  t.eq(nums(pair.effective_events(env,canon.object({events=floats({11800})}),1045)),{1000})
end)

t.run()
