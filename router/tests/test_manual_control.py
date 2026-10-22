"""Operator queue regression checks. All storage and diagnostics are in memory."""
from contextlib import nullcontext
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import manual_control as manual
import native_switch as native


class ManualControlTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000.0
        self.revision = 'a'*32
        self.settings = {'monitor_only': '0', 'native_enabled': '0',
            'native_until': '1200', 'native_trial': 'trial', 'native_session_loss': '1',
            'plan_source': 'openvpn:1_1', 'plan_target': 'wireguard:peer_2'}
        self.selection = {'hash': 'b'*64, 'settings_hash': 'c'*64,
            'vendor_identity': 'd'*64, 'source': {'id': 'openvpn:1_1'},
            'target': {'id': 'wireguard:peer_2'}, 'direction': 'first'}
        self.certificate = {'hash': 'b'*64, 'settings_hash': 'c'*64,
            'vendor_identity': 'd'*64, 'source': 'openvpn:1_1',
            'target': 'wireguard:peer_2', 'direction': 'first', 'until': 1200}
        self.journal = {}
        self.data = {'native-status.json': {'time': self.now},
            'native-certificate.json': self.certificate,
            'native-attempts.json': {'trial': 'trial', 'count': 1},
            'native-stop.json': {}, 'auto-control.json': {}}
        self.writes = []
        self.backend = MagicMock()
        self.backend.policy.side_effect = lambda: copy.deepcopy({'settings': self.settings})
        self.backend.diagnostic.side_effect = lambda: ([], copy.deepcopy(self.selection))
        def read(path, default=None):
            return copy.deepcopy(self.data.get(path.name, default))
        def write(path, value):
            self.writes.append(path.name)
            self.data[path.name] = copy.deepcopy(value)
        def revision(directory, rotate=False):
            if rotate:
                self.revision = ('e' if self.revision != 'e'*32 else 'f')*32
            return self.revision
        for patcher in (patch.object(agent, 'read_json', side_effect=read),
                        patch.object(agent, 'atomic_json', side_effect=write),
                        patch.object(auto_control, 'control_lock', side_effect=lambda *a: nullcontext()),
                        patch.object(auto_control, 'revision_locked', side_effect=revision),
                        patch.object(auto_control, 'current_revision', side_effect=lambda: self.revision),
                        patch.object(native, 'Linux', return_value=self.backend),
                        patch.object(native, 'journal_read', side_effect=lambda: copy.deepcopy(self.journal)),
                        patch.object(manual.time, 'time', side_effect=lambda: self.now)):
            patcher.start(); self.addCleanup(patcher.stop)

    def queue(self, direction='reserve'):
        return manual.request(direction, self.revision)

    def queued(self):
        answer = self.queue()
        self.assertIs(answer['accepted'], True)
        self.assertIs(answer['completed'], False)
        return self.data['manual-control.json']

    def test_queue_never_enables_auto_or_reports_completion(self):
        old_revision = self.revision
        answer = self.queue()
        self.assertEqual(self.writes, ['manual-control.json'])
        self.assertEqual(self.data['auto-control.json'], {})
        self.assertEqual(self.settings['native_enabled'], '0')
        self.assertEqual(self.settings['monitor_only'], '0')
        self.assertNotEqual(old_revision, answer['control_revision'])
        self.assertEqual(answer['control_revision'], self.revision)
        self.assertTrue(manual.valid_record(self.data['manual-control.json']))
        self.assertEqual(manual.public_status()['state'], 'QUEUED')
        self.assertIs(manual.public_status()['completed'], False)
        self.assertEqual(manual.request('reserve', old_revision)['blockers'], ['CONTROL-REVISION-STALE'])

    def test_invalid_rpc_fields_refuse_without_diagnostics(self):
        for direction, revision in [('other', 'a'*32), (True, 'a'*32),
                                    ([], 'a'*32), ('reserve', ''), ('primary', 'A'*32)]:
            self.assertFalse(manual.request(direction, revision)['accepted'])
        self.backend.policy.assert_not_called()
        self.assertEqual(self.writes, [])

    def test_monitor_only_and_platform_blockers_are_preserved(self):
        self.settings['monitor_only'] = '1'
        self.backend.diagnostic.side_effect = lambda: (['UNSUPPORTED-BOARD'], self.selection)
        answer = self.queue()
        self.assertEqual(answer['blockers'], ['MONITOR-ONLY-DEPLOYMENT', 'UNSUPPORTED-BOARD'])
        self.assertEqual(self.writes, [])

    def test_missing_stale_future_supervisor_cannot_queue(self):
        for state in ({}, {'time': 900}, {'time': 1001}, {'time': True}):
            self.data['native-status.json'] = state
            self.assertIn('MANUAL-SUPERVISOR-UNAVAILABLE', self.queue()['blockers'])
        self.assertEqual(self.writes, [])

    def test_auto_on_requires_explicit_stop_first(self):
        self.settings['native_enabled'] = '1'
        self.assertIn('MANUAL-STOP-AUTO-FIRST', self.queue()['blockers'])
        self.assertEqual(self.writes, [])

    def test_certificate_identity_and_attempt_limit_are_not_bypassed(self):
        for field in ('hash', 'settings_hash', 'vendor_identity', 'source', 'target', 'direction'):
            old = self.certificate[field]
            self.certificate[field] = 'changed'
            self.assertIn('LAN-TRIAL-REQUIRED', self.queue()['blockers'])
            self.certificate[field] = old
        self.data['native-attempts.json']['count'] = 3
        self.assertIn('TRIAL-ATTEMPT-LIMIT', self.queue()['blockers'])
        self.assertEqual(self.writes, [])

    def test_active_transaction_never_gets_new_forward_request(self):
        for phase in ('ARMED', 'APPLYING', 'WAIT-CLIENT', 'COMMITTED', 'HELD-ON-RESERVE', 'RELEASE-PENDING'):
            self.journal = {'phase': phase}
            self.assertIn('TRANSACTION-IN-PROGRESS', self.queue()['blockers'])
        self.assertEqual(self.writes, [])

    def test_stop_during_slow_preflight_fences_request(self):
        def diagnostic():
            self.revision = 'f'*32
            return [], self.selection
        self.backend.diagnostic.side_effect = diagnostic
        self.assertEqual(self.queue()['blockers'], ['CONTROL-REVISION-STALE'])
        self.assertEqual(self.writes, [])

    def test_policy_change_before_queue_is_refused(self):
        self.backend.policy.side_effect = [{'settings': self.settings}, {'settings': {}}]
        self.assertEqual(self.queue()['blockers'], ['MANUAL-CONFIG-CHANGED'])
        self.assertEqual(self.writes, [])

    def test_pending_request_is_not_replaced(self):
        record = copy.deepcopy(self.queued())
        self.assertEqual(self.queue()['blockers'], ['MANUAL-REQUEST-PENDING'])
        self.assertEqual(self.data['manual-control.json'], record)

    def test_claim_is_one_shot_before_any_attempt(self):
        record = self.queued()
        claimed, reason = manual.claim_pending(self.settings, self.revision, {}, self.now)
        self.assertIsNone(reason)
        self.assertEqual(claimed['request_id'], record['request_id'])
        self.assertEqual(self.data['manual-control.json']['state'], 'CLAIMED')
        self.assertEqual(manual.claim_pending(self.settings, self.revision, {}, self.now),
                         (None, 'MANUAL-ALREADY-CLAIMED'))
        self.assertEqual(self.data['auto-control.json'], {})

    def test_stop_after_queue_cancels_without_claim(self):
        self.queued()
        self.revision = 'f'*32
        claimed, reason = manual.claim_pending(self.settings, self.revision, {}, self.now)
        self.assertIsNone(claimed)
        self.assertEqual(reason, 'CONTROL-REVISION-STALE')
        self.assertEqual(self.data['manual-control.json']['state'], 'CANCELLED')

    def test_stop_allows_new_explicit_request_after_claimed_process_was_lost(self):
        old = self.queued()
        manual.claim_pending(self.settings, self.revision, {}, self.now)
        self.revision = 'f'*32
        self.assertTrue(manual.control_status()['reserve']['allowed'])
        answer = self.queue()
        self.assertTrue(answer['accepted'])
        self.assertNotEqual(answer['request_id'], old['request_id'])
        self.assertFalse(manual.publish_result(old['request_id'], 'REFUSED', code='LOST-PROCESS'))

    def test_stopped_claimed_record_is_cancelled_not_replayed(self):
        self.queued()
        manual.claim_pending(self.settings, self.revision, {}, self.now)
        self.revision = 'f'*32
        self.assertEqual(manual.claim_pending(self.settings, self.revision, {}, self.now),
                         (None, 'CONTROL-REVISION-STALE'))
        self.assertEqual(self.data['manual-control.json']['state'], 'CANCELLED')

    def test_malformed_auto_state_is_not_treated_as_off(self):
        self.data['auto-control.json'] = {'mode': 'unknown'}
        self.assertIn('MANUAL-STATE-UNVERIFIED', self.queue()['blockers'])
        self.assertEqual(self.writes, [])

    def test_newer_stop_and_expiry_and_changed_pair_refuse_claim(self):
        record = self.queued()
        self.assertEqual(manual.claim_reason(record, self.settings, self.revision,
                         {'requested': self.now, 'all_trials': True}, self.now), 'STOP-SUPERSEDED-MANUAL')
        self.assertEqual(manual.claim_reason(record, self.settings, self.revision, {}, self.now+61),
                         'MANUAL-REQUEST-EXPIRED')
        settings = dict(self.settings, plan_target='removed')
        self.assertEqual(manual.claim_reason(record, settings, self.revision, {}, self.now),
                         'MANUAL-CONFIG-CHANGED')
        settings = dict(self.settings, native_until='999')
        self.assertEqual(manual.claim_reason(record, settings, self.revision, {}, self.now),
                         'BOUNDED-DEADLINE-REQUIRED')

    def test_primary_names_existing_transaction_without_enabling_auto(self):
        self.journal = {'phase': 'HELD-ON-RESERVE', 'tx': '7'*32,
                        'source': self.settings['plan_source'], 'target': self.settings['plan_target']}
        answer = self.queue('primary')
        self.assertTrue(answer['accepted'])
        self.assertEqual(self.data['manual-control.json']['transaction_id'], '7'*32)
        self.assertEqual(self.writes, ['manual-control.json'])
        self.assertEqual(self.data['auto-control.json'], {})

    def test_primary_recovery_does_not_require_unexpired_trial(self):
        self.settings['native_until'] = '900'
        self.journal = {'phase': 'HELD-ON-RESERVE', 'tx': '7'*32,
                        'source': self.settings['plan_source'], 'target': self.settings['plan_target']}
        answer = self.queue('primary')
        self.assertTrue(answer['accepted'])
        claimed, reason = manual.claim_pending(self.settings, self.revision, {}, self.now)
        self.assertIsNone(reason)
        self.assertEqual(claimed['transaction_id'], '7'*32)

    def test_primary_no_transaction_or_mismatching_pair_is_refused(self):
        self.assertEqual(self.queue('primary')['blockers'], ['RETURN-NOT-APPLICABLE'])
        self.journal = {'phase': 'COMMITTED', 'tx': '7'*32, 'source': 'other', 'target': 'another'}
        self.assertEqual(self.queue('primary')['blockers'], ['RETURN-NOT-APPLICABLE'])
        self.assertEqual(self.writes, [])

    def test_only_claimed_transaction_can_publish_completion(self):
        record = self.queued()
        with self.assertRaisesRegex(ValueError, 'MANUAL-COMPLETION-UNVERIFIED'):
            manual.publish_result(record['request_id'], 'COMPLETED', tx='7'*32)
        manual.claim_pending(self.settings, self.revision, {}, self.now)
        with self.assertRaisesRegex(ValueError, 'MANUAL-COMPLETION-UNVERIFIED'):
            manual.publish_result(record['request_id'], 'COMPLETED')
        self.assertTrue(manual.publish_result(record['request_id'], 'COMPLETED', tx='7'*32))
        self.assertTrue(manual.public_status()['completed'])
        self.assertFalse(manual.publish_result(record['request_id'], 'APPLYING'))

    def test_old_result_cannot_overwrite_another_request(self):
        self.queued()
        self.assertFalse(manual.publish_result('f'*32, 'REFUSED', code='NO-PROOF'))
        self.assertEqual(self.data['manual-control.json']['state'], 'QUEUED')

    def test_malformed_ram_is_unknown_not_idle_or_completed(self):
        for record in (None, [], False, {'state': 'COMPLETED'}, {'secret': 'PRIVATE_SENTINEL'}):
            self.data['manual-control.json'] = record
            status = manual.public_status()
            self.assertEqual(status['state'], 'UNCONFIRMED')
            self.assertFalse(status['completed'])
            self.assertNotIn('PRIVATE_SENTINEL', str(status))
        self.data['manual-control.json'] = {}
        record = copy.deepcopy(self.queued())
        for field, value in [('state', []), ('requested_at', True), ('code', 'PRIVATE raw secret'),
                             ('transaction_id', 'not-id'), ('until', float('inf'))]:
            bad = dict(record); bad[field] = value
            self.assertFalse(manual.valid_record(bad))

    def test_transport_failure_never_leaks_exception_or_reports_queued(self):
        self.backend.policy.side_effect = OSError('PRIVATE_SENTINEL')
        answer = self.queue()
        self.assertFalse(answer['accepted'])
        self.assertFalse(answer['queued'])
        self.assertNotIn('PRIVATE_SENTINEL', str(answer))

    def test_control_status_uses_same_certification_and_does_not_queue(self):
        status = manual.control_status()
        self.assertTrue(status['available'])
        self.assertTrue(status['reserve']['allowed'])
        self.assertFalse(status['primary']['allowed'])
        self.assertEqual(self.writes, [])
        self.certificate['vendor_identity'] = 'bad'
        self.assertIn('LAN-TRIAL-REQUIRED', manual.control_status()['reserve']['blockers'])
        self.settings['monitor_only'] = '1'
        self.backend.diagnostic.reset_mock()
        self.assertFalse(manual.control_status()['available'])
        self.backend.diagnostic.assert_not_called()
        self.assertEqual(self.writes, [])

    def test_pending_or_corrupt_queue_disables_controls(self):
        self.queued()
        self.assertIn('MANUAL-REQUEST-PENDING', manual.control_status()['reserve']['blockers'])
        self.data['manual-control.json'] = []
        self.assertIn('MANUAL-STATE-UNVERIFIED', manual.control_status()['reserve']['blockers'])


if __name__ == '__main__':
    unittest.main()
