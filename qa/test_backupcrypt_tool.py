"""Owner-held age identity and the opt-in secrets archive (scripts/backupcrypt/agetool.py, secrets_archive.py).
DPAPI is replaced by a reversible fake (the real one is Windows-only and per user); the TOTP gate is the real one."""
import io
import json
import os
import re
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'/'backupcrypt'))
sys.path.insert(1, str(ROOT/'scripts'/'signing'))
os.environ['HOMENSAI_AGE_PURE'] = os.environ.get('HOMENSAI_AGE_PURE', '1')
import age_format as age  # noqa: E402
import agetool  # noqa: E402
import secret_store  # noqa: E402
import secrets_archive  # noqa: E402
import totp  # noqa: E402

MARK = b'PLAINTEXT-MARKER-0f3c9a'


def fake_protect(data):
    return b'FAKE-DPAPI' + bytes(b ^ 0x5a for b in data)


def fake_unprotect(blob):
    if not blob.startswith(b'FAKE-DPAPI'):
        raise secrets_archive.ArchiveError('DPAPI-UNPROTECT-FAILED')
    return bytes(b ^ 0x5a for b in blob[10:])


class FakeConsole:
    def __init__(self, secrets=(), codes=()):
        self.lines, self.secrets, self.codes, self.qr = [], list(secrets), list(codes), []

    def code(self, prompt=''):
        value = self.codes.pop(0)
        return value() if callable(value) else value

    def secret(self, prompt):
        return self.secrets.pop(0)

    def say(self, text=''):
        self.lines.append(text)

    def show_qr(self, text, mode, title):
        self.qr.append((mode, title))

    def text(self):
        return '\n'.join(self.lines)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.store = secret_store.Store(self.dir/'store', protect=fake_protect, unprotect=fake_unprotect)
        self.repo = self.dir/'recipients.txt'

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, argv, console=None):
        console = console or FakeConsole()
        err = io.StringIO()
        stderr, sys.stderr = sys.stderr, err
        try:
            code = agetool.main(argv+['--repo-recipients', str(self.repo)], store=self.store, console=console)
        finally:
            sys.stderr = stderr
        return code, console, err.getvalue()

    def enrol(self):
        seed = []
        console = FakeConsole(codes=[lambda: totp.totp(totp.seed_bytes(seed[0]), time.time())])
        original = console.say

        def say(text=''):
            match = re.match(r'Manual entry key: (.*)', text)
            if match:
                seed.append(match.group(1).replace(' ', ''))
            original(text)
        console.say = say
        code, _, err = self.run_tool(['setup-totp', '--qr', 'none'], console)
        self.assertEqual(code, 0, err)
        return seed[0]

    def current_code(self, seed, offset=0):
        return totp.totp(totp.seed_bytes(seed), time.time()+offset)


class Identity(Base):
    def test_new_identity_pins_and_writes_repo_recipient(self):
        code, console, err = self.run_tool(['new-identity'])
        self.assertEqual(code, 0, err)
        identity = agetool.load_identity(self.store)
        self.assertEqual(agetool.repo_recipients(self.repo), [identity.recipient()])
        self.assertEqual(agetool.pinned_recipients(self.store), [identity.recipient()])
        self.assertNotIn('AGE-SECRET-KEY', console.text())
        self.assertNotIn(b'AGE-SECRET-KEY', (self.store.root/agetool.IDENTITY).read_bytes())
        code, _, err = self.run_tool(['new-identity'])
        self.assertEqual(code, 2)
        self.assertIn('IDENTITY-EXISTS', err)

    def test_replace_retires_never_deletes(self):
        self.run_tool(['new-identity'])
        old = agetool.load_identity(self.store)
        code, _, err = self.run_tool(['new-identity', '--replace'])
        self.assertEqual(code, 0, err)
        retired = [p.name for p in self.store.root.iterdir() if p.name.startswith('age-backup.retired-')]
        self.assertEqual(len([n for n in retired if n.endswith('identity.dpapi')]), 1)
        self.assertNotEqual(agetool.load_identity(self.store).recipient(), old.recipient())

    def test_reveal_needs_totp_and_shows_identity_once_gate_passes(self):
        self.run_tool(['new-identity'])
        code, console, err = self.run_tool(['reveal', '--qr', 'none'])
        self.assertEqual(code, 2)
        self.assertIn('TOTP-NOT-ENROLLED', err)
        seed = self.enrol()
        code, console, err = self.run_tool(['reveal', '--qr', 'none'], FakeConsole(codes=['000000' if self.current_code(seed) != '000000' else '111111']))
        self.assertEqual(code, 2)
        self.assertIn('TOTP-WRONG-CODE', err)
        self.assertNotIn('AGE-SECRET-KEY', console.text())
        code, console, err = self.run_tool(['reveal', '--qr', 'console'], FakeConsole(codes=[self.current_code(seed, 30)]))
        self.assertEqual(code, 0, err)
        self.assertIn(agetool.load_identity(self.store).encode(), console.text())
        self.assertEqual(console.qr[0][0], 'console')
        code, _, err = self.run_tool(['reveal', '--qr', 'none'], FakeConsole(codes=[self.current_code(seed, 30)]))
        self.assertIn('TOTP-REPLAYED', err)

    def test_test_code_refused_outside_test_runs(self):
        previous = os.environ.pop(agetool.TEST_ENV, None)
        try:
            with self.assertRaises(agetool.ToolError):
                agetool.Console('123456')
        finally:
            if previous is not None:
                os.environ[agetool.TEST_ENV] = previous

    def test_import_on_a_new_pc(self):
        self.run_tool(['new-identity'])
        identity = agetool.load_identity(self.store)
        new_pc = secret_store.Store(self.dir/'new-pc', protect=fake_protect, unprotect=fake_unprotect)
        stranger = age.Identity.generate()
        console = FakeConsole(secrets=[stranger.encode()])
        code = agetool.main(['import', '--repo-recipients', str(self.repo)], store=new_pc, console=console)
        self.assertEqual(code, 2)
        self.assertFalse(new_pc.has(agetool.IDENTITY))
        spaced = ' '.join(identity.encode()[i:i+4] for i in range(0, len(identity.encode()), 4))
        code = agetool.main(['import', '--repo-recipients', str(self.repo)], store=new_pc, console=FakeConsole(secrets=[spaced]))
        self.assertEqual(code, 0)
        self.assertEqual(agetool.load_identity(new_pc).recipient(), identity.recipient())
        self.assertEqual(agetool.pinned_recipients(new_pc), [identity.recipient()])


class Recipients(Base):
    def test_edited_repository_file_is_refused_until_trusted(self):
        self.run_tool(['new-identity'])
        attacker = age.Identity.generate()
        self.repo.write_text('%s\n' % attacker.recipient().encode(), encoding='utf-8')
        source = self.dir/'in.bin'
        source.write_bytes(MARK)
        code, _, err = self.run_tool(['encrypt', '--in', str(source), '--out', str(self.dir/'out.age')])
        self.assertEqual(code, 2)
        self.assertIn('RECIPIENTS-MISMATCH', err)
        self.assertFalse((self.dir/'out.age').exists())
        code, _, err = self.run_tool(['recipients', '--trust-repo'])
        self.assertEqual(code, 0, err)
        code, _, err = self.run_tool(['encrypt', '--in', str(source), '--out', str(self.dir/'out.age')])
        self.assertEqual(code, 0, err)
        self.assertEqual(age.decrypt((self.dir/'out.age').read_bytes(), [attacker]), MARK)

    def test_no_pin_refused(self):
        with self.assertRaises(agetool.ToolError):
            agetool.encryption_recipients(self.store, self.repo)

    def test_malformed_and_duplicate_lines(self):
        one = age.Identity.generate().recipient().encode()
        with self.assertRaises(agetool.ToolError):
            agetool.parse_recipients(one+'\n'+one+'\n')
        with self.assertRaises(agetool.ToolError):
            agetool.parse_recipients('age1notarecipient\n')
        self.assertEqual(len(agetool.parse_recipients('# c\n\n%s  # owner\n' % one)), 1)


def make_private(root):
    p = root/'private'
    access = p/'portable-router-access-2026-10-20'
    (access/'python'/'cryptography').mkdir(parents=True)
    (access/'python'/'cryptography'/'big.py').write_bytes(b'x'*10)
    (access/'__pycache__').mkdir()
    (access/'__pycache__'/'x.pyc').write_bytes(b'x')
    (access/'portable-access.key.dpapi').write_bytes(fake_protect(MARK+b'-ssh'))
    (access/'known_hosts').write_bytes(b'router ssh-ed25519 AAAA')
    (access/'alpha2-backup-after.enc').write_bytes(b'HSBK1'+os.urandom(40))
    (access/'alpha2-backup-after.key.dpapi').write_bytes(fake_protect(os.urandom(32)))
    (access/'nested').mkdir()
    (access/'nested'/'state.local.json').write_bytes(MARK+b'-state')
    acceptance = p/'acceptance-20261022'
    acceptance.mkdir()
    (acceptance/'pre-pair-config.enc').write_bytes(b'HSBK1'+os.urandom(30))
    (acceptance/'pre-pair-config.key.dpapi').write_bytes(fake_protect(os.urandom(32)))
    (acceptance/'pre-pair-config.receipt.json').write_bytes(b'{}')
    (acceptance/'unrelated.json').write_bytes(b'{}')
    (acceptance/'deeper'/'deepest').mkdir(parents=True)
    (acceptance/'deeper'/'x.key.dpapi').write_bytes(fake_protect(b'k2'))
    (acceptance/'deeper'/'deepest'/'too-deep.key.dpapi').write_bytes(fake_protect(b'k3'))
    (p/'router-backup-20261017.tgz').write_bytes(MARK+b'-tgz')
    (p/'other.tgz').write_bytes(b'not selected')
    signing = p/'signing'
    signing.mkdir()
    (signing/'main.key.dpapi').write_bytes(b'never')
    (signing/'age-backup.identity.dpapi').write_bytes(b'never')
    worktree = p/'some-worktree'
    worktree.mkdir()
    (worktree/'.git').write_text('gitdir: x')
    (worktree/'a.key.dpapi').write_bytes(b'never')
    research = p/'research'
    research.mkdir()
    (research/'api-token.txt').write_bytes(MARK+b'-token')
    return p


class Archive(Base):
    def setUp(self):
        super().setUp()
        self.private = make_private(self.dir)
        self.identity = age.Identity.generate()

    def test_selection(self):
        paths, skipped = secrets_archive.select(self.private, ['research/api-token.txt [password/token-name]',
                                                               '../outside.txt', 'signing/main.key.dpapi'])
        self.assertEqual(paths, [
            'acceptance-20261022/deeper/x.key.dpapi', 'acceptance-20261022/pre-pair-config.enc',
            'acceptance-20261022/pre-pair-config.key.dpapi', 'acceptance-20261022/pre-pair-config.receipt.json',
            'portable-router-access-2026-10-20/alpha2-backup-after.enc',
            'portable-router-access-2026-10-20/alpha2-backup-after.key.dpapi',
            'portable-router-access-2026-10-20/known_hosts', 'portable-router-access-2026-10-20/nested/state.local.json',
            'portable-router-access-2026-10-20/portable-access.key.dpapi', 'research/api-token.txt',
            'router-backup-20261017.tgz'])
        self.assertIn('../outside.txt [outside private]', skipped)
        self.assertIn('signing/main.key.dpapi [never]', skipped)

    def test_router_backup_limit_and_access_file_size(self):
        access = self.private/'portable-router-access-2026-10-20'
        for index in range(4):
            path = access/('alpha%d-backup.enc' % (10+index))
            path.write_bytes(b'HSBK1')
            os.utime(path, (1000000+index, 1000000+index))
        (access/'stage-python.sh').write_bytes(b'#' * (secrets_archive.ACCESS_MAX_FILE+1))
        (access/'big.key.dpapi').write_bytes(b'k' * (secrets_archive.ACCESS_MAX_FILE+1))
        paths, skipped = secrets_archive.select(self.private, router_backups=2)
        blobs = [p for p in paths if p.endswith(('.enc', '.aesgcm'))]
        self.assertEqual(len(blobs), 2)
        self.assertIn('portable-router-access-2026-10-20/big.key.dpapi', paths)
        self.assertIn('portable-router-access-2026-10-20/stage-python.sh [>1 MB, not key material]', skipped)
        self.assertNotIn('portable-router-access-2026-10-20/alpha10-backup.enc', paths)
        self.assertIn('portable-router-access-2026-10-20/alpha10-backup.enc [older router backup; router_backups=2]', skipped)
        everything, _ = secrets_archive.select(self.private, router_backups=-1)
        self.assertEqual(len([p for p in everything if p.endswith(('.enc', '.aesgcm'))]), 6)
        none, _ = secrets_archive.select(self.private, router_backups=0)
        self.assertFalse(any(p.endswith(('.enc', '.aesgcm')) for p in none))
        self.assertIn('acceptance-20261022/pre-pair-config.key.dpapi', none)

    def test_large_files_skipped(self):
        original = secrets_archive.MAX_FILE
        secrets_archive.MAX_FILE = 20
        try:
            paths, skipped = secrets_archive.select(self.private)
        finally:
            secrets_archive.MAX_FILE = original
        self.assertNotIn('router-backup-20261017.tgz', paths)
        self.assertIn('router-backup-20261017.tgz [>20 MB]', skipped)

    def test_create_restore_round_trip_never_plaintext(self):
        out = self.dir/'stage'/secrets_archive.ARCHIVE_NAME
        out.parent.mkdir()
        summary = secrets_archive.create(self.private, out, [self.identity.recipient()], ['research/api-token.txt'],
                                         unprotect=fake_unprotect)
        sealed = out.read_bytes()
        self.assertNotIn(MARK, sealed)
        self.assertFalse(any(p.name.endswith('.partial') for p in out.parent.iterdir()))
        self.assertEqual(summary['unwrapped'], 4)
        self.assertEqual(summary['unwrap_failed'], [])
        self.assertIn('portable-router-access-2026-10-20/portable-access.key.plain', summary['names'])
        self.assertNotIn(MARK.decode(), json.dumps(summary))
        names = secrets_archive.list_names(sealed, [self.identity])
        self.assertIn(secrets_archive.INNER_MANIFEST, names)
        into = self.dir/'restored'
        written = secrets_archive.restore(sealed, [self.identity], into, protect=fake_protect)
        self.assertIn('portable-router-access-2026-10-20/portable-access.key.dpapi', written)
        self.assertEqual(fake_unprotect((into/'portable-router-access-2026-10-20'/'portable-access.key.dpapi').read_bytes()),
                         MARK+b'-ssh')
        self.assertFalse((into/'portable-router-access-2026-10-20'/'portable-access.key.plain').exists())
        self.assertEqual((into/'router-backup-20261017.tgz').read_bytes(), MARK+b'-tgz')
        with self.assertRaises(secrets_archive.ArchiveError):
            secrets_archive.restore(sealed, [self.identity], into, protect=fake_protect)
        with self.assertRaises(age.NoMatchError):
            secrets_archive.restore(sealed, [age.Identity.generate()], self.dir/'other', protect=fake_protect)

    def test_unwrap_failure_keeps_blob_and_reports(self):
        (self.private/'acceptance-20261022'/'deeper'/'x.key.dpapi').write_bytes(b'real-dpapi-of-another-user')
        out = self.dir/'s.age'
        summary = secrets_archive.create(self.private, out, [self.identity.recipient()], unprotect=fake_unprotect)
        self.assertEqual(summary['unwrap_failed'], ['acceptance-20261022/deeper/x.key.dpapi'])
        self.assertIn('acceptance-20261022/deeper/x.key.dpapi', summary['names'])

    def test_restore_refuses_unsafe_entries(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as tar:
            info = tarfile.TarInfo('../escape.txt')
            info.size = 1
            tar.addfile(info, io.BytesIO(b'x'))
        sealed = age.encrypt(buffer.getvalue(), [self.identity.recipient()])
        with self.assertRaises(secrets_archive.ArchiveError):
            secrets_archive.restore(sealed, [self.identity], self.dir/'r', protect=fake_protect)
        self.assertFalse((self.dir/'escape.txt').exists())

    def make_link(self, link, target):
        """A directory symlink, or a Windows junction when symlinks need a privilege this account lacks."""
        try:
            os.symlink(target, link, target_is_directory=True)
            return
        except (OSError, NotImplementedError):
            pass
        try:
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        except (ImportError, AttributeError, OSError):
            self.skipTest('neither a directory symlink nor a junction can be created here')

    def sealed_two_level(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as tar:
            info = tarfile.TarInfo('sub/secret.txt')
            info.size = len(MARK)
            tar.addfile(info, io.BytesIO(MARK))
        return age.encrypt(buffer.getvalue(), [self.identity.recipient()])

    def test_restore_never_follows_an_existing_link(self):
        # F-08 (audit 06.11.2026): an existing linked subdirectory of --into redirected new secret files outside it.
        sealed = self.sealed_two_level()
        outside = self.dir/'outside'
        outside.mkdir()
        into = self.dir/'into'
        into.mkdir()
        self.make_link(into/'sub', outside)
        with self.assertRaises(secrets_archive.ArchiveError):
            secrets_archive.restore(sealed, [self.identity], into, protect=fake_protect)
        self.assertEqual(list(outside.iterdir()), [], 'nothing was written through the link')
        linked = self.dir/'linked-into'
        self.make_link(linked, outside)
        with self.assertRaisesRegex(secrets_archive.ArchiveError, 'RESTORE-DESTINATION-UNSAFE'):
            secrets_archive.restore(sealed, [self.identity], linked, protect=fake_protect)
        self.assertEqual(list(outside.iterdir()), [])
        # A link that appears after the emptiness check is still refused when the parent directories are made.
        fresh = self.dir/'fresh'
        fresh.mkdir()
        self.make_link(fresh/'sub', outside)
        with self.assertRaisesRegex(secrets_archive.ArchiveError, 'RESTORE-PATH-REDIRECTED'):
            secrets_archive._safe_parent(fresh.resolve(), 'sub/secret.txt')
        self.assertEqual(list(outside.iterdir()), [])

    def test_restore_into_new_or_empty_directory(self):
        sealed = self.sealed_two_level()
        empty = self.dir/'empty'
        empty.mkdir()
        self.assertEqual(secrets_archive.restore(sealed, [self.identity], empty, protect=fake_protect), ['sub/secret.txt'])
        self.assertEqual((empty/'sub'/'secret.txt').read_bytes(), MARK)
        self.assertEqual(secrets_archive.restore(sealed, [self.identity], self.dir/'new'/'dir', protect=fake_protect),
                         ['sub/secret.txt'])
        busy = self.dir/'busy'
        busy.mkdir()
        (busy/'unrelated.txt').write_text('x')
        with self.assertRaisesRegex(secrets_archive.ArchiveError, 'RESTORE-DESTINATION-NOT-EMPTY'):
            secrets_archive.restore(sealed, [self.identity], busy, protect=fake_protect)

    def test_cli_secrets_archive_and_verify(self):
        self.run_tool(['new-identity'])
        extra = self.dir/'extra.json'
        extra.write_text(json.dumps(['research/api-token.txt [password/token-name]']), encoding='utf-8')
        original = secrets_archive.dpapi
        secrets_archive.dpapi = lambda data, protect: fake_protect(data) if protect else fake_unprotect(data)
        try:
            code, console, err = self.run_tool(['secrets-archive', '--out', str(self.dir), '--private', str(self.private),
                                                '--also-json', str(extra)])
        finally:
            secrets_archive.dpapi = original
        self.assertEqual(code, 0, err)
        summary = json.loads(console.lines[-1])
        self.assertEqual(summary['result'], 'OK')
        self.assertIn('research/api-token.txt', summary['names'])
        code, console, err = self.run_tool(['verify-archive', '--archive', str(self.dir/secrets_archive.ARCHIVE_NAME), '--list'])
        self.assertEqual(code, 0, err)
        self.assertIn('HEADER-OK x25519_recipients=1', console.lines[0])
        self.assertIn('router-backup-20261017.tgz', console.lines)

    def test_cli_decrypt_with_pasted_identity(self):
        self.run_tool(['new-identity'])
        identity = agetool.load_identity(self.store)
        source = self.dir/'plain.bin'
        source.write_bytes(MARK)
        self.run_tool(['encrypt', '--in', str(source), '--out', str(self.dir/'x.age'), '--armor'])
        self.assertTrue((self.dir/'x.age').read_bytes().startswith(age.ARMOR_BEGIN))
        code, _, err = self.run_tool(['decrypt', '--in', str(self.dir/'x.age'), '--out', str(self.dir/'back.bin'),
                                      '--paste-identity'], FakeConsole(secrets=[identity.encode().lower()]))
        self.assertEqual(code, 0, err)
        self.assertEqual((self.dir/'back.bin').read_bytes(), MARK)
        code, _, err = self.run_tool(['decrypt', '--in', str(self.dir/'x.age'), '--out', str(self.dir/'back.bin')])
        self.assertEqual(code, 2)
        self.assertIn('OUT-EXISTS', err)

    def test_missing_arguments(self):
        code, _, err = self.run_tool(['encrypt'])
        self.assertEqual(code, 2)
        self.assertIn('ARGUMENTS', err)


class Vendored(unittest.TestCase):
    def test_signing_helpers_are_the_signing_branch_files(self):
        # the one copy shared with the signing tools (blob ids at the integration of alpha9, with the recovery codes and
        # the lab mode of feat/usign-signing-20261103): a change here must be reviewed for the age tools too
        import hashlib
        expected = {'secret_store.py': '8976da45f9e101ef84c1ff92cc901d994e299ba1',
                    'totp.py': 'd882570ed5460a0a7fdcc1f8f80b9a51a913a56f',
                    'qr.py': '2ef8283698e5fb255c991ec4dfca761a74682426'}
        for name, blob in expected.items():
            data = (ROOT/'scripts'/'signing'/name).read_bytes().replace(b'\r\n', b'\n')
            self.assertEqual(hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest(), blob, name)


if __name__ == '__main__':
    os.environ[agetool.TEST_ENV] = '1'
    unittest.main()
