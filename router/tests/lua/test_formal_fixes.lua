-- Formal model of the Auto supervisor (03.11.2026, private/math/formal/model.py): each counterexample trace of
-- K2, K3, K4, K5, K9 and the K1 tail replayed on the Lua supervisor. Each test fails on integ/alpha7 (0215164a)
-- and passes with the fix. Python twin: tests/test_formal_fixes.py (+ test_held_start_handover.py for K1).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local A=require('auto')
local ctl=require('auto_control')
local pair=require('pair')
local control=require('control_request')
local boot_resume=require('boot_resume')
local durable=require('durable')

-- the router of test_boot_held.lua: a RUNNING pair session, a manual switch held on the reserve (or an automatic
-- COMMITTED one with opts.flow='committed'), the owner's resume marker
local function router(opts)
  opts=opts or {}
  local WG,OVPN='wgclient1','ovpnclient1'
  local IFACE={['wireguard:peer_1']=WG,['openvpn:1_1']=OVPN}
  local env=t.env()
  local B=env.backend
  local up={[WG]=true,[OVPN]=true}
  local up_at={[WG]=-1e9,[OVPN]=-1e9}
  env.names={WG,OVPN}
  local net_log={ifup={},ifdown={}}
  env.up,env.up_at,env.net_log=up,up_at,net_log
  local guard=B.guard
  B.guard=function(devices,revision)
    if devices~=nil and #devices==0 then error(setmetatable({code='UNSAFE-GUARD-DEVICE'},ctl.Refused),0) end
    return guard(devices,revision)
  end
  B.devices=function() local out={};for _,name in ipairs({OVPN,WG}) do if up[name] then out[#out+1]=name end end;return out end
  B.health=function(id) local name=IFACE[id];return name~=nil and up[name] end
  B.recovery_ready=function(id) return B.health(id) end
  local rows=canon.array({canon.object({['.name']=WG,proto='wgclient',auto='0',disabled='0'}),
    canon.object({['.name']=OVPN,proto='ovpnclient',auto='0',disabled='0'})})
  env.rows=rows
  env.identity=string.rep('aa',32)
  env.net={network=function() return canon.decode(canon.encode(rows)) end,
    identity=function() return env.identity end,configs=function() return canon.object({}) end,
    changed=function() return false end,
    client_down=function(name) return not up[name] end,
    ifup=function(name,revision)
      env.run.require_revision(revision)
      net_log.ifup[#net_log.ifup+1]=name;up[name]=true;up_at[name]=env.run.clock()
    end,
    ifdown=function(name) net_log.ifdown[#net_log.ifdown+1]=name;up[name]=false end,
    quiet=function() end,set_disabled=function() end,interface_exists=function(name) return up[name] end}
  local sel=B.selection
  local id=string.rep('11',16)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=id,request_source='manual'})))
  pair.save(env,canon.object({id=id,phase='RUNNING',ran=true,started=canon.float(env.run.wall()-600),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({[WG]='wgclient',[OVPN]='ovpnclient'}),protected=canon.object({}),owned=canon.array({WG,OVPN}),
    before_flags=canon.object({[WG]='0',[OVPN]='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)}))
  if opts.flow=='committed' then
    T.attempt(env,sel,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
      probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
    t.eq(T.journal_read(env).phase,'COMMITTED','the committed journal before the cut')
  else
    T.attempt(env,sel,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),manual_request_id=string.rep('ab',16),
      request_source='manual',pair_destination='target',probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
    t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE','the held journal before the cut')
  end
  env.run.fs.write_atomic(env.persist..'/'..boot_resume.MARKER,boot_resume.marker(env.run.wall()-900))
  return env
end

-- sysrq-b: flash kept, RAM (runtime) empty, tunnels down, no nft guard, the kernel from UCI
local function cut(env)
  for path in pairs(env.run.fs.files) do if string.sub(path,1,#env.runtime+1)==env.runtime..'/' then env.run.fs.files[path]=nil end end
  for _,name in ipairs(env.names) do env.up[name]=false end
  pair.revive_log_reset();pair.handover_log_reset();if pair.outside_guard_reset then pair.outside_guard_reset() end
  env.backend.guarded=false;env.backend.guard_calls={}
  env.backend.kernel={};for i,x in ipairs(env.backend.uci) do env.backend.kernel[i]=x end
  env.run.mono_now=40
  env.slept={}
end
local function today(env) env.run.fs.write_atomic(env.runtime..'/'..pair.HANDOVER_FILE,canon.encode(canon.object({state='refused'}))) end
local function reserve_only(env)
  local sel=env.backend.selection
  local primary={ok=false}
  env.backend.health=function(id) if id==sel.target.id then return env.up['ovpnclient1'] end;return primary.ok and env.up['wgclient1'] end
  env.backend.recovery_ready=function(id) return env.backend.health(id) end
  return primary
end
local function fresh_ctx() return {last_return=0,consumed=canon.object({}),last_attempt=0} end
local function quiet_log() local log=durable.log;durable.log=function() end;return function() durable.log=log end end
local function start_deps(env,calls)
  local fs=env.run.fs
  return {read=function(p) if p=='/proc/sys/kernel/random/uuid' then return ctl.uuid_hex() end;return fs.read(p) end,
    write=function(p,text) fs.write_atomic(p,text) end,exists=function(p) return fs.read(p)~=nil end,
    now=env.run.wall,clock=env.run.clock,runtime=env.runtime,persist=env.persist,
    try_lock=function(fn) return true,fn() end,
    native_policy=function() return canon.encode(env.backend.policy()) end,
    journal=function() return T.journal_read(env) end,auto_blocker=function() return nil end,
    preparation=function() if calls then calls.preparation=(calls.preparation or 0)+1 end;return {checks={}} end,
    read_state=function() return pair.read_state(env) end,intent=function() return pair.intent(env) end}
end
local function resume_of(env)
  local deps=start_deps(env)
  return boot_resume.new({read=deps.read,exists=deps.exists,now=env.run.wall,runtime=env.runtime,persist=env.persist,
    write_ram=function(p,text) env.run.fs.write_atomic(p,text) end,FALLBACK=control.FALLBACK,
    uptime=function() return env.run.clock() end,intent=function() return pair.intent(env) end,
    revision=function() return ctl.revision_locked(env) end,
    start=function(arguments) return control.start(deps,arguments) end,fallback=function() error('no agent.py here',0) end})
end
local function last_guard(env) return env.backend.guard_calls[#env.backend.guard_calls] end

------------------------------------------------------------------------------------------------------
-- K3: power cut while the journal is HELD-ON-RESERVE and the session handed over (STOPPED + handover)
------------------------------------------------------------------------------------------------------
t.test('K3: a power cut inside the handover window - the VPN-only guard of the held reserve comes back in the recovery',function()
  local restore=quiet_log()
  local env=router()
  cut(env)
  reserve_only(env)
  t.eq(A.recover(env),'ready')
  t.truthy(pair.read_state(env).handover~=nil,'handed over to the boot resume Start')
  -- the second cut before the Start: RAM (guard, handover marker) lost, the session record STOPPED + handover stays
  cut(env)
  t.eq(A.recover(env),'ready')
  restore()
  local state=pair.read_state(env)
  t.eq(state.phase,'STOPPED');t.truthy(state.handover~=nil,'the handover itself is untouched')
  t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE');t.eq(env.backend.uci,{'r2','r1'},'traffic stays on the reserve')
  t.eq(env.backend.guarded,true,'the LAN is guarded again (K3: none until the handover was released, up to 600 s)')
  t.eq(last_guard(env),'vpn-only')
  t.eq(env.net_log.ifup,{'ovpnclient1','wgclient1','ovpnclient1','wgclient1'},'the handed-over clients were started for the guard')
  -- the Start still adopts the reserve as before
  t.eq(resume_of(env).tick(),'RESUMED')
end)

t.test('K3: a HELD-ON-RESERVE journal whose order changed is left to the loop (no guard on a foreign route)',function()
  local restore=quiet_log()
  local env=router()
  local state=pair.read_state(env);state.phase='STOPPED';pair.save(env,state)
  cut(env)
  env.backend.uci={'r1','r2'};env.backend.kernel={'r1','r2'}
  for _,name in ipairs(env.names) do env.up[name]=true end
  t.eq(A.recover(env),'ready')
  restore()
  t.eq(env.backend.guarded,false)
end)

------------------------------------------------------------------------------------------------------
-- K4: begin() with slow clients: the 90 s self-releasing block expired before guard(devices)
------------------------------------------------------------------------------------------------------
-- the kernel's view of the guard: the full block releases itself GUARD_RELEASE_SECONDS after it was armed
local function guard_clock(env)
  local B=env.backend
  local g={mode=nil,until_=nil,lapses={},full=0}
  local guard=B.guard
  B.guard=function(devices,revision)
    guard(devices,revision)
    if devices==nil then g.mode='full';g.until_=env.run.clock()+90;g.full=g.full+1 else g.mode='vpn';g.until_=nil end
  end
  local unguard=B.unguard
  B.unguard=function() unguard();g.mode=nil end
  function g.check(where)
    if g.mode=='full' and env.run.clock()>=g.until_ then g.lapses[#g.lapses+1]=where end
    if g.mode==nil then g.lapses[#g.lapses+1]=where..' (none)' end
  end
  -- slow vendor: quiet waits its whole bound, ifup -w 20 s
  env.net.quiet=function(seconds) env.run.advance(seconds);g.check('quiet '..seconds) end
  local ifup=env.net.ifup
  env.net.ifup=function(name,revision) ifup(name,revision);env.run.advance(20);g.check('ifup '..name) end
  return g
end

t.test('K4: Start with both clients down (quiet 20 + ifup -w + quiet 45 per role) - the LAN block never lapses',function()
  local restore=quiet_log()
  local env=router()
  local j=T.journal_read(env);j.phase='ROLLED-BACK';j.restored_order=canon.array({'r1','r2'});T.journal_write(env,j)
  env.backend.uci={'r1','r2'};env.backend.kernel={'r1','r2'}
  local state=pair.read_state(env);state.phase='STOPPED';pair.save(env,state)
  for _,name in ipairs(env.names) do env.up[name]=false end
  local g=guard_clock(env)
  local request=canon.object({id=string.rep('22',16),revision=env.revision})
  pair.save(env,state)
  local s=pair.begin(env,env.backend.settings,request)
  restore()
  t.eq(s.phase,'RUNNING');t.eq(env.net_log.ifup,{'wgclient1','ovpnclient1'})
  t.eq(#g.lapses,0,'the guard lapsed at: '..table.concat(g.lapses,', '))
  t.eq(g.mode,'vpn','guard(devices) at the end')
  t.truthy(g.full>=4,'re-armed before every bounded step ('..g.full..')')
end)

t.test('K4: Start after a boot handover (VPN-only on the reserve) - never downgraded to the self-releasing block',function()
  local restore=quiet_log()
  local env=router()
  cut(env)
  reserve_only(env)
  t.eq(A.recover(env),'ready')
  t.truthy(pair.read_state(env).handover~=nil)
  env.up['wgclient1']=false  -- the primary client still connecting: begin() starts it (the slowest path)
  t.eq(resume_of(env).tick(),'RESUMED')
  local g=guard_clock(env)
  g.mode='vpn'  -- what the handover left
  A.iteration(env,fresh_ctx())
  restore()
  local j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'COMMITTED','BOOT-RESERVE-ADOPTED'})
  t.eq(#g.lapses,0,'the guard lapsed at: '..table.concat(g.lapses,', '))
  t.eq(g.full,0,'VPN-only throughout, the reserve kept working for the LAN')
end)

------------------------------------------------------------------------------------------------------
-- K2: a restart must not reset the flap-damping hold of the return
------------------------------------------------------------------------------------------------------
-- the primary stable for env.stable seconds; recovery_ready honours recovery_primary_stable (set to 30 here)
local function damping(env)
  local B=env.backend
  -- primary_stable 30 s explicitly (the default is 120 s since the 03.11.2026 tuning, integ/alpha8)
  B.settings.recovery_primary_stable='30'
  env.stable=40
  B.recovery_ready=function(id,settings)
    local need=tonumber(settings and settings.recovery_primary_stable) or 30
    if id==B.selection.source.id then return B.health(id)==true and env.stable>=need end
    return B.health(id)==true
  end
  -- three failovers inside the window: attempt_limit 3 reached, hold = 2 * primary_stable = 60 s
  local now=env.run.wall()
  ctl.write_json(env.run,env.persist..'/pair-auto-budget.json',canon.object({events=canon.array({canon.float(now-300),canon.float(now-200),canon.float(now-100)})}))
  t.eq(pair.ledger_hold(env,B.settings,now),60)
end

t.test('K2: recovery cleanup after a restart keeps the damped hold (primary stable 40 s < hold 60 s): held on the reserve',function()
  local restore=quiet_log()
  local env=router({flow='committed'})
  cut(env);today(env)
  damping(env)
  t.eq(A.recover(env),'ready')
  local j=T.journal_read(env)
  t.eq(j.phase,'HELD-ON-RESERVE','K2: returned via recovery_ready without return_hold before the fix')
  t.eq(env.backend.uci,{'r2','r1'});t.eq(pair.read_state(env).phase,'HELD')
  -- the primary stable for the hold: the next cleanup pass returns
  env.stable=61
  A.iteration(env,fresh_ctx())
  restore()
  t.eq(T.journal_read(env).phase,'ROLLED-BACK');t.eq(env.backend.uci,{'r1','r2'})
end)

t.test('K2: an owner Stop or a failing reserve returns without the damped hold, as before',function()
  local restore=quiet_log()
  for _,case in ipairs({'stop','reserve'}) do
    local env=router({flow='committed'})
    cut(env);today(env)
    damping(env)
    if case=='stop' then env.run.advance(5);ctl.stop_latch(env,canon.null) end
    if case=='reserve' then
      local health=env.backend.health
      env.backend.health=function(id) if id==env.backend.selection.target.id then return false end;return health(id) end
    end
    t.eq(A.recover(env),'ready')
    t.eq(T.journal_read(env).phase,'ROLLED-BACK',case)
  end
  restore()
end)

t.test('K2: the boot handover check counts the primary as proven only after the damped hold',function()
  local restore=quiet_log()
  local env=router({flow='committed'})
  cut(env)
  damping(env)
  t.eq(A.recover(env),'ready')
  restore()
  local state=pair.read_state(env)
  t.truthy(state.handover~=nil,'handed over on the reserve (PRIMARY-PROVEN with primary_stable before the fix)')
  t.eq(T.journal_read(env).phase,'COMMITTED');t.eq(env.backend.uci,{'r2','r1'})
end)

------------------------------------------------------------------------------------------------------
-- K5: the revision check and the COMMITTED write under one lock
------------------------------------------------------------------------------------------------------
t.test('K5: an owner Stop right after the last revision check is never followed by a COMMITTED write',function()
  local env=t.env()
  local run=env.run
  local events={}
  local armed,checks,pending=false,0,false
  local function stop()
    events[#events+1]='stop'
    run.fs.write_atomic(env.runtime..'/auto-control-revision.json',canon.encode(canon.object({revision=string.rep('99',16)})))
  end
  -- the confirmation branch's assert_selection (journal WAIT-CLIENT) arms the Stop at the second check after it
  local assert_selection=T.assert_selection
  T.assert_selection=function(e,sel) if T.journal_read(e).phase=='WAIT-CLIENT' then armed=true;checks=0 end;return assert_selection(e,sel) end
  local require_revision=run.require_revision
  run.require_revision=function(expected,directory)
    require_revision(expected,directory)
    if armed then
      checks=checks+1
      if checks==2 then
        armed=false
        -- the Stop needs the control lock (auto_control.stop rotates the revision under it)
        if run.locks>0 then pending=true else stop() end
      end
    end
  end
  local lock=run.lock
  run.lock=function(fn,directory)
    local r={pcall(lock,fn,directory)}
    if pending and run.locks==0 then pending=false;stop() end
    if not r[1] then error(r[2],0) end
    return unpack(r,2)
  end
  local write=T.journal_write
  T.journal_write=function(e,value) if value.phase=='COMMITTED' and T.journal_read(e).phase~='COMMITTED' then events[#events+1]='commit' end;return write(e,value) end
  local ok=pcall(T.attempt,env,env.backend.selection,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
  T.assert_selection,T.journal_write=assert_selection,write
  t.eq(events,{'commit','stop'},'COMMITTED-AFTER-STOP before the fix')
end)

------------------------------------------------------------------------------------------------------
-- K9 (owner decision 03.11.2026): a session HELD by an outside GL change keeps the VPN-only guard after a power cut
------------------------------------------------------------------------------------------------------
-- Auto ran on the primary (journal ROLLED-BACK), the owner changed the VPN clients in the GL panel: HELD with
-- PAIR-EXTERNAL-NETWORK-CHANGE, the guard VPN-only from the running session
local function held_by_gl(env)
  local j=T.journal_read(env);j.phase='ROLLED-BACK';j.restored_order=canon.array({'r1','r2'});T.journal_write(env,j)
  env.backend.uci={'r1','r2'};env.backend.kernel={'r1','r2'}
  local state=pair.read_state(env);state.phase='HELD';state.recovery_error='PAIR-EXTERNAL-NETWORK-CHANGE';pair.save(env,state)
  env.identity=string.rep('bb',32)
  env.backend.guarded=true
end

t.test('K9: power cut after a GL edit - the guard comes back (full block while no tunnel is up, re-armed; VPN-only once one is)',function()
  local restore=quiet_log()
  local env=router()
  held_by_gl(env)
  cut(env)
  t.eq(A.recover(env),'ready')
  local state=pair.read_state(env)
  t.eq({state.phase,state.recovery_error},{'HELD','PAIR-EXTERNAL-NETWORK-CHANGE'})
  t.eq(env.backend.guarded,true,'K9: the LAN went out through the GL configuration before')
  t.eq(last_guard(env),'full','no VPN tunnel is up: no internet')
  local ctx=fresh_ctx()
  local count=#env.backend.guard_calls
  env.run.advance(10);A.iteration(env,ctx)
  t.eq(#env.backend.guard_calls,count,'not re-armed on every pass')
  env.run.advance(pair.OUTSIDE_REARM);A.iteration(env,ctx)
  t.eq(#env.backend.guard_calls,count+1,'re-armed before the 90 s self-release');t.eq(last_guard(env),'full')
  env.up['ovpnclient1']=true
  env.run.advance(5);A.iteration(env,ctx)
  t.eq(last_guard(env),'vpn-only','LAN only through the VPN tunnel that is up')
  count=#env.backend.guard_calls
  env.run.advance(60);A.iteration(env,ctx)
  t.eq(#env.backend.guard_calls,count,'VPN-only is not reinstalled while the tunnels stay the same')
  restore()
end)

t.test('K9: the owner Stop releases the guard; it stays released',function()
  local restore=quiet_log()
  local env=router()
  held_by_gl(env)
  cut(env)
  env.up['ovpnclient1']=true
  t.eq(A.recover(env),'ready')
  t.eq(env.backend.guarded,true);t.eq(last_guard(env),'vpn-only')
  env.run.advance(5);ctl.stop_latch(env,canon.null);pair.stop_locked(env,ctl.revision_locked(env))
  local ctx=fresh_ctx()
  A.iteration(env,ctx)
  t.eq(env.backend.guarded,false,'Stop releases as before')
  env.run.advance(60);A.iteration(env,ctx)
  t.eq(env.backend.guarded,false,'and nothing guards again')
  -- and after a later power cut too (the Stop latch is on flash)
  cut(env)
  t.eq(A.recover(env),'ready')
  t.eq(env.backend.guarded,false)
  restore()
end)

t.test('K9 + K4: the Start that ends the outside-change hold keeps its VPN-only guard while the clients start',function()
  local restore=quiet_log()
  local env=router()
  held_by_gl(env)
  cut(env)
  env.up['ovpnclient1']=true
  t.eq(A.recover(env),'ready')
  t.eq(last_guard(env),'vpn-only','the outside-change hold')
  -- the Start's hand-over (pair_auto.release_for_start in agent.py) archived the old session
  local state=pair.read_state(env);state.phase='STOPPED';state.owned=canon.array({});state.recovery_error=nil;pair.save(env,state)
  local g=guard_clock(env)
  g.mode='vpn'
  local s=pair.begin(env,env.backend.settings,canon.object({id=string.rep('33',16),revision=ctl.revision_locked(env)}))
  restore()
  t.eq(s.phase,'RUNNING')
  t.eq(#g.lapses,0,'the guard lapsed at: '..table.concat(g.lapses,', '))
  t.eq(g.full,0,'never downgraded to the self-releasing full block')
  t.eq(pair.outside_guard_mode(),nil,'the hold is over')
end)

t.test('K9/K2: an older Stop latch is not the Stop of a later (programmatic) session',function()
  local env=router()
  local state=pair.read_state(env)
  env.run.fs.files[env.persist..'/'..boot_resume.MARKER]=nil
  local function latch(at) env.run.fs.write_atomic(env.persist..'/native-stop.json',canon.encode(canon.object({requested=canon.float(at)}))) end
  t.eq(pair.owner_stopped(env,state),false,'no latch')
  latch(ctl.num(state.started)-100)
  t.eq(pair.owner_stopped(env,state),false,'a Stop before this session started')
  t.eq(pair.owner_stopped(env,nil),true,'no start known: the latch is the Stop')
  latch(ctl.num(state.started)+1)
  t.eq(pair.owner_stopped(env,state),true,'a Stop after this session started')
  env.run.fs.write_atomic(env.persist..'/'..boot_resume.MARKER,boot_resume.marker(ctl.num(state.started)+2))
  t.eq(pair.owner_stopped(env,state),false,'the owner Started again after it')
  env.run.fs.write_atomic(env.persist..'/native-stop.json','{damaged')
  t.eq(pair.owner_stopped(env,state),false,'a damaged latch is not a Stop')
end)

t.test('K9: a held journal or a non-readopt HELD code is not this hold',function()
  local restore=quiet_log()
  local env=router()
  local state=pair.read_state(env);state.phase='HELD';state.recovery_error='PAIR-EXTERNAL-NETWORK-CHANGE';pair.save(env,state)
  t.eq(pair.outside_hold(env),false,'HELD-ON-RESERVE keeps its own guard rules')
  held_by_gl(env)
  state=pair.read_state(env);state.recovery_error='UNSAFE-GUARD-DEVICE';pair.save(env,state)
  t.eq(pair.outside_hold(env),false)
  restore()
end)

------------------------------------------------------------------------------------------------------
-- K11: the owner's Start hands the outside-change hold over (release_session, under the control lock) while a
-- cleanup pass of the supervisor already read the HELD record
------------------------------------------------------------------------------------------------------
t.test('K11: a cleanup pass in flight never writes STOPPING over the Start hand-over',function()
  local restore=quiet_log()
  local env=router()
  held_by_gl(env)
  pair.stop_locked(env,ctl.revision_locked(env))  -- Auto off: the tick cleans the HELD session up
  local interfaces=pair.state_interfaces
  local raced=nil
  pair.state_interfaces=function(state)
    -- the first step of cleanup(): the owner's Start hands the session over right now
    if raced==nil then raced=false;raced=pair.release_session(env,pair.read_state(env),'PAIR-EXTERNAL-NETWORK-CHANGE') end
    return interfaces(state)
  end
  local ok,err=pcall(pair.tick,env,env.backend.settings,ctl.revision_locked(env))
  pair.state_interfaces=interfaces
  restore()
  t.truthy(ok,tostring(err));t.eq(raced,true)
  local state=pair.read_state(env)
  t.eq(state.phase,'STOPPED','K11: the stale cleanup wrote STOPPING over the hand-over (then HELD again)')
  t.eq(state.operator_resolution.trigger,'PAIR-EXTERNAL-NETWORK-CHANGE')
  pair.tick(env,env.backend.settings,ctl.revision_locked(env))
  t.eq(pair.read_state(env).phase,'STOPPED','a later pass leaves the handed-over record alone')
end)

-- the same race on the failure path (an error before the STOPPING write, e.g. PAIR-EXTERNAL-POLICY-CHANGE):
-- publish_failure reads the record and writes HELD, both under the control lock of the hand-over
t.test('K11: a failure marks the record HELD only under the control lock',function()
  local restore=quiet_log()
  local env=router()
  held_by_gl(env)
  local run=env.run
  local inside=false
  local lock=run.lock
  run.lock=function(fn,directory)
    return lock(function() local outer=inside;inside=true;local r={pcall(fn)};inside=outer;if not r[1] then error(r[2],0) end;return unpack(r,2) end,directory)
  end
  local writes={}
  local save=pair.save
  pair.save=function(e,state) writes[#writes+1]={state.phase,inside};return save(e,state) end
  local ok,err=pcall(pair.publish_failure,env,'PAIR-EXTERNAL-POLICY-CHANGE')
  pair.save,run.lock=save,lock
  t.truthy(ok,tostring(err))
  t.eq(writes,{{'HELD',true}},'K11: HELD written outside the control lock')
  t.eq(pair.read_state(env).recovery_error,'PAIR-EXTERNAL-POLICY-CHANGE')
  t.eq(pair.release_session(env,pair.read_state(env),'PAIR-EXTERNAL-POLICY-CHANGE'),true)
  pair.publish_failure(env,'PAIR-RECOVERY-REQUIRED')
  restore()
  t.eq(pair.read_state(env).phase,'STOPPED','a failure after the hand-over leaves its record alone')
end)

------------------------------------------------------------------------------------------------------
-- K1 tail: the boot resume's programmatic Start reaches the early hand-over (agent.py) with the owner's marker
------------------------------------------------------------------------------------------------------
t.test('K1 tail: a programmatic Start with the owner resume marker goes to the hand-over before preparation; Stop wins',function()
  local restore=quiet_log()
  for _,case in ipairs({'manual','resume','no-marker','stopped'}) do
    local env=router()
    held_by_gl(env)
    pair.stop_locked(env,ctl.revision_locked(env))
    if case=='no-marker' then env.run.fs.files[env.persist..'/'..boot_resume.MARKER]=nil end
    if case=='stopped' then ctl.stop_latch(env,canon.null) end
    local calls={}
    local reply=control.start(start_deps(env,calls),canon.object({control_revision=ctl.revision_locked(env),request_source=case=='manual' and 'manual' or 'programmatic'}))
    t.eq(reply,control.FALLBACK,case)
    if case=='manual' or case=='resume' then t.eq(calls.preparation,nil,case..': handed to agent.py before the preparation snapshot')
    else t.eq(calls.preparation,1,case..': the ordinary path') end
  end
  restore()
end)

t.run()
