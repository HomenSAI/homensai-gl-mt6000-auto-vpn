-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- durable.lua: the one file-write primitive of the Lua line (2.0.0-lua) for state that must survive a power cut
-- at any moment, and the recovery helpers that go with it (POWER-CUT-INTEGRITY-2026-10-31.ru.md).
--
-- write(path, text): the same steps as agent.atomic_json / native_history.atomic in Python:
--   1. a unique temporary file '.<name>.<unique>.pending' in the SAME directory (rename never crosses a file system)
--   2. write all bytes, flush, close; mode 0600
--   3. fsync of the temporary file (nixio File:sync on a read descriptor; Linux fsync works on any descriptor)
--   4. rename() over the target: readers see the old or the new file, never a mix
--   5. fsync of the directory (nixio.open(dir,'r'):sync()): the rename itself is on flash before write() returns
-- Without nixio steps 3+5 are one `sync` (whole system, slower; measured only on a router without nixio).
-- A power cut before 4 leaves the old target plus a leftover .pending (removed by sweep() at the next start);
-- between 4 and 5 the target is the old or the new version, both complete. Every reader of a file written here
-- therefore only ever sees a complete version - the readers still treat a damaged file as a known state
-- (flash corruption, a file written by another tool, an interrupted opkg).
-- write(path, text, {sync=false}) and any path in RAM (/tmp, /var/run: tmpfs): the same rename, no fsync.
--
-- Every system call goes through M.ops so the PC tests can record the order of the steps and inject failures.
local canon=require('canon')

local M={}
M.PENDING_PATTERN='^%.[A-Za-z0-9_.-]+%.pending$'
M.SWEEP_AGE=120          -- a writer keeps its .pending for well under a second
M.QUARANTINE_DIR='quarantine'
M.QUARANTINE_LIMIT=8     -- damaged copies kept per directory (oldest removed first)
M.QUARANTINE_MAX_BYTES=256*1024

local okn,nixio=pcall(require,'nixio')
if not (okn and type(nixio)=='table') then nixio=nil end
local okf,nfs=pcall(require,'nixio.fs')
if not (okf and type(nfs)=='table') then nfs=nil end

local function default_ops()
  local ops={}
  function ops.open_write(path) return io.open(path,'wb') end
  function ops.mkdir(path)
    if nfs and nfs.mkdir and nfs.mkdir(path,'700')~=nil then return true end
    return os.execute('mkdir -p '..path..' && chmod 700 '..path)==0  -- path checked by split(): [A-Za-z0-9_./-] only
  end
  function ops.chmod600(path)
    if nfs and nfs.chmod then return nfs.chmod(path,'rw-------')~=nil end
    return os.execute('chmod 600 '..path)==0
  end
  -- fsync(path): true when the inode is on flash; false when this router cannot tell (no nixio)
  function ops.fsync(path)
    if not (nixio and nixio.open) then return false end
    local ok,res=pcall(function()
      local h=nixio.open(path,'r')
      if not h then return false end
      local s=h:sync();h:close()
      return s and true or false
    end)
    return ok and res==true
  end
  ops.fsync_dir=ops.fsync  -- open(dir, O_RDONLY) + fsync: the directory entries (rename, create, unlink)
  function ops.sync_all() return os.execute('sync')==0 end
  function ops.rename(a,b) return os.rename(a,b) end
  function ops.remove(path) return os.remove(path) end
  function ops.dir(path)
    if not (nfs and nfs.dir) then return nil end
    local ok,iter=pcall(nfs.dir,path)
    if not ok or not iter then return nil end
    local out={}
    for name in iter do if name~='.' and name~='..' then out[#out+1]=name end end
    return out
  end
  function ops.lstat(path)
    if not (nfs and nfs.lstat) then return nil end
    local st=nfs.lstat(path)
    if not st then return nil end
    return {type=st.type,size=st.size,mtime=st.mtime}
  end
  function ops.now() return os.time() end
  return ops
end
M.ops=default_ops()
M.default_ops=default_ops
M.have_nixio=nixio~=nil and nfs~=nil

local function split(path)
  local directory,name=string.match(path or '','^(.*)/([^/]+)$')
  if not canon.safe_directory(directory) or not name or not string.find(name,'^[A-Za-z0-9_.-]+$') then
    error('durable: unsafe path',0)
  end
  return directory,name
end
M.split=split

-- sync_directory(directory): the rename/create/unlink inside it is on flash; false when it could not be proved
function M.sync_directory(directory)
  local ok,res=pcall(M.ops.fsync_dir,directory)
  return ok and res==true
end

-- RAM file systems on OpenWrt (/var is a link to /tmp): an fsync there is a no-op, so it is skipped
M.RAM_PREFIXES={'/tmp/','/var/run/','/var/','/run/','/dev/shm/'}
function M.in_ram(path)
  for _,prefix in ipairs(M.RAM_PREFIXES) do if string.sub(path,1,#prefix)==prefix then return true end end
  return false
end

-- write(path, text[, opts]) -> true; raises on any failure (the target is then unchanged, no .pending left).
-- opts.sync: true forces the fsync steps, false skips them; default: fsync unless the path is in RAM.
function M.write(path,text,opts)
  if type(text)~='string' then error('durable: text',0) end
  local sync
  if opts and opts.sync~=nil then sync=opts.sync==true else sync=not M.in_ram(path or '') end
  local ops=M.ops
  local directory,name=split(path)
  local pending=directory..'/.'..name..'.'..canon.unique()..'.pending'
  local f=ops.open_write(pending)
  local created_directory=false
  if not f then
    created_directory=ops.mkdir(directory)
    f=ops.open_write(pending)
    if not f then error('durable: cannot create '..pending,0) end
  end
  local ok,err=pcall(function()
    assert(f:write(text));assert(f:flush())
    f:close();f=nil
    assert(ops.chmod600(pending),'chmod')
    if sync and not ops.fsync(pending) then
      if not ops.sync_all() then error('durable: fsync unavailable',0) end
    end
  end)
  if not ok then
    if f then pcall(f.close,f) end
    ops.remove(pending)
    error(err,0)
  end
  local renamed,rerr=ops.rename(pending,path)
  if not renamed then ops.remove(pending);error(rerr or 'durable: rename',0) end
  if sync then
    if not M.sync_directory(directory) then ops.sync_all() end
    if created_directory then M.sync_directory(string.match(directory,'^(.*)/[^/]+$') or '/') end
  end
  return true
end

-- sweep(directory[, max_age[, now]]) -> number removed: leftover '.<name>.<x>.pending' files of an interrupted
-- write (a power cut between steps 1 and 4), from this module or Python's mkstemp writers (same pattern). Only
-- files whose mtime is further than max_age from now - in either direction, the clock of a router without a
-- battery may jump back at boot - so a writer that is running right now never loses its file.
function M.sweep(directory,max_age,now)
  local ops=M.ops
  max_age=max_age or M.SWEEP_AGE
  now=now or ops.now()
  local names=ops.dir(directory)
  if not names then return 0 end
  local removed=0
  for _,name in ipairs(names) do
    if string.find(name,M.PENDING_PATTERN) then
      local path=directory..'/'..name
      local st=ops.lstat(path)
      if st and st.type=='reg' and type(st.mtime)=='number' and math.abs(now-st.mtime)>max_age then
        if ops.remove(path) then removed=removed+1 end
      end
    end
  end
  if removed>0 then M.sync_directory(directory) end
  return removed
end

-- damage(text) -> nil for a plausible text, else 'EMPTY' | 'ZERO-FILLED' | 'BINARY': the kind of a file a power
-- cut on a non-atomic writer leaves (a zero-length or zero-filled file is the classic one). Used for the log line.
function M.damage(text)
  if text==nil then return nil end
  if #text==0 then return 'EMPTY' end
  if not string.find(text,'[^%z]') then return 'ZERO-FILLED' end
  if string.find(text,'%z') then return 'BINARY' end
  return nil
end

-- quarantine(path, text, code[, fs]) -> the copy's path or nil. Keeps the damaged bytes for the maintainer
-- (<dir>/quarantine/<name>.<sha8>.damaged, 0600, at most QUARANTINE_LIMIT per directory, each at most
-- QUARANTINE_MAX_BYTES); the same bytes are kept once. fs: the caller's {read, write_atomic} (runner.fs on the
-- router, the fake in tests); default this module. Never raises: evidence must not break recovery.
function M.quarantine(path,text,code,fs)
  local ok,result=pcall(function()
    if type(text)~='string' then return nil end
    local directory,name=split(path)
    local qdir=directory..'/'..M.QUARANTINE_DIR
    local body=string.sub(text,1,M.QUARANTINE_MAX_BYTES)
    local copy=qdir..'/'..name..'.'..string.sub(canon.sha256(body),1,8)..'.damaged'
    local exists
    if fs and fs.read then exists=fs.read(copy)~=nil else exists=M.ops.lstat(copy)~=nil end
    if exists then return copy end
    local kept={}
    for _,n in ipairs(M.ops.dir(qdir) or {}) do
      if string.find(n,'%.damaged$') then
        local st=M.ops.lstat(qdir..'/'..n)
        kept[#kept+1]={name=n,mtime=st and st.mtime or 0}
      end
    end
    table.sort(kept,function(a,b) if a.mtime~=b.mtime then return a.mtime<b.mtime end;return a.name<b.name end)
    for i=1,#kept-M.QUARANTINE_LIMIT+1 do M.ops.remove(qdir..'/'..kept[i].name) end
    if fs and fs.write_atomic then fs.write_atomic(copy,body) else M.write(copy,body) end
    M.log((code or 'STATE-FILE-DAMAGED')..' '..name..' '..(M.damage(text) or 'UNPARSEABLE')..' '..#text..' bytes; copy kept in '..M.QUARANTINE_DIR)
    return copy
  end)
  if ok then return result end
  return nil
end

-- log(line): one system log line (logread -e homensai); the text is ours (codes, file names, numbers) and is
-- passed through a quoted argument without its own quotes.
function M.log(line)
  local text=string.gsub(tostring(line),"[^%w %.%,%:%;%-%_%/%(%)]",'')
  pcall(os.execute,"logger -t homensai-vpn '"..string.sub(text,1,400).."' >/dev/null 2>&1")
end

return M
