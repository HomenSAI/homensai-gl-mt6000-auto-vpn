-- monitor_io.lua on the PC: the curl argument list (no shell, constant options), curl exit codes and header
-- parsing, refusal of unsafe arguments, the non-blocking try_lock against a real flock holder, capabilities.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local io_=require('monitor_io')

local base=(os.getenv('TMPDIR') or '/tmp')..'/homensai-io-test-'..tostring(os.time())..'-'..tostring(math.random(100000))
os.execute('mkdir -p '..base)
io_.configure({RUNTIME=base})

local function write(path,text) local f=assert(io.open(path,'wb'));f:write(text);f:close() end
local function argument(argv,name) for i,v in ipairs(argv) do if v==name then return argv[i+1] end end end

t.test('https_get: constant curl argv bound to the device, certificate for the hostname, files removed',function()
  local seen
  io_.spawn=function(argv,seconds,cb)
    seen={argv=argv,seconds=seconds}
    write(argument(argv,'-D'),'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\n\r\n')
    write(argument(argv,'-o'),'ip=93.184.216.34\nhttp=http/1.1\n')
    cb(0)
  end
  local response,kind=t.await({},function(cb) io_.https_get('wgclient1','1.1.1.1','one.one.one.one','/cdn-cgi/trace',6,cb) end)
  t.eq(kind,nil);t.eq(response,{status=200,body='ip=93.184.216.34\nhttp=http/1.1\n'})
  local argv=seen.argv
  t.eq(argv[1],'/usr/bin/curl');t.eq(argv[2],'-q','-q must be first: no curlrc')
  t.eq(argument(argv,'--interface'),'wgclient1');t.eq(argument(argv,'--resolve'),'one.one.one.one:443:1.1.1.1')
  t.eq(argument(argv,'-m'),'6');t.eq(argument(argv,'--proto'),'=https');t.eq(argument(argv,'--max-redirs'),'0')
  t.eq(argv[#argv],'https://one.one.one.one/cdn-cgi/trace')
  for _,v in ipairs(argv) do t.truthy(not string.find(v,'[;|&`$<>]') or v=='https://one.one.one.one/cdn-cgi/trace','no shell syntax: '..v) end
  t.eq(seen.seconds,7)
  t.eq(io_.file_size(argument(argv,'-D')),nil);t.eq(io_.file_size(argument(argv,'-o')),nil)
end)

t.test('https_get: curl exit codes and status lines map to the Python detail results',function()
  local function run(code,head,body)
    io_.spawn=function(argv,seconds,cb)
      if head then write(argument(argv,'-D'),head) end
      if body then write(argument(argv,'-o'),body) end
      cb(code)
    end
    return t.await({},function(cb) io_.https_get('wgclient1','8.8.8.8','dns.google','/resolve?name=example.com&type=A',6,cb) end)
  end
  t.eq({run(28)},{nil,'timeout'});t.eq({run(60)},{nil,'tls-error'});t.eq({run(35)},{nil,'tls-error'})
  t.eq({run(63)},{nil,'invalid-response'});t.eq({run(7)},{nil,'transport-error'});t.eq({run(0)},{nil,'transport-error'},'no header file')
  t.eq(run(0,'HTTP/1.1 426 Upgrade Required\r\n\r\n',''),{status=426,body=''})
  t.eq({run(0,'garbage\r\n\r\n','x')},{nil,'invalid-response'})
  io_.spawn=function(argv,seconds,cb) cb(nil,'timeout') end
  t.eq({t.await({},function(cb) io_.https_get('wgclient1','8.8.8.8','dns.google','/x',6,cb) end)},{nil,'timeout'})
  local called=false
  io_.spawn=function() called=true end
  t.eq({t.await({},function(cb) io_.https_get('wg client','8.8.8.8','dns.google','/x',6,cb) end)},{nil,'transport-error'})
  t.eq({t.await({},function(cb) io_.https_get('wgclient1','8.8.8.8;id','dns.google','/x',6,cb) end)},{nil,'transport-error'})
  t.eq({t.await({},function(cb) io_.https_get('wgclient1','8.8.8.8','dns.google','/x y',6,cb) end)},{nil,'transport-error'})
  t.eq(called,false,'unsafe arguments never reach a child')
end)

t.test('without an event loop the socket and child primitives refuse instead of blocking',function()
  local _,kind=t.await({},function(cb) io_.datagram('udp','wgclient1','9.9.9.9',53,'x',3,function() return true end,cb) end)
  t.eq(kind,'unavailable')
  local rc
  rc,kind=t.await({},function(cb) io_.bridge(base..'/status-bridge.json',cb) end)
  t.eq(rc,nil);t.eq(kind,'unavailable')
end)

t.test('try_lock: free -> runs; held by another process (flock) -> false at once',function()
  t.eq({io_.try_lock(base,function() return 42 end)},{true,42})
  os.execute('flock -x '..base..'/auto-control.lock sleep 3 >/dev/null 2>&1 &')
  os.execute('sleep 0.5')
  local started=os.time()
  t.eq(io_.try_lock(base,function() return 1 end),false)
  t.truthy(os.time()-started<=1,'never waits')
  t.eq(io_.try_lock('/bad dir',function() return 1 end),false)
  t.eq(io_.try_lock(base,function() return 1 end,'../x'),false)
end)

t.test('capabilities: a record without SO_MARK or TLS requirements',function()
  local caps=io_.capabilities()
  t.eq(caps.so_mark_required,false);t.eq(caps.https,'curl --interface');t.eq(caps.probes,'device-bound (SO_BINDTODEVICE), no fwmark')
  t.truthy(type(caps.nixio)=='boolean' and type(caps.raw_icmp)=='boolean')
end)

t.test('write_ram and file_key',function()
  local path=base..'/x.json'
  io_.write_ram(path,'{"a":1}')
  t.eq(io_.read_file(path),'{"a":1}')
  t.truthy(io_.file_key(path)~=nil);t.eq(io_.file_key(base..'/missing'),nil)
  t.eq(pcall(io_.write_ram,base..'/../y','x'),false)
end)

t.test('cleanup',function() os.execute('rm -rf '..base) end)

t.test('capture: output through a RAM file (no pipe to interrupt), exit status kept, no file left',function()
  os.execute('mkdir -p '..base)
  t.eq(io_.capture('printf abc'),'abc')
  t.eq(io_.capture('printf x; exit 3'),nil)
  t.eq(io_.capture('true'),'')
  local p=io.popen('ls -a '..base);local names=p:read('*a');p:close()
  t.eq(string.find(names,'%.cmd%-'),nil,'no temporary output file left')
  os.execute('rm -rf '..base)
end)

t.test('datagram: raw ICMP is sent with sendto (the router nixio refuses connect(host,0)); UDP stays connected',function()
  local log={}
  local fd_cb
  local function sock()
    local s={}
    function s:setopt() return true end
    function s:setblocking() return true end
    function s:connect(host,port) log[#log+1]={'connect',host,port};if port==0 then return nil,-8,'Unrecognized service' end;return true end
    function s:sendto(packet,host,port) log[#log+1]={'sendto',host,port};return #packet end
    function s:send(packet) log[#log+1]={'send'};return #packet end
    function s:fileno() return 7 end
    function s:recvfrom() return 'reply','1.1.1.1' end
    function s:close() end
    return s
  end
  local saved={nixio=package.loaded['nixio'],mio=package.loaded['monitor_io']}
  package.loaded['nixio']={socket=function() return sock() end}
  local loop={ULOOP_READ=1,fd_add=function(fd,cb) fd_cb=cb;return {delete=function() end} end,
    timer=function(cb) return {set=function() end,cancel=function() end} end}
  package.loaded['monitor_io']=nil
  local ok,err=pcall(function()
    local m=require('monitor_io')
    m.attach_loop(loop)
    local got
    m.datagram('icmp','wgclient1','1.1.1.1',0,'pkt',1,function() return true end,function(data) got=data end)
    t.eq(log,{{'sendto','1.1.1.1',0}},'no connect for ICMP')
    fd_cb();t.eq(got,'reply')
    log={}
    m.datagram('udp','wgclient1','9.9.9.9',53,'q',3,function() return true end,function() end)
    t.eq(log,{{'connect','9.9.9.9',53},{'send'}})
  end)
  package.loaded['nixio'],package.loaded['monitor_io']=saved.nixio,saved.mio
  if not ok then error(err,0) end
end)

t.run()
