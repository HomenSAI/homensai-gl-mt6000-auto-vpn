-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
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
function M.write_atomic(path,text)
  local directory,name=string.match(path,'^(.*)/([^/]+)$')
  if not canon.safe_directory(directory) or not string.find(name,'^[A-Za-z0-9_.-]+$') then error('monitor_io: unsafe path',0) end
  local pending=directory..'/.'..name..'.'..canon.unique()..'.pending'
  local f=io.open(pending,'wb')
  if not f then os.execute('mkdir -p '..directory..' && chmod 700 '..directory);f=assert(io.open(pending,'wb')) end
  assert(f:write(text));assert(f:flush());f:close()
  local synced=false
  if nixio and nixio.open and nfs and nfs.chmod then
    synced=pcall(function() assert(nfs.chmod(pending,'rw-------'));local h=assert(nixio.open(pending,'r'));assert(h:sync());h:close() end)
  end
  if not synced then os.execute('chmod 600 '..pending..' && sync') end
  local renamed,err=os.rename(pending,path)
  if not renamed then os.remove(pending);error(err,0) end
end
-- RAM-only write without fsync (reply files of the rpcd bridge, probe scratch files).
function M.write_ram(path,text)
  local directory,name=string.match(path,'^(.*)/([^/]+)$')
  if not canon.safe_directory(directory) or not string.find(name,'^[A-Za-z0-9_.-]+$') then error('monitor_io: unsafe path',0) end
  local pending=directory..'/.'..name..'.'..canon.unique()..'.pending'
  local f=assert(io.open(pending,'wb'));assert(f:write(text));f:close()
  if nfs and nfs.chmod then pcall(nfs.chmod,pending,'rw-------') end
  local renamed,err=os.rename(pending,path)
  if not renamed then os.remove(pending);error(err,0) end
end
function M.remove(path) os.remove(path) end
function M.exists(path) return M.file_size(path)~=nil end

local SYSFS={ifindex=true,['statistics/rx_bytes']=true,['statistics/tx_bytes']=true,operstate=true}
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
}
function M.command(name,...)
  local build=M.COMMANDS[name]
  if not build then return nil,'unknown command '..tostring(name) end
  local line=build(...)
  if not line then return nil,'invalid command argument' end
  return capture(line)
end

------------------------------------------------------------------------------------------------------
-- try_lock(directory, fn, name): flock(2) like Python's control_lock/rpc_throttle, but NON-blocking: returns
-- false when another process holds it (the event loop never waits), else true, fn's results. The flock is
-- taken by busybox flock(1) -n on the descriptor this process holds open (see control.lua: nixio's lock() is
-- lockf and does not exclude Python's flock); closing the file releases it.
------------------------------------------------------------------------------------------------------
function M.try_lock(directory,fn,name)
  name=name or 'auto-control.lock'
  if not canon.safe_directory(directory) or not string.find(name,'^[a-z.-]+$') then return false end
  local st=lstat(directory)
  if st and st.type=='lnk' then return false end
  local path=directory..'/'..name
  local file=io.open(path,'a')
  if not file then os.execute('mkdir -p '..directory..' && chmod 700 '..directory);file=io.open(path,'a') end
  if not file then return false end
  local p=io.popen('for f in /proc/$$/fd/*; do if [ "$f" -ef '..path..' ]; then flock -n -x "${f##*/}" && echo ok; exit 0; fi; done; exit 97','r')
  local out=p and p:read('*a') or ''
  if p then p:close() end
  if out~='ok\n' then file:close();return false end
  local results={pcall(fn)}
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
    assert(sock:connect(host,port or 0))
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
  local sent=pcall(function() assert(sock:send(packet)) end)
  if not sent then finish(nil,'transport') end
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
