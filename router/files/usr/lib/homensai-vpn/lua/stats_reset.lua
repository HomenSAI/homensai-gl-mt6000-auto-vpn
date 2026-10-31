-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- stats_reset.lua: stats_reset.py inside the Lua monitor (plan item 6). The page's "reset charts/statistics" button
-- still queues its request through agent.py (stats_reset.request, a short RAM write); until item 6 nothing applied it
-- under the Lua monitor and the page waited forever. The monitor now applies it in its own loop, as
-- agent.monitor_loop does: archive first (checksummed, read back, newest 10 / 12 MB kept), then the native history
-- and the speed history are reset under their own locks, the in-memory accounting/reliability and the histories are
-- cleared, one checkpoint saves everything, and stats-reset-result.json carries the coded result.
-- Same files, same result codes, same archive layout ('<int(now)>-<scope>.json', {schema,scope,time,data,sha256}).
--
-- Never blocking the event loop: the native-history lock and auto-control.lock (speed history) are taken with a
-- non-blocking flock; when one is busy the request stays queued and the next pass retries (Python waited).
-- Differences: dict insertion order of the archive file (sorted keys here; the checksum is over the sorted text in
-- both lines); the late-change comparison is over canonical JSON (Python: dict equality; 1 == 1.0 there).
local canon=require('canon')
local reliability=require('reliability')
local latency=require('latency_history')
local responses=require('response_history')

local M={}
local NULL=canon.null
local N=canon.number
M.SCOPES={latency=true,auto=true,traffic=true,quality=true,speed=true,ranking=true,all=true}
M.ARCHIVE_KEEP=10;M.ARCHIVE_BYTES=12*1024*1024
M.REQUEST='stats-reset-request.json';M.RESULT='stats-reset-result.json'
local copy=reliability.copy

local function parts_of(scope)
  if scope=='all' then return {latency=true,auto=true,traffic=true,quality=true,speed=true} end
  if scope=='ranking' then return {speed=true,quality=true} end
  return {[scope]=true}
end
M.parts_of=parts_of

local function read_json(runner,path)
  local text=runner.read_file(path)
  if text==nil then return nil end
  return canon.decode(text)
end

-- peek(runner, runtime): the queued request's parts without consuming it (nil when there is none)
function M.peek(runner,runtime)
  local ok,value=pcall(read_json,runner,runtime..'/'..M.REQUEST)
  if not ok or not canon.is_object(value) or not M.SCOPES[value.scope] then return nil end
  return parts_of(value.scope)
end

-- stats_reset.pending: read and remove the request; nil unless {scope, nonce:[a-f0-9]{32}}
function M.pending(runner,runtime)
  local path=runtime..'/'..M.REQUEST
  local size=runner.file_size(path)
  if size==nil or size>4096 then return nil end  -- absent, not a regular file, oversize: Python leaves it
  local ok,value=pcall(read_json,runner,path)
  if not ok then value=nil end
  pcall(runner.remove,path)
  if not canon.is_object(value) or not M.SCOPES[value.scope] or type(value.nonce)~='string' or #value.nonce~=32
     or not string.find(value.nonce,'^[a-f0-9]+$') then return nil end
  return value
end

------------------------------------------------------------------------------------------------------
-- response_compare.ResponseCompare: only what the reset needs (load, data, clear, save)
------------------------------------------------------------------------------------------------------
local COMPARE_METHODS={['icmp-1.1.1.1']=true,['icmp-8.8.8.8']=true,['icmp-9.9.9.9']=true,websites=true}
M.COMPARE_NAME='response-compare.json';M.COMPARE_MAX_BYTES=512*1024
local function compare_identifier(v)
  if type(v)~='string' then return false end
  local rest=string.match(v,'^openvpn:(.*)$') or string.match(v,'^wireguard:(.*)$')
  return rest~=nil and #rest>=1 and #rest<=80 and string.find(rest,'^[A-Za-z0-9_.:-]+$')~=nil
end
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function finite(v) local x=N(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local Compare={};Compare.__index=Compare
local function compare_empty() return canon.object({version=1,rows=canon.object(),seen=canon.object()}) end
function M.compare_validate(d)
  local function fail(code) error(code,0) end
  if not canon.is_object(d) or count(d)~=3 or d.version==nil or d.rows==nil or d.seen==nil or not reliability.eq(d.version,1)
     or type(d.version)=='boolean' or not canon.is_object(d.rows) or not canon.is_object(d.seen) then fail('RESPONSE-COMPARE-SCHEMA') end
  for method,profiles in pairs(d.rows) do
    if not COMPARE_METHODS[method] or not canon.is_object(profiles) or count(profiles)>32 then fail('RESPONSE-COMPARE-SCHEMA') end
    for identifier,rows in pairs(profiles) do
      if not compare_identifier(identifier) or not canon.is_array(rows) or #rows>7*24+1 then fail('RESPONSE-COMPARE-SCHEMA') end
      for _,row in ipairs(rows) do
        if not canon.is_array(row) or #row~=4 or not finite(row[1]) then fail('RESPONSE-COMPARE-VALUE') end
        for i=2,4 do if type(row[i])~='number' or row[i]%1~=0 or row[i]<0 then fail('RESPONSE-COMPARE-VALUE') end end
        if row[3]==0 and row[2]~=0 then fail('RESPONSE-COMPARE-VALUE') end
      end
    end
  end
  if count(d.seen)>256 then fail('RESPONSE-COMPARE-SCHEMA') end
  for k,v in pairs(d.seen) do if type(k)~='string' or not finite(v) then fail('RESPONSE-COMPARE-SCHEMA') end end
end
function M.compare_new(data,notice)
  local self=setmetatable({data=data and copy(data) or compare_empty(),notice=notice},Compare)
  M.compare_validate(self.data)
  return self
end
function M.compare_load(io_,path)
  local ok,result=pcall(function()
    if io_.unsafe and io_.unsafe(path,M.COMPARE_MAX_BYTES) then error('size',0) end
    local value=io_.read_json(path,nil)
    if value==nil then return M.compare_new() end
    if not canon.is_object(value) or count(value)~=2 or value.data==nil or type(value.sha256)~='string' or value.sha256~=canon.digest(value.data) then error('checksum',0) end
    return M.compare_new(value.data)
  end)
  if ok then return result end
  return M.compare_new(nil,'RESPONSE-COMPARE-UNAVAILABLE')
end
function Compare:clear()
  if self.notice=='RESPONSE-COMPARE-UNAVAILABLE' then error(self.notice,0) end
  self.data=compare_empty()
end
function Compare:save(io_,path)
  if self.notice=='RESPONSE-COMPARE-UNAVAILABLE' then error(self.notice,0) end
  M.compare_validate(self.data)
  local data=copy(self.data)
  local raw=canon.encode(data)
  if #raw>M.COMPARE_MAX_BYTES then error('RESPONSE-COMPARE-SIZE',0) end
  io_.write_json(path,canon.object({data=data,sha256=canon.sha256(raw)}))
  if self.notice=='RESPONSE-COMPARE-WRITE-FAILED' then self.notice=nil end
end
function Compare:has_rows() return next(self.data.rows)~=nil end

------------------------------------------------------------------------------------------------------
-- the histories a reset works on (agent.monitor_loop load_histories(True))
------------------------------------------------------------------------------------------------------
local function file_io(runner)
  return {read_json=function(path,default) local text=runner.read_file(path);if text==nil then return default end;return canon.decode(text) end,
    write_json=function(path,value) runner.write_atomic(path,canon.encode(value)) end,
    unsafe=function(path,limit) local size=runner.file_size(path);return size~=nil and size>limit end}
end
M.file_io=file_io

-- histories(runner, persist[, in_memory]): {latency, website, ping, compare}; in_memory replaces the loaded ones
-- the monitor already holds (Diagnostics: its live latency/ping histories).
function M.histories(runner,persist,in_memory)
  local io_=file_io(runner)
  local state={}
  if type(in_memory)=='table' and in_memory.latency then state.latency=in_memory.latency
  else state.latency=latency.load(io_,persist..'/'..latency.NAME) end
  state.website=responses.load(io_,persist..'/'..responses.WEBSITE.NAME,responses.WEBSITE)
  if type(in_memory)=='table' and in_memory.ping then state.ping=in_memory.ping
  else state.ping=responses.load(io_,persist..'/'..responses.NAME) end
  state.compare=M.compare_load(io_,persist..'/'..M.COMPARE_NAME)
  return state
end

------------------------------------------------------------------------------------------------------
-- archive, native/speed history resets
------------------------------------------------------------------------------------------------------
local function list_archives(runner,folder)
  local names={}
  for _,name in ipairs(runner.list_dir and runner.list_dir(folder) or {}) do
    if string.find(name,'^[0-9]+%-[a-z]+%.json$') then names[#names+1]=name end
  end
  table.sort(names)
  return names
end

function M.archive(runner,persist,scope,payload,now)
  local folder=persist..'/stats-archive'
  if runner.unsafe_directory and runner.unsafe_directory(folder) then error('STATS-RESET-ARCHIVE-PATH',0) end
  local name=string.format('%d-%s.json',math.floor(N(now)),scope)
  runner.write_atomic(folder..'/'..name,canon.encode(canon.object({schema=1,scope=scope,time=now,data=payload,sha256=canon.digest(payload)})))
  local saved=list_archives(runner,folder)
  local function total()
    local sum=0;for _,n in ipairs(saved) do sum=sum+(runner.file_size(folder..'/'..n) or 0) end;return sum
  end
  while #saved>1 and (#saved>M.ARCHIVE_KEEP or total()>M.ARCHIVE_BYTES) do
    pcall(runner.remove,folder..'/'..table.remove(saved,1))
  end
  return name
end

-- stats_reset.reset_native_history (inside the native-history lock taken by the caller)
function M.reset_native_history(env,persist,now,before)
  local history=require('history')
  local h=history.new(env,persist,10000,7)
  local data=h:load()
  local old=copy(data)
  if before then before(old) end
  data=copy(data)  -- never change the resident copy of history.lua in place
  h:migrate(data)
  data.events=canon.array();data.months=canon.object();data.days=canon.object();data.totals=canon.object()
  data.counted=canon.object();data.daily_since=now;data.returns_since=now;data.detail_budget_dropped=0
  data.counter_accuracy='reset by the owner';data.legacy_months=canon.object()
  data.counted_state=nil;data.counted_reason=nil
  local text=canon.encode(h:envelope(data))
  env.run.fs.write_atomic(h.path,text);env.run.fs.write_atomic(h.backup,text)
  history.forget_resident()
  return old
end

-- speed_test.load_history(): the newest valid copy, results within the retention days
function M.load_speed(runner,persist,now,days)
  local found=false
  for _,name in ipairs({'speed-history.json','speed-history.backup.json'}) do
    local ok,data=pcall(function()
      local item=read_json(runner,persist..'/'..name)
      if item==nil then return nil end
      found=true
      local d=item.data
      if not canon.is_object(item) or not canon.is_object(d) then error('schema',0) end
      if not reliability.eq(item.schema,1) or item.sha256~=canon.digest(d) then return nil end
      if not canon.is_array(d.results) or #d.results>500 then return nil end
      for _,row in ipairs(d.results) do if not canon.is_object(row) or not finite(row.time) then return nil end end
      local kept=canon.array()
      for _,row in ipairs(d.results) do if N(row.time)>=N(now)-days*86400 then kept[#kept+1]=row end end
      d.results=kept;d.retention_days=days
      return d
    end)
    if ok and data then return data end
    if not ok then found=true end
  end
  if found then error('SPEED-HISTORY-CORRUPT',0) end
  return canon.object({results=canon.array(),retention_days=days})
end

-- stats_reset.reset_speed_history (inside auto-control.lock taken by the caller)
function M.reset_speed_history(runner,persist,now,days,before)
  local data=M.load_speed(runner,persist,now,days)
  local old=copy(data)
  if before then before(old) end
  data.results=canon.array();data.history_truncated=0
  local text=canon.encode(canon.object({schema=1,data=data,sha256=canon.digest(data)}))
  runner.write_atomic(persist..'/speed-history.backup.json',text);runner.write_atomic(persist..'/speed-history.json',text)
  return old
end

------------------------------------------------------------------------------------------------------
-- stats_reset.apply
------------------------------------------------------------------------------------------------------
-- apply(ctx, request, acc, state, now) -> result; ctx={runner, persist, env, days}. Mutates acc and state.
function M.apply(ctx,value,acc,state,now)
  local runner,persist=ctx.runner,ctx.persist
  now=reliability.pyf(now)
  local scope=value.scope;local parts=parts_of(scope)
  local function result(extra)
    local r=canon.object({nonce=value.nonce,scope=scope,time=now})
    for k,v in pairs(extra) do r[k]=v end
    return r
  end
  if state.website and (parts.latency or parts.quality) and state.website.notice=='WEBSITE-HISTORY-UNAVAILABLE' then
    return result({done=false,code='WEBSITE-HISTORY-UNAVAILABLE'})
  end
  local name
  local ok,err=pcall(function()
    local payload=canon.object()
    local exported=acc:export()
    if parts.latency then payload.latency=copy(state.latency.data) end
    if state.website and (parts.latency or parts.quality) then payload.website_response=copy(state.website.data) end
    if state.ping and (parts.latency or parts.quality) and state.ping.notice~='PING-HISTORY-UNAVAILABLE' then payload.ping_response=copy(state.ping.data) end
    if state.compare and parts.quality and state.compare.notice~='RESPONSE-COMPARE-UNAVAILABLE' then payload.response_compare=copy(state.compare.data) end
    if parts.auto then payload.reliability=exported.reliability end
    if parts.traffic then
      payload.traffic=canon.object({months=exported.months,days=exported.days,wan=exported.wan,gaps=exported.gaps})
    end
    if parts.quality then payload.quality=canon.object({quality=exported.quality,activity=exported.activity}) end
    if parts.auto then
      local history=require('history')
      payload.native_history=history.new(ctx.env,persist,10000,7):load()
    end
    if parts.speed then payload.speed=M.load_speed(runner,persist,now,ctx.days or 7) end
    name=M.archive(runner,persist,scope,payload,now)
    local saved=read_json(runner,persist..'/stats-archive/'..name)
    if not canon.is_object(saved) or saved.sha256~=canon.digest(saved.data) then error('STATS-RESET-ARCHIVE-UNVERIFIED',0) end
    local function extra(key)
      return function(current)
        if canon.encode(current)~=canon.encode(payload[key]==nil and NULL or payload[key]) then
          M.archive(runner,persist,scope..'late',canon.object({[key]=current}),now)
        end
      end
    end
    if parts.auto then M.reset_native_history(ctx.env,persist,now,extra('native_history')) end
    if parts.speed then M.reset_speed_history(runner,persist,now,ctx.days or 7,extra('speed')) end
  end)
  if not ok then
    local text=type(err)=='table' and tostring(err.code or err) or tostring(err)
    local code=(string.find(text,'^[A-Z][A-Z0-9_-]*$') and #text<=96) and text or 'STATS-RESET-FAILED'
    return result({done=false,code=code})
  end
  if parts.latency then state.latency=latency.new() end
  if state.website then
    if parts.latency then state.website:clear(now) elseif parts.quality then state.website:clear_statistics(now) end
  end
  if state.compare and parts.quality and state.compare.notice~='RESPONSE-COMPARE-UNAVAILABLE' then state.compare:clear() end
  if state.ping and state.ping.notice~='PING-HISTORY-UNAVAILABLE' then
    if parts.latency then state.ping:clear(now) elseif parts.quality then state.ping:clear_statistics(now) end
  end
  if parts.auto then
    acc.reliability=reliability.new(nil,acc.reliability.detail_days);acc.reliability.critical=true
  end
  if parts.traffic then
    acc.months=canon.object();acc.days=canon.object();acc.previous={};acc.gaps=0
    if acc.wan~=nil then acc.wan=require('accounting').new(nil,true) end
  end
  if parts.quality then acc.quality=canon.object();acc.activity=canon.object();acc.activity_previous={} end
  return result({done=true,archive=name})
end

-- save(ctx, acc, state): agent.checkpoint(accounting, *histories) after a done reset (Work mode too).
function M.save(ctx,acc,state)
  local runner,persist=ctx.runner,ctx.persist
  require('accounting').checkpoint(runner,persist,acc)
  local io_=file_io(runner)
  local now=runner.wall()
  if state.latency then
    local ok=pcall(function() state.latency:save(io_,persist..'/'..latency.NAME,now) end)
    if not ok and state.latency.notice~='LATENCY-HISTORY-UNAVAILABLE' then state.latency.notice='LATENCY-HISTORY-WRITE-FAILED' end
  end
  if state.website then
    local ok=pcall(function() state.website:save(io_,persist..'/'..responses.WEBSITE.NAME,now) end)
    if not ok and state.website.notice~='WEBSITE-HISTORY-UNAVAILABLE' then state.website.notice='WEBSITE-HISTORY-WRITE-FAILED' end
  end
  if state.ping then
    local ok=pcall(function() state.ping:save(io_,persist..'/'..responses.NAME,now) end)
    if not ok and state.ping.notice~='PING-HISTORY-UNAVAILABLE' then state.ping.notice='PING-HISTORY-WRITE-FAILED' end
  end
  if state.compare and state.compare:has_rows() then
    local ok=pcall(function() state.compare:save(io_,persist..'/'..M.COMPARE_NAME) end)
    if not ok and state.compare.notice~='RESPONSE-COMPARE-UNAVAILABLE' then state.compare.notice='RESPONSE-COMPARE-WRITE-FAILED' end
  end
end

return M
