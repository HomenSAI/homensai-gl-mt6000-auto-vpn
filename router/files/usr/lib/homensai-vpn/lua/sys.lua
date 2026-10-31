-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- sys.lua: every router read and command of backend.lua / platform.lua / net.lua / recovery.lua (2.0.0-lua
-- line). Tests replace the whole table with a fake of the same shape (tests/lua/backend_fake.lua).
--
-- Commands: exec(argv) single-quotes every argument and refuses an argument with a quote, NUL or newline, so no
-- shell line is ever built from unquoted data; most arguments are constants or names already checked against
-- ^[A-Za-z0-9_]{1,15}$ by the caller. Input goes through a file of ours in the RAM directory. A child never
-- inherits the held control-lock descriptor (control.held_fd), like Python's close_fds.
-- In-process where the router allows it: libubus (ubus calls), libuci (cursors), nixio.fs (stat, dir) and the
-- packaged Lua helpers (native_policy.lua, inventory.lua, pair network read) run in this process with print()
-- captured, so the JSON text is exactly what Python's json.loads(command(['lua',...])) reads.
local canon=require('canon')
local control=require('control')
local runner=require('runner')

local M={}
M.RUNTIME=runner.RUNTIME
M.LIB='/usr/lib/homensai-vpn'

local function refuse(code) error(setmetatable({code=code,value_error=true},require('auto_control').Refused),0) end

local okfs,nfs=pcall(require,'nixio.fs')
if not (okfs and type(nfs)=='table') then nfs=nil end
local okn,nixio=pcall(require,'nixio')
if not (okn and type(nixio)=='table') then nixio=nil end
M.have_nixio=nfs~=nil

function M.wall() return runner.wall() end
function M.clock() return runner.clock() end
function M.sleep(seconds)
  if seconds<=0 then return end
  if nixio and nixio.nanosleep then nixio.nanosleep(math.floor(seconds),math.floor((seconds%1)*1e9))
  else os.execute('sleep '..string.format('%.1f',seconds)) end
end

------------------------------------------------------------------------------------------------------
-- files
------------------------------------------------------------------------------------------------------
-- read(path, maximum): nil when missing; raises when larger than maximum
function M.read(path,maximum)
  local f=io.open(path,'rb')
  if not f then return nil end
  local text=f:read(maximum and (maximum+1) or '*a') or ''
  f:close()
  if maximum and #text>maximum then refuse('OVERSIZE-FILE') end
  return text
end

local STAT_TYPES={['8']='reg',['4']='dir',a='lnk',['2']='chr',['6']='blk',['1']='fifo',c='sock'}
-- permission bits (incl. setuid/setgid/sticky) from nixio's modestr ('rwsr-x--T'); nil when it is malformed
local function modestr_bits(text)
  if type(text)~='string' or #text~=9 then return nil end
  local bits=0
  local function at(i) return string.sub(text,i,i) end
  local weights={256,128,64,32,16,8,4,2,1}
  for i=1,9 do
    local c=at(i)
    local want=(i%3==1) and 'r' or ((i%3==2) and 'w' or 'x')
    if c==want then bits=bits+weights[i]
    elseif i%3==0 and (c=='s' or c=='t') then bits=bits+weights[i]+(i==3 and 2048 or (i==6 and 1024 or 512))
    elseif i%3==0 and (c=='S' or c=='T') then bits=bits+(i==3 and 2048 or (i==6 and 1024 or 512))
    elseif c~='-' then return nil end
  end
  return bits
end
-- mode from nixio: modestr, cross-checked with modedec (the octal digits of the 9 permission bits written as
-- a decimal number); any disagreement gives nil, which every caller treats as "not verified"
local function nixio_mode(st)
  local bits=modestr_bits(st.modestr)
  if bits==nil or type(st.modedec)~='number' then return nil end
  local d,m,place=st.modedec,0,1
  while d>0 do m=m+(d%10)*place;d=math.floor(d/10);place=place*8 end
  if m%512~=bits%512 then return nil end
  return bits
end
M.modestr_bits=modestr_bits
-- lstat(path) -> {type,size,ino,dev,mtime,uid,mode} (mode: permission bits incl. setuid/sticky) or nil
function M.lstat(path)
  if nfs and nfs.lstat then
    local st=nfs.lstat(path)
    if not st then return nil end
    return {type=st.type,size=st.size,ino=st.ino,dev=st.dev,mtime=st.mtime,ctime=st.ctime,uid=st.uid,mode=nixio_mode(st)}
  end
  local rc,out=M.exec({'stat','-c','%f %s %i %d %Y %Z %u',path})
  if rc~=0 then return nil end
  local raw,size,ino,dev,mtime,ctime,uid=string.match(out,'^(%x+) (%d+) (%d+) (%d+) (%d+) (%d+) (%d+)')
  if not raw then return nil end
  local bits=tonumber(raw,16)
  local kind=STAT_TYPES[string.format('%x',math.floor(bits/4096))] or 'other'
  return {type=kind,size=tonumber(size),ino=tonumber(ino),dev=tonumber(dev),mtime=tonumber(mtime),ctime=tonumber(ctime),uid=tonumber(uid),mode=bits%4096}
end
-- lstat_exact(path): the mode/uid checks of rtp_boot and recovery archives. The MT3000 (GL 4.11) has no
-- stat(1), so this is nixio's lstat with the mode read from modestr and cross-checked against modedec;
-- without nixio it is busybox stat(1).
function M.lstat_exact(path)
  return M.lstat(path)
end
function M.euid()
  local rc,out=M.exec({'id','-u'})
  return rc==0 and tonumber(string.match(out,'^(%d+)')) or nil
end
-- stat(path): follows a symlink
function M.stat(path)
  if nfs and nfs.stat then
    local st=nfs.stat(path)
    if not st then return nil end
    return {type=st.type,size=st.size,ino=st.ino,dev=st.dev,mtime=st.mtime,ctime=st.ctime,uid=st.uid}
  end
  local rc,out=M.exec({'stat','-L','-c','%f %s %i %d %Y %Z %u',path})
  if rc~=0 then return nil end
  local raw,size,ino,dev,mtime,ctime,uid=string.match(out,'^(%x+) (%d+) (%d+) (%d+) (%d+) (%d+) (%d+)')
  if not raw then return nil end
  local kind=STAT_TYPES[string.format('%x',math.floor(tonumber(raw,16)/4096))] or 'other'
  return {type=kind,size=tonumber(size),ino=tonumber(ino),dev=tonumber(dev),mtime=tonumber(mtime),ctime=tonumber(ctime),uid=tonumber(uid)}
end
-- key(path): a cheap change fingerprint (inode, size, times); 'absent' when missing
function M.key(path)
  local st=M.lstat(path)
  if not st then return 'absent' end
  return table.concat({tostring(st.type),tostring(st.ino),tostring(st.size),tostring(st.mtime),tostring(st.ctime)},':')
end
function M.exists(path) return M.stat(path)~=nil end
-- dir(path): entry names (without . and ..) or nil
function M.dir(path)
  if nfs and nfs.dir then
    local ok,iter=pcall(nfs.dir,path)
    if not ok or not iter then return nil end
    local out={}
    for name in iter do if name~='.' and name~='..' then out[#out+1]=name end end
    return out
  end
  local rc,text=M.exec({'ls','-1a',path})
  if rc~=0 then return nil end
  local out={}
  for name in string.gmatch(text,'[^\n]+') do if name~='.' and name~='..' then out[#out+1]=name end end
  return out
end
function M.remove(path) os.remove(path) end
function M.write_private(path,text)  -- 0600, our RAM directory only
  runner.fs.write_atomic(path,text)
end
-- nixio takes a mode only as an octal string ('700') or a symbolic one, never a number
local function octal(mode) return string.format('%o',mode) end
M.octal=octal
function M.mkdir(path,mode)
  if nfs and nfs.mkdir then local ok=nfs.mkdir(path,octal(mode or 448));return ok~=nil end
  return M.exec({'mkdir','-m',string.format('%o',mode or 448),path})==0
end
function M.rmdir(path) if nfs and nfs.rmdir then nfs.rmdir(path) else M.exec({'rmdir',path}) end end
function M.unique() return canon.unique() end
-- create path exclusively (O_EXCL, no symlink follow) with mode 0600 and fsync it; true when created
function M.create_exclusive(path,text)
  if nixio and nixio.open then
    -- nixio.open takes fopen-style strings only; O_CREAT|O_EXCL needs the numeric flags
    local f=nixio.open(path,nixio.open_flags('wronly','creat','excl'),octal(384))
    if not f then return false end
    if text and #text>0 then f:write(text) end
    f:sync();f:close()
    return true
  end
  if M.lstat(path) then return false end
  local f=io.open(path,'wb');if not f then return false end
  if text then f:write(text) end
  f:close();os.execute('chmod 600 '..path)
  return true
end

------------------------------------------------------------------------------------------------------
-- commands
------------------------------------------------------------------------------------------------------
-- descriptors a child must not inherit: the held control lock and the supervisor's native.lock
M.close_fds={}
local function closing()
  local parts={}
  local fd=control.held_fd()
  if fd then parts[#parts+1]=' '..fd..'>&-' end
  for _,x in ipairs(M.close_fds) do parts[#parts+1]=' '..string.format('%d',x)..'>&-' end
  return table.concat(parts)
end
local function quote(arg)
  if type(arg)~='string' or string.find(arg,"[%z\n']") then error('sys: unsafe command argument',0) end
  return "'"..arg.."'"
end
local have_timeout=nil
local MARKER='__HOMENSAI_SYS_RC__'
-- exec(argv, {timeout=seconds, input=text, max=bytes}) -> exit status, stdout
function M.exec(argv,opts)
  opts=opts or {}
  local parts={}
  for i,a in ipairs(argv) do parts[i]=quote(a) end
  local line=table.concat(parts,' ')
  if opts.timeout then
    if have_timeout==nil then have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0 end
    if have_timeout then line='timeout '..string.format('%d',math.floor(opts.timeout))..' '..line end
  end
  local input=nil
  if opts.input then
    input=M.RUNTIME..'/.sys-'..canon.unique()..'.in'
    local f=io.open(input,'wb')
    if not f then os.execute('mkdir -p '..M.RUNTIME..' && chmod 700 '..M.RUNTIME);f=assert(io.open(input,'wb')) end
    f:write(opts.input);f:close()
    line=line..' <'..input
  else
    line=line..' </dev/null'
  end
  line=line..closing()
  local p=io.popen(line..' 2>/dev/null; echo "'..MARKER..'$?"','r')
  local out=p and p:read('*a') or ''
  if p then p:close() end
  if input then os.remove(input) end
  local body,rc=string.match(out,'^(.*)'..MARKER..'(%d+)\n$')
  if not body then return 255,'' end
  if #body>(opts.max or 2*1024*1024) then refuse('NATIVE-SYSTEM-001') end
  return tonumber(rc),body
end
-- command(argv): stdout, or a refusal like CalledProcessError
function M.command(argv,opts)
  local rc,out=M.exec(argv,opts)
  if rc~=0 then refuse(opts and opts.code or 'COMMAND-FAILED') end
  return out
end
-- detached(line_id, value): the only background job, the guard release of one nft set generation
function M.guard_release(generation,seconds,table_name)
  if type(generation)~='string' or not string.find(generation,'^[0-9a-f]+$') or #generation~=8 then error('sys: generation',0) end
  if type(table_name)~='string' or not string.find(table_name,'^[A-Za-z0-9_]+$') then error('sys: table',0) end
  -- The job itself holds the quoted nft element '{ "br-lan" }' (as in Python), so it is passed to sh -c
  -- with each of its own quotes closed and reopened ('\''); quote() would refuse it.
  local job='sleep '..string.format('%d',seconds)..'; nft delete element inet '..table_name..' blocked_lan_'..generation..[[ '{ "br-lan" }' 2>/dev/null || :]]
  local word="'"..string.gsub(job,"'","'\\''").."'"
  local line='(setsid sh -c '..word..' || sh -c '..word..') </dev/null >/dev/null 2>&1'..closing()..' &'
  return os.execute(line)==0
end

------------------------------------------------------------------------------------------------------
-- ubus / uci / packaged Lua helpers in this process
------------------------------------------------------------------------------------------------------
local function to_canon(v)
  if type(v)~='table' then return v end
  if next(v)==nil then return canon.object({}) end
  local n=#v
  local count=0
  for _ in pairs(v) do count=count+1 end
  local out={}
  if n>0 and count==n then
    for i=1,n do out[i]=to_canon(v[i]) end
    return canon.array(out)
  end
  for k,x in pairs(v) do out[tostring(k)]=to_canon(x) end
  return canon.object(out)
end
M.to_canon=to_canon
local connection=nil
-- ubus(object, method): the reply (canon tables) or nil, like a failed `ubus call`
function M.ubus(object,method)
  local ok,ubus=pcall(require,'ubus')
  if ok and type(ubus)=='table' and ubus.connect then
    for _=1,2 do
      connection=connection or ubus.connect()
      if connection then
        local reply=connection:call(object,method,{})
        if reply~=nil then return to_canon(reply) end
        -- nil: no such object or a dead connection; retry once on a fresh connection
        pcall(function() connection:close() end);connection=nil
      end
    end
    return nil
  end
  local rc,out=M.exec({'ubus','call',object,method},{timeout=5})
  if rc~=0 then return nil end
  local dok,value=pcall(canon.decode,out)
  return dok and value or nil
end

function M.uci_cursor(confdir,savedir)
  local ok,uci=pcall(require,'uci')
  if not ok or type(uci)~='table' or not uci.cursor then return nil end
  if confdir then return uci.cursor(confdir,savedir) end
  return uci.cursor()
end

local compiled={}
-- stdin: what `lua -e <source>` would read on its standard input (NETWORK_WRITE reads its job with
-- io.read('*a')); the chunk sees it through its own io.read and never the daemon's stdin.
local function run_chunk(chunk,stdin)
  local out={}
  local pending=stdin
  local chunk_io=setmetatable({read=function(format)
    if format~='*a' then error('sys.chunk: only io.read("*a")',2) end
    local text=pending or '';pending=nil
    return text
  end},{__index=io})
  local env=setmetatable({io=chunk_io,print=function(...)
    local n=select('#',...);local t={}
    for i=1,n do t[i]=tostring((select(i,...))) end
    out[#out+1]=table.concat(t,'\t')..'\n'
  end},{__index=_G})
  setfenv(chunk,env)
  chunk()
  return table.concat(out)
end
-- script(path): what `lua <path>` prints, run in this process
function M.script(path)
  local chunk=compiled[path]
  if not chunk then chunk=assert(loadfile(path));compiled[path]=chunk end
  return run_chunk(chunk)
end
-- chunk(name, source, stdin): the same for a packaged source text (pair_auto.NETWORK_READ / NETWORK_WRITE)
function M.chunk(name,source,stdin)
  local chunk=compiled[name]
  if not chunk then chunk=assert(loadstring(source,'='..name));compiled[name]=chunk end
  return run_chunk(chunk,stdin)
end

-- spawn(argv, {timeout}): start a command in the background; its exit status lands in a file of ours.
-- wait(handle, seconds) -> exit status, or nil when it did not finish in time (Python forward_dispatch: the
-- command is dispatched under the control lock and awaited outside it).
function M.spawn(argv,opts)
  opts=opts or {}
  local parts={}
  for i,a in ipairs(argv) do parts[i]=quote(a) end
  local line=table.concat(parts,' ')
  if opts.timeout then
    if have_timeout==nil then have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0 end
    if have_timeout then line='timeout '..string.format('%d',math.floor(opts.timeout))..' '..line end
  end
  local status=M.RUNTIME..'/.spawn-'..canon.unique()..'.status'
  local full='('..line..' </dev/null >/dev/null 2>&1; echo $? >'..status..'.part && mv '..status..'.part '..status..')'..closing()..' &'
  if os.execute(full)~=0 then return nil end
  return status
end
function M.wait(handle,seconds)
  if not handle then return nil end
  local end_=M.clock()+seconds
  while true do
    local f=io.open(handle,'r')
    if f then
      local text=f:read('*l');f:close();os.remove(handle)
      return tonumber(text)
    end
    if M.clock()>=end_ then return nil end
    M.sleep(0.1)
  end
end

local machine=nil
function M.machine()
  if machine==nil then local rc,out=M.exec({'uname','-m'});machine=rc==0 and string.match(out,'^(%S+)') or '' end
  return machine
end

return M
