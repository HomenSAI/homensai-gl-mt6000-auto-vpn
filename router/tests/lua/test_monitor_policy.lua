-- probe_policy.lua: levels, forced boost, the boost episode and its decision log, dense episode closing.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local policy=require('probe_policy')

local function memory()
  local files={}
  return files,{read_json=function(path,default) local v=files[path];if v==nil then return default end;return canon.decode(v) end,
    write_json=function(path,value) files[path]=canon.encode(value) end}
end
local PAIR={source='wireguard:peer_7',target='wireguard:peer_8'}
local function row(id,code,https,dns) return canon.object({id=id,code=code==nil and canon.null or code,https_success=https or 3,dns_ok=dns==nil and true or dns}) end
local GOOD={row('wireguard:peer_7'),row('wireguard:peer_8')}
local BAD={row('wireguard:peer_7','VPN-003',1),row('wireguard:peer_8')}

t.test('level, interval and measure: owner level, legacy interval mapping, digit strings',function()
  t.eq(policy.level({probe_level='3'}),3);t.eq(policy.level({probe_level=9,interval=60}),1);t.eq(policy.level({interval=30}),2)
  t.eq(policy.level({interval='15'}),4);t.eq(policy.level({}),5)
  t.eq(policy.measure_interval({probe_level=2}),120);t.eq(policy.measure_interval({probe_level=2,measure_interval='45'}),45)
  t.eq(policy.boost_enabled({probe_level=1,probe_boost='0'}),true,'levels 1-2 always boost (owner decision)')
  t.eq(policy.boost_enabled({probe_level=4,probe_boost='0'}),false);t.eq(policy.boost_enabled({probe_level=4}),true)
  t.eq(policy.response_metric({response_metric='websites'}),'websites');t.eq(policy.response_metric({response_metric='x'}),'icmp-1.1.1.1')
  t.eq(policy.failing(row('a',nil,2,true)),false);t.eq(policy.failing(row('a',nil,1,true)),true);t.eq(policy.failing(row('a',nil,3,false)),true)
  t.eq(policy.failing(canon.object({id='a',code=canon.null,dns_ok=true})),true,'no https_success: failing')
end)

t.test('owner ping interval and its freshness window (probe_policy.ping_interval/ping_valid_for)',function()
  t.eq(policy.ping_interval({}),60)
  for _,c in ipairs({{10,10},{'10',10},{300,300},{'120',120},{5,60},{0,60},{310,60},{15,60},{'15',60},{'1e2',60},{'',60},{'abc',60},{-10,60},{true,60}}) do
    t.eq(policy.ping_interval({ping_interval=c[1]}),c[2],tostring(c[1]))
  end
  t.eq(policy.ping_interval({ping_interval=canon.decode('60.0')}),60);t.eq(policy.ping_interval({ping_interval=canon.null}),60)
  t.eq(policy.ping_interval({probe_level=5,measure_interval=30}),60,'the probe level no longer sets the ping cadence')
  for _,c in ipairs({{{ping_interval=10,interval=10},45},{{ping_interval=20,interval=10},45},{{ping_interval=30,interval=10},60},{{},105},
      {{ping_interval=10,interval=60},105},{{ping_interval=300,interval=10},465},{{ping_interval=120,interval=30},195}}) do
    t.eq(policy.ping_valid_for(c[1]),c[2])
  end
  local _,io_=memory()
  local p=policy.Booster('/run/hv','/etc/hv',io_):public({probe_level=1,interval=60,ping_interval='20'},1000)
  t.eq(p.ping_interval,20);t.eq(p.effective_ping_interval,60);t.eq(p.ping_valid_for,105);t.eq(p.measure_interval,300)
end)

t.test('a level change is recorded once; the state goes to RAM, the decisions to flash',function()
  local files,io_=memory()
  local b=policy.Booster('/run/hv','/etc/hv',io_)
  local settings={probe_level='3',interval='20',measure_interval='60',probe_boost='1'}
  local rows=b:observe(settings,GOOD,PAIR,'OBSERVING',1000)
  t.eq(#rows,1);t.eq(rows[1].kind,'level');t.eq(rows[1].level,3);t.eq(rows[1].interval,20);t.eq(rows[1].result,'applied');t.eq(rows[1].sequence,1)
  t.eq(#b:observe(settings,GOOD,PAIR,'OBSERVING',1010),0,'unchanged level: nothing recorded')
  local state=canon.decode(files['/run/hv/probe-boost.json'])
  t.eq(state.active,false);t.eq(state.level,{3,20,60,true})
  t.eq(#canon.decode(files['/etc/hv/probe-history.json']),1)
  local again=policy.Booster('/run/hv','/etc/hv',io_)
  t.eq(#again:observe(settings,GOOD,PAIR,'OBSERVING',1020),0,'the state survives a restart')
end)

t.test('boost episode: start on a watched failure, faster cadence, end as false alarm with a rest',function()
  local files,io_=memory()
  local b=policy.Booster('/run/hv','/etc/hv',io_)
  local settings={probe_level=1}
  b:observe(settings,GOOD,PAIR,'OBSERVING',1000)
  local rows=b:observe(settings,BAD,PAIR,'OBSERVING',1060)
  t.eq(rows[1].kind,'boost-start');t.eq(rows[1].profile,'wireguard:peer_7');t.eq(rows[1].role,'source');t.eq(rows[1].code,'VPN-003')
  t.eq(b:active(),true);t.eq(b:interval(settings,1060),10);t.eq(b:measure(settings),30)
  local public=b:public(settings,1060)
  t.eq(public.boost_active,true);t.eq(public.boost_trigger.profile,'wireguard:peer_7');t.eq(canon.number(public.boost_until),1660)
  t.eq(public.effective_interval,10);t.eq(public.levels['1'],{60,300});t.eq(public.suspicion,canon.null)
  rows=b:observe(settings,GOOD,PAIR,'OBSERVING',1700)
  t.eq(rows[1].kind,'boost-end');t.eq(rows[1].result,'false-alarm');t.eq(rows[1].duration,640);t.eq(rows[1].failures,1)
  t.eq(b:active(),false);t.eq(canon.number(b.state.rest_until),2300);t.eq(b.state.rest_profile,'wireguard:peer_7')
  t.eq(#b:observe(settings,BAD,PAIR,'OBSERVING',1710),0,'resting: no new episode for one hold')
  local history=canon.decode(files['/etc/hv/probe-history.json'])
  t.eq(#history,3);t.eq(history[3].sequence,3)
end)

t.test('boost: confirmed failures, switch and disabled endings; no start outside watching states',function()
  local _,io_=memory()
  local b=policy.Booster('/run/hv','/etc/hv',io_)
  local settings={probe_level=5}
  b:observe(settings,GOOD,PAIR,'OBSERVING',0)
  t.eq(#b:observe(settings,BAD,PAIR,'ARMED',10),0,'not watching: no episode')
  b:observe(settings,BAD,PAIR,'OBSERVING',20)
  b:observe(settings,BAD,PAIR,'OBSERVING',30);b:observe(settings,BAD,PAIR,'OBSERVING',40)
  local rows=b:observe(settings,BAD,PAIR,'OBSERVING',700)
  t.eq(rows[1].result,'failure-confirmed')
  b=policy.Booster('/run/hv','/etc/hv',io_)
  b.state=canon.object({active=false})
  b:observe(settings,BAD,PAIR,'COMMITTED',3000)
  rows=b:observe(settings,BAD,PAIR,'APPLYING',3010)
  t.eq(b.state.switched,true)
  rows=b:observe({probe_level=5,probe_boost='0'},BAD,PAIR,'COMMITTED',3020)
  local ended
  for _,r in ipairs(rows) do if r.kind=='boost-end' then ended=r end end
  t.eq(ended.result,'disabled')
end)

t.test('a dense episode carried from the Python monitor ends by the same rules',function()
  local files,io_=memory()
  files['/run/hv/probe-boost.json']=canon.encode(canon.object({active=false,dense=canon.object({profile='wireguard:peer_7',role='source',reason='rx-stall',
    started=1000,['until']=1060,native_state='OBSERVING',checks=0,failures=0,good=0,reserve_good=0,last_code=canon.null})}))
  local b=policy.Booster('/run/hv','/etc/hv',io_)
  local settings={probe_level=3}
  t.eq(b:interval(settings,1010),4,'dense cadence');t.eq(b:public(settings,1010).suspicion.reason,'rx-stall')
  b:observe(settings,GOOD,PAIR,'OBSERVING',1010)
  local rows=b:observe(settings,GOOD,PAIR,'OBSERVING',1014)
  local ended
  for _,r in ipairs(rows) do if r.kind=='suspicion-end' then ended=r end end
  t.eq(ended.result,'false-alarm');t.eq(ended.checks,2);t.eq(ended.rest,30)
  t.eq(b.state.dense,nil);t.eq(b.state.suspicion_rest['wireguard:peer_7'].false_alarms,1)
  t.eq(b.state.streaks['wireguard:peer_7'].failures,0)
  t.eq(b:suspect(settings,{{profile='wireguard:peer_7',reason='rx-stall'}},PAIR,'OBSERVING',1020),false,'resting after a false alarm')
  t.eq(b:suspect(settings,{{profile='wireguard:peer_8',reason='link-missing',evidence={stalled_s=5,secret='x'}}},PAIR,'OBSERVING',1020),true)
  t.eq(b.state.dense.evidence,{stalled_s=5})
end)

t.run()
