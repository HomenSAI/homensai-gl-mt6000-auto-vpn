"""Power cut during a switch (soak, alpha16): recovery failures right after boot are retried, not counted.

Same rule as auto.lua boot_rollback (router/tests/lua/test_auto_recovery.lua).
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files/usr/lib/homensai-vpn'))
import native_switch as native


class BootRollbackRetry(unittest.TestCase):
    def run_case(self, errors, uptime, stop=False):
        calls = []
        def rollback(backend, journal, reason):
            calls.append(reason)
            if len(calls) <= len(errors):
                raise errors[len(calls)-1]
            return 'done'
        slept = []
        journal = {}
        with patch.object(native, 'rollback', side_effect=rollback), \
                patch.object(native, 'journal_write'), \
                patch.object(native, 'recovery_package', return_value='test'), \
                patch.object(native, 'STOP', stop), \
                patch('pair_auto._log'):
            clock = [uptime]
            def sleep(seconds):
                slept.append(seconds);clock[0] += seconds
            try:
                result = native.boot_rollback(None, journal, uptime=lambda: clock[0], sleep=sleep)
            except Exception as error:
                result = error
        return result, calls, slept, journal

    def test_transient_codes_retried_in_boot_window(self):
        result, calls, slept, journal = self.run_case(
            [ValueError('KERNEL-POLICY-UNVERIFIED'), native.Refused('ROLLBACK-UNVERIFIED')], 90)
        self.assertEqual(result, 'done')
        self.assertEqual(calls, ['SUPERVISOR-RECOVERY']*3)
        self.assertEqual(slept, [native.BOOT_RETRY_WAIT]*2)
        self.assertNotIn('rollback_failures', journal)

    def test_counted_after_boot_window(self):
        result, calls, slept, journal = self.run_case([ValueError('KERNEL-POLICY-UNVERIFIED')]*5,
                                                      native.BOOT_SETTLE_UPTIME-native.BOOT_RETRY_WAIT-5)
        self.assertIsInstance(result, ValueError)
        self.assertEqual(len(calls), 2)
        self.assertEqual(journal['rollback_failures'], 1)

    def test_other_code_counted_at_once(self):
        result, calls, slept, journal = self.run_case([native.Refused('POLICY-IDENTITY-CHANGED')], 90)
        self.assertIsInstance(result, native.Refused)
        self.assertEqual((len(calls), slept, journal['rollback_failures']), (1, [], 1))

    def test_stop_counts_at_once(self):
        result, calls, slept, journal = self.run_case([native.Refused('ROLLBACK-UNVERIFIED')]*3, 90, stop=True)
        self.assertIsInstance(result, native.Refused)
        self.assertEqual((len(calls), journal['rollback_failures']), (1, 1))


if __name__ == '__main__':
    unittest.main()
