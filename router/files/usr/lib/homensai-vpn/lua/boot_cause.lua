-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- boot_cause.lua: why the previous boot ended - kernel crash, planned reboot, plain reboot or power cut
-- (GL-SENSORS-2026-11-04.ru.md, item 5). Twin of boot_cause.py (shared cases router/tests/gl_sensors_cases.json).
-- Kernel crash: a dmesg-ramoops-* file still in /sys/fs/pstore, or /tmp/log/crash_log (GL gl_crash_log, START=99, runs
-- before our S99homensai-vpn: procd starts S* scripts one after another in name order; it deletes pstore after the
-- merge) whose fingerprint changed since the previous boot. Planned reboot: gl_timer.reboot matches the local time at
-- shutdown (`lua boot_cause.lua shutdown-reason`, called by the init script's stop on a system shutdown).
if arg and arg[0] and string.find(arg[0],'boot_cause%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local M={}
M.STATE='boot-cause.json'
M.CRASH_LOG='/tmp/log/crash_log'
M.PSTORE='/sys/fs/pstore'
M.MATCH_MINUTES=3
M.LIMIT=1024*1024

function M.fingerprint(data)
  if type(data)~='string' or data=='' then return '' end
  local h,n,byte=0,#data,string.byte
  for i=1,n,256 do  -- 256 bytes per call: one C call instead of 256 (the result is the same byte by byte)
    local chunk={byte(data,i,math.min(i+255,n))}
    for k=1,#chunk do h=(h*31+chunk[k])%4294967296 end
  end
  return string.format('%d:%08x',#data,h)
end

function M.crash_evidence(pstore_names,crash_data,remembered)
  local fp=M.fingerprint(crash_data)
  for _,name in ipairs(pstore_names or {}) do
    if type(name)=='string' and string.find(name,'^dmesg%-ramoops%-%d+$') then return 'crash',fp end
  end
  if type(remembered)~='string' then return 'unknown',fp end
  if fp~='' and fp~=remembered then return 'crash',fp end
  return 'none',fp
end

local function int(v) if type(v)=='string' and string.find(v,'^%d%d?$') then return tonumber(v) end;return nil end

-- timer: {enable=,hour=,min=,week=} strings as uci gives them; wday 0 = Sunday (cron)
function M.planned(timer,wday,hour,minute)
  if type(timer)~='table' or timer.enable~='1' then return false end
  local h,m,week=int(timer.hour),int(timer.min),timer.week
  if h==nil or m==nil or type(week)~='string' then return false end
  local days={}
  for part in string.gmatch(string.gsub(week,',',' '),'%S+') do
    local value=int(part)
    if value==nil then return false end
    days[value==0 and 7 or value]=true
  end
  if not days[wday==0 and 7 or wday] then return false end
  local delta=hour*60+minute-(h*60+m)
  return delta>=0 and delta<=M.MATCH_MINUTES
end

function M.shutdown_reason(timer,wday,hour,minute)
  if M.planned(timer,wday,hour,minute) then return 'planned-reboot' end
  return 'reboot'
end

local function read(path,limit)
  local f=io.open(path,'rb');if not f then return nil end
  local data=f:read(limit or M.LIMIT);f:close();return data
end

local function remembered_fp(persist)
  local text=read(persist..'/'..M.STATE)
  if text==nil then return nil,true end
  local ok,row=pcall(function() return require('canon').decode(text) end)
  if ok and type(row)=='table' and type(row.crash_fp)=='string' then return row.crash_fp,true end
  return nil,false
end

-- evaluate(persist, options): options.list_dir(path)->names, options.write(path,text), options.pstore, options.crash_log
function M.evaluate(persist,options)
  options=options or {}
  local ok,result=pcall(function()
    local names=options.list_dir and options.list_dir(options.pstore or M.PSTORE) or {}
    local remembered=remembered_fp(persist)
    local verdict,fp=M.crash_evidence(names,read(options.crash_log or M.CRASH_LOG),remembered)
    if fp~=remembered and options.write then
      pcall(options.write,persist..'/'..M.STATE,require('canon').encode(require('canon').object({crash_fp=fp})))
    end
    return verdict
  end)
  if ok then return result end
  return 'unknown'
end

function M.refresh(persist,options)
  options=options or {}
  local remembered,valid=remembered_fp(persist)
  if not valid or type(remembered)~='string' then return false end
  local fp=M.fingerprint(read(options.crash_log or M.CRASH_LOG))
  if fp==remembered or not options.write then return false end
  return pcall(options.write,persist..'/'..M.STATE,require('canon').encode(require('canon').object({crash_fp=fp})))
end

-- CLI for the init script: `lua boot_cause.lua shutdown-reason` prints planned-reboot or reboot (never fails).
if arg and arg[0] and string.find(arg[0],'boot_cause%.lua$') and arg[1]=='shutdown-reason' then
  local reason='reboot'
  pcall(function()
    local cursor=require('uci').cursor()
    local timer={enable=cursor:get('gl_timer','reboot','enable'),hour=cursor:get('gl_timer','reboot','hour'),
      min=cursor:get('gl_timer','reboot','min'),week=cursor:get('gl_timer','reboot','week')}
    if type(timer.week)=='table' then timer.week=table.concat(timer.week,' ') end
    local t=os.date('*t')
    reason=M.shutdown_reason(timer,t.wday-1,t.hour,t.min)
  end)
  io.write(reason,'\n')
end

return M
