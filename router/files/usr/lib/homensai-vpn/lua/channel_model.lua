-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- channel_model.lua: channel_model.py for the Lua supervisor and monitor - the channel-failure detector of Auto
-- (owner decision 03.11.2026; option failure_model 'hmm' (default) | 'hmm-fast' | 'consecutive').
-- Same constants, same arithmetic in the same order (doubles, math.exp): tests/hmm_detector_cases.json (generated
-- from the Python module by tests/gen_hmm_detector_cases.py) gives the same probabilities within 1e-9 and the same
-- decisions in both runtimes. Formulas and the reasons: channel_model.py and
-- docs/architecture/HMM-DETECTOR-2026-11-03.ru.md.
-- Hot path (M.step): six locals, updated in place in the caller's array; no table is created per sample.
local canon=require('canon')

local M={}
local NULL=canon.null
local exp,mmax,mmin=math.exp,math.max,math.min

M.MODELS={hmm=true,['hmm-fast']=true,consecutive=true}
M.DEFAULT='hmm'
M.STATES={'G','L','M','B','X','N'}
M.HARD={['VPN-003']=true,['VPN-001']=true,['VPN-MTU']=true}
-- EMIS[state] = {normal O, D, H, dense O, D, H} (study section 2.3; channel_model.EMIS)
M.EMIS={{0.994,0.004,0.002,0.994,0.004,0.002},
  {0.8717,0.1233,0.0050,0.8647,0.1209,0.0144},
  {0.2520,0.2087,0.5393,0.1042,0.0784,0.8174},
  {0.010,0.010,0.980,0.010,0.010,0.980},
  {0.010,0.010,0.980,0.010,0.010,0.980},
  {0.020,0.970,0.010,0.020,0.970,0.010}}
M.LAM={1/7200.0,1/21600.0,4/21600.0,1/21600.0,1/604800.0}   -- L M B X N, per second
M.DUR={1800.0,1800.0,4.0,900.0,1800.0}                        -- L M B X N, seconds (B: the preset's dur_b)
M.PRESETS={hmm={theta=0.8,dur_b=4.0},['hmm-fast']={theta=0.7,dur_b=3.0}}
M.COST=20.0;M.SUSPECT=0.2;M.HEALTHY=0.9;M.CLEAN=300;M.FLOOR=1e-9  -- HEALTHY 0.95 -> 0.9: owner 03.11.2026
M.WINDOW=600.0;M.FIRST_DT=10.0;M.DT_MAX=600.0;M.DENSE_GAP=7.0
M.HTTP_NORMAL=6.0;M.HTTP_DENSE=3.0;M.DNS_WAIT=3.0;M.PUBLISHED=2.5
-- Fast end of the master slider (channel_model.py, docs/architecture/FAST-SWITCH-2026-11-04.ru.md): M.leave_rule
M.OR_FAILURES={2,10};M.TURBO_BEATS={3,8};M.WAKE_NAME='pair-wake.json';M.BEAT_FRESH=2.5

local function num(v) return canon.number(v) end
local function finite(x) return type(x)=='number' and x==x and x~=math.huge and x~=-math.huge end
local function none(v) return v==nil or v==NULL end

function M.name(settings)
  local v=type(settings)=='table' and settings.failure_model or nil
  if type(v)=='string' and M.MODELS[v] then return v end
  return M.DEFAULT
end

-- Numeric options (2.1.0-alpha9, master slider / network advisor; channel_model.custom / numeric / resolve):
-- option hmm_theta, hmm_dur_b, return_pg; absent = the preset of failure_model, i.e. exactly alpha8.
M.NUMERIC={hmm_theta={0.5,0.99},hmm_dur_b={1.0,15.0},return_pg={0.5,0.99}}
local CUSTOM,CUSTOM_SIZE={},0
function M.custom(theta,dur_b,model,healthy)
  model=model or 'hmm';if healthy==nil then healthy=M.HEALTHY end
  local key=string.format('%s|%.17g|%.17g|%.17g',model,theta,dur_b,healthy)
  if CUSTOM[key] then return CUSTOM[key] end
  local L,D=M.LAM,M.DUR
  local dur={D[1],D[2],dur_b,D[4],D[5]}
  local total=L[1]+L[2]+L[3]+L[4]+L[5]
  local ratio,weight={},{}
  for i=1,5 do ratio[i]=L[i]/total;weight[i]=exp(-M.COST/dur[i]) end
  local preset=M.PRESETS[model]
  local plain=preset~=nil and preset.theta==theta and preset.dur_b==dur_b and healthy==M.HEALTHY
  local p={model=model,theta=theta,dur=dur,lam=L,total=total,ratio=ratio,weight=weight,healthy=healthy,key=plain and model or key}
  CUSTOM_SIZE=CUSTOM_SIZE+1
  if CUSTOM_SIZE>64 then CUSTOM={};CUSTOM_SIZE=1 end
  CUSTOM[key]=p
  return p
end
function M.params(model)
  local preset=type(model)=='string' and M.PRESETS[model] or nil
  if not preset then return nil end
  return M.custom(preset.theta,preset.dur_b,model)
end
-- The owner's numeric option within its range, or nil (absent, malformed or out of range = the preset).
function M.numeric(settings,key)
  local v=type(settings)=='table' and num(settings[key]) or nil
  if not finite(v) then return nil end
  local range=M.NUMERIC[key]
  if v<range[1] or v>range[2] then return nil end
  return v
end
-- The constants Auto decides with: the preset of failure_model overridden by hmm_theta / hmm_dur_b / return_pg.
function M.resolve(settings)
  local model=M.name(settings)
  local preset=M.PRESETS[model]
  if not preset then return nil end
  local theta,dur_b,healthy=M.numeric(settings,'hmm_theta'),M.numeric(settings,'hmm_dur_b'),M.numeric(settings,'return_pg')
  if theta==nil then theta=preset.theta end
  if dur_b==nil then dur_b=preset.dur_b end
  return M.custom(theta,dur_b,model,healthy)
end

-- 0 O / 1 D / 2 H, or nil when the sample is not an observation of the channel's health
function M.observation(sample)
  local code=sample.code
  if none(code) then
    local hs=sample.https_success
    if sample.dns_ok==true and type(hs)=='number' and hs%1==0 and hs>=2 then return 0 end
    return nil
  end
  if code=='DNS-001' then return 1 end
  if M.HARD[code] then return 2 end
  return nil
end

-- One predict + update of pi (6 probabilities G L M B X N) in place.
function M.step(pi,dt,obs,dense,p)
  local g=exp(-p.total*dt)
  local gone=1-g
  local dur,ratio=p.dur,p.ratio
  local p0=pi[1]
  local o0=p0*g
  local e
  e=exp(-dt/dur[1]);o0=o0+pi[2]*(1-e);local o1=pi[2]*e+p0*ratio[1]*gone
  e=exp(-dt/dur[2]);o0=o0+pi[3]*(1-e);local o2=pi[3]*e+p0*ratio[2]*gone
  e=exp(-dt/dur[3]);o0=o0+pi[4]*(1-e);local o3=pi[4]*e+p0*ratio[3]*gone
  e=exp(-dt/dur[4]);o0=o0+pi[5]*(1-e);local o4=pi[5]*e+p0*ratio[4]*gone
  e=exp(-dt/dur[5]);o0=o0+pi[6]*(1-e);local o5=pi[6]*e+p0*ratio[5]*gone
  local k=obs+(dense and 4 or 1)
  local E=M.EMIS
  o0=o0*E[1][k];o1=o1*E[2][k];o2=o2*E[3][k];o3=o3*E[4][k];o4=o4*E[5][k];o5=o5*E[6][k]
  local z=o0+o1+o2+o3+o4+o5
  if not (z>0) then z=1.0 end
  local F=M.FLOOR
  o0=mmax(F,o0/z);o1=mmax(F,o1/z);o2=mmax(F,o2/z);o3=mmax(F,o3/z);o4=mmax(F,o4/z);o5=mmax(F,o5/z)
  local w=o0+o1+o2+o3+o4+o5
  pi[1]=o0/w;pi[2]=o1/w;pi[3]=o2/w;pi[4]=o3/w;pi[5]=o4/w;pi[6]=o5/w
  return pi
end

function M.persist(pi,p)
  local w=p.weight
  return pi[3]*w[2]+pi[4]*w[3]+pi[5]*w[4]+pi[6]*w[5]
end
function M.remaining(pi,p)
  local d=p.dur
  return pi[3]*d[2]+pi[4]*d[3]+pi[5]*d[4]+pi[6]*d[5]
end

-- replay(points, p) -> pi, newest observation time, observations (points ascending, unique stamps)
-- Seconds after the sample's start when its result is known (channel_model.delay).
function M.delay(code,dense)
  if code=='VPN-003' then return dense and M.HTTP_DENSE or M.HTTP_NORMAL end
  if code=='DNS-001' then return M.DNS_WAIT end
  return M.PUBLISHED
end
-- The model's clock is when each result became known (sample time + delay), as in the calibrated study.
function M.replay(points,p)
  local pi={1.0,0.0,0.0,0.0,0.0,0.0}
  local last,seen,previous,count=nil,nil,nil,0
  local step,observation,delay,gap,first,cap=M.step,M.observation,M.delay,M.DENSE_GAP,M.FIRST_DT,M.DT_MAX
  for i=1,#points do
    local point=points[i]
    local t=num(point.time)
    local obs=observation(point)
    if obs~=nil then
      local dense=point.dense
      if type(dense)~='boolean' then dense=previous~=nil and t-previous<=gap end
      local known=t+delay(point.code,dense)
      local dt=first
      if seen~=nil then dt=mmin(mmax(known-seen,0.0),cap) end
      step(pi,dt,obs,dense,p)
      last=t;seen=known;count=count+1
    end
    previous=t
  end
  return pi,last,count
end

local function same_health(a,b)
  local ca,cb=a.code,b.code;if ca==nil then ca=NULL end;if cb==nil then cb=NULL end
  local da,db=a.dns_ok,b.dns_ok;if da==nil then da=NULL end;if db==nil then db=NULL end
  local ha,hb=a.https_success,b.https_success
  if num(ha)~=nil and num(hb)~=nil then ha,hb=num(ha),num(hb) end
  if ha==nil then ha=NULL end;if hb==nil then hb=NULL end
  return ca==cb and da==db and ha==hb
end
M.same_health=same_health
-- The channel's samples of the last WINDOW s, ascending, one per stamp; nil when two of one stamp disagree.
function M.window(samples,identifier,now)
  now=num(now)
  if type(samples)~='table' or not finite(now) then return nil end
  local seen,points={},{}
  for _,point in ipairs(samples) do
    if type(point)=='table' and point~=NULL and point.id==identifier then
      local t=num(point.time)
      if finite(t) and 0<=now-t and now-t<=M.WINDOW then
        local first=seen[t]
        if first then
          if not same_health(first,point) then return nil end
        else seen[t]=point;points[#points+1]=point end
      end
    end
  end
  table.sort(points,function(a,b) return num(a.time)<num(b.time) end)
  return points
end

local MEMO,MEMO_SIZE={},0
-- evaluate(samples, identifier, now, max_age, model, profile, env) -> view | nil (see channel_model.evaluate)
function M.evaluate(samples,identifier,now,max_age,model,profile,env)
  local p=type(model)=='table' and model or M.params(model)   -- a preset name or M.resolve(settings)
  max_age=num(max_age)
  if p==nil or not finite(max_age) or max_age<=0 then return nil end
  model=p.model
  if profile~=nil then
    samples=require('pair').scoped_samples(env,samples,profile)
    -- failure_diagnosis.scoped_samples: two samples of one stamp that disagree leave no evidence at all
    local seen={}
    for _,point in ipairs(samples) do
      local t=num(point.time)
      if seen[t] and not M.same_health(seen[t],point) then samples={};break end
      seen[t]=point
    end
  end
  local points=M.window(samples,identifier,now)
  if points==nil then return nil end
  now=num(now)
  -- Auto ticks every 2 s, samples arrive every 4-10 s: the replay of an unchanged window is remembered
  -- (published samples never change; the key changes with every new or expired sample).
  local pi,last,count
  local times,shape=0,0
  for i=1,#points do
    local point=points[i];local obs=M.observation(point)
    times=times+num(point.time);shape=shape+i*(4+(obs or 3)+(point.dense==true and 8 or 0)+16*M.delay(point.code,true))
  end
  local key=string.format('%s|%s|%d|%.17g|%.17g',p.key,tostring(identifier),#points,times,shape)
  local hit=MEMO[key]
  if hit then pi,last,count={hit[1],hit[2],hit[3],hit[4],hit[5],hit[6]},hit.last,hit.count
  else
    pi,last,count=M.replay(points,p)
    MEMO_SIZE=MEMO_SIZE+1
    if MEMO_SIZE>16 then MEMO={};MEMO_SIZE=1 end
    MEMO[key]={pi[1],pi[2],pi[3],pi[4],pi[5],pi[6],last=last,count=count}
  end
  -- like streak(): a newest sample that is no observation (CHECK-001, ROUTE-001, ...) leaves no decision
  local fresh=last~=nil and now-last<=max_age and M.observation(points[#points])~=nil
  local chance=M.persist(pi,p)
  local bad=1-pi[1]-pi[2]
  return {model=model,pi=pi,time=last,observations=count,persist=chance,p_bad=bad,p_healthy=pi[1],
    remaining=M.remaining(pi,p),failed=fresh and chance>=p.theta,suspect=fresh and bad>=M.SUSPECT,healthy=fresh and pi[1]>=p.healthy}
end

-- Auto's "the channel carrying traffic failed" (pair.streak for 'consecutive').
function M.channel_failed(samples,identifier,count,now,max_age,settings,profile,env)
  local model=M.name(settings)
  if model=='consecutive' then return require('pair').streak(samples,identifier,count,now,max_age,false,profile,env) end
  local view=M.evaluate(samples,identifier,now,max_age,M.resolve(settings),profile,env)
  return view~=nil and view.failed==true
end

local function whole(v)
  if type(v)=='string' and string.find(v,'^%d+$') then v=tonumber(v) end
  if canon.is_float(v) then return nil end
  if type(v)=='number' and v%1==0 then return v end
  return nil
end
-- channel_model.or_failures: N of "the model OR N failed samples in a row", or nil
function M.or_failures(settings)
  local v=type(settings)=='table' and whole(settings.hmm_or_failures) or nil
  if not v or v<M.OR_FAILURES[1] or v>M.OR_FAILURES[2] or M.name(settings)=='consecutive' then return nil end
  return v
end
-- channel_model.turbo_on: the expert opt-in (option slider_turbo, default off)
function M.turbo_on(settings)
  return type(settings)=='table' and (settings.slider_turbo==true or settings.slider_turbo=='1') and M.name(settings)~='consecutive'
end
-- channel_model.heartbeat_k: k lost heartbeats in a row that leave the primary, or nil
function M.heartbeat_k(settings)
  if not M.turbo_on(settings) then return nil end
  local v=whole(settings.turbo_beats)
  if not v or v<M.TURBO_BEATS[1] or v>M.TURBO_BEATS[2] then return nil end
  return v
end
-- channel_model.heartbeat_failed: both channels silent is a WAN outage; an old or foreign row proves nothing
function M.heartbeat_failed(beat,source,target,k,now)
  if k==nil or type(beat)~='table' or beat==NULL or beat.reason~='heartbeat' then return false end
  local t=num(beat.time)
  if not finite(t) or now-t<0 or now-t>M.BEAT_FRESH then return false end
  local lost=beat.lost
  return beat.id==source and beat.target==target and beat.target_ok==true and type(lost)=='number' and lost%1==0 and lost>=k
end
-- channel_model.leave_rule: why Auto leaves the primary now: 'model', 'streak', 'heartbeat', or nil
function M.leave_rule(samples,identifier,count,now,max_age,settings,profile,env,target,beat)
  if M.channel_failed(samples,identifier,count,now,max_age,settings,profile,env) then
    return M.name(settings)=='consecutive' and 'streak' or 'model'
  end
  local extra=M.or_failures(settings)
  if extra~=nil and require('pair').streak(samples,identifier,extra,now,max_age,false,profile,env) then return 'streak' end
  if M.heartbeat_failed(beat,identifier,target,M.heartbeat_k(settings),now) then
    local view=M.evaluate(samples,identifier,now,max_age,M.resolve(settings),profile,env)
    if view~=nil and view.time~=nil and now-view.time<=max_age then return 'heartbeat' end
  end
  return nil
end

-- The extra gate of a planned return from a healthy reserve (channel_model.return_ready).
function M.return_ready(samples,identifier,count,now,max_age,settings,profile,env)
  local model=M.name(settings)
  if model=='consecutive' then return true end
  local view=M.evaluate(samples,identifier,now,max_age,M.resolve(settings),profile,env)
  if view~=nil and view.healthy then return true end
  local pair=require('pair')
  local points=samples
  if profile~=nil then points=pair.scoped_samples(env,samples,profile) end
  if type(points)~='table' then return false end
  local list={}
  for _,point in ipairs(points) do if type(point)=='table' and point~=NULL then list[#list+1]=point end end
  return pair.stable_success(list,identifier,count,M.CLEAN,num(now),num(max_age))==true
end

local function round(x,scale) return math.floor(x*scale+0.5)/scale end
M.round=round
-- The status row field failure_model (channel_model.public)
function M.public(view)
  if view==nil then return nil end
  return canon.object({model=view.model,p_bad=canon.float(round(view.p_bad,10000)),p_healthy=canon.float(round(view.p_healthy,10000)),
    persist=canon.float(round(view.persist,10000)),remaining_s=canon.float(round(view.remaining,10)),failed=view.failed,suspect=view.suspect,
    time=view.time==nil and NULL or canon.float(view.time),observations=view.observations})
end

-- The monitor's public view of one measured channel (its current binding only), or nil ('consecutive').
local IDENTITY={'interface','vendor_tunnel_id','vendor_generation'}
local function nv(v) if v==nil then return NULL end;return v end
function M.row_view(samples,row,now,max_age,settings)
  local model=M.name(settings)
  if model=='consecutive' or type(row)~='table' or type(samples)~='table' then return nil end
  local identifier=row.id
  local points={}
  for _,s in ipairs(samples) do
    if type(s)=='table' and s~=NULL and s.id==identifier then
      local same=true
      for _,k in ipairs(IDENTITY) do if nv(s[k])~=nv(row[k]) then same=false;break end end
      if same then points[#points+1]=s end
    end
  end
  return M.public(M.evaluate(points,identifier,now,max_age,M.resolve(settings)))
end

return M
