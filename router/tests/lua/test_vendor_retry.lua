-- A failover the vendor aborted before COMMITTED is retried promptly, not after the cooldown.
-- MT3000 59-cycle primary-drop soak 03-04.11.2026 (2.1.0-alpha7, this Lua runtime), cycle 28: journal APPLYING at
-- 19.11 s, apply_steps' first diagnostic VENDOR-WORKER-QUIET-UNVERIFIED -> ROLLED-BACK at 20.43 s, then OBSERVING
-- PAIR-RATE-LIMIT with the primary still failed until 81.43 s (the dispatch charge stayed: 60 s cooldown spacing);
-- traffic moved at 84.2 s. Python twin: tests/test_vendor_retry.py (vendor_retry_cases.json, the same decisions).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local T=require('transaction')

local QUIET='VENDOR-WORKER-QUIET-UNVERIFIED'
local RETRY_BASE=5  -- pair.RETRY_BASE (checked below); a literal so the unfixed code fails on the timeline itself
local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../vendor_retry_cases.json')).cases
local function floats(list) local out={};for i,x in ipairs(list) do out[i]=canon.float(x) end;return canon.array(out) end
local function nums(list) local out={};for i,x in ipairs(list or {}) do out[i]=canon.number(x) end;return out end

t.test('retry_wait: the shared cases',function()
  for _,case in ipairs(CASES) do
    local got=pair.retry_wait(case.aborted,case.events,canon.number(case.now),pair.recovery_normalized(case.settings))
    t.eq(got,canon.number(case.wait),case.name)
  end
end)

t.test('backoff constants: the same codes as the transient vendor states of the verify wait',function()
  t.eq({pair.RETRY_BASE,pair.ABORT_KEEP},{RETRY_BASE,16})
  local a,b={},{}
  for k in pairs(pair.ABORT_REFUND_CODES) do a[#a+1]=k end
  for k in pairs(T.VERIFY_TRANSIENT) do b[#b+1]=k end
  table.sort(a);table.sort(b);t.eq(a,b)
end)

local function ledger_path(env) return env.persist..'/pair-auto-budget.json' end
local function write_ledger(env,events,aborted)
  local value=canon.object({events=floats(events)})
  if aborted then value.aborted=floats(aborted) end
  env.run.fs.write_atomic(ledger_path(env),canon.encode(value))
end

t.test('charge_attempt: returns its stamp, keeps the abort series, waits out the backoff',function()
  local env=t.env();local now=env.run.wall()
  write_ledger(env,{now-500},{now-4})
  t.code('PAIR-RATE-LIMIT',pair.charge_attempt,env,t.settings(),env.revision,false)
  env.run.advance(1)
  t.eq(pair.charge_attempt(env,t.settings(),env.revision,false),now+1)
  local ledger=t.read(env,ledger_path(env))
  t.eq(nums(ledger.events),{now-500,now+1});t.eq(nums(ledger.aborted),{now-4})
  local fresh=t.env();pair.charge_attempt(fresh,t.settings(),fresh.revision,false)
  t.eq(t.read(fresh,ledger_path(fresh)).aborted,nil,'no abort: the ledger format is unchanged')
end)

local function journal_with(env,fields)
  local value={phase='ROLLED-BACK',failure_code=QUIET,started=canon.float(9000),pair_transition=canon.object({destination_role='target'})}
  for k,v in pairs(fields or {}) do value[k]=v end
  local real=T.journal_read
  T.journal_read=function() return value end
  return function() T.journal_read=real end
end

t.test('refund_abort: a vendor-aborted, rolled-back failover is refunded',function()
  local env=t.env();env.run.wall_now=9002.5
  write_ledger(env,{8500,9001})
  local restore=journal_with(env)
  local ok,res=pcall(pair.refund_abort,env,9001,QUIET);restore()
  assert(ok,res);t.eq(res,true)
  local ledger=t.read(env,ledger_path(env))
  t.eq(nums(ledger.events),{8500});t.eq(nums(ledger.aborted),{9002.5})
end)

t.test('refund_abort: needs a vendor code and a proven rollback',function()
  local refused={{'code not transient',{},'CLIENT-CONFIRMATION-TIMEOUT'},
    {'journal committed',{phase='COMMITTED',confirmed=canon.float(9003)},QUIET},
    {'rolled back after a confirmation',{confirmed=canon.float(9003)},QUIET},
    {'another failure',{failure_code='VENDOR-WORKER-BUSY'},QUIET},
    {'not a pair transition',{pair_transition=canon.null},QUIET},
    {'a newer transaction',{started=canon.float(9001.5)},QUIET}}
  for _,row in ipairs(refused) do
    local env=t.env();env.run.wall_now=9002.5
    write_ledger(env,{8500,9001})
    local restore=journal_with(env,row[2])
    local ok,res=pcall(pair.refund_abort,env,9001,row[3]);restore()
    assert(ok,res);t.eq(res,false,row[1])
    t.eq(nums(t.read(env,ledger_path(env)).events),{8500,9001},row[1])
  end
  local env=t.env();env.run.wall_now=9002.5;write_ledger(env,{8500,9001})
  local restore=journal_with(env)
  local ok,res=pcall(pair.refund_abort,env,9000.5,QUIET);restore()
  assert(ok,res);t.eq(res,false,'a charge that is not in the ledger')
end)

t.test('refund_abort: the abort list stays bounded',function()
  local env=t.env();env.run.wall_now=9101
  local old={};for k=0,39 do old[#old+1]=8200+10*k end
  write_ledger(env,{9100},old)
  local restore=journal_with(env,{started=canon.float(9100),failure_code='VENDOR-WORKER-BUSY'})
  local ok,res=pcall(pair.refund_abort,env,9100,'VENDOR-WORKER-BUSY');restore()
  assert(ok,res);t.eq(res,true)
  local aborted=nums(t.read(env,ledger_path(env)).aborted)
  t.eq(#aborted,pair.ABORT_KEEP);t.eq(aborted[#aborted],9101)
end)

-- pair.tick every `step` s with the real transaction (fake vendor) and the real committed return.
-- opts: up(at) primary health, stop (s), step, abort(log) -> arm the vendor abort for this dispatch,
-- code (the abort's code), busy(at) diagnostic VENDOR-WORKER-BUSY, settings overrides.
local function sim(opts)
  local step=opts.step or 2.5
  local env=t.env({settings=t.settings(opts.settings)})
  local sel=env.backend.selection
  local start=env.run.wall()
  sel.source.vendor_changed_at=canon.float(start-1000);sel.target.vendor_changed_at=canon.float(start-1000)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(start),id=string.rep('11',16),request_source='manual'})))
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='0'}),canon.object({['.name']='ovpnclient1',disabled='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function() return false end}
  pair.save(env,canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(start-1000),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)}))
  local rows={}
  env.backend.recovery_ready=function(id,settings)
    local policy=pair.recovery_normalized(settings)
    return pair.stable_success(canon.array(rows),id,policy.primary_successes,pair.stable_seconds(settings,policy),env.run.wall(),30)
  end
  local log={switches={},returns={},dispatches={},aborts={},busy_dispatch={},published={},reserve={},attempts={}}
  local real_attempt=T.attempt
  T.attempt=function(...) log.attempts[#log.attempts+1]=env.run.wall()-start;return real_attempt(...) end
  local armed=false
  local real_charge=pair.charge_attempt
  pair.charge_attempt=function(...)
    local stamp=real_charge(...)
    local at=env.run.wall()-start
    log.dispatches[#log.dispatches+1]=at
    if opts.busy and opts.busy(at) then log.busy_dispatch[#log.busy_dispatch+1]=at end
    armed=opts.abort~=nil and opts.abort(log,at) or false
    return stamp
  end
  -- the vendor: busy for the decision when opts.busy; when armed, apply_steps' first diagnostic (journal APPLYING)
  -- reports the abort code exactly once (MT3000 cycle 28), so the transaction rolls back before any write
  local B=env.backend
  B.diagnostic=function()
    local at=env.run.wall()-start
    if armed then
      local ok,j=pcall(T.journal_read,env)
      if ok and j.phase=='APPLYING' then armed=false;log.aborts[#log.aborts+1]=at;return {opts.code or QUIET},nil end
    end
    if opts.busy and opts.busy(at) then return {'VENDOR-WORKER-BUSY'},nil end
    return {},B.selection
  end
  local settings=t.settings(opts.settings)
  local ok,err=pcall(function()
    while env.run.wall()<start+opts.stop do
      local now=env.run.wall();local at=now-start;local up=opts.up(at)
      rows[#rows+1]=canon.object({id=sel.source.id,time=canon.float(now),code=up and canon.null or 'VPN-003',dns_ok=up,https_success=up and 2 or 0,
        interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',vendor_generation=t.GEN1})
      rows[#rows+1]=canon.object({id=sel.target.id,time=canon.float(now),code=canon.null,dns_ok=true,https_success=2,interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2})
      while #rows>0 and canon.number(rows[1].time)<now-900 do table.remove(rows,1) end
      local profiles=canon.array({canon.object({id=sel.source.id,interface='wgclient1',time=canon.float(now),code=up and canon.null or 'VPN-003',dns_ok=up,https_success=up and 2 or 0,vendor_state='SETTLED'}),
        canon.object({id=sel.target.id,interface='ovpnclient1',time=canon.float(now),code=canon.null,dns_ok=true,https_success=2,vendor_state='SETTLED'})})
      env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(now),samples=canon.array(rows),profiles=profiles})))
      local before=B.kernel[1]
      t.eq(pair.tick(env,settings,env.revision),true)
      local after=B.kernel[1]
      if before=='r1' and after=='r2' then log.switches[#log.switches+1]=at end
      if before=='r2' and after=='r1' then log.returns[#log.returns+1]=at end
      log.reserve[at]=(after=='r2')
      local st=t.read(env,env.runtime..'/native-status.json') or {}
      log.published[#log.published+1]={at,st.state,st.reason,st.source_failures,st.blockers}
      env.run.advance(step)
    end
  end)
  pair.charge_attempt=real_charge;T.attempt=real_attempt
  if not ok then error(err,0) end
  log.env=env;log.start=start
  return log
end

local function list(v) local out={};for i,x in ipairs(v) do out[i]=tostring(x) end;return table.concat(out,',') end

t.test('cycle 28: a vendor-aborted failover is retried within seconds, not after the cooldown',function()
  local log=sim({up=function(at) return not (at>=0 and at<150) end,stop=120,abort=function(l) return #l.dispatches==1 end})
  t.eq(log.aborts,{5},'detected after three failed samples, aborted by the vendor at APPLYING')
  t.eq(#log.switches,1,'dispatches '..list(log.dispatches))
  local moved=log.switches[1]
  t.truthy(moved-log.aborts[1]<=RETRY_BASE+2.5,'retried after the short backoff (alpha7: 60 s): moved at '..moved)
  t.truthy(moved-log.aborts[1]>=RETRY_BASE,'never hot: the backoff is kept')
  t.truthy(moved<=35,'within the 20-35 s band of the other 56 soak failovers')
  local held={}
  for _,p in ipairs(log.published) do
    if p[2]=='OBSERVING' and p[3]=='PAIR-RATE-LIMIT' and p[4]==true then held[#held+1]=p[1] end
  end
  t.eq(held,{7.5},'the one tick inside the backoff says why it waits')
  t.eq(log.attempts,log.dispatches,'no transaction is started inside the backoff')
  local ledger=t.read(log.env,ledger_path(log.env))
  t.eq(nums(ledger.events),{log.start+moved},'the aborted attempt is no switch')
  t.eq(nums(ledger.aborted),{log.start+5})
  t.eq(T.journal_read(log.env).phase,'COMMITTED')
end)

t.test('a non-vendor failure still waits the cooldown',function()
  local log=sim({up=function(at) return not (at>=0 and at<150) end,stop=120,abort=function(l) return #l.dispatches==1 end,code='CLIENT-CONFIRMATION-TIMEOUT'})
  t.eq(log.aborts,{5})
  t.truthy(log.switches[1]-5>=60,'switched at '..tostring(log.switches[1]))
end)

t.test('vendor busy: no dispatch while busy, the retry right after it ends',function()
  local log=sim({up=function(at) return not (at>=0 and at<150) end,stop=120,abort=function(l) return #l.dispatches==1 end,
    busy=function(at) return at>5 and at<40 end})
  t.eq(#log.busy_dispatch,0,'dispatched while busy at '..list(log.busy_dispatch))
  t.eq(log.dispatches,{5,40})
  local blocked=false
  for _,p in ipairs(log.published) do if p[2]=='BLOCKED' and p[5] and p[5][1]=='VENDOR-WORKER-BUSY' then blocked=true end end
  t.truthy(blocked,'BLOCKED VENDOR-WORKER-BUSY published')
end)

t.test('a vendor that never settles: growing backoff, never hot, no switch counted',function()
  local log=sim({up=function(at) return at<0 end,stop=900,abort=function() return true end})
  t.eq(#log.switches,0)
  t.eq(log.attempts,log.dispatches,'no transaction is started inside the backoff')
  local gaps={}
  for i=2,#log.dispatches do gaps[#gaps+1]=log.dispatches[i]-log.dispatches[i-1] end
  t.eq({gaps[1],gaps[2],gaps[3],gaps[4]},{5,10,20,40},'gaps '..list(gaps))
  for i=5,#gaps do t.eq(gaps[i],60,'gaps '..list(gaps)) end
  t.truthy(#log.dispatches<=20,'bounded: '..#log.dispatches)
  local ledger=t.read(log.env,ledger_path(log.env))
  t.eq(#ledger.events,0,'no aborted attempt is counted as a switch')
  t.truthy(#ledger.aborted<=pair.ABORT_KEEP)
end)

-- flap 60/120 x10, tick 10 s, 30 s stability base (as test_flap_damping.lua): the first failover of every outage
-- aborted by the vendor; the returns stay damped exactly as without the aborts.
local DOWN,UP,CYCLES=60,120,10
local function flap_up(at) local o=at-30;return o<0 or o>=(DOWN+UP)*CYCLES or o%(DOWN+UP)>=DOWN end
t.test('flap 60/120 x10: returns damped as without aborts, every outage left',function()
  local function run(aborting)
    local last=nil
    return sim({up=flap_up,stop=30+(DOWN+UP)*CYCLES+300,step=10,settings={recovery_primary_stable='30'},
      abort=function(l,at) local outage=math.floor((at-30)/(DOWN+UP));local first=last~=outage;last=outage;return aborting and first end})
  end
  local plain,aborted=run(false),run(true)
  t.truthy(#aborted.aborts>0,'the vendor aborted failovers')
  t.eq(aborted.returns,plain.returns,'the same damped returns')
  t.eq(#aborted.switches,#plain.switches)
  t.truthy(#aborted.returns<CYCLES,'damping kept the reserve through a recovery')
  for k=0,CYCLES-1 do
    local down=30+k*(DOWN+UP)
    for at=down+50,down+DOWN-10,10 do
      if not aborted.reserve[at] then error('traffic on the dead primary at '..at..' s; switches '..list(aborted.switches),0) end
    end
  end
end)

t.run()
