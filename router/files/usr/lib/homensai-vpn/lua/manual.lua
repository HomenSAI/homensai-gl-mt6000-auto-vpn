-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- manual.lua: pair_manual.py (supervisor side) + manual_dispatch.py confirmations for the Lua supervisor.
--
-- pair-manual-control.json keeps the Python record and states QUEUED/CLAIMED/COMPLETED/REFUSED/CANCELLED/
-- UNCONFIRMED. consume(): claim under the control lock, light checks, then either the instant path
-- (instant_switch.lua: the APPLYING journal built like native_switch.instant_manual, one fenced UCI session,
-- one atomic iptables-restore, HELD-ON-RESERVE) or the full guarded transaction.attempt(); the owner click is
-- never rate limited on the instant path (owner decision, 30 Oct 2026). held_reserve() watches a manual hold.
-- The UI side (request/controls/public) stays in the monitor; light_gate() is here for it to call later.
local canon=require('canon')
local ctl=require('auto_control')
local T=require('transaction')
local pair=require('pair')
local instant=require('instant_switch')

local M={}
local NULL=canon.null
local isnone,num,finite=ctl.isnone,ctl.num,ctl.finite
local refuse,is_refused=ctl.refuse,ctl.is_refused
local same_list,copy_list,order_is,getd,merge=T.same_list,T.copy_list,T.order_is,T.getd,T.merge
local P=pair.policy
M.PENDING={QUEUED=true,CLAIMED=true}
M.STATES={QUEUED=true,CLAIMED=true,COMPLETED=true,REFUSED=true,CANCELLED=true,UNCONFIRMED=true}
local function fwall(env) return canon.float(env.run.wall()) end
local function value_error(code) error(setmetatable({code=code,value_error=true},ctl.Refused),0) end
function M.path(env) return env.runtime..'/pair-manual-control.json' end

local BASE={id=true,pair=true,revision=true,direction=true,state=true,requested=true,updated=true,selection=true,code=true}
function M.valid(row)
  if not canon.is_object(row) then return false end
  for k in pairs(row) do if not BASE[k] and k~='request_source' then return false end end
  for k in pairs(BASE) do if row[k]==nil then return false end end
  local rs=row.request_source
  if rs~=nil and rs~='manual' and rs~='test' and rs~='programmatic' and rs~='unknown' then return false end
  for _,key in ipairs({'id','pair','revision'}) do if not ctl.hex(row[key],32) then return false end end
  if row.direction~='primary' and row.direction~='reserve' and row.direction~='resume' then return false end
  if not M.STATES[row.state] then return false end
  for _,key in ipairs({'requested','updated'}) do if not finite(row[key]) or num(row[key])<=0 then return false end end
  if num(row.updated)<num(row.requested) or not canon.is_object(row.selection) then return false end
  if row.code~=NULL and not ctl.code_ok(row.code) then return false end
  local selected=row.selection
  local n=0;for _ in pairs(selected) do n=n+1 end
  if row.direction=='resume' then return n==0 end
  if n==1 and selected.tx~=nil then return selected.tx==NULL or ctl.hex(selected.tx,32) end
  if n~=6 then return false end
  for _,k in ipairs({'hash','settings_hash','vendor_identity'}) do if not ctl.hex(selected[k],64) then return false end end
  for _,k in ipairs({'source','target'}) do if not require('history').is_profile(selected[k]) then return false end end
  if selected.source==selected.target or selected.tx==nil then return false end
  return selected.tx==NULL or ctl.hex(selected.tx,32)
end

function M.read(env)
  local row=ctl.read_json(env.run,M.path(env),canon.object({}))
  if canon.is_object(row) and next(row)==nil then return row end
  if not M.valid(row) then value_error('PAIR-MANUAL-STATE-UNVERIFIED') end
  return row
end

function M.active(state,intent,revision)
  return state.phase=='RUNNING' and intent.mode=='on' and state.id==intent.id and state.revision==intent.revision and intent.revision==revision
end

function M.healthy(status,identifier,now,valid_for)
  valid_for=valid_for or 90
  local profiles=getd(status,'profiles',canon.array({}))
  if not canon.is_array(profiles) then return false end
  for _,row in ipairs(profiles) do
    if canon.is_object(row) and row.id==identifier then
      local stamp=num(row.time)
      return stamp~=nil and finite(stamp) and 0<=now-stamp and now-stamp<=valid_for and isnone(row.code) and row.dns_ok==true and (num(row.https_success) or 0)>=2
    end
  end
  return false
end

-- light_gate(direction, settings): the first blocker of an instant click from RAM state only, or nil.
function M.light_gate(env,direction,settings)
  local now=env.run.wall()
  local native=ctl.read_json(env.run,T.paths(env).state,canon.object({}))
  local status=ctl.read_json(env.run,T.paths(env).status,canon.object({}))
  local queued=M.read(env)
  if not canon.is_object(native) or not canon.is_object(status) then return 'PAIR-MANUAL-STATE-UNVERIFIED' end
  local s=native.state
  if (next(queued)~=nil and M.PENDING[queued.state]) or s=='ARMED' or s=='APPLYING' or s=='WAIT-CLIENT' or s=='RESTORING' then return 'PAIR-MANUAL-BUSY' end
  local t=num(native.time)
  if not (t and 0<=now-t and now-t<=30) then return 'PAIR-MANUAL-STALE' end
  local phase=T.journal_read(env).phase
  if not (phase==nil or phase=='ROLLED-BACK' or phase=='COMMITTED' or phase=='HELD-ON-RESERVE') then return 'TRANSACTION-IN-PROGRESS' end
  local target=direction=='primary' and native.source or native.target
  if not M.healthy(status,target,now,pair.valid_for(settings)) then return direction=='primary' and 'SOURCE-NOT-HEALTHY' or 'PAIR-MANUAL-TARGET-UNHEALTHY' end
  return nil
end

function M.terminalize_pending_locked(env,result,code)
  if (result~='CANCELLED' and result~='UNCONFIRMED') or (code~='CONTROL-REVISION-STALE' and code~='PAIR-MANUAL-RECOVERED') then value_error('PAIR-MANUAL-STATE-UNVERIFIED') end
  local row=M.read(env)
  if next(row)~=nil and M.PENDING[row.state] then
    row.state=result;row.updated=canon.float(math.max(env.run.wall(),num(row.requested)));row.code=code
    ctl.write_json(env.run,M.path(env),row)
    return true
  end
  return false
end

function M.lease_until(settings,state,now)
  local until_=tonumber(settings.native_until~=nil and settings.native_until~=NULL and settings.native_until or 0)
  if not until_ then return nil end
  if settings.native_trial~=state.id or not (now+30<=until_ and until_<=now+14400) then return nil end
  return until_
end

-- manual_dispatch._confirmed_return / _confirmed_reserve
function M.confirmed_return(record,result,value,live_order,live_hash,now)
  return canon.is_object(result) and result.ok==true and result.code=='RETURNED' and num(result.request)==record.requested_at
    and finite(result.time) and record.requested_at<=num(result.time) and num(result.time)<=now
    and value.tx==record.transaction_id and value.phase=='ROLLED-BACK' and value.source==record.source_id and value.target==record.target_id
    and same_list(live_order,getd(value,'restored_order',value.before)) and live_hash==value.hash
end
function M.confirmed_reserve(record,value,live_order,live_hash)
  return record.direction=='reserve' and value.manual_request_id==record.request_id and value.phase=='HELD-ON-RESERVE' and not isnone(value.confirmed)
    and value.source==record.source_id and value.target==record.target_id and value.hash==record.selection_hash and value.vendor_identity==record.vendor_identity
    and (num(value.started) or 0)>=record.requested_at and (num(value.confirmed) or 0)>=(num(value.started) or 0)
    and same_list(live_order,value.after) and live_hash==value.hash
end

-- manual_dispatch.recover_pending: report interrupted claimed legacy work; never replay it.
function M.recover_pending(env)
  if not (env.deps and env.deps.manual_control) then return end
  local record=ctl.read_json_safe(env.run,env.runtime..'/manual-control.json',canon.object({}))
  if not env.deps.manual_control.valid_record(record) or not (record.state=='CLAIMED' or record.state=='APPLYING' or record.state=='WAIT-CLIENT') then return end
  local value=T.journal_read(env)
  T.bind_policy_context(env,value)
  local lo,lh=env.backend.order()
  local verified=M.confirmed_reserve(record,value,lo,lh)
  env.deps.manual_control.publish_result(record.request_id,verified and 'COMPLETED' or 'UNCONFIRMED',verified and value.tx or nil,verified and nil or 'MANUAL-SUPERVISOR-RECOVERED')
end

------------------------------------------------------------------------------------------------------
-- the instant path: native_switch.instant_manual built on instant_switch.lua
------------------------------------------------------------------------------------------------------
function M.instant_manual(env,selection,until_,revision,request_id,request_source,destination,session_order,kernel_before)
  local scope=getd(selection,'proof_scope','external-lan')
  if not ctl.hex(request_id,32) or (destination~='source' and destination~='target') or scope~='router-probed-ipv4' or session_order==nil then refuse('MANUAL-REQUEST-INVALID') end
  T.bind_policy_context(env,selection)
  T.require_control_revision(env,revision)
  local before=copy_list(selection.order)
  local ok,ctx,after=pcall(function()
    local ctx=P.transition(selection,session_order,destination)
    return ctx,P.desired_order(ctx,before,destination)
  end)
  if not ok then refuse('POLICY-IDENTITY-CHANGED') end
  kernel_before=kernel_before or env.backend.attest_policy(selection)
  local fingerprint=kernel_before.kernel_fingerprint
  if not (kernel_before.verified==true or kernel_before.repairable_missing==true) or not ctl.hex(fingerprint,64) then refuse('KERNEL-POLICY-UNVERIFIED') end
  -- assess() checks the stock boot prefix (pins, owners, modes) and says whether it is already in place. Only
  -- then is prepare() skipped: it would take the control lock just to re-run the same checks and write nothing;
  -- a Stop in between is caught by the control revision of every fenced write of instant.switch below.
  if env.deps and env.deps.rtp_boot then
    local assessed=env.deps.rtp_boot.assess()
    if not (type(assessed)=='table' and assessed.ready==true) then env.deps.rtp_boot.prepare(revision) end
  end
  local tx=ctl.uuid_hex();local wall_,mono_=env.run.wall(),env.run.clock()
  local settings=env.backend.policy().settings
  local lease_end,lease_error=T.monotonic_lease(env,settings,until_,wall_,mono_)
  if lease_error then refuse(lease_error) end
  local source=ctl.normalize_request_source(request_source)
  local profiles=canon.object({})
  for _,role in ipairs({'source','target'}) do
    local row=canon.object({})
    for _,key in ipairs({'id','protocol','interface','vendor_tunnel_id','vendor_generation'}) do row[key]=selection[role][key]==nil and NULL or selection[role][key] end
    profiles[role]=row
  end
  local value=canon.object({tx=tx,phase='APPLYING',before=before,after=after,hash=selection.hash,source=selection.source.id,target=selection.target.id,
    deadline=canon.float(math.min(until_,wall_+T.TRANSACTION_SECONDS)),monotonic_deadline=canon.float(math.min(lease_end,mono_+T.TRANSACTION_SECONDS)),
    lease_monotonic_until=canon.float(lease_end),trial=false,trial_nonce=getd(settings,'native_trial',NULL),pid=NULL,started=canon.float(wall_),
    vendor_identity=selection.vendor_identity,process_bindings=getd(selection,'process_bindings',NULL),proof_scope=scope,control_revision=revision,
    manual_request_id=request_id,pair_transition=ctx,vendor_profiles=profiles,kernel_before_fingerprint=fingerprint,kernel_before_verified=kernel_before.verified==true,
    forward_policy_touched=true,rtp_dispatched=true,transition_source=source,manual_instant=true})
  P.metadata(value)
  local function publish_pair(row) T.publish(env,merge(row,{transition_source=source,destination_role=destination,destination_profile_id=selection[destination].id})) end
  publish_pair(merge(T.pair_event_fields(value),{state='APPLYING',source=value.source,target=value.target,trial=false,reason='OPERATOR-MANUAL',manual_instant=true,
    transition_kind=T.transition_kind(selection.source,selection.target)}))
  local names,tunnels=env.backend.instant_request(selection,after)
  local request=canon.object({direction=destination=='source' and 'primary' or 'reserve',control_revision=revision,journal=value,names=names,tunnel_order=tunnels})
  local result=instant.switch(env.run,request,request.direction,{journal_path=T.paths(env).journal})
  T.manual_stamp(env,'switched')
  if result.ok~=true then
    local code=type(result.code)=='string' and result.code or 'NATIVE-SYSTEM-001'
    local err=setmetatable({code=code},ctl.Refused)
    local sok,saved=pcall(T.journal_read,env)
    if sok and saved.tx==tx then value=saved end
    value.failure_detail=T.record_attempt_failure(env,tx,'instant',err,mono_);value.failure_code=code
    if result.rollback_required then
      pcall(T.journal_write,env,value)
      require('rollback').rollback_counted(env,value,'TRANSACTION-FAILED')
    else
      if value.phase~='ROLLED-BACK' then value.phase='ROLLED-BACK';value.reason='FAILED-BEFORE-APPLY';value.restored_order=copy_list(before);value.finished=fwall(env) end
      pcall(T.journal_write,env,value)
      publish_pair(merge(T.pair_event_fields(value,{completed=true,outcome='refused',restoring=true}),{state='ROLLED-BACK',reason='TRANSACTION-FAILED',
        source=value.source,target=value.target,blockers=canon.array({code})}))
    end
    error(err,0)
  end
  if not order_is(env,after,selection.hash) then refuse('POLICY-CHANGED-DURING-APPLY') end
  local kernel=env.backend.attest_policy(merge(selection,{order=copy_list(after)}))
  if kernel.verified~=true or kernel.role~=destination then refuse('KERNEL-POLICY-UNVERIFIED') end
  if not env.backend.guard_exists() then env.backend.guard(env.backend.devices(),revision) end
  T.manual_stamp(env,'verified')
  return kernel
end

------------------------------------------------------------------------------------------------------
-- consume / held_reserve
------------------------------------------------------------------------------------------------------
function M.consume(env,state,settings,revision)
  local row=M.read(env)
  if next(row)==nil or not M.PENDING[row.state] then return false end
  local claimed=env.run.lock(function()
    row=M.read(env)
    if next(row)==nil or not M.PENDING[row.state] then return false end
    if row.state=='CLAIMED' then M.terminalize_pending_locked(env,'UNCONFIRMED','PAIR-MANUAL-RECOVERED');return true end
    local reason=nil
    local now=env.run.wall()
    if ctl.revision_locked(env)~=row.revision or row.pair~=state.id then reason='CONTROL-REVISION-STALE'
    elseif not (num(row.requested)<=now and now<=num(row.requested)+60) then reason='PAIR-MANUAL-EXPIRED' end
    if reason then
      row.state='CANCELLED';row.updated=canon.float(math.max(now,num(row.requested)));row.code=reason;ctl.write_json(env.run,M.path(env),row);return true
    end
    row.state='CLAIMED';row.updated=canon.float(now);ctl.write_json(env.run,M.path(env),row)
    return 'claimed'
  end,env.runtime)
  if claimed~='claimed' then return claimed end
  T.manual_stamp(env,'claimed',row.id)
  local function finish(result,code)
    env.run.lock(function()
      local current=M.read(env)
      if next(current)==nil or current.id~=row.id or not M.PENDING[current.state] then return end
      if ctl.revision_locked(env)~=revision then result='CANCELLED';code='CONTROL-REVISION-STALE' end
      current.state=result;current.code=code==nil and NULL or code;current.updated=canon.float(math.max(env.run.wall(),num(row.requested)))
      ctl.write_json(env.run,M.path(env),current)
    end,env.runtime)
  end
  local ok,err=pcall(function()
    pair.require_running(env,revision)
    if row.direction=='resume' then
      env.run.lock(function() pair.require_running(env,revision);state.manual_hold=nil;state.manual_selection=nil;pair.save(env,state) end,env.runtime)
      finish('COMPLETED');return
    end
    T.bind_policy_context(env,state)
    local blockers,selection=env.backend.diagnostic()
    local expected=row.selection
    T.manual_stamp(env,'diagnosed')
    if #blockers>0 then refuse(blockers[1]) end
    local tx_only=expected.tx~=nil and expected.hash==nil
    if not tx_only and (selection.hash~=expected.hash or getd(selection,'settings_hash',NULL)~=expected.settings_hash or selection.vendor_identity~=expected.vendor_identity
                        or selection.source.id~=expected.source or selection.target.id~=expected.target) then refuse('MANUAL-CONFIG-CHANGED') end
    local value=T.journal_read(env)
    local hold,kernel,fresh
    if not isnone(state.policy_roles) then
      local lo,lh=env.backend.order()
      if canon.encode(P.proof(selection))~=canon.encode(state.policy_roles) or getd(value,'tx',NULL)~=getd(expected,'tx',NULL)
         or not (value.phase==nil or value.phase=='ROLLED-BACK' or value.phase=='COMMITTED' or value.phase=='HELD-ON-RESERVE')
         or not P.state_order_matches(state,value,lo,lh) then refuse('MANUAL-CONFIG-CHANGED') end
      hold=row.direction=='primary' and 'source' or 'target'
      local instant_on=env.backend.fast_switch_enabled()
      local alive=instant_on and M.healthy(ctl.read_json(env.run,T.paths(env).status,canon.object({})),selection[hold].id,env.run.wall(),pair.valid_for(settings))
      if not alive and env.backend.health(selection[hold].id)~=true then refuse(hold=='source' and 'SOURCE-NOT-HEALTHY' or 'PAIR-MANUAL-TARGET-UNHEALTHY') end
      kernel=env.backend.attest_policy(selection)
      T.manual_stamp(env,'attested')
      if kernel.verified==true and kernel.role==hold then
        if kernel.policy_hash~=selection.hash or not same_list(kernel.order,selection.order) then refuse('KERNEL-POLICY-UNVERIFIED') end
        local profiles=canon.object({})
        for _,key in ipairs({'source','target'}) do
          local identity=pair.profile_identity(env,selection[key])
          if not identity then refuse('PROFILE-IDENTITY-CHANGED') end
          profiles[key]=identity
        end
        local selected=canon.object({request_id=row.id,role=hold,order=copy_list(selection.order),hash=selection.hash,vendor_identity=selection.vendor_identity,profiles=profiles})
        env.run.lock(function()
          pair.require_running(env,revision);state.manual_hold=hold;state.manual_hold_source=getd(row,'request_source','unknown')
          pair.remember_selected(env,state,kernel);state.manual_selection=selected;pair.save(env,state)
        end,env.runtime)
        T.publish(env,{state='OBSERVING',mode='continuous-pair',proof_scope=pair.MODE,source=selection.source.id,target=selection.target.id,reason='MANUAL-ALREADY-SELECTED',
          manual=true,readiness_verified=true,kernel_policy_verified=true,kernel_proof=kernel,route_changed=false,transition_completed=true,
          transition_outcome='policy-verified',transition_source=getd(row,'request_source','unknown')})
        finish('COMPLETED','MANUAL-ALREADY-SELECTED');return
      end
      if kernel.verified~=true and kernel.repairable_missing~=true then refuse('KERNEL-POLICY-UNVERIFIED') end
      if instant_on then
        pair.require_running(env,revision)
        local until_=M.lease_until(settings,state,env.run.wall()) or pair.configure_lease(env,state)
        T.manual_stamp(env,'lease')
        kernel=M.instant_manual(env,selection,until_,revision,row.id,row.request_source,hold,state.order,kernel)
        fresh=selection
      else
        local recovery=pair.recovery_normalized(settings)
        pair.require_running(env,revision)
        local now=env.run.wall()
        local events,permitted=pair.budget(ctl.read_json(env.run,select(3,pair.paths(env)),canon.object({events=canon.array({})})).events,now,recovery.attempt_window*60,recovery.attempt_limit)
        if not permitted then refuse('PAIR-RATE-LIMIT') end
        if #events>0 and now-num(events[#events])<math.max(recovery.cooldown,recovery.min_dwell) then refuse('PAIR-MANUAL-COOLDOWN') end
        local until_=pair.configure_lease(env,state)
        local b2;b2,fresh=env.backend.diagnostic()
        if #b2>0 then refuse(b2[1]) end
        lo,lh=env.backend.order()
        if canon.encode(P.proof(fresh))~=canon.encode(state.policy_roles) or fresh.hash~=expected.hash or getd(fresh,'settings_hash',NULL)~=expected.settings_hash
           or fresh.vendor_identity~=expected.vendor_identity or not P.state_order_matches(state,value,lo,lh) then refuse('MANUAL-CONFIG-CHANGED') end
        T.attempt(env,fresh,until_,false,{control_revision=revision,manual_request_id=row.id,request_source=row.request_source,pair_destination=hold,pair_session_order=state.order,
          on_dispatch=function()
            pair.require_running(env,revision);local stamp=env.run.wall()
            local charged,allowed=pair.budget(ctl.read_json(env.run,select(3,pair.paths(env)),canon.object({events=canon.array({})})).events,stamp,recovery.attempt_window*60,recovery.attempt_limit)
            if not allowed then refuse('PAIR-RATE-LIMIT') end
            if #charged>0 and stamp-num(charged[#charged])<math.max(recovery.cooldown,recovery.min_dwell) then refuse('PAIR-MANUAL-COOLDOWN') end
            charged[#charged+1]=canon.float(stamp);ctl.write_json(env.run,select(3,pair.paths(env)),canon.object({events=charged}))
          end})
      end
      value=T.journal_read(env);local context=P.metadata(value)
      if context==nil or context.destination_role~=hold or not same_list(context.session_order,state.order) or value.manual_request_id~=row.id
         or value.phase~='HELD-ON-RESERVE' or isnone(value.confirmed) or not order_is(env,value.after,value.hash) then refuse('MANUAL-COMPLETION-UNVERIFIED') end
      if not instant_on then kernel=env.backend.attest_policy(merge(fresh,{order=copy_list(value.after)})) end
      if kernel.verified~=true or kernel.role~=hold then refuse('KERNEL-POLICY-UNVERIFIED') end
    elseif row.direction=='reserve' then
      if not (value.phase==nil or value.phase=='ROLLED-BACK') or not order_is(env,state.order,state.policy_hash) then refuse('TRANSACTION-IN-PROGRESS') end
      if env.backend.health(selection.target.id)~=true then refuse('PAIR-MANUAL-TARGET-UNHEALTHY') end
      local recovery=pair.recovery_normalized(settings)
      pair.require_running(env,revision);local now=env.run.wall()
      local events,permitted=pair.budget(ctl.read_json(env.run,select(3,pair.paths(env)),canon.object({events=canon.array({})})).events,now,recovery.attempt_window*60,recovery.attempt_limit)
      if not permitted then refuse('PAIR-RATE-LIMIT') end
      if #events>0 and now-num(events[#events])<math.max(recovery.cooldown,recovery.min_dwell) then refuse('PAIR-MANUAL-COOLDOWN') end
      pair.require_running(env,revision);events[#events+1]=canon.float(now);ctl.write_json(env.run,select(3,pair.paths(env)),canon.object({events=events}))
      local until_=pair.configure_lease(env,state);local b2;b2,selection=env.backend.diagnostic()
      if #b2>0 then refuse(b2[1]) end
      T.attempt(env,selection,until_,false,{control_revision=revision,manual_request_id=row.id,request_source=row.request_source})
      value=T.journal_read(env)
      if value.manual_request_id~=row.id or value.phase~='HELD-ON-RESERVE' or isnone(value.confirmed) or not order_is(env,value.after,value.hash) then refuse('MANUAL-COMPLETION-UNVERIFIED') end
      hold='target'
    else
      if getd(value,'tx',NULL)~=getd(expected,'tx',NULL) or (value.phase~='COMMITTED' and value.phase~='HELD-ON-RESERVE') then refuse('RETURN-TRANSACTION-MISMATCH') end
      local handled=T.handle_return(env,value,canon.object({time=row.requested,tx=value.tx}),0,revision)
      local record={requested_at=num(row.requested),transaction_id=value.tx,source_id=selection.source.id,target_id=selection.target.id}
      local lo,lh=env.backend.order()
      if not handled or not M.confirmed_return(record,ctl.read_json(env.run,T.paths(env).return_result,canon.object({})),T.journal_read(env),lo,lh,env.run.wall()) then refuse('RETURN-UNCONFIRMED') end
      hold='source'
    end
    env.run.lock(function()
      pair.require_running(env,revision);state.manual_selection=nil;state.manual_hold=hold;state.manual_hold_source=getd(row,'request_source','unknown')
      if not isnone(state.policy_roles) then
        pair.remember_selected(env,state,kernel)
        local profiles=canon.object({})
        for _,key in ipairs({'source','target'}) do profiles[key]=pair.profile_identity(env,fresh[key]) or NULL end
        state.manual_selection=canon.object({request_id=row.id,role=hold,order=copy_list(value.after),hash=value.hash,vendor_identity=fresh.vendor_identity,profiles=profiles})
      end
      pair.save(env,state)
    end,env.runtime)
    T.manual_stamp(env,'saved')
    local general=not isnone(state.policy_roles)
    local fields=general and T.pair_event_fields(value,{completed=true,outcome='committed'}) or {}
    if value.manual_instant==true then fields=merge(fields,{manual_instant=true,switch_seconds=getd(value,'instant_seconds',NULL)}) end
    T.publish(env,merge(fields,{state=hold=='target' and 'COMMITTED' or (general and 'OBSERVING' or 'ROLLED-BACK'),mode='continuous-pair',proof_scope=pair.MODE,
      source=selection.source.id,target=selection.target.id,reason='OPERATOR-MANUAL',manual=true,readiness_verified=general,kernel_policy_verified=general,
      kernel_proof=general and kernel or NULL,transition_source=getd(row,'request_source','unknown'),original_restored=order_is(env,state.order,state.policy_hash)}))
    finish('COMPLETED');T.manual_stamp(env,'done')
  end)
  if not ok then
    if not is_refused(err) then error(err,0) end
    local refused=not err.value_error
    local code=(refused and ctl.code_ok(err.code)) and err.code or 'PAIR-MANUAL-UNCONFIRMED'
    finish(refused and 'REFUSED' or 'UNCONFIRMED',code)
  end
  return true
end

-- the steady hold re-proves its channel with a live probe at most this often (backend.health reuse)
M.HOLD_HEALTH_REUSE=30
function M.held_reserve(env,state,value,settings,status)
  T.bind_policy_context(env,state)
  local adopted=state.manual_selection
  if canon.is_object(adopted) and state.manual_hold==adopted.role then
    local blockers,selection=env.backend.diagnostic()
    if #blockers>0 then refuse(blockers[1]) end
    local kernel=env.backend.attest_policy(selection)
    if kernel.verified~=true then return false end
    local current=pair.profile_identity(env,selection[adopted.role]);local expected=adopted.profiles[adopted.role]
    local lo,lh=env.backend.order()
    local function same_identity(a,b) for _,k in ipairs({'id','protocol','interface','vendor_tunnel_id'}) do if a[k]~=b[k] then return false end end;return true end
    if kernel.role~=adopted.role or not same_list(lo,adopted.order) or lh~=adopted.hash or current==nil or not same_identity(current,expected) then refuse('PAIR-MANUAL-HOLD-UNVERIFIED') end
    if env.backend.health(selection[adopted.role].id,M.HOLD_HEALTH_REUSE)~=true then state.manual_hold=nil;state.manual_selection=nil;pair.save(env,state);return false end
    if canon.encode(current)~=canon.encode(expected) then adopted.profiles[adopted.role]=current;pair.save(env,state) end
    pair.resume_running(env,state)
    T.publish(env,{state='OBSERVING',reason=adopted.role=='target' and 'PAIR-MANUAL-HOLD-RESERVE' or 'PAIR-MANUAL-HOLD-PRIMARY',manual=true,source=selection.source.id,target=selection.target.id,
      readiness_verified=true,kernel_policy_verified=true,kernel_proof=kernel,transition_source=getd(state,'manual_hold_source','unknown'),mode='continuous-pair',proof_scope=pair.MODE})
    return true
  end
  local context=P.metadata(value)
  local now=env.run.wall();local age=pair.valid_for(settings)
  if (state.manual_hold=='source' or state.manual_hold=='target') and context~=nil then
    local hold=state.manual_hold
    local lo,lh=env.backend.order()
    if isnone(value.confirmed) or P.current_role(value)~=hold or not P.state_order_matches(state,value,lo,lh) then refuse('PAIR-MANUAL-HOLD-UNVERIFIED') end
    local kernel=env.backend.attest_policy()
    if kernel.verified~=true then return false end
    local resolved=env.deps.resolve_pair(status,settings,now,age,pair.settle_for(settings))
    local expected=getd(getd(value,'vendor_profiles',canon.object({})),hold,nil);local profile=resolved[hold]
    if resolved.coordination.state~='READY' or isnone(profile) or profile.id~=value[hold] or expected==nil or canon.encode(pair.profile_identity(env,profile) or NULL)~=canon.encode(expected) then
      T.publish(env,{state='BLOCKED',reason='PROFILE-IDENTITY-CHANGED',blockers=canon.array({'PROFILE-IDENTITY-CHANGED'}),source=value.source,target=value.target,mode='continuous-pair',proof_scope=pair.MODE})
      return true
    end
    if pair.streak(pair.scoped_samples(env,getd(status,'samples',canon.array({})),profile),profile.id,pair.recovery_normalized(settings).failures,now,age,false,profile,env) then
      state.manual_hold=nil;pair.save(env,state);return false
    end
    pair.resume_running(env,state)
    T.publish(env,{state=hold=='target' and 'COMMITTED' or 'OBSERVING',reason=hold=='target' and 'PAIR-MANUAL-HOLD-RESERVE' or 'PAIR-MANUAL-HOLD-PRIMARY',manual=true,
      transition_source=getd(state,'manual_hold_source','unknown'),source=value.source,target=value.target,readiness_verified=true,kernel_policy_verified=true,kernel_proof=kernel,mode='continuous-pair',proof_scope=pair.MODE})
    return true
  end
  if state.manual_hold~='target' then return false end
  if (value.phase~='COMMITTED' and value.phase~='HELD-ON-RESERVE') or isnone(value.confirmed) or not order_is(env,value.after,value.hash) then refuse('PAIR-MANUAL-HOLD-UNVERIFIED') end
  local row=nil
  for _,p in ipairs(getd(status,'profiles',canon.array({}))) do if p.id==value.target then row=p end end
  local recovery=pair.recovery_normalized(settings)
  local resolved=env.deps.resolve_pair(status,settings,now,age,pair.settle_for(settings))
  local expected=getd(getd(value,'vendor_profiles',canon.object({})),'target',nil)
  local verified=resolved.coordination.state=='READY' and not isnone(resolved.target) and resolved.target.id==value.target
    and (expected==nil or canon.encode(pair.profile_identity(env,resolved.target) or NULL)==canon.encode(expected))
  if not verified then
    T.publish(env,{state='DEGRADED-ON-RESERVE',reason='RESERVE-IDENTITY-UNKNOWN',manual=true,transition_source=getd(state,'manual_hold_source','unknown'),source=value.source,target=value.target,mode='continuous-pair',proof_scope=pair.MODE})
    return true
  end
  local failed=row~=nil and pair.streak(pair.scoped_samples(env,getd(status,'samples',canon.array({})),row),row.id,recovery.failures,now,age,false,row,env)
  if failed then state.manual_hold=nil;pair.save(env,state);return false end
  T.publish(env,{state='COMMITTED',reason='PAIR-MANUAL-HOLD-RESERVE',manual=true,transition_source=getd(state,'manual_hold_source','unknown'),source=value.source,target=value.target,mode='continuous-pair',proof_scope=pair.MODE})
  return true
end

return M
