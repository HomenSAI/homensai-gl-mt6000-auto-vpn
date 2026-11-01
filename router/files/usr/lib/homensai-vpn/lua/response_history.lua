-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- response_history.lua: ping_response_history.PingResponseHistory (on website_response_history's minute rows)
-- for the Lua monitor's Diagnostics mode. Same file /etc/homensai-vpn/ping-response-history.json
-- ({"data":...,"sha256":<canonical sha256>}), same 13-column minute rows, same public view; Python loads what
-- Lua saves and the other way round (tests/test_lua_monitor_item2.py).
-- Work mode: an empty in-memory history that is neither filled nor saved (agent.monitor_loop load_histories).
-- Minimal port (owner plan item 2): only the ICMP metric. The website/latency/compare histories stay with the
-- Python line; with metric 'websites' the status carries Python's WEBSITE-HISTORY-UNAVAILABLE fallback.
-- Item 6: the route kind of a minute is the full route_history.observed_route (reliability.lua).
local canon=require('canon')

local M={}
M.METRIC='icmp-rtt-ms';M.TARGET_SET='icmp-echo';M.MAX_MS=60000;M.VALID_FOR=465;M.PREFIX='PING-HISTORY'
M.DEFINITION='one ICMP echo per channel per check through its own tunnel; minute means of replies'
M.SCOPE='observed ICMP replies only; a lost echo is a gap; website history is separate'
M.WEBSITE_METRIC='websites-https-mean-ms-v1';M.WEBSITE_TARGET_SET='google-cloudflare-wikipedia-v1'
M.DAY=86400;M.WEEK=7*86400;M.MAX_ROWS=30*1440+1;M.MAX_BYTES=4*1024*1024  -- up to 30 days (retention.lua)
M.NAME='ping-response-history.json'
local KINDS={source=true,target=true,unknown=true,off=true,switching=true,blocked=true,down=true}
local NULL=canon.null

local function num(v) return canon.number(v) end
local function finite(v) local x=num(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function int(v) return type(v)=='number' and v%1==0 end
local function none(v) return v==nil or v==NULL end
local function is_dict(v) return canon.is_object(v) end
-- rows built in the monitor are plain Lua tables (probe.ping_public) or canon objects
local function is_map(v) return type(v)=='table' and v~=NULL and not canon.is_array(v) and not canon.is_float(v) end
local function identifier(v) return type(v)=='string' and (string.find(v,'^openvpn:[A-Za-z0-9_.:-]+$') or string.find(v,'^wireguard:[A-Za-z0-9_.:-]+$'))~=nil and #v<=90 end
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local KEYS={}  -- sha256 may be a sha256sum child on the router: one digest per pair per process
local function pair_key(ids)
  local text=ids[1]..'\0'..ids[2]
  local key=KEYS[text]
  if not key then key=string.sub(canon.sha256(text),1,16);KEYS[text]=key end
  return key
end
M.pair_key=pair_key

local function empty(spec)
  spec=spec or M
  return canon.object({version=1,metric=spec.METRIC,target_set=spec.TARGET_SET,rows=canon.array(),pairs=canon.object(),current=NULL,
    seen=canon.object(),saved=NULL,stats_since=NULL,reset_floor=NULL})
end
M.empty=empty

function M.mean_from_tenths(total,n)
  if n==0 then return NULL end
  return canon.float(math.floor((2*total+n)/(2*n))/10)
end
local function sum_tenths(row,side) return math.floor((num(row[2+side]) or 0)*row[4+side]*10+0.5) end
M.sum_tenths=sum_tenths

-- website_response_history.validate (row indexes are 1-based here: row[1] is Python's row[0])
function M.validate(d,spec)
  spec=spec or M
  local function fail(code) error(code,0) end
  if not is_dict(d) then fail('WEBSITE-HISTORY-SCHEMA') end
  local keys=0;for k in pairs(empty(spec)) do keys=keys+1;if d[k]==nil then fail('WEBSITE-HISTORY-SCHEMA') end end
  if count(d)~=keys or d.version~=1 or d.metric~=spec.METRIC or d.target_set~=spec.TARGET_SET or not canon.is_array(d.rows) or #d.rows>M.MAX_ROWS
     or not is_dict(d.pairs) or count(d.pairs)>32 or not is_dict(d.seen) or count(d.seen)>64 then fail('WEBSITE-HISTORY-SCHEMA') end
  for _,key in ipairs({'saved','stats_since','reset_floor'}) do if not none(d[key]) and (not finite(d[key]) or num(d[key])<0) then fail('WEBSITE-HISTORY-SCHEMA') end end
  for key,pair in pairs(d.pairs) do
    if type(key)~='string' or not string.find(key,'^[a-f0-9]+$') or #key~=16 or not canon.is_array(pair) or #pair~=2 or pair[1]==pair[2]
       or not identifier(pair[1]) or not identifier(pair[2]) or key~=pair_key(pair) then fail('WEBSITE-HISTORY-PAIR') end
  end
  if not none(d.current) and d.pairs[d.current]==nil then fail('WEBSITE-HISTORY-PAIR') end
  for key,stamp in pairs(d.seen) do if not identifier(key) or not finite(stamp) then fail('WEBSITE-HISTORY-SEEN') end end
  local previous=-1
  for _,row in ipairs(d.rows) do
    if not canon.is_array(row) or #row~=13 or not finite(row[1]) or num(row[1])<previous or num(row[1])<0 or not KINDS[row[6]] or d.pairs[row[7]]==nil then fail('WEBSITE-HISTORY-ROW') end
    for side=0,1 do
      local value,c,success,attempted,partial=row[2+side],row[4+side],row[8+side],row[10+side],row[12+side]
      for _,v in ipairs({c,success,attempted,partial}) do if not int(v) or v<0 then fail('WEBSITE-HISTORY-VALUE') end end
      if c+partial>120 or attempted~=3*(c+partial) or not (c*3<=success and success<=c*3+partial*2) or (c==0)~=none(value)
         or (not none(value) and (not finite(value) or num(value)<0 or num(value)>spec.MAX_MS)) then fail('WEBSITE-HISTORY-VALUE') end
    end
    previous=num(row[1])
  end
end

local History={};History.__index=History
function M.new(data,notice,spec)
  spec=spec or M
  local self=setmetatable({data=data or empty(spec),notice=notice,spec=spec,retention_seconds=M.WEEK,byte_budget=nil},History)
  M.validate(self.data,spec)
  return self
end
-- load(io, path): io.read_json(path) raises on a broken file; a missing file is an empty history.
function M.load(io_,path,spec)
  spec=spec or M
  local ok,result=pcall(function()
    if io_.unsafe and io_.unsafe(path,M.MAX_BYTES) then error('size',0) end
    local value=io_.read_json(path,nil)
    if value==nil then return M.new(nil,nil,spec) end
    if not is_dict(value) or count(value)~=2 or type(value.sha256)~='string' or value.data==nil or value.sha256~=canon.digest(value.data) then error('checksum',0) end
    return M.new(value.data,nil,spec)
  end)
  if ok then return result end
  return M.new(nil,spec.PREFIX..'-UNAVAILABLE',spec)
end

-- ping_response_history.measurement
function M.measurement(profile,now)
  if not is_map(profile) or not finite(now) then return nil end
  if profile.vendor_state~='SETTLED' or profile.administrative_state=='disabled' then return nil end
  local sample=profile.ping
  if not is_map(sample) or sample.metric~=M.METRIC or (sample.state~='ok' and sample.state~='failed') then return nil end
  local stamp,ttl=num(sample.time),num(sample.valid_for)
  if not finite(sample.time) or not finite(sample.valid_for) or not (0<ttl and ttl<=M.VALID_FOR) or not (0<=now-stamp and now-stamp<=ttl) then return nil end
  if sample.interface~=profile.interface or sample.vendor_tunnel_id~=profile.vendor_tunnel_id then return nil end
  if sample.state=='failed' then return {time=stamp,avg_ms=nil,successes=0} end
  local rtt=num(sample.rtt_ms)
  if not finite(sample.rtt_ms) or rtt<0 or rtt>M.MAX_MS then return nil end
  return {time=stamp,avg_ms=math.floor(rtt*10+0.5)/10,successes=3}
end

-- route_history.observed_route: the full classification (reliability.lua, with the channel_path kernel proof)
function M.observed_route(status,now) return require('reliability').observed_route(status,now) end

-- observe(status, settings, now, retention_days)
function History:observe(status,settings,now,retention_days)
  if not is_map(status) or not finite(now) or now<0 then return end
  self.retention_seconds=(retention_days or 7)*M.DAY
  local d=self.data
  if #d.rows>0 and now<num(d.rows[#d.rows][1]) then return end
  local kept=canon.array();for _,r in ipairs(d.rows) do if num(r[1])>=now-self.retention_seconds then kept[#kept+1]=r end end
  d.rows=kept
  local used={};for _,r in ipairs(d.rows) do used[r[7]]=true end
  for k in pairs(d.pairs) do if not used[k] then d.pairs[k]=nil end end
  if d.pairs[d.current]==nil then d.current=NULL end
  local native=is_map(status.native_failover) and status.native_failover or canon.object()
  local trusted=native.certified==true or (native.mode=='continuous-pair' and native.proof_scope=='router-probed-ipv4' and native.readiness_verified==true)
  local fresh=trusted and finite(native.time) and 0<=now-num(native.time) and now-num(native.time)<=30
  local plan=is_map(status.failover_plan) and status.failover_plan or canon.object()
  local ids={}
  for i,role in ipairs({'source','target'}) do
    if fresh then ids[i]=native[role] else ids[i]=plan[role]; if ids[i]==nil and type(settings)=='table' then ids[i]=settings['plan_'..role] end end
  end
  if ids[1]==ids[2] or not identifier(ids[1]) or not identifier(ids[2]) then return end
  local key=pair_key(ids)
  if d.pairs[key]==nil and count(d.pairs)>=32 then self.notice=M.PREFIX..'-PAIR-LIMIT';return end
  d.pairs[key]=canon.array({ids[1],ids[2]});d.current=key
  local function bucket(stamp)
    for i=#d.rows,1,-1 do local r=d.rows[i];if num(r[1])==stamp and r[7]==key then return r end end
    local created=canon.array({stamp,NULL,NULL,0,0,'unknown',key,0,0,0,0,0,0})
    local index=#d.rows+1
    for i=1,#d.rows do if num(d.rows[i][1])>stamp then index=i;break end end
    table.insert(d.rows,index,created)
    return created
  end
  local row=bucket(math.floor(now/60)*60)
  local ok,kind=pcall(M.observed_route,status,now)
  row[6]=ok and kind or 'unknown'
  local profiles=type(status.profiles)=='table' and status.profiles or {}
  for side,id in ipairs(ids) do
    local matched={}
    for _,p in ipairs(profiles) do if is_map(p) and p.id==id then matched[#matched+1]=p end end
    local sample=#matched==1 and M.measurement(matched[1],now) or nil
    local seen=num(d.seen[id]) or -1
    if sample and sample.time>seen and (none(d.reset_floor) or sample.time>num(d.reset_floor)) then
      local r=bucket(math.floor(sample.time/60)*60)
      local s=side-1
      if r[4+s]+r[12+s]<120 then
        r[8+s]=r[8+s]+sample.successes;r[10+s]=r[10+s]+3;d.seen[id]=canon.float(sample.time)
        if sample.avg_ms==nil then r[12+s]=r[12+s]+1
        else
          local c=r[4+s]
          r[2+s]=canon.float(((num(r[2+s]) or 0)*c+sample.avg_ms)/(c+1));r[4+s]=c+1
        end
      end
    end
  end
  if #d.rows>M.MAX_ROWS then local cut=canon.array();for i=#d.rows-M.MAX_ROWS+1,#d.rows do cut[#cut+1]=d.rows[i] end;d.rows=cut end
  used={};for _,r in ipairs(d.rows) do used[r[7]]=true end
  for k in pairs(d.pairs) do if not used[k] then d.pairs[k]=nil end end
  local known={};for _,pair in pairs(d.pairs) do known[pair[1]]=true;known[pair[2]]=true end
  for k in pairs(d.seen) do if not known[k] then d.seen[k]=nil end end
end

function History:statistics(rows,side,since)
  local c,total,incomplete,succ,att=0,0,0,0,0
  for _,r in ipairs(rows) do
    if num(r[1])>=since then
      c=c+r[4+side];total=total+sum_tenths(r,side);incomplete=incomplete+r[12+side];succ=succ+r[8+side];att=att+r[10+side]
    end
  end
  return canon.object({metric=M.METRIC,target_set=M.TARGET_SET,avg_ms=c>0 and M.mean_from_tenths(total,c) or NULL,
    complete_samples=c,incomplete_samples=incomplete,cycles=c+incomplete,complete=c,sum_ms=canon.float(total/10),sum_tenths=total,
    successful_checks=succ,attempted_checks=att,since=since})
end

function History:public(now)
  local d=self.data
  local rows={};for _,r in ipairs(d.rows) do if r[7]==d.current then rows[#rows+1]=r end end
  local since=num(d.stats_since) or 0
  if canon.is_float(d.stats_since) then since=d.stats_since end
  local packed,coverage=canon.array(),canon.array()
  for i=math.max(1,#rows-1440),#rows do
    local r=rows[i]
    packed[#packed+1]=canon.array({r[1],r[4]>0 and sum_tenths(r,0) or NULL,r[5]>0 and sum_tenths(r,1) or NULL,r[4],r[5],r[6]})
    coverage[#coverage+1]=canon.array({r[1],r[8],r[9],r[10],r[11],r[12],r[13]})
  end
  local pair=canon.array();if d.current~=NULL and d.pairs[d.current] then pair=canon.array({d.pairs[d.current][1],d.pairs[d.current][2]}) end
  local statistics=canon.object()
  for side,role in ipairs({'source','target'}) do statistics[role]=self:statistics(rows,side-1,num(since) or 0) end
  local result=canon.object({version=1,metric=M.METRIC,target_set=M.TARGET_SET,row_encoding='sum-tenths',definition=M.DEFINITION,
    resolution_seconds=60,retention_seconds=self.retention_seconds,pair=pair,rows=packed,coverage_rows=coverage,rows_count=#rows,
    saved=d.saved,notice=self.notice==nil and NULL or self.notice,stats_since=d.stats_since,reset_floor=d.reset_floor,
    statistics=statistics,scope=M.SCOPE})
  local ps=canon.object()
  for i,id in ipairs(pair) do ps[id]=statistics[i==1 and 'source' or 'target'] end
  result.profile_statistics=ps
  return result
end

-- save(io, path, now): io.write_json(path, envelope). Raises the PREFIX codes like Python.
function History:save(io_,path,now)
  if not finite(now) or now<0 then error(self.spec.PREFIX..'-TIME',0) end
  if self.notice==self.spec.PREFIX..'-UNAVAILABLE' then error(self.notice,0) end
  require('retention').trim_to_budget(self.data,self.byte_budget)  -- size mode: the oldest rows give way
  M.validate(self.data,self.spec)
  local data=canon.decode(canon.encode(self.data))
  data.saved=canon.float(now)
  local raw=canon.encode(data)
  if #raw>M.MAX_BYTES then error(self.spec.PREFIX..'-SIZE',0) end
  io_.write_json(path,canon.object({data=data,sha256=canon.sha256(raw)}))
  self.data.saved=canon.float(now)
  if self.notice==self.spec.PREFIX..'-WRITE-FAILED' then self.notice=nil end
end

-- website_response_history.clear(now) / clear_statistics(now): the owner's statistics reset (stats_reset.lua)
function History:clear(now)
  if self.notice==self.spec.PREFIX..'-UNAVAILABLE' then error(self.notice,0) end
  local floor=now
  if floor==nil then
    floor=0;for _,v in pairs(self.data.seen) do if num(v)>num(floor) then floor=v end end
  end
  if not finite(floor) or num(floor)<0 then error(self.spec.PREFIX..'-TIME',0) end
  self.data=empty(self.spec);self.data.reset_floor=floor;self.notice=nil
end
function History:clear_statistics(now)
  if self.notice==self.spec.PREFIX..'-UNAVAILABLE' then error(self.notice,0) end
  if not finite(now) or num(now)<0 then error(self.spec.PREFIX..'-TIME',0) end
  self.data.stats_since=math.ceil(num(now)/60)*60  -- an int, as math.ceil in Python
end

-- The website-response history file (website-response-history.json): the same rows and envelope with the
-- website metric. The Lua monitor does not measure websites; it loads, resets and saves this file for the
-- owner's statistics reset (stats_reset.lua), as agent.monitor_loop does in Work mode.
M.WEBSITE={METRIC='websites-https-mean-ms-v1',TARGET_SET='google-cloudflare-wikipedia-v1',MAX_MS=6000,PREFIX='WEBSITE-HISTORY',
  NAME='website-response-history.json'}

-- The status field when the owner's metric is 'websites' (not ported): Python's own fallback shape.
function M.website_unavailable()
  return canon.object({metric=M.WEBSITE_METRIC,target_set=M.WEBSITE_TARGET_SET,rows=canon.array(),coverage_rows=canon.array(),notice='WEBSITE-HISTORY-UNAVAILABLE'})
end

return M
