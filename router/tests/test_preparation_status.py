from pathlib import Path
import hashlib
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files/usr/lib/homensai-vpn'))
import preparation_status as p


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('tmp/sysinfo', 'etc/rc.d', 'etc/modules.d', 'etc/homensai-vpn/disabled-module-autoload', 'proc'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        (self.root / 'tmp/sysinfo/board_name').write_text('glinet,mt3000-snand')
        (self.root / 'proc/modules').write_text('mtkhnat 1024 0 - Live 0\n')
        self.saved = self.root / 'etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe'
        self.saved.write_bytes(b'shortcut-fe\nshortcut-fe-ipv6\n')
        self.pin = patch.object(p, 'AUTOLOAD_SHA', hashlib.sha256(self.saved.read_bytes()).hexdigest())
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def run_flag(self, args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=b'0\n')

    def report(self, run=None):
        return p.snapshot(self.root, run or self.run_flag)

    def test_ready_never_authorizes_native_or_external_lan_and_never_writes(self):
        before = {x.relative_to(self.root): x.read_bytes() for x in self.root.rglob('*') if x.is_file()}
        report = self.report()
        self.assertEqual(report['state'], 'pass')
        self.assertEqual(len(report['checks']), 7)
        self.assertFalse(report['native_permission'])
        self.assertFalse(report['external_lan_verified'])
        self.assertEqual(before, {x.relative_to(self.root): x.read_bytes() for x in self.root.rglob('*') if x.is_file()})

    def test_boot_links_and_live_sfe_remain_failures(self):
        (self.root / 'etc/rc.d/S95vpn-client').write_text('not even a symlink')
        (self.root / 'etc/modules.d/09-shortcut-fe').write_text('shortcut-fe')
        (self.root / 'proc/modules').write_text('shortcut_fe 2048 0 - Live 0\n')
        rows = {x['code']: x['state'] for x in self.report()['checks']}
        for key in ('PREP-STOCK-VPN-BOOT', 'PREP-SFE-AUTOLOAD', 'PREP-SFE-RUNTIME'):
            self.assertEqual(rows[key], 'fail')

    def test_missing_or_changed_preservation_is_unknown(self):
        self.saved.write_bytes(b'changed')
        self.assertIn({'code': 'PREP-SFE-AUTOLOAD', 'state': 'unknown'}, self.report()['checks'])
        self.saved.unlink()
        self.assertIn({'code': 'PREP-SFE-AUTOLOAD', 'state': 'unknown'}, self.report()['checks'])

    def test_uci_failure_does_not_hide_other_evidence_or_publish_values(self):
        def run(args, **kwargs):
            self.assertEqual(args[:3], ['uci', '-q', 'get'])
            return SimpleNamespace(returncode=2, stdout=b'private value')
        report = self.report(run)
        self.assertEqual(report['state'], 'incomplete')
        self.assertNotIn('private value', str(report))
        self.assertEqual(sum(x['state'] == 'unknown' for x in report['checks']), 3)

    def test_unknown_board_never_inherits_mt3000_readiness(self):
        (self.root / 'tmp/sysinfo/board_name').write_text('glinet,gl-mt6000')
        self.assertEqual(self.report()['state'], 'unsupported')
        (self.root / 'tmp/sysinfo/board_name').unlink()
        self.assertEqual(self.report()['state'], 'unknown')

    def test_selected_second_client_is_checked_instead_of_an_unused_first_slot(self):
        seen=[]
        def run(args,**kwargs):seen.append(args[-1]);return self.run_flag(args,**kwargs)
        report=p.snapshot(self.root,run,settings={'plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'openvpn:ovpnclient2'})
        self.assertEqual(report['state'],'pass');self.assertIn('network.ovpnclient2.auto',seen)
        self.assertNotIn('network.ovpnclient1.auto',seen)
        self.assertIn('PREP-TARGET-AUTOSTART',[row['code']for row in report['checks']])


if __name__ == '__main__':
    unittest.main()
