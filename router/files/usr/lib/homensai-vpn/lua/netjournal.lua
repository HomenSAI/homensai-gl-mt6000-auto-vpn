-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- netjournal.lua: netjournal.py for the Lua monitor - the network-behaviour journal of the Auto pair (2.1.0-alpha9,
-- owner design 04.11.2026). Same records, same arithmetic (tests/advisor_cases.json, generated from the Python module
-- by tests/gen_advisor_cases.py). Record format, the outage estimate, the unnecessary-failover rules and the
-- RAM / flash policy: netjournal.py and docs/architecture/NETWORK-ADVISOR-2026-11-04.ru.md.
-- Single writer: the monitor (observe once per pass); the advisor only reads.
local canon=require('canon')
local CM=require('channel_model')

local M={}
local NULL=canon.null
local floor,mmin,mmax=math.floor,math.min,math.max

M.VERSION=1
M.DAY=86400;M.SLOT=300;M.SLOTS=288;M.HOURS=24;M.RETENTION=30
M.EDGES={1,2,3,5,8,13,21,34,55,89,144,233,377,610,987}
M.MAX_OUTAGES=100;M.MAX_SHORT=60;M.SHORT=15;M.SHORTS=16384
M.MAX_TUNNELS=4;M.PACK=128;M.TOTAL_CAP=127
M.STALE=120;M.FLAP_RETURN=600;M.FALSE_LOOKBACK=60;M.COST=20
M.RAM_SPACING=60
M.DAYS_NAME='netjournal-days.json';M.TODAY_NAME='netjournal-today.json';M.FLASH_NAME='netjournal.json'

local function finite(x) return type(x)=='number' and x==x and x~=math.huge and x~=-math.huge end
local function number(v) v=canon.number(v);if finite(v) then return v end;return nil end
local function zeros(n) local t=canon.array();for i=1,n do t[i]=0 end;return t end
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function is_int(v) return type(v)=='number' and v%1==0 end

function M.day_index(now,offset) return floor((now+offset)/M.DAY) end
function M.new_day(day) return canon.object({d=day,sw=0,rt=0,us=0,ch=canon.object()}) end
function M.new_tunnel(role)
  return canon.object({r=role,n=0,f=0,lp=zeros(M.SLOTS),rs=zeros(M.HOURS),rn=zeros(M.HOURS),oh=zeros(#M.EDGES),o=canon.array(),ox=0})
end
function M.new_state() return canon.object({open=canon.object(),ok=canon.object(),fail=canon.object(),route=NULL,ret=NULL,fo=NULL}) end
function M.new() return {v=M.VERSION,days={},cur=nil,st=M.new_state(),flash_day=nil} end

function M.bin_of(d)
  local index=1
  for i,edge in ipairs(M.EDGES) do if d>=edge then index=i end end
  return index
end
-- (short outages, failed checks, checks) of one 'lp' slot
function M.unpack(v) return floor(v/M.SHORTS),floor((v%M.SHORTS)/M.PACK),v%M.PACK end

local function close(rec,o,ok_time,day,offset)
  local start,prev,last,flags=o[1],o[2],o[3],o[4]
  local lower,upper=last-start,ok_time-prev
  local d=mmax(1,floor((lower+upper)/2+0.5))
  local second=floor(start+offset-day*M.DAY)
  local bin=M.bin_of(d);rec.oh[bin]=rec.oh[bin]+1
  if d<=M.SHORT then
    local slot=mmin(M.SLOTS-1,mmax(0,floor(second/M.SLOT)))+1
    if floor(rec.lp[slot]/M.SHORTS)<M.TOTAL_CAP then rec.lp[slot]=rec.lp[slot]+M.SHORTS end
  end
  local cap=3*(d<=M.SHORT and M.MAX_SHORT or M.MAX_OUTAGES)
  if #rec.o<cap then local n=#rec.o;rec.o[n+1]=second;rec.o[n+2]=d;rec.o[n+3]=flags
  else rec.ox=rec.ox+1 end
  return start,d
end

-- observe(journal, samples, pair, route, now, offset) -> rolled (a day was completed): netjournal.observe
function M.observe(journal,samples,pair,route,now,offset)
  local rolled=false
  local day=M.day_index(now,offset)
  local cur=journal.cur
  if cur==nil or cur.d<day then
    if cur~=nil then journal.days[#journal.days+1]=cur;rolled=true end
    local kept={}
    for _,d in ipairs(journal.days) do if d.d>=day-M.RETENTION then kept[#kept+1]=d end end
    while #kept>M.RETENTION do table.remove(kept,1) end
    journal.days=kept
    cur=M.new_day(day);journal.cur=cur
  end
  day=cur.d
  local st=journal.st
  local source=type(pair)=='table' and pair.source or nil
  local target=type(pair)=='table' and pair.target or nil
  local roles={}
  if type(source)=='string' and source~='' then roles[source]=0 else source=nil end
  if type(target)=='string' and target~='' and target~=source then roles[target]=1 end
  for _,key in ipairs({'open','ok','fail'}) do
    local drop={}
    for identifier in pairs(st[key]) do if roles[identifier]==nil then drop[#drop+1]=identifier end end
    for _,identifier in ipairs(drop) do st[key][identifier]=nil end
  end
  local carrying=nil
  if route=='source' then carrying=source elseif route=='target' then carrying=target end
  local points={}
  for _,s in ipairs(type(samples)=='table' and samples or {}) do
    if type(s)=='table' and s~=NULL and type(s.id)=='string' and roles[s.id]~=nil and number(s.time)~=nil then points[#points+1]=s end
  end
  -- stable like Python's sorted(): the original order breaks ties
  for i,s in ipairs(points) do s=points[i];points[i]={s,i} end
  table.sort(points,function(a,b) local ta,tb=number(a[1].time),number(b[1].time);if ta~=tb then return ta<tb end;return a[2]<b[2] end)
  for _,pair_ in ipairs(points) do
    local s=pair_[1]
    local identifier=s.id
    local obs=CM.observation(s)
    if obs~=nil then
      local rec=cur.ch[identifier]
      if rec==nil and count(cur.ch)<M.MAX_TUNNELS then rec=M.new_tunnel(roles[identifier]);cur.ch[identifier]=rec end
      if rec~=nil then
        rec.r=roles[identifier]
        local t=number(s.time)
        local second=t+offset-day*M.DAY
        local slot=mmin(M.SLOTS-1,mmax(0,floor(second/M.SLOT)))+1
        local hour=mmin(M.HOURS-1,mmax(0,floor(second/3600)))+1
        local shorts,fails,total=M.unpack(rec.lp[slot])
        if total<M.TOTAL_CAP then
          total=total+1
          if obs>0 then fails=fails+1 end
        end
        rec.lp[slot]=shorts*M.SHORTS+fails*M.PACK+total
        rec.n=rec.n+1
        if obs==0 then
          local rtt=number(s.rtt_ms)
          if rtt~=nil and rtt>=0 and rtt<=60000 then rec.rs[hour]=rec.rs[hour]+floor(rtt+0.5);rec.rn[hour]=rec.rn[hour]+1 end
          local o=st.open[identifier]
          if o~=nil then
            st.open[identifier]=nil
            local start,d=close(rec,o,t,day,offset)
            local fo=st.fo
            if identifier==source and fo~=NULL and fo.us==0 and start<=fo.t and start+d-fo.t<M.COST then
              cur.us=cur.us+1;fo.us=1
            end
          end
          st.ok[identifier]=t
        else
          rec.f=rec.f+1
          st.fail[identifier]=t
          local o=st.open[identifier]
          if o==nil then
            local prev=st.ok[identifier]
            if prev==nil or prev>t or t-prev>M.STALE then prev=t end
            st.open[identifier]=canon.array({t,prev,t,(identifier==carrying and 1 or 0)+(roles[identifier]==1 and 2 or 0)})
          else o[3]=t end
        end
      end
    end
  end
  if route=='source' or route=='target' then
    local last=st.route
    if last=='source' and route=='target' then
      cur.sw=cur.sw+1
      local us=0
      local failed=source and st.fail[source] or nil
      if st.ret~=NULL and now-st.ret<M.FLAP_RETURN then us=1
      elseif not (source and st.open[source]) and (failed==nil or now-failed>M.FALSE_LOOKBACK) then us=1 end
      cur.us=cur.us+us;st.fo=canon.object({t=now,us=us})
    elseif last=='target' and route=='source' then
      cur.rt=cur.rt+1;st.ret=now;st.fo=NULL
    end
    st.route=route
  end
  return rolled
end

function M.open_outages(journal)
  local out=canon.array()
  for identifier in pairs(journal.st.open) do out[#out+1]=identifier end
  table.sort(out)
  return out
end

function M.flash_due(journal,now,offset)
  return #journal.days>0 and journal.flash_day~=M.day_index(now,offset)
end

local function days_array(journal) local a=canon.array();for i,d in ipairs(journal.days) do a[i]=d end;return a end
local function nv(v) if v==nil then return NULL end;return v end
function M.days_text(journal) return canon.encode(canon.object({v=M.VERSION,days=days_array(journal)})) end
function M.today_text(journal)
  return canon.encode(canon.object({v=M.VERSION,cur=nv(journal.cur),st=journal.st,flash_day=nv(journal.flash_day)}))
end
function M.flash_text(journal,now,offset)
  return canon.encode(canon.object({v=M.VERSION,days=days_array(journal),saved_day=M.day_index(now,offset)}))
end

local function array_len(v,n) return type(v)=='table' and v~=NULL and #v==n end
local function valid_day(d)
  if type(d)~='table' or d==NULL or not is_int(d.d) or type(d.ch)~='table' or d.ch==NULL then return false end
  for _,k in ipairs({'sw','rt','us'}) do if not is_int(d[k]) then return false end end
  for _,r in pairs(d.ch) do
    if type(r)~='table' or not array_len(r.lp,M.SLOTS) or type(r.o)~='table' or not array_len(r.oh,#M.EDGES)
      or not array_len(r.rs,M.HOURS) or not array_len(r.rn,M.HOURS) then return false end
  end
  return true
end
M.valid_day=valid_day

local function parse(raw)
  if type(raw)~='string' then return nil end
  local ok,value=pcall(canon.decode,raw)
  if not ok or type(value)~='table' or value==NULL then return nil end
  value=canon.plain(value)
  if value.v~=M.VERSION then return nil end
  return value
end
-- load(days_text, today_text, flash_text) -> journal: netjournal.load
function M.load(days_raw,today_raw,flash_raw)
  local journal=M.new()
  local days,source=parse(days_raw),'ram'
  if days==nil then
    days,source=parse(flash_raw),'flash'
    if days~=nil and is_int(days.saved_day) then journal.flash_day=days.saved_day end
  end
  if days~=nil and type(days.days)=='table' then
    local list={}
    for _,d in ipairs(days.days) do if valid_day(d) then list[#list+1]=d end end
    table.sort(list,function(a,b) return a.d<b.d end)
    while #list>M.RETENTION do table.remove(list,1) end
    journal.days=list
  end
  local today=parse(today_raw)
  if today~=nil and source=='ram' then
    if valid_day(today.cur) then journal.cur=today.cur end
    local st=today.st
    if type(st)=='table' and st~=NULL and type(st.open)=='table' and type(st.ok)=='table' and type(st.fail)=='table' then
      for _,k in ipairs({'open','ok','fail'}) do if st[k]==NULL then st[k]=canon.object() end end
      if st.route==nil then st.route=NULL end;if st.ret==nil then st.ret=NULL end;if st.fo==nil then st.fo=NULL end
      journal.st=st
    end
    if is_int(today.flash_day) then journal.flash_day=today.flash_day end
  end
  return journal
end

-- The monitor's side (netjournal.Writer): io = {read(path)->text|nil, write_ram(path,text), write_flash(path,text)}
local Writer={};Writer.__index=Writer
function M.writer(io,runtime,persist)
  local self=setmetatable({io=io,runtime=runtime,persist=persist,today_at=nil,flash_writes=0},Writer)
  local days_raw=io.read(runtime..'/'..M.DAYS_NAME)
  self.journal=M.load(days_raw,io.read(runtime..'/'..M.TODAY_NAME),io.read(persist..'/'..M.FLASH_NAME))
  if days_raw==nil then io.write_ram(runtime..'/'..M.DAYS_NAME,M.days_text(self.journal)) end
  return self
end
function Writer:pass(samples,pair,route,now,offset,clock)
  local rolled=M.observe(self.journal,samples,pair,route,now,offset)
  if rolled then self.io.write_ram(self.runtime..'/'..M.DAYS_NAME,M.days_text(self.journal)) end
  if M.flash_due(self.journal,now,offset) then
    self.journal.flash_day=M.day_index(now,offset)
    self.io.write_flash(self.persist..'/'..M.FLASH_NAME,M.flash_text(self.journal,now,offset));self.flash_writes=self.flash_writes+1
    rolled=true
  end
  if rolled or self.today_at==nil or clock-self.today_at>=M.RAM_SPACING then
    self.io.write_ram(self.runtime..'/'..M.TODAY_NAME,M.today_text(self.journal));self.today_at=clock
  end
  return rolled
end

-- The router's local offset from UTC at `now` (TZ of the monitor process, daylight saving included).
function M.local_offset(now)
  now=floor(now)
  local here=os.date('*t',now)
  local utc=os.date('!*t',now)
  utc.isdst=here.isdst
  return floor(os.time(here)-os.time(utc))
end

return M
