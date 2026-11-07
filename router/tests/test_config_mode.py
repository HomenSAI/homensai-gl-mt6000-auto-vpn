"""The UCI config holds the Telegram token: it must be root-only (0600) in the package, after install and after every
confirmed write by the Python runtime. The Lua writer is covered in test_lua_contracts.py. No router access."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROUTER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROUTER))
sys.path.insert(0, str(ROUTER / 'files/usr/lib/homensai-vpn'))
import build_ipk
import package_hooks
import setup_config as setup

CONF = 'etc/config/homensai_vpn'


class PackageMode(unittest.TestCase):
    def test_config_ships_root_only_and_everything_else_keeps_its_mode(self):
        files = {name: mode for name, _, mode in build_ipk.selected_files()}
        self.assertEqual(files[CONF], 0o600)
        for name, mode in files.items():
            if name != CONF:
                self.assertIn(mode, (0o644, 0o755), name)

    def test_integrity_manifest_lists_the_config_with_mode_only(self):
        manifest = build_ipk.payload_manifest([(n, p, m) for n, p, m in build_ipk.selected_source_files()])
        rows = [line for line in manifest.decode().splitlines() if line.endswith(' /' + CONF)]
        self.assertEqual(len(rows), 1)
        self.assertRegex(rows[0], r'^-{64} 0600 /')

    def test_postinst_and_sdk_makefile_set_0600(self):
        postinst = package_hooks.scripts()['postinst']
        self.assertIn('chmod 0600 /etc/config/homensai_vpn', postinst)
        self.assertLess(postinst.index('chmod 0600 /etc/config/homensai_vpn'), postinst.index('/etc/init.d/homensai-vpn enable'))
        self.assertIn('chmod 0600 /etc/config/homensai_vpn', (ROUTER / 'package-hooks.mk').read_text(encoding='utf-8'))
        self.assertRegex((ROUTER / 'Makefile').read_text(encoding='utf-8'), r'chmod 0600 \$\(1\)/etc/config/homensai_vpn')


@unittest.skipUnless(os.name == 'posix', 'POSIX permission bits')
class PythonWriter(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config = Path(directory.name) / 'homensai_vpn'
        self.config.write_text("config main 'main'\n")
        self.config.chmod(0o644)
        patcher = patch.object(setup, 'CONFIG', str(self.config))
        patcher.start()
        self.addCleanup(patcher.stop)

    def mode(self):
        return self.config.stat().st_mode & 0o777

    def test_harden_config_sets_0600_and_tolerates_a_missing_file(self):
        setup.harden_config()
        self.assertEqual(self.mode(), 0o600)
        setup.harden_config(str(self.config) + '.missing')

    def writer(self, stdout=b'OK', code=0):
        return subprocess.CompletedProcess([], code, stdout=stdout, stderr=b'')

    def test_telegram_save_leaves_the_config_root_only(self):
        arguments = {'token': '123456789:' + 'Ab3_' * 9, 'chat': '-1001', 'enabled': True, 'interval': 60}
        with patch.object(setup, 'control_lock'), patch.object(setup, 'inventory', return_value={'profiles': [], 'settings': {}}), \
                patch('rpc_throttle.allow', return_value=True), patch.object(setup.subprocess, 'run', return_value=self.writer()):
            result = setup.save(arguments, 'telegram')
        self.assertTrue(result['saved'], result)
        self.assertEqual(self.mode(), 0o600)

    def test_forget_and_failed_save(self):
        with patch.object(setup, 'control_lock'), patch('rpc_throttle.allow', return_value=True), \
                patch.object(setup.subprocess, 'run', return_value=self.writer(b'FAIL', 1)):
            self.assertFalse(setup.save({}, 'forget')['saved'])
        self.assertEqual(self.mode(), 0o644, 'a refused write changes nothing')
        with patch.object(setup, 'control_lock'), patch('rpc_throttle.allow', return_value=True), \
                patch.object(setup.subprocess, 'run', return_value=self.writer()):
            self.assertTrue(setup.save({}, 'forget')['saved'])
        self.assertEqual(self.mode(), 0o600)


if __name__ == '__main__':
    unittest.main()
