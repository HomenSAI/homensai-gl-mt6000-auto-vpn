"""Self-check and self-restore of the installed program files (TODO item 15; INTEGRITY-MATRIX-2026-11-01.ru.md).

1. The payload manifest (build_ipk) ships in the package, in both builders.
2. /usr/sbin/homensai-vpn-integrity: verify / snapshot / boot / restore against damaged, missing and re-moded files,
   a damaged manifest, a damaged or foreign pristine copy, the restore-loop limits and an opkg run; the owner's
   config, terms, journal and history are never written. Needs sh, sha256sum, tar, `stat -c`, awk.
   `recheck` (safety review F-02): the check deferred while opkg ran is done once opkg ends (INTEGRITY-RECHECK-NOTE.md).
3. The init script: the mode the tool returns decides the procd instances (normal, no-c, python, stopped); a damaged
   tool is put back from the pristine copy; without a tool the service starts as before.
4. The status fields (agent.py and the Lua monitor read RUNTIME/integrity.json).
5. Current Lua layers with damaged modules / canon_c.so (needs lua5.1), and the Lua Auto daemon with a damaged load
   path (writes /usr/lib/homensai-vpn, /var/run and /etc: only with HOMENSAI_FAULT_SANDBOX=1 in a throw-away container).
"""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import re
import time
import unittest

ROUTER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROUTER))
import build_ipk  # noqa: E402

TOOL = ROUTER/'files'/'usr'/'sbin'/'homensai-vpn-integrity'
INIT = ROUTER/'files'/'etc'/'init.d'/'homensai-vpn'
LUA_SRC = ROUTER/'files'/'usr'/'lib'/'homensai-vpn'/'lua'
CANON_C = ROUTER/'files'/'usr'/'lib'/'lua'/'canon_c.so'
HAVE_SH = all(shutil.which(x) for x in ('sh', 'sha256sum', 'tar', 'stat', 'awk', 'cmp'))
LUA = shutil.which('lua5.1')
MANIFEST = build_ipk.MANIFEST_PATH


def make_ipk(files, version=build_ipk.VERSION):
    data = build_ipk.archive(build_ipk.with_manifest(files, version))
    controls = build_ipk.archive([('control', b'Package: homensai-auto-vpn\n', 0o644)])
    return build_ipk.archive([('debian-binary', b'2.0\n', 0o644), ('control.tar.gz', controls, 0o644),
                              ('data.tar.gz', data, 0o644)])


def sample_files():
    return [('etc/config/homensai_vpn', b"config main 'main'\n", 0o644),
            ('etc/init.d/homensai-vpn', b'#!/bin/sh /etc/rc.common\nSTART=99\n', 0o755),
            ('usr/lib/homensai-vpn/lua/canon.lua', b'return {x=1}\n', 0o644),
            ('usr/lib/homensai-vpn/agent.py', b'print(1)\n', 0o644),
            ('usr/lib/homensai-vpn/inventory.lua', b'print(2)\n', 0o644),
            ('usr/lib/lua/canon_c.so', b'\x7fELF-not-really\n', 0o644),
            ('www/luci-static/resources/view/homensai-vpn/dashboard9.js', b"'use strict';\n", 0o644)]


def install(root, ipk):
    """What opkg leaves on the overlay: the data members at their paths with their modes."""
    with tarfile.open(fileobj=io.BytesIO(ipk), mode='r:gz') as outer:
        data = outer.extractfile('./data.tar.gz').read()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as inner:
        for member in inner.getmembers():
            target = Path(root)/member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.exists():
                target.unlink()  # never write through a planted symlink
            target.write_bytes(inner.extractfile(member).read())
            os.chmod(target, member.mode)


class ManifestTest(unittest.TestCase):
    def test_the_payload_carries_the_manifest_of_every_other_file(self):
        files = build_ipk.selected_files()
        names = [name for name, _, _ in files]
        self.assertEqual(names.count(MANIFEST), 1)
        source = build_ipk.selected_source_files()
        manifest = dict((name, payload) for name, payload, _ in files)[MANIFEST]
        self.assertEqual(manifest, build_ipk.payload_manifest(source))
        text = manifest.decode()
        rows = [line.split(' ') for line in text.splitlines() if not line.startswith('#')]
        self.assertEqual(sorted('/'+name for name, _, _ in source), [row[2] for row in rows])
        by_path = {row[2]: row for row in rows}
        self.assertEqual(by_path['/etc/config/homensai_vpn'][0], '-'*64, 'the owner config is never hashed')
        name, payload, mode = next(f for f in source if f[0] == 'usr/lib/homensai-vpn/lua/canon.lua')
        self.assertEqual(by_path['/'+name][:2], [hashlib.sha256(payload).hexdigest(), '%04o' % mode])
        for executable in ('/etc/init.d/homensai-vpn', '/usr/sbin/homensai-vpn-integrity', '/usr/sbin/homensai-vpn-emergency'):
            self.assertEqual(by_path[executable][1], '0755', executable)
        self.assertIn('# version '+build_ipk.VERSION, text)

    def test_sdk_staging_ships_the_same_manifest(self):
        import stage_files
        with tempfile.TemporaryDirectory() as folder:
            stage_files.stage(Path(folder)/'payload')
            staged = (Path(folder)/'payload'/MANIFEST).read_bytes()
        self.assertEqual(staged, build_ipk.payload_manifest(build_ipk.selected_source_files()))
        self.assertIn('$(1)/usr/sbin/homensai-vpn-integrity', (ROUTER/'Makefile').read_text())

    def test_manifest_refuses_itself_and_unsafe_names(self):
        for name in (MANIFEST, 'usr/lib/a b.lua', 'usr/../etc/x', 'usr/lib/x"y'):
            with self.subTest(name), self.assertRaises(ValueError):
                build_ipk.payload_manifest([(name, b'', 0o644)])

    def test_manifest_is_small_and_reproducible(self):
        files = build_ipk.selected_source_files()
        self.assertEqual(build_ipk.payload_manifest(files), build_ipk.payload_manifest(list(reversed(files))))
        self.assertLess(len(build_ipk.payload_manifest(files)), 64*1024)

    def test_postinst_makes_the_pristine_copy_before_the_restart(self):
        from package_hooks import scripts
        post = scripts()['postinst']
        snap = post.index('/usr/sbin/homensai-vpn-integrity snapshot')
        self.assertLess(snap, post.rindex('/etc/init.d/homensai-vpn restart'))
        # A refused copy (no space, permissions only) is a warning; a damaged unpacked payload stops before the restart
        # (audit 06.11.2026, F-19: every snapshot failure used to be a warning).
        # R4-07b (night2 N3-lifecycle 2): only the documented storage refusal (7) is a warning; an unexpected helper exit
        # (2 usage, 126/127 missing or damaged helper, anything else) aborts before enable/restart.
        self.assertIn('7) echo INTEGRITY-SNAPSHOT-REFUSED >&2; rm -f /etc/homensai-vpn/upgrade-result.json ;;', post)
        self.assertIn('0) rm -f /etc/homensai-vpn/upgrade-result.json ;;', post)   # a good install clears the old reason
        self.assertNotIn('*) echo INTEGRITY-SNAPSHOT-REFUSED', post)
        # Owner decision 07.11.2026: both refusals roll back to the previous working version (rollback_and_start, which
        # always ends with exit 1) instead of only stopping; the plain enable/restart of a good install comes after.
        enable = post.rindex('\n/etc/init.d/homensai-vpn enable\n')
        begin = post.index('rollback_and_start() {')
        function = post[begin:post.index('\n    exit 1\n}\n', begin)+len('\n    exit 1')]
        self.assertTrue(function.rstrip().endswith('exit 1'), function[-200:])
        self.assertLess(begin, post.index('/usr/sbin/homensai-vpn-integrity snapshot'))
        unexpected = post.index('*) echo "INTEGRITY-HELPER-FAILED')
        self.assertIn('rollback_and_start INTEGRITY-HELPER-FAILED ;;', post[unexpected:post.index('\n', unexpected)])
        self.assertLess(unexpected, enable)
        damaged = post.index('8) echo INTEGRITY-PAYLOAD-DAMAGED')
        self.assertLess(damaged, enable)
        self.assertIn('rollback_and_start INTEGRITY-PAYLOAD-DAMAGED ;;', post[damaged:post.index('\n', damaged)])
        self.assertIn('/usr/sbin/homensai-vpn-integrity snapshot', (ROUTER/'package-hooks.mk').read_text())


class ToolCase(unittest.TestCase):
    """A fake router root with the sample package installed and its pristine copy made by `snapshot`."""
    files = staticmethod(sample_files)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp/'root'
        self.ipk = make_ipk(self.files())
        install(self.root, self.ipk)
        self.persist = self.root/'etc'/'homensai-vpn'
        self.runtime = self.tmp/'run'
        # the deferred recheck polls every second here and never reaches the real init script of the host
        self.env = dict(os.environ, HOMENSAI_INTEGRITY_ROOT=str(self.root), HOMENSAI_INTEGRITY_RUNTIME=str(self.runtime),
                        HOMENSAI_INTEGRITY_PERSIST=str(self.persist), HOMENSAI_INTEGRITY_OPKG_LOCK=str(self.tmp/'opkg.lock'),
                        HOMENSAI_INTEGRITY_INIT=str(self.tmp/'no-init'), HOMENSAI_INTEGRITY_RECHECK_EVERY='1',
                        TMPDIR=str(self.tmp))
        self.pristine = self.persist/'pristine'/'payload.tar.gz'
        self.recheck_lock = self.runtime/'integrity-recheck.pid'

    def tearDown(self):
        self.stop_recheck()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stop_recheck(self):
        """A detached recheck a deferred boot launched must not outlive the test."""
        try:
            os.kill(int(os.readlink(self.recheck_lock)), 15)
        except (OSError, ValueError):
            pass

    def wait_for(self, predicate, timeout=30.0):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.1)
        return predicate()

    def report_code(self):
        try:
            return json.loads((self.runtime/'integrity.json').read_text())['code']
        except (OSError, ValueError, KeyError):
            return None

    def run_tool(self, *args):
        result = subprocess.run(['sh', str(TOOL)]+list(args), capture_output=True, text=True, env=self.env, timeout=120)
        return result.returncode, result.stdout

    def path(self, name):
        return self.root/name

    def snapshot(self):
        rc, out = self.run_tool('snapshot')
        self.assertEqual(rc, 0, out)
        return out

    def boot(self):
        rc, out = self.run_tool('boot')
        self.assertEqual(rc, 0, out)
        mode = out.strip().splitlines()[-1]
        self.assertTrue(mode.startswith('mode='), out)
        return mode[5:], json.loads((self.runtime/'integrity.json').read_text()), out

    def new_boot(self):
        (self.runtime/'integrity-restore.done').unlink(missing_ok=True)


@unittest.skipUnless(HAVE_SH, 'needs sh, sha256sum, tar, stat -c, awk, cmp')
class VerifyTest(ToolCase):
    def verify(self):
        return self.run_tool('verify', str(self.root))

    def test_clean_install_verifies(self):
        self.assertEqual(self.verify(), (0, ''))

    def test_zero_byte_truncated_flipped_deleted_and_mode(self):
        canon = self.path('usr/lib/homensai-vpn/lua/canon.lua')
        cases = [('zero', lambda: canon.write_bytes(b''), 'INTEGRITY-FILE-DAMAGED'),
                 ('half', lambda: canon.write_bytes(b'return {x='), 'INTEGRITY-FILE-DAMAGED'),
                 ('flip', lambda: canon.write_bytes(b'return {x=2}\n'), 'INTEGRITY-FILE-DAMAGED'),
                 ('delete', lambda: canon.unlink(), 'INTEGRITY-FILE-MISSING'),
                 ('symlink', lambda: (canon.unlink(), canon.symlink_to('/etc/passwd')), 'INTEGRITY-FILE-MISSING')]
        for label, damage, code in cases:
            with self.subTest(label):
                install(self.root, self.ipk)
                damage()
                rc, out = self.verify()
                self.assertEqual((rc, out.strip()), (3, code+' /usr/lib/homensai-vpn/lua/canon.lua'))
        install(self.root, self.ipk)
        os.chmod(self.path('etc/init.d/homensai-vpn'), 0o644)
        self.assertEqual(self.verify(), (3, 'INTEGRITY-FILE-MODE /etc/init.d/homensai-vpn\n'))

    def test_several_problems_are_listed_sorted(self):
        self.path('usr/lib/homensai-vpn/agent.py').unlink()
        self.path('usr/lib/homensai-vpn/lua/canon.lua').write_bytes(b'')
        rc, out = self.verify()
        self.assertEqual(rc, 3)
        self.assertEqual(out.splitlines(), ['INTEGRITY-FILE-DAMAGED /usr/lib/homensai-vpn/lua/canon.lua',
                                            'INTEGRITY-FILE-MISSING /usr/lib/homensai-vpn/agent.py'])

    def test_owner_config_is_never_compared(self):
        self.path('etc/config/homensai_vpn').write_bytes(b"config main 'main'\n\toption terms_version '2'\n")
        self.assertEqual(self.verify(), (0, ''))
        self.path('etc/config/homensai_vpn').unlink()
        self.assertEqual(self.verify()[0], 0)

    def test_damaged_or_missing_manifest_is_its_own_code(self):
        manifest = self.path(MANIFEST)
        good = manifest.read_bytes()
        for content in (b'', b'\0'*512, b'garbage\n', good.replace(b' 0644 ', b' 644 ', 1),
                        good+b'0'*64+b' 0644 /usr/../etc/shadow\n', good.split(b'\n', 2)[0]+b'\n'):
            manifest.write_bytes(content)
            rc, out = self.verify()
            self.assertEqual((rc, out.split(' ')[0]), (4, 'INTEGRITY-MANIFEST-UNREADABLE'), content[:40])
        manifest.unlink()
        self.assertEqual(self.verify()[0], 4)


@unittest.skipUnless(HAVE_SH, 'needs sh, sha256sum, tar, stat -c, awk, cmp')
class SnapshotTest(ToolCase):
    def test_snapshot_holds_the_verified_files_and_never_the_owner_config(self):
        self.path('etc/config/homensai_vpn').write_bytes(b"config main 'main'\n\toption token 'secret'\n")
        self.assertIn('INTEGRITY-SNAPSHOT-MADE '+build_ipk.VERSION, self.snapshot())
        sha = (self.pristine.parent/'payload.tar.gz.sha256').read_text().split()
        self.assertEqual(sha, [hashlib.sha256(self.pristine.read_bytes()).hexdigest(), 'payload.tar.gz'])
        with tarfile.open(self.pristine) as tar:
            names = sorted(tar.getnames())
        self.assertIn('./'+MANIFEST, names)
        self.assertIn('./usr/lib/homensai-vpn/lua/canon.lua', names)
        self.assertNotIn('./etc/config/homensai_vpn', names)
        self.assertEqual(oct(self.pristine.parent.stat().st_mode & 0o777), '0o700')

    def test_snapshot_of_damaged_files_is_refused_and_keeps_the_old_copy(self):
        self.snapshot()
        before = self.pristine.read_bytes()
        self.path('usr/lib/homensai-vpn/agent.py').write_bytes(b'damaged')
        rc, out = self.run_tool('snapshot')
        self.assertEqual(rc, 8, 'a damaged payload is not a space refusal: postinst must not start it')
        self.assertIn('INTEGRITY-SNAPSHOT-REFUSED INTEGRITY-FILE-DAMAGED /usr/lib/homensai-vpn/agent.py', out)
        self.assertIn('INTEGRITY-PAYLOAD-DAMAGED', out)
        self.assertEqual(self.pristine.read_bytes(), before)

    def test_missing_file_is_a_damaged_payload(self):
        self.snapshot()
        before = self.pristine.read_bytes()
        self.path('usr/lib/homensai-vpn/agent.py').unlink()
        rc, out = self.run_tool('snapshot')
        self.assertEqual(rc, 8, out)
        self.assertIn('INTEGRITY-SNAPSHOT-REFUSED INTEGRITY-FILE-MISSING /usr/lib/homensai-vpn/agent.py', out)
        self.assertIn('INTEGRITY-PAYLOAD-DAMAGED', out)
        self.assertEqual(self.pristine.read_bytes(), before)

    def test_failed_publication_of_the_copy_is_refused_not_made(self):
        # F-19: the rename chain failing used to fall through to INTEGRITY-SNAPSHOT-MADE and exit 0.
        self.snapshot()
        before = self.pristine.read_bytes()
        # mv fails as a shell function in front of the sourced tool (the tool calls mv by name). A fake mv file on PATH
        # cannot run in the offline CI: its tmpfs is mounted noexec, the shell skips the unexecutable fake and the real mv
        # succeeds (INTEGRITY-SNAPSHOT-MADE, exit 0) - a test artefact, not a product fault (router/tests/CI-FIX-NOTE.md).
        result = subprocess.run(['sh', '-c', 'mv() { return 1; }; . "$0"', str(TOOL), 'snapshot'],
                                capture_output=True, text=True, env=self.env, timeout=120)
        rc, out = result.returncode, result.stdout
        self.assertEqual(rc, 7, out)
        self.assertIn('INTEGRITY-SNAPSHOT-REFUSED publish', out)
        self.assertNotIn('INTEGRITY-SNAPSHOT-MADE', out)
        self.assertEqual(self.pristine.read_bytes(), before)
        self.assertFalse(Path(str(self.pristine)+'.new').exists())

    def test_permission_only_difference_is_a_refusal_not_damage(self):
        self.path('usr/lib/homensai-vpn/agent.py').chmod(0o600)
        rc, out = self.run_tool('snapshot')
        if 'INTEGRITY-FILE-MODE' not in out:
            self.skipTest('this file system does not keep POSIX modes')
        self.assertEqual(rc, 7, out)
        self.assertNotIn('INTEGRITY-PAYLOAD-DAMAGED', out)


@unittest.skipUnless(HAVE_SH, 'needs sh, sha256sum, tar, stat -c, awk, cmp')
class BootTest(ToolCase):
    def setUp(self):
        super().setUp()
        self.snapshot()
        self.journal = self.persist/'native-transaction.json'
        self.journal.write_bytes(b'{"broken journal stays as evidence"')
        self.history = self.persist/'native-history.json'
        self.history.write_bytes(b'')
        self.owner = b"config main 'main'\n\toption terms_version '2'\n\toption enabled '1'\n"
        self.path('etc/config/homensai_vpn').write_bytes(self.owner)

    def assert_owner_data_untouched(self):
        self.assertEqual(self.path('etc/config/homensai_vpn').read_bytes(), self.owner)
        self.assertEqual(self.journal.read_bytes(), b'{"broken journal stays as evidence"')
        self.assertEqual(self.history.read_bytes(), b'')

    def test_clean_boot(self):
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code'], report['mode'], report['restored'], report['files']),
                         ('normal', 'INTEGRITY-OK', 'normal', 0, []))
        self.assertEqual(report['version'], build_ipk.VERSION)
        self.assertLessEqual(abs(report['time']-time.time()), 60)

    def test_damaged_files_and_manifest_are_restored_but_never_owner_data(self):
        self.path('usr/lib/homensai-vpn/lua/canon.lua').write_bytes(b'')
        self.path('usr/lib/homensai-vpn/agent.py').unlink()
        os.chmod(self.path('etc/init.d/homensai-vpn'), 0o600)
        mode, report, out = self.boot()
        self.assertEqual((mode, report['code'], report['restored']), ('normal', 'INTEGRITY-RESTORED', 1), out)
        self.assertEqual(sorted(report['files']), ['/etc/init.d/homensai-vpn', '/usr/lib/homensai-vpn/agent.py',
                                                   '/usr/lib/homensai-vpn/lua/canon.lua'])
        self.assertEqual(self.run_tool('verify', str(self.root)), (0, ''))
        self.assertEqual(oct(self.path('etc/init.d/homensai-vpn').stat().st_mode & 0o777), '0o755')
        self.assert_owner_data_untouched()
        self.path(MANIFEST).write_bytes(b'\0'*64)
        self.new_boot()
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code']), ('normal', 'INTEGRITY-RESTORED'))
        self.assertEqual(self.run_tool('verify', str(self.root)), (0, ''))

    def test_without_a_pristine_copy_the_mode_follows_the_damaged_layer(self):
        cases = [(['usr/lib/homensai-vpn/lua/canon.lua'], 'python'),
                 (['usr/lib/homensai-vpn/agent.py'], 'normal'),
                 (['usr/lib/lua/canon_c.so'], 'no-c'),
                 (['www/luci-static/resources/view/homensai-vpn/dashboard9.js'], 'normal'),
                 (['usr/lib/homensai-vpn/lua/canon.lua', 'usr/lib/homensai-vpn/agent.py'], 'stopped'),
                 (['usr/lib/homensai-vpn/inventory.lua'], 'stopped')]
        shutil.rmtree(self.pristine.parent)
        for damaged, expected in cases:
            with self.subTest(damaged=damaged):
                install(self.root, self.ipk)
                self.path('etc/config/homensai_vpn').write_bytes(self.owner)
                for name in damaged:
                    self.path(name).write_bytes(b'damaged')
                mode, report, _ = self.boot()
                self.assertEqual((mode, report['code'], report['mode']), (expected, 'INTEGRITY-SOURCE-MISSING', expected))
                self.assertEqual(sorted(report['files']), sorted('/'+name for name in damaged))
                self.assert_owner_data_untouched()

    def test_a_damaged_pristine_copy_restores_nothing(self):
        self.path('usr/lib/homensai-vpn/lua/canon.lua').write_bytes(b'')
        data = bytearray(self.pristine.read_bytes())
        data[len(data)//2] ^= 0xff
        self.pristine.write_bytes(bytes(data))
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code']), ('python', 'INTEGRITY-SOURCE-DAMAGED'))
        self.assertEqual(self.path('usr/lib/homensai-vpn/lua/canon.lua').read_bytes(), b'')

    def test_a_pristine_copy_of_another_version_restores_nothing(self):
        other = self.tmp/'other'
        install(other, make_ipk(sample_files(), version='9.9.9-1'))
        env = dict(self.env, HOMENSAI_INTEGRITY_ROOT=str(other))
        subprocess.run(['sh', str(TOOL), 'snapshot'], env=env, check=True, capture_output=True, timeout=60)
        self.path('usr/lib/homensai-vpn/lua/canon.lua').write_bytes(b'')
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code']), ('python', 'INTEGRITY-SOURCE-VERSION'))

    def test_no_restore_loop_once_per_boot_and_three_per_day(self):
        canon = self.path('usr/lib/homensai-vpn/lua/canon.lua')
        canon.write_bytes(b'')
        self.assertEqual(self.boot()[1]['code'], 'INTEGRITY-RESTORED')
        canon.write_bytes(b'')
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code']), ('python', 'INTEGRITY-RESTORE-LIMIT'), 'once per boot')
        for _ in range(2):
            self.new_boot()
            self.assertEqual(self.boot()[1]['code'], 'INTEGRITY-RESTORED')
            canon.write_bytes(b'')
        self.new_boot()
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code']), ('python', 'INTEGRITY-RESTORE-LIMIT'), 'three in 24 h')
        self.assertEqual(canon.read_bytes(), b'')
        # a clock set back still counts the "future" restores: the limit only gets stricter
        log = self.persist/'integrity-restores.log'
        log.write_text('\n'.join(str(int(time.time())+86400*5) for _ in range(3))+'\n')
        self.new_boot()
        self.assertEqual(self.boot()[1]['code'], 'INTEGRITY-RESTORE-LIMIT')
        # old entries expire
        log.write_text('\n'.join(str(int(time.time())-86400*2) for _ in range(5))+'\n')
        self.new_boot()
        self.assertEqual(self.boot()[1]['code'], 'INTEGRITY-RESTORED')

    def test_no_check_while_opkg_runs_and_no_check_without_manifest_or_copy(self):
        self.path('usr/lib/homensai-vpn/lua/canon.lua').write_bytes(b'')
        (self.tmp/'opkg.lock').write_text('')
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code']), ('normal', 'INTEGRITY-DEFERRED'))
        self.assertEqual(self.path('usr/lib/homensai-vpn/lua/canon.lua').read_bytes(), b'')
        (self.tmp/'opkg.lock').unlink()
        # F-02: the detached recheck then checks; no service runs here, so nothing is restored or started
        self.assertTrue(self.wait_for(lambda: self.report_code() not in (None, 'INTEGRITY-DEFERRED') and not os.path.lexists(self.recheck_lock)))
        report = json.loads((self.runtime/'integrity.json').read_text())
        self.assertEqual((report['code'], report['mode'], report['files']),
                         ('INTEGRITY-RECHECK-DAMAGED', 'python', ['/usr/lib/homensai-vpn/lua/canon.lua']))
        self.assertEqual(self.path('usr/lib/homensai-vpn/lua/canon.lua').read_bytes(), b'')
        shutil.rmtree(self.pristine.parent)
        self.path(MANIFEST).unlink()
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code']), ('normal', 'INTEGRITY-UNVERIFIED'))

    def test_manual_restore_from_an_ipk(self):
        ipk = self.tmp/'pkg.ipk'
        ipk.write_bytes(self.ipk)
        sha = self.tmp/'pkg.ipk.sha256'
        sha.write_text(hashlib.sha256(self.ipk).hexdigest()+'  pkg.ipk\n')
        self.path('usr/lib/homensai-vpn/agent.py').write_bytes(b'')
        rc, out = self.run_tool('restore', str(ipk), str(sha), str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertIn('INTEGRITY-FILE-RESTORED INTEGRITY-FILE-DAMAGED /usr/lib/homensai-vpn/agent.py', out)
        self.assert_owner_data_untouched()
        sha.write_text('0'*64+'\n')
        self.assertEqual(self.run_tool('restore', str(ipk), str(sha), str(self.root))[0], 5)


RUNNING = 'ubus() { echo \'{"homensai-vpn": {"instances": {"monitor": {"running": true, "pid": 4242}}}}\'; }\n'
NOT_RUNNING = 'ubus() { echo \'{"homensai-vpn": {}}\'; }\n'
# The init script as a shell function (the CI tmpfs is noexec: no fake executable). `restart` runs what the real init's
# start_service runs: the boot self-check, now without the opkg lock.
FAKE_INIT = ('fake_init() { echo "$1" >>"$QA_CALLS"; case "$1" in enabled) return "${QA_ENABLED:-0}" ;;'
             ' restart) sh "$QA_TOOL" boot >/dev/null 2>&1 ;; esac; }\n')


@unittest.skipUnless(HAVE_SH, 'needs sh, sha256sum, tar, stat -c, awk, cmp, readlink')
class RecheckTest(ToolCase):
    """Safety review F-02 (07.11.2026): postinst restarts the service while opkg still holds its lock, so `boot` answers
    INTEGRITY-DEFERRED; `recheck` waits for opkg to end, verifies read-only and writes the real result. Damaged content
    restarts only a running, enabled service (the boot path then restores and decides); it never starts a stopped one."""

    def setUp(self):
        super().setUp()
        self.snapshot()
        self.owner = b"config main 'main'\n\toption terms_version '2'\n\toption enabled '1'\n"
        self.path('etc/config/homensai_vpn').write_bytes(self.owner)
        self.journal = self.persist/'native-transaction.json'
        self.journal.write_bytes(b'{"journal stays"}')
        self.calls = self.tmp/'calls'
        self.env.update(HOMENSAI_INTEGRITY_INIT='fake_init', QA_CALLS=str(self.calls), QA_TOOL=str(TOOL))
        self.deferred()

    def deferred(self):
        """The record a deferred boot leaves (written directly: a real deferred boot launches its own recheck)."""
        self.runtime.mkdir(parents=True, exist_ok=True)
        (self.runtime/'integrity.json').write_text('{"code":"INTEGRITY-DEFERRED","mode":"normal","restored":0,"files":[],'
                                                   '"version":"%s","time":1}\n' % build_ipk.VERSION)

    def recheck(self, stubs=RUNNING, **env):
        result = subprocess.run(['sh', '-c', stubs+FAKE_INIT+'. "$0"', str(TOOL), 'recheck'], capture_output=True,
                                text=True, env=dict(self.env, **env), timeout=120)
        report = json.loads((self.runtime/'integrity.json').read_text())
        return result.returncode, report, result.stdout

    def init_calls(self):
        return self.calls.read_text().split() if self.calls.exists() else []

    def assert_owner_data_untouched(self):
        self.assertEqual(self.path('etc/config/homensai_vpn').read_bytes(), self.owner)
        self.assertEqual(self.journal.read_bytes(), b'{"journal stays"}')

    def test_clean_files_are_reported_ok_and_the_monitor_is_not_restarted(self):
        rc, report, out = self.recheck()
        self.assertEqual((rc, report['code'], report['mode'], report['files']), (0, 'INTEGRITY-OK', 'normal', []))
        self.assertEqual(report['version'], build_ipk.VERSION)
        self.assertLessEqual(abs(report['time']-time.time()), 60)
        self.assertIn('INTEGRITY-RECHECKED INTEGRITY-OK', out)
        self.assertEqual(self.init_calls(), [], 'nothing to restore: no restart')
        self.assertFalse(os.path.lexists(self.recheck_lock))

    def test_permissions_only_or_nothing_to_compare_never_restart(self):
        os.chmod(self.path('etc/init.d/homensai-vpn'), 0o644)
        rc, report, out = self.recheck()
        if report['code'] == 'INTEGRITY-OK':
            self.skipTest('this file system does not keep POSIX modes')
        self.assertEqual((rc, report['code'], report['mode'], report['files']),
                         (0, 'INTEGRITY-MODE-DIFFERS', 'normal', ['/etc/init.d/homensai-vpn']))
        self.deferred()
        shutil.rmtree(self.pristine.parent)
        self.path(MANIFEST).unlink()
        rc, report, out = self.recheck()
        self.assertEqual((rc, report['code'], report['mode']), (0, 'INTEGRITY-UNVERIFIED', 'normal'))
        self.assertEqual(self.init_calls(), [])

    def test_damage_restarts_a_running_service_and_the_boot_path_restores(self):
        canon = self.path('usr/lib/homensai-vpn/lua/canon.lua')
        good = canon.read_bytes()
        canon.write_bytes(b'')
        rc, report, out = self.recheck()
        self.assertEqual(rc, 0, out)
        self.assertIn('INTEGRITY-FILE-DAMAGED /usr/lib/homensai-vpn/lua/canon.lua', out)
        self.assertIn('INTEGRITY-RECHECK-DAMAGED: files damaged after the installation; the service restarts', out)
        self.assertEqual(self.init_calls(), ['enabled', 'restart'])
        # the result is the one the restarted service's boot self-check wrote, with the existing consequences
        self.assertEqual((report['code'], report['mode'], report['restored'], report['files']),
                         ('INTEGRITY-RESTORED', 'normal', 1, ['/usr/lib/homensai-vpn/lua/canon.lua']))
        self.assertEqual(canon.read_bytes(), good)
        self.assert_owner_data_untouched()
        self.assertFalse(os.path.lexists(self.recheck_lock))

    def test_damage_never_starts_a_stopped_or_disabled_service(self):
        for name in ('usr/lib/homensai-vpn/lua/canon.lua', 'usr/lib/homensai-vpn/agent.py'):
            self.path(name).write_bytes(b'damaged')
        for label, stubs, env, calls in (('not running', NOT_RUNNING, {}, ['enabled']),
                                         ('disabled', RUNNING, {'QA_ENABLED': '1'}, ['enabled']),
                                         ('no init script', RUNNING, {'HOMENSAI_INTEGRITY_INIT': str(self.tmp/'none')}, [])):
            with self.subTest(label):
                self.deferred()
                self.calls.unlink(missing_ok=True)
                rc, report, out = self.recheck(stubs, **env)
                self.assertEqual(rc, 0, out)
                self.assertEqual(self.init_calls(), calls, 'no restart, no start')
                self.assertEqual((report['code'], report['mode'], report['restored']), ('INTEGRITY-RECHECK-DAMAGED', 'stopped', 0))
                self.assertEqual(sorted(report['files']), ['/usr/lib/homensai-vpn/agent.py', '/usr/lib/homensai-vpn/lua/canon.lua'])
                self.assertEqual(self.path('usr/lib/homensai-vpn/agent.py').read_bytes(), b'damaged', 'read-only')
                self.assert_owner_data_untouched()
        # the mode reaches the existing Start refusal (BH-04, both twins read only `mode`)
        sys.path.insert(0, str(ROUTER/'files'/'usr'/'lib'/'homensai-vpn'))
        import auto_control
        self.assertEqual(auto_control.integrity_blocker(self.runtime), 'INTEGRITY-AUTO-BLOCKED')

    def test_a_real_result_written_meanwhile_is_never_overwritten(self):
        self.path('usr/lib/homensai-vpn/lua/canon.lua').write_bytes(b'')
        later = '{"code":"INTEGRITY-RESTORE-LIMIT","mode":"python","restored":0,"files":[],"version":"x","time":2}\n'
        (self.runtime/'integrity.json').write_text(later)
        rc, _, _ = self.recheck()
        self.assertEqual(rc, 0)
        self.assertEqual((self.runtime/'integrity.json').read_text(), later)
        self.assertEqual(self.init_calls(), [], 'a later service start already decided')

    def test_one_recheck_at_a_time_and_a_dead_holder_is_replaced(self):
        os.symlink(str(os.getpid()), self.recheck_lock)               # a live recheck already waits
        rc, report, _ = self.recheck()
        self.assertEqual((rc, report['code']), (0, 'INTEGRITY-DEFERRED'))
        self.assertEqual(os.readlink(self.recheck_lock), str(os.getpid()))
        os.unlink(self.recheck_lock)
        dead = subprocess.Popen(['sh', '-c', 'exit 0'])
        dead.wait()
        for holder in (str(dead.pid), 'garbage'):
            with self.subTest(holder=holder):
                self.deferred()
                os.symlink(holder, self.recheck_lock)
                rc, report, _ = self.recheck()
                self.assertEqual((rc, report['code']), (0, 'INTEGRITY-OK'))
                self.assertFalse(os.path.lexists(self.recheck_lock))

    def test_it_waits_for_opkg_and_gives_up_after_the_limit(self):
        lock = self.tmp/'opkg.lock'
        lock.write_text('')
        started = time.monotonic()
        rc, report, out = self.recheck(HOMENSAI_INTEGRITY_RECHECK_LIMIT='2')
        self.assertGreaterEqual(time.monotonic()-started, 1.5)
        self.assertEqual((rc, report['code'], report['mode']), (0, 'INTEGRITY-RECHECK-TIMEOUT', 'normal'))
        self.assertIn('INTEGRITY-RECHECK-TIMEOUT: opkg still holds its lock after 2 s', out)
        self.assertEqual(self.init_calls(), [])
        # waiting: nothing is decided while the lock is held, the check runs as soon as it is gone
        self.deferred()
        waiting = subprocess.Popen(['sh', '-c', RUNNING+FAKE_INIT+'. "$0"', str(TOOL), 'recheck'], env=self.env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(2.5)
            self.assertIsNone(waiting.poll())
            self.assertEqual(self.report_code(), 'INTEGRITY-DEFERRED')
            lock.unlink()
            self.assertEqual(waiting.wait(timeout=30), 0)
        finally:
            if waiting.poll() is None:
                waiting.kill()
        self.assertEqual(self.report_code(), 'INTEGRITY-OK')

    def test_a_deferred_boot_launches_the_recheck_detached(self):
        lock = self.tmp/'opkg.lock'
        lock.write_text('')
        self.env['HOMENSAI_INTEGRITY_INIT'] = str(self.tmp/'none')     # a launched recheck has no shell stubs
        started = time.monotonic()
        mode, report, _ = self.boot()
        self.assertLess(time.monotonic()-started, 20, 'the init does not wait for the recheck')
        self.assertEqual((mode, report['code']), ('normal', 'INTEGRITY-DEFERRED'))
        self.assertTrue(self.wait_for(lambda: os.path.lexists(self.recheck_lock)), 'the recheck waits for opkg')
        time.sleep(1.5)
        self.assertEqual(self.report_code(), 'INTEGRITY-DEFERRED')
        lock.unlink()
        self.assertTrue(self.wait_for(lambda: self.report_code() == 'INTEGRITY-OK' and not os.path.lexists(self.recheck_lock)))
        # a second deferred boot while one recheck waits starts no second one
        lock.write_text('')
        self.boot()
        self.assertTrue(self.wait_for(lambda: os.path.lexists(self.recheck_lock)))
        first = os.readlink(self.recheck_lock)
        self.boot()
        time.sleep(1.5)
        self.assertEqual(os.readlink(self.recheck_lock), first)
        lock.unlink()
        self.assertTrue(self.wait_for(lambda: self.report_code() == 'INTEGRITY-OK' and not os.path.lexists(self.recheck_lock)))

    def test_the_launch_is_detached_and_documented(self):
        text = TOOL.read_text()
        self.assertIn('sh "$SELF" recheck </dev/null >/dev/null 2>&1 &', text)
        self.assertIn('| boot | recheck |', text)


@unittest.skipUnless(HAVE_SH, 'needs sh, sha256sum, tar, awk, cmp')
class UpgradeRollbackTest(ToolCase):
    """Owner decision 07.11.2026: a damaged or unverified package on upgrade rolls back to the previous working version
    (the pristine copy the last good installation saved), starts it and records the reason for the page; without a
    previous copy the service stays off with the reason. The owner's config, journal and history are never written."""
    NEW = '9.9.9-alpha99'

    def setUp(self):
        super().setUp()
        self.snapshot()                                   # the previous, working version keeps its pristine copy
        self.old_files = {name: payload for name, payload, _ in self.files()}
        self.old_manifest = self.path(MANIFEST).read_bytes()
        newer = [(name, payload + b'# new\n' if name.endswith('.py') else payload, mode) for name, payload, mode in self.files()]
        newer.append(('usr/lib/homensai-vpn/lua/only_new.lua', b'return 2\n', 0o644))
        install(self.root, make_ipk(newer, self.NEW))     # opkg unpacks the new version over it
        self.owner = b"config main 'main'\n\toption terms_version '2'\n\toption enabled '1'\n"
        self.path('etc/config/homensai_vpn').write_bytes(self.owner)
        self.journal = self.persist/'native-transaction.json'
        self.journal.write_bytes(b'{"journal stays"}')
        self.env.update(HOMENSAI_ROLLBACK_ROOT=str(self.root), HOMENSAI_ROLLBACK_PERSIST=str(self.persist))
        # BH-02: preinst recorded the version that was running before this upgrade (the previous one)
        (self.persist/'upgrade-from').write_text(build_ipk.VERSION+'\n')

    def rollback(self, reason='INTEGRITY-PAYLOAD-DAMAGED'):
        from package_hooks import ROLLBACK_SCRIPT
        result = subprocess.run(['sh', '-s', reason], input=ROLLBACK_SCRIPT, capture_output=True, text=True, env=self.env, timeout=120)
        record = self.persist/'upgrade-result.json'
        return result.returncode, (json.loads(record.read_text()) if record.exists() else None)

    def assert_owner_data_untouched(self):
        self.assertEqual(self.path('etc/config/homensai_vpn').read_bytes(), self.owner)
        self.assertEqual(self.journal.read_bytes(), b'{"journal stays"}')

    def test_a_damaged_new_version_rolls_back_to_the_previous_one(self):
        self.path('usr/lib/homensai-vpn/lua/canon.lua').write_bytes(b'')          # the damage the snapshot found
        rc, record = self.rollback()
        self.assertEqual(rc, 0)
        self.assertEqual({k: record[k] for k in ('code', 'reason', 'from', 'to')},
                         {'code': 'UPGRADE-ROLLED-BACK', 'reason': 'INTEGRITY-PAYLOAD-DAMAGED', 'from': self.NEW, 'to': build_ipk.VERSION})
        for name, payload in self.old_files.items():
            if name != 'etc/config/homensai_vpn':
                self.assertEqual(self.path(name).read_bytes(), payload, name)
        self.assertEqual(self.path(MANIFEST).read_bytes(), self.old_manifest)
        self.assertEqual(oct(self.path('etc/init.d/homensai-vpn').stat().st_mode & 0o777), '0o755')
        self.assertEqual(self.run_tool('verify', str(self.root)), (0, ''), 'the previous version verifies as installed')
        self.assert_owner_data_untouched()
        self.assertFalse(list(self.root.rglob('*.rollback-new')))

    def test_an_unverified_helper_rolls_back_the_same_way(self):
        self.path('usr/lib/homensai-vpn/agent.py').unlink()
        rc, record = self.rollback('INTEGRITY-HELPER-FAILED')
        self.assertEqual((rc, record['code'], record['reason']), (0, 'UPGRADE-ROLLED-BACK', 'INTEGRITY-HELPER-FAILED'))
        self.assertEqual(self.path('usr/lib/homensai-vpn/agent.py').read_bytes(), self.old_files['usr/lib/homensai-vpn/agent.py'])
        rc, record = self.rollback('$(reboot)')                                      # an unknown reason is never echoed
        self.assertEqual(record['reason'], 'INTEGRITY-HELPER-FAILED')

    def test_without_a_previous_copy_nothing_is_touched_and_the_reason_is_recorded(self):
        before = self.path('usr/lib/homensai-vpn/agent.py').read_bytes()
        self.pristine.unlink()
        rc, record = self.rollback()
        self.assertEqual((rc, record['code'], record['to']), (5, 'UPGRADE-ROLLBACK-UNAVAILABLE', ''))
        self.assertEqual(self.path('usr/lib/homensai-vpn/agent.py').read_bytes(), before)
        self.assert_owner_data_untouched()

    def test_a_damaged_previous_copy_is_never_used(self):
        before = self.path('usr/lib/homensai-vpn/agent.py').read_bytes()
        data = bytearray(self.pristine.read_bytes())
        data[len(data)//2] ^= 0xff
        self.pristine.write_bytes(bytes(data))
        rc, record = self.rollback()
        self.assertEqual((rc, record['code']), (5, 'UPGRADE-ROLLBACK-UNAVAILABLE'))
        self.assertEqual(self.path('usr/lib/homensai-vpn/agent.py').read_bytes(), before)

    def test_bh02_only_the_version_that_was_running_is_restored(self):
        # bug hunt 07.11.2026: a pristine copy older than the running version (snapshot exit 7 kept it) is never used
        before = self.path('usr/lib/homensai-vpn/agent.py').read_bytes()
        for recorded in ('2.0.0-alpha1-1\n', None, '$(reboot)\n'):
            with self.subTest(recorded=recorded):
                if recorded is None:(self.persist/'upgrade-from').unlink()
                else:(self.persist/'upgrade-from').write_text(recorded)
                rc, record = self.rollback()
                self.assertEqual((rc, record['code'], record['to']), (5, 'UPGRADE-ROLLBACK-UNAVAILABLE', ''))
                self.assertEqual(self.path('usr/lib/homensai-vpn/agent.py').read_bytes(), before, 'nothing copied')
                self.assert_owner_data_untouched()

    def hook_part(self, name, end, tail):
        """The first part of a hook with its absolute paths moved into the fake root."""
        from package_hooks import scripts
        body = scripts()[name]
        body = body[:body.index(end)] if end else body
        return (body.replace('/usr/lib/homensai-vpn/integrity.sha256', str(self.path(MANIFEST)))
                .replace('/etc/homensai-vpn', str(self.persist)).replace('/etc/config/homensai_vpn', str(self.tmp/'no-config'))
                .replace('[ -x /usr/bin/python3 ]', '[ -x /bin/sh ]').replace('/usr/bin/python3', 'true')+tail)

    def test_bh02_preinst_records_the_running_version(self):
        (self.persist/'upgrade-from').unlink()
        self.path(MANIFEST).write_text('# homensai-auto-vpn payload manifest v1\n# version 2.1.0-alpha8-1\n')
        result = subprocess.run(['sh', '-c', self.hook_part('preinst', None, '')], capture_output=True, text=True, timeout=30,
                                env=dict(self.env, IPKG_INSTROOT=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.persist/'upgrade-from').read_text(), '2.1.0-alpha8-1\n')
        self.path(MANIFEST).unlink()                           # a first install: nothing to roll back to
        subprocess.run(['sh', '-c', self.hook_part('preinst', None, '')], check=True, timeout=30, env=dict(self.env, IPKG_INSTROOT=''))
        self.assertFalse((self.persist/'upgrade-from').exists())

    def test_bh03_a_later_postinst_run_over_the_rolled_back_files_refuses(self):
        # bug hunt 07.11.2026: opkg keeps the rolled-back package unpacked; a later configure runs its postinst again
        from package_hooks import package_version
        new = package_version()
        trap_marker = self.persist/'maintenance.json'
        def run(installed, result):
            self.path(MANIFEST).write_text('# homensai-auto-vpn payload manifest v1\n# version %s\n' % installed)
            record = self.persist/'upgrade-result.json'
            if result is None:
                if record.exists():record.unlink()
            else:record.write_text(json.dumps(result, separators=(',', ':')))
            trap_marker.write_text('{}')
            body = self.hook_part('postinst', '/usr/bin/python3 - prepare', 'echo PASSED\n')
            return subprocess.run(['sh', '-c', body], capture_output=True, text=True, timeout=30, env=dict(self.env, IPKG_INSTROOT=''))
        rolled = {'code': 'UPGRADE-ROLLED-BACK', 'reason': 'INTEGRITY-PAYLOAD-DAMAGED', 'from': new, 'to': '2.1.0-alpha8-1', 'time': 1}
        result = run('2.1.0-alpha8-1', rolled)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('PASSED', result.stdout)
        self.assertIn('UPGRADE-NOT-INSTALLED', result.stderr)
        self.assertEqual(json.loads((self.persist/'upgrade-result.json').read_text()), rolled, 'the reason stays for the page')
        self.assertFalse(trap_marker.exists(), 'the maintenance marker still ends with postinst')
        # opkg install --force-reinstall unpacked the new files again; another package was rolled back; no record
        for installed, record in ((new, rolled), ('2.1.0-alpha8-1', dict(rolled, **{'from': '9.9.9-alpha1-1'})),
                                  ('2.1.0-alpha8-1', None), ('2.1.0-alpha8-1', dict(rolled, code='UPGRADE-ROLLBACK-FAILED'))):
            with self.subTest(installed=installed, record=record):
                result = run(installed, record)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('PASSED', result.stdout)

    def test_bh03_the_sdk_hooks_carry_the_make_version_not_a_literal(self):
        from package_hooks import sdk_fragment
        text = sdk_fragment()
        self.assertIn("package_version='$(PKG_VERSION)-$(PKG_RELEASE)'", text)
        self.assertNotIn(build_ipk.VERSION, text)
        self.assertIn('lifecycle_scripts(VERSION)', (ROUTER/'build_ipk.py').read_text())

    def postinst_rollback(self, reason):
        """postinst's rollback_and_start with the init script, rpcd and luci_cache replaced by a recorder."""
        from package_hooks import scripts
        post = scripts()['postinst']
        start = post.index('rollback_and_start() {')
        end = '\n    exit 1\n}\n'
        function = post[start:post.index(end, start)+len(end)]
        calls = self.tmp/'calls'
        function = (function.replace('/etc/init.d/homensai-vpn ', 'rec init ').replace('/etc/init.d/rpcd ', 'rec rpcd ')
                    .replace('/usr/bin/python3 ', 'rec python3 '))
        body = 'set -eu\nrec() { echo "$*" >>"%s"; }\n%s\nrollback_and_start %s\necho NOT-REACHED\n' % (calls, function, reason)
        result = subprocess.run(['sh', '-c', body], capture_output=True, text=True, env=self.env, timeout=120)
        return result, (calls.read_text().splitlines() if calls.exists() else [])

    def test_postinst_starts_the_rolled_back_version_and_reports_failure(self):
        result, calls = self.postinst_rollback('INTEGRITY-PAYLOAD-DAMAGED')
        self.assertEqual(result.returncode, 1, 'the new package is not installed: the operation fails')
        self.assertNotIn('NOT-REACHED', result.stdout)
        self.assertIn('UPGRADE-ROLLED-BACK', result.stderr)
        self.assertEqual(calls, ['init enable', 'init restart', 'rpcd reload', 'python3 /usr/lib/homensai-vpn/luci_cache.py'])
        # nothing in the rollback touches the Auto intent: Auto resumes only from an owner-started intent on disk
        from package_hooks import ROLLBACK_SCRIPT
        for word in ('auto-control', 'native_start', 'native-stop', 'pair-auto'):
            self.assertNotIn(word, ROLLBACK_SCRIPT)

    def test_postinst_without_a_previous_copy_keeps_the_service_off(self):
        self.pristine.unlink()
        result, calls = self.postinst_rollback('INTEGRITY-PAYLOAD-DAMAGED')
        self.assertEqual((result.returncode, calls), (1, []))
        self.assertIn('UPGRADE-ROLLBACK-UNAVAILABLE', result.stderr)


@unittest.skipUnless(HAVE_SH, 'needs sh, sha256sum, tar, stat -c, awk, cmp')
class RealPayloadTest(ToolCase):
    """The real 2.0.0 payload (all ~175 files): snapshot, a damaged Lua module, boot restores it."""
    files = staticmethod(build_ipk.selected_source_files)

    def test_real_payload_round_trip(self):
        self.snapshot()
        size = self.pristine.stat().st_size
        self.assertLess(size, 2*1024*1024)
        target = self.path('usr/lib/homensai-vpn/lua/transaction.lua')
        good = target.read_bytes()
        target.write_bytes(good[:len(good)//2])
        started = time.monotonic()
        mode, report, _ = self.boot()
        self.assertEqual((mode, report['code'], report['files']), ('normal', 'INTEGRITY-RESTORED', ['/usr/lib/homensai-vpn/lua/transaction.lua']))
        self.assertEqual(target.read_bytes(), good)
        self.assertLess(time.monotonic()-started, 60)
        started = time.monotonic()
        self.assertEqual(self.run_tool('verify', str(self.root)), (0, ''))
        print('\n  real payload: pristine copy %d bytes, verify %.2f s on this host' % (size, time.monotonic()-started))


INIT_STUBS = '''
chmod() { :; }
logger() { printf 'LOG %s\\n' "$*" >>"$QA_LOG"; }
config_load() { CONFIG_main_monitor_only=0; }
config_get_bool() { eval "$1=1"; }
config_get() { eval "$1=\\${4}"; }
procd_open_instance() { printf 'OPEN %s\\n' "$1"; }
procd_set_param() { printf 'PARAM %s\\n' "$*"; }
procd_close_instance() { printf 'CLOSE\\n'; }
ubus() { :; }
jsonfilter() { cat >/dev/null; printf 'glinet,mt3000-snand\\n'; }
start_service
'''


@unittest.skipUnless(HAVE_SH, 'needs sh, sha256sum, tar, awk')
class InitGateTest(unittest.TestCase):
    """start_service with the integrity gate: the tool path, manifest and pristine copy point into a temp dir."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def start(self, tool_text=None, manifest=None, pristine=None, core=False):
        script = INIT.read_text()
        tool = self.tmp/'homensai-vpn-integrity'
        if tool_text is not None:
            tool.write_text(tool_text)
        body = script.split('\n', 1)[1]
        body = body.replace('tool=/usr/sbin/homensai-vpn-integrity', 'tool=%s' % tool)
        body = body.replace('manifest=/usr/lib/homensai-vpn/integrity.sha256', 'manifest=%s' % (manifest or self.tmp/'none'))
        body = body.replace('pristine=/etc/homensai-vpn/pristine/payload.tar.gz', 'pristine=%s' % (pristine or self.tmp/'none.tar.gz'))
        body = body.replace('report=/var/run/homensai-vpn/integrity.json', 'report=%s' % (self.tmp/'run'/'integrity.json'))
        if core:
            body = body.replace('${CONFIG_main_lua_core_process:-0}', '1')
        # every Lua file and /usr/bin/lua present, as on the router
        body = re.sub(r'\[ -f /usr/lib/homensai-vpn/lua/[a-z_]+\.lua \]', '[ -f /bin/sh ]', body.replace('[ -x /usr/bin/lua ]', '[ -x /bin/sh ]'))
        body = body.replace('rm -f /var/run/homensai-vpn/lua-monitor.ready', ':')
        log = self.tmp/'syslog'
        log.write_text('')
        result = subprocess.run(['sh', '-c', body+INIT_STUBS], capture_output=True, text=True, timeout=60,
                                env=dict(os.environ, QA_LOG=str(log)))
        self.assertEqual(result.returncode, 0, result.stderr)
        instances = {}
        for block in result.stdout.split('OPEN ')[1:]:
            name, rest = block.split('\n', 1)
            instances[name] = [line[6:] for line in rest.splitlines() if line.startswith('PARAM ')]
        return instances, result.stderr+log.read_text()

    @staticmethod
    def fake(mode):
        return '#!/bin/sh\n[ "$1" = boot ] && echo "INTEGRITY-SOMETHING /x" && echo mode=%s\n' % mode

    def command(self, instances, name):
        return next(p for p in instances[name] if p.startswith('command '))

    def test_normal_starts_lua_as_before(self):
        instances, _ = self.start(self.fake('normal'))
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))
        self.assertIn('lua/auto.lua daemon', self.command(instances, 'native'))
        self.assertFalse(any('HOMENSAI_CANON_C' in p for ps in instances.values() for p in ps))

    def test_without_the_tool_monitoring_runs_but_auto_is_not_started(self):
        """Owner decision 07.11.2026: a missing self-check tool means an unverified installation. The page and the
        monitor keep working; no Auto supervisor (Lua or Python native instance, nor hv-core) is started; the reason is
        logged and published for the page with the fix."""
        instances, err = self.start(None)
        self.assertEqual(sorted(instances), ['monitor'])
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))
        self.assertIn('INTEGRITY-TOOL-MISSING', err)
        self.assertIn('Auto is not started; reinstall the package', err)
        report = json.loads((self.tmp/'run'/'integrity.json').read_text())
        self.assertEqual((report['code'], report['mode'], report['files']),
                         ('INTEGRITY-TOOL-MISSING', 'no-auto', ['/usr/sbin/homensai-vpn-integrity']))
        # hv-core would run the Auto supervisor inside the monitor process: the plain Lua monitor runs instead
        instances, _ = self.start(None, core=True)
        self.assertEqual(sorted(instances), ['monitor'])
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))
        # with the tool present hv-core is still chosen as before (the stub proves the switch is reachable)
        instances, _ = self.start(self.fake('normal'), core=True)
        self.assertIn('hv_core.lua daemon', self.command(instances, 'monitor'))
        self.assertIn('hv_core.lua standby', self.command(instances, 'native'))

    def test_python_mode_runs_both_python_layers(self):
        instances, _ = self.start(self.fake('python'))
        self.assertIn('/usr/bin/python3 /usr/lib/homensai-vpn/agent.py daemon', self.command(instances, 'monitor'))
        self.assertIn('/usr/bin/python3 /usr/lib/homensai-vpn/native_switch.py daemon', self.command(instances, 'native'))

    def test_no_c_mode_turns_the_c_module_off_in_lua(self):
        instances, _ = self.start(self.fake('no-c'))
        self.assertIn('env HOMENSAI_CANON_C=0', instances['monitor'])
        self.assertTrue(any(p.startswith('env TZ=') and p.endswith('HOMENSAI_CANON_C=0') for p in instances['native']), instances['native'])

    def test_stopped_mode_opens_no_instance(self):
        instances, err = self.start(self.fake('stopped'))
        self.assertEqual(instances, {})
        self.assertIn('INTEGRITY-SERVICE-STOPPED', err)

    def test_a_crashing_tool_never_blocks_the_monitor_but_never_starts_auto(self):
        # BH-01 (bug hunt 07.11.2026): no usable answer is not a verified installation: monitoring only, the reason published
        for tool in ('#!/bin/sh\nexit 3\n', '#!/bin/sh\necho mode=weird\n', '#!/bin/sh\necho hello\n'):
            with self.subTest(tool=tool):
                instances, err = self.start(tool)
                self.assertEqual(sorted(instances), ['monitor'])
                self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))
                self.assertIn('INTEGRITY-TOOL-FAILED', err)
                report = json.loads((self.tmp/'run'/'integrity.json').read_text())
                self.assertEqual((report['code'], report['mode']), ('INTEGRITY-TOOL-FAILED', 'no-auto'))
        instances, _ = self.start('#!/bin/sh\nexit 3\n', core=True)
        self.assertEqual(sorted(instances), ['monitor'])
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'), 'no hv-core with the Auto supervisor inside')

    def test_a_damaged_tool_is_put_back_from_the_pristine_copy_or_skipped(self):
        good = self.fake('python')
        manifest = self.tmp/'integrity.sha256'
        manifest.write_text('# homensai-auto-vpn payload manifest v1\n%s 0755 /usr/sbin/homensai-vpn-integrity\n'
                            % hashlib.sha256(good.encode()).hexdigest())
        stage = self.tmp/'stage'
        (stage/'usr'/'sbin').mkdir(parents=True)
        (stage/'usr'/'sbin'/'homensai-vpn-integrity').write_text(good)
        pristine = self.tmp/'payload.tar.gz'
        subprocess.run(['tar', '-czf', str(pristine), '-C', str(stage), './usr/sbin/homensai-vpn-integrity'], check=True)
        (self.tmp/'payload.tar.gz.sha256').write_text(hashlib.sha256(pristine.read_bytes()).hexdigest()+'  payload.tar.gz\n')
        instances, err = self.start('#!/bin/sh\necho mode=stopped\n', manifest, pristine)
        self.assertIn('INTEGRITY-TOOL-DAMAGED', err)
        self.assertIn('INTEGRITY-FILE-RESTORED', err)
        self.assertEqual((self.tmp/'homensai-vpn-integrity').read_text(), good)
        self.assertIn('python3', self.command(instances, 'monitor'), 'the restored tool decided')
        # damaged copy: the damaged tool is not run; BH-01 (bug hunt 07.11.2026): nothing is verified, so monitoring
        # only - never the full Auto the old 'normal' answer started - and the reason is published
        (self.tmp/'homensai-vpn-integrity').write_text('#!/bin/sh\necho mode=stopped\n')
        (self.tmp/'payload.tar.gz.sha256').write_text('0'*64+'\n')
        instances, err = self.start(None, manifest, pristine)
        self.assertEqual(sorted(instances), ['monitor'])
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))
        self.assertEqual((self.tmp/'homensai-vpn-integrity').read_text(), '#!/bin/sh\necho mode=stopped\n')
        report = json.loads((self.tmp/'run'/'integrity.json').read_text())
        self.assertEqual((report['code'], report['mode']), ('INTEGRITY-TOOL-DAMAGED', 'no-auto'))


class StatusFieldTest(unittest.TestCase):
    def test_both_monitors_publish_the_integrity_report(self):
        agent = (ROUTER/'files/usr/lib/homensai-vpn/agent.py').read_text()
        self.assertIn("status['integrity']=read_json(RUNTIME/'integrity.json',None)", agent)
        monitor = (LUA_SRC/'monitor.lua').read_text()
        self.assertIn("status.integrity=self:read_json(self.runtime..'/integrity.json',NULL)", monitor)
        # the persistent upgrade outcome (rolled back / refused) is published by both twins for the red reason line
        self.assertIn("status['upgrade_result']=read_json(PERSIST/'upgrade-result.json',None)", agent)
        self.assertIn("status.upgrade_result=self:read_json(self.persist..'/upgrade-result.json',NULL)", monitor)

    def test_every_upgrade_code_has_a_bilingual_row_and_the_page_shows_it_red(self):
        from package_hooks import ROLLBACK_SCRIPT, scripts
        codes = set(re.findall(r'(?<![A-Z-])UPGRADE-[A-Z]+(?:-[A-Z]+)*', ROLLBACK_SCRIPT+scripts()['postinst']))  # not LIFECYCLE-UPGRADE-READY
        self.assertEqual(codes, {'UPGRADE-ROLLED-BACK', 'UPGRADE-ROLLBACK-UNAVAILABLE', 'UPGRADE-ROLLBACK-FAILED',
                                 'UPGRADE-ROLLBACK-VERSION', 'UPGRADE-NOT-INSTALLED'})  # BH-02, BH-03
        table = (ROUTER/'error_table.inc.js').read_text(encoding='utf8')
        for code in codes | {'INTEGRITY-TOOL-MISSING'}:
            row = re.search(r"\['%s','service','([^']+)','([^']+)','([^']+)','([^']+)','([^']+)','([^']+)'\]" % code, table)
            self.assertIsNotNone(row, code)
            self.assertRegex(row.group(2)+row.group(4)+row.group(6), '[а-я]', code+': Russian text')
        self.assertIn('reinstall the package', table.split("['INTEGRITY-TOOL-MISSING'", 1)[1].split('\n', 1)[0].lower())
        views = (ROUTER/'ui'/'views.js').read_text(encoding='utf8')
        self.assertIn('function integrityBanner()', views)
        self.assertIn('upgrade_result', views)

    def test_every_code_of_the_tool_has_a_row_in_the_error_table(self):
        codes = set(re.findall(r'INTEGRITY-[A-Z]+(?:-[A-Z]+)*', TOOL.read_text()+INIT.read_text()))
        codes -= {'INTEGRITY-SOMETHING', 'INTEGRITY-MATRIX'}  # a test stub; the design document's name
        table = (ROUTER/'error_table.inc.js').read_text(encoding='utf8')
        rows = set(re.findall(r"\['(INTEGRITY-[A-Z-]+)','service'", table))
        self.assertEqual(sorted(codes-rows), [])


def lua(code, *, cpath=None, path=None):
    lua_path = (path or str(LUA_SRC))+'/?.lua;;'
    prelude = "package.path=%r package.cpath=%r..package.cpath " % (lua_path, (cpath+'/?.so;') if cpath else '')
    result = subprocess.run([LUA, '-e', prelude+code], capture_output=True, text=True, timeout=60)
    return result.returncode, result.stdout.strip(), result.stderr


@unittest.skipUnless(LUA, 'needs lua5.1')
class LuaLayerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.lua = self.tmp/'lua'
        shutil.copytree(LUA_SRC, self.lua)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_canon_c_wrong_architecture_or_garbage_falls_back_to_pure_lua(self):
        cdir = self.tmp/'c'
        cdir.mkdir()
        for label, payload in (('shipped aarch64 module on this host', CANON_C.read_bytes()),
                               ('zero bytes', b''), ('garbage', b'\x7fELF'+b'\0'*100)):
            with self.subTest(label):
                (cdir/'canon_c.so').write_bytes(payload)
                rc, out, err = lua("local c=require('canon') print(tostring(c.c_module)..' '..c.encode(c.object({a=1})))",
                                   cpath=str(cdir), path=str(self.lua))
                self.assertEqual((rc, out), (0, 'nil {"a":1}'), err)

    def test_finding_zero_byte_module_loads_as_true(self):
        # Lua's require() accepts an empty chunk: the damage shows only at the first use (the checksum catches it)
        (self.lua/'terms.lua').write_bytes(b'')
        rc, out, _ = lua("print(tostring(require('terms')))", path=str(self.lua))
        self.assertEqual((rc, out), (0, 'true'))

    def test_finding_one_changed_byte_can_change_behaviour_silently(self):
        text = (self.lua/'terms.lua').read_bytes()
        self.assertIn(b"return '2'", text)
        (self.lua/'terms.lua').write_bytes(text.replace(b"return '2'", b"return '3'"))
        rc, out, _ = lua("print(require('terms'))", path=str(self.lua))
        self.assertEqual((rc, out), (0, '3'))


SANDBOX = os.environ.get('HOMENSAI_FAULT_SANDBOX') == '1' and Path('/.dockerenv').exists()


@unittest.skipUnless(LUA and SANDBOX, 'needs lua5.1 and HOMENSAI_FAULT_SANDBOX=1 in a throw-away container')
class AutoDaemonLoadErrorTest(unittest.TestCase):
    """The Lua Auto daemon with a module of its load path truncated: LUA-AUTO-LOAD-FAILED hands over to Python."""
    INSTALL = Path('/usr/lib/homensai-vpn')

    def test_a_load_error_hands_over_to_python(self):
        for directory in (self.INSTALL, Path('/var/run/homensai-vpn'), Path('/etc/homensai-vpn')):
            shutil.rmtree(directory, ignore_errors=True)
        shutil.copytree(ROUTER/'files'/'usr'/'lib'/'homensai-vpn', self.INSTALL)
        Path('/etc/homensai-vpn').mkdir(parents=True)
        target = self.INSTALL/'lua'/'transaction.lua'
        target.write_bytes(target.read_bytes()[:len(target.read_bytes())//2])
        result = subprocess.run(['timeout', '8', LUA, str(self.INSTALL/'lua'/'auto.lua'), 'daemon'], capture_output=True,
                                text=True, env=dict(os.environ, LUA_PATH=str(self.INSTALL/'lua')+'/?.lua;;'))
        self.assertIn('LUA-AUTO-LOAD-FAILED', result.stderr)


if __name__ == '__main__':
    unittest.main()
