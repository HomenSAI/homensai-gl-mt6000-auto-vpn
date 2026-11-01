"""Self-check and self-restore of the installed program files (TODO item 15; INTEGRITY-MATRIX-2026-11-01.ru.md).

1. The payload manifest (build_ipk) ships in the package, in both builders.
2. /usr/sbin/homensai-vpn-integrity: verify / snapshot / boot / restore against damaged, missing and re-moded files,
   a damaged manifest, a damaged or foreign pristine copy, the restore-loop limits and an opkg run; the owner's
   config, terms, journal and history are never written. Needs sh, sha256sum, tar, `stat -c`, awk.
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
        self.assertLess(snap, post.index('/etc/init.d/homensai-vpn restart'))
        self.assertIn('|| echo INTEGRITY-SNAPSHOT-REFUSED', post, 'a refused copy never fails the installation')
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
        self.env = dict(os.environ, HOMENSAI_INTEGRITY_ROOT=str(self.root), HOMENSAI_INTEGRITY_RUNTIME=str(self.runtime),
                        HOMENSAI_INTEGRITY_PERSIST=str(self.persist), HOMENSAI_INTEGRITY_OPKG_LOCK=str(self.tmp/'opkg.lock'),
                        TMPDIR=str(self.tmp))
        self.pristine = self.persist/'pristine'/'payload.tar.gz'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

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
        self.assertEqual(rc, 7)
        self.assertIn('INTEGRITY-SNAPSHOT-REFUSED INTEGRITY-FILE-DAMAGED /usr/lib/homensai-vpn/agent.py', out)
        self.assertEqual(self.pristine.read_bytes(), before)


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

    def start(self, tool_text=None, manifest=None, pristine=None):
        script = INIT.read_text()
        tool = self.tmp/'homensai-vpn-integrity'
        if tool_text is not None:
            tool.write_text(tool_text)
        body = script.split('\n', 1)[1]
        body = body.replace('tool=/usr/sbin/homensai-vpn-integrity', 'tool=%s' % tool)
        body = body.replace('manifest=/usr/lib/homensai-vpn/integrity.sha256', 'manifest=%s' % (manifest or self.tmp/'none'))
        body = body.replace('pristine=/etc/homensai-vpn/pristine/payload.tar.gz', 'pristine=%s' % (pristine or self.tmp/'none.tar.gz'))
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

    def test_without_the_tool_the_service_starts_as_before_and_says_so(self):
        instances, err = self.start(None)
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))
        self.assertIn('INTEGRITY-TOOL-MISSING', err)

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

    def test_a_crashing_tool_never_blocks_the_start(self):
        instances, _ = self.start('#!/bin/sh\nexit 3\n')
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))

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
        # damaged copy: the damaged tool is not run, the service starts as before
        (self.tmp/'homensai-vpn-integrity').write_text('#!/bin/sh\necho mode=stopped\n')
        (self.tmp/'payload.tar.gz.sha256').write_text('0'*64+'\n')
        instances, err = self.start(None, manifest, pristine)
        self.assertIn('lua/monitor.lua daemon', self.command(instances, 'monitor'))
        self.assertEqual((self.tmp/'homensai-vpn-integrity').read_text(), '#!/bin/sh\necho mode=stopped\n')


class StatusFieldTest(unittest.TestCase):
    def test_both_monitors_publish_the_integrity_report(self):
        agent = (ROUTER/'files/usr/lib/homensai-vpn/agent.py').read_text()
        self.assertIn("status['integrity']=read_json(RUNTIME/'integrity.json',None)", agent)
        monitor = (LUA_SRC/'monitor.lua').read_text()
        self.assertIn("status.integrity=self:read_json(self.runtime..'/integrity.json',NULL)", monitor)

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
