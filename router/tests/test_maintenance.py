"""Plan item 54 (audit F-16/F-17): the package maintenance marker, maintenance.py.

Shared cases: maintenance_cases.json; Lua twin: tests/lua/test_maintenance.lua (maintenance.lua, the same cases)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'files/usr/lib/homensai-vpn'))
import maintenance  # noqa: E402

DATA = json.loads((HERE/'maintenance_cases.json').read_text(encoding='utf-8'))


def marker_of(case):
    value = case['marker']
    if value == 'UNREADABLE':return False
    if isinstance(value, dict) and value.get('boot_id') in ('BOOT', 'OTHER'):
        value = dict(value, boot_id=DATA['boot'] if value['boot_id'] == 'BOOT' else DATA['other_boot'])
    return value


class SharedCases(unittest.TestCase):
    def test_shared_cases(self):
        for case in DATA['cases']:
            with self.subTest(case['name']):
                boot = case['boot'] if 'boot' in case else DATA['boot']
                view = maintenance.classify(marker_of(case), boot, case['uptime'], case['now'])
                for key, value in case['expect'].items():
                    self.assertEqual(view.get(key), value, key)
                if view['state'] == 'active':
                    self.assertEqual(view['code'], 'MAINTENANCE-IN-PROGRESS');self.assertNotIn('reason', view)
                elif view['state'] == 'stale':
                    self.assertEqual(view['code'], 'MAINTENANCE-INTERRUPTED');self.assertIn('reason', view)
                else:
                    self.assertEqual(view, {'state': 'none'})


class Files(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.persist = self.root/'etc';self.persist.mkdir()
        self.proc = self.root/'proc';(self.proc/'sys/kernel/random').mkdir(parents=True)
        (self.proc/'sys/kernel/random/boot_id').write_text(DATA['boot']+'\n')
        (self.proc/'uptime').write_text('100.25 300.00\n')

    def mark(self, **fields):
        row = dict({'action': 'upgrade', 'boot_id': DATA['boot'], 'uptime': 90.0, 'time': 990.0}, **fields)
        (self.persist/'maintenance.json').write_text(json.dumps(row))

    def test_proc_readers(self):
        self.assertEqual(maintenance.boot_id(self.proc), DATA['boot'])
        self.assertEqual(maintenance.uptime(self.proc), 100.25)
        self.assertIsNone(maintenance.boot_id(self.root/'missing'))
        self.assertIsNone(maintenance.uptime(self.root/'missing'))

    def test_blocker_and_public(self):
        self.assertIsNone(maintenance.blocker(self.persist, self.proc, 1000))
        self.assertIsNone(maintenance.public(self.persist, self.proc, 1000))
        self.mark()
        self.assertEqual(maintenance.blocker(self.persist, self.proc, 1000), 'MAINTENANCE-IN-PROGRESS')
        self.assertEqual(maintenance.public(self.persist, self.proc, 1000),
                         {'state': 'active', 'code': 'MAINTENANCE-IN-PROGRESS', 'action': 'upgrade', 'since': 990.0})
        self.mark(boot_id=DATA['other_boot'])                       # the power cut: the next boot never blocks
        self.assertIsNone(maintenance.blocker(self.persist, self.proc, 1000))
        self.assertEqual(maintenance.public(self.persist, self.proc, 1000)['reason'], 'reboot')

    def test_damaged_symlinked_or_huge_marker_is_stale_never_blocking(self):
        path = self.persist/'maintenance.json'
        path.write_text('{"action":')
        self.assertEqual(maintenance.public(self.persist, self.proc, 1000)['reason'], 'invalid')
        path.write_text(json.dumps({'action': 'upgrade', 'pad': 'x'*5000}))
        self.assertEqual(maintenance.public(self.persist, self.proc, 1000)['reason'], 'invalid')
        path.unlink()
        target = self.root/'elsewhere.json'
        target.write_text(json.dumps({'action': 'upgrade', 'boot_id': DATA['boot'], 'uptime': 90, 'time': 990}))
        try:os.symlink(str(target), str(path))
        except (OSError, NotImplementedError):self.skipTest('no symlinks')
        self.assertIsNone(maintenance.blocker(self.persist, self.proc, 1000))

    def test_clear_stale_reports_and_removes_only_a_stale_marker(self):
        self.assertIsNone(maintenance.clear_stale(self.persist, self.proc, 1000))
        self.mark()
        self.assertIsNone(maintenance.clear_stale(self.persist, self.proc, 1000), 'an active marker stays')
        self.assertTrue((self.persist/'maintenance.json').exists())
        self.mark(boot_id=DATA['other_boot'])
        (self.persist/'upgrade-result.json').write_text('{"code":"UPGRADE-ROLLED-BACK"}')
        record = maintenance.clear_stale(self.persist, self.proc, 1000)
        self.assertFalse((self.persist/'maintenance.json').exists())
        stored = json.loads((self.persist/'upgrade-result.json').read_text())
        self.assertEqual(stored, record)
        self.assertEqual({k: stored[k] for k in ('code', 'reason', 'action', 'from', 'to', 'since')},
                         {'code': 'MAINTENANCE-INTERRUPTED', 'reason': 'reboot', 'action': 'upgrade', 'from': '', 'to': '', 'since': 990.0})
        self.assertFalse(list(self.persist.glob('.*.new')))

    def test_cli_accepts_only_clear_stale(self):
        script = HERE.parent/'files/usr/lib/homensai-vpn/maintenance.py'
        result = subprocess.run([sys.executable, '-I', str(script), 'other'], capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)


class SharedFiles(unittest.TestCase):
    """IR-06 (integration review 07.11.2026): the marker file as read from disk; Lua twin: tests/lua/test_maintenance.lua
    (the same maintenance_cases.json "files")."""
    def test_shared_file_cases(self):
        for case in DATA['files']:
            with self.subTest(case['name']), tempfile.TemporaryDirectory() as directory:
                root = Path(directory);persist = root/'etc';persist.mkdir()
                proc = root/'proc';(proc/'sys/kernel/random').mkdir(parents=True)
                (proc/'sys/kernel/random/boot_id').write_text(DATA['boot']+'\n')
                (proc/'uptime').write_text('%s 1.0\n' % case['uptime'])
                path = persist/'maintenance.json';target = root/'elsewhere.json'
                marker = marker_of(case)
                if case['layout'] == 'regular':path.write_text(json.dumps(marker))
                elif case['layout'] == 'symlink':
                    target.write_text(json.dumps(marker));os.symlink(str(target), str(path))
                elif case['layout'] == 'dangling':os.symlink(str(root/'missing.json'), str(path))
                elif case['layout'] == 'directory':path.mkdir()
                want = case['expect']
                got = maintenance.read_marker(persist)
                self.assertIs(got is False, want['read'] == 'invalid')
                view = maintenance.current(persist, proc, case['now'])
                self.assertEqual(view['state'], want['state'])
                if 'reason' in want:self.assertEqual(view['reason'], want['reason'])
                self.assertEqual(maintenance.blocker(persist, proc, case['now']), want['blocker'])
                if 'clear_stale' in want:
                    record = maintenance.clear_stale(persist, proc, case['now'])
                    if want['clear_stale'] is None:
                        self.assertIsNone(record);self.assertTrue(os.path.lexists(str(path)))
                    else:
                        self.assertEqual({k: record[k] for k in want['clear_stale']}, want['clear_stale'])
                        self.assertFalse(os.path.lexists(str(path)), 'the link itself is removed')
                if case['layout'] == 'symlink':
                    self.assertEqual(json.loads(target.read_text()), marker, 'the target is never touched')


class ServiceStart(unittest.TestCase):
    def test_init_reports_a_stale_marker_after_the_integrity_gate_before_any_instance(self):
        init = (HERE.parent/'files/etc/init.d/homensai-vpn').read_text(encoding='utf-8')
        body = init[init.index('start_service() {'):]
        call = body.index('maintenance_report "$integrity_mode" "$canon_env"')
        self.assertLess(body.index('integrity_mode=$(integrity_gate)'), call)
        self.assertLess(call, body.index('procd_open_instance monitor'))
        function = init[init.index('maintenance_report() {'):init.index('start_service() {')]
        self.assertIn('/usr/lib/homensai-vpn/lua/maintenance.lua clear-stale', function)
        self.assertIn('/usr/lib/homensai-vpn/maintenance.py clear-stale', function)
        self.assertIn('stopped) return 0', function)       # damaged Lua and Python: nothing runs


if __name__ == '__main__':
    unittest.main()
