-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- Trace-conformance driver, Lua line (tools/formal/trace_check.py, 04.11.2026). Offline, no router.
-- The twin of tests/trace_driver.py: the real Lua supervisor (auto.recover / auto.iteration, pair, transaction,
-- rollback, forward_resume, control_request, boot_resume) on the fake router of auto_harness.lua (UCI order and kernel
-- order kept apart), the same scenario events and the same abstract state read back after every event.
-- Usage: lua5.1 trace_driver.lua scenarios.json traces.json   (run from tests/lua)
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local A=require('auto')
local ctl=require('auto_control')
local pair=require('pair')
local control=require('control_request')
local boot_resume=require('boot_resume')
local durable=require('durable')
local R=require('rollback')
local CM=require('channel_model')
durable.log=function() end

local PHASES={ARMED='ARMED',APPLYING='APPLYING',['WAIT-CLIENT']='WAIT',COMMITTED='COMMITTED',['HELD-ON-RESERVE']='HOR',
  RESTORING='RESTORING',['ROLLED-BACK']='RB',['RELEASE-PENDING']='RP'}
local READOPT=pair.READOPT_CODES
local KILLED=setmetatable({code='DRIVER-KILLED'},{__tostring=function() return 'DRIVER-KILLED' end})
local WG,OVPN='wgclient1','ovpnclient1'

local function copy(list) local o={};for i,x in ipairs(list) do o[i]=x end;return canon.array(o) end

local function scenario_run(events)
  local env=t.env()
  local B=env.backend
  local run=env.run
  local fs=run.fs
  run.mono_now=5000
  B.settings.native_enabled='0'   -- as the Python fixture: pair mode, no legacy trial
  local D={trace={},snaps={},writes=0,kill_at=nil,in_pass=false,dead=false,fault=0,fault_fired=false,gave_up=false,
    current='boot',mid=nil,monitor=nil}
  local up={[WG]=true,[OVPN]=true}
  local health={}
  local src,tgt=B.selection.source.id,B.selection.target.id
  health[src]=true;health[tgt]=true
  env.up,env.names=up,{WG,OVPN}
  env.identity=string.rep('aa',32)
  env.prep=false
  local base_hash=B.hash
  local base_order=copy(B.uci)
  local IFACE={[src]=WG,[tgt]=OVPN}

  local function alive() if D.dead then error(KILLED,0) end end
  local observe
  local function wrote()
    D.writes=D.writes+1
    D.snaps[#D.snaps+1]=observe()
    if D.kill_at~=nil and D.in_pass and D.writes>=D.kill_at then D.kill_at=nil;D.dead=true;error(KILLED,0) end
  end
  -- the file writes that are crash points (the same five records as the Python driver), every write frozen after a kill
  local counted={[env.persist..'/native-transaction.json']=true,[env.persist..'/pair-auto-state.json']=true,
    [env.runtime..'/pair-auto-control.json']=true,[env.persist..'/native-stop.json']=true,[env.persist..'/'..boot_resume.MARKER]=true}
  local write_atomic=fs.write_atomic
  fs.write_atomic=function(path,text) alive();write_atomic(path,text);if counted[path] then wrote() end end
  local remove=fs.remove
  fs.remove=function(path) alive();remove(path) end

  -- fake router: tunnel health, devices, guard mode, the live selection, the preflight
  function B.health(id) return health[id]==true end
  B.recovery_ready=function(id) return B.health(id) end
  B.probe=function(profile) if B.health(profile.id) then return canon.object({code=canon.null,dns_ok=true,https_success=2}) end;return canon.object({code='VPN-001'}) end
  B.devices=function() local out={};for _,name in ipairs({OVPN,WG}) do if up[name] then out[#out+1]=name end end;return out end
  local function live() local s=canon.decode(canon.encode(B.selection));s.order=copy(B.uci);s.hash=B.hash;return s end
  B.diagnostic=function() if D.reserve_lost then return {'RESERVE-NOT-CONNECTED'},live() end;return {},live() end
  B.pair_preflight=function(settings)
    if env.prep then error(setmetatable({code='PREP-TARGET-AUTOSTART',value_error=true},ctl.Refused),0) end
    if table.concat(B.kernel,',')~=table.concat(B.uci,',') then error(setmetatable({code='KERNEL-POLICY-UNVERIFIED',value_error=true},ctl.Refused),0) end
    return live()
  end
  B.mode=nil
  local guard,unguard,reorder,apply=B.guard,B.unguard,B.reorder,B.apply
  B.guard=function(devices,revision)
    alive()
    if devices~=nil and #devices==0 then error(setmetatable({code='UNSAFE-GUARD-DEVICE'},ctl.Refused),0) end
    guard(devices,revision);B.mode=devices and 'vpn' or 'full';wrote()
  end
  B.unguard=function() alive();unguard();B.mode=nil;wrote() end
  B.guard_exists=function() return B.mode~=nil end
  B.reorder=function(...) alive();reorder(...);wrote() end
  B.apply=function(write_command)
    alive()
    if D.fault>0 then D.fault=D.fault-1;D.fault_fired=true;error(setmetatable({code='NATIVE-SYSTEM-001'},ctl.Refused),0) end
    apply(write_command);wrote()
  end
  -- the router-probed decision inputs follow the abstract tunnel health (no monitor samples are simulated)
  CM.channel_failed=function(samples,id) return not B.health(id) end
  CM.return_ready=function(samples,id) return B.health(id) end
  pair.streak=function(samples,id,count,now,age,good) return B.health(id)==(good==true) end
  pair.source_unstable=function() return false end
  env.deps.diagnose=function() return {suppress_switch=false} end
  env.net={network=function() return canon.array({canon.object({['.name']=WG,proto='wgclient',auto='0',disabled='0'}),
      canon.object({['.name']=OVPN,proto='ovpnclient',auto='0',disabled='0'})}) end,
    identity=function() return env.identity end,configs=function() return canon.object({}) end,
    changed=function() return false end,
    client_down=function(name) return not up[name] end,
    ifup=function(name,revision) run.require_revision(revision);up[name]=true end,
    ifdown=function(name) up[name]=false end,
    quiet=function() end,set_disabled=function() end,interface_exists=function(name) return up[name] end}
  local give_up=R.give_up
  R.give_up=function(...) D.gave_up=true;env.stopped=true;return give_up(...) end

  -- control_request FALLBACK: agent.py runs the Python release_for_start and auto_prepare first. No agent.py here: the same
  -- two steps on the Lua twins (release_session under the readopt ledger; the prep flag as in the Python driver), the
  -- request itself is then Lua's again. Such a step is marked 'fallback' in the trace.
  local function agent_start()
    local sok,state=pcall(pair.read_state,env)
    local iok,row=pcall(pair.intent,env)
    if not (sok and iok) then return end
    if state.phase=='HELD' and READOPT[state.recovery_error] and row.mode~='on' then
      pcall(pair.release_session,env,state,state.recovery_error);state=pair.read_state(env)
    end
    if env.prep and row.mode~='on' and (state.phase==nil or pair.TERMINAL[state.phase]) then env.prep=false end
  end
  -- the owner's buttons (control_request) and the monitor (boot_resume) on the same files
  local function deps()
    return {read=function(p) if p=='/proc/sys/kernel/random/uuid' then return ctl.uuid_hex() end;return fs.read(p) end,
      write=function(p,text) fs.write_atomic(p,text) end,exists=function(p) return fs.read(p)~=nil end,
      now=run.wall,clock=run.clock,runtime=env.runtime,persist=env.persist,
      try_lock=function(fn) return true,fn() end,
      native_policy=function() return canon.encode(B.policy()) end,
      journal=function() return T.journal_read(env) end,auto_blocker=function() return nil end,
      preparation=function() if env.prep then return {checks={{code='PREP-TARGET-AUTOSTART',state='fail'}}} end;return {checks={}} end,
      read_state=function() return pair.read_state(env) end,intent=function() return pair.intent(env) end,
      terminalize=function() return require('manual').terminalize_pending_locked(env,'CANCELLED','CONTROL-REVISION-STALE') end,
      nft=function() return 1,'' end}
  end
  local function new_monitor()
    local d=deps()
    return boot_resume.new({read=d.read,exists=d.exists,now=run.wall,runtime=env.runtime,persist=env.persist,
      write_ram=function(p,text) fs.write_atomic(p,text) end,FALLBACK=control.FALLBACK,
      uptime=function() return run.clock() end,intent=function() return pair.intent(env) end,
      revision=function() return ctl.revision_locked(env) end,
      start=function(arguments) return control.start(d,arguments) end,
      fallback=function(arguments)
        D.fell_back=true;agent_start()
        local again=control.start(d,arguments)
        if again==control.FALLBACK then error('still FALLBACK',0) end
      end})
  end

  -- the abstract state
  -- P is the order the session started on (a Start after an outside change adopts whatever order it finds), as in the model
  local function role(order,hash,expected,primary)
    if hash~=expected then return 'F' end
    if table.concat(order,',')==table.concat(primary,',') then return 'P' end
    local a,b=copy(order),copy(primary);table.sort(a);table.sort(b)
    return table.concat(a,',')==table.concat(b,',') and 'R' or 'F'
  end
  observe=function()
    local iok,row=pcall(pair.intent,env);if not iok or type(row)~='table' then row={mode='BAD'} end
    local sok,state=pcall(pair.read_state,env);if not sok or type(state)~='table' then state={phase='BAD'} end
    local jok,j=pcall(T.journal_read,env);if not jok or type(j)~='table' then j={phase='BAD'} end
    local rtext=fs.read(env.runtime..'/auto-control-revision.json')
    local rok,rrow=pcall(canon.decode,rtext or '')
    local revision=rok and type(rrow)=='table' and rrow.revision or nil
    local on=row.mode=='on' and revision~=nil and row.revision==revision
    local marker=boot_resume.wanted(fs.read,env.persist)==true
    local readopt=0
    local ltext=fs.read(env.runtime..'/pair-readopt.json')
    local lok,ledger=pcall(canon.decode,ltext or '')
    if lok and type(ledger)=='table' and type(ledger.events)=='table' then
      for _,x in ipairs(ledger.events) do local v=canon.number(x);if v and run.wall()-v>=0 and run.wall()-v<900 then readopt=readopt+1 end end
    end
    local expected=type(state.policy_hash)=='string' and state.policy_hash or base_hash
    local primary=type(state.order)=='table' and state.order or base_order
    local phase=j.phase
    local jr='NONE'
    if phase~=nil and phase~=canon.null then jr=PHASES[phase] or ('BAD:'..tostring(phase)) end
    local fails=canon.number(j.rollback_failures) or 0
    local function has(v) return v~=nil and v~=canon.null end
    return canon.object({intent=on and 'on' or 'off',fresh=on and state.id~=row.id or false,marker=marker,
      sess=type(state.phase)=='string' and state.phase or 'NONE',
      readopt_code=state.phase=='HELD' and READOPT[state.recovery_error]==true or false,
      ran=state.ran==true,ho=has(state.handover),kept=has(state.kept),jr=jr,rtp=j.rtp_dispatched==true,
      fails=math.min(2,fails),fres=has(j.forward_resumed),failed=has(j.failure_code),
      uci=role(B.uci,B.hash,expected,primary),kern=role(B.kernel,B.hash,expected,primary),guard=B.mode or 'none',
      pUp=B.health(src),rUp=B.health(tgt),readopt=math.min(3,readopt),
      sc=has(state.server_change) and tostring(state.server_change.phase) or '-'})
  end
  local function record(event,end_,extra)
    local row=canon.object({event=event,['end']=end_,obs=observe(),writes=canon.array(D.snaps),n_writes=D.writes,t=canon.float(run.wall())})
    if D.fault_fired then row.fault=true end
    for k,v in pairs(extra or {}) do row[k]=v end
    D.trace[#D.trace+1]=row
    D.snaps={};D.writes=0;D.fault_fired=false
  end

  -- RAM loss
  local function lose_process()
    D.dead=false;env.stopped=false
    pcall(pair.revive_log_reset);pcall(pair.handover_log_reset);if pair.outside_guard_reset then pair.outside_guard_reset() end
    for k in pairs(pair.late_aborts) do pair.late_aborts[k]=nil end
  end
  local function power_cut()
    for path in pairs(fs.files) do if string.sub(path,1,#env.runtime+1)==env.runtime..'/' then fs.files[path]=nil end end
    for name in pairs(up) do up[name]=false end
    B.mode=nil;B.guarded=false
    B.kernel=copy(B.uci)
    run.wall_now=run.wall_now+60;run.mono_now=40
    D.monitor=nil
  end

  -- events between the passes
  local function apply_event(kind)
    if kind=='start' or kind=='stop' then run.advance(1) end
    if kind=='start' then
      local ok,reply=pcall(control.start,deps(),canon.object({control_revision=ctl.revision_locked(env),request_source='manual'}))
      if not ok then return {reply='error '..tostring(type(reply)=='table' and reply.code or reply)} end
      if reply==control.FALLBACK then
        agent_start()
        local rok,again=pcall(control.start,deps(),canon.object({control_revision=ctl.revision_locked(env),request_source='manual'}))
        if rok and again~=control.FALLBACK then
          return {reply=(again.blockers and again.blockers[1]) or (again.accepted and 'accepted') or '?',fallback=true}
        end
        return {reply='FALLBACK',fallback=true}
      end
      return {reply=(reply.blockers and reply.blockers[1]) or (reply.accepted and 'accepted') or '?'}
    elseif kind=='stop' then
      local ok,reply=pcall(control.stop,deps(),canon.object({request_source='manual'}))
      if not ok then return {reply='error'} end
      if reply==control.FALLBACK then return {reply='FALLBACK'} end
      return {reply=reply.already_requested and 'already_requested' or (reply.queued and 'queued' or tostring(reply.code))}
    elseif kind=='resume' then
      if D.monitor==nil then
        -- the monitor runs from the boot on; first reached after the boot window it only serves supervisor restarts
        D.monitor=new_monitor()
        if run.clock()>=boot_resume.BOOT_AGE then D.monitor.done=true end
      end
      local m=D.monitor
      D.fell_back=false
      local state
      for _=1,400 do
        local ok,s=pcall(m.tick)
        state=ok and s or ('error '..tostring(s))
        if m.done and m.watch_until==nil then break end
        run.advance(5)
      end
      return {reply=tostring(state),fallback=D.fell_back or nil}  -- a nil state: nothing to resume for this monitor
    elseif kind=='p_down' or kind=='p_up' then health[src]=(kind=='p_up')
    elseif kind=='r_down' or kind=='r_up' or kind=='r_lost' then
      health[tgt]=(kind=='r_up');D.reserve_lost=kind=='r_lost' or (D.reserve_lost and kind=='r_down')
    elseif kind=='gl_pol' then B.hash=run.sha256(B.hash..'gl');env.prep=true
    elseif kind=='gl_net' then env.identity=run.sha256(env.identity..'gl');env.prep=true
    elseif kind=='busy' then D.fault=1
    elseif kind=='wait' then run.advance(60)
    elseif kind=='wait_long' then run.advance(700)
    else error('unknown event '..tostring(kind)) end
    return {}
  end

  lose_process()   -- module-level state of a previous scenario (outside guard, late aborts) never leaks in
  local queue={};for i,e in ipairs(events) do queue[i]=e end
  local qi=0
  local function pop() qi=qi+1;return queue[qi] end

  -- one supervisor process: recovery, then loop passes; -> 'killed' | 'down', err | 'giveup' | 'end'
  local function supervisor()
    local ok,res=pcall(A.recover,env)
    if D.dead then return 'killed' end
    if not ok then return 'down',tostring(type(res)=='table' and res.code or res) end
    if res=='stopped' then return D.gave_up and 'giveup' or 'down' end
    if D.current=='boot' then D.monitor=new_monitor();pcall(D.monitor.tick) end   -- an old boot: watches restarts only
    record(D.current,'IDLE')
    local ctx={last_return=0,consumed=canon.object({}),last_trial=nil,last_attempt=0}
    while true do
      while true do
        local ev=pop()
        if ev==nil then return 'end' end
        local kind,at=string.match(ev,'^([%w_]+)@?(%d*)$')
        if kind=='tick' then D.current='tick';break end
        if kind=='crash' or kind=='power' then
          D.current=kind
          if at~='' then D.kill_at=tonumber(at);D.mid=kind;break end
          return 'killed'
        end
        local extra=apply_event(kind)
        record(kind,'IDLE',extra)
      end
      D.in_pass=true
      local pok,pause=pcall(A.iteration,env,ctx)
      D.in_pass=false
      if D.dead then return 'killed' end
      if D.kill_at~=nil then D.kill_at=nil;D.current='tick';D.mid=nil end
      if not pok then return 'down',tostring(type(pause)=='table' and pause.code or pause) end
      if pause=='exit' then return 'down' end
      env.sleep(pause=='nap' and 2 or (tonumber(pause) or 2))  -- before the record, as the Python loop: one clock for both drivers
      record(D.current,'IDLE')
    end
  end

  while true do
    local why,err=supervisor()
    if why=='end' then break end
    if why=='killed' then
      local kind=D.current=='power' and 'power' or 'crash'
      D.kill_at=nil;D.dead=false
      if kind=='power' then power_cut() end
      lose_process()
      record(kind,'DOWN',{mid=D.mid~=nil})
      D.mid=nil;D.current='recover'
    elseif why=='giveup' then
      record(D.current,'GIVEUP');break
    else
      record(D.current,'DOWN',err and {error=err} or nil)
      lose_process();D.current='recover'
    end
  end
  return D.trace
end

local function main()
  local f=assert(io.open(arg[1],'rb'));local text=f:read('*a');f:close()
  local scenarios=canon.decode(text)
  local out={}
  local errors,steps=0,0
  for _,sc in ipairs(scenarios) do
    local started=os.clock()
    local ok,trace=xpcall(function() return scenario_run(sc.events) end,function(e) return debug.traceback(tostring(type(e)=='table' and (e.code or canon.encode(e)) or e),2) end)
    local row=canon.object({name=sc.name,runtime='lua',seconds=canon.float(os.clock()-started+0.0001)})
    if ok then row.steps=canon.array(trace);steps=steps+#trace
    else row.steps=canon.array({});row.driver_error=string.sub(trace,-3000);errors=errors+1 end
    out[#out+1]=row
  end
  local g=assert(io.open(arg[2],'wb'));g:write(canon.encode(canon.array(out)));g:close()
  print(string.format('TRACE-DRIVER lua: %d scenarios, %d steps, %d driver errors',#out,steps,errors))
end
main()
