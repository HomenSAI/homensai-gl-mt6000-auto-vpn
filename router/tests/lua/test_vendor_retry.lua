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
  local value={phase='ROLLED-BACK',failure_code=QUIET,started=canon.float(9000),pair_transition=canon.object({destination_role='target'}),
    rtp_dispatched=false,forward_policy_touched=false}
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
    {'a newer transaction',{started=canon.float(9001.5)},QUIET},
    -- review 04.11.2026 (finding 6): the vendor code came after the switch itself (the verify wait after rtp2, wait_quiet
    -- after the dispatch): two real kernel switches (there and back) are no abort
    {'after the kernel switch',{rtp_dispatched=true},QUIET},
    {'after a policy write',{forward_policy_touched=true},QUIET},
    {'a journal without the dispatch flags',{rtp_dispatched=canon.null},QUIET}}
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
    policy_roles=(not opts.no_roles) and pair.policy.proof(sel) or nil}))
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
  B.vendor_busy_seen=opts.seen
  B.diagnostic=function()
    local at=env.run.wall()-start
    if armed then
      local ok,j=pcall(T.journal_read,env)
      if ok and j.phase=='APPLYING' then armed=false;log.aborts[#log.aborts+1]=at;return {opts.code or QUIET},nil end
    end
    if opts.busy and opts.busy(at) then return {'VENDOR-WORKER-BUSY'},opts.busy_selection and B.selection or nil end
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
      log.published[#log.published+1]={at,st.state,st.reason,st.source_failures,st.blockers,st}
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

------------------------------------------------------------------------------------------------------
-- a long VENDOR-WORKER-BUSY: what was seen is visible; the blocker itself stays
------------------------------------------------------------------------------------------------------
local LOCK=canon.decode(read_file(t.here..'/../vendor_lock_cases.json'))
local DEAD={kind='rtp-lock-dead',mark='rtp-lock:9:24680',pid=24680,workers=1}
t.test('busy_seen_step: the shared cases',function()
  t.eq({pair.BUSY_SEEN_SECONDS,pair.BUSY_SCAN_SECONDS},{120,30})
  for _,case in ipairs(LOCK.cases) do
    local track,got,scans,last=nil,{},{},nil
    for index,tick in ipairs(case.ticks) do
      local row
      track,row=pair.busy_seen_step(track,tick[2],canon.number(tick[1]),function(scan)
        if scan then scans[#scans+1]=index-1 end
        if tick[3]=='raise' then error('read failed') end
        return tick[3]
      end)
      got[index]=row and row.kind or canon.null
      last=row
    end
    t.eq(canon.encode(canon.array(got)),canon.encode(case.expect),case.name)
    t.eq(canon.encode(canon.array(scans)),canon.encode(case.scans),case.name..': scans')
    local workers=last and last.workers;if workers==nil then workers=canon.null end
    t.eq(workers,case.workers,case.name..': workers')
  end
end)

t.test('every kind has its own code',function()
  local seen={}
  for kind,code in pairs(pair.BUSY_CODES) do t.truthy(string.find(code,'^VENDOR%-BUSY%-'),code);t.eq(seen[code],nil);seen[code]=kind end
  t.eq(pair.BUSY_CODES['rtp-lock-dead'],'VENDOR-BUSY-RTP-LOCK-DEAD');t.eq(pair.BUSY_CODES['rtp-lock-live'],'VENDOR-BUSY-RTP-LOCK-LIVE')
  t.eq(pair.BUSY_CODES['tunnel-switch'],'VENDOR-BUSY-TUNNEL-SWITCH');t.eq(pair.BUSY_CODES.workers,'VENDOR-BUSY-WORKERS');t.eq(pair.BUSY_CODES.unidentified,'VENDOR-BUSY-UNIDENTIFIED')
end)

local function none(v) return v==nil or v==canon.null end
local function with_log(fn)
  local durable=require('durable')
  local real,lines=durable.log,{}
  durable.log=function(line) lines[#lines+1]=line end
  local ok,err=pcall(fn,lines)
  durable.log=real
  if not ok then error(err,0) end
end

for _,no_roles in ipairs({false,true}) do
t.test('dead primary, healthy reserve, the rtp2 lock of a gone holder: its own code, the pair named, still no attempt, one log line'..(no_roles and ' (session without policy roles)' or ' (policy roles: every normal session)'),function()
  with_log(function(lines)
    local scans=0
    local log=sim({up=function(at) return at<0 end,busy=function() return true end,busy_selection=true,stop=1800,no_roles=no_roles,
      seen=function(scan) if scan then scans=scans+1 end;return DEAD end})
    t.eq(#log.dispatches,0,'the blocker is not bypassed');t.eq(#log.switches,0);t.eq(#log.attempts,0)
    local first
    local source,target=log.env.backend.selection.source.id,log.env.backend.selection.target.id
    for _,p in ipairs(log.published) do
      t.eq(p[2],'BLOCKED');t.eq(canon.encode(p[5]),'["VENDOR-WORKER-BUSY"]','the blockers are the same list as before')
      local st=p[6]
      t.eq(st.source,source,'at '..p[1]);t.eq(st.target,target)
      if p[1]<120 then t.truthy(none(p[3]),'at '..p[1]);t.eq(st.vendor_lock_pid,nil)
      else
        first=first or p[1]
        t.eq(p[3],'VENDOR-BUSY-RTP-LOCK-DEAD','at '..p[1]);t.eq(st.vendor_lock_pid,24680)
        t.truthy(canon.number(st.busy_seconds)>=120);t.eq(canon.number(st.vendor_workers),1,'the child that still runs is shown')
      end
    end
    t.eq(first,120)
    t.eq(#lines,1,'one log line, not one per tick: '..#lines)
    t.truthy(string.find(lines[1],'VENDOR-BUSY-RTP-LOCK-DEAD: VENDOR-WORKER-BUSY for 120 s, lock pid 24680, vendor workers seen 1; observed only',1,true),lines[1])
    t.truthy(scans<=57,'a worker scan every 30 s, not every tick: '..scans)
    local items={}
    for _,row in ipairs(t.read(log.env,log.env.persist..'/native-history.json').data.tail) do
      for _,code in ipairs(row.codes) do if code=='VENDOR-BUSY-RTP-LOCK-DEAD' then items[#items+1]=row end end
    end
    t.eq(#items,1,'one journal event, not one per tick')
    t.eq(items[1].source,source)
  end)
end)
end

t.test('each observed cause reaches the publication under its own code',function()
  for kind,code in pairs(pair.BUSY_CODES) do
    local log=sim({up=function(at) return at<0 end,busy=function() return true end,stop=125,
      seen=function() return {kind=kind,mark='k'} end})
    local last=log.published[#log.published]
    t.eq(last[3],code,kind);t.eq(#log.dispatches,0,kind)
  end
end)

t.test('the blocker ends: the failover follows at once, nothing was held back by the code',function()
  local log=sim({up=function(at) return at<0 end,busy=function(at) return at<300 end,busy_selection=true,stop=320,seen=function() return DEAD end})
  t.eq(log.switches,{300})
end)

t.test('one free tick ends the episode: the count starts again, also on the tick path that has no blockers to publish',function()
  for _,no_roles in ipairs({false,true}) do
    local log=sim({up=function() return true end,busy=function(at) return at<100 or at>=105 end,busy_selection=true,stop=240,no_roles=no_roles,seen=function() return DEAD end})
    local first
    for _,p in ipairs(log.published) do if p[3]=='VENDOR-BUSY-RTP-LOCK-DEAD' and not first then first=p[1] end end
    t.eq(first,225,'120 s after the blocker came back')
  end
end)

t.test('an observation that fails or a backend without one: unidentified, no attempt, the tick goes on',function()
  for _,seen in ipairs({function() error('read failed') end,function() return 'nonsense' end,false}) do
    for _,no_roles in ipairs({false,true}) do
      local log=sim({up=function(at) return at<0 end,busy=function() return true end,stop=125,seen=seen or nil,no_roles=no_roles})
      t.eq(log.published[#log.published][3],'VENDOR-BUSY-UNIDENTIFIED');t.eq(#log.dispatches,0)
      for _,p in ipairs(log.published) do
        if p[1]<120 then t.truthy(none(p[3])) end
        if no_roles then t.eq(p[6].source,nil,'no selection, nothing invented') end
      end
    end
  end
end)

t.test('other blockers name no pair and read nothing',function()
  local log=sim({up=function() return true end,stop=10,no_roles=true,seen=function() error('must not be asked') end})
  local env=log.env
  env.backend.diagnostic=function() return {'PROFILE-NOT-MONITORED'},env.backend.selection end
  for _=1,60 do pair.tick(env,t.settings(),env.revision);env.run.advance(2.5) end
  local st=t.read(env,env.runtime..'/native-status.json')
  t.eq(st.state,'BLOCKED');t.truthy(none(st.reason));t.eq(st.source,nil);t.eq(env.busy_track,nil)
end)

t.test('a transaction still meets the blocker: no path through the status code',function()
  local env=t.env()
  env.backend.diagnostic=function() return {'VENDOR-WORKER-BUSY'},env.backend.selection end
  env.busy_track={since=0,seen=0,mark_since=0,mark='k',kind='rtp-lock-dead',pid=24680}
  t.code('VENDOR-WORKER-BUSY',T.assert_selection,env,env.backend.selection)
end)

t.test('platform.vendor_busy_seen: what is seen, never more',function()
  local platform=require('platform')
  local function sys(fields)
    local s={proc={},alive={},busy=0,scans=0}
    for k,v in pairs(fields or {}) do s[k]=v end
    s.clock=function() return 1 end
    s.exists=function(path) return s.alive[path]==true end
    s.lstat=function(path)
      if path==platform.RTP_LOCK then return s.lock and {type=s.lock_type or 'reg',size=6,ino=9} or nil end
      if s.queue and string.find(path,'gl_reload_service',1,true) then return {type='dir'} end
    end
    s.read=function(path)
      if path==platform.RTP_LOCK then return s.lock end
      return s.proc[path]
    end
    s.dir=function(path)
      if path=='/var/run' then return s.switch_lock and {'tunnel-switch-1.lock'} or {} end
      return {'x'}
    end
    return s
  end
  local LOCKED='24680\n'
  local BASE='/proc/24680'
  local workers=platform.workers
  local args
  platform.workers=function(sy,deadline,ignore) sy.scans=sy.scans+1;args={deadline,ignore};return {busy=sy.busy,verified=sy.verified~=false,time=0} end
  local ok,err=pcall(function()
    local seen=platform.vendor_busy_seen
    local row=seen(sys({lock=LOCKED}))
    t.eq(row.kind,'rtp-lock-dead');t.eq(row.pid,24680);t.eq(row.mark,'rtp-lock:9:24680');t.eq(row.workers,nil)
    local quiet=sys({lock=LOCKED});row=seen(quiet,true)
    t.eq(args,{3,true},'the lock file itself does not count as a worker');t.eq(row.workers,0);t.eq(quiet.scans,1)
    local unscanned=sys({lock=LOCKED});seen(unscanned);t.eq(unscanned.scans,0,'no /proc scan on a plain tick')
    row=seen(sys({lock=LOCKED,busy=2}),true);t.eq(row.kind,'rtp-lock-dead','a dead holder stays what was seen');t.eq(row.workers,2,'its children may run')
    row=seen(sys({lock=LOCKED,verified=false}),true);t.eq(row.workers,nil,'unverified is not zero')
    row=seen(sys({lock=LOCKED,alive={[BASE]=true},proc={[BASE..'/cmdline']='/bin/sh\0/usr/bin/rtp2.sh\0'}}));t.eq(row.kind,'rtp-lock-live')
    row=seen(sys({lock=LOCKED,alive={[BASE]=true},proc={[BASE..'/cmdline']='dnsmasq\0'}}));t.eq(row.kind,'rtp-lock-dead','the number went to another process')
    row=seen(sys({lock=LOCKED,alive={[BASE]=true},proc={[BASE..'/cmdline']=''}}));t.eq(row.kind,'rtp-lock-dead','a zombie does not run')
    row=seen(sys({lock=LOCKED,alive={[BASE]=true}}));t.eq(row.kind,'unidentified','a failed read proves no death');t.eq(row.pid,24680)
    row=seen(sys({lock=LOCKED,lock_type='lnk'}));t.eq(row.kind,'unidentified','a link is never trusted')
    row=seen(sys({lock='garbage'}));t.eq(row.kind,'unidentified');t.eq(row.mark,'rtp-lock:9')
    row=seen(sys({switch_lock=true}));t.eq(row.kind,'tunnel-switch')
    row=seen(sys({lock=LOCKED,switch_lock=true}));t.eq(row.kind,'rtp-lock-dead','the rtp2 file is named first')
    row=seen(sys({}));t.eq(row.kind,'unidentified','no file proves nothing');t.eq(row.mark,'no-file')
    row=seen(sys({busy=1}),true);t.eq(row.kind,'workers')
    row=seen(sys({queue=true}),true);t.eq(row.kind,'workers')
    row=seen(sys({}),true);t.eq(row.kind,'unidentified','no file and no worker is still not quiet');t.eq(row.workers,0)
    t.eq(platform.rtp_lock_busy(sys({lock=LOCKED})),true,'the blocker stays for this very lock')
    t.eq(platform.ALLOWED_STALE_LOCK,nil,'nothing allowed the lock on the way')
  end)
  platform.workers=workers
  if not ok then error(err,0) end
end)

t.test('platform.workers: the lock file counts unless the caller asks what runs besides it',function()
  local platform=require('platform')
  local s={clock=function() return 1 end,wall=function() return 1 end,
    lstat=function(path) if path==platform.RTP_LOCK or path=='/proc/locks' then return {type='reg',size=0} end end,
    stat=function(path) if path=='/proc/locks' then return {type='reg',size=0} end end,
    read=function(path) if path==platform.RTP_LOCK then return '24680\n' end;if path=='/proc/locks' then return '' end end,
    dir=function() return {} end}
  t.eq(platform.workers(s).busy,1)
  t.eq(platform.workers(s,nil,true).busy,0)
end)

-- the Telegram notice ----------------------------------------------------------------------------------------------
local telegram=require('telegram')
local function notice_d(send)
  local d={runtime='/run/hv',files={},sent={},removed=0}
  d.read=function(path) return d.files[path] end
  d.size=function(path) return d.files[path] and #d.files[path] or nil end
  d.is_link=function() return false end
  d.write=function(path,text) d.files[path]=text end
  d.remove=function(path) d.files[path]=nil;d.removed=d.removed+1 end
  d.lock=function(fn) return fn() end
  d.send=send or function(config,text) d.sent[#d.sent+1]=text end
  return d
end
local function native(reason,fields)
  local value=canon.object({state='BLOCKED',reason=reason,time=canon.float(1000),busy_seconds=125,vendor_lock_pid=24680,vendor_workers=1})
  for k,v in pairs(fields or {}) do value[k]=v end
  return canon.object({native_failover=value})
end
t.test('the notice: the shared text and key, every code has a text',function()
  for _,case in ipairs(LOCK.notices) do
    t.eq(telegram.vendor_notice_key(case.native,1000),case.key)
    t.eq(telegram.vendor_notice_text(case.native),case.text)
  end
  for _,code in pairs(pair.BUSY_CODES) do t.truthy(telegram.NOTICE_TEXT[code],code) end
  t.truthy(string.find(telegram.NOTICE_TEXT['VENDOR-BUSY-RTP-LOCK-DEAD'],'does not prove',1,true));t.truthy(string.find(telegram.NOTICE_TEXT['VENDOR-BUSY-UNIDENTIFIED'],'does not prove',1,true))
  for _,text in pairs(telegram.NOTICE_TEXT) do t.eq(string.find(string.lower(text),'quiet',1,true),nil);t.eq(string.find(string.lower(text),'stale',1,true),nil) end
end)
t.test('the notice: once per cause and pid, again for another, again after the state ended; no schedule field moves',function()
  local d=notice_d()
  local state=canon.object({sent=canon.float(990),confirmed_reports=4})
  local out=telegram.vendor_notice(d,{},native('VENDOR-BUSY-RTP-LOCK-DEAD'),state,1001)
  t.eq(#d.sent,1);t.eq(out.sent,state.sent);t.eq(out.attempt,nil,'a report is not pushed back');t.eq(out.confirmed_reports,4);t.eq(out.period_keys,nil)
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-RTP-LOCK-DEAD'),state,1002);t.eq(#d.sent,1,'no second notice')
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-RTP-LOCK-DEAD',{vendor_lock_pid=24681}),state,1003);t.eq(#d.sent,2,'another pid')
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-RTP-LOCK-LIVE',{vendor_lock_pid=24681}),state,1004);t.eq(#d.sent,3,'another cause')
  telegram.vendor_notice(d,{},canon.object({native_failover=canon.object({state='OBSERVING',time=canon.float(1005)})}),state,1005)
  t.eq(d.files['/run/hv/'..telegram.NOTICE_FILE],nil)
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-RTP-LOCK-LIVE',{vendor_lock_pid=24681}),state,1006);t.eq(#d.sent,4,'a new episode')
  t.truthy(string.find(d.sent[1],'Observed:',1,true))
end)
local function deliver_d()
  local d=notice_d()
  d.config=function() return {telegram_enabled='1',telegram_chat='-100',telegram_token='123:synthetic',telegram_schedule='interval',telegram_interval='60',telegram_weekly='0',telegram_monthly='0'} end
  d.sha256=function() return string.rep('ab',32) end
  d.wall=function() return 1001 end
  d.sleep=function() end
  return d
end
t.test('the notice goes through deliver(): no report is due, it is sent, the schedule stays; a running backoff holds it',function()
  local d=deliver_d()
  local saved=canon.object({sent=canon.float(990),attempt=canon.float(990),retry_after=canon.float(5)})
  local public,state,sent=telegram.deliver(d,native('VENDOR-BUSY-RTP-LOCK-DEAD'),saved,1001)
  t.eq(#d.sent,1,'told at once');t.eq(sent,false,'no report was sent');t.eq(public.code,nil)
  t.eq(canon.number(state.sent),990,'the report schedule did not move');t.eq(canon.number(state.attempt),990)
  t.truthy(telegram.valid(state),'the sender state keeps its schema')
  local held=deliver_d()
  telegram.deliver(held,native('VENDOR-BUSY-RTP-LOCK-DEAD'),canon.object({sent=canon.float(990),attempt=canon.float(1000),retry_after=canon.float(300)}),1001)
  t.eq(#held.sent,0,'the Telegram backoff holds for a notice too')
end)

t.test('the notice: only for a fresh BLOCKED with one of the codes',function()
  local d=notice_d()
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-WORKERS'),canon.object(),1000+telegram.NOTICE_MAX_AGE+1);t.eq(#d.sent,0,'an old status')
  telegram.vendor_notice(d,{},native('PAIR-WAITING-PROBES'),canon.object(),1001);t.eq(#d.sent,0)
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-WORKERS',{state='ARMED'}),canon.object(),1001);t.eq(#d.sent,0)
  telegram.vendor_notice(d,{},canon.object(),canon.object(),1001);t.eq(#d.sent,0)
end)
t.test('the notice: a failed send keeps the usual backoff and comes again, a confirmed one is not repeated',function()
  local tries,fail=0,true
  local d=notice_d(function() tries=tries+1;if fail then error(telegram.rejection(429,600),0) end end)
  local out=telegram.vendor_notice(d,{},native('VENDOR-BUSY-WORKERS'),canon.object(),1001)
  t.eq(out.last_code,'TELEGRAM-RATE-LIMIT');t.eq(canon.number(out.retry_after),600);t.eq(canon.number(out.attempt),1001);t.eq(canon.number(out.known_failures),1)
  t.eq(d.files['/run/hv/'..telegram.NOTICE_FILE],nil)
  fail=false
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-WORKERS'),out,1010);t.eq(tries,2)
  telegram.vendor_notice(d,{},native('VENDOR-BUSY-WORKERS'),out,1020);t.eq(tries,2)
end)

t.run()
