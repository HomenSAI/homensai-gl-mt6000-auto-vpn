-- Router self-test of the real sys.lua (run on the MT3000 from a copy in /tmp, never against the service):
--   lua router_sys_selftest.lua <lua-dir> <scratch-dir>
-- Exercises every sys call with the router's own nixio/libubus/libuci, in a scratch directory only.
-- The backend tests on the PC use a fake sys, so platform differences (nixio argument forms) show up here.
-- Prints one JSON line: {"ok":<all passed>,"checks":{name:"ok"|error}}.
local dir,scratch=arg[1],arg[2]
package.path=dir..'/?.lua;'..package.path
local canon=require('canon')
canon.configure({runtime=scratch})
local runner=require('runner')
local sys=require('sys')
sys.RUNTIME=scratch
local checks,all={},true
local function check(name,fn)
  local ok,err=pcall(fn)
  if ok then checks[name]='ok'
  else all=false;checks[name]=type(err)=='table' and ('code '..tostring(err.code)) or tostring(err) end
end
local function want(v,msg) if not v then error(msg,2) end end

check('have_nixio',function() want(sys.have_nixio,'nixio.fs missing') end)
check('mkdir_700',function()
  local d=scratch..'/d-'..sys.unique()
  want(sys.mkdir(d,448),'mkdir failed')
  local st=sys.lstat_exact(d);want(st and st.type=='dir' and st.mode==448,'mode '..tostring(st and st.mode))
  local st2=sys.lstat(d);want(st2 and st2.mode==448,'nixio mode '..tostring(st2 and st2.mode))
  want(not sys.mkdir(d,448),'second mkdir must fail')
  sys.rmdir(d);want(not sys.exists(d),'rmdir')
end)
check('mkdir_755',function()
  local d=scratch..'/e-'..sys.unique()
  want(sys.mkdir(d,493),'mkdir failed')
  local st=sys.lstat_exact(d);want(st.mode==493,'mode '..tostring(st.mode))
  sys.rmdir(d)
end)
check('create_exclusive',function()
  local p=scratch..'/x-'..sys.unique()
  want(sys.create_exclusive(p,'abc'),'create failed')
  want(not sys.create_exclusive(p,'abc'),'second create must fail')
  want(sys.read(p)=='abc','content')
  local st=sys.lstat_exact(p);want(st.mode==384,'mode '..tostring(st.mode))
  sys.remove(p)
end)
check('write_private',function()
  local p=scratch..'/w-'..sys.unique()..'.json'
  sys.write_private(p,'{"a":1}')
  want(sys.read(p)=='{"a":1}','content')
  local st=sys.lstat_exact(p);want(st.mode==384,'mode '..tostring(st.mode))
  sys.remove(p)
end)
check('lstat_symlink_key_dir',function()
  local p=scratch..'/l-'..sys.unique()
  os.execute("ln -s /etc/config/network '"..p.."'")
  local st=sys.lstat(p);want(st and st.type=='lnk','lstat type '..tostring(st and st.type))
  local st2=sys.stat(p);want(st2 and st2.type=='reg','stat type '..tostring(st2 and st2.type))
  want(sys.key('/nonexistent-'..sys.unique())=='absent','absent key')
  want(string.find(sys.key('/etc/config/network'),'^reg:'),'key '..sys.key('/etc/config/network'))
  local names=sys.dir(scratch);local seen=false
  for _,n in ipairs(names or {}) do if scratch..'/'..n==p then seen=true end end
  want(seen,'dir listing')
  sys.remove(p)
end)
check('sticky_tmp_and_lstat_exact',function()
  local st=sys.lstat_exact('/tmp');want(st and st.type=='dir' and st.mode==1023,'tmp mode '..tostring(st and st.mode))
  local cfg=sys.lstat_exact('/etc/config/network');want(cfg and cfg.type=='reg' and cfg.uid==0 and cfg.mode,'config')
end)
check('read_limit',function()
  want(sys.read('/proc/version',4096),'read')
  want(not pcall(sys.read,'/proc/version',5),'oversize refused')
end)
check('exec_and_input',function()
  local rc,out=sys.exec({'echo','a b'});want(rc==0 and out=='a b\n','echo '..tostring(rc)..' '..tostring(out))
  rc,out=sys.exec({'cat'},{input='xyz',timeout=5});want(rc==0 and out=='xyz','input')
  rc=sys.exec({'sh','-c','exit 7'});want(rc==7,'rc '..tostring(rc))
  want(not pcall(sys.command,{'false'}),'command refuses')
  want(not pcall(sys.exec,{'echo',"a'b"}),'quote refused')
end)
check('spawn_wait',function()
  local h=sys.spawn({'sh','-c','sleep 1; exit 3'},{timeout=5});want(h,'spawn')
  want(sys.wait(h,10)==3,'wait')
end)
check('guard_release_line',function()
  local seen;local execute=os.execute
  os.execute=function(line) seen=line;return 0 end
  local ok,err=pcall(sys.guard_release,'0a1b2c3d',75,'homensai_guard')
  os.execute=execute
  want(ok,tostring(err))
  local word=string.match(seen,'^%(setsid sh %-c (.-) || sh %-c ')
  local p=io.popen('printf %s '..word);local back=p:read('*a');p:close()
  want(back==[[sleep 75; nft delete element inet homensai_guard blocked_lan_0a1b2c3d '{ "br-lan" }' 2>/dev/null || :]],back)
end)
check('ubus',function()
  local b=sys.ubus('system','board');want(canon.is_object(b) and b.board_name,'board')
end)
check('uci_cursor',function()
  local c=sys.uci_cursor();want(c,'cursor')
end)
check('machine_euid_clock',function()
  want(sys.machine()=='aarch64','machine '..tostring(sys.machine()))
  want(sys.euid()==0,'euid')
  local a=sys.clock();sys.sleep(0.2);want(sys.clock()-a>=0.15,'sleep')
end)
check('runner_fs',function()
  local p=scratch..'/r-'..sys.unique()
  runner.fs.write_atomic(p,'1');want(sys.read(p)=='1','write_atomic')
  sys.remove(p)
end)
-- Power-cut primitive (durable.lua): the fsync of a directory through nixio.open(dir,'r'):sync() is the one nixio
-- use the PC cannot exercise. /etc is the UBIFS overlay: an fsync of the directory only flushes, it changes nothing.
check('durable_write_dir_sync_sweep',function()
  local durable=require('durable')
  want(durable.have_nixio,'nixio missing')
  local p=scratch..'/dur-'..sys.unique()..'.json'
  durable.write(p,'{"a":1}',{sync=true})
  want(sys.read(p)=='{"a":1}','content')
  local st=sys.lstat_exact(p);want(st.mode==384,'mode '..tostring(st.mode))
  want(durable.sync_directory(scratch),'fsync of a tmpfs directory')
  want(durable.sync_directory('/etc/config'),'fsync of an overlay directory')
  local leftover=scratch..'/.x.json.dead-1.pending'
  local f=io.open(leftover,'wb');f:write('x');f:close()
  want(durable.sweep(scratch,120,os.time())==0,'a fresh .pending is kept')
  want(durable.sweep(scratch,120,os.time()+1000)==1,'an old .pending is removed')
  want(not sys.exists(leftover),'gone')
  sys.remove(p)
end)
check('chunk_stdin',function()
  want(sys.chunk('echo_stdin',"print(io.read('*a'))",'abc')=='abc\n','stdin')
end)
-- The pair network read and write exactly as the supervisor runs them in-process (net.lua), the write
-- against a COPY of /etc/config/network in the scratch directory: the router's config never changes.
check('network_read_write_on_copy',function()
  local net=require('net')
  local cjson=require('cjson')
  local before=sys.read('/etc/config/network')
  local text=sys.chunk('pair_network_read',net.NETWORK_READ)
  local sections=cjson.decode(text)
  want(type(sections)=='table' and #sections>0,'read')
  local managed,iface,value={},nil,nil
  for _,s in ipairs(sections) do
    local name=s['.name']
    if (s.proto=='wgclient' and string.find(name,'^wgclient%d+$')) or (s.proto=='ovpnclient' and string.find(name,'^ovpnclient%d+$')) then
      managed[name]=s.proto
      if not iface then iface=name;value=(s.disabled=='1') and '0' or '1' end
    end
  end
  local count=0;for _ in pairs(managed) do count=count+1 end
  want(count==2,'two managed clients, got '..count)
  local conf=scratch..'/conf';sys.mkdir(conf,448)
  local f=io.open(conf..'/network','wb');f:write(before);f:close()
  local stage=scratch..'/stage';sys.mkdir(stage,448)
  local source,n=string.gsub(net.NETWORK_WRITE,"u%.cursor%('/etc/config',q%.stage%)","u.cursor('"..conf.."',q.stage)")
  want(n==1,'confdir substitution')
  local payload=cjson.encode({stage=stage,expected=sections,interface=iface,value=value,managed=managed})
  local ok,err=pcall(sys.chunk,'pair_network_write_copy',source,payload)
  want(ok,'write: '..tostring(err))
  local copy=sys.read(conf..'/network')
  want(copy~=before,'the copy changed')
  local c=require('uci').cursor(conf,stage)
  want(c:get('network',iface,'disabled')==value,'value in the copy')
  want(sys.read('/etc/config/network')==before,'the real network config is unchanged')
end)
-- The live probe I/O (plan item 4) with the router's own nixio and curl, bound to the loopback device: nothing
-- leaves the router (1.1.1.1/9.9.9.9 are not reachable through lo), but the curl group, its files and marker,
-- and every nixio socket call (bindtodevice, setblocking, connect, send, recvfrom, poll) really run.
check('probe_io_on_lo',function()
  want(sys.probe_capable(),'probe_capable (nixio bindtodevice + '..sys.CURL..')')
  local started=sys.clock()
  local answers,data,kind=sys.probe_io('lo',{{address='1.1.1.1',hostname='one.one.one.one',path='/cdn-cgi/trace',seconds=2},
    {address='8.8.8.8',hostname='dns.google',path='/resolve?name=example.com&type=A',seconds=2}},
    {host='9.9.9.9',port=53,packet=string.rep('\0',12),seconds=1,accept=function() return true end})
  want(#answers==2,'two answers')
  for i=1,2 do want(answers[i].response==nil and type(answers[i].kind)=='string','answer '..i..' must fail on lo, got '..tostring(answers[i].kind)) end
  want(data==nil and type(kind)=='string','dns on lo: '..tostring(kind))
  want(sys.clock()-started<6,'bounded time')
  local left=sys.dir(scratch) or {}
  for _,name in ipairs(left) do want(not string.find(name,'^%.probe%-'),'probe file left: '..name) end
end)
print(canon.encode(canon.object({ok=all,checks=canon.object(checks)})))
