-- TODO-PERF step 4 (diagnostic cache): a cached value never hides a change. platform.cached_file (fw3.state zones,
-- vendor pin hashes, the audit pin list) by the file fingerprint with the racy and age rules; the route/rule JSON
-- reused only for a byte-identical `ip` output; own writes drop the backend caches. The same decisions as Python
-- (native_platform.cached_file) are checked in tests/test_lua_backend.py (file_cache cases).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
package.preload['sys']=function() return {} end
local canon=require('canon')
local fake=require('backend_fake')
local backend_mod=require('backend')
local platform=require('platform')
local diagnosis=require('diagnosis')
local O,A=canon.object,canon.array
local NOW=1761830400

local function fw3(zones)
  local out={'package fw3_state','config defaults',"\toption input 'ACCEPT'"}
  for _,z in ipairs(zones) do out[#out+1]='config zone';out[#out+1]="\toption name '"..z.."'" end
  return table.concat(out,'\n')..'\n'
end
local ZONES={'lan','wan','wgclient1','ovpnclient2'}
local BOARD=O({board_name='glinet,mt3000-snand',model='GL.iNet GL-MT3000',kernel='5.4.211',release=O({target='mediatek/mt7981'})})
local DATA=O({firewall_include=O({path='/usr/bin/rtp2.sh',type='script',reload='0'}),
  settings=O({plan_source_tunnel='wireguard:wgclient1',plan_target_tunnel='openvpn:ovpnclient2'})})

local function platform_world()
  local files={['/var/run/fw3.state']=fw3(ZONES),['/proc/locks']=''}
  for path in pairs(platform.PINS) do files[path]='vendor '..path end
  return {wall=NOW,clock=1000,files=files,dirs={['/var/run']={},['/proc']={}},mtimes={},inodes={}}
end
-- the four vendor pins hash to the test contents (assess compares them with PINS)
local saved_pins=platform.PINS
local function with_pins(fn)
  local pins={}
  for path in pairs(saved_pins) do pins[path]=canon.sha256('vendor '..path) end
  platform.PINS=pins
  local ok,err=pcall(fn)
  platform.PINS=saved_pins
  if not ok then error(err,0) end
end
local function has(list,code) for _,x in ipairs(list) do if x==code then return true end end;return false end
local function pass(w,seconds) w.wall=w.wall+(seconds or 2);w.clock=w.clock+(seconds or 2) end

t.test('an unchanged old fw3.state is parsed once; the assessment stays the same',function()
  with_pins(function()
    local w=platform_world();local sys=fake.new(w)
    for _=1,5 do t.eq(platform.assess(sys,BOARD,DATA),{});pass(w) end
    t.eq(sys.calls['read:/var/run/fw3.state'],1,'one read for five passes')
    for path in pairs(platform.PINS) do t.eq(sys.calls['read:'..path],1,'pin hashed once: '..path) end
  end)
end)

t.test('a changed fw3.state between passes is always seen: size, mtime, inode, type',function()
  with_pins(function()
    local w=platform_world();local sys=fake.new(w)
    t.eq(platform.assess(sys,BOARD,DATA),{});pass(w)
    -- same size, newer mtime: the selected reserve zone is gone
    w.files['/var/run/fw3.state']=fw3({'lan','wan','wgclient1','ovpnclientX'});w.mtimes['/var/run/fw3.state']=50
    t.truthy(has(platform.assess(sys,BOARD,DATA),'FW3-SELECTED-ZONE-UNVERIFIED'),'mtime change seen');pass(w)
    -- back, but replaced by rename: a new inode with the same size and mtime
    w.files['/var/run/fw3.state']=fw3(ZONES);w.inodes['/var/run/fw3.state']=99
    t.eq(platform.assess(sys,BOARD,DATA),{},'inode change seen');pass(w)
    -- a symlink in its place
    w.links['/var/run/fw3.state']=true
    t.truthy(has(platform.assess(sys,BOARD,DATA),'FW3-RUNTIME-STATE-UNVERIFIED'),'symlink seen')
    w.links['/var/run/fw3.state']=nil;pass(w)
    -- removed
    w.files['/var/run/fw3.state']=nil
    t.truthy(has(platform.assess(sys,BOARD,DATA),'FW3-RUNTIME-STATE-UNVERIFIED'),'missing seen')
  end)
end)

t.test('racy: a file written within 2 s of its read is read again, so a same-second same-size rewrite is seen',function()
  with_pins(function()
    local w=platform_world();local sys=fake.new(w)
    w.mtimes['/var/run/fw3.state']=NOW  -- written in this very second
    t.eq(platform.assess(sys,BOARD,DATA),{})
    -- rewritten in the same second with the same size: the key (inode, size, mtime, ctime) is unchanged
    w.files['/var/run/fw3.state']=fw3({'lan','wan','wgclient1','ovpnclientX'})
    t.truthy(has(platform.assess(sys,BOARD,DATA),'FW3-SELECTED-ZONE-UNVERIFIED'),'the young entry was not trusted')
    t.eq(sys.calls['read:/var/run/fw3.state'],2)
    -- once the file is 2 s old the entry is trusted
    w.wall=NOW+2;platform.assess(sys,BOARD,DATA);platform.assess(sys,BOARD,DATA)
    t.eq(sys.calls['read:/var/run/fw3.state'],3)
  end)
end)

t.test('age: every derived value is recomputed at least every 30 s even with an unchanged key',function()
  local w=platform_world();local sys=fake.new(w)
  local n=0
  local function get() return platform.cached_file(sys,'x','/var/run/fw3.state',function() n=n+1;return n end) end
  t.eq(get(),1);w.clock=w.clock+29.9;t.eq(get(),1);w.clock=w.clock+0.1;t.eq(get(),2)
  w.clock=w.clock-100;t.eq(get(),3,'a clock that went back is no reuse')
end)

t.test('a failed compute leaves no entry; a missing file is never cached',function()
  local w=platform_world();local sys=fake.new(w)
  w.files['/var/run/fw3.state']='package fw3_state\nconfig zone\n'  -- invalid: no defaults, no name
  t.code('STATE-ZONE-NAME',platform.fw3_zones,sys)
  t.code('STATE-ZONE-NAME',platform.fw3_zones,sys)
  t.eq(sys.calls['read:/var/run/fw3.state'],2,'an error is read again')
  local n=0
  local function get() return platform.cached_file(sys,'gone','/nowhere',function() n=n+1;return n end) end
  t.eq(get(),1);t.eq(get(),2)
end)

t.test('a changed vendor pin is seen on the next pass; caches belong to one sys table',function()
  with_pins(function()
    local w=platform_world();local sys=fake.new(w)
    t.eq(platform.assess(sys,BOARD,DATA),{});pass(w)
    w.files['/etc/rc.common']='vendor /etc/rc.commoX';w.mtimes['/etc/rc.common']=77
    t.truthy(has(platform.assess(sys,BOARD,DATA),'VENDOR-CODE-CHANGED'))
    local other=fake.new(platform_world())
    t.eq(platform.assess(other,BOARD,DATA),{},'another router (fake) does not see the first one\'s cache')
  end)
end)

-- the backend: audit pin list, route and rule reads ------------------------------------------------------
local function backend_world()
  local w=platform_world()
  w.files['/etc/glversion']='4.11.0\n'
  w.files['/usr/bin/rtp2.sh']='rtp2';w.files['/usr/bin/setup_instance']='setup'
  w.files['/usr/lib/homensai-vpn/native-audit-hashes.json']='{\n  "/usr/bin/rtp2.sh": "'..canon.sha256('rtp2')..'",\n  "/usr/bin/setup_instance": "'..canon.sha256('setup')..'"\n}\n'
  w.files['/sys/class/net/wgclient1/ifindex']='10\n';w.files['/sys/class/net/ovpnclient2/ifindex']='11\n'
  w.ubus={['system board']=BOARD,['network.interface.wgclient1 status']=O({up=true,l3_device='wgclient1'}),
    ['network.interface.ovpnclient2 status']=O({up=true,l3_device='ovpnclient2'})}
  local routes=A({O({dst='default',dev='wgclient1',table='1001'}),O({dst='default',dev='ovpnclient2',table='1012'}),O({dst='192.168.8.0/24',dev='br-lan'})})
  local rules=A({O({priority=0,src='all',table='local'}),O({priority=6000,src='all',fwmark='0x1000',fwmask='0xf000',table='1001'}),
    O({priority=6000,src='all',fwmark='0xb000',fwmask='0xf000',table='1012'})})
  w.commands={['nft --version']={rc=0,out='nftables\n'},['ip -4 -j route show table all']={rc=0,out=canon.encode(routes)},
    ['ip -4 -j rule show']={rc=0,out=canon.encode(rules)}}
  for _,a in ipairs({'1.1.1.1','8.8.8.8','9.9.9.9'}) do
    w.commands['ip -4 -j route get '..a..' mark 4096']={rc=0,out='[{"dst":"'..a..'","dev":"wgclient1","table":"1001"}]'}
    w.commands['ip -4 -j route get '..a..' mark 45056']={rc=0,out='[{"dst":"'..a..'","dev":"ovpnclient2","table":"1012"}]'}
  end
  local sections=A({O({['.name']='global',['.anonymous']=false,['.type']='policy',enabled='1'}),O({['.name']='default',['.anonymous']=false,['.type']='default',enabled='0'}),
    O({['.name']='cfg0123ab',['.anonymous']=true,['.type']='rule',enabled='1',killswitch='1',via='wgclient1',mark='0x1000',tunnel_id='5841'}),
    O({['.name']='cfg0456cd',['.anonymous']=true,['.type']='rule',enabled='1',killswitch='1',via='ovpnclient2',mark='0xb000',tunnel_id='4192'})})
  w.scripts={['/usr/lib/homensai-vpn/native_policy.lua']=canon.encode(O({sections=sections,settings=O({plan_source='wireguard:peer_2002',
    plan_target='openvpn:40354_2020',native_order_direction='first',terms_version=require('terms'),interval='10',
    plan_source_tunnel='wireguard:wgclient1',plan_target_tunnel='openvpn:ovpnclient2'}),hnat_enable='0',ipv6='0',firewall_defaults=A({}),lan='br-lan',
    firewall_include=O({path='/usr/bin/rtp2.sh',type='script',reload='0'})}))..'\n',
    ['/usr/lib/homensai-vpn/inventory.lua']=canon.encode(O({profiles=A({
      O({id='wireguard:peer_2002',section='peer_2002',protocol='wireguard',interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1'}),
      O({id='openvpn:40354_2020',section='40354_2020',protocol='openvpn',interface='ovpnclient2',vendor_tunnel_id='openvpn:ovpnclient2'})}),
      servers=A({}),settings=O({})}))}
  w.chunks={}
  return w
end
local function measured(id,protocol,interface,mark,table_,ifindex)
  return O({id=id,protocol=protocol,interface=interface,vendor_tunnel_id=protocol..':'..interface,device=interface,mark=mark,table=table_,ifindex=ifindex})
end
local function with_backend(fn)
  local saved=diagnosis.resolve_pair
  diagnosis.resolve_pair=function()
    return {source=measured('wireguard:peer_2002','wireguard','wgclient1',4096,'1001',10),
      target=measured('openvpn:40354_2020','openvpn','ovpnclient2',45056,'1012',11),coordination=O({state='READY',code='PAIR-READY'})}
  end
  local ok,err=pcall(function()
    with_pins(function()
      local w=backend_world();local sys=fake.new(w)
      local B=backend_mod.new(sys)
      local env={run={wall=sys.wall,clock=sys.clock,lock=function(f) return f() end,fs={read=function(p) return w.files[p] end}},runtime='/run/hv',persist='/etc/hv',
        stop=function() return false end,sleep=function() end}
      B.bind(env);env.backend=B
      B.acceleration=function() return O({loaded=A({}),hnat_runtime='disabled'}) end
      fn(w,sys,B)
    end)
  end)
  diagnosis.resolve_pair=saved
  if not ok then error(err,0) end
end
-- counts canon.decode calls on texts that look like a route or rule dump
local function count_decodes(fn)
  local real=canon.decode
  local n=0
  canon.decode=function(text,...) if type(text)=='string' and string.find(text,'"priority"',1,true) or string.find(tostring(text),'"dst":"default"',1,true) then n=n+1 end;return real(text,...) end
  local ok,err=pcall(fn)
  canon.decode=real
  if not ok then error(err,0) end
  return n
end

t.test('idle diagnostics: route and rule tables are read live on every pass, decoded only when the text changed',function()
  with_backend(function(w,sys,B)
    local b,s=B.diagnostic();t.eq(b,{});t.truthy(s and s.vendor_identity)
    local reads=sys.calls['exec:ip'] or 0
    local n=count_decodes(function() for _=1,3 do pass(w);t.eq((B.diagnostic()),{}) end end)
    t.eq(n,0,'identical texts are not decoded again')
    t.eq((sys.calls['exec:ip'] or 0)-reads,6,'route and rule dumps still read on each of the 3 passes')
  end)
end)

t.test('a route that moved between passes is seen at once (no cached route answer)',function()
  with_backend(function(w,sys,B)
    t.eq((B.diagnostic()),{});pass(w)
    -- the reserve's default route moves to another table: its fwmark rule no longer reaches it
    w.commands['ip -4 -j route show table all'].out=canon.encode(A({O({dst='default',dev='wgclient1',table='1001'}),O({dst='default',dev='ovpnclient2',table='1013'})}))
    t.eq((B.diagnostic()),{'PROFILE-IDENTITY-CHANGED'})
  end)
end)

t.test('a rule that changed between passes is seen at once',function()
  with_backend(function(w,sys,B)
    t.eq((B.diagnostic()),{});pass(w)
    w.commands['ip -4 -j rule show'].out=canon.encode(A({O({priority=6000,src='all',fwmark='0x1000',fwmask='0xf000',table='1001'}),
      O({priority=6000,src='all',fwmark='0xc000',fwmask='0xf000',table='1012'})}))
    for _,a in ipairs({'1.1.1.1','8.8.8.8','9.9.9.9'}) do
      w.commands['ip -4 -j route get '..a..' mark 49152']={rc=0,out='[{"dst":"'..a..'","dev":"ovpnclient2","table":"1012"}]'}
    end
    t.eq((B.diagnostic()),{'PROFILE-IDENTITY-CHANGED'})
  end)
end)

t.test('a changed audit pin list or pinned program is seen on the next pass',function()
  with_backend(function(w,sys,B)
    t.eq((B.diagnostic()),{});pass(w)
    w.files['/usr/bin/setup_instance']='setuX';w.mtimes['/usr/bin/setup_instance']=60
    t.eq((B.diagnostic()),{'VENDOR-CODE-CHANGED'});pass(w)
    w.files['/usr/lib/homensai-vpn/native-audit-hashes.json']='{\n  "/usr/bin/rtp2.sh": "'..canon.sha256('rtp2')..'",\n  "/usr/bin/setup_instance": "'..canon.sha256('setuX')..'"\n}\n'
    w.mtimes['/usr/lib/homensai-vpn/native-audit-hashes.json']=61
    t.eq((B.diagnostic()),{},'the new pin list is used')
    w.files['/usr/lib/homensai-vpn/native-audit-hashes.json']='not json'
    t.eq((B.diagnostic()),{'VENDOR-CODE-UNVERIFIED'})
  end)
end)

t.test('an own write drops the backend caches: the next pass decodes the tables again',function()
  with_backend(function(w,sys,B)
    B.diagnostic();pass(w)
    B.run_write(nil,'uci',function() end)
    local n=count_decodes(function() t.eq((B.diagnostic()),{}) end)
    t.eq(n,2,'route and rule texts decoded after the write')
  end)
end)

t.run()
