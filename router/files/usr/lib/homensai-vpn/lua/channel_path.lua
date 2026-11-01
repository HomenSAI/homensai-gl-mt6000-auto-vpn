-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- channel_path.lua: channel_path.public_status() for the Lua monitor's status reply (plan item 4), so the page's
-- "active channel" no longer needs status_bridge.py (a Python process while the page is open).
--
-- Same decisions and fields as channel_path.py: snapshot() (legacy confirmed transaction), pair_snapshot()
-- (continuous pair: session RUNNING, fresh monitor and supervisor, no transition/blockers, configured roles, live
-- policy order matching the session, kernel proof), public_status() with the same fail-safe projection on any
-- doubt. from_kernel/cached_projection/empty_snapshot are monitor_status.lua's ports.
--
-- One deliberate difference, the kernel proof: Python's display path re-used its own 15 s kernel attestation
-- (pair_manual.attested: iptables-save + ip rule, ~5 s of CPU on the MT3000). Here the proof is the supervisor's
-- own attestation of this session, published in native-status.json (channel_path, written from the
-- kernel_proof of every OBSERVING/COMMITTED pass): it counts only when it is confirmed, not transitioning, for the
-- same source/target, and at most 15 s old - the same freshness as Python's cache. The supervisor attests exactly
-- the policy hash and order of the session (pair tick: state_order_matches + attest_policy(selection)); the live
-- order is still re-read here and must match the session (state_order_matches) and select the same role.
-- A green channel therefore needs a fresh positive kernel proof, as before; without one the field says
-- KERNEL-POLICY-UNVERIFIED.
local canon=require('canon')
local page=require('monitor_status')

local M={}
local NULL=canon.null
M.MODE='router-probed-ipv4'
local TRANSITIONING={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true}

local function none(v) return v==nil or v==NULL end
local function num(v) return canon.number(v) end
local function finite(v) local x=num(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function fresh(v,now,age) return finite(v) and -5<=now-num(v) and now-num(v)<=age end
local function truthy(v)
  if none(v) or v==false or v=='' then return false end
  local n=num(v);if n~=nil then return n~=0 end
  if type(v)=='table' then return next(v)~=nil end
  return true
end
local function nonempty(v) return type(v)=='string' and v~='' end
local function same_list(a,b)
  if not canon.is_array(a) or not canon.is_array(b) or #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i] then return false end end
  return true
end
local function pair_policy() return require('pair').policy end

M.from_kernel=page.from_kernel
M.cached_projection=page.cached_projection

-- channel_path.snapshot(status, journal, live_order): live = {order, hash} or nil
function M.snapshot(status,journal,live,now)
  local result=page.empty_snapshot(now)
  if not canon.is_object(status) or not canon.is_object(journal) then return result end
  local source,target=journal.source,journal.target
  if not nonempty(source) or not nonempty(target) or source==target then return result end
  result.source_profile_id=source;result.target_profile_id=target
  local controller=status.native_failover
  if controller==nil then controller=canon.object() end
  if truthy(status.rpc_error) or not fresh(status.time,now,90) or not canon.is_object(controller) or not fresh(controller.time,now,30) then return result end
  local phase=journal.phase
  if not none(controller.tx) and controller.tx~=journal.tx then return result end
  if TRANSITIONING[phase] then
    if controller.state~=phase then return result end
    result.transitioning=true
    return result
  end
  if phase~='COMMITTED' and phase~='HELD-ON-RESERVE' and phase~='ROLLED-BACK' then return result end
  if not fresh(journal.confirmed,now,14400) then return result end
  local P=pair_policy()
  local ok,context=pcall(P.metadata,journal)
  if not ok then return result end
  local side,expected
  if context~=nil then
    local rok,role=pcall(P.current_role,journal)
    if not rok then return result end
    side=role;expected=P.current_order(journal)
  else
    side=phase=='ROLLED-BACK' and 'source' or 'target'
    expected=journal[side=='source' and 'before' or 'after']
  end
  if not live or not same_list(live[1],expected) or live[2]~=journal.hash then return result end
  local profiles=status.profiles
  if profiles==nil then profiles=canon.array() end
  if not canon.is_array(profiles) then return result end
  local row=nil
  for _,p in ipairs(profiles) do if canon.is_object(p) and p.id==journal[side] then row=p;break end end
  local proofs=journal.vendor_profiles
  local proof=canon.is_object(proofs) and proofs[side] or nil
  if not row or not canon.is_object(proof) or not fresh(row.time,now,90) then return result end
  local identity=require('identity')
  local measured=identity.profile_identity(row)
  if next(proof)==nil or measured==nil or canon.encode(measured)~=canon.encode(proof) then return result end
  result.confirmed=true;result.active_profile_id=journal[side]
  return result
end

-- channel_path.pair_snapshot(status, state, journal, live_order, kernel)
function M.pair_snapshot(status,state,journal,live,now,kernel)
  local result=page.from_kernel(nil,nil,nil,now)
  result.scope='verified live router policy selection; Internet health is separate'
  local native=status.native_failover
  if native==nil then native=canon.object() end
  if state.phase~='RUNNING' or truthy(status.rpc_error) or not fresh(status.time,now,90) or not canon.is_object(native)
     or not fresh(native.time,now,30) then return result end
  local source,target=native.source,native.target
  if not nonempty(source) or not nonempty(target) or source==target then return result end
  result.source_profile_id=source;result.target_profile_id=target
  result.transitioning=TRANSITIONING[native.state]==true
  if result.transitioning or native.state=='BLOCKED' or truthy(native.blockers) then return result end
  local identity=state.policy_roles
  if none(identity) then return result end
  local P=pair_policy()
  local ok,out=pcall(function()
    if identity.source_id~=source or identity.target_id~=target or not P.state_order_matches(state,journal,live[1],live[2]) then return result end
    local selected=P.role(identity,live[1])
    local configured=identity[selected..'_id']
    result.configured_profile_id=configured
    if not canon.is_object(kernel) or kernel.verified~=true or not fresh(kernel.time,now,15) or kernel.role~=selected
       or kernel.profile_id~=configured or kernel.policy_hash~=state.policy_hash or not same_list(kernel.order,live[1]) then
      result.kernel_policy_verified=false;result.code='KERNEL-POLICY-UNVERIFIED'
      return result
    end
    for k,v in pairs(page.from_kernel(kernel,source,target,now)) do result[k]=v end
    return result
  end)
  if ok then return out end
  return result
end

-- The supervisor's own kernel proof of this session (see the header), in pair_manual.attested()'s shape.
function M.supervisor_kernel(native,state,live)
  if not canon.is_object(native) then return nil end
  local path=native.channel_path
  if not canon.is_object(path) or path.mode~='continuous-pair' or path.selection_proof~='fw3-kernel-marking'
     or path.confirmed~=true or path.kernel_policy_verified~=true or path.transitioning==true
     or path.source_profile_id~=native.source or path.target_profile_id~=native.target then return nil end
  local active=path.active_profile_id
  local role=(active==native.source and 'source') or (active==native.target and 'target') or nil
  if not role or not finite(path.checked_at) then return nil end
  -- the attested policy is the session's (the supervisor checks state_order_matches before attest_policy)
  return canon.object({verified=true,time=path.checked_at,role=role,profile_id=active,policy_hash=state.policy_hash,order=live[1]})
end

-- The same proof for the manual buttons (page_controls.lua, pair_manual.controls' kernel): counted only under the
-- rule the page's channel_path applies (fresh within 15 s, the role the live order selects for this session), so
-- the buttons and the active channel always rest on one reading. nil = no verified kernel proof.
function M.page_kernel(native,state,live,now)
  local kernel=M.supervisor_kernel(native,state,live)
  if not kernel or not fresh(kernel.time,now,15) then return nil end
  local identity=state.policy_roles
  if none(identity) then return nil end
  local ok,selected=pcall(pair_policy().role,identity,live[1])
  if not ok or selected~=kernel.role then return nil end
  return kernel
end

-- channel_path.public_status(status). deps: journal() -> journal (raises), state() -> pair state (raises),
-- order(process_bindings) -> order, hash (raises).
function M.public_status(deps,status,now)
  local native=canon.is_object(status) and status.native_failover or nil
  if not canon.is_object(native) then native=canon.object() end
  local required=native.mode=='continuous-pair' or native.proof_scope==M.MODE
  local ok,result=pcall(function()
    local journal=deps.journal()
    required=required or not none(journal.pair_transition) or journal.proof_scope==M.MODE
    local state=deps.state()
    local pair_mode=not none(state.policy_roles) or not none(journal.pair_transition) or journal.proof_scope==M.MODE
      or native.mode=='continuous-pair'
    if pair_mode then
      if native.state=='BLOCKED' or truthy(native.blockers) then return page.from_kernel(nil,native.source,native.target,now) end
      local bindings=require('identity').validate(state.process_bindings)  -- use_process_bindings: POLICY-IDENTITY-CHANGED
      local order,hash=deps.order(bindings)
      local live={order,hash}
      local kernel=nil
      if state.phase=='RUNNING' then kernel=M.supervisor_kernel(native,state,live) end
      return M.pair_snapshot(status,state,journal,live,now,kernel)
    end
    local live=nil
    if next(journal)~=nil then local order,hash=deps.order(nil);live={order,hash} end
    return M.snapshot(status,journal,live,now)
  end)
  if ok then return result end
  if required then return page.from_kernel(nil,native.source,native.target,now) end
  return page.empty_snapshot(now)
end

return M
