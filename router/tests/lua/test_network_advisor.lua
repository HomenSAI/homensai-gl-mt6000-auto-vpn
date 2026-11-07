-- Network journal and advisor (lua/netjournal.lua, lua/advisor.lua; 2.1.0-alpha9). Python twin:
-- tests/test_network_advisor.py over the same tests/advisor_cases.json (generated from netjournal.py / advisor.py by
-- tests/gen_advisor_cases.py): the same records (exact integers), numbers within the file's tolerance, the same
-- decisions and the same texts. The synthetic days (tests/advisor_sim.py) are rebuilt here by a port of the generator.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local A=require('advisor')
local J=require('netjournal')
local CM=require('channel_model')
local NULL=canon.null
local N=canon.number

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.plain(canon.decode(read_file(t.here..'/../advisor_cases.json')))
local TOL=CASES.tolerance
local CURVE=A.load_curve(t.here..'/../../files/usr/lib/homensai-vpn/slider_curve.json')
local function none(v) return v==nil or v==NULL end

local function near(a,b,msg)
  if none(a) and none(b) then return end
  if type(a)=='boolean' or type(b)=='boolean' or type(a)=='string' or type(b)=='string' then
    if a~=b then error((msg or 'not equal')..': '..tostring(a)..' vs '..tostring(b),2) end;return
  end
  if type(b)=='table' then
    if type(a)~='table' then error((msg or 'not a table')..': '..tostring(a),2) end
    for k,v in pairs(b) do near(a[k],v,(msg or '')..'.'..tostring(k)) end
    for k,v in pairs(a) do if b[k]==nil and not none(v) then error((msg or '')..': extra key '..tostring(k),2) end end
    return
  end
  if type(a)~='number' or type(b)~='number' or math.abs(a-b)>TOL then error((msg or 'not near')..': '..tostring(a)..' vs '..tostring(b),2) end
end

-- tests/gen_advisor_cases.fingerprint
local function fingerprint(day)
  local out=canon.object({d=day.d,sw=day.sw,rt=day.rt,us=day.us,ch=canon.object()})
  for identifier,rec in pairs(day.ch) do
    local lp_sum,lp_w,rs_sum,rn_sum,rs_w=0,0,0,0,0
    for i,v in ipairs(rec.lp) do lp_sum=lp_sum+v;lp_w=lp_w+(i-1)*v end
    for i=1,#rec.rs do rs_sum=rs_sum+rec.rs[i];rn_sum=rn_sum+rec.rn[i];rs_w=rs_w+(i-1)*rec.rs[i] end
    local o=canon.array();for i,v in ipairs(rec.o) do o[i]=v end
    local oh=canon.array();for i,v in ipairs(rec.oh) do oh[i]=v end
    out.ch[identifier]=canon.object({r=rec.r,n=rec.n,f=rec.f,lp_sum=lp_sum,lp_w=lp_w,rs_sum=rs_sum,rn_sum=rn_sum,rs_w=rs_w,oh=oh,o=o,ox=rec.ox})
  end
  return out
end
local function same_fp(day,want,msg)
  local a=canon.encode(fingerprint(day))
  local b=canon.encode(canon.object(want))
  if a~=b then error((msg or 'record differs')..':\n lua '..a..'\n  py '..b,2) end
end

-- tests/advisor_sim.py (port: advisor_sim.lua)
local SIM=require('advisor_sim').new(CASES)
local PRIMARY=SIM.primary
local failing,sample,scenario_days,build=SIM.failing,SIM.sample,SIM.scenario_days,SIM.build
local BUILT={}
local function built(name,days,offset)
  local key=name..'|'..days..'|'..offset
  if not BUILT[key] then BUILT[key]=build(scenario_days(name,days),offset) end
  return BUILT[key]
end

------------------------------------------------------------------------------------------------------
t.test('journal sequences: the same records, open outages and texts',function()
  for _,case in ipairs(CASES.journal) do
    local journal=J.new()
    for _,p in ipairs(case.passes) do J.observe(journal,p[2],p[4],p[3],p[1],case.offset) end
    t.eq(#journal.days,#case.days,case.name)
    for i,d in ipairs(journal.days) do same_fp(d,case.days[i],case.name) end
    same_fp(journal.cur,case.cur,case.name)
    t.eq(canon.encode(J.open_outages(journal)),canon.encode(canon.array(case.open)),case.name)
    t.eq(journal.st.route==NULL and NULL or journal.st.route,none(case.route) and NULL or case.route,case.name)
    t.eq(J.flash_due(journal,case.passes[#case.passes][1],case.offset),case.flash_due,case.name)
    t.eq(J.days_text(journal),case.text,case.name..' days text')
  end
end)

t.test('synthetic weeks: the same day records as Python, ~3 KB a day',function()
  for label,b in pairs(CASES.builds) do
    local name=b.name or label
    local journal=built(name,b.days,b.offset)
    t.eq(#journal.days,#b.fingerprints,label)
    for i,d in ipairs(journal.days) do
      same_fp(d,b.fingerprints[i],label..' day '..i)
      t.eq(#canon.encode(d),b.sizes[i],label..' size')
    end
  end
end)

t.test('the journal survives its own files (RAM, flash after a reboot) and refuses damage',function()
  local journal=built('flappy',7,0)
  local again=J.load(J.days_text(journal),J.today_text(journal),nil)
  t.eq(J.days_text(again),J.days_text(journal))
  t.eq(canon.encode(again.cur),canon.encode(journal.cur))
  local boot=J.load(nil,nil,J.flash_text(journal,CASES.base+7*86400+100,0))
  t.eq(J.days_text(boot),J.days_text(journal));t.eq(boot.flash_day,J.day_index(CASES.base+7*86400+100,0));t.eq(boot.cur,nil)
  local damaged=J.load('{"v":1,"days":[{"d":3}]}','{"v":2}','not json')
  t.eq(#damaged.days,0);t.eq(damaged.cur,nil)
end)

t.test('flash: at most one write a day, RAM today file at most once a minute',function()
  local files,flash,ram={},0,0
  local io_={read=function(p) return files[p] end,write_ram=function(p,s) files[p]=s;ram=ram+1 end,
    write_flash=function(p,s) files[p]=s;flash=flash+1 end}
  local writer=J.writer(io_,'/run','/etc')
  local events=CASES.scenarios.long
  local day_flash={}
  for day=0,2 do
    for k=0,8639 do
      local now=CASES.base+day*86400+k*10+8
      local before=flash
      writer:pass({sample(PRIMARY,now-8,failing(events,'P',k*10),false,40)},CASES.pair,'source',now,0,now)
      if flash>before then local d=J.day_index(now,0);day_flash[d]=(day_flash[d] or 0)+1 end
      if day==1 and k==4000 then writer=J.writer(io_,'/run','/etc') end      -- a monitor restart (RAM files kept)
    end
  end
  for _,n in pairs(day_flash) do t.eq(n,1) end
  t.eq(flash,2)
  t.truthy(ram<=3*1440+10,'RAM writes '..ram)
end)

t.test('curve interpolation, replay, behaviour and safety equal Python',function()
  for _,c in ipairs(CASES.interpolate) do
    local got=A.interpolate(CURVE,c.t)
    for _,k in ipairs(CURVE.params) do near(got[k],c.expect[k],'t='..c.t..' '..k) end
    near(got.t,c.expect.t);near(got.m,c.expect.m,'m');near(got.g,c.expect.g,'g')
  end
  for _,c in ipairs(CASES.behaviour) do
    local known=A.knowns(c.theta,c.dur_b)
    for i=1,known.n do near(known[i] or NULL,c.knowns[i],'known '..i) end
    local ride,leave=A.behaviour(c.theta,c.dur_b)
    t.eq(ride,c.ride);near(leave or NULL,c.leave,'leave')
  end
  for _,c in ipairs(CASES.outcome) do
    local a,b,s=A.outcome(c.d,A.knowns(c.theta,c.dur_b))
    near({a,b,s},c.expect,'outcome d='..c.d)
  end
  for _,c in ipairs(CASES.safety) do
    local p={};for k,v in pairs(c.params) do if v~=NULL then p[k]=v end end
    t.eq(canon.encode(canon.array(A.safety(p))),canon.encode(canon.array(c.codes)))
  end
end)

t.test('current settings, keys, modes, windows',function()
  for _,c in ipairs(CASES.current) do
    local got=A.current(c.settings,CURVE)
    for k,v in pairs(c.expect) do near(got[k],v,'current '..k) end
    t.eq(A.settings_key(c.settings),c.key);t.eq(A.mode(c.settings),c.mode);t.eq(A.window(c.settings),c.window)
  end
  -- alpha8 defaults: no numeric option = exactly the preset (same object key -> the same memo as before)
  t.eq(CM.resolve(canon.object({failure_model='hmm'})).key,'hmm')
  t.eq(CM.resolve(canon.object({failure_model='hmm-fast'})).key,'hmm-fast')
  t.eq(CM.resolve(canon.object({failure_model='consecutive',hmm_theta=0.6})),nil)
  local p=CM.resolve(canon.object({failure_model='hmm',hmm_theta=0.6,hmm_dur_b=canon.float(8.0),return_pg=0.95}))
  t.eq(p.theta,0.6);t.eq(p.dur[3],8.0);t.eq(p.healthy,0.95)
  p=CM.resolve(canon.object({failure_model='hmm',hmm_theta=0.2,hmm_dur_b='4',return_pg=true}))
  t.eq(p.key,'hmm')
  -- return_pg is the "healthy" threshold of the planned return (tests/test_network_advisor.py, the same samples)
  local rows=canon.array()
  local function add(tt,fail)
    rows[#rows+1]=canon.object({id='p',time=tt,code=fail and 'VPN-003' or NULL,dns_ok=true,https_success=fail and 0 or 3})
  end
  for tt=1000,1190,10 do add(tt,false) end;add(1200,true);for tt=1210,1250,10 do add(tt,false) end
  local base=CM.evaluate(rows,'p',1255,30,CM.resolve(canon.object({failure_model='hmm'})))
  local low=CM.evaluate(rows,'p',1255,30,CM.resolve(canon.object({failure_model='hmm',return_pg=0.5})))
  local high=CM.evaluate(rows,'p',1255,30,CM.resolve(canon.object({failure_model='hmm',return_pg=0.99})))
  t.eq(low.healthy,true);t.eq(high.healthy,false);t.eq(base.healthy,base.pi[1]>=0.9)
end)

t.test('unimodal, golden section, plural',function()
  for _,c in ipairs(CASES.unimodal) do t.eq(A.unimodal(c[1]),c[2]) end
  for _,c in ipairs(CASES.golden) do
    local f
    if c.kind=='quad' then f=function(x) return (x-c.m)^2 end else f=function(x) return math.floor(math.abs(x-c.m)*20)/20 end end
    local x,n=A.golden(f)
    near(x,c.expect[1],'golden '..c.kind..' '..c.m);t.eq(n,c.expect[2])
  end
  for _,c in ipairs(CASES.plural) do t.eq(A.plural_ru(c[1],'день','дня','дней'),c[2]) end
end)

t.test('events of the window equal Python',function()
  for _,c in ipairs(CASES.events) do
    local ev=A.events(built(c.scenario,7,0).days,c.today,c.window)
    local outs={};for i,o in ipairs(ev.outages) do outs[i]={o[1],o[2]} end
    near({n=ev.n,days=ev.days,weight_days=ev.weight_days,groups=ev.groups,counts=ev.counts,outages=outs,durations=ev.durations},c.expect,c.scenario..' w'..c.window)
  end
end)

t.test('recommendations: the same state, position, effect and texts',function()
  for _,c in ipairs(CASES.recommend) do
    local days=built(c.scenario,7,0).days
    if c.tail~=nil then local list={};for i=#days-c.tail+1,#days do if i>=1 then list[#list+1]=days[i] end end;days=list end
    local r=A.recommend(CURVE,days,c.settings,c.now,c.offset)
    local label=c.scenario..' '..tostring(c.settings.failure_model)..' '..tostring(c.settings.advisor_mode)
    for k,v in pairs(c.expect) do near(r[k],v,label..' '..k) end
  end
end)

t.test('summary of the journal equals Python',function()
  for _,c in ipairs(CASES.summary) do
    local s=canon.plain(canon.decode(canon.encode(A.summary(built(c.scenario,7,0).days,nil,c.today,c.window))))
    near(s,c.expect,c.scenario)
  end
end)

t.test('auto mode steps and the nightly schedule equal Python',function()
  for _,c in ipairs(CASES.auto_step) do
    local got=A.auto_step(CURVE,c.result,c.settings,c.changes,c.calm,c.now)
    near({apply=got.apply,t=got.t or NULL,code=got.code or NULL},c.expect,c.name)
  end
  for i,c in ipairs(CASES.job_due) do
    t.eq(A.job_due(c.result~=NULL and c.result or nil,c.key,c.now,c.offset,c.last~=NULL and c.last or nil),c.expect,'job_due '..i)
  end
end)

t.test('the monitor part: one journal writer, the job request, the status field',function()
  local files,spawned={},0
  local io_={read=function(p) return files[p] end,write_ram=function(p,s) files[p]=s end,write_flash=function(p,s) files[p]=s end,
    spawn=function() spawned=spawned+1;return true end}
  local start=CASES.base+100
  local part=A.monitor_part(io_,'/run','/etc',start,CURVE)
  local settings=canon.object({failure_model='hmm',advisor_mode='auto',telegram_destination='secret'})
  local status
  for k=0,119 do
    local now=start+k*10
    status=part:pass({sample(PRIMARY,now-8,k==70,false,40)},CASES.pair,'source','OBSERVING',settings,now,0,now)
  end
  t.eq(spawned,1)
  local request=canon.decode(files['/run/advisor-request.json'])
  t.eq(request.settings.advisor_mode,'auto');t.eq(request.settings.telegram_destination,nil)
  t.eq(request.calm.native,'OBSERVING');t.eq(#request.calm.open,0)
  t.eq(status.mode,'auto');t.eq(status.window_days,7);t.eq(status.recommendation,NULL)
  t.eq(status.current.label,'preset');t.eq(N(status.current.nearest_t),0.6)
  t.eq(status.journal.tunnels[PRIMARY].outages,1)
  local text=canon.encode(status)
  t.truthy(#text<4000,'status field '..#text..' bytes')
end)

t.test('the nightly job (lua advisor.lua run) on real files',function()
  local dir=os.getenv('HOMENSAI_TEST_RUNTIME') or os.getenv('TMPDIR') or '/tmp'
  dir=dir..'/advisor-test-'..tostring(os.time())..'-'..tostring(math.random(1000000))
  assert(os.execute('mkdir -p '..dir..'/run '..dir..'/etc')==0)
  local journal=built('blips',7,0)
  local function write(path,text) local f=assert(io.open(path,'wb'));f:write(text);f:close() end
  write(dir..'/run/'..J.DAYS_NAME,J.days_text(journal))
  local now=CASES.base+7*86400+3.5*3600
  write(dir..'/run/advisor-request.json',canon.encode(canon.object({settings=canon.object({failure_model='hmm',advisor_mode='auto'}),
    now=canon.float(now),offset=0,key='k',calm=canon.object({open=canon.array(),route='source',native='OBSERVING'})})))
  local applied={}
  local saved=A.CURVE_PATH;A.CURVE_PATH=t.here..'/../../files/usr/lib/homensai-vpn/slider_curve.json'
  local r=A.run(dir..'/run',dir..'/etc',function(x) applied[#applied+1]=x;return canon.object({saved=true}) end,write)
  A.CURVE_PATH=saved
  t.eq(r.state,'shift');t.eq(r.t,0.4);t.eq(#applied,1);t.eq(applied[1],0.5)
  local file=canon.decode(read_file(dir..'/run/advisor.json'))
  t.eq(file.state,'shift');t.eq(file.applied.saved,true);t.eq(N(file.auto.t),0.5)
  os.execute('rm -rf '..dir)
end)

t.run()
