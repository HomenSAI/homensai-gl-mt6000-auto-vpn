import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import native_switch as native
import native_proof
import pair_auto as pair


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.runtime=root/'run';self.persist=root/'persist'
        self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,auto_control,native):
            for name,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,name):
                    p=patch.object(module,name,value);p.start();self.addCleanup(p.stop)
        self.revision=auto_control.current_revision()
        self.state=dict(id='a'*32,phase='RUNNING',owned=['wgclient1'],
            before_flags={'wgclient1':'1','ovpnclient1':'0'},network_identity='b'*64,
            protected={},process_bindings=None,order=['a','b'],policy_hash='c'*64,revision=self.revision)

    def test_pair_start_source_is_preserved_and_duplicate_cannot_relabel(self):
        self.assertTrue(pair.request(self.revision,request_source='test')['accepted'])
        self.assertEqual(pair.intent()['request_source'],'test')
        self.assertTrue(pair.request(self.revision,request_source='manual')['already_requested'])
        self.assertEqual(pair.intent()['request_source'],'test')
        self.assertEqual(auto_control.public_status()['activation_source'],'test')

    def test_retry_budget_is_rolling_and_survives_a_new_session(self):
        events=[100,200,300]
        kept,allowed=pair.budget(events,400)
        self.assertEqual(kept,events);self.assertFalse(allowed)
        self.assertEqual(pair.budget(events,1000),([200,300],True))
        for bad in ([401],[True],[float('nan')],None,[-1]):
            with self.assertRaises(ValueError):pair.budget(bad,400)

    def test_duplicate_start_is_idempotent_and_stop_revision_fences_it(self):
        first=pair.request(self.revision);saved=pair.intent()
        second=pair.request(self.revision)
        self.assertTrue(first['accepted']);self.assertTrue(second['already_requested'])
        self.assertEqual(pair.intent(),saved)
        new=auto_control.current_revision(rotate=True)
        self.assertFalse(pair.request(self.revision)['accepted'])
        with auto_control.control_lock():pair.stop_locked(new)
        self.assertIsNone(pair.public_intent())

    def test_display_phase_covers_queue_start_cleanup_and_terminal_failure(self):
        self.assertIsNone(pair.public_phase())
        pair.request(self.revision)
        self.assertEqual(pair.public_phase(),'STARTING')
        self.state.update(id=pair.intent()['id'],phase='STARTING')
        pair.save(self.state)
        self.assertEqual(pair.public_phase(),'STARTING')
        self.state['phase']='RUNNING';pair.save(self.state)
        self.assertEqual(pair.public_phase(),'RUNNING')
        with auto_control.control_lock():pair.stop_locked(self.revision)
        self.assertEqual(pair.public_phase(),'STOPPING')
        self.state['phase']='STOPPED';pair.save(self.state)
        self.assertEqual(pair.public_phase(),'STOPPED')
        pair.request(self.revision)
        self.assertEqual(pair.public_phase(),'STARTING')
        self.state.update(id=pair.intent()['id'],phase='FAILED');pair.save(self.state)
        self.assertEqual(pair.public_phase(),'FAILED')

    def test_unrecovered_owned_profiles_refuse_new_start(self):
        pair.save(self.state)
        self.assertIn('PAIR-RECOVERY-REQUIRED',pair.request(self.revision)['blockers'])

    def test_failed_start_stop_status_keeps_latest_request_timestamp(self):
        pair.request(self.revision)
        started=auto_control.public_status()
        self.assertEqual(started['requested'],'on')
        self.state.update(id=pair.intent()['id'],phase='STOPPED');pair.save(self.state)
        with auto_control.control_lock():pair.stop_locked(self.revision)
        stopped=auto_control.public_status()
        self.assertEqual(stopped['requested'],'off')
        self.assertEqual(stopped['pair_phase'],'STOPPED')
        self.assertGreaterEqual(stopped['requested_at'],started['requested_at'])
        self.assertEqual(stopped['requested_at'],pair.intent()['time'])

    def test_corrupt_state_never_becomes_fresh_start(self):
        pair.paths()[1].write_text('{"data":{},"sha256":"wrong"}')
        self.assertFalse(pair.request(self.revision)['accepted'])
        self.assertEqual(pair.paths()[1].read_text(),'{"data":{},"sha256":"wrong"}')

    def test_nested_invalid_ownership_refuses_even_with_valid_checksum(self):
        state=copy.deepcopy(self.state);state['owned']=[{}]
        pair.save(state)
        with self.assertRaisesRegex(ValueError,'PAIR-STATE-UNVERIFIED'):pair.read_state()

    def test_profile_identity_ignores_only_owned_disabled_flags(self):
        rows=[{'.name':'wgclient1','disabled':'1','config':'peer_1'},{'.name':'lan','ipaddr':'192.0.2.1'}]
        changed=copy.deepcopy(rows);changed[0]['disabled']='0'
        self.assertEqual(pair.normalized_network(rows),pair.normalized_network(changed))
        changed[0]['config']='peer_2'
        self.assertNotEqual(pair.normalized_network(rows),pair.normalized_network(changed))
        changed=copy.deepcopy(rows);changed[1]['ipaddr']='192.0.2.2'
        self.assertNotEqual(pair.normalized_network(rows),pair.normalized_network(changed))

    def test_external_policy_is_never_overwritten_by_stop(self):
        backend=Mock();backend.order.return_value=(['external','b'],'c'*64)
        with patch.object(native,'journal_read',return_value={}),patch.object(native,'command')as command:
            with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-POLICY-CHANGE'):pair.cleanup(backend,self.state)
            command.assert_not_called();backend.unguard.assert_not_called()

    def test_stop_on_unhealthy_primary_holds_reserve_and_never_stops_profiles(self):
        backend=Mock()
        with patch.object(native,'journal_read',return_value={'phase':'COMMITTED'}),patch.object(native,'finish_committed',return_value=False),patch.object(native,'command')as command:
            self.assertFalse(pair.cleanup(backend,self.state))
            self.assertEqual(pair.read_state()['phase'],'HELD')
            command.assert_not_called()

    def test_external_network_change_never_dispatches_ifdown(self):
        backend=Mock();backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[{'.name':'external'}]),patch.object(native,'command')as command:
            with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-NETWORK-CHANGE'):pair.cleanup(backend,self.state)
            command.assert_not_called()

    def test_restart_never_resumes_previous_intent(self):
        pair.request(self.revision);pair.save(self.state)
        with patch.object(pair,'cleanup')as cleanup:
            pair.recover(Mock())
        cleanup.assert_called_once();self.assertIsNone(pair.public_intent())

    def test_router_proof_never_matches_hosted_or_external(self):
        proof={'proof_scope':native_proof.ROUTER}
        for other in ({},{'proof_scope':native_proof.HOSTED}):
            self.assertFalse(native_proof.matches(proof,other))
            self.assertFalse(native_proof.matches(other,proof))
        with self.assertRaises(ValueError):native_proof.requested({'native_proof_scope':native_proof.ROUTER})
        self.assertEqual(native_proof.requested({'native_proof_scope':native_proof.ROUTER,'pair_auto_mode':pair.MODE}),pair.MODE)

    def test_observer_does_not_consume_an_attempt_or_claim_lan_certificate(self):
        self.state['id']=pair.request(self.revision)and pair.intent()['id'];pair.save(self.state)
        selection={'source':{'id':'a'},'target':{'id':'b'},'vendor_identity':'d'*64}
        backend=Mock();backend.diagnostic.return_value=([],selection)
        backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch('failover_plan.streak',return_value=False),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),patch.object(native,'publish')as publish,patch.object(native,'attempt')as attempt:
            self.assertTrue(pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision))
        attempt.assert_not_called();status=publish.call_args.args[0]
        self.assertEqual(status['state'],'OBSERVING');self.assertFalse(status['certified'])
        self.assertFalse(status['external_lan_verified']);self.assertTrue(status['readiness_verified'])
        self.assertFalse((self.persist/'pair-auto-budget.json').exists())

    def test_profile_ownership_is_durable_before_each_activation(self):
        request={'id':'a'*32,'revision':self.revision}
        selection={'source':{'interface':'wgclient1'},'target':{'interface':'ovpnclient1'},
                   'process_bindings':None,'order':['a','b'],'hash':'c'*64}
        rows=[{'.name':k,'proto':v,'auto':'0','disabled':'1','config':'selected'}for k,v in pair.INTERFACES.items()]
        changed=[]
        def write(state,interface,value,revision):
            durable=pair.read_state()
            self.assertIn(interface,durable['owned']);self.assertEqual(durable['phase'],'STARTING')
            self.assertEqual(value,'0');changed.append(interface)
        backend=Mock();backend.devices.return_value=['wgclient1','ovpnclient1']
        with patch.object(pair,'preflight',return_value=selection),patch.object(pair,'network',return_value=rows),patch.object(pair,'configs',return_value={}),patch.object(pair,'quiet'),patch.object(pair,'set_disabled',side_effect=write),patch.object(native,'forward_dispatch')as dispatch:
            state=pair.begin(backend,{},request)
        self.assertEqual(changed,['wgclient1','ovpnclient1']);self.assertEqual(state['phase'],'RUNNING')
        self.assertEqual(dispatch.call_count,2)
        self.assertEqual([call.args[0] for call in dispatch.call_args_list],
                         [['ifup','-w','wgclient1'],['ifup','-w','ovpnclient1']])

    def test_stop_between_profile_starts_prevents_second_activation(self):
        request={'id':'a'*32,'revision':self.revision}
        selection={'source':{'interface':'wgclient1'},'target':{'interface':'ovpnclient1'},
                   'process_bindings':None,'order':['a','b'],'hash':'c'*64}
        rows=[{'.name':k,'proto':v,'auto':'0','disabled':'1','config':'selected'}for k,v in pair.INTERFACES.items()]
        backend=Mock()
        with patch.object(pair,'preflight',return_value=selection),patch.object(pair,'network',return_value=rows),patch.object(pair,'configs',return_value={}),patch.object(pair,'quiet'),patch.object(pair,'set_disabled')as write,patch.object(native,'forward_dispatch',side_effect=lambda *a,**k:auto_control.current_revision(rotate=True)):
            with self.assertRaisesRegex(native.Refused,'CLIENT-STOP'):pair.begin(backend,{},request)
        self.assertEqual(write.call_count,1);self.assertEqual(pair.read_state()['owned'],['wgclient1'])

    def test_attempt_limit_recovers_with_time_without_reset_or_new_start(self):
        request=pair.request(self.revision);self.state['id']=pair.intent()['id'];pair.save(self.state)
        selection={'source':{'id':'a'},'target':{'id':'b'},'vendor_identity':'d'*64}
        backend=Mock();backend.diagnostic.return_value=([],selection)
        backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch('failover_plan.streak',return_value=True),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),patch.object(native,'publish'),patch.object(native,'attempt')as attempt,patch.object(pair,'configure_lease',return_value=20000):
            for stamp in (10000,10300,10600,10900,10901):
                with patch.object(pair.time,'time',return_value=stamp):pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision)
        # At the exact window boundary the oldest attempt expires. A new
        # Start does not grant a fresh budget; minimum dwell still applies.
        self.assertEqual(attempt.call_count,4)
        ledger=json.loads((self.persist/'pair-auto-budget.json').read_text())
        self.assertEqual(ledger['events'],[10300,10600,10900])

    def test_daemon_cli_and_imported_helpers_share_refused_and_stop(self):
        import subprocess
        root=Path(pair.__file__).parent
        code="""import sys,types,pathlib
sys.path.insert(0,sys.argv[1]);path=pathlib.Path(sys.argv[1])/'native_switch.py'
module=types.ModuleType('__main__');module.__file__=str(path);sys.modules['__main__']=module
sys.argv=[str(path),'invalid']
try:exec(compile(path.read_text(),str(path),'exec'),module.__dict__)
except SystemExit:pass
import native_switch,pair_auto
assert native_switch is module
module.STOP=True
try:pair_auto.require_running('invalid')
except module.Refused:pass
else:raise AssertionError('CLI/helper exceptions diverged')
"""
        result=subprocess.run([sys.executable,'-c',code,str(root)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
