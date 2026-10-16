from contextlib import nullcontext
from pathlib import Path
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import fault_control as fault
import recovery_settings as recovery
from test_native_switch import fixture
import native_switch as native

class FaultTests(unittest.TestCase):
    def args(self):return {'profile':'a','scope':'profile','duration':60}
    def eligibility(self,args=None,mutation=None):
        row=lambda identifier,channel:{'id':identifier,'interface':'wg'+identifier,'channel':channel,'code':None,'dns_ok':True,'https_success':2,'time':995}
        status={'time':995,'profiles':[row('a','Main'),row('b','Reserve')]};state={'state':'OBSERVING','certified':True,'time':995};settings={'native_session_loss':'1','native_until':'2000'};selection={'source':{'id':'a'},'target':{'id':'b'}}
        if mutation:mutation(status,state,settings,selection)
        return fault.eligibility(args or self.args(),{},status,state,settings,selection,[],1000)
    def test_only_certified_fresh_current_source_with_healthy_reserve(self):
        self.assertEqual(self.eligibility()[0]['id'],'a')
        mutations=[lambda s,n,c,p:n.update(certified=False),lambda s,n,c,p:n.update(state='COMMITTED'),lambda s,n,c,p:s.update(time=1),lambda s,n,c,p:c.update(native_session_loss='0'),lambda s,n,c,p:c.update(native_until='1050'),lambda s,n,c,p:s['profiles'][1].update(code='VPN-003'),lambda s,n,c,p:p['source'].update(id='b')]
        for mutation in mutations:
            with self.assertRaises(fault.FaultError):self.eligibility(mutation=mutation)
    def test_channel_fault_cannot_remove_the_reserve(self):
        with self.assertRaisesRegex(fault.FaultError,'REMOVE-RESERVE'):
            self.eligibility(dict(self.args(),scope='channel'),lambda s,n,c,p:s['profiles'][1].update(channel='Main'))
    def test_bad_scope_duration_or_extra_fields_rejected(self):
        for changes in ({'duration':181},{'duration':True},{'duration':10},{'scope':'wan'},{'extra':1}):
            with self.assertRaises(fault.FaultError):self.eligibility(dict(self.args(),**changes))
    def test_kernel_timeout_present_on_every_drop_scope_and_no_input_chain(self):
        value=fault.script(['wg0','tun0'],60,'a'*32)
        self.assertNotIn('set devices',value);self.assertIn('set fault_devs',value)
        self.assertIn('flags timeout',value);self.assertIn('"wg0" timeout 60s',value);self.assertIn('"tun0" timeout 60s',value)
        self.assertNotIn('hook input',value);self.assertIn('iifname "br-lan"',value);self.assertIn('meta nfproto ipv4',value)
    def test_unsafe_device_never_enters_nft_script(self):
        for devices in ([],['wg0;flush ruleset'],['wg0\n'],['x'*16]):
            with self.assertRaises(fault.FaultError):fault.script(devices,60,'a'*32)
    def test_foreign_table_never_deleted(self):
        with patch.object(fault.Nft,'contents',return_value='foreign'),patch.object(fault.subprocess,'run') as run:
            with self.assertRaisesRegex(fault.FaultError,'FOREIGN'):fault.Nft().cleanup('a'*32)
        run.assert_not_called()
    def test_nft_timeout_preflight_failure_never_applies_unbounded_fallback(self):
        with tempfile.TemporaryDirectory() as d,patch.object(fault,'RUNTIME',Path(d)),patch.object(fault.Nft,'contents',return_value=None),patch.object(fault.subprocess,'run',return_value=MagicMock(returncode=1)) as run:
            with self.assertRaisesRegex(fault.FaultError,'TIMEOUT-RULE'):fault.Nft().apply(['wg0'],60,'a'*32)
            self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[0][1],'-c')
    def test_watchdog_cleans_owned_table_even_without_parent(self):
        value={'nonce':'a'*32,'monotonic_until':1}
        with patch.object(fault,'load',return_value=value),patch.object(fault,'control_lock',return_value=nullcontext()),patch.object(fault,'atomic_json') as write,patch.object(fault,'Nft') as engine:
            fault.worker('a'*32)
        engine.return_value.cleanup.assert_called_once_with('a'*32);self.assertTrue(write.call_args.args[1]['cleaned'])
    def test_public_status_excludes_watchdog_nonce_and_devices(self):
        value={'nonce':'a'*32,'phase':'ACTIVE','monotonic_until':time.monotonic()+20,'until':time.time()+20,'profiles':['a'],'devices':['wg0'],'scope':'profile'}
        with patch.object(fault,'load',return_value=value),patch.object(fault,'read_json',return_value={}):result=fault.public_status()
        self.assertNotIn('nonce',result);self.assertNotIn('devices',result)
    def test_corrupt_intent_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as d,patch.object(fault,'RUNTIME',Path(d)):
            (Path(d)/'fault-intent.json').write_text(json.dumps({'data':{'nonce':'a'*32},'sha256':'incorrect'}))
            with self.assertRaises(fault.FaultError):fault.load()

class RecoveryObservationTests(unittest.TestCase):
    def samples(self):return [{'id':'a','time':1000-i*20,'code':None,'dns_ok':True,'https_success':2} for i in range(5)]
    def test_return_needs_success_count_and_stable_span(self):
        self.assertTrue(recovery.stable_success(self.samples(),'a',3,60,1000))
        self.assertFalse(recovery.stable_success(self.samples()[:3],'a',3,60,1000))
    def test_failure_gap_stale_future_and_duplicate_do_not_make_stable_return(self):
        points=self.samples();points[1]['code']='DNS-001';self.assertFalse(recovery.stable_success(points,'a',3,60,1000))
        self.assertFalse(recovery.stable_success(self.samples(),'a',3,60,2000))
        self.assertFalse(recovery.stable_success(self.samples()*3,'a',10,60,1000))
    def test_general_policy_allows_third_connected_generic_without_moving_special_rules(self):
        data,profiles=fixture();profiles.append({'id':'openvpn:3_3','interface':'ovpnclient3'});data['sections'].append({'.name':'c','.type':'rule','enabled':'1','killswitch':'1','via':'ovpnclient3'});data['settings']['plan_target']='openvpn:3_3'
        result=native.choose(data,profiles);self.assertEqual(result['target_rule'],'c');self.assertEqual(result['order'][:3],['global','default','special'])
