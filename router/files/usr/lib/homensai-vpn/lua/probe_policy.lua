-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- probe_policy.lua: probe_policy.py for the Lua monitor (owner probe level 1-5, the automatic boost, the dense
-- suspicion episode bookkeeping and the decision log probe-history.json).
-- Same files and rows as Python: state probe-boost.json in RAM (every pass), decisions probe-history.json on
-- flash (only on a level change and at the start/end of a boost or suspicion episode; at most 500 rows).
-- The passive suspicion watcher (suspicion.py) is not ported; suspect() is called by the fast-detection pulse
-- (fast_detect.lua, reason 'heartbeat-lost', only with option lua_fast_detect '1'); a dense episode carried over
-- from the Python monitor still ends by the same rules.
-- io: {read_json(path,default), write_json(path,value)} (the monitor's runner adapters).
-- Failure model (channel_model.lua, option failure_model 'hmm'/'hmm-fast'): observe(..., models) with the monitor's
-- per-channel views; the model's suspicion of the channel carrying traffic starts an episode (reason 'model') and
-- the model decides when an episode ends (probe_policy.py, the same rules).
local canon=require('canon')

local M={}
M.LEVELS={[1]={60,300},[2]={30,120},[3]={20,60},[4]={15,45},[5]={10,30}}
M.DEFAULT_LEVEL=5
M.BOOST_INTERVAL=10;M.BOOST_MEASURE=30;M.BOOST_HOLD=600
M.CONFIRM_FAILURES=3
M.HISTORY_LIMIT=500
M.HISTORY_NAME='probe-history.json';M.STATE_NAME='probe-boost.json'
-- Firmware wait (owner decision 01.11.2026, variant A; probe_policy.py): while a tunnel of the Auto pair is
-- PENDING or inside its settle period, or Auto waits only for the firmware, passes run every WAIT_INTERVAL s
-- (memory only, at most WAIT_MAX s per wait). The vendor gate rules are unchanged.
M.WAIT_INTERVAL=10;M.WAIT_MAX=600
M.WAIT_BLOCKERS={['VENDOR-SETTLING']=true,['PROFILE-IDENTITY-CHANGED']=true,['VENDOR-WORKER-BUSY']=true,['OBSERVATION-STALE']=true}
M.DENSE_INTERVAL=4;M.DENSE_MAX=60;M.DENSE_GOOD=2
M.TURBO_DENSE=3    -- the expert opt-in only (M.dense_interval)
M.SUSPICION_REST=30
M.FORCED_BOOST_LEVELS={[1]=true,[2]=true}
M.RESPONSE_METRICS={['icmp-1.1.1.1']='1.1.1.1',['icmp-8.8.8.8']='8.8.8.8',['icmp-9.9.9.9']='9.9.9.9',websites=false}
M.DEFAULT_RESPONSE='icmp-1.1.1.1'
local TRANSITIONS={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true,COMMITTED=true}
local WATCHING={OBSERVING=true,COMMITTED=true,['DEGRADED-ON-RESERVE']=true}
-- 'wg-rekey' (wg_events.lua) and 'wan-ok-tunnel-down' (wan_diag.lua hasten): GL-SENSORS-2026-11-04, dense checks only
local SUSPICION_REASONS={['rx-stall']=true,['wg-handshake-stale']=true,['link-missing']=true,['heartbeat-lost']=true,
  ['wg-rekey']=true,['wan-ok-tunnel-down']=true,['cusum-loss']=true}
-- REST_BYPASS, CUSUM_* (probe_policy.py; CUSUM-TRIGGER-2026-11-04.ru.md): these reasons pass a running suspicion rest,
-- bounded by what the dense checks found: state cusum_at {profile -> {at=end of the last such episode, clean=such
-- episodes in a row in which no check failed}}. A failed dense check clears clean; no gap while clean <= CUSUM_FREE,
-- then CUSUM_GAP*2^(clean-CUSUM_FREE-1) seconds, at most CUSUM_GAP_MAX.
M.REST_BYPASS={['cusum-loss']=true};M.CUSUM_FREE=2;M.CUSUM_GAP=60;M.CUSUM_GAP_MAX=600
local CARRIED={'dense','suspicion_rest','streaks','cusum_at'}
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
-- probe_policy.ping_interval / ping_valid_for: the owner ping cadence (option ping_interval, 10..300 s in steps
-- of 10, otherwise 60) and its freshness window: 1.5 x max(ping cadence, normal check interval) + 15 s, at least 45 s.
M.PING_INTERVAL_DEFAULT=60;M.PING_INTERVAL_MIN=10;M.PING_INTERVAL_MAX=300;M.PING_INTERVAL_STEP=10;M.PING_VALID_FLOOR=45
function M.ping_interval(settings)
  local v=int(get(settings,'ping_interval'),M.PING_INTERVAL_MIN,M.PING_INTERVAL_MAX)
  if v and v%M.PING_INTERVAL_STEP==0 then return v end
  return M.PING_INTERVAL_DEFAULT
end
function M.ping_valid_for(settings)
  local spacing=math.max(M.ping_interval(settings),int(get(settings,'interval'),10,300) or 10)
  return math.max(M.PING_VALID_FLOOR,M.measure_valid_for(spacing))
end
function M.response_metric(settings)
  local v=get(settings,'response_metric')
  if type(v)=='string' and M.RESPONSE_METRICS[v]~=nil then return v end
  return M.DEFAULT_RESPONSE
end
-- probe_policy.dense_interval: M.DENSE_INTERVAL, or M.TURBO_DENSE with the expert opt-in (channel_model.heartbeat_k)
function M.dense_interval(settings)
  return require('channel_model').heartbeat_k(settings)~=nil and M.TURBO_DENSE or M.DENSE_INTERVAL
end
-- probe_policy.wake_row: L1, the hint the monitor leaves in RAM after it published a failed sample of an Auto channel
function M.wake_row(settings,rows,pair,now)
  local off=get(settings,'auto_event_wake')
  if off==false or off=='0' or not is_dict(pair) or type(rows)~='table' then return nil end
  local source,target=get(pair,'source'),get(pair,'target')
  for _,row in ipairs(rows) do
    if type(row)=='table' and row~=NULL then
      local id=row.id
      if type(id)=='string' and (id==source or id==target) and M.failing(row) then return canon.object({reason='sample',time=canon.float(now),id=id}) end
    end
  end
  return nil
end
function M.failing(row)
  local h=get(row,'https_success')
  return get(row,'code')~=nil or get(row,'dns_ok')==false or not (type(h)=='number' and h%1==0) or h<2
end
local function bad_code(row) return get(row,'code') or (get(row,'dns_ok')==false and 'DNS-001' or 'VPN-003') end

-- Seconds a REST_BYPASS reason waits after the end of the last such episode.
function M.cusum_gap(clean)
  if clean<=M.CUSUM_FREE then return 0 end
  return math.min(M.CUSUM_GAP*2^(clean-M.CUSUM_FREE-1),M.CUSUM_GAP_MAX)
end

-- probe_policy.firmware_wait: a tunnel of the Auto pair is PENDING or inside its settle period, or Auto waits
-- only for the firmware (ARMED, or BLOCKED with WAIT_BLOCKERS only).
function M.firmware_wait(settings,observation,pair,native,now)
  if is_dict(native) then
    local state,blockers=get(native,'state'),get(native,'blockers')
    if state=='ARMED' then return true end
    if state=='BLOCKED' and canon.is_array(blockers) and #blockers>0 then
      local all=true
      for _,x in ipairs(blockers) do if type(x)~='string' or not M.WAIT_BLOCKERS[x] then all=false end end
      if all then return true end
    end
  end
  local ids,any={},false
  if is_dict(pair) then
    for _,role in ipairs({'source','target'}) do
      local v=get(pair,role);if type(v)=='string' then ids[v]=true;any=true end
    end
  end
  local groups=is_dict(observation) and get(observation,'groups') or nil
  if not any or not canon.is_array(groups) then return false end
  -- pair.settle_for reads only a canon object (plain monitor settings would give the legacy 60 s)
  local settle=require('pair').settle_for(canon.object({interval=get(settings,'interval')}))
  for _,group in ipairs(groups) do
    local current=is_dict(group) and get(group,'current_profile') or nil
    if type(current)=='string' and ids[current] then
      if get(group,'state')=='PENDING' then return true end
      local changed=get(group,'changed_at')
      if get(group,'state')=='SETTLED' and type(changed)~='boolean' and finite(changed)
         and 0<=now-num(changed) and now-num(changed)<settle then return true end
    end
  end
  return false
end

local Booster={};Booster.__index=Booster
function M.Booster(runtime,persist,io_)
  local self=setmetatable({runtime=runtime,persist=persist,io=io_},Booster)
  local ok,state=pcall(io_.read_json,runtime..'/'..M.STATE_NAME,canon.object())
  if ok and is_dict(state) and type(state.active)=='boolean' then self.state=canon.object(state) else self.state=canon.object({active=false}) end
  return self
end
function Booster:active() return self.state.active==true end
function Booster:waiting(now)
  local since=self.wait_since
  return since~=nil and 0<=now-since and now-since<=M.WAIT_MAX
end
function Booster:note_wait(settings,observation,pair,native,now)
  if M.firmware_wait(settings,observation,pair,native,now) then
    if self.wait_since==nil or now<self.wait_since then self.wait_since=now end
  else self.wait_since=nil end
  return self:waiting(now)
end
function Booster:dense(now)
  local episode=get(self.state,'dense')
  if not is_dict(episode) or not finite(get(episode,'until')) then return nil end
  if now<=num(episode['until'])+M.DENSE_INTERVAL then return episode end
  return nil
end
function Booster:interval(settings,now)
  local normal=int(get(settings,'interval'),10,300) or 10
  if self:dense(now) then return math.min(normal,M.dense_interval(settings)) end
  if self:waiting(now) then return math.min(normal,M.WAIT_INTERVAL) end
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
-- models: {profile id = channel_model.public view} of the pair channels (HMM modes), or nil.
function Booster:observe(settings,rows,pair,native_state,now,models)
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
  if type(models)~='table' then models=nil end
  for _,row in ipairs(self:dense_observe(settings,rows,pair,native_state,now,models)) do recorded[#recorded+1]=row end
  for _,row in ipairs(self:model_suspect(settings,pair,native_state,now,models)) do recorded[#recorded+1]=row end
  pcall(self.io.write_json,self.runtime..'/'..M.STATE_NAME,self.state)
  return recorded
end

function Booster:episode_row(settings,kind,episode,now,fields)
  local row=self:base(settings,kind)
  row.profile=n0(get(episode,'profile'));row.role=n0(get(episode,'role'));row.reason=n0(get(episode,'reason'));row.dense_interval=M.dense_interval(settings)
  for k,v in pairs(fields) do row[k]=v end
  return self:record(row,now)
end

-- A passive suspicion asks for an immediate full check and dense confirmation (suspicion.py not ported yet).
-- models: as in observe(); a REST_BYPASS reason adds nothing once the failure model decided.
function Booster:suspect(settings,suspicions,pair,native_state,now,models)
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
      local bypass=M.REST_BYPASS[item.reason]==true
      local decided=false
      if bypass then
        local view=type(models)=='table' and models[profile] or nil
        decided=type(view)=='table' and view.failed==true
        local at,clean=self:forced(profile)
        bypass=now>=at+M.cusum_gap(clean) or now<at
      end
      if not decided and (bypass or now>=(num(get(held,'until')) or 0)) and (num(get(streak,'failures')) or 0)<M.CONFIRM_FAILURES then
        local evidence=canon.object()
        for _,k in ipairs({'stalled_s','tx_packets','handshake_age_s','losses','cause','event'}) do local e=get(item,'evidence');if is_dict(e) and e[k]~=nil then evidence[k]=e[k] end end
        local episode=canon.object({profile=profile,role=roles[profile],reason=item.reason,evidence=evidence,started=canon.float(now),
          ['until']=canon.float(now+M.DENSE_MAX),native_state=native_state,checks=0,failures=0,good=0,reserve_good=0,last_code=NULL})
        self.state.dense=episode
        if M.REST_BYPASS[item.reason] then self:note_forced(profile,now,nil,roles) end
        self:episode_row(settings,'suspicion-start',episode,now,{evidence=evidence,code=NULL,result='started'})
        pcall(self.io.write_json,self.runtime..'/'..M.STATE_NAME,self.state)
        return true
      end
    end
  end
  return false
end

-- The channel's record of REST_BYPASS episodes: at, clean (a damaged one counts as none).
function Booster:forced(profile)
  local forced=get(self.state,'cusum_at')
  local record=is_dict(forced) and get(forced,profile) or nil
  local at=is_dict(record) and get(record,'at') or nil
  local clean=is_dict(record) and get(record,'clean') or nil
  if not finite(at) or type(clean)~='number' or clean%1~=0 or clean<0 then return -math.huge,0 end
  return num(at),clean
end
function Booster:note_forced(profile,at,clean,ids)
  local forced=is_dict(get(self.state,'cusum_at')) and self.state.cusum_at or {}
  local kept=canon.object()
  for key,value in pairs(forced) do if ids==nil or ids[key] then kept[key]=value end end
  local last_at,last_clean=self:forced(profile)
  kept[profile]=canon.object({at=canon.float(at or last_at),clean=clean or last_clean})
  self.state.cusum_at=kept
end

-- The failure model's suspicion of the channel carrying traffic starts a dense episode (reason 'model').
function Booster:model_suspect(settings,pair,native_state,now,models)
  if models==nil or self:dense(now) or not WATCHING[native_state] or not is_dict(pair) then return {} end
  local role=native_state=='OBSERVING' and 'source' or 'target'
  local profile=get(pair,role)
  local view=profile~=nil and models[profile] or nil
  if type(view)~='table' or view.suspect~=true or view.failed==true then return {} end
  local rest=is_dict(get(self.state,'suspicion_rest')) and self.state.suspicion_rest or canon.object()
  local held=is_dict(get(rest,profile)) and rest[profile] or {}
  if now<(num(get(held,'until')) or 0) then return {} end
  local evidence=canon.object({p_bad=n0(view.p_bad),persist=n0(view.persist)})
  local episode=canon.object({profile=profile,role=role,reason='model',evidence=evidence,started=canon.float(now),
    ['until']=canon.float(now+M.DENSE_MAX),native_state=native_state,checks=0,failures=0,good=0,reserve_good=0,last_code=NULL})
  self.state.dense=episode
  return {self:episode_row(settings,'suspicion-start',episode,now,{evidence=evidence,code=NULL,result='started'})}
end

function Booster:dense_observe(settings,rows,pair,native_state,now,models)
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
    if M.failing(row) then
      episode.failures=episode.failures+1;episode.good=0;episode.bad=true;episode.last_code=bad_code(row)
      local _,clean=self:forced(suspect)
      if clean>0 then self:note_forced(suspect,nil,0) end
    else episode.good=episode.good+1;episode.failures=0 end
  end
  if other then episode.reserve_good=M.failing(other) and 0 or episode.reserve_good+1 end
  local switched=TRANSITIONS[native_state] or (native_state~=get(episode,'native_state') and (native_state=='COMMITTED' or native_state=='DEGRADED-ON-RESERVE'))
  local result
  local view=models~=nil and models[suspect] or nil
  if type(view)=='table' then
    -- the failure model decides the episode (it decides the switch too)
    local decided=view.failed==true
    if switched then result='switched'
    elseif episode.good>=M.DENSE_GOOD and view.suspect~=true then result='false-alarm'
    elseif decided and (reserve==nil or episode.reserve_good>=M.DENSE_GOOD) then result='failure-confirmed'
    elseif not WATCHING[native_state] then result='cancelled'
    elseif now>=(num(get(episode,'until')) or 0) then result=decided and 'failure-confirmed' or 'expired' end
  elseif switched then result='switched'
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
  if M.REST_BYPASS[get(episode,'reason')] then
    local _,clean=self:forced(suspect)
    self:note_forced(suspect,now,clean+(get(episode,'bad') and 0 or 1))
  end
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
    ping_interval=M.ping_interval(settings),ping_valid_for=M.ping_valid_for(settings),
    effective_ping_interval=math.max(M.ping_interval(settings),self:interval(settings,now)),
    suspicion=suspicion,dense_interval=M.dense_interval(settings),boost_interval=M.BOOST_INTERVAL,boost_hold=M.BOOST_HOLD,levels=levels})
end

return M
