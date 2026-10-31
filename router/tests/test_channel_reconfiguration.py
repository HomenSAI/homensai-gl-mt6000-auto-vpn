"""Channel removal/rebinding must preserve live probes and recoverable ownership."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import native_switch as native
import pair_auto as pair


class ReconfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.runtime = self.root/'run'; self.persist = self.root/'persist'
        self.runtime.mkdir(); self.persist.mkdir()
        for module in (agent, auto_control, native):
            for name, value in (('RUNTIME', self.runtime), ('PERSIST', self.persist)):
                p = patch.object(module, name, value); p.start(); self.addCleanup(p.stop)
        self.revision = auto_control.current_revision()
        self.state = dict(id='a'*32, phase='RUNNING', owned=['wgclient1'],
                          before_flags={'wgclient1':'1','ovpnclient1':'0'}, network_identity='b'*64,
                          protected={}, process_bindings=None, order=['old'], policy_hash='c'*64,
                          revision=self.revision)

    def test_four_to_two_disabled_and_deleted_channels_do_not_spend_probe_budget(self):
        rows = [dict(id='old', interface='ovpnclient1', administrative_state='disabled'),
                dict(id='deleted', interface=None),
                dict(id='ovpn', interface='ovpnclient2', administrative_state='enabled'),
                dict(id='wg', interface='wgclient1', administrative_state='enabled')]
        self.assertEqual([p['id'] for p in agent.probe_profiles(rows, {'probe_limit':2})], ['ovpn','wg'])
        self.assertEqual(len(rows), 4, 'catalogue is retained separately from live probes')

    def test_selected_tunnels_get_slots_before_unrelated_channels(self):
        rows = [dict(id='extra', interface='extra', administrative_state='enabled'),
                dict(id='unknown', interface='unknown'),
                dict(id='replacement', interface='wgclient1', vendor_tunnel_id='wireguard:wgclient1', administrative_state='enabled')]
        settings={'probe_limit':1, 'plan_source':'former-id', 'plan_source_tunnel':'wireguard:wgclient1'}
        self.assertEqual(agent.probe_profiles(rows,settings)[0]['id'],'replacement')
        self.assertEqual(agent.probe_profiles(rows,{'probe_limit':1})[0]['id'],'extra')

    def test_restart_conflict_keeps_ownership_cancels_intent_and_publishes_a_fresh_error(self):
        pair.request(self.revision); pair.save(self.state)
        budget=self.persist/'pair-auto-budget.json'; budget.write_text('{"events":[1]}')
        backend=Mock(); backend.order.return_value=(['current'], 'd'*64)
        with patch.object(native,'journal_read',return_value={'phase':'ROLLED-BACK'}), patch.object(native,'publish') as publish, patch.object(native,'command') as command:
            self.assertFalse(pair.recover(backend))
        self.assertIsNone(pair.public_intent())
        self.assertEqual(pair.public_phase(),'HELD')
        saved=pair.read_state(); self.assertEqual(saved['owned'],self.state['owned'])
        self.assertEqual(saved['recovery_error'],'PAIR-EXTERNAL-POLICY-CHANGE')
        self.assertEqual(publish.call_args.args[0]['blockers'],['PAIR-EXTERNAL-POLICY-CHANGE'])
        self.assertFalse(publish.call_args.args[0]['original_restored'])
        self.assertEqual(budget.read_text(),'{"events":[1]}')
        command.assert_not_called(); backend.unguard.assert_not_called()

    def test_corrupt_ownership_does_not_crash_recovery_or_tick_and_is_never_rewritten(self):
        path=pair.paths()[1]; path.write_text('{broken')
        with patch.object(native,'publish') as publish:
            self.assertFalse(pair.recover(Mock()))
            self.assertTrue(pair.tick(Mock(),{},self.revision))
        self.assertEqual(path.read_text(),'{broken')
        self.assertEqual(publish.call_count,2)

    def test_valid_checksum_with_invalid_phase_cannot_crash_status_or_start(self):
        for phase in ([], {}, None, True):
            state=dict(self.state,phase=phase);pair.save(state)
            with self.assertRaisesRegex(ValueError,'PAIR-STATE-UNVERIFIED'):pair.read_state()
            self.assertEqual(pair.public_phase(),'UNKNOWN')
            self.assertFalse(pair.request(self.revision)['accepted'])
            self.assertEqual(auto_control.public_status()['pair_phase'],'UNKNOWN')

    def test_network_change_during_recovery_is_visible_without_ifdown(self):
        pair.save(self.state); backend=Mock(); backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}), patch.object(pair,'network',return_value=[]), patch.object(native,'publish') as publish, patch.object(native,'command') as command:
            self.assertFalse(pair.recover(backend))
        self.assertEqual(publish.call_args.args[0]['blockers'],['PAIR-EXTERNAL-NETWORK-CHANGE'])
        command.assert_not_called()

    def test_continuous_pair_does_not_parse_a_legacy_expired_or_malformed_trial_window(self):
        with ExitStack() as stack:
            for name,value in {'JOURNAL':self.persist/'journal','STATE':self.runtime/'native-status.json','CERT':self.persist/'cert','ATTEMPTS':self.persist/'attempts','PREPARE':self.persist/'prepare','STOP':False}.items():
                stack.enter_context(patch.object(native,name,value))
            backend=Mock(); backend.policy.return_value={'settings':{'pair_auto_mode':pair.MODE,'native_until':'not-a-date'}}
            stack.enter_context(patch.object(native,'Linux',return_value=backend))
            stack.enter_context(patch.object(native,'journal_read',return_value={}))
            stack.enter_context(patch('manual_dispatch.recover_pending'))
            stack.enter_context(patch.object(pair,'recover',return_value=True))
            def tick(*args):native.STOP=True; return True
            tick_mock=stack.enter_context(patch.object(pair,'tick',side_effect=tick))
            deadline=stack.enter_context(patch.object(native,'deadline',side_effect=AssertionError('Legacy window parsed before continuous pair')))
            stack.enter_context(patch.object(native.time,'sleep'))
            native.serve()
            tick_mock.assert_called_once(); deadline.assert_not_called()

    def test_preparation_reports_the_exact_failed_check_before_starting_any_profiles(self):
        import preparation_status
        settings={'pair_auto_mode':pair.MODE,'terms_version':__import__('agent').TERMS_VERSION,'native_session_loss':'1'}
        for code in ('PREP-HNAT-CONFIG','PREP-SFE-AUTOLOAD','PREP-WGCLIENT1-AUTOSTART'):
            def read(path, **kwargs):return 'glinet,mt3000-snand' if path.name=='board_name' else '4.11.0'
            with patch.object(Path,'read_text',read), patch.object(preparation_status,'snapshot',return_value={'state':'incomplete','checks':[{'code':code,'state':'fail'}]}), patch.object(native,'command') as command:
                with self.assertRaisesRegex(ValueError,code):pair.preflight(Mock(),settings)
                command.assert_not_called()

    def test_supervisor_startup_and_shutdown_publish_conflict_instead_of_exiting_with_exception(self):
        pair.save(self.state)
        with ExitStack() as stack:
            for name,value in {'JOURNAL':self.persist/'journal','STATE':self.runtime/'native-status.json','CERT':self.persist/'cert','ATTEMPTS':self.persist/'attempts','PREPARE':self.persist/'prepare','STOP':False}.items():
                stack.enter_context(patch.object(native,name,value))
            backend=Mock(); backend.order.return_value=(['current'],'d'*64)
            stack.enter_context(patch.object(native,'Linux',return_value=backend))
            stack.enter_context(patch.object(native,'journal_read',return_value={}))
            stack.enter_context(patch('manual_dispatch.recover_pending'))
            seen=[]
            def publish(value):seen.append(value); native.STOP=True
            stack.enter_context(patch.object(native,'publish',side_effect=publish))
            command=stack.enter_context(patch.object(native,'command'))
            native.serve()
            self.assertEqual(len(seen),2,'startup and shutdown both retain a visible failure')
            self.assertTrue(all(row['blockers']==['PAIR-EXTERNAL-POLICY-CHANGE'] for row in seen))
            command.assert_not_called(); backend.unguard.assert_not_called()


if __name__=='__main__':unittest.main()
