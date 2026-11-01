-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- latency_history.lua: latency_history.LatencyHistory (bounded one-minute HTTPS-latency means of the Auto pair for
-- the configured 1-30 days, retention.lua) and website_response_history.technical_history_tail, for the Lua monitor (plan item 6).
-- Same file /etc/homensai-vpn/latency-history.json ({"data":...,"sha256":sha256(sorted compact JSON of data)}), same
-- 7-column minute rows, same public view; values keep Python's types (minute stamps are ints, means are floats,
-- 'seen' and 'saved' are float time stamps). Filled and saved only in the Diagnostics statistics mode, like Python;
-- in Work mode the monitor publishes the empty view.
-- Python quirk kept on purpose (files stay interchangeable): a minute whose observed route is 'blocked' or 'down'
-- is written although KINDS does not list them, and the next load of that file reports LATENCY-HISTORY-UNAVAILABLE.
local canon=require('canon')
local reliability=require('reliability')

local M={}
local NULL=canon.null
local N=canon.number
local isf=canon.is_float
M.DAY=86400;M.WEEK=7*86400;M.MAX_ROWS=30*1440+1;M.MAX_BYTES=4*1024*1024
M.PUBLIC_ROWS=7*1440+1  -- rows_json carries at most the newest week (status transport bound)
M.NAME='latency-history.json'
local KINDS={source=true,target=true,unknown=true,off=true,switching=true}
M.SCOPE='observed minute means; gaps are unobserved; not ICMP or LAN proof'

local function none(v) return v==nil or v==NULL end
local function number(v) local x=N(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function is_int(v) return type(v)=='number' and v%1==0 end
local function identifier(v)  -- ^(?:openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$
  if type(v)~="string" then return false end
  local rest=string.match(v,"^openvpn:(.*)$") or string.match(v,"^wireguard:(.*)$")
  return rest~=nil and #rest>=1 and #rest<=80 and string.find(rest,"^[A-Za-z0-9_.:-]+$")~=nil
end
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function fail(code) error(code,0) end
local KEYS={}
local function pair_key(ids)
  local text=ids[1]..'\0'..ids[2]
  local key=KEYS[text]
  if not key then key=string.sub(canon.sha256(text),1,16);KEYS[text]=key end
  return key
end
M.pair_key=pair_key

-- retention_settings.days(settings)
function M.days(settings) return require('retention').days(settings) end

local function empty() return canon.object({version=1,rows=canon.array(),pairs=canon.object(),current=NULL,seen=canon.object(),saved=NULL}) end

function M.validate(d)
  if not canon.is_object(d) or count(d)~=6 then fail('LATENCY-HISTORY-SCHEMA') end
  for k in pairs(empty()) do if d[k]==nil then fail('LATENCY-HISTORY-SCHEMA') end end
  if not reliability.eq(d.version,1) or type(d.version)=='boolean' or not canon.is_array(d.rows) or #d.rows>M.MAX_ROWS
     or not canon.is_object(d.pairs) or count(d.pairs)>32 or not canon.is_object(d.seen) or count(d.seen)>64
     or (d.saved~=NULL and not number(d.saved)) then fail('LATENCY-HISTORY-SCHEMA') end
  for key,pair in pairs(d.pairs) do
    if type(key)~='string' or #key~=16 or not string.find(key,'^[a-f0-9]+$') or not canon.is_array(pair) or #pair~=2 or pair[1]==pair[2]
       or not identifier(pair[1]) or not identifier(pair[2]) then fail('LATENCY-HISTORY-PAIR') end
    if key~=pair_key(pair) then fail('LATENCY-HISTORY-PAIR') end
  end
  if d.current~=NULL and d.pairs[d.current]==nil then fail('LATENCY-HISTORY-CURRENT') end
  for key,stamp in pairs(d.seen) do if not identifier(key) or not number(stamp) then fail('LATENCY-HISTORY-SEEN') end end
  local previous=-1
  for _,row in ipairs(d.rows) do
    if not canon.is_array(row) or #row~=7 or not number(row[1]) or N(row[1])<0 or N(row[1])<previous
       or type(row[7])~='string' or d.pairs[row[7]]==nil or not KINDS[row[6]] then fail('LATENCY-HISTORY-ROW') end
    for side=0,1 do
      local value,c=row[2+side],row[4+side]
      if not is_int(c) or c<0 or c>120 or (c==0)~=(value==NULL) or (value~=NULL and (not number(value) or N(value)<0 or N(value)>600000)) then
        fail('LATENCY-HISTORY-VALUE')
      end
    end
    previous=N(row[1])
  end
end

local History={};History.__index=History
function M.new(data,notice)
  local self=setmetatable({data=data or empty(),notice=notice,retention_seconds=M.WEEK,byte_budget=nil},History)
  if data then self.data=reliability.copy(data) end
  M.validate(self.data)
  return self
end

-- load(io, path): io.read_json(path, nil) (raises on a broken file), io.unsafe(path, limit) (symlink/oversize)
function M.load(io_,path)
  local ok,result=pcall(function()
    if io_.unsafe and io_.unsafe(path,M.MAX_BYTES) then error('size',0) end
    local value=io_.read_json(path,nil)
    if value==nil then return M.new() end
    if not canon.is_object(value) or count(value)~=2 or value.data==nil or type(value.sha256)~='string' or value.sha256~=canon.digest(value.data) then error('checksum',0) end
    return M.new(value.data)
  end)
  if ok then return result end
  return M.new(nil,'LATENCY-HISTORY-UNAVAILABLE')
end

local CURRENT_STATES={OBSERVING=true,COMMITTED=true,['DEGRADED-ON-RESERVE']=true,['STOPPED-ON-RESERVE']=true}
local function profile_rows(status)
  local profiles=type(status)=='table' and status.profiles or nil
  if not canon.is_array(profiles) and not (type(profiles)=='table' and profiles~=NULL and (#profiles>0 or next(profiles)==nil)) then return {} end
  return profiles
end

-- observe(status, settings, now)
function History:observe(status,settings,now)
  if not number(now) or N(now)<0 then return end
  local t=N(now)
  self.retention_seconds=M.days(settings)*M.DAY
  local d=self.data
  if #d.rows>0 and t<N(d.rows[#d.rows][1]) then return end
  local native=type(status)=='table' and status.native_failover or nil
  if not canon.is_object(native) then native=canon.object() end
  local trusted=native.certified==true or (native.mode=='continuous-pair' and native.proof_scope=='router-probed-ipv4' and native.readiness_verified==true)
  local native_current=trusted and number(native.time) and -5<=t-N(native.time) and t-N(native.time)<=30 and CURRENT_STATES[native.state]==true
  local kept=canon.array();for _,row in ipairs(d.rows) do if N(row[1])>=t-self.retention_seconds then kept[#kept+1]=row end end
  d.rows=kept
  local used={};for _,row in ipairs(d.rows) do used[row[7]]=true end
  for k in pairs(d.pairs) do if not used[k] then d.pairs[k]=nil end end
  if d.current~=NULL and d.pairs[d.current]==nil then d.current=NULL end
  local valid={};for _,pair in pairs(d.pairs) do valid[pair[1]]=true;valid[pair[2]]=true end
  for k in pairs(d.seen) do if not valid[k] then d.seen[k]=nil end end
  local ids={}
  for i,role in ipairs({'source','target'}) do
    if native_current then ids[i]=native[role] else ids[i]=type(settings)=='table' and settings['plan_'..role] or nil end
  end
  if ids[1]==ids[2] or not identifier(ids[1]) or not identifier(ids[2]) then return end
  local key=pair_key(ids)
  local minute=math.floor(t/60)*60
  if d.pairs[key]==nil and count(d.pairs)>=32 then self.notice='LATENCY-PAIR-LIMIT';return end
  d.pairs[key]=canon.array({ids[1],ids[2]});d.current=key
  local last=d.rows[#d.rows]
  if not last or N(last[1])~=minute or last[7]~=key then d.rows[#d.rows+1]=canon.array({minute,NULL,NULL,0,0,'unknown',key}) end
  local row=d.rows[#d.rows]
  local ok,kind=pcall(reliability.observed_route,status,t)
  row[6]=ok and kind or 'unknown'
  if (row[6]=='source' or row[6]=='target') and not native_current then row[6]='unknown' end
  local profiles=profile_rows(status)
  for index,id in ipairs(ids) do
    local p=nil
    for _,candidate in ipairs(profiles) do
      if type(candidate)=="table" and candidate~=NULL and not canon.is_array(candidate) and not isf(candidate) and candidate.id==id then p=candidate;break end
    end
    if p and none(p.code) and p.dns_ok==true and is_int(p.https_success) and p.https_success>=2 and p.vendor_state=='SETTLED' then
      local stamp,rtt=p.time,p.rtt_ms
      local seen=d.seen[id]
      if number(stamp) and -5<=t-N(stamp) and t-N(stamp)<=90 and N(stamp)>(seen==nil and -1 or N(seen)) and number(rtt) and N(rtt)>=0 and N(rtt)<=600000 then
        local c=row[index+3]
        if c<120 then
          local mean=row[index+1];local base=(mean==NULL or N(mean)==0) and 0 or N(mean)
          row[index+1]=canon.float((base*c+N(rtt))/(c+1));row[index+3]=c+1;d.seen[id]=reliability.pyf(stamp)
        end
      end
    end
  end
  if #d.rows>M.MAX_ROWS then local cut=canon.array();for i=#d.rows-M.MAX_ROWS+1,#d.rows do cut[#cut+1]=d.rows[i] end;d.rows=cut end
  valid={};for _,pair in pairs(d.pairs) do valid[pair[1]]=true;valid[pair[2]]=true end
  for k in pairs(d.seen) do if not valid[k] then d.seen[k]=nil end end
end

-- round(x, 1) of Python: correctly rounded decimal of the binary value (printf %.1f is exact on glibc and musl)
local function round1(v)
  if v==NULL then return NULL end
  if not isf(v) then return v end  -- round(int, 1) is the int
  return canon.float(tonumber(string.format('%.1f',v.value)))
end
M.round1=round1

function History:public()
  local d=self.data
  local rows=canon.array()
  for _,r in ipairs(d.rows) do
    if r[7]==d.current then rows[#rows+1]=canon.array({r[1],round1(r[2]),round1(r[3]),r[4],r[5],r[6]}) end
  end
  local tail=canon.array();for i=math.max(1,#rows-1440),#rows do tail[#tail+1]=rows[i] end
  local pair=canon.array()
  if d.current~=NULL and d.pairs[d.current] then pair=canon.array({d.pairs[d.current][1],d.pairs[d.current][2]}) end
  local result=canon.object({version=1,metric='https-rtt-ms',resolution_seconds=60,retention_seconds=self.retention_seconds,
    pair=pair,rows=tail,rows_count=#rows,saved=d.saved,notice=self.notice==nil and NULL or self.notice,scope=M.SCOPE})
  if #rows>1441 then
    local week=canon.array();for i=math.max(1,#rows-M.PUBLIC_ROWS+1),#rows do week[#week+1]=rows[i] end
    result.rows_json=canon.encode(week)
  end
  return result
end

-- save(io, path, now): io.write_json(path, envelope); raises the Python codes.
function History:save(io_,path,now)
  if not number(now) or N(now)<0 then error('LATENCY-HISTORY-TIME',0) end
  if self.notice=='LATENCY-HISTORY-UNAVAILABLE' then error(self.notice,0) end
  require('retention').trim_to_budget(self.data,self.byte_budget)  -- size mode: the oldest rows give way
  local data=reliability.copy(self.data);data.saved=reliability.pyf(now)
  local raw=canon.encode(data)
  if #raw>M.MAX_BYTES then error('LATENCY-HISTORY-SIZE',0) end
  io_.write_json(path,canon.object({data=data,sha256=canon.sha256(raw)}))
  self.data.saved=reliability.pyf(now)
  if self.notice=='LATENCY-HISTORY-WRITE-FAILED' then self.notice=nil end
end

-- website_response_history.technical_history_tail(history, now)
function M.technical_history_tail(history,now)
  if not canon.is_object(history) then return history end
  local result=canon.object();for k,v in pairs(history) do result[k]=v end
  result.rows_json=nil
  local rows=canon.is_array(result.rows) and result.rows or canon.array()
  local selected=rows
  if number(now) then
    selected=canon.array()
    for _,row in ipairs(rows) do
      if canon.is_array(row) and #row>0 and number(row[1]) and N(now)-M.DAY<=N(row[1]) and N(row[1])<=N(now) then selected[#selected+1]=row end
    end
  end
  local tail=canon.array();for i=math.max(1,#selected-1440),#selected do tail[#tail+1]=selected[i] end
  result.rows=tail
  result.technical_history_tail_only=true
  result.retained_rows_count=history.rows_count==nil and #selected or history.rows_count
  result.served_rows_count=#tail
  return result
end

return M
