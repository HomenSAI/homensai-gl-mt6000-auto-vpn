"""Router install path: 02-install.sh signature + release chain checks and homensai-vpn-trust-key, against shell fakes.

usign is the Python twin scripts/signing/pyusign.py (or the real OpenWrt binary when QA_REAL_USIGN names it; the
cross-check run in docs/architecture/SIGNING-2026-11-03.ru.md). CI /tmp is noexec: every fake is a shell function."""
import base64
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/signing'))
import chain  # noqa: E402
import usign_format  # noqa: E402

KIT = ROOT/'router-test-kit/02-install.sh'
TRUST_TOOL = ROOT/'router/files/usr/sbin/homensai-vpn-trust-key'
PYUSIGN = ROOT/'scripts/signing/pyusign.py'
MAIN = usign_format.SecretKey(bytes(range(32)), bytes.fromhex('1111111111111111'))
RESERVE = usign_format.SecretKey(bytes(range(1, 33)), bytes.fromhex('2222222222222222'))
STRANGER = usign_format.SecretKey(bytes(range(2, 34)), bytes.fromhex('3333333333333333'))
COMMIT = 'c'*40

FUNCTIONS = '''
opkg() { printf 'opkg %s\\n' "$*" >> "$QA_CALLS"; case "$1" in status) [ -n "$QA_INSTALLED" ] && printf 'Package: homensai-auto-vpn\\nVersion: %s\\n' "$QA_INSTALLED"; return 0;; install) QA_INSTALLED=$QA_NEW; return 0;; *) return 71;; esac; }
uci() { printf 'uci %s\\n' "$*" >> "$QA_CALLS"; return 1; }
nft() { return 1; }
id() { [ "$1" = -u ] && printf '%s\\n' "$QA_UID"; }
'''
USIGN = '''usign() { "$QA_PYTHON" "$QA_PYUSIGN" "$@"; }\n'''
REAL_USIGN = '''usign() { "$QA_REAL_USIGN" "$@"; }\n'''


def build_chain(packages, signer=MAIN, revoked=None, signers=None, evidence=None):
    lines, entries = [], []
    for index, payload in enumerate(packages):
        key = (signers or {}).get(index, signer)
        version = '2.1.0-alpha%d' % (index+1)
        entry = chain.next_entry(entries, 'homensai-auto-vpn_%s-1_all.ipk' % version, version, version+'-1',
                                 hashlib.sha256(payload).hexdigest(), len(payload), COMMIT, '2026-11-03T12:00:00Z',
                                 key.key_id.hex(), origin='release', revoked=(revoked or {}).get(index, ''),
                                 evidence_sha256=(evidence or {}).get(index))
        lines.append(chain.make_line(entry, key))
        entries.append(entry)
    return b'\n'.join(lines)+b'\n'


def kit_item(key):
    return '%s:%s' % (key.key_id.hex(), base64.b64encode(usign_format.PublicKey(key.public, key.key_id).to_bytes()).decode())


@unittest.skipUnless(os.name == 'posix' and shutil.which('sh') and shutil.which('sha256sum'), 'isolated POSIX harness required')
class InstallSignatureTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.packages = [b'old package %d\n' % index for index in range(3)]+[b'new package bytes\n'*50]
        self.ipk = self.root/'homensai-auto-vpn_2.1.0-alpha4-1_all.ipk'
        self.ipk.write_bytes(self.packages[-1])
        (self.root/'kit').mkdir()
        (self.root/'kit/fingerprint.before').write_text('baseline\n')
        self.keys_dir, self.local_dir = self.root/'etc/keys', self.root/'etc/keys.local'
        self.installed_chain = self.root/'etc/chain.jsonl'
        self.write_chain(build_chain(self.packages))
        self.sign()
        self.trusted, self.revoked = [MAIN, RESERVE], ''

    def write_chain(self, data):
        (self.root/'CHAIN.jsonl').write_bytes(data)

    def sign(self, key=MAIN, data=None):
        Path(str(self.ipk)+'.sig').write_bytes(key.sign_file(self.packages[-1] if data is None else data))

    def script(self):
        payload = self.packages[-1]
        text = KIT.read_text(encoding='utf-8')
        replaced = []
        for line in text.split('\n'):
            name = line.split('=', 1)[0]
            values = {'EXPECTED_SHA': hashlib.sha256(payload).hexdigest(), 'EXPECTED_SIZE': str(len(payload)),
                      'EXPECTED_VERSION': '2.1.0-alpha4-1', 'TRUSTED_KEYS': "'%s'" % ' '.join(kit_item(key) for key in self.trusted),
                      'REVOKED_KEYS': "'%s'" % self.revoked}
            replaced.append(name+'='+values[name] if name in values and '=' in line and not line.startswith('#') else line)
        path = self.root/'02-install.sh'
        path.write_text('\n'.join(replaced), encoding='utf-8')
        return path

    def run_kit(self, *args, usign=True, installed=''):
        calls = self.root/'calls'
        if calls.exists():
            calls.unlink()
        real = os.environ.get('QA_REAL_USIGN')
        functions = FUNCTIONS+((REAL_USIGN if real else USIGN) if usign else '')
        env = dict(os.environ, QA_CALLS=str(calls), QA_PYTHON=sys.executable, QA_PYUSIGN=str(PYUSIGN), QA_INSTALLED=installed,
                   QA_NEW='2.1.0-alpha4-1', HOMENSAI_KIT=str(self.root/'kit'), HOMENSAI_KEYS=str(self.keys_dir),
                   HOMENSAI_LOCAL_KEYS=str(self.local_dir), HOMENSAI_CHAIN=str(self.installed_chain), PATH='/usr/bin:/bin')
        result = subprocess.run(['sh', '-c', functions+'script=$1; shift; . "$script"', 'kit-harness', str(self.script()), str(self.ipk)]+list(args),
                                env=env, cwd=self.root, capture_output=True, text=True, timeout=300)
        self.installed = calls.exists() and any(line.startswith('opkg install') for line in calls.read_text().splitlines())
        return result

    def assertRefused(self, result, code, exit_code):
        self.assertEqual(result.returncode, exit_code, result.stdout+result.stderr)
        self.assertIn('STOP: '+code, result.stderr)
        self.assertFalse(self.installed, 'opkg install must not run after a refusal')

    def install_keys(self, *keys):
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        for key in keys:
            (self.keys_dir/key.key_id.hex()).write_bytes(key.public_file('test key'))

    # -- valid / missing ----------------------------------------------------------------------------------------------
    def test_valid_signature_and_chain_install_and_record_history(self):
        result = self.run_kit()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertTrue(self.installed)
        self.assertIn('release chain verified: 4 entries', result.stdout)
        self.assertIn('package signature verified (key 1111111111111111)', result.stdout)
        self.assertEqual(self.installed_chain.read_bytes(), (self.root/'CHAIN.jsonl').read_bytes())

    def test_missing_signature_requires_explicit_flag(self):
        Path(str(self.ipk)+'.sig').unlink()
        self.assertRefused(self.run_kit(), 'SIGNATURE-MISSING', 20)
        result = self.run_kit('--allow-unsigned')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('WARNING: SIGNATURE-MISSING', result.stdout)
        self.assertTrue(self.installed)

    def test_missing_chain_requires_explicit_flag_but_present_signature_is_still_checked(self):
        (self.root/'CHAIN.jsonl').unlink()
        self.assertRefused(self.run_kit(), 'SIGNATURE-MISSING', 20)
        self.sign(STRANGER)
        self.assertRefused(self.run_kit('--allow-unsigned'), 'SIGNATURE-KEY-UNTRUSTED', 22)
        self.assertFalse(self.installed_chain.exists())

    def test_present_signature_without_usign_fails_closed(self):
        self.assertRefused(self.run_kit(usign=False), 'SIGNATURE-TOOL-MISSING', 24)

    def test_unknown_option_refused(self):
        result = self.run_kit('--force')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.installed)

    # -- package signature ---------------------------------------------------------------------------------------------
    def test_wrong_package_signature_refused(self):
        self.sign(data=b'other bytes')
        self.assertRefused(self.run_kit(), 'SIGNATURE-INVALID', 21)

    def test_garbage_signature_refused(self):
        Path(str(self.ipk)+'.sig').write_text('untrusted comment: x\nAAAA\n')
        self.assertRefused(self.run_kit(), 'SIGNATURE-INVALID', 21)

    def test_untrusted_package_key_refused(self):
        self.sign(STRANGER)
        self.assertRefused(self.run_kit(), 'SIGNATURE-KEY-UNTRUSTED', 22)

    def test_revoked_package_key_refused(self):
        self.revoked = '1111111111111111:3'
        self.write_chain(build_chain(self.packages, signers={3: RESERVE}))
        self.assertRefused(self.run_kit(), 'SIGNATURE-KEY-REVOKED', 23)
        self.sign(RESERVE)
        self.assertEqual(self.run_kit().returncode, 0)

    # -- release chain ------------------------------------------------------------------------------------------------
    def chain_lines(self):
        return (self.root/'CHAIN.jsonl').read_bytes().split(b'\n')[:-1]

    def put_lines(self, lines):
        self.write_chain(b'\n'.join(lines)+b'\n')

    def test_tampered_field_refused(self):
        for old, new in ((b'"size":', b'"size":1'), (b'"date_utc":"2026', b'"date_utc":"2027'), (b'"origin":"release"', b'"origin":"imported"')):
            with self.subTest(field=old):
                lines = self.chain_lines()
                lines[1] = lines[1].replace(old, new, 1)
                self.put_lines(lines)
                self.assertRefused(self.run_kit(), 'CHAIN-SIGNATURE-INVALID', 25)

    def test_reordered_and_dropped_entries_refused(self):
        lines = self.chain_lines()
        self.put_lines([lines[0], lines[2], lines[1], lines[3]])
        self.assertRefused(self.run_kit(), 'CHAIN-SEQ-GAP', 25)
        self.put_lines([lines[0], lines[2], lines[3]])
        self.assertRefused(self.run_kit(), 'CHAIN-SEQ-GAP', 25)

    def test_resigned_rewritten_entry_breaks_the_link(self):
        entries = chain.verify_chain((self.root/'CHAIN.jsonl').read_bytes(), {MAIN.key_id.hex(): MAIN})
        entries[1]['sha256'] = 'e'*64
        lines = self.chain_lines()
        lines[1] = chain.make_line(entries[1], MAIN)
        self.put_lines(lines)
        self.assertRefused(self.run_kit(), 'CHAIN-PREV-MISMATCH', 25)

    def test_malformed_line_refused(self):
        lines = self.chain_lines()
        self.put_lines(lines[:2]+[lines[2]+b' ']+lines[3:])
        self.assertRefused(self.run_kit(), 'CHAIN-FORMAT', 25)

    def test_untrusted_and_revoked_chain_keys_refused(self):
        self.write_chain(build_chain(self.packages, signers={1: STRANGER}))
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-UNTRUSTED', 25)
        self.write_chain(build_chain(self.packages, revoked={3: '1111111111111111:2'}, signers={3: RESERVE}))
        self.sign(RESERVE)
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-REVOKED', 25)
        self.write_chain(build_chain(self.packages, revoked={3: '1111111111111111:3'}, signers={3: RESERVE}))
        self.assertEqual(self.run_kit().returncode, 0, 'history signed before the revocation stays valid')

    # -- signed link to the test-evidence manifest (optional field evidence_sha256) -------------------------------------
    EVIDENCE = {1: 'ab'*32, 3: '0123456789abcdef'*4}

    def test_entries_with_and_without_evidence_install(self):
        self.write_chain(build_chain(self.packages, evidence=self.EVIDENCE))
        self.assertIn(b'"evidence_sha256":"'+b'ab'*32+b'"', self.chain_lines()[1])
        self.assertNotIn(b'evidence_sha256', self.chain_lines()[0])
        result = self.run_kit()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('release chain verified: 4 entries', result.stdout)
        self.assertEqual(self.installed_chain.read_bytes(), (self.root/'CHAIN.jsonl').read_bytes())

    def test_evidence_link_is_covered_by_the_signature(self):
        self.write_chain(build_chain(self.packages, evidence=self.EVIDENCE))
        original = self.chain_lines()
        lines = list(original)
        lines[3] = lines[3].replace(b'0123456789abcdef', b'0123456789abcdee', 1)    # another manifest hash
        self.put_lines(lines)
        self.assertRefused(self.run_kit(), 'CHAIN-SIGNATURE-INVALID', 25)
        lines = list(original)
        lines[1] = lines[1].replace(b'"evidence_sha256":"'+b'ab'*32+b'",', b'', 1)    # the link quietly removed
        self.put_lines(lines)
        self.assertRefused(self.run_kit(), 'CHAIN-SIGNATURE-INVALID', 25)
        lines = list(original)
        lines[0] = lines[0].replace(b'"key_id":', b'"evidence_sha256":"'+b'cd'*32+b'","key_id":', 1)   # a link added to old history
        self.put_lines(lines)
        self.assertRefused(self.run_kit(), 'CHAIN-SIGNATURE-INVALID', 25)

    def test_revocation_declared_in_an_entry_with_evidence_applies(self):
        self.write_chain(build_chain(self.packages, revoked={3: '1111111111111111:2'}, signers={3: RESERVE}, evidence={3: 'ab'*32}))
        self.sign(RESERVE)
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-REVOKED', 25)
        self.write_chain(build_chain(self.packages, revoked={3: '1111111111111111:3'}, signers={3: RESERVE}, evidence={3: 'ab'*32}))
        result = self.run_kit()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_misplaced_or_malformed_evidence_field_refused(self):
        self.write_chain(build_chain(self.packages, evidence=self.EVIDENCE))
        original = self.chain_lines()
        field = b'"evidence_sha256":"'+b'ab'*32+b'",'
        for label, line in (('after key_id', original[1].replace(field, b'', 1).replace(b'"origin":', field+b'"origin":', 1)),
                            ('upper case', original[1].replace(b'ab'*32, b'AB'*32, 1)),
                            ('short', original[1].replace(b'ab'*32, b'ab'*31, 1)),
                            ('twice', original[1].replace(field, field+field, 1))):
            with self.subTest(label):
                lines = list(original)
                lines[1] = line
                self.put_lines(lines)
                self.assertRefused(self.run_kit(), 'CHAIN-FORMAT', 25)

    def test_package_that_is_not_the_head_refused(self):
        self.write_chain(build_chain(self.packages[:-1]+[b'another package\n']))
        self.assertRefused(self.run_kit(), 'CHAIN-HEAD-MISMATCH', 26)

    def test_forked_history_refused(self):
        self.installed_chain.parent.mkdir(parents=True)
        self.installed_chain.write_bytes(build_chain(self.packages[:2]+[b'a different third release\n']))
        self.assertRefused(self.run_kit(), 'CHAIN-FORK', 27)

    def test_extending_history_accepted(self):
        self.installed_chain.parent.mkdir(parents=True)
        self.installed_chain.write_bytes(build_chain(self.packages[:3]))
        result = self.run_kit(installed='2.1.0-alpha3-1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('extends the installed history (3 -> 4 entries)', result.stdout)

    def test_rollback_needs_downgrade_flag(self):
        self.installed_chain.parent.mkdir(parents=True)
        self.installed_chain.write_bytes(build_chain(self.packages+[b'fifth\n']))
        self.assertRefused(self.run_kit(), 'CHAIN-DOWNGRADE', 28)
        result = self.run_kit('--allow-downgrade')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('WARNING: downgrade', result.stdout)

    # -- trust anchors ------------------------------------------------------------------------------------------------
    def test_upgrade_trusts_installed_keys_not_the_kit(self):
        self.install_keys(RESERVE)
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-UNTRUSTED', 25)
        self.install_keys(MAIN)
        self.assertEqual(self.run_kit().returncode, 0)

    def install_local_keys(self, *keys):
        self.local_dir.mkdir(parents=True, exist_ok=True)
        for key in keys:
            (self.local_dir/key.key_id.hex()).write_bytes(key.public_file('administrator key'))

    def test_local_keys_alone_do_not_hide_the_kit_keys(self):
        # a firmware upgrade keeps keys.local (keep.d) and loses keys/: the official release still installs
        self.install_local_keys(STRANGER)
        result = self.run_kit()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('release keys (first-install)', result.stdout)

    def test_local_keys_are_added_on_top_in_both_modes(self):
        self.write_chain(build_chain(self.packages, signers={3: STRANGER}))
        self.sign(STRANGER)
        self.install_local_keys(STRANGER)
        self.assertEqual(self.run_kit().returncode, 0, 'first install')
        self.install_keys(MAIN)
        result = self.run_kit()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('release keys (upgrade)', result.stdout)

    def test_only_the_installed_keys_mean_an_upgrade_and_the_kit_stays_out_of_it(self):
        self.install_keys(RESERVE)
        self.install_local_keys(STRANGER)
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-UNTRUSTED', 25)

    def test_a_local_revocation_outlives_a_firmware_upgrade(self):
        self.install_local_keys(STRANGER)
        (self.local_dir/'revoked').write_text('1111111111111111:0\n')
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-REVOKED', 25)

    def test_the_kept_history_still_refuses_a_rollback_after_a_firmware_upgrade(self):
        # keys/ gone, chain.jsonl kept: the kit keys check the chain, the history stops the older package
        self.installed_chain.parent.mkdir(parents=True)
        self.installed_chain.write_bytes(build_chain(self.packages+[b'fifth\n']))
        self.assertRefused(self.run_kit(), 'CHAIN-DOWNGRADE', 28)
        kept = (ROOT/'router/files/lib/upgrade/keep.d/homensai-vpn').read_text(encoding='ascii').splitlines()
        default = [line for line in KIT.read_text(encoding='utf-8').splitlines() if line.startswith('INSTALLED_CHAIN=')]
        self.assertEqual(default, ['INSTALLED_CHAIN=${HOMENSAI_CHAIN:-/etc/homensai-vpn/chain.jsonl}'])
        self.assertIn('/etc/homensai-vpn/chain.jsonl', kept)

    def test_installed_revocation_list_applies(self):
        self.install_keys(MAIN, RESERVE)
        (self.keys_dir/'revoked').write_text('# test\n1111111111111111:0\n')
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-REVOKED', 25)

    def test_damaged_revocation_list_fails_closed(self):
        self.revoked = '1111111111111111:x'
        self.assertRefused(self.run_kit(), 'CHAIN-FORMAT', 25)

    # -- homensai-vpn-trust-key ---------------------------------------------------------------------------------------
    def trust(self, *args, answer='', uid='0'):
        functions = FUNCTIONS+(REAL_USIGN if os.environ.get('QA_REAL_USIGN') else USIGN)
        env = dict(os.environ, QA_PYTHON=sys.executable, QA_PYUSIGN=str(PYUSIGN), QA_UID=uid, QA_CALLS=str(self.root/'calls'),
                   HOMENSAI_KEYS=str(self.keys_dir), HOMENSAI_LOCAL_KEYS=str(self.local_dir), PATH='/usr/bin:/bin')
        return subprocess.run(['sh', '-c', functions+'script=$1; shift; . "$script"', 'trust-harness', str(TRUST_TOOL)]+list(args),
                              env=env, input=answer+'\n', capture_output=True, text=True, timeout=60)

    def test_trust_key_requires_typed_key_id_and_then_install_accepts_new_key(self):
        self.install_keys(MAIN)
        self.write_chain(build_chain(self.packages, signers={3: STRANGER}))
        self.sign(STRANGER)
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-UNTRUSTED', 25)
        pub = self.root/'new.pub'
        pub.write_bytes(STRANGER.public_file('HomenS.AI Auto VPN release key main 3333333333333333'))
        cancelled = self.trust('add', str(pub), answer='y')
        self.assertEqual(cancelled.returncode, 3, cancelled.stdout+cancelled.stderr)
        self.assertIn(usign_format.PublicKey(STRANGER.public, STRANGER.key_id).full_fingerprint(), cancelled.stdout)
        self.assertFalse((self.local_dir/'3333333333333333').exists())
        self.assertEqual(self.trust('add', str(pub), answer='3333333333333333', uid='1000').returncode, 1)
        done = self.trust('add', str(pub), answer='3333333333333333')
        self.assertEqual(done.returncode, 0, done.stdout+done.stderr)
        self.assertIn('TRUSTED: 3333333333333333', done.stdout)
        self.assertEqual(self.run_kit().returncode, 0)
        shown = self.trust('show')
        self.assertIn('3333333333333333', shown.stdout)

    def test_trust_key_refuses_revoked_and_malformed_keys(self):
        self.install_keys(MAIN)
        (self.keys_dir/'revoked').write_text('3333333333333333:5\n')
        pub = self.root/'new.pub'
        pub.write_bytes(STRANGER.public_file('x'))
        result = self.trust('add', str(pub), answer='3333333333333333')
        self.assertIn('TRUST-KEY-REVOKED', result.stderr)
        pub.write_text('untrusted comment: x\nnot a key\n')
        self.assertIn('TRUST-KEY-FORMAT', self.trust('add', str(pub), answer='x').stderr)

    def test_trust_key_revoke_is_honoured_by_install(self):
        self.install_keys(MAIN, RESERVE)
        self.assertEqual(self.trust('revoke', '1111111111111111', '2').returncode, 0)
        self.assertRefused(self.run_kit(), 'CHAIN-KEY-REVOKED', 25)


class KitConsistencyTests(unittest.TestCase):
    def test_kit_keys_equal_the_package_keys(self):
        import keytool
        trusted, revoked = keytool.kit_literals(ROOT)
        text = KIT.read_text(encoding='utf-8')
        self.assertIn('\n'+trusted+'\n', text)
        self.assertIn('\n'+revoked+'\n', text)

    def test_kit_line_expression_equals_python_shape(self):
        # The sed expression in 02-install.sh and chain.LINE must describe the same fields in the same order.
        text = KIT.read_text(encoding='utf-8')
        for field in chain.ENTRY_KEYS:
            self.assertIn('"%s":' % field, text)
        self.assertIn('\\{99\\}=', text)
        self.assertIn('"%s"' % chain.EVIDENCE_KEY, text)   # the optional link is handled by the kit as well
