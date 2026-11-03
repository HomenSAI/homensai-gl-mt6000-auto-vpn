"""MT3000 03.11.2026 (2.1.0-alpha6): the owner changed VPN clients in the GL panel (a new ovpnclient1 with
network.*.auto unset, the stock S95vpn-client boot link back). Auto went HELD with PAIR-EXTERNAL-POLICY-CHANGE,
the owner saved a new pair and pressed Start: PREPARATION-RECOVERY-REQUIRED for good, because preparation
refuses while a session is HELD and the hand-over (pair_auto.release_session) ran only after preparation.

The owner's Start now hands the session over first (same release_session, under the control lock), then
prepares with the reviewed writer (durable before-records, readback) and requests the pair. Real auto_control,
pair_auto and preparation_control on temporary router files; only the router reads are faked."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import configuration_guard
import native_switch as native
import pair_auto as pair
import preparation_control as prep
import preparation_status

OLD_REVISION = 'e'*32


class HeldStartHandover(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.runtime = self.root/'run';self.persist = self.root/'persist'
        for name in ('run', 'persist', 'etc/config', 'etc/init.d', 'etc/rc.d', 'etc/modules.d', 'tmp/sysinfo', 'proc/sys/kernel/random'):
            (self.root/name).mkdir(parents=True, exist_ok=True)
        (self.root/'tmp/sysinfo/board_name').write_text('glinet,mt3000-snand')
        (self.root/'etc/glversion').write_text('4.11.0')
        (self.root/'proc/sys/kernel/random/boot_id').write_text('11111111-1111-1111-1111-111111111111')
        for name in prep.PACKAGES:(self.root/'etc/config'/name).write_text('private fixture '+name+'\n')
        # GL created a new ovpnclient1 (auto unset) and re-enabled the stock boot link; the old pair owned ovpnclient2
        self.values = {'wgclient1':{'proto':'wgclient','auto':'0'}, 'ovpnclient1':{'proto':'ovpnclient','auto':None},
                       'ovpnclient2':{'proto':'ovpnclient','auto':'0'}, 'hnat':'0', 'hnat_type':'mtkhnat',
                       'defaults':[{'section':'cfg0001','flow_offloading':'0','flow_offloading_hw':'0'}]}
        (self.root/'etc/init.d/vpn-client').write_text('never execute this fixture')
        for prefix in ('S95', 'K10'):(self.root/'etc/rc.d'/(prefix+'vpn-client')).symlink_to('../init.d/vpn-client')
        self.settings = {'pair_auto_mode':pair.MODE, 'terms_version':agent.TERMS_VERSION, 'router_model':'auto',
                         'plan_source_tunnel':'wireguard:wgclient1', 'plan_target_tunnel':'openvpn:ovpnclient1'}
        self.journal = {'phase':'ROLLED-BACK', 'tx':'f'*32}
        for module in (agent, auto_control, native, prep):
            for key, value in (('RUNTIME', self.runtime), ('PERSIST', self.persist)):
                if hasattr(module, key):self.use(patch.object(module, key, value))
        self.use(patch.object(prep, 'ROOT', self.root))
        self.use(patch.object(prep, 'inventory', side_effect=lambda:{'settings':dict(self.settings)}))
        self.use(patch.object(prep, 'options', side_effect=lambda:copy.deepcopy(self.values)))
        self.use(patch.object(prep, 'write_uci', side_effect=self.write_uci))
        self.use(patch.object(configuration_guard, 'blocked', return_value=None))
        self.backend = Mock()
        self.backend.policy.side_effect = lambda:{'settings':dict(self.settings), 'sections':{}}
        self.backend.acceleration.return_value = {'loaded':[], 'hnat_runtime':'disabled'}
        self.use(patch.object(native, 'Linux', return_value=self.backend))
        self.use(patch.object(native, 'journal_read', side_effect=lambda:dict(self.journal)))
        self.snapshot = self.use(patch.object(preparation_status, 'snapshot', side_effect=self.fake_snapshot))
        self.use(patch('speed_pause.public', return_value={}))
        self.remember = self.use(patch('boot_resume.remember'))
        self.revision = auto_control.current_revision()
        # the HELD session of the old pair, its Start intent long over
        self.state = dict(id='a'*32, phase='HELD', owned=['wgclient1', 'ovpnclient2'],
                          interfaces={'wgclient1':'wgclient', 'ovpnclient2':'ovpnclient'},
                          before_flags={'wgclient1':'0', 'ovpnclient2':'0'}, network_identity='b'*64, protected={},
                          process_bindings=None, order=['a', 'b'], policy_hash='c'*64, revision=OLD_REVISION,
                          recovery_error='PAIR-EXTERNAL-POLICY-CHANGE', started=1.0)
        pair.save(self.state)
        self.raw_state = pair.paths()[1].read_bytes()
        agent.atomic_json(pair.paths()[0], {'mode':'off', 'revision':OLD_REVISION, 'time':time.time()-600, 'request_source':'manual'})
        agent.atomic_json(self.persist/'native-stop.json', {'requested':time.time()-600, 'trial':None, 'all_trials':True, 'request_source':'manual'})

    def use(self, item):
        value = item.start();self.addCleanup(item.stop);return value

    def write_uci(self, action, plan):
        path = self.root/'etc/config'/plan['before']['package'];path.write_text(path.read_text()+'# reviewed option\n')
        for row in plan['before']['options']:self.values[row['section']]['auto'] = '0'

    def fake_snapshot(self, settings=None):
        links = [p.name for p in (self.root/'etc/rc.d').iterdir() if p.name.startswith('S') and p.name[3:] == 'vpn-client']
        checks = [{'code':'PREP-HNAT-CONFIG', 'state':'pass'},
                  {'code':'PREP-SOURCE-AUTOSTART', 'state':'pass' if self.values['wgclient1']['auto'] == '0' else 'fail'},
                  {'code':'PREP-TARGET-AUTOSTART', 'state':'pass' if self.values['ovpnclient1']['auto'] == '0' else 'fail'},
                  {'code':'PREP-STOCK-VPN-BOOT', 'state':'fail' if links else 'pass'},
                  {'code':'PREP-SFE-BOOT', 'state':'pass'}, {'code':'PREP-SFE-AUTOLOAD', 'state':'pass'}, {'code':'PREP-SFE-RUNTIME', 'state':'pass'}]
        return {'state':'pass' if all(row['state'] == 'pass' for row in checks) else 'incomplete', 'checks':checks}

    def start(self, source='manual', revision=None):
        return auto_control.start(revision or self.revision, request_source=source)

    def records(self):
        directory = self.persist/'preparation-changes'
        return [agent.read_json(path)['data'] for path in directory.glob('*.json')] if directory.exists() else []

    def archives(self):
        return sorted((self.persist/'session-recovery').glob('pair-'+self.state['id']+'-readopt-*.json')) if (self.persist/'session-recovery').exists() else []

    def assert_untouched(self):
        self.assertEqual(pair.paths()[1].read_bytes(), self.raw_state, 'the HELD record stays as it was')
        self.assertEqual(self.records(), [], 'no preparation write')
        self.assertTrue((self.root/'etc/rc.d/S95vpn-client').is_symlink())
        self.assertIsNone(self.values['ovpnclient1']['auto'])
        self.assertNotEqual(pair.intent().get('mode'), 'on', 'nothing started')
        self.assertEqual(self.archives(), [])
        self.remember.assert_not_called()

    # --- the router state of 03.11.2026 -----------------------------------------------------------------------

    def test_preparation_preview_refuses_while_held(self):
        self.assertEqual(prep.preview({'action':'target-autostart'})['code'], 'PREPARATION-RECOVERY-REQUIRED')

    def test_owner_start_hands_over_prepares_and_starts(self):
        reply = self.start()
        self.assertTrue(reply.get('accepted'), reply)
        self.assertEqual(reply['mode'], 'continuous-pair');self.assertNotIn('blockers', reply)
        # 1. the old session was handed over exactly as release_session does
        state = pair.read_state()
        self.assertEqual((state['phase'], state['owned'], state['recovery_error']), ('STOPPED', [], None))
        resolution = state['operator_resolution']
        self.assertEqual(resolution['reason'], 'AUTOMATIC-EXTERNAL-CHANGE-READOPT')
        self.assertEqual(resolution['trigger'], 'PAIR-EXTERNAL-POLICY-CHANGE')
        self.assertEqual(resolution['retired_owned'], ['wgclient1', 'ovpnclient2'])
        self.assertFalse(resolution['old_flags_restored'])
        self.assertEqual(len(self.archives()), 1);self.assertEqual(self.archives()[0].read_bytes(), self.raw_state)
        self.assertEqual(len(agent.read_json(self.runtime/'pair-readopt.json')['events']), 1)
        # 2. preparation: the two restart-free fixes, each with its verified before-record
        rows = {row['action']:row for row in self.records()}
        self.assertEqual(set(rows), {'target-autostart', 'vpn-boot'})
        self.assertTrue(all(row['state'] == 'VERIFIED' and row['restart_required'] is False for row in rows.values()))
        self.assertEqual(rows['target-autostart']['before']['interface'], 'ovpnclient1')
        self.assertEqual(rows['target-autostart']['before']['options'][0]['before'], None)
        self.assertIn('S95vpn-client', [row['name'] for row in rows['vpn-boot']['before']['links']])
        self.assertEqual(self.values['ovpnclient1']['auto'], '0');self.assertEqual(self.values['ovpnclient2']['auto'], '0')
        self.assertFalse((self.root/'etc/rc.d/S95vpn-client').exists())
        self.assertTrue((self.root/'etc/rc.d/K10vpn-client').is_symlink(), 'the kill link is kept')
        self.assertIsNone(prep.auto_blocker())
        # 3. the pair request: an explicit owner Start, remembered for a power cut
        row = pair.intent()
        self.assertEqual((row['mode'], row['revision'], row['request_source']), ('on', self.revision, 'manual'))
        self.remember.assert_called_once_with()
        # a repeated click changes nothing
        again = self.start();self.assertTrue(again['already_requested'])
        self.assertEqual(len(self.archives()), 1);self.assertEqual(len(self.records()), 2)

    # --- negative cases ---------------------------------------------------------------------------------------

    def test_busy_journal_still_refuses_without_any_write(self):
        for phase in ('COMMITTED', 'HELD-ON-RESERVE', 'APPLYING'):
            with self.subTest(phase=phase):
                self.journal = {'phase':phase, 'tx':'f'*32}
                self.assertEqual(self.start()['blockers'], ['TRANSACTION-IN-PROGRESS'])
                self.assert_untouched()

    def test_journal_not_settled_is_never_handed_over(self):
        # defence in depth: release_for_start itself keeps the journal rule of release_session
        for phase in ('COMMITTED', 'RESTORING', 'UNKNOWN-PHASE'):
            with self.subTest(phase=phase):
                self.journal = {'phase':phase}
                self.assertEqual(pair.release_for_start(self.revision, self.settings, time.time()), 'PAIR-RECOVERY-REQUIRED')
                self.assert_untouched()

    def test_stop_during_the_start_preflight_wins(self):
        policy = json.dumps({'settings':{}}).encode()
        def stop_now():
            with patch.object(agent, 'command', return_value=policy):auto_control.stop(request_source='manual')
            return None
        with patch.object(prep, 'auto_blocker', side_effect=stop_now):
            self.assertEqual(self.start()['blockers'], ['CONTROL-REVISION-STALE'])
        self.assert_untouched()
        self.assertEqual(pair.intent()['mode'], 'off')

    def test_stop_during_preparation_wins_after_the_hand_over(self):
        policy = json.dumps({'settings':{}}).encode()
        calls = []
        def snapshot_then_stop(settings=None):
            calls.append(1)
            if len(calls) == 1:
                with patch.object(agent, 'command', return_value=policy):auto_control.stop(request_source='manual')
            return self.fake_snapshot(settings)
        self.snapshot.side_effect = snapshot_then_stop
        reply = self.start()
        self.assertFalse(reply['accepted']);self.assertEqual(reply['blockers'], ['PREPARATION-STALE-REVIEW'])
        self.assertEqual(self.records(), [], 'no preparation write after the Stop')
        self.assertTrue((self.root/'etc/rc.d/S95vpn-client').is_symlink())
        self.assertEqual(pair.intent()['mode'], 'off', 'nothing started')
        self.assertEqual(pair.read_state()['phase'], 'STOPPED', 'the hand-over itself starts nothing')
        self.remember.assert_not_called()

    def test_newer_stop_latch_or_failed_stop_refuse_the_hand_over(self):
        arrived = time.time()
        agent.atomic_json(self.persist/'native-stop.json', {'requested':arrived+1, 'trial':None, 'all_trials':True})
        self.assertEqual(pair.release_for_start(self.revision, self.settings, arrived), 'STOP-SUPERSEDED-START')
        agent.atomic_json(self.persist/'native-stop.json', {'requested':arrived-100, 'trial':None, 'all_trials':True, 'control_revision_failed':True})
        self.assertEqual(pair.release_for_start(self.revision, self.settings, arrived), 'CONTROL-REVISION-STALE')
        self.assertEqual(pair.release_for_start('b'*32, self.settings, arrived), 'CONTROL-REVISION-STALE')
        self.assert_untouched()

    def test_exhausted_readopt_ledger_refuses(self):
        now = time.time()
        agent.atomic_json(self.runtime/'pair-readopt.json', {'events':[now-30, now-20, now-10]})
        self.assertEqual(self.start()['blockers'], ['PAIR-RECOVERY-REQUIRED'])
        self.assert_untouched()

    def test_only_the_owners_start_with_terms_and_a_readopt_code_hands_over(self):
        for source in ('programmatic', 'test', 'unknown'):
            with self.subTest(source=source):
                self.assertEqual(self.start(source)['blockers'], ['PREPARATION-RECOVERY-REQUIRED'])
                self.assert_untouched()
        self.settings['terms_version'] = '1'
        self.assertEqual(self.start()['blockers'], ['PREPARATION-RECOVERY-REQUIRED']);self.assert_untouched()
        self.settings['terms_version'] = agent.TERMS_VERSION
        self.state['recovery_error'] = 'UNSAFE-GUARD-DEVICE';pair.save(self.state);self.raw_state = pair.paths()[1].read_bytes()
        self.assertEqual(self.start()['blockers'], ['PREPARATION-RECOVERY-REQUIRED']);self.assert_untouched()

    def test_an_active_intent_is_never_handed_over(self):
        agent.atomic_json(pair.paths()[0], {'mode':'on', 'revision':OLD_REVISION, 'time':time.time()-60, 'id':'d'*32, 'request_source':'manual'})
        self.assertIsNone(pair.release_for_start(self.revision, self.settings, time.time()))
        self.assertEqual(pair.paths()[1].read_bytes(), self.raw_state);self.assertEqual(self.archives(), [])

    def test_preparation_record_integrity_is_checked_before_the_hand_over(self):
        directory = self.persist/'preparation-changes';directory.mkdir()
        (directory/('0'*32+'.json')).write_text('{"data":{"state":"PREPARED"},"sha256":"x"}')
        self.assertEqual(self.start()['blockers'], ['PREPARATION-RECOVERY-REQUIRED'])
        self.assertEqual(pair.paths()[1].read_bytes(), self.raw_state);self.assertEqual(self.archives(), [])


if __name__ == '__main__':unittest.main()
