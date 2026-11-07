-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- maintenance.lua: the package maintenance marker (plan item 54, audit F-16/F-17). Python twin: maintenance.py (the
-- same rules; shared cases router/tests/maintenance_cases.json).
--
-- The package hooks (lifecycle_guard.py in prerm/preinst/postinst) write PERSIST/maintenance.json under the control lock
-- before they assess the state and remove it when the package operation ends. While it is active a Start, a manual
-- switch, the failure test and the speed test are refused with MAINTENANCE-IN-PROGRESS and the supervisor begins no new
-- session; Stop is never refused and a running recovery or rollback is never blocked. Active only within the same boot
-- (boot_id) and for at most LIMIT s of uptime after its last write; anything else is stale: it blocks nothing, the page
-- shows MAINTENANCE-INTERRUPTED and the service start (`lua maintenance.lua clear-stale`, init.d) moves it into
-- upgrade-result.json.
local canon=require('canon')
local NULL=canon.null

local M={}
M.MARKER='maintenance.json'
M.RESULT='upgrade-result.json'
M.LIMIT=900
M.SKEW=60
M.ACTIONS={install=true,upgrade=true,remove=true}
M.ACTIVE='MAINTENANCE-IN-PROGRESS'
M.STALE='MAINTENANCE-INTERRUPTED'

-- a finite number >= 0 (canon floats included); nil otherwise
local function number(v)
  local x=canon.number(v)
  if x==nil or x~=x or x==math.huge or x==-math.huge or x<0 then return nil end
  return x
end
M.number=number

local BOOT='^%x%x%x%x%x%x%x%x%-%x%x%x%x%-%x%x%x%x%-%x%x%x%x%-%x%x%x%x%x%x%x%x%x%x%x%x$'
local function boot(v)
  if type(v)=='string' and string.find(v,BOOT) and not string.find(v,'%u') then return v end
  return nil
end

local function view(marker,state,code,reason)
  local since=number(marker.time)
  local out=canon.object({state=state,code=code,action=marker.action,since=since and canon.float(since) or NULL})
  if reason then out.reason=reason end
  return out
end

-- marker: the decoded file, nil when absent, false when unreadable. boot: this boot's id or nil; uptime: seconds since
-- boot or nil; now: wall clock. The public view {state=none|active|stale, ...} (maintenance.classify).
function M.classify(marker,current_boot,uptime,now)
  if marker==nil or marker==NULL then return canon.object({state='none'}) end
  if not canon.is_object(marker) or type(marker.action)~='string' or not M.ACTIONS[marker.action] then
    return canon.object({state='stale',code=M.STALE,action=NULL,since=NULL,reason='invalid'})
  end
  local marked,here=boot(marker.boot_id),boot(current_boot)
  if marked and here then
    if marked~=here then return view(marker,'stale',M.STALE,'reboot') end
    local at,up=number(marker.uptime),number(uptime)
    if at and up then
      local age=up-at
      if 0<=age and age<=M.LIMIT then return view(marker,'active',M.ACTIVE) end
      return view(marker,'stale',M.STALE,age>M.LIMIT and 'timeout' or 'invalid')
    end
  end
  -- no usable boot id or uptime: the wall clock bounds it
  local since,wall=number(marker.time),number(now)
  if since and wall then
    local age=wall-since
    if -M.SKEW<=age and age<=M.LIMIT then return view(marker,'active',M.ACTIVE) end
    return view(marker,'stale',M.STALE,'timeout')
  end
  return view(marker,'stale',M.STALE,'invalid')
end

-- lstat(path) -> the file type ('reg', 'lnk', 'dir', ...) without following a symlink, or nil (absent / no way to
-- tell): nixio.fs.lstat (LuCI's nixio is on every supported router), else sys.lstat (busybox stat). Replaceable in tests.
function M.lstat(path)
  local ok,nfs=pcall(require,'nixio.fs')
  if ok and type(nfs)=='table' and nfs.lstat then
    local st=nfs.lstat(path)
    return st and st.type or nil
  end
  local sok,sys=pcall(require,'sys')
  if sok and type(sys)=='table' and sys.lstat then
    local st=sys.lstat(path)
    return st and st.type or nil
  end
  return nil
end

-- read(path) -> text|nil (pcall-safe). nil = absent, false = unreadable or too big.
-- IR-06 (integration review 07.11.2026): a symlink (or any non-regular file) in the marker's place is unreadable
-- (false: stale 'invalid', never followed, whatever reader is passed), exactly as maintenance.read_marker; clear_stale
-- then reports it and removes the link itself. Before, Lua followed it and could call it active while Python called it
-- stale. Shared case: maintenance_cases.json "files".
function M.read_marker(read,persist)
  local path=persist..'/'..M.MARKER
  local lok,kind=pcall(M.lstat,path)
  if not lok or (kind~=nil and kind~='reg') then return false end
  local ok,text=pcall(read,path)
  if not ok then return false end
  if text==nil then return nil end
  if type(text)~='string' or #text>4096 then return false end
  local dok,value=pcall(canon.decode,text)
  if not dok then return false end
  return value
end

function M.boot_id(read,proc)
  local ok,text=pcall(read,(proc or '/proc')..'/sys/kernel/random/boot_id')
  if not ok or type(text)~='string' then return nil end
  return boot((string.gsub(text,'%s+$','')))
end

function M.uptime(read,proc)
  local ok,text=pcall(read,(proc or '/proc')..'/uptime')
  if not ok or type(text)~='string' then return nil end
  return number(tonumber(string.match(text,'^%s*([0-9.]+)')))
end

function M.current(read,persist,now,proc)
  return M.classify(M.read_marker(read,persist),M.boot_id(read,proc),M.uptime(read,proc),now)
end

-- MAINTENANCE-IN-PROGRESS while a package operation runs, else nil. Never raises.
function M.blocker(read,persist,now,proc)
  local ok,v=pcall(M.current,read,persist,now,proc)
  if ok and v.state=='active' then return M.ACTIVE end
  return nil
end

-- status.maintenance: NULL without a marker, else the view
function M.public(read,persist,now,proc)
  local ok,v=pcall(M.current,read,persist,now,proc)
  if not ok or v.state=='none' then return NULL end
  return v
end

local function read_file(path)
  local f=io.open(path,'rb')
  if not f then return nil end
  local s=f:read('*a');f:close()
  return s
end
M.read_file=read_file

-- Service start: a stale marker becomes upgrade-result.json (MAINTENANCE-INTERRUPTED) and is removed; an active one
-- stays. Returns the record or nil; raises on a failed write (the marker then stays, it blocks nothing).
function M.clear_stale(persist,now,read,proc)
  read=read or read_file
  local v=M.current(read,persist,now,proc)
  if v.state~='stale' then return nil end
  local record=canon.object({code=M.STALE,reason=v.reason,action=(v.action~=NULL and v.action) or '',['from']='',to='',
    since=v.since,time=canon.float(now)})
  local temporary=persist..'/.'..M.RESULT..'.new'
  local f=assert(io.open(temporary,'wb'))
  assert(f:write(canon.encode(record)))
  f:flush();f:close()
  assert(os.rename(temporary,persist..'/'..M.RESULT))
  assert(os.remove(persist..'/'..M.MARKER))
  return record
end

if arg and type(arg[0])=='string' and (arg[0]=='maintenance.lua' or string.find(arg[0],'/maintenance%.lua$'))
   and arg[1]=='clear-stale' and arg[2]==nil then
  local ok,record=pcall(M.clear_stale,'/etc/homensai-vpn',os.time())
  if not ok then io.stderr:write('MAINTENANCE-CLEAR-FAILED\n');os.exit(1) end
  if record then print(M.STALE..' '..record.reason..' '..record.action) end
  os.exit(0)
end

return M
