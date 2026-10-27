"""Configured tunnel epochs and attribution; no router/network mutations."""
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import setup_config
from vendor_observation import VendorObserver, tunnel_identity


def profile(number=1,tunnel='wgclient1',group='90'):
    return {'id':'wireguard:peer_'+str(number),'section':'peer_'+str(number),'protocol':'wireguard',
            'name':'Server '+str(number),'interface':tunnel,
            'vendor_tunnel_id':'wireguard:'+tunnel if tunnel else None,
            'vendor_profile_group_id':'wireguard:'+group}


def inventory(*profiles):return {'profiles':list(profiles),'settings':{}}


def measure(p,**extra):
    return dict({'id':p['id'],'time':1000,'code':None,'https_success':3,'dns_ok':True,'rtt_ms':12,
                 'exit_ip':'93.184.216.34','device':'wgclient1','mark':4096,'table':'1001','ifindex':7},**extra)


class VendorObservationTests(unittest.TestCase):
    def test_endpoint_details_reach_status_only_for_matching_identity_and_without_extra_fields(self):
        p=profile();data=inventory(p);observer=VendorObserver()
        measured=measure(p,probe_checks=[{'target':'dns.quad9.net','result':'http-unsupported','http_status':505,'elapsed_ms':120,'token':'PRIVATE'},
              {'target':'dns.google','result':'ok','http_status':200,'elapsed_ms':80},
              {'target':'unknown-private-host','result':'ok','password':'PRIVATE'}])
        _,rows=observer.observe(data,data,[measured],1000)
        self.assertEqual(len(rows[0]['probe_checks']),2)
        self.assertEqual(rows[0]['probe_checks'][0]['http_status'],505)
        self.assertNotIn('PRIVATE',json.dumps(rows));self.assertNotIn('unknown-private-host',json.dumps(rows))
        _,changed=observer.observe(data,inventory(profile(2)),[measured],1030)
        self.assertNotIn('probe_checks',changed[0])

    def test_provider_group_does_not_merge_two_independent_logical_tunnels(self):
        first=profile();second=profile(2,'wgclient2')
        observed,_=VendorObserver().observe(inventory(first,second),inventory(first,second),[],1000)
        self.assertEqual({g['id'] for g in observed['groups']},{'wireguard:wgclient1','wireguard:wgclient2'})
        self.assertTrue(all(len(g['profiles'])==1 for g in observed['groups']))

    def test_two_distinct_stable_scans_are_identity_only_and_never_exhaustion_proof(self):
        observer=VendorObserver();p=profile();data=inventory(p)
        initial,rows=observer.observe(data,data,[measure(p)],1000)
        settled,again=observer.observe(data,data,[measure(p)],1030)
        self.assertEqual(initial['groups'][0]['state'],'PENDING')
        self.assertEqual(settled['groups'][0]['state'],'SETTLED')
        self.assertEqual(settled['groups'][0]['stable_samples'],2)
        self.assertEqual(rows[0]['vendor_generation'],again[0]['vendor_generation'])
        self.assertIsNone(settled['groups'][0]['vendor_attempts_exhausted'])
        self.assertEqual(settled['events'][0]['cause'],'UNOBSERVED')

    def test_profile_change_during_pass_drops_old_success_without_retagging_id(self):
        first=profile();second=profile(2);observer=VendorObserver()
        original=measure(first);untouched=copy.deepcopy(original)
        state,rows=observer.observe(inventory(first),inventory(second),[original],1000)
        self.assertEqual(rows[0]['id'],first['id']);self.assertEqual(original,untouched)
        self.assertEqual(rows[0]['code'],'VENDOR-IDENTITY-CHANGED')
        for key in ('https_success','dns_ok','rtt_ms','exit_ip'):self.assertNotIn(key,rows[0])
        self.assertIsNone(rows[0]['vendor_generation']);self.assertEqual(state['groups'][0]['state'],'UNKNOWN')

    def test_a_to_b_to_a_and_restart_have_distinct_epochs_keep_original_profile_history(self):
        observer=VendorObserver();generations=[]
        for index,p in enumerate((profile(),profile(2),profile())):
            state,rows=observer.observe(inventory(p),inventory(p),[measure(p)],1000+30*index)
            generations.append(rows[0]['vendor_generation']);self.assertEqual(rows[0]['id'],p['id'])
        self.assertEqual(len(set(generations)),3)
        self.assertEqual(state['groups'][0]['profiles'],['wireguard:peer_1','wireguard:peer_2'])
        _,rows=VendorObserver().observe(inventory(profile()),inventory(profile()),[measure(profile())],1090)
        self.assertNotIn(rows[0]['vendor_generation'],generations)

    def test_kernel_epoch_change_and_disappear_reappear_reset_settling(self):
        observer=VendorObserver();p=profile();data=inventory(p)
        _,first=observer.observe(data,data,[measure(p)],1000)
        changed,second=observer.observe(data,data,[measure(p,ifindex=8)],1030)
        self.assertEqual(changed['groups'][0]['state'],'PENDING')
        self.assertNotEqual(first[0]['vendor_generation'],second[0]['vendor_generation'])
        missing,_=observer.observe(inventory(),inventory(),[],1060)
        self.assertEqual(missing['groups'][0]['state'],'UNKNOWN')
        self.assertIsNone(missing['groups'][0]['generation'])
        _,third=observer.observe(data,data,[measure(p,ifindex=8)],1090)
        self.assertNotEqual(second[0]['vendor_generation'],third[0]['vendor_generation'])

    def test_duplicate_tunnels_duplicate_profile_and_protocol_mismatch_fail_closed(self):
        p=profile()
        for profiles in ([p,profile(2)],[p,p],[dict(p,protocol='openvpn')],
                         [dict(p,vendor_tunnel_id='wireguard:other')]):
            data=inventory(*profiles)
            _,rows=VendorObserver().observe(data,data,[measure(p)],1000)
            self.assertIsNotNone(rows[0]['code']);self.assertIsNone(rows[0]['vendor_generation'])
            self.assertNotIn('dns_ok',rows[0])
        self.assertIsNone(tunnel_identity(dict(p,id='openvpn:1_1')))

    def test_measured_payload_cannot_override_inventory_protocol_or_interface(self):
        p=profile();_,rows=VendorObserver().observe(inventory(p),inventory(p),
            [dict(measure(p),protocol='openvpn',section='injected',interface='other')],1000)
        self.assertNotIn('protocol',rows[0]);self.assertNotIn('section',rows[0])
        self.assertEqual(rows[0]['interface'],'wgclient1')

    def test_repeated_timestamp_does_not_settle_and_clock_reversal_rotates_generation(self):
        observer=VendorObserver();p=profile();data=inventory(p)
        _,first=observer.observe(data,data,[measure(p)],1000)
        repeated,_=observer.observe(data,data,[measure(p)],1000)
        self.assertEqual(repeated['groups'][0]['stable_samples'],1)
        reversed_state,rows=observer.observe(data,data,[measure(p)],999)
        self.assertEqual(reversed_state['groups'][0]['state'],'PENDING')
        self.assertNotEqual(rows[0]['vendor_generation'],first[0]['vendor_generation'])

    def test_events_are_bounded_and_cannot_contain_credentials(self):
        observer=VendorObserver()
        for index in range(80):
            p=profile(index%2+1);p['private_key']='PRIVATE_SENTINEL';p['endpoint']='ENDPOINT_SENTINEL'
            state,_=observer.observe(inventory(p),inventory(p),[measure(p)],1000+index)
        self.assertEqual(len(state['events']),50)
        self.assertNotIn('SENTINEL',json.dumps(state));self.assertNotIn('private_key',json.dumps(state))

    def test_400_tunnels_churn_keeps_selected_channels_first_and_recent_members_bounded(self):
        observer=VendorObserver();profiles=[profile(index+1,'wgclient'+str(index+1)) for index in range(400)]
        data=inventory(*profiles)
        data['settings']={'plan_source':profiles[-1]['id'],'plan_source_tunnel':profiles[-1]['vendor_tunnel_id'],
                          'plan_target':profiles[-2]['id'],'plan_target_tunnel':profiles[-2]['vendor_tunnel_id']}
        for index in range(20):
            data['profiles'][0]=profile(1000+index)
            state,_=observer.observe(data,data,[],1000+index)
        self.assertEqual(len(state['groups']),400)
        self.assertEqual([g['id'] for g in state['groups'][:2]],['wireguard:wgclient400','wireguard:wgclient399'])
        changed=[g for g in state['groups'] if g['id']=='wireguard:wgclient1'][0]
        self.assertEqual(len(changed['profiles']),8)
        self.assertEqual(changed['profiles'][0],changed['current_profile'])
        self.assertEqual(changed['profiles'][1],changed['previous_profile'])
        self.assertLess(len(json.dumps(state,ensure_ascii=True).encode()),300000)

    def test_saved_pair_channel_survives_vendor_member_change_but_new_inactive_choice_clears(self):
        old=profile(1,None);new=profile(3);reserve=profile(2,'wgclient2')
        args={'source':old['id'],'target':reserve['id'],'interval':30,'duration':10,'session_loss':False,
              'servers':[{'profile':p['id'],'name':p['name'],'channel':'editable-label','priority':i+1,'enabled':True}
                         for i,p in enumerate((old,new,reserve))]}
        existing={'plan_source':old['id'],'plan_source_tunnel':'wireguard:wgclient1'}
        main=setup_config.system_payload(args,[old,new,reserve],existing)['main']
        self.assertEqual(main['plan_source_tunnel'],'wireguard:wgclient1')
        self.assertEqual(main['plan_target_tunnel'],'wireguard:wgclient2')
        existing['plan_source']='wireguard:peer_999'
        self.assertEqual(setup_config.system_payload(args,[old,new,reserve],existing)['main']['plan_source_tunnel'],'')

    def test_actual_system_save_derives_anchors_only_after_entering_control_lock(self):
        entered=[];p=profile();reserve=profile(2,'wgclient2')
        args={'source':p['id'],'target':reserve['id'],'interval':30,'duration':10,'session_loss':False,
              'servers':[{'profile':r['id'],'name':r['name'],'channel':'Main','priority':i+1,'enabled':True}
                         for i,r in enumerate((p,reserve))]}
        @contextmanager
        def lock():
            entered.append(True)
            try:yield
            finally:entered.pop()
        def snapshot():
            self.assertTrue(entered);return inventory(p,reserve)
        from types import SimpleNamespace
        with patch.object(setup_config,'control_lock',side_effect=lock),patch.object(setup_config,'inventory',side_effect=snapshot),\
                patch.object(agent,'read_json',return_value={}),patch('native_switch.journal_read',return_value={}),\
                patch('rpc_throttle.allow',return_value=True),patch.object(setup_config.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'OK')) as writer:
            self.assertTrue(setup_config.save(args,'system')['saved'])
        self.assertEqual(json.loads(writer.call_args.kwargs['input'])['main']['plan_source_tunnel'],'wireguard:wgclient1')

    def test_monitor_follows_saved_tunnel_new_member_but_respects_explicit_disable(self):
        old=profile(1,None);new=profile(3);unrelated=profile(4,'wgclient4')
        data=inventory(old,new,unrelated)
        data['servers']=[{'profile':old['id'],'enabled':True}]
        data['settings']={'plan_source':old['id'],'plan_source_tunnel':'wireguard:wgclient1'}
        rows,_=agent.monitoring_profiles(data)
        self.assertEqual({p['id'] for p in rows},{old['id'],new['id']})
        self.assertEqual([p for p in rows if p['id']==new['id']][0]['name'],new['name'])
        data['servers'].append({'profile':new['id'],'enabled':False})
        rows,_=agent.monitoring_profiles(data)
        self.assertEqual([p['id'] for p in rows],[old['id']])

    def test_explicit_pair_inside_one_known_tunnel_is_refused(self):
        old=profile(1,None);current=profile(2)
        args={'source':old['id'],'target':current['id'],'interval':30,'duration':10,'session_loss':False,
              'servers':[{'profile':p['id'],'name':p['name'],'channel':'Different '+str(i),
                          'priority':i+1,'enabled':True} for i,p in enumerate((old,current))]}
        with self.assertRaisesRegex(ValueError,'SETUP-SAME-TUNNEL'):
            setup_config.system_payload(args,[old,current],{'plan_source':old['id'],'plan_source_tunnel':'wireguard:wgclient1'})

    def test_kernel_rebound_during_probe_strips_all_quality(self):
        before={'code':None,'device':'wgclient1','mark':4096,'table':'1001','ifindex':7}
        with patch.object(agent,'route_binding',side_effect=[before,dict(before,ifindex=8)]),\
                patch.object(agent,'https_probe',return_value=12),patch.object(agent,'dns_probe',return_value=True):
            row=agent.probe(profile())
        self.assertEqual(row['code'],'VENDOR-IDENTITY-CHANGED')
        for key in ('https_success','dns_ok','rtt_ms','exit_ip'):self.assertNotIn(key,row)

    def test_parallel_probes_sharing_device_do_not_share_exit_identity(self):
        def binding(logical):return {'code':None,'device':'wgclient1','mark':4096 if logical=='wgclient1' else 8192,'table':'1001','ifindex':7}
        def trace(device,mark,target):
            address='93.184.216.34' if mark==4096 else '8.8.8.8'
            agent.remember_exit(device,('ip='+address+'\n').encode());return 12
        with patch.object(agent,'route_binding',side_effect=binding),patch.object(agent,'https_probe',side_effect=trace),\
                patch.object(agent,'dns_probe',return_value=True),ThreadPoolExecutor(max_workers=2) as pool:
            rows=list(pool.map(agent.probe,[profile(),profile(2,'wgclient2')]))
        self.assertEqual([r['exit_ip'] for r in rows],['93.184.216.34','8.8.8.8'])

    @unittest.skipUnless(shutil.which('lua5.1'),'Lua 5.1 runtime absent')
    def test_real_lua_inventory_does_not_last_win_duplicate_or_wrong_protocol_binding(self):
        root=Path(__file__).resolve().parents[1];fixture=(root/'tests/test_inventory.lua').read_text()
        variants=[fixture.replace("proto='wgclient',config='peer_56'","proto='ovpnclient',config='peer_56'"),
                  fixture.replace("{['.name']='wgclient1',['.type']='interface',proto='wgclient',config='peer_56'}",
                      "{['.name']='wgclient1',['.type']='interface',proto='wgclient',config='peer_56'},"+
                      "{['.name']='wgclient2',['.type']='interface',proto='wgclient',config='peer_56'}")]
        for script in variants:
            result=subprocess.run([shutil.which('lua5.1'),'-',str(root/'files/usr/lib/homensai-vpn/inventory.lua')],
                input=script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=True)
            p=[p for p in json.loads(result.stdout)['profiles'] if p['protocol']=='wireguard'][0]
            self.assertIsNone(p['interface']);self.assertIsNone(p['vendor_tunnel_id'])


if __name__=='__main__':unittest.main()
