-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- page_controls.lua: the last two page fields status_bridge.py computed for the Lua monitor, now in Lua, so the
-- monitor answers the page without starting Python:
--   manual_switch_control  pair_manual.controls() / manual_control.control_status(), chosen like
--                          agent.status_reply (pair_manual.public_for_status, monitor_status.manual_switch)
--   scan                   scan_control.public()
-- Same fields, values and codes as the Python functions on the same inputs (differential test:
-- tests/test_lua_page_controls.py). Nothing here starts a process: every input is a RAM/flash file the monitor
-- already reads (cached by file key where the monitor caches), the router policy the monitor already holds
-- (native_policy.lua, re-read only when a UCI package changes) and the supervisor's published kernel proof.
--
-- One deliberate difference, the kernel proof of the pair buttons (as in channel_path.lua): Python's
-- pair_manual.attested() ran its own iptables-save/ip rule attestation (~5 s CPU on the MT3000, cached 15 s). Here
-- the proof is the supervisor's own attestation of this session, published in native-status.json, with exactly
-- the rule the page's channel_path uses (channel_path.page_kernel: confirmed, same pair, same live order, at most
-- 15 s old). One source: the buttons and the "active channel" can never disagree about the kernel.
-- No fresh proof -> KERNEL-POLICY-UNVERIFIED, as Python without a verified attestation (never a false "allowed").
--
-- The legacy (non-pair) control_status needs a display diagnostic: deps.diagnostic() (the monitor reuses
-- display-diagnostic.json younger than 15 s exactly like manual_control.display_diagnostic, else runs the Lua
-- backend's diagnostic). When a dependency cannot answer at all it raises M.UNAVAILABLE and the monitor falls
-- back to status_bridge.py for that one answer (never on a timer).
local canon=require('canon')

local M={}
local NULL=canon.null
M.UNAVAILABLE=setmetatable({},{__tostring=function() return 'PAGE-CONTROLS-UNAVAILABLE' end})
M.PENDING={QUEUED=true,CLAIMED=true}
local NATIVE_BUSY={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true}
local QUIET={['ROLLED-BACK']=true,COMMITTED=true,['HELD-ON-RESERVE']=true}

local function none(v) return v==nil or v==NULL end
local function num(v) return canon.number(v) end
local function finite(v) local x=num(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function hex(v,n) return type(v)=='string' and #v==n and string.find(v,'^[a-f0-9]+$')~=nil end
local function is_dict(v) return canon.is_object(v) end
local function get(t,k) if type(t)~='table' or t==NULL then return nil end;local v=t[k];if v==NULL then return nil end;return v end
local function n0(v) if v==nil then return NULL end;return v end
local function truthy(v) return require('py').truthy(v) end
local function eq(a,b) return require('py').eq(a,b) end
local function list(t) return canon.array(t or {}) end
local function copy_list(t) local out={};for i=1,#t do out[i]=t[i] end;return out end
local function contains(t,x) for i=1,#t do if t[i]==x then return true end end;return false end
-- sorted(set(x)) of code strings
local function sorted_set(t)
  local seen,out={},{}
  for _,x in ipairs(t) do if not seen[x] then seen[x]=true;out[#out+1]=x end end
  table.sort(out)
  return out
end
local function unavailable_error(e) return e==M.UNAVAILABLE end

------------------------------------------------------------------------------------------------------
-- scan_control.public(root, read, now)
------------------------------------------------------------------------------------------------------
local SCAN_STATES={QUEUED=true,RUNNING=true,COMPLETED=true,FAILED=true}
local SCAN_FIELDS={'request_id','state','requested_at','started_at','finished_at','code','measurement_request_id','measured_at','checked','failed'}
-- row: the decoded scan.state ({} when missing; the caller lets a read error propagate like agent.read_json)
function M.scan_public(row,now)
  if not is_dict(row) or not hex(row.request_id,32) then return canon.object({state='IDLE'}) end
  local requested=row.requested_at
  if not SCAN_STATES[row.state] or num(requested)==nil or not finite(requested) then
    return canon.object({state='FAILED',code='SCAN-STATE-CORRUPT'})
  end
  local out=canon.object()
  for _,k in ipairs(SCAN_FIELDS) do if row[k]~=nil then out[k]=row[k] end end
  if (out.state=='QUEUED' or out.state=='RUNNING') and (now<num(requested) or now-num(requested)>300) then
    out.state='FAILED';out.code='SCAN-DEADLINE-EXCEEDED'
  end
  return out
end

------------------------------------------------------------------------------------------------------
-- pair_manual.controls()
------------------------------------------------------------------------------------------------------
-- pair_manual.healthy
local function healthy(status,identifier,now,valid_for)
  local profiles=status.profiles
  if profiles==nil then profiles=canon.array() end
  if not canon.is_array(profiles) then return false end
  for _,row in ipairs(profiles) do
    if is_dict(row) and eq(row.id,identifier) then
      local stamp=row.time
      local s=num(stamp)
      if not (s~=nil and finite(stamp) and 0<=now-s and now-s<=valid_for and none(row.code) and row.dns_ok==true) then return false end
      -- row.get('https_success',0)>=2: a bool counts as 0/1, anything else non-numeric is Python's TypeError
      local https=row.https_success;if https==nil then https=0 end
      if type(https)=='boolean' then https=https and 1 or 0
      elseif num(https)==nil then error('TypeError',0) end
      return num(https)>=2
    end
  end
  return false
end
M.healthy=healthy

-- deps (every function may raise; a raise is Python's caught exception unless it is M.UNAVAILABLE):
--   now                         wall clock (float seconds)
--   read_state()                pair-auto-state.json, checked (pair_auto.read_state)
--   intent()                    pair-auto-control.json (pair_auto.intent)
--   current_revision()          auto-control-revision.json (auto_control.current_revision)
--   validate_bindings(b)        process_policy.validate (backend.use_process_bindings)
--   settings()                  backend.policy()['settings']
--   order(bindings)             backend.order() -> order, hash
--   native()                    native-status.json ({} when missing)
--   status()                    status.json (the monitor's published status)
--   journal()                   native_switch.journal_read()
--   queued()                    pair_manual.read() (raises on an invalid row)
--   ledger()                    pair-auto-budget.json ({events=[]} when missing)
--   kernel(state,journal,live)  the kernel proof (pair_manual.attested) -> table
--   fast()                      native_switch.fast_switch_enabled()
function M.pair_controls(d)
  local pair=require('pair')
  local P=pair.policy
  local now=d.now
  local result=canon.object({available=false,mode='continuous-pair',time=canon.float(now)})
  local ok,err=pcall(function()
    local state=d.read_state()
    local revision=d.current_revision()
    local intent=d.intent()
    if not (get(state,'phase')=='RUNNING' and get(intent,'mode')=='on' and eq(get(state,'id'),get(intent,'id'))
            and eq(get(state,'revision'),get(intent,'revision')) and eq(get(intent,'revision'),revision)) then return end
    result.available=true;result.control_revision=n0(revision);result.hold=n0(state.manual_hold)
    local bindings=d.validate_bindings(state.process_bindings)
    local settings=d.settings()
    if settings==nil then error('KeyError',0) end
    local valid_for=pair.valid_for(settings)
    result.observation_valid_for=valid_for
    local native=d.native();local status=d.status();local journal=d.journal();local queued=d.queued()
    if not is_dict(native) or not is_dict(status) then error('PAIR-MANUAL-STATE-UNVERIFIED',0) end
    local t=native.time
    local fresh=num(t)~=nil and 0<=now-num(t) and now-num(t)<=30
    local busy=(is_dict(queued) and next(queued)~=nil and M.PENDING[queued.state]==true) or NATIVE_BUSY[get(native,'state')]==true
    local reasons=busy and {'PAIR-MANUAL-BUSY'} or (not fresh and {'PAIR-MANUAL-STALE'} or {})
    local source,target=native.source,native.target
    local primary,reserve=copy_list(reasons),copy_list(reasons)
    local general=not none(state.policy_roles)
    local phase=get(journal,'phase')
    local live=nil
    local function live_order()
      if not live then local o,h=d.order(bindings);live={o,h} end
      return live
    end
    if general then
      if not (phase==nil or QUIET[phase]) or not P.state_order_matches(state,journal,live_order()[1],live_order()[2]) then
        primary[#primary+1]='TRANSACTION-IN-PROGRESS';reserve[#reserve+1]='TRANSACTION-IN-PROGRESS'
      end
    else
      if phase~='COMMITTED' and phase~='HELD-ON-RESERVE' then primary[#primary+1]='RETURN-NOT-APPLICABLE' end
      if not (phase==nil or phase=='ROLLED-BACK') then reserve[#reserve+1]='TRANSACTION-IN-PROGRESS' end
    end
    if not healthy(status,source,now,valid_for) then primary[#primary+1]='SOURCE-NOT-HEALTHY' end
    if not healthy(status,target,now,valid_for) then reserve[#reserve+1]='PAIR-MANUAL-TARGET-UNHEALTHY' end
    local ledger=d.ledger()
    if not is_dict(ledger) then error('AttributeError',0) end
    local events=ledger.events
    local permitted,policy
    if truthy(events) then
      policy=pair.recovery_normalized(settings)
      events,permitted=pair.budget(events,now,policy.attempt_window*60,policy.attempt_limit)
    else
      events,permitted=pair.budget(events,now)
    end
    local busy_switch=contains(primary,'TRANSACTION-IN-PROGRESS')
    local kernel=canon.object()
    if general and not busy_switch then kernel=d.kernel(state,journal,live_order()) or canon.object() end
    local role=get(kernel,'role')
    local known=(kernel.verified==true and (role=='source' or role=='target')) and role or nil
    if general and not busy_switch and known==nil and kernel.repairable_missing~=true then
      primary[#primary+1]='KERNEL-POLICY-UNVERIFIED';reserve[#reserve+1]='KERNEL-POLICY-UNVERIFIED'
    end
    local fast=general and d.fast()==true
    if fast then
      -- the instant owner switch is never rate limited (pair_manual.consume)
    elseif not permitted then
      if known~='target' then reserve[#reserve+1]='PAIR-RATE-LIMIT' end
      if general and known~='source' then primary[#primary+1]='PAIR-RATE-LIMIT' end
    elseif #events>0 then
      if now-num(events[#events])<math.max(policy.cooldown,policy.min_dwell) then
        if known~='target' then reserve[#reserve+1]='PAIR-MANUAL-COOLDOWN' end
        if general and known~='source' then primary[#primary+1]='PAIR-MANUAL-COOLDOWN' end
      end
    end
    result.instant=fast
    local hold=get(state,'manual_hold')
    result.primary=canon.object({allowed=#primary==0,blockers=list(primary)})
    result.reserve=canon.object({allowed=#reserve==0,blockers=list(reserve)})
    result.resume=canon.object({allowed=#reasons==0 and (hold=='source' or hold=='target'),blockers=list(copy_list(reasons))})
    result.blockers=list(copy_list(reasons))
  end)
  if not ok then
    if unavailable_error(err) then error(err,0) end
    result.available=false;result.blockers=list({'PAIR-MANUAL-STATE-UNVERIFIED'})
  end
  return result
end

------------------------------------------------------------------------------------------------------
-- manual_control.control_status() (the legacy one-shot request outside a pair session)
------------------------------------------------------------------------------------------------------
local LEGACY_PENDING={QUEUED=true,CLAIMED=true,APPLYING=true,['WAIT-CLIENT']=true}

-- native_proof.matches
local PROOF={['external-lan']=true,['router-hosted-ipv4']=true,['router-probed-ipv4']=true}
local function proof_matches(first,second)
  if not is_dict(first) or not is_dict(second) then return false end
  local a=first.proof_scope;if a==nil then a='external-lan' end
  local b=second.proof_scope;if b==nil then b='external-lan' end
  return type(a)=='string' and PROOF[a]==true and a==b
end

local function sub_id(selection,key)
  local row=selection[key]
  if row==nil then return nil end
  if not is_dict(row) then error('AttributeError',0) end
  return row.id
end

-- auto_control.readiness(settings, certificate, consumed, selection, [], now)
function M.readiness(settings,certificate,consumed,selection,now)
  local T=require('transaction')
  local reasons={}
  if not (is_dict(settings) and is_dict(certificate) and is_dict(consumed)) then return {'START-STATE-UNVERIFIED'} end
  local ok,until_=pcall(T.deadline,get(settings,'native_until'))
  if not ok then
    if type(until_)~='table' or type(until_.code)~='string' then error(until_,0) end
    reasons[#reasons+1]=until_.code;until_=0
  end
  if not (now<until_ and until_<=now+14400) then reasons[#reasons+1]='BOUNDED-DEADLINE-REQUIRED' end
  if settings.native_session_loss~='1' then reasons[#reasons+1]='SESSION-LOSS-NOT-ACCEPTED' end
  if not truthy(settings.native_trial) or not eq(consumed.trial,settings.native_trial) then reasons[#reasons+1]='LAN-TRIAL-REQUIRED' end
  local count=consumed.count;if count==nil then count=0 end
  if not (require('py').is_int(count) and 0<=count and count<3) then reasons[#reasons+1]='TRIAL-ATTEMPT-LIMIT' end
  local certified_until=certificate['until'];if certified_until==nil then certified_until=0 end
  local fine=is_dict(selection) and is_dict(selection.source) and is_dict(selection.target)
  if fine then
    fine=eq(certificate.hash,selection.hash) and eq(certificate.source,selection.source.id) and eq(certificate.target,selection.target.id)
      and eq(certificate.direction,selection.direction)
      and (num(certified_until)~=nil and finite(certified_until) and num(certified_until)>=until_)
      and eq(certificate.settings_hash,selection.settings_hash) and proof_matches(certificate,selection)
  end
  if not fine then reasons[#reasons+1]='LAN-TRIAL-REQUIRED' end
  return sorted_set(reasons)
end

-- manual_control._preflight
function M.preflight(direction,settings,blockers,selection,journal,state,auto,stopped,certificate,consumed,now)
  local ctl=require('auto_control')
  local reasons=copy_list(blockers)
  for _,row in ipairs({settings,journal,state,auto,stopped}) do if not is_dict(row) then return {'MANUAL-STATE-UNVERIFIED'} end end
  local mode=get(settings,'monitor_only')
  if mode~=nil and mode~='0' then reasons[#reasons+1]='MONITOR-ONLY-DEPLOYMENT' end
  local t=state.time
  if not (finite(t) and num(t)>0) or not (0<=now-num(t) and now-num(t)<=30) then reasons[#reasons+1]='MANUAL-SUPERVISOR-UNAVAILABLE' end
  if not ctl.valid_stop(stopped) or stopped.control_revision_failed==true then reasons[#reasons+1]='MANUAL-STATE-UNVERIFIED' end
  if (ctl.effective_intent(settings,stopped,auto,now,require('transaction').deadline)) then reasons[#reasons+1]='MANUAL-STOP-AUTO-FIRST' end
  local amode=get(auto,'mode')
  if amode~=nil and amode~='on' and amode~='off' then reasons[#reasons+1]='MANUAL-STATE-UNVERIFIED' end
  if not is_dict(selection) then reasons[#reasons+1]='MANUAL-SELECTION-UNVERIFIED' end
  if #reasons>0 then return sorted_set(reasons) end
  local phase=get(journal,'phase')
  if direction=='reserve' then
    if not (phase==nil or phase=='ROLLED-BACK') then return {'TRANSACTION-IN-PROGRESS'} end
    reasons=M.readiness(settings,certificate,consumed,selection,now)
    if not is_dict(certificate) or not eq(certificate.vendor_identity,selection.vendor_identity) or not hex(selection.vendor_identity,64) then
      reasons[#reasons+1]='LAN-TRIAL-REQUIRED'
    end
    return sorted_set(reasons)
  end
  if (phase~='COMMITTED' and phase~='HELD-ON-RESERVE') or not hex(journal.tx,32)
     or not eq(journal.source,sub_id(selection,'source')) or not eq(journal.target,sub_id(selection,'target')) then
    return {'RETURN-NOT-APPLICABLE'}
  end
  return {}
end

-- deps: now, settings(), native(), current_revision(), diagnostic() -> blockers, selection (display_diagnostic),
--   journal(), read_json(path, default) (raises), runtime, persist
function M.legacy_controls(d)
  local page=require('monitor_status')
  local now=d.now
  local result=canon.object({time=canon.float(now),control_revision=NULL,available=false,blockers=list({'MANUAL-STATE-UNVERIFIED'})})
  local ok,err=pcall(function()
    local settings=d.settings()
    if settings==nil then error('KeyError',0) end
    local state=d.native()
    if is_dict(settings) then
      local mode=get(settings,'monitor_only')
      if mode~=nil and mode~='0' then
        local function reasons() return list({'MONITOR-ONLY-DEPLOYMENT'}) end
        result.blockers=reasons()
        result.reserve=canon.object({allowed=false,blockers=reasons()})
        result.primary=canon.object({allowed=false,blockers=reasons()})
        return
      end
    end
    local revision=d.current_revision()
    local blockers,selection=d.diagnostic()
    local journal=d.journal()
    local auto=d.read_json(d.runtime..'/auto-control.json',canon.object())
    local stopped=d.read_json(d.persist..'/native-stop.json',canon.object())
    local certificate=d.read_json(d.persist..'/native-certificate.json',canon.object())
    local consumed=d.read_json(d.persist..'/native-attempts.json',canon.object())
    local pending=d.read_json(d.runtime..'/manual-control.json',canon.object())
    local extra={}
    local empty=is_dict(pending) and next(pending)==nil
    if not empty and not page.legacy_valid(pending) then extra={'MANUAL-STATE-UNVERIFIED'}
    elseif truthy(pending) and LEGACY_PENDING[pending.state] and eq(pending.control_revision,revision) then extra={'MANUAL-REQUEST-PENDING'} end
    local answers={}
    for _,direction in ipairs({'reserve','primary'}) do
      local all=copy_list(extra)
      for _,x in ipairs(M.preflight(direction,settings,blockers,selection,journal,state,auto,stopped,certificate,consumed,now)) do all[#all+1]=x end
      local reasons=sorted_set(all)
      answers[direction]=reasons
    end
    result.reserve=canon.object({allowed=#answers.reserve==0,blockers=list(copy_list(answers.reserve))})
    result.primary=canon.object({allowed=#answers.primary==0,blockers=list(copy_list(answers.primary))})
    result.control_revision=n0(revision)
    local any=#answers.reserve==0 or #answers.primary==0
    result.available=any
    if any then result.blockers=list()
    else
      local both=copy_list(answers.reserve);for _,x in ipairs(answers.primary) do both[#both+1]=x end
      result.blockers=list(sorted_set(both))
    end
  end)
  if not ok then
    if unavailable_error(err) then error(err,0) end
    result.reserve=canon.object({allowed=false,blockers=list({'MANUAL-STATE-UNVERIFIED'})})
    result.primary=canon.object({allowed=false,blockers=list({'MANUAL-STATE-UNVERIFIED'})})
  end
  return result
end

------------------------------------------------------------------------------------------------------
-- status_bridge.compute's manual_switch_control: pair controls first, then the choice of public_for_status
------------------------------------------------------------------------------------------------------
-- choose(available) -> use_pair (monitor_status.manual_switch with the reply's native_failover).
-- Returns the field, or raises M.UNAVAILABLE when the Lua side cannot answer (the monitor's bridge fallback).
function M.manual_switch_control(pair_deps,legacy_deps,choose)
  local control=M.pair_controls(pair_deps)
  if choose(control.available==true) then return control end
  return M.legacy_controls(legacy_deps)
end

return M
