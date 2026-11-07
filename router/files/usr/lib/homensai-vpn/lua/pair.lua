-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- pair.lua: pair_auto.py + pair_policy.py (+ the small pure helpers they use: recovery_settings.normalized/
-- stable_success, observation_freshness.valid_for/settle_for, failover_plan.streak) for the Lua supervisor.
--
-- State files are the Python ones: pair-auto-control.json (intent), pair-auto-state.json
-- ({"data":...,"sha256":checksum(data)}), pair-auto-budget.json, pair-readopt.json, pair-revive.json.
-- The network side of begin()/cleanup()/revive()/set_disabled (uci network read/write, config digests,
-- stock_derived.network_partition) is not ported yet: it is env.net {network(), identity(rows,managed),
-- configs(managed), changed(state,observed,skip), set_disabled(state,interface,value,revision),
-- client_down(interface), ifup(interface,revision), ifdown(interface), quiet(seconds,revision)}; without it
-- every path that needs it refuses with PAIR-NETWORK-UNVERIFIED (fail closed, as the Python ValueError).
local canon=require('canon')
local ctl=require('auto_control')
local T=require('transaction')

local M={}
local NULL=canon.null
local isnone,num,finite=ctl.isnone,ctl.num,ctl.finite
local refuse,is_refused=ctl.refuse,ctl.is_refused
local same_list,copy_list,order_is,getd,merge=T.same_list,T.copy_list,T.order_is,T.getd,T.merge

M.MODE='router-probed-ipv4'
M.TRANSIENT_START={['VENDOR-WORKER-BUSY']=true,['VENDOR-SETTLING']=true,['OBSERVATION-STALE']=true}
M.TRANSIENT_START_SECONDS=90
M.TERMINAL={STOPPED=true,FAILED=true}
M.INTERFACES={wgclient1='wgclient',ovpnclient1='ovpnclient'}
M.READOPT_CODES={['PAIR-EXTERNAL-NETWORK-CHANGE']=true,['PAIR-EXTERNAL-CONFIG-CHANGE']=true,['PAIR-EXTERNAL-POLICY-CHANGE']=true,['SOURCE-ORDER-MISMATCH']=true}
M.READOPT_LIMIT=3
M.REVIVE_PAUSE=120
M.REVIVE_LIMIT=4
-- VENDOR-WORKER-BUSY has no timeout: with a dead primary Auto waits without an attempt for as long as it lasts, and a long
-- wait looked like every short one. After BUSY_SEEN_SECONDS with the same thing in the way (the same file: inode and pid)
-- the publication names what was seen: its own code per cause, one log line, one journal event, a Telegram notice
-- (telegram.vendor_notice). It changes no decision: the blocker stays, no lock is touched. The codes say what was observed,
-- never that GL is idle (platform.vendor_busy_seen). Lock study 05.11.2026: threshold about 120 s; only-this-blocker episodes
-- at most 2.3 s, the longest with other blockers 213.5-222.3 s. Twin: pair_auto.busy_seen_step.
M.BUSY_SEEN_SECONDS=120
M.BUSY_SCAN_SECONDS=30  -- seconds between worker scans; a longer gap in busy ends the episode
M.BUSY_CODES={['rtp-lock-dead']='VENDOR-BUSY-RTP-LOCK-DEAD',['rtp-lock-live']='VENDOR-BUSY-RTP-LOCK-LIVE',['tunnel-switch']='VENDOR-BUSY-TUNNEL-SWITCH',
  workers='VENDOR-BUSY-WORKERS',unidentified='VENDOR-BUSY-UNIDENTIFIED'}
M.DEVICE_WAIT=60   -- seconds a recovery revive waits for a revived tunnel device (bounded; no guard meanwhile)

local function fwall(env) return canon.float(env.run.wall()) end
local function value_error(code) error(setmetatable({code=code,value_error=true},ctl.Refused),0) end
local function set_of(list) local s={};for _,x in ipairs(list) do s[x]=true end;return s end
local function same_set(a,b)
  local sa,sb=set_of(a),set_of(b)
  for k in pairs(sa) do if not sb[k] then return false end end
  for k in pairs(sb) do if not sa[k] then return false end end
  return true
end
local function index_of(list,x) for i=1,#list do if list[i]==x then return i end end;return nil end
local function distinct(list) local s={};for _,x in ipairs(list) do if s[x] then return false end;s[x]=true end;return true end

------------------------------------------------------------------------------------------------------
-- pure helpers of other Python modules
------------------------------------------------------------------------------------------------------
-- primary_stable 120 s (was 30) together with rescue_stable 10 s (0..60, 0 = the full primary_stable): the offline study
-- of 03.11.2026, see recovery_settings.py (Python twin) and docs/architecture/RESCUE-STABLE-2026-11-03.ru.md
local DEFAULTS={failures=3,successes=2,cooldown=60,min_dwell=60,return_policy='healthy_primary',primary_successes=2,primary_stable=120,attempt_limit=3,attempt_window=15,rescue_stable=10,
  flap_model='double',flap_limit=2,flap_window=60,flap_halflife=1800,flap_suppress=1500,flap_reuse=500}  -- recovery_settings.py: why flap_* stands apart from attempt_*
local RANGES={failures={2,10},successes={2,10},cooldown={60,1800},min_dwell={60,3600},primary_successes={2,10},primary_stable={30,600},attempt_limit={1,10},attempt_window={1,15},rescue_stable={0,60},
  flap_limit={1,10},flap_window={1,120},flap_halflife={600,3600},flap_suppress={1000,3000},flap_reuse={200,1000}}
M.RESCUE_REASON='RESERVE-FAILED-PRIMARY-VERIFIED'
function M.recovery_normalized(settings)
  local result={}
  for key,default in pairs(DEFAULTS) do
    local value=settings['recovery_'..key]
    if isnone(value) then value=default end
    if key=='return_policy' then result[key]=(value=='healthy_primary' or value=='hold_reserve') and value or default
    elseif key=='flap_model' then result[key]=(value=='double' or value=='halflife') and value or default
    elseif key=='attempt_limit' or key=='attempt_window' or key=='flap_limit' or key=='flap_window' then
      local number
      if type(value)=='number' and value%1==0 then number=value
      elseif type(value)=='string' and string.find(value,'^[0-9][0-9]?[0-9]?$') then number=tonumber(value)
      else number=default end
      local lo,hi=RANGES[key][1],RANGES[key][2]
      result[key]=(lo<=number and number<=hi) and number or default
    else
      local number
      -- review F-46 (06.11.2026): one grammar with recovery_settings.normalized: a whole number or a decimal string
      -- R2-03: at most 9 digits, and a failed conversion takes the default (recovery_settings.normalized)
      if type(value)=='number' and value%1==0 then number=value
      elseif type(value)=='string' and string.find(value,'^%s*[+-]?%d+%s*$') and #string.match(value,'%d+')<=9 then number=tonumber(value) or default
      else number=default end
      if type(number)~='number' or number~=number or number==math.huge or number==-math.huge then number=default end
      local lo,hi=RANGES[key][1],RANGES[key][2]
      result[key]=math.max(lo,math.min(hi,number))
    end
  end
  return result
end
-- recovery_settings.rescue_settings / stable_seconds: the reserve carrying the traffic has failed itself, so the
-- primary is proven with min(primary_stable, rescue_stable) seconds of stability (rescue_stable 0 = primary_stable).
-- rescue_return is a transient boolean, never a UCI option.
function M.rescue_settings(settings)
  local out=canon.object({})
  for k,v in pairs(settings) do out[k]=v end
  out.rescue_return=true
  return out
end
function M.stable_seconds(settings,policy)
  policy=policy or M.recovery_normalized(settings)
  if type(settings)=='table' and settings.rescue_return==true and policy.rescue_stable>0 then
    return math.min(policy.primary_stable,policy.rescue_stable)
  end
  return policy.primary_stable
end
-- The one return rule of both deciders - M.tick (kernel on the reserve) and transaction.committed_recovery_decision
-- (COMMITTED journal); Python twin: recovery_settings.return_rule. reserve: 'failed' (the reserve carrying the traffic
-- failed itself) -> the rescue: rescue_settings (min(primary_stable, rescue_stable) s) and NO model gate, the HMM return
-- gate never delays leaving a dead reserve; 'planned' (the reserve did not fail) -> max(primary_stable, hold) s (hold:
-- the flap-damping return_hold) AND, in the HMM modes, channel_model.return_ready; 'unknown' (pair tick only: neither
-- the reserve's success streak nor its failure) -> primary_stable, no model gate. -> settings for recovery_ready, gate.
function M.return_rule(settings,reserve,hold)
  if reserve=='failed' then return M.rescue_settings(settings),false end
  if reserve=='planned' then
    local policy=M.recovery_normalized(settings)
    local ready=settings
    if hold~=nil and hold>policy.primary_stable then ready=merge(settings,{recovery_primary_stable=hold}) end
    return ready,require('channel_model').name(settings)~='consecutive'
  end
  if reserve=='unknown' then return settings,false end
  error('return_rule: unknown reserve state',2)
end
function M.valid_for(settings)
  local value=canon.is_object(settings) and settings.interval or nil
  if type(value)=='string' and string.find(value,'^[0-9][0-9]?[0-9]?$') then value=tonumber(value) end
  if type(value)~='number' or value%1~=0 or value<10 or value>300 then return 90 end
  return math.max(30,math.min(900,value*3))
end
-- observation_freshness.settle_for: at most SETTLE_MAX s (owner decision 01.11.2026, variant B; see there).
M.SETTLE_MAX=45
function M.settle_for(settings) return math.max(30,math.min(M.SETTLE_MAX,math.floor(M.valid_for(settings)*2/3))) end

local GENERATION='^[a-f0-9]+$'
function M.profile_identity(env,profile)
  if env and env.deps and env.deps.profile_identity then return env.deps.profile_identity(profile) end
  if not canon.is_object(profile) then return nil end
  local tunnel=profile.vendor_tunnel_id
  local generation=profile.generation~=nil and profile.generation or profile.vendor_generation
  if isnone(tunnel) or tunnel=='' or not (type(generation)=='string' and #generation==32 and string.find(generation,GENERATION)) then return nil end
  local out=canon.object({})
  for _,key in ipairs({'id','protocol','interface','vendor_tunnel_id','vendor_generation'}) do out[key]=profile[key]==nil and NULL or profile[key] end
  return out
end
function M.scoped_samples(env,samples,profile)
  local identity=M.profile_identity(env,profile)
  if not identity or type(samples)~='table' or canon.is_object(samples) then return {} end
  local changed=num(profile.vendor_changed_at)
  if not changed or not finite(changed) then return {} end
  local points={}
  for _,point in ipairs(samples) do
    local t=num(point.time)
    if canon.is_object(point) and point.id==identity.id and t and finite(t) and t>=changed
       and point.interface==identity.interface and point.vendor_tunnel_id==identity.vendor_tunnel_id and point.vendor_generation==identity.vendor_generation then
      points[#points+1]=point
    end
  end
  return points
end
local FAILURES={['VPN-001']=true,['VPN-003']=true,['DNS-001']=true,['VPN-MTU']=true}  -- VPN-MTU: mtu_check.lua
function M.streak(samples,identifier,count,now,max_age,good,profile,env)
  if not (type(samples)=='table') or type(count)~='number' or count%1~=0 or count<1 or count>10
     or not finite(now) or not finite(max_age) or max_age<=0 then return false end
  if profile~=nil then samples=M.scoped_samples(env,samples,profile) end
  local points={}
  for _,s in ipairs(samples) do
    local t=num(s.time)
    if canon.is_object(s) and s.id==identifier and t and finite(t) and 0<=now-t and now-t<=max_age*count then points[#points+1]=s end
  end
  table.sort(points,function(a,b) return num(a.time)>num(b.time) end)
  local unique,seen={},{}
  for _,point in ipairs(points) do
    local stamp=num(point.time)
    local health=canon.encode(canon.array({getd(point,'code',NULL),getd(point,'dns_ok',NULL),getd(point,'https_success',NULL)}))
    if seen[stamp]~=nil and seen[stamp]~=health then return false end
    if seen[stamp]==nil then unique[#unique+1]=point;seen[stamp]=health end
  end
  if #unique<count or now-num(unique[1].time)>max_age then return false end
  for index=1,count do
    local point=unique[index]
    if index>1 and num(unique[index-1].time)-num(point.time)>max_age then return false end
    if good then
      local hs=point.https_success
      if not isnone(point.code) or point.dns_ok~=true or type(hs)~='number' or hs%1~=0 or hs<2 then return false end
    elseif type(point.code)~='string' or not FAILURES[point.code] then return false end
  end
  return true
end
function M.stable_success(samples,identifier,count,seconds,now,max_age)
  max_age=max_age or 90
  local points={}
  for _,point in ipairs(samples) do
    local t=num(point.time)
    if point.id==identifier and t and finite(t) and 0<=now-t and now-t<=seconds+max_age*count then points[t]=point end
  end
  local stamps={};for t in pairs(points) do stamps[#stamps+1]=t end
  table.sort(stamps,function(a,b) return a>b end)
  local previous,good=nil,{}
  for _,stamp in ipairs(stamps) do
    local point=points[stamp]
    if previous==nil and now-stamp>max_age then return false end
    if previous~=nil and previous-stamp>max_age then break end
    if not isnone(point.code) or point.dns_ok~=true or (num(point.https_success) or 0)<2 then break end
    good[#good+1]=stamp;previous=stamp
  end
  return #good>=count and (good[1]-good[#good])>=seconds
end

-- Late-switch recheck (MT3000 phase 2, 02.11.2026, 2.1.0-alpha5): a 15 s blackout of the primary was left at
-- about 20 s, after the primary had already recovered at 15 s. The streak above was met by three dense samples
-- whose checks all ran inside the blackout (started at about 3.5/7.5/11.5 s, published about 2.5 s later), and the
-- tick that read them needed a few more seconds (diagnostics, lease, kernel proof) before APPLYING; the monitor's
-- first healthy sample (started at 15.5 s) arrived only while the switch was already running. Right before the
-- failover commits the source is therefore looked at once more: a healthy source sample the monitor published
-- after the decision's evidence, else one bounded live probe (RECHECK_SECONDS per check). Only positive health
-- evidence aborts (a dead primary can never pass DNS + 2 of 3 HTTPS); a timeout, an error or an unavailable probe
-- goes on with the switch exactly as before. Python: pair_auto.late_recheck and its helpers.
M.LATE_RECHECK_CODE='PRIMARY-RECOVERED-BEFORE-SWITCH'
M.RECHECK_SECONDS=1
-- L2 (FAST-SWITCH-2026-11-04.ru.md): the live probe of the recheck starts with the decision and runs beside the preparation
-- (lease, readiness), its answer is taken right before the failover commits; the monitor's newest sample is still read
-- last. Owner 05.11.2026: off until measured on a router (option parallel_recheck '1' turns it on, a saved value stays). Never
-- skipped: without the parallel start (the default, no start) the old sequential probe runs.
-- Failures the short live probe cannot see: VPN-MTU (mtu_check.lua, large packets lost) passes DNS + HTTPS with small
-- packets, and Auto's live probes never run the large-packet check. With such evidence only a newer healthy monitor
-- sample (the monitor re-runs that check on every probe after a black hole) may stop the failover.
M.PROBE_BLIND_CODES={['VPN-MTU']=true}
-- source id -> the newest source sample stamp a recheck contradicted (memory only): the same evidence never
-- starts a second decision; the monitor's next sample of the source decides again.
-- 'beat:'..source id -> the `since` of the run of lost heartbeats a recheck contradicted (review 04.11.2026, finding 3). The
-- rule 'heartbeat' speaks on healthy monitor samples, so with ICMP filtered on the primary's targets the next sample was
-- new evidence for a verdict the live probe had just refuted: a lease on flash and a probe every pass, ~8640 writes a
-- day. The refutation holds for the whole run; a new run, or a failure the monitor itself sees (rule 'model'/'streak'),
-- decides again.
M.late_aborts={}
local function good_point(point)
  local hs=point.https_success
  return isnone(point.code) and point.dns_ok==true and type(hs)=='number' and hs%1==0 and hs>=2
end
M.good_point=good_point
-- newest_sample(samples, identifier, profile, env): the newest sample of identifier inside its profile generation
-- (scoped_samples); nil without one, or when two samples of one stamp disagree (failure_diagnosis.scoped_samples).
function M.newest_sample(samples,identifier,profile,env)
  if profile~=nil then samples=M.scoped_samples(env,samples,profile) end
  if type(samples)~='table' then return nil end
  local best,seen=nil,{}
  for _,point in ipairs(samples) do
    local t=canon.is_object(point) and point.id==identifier and num(point.time) or nil
    if t and finite(t) then
      local health=canon.encode(canon.array({getd(point,'code',NULL),getd(point,'dns_ok',NULL),getd(point,'https_success',NULL)}))
      if seen[t]~=nil and seen[t]~=health then return nil end
      seen[t]=health
      if best==nil or t>num(best.time) then best=point end
    end
  end
  return best
end
-- monitor_recovered: the monitor published a healthy sample of the source newer than the decision's evidence
-- (and not from the future).
function M.monitor_recovered(samples,identifier,evidence,now,profile,env)
  if not finite(evidence) or not finite(now) then return false end
  local point=M.newest_sample(samples,identifier,profile,env)
  if not point then return false end
  local t=num(point.time)
  return t>num(evidence) and t<=num(now) and good_point(point)
end
-- same_evidence: a recheck already contradicted this very evidence (no newer source sample since)
function M.same_evidence(aborted,evidence)
  return finite(aborted) and finite(evidence) and num(evidence)<=num(aborted)
end
-- recheck_begin(env, selection, evidence_code, settings) -> pending | nil: L2, the live probe of late_recheck starts now
-- (nil: not started; late_recheck then probes sequentially, or not at all for a PROBE_BLIND_CODES failure, as before)
function M.recheck_begin(env,selection,evidence_code,settings)
  local on=settings.parallel_recheck
  if (on~=true and on~='1') or not env.backend.recheck_begin then return nil end
  if type(evidence_code)=='string' and M.PROBE_BLIND_CODES[evidence_code] then return nil end
  local ok,pending=pcall(env.backend.recheck_begin,selection.source.id,M.RECHECK_SECONDS)
  if ok then return pending end
  return nil
end
-- recheck_finish(env, pending) -> the live answer (true | false | nil); any failure of the last look goes on with the switch
function M.recheck_finish(env,pending)
  local ok,healthy=pcall(env.backend.recheck_finish,pending)
  return ok and healthy or nil
end
-- late_recheck(env, selection, evidence, evidence_code, pending) -> code, how | nil: the last look at the source before a
-- failover commits. evidence_code: the code of the decision's newest source sample; a PROBE_BLIND_CODES failure is
-- never contradicted by the live probe. pending: the probe recheck_begin started; its answer takes the place of a new one.
function M.late_recheck(env,selection,evidence,evidence_code,pending)
  local identifier=selection.source.id
  local ok,status=pcall(ctl.read_json,env.run,T.paths(env).status,canon.object({}))
  if ok and canon.is_object(status) and M.monitor_recovered(getd(status,'samples',canon.array({})),identifier,evidence,env.run.wall(),selection.source,env) then
    if pending then M.recheck_finish(env,pending) end
    return M.LATE_RECHECK_CODE,'monitor'
  end
  if pending then
    if M.recheck_finish(env,pending)==true then return M.LATE_RECHECK_CODE,'probe' end
    return nil
  end
  if env.backend.recheck and not (type(evidence_code)=='string' and M.PROBE_BLIND_CODES[evidence_code]) then
    local pok,healthy=pcall(env.backend.recheck,identifier,M.RECHECK_SECONDS)
    if pok and healthy==true then return M.LATE_RECHECK_CODE,'probe' end
  end
  return nil
end

-- pair_auto.decision_timing: the stamps of the last decision in RAM (FAST-SWITCH-2026-11-04.ru.md); measurement only
function M.decision_timing(env,decided,prepared,rechecked,rule,parallel)
  pcall(ctl.write_json,env.run,env.runtime..'/pair-decision-timing.json',canon.object({decided=canon.float(decided),prepared=canon.float(prepared),
    rechecked=canon.float(rechecked),rule=rule,parallel=parallel}))
end

------------------------------------------------------------------------------------------------------
-- pair_policy
------------------------------------------------------------------------------------------------------
local P={}
M.policy=P
local function pvalid(value,order)
  if not canon.is_object(value) or not canon.is_array(order) or #order<2 or #order>400 then value_error('PAIR-POLICY-UNVERIFIED') end
  for _,k in ipairs(order) do if type(k)~='string' or k=='' then value_error('PAIR-POLICY-UNVERIFIED') end end
  if not distinct(order) or (value.direction~='first' and value.direction~='last') then value_error('PAIR-POLICY-UNVERIFIED') end
  for _,key in ipairs({'source_rule','target_rule','source_id','target_id'}) do
    if type(value[key])~='string' or value[key]=='' then value_error('PAIR-POLICY-UNVERIFIED') end
  end
  if value.source_rule==value.target_rule or value.source_id==value.target_id then value_error('PAIR-POLICY-UNVERIFIED') end
  local generic=value.generic_rules
  if not canon.is_array(generic) or #generic<2 or #generic>16 then value_error('PAIR-POLICY-UNVERIFIED') end
  local oset=set_of(order)
  for _,k in ipairs(generic) do if type(k)~='string' or not oset[k] then value_error('PAIR-POLICY-UNVERIFIED') end end
  if not distinct(generic) then value_error('PAIR-POLICY-UNVERIFIED') end
  local gset=set_of(generic)
  if not gset[value.source_rule] or not gset[value.target_rule] then value_error('PAIR-POLICY-UNVERIFIED') end
  return value
end
P.validate=pvalid
function P.proof(selection)
  local value=canon.object({source_rule=getd(selection,'source_rule',NULL),target_rule=getd(selection,'target_rule',NULL),direction=getd(selection,'direction',NULL)})
  local generic=getd(selection,'generic_rules',nil)
  local list={}
  if generic then for i,x in ipairs(generic) do list[i]=x end else list={value.source_rule,value.target_rule} end
  table.sort(list);value.generic_rules=canon.array(list)
  value.source_id=getd(getd(selection,'source',canon.object({})),'id',NULL)
  value.target_id=getd(getd(selection,'target',canon.object({})),'id',NULL)
  pvalid(value,selection.order)
  return value
end
function P.role(value,order)
  pvalid(value,order)
  local generic={};for i,x in ipairs(value.generic_rules) do generic[i]=x end
  table.sort(generic,function(a,b) return index_of(order,a)<index_of(order,b) end)
  local chosen=value.direction=='first' and generic[1] or generic[#generic]
  for _,key in ipairs({'source','target'}) do if value[key..'_rule']==chosen then return key end end
  value_error('PAIR-POLICY-UNVERIFIED')
end
function P.desired_order(value,order,destination)
  if destination~='source' and destination~='target' then value_error('PAIR-POLICY-UNVERIFIED') end
  local current=P.role(value,order)
  local result=copy_list(order)
  if current~=destination then
    local a,b=index_of(result,value.source_rule),index_of(result,value.target_rule)
    result[a],result[b]=result[b],result[a]
  end
  if P.role(value,result)~=destination then value_error('PAIR-POLICY-UNVERIFIED') end
  return result
end
function P.transition(selection,session_order,destination)
  local identity=P.proof(selection);local before=selection.order
  if not canon.is_array(session_order) or #session_order~=#before or not same_set(session_order,before) then value_error('PAIR-POLICY-UNVERIFIED') end
  if not (same_list(session_order,P.desired_order(identity,before,'source')) or same_list(session_order,P.desired_order(identity,before,'target'))) then
    value_error('PAIR-POLICY-UNVERIFIED')
  end
  local out=merge(identity)
  out.destination_role=destination;out.before_policy_role=P.role(identity,before)
  out.session_order=copy_list(session_order);out.primary_order=P.desired_order(identity,before,'source')
  return out
end
local META_KEYS={source_rule=true,target_rule=true,direction=true,generic_rules=true,source_id=true,target_id=true,destination_role=true,before_policy_role=true,session_order=true,primary_order=true}
function P.metadata(value)
  local ctx=value.pair_transition
  if isnone(ctx) then return nil end
  if not canon.is_object(ctx) then value_error('PAIR-POLICY-UNVERIFIED') end
  local n=0
  for k in pairs(ctx) do if not META_KEYS[k] then value_error('PAIR-POLICY-UNVERIFIED') end;n=n+1 end
  if n~=10 then value_error('PAIR-POLICY-UNVERIFIED') end
  local identity=pvalid(ctx,value.before)
  if identity.source_id~=value.source or identity.target_id~=value.target or (ctx.destination_role~='source' and ctx.destination_role~='target')
     or ctx.before_policy_role~=P.role(identity,value.before) or not same_list(value.after,P.desired_order(identity,value.before,ctx.destination_role)) then
    value_error('PAIR-POLICY-UNVERIFIED')
  end
  for _,key in ipairs({'session_order','primary_order'}) do
    if not canon.is_array(ctx[key]) or #ctx[key]~=#value.before or not same_set(ctx[key],value.before) then value_error('PAIR-POLICY-UNVERIFIED') end
  end
  if not same_list(ctx.primary_order,P.desired_order(identity,value.before,'source')) then value_error('PAIR-POLICY-UNVERIFIED') end
  if not (same_list(ctx.session_order,P.desired_order(identity,value.before,'source')) or same_list(ctx.session_order,P.desired_order(identity,value.before,'target'))) then
    value_error('PAIR-POLICY-UNVERIFIED')
  end
  for _,key in ipairs({'restored_order','restore_target_order'}) do
    local restored=value[key]
    if not isnone(restored) and not T.in_orders(restored,value.before,ctx.primary_order,ctx.session_order) then value_error('PAIR-POLICY-UNVERIFIED') end
  end
  return ctx
end
function P.current_order(value)
  if value.phase=='COMMITTED' or value.phase=='HELD-ON-RESERVE' then return value.after end
  if value.phase=='ROLLED-BACK' then return getd(value,'restored_order',value.before) end
  return nil
end
function P.current_role(value)
  local ctx=P.metadata(value);local order=P.current_order(value)
  if ctx~=nil and order~=nil then return P.role(ctx,order) end
  return nil
end
function P.state_order_matches(state,value,live_order,live_hash)
  local ok,ctx=pcall(P.metadata,value)
  if not ok then return false end
  if same_list(live_order,state.order) and live_hash==state.policy_hash and (value.phase==nil or value.phase=='ROLLED-BACK') then return true end
  local identity=getd(state,'policy_roles',nil)
  if ctx==nil or not same_list(ctx.session_order,state.order) or value.hash~=state.policy_hash then return false end
  if identity~=nil then for key,item in pairs(identity) do if canon.encode(getd(ctx,key,NULL))~=canon.encode(item) then return false end end end
  local current=P.current_order(value)
  return current~=nil and same_list(live_order,current) and live_hash==value.hash
end

------------------------------------------------------------------------------------------------------
-- state files
------------------------------------------------------------------------------------------------------
function M.paths(env) return env.runtime..'/pair-auto-control.json',env.persist..'/pair-auto-state.json',env.persist..'/pair-auto-budget.json' end

function M.state_interfaces(data)
  local managed=canon.is_object(data) and data.interfaces or nil
  if isnone(managed) then return M.INTERFACES end
  if not canon.is_object(managed) then value_error('PAIR-STATE-UNVERIFIED') end
  local count=0
  for name,proto in pairs(managed) do
    if not ((string.find(name,'^wgclient[1-9]%d*$') and proto=='wgclient') or (string.find(name,'^ovpnclient[1-9]%d*$') and proto=='ovpnclient')) or #name>14 then
      value_error('PAIR-STATE-UNVERIFIED')
    end
    count=count+1
  end
  if count~=2 then value_error('PAIR-STATE-UNVERIFIED') end
  return managed
end

function M.read_state(env)
  local _,path=M.paths(env)
  if env.run.fs.unsafe and env.run.fs.unsafe(path) then value_error('PAIR-STATE-UNVERIFIED') end
  local envelope=ctl.read_json(env.run,path,canon.object({}))
  if canon.is_object(envelope) and next(envelope)==nil then return canon.object({}) end
  local data=canon.is_object(envelope) and envelope.data or nil
  local managed
  if canon.is_object(data) then managed=M.state_interfaces(data) else managed={} end
  local PH={STARTING=true,RUNNING=true,STOPPING=true,HELD=true,STOPPED=true,FAILED=true}
  if not canon.is_object(data) or envelope.sha256~=canon.digest(data) or not PH[data.phase] or not ctl.hex(data.id,32)
     or not canon.is_array(data.owned) or not canon.is_object(data.before_flags) or not ctl.hex(data.network_identity,64) then
    value_error('PAIR-STATE-UNVERIFIED')
  end
  for _,x in ipairs(data.owned) do if type(x)~='string' or not managed[x] then value_error('PAIR-STATE-UNVERIFIED') end end
  if not distinct(data.owned) then value_error('PAIR-STATE-UNVERIFIED') end
  local flags=0
  for k,v in pairs(data.before_flags) do
    if not managed[k] or (v~='0' and v~='1') then value_error('PAIR-STATE-UNVERIFIED') end
    flags=flags+1
  end
  local mcount=0;for _ in pairs(managed) do mcount=mcount+1 end
  if flags~=mcount then value_error('PAIR-STATE-UNVERIFIED') end
  if data.protected_static~=nil then
    local ps=data.protected_static
    if not canon.is_object(ps) or ps.firewall==nil or not ctl.hex(ps.firewall,64) then value_error('PAIR-STATE-UNVERIFIED') end
    for k in pairs(ps) do if k~='firewall' then value_error('PAIR-STATE-UNVERIFIED') end end
  end
  if data.kept~=nil or data.kept_flags~=nil or data.kept_at~=nil or data.kept_tx~=nil then
    -- the boot handover (M.boot_keep): only on a STOPPED session, owned clients with their flags before the session;
    -- kept_tx: kept for the restart Start after this supervisor's forward resume of that transaction (no boot)
    local kept,kf=data.kept,data.kept_flags
    if data.phase~='STOPPED' or not canon.is_array(kept) or #kept==0 or not canon.is_object(kf) or not finite(data.kept_at) or num(data.kept_at)<0
       or (data.kept_tx~=nil and not ctl.hex(data.kept_tx,32)) then
      value_error('PAIR-STATE-UNVERIFIED')
    end
    for _,x in ipairs(kept) do if type(x)~='string' or not managed[x] or (kf[x]~='0' and kf[x]~='1') then value_error('PAIR-STATE-UNVERIFIED') end end
    if not distinct(kept) then value_error('PAIR-STATE-UNVERIFIED') end
    local n=0;for _ in pairs(kf) do n=n+1 end
    if n~=#kept then value_error('PAIR-STATE-UNVERIFIED') end
  end
  if data.handover~=nil then
    -- the boot handover on the reserve (M.boot_handover): only on a STOPPED session, its own order and policy
    local h=data.handover
    local ok=data.phase=='STOPPED' and canon.is_object(h) and ctl.hex(h.tx,32) and h.policy_hash==data.policy_hash and canon.is_array(h.order)
      and canon.is_array(data.order) and same_list(h.order,data.order) and finite(h.at) and num(h.at)>=0
    if ok then local n=0;for _ in pairs(h) do n=n+1 end;ok=n==4 end
    if not ok then value_error('PAIR-STATE-UNVERIFIED') end
  end
  if data.manual_hold~=nil and data.manual_hold~='source' and data.manual_hold~='target' then value_error('PAIR-MANUAL-HOLD-UNVERIFIED') end
  local mhs=data.manual_hold_source
  if mhs~=nil and mhs~='manual' and mhs~='test' and mhs~='programmatic' and mhs~='unknown' then value_error('PAIR-MANUAL-HOLD-UNVERIFIED') end
  if data.policy_roles~=nil then
    local ok=pcall(pvalid,data.policy_roles,data.order)
    if not ok then value_error('PAIR-STATE-UNVERIFIED') end
  end
  if data.selected_policy~=nil then
    local s=data.selected_policy
    local ok=canon.is_object(s) and s.hash==data.policy_hash and (s.role=='source' or s.role=='target') and finite(s.since) and num(s.since)>0
    if ok then local n=0;for _ in pairs(s) do n=n+1 end;ok=n==4 and s.order~=nil end
    if ok then local rok,role=pcall(P.role,data.policy_roles,s.order);ok=rok and role==s.role end
    if not ok then value_error('PAIR-STATE-UNVERIFIED') end
  end
  if data.manual_selection~=nil then
    local s=data.manual_selection
    local ok=canon.is_object(s) and ctl.hex(s.request_id,32) and (s.role=='source' or s.role=='target') and s.role==data.manual_hold
      and canon.is_array(s.order) and s.hash==data.policy_hash and canon.is_array(data.order) and #s.order==#data.order and same_set(s.order,data.order)
      and ctl.hex(s.vendor_identity,64) and canon.is_object(s.profiles)
    if ok then local n=0;for _ in pairs(s) do n=n+1 end;ok=n==6 end
    if ok then
      local n=0
      for key,profile in pairs(s.profiles) do
        n=n+1
        if (key~='source' and key~='target') or not canon.is_object(profile) or canon.encode(M.profile_identity(env,profile) or NULL)~=canon.encode(profile) then ok=false end
      end
      ok=ok and n==2
    end
    if not ok then value_error('PAIR-STATE-UNVERIFIED') end
  end
  return data
end

function M.save(env,state)
  local _,path=M.paths(env)
  ctl.write_json(env.run,path,canon.object({data=state,sha256=canon.digest(state)}))
end

function M.intent(env)
  local path=M.paths(env)
  local row=ctl.read_json(env.run,path,canon.object({}))
  if not canon.is_object(row) then value_error('PAIR-INTENT-UNVERIFIED') end
  if next(row)~=nil and ((row.mode~='on' and row.mode~='off') or type(row.revision)~='string' or not finite(row.time)) then value_error('PAIR-INTENT-UNVERIFIED') end
  return row
end

function M.stop_locked(env,revision,request_source)
  ctl.write_json(env.run,(M.paths(env)),canon.object({mode='off',revision=revision,time=fwall(env),request_source=ctl.normalize_request_source(request_source or 'programmatic')}))
end

-- pair_auto.budget: the ledger lives longer than the rate limit looks back (the flap damping remembers failovers);
-- LEDGER_SIZE bounds the file, failovers older than RATE_MEMORY give way first.
M.RATE_MEMORY=900;M.LEDGER_MEMORY=14400;M.LEDGER_SIZE=15
function M.budget(events,now,window,limit)
  window=window or 900;limit=limit or 3
  if not canon.is_array(events) or #events>16 or not finite(now) then value_error('PAIR-BUDGET-UNVERIFIED') end
  local values={}
  for i,x in ipairs(events) do
    local v=num(x)
    if not v or not finite(v) or v<0 then value_error('PAIR-BUDGET-UNVERIFIED') end
    values[i]=math.min(v,now)
  end
  if type(window)~='number' or window%1~=0 or window<60 or window>900 or type(limit)~='number' or limit%1~=0 or limit<1 or limit>10 then value_error('PAIR-BUDGET-UNVERIFIED') end
  local recent,older={},{}
  for _,x in ipairs(values) do
    if now-x<M.RATE_MEMORY then recent[#recent+1]=x elseif now-x<M.LEDGER_MEMORY then older[#older+1]=x end
  end
  table.sort(recent);table.sort(older)
  local count=0
  for _,x in ipairs(recent) do if now-x<window then count=count+1 end end
  local out={}
  for i=#older-math.max(0,M.LEDGER_SIZE-#recent)+1,#older do
    if i>=1 then out[#out+1]=canon.float(older[i]) end
  end
  for _,x in ipairs(recent) do out[#out+1]=canon.float(x) end
  return canon.array(out),count<limit and #recent<16
end

-- BH3-03 (bug hunt 07.11.2026), twin of pair_auto.charge_clock/effective_events/clock_note: after a backward clock step
-- the clamped future stamps kept the cooldown spacing from ever elapsing (every failover PAIR-RATE-LIMIT for the size of
-- the step). Ages are measured on the monotonic clock of this boot (RAM note: uptime second + boot_id of each charge); a
-- stamp more than CLOCK_SKEW s in the future without a note (another boot, an old ledger) is as old as the current uptime:
-- at most one cooldown from now. The wall age still wins when it is larger (tests/budget_clock_cases.json).
M.CLOCK_SKEW=120;M.CLOCK_NAME='pair-budget-clock.json';M.BOOT_ID='/proc/sys/kernel/random/boot_id'
function M.boot_clock(env)
  local okc,up=pcall(env.run.clock)
  up=okc and num(up) or nil
  if not up or not finite(up) or up<0 then return nil,nil end
  local okb,text=pcall(env.run.fs.read,M.BOOT_ID)
  local boot=okb and type(text)=='string' and string.match(text,'^%s*([0-9a-f%-]+)%s*$') or nil
  if not boot or #boot<8 or #boot>64 then return nil,nil end
  return up,boot
end
function M.charge_clock(events,record,now,uptime,boot)
  if not canon.is_array(events) then return events end
  local out={}
  if not (type(uptime)=='number' and finite(uptime) and uptime>=0 and finite(now)) then
    for i,x in ipairs(events) do out[i]=x end
    return canon.array(out)
  end
  local noted={}
  if canon.is_object(record) and type(boot)=='string' and boot~='' and record.boot==boot and canon.is_array(record.at) then
    for _,p in ipairs(record.at) do
      if canon.is_array(p) and #p==2 then
        local w,u=num(p[1]),num(p[2])
        if w and u and finite(w) and finite(u) and u>=0 then noted[w]=u end
      end
    end
  end
  for i,x in ipairs(events) do
    local v=num(x)
    if not v or not finite(v) or v<0 then out[i]=x
    else
      local age,bound=now-v,nil
      if noted[v] then if uptime>=noted[v] then bound=uptime-noted[v] end
      elseif age< -M.CLOCK_SKEW then bound=uptime end
      if bound and bound>age then out[i]=canon.float(now-bound) else out[i]=x end
    end
  end
  return canon.array(out)
end
function M.effective_events(env,ledger,now)
  local events=canon.is_object(ledger) and ledger.events or nil
  local up,boot=M.boot_clock(env)
  if not up then return events end
  local record=ctl.read_json_safe(env.run,env.runtime..'/'..M.CLOCK_NAME,canon.object({}))
  return M.charge_clock(events,record,now,up,boot)
end
function M.clock_note(env,events,stamp)
  local up,boot=M.boot_clock(env)
  if not up then return end
  pcall(function()
    local record=ctl.read_json_safe(env.run,env.runtime..'/'..M.CLOCK_NAME,canon.object({}))
    local present={}
    for _,x in ipairs(events) do local v=num(x);if v then present[v]=true end end
    local at={}
    if canon.is_object(record) and record.boot==boot and canon.is_array(record.at) then
      for _,p in ipairs(record.at) do
        if canon.is_array(p) and #p==2 and num(p[1]) and present[num(p[1])] and num(p[1])~=stamp then at[#at+1]=p end
      end
    end
    at[#at+1]=canon.array({canon.float(stamp),canon.float(up)})
    local list={}
    for i=math.max(1,#at-15),#at do list[#list+1]=at[i] end
    ctl.write_json(env.run,env.runtime..'/'..M.CLOCK_NAME,canon.object({boot=boot,at=canon.array(list)}))
  end)
end

-- Flap damping (MT3000 flap test 02.11.2026, primary 60 s down / 120 s up): the rolling attempt limit used to
-- block the FAILOVER, so after three switches traffic stayed on a dead primary while every recovery still
-- returned after ~70 s. Like RFC 2439/7196 route-flap damping and BFD/VRRP hold-down, leaving a failed
-- primary is never limited (only the cooldown spacing bounds retries of a failed attempt); the RETURN is
-- damped instead. HOLD_CAP is the longest primary stability the settings allow (RANGES.primary_stable).
M.HOLD_CAP=600
M.PENALTY=1000
-- flap_model 'halflife' (RFC 2439 penalty, study wave 3): pair_auto.halflife_hold, replayed from the ledger on every call.
function M.halflife_hold(events,now,recovery)
  local half,stable,reuse=recovery.flap_halflife,recovery.primary_stable,recovery.flap_reuse
  local stamps={}
  for _,x in ipairs(events) do local v=num(x);if v and v<=now then stamps[#stamps+1]=v end end
  table.sort(stamps)
  local penalty,last,suppressed=0.0,nil,false
  for _,stamp in ipairs(stamps) do
    penalty=last and penalty*0.5^((stamp-last)/half) or 0.0
    if suppressed and penalty<reuse then suppressed=false end
    penalty=penalty+M.PENALTY;last=stamp
    if penalty>recovery.flap_suppress then suppressed=true end
  end
  if not last then return stable end
  penalty=penalty*0.5^((now-last)/half)
  if not suppressed or penalty<reuse then return stable end
  return math.floor(math.min(M.HOLD_CAP,math.max(stable,stable+half*math.log(penalty/reuse)/math.log(2))))
end
-- Seconds the primary must be stably healthy before Auto returns to it. flap_model 'double' (default): primary_stable
-- below flap_limit failovers within flap_window minutes; the failover that reaches the limit, and every further one,
-- doubles it (capped); failovers ageing out of the window decay it. 'halflife': M.halflife_hold.
-- Twin: pair_auto.return_hold (flap_damping_cases.json).
function M.return_hold(events,now,recovery)
  if recovery.flap_model=='halflife' then return M.halflife_hold(events,now,recovery) end
  local window=recovery.flap_window*60
  local count=0
  for _,x in ipairs(events) do local v=num(x);if v and now-v>=0 and now-v<window then count=count+1 end end
  local excess=count-recovery.flap_limit+1
  if excess<=0 then return recovery.primary_stable end
  return math.floor(math.min(M.HOLD_CAP,recovery.primary_stable*2^math.min(excess,6)))
end

-- Aborted failover retry (MT3000 59-cycle primary-drop soak 03-04.11.2026, 2.1.0-alpha7, cycle 28): the failover was
-- dispatched (APPLYING, ledger charged), apply_steps' first diagnostic saw VENDOR-WORKER-QUIET-UNVERIFIED and the
-- transaction rolled back before any switch; the charge stayed, so the next failover waited the whole cooldown spacing
-- (PAIR-RATE-LIMIT, ~60 s) while the primary was dead: traffic moved after 84 s instead of 20-35 s. A failover refused
-- by a transient vendor state (M.ABORT_REFUND_CODES) whose journal is verifiably ROLLED-BACK and never COMMITTED is not
-- a switch: its charge is refunded (neither the cooldown spacing nor the flap damping counts it) and the abort is kept
-- under 'aborted'. While the primary stays failed the retry waits RETRY_BASE*2^(n-1) s after the n-th consecutive
-- abort, capped at max(cooldown, min_dwell): 5, 10, 20, 40, 60 s - prompt, never hot. Every vendor gate stays as it
-- was: a busy vendor worker still refuses the switch itself. Twin: pair_auto.retry_wait / refund_abort
-- (tests/vendor_retry_cases.json).
M.ABORT_REFUND_CODES={['VENDOR-WORKER-BUSY']=true,['VENDOR-SETTLING']=true,['VENDOR-WORKER-QUIET-UNVERIFIED']=true}
M.RETRY_BASE=5
M.ABORT_KEEP=16
-- The ledger's 'aborted' stamps inside the 900 s ledger window, oldest first, at most ABORT_KEEP. Lenient: a damaged
-- entry is dropped (the next refund writes a clean list); a missing key is no abort.
function M.abort_stamps(raw,now)
  local kept={}
  if not canon.is_array(raw) then return kept end
  for _,x in ipairs(raw) do
    local v=num(x)
    -- BH3-03: a stamp more than CLOCK_SKEW s in the future predates a backward clock step: dropped, not clamped
    if v and finite(v) and v>=0 and now-v<900 and v-now<=M.CLOCK_SKEW then kept[#kept+1]=math.min(v,now) end
  end
  table.sort(kept)
  local out={}
  for i=math.max(1,#kept-M.ABORT_KEEP+1),#kept do out[#out+1]=kept[i] end
  return out
end
-- Seconds before a failover aborted by the vendor may be dispatched again (0: now). Only the aborts after the last
-- charged switch count (a completed switch ends the series).
function M.retry_wait(aborted,events,now,recovery)
  local last=nil
  for _,x in ipairs(events or {}) do local v=num(x);if v and (last==nil or v>last) then last=v end end
  local recent={}
  for _,x in ipairs(M.abort_stamps(aborted,now)) do if last==nil or x>last then recent[#recent+1]=x end end
  if #recent==0 then return 0 end
  local wait=math.min(math.max(recovery.cooldown,recovery.min_dwell),M.RETRY_BASE*2^math.min(#recent-1,8))
  return math.max(0,recent[#recent]+wait-now)
end
local function ledger_events(env,now)
  local _,_,path=M.paths(env)
  local ledger=ctl.read_json(env.run,path,canon.object({events=canon.array({})}))
  if not canon.is_object(ledger) then return NULL end
  return M.effective_events(env,ledger,now) or NULL  -- BH3-03: ages on the monotonic clock of this boot
end
-- What flap damping counts (review 04.11.2026, finding 5). The ledger's events are every charge, the rate limit and the
-- cooldown need them all; the return of the pair_return path, a kernel repair and a manual switch are charges too but no
-- failovers, and the documented hold (240 s for two failovers in an hour) was reached by one failover and one of those.
-- They are listed under 'others'. A ledger written before this key has none: every charge counts, as it did.
-- Python: pair_auto.failover_events.
function M.failover_events(events,ledger)
  local others=canon.is_object(ledger) and ledger.others or nil
  if not canon.is_array(others) then return events end
  local skip,out={},{}
  for _,x in ipairs(others) do local v=num(x);if v then skip[v]=true end end
  for _,x in ipairs(events) do if not skip[num(x)] then out[#out+1]=x end end
  return canon.array(out)
end
local function ledger_row(env)
  local _,_,path=M.paths(env)
  local ledger=ctl.read_json(env.run,path,canon.object({events=canon.array({})}))
  return canon.is_object(ledger) and ledger or canon.object({})
end
-- return_hold from the persistent failover ledger; an unreadable ledger holds the longest.
function M.ledger_hold(env,settings,now)
  local recovery=M.recovery_normalized(settings)
  local ok,events=pcall(function()
    local ledger=ledger_row(env)
    return M.failover_events((M.budget(M.effective_events(env,ledger,now) or NULL,now,recovery.attempt_window*60,recovery.attempt_limit)),ledger)
  end)
  if not ok then return M.HOLD_CAP end
  return M.return_hold(events,now,recovery)
end
-- One charge: events are the budget()ed stamps before it. 'aborted' and 'others' stay with the file, so that no writer
-- loses what another one recorded. Python: pair_auto.ledger_charge.
function M.ledger_charge(env,events,stamp,failover)
  local _,_,path=M.paths(env)
  local okr,ledger=pcall(ledger_row,env)
  if not okr then ledger=canon.object({}) end
  local value=canon.object({})
  -- 'aborted' is kept: a refund of this charge must still see the earlier aborts of the series (M.retry_wait)
  local aborted=M.abort_stamps(ledger.aborted,stamp)
  if #aborted>0 then
    local list={};for i,x in ipairs(aborted) do list[i]=canon.float(x) end
    value.aborted=canon.array(list)
  end
  local present,others={},{}
  for _,x in ipairs(events) do local v=num(x);if v then present[v]=true end end
  if canon.is_array(ledger.others) then
    for _,x in ipairs(ledger.others) do if present[num(x)] then others[#others+1]=x end end
  end
  if not failover then others[#others+1]=canon.float(stamp) end
  if #others>0 then value.others=canon.array(others) end
  events[#events+1]=canon.float(stamp)
  value.events=events
  ctl.write_json(env.run,path,value)
  M.clock_note(env,events,stamp)  -- BH3-03: the monotonic age of this charge
end
local function ledger_aborted(env)
  local _,_,path=M.paths(env)
  local ledger=ctl.read_json(env.run,path,canon.object({events=canon.array({})}))
  return canon.is_object(ledger) and ledger.aborted or nil
end
-- The failover charged at `stamp` was refused by `code` and rolled back before COMMITTED: drop its charge and
-- remember the abort. Anything unproven (other code, journal not ROLLED-BACK by this very failure, charge not found)
-- keeps the charge: the cooldown spacing then applies as before. True when refunded.
-- Review 04.11.2026 (finding 6): the same VENDOR-* codes also come AFTER the switch itself (the verify wait after the rtp2
-- dispatch, wait_quiet after it): that rollback followed a real kernel switch, so the charge stays. Refunded only when the
-- journal proves that nothing was written: rtp_dispatched and forward_policy_touched both exactly false.
function M.refund_abort(env,stamp,code)
  if type(code)~='string' or not M.ABORT_REFUND_CODES[code] or not finite(stamp) then return false end
  stamp=num(stamp)
  local journal=T.journal_read(env)
  local started=num(journal.started)
  if journal.phase~='ROLLED-BACK' or journal.failure_code~=code or not isnone(journal.confirmed)
     or isnone(journal.pair_transition) or started==nil or started>stamp
     or journal.rtp_dispatched~=false or journal.forward_policy_touched~=false then return false end
  local _,_,path=M.paths(env)
  local ledger=ctl.read_json(env.run,path,canon.object({events=canon.array({})}))
  if not canon.is_object(ledger) or not canon.is_array(ledger.events) then return false end
  local events,found={},false
  for _,x in ipairs(ledger.events) do
    if not found and num(x)==stamp then found=true else events[#events+1]=x end
  end
  if not found then return false end
  local now=env.run.wall()
  local aborted=M.abort_stamps(ledger.aborted,now);aborted[#aborted+1]=now
  local list={};for i=math.max(1,#aborted-M.ABORT_KEEP+1),#aborted do list[#list+1]=canon.float(aborted[i]) end
  local row=canon.object({events=canon.array(events),aborted=canon.array(list)})
  if canon.is_array(ledger.others) and #ledger.others>0 then row.others=ledger.others end
  ctl.write_json(env.run,path,row)
  return true
end

function M.require_running(env,revision)
  T.require_control_revision(env,revision)
  if env.stop() then refuse('CLIENT-STOP') end
end

function M.publish_failure(env,err)
  local code=(type(err)=='string' and ctl.code_ok(err)) and err or (is_refused(err) and ctl.code_ok(err.code) and err.code) or 'PAIR-SYSTEM-001'
  -- K11 (formal model 03.11.2026): read and write under the control lock. The owner's Start hands a session HELD by an
  -- outside change over under this lock (release_session: STOPPED); a HELD written from an older read would undo that
  -- hand-over (the Start then refused PAIR-RECOVERY-REQUIRED). Python: pair_auto.publish_failure.
  local outside=nil
  pcall(env.run.lock,function()
    local pending=M.read_state(env)
    -- review 04.11.2026 (finding 3): an unchanged HELD record is not written again on every pass
    if next(pending)~=nil and not M.TERMINAL[pending.phase] and not (pending.phase=='HELD' and pending.recovery_error==code) then
      pending.phase='HELD';pending.recovery_error=code;M.save(env,pending)
    end
    -- owner decision 07.11.2026: a hold decided by readopt_class is named with its class (never a value)
    if pending.phase=='HELD' and canon.is_object(pending.outside_change) and pending.outside_change.trigger==code then outside=pending.outside_change end
  end,env.runtime)
  local value={state='BLOCKED',mode='continuous-pair',proof_scope=M.MODE,original_restored=false,blockers=canon.array({code})}
  if outside~=nil then value.reason=M.HOLD_CODE;value.outside_change=outside end
  local ok=pcall(T.publish,env,value)
  if not ok then ctl.write_json(env.run,T.paths(env).state,merge(value,{time=fwall(env),history_error='HISTORY-001'})) end
end

function M.fail_request(env,request,revision,err)
  local code=is_refused(err) and ctl.code_ok(err.code) and err.code or 'PAIR-SYSTEM-001'
  return env.run.lock(function()
    local current=M.intent(env)
    if ctl.revision_locked(env)~=revision or current.revision~=revision or current.mode~='on' or current.id~=request.id then return false end
    ctl.write_json(env.run,(M.paths(env)),canon.object({mode='off',revision=revision,time=fwall(env),failed_request_id=request.id,failure_code=code,
      request_source=getd(current,'request_source','unknown')}))
    return true
  end,env.runtime)
end

function M.fence_recovery(env)
  env.run.lock(function()
    if env.run.fs.read((M.paths(env)))~=nil then M.stop_locked(env,ctl.revision_locked(env)) end
    pcall(require('manual').terminalize_pending_locked,env,'UNCONFIRMED','PAIR-MANUAL-RECOVERED')
  end,env.runtime)
end

function M.resume_running(env,state)
  if state.phase=='HELD' and state.ran==true then state.phase='RUNNING';state.recovery_error=nil;M.save(env,state) end
end

function M.remember_selected(env,state,kernel)
  if kernel.verified~=true or (kernel.role~='source' and kernel.role~='target') or kernel.policy_hash~=state.policy_hash or not finite(kernel.time) then
    value_error('KERNEL-POLICY-UNVERIFIED')
  end
  if P.role(state.policy_roles,kernel.order)~=kernel.role then value_error('KERNEL-POLICY-UNVERIFIED') end
  local old=getd(state,'selected_policy',canon.object({}))
  if old.role==kernel.role and old.hash==kernel.policy_hash and same_list(old.order,kernel.order) then return false end
  state.selected_policy=canon.object({role=kernel.role,order=copy_list(kernel.order),hash=kernel.policy_hash,since=kernel.time})
  M.save(env,state);return true
end

-- Record a dispatched automatic switch. limited=false (leaving a failed path) ignores the attempt count:
-- only the cooldown spacing applies; it bounds retries of a failed attempt (<=15 per 15 min, the ledger size).
-- failover=false: a charge flap damping does not count (M.failover_events): a kernel repair, the return of pair_return.
function M.charge_attempt(env,settings,revision,limited,failover)
  M.require_running(env,revision)
  local now=env.run.wall();local policy=M.recovery_normalized(settings)
  local events,allowed=M.budget(ledger_events(env,now),now,policy.attempt_window*60,policy.attempt_limit)
  local aborted=M.abort_stamps(ledger_aborted(env),now)
  if (limited~=false and not allowed) or (#events>0 and now-num(events[#events])<math.max(policy.cooldown,policy.min_dwell))
     or M.retry_wait(canon.array(aborted),events,now,policy)>0 then refuse('PAIR-RATE-LIMIT') end
  M.ledger_charge(env,events,now,failover~=false)
  return now
end

-- configure_lease(): a fresh bounded transaction lease written to the own config (fenced).
function M.configure_lease(env,state)
  M.require_running(env,state.revision)
  local until_=env.run.wall()+180
  local text=canon.repr_float(until_)  -- Python: str(time.time()+180)
  env.run.fenced(state.revision,function() env.backend.write_lease(M.MODE,state.id,text) end)
  return until_
end

local function net(env) if not env.net then value_error('PAIR-NETWORK-UNVERIFIED') end;return env.net end

function M.readopt_allowed(env,now)
  local ledger=ctl.read_json_safe(env.run,env.runtime..'/pair-readopt.json',canon.object({}))
  local events={}
  local raw=canon.is_object(ledger) and ledger.events or nil
  if canon.is_array(raw) then
    for _,x in ipairs(raw) do local v=num(x);if v and finite(v) and 0<=now-v and now-v<900 then events[#events+1]=v end end
  end
  return events,#events<M.READOPT_LIMIT
end

-- Owner decision 07.11.2026 ('by risk + notification', review F-32 / A9 finding 2): a RUNNING session that meets a change
-- made outside the app adopts the current configuration by itself only when the change is proven to touch nothing but
-- ADOPT_PACKAGES (Wi-Fi, DHCP, the GL DNS page) or the network interface/address class of PAIR-EXTERNAL-NETWORK-CHANGE
-- (net.identity without the pair's interfaces; unchanged, not widened). The VPN profiles (wireguard, ovpnclient), the
-- firewall, the pair's route_policy rules (PAIR-EXTERNAL-POLICY-CHANGE, SOURCE-ORDER-MISMATCH), any other package, or a
-- class that cannot be read is HELD: PAIR-OUTSIDE-CHANGE-HELD, the K9 guard stays, only the owner's Start (release_session
-- from control_request / pair_auto.release_for_start) or Stop ends it. Every decision is told: a history event, the status
-- field outside_change (class and package names, never a value), one log line. Python: pair_auto.readopt_class.
M.ADOPT_PACKAGES={wireless=true,dhcp=true,['gl-dns-v2']=true}
M.ADOPT_CODE='PAIR-OUTSIDE-CHANGE-ADOPTED'
M.HOLD_CODE='PAIR-OUTSIDE-CHANGE-HELD'

function M.changed_packages(env,state,observed)
  local n=net(env)
  local names={}
  for name in pairs(state.protected) do if name~='route_policy' then names[#names+1]=name end end
  table.sort(names)
  local out={}
  for _,name in ipairs(names) do
    local skip={}
    for _,other in ipairs(names) do if other~=name then skip[other]=true end end
    if n.changed(state,observed,skip) then out[#out+1]=name end
  end
  return out
end

function M.readopt_class(env,state,code,now)
  local row=canon.object({decision='HOLD',trigger=code,packages=canon.array({}),why='UNCLASSIFIED',time=canon.float(now or env.run.wall())})
  if code~='PAIR-EXTERNAL-NETWORK-CHANGE' and code~='PAIR-EXTERNAL-CONFIG-CHANGE' then
    row.packages=canon.array({'route_policy'});row.why='POLICY-OR-ORDER';return row
  end
  local ok,packages=pcall(function() return M.changed_packages(env,state,net(env).configs(M.state_interfaces(state))) end)
  if not ok then row.why='UNREADABLE';return row end
  if code=='PAIR-EXTERNAL-NETWORK-CHANGE' then table.insert(packages,1,'network') end
  row.packages=canon.array(packages)
  if #packages==0 then return row end
  for _,name in ipairs(packages) do if name~='network' and not M.ADOPT_PACKAGES[name] then row.why='FOREIGN-PACKAGES';return row end end
  row.decision='ADOPT';row.why='ADOPT-PACKAGES-ONLY'
  return row
end

local function outside_change_log(verdict,adopted_by)
  pcall(function()
    local names={};for _,x in ipairs(verdict.packages) do names[#names+1]=x end
    require('durable').log((verdict.decision=='ADOPT' and M.ADOPT_CODE or M.HOLD_CODE)..': '..tostring(verdict.trigger)..' by '..(adopted_by or 'automatic')
      ..', packages '..(#names>0 and table.concat(names,' ') or '-')..' ('..tostring(verdict.why)..')')
  end)
end

-- Owner decision 07.11.2026: the decision goes to the Telegram sender's RAM ring (telegram.outside_push), told on its next
-- round. One local write, never the network, never raises. Python: pair_auto.outside_notice.
local function outside_notice(env,verdict)
  pcall(function()
    local tg=require('telegram')
    local path=env.runtime..'/'..tg.OUTSIDE_FILE
    local okc,mono=pcall(env.run.clock)  -- BH-05: the monotonic stamp the sender ages the item by
    ctl.write_json(env.run,path,tg.outside_push(ctl.read_json_safe(env.run,path,canon.object({})),verdict,okc and mono or nil))
  end)
end

-- adopted_by='owner-stop' (M.end_hold_on_stop): the owner's Stop ends the hold - no adoption, outside the readopt budget.
function M.release_session(env,state,code,verdict,adopted_by)
  local now=env.run.wall()
  adopted_by=adopted_by or 'owner-start'
  local stop=adopted_by=='owner-stop'
  if verdict==nil then
    verdict=canon.object({decision=stop and 'STOP' or 'ADOPT',trigger=code,packages=canon.array({}),why=stop and 'OWNER-STOP' or 'OWNER-START',time=canon.float(now)})
    if canon.is_object(state.outside_change) and canon.is_array(state.outside_change.packages) then
      verdict.packages=canon.array(copy_list(state.outside_change.packages))  -- the hold's classification, no values
    end
  end
  local events,allowed=M.readopt_allowed(env,now)
  local phase=T.journal_read(env).phase
  if (not allowed and not stop) or (phase~=nil and phase~='ROLLED-BACK') then return false end
  local _,path=M.paths(env)
  local raw=env.run.fs.read(path)
  local directory=env.persist..'/session-recovery'
  local archive=directory..'/pair-'..state.id..(stop and '-stop-' or '-readopt-')..string.format('%d',math.floor(now))..'.json'
  if env.run.fs.read(archive)~=nil then value_error('PAIR-STATE-UNVERIFIED') end
  env.run.fs.write_atomic(archive,raw)
  if env.run.fs.read(archive)~=raw then value_error('PAIR-STATE-UNVERIFIED') end
  local resolved=canon.decode(canon.encode(state))
  resolved.phase='STOPPED';resolved.owned=canon.array({});resolved.original_restored=false;resolved.recovery_error=NULL
  resolved.operator_resolution=canon.object({reason='AUTOMATIC-EXTERNAL-CHANGE-READOPT',time=canon.float(now),archive=string.match(archive,'[^/]+$'),
    trigger=code,original_sha256=canon.sha256(raw),retired_owned=copy_list(getd(state,'owned',canon.array({}))),old_flags_restored=false,
    adopted_by=adopted_by,outside_change=verdict})
  resolved.outside_change=nil
  M.save(env,resolved)
  if not stop then  -- the owner's Stop adopts nothing: it never spends (nor is refused by) the 3/900 s adoption budget
    local list={};for i,x in ipairs(events) do list[i]=canon.float(x) end;list[#list+1]=canon.float(now)
    ctl.write_json(env.run,env.runtime..'/pair-readopt.json',canon.object({events=canon.array(list)}))
  end
  outside_change_log(verdict,adopted_by)
  if adopted_by=='owner-stop' or adopted_by=='owner-start' then  -- owner decision 07.11.2026: the hold the owner ended is told (class RELEASE)
    outside_notice(env,canon.object({decision='RELEASE',release=stop and 'STOP' or 'START',trigger=code,why=verdict.why,packages=verdict.packages,time=canon.float(now)}))
  end
  return true
end

function M.readopt_running(env,state,request_row,revision,code)
  local verdict=M.readopt_class(env,state,code)
  if verdict.decision~='ADOPT' then
    -- HOLD (owner decision 07.11.2026): the record says why under the control lock; publish_failure then writes the same
    -- HELD code (no second write) and carries the class into the status. Start or Stop are the only ways out.
    env.run.lock(function()
      local ok,pending=pcall(M.read_state,env)
      if ok and next(pending)~=nil and pending.id==state.id and not M.TERMINAL[pending.phase] then
        pending.phase='HELD';pending.recovery_error=code;pending.outside_change=verdict;M.save(env,pending)
      end
    end,env.runtime)
    outside_change_log(verdict,nil)
    outside_notice(env,verdict)
    return false
  end
  local handed=env.run.lock(function()
    local current=M.intent(env)
    if ctl.revision_locked(env)~=revision or current.revision~=revision or current.mode~='on' or current.id~=request_row.id or not M.release_session(env,state,code,verdict,'automatic') then return false end
    ctl.write_json(env.run,(M.paths(env)),canon.object({mode='on',revision=revision,time=fwall(env),id=ctl.uuid_hex(),request_source=getd(current,'request_source','unknown')}))
    return true
  end,env.runtime)
  if not handed then return false end
  outside_notice(env,verdict)  -- the ARMED status lasts seconds: the Telegram ring keeps the ADOPT for the next round
  T.publish(env,{state='ARMED',mode='continuous-pair',proof_scope=M.MODE,reason='PAIR-READOPTED',blockers=canon.array({}),outside_change=verdict})
  return true
end

------------------------------------------------------------------------------------------------------
-- begin / cleanup / revive (network side through env.net)
------------------------------------------------------------------------------------------------------
function M.preflight(env,settings)
  if settings.pair_auto_mode~=M.MODE or settings.terms_version~=require('terms') then value_error('PAIR-MODE-NOT-CONFIGURED') end
  if settings.native_session_loss~='1' then value_error('SESSION-LOSS-NOT-ACCEPTED') end
  local selection=env.backend.pair_preflight(settings)  -- platform pins, acceleration, assess(), choose(), pair_interfaces.selection
  T.bind_policy_context(env,selection)
  return selection
end

function M.begin(env,settings,request)
  local selection=M.preflight(env,settings)
  -- Owner 05.11.2026: a Start with an unaccepted key on the channel that carries the traffic afterwards (the source, or the
  -- reserve of a boot handover: T.carrying_unaccepted) takes nothing: no session, no guard, no ifup. A key on the other channel
  -- lets it go, the directional gate keeps the pair off that channel. The owner's Start and the boot resume alike; the refusal
  -- ends the request through M.fail_request. Python: pair_auto.begin.
  local pinned=T.carrying_unaccepted(env,selection)
  if pinned then refuse(pinned) end
  local n=net(env)
  local managed=env.backend.selection_interfaces(selection)
  local data=n.network()
  local selected={}
  local count=0
  for _,row in ipairs(data) do if managed[row['.name']] then selected[row['.name']]=row;count=count+1 end end
  local mcount=0;for _ in pairs(managed) do mcount=mcount+1 end
  if count~=mcount then value_error('PAIR-PROFILES-UNVERIFIED') end
  for name,row in pairs(selected) do
    if row.proto~=managed[name] or row.auto~='0' or (row.disabled~='0' and row.disabled~='1') then value_error('PAIR-PROFILES-UNVERIFIED') end
  end
  local flags=canon.object({});for name,row in pairs(selected) do flags[name]=row.disabled end
  -- variant D: a boot handover on the reserve is adopted only after a fresh check of everything (else the old path)
  local handover=nil
  local hok,hprior=pcall(M.read_state,env)
  if hok and M.has_handover(hprior) then
    local jok,value=pcall(T.journal_read,env)
    if jok and M.handover_matches(hprior,value) then
      local cok,kernel=pcall(M.adoptable,env,selection,value,hprior)
      if not cok or kernel==nil then M.release_handover(env,hprior);value_error('BOOT-RESERVE-UNVERIFIED') end
      handover={prior=hprior,value=value,kernel=kernel}
    end
  end
  -- the clients a boot cleanup kept up for this Start (M.boot_keep) stay owned, with their flags before the old session:
  -- a later Stop returns them exactly as the old cleanup would have. Everything else of the session is read fresh here.
  local adopted=canon.array({})
  local pok,prior=pcall(M.read_state,env)
  if pok and M.has_kept(prior) then
    for _,name in ipairs(prior.kept) do
      if selected[name] and selected[name].disabled=='0' then adopted[#adopted+1]=name;flags[name]=prior.kept_flags[name] end
    end
  end
  local state=canon.object({id=request.id,phase='STARTING',started=fwall(env),revision=request.revision,network_identity=n.identity(data,managed),
    interfaces=managed,protected=n.configs(managed),owned=adopted,before_flags=flags,process_bindings=getd(selection,'process_bindings',NULL),
    order=copy_list(handover and handover.prior.handover.order or selection.order),policy_hash=selection.hash})
  pcall(function() state.protected_static=canon.object({firewall=n.static_firewall_digest()}) end)
  state.policy_roles=P.proof(selection)
  M.save(env,state)
  -- K4 (formal model 03.11.2026): the full block releases itself after GUARD_RELEASE_SECONDS (90 s), but bringing
  -- both clients up takes up to ~170 s (quiet 20 + ifup -w + quiet 45 per role). The guard is therefore re-armed
  -- before every bounded step (each well below 90 s): never a moment without a guard while the clients start, and
  -- the kernel still releases the block 90 s after a lost process. A VPN-only guard already standing - the boot
  -- handover's held reserve (proven up), or the outside-change hold this Start ends (K9) - is kept VPN-only on the
  -- tunnels that are up, never downgraded to the self-releasing full block.
  local keep_vpn=handover~=nil or (M.outside_guard_mode()=='vpn' and env.backend.guard_exists())
  M.outside_guard_reset()
  local function hold_guard()
    if keep_vpn then
      local ok,devices=pcall(env.backend.devices)
      if ok and type(devices)=='table' and #devices>0 then env.backend.guard(devices);return end
    end
    env.backend.guard()
  end
  hold_guard()
  for index,role in ipairs({'source','target'}) do
    local interface=selection[role].interface
    M.require_running(env,request.revision)
    if index>1 then hold_guard() end
    n.quiet(20,request.revision)
    if selected[interface].disabled=='1' then
      state.owned[#state.owned+1]=interface;M.save(env,state)
      hold_guard()
      n.set_disabled(state,interface,'0',request.revision)
      n.ifup(interface,request.revision)
      hold_guard()
      n.quiet(45,request.revision)
    elseif n.client_down(interface) then
      if not index_of(state.owned,interface) then state.owned[#state.owned+1]=interface;M.save(env,state) end
      hold_guard()
      pcall(n.ifup,interface,request.revision)
      hold_guard()
      n.quiet(45,request.revision)
    end
  end
  state.phase='RUNNING';state.ran=true
  M.require_running(env,request.revision)
  env.backend.guard(env.backend.devices(),request.revision)
  M.save(env,state)
  if handover then M.adopt_journal(env,state,handover.value,handover.kernel,request.revision) end
  return state
end

-- 01.11.2026: the boot recovery trace (durable.boot_step, only while the boot is young)
local function boot_step(env,step)
  local ok,now=pcall(env.run.clock)
  if ok then pcall(function() require('durable').boot_step(now,step) end) end
end

-- Owner decision 01.11.2026 (variant C, BOOT-RECOVERY-2026-11-01.ru.md; physical power cuts on beta1): the boot
-- cleanup stopped the pair's two healthy clients (ifdown + vendor quiet, ~20 s) only for the boot resume's Start to
-- bring them up again. Now, when the boot resume will press Start (the owner's marker, no newer Stop latch, the boot
-- resume not finished, uptime below BOOT_KEEP_UPTIME) and every owned client is up, the cleanup keeps them: the route
-- is restored and verified exactly as before (rollback / finish_committed, order_is), the session ends STOPPED and
-- records the kept clients with their flags before the session (kept, kept_flags, kept_at). The next Start's begin()
-- adopts them as owned and reads everything else fresh (preflight, identity, configs, the kernel attestation of the
-- running session), so no tunnel identity of the old session is reused. Without that Start within KEEP_SECONDS (or
-- after a Stop, a failed boot resume, the boot window) release_kept() stops them as the old cleanup would have.
-- An owner Stop (stop_revision) and any client that is not up keep the old behaviour. Python: pair_auto.boot_keep.
M.BOOT_KEEP_UPTIME=900   -- boot_resume.UNTIL_UPTIME
M.KEEP_SECONDS=600
function M.has_kept(state) return canon.is_object(state) and state.phase=='STOPPED' and canon.is_array(state.kept) and #state.kept>0 end
-- pending, uptime, and the reason when not pending (the handover refusal log)
-- tx (03.11.2026, forward_resume.lua): this supervisor's recovery finished the switch tx on the reserve after a restart
-- without a boot; the monitor's restart resume (boot_resume token) presses Start for it, so neither the boot window
-- nor this boot's resume state applies - only the owner's marker and Stop latch, and the marker's KEEP_SECONDS.
-- (2.1.0-alpha7 fix, 03.11.2026: also a refused resume of tx - the restart Start comes all the same; the handover itself
-- still needs a finished one, see boot_handover)
local function resume_pending(env,tx)
  local ok,now=pcall(env.run.clock)
  local forward=tx~=nil and ok and type(now)=='number' and require('forward_resume').restarted(env,tx)
  if not forward and (not ok or type(now)~='number' or now<0 or now>=M.BOOT_KEEP_UPTIME) then return false,now,'UPTIME' end
  local br=require('boot_resume')
  local wok,wanted,why=pcall(br.wanted,function(p) return env.run.fs.read(p) end,env.persist)
  if not wok then return false,now,'RESUME-MARKER-UNREADABLE' end
  if not wanted then return false,now,tostring(why or 'AUTO-RESUME-NOT-REQUESTED') end
  if forward then
    -- the restart resume of this supervisor start (its token) that failed or skipped ends the wait
    local row=ctl.read_json_safe(env.run,env.runtime..'/'..br.STATE,canon.object({}))
    local token=br.token(function(p) return env.run.fs.read(p) end,env.runtime)
    if token~=nil and canon.is_object(row) and row.supervisor==token and (row.state=='FAILED' or row.state=='SKIPPED') then
      return false,now,'RESUME-'..row.state
    end
    return true,now
  end
  local row=ctl.read_json_safe(env.run,env.runtime..'/'..br.STATE,canon.object({}))
  if canon.is_object(row) and (row.state=='FAILED' or row.state=='SKIPPED') then return false,now,'RESUME-'..row.state end
  return true,now
end
-- tx: the journal's transaction; when this supervisor start ran its forward resume (forward_resume.restarted), the
-- restart Start replaces the boot window (MT3000 2.1.0-alpha7: a refused resume tore the healthy reserve down)
function M.boot_keep(env,state,stop_revision,tx)
  if stop_revision~=nil or not canon.is_array(state.owned) or #state.owned==0 or not resume_pending(env,tx) then return false end
  local n=env.net
  for _,interface in ipairs(state.owned) do
    local ok,up=pcall(function() return n.interface_exists(interface) and not n.client_down(interface) end)
    if not (ok and up) then return false end
  end
  return true
end
function M.kept_valid(env,state,tx)
  local pending,now=resume_pending(env,tx)
  local at=num(state.kept_at)
  return pending and at~=nil and at<=now and now-at<M.KEEP_SECONDS
end
-- release_kept(): the kept clients are stopped and their flags restored, as the old boot cleanup would have done
function M.release_kept(env,state)
  local n=net(env)
  local managed=M.state_interfaces(state)
  for i=#state.kept,1,-1 do
    local interface=state.kept[i]
    if n.identity(n.network(),managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed),{firewall=true}) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
    n.ifdown(interface)
    n.quiet(45)
    n.set_disabled(state,interface,state.kept_flags[interface])
    if n.interface_exists(interface) then value_error('PAIR-PROFILE-STOP-UNVERIFIED') end
  end
  env.backend.unguard()
  state.kept=nil;state.kept_flags=nil;state.kept_at=nil;state.kept_tx=nil;M.save(env,state)
  boot_step(env,'pair kept clients released')
end

-- Owner decision 01.11.2026 (variant D, BOOT-RECOVERY-2026-11-01.ru.md; physical power cuts on beta1): after a boot
-- with a completed switch on the reserve (journal COMMITTED or HELD-ON-RESERVE, current role target) the cleanup
-- waited ~60-130 s for the primary proof (primary_successes + primary_stable) before it could end the session, and
-- only then the boot resume's Start was accepted. Now, when the boot resume will press Start and the reserve route
-- is proven freshly (attest_policy verified with role target, the reserve healthy by a fresh probe, the live order
-- the journal's), the old session hands over: it ends STOPPED with handover={tx,order,policy_hash,at} (and its kept
-- clients, variant C), the guard stays VPN-only, the journal is untouched. Start accepts exactly this journal; the
-- new session's begin() checks everything again (preflight, the journal's policy identity, the live order, the
-- kernel proof role target, the reserve health) and then records the adoption in the journal (COMMITTED,
-- BOOT-RESERVE-ADOPTED, boot_adopted={session,time,from_phase,from_reason}, confirmed=now so min_dwell counts from
-- here, no manual request). From there the normal committed return policy (committed_recovery_decision:
-- recovery_ready = primary_successes + primary_stable, min_dwell) brings it back to the primary. Any failed check,
-- an owner Stop, no Start within KEEP_SECONDS, a failed boot resume: release_handover() and today's path (cleanup,
-- finish_committed, the primary-proof wait). Interrupted switches (ARMED/APPLYING/WAIT-CLIENT/RESTORING) never get
-- here: they roll back as before (03.11.2026: unless forward_resume.lua finished one after a restart without a boot;
-- that COMMITTED journal gets its own handover, see resume_pending). One handover per boot (RAM marker). Python:
-- pair_auto.boot_handover.
M.HANDOVER_FILE='pair-handover.json'
function M.has_handover(state) return canon.is_object(state) and state.phase=='STOPPED' and canon.is_object(state.handover) end
function M.handover_matches(state,value)
  return M.has_handover(state) and canon.is_object(value) and state.handover.tx==value.tx and (value.phase=='COMMITTED' or value.phase=='HELD-ON-RESERVE')
end
-- the reserve route the old session left, freshly: kernel proof role target and a healthy reserve; the kernel or nil
local function reserve_proven(env,value,selection)
  local kernel=env.backend.attest_policy(selection)
  if not canon.is_object(kernel) or kernel.verified~=true or kernel.role~='target' then return nil end
  if env.backend.health(value.target)~=true then return nil end
  return kernel
end
-- 01.11.2026 (MT3000 sysrq-b on beta3: no handover, no reason in the log): the checks run on every cleanup pass for
-- at most HANDOVER_WAIT s from the first one (the revive and the vendor need some seconds after the boot), each
-- refusal is logged once per reason (BOOT-RECOVERY-STEP: handover refused <reason>), and after the wait today's path
-- goes on without further checks. The reserve health is the backend's live probe (health(): live_probe or the
-- lua_bridge probe, never the monitor samples). Only the reserve has to be up: the primary may still be connecting
-- (all owned clients are kept and adopted; begin() starts the ones that are down). RAM marker HANDOVER_FILE:
-- {state='waiting',first} -> {state='handed'|'refused'}. Python: pair_auto.boot_handover.
M.HANDOVER_WAIT=60
local handover_logged=nil
local function handover_refused(env,reason)
  if handover_logged~=reason then handover_logged=reason;boot_step(env,'handover refused '..reason) end
  return false
end
function M.handover_log_reset() handover_logged=nil end
-- nil when the reserve route can be handed over, else the refusal reason; the kernel proof as the second value
function M.handover_check(env,state,value,context)
  local role=P.current_role(value)
  if role~='target' then return 'ROLE '..tostring(role) end
  if not same_list(context.session_order,state.order) then return 'SESSION-ORDER' end
  -- a primary already proven returns at once on today's path; the handover only replaces the wait for the proof.
  -- K2 (formal model 03.11.2026): "proven" with the flap-damping hold of the failover ledger, as the running tick
  -- (ledger_hold): a restart must not turn a flapping primary into a proven one
  local settings=env.backend.policy().settings
  local hold=M.ledger_hold(env,settings,env.run.wall())
  if hold>M.recovery_normalized(settings).primary_stable then settings=merge(settings,{recovery_primary_stable=hold}) end
  if env.backend.recovery_ready(value.source,settings)==true then return 'PRIMARY-PROVEN' end
  local lo,lh=env.backend.order()
  if not P.state_order_matches(state,value,lo,lh) then return 'ORDER' end
  local kernel=env.backend.attest_policy()
  if not canon.is_object(kernel) or kernel.verified~=true then return 'KERNEL '..tostring(canon.is_object(kernel) and kernel.code or 'UNVERIFIED') end
  if kernel.role~='target' then return 'KERNEL-ROLE '..tostring(kernel.role) end
  local health=env.backend.health(value.target)
  if health~=true then return 'RESERVE-HEALTH '..tostring(health==nil and 'UNKNOWN' or health) end
  return nil,kernel
end
function M.boot_handover(env,state,value,context,stop_revision)
  if stop_revision~=nil or context==nil or (value.phase~='COMMITTED' and value.phase~='HELD-ON-RESERVE') then return false end
  local path=env.runtime..'/'..M.HANDOVER_FILE
  local marker=ctl.read_json_safe(env.run,path,canon.object({}))
  if not canon.is_object(marker) then marker=canon.object({}) end
  -- one handover per boot; a switch this supervisor finished after a restart (forward_resume) gets its own one
  local forward=require('forward_resume').marked(env,value.tx)
  if forward and marker.tx~=value.tx then marker=canon.object({}) end
  if marker.state=='handed' or marker.state=='refused' then return false end
  local pending,now,why=resume_pending(env,forward and value.tx or nil)
  if not pending then return handover_refused(env,why) end
  local first=num(marker.first)
  if first==nil or first>now then
    first=now
    ctl.write_json(env.run,path,canon.object({state='waiting',first=canon.float(now),tx=forward and value.tx or NULL}))
  end
  if now-first>=M.HANDOVER_WAIT then
    ctl.write_json(env.run,path,canon.object({state='refused',first=canon.float(first),reason=handover_logged or NULL,tx=forward and value.tx or NULL}))
    return handover_refused(env,'WAIT-OVER after '..tostring(handover_logged))
  end
  local ok,reason=pcall(M.handover_check,env,state,value,context)
  if not ok then reason='ERROR '..tostring(is_refused(reason) and reason.code or reason) end
  if reason~=nil then return handover_refused(env,reason) end
  env.backend.guard(env.backend.devices())  -- VPN-only on the running tunnels, as the held journal had
  ctl.write_json(env.run,path,canon.object({state='handed',first=canon.float(first),tx=value.tx,time=fwall(env)}))
  state.handover=canon.object({tx=value.tx,order=copy_list(state.order),policy_hash=state.policy_hash,at=canon.float(env.run.clock())})
  if #state.owned>0 then
    local flags=canon.object({});for _,interface in ipairs(state.owned) do flags[interface]=state.before_flags[interface] end
    state.kept=copy_list(state.owned);state.kept_flags=flags;state.kept_at=state.handover.at
  end
  state.phase='STOPPED';M.save(env,state)
  boot_step(env,'pair cleanup handover on the reserve '..value.tx)
  return true
end
-- boot_handover may still act on this journal (a read of its first gates)
local function handover_open(env,value)
  local marker=ctl.read_json_safe(env.run,env.runtime..'/'..M.HANDOVER_FILE,canon.object({}))
  if not canon.is_object(marker) then marker=canon.object({}) end
  local forward=require('forward_resume').marked(env,value.tx)
  if forward and marker.tx~=value.tx then marker=canon.object({}) end
  if marker.state=='handed' or marker.state=='refused' then return false end
  return (resume_pending(env,forward and value.tx or nil))
end
-- T4 (trace conformance 04.11.2026, as finding 3 for the outside-change hold): a session HELD on a HELD-ON-RESERVE journal
-- that waits for its primary (a Stop on a dead primary, K8; also with an edit in the GL panel visible) wrote STOPPING, the
-- journal and HELD on every pass, about every 2 s for as long as the primary was down. Read-only: true when this pass would
-- change nothing (the cleanup then writes no file). Any doubt: false, the full cleanup. Python: pair_auto.reserve_waits.
function M.reserve_waits(env,state,value,context,stop_revision)
  if stop_revision~=nil or context==nil or state.phase~='HELD' or state.server_change~=nil or value.phase~='HELD-ON-RESERVE' then return false end
  local ok,result=pcall(function()
    local devices=env.backend.devices()
    if type(devices)~='table' or #devices==0 or handover_open(env,value) then return false end
    return T.hold_unchanged(env,value,'PAIR-STOPPED',state.order,M.cleanup_hold(env,state,value,stop_revision))
  end)
  return ok and result==true
end
-- back to today's path: the old session is HELD again and the next cleanup waits for the primary proof as before
function M.release_handover(env,state)
  state.handover=nil;state.kept=nil;state.kept_flags=nil;state.kept_at=nil;state.kept_tx=nil
  state.phase='HELD';M.save(env,state)
  boot_step(env,'pair handover released')
end
-- begin(): the fresh checks of the adoption; the kernel proof or nil
function M.adoptable(env,selection,value,prior)
  local ctx=P.metadata(value)
  if ctx==nil or selection.hash~=value.hash or selection.hash~=prior.handover.policy_hash then return nil end
  if getd(selection.source,'id',nil)~=value.source or getd(selection.target,'id',nil)~=value.target then return nil end
  if not same_list(ctx.session_order,prior.handover.order) or not same_set(selection.order,prior.handover.order) then return nil end
  for key,item in pairs(P.proof(selection)) do if canon.encode(getd(ctx,key,NULL))~=canon.encode(item) then return nil end end
  local lo,lh=env.backend.order()
  if not same_list(lo,P.current_order(value)) or lh~=value.hash or P.current_role(value)~='target' then return nil end
  return reserve_proven(env,value,selection)
end
-- the new session's journal says where it started: on the reserve, adopted at this boot
function M.adopt_journal(env,state,value,kernel,revision)
  local now=fwall(env)
  value.boot_adopted=canon.object({session=state.id,time=now,from_phase=value.phase,from_reason=getd(value,'reason',NULL)})
  value.phase='COMMITTED';value.reason='BOOT-RESERVE-ADOPTED';value.confirmed=now;value.control_revision=revision
  value.manual_request_id=nil
  T.journal_write(env,value)
  pcall(M.remember_selected,env,state,kernel)
  T.publish(env,{state='COMMITTED',reason='BOOT-RESERVE-ADOPTED',source=value.source,target=value.target,mode='continuous-pair',proof_scope=M.MODE,
    readiness_verified=true,kernel_policy_verified=true,kernel_proof=kernel,original_restored=false,blockers=canon.array({})})
  boot_step(env,'pair session adopted the reserve '..value.tx)
end

-- owner_stopped(state): a Stop (or a give-up) is newer than the last Start of this session - the stop latch
-- native-stop.json against the later of the owner's resume marker auto-resume.json (boot_resume.wanted's decision)
-- and the session's own start (state.started: a programmatic Start leaves no marker, an older latch is not its Stop).
-- A damaged latch is not a Stop (the guard of the outside-change hold is never dropped on a damaged file). Python:
-- pair_auto.owner_stopped.
function M.owner_stopped(env,state)
  local read=function(p) return env.run.fs.read(p) end
  local ok,text=pcall(read,env.persist..'/native-stop.json')
  if not ok or text==nil then return false end
  local dok,latch=pcall(canon.decode,text)
  local stopped=dok and canon.is_object(latch) and num(latch.requested) or nil
  if stopped==nil or not finite(stopped) then return false end
  local mok,mtext=pcall(read,env.persist..'/'..require('boot_resume').MARKER)
  local at=nil
  if mok and mtext~=nil then
    local mdok,marker=pcall(canon.decode,mtext)
    at=mdok and canon.is_object(marker) and marker.enabled==true and num(marker.time) or nil
    if at~=nil and not finite(at) then at=nil end
  end
  local started=canon.is_object(state) and num(state.started) or nil
  if started~=nil and finite(started) and (at==nil or started>at) then at=started end
  return at==nil or stopped>=at
end

-- K2 (formal model 03.11.2026): the cleanup of a committed/held reserve that no owner Stop asked for (a recovery
-- after a crash or a power cut, a released handover) returns to the primary only after the flap-damping hold of
-- the failover ledger, exactly as the running tick (ledger_hold, committed_recovery_decision): the restart must not
-- reset a hold that was doubled by a flapping primary. A failing reserve is left without the damped hold (as the
-- tick), and an owner Stop returns as before. nil = no damping. Python: pair_auto.cleanup_hold.
function M.cleanup_hold(env,state,value,stop_revision)
  if stop_revision~=nil or M.owner_stopped(env,state) then return nil end
  local settings=env.backend.policy().settings
  local hold=M.ledger_hold(env,settings,env.run.wall())
  if hold<=M.recovery_normalized(settings).primary_stable then return nil end
  if env.backend.health(value.target)~=true then return nil end
  return hold
end

-- K9, owner decision 03.11.2026 (formal model): a session HELD by a change made outside the app (a readopt code;
-- the cleanup stops before its guard step) keeps the LAN behind the VPN-only guard until the owner presses Start
-- (pair_auto.release_for_start hands it over) or Stop. Before, a power cut dropped the guard (RAM) and the recovery
-- never put it back: the LAN went out through the GL configuration without the VPN. Only with a settled journal
-- (none or ROLLED-BACK; a held journal keeps its own guard rules). VPN-only on the tunnels that are up; with no
-- tunnel up the full block, re-armed every OUTSIDE_REARM s (it still releases itself 90 s after a lost process).
-- The owner's Stop (owner_stopped) releases the guard. Called after a failed recovery or cleanup of a session that
-- is not running; returns true when the session is such a hold. Python: pair_auto.outside_hold.
M.OUTSIDE_REARM=45
local outside_guard={}

-- Owner rule 07.11.2026 (T4-A, router/tests/T4A-NOTE.md): a session HELD by an outside change stays held until the owner
-- presses Stop and then Start; the Stop itself ends STOPPED. Before, the Stop only released the K9 guard (outside_hold)
-- and the record stayed HELD with its readopt code - since F-32 holds a foreign route_policy change instead of adopting
-- it, every Stop after such a change ended HELD. The record is retired exactly as the owner's Start retires it
-- (release_session: archived, owned=[] - a profile is never stopped after an outside change), under the control lock,
-- only while Auto is off and this session's Stop latch stands, with a settled journal. Python: pair_auto.end_hold_on_stop.
function M.end_hold_on_stop(env,state)
  return env.run.lock(function()
    local ok,current=pcall(M.read_state,env)
    if not ok or not canon.is_object(current) or current.id~=state.id or current.phase~='HELD' or not M.READOPT_CODES[current.recovery_error]
      or M.intent(env).mode=='on' or not M.owner_stopped(env,current) then return false end
    return M.release_session(env,current,current.recovery_error,nil,'owner-stop')
  end,env.runtime)
end
local orphan_seen=nil
function M.outside_guard_reset() outside_guard={};orphan_seen=nil end
function M.outside_guard_mode() return outside_guard.mode end
function M.outside_hold(env)
  local state=M.read_state(env)
  if not (canon.is_object(state) and state.phase=='HELD' and M.READOPT_CODES[state.recovery_error]) then return false end
  local phase=T.journal_read(env).phase
  if phase~=nil and phase~='ROLLED-BACK' then return false end
  local B=env.backend
  if M.owner_stopped(env,state) then
    outside_guard={}
    if B.guard_exists() then
      B.unguard()
      pcall(function() require('durable').log('PAIR-OUTSIDE-CHANGE-GUARD: released by the owner Stop') end)
    end
    if M.end_hold_on_stop(env,state) then  -- T4-A: the Stop ends STOPPED; the next Start begins a new session
      T.publish(env,{state='STOPPED',mode='continuous-pair',proof_scope=M.MODE,original_restored=false,blockers=canon.array({})})
    end
    return true
  end
  local ok,devices=pcall(B.devices)
  local list=nil
  if ok and type(devices)=='table' and #devices>0 then list=copy_list(devices);table.sort(list) end
  local now=env.run.clock()
  local exists=B.guard_exists()
  if list then
    local key=table.concat(list,' ')
    if not exists or outside_guard.mode~='vpn' or outside_guard.key~=key then
      B.guard(list);outside_guard={mode='vpn',key=key,at=now}
      pcall(function() require('durable').log('PAIR-OUTSIDE-CHANGE-GUARD: VPN-only '..key..' until Start or Stop') end)
    end
  elseif not exists or outside_guard.mode~='full' or now-outside_guard.at>=M.OUTSIDE_REARM then
    local first=outside_guard.mode~='full'
    B.guard();outside_guard={mode='full',at=now}
    if first then pcall(function() require('durable').log('PAIR-OUTSIDE-CHANGE-GUARD: no VPN tunnel up, LAN blocked until Start or Stop') end) end
  end
  return true
end

-- Review 04.11.2026 (finding 5): a session that owns no interface (its clients were already up when it started) had no
-- network/configuration check left in cleanup: a K9 hold with PAIR-EXTERNAL-NETWORK-/CONFIG-CHANGE ended STOPPED and
-- unguarded on the next pass, against the owner decision "the guard stays until Start or Stop". Until the owner's Stop
-- (or Start) the change is checked again exactly as for owned interfaces. Python: pair_auto.outside_recheck.
M.OUTSIDE_RECHECK_CODES={['PAIR-EXTERNAL-NETWORK-CHANGE']=true,['PAIR-EXTERNAL-CONFIG-CHANGE']=true}
function M.outside_recheck(env,state,stop_revision)
  return stop_revision==nil and canon.is_object(state) and state.phase=='HELD' and M.OUTSIDE_RECHECK_CODES[state.recovery_error]==true
    and not M.owner_stopped(env,state)
end

-- Review 04.11.2026 (finding 3): the refusal the cleanup of a session HELD by an outside change would raise before its
-- first action, found read-only - or nil (the full cleanup runs). Before, every pass of a stable hold wrote STOPPING and
-- then HELD again (publish_failure), about every 2 s for as long as the hold lasted: flash writes, and this supervisor's
-- after-stop key (backend.lua: it holds the state file's identity) started python3 on every pass. Python: held_unchanged.
function M.held_unchanged(env,state,value,context,stop_revision)
  if stop_revision~=nil or state.phase~='HELD' or not M.READOPT_CODES[state.recovery_error] or state.server_change~=nil then return nil end
  if value.phase~=nil and value.phase~='ROLLED-BACK' then return nil end
  if not order_is(env,state.order,state.policy_hash) then
    local lo,lh=env.backend.order()
    if context~=nil and P.state_order_matches(state,value,lo,lh) then return nil end  -- the cleanup rolls back
    return 'PAIR-EXTERNAL-POLICY-CHANGE'
  end
  if not ((canon.is_array(state.owned) and #state.owned>0) or M.outside_recheck(env,state)) then return nil end
  local n=net(env)
  local managed=M.state_interfaces(state)
  if n.identity(n.network(),managed)~=state.network_identity then return 'PAIR-EXTERNAL-NETWORK-CHANGE' end
  if n.changed(state,n.configs(managed),{firewall=true}) then return 'PAIR-EXTERNAL-CONFIG-CHANGE' end
  return nil
end

-- Review 04.11.2026 (finding 4): the owner's Start hands a session HELD by an outside change over (release_for_start:
-- STOPPED, owned=[]) and the next session's begin() takes the K9 VPN-only guard over. A Start refused after that
-- hand-over (agent.py: pair_auto.release_orphan_guard releases it then) or ended before its request left the guard with
-- no session: no internet on the LAN while it is routed via WAN, and the owner's Stop did not release it (the journal
-- path needs the restored order). This supervisor releases it after the owner's Stop (once per handed-over record).
-- Only that guard: a STOPPED handed-over record that owns nothing, no kept/handover clients, intent not 'on', journal
-- absent or ROLLED-BACK. Python: pair_auto.release_orphan_guard.
local function orphan_candidate(state)
  local resolution=canon.is_object(state) and state.operator_resolution or nil
  return canon.is_object(state) and state.phase=='STOPPED' and not (canon.is_array(state.owned) and #state.owned>0)
    and state.kept==nil and state.handover==nil
    and canon.is_object(resolution) and resolution.reason=='AUTOMATIC-EXTERNAL-CHANGE-READOPT'
end
function M.release_orphan_guard(env,state)
  if not orphan_candidate(state) then return false end
  local key=tostring(state.id)..'|'..tostring(num(state.operator_resolution.time))
  if orphan_seen==key then return false end  -- looked at once after the Stop: nothing installs this guard again
  if not M.owner_stopped(env,state) then return false end
  local B=env.backend
  local released=env.run.lock(function()
    local current=M.read_state(env)
    if not orphan_candidate(current) or M.intent(env).mode=='on' then return false end
    local phase=T.journal_read(env).phase
    if phase~=nil and phase~='ROLLED-BACK' then return false end
    if not B.guard_exists() then return false end
    B.unguard()
    return true
  end,env.runtime)
  orphan_seen=key
  if released then
    outside_guard={}
    pcall(function() require('durable').log('PAIR-OUTSIDE-CHANGE-GUARD: released, the handed-over session ended without a new one (owner Stop)') end)
  end
  return released
end

function M.cleanup(env,state,stop_revision)
  local n=net(env)
  local managed=M.state_interfaces(state)
  T.bind_policy_context(env,state)
  if state.server_change~=nil then M.server_resume(env,state) end  -- a server change cut short: adopt this supervisor's own write
  local value=T.journal_read(env)
  local context=P.metadata(value)
  if context~=nil and (not same_list(context.session_order,state.order) or value.hash~=state.policy_hash) then
    -- T4 (trace conformance 04.11.2026): a finished journal of the policy before an outside change is no claim on this
    -- session (the Start after the change adopted the new policy): its Stop ended HELD instead of STOPPED until the next
    -- Start. Only a journal still in progress is one; the live order is checked below for both. Python: pair_auto.cleanup.
    if value.phase~=nil and value.phase~='ROLLED-BACK' then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
    context=nil
  end
  -- K11 (formal model 03.11.2026): the owner's Start hands a session HELD by an outside change over under the control
  -- lock (release_for_start / request -> release_session: archived, STOPPED). A cleanup pass that read the record
  -- before must not write its STOPPING over that hand-over (Start then refused PAIR-RECOVERY-REQUIRED and the session
  -- stayed HELD). The record is read again under the same lock: another session or a finished one (the hand-over's
  -- STOPPED) - this pass ends without a write.
  local recheck=M.outside_recheck(env,state,stop_revision)  -- finding 5: read before the STOPPING write (phase HELD)
  local unchanged=M.held_unchanged(env,state,value,context,stop_revision)  -- finding 3
  local waiting=unchanged==nil and M.reserve_waits(env,state,value,context,stop_revision)  -- T4
  local ours=env.run.lock(function()
    local now=M.read_state(env)
    if canon.is_object(now) and next(now)~=nil and (now.id~=state.id or (M.TERMINAL[now.phase] and not M.TERMINAL[state.phase])) then return false end
    if unchanged==nil and not waiting then state.phase='STOPPING';M.save(env,state) end
    return true
  end,env.runtime)
  if not ours then boot_step(env,'pair cleanup superseded by a hand-over');return false end
  if unchanged~=nil then value_error(unchanged) end  -- the hold is unchanged: nothing written (publish_failure: same code)
  if waiting then
    env.backend.guard(env.backend.devices())  -- the guard follows the tunnels as on every pass; no file is written
    return false
  end
  local phase=value.phase
  boot_step(env,'pair cleanup '..tostring(phase))
  if phase=='ARMED' or phase=='APPLYING' or phase=='WAIT-CLIENT' or phase=='RESTORING' then
    if value.activation_reapply==true and same_list(value.before,value.after) and env.deps and env.deps.activation_finalize then
      env.deps.activation_finalize(env,state,value,true)
    else value_error('PAIR-RECOVERY-REQUIRED') end
  end
  if phase=='COMMITTED' or phase=='HELD-ON-RESERVE' then
    M.ensure_devices(env,state)  -- finish_committed/rollback end with guard(devices()): the pair's own tunnels first
    if M.boot_handover(env,state,value,context,stop_revision) then return true end
    local finished
    local hold=M.cleanup_hold(env,state,value,stop_revision)
    if context~=nil then finished=T.finish_committed(env,value,'PAIR-STOPPED',state.order,hold) else finished=T.finish_committed(env,value,'PAIR-STOPPED',nil,hold) end
    if not finished then state.phase='HELD';M.save(env,state);return false end
  else
    local lo,lh=env.backend.order()
    if context~=nil and P.state_order_matches(state,value,lo,lh) and not order_is(env,state.order,state.policy_hash) then
      M.ensure_devices(env,state)
      if env.backend.recovery_ready(value[P.role(context,state.order)],env.backend.policy().settings)~=true then value_error('PAIR-RECOVERY-REQUIRED') end
      require('rollback').rollback(env,value,'PAIR-STOPPED',state.order)
    end
  end
  if not order_is(env,state.order,state.policy_hash) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
  if M.boot_keep(env,state,stop_revision,value.tx) then
    if n.identity(n.network(),managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed),{firewall=true}) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
    local flags=canon.object({});for _,interface in ipairs(state.owned) do flags[interface]=state.before_flags[interface] end
    -- the guard stays: the next session's begin() guards again, release_kept() removes it
    state.kept=copy_list(state.owned);state.kept_flags=flags;state.kept_at=canon.float(env.run.clock())
    if type(value.tx)=='string' and require('forward_resume').restarted(env,value.tx) then state.kept_tx=value.tx end
    state.phase='STOPPED';M.save(env,state)
    boot_step(env,'pair cleanup kept '..table.concat(state.kept,' '))
    return true
  end
  if recheck and #state.owned==0 then
    if n.identity(n.network(),managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed),{firewall=true}) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
  end
  for i=#state.owned,1,-1 do
    local interface=state.owned[i]
    if n.identity(n.network(),managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed),{firewall=true}) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
    boot_step(env,'pair cleanup ifdown '..interface)
    n.ifdown(interface)
    n.quiet(45)
    boot_step(env,'pair cleanup quiet '..interface)
    n.set_disabled(state,interface,state.before_flags[interface])
    if n.interface_exists(interface) then value_error('PAIR-PROFILE-STOP-UNVERIFIED') end
  end
  if stop_revision==nil then
    env.backend.unguard();state.phase='STOPPED';M.save(env,state)
  else
    env.run.lock(function()
      T.require_control_revision(env,stop_revision)
      local current=M.intent(env)
      if current.mode~='off' or current.revision~=stop_revision then refuse('CLIENT-STOP') end
      env.backend.unguard();state.phase='STOPPED';M.save(env,state)
    end,env.runtime)
  end
  boot_step(env,'pair cleanup done')
  return true
end

function M.recover(env)
  local ok,err=pcall(function()
    M.fence_recovery(env)
    local state=M.read_state(env)
    if next(state)~=nil and not M.TERMINAL[state.phase] then
      if not M.cleanup(env,state) then M.publish_failure(env,'PAIR-RECOVERY-REQUIRED');return false end
    end
    return true
  end)
  if not ok then M.publish_failure(env,err) end
  if not ok or err==false then pcall(M.outside_hold,env) end  -- K9: a session held by an outside change keeps its guard
  if not ok then return false end
  return err
end

function M.revive(env,state,revision,value,rows)
  local n=net(env)
  local phase=value.phase
  if not (phase==nil or phase=='ROLLED-BACK' or phase=='COMMITTED' or phase=='HELD-ON-RESERVE') then return false end
  if env.backend.speed_active and env.backend.speed_active() then return false end
  if env.backend.vendor_busy and env.backend.vendor_busy() then return false end
  local now=env.run.wall()
  local path=env.runtime..'/pair-revive.json'
  local ledger=ctl.read_json_safe(env.run,path,canon.object({}))
  if not canon.is_object(ledger) then ledger=canon.object({}) end
  local by_name={};for _,row in ipairs(rows) do by_name[row['.name']]=row end
  local names={};for name in pairs(M.state_interfaces(state)) do names[#names+1]=name end;table.sort(names)
  for _,interface in ipairs(names) do
    local events={}
    local raw=ledger[interface]
    if canon.is_array(raw) then for _,x in ipairs(raw) do local v=num(x);if v and finite(v) and 0<=now-v and now-v<900 then events[#events+1]=v end end end
    local row=by_name[interface] or {}
    if row.disabled=='0' and not (#events>0 and now-events[#events]<M.REVIVE_PAUSE) and #events<M.REVIVE_LIMIT and n.client_down(interface) then
      local list={};for i,x in ipairs(events) do list[i]=canon.float(x) end;list[#list+1]=canon.float(now)
      ledger[interface]=canon.array(list);ctl.write_json(env.run,path,ledger)
      if not index_of(state.owned,interface) then state.owned[#state.owned+1]=interface;M.save(env,state) end
      local ok=pcall(n.ifup,interface,revision)
      if not ok then return true end
      n.quiet(45,revision)
      env.backend.guard(env.backend.devices(),revision)
      return true
    end
  end
  return false
end

-- Power cut with a held/committed journal (MT3000 sysrq-b, 31.10.2026): after the boot the intent (RAM) is gone,
-- and the prepared router does not start the VPN clients by itself (the vendor autostart is off; the pair starts
-- them). The pair cleanup of a COMMITTED/HELD-ON-RESERVE journal ends with guard(devices()), which refuses an empty
-- device list (UNSAFE-GUARD-DEVICE): the journal stayed held forever and Start refused TRANSACTION-IN-PROGRESS.
-- ensure_devices() starts the pair's two configured clients (the interfaces of the pair state - `interfaces`,
-- not only `owned`: clients that were already up when the session began are not owned, alpha14 cut 31.10.2026)
-- when no tunnel device is up. The checks are begin()'s profile checks: each row exists with its protocol,
-- auto='0' and disabled='0' (a client the operator disabled is never touched), netifd reports it stopped, and the
-- profile definitions (wireguard / ovpnclient configs) are the session's. The whole-network identity and the other
-- protected configs (wireless, dhcp, DNS: the vendor rewrites some at boot, e.g. the repeater) are only logged:
-- they do not change which profile ifup starts. ifup is Stop-fenced by the current control revision, bounded by the
-- shared pair-revive.json budget, then a bounded wait for a device. No guard exists while it waits: the LAN is never
-- blocked by the wait. A client the session did not own stays up after the cleanup (as before the session); an
-- owned one is returned by the cleanup as before. Every skip is logged (PAIR-RECOVERY-REVIVE-SKIPPED, at most once
-- per reason per 5 min). Returns the device list, or nil (the caller goes on and fails with its own code, as
-- before). Never raises.
M.PROFILE_CONFIGS={wireguard=true,ovpnclient=true}
M.SKIP_LOG_EVERY=300
local skip_logged={}
-- busy_seen_step(track, busy, now, observe) -> track, row|nil. observe(scan) -> vendor_busy_seen's row. Monotonic time, counted
-- per mark: a new file or pid starts again. Without a file 'workers' stays once seen: each flip of the reason is a journal write.
function M.busy_seen_step(track,busy,now,observe)
  if not busy then return nil,nil end
  if track and now-track.seen>M.BUSY_SCAN_SECONDS then track=nil end
  track=track or {since=now}
  track.seen=now
  local scan=now-track.since>=M.BUSY_SEEN_SECONDS and (track.scanned==nil or now-track.scanned>=M.BUSY_SCAN_SECONDS)
  if scan then track.scanned=now end
  local ok,row=pcall(observe,scan)
  if not ok or type(row)~='table' or type(row.mark)~='string' or not M.BUSY_CODES[row.kind] then row={kind='unidentified',mark='no-file'} end
  if row.mark~=track.mark then
    track.mark=row.mark;track.mark_since=now;track.kind=row.kind;track.pid=row.pid;track.workers=nil;track.logged=nil
  elseif track.kind=='unidentified' or row.kind~='unidentified' then track.kind=row.kind end
  if scan then track.workers=row.workers end
  if now-track.mark_since<M.BUSY_SEEN_SECONDS then return track,nil end
  return track,{kind=track.kind,pid=track.pid,workers=track.workers,seconds=math.floor(now-track.mark_since)}
end
-- busy_fields(env, blockers, value): adds the code to a BLOCKED publication once a busy lasted. Never raises: only a status
-- text depends on it.
function M.busy_fields(env,blockers,value)
  pcall(function()
    local busy=false
    for _,code in ipairs(blockers) do if code=='VENDOR-WORKER-BUSY' then busy=true end end
    local track,row=M.busy_seen_step(env.busy_track,busy,env.run.clock(),function(scan) return env.backend.vendor_busy_seen(scan) end)
    env.busy_track=track
    if not row or not value then return end
    local code=M.BUSY_CODES[row.kind]
    value.reason=code;value.busy_seconds=row.seconds
    value.vendor_lock_pid=row.pid==nil and NULL or row.pid
    value.vendor_workers=row.workers==nil and NULL or row.workers
    if track.logged~=code then
      track.logged=code
      pcall(function() require('durable').log(code..': VENDOR-WORKER-BUSY for '..row.seconds..' s, lock pid '..tostring(row.pid)..
        ', vendor workers seen '..tostring(row.workers)..'; observed only, Auto stays blocked, no lock touched') end)
    end
  end)
  return value
end

-- Verification gap (MT3000 cut 07.11.2026, alpha8: the owner's lamp showed BLOCKED without a reason for 2-3 s about 12 s
-- and 27 s after an own transition, then came back by itself). A pass whose diagnostic() answers only a short vendor or
-- observation wait (a GL worker holding its tunnel-switch/rtp lock - the lock study of 05.11.2026 measured such
-- only-this-blocker episodes at 2.3 s at most -, or the monitor's next write not there yet) ends before its attestation.
-- Right after a CONFIRMED pass of the same session that pass now keeps the last confirmed publication (state, reason,
-- roles) with verifying=true and the wait codes in verify_blockers; readiness_verified and kernel_policy_verified are
-- false (this pass verified nothing), and the channel path carries the earlier kernel proof with its ORIGINAL time
-- (never renewed). The gap lasts only while that proof is inside its 15 s validity (channel_path valid_for): after it,
-- for any other blocker, or after a BLOCKED/transition, BLOCKED is published exactly as before. No decision is taken
-- in a gap pass (it still ends there). Python twin: pair_auto.verify_gap.
M.VERIFY_GAP_SECONDS=15
M.VERIFY_GAP_BLOCKERS={['VENDOR-WORKER-BUSY']=true,['VENDOR-SETTLING']=true,['OBSERVATION-STALE']=true,
  ['PROFILE-IDENTITY-CHANGED']=true,['VENDOR-IDENTITY-UNKNOWN']=true,['RESERVE-NOT-CONNECTED']=true}
-- IR-02 (integration review 07.11.2026): DEGRADED-ON-RESERVE is a confirmed publication too since the owner decisions of
-- 07.11 (a held pass on the pinned reserve, RESERVE-FAILED / RESERVE-HEALTH-UNKNOWN, carries the kernel proof); without it
-- a short wait right after that pass still fell through to BLOCKED without a reason. Python: pair_auto.VERIFY_GAP_STATES.
M.VERIFY_GAP_STATES={OBSERVING=true,COMMITTED=true,['DEGRADED-ON-RESERVE']=true}
M.VERIFY_GAP_KEEP={'state','reason','source','target','certified','external_lan_verified','vendor_identity','source_failures','reserve_healthy'}
-- verify_gap(previous, blockers, now, roles) -> the publication that keeps the confirmed state, or nil (publish BLOCKED).
-- previous: native-status.json as published; roles: the session's policy_roles (source_id/target_id).
function M.verify_gap(previous,blockers,now,roles)
  if type(blockers)~='table' or blockers==NULL or #blockers==0 then return nil end
  for _,code in ipairs(blockers) do if not M.VERIFY_GAP_BLOCKERS[code] then return nil end end
  if not canon.is_object(previous) or not canon.is_object(roles) then return nil end
  if previous.mode~='continuous-pair' or not M.VERIFY_GAP_STATES[previous.state] then return nil end
  if type(previous.blockers)=='table' and previous.blockers~=NULL and #previous.blockers>0 then return nil end
  if type(previous.source)~='string' or previous.source==previous.target
     or previous.source~=roles.source_id or previous.target~=roles.target_id then return nil end
  local path=previous.channel_path
  if not canon.is_object(path) or path.confirmed~=true or path.kernel_policy_verified~=true or path.transitioning==true
     or path.source_profile_id~=previous.source or path.target_profile_id~=previous.target then return nil end
  local active=path.active_profile_id
  local role=(active==previous.source and 'source') or (active==previous.target and 'target') or nil
  local checked,t=num(path.checked_at),num(now)
  if not role or not finite(checked) or not finite(t) then return nil end
  local age=t-checked
  if age<0 or age>M.VERIFY_GAP_SECONDS then return nil end
  local value={mode='continuous-pair',proof_scope=M.MODE}
  for _,key in ipairs(M.VERIFY_GAP_KEEP) do if previous[key]~=nil then value[key]=previous[key] end end
  local since=num(previous.verifying_since)
  if previous.verifying~=true or not finite(since) or since>t or since<checked then since=t end
  local codes={};for i,code in ipairs(blockers) do codes[i]=code end
  value.blockers=canon.array({});value.verifying=true;value.verifying_since=canon.float(since);value.verify_blockers=canon.array(codes)
  value.readiness_verified=false;value.kernel_policy_verified=false
  value.kernel_proof=canon.object({verified=true,time=path.checked_at,role=role,profile_id=active})
  return value,age
end
-- verify_gap_publish(env, state, blockers): publishes the kept state of a verification gap; false = publish BLOCKED.
-- Never raises (only the status text depends on it); the first pass of a gap leaves one log line naming the wait.
function M.verify_gap_publish(env,state,blockers)
  local ok,value,age,previous=pcall(function()
    local previous=ctl.read_json_safe(env.run,T.paths(env).state,canon.object({}))
    local value,age=M.verify_gap(previous,blockers,env.run.wall(),canon.is_object(state) and state.policy_roles or nil)
    return value,age,previous
  end)
  if not ok or value==nil then return false end
  M.busy_fields(env,blockers,nil)  -- the busy episode is still measured
  if not pcall(T.publish,env,value) then return false end
  if previous.verifying~=true then
    pcall(function() require('durable').log('PAIR-VERIFY-GAP: '..table.concat(blockers,',')..'; '..tostring(value.state)
      ..' kept on the kernel proof of '..string.format('%.1f',age)..' s ago (bounded '..M.VERIFY_GAP_SECONDS..' s)') end)
  end
  return true
end

local function revive_log(env,line,key)
  if key then
    local now=env.run.clock()
    if skip_logged[key] and now-skip_logged[key]<M.SKIP_LOG_EVERY then return end
    skip_logged[key]=now
  end
  pcall(function() require('durable').log(line) end)
end
M.revive_log_reset=function() skip_logged={} end
function M.ensure_devices(env,state)
  local ok,devices=pcall(env.backend.devices)
  if ok and type(devices)=='table' and #devices>0 then return devices end
  if env.stop() or not canon.is_object(state) or next(state)==nil then return nil end
  local started={}
  local function skip(reason) revive_log(env,'PAIR-RECOVERY-REVIVE-SKIPPED: '..reason,reason) end
  local rok,rerr=pcall(function()
    local n=env.net
    if type(n)~='table' or not n.network or not n.client_down or not n.ifup then skip('NETWORK-SIDE-UNAVAILABLE');return end
    local managed=M.state_interfaces(state)
    local rows=n.network()
    if n.identity(rows,managed)~=state.network_identity then
      revive_log(env,'PAIR-RECOVERY-REVIVE: network identity differs from the session (profiles checked one by one)','identity')
    end
    local skipped={firewall=true}
    if canon.is_object(state.protected) then for name in pairs(state.protected) do if not M.PROFILE_CONFIGS[name] then skipped[name]=true end end end
    if n.changed(state,n.configs(managed),skipped) then skip('PAIR-EXTERNAL-CONFIG-CHANGE');return end
    local revision=ctl.current_revision(env)
    local now=env.run.wall()
    local path=env.runtime..'/pair-revive.json'
    local ledger=ctl.read_json_safe(env.run,path,canon.object({}))
    if not canon.is_object(ledger) then ledger=canon.object({}) end
    local by_name={};for _,row in ipairs(rows) do by_name[row['.name']]=row end
    local names={};for name in pairs(managed) do names[#names+1]=name end;table.sort(names)
    for _,interface in ipairs(names) do
      local events={}
      local raw=ledger[interface]
      if canon.is_array(raw) then for _,x in ipairs(raw) do local v=num(x);if v and finite(v) and 0<=now-v and now-v<900 then events[#events+1]=v end end end
      local row=by_name[interface]
      if not row or row.proto~=managed[interface] or row.auto~='0' or row.disabled~='0' then skip('PAIR-PROFILES-UNVERIFIED '..interface)
      elseif (#events>0 and now-events[#events]<M.REVIVE_PAUSE) or #events>=M.REVIVE_LIMIT then skip('REVIVE-BUDGET '..interface)
      elseif not n.client_down(interface) then skip('NOT-STOPPED '..interface)
      else
        local list={};for i,x in ipairs(events) do list[i]=canon.float(x) end;list[#list+1]=canon.float(now)
        ledger[interface]=canon.array(list);ctl.write_json(env.run,path,ledger)
        local iok,ierr=pcall(n.ifup,interface,revision)
        started[#started+1]=interface
        revive_log(env,'PAIR-RECOVERY-REVIVE: ifup '..interface..(iok and '' or (' failed '..tostring(is_refused(ierr) and ierr.code or ierr))))
      end
    end
  end)
  if not rok then revive_log(env,'PAIR-RECOVERY-REVIVE: '..tostring(is_refused(rerr) and rerr.code or rerr)) end
  if #started==0 then return nil end
  local deadline=env.run.clock()+M.DEVICE_WAIT
  while true do
    local dok,list=pcall(env.backend.devices)
    if dok and type(list)=='table' and #list>0 then return list end
    if env.stop() or env.run.clock()>=deadline then return nil end
    env.sleep(2)
  end
end

-- boot_devices(): ensure_devices() for the pair session a boot recovery finds (none or a terminal one: nil).
function M.boot_devices(env)
  local ok,state=pcall(M.read_state,env)
  -- K3 (formal model 03.11.2026): a session handed over on the reserve (STOPPED with handover) still owns its
  -- clients until the Start adopts them: after a power cut they are started for the VPN-only guard of the held reserve
  if not ok or not canon.is_object(state) or next(state)==nil or (M.TERMINAL[state.phase] and not M.has_handover(state)) then return nil end
  return M.ensure_devices(env,state)
end

------------------------------------------------------------------------------------------------------
-- tick
------------------------------------------------------------------------------------------------------
-- The diagnostic accepted a source that keeps being rebuilt only to leave it (diagnosis.resolve_pair).
function M.source_unstable(selection)
  local coordination=canon.is_object(selection) and selection.coordination or nil
  return canon.is_object(coordination) and coordination.code==require('diagnosis').SOURCE_UNSTABLE
end

function M.reapply_missing_policy(env,state,settings,revision,value,observed)
  if isnone(state.policy_roles) then return false end
  local requested=M.intent(env)
  if requested.mode~='on' or requested.revision~=revision or requested.id~=state.id then refuse('CLIENT-STOP') end
  local blockers,selection=env.backend.diagnostic()
  if #blockers==1 and blockers[1]=='RESERVE-NOT-CONNECTED' and (value.phase=='COMMITTED' or value.phase=='HELD-ON-RESERVE') then
    -- T3 (trace conformance 04.11.2026): the traffic is on a reserve whose client is gone. This blocker used to end the
    -- pass here, before the committed decision: no return while the primary was healthy, until the reserve came back.
    -- Nothing to repair without a selection; the outside-change check stays and the decision goes on.
    local lo,lh=env.backend.order()
    if not P.state_order_matches(state,value,lo,lh) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
    return false
  end
  if #blockers>0 or not selection then
    if M.verify_gap_publish(env,state,blockers) then return true end  -- a short wait right after a confirmed pass
    local identity=state.policy_roles
    local published={state='BLOCKED',mode='continuous-pair',proof_scope=M.MODE,source=identity.source_id,target=identity.target_id,
      blockers=canon.array(#blockers>0 and blockers or {'PAIR-POLICY-UNVERIFIED'}),readiness_verified=false,kernel_policy_verified=false}
    T.publish(env,M.busy_fields(env,blockers,published))
    return true
  end
  if state.selected_policy==nil then
    -- A Start does not begin with an unaccepted key on the carrying channel (M.begin; here: a key seen while it ran, which waits
    -- for the owner's word); a key on the other channel changes nothing. A session that already proved its route goes on
    -- working, only a move onto that channel is refused (T.key_unaccepted).
    local pinned=T.carrying_unaccepted(env,selection)
    if pinned then
      T.publish(env,{state='BLOCKED',mode='continuous-pair',proof_scope=M.MODE,source=selection.source.id,target=selection.target.id,
        blockers=canon.array({pinned}),readiness_verified=false,kernel_policy_verified=false})
      return true
    end
  end
  local lo,lh=env.backend.order()
  if canon.encode(P.proof(selection))~=canon.encode(state.policy_roles) or not P.state_order_matches(state,value,lo,lh) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
  local kernel=env.backend.attest_policy(selection)
  if kernel.verified==true then
    M.remember_selected(env,state,kernel)
    -- LAN DNS follows the verified active channel: repairs drift after a GL rebuild of dns_mark (fw3/vpn-client
    -- reload, boot). Observation-grade: never fails the pass.
    if (kernel.role=='source' or kernel.role=='target') and env.backend.dns_mark_follow then pcall(env.backend.dns_mark_follow) end
    if observed then observed.selection=selection;observed.kernel=kernel end
    return false
  end
  if kernel.repairable_missing~=true then
    T.publish(env,{state='BLOCKED',reason='KERNEL-POLICY-UNVERIFIED',blockers=canon.array({'KERNEL-POLICY-UNVERIFIED'}),source=selection.source.id,target=selection.target.id,mode='continuous-pair',proof_scope=M.MODE})
    return true
  end
  local destination=P.role(state.policy_roles,selection.order)
  -- Never rebuild the policy towards a source the vendor keeps rebuilding: the decision below leaves it.
  if destination=='source' and M.source_unstable(selection) then return false end
  if not isnone(state.manual_hold) and state.manual_hold~=destination then refuse('PAIR-MANUAL-HOLD-UNVERIFIED') end
  local recovery=M.recovery_normalized(settings);local now=env.run.wall()
  local events,allowed=M.budget(ledger_events(env,now),now,recovery.attempt_window*60,recovery.attempt_limit)
  if not allowed or (#events>0 and now-num(events[#events])<math.max(recovery.cooldown,recovery.min_dwell)) then
    T.publish(env,{state='BLOCKED',reason='KERNEL-POLICY-UNVERIFIED',blockers=canon.array({'KERNEL-POLICY-UNVERIFIED','PAIR-RATE-LIMIT'}),source=selection.source.id,target=selection.target.id,mode='continuous-pair',proof_scope=M.MODE})
    return true
  end
  local until_=M.configure_lease(env,state)
  M.require_running(env,revision)
  T.attempt(env,selection,until_,false,{control_revision=revision,pair_destination=destination,pair_session_order=state.order,pair_reapply=true,
    on_dispatch=function() M.charge_attempt(env,settings,revision,nil,false) end})
  M.resume_running(env,state)
  return true
end

-- BH-06 (bug hunt 07.11.2026): the hold_reserve rescue probe of a reserve the detector calls failed is a full live probe.
-- During a total outage the precondition holds on every tick, so the dead reserve was probed afresh each tick. One probe
-- result is kept per failure episode (this session, this reserve) for RESCUE_PROBE_INTERVAL monotonic seconds in the
-- supervisor's env (process memory); tick clears it when the precondition no longer holds. Twin: pair_auto.rescue_health.
M.RESCUE_PROBE_INTERVAL=60
function M.rescue_health(env,state,target)
  local okc,mono=pcall(env.run.clock)
  mono=okc and num(mono) or nil
  local row=env.rescue_probe
  if row and mono and row.session==state.id and row.target==target and mono-row.at>=0 and mono-row.at<M.RESCUE_PROBE_INTERVAL then
    return row.health
  end
  local health=env.backend.health(target)
  env.rescue_probe=mono and {session=state.id,target=target,at=mono,health=health} or nil
  return health
end

function M.tick(env,settings,revision)
  local request_row=canon.object({})
  local ok,result=pcall(function()
    request_row=M.intent(env)
    local state=M.read_state(env)
    local has_state=next(state)~=nil
    local running=request_row.mode=='on' and request_row.revision==revision
    if not running and M.has_handover(state) then
      -- the journal stays as the old session left it until the Start: nothing else may finish it meanwhile
      if M.kept_valid(env,canon.object({kept_at=state.handover.at}),state.handover.tx) then return true end
      M.release_handover(env,state)
      return true
    end
    if not running and M.has_kept(state) then
      if M.kept_valid(env,state,state.kept_tx) then return false end  -- the boot (or restart) resume's Start is still coming
      M.release_kept(env,state)
      T.publish(env,{state='STOPPED',mode='continuous-pair',proof_scope=M.MODE,original_restored=true,blockers=canon.array({})})
      return true
    end
    local relevant=running or (has_state and not M.TERMINAL[state.phase])
    if not relevant then
      if not running and has_state then pcall(M.release_orphan_guard,env,state) end  -- review 04.11.2026 (finding 4)
      return false
    end
    if not running then
      if has_state and not M.TERMINAL[state.phase] then if not M.cleanup(env,state) then return true end end
      T.publish(env,{state='STOPPED',mode='continuous-pair',proof_scope=M.MODE,original_restored=(not has_state) or state.phase=='STOPPED',blockers=canon.array({})})
      return true
    end
    if not has_state or state.id~=request_row.id then
      if settings.pair_auto_mode~=M.MODE then value_error('PAIR-MODE-NOT-CONFIGURED') end
      if has_state and not M.TERMINAL[state.phase] then value_error('PAIR-RECOVERY-REQUIRED') end
      -- plan item 54: no new session while a package operation runs; the Start stays queued (pair_auto.tick)
      local maintenance=require('maintenance').blocker(function(path) return env.run.fs.read(path) end,env.persist,env.run.wall())
      if maintenance then
        T.publish(env,{state='ARMED',mode='continuous-pair',proof_scope=M.MODE,reason=maintenance,blockers=canon.array({maintenance})})
        return true
      end
      state=M.begin(env,settings,request_row)
    end
    T.bind_policy_context(env,state)
    if settings.pair_auto_mode~=M.MODE then value_error('PAIR-MODE-NOT-CONFIGURED') end
    local n=net(env)
    local managed=M.state_interfaces(state)
    local rows=n.network()
    local pending=state.server_change
    if canon.is_object(pending) and (pending.phase=='APPLYING' or n.identity(rows,managed)~=state.network_identity or n.changed(state,n.configs(managed))) then
      -- a change cut short in any phase (a crash, a rollback that raised after its uci writes): resolved before the checks
      M.server_resume(env,state,revision);managed=M.state_interfaces(state);rows=n.network()
    end
    if n.identity(rows,managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed)) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
    local value=T.journal_read(env)
    local status=ctl.read_json(env.run,T.paths(env).status,canon.object({}))
    local manual=require('manual')
    if state.server_change~=nil then
      if M.server_pending(env,state,settings,revision) then return true end  -- this session's own server change (stages 2, 3)
      value=T.journal_read(env)  -- a finished change may have re-bound or completed the journal
    end
    if manual.consume(env,state,settings,revision) then return true end
    if M.revive(env,state,revision,value,rows) then return true end
    if manual.held_reserve(env,state,value,settings,status) then return true end
    if M.server_start(env,state,settings,revision,value) then return true end
    local observed={}
    if M.reapply_missing_policy(env,state,settings,revision,value,observed) then return true end
    local kernel=observed.kernel
    local applied_target=(value.phase=='COMMITTED' or value.phase=='HELD-ON-RESERVE')
      or (value.activation_reapply==true and value.phase=='ROLLED-BACK' and value.trial_nonce==state.id and value.control_revision==state.revision and state.revision==revision)
    if applied_target and P.current_role(value)~='source' then
      local now=env.run.wall()
      local decision=T.committed_recovery_decision(env,value,settings,getd(status,'samples',canon.array({})),now,status,M.ledger_hold(env,settings,now))
      if decision.action=='RESTORE-PRIMARY' then
        local context=P.metadata(value)
        local progress=value
        if kernel then progress=merge(value,{restore_before_order=copy_list(kernel.order),restore_before_verified=true}) end
        local fields=context and T.pair_event_fields(progress,{restoring=true,restore_order=context.primary_order}) or {}
        T.publish(env,merge(fields,{state='RESTORING',mode='continuous-pair',proof_scope=M.MODE,source=value.source,target=value.target,reason=decision.reason,blockers=canon.array({})}))
        if T.finish_committed(env,value,decision.reason) then
          local final_kernel=context and env.backend.attest_policy() or NULL
          if context then
            if final_kernel.verified~=true or final_kernel.role~='source' or not same_list(final_kernel.order,context.primary_order) then refuse('ROLLBACK-UNVERIFIED') end
            M.remember_selected(env,state,final_kernel)
          end
          M.resume_running(env,state)
          fields=context and T.pair_event_fields(value,{completed=true,outcome='restored',restoring=true}) or {}
          T.publish(env,merge(fields,{state='ROLLED-BACK',reason=decision.reason,source=value.source,target=value.target,
            original_restored=order_is(env,state.order,state.policy_hash),mode='continuous-pair',proof_scope=M.MODE,kernel_proof=final_kernel}))
        else
          T.publish(env,{state='DEGRADED-ON-RESERVE',reason=getd(value,'reason','SOURCE-NOT-VERIFIED'),source=value.source,target=value.target,mode='continuous-pair',proof_scope=M.MODE,original_restored=false,blockers=canon.array({})})
        end
        return true
      else
        if decision.rebind then pcall(M.reserve_rebound,env,revision) end  -- finding 7
        M.resume_running(env,state)
        local verified=kernel~=nil and kernel.verified==true
        local reapply=value.activation_reapply==true
        T.publish(env,{state=decision.action=='OBSERVE' and (reapply and 'OBSERVING' or 'COMMITTED') or 'DEGRADED-ON-RESERVE',source=value.source,target=value.target,
          mode='continuous-pair',proof_scope=M.MODE,readiness_verified=verified,kernel_policy_verified=verified,kernel_proof=kernel or NULL,
          reason=(reapply and decision.action=='OBSERVE') and 'PAIR-WATCHING' or decision.reason,blockers=canon.array({})})
        return true
      end
    end
    local blockers,selection=env.backend.diagnostic()
    if #blockers==0 then M.busy_fields(env,blockers,nil) end
    if #blockers>0 then
      local age=env.run.wall()-num(state.started)
      local preparing=0<=age and age<=180
      local busy=false
      for _,x in ipairs(blockers) do
        if x=='VENDOR-WORKER-BUSY' then busy=true end
        if x~='VENDOR-SETTLING' and x~='OBSERVATION-STALE' and x~='PROFILE-IDENTITY-CHANGED' and x~='RESERVE-NOT-CONNECTED' then preparing=false end
      end
      if M.verify_gap_publish(env,state,blockers) then return true end  -- a short wait right after a confirmed pass
      local value={state=preparing and 'ARMED' or 'BLOCKED',mode='continuous-pair',proof_scope=M.MODE,reason=preparing and 'PAIR-WAITING-PROBES' or NULL,blockers=canon.array(blockers)}
      -- the page names the pair that waits; a manual switch still meets the same blocker in its transaction
      if busy and canon.is_object(selection) then value.source=selection.source.id;value.target=selection.target.id end
      T.publish(env,M.busy_fields(env,blockers,value))
      return true
    end
    local lo,lh=env.backend.order()
    if not P.state_order_matches(state,value,lo,lh) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
    M.resume_running(env,state)
    local now=env.run.wall()
    local recovery=M.recovery_normalized(settings)
    local age=M.valid_for(settings)
    local samples=getd(status,'samples',canon.array({}))
    -- An unstable source (no healthy observation for the whole bounded window, across its vendor rebuilds)
    -- is the failure evidence itself: its generation-scoped streak restarts on every rebuild.
    local unstable=M.source_unstable(selection)
    -- The owner's failure model (channel_model.lua: 'hmm' default, 'hmm-fast', or 'consecutive' = the streak).
    local CM=require('channel_model')
    local beat=CM.heartbeat_k(settings)~=nil and ctl.read_json_safe(env.run,env.runtime..'/'..CM.WAKE_NAME,canon.object({})) or nil
    local rule=unstable and 'unstable' or CM.leave_rule(samples,selection.source.id,recovery.failures,now,age,settings,selection.source,env,selection.target.id,beat)
    local failed=rule~=nil
    local healthy=M.streak(samples,selection.target.id,recovery.successes,now,age,true,selection.target,env)
    local diagnosis=env.deps and env.deps.diagnose and env.deps.diagnose(status,selection.source.id,now,settings) or {}
    if unstable and diagnosis.suppress_switch then diagnosis=merge(diagnosis,{suppress_switch=false}) end
    local events=M.budget(ledger_events(env,now),now,recovery.attempt_window*60,recovery.attempt_limit)
    local dwell=#events==0 or now-num(events[#events])>=math.max(recovery.cooldown,recovery.min_dwell)
    -- a failover the vendor aborted is retried after its short backoff (M.retry_wait), not after the cooldown
    local retry_ready=M.retry_wait(ledger_aborted(env),events,now,recovery)<=0
    local since=num(getd(getd(state,'selected_policy',canon.object({})),'since',nil)) or now
    -- The one return rule (M.return_rule, Python recovery_settings.return_rule): a healthy reserve is left only after
    -- the damped stable window AND, in the HMM modes, channel_model.return_ready; a reserve that failed itself after the
    -- rescue stability min(primary_stable, rescue_stable) without the model gate; otherwise primary_stable.
    local on_reserve=kernel~=nil and kernel.role=='target' and isnone(state.manual_hold) and now-since>=recovery.min_dwell and dwell
    -- Owner decision 07.11.2026 (F-80), the path without an open journal (traffic on the reserve per selected_policy
    -- after a boot or an accepted manual selection): hold_reserve means "do not return from a WORKING reserve". A
    -- reserve the detector calls failed is probed once per RESCUE_PROBE_INTERVAL s of one failure episode (BH-06:
    -- rescue_health, backend.health); only a FRESH NEGATIVE probe opens the rescue
    -- rule (rescue_stable, no model gate, RESERVE-FAILED-PRIMARY-VERIFIED) through the same attempt, guards and
    -- cooldown as the planned return; an unknown probe holds (RESERVE-HEALTH-UNKNOWN), an alive probe observes.
    -- Twin: transaction.committed_recovery_decision (journal path), Python pair_auto.tick.
    local reserve_health,held=nil,nil
    if on_reserve and recovery.return_policy~='healthy_primary' and not healthy
       and CM.channel_failed(samples,selection.target.id,recovery.failures,now,age,settings,selection.target,env) then
      reserve_health=M.rescue_health(env,state,selection.target.id)
      if reserve_health==false then held='RESERVE-FAILED'
      elseif reserve_health==nil then held='RESERVE-HEALTH-UNKNOWN' end
    else
      env.rescue_probe=nil  -- BH-06: the failure episode ended, the next one probes at once
    end
    local returning=on_reserve and (recovery.return_policy=='healthy_primary' or reserve_health==false)
    local ready_settings,model_gate=settings,false
    if returning then
      local reserve='unknown'
      if healthy then reserve='planned'
      elseif reserve_health==false or CM.channel_failed(samples,selection.target.id,recovery.failures,now,age,settings,selection.target,env) then reserve='failed' end
      ready_settings,model_gate=M.return_rule(settings,reserve,healthy and M.return_hold(M.failover_events(events,ledger_row(env)),now,recovery) or nil)
    end
    if returning
       and (not model_gate or CM.return_ready(samples,selection.source.id,recovery.primary_successes,now,age,settings,selection.source,env))
       and not T.key_unaccepted(env,selection.source.id)
       and env.backend.recovery_ready(selection.source.id,ready_settings)==true then
      local until_=M.configure_lease(env,state)
      local b2,fresh=env.backend.diagnostic()
      if #b2>0 then value_error('PAIR-READINESS-CHANGED') end
      T.attempt(env,fresh,until_,false,{control_revision=revision,pair_destination='source',pair_return=true,pair_session_order=state.order,
        on_dispatch=function() M.charge_attempt(env,settings,revision,false,false) end})
      return true
    end
    local order=getd(selection,'order',canon.array({}))
    local si,ti=index_of(order,selection.source_rule),index_of(order,selection.target_rule)
    local reserve_first=getd(selection,'direction','first')=='first' and si~=nil and ti~=nil and ti<si
    local verified=kernel~=nil and kernel.verified==true
    if failed and healthy and reserve_first then
      T.publish(env,{state='OBSERVING',mode='continuous-pair',readiness_verified=true,certified=false,proof_scope=M.MODE,external_lan_verified=false,
        source=selection.source.id,target=selection.target.id,reason='RESERVE-ALREADY-FIRST',blockers=canon.array({}),kernel_proof=kernel or NULL,kernel_policy_verified=verified})
      return true
    end
    -- Leaving a failed primary is never blocked by the attempt limit (flap damping slows the return instead).
    if failed and healthy and dwell and retry_ready and not diagnosis.suppress_switch then
      local pinned=T.key_unaccepted(env,selection.target.id)
      if pinned then
        -- the owner's option: the reserve is not trusted, the pair stays where it is until he accepts the key
        T.publish(env,{state='BLOCKED',mode='continuous-pair',proof_scope=M.MODE,reason=pinned,blockers=canon.array({pinned}),source=selection.source.id,
          target=selection.target.id,source_failures=failed,reserve_healthy=healthy,kernel_proof=kernel or NULL,kernel_policy_verified=verified})
        return true
      end
      -- late-switch recheck (see M.late_recheck); an unstable source is left on its instability as before
      local evidence,evidence_code=nil,nil
      if not unstable then
        local newest=M.newest_sample(samples,selection.source.id,selection.source,env)
        evidence=newest and num(newest.time) or nil
        evidence_code=newest and type(newest.code)=='string' and newest.code or nil
      end
      local function late_abort(how)
        T.publish(env,{state='OBSERVING',mode='continuous-pair',readiness_verified=true,certified=false,proof_scope=M.MODE,external_lan_verified=false,
          source=selection.source.id,target=selection.target.id,vendor_identity=getd(selection,'vendor_identity',NULL),kernel_proof=kernel or NULL,
          kernel_policy_verified=verified,source_failures=failed,reserve_healthy=healthy,reason=M.LATE_RECHECK_CODE,late_recheck=how,blockers=canon.array({})})
        return true
      end
      if evidence~=nil and M.same_evidence(M.late_aborts[selection.source.id],evidence) then return late_abort('same-evidence') end
      local beat_run=nil
      if rule=='heartbeat' and type(beat)=='table' and beat~=NULL then beat_run=num(beat.since) end
      if beat_run~=nil and M.late_aborts['beat:'..selection.source.id]==beat_run then return late_abort('same-run') end
      local pending=evidence~=nil and M.recheck_begin(env,selection,evidence_code,settings) or nil
      local pok,until_,b2,fresh=pcall(function()
        local lease=M.configure_lease(env,state)
        local blockers2,selected=env.backend.diagnostic()
        return lease,blockers2,selected
      end)
      if not pok then
        if pending then M.recheck_finish(env,pending) end  -- its children and files end with it
        error(until_,0)
      end
      if #b2>0 then
        if pending then M.recheck_finish(env,pending) end
        value_error('PAIR-READINESS-CHANGED')
      end
      local prepared=env.run.wall()
      if evidence~=nil then
        local code,how=M.late_recheck(env,selection,evidence,evidence_code,pending)
        M.decision_timing(env,now,prepared,env.run.wall(),rule,pending~=nil)
        if code then
          M.late_aborts[selection.source.id]=evidence
          if beat_run~=nil then M.late_aborts['beat:'..selection.source.id]=beat_run end
          return late_abort(how)
        end
      end
      M.late_aborts[selection.source.id]=nil;M.late_aborts['beat:'..selection.source.id]=nil
      -- the owner's hold ends only when the traffic really moves: a refuted decision leaves it (review 04.11.2026, finding 3)
      if not isnone(state.manual_hold) then state.manual_hold=nil;M.save(env,state) end
      local charged=nil
      local aok,aerr=pcall(T.attempt,env,fresh,until_,false,{probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,failure_model=CM.name(settings),failure_rule=rule,required_failures=recovery.failures,required_successes=recovery.successes}),
        control_revision=revision,pair_session_order=state.order,on_dispatch=function() charged=M.charge_attempt(env,settings,revision,false) end})
      if not aok then
        -- a vendor-aborted, rolled-back failover is not a switch (M.refund_abort); the error is still published
        if charged~=nil and is_refused(aerr) then pcall(M.refund_abort,env,charged,aerr.code) end  -- unproven: the charge stays
        error(aerr,0)
      end
    else
      local reason
      -- held: the pinned reserve failed (fresh probe false, the primary not yet rescue_stable) or its probe is unknown
      if held then reason=held
      elseif diagnosis.suppress_switch then reason=diagnosis.code
      elseif failed and healthy and not (dwell and retry_ready) then reason='PAIR-RATE-LIMIT'
      elseif state.manual_hold=='source' then reason='PAIR-MANUAL-HOLD-PRIMARY'
      else reason='PAIR-WATCHING' end
      T.publish(env,{state=held and 'DEGRADED-ON-RESERVE' or 'OBSERVING',mode='continuous-pair',readiness_verified=true,certified=false,proof_scope=M.MODE,external_lan_verified=false,
        source=selection.source.id,target=selection.target.id,vendor_identity=getd(selection,'vendor_identity',NULL),kernel_proof=kernel or NULL,
        kernel_policy_verified=verified,source_failures=failed,reserve_healthy=healthy,reason=reason,blockers=canon.array({})})
    end
    return true
  end)
  if ok then return result end
  local err=result
  if not is_refused(err) then error(err,0) end  -- a plain Lua error is a bug, not a recovery conflict
  local pok,pending=pcall(M.read_state,env)
  if not pok then pending=canon.object({}) end
  local code=err.code
  if pending.phase=='RUNNING' and M.READOPT_CODES[code] and request_row.mode=='on' then
    local rok,handed=pcall(M.readopt_running,env,pending,request_row,revision,code)
    if rok and handed then return true end
  end
  if code=='BOOT-RESERVE-UNVERIFIED' and request_row.mode=='on' then
    pcall(M.fail_request,env,request_row,revision,err)  -- the old session is HELD again; today's path follows
    M.publish_failure(env,err)
    return true
  end
  if pending.phase=='STARTING' then
    local cok=pcall(function() M.cleanup(env,pending);pending=M.read_state(env) end)
    if not cok then pending.phase='HELD';M.save(env,pending) end
  end
  local settled=pending.phase==nil or pending.phase=='STOPPED' or pending.phase=='FAILED'
  local age=env.run.wall()-(num(request_row.time) or 0)
  if M.TRANSIENT_START[code] and settled and request_row.mode=='on' and 0<=age and age<=M.TRANSIENT_START_SECONDS then
    T.publish(env,{state='ARMED',mode='continuous-pair',proof_scope=M.MODE,reason='PAIR-WAITING-VENDOR',blockers=canon.array({code})})
    return true
  end
  if (settled or (pending.phase=='HELD' and pending.ran~=true)) and request_row.mode=='on' then M.fail_request(env,request_row,revision,err) end
  M.publish_failure(env,err)
  -- K9: not running (after a recovery, or the owner's Stop): the outside-change hold keeps or releases its guard
  if not (request_row.mode=='on' and request_row.revision==revision) then pcall(M.outside_hold,env) end
  return true
end

------------------------------------------------------------------------------------------------------
-- best server inside a channel, stages 2 and 3 (server_pick.lua; SERVER-PICK-DESIGN-2026-11-02.ru.md). Python: pair_auto.server_*
------------------------------------------------------------------------------------------------------
-- MT3000 02.11.2026: a server change of the idle reserve made outside the pair (uci route_policy + network,
-- ifdown/ifup) was an external change for this session - PAIR-READOPTED, a 7.1 s LAN stall on the WORKING channel,
-- HELD after three in 15 min. Now this supervisor makes the change itself, inside its control lock, and re-binds its
-- own session to it (network_identity, protected route_policy digest, order, policy_hash, policy_roles,
-- selected_policy and the journal): no external code, no readopt. The monitor job only measures and writes the
-- hand-off (server_pick.CHANGE). The record state.server_change (phase APPLYING -> CONNECTING -> SETTLING, role) keeps
-- the pair waiting (reason SERVER-CHANGING, no switch decision) at most CONNECT_WAIT s for the tunnel to pass the
-- pair's own health check (DNS + HTTPS through it), else the previous server comes back the same way; then at most
-- SETTLE_WAIT s for the monitor to observe the new profile.
-- Stage 2 (role 'target'): the idle reserve while the traffic is on the primary and the pair rests.
-- Stage 3 (role 'source'): the failed primary while the traffic is on the reserve after a completed automatic switch
-- (journal COMMITTED). The open journal is re-bound too, so the normal return rules bring the traffic back to the
-- primary on its new server (the return reads the journal's source id: streaks and the fresh check follow the new id).
-- The carrying reserve is never touched. Both tunnels are bound by tunnel id (plan_source_tunnel/plan_target_tunnel).
-- A crash or power cut inside a change (any phase): M.server_resume adopts the live from, or to once verified; an
-- unverified to is restored to from unless its tunnel carries (before auto.recover compares a COMMITTED journal with
-- the live order, in the cleanup and in tick before the external-change checks). env.server_io: tests.
local function server_io(env) return env.server_io or require('server_pick').router_io(env.runtime) end
local function server_enabled(settings) return canon.is_object(settings) and (settings.server_pick=='1' or settings.server_pick==true) end

-- source interface, reserve interface, the set of interfaces bound by their tunnel id (plan_source_tunnel and
-- plan_target_tunnel, alpha27): a tunnel chosen by its profile id would lose its binding with the new server's id
function M.server_interfaces(state,settings)
  local managed=M.state_interfaces(state)
  local anchored={}
  for _,role in ipairs({'source','target'}) do
    local anchor=canon.is_object(settings) and settings['plan_'..role..'_tunnel'] or nil
    local kind,name=nil,nil
    if type(anchor)=='string' then kind,name=string.match(anchor,'^([^:]*):([^:]*)$') end
    local protocol=({wgclient='wireguard',ovpnclient='openvpn'})[name and managed[name] or '']
    if protocol~=nil and kind==protocol then anchored[role]=name end
  end
  local names={};for name in pairs(managed) do names[#names+1]=name end;table.sort(names)
  local function other(x) for _,name in ipairs(names) do if name~=x then return name end end end
  local source,target=anchored.source,anchored.target
  if source==nil and target~=nil then source=other(target) end
  if target==nil and source~=nil then target=other(source) end
  if source==nil or source==target then return nil,nil,{} end
  local set={};for _,name in pairs(anchored) do set[name]=true end
  return source,target,set
end

local function server_tunnel(pending)
  return {tunnel_id=pending.tunnel_id,protocol=pending.protocol,section=pending.section,interface=pending.interface}
end

-- this supervisor's own server change adopted by the session (server_pick.rebind); error when the live change is
-- not only the changed tunnel's (the normal checks then see an external change). The journal is written first.
-- F-27 (pair_auto.server_network_delta_only): the live network may differ from the session's identity only in the
-- selected interface's `config` naming the recorded from/to server (this supervisor's own write); anything else is
-- somebody else's edit and is never absorbed into the baseline.
function M.server_network_delta_only(env,state,rows,managed,interface,protocol)
  local S=require('server_pick')
  local n=net(env)
  local identity=state.network_identity
  if n.identity(rows,managed)==identity then return true end
  local pending=state.server_change
  if not canon.is_object(pending) then return false end
  for _,side in ipairs({'from','to'}) do
    local server=pending[side]
    local config=canon.is_object(server) and S.network_config(protocol,server.group_id,server.profile_id) or nil
    if config~=nil then
      local trial=canon.decode(canon.encode(rows))
      for _,row in ipairs(trial) do if row['.name']==interface then row.config=config end end
      if n.identity(trial,managed)==identity then return true end
    end
  end
  return false
end

function M.server_rebind(env,state,interface,protocol,role)
  local S=require('server_pick')
  local n=net(env)
  local managed=M.state_interfaces(state)
  if n.forget then n.forget() end
  if env.backend.invalidate then env.backend.invalidate() end
  local rows=n.network()
  if not M.server_network_delta_only(env,state,rows,managed,interface,protocol) then error(S.FAILED,0) end
  local config=nil
  for _,row in ipairs(rows) do if row['.name']==interface then config=row.config end end
  local profile=type(config)=='string' and ((protocol=='openvpn' and 'openvpn:' or 'wireguard:')..config) or nil
  local order,hash=env.backend.order()
  local updated,journal=S.rebind(state,T.journal_read(env),order,hash,profile,role or 'target')
  updated.network_identity=n.identity(rows,managed)
  if canon.is_object(updated.protected) then
    -- route_policy always; wireguard after GL's update_provider_config step (server_pick.PROVIDER_SCRIPT)
    local current=nil
    for _,name in ipairs({'route_policy','wireguard'}) do
      if updated.protected[name]~=nil and (name=='route_policy' or protocol=='wireguard') then
        current=current or n.configs(managed);updated.protected[name]=current[name]
      end
    end
  end
  if journal~=nil then T.journal_write(env,journal) end
  for k in pairs(state) do state[k]=nil end
  for k,v in pairs(updated) do state[k]=v end
  M.save(env,state)
end

-- one server change of an idle tunnel (stage 1's steps) under the control lock, the session re-bound before the lock
-- is released -> server_pick.PICKED, or FAILED (a failed step, or a change the session cannot explain).
-- revision nil: a resume outside a running Auto (boot, cleanup) - refused while any Auto intent is on
-- outcome (a table, optional) gets server_pick.run_plan's changed/committed/touched and rebound (the session re-bound)
function M.server_apply(env,state,revision,tunnel,target,io_,role,outcome)
  local S=require('server_pick')
  local plan=S.switch_plan(tunnel,target,true,true,false,false,1)
  local report=type(outcome)=='table' and outcome or {}
  report.changed=false;report.committed=false;report.touched=false;report.rebound=false
  if plan.code~=nil then return S.FAILED end
  return env.run.lock(function()
    local current=M.intent(env)
    if revision==nil then
      if current.mode=='on' then refuse('CLIENT-STOP') end
    elseif ctl.revision_locked(env)~=revision or current.mode~='on' or current.revision~=revision or current.id~=state.id then refuse('CLIENT-STOP') end
    -- F-27: the route_policy sections before the write; afterwards only the tunnel's own rule may differ, and only
    -- in the server fields the plan writes (server_pick.policy_delta_only)
    -- The record's policy_before (server_start, before the first write) is the baseline of the change AND of every
    -- rollback or resume restore of it: a foreign edit that landed meanwhile fails the rollback too (pair_auto twin).
    local policy=type(env.backend.policy)=='function' and env.backend.policy or nil
    local pending=canon.is_object(state) and state.server_change or nil
    local snapshot=canon.is_object(pending) and canon.is_array(pending.policy_before) and pending.policy_before or nil
    if snapshot==nil and policy then local pok,data=pcall(policy);snapshot=pok and canon.is_object(data) and data.sections or nil end
    local done=S.run_plan(plan,io_,true)
    report.changed=done.changed;report.committed=done.committed;report.touched=done.touched
    if policy then
      if env.backend.invalidate then env.backend.invalidate() end
      local pok,data=pcall(policy);local live=pok and canon.is_object(data) and data.sections or nil
      if snapshot==nil or live==nil or not S.policy_delta_only(snapshot,live,tunnel.section) then return S.FAILED end
    end
    local ok,err=pcall(M.server_rebind,env,state,tunnel.interface,tunnel.protocol,role)
    if not ok then
      if type(err)=='string' or (is_refused(err) and err.value_error) then return S.FAILED end
      error(err,0)
    end
    report.rebound=true
    return done.code
  end,env.runtime)
end

local function server_publish(env,state,kernel)
  local S=require('server_pick')
  local roles=canon.is_object(state.policy_roles) and state.policy_roles or canon.object({})
  local verified=canon.is_object(kernel) and kernel.verified==true
  T.publish(env,{state='OBSERVING',mode='continuous-pair',proof_scope=M.MODE,reason=S.CHANGING,source=getd(roles,'source_id',NULL),
    target=getd(roles,'target_id',NULL),readiness_verified=verified,kernel_policy_verified=verified,kernel_proof=kernel or NULL,blockers=canon.array({})})
end

-- a valid hand-off of the monitor job taken when the gate allows it; true: this pass changed a server
function M.server_start(env,state,settings,revision,value)
  local S=require('server_pick')
  if not server_enabled(settings) then return false end
  local io_=server_io(env)
  local okr,row=pcall(function() return canon.decode(io_.read(io_.runtime..'/'..S.CHANGE) or 'null') end)
  if not okr then row=nil end
  local now=env.run.wall()
  local okh,record=pcall(function() return canon.decode(io_.read(io_.runtime..'/'..S.STATE) or '{}') end)
  if not okh or not canon.is_object(record) then record=canon.object({}) end
  local history=canon.is_object(record.changes) and record.changes or canon.object({})
  local taken=type(record.taken)~='boolean' and num(record.taken) or nil
  local stamp=canon.is_object(row) and type(row.time)~='boolean' and num(row.time) or nil
  if taken and finite(taken) and stamp and stamp<=taken then return false end  -- taken once
  local claimed=S.claim(io_,row,now)
  if claimed==nil then return false end
  local tunnel=claimed.tunnel
  local source,reserve,anchors=M.server_interfaces(state,settings)
  local kernel=env.backend.attest_policy()
  local left=S.changes_left(history,tunnel.tunnel_id,now)
  local gate={enabled=true,phase=state.phase,journal_phase=value.phase,journal_manual=not isnone(value.manual_request_id),
    kernel_verified=canon.is_object(kernel) and kernel.verified==true,kernel_role=canon.is_object(kernel) and kernel.role or nil,interface=tunnel.interface,
    source_interface=source,target_interface=reserve,manual_hold=state.manual_hold,pending=state.server_change~=nil,anchored=anchors[tunnel.interface]==true,
    busy=S.vendor_busy(tunnel.tunnel_id,io_),left=left}
  local code=S.gate(gate)
  local role=S.role_of(gate)
  if code==nil then
    -- a server change waits for the owner's word on a key of either channel (attest_policy used to refuse it as a blocker)
    local roles=getd(state,'policy_roles',canon.object({}))
    if T.key_unaccepted(env,roles.source_id,roles.target_id) then code=S.DEFERRED end
  end
  if code==nil then
    -- stage 2: the live order is the session's; stage 3: the COMMITTED journal's, with the session's context
    local lo,lh=env.backend.order()
    if role=='target' and not (same_list(lo,state.order) and lh==state.policy_hash) then code=S.DEFERRED end
    if role=='source' and not P.state_order_matches(state,value,lo,lh) then code=S.DEFERRED end
  end
  if code~=nil then
    if S.EVENT_CODES[code] then S.event(io_,code,tunnel,now,nil,row.time) end
    return false
  end
  local change=S.project_change(canon.object({time=now,from=row.from,to=row.to,from_ms=getd(row,'from_ms',NULL),to_ms=getd(row,'to_ms',NULL),
    from_location=getd(row,'from_location',NULL),to_location=getd(row,'to_location',NULL)}))
  if change==false then change=canon.object({time=now,from=row.from,to=row.to,from_ms=NULL,to_ms=NULL,from_location=NULL,to_location=NULL}) end
  local goal=claimed.target
  local target=canon.object({group_id=goal.group_id,profile_id=goal.profile_id,id=S.profile_id(tunnel.protocol,goal.group_id,goal.profile_id)})
  local previous=canon.object({group_id=claimed.previous.group_id,profile_id=claimed.previous.profile_id})
  local pending=canon.object({tunnel_id=tunnel.tunnel_id,protocol=tunnel.protocol,section=tunnel.section,interface=tunnel.interface,phase='APPLYING',role=role,
    from=previous,to=target,started=canon.float(now),deadline=canon.float(now+S.CONNECT_WAIT),request=row.time,change=change})
  -- F-27: the route_policy sections before the first write, the baseline of the change and of its rollback/resume
  if type(env.backend.policy)=='function' then
    local pok,data=pcall(env.backend.policy)
    if pok and canon.is_object(data) and canon.is_array(data.sections) then pending.policy_before=canon.decode(canon.encode(data.sections)) end
  end
  state.server_change=pending;M.save(env,state)  -- before the first write: a crash in between is seen by M.server_resume
  S.record(io_,tunnel.tunnel_id,now,nil,true,row.time)  -- every attempt counts for the hourly limit; taken once
  local function with(fields) local out=canon.decode(canon.encode(pending));for k,v in pairs(fields) do out[k]=v end;return out end
  local first={}
  if M.server_apply(env,state,revision,tunnel,target,io_,role,first)==S.PICKED then
    state.server_change=with({phase='CONNECTING'})
  elseif first.changed==false then
    -- nothing was written (the first uci step failed): nothing to roll back, no change to wait for
    S.event(io_,S.FAILED,tunnel,now,change,row.time,S.NOT_CHANGED)
    state.server_change=nil;M.save(env,state)
    return false
  else
    local back={}
    local undone=M.server_apply(env,state,revision,tunnel,previous,io_,role,back)==S.PICKED
    S.event(io_,S.FAILED,tunnel,now,change,row.time,S.rollback_note(undone,first,back))
    state.server_change=with({phase='SETTLING',deadline=canon.float(now+S.SETTLE_WAIT),rolled_back=true})
  end
  M.save(env,state)
  server_publish(env,state,kernel)
  return true
end

-- stage 3: once the monitor observes the new primary profile, the open COMMITTED journal records its vendor identity
-- (vendor_profiles.source, vendor_identity) the way the switch records it (pair_auto.server_settled); true: updated
-- Finding 7: a vendor rebuild of the reserve proven by committed_recovery_decision (rebind). The open journal records the
-- live generations and vendor_identity the way the switch records them, so forward_resume, channel_path and a later
-- rollback compare the live profiles. Both roles: the vendor rebuilds the primary as well (the incident did) and
-- vendor_identity covers both. Fresh diagnostic with no blocker, the same stable identity for both roles, under the
-- control lock against a Stop. settled: a manual primary hold, its journal may be ROLLED-BACK. True when the journal was
-- updated. Python: pair_auto.reserve_rebound.
function M.reserve_rebound(env,revision,settled)
  local identity=require('identity')
  local blockers,selection=env.backend.diagnostic()
  if #blockers>0 or not canon.is_object(selection) then return false end
  local live={source=identity.profile_identity(selection.source),target=identity.profile_identity(selection.target)}
  local vid=selection.vendor_identity
  if live.source==nil or live.target==nil or not ctl.hex(vid,64) then return false end
  local done=env.run.lock(function()
    T.require_control_revision(env,revision)
    local value=T.journal_read(env)
    local proofs=value.vendor_profiles
    local open=value.phase=='COMMITTED' or value.phase=='HELD-ON-RESERVE' or (settled==true and value.phase=='ROLLED-BACK')
    if not open or not canon.is_object(proofs) then return false end
    local same=getd(value,'vendor_identity',nil)==vid
    for _,role in ipairs({'source','target'}) do
      local proof=getd(proofs,role,nil)
      if not canon.is_object(proof) then return false end
      for _,key in ipairs(T.RESERVE_STABLE) do if canon.encode(getd(live[role],key,NULL))~=canon.encode(getd(proof,key,NULL)) then return false end end
      same=same and canon.encode(live[role])==canon.encode(proof)
    end
    if same then return false end
    local updated=canon.decode(canon.encode(value))
    updated.vendor_profiles.source=live.source;updated.vendor_profiles.target=live.target;updated.vendor_identity=vid
    T.journal_write(env,updated)
    return true
  end,env.runtime)
  if done then pcall(function() require('durable').log('PAIR-RESERVE-REBOUND: the vendor rebuilt '..tostring(live.target.id)..'; the journal follows its new generation') end) end
  return done
end

function M.server_settled(env,selection)
  local identity=require('identity')
  local ok,value=pcall(T.journal_read,env)
  if not ok then return false end
  local proofs=value.vendor_profiles
  if value.phase~='COMMITTED' or not canon.is_object(proofs) or not canon.is_object(selection) then return false end
  local source=identity.profile_identity(selection.source)
  local target=identity.profile_identity(selection.target)
  if source==nil or source.id~=value.source or target==nil or canon.encode(target)~=canon.encode(getd(proofs,'target',NULL)) then return false end
  local vid=selection.vendor_identity
  if not ctl.hex(vid,64) then vid=getd(value,'vendor_identity',nil) end
  if canon.encode(getd(proofs,'source',NULL))==canon.encode(source) and getd(value,'vendor_identity',nil)==vid then return false end
  local updated=canon.decode(canon.encode(value))
  updated.vendor_profiles.source=source
  if vid~=nil then updated.vendor_identity=vid end
  T.journal_write(env,updated)
  return true
end

-- at a resume: true unless the kernel proves the traffic on the other tunnel (an unknown route is carrying)
local function server_carrying(env,pending)
  local ok,kernel=pcall(env.backend.attest_policy)
  local role=getd(pending,'role','target')
  return not (ok and canon.is_object(kernel) and kernel.verified==true and (kernel.role=='source' or kernel.role=='target') and kernel.role~=role)
end

-- a server change record a crash, a power cut or a rollback that raised left behind (any phase): the live server of
-- the tunnel (route_policy and network both) is adopted (M.server_rebind) when it is the recorded from, or to after its
-- CONNECTING check passed (verified). An unverified to is restored to from (M.server_apply, as a timeout rollback;
-- revision nil outside a running Auto) unless its tunnel now carries the traffic (then adopted and logged); a failed
-- restore adopts what is live. Anything else is left to the normal checks (an external change). The record is
-- removed either way. Never raises; true when re-bound.
function M.server_resume(env,state,revision)
  local S=require('server_pick')
  local pending=canon.is_object(state) and state.server_change or nil
  if pending==nil then return false end
  local adopted,note=nil,''
  pcall(function()
    local io_=server_io(env);local tunnel=server_tunnel(pending);local role=getd(pending,'role','target')
    local function live_side()
      local group,profile=S.live_server(io_,tunnel)
      local config=nil
      for _,row in ipairs(net(env).network()) do if row['.name']==tunnel.interface then config=row.config end end
      for _,side in ipairs({'to','from'}) do
        local server=pending[side]
        if canon.is_object(server) and group~=nil and group==server.group_id and profile==server.profile_id
           and config==S.network_config(tunnel.protocol,server.group_id,server.profile_id) then return side end
      end
      return nil
    end
    local side=live_side()
    if side=='to' and pending.verified~=true then
      if not canon.is_object(pending.from) or server_carrying(env,pending) then note=' (not verified; its tunnel carries the traffic)'
      else
        local ok,code=pcall(M.server_apply,env,state,revision,tunnel,pending.from,io_,role)
        if ok and code==S.PICKED then adopted,side,note='from',nil,' (the new one was not verified: restored)'
        else side,note=live_side(),' (the unverified new one could not be restored)' end
      end
    end
    if side~=nil then
      M.server_rebind(env,state,tunnel.interface,tunnel.protocol,role)
      adopted=side
    end
  end)
  pcall(function() state.server_change=nil;M.save(env,state) end)
  pcall(function() require('durable').log('SERVER-PICK-RESUMED: '..(adopted and ('adopted the recorded '..adopted..' server'..note) or ('not explainable; the normal checks decide'..note))) end)
  return adopted~=nil
end

-- the supervisor start (auto.recover, before it compares a COMMITTED journal with the live order)
function M.server_resume_boot(env)
  local ok,state=pcall(M.read_state,env)
  if not ok or not canon.is_object(state) or state.server_change==nil then return false end
  boot_step(env,'server change resume')
  return M.server_resume(env,state)
end

-- while this supervisor's own server change is pending: true = this pass waited (no other decision)
function M.server_pending(env,state,settings,revision)
  local S=require('server_pick')
  local pending=state.server_change
  if pending==nil then return false end
  local now=env.run.wall()
  if canon.is_object(pending) and pending.phase=='APPLYING' then
    M.server_resume(env,state,revision)  -- a crash inside the change (the supervisor restarted mid-way)
    return false
  end
  local started,deadline=canon.is_object(pending) and num(pending.started) or nil,canon.is_object(pending) and num(pending.deadline) or nil
  local role=canon.is_object(pending) and getd(pending,'role','target') or nil
  if not canon.is_object(pending) or (pending.phase~='CONNECTING' and pending.phase~='SETTLING') or type(pending.started)=='boolean' or type(pending.deadline)=='boolean'
     or not started or not finite(started) or not deadline or not finite(deadline) or not canon.is_object(pending.to) or not canon.is_object(pending.from)
     or (role~='source' and role~='target') then
    state.server_change=nil;M.save(env,state)  -- a damaged record: the normal checks decide
    return false
  end
  local io_=server_io(env);local tunnel=server_tunnel(pending)
  local within=started<=now and now<deadline
  local function with(fields) local out=canon.decode(canon.encode(pending));for k,v in pairs(fields) do out[k]=v end;return out end
  if pending.phase=='CONNECTING' then
    if env.backend.health(pending.to.id)==true then
      S.record(io_,pending.tunnel_id,now,getd(pending,'change',nil),false)
      S.event(io_,S.PICKED,tunnel,now,getd(pending,'change',nil),getd(pending,'request',nil))
      state.server_change=with({phase='SETTLING',deadline=canon.float(now+S.SETTLE_WAIT),verified=true});M.save(env,state)  -- a resume keeps to
    elseif not within then
      local undone=M.server_apply(env,state,revision,tunnel,pending.from,io_,role)==S.PICKED
      S.event(io_,S.FAILED,tunnel,now,getd(pending,'change',nil),getd(pending,'request',nil),undone and 'rolled back' or 'rollback failed')
      state.server_change=with({phase='SETTLING',deadline=canon.float(now+S.SETTLE_WAIT),rolled_back=true});M.save(env,state)
    end
    server_publish(env,state)
    return true
  end
  local blockers,selection=env.backend.diagnostic()
  if #blockers==0 or not within then
    if #blockers==0 and role=='source' then pcall(M.server_settled,env,selection) end  -- observation-grade
    state.server_change=nil;M.save(env,state)
    return false
  end
  server_publish(env,state)
  return true
end

return M
