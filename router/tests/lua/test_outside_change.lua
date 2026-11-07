-- Owner decision 07.11.2026 ('by risk + notification', review F-32 / A9 finding 2): the Lua twin of
-- test_outside_change_policy.py. Shared cases: tests/outside_change_cases.json (pair.readopt_class); the running
-- session's tick: wireless/dhcp/dns adopted and told, wireguard held and told, the budget untouched by a hold.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local ctl=require('auto_control')

local function cases()
  local f=io.open(t.here..'/../outside_change_cases.json','rb');local text=f:read('*a');f:close()
  return canon.decode(text)
end

-- a net stub whose changed() follows net.lua exactly (a missing digest is unreadable, firewall legacy raw match)
local function net_for(observed,raw_firewall)
  return {configs=function() if observed==nil then error(setmetatable({code='PAIR-CONFIG-UNVERIFIED'},ctl.Refused),0) end;return observed end,
    changed=function(state,obs,skip)
      local skipped={};for k,v in pairs(skip or {}) do if type(k)=='number' then skipped[v]=true else skipped[k]=v end end
      for name,sha in pairs(state.protected) do
        if name~='route_policy' and not skipped[name] then
          if obs[name]==nil then error(setmetatable({code='PAIR-CONFIG-UNVERIFIED'},ctl.Refused),0) end
          if obs[name]~=sha and not (name=='firewall' and raw_firewall==sha) then return true end
        end
      end
      return false
    end,
    network=function() return canon.array({}) end,identity=function() return string.rep('b',64) end,client_down=function() return false end}
end

t.test('readopt_class: every shared case (tests/outside_change_cases.json) decides as in Python',function()
  local data=cases()
  t.truthy(#data.cases>=16,'the shared cases')
  for _,case in ipairs(data.cases) do
    local protected=canon.object({});for k,v in pairs(data.protected) do protected[k]=v end
    for k,v in pairs(case.protected_extra or {}) do protected[k]=v end
    local observed=nil
    if case.observed~=canon.null then
      observed=canon.object({});for k,v in pairs(protected) do observed[k]=v end
      for k,v in pairs(case.observed) do observed[k]=v end
    end
    local env=t.env();env.net=net_for(observed,'raw')
    local state=canon.object({protected=protected,interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'})})
    local row=pair.readopt_class(env,state,case.trigger,5.0)
    t.eq({row.decision,row.trigger},{case.decision,case.trigger},case.name);t.eq(canon.number(row.time),5,case.name)
    local got={};for i,x in ipairs(row.packages) do got[i]=x end
    local want={};for i,x in ipairs(case.packages) do want[i]=x end
    t.eq(table.concat(got,','),table.concat(want,','),case.name)
    t.truthy(not string.find(canon.encode(row),'w2',1,true),'names only, never a digest')
  end
end)

local function running(env,protected)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=string.rep('11',16),request_source='manual'})))
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(env.run.wall()-1000),revision=env.revision,network_identity=string.rep('b',64),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=protected,owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=env.backend.selection.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(env.backend.selection)})
  pair.save(env,state)
  return state
end

t.test('pair.tick: a Wi-Fi/DHCP change is adopted and told; a wireguard change is HELD with its class, no adoption, no budget spent',function()
  local data=cases()
  local protected=canon.object({});for k,v in pairs(data.protected) do protected[k]=v end
  local observed=canon.object({});for k,v in pairs(protected) do observed[k]=v end;observed.wireless='l2';observed.dhcp='d2'
  local env=t.env();env.net=net_for(observed,'raw')
  running(env,protected)
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  local saved=pair.read_state(env)
  t.eq(saved.phase,'STOPPED');t.eq(saved.operator_resolution.adopted_by,'automatic');t.eq(saved.operator_resolution.outside_change.decision,'ADOPT')
  t.eq({saved.operator_resolution.outside_change.packages[1],saved.operator_resolution.outside_change.packages[2]},{'dhcp','wireless'})
  t.eq(saved.outside_change,nil)
  local row=pair.intent(env);t.eq(row.mode,'on');t.truthy(row.id~=string.rep('11',16),'a fresh request')
  local status=t.read(env,env.runtime..'/native-status.json');t.eq(status.reason,'PAIR-READOPTED');t.eq(status.outside_change.packages[2],'wireless')
  t.eq(#t.read(env,env.runtime..'/pair-readopt.json').events,1)
  -- wireguard: HELD, told, nothing adopted
  observed=canon.object({});for k,v in pairs(protected) do observed[k]=v end;observed.wireguard='w2'
  env=t.env();env.net=net_for(observed,'raw')
  running(env,protected)
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  saved=pair.read_state(env)
  t.eq({saved.phase,saved.recovery_error},{'HELD','PAIR-EXTERNAL-CONFIG-CHANGE'})
  t.eq({saved.outside_change.decision,saved.outside_change.packages[1],#saved.outside_change.packages},{'HOLD','wireguard',1})
  t.eq(saved.operator_resolution,nil);t.eq(pair.intent(env).id,string.rep('11',16))
  status=t.read(env,env.runtime..'/native-status.json')
  t.eq({status.state,status.reason,status.blockers[1],status.outside_change.packages[1]},{'BLOCKED','PAIR-OUTSIDE-CHANGE-HELD','PAIR-EXTERNAL-CONFIG-CHANGE','wireguard'})
  t.eq(t.read(env,env.runtime..'/pair-readopt.json'),nil)
  -- the next pass keeps the hold and the class
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  t.eq(pair.read_state(env).phase,'HELD');t.eq(t.read(env,env.runtime..'/native-status.json').reason,'PAIR-OUTSIDE-CHANGE-HELD')
end)

t.test('readopt_running: order mismatch, policy change and an unreadable class are HELD; release_session records the owner Start',function()
  local data=cases()
  local protected=canon.object({});for k,v in pairs(data.protected) do protected[k]=v end
  for _,code in ipairs({'SOURCE-ORDER-MISMATCH','PAIR-EXTERNAL-POLICY-CHANGE'}) do
    local env=t.env();env.net=net_for(protected,'raw')
    local state=running(env,protected)
    t.eq(pair.readopt_running(env,state,pair.intent(env),env.revision,code),false)
    local saved=pair.read_state(env)
    t.eq({saved.phase,saved.recovery_error,saved.outside_change.decision,saved.outside_change.packages[1]},{'HELD',code,'HOLD','route_policy'},code)
    t.eq(pair.intent(env).id,string.rep('11',16))
  end
  local env=t.env();env.net=net_for(nil,'raw')
  local state=running(env,protected)
  t.eq(pair.readopt_running(env,state,pair.intent(env),env.revision,'PAIR-EXTERNAL-CONFIG-CHANGE'),false)
  local saved=pair.read_state(env);t.eq({saved.phase,saved.outside_change.why,#saved.outside_change.packages},{'HELD','UNREADABLE',0})
  -- the owner's Start: release_session without a verdict records adopted_by='owner-start' and the hold's package names
  t.eq(pair.release_session(env,saved,saved.recovery_error),true)
  local released=pair.read_state(env)
  t.eq({released.phase,released.operator_resolution.adopted_by,released.operator_resolution.outside_change.why},{'STOPPED','owner-start','OWNER-START'})
  t.eq(released.outside_change,nil);t.eq(#t.read(env,env.runtime..'/pair-readopt.json').events,1)
  t.eq(pair.READOPT_LIMIT,3)
end)

t.run()
