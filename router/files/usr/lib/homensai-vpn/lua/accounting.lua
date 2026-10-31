-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- accounting.lua: agent.Accounting (interface counters by month/day, probe quality buckets, channel activity and,
-- since Lua plan item 6, the reliability model of reliability.lua), the checkpoint.json envelope
-- {data:{version,saved,accounting},sha256} with checkpoint_schema.validate, and stats_mode.py (Work/Diagnostics
-- from /etc/config/homensai_vpn). Lua 5.1, no router modules: time and files come from the injected runner
-- (wall(), read_file(), write_atomic(), file_size(), config_text(), config_mtime()).
-- Day/month boundaries use the process local time (os.date/os.time), as Python used datetime.fromtimestamp
-- and time.mktime under TZ=CET-1CEST,M3.5.0,M10.5.0/3 (monitor_io sets TZ the same way).
--
-- Values keep their Python types (item 6): ints are plain Lua numbers, Python floats are canon.float boxes; every
-- time stamp is a float (time.time()), traffic shares and seconds become floats as soon as Python adds a weighted
-- share to them, counters stay ints. The canonical JSON of export() is therefore the text of
-- json.dumps(Accounting.export(), sort_keys=True) for the same inputs (tests/test_lua_history.py). The size
-- budgets (3 MB retention, 500 KB page) measure json.dumps' default separators (', ' and ': ') like Python.
-- Not byte-identical: agent.atomic_json writes dict insertion order, canon writes sorted keys (the checksum is
-- over the sorted text in both lines, so either line verifies the other's file).
local canon=require('canon')
local reliability=require('reliability')

local M={}
M.SAFE=function(s) return type(s)=='string' and #s>=1 and #s<=96 and string.find(s,'^[A-Za-z0-9_.:-]+$')~=nil end
M.WORK_SAMPLE_SECONDS=6*3600
M.WORK_CHECKPOINT_SECONDS=86400
M.STATS_HOURS={24,72,168,336}
M.STATS_DEFAULT_HOURS=24

local NULL=canon.null
local N=canon.number
local isf=canon.is_float
local function is_number(v) return type(v)=='number' and v==v and v~=math.huge and v~=-math.huge end
local function is_int(v) return is_number(v) and v%1==0 end
M.is_number,M.is_int=is_number,is_int
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function sorted_keys(t) local keys={};for k in pairs(t) do keys[#keys+1]=k end;table.sort(keys);return keys end
local function day_of(ts) return os.date('%Y-%m-%d',math.floor(N(ts))) end
local function month_of(ts) return os.date('%Y-%m',math.floor(N(ts))) end
-- Midnight after the day containing ts (time.mktime of tomorrow 00:00 local); DST handled by mktime (isdst=-1).
local function next_midnight(ts)
  local t=os.date('*t',math.floor(N(ts)))
  return os.time({year=t.year,month=t.month,day=t.day+1,hour=0,min=0,sec=0})
end
local function next_month_start(ts)
  local t=os.date('*t',math.floor(N(ts)))
  local year,month=t.year,t.month+1
  if month==13 then year,month=year+1,1 end
  return os.time({year=year,month=month,day=1,hour=0,min=0,sec=0})
end
M.next_midnight,M.next_month_start,M.day_of,M.month_of=next_midnight,next_month_start,day_of,month_of

local F,pyf,add=canon.float,reliability.pyf,reliability.add
local pymin,pymax=reliability.pymin,reliability.pymax
local function none(v) return v==nil or v==NULL end
local function obj(t) return canon.object(t or {}) end
local function ensure(t,key,default) if t[key]==nil then t[key]=default end;return t[key] end
local function dict_or_empty(v) if type(v)=='table' and v~=NULL and not isf(v) then return obj(v) end;return obj() end

-- Length of json.dumps(value, ensure_ascii=True) with the default separators: the compact canonical text plus
-- one space after every ',' and ':' between items (sort order does not change a length).
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

------------------------------------------------------------------------------------------------------
-- Accounting
------------------------------------------------------------------------------------------------------
local Accounting={};Accounting.__index=Accounting
M.Accounting=Accounting

-- new(data, nested): agent.Accounting(data). Raises the reliability codes on an invalid reliability model,
-- as the Python constructor does (restore() then tries the backup copy).
function M.new(data,nested)
  if none(data) then data=nil end
  local self=setmetatable({},Accounting)
  self.months=dict_or_empty(data and data.months)
  self.days=dict_or_empty(data and data.days)
  self.retention=dict_or_empty(data and data.retention)
  self.quality=dict_or_empty(data and data.quality)
  self.activity=dict_or_empty(data and data.activity)
  self.gaps=data and N(data.gaps) and math.floor(N(data.gaps)) or 0  -- int(data.get('gaps', 0))
  self.previous={}  -- never carry kernel counter baselines across a restart
  self.activity_previous={}
  self.reliability=reliability.new(data and data.reliability or nil,7)
  self.wan=nil
  local wan=data and data.wan
  if not nested and type(wan)=='table' and wan~=NULL and not canon.is_array(wan) and not isf(wan) then self.wan=M.new(wan,true) end
  return self
end
function Accounting:detail_days() return self.reliability.detail_days end

local function new_day_row() return obj({rx=0,tx=0,seconds=0,boundary_estimated=false,gaps=0,observed=false}) end

-- sample(device, ifindex, rx, tx, now, max_gap): rx/tx are ints (sysfs), now is a float time stamp.
function Accounting:sample(device,ifindex,rx,tx,now,max_gap)
  max_gap=max_gap or 90
  if not M.SAFE(device) or math.min(rx,tx)<0 then error('invalid interface counter') end
  local t=N(now)
  local previous=self.previous[device]
  self.previous[device]={ifindex,rx,tx,t}
  if not previous then return end
  local old_index,old_rx,old_tx,old_time=previous[1],previous[2],previous[3],previous[4]
  if t<=old_time then
    if t==old_time and rx==old_rx and tx==old_tx then self.previous[device]=previous;return end
    self.previous[device]=nil;self.gaps=self.gaps+1;self:note_gap(old_time,t);return
  end
  if old_index~=ifindex or rx<old_rx or tx<old_tx or t-old_time>max_gap then
    self.gaps=self.gaps+1;self:note_gap(old_time,t);return
  end
  local cursor=old_time
  while cursor<t do
    local boundary=next_month_start(cursor)
    local finish=math.min(t,boundary)
    local weight=(finish-cursor)/(t-old_time)
    local record=ensure(self.months,month_of(cursor),obj({rx=0,tx=0,seconds=0,boundary_estimated=false}))
    record.rx=F(N(record.rx)+(rx-old_rx)*weight);record.tx=F(N(record.tx)+(tx-old_tx)*weight)
    record.seconds=F(N(record.seconds)+(finish-cursor))
    if boundary<t then record.boundary_estimated=true end
    cursor=finish
  end
  cursor=old_time
  while cursor<t do
    local boundary=next_midnight(cursor)
    local finish=math.min(t,boundary)
    local weight=(finish-cursor)/(t-old_time)
    local record=ensure(self.days,day_of(cursor),new_day_row())
    record.observed=true
    record.first_sample=record.first_sample==nil and F(cursor) or pymin(record.first_sample,F(cursor))
    record.last_sample=record.last_sample==nil and F(finish) or pymax(record.last_sample,F(finish))
    record.rx=F(N(record.rx)+(rx-old_rx)*weight);record.tx=F(N(record.tx)+(tx-old_tx)*weight)
    record.seconds=F(N(record.seconds)+(finish-cursor))
    if boundary<t then record.boundary_estimated=true end
    cursor=finish
  end
  local days=sorted_keys(self.days)
  for i=1,#days-400 do self.days[days[i]]=nil end
  local current_month=month_of(t)
  local others={}
  for _,key in ipairs(sorted_keys(self.months)) do if key~=current_month then others[#others+1]=key end end
  local keep=self.months[current_month]~=nil and 17 or 18
  for i=1,#others-keep do self.months[others[i]]=nil end
end

function Accounting:note_gap(start,finish)
  local cursor=math.min(N(start),N(finish));local last=math.max(N(start),N(finish))
  cursor=math.max(cursor,last-400*86400)
  while true do
    local row=ensure(self.days,day_of(cursor),new_day_row())
    row.gaps=add(row.gaps or 0,1)
    local boundary=next_midnight(cursor)
    if boundary>=last then break end
    cursor=boundary
  end
  local days=sorted_keys(self.days)
  for i=1,#days-400 do self.days[days[i]]=nil end
end

local DOWN_CODES={['VPN-001']=true,['VPN-003']=true,['DNS-001']=true}
local function empty_activity_day() return obj({up=0,down=0,idle=0,unknown=0,connections=0,failures=0}) end
local function truthy_text(v) return v~=nil and v~=NULL and v~=false and v~='' end

function Accounting:track_activity(rows,now,max_gap)
  max_gap=max_gap or 90
  local t=N(now);local stamp=F(t)
  local window=self:detail_days()*86400
  for _,item in ipairs(rows) do
    local key=item.id
    local profile=ensure(self.activity,key,obj({days=obj(),last_seen=stamp}))
    profile.name=(item.name==nil) and key or item.name;profile.protocol=(item.protocol==nil) and 'unknown' or item.protocol
    local code=item.code;if code==NULL then code=nil end
    local active=truthy_text(item.interface)
    local state=(not active) and 'idle' or (not truthy_text(code)) and 'up' or DOWN_CODES[code] and 'down' or 'unknown'
    local previous=self.activity_previous[key]
    local skip=false
    if previous and t<=previous[1] then
      if t<previous[1] then self.gaps=self.gaps+1 end
      skip=true  -- never move a baseline backwards or double-count time
    end
    if not skip then
      local beginning=previous and previous[1] or (N(profile.last_seen) or t)
      local interval_state=(previous and t-beginning>0 and t-beginning<=max_gap) and previous[2] or 'unknown'
      local cursor=math.max(beginning,t-window)
      while cursor<t do
        local finish=math.min(t,next_midnight(cursor))
        local bucket=ensure(profile.days,day_of(cursor),empty_activity_day())
        bucket[interval_state]=F(N(bucket[interval_state] or 0)+(finish-cursor))
        cursor=finish
      end
      local bucket=ensure(profile.days,day_of(t),empty_activity_day())
      if previous and t-previous[1]>0 and t-previous[1]<=max_gap then
        if active and not previous[3] then bucket.connections=add(bucket.connections,1) end
        if state=='down' and previous[2]~='down' then bucket.failures=add(bucket.failures,1) end
      end
      self.activity_previous[key]={t,state,active}
      profile.last_seen=stamp
      local cutoff=day_of(t-window)
      local kept=obj()
      for day,row in pairs(profile.days) do if day>=cutoff then kept[day]=row end end
      profile.days=kept
    end
  end
  local kept=obj()
  for key,value in pairs(self.activity) do if (N(value.last_seen) or 0)>=t-window then kept[key]=value end end
  self.activity=kept
  if count(self.activity)>400 then
    local keys=sorted_keys(self.activity)
    table.sort(keys,function(a,b) return (N(self.activity[a].last_seen) or 0)>(N(self.activity[b].last_seen) or 0) end)
    local trimmed=obj()
    for i=1,400 do trimmed[keys[i]]=self.activity[keys[i]] end
    self.activity=trimmed
  end
end

local UNKNOWN_CODES={['CHECK-001']=true,['SYSTEM-001']=true,['ROUTE-001']=true,['PROFILE-INACTIVE']=true,['CHECK-LIMIT']=true,
  ['VENDOR-IDENTITY-CHANGED']=true,['VENDOR-IDENTITY-UNKNOWN']=true}
local function last_time(value)
  local last=value.last
  if type(last)~='table' or last==NULL or isf(last) then return 0 end
  return N(last.time) or 0
end

-- observe(result, max_gap, native, pair): reliability first, then the hourly quality bucket (agent.Accounting.observe).
function Accounting:observe(result,max_gap,native,pair)
  self.reliability:observe(result,max_gap,native,pair)
  local identifier,stamp=result.id,result.time
  local window=self:detail_days()*86400
  local kept=obj()
  for key,value in pairs(self.quality) do if last_time(value)>=N(stamp)-window then kept[key]=value end end
  self.quality=kept
  local bucket=tostring(math.floor(N(stamp)/3600))
  local profile=ensure(self.quality,identifier,obj({buckets=obj(),last=NULL}))
  local code=result.code;if code==nil then code=NULL end
  local rtt=result.rtt_ms;if rtt==nil then rtt=NULL end
  profile.last=obj({time=stamp==nil and NULL or stamp,code=code,rtt_ms=rtt})
  local row=ensure(profile.buckets,bucket,obj({n=0,success=0,rtt_sum=0,unknown=0}))
  if code~=NULL and UNKNOWN_CODES[code] then row.unknown=add(row.unknown,1)
  else
    row.n=add(row.n,1)
    if code==NULL then
      row.success=add(row.success,1)
      local value=rtt;if value==NULL or value==false or N(value)==0 then value=0 end  -- result.get('rtt_ms') or 0
      row.rtt_sum=add(row.rtt_sum,value)
    end
  end
  for key in pairs(profile.buckets) do if tonumber(key)*3600<N(stamp)-window then profile.buckets[key]=nil end end
  if count(self.quality)>400 then
    local keys=sorted_keys(self.quality)
    table.sort(keys,function(a,b) return last_time(self.quality[a])>last_time(self.quality[b]) end)
    local trimmed=obj()
    for i=1,400 do trimmed[keys[i]]=self.quality[keys[i]] end
    self.quality=trimmed
  end
end

function Accounting:export()
  return obj({months=self.months,days=self.days,gaps=self.gaps,quality=self.quality,activity=self.activity,
    retention=self.retention,reliability=self.reliability:export(),wan=self.wan and self.wan:export() or NULL})
end
-- The same value without copying the reliability model (encoded at once by the checkpoint and the size checks).
function Accounting:export_view()
  return obj({months=self.months,days=self.days,gaps=self.gaps,quality=self.quality,activity=self.activity,
    retention=self.retention,reliability=self.reliability:export_view(),wan=self.wan and self.wan:export_view() or NULL})
end

-- Python's len(json.dumps(export)) by parts (CPU: one encode of each small part, the reliability event list from
-- its cached per-event lengths); dict_size(sizes) is the whole length.
function Accounting:part_sizes()
  local P=M.python_size
  return {months=P(self.months),days=P(self.days),gaps=P(self.gaps),quality=P(self.quality),activity=P(self.activity),
    retention=P(self.retention),reliability=self.reliability:python_size(),wan=self.wan and self.wan:python_size() or 4}
end
function Accounting:python_size() return reliability.dict_size(self:part_sizes()) end
function Accounting:encoded_size(value) if value then return M.python_size(value) end;return self:python_size() end

-- compact(limit) -> the part sizes of the compacted export
function Accounting:compact(limit)
  limit=limit or 3*1024*1024
  local sizes=self:part_sizes()
  while reliability.dict_size(sizes)>limit do
    local buckets={}
    for profile,value in pairs(self.quality) do
      for key in pairs(value.buckets or {}) do buckets[#buckets+1]={tonumber(key),profile,key} end
    end
    if #buckets>0 then
      table.sort(buckets,function(a,b) if a[1]~=b[1] then return a[1]<b[1] end;if a[2]~=b[2] then return a[2]<b[2] end;return a[3]<b[3] end)
      local take=math.max(1,math.floor(#buckets/2))
      for i=1,take do self.quality[buckets[i][2]].buckets[buckets[i][3]]=nil end
      self.retention.quality_buckets_dropped=add(self.retention.quality_buckets_dropped or 0,take)
    else
      local days={}
      for profile,value in pairs(self.activity) do for key in pairs(value.days or {}) do days[#days+1]={key,profile} end end
      if #days==0 then error('accounting retention budget exceeded') end
      table.sort(days,function(a,b) if a[1]~=b[1] then return a[1]<b[1] end;return a[2]<b[2] end)
      local take=math.max(1,math.floor(#days/4))
      for i=1,take do self.activity[days[i][2]].days[days[i][1]]=nil end
      self.retention.activity_days_dropped=add(self.retention.activity_days_dropped or 0,take)
    end
    sizes.quality=M.python_size(self.quality);sizes.activity=M.python_size(self.activity);sizes.retention=M.python_size(self.retention)
  end
  return sizes
end

function Accounting:apply_detail_retention(days,now)
  self.reliability.detail_days=days;self.reliability:prune(pyf(now))
  local cutoff=N(now)-days*86400;local date_cutoff=day_of(cutoff)
  local kept=obj();for key,row in pairs(self.days) do if key>=date_cutoff then kept[key]=row end end;self.days=kept
  kept=obj()
  for key,value in pairs(self.quality) do if last_time(value)>=cutoff then kept[key]=value end end
  self.quality=kept
  for _,value in pairs(self.quality) do
    local buckets=obj();for key,row in pairs(value.buckets or {}) do if tonumber(key)*3600>=cutoff then buckets[key]=row end end;value.buckets=buckets
  end
  for _,value in pairs(self.activity) do
    local kept_days=obj();for key,row in pairs(value.days or {}) do if key>=date_cutoff then kept_days[key]=row end end;value.days=kept_days
  end
  kept=obj();for key,value in pairs(self.activity) do if (N(value.last_seen) or 0)>=cutoff then kept[key]=value end end;self.activity=kept
  if self.wan then self.wan:apply_detail_retention(days,now) end
end

-- public_export(now): the page view (agent.Accounting.public_export); 'reliability' is the public model.
function Accounting:public_export(now)
  now=N(now) or os.time()
  local sizes=self:compact()
  local data=self:export_view()
  data.reliability=self.reliability:public()
  sizes.reliability=M.python_size(data.reliability)
  if reliability.dict_size(sizes)<=500*1024 then return data end
  local quality=obj()
  for identifier,value in pairs(self.quality) do
    local totals=obj({n=0,success=0,rtt_sum=0,unknown=0})
    for _,bucket in pairs(value.buckets or {}) do for key in pairs(totals) do totals[key]=add(totals[key],bucket[key] or 0) end end
    quality[identifier]=obj({last=value.last==nil and NULL or value.last,buckets=obj({summary=totals})})
  end
  data.quality=quality;data.rpc_aggregated=true
  if self:encoded_size(data)<=500*1024 then return data end
  local today=day_of(now);local week=day_of(now-6*86400);local month=string.sub(today,1,7)
  local activity=obj()
  for identifier,value in pairs(self.activity) do
    local periods=obj()
    for _,period in ipairs({'day','week','month'}) do
      local total=empty_activity_day()
      for day,bucket in pairs(value.days or {}) do
        local included=(period=='day' and day==today) or (period=='week' and day>=week and day<=today) or (period=='month' and string.sub(day,1,7)==month and day<=today)
        if included then for key in pairs(total) do total[key]=add(total[key],bucket[key] or 0) end end
      end
      periods[period]=total
    end
    activity[identifier]=obj({name=value.name==nil and identifier or value.name,protocol=value.protocol==nil and 'unknown' or value.protocol,days=obj(),periods=periods})
  end
  data.activity=activity
  return data
end


------------------------------------------------------------------------------------------------------
-- checkpoint_schema.validate
------------------------------------------------------------------------------------------------------
local function refuse(code) error(code,0) end
local function is_dict(v) return type(v)=='table' and v~=canon.null and not canon.is_array(v) and not canon.is_float(v) and (canon.is_object(v) or #v==0) end
local function timestamp(value)
  local n=canon.number(value)
  if type(value)=='boolean' or not n or n~=n or n<0 or n>253370764799 then refuse('CHECKPOINT-TIME') end
end
local function valid_day(key)
  local y,m,d=string.match(key,'^(%d%d%d%d)%-(%d%d)%-(%d%d)$')
  if not y then return false end
  y,m,d=tonumber(y),tonumber(m),tonumber(d)
  if m<1 or m>12 or d<1 then return false end
  local days={31,(y%4==0 and (y%100~=0 or y%400==0)) and 29 or 28,31,30,31,30,31,31,30,31,30,31}
  return d<=days[m]
end
local function accounting_schema(value,nested)
  if not is_dict(value) then refuse('CHECKPOINT-ACCOUNTING') end
  for _,key in ipairs({'months','days','quality','activity','retention'}) do
    if value[key]~=nil and not is_dict(value[key]) then refuse('CHECKPOINT-COLLECTION') end
  end
  local gaps=value.gaps
  if gaps~=nil and (type(gaps)=='boolean' or not is_int(gaps) or canon.is_float(gaps) or gaps<0) then refuse('CHECKPOINT-GAPS') end
  for key,row in pairs(value.months or {}) do
    if not string.find(key,'^%d%d%d%d%-%d%d$') or tonumber(string.sub(key,6))<1 or tonumber(string.sub(key,6))>12 or not is_dict(row) then refuse('CHECKPOINT-MONTH') end
  end
  local function day_rows(rows) for key,row in pairs(rows) do if not valid_day(key) or not is_dict(row) then refuse('CHECKPOINT-DAY') end end end
  day_rows(value.days or {})
  for _,collection in ipairs({value.months or {},value.days or {}}) do
    for _,row in pairs(collection) do
      for _,key in ipairs({'rx','tx','seconds'}) do
        local n=row[key]
        if n~=nil and (type(n)=='boolean' or not canon.number(n) or canon.number(n)<0) then refuse('CHECKPOINT-COUNTER') end
      end
    end
  end
  for _,profile in pairs(value.quality or {}) do
    if not is_dict(profile) or (profile.buckets~=nil and not is_dict(profile.buckets)) then refuse('CHECKPOINT-QUALITY') end
    if profile.last~=nil and profile.last~=canon.null and not is_dict(profile.last) then refuse('CHECKPOINT-LAST') end
    for key,row in pairs(profile.buckets or {}) do
      if not string.find(key,'^%d+$') or #key>12 or not is_dict(row) then refuse('CHECKPOINT-BUCKET') end
    end
  end
  for _,profile in pairs(value.activity or {}) do
    if not is_dict(profile) or (profile.days~=nil and not is_dict(profile.days)) then refuse('CHECKPOINT-ACTIVITY') end
    timestamp(profile.last_seen==nil and 0 or profile.last_seen);day_rows(profile.days or {})
  end
  if value.reliability~=nil then reliability.new(value.reliability) end  -- Reliability(value['reliability']) raises its codes
  if value.wan~=nil and value.wan~=canon.null then
    if nested then refuse('CHECKPOINT-WAN-DEPTH') end
    accounting_schema(value.wan,true)
  end
end
function M.validate(envelope)
  if not is_dict(envelope) or not is_dict(envelope.data) then refuse('CHECKPOINT-ENVELOPE') end
  local data=envelope.data
  if type(data.version)=='boolean' or canon.is_float(data.version) or data.version~=1 then refuse('CHECKPOINT-VERSION') end
  timestamp(data.saved);accounting_schema(data.accounting)
  local remaining=200000
  local function walk(value,depth)
    remaining=remaining-1
    if remaining<0 or depth>12 then refuse('CHECKPOINT-BOUNDS') end
    if canon.is_float(value) then
      if value.value<0 or value.value>1e30 then refuse('CHECKPOINT-NUMBER') end
    elseif value==canon.null or type(value)=='boolean' then return
    elseif type(value)=='number' then
      if value~=value or value<0 or value>1e30 then refuse('CHECKPOINT-NUMBER') end
    elseif type(value)=='string' then
      if #value>4096 then refuse('CHECKPOINT-STRING') end
    elseif type(value)=='table' then
      if canon.is_array(value) or (not canon.is_object(value) and #value>0) then
        if #value>10000 then refuse('CHECKPOINT-LIST') end
        for _,item in ipairs(value) do walk(item,depth+1) end
      else
        for key,item in pairs(value) do
          if type(key)~='string' or #key>256 then refuse('CHECKPOINT-KEY') end
          walk(item,depth+1)
        end
      end
    else refuse('CHECKPOINT-VALUE') end
  end
  walk(data,0)
  return data
end

------------------------------------------------------------------------------------------------------
-- checkpoint / restore (agent.checkpoint / agent.restore without the optional histories)
------------------------------------------------------------------------------------------------------
local function read_envelope(runner,path)
  local text=runner.read_file(path)
  if text==nil then return nil end
  return canon.decode(text)
end
M.read_envelope=read_envelope

function M.checkpoint(runner,persist,accounting)
  accounting:compact()
  local payload=obj({version=1,saved=F(runner.wall()),accounting=accounting:export_view()})
  local ok,old=pcall(read_envelope,runner,persist..'/checkpoint.json')
  if ok and old then
    pcall(function()
      M.validate(old)
      if old.sha256==canon.digest(old.data) then
        local previous=M.new(old.data.accounting)
        previous:apply_detail_retention(accounting:detail_days(),F(runner.wall()))
        old.data.accounting=previous:export_view();old.sha256=canon.digest(old.data)
        runner.write_atomic(persist..'/checkpoint.backup.json',canon.encode(old))
      end
    end)
  end
  local envelope=obj({data=payload,sha256=canon.digest(payload)})
  runner.write_atomic(persist..'/checkpoint.json',canon.encode(envelope))
  return envelope
end

function M.restore(runner,persist)
  local seen_error=false
  for _,filename in ipairs({'checkpoint.json','checkpoint.backup.json'}) do
    local ok,result=pcall(function()
      local raw=read_envelope(runner,persist..'/'..filename)
      if raw==nil then return nil end
      M.validate(raw)
      if raw.sha256~=canon.digest(raw.data) then seen_error=true;return nil end
      if raw.data.version~=1 then seen_error=true;return nil end
      local acc=M.new(raw.data.accounting)
      local saved=canon.number(raw.data.saved) or runner.wall()
      acc.gaps=acc.gaps+1;acc:note_gap(saved,runner.wall())
      if acc.wan then acc.wan.gaps=acc.wan.gaps+1;acc.wan:note_gap(saved,runner.wall()) end
      return acc
    end)
    if ok and result then return result,(seen_error and 'STORAGE-RECOVERED' or nil) end
    if not ok then seen_error=true end
  end
  return M.new(),(seen_error and 'STORAGE-001' or nil)
end

-- sample_counters: sysfs readings of each measured device (one sample per device per pass)
function M.sample_counters(runner,profiles,accounting,now,max_gap)
  local devices={}
  for _,p in ipairs(profiles) do
    local device=p.device
    if device and device~=canon.null and not devices[device] and M.SAFE(device) then
      devices[device]=true
      local ok=pcall(function()
        local ifindex=tonumber(runner.sysfs(device,'ifindex'));local rx=tonumber(runner.sysfs(device,'statistics/rx_bytes'));local tx=tonumber(runner.sysfs(device,'statistics/tx_bytes'))
        if not ifindex or not rx or not tx then error('unreadable counters') end
        accounting:sample(device,ifindex,rx,tx,now,max_gap)
      end)
      if not ok then accounting.gaps=accounting.gaps+1 end
    end
  end
end

------------------------------------------------------------------------------------------------------
-- stats_mode.py
------------------------------------------------------------------------------------------------------
M.stats={}
local stats_cache={key=nil,options={}}
function M.stats.options(runner)
  local mtime=runner.config_mtime()
  if mtime==nil then return nil end
  if stats_cache.key==mtime then return stats_cache.options end
  local text=runner.config_text()
  if text==nil then return {} end
  local found={}
  for _,name in ipairs({'stats_mode','stats_until'}) do
    for line in string.gmatch(text,'[^\n]+') do
      local value=string.match(line,"^%s*option%s+"..name.."%s+'?([A-Za-z0-9_.-]+)'?%s*$")
      if value and #value<=32 then found[name]=value;break end
    end
  end
  stats_cache.key=mtime;stats_cache.options=found
  return found
end
function M.stats.until_time(runner)
  local found=M.stats.options(runner) or {}
  local value=tonumber(found.stats_until or '0') or 0
  return value>0 and value or 0
end
function M.stats.diagnostic(runner,now)
  local found=M.stats.options(runner)
  if found==nil then return true end  -- no package config: not an installed router, record everything
  local until_time=M.stats.until_time(runner)
  return found.stats_mode=='diagnostic' and now<until_time and until_time<=now+M.STATS_HOURS[#M.STATS_HOURS]*3600+60
end
function M.stats.public(runner,now)
  local active=M.stats.diagnostic(runner,now)
  local until_time=M.stats.until_time(runner)
  local bounded=active and until_time>0
  return obj({mode=active and 'diagnostic' or 'work',['until']=bounded and until_time or canon.null,
    remaining=bounded and math.max(0,math.floor(until_time-now+0.5)) or 0,hours=canon.array({unpack(M.STATS_HOURS)}),default_hours=M.STATS_DEFAULT_HOURS})
end
M.stats.STORAGE={{'ram','status.json',nil},{'flash','native-transaction.json',nil},{'flash','pair-auto-state.json',nil},
  {'flash','native-history.json','native-history.backup.json'},{'flash','checkpoint.json','checkpoint.backup.json'},
  {'flash','latency-history.json',nil},{'flash','ping-response-history.json',nil},{'flash','website-response-history.json',nil},
  {'flash','response-compare.json',nil},{'flash','probe-history.json',nil},{'flash','switch-timing.json',nil},
  {'flash','speed-history.json','speed-history.backup.json'},{'flash','fault-history.json',nil}}
function M.stats.storage(runner,runtime,persist)
  local result=obj()
  for _,entry in ipairs(M.stats.STORAGE) do
    local base=entry[1]=='ram' and runtime or persist
    local total=nil
    for _,item in ipairs({entry[2],entry[3]}) do
      local size=runner.file_size(base..'/'..item)
      if size then total=(total or 0)+size end
    end
    if total~=nil then result[entry[1]..':'..entry[2]]=total end
  end
  return result
end

return M
