-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- control.lua: auto_control.control_lock and native_switch.require_control_revision for the Lua core.
--
-- Python's control_lock is flock(2) on /var/run/homensai-vpn/auto-control.lock. nixio's File:lock() is
-- lockf(3), i.e. POSIX record locks, which do NOT exclude flock(2) holders, so it cannot be used. The lock
-- is taken with busybox flock(1) on the descriptor this Lua process holds open: a flock belongs to the open
-- file description, so it stays held after flock(1) exits and is released when Lua closes the file -
-- exactly like `os.close(fd)` in Python. Tests check mutual exclusion against the real Python lock.
-- Every command line here is constant apart from the configured directory, which must pass
-- canon.safe_directory (absolute, [A-Za-z0-9_./-], no '..').
local canon=require('canon')

local M={}
M.RUNTIME='/var/run/homensai-vpn'

local Refused={}
Refused.__index=Refused
Refused.__tostring=function(e) return e.code end
M.Refused=Refused
local function refuse(code) error(setmetatable({code=code},Refused),0) end
function M.is_refused(e) return type(e)=='table' and getmetatable(e)==Refused end

local held=nil  -- descriptor number of the held lock (children must not inherit it)
function M.held_fd() return held end

local function directory_of(directory)
  directory=directory or M.RUNTIME
  if not canon.safe_directory(directory) then refuse('CONTROL-LOCK-UNAVAILABLE') end
  local ok,nixio=pcall(require,'nixio.fs')
  if ok and type(nixio)=='table' and nixio.lstat then  -- Python refuses a symlinked control directory
    local st=nixio.lstat(directory)
    if st and st.type=='lnk' then refuse('CONTROL-LOCK-UNAVAILABLE') end
  end
  return directory
end

-- `-ef` compares device and inode, so /var/run -> /tmp/run does not matter.
local function flock_inherited(path)
  local p=io.popen('for f in /proc/$$/fd/*; do if [ "$f" -ef '..path..' ]; then '..
                   'flock -x "${f##*/}" && echo "${f##*/}"; exit 0; fi; done; exit 97','r')
  if not p then return nil end
  local out=p:read('*a');p:close()
  return tonumber(string.match(out,'^(%d+)\n$'))
end

function M.lock(fn,directory)
  if held then refuse('CONTROL-LOCK-REENTRY') end  -- a second description of the same file would deadlock
  directory=directory_of(directory)
  local path=directory..'/auto-control.lock'
  local file=io.open(path,'a')
  if not file then  -- directory.mkdir(mode=0o700, parents=True, exist_ok=True), only when missing
    os.execute('mkdir -p '..directory..' && chmod 700 '..directory)
    file=io.open(path,'a')
  end
  if not file then refuse('CONTROL-LOCK-UNAVAILABLE') end
  local fd=flock_inherited(path)
  if not fd then file:close();refuse('CONTROL-LOCK-UNAVAILABLE') end
  held=fd
  local results={pcall(fn)}
  held=nil
  file:close()  -- releases the flock
  if not results[1] then error(results[2],0) end
  return unpack(results,2)
end

-- require_control_revision(expected): {"revision": <32 hex>} exactly; Stop rotates it.
function M.require_revision(expected,directory)
  if type(expected)~='string' or #expected~=32 or not string.find(expected,'^[a-f0-9]+$') then refuse('CLIENT-STOP') end
  local f=io.open(directory_of(directory)..'/auto-control-revision.json','rb')
  if not f then refuse('CLIENT-STOP') end
  local text=f:read('*a');f:close()
  local ok,record=pcall(canon.decode,text)
  if not ok or not canon.is_object(record) then refuse('CLIENT-STOP') end
  local keys=0
  for _ in pairs(record) do keys=keys+1 end
  if keys~=1 or record.revision~=expected then refuse('CLIENT-STOP') end
end

-- Lock, check the revision, then fn(): every durable or kernel write of the Lua core goes through here.
function M.fenced(expected,fn,directory)
  return M.lock(function()
    M.require_revision(expected,directory)
    return fn()
  end,directory)
end

return M
