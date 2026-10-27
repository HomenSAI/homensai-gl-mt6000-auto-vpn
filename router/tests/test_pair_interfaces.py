import copy
from pathlib import Path
import sys,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import pair_interfaces as members
import pair_auto as pair
import native_switch as native
import test_pair_auto as pair_tests


class InterfaceTests(unittest.TestCase):
    def test_current_second_slot_and_same_protocol_pairs_are_exact_and_distinct(self):
        for first,second in [('wireguard:wgclient1','openvpn:ovpnclient2'),('wireguard:wgclient2','wireguard:wgclient3')]:
            roles=members.roles({'plan_source_tunnel':first,'plan_target_tunnel':second})
            self.assertEqual(roles,{'source':first.split(':')[1],'target':second.split(':')[1]})
        for value in (None,{},[],{'wgclient1':'ovpnclient'},{'wgclient1':'wgclient','evil;reboot':'wgclient'},{'wgclient01':'wgclient','ovpnclient2':'ovpnclient'}):
            with self.assertRaises(ValueError):members.validate(value)
        for source,target in [('wireguard:wgclient1','wireguard:wgclient1'),('openvpn:wgclient1','openvpn:ovpnclient2')]:
            with self.assertRaises(ValueError):members.roles({'plan_source_tunnel':source,'plan_target_tunnel':target})

    def test_network_normalization_ignores_only_the_selected_members(self):
        rows=[{'.name':'wgclient1','disabled':'0'},{'.name':'ovpnclient1','disabled':'1'},{'.name':'ovpnclient2','disabled':'0'}]
        changed=copy.deepcopy(rows);changed[2]['disabled']='1'
        managed={'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}
        self.assertEqual(pair.normalized_network(rows,managed),pair.normalized_network(changed,managed))
        changed[1]['disabled']='0'
        self.assertNotEqual(pair.normalized_network(rows,managed),pair.normalized_network(changed,managed))


class PairStartupTests(unittest.TestCase):
    setUp=pair_tests.Tests.setUp
    def test_refused_preflight_finishes_its_request_and_can_be_retried(self):
        pair.request(self.revision);request=pair.intent();old=copy.deepcopy(self.state);old['phase']='STOPPED';pair.save(old)
        with patch.object(pair,'begin',side_effect=ValueError('PREP-SOURCE-AUTOSTART')),patch.object(native,'publish') as publish:
            self.assertTrue(pair.tick(Mock(),{'pair_auto_mode':pair.MODE},self.revision))
        self.assertEqual(pair.public_phase(),'FAILED');self.assertIsNone(pair.public_intent())
        self.assertEqual(pair.intent()['failed_request_id'],request['id']);self.assertEqual(pair.read_state()['owned'],old['owned'])
        self.assertEqual(publish.call_args.args[0]['blockers'],['PREP-SOURCE-AUTOSTART'])
        self.assertTrue(pair.request(self.revision)['accepted']);self.assertEqual(pair.public_phase(),'STARTING')

    def test_a_late_failure_cannot_overwrite_stop_or_a_new_start(self):
        pair.request(self.revision);old=pair.intent();new=__import__('auto_control').current_revision(rotate=True)
        with __import__('auto_control').control_lock():pair.stop_locked(new)
        self.assertFalse(pair.fail_request(old,self.revision,ValueError('PREP-SOURCE-AUTOSTART')))
        self.assertEqual(pair.intent()['mode'],'off')
        pair.request(new);current=pair.intent()
        self.assertFalse(pair.fail_request(old,self.revision,ValueError('PREP-SOURCE-AUTOSTART')))
        self.assertEqual(pair.intent()['id'],current['id'])

    def test_already_connected_second_slot_is_not_reconnected(self):
        selection={'source':{'interface':'wgclient1','protocol':'wireguard'},'target':{'interface':'ovpnclient2','protocol':'openvpn'},'process_bindings':None,'order':['a','b'],'hash':'c'*64}
        managed=members.selection(selection);rows=[{'.name':name,'proto':proto,'auto':'0','disabled':'0','config':'existing'}for name,proto in managed.items()]
        backend=Mock()
        with patch.object(pair,'preflight',return_value=selection),patch.object(pair,'network',return_value=rows),patch.object(pair,'configs',return_value={}),patch.object(pair,'quiet'),patch.object(pair,'set_disabled') as write,patch.object(native,'forward_dispatch') as dispatch:
            state=pair.begin(backend,{}, {'id':'a'*32,'revision':self.revision})
        self.assertEqual(state['interfaces'],managed);self.assertEqual(state['before_flags'],{'wgclient1':'0','ovpnclient2':'0'})
        self.assertEqual(state['owned'],[]);self.assertEqual(pair.read_state()['phase'],'RUNNING')
        write.assert_not_called();dispatch.assert_not_called()
