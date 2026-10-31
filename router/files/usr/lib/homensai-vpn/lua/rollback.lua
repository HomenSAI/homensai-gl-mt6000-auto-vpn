-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- rollback.lua: native_switch.rollback / rollback_counted / give_up / abandon in Lua (2.0.0-lua-alpha2).
--
-- The journal phases and their writes are the Python ones: RESTORING with restore_target_order and
-- restore_kernel_fingerprint, ROLLED-BACK with restored_order, RELEASE-PENDING when our guard could not be
-- removed. rollback_counted() increments rollback_failures (bounded by ROLLBACK_FAILURE_LIMIT=2, checked by
-- journal.validate) so that a repeated failure ends in give_up() instead of a loop.
-- Not ported yet (called through env.deps.rollback_recovery when present, else the step is refused with the
-- Python code): vendor_rebuild_applies/rebuild (a worker that died inside rtp2.sh), authorize/promote_forward/
-- record_step/order_allowed (recorded restore steps), settled; and env.deps.activation_finalize.
local canon=require('canon')
local ctl=require('auto_control')
local T=require('transaction')

local M={}
local NULL=canon.null
local isnone,num=ctl.isnone,ctl.num
local refuse=ctl.refuse
local same_list,copy_list,order_is,in_orders,getd,merge=T.same_list,T.copy_list,T.order_is,T.in_orders,T.getd,T.merge
local function fwall(env) return canon.float(env.run.wall()) end

function M.recovery_package(env) return env.version or '2.0.0-lua-alpha2' end

-- abandon(): the router policy was changed by someone else - stop, release our guard, never hold the LAN.
function M.abandon(env,value,code)
  local ok=pcall(env.backend.unguard)
  if not ok then
    value.phase='RELEASE-PENDING';value.reason=code;value.abandoned=true
    T.journal_write(env,value)
    ctl.stop_latch(env,getd(value,'trial_nonce',NULL))
    env.backend.clear_native_options()
    T.publish(env,{state='BLOCKED',reason='GUARD-RELEASE-UNCONFIRMED',blockers=canon.array({'GUARD-RELEASE-UNCONFIRMED'}),guard='unverified',
      original_restored=false,source=getd(value,'source',NULL),target=getd(value,'target',NULL)})
    refuse('GUARD-RELEASE-UNCONFIRMED')
  end
  value.phase='ROLLED-BACK';value.reason=code;value.abandoned=true;value.finished=fwall(env)
  pcall(T.journal_write,env,value)
  pcall(ctl.stop_latch,env,getd(value,'trial_nonce',NULL))
  env.backend.clear_native_options()
  pcall(T.publish,env,{state='STOPPED',reason=code,original_restored=false,source=getd(value,'source',NULL),target=getd(value,'target',NULL),trial=getd(value,'trial',false)})
end

local function rr(env) return env.deps and env.deps.rollback_recovery or nil end

function M.rollback(env,value,reason,restore_order)
  local policy=require('pair').policy
  local pair=require('pair')
  local restore_started=env.run.wall()
  T.bind_policy_context(env,value)
  if value.activation_reapply==true and same_list(value.before,value.after)
     and (value.phase=='ARMED' or value.phase=='APPLYING' or value.phase=='RESTORING')
     and isnone(value.confirmed) and isnone(value.kernel_confirmed) and value.kernel_before_verified==false then
    if pair.intent(env).mode=='off' then
      if not (env.deps and env.deps.activation_finalize) then refuse('ACTIVATION-RECOVERY-UNAVAILABLE') end
      env.deps.activation_finalize(env,pair.read_state(env),value,true)
      return
    end
  end
  local restore_fingerprint,resume_check,recovery_revision=nil,nil,nil
  local pair_context=nil
  if not isnone(value.pair_transition) and value.rtp_dispatched==false
     and (value.phase=='ARMED' or value.phase=='APPLYING' or value.phase=='WAIT-CLIENT' or value.phase=='RESTORING') then
    -- The kernel may now be foreign: undo only our UCI ordering, never invoke RTP for a transaction that did not dispatch it.
    local order,fingerprint=env.backend.order()
    if fingerprint~=value.hash or not in_orders(order,value.before,value.after) then
      M.abandon(env,value,'EXTERNAL-POLICY-CHANGE')
      refuse('EXTERNAL-POLICY-CHANGE-RELEASED')
    end
    if not same_list(order,value.before) then env.backend.reorder(value.before) end
    -- Power cut (POWER-CUT-INTEGRITY-2026-10-31.ru.md): the vendor rebuilt the kernel at boot from the MOVED UCI
    -- order, so undoing UCI alone would leave the traffic on the reserve while UCI and this journal say primary.
    -- When the kernel is no longer the one recorded before our move, the vendor's own reload from the restored UCI
    -- makes it follow again (the same rebuild every route-policy change triggers). Best effort: a failure keeps
    -- the previous behaviour (journal ROLLED-BACK, kernel_policy_verified=false, the loop's attestation blocks).
    if ctl.hex(value.kernel_before_fingerprint,64) then
      local kok,live=pcall(env.backend.kernel_fingerprint)
      if kok and live~=value.kernel_before_fingerprint then pcall(env.backend.apply) end
    end
    local devices=env.backend.devices()
    if #devices>0 then env.backend.guard(devices) end
    value.phase='ROLLED-BACK';value.reason=reason;value.finished=fwall(env);value.restore_before_order=copy_list(order)
    value.restore_before_verified=false;value.restored_order=copy_list(value.before);value.kernel_policy_verified=false
    T.journal_write(env,value)
    local fields=T.pair_event_fields(value,{completed=true,outcome='refused',restoring=true})
    T.publish(env,merge(fields,{state='ROLLED-BACK',reason=reason,source=value.source,target=value.target,
      proof_scope=getd(value,'proof_scope','router-probed-ipv4'),blockers=canon.array(not isnone(value.failure_code) and {value.failure_code} or {}),
      original_restored=false,transition_source=getd(value,'transition_source','unknown')}))
    return
  end
  if not isnone(value.pair_transition) then
    local ok,ctx=pcall(policy.metadata,value)
    if not ok then refuse('JOURNAL-INTEGRITY-FAILED') end
    pair_context=ctx
    local helpers=rr(env)
    if helpers and helpers.vendor_rebuild_applies(env,value) then
      return helpers.rebuild(env,value,reason,restore_order or getd(value,'restore_target_order',nil) or value.before)
    end
    restore_order=restore_order or getd(value,'restore_target_order',nil) or value.before
    if not in_orders(restore_order,value.before,pair_context.primary_order,pair_context.session_order) then refuse('POLICY-IDENTITY-CHANGED') end
    local live_order,live_hash=env.backend.order()
    if live_hash~=value.hash then refuse('POLICY-IDENTITY-CHANGED') end
    local known_order=in_orders(live_order,value.before,value.after,value.restored_order,value.restore_target_order)
    if helpers then helpers.vendor_settled(env) end
    local kernel_before=env.backend.attest_policy()
    local pending_step=value.phase=='RESTORING' and value.restore_order_step~=nil
    local same_graph=false
    if pending_step then
      if not helpers then refuse('KERNEL-POLICY-UNVERIFIED') end
      if not helpers.order_allowed(value,live_order) then refuse('POLICY-IDENTITY-CHANGED') end
      same_graph=kernel_before.kernel_fingerprint==value.restore_kernel_fingerprint
      if not same_graph and not (kernel_before.verified==true and same_list(live_order,value.restore_target_order)
                                 and (value.restore_rtp_dispatched==true or value.rtp_dispatched==true)) then refuse('KERNEL-POLICY-UNVERIFIED') end
    end
    if (pending_step and same_graph) or not known_order or not (kernel_before.verified==true or kernel_before.repairable_missing==true) then
      if not helpers then refuse('KERNEL-POLICY-UNVERIFIED') end
      if value.phase=='APPLYING' or value.phase=='WAIT-CLIENT' then resume_check,recovery_revision=helpers.promote_forward(env,value,restore_order)
      else resume_check,recovery_revision=helpers.authorize(env,value) end
    end
    restore_fingerprint=kernel_before.kernel_fingerprint
    if not ctl.hex(restore_fingerprint,64) then refuse('KERNEL-POLICY-UNVERIFIED') end
    if resume_check~=nil and restore_fingerprint~=value.restore_kernel_fingerprint then refuse('KERNEL-POLICY-UNVERIFIED') end
    if env.backend.kernel_fingerprint()~=restore_fingerprint then refuse('KERNEL-POLICY-UNVERIFIED') end
    if not order_is(env,live_order,live_hash) then refuse('POLICY-IDENTITY-CHANGED') end
    if resume_check==nil then
      value.restore_before_order=copy_list(live_order);value.restore_before_verified=kernel_before.verified==true
      for _,key in ipairs({'restore_order_step','restore_proof_source','restore_order_origin','restore_rtp_dispatched'}) do value[key]=nil end
    end
    if value.phase=='ARMED' and isnone(value.pid) and same_list(restore_order,value.before) and order_is(env,value.before,value.hash) then
      value.phase='ROLLED-BACK';value.reason=reason;value.finished=fwall(env);value.restored_order=copy_list(restore_order)
      T.journal_write(env,value);return
    end
    value.restore_target_order=copy_list(restore_order);value.phase='RESTORING';value.restore_kernel_fingerprint=restore_fingerprint
    T.journal_write(env,value)
    local fields=T.pair_event_fields(value,{restoring=true,restore_order=restore_order})
    T.publish(env,merge(fields,{state='RESTORING',reason=reason,source=value.source,target=value.target,proof_scope=getd(value,'proof_scope','router-probed-ipv4')}))
  elseif restore_order~=nil and not same_list(restore_order,value.before) then
    refuse('POLICY-IDENTITY-CHANGED')
  end
  restore_order=restore_order or value.before
  T.note_phase(env,value,'RESTORING')
  if value.phase=='ARMED' and isnone(value.pid) and order_is(env,value.before,value.hash) then
    value.phase='ROLLED-BACK';value.reason=reason;value.finished=fwall(env);T.journal_write(env,value);return
  end
  env.backend.guard()
  local function restore_check()
    if restore_fingerprint==nil then return end
    if resume_check~=nil then resume_check() end
    local _,h=env.backend.order()
    if h~=value.hash or env.backend.kernel_fingerprint()~=restore_fingerprint then refuse('KERNEL-POLICY-UNVERIFIED') end
  end
  -- detail: {op='reorder',section=,index=} | {op='commit'} | ... (the facts of Python's command line for record_step);
  -- fn may return a waiter: a command dispatched under the lock is awaited outside it (forward_dispatch)
  local function restore_command(kind,fn,detail)
    restore_check()
    if restore_fingerprint~=nil then
      local helpers=rr(env)
      if helpers then helpers.record_step(env,value,kind,detail) end
      restore_check()
    end
    if kind=='rtp' or kind=='kernel' then value.restore_rtp_dispatched=true;T.journal_write(env,value) end
    local result
    if recovery_revision~=nil then result=env.run.fenced(recovery_revision,fn) else result=fn() end
    if type(result)=='function' then result=result() end
    return result
  end
  local order,fingerprint=env.backend.order()
  if fingerprint~=value.hash or (resume_check==nil and not in_orders(order,value.before,value.after,value.restored_order,value.restore_target_order)) then
    M.abandon(env,value,'EXTERNAL-POLICY-CHANGE')
    refuse('EXTERNAL-POLICY-CHANGE-RELEASED')
  end
  if restore_fingerprint~=nil then
    restore_check()
    if not same_list(order,restore_order) then env.backend.reorder(restore_order,restore_check,restore_command)
    elseif resume_check~=nil and value.restore_order_step~=nil then restore_command('uci',function() return env.backend.uci_commit() end,{op='commit'}) end
    restore_check()
    env.backend.apply(restore_command)
  else
    if not same_list(order,restore_order) then env.backend.reorder(restore_order) end
    env.backend.apply()
  end
  order,fingerprint=env.backend.order()
  if not same_list(order,restore_order) or fingerprint~=value.hash then
    pcall(function() env.backend.guard(env.backend.devices()) end)
    refuse('ROLLBACK-UNVERIFIED')
  end
  local proof={}
  if pair_context~=nil then
    local helpers=rr(env)
    local blockers,current
    if helpers and helpers.settled then blockers,current=helpers.settled(env) else blockers,current=env.backend.diagnostic() end
    if #blockers==0 and current then proof=env.backend.attest_policy(current) end
    if proof.verified~=true or proof.role~=policy.role(pair_context,restore_order) then
      env.backend.guard(env.backend.devices())
      refuse('ROLLBACK-UNVERIFIED')
    end
  end
  value.phase='ROLLED-BACK';value.reason=reason;value.finished=fwall(env)
  if pair_context~=nil then value.restored_order=copy_list(restore_order) end
  T.journal_write(env,value)
  if (reason=='PRIMARY-STABLY-RECOVERED' or not isnone(value.manual_request_id)) and env.deps and env.deps.record_switch_time then
    pcall(env.deps.record_switch_time,env,num(value.finished)-restore_started)
  end
  env.backend.guard(env.backend.devices())
  if pair_context~=nil then
    local fields=T.pair_event_fields(value,{completed=true,outcome='restored',restoring=true})
    local state=(reason=='PAIR-STOPPED' or reason=='SERVICE-STOPPED' or reason=='SUPERVISOR-RECOVERY') and 'RESTORING' or 'ROLLED-BACK'
    local row=merge(fields,{state=state,reason=reason,source=value.source,target=value.target,proof_scope=getd(value,'proof_scope','router-probed-ipv4'),
      kernel_proof=proof,original_restored=same_list(restore_order,pair_context.session_order)})
    if reason=='TRANSACTION-FAILED' then
      row.transition_source=getd(value,'transition_source','unknown');row.manual=not isnone(value.manual_request_id)
      row.blockers=canon.array(not isnone(value.failure_code) and {value.failure_code} or {})
    end
    T.publish(env,row)
  end
end

function M.rollback_counted(env,value,reason)
  local ok,err=pcall(M.rollback,env,value,reason)
  if ok then return err end
  value.rollback_failures=(num(getd(value,'rollback_failures',0)) or 0)+1
  value.rollback_package=M.recovery_package(env)
  pcall(T.journal_write,env,value)
  error(err,0)
end

-- give_up(): VPN-only guard, Auto stopped (not restartable by itself), alarm published until the operator
-- closes the journal or the daemon is stopped.
function M.give_up(env,value,code)
  local guard='VPN-only; IPv6 forwarded traffic blocked'
  local ok=pcall(function() env.backend.guard(env.backend.devices()) end)
  if not ok then guard='VPN-only guard could not be confirmed' end
  local tok,trial=pcall(function() return env.backend.policy().settings.native_trial end)
  if not tok or isnone(trial) or trial=='' then trial=getd(value,'trial_nonce',NULL) end
  pcall(ctl.stop_latch,env,trial)
  local blockers={code}
  if not env.backend.clear_native_options() then blockers[#blockers+1]='AUTO-OPTIONS-NOT-CLEARED' end
  local state={state='BLOCKED',blockers=canon.array(blockers),alarm=code,original_restored=false,source=getd(value,'source',NULL),target=getd(value,'target',NULL),guard=guard}
  while true do
    local pok=pcall(T.publish,env,state)
    if not pok then ctl.write_json(env.run,T.paths(env).state,merge(state,{history_error='HISTORY-001',time=fwall(env)})) end
    if env.stop() then return end
    local jok,current=pcall(T.journal_read,env)
    if jok and next(current)==nil then return end
    env.sleep(10)
  end
end

return M
