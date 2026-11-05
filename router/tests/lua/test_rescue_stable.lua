-- rescue_stable (03.11.2026): a reserve that failed while carrying hands the traffic back after min(primary_stable,
-- rescue_stable) seconds of primary stability (default 10 s, 0 = the old full primary_stable); default primary_stable
-- 120 s. Python twin: tests/test_rescue_stable.py (rescue_stable_cases.json, the same decisions).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local T=require('transaction')

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../rescue_stable_cases.json'))
local function none(v) return v==nil or v==canon.null end
local function copy(o) local out=canon.object({});for k,v in pairs(o) do out[k]=v end;return out end

local function fake(env,ready_upto,reserve_health)
  local asked={}
  env.backend.recovery_ready=function(id,settings) local s=pair.stable_seconds(settings);asked[#asked+1]=s;return s<=ready_upto end
  env.backend.health=function(id) if id==env.backend.selection.source.id then return true end;return reserve_health end
  return asked
end

t.test('recovery_normalized: the shared cases',function()
  for _,case in ipairs(CASES.normalized) do
    local policy=pair.recovery_normalized(case.settings)
    t.eq({policy.primary_stable,policy.rescue_stable},{case.primary_stable,case.rescue_stable},case.name)
  end
end)

t.test('stable_seconds: the shared cases',function()
  for _,case in ipairs(CASES.stable_seconds) do t.eq(pair.stable_seconds(case.settings),case.seconds,case.name) end
end)

-- The reserve's failure comes from the case for every failure model (pair.streak for 'consecutive',
-- channel_model.channel_failed for the HMM modes); channel_model.return_ready answers model_ready (default true).
local CM=require('channel_model')
local function decisions(list,check_model)
  local real_streak,real_failed,real_ready=pair.streak,CM.channel_failed,CM.return_ready
  local ok,err=pcall(function()
    for _,case in ipairs(list) do
      local env=t.env()
      local health=case.reserve_health;if none(health) then health=true end
      local asked=fake(env,case.ready_upto,health)
      local consulted={}
      pair.streak=function() return case.reserve_failed end
      CM.channel_failed=function() return case.reserve_failed end
      CM.return_ready=function(samples,id) consulted[#consulted+1]=id;if none(case.model_ready) then return true end;return case.model_ready end
      local sel=env.backend.selection
      local value=canon.object({source=sel.source.id,target=sel.target.id,confirmed=canon.float(900)})
      local hold=case.hold;if none(hold) then hold=nil end
      local d=T.committed_recovery_decision(env,value,copy(case.settings),canon.array({}),case.now or 1000,canon.object({}),hold)
      t.eq({d.action,d.reason},{case.action,case.reason},case.name)
      local want=case.asked;if none(want) then want=nil end
      t.eq(asked[#asked],want,case.name..': stability asked')
      if check_model then
        t.eq(#consulted>0,case.model_asked,case.name..': model gate consulted')
        if #consulted>0 then t.eq(consulted,{sel.source.id},case.name..': the gate looks at the primary') end
      end
    end
  end)
  pair.streak,CM.channel_failed,CM.return_ready=real_streak,real_failed,real_ready
  if not ok then error(err,0) end
end

t.test('committed_recovery_decision: the shared cases',function() decisions(CASES.decisions,false) end)

t.test('return_rule: the shared cases (Python recovery_settings.return_rule)',function()
  for _,case in ipairs(CASES.return_rule) do
    local settings=copy(case.settings)
    local hold=case.hold;if none(hold) then hold=nil end
    local ready,gate=pair.return_rule(settings,case.reserve,hold)
    t.eq({pair.stable_seconds(ready),gate},{case.seconds,case.gate},case.name)
    t.eq(canon.encode(settings),canon.encode(copy(case.settings)),case.name..': the owner settings are never changed')
  end
  t.eq(pcall(pair.return_rule,canon.object({}),'healthy'),false)
end)

t.test('combined: rescue_stable x failure model (healthy / failed reserve x hmm / hmm-fast / consecutive)',function()
  decisions(CASES.combined,true)
end)

t.test('source_ready: the shared cases',function()
  for _,case in ipairs(CASES.source_ready) do
    local env=t.env()
    local asked=fake(env,case.ready_upto,true)
    t.eq(T.source_ready(env,canon.object({source=env.backend.selection.source.id}),copy(case.settings),case.reason),case.ready,case.name)
    t.eq(asked,{case.asked},case.name..': stability asked')
  end
end)

t.test('rescue_settings: a copy with the transient marker, never part of the fingerprint',function()
  local settings=canon.object({recovery_primary_stable='300'})
  local marked=pair.rescue_settings(settings)
  t.eq(marked.rescue_return,true);t.eq(settings.rescue_return,nil);t.eq(marked.recovery_primary_stable,'300')
  t.eq(pair.recovery_normalized(marked).rescue_return,nil)
  t.eq(require('identity').fingerprint(marked),require('identity').fingerprint(settings))
  t.eq(pair.RESCUE_REASON,'RESERVE-FAILED-PRIMARY-VERIFIED')
end)

t.run()
