-- Port of tests/advisor_sim.py (deterministic synthetic network days) for test_network_advisor.lua and
-- bench_advisor.lua. Same events, the same checks every 10 s (+ a dense check 4 s after a failed primary check),
-- the same simple Auto route.
local canon=require('canon')
local J=require('netjournal')
local NULL=canon.null

local M={}
function M.new(cases)
  local S={cases=cases,primary=cases.pair.source,reserve=cases.pair.target}
  function S.failing(events,who,tt)
    for _,e in ipairs(events) do
      if e[1]=='out' and who=='P' and e[2]<=tt and tt<e[2]+e[3] then return true end
      if e[1]=='rout' and who=='R' and e[2]<=tt and tt<e[2]+e[3] then return true end
      if e[1]=='loss' and who=='P' and e[2]<=tt and tt<e[2]+e[3] then
        local k=math.floor((tt-e[2])/10)
        if math.floor((k+1)*e[4]/100.0)>math.floor(k*e[4]/100.0) then return true end
      end
    end
    return false
  end
  function S.route(events,tt)
    for _,e in ipairs(events) do
      if e[1]=='out' and e[3]>=25 and e[2]+25<=tt and tt<e[2]+e[3]+150 then return 'target' end
      if e[1]=='rout' and e[2]<=tt and tt<e[2]+e[3]+60 then return 'target' end
    end
    return 'source'
  end
  function S.sample(identifier,time,fail,dense,rtt)
    local s={id=identifier,time=time,dense=dense}
    if fail then s.code='VPN-003';s.dns_ok=true;s.https_success=0
    else s.code=NULL;s.dns_ok=true;s.https_success=3;s.rtt_ms=rtt end
    return s
  end
  function S.scenario_days(name,days)
    local events=cases.scenarios[name]
    local list={}
    if name=='quiet' then
      local flat={};for _,day in ipairs(events) do for _,e in ipairs(day) do flat[#flat+1]=e end end
      for i=1,days do list[i]=flat end
    else for i=1,days do list[i]=events end end
    return list
  end
  function S.build(days_events,offset)
    local journal=J.new()
    for i,events in ipairs(days_events) do
      local day_start=cases.base+(i-1)*86400-offset
      local tt=0.0
      while tt<86400 do
        local samples={}
        for _,who in ipairs({'P','R'}) do
          local identifier=who=='P' and S.primary or S.reserve
          local fail=S.failing(events,who,tt)
          samples[#samples+1]=S.sample(identifier,day_start+tt+(who=='P' and 0.0 or 0.5),fail,false,40+math.floor(tt/3600))
          if who=='P' and fail then
            local f2=S.failing(events,'P',tt+4.0)
            samples[#samples+1]=S.sample(identifier,day_start+tt+4.0,f2,true,40)
          end
        end
        J.observe(journal,samples,cases.pair,S.route(events,tt),day_start+tt+8.0,offset)
        tt=tt+10.0
      end
    end
    J.observe(journal,{},cases.pair,'source',cases.base+#days_events*86400-offset+1,offset)
    return journal
  end
  return S
end
return M
