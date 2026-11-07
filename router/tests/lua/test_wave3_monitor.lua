-- The pass plan inside the Lua monitor (probe_plan.lua; Python twin: test_wave3_product.py MonitorWiring): phases on the
-- grid, the wait a suspicion releases, the reserve carried over a skipped pass and measured out of turn.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local monitor=require('monitor')
local SOURCE,TARGET='wireguard:peer_7','wireguard:peer_8'

local function fresh(settings)
  local inventory=t.inventory()
  for k,v in pairs(settings or {}) do inventory.settings[k]=v end
  local R=t.fake_runner({inventory=inventory})
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  R.devices={}
  local https=R.https_get
  function R.https_get(device,address,hostname,path,seconds,cb,agent)
    if R.devices[#R.devices]~=device then R.devices[#R.devices+1]=device end
    if R.dead and R.dead[device] then cb(nil,'timeout');return end
    return https(device,address,hostname,path,seconds,cb,agent)
  end
  R.timers={}
  function R.after(ms,fn)
    local handle={ms=ms,fn=fn}
    handle.cancel=function() handle.cancelled=true end
    R.timers[#R.timers+1]=handle
    return handle
  end
  return R,monitor.new(R)
end
local function fire(R,handle) if not handle.cancelled then handle.cancelled=true;handle.fn() end end
local function pending(R,after_ms)
  for _,h in ipairs(R.timers) do if not h.cancelled and h.ms==after_ms then return h end end
  return nil
end
local function clean_row(id,now) return canon.object({id=id,code=canon.null,dns_ok=true,https_success=3,vendor_state='SETTLED',time=now}) end
local function idle_memo(R,m)
  m.plan_memo.pair=canon.object({source=SOURCE,target=TARGET});m.plan_memo.native='OBSERVING'
  m.plan_memo.rows={[SOURCE]=clean_row(SOURCE,R.now-10),[TARGET]=clean_row(TARGET,R.now-10)}
end
-- real passes until both rows have settled and the firmware wait is over (two equal observations and the settle period)
local function settle(R,m)
  for _=1,30 do
    local status=m:pass();R.advance(10)
    local rows=status.profiles
    if rows[1].vendor_state=='SETTLED' and rows[2].vendor_state=='SETTLED' and not m.booster:waiting(R.wall()) then return status end
  end
  error('never settled')
end
-- real passes until the plan skips the reserve: the next pass is the one that measures it again
local function to_skip(R,m)
  for _=1,6 do
    local status=m:pass();R.advance(10)
    if #status.probe_plan.skip>0 then return status end
  end
  error('the reserve was never skipped')
end

t.test('spread: the idle reserve starts with the pass, the carrying primary at its phase, one publish',function()
  local R,m=fresh();idle_memo(R,m)
  local published;t.eq(m:start_pass(function(status) published=status end),true)
  t.eq(R.devices,{'wgclient2'},'only the reserve so far');t.eq(published,nil)
  local wait=pending(R,3000);t.truthy(wait,'the phase T/K capped: 3 s')
  R.advance(3);fire(R,wait)
  t.eq(R.devices,{'wgclient2','wgclient'});t.truthy(published~=nil and published.profiles,'the pass ended after the primary')
  t.eq(canon.plain(published.probe_plan.order),{TARGET,SOURCE})
  t.eq(canon.number(published.probe_plan.offsets[2]),3)
end)

t.test('spread: a suspicion during the wait starts the rest of the pass at once',function()
  local R,m=fresh();idle_memo(R,m)
  local done=false;m:start_pass(function() done=true end)
  local wait=pending(R,3000)
  m:spread_now()
  t.eq(R.devices,{'wgclient2','wgclient'});t.eq(wait.cancelled,true);t.eq(done,true)
  t.eq(m.spread_release,nil,'closed with the pass')
  m:spread_now()  -- no pass, no effect
end)

t.test('spread: both sensors of the watcher take the same way, idle or inside a pass',function()
  local R,m=fresh();idle_memo(R,m)
  local set={};local timer={set=function(_,ms) set[#set+1]=ms end}
  m:suspected_now(timer);t.eq(set,{1},'no pass: the next one now')
  m:start_pass();set={}
  m:suspected_now(timer)
  t.eq(set,{},'a running pass ends first');t.eq(R.devices,{'wgclient2','wgclient'},'but its wait is over')
  local f=assert(io.open(t.here..'/../../files/usr/lib/homensai-vpn/lua/monitor.lua','rb'));local text=f:read('*a');f:close()
  t.truthy(string.find(text,'if okf and suspected then monitor:suspected_now(timer) end',1,true))
  t.truthy(string.find(text,'if okg and wanted then monitor:suspected_now(timer) end',1,true))
end)

t.test('spread: nothing waits outside the clean idle state, and option 0 never waits',function()
  local R,m=fresh();idle_memo(R,m)
  m.plan_memo.rows[SOURCE].code='VPN-003'
  m:start_pass();t.eq(#R.timers>0 and pending(R,3000)~=nil,false);t.eq(R.devices,{'wgclient','wgclient2'},'order as before')
  local R2,m2=fresh({probe_spread=false});idle_memo(R2,m2)
  m2:start_pass();t.eq(pending(R2,3000),nil)
  local R3,m3=fresh();idle_memo(R3,m3);m3.plan_memo.native='COMMITTED'
  m3:start_pass();t.eq(pending(R3,3000),nil)
end)

t.test('grid: lateness of the timer does not add up, an event moves the grid',function()
  local R,m=fresh()
  m:start_pass();m.pass_seconds=.3
  t.truthy(math.abs(m:next_delay()-9.7)<1e-6)
  R.advance(10.4)    -- the timer fired 400 ms late
  m:start_pass();m.pass_seconds=.3
  t.truthy(math.abs(m:next_delay()-9.3)<1e-6,'planned from the slot, not from the late start')
  R.advance(4)       -- a kick: a pass far from its slot
  m:start_pass();m.pass_seconds=.3
  t.truthy(math.abs(m:next_delay()-9.7)<1e-6,'the grid moved to the event')
  local R2,m2=fresh({probe_spread=false})
  m2:start_pass();m2.pass_seconds=.3
  t.truthy(math.abs(m2:next_delay()-9.7)<1e-6,'option off: the former formula')
  t.eq(m2.grid_slot,nil)
end)

t.test('reserve budget: off by default, on: the idle reserve is carried over a pass and stays fresh',function()
  local R,m=fresh({probe_spread=false});local status=settle(R,m)
  R.devices={};status=m:pass();t.eq(#R.devices,2,'off: both every pass')
  local R2,m2=fresh({reserve_probe_interval=60,probe_spread=false});settle(R2,m2)
  to_skip(R2,m2)
  m2:pass();R2.advance(10)   -- a measured pass: the next one skips
  R2.devices={}
  local samples=#m2.samples
  local before=m2.plan_memo.rows[TARGET].time
  status=m2:pass()
  t.eq(R2.devices,{'wgclient'},'the reserve is not measured in this pass')
  local reserve
  for _,row in ipairs(status.profiles) do if row.id==TARGET then reserve=row end end
  t.eq(canon.number(reserve.time),canon.number(before),'its row keeps the real measurement time');t.eq(reserve.code,canon.null)
  t.eq(#m2.samples,samples+1,'no invented sample')
  t.eq(canon.plain(status.probe_plan.skip),{TARGET})
  R2.advance(10);R2.devices={};status=m2:pass()
  t.eq(#R2.devices,2,'20 s old: measured')
end)

t.test('reserve budget: a failed primary, a dense episode and a moved tunnel bring the reserve back at once',function()
  local R,m=fresh({reserve_probe_interval=60,probe_spread=false});settle(R,m)
  to_skip(R,m)
  m:pass();R.advance(10)                  -- measured: the next pass would skip it
  R.dead={wgclient=true};R.devices={}
  local failed=m:pass();R.advance(10)     -- the primary fails in the skipped pass
  t.eq(R.devices,{'wgclient'},'still skipped: nothing was known yet');t.eq(#failed.probe_plan.skip,1)
  R.dead=nil;R.devices={};m:pass()
  t.eq(#R.devices,2,'out of turn after the failed primary check')
  local R2,m2=fresh({reserve_probe_interval=60,probe_spread=false});settle(R2,m2)
  to_skip(R2,m2)
  m2:pass();R2.advance(10)
  m2.plan_memo.measured[TARGET].vendor_generation='another'
  R2.devices={}
  local status=m2:pass()
  local row;for _,x in ipairs(status.profiles) do if x.id==TARGET then row=x end end
  t.eq(row.code,'CHECK-LIMIT','a success is never attached to another generation')
  R2.advance(10);R2.devices={};m2:pass();t.eq(#R2.devices,2,'measured in the next pass')
end)

t.run()
