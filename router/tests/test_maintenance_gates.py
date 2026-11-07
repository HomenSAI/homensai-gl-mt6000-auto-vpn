"""Plan item 54 (audit F-16): while the package hooks hold the maintenance marker, Start, the manual click, the failure
test, the speed test and the return button are refused with MAINTENANCE-IN-PROGRESS and the supervisor begins no new
session; Stop is never refused, and a stale marker (another boot, too old) blocks nothing.
Lua twin: tests/lua/test_control_request.lua (control_request.start / fault_start), pair.tick (tests/lua/test_maintenance_tick.lua)."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import auto_control  # noqa: E402
import maintenance  # noqa: E402
import pair_auto  # noqa: E402

REV = 'a'*32


class Gates(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.runtime = root/'run';self.runtime.mkdir(mode=0o700)
        self.persist = root/'etc';self.persist.mkdir(mode=0o700)
        (self.runtime/'auto-control-revision.json').write_text(json.dumps({'revision': REV}))
        for target in (patch.object(auto_control, 'RUNTIME', self.runtime), patch.object(auto_control, 'PERSIST', self.persist),
                       patch.object(agent, 'RUNTIME', self.runtime), patch.object(agent, 'PERSIST', self.persist),
                       patch.object(maintenance, 'PROC', root/'no-proc')):  # no boot id: the wall clock bounds the marker
            target.start();self.addCleanup(target.stop)

    def mark(self, age=5):
        (self.persist/'maintenance.json').write_text(json.dumps({'action': 'upgrade', 'time': time.time()-age}))

    def test_start_is_refused_first_and_nothing_is_written(self):
        self.mark()
        with patch('native_switch.Linux', side_effect=AssertionError('no router read during a package operation')):
            self.assertEqual(auto_control.start(REV, request_source='manual'),
                             {'accepted': False, 'blockers': ['MAINTENANCE-IN-PROGRESS']})
        self.assertFalse((self.runtime/'auto-control.json').exists())

    def test_the_pair_request_checks_again_under_the_lock(self):
        # F-16: the guard marks under the same control lock between Start's preflight and this write
        self.mark()
        self.assertEqual(pair_auto.request(REV, request_source='manual'), {'accepted': False, 'blockers': ['MAINTENANCE-IN-PROGRESS']})
        self.assertFalse((self.runtime/'pair-auto-control.json').exists())
        self.assertFalse((self.persist/'auto-resume.json').exists())

    def test_a_stale_marker_never_blocks(self):
        self.mark(age=maintenance.LIMIT+10)
        self.assertIsNone(auto_control.maintenance_blocker())
        self.assertIsNone(agent.maintenance_refusal('pair_manual'))

    def test_buttons_answer_with_the_code(self):
        self.mark()
        self.assertEqual(auto_control.return_request(self.runtime), {'accepted': False, 'code': 'MAINTENANCE-IN-PROGRESS'})
        self.assertFalse((self.runtime/'native-return.json').exists())
        self.assertEqual(agent.control_reply('fault_start', {'profile': 'x', 'scope': 'channel', 'duration': 30}),
                         {'accepted': False, 'code': 'MAINTENANCE-IN-PROGRESS'})
        self.assertEqual(agent.pair_manual_reply({'direction': 'reserve', 'control_revision': REV}),
                         {'accepted': False, 'queued': False, 'completed': False, 'blockers': ['MAINTENANCE-IN-PROGRESS']})
        for method in ('speed_start', 'native_return'):
            self.assertEqual(agent.maintenance_refusal(method), {'accepted': False, 'code': 'MAINTENANCE-IN-PROGRESS'})
        self.assertEqual(agent.maintenance_refusal('manual_switch')['blockers'], ['MAINTENANCE-IN-PROGRESS'])

    def test_stop_is_never_refused(self):
        self.mark()
        with patch('agent.command', return_value=json.dumps({'settings': {'native_trial': ''}})):
            reply = auto_control.stop(runtime=self.runtime, persist=self.persist, request_source='manual')
        self.assertEqual(reply.get('queued'), True)
        self.assertTrue((self.persist/'native-stop.json').exists())

    def test_the_supervisor_begins_no_session_and_keeps_the_start_queued(self):
        self.mark()
        published = []
        row = {'mode': 'on', 'revision': REV, 'id': 'b'*32, 'time': time.time()}
        with patch.object(pair_auto, 'intent', return_value=row), patch.object(pair_auto, 'read_state', return_value={}), \
                patch.object(pair_auto, 'begin', side_effect=AssertionError('no session during a package operation')), \
                patch('native_switch.publish', side_effect=published.append), \
                patch.object(pair_auto, 'fail_request', side_effect=AssertionError('the Start stays queued')):
            self.assertTrue(pair_auto.tick(object(), {'pair_auto_mode': pair_auto.MODE}, REV))
        self.assertEqual([(p['state'], p['reason'], p['blockers']) for p in published],
                         [('ARMED', 'MAINTENANCE-IN-PROGRESS', ['MAINTENANCE-IN-PROGRESS'])])


class ShutdownRecord(unittest.TestCase):
    def test_the_supervisor_records_whether_its_shutdown_recovery_finished(self):
        # audit F-17: read by lifecycle_guard.shutdown_refusal after the service stop
        import native_switch
        import lifecycle_guard
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);runtime = root/'var/run/homensai-vpn';runtime.mkdir(parents=True)
            with patch.object(native_switch, 'RUNTIME', runtime), patch('agent.RUNTIME', runtime):
                native_switch.shutdown_record(True)
                self.assertEqual(json.loads((runtime/'supervisor-shutdown.json').read_text())['ok'], True)
                self.assertIsNone(lifecycle_guard.shutdown_refusal(root))
                native_switch.shutdown_record(False)
                row = json.loads((runtime/'supervisor-shutdown.json').read_text())
                self.assertEqual((row['ok'], row['code']), (False, 'PAIR-RECOVERY-REQUIRED'))
                self.assertEqual(lifecycle_guard.shutdown_refusal(root), 'LIFECYCLE-RECOVERY-UNFINISHED')
                native_switch.shutdown_record(None)          # an unknown result is not a finished recovery
                self.assertEqual(lifecycle_guard.shutdown_refusal(root), 'LIFECYCLE-RECOVERY-UNFINISHED')
        source = (HERE.parent/'files/usr/lib/homensai-vpn/native_switch.py').read_text(encoding='utf-8')
        self.assertIn('shutdown_record(pair_shutdown(backend))', source)


class Status(unittest.TestCase):
    def test_both_monitors_publish_the_maintenance_view_and_the_catalogue_names_every_code(self):
        lib = HERE.parent/'files/usr/lib/homensai-vpn'
        self.assertIn("status['maintenance']=maintenance_public(PERSIST)", (lib/'agent.py').read_text(encoding='utf-8'))
        self.assertIn("status.maintenance=require('maintenance').public(runner.read_file,self.persist,runner.wall())",
                      (lib/'lua/monitor.lua').read_text(encoding='utf-8'))
        rows = (HERE.parent/'error_table.inc.js').read_text(encoding='utf-8')+(HERE.parent/'error_rows_extra.inc.js').read_text(encoding='utf-8')
        import re
        for code in ('MAINTENANCE-IN-PROGRESS', 'MAINTENANCE-INTERRUPTED', 'LIFECYCLE-STOP-UNFINISHED',
                     'LIFECYCLE-RECOVERY-UNFINISHED', 'LIFECYCLE-MAINTENANCE-FAILED'):
            row = re.search(r'''\[['"]%s['"], ?['"]service['"](.*)\],''' % code, rows)
            self.assertIsNotNone(row, code)
            self.assertRegex(row.group(1), '[а-я]', code+': Russian text')


if __name__ == '__main__':
    unittest.main()
