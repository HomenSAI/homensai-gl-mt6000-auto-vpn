-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
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
local durable=require('durable')

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
function M.write_private(path,text)  -- 0600, our RAM directory only (tmpfs: no fsync)
  durable.write(path,text,{sync=false})
end
-- write_atomic(path,text): the durable flash write (durable.lua): temporary file, fsync, rename, fsync of the
-- directory. sweep_pending(directory): leftovers of a write a power cut interrupted.
function M.write_atomic(path,text) return durable.write(path,text) end
function M.sweep_pending(directory,max_age) return durable.sweep(directory,max_age) end
M.durable=durable
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
    -- the new name itself on flash too (a power cut must not lose an archive the journal already refers to)
    local directory=string.match(path,'^(.*)/[^/]+$')
    if directory and not durable.in_ram(path) then durable.sync_directory(directory) end
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

------------------------------------------------------------------------------------------------------
-- live channel probe I/O (live_probe.lua, plan item 4): the Lua monitor's primitives in a blocking form.
-- The supervisor's pass is synchronous, so the checks of one probe run side by side and the pass waits for
-- all of them: the HTTPS checks are `curl --interface <dev>` children started together in one background
-- group (no shell line from data: constant flags, validated words, paths of ours), the DNS check is a nixio
-- UDP socket bound to the device (no SO_MARK on the router) read while curl runs. Outputs go to files of ours
-- in RAM and the group's end is a marker file: no pipe read that SIGCHLD could interrupt.
------------------------------------------------------------------------------------------------------
M.CURL='/usr/bin/curl'
function M.random(n)
  local f=io.open('/dev/urandom','rb')
  if f then local data=f:read(n);f:close();if data and #data==n then return data end end
  local out={};for i=1,n do out[i]=string.char(math.random(0,255)) end
  return table.concat(out)
end
local probe_ready=nil
-- probe_capable(): nixio with SO_BINDTODEVICE and the curl binary; else the caller keeps the Python bridge
function M.probe_capable()
  if probe_ready==nil then
    probe_ready=false
    local st=M.stat(M.CURL)
    if nixio and nixio.socket and st and st.type=='reg' then
      probe_ready=pcall(function()
        local sock=assert(nixio.socket('inet','dgram'))
        local ok=sock:setopt('socket','bindtodevice','lo')
        sock:close()
        assert(ok)
      end)
    end
  end
  return probe_ready
end
local function probe_word(s,limit) return type(s)=='string' and #s>=1 and #s<=limit and string.find(s,'^[A-Za-z0-9_.:-]+$')~=nil end
local function probe_request_ok(r)
  return type(r)=='table' and type(r.address)=='string' and string.find(r.address,'^%d+%.%d+%.%d+%.%d+$')~=nil
    and type(r.hostname)=='string' and string.find(r.hostname,'^[a-z0-9.-]+$')~=nil and #r.hostname<=64
    and type(r.path)=='string' and string.find(r.path,'^/[A-Za-z0-9_./?=&%-]*$')~=nil and #r.path<=512
    and type(r.seconds)=='number' and r.seconds%1==0 and r.seconds>=1 and r.seconds<=30
end
local function read_small(path,limit)
  local f=io.open(path,'rb');if not f then return nil end
  local text=f:read(limit);f:close();return text
end
local function present(path) local f=io.open(path,'rb');if f then f:close();return true end;return false end
-- the curl exit status and files -> response {status, body} or nil, kind (monitor_io.https_get rules)
local TIMEOUT_EXIT={[124]=true,[137]=true,[143]=true}  -- timeout(1) expiry / killed
function M.curl_answer(code,headers,body)
  if code==nil or TIMEOUT_EXIT[code] or code==28 then return nil,'timeout' end
  if require('monitor_io').CURL_TLS[code] then return nil,'tls-error' end
  if code==63 and not headers then return nil,'invalid-response' end
  if (code~=0 and code~=63) or not headers then return nil,'transport-error' end
  local status
  for line in string.gmatch(headers,'[^\r\n]+') do
    local s=string.match(line,'^HTTP/[0-9.]+ (%d%d%d)')
    if s then status=tonumber(s) end
  end
  if not status then return nil,'invalid-response' end
  -- 63: the body is larger than the 32768 bytes Python reads; the status is kept (Python checks it first)
  return {status=status,body=body or '',oversize=(code==63) or nil},nil
end
-- start the HTTPS group in the background; -> files, marker (nil when it could not start)
local function https_start(device,requests)
  local base=M.RUNTIME..'/.probe-'..canon.unique()
  local files,parts={},{}
  for i,r in ipairs(requests) do
    if not probe_request_ok(r) then error('sys: probe request',0) end
    local f={h=base..'-'..i..'.h',b=base..'-'..i..'.b',w=base..'-'..i..'.w',r=base..'-'..i..'.r'}
    files[i]=f
    local argv={M.CURL,'-q','-s','--http1.1','--proto','=https','--max-redirs','0','-m',string.format('%d',r.seconds),
      '--interface',device,'--resolve',r.hostname..':443:'..r.address,
      '-H','Accept: application/dns-json, application/dns-message, text/plain',
      '--max-filesize','32769','-D',f.h,'-o',f.b,'-w','%{time_total}','https://'..r.hostname..r.path}
    local words={}
    for k,a in ipairs(argv) do words[k]=quote(a) end
    local line=table.concat(words,' ')
    if have_timeout==nil then have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0 end
    if have_timeout then line='timeout '..string.format('%d',r.seconds+1)..' '..line end
    parts[#parts+1]='( '..line..' >'..quote(f.w)..' 2>/dev/null; echo $? >'..quote(f.r)..' ) &'
  end
  local marker=base..'.done'
  if #files==0 then return files,nil end
  local group='( '..table.concat(parts,' ')..' wait; : >'..quote(marker)..' ) </dev/null >/dev/null 2>&1'..closing()..' &'
  if os.execute(group)~=0 then return files,nil end
  return files,marker
end
-- one UDP question through the device; -> data or nil, kind ('unavailable' | 'transport' | 'timeout')
local function dns_exchange(device,dns)
  if not nixio or not nixio.socket or type(dns.host)~='string' or not string.find(dns.host,'^%d+%.%d+%.%d+%.%d+$') then return nil,'unavailable' end
  local sock=nil
  local opened=pcall(function()
    sock=assert(nixio.socket('inet','dgram'))
    assert(sock:setopt('socket','bindtodevice',device))
    assert(sock:setblocking(false))
    assert(sock:connect(dns.host,dns.port))
  end)
  local function close() if sock then pcall(function() sock:close() end) end end
  if not opened then close();return nil,'unavailable' end
  local deadline=M.clock()+dns.seconds
  if not pcall(function() assert(sock:send(dns.packet)) end) then close();return nil,'transport' end
  local eagain=(nixio.const and nixio.const.EAGAIN) or 11
  local flags=nil
  if nixio.poll and nixio.poll_flags then pcall(function() flags=nixio.poll_flags('in') end) end
  local idle=0
  while true do
    local data,code=sock:recvfrom(4096)
    if type(data)=='string' then
      if dns.accept(data) then close();return data end
    elseif data==nil and code~=eagain and code~=11 then close();return nil,'transport' end
    local left=deadline-M.clock()
    if left<=0 then close();return nil,'timeout' end
    if type(data)~='string' then
      -- poll until readable; should poll ever return at once without data, fall back to 20 ms naps (bounded CPU)
      idle=idle+1
      local polled=false
      if flags and idle<=20 then
        local ok,count=pcall(nixio.poll,{{fd=sock,events=flags}},math.max(1,math.floor(left*1000)))
        polled=ok and type(count)=='number'
      end
      if not polled then M.sleep(math.min(0.02,left)) end
    end
  end
end
-- probe_io(device, requests, dns) -> answers, dns_data|nil, dns_kind (see live_probe.lua)
function M.probe_io(device,requests,dns)
  if not probe_word(device,15) then error('sys: probe device',0) end
  local started=M.clock()
  local longest=0
  for _,r in ipairs(requests) do if type(r)=='table' and type(r.seconds)=='number' and r.seconds>longest then longest=r.seconds end end
  -- curl first: the children must not inherit the DNS socket
  local files,marker=https_start(device,requests)
  local dns_data,dns_kind=nil,nil
  if dns then dns_data,dns_kind=dns_exchange(device,dns) end
  local finished=marker~=nil and present(marker)
  if marker then
    local limit=started+longest+3
    while not finished and M.clock()<limit do M.sleep(0.02);finished=present(marker) end
  end
  local total=M.clock()-started
  local answers={}
  for i,f in ipairs(files) do
    local code=tonumber(string.match(read_small(f.r,16) or '','^(%d+)'))
    local headers,body,w=read_small(f.h,40000),read_small(f.b,40000),read_small(f.w,64)
    if finished then os.remove(f.h);os.remove(f.b);os.remove(f.w);os.remove(f.r) end
    local response,kind
    if marker==nil then kind='transport-error' else response,kind=M.curl_answer(code,headers,body) end
    answers[i]={response=response,kind=kind,elapsed=tonumber(string.match(w or '','^%s*([0-9]+%.?[0-9]*)')) or total}
  end
  if finished then os.remove(marker) end
  return answers,dns_data,dns_kind
end

local machine=nil
function M.machine()
  if machine==nil then local rc,out=M.exec({'uname','-m'});machine=rc==0 and string.match(out,'^(%S+)') or '' end
  return machine
end

return M
