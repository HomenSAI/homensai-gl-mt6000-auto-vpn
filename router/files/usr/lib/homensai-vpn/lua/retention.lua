-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- retention.lua: retention_settings.py for the Lua line (owner, 31 Oct 2026): how long statistics are kept, by time
-- (1..7, 14 or 30 days) or by a size budget (1..32 MB of flash). Same options, defaults, size model, refusal codes
-- and the same oldest-rows trim (tests/test_retention_differential.py runs both on the same inputs).
-- The model constants and their calibration are documented in retention_settings.py.
local canon=require('canon')

local M={}
M.MODES={time=true,size=true}
M.DAY_STOPS={1,2,3,4,5,6,7,14,30}
M.MAX_DAYS=30;M.LEGACY_MAX_DAYS=7;M.DEFAULT_DAYS=7
M.MB_MIN=1;M.MB_MAX=32;M.DEFAULT_MB=4;M.MIB=1048576
M.MODEL={latency_row_flash_fast=79,latency_row_flash_slow=57,response_row_flash=69,
  latency_row_ram=422,response_row_ram=548,
  accounting_day_flash=69778,accounting_cap=3*1048576,accounting_ram_ratio=7,
  compare_flash=36421,compare_ram=212753}
local STOP={};for _,d in ipairs(M.DAY_STOPS) do STOP[d]=true end
local NULL=canon.null

local function is_dict(v) return type(v)=='table' and v~=NULL and not canon.is_array(v) and not canon.is_float(v) end
-- Python _int: an int (not bool, not a JSON float) or 1-4 decimal digits
local function int(raw)
  if type(raw)=='number' and raw%1==0 then return raw end
  if type(raw)=='string' and string.find(raw,'^[0-9]+$') and #raw<=4 then return tonumber(raw) end
  return nil
end
M.int=int

function M.legacy_days(settings)
  local raw=M.DEFAULT_DAYS
  if is_dict(settings) and settings.history_days~=nil then raw=settings.history_days end
  if type(raw)=='number' and raw%1==0 and raw>=1 and raw<=M.LEGACY_MAX_DAYS then return raw end
  if type(raw)=='string' and string.find(raw,'^[1-7]$') then return tonumber(raw) end
  return M.DEFAULT_DAYS
end

-- (mode, days, mb) the owner chose; without the new options the old history_days decides (time mode)
function M.choice(settings)
  if not is_dict(settings) then settings={} end
  local mode=settings.stats_retention_mode
  if type(mode)~='string' or not M.MODES[mode] then mode=nil end
  local days=int(settings.stats_retention_days)
  if mode==nil or not STOP[days] then days=M.legacy_days(settings) end
  local mb=int(settings.stats_retention_mb)
  if mb==nil or mb<M.MB_MIN or mb>M.MB_MAX then mb=M.DEFAULT_MB end
  return mode or 'time',days,mb
end

local function interval(settings)
  local v=is_dict(settings) and int(settings.interval) or nil
  if v and v>=10 and v<=300 then return v end
  return 10
end
function M.compare_on(settings) return is_dict(settings) and (settings.response_compare==true or settings.response_compare=='1') end

function M.per_day(settings)
  local i=interval(settings);local rows=math.floor(86400/math.max(60,i))
  local lat=i<60 and M.MODEL.latency_row_flash_fast or M.MODEL.latency_row_flash_slow
  local acc=M.MODEL.accounting_day_flash
  return {rows=rows,latency={rows*lat,rows*M.MODEL.latency_row_ram},response={rows*M.MODEL.response_row_flash,rows*M.MODEL.response_row_ram},
    accounting={acc,acc*M.MODEL.accounting_ram_ratio}}
end

function M.estimate(settings,days)
  local part=M.per_day(settings);local compare=M.compare_on(settings)
  local acc=math.min(M.MODEL.accounting_cap,days*part.accounting[1])
  local acc_ram=acc*M.MODEL.accounting_ram_ratio
  return canon.object({flash=days*(part.latency[1]+part.response[1])+2*acc+(compare and M.MODEL.compare_flash or 0),
    ram=days*(part.latency[2]+part.response[2])+acc_ram+(compare and M.MODEL.compare_ram or 0),work_flash=2*acc,work_ram=acc_ram})
end

local function daily(part) return part.latency[1]+part.response[1]+2*part.accounting[1] end
function M.size_days(settings,mb)
  local part=M.per_day(settings)
  local budget=mb*M.MIB-(M.compare_on(settings) and M.MODEL.compare_flash or 0)
  return math.max(1,math.min(M.MAX_DAYS,math.floor(budget/daily(part))))
end

function M.resolve(settings)
  local mode,days,mb=M.choice(settings)
  local result={mode=mode,days=days,mb=mb,effective_days=days,latency_bytes=nil,response_bytes=nil}
  if mode=='size' then
    local part=M.per_day(settings)
    local budget=math.max(0,mb*M.MIB-(M.compare_on(settings) and M.MODEL.compare_flash or 0))
    local d=daily(part)
    result.effective_days=M.size_days(settings,mb)
    result.latency_bytes=math.floor(budget*part.latency[1]/d)
    result.response_bytes=math.floor(budget*part.response[1]/d)
  end
  return result
end

-- retention_settings.days(settings): the effective detail period (1..30 days)
function M.days(settings) return M.resolve(settings).effective_days end

function M.public(settings)
  local r=M.resolve(settings)
  local stops=canon.array();for i,d in ipairs(M.DAY_STOPS) do stops[i]=d end
  local model=canon.object();for k,v in pairs(M.MODEL) do model[k]=v end
  return canon.object({mode=r.mode,days=r.days,mb=r.mb,effective_days=r.effective_days,
    latency_bytes=r.latency_bytes==nil and NULL or r.latency_bytes,response_bytes=r.response_bytes==nil and NULL or r.response_bytes,
    interval=interval(settings),compare=M.compare_on(settings)==true,websites=is_dict(settings) and settings.response_metric=='websites' or false,
    day_stops=stops,mb_min=M.MB_MIN,mb_max=M.MB_MAX,model=model,estimate=M.estimate(settings,r.effective_days)})
end

-- trim_to_budget(data, budget): drop the oldest minute rows until canon.encode(data) fits; the same integer steps
function M.trim_to_budget(data,budget)
  if type(budget)~='number' or budget%1~=0 or budget<0 or not is_dict(data) or not canon.is_array(data.rows) then return 0 end
  local size=#canon.encode(data)
  local dropped=0
  while size>budget and #data.rows>0 do
    local count=#data.rows
    local take=math.min(count,math.max(1,math.floor(((size-budget)*count+size-1)/size)))
    local kept=canon.array()
    for i=take+1,count do kept[#kept+1]=data.rows[i] end
    data.rows=kept;dropped=dropped+take
    size=#canon.encode(data)
  end
  return dropped
end

-- retention_settings.payload: the setup_stats mode 'retention' (errors are {code=...} like setup.lua)
local function fail(code) error({code=code},0) end
local function keys_are(t,list)
  local want={};for _,k in ipairs(list) do want[k]=true end
  local n=0
  for k in pairs(t) do if not want[k] then return false end;n=n+1 end
  return n==#list
end
function M.payload(arguments)
  if not is_dict(arguments) or type(arguments.retention)~='string' or not M.MODES[arguments.retention] then fail('STATS-RETENTION-FIELDS') end
  if arguments.retention=='time' then
    if not keys_are(arguments,{'mode','retention','days'}) then fail('STATS-RETENTION-FIELDS') end
    local d=arguments.days
    if type(d)~='number' or d%1~=0 or not STOP[d] then fail('STATS-RETENTION-DAYS') end
    return {stats_retention_mode='time',stats_retention_days=string.format('%d',d),history_days=string.format('%d',math.min(M.LEGACY_MAX_DAYS,d))}
  end
  if not keys_are(arguments,{'mode','retention','mb'}) then fail('STATS-RETENTION-FIELDS') end
  local mb=arguments.mb
  if type(mb)~='number' or mb%1~=0 or mb<M.MB_MIN or mb>M.MB_MAX then fail('STATS-RETENTION-SIZE') end
  return {stats_retention_mode='size',stats_retention_mb=string.format('%d',mb)}
end

-- status.stats_mode.capacity: free flash under persist (nixio.fs.statvfs) and MemAvailable, in bytes or null
function M.capacity(persist,read_file)
  local free=NULL
  local okfs,fs=pcall(require,'nixio.fs')
  if okfs and type(fs)=='table' and fs.statvfs then
    local ok,st=pcall(fs.statvfs,persist)
    if ok and type(st)=='table' and tonumber(st.bavail) and tonumber(st.frsize or st.bsize) then free=tonumber(st.bavail)*tonumber(st.frsize or st.bsize) end
  end
  local ram=NULL
  local okr,text=pcall(read_file or function(path) local f=io.open(path,'r');if not f then return nil end;local t=f:read('*a');f:close();return t end,'/proc/meminfo')
  if okr and type(text)=='string' then
    local kb=string.match(text,'MemAvailable:%s*(%d+)')
    if kb then ram=tonumber(kb)*1024 end
  end
  return canon.object({flash_free=free,ram_available=ram})
end

return M
