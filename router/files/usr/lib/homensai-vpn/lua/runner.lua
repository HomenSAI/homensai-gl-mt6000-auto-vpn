-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- runner.lua: the router side of every external call of instant_switch.lua (agent.command/atomic_json
-- counterpart). Tests replace the whole table with fakes.
--
-- Security rule: no shell line is ever built from data. Commands are the constants below; data goes
-- through a pipe (iptables-restore, sha256sum) or through a file we have just written in our RAM
-- directory (conntrack mark, uci batch). The only variable part of a line is a path we chose
-- (canon.safe_directory + canon.unique names).
-- Lua 5.1 facts: io.popen():close() does not return the exit status (statuses are echoed to a marker or a
-- file of ours); os.execute() returns the raw wait status (0 = success).
local canon=require('canon')
local control=require('control')

local M={}
M.RUNTIME='/var/run/homensai-vpn'
M.MAX_OUTPUT=2*1024*1024  -- agent.command(): oversize command response

local Refused={}
Refused.__index=Refused
Refused.__tostring=function(e) return e.code end
M.Refused=Refused
local function refuse(code,detail) error(setmetatable({code=code,detail=detail},Refused),0) end
function M.is_refused(e) return type(e)=='table' and getmetatable(e)==Refused end

function M.configure(options)
  if options.runtime then
    if not canon.safe_directory(options.runtime) then error('runner: unsafe runtime directory',2) end
    M.RUNTIME=options.runtime;canon.configure({runtime=options.runtime});control.RUNTIME=options.runtime
  end
end

local have_timeout=nil
local function bounded(line)
  if have_timeout==nil then have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0 end
  return have_timeout and ('timeout 5 '..line) or line
end
-- Children never keep the control lock alive: close the held descriptor in them.
local function unlocked(line)
  local fd=control.held_fd()
  if fd then return line..' '..fd..'>&-' end
  return line
end

M.COMMANDS={
  uci_show='uci show route_policy',
  uci_names='uci -X show route_policy',
  iptables_save='iptables-save -t mangle',
}

local MARKER='__HOMENSAI_RC__'
-- Output of one of M.COMMANDS; raises COMMAND-FAILED on a non-zero exit.
function M.capture(name)
  local line=M.COMMANDS[name]
  if not line then error('runner: unknown command '..tostring(name),2) end
  local p=io.popen(unlocked(bounded(line))..' 2>/dev/null; echo "'..MARKER..'$?"','r')
  if not p then refuse('COMMAND-FAILED',name) end
  local out=p:read('*a');p:close()
  local body,rc=string.match(out,'^(.*)'..MARKER..'(%d+)\n$')
  if not body or rc~='0' then refuse('COMMAND-FAILED',name..' exit '..tostring(rc)) end
  if #body>M.MAX_OUTPUT then refuse('NATIVE-SYSTEM-001','oversize command response') end
  return body
end

local function status_file(name) return M.RUNTIME..'/.'..name..'-'..canon.unique()..'.status' end
local function read_status(path)
  local f=io.open(path,'r');local text=f and f:read('*l');if f then f:close() end
  os.remove(path)
  return text
end

-- iptables-restore --noflush with the payload on stdin (no rules file on disk).
function M.restore(payload)
  local path=status_file('restore')
  local p=io.popen(unlocked(bounded('iptables-restore --noflush'))..' >/dev/null 2>&1; echo $? >'..path,'w')
  if not p then refuse('COMMAND-FAILED','iptables-restore') end
  p:write(payload);p:close()
  local status=read_status(path)
  if status~='0' then refuse('COMMAND-FAILED','iptables-restore exit '..tostring(status)) end
  return true
end

-- conntrack -D -m <mark>/0xf000: the mark (validated) is read from our file by the shell, never parsed.
function M.conntrack_delete(mark)
  if type(mark)~='string' or not string.find(mark,'^0x[0-9a-f]+$') or #mark>10 then refuse('FAST-MARK') end
  local path=M.RUNTIME..'/.conntrack-'..canon.unique()..'.mark'
  local f=assert(io.open(path,'wb'));f:write(mark);f:close()
  local status=os.execute(unlocked(bounded('conntrack -D -m "$(cat '..path..')/0xf000"'))..' >/dev/null 2>&1')
  os.remove(path)
  return status==0
end

-- libuci cursor when libuci-lua is installed (no process); nil otherwise.
function M.uci_cursor()
  local ok,uci=pcall(require,'uci')
  if ok and type(uci)=='table' and uci.cursor then return uci.cursor() end
  return nil
end

-- Fallback writer without libuci: `uci batch` reads our file (section names already validated).
function M.uci_batch(lines)
  local path=M.RUNTIME..'/.uci-'..canon.unique()..'.batch'
  local f=assert(io.open(path,'wb'));f:write(table.concat(lines,'\n'),'\n');f:close()
  local status=os.execute(unlocked(bounded('uci batch <'..path))..' >/dev/null 2>&1')
  os.remove(path)
  if status~=0 then refuse('POLICY-REORDER-UNVERIFIED') end
  return true
end

-- Monotonic seconds: CLOCK_BOOTTIME from /proc/uptime (10 ms steps; equal to time.monotonic() on a router
-- that never suspends - the dry run prints both).
function M.clock()
  local f=assert(io.open('/proc/uptime','r'));local text=f:read('*l');f:close()
  return tonumber(string.match(text,'^([0-9.]+)'))
end
-- Wall seconds like time.time(): microseconds with nixio, whole seconds without it.
function M.wall()
  local ok,nixio=pcall(require,'nixio')
  if ok and type(nixio)=='table' and nixio.gettimeofday then local s,us=nixio.gettimeofday();return s+us/1e6 end
  return os.time()
end

M.lock=control.lock
M.require_revision=control.require_revision
function M.fenced(expected,fn) return control.fenced(expected,fn,M.RUNTIME) end
function M.sha256(text) return canon.sha256(text) end

------------------------------------------------------------------------------------------------------
-- files: journal_read / atomic_json rules
------------------------------------------------------------------------------------------------------
M.fs={}
function M.fs.read(path)
  local f=io.open(path,'rb')
  if not f then return nil end
  local text=f:read('*a');f:close()
  return text
end
-- A symlink, a non-file or more than 1 MB is refused (journal_read). Without nixio only the size is known;
-- the directory is root-only (0700) and rename() never follows a symlink at the destination.
function M.fs.unsafe(path)
  local ok,fs=pcall(require,'nixio.fs')
  if ok and type(fs)=='table' and fs.lstat then
    local st=fs.lstat(path)
    if not st then return false end
    return st.type~='reg' or st.size>1024*1024
  end
  local f=io.open(path,'rb')
  if not f then return false end
  local size=f:seek('end');f:close()
  return size==nil or size>1024*1024
end
-- atomic_json(): unique temp name in the same directory, mode 0600, flush, fsync, rename.
-- Lua io has no fsync: nixio's File:sync() when present, otherwise `sync` (measure on the device).
function M.fs.write_atomic(path,text)
  local directory,name=string.match(path,'^(.*)/([^/]+)$')
  if not canon.safe_directory(directory) or not string.find(name,'^[A-Za-z0-9_.-]+$') then error('runner: unsafe path',0) end
  local pending=directory..'/.'..name..'.'..canon.unique()..'.pending'
  local f=io.open(pending,'wb')
  if not f then
    os.execute('mkdir -p '..directory..' && chmod 700 '..directory)
    f=assert(io.open(pending,'wb'))
  end
  assert(f:write(text));assert(f:flush());f:close()
  local synced=false
  local ok,nixio=pcall(require,'nixio')
  local ok2,nfs=pcall(require,'nixio.fs')
  if ok and ok2 and type(nixio)=='table' and nixio.open and type(nfs)=='table' and nfs.chmod then
    synced=pcall(function()
      assert(nfs.chmod(pending,'rw-------'))
      local h=assert(nixio.open(pending,'r'));assert(h:sync());h:close()  -- fsync of the inode
    end)
  end
  if not synced then os.execute('chmod 600 '..pending..' && sync') end
  local renamed,err=os.rename(pending,path)
  if not renamed then os.remove(pending);error(err,0) end
end

-- Resident memory of this process (kB) and the Lua heap.
function M.memory()
  local result={}
  local f=io.open('/proc/self/status','r')
  if f then
    for line in f:lines() do
      local key,value=string.match(line,'^([A-Za-z]+):%s+(%d+) kB')
      if key=='VmRSS' or key=='VmHWM' or key=='RssAnon' or key=='RssFile' then result[key]=tonumber(value) end
    end
    f:close()
  end
  result.lua_heap_kb=math.floor(collectgarbage('count'))
  return result
end

return M
