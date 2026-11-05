-- forward_resume.lua (03.11.2026). MT3000 2.1.0-alpha5: the Auto process was SIGKILLed in the middle of an automatic
-- switch to the reserve (APPLYING) while the primary stayed down; the recovery rolled back onto the dead primary, tore
-- the pair down and rebuilt it, then switched again: 128 s without internet on the LAN (normal failover ~20 s).
-- Here the real attempt() runs on the harness router and is "killed" at a chosen point: from that moment every
-- durable write (files, UCI, kernel, guard) raises, exactly like SIGKILL leaves the state. Then the restarted
-- supervisor's recover() runs and the monitor's restart resume presses Start. Python: tests/test_forward_resume.py.
-- Shared decide() cases: tests/forward_resume_cases.json.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local A=require('auto')
local R=require('rollback')
local ctl=require('auto_control')
local pair=require('pair')
local control=require('control_request')
local boot_resume=require('boot_resume')
local durable=require('durable')
local FR=require('forward_resume')
local platform=require('platform')
platform.rtp_contract=function() end              -- the pinned rtp2.sh / board / firmware: present
platform.rtp_checked=function() return {} end      -- the prefix directories and the gate: present, owned, empty

local PRIMARY,RESERVE='wireguard:peer_1','openvpn:1_1'
local BEFORE,AFTER={'r1','r2'},{'r2','r1'}
-- the normal automatic failover on the MT3000 (MEASUREMENTS, 2.1.0): ~20 s from the outage to traffic on the reserve
local NORMAL_BUDGET=20
local KILLED={code='SIGKILL'}

local log_lines={}
durable.log=function(line) log_lines[#log_lines+1]=line end

-- the router of tests/lua/test_boot_held.lua: a RUNNING continuous pair session, both clients up, the owner's marker.
-- Time costs of the network steps (a quiet wait, an ifup/ifdown) are modelled so that the old path shows its length.
local function router()
  local WG,OVPN='wgclient1','ovpnclient1'
  local env=t.env()
  local B=env.backend
  local up={[WG]=true,[OVPN]=true}
  env.up=up
  env.net_log={ifup={},ifdown={},quiet=0}
  B.health_of[PRIMARY]=false  -- the primary's output is dropped
  local guard=B.guard
  B.guard=function(devices,revision)
    if devices~=nil and #devices==0 then error(setmetatable({code='UNSAFE-GUARD-DEVICE'},ctl.Refused),0) end
    return guard(devices,revision)
  end
  B.devices=function() local out={};for _,name in ipairs({OVPN,WG}) do if up[name] then out[#out+1]=name end end;return out end
  local rows=canon.array({canon.object({['.name']=WG,proto='wgclient',auto='0',disabled='0'}),canon.object({['.name']=OVPN,proto='ovpnclient',auto='0',disabled='0'})})
  env.net={network=function() return canon.decode(canon.encode(rows)) end,identity=function() return string.rep('aa',32) end,
    configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function(name) return not up[name] end,
    ifup=function(name,revision) env.run.require_revision(revision);env.net_log.ifup[#env.net_log.ifup+1]=name;up[name]=true;env.run.advance(2) end,
    ifdown=function(name) env.net_log.ifdown[#env.net_log.ifdown+1]=name;up[name]=false;env.run.advance(2) end,
    quiet=function() env.net_log.quiet=env.net_log.quiet+1;env.run.advance(10) end,
    set_disabled=function() end,interface_exists=function(name) return up[name] end}
  local sel=B.selection
  local id=string.rep('11',16)
  B.settings.native_trial=id  -- pair.configure_lease: the session id is the lease nonce
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=id,request_source='manual'})))
  pair.save(env,canon.object({id=id,phase='RUNNING',ran=true,started=canon.float(env.run.wall()-600),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({[WG]='wgclient',[OVPN]='ovpnclient'}),protected=canon.object({}),owned=canon.array({WG,OVPN}),
    before_flags=canon.object({[WG]='0',[OVPN]='0'}),process_bindings=sel.process_bindings,order=canon.array(BEFORE),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)}))
  env.run.fs.write_atomic(env.persist..'/'..boot_resume.MARKER,boot_resume.marker(env.run.wall()-900))
  -- the rtp_boot of deps.lua with the real gates of platform.lua (prepare's owner-intent fence under the control lock);
  -- only the file primitives of the stock boot prefix are stubbed (all present, pinned). MT3000 2.1.0-alpha7,
  -- 03.11.2026: without rtp_boot here the real prepare() never ran and the router refused CLIENT-STOP on every
  -- untouched-kernel resume.
  env.rtp_calls={}
  local sys_={}
  env.deps.rtp_boot={
    assess=function() return platform.rtp_assess(sys_) end,
    prepare=function(revision) env.rtp_calls[#env.rtp_calls+1]='prepare';return platform.rtp_prepare(env,sys_,revision) end,
    ready=function() if not pcall(platform.rtp_ready,sys_) then ctl.refuse('RTP-BOOT-PRECONDITION-UNVERIFIED') end;return true end,
    recovery_prefix=function() env.rtp_calls[#env.rtp_calls+1]='recovery_prefix'
      if not pcall(platform.rtp_recovery_prefix,sys_) then ctl.refuse('RTP-BOOT-PRECONDITION-UNVERIFIED') end;return true end,
  }
  return env
end

-- SIGKILL model: from kill() on, every durable write raises (files, UCI order, kernel, guard)
local function killable(env)
  local k={on=false}
  local fs=env.run.fs
  for _,name in ipairs({'write_atomic','remove','rename'}) do
    local f=fs[name];fs[name]=function(...) if k.on then error(KILLED,0) end;return f(...) end
  end
  local B=env.backend
  for _,name in ipairs({'reorder','apply','guard','unguard','clear_native_options','write_lease'}) do
    local f=B[name];B[name]=function(...) if k.on then error(KILLED,0) end;return f(...) end
  end
  function k.kill() k.on=true;error(KILLED,0) end
  return k
end

-- where the process dies: wraps the named backend call so the kill lands before or after it
local POINTS={
  ['before-reorder']={'reorder','before'},   -- APPLYING, nothing written yet
  ['after-reorder']={'apply','before'},      -- APPLYING, UCI moved, kernel untouched
  ['after-kernel']={'apply','after'},        -- APPLYING, kernel on the reserve, verifying (the MT3000 evidence)
  ['trace']={'trace','before'},              -- APPLYING, apply done, the exit trace running
  ['wait-client']={'probe','before'},        -- WAIT-CLIENT, confirming
}
local function kill_at(env,k,point)
  local name,when=POINTS[point][1],POINTS[point][2]
  local B=env.backend
  local f=B[name]
  B[name]=function(...)
    if when=='before' then B[name]=f;k.kill() end
    local r={f(...)}
    B[name]=f;k.kill()
    return unpack(r)
  end
end

-- the monitor (boot_resume) as it runs on the router: started long before, it has seen the old token
local function monitor(env)
  local fs=env.run.fs
  local deps={read=function(p) if p=='/proc/sys/kernel/random/uuid' then return ctl.uuid_hex() end;return fs.read(p) end,
    write=function(p,text) fs.write_atomic(p,text) end,exists=function(p) return fs.read(p)~=nil end,
    now=env.run.wall,clock=env.run.clock,runtime=env.runtime,persist=env.persist,try_lock=function(fn) return true,fn() end,
    native_policy=function() return canon.encode(env.backend.policy()) end,journal=function() return T.journal_read(env) end,
    auto_blocker=function() return nil end,preparation=function() return {checks={}} end,
    read_state=function() return pair.read_state(env) end,intent=function() return pair.intent(env) end}
  local r=boot_resume.new({read=deps.read,exists=deps.exists,now=env.run.wall,runtime=env.runtime,persist=env.persist,
    write_ram=function(p,text) fs.write_atomic(p,text) end,FALLBACK=control.FALLBACK,uptime=function() return env.run.clock() end,
    intent=function() return pair.intent(env) end,revision=function() return ctl.revision_locked(env) end,
    start=function(arguments) return control.start(deps,arguments) end,fallback=function() error('no agent.py here',0) end})
  r.tick()
  return r
end

-- the LAN goes out through the reserve: kernel role target, VPN-only guard
local function lan_on_reserve(env)
  local B=env.backend
  local ok,r=pcall(pair.policy.role,pair.policy.proof(B.selection),canon.array(B.kernel))
  return ok and r=='target' and B.guarded==true and B.guard_calls[#B.guard_calls]=='vpn-only'
end

-- the automatic failover of pair.tick, killed at point; returns env, the kill switch, the monitor, the APPLYING time
local function crashed(point,opts)
  opts=opts or {}
  log_lines={}
  pair.revive_log_reset();pair.handover_log_reset()
  local env=router()
  if opts.setup then opts.setup(env) end
  local r=monitor(env)
  local k=killable(env)
  kill_at(env,k,point)
  local started=env.run.wall()
  local ok,err=pcall(T.attempt,env,env.backend.selection,env.run.wall()+180,false,{control_revision=env.revision,pair_session_order=canon.array(BEFORE),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
  t.eq(ok,false,'the attempt was killed');t.eq(err,KILLED,'killed, not refused')
  -- procd restarts the process: RAM (runtime) kept, no reboot, the nft guard and the kernel as they were
  k.on=false
  env.run.advance(opts.restart_delay or 5)
  env.slept={}
  return env,k,r,started
end

local function rollbacks()
  local calls={}
  local original=R.rollback
  R.rollback=function(env,value,reason,...) calls[#calls+1]=reason;return original(env,value,reason,...) end
  return calls,function() R.rollback=original end
end

local function history_states(env)
  local out={}
  for _,row in ipairs(t.history(env).events) do out[#out+1]=row.state..':'..tostring(row.reason) end
  return out
end

------------------------------------------------------------------------------------------------------
-- decide(): the shared cases
------------------------------------------------------------------------------------------------------
t.test('decide(): every shared case (tests/forward_resume_cases.json) gives the same code as in Python',function()
  local f=io.open(t.here..'/../forward_resume_cases.json','rb');local text=f:read('*a');f:close()
  local data=canon.decode(text)
  t.truthy(#data.cases>=30,'the shared cases')
  for _,case in ipairs(data.cases) do
    local j=canon.decode(canon.encode(data.journal))
    for key,v in pairs(case.set or {}) do j[key]=v end
    for _,key in ipairs(case.unset or {}) do j[key]=nil end
    local facts={};for key,v in pairs(data.facts) do facts[key]=v end
    for key,v in pairs(case.facts or {}) do facts[key]=v end
    local expect=case.expect;if expect==canon.null then expect=nil end
    t.eq(FR.decide(j,facts),expect,case.name)
  end
end)

t.test('decide(): the live probes run only when every cheaper check passed',function()
  local probed=0
  local j=canon.object({tx=string.rep('ab',16),phase='APPLYING',proof_scope='router-probed-ipv4',pair_transition=canon.object({destination_role='target',before_policy_role='source'}),
    trial=false,transition_source='automatic',before=canon.array(BEFORE),after=canon.array(AFTER),started=1000,deadline=1120,monotonic_deadline=620})
  local facts={same_boot=true,wall=1020,mono=520,wanted=false,stopping=false,source_health=function() probed=probed+1;return false end,
    reserve_health=function() probed=probed+1;return true end}
  t.eq(FR.decide(j,facts),'OWNER-STOP');t.eq(probed,0)
  facts.wanted=true
  t.eq(FR.decide(j,facts),nil);t.eq(probed,2)
end)

------------------------------------------------------------------------------------------------------
-- end to end: killed in the middle of the switch, finished forward after the restart
------------------------------------------------------------------------------------------------------
t.test('end to end (MT3000 evidence): killed while verifying in APPLYING - the restart finishes the switch, no rollback, no pair rebuild, Auto adopts the reserve',function()
  local env,_,r,started=crashed('after-kernel')
  local j=T.journal_read(env)
  t.eq(j.phase,'APPLYING');t.eq(env.backend.kernel,AFTER,'the kernel was already on the reserve');t.eq(env.backend.guard_calls[#env.backend.guard_calls],'full')
  t.eq(lan_on_reserve(env),false,'the LAN is blocked (full guard) while the process is dead')
  local calls,restore=rollbacks()
  local restart=env.run.wall()
  local kernel_seen={}
  local apply=env.backend.apply
  env.backend.apply=function(...) local x={apply(...)};kernel_seen[#kernel_seen+1]=table.concat(env.backend.kernel,',');return unpack(x) end
  -- while the restarted supervisor confirms (WAIT-CLIENT), the LAN already goes out through the reserve
  local probe,confirming=env.backend.probe,nil
  env.backend.probe=function(...) if confirming==nil then confirming=lan_on_reserve(env) end;return probe(...) end
  t.eq(A.recover(env),'ready')
  env.backend.probe=probe
  t.eq(confirming,true,'VPN-only guard and the reserve kernel before the confirmation')
  restore()
  j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'COMMITTED',FR.REASON})
  t.eq({j.forward_resumed.from_phase,j.forward_resumed.kernel,j.forward_resumed.stage},{'APPLYING','reserve','apply'})
  t.eq(#calls,0,'no rollback');t.eq(#kernel_seen,0,'no kernel write: the reserve graph was proven and kept')
  t.eq(env.backend.uci,AFTER);t.truthy(lan_on_reserve(env),'traffic on the reserve, VPN-only guard')
  t.truthy(canon.number(j.confirmed)-restart<=NORMAL_BUDGET,'traffic on the reserve within the normal failover budget after the restart')
  t.truthy(canon.number(j.confirmed)-started<=2*NORMAL_BUDGET,'and within two budgets of the switch start (was 128 s on the router)')
  t.eq(#env.net_log.ifdown,0,'no pair teardown');t.eq(#env.net_log.ifup,0,'no pair rebuild')
  local state=pair.read_state(env)
  t.eq(state.phase,'STOPPED');t.eq(state.handover.tx,j.tx,'handed over to the restart Start');t.eq(state.kept,canon.array({'wgclient1','ovpnclient1'}))
  t.eq(pair.intent(env).mode,'off','the restarted supervisor never resumes Auto by itself')
  -- the monitor sees the new supervisor token and presses the owner's Start; the new session adopts the reserve
  t.eq(r.tick(),'RESUMED');t.eq(pair.intent(env).mode,'on')
  A.iteration(env,{last_return=0,consumed=canon.object({}),last_attempt=0})
  j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'COMMITTED','BOOT-RESERVE-ADOPTED'});t.eq(j.boot_adopted.from_reason,FR.REASON)
  t.eq(pair.read_state(env).phase,'RUNNING');t.eq(#env.net_log.ifup,0,'the kept clients adopted, no second ifup')
  t.truthy(lan_on_reserve(env),'still on the reserve')
  t.truthy(env.run.wall()-restart<=NORMAL_BUDGET,'Auto running again within the budget')
  local states=history_states(env)
  for _,s in ipairs(states) do t.truthy(not string.find(s,'RESTORING',1,true) and not string.find(s,'ROLLED-BACK',1,true),'no rollback in the history: '..s) end
  local found=false;for _,l in ipairs(log_lines) do if string.find(l,'SUPERVISOR-FORWARD-RESUMED',1,true) then found=true end end
  t.truthy(found,'one log line')
end)

t.test('control: the same kill without forward_resume rolls back onto the dead primary and tears the pair down',function()
  local env=crashed('after-kernel')
  local try=FR.try
  FR.try=function() return false,'DISABLED' end
  local restart=env.run.wall()
  local ok=pcall(A.recover,env)
  FR.try=try
  t.truthy(ok)
  local j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'ROLLED-BACK','SUPERVISOR-RECOVERY'})
  t.eq(env.backend.kernel,BEFORE,'the LAN back on the failed primary');t.eq(lan_on_reserve(env),false)
  t.eq(env.net_log.ifdown,{'ovpnclient1','wgclient1'},'both clients stopped');t.eq(pair.read_state(env).phase,'STOPPED')
  t.truthy(env.run.wall()-restart>NORMAL_BUDGET,'and the teardown alone is longer than a normal failover')
end)

t.test('the finished switch ends the LAN flows still NATed to the primary once (flow_reset); a failing reset never undoes it',function()
  for _,failing in ipairs({false,true}) do
    local env=crashed('after-kernel')
    local resets={}
    env.backend.flow_reset=function(old,new)
      resets[#resets+1]={old,new}
      if failing then error('conntrack exploded') end
      return {code='FLOW-RESET-DONE',deleted=1}
    end
    t.eq(A.recover(env),'ready')
    local j=T.journal_read(env)
    t.eq({j.phase,j.reason},{'COMMITTED',FR.REASON})
    t.eq(resets,{{PRIMARY,RESERVE}});t.truthy(lan_on_reserve(env))
  end
end)

for _,point in ipairs({'before-reorder','after-reorder','trace','wait-client'}) do
  t.test('end to end: killed at '..point..' - finished forward after the restart',function()
    local env,_,r=crashed(point)
    local from=T.journal_read(env).phase
    local calls,restore=rollbacks()
    local restart=env.run.wall()
    t.eq(A.recover(env),'ready')
    restore()
    local j=T.journal_read(env)
    t.eq({j.phase,j.reason},{'COMMITTED',FR.REASON});t.eq(#calls,0)
    t.eq(j.forward_resumed.from_phase,from)
    local untouched=point=='before-reorder' or point=='after-reorder'
    t.eq(j.forward_resumed.kernel,untouched and 'untouched' or 'reserve')
    if untouched then t.eq({j.rtp_dispatched,j.forward_policy_touched},{true,true},'the redone writes are recorded') end
    t.eq(env.backend.uci,AFTER);t.eq(env.backend.kernel,AFTER);t.truthy(lan_on_reserve(env))
    t.truthy(canon.number(j.confirmed)-restart<=NORMAL_BUDGET)
    t.eq(#env.net_log.ifdown,0);t.eq(pair.read_state(env).handover.tx,j.tx)
    t.eq(r.tick(),'RESUMED')
    A.iteration(env,{last_return=0,consumed=canon.object({}),last_attempt=0})
    t.eq(T.journal_read(env).reason,'BOOT-RESERVE-ADOPTED')
  end)
end

------------------------------------------------------------------------------------------------------
-- unsafe variants: the old rollback, unchanged
------------------------------------------------------------------------------------------------------
local function rolled_back(env,why,resumed_before)
  local calls,restore=rollbacks()
  local ok,err=pcall(A.recover,env)
  restore()
  local j=T.journal_read(env)
  t.eq(calls[1],'SUPERVISOR-RECOVERY',why..': the old rollback ran')
  if not resumed_before then t.eq(j.forward_resumed,nil,why..': nothing resumed') end
  t.truthy(j.phase~='COMMITTED' or j.reason~=FR.REASON,why)
  return j,ok,err
end

local function refused_for(code)
  for _,l in ipairs(log_lines) do if l=='SUPERVISOR-FORWARD: rollback ('..code..')' then return true end end
  return false
end

local UNSAFE={
  {'the reserve is not healthy',function(env) env.backend.health_of[RESERVE]=false end,'RESERVE-NOT-HEALTHY'},
  {'the primary came back',function(env) env.backend.health_of[PRIMARY]=true end,'SOURCE-NOT-FAILED'},
  {'the primary unknown',function(env) env.backend.health=function(id) if id==PRIMARY then return nil end;return true end end,'SOURCE-NOT-FAILED'},
  {'the owner pressed Stop while the process was dead',function(env) env.run.advance(1);ctl.stop_latch(env,canon.null) end,'OWNER-STOP'},
  {'no owner marker (Auto not started by the owner)',function(env) env.run.fs.remove(env.persist..'/'..boot_resume.MARKER) end,'OWNER-STOP'},
  {'the transaction is nearly over',function(env) env.run.advance(110) end,'EXPIRED'},
  {'a power cut: RAM gone, monotonic clock restarted',function(env)
    for path in pairs(env.run.fs.files) do if string.sub(path,1,#env.runtime+1)==env.runtime..'/' and not string.find(path,'auto-control-revision',1,true) then env.run.fs.files[path]=nil end end
    env.run.mono_now=40 end,'OTHER-BOOT'},
  {'the reserve tunnel was rebuilt (new vendor generation)',function(env)
    local sel=canon.decode(canon.encode(env.backend.selection));sel.target.vendor_generation=string.rep('03',16);env.backend.selection=sel end,'IDENTITY'},
  {'the pair session changed (another session id)',function(env) local s=pair.read_state(env);s.id=string.rep('22',16);pair.save(env,s) end,'PAIR-SESSION'},
  {'the service is stopping',function(env) env.stopped=true end,'OWNER-STOP'},
}
for _,case in ipairs(UNSAFE) do
  t.test('unsafe, rolls back as before: '..case[1],function()
    local env=crashed('after-kernel')
    case[2](env)
    rolled_back(env,case[1])
    t.truthy(refused_for(case[3]),case[1]..': refused for '..case[3])
  end)
end

t.test('unsafe, rolls back as before: an interrupted manual switch',function()
  log_lines={}
  local env=router()
  local k=killable(env);kill_at(env,k,'after-kernel')
  local ok,err=pcall(T.attempt,env,env.backend.selection,env.run.wall()+180,false,{control_revision=env.revision,pair_session_order=canon.array(BEFORE),
    manual_request_id=string.rep('ab',16),request_source='manual',pair_destination='target'})
  t.eq(err,KILLED);k.on=false;env.run.advance(5)
  local j=rolled_back(env,'manual')
  t.truthy(refused_for('NOT-AUTOMATIC'),'refused as a manual switch')
  t.eq({j.phase,j.reason},{'ROLLED-BACK','SUPERVISOR-RECOVERY'});t.eq(env.backend.kernel,BEFORE)
end)

t.test('unsafe: a kernel graph that is neither the recorded one nor the reserve is never written forward',function()
  local env=crashed('after-kernel')
  env.backend.kernel={'r2','r1','x'}  -- a foreign graph (a vendor rebuild in between)
  local before=T.journal_read(env)
  local calls,restore=rollbacks()
  pcall(A.recover,env)
  restore()
  t.eq(calls[1],'SUPERVISOR-RECOVERY');t.eq(T.journal_read(env).forward_resumed,nil);t.eq(env.backend.kernel,{'r2','r1','x'},'nothing written by the resume')
  t.eq(before.phase,'APPLYING');t.truthy(refused_for('KERNEL'))
end)

t.test('unsafe: a foreign UCI order (external change) is never resumed',function()
  -- a changed policy hash, and (the kernel still the recorded one, so only the order check stands) a foreign order
  for _,case in ipairs({{'after-kernel',{'r1','r2','x'},string.rep('cd',32)},{'before-reorder',{'r1','x','r2'},nil}}) do
    local env=crashed(case[1])
    env.backend.uci=case[2];if case[3] then env.backend.hash=case[3] end
    local calls,restore=rollbacks()
    pcall(A.recover,env)
    restore()
    t.eq(T.journal_read(env).forward_resumed,nil);t.truthy(T.journal_read(env).phase~='COMMITTED');t.truthy(refused_for('ORDER'),case[1])
    t.eq(env.backend.uci,case[2],'nothing written forward')
  end
end)

t.test('no double action: killed again during the resume - the second restart rolls back (one resume per transaction)',function()
  local env,k=crashed('after-kernel')
  kill_at(env,k,'wait-client')
  local ok,err=pcall(A.recover,env)
  t.eq(err,KILLED,'killed while the resume confirmed')
  local j=T.journal_read(env)
  t.eq(j.phase,'WAIT-CLIENT');t.eq(j.forward_resumed.from_phase,'APPLYING')
  k.on=false;env.run.advance(5);pair.handover_log_reset()
  local j2=rolled_back(env,'second restart',true)
  t.eq({j2.phase,j2.reason},{'ROLLED-BACK','SUPERVISOR-RECOVERY'});t.truthy(refused_for('ALREADY-RESUMED'))
  t.eq(env.backend.kernel,BEFORE)
end)

t.test('owner Stop wins during the resume: the new revision fences every write, then the old rollback',function()
  local env=crashed('after-kernel')
  local probe=env.backend.probe
  env.backend.probe=function(...) env.backend.probe=probe;ctl.stop_latch(env,canon.null);return probe(...) end
  local calls,restore=rollbacks()
  pcall(A.recover,env)
  restore()
  local j=T.journal_read(env)
  t.eq(calls[1],'SUPERVISOR-RECOVERY');t.eq({j.phase,j.reason},{'ROLLED-BACK','SUPERVISOR-RECOVERY'})
  t.eq(j.forward_resumed.from_phase,'APPLYING','the resume was recorded before it was refused')
  t.eq(env.backend.kernel,BEFORE);t.eq(pair.intent(env).mode,'off');t.truthy(refused_for('CLIENT-STOP'))
end)

------------------------------------------------------------------------------------------------------
-- MT3000 2.1.0-alpha7, 03.11.2026 15:07:59: SIGKILL the moment the status showed APPLYING (kernel untouched). The
-- restart rotated the control revision and fenced the pair intent off (every restart does), the resume logged
-- 'resuming ... (kernel untouched)' and refused CLIENT-STOP in rtp_boot.prepare() (it wants a running owner intent of
-- the new revision); the rollback onto the dead primary and the pair teardown followed: 129.8 s without internet.
------------------------------------------------------------------------------------------------------
t.test('router alpha7: killed as APPLYING showed (kernel untouched) - the restart finishes forward through the real restart fences',function()
  local env=crashed('before-reorder')
  local j=T.journal_read(env)
  t.eq(j.phase,'APPLYING');t.eq(env.backend.kernel,BEFORE);t.eq(env.backend.uci,BEFORE)
  t.eq({pair.intent(env).mode,ctl.revision_locked(env)},{'on',env.revision},'the owner Auto on, the revision unchanged')
  env.rtp_calls={}
  local calls,restore=rollbacks()
  local restart=env.run.wall()
  t.eq(A.recover(env),'ready')
  restore()
  t.truthy(ctl.revision_locked(env)~=env.revision,'the restart rotated the control revision')
  t.eq(pair.intent(env).mode,'off','and fenced the pair intent: the monitor restart resume presses Start')
  t.eq(refused_for('CLIENT-STOP'),false,'no CLIENT-STOP')
  j=T.journal_read(env)
  t.eq({j.phase,j.reason,j.forward_resumed.kernel},{'COMMITTED',FR.REASON,'untouched'})
  local prefixed=false;for _,c in ipairs(env.rtp_calls) do if c=='recovery_prefix' then prefixed=true end end
  t.truthy(prefixed,'the stock boot prefix checked before the redone writes')
  t.eq(#calls,0,'no rollback');t.truthy(lan_on_reserve(env))
  t.eq(#env.net_log.ifdown,0,'neither client stopped: the reserve carries the LAN')
  t.truthy(canon.number(j.confirmed)-restart<=NORMAL_BUDGET)
end)

t.test('router alpha7: an owner Stop during the redone writes still wins (CLIENT-STOP, the old rollback)',function()
  local env=crashed('before-reorder')
  local reorder=env.backend.reorder
  env.backend.reorder=function(...) env.backend.reorder=reorder;ctl.stop_latch(env,canon.null);return reorder(...) end
  local calls,restore=rollbacks()
  pcall(A.recover,env)
  restore()
  local j=T.journal_read(env)
  t.truthy(refused_for('CLIENT-STOP'),'refused CLIENT-STOP')
  t.eq(calls[1],'SUPERVISOR-RECOVERY');t.eq({j.phase,j.reason},{'ROLLED-BACK','SUPERVISOR-RECOVERY'})
  t.eq(j.forward_resumed.kernel,'untouched');t.eq(env.backend.kernel,BEFORE);t.eq(pair.intent(env).mode,'off')
end)

-- the alpha7 router after the refusal: the rollback onto the dead primary, then the pair cleanup of this restart (uptime
-- past the boot window) stopped BOTH clients, the healthy reserve too (~20 s), and the restart Start brought them up
-- again (~26 s). A refused resume now keeps them for the restart Start like the boot cleanup does (variant C).
local function refused_restart(env)
  env.run.advance(110)  -- the transaction nearly over: refused EXPIRED, the old rollback onto the primary
  local calls,restore=rollbacks()
  t.eq(A.recover(env),'ready')
  restore()
  t.truthy(env.run.clock()>pair.BOOT_KEEP_UPTIME,'not a boot')
  t.truthy(refused_for('EXPIRED'),'refused');t.eq(calls[1],'SUPERVISOR-RECOVERY')
  local j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'ROLLED-BACK','SUPERVISOR-RECOVERY'});t.eq(env.backend.kernel,BEFORE)
  return j
end

t.test('router alpha7: a refused resume keeps the pair clients (the healthy reserve) up for the restart Start, which adopts them',function()
  local env,_,r=crashed('before-reorder')
  local j=refused_restart(env)
  t.eq(#env.net_log.ifdown,0,'neither client stopped by the cleanup')
  local state=pair.read_state(env)
  t.eq(state.phase,'STOPPED');t.eq(state.kept,canon.array({'wgclient1','ovpnclient1'}));t.eq(state.kept_tx,j.tx)
  t.eq(env.backend.guard_calls[#env.backend.guard_calls],'vpn-only','the VPN-only guard stays until the Start')
  -- a supervisor pass before the monitor's Start: still kept
  t.eq(pair.tick(env,env.backend.settings,ctl.revision_locked(env)),false)
  t.eq(#env.net_log.ifdown,0);t.truthy(pair.read_state(env).kept~=nil)
  -- the monitor's restart resume presses the owner's Start: the new session adopts the running clients
  t.eq(r.tick(),'RESUMED');t.eq(pair.intent(env).mode,'on')
  A.iteration(env,{last_return=0,consumed=canon.object({}),last_attempt=0})
  local s=pair.read_state(env)
  t.eq(s.phase,'RUNNING');t.eq(s.owned,canon.array({'wgclient1','ovpnclient1'}),'adopted as owned')
  t.eq(#env.net_log.ifup,0,'no ifup');t.eq(#env.net_log.ifdown,0,'no ifdown')
end)

t.test('router alpha7: the kept clients of a refused resume are released when the restart resume fails (as before)',function()
  local env=crashed('before-reorder')
  refused_restart(env)
  local token=t.read(env,env.runtime..'/'..boot_resume.SUPERVISOR).id
  env.run.fs.write_atomic(env.runtime..'/'..boot_resume.STATE,canon.encode(canon.object({state='FAILED',supervisor=token})))
  t.eq(pair.tick(env,env.backend.settings,ctl.revision_locked(env)),true)
  t.eq(env.net_log.ifdown,{'ovpnclient1','wgclient1'},'both clients stopped as the old cleanup did')
  local s=pair.read_state(env);t.eq(s.kept,nil);t.eq(s.kept_tx,nil);t.eq(s.phase,'STOPPED')
end)

t.test('a power cut (OTHER-BOOT) writes no restart marker: the boot cleanup keeps its own boot window',function()
  local env=crashed('before-reorder')
  for path in pairs(env.run.fs.files) do if string.sub(path,1,#env.runtime+1)==env.runtime..'/' and not string.find(path,'auto-control-revision',1,true) then env.run.fs.files[path]=nil end end
  env.run.mono_now=40
  rolled_back(env,'power cut')
  t.truthy(refused_for('OTHER-BOOT'))
  t.eq(env.run.fs.read(env.runtime..'/'..FR.FILE),nil,'no marker');t.eq(pair.read_state(env).kept_tx,nil)
end)

t.test('the restart resume failing ends the handover: the cleanup goes on as before (primary proof wait)',function()
  local env,_,r=crashed('after-kernel')
  t.eq(A.recover(env),'ready')
  t.truthy(pair.read_state(env).handover~=nil)
  -- the monitor's resume of this supervisor start fails (e.g. the restart limit)
  local token=t.read(env,env.runtime..'/'..boot_resume.SUPERVISOR).id
  env.run.fs.write_atomic(env.runtime..'/'..boot_resume.STATE,canon.encode(canon.object({state='FAILED',supervisor=token})))
  local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  A.iteration(env,ctx)
  local state=pair.read_state(env)
  t.eq(state.handover,nil);t.eq(state.phase,'HELD')
  t.eq(T.journal_read(env).phase,'COMMITTED','the reserve keeps the traffic while the primary is down');t.truthy(lan_on_reserve(env))
end)

t.test('the handover of a resumed switch outlives the boot window and its one-per-boot marker',function()
  local env=crashed('after-kernel',{setup=function(env)
    env.run.fs.write_atomic(env.runtime..'/'..pair.HANDOVER_FILE,canon.encode(canon.object({state='handed',tx=string.rep('99',16)})))
  end})
  t.truthy(env.run.clock()>pair.BOOT_KEEP_UPTIME,'not a boot')
  t.eq(A.recover(env),'ready')
  t.eq(pair.read_state(env).handover.tx,T.journal_read(env).tx)
  t.eq(t.read(env,env.runtime..'/'..pair.HANDOVER_FILE).state,'handed')
end)

-- K5 (formal model 03.11.2026, FORMAL-FIXES-2026-11-03.ru.md): the last revision check and the COMMITTED write of the
-- resume run inside one control lock (a Stop rotates the revision under that lock: before the check or after the write)
t.test('K5: the resume checks the revision and writes COMMITTED under one control lock',function()
  local env=crashed('wait-client')
  local run=env.run
  local epoch,inside=0,nil
  local lock=run.lock
  run.lock=function(fn,directory)
    epoch=epoch+1
    local mine=epoch
    return lock(function() local outer=inside;inside=mine;local r={pcall(fn)};inside=outer;if not r[1] then error(r[2],0) end;return unpack(r,2) end,directory)
  end
  local checked,committed=false,nil
  local require_revision=run.require_revision
  run.require_revision=function(...) require_revision(...);checked=inside or false end
  local write=T.journal_write
  T.journal_write=function(e,value)
    if value.phase=='COMMITTED' and committed==nil then committed={checked=checked,inside=inside} end
    return write(e,value)
  end
  local ok,err=pcall(A.recover,env)
  T.journal_write,run.lock,run.require_revision=write,lock,require_revision
  t.truthy(ok,tostring(err))
  t.eq(T.journal_read(env).reason,FR.REASON)
  t.truthy(committed~=nil and committed.inside~=nil,'COMMITTED written under the control lock')
  t.eq(committed.checked,committed.inside,'the last revision check before it inside the same lock')
end)

t.run()
