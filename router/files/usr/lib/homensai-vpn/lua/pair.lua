-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
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
local DEFAULTS={failures=3,successes=2,cooldown=60,min_dwell=60,return_policy='healthy_primary',primary_successes=2,primary_stable=30,attempt_limit=3,attempt_window=15}
local RANGES={failures={3,10},successes={2,10},cooldown={60,1800},min_dwell={60,3600},primary_successes={2,10},primary_stable={30,600},attempt_limit={1,10},attempt_window={1,15}}
function M.recovery_normalized(settings)
  local result={}
  for key,default in pairs(DEFAULTS) do
    local value=settings['recovery_'..key]
    if isnone(value) then value=default end
    if key=='return_policy' then result[key]=(value=='healthy_primary' or value=='hold_reserve') and value or default
    elseif key=='attempt_limit' or key=='attempt_window' then
      local number
      if type(value)=='number' and value%1==0 then number=value
      elseif type(value)=='string' and string.find(value,'^[0-9][0-9]?[0-9]?$') then number=tonumber(value)
      else number=default end
      local lo,hi=RANGES[key][1],RANGES[key][2]
      result[key]=(lo<=number and number<=hi) and number or default
    else
      local number
      if type(value)=='number' then number=value<0 and -math.floor(-value) or math.floor(value)
      elseif type(value)=='string' and string.find(value,'^%s*[+-]?%d+%s*$') then number=tonumber(value)
      else number=default end
      local lo,hi=RANGES[key][1],RANGES[key][2]
      result[key]=math.max(lo,math.min(hi,number))
    end
  end
  return result
end
function M.valid_for(settings)
  local value=canon.is_object(settings) and settings.interval or nil
  if type(value)=='string' and string.find(value,'^[0-9][0-9]?[0-9]?$') then value=tonumber(value) end
  if type(value)~='number' or value%1~=0 or value<10 or value>300 then return 90 end
  return math.max(30,math.min(900,value*3))
end
function M.settle_for(settings) return math.max(30,math.min(600,math.floor(M.valid_for(settings)*2/3))) end

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
local FAILURES={['VPN-001']=true,['VPN-003']=true,['DNS-001']=true}
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
  local kept={}
  for _,x in ipairs(values) do if now-x<900 then kept[#kept+1]=x end end
  table.sort(kept)
  local count=0
  for _,x in ipairs(kept) do if now-x<window then count=count+1 end end
  local out={};for i,x in ipairs(kept) do out[i]=canon.float(x) end
  return canon.array(out),count<limit and #kept<16
end
local function ledger_events(env)
  local _,_,path=M.paths(env)
  local ledger=ctl.read_json(env.run,path,canon.object({events=canon.array({})}))
  return canon.is_object(ledger) and ledger.events or NULL
end
local function save_ledger(env,events,stamp)
  local _,_,path=M.paths(env)
  events[#events+1]=canon.float(stamp)
  ctl.write_json(env.run,path,canon.object({events=events}))
end

function M.require_running(env,revision)
  T.require_control_revision(env,revision)
  if env.stop() then refuse('CLIENT-STOP') end
end

function M.publish_failure(env,err)
  local code=(type(err)=='string' and ctl.code_ok(err)) and err or (is_refused(err) and ctl.code_ok(err.code) and err.code) or 'PAIR-SYSTEM-001'
  pcall(function()
    local pending=M.read_state(env)
    if next(pending)~=nil and not M.TERMINAL[pending.phase] then pending.phase='HELD';pending.recovery_error=code;M.save(env,pending) end
  end)
  local value={state='BLOCKED',mode='continuous-pair',proof_scope=M.MODE,original_restored=false,blockers=canon.array({code})}
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

function M.charge_attempt(env,settings,revision)
  M.require_running(env,revision)
  local now=env.run.wall();local policy=M.recovery_normalized(settings)
  local events,allowed=M.budget(ledger_events(env),now,policy.attempt_window*60,policy.attempt_limit)
  if not allowed or (#events>0 and now-num(events[#events])<math.max(policy.cooldown,policy.min_dwell)) then refuse('PAIR-RATE-LIMIT') end
  save_ledger(env,events,now)
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

function M.release_session(env,state,code)
  local now=env.run.wall()
  local events,allowed=M.readopt_allowed(env,now)
  local phase=T.journal_read(env).phase
  if not allowed or (phase~=nil and phase~='ROLLED-BACK') then return false end
  local _,path=M.paths(env)
  local raw=env.run.fs.read(path)
  local directory=env.persist..'/session-recovery'
  local archive=directory..'/pair-'..state.id..'-readopt-'..string.format('%d',math.floor(now))..'.json'
  if env.run.fs.read(archive)~=nil then value_error('PAIR-STATE-UNVERIFIED') end
  env.run.fs.write_atomic(archive,raw)
  if env.run.fs.read(archive)~=raw then value_error('PAIR-STATE-UNVERIFIED') end
  local resolved=canon.decode(canon.encode(state))
  resolved.phase='STOPPED';resolved.owned=canon.array({});resolved.original_restored=false;resolved.recovery_error=NULL
  resolved.operator_resolution=canon.object({reason='AUTOMATIC-EXTERNAL-CHANGE-READOPT',time=canon.float(now),archive=string.match(archive,'[^/]+$'),
    trigger=code,original_sha256=canon.sha256(raw),retired_owned=copy_list(getd(state,'owned',canon.array({}))),old_flags_restored=false})
  M.save(env,resolved)
  local list={};for i,x in ipairs(events) do list[i]=canon.float(x) end;list[#list+1]=canon.float(now)
  ctl.write_json(env.run,env.runtime..'/pair-readopt.json',canon.object({events=canon.array(list)}))
  return true
end

function M.readopt_running(env,state,request_row,revision,code)
  local handed=env.run.lock(function()
    local current=M.intent(env)
    if ctl.revision_locked(env)~=revision or current.revision~=revision or current.mode~='on' or current.id~=request_row.id or not M.release_session(env,state,code) then return false end
    ctl.write_json(env.run,(M.paths(env)),canon.object({mode='on',revision=revision,time=fwall(env),id=ctl.uuid_hex(),request_source=getd(current,'request_source','unknown')}))
    return true
  end,env.runtime)
  if not handed then return false end
  T.publish(env,{state='ARMED',mode='continuous-pair',proof_scope=M.MODE,reason='PAIR-READOPTED',blockers=canon.array({})})
  return true
end

------------------------------------------------------------------------------------------------------
-- begin / cleanup / revive (network side through env.net)
------------------------------------------------------------------------------------------------------
function M.preflight(env,settings)
  if settings.pair_auto_mode~=M.MODE or settings.terms_version~='1' then value_error('PAIR-MODE-NOT-CONFIGURED') end
  if settings.native_session_loss~='1' then value_error('SESSION-LOSS-NOT-ACCEPTED') end
  local selection=env.backend.pair_preflight(settings)  -- platform pins, acceleration, assess(), choose(), pair_interfaces.selection
  T.bind_policy_context(env,selection)
  return selection
end

function M.begin(env,settings,request)
  local selection=M.preflight(env,settings)
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
  local state=canon.object({id=request.id,phase='STARTING',started=fwall(env),revision=request.revision,network_identity=n.identity(data,managed),
    interfaces=managed,protected=n.configs(managed),owned=canon.array({}),before_flags=flags,process_bindings=getd(selection,'process_bindings',NULL),
    order=copy_list(selection.order),policy_hash=selection.hash})
  pcall(function() state.protected_static=canon.object({firewall=n.static_firewall_digest()}) end)
  state.policy_roles=P.proof(selection)
  M.save(env,state)
  env.backend.guard()
  for _,role in ipairs({'source','target'}) do
    local interface=selection[role].interface
    M.require_running(env,request.revision)
    n.quiet(20,request.revision)
    if selected[interface].disabled=='1' then
      state.owned[#state.owned+1]=interface;M.save(env,state)
      n.set_disabled(state,interface,'0',request.revision)
      n.ifup(interface,request.revision)
      n.quiet(45,request.revision)
    elseif n.client_down(interface) then
      state.owned[#state.owned+1]=interface;M.save(env,state)
      pcall(n.ifup,interface,request.revision)
      n.quiet(45,request.revision)
    end
  end
  state.phase='RUNNING';state.ran=true
  M.require_running(env,request.revision)
  env.backend.guard(env.backend.devices(),request.revision)
  M.save(env,state)
  return state
end

function M.cleanup(env,state,stop_revision)
  local n=net(env)
  local managed=M.state_interfaces(state)
  T.bind_policy_context(env,state)
  local value=T.journal_read(env)
  local context=P.metadata(value)
  if context~=nil and (not same_list(context.session_order,state.order) or value.hash~=state.policy_hash) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
  state.phase='STOPPING';M.save(env,state)
  local phase=value.phase
  if phase=='ARMED' or phase=='APPLYING' or phase=='WAIT-CLIENT' or phase=='RESTORING' then
    if value.activation_reapply==true and same_list(value.before,value.after) and env.deps and env.deps.activation_finalize then
      env.deps.activation_finalize(env,state,value,true)
    else value_error('PAIR-RECOVERY-REQUIRED') end
  end
  if phase=='COMMITTED' or phase=='HELD-ON-RESERVE' then
    local finished
    if context~=nil then finished=T.finish_committed(env,value,'PAIR-STOPPED',state.order) else finished=T.finish_committed(env,value,'PAIR-STOPPED') end
    if not finished then state.phase='HELD';M.save(env,state);return false end
  else
    local lo,lh=env.backend.order()
    if context~=nil and P.state_order_matches(state,value,lo,lh) and not order_is(env,state.order,state.policy_hash) then
      if env.backend.recovery_ready(value[P.role(context,state.order)],env.backend.policy().settings)~=true then value_error('PAIR-RECOVERY-REQUIRED') end
      require('rollback').rollback(env,value,'PAIR-STOPPED',state.order)
    end
  end
  if not order_is(env,state.order,state.policy_hash) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
  for i=#state.owned,1,-1 do
    local interface=state.owned[i]
    if n.identity(n.network(),managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed),{firewall=true}) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
    n.ifdown(interface)
    n.quiet(45)
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
  if not ok then M.publish_failure(env,err);return false end
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

------------------------------------------------------------------------------------------------------
-- tick
------------------------------------------------------------------------------------------------------
function M.reapply_missing_policy(env,state,settings,revision,value,observed)
  if isnone(state.policy_roles) then return false end
  local requested=M.intent(env)
  if requested.mode~='on' or requested.revision~=revision or requested.id~=state.id then refuse('CLIENT-STOP') end
  local blockers,selection=env.backend.diagnostic()
  if #blockers>0 or not selection then
    local identity=state.policy_roles
    T.publish(env,{state='BLOCKED',mode='continuous-pair',proof_scope=M.MODE,source=identity.source_id,target=identity.target_id,
      blockers=canon.array(#blockers>0 and blockers or {'PAIR-POLICY-UNVERIFIED'}),readiness_verified=false,kernel_policy_verified=false})
    return true
  end
  local lo,lh=env.backend.order()
  if canon.encode(P.proof(selection))~=canon.encode(state.policy_roles) or not P.state_order_matches(state,value,lo,lh) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
  local kernel=env.backend.attest_policy(selection)
  if kernel.verified==true then
    M.remember_selected(env,state,kernel)
    if observed then observed.selection=selection;observed.kernel=kernel end
    return false
  end
  if kernel.repairable_missing~=true then
    T.publish(env,{state='BLOCKED',reason='KERNEL-POLICY-UNVERIFIED',blockers=canon.array({'KERNEL-POLICY-UNVERIFIED'}),source=selection.source.id,target=selection.target.id,mode='continuous-pair',proof_scope=M.MODE})
    return true
  end
  local destination=P.role(state.policy_roles,selection.order)
  if not isnone(state.manual_hold) and state.manual_hold~=destination then refuse('PAIR-MANUAL-HOLD-UNVERIFIED') end
  local recovery=M.recovery_normalized(settings);local now=env.run.wall()
  local events,allowed=M.budget(ledger_events(env),now,recovery.attempt_window*60,recovery.attempt_limit)
  if not allowed or (#events>0 and now-num(events[#events])<math.max(recovery.cooldown,recovery.min_dwell)) then
    T.publish(env,{state='BLOCKED',reason='KERNEL-POLICY-UNVERIFIED',blockers=canon.array({'KERNEL-POLICY-UNVERIFIED','PAIR-RATE-LIMIT'}),source=selection.source.id,target=selection.target.id,mode='continuous-pair',proof_scope=M.MODE})
    return true
  end
  local until_=M.configure_lease(env,state)
  M.require_running(env,revision)
  T.attempt(env,selection,until_,false,{control_revision=revision,pair_destination=destination,pair_session_order=state.order,pair_reapply=true,
    on_dispatch=function() M.charge_attempt(env,settings,revision) end})
  M.resume_running(env,state)
  return true
end

function M.tick(env,settings,revision)
  local request_row=canon.object({})
  local ok,result=pcall(function()
    request_row=M.intent(env)
    local state=M.read_state(env)
    local has_state=next(state)~=nil
    local running=request_row.mode=='on' and request_row.revision==revision
    local relevant=running or (has_state and not M.TERMINAL[state.phase])
    if not relevant then return false end
    if not running then
      if has_state and not M.TERMINAL[state.phase] then if not M.cleanup(env,state) then return true end end
      T.publish(env,{state='STOPPED',mode='continuous-pair',proof_scope=M.MODE,original_restored=(not has_state) or state.phase=='STOPPED',blockers=canon.array({})})
      return true
    end
    if not has_state or state.id~=request_row.id then
      if settings.pair_auto_mode~=M.MODE then value_error('PAIR-MODE-NOT-CONFIGURED') end
      if has_state and not M.TERMINAL[state.phase] then value_error('PAIR-RECOVERY-REQUIRED') end
      state=M.begin(env,settings,request_row)
    end
    T.bind_policy_context(env,state)
    if settings.pair_auto_mode~=M.MODE then value_error('PAIR-MODE-NOT-CONFIGURED') end
    local n=net(env)
    local managed=M.state_interfaces(state)
    local rows=n.network()
    if n.identity(rows,managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if n.changed(state,n.configs(managed)) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
    local value=T.journal_read(env)
    local status=ctl.read_json(env.run,T.paths(env).status,canon.object({}))
    local manual=require('manual')
    if manual.consume(env,state,settings,revision) then return true end
    if M.revive(env,state,revision,value,rows) then return true end
    if manual.held_reserve(env,state,value,settings,status) then return true end
    local observed={}
    if M.reapply_missing_policy(env,state,settings,revision,value,observed) then return true end
    local kernel=observed.kernel
    local applied_target=(value.phase=='COMMITTED' or value.phase=='HELD-ON-RESERVE')
      or (value.activation_reapply==true and value.phase=='ROLLED-BACK' and value.trial_nonce==state.id and value.control_revision==state.revision and state.revision==revision)
    if applied_target and P.current_role(value)~='source' then
      local now=env.run.wall()
      local decision=T.committed_recovery_decision(env,value,settings,getd(status,'samples',canon.array({})),now,status)
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
    if #blockers>0 then
      local age=env.run.wall()-num(state.started)
      local preparing=0<=age and age<=180
      for _,x in ipairs(blockers) do
        if x~='VENDOR-SETTLING' and x~='OBSERVATION-STALE' and x~='PROFILE-IDENTITY-CHANGED' and x~='RESERVE-NOT-CONNECTED' then preparing=false end
      end
      T.publish(env,{state=preparing and 'ARMED' or 'BLOCKED',mode='continuous-pair',proof_scope=M.MODE,reason=preparing and 'PAIR-WAITING-PROBES' or NULL,blockers=canon.array(blockers)})
      return true
    end
    local lo,lh=env.backend.order()
    if not P.state_order_matches(state,value,lo,lh) then value_error('PAIR-EXTERNAL-POLICY-CHANGE') end
    M.resume_running(env,state)
    local now=env.run.wall()
    local recovery=M.recovery_normalized(settings)
    local age=M.valid_for(settings)
    local samples=getd(status,'samples',canon.array({}))
    local failed=M.streak(samples,selection.source.id,recovery.failures,now,age,false,selection.source,env)
    local healthy=M.streak(samples,selection.target.id,recovery.successes,now,age,true,selection.target,env)
    local diagnosis=env.deps and env.deps.diagnose and env.deps.diagnose(status,selection.source.id,now,settings) or {}
    local events,permitted=M.budget(ledger_events(env),now,recovery.attempt_window*60,recovery.attempt_limit)
    local dwell=#events==0 or now-num(events[#events])>=math.max(recovery.cooldown,recovery.min_dwell)
    local since=num(getd(getd(state,'selected_policy',canon.object({})),'since',nil)) or now
    if kernel and kernel.role=='target' and isnone(state.manual_hold) and recovery.return_policy=='healthy_primary'
       and now-since>=recovery.min_dwell and permitted and dwell and env.backend.recovery_ready(selection.source.id,settings)==true then
      local until_=M.configure_lease(env,state)
      local b2,fresh=env.backend.diagnostic()
      if #b2>0 then value_error('PAIR-READINESS-CHANGED') end
      T.attempt(env,fresh,until_,false,{control_revision=revision,pair_destination='source',pair_return=true,pair_session_order=state.order,
        on_dispatch=function() M.charge_attempt(env,settings,revision) end})
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
    if failed and healthy and permitted and dwell and not diagnosis.suppress_switch then
      if not isnone(state.manual_hold) then state.manual_hold=nil;M.save(env,state) end
      local until_=M.configure_lease(env,state)
      local b2,fresh=env.backend.diagnostic()
      if #b2>0 then value_error('PAIR-READINESS-CHANGED') end
      T.attempt(env,fresh,until_,false,{probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=recovery.failures,required_successes=recovery.successes}),
        control_revision=revision,pair_session_order=state.order,on_dispatch=function() M.charge_attempt(env,settings,revision) end})
    else
      local reason
      if not permitted then reason='PAIR-RATE-LIMIT'
      elseif diagnosis.suppress_switch then reason=diagnosis.code
      elseif state.manual_hold=='source' then reason='PAIR-MANUAL-HOLD-PRIMARY'
      else reason='PAIR-WATCHING' end
      T.publish(env,{state='OBSERVING',mode='continuous-pair',readiness_verified=true,certified=false,proof_scope=M.MODE,external_lan_verified=false,
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
  return true
end

return M
