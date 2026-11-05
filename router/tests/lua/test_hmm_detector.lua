-- Channel-failure detector (lua/channel_model.lua; option failure_model 'hmm' | 'hmm-fast' | 'consecutive').
-- Python twin: tests/test_hmm_detector.py over the same tests/hmm_detector_cases.json (generated from
-- channel_model.py): every probability within the file's tolerance (1e-9), every decision identical; plus the
-- probe_policy model episodes, the committed return gate and an allocation check of the hot path.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local CM=require('channel_model')
local NULL=canon.null
local N=canon.number

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../hmm_detector_cases.json'))
local PROFILE=CASES.profile
local TOL=N(CASES.tolerance)

local function near(a,b,msg)
  a,b=N(a),N(b)
  if a==nil or b==nil or math.abs(a-b)>TOL then error((msg or 'not near')..': '..tostring(a)..' vs '..tostring(b),2) end
end
local function sample(r,gen)
  local s=canon.object({id=(r.id~=nil and r.id~=NULL) and r.id or PROFILE.id,time=canon.float(N(r.t)),code=r.code,dns_ok=r.dns_ok,
    https_success=r.https,interface=PROFILE.interface,vendor_tunnel_id=PROFILE.vendor_tunnel_id,
    vendor_generation=gen or ((r.gen~=nil and r.gen~=NULL) and r.gen or PROFILE.vendor_generation)})
  if type(r.dense)=='boolean' then s.dense=r.dense end
  return s
end
local function samples(rows) local out=canon.array({});for i,r in ipairs(rows) do out[i]=sample(r) end;return out end
local function settings(model) return canon.object({failure_model=model}) end

t.test('constants equal the Python module',function()
  for _,model in ipairs({'hmm','hmm-fast'}) do
    local p,want=CM.params(model),CASES.constants[model]
    near(p.theta,want.theta,'theta');near(p.total,want.total,'total')
    for i=1,5 do near(p.dur[i],want.dur[i],'dur');near(p.ratio[i],want.ratio[i],'ratio');near(p.weight[i],want.weight[i],'weight') end
  end
  for k,v in pairs(CASES.constants.module) do near(CM[k],v,k) end
  for i=1,6 do for j=1,6 do near(CM.EMIS[i][j],CASES.constants.EMIS[i][j],'EMIS') end end
  for i=1,5 do near(CM.LAM[i],CASES.constants.LAM[i],'LAM') end
  t.eq(CM.params('consecutive'),nil)
  for _,pair in ipairs(CASES.names) do t.eq(CM.name(canon.object({failure_model=pair[1]})),pair[2]) end
  t.eq(CM.name(nil),'hmm')
end)

t.test('steps: the same probabilities after every sample',function()
  for _,case in ipairs(CASES.steps) do
    local p=CM.params(case.model);local pi={1.0,0,0,0,0,0}
    for i,s in ipairs(case.seq) do
      CM.step(pi,N(s[1]),N(s[2]),s[3],p)
      for k=1,6 do near(pi[k],case.pi[i][k],'pi') end
      near(CM.persist(pi,p),case.persist[i],'persist')
    end
    near(CM.remaining(pi,p),case.remaining,'remaining')
  end
end)

t.test('evaluate: the shared cases',function()
  for _,case in ipairs(CASES.evaluate) do
    local v=CM.evaluate(samples(case.rows),PROFILE.id,N(case.now),N(case.max_age),case.model,case.profile and PROFILE or nil,nil)
    local want=case.expect
    t.eq(v==nil,want==NULL,case.name)
    if v then
      for k=1,6 do near(v.pi[k],want.pi[k],case.name..' pi') end
      for _,key in ipairs({'persist','p_bad','p_healthy','remaining'}) do near(v[key],want[key],case.name..' '..key) end
      t.eq(v.time==nil and NULL or v.time,want.time==NULL and NULL or N(want.time),case.name..' time')
      for _,key in ipairs({'observations','failed','suspect','healthy'}) do t.eq(v[key],want[key],case.name..' '..key) end
    end
  end
end)

t.test('channel_failed and return_ready: the shared cases',function()
  for _,case in ipairs(CASES.channel_failed) do
    t.eq(CM.channel_failed(samples(case.rows),PROFILE.id,case.count,N(case.now),N(case.max_age),settings(case.model),PROFILE,nil),case.expect,case.name..' '..case.model)
  end
  for _,case in ipairs(CASES.return_ready) do
    t.eq(CM.return_ready(samples(case.rows),PROFILE.id,case.count,N(case.now),N(case.max_age),settings(case.model),PROFILE,nil),case.expect,case.name..' '..case.model)
  end
end)

t.test('streams of the tick simulation: Auto decides at the same publications',function()
  local profile=canon.object({});for k,v in pairs(PROFILE) do profile[k]=v end
  profile.vendor_changed_at=canon.float(-1e6)
  for _,case in ipairs(CASES.streams) do
    local seen=canon.array({})
    for i,r in ipairs(case.rows) do
      seen[#seen+1]=sample(r)
      local pub,want=N(case.decisions[i][1]),case.decisions[i][2]
      t.eq(CM.channel_failed(seen,PROFILE.id,3,pub,30,settings(case.model),profile,nil),want,case.name..' at '..pub)
    end
    if case.final~=NULL then
      local v=CM.evaluate(seen,PROFILE.id,N(case.decisions[#case.decisions][1]),30,case.model,nil,nil)
      for k=1,6 do near(v.pi[k],case.final.pi[k],case.name..' final pi') end
    end
  end
end)

t.test('public and row_view: the shared cases',function()
  for _,case in ipairs(CASES.public) do
    local v={};for k,x in pairs(case.view) do v[k]=x end
    v.time=N(case.view.time);for _,k in ipairs({'persist','p_bad','p_healthy','remaining'}) do v[k]=N(v[k]) end
    local got=CM.public(v)
    for _,k in ipairs({'p_bad','p_healthy','persist','remaining_s'}) do near(got[k],case.expect[k],k) end
    for _,k in ipairs({'model','failed','suspect','observations'}) do t.eq(got[k],case.expect[k],k) end
  end
  for _,case in ipairs(CASES.row_view) do
    local list=samples(case.rows)
    list[#list+1]=sample({t=case.other_generation_at,code=NULL,dns_ok=true,https=3},CASES.other_generation)
    local got=CM.row_view(list,PROFILE,N(case.now),N(case.max_age),settings(case.model))
    t.eq(got==nil,case.expect==NULL,case.model)
    if got then
      for _,k in ipairs({'p_bad','p_healthy','persist','remaining_s'}) do near(got[k],case.expect[k],k) end
      for _,k in ipairs({'model','failed','suspect','observations'}) do t.eq(got[k],case.expect[k],k) end
      t.eq(N(got.time),N(case.expect.time))
    end
  end
end)

t.test('the hot path allocates nothing and is numerically stable',function()
  local p=CM.params('hmm');local pi={1.0,0,0,0,0,0}
  collectgarbage('collect');collectgarbage('stop')
  local before=collectgarbage('count')
  local dts={0,1e-9,4,10,600}
  for i=1,100000 do CM.step(pi,dts[i%5+1],i%3,i%2==0,p) end
  local grown=collectgarbage('count')-before
  collectgarbage('restart')
  t.truthy(grown<1,'step allocated '..grown..' KB')
  local sum=0;for k=1,6 do t.truthy(pi[k]==pi[k] and pi[k]>=CM.FLOOR*0.99,'finite, above the floor');sum=sum+pi[k] end
  t.truthy(math.abs(sum-1)<1e-12,'a distribution')
  local t0=os.clock();for i=1,100000 do CM.step(pi,10,i%3,false,p) end
  io.stderr:write(string.format('channel_model.step: %.2f us per sample (this host)\n',(os.clock()-t0)/100000*1e6))
end)

t.test('invalid input never decides',function()
  local rows=samples({{t=1100,code=NULL,dns_ok=true,https=3},{t=1110,code='VPN-003',dns_ok=true,https=0}})
  t.eq(CM.evaluate(nil,PROFILE.id,1115,30,'hmm'),nil)
  t.eq(CM.evaluate(rows,PROFILE.id,0/0,30,'hmm'),nil)
  t.eq(CM.evaluate(rows,PROFILE.id,1115,0,'hmm'),nil)
  t.eq(CM.evaluate(rows,PROFILE.id,1115,math.huge,'hmm'),nil)
  t.eq(CM.evaluate(rows,PROFILE.id,1115,30,'other'),nil)
  t.eq(CM.channel_failed(nil,'x',3,1115,30,canon.object({})),false)
  t.eq(CM.return_ready(nil,'x',2,1115,30,canon.object({})),false)
  t.eq(CM.return_ready(nil,'x',2,1115,30,settings('consecutive')),true)
end)

local function booster()
  local files={}
  local io_={read_json=function(path,default) local v=files[path];if v==nil then return default end;return v end,
    write_json=function(path,value) files[path]=value end}
  return require('probe_policy').Booster('/r','/p',io_)
end
local PAIR=canon.object({source='a',target='b'})
local function rows(a_ok,b_ok)
  if b_ok==nil then b_ok=true end
  local function r(id,ok) return canon.object({id=id,code=ok and NULL or 'VPN-003',dns_ok=true,https_success=ok and 3 or 0}) end
  return canon.array({r('a',a_ok),r('b',b_ok)})
end
local function ends(recorded) local out={};for _,r in ipairs(recorded) do if r.kind=='suspicion-end' then out[#out+1]=r.result end end;return out end

t.test('probe_policy: the model suspicion starts an episode and the model ends it',function()
  local b=booster();local s=canon.object({interval=10,failure_model='hmm'})
  local suspect={a={suspect=true,failed=false,p_bad=0.3,persist=0.2}}
  b:observe(s,rows(false),PAIR,'OBSERVING',1000,suspect)
  t.eq(b:dense(1000).reason,'model');t.eq(b:interval(s,1000),4)
  for _,now in ipairs({1004,1008,1012}) do b:observe(s,rows(false),PAIR,'OBSERVING',now,suspect) end
  t.truthy(b:dense(1012)~=nil,'three failures do not end it while the model is undecided')
  t.eq(ends(b:observe(s,rows(false),PAIR,'OBSERVING',1016,{a={suspect=true,failed=true}})),{'failure-confirmed'})
  b:observe(s,rows(false),PAIR,'OBSERVING',1020,{a={suspect=true,failed=true}})
  t.eq(b:dense(1020),nil,'a decided model starts nothing')
end)

t.test('probe_policy: false alarm needs the suspicion gone; only the channel carrying traffic',function()
  local b=booster();local s=canon.object({interval=10})
  b:observe(s,rows(false),PAIR,'OBSERVING',1000,{a={suspect=true,failed=false}})
  for _,now in ipairs({1004,1008}) do b:observe(s,rows(true),PAIR,'OBSERVING',now,{a={suspect=true,failed=false}}) end
  t.truthy(b:dense(1008)~=nil)
  t.eq(ends(b:observe(s,rows(true),PAIR,'OBSERVING',1012,{a={suspect=false,failed=false}})),{'false-alarm'})
  local c=booster()
  c:observe(s,rows(true,false),PAIR,'OBSERVING',1000,{b={suspect=true,failed=false}});t.eq(c:dense(1000),nil)
  c:observe(s,rows(true,false),PAIR,'COMMITTED',1002,{b={suspect=true,failed=false}});t.eq(c:dense(1002).profile,'b')
  local d=booster();d:observe(s,rows(false),PAIR,'OBSERVING',1000);t.eq(d:dense(1000),nil,'no models: the previous rules')
end)

t.test('committed return: the HMM modes want the primary healthy (the reserve is)',function()
  local T=require('transaction')
  local function series(start,kinds,profile_id,gen,iface,tunnel)
    local out={}
    for i=1,#kinds do
      local k=kinds:sub(i,i)
      out[#out+1]=canon.object({id=profile_id,time=canon.float(start+10*(i-1)),code=k=='O' and NULL or (k=='D' and 'DNS-001' or 'VPN-003'),
        dns_ok=k~='D',https_success=k=='H' and 0 or 3,interface=iface,vendor_tunnel_id=tunnel,vendor_generation=gen})
    end
    return out
  end
  local reserve=canon.object({id='openvpn:1_1',protocol='openvpn',interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=string.rep('02',16),vendor_changed_at=1000})
  local function decide(model,primary,reserve_kinds,now)
    local list=canon.array({})
    for _,s in ipairs(series(now-10*#primary,primary,PROFILE.id,PROFILE.vendor_generation,PROFILE.interface,PROFILE.vendor_tunnel_id)) do list[#list+1]=s end
    for _,s in ipairs(series(now-10*#reserve_kinds,reserve_kinds,reserve.id,reserve.vendor_generation,reserve.interface,reserve.vendor_tunnel_id)) do list[#list+1]=s end
    local env={deps={resolve_pair=function() return {coordination={state='READY'},target=reserve,source=PROFILE} end,testing_profile=function() return false end},
      backend={recovery_ready=function() return true end,health=function() return false end}}
    local value=canon.object({source=PROFILE.id,target=reserve.id,confirmed=now-600,started=now-600})
    return T.committed_recovery_decision(env,value,canon.object({failure_model=model}),list,now,canon.object({}),30)
  end
  local lossy='ODOODOOODOODOOOD'..string.rep('O',8)
  t.eq(decide('consecutive',lossy,'OOOOOO',1500).action,'RESTORE-PRIMARY')
  t.eq(decide('hmm',lossy,'OOOOOO',1500).action,'OBSERVE')
  t.eq(decide('hmm',string.rep('H',10)..string.rep('O',6),'OOOOOO',1500).action,'RESTORE-PRIMARY')
  t.eq(decide('hmm',lossy..string.rep('O',24),'OOOOOO',1500).action,'RESTORE-PRIMARY')
  t.eq(decide('hmm',lossy,'OOOHHH',1500).reason,'RESERVE-FAILED-PRIMARY-VERIFIED')
  t.eq(decide('hmm',lossy,'OOOOHH',1500).action,'OBSERVE')
end)

t.run()
