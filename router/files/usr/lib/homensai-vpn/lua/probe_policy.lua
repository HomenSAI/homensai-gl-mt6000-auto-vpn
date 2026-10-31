-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- probe_policy.lua: probe_policy.py for the Lua monitor (owner probe level 1-5, the automatic boost, the dense
-- suspicion episode bookkeeping and the decision log probe-history.json).
-- Same files and rows as Python: state probe-boost.json in RAM (every pass), decisions probe-history.json on
-- flash (only on a level change and at the start/end of a boost or suspicion episode; at most 500 rows).
-- The passive suspicion watcher (suspicion.py) is not ported yet: suspect() exists for it but nothing calls it
-- in the Lua monitor; a dense episode carried over from the Python monitor still ends by the same rules.
-- io: {read_json(path,default), write_json(path,value)} (the monitor's runner adapters).
local canon=require('canon')

local M={}
M.LEVELS={[1]={60,300},[2]={30,120},[3]={20,60},[4]={15,45},[5]={10,30}}
M.DEFAULT_LEVEL=5
M.BOOST_INTERVAL=10;M.BOOST_MEASURE=30;M.BOOST_HOLD=600
M.CONFIRM_FAILURES=3
M.HISTORY_LIMIT=500
M.HISTORY_NAME='probe-history.json';M.STATE_NAME='probe-boost.json'
M.DENSE_INTERVAL=4;M.DENSE_MAX=60;M.DENSE_GOOD=2
M.SUSPICION_REST=30
M.FORCED_BOOST_LEVELS={[1]=true,[2]=true}
M.RESPONSE_METRICS={['icmp-1.1.1.1']='1.1.1.1',['icmp-8.8.8.8']='8.8.8.8',['icmp-9.9.9.9']='9.9.9.9',websites=false}
M.DEFAULT_RESPONSE='icmp-1.1.1.1'
local TRANSITIONS={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true,COMMITTED=true}
local WATCHING={OBSERVING=true,COMMITTED=true,['DEGRADED-ON-RESERVE']=true}
local SUSPICION_REASONS={['rx-stall']=true,['wg-handshake-stale']=true,['link-missing']=true}
local CARRIED={'dense','suspicion_rest','streaks'}
local NULL=canon.null
M.TRANSITIONS,M.WATCHING=TRANSITIONS,WATCHING

local function is_dict(v) return canon.is_object(v) or (type(v)=='table' and v~=NULL and not canon.is_array(v) and not canon.is_float(v) and next(v)~=nil and #v==0) end
local function num(v) return canon.number(v) end
local function finite(v) local x=num(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function none(v) return v==nil or v==NULL end
local function get(t,k) if not is_dict(t) then return nil end;local v=t[k];if v==NULL then return nil end;return v end

-- _int: a Python int or a string of digits within [low, high]
function M.int(value,low,high)
  if type(value)=='string' and string.find(value,'^%d+$') then value=tonumber(value) end
  if canon.is_float(value) then return nil end
  if type(value)=='number' and value%1==0 and value>=low and value<=high then return value end
  return nil
end
local int=M.int

function M.level(settings)
  local chosen=int(get(settings,'probe_level'),1,5)
  if chosen then return chosen end
  local interval=int(get(settings,'interval'),10,300) or 10
  for _,n in ipairs({5,4,3,2}) do if interval<=M.LEVELS[n][1] then return n end end
  return 1
end
function M.boost_enabled(settings)
  if M.FORCED_BOOST_LEVELS[M.level(settings)] then return true end
  local v=get(settings,'probe_boost')
  return not (v==false or v=='0')
end
function M.measure_interval(settings) return int(get(settings,'measure_interval'),30,300) or M.LEVELS[M.level(settings)][2] end
function M.measure_valid_for(interval) return math.floor(interval*3/2)+15 end
function M.response_metric(settings)
  local v=get(settings,'response_metric')
  if type(v)=='string' and M.RESPONSE_METRICS[v]~=nil then return v end
  return M.DEFAULT_RESPONSE
end
function M.failing(row)
  local h=get(row,'https_success')
  return get(row,'code')~=nil or get(row,'dns_ok')==false or not (type(h)=='number' and h%1==0) or h<2
end
local function bad_code(row) return get(row,'code') or (get(row,'dns_ok')==false and 'DNS-001' or 'VPN-003') end

local Booster={};Booster.__index=Booster
function M.Booster(runtime,persist,io_)
  local self=setmetatable({runtime=runtime,persist=persist,io=io_},Booster)
  local ok,state=pcall(io_.read_json,runtime..'/'..M.STATE_NAME,canon.object())
  if ok and is_dict(state) and type(state.active)=='boolean' then self.state=canon.object(state) else self.state=canon.object({active=false}) end
  return self
end
function Booster:active() return self.state.active==true end
function Booster:dense(now)
  local episode=get(self.state,'dense')
  if not is_dict(episode) or not finite(get(episode,'until')) then return nil end
  if now<=num(episode['until'])+M.DENSE_INTERVAL then return episode end
  return nil
end
function Booster:interval(settings,now)
  local normal=int(get(settings,'interval'),10,300) or 10
  if self:dense(now) then return math.min(normal,M.DENSE_INTERVAL) end
  return self:active() and math.min(normal,M.BOOST_INTERVAL) or normal
end
function Booster:measure(settings)
  local normal=M.measure_interval(settings)
  return self:active() and math.min(normal,M.BOOST_MEASURE) or normal
end
function Booster:history()
  local ok,rows=pcall(self.io.read_json,self.persist..'/'..M.HISTORY_NAME,canon.array())
  local out=canon.array()
  if ok and canon.is_array(rows) then
    for _,row in ipairs(rows) do if is_dict(row) and type(row.sequence)=='number' and row.sequence%1==0 then out[#out+1]=row end end
  end
  return out
end
function Booster:record(row,now)
  local rows=self:history()
  row=canon.object(row);row.time=canon.float(now);row.sequence=#rows>0 and rows[#rows].sequence+1 or 1
  for k,v in pairs(row) do if v==nil then row[k]=NULL end end
  rows[#rows+1]=row
  local kept=canon.array();for i=math.max(1,#rows-M.HISTORY_LIMIT+1),#rows do kept[#kept+1]=rows[i] end
  pcall(self.io.write_json,self.persist..'/'..M.HISTORY_NAME,kept)
  return row
end
local function n0(v) return v==nil and NULL or v end

function Booster:base(settings,kind)
  return {kind=kind,level=M.level(settings),interval=int(get(settings,'interval'),10,300) or 10,
    measure_interval=M.measure_interval(settings),boost_enabled=M.boost_enabled(settings)}
end

-- One decision per monitor pass; returns the history rows it recorded.
function Booster:observe(settings,rows,pair,native_state,now)
  local recorded=canon.array()
  local state=self.state
  local chosen,enabled=M.level(settings),M.boost_enabled(settings)
  local interval,measure=int(get(settings,'interval'),10,300) or 10,M.measure_interval(settings)
  local current=canon.array({chosen,interval,measure,enabled})
  if none(state.level) or canon.encode(state.level)~=canon.encode(current) then
    local row=self:base(settings,'level');row.result='applied';row.code=NULL
    recorded[#recorded+1]=self:record(row,now)
    state.level=current
  end
  local selected={}
  if is_dict(pair) then
    if get(pair,'source') then selected[pair.source]='source' end
    if get(pair,'target') then selected[pair.target]='target' end
  end
  local bad={}
  for _,row in ipairs(rows) do if is_dict(row) and get(row,'id')~=nil and selected[row.id] and M.failing(row) then bad[#bad+1]=row end end
  if get(state,'rest_profile') then
    for _,r in ipairs(rows) do if is_dict(r) and get(r,'id')==state.rest_profile and not M.failing(r) then state.rest_profile=nil;break end end
  end
  if self:active() then
    if TRANSITIONS[native_state] then state.switched=true end
    if #bad>0 then
      local failures=(num(get(state,'failures')) or 0)+1
      local started=num(get(state,'started')) or now
      local done=get(state,'switched') or failures>M.CONFIRM_FAILURES
      state.failures=failures;state.last_code=bad_code(bad[1])
      state['until']=done and n0(get(state,'until') or 0) or canon.float(math.min(now+M.BOOST_HOLD,started+2*M.BOOST_HOLD))
    end
    if not enabled or now>=(num(get(state,'until')) or 0) then
      local result=get(state,'switched') and 'switched' or ((num(get(state,'failures')) or 0)>=M.CONFIRM_FAILURES and 'failure-confirmed' or 'false-alarm')
      if not enabled then result='disabled' end
      local trigger=is_dict(get(state,'trigger')) and state.trigger or {}
      local row=self:base(settings,'boost-end')
      row.profile=n0(get(trigger,'profile'));row.role=n0(get(trigger,'role'));row.code=n0(get(state,'last_code') or get(trigger,'code'))
      row.result=result;row.failures=math.floor(num(get(state,'failures')) or 0)
      row.duration=math.floor(math.max(0,now-(num(get(state,'started')) or now))+0.5);row.boost_interval=M.BOOST_INTERVAL
      recorded[#recorded+1]=self:record(row,now)
      local carried=canon.object()
      for _,key in ipairs(CARRIED) do if state[key]~=nil then carried[key]=state[key] end end
      carried.active=false;carried.level=current;carried.rest_until=canon.float(now+M.BOOST_HOLD);carried.rest_profile=n0(get(trigger,'profile'))
      self.state=carried;state=carried
    end
  elseif enabled and #bad>0 and WATCHING[native_state] and now>=(num(get(state,'rest_until')) or 0) and get(bad[1],'id')~=get(state,'rest_profile') then
    local row=bad[1];local code=bad_code(row)
    local trigger=canon.object({profile=row.id,role=n0(selected[row.id]),code=code})
    state.active=true;state.started=canon.float(now);state['until']=canon.float(now+M.BOOST_HOLD);state.failures=1
    state.switched=TRANSITIONS[native_state]==true;state.trigger=trigger;state.last_code=code
    local rec=self:base(settings,'boost-start')
    rec.boost_enabled=true;rec.profile=trigger.profile;rec.role=trigger.role;rec.code=code;rec.result='started';rec.boost_interval=M.BOOST_INTERVAL
    recorded[#recorded+1]=self:record(rec,now)
  end
  for _,row in ipairs(self:dense_observe(settings,rows,pair,native_state,now)) do recorded[#recorded+1]=row end
  pcall(self.io.write_json,self.runtime..'/'..M.STATE_NAME,self.state)
  return recorded
end

function Booster:episode_row(settings,kind,episode,now,fields)
  local row=self:base(settings,kind)
  row.profile=n0(get(episode,'profile'));row.role=n0(get(episode,'role'));row.reason=n0(get(episode,'reason'));row.dense_interval=M.DENSE_INTERVAL
  for k,v in pairs(fields) do row[k]=v end
  return self:record(row,now)
end

-- A passive suspicion asks for an immediate full check and dense confirmation (suspicion.py not ported yet).
function Booster:suspect(settings,suspicions,pair,native_state,now)
  if self:dense(now) or not WATCHING[native_state] or not is_dict(pair) then return false end
  local roles={}
  if get(pair,'source') then roles[pair.source]='source' end
  if get(pair,'target') then roles[pair.target]='target' end
  local rest=is_dict(get(self.state,'suspicion_rest')) and self.state.suspicion_rest or canon.object()
  local streaks=is_dict(get(self.state,'streaks')) and self.state.streaks or canon.object()
  for _,item in ipairs(type(suspicions)=='table' and suspicions or {}) do
    local profile=is_dict(item) and SUSPICION_REASONS[get(item,'reason')] and get(item,'profile') or nil
    if profile and roles[profile] then
      local held=is_dict(get(rest,profile)) and rest[profile] or {}
      local streak=is_dict(get(streaks,profile)) and streaks[profile] or {}
      if now>=(num(get(held,'until')) or 0) and (num(get(streak,'failures')) or 0)<M.CONFIRM_FAILURES then
        local evidence=canon.object()
        for _,k in ipairs({'stalled_s','tx_packets','handshake_age_s'}) do local e=get(item,'evidence');if is_dict(e) and e[k]~=nil then evidence[k]=e[k] end end
        local episode=canon.object({profile=profile,role=roles[profile],reason=item.reason,evidence=evidence,started=canon.float(now),
          ['until']=canon.float(now+M.DENSE_MAX),native_state=native_state,checks=0,failures=0,good=0,reserve_good=0,last_code=NULL})
        self.state.dense=episode
        self:episode_row(settings,'suspicion-start',episode,now,{evidence=evidence,code=NULL,result='started'})
        pcall(self.io.write_json,self.runtime..'/'..M.STATE_NAME,self.state)
        return true
      end
    end
  end
  return false
end

function Booster:dense_observe(settings,rows,pair,native_state,now)
  local recorded={}
  local state=self.state
  local streaks=is_dict(get(state,'streaks')) and state.streaks or canon.object()
  local ids={}
  if is_dict(pair) then ids={get(pair,'source'),get(pair,'target')} end
  local idset={};for i=1,2 do if ids[i]~=nil then idset[ids[i]]=true end end
  for _,row in ipairs(rows) do
    if is_dict(row) and get(row,'id')~=nil and idset[row.id] then
      local previous=is_dict(get(streaks,row.id)) and streaks[row.id] or {}
      streaks[row.id]=canon.object({failures=M.failing(row) and math.floor((num(get(previous,'failures')) or 0)+1) or 0,time=canon.float(now)})
    end
  end
  local kept=canon.object();for k,v in pairs(streaks) do if idset[k] then kept[k]=v end end
  state.streaks=kept
  local episode=get(state,'dense')
  if not is_dict(episode) then return recorded end
  if not self:dense(now) then episode['until']=canon.float(now) end
  local suspect=get(episode,'profile')
  local reserve=nil
  for i=1,2 do if ids[i]~=nil and ids[i]~=suspect then reserve=ids[i];break end end
  local row,other
  for _,r in ipairs(rows) do
    if is_dict(r) and get(r,'id')==suspect and row==nil then row=r end
    if is_dict(r) and reserve~=nil and get(r,'id')==reserve and other==nil then other=r end
  end
  for _,key in ipairs({'checks','failures','good','reserve_good'}) do episode[key]=math.floor(num(get(episode,key)) or 0) end
  if row then
    episode.checks=episode.checks+1
    if M.failing(row) then episode.failures=episode.failures+1;episode.good=0;episode.last_code=bad_code(row)
    else episode.good=episode.good+1;episode.failures=0 end
  end
  if other then episode.reserve_good=M.failing(other) and 0 or episode.reserve_good+1 end
  local switched=TRANSITIONS[native_state] or (native_state~=get(episode,'native_state') and (native_state=='COMMITTED' or native_state=='DEGRADED-ON-RESERVE'))
  local result
  if switched then result='switched'
  elseif episode.good>=M.DENSE_GOOD then result='false-alarm'
  elseif episode.failures>=M.CONFIRM_FAILURES and (reserve==nil or episode.reserve_good>=M.DENSE_GOOD) then result='failure-confirmed'
  elseif not WATCHING[native_state] then result='cancelled'
  elseif now>=(num(get(episode,'until')) or 0) then result=episode.failures>=M.CONFIRM_FAILURES and 'failure-confirmed' or 'expired' end
  if not result then return recorded end
  local rest=is_dict(get(state,'suspicion_rest')) and state.suspicion_rest or canon.object()
  local held=is_dict(get(rest,suspect)) and rest[suspect] or {}
  local alarms=result=='false-alarm' and math.floor((num(get(held,'false_alarms')) or 0)+1) or 0
  local pause=math.min(M.SUSPICION_REST*2^math.max(0,alarms-1),M.BOOST_HOLD)
  rest[suspect]=canon.object({['until']=canon.float(now+pause),false_alarms=alarms})
  local rkept=canon.object();for k,v in pairs(rest) do if idset[k] then rkept[k]=v end end
  state.suspicion_rest=rkept
  state.dense=nil
  recorded[#recorded+1]=self:episode_row(settings,'suspicion-end',episode,now,{result=result,code=n0(get(episode,'last_code')),
    checks=episode.checks,failures=episode.failures,reserve_good=episode.reserve_good,
    duration=math.floor(math.max(0,now-(num(get(episode,'started')) or now))+0.5),rest=pause})
  return recorded
end

function Booster:public(settings,now)
  local trigger=is_dict(get(self.state,'trigger')) and self.state.trigger or canon.object()
  local dense=self:dense(now)
  local suspicion=NULL
  if dense then
    suspicion=canon.object()
    for _,k in ipairs({'profile','role','reason','started','until'}) do suspicion[k]=n0(get(dense,k)) end
  end
  local levels=canon.object()
  for k,v in pairs(M.LEVELS) do levels[tostring(k)]=canon.array({v[1],v[2]}) end
  local active=self:active()
  return canon.object({level=M.level(settings),interval=int(get(settings,'interval'),10,300) or 10,measure_interval=M.measure_interval(settings),
    boost_enabled=M.boost_enabled(settings),boost_active=active,boost_until=active and n0(get(self.state,'until')) or NULL,
    boost_trigger=active and trigger or NULL,effective_interval=self:interval(settings,now),effective_measure_interval=self:measure(settings),
    suspicion=suspicion,dense_interval=M.DENSE_INTERVAL,boost_interval=M.BOOST_INTERVAL,boost_hold=M.BOOST_HOLD,levels=levels})
end

return M
