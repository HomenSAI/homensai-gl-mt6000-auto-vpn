-- Power cut with a held journal (MT3000 sysrq-b, 31.10.2026, evidence-alpha13-powercut-held.json):
-- before the cut Auto was on, the journal HELD-ON-RESERVE (OPERATOR-MANUAL), the pair session RUNNING. After the
-- boot the intent (RAM) is gone, the prepared router leaves the VPN clients down (the vendor autostart is off; the
-- pair starts them), the guard refuses an empty device list (UNSAFE-GUARD-DEVICE). Before the fix the pair cleanup
-- failed on every pass, the journal stayed HELD-ON-RESERVE and Start (and the boot resume) was refused
-- TRANSACTION-IN-PROGRESS forever. Now the supervisor starts the pair's own clients, the journal settles without
-- any owner action, and the boot resume's Start succeeds - also across a forward NTP step of the wall clock.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local A=require('auto')
local ctl=require('auto_control')
local pair=require('pair')
local control=require('control_request')
local boot_resume=require('boot_resume')
local durable=require('durable')

-- a router with a RUNNING pair session and a manual switch held on the reserve
-- opts: settle, wg/ovpn (interface names), owned (list), flow ('held' | 'committed'), protected/live (config digests)
local function router(opts)
  opts=opts or {}
  local WG,OVPN=opts.wg or 'wgclient1',opts.ovpn or 'ovpnclient1'
  local IFACE={['wireguard:peer_1']=WG,['openvpn:1_1']=OVPN}
  local env=t.env()
  local B=env.backend
  local up={[WG]=true,[OVPN]=true}
  local up_at={[WG]=-1e9,[OVPN]=-1e9}
  env.names={WG,OVPN}
  local net_log={ifup={},ifdown={}}
  env.up,env.up_at,env.net_log=up,up_at,net_log
  -- the real guard refuses an empty device list
  local guard=B.guard
  B.guard=function(devices,revision)
    if devices~=nil and #devices==0 then error(setmetatable({code='UNSAFE-GUARD-DEVICE'},ctl.Refused),0) end
    return guard(devices,revision)
  end
  B.devices=function() local out={};for _,name in ipairs({OVPN,WG}) do if up[name] then out[#out+1]=name end end;return out end
  -- a channel is healthy only some time after its client came up (probes need fresh samples)
  local settle=opts.settle or 0
  B.health=function(id) local name=IFACE[id];return name~=nil and up[name] and env.run.clock()-up_at[name]>=settle end
  B.recovery_ready=function(id) return B.health(id) end
  local rows=canon.array({canon.object({['.name']=WG,proto='wgclient',auto='0',disabled='0'}),
    canon.object({['.name']=OVPN,proto='ovpnclient',auto='0',disabled='0'})})
  env.rows=rows
  env.live=opts.live or canon.object({})
  env.net={network=function() return canon.decode(canon.encode(rows)) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.decode(canon.encode(env.live)) end,
    changed=function(state,observed,skip)  -- net.changed: protected digests against the live ones, minus skip
      local skipped={};for k,v in pairs(skip or {}) do if type(k)=='number' then skipped[v]=true else skipped[k]=v end end
      for name,sha in pairs(state.protected) do if name~='route_policy' and not skipped[name] and observed[name]~=sha then return true end end
      return false
    end,
    client_down=function(name) return not up[name] end,
    ifup=function(name,revision)
      env.run.require_revision(revision)  -- Stop-fenced like forward_dispatch
      net_log.ifup[#net_log.ifup+1]=name;up[name]=true;up_at[name]=env.run.clock()
    end,
    ifdown=function(name) net_log.ifdown[#net_log.ifdown+1]=name;up[name]=false end,
    quiet=function() end,set_disabled=function() end,interface_exists=function(name) return up[name] end}
  local sel=B.selection
  local id=string.rep('11',16)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=id,request_source='manual'})))
  pair.save(env,canon.object({id=id,phase='RUNNING',ran=true,started=canon.float(env.run.wall()-600),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({[WG]='wgclient',[OVPN]='ovpnclient'}),protected=opts.protected or canon.object({}),owned=canon.array(opts.owned or {WG,OVPN}),
    before_flags=canon.object({[WG]='0',[OVPN]='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel)}))
  if opts.flow=='committed' then
    -- an automatic switch to the reserve: COMMITTED, reason null
    T.attempt(env,sel,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
      probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
    local j=T.journal_read(env)
    t.eq(j.phase,'COMMITTED','the committed journal before the cut')
  else
    -- the owner's manual switch: HELD-ON-RESERVE / OPERATOR-MANUAL as its stable phase
    T.attempt(env,sel,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),manual_request_id=string.rep('ab',16),
      request_source='manual',pair_destination='target',probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
    local j=T.journal_read(env)
    t.eq({j.phase,j.reason},{'HELD-ON-RESERVE','OPERATOR-MANUAL'},'the held journal before the cut')
  end
  -- the owner's own Start was remembered on flash before
  env.run.fs.write_atomic(env.persist..'/'..boot_resume.MARKER,boot_resume.marker(env.run.wall()-900))
  return env
end

-- the router after sysrq-b: flash kept, RAM (runtime) empty, the tunnels down, no nft guard, the kernel from UCI
local function cut(env)
  for path in pairs(env.run.fs.files) do if string.sub(path,1,#env.runtime+1)==env.runtime..'/' then env.run.fs.files[path]=nil end end
  for _,name in ipairs(env.names) do env.up[name]=false end
  pair.revive_log_reset();pair.handover_log_reset()
  env.backend.guarded=false;env.backend.guard_calls={}
  env.backend.kernel={};for i,x in ipairs(env.backend.uci) do env.backend.kernel[i]=x end
  env.run.mono_now=40  -- uptime when the supervisor starts
  env.slept={}
end

-- today's path (no variant D handover at this boot): the one-per-boot RAM marker is already there
local function today(env) env.run.fs.write_atomic(env.runtime..'/'..pair.HANDOVER_FILE,canon.encode(canon.object({state='refused'}))) end

-- the monitor's Start (control_request.start) on this router
local function start_deps(env)
  local fs=env.run.fs
  return {read=function(p) if p=='/proc/sys/kernel/random/uuid' then return ctl.uuid_hex() end;return fs.read(p) end,
    write=function(p,text) fs.write_atomic(p,text) end,exists=function(p) return fs.read(p)~=nil end,
    now=env.run.wall,clock=env.run.clock,runtime=env.runtime,persist=env.persist,
    try_lock=function(fn) return true,fn() end,
    native_policy=function() return canon.encode(env.backend.policy()) end,
    journal=function() return T.journal_read(env) end,auto_blocker=function() return nil end,
    preparation=function() return {checks={}} end,
    read_state=function() return pair.read_state(env) end,intent=function() return pair.intent(env) end}
end
local function resume_of(env)
  local deps=start_deps(env)
  return boot_resume.new({read=deps.read,exists=deps.exists,now=env.run.wall,runtime=env.runtime,persist=env.persist,
    write_ram=function(p,text) env.run.fs.write_atomic(p,text) end,FALLBACK=control.FALLBACK,
    uptime=function() return env.run.clock() end,
    intent=function() return pair.intent(env) end,
    revision=function() return ctl.revision_locked(env) end,
    start=function(arguments) return control.start(deps,arguments) end,
    fallback=function() error('no agent.py here',0) end})
end
local function status(env) return t.read(env,env.runtime..'/native-status.json') or canon.object({}) end

t.test('control: without the fix the held journal never settles and Start is refused forever',function()
  local log=durable.log;durable.log=function() end
  local env=router()
  cut(env)
  local ensure=pair.ensure_devices
  pair.ensure_devices=function() return nil end
  local boot=pair.boot_devices
  pair.boot_devices=function() return nil end
  local ok,err=pcall(function()
    t.eq(A.recover(env),'ready')
    local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
    for _=1,20 do A.iteration(env,ctx);env.run.advance(15) end
    t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE')
    t.eq(status(env).blockers,canon.array({'UNSAFE-GUARD-DEVICE'}))
    local reply=control.start(start_deps(env),canon.object({control_revision=ctl.revision_locked(env),request_source='programmatic'}))
    t.eq(reply.blockers,canon.array({'TRANSACTION-IN-PROGRESS'}))
  end)
  pair.ensure_devices=ensure;pair.boot_devices=boot;durable.log=log
  if not ok then error(err,0) end
end)

t.test('boot recovery starts the pair clients, the held journal settles at once, Start then succeeds',function()
  local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
  local env=router()
  cut(env)
  t.eq(A.recover(env),'ready')
  durable.log=log
  t.eq(env.net_log.ifup,{'ovpnclient1','wgclient1'},'the pair started its own two clients')
  local j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'ROLLED-BACK','PAIR-STOPPED'})
  t.eq(env.backend.uci,{'r1','r2'});t.eq(env.backend.kernel,{'r1','r2'})
  local state=pair.read_state(env)
  t.eq(state.phase,'STOPPED')
  -- owner decision 01.11.2026 (variant C): the boot resume will press Start, both clients are up: they stay up
  t.eq(#env.net_log.ifdown,0,'the healthy clients are kept for the boot resume Start')
  t.eq(state.kept,canon.array({'wgclient1','ovpnclient1'}));t.eq(state.kept_flags,canon.object({wgclient1='0',ovpnclient1='0'}))
  t.eq(env.backend.guarded,true,'the guard stays');t.eq(env.backend.guard_calls[#env.backend.guard_calls],'vpn-only')
  for _,call in ipairs(env.backend.guard_calls) do t.truthy(call=='vpn-only' or call=='full') end
  local text=table.concat(lines,'\n')
  t.truthy(string.find(text,'PAIR-RECOVERY-REVIVE: ifup wgclient1',1,true),'logged')
  t.truthy(string.find(text,'BOOT-RECOVERY-STEP: pair cleanup kept wgclient1 ovpnclient1',1,true),text)
  local r=resume_of(env)
  t.eq(r.tick(),'RESUMED')
  t.eq(pair.intent(env).mode,'on')
end)

------------------------------------------------------------------------------------------------------
-- Owner decision 01.11.2026 (variant C): healthy clients kept across the boot cleanup for the boot resume Start
------------------------------------------------------------------------------------------------------
local function quiet_log() local log=durable.log;durable.log=function() end;return function() durable.log=log end end

t.test('variant C: the next Start adopts the kept clients as owned (flags before the old session), no second ifup',function()
  local restore=quiet_log()
  local env=router()
  cut(env)
  t.eq(A.recover(env),'ready')
  local old=pair.read_state(env)
  local r=resume_of(env)
  t.eq(r.tick(),'RESUMED')
  local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  A.iteration(env,ctx)
  restore()
  local state=pair.read_state(env)
  t.truthy(state.id~=old.id,'a new session');t.eq(state.kept,nil)
  t.eq(state.owned,canon.array({'wgclient1','ovpnclient1'}),'still owned: a later Stop returns them')
  t.eq(state.before_flags,canon.object({wgclient1='0',ovpnclient1='0'}))
  t.eq(env.net_log.ifup,{'ovpnclient1','wgclient1'},'only the revive brought them up')
  t.eq(#env.net_log.ifdown,0)
  -- the owner's Stop of the new session returns them as before
  ctl.stop_latch(env,canon.null);pair.stop_locked(env,ctl.revision_locked(env))
  pair.cleanup(env,state)
  t.eq(env.net_log.ifdown,{'ovpnclient1','wgclient1'})
end)

t.test('variant C off: no owner marker, a newer Stop latch, or a client down - the old cleanup stops the clients',function()
  local restore=quiet_log()
  for _,case in ipairs({'no-marker','stop','down'}) do
    local env=router()
    cut(env)
    if case=='no-marker' then env.run.fs.files[env.persist..'/'..boot_resume.MARKER]=nil end
    if case=='stop' then ctl.stop_latch(env,canon.null) end
    if case=='down' then
      local up=env.net.client_down;env.net.client_down=function(name) if name=='ovpnclient1' then return true end;return up(name) end
    end
    t.eq(A.recover(env),'ready')
    local state=pair.read_state(env)
    t.eq(state.phase,'STOPPED',case);t.eq(state.kept,nil,case)
    t.eq(env.net_log.ifdown,{'ovpnclient1','wgclient1'},case)
    t.eq(env.backend.guarded,false,case)
  end
  restore()
end)

t.test('variant C: without the Start (expiry, Stop, failed boot resume) the kept clients are released as the old cleanup',function()
  local restore=quiet_log()
  for _,case in ipairs({'expiry','stop','failed'}) do
    local env=router()
    cut(env)
    t.eq(A.recover(env),'ready')
    t.eq(#pair.read_state(env).kept,2,case)
    local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
    A.iteration(env,ctx)
    t.eq(#env.net_log.ifdown,0,case..': kept while the Start is still coming')
    if case=='expiry' then env.run.advance(pair.KEEP_SECONDS) end
    if case=='stop' then env.run.advance(5);ctl.stop_latch(env,canon.null) end
    if case=='failed' then env.run.fs.write_atomic(env.runtime..'/'..boot_resume.STATE,canon.encode(canon.object({state='FAILED'}))) end
    A.iteration(env,ctx)
    local state=pair.read_state(env)
    t.eq(env.net_log.ifdown,{'ovpnclient1','wgclient1'},case);t.eq(state.kept,nil,case);t.eq(state.phase,'STOPPED',case)
    t.eq(env.backend.guarded,false,case..': guard removed with them')
  end
  restore()
end)

t.test('variant C: an unaccepted key refuses the Start, the kept clients go as after any failed resume',function()
  local restore=quiet_log()
  local env=router({flow='committed'})
  cut(env)
  env.backend.health=function(id) return env.up[({['wireguard:peer_1']='wgclient1',['openvpn:1_1']='ovpnclient1'})[id]] end
  env.backend.recovery_ready=function(id) return env.backend.health(id) end
  t.eq(A.recover(env),'ready')
  local old=pair.read_state(env)
  t.truthy(old.kept~=nil,'the fixture keeps the clients')
  env.backend.key_unaccepted=function() return 'SERVER-KEY-UNACCEPTED' end
  local r=resume_of(env);local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  t.eq(r.tick(),'RESUMED')
  A.iteration(env,ctx)
  local intent=pair.intent(env)
  t.eq({intent.mode,intent.failure_code},{'off','SERVER-KEY-UNACCEPTED'})
  t.eq(pair.read_state(env).id,old.id,'no new session');t.truthy(pair.read_state(env).kept~=nil);t.eq(#env.net_log.ifdown,0)
  env.run.fs.write_atomic(env.runtime..'/'..boot_resume.STATE,canon.encode(canon.object({state='FAILED'})))
  A.iteration(env,ctx)
  restore()
  t.eq(pair.read_state(env).kept,nil);t.eq(#env.net_log.ifdown,2,'stopped as the old cleanup would have')
end)

t.test('variant C: a key on the idle reserve does not stop the Start (owner 05.11.2026)',function()
  local restore=quiet_log()
  local env=router({flow='committed'})
  cut(env)
  env.backend.health=function(id) return env.up[({['wireguard:peer_1']='wgclient1',['openvpn:1_1']='ovpnclient1'})[id]] end
  env.backend.recovery_ready=function(id) return env.backend.health(id) end
  t.eq(A.recover(env),'ready')
  local old=pair.read_state(env)
  t.truthy(old.kept~=nil,'the fixture keeps the clients')
  env.backend.key_unaccepted=function(profiles) for _,x in ipairs(profiles) do if x=='openvpn:1_1' then return 'SERVER-KEY-UNACCEPTED' end end end
  local r=resume_of(env);local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  t.eq(r.tick(),'RESUMED')
  A.iteration(env,ctx)
  restore()
  t.eq(pair.intent(env).failure_code,nil);t.eq(pair.read_state(env).phase,'RUNNING');t.truthy(pair.read_state(env).id~=old.id)
end)

t.test('variant C: an owner Stop of a running session never keeps; the kept fields are validated',function()
  local restore=quiet_log()
  local env=router()
  local state=pair.read_state(env)
  env.run.mono_now=40
  local revision=ctl.revision_locked(env);pair.stop_locked(env,revision)
  t.eq(pair.cleanup(env,state,revision),true)
  t.eq(env.net_log.ifdown,{'ovpnclient1','wgclient1'})
  restore()
  t.eq(pair.read_state(env).kept,nil)
  local bad=pair.read_state(env);bad.phase='RUNNING';bad.kept=canon.array({'wgclient1'});bad.kept_flags=canon.object({wgclient1='0'});bad.kept_at=1
  pair.save(env,bad)
  t.code('PAIR-STATE-UNVERIFIED',pair.read_state,env)
  bad.phase='STOPPED';bad.kept_flags=canon.object({wgclient1='2'});pair.save(env,bad)
  t.code('PAIR-STATE-UNVERIFIED',pair.read_state,env)
  bad.kept_flags=canon.object({wgclient1='1'});pair.save(env,bad)
  t.eq(pair.read_state(env).kept_flags.wgclient1,'1')
end)

------------------------------------------------------------------------------------------------------
-- Owner decision 01.11.2026 (variant D): a completed switch on the reserve is handed over to the boot resume Start
------------------------------------------------------------------------------------------------------
-- the primary is not proven yet after the boot (no fresh probes), the reserve is healthy
local function reserve_only(env)
  local sel=env.backend.selection
  local primary={ok=false}
  env.backend.health=function(id) if id==sel.target.id then return env.up['ovpnclient1'] end;return primary.ok and env.up['wgclient1'] end
  env.backend.recovery_ready=function(id) return env.backend.health(id) end
  return primary
end
local function fresh_ctx() return {last_return=0,consumed=canon.object({}),last_attempt=0} end

t.test('variant D: the held reserve is handed over at once; Start adopts it (COMMITTED BOOT-RESERVE-ADOPTED); the return policy brings the primary back',function()
  local restore=quiet_log()
  local env=router()
  cut(env)
  local primary=reserve_only(env)
  t.eq(A.recover(env),'ready')
  local old=pair.read_state(env);local held=T.journal_read(env)
  t.eq(old.phase,'STOPPED');t.eq(old.handover.tx,held.tx);t.eq(old.handover.order,canon.array({'r1','r2'}))
  t.eq({held.phase,held.reason},{'HELD-ON-RESERVE','OPERATOR-MANUAL'},'the journal is untouched until the Start')
  t.eq(env.backend.uci,{'r2','r1'},'traffic stays on the reserve');t.eq(env.backend.guarded,true,'the guard stays')
  t.eq(#env.net_log.ifdown,0)
  local ctx=fresh_ctx()
  A.iteration(env,ctx)
  t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE','nothing else finishes the journal while the Start is coming')
  t.eq(resume_of(env).tick(),'RESUMED','Start accepted without the primary proof')
  A.iteration(env,ctx)
  restore()
  local j=T.journal_read(env);local state=pair.read_state(env)
  t.eq({j.phase,j.reason,j.tx},{'COMMITTED','BOOT-RESERVE-ADOPTED',held.tx})
  t.eq({j.boot_adopted.session,j.boot_adopted.from_phase,j.boot_adopted.from_reason},{state.id,'HELD-ON-RESERVE','OPERATOR-MANUAL'})
  t.eq(j.manual_request_id,nil,'automatic from here')
  t.eq(state.phase,'RUNNING');t.truthy(state.id~=old.id);t.eq(state.order,canon.array({'r1','r2'}),'the old session order')
  t.eq(state.owned,canon.array({'wgclient1','ovpnclient1'}));t.eq(state.handover,nil)
  t.eq(env.backend.uci,{'r2','r1'});t.eq(env.net_log.ifup,{'ovpnclient1','wgclient1'},'no second ifup')
  -- the normal committed return policy: the primary proven, min_dwell counted from the adoption
  primary.ok=true
  A.iteration(env,ctx)
  t.eq(T.journal_read(env).phase,'COMMITTED','min_dwell from the adoption')
  env.run.advance(61)
  A.iteration(env,ctx)
  j=T.journal_read(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(env.backend.uci,{'r1','r2'});t.eq(pair.read_state(env).phase,'RUNNING')
end)

-- 01.11.2026 (MT3000 beta3 cut: no handover, no reason): bounded retry on every cleanup pass, each refusal logged once
local function handover_lines(lines)
  local out={};for _,l in ipairs(lines) do local r=string.match(l,'^BOOT%-RECOVERY%-STEP: handover refused (.-) at ') if r then out[#out+1]=r end end;return out
end

t.test('variant D retry: the reserve not healthy yet at the first pass - refused once in the log, handed over on a later pass',function()
  local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
  local env=router()
  cut(env)
  reserve_only(env)
  local probe=env.backend.health
  local ready=false
  env.backend.health=function(id) if id==env.backend.selection.target.id and not ready then return nil end;return probe(id) end
  t.eq(A.recover(env),'ready')
  t.eq(pair.read_state(env).phase,'HELD');t.eq(pair.read_state(env).handover,nil)
  local ctx=fresh_ctx()
  for _=1,3 do env.run.advance(2);A.iteration(env,ctx) end
  t.eq(handover_lines(lines),{'RESERVE-HEALTH UNKNOWN'},'one line per reason, not per pass')
  ready=true
  env.run.advance(2);A.iteration(env,ctx)
  durable.log=log
  local state=pair.read_state(env)
  t.eq(state.phase,'STOPPED');t.truthy(state.handover~=nil,'handed over on a later pass')
  t.eq(t.read(env,env.runtime..'/'..pair.HANDOVER_FILE).state,'handed')
end)

t.test('variant D retry: the primary client still connecting does not block the handover; all owned clients are kept',function()
  local restore=quiet_log()
  local env=router()
  cut(env)
  reserve_only(env)
  local down=env.net.client_down
  env.net.client_down=function(name) if name=='wgclient1' then return true end;return down(name) end
  t.eq(A.recover(env),'ready')
  restore()
  local state=pair.read_state(env)
  t.truthy(state.handover~=nil);t.eq(state.kept,canon.array({'wgclient1','ovpnclient1'}))
end)

t.test('variant D retry is bounded: after HANDOVER_WAIT today\'s path goes on without further checks',function()
  local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
  local env=router()
  cut(env)
  reserve_only(env)
  local probe=env.backend.health
  local ready=false
  env.backend.health=function(id) if id==env.backend.selection.target.id and not ready then return false end;return probe(id) end
  t.eq(A.recover(env),'ready')
  local ctx=fresh_ctx()
  for _=1,8 do env.run.advance(10);A.iteration(env,ctx) end
  t.eq(t.read(env,env.runtime..'/'..pair.HANDOVER_FILE).state,'refused')
  ready=true
  env.run.advance(2);A.iteration(env,ctx)
  durable.log=log
  t.eq(pair.read_state(env).handover,nil,'no handover after the wait');t.eq(pair.read_state(env).phase,'HELD')
  t.eq(handover_lines(lines),{'RESERVE-HEALTH false','WAIT-OVER after RESERVE-HEALTH false'})
end)

t.test('variant D: every refusal names its reason (kernel, order, primary proven, no marker)',function()
  for _,case in ipairs({'kernel','primary','marker'}) do
    local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
    local env=router()
    cut(env)
    local primary=reserve_only(env)
    if case=='kernel' then env.backend.kernel={'r1','r2'} end
    if case=='primary' then primary.ok=true end
    if case=='marker' then env.run.fs.files[env.persist..'/'..boot_resume.MARKER]=nil end
    A.recover(env)
    durable.log=log
    local got=handover_lines(lines)[1] or ''
    local want=({kernel='KERNEL ',primary='PRIMARY-PROVEN',marker='AUTO-RESUME-NOT-REQUESTED'})[case]
    t.truthy(string.find(got,want,1,true)==1,case..': '..got)
  end
end)

t.test('variant D off: an unhealthy reserve, an unverified kernel, a proven primary, no marker - today\'s path',function()
  local restore=quiet_log()
  for _,case in ipairs({'reserve-down','kernel','primary-proven','no-marker'}) do
    local env=router()
    cut(env)
    local primary=reserve_only(env)
    if case=='reserve-down' then env.backend.health=function() return false end end
    if case=='kernel' then env.backend.kernel={'r1','r2'} end
    if case=='primary-proven' then primary.ok=true end
    if case=='no-marker' then env.run.fs.files[env.persist..'/'..boot_resume.MARKER]=nil end
    t.eq(A.recover(env),'ready')
    local state=pair.read_state(env)
    t.eq(state.handover,nil,case)
    if case=='primary-proven' then  -- returns at once, as today
      t.eq(T.journal_read(env).phase,'ROLLED-BACK',case)
    elseif case~='kernel' then
      t.eq(state.phase,'HELD',case);t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE',case)
    end
  end
  restore()
end)

t.test('variant D: a reserve that fails the fresh check at Start - the request fails, the old session is HELD, today\'s path',function()
  local restore=quiet_log()
  local env=router()
  cut(env)
  reserve_only(env)
  t.eq(A.recover(env),'ready')
  t.truthy(pair.read_state(env).handover~=nil)
  t.eq(resume_of(env).tick(),'RESUMED')
  env.backend.health=function() return false end  -- the reserve dropped before the new session began
  A.iteration(env,fresh_ctx())
  restore()
  local intent=pair.intent(env)
  t.eq({intent.mode,intent.failure_code},{'off','BOOT-RESERVE-UNVERIFIED'})
  local state=pair.read_state(env)
  t.eq(state.phase,'HELD');t.eq(state.handover,nil);t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE','not adopted')
end)

-- Review 05.11.2026: the resume's Start meets the same refusal as the owner's: no exception for a power cut. Python: test_boot_held.py.
local function run_resume(env)
  local r=resume_of(env);local ctx=fresh_ctx();local final
  for _=1,20 do
    final=r.tick()
    if final=='FAILED' then break end
    A.iteration(env,ctx)
    env.run.advance(boot_resume.EVERY)
  end
  return final
end

t.test('a key on the idle primary: the boot resume adopts the reserve, no return onto the primary until the owner\'s word',function()
  local restore=quiet_log()
  local env=router()
  cut(env)
  local primary=reserve_only(env)
  t.eq(A.recover(env),'ready')
  local held=T.journal_read(env)
  local bad={['wireguard:peer_1']=true}
  env.backend.key_unaccepted=function(profiles) for _,x in ipairs(profiles) do if bad[x] then return 'SERVER-KEY-UNACCEPTED' end end end
  local ctx=fresh_ctx()
  t.eq(resume_of(env).tick(),'RESUMED')
  A.iteration(env,ctx)
  local j=T.journal_read(env);local state=pair.read_state(env)
  t.eq({j.phase,j.reason,j.tx},{'COMMITTED','BOOT-RESERVE-ADOPTED',held.tx});t.eq(state.phase,'RUNNING')
  t.truthy(state.selected_policy~=nil,'the route is proved: no BLOCKED first pass');t.eq(env.backend.uci,{'r2','r1'})
  primary.ok=true
  env.run.advance(61)
  A.iteration(env,ctx)
  t.eq(T.journal_read(env).phase,'COMMITTED','a healthy primary with its key unaccepted: no return');t.eq(env.backend.uci,{'r2','r1'})
  bad['wireguard:peer_1']=nil
  env.run.advance(61)
  A.iteration(env,ctx)
  restore()
  t.eq(T.journal_read(env).phase,'ROLLED-BACK','his word lets the return go');t.eq(env.backend.uci,{'r1','r2'})
end)

t.test('a key on the reserve that carries: the boot resume starts nothing, the code is visible, the handover ends on today\'s path',function()
  local restore=quiet_log()
  for _,id in ipairs({'openvpn:1_1'}) do
    local env=router()
    cut(env)
    reserve_only(env)
    t.eq(A.recover(env),'ready')
    local held=T.journal_read(env)
    t.truthy(pair.read_state(env).handover~=nil)
    local ups=#env.net_log.ifup;local guards=#env.backend.guard_calls
    env.backend.key_unaccepted=function(profiles) for _,x in ipairs(profiles) do if x==id then return 'SERVER-KEY-UNACCEPTED' end end end
    t.eq(run_resume(env),'FAILED',id)
    local row=canon.decode(env.run.fs.read(env.runtime..'/'..boot_resume.STATE))
    t.eq({row.state,row.code},{'FAILED','SERVER-KEY-UNACCEPTED'})
    local intent=pair.intent(env)
    t.eq({intent.mode,intent.failure_code},{'off','SERVER-KEY-UNACCEPTED'})
    t.eq({T.journal_read(env).phase,T.journal_read(env).tx},{'HELD-ON-RESERVE',held.tx},'not adopted')
    t.eq(env.backend.uci,{'r2','r1'},'the traffic stays');t.eq(env.backend.guarded,true,'the guard stays')
    t.eq(#env.net_log.ifup,ups,'no client started');t.eq(#env.backend.guard_calls,guards,'no guard written')
    A.iteration(env,fresh_ctx())
    local state=pair.read_state(env)
    t.eq(state.handover,nil);t.eq(state.phase,'HELD','the failed resume releases it, as every failed resume')
  end
  restore()
end)

t.test('variant D: an owner Stop, a failed boot resume or no Start within KEEP_SECONDS release the handover',function()
  local restore=quiet_log()
  for _,case in ipairs({'stop','failed','expiry'}) do
    local env=router()
    cut(env)
    reserve_only(env)
    t.eq(A.recover(env),'ready')
    local ctx=fresh_ctx()
    if case=='stop' then env.run.advance(5);ctl.stop_latch(env,canon.null) end
    if case=='failed' then env.run.fs.write_atomic(env.runtime..'/'..boot_resume.STATE,canon.encode(canon.object({state='FAILED'}))) end
    if case=='expiry' then env.run.advance(pair.KEEP_SECONDS) end
    A.iteration(env,ctx)
    local state=pair.read_state(env)
    t.eq(state.handover,nil,case)
    A.iteration(env,ctx)
    t.eq(pair.read_state(env).phase,'HELD',case..': the old cleanup waits for the primary proof again')
    t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE',case)
    t.eq(control.start(start_deps(env),canon.object({control_revision=ctl.revision_locked(env),request_source='programmatic'})).blockers[1],'TRANSACTION-IN-PROGRESS',case)
  end
  restore()
end)

t.test('variant D: an interrupted switch still rolls back; Start accepts only the handed-over journal',function()
  local restore=quiet_log()
  local env=router()
  local j=T.journal_read(env);j.phase='WAIT-CLIENT';T.journal_write(env,j)
  cut(env)
  reserve_only(env)
  A.recover(env)
  t.eq(T.journal_read(env).phase,'ROLLED-BACK');t.eq(pair.read_state(env).handover,nil)
  local env2=router()
  cut(env2)
  reserve_only(env2)
  A.recover(env2)
  local deps=start_deps(env2)
  t.eq(control.handover_matches(deps,T.journal_read(env2)),true)
  local other=T.journal_read(env2);other.tx=string.rep('9',32)
  t.eq(control.handover_matches(deps,other),false)
  restore()
end)

t.test('settles by itself ~80 s later through the supervisor passes; boot resume waits and survives an NTP step',function()
  local log=durable.log;durable.log=function() end
  local env=router({settle=80})
  cut(env)
  today(env)
  t.eq(A.recover(env),'ready')
  t.eq(env.net_log.ifup,{'ovpnclient1','wgclient1'})
  -- the primary is not verified yet: held (the guard on the started devices), not a dead end
  t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE');t.eq(pair.read_state(env).phase,'HELD')
  t.eq(env.backend.guard_calls[#env.backend.guard_calls],'vpn-only')
  local r=resume_of(env)
  local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  local states={}
  local settled_at=nil
  for step=1,40 do
    A.iteration(env,ctx)
    if not settled_at and T.journal_read(env).phase=='ROLLED-BACK' then settled_at=env.run.clock() end
    local s=r.tick()
    states[#states+1]=s
    if s=='RESUMED' then break end
    env.run.advance(5)
    if step==3 then env.run.wall_now=env.run.wall_now+4*3600 end  -- chrony: "time sync success" right after the boot
  end
  durable.log=log
  t.eq(states[1],'WAITING')
  t.eq(states[#states],'RESUMED','the boot resume Start succeeded: '..table.concat(states,','))
  t.truthy(settled_at and settled_at-40<=180,'settled within the supervisor passes')
  t.eq(t.read(env,env.runtime..'/boot-resume.json').state,'RESUMED')
  t.eq(pair.intent(env).mode,'on')
  t.eq(env.net_log.ifup,{'ovpnclient1','wgclient1'},'no extra ifup: the clients stayed up until the cleanup')
end)

t.test('a changed profile definition (wireguard/ovpnclient config): the clients are not touched, the skip is logged',function()
  local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
  local env=router({protected=canon.object({wireguard='a',ovpnclient='b'}),live=canon.object({wireguard='a',ovpnclient='b'})})
  cut(env)
  env.live.wireguard='changed'
  t.eq(A.recover(env),'ready')
  durable.log=log
  t.eq(#env.net_log.ifup,0,'no ifup')
  t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE')
  t.eq(status(env).state,'BLOCKED')
  t.truthy(string.find(table.concat(lines,'\n'),'PAIR-RECOVERY-REVIVE-SKIPPED: PAIR-EXTERNAL-CONFIG-CHANGE',1,true),'logged')
end)

t.test('a disabled or foreign-protocol row is never started; a client that is not stopped is not restarted',function()
  local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
  local env=router()
  cut(env)
  env.rows[1].disabled='1';env.rows[2].proto='static'
  t.eq(A.recover(env),'ready')
  durable.log=log
  t.eq(#env.net_log.ifup,0)
  local text=table.concat(lines,'\n')
  t.truthy(string.find(text,'PAIR-PROFILES-UNVERIFIED wgclient1',1,true) and string.find(text,'PAIR-PROFILES-UNVERIFIED ovpnclient1',1,true),text)
end)

t.test('alpha14 power cut: COMMITTED journal, pair HELD with owned [], both clients down, no revive ledger, vendor-rewritten wireless',function()
  local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
  local live=canon.object({wireguard='w1',ovpnclient='o1',wireless='before',dhcp='d',['gl-dns-v2']='g'})
  local env=router({flow='committed',wg='wgclient1',ovpn='ovpnclient2',owned={},protected=canon.decode(canon.encode(live)),live=live})
  -- the state the router found after the boot (evidence-alpha14-powercut-committed.json)
  local state=pair.read_state(env);state.phase='HELD';state.recovery_error='UNSAFE-GUARD-DEVICE';pair.save(env,state)
  cut(env)
  env.live.wireless='rewritten-by-the-repeater-at-boot'
  env.net.identity=function() return string.rep('bb',32) end  -- the whole network config differs (vendor wwan edit)
  t.eq(env.run.fs.read(env.persist..'/pair-revive.json'),nil);t.eq(env.run.fs.read(env.runtime..'/pair-revive.json'),nil)
  t.eq(A.recover(env),'ready')
  durable.log=log
  local text=table.concat(lines,'\n')
  t.eq(env.net_log.ifup,{'ovpnclient2','wgclient1'},'the pair\'s two configured clients, not only owned ones: '..text)
  t.truthy(string.find(text,'PAIR-RECOVERY-REVIVE: ifup ovpnclient2',1,true))
  t.truthy(not string.find(text,'GUARD-DEVICE-UNAVAILABLE',1,true),'the COMMITTED guard found its devices')
  local j=T.journal_read(env)
  t.eq({j.phase,j.reason},{'ROLLED-BACK','PAIR-STOPPED'})
  t.eq(env.backend.uci,{'r1','r2'});t.eq(env.backend.kernel,{'r1','r2'})
  t.eq(pair.read_state(env).phase,'STOPPED')
  t.eq(#env.net_log.ifdown,0,'clients the session did not own stay up, as before the session')
  t.eq(env.backend.guarded,false,'no guard left')
  local r=resume_of(env)
  t.eq(r.tick(),'RESUMED');t.eq(pair.intent(env).mode,'on')
end)

t.test('alpha14 state, control: the old owned-only/identity-gated revive leaves the journal COMMITTED and Start refused',function()
  local log=durable.log;durable.log=function() end
  local env=router({flow='committed',wg='wgclient1',ovpn='ovpnclient2',owned={}})
  local state=pair.read_state(env);state.phase='HELD';pair.save(env,state)
  cut(env)
  local ensure,boot=pair.ensure_devices,pair.boot_devices
  pair.ensure_devices=function() return nil end;pair.boot_devices=function() return nil end
  local ok,err=pcall(function()
    t.eq(A.recover(env),'ready')
    local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
    for _=1,10 do A.iteration(env,ctx);env.run.advance(15) end
    t.eq(T.journal_read(env).phase,'COMMITTED')
    t.eq(status(env).blockers,canon.array({'UNSAFE-GUARD-DEVICE'}))
    t.eq(control.start(start_deps(env),canon.object({control_revision=ctl.revision_locked(env),request_source='programmatic'})).blockers,canon.array({'TRANSACTION-IN-PROGRESS'}))
  end)
  pair.ensure_devices,pair.boot_devices=ensure,boot;durable.log=log
  if not ok then error(err,0) end
end)

t.test('the revive is bounded: an ifup that never brings a device waits DEVICE_WAIT, then the pause applies',function()
  local log=durable.log;durable.log=function() end
  local env=router()
  cut(env)
  env.net.ifup=function(name) env.net_log.ifup[#env.net_log.ifup+1]=name end  -- the client never comes up
  local t0=env.run.clock()
  t.eq(A.recover(env),'ready')
  t.truthy(env.run.clock()-t0<=pair.DEVICE_WAIT+A.BOOT_DEVICE_WAIT+10,'bounded')
  t.eq(#env.net_log.ifup,2,'one attempt per client inside REVIVE_PAUSE')
  t.eq(env.backend.guarded,false,'the LAN is never blocked while waiting')
  t.eq(T.journal_read(env).phase,'HELD-ON-RESERVE')
  local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  for _=1,10 do A.iteration(env,ctx);env.run.advance(15) end
  t.truthy(#env.net_log.ifup<=2*pair.REVIVE_LIMIT,'bounded by the revive budget ('..#env.net_log.ifup..')')
  durable.log=log
end)

t.test('owner decision extension: supervisor killed in idle (procd restart, no reboot) resumes; after a Stop it stays off',function()
  local log=durable.log;durable.log=function() end
  local env=router()
  cut(env)
  t.eq(A.recover(env),'ready')
  local first=t.read(env,env.runtime..'/supervisor-start.json').id
  t.truthy(type(first)=='string' and #first==32,'the supervisor start token')
  local r=resume_of(env)
  t.eq(r.tick(),'RESUMED');t.eq(pair.intent(env).mode,'on')
  -- kill -9 in idle: procd restarts the supervisor, its recovery fences (revokes) the intent
  env.run.advance(600)
  t.eq(A.recover(env),'ready')
  t.eq(pair.intent(env).mode,'off','the restarted supervisor never resumes by itself')
  t.truthy(t.read(env,env.runtime..'/supervisor-start.json').id~=first,'a fresh token')
  t.eq(r.tick(),'RESUMED');t.eq(pair.intent(env).mode,'on','the monitor resumed the owner Auto')
  t.eq(t.read(env,env.runtime..'/boot-resume.json').trigger,'supervisor-restart')
  -- the owner presses Stop, then the supervisor is killed again: Auto stays off
  env.run.advance(60)
  ctl.stop_latch(env,canon.null)
  t.eq(A.recover(env),'ready')
  t.eq(r.tick(),'SKIPPED');t.eq(t.read(env,env.runtime..'/boot-resume.json').code,'AUTO-RESUME-STOPPED')
  t.eq(pair.intent(env).mode,'off')
  durable.log=log
end)

t.run()
