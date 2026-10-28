import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from channel_path import snapshot, pair_snapshot


class ChannelPathTests(unittest.TestCase):
    def setUp(self):
        self.now = 10000
        identity = {'id':'wireguard:b','protocol':'wireguard','interface':'wgclient1',
                    'vendor_tunnel_id':'wireguard:wgclient1','vendor_generation':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}
        self.status = {'time':self.now, 'native_failover':{'time':self.now},
                       'profiles':[dict(identity,time=self.now,code=None,dns_ok=True,https_success=2)]}
        self.journal = {'phase':'COMMITTED','source':'openvpn:a','target':'wireguard:b','before':['r1','r2'],
                        'after':['r2','r1'],'hash':'h','confirmed':self.now-5,
                        'vendor_profiles':{'target':identity}}
        self.order = (['r2','r1'],'h')

    def test_only_confirmed_live_order_selects_target(self):
        self.assertEqual(snapshot(self.status,self.journal,self.order,self.now)['active_profile_id'],'wireguard:b')

    def test_ack_without_journal_never_selects_channel(self):
        self.status['manual_switch'] = {'state':'COMPLETED','target_id':'b'}
        self.assertFalse(snapshot(self.status,{},self.order,self.now)['confirmed'])

    def test_wrong_live_order_or_hash_refuses_selection(self):
        for order in ((['r1','r2'],'h'),(['r2','r1'],'different')):
            self.assertFalse(snapshot(self.status,self.journal,order,self.now)['confirmed'])

    def test_stale_monitor_controller_or_profile_is_unknown(self):
        for target,key in ((self.status,'time'),(self.status['native_failover'],'time'),(self.status['profiles'][0],'time')):
            old=target[key];target[key]=self.now-1000
            self.assertFalse(snapshot(self.status,self.journal,self.order,self.now)['confirmed']);target[key]=old

    def test_replaced_generation_cannot_inherit_green(self):
        self.status['profiles'][0]['vendor_generation']='g2'
        self.assertFalse(snapshot(self.status,self.journal,self.order,self.now)['confirmed'])

    def test_transition_is_yellow_without_selected_route(self):
        for phase in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):
            self.journal['phase']=phase
            self.status['native_failover']['state']=phase
            result=snapshot(self.status,self.journal,self.order,self.now)
            self.assertTrue(result['transitioning']);self.assertIsNone(result['active_profile_id'])

    def test_stale_transition_journal_with_stopped_controller_is_grey(self):
        self.journal['phase']='APPLYING';self.status['native_failover']['state']='STOPPED'
        self.assertFalse(snapshot(self.status,self.journal,self.order,self.now)['transitioning'])

    def test_malformed_profile_proof_does_not_crash_status(self):
        self.journal['vendor_profiles']=[]
        self.assertFalse(snapshot(self.status,self.journal,self.order,self.now)['confirmed'])

    def test_rollback_returns_selection_to_proved_source(self):
        self.journal.update(phase='ROLLED-BACK',source='wireguard:b',target='openvpn:a')
        self.journal['vendor_profiles']['source']=self.journal['vendor_profiles'].pop('target')
        result=snapshot(self.status,self.journal,(['r1','r2'],'h'),self.now)
        self.assertEqual(result['active_profile_id'],'wireguard:b')

    def test_no_client_confirmation_no_selected_channel(self):
        self.journal.pop('confirmed')
        self.assertFalse(snapshot(self.status,self.journal,self.order,self.now)['confirmed'])

    def test_failed_selected_path_stays_selected_for_red_display(self):
        self.status['profiles'][0]['code']='DNS-001'
        self.assertTrue(snapshot(self.status,self.journal,self.order,self.now)['confirmed'])


    def test_pair_policy_selection_is_independent_of_internet_health(self):
        from pair_policy import proof,transition
        selection={'source_rule':'r1','target_rule':'r2','direction':'first','order':['r1','r2'],
                   'source':{'id':'openvpn:1_1'},'target':{'id':'wireguard:peer_2'}}
        state={'phase':'RUNNING','order':['r1','r2'],'policy_hash':'h','policy_roles':proof(selection)}
        self.status['native_failover'].update(state='OBSERVING',source='openvpn:1_1',target='wireguard:peer_2')
        self.status['profiles'][0]['code']='DNS-001'
        result=pair_snapshot(self.status,state,{},(['r1','r2'],'h'),self.now)
        self.assertFalse(result['confirmed']);self.assertEqual(result['configured_profile_id'],'openvpn:1_1','configuration alone is not applied route proof')
        self.journal.update(source='openvpn:1_1',target='wireguard:peer_2')
        self.journal['pair_transition']=transition(selection,state['order'],'target')
        kernel={'verified':True,'role':'target','profile_id':'wireguard:peer_2','order':['r2','r1'],'policy_hash':'h','time':self.now}
        result=pair_snapshot(self.status,state,self.journal,self.order,self.now,kernel=kernel)
        self.assertTrue(result['confirmed']);self.assertEqual(result['active_profile_id'],'wireguard:peer_2')
        self.assertIn('Internet health is separate',result['scope'])

    def test_reserve_first_baseline_cannot_be_reported_as_primary_or_as_kernel_proof(self):
        from pair_policy import proof
        selection={'source_rule':'r1','target_rule':'r2','direction':'first','order':['r2','r1'],
                   'source':{'id':'openvpn:1_1'},'target':{'id':'wireguard:peer_2'}}
        state={'phase':'RUNNING','order':['r2','r1'],'policy_hash':'h','policy_roles':proof(selection)}
        self.status['native_failover'].update(state='OBSERVING',source='openvpn:1_1',target='wireguard:peer_2')
        result=pair_snapshot(self.status,state,{},(['r2','r1'],'h'),self.now)
        self.assertEqual(result['configured_profile_id'],'wireguard:peer_2');self.assertFalse(result['confirmed']);self.assertIsNone(result['active_profile_id'])
        kernel={'verified':True,'role':'target','profile_id':'wireguard:peer_2','order':['r2','r1'],'policy_hash':'h','time':self.now}
        result=pair_snapshot(self.status,state,{},(['r2','r1'],'h'),self.now,kernel=kernel)
        self.assertTrue(result['confirmed']);self.assertEqual(result['active_profile_id'],'wireguard:peer_2')
        kernel['role']='source'
        self.assertFalse(pair_snapshot(self.status,state,{},(['r2','r1'],'h'),self.now,kernel=kernel)['confirmed'])

    def test_historical_pair_state_without_role_proof_is_not_primary_selection(self):
        state={'phase':'RUNNING','order':['r2','r1'],'policy_hash':'h'}
        self.status['native_failover'].update(state='OBSERVING',source='openvpn:a',target='wireguard:b')
        self.assertFalse(pair_snapshot(self.status,state,{},(['r2','r1'],'h'),self.now)['confirmed'])

    def test_pair_external_order_or_stale_state_never_invents_selection(self):
        state={'phase':'RUNNING','order':['r1','r2'],'policy_hash':'h'}
        self.status['native_failover'].update(state='OBSERVING',source='openvpn:a',target='wireguard:b')
        self.assertFalse(pair_snapshot(self.status,state,self.journal,(['r1','r2'],'other'),self.now)['confirmed'])
        state['phase']='STOPPED'
        self.assertFalse(pair_snapshot(self.status,state,self.journal,self.order,self.now)['confirmed'])
        state['phase']='RUNNING';self.status['native_failover']['time']=self.now-1000
        self.assertFalse(pair_snapshot(self.status,state,self.journal,self.order,self.now)['confirmed'])


if __name__=='__main__':unittest.main()
