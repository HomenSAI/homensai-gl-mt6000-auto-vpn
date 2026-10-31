-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- reliability.lua: reliability.py (Reliability: seven-day incident detail, monthly and lifetime observed counters;
-- active_controller) and route_history.py (RouteHistory: compact observed route intervals of the last 24 hours;
-- observed_route) for the Lua monitor (Lua plan item 6). The data lives inside checkpoint.json under
-- accounting.reliability exactly as agent.Accounting.export() writes it, so either line restores what the other
-- saved.
--
-- Values keep their Python types: an int stays a plain Lua number, a Python float is a canon.float box (decoded
-- floats are boxed; every time stamp the monitor passes in is a float, as time.time() is in Python). Arithmetic
-- follows Python: int+int is an int, anything with a float is a float. min()/max() return one of their operands,
-- the first one on a tie, as Python does. Canonical JSON of the export is therefore the same text as
-- json.dumps(export, sort_keys=True) of the Python object fed with the same inputs (tests/test_lua_history.py).
--
-- Difference: on an exact tie of two profiles' last observation times the 400-profile bound drops the
-- lexicographically smallest id (Python: the first inserted); prune() measures the detail budget with a
-- per-event cache of the encoded length instead of encoding the whole list again (same number).
local canon=require('canon')

local M={}
local NULL=canon.null
M.DAY=86400;M.WEEK=7*86400
M.MAX_EVENTS=10000;M.DETAIL_BYTES=1024*1024
M.METRICS={'checks','failed_checks','outages','recoveries','observed_up_seconds','observed_down_seconds','unknown_intervals','auto_observed_seconds'}
local METRIC_SET={};for _,m in ipairs(M.METRICS) do METRIC_SET[m]=true end
local BAD={['VPN-001']=true,['VPN-003']=true,['DNS-001']=true}
M.BAD=BAD
local ROUTE_KINDS={source=true,target=true,switching=true,unknown=true,off=true,blocked=true,down=true}
M.ROUTE_KINDS=ROUTE_KINDS

------------------------------------------------------------------------------------------------------
-- Python value helpers
------------------------------------------------------------------------------------------------------
local N=canon.number
local isf=canon.is_float
local function none(v) return v==nil or v==NULL end
local function isnum(v) return type(v)=='number' or isf(v) end            -- type(v) in (int,float)
local function is_int(v) return type(v)=='number' and v%1==0 end            -- type(v) is int
local function finite(v)                                                     -- reliability.finite
  local x=N(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge and x>=0
end
local function stamp(v)                                                      -- RouteHistory.stamp
  local x=N(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge and x>=0 and x<=253370764799
end
M.finite,M.stamp=finite,stamp
local function F(x) return canon.float(x) end
-- A value Python holds as a float (time.time(), round(x,1)): plain numbers are boxed, boxes and None kept.
local function pyf(v) if type(v)=='number' then return F(v) end;return v end
M.pyf=pyf
local function add(a,b) local r=N(a)+N(b);if isf(a) or isf(b) then return F(r) end;return r end
local function sub(a,b) local r=N(a)-N(b);if isf(a) or isf(b) then return F(r) end;return r end
local function pymin(a,b) if N(b)<N(a) then return b end;return a end
local function pymax(a,b) if N(b)>N(a) then return b end;return a end
M.add,M.sub,M.pymin,M.pymax=add,sub,pymin,pymax
-- Python ==: numbers by value (1 == 1.0), None/missing alike, everything else by identity/value
local function eq(a,b)
  if isnum(a) and isnum(b) then return N(a)==N(b) end
  if none(a) and none(b) then return true end
  return a==b
end
M.eq=eq
local function truthy(v)
  if none(v) or v==false then return false end
  if isnum(v) then return N(v)~=0 end
  if type(v)=='string' then return v~='' end
  if type(v)=='table' then return next(v)~=nil end
  return true
end
M.truthy=truthy
local function is_dict(v) return canon.is_object(v) end
local function is_list(v) return canon.is_array(v) end
local function is_profile(v)
  return type(v)=='string' and (string.find(v,'^openvpn:[0-9]+_[0-9]+$')~=nil or string.find(v,'^wireguard:peer_[0-9]+$')~=nil)
end
M.is_profile=is_profile
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function sorted_keys(t) local keys={};for k in pairs(t) do keys[#keys+1]=k end;table.sort(keys);return keys end
local function fail(code) error(code,0) end
local function month_of(t) return os.date('%Y-%m',math.floor(N(t))) end
local function next_month_start(t)
  local d=os.date('*t',math.floor(N(t)))
  local year,month=d.year,d.month+1
  if month==13 then year,month=year+1,1 end
  return os.time({year=year,month=month,day=1,hour=0,min=0,sec=0})
end
local function copy(v)  -- copy.deepcopy of canon values (boxes are immutable and shared)
  if type(v)~='table' or v==NULL or isf(v) then return v end
  local out={};for k,item in pairs(v) do out[k]=copy(item) end
  return setmetatable(out,getmetatable(v))
end
M.copy=copy

------------------------------------------------------------------------------------------------------
-- route_history.RouteHistory
------------------------------------------------------------------------------------------------------
local Routes={};Routes.__index=Routes
M.Routes=Routes

local function route_default() return canon.object({segments=canon.array(),last=NULL,since=NULL,dropped=0}) end
function M.routes(data)
  local d=(data~=nil and data~=NULL and truthy(data)) and copy(data) or route_default()
  if not is_dict(d) or count(d)~=4 or d.segments==nil or d.last==nil or d.since==nil or d.dropped==nil
     or not is_list(d.segments) or #d.segments>4096 or not is_int(d.dropped) or d.dropped<0 then fail('STATISTICS-ROUTE-SCHEMA') end
  local previous=nil
  for _,row in ipairs(d.segments) do
    if not is_dict(row) or count(row)~=3 or row.start==nil or row['end']==nil or not ROUTE_KINDS[row.kind]
       or not stamp(row.start) or not stamp(row['end']) or N(row['end'])<N(row.start) or (previous~=nil and N(row.start)<previous) then
      fail('STATISTICS-ROUTE-SEGMENT')
    end
    previous=N(row['end'])
  end
  local last=d.last
  if last~=NULL and (not is_dict(last) or count(last)~=2 or not stamp(last.time) or not ROUTE_KINDS[last.kind]) then fail('STATISTICS-ROUTE-LAST') end
  if d.since~=NULL and not stamp(d.since) then fail('STATISTICS-ROUTE-SINCE') end
  return setmetatable({data=d},Routes)
end

function Routes:observe(kind,now,max_gap)
  max_gap=max_gap or 90
  if not ROUTE_KINDS[kind] or not stamp(now) then fail('STATISTICS-ROUTE-OBSERVATION') end
  local d=self.data;local old=d.last
  if old~=NULL and N(now)<=N(old.time) then return false end
  local changed=old==NULL or old.kind~=kind
  if d.since==NULL then d.since=now end
  local floor=sub(now,M.DAY)
  if old~=NULL then
    local interval_kind=N(now)-N(old.time)<=max_gap and old.kind or 'unknown'
    local rows=d.segments;local begin=pymax(old.time,floor)
    local tail=rows[#rows]
    if tail and tail.kind==interval_kind and eq(tail['end'],begin) then tail['end']=now
    else rows[#rows+1]=canon.object({start=begin,['end']=now,kind=interval_kind}) end
  end
  d.last=canon.object({time=now,kind=kind})
  local kept=canon.array()
  for _,row in ipairs(d.segments) do
    if N(row['end'])>N(floor) then kept[#kept+1]=canon.object({start=pymax(row.start,floor),['end']=row['end'],kind=row.kind}) end
  end
  if #kept>4096 then
    d.dropped=d.dropped+(#kept-4096)
    local cut=canon.array();for i=#kept-4095,#kept do cut[#cut+1]=kept[i] end;kept=cut
  end
  d.segments=kept
  return changed
end
function Routes:export() return copy(self.data) end

------------------------------------------------------------------------------------------------------
-- channel_path.observed_pair_role and route_history.observed_route
------------------------------------------------------------------------------------------------------
local PHASES={BLOCKED=true,ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true}
function M.observed_pair_role(native,now)
  if not is_dict(native) or PHASES[native.state] or truthy(native.blockers) then return nil end
  local path=require('monitor_status').cached_projection(native.channel_path,N(now))
  if path.confirmed~=true or not eq(path.source_profile_id,native.source) or not eq(path.target_profile_id,native.target) then return nil end
  for _,role in ipairs({'source','target'}) do
    if eq(path.active_profile_id,native[role]) then return role end
  end
  return nil
end

local OFF={STOPPED=true,DISABLED=true,EXPIRED=true,['SERVICE-STOPPED']=true}
local SWITCHING={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true}
local function profile_row(status,identifier)
  if none(identifier) then return nil end
  local rows=status.profiles
  if type(rows)~='table' or rows==NULL then return nil end
  for _,row in ipairs(rows) do if type(row)=='table' and row~=NULL and eq(row.id,identifier) then return row end end
  return nil
end
local function fresh_row(row,now) return row~=nil and stamp(row.time) and 0<=now-N(row.time) and now-N(row.time)<=90 end
function M.observed_route(status,now)
  now=N(now)
  local native=type(status)=='table' and status~=NULL and status.native_failover or nil
  if not is_dict(native) or not stamp(native.time) or not (0<=now-N(native.time) and now-N(native.time)<=30) then return 'unknown' end
  local state=native.state
  if OFF[state] then return 'off' end
  if SWITCHING[state] then return 'switching' end
  local function failing(identifier)
    local p=truthy(identifier) and profile_row(status,identifier) or nil
    if not p or not fresh_row(p,now) then return false end
    return not (none(p.code) and p.dns_ok==true and (N(p.https_success) or 0)>=2)
  end
  if truthy(native.source) and truthy(native.target) and not eq(native.source,native.target) and failing(native.source) and failing(native.target) then return 'down' end
  local required=native.mode=='continuous-pair' or native.proof_scope=='router-probed-ipv4' or native.transition_metadata_present==true
  local role
  if required then role=M.observed_pair_role(native,now)
  elseif state=='COMMITTED' or state=='DEGRADED-ON-RESERVE' or state=='STOPPED-ON-RESERVE' then role='target'
  elseif state=='OBSERVING' and native.certified==true then role='source' end
  if role then
    if fresh_row(profile_row(status,native[role]),now) then return role end
    return 'unknown'
  end
  if state=='BLOCKED' or state=='FAILED' then return 'blocked' end
  return 'unknown'
end

------------------------------------------------------------------------------------------------------
-- reliability.active_controller
------------------------------------------------------------------------------------------------------
local CONTROLLER_STATES={OBSERVING=true,COMMITTED=true,['DEGRADED-ON-RESERVE']=true,ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true,BLOCKED=true}
function M.active_controller(native,state,intent,now)
  if not is_dict(native) or not is_dict(state) or not is_dict(intent) then return false end
  local stamp_=native.time
  return state.phase=='RUNNING' and intent.mode=='on' and type(state.id)=='string' and state.id==intent.id
    and eq(state.revision,intent.revision) and native.mode=='continuous-pair' and CONTROLLER_STATES[native.state]==true
    and finite(stamp_) and finite(now) and 0<=N(now)-N(stamp_) and N(now)-N(stamp_)<90
end

------------------------------------------------------------------------------------------------------
-- reliability.Reliability
------------------------------------------------------------------------------------------------------
local Reliability={};Reliability.__index=Reliability
M.Reliability=Reliability

local function default_data()
  return canon.object({schema=1,since=NULL,sequence=0,totals=canon.object(),months=canon.object(),events=canon.array(),
    profiles=canon.object(),details_dropped=0})
end
local FIELDS={schema=true,since=true,sequence=true,totals=true,months=true,events=true,profiles=true,details_dropped=true,controller=true,route_history=true}
local EVENT_FIELDS={sequence=true,time=true,profile=true,kind=true,code=true,observed_duration_seconds=true,role=true,selected=true}
local LEGACY_STATES={OBSERVING=true,COMMITTED=true,ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true,BLOCKED=true,STOPPED=true,
  ['STOPPED-ON-RESERVE']=true,['DEGRADED-ON-RESERVE']=true,DISABLED=true,EXPIRED=true,['SERVICE-STOPPED']=true}
local PROFILE_STATES={up=true,down=true,off=true,unknown=true}

-- Reliability(data, detail_days): raises the Python codes (STATISTICS-*) on an invalid structure.
function M.new(data,detail_days)
  detail_days=detail_days==nil and 7 or detail_days
  if not is_int(detail_days) or detail_days<1 or detail_days>30 then fail('STATISTICS-RETENTION') end  -- retention.MAX_DAYS
  local d=(data~=nil and data~=NULL and truthy(data)) and copy(data) or default_data()
  if not is_dict(d) or not eq(d.schema,1) or type(d.schema)=='boolean' or not is_int(d.sequence) or d.sequence<0 or d.sequence>=2^53
     or not is_dict(d.totals) or not is_dict(d.months) or count(d.months)>1200
     or not is_list(d.events) or #d.events>M.MAX_EVENTS or not is_dict(d.profiles) or count(d.profiles)>400 then
    fail('STATISTICS-SCHEMA')
  end
  for k in pairs(d) do if not FIELDS[k] then fail('STATISTICS-FIELDS') end end
  if d.since~=nil and d.since~=NULL and not finite(d.since) then fail('STATISTICS-SINCE') end
  if not is_int(d.details_dropped) or d.details_dropped<0 then fail('STATISTICS-RETENTION') end
  for month in pairs(d.months) do
    if type(month)~='string' or not string.find(month,'^%d%d%d%d%-%d%d$') or tonumber(string.sub(month,6))<1 or tonumber(string.sub(month,6))>12 then fail('STATISTICS-MONTH') end
  end
  local last=0
  for _,row in ipairs(d.events) do
    local bad=not is_dict(row)
    if not bad then for k in pairs(row) do if not EVENT_FIELDS[k] then bad=true end end end
    if bad or not is_int(row.sequence) or not (last<row.sequence and row.sequence<=d.sequence) or not finite(row.time)
       or not is_profile(row.profile) or (row.kind~='FAILURE' and row.kind~='RECOVERY' and row.kind~='DISABLED')
       or (row.code~=nil and not BAD[row.code])
       or (row.observed_duration_seconds~=nil and not finite(row.observed_duration_seconds))
       or (row.role~=nil and row.role~='source' and row.role~='target' and row.role~='unknown')
       or (row.selected~=nil and row.selected~='source' and row.selected~='target' and row.selected~='off' and row.selected~='unknown') then
      fail('STATISTICS-EVENT')
    end
    last=row.sequence
  end
  for key,row in pairs(d.profiles) do
    if is_dict(row) and not PROFILE_STATES[row.state] and (none(row.state) or LEGACY_STATES[row.state])
       and eq(row.opened,row.time) and row.opened_observed==true then
      for _,e in ipairs(d.events) do
        if is_dict(e) and e.profile==key and eq(e.time,row.time) and e.kind=='FAILURE' and BAD[e.code] and e.role~=nil then row.state='down';break end
      end
    end
    local bad=not is_profile(key) or not is_dict(row)
    if not bad then for k in pairs(row) do if k~='time' and k~='state' and k~='opened' and k~='opened_observed' then bad=true end end end
    if bad or not finite(row.time) or not PROFILE_STATES[row.state] or (not none(row.opened) and not finite(row.opened)) then fail('STATISTICS-PROFILE') end
  end
  local old=d.controller
  if old~=nil and old~=NULL and (not is_dict(old) or count(old)~=2 or not finite(old.time) or type(old.active)~='boolean') then fail('STATISTICS-CONTROLLER') end
  local all={d.totals};for _,v in pairs(d.months) do all[#all+1]=v end
  for _,totals in ipairs(all) do
    if not is_dict(totals) then fail('STATISTICS-COUNTERS') end
    for k,v in pairs(totals) do if not METRIC_SET[k] or not finite(v) then fail('STATISTICS-COUNTERS') end end
  end
  local self=setmetatable({data=d,detail_days=detail_days,critical=false},Reliability)
  self.routes=M.routes(d.route_history)
  return self
end

function Reliability:add(key,value,now)
  local month=month_of(now)
  local months=self.data.months
  if months[month]==nil then months[month]=canon.object() end
  for _,totals in ipairs({self.data.totals,months[month]}) do totals[key]=add(totals[key] or 0,value) end
end

function Reliability:seconds(key,start,finish)
  while N(start)<N(finish) do
    local boundary=F(next_month_start(start))
    local stop=pymin(finish,boundary)
    self:add(key,sub(stop,start),start);start=stop
  end
end

function Reliability:event(profile,kind,now,code,duration)
  local d=self.data;d.sequence=d.sequence+1
  local item=canon.object({sequence=d.sequence,time=now,profile=profile,kind=kind})
  if BAD[code] then item.code=code end
  if duration~=nil and finite(duration) then item.observed_duration_seconds=duration end
  d.events[#d.events+1]=item;self.critical=true
end

local function selected_legacy(state,native)
  if state=='COMMITTED' or state=='DEGRADED-ON-RESERVE' or state=='STOPPED-ON-RESERVE' then return 'target' end
  if state=='OBSERVING' and native.certified==true then return 'source' end
  if OFF[state] then return 'off' end
  return 'unknown'
end
function Reliability:event_context(key,now,native,pair)
  local event=self.data.events[#self.data.events]
  event.role='unknown';event.selected='unknown'
  local function pget(k) if is_dict(pair) then return pair[k] end;return nil end
  if is_dict(pair) and not eq(pair.source,pair.target) then
    event.role=key==pair.source and 'source' or (key==pair.target and 'target' or 'unknown')
  end
  if is_dict(native) and finite(native.time) and -5<=N(now)-N(native.time) and N(now)-N(native.time)<=30
     and (pair==nil or (eq(native.source,pget('source')) and eq(native.target,pget('target')))) then
    if pair==nil and not eq(native.source,native.target) then
      event.role=key==native.source and 'source' or (key==native.target and 'target' or 'unknown')
    end
    local state=native.state
    local required=native.mode=='continuous-pair' or native.proof_scope=='router-probed-ipv4' or native.transition_metadata_present==true
    if required then
      event.selected=OFF[state] and 'off' or (M.observed_pair_role(native,now) or 'unknown')
    else event.selected=selected_legacy(state,native) end
  end
end

-- Encoded length of one event (canon text; Python's json.dumps of the same dict has the same length), and its
-- length with json.dumps' default separators (one more character per ':' and per ',' between items).
local event_length=setmetatable({},{__mode='k'})
local event_spaced=setmetatable({},{__mode='k'})
local function length_of(row)
  local n=event_length[row]
  if not n then
    n=#canon.encode(row);event_length[row]=n
    local k=count(row);event_spaced[row]=n+(k>0 and 2*k-1 or 0)
  end
  return n
end

-- Length of json.dumps(value, ensure_ascii=True) with the default separators ', ' and ': ' (sort order does not
-- change a length): the compact canonical text plus one character per separator between items.
local function separators(value)
  if type(value)~='table' or value==NULL or isf(value) then return 0 end
  local n,extra=0,0
  if canon.is_array(value) then
    for _,item in ipairs(value) do n=n+1;extra=extra+separators(item) end
    return extra+(n>0 and n-1 or 0)
  end
  for _,item in pairs(value) do n=n+1;extra=extra+separators(item) end
  return extra+(n>0 and 2*n-1 or 0)
end
function M.python_size(value) return #canon.encode(value)+separators(value) end
-- Size of a dict from the sizes of its values: {"k": v, ...}
function M.dict_size(sizes)
  local total,n=2,0
  for key,size in pairs(sizes) do total=total+#canon.quote(key)+2+size;n=n+1 end
  return total+(n>1 and 2*(n-1) or 0)
end

-- prune runs after every observation (twice per pass with two channels). CPU: the event list is only rebuilt when
-- something leaves it, and the encoded size of the kept list is carried along (self.size: the list it describes,
-- how many of its items are counted, their total) instead of encoding up to 1 MB every time; the result is the
-- list Python's comprehension and json.dumps loop produce.
function Reliability:prune(now)
  local d=self.data
  local t=N(now)
  local horizon=t-self.detail_days*86400
  local kept=d.events
  local n=#kept
  local size=self.size
  local function count(list)
    if not size or size.list~=list or size.count>#list then size={list=list,count=0,total=1,low=math.huge,high=-math.huge} end
    -- '[' and ']' plus one ',' between items: 2+(n-1) = 1+n, plus the item texts; and the time range
    for i=size.count+1,#list do
      local row=list[i];local s=N(row.time)
      size.total=size.total+length_of(row)+1
      if s<size.low then size.low=s end
      if s>size.high then size.high=s end
    end
    size.count=#list
  end
  count(kept)
  if n>0 and (size.low<horizon or size.high>t) then  -- something leaves the window: rebuild (Python's comprehension)
    local fresh=canon.array()
    for _,row in ipairs(kept) do local s=N(row.time);if horizon<=s and s<=t then fresh[#fresh+1]=row end end
    kept=fresh;n=#kept;size=nil;count(kept)
  end
  local overflow=math.max(0,n-M.MAX_EVENTS)
  local total=size.total
  for i=1,overflow do total=total-length_of(kept[i])-1 end
  while n-overflow>1 and total>M.DETAIL_BYTES do
    local step=math.max(1,math.floor((n-overflow)/10))
    for i=overflow+1,overflow+step do total=total-length_of(kept[i])-1 end
    overflow=overflow+step
  end
  if overflow>0 then
    local cut=canon.array();for i=overflow+1,n do cut[#cut+1]=kept[i] end;kept=cut
    d.details_dropped=d.details_dropped+overflow
    size=nil;count(kept)
  end
  self.size=size
  d.events=kept
  local months=sorted_keys(d.months)
  for i=1,#months-1200 do d.months[months[i]]=nil end
  local profiles=canon.object()
  for key,value in pairs(d.profiles) do if N(now)-N(value.time)<=self.detail_days*86400 then profiles[key]=value end end
  d.profiles=profiles
end

-- observe(row, max_gap, native, pair): one probe result {id,time,code,administrative_state,dns_ok,https_success}.
function Reliability:observe(row,max_gap,native,pair)
  max_gap=max_gap or 90
  local key,now=row.id,row.time
  if type(key)~='string' or not is_profile(key) or not finite(now) or N(now)>253370764799 then return false end
  local d=self.data;local previous=d.profiles[key]
  if previous~=nil and N(now)<=N(previous.time) then return false end
  if d.since==NULL or d.since==nil then d.since=now end
  local code=row.code;if code==NULL then code=nil end
  local state
  if row.administrative_state=='disabled' or code=='PROFILE-INACTIVE' then state='off'
  elseif BAD[code] then state='down'
  elseif code==nil and row.dns_ok==true and (N(row.https_success) or 0)>=2 then state='up'
  else state='unknown' end
  if state~='off' then self:add('checks',1,now) end
  if state=='down' then self:add('failed_checks',1,now) end
  local contiguous=previous~=nil and 0<N(now)-N(previous.time) and N(now)-N(previous.time)<=max_gap
  if contiguous and (previous.state=='up' or previous.state=='down') then
    self:seconds('observed_'..previous.state..'_seconds',previous.time,now)
  elseif previous~=nil and (not contiguous or previous.state=='unknown') then self:add('unknown_intervals',1,now) end
  local opened=previous and previous.opened or nil
  if opened==NULL then opened=nil end
  local observed=previous~=nil and truthy(previous.opened_observed) and contiguous and state~='unknown'
  if state=='off' and opened~=nil then
    self:event(key,'DISABLED',now);opened=nil;observed=false
  elseif state=='down' and opened==nil then
    self:add('outages',1,now);self:event(key,'FAILURE',now,code);opened=now;observed=true
    self:event_context(key,now,native,pair)
  elseif state=='up' and opened~=nil then
    self:add('recoveries',1,now)
    self:event(key,'RECOVERY',now,nil,observed and sub(now,opened) or nil);opened=nil
    self:event_context(key,now,native,pair)
  end
  d.profiles[key]=canon.object({time=now,state=state,opened=opened==nil and NULL or opened,opened_observed=observed and true or false})
  if count(d.profiles)>400 then
    local oldest=nil
    for _,k in ipairs(sorted_keys(d.profiles)) do
      if oldest==nil or N(d.profiles[k].time)<N(d.profiles[oldest].time) then oldest=k end
    end
    d.profiles[oldest]=nil
  end
  self:prune(now)
  return self.critical
end

function Reliability:controller(active,now,max_gap)
  max_gap=max_gap or 90
  if not finite(now) then return end
  local old=self.data.controller
  if old~=nil and old~=NULL and N(now)<=N(old.time) then return end
  if old~=nil and old~=NULL and old.active and active and N(now)-N(old.time)<=max_gap then
    self:seconds('auto_observed_seconds',old.time,now)
  end
  self.data.controller=canon.object({time=now,active=active==true})
end

-- export(): a deep copy like Python's. export_view(): the same value without copying (CPU: the size checks and
-- the checkpoint encode it at once and never keep it).
function Reliability:export()
  local data=copy(self.data);data.route_history=self.routes:export();return data
end
function Reliability:export_view()
  local data=canon.object();for k,v in pairs(self.data) do data[k]=v end
  data.route_history=self.routes.data;return data
end
-- python_size(): len(json.dumps(self.export())) with the default separators; the event list (up to 1 MB) is
-- measured from the per-event lengths, carried along while the list only grows.
function Reliability:python_size()
  local d=self.data
  local sizes={}
  for key,value in pairs(d) do if key~='events' and key~='route_history' then sizes[key]=M.python_size(value) end end
  sizes.route_history=M.python_size(self.routes.data)
  local events=d.events
  local spaced=self.spaced
  if not spaced or spaced.list~=events or spaced.count>#events then spaced={list=events,count=0,total=0} end
  for i=spaced.count+1,#events do length_of(events[i]);spaced.total=spaced.total+event_spaced[events[i]] end
  spaced.count=#events;self.spaced=spaced
  sizes.events=2+spaced.total+(#events>1 and 2*(#events-1) or 0)
  return M.dict_size(sizes)
end

function Reliability:public()
  local d=self.data
  local weekly=NULL
  if not truthy(d.details_dropped) then
    local outages,recoveries=0,0
    for _,row in ipairs(d.events) do
      if row.kind=='FAILURE' then outages=outages+1 elseif row.kind=='RECOVERY' then recoveries=recoveries+1 end
    end
    weekly=canon.object({outages=outages,recoveries=recoveries})
  end
  local events=canon.array()
  for i=math.max(1,#d.events-99),#d.events do events[#events+1]=copy(d.events[i]) end
  local latest=0
  for _,p in pairs(d.profiles) do if N(p.time)>latest then latest=N(p.time) end end
  local failures=canon.array()
  for _,e in ipairs(d.events) do
    if e.kind=='FAILURE' and N(e.time)>=latest-86400 then failures[#failures+1]=canon.array({e.time,e.role or 'unknown',e.selected or 'unknown'}) end
  end
  return canon.object({since=d.since==nil and NULL or d.since,totals=copy(d.totals),weekly=weekly,months=copy(d.months),events=events,
    sequence=d.sequence,detail_days=self.detail_days,details_dropped=d.details_dropped,route_history=self.routes:export(),
    failure_history=canon.object({events=failures,since=d.since==nil and NULL or d.since,details_dropped=d.details_dropped}),
    scope='observed VPN checks and outage edges; not LAN availability',checkpointed=true})
end

return M
