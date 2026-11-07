-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- advisor.lua: advisor.py for the Lua monitor - the network advisor of the master slider (2.1.0-alpha9, owner design
-- 04.11.2026). Same constants, same arithmetic in the same order, the same texts (tests/advisor_cases.json, generated
-- from the Python module by tests/gen_advisor_cases.py). The method and the reasons: advisor.py and
-- docs/architecture/NETWORK-ADVISOR-2026-11-04.ru.md.
-- `lua advisor.lua run` is the nightly job the monitor starts under nice -n 19.
if arg and arg[0] and string.find(arg[0],'advisor%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local canon=require('canon')
local CM=require('channel_model')
local J=require('netjournal')

local M={}
local NULL=canon.null
local floor,mmin,mmax,abs=math.floor,math.min,math.max,math.abs

M.CURVE_PATH='/usr/lib/homensai-vpn/slider_curve.json'
M.VERSION=1
M.MODES={auto=true,advice=true,manual=true}
M.DEFAULT_MODE='advice'
M.WINDOWS={[1]=true,[7]=true,[30]=true}
M.DEFAULT_WINDOW=7
M.MIN_EVENTS=5;M.MIN_SAVING=0.05;M.AUTO_STEP=0.1;M.AUTO_SPACING=20*3600
M.RUN_AT=3*3600+30*60;M.RUN_SPACING=600;M.GOLDEN_TOL=0.02
M.EXEC=2.0;M.BLIP=1.5;M.NORMAL=10.0;M.DENSE={4.0,5.0,6.0};M.PHASES={0.0,2.0,4.0,6.0,8.0};M.HISTORY=60.0;M.HORIZON=300.0
M.LOSSY=0.05;M.HEAVY=0.30;M.LOSSY_MIN_SAMPLES=5;M.LOSSY_MIN_SHORTS=2
M.FLAP_GAP=180;M.FLAP_MIN=3;M.NOISY_SHORT=15;M.NOISY_MIN=4;M.SHORT_MAX=15;M.MEDIUM_MAX=45;M.RESERVE_MIN=20
M.GROUPS={'short','medium','long','loss_light','loss_heavy','flap','reserve_fail','noisy'}
M.TABLE_GROUPS={loss_light=true,loss_heavy=true,flap=true,reserve_fail=true,noisy=true}
M.TABLE_ORDER={'loss_light','loss_heavy','flap','reserve_fail','noisy'}
M.MIN_T=-0.7;M.FAST_MIN_T=-0.2
M.SAFE_ORDER={'theta','dur_b','pg','primary_stable','rescue_stable'}
M.SAFE={theta={0.5,0.99},dur_b={1.0,15.0},pg={0.5,0.99},primary_stable={30,600},rescue_stable={0,60}}
M.TRANSITION={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true}
M.RESULT_NAME='advisor.json';M.REQUEST_NAME='advisor-request.json';M.CHANGES_NAME='advisor-changes.json'

local function finite(x) return type(x)=='number' and x==x and x~=math.huge and x~=-math.huge end
local function number(v) v=canon.number(v);if finite(v) then return v end;return nil end
local function round2(x) return floor(x*100+0.5)/100 end
M.round2=round2
local function nv(v) if v==nil then return NULL end;return v end

local function read_file(path) local f=io.open(path,'rb');if not f then return nil end;local s=f:read('*a');f:close();return s end
function M.load_curve(path)
  local curve=canon.plain(canon.decode(assert(read_file(path or M.CURVE_PATH),'ADVISOR-CURVE-MISSING')))
  local a=curve.anchors
  if type(a)~='table' or #a<2 or a[1].t~=0 or a[#a].t~=1 then error('ADVISOR-CURVE-INVALID',0) end
  for i=1,#a-1 do if not (a[i].t<a[i+1].t) then error('ADVISOR-CURVE-INVALID',0) end end
  local fast=curve.fast_anchors
  if type(fast)~='table' then fast={};curve.fast_anchors=fast end
  local previous=0
  for _,x in ipairs(fast) do
    if not (x.t<previous) then error('ADVISOR-CURVE-INVALID',0) end
    previous=x.t
  end
  return curve
end

function M.round_step(x,step)
  local value=floor(x/step+0.5)*step
  if step>=1 then return floor(value+0.5) end
  return floor(value*100+0.5)/100
end
local function lerp(a,b,f)
  if a==nil or a==NULL or b==nil or b==NULL then return nil end
  return a+f*(b-a)
end
function M.segment(curve,t)
  local anchors=curve.anchors
  t=mmin(1.0,mmax(0.0,t))
  local i=1
  while i<#anchors-1 and anchors[i+1].t<=t do i=i+1 end
  local a,b=anchors[i],anchors[i+1]
  return a,b,(t-a.t)/(b.t-a.t)
end
-- advisor.fast_anchor: the step of a position t < 0, the fastest anchor it has reached (nil: not yet at -0.1)
function M.fast_anchor(curve,t)
  local best=nil
  for _,a in ipairs(curve.fast_anchors) do
    if t<=a.t+1e-9 then best=a end
  end
  return best
end
function M.interpolate(curve,t)
  local step=t<0 and M.fast_anchor(curve,t) or nil
  if step then
    local out={t=step.t}
    for k,name in ipairs(curve.params) do out[name]=step.p[k] end
    for k,name in ipairs(curve.fast_params) do
      local v=step.x[k]
      if v~=NULL then out[name]=v end
    end
    out.m={};for k=1,#step.m do out.m[k]=step.m[k] end
    out.g={};for k=1,#step.g do out.g[k]={step.g[k][1],step.g[k][2]} end
    return out
  end
  local a,b,f=M.segment(curve,t)
  local out={t=round2(mmin(1.0,mmax(0.0,t)))}
  for k,name in ipairs(curve.params) do out[name]=M.round_step(lerp(a.p[k],b.p[k],f),curve.steps[name]) end
  out.m={};for k=1,#a.m do out.m[k]=lerp(a.m[k],b.m[k],f) end
  out.g={};for k=1,#a.g do out.g[k]={lerp(a.g[k][1],b.g[k][1],f),lerp(a.g[k][2],b.g[k][2],f)} end
  return out
end

------------------------------------------------------------------------------------------------------
-- replay of an outage through the decision code (advisor.knowns / outcome / behaviour)
------------------------------------------------------------------------------------------------------
local KNOWN,KNOWN_SIZE={},0
function M.knowns(theta,dur_b,cons)
  local key=string.format('%.17g|%.17g|%s',theta,dur_b,tostring(cons))
  if KNOWN[key] then return KNOWN[key] end
  local p=CM.custom(theta,dur_b)
  local out={n=0}
  for _,di in ipairs(M.DENSE) do
    for _,phase in ipairs(M.PHASES) do
      local pi={1.0,0.0,0.0,0.0,0.0,0.0}
      local seen,tau,dense,found,failed=nil,phase-M.HISTORY,false,nil,0
      while tau<M.HORIZON do
        local fail=tau>=0
        local known=tau+(fail and (dense and CM.HTTP_DENSE or CM.HTTP_NORMAL) or CM.PUBLISHED)
        local dt=CM.FIRST_DT
        if seen~=nil then dt=mmin(mmax(known-seen,0.0),CM.DT_MAX) end
        CM.step(pi,dt,fail and 2 or 0,dense,p);seen=known
        if fail then failed=failed+1 end
        if fail and (CM.persist(pi,p)>=theta or (cons~=nil and failed>=cons)) then found=known;break end
        local suspect=1-pi[1]-pi[2]>=CM.SUSPECT
        if suspect then tau=mmax(tau+di,known) else tau=tau+M.NORMAL end
        dense=suspect
      end
      out.n=out.n+1;out[out.n]=found or false
    end
  end
  KNOWN_SIZE=KNOWN_SIZE+1
  if KNOWN_SIZE>64 then KNOWN={};KNOWN_SIZE=1 end
  KNOWN[key]=out
  return out
end
function M.outcome(d,known)
  local down,unnecessary,switched=0.0,0,0
  for i=1,known.n do
    local k=known[i]
    if k and d>k then
      local leave=k+M.EXEC;switched=switched+1
      down=down+mmin(d,leave)+2*M.BLIP
      if d<=leave then unnecessary=unnecessary+1 end
    else down=down+d end
  end
  return down/known.n,unnecessary/known.n,switched/known.n
end
local BEHAVIOUR,BEHAVIOUR_SIZE={},0
function M.behaviour(theta,dur_b,cons)
  local key=string.format('%.17g|%.17g|%s',theta,dur_b,tostring(cons))
  local hit=BEHAVIOUR[key]
  if hit then return hit[1],hit[2] end
  local ride,leave=M.behaviour_uncached(theta,dur_b,cons)
  BEHAVIOUR_SIZE=BEHAVIOUR_SIZE+1
  if BEHAVIOUR_SIZE>64 then BEHAVIOUR={};BEHAVIOUR_SIZE=1 end
  BEHAVIOUR[key]={ride,leave}
  return ride,leave
end
function M.behaviour_uncached(theta,dur_b,cons)
  local known=M.knowns(theta,dur_b,cons)
  local ride=0
  for d=1,M.HORIZON do local _,_,s=M.outcome(d,known);if s<0.5 then ride=d end end
  local leave,all=0,true
  for i=1,known.n do if not known[i] then all=false end end
  if all then
    for i=1,known.n do leave=leave+(known[i]+M.EXEC) end
    leave=leave/known.n
  else leave=nil end
  return ride,leave
end
function M.safety(params)
  local codes={}
  for _,key in ipairs(M.SAFE_ORDER) do
    local v=number(params[key]);local range=M.SAFE[key]
    if v==nil or v<range[1] or v>range[2] then return {'ADVISOR-OUT-OF-BOUNDS'} end
  end
  if params.pg<params.theta then codes[#codes+1]='ADVISOR-PG-BELOW-THETA' end
  if params.rescue_stable>params.primary_stable then codes[#codes+1]='ADVISOR-RESCUE-ABOVE-STABLE' end
  local ride,leave=M.behaviour(params.theta,params.dur_b,params.cons_f)
  if leave==nil or not (ride<leave) then codes[#codes+1]='ADVISOR-RIDE-NOT-BELOW-LEAVE' end
  return codes
end

------------------------------------------------------------------------------------------------------
-- settings
------------------------------------------------------------------------------------------------------
local function option_int(settings,key,low,high,default)
  local v=type(settings)=='table' and number(settings[key]) or nil
  if v~=nil and v%1==0 and v>=low and v<=high then return v end
  return default
end
function M.mode(settings) local v=type(settings)=='table' and settings.advisor_mode or nil;if M.MODES[v] then return v end;return M.DEFAULT_MODE end
function M.window(settings)
  local v=type(settings)=='table' and settings.advisor_window or nil
  if type(v)=='number' and M.WINDOWS[v] then return v end
  return M.DEFAULT_WINDOW
end
function M.slider_t(settings)
  local v=type(settings)=='table' and number(settings.slider_t) or nil
  if v~=nil and v>=M.MIN_T and v<=1 then return round2(v) end
  return nil
end
function M.fast_enabled(settings) return type(settings)=='table' and (settings.slider_fast==true or settings.slider_fast=='1') end
function M.t_floor(settings)
  if CM.turbo_on(settings) then return M.MIN_T end
  return M.fast_enabled(settings) and M.FAST_MIN_T or 0
end
local function params_of(curve,a) local p={};for k,name in ipairs(curve.params) do p[name]=a.p[k] end;return p end
function M.nearest(curve,params)
  local ride,leave=M.behaviour(params.theta,params.dur_b)
  local best_d,best_t=nil,nil
  for _,a in ipairs(curve.anchors) do
    local p=params_of(curve,a)
    local r,l=M.behaviour(p.theta,p.dur_b)
    local dl
    if leave==nil and l==nil then dl=0.0 elseif leave==nil or l==nil then dl=100.0 else dl=(leave-l)/2 end
    local dist=((ride-r)/2)^2+dl^2+((params.pg-p.pg)/0.05)^2+((params.primary_stable-p.primary_stable)/60)^2+((params.rescue_stable-p.rescue_stable)/5)^2
    if best_d==nil or dist<=best_d+1e-12 then best_d,best_t=dist,a.t end
  end
  return best_t
end
local PARAM_KEYS={'theta','dur_b','pg','primary_stable','rescue_stable'}
function M.current(settings,curve)
  local model=CM.name(settings)
  local preset=CM.PRESETS[model] or CM.PRESETS.hmm
  local theta,dur_b,pg=CM.numeric(settings,'hmm_theta'),CM.numeric(settings,'hmm_dur_b'),CM.numeric(settings,'return_pg')
  local numeric=theta~=nil or dur_b~=nil or pg~=nil
  local cur={theta=theta==nil and preset.theta or theta,dur_b=dur_b==nil and preset.dur_b or dur_b,pg=pg==nil and CM.HEALTHY or pg,
    primary_stable=option_int(settings,'recovery_primary_stable',30,600,120),rescue_stable=option_int(settings,'recovery_rescue_stable',0,60,10)}
  local t=M.slider_t(settings)
  local extra,beats=CM.or_failures(settings),CM.heartbeat_k(settings)
  local attached=false
  if t~=nil and model~='consecutive' then
    local point=M.interpolate(curve,t)
    attached=extra==point.cons_f and beats==point.beat_k
    for _,k in ipairs(PARAM_KEYS) do if abs(point[k]-cur[k])>=1e-9 then attached=false end end
  end
  local label
  if attached then label='slider'
  elseif not numeric and extra==nil and beats==nil and cur.primary_stable==120 and cur.rescue_stable==10 then label='preset'
  else label='custom' end
  cur.failure_model=model;cur.slider_t=t;cur.attached=attached;cur.label=label
  cur.nearest_t=M.nearest(curve,cur)
  cur.t_ref=attached and t or cur.nearest_t
  cur.or_failures=extra;cur.beats=beats;cur.fast=M.fast_enabled(settings);cur.turbo=CM.turbo_on(settings)
  return cur
end
function M.settings_key(settings)
  local cur={M.mode(settings),tostring(M.window(settings)),CM.name(settings)}
  for _,key in ipairs({'hmm_theta','hmm_dur_b','return_pg','slider_t','recovery_primary_stable','recovery_rescue_stable'}) do
    local v=type(settings)=='table' and number(settings[key]) or nil
    cur[#cur+1]=v==nil and '-' or string.format('%g',v)
  end
  -- the fast end only when it is in use (the key of every other router stays as it was)
  local extra,beats,fast=CM.or_failures(settings),CM.heartbeat_k(settings),M.fast_enabled(settings)
  if extra~=nil or beats~=nil or fast then
    local function shown(v) if v==nil then return 'None' end;return tostring(v) end
    cur[#cur+1]=string.format('fast%s/%s/%s',shown(extra),shown(beats),fast and 'True' or 'False')
  end
  return table.concat(cur,'|')
end

------------------------------------------------------------------------------------------------------
-- journal -> events
------------------------------------------------------------------------------------------------------
function M.day_weight(age,window_days) local half=mmax(window_days/2.0,0.5);return 0.5^(age/half) end
local function triples(rec)
  local out={};local o=rec.o or {}
  for i=1,#o-2,3 do out[#out+1]={o[i],o[i+1],o[i+2]} end
  return out
end
M.triples=triples
local function tuple_less(a,b)
  for i=1,3 do if a[i]~=b[i] then return a[i]<b[i] end end
  return false
end
local function sorted_keys(t) local k={};for key in pairs(t) do k[#k+1]=key end;table.sort(k);return k end
local function sorted_days(days) local list={};for i,d in ipairs(days) do list[i]=d end;table.sort(list,function(a,b) return a.d<b.d end);return list end

function M.events(days,today,window_days)
  local ev={outages={},groups={loss_light=0.0,loss_heavy=0.0,flap=0.0,reserve_fail=0.0,noisy=0.0},n=0,days=0,weight_days=0.0,
    counts={outages=0,short=0,medium=0,long=0,loss_episodes=0,flaps=0,noisy_hours=0,reserve_failures=0},durations={}}
  for _,day in ipairs(sorted_days(days)) do
    local age=today-1-day.d
    if age>=0 and age<window_days then
      local w=M.day_weight(age,window_days)
      local used=false
      for _,identifier in ipairs(sorted_keys(day.ch)) do
        local rec=day.ch[identifier]
        local outs=triples(rec);table.sort(outs,tuple_less)
        if rec.r==1 then
          for _,o in ipairs(outs) do
            local d,flags=o[2],o[3]
            if flags%2==1 and d>=M.RESERVE_MIN then
              ev.groups.reserve_fail=ev.groups.reserve_fail+w;ev.counts.reserve_failures=ev.counts.reserve_failures+1;ev.n=ev.n+1
            end
          end
        else
          used=true
          for _,o in ipairs(outs) do ev.durations[#ev.durations+1]=o[2] end
          local lossy={}
          for i=1,J.SLOTS do
            local shorts,fails,total=J.unpack(rec.lp[i])
            lossy[i]=total>=M.LOSSY_MIN_SAMPLES and fails>=M.LOSSY*total and shorts>=M.LOSSY_MIN_SHORTS
          end
          local i=1
          while i<=J.SLOTS do
            if not lossy[i] then i=i+1
            else
              local j,fails,total=i,0,0
              while j<=J.SLOTS and lossy[j] do local _,f,n=J.unpack(rec.lp[j]);fails=fails+f;total=total+n;j=j+1 end
              local group=fails>=M.HEAVY*total and 'loss_heavy' or 'loss_light'
              ev.groups[group]=ev.groups[group]+w*2*(j-i);ev.counts.loss_episodes=ev.counts.loss_episodes+1;ev.n=ev.n+1
              i=j
            end
          end
          local rest={}
          for _,o in ipairs(outs) do
            local s,d=o[1],o[2]
            if not (d<=J.SHORT and lossy[mmin(J.SLOTS-1,mmax(0,floor(s/J.SLOT)))+1]) then rest[#rest+1]={s,d} end
          end
          local keep={}
          local k=1
          while k<=#rest do
            local m=k
            while m+1<=#rest and rest[m+1][1]-(rest[m][1]+rest[m][2])<M.FLAP_GAP do m=m+1 end
            if m-k+1>=M.FLAP_MIN then ev.groups.flap=ev.groups.flap+w;ev.counts.flaps=ev.counts.flaps+1;ev.n=ev.n+1
            else for x=k,m do keep[#keep+1]=rest[x] end end
            k=m+1
          end
          local hours={}
          for _,o in ipairs(keep) do if o[2]<=M.NOISY_SHORT then local h=floor(o[1]/3600);hours[h]=(hours[h] or 0)+1 end end
          local noisy={};local list={}
          for h,c in pairs(hours) do if c>=M.NOISY_MIN then noisy[h]=true;list[#list+1]=h end end
          table.sort(list)
          for _ in ipairs(list) do ev.groups.noisy=ev.groups.noisy+w;ev.counts.noisy_hours=ev.counts.noisy_hours+1;ev.n=ev.n+1 end
          for _,o in ipairs(keep) do
            local s,d=o[1],o[2]
            if not (d<=M.NOISY_SHORT and noisy[floor(s/3600)]) then
              ev.outages[#ev.outages+1]={d,w};ev.n=ev.n+1;ev.counts.outages=ev.counts.outages+1
              local kind=d<=M.SHORT_MAX and 'short' or (d<=M.MEDIUM_MAX and 'medium' or 'long')
              ev.counts[kind]=ev.counts[kind]+1
            end
          end
        end
      end
      if used then ev.days=ev.days+1;ev.weight_days=ev.weight_days+w end
    end
  end
  table.sort(ev.durations)
  ev.counts.natural=#ev.durations
  return ev
end

function M.cost(ev,curve,theta,dur_b,t_table,cons)
  local known=M.knowns(theta,dur_b,cons)
  local down,unnecessary=0.0,0.0
  for _,o in ipairs(ev.outages) do
    local a,b=M.outcome(o[1],known)
    down=down+o[2]*a;unnecessary=unnecessary+o[2]*b
  end
  local a,b,f
  local step=t_table<0 and M.fast_anchor(curve,t_table) or nil
  if step then a,b,f=step,step,0.0 else a,b,f=M.segment(curve,t_table) end
  for index,group in ipairs(M.GROUPS) do
    if M.TABLE_GROUPS[group] then
      local weight=ev.groups[group]
      if weight>0 then
        down=down+weight*lerp(a.g[index][1],b.g[index][1],f);unnecessary=unnecessary+weight*lerp(a.g[index][2],b.g[index][2],f)
      end
    end
  end
  return down+curve.lambda_s*unnecessary,down,unnecessary
end
function M.cost_at(ev,curve,t)
  local point=M.interpolate(curve,t)
  return M.cost(ev,curve,point.theta,point.dur_b,point.t,point.cons_f)
end
function M.unimodal(values,tol)
  tol=tol or 1e-9
  local i=1
  while i<#values and values[i+1]<=values[i]+tol do i=i+1 end
  while i<#values and values[i+1]>=values[i]-tol do i=i+1 end
  return i==#values
end
function M.golden(f,a,b,tol)
  a=a or 0.0;b=b or 1.0;tol=tol or M.GOLDEN_TOL
  local g=(math.sqrt(5)-1)/2
  local c,d=b-g*(b-a),a+g*(b-a)
  local fc,fd,n=f(round2(c)),f(round2(d)),2
  while b-a>tol do
    if fc<=fd then b=d;d=c;fd=fc;c=b-g*(b-a);fc=f(round2(c))
    else a=c;c=d;fc=fd;d=a+g*(b-a);fd=f(round2(d)) end
    n=n+1
  end
  return round2((a+b)/2),n
end
function M.search(ev,curve,t_ref,fast)
  local costs,candidates={},{}
  for i,a in ipairs(curve.anchors) do
    costs[i]=(M.cost_at(ev,curve,a.t));candidates[i]={a.t,costs[i]}
  end
  local method,evaluations='anchors',#curve.anchors
  if fast then
    for _,a in ipairs(curve.fast_anchors) do
      if a.t>=M.FAST_MIN_T then
        candidates[#candidates+1]={a.t,(M.cost_at(ev,curve,a.t))};evaluations=evaluations+1
      end
    end
  end
  if M.unimodal(costs) then
    local t,n=M.golden(function(x) return (M.cost_at(ev,curve,x)) end)
    candidates[#candidates+1]={t,(M.cost_at(ev,curve,t))};method='golden';evaluations=evaluations+n+1
  end
  local best=nil
  for _,cand in ipairs(candidates) do
    local t,c=cand[1],cand[2]
    if best==nil or c<best[2]-1e-9 then best={t,c}
    elseif abs(c-best[2])<=1e-9 then
      local da,db=abs(t-t_ref),abs(best[1]-t_ref)
      if da<db or (da==db and t<best[1]) then best={t,c} end
    end
  end
  return {t=best[1],cost=best[2],method=method,anchor_costs=costs,evaluations=evaluations}
end

------------------------------------------------------------------------------------------------------
-- texts (advisor.reason): the same bytes as Python
------------------------------------------------------------------------------------------------------
function M.plural_ru(n,one,few,many)
  if n%10==1 and n%100~=11 then return one end
  if n%10>=2 and n%10<=4 and not (n%100>=12 and n%100<=14) then return few end
  return many
end
local function fnum(x,digits,lang)
  local text=string.format('%.'..digits..'f',x)
  if string.sub(text,1,1)=='-' and tonumber(text)==0 then text=string.sub(text,2) end
  if lang=='ru' then text=string.gsub(text,'%.',',') end
  return text
end
local function signed(x,digits,lang)
  local text=fnum(x,digits,lang)
  if string.sub(text,1,1)=='-' or tonumber((string.gsub(text,',','.')))==0 then return text end
  return '+'..text
end
local function where(cur,lang)
  if cur.attached then return (lang=='ru' and 'положение ' or 'position ')..fnum(cur.slider_t,2,lang) end
  if cur.label=='preset' then return lang=='ru' and 'стандартные настройки' or 'standard settings' end
  return lang=='ru' and 'пользовательские настройки' or 'custom settings'
end
local function facts(result,lang)
  local c,n,med=result.counts,result.days_used,result.outage_median_s
  local m=(med==nil or med==NULL) and '-' or tostring(med)
  if lang=='ru' then
    return string.format('на основании %d %s: обрывов основного %d (медиана %s с), эпизодов потерь %d, дребезга %d, отказов резерва %d',
      n,M.plural_ru(n,'дня','дней','дней'),c.natural,m,c.loss_episodes,c.flaps,c.reserve_failures)
  end
  return string.format('based on %d day%s: %d outages of the primary (median %s s), %d loss episodes, %d flaps, %d reserve failures',
    n,n==1 and '' or 's',c.natural,m,c.loss_episodes,c.flaps,c.reserve_failures)
end
function M.reason(result,cur,lang)
  local state=result.state
  if state=='no-data' then
    return lang=='ru' and 'Мало данных: журнал сети за выбранное окно пуст. Настройки не меняются.'
      or 'Not enough data: the network journal of the window is empty. Settings stay as they are.'
  end
  if state=='few-data' then
    local n,d=result.events,result.days_used
    if lang=='ru' then
      return string.format('Мало данных: %d %s за %d %s (нужно не меньше %d). Настройки не меняются.',
        n,M.plural_ru(n,'событие','события','событий'),d,M.plural_ru(d,'день','дня','дней'),M.MIN_EVENTS)
    end
    return string.format('Not enough data: %d event%s in %d day%s (at least %d needed). Settings stay as they are.',
      n,n==1 and '' or 's',d,d==1 and '' or 's',M.MIN_EVENTS)
  end
  local e=result.effect
  if state=='inactive' and cur.beats~=nil then
    return lang=='ru' and 'Турбо включён владельцем: советник его не рекомендует и не меняет.'
      or "Turbo is on by the owner's choice: the advisor neither recommends nor changes it."
  end
  if state=='inactive' then
    return lang=='ru' and 'Детектор «сбои подряд»: ползунок на него не действует, рекомендация не применяется.'
      or 'Detector "failures in a row": the slider does not apply to it; nothing is changed.'
  end
  if state=='keep' then
    if lang=='ru' then
      return string.format('Оставить %s: %s. Лучшее положение %s сэкономило бы %s %% (нужно не меньше 5 %%).',
        where(cur,'ru'),facts(result,'ru'),fnum(result.best_t,2,'ru'),fnum(e.saving_pct,1,'ru'))
    end
    return string.format('Keep %s: %s. The best position %s would save %s %% (at least 5 %% needed).',
      where(cur,'en'),facts(result,'en'),fnum(result.best_t,2,'en'),fnum(e.saving_pct,1,'en'))
  end
  if lang=='ru' then
    return string.format('Рекомендовано %s. Предлагается положение %s (сейчас: %s). Ожидаемо за сутки: простой %s с, лишних переключений %s, экономия %s %%.',
      facts(result,'ru'),fnum(result.t,2,'ru'),where(cur,'ru'),signed(-e.downtime_s_day,1,'ru'),signed(-e.unnecessary_per_day,2,'ru'),fnum(e.saving_pct,1,'ru'))
  end
  return string.format('Recommended %s. Suggested position %s (now: %s). Expected per day: downtime %s s, unnecessary switches %s, saving %s %%.',
    facts(result,'en'),fnum(result.t,2,'en'),where(cur,'en'),signed(-e.downtime_s_day,1,'en'),signed(-e.unnecessary_per_day,2,'en'),fnum(e.saving_pct,1,'en'))
end

------------------------------------------------------------------------------------------------------
-- the recommendation (advisor.recommend)
------------------------------------------------------------------------------------------------------
local function obj(t) return canon.object(t) end
local function float(x) if x==nil then return NULL end;return canon.float(x) end
function M.recommend(curve,days,settings,now,offset)
  local today=J.day_index(now,offset)
  local cur=M.current(settings,curve)
  local w=M.window(settings)
  local ev=M.events(days,today,w)
  local d=ev.durations
  local counts=obj({});for k,v in pairs(ev.counts) do counts[k]=v end
  local result={version=M.VERSION,day=today,generated=now,mode=M.mode(settings),window_days=w,key=M.settings_key(settings),
    events=ev.n,days_used=ev.days,counts=counts,outage_median_s=#d>0 and d[floor((#d-1)/2)+1] or nil,
    state=nil,t=nil,best_t=nil,method=nil,evaluations=0,anchor_costs=nil,effect=nil,predicted=nil}
  if ev.days==0 then result.state='no-data'
  elseif ev.n<M.MIN_EVENTS then result.state='few-data'
  else
    local best=M.search(ev,curve,cur.t_ref,cur.fast)
    local total,down,unnecessary=M.cost(ev,curve,cur.theta,cur.dur_b,cur.t_ref,cur.or_failures)
    local btotal,bdown,bunnecessary=M.cost_at(ev,curve,best.t)
    local saving=total>0 and (total-btotal)/total or 0.0
    local wd=ev.weight_days
    local costs={};for i,c in ipairs(best.anchor_costs) do costs[i]=round2(c) end
    result.best_t=best.t;result.method=best.method;result.evaluations=best.evaluations;result.anchor_costs=costs
    result.effect={saving_pct=floor(saving*1000+0.5)/10,downtime_s_day=floor((down-bdown)/wd*10+0.5)/10,
      unnecessary_per_day=floor((unnecessary-bunnecessary)/wd*100+0.5)/100,
      cost_now_s_day=floor(total/wd*10+0.5)/10,cost_best_s_day=floor(btotal/wd*10+0.5)/10}
    local moved=not (cur.attached and abs(best.t-cur.slider_t)<0.005)
    if cur.failure_model=='consecutive' or cur.beats~=nil then result.state='inactive'
    elseif saving>=M.MIN_SAVING and moved then result.state='shift';result.t=best.t
    else result.state='keep';result.t=cur.attached and cur.slider_t or nil end
    if result.t~=nil then
      local point=M.interpolate(curve,result.t)
      local predicted={}
      for k,name in ipairs(curve.metrics) do local x=point.m[k];predicted[name]=x~=nil and floor(x*100+0.5)/100 or nil end
      result.predicted=predicted
    end
  end
  result.reason_ru=M.reason(result,cur,'ru');result.reason_en=M.reason(result,cur,'en')
  return result
end

function M.calm_codes(calm)
  if type(calm)~='table' or calm==NULL then return {'ADVISOR-CALM-UNKNOWN'} end   -- no evidence of calm is no calm
  -- review F-82 (06.11.2026): no fresh observation of the route ('unknown', or none at all) is no evidence of calm either
  if calm.route==nil or calm.route==NULL or calm.route=='unknown' then return {'ADVISOR-CALM-UNKNOWN'} end
  local codes={}
  if type(calm.open)=='table' and calm.open~=NULL and #calm.open>0 then codes[#codes+1]='ADVISOR-BUSY-OUTAGE' end
  -- manual: the owner's click is waiting for the supervisor; a change of the settings now would end it in
  -- MANUAL-CONFIG-CHANGED (review 04.11.2026)
  if calm.route=='switching' or calm.route=='down' or M.TRANSITION[calm.native] or M.TRANSITION[calm.phase]
     or (calm.manual~=nil and calm.manual~=NULL and calm.manual~=false) then
    codes[#codes+1]='ADVISOR-BUSY-SWITCH'
  end
  return codes
end
function M.auto_step(curve,result,settings,changes,calm,now)
  local cur=M.current(settings,curve)
  local function no(code) return {apply=false,t=nil,code=code} end
  if M.mode(settings)~='auto' then return no('ADVISOR-NOT-AUTO') end
  if cur.failure_model=='consecutive' then return no('ADVISOR-MODEL-CONSECUTIVE') end
  if cur.beats~=nil then return no('ADVISOR-TURBO') end
  if type(result)~='table' or result.state~='shift' or number(result.t)==nil then return no('ADVISOR-NO-SHIFT') end
  local busy=M.calm_codes(calm)
  if #busy>0 then return no(busy[1]) end
  local last=nil
  for _,c in ipairs(type(changes)=='table' and changes or {}) do
    if type(c)=='table' and c.source=='auto' and number(c.time)~=nil then last=mmax(last or -math.huge,number(c.time)) end
  end
  if last~=nil and now-last<M.AUTO_SPACING then return no('ADVISOR-ONCE-A-DAY') end
  local start=cur.t_ref
  local delta=mmin(M.AUTO_STEP,mmax(-M.AUTO_STEP,number(result.t)-start))
  local t=round2(start+delta)
  if t<0 and not (cur.fast and t>=M.FAST_MIN_T) then return no('ADVISOR-FAST-OFF') end
  if cur.attached and abs(t-cur.slider_t)<0.005 then return no('ADVISOR-NO-SHIFT') end
  if #M.safety(M.interpolate(curve,t))>0 then return no('ADVISOR-UNSAFE') end
  return {apply=true,t=t,code=nil}
end
function M.job_due(result,key,now,offset,last_spawn)
  if last_spawn~=nil and now-last_spawn<M.RUN_SPACING then return false end
  if type(result)~='table' or result==NULL or type(result.day)~='number' or result.day%1~=0 then return true end
  if result.key~=key then return true end
  local today=J.day_index(now,offset)
  return now+offset-today*J.DAY>=M.RUN_AT and result.day~=today
end

------------------------------------------------------------------------------------------------------
-- public views (advisor.summary / public_status)
------------------------------------------------------------------------------------------------------
function M.summary(days,cur_day,today,window_days)
  local tunnels,pair,used={}, {switches=0,returns=0,unnecessary=0},0
  local list={};for _,d in ipairs(days) do list[#list+1]=d end
  if cur_day then list[#list+1]=cur_day end
  table.sort(list,function(a,b) return a.d<b.d end)
  for _,day in ipairs(list) do
    if today-day.d>=0 and today-day.d<=window_days then
      used=used+1
      pair.switches=pair.switches+day.sw;pair.returns=pair.returns+day.rt;pair.unnecessary=pair.unnecessary+day.us
      for identifier,rec in pairs(day.ch) do
        local t=tunnels[identifier]
        if not t then
          t={role='primary',n=0,f=0,hist={},d={},rs={},rn={},more=0}
          for i=1,#J.EDGES do t.hist[i]=0 end;for i=1,J.HOURS do t.rs[i]=0;t.rn[i]=0 end
          tunnels[identifier]=t
        end
        t.role=rec.r==1 and 'reserve' or 'primary'
        t.n=t.n+rec.n;t.f=t.f+rec.f;t.more=t.more+(rec.ox or 0)
        for i=1,#J.EDGES do t.hist[i]=t.hist[i]+rec.oh[i] end
        for i=1,J.HOURS do t.rs[i]=t.rs[i]+rec.rs[i];t.rn[i]=t.rn[i]+rec.rn[i] end
        for _,o in ipairs(triples(rec)) do t.d[#t.d+1]=o[2] end
      end
    end
  end
  local out=obj({})
  for _,identifier in ipairs(sorted_keys(tunnels)) do
    local t=tunnels[identifier];table.sort(t.d);local n=#t.d
    local total=0;for i=1,#t.hist do total=total+t.hist[i] end
    local rtt=canon.array();for i=1,J.HOURS do rtt[i]=t.rn[i]>0 and floor(t.rs[i]/t.rn[i]+0.5) or NULL end
    out[identifier]=obj({role=t.role,observations=t.n,loss_pct=t.n>0 and float(floor(1000*t.f/t.n+0.5)/10) or NULL,
      outages=total,outage_hist=canon.array(t.hist),outage_median_s=n>0 and t.d[floor((n-1)/2)+1] or NULL,
      outage_p90_s=n>=100 and t.d[math.ceil(0.9*n)] or NULL,survival_ready=n>=100,durations_kept=n,rtt_by_hour_ms=rtt})
  end
  local edges=canon.array();for i,e in ipairs(J.EDGES) do edges[i]=e end
  return obj({days=used,window_days=window_days,edges_s=edges,tunnels=out,pair=obj(pair)})
end

-- JSON form of a result (floats marked as in Python's json)
local FLOATS={generated=true,t=true,best_t=true}
function M.public_result(result)
  if type(result)~='table' then return NULL end
  local out=obj({})
  for k,v in pairs(result) do
    if FLOATS[k] and type(v)=='number' then out[k]=canon.float(v)
    elseif type(v)=='table' and v~=NULL and getmetatable(v)==nil then
      if #v>0 then local a=canon.array();for i,x in ipairs(v) do a[i]=type(x)=='number' and canon.float(x) or x end;out[k]=a
      else local o=obj({});for kk,x in pairs(v) do o[kk]=(type(x)=='number' and x%1~=0) and canon.float(x) or x end;out[k]=o end
    else out[k]=v end
  end
  for _,k in ipairs({'state','t','best_t','method','anchor_costs','effect','predicted','outage_median_s'}) do if out[k]==nil then out[k]=NULL end end
  return out
end
function M.public_status(settings,curve,result,journal_summary,changes)
  local cur=M.current(settings,curve)
  local rec=NULL
  if type(result)=='table' and result~=NULL then
    rec=obj({})
    for _,k in ipairs({'state','t','best_t','method','effect','predicted','reason_ru','reason_en','events','days_used','counts','generated','window_days','applied'}) do
      local v=result[k];if v==nil then v=NULL end;rec[k]=v
    end
  end
  local current=obj({})
  for _,k in ipairs({'t_ref','slider_t','attached','label','nearest_t','failure_model','theta','dur_b','pg','primary_stable','rescue_stable','or_failures','beats','fast','turbo'}) do
    local v=cur[k];if v==nil then v=NULL elseif type(v)=='number' and (k=='theta' or k=='dur_b' or k=='pg' or k=='t_ref' or k=='slider_t' or k=='nearest_t') then v=canon.float(v) end
    current[k]=v
  end
  local last=NULL
  if type(changes)=='table' and #changes>0 then last=changes[#changes] end
  return obj({mode=M.mode(settings),window_days=M.window(settings),curve_version=nv(curve.version),current=current,
    recommendation=rec,journal=journal_summary,last_change=last})
end

------------------------------------------------------------------------------------------------------
-- the monitor's part (advisor.MonitorPart): journal writer, starter of the nightly job, the status field
------------------------------------------------------------------------------------------------------
M.REQUEST_KEYS={'failure_model','hmm_theta','hmm_dur_b','return_pg','slider_t','advisor_mode','advisor_window',
  'recovery_primary_stable','recovery_rescue_stable','hmm_or_failures','turbo_beats','slider_fast','slider_turbo'}
local Part={};Part.__index=Part
-- io = {read(path)->text|nil, write_ram(path,text), write_flash(path,text), spawn()->bool}
function M.monitor_part(io,runtime,persist,now,curve)
  local self=setmetatable({io=io,runtime=runtime,persist=persist,curve=curve or M.load_curve(),last_spawn=now,changes={}},Part)
  self.writer=J.writer(io,runtime,persist)
  return self
end
function Part:read_result()
  local text=self.io.read(self.runtime..'/'..M.RESULT_NAME)
  if not text then return nil end
  local ok,value=pcall(canon.decode,text)
  if not ok or type(value)~='table' or value==NULL or canon.is_array(value) then return nil end
  return canon.plain(value)
end
function Part:pass(samples,pair,route,native_state,settings,now,offset,clock)
  local journal=self.writer.journal
  self.writer:pass(samples,pair,route,now,offset,clock)
  local result=self:read_result()
  local key=M.settings_key(settings)
  if M.job_due(result,key,now,offset,self.last_spawn) then
    local subset=canon.object()
    for _,k in ipairs(M.REQUEST_KEYS) do
      local v=type(settings)=='table' and settings[k] or nil
      if v~=nil and v~=NULL then subset[k]=(type(v)=='number' and v%1~=0) and canon.float(v) or v end
    end
    local request=canon.object({settings=subset,now=canon.float(now),offset=offset,key=key,
      calm=canon.object({open=J.open_outages(journal),route=nv(route),native=nv(native_state)})})
    self.io.write_ram(self.runtime..'/'..M.REQUEST_NAME,canon.encode(request))
    if self.io.spawn() then self.last_spawn=now end
  end
  local w=M.window(settings);local today=J.day_index(now,offset)
  local skey=table.concat({#journal.days,journal.cur and journal.cur.d or '-',w,floor(now/60)},'|')
  if skey~=self.summary_key then self.summary=M.summary(journal.days,journal.cur,today,w);self.summary_key=skey end
  local ckey=floor(now/60)
  if ckey~=self.changes_key then self.changes=M.changes(self.persist);self.changes_key=ckey end
  return M.public_status(settings,self.curve,result,self.summary,self.changes)
end

------------------------------------------------------------------------------------------------------
-- the nightly job: lua advisor.lua run
------------------------------------------------------------------------------------------------------
function M.changes(persist)
  local text=read_file(persist..'/'..M.CHANGES_NAME)
  if not text then return {} end
  local ok,value=pcall(canon.decode,text)
  if not ok or type(value)~='table' or type(value.changes)~='table' then return {} end
  local out={}
  for _,c in ipairs(canon.plain(value.changes)) do if type(c)=='table' then out[#out+1]=c end end
  return out
end
function M.load_days(runtime,persist)
  return J.load(read_file(runtime..'/'..J.DAYS_NAME),nil,read_file(persist..'/'..J.FLASH_NAME)).days
end
-- run(runtime, persist, apply(t, result) -> applied record | nil) -> result
function M.run(runtime,persist,apply,write)
  local raw=read_file(runtime..'/'..M.REQUEST_NAME)
  local ok,request=pcall(canon.decode,raw or '')
  if not ok or type(request)~='table' then error('ADVISOR-REQUEST-INVALID',0) end
  request=canon.plain(request)
  local settings=type(request.settings)=='table' and request.settings or {}
  local now,offset=number(request.now),request.offset
  if now==nil or type(offset)~='number' or offset%1~=0 then error('ADVISOR-REQUEST-INVALID',0) end
  local curve=M.load_curve()
  local result=M.recommend(curve,M.load_days(runtime,persist),settings,now,offset)
  local step=M.auto_step(curve,result,settings,M.changes(persist),request.calm,now)
  result.auto=obj({apply=step.apply,t=step.t and canon.float(step.t) or NULL,code=nv(step.code)})
  write(runtime..'/'..M.RESULT_NAME,canon.encode(M.public_result(result)))
  if step.apply and apply then
    result.applied=apply(step.t,result)
    write(runtime..'/'..M.RESULT_NAME,canon.encode(M.public_result(result)))
  end
  return result
end

if arg and arg[0] and string.find(arg[0],'advisor%.lua$') and arg[1]=='run' then
  local runtime,persist=canon.RUNTIME,'/etc/homensai-vpn'
  local durable=require('durable')
  local function write(path,text) durable.write(path,text,{sync=false}) end
  -- the settings write itself (UCI through setup_save.lua under the control lock) is advisor_control.py
  local function apply()
    local p=io.popen('/usr/bin/python3 /usr/lib/homensai-vpn/advisor_control.py auto-apply 2>/dev/null','r')
    local out=p and p:read('*a') or '';if p then p:close() end
    local okd,value=pcall(canon.decode,out)
    return okd and value or canon.object({saved=false,code='ADVISOR-APPLY-UNCONFIRMED'})
  end
  local okr,err=pcall(M.run,runtime,persist,apply,write)
  if not okr then io.stderr:write('advisor: ',tostring(err),'\n');os.exit(1) end
  os.exit(0)
end

return M
