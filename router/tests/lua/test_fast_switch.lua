-- The fast end of Auto (FAST-SWITCH-2026-11-04.ru.md). Python twin: tests/test_fast_switch.py over the same
-- fast_switch_cases.json (generated from channel_model.py, probe_policy.py and advisor.py by gen_fast_switch_cases.py).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local CM=require('channel_model')
local pair=require('pair')
local policy=require('probe_policy')
local A=require('advisor')
local auto=require('auto')
local fast=require('fast_detect')
local NULL=canon.null
local N=canon.number

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../fast_switch_cases.json'))
local CURVE=A.load_curve(t.here..'/../../files/usr/lib/homensai-vpn/slider_curve.json')
local PROFILE=CASES.profile
local NOW=N(CASES.now)
local TOL=N(CASES.tolerance)

local function plain(v) -- a decoded settings object -> plain numbers for the options, as inventory.lua gives them
  if v==NULL then return nil end
  return v
end
local function near(a,b,msg)
  a,b=N(a),N(b)
  if a==nil or b==nil or math.abs(a-b)>TOL then error((msg or 'not near')..': '..tostring(a)..' vs '..tostring(b),2) end
end
local function sample(r)
  return canon.object({id=PROFILE.id,time=canon.float(N(r.t)),code=r.code,dns_ok=r.dns_ok,https_success=r.https,interface=PROFILE.interface,
    vendor_tunnel_id=PROFILE.vendor_tunnel_id,vendor_generation=(r.gen~=nil and r.gen~=NULL) and r.gen or PROFILE.vendor_generation})
end
local function samples(rows) local out=canon.array({});for i,r in ipairs(rows) do out[i]=sample(r) end;return out end

t.test('options: the shared cases',function()
  for _,case in ipairs(CASES.options) do
    local s=case.settings
    t.eq(CM.or_failures(s),plain(case.or_failures),'or_failures '..canon.encode(s))
    t.eq(CM.turbo_on(s)==true,case.turbo_on,'turbo_on '..canon.encode(s))
    t.eq(CM.heartbeat_k(s),plain(case.heartbeat_k),'heartbeat_k '..canon.encode(s))
    t.eq(policy.dense_interval(s),case.dense,'dense '..canon.encode(s))
  end
end)

t.test('leave_rule: the shared cases',function()
  for _,case in ipairs(CASES.leave) do
    local env=t.env()
    local got=CM.leave_rule(samples(case.rows),PROFILE.id,3,NOW,30,case.settings,PROFILE,env,CASES.reserve,plain(case.beat))
    t.eq(got,plain(case.expect),case.name)
  end
end)

t.test('wake_row: the shared cases',function()
  for _,case in ipairs(CASES.wake) do
    local got=policy.wake_row(case.settings,case.rows,plain(case.pair),NOW)
    if plain(case.expect)==nil then t.eq(got,nil,canon.encode(case.settings))
    else t.eq({got.reason,got.id,N(got.time)},{case.expect.reason,case.expect.id,NOW}) end
  end
end)

t.test('the steps of the slider: the shared cases',function()
  local ts={1,0.5,0,-0.01,-0.05,-0.09,-0.1,-0.15,-0.2,-0.25,-0.3,-0.35,-0.4,-0.5,-0.6,-0.7,-0.75}
  for i,want in ipairs(CASES.advisor.steps) do
    local p=A.interpolate(CURVE,ts[i])
    near(p.t,want.t,'t '..ts[i])
    for _,k in ipairs({'theta','dur_b','pg','primary_stable','rescue_stable'}) do near(p[k],want[k],k..' at '..ts[i]) end
    for _,k in ipairs({'cons_f','beat_k','dense_interval'}) do t.eq(p[k],plain(want[k]),k..' at '..ts[i]) end
  end
end)

t.test('floors, safety, behaviour',function()
  for _,c in ipairs(CASES.advisor.floors) do
    near(A.t_floor(c.settings),c.floor,canon.encode(c.settings));t.eq(A.fast_enabled(c.settings)==true,c.fast,canon.encode(c.settings))
  end
  for _,c in ipairs(CASES.advisor.safety) do
    local got=A.safety(A.interpolate(CURVE,N(c.t)))
    t.eq(#got,#c.codes,'safety at '..N(c.t))
    for i,x in ipairs(c.codes) do t.eq(got[i],x) end
  end
  for _,c in ipairs(CASES.advisor.behaviour) do
    local ride,leave=A.behaviour(N(c.theta),N(c.dur_b),plain(c.cons))
    near(ride,c.value[1],'ride');near(leave,c.value[2],'leave')
  end
end)

local function settings_of(s)  -- number options as plain Lua numbers (the decoded fractions are float objects)
  local out=canon.object({})
  for k,v in pairs(s) do out[k]=N(v) or v end
  return out
end

t.test('current and the settings key: the shared cases',function()
  for _,c in ipairs(CASES.advisor.current) do
    local s=settings_of(c.settings)
    local cur=A.current(s,CURVE)
    t.eq(A.settings_key(s),c.key,c.name)
    local want=c.current
    t.eq(cur.slider_t==nil and NULL or cur.slider_t~=nil,want.slider_t==NULL and NULL or true,c.name..' slider_t')
    if want.slider_t~=NULL then near(cur.slider_t,want.slider_t,c.name) end
    t.eq(cur.attached,want.attached,c.name..' attached');t.eq(cur.label,want.label,c.name..' label')
    near(cur.t_ref,want.t_ref,c.name..' t_ref')
    t.eq(cur.or_failures,plain(want.or_failures),c.name);t.eq(cur.beats,plain(want.beats),c.name)
    t.eq(cur.fast==true,want.fast,c.name);t.eq(cur.turbo==true,want.turbo,c.name)
  end
end)

local function events_of(ev)
  local out={outages={},groups={},n=ev.n,days=ev.days,weight_days=N(ev.weight_days)}
  for i,o in ipairs(ev.outages) do out.outages[i]={N(o[1]),N(o[2])} end
  for k,v in pairs(ev.groups) do out.groups[k]=N(v) end
  return out
end

t.test('search and costs: the shared cases',function()
  local ev={}
  for name,e in pairs(CASES.advisor.events) do ev[name]=events_of(e) end
  for _,c in ipairs(CASES.advisor.costs) do
    local total,down,unnecessary=A.cost_at(ev[c.events],CURVE,N(c.t))
    near(total,c.value[1],'total');near(down,c.value[2],'down');near(unnecessary,c.value[3],'unnecessary')
  end
  for _,c in ipairs(CASES.advisor.search) do
    local best=A.search(ev[c.events],CURVE,0,c.fast)
    near(best.t,c.t,c.events);near(best.cost,c.cost,c.events);t.eq(best.method,c.method,c.events);t.eq(best.evaluations,c.evaluations,c.events)
  end
end)

t.test('auto_step: the shared cases',function()
  local calm={open={},route='source',native='OBSERVING'}
  for _,c in ipairs(CASES.advisor.auto) do
    local step=A.auto_step(CURVE,{state='shift',t=N(c.t)},settings_of(c.settings),{},calm,NOW)
    t.eq(step.apply,c.apply,c.name)
    if c.to==NULL then t.eq(step.t,nil,c.name) else near(step.t,c.to,c.name) end
    t.eq(step.code,plain(c.code),c.name)
  end
end)

t.test('turbo: the advisor stays out of it, with its own reason',function()
  local s=settings_of(canon.object({slider_t=-0.5,hmm_theta=0.5,hmm_dur_b=2,return_pg=0.8,recovery_primary_stable=120,recovery_rescue_stable=5,hmm_or_failures=2,turbo_beats=5,slider_fast=true,slider_turbo=true}))
  local cur=A.current(s,CURVE)
  t.truthy(cur.attached)
  t.truthy(string.find(A.reason({state='inactive'},cur,'ru'),'Турбо',1,true))
  local real=A.events
  local ev=events_of(CASES.advisor.events.lossy)
  ev.durations={};ev.counts={natural=2,loss_episodes=0,flaps=0,reserve_failures=0}
  A.events=function() return ev end
  local ok,result=pcall(A.recommend,CURVE,{},s,NOW,0)
  A.events=real
  t.truthy(ok,tostring(result));t.eq(result.state,'inactive');t.eq(result.t,nil)
  t.truthy(string.find(result.reason_ru,'Турбо',1,true))
end)

t.test('wake_due: a new row ends one nap, a bad row none',function()
  local env=t.env()
  t.eq(auto.wake_due(env),false,'no row')
  env.run.fs.write_atomic(env.runtime..'/'..CM.WAKE_NAME,'{"reason":"sample","time":5.5,"id":"a"}')
  t.eq(auto.wake_due(env),true);t.eq(auto.wake_due(env),false,'the same row wakes once')
  env.run.fs.write_atomic(env.runtime..'/'..CM.WAKE_NAME,'{"reason":"sample","time":6.5,"id":"a"}')
  t.eq(auto.wake_due(env),true)
  for _,moment in ipairs({7.5,8.5}) do  -- a heartbeat row is rewritten every beat, it wakes once per run of lost beats
    env.run.fs.write_atomic(env.runtime..'/'..CM.WAKE_NAME,string.format('{"reason":"heartbeat","time":%s,"since":100.5,"id":"a"}',moment))
    t.eq(auto.wake_due(env),moment==7.5)
  end
  for _,bad in ipairs({'[]','{"time":"x"}','{','null'}) do
    env.run.fs.write_atomic(env.runtime..'/'..CM.WAKE_NAME,bad)
    t.eq(auto.wake_due(env),false,bad)
  end
end)

t.test('nap: a wake row ends it at once',function()
  local env=t.env()
  env.run.fs.write_atomic(env.runtime..'/'..CM.WAKE_NAME,'{"reason":"sample","time":5.5,"id":"a"}')
  local slept=0;env.sleep=function() slept=slept+1 end
  auto.nap(env,2)
  t.eq(slept,0)
end)

local function selection() return {source=PROFILE,target=canon.object({id=CASES.reserve})} end
local function status(env,rows)
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({samples=samples(rows)})))
end
local BAD={t=990,code='VPN-003',dns_ok=false,https=0}
local GOOD={t=995,code=NULL,dns_ok=true,https=3}

local function parallel_backend(env,answer)
  local log={}
  env.backend.recheck=function() log[#log+1]='sequential';return true end
  env.backend.recheck_begin=function(id,seconds) log[#log+1]='begin:'..id..':'..seconds;return {id=id} end
  env.backend.recheck_finish=function(p) log[#log+1]='finish:'..p.id;if answer=='error' then error('boom',0) end;return answer end
  return log
end

local ON=canon.object({parallel_recheck='1'})

t.test('L2: off until measured, a saved value stays',function()
  for _,row in ipairs({{canon.object({}),false},{canon.object({parallel_recheck=canon.null}),false},{canon.object({parallel_recheck=''}),false},
                      {canon.object({parallel_recheck='0'}),false},{canon.object({parallel_recheck=false}),false},
                      {canon.object({parallel_recheck='1'}),true},{canon.object({parallel_recheck=true}),true}}) do
    local env=t.env();env.run.wall_now=1000
    parallel_backend(env,true)
    t.eq(pair.recheck_begin(env,selection(),nil,row[1])~=nil,row[2])
  end
end)

t.test('L2: the probe starts first, its answer replaces a new one',function()
  local env=t.env();env.run.wall_now=1000
  local log=parallel_backend(env,true)
  local pending=pair.recheck_begin(env,selection(),nil,ON)
  t.eq(log,{'begin:'..PROFILE.id..':1'})
  status(env,{BAD})
  t.eq({pair.late_recheck(env,selection(),990,nil,pending)},{pair.LATE_RECHECK_CODE,'probe'})
  t.eq(log,{'begin:'..PROFILE.id..':1','finish:'..PROFILE.id})
end)

t.test('L2: a false, empty or failed answer goes on with the switch',function()
  for _,answer in ipairs({false,'nil','error'}) do
    local env=t.env();env.run.wall_now=1000
    parallel_backend(env,answer=='nil' and nil or answer)
    local pending=pair.recheck_begin(env,selection(),nil,ON)
    status(env,{BAD})
    t.eq(pair.late_recheck(env,selection(),990,nil,pending),nil)
  end
end)

t.test('L2: a healthy monitor sample still wins, and the pending probe is collected',function()
  local env=t.env();env.run.wall_now=1000
  local log=parallel_backend(env,false)
  local pending=pair.recheck_begin(env,selection(),nil,ON)
  status(env,{BAD,GOOD})
  t.eq({pair.late_recheck(env,selection(),990,nil,pending)},{pair.LATE_RECHECK_CODE,'monitor'})
  t.eq(log[#log],'finish:'..PROFILE.id)
end)

t.test('L2: never skipped',function()
  for _,s in ipairs({canon.object({}),canon.object({parallel_recheck='0'}),canon.object({parallel_recheck=false})}) do
    local env=t.env();env.run.wall_now=1000
    local log=parallel_backend(env,true)
    t.eq(pair.recheck_begin(env,selection(),nil,s),nil)
    status(env,{BAD})
    t.eq({pair.late_recheck(env,selection(),990,nil,nil)},{pair.LATE_RECHECK_CODE,'probe'})
    t.eq(log,{'sequential'})
  end
  -- no parallel start on this backend, or the start failed: the sequential probe
  local env=t.env();env.run.wall_now=1000
  local log=parallel_backend(env,true)
  env.backend.recheck_begin=function() error('no',0) end
  t.eq(pair.recheck_begin(env,selection(),nil,ON),nil)
  env.backend.recheck_begin=nil
  t.eq(pair.recheck_begin(env,selection(),nil,ON),nil)
end)

t.test('L2: a probe-blind failure is not contradicted',function()
  local env=t.env();env.run.wall_now=1000
  local log=parallel_backend(env,true)
  t.eq(pair.recheck_begin(env,selection(),'VPN-MTU',ON),nil)
  status(env,{BAD})
  t.eq(pair.late_recheck(env,selection(),990,'VPN-MTU',nil),nil)
  t.eq(#log,0)
end)

t.test('decision timing: measurement only',function()
  local env=t.env()
  pair.decision_timing(env,1.5,2.5,3.5,'model',true)
  t.eq(t.read(env,env.runtime..'/pair-decision-timing.json').rule,'model')
end)

t.test('heartbeat state: the reserve must have answered within TARGET_OK s',function()
  local p=fast.Pulse({random=function(n) return string.rep('a',n) end,sysfs=function() return nil end},function() return false end)
  p.pair_ids={source='a',target='b'}
  p.channels={a={id='a',lost=4,last='lost'},b={id='b',lost=0,last='ok',ok_at=99}}
  t.eq(p:beat_state(100).target_ok,true);t.eq(p:beat_state(100).lost,4)
  t.eq(p:beat_state(101.5).target_ok,false,'too long ago')
  p.channels.b.last='lost'
  t.eq(p:beat_state(100).target_ok,false,'its last beat was lost')
  p.channels.b=nil
  t.eq(p:beat_state(100),nil,'no reserve channel, no state')
  p.pair_ids={}
  t.eq(p:beat_state(100),nil)
end)

t.run()
