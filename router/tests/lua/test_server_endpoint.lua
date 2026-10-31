-- server_endpoint.lua: the peer address of a live VPN client (server_endpoint.py in Lua) - parsing, the
-- WireGuard and OpenVPN paths over a fake world, the per-epoch cache of the monitor, the probe/monitor wiring.
-- Same-as-Python checks: tests/test_lua_server_endpoint.py drives `--observe <world.json>` against
-- server_endpoint.observe on the same fixtures.
local here=(arg[0]:match('^(.*)/[^/]*$') or '.')
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..here..'/?.lua;'..package.path
local canon=require('canon')
local E=require('server_endpoint')

-- A world: files (a string, or a list read in order with the last one repeating), links, dirs, wg output.
local function world_fs(w)
  local seen={}
  local F={wg_calls=0,now=w.clock or 100}
  function F.read(path,limit)
    if w.errors and w.errors[path] then return false end
    local v=w.files[path]
    if v==nil or v==canon.null then return nil end
    if type(v)=='table' then
      seen[path]=(seen[path] or 0)+1
      v=v[math.min(seen[path],#v)]
    end
    return string.sub(v,1,limit+1)
  end
  function F.readlink(path) local v=(w.links or {})[path];return type(v)=='string' and v or nil end
  function F.dir(path) local v=(w.dirs or {})[path];if type(v)~='table' or v==canon.null then return nil end;return v end
  function F.clock() F.now=F.now+(w.clock_step or 0);return F.now end
  function F.wg(interface)
    F.wg_calls=F.wg_calls+1
    local v=w.wg
    if type(v)=='table' and v~=canon.null then seen.wg=(seen.wg or 0)+1;v=v[math.min(seen.wg,#v)] end
    if v==nil or v==canon.null then return nil end
    return v
  end
  return F
end

-- Differential mode for tests/test_lua_server_endpoint.py
if arg[1]=='--observe' then
  local f=assert(io.open(arg[2],'rb'));local text=f:read('*a');f:close()
  local cases=canon.decode(text)
  local out=canon.array()
  for _,case in ipairs(cases) do
    local value=E.observe(case.profile,case.now,world_fs(case.world))
    out[#out+1]=value and canon.object(value) or canon.null
  end
  io.write(canon.encode(out))
  os.exit(0)
end
if arg[1]=='--address' then
  local f=assert(io.open(arg[2],'rb'));local text=f:read('*a');f:close()
  local out=canon.array()
  for _,value in ipairs(canon.decode(text)) do
    local ok,host,port=pcall(E.address,value)
    out[#out+1]=ok and canon.array({host,port}) or canon.null
  end
  io.write(canon.encode(out))
  os.exit(0)
end

local t=dofile(here..'/harness.lua')

local WG={id='wireguard:peer_1',protocol='wireguard',interface='wgclient1'}
local OVPN={id='openvpn:1_1',protocol='openvpn',interface='ovpnclient1'}
local function wg_world(output,ifindex) return {files={['/sys/class/net/wgclient1/ifindex']=ifindex or '7\n'},wg=output} end
local STAT='4242 (openvpn) S 1 4242 4242 0 -1 4194560 300 0 0 0 5 7 0 0 20 0 1 0 12345 5000000 900 4294967295'
local function ovpn_world(extra)
  local w={files={['/sys/class/net/ovpnclient1/ifindex']='9\n',['/var/run/ovpnclient-ovpnclient1.pid']='4242\n',
    ['/proc/4242/comm']='openvpn\n',['/proc/4242/stat']=STAT,
    ['/proc/4242/cmdline']='/usr/sbin/openvpn\0--cd\0/etc/openvpn\0--dev\0ovpnclient1\0--config\0x.ovpn\0',
    ['/proc/4242/net/udp']='  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n'..
      '   1: 0200A8C0:A1B2 086433C6:04AA 01 00000000:00000000 00:00000000 00000000     0        0 55 2 00000000 0\n'..
      '   2: 00000000:0035 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 77 2 00000000 0\n'},
    links={['/proc/4242/fd/0']='/dev/null',['/proc/4242/fd/3']='socket:[55]',['/proc/4242/fd/4']='anon_inode:[eventfd]',['/proc/4242/fd/5']='/dev/net/tun'},
    dirs={['/proc/4242/fd']={'0','3','4','5'}}}
  for k,v in pairs(extra or {}) do w.files[k]=v end
  return w
end

t.test('address: the server_endpoint.address rules (IPv4, IPv6, mapped, refusals)',function()
  local function a(v) local ok,h,p=pcall(E.address,v);if ok then return h..'#'..p end;return nil end
  t.eq(a('198.51.100.8:1194'),'198.51.100.8#1194')
  t.eq(a('[2001:db8::1]:51820'),'2001:db8::1#51820')
  t.eq(a('[2001:0DB8:0:0:0:0:0:000A]:1'),'2001:db8::a#1')
  t.eq(a('[::ffff:198.51.100.7]:443'),'198.51.100.7#443')
  t.eq(a('[1:0:0:2:0:0:0:3]:9'),'1:0:0:2::3#9')
  t.eq(a('[1:0:0:2:0:0:3:4]:9'),'1::2:0:0:3:4#9','the first of two equal zero runs')
  t.eq(a('[1:0:2:3:4:5:6:7]:9'),'1:0:2:3:4:5:6:7#9','a single zero hextet is not compressed')
  t.eq(a('[::1.2.3.4]:9'),'::102:304#9')
  t.eq(a('[fe80::1%wg0]:51820'),'fe80::1%wg0#51820')
  for _,bad in ipairs({'(none)','host.example:443','user:secret@198.51.100.1:443','127.0.0.1:7505','0.0.0.0:0','198.51.100.1:65536',
    'https://198.51.100.1:443','[::1]:5','[::]:5','[ff02::1]:5','224.0.0.1:5','198.51.100.1:0','01.2.3.4:5','1.2.3.256:5','[1::2::3]:5',
    '[1:2:3:4:5:6:7:8:9]:5','198.51.100.1:','198.51.100.1','[2001:db8::1]:5:6',string.rep('1',101)}) do
    t.eq(a(bad),nil,bad)
  end
end)

t.test('proc_address and socket_peers: owned sockets only, established TCP only, byte order',function()
  t.eq({E.proc_address('086433C6:04AA',false)},{'198.51.100.8',1194})
  t.truthy(not pcall(E.proc_address,'0100007F:04AA',false),'loopback refused')
  t.truthy(not pcall(E.proc_address,'00000000:0000',false),'unconnected socket refused')
  t.truthy(not pcall(E.proc_address,'086433C6',false))
  t.eq({E.proc_address('B80D0120000000000000000001000000:CA6C',true)},{'2001:db8::1',51820})
  t.eq({E.proc_address('0000000000000000FFFF0000086433C6:01BB',true)},{'198.51.100.8',443})
  local text='header\n0: 00000000:0000 086433C6:04AA 01 0 0 0 0 0 55\n1: 00000000:0000 096433C6:01BB 01 0 0 0 0 0 99\n2: 00000000:0000 0A6433C6:01BB 02 0 0 0 0 0 55\n'
  local peers=E.socket_peers(text,{['55']=true},'tcp',false)
  local list={};for _,p in pairs(peers) do list[#list+1]=p end
  t.eq(list,{{'198.51.100.8',1194,'tcp'}})
  t.eq(next(E.socket_peers(text,{missing=true},'tcp',false)),nil)
  t.eq(next(E.socket_peers(string.rep('x',65537),{['55']=true},'tcp',false)),nil)
end)

t.test('process_epoch: the start time, not CPU counters; truncation refused',function()
  t.eq(E.process_epoch(STAT),'12345')
  t.eq(E.process_epoch('1 (a) b) S'..string.rep(' 0',18)..' 777'),'777','the last parenthesis ends the command name')
  for _,bad in ipairs({'','123 (openvpn) S','no closing parenthesis'}) do t.truthy(not pcall(E.process_epoch,bad),bad) end
end)

t.test('WireGuard: one peer, interface epoch, ambiguity and refusals',function()
  local found=E.observe(WG,100,world_fs(wg_world('public-key-not-exported\t198.51.100.2:51820\n')))
  t.eq(found,{profile='wireguard:peer_1',interface='wgclient1',host='198.51.100.2',port=51820,transport='udp',time=100,source='live-kernel-peer'})
  t.eq(E.observe(WG,100,world_fs(wg_world('a\t198.51.100.2:51820\nb\t198.51.100.3:51820\n'))),nil,'two peers')
  t.eq(E.observe(WG,100,world_fs(wg_world('a\t198.51.100.2:51820\nb\t198.51.100.2:51820\n'))).host,'198.51.100.2','the same peer twice is one peer')
  t.eq(E.observe(WG,100,world_fs(wg_world('a\t(none)\n'))),nil)
  t.eq(E.observe(WG,100,world_fs(wg_world(''))),nil)
  t.eq(E.observe(WG,100,world_fs(wg_world(nil))),nil,'wg failed')
  t.eq(E.observe(WG,100,world_fs(wg_world('a\t198.51.100.2:51820\n',{'7\n','8\n'}))),nil,'ifindex changed during the read')
  t.eq(E.observe(WG,100,world_fs({files={},wg='a\t198.51.100.2:51820\n'})),nil,'no interface')
  local slow=wg_world('a\t198.51.100.2:51820\n');slow.clock_step=0.6
  t.eq(E.observe(WG,100,world_fs(slow)),nil,'over the 0.5 s bound')
  for _,interface in ipairs({'wgclient1; reboot','eth0','../../etc/shadow','wgclient10000','wgclient'}) do
    local fs=world_fs(wg_world('a\t198.51.100.2:51820\n'))
    t.eq(E.observe({id='wireguard:peer_1',protocol='wireguard',interface=interface},100,fs),nil,interface);t.eq(fs.wg_calls,0,'no command for '..interface)
  end
  t.eq(E.observe({id='openvpn:1_1',protocol='wireguard',interface='wgclient1'},100,world_fs(wg_world('a\t198.51.100.2:51820\n'))),nil,'id/protocol mismatch')
end)

t.test('OpenVPN: the owned connected socket of the client process, bound to its epoch',function()
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world())),{profile='openvpn:1_1',interface='ovpnclient1',host='198.51.100.8',port=1194,transport='udp',time=5,source='live-kernel-peer'})
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world({['/proc/4242/stat']={STAT,(string.gsub(STAT,'12345','12399'))}}))),nil,'restarted process')
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world({['/proc/4242/comm']='sh\n'}))),nil)
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world({['/proc/4242/cmdline']='openvpn\0--dev\0ovpnclient2\0'}))),nil)
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world({['/proc/4242/cmdline']='openvpn\0--dev\0ovpnclient1\0--dev\0ovpnclient1\0'}))),nil)
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world({['/var/run/ovpnclient-ovpnclient1.pid']='1\n'}))),nil)
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world({['/var/run/ovpnclient-ovpnclient1.pid']=canon.null}))),nil)
  local tcp=ovpn_world({['/proc/4242/net/tcp']='h\n0: 0200A8C0:A1B2 146433CB:01BB 01 0 0 0 0 0 56\n'})
  tcp.links['/proc/4242/fd/6']='socket:[56]';tcp.dirs['/proc/4242/fd'][5]='6'
  t.eq(E.observe(OVPN,5,world_fs(tcp)),nil,'two connections: never guess')
  local many=ovpn_world();for i=6,262 do many.dirs['/proc/4242/fd'][#many.dirs['/proc/4242/fd']+1]=tostring(i) end
  t.eq(E.observe(OVPN,5,world_fs(many)),nil,'more than 256 descriptors')
  local unreadable=ovpn_world();unreadable.errors={['/proc/4242/net/udp']=true}
  t.eq(E.observe(OVPN,5,world_fs(unreadable)),nil,'an unreadable socket table is an error, not a missing one')
  t.eq(E.observe(OVPN,5,world_fs(ovpn_world({['/proc/4242/net/udp']=canon.null}))),nil,'no socket table: no peer')
end)

t.test('Observer: wg runs once per tunnel epoch, refreshed after REFRESH, retried after RETRY; OpenVPN never cached',function()
  local w=wg_world('a\t198.51.100.2:51820\n')
  local fs=world_fs(w)
  local o=E.Observer(fs,{refresh=300,retry=60})
  t.eq(o:observe(WG,100).time,100);t.eq(fs.wg_calls,1)
  fs.now=fs.now+30
  local again=o:observe(WG,130)
  t.eq(again.time,130,'the confirmed peer is published with this pass');t.eq(again.host,'198.51.100.2');t.eq(fs.wg_calls,1,'no wg for the same epoch')
  w.files['/sys/class/net/wgclient1/ifindex']='8\n'
  w.wg='a\t198.51.100.9:51820\n'
  t.eq(o:observe(WG,140).host,'198.51.100.9','a new interface epoch reads the peer again');t.eq(fs.wg_calls,2)
  fs.now=fs.now+301
  o:observe(WG,500);t.eq(fs.wg_calls,3,'refresh after REFRESH seconds')
  w.wg=nil;fs.now=fs.now+301
  t.eq(o:observe(WG,900),nil);t.eq(fs.wg_calls,4)
  fs.now=fs.now+30;t.eq(o:observe(WG,930),nil);t.eq(fs.wg_calls,4,'a missing peer is retried only after RETRY')
  w.wg='a\t198.51.100.9:51820\n';fs.now=fs.now+31;t.eq(o:observe(WG,961).host,'198.51.100.9');t.eq(fs.wg_calls,5)
  w.files['/sys/class/net/wgclient1/ifindex']=nil
  t.eq(o:observe(WG,970),nil,'interface gone');t.eq(o.memo[WG.id],nil)
  o:retain({});t.eq(next(o.memo),nil)
  local ow=ovpn_world();local ofs=world_fs(ow);local reads=0;local read=ofs.read
  ofs.read=function(path,limit) if path=='/proc/4242/comm' then reads=reads+1 end;return read(path,limit) end
  local oo=E.Observer(ofs)
  oo:observe(OVPN,1);oo:observe(OVPN,2);t.eq(reads,2,'OpenVPN: /proc read every pass')
  t.eq(E.Observer(nil):observe(WG,1),nil,'no file view: nothing observed')
end)

t.test('probe: server_endpoint attached after the route identity check, never on a changed identity, faults ignored',function()
  local mh=dofile(here..'/monitor_harness.lua')
  local probe=require('probe')
  local R=mh.fake_runner()
  local profile=R.inventory_data.profiles[2]
  local seen
  local function endpoint(p,now) seen=p.id;return {profile=p.id,interface=p.interface,host='198.51.100.2',port=51820,transport='udp',time=now,source='live-kernel-peer'} end
  local result
  probe.probe(R,profile,function(r) result=r end,endpoint)
  t.eq(seen,'wireguard:peer_8');t.eq(result.server_endpoint.host,'198.51.100.2');t.eq(result.server_endpoint.time,R.now)
  R.https_status=503
  probe.probe(R,profile,function(r) result=r end,endpoint)
  t.eq(result.code,'VPN-003');t.eq(result.server_endpoint.host,'198.51.100.2','Python attaches it whatever the health code')
  R.https_status=200
  probe.probe(R,profile,function(r) result=r end,function() error('boom') end)
  t.eq(result.code,nil);t.eq(result.server_endpoint,nil);t.truthy(#R.logs>0,'the fault is logged')
  probe.probe(R,profile,function(r) result=r end)
  t.eq(result.server_endpoint,nil,'no observer: no field')
end)

t.test('monitor: the published status row carries the peer address of its channel (wg read once per epoch)',function()
  local mh=dofile(here..'/monitor_harness.lua')
  local monitor=require('monitor')
  local R=mh.fake_runner()
  local fs=world_fs({files={['/sys/class/net/wgclient2/ifindex']='21\n'},wg='k\t[2001:db8::7]:51820\n'})
  local m=monitor.new(R,{endpoint_fs=fs})
  local status=m:pass()
  local row
  for _,p in ipairs(status.profiles) do if p.id=='wireguard:peer_8' then row=p end end
  t.eq(row.server_endpoint.host,'2001:db8::7');t.eq(row.server_endpoint.interface,'wgclient2');t.eq(row.server_endpoint.source,'live-kernel-peer')
  for _,p in ipairs(status.profiles) do if p.id~='wireguard:peer_8' then t.eq(p.server_endpoint,nil,p.id) end end
  t.truthy(string.find(canon.encode(status),'"server_endpoint"',1,true)~=nil,'in status.json')
  R.advance(10);m:pass();t.eq(fs.wg_calls,1,'second pass: same epoch, no wg')
  t.eq(status.response_metric,'icmp-1.1.1.1','the response metric is published')
end)

t.run()
