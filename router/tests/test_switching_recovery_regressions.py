"""Regression coverage for durable dispatch interruption and manual visibility.

The transaction/journal/control locks are real; only the router and process
boundaries are replaced by the existing deterministic platform fixture.
"""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import auto_live
import native_switch as native
import observation_freshness
import pair_auto as pair
import pair_manual as manual
import test_pair_manual_directions as fixture


class SwitchingRecovery(unittest.TestCase):
    def setUp(self):
        self.case = fixture.PairManualDirections()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.kernel_applied = True

    def test_stop_after_durable_arm_before_spawn_closes_undispatched_journal(self):
        case = self.case
        self.assertTrue(manual.request('primary', case.revision)['accepted'])
        write = native.journal_write
        stopped = []

        def stop_after_arm(row):
            write(row)
            if row.get('phase') == 'ARMED' and not stopped:
                revision = auto_control.current_revision(rotate=True)
                pair.stop_locked(revision)
                stopped.append(revision)

        with patch.object(native, 'journal_write', side_effect=stop_after_arm):
            manual.consume(case.backend, pair.read_state(), case.settings, case.revision)
        self.assertEqual(manual.public()['state'], 'CANCELLED')
        case.spawn.assert_not_called()
        case.backend.apply.assert_not_called()
        self.assertEqual(native.journal_read()['phase'], 'ROLLED-BACK')
        self.assertFalse((case.persist / 'pair-auto-budget.json').exists())
        self.assertTrue(pair.tick(case.backend, case.settings, stopped[0]))
        self.assertEqual(pair.read_state()['phase'], 'STOPPED')

    def test_supervisor_hands_stranded_pair_journal_to_independent_recovery(self):
        case = self.case
        pending = case.request('primary')
        pending['phase'] = 'RESTORING'
        native.JOURNAL.unlink()  # Empty pre-start fixture; the interrupted tick writes it below.
        case.backend.apply.reset_mock()
        called = []

        def incomplete_tick(*_args):
            self.assertFalse(called, 'an unfinished journal must not be polled forever')
            called.append(True)
            native.journal_write(pending)
            return True

        with patch.object(pair, 'recover', return_value=True), \
                patch.object(pair, 'tick', side_effect=incomplete_tick), \
                patch.object(native, 'JOURNAL_ALARM', case.persist / 'alarm.json'), \
                patch.object(native, 'ATTEMPTS', case.persist / 'attempts.json'), \
                patch.object(native.time, 'sleep'):
            native.serve()
        self.assertEqual(len(called), 1)
        self.assertEqual(native.journal_read()['phase'], 'RESTORING')
        self.assertEqual(pair.intent()['mode'], 'off')
        case.backend.apply.assert_not_called()

    def test_stop_cancels_queued_manual_once_without_waiting_for_another_start(self):
        case = self.case
        self.assertTrue(manual.request('primary', case.revision)['accepted'])
        with patch.object(agent, 'command', side_effect=OSError('router not present')):
            auto_control.stop(runtime=case.runtime, persist=case.persist)
        first = manual.read()
        self.assertEqual(first['state'], 'CANCELLED')
        with patch.object(agent, 'command', side_effect=OSError('router not present')):
            auto_control.stop(runtime=case.runtime, persist=case.persist)
        manual.recover()
        self.assertEqual(manual.read(), first)
        case.spawn.assert_not_called()

    def test_supported_long_interval_does_not_disable_healthy_manual_choices(self):
        case = self.case
        case.settings['interval'] = '300'
        status = agent.read_json(case.runtime / 'status.json')
        for profile in status['profiles']:
            profile['time'] = fixture.NOW - 100
        agent.atomic_json(case.runtime / 'status.json', status)
        control = manual.controls()
        self.assertTrue(control['primary']['allowed'], control)
        self.assertTrue(control['reserve']['allowed'], control)
        self.assertEqual(control['observation_valid_for'], 900)

    def test_short_interval_rejects_outdated_or_future_health(self):
        case = self.case
        case.settings['interval'] = '10'
        status = agent.read_json(case.runtime / 'status.json')
        for stamp in (fixture.NOW - 31, fixture.NOW + 1):
            with self.subTest(stamp=stamp):
                for profile in status['profiles']:
                    profile['time'] = stamp
                agent.atomic_json(case.runtime / 'status.json', status)
                control = manual.controls()
                self.assertFalse(control['primary']['allowed'])
                self.assertFalse(control['reserve']['allowed'])
                self.assertEqual(control['observation_valid_for'], 30)

    def test_orphan_claim_is_terminalized_once_without_replaying_work(self):
        case = self.case
        self.assertTrue(manual.request('primary', case.revision)['accepted'])
        row = manual.read()
        row['state'] = 'CLAIMED'
        agent.atomic_json(manual.path(), row)
        self.assertTrue(manual.consume(case.backend, pair.read_state(), case.settings, case.revision))
        first = manual.read()
        self.assertEqual(first['state'], 'UNCONFIRMED')
        self.assertEqual(first['code'], 'PAIR-MANUAL-RECOVERED')
        self.assertFalse(manual.consume(case.backend, pair.read_state(), case.settings, case.revision))
        manual.recover()
        self.assertEqual(manual.read(), first)
        case.spawn.assert_not_called()

    def test_recovery_revokes_intent_before_rollback_failure(self):
        case = self.case
        pending = case.request('primary')
        pending['phase'] = 'RESTORING'
        native.journal_write(pending)
        case.allow_next()
        # An interrupted request may have no terminal result even though its
        # journal already exists. Startup must revoke it before any retry.
        row = manual.read()
        row['state'] = 'CLAIMED'
        agent.atomic_json(manual.path(), row)
        with patch.object(native, 'JOURNAL_ALARM', case.persist / 'alarm.json'), \
                patch.object(native, 'rollback_counted', side_effect=native.Refused('ROLLBACK-UNVERIFIED')):
            with self.assertRaisesRegex(native.Refused, 'ROLLBACK-UNVERIFIED'):
                native.serve()
        self.assertEqual(pair.intent()['mode'], 'off')
        self.assertEqual(manual.public()['state'], 'UNCONFIRMED')
        self.assertEqual(native.journal_read()['phase'], 'RESTORING')

    def test_damaged_manual_metadata_cannot_prevent_stop_or_journal_recovery(self):
        case = self.case
        manual.path().write_text('{damaged', encoding='utf8')
        with patch.object(agent, 'command', side_effect=OSError('router not present')):
            result = auto_control.stop(runtime=case.runtime, persist=case.persist)
        self.assertTrue(result['queued'])
        self.assertEqual(pair.intent()['mode'], 'off')
        self.assertTrue(agent.read_json(case.persist / 'native-stop.json')['all_trials'])
        pair.fence_recovery()
        self.assertEqual(manual.path().read_text(), '{damaged')

    def test_pair_terminal_outcome_remains_visible_with_controls_disabled(self):
        case = self.case
        accepted = manual.request('primary', case.revision)
        with patch.object(agent, 'command', side_effect=OSError('router not present')):
            auto_control.stop(runtime=case.runtime, persist=case.persist)
        self.assertFalse(manual.controls()['available'])
        use_pair, result = manual.public_for_status({'mode': 'continuous-pair'})
        self.assertTrue(use_pair)
        self.assertEqual(result['request_id'], accepted['request_id'])
        self.assertEqual(result['state'], 'CANCELLED')
        self.assertFalse(result['completed'])

    def test_full_and_live_rpc_keep_the_same_cancelled_request_and_health_clock(self):
        case = self.case
        accepted = manual.request('primary', case.revision)
        monitor = agent.read_json(case.runtime / 'status.json')
        observation_freshness.attach(monitor, {'interval': 300})
        agent.atomic_json(case.runtime / 'status.json', monitor)
        with patch.object(agent, 'command', side_effect=OSError('router not present')):
            auto_control.stop(runtime=case.runtime, persist=case.persist)
        output = io.StringIO()
        with patch.object(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(b'{}'))), \
                patch('speed_test.public_status', return_value={'results': []}), \
                patch('retention_settings.configured_days', return_value=7), \
                patch('manual_control.control_status', side_effect=AssertionError('pair outcome was routed to legacy')), \
                redirect_stdout(output):
            agent.rpc('status')
        full = json.loads(output.getvalue())
        live = auto_live.snapshot()
        for status in (full, live):
            self.assertEqual(status['manual_switch']['request_id'], accepted['request_id'])
            self.assertEqual(status['manual_switch']['state'], 'CANCELLED')
            self.assertEqual(status['observation_valid_for'], 900)
            self.assertEqual(status['profiles'][0]['time'], fixture.NOW)
            self.assertEqual(status['profiles'][0]['observation_valid_for'], 900)

    def test_freshness_projection_never_refreshes_measurement_time(self):
        status = {'time': 100, 'profiles': [{'id': 'vpn', 'time': 90,
                                         'website_response': {'valid_for': 45}}]}
        observation_freshness.attach(status, {'interval': '300'})
        self.assertEqual(status['time'], 100)
        self.assertEqual(status['profiles'][0]['time'], 90)
        self.assertEqual(status['profiles'][0]['observation_valid_for'], 900)
        self.assertEqual(status['profiles'][0]['website_response']['valid_for'], 45)
        for invalid in (True, -1, 0, 301, 'nan', [], 1e100):
            with self.subTest(invalid=invalid):
                self.assertEqual(observation_freshness.valid_for({'interval': invalid}), 90)


if __name__ == '__main__':
    unittest.main()
