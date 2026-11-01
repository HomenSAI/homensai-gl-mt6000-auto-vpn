-- CPU cost of one idle Auto diagnostic (backend.diagnostic with the real platform.assess), measured with os.clock().
--   lua5.1 router/tests/lua/bench_diagnostic.lua [passes] [routes] [processes]
-- A fake GL-MT3000 (backend_fake.lua): a realistic fw3.state (lan/wan/guest/two VPN zones, ipsets), the four vendor
-- pins, native-audit-hashes.json, `ip -4 -j route show table all` with [routes] routes (local/broadcast/main and the
-- two VPN tables), `ip -4 -j rule show`, /proc with [processes] user processes plus kernel threads, /proc/locks.
-- Nothing changes between passes, as on an idle router. The fake costs no syscalls, so the numbers are the Lua
-- work only (the router adds the reads and the two `ip` processes); compare before/after on the same machine.
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..here..'/?.lua;'..package.path
package.preload['sys']=function() return {} end
local canon=require('canon')
canon.configure({runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp'})
local fake=require('backend_fake')
local backend_mod=require('backend')
local platform=require('platform')

local passes=tonumber(arg[1]) or 200
local nroutes=tonumber(arg[2]) or 400
local nproc=tonumber(arg[3]) or 80
local O,A=canon.object,canon.array
local NOW=1761830400

local function fw3_state()
  local out={'package fw3_state','','config defaults',"\toption input 'ACCEPT'","\toption output 'ACCEPT'","\toption forward 'REJECT'","\toption flow_offloading '0'",''}
  for _,z in ipairs({'lan','wan','guest','wgclient1','ovpnclient2'}) do
    out[#out+1]="config zone '"..z.."'"
    out[#out+1]="\toption name '"..z.."'"
    out[#out+1]="\toption input 'ACCEPT'"
    out[#out+1]="\toption output 'ACCEPT'"
    out[#out+1]="\toption forward '"..(z=='lan' and 'ACCEPT' or 'REJECT').."'"
    out[#out+1]="\tlist network '"..z.."'"
    out[#out+1]="\tlist device 'br-"..z.."' # runtime"
    out[#out+1]=''
  end
  for i=1,12 do
    out[#out+1]="config ipset 'set"..i.."'"
    out[#out+1]="\toption name 'gl_set_"..i.."'"
    out[#out+1]="\tlist match 'dest_ip'"
    out[#out+1]="\toption family 'ipv4'"
    out[#out+1]=''
  end
  return table.concat(out,'\n')
end

local function routes()
  local rows={
    O({dst='default',gateway='192.168.1.1',dev='eth0',protocol='static',flags=A({})}),
    O({dst='default',dev='wgclient1',table='1001',scope='link',flags=A({})}),
    O({dst='default',dev='ovpnclient2',table='1012',scope='link',flags=A({})})}
  local i=0
  while #rows<nroutes do
    i=i+1
    local t=({'local','main','1001','1012'})[i%4+1]
    rows[#rows+1]=O({type=t=='local' and (i%3==0 and 'broadcast' or 'local') or canon.null,dst=string.format('10.%d.%d.0/24',math.floor(i/250)%250,i%250),
      dev=({'br-lan','eth0','wgclient1','ovpnclient2'})[i%4+1],table=t,protocol='kernel',scope='link',prefsrc='192.168.8.1',flags=A({})})
    if rows[#rows].type==canon.null then rows[#rows].type=nil end
  end
  return canon.encode(A(rows))
end
local RULES=canon.encode(A({O({priority=0,src='all',table='local'}),O({priority=6000,src='all',fwmark='0x1000',fwmask='0xf000',table='1001'}),
  O({priority=6000,src='all',fwmark='0xb000',fwmask='0xf000',table='1012'}),O({priority=32766,src='all',table='main'}),O({priority=32767,src='all',table='default'})}))

local function policy_text()
  local function rule(name,idx,via,mark,extra)
    local r=O({['.name']=name,['.anonymous']=true,['.type']='rule',['.index']=idx,enabled='1',killswitch='1',via=via,mark=mark,tunnel_id=tostring(idx*1000),options_in_used='0'})
    for k,v in pairs(extra) do r[k]=v end
    return r
  end
  local sections=A({O({['.name']='global',['.anonymous']=false,['.type']='policy',enabled='1'}),O({['.name']='default',['.anonymous']=false,['.type']='default',enabled='0'}),
    rule('cfg0123ab',2,'wgclient1','0x1000',{via_type='wireguard',peer_id='2002'}),rule('cfg0456cd',3,'ovpnclient2','0xb000',{via_type='openvpn',group_id='40354',client_id='2020'}),
    O({['.name']='gl_process_vpn',['.anonymous']=false,['.type']='rule_process',enabled='1',from_type='process_gid',via='wgclient1',mark='0x1000',tunnel_id='10100'})})
  return canon.encode(O({sections=sections,settings=O({plan_source='wireguard:peer_2002',plan_target='openvpn:40354_2020',native_order_direction='first',
    terms_version=require('terms'),interval='10',plan_source_tunnel='wireguard:wgclient1',plan_target_tunnel='openvpn:ovpnclient2'}),
    firewall_defaults=A({}),hnat_enable='0',ipv6='0',lan='br-lan',firewall_include=O({path='/usr/bin/rtp2.sh',type='script',reload='0'})}))..'\n'
end
local INVENTORY=canon.encode(O({profiles=A({
  O({id='wireguard:peer_2002',section='peer_2002',protocol='wireguard',name='WG',interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',administrative_state='enabled'}),
  O({id='openvpn:40354_2020',section='40354_2020',protocol='openvpn',name='OV',interface='ovpnclient2',vendor_tunnel_id='openvpn:ovpnclient2',administrative_state='enabled'})}),
  servers=A({}),settings=O({history_days=5}),native_candidates=A({}),wan_interfaces=A({'wan'})}))

local function world()
  local files={['/etc/glversion']='4.11.0\n',['/var/run/fw3.state']=fw3_state(),['/proc/locks']='1: POSIX  ADVISORY  WRITE 1234 00:0f:4321 0 EOF\n',
    ['/tmp/sysinfo/board_name']='glinet,mt3000-snand\n'}
  local audit={}
  for path in pairs(platform.PINS) do files[path]=string.rep('#!/bin/sh\n# vendor '..path..'\n',400) end
  for _,path in ipairs({'/usr/bin/rtp2.sh','/usr/bin/setup_instance','/usr/bin/vendor_a','/usr/bin/vendor_b','/usr/bin/vendor_c','/usr/bin/vendor_d'}) do
    files[path]=string.rep('#!/bin/sh\n# '..path..'\n',300);audit[#audit+1]=string.format('  "%s": "%s"',path,canon.sha256(files[path]))
  end
  files['/usr/lib/homensai-vpn/native-audit-hashes.json']='{\n'..table.concat(audit,',\n')..'\n}\n'
  files['/sys/class/net/wgclient1/ifindex']='10\n';files['/sys/class/net/ovpnclient2/ifindex']='11\n'
  local pids={}
  for pid=1,nproc+40 do
    local name=tostring(pid);pids[#pids+1]=name
    local kthread=pid>nproc
    local comm=kthread and 'kworker/'..pid or ({'procd','ubusd','netifd','dnsmasq','odhcpd','uhttpd','nginx','lua','crond','dropbear'})[pid%10+1]
    local flags=kthread and '2129984' or '4194560'
    files['/proc/'..name..'/stat']=name..' ('..comm..') S 1 '..name..' '..name..' 0 -1 '..flags..' 120 0 0 0 5 3 0 0 20 0 1 0 '..(1000+pid)..' 1234567 300 4294967295 1 1 0 0 0 0 0 4096 0 0 0 0 17 0 0 0 0 0 0\n'
    files['/proc/'..name..'/cmdline']='/usr/sbin/'..comm..'\0-f\0/etc/config/'..comm..'\0'
    files['/proc/'..name..'/wchan']='do_epoll_wait'
  end
  local ok_status=O({profiles=A({}),samples=A({})})
  return {wall=NOW,clock=1000,runtime='/run/hv',files=files,
    dirs={['/var/run']={'fw3.state','dnsmasq'},['/proc']=pids},
    ubus={['system board']=O({board_name='glinet,mt3000-snand',model='GL.iNet GL-MT3000',kernel='5.4.211',release=O({target='mediatek/mt7981'})}),
          ['network.interface.wgclient1 status']=O({up=true,l3_device='wgclient1'}),['network.interface.ovpnclient2 status']=O({up=true,l3_device='ovpnclient2'})},
    commands={['nft --version']={rc=0,out='nftables\n'},['ip -4 -j route show table all']={rc=0,out=routes()},['ip -4 -j rule show']={rc=0,out=RULES},
      ['ip -4 -j route get 1.1.1.1 mark 4096']={rc=0,out='[{"dst":"1.1.1.1","dev":"wgclient1","table":"1001"}]'},
      ['ip -4 -j route get 8.8.8.8 mark 4096']={rc=0,out='[{"dst":"8.8.8.8","dev":"wgclient1","table":"1001"}]'},
      ['ip -4 -j route get 9.9.9.9 mark 4096']={rc=0,out='[{"dst":"9.9.9.9","dev":"wgclient1","table":"1001"}]'},
      ['ip -4 -j route get 1.1.1.1 mark 45056']={rc=0,out='[{"dst":"1.1.1.1","dev":"ovpnclient2","table":"1012"}]'},
      ['ip -4 -j route get 8.8.8.8 mark 45056']={rc=0,out='[{"dst":"8.8.8.8","dev":"ovpnclient2","table":"1012"}]'},
      ['ip -4 -j route get 9.9.9.9 mark 45056']={rc=0,out='[{"dst":"9.9.9.9","dev":"ovpnclient2","table":"1012"}]'}},
    scripts={['/usr/lib/homensai-vpn/native_policy.lua']=policy_text(),['/usr/lib/homensai-vpn/inventory.lua']=INVENTORY},chunks={},mtimes={},
    status=ok_status}
end

-- The monitor's freshness proof (diagnosis.resolve_pair over status.json) is replaced by a READY pair equal to the
-- live bindings: it is not part of this step, and without it the diagnostic stops before the route reads.
local diagnosis=require('diagnosis')
diagnosis.resolve_pair=function()
  local function row(id,protocol,interface,device,mark,table_,ifindex)
    return O({id=id,protocol=protocol,interface=interface,vendor_tunnel_id=protocol..':'..interface,device=device,mark=mark,table=table_,ifindex=ifindex})
  end
  return {source=row('wireguard:peer_2002','wireguard','wgclient1','wgclient1',4096,'1001',10),
    target=row('openvpn:40354_2020','openvpn','ovpnclient2','ovpnclient2',45056,'1012',11),coordination=O({state='READY',code='PAIR-READY'})}
end

local w=world()
local sys=fake.new(w)
local B=backend_mod.new(sys)
local env={run={wall=sys.wall,clock=sys.clock,lock=function(fn) return fn() end,fs={read=function(p) return w.files[p] end}},runtime='/run/hv',persist='/etc/hv',
  stop=function() return false end,sleep=function() end}
B.bind(env);env.backend=B
B.acceleration=function() return O({loaded=A({}),hnat_runtime='disabled'}) end
-- the clock advances like the router's 2 s pass, so time-bounded caches behave as there
local blockers=B.diagnostic()
local profile={}
local function timed(name,fn)
  local t0=os.clock();fn();profile[name]=(profile[name] or 0)+(os.clock()-t0)
end
local t0=os.clock()
for _=1,passes do
  w.wall=w.wall+2;w.clock=w.clock+2
  timed('diagnostic',function() blockers=B.diagnostic() end)
end
local total=os.clock()-t0
local parts={}
for _=1,passes do
  w.wall=w.wall+2;w.clock=w.clock+2
  local data=B.policy()
  timed('assess',function() platform.assess(sys,sys.ubus('system','board'),data) end)
  timed('workers',function() platform.workers(sys,sys.clock()+2) end)
  timed('route_json',function() canon.decode(w.commands['ip -4 -j route show table all'].out) end)
  timed('fw3_zones',function() platform.zones(w.files['/var/run/fw3.state']) end)
end
for k,v in pairs(profile) do parts[#parts+1]=string.format('%s=%.3f ms',k,v*1000/passes) end
table.sort(parts)
print(string.format('diagnostic: %.3f ms per idle pass (%d passes, %d routes = %d bytes, %d processes); blockers=%s',
  total*1000/passes,passes,nroutes,#w.commands['ip -4 -j route show table all'].out,nproc,table.concat(blockers,',')))
print('  parts (each alone, uncached reference for route_json/fw3_zones): '..table.concat(parts,'  '))
