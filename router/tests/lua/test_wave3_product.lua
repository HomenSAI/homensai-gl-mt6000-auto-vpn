-- Wave 3 study winners in the product: the same shared cases as tests/test_wave3_product.py over the Lua twins, the ledger
-- (pair.budget) and the pass of the Lua monitor (phases, the wait a suspicion releases, the reserve carried over a skip).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local NULL=canon.null
local pair=require('pair')
local plan=require('probe_plan')
local retry=require('retry_policy')

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local PLAN=canon.decode(read_file(t.here..'/../probe_plan_cases.json'))
local RETRY=canon.decode(read_file(t.here..'/../retry_policy_cases.json'))

local function list(values) local out={};for i,v in ipairs(values) do out[i]=canon.number(v) or v end;return out end
local function nums(values) local out={};for i,v in ipairs(values) do out[i]=canon.number(v) end;return out end
-- JSON numbers can be boxed floats: the plan works on plain numbers
local function plain(value)
  if type(value)~='table' or value==NULL then return value end
  if canon.is_float(value) then return canon.number(value) end
  local out={};for k,v in pairs(value) do out[k]=plain(v) end
  return out
end

t.test('probe_plan: the shared plan cases',function()
  for _,case in ipairs(PLAN.plan) do
    local got=plan.plan(plain(case.ids),plain(case.context),plain(case.settings))
    t.eq(canon.encode(canon.array(got.skip)),canon.encode(case.skip),case.name..': skip')
    t.eq(canon.encode(canon.array(got.order)),canon.encode(case.order),case.name..': order')
    t.eq(nums(got.offsets),nums(case.offsets),case.name..': offsets')
  end
end)

t.test('probe_plan: effective interval, slots, clean, carried',function()
  for _,case in ipairs(PLAN.effective) do
    t.eq(plan.effective_reserve(plain(case.settings),canon.number(case.interval),canon.number(case.valid_for)),canon.number(case.every))
  end
  for _,case in ipairs(PLAN.next_slot) do
    local next_,delay=plan.next_slot(canon.number(case.slot),canon.number(case.interval),canon.number(case.now))
    t.eq(next_,canon.number(case.next),case.name);t.truthy(math.abs(delay-canon.number(case.delay))<1e-9,case.name)
  end
  for _,case in ipairs(PLAN.begin_slot) do
    local expected=case.expected;if expected==NULL then expected=nil else expected=canon.number(expected) end
    t.eq(plan.begin_slot(expected,canon.number(case.now)),canon.number(case.slot),case.name)
  end
  for _,case in ipairs(PLAN.clean) do t.eq(plan.clean(case.row==NULL and nil or plain(case.row)),case.clean,case.name) end
  for _,case in ipairs(PLAN.carried) do
    t.eq(plan.carried(plain(case.row),{groups=plain(case.groups)})~=nil,case.kept,case.name)
  end
end)

t.test('retry_policy: the shared cases',function()
  for _,case in ipairs(RETRY.base) do t.eq(retry.base(canon.number(case.n)),canon.number(case.base)) end
  for _,case in ipairs(RETRY.pause) do
    local u=canon.number(case.u)
    local got=retry.pause(canon.number(case.n),plain(case.settings),function() return u end)
    t.truthy(math.abs(got-canon.number(case.pause))<1e-9,'pause '..tostring(got))
  end
  for _,case in ipairs(RETRY.count) do
    local last=case.last;if last==NULL then last=nil else last=canon.number(last) end
    t.eq(retry.count(canon.number(case.failures),last,canon.number(case.now)),canon.number(case.count),case.name)
  end
end)

t.test('retry_policy: real draws stay inside the bounds and differ',function()
  local seen={}
  for n=1,8 do for _=1,50 do
    local value=retry.pause(n,{})
    t.truthy(value>=retry.FLOOR and value<=retry.base(n))
    seen[value]=true
  end end
  local count=0;for _ in pairs(seen) do count=count+1 end
  t.truthy(count>100,'the pauses come from the kernel, not from an unseeded generator')
end)

t.test('budget: the ledger outlives the rate limit and never overflows',function()
  local now=100000
  local function arr(values) local out={};for i,v in ipairs(values) do out[i]=canon.float(v) end;return canon.array(out) end
  local kept,allowed=pair.budget(arr({now-3000,now-2000,now-1000}),now,900,3)
  t.eq(#kept,3,'older failovers stay for the damping');t.eq(allowed,true)
  local _,blocked=pair.budget(arr({now-800,now-500,now-100}),now,900,3)
  t.eq(blocked,false)
  local events=canon.array({})
  for index=0,119 do
    local stamp=100000+60*index
    events=pair.budget(events,stamp,900,3)
    events[#events+1]=canon.float(stamp)
    t.truthy(#events<=16)
  end
  t.eq(#pair.budget(events,100000+60*120,900,3),pair.LEDGER_SIZE)
  local older={};for i=1,14 do older[i]=now-3000-60*i end
  older[#older+1]=now-200;older[#older+1]=now-100
  local mixed=pair.budget(arr(older),now,900,3)
  t.eq(#mixed,pair.LEDGER_SIZE);t.eq(canon.number(mixed[#mixed]),now-100);t.eq(canon.number(mixed[#mixed-1]),now-200)
  t.eq(#pair.budget(arr({now-pair.LEDGER_MEMORY,now-pair.LEDGER_MEMORY+1}),now),1)
end)

t.test('settings: defaults, and a preset saved by the page does not turn the damping back',function()
  local r=pair.recovery_normalized(canon.object({}))
  t.eq({r.flap_model,r.flap_limit,r.flap_window,r.flap_halflife,r.flap_suppress,r.flap_reuse},{'double',2,60,1800,1500,500})
  t.eq({r.attempt_limit,r.attempt_window},{3,15})
  local p=pair.recovery_normalized(canon.object({recovery_attempt_limit='3',recovery_attempt_window='15'}))
  t.eq(pair.return_hold({4000,4900},5000,p),240)
  local c=pair.recovery_normalized(canon.object({recovery_flap_halflife='60',recovery_flap_suppress='9000',recovery_flap_reuse='1',recovery_flap_model='x'}))
  t.eq({c.flap_model,c.flap_halflife,c.flap_suppress,c.flap_reuse},{'double',600,3000,200})
end)

t.test('a failed pass: the pause grows with the series, a quiet minute restarts it, the option keeps 5 s',function()
  local A=require('auto');local ctl=require('auto_control')
  local tick=pair.tick
  pair.tick=function() ctl.refuse('PAIR-TEST-FAILED') end
  local draws={}
  local uniform=retry.uniform
  retry.uniform=function() return 0.5 end
  local ok,err=pcall(function()
    local env=t.env()
    local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
    local function step() local pause=A.iteration(env,ctx);draws[#draws+1]=ctx.nap_seconds;ctx.nap_seconds=nil;return pause end
    for _=1,7 do t.eq(step(),'nap');env.run.advance(1) end
    t.eq(draws,{1,1,2,3,5,7.5,7.5},'half of 2, 2, 4, 6, 10, 15, 15')
    t.eq(t.read(env,env.runtime..'/native-status.json').blockers[1],'PAIR-TEST-FAILED')
    env.run.advance(61);draws={}
    step();t.eq(draws,{1},'a new series')
    local fixed=t.env({settings=t.settings({retry_backoff='fixed'})})
    local c2={last_return=0,consumed=canon.object({}),last_attempt=0}
    t.eq(A.iteration(fixed,c2),5);t.eq(c2.nap_seconds,nil)
  end)
  pair.tick=tick;retry.uniform=uniform
  if not ok then error(err,0) end
end)

t.test('a failed pass: the blocking driver rests the retry pause, not the 2 s of a tick',function()
  local A=require('auto');local ctl=require('auto_control')
  local tick=pair.tick
  local uniform=retry.uniform
  pair.tick=function() ctl.refuse('PAIR-TEST-FAILED') end
  retry.uniform=function() return 0.5 end
  local env=t.env()
  local ok,err=pcall(A.run_blocking,env,2)
  pair.tick=tick;retry.uniform=uniform
  if not ok then error(err,0) end
  local rest=0;for _,s in ipairs(env.slept) do rest=rest+s end
  t.truthy(math.abs(rest-1)<1e-6,'half of the first base: '..rest)
end)

t.test('a failed pass: M.nap carries the retry pause and a queued click ends it',function()
  local A=require('auto')
  local env=t.env();local slept=0
  env.sleep=function(s) slept=slept+s;env.run.advance(s) end
  A.nap(env,3.3);t.truthy(math.abs(slept-3.3)<1e-6,'waits the pause, not the 2 s of a tick')
  slept=0
  -- the whole row as manual_request writes it: the stamps come back from JSON as canon.float tables (review 05.11.2026,
  -- a row without requested hid that the key held the address of a new table at each read)
  local function click(id,stamp)
    env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json',canon.encode(canon.object({id=id,pair=string.rep('b',32),revision=string.rep('c',32),
      direction='reserve',state='QUEUED',requested=canon.float(stamp),updated=canon.float(stamp),selection=canon.object({tx=canon.null}),code=canon.null})))
  end
  click(string.rep('a',32),1761830400.25)
  t.truthy(canon.is_float(t.read(env,env.runtime..'/pair-manual-control.json').requested),'the fixture is the real shape')
  A.nap(env,10);t.eq(slept,0)
  -- review 04.11.2026 (finding 4): the same row ends one pause only, a new one ends the next
  A.nap(env,3);t.truthy(math.abs(slept-3)<1e-6,'a click that stays QUEUED is no reason to spin')
  slept=0
  click(string.rep('d',32),1761830400.25)
  A.nap(env,10);t.eq(slept,0,'a new id with the same stamp')
  A.nap(env,1);t.truthy(math.abs(slept-1)<1e-6)
  slept=0
  click(string.rep('d',32),1761830400.5)
  A.nap(env,10);t.eq(slept,0,'the same id, a new stamp')
  A.nap(env,1);t.truthy(math.abs(slept-1)<1e-6)
end)

t.test('a queued click no pass reaches costs the failing passes no pause (real float stamps, review 05.11.2026)',function()
  local A=require('auto');local ctl=require('auto_control')
  local env=t.env();local sel=env.backend.selection
  local id=string.rep('11',16)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=id,request_source='manual'})))
  env.net={network=function() ctl.refuse('PAIR-NETWORK-UNVERIFIED') end}
  pair.save(env,canon.object({id=id,phase='RUNNING',ran=true,started=canon.float(env.run.wall()-10),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)}))
  env.run.fs.write_atomic(env.runtime..'/status.json','{"samples":[],"profiles":[]}')
  local now=env.run.wall()-0.25  -- a stamp with a fraction, as time.time() leaves it
  local path=env.runtime..'/pair-manual-control.json'
  env.run.fs.write_atomic(path,canon.encode(canon.object({id=string.rep('ab',16),pair=id,revision=env.revision,direction='reserve',state='QUEUED',
    requested=canon.float(now),updated=canon.float(now),selection=canon.object({tx=canon.null}),code=canon.null,request_source='manual'})))
  local uniform=retry.uniform
  retry.uniform=function() return 0.5 end
  local ok,err=pcall(function()
    local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
    local passes=0;local started=env.run.wall()
    while env.run.wall()-started<70 do
      passes=passes+1
      local pause=A.iteration(env,ctx)
      if pause=='nap' then local seconds=ctx.nap_seconds or 2;ctx.nap_seconds=nil;A.nap(env,seconds);env.sleep(0.2) else env.sleep(pause) end
    end
    t.truthy(passes<70,'one pass per pause, not five a second: '..passes)
  end)
  retry.uniform=uniform
  if not ok then error(err,0) end
  local row=t.read(env,path);t.eq({row.state,row.code},{'CANCELLED','PAIR-MANUAL-EXPIRED'})
end)

t.test('a queued click ends after its 60 s also when no pass reaches consume (finding 4)',function()
  local A=require('auto');local manual=require('manual')
  local env=t.env();local path=env.runtime..'/pair-manual-control.json'
  local function row(state,requested)
    env.run.fs.write_atomic(path,canon.encode(canon.object({id=string.rep('a',32),pair=string.rep('b',32),revision=string.rep('c',32),direction='reserve',
      state=state,requested=canon.float(requested),updated=canon.float(requested),selection=canon.object({tx=canon.null}),code=canon.null})))
  end
  local now=env.run.wall()
  row('QUEUED',now-59);t.eq(manual.expire_queued(env),false);t.eq(t.read(env,path).state,'QUEUED')
  row('CLAIMED',now-120);t.eq(manual.expire_queued(env),false);t.eq(t.read(env,path).state,'CLAIMED')
  row('COMPLETED',now-120);t.eq(manual.expire_queued(env),false);t.eq(t.read(env,path).state,'COMPLETED')
  env.run.fs.write_atomic(path,'{"state":"QUEUED"}');t.eq(manual.expire_queued(env),false)
  env.run.fs.remove(path);t.eq(manual.expire_queued(env),false)
  -- the pass fails before the tick: the row still ends, with the code of consume
  row('QUEUED',now-61)
  env.backend.policy=function() require('auto_control').refuse('POLICY-READ-FAILED') end
  A.iteration(env,{last_return=0,consumed=canon.object({}),last_attempt=0})
  local got=t.read(env,path);t.eq({got.state,got.code},{'CANCELLED','PAIR-MANUAL-EXPIRED'})
end)

t.run()
