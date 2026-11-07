"""The signing test lab: isolation both ways, masking, and every drill run headless over the real tools.

Offline. The real store is never touched: every path here is a temporary directory. Off Windows the lab uses its test wrapper
instead of DPAPI (HOMENSAI_SIGNING_TEST=1, set here only). The router steps of the drills run the real 02-install.sh and
homensai-vpn-trust-key under `sh` with the Python usign twin; the alpine + real usign run is in the evidence folder."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/signing'))
sys.path.insert(1, str(ROOT/'scripts/backupcrypt'))
sys.path.insert(0, str(ROOT/'qa'))
import agetool  # noqa: E402
import keytool  # noqa: E402
import lab_drills  # noqa: E402
import lab_mode  # noqa: E402
import lab_router  # noqa: E402
import ots  # noqa: E402
import secret_store  # noqa: E402
import secrets_archive  # noqa: E402
import test_signing_core as core  # noqa: E402
import totp  # noqa: E402
import usign_format as u  # noqa: E402

HAS_GIT = bool(shutil.which('git'))


def fake_root():
    return tempfile.mkdtemp(prefix='hsai-lab-qa-')


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(fake_root())
        self.addCleanup(lab_mode.remove_tree, self.base)
        patcher = mock.patch.dict(os.environ, {lab_mode.TEST_ENV: '1'})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(lab_mode.ENV_DIR, None)
        os.environ.pop(lab_mode.ENV_STORE, None)

    def marked(self, name='lab'):
        path = self.base/name
        path.mkdir(parents=True, exist_ok=True)
        (path/lab_mode.MARKER).write_text('{"lab": true}\n', encoding='ascii')
        return path

    def lab_store(self, name='lab'):
        root = self.marked(name)/'store'
        return secret_store.Store(root, protect=lab_mode.test_protect, unprotect=lab_mode.test_protect, lab=True)


class RealRefusesLab(Base):
    def test_real_store_refuses_a_marked_lab_and_anything_below_it(self):
        lab = self.marked()
        for path in (lab, lab/'store', lab/'store'/'deep'):
            with self.assertRaisesRegex(ValueError, 'STORE-LAB-DIR-REFUSED'):
                core.fake_store(path)

    def test_real_store_refuses_the_lab_name_even_before_the_marker_exists(self):
        with self.assertRaisesRegex(ValueError, 'STORE-LAB-DIR-REFUSED'):
            core.fake_store(self.base/lab_mode.DIR_NAME/'store')

    def test_env_store_pointing_into_a_lab_is_refused(self):
        lab = self.marked()
        with mock.patch.dict(os.environ, {lab_mode.ENV_STORE: str(lab/'store')}):
            with self.assertRaisesRegex(ValueError, 'STORE-LAB-DIR-REFUSED'):
                secret_store.Store(None, protect=bytes, unprotect=bytes)

    def test_lab_key_in_a_real_trust_list_is_refused(self):
        tree = self.base/'repo'
        folder = tree/keytool.KEYS_DIR
        folder.mkdir(parents=True)
        key = lab_mode.new_key(True, u.SecretKey.generate)
        (folder/key.key_id.hex()).write_bytes(key.public_file('copied'))
        with self.assertRaisesRegex(ValueError, 'KEYS-LAB-KEY-REFUSED'):
            keytool.trusted_keys(tree)

    def test_real_sign_path_refuses_a_lab_secret(self):
        tree = self.base/'repo'
        tree.mkdir()
        store = core.fake_store(self.base/'real-store')
        key = lab_mode.new_key(True, u.SecretKey.generate)
        store.write_secret('main.key.dpapi', key.to_file('copied from a lab'))
        with self.assertRaisesRegex(ValueError, 'SIGN-LAB-KEY-REFUSED'):
            keytool.load_secret(tree, store, 'main')

    def test_real_import_refuses_a_lab_line_before_storing_it(self):
        store = core.fake_store(self.base/'real-store')
        key = lab_mode.new_key(True, u.SecretKey.generate)
        line = keytool.secret_payload('main', key)
        self.assertTrue(line.startswith('HSAI-SK1-LAB:MAIN:'))
        console = core.Console(secrets=[line])
        tree = self.base/'repo'
        tree.mkdir()
        with contextlib.redirect_stderr(open(os.devnull, 'w')) as sink:
            code = keytool.main(['import', '--key', 'main'], root=tree, store=store, console=console)
            sink.close()
        self.assertEqual(code, 2)
        self.assertFalse(store.has('main.key.dpapi'))

    def test_a_lab_tag_on_a_real_id_and_the_reverse_are_format_errors(self):
        real, lab = u.SecretKey.generate(), lab_mode.new_key(True, u.SecretKey.generate)
        for key, other in ((real, lab_mode.PAYLOAD_TAG), (lab, 'HSAI-SK1')):
            body = keytool.secret_payload('main', key).rsplit(':', 1)[0].split(':', 1)[1]
            body = other+':'+body
            with self.assertRaisesRegex(ValueError, 'IMPORT-FORMAT'):
                keytool.parse_payload(body+':'+keytool._check(body))

    def test_real_keys_never_get_the_lab_prefix(self):
        lab = lab_mode.new_key(True, u.SecretKey.generate)
        keys = iter([lab, u.SecretKey(bytes(range(32)), bytes.fromhex('1111111111111111'))])
        self.assertEqual(lab_mode.new_key(False, lambda: next(keys)).key_id.hex(), '1111111111111111')

    def test_publication_refuses_a_lab_environment(self):
        for name, value in ((lab_mode.ENV_DIR, str(self.base)), (lab_mode.ENV_STORE, str(self.base/lab_mode.DIR_NAME/'store'))):
            with mock.patch.dict(os.environ, {name: value}):
                with self.assertRaisesRegex(ValueError, 'PUBLICATION-LAB-ENV'):
                    lab_mode.refuse_lab_environment()
        lab_mode.refuse_lab_environment()

    def test_publication_scan_finds_lab_ids_in_all_three_places(self):
        lab = lab_mode.KEY_ID_PREFIX+'00112233'
        for kwargs in ({'names': ['router/files/etc/homensai-vpn/keys/'+lab]}, {'chain_data': b'{"key_id":"%s"}' % lab.encode()}, {'signature_id': lab}):
            with self.assertRaisesRegex(ValueError, 'PUBLICATION-LAB-KEY'):
                lab_mode.refuse_in_publication(**kwargs)
        lab_mode.refuse_in_publication(['701cdf098a0f849f'], b'{"key_id":"701cdf098a0f849f"}', 'a1c06016584475fa')

    def test_secrets_archive_never_takes_the_lab(self):
        self.assertTrue({'signing', 'signing-lab', 'signing-lab-tools'} <= secrets_archive.NEVER_TOP)

    def test_real_otpauth_uri_is_unchanged_and_the_lab_one_says_test(self):
        store = self.lab_store()
        self.assertIn('TEST%20LAB', keytool.otpauth(store, 'A'*32))
        self.assertIn('issuer=HomenS.AI%20TEST%20LAB', keytool.otpauth(store, 'A'*32))
        self.assertNotIn('LAB', keytool.otpauth(core.fake_store(self.base/'real'), 'B'*32))

    def test_lab_and_real_stores_use_different_dpapi_entropy(self):
        lab = self.marked()
        calls = []
        with mock.patch.object(secret_store, '_dpapi', lambda data, protect, secondary=None: calls.append(secondary) or data):
            secret_store.Store(lab/'store', lab=True).protect(b'x')
            secret_store.Store(self.base/'real').protect(b'x')
        self.assertEqual(calls, [secret_store.ENTROPY_LAB, None])
        self.assertNotEqual(secret_store.ENTROPY_LAB, secret_store.ENTROPY)

    @unittest.skipUnless(os.name == 'nt', 'DPAPI is Windows only')
    def test_lab_blob_and_real_blob_cannot_cross(self):
        lab = self.marked()
        real_store, lab_store = secret_store.Store(self.base/'real'), secret_store.Store(lab/'store', lab=True)
        with self.assertRaises(secret_store.StoreError):
            real_store.unprotect(lab_store.protect(b'test only'))
        with self.assertRaises(secret_store.StoreError):
            lab_store.unprotect(real_store.protect(b'test only'))


class LabRefusesReal(Base):
    def test_lab_refuses_the_real_store_its_parents_and_children(self):
        real = self.base/'checkout'/'private'/'signing'
        real.mkdir(parents=True)
        with mock.patch.object(lab_mode, 'real_store_roots', lambda: [real.resolve()]):
            for path in (real, real.parent, real.parent.parent, real/'inside'):
                with self.assertRaisesRegex(ValueError, 'LAB-DIR-REAL-STORE'):
                    lab_mode.LabDir(path)

    def test_the_real_store_of_this_checkout_is_known_when_there_is_one(self):
        with mock.patch.object(lab_mode, '_checkout_parent', lambda: self.base):
            self.assertIn((self.base/'private'/'signing').resolve(), lab_mode.real_store_roots())
            self.assertEqual(lab_mode.default_lab_root(), self.base/'private'/'signing-lab')

    def test_lab_refuses_a_git_checkout_a_home_and_a_used_folder(self):
        tree = self.base/'tree'
        (tree/'.git').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'LAB-DIR-IS-A-CHECKOUT'):
            lab_mode.LabDir(tree)
        with self.assertRaisesRegex(ValueError, 'LAB-DIR-UNSAFE'):
            lab_mode.LabDir(Path.home())
        used = self.base/'used'
        used.mkdir()
        (used/'main.key.dpapi').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'LAB-DIR-NOT-EMPTY'):
            lab_mode.LabDir(used)

    def test_real_key_in_a_lab_tree_is_refused(self):
        tree = self.marked()/'repo'
        folder = tree/keytool.KEYS_DIR
        folder.mkdir(parents=True)
        key = u.SecretKey.generate()
        (folder/key.key_id.hex()).write_bytes(key.public_file('copied'))
        with self.assertRaisesRegex(ValueError, 'KEYS-REAL-KEY-IN-LAB'):
            keytool.trusted_keys(tree)

    def test_lab_sign_path_refuses_a_real_secret(self):
        store = self.lab_store()
        key = u.SecretKey.generate()
        store.write_secret('main.key.dpapi', key.to_file('real'))
        tree = store.root.parent/'repo'
        tree.mkdir()
        with self.assertRaisesRegex(ValueError, 'SIGN-REAL-KEY-IN-LAB'):
            keytool.load_secret(tree, store, 'main')

    def test_lab_import_refuses_a_real_line_before_storing_it(self):
        store = self.lab_store()
        tree = store.root.parent/'repo'
        tree.mkdir()
        console = core.Console(secrets=[keytool.secret_payload('main', u.SecretKey.generate())])
        with self.assertRaisesRegex(ValueError, 'IMPORT-REAL-KEY-IN-LAB'):
            keytool.cmd_import(mock.Mock(key='main', replace=False), tree, store, console)
        self.assertFalse(store.has('main.key.dpapi'))

    def test_mode_pair_mismatch_is_refused_both_ways(self):
        lab = self.marked()
        with self.assertRaisesRegex(ValueError, 'LAB-MODE-MISMATCH'):
            lab_mode.check_pair(lab/'repo', core.fake_store(self.base/'real'))
        with self.assertRaisesRegex(ValueError, 'LAB-MODE-MISMATCH'):
            lab_mode.check_pair(self.base/'realtree', self.lab_store())
        lab_mode.check_pair(lab/'repo', self.lab_store())
        lab_mode.check_pair(self.base/'realtree', core.fake_store(self.base/'real'))

    def test_a_real_store_object_cannot_pretend_to_be_a_lab(self):
        with self.assertRaisesRegex(ValueError, 'STORE-NOT-A-LAB'):
            secret_store.Store(self.base/'plain', protect=bytes, unprotect=bytes, lab=True)

    def test_the_auto_answers_refuse_a_real_store(self):
        run = mock.Mock()
        run.world.store = core.fake_store(self.base/'real')
        with self.assertRaisesRegex(ValueError, 'LAB-CONSOLE-REAL-STORE'):
            lab_drills.LabConsole(run)

    def test_marker_in_a_real_tree_only_makes_it_refuse_its_real_keys(self):
        tree = self.base/'repo'
        (tree/keytool.KEYS_DIR).mkdir(parents=True)
        key = u.SecretKey.generate()
        (tree/keytool.KEYS_DIR/key.key_id.hex()).write_bytes(key.public_file('real'))
        (tree/lab_mode.MARKER).write_text('{}', encoding='ascii')
        with self.assertRaisesRegex(ValueError, 'KEYS-REAL-KEY-IN-LAB'):
            keytool.trusted_keys(tree)


class ResetTests(Base):
    def test_reset_deletes_only_the_lab(self):
        lab = lab_mode.LabDir(self.marked('sub/lab'))
        (lab.root/'store').mkdir()
        (lab.root/'store'/'main.key.dpapi').write_bytes(b'x')
        readonly = lab.root/'store'/'readonly'
        readonly.write_bytes(b'x')
        readonly.chmod(0o444)
        beside = self.base/'sub'/'beside.txt'
        beside.write_text('keep')
        lab.reset()
        self.assertFalse(lab.root.exists())
        self.assertEqual(beside.read_text(), 'keep')

    def test_reset_needs_the_marker_and_rechecks_the_path(self):
        path = self.base/'plain'
        path.mkdir()
        lab = lab_mode.LabDir(path)
        (path/'file').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'LAB-DIR-NOT-EMPTY'):
            lab.reset()
        self.assertTrue((path/'file').exists())
        (path/'file').unlink()
        with self.assertRaisesRegex(ValueError, 'LAB-RESET-NO-MARKER'):
            lab.reset()

    def test_a_checkout_that_appeared_later_is_not_deleted(self):
        lab = lab_mode.LabDir(self.marked())
        (lab.root/'.git').mkdir()
        with self.assertRaisesRegex(ValueError, 'LAB-DIR-IS-A-CHECKOUT'):
            lab.reset()
        self.assertTrue(lab.root.exists())


class MaskTests(unittest.TestCase):
    def test_secret_shapes_never_survive(self):
        key = lab_mode.new_key(True, u.SecretKey.generate)
        line = keytool.secret_payload('main', key)
        seed = totp.new_seed()
        recovery = totp.new_recovery_codes()[0]
        identity = agetool.age.Identity.generate().encode()
        for text, secret in ((keytool.grouped(line, 4), line[20:40]), (line, line[20:40]), (' 1. %s' % recovery, recovery), (identity, identity),
                             ('Manual entry key: %s' % keytool.grouped(seed), seed[:4]), (totp.otpauth_uri(seed), seed), (seed, seed)):
            self.assertNotIn(secret, lab_drills.mask(text).replace(' ', ''))
        self.assertEqual(lab_drills.mask('value hello', ['hello']), 'value '+lab_drills.MASKED)

    def test_a_failed_check_ends_the_drill_and_is_recorded(self):
        run = lab_drills.Run.__new__(lab_drills.Run)
        run.steps, run.emit = [], lambda event: None
        run.check(True, 'holds')
        with self.assertRaises(lab_drills.DrillFailed):
            run.check(False, 'broken')
        self.assertEqual([row['ok'] for row in run.steps], [True, False])

    def test_public_facts_stay_readable(self):
        text = 'SIGNED homensai-auto-vpn_0.0.3-alpha1-1_all.ipk with main key 1ab01ab08b155256; chain seq 2'
        self.assertEqual(lab_drills.mask(text), text)


def ots_proof(digest):
    """A proof with a pending calendar attestation, in the real file format."""
    stamp = ots.DetachedTimestamp(digest)
    stamp.root.add_op(ots.OP_APPEND, b'\x01'*16).add_op(ots.OP_SHA256).add_attestation(ots.Attestation.pending('https://a.pool.opentimestamps.org'))
    return stamp.serialize()


@unittest.skipUnless(HAS_GIT and (os.name == 'nt' or (shutil.which('sh') and shutil.which('sha256sum'))), 'git and a POSIX shell or Windows needed')
class AllDrills(unittest.TestCase):
    """The whole list, once, in the order the owner walks it. Real tools, real router scripts, fake calendars only."""
    @classmethod
    def setUpClass(cls):
        cls.base = Path(fake_root())
        cls.environment = mock.patch.dict(os.environ, {lab_mode.TEST_ENV: '1'})
        cls.environment.start()
        os.environ.pop(lab_mode.ENV_DIR, None)
        cls.scrypt = mock.patch.object(totp, 'SCRYPT_N', 2**4)
        cls.scrypt.start()
        cls.real_tree = cls.fingerprint()
        cls.lab = lab_mode.LabDir(cls.base/'lab').ensure()
        cls.secrets = []

        def emit(event):
            if event['type'] == 'secret':
                cls.secrets += [event[name] for name in ('text',) if name in event]+list(event.get('codes', []))
        box = lab_router.Sandbox('host', 'qa host') if os.name == 'posix' else None
        cls.results = {row['id']: row for row in lab_drills.run_all(cls.lab, emit=emit, stamper=lambda digest: (ots_proof(digest), {'ok': ['fake']}), sandbox=box)}

    @classmethod
    def tearDownClass(cls):
        cls.scrypt.stop()
        cls.environment.stop()
        lab_mode.remove_tree(cls.base)

    @classmethod
    def fingerprint(cls):
        digest = hashlib.sha256()
        for path in sorted((ROOT/keytool.KEYS_DIR).iterdir())+[ROOT/keytool.KIT, ROOT/keytool.CHAIN, agetool.REPO_RECIPIENTS]:
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def test_every_drill_passed(self):
        self.assertEqual({key: row['status'] for key, row in self.results.items()}, {row[0]: lab_drills.PASS for row in lab_drills.TITLES},
                         json.dumps({key: row['message'] for key, row in self.results.items() if row['status'] != 'PASS'}, ensure_ascii=False))

    def test_nothing_real_changed(self):
        self.assertEqual(self.fingerprint(), self.real_tree)

    def test_report_covers_every_drill_with_masked_output_only(self):
        report = self.lab.report.read_text(encoding='utf-8')+self.lab.results.read_text(encoding='utf-8')
        self.assertIn('ТЕСТОВАЯ ЛАБОРАТОРИЯ', report)
        for row in lab_drills.TITLES:
            self.assertIn(row[1], report)
        self.assertGreater(len(self.secrets), 20)
        for secret in self.secrets:
            self.assertNotIn(secret, report)
            self.assertNotIn(secret[-12:], report)
        self.assertNotIn('AGE-SECRET-KEY-1Q', report)

    def test_headless_run_leaves_the_lab_clean(self):
        self.assertFalse((self.lab.root/'work').exists())
        self.assertEqual(lab_drills.lab_state(self.lab)['keys'], [])

    def test_a_failed_expectation_is_a_fail_not_a_pass(self):
        lab = lab_mode.LabDir(self.base/'failing').ensure()
        session = lab_drills.Session(lab, clock=lab_drills.VirtualClock(), network=False)
        run = lab_drills.Run(session, 'a')
        with mock.patch.object(lab_mode, 'is_lab_key_id', lambda value: False):
            result = run.execute()
        self.assertEqual(result['status'], lab_drills.FAIL)
        lab_mode.remove_tree(lab.root)

    def test_a_tool_that_stops_refusing_fails_the_drill(self):
        """A drill proves the real path only if a broken path makes it fail."""
        for drill, target, attribute, broken in (('d', totp, 'check_code', lambda *args, **kwargs: 1), ('l', keytool.chain, 'check_extends', lambda *args, **kwargs: 'extends'),
                                                 ('h', totp, 'check_recovery', lambda *args, **kwargs: 5)):
            lab = lab_mode.LabDir(self.base/('broken-'+drill)).ensure()
            session = lab_drills.Session(lab, clock=lab_drills.VirtualClock(), network=False, sandbox=lab_router.Sandbox(None, 'nothing'))
            prepare = lab_drills.Run(session, 'g')
            prepare.routers = []
            prepare.need_codes()
            with mock.patch.object(target, attribute, broken):
                self.assertEqual(lab_drills.Run(session, drill).execute()['status'], lab_drills.FAIL, drill)
            lab_mode.remove_tree(lab.root)

    def test_skip_is_never_counted_as_a_pass(self):
        lab = lab_mode.LabDir(self.base/'skipping').ensure()
        session = lab_drills.Session(lab, clock=lab_drills.VirtualClock(), network=False)
        self.assertEqual(lab_drills.Run(session, 'm').execute()['status'], lab_drills.SKIP)
        session.sandbox = lab_router.Sandbox(None, 'nothing')
        self.assertEqual(lab_drills.Run(session, 'k').execute()['status'], lab_drills.SKIP)
        lab_mode.remove_tree(lab.root)

    def test_manual_mode_stops_at_a_missing_step(self):
        lab = lab_mode.LabDir(self.base/'blocked').ensure()
        session = lab_drills.Session(lab)
        self.assertEqual(lab_drills.Run(session, 'd', auto=False).execute()['status'], lab_drills.BLOCKED)
        lab_mode.remove_tree(lab.root)


@unittest.skipUnless(HAS_GIT, 'git needed')
class CommandLine(Base):
    def lab_env(self):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        environment.pop(lab_mode.ENV_DIR, None)
        return environment

    def test_tools_take_the_lab_from_the_flag_and_the_environment(self):
        lab = self.base/'lab'
        run = subprocess.run([sys.executable, str(ROOT/'scripts/signing/keytool.py'), 'new-keys', '--lab', str(lab)], capture_output=True, text=True,
                             env=self.lab_env(), timeout=120, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('TEST LAB', run.stdout)
        environment = self.lab_env()
        environment[lab_mode.ENV_DIR] = str(lab)
        run = subprocess.run([sys.executable, str(ROOT/'scripts/signing/keytool.py'), 'fingerprints'], capture_output=True, text=True, env=environment,
                             timeout=120, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('TEST LAB KEY', run.stdout)
        self.assertIn(lab_mode.KEY_ID_PREFIX, run.stdout)
        run = subprocess.run([sys.executable, str(ROOT/'scripts/backupcrypt/agetool.py'), 'recipients', '--lab', str(lab)], capture_output=True, text=True,
                             env=self.lab_env(), timeout=120, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('MISMATCH-OR-EMPTY', run.stdout)

    def test_reset_from_the_command_line(self):
        lab = self.base/'lab'
        for argv in (['--run-all-drills', '--only', 'a', '--no-network'], ['--reset']):
            run = subprocess.run([sys.executable, str(ROOT/'scripts/signing/lab.py'), '--lab', str(lab)]+argv, capture_output=True, text=True,
                                 env=self.lab_env(), timeout=300, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        self.assertFalse(lab.exists())


if __name__ == '__main__':
    unittest.main()
