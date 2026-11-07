"""scripts/secret_scan.py and its wiring (hook, gitflow privacy, publication, offline CI). Every secret here is made up and
assembled at run time, so this file itself contains nothing the scanner would flag."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import gzip
import os
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


scan = load('secret_scan', 'scripts/secret_scan.py')
flow = load('gitflow_for_scan_test', 'tools/gitflow.py')
publish = load('publish_reviewed_for_scan_test', 'scripts/publish-reviewed.py')

B44 = ''.join('kB3dE5gH7jK9mN1pQ3sT5vW7yZ9bD2fH4jL6nP8rT0uWxYcA'[i % 50] for i in range(42)) + 'A='
TELEGRAM = '123456789' + ':' + 'A' * 35
AGE = 'AGE-SECRET-' + 'KEY-1' + 'Q' * 58
PEM = '-----BEGIN ' + 'PRIVATE KEY-----'
CASES = {
    'pem_private_key': PEM + '\nMIIE\n',
    'age_secret': AGE + '\n',
    'usign_secret': 'untrusted comment: signify secret' + ' key\nRWRC\n',
    'openvpn_inline': '<' + 'key>\nMIIE\n',
    'openvpn_auth_file': 'auth-user-' + 'pass creds.txt\n',
    'telegram_token': 'x ' + TELEGRAM + ' y\n',
    'github_token': 'gh' + 'o_' + 'a' * 36,
    'api_key_token': 'AK' + 'IA' + 'ABCDEFGHIJKLMNOP',
    'bearer': 'Authorization: Bearer ' + 'abcdefghijklmnopqrstuvwxyz0123456789',
    'wg_key': '[Interface]\nPrivate' + 'Key = ' + B44 + '\n',
    'psk_hex': 'wpa: ps' + 'k=' + '0123456789abcdef' * 4,
    'uci_option_secret': "\toption ps" + "k 'Qx7zLmPw93'\n",
    'uci_dotted_secret': "wireless.@wifi-iface[0].k" + "ey='Qx7zLmPw93'\n",
    'kv_secret': 'config = {"pass' + 'word": "Qx7zLmPw93Zz"}\n',
    'url_credentials': 'git clone https://' + 'bob:Qx7zLmPw93@host.example/x.git',
    'shadow_hash': 'root:$' + '1$abcdefgh$' + 'a' * 22 + ':0:0:99999:7:::',
}
CLEAN = {
    'placeholder': 'password = "changeme-please"\n',
    'variable': 'token = "${TOKEN_FROM_ENV}"\n',
    'regex': "local TOKEN='^[0-9]+:[A-Za-z0-9_-]+$'\n",
    'plain': 'nothing to see here 203.0.113.7 version 1.2.3\n',
    'short': 'ts 1234567:abc\n',
    'call': 'password = "get_password()"\n',
    'repeat': 'password = "aaaaaaaaaaaa"\n',
}


def run_scan(*argv, cwd=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = scan.main(list(argv))
    return code, out.getvalue() + err.getvalue()


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True,
                          env=dict(__import__('os').environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@localhost',
                                   GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@localhost')).stdout.strip()


class ScannerRules(unittest.TestCase):
    def test_every_rule_fires_and_value_is_never_printed(self):
        allow = scan.Allowlist()
        for rule, text in CASES.items():
            with self.subTest(rule=rule):
                found = scan.scan_blob('src/example_module.txt', text.encode(), allow)
                self.assertIn(rule, {f.rule for f in found})
                self.assertNotIn(text.strip(), ' '.join(str(f) for f in found))
        every = ''.join(CASES.values()).encode()
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'leak.txt').write_bytes(every)
            code, output = run_scan('--paths', 'leak.txt', '--root', directory)
        self.assertEqual(code, 1)
        for secret in (B44, TELEGRAM, AGE, 'Qx7zLmPw93', 'abcdefghijklmnopqrstuvwxyz0123456789'):
            self.assertNotIn(secret, output)
        self.assertIn('SECRET-SCAN-FAIL', output)

    def test_placeholders_and_code_are_not_findings(self):
        for label, text in CLEAN.items():
            with self.subTest(label=label):
                self.assertEqual(scan.scan_blob('src/example_module.txt', text.encode(), scan.Allowlist()), [])

    def test_line_marker_allows_one_line_only(self):
        text = (CASES['uci_option_secret'].rstrip() + ' # secret-scan: allow\n' + CASES['uci_dotted_secret']).encode()
        found = scan.scan_blob('docs/x.txt', text, scan.Allowlist())
        self.assertEqual([f.rule for f in found], ['uci_dotted_secret'])
        self.assertEqual(found[0].line, 2)

    def test_allowlist_needs_a_reason_and_scopes_paths(self):
        with self.assertRaisesRegex(ValueError, 'ALLOWLIST-REASON-MISSING'):
            scan.Allowlist({'paths': [{'glob': '*', 'rules': ['*']}]})
        allow = scan.Allowlist({'paths': [{'glob': 'tests/vectors/*', 'rules': ['age_secret'], 'reason': 'public vector'}],
                                'values': [{'rules': ['kv_secret'], 'regex': 'Qx7z', 'paths': ['tests/*'], 'reason': 'test value'}]})
        data = CASES['age_secret'].encode()
        self.assertEqual(scan.scan_blob('tests/vectors/a.txt', data, allow), [])
        self.assertTrue(scan.scan_blob('src/a.txt', data, allow))
        self.assertTrue(scan.scan_blob('tests/vectors/a.txt', CASES['telegram_token'].encode(), allow),
                        'a file row allows only the rules it names')
        kv = CASES['kv_secret'].encode()
        self.assertEqual(scan.scan_blob('tests/a.py', kv, allow), [])
        self.assertTrue(scan.scan_blob('src/a.py', kv, allow))
        self.assertTrue(scan.scan_blob('tests/a.py', CASES['telegram_token'].encode(), allow))

    def test_shipped_allowlist_loads_and_every_row_has_a_reason(self):
        allow = scan.Allowlist.load()
        self.assertTrue(allow.paths and allow.values)

    def test_forbidden_names_and_archive_members(self):
        for name in ('x/router-backup-2026.tgz', 'a.dpapi', 'k/main.key', 'x.private.json', 'y.local.md', 'c.ovpn', 'e.enc',
                     '.env', 'id_rsa', 'private/notes.txt', '.claude/worktrees/a/f.py', 'secrets/x.txt'):
            with self.subTest(name=name):
                self.assertTrue(scan.name_findings(name, scan.Allowlist()), name)
        for name in ('.env.example', 'docs/readme.md', 'router/files/etc/config/homensai_vpn', 'a/probe-anchors/root.pem'):
            with self.subTest(name=name):
                self.assertEqual(scan.name_findings(name, scan.Allowlist()), [])

    def test_archives_are_opened(self):
        buffer = io.BytesIO()
        payload = CASES['telegram_token'].encode()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            info = tarfile.TarInfo('./etc/config/homensai_vpn')
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        found = scan.scan_blob('pkg.ipk', buffer.getvalue(), scan.Allowlist())
        self.assertEqual([(f.path, f.rule) for f in found], [('pkg.ipk!./etc/config/homensai_vpn', 'telegram_token')])


def zip_bytes(members, stored=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED) as archive:
        for name, data in members:
            archive.writestr(name, data)
    return buffer.getvalue()


def tar_gz_bytes(members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def rules(found):
    return {f.rule for f in found}


class ScannerFailsClosed(unittest.TestCase):
    """Security audit 06.11.2026 (F-04, F-05, F-06): content the scanner cannot read is a finding, never "clean"."""

    def test_nul_byte_does_not_hide_structural_markers_or_tokens(self):
        allow = scan.Allowlist()
        for prefix in (b'\0', b'x' * 7999 + b'\0', b'\x89PNG\r\n\x1a\n\0\0'):
            for rule in ('pem_private_key', 'github_token', 'age_secret', 'telegram_token'):
                data = prefix + b'\n' + CASES[rule].encode()
                with self.subTest(offset=len(prefix), rule=rule):
                    self.assertIn(rule, rules(scan.scan_blob('src/probe.txt', data, allow)))
        self.assertEqual(scan.scan_blob('img/logo.png', b'\x89PNG\r\n\x1a\n\0\0\0\rIHDR' + bytes(range(256)), allow), [])

    def test_utf16_text_is_decoded(self):
        for codec, bom in (('utf-16-le', b'\xff\xfe'), ('utf-16-be', b'\xfe\xff'), ('utf-16-le', b'')):
            for rule in ('telegram_token', 'kv_secret', 'pem_private_key'):
                data = bom + ('line one\n' + CASES[rule]).encode(codec)
                with self.subTest(codec=codec, bom=bool(bom), rule=rule):
                    self.assertIn(rule, rules(scan.scan_blob('docs/notes.txt', data, scan.Allowlist())))

    def test_archive_depth_member_size_and_damage_fail_closed(self):
        allow = scan.Allowlist()
        nested = CASES['telegram_token'].encode()
        for _ in range(4):
            nested = zip_bytes([('inner.zip', nested)])
        self.assertIn('archive_too_deep', rules(scan.scan_blob('deep.zip', nested, allow)))
        with mock.patch.object(scan, 'MAX_FILE', 4000):
            big = (b'A' * 9000) + b'\n' + CASES['telegram_token'].encode()
            for name, data in (('big.zip', zip_bytes([('big.txt', big)])), ('big.tgz', tar_gz_bytes([('big.txt', big)]))):
                with self.subTest(name=name):
                    self.assertLess(len(data), 4000)
                    self.assertIn('archive_member_too_large', rules(scan.scan_blob(name, data, allow)))
        broken = b'PK\x03\x04' + b'\0' * 40 + CASES['wg_key'].encode()
        self.assertTrue(rules(scan.scan_blob('broken.zip', broken, allow)) & {'archive_unreadable'})
        self.assertIn('archive_unreadable', rules(scan.scan_blob('broken.gz', b'\x1f\x8b\x08\0garbage' + b'\0' * 30, allow)))
        with mock.patch.object(scan, 'ARCHIVE_BUDGET', 1000):
            self.assertIn('archive_budget', rules(scan.scan_blob('bomb.zip', zip_bytes([('a.txt', b'A' * 5000)]), allow)))
        # A text file that merely starts with "PK" is text, not a damaged archive.
        self.assertEqual(scan.scan_blob('router/Makefile', b'PKG_NAME:=x\nPKG_VERSION:=1\n', allow), [])

    def test_plain_gzip_and_readable_archives_are_scanned(self):
        allow = scan.Allowlist()
        found = scan.scan_blob('logs/run.log.gz', gzip.compress(CASES['telegram_token'].encode()), allow)
        self.assertIn('telegram_token', rules(found))
        found = scan.scan_blob('bundle.zip', zip_bytes([('a/b.txt', CASES['github_token'].encode())]), allow)
        self.assertEqual([(f.path, f.rule) for f in found], [('bundle.zip!a/b.txt', 'github_token')])

    def test_directory_rules_come_before_basename_exceptions(self):
        allow = scan.Allowlist()
        for name in ('private/.env.example', 'secrets/.env.example', 'a/private/.env.example', 'private/a!b.txt',
                     'docs/x!y/private.ovpn', 'notes!/k.ovpn', '.ssh/.env.example'):
            with self.subTest(name=name):
                self.assertTrue(scan.name_findings(name, allow), name)
        self.assertEqual(scan.name_findings('docs/.env.example', allow), [])
        self.assertIn('forbidden_dir', rules(scan.scan_blob('private/a!b.txt', b'harmless', allow)), 'a top-level name with ! is not an archive member')
        self.assertEqual(scan.name_findings('a!b/readme.md', allow), [])

    def test_archive_members_follow_the_same_directory_and_name_rules(self):
        allow = scan.Allowlist()
        for member in ('private/notes.txt', 'secrets/.env.example', '.ssh/config', 'home/x.ovpn', 'etc/router-backup.bin',
                       '.env.local', 'cfg/settings.local.json'):
            data = tar_gz_bytes([(member, b'harmless\n')])
            with self.subTest(member=member):
                self.assertTrue(rules(scan.scan_blob('pkg.ipk', data, allow)) & {'forbidden_dir', 'forbidden_name'}, member)
        package = tar_gz_bytes([('./debian-binary', b'2.0\n'), ('./control.tar.gz', tar_gz_bytes([('./control', b'Package: x\n')])),
                                ('./data.tar.gz', tar_gz_bytes([('./etc/config/homensai_vpn', b"config main 'main'\n")]))])
        self.assertEqual(scan.scan_blob('releases/x_1_all.ipk', package, allow), [], 'nested package containers stay allowed')

    def test_member_name_with_exclamation_mark_keeps_its_directory(self):
        # R4-08 (night2 N3-lifecycle 5): the walker used to keep only the text after the last '!', so private/notes!public.txt passed
        allow = scan.Allowlist()
        for member in ('private/notes!public.txt', 'secrets/a!b!c.txt', 'docs/private/x!y'):
            for data in (zip_bytes([(member, b'harmless\n')]), tar_gz_bytes([(member, b'harmless\n')])):
                with self.subTest(member=member):
                    found = scan.scan_blob('attachments.zip', data, allow)
                    self.assertIn('forbidden_dir', rules(found), member)
                    self.assertEqual({f.path for f in found}, {'attachments.zip!' + member})
        # an ordinary member whose name holds a '!' is still clean, and the outer archive's own directory is not the member's
        self.assertEqual(scan.scan_blob('out/x.zip', zip_bytes([('docs/a!b.txt', b'harmless\n')]), allow), [])

    def test_bzip2_and_xz_streams_are_opened_by_content_and_fail_closed(self):
        # R4-08 (night2 N3-lifecycle 6): the publication scanner treated bzip2/xz as ordinary bytes
        import bz2, lzma
        allow = scan.Allowlist()
        payload = CASES['telegram_token'].encode()
        for label, data in (('<bunzip2>', bz2.compress(payload)), ('<unxz>', lzma.compress(payload))):
            with self.subTest(label=label):
                found = scan.scan_blob('notes.bin', data, allow)
                self.assertEqual([(f.path, f.rule) for f in found], [('notes.bin!' + label, 'telegram_token')])
                self.assertEqual(rules(scan.scan_blob('notes.bin', data[:-6], allow)), {'archive_unreadable'}, 'a truncated stream is a finding')
        # bzip2/xz tars are walked like gzip tars
        for mode in ('w:bz2', 'w:xz'):
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode=mode) as archive:
                info = tarfile.TarInfo('private/notes.txt');info.size = 8
                archive.addfile(info, io.BytesIO(b'harmless'))
            with self.subTest(mode=mode):
                self.assertIn('forbidden_dir', rules(scan.scan_blob('bundle.bin', buffer.getvalue(), allow)))


@unittest.skipUnless(shutil.which('git'), 'Git integration is covered by the full Python 3.11 CI image')
class GitModes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='homensai-scan-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        (self.repo / 'ok.txt').write_text('fine\n')
        git(self.repo, 'add', 'ok.txt')
        git(self.repo, 'commit', '-qm', 'base')
        self.base = git(self.repo, 'rev-parse', 'HEAD')

    def test_staged_scans_the_index_not_the_working_tree(self):
        (self.repo / 'leak.txt').write_text(CASES['telegram_token'])
        code, output = run_scan('--staged', '--repo', str(self.repo))
        self.assertEqual(code, 0, 'unstaged file must not count')
        git(self.repo, 'add', 'leak.txt')
        code, output = run_scan('--staged', '--repo', str(self.repo))
        self.assertEqual(code, 1)
        self.assertIn('leak.txt:1 telegram_token', output)
        self.assertNotIn(TELEGRAM, output)
        (self.repo / 'leak.txt').write_text('clean again\n')          # the index still holds the secret
        self.assertEqual(run_scan('--staged', '--repo', str(self.repo))[0], 1)
        git(self.repo, 'add', 'leak.txt')
        self.assertEqual(run_scan('--staged', '--repo', str(self.repo))[0], 0)

    def test_staged_blocks_forbidden_name_with_harmless_content(self):
        (self.repo / 'x.private.json').write_text('{}\n')
        git(self.repo, 'add', '-f', 'x.private.json')
        code, output = run_scan('--staged', '--repo', str(self.repo))
        self.assertEqual(code, 1)
        self.assertIn('forbidden_name', output)

    def test_range_checks_only_new_objects_and_tree_checks_everything(self):
        (self.repo / 'old.txt').write_text(CASES['telegram_token'])
        git(self.repo, 'add', 'old.txt')
        git(self.repo, 'commit', '-qm', 'old leak')
        old = git(self.repo, 'rev-parse', 'HEAD')
        (self.repo / 'new.txt').write_text('harmless\n')
        git(self.repo, 'add', 'new.txt')
        git(self.repo, 'commit', '-qm', 'new')
        new = git(self.repo, 'rev-parse', 'HEAD')
        self.assertEqual(run_scan('--repo', str(self.repo), '--range', new, '--not', old)[0], 0)
        self.assertEqual(run_scan('--repo', str(self.repo), '--range', new, '--not', self.base)[0], 1)
        self.assertEqual(run_scan('--repo', str(self.repo), '--tree', new)[0], 1)
        self.assertEqual(run_scan('--repo', str(self.repo), '--tree', self.base)[0], 0)

    def test_manifest_mode_scans_only_listed_files(self):
        root = Path(self.temp.name) / 'tree'
        root.mkdir()
        (root / 'a.txt').write_text('fine\n')
        (root / 'b.txt').write_text(CASES['wg_key'])
        manifest = root / 'm.json'
        manifest.write_text(json.dumps(['a.txt']))
        self.assertEqual(run_scan('--manifest', str(manifest), '--root', str(root))[0], 0)
        manifest.write_text(json.dumps(['a.txt', 'b.txt']))
        self.assertEqual(run_scan('--manifest', str(manifest), '--root', str(root))[0], 1)

    def test_gitflow_privacy_refuses_a_staged_secret(self):
        config = Path(self.temp.name) / 'flow.json'
        config.write_text(json.dumps({'primary': {'remote': 'origin', 'urls': []}, 'secondary': {'remote': 'github', 'urls': []}, 'checks': []}))
        repo = flow.Repo(self.repo, config)
        (self.repo / 'notes.txt').write_text('ok\n')
        git(self.repo, 'add', 'notes.txt')
        repo.privacy()
        (self.repo / 'notes.txt').write_text(CASES['uci_option_secret'])
        git(self.repo, 'add', 'notes.txt')
        with self.assertRaisesRegex(flow.FlowError, 'SECRET-PATTERN-STAGED'):
            repo.privacy()

    def test_sync_plan_refuses_to_publish_a_secret_to_the_secondary_remote(self):
        primary, secondary = Path(self.temp.name) / 'primary.git', Path(self.temp.name) / 'secondary.git'
        for bare in (primary, secondary):
            subprocess.run(['git', 'init', '--bare', '-q', str(bare)], check=True)
        config = Path(self.temp.name) / 'flow.json'
        config.write_text(json.dumps({'primary': {'remote': 'origin', 'urls': [str(primary)]},
                                      'secondary': {'remote': 'github', 'urls': [str(secondary)]}, 'checks': []}))
        git(self.repo, 'remote', 'add', 'origin', str(primary))
        git(self.repo, 'remote', 'add', 'github', str(secondary))
        git(self.repo, 'push', '-q', 'origin', 'main')
        git(self.repo, 'push', '-q', 'github', 'main')
        git(self.repo, 'checkout', '-qb', 'backup/leaky')
        (self.repo / 'leak.txt').write_text(CASES['wg_key'])
        git(self.repo, 'add', 'leak.txt')
        git(self.repo, 'commit', '-qm', 'leak')
        git(self.repo, 'push', '-q', 'origin', 'backup/leaky')
        approval = Path(self.temp.name) / 'approval.json'
        approval.write_text(json.dumps({'allow_publish': True, 'primary_url': str(primary), 'secondary_url': str(secondary),
                                        'expires': __import__('time').time() + 60}))
        repo = flow.Repo(self.repo, config)
        with self.assertRaisesRegex(flow.FlowError, 'SECRET-PATTERN-IN-PUBLICATION'):
            repo.sync_plan(True, approval)
        refs = subprocess.run(['git', '-C', str(secondary), 'for-each-ref', '--format=%(refname)'], capture_output=True, text=True).stdout
        self.assertNotIn('backup/leaky', refs, 'nothing was pushed')

    def test_publication_scans_refuse_secrets_in_tree_and_new_commit(self):
        (self.repo / 'leak.txt').write_text(CASES['wg_key'])
        git(self.repo, 'add', 'leak.txt')
        git(self.repo, 'commit', '-qm', 'leak')
        head = git(self.repo, 'rev-parse', 'HEAD')
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'PUBLICATION-SECRET-SCAN'):
                publish.scan_publication(head, repo=self.repo)
            with self.assertRaisesRegex(ValueError, 'PUBLICATION-SECRET-SCAN'):
                publish.scan_new_commit(head, self.base, repo=self.repo)
        publish.scan_publication(self.base, repo=self.repo)
        publish.scan_new_commit(self.base, self.base, repo=self.repo)


class Wiring(unittest.TestCase):
    def test_hook_ci_and_publication_call_the_scanner_in_order(self):
        hook = (ROOT / '.githooks/pre-commit').read_text(encoding='utf-8')
        self.assertIn('scripts/secret_scan.py --staged', hook)
        self.assertLess(hook.index('secret_scan.py'), hook.index('bump-version.py'))
        self.assertEqual(len(__import__('re').findall(r'secret_scan\.py --staged \|\| \{[^}]*exit 1; \}', hook)), 1, 'the scan blocks the commit')
        # 07.11.2026: the hook only checks the version fingerprint and refuses; it never bumps, renames or stages by itself
        self.assertIn('bump-version.py --check', hook)
        self.assertIn('--fingerprint-only', hook)
        self.assertNotIn('git add', hook)
        self.assertNotIn('SKIPPED', hook, 'a missing scanner must block, not skip (F-07)')
        ci = (ROOT / 'qa/run_offline_ci.py').read_text(encoding='utf-8')
        self.assertIn("'scripts/secret_scan.py','--manifest'", ci)
        main = (ROOT / 'scripts/publish-reviewed.py').read_text(encoding='utf-8')
        self.assertLess(main.index('scan_publication(a.source'), main.index('save(canonical)'))
        self.assertGreater(main.index("save(branch)", main.index('scan_new_commit(public,parent)')), main.index('scan_new_commit(public,parent)'))
        gitflow = (ROOT / 'tools/gitflow.py').read_text(encoding='utf-8')
        self.assertLess(gitflow.index("scanner.range_entries"), gitflow.index("'push','--atomic'"))

    @unittest.skipUnless(shutil.which('sh'), 'POSIX sh is needed to execute the hook')
    def test_hook_refuses_when_the_scanner_is_missing(self):
        # F-07: the old hook printed "SKIPPED" and went on to commit without any secret scan.
        with tempfile.TemporaryDirectory(prefix='homensai-hook-') as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            (root / 'scripts' / 'bump-version.py').write_text('print("VERSION-CURRENT")\n')
            hook = root / 'pre-commit'
            hook.write_bytes((ROOT / '.githooks/pre-commit').read_bytes().replace(b'\r\n', b'\n'))
            env = dict(os.environ, GIT_DIR=str(root / 'no-such-git-dir'))
            result = subprocess.run(['sh', str(hook)], cwd=str(root), capture_output=True, text=True, env=env, timeout=120)
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn('secret scan cannot run', result.stderr)

    @unittest.skipUnless(shutil.which('sh'), 'POSIX sh is needed to execute the hook')
    def test_hook_refuses_a_stale_fingerprint_and_never_bumps(self):
        # 07.11.2026: check-and-refuse. A stale fingerprint stops the commit with the command to run; nothing is edited.
        for stale in (True, False):
            with tempfile.TemporaryDirectory(prefix='homensai-hook-') as directory:
                root = Path(directory)
                (root / 'scripts').mkdir()
                (root / 'scripts' / 'secret_scan.py').write_text('import sys\nsys.exit(0)\n')
                (root / 'scripts' / 'bump-version.py').write_text(
                    'import sys, pathlib\n'
                    'pathlib.Path("calls.txt").open("a").write(" ".join(sys.argv[1:]) + "\\n")\n'
                    'sys.exit(%d if "--check" in sys.argv else 99)\n' % (1 if stale else 0))
                hook = root / 'pre-commit'
                hook.write_bytes((ROOT / '.githooks/pre-commit').read_bytes().replace(b'\r\n', b'\n'))
                env = dict(os.environ, GIT_DIR=str(root / 'no-such-git-dir'), HOMENSAI_TEST_PYTHON=sys.executable)
                # The hook calls `python` (Git for Windows). An image with only python3 (the offline-CI python311 image)
                # gets it as a shell function in front of the sourced hook; a fake file would sit on the noexec tmpfs.
                command = ['sh', str(hook)] if shutil.which('python') else \
                    ['sh', '-c', 'python() { "$HOMENSAI_TEST_PYTHON" "$@"; }; . "$0"', str(hook)]
                result = subprocess.run(command, cwd=str(root), capture_output=True, text=True, env=env, timeout=120)
                calls = (root / 'calls.txt').read_text().split('\n')[:-1]
            self.assertEqual(calls, ['--check'], 'the hook may only run the check, never the bump')
            if stale:
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertIn('python scripts/bump-version.py --fingerprint-only', result.stderr)
                self.assertIn('nothing committed', result.stderr)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_gitignore_hides_secret_files_but_no_tracked_file(self):
        text = (ROOT / '.gitignore').read_text(encoding='utf-8')
        for line in ('.claude/worktrees/', '*.dpapi', '*.enc', '*.tgz', '*.private.*', '*.local.*', 'router-backup*', '*.ovpn'):
            self.assertIn(line, text.splitlines())
        if shutil.which('git') and (ROOT / '.git').exists():
            tracked_ignored = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-ci', '--exclude-standard'],
                                             capture_output=True, text=True).stdout.splitlines()
            hidden = [n for n in tracked_ignored if n.endswith(('.dpapi', '.enc', '.tgz', '.ovpn')) or '.private.' in n
                      or '.local.' in n or 'router-backup' in n or n.startswith('.claude/worktrees/')]
            self.assertEqual(hidden, [])


if __name__ == '__main__':
    unittest.main()
