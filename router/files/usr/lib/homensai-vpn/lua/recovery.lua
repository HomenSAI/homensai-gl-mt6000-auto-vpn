-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- recovery.lua: rollback_recovery.py and activation_recovery.finalize for the Lua supervisor (2.0.0-lua line).
-- env.deps.rollback_recovery (the helper table rollback.lua calls) and env.deps.activation_finalize.
--
-- Resume only our proven, unchanged pre-RTP rollback graph: a recorded full mangle/rule fingerprint, the
-- current tunnel bindings and the stopped owning session must all agree before any retry is dispatched. The
-- recorded restore step is persisted before its UCI write, never inferred afterwards.
-- Difference of form only: Python's record_step() sees the command line (`uci reorder route_policy.<s>=<i>` /
-- `uci commit route_policy`); here backend.reorder passes the same facts as detail {op,section,index}.
local canon=require('canon')
local ctl=require('auto_control')
local py=require('py')
local identity=require('identity')
local attest=require('attest')
local platform=require('platform')

local M={}
local NULL=canon.null
local isnone,eq=py.isnone,py.eq
local refuse=ctl.refuse
local function value_error(code) identity.value_error(code) end
local function get(t,k) local v=t[k];if v==NULL then return nil end;return v end
local function has(t,k) return t[k]~=nil end
local function same_list(a,b)
  if type(a)~='table' or type(b)~='table' or #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i] then return false end end
  return true
end
local function copy_list(a) local out={};for i=1,#a do out[i]=a[i] end;return canon.array(out) end
local function hex64(v) return type(v)=='string' and #v==64 and string.find(v,'^[a-f0-9]+$')~=nil end

M.VENDOR_LOCK='/tmp/run/rtp2.lock'
M.RECOVERY_RTP_TIMEOUT=90
M.STABLE_PROFILE={'id','protocol','interface','vendor_tunnel_id'}
M.SETTLE_SECONDS=90;M.SETTLE_POLL=3
M.VENDOR_SETTLE_SECONDS=60;M.VENDOR_SETTLE_POLL=3

-- order_steps(): the minimal left-to-right UCI moves of Linux.reorder()
function M.order_steps(before,target)
  if not canon.is_array(before) or not canon.is_array(target) or #before<2 or #before>400 or #before~=#target then value_error('JOURNAL-INTEGRITY-FAILED') end
  local set,tset={},{}
  for _,x in ipairs(before) do if type(x)~='string' or set[x] then value_error('JOURNAL-INTEGRITY-FAILED') end;set[x]=true end
  for _,x in ipairs(target) do if type(x)~='string' or not set[x] then value_error('JOURNAL-INTEGRITY-FAILED') end;tset[x]=true end
  for x in pairs(set) do if not tset[x] then value_error('JOURNAL-INTEGRITY-FAILED') end end
  local current=copy_list(before)
  local steps={}
  for index,identifier in ipairs(target) do
    if current[index]~=identifier then
      local previous=copy_list(current)
      for i=#current,1,-1 do if current[i]==identifier then table.remove(current,i) end end
      table.insert(current,index,identifier)
      steps[#steps+1]=canon.object({version=1,kind='reorder',before=previous,after=copy_list(current),section=identifier,index=index-1})
    end
  end
  return steps
end

function M.restore_origin(journal)
  if not has(journal,'restore_proof_source') and not has(journal,'restore_order_origin') then return get(journal,'restore_before_order') end
  local source=get(journal,'restore_proof_source')
  local origins={get(journal,'after')}
  if source=='vendor-rebuild' then
    local detail=get(journal,'failure_detail')
    if not canon.is_object(detail) or detail.worker_stage~='rtp-dispatch' then value_error('JOURNAL-INTEGRITY-FAILED') end
    origins[#origins+1]=get(journal,'before')
  elseif source~='forward' then value_error('JOURNAL-INTEGRITY-FAILED') end
  local origin=get(journal,'restore_order_origin')
  local known=false
  for _,o in ipairs(origins) do if eq(origin,o) then known=true end end
  if not known or not eq(get(journal,'restore_before_order'),get(journal,'before')) or not eq(get(journal,'restore_target_order'),get(journal,'before'))
     or eq(get(journal,'before'),get(journal,'after')) or journal.kernel_before_verified~=true or journal.restore_before_verified~=true
     or journal.rtp_dispatched~=true or journal.forward_policy_touched~=true or not isnone(journal.confirmed) or not isnone(journal.kernel_confirmed)
     or not has(journal,'restore_order_step') or not eq(get(journal,'restore_kernel_fingerprint'),get(journal,'kernel_before_fingerprint')) then
    value_error('JOURNAL-INTEGRITY-FAILED')
  end
  return journal.restore_order_origin
end

-- validate_step(): a new checkpoint grants only one canonical before/after transition
function M.validate_step(journal)
  local before=M.restore_origin(journal);local target=get(journal,'restore_target_order')
  if not has(journal,'restore_order_step') then return nil end
  local step=journal.restore_order_step
  local phase=journal.phase
  local rb=get(journal,'restore_before_order')
  if not canon.is_object(step) or not py.is_int(step.version) or step.version~=1
     or not (phase=='RESTORING' or phase=='ROLLED-BACK' or phase=='RELEASE-PENDING') or journal.restore_before_verified~=true
     or not hex64(get(journal,'restore_kernel_fingerprint'))
     or not (eq(rb,get(journal,'before')) or eq(rb,get(journal,'after')) or eq(rb,get(journal,'restored_order'))) then
    value_error('JOURNAL-INTEGRITY-FAILED')
  end
  local moves=M.order_steps(before,target)
  local commit=canon.object({version=1,kind='commit',before=target,after=target})
  if eq(step,commit) then return step end
  if py.is_int(step.index) then for _,expected in ipairs(moves) do if eq(step,expected) then return step end end end
  value_error('JOURNAL-INTEGRITY-FAILED')
end

function M.order_allowed(journal,order)
  local step=M.validate_step(journal)
  if step~=nil then return eq(order,step.before) or eq(order,step.after) end
  return eq(order,get(journal,'restore_target_order'))
end

local function T() return require('transaction') end
local function pair() return require('pair') end

-- record_step(): persist a verified pending UCI write before dispatch, never infer a lost step
function M.record_step(env,journal,kind,detail)
  if kind~='uci' or type(detail)~='table' or not (detail.op=='reorder' or detail.op=='commit') then return end
  if journal.restore_before_verified~=true then return end
  if not eq(T().journal_read(env),journal) then refuse('JOURNAL-INTEGRITY-FAILED') end
  local backend=env.backend
  local sections=backend.policy().sections;local bindings=get(journal,'process_bindings')
  local live=identity.policy_order(sections,bindings)
  if identity.policy_hash(sections,bindings)~=journal.hash then refuse('POLICY-IDENTITY-CHANGED') end
  local target=journal.restore_target_order
  local step
  if detail.op=='commit' then
    if not eq(live,target) then refuse('POLICY-IDENTITY-CHANGED') end
    step=canon.object({version=1,kind='commit',before=copy_list(live),after=copy_list(live)})
  else
    local ok,steps=pcall(M.order_steps,M.restore_origin(journal),target)
    if not ok then error(steps,0) end
    for _,row in ipairs(steps) do if eq(row.before,live) then step=row;break end end
    local names={}
    for _,row in ipairs(sections) do names[identity.section_id(row,bindings)]=row['.name'] end
    if step==nil or names[step.section]~=detail.section or step.index~=detail.index then refuse('POLICY-IDENTITY-CHANGED') end
  end
  local function unchanged()
    local o,h=backend.order()
    return eq(T().journal_read(env),journal) and same_list(o,live) and h==journal.hash
  end
  if not unchanged() then refuse('POLICY-IDENTITY-CHANGED') end
  journal.restore_order_step=step
  T().journal_write(env,journal)
  if not unchanged() then refuse('POLICY-IDENTITY-CHANGED') end
end

function M.forward_proof(journal)
  local phase=journal.phase
  if not ((phase=='APPLYING' or phase=='WAIT-CLIENT') and journal.rtp_dispatched==true and journal.forward_policy_touched==true
     and journal.kernel_before_verified==true and isnone(journal.confirmed) and isnone(journal.kernel_confirmed)
     and not eq(get(journal,'before'),get(journal,'after'))) then return false end
  for key in pairs(journal) do if string.sub(key,1,7)=='restore' then return false end end
  return true
end

local function revision_marker(env)
  local row=ctl.read_json_safe(env.run,env.runtime..'/auto-control-revision.json',canon.object({}))
  return canon.is_object(row) and get(row,'revision') or nil
end
local function roles_of(context)
  local out=canon.object({})
  for _,key in ipairs({'source_rule','target_rule','direction','generic_rules','source_id','target_id'}) do out[key]=context[key] end
  return out
end
local function session_matches(state,requested,revision,journal,context)
  return requested.mode=='off' and eq(requested.revision,revision)
    and (state.phase=='RUNNING' or state.phase=='HELD' or state.phase=='STOPPING')
    and eq(state.id,get(journal,'trial_nonce')) and eq(state.revision,get(journal,'control_revision'))
    and eq(get(state,'process_bindings'),get(journal,'process_bindings'))
    and eq(state.order,context.session_order) and eq(state.policy_hash,get(journal,'hash'))
    and eq(state.policy_roles,roles_of(context))
end
local function valid_binding(binding)
  return canon.is_object(binding) and isnone(binding.code) and type(binding.device)=='string' and #binding.device>=1 and #binding.device<=15
    and string.find(binding.device,'^[A-Za-z0-9_]+$')~=nil and py.is_int(binding.mark) and binding.mark>0
    and type(binding.table)=='string' and string.find(binding.table,'^%d+$')~=nil and py.is_int(binding.ifindex) and binding.ifindex>0
end
local function observed_identity(env,selection)
  local proof=canon.object({})
  for _,role in ipairs({'source','target'}) do
    proof[role]=canon.object({profile=identity.profile_identity(selection[role]) or NULL,kernel=selection[role].kernel_binding})
  end
  return env.backend.digest and env.backend.digest(proof) or canon.digest(proof)
end

-- authorize(): the full live proof that a recorded restore may be resumed (and the check to repeat)
function M.authorize(env,journal,forward)
  local backend=env.backend
  local P=pair().policy
  local function deny() refuse('KERNEL-POLICY-UNVERIFIED') end
  local fingerprint=get(journal,forward and 'kernel_before_fingerprint' or 'restore_kernel_fingerprint')
  local context=P.metadata(journal)
  if context==nil or not hex64(fingerprint) then deny() end
  if forward then
    if not M.forward_proof(journal) then deny() end
  elseif journal.phase~='RESTORING' or journal.restore_before_verified~=true or isnone(journal.restore_target_order) or isnone(journal.restore_before_order) then deny() end
  local revision=revision_marker(env)
  T().require_control_revision(env,revision)
  local state=pair().read_state(env);local requested=pair().intent(env)
  if not session_matches(state,requested,revision,journal,context) then deny() end
  local function check()
    T().require_control_revision(env,revision)
    if not eq(pair().intent(env),requested) or not eq(pair().read_state(env),state) or not eq(T().journal_read(env),journal) or backend.guard_exists()~=true then deny() end
    local managed=pair().state_interfaces(state)
    if env.net.identity(env.net.network(),managed)~=state.network_identity or env.net.changed(state,env.net.configs(managed)) then deny() end
    local blockers,selection=backend.diagnostic()
    if #blockers>0 or not canon.is_object(selection) or not eq(P.proof(selection),state.policy_roles) or selection.hash~=journal.hash
       or not eq(get(selection,'vendor_identity'),get(journal,'vendor_identity')) or not eq(get(selection,'process_bindings'),get(journal,'process_bindings')) then deny() end
    local profiles=get(journal,'vendor_profiles') or canon.object({})
    for _,role in ipairs({'source','target'}) do
      local current=selection[role] or canon.object({})
      local id=identity.profile_identity(current)
      if id==nil or not eq(id,canon.is_object(profiles) and profiles[role] or nil) then deny() end
      if not valid_binding(current.kernel_binding) then deny() end
    end
    if observed_identity(env,selection)~=journal.vendor_identity then deny() end
    local lo,lh=backend.order()
    local allowed
    if forward then allowed=eq(lo,journal.after) else allowed=M.order_allowed(journal,lo) end
    if not same_list(lo,selection.order) or lh~=journal.hash or not allowed or backend.kernel_fingerprint()~=fingerprint then deny() end
    T().require_control_revision(env,revision)
    local lo2,lh2=backend.order()
    if not eq(pair().intent(env),requested) or not eq(pair().read_state(env),state) or not eq(T().journal_read(env),journal)
       or not same_list(lo2,lo) or lh2~=lh or backend.guard_exists()~=true then deny() end
  end
  check()
  return check,revision
end

local function replace(journal,value)
  for k in pairs(journal) do journal[k]=nil end
  for k,v in pairs(value) do journal[k]=v end
end

-- promote_forward(): reuse an existing full forward proof only after Stop, never infer one
function M.promote_forward(env,journal,target)
  if not eq(target,journal.before) then refuse('KERNEL-POLICY-UNVERIFIED') end
  local check,revision=M.authorize(env,journal,true)
  local state=pair().read_state(env);local requested=pair().intent(env)
  local pending=py.copy(journal)
  pending.phase='RESTORING';pending.restore_proof_source='forward';pending.restore_order_origin=copy_list(journal.after)
  pending.restore_before_order=copy_list(journal.before);pending.restore_before_verified=true;pending.restore_target_order=copy_list(target)
  pending.restore_kernel_fingerprint=journal.kernel_before_fingerprint
  local steps=M.order_steps(pending.restore_order_origin,target)
  if #steps==0 then refuse('JOURNAL-INTEGRITY-FAILED') end
  pending.restore_order_step=steps[1]
  check()
  env.run.lock(function()
    T().require_control_revision(env,revision)
    if not eq(T().journal_read(env),journal) or not eq(pair().read_state(env),state) or not eq(pair().intent(env),requested) then refuse('JOURNAL-INTEGRITY-FAILED') end
    T().journal_write(env,pending)
    if not eq(T().journal_read(env),pending) then refuse('JOURNAL-INTEGRITY-FAILED') end
  end,env.runtime)
  replace(journal,pending)
  return M.authorize(env,journal,false)
end

------------------------------------------------------------------------------------------------------
-- own interrupted vendor rebuild (rtp2.sh died inside our transaction)
------------------------------------------------------------------------------------------------------
function M.interrupted_vendor_rtp(journal)
  local detail=get(journal,'failure_detail')
  return journal.phase=='APPLYING' and M.forward_proof(journal) and canon.is_object(detail) and detail.worker_stage=='rtp-dispatch'
end
function M.unrouted_kernel(env)
  local sys=env.backend.sys
  local ok,result=pcall(function()
    local text=sys.command({'iptables-save','-t','mangle'},{timeout=5})
    if not canon.valid_utf8(text) then return false end
    return attest.unrouted(text)
  end)
  return ok and result==true
end
function M.vendor_rebuild_applies(env,journal)
  if journal.phase=='RESTORING' and get(journal,'restore_proof_source')=='vendor-rebuild' then return true end
  return M.interrupted_vendor_rtp(journal) and env.backend.kernel_fingerprint()~=get(journal,'kernel_before_fingerprint') and M.unrouted_kernel(env)
end

-- settled(): diagnostic(), waiting a bounded time while it is only not ready yet (nothing is written)
function M.settled(env)
  local until_=env.run.clock()+M.SETTLE_SECONDS
  while true do
    local blockers,current=env.backend.diagnostic()
    if (#blockers==0 and canon.is_object(current)) or env.run.clock()>=until_ or env.stop() then return blockers,current end
    env.sleep(M.SETTLE_POLL)
  end
end
-- vendor_settled(): MT3000 only - wait (bounded) for quiet GL workers and a stable kernel graph
function M.vendor_settled(env)
  local backend=env.backend
  if not backend.detect or backend.detect()~='mt3000' then return end
  local until_=env.run.clock()+M.VENDOR_SETTLE_SECONDS
  pcall(platform.wait_quiet,backend.sys,math.min(30,math.max(1,until_-env.run.clock())))
  local previous=nil
  while env.run.clock()<until_ and not env.stop() do
    local ok,current=pcall(backend.kernel_fingerprint)
    if not ok then current=nil end
    if current~=nil and current==previous then return end
    previous=current;env.sleep(M.VENDOR_SETTLE_POLL)
  end
end

function M.rebuild(env,journal,reason,target)
  local backend,sys=env.backend,env.backend.sys
  local P=pair().policy
  local function deny(code) refuse(code or 'KERNEL-POLICY-UNVERIFIED') end
  local context=P.metadata(journal)
  if context==nil or not eq(target,journal.before) then deny() end
  if journal.phase=='RESTORING' then
    if get(journal,'restore_proof_source')~='vendor-rebuild' then deny() end
    if not pcall(M.validate_step,journal) then deny('JOURNAL-INTEGRITY-FAILED') end
  elseif not M.interrupted_vendor_rtp(journal) then deny() end
  local pid=get(journal,'pid')
  if pid~=nil and py.is_int(pid) then
    local command=sys.read('/proc/'..string.format('%d',pid)..'/cmdline')
    if command and type(journal.tx)=='string' and string.find(command,'native_switch.py\0apply\0'..journal.tx,1,true) then deny('VENDOR-WORKER-BUSY') end
  end
  local revision=revision_marker(env)
  T().require_control_revision(env,revision)
  local state=pair().read_state(env);local requested=pair().intent(env)
  if not session_matches(state,requested,revision,journal,context) then deny() end
  local managed=pair().state_interfaces(state)
  local lock,kernel_seen=nil,nil
  local net=env.net

  local function pending(final)
    local text=sys.command({'uci','-q','changes'},{timeout=10})
    local lines={}
    for line in string.gmatch(require('kernel').decode(text),'[^\n]+') do if string.find(line,'%S') then lines[#lines+1]=line end end
    local step=get(journal,'restore_order_step') or canon.object({})
    local owned=step.kind=='reorder' or (step.kind=='commit' and not eq(get(journal,'restore_order_origin'),get(journal,'restore_target_order')))
    if #lines>0 then
      local foreign=false
      for _,x in ipairs(lines) do if string.sub(x,1,13)~='route_policy.' then foreign=true end end
      if final or not owned or foreign then deny('PAIR-EXTERNAL-CONFIG-CHANGE') end
    end
  end
  local function configuration(final)
    if net.identity(net.network(),managed)~=state.network_identity then deny('PAIR-EXTERNAL-NETWORK-CHANGE') end
    local observed=net.configs(managed)
    if net.changed(state,observed,{firewall=true}) then deny('PAIR-EXTERNAL-CONFIG-CHANGE') end
    if not net.changed(state,observed) then return end
    local static=canon.is_object(state.protected_static) and get(state.protected_static,'firewall') or nil
    if final or (static~=nil and net.static_firewall_digest(net.firewall_bytes())~=static) then deny('PAIR-EXTERNAL-CONFIG-CHANGE') end
  end
  local function selection()
    local ok,value=pcall(platform.vendor_lock_pid,sys)
    if not ok then deny('VENDOR-WORKER-BUSY') end
    lock=value
    platform.ALLOWED_STALE_LOCK=lock
    local sok,blockers,current=pcall(M.settled,env)
    platform.ALLOWED_STALE_LOCK=nil
    if not sok then error(blockers,0) end
    if #blockers>0 or not canon.is_object(current) or not eq(P.proof(current),state.policy_roles) or current.hash~=journal.hash
       or not eq(get(current,'process_bindings'),get(journal,'process_bindings')) then deny() end
    local recorded=get(journal,'vendor_profiles') or canon.object({})
    local same_epoch=true
    for _,key in ipairs({'source','target'}) do
      local row=current[key] or canon.object({})
      local live=identity.profile_identity(row)
      local rec=canon.is_object(recorded) and recorded[key] or nil
      if live==nil or not canon.is_object(rec) then deny() end
      for _,field in ipairs(M.STABLE_PROFILE) do if not eq(live[field],rec[field]) then deny() end end
      same_epoch=same_epoch and eq(live,rec)
      if not valid_binding(row.kernel_binding) then deny() end
    end
    if same_epoch and (not eq(get(current,'vendor_identity'),get(journal,'vendor_identity')) or observed_identity(env,current)~=journal.vendor_identity) then deny() end
    return current
  end
  local function check()
    T().require_control_revision(env,revision)
    if not eq(pair().intent(env),requested) or not eq(pair().read_state(env),state) or not eq(T().journal_read(env),journal) or backend.guard_exists()~=true then deny() end
    pending(false);configuration(false)
    local current=selection()
    local lo,lh=backend.order()
    local allowed
    if journal.phase=='RESTORING' then allowed=M.order_allowed(journal,lo) else allowed=eq(lo,journal.after) or eq(lo,journal.before) end
    local fingerprint=backend.kernel_fingerprint()
    if not same_list(lo,current.order) or lh~=journal.hash or not allowed or type(fingerprint)~='string' then deny() end
    if journal.restore_rtp_dispatched~=true then
      if not M.unrouted_kernel(env) then deny() end
      if kernel_seen==nil then kernel_seen=fingerprint elseif fingerprint~=kernel_seen then deny() end
    end
    T().require_control_revision(env,revision)
    local lo2,lh2=backend.order()
    if not eq(pair().intent(env),requested) or not eq(pair().read_state(env),state) or not eq(T().journal_read(env),journal)
       or not same_list(lo2,lo) or lh2~=lh or backend.guard_exists()~=true then deny() end
    return lo
  end

  local live=check()
  if journal.phase=='APPLYING' then
    local updated=py.copy(journal)
    updated.phase='RESTORING';updated.restore_proof_source='vendor-rebuild';updated.restore_order_origin=copy_list(live)
    updated.restore_before_order=copy_list(journal.before);updated.restore_before_verified=true;updated.restore_target_order=copy_list(target)
    updated.restore_kernel_fingerprint=journal.kernel_before_fingerprint
    local steps=M.order_steps(live,target)
    updated.restore_order_step=steps[1] or canon.object({version=1,kind='commit',before=copy_list(target),after=copy_list(target)})
    env.run.lock(function()
      T().require_control_revision(env,revision)
      if not eq(T().journal_read(env),journal) or not eq(pair().read_state(env),state) or not eq(pair().intent(env),requested) then deny('JOURNAL-INTEGRITY-FAILED') end
      T().journal_write(env,updated)
      if not eq(T().journal_read(env),updated) then deny('JOURNAL-INTEGRITY-FAILED') end
    end,env.runtime)
    replace(journal,updated)
    T().publish(env,T().merge(T().pair_event_fields(journal,{restoring=true,restore_order=target}),{state='RESTORING',reason=reason,
      source=journal.source,target=journal.target,proof_scope=get(journal,'proof_scope') or 'router-probed-ipv4'}))
  end

  local function write(kind,fn,detail)
    check()
    M.record_step(env,journal,kind,detail)
    check()
    local timeout=nil
    if kind=='rtp' then
      if lock~=nil then
        local ok,pid=pcall(platform.vendor_lock_pid,sys)
        if not ok or pid~=lock then deny('VENDOR-WORKER-BUSY') end
        sys.remove(M.VENDOR_LOCK)
      end
      journal.restore_rtp_dispatched=true;T().journal_write(env,journal)
      timeout=M.RECOVERY_RTP_TIMEOUT
    elseif kind=='kernel' then
      journal.restore_rtp_dispatched=true;T().journal_write(env,journal)
    end
    local result=env.run.fenced(revision,function() return fn(timeout) end)
    if type(result)=='function' then result=result() end
    return result
  end

  local step=get(journal,'restore_order_step') or canon.object({})
  if not same_list(live,target) then backend.reorder(target,nil,write)
  elseif step.kind=='reorder' then write('uci',function() backend.uci_commit() end,{op='commit'}) end
  backend.apply(write)

  local function failed(code)
    pcall(function() backend.guard(backend.devices()) end)
    deny(code or 'ROLLBACK-UNVERIFIED')
  end
  local lo,lh=backend.order()
  if not same_list(lo,target) or lh~=journal.hash then failed() end
  local blockers,current=M.settled(env)
  local kernel_proof=(#blockers==0 and current) and backend.attest_policy(current) or canon.object({})
  if kernel_proof.verified~=true or kernel_proof.role~=P.role(context,target) then failed() end
  if backend.guard_exists()~=true then failed() end
  local fok,ferr=pcall(function() pending(true);configuration(true) end)
  if not fok then
    if type(ferr)=='table' and type(ferr.code)=='string' and not ferr.value_error then failed(ferr.code) end
    error(ferr,0)
  end
  T().require_control_revision(env,revision)
  if not eq(pair().intent(env),requested) or not eq(pair().read_state(env),state) then failed('CLIENT-STOP') end
  journal.phase='ROLLED-BACK';journal.reason=reason;journal.finished=canon.float(env.run.wall());journal.restored_order=copy_list(target)
  T().journal_write(env,journal)
  backend.guard(backend.devices())
  local fields=T().pair_event_fields(journal,{completed=true,outcome='restored',restoring=true})
  local restoring=reason=='PAIR-STOPPED' or reason=='SERVICE-STOPPED' or reason=='SUPERVISOR-RECOVERY'
  T().publish(env,T().merge(fields,{state=restoring and 'RESTORING' or 'ROLLED-BACK',reason=reason,source=journal.source,target=journal.target,
    proof_scope=get(journal,'proof_scope') or 'router-probed-ipv4',kernel_proof=kernel_proof,original_restored=eq(target,context.session_order),vendor_rebuild=true}))
end

-- the helper table rollback.lua calls (signatures of rollback.lua)
function M.helpers()
  return {
    vendor_rebuild_applies=M.vendor_rebuild_applies,
    rebuild=M.rebuild,
    vendor_settled=M.vendor_settled,
    order_allowed=M.order_allowed,
    promote_forward=M.promote_forward,
    authorize=function(env,value) return M.authorize(env,value,false) end,
    record_step=M.record_step,
    settled=M.settled,
  }
end

------------------------------------------------------------------------------------------------------
-- activation_recovery.finalize: close only an inactive failed, no-order-change activation at its exact old
-- missing baseline; the original journal is archived and read back first. No route/kernel/flag write.
------------------------------------------------------------------------------------------------------
M.ACTIVATION_PINS={['/etc/init.d/vpn-client']='3b751f0691202bc930b8113d7b55d0a38003369c015c672d0797723f1aa79e9a',
  ['/usr/bin/rtp2.sh']='d6863630241e0bc68f56cc1eb8ccca45006083c1166e742e8500b28b5e2a544e'}
local function recovery_required() refuse('PAIR-RECOVERY-REQUIRED') end

local function platform_checked(sys)
  for _,pair_ in ipairs({{'/tmp/sysinfo/board_name','glinet,mt3000-snand'},{'/etc/glversion','4.11.0'}}) do
    local st=sys.lstat(pair_[1])
    if not st or st.type~='reg' or st.size>128 then recovery_required() end
    local text=sys.read(pair_[1],128)
    if not text or string.match(text,'^%s*(.-)%s*$')~=pair_[2] then recovery_required() end
  end
  for name,sha in pairs(M.ACTIVATION_PINS) do
    local st=sys.lstat(name)
    if not st or st.type~='reg' or st.size>262144 then recovery_required() end
    local ok,value=pcall(platform.sha_file,sys,name)
    if not ok or value~=sha then recovery_required() end
  end
end

-- auto_control.public_status()['requested'] (the only field finalize reads)
function M.requested_mode(env)
  local valid=true
  local function record(path)
    local ok,row=pcall(ctl.read_json,env.run,path,canon.object({}))
    if not ok or not canon.is_object(row) then valid=false;return canon.object({}) end
    return row
  end
  local function stamp(row,key)
    local v=row[key];if v==nil then v=0 end
    local x=canon.number(v)
    if x==nil or type(v)=='boolean' or not py.finite(v) or x<0 then valid=false;return 0 end
    return x
  end
  local request=record(env.runtime..'/auto-control.json')
  local stopped=record(env.persist..'/native-stop.json')
  local requested,stop=stamp(request,'time'),stamp(stopped,'requested')
  stamp(request,'until')
  local mode=request.mode;if mode==nil then mode='off' end
  if mode~='on' and mode~='off' then valid=false end
  if stop>=requested then mode='off' end
  local result=record(env.runtime..'/native-return-result.json')
  if next(result)~=nil then
    stamp(result,'request');stamp(result,'time')
    local code=result.code
    if type(result.ok)~='boolean' or (not isnone(code) and not (type(code)=='string' and ctl.code_ok(code))) then valid=false end
  end
  local rok,revision=pcall(ctl.current_revision,env)
  if not rok then revision=nil end
  if stopped.control_revision_failed==true then revision=nil end
  local pok,intent=pcall(pair().intent,env)
  if pok and next(intent)~=nil and valid and eq(intent.revision,revision) and (canon.number(intent.time) or 0)>stop then mode=intent.mode end
  return valid and mode or 'unknown'
end

local function facts(env,state,journal,allow_stopping)
  local backend,sys=env.backend,env.backend.sys
  platform_checked(sys)
  local requested=pair().intent(env)
  local revision=revision_marker(env)
  if requested.mode~='off' or not eq(requested.revision,revision) or type(revision)~='string' or #revision~=32 or not string.find(revision,'^[a-f0-9]+$') then recovery_required() end
  T().require_control_revision(env,revision)
  if M.requested_mode(env)~='off' then recovery_required() end
  local phases=allow_stopping and {STOPPED=true,FAILED=true,STOPPING=true,HELD=true,RUNNING=true} or {STOPPED=true,FAILED=true}
  if not phases[state.phase] or not (canon.is_array(state.owned) and #state.owned==0) then recovery_required() end
  local manual=require('manual')
  local pending=manual.read(env)
  if next(pending)~=nil and manual.PENDING[pending.state] and pending.revision==revision then recovery_required() end
  local context=pair().policy.metadata(journal)
  local roles=state.policy_roles
  local keys={source_rule=true,target_rule=true,source_id=true,target_id=true,direction=true,generic_rules=true}
  local ok=context~=nil and journal.activation_reapply==true and isnone(journal.manual_request_id) and canon.is_object(roles)
  if ok then
    local n=0
    for k,v in pairs(roles) do n=n+1;if not keys[k] or not eq(context[k],v) then ok=false end end
    if n~=6 then ok=false end
  end
  local phase=journal.phase
  if not ok or not eq(get(state,'process_bindings'),get(journal,'process_bindings'))
     or not (phase=='ARMED' or phase=='APPLYING' or phase=='RESTORING') or not isnone(journal.confirmed) or not isnone(journal.kernel_confirmed)
     or journal.kernel_before_verified~=false or not eq(journal.before,journal.after) or not eq(journal.before,state.order)
     or not eq(context.session_order,state.order) or not eq(journal.hash,state.policy_hash)
     or not eq(journal.restore_before_order==nil and journal.before or journal.restore_before_order,journal.before)
     or not eq(journal.restore_target_order==nil and journal.before or journal.restore_target_order,journal.before) then recovery_required() end
  local pid,tx=get(journal,'pid'),get(journal,'tx')
  if py.is_int(pid) and pid>1 then
    local raw=sys.read('/proc/'..string.format('%d',pid)..'/cmdline',8193)
    if raw~=nil then
      if #raw>8192 or string.sub(raw,-1)~='\0' or string.find(require('kernel').decode(raw),'native_switch.py\0apply\0'..py.str(tx),1,true) then recovery_required() end
    end
  end
  T().bind_policy_context(env,state)
  local lo,lh=backend.order()
  if not same_list(lo,state.order) or lh~=state.policy_hash then recovery_required() end
  local managed=pair().state_interfaces(state)
  if env.net.identity(env.net.network(),managed)~=state.network_identity or env.net.changed(state,env.net.configs(managed)) then recovery_required() end
  local kernel=backend.attest_policy()
  local original=get(journal,'kernel_before_fingerprint')
  if not hex64(original) or kernel.verified~=false or kernel.repairable_missing~=true or kernel.kernel_fingerprint~=original then recovery_required() end
  if not allow_stopping and backend.guard_exists() then recovery_required() end
  return revision
end

function M.finalize(env,state,journal,allow_stopping,check_only)
  local backend,sys=env.backend,env.backend.sys
  state=state or pair().read_state(env)
  journal=journal or T().journal_read(env)
  if journal.phase=='ROLLED-BACK' and journal.failed_activation_unchanged==true then
    return {result='ALREADY_FINALIZED',changed=false,kernel_verified=false}
  end
  local journal_path=T().paths(env).journal
  local _,state_path=pair().paths(env)
  local jst,sst=sys.lstat(journal_path),sys.lstat(state_path)
  if (jst and jst.type=='lnk') or (sst and sst.type=='lnk') then recovery_required() end
  local raw,state_raw=sys.read(journal_path),sys.read(state_path)
  if not raw or not state_raw or #raw>1024*1024 or #state_raw>1024*1024 then recovery_required() end
  local eok,envelope=pcall(canon.decode,raw);local ook,owned=pcall(canon.decode,state_raw)
  if not eok or not ook or not canon.is_object(envelope) or envelope.schema~=1 or not eq(envelope.data,journal) or envelope.sha256~=canon.digest(journal)
     or not canon.is_object(owned) or not eq(owned.data,state) or owned.sha256~=canon.digest(state) then recovery_required() end
  local revision=facts(env,state,journal,allow_stopping)
  pcall(platform.wait_quiet,sys,8)
  facts(env,state,journal,allow_stopping)
  if sys.read(journal_path)~=raw or sys.read(state_path)~=state_raw then recovery_required() end
  local sha=canon.sha256(raw)
  if check_only then return {result='READY_UNCHANGED',changed=false,kernel_verified=false,journal_sha256=sha} end
  local directory=env.persist..'/session-recovery'
  local archive
  env.run.lock(function()
    T().require_control_revision(env,revision)
    if pair().intent(env).mode~='off' or sys.read(journal_path)~=raw or sys.read(state_path)~=state_raw then recovery_required() end
    local dst=sys.lstat_exact(directory)
    if dst and dst.type=='lnk' then recovery_required() end
    if not dst then sys.mkdir(directory,448);dst=sys.lstat_exact(directory) end
    if not dst or dst.type~='dir' or dst.uid~=sys.euid() or dst.mode%64~=0 then recovery_required() end
    archive=directory..'/failed-activation-'..string.sub(string.gsub(sys.unique(),'[^0-9a-f]',''),1,32)..'.json'
    if not sys.create_exclusive(archive,raw) or sys.read(archive)~=raw then recovery_required() end
  end,env.runtime)
  facts(env,state,journal,allow_stopping)
  env.run.lock(function()
    T().require_control_revision(env,revision)
    if pair().intent(env).mode~='off' or sys.read(journal_path)~=raw or sys.read(state_path)~=state_raw or sys.read(archive)~=raw then recovery_required() end
    local resolved=py.copy(journal)
    local now=canon.float(env.run.wall())
    resolved.phase='ROLLED-BACK';resolved.restored_order=copy_list(journal.before);resolved.finished=now
    resolved.failed_activation_unchanged=true;resolved.kernel_policy_verified=false
    resolved.failure_resolution=canon.object({archive=string.match(archive,'[^/]+$'),sha256=sha,old_phase=journal.phase,time=now,kernel_unchanged=true})
    T().journal_write(env,resolved)
    if not eq(T().journal_read(env),resolved) then recovery_required() end
    replace(journal,resolved)
  end,env.runtime)
  return {result='FINALIZED_UNCHANGED',changed=true,archived=true,journal_sha256=sha,kernel_verified=false}
end

return M
