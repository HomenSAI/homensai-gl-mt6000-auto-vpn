-- backend.lua with a fake router (backend_fake.lua): caches answer only for unchanged reads, writes go through
-- write_command with the facts recovery needs, the guard, the probe bridge and the negative health memo,
-- recovery.record_step, the env wiring. The same-as-Python checks are in tests/test_lua_backend.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
package.preload['sys']=function() return {} end
local canon=require('canon')
local fake=require('backend_fake')
local backend_mod=require('backend')
local identity=require('identity')
local platform=require('platform')
local recovery=require('recovery')
local NOW=1761830400

local function O(t_) return canon.object(t_) end
local function A(t_) return canon.array(t_) end
local function sections(reserve_first)
  local wg=O({['.name']='cfg0123ab',['.anonymous']=true,['.type']='rule',['.index']=2,enabled='1',killswitch='1',via='wgclient1',via_type='wireguard',
    peer_id='2002',mark='0x1000',tunnel_id='5841',options_in_used='0'})
  local ovpn=O({['.name']='cfg0456cd',['.anonymous']=true,['.type']='rule',['.index']=3,enabled='1',killswitch='1',via='ovpnclient2',via_type='openvpn',
    group_id='40354',client_id='2020',mark='0xb000',tunnel_id='4192',options_in_used='0'})
  local rows={O({['.name']='global',['.anonymous']=false,['.type']='policy',enabled='1'}),O({['.name']='default',['.anonymous']=false,['.type']='default',enabled='0'})}
  if reserve_first then rows[3]=ovpn;rows[4]=wg else rows[3]=wg;rows[4]=ovpn end
  rows[5]=O({['.name']='gl_process_vpn',['.anonymous']=false,['.type']='rule_process',enabled='1',from_type='process_gid',via=reserve_first and 'ovpnclient2' or 'wgclient1',
    mark=reserve_first and '0xb000' or '0x1000',tunnel_id='10100'})
  return A(rows)
end
local function policy_text(reserve_first)
  return canon.encode(O({sections=sections(reserve_first),settings=O({plan_source='wireguard:peer_2002',plan_target='openvpn:40354_2020',
    native_order_direction='first',terms_version=require('terms'),interval='10'}),firewall_defaults=A({}),hnat_enable='0',ipv6='0',lan='br-lan',
    firewall_include=O({path='/usr/bin/rtp2.sh',type='script',reload='0'})}))..'\n'
end
local INVENTORY=canon.encode(O({profiles=A({
  O({id='wireguard:peer_2002',section='peer_2002',protocol='wireguard',name='WG',interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',administrative_state='enabled'}),
  O({id='openvpn:40354_2020',section='40354_2020',protocol='openvpn',name='OV',interface='ovpnclient2',vendor_tunnel_id='openvpn:ovpnclient2',administrative_state='enabled'})}),
  servers=A({}),settings=O({history_days=5}),native_candidates=O({}),wan_interfaces=A({'wan'})}))

local function world()
  local w={wall=NOW,clock=1000,runtime='/run/hv',files={['/etc/glversion']='4.11.0\n'},dirs={['/var/run']={},['/proc']={}},
    ubus={['system board']=O({board_name='glinet,gl-mt6000'}),['network.interface.wgclient1 status']=O({up=true,l3_device='wgclient1'}),
          ['network.interface.ovpnclient2 status']=O({up=true,l3_device='ovpnclient2'})},
    commands={['nft --version']={rc=0,out='nftables\n'}},scripts={['/usr/lib/homensai-vpn/native_policy.lua']=policy_text(false),
      ['/usr/lib/homensai-vpn/inventory.lua']=INVENTORY},chunks={},mtimes={}}
  return w
end
local function backend(w)
  local sys=fake.new(w)
  local B=backend_mod.new(sys)
  local locks=0
  local env={run={wall=sys.wall,clock=sys.clock,lock=function(fn) locks=locks+1;return fn() end,require_revision=function(r) if r~=string.rep('7',32) then error(setmetatable({code='CLIENT-STOP'},require('auto_control').Refused),0) end end,
    fenced=function(r,fn) return fn() end,fs={read=function(p) return w.files[p] end}},runtime='/run/hv',persist='/etc/hv',stop=function() return false end,sleep=function() end}
  B.bind(env);env.backend=B
  B.acceleration=function() return O({loaded=A({}),hnat_runtime='disabled'}) end
  return B,sys,env
end

t.test('policy/inventory/order are read once while their UCI files are unchanged; a delta write is seen at once',function()
  local w=world();local B,sys=backend(w)
  local o1,h1=B.order();local o2,h2=B.order();B.policy();B.inventory();B.inventory()
  t.eq(sys.calls['script:/usr/lib/homensai-vpn/native_policy.lua'],1,'policy script once')
  t.eq(sys.calls['script:/usr/lib/homensai-vpn/inventory.lua'],1,'inventory script once')
  t.eq(h1,h2);t.eq(#o1,5)
  -- an uncommitted `uci reorder` writes /tmp/.uci/route_policy: the next read must see it
  w.files['/tmp/.uci/route_policy']="route_policy.cfg0456cd='rule'\n";w.scripts['/usr/lib/homensai-vpn/native_policy.lua']=policy_text(true)
  local o3,h3=B.order()
  t.eq(sys.calls['script:/usr/lib/homensai-vpn/native_policy.lua'],2,'re-read after the delta changed')
  t.eq(o3[3],o1[4],'moved');t.truthy(h3~=h1,'the process binding follows the first rule: another hash')
end)

t.test('policy() hands out copies: a caller cannot change the cached data',function()
  local B=backend(world())
  local d=B.policy();d.sections[1].enabled='0';d.settings.terms_version='x'
  local again=B.policy()
  t.eq(again.sections[1].enabled,'1');t.eq(again.settings.terms_version,require('terms'))
  t.eq(B.history_days(),5)
end)

t.test('the idle tick costs reads, not processes: the second diagnostic starts no script, no hash and no route lookup',function()
  local w=world()
  w.ubus['system board']=O({board_name='glinet,gl-mt6000'})
  local B,sys=backend(w)
  B.diagnostic()
  local before={}
  for k,v in pairs(sys.calls) do before[k]=v end
  B.diagnostic();B.diagnostic()
  local function grew(name) return (sys.calls[name] or 0)-(before[name] or 0) end
  t.eq(grew('script:/usr/lib/homensai-vpn/native_policy.lua'),0)
  t.eq(grew('script:/usr/lib/homensai-vpn/inventory.lua'),0)
  t.eq(grew('ubus:system'),0,'board read once per process')
  t.eq(grew('exec:nft'),0,'nft --version once per process')
end)

t.test('uci reorder: one move per changed index, then one commit; write_command gets the facts record_step checks',function()
  local w=world();local B,sys=backend(w)
  local reordered=false
  w.handler=function(argv)
    if argv[1]=='uci' and argv[2]=='reorder' then
      reordered=true;w.scripts['/usr/lib/homensai-vpn/native_policy.lua']=policy_text(true)
      w.files['/tmp/.uci/route_policy']='x';return 0,''
    end
    if argv[1]=='uci' and argv[2]=='commit' then w.files['/tmp/.uci/route_policy']=nil;return 0,'' end
  end
  -- the process binding is part of the identity; the swap is checked with it
  B.use_process_bindings(O({wgclient1=4096,ovpnclient2=45056}))
  local order=B.order()
  local target=A({order[1],order[2],order[4],order[3],order[5]})
  local writes={}
  B.reorder(target,nil,function(kind,fn,detail) writes[#writes+1]={kind,detail};return fn() end)
  -- the derived gl_process_vpn fields follow the first rule and are outside the identity: same hash, new order
  t.eq(#writes,2)
  t.eq(writes[1][1],'uci');t.eq(writes[1][2].op,'reorder');t.eq(writes[1][2].section,'cfg0456cd');t.eq(writes[1][2].index,2)
  t.eq(writes[2][2].op,'commit')
  t.truthy(reordered)
  local live=B.order()
  t.eq(live[3],order[4])
end)

t.test('reorder of an unknown identity or an unsafe section name is refused before any write',function()
  local B,sys=backend(world())
  local order=B.order()
  local e=t.raises(B.reorder,A({order[1],order[2],order[3],order[4],'other'}))
  t.eq(e.code,'POLICY-IDENTITY-CHANGED')
  t.eq(sys.calls['exec:uci'],nil)
end)

t.test('guard: VPN-only rules from validated devices, a timed full block with its own release generation',function()
  local w=world();local B,sys=backend(w)
  local installed=false
  w.handler=function(argv)
    if argv[1]~='nft' then return nil end
    if argv[2]=='list' then return installed and 0 or 1,installed and 'comment "homensai-owned-guard"' or '' end
    if argv[2]=='-c' then return 0,'' end
    if argv[2]=='-f' then installed=true;return 0,'' end
    if argv[2]=='delete' then installed=false;return 0,'' end
  end
  B.guard(B.devices())
  t.truthy(installed);t.eq(sys.calls.guard_release,nil,'no release job for the VPN-only guard')
  B.guard()
  t.truthy(w.released and #w.released==8,'release armed for the generation')
  B.unguard();t.truthy(not installed)
  t.eq(t.raises(B.guard,{'br-lan; flush ruleset'}).code,'UNSAFE-GUARD-DEVICE')
  w.handler=function(argv) if argv[1]=='nft' and argv[2]=='list' then return 0,'table inet homensai_vpn_guard { }' end end
  t.eq(t.raises(B.guard_exists).code,'FOREIGN-GUARD-TABLE')
end)

t.test('guard with a control revision is dispatched under the lock and fails closed on Stop',function()
  local w=world();local B,sys,env=backend(w)
  w.handler=function(argv) if argv[1]=='nft' then return argv[2]=='list' and 1 or 0,'' end end
  local e=t.raises(B.guard,{'wgclient1'},string.rep('8',32))
  t.eq(e.code,'CLIENT-STOP')
end)

t.test('probe bridge: one Python process per health check; a negative answer is reused for 10 s, a positive never',function()
  local w=world();local B,sys=backend(w)
  local healthy=false
  w.handler=function(argv)
    if argv[1]=='python3' then
      return 0,canon.encode(O({id='x',code=healthy and canon.null or 'VPN-003',dns_ok=healthy,https_success=healthy and 2 or 0}))..'\n'
    end
  end
  t.eq(B.health('wireguard:peer_2002'),false)
  t.eq(B.health('wireguard:peer_2002'),false)
  t.eq(sys.calls['exec:python3'],1,'memo within 10 s')
  healthy=true;w.clock=w.clock+11
  t.eq(B.health('wireguard:peer_2002'),true)
  t.eq(B.health('wireguard:peer_2002'),true)
  t.eq(sys.calls['exec:python3'],3,'a positive answer is never reused')
  -- the steady manual hold may reuse a positive answer for `reuse` seconds; a negative one ends the reuse
  t.eq(B.health('wireguard:peer_2002',30),true)
  t.eq(sys.calls['exec:python3'],3,'reused by the hold')
  w.clock=w.clock+31
  t.eq(B.health('wireguard:peer_2002',30),true)
  t.eq(sys.calls['exec:python3'],4,'older than the reuse window: live again')
  healthy=false;w.clock=w.clock+31
  t.eq(B.health('wireguard:peer_2002',30),false)
  healthy=true;w.clock=w.clock+11
  t.eq(B.health('wireguard:peer_2002',30),true)
  t.eq(sys.calls['exec:python3'],6,'after a failure the next answer is live')
  t.eq(B.health('unknown:x'),false)
  w.handler=function(argv) if argv[1]=='python3' then return 0,'{"code":"EXIT-TRACE-FAILED"}\n' end end
  t.eq(t.raises(B.trace,O({id='wireguard:peer_2002'})).code,'EXIT-TRACE-FAILED')
  w.handler=function(argv) if argv[1]=='python3' then return 0,'{"exit":"198.51.100.7"}\n' end end
  t.eq(B.trace(O({id='wireguard:peer_2002'})),'198.51.100.7')
end)

t.test('clear_native_options never overwrites pending foreign changes',function()
  local w=world();local B,sys=backend(w)
  w.commands['uci -q changes homensai_vpn']={rc=0,out="homensai_vpn.main.x='1'\n"}
  t.eq(B.clear_native_options(),false)
  w.commands['uci -q changes homensai_vpn']={rc=0,out=''}
  w.commands['uci -q batch']={rc=0,out=''}
  t.eq(B.clear_native_options(),true)
end)

t.test('apply on a non-MT3000 board: process binding CAS, then rtp2.sh dispatched through write_command',function()
  local w=world()
  w.scripts['/usr/lib/homensai-vpn/native_policy.lua']=policy_text(false)
  local B,sys=backend(w)
  B.use_process_bindings(O({wgclient1=4096,ovpnclient2=45056}))
  w.commands['/usr/bin/rtp2.sh not_reload_network']={rc=0,out=''}
  local kinds={}
  B.apply(function(kind,fn,detail) kinds[#kinds+1]=kind;local r=fn();if type(r)=='function' then r=r() end;return r end)
  t.eq(kinds,{'rtp'},'already applied: no CAS write')
  t.eq(sys.spawned[1],'/usr/bin/rtp2.sh not_reload_network')
  w.commands['/usr/bin/rtp2.sh not_reload_network']={rc=1,out=''}
  t.eq(t.raises(B.apply,function(kind,fn) local r=fn();if type(r)=='function' then r=r() end;return r end).code,'COMMAND-FAILED')
end)

t.test('fast_switch option and instant_request follow the Python readers',function()
  local w=world();local B=backend(w)
  t.eq(B.fast_switch_enabled(),false,'no config file')
  w.files['/etc/config/homensai_vpn']="config main 'main'\n\toption fast_switch '1'\n"
  t.eq(B.fast_switch_enabled(),true)
  w.files['/etc/config/homensai_vpn']="config main 'main'\n  option fast_switch 0\n"
  t.eq(B.fast_switch_enabled(),false)
  local order=B.order()
  local names,tunnels=B.instant_request(nil,A({order[1],order[2],order[4],order[3],order[5]}))
  t.eq(tunnels,{'4192','5841'});t.eq(names[order[3]],'cfg0123ab')
end)

t.test('recovery.record_step persists the exact pending move before it is dispatched',function()
  local w=world();local B,sys,env=backend(w)
  local journal_store=nil
  package.loaded.transaction=nil
  local T=require('transaction')
  local bindings=O({wgclient1=4096,ovpnclient2=45056})
  B.use_process_bindings(bindings)
  local order=B.order()
  local before=A({order[1],order[2],order[4],order[3],order[5]})
  local j=O({phase='RESTORING',before=order,after=before,restore_before_order=before,restore_target_order=order,restore_before_verified=true,
    restore_kernel_fingerprint=string.rep('f',64),hash=select(2,B.order()),process_bindings=bindings})
  local saved_read,saved_write=T.journal_read,T.journal_write
  T.journal_read=function() return canon.decode(canon.encode(journal_store or j)) end
  T.journal_write=function(_,v) journal_store=canon.decode(canon.encode(v)) end
  -- the live UCI order is still `after`
  w.scripts['/usr/lib/homensai-vpn/native_policy.lua']=policy_text(true);B.invalidate()
  local ok,err=pcall(recovery.record_step,env,j,'uci',{op='reorder',section='cfg0123ab',index=2})
  T.journal_read,T.journal_write=saved_read,saved_write
  t.truthy(ok,tostring(err and err.code))
  t.eq(journal_store.restore_order_step.kind,'reorder');t.eq(journal_store.restore_order_step.index,2)
  t.eq(journal_store.restore_order_step.section,order[3])
  -- a different command line than the recorded plan is refused
  T.journal_read=function() return canon.decode(canon.encode(journal_store)) end
  T.journal_write=function(_,v) journal_store=canon.decode(canon.encode(v)) end
  local j2=canon.decode(canon.encode(journal_store))
  local ok2,err2=pcall(recovery.record_step,env,j2,'uci',{op='reorder',section='cfg0456cd',index=2})
  T.journal_read,T.journal_write=saved_read,saved_write
  t.truthy(not ok2 and err2.code=='POLICY-IDENTITY-CHANGED')
  -- other kinds are not recorded
  t.eq(recovery.record_step(env,j,'kernel',{op='kernel'}),nil)
end)

t.test('bind() wires env.net and the deps transaction/pair/rollback call',function()
  local B,sys,env=backend(world())
  for _,name in ipairs({'resolve_pair','diagnose','profile_identity','rtp_boot','rollback_recovery','activation_finalize','record_switch_time','manual_control','testing_profile','from_kernel'}) do
    t.truthy(env.deps[name]~=nil,name)
  end
  for _,name in ipairs({'vendor_rebuild_applies','rebuild','vendor_settled','order_allowed','promote_forward','authorize','record_step','settled'}) do
    t.truthy(type(env.deps.rollback_recovery[name])=='function',name)
  end
  for _,name in ipairs({'network','identity','configs','changed','set_disabled','client_down','ifup','ifdown','quiet','interface_exists','static_firewall_digest','firewall_bytes'}) do
    t.truthy(type(env.net[name])=='function',name)
  end
  t.eq(env.deps.testing_profile('x'),false)
end)

t.test('net.configs hashes a config file once per change',function()
  local w=world();local B,sys,env=backend(w)
  for _,name in ipairs(require('net').CONFIGS) do w.files['/etc/config/'..name]="config x '"..name.."'\n" end
  local first=env.net.configs(identity.LEGACY)
  local reads=sys.calls['read:/etc/config/firewall']
  env.net.configs(identity.LEGACY)
  t.eq(sys.calls['read:/etc/config/firewall'],reads,'unchanged: not read again')
  w.files['/etc/config/firewall']="config x 'firewall2'\n"
  local second=env.net.configs(identity.LEGACY)
  t.truthy(second.firewall~=first.firewall and second.dhcp==first.dhcp)
end)

t.test('platform workers: kernel threads and zombies are skipped, a worker process is busy, a vanished pid is not an error',function()
  local w=world()
  w.dirs['/proc']={'1','2','3','4','self'}
  w.files['/proc/locks']=''
  w.files['/proc/1/stat']='1 (procd) S 0 1 1 0 -1 4194560 1 2 3 4 5 6 7 8 20 0 1 0 15 0 0'
  w.files['/proc/1/cmdline']='/sbin/procd\0';w.files['/proc/1/wchan']='0'
  w.files['/proc/2/stat']='2 (kthreadd) S 0 0 0 0 -1 2129984 0 0 0 0 0 0 0 0 20 0 1 0 15 0 0'
  w.files['/proc/3/stat']='3 (sh) S 1 3 3 0 -1 4194304 1 2 3 4 5 6 7 8 20 0 1 0 99 0 0'
  w.files['/proc/3/cmdline']='/bin/sh\0/usr/bin/rtp2.sh\0not_reload_network\0';w.files['/proc/3/wchan']='do_wait'
  local sys=fake.new(w)
  local row=platform.workers(sys)
  t.eq(row.busy,1);t.eq(row.verified,true)
  w.files['/proc/3/cmdline']='/bin/sh\0'
  t.eq(platform.workers(sys).busy,0)
  w.files['/proc/locks']='1: FLOCK  ADVISORY  WRITE 1234 00:0e:5678 0 EOF\n'
  w.files['/tmp/run/fw3.lock']='';w.devs={['/tmp/run/fw3.lock']=14};w.inodes={['/tmp/run/fw3.lock']=5678}
  t.eq(platform.workers(sys).busy,1,'a held fw3 lock')
end)

t.run()
