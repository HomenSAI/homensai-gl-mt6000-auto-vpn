-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- monitor_io.lua: the router side of every external access of the Lua monitor (the injectable "runner").
-- Tests replace this whole table with fakes; nothing in monitor.lua/probe.lua/accounting.lua/rpc.lua touches
-- sockets, files, clocks or processes except through it.
-- Rules: no shell line is ever built from request data. Command lines are the constants below; the only
-- variable parts are values validated against a strict character class (logical interface, dotted IPv4, decimal
-- mark, method name) or paths we chose ourselves. Child processes of the probes are started WITHOUT a shell
-- from constant argument lists (uloop.process -> execve).
--
-- Router facts (docs/architecture/LUA-ROUTER-FACTS-2026-10-30.ru.md, MT3000, GL 4.11 / OpenWrt 21.02):
--   nixio has bindtodevice and raw ICMP, but NO SO_MARK and NO TLS. SO_BINDTODEVICE alone routes through the
--   tunnel (the kernel uses the device even without a route/mark rule): ping -I wgclient1 / curl --interface
--   wgclient1 reach the tunnel's exit. So: DNS over UDP and ICMP use nixio sockets bound to the device only;
--   HTTPS uses `curl --interface <dev>` child processes. The fwmark of the tunnel is still read and compared
--   before/after every probe (route identity), it is just not set on our sockets.
-- Every probe primitive is NON-blocking under uloop: sockets are watched with uloop.fd_add, children with
-- uloop.process, each with its own deadline timer; the callback runs exactly once.
local canon=require('canon')

local M={}
M.RUNTIME='/var/run/homensai-vpn'
M.PERSIST='/etc/homensai-vpn'
M.CONFIG='/etc/config/homensai_vpn'
M.PACKAGE_CONTROL='/usr/lib/opkg/info/homensai-auto-vpn-lua.control'
M.AGENT='/usr/bin/python3 /usr/lib/homensai-vpn/agent.py'
M.INVENTORY='/usr/bin/lua /usr/lib/homensai-vpn/inventory.lua'
M.NATIVE_POLICY='/usr/bin/lua /usr/lib/homensai-vpn/native_policy.lua'
M.CURL='/usr/bin/curl'
M.PYTHON='/usr/bin/python3'
M.BRIDGE='/usr/lib/homensai-vpn/status_bridge.py'
M.MAX_OUTPUT=2*1024*1024
M.TZ='CET-1CEST,M3.5.0,M10.5.0/3'
M.CHILD_ENV={'PATH=/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL=C'}

local nixio_ok,nixio=pcall(require,'nixio')
if not nixio_ok or type(nixio)~='table' then nixio=nil end
local nfs_ok,nfs=pcall(require,'nixio.fs')
if not nfs_ok or type(nfs)~='table' then nfs=nil end
local uloop  -- loaded by M.attach_loop() on the router (monitor.run); absent in tests and one-shot tools

local function safe_word(s,limit) return type(s)=='string' and #s>=1 and #s<=limit and string.find(s,'^[A-Za-z0-9_.:-]+$')~=nil end
local function dotted(s) return type(s)=='string' and string.find(s,'^%d+%.%d+%.%d+%.%d+$')~=nil end

function M.configure(options)
  for _,key in ipairs({'RUNTIME','PERSIST','CONFIG','PACKAGE_CONTROL'}) do
    if options[key] then
      if not canon.safe_directory(options[key]) then error('monitor_io: unsafe path '..key,2) end
      M[key]=options[key]
    end
  end
  if options.RUNTIME then canon.configure({runtime=options.RUNTIME}) end
end

function M.log(text) io.stderr:write('hv-monitor: ',tostring(text),'\n') end

function M.setup_timezone()
  if nixio and nixio.setenv then nixio.setenv('TZ',M.TZ) end
end

------------------------------------------------------------------------------------------------------
-- clocks, randomness
------------------------------------------------------------------------------------------------------
function M.wall()
  if nixio and nixio.gettimeofday then local s,us=nixio.gettimeofday();return s+us/1e6 end
  return os.time()
end
-- Monotonic seconds (CLOCK_BOOTTIME basis, 10 ms resolution): the same clock Python's time.monotonic()
-- values in RAM files are compared with (pair-manual-kernel-cache.json 'at').
function M.clock()
  local f=io.open('/proc/uptime','r')
  if not f then return os.clock() end
  local text=f:read('*l');f:close()
  return tonumber(string.match(text or '','^([0-9.]+)')) or os.clock()
end
-- Microsecond clock for short intervals (probe elapsed times); callers reject a negative difference.
function M.hires()
  if nixio and nixio.gettimeofday then local s,us=nixio.gettimeofday();return s+us/1e6 end
  return M.clock()
end
function M.random(n)
  local f=io.open('/dev/urandom','rb')
  if f then local data=f:read(n);f:close();if data and #data==n then return data end end
  local out={};for i=1,n do out[i]=string.char(math.random(0,255)) end
  return table.concat(out)
end

------------------------------------------------------------------------------------------------------
-- files (agent.read_json / atomic_json rules)
------------------------------------------------------------------------------------------------------
local function lstat(path) if nfs and nfs.lstat then return nfs.lstat(path) end;return nil end

function M.file_size(path)
  local st=lstat(path)
  if st then return st.type=='reg' and st.size or nil end
  local f=io.open(path,'rb');if not f then return nil end
  local size=f:seek('end');f:close();return size
end
-- Change key of a file (inode, size, mtime); nil when absent. Used to reuse parsed files in memory.
function M.file_key(path)
  local st=lstat(path)
  if st then return st.type..':'..tostring(st.ino)..':'..tostring(st.size)..':'..tostring(st.mtime) end
  local size=M.file_size(path)
  return size and ('size:'..size..':'..os.time()) or nil  -- without nixio the key changes every second
end
-- nil when absent; raises on a symlink or more than 4 MB (agent.read_json).
function M.read_file(path)
  local st=lstat(path)
  if st and st.type~='reg' then error('symlink storage refused',0) end
  local f=io.open(path,'rb')
  if not f then return nil end
  local size=f:seek('end');f:seek('set',0)
  if size and size>4*1024*1024 then f:close();error('oversize state',0) end
  local text=f:read('*a');f:close()
  return text
end
function M.unsafe(path)
  local st=lstat(path)
  return st~=nil and (st.type~='reg' or st.size>1024*1024)
end
-- Flash writes: durable.write (temporary file, fsync, rename, fsync of the directory) - the one primitive of
-- the Lua line. RAM-only writes (reply files of the rpcd bridge, probe scratch files): the same rename, no fsync.
function M.write_atomic(path,text) return require('durable').write(path,text) end
function M.write_ram(path,text) return require('durable').write(path,text,{sync=false}) end
function M.remove(path) os.remove(path) end
-- Names in a directory (nixio.fs.dir; no child process); {} when absent or without nixio.fs.
function M.list_dir(path)
  local names={}
  if not (nfs and nfs.dir) then return names end
  local ok,iterator=pcall(nfs.dir,path)
  if not ok or not iterator then return names end
  for name in iterator do if name~='.' and name~='..' then names[#names+1]=name end end
  return names
end
-- A directory that is a symlink (stats-archive must be a real folder, like Python's is_symlink check).
function M.unsafe_directory(path) local st=lstat(path);return st~=nil and st.type~='dir' end
function M.exists(path) return M.file_size(path)~=nil end

local SYSFS={ifindex=true,['statistics/rx_bytes']=true,['statistics/tx_bytes']=true,operstate=true,
  ['statistics/rx_packets']=true,['statistics/tx_packets']=true}
function M.sysfs(device,name)
  if not safe_word(device,15) or not SYSFS[name] then return nil end
  local f=io.open('/sys/class/net/'..device..'/'..name,'r')
  if not f then return nil end
  local text=f:read('*l');f:close();return text
end

function M.config_mtime()
  if nfs and nfs.stat then local st=nfs.stat(M.CONFIG);return st and (st.mtime..':'..st.size..':'..(st.ino or 0)) or nil end
  local f=io.open(M.CONFIG,'r');if not f then return nil end;f:close()
  return tostring(os.time())  -- without nixio the cache key changes every second: the file is re-read
end
function M.config_text()
  local f=io.open(M.CONFIG,'r');if not f then return nil end
  local text=f:read('*a');f:close();return text
end
-- Installed package version from opkg's control file; nil when unknown (never guessed).
function M.package_version()
  local size=M.file_size(M.PACKAGE_CONTROL)
  if not size or size>8192 then return nil end
  local f=io.open(M.PACKAGE_CONTROL,'r');if not f then return nil end
  local text=f:read('*a');f:close()
  for line in string.gmatch(text,'[^\n]+') do
    local value=string.match(line,'^Version: (.-)%s*$')
    if value then return (string.find(value,'^[0-9A-Za-z.+~_-]+$') and #value<=48) and value or nil end
  end
  return nil
end

------------------------------------------------------------------------------------------------------
-- constant commands (short, synchronous: ubus/ip/inventory, as the Python monitor ran them)
------------------------------------------------------------------------------------------------------
local have_timeout
local function bounded(line)
  if have_timeout==nil then have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0 end
  return have_timeout and ('timeout 5 '..line) or line
end
-- The output goes to a file of ours in RAM, never through a pipe: the async curl children of this process
-- (uloop.process) exit at any moment, and their SIGCHLD interrupts a blocking pipe read (EINTR), which left a
-- partial answer and "sh: write error: Broken pipe" on the MT3000. system() (os.execute) retries its wait and
-- a regular-file read is not interrupted.
local function capture(line)
  local path=M.RUNTIME..'/.cmd-'..canon.unique()..'.out'
  local rc=os.execute('{ '..bounded(line)..'; } >'..path..' 2>/dev/null')
  local f=io.open(path,'rb')
  local body=f and f:read('*a') or nil
  if f then f:close() end
  os.remove(path)
  if rc~=0 or body==nil then return nil,'COMMAND-FAILED' end
  if #body>M.MAX_OUTPUT then return nil,'oversize command response' end
  return body
end
M.capture=capture

M.COMMANDS={
  iface_status=function(logical) if not safe_word(logical,64) then return nil end;return 'ubus call network.interface.'..logical..' status' end,
  routes=function() return 'ip -4 -j route show table all' end,
  rules=function() return 'ip -4 -j rule show' end,
  route_get=function(address,mark)
    if not dotted(address) or not (type(mark)=='string' and string.find(mark,'^%d+$') and #mark<=10) then return nil end
    return 'ip -4 -j route get '..address..' mark '..mark
  end,
  inventory=function() return M.INVENTORY end,
  native_policy=function() return M.NATIVE_POLICY end,
  nft_fault_list=function() return 'nft list table inet homensai_vpn_fault' end,
  nft_fault_delete=function() return 'nft delete table inet homensai_vpn_fault' end,
}
function M.command(name,...)
  local build=M.COMMANDS[name]
  if not build then return nil,'unknown command '..tostring(name) end
  local line=build(...)
  if not line then return nil,'invalid command argument' end
  return capture(line)
end

-- Exit status of os.execute (Lua 5.1 returns the raw wait status): the exit code, 128+signal when killed.
local function exit_code(status)
  if type(status)~='number' then return 255 end
  if status>=256 then return math.floor(status/256) end
  if status>0 then return 128+status%128 end
  return 0
end
M.exit_code=exit_code
-- capture_rc(line): exit code, output (through a RAM file, like capture); the caller judges the code.
local function capture_rc(line)
  local path=M.RUNTIME..'/.cmd-'..canon.unique()..'.out'
  local status=os.execute('{ '..line..'; } >'..path..' 2>/dev/null')
  local f=io.open(path,'rb')
  local body=f and f:read('*a') or ''
  if f then f:close() end
  os.remove(path)
  if #body>M.MAX_OUTPUT then return 255,'' end
  return exit_code(status),body
end
-- command_rc(name): a constant command (5 s bound) -> exit code, output. Python's subprocess.run(...).returncode.
function M.command_rc(name,...)
  local build=M.COMMANDS[name]
  if not build then return 255,'' end
  local line=build(...)
  if not line then return 255,'' end
  return capture_rc(bounded(line))
end
-- exec(argv, {timeout=}) -> exit code, output: the sys.exec() shape platform.lua expects (preparation checks).
-- Every argument is single-quoted; one with a quote, NUL or newline is refused (no shell line from data).
function M.exec(argv,opts)
  local parts={}
  for i,a in ipairs(argv) do
    if type(a)~='string' or string.find(a,"[%z\n']") then error('monitor_io: unsafe command argument',0) end
    parts[i]="'"..a.."'"
  end
  local line=table.concat(parts,' ')..' </dev/null'
  if opts and opts.timeout then
    if have_timeout==nil then have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0 end
    if have_timeout then line='timeout '..string.format('%d',math.floor(opts.timeout))..' '..line end
  end
  return capture_rc(line)
end
-- The read-only view of server_endpoint.lua (the peer address of a live VPN client, server_endpoint.py):
-- bounded file reads (nil = missing, false = another error), readlink/dir of /proc/<pid>/fd through nixio.fs
-- (no child process), a monotonic clock, and `wg show <wgclientN> endpoints` (1 s bound, output through a RAM
-- file like every command of this process: SIGCHLD of the curl children interrupts pipe reads).
function M.endpoint_fs()
  local F={}
  function F.read(path,limit)
    local f,_,errno=io.open(path,'rb')
    if not f then return errno==2 and nil or false end
    local ok,data=pcall(f.read,f,limit+1)
    f:close()
    if not ok then return false end
    return data or ''
  end
  function F.readlink(path)
    if not (nfs and nfs.readlink) then return nil end
    local ok,target=pcall(nfs.readlink,path)
    return ok and type(target)=='string' and target or nil
  end
  function F.dir(path)
    if not (nfs and nfs.dir) then return nil end
    local ok,iterator=pcall(nfs.dir,path)
    if not ok or not iterator then return nil end
    local names={}
    for name in iterator do
      if name~='.' and name~='..' then names[#names+1]=name end
      if #names>256 then break end  -- server_endpoint refuses more than 256 descriptors anyway
    end
    return names
  end
  F.clock=M.hires
  function F.wg(interface)
    if type(interface)~='string' or not string.find(interface,'^wgclient%d%d?%d?%d?$') then return nil end
    if have_timeout==nil then have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0 end
    local rc,body=capture_rc((have_timeout and 'timeout 1 ' or '')..'wg show '..interface..' endpoints')
    if rc~=0 then return nil end
    return body
  end
  return F
end

-- The read-only file view of platform.lua (preparation_control.auto_blocker, preparation_status.snapshot):
-- lstat {type,size}, read(path,maximum) (raises above maximum), dir(path) -> names | nil, exec as above.
function M.platform_sys()
  local S={}
  function S.lstat(path)
    if nfs and nfs.lstat then
      local st=nfs.lstat(path)
      if not st then return nil end
      return {type=st.type,size=st.size}
    end
    local f=io.open(path,'rb');if not f then return nil end
    local size=f:seek('end');f:close()
    return {type='reg',size=size}
  end
  function S.read(path,maximum)
    local f=io.open(path,'rb')
    if not f then return nil end
    local text=f:read(maximum and (maximum+1) or '*a') or ''
    f:close()
    if maximum and #text>maximum then error({code='OVERSIZE-FILE'},0) end
    return text
  end
  function S.dir(path)
    if not (nfs and nfs.dir) then return nil end
    local ok,iter=pcall(nfs.dir,path)
    if not ok or not iter then return nil end
    local out={}
    for name in iter do if name~='.' and name~='..' then out[#out+1]=name end end
    return out
  end
  S.exec=M.exec
  S.wall=M.wall;S.clock=M.clock
  -- readiness.lua (system_readiness.snapshot): shutil.which / Path.is_file / shutil.disk_usage + statvfs/os.access,
  -- all through nixio.fs (no child process); without nixio.fs every answer is "not proven" (nil).
  function S.executable(path)
    if not (nfs and nfs.stat and nfs.access) then return false end
    local st=nfs.stat(path)
    return st~=nil and st.type~='dir' and nfs.access(path,'x')==true
  end
  function S.is_file(path)
    if not (nfs and nfs.stat) then return false end
    local st=nfs.stat(path)
    return st~=nil and st.type=='reg'
  end
  function S.readlink(path)
    if not (nfs and nfs.readlink) then return nil end
    local ok,target=pcall(nfs.readlink,path)
    return ok and type(target)=='string' and target or nil
  end
  function S.storage(path)
    if not (nfs and nfs.statvfs) then return nil,nil end
    local ok,v=pcall(nfs.statvfs,path)
    if not ok or type(v)~='table' or type(v.bavail)~='number' or type(v.frsize)~='number' then return nil,nil end
    local free=v.bavail*v.frsize
    local writable=nil
    if type(v.flag)=='number' and nfs.access then
      writable=(v.flag%2==0) and nfs.access(path,'w')==true  -- ST_RDONLY is bit 0
    end
    return free,writable
  end
  function S.path_env() return os.getenv('PATH') end
  return S
end
-- Anything at this path (a file of any type, a symlink): Python's Path.exists()/is_symlink() test.
function M.present(path)
  if nfs and nfs.lstat then return nfs.lstat(path)~=nil end
  local f=io.open(path,'rb');if f then f:close();return true end
  return false
end

------------------------------------------------------------------------------------------------------
-- try_lock(directory, fn, name): flock(2) like Python's control_lock/rpc_throttle, but NON-blocking: returns
-- false when another process holds it (the event loop never waits), else true, fn's results. The flock is
-- taken by busybox flock(1) -n on the descriptor this process holds open (see control.lua: nixio's lock() is
-- lockf and does not exclude Python's flock); closing the file releases it.
------------------------------------------------------------------------------------------------------
local held_try=nil  -- descriptor of the lock try_lock holds now (a detached child closes it: speed.lua)
function M.held_fd() return held_try end
function M.try_lock(directory,fn,name)
  name=name or 'auto-control.lock'
  if not canon.safe_directory(directory) or not string.find(name,'^[a-z.-]+$') then return false end
  local st=lstat(directory)
  if st and st.type=='lnk' then return false end
  local path=directory..'/'..name
  local file=io.open(path,'a')
  if not file then os.execute('mkdir -p '..directory..' && chmod 700 '..directory);file=io.open(path,'a') end
  if not file then return false end
  local p=io.popen('for f in /proc/$$/fd/*; do if [ "$f" -ef '..path..' ]; then flock -n -x "${f##*/}" && echo "ok ${f##*/}"; exit 0; fi; done; exit 97','r')
  local out=p and p:read('*a') or ''
  if p then p:close() end
  local fd=tonumber(string.match(out,'^ok (%d+)\n$'))
  if not fd then file:close();return false end
  local outer=held_try
  held_try=fd
  local results={pcall(fn)}
  held_try=outer
  file:close()
  if not results[1] then error(results[2],0) end
  return true,unpack(results,2)
end

------------------------------------------------------------------------------------------------------
-- event loop attachment and non-blocking primitives
------------------------------------------------------------------------------------------------------
function M.attach_loop(loop) uloop=loop end
function M.async() return uloop~=nil end

-- Every armed uloop object (timer, fd watch, child process, socket) is held here until it completes. The
-- libubox-lua userdata cancel themselves in __gc: an object only an unreachable closure points to would be
-- collected in a long-running daemon and its callback would never come (one-shot runs never see it).
M.live={}
function M.live_count() local n=0;for _ in pairs(M.live) do n=n+1 end;return n end

-- after(ms, fn) -> handle with :cancel()
function M.after(ms,fn)
  if not uloop then error('monitor_io: no event loop',0) end
  local handle={}
  local timer=uloop.timer(function() M.live[handle]=nil;fn() end)
  M.live[handle]=timer
  timer:set(math.max(1,math.floor(ms)))
  handle.cancel=function() M.live[handle]=nil;pcall(function() timer:cancel() end) end
  return handle
end

local function once(cb)
  local fired=false
  return function(...) if fired then return end;fired=true;return cb(...) end
end

local function pid_of(process)
  if type(process)=='number' then return process end
  if type(process)=='userdata' or type(process)=='table' then
    local ok,pid=pcall(function() return process:pid() end)
    if ok and type(pid)=='number' then return pid end
  end
  return nil
end

-- spawn(argv, seconds, cb(exit_code|nil, kind)): execve(argv[1], argv) without a shell; killed at the deadline.
-- argv elements are constants or validated words chosen by the caller; never request text.
function M.spawn(argv,seconds,cb)
  cb=once(cb)
  if not uloop then cb(nil,'unavailable');return end
  local args={};for i=2,#argv do args[#args+1]=argv[i] end
  local guard
  local key={}
  local ok,process=pcall(uloop.process,argv[1],args,M.CHILD_ENV,function(code)
    M.live[key]=nil
    if guard then guard.cancel() end
    cb(tonumber(code) or -1,nil)
  end)
  if not ok or not process then cb(nil,'unavailable');return end
  M.live[key]=process
  local pid=pid_of(process)
  guard=M.after(seconds*1000+500,function()
    M.live[key]=nil
    if pid and nixio and nixio.kill then pcall(nixio.kill,pid,9) end
    cb(nil,'timeout')
  end)
end

-- datagram(kind, device, host, port, packet, seconds, accept, cb(data|nil, kind_or_nil, sent_at, received_at))
-- kind 'udp' (SOCK_DGRAM) or 'icmp' (SOCK_RAW/IPPROTO_ICMP). The socket is bound to the device only (no SO_MARK
-- in nixio; see the router facts). accept(data, peer) -> true for the awaited answer; others are ignored.
function M.datagram(kind,device,host,port,packet,seconds,accept,cb)
  cb=once(cb)
  if not nixio or not uloop then cb(nil,'unavailable');return end
  if not safe_word(device,15) or not dotted(host) then cb(nil,'unavailable');return end
  local sock,ufd,guard
  local key={}
  local function finish(...)
    M.live[key]=nil
    if guard then guard.cancel() end
    if ufd then pcall(function() ufd:delete() end) end
    if sock then pcall(function() sock:close() end) end
    cb(...)
  end
  local ok=pcall(function()
    sock=assert(nixio.socket('inet',kind=='icmp' and 'raw' or 'dgram',kind=='icmp' and 'icmp' or nil))
    assert(sock:setopt('socket','bindtodevice',device))
    assert(sock:setblocking(false))
    -- A raw ICMP socket is not connected: nixio's connect() resolves the port as a service name and refuses 0
    -- ("Unrecognized service", measured on the MT3000), so every ping failed PING-UNAVAILABLE. ICMP uses sendto.
    if kind~='icmp' then assert(sock:connect(host,port or 0)) end
  end)
  if not ok then finish(nil,'unavailable');return end
  local sent_at=M.hires()
  local fd=sock:fileno()
  ufd=uloop.fd_add(fd,function()
    for _=1,32 do
      local data,peer=sock:recvfrom(4096)
      local received_at=M.hires()
      if data==false then return end  -- would block
      if data==nil then
        -- nixio: nil, errno, message. EAGAIN: wait for the next event; any other error ends the check now
        -- (a level-triggered error must not spin until the deadline).
        local eagain=(nixio.const and nixio.const.EAGAIN) or 11
        if peer~=eagain and peer~=11 then finish(nil,'transport') end
        return
      end
      if accept(data,peer) then finish(data,nil,sent_at,received_at);return end
    end
  end,uloop.ULOOP_READ or 1)
  M.live[key]={sock=sock,ufd=ufd}
  guard=M.after(seconds*1000,function() finish(nil,'timeout') end)
  local sent=pcall(function()
    if kind=='icmp' then assert(sock:sendto(packet,host,0)) else assert(sock:send(packet)) end
  end)
  if not sent then finish(nil,'transport') end
end

-- beat_socket(device) -> handle | nil, 'missing'|'unavailable'  (fast_detect.lua, Lua plan item 5)
-- One persistent non-blocking raw ICMP socket bound to the tunnel device (no SO_MARK, as datagram()). It is
-- never watched by uloop: the pulse sends one echo per beat and reads the answers of the previous beat without
-- blocking, so a beat costs a few syscalls and no loop object. handle:send(target, packet) -> true | nil, kind
-- ('refused': the kernel/firewall refused the send; 'missing': the device is gone; 'unavailable'); handle:recv()
-- -> data | nil (nothing more now); handle:close().
M.SEND_REFUSED={[1]=true,[13]=true,[100]=true,[101]=true,[105]=true,[113]=true}  -- EPERM EACCES ENETDOWN ENETUNREACH ENOBUFS EHOSTUNREACH
M.SEND_MISSING={[6]=true,[19]=true}                                               -- ENXIO ENODEV
function M.beat_socket(device)
  if not nixio or not safe_word(device,15) then return nil,'unavailable' end
  local sock=nixio.socket('inet','raw','icmp')
  if not sock then return nil,'unavailable' end
  local bound,code=sock:setopt('socket','bindtodevice',device)
  if not bound then pcall(function() sock:close() end);return nil,M.SEND_MISSING[code] and 'missing' or 'unavailable' end
  if not sock:setblocking(false) then pcall(function() sock:close() end);return nil,'unavailable' end
  local handle={}
  function handle:send(target,packet)
    if not dotted(target) then return nil,'unavailable' end
    -- sendto, never connect(): nixio refuses port 0 as a service name on the router (see datagram())
    local ok,err=sock:sendto(packet,target,0)
    if ok then return true end
    if M.SEND_REFUSED[err] then return nil,'refused' end
    if M.SEND_MISSING[err] then return nil,'missing' end
    return nil,'unavailable'
  end
  function handle:recv()
    local data=sock:recvfrom(4096)
    if type(data)~='string' then return nil end  -- false: would block; nil: an error (read again next beat)
    return data
  end
  function handle:close() pcall(function() sock:close() end) end
  return handle
end

-- HTTPS GET through the tunnel device with curl (nixio has no TLS). The certificate is checked for the
-- hostname (curl default CA store), the connection goes to the fixed address (--resolve), HTTP/1.1, no
-- redirects, body capped. cb(response|nil, kind): response={status=<int>, body=<bytes>}.
M.CURL_TLS={[35]=true,[51]=true,[53]=true,[54]=true,[58]=true,[59]=true,[60]=true,[64]=true,[66]=true,[77]=true,
  [80]=true,[82]=true,[83]=true,[90]=true,[91]=true}
function M.https_get(device,address,hostname,path,seconds,cb)
  cb=once(cb)
  if not safe_word(device,15) or not dotted(address) or not string.find(hostname,'^[a-z0-9.-]+$')
     or not string.find(path,'^/[A-Za-z0-9_./?=&%-]*$') then cb(nil,'transport-error');return end
  local base=M.RUNTIME..'/probe-'..canon.unique()
  local head,body=base..'.h',base..'.b'
  local argv={M.CURL,'-q','-s','--http1.1','--proto','=https','--max-redirs','0','-m',tostring(seconds),
    '--interface',device,'--resolve',hostname..':443:'..address,
    '-H','Accept: application/dns-json, application/dns-message, text/plain',
    '--max-filesize','32769','-D',head,'-o',body,'https://'..hostname..path}
  M.spawn(argv,seconds+1,function(code,kind)
    local function read(p) local f=io.open(p,'rb');if not f then return nil end;local t=f:read(40000);f:close();return t end
    local headers,content=read(head),read(body)
    os.remove(head);os.remove(body)
    if kind then cb(nil,kind=='timeout' and 'timeout' or 'transport-error');return end
    if code==28 then cb(nil,'timeout');return end
    if M.CURL_TLS[code] then cb(nil,'tls-error');return end
    if code==63 then cb(nil,'invalid-response');return end
    if code~=0 or not headers then cb(nil,'transport-error');return end
    local status
    for line in string.gmatch(headers,'[^\r\n]+') do
      local s=string.match(line,'^HTTP/[0-9.]+ (%d%d%d)')
      if s then status=tonumber(s) end
    end
    if not status then cb(nil,'invalid-response');return end
    cb({status=status,body=content or ''},nil)
  end)
end

------------------------------------------------------------------------------------------------------
-- capabilities (published in status.lua_backend; the first router pass shows what was detected)
------------------------------------------------------------------------------------------------------
local caps
function M.capabilities()
  if caps then return caps end
  caps={nixio=nixio~=nil,bindtodevice=false,raw_icmp=false,so_mark=false,so_mark_required=false,tls=false,
    https='curl --interface',curl=M.file_size(M.CURL)~=nil,uloop=uloop~=nil,sha256=canon.sha256_backend(),
    probes='device-bound (SO_BINDTODEVICE), no fwmark'}
  if nixio then
    pcall(function()
      local sock=assert(nixio.socket('inet','dgram'))
      caps.bindtodevice=pcall(function() assert(sock:setopt('socket','bindtodevice','lo')) end)
      caps.so_mark=pcall(function() assert(sock:setopt('socket','mark',1)) end)
      sock:close()
    end)
    caps.tls=type(nixio.tls)=='function'
    pcall(function() local sock=nixio.socket('inet','raw','icmp');if sock then caps.raw_icmp=true;sock:close() end end)
  end
  return caps
end

-- Background Python helper of the temporary status bridge (status_bridge.py, see monitor_status.lua):
-- constant argv, output file chosen by us, never request data.
function M.bridge(output,cb)
  if not uloop or M.file_size(M.BRIDGE)==nil then cb(nil,'unavailable');return end
  M.spawn({M.PYTHON,M.BRIDGE,output},20,cb)
end

-- Readiness marker of the rpcd dispatcher (RAM): present while the Lua object serves; removed at shutdown.
M.READY='lua-monitor.ready'

return M
