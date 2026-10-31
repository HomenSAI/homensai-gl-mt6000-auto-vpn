"""Lua Auto backend (plan item 1, lua/backend.lua and the modules it uses) against native_switch.Linux.

One Lua process (tests/lua/backend_differential.lua) evaluates every case; Python evaluates the same inputs with
the real modules: section_id/policy_order/policy_hash, choose, failure_diagnosis.resolve_pair/diagnose/
scoped_samples, kernel_policy.attest/missing_only/static_bindings/unrouted, the kernel_fingerprint digest,
pair_auto.normalized_network/config_digest/static_firewall_digest, recovery_settings.fingerprint,
rollback_recovery.order_steps/validate_step/order_allowed/forward_proof/restore_origin, channel_path.from_kernel,
mt3000_manual_platform._zones, the hook-state readers, process_policy, pair_interfaces.roles,
manual_control.valid_record - and whole Linux methods on one fake router: diagnostic() (blockers, selection,
vendor_identity, settings_hash, coordination), kernel_fingerprint(), attest_policy(), order(), candidates(),
the instant-switch request and the guard nft script.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
sys.path.insert(0,str(HERE))
import agent
import native_switch as n
import kernel_policy as kp
import failure_diagnosis as fd
import pair_auto
import recovery_settings
import rollback_recovery as rr
import channel_path
import mt3000_manual_platform as mt
import process_policy
import pair_interfaces
import manual_control
from vendor_fixture import stamp, attach
from test_kernel_policy import fixture as kernel_fixture, network_fixture

LUA=shutil.which('lua5.1')
DRIVER=HERE/'lua'/'backend_differential.lua'
NOW=1761830400.25
LOOSE={'zones','static_bindings','attest','missing_only','order_steps','validate_step','restore_origin','order_allowed'}


def norm(value):
    return json.loads(json.dumps(value,sort_keys=True))


def outcome(fn,*args):
    try:result=fn(*args)
    except n.Refused as error:return {'refused':str(error)}
    except ValueError as error:return {'value_error':str(error)}
    except Exception as error:return {'error':type(error).__name__}
    return {'ok':norm(result)}


def same(kind,python,lua):
    if 'error' in python or 'error' in lua:return set(python)==set(lua)
    if kind in LOOSE and ('value_error' in python or 'value_error' in lua):return set(python)==set(lua)
    return python==lua


def run_lua(cases):
    with tempfile.TemporaryDirectory() as directory:
        source=Path(directory)/'cases.json';target=Path(directory)/'results.json'
        source.write_text(json.dumps([{'kind':k,'input':i} for k,i,_ in cases]),encoding='ascii')
        result=subprocess.run([LUA,str(DRIVER),str(source),str(target)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600,
                              env=dict(os.environ,HOMENSAI_TEST_RUNTIME=directory))
        if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
        return json.loads(target.read_text(encoding='utf8'))


# --- fixtures ----------------------------------------------------------------------------------------------
def stock_sections(process_via='wgclient1',reserve_first=False):
    wg={'.name':'cfg0123ab','.anonymous':True,'.type':'rule','.index':2,'enabled':'1','killswitch':'1','via':'wgclient1','via_type':'wireguard',
        'peer_id':'2002','mark':'0x1000','tunnel_id':'5841','options_in_used':'0','name':'WG rule'}
    ovpn={'.name':'cfg0456cd','.anonymous':True,'.type':'rule','.index':3,'enabled':'1','killswitch':'1','via':'ovpnclient2','via_type':'openvpn',
          'group_id':'40354','client_id':'2020','mark':'0xb000','tunnel_id':'4192','options_in_used':'0'}
    process={'.name':'gl_process_vpn','.anonymous':False,'.type':'rule_process','.index':5,'enabled':'1','from_type':'process_gid',
             'via':process_via,'mark':'0x1000' if process_via=='wgclient1' else '0xb000','tunnel_id':'10100'}
    base=[{'.name':'global','.anonymous':False,'.type':'policy','.index':0,'enabled':'1'},
          {'.name':'default','.anonymous':False,'.type':'default','.index':1,'enabled':'0'}]
    rules=[ovpn,wg] if reserve_first else [wg,ovpn]
    return base+rules+[process]


BINDINGS={'wgclient1':4096,'ovpnclient2':45056}


def profiles(now=NOW):
    return [stamp({'id':'wireguard:peer_2002','interface':'wgclient1','section':'peer_2002'},now),
            stamp({'id':'openvpn:40354_2020','interface':'ovpnclient2','section':'40354_2020'},now)]


def policy_data(sections=None,**settings):
    data={'sections':sections if sections is not None else stock_sections(),
          'settings':dict({'plan_source':'wireguard:peer_2002','plan_target':'openvpn:40354_2020','native_order_direction':'first',
                           'terms_version':'1','interval':'10'},**settings),
          'firewall_defaults':[{'.name':'cfg01','.type':'defaults','.anonymous':True,'flow_offloading':'0'}],
          'firewall_include':{'path':'/usr/bin/rtp2.sh','type':'script','reload':'0'},'hnat_enable':'0','ipv6':'0','lan':'br-lan'}
    return data


def inventory_rows():
    rows=[]
    for p in profiles():
        rows.append({'id':p['id'],'section':p['section'],'protocol':p['protocol'],'name':p['id'],'group_id':'40354' if p['protocol']=='openvpn' else '',
                     'profile_id':'2020' if p['protocol']=='openvpn' else '2002','vendor_profile_group_id':None,
                     'vendor_tunnel_id':p['vendor_tunnel_id'],'interface':p['interface'],'administrative_state':'enabled'})
    return {'profiles':rows,'servers':[{'id':'s1','profile':'openvpn:40354_2020','name':'','channel':'nl','priority':100,'enabled':True}],
            'settings':{'history_days':7},'native_candidates':[],'wan_interfaces':['wan']}


def status_json(now=NOW,**changes):
    status={'profiles':profiles(now)}
    for row,(device,mark,table,ifindex) in zip(status['profiles'],(('wgclient1',4096,'1001',10),('ovpnclient2',45056,'1012',11))):
        row.update(device=device,mark=mark,table=table,ifindex=ifindex)
    attach(status,now)
    status.update(changes)
    return status


def ubus_iface(up=True,device=None):
    return {'up':up,'l3_device':device,'pending':False,'available':True} if up else {'up':False,'pending':False,'available':True}


def base_world(**over):
    world={'wall':NOW,'clock':1000,'runtime':'/run/hv','assess':[],
           'acceleration':{'loaded':[],'hnat_runtime':'disabled','hnat_state_text':'disabled','hook_log':[],'debugfs_mounted':False,'hook_exists':False},
           'policy':policy_data(),'inventory':inventory_rows(),'status':status_json(),
           'board':{'board_name':'glinet,mt3000-snand','model':'GL.iNet GL-MT3000','kernel':'5.4.211','release':{'target':'mediatek/mt7981'}},
           'glversion':'4.11.0\n',
           'ifaces':{'wgclient1':ubus_iface(True,'wgclient1'),'ovpnclient2':ubus_iface(True,'ovpnclient2')},
           'routes':[{'dst':'default','dev':'wgclient1','table':'1001'},{'dst':'default','dev':'ovpnclient2','table':'1012'},
                     {'dst':'192.168.8.0/24','dev':'br-lan','table':'main'}],
           'rules':[{'priority':0,'src':'all','table':'local'},{'priority':6000,'src':'all','fwmark':'0x1000','fwmask':'0xf000','table':'1001'},
                    {'priority':6000,'src':'all','fwmark':'0xb000','fwmask':'0xf000','table':'1012'},{'priority':32766,'src':'all','table':'main'}],
           'ifindex':{'wgclient1':10,'ovpnclient2':11},
           'vendor':{'/usr/bin/rtp2.sh':b'#!/bin/sh\n# rtp2\n','/usr/bin/setup_instance':b'#!/bin/sh\n# setup\n'},
           'audit_extra':{},'mangle':None,'network':None}
    world.update(over)
    return world


def route_get(world,address,mark):
    for rule in world['rules']:
        if rule.get('fwmark') and int(str(rule['fwmark']),0)==mark:
            dev=next((r['dev'] for r in world['routes'] if str(r.get('table','main'))==str(rule['table']) and r.get('dst')=='default'),None)
            if world.get('route_get_override') and address in world['route_get_override']:return world['route_get_override'][address]
            return [{'dst':address,'dev':dev,'table':str(rule['table'])}]
    return [{'dst':address,'dev':'eth0','table':'main'}]


def lua_world(world):
    """The same router as the Python patches, for tests/lua/backend_fake.lua."""
    audit={name:hashlib.sha256(data).hexdigest() for name,data in world['vendor'].items()}
    audit.update(world['audit_extra'])
    files={'/etc/glversion':world['glversion'],'/run/hv/status.json':json.dumps(world['status']),
           '/usr/lib/homensai-vpn/native-audit-hashes.json':json.dumps(audit,indent=2)}
    for dev,index in world['ifindex'].items():files['/sys/class/net/'+dev+'/ifindex']=str(index)+'\n'
    hexfiles={name:data.hex() for name,data in world['vendor'].items()}
    commands={'nft --version':{'rc':0,'out':'nftables v1.0.2\n'},
              'ip -4 -j route show table all':{'out':json.dumps(world['routes'])},
              'ip -4 -j rule show':{'out':json.dumps(world['rules'])}}
    for address in ('1.1.1.1','8.8.8.8','9.9.9.9'):
        for rule in world['rules']:
            if rule.get('fwmark'):
                mark=int(str(rule['fwmark']),0)
                commands['ip -4 -j route get %s mark %d'%(address,mark)]={'out':json.dumps(route_get(world,address,mark))}
    if world['mangle'] is not None:commands['iptables-save -t mangle']={'out':world['mangle']}
    ubus={'system board':world['board']}
    for name,value in world['ifaces'].items():ubus['network.interface.'+name+' status']=value
    chunks={}
    if world['network'] is not None:chunks['pair_network_read']=json.dumps(world['network'])+'\n'
    return {'wall':world['wall'],'clock':world['clock'],'runtime':'/run/hv','files':files,'hexfiles':hexfiles,'commands':commands,'ubus':ubus,
            'scripts':{'/usr/lib/homensai-vpn/native_policy.lua':json.dumps(world['policy'])+'\n',
                       '/usr/lib/homensai-vpn/inventory.lua':json.dumps(world['inventory'])+'\n'},
            'chunks':chunks,'dirs':{'/var/run':[],'/proc':[]},'assess':world['assess'],'acceleration':world['acceleration']}


class PythonRouter:
    """Patches native_switch/agent I/O so that Linux() reads the same router as the Lua fake."""
    def __init__(self,world):self.world=world

    def __enter__(self):
        world=self.world;self.stack=ExitStack();stack=self.stack
        self.root=Path(stack.enter_context(tempfile.TemporaryDirectory()))
        root=self.root
        (root/'run').mkdir();(root/'run/status.json').write_text(json.dumps(world['status']))
        audit={name:hashlib.sha256(data).hexdigest() for name,data in world['vendor'].items()};audit.update(world['audit_extra'])
        (root/'lib').mkdir();(root/'lib/native-audit-hashes.json').write_text(json.dumps(audit,indent=2))
        (root/'etc').mkdir();(root/'etc/glversion').write_text(world['glversion'])
        for name,data in world['vendor'].items():
            p=root/name.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        (root/'var/run').mkdir(parents=True)
        for dev,index in world['ifindex'].items():
            p=root/'sys/class/net'/dev;p.mkdir(parents=True);(p/'ifindex').write_text(str(index)+'\n')
        real=Path
        module=real(n.__file__)
        class Rooted(type(real())):
            def __new__(cls,*parts):
                p=real(*parts)
                if p==module:return real(root,'lib',module.name)
                if p.is_absolute():return real(root,*p.parts[1:])
                return p
        def command(args,timeout=5):
            if args==['/usr/bin/lua',n.HELPER]:return json.dumps(world['policy']).encode()
            if args==['/usr/bin/lua',agent.INVENTORY]:return json.dumps(world['inventory']).encode()
            if args==['ubus','call','system','board']:return json.dumps(world['board']).encode()
            if args==['nft','--version']:return b'nftables v1.0.2\n'
            if args[:2]==['ubus','call'] and args[2].startswith('network.interface.'):
                value=world['ifaces'].get(args[2][len('network.interface.'):])
                if value is None:raise subprocess.CalledProcessError(4,args)
                return json.dumps(value).encode()
            if args==['ip','-4','-j','route','show','table','all']:return json.dumps(world['routes']).encode()
            if args==['ip','-4','-j','rule','show']:return json.dumps(world['rules']).encode()
            if args[:5]==['ip','-4','-j','route','get']:return json.dumps(route_get(world,args[5],int(args[7]))).encode()
            if args==['iptables-save','-t','mangle'] and world['mangle'] is not None:return world['mangle'].encode()
            raise subprocess.CalledProcessError(1,args)
        for target,value in ((n,'command'),(agent,'command')):stack.enter_context(patch.object(target,value,command))
        stack.enter_context(patch.object(n,'Path',Rooted));stack.enter_context(patch.object(agent,'Path',Rooted))
        stack.enter_context(patch.object(n,'RUNTIME',root/'run'))
        stack.enter_context(patch('preparation_control.auto_blocker',return_value=None))
        stack.enter_context(patch('native_platform.assess',side_effect=lambda board,data:list(world['assess'])))
        stack.enter_context(patch('device_profile.detect',return_value='unknown'))
        stack.enter_context(patch('rollback_recovery.rtp_lock_busy',return_value=False))
        stack.enter_context(patch.object(n.Linux,'acceleration',lambda self:copy.deepcopy(world['acceleration'])))
        stack.enter_context(patch('time.time',return_value=NOW))
        if world['network'] is not None:stack.enter_context(patch('pair_auto.network',side_effect=lambda:copy.deepcopy(world['network'])))
        return self

    def __exit__(self,*exc):self.stack.close()


def py_diagnostic(world):
    with PythonRouter(world):
        blockers,selection=n.Linux().diagnostic()
        return [blockers,selection]


def py_attest_policy(world,selection):
    with PythonRouter(world):
        with patch.object(n,'slot_contract_verified',return_value=True):
            result=n.Linux().attest_policy(copy.deepcopy(selection))
    result.pop('time',None)
    return result


def py_kernel_fingerprint(world):
    with PythonRouter(world):return n.Linux().kernel_fingerprint()


def py_order(world,bindings):
    with PythonRouter(world):
        backend=n.Linux()
        if bindings is not None:backend.use_process_bindings(bindings)
        order,digest=backend.order();return [order,digest]


def py_candidates(world):
    with PythonRouter(world):return n.Linux().candidates()


def py_instant_request(world,bindings,after):
    with PythonRouter(world):
        backend=n.Linux()
        if bindings is not None:backend.use_process_bindings(bindings)
        sections=backend.policy()['sections'];names={};tunnels={}
        for s in sections:
            identity=n.section_id(s,backend.process_bindings);names[identity]=s['.name']
            if s.get('.type')=='rule' and s.get('enabled','1')!='0' and s.get('tunnel_id'):tunnels[identity]=str(s['tunnel_id'])
        order=[tunnels[i] for i in after if i in tunnels]
        if len(order)!=2:raise n.Refused('FAST-RULES')
        return [names,order]


def py_guard_script(devices):
    seen={}
    state={'installed':False}
    def run(args,stdout=None,stderr=None,timeout=None,**_):
        if args[:3]==['nft','list','table']:
            return SimpleNamespace(returncode=0 if state['installed'] else 1,stdout=b'... comment "homensai-owned-guard" ...')
        if args[:2]==['nft','-c']:seen['script']=Path(args[3]).read_text();return SimpleNamespace(returncode=0,stdout=b'')
        if args[:2]==['nft','-f']:state['installed']=True;return SimpleNamespace(returncode=0,stdout=b'')
        raise AssertionError(args)
    with tempfile.TemporaryDirectory() as folder:
        with patch.object(n,'RUNTIME',Path(folder)),patch.object(n.subprocess,'run',side_effect=run),\
             patch.object(n.subprocess,'Popen'),patch.object(n.uuid,'uuid4',return_value=SimpleNamespace(hex='00000001'+'0'*24)):
            n.Linux().guard(devices)
    return seen['script']


# --- cases -------------------------------------------------------------------------------------------------
def identity_cases():
    cases=[]
    for bindings in (None,BINDINGS):
        for sections in (stock_sections(),stock_sections(reserve_first=True),stock_sections(process_via='ovpnclient2'),
                         kernel_fixture()[0]['sections']):
            cases.append(('section_ids',{'sections':sections,'bindings':bindings},
                          lambda s=sections,b=bindings:{'ids':[n.section_id(x,b) for x in s],'order':n.policy_order(s,b),'hash':n.policy_hash(s,b)}))
    odd=stock_sections();odd[2]['from']=['192.168.8.10','192.168.8.11'];odd[3]['name']='Канал ✓';odd[3]['masq']='1'
    odd.append({'.name':'cfg0999ee','.anonymous':'1','.type':'rule','enabled':'0','via':'wgclient3','mark':'7','to_manual':[]})
    for b in (None,BINDINGS):
        cases.append(('section_ids',{'sections':odd,'bindings':b},lambda s=odd,b=b:{'ids':[n.section_id(x,b) for x in s],'order':n.policy_order(s,b),'hash':n.policy_hash(s,b)}))
    dup=stock_sections()+[copy.deepcopy(stock_sections()[2])]
    cases.append(('section_ids',{'sections':dup,'bindings':None},lambda:{'order':n.policy_order(dup,None)}))
    for bindings in ({'wgclient1':4096},{'wgclient1':4096,'eth0':1},{'wgclient1':4096,'ovpnclient2':4096},{'wgclient1':0,'ovpnclient2':1}):
        cases.append(('section_ids',{'sections':stock_sections(),'bindings':bindings},lambda b=bindings:n.policy_hash(stock_sections(),b)))
    # process_policy / pair_interfaces
    for interfaces in (('wgclient1','ovpnclient2'),('wgclient1','wgclient9')):
        for sections in (stock_sections(),stock_sections(process_via='ovpnclient2'),kernel_fixture()[0]['sections']):
            cases.append(('selected_bindings',{'sections':sections,'interfaces':list(interfaces)},lambda s=sections,i=interfaces:process_policy.selected_bindings(s,i)))
    for sections in (stock_sections(),stock_sections(reserve_first=True),stock_sections(process_via='ovpnclient2')):
        cases.append(('applied',{'sections':sections,'bindings':BINDINGS},lambda s=sections:process_policy.applied(s,BINDINGS)))
    for settings in ({},{'plan_source_tunnel':'wireguard:wgclient2','plan_target_tunnel':'openvpn:ovpnclient3'},
                     {'plan_source_tunnel':'openvpn:wgclient2'},{'plan_target_tunnel':'wireguard:wgclient1'},{'plan_source_tunnel':'a:b:c'}):
        cases.append(('roles',{'settings':settings},lambda s=settings:pair_interfaces.roles(s)))
    return cases


def choose_cases():
    cases=[]
    variants=[{},{'native_order_direction':'last'},{'native_order_direction':None},{'native_proof_scope':'router-probed-ipv4'},
              {'native_proof_scope':'router-probed-ipv4','pair_auto_mode':'router-probed-ipv4'},{'native_proof_scope':'bogus'},
              {'plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'openvpn:ovpnclient2','plan_source':None,'plan_target':None},
              {'plan_source_tunnel':'wireguard:nope'},{'plan_target':'wireguard:peer_2002'}]
    for sections in (stock_sections(),stock_sections(reserve_first=True),kernel_fixture()[0]['sections']):
        for change in variants:
            data=policy_data(copy.deepcopy(sections),**{k:v for k,v in change.items() if v is not None})
            for k,v in change.items():
                if v is None:data['settings'].pop(k,None)
            rows=profiles()
            cases.append(('choose',{'data':data,'profiles':rows},lambda d=data,r=rows:n.choose(copy.deepcopy(d),copy.deepcopy(r))))
    def mutated(fn):
        data=policy_data();fn(data);return data
    for fn in (lambda d:d.update(ipv6='1'),lambda d:d['sections'][1].update(enabled='1'),lambda d:d['sections'][0].update(enabled='0'),
               lambda d:d['sections'][2].update(killswitch='0'),lambda d:d['sections'][3].update(via='wgclient1'),
               lambda d:d['firewall_defaults'][0].update(flow_offloading_hw='1'),lambda d:d.update(firewall_defaults={}),
               lambda d:d['sections'].insert(4,{'.name':'sp','.type':'rule','enabled':'1','killswitch':'1','via':'wgclient3','from':'10.0.0.1'}),
               lambda d:d['sections'].insert(2,{'.name':'sp','.type':'rule','enabled':'1','killswitch':'1','via':'wgclient3','from':'10.0.0.1'}),
               lambda d:d['sections'].insert(3,{'.name':'mid','.type':'rule','enabled':'0','via':'wgclient3'}),
               lambda d:d['sections'][4].update(mark='0x2000')):
        data=mutated(fn);rows=profiles()
        cases.append(('choose',{'data':data,'profiles':rows},lambda d=data,r=rows:n.choose(copy.deepcopy(d),copy.deepcopy(r))))
    rows=profiles();rows[1]['interface']=None
    cases.append(('choose',{'data':policy_data(),'profiles':rows},lambda r=rows:n.choose(policy_data(),copy.deepcopy(r))))
    rows=profiles()+[copy.deepcopy(profiles()[0])]
    cases.append(('choose',{'data':policy_data(),'profiles':rows},lambda r=rows:n.choose(policy_data(),copy.deepcopy(r))))
    rows=profiles();rows[1]['vendor_tunnel_id']='openvpn:other'
    cases.append(('choose',{'data':policy_data(),'profiles':rows},lambda r=rows:n.choose(policy_data(),copy.deepcopy(r))))
    return cases


def diagnosis_cases():
    cases=[];settings=policy_data()['settings']
    def status(fn=None,now=NOW):
        s=status_json(now)
        if fn:fn(s)
        return s
    changes=[None,lambda s:s.update(time=NOW-100),lambda s:s.update(error='x'),lambda s:s['vendor_observation']['groups'][0].update(state='PENDING'),
             lambda s:s['vendor_observation']['groups'][1].update(generation='0'*32),lambda s:s.update(uplink_observation={'state':'DOWN','time':NOW}),
             lambda s:s['vendor_observation']['groups'][0].update(changed_at=NOW-10),lambda s:s['profiles'][0].update(vendor_changed_at=NOW-121),
             lambda s:s['profiles'][0].update(vendor_state='PENDING'),lambda s:s['profiles'][1].update(time=NOW-200),
             lambda s:s['vendor_observation']['groups'][0].update(stable_samples=1),lambda s:s['vendor_observation'].update(version=True),
             lambda s:s['profiles'].append(copy.deepcopy(s['profiles'][0])),lambda s:s['profiles'][0].update(code='VPN-001',dns_ok=False,https_success=0),
             lambda s:s['profiles'][0].update(code='DNS-001'),lambda s:s['profiles'][0].update(code='ROUTE-001'),lambda s:s['profiles'][0].update(interface=None),
             lambda s:s['profiles'][0].update(vendor_state='UNKNOWN'),lambda s:s['profiles'][0].update(code='VENDOR-IDENTITY-CHANGED')]
    for change in changes:
        s=status(change)
        for age,settle in ((30,30),(90,60),(0,30),(30,10)):
            cases.append(('resolve_pair',{'status':s,'settings':settings,'now':NOW,'max_age':age,'settle':settle},
                          lambda s=s,a=age,t=settle:fd.resolve_pair(copy.deepcopy(s),settings,NOW,a,t)))
        for st in (settings,None,{'interval':'60'}):
            cases.append(('diagnose',{'status':s,'source':'wireguard:peer_2002','now':NOW,'settings':st},
                          lambda s=s,st=st:fd.diagnose(copy.deepcopy(s),'wireguard:peer_2002',NOW,st)))
    for anchors in ({'plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'openvpn:ovpnclient2'},
                    {'plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'wireguard:wgclient1'},{'plan_source':'missing'}):
        st=dict(settings,**anchors);s=status()
        cases.append(('resolve_pair',{'status':s,'settings':st,'now':NOW,'max_age':30,'settle':30},lambda s=s,st=st:fd.resolve_pair(s,st,NOW,30,30)))
    rows=profiles()
    samples=[{'id':rows[0]['id'],'time':NOW-k*10,'code':None,'dns_ok':True,'https_success':2,'interface':'wgclient1',
              'vendor_tunnel_id':rows[0]['vendor_tunnel_id'],'vendor_generation':rows[0]['vendor_generation']} for k in range(5)]
    for change in (None,lambda x:x[1].update(vendor_generation='f'*32),lambda x:x.append(dict(x[0],code='VPN-001')),lambda x:x.append({'id':1}),
                   lambda x:x[2].update(time=NOW-1000)):
        values=copy.deepcopy(samples)
        if change:change(values)
        cases.append(('scoped_samples',{'samples':values,'profile':rows[0]},lambda v=values:fd.scoped_samples(v,rows[0])))
    return cases


def kernel_cases():
    cases=[]
    for reserve in (False,True):
        data,selection,mangle,rules=kernel_fixture(reserve)
        cases.append(('attest',{'policy':data,'selection':selection,'mangle':mangle,'rules':rules},lambda d=data,s=selection,m=mangle,r=rules:kp.attest(d,s,m,r)))
    data,selection,mangle,rules=kernel_fixture()
    mutations=[lambda s:'*mangle\n:PREROUTING ACCEPT [100:1000]\n:PORTAL_TTL - [0:0]\nCOMMIT\n',
               lambda s:s.replace('-A PREROUTING -j VPN_PREROUTING_HOOK\n',''),lambda s:s.replace('-i br-lan -j ROUTE_POLICY','-i guest -j ROUTE_POLICY'),
               lambda s:s.replace('--set-xmark 0x1000/0xf000','--set-xmark 0xb000/0xf000'),lambda s:s.replace('--set-xmark 0x1000/0xf000','--set-xmark 0x1000/0xff00'),
               lambda s:s.replace('-j MARK --set-xmark 0x1000','-i guest -j MARK --set-xmark 0x1000'),
               lambda s:s.replace('COMMIT','-A PREROUTING -j MARK --set-xmark 0xb000/0xf000\nCOMMIT'),
               lambda s:s.replace('-A TUNNEL5841_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP\n',''),
               lambda s:s.replace('COMMIT','-A vpn_in_new_mark -i br-lan -j CONNMARK --set-xmark 0xb000/0xf000\nCOMMIT'),
               lambda s:s.replace('COMMIT','-A vpn_in_new_mark -i eth0 -j CONNMARK --set-xmark 0xb000/0xf000\nCOMMIT'),
               lambda s:s.replace('COMMIT','-A VPN_PREROUTING_HOOK -j CONNMARK --save-mark\nCOMMIT'),
               lambda s:s.replace('COMMIT','-A VPN_PREROUTING_HOOK -i eth1 -j ACCEPT\nCOMMIT'),
               lambda s:s.replace('COMMIT','-A PREROUTING -j TCPMSS --clamp-mss-to-pmtu\nCOMMIT'),
               lambda s:s.replace('COMMIT','-A PORTAL_TTL -j TTL --ttl-set 64\nCOMMIT'),
               lambda s:s.replace('COMMIT','-A PORTAL_TTL -j ACCEPT\nCOMMIT'),
               lambda s:s.replace('[0:0]','[1234:100000]'),lambda s:'*mangle\n:PREROUTING ACCEPT [0:0]\n:ROUTE_POLICY - [0:0]\nCOMMIT\n',
               lambda s:'*mangle\n:PREROUTING ACCEPT [0:0]\n-A PREROUTING -j MARK --set-xmark 0x8000/0xf000\nCOMMIT\n',
               lambda s:'*mangle\n:PREROUTING ACCEPT [0:0]\n:PORTAL_TTL - [0:0]\n-A PREROUTING -j PORTAL_TTL\n-A PORTAL_TTL -j TTL --ttl-set 1\nCOMMIT\n',
               lambda s:s.replace('*mangle','# Generated by iptables-save v1.8.7\n*mangle'),lambda s:s+'garbage\n',lambda s:s.replace('"','')]
    for change in mutations:
        text=change(mangle)
        for kind,fn in (('attest',kp.attest),('missing_only',kp.missing_only)):
            cases.append((kind,{'policy':data,'selection':selection,'mangle':text,'rules':rules},lambda f=fn,t=text:f(data,copy.deepcopy(selection),t,rules)))
        cases.append(('unrouted',{'text':text},lambda t=text:kp.unrouted(t)))
        cases.append(('fingerprint',{'mangle':text,'rules':rules},lambda t=text:n.digest({'mangle':kp.parse_mangle(t),'rules':rules})))
    rule_changes=[lambda r:r.append(copy.deepcopy(r[0])),lambda r:r[0].update(table='1012'),lambda r:r[0].update(fwmask='0xff00'),
                  lambda r:r[0].update(iif='lo'),lambda r:r[0].update(priority=10000),lambda r:r[0].update(uidrange='0-0'),
                  lambda r:r[0].update(tos='0x10'),lambda r:r[0].update({'not':None}),lambda r:r.insert(0,{'priority':5000,'src':'all','iif':'br-lan','action':'blackhole'}),
                  lambda r:r.insert(0,{'priority':5000,'src':'all','table':'9999'}),
                  lambda r:r.__setitem__(slice(0,0),[{'priority':0,'src':'all','table':'local'},{'priority':1,'src':'all','iif':'lo','table':'16800'},
                                                     {'priority':800,'src':'all','table':'9910','suppress_prefixlen':0}]),
                  lambda r:r[0].update(fwmark='0x1000/0xf000',fwmask=None),lambda r:r[0].update(fwmark=4096),lambda r:r.reverse(),
                  lambda r:r.insert(0,{'priority':10,'src':'all','fwmark':'0x2000/0xf000','table':'1002'}),
                  lambda r:r.insert(0,{'priority':10,'src':'all','fwmark':'0x1000/0xf000','table':'1002','not':None})]
    for change in rule_changes:
        values=copy.deepcopy(rules);change(values)
        cases.append(('attest',{'policy':data,'selection':selection,'mangle':mangle,'rules':values},lambda v=values:kp.attest(data,copy.deepcopy(selection),mangle,v)))
        cases.append(('fingerprint',{'mangle':mangle,'rules':values},lambda v=values:n.digest({'mangle':kp.parse_mangle(mangle),'rules':v})))
    # static bindings
    for change in (None,lambda s,r:s['source'].update(kernel_binding={'code':'VPN-001'}),lambda s,r:s['source'].update(kernel_binding={'code':'ROUTE-001'}),
                   lambda s,r:r[0].update(ip4table='9999'),lambda s,r:r[0].update(config='peer_9999'),lambda s,r:r[1].update(mark='0xb000/0xf000'),
                   lambda s,r:r[1].update(lookup='1012'),lambda s,r:r[1].update(priority='5000'),lambda s,r:s['source'].update(interface='wgclient6'),
                   lambda s,r:r.append(copy.deepcopy(r[0]))):
        chosen=copy.deepcopy(selection);rows=network_fixture(chosen)
        if change:change(chosen,rows)
        cases.append(('static_bindings',{'selection':chosen,'network':rows},lambda c=chosen,r=rows:kp.static_bindings(c,r)))
    return cases


def network_cases():
    cases=[]
    rows=[{'.name':'loopback','.type':'interface','.anonymous':False,'proto':'static','ipaddr':'127.0.0.1'},
          {'.name':'wgclient1','.type':'interface','.anonymous':False,'proto':'wgclient','disabled':'0','auto':'0','config':'peer_2002'},
          {'.name':'cfg0a1b2c','.type':'rule','.anonymous':True,'mark':'0x1000/0xf000','lookup':'1001','priority':'6000'},
          {'.name':'ovpnclient7','.type':'interface','.anonymous':False,'proto':'ovpnclient','disabled':'1'},
          {'.name':'cfg0a1b2d','.type':'route','.anonymous':True,'target':'10.0.0.0/8'},
          {'.name':'lan','.type':'interface','.anonymous':False,'proto':'static','ipaddr':['192.168.8.1/24','fd00::1/64']}]
    for managed in (None,{'wgclient1':'wgclient','ovpnclient2':'ovpnclient'},{'wgclient1':'wgclient','ovpnclient7':'ovpnclient'}):
        cases.append(('normalized_network',{'rows':rows,'managed':managed},lambda m=managed:pair_auto.normalized_network(rows,m)))
    dhcp=(b"config dnsmasq\n\toption domain 'lan'\n\nconfig dnsmasq 'wgclient3'\n\toption disabled '1'\n\nconfig dnsmasq 'ovpnclient2'\n"
          b"\toption disabled '1'\n\nconfig dnsmasq 'wgclient4'\n\toption disabled '0'\nconfig host\n\toption name 'x'\n")
    firewall=(b"config zone\n\toption name 'wan'\n\toption gl_wan_like '1'\n\toption gl_bwa_managed\t'1'\r\n\toption gl_wan_likes '1'\n"
              b"config rule\n\toption name 'v'\n\toption gl_vpn_rules '1'\n\nconfig\trule\n\toption gl_vpn_rules '1'  \r\nconfig rule\n\toption gl_vpn_rules '0'\n")
    for name,data in (('dhcp',dhcp),('firewall',firewall),('wireguard',b"config peer 'x'\n"),('dhcp',b''),('firewall',b'\n\n')):
        for managed in (None,{'wgclient3':'wgclient','ovpnclient2':'ovpnclient'}):
            cases.append(('config_digest',{'name':name,'data':data.hex(),'managed':managed},lambda nm=name,d=data,m=managed:pair_auto.config_digest(nm,d,m)))
    for data in (firewall,b"config defaults\n",firewall.replace(b"'1'  \r\n",b"'1'")):
        cases.append(('static_firewall_digest',{'data':data.hex()},lambda d=data:pair_auto.static_firewall_digest(d)))
    for settings in ({},{'recovery_failures':'5','recovery_cooldown':' 120 ','recovery_return_policy':'hold_reserve'},
                     {'recovery_failures':'99','recovery_attempt_limit':'011','recovery_attempt_window':'x'},{'recovery_min_dwell':'-5','recovery_primary_stable':'1e3'}):
        cases.append(('settings_fingerprint',{'settings':settings},lambda s=settings:recovery_settings.fingerprint(s)))
    return cases


def recovery_cases():
    cases=[]
    a,b,c='a_'+'1'*60,'b_'+'2'*60,'cfg03'
    for before,target in (([a,b,c],[b,a,c]),([a,b,c],[c,b,a]),([a,b],[a,b]),([a,b],[a,c]),([a],[a]),([a,a],[a,a])):
        cases.append(('order_steps',{'before':before,'target':target},lambda x=before,y=target:list(rr.order_steps(x,y))))
    fp='f'*64
    base={'phase':'RESTORING','before':[a,b,c],'after':[b,a,c],'restore_before_order':[b,a,c],'restore_target_order':[a,b,c],
          'restore_before_verified':True,'restore_kernel_fingerprint':fp,'hash':'h'}
    steps=list(rr.order_steps([b,a,c],[a,b,c]))
    journals=[base,dict(base,restore_order_step=steps[0]),dict(base,restore_order_step={'version':1,'kind':'commit','before':[a,b,c],'after':[a,b,c]}),
              dict(base,restore_order_step=dict(steps[0],index=True)),dict(base,restore_order_step=dict(steps[0],index=5)),
              dict(base,restore_order_step=steps[0],phase='APPLYING'),dict(base,restore_order_step=steps[0],restore_before_verified=False)]
    forward=dict(base,restore_proof_source='forward',restore_order_origin=[b,a,c],restore_before_order=[a,b,c],kernel_before_verified=True,
                 rtp_dispatched=True,forward_policy_touched=True,kernel_before_fingerprint=fp,restore_order_step=steps[0])
    journals+=[forward,dict(forward,restore_proof_source='vendor-rebuild'),dict(forward,restore_proof_source='vendor-rebuild',failure_detail={'worker_stage':'rtp-dispatch'}),
               dict(forward,confirmed=1.5),dict(forward,restore_proof_source='other')]
    for journal in journals:
        cases.append(('validate_step',{'journal':journal},lambda j=journal:rr.validate_step(j)))
        cases.append(('restore_origin',{'journal':journal},lambda j=journal:rr.restore_origin(j)))
        for order in ([a,b,c],[b,a,c],[c,a,b]):
            cases.append(('order_allowed',{'journal':journal,'order':order},lambda j=journal,o=order:rr.order_allowed(j,o)))
    applying={'phase':'APPLYING','before':[a,b],'after':[b,a],'rtp_dispatched':True,'forward_policy_touched':True,'kernel_before_verified':True,'confirmed':None}
    for journal in (applying,dict(applying,restore_x=1),dict(applying,after=[a,b]),dict(applying,phase='WAIT-CLIENT'),dict(applying,kernel_confirmed=2)):
        cases.append(('forward_proof',{'journal':journal},lambda j=journal:rr.forward_proof(j)))
    return cases


def misc_cases():
    cases=[]
    s,t='wireguard:peer_1','openvpn:2_3'
    for kernel in (None,{'verified':True,'role':'source','profile_id':s,'time':NOW-3},{'verified':True,'role':'target','profile_id':t,'time':NOW-30},
                   {'verified':True,'role':'target','profile_id':s,'time':NOW},{'verified':True,'role':'source','profile_id':s,'time':NOW+10},
                   {'verified':False,'role':'source','profile_id':s,'time':NOW},{'verified':True,'role':'source','profile_id':s,'time':True}):
        for pair in ((s,t),(s,s),(s,'bad'),(None,t)):
            cases.append(('from_kernel',{'kernel':kernel,'source':pair[0],'target':pair[1],'now':NOW},lambda k=kernel,p=pair:channel_path.from_kernel(k,p[0],p[1],NOW)))
    good="package fw3_state\n\nconfig defaults\n\toption input 'ACCEPT'\n\nconfig zone 'z1'\n\toption name 'lan'\n\tlist network 'lan'\n\nconfig zone\n\toption name 'wan' # comment\n\nconfig zone\n\toption name \"wgclient\"\n"
    for text in (good,good+"\nconfig zone\n\toption name 'wan'\n",good.replace('package fw3_state\n',''),good+'config ipset\n\toption name x\n',
                 good+"config zone\n\toption name 'bad name'\n",good+"config zone 'z1'\n\toption name 'x'\n",'',good+"\toption name 'dup'\n",good.replace("'lan'\n\tlist","'lan'\n\toption name 'lan2'\n\tlist")):
        cases.append(('zones',{'text':text},lambda t=text:sorted(mt._zones(t))))
    log="[   12.5] hnat hook is disabled now!\n[ 13.000] value=1, hook is enabled now!\n[14] going to disable hook\n[15.1] something else\n"
    for lines,after in ((log,0),(log,13.5),(log,100),("[1.0] hnat_hook_toggle: disabled.\n",0),("[1.0] hook status = enabled !\n",0),
                        ("[1.0] HNAT HOOK IS ENABLED\n",0),("[1.0] hook_toggle is is currently: enabled\n",0),("[1.0] value=0, hook is enabled now!\n",0),("x\n",0)):
        cases.append(('hook_state',{'lines':lines,'after':after},lambda l=lines,a=after:n.fresh_hook_state(l,a)))
    before="[1.0] a\n[2.0] b\n";after_text=before+"[3.0] hook is disabled now!\n"
    for x,y in ((before,after_text),('',after_text),(before,before+before),(before,"[3.0] hook is enabled\n")):
        cases.append(('appended',{'before':x,'after':y},lambda x=x,y=y:n.appended_hook_state(x,y)))
    record={'schema':1,'state':'CLAIMED','direction':'reserve','request_id':'a'*32,'control_revision':'b'*32,'requested_at':10.5,'updated_at':11,
            'trial':'t','until':20,'source_id':'x','target_id':'y','transaction_id':None,'selection_hash':'c'*64,'vendor_identity':'d'*64,
            'settings_hash':'e'*64,'code':None}
    for change in ({},{'request_source':'manual'},{'request_source':'other'},{'schema':True},{'updated_at':9},{'code':'bad'},{'code':'OK-1'},
                   {'transaction_id':'f'*32},{'source_id':'y'},{'extra':1},{'trial':''}):
        row=dict(record,**change)
        cases.append(('valid_record',{'record':row},lambda r=row:manual_control.valid_record(r)))
    return cases


def backend_cases():
    cases=[]
    worlds=[base_world()]
    def variant(**over):worlds.append(base_world(**over))
    variant(assess=['VENDOR-WORKER-BUSY','FW3-SELECTED-ZONE-UNVERIFIED'])
    variant(glversion='4.10.0\n')
    variant(board={'board_name':'glinet,gl-mt6000'})
    variant(audit_extra={'/usr/bin/missing':'0'*64})
    variant(audit_extra={'/usr/bin/rtp2.sh':'0'*64})
    variant(acceleration={'loaded':['mtkhnat'],'hnat_runtime':'enabled'})
    variant(acceleration={'loaded':['shortcut_fe'],'hnat_runtime':'unknown'})
    variant(policy=policy_data(terms_version='0'))
    variant(policy=policy_data(monitor_only='1'))
    variant(policy=policy_data(router_model='mt3000'))
    variant(policy=dict(policy_data(),lan='eth0'))
    variant(policy=policy_data(interval='x'))
    variant(policy=policy_data(interval='60'))
    variant(policy=policy_data(stock_sections(reserve_first=True)))
    variant(status=status_json(NOW-500))
    variant(ifaces={'wgclient1':ubus_iface(True,'wgclient1'),'ovpnclient2':ubus_iface(False)})
    down=status_json()
    for row in down['profiles']:
        if row['interface']=='ovpnclient2':row.update(code='VPN-001',device=None,mark=None,table=None,ifindex=None)
    variant(ifaces={'wgclient1':ubus_iface(True,'wgclient1'),'ovpnclient2':ubus_iface(False)},status=down)
    variant(ifindex={'wgclient1':12,'ovpnclient2':11})
    variant(route_get_override={'8.8.8.8':[{'dst':'8.8.8.8','dev':'eth0','table':'main'}]})
    inv=inventory_rows();inv['servers'][0]['enabled']=False
    variant(inventory=inv)
    inv=inventory_rows();inv['profiles'].append({'id':'bad id!','section':'x'});inv['servers']={}
    variant(inventory=inv)
    variant(ifaces={'wgclient1':ubus_iface(True,'wgclient1')})
    for world in worlds:
        cases.append(('diagnostic',{'world':lua_world(world)},lambda w=world:py_diagnostic(w)))
    data,selection,mangle,rules=kernel_fixture()
    kworld=base_world(policy=dict(policy_data(),sections=data['sections'],settings=dict(policy_data()['settings'],**data['settings'])),
                      mangle=mangle,rules=rules,network=network_fixture(selection))
    cases.append(('kernel_fingerprint',{'world':lua_world(kworld)},lambda:py_kernel_fingerprint(kworld)))
    for change in (None,lambda m:m.replace('--set-xmark 0x1000/0xf000','--set-xmark 0xb000/0xf000'),
                   lambda m:'*mangle\n:PREROUTING ACCEPT [100:1000]\n:PORTAL_TTL - [0:0]\nCOMMIT\n'):
        w=copy.deepcopy(kworld)
        if change:w['mangle']=change(w['mangle'])
        cases.append(('attest_policy',{'world':lua_world(w),'selection':selection},lambda w=w:py_attest_policy(w,selection)))
        cases.append(('kernel_fingerprint',{'world':lua_world(w)},lambda w=w:py_kernel_fingerprint(w)))
    w=copy.deepcopy(kworld);w['network'][0]['ip4table']='9999'
    cases.append(('attest_policy',{'world':lua_world(w),'selection':selection},lambda w=w:py_attest_policy(w,selection)))
    for world,bindings in ((base_world(),None),(base_world(),BINDINGS),(base_world(policy=policy_data(stock_sections(reserve_first=True))),BINDINGS)):
        cases.append(('order',{'world':lua_world(world),'bindings':bindings},lambda w=world,b=bindings:py_order(w,b)))
        cases.append(('candidates',{'world':lua_world(world)},lambda w=world:py_candidates(w)))
        ids=n.policy_order(world['policy']['sections'],bindings)
        for after in ([ids[0],ids[1],ids[3],ids[2],ids[4]],ids,[ids[0],ids[1],ids[2]]):
            cases.append(('instant_request',{'world':lua_world(world),'bindings':bindings,'after':after},lambda w=world,b=bindings,a=after:py_instant_request(w,b,a)))
    for devices in (None,['wgclient1','ovpnclient2','wgclient1'],['wg;x'],[]):
        cases.append(('guard_script',{'world':lua_world(base_world()),'devices':devices},lambda d=devices:py_guard_script(d)))
    return cases


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaBackendSameAsPython(unittest.TestCase):
    def check(self,cases):
        results=run_lua(cases)
        self.assertEqual(len(results),len(cases))
        failures=[]
        for (kind,data,fn),lua in zip(cases,results):
            python=outcome(fn)
            if not same(kind,python,lua):failures.append((kind,json.dumps(data)[:300],python,lua))
        if failures:
            text='\n'.join('%s %s\n  python=%s\n  lua=%s'%(k,d,json.dumps(p)[:1500],json.dumps(l)[:1500]) for k,d,p,l in failures[:8])
            self.fail('%d of %d cases differ:\n%s'%(len(failures),len(cases),text))
        return results

    def test_identity_digests_choose_and_process_bindings(self):self.check(identity_cases()+choose_cases())
    def test_pair_freshness_diagnosis_and_scoped_samples(self):self.check(diagnosis_cases())
    def test_kernel_attestation_fingerprint_and_static_slots(self):self.check(kernel_cases())
    def test_network_identity_config_digests_and_settings_fingerprint(self):self.check(network_cases())
    def test_rollback_recovery_steps_and_proofs(self):self.check(recovery_cases())
    def test_channel_path_zones_hook_state_and_manual_record(self):self.check(misc_cases())

    def test_linux_methods_on_one_fake_router(self):
        cases=backend_cases()
        results=self.check(cases)
        # The happy path really is the full proof (not two equal refusals): a selection with a vendor identity.
        first=results[0]['ok']
        self.assertEqual(first[0],[]);self.assertRegex(first[1]['vendor_identity'],'^[a-f0-9]{64}$')
        self.assertEqual(first[1]['source']['kernel_binding'],{'code':None,'device':'wgclient1','mark':4096,'table':'1001','ifindex':10})
        attested=[r for (k,_,_),r in zip(cases,results) if k=='attest_policy']
        self.assertTrue(attested[0]['ok']['verified']);self.assertTrue(attested[2]['ok']['repairable_missing'])


if __name__=='__main__':
    unittest.main()
