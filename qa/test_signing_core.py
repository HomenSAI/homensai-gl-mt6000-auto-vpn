"""Release signing on the PC: Ed25519/usign format, release chain, TOTP gate, secret payload, keytool commands.

Offline. The DPAPI store is replaced by a reversible test protector (DPAPI itself is exercised only on Windows)."""
import base64
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
import chain  # noqa: E402
import keytool  # noqa: E402
import secret_store  # noqa: E402
import totp  # noqa: E402
import usign_format as u  # noqa: E402

RFC8032 = [  # RFC 8032 section 7.1, tests 1-3 and SHA(abc)
    ('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60', 'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a', '',
     'e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b'),
    ('4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb', '3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c', '72',
     '92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00'),
    ('c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7', 'fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025', 'af82',
     '6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a'),
    ('833fe62409237b9d62ec77587520911e9a759cec1d19755b7da901b96dca3d42', 'ec172b93ad5e563bf4932c70e1245034c35467ef2efd4d64ebf819683467e2bf',
     'ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f',
     'dc2a4459e7369633a52b1bf277839a00201009a3efbf3ecb69bea2186c26b58909351fc9ac90b3ecfdfbc7c66431e0303dca179c138ac17ad9bef1177331a704'),
]
# A usign 2020 key pair and signature made by the real OpenWrt 21.02.7 SDK usign (docs/architecture/SIGNING-2026-11-03.ru.md).
REAL_PUB = b'untrusted comment: real test\nRWQgGCxsOW/r4/YReqJSKs/pz9OoReQWqicn/fZGx6qgW8M+oEOogbq8\n'
REAL_MESSAGE = b'HomenS.AI usign interoperability vector\n'
REAL_SIG = (b'untrusted comment: signed by key 20182c6c396febe3\n'
            b'RWQgGCxsOW/r45t4P0w2wihEHcyqro9OlQiFT4Pc+wQYrmRnsVlFggLNGCb5sy52CrAdmwWYoMxkUoqKUtl5T9Ji7w2TJBNtQAE=\n')


class Ed25519Tests(unittest.TestCase):
    def test_rfc8032_vectors(self):
        for seed, public, message, signature in RFC8032:
            seed, public, message, signature = map(bytes.fromhex, (seed, public, message, signature))
            self.assertEqual(u.public_key(seed), public)
            self.assertEqual(u.sign(seed, message), signature)
            self.assertTrue(u.verify(public, message, signature))
            self.assertFalse(u.verify(public, message+b'x', signature))
            for index in (0, 31, 32, 63):
                broken = bytearray(signature)
                broken[index] ^= 1
                self.assertFalse(u.verify(public, message, bytes(broken)))

    def test_non_canonical_s_rejected(self):
        seed, public, message, signature = map(bytes.fromhex, RFC8032[0])
        s = int.from_bytes(signature[32:], 'little')+u.L
        self.assertFalse(u.verify(public, message, signature[:32]+s.to_bytes(32, 'little')))


class UsignFormatTests(unittest.TestCase):
    def test_round_trip_and_layout(self):
        key = u.SecretKey.generate()
        self.assertEqual(len(base64.b64decode(key.to_file('c').split(b'\n')[1])), 104)
        again = u.SecretKey.from_file(key.to_file('comment'))
        self.assertEqual((again.seed, again.key_id, again.public), (key.seed, key.key_id, key.public))
        public = u.PublicKey.from_file(key.public_file('p'))
        signature = key.sign_file(b'payload')
        self.assertTrue(signature.startswith(b'untrusted comment: signed by key %s\n' % key.key_id.hex().encode()))
        self.assertEqual(u.verify_file({public.key_id.hex(): public}, b'payload', signature), key.key_id.hex())
        # Same seed clamping as usign generate().
        self.assertEqual(key.seed[0] & 7, 0)
        self.assertEqual(key.seed[31] & 0xc0, 0x40)

    def test_secret_checksum_and_public_mismatch_detected(self):
        raw = bytearray(base64.b64decode(u.SecretKey.generate().to_file('c').split(b'\n')[1]))
        raw[50] ^= 1
        with self.assertRaisesRegex(ValueError, 'USIGN-SECRET-CHECKSUM'):
            u.SecretKey.from_file(b'untrusted comment: c\n'+base64.b64encode(bytes(raw))+b'\n')

    def test_verify_file_codes(self):
        key, other = u.SecretKey.generate(), u.SecretKey.generate()
        keys = {key.key_id.hex(): u.PublicKey(key.public, key.key_id)}
        with self.assertRaisesRegex(ValueError, 'SIGNATURE-KEY-UNTRUSTED'):
            u.verify_file(keys, b'm', other.sign_file(b'm'))
        with self.assertRaisesRegex(ValueError, 'SIGNATURE-KEY-REVOKED'):
            u.verify_file(keys, b'm', key.sign_file(b'm'), revoked=[key.key_id.hex()])
        with self.assertRaisesRegex(ValueError, 'SIGNATURE-INVALID'):
            u.verify_file(keys, b'n', key.sign_file(b'm'))
        with self.assertRaisesRegex(ValueError, 'USIGN-SIGNATURE-FORMAT'):
            u.verify_file(keys, b'm', b'untrusted comment: x\nAAAA\n')

    def test_real_usign_vector(self):
        public = u.PublicKey.from_file(REAL_PUB)
        self.assertEqual(public.key_id.hex(), '20182c6c396febe3')
        self.assertEqual(u.verify_file({'20182c6c396febe3': public}, REAL_MESSAGE, REAL_SIG), '20182c6c396febe3')
        with self.assertRaises(ValueError):
            u.verify_file({'20182c6c396febe3': public}, REAL_MESSAGE+b'!', REAL_SIG)


def make_chain(count, key, revoked=None, signers=None):
    lines, entries = [], []
    for index in range(count):
        signer = (signers or {}).get(index, key)
        entry = chain.next_entry(entries, 'homensai-auto-vpn_1.0.%d-1_all.ipk' % index, '1.0.%d' % index, '1.0.%d-1' % index,
                                 hashlib.sha256(b'%d' % index).hexdigest(), 10+index, 'a'*40, '2026-11-03T00:00:00Z',
                                 signer.key_id.hex(), revoked=(revoked or {}).get(index, ''))
        lines.append(chain.make_line(entry, signer))
        entries.append(entry)
    return b'\n'.join(lines)+b'\n'


class ChainTests(unittest.TestCase):
    main = u.SecretKey(bytes(range(32)), bytes.fromhex('1111111111111111'))
    reserve = u.SecretKey(bytes(range(1, 33)), bytes.fromhex('2222222222222222'))
    stranger = u.SecretKey(bytes(range(2, 34)), bytes.fromhex('3333333333333333'))

    def keys(self, *keys):
        return {key.key_id.hex(): u.PublicKey(key.public, key.key_id) for key in (keys or (self.main, self.reserve))}

    def code(self, data, keys=None, revoked=()):
        with self.assertRaises(chain.ChainError) as caught:
            chain.verify_chain(data, keys or self.keys(), revoked)
        return caught.exception.code

    def test_valid_chain(self):
        entries = chain.verify_chain(make_chain(5, self.main), self.keys())
        self.assertEqual([entry['seq'] for entry in entries], list(range(5)))
        self.assertEqual(entries[0]['prev'], '0'*64)
        self.assertEqual(entries[1]['prev'], chain.entry_hash(entries[0]))

    def test_every_field_is_covered(self):
        data = make_chain(3, self.main)
        lines = data.split(b'\n')
        for field, value in (('artifact', b'"x.ipk"'), ('date_utc', b'"2020-01-01T00:00:00Z"'), ('version', b'"9.9.9"'),
                             ('package_version', b'"9.9.9-1"'), ('sha256', b'"%s"' % (b'0'*64)), ('size', b'99'),
                             ('source_commit', b'"%s"' % (b'b'*40)), ('origin', b'"imported"')):
            entry = json.loads(lines[1][len(b'{"entry":'):lines[1].index(b',"sig"')])
            entry[field] = json.loads(value)
            tampered = b'{"entry":'+chain.canonical(entry)+lines[1][lines[1].index(b',"sig"'):]
            with self.subTest(field=field):
                self.assertEqual(self.code(b'\n'.join([lines[0], tampered, lines[2], b''])), 'CHAIN-SIGNATURE-INVALID')

    def test_distinct_codes(self):
        lines = make_chain(4, self.main).split(b'\n')[:-1]
        join = lambda items: b'\n'.join(items)+b'\n'
        self.assertEqual(self.code(b''), 'CHAIN-EMPTY')
        self.assertEqual(self.code(join([lines[0], lines[2], lines[1], lines[3]])), 'CHAIN-SEQ-GAP')
        self.assertEqual(self.code(join([lines[0], lines[1], lines[3]])), 'CHAIN-SEQ-GAP')
        self.assertEqual(self.code(join(lines[1:])), 'CHAIN-SEQ-GAP')
        self.assertEqual(self.code(join(lines[:2]+[lines[2]+b' '])), 'CHAIN-FORMAT')
        self.assertEqual(self.code(join(lines).replace(b'\n', b'\r\n')), 'CHAIN-FORMAT')
        self.assertEqual(self.code(join(lines), keys=self.keys(self.reserve)), 'CHAIN-KEY-UNTRUSTED')
        self.assertEqual(self.code(join(lines), revoked={('1111111111111111', 2)}), 'CHAIN-KEY-REVOKED')
        self.assertEqual(self.code(make_chain(3, self.main, signers={1: self.stranger})), 'CHAIN-KEY-UNTRUSTED')
        # A rewritten entry re-signed by a trusted key no longer matches the next entry's link.
        entries = chain.verify_chain(join(lines), self.keys())
        entries[1]['size'] = 1
        self.assertEqual(self.code(join([lines[0], chain.make_line(entries[1], self.main)]+lines[2:])), 'CHAIN-PREV-MISMATCH')
        # A signature by key A presented as key B is refused even when both are trusted.
        signature = lines[1][lines[1].index(b',"sig"'):]
        swapped = b'{"entry":'+chain.canonical(dict(entries[1], key_id='2222222222222222'))+signature
        self.assertEqual(self.code(join([lines[0], swapped])), 'CHAIN-KEY-MISMATCH')
        duplicate = dict(chain.verify_chain(join(lines[:2]), self.keys())[1])
        third = chain.next_entry([entries[0], duplicate], 'a.ipk', '1.0.1', '1.0.1-1', 'f'*64, 1, 'a'*40, '2026-11-03T00:00:00Z', '1111111111111111')
        self.assertEqual(self.code(join(lines[:2]+[chain.make_line(third, self.main)])), 'CHAIN-DUPLICATE-VERSION')

    def test_revocation_is_bounded_by_seq_and_declared_in_chain(self):
        data = make_chain(4, self.main, revoked={3: '1111111111111111:3'}, signers={3: self.reserve})
        self.assertEqual(len(chain.verify_chain(data, self.keys())), 4)
        data = make_chain(4, self.main, revoked={3: '1111111111111111:2'}, signers={3: self.reserve})
        self.assertEqual(self.code(data), 'CHAIN-KEY-REVOKED')
        with self.assertRaisesRegex(ValueError, 'CHAIN-REVOCATION-FORMAT'):
            chain.parse_revocations('111:2')

    def test_head_and_history_checks(self):
        data = make_chain(3, self.main)
        entries = chain.verify_chain(data, self.keys())
        self.assertEqual(chain.check_head(entries, (hashlib.sha256(b'2').hexdigest(), 12), '1.0.2-1')['seq'], 2)
        with self.assertRaises(chain.ChainError):
            chain.check_head(entries, b'other')
        shorter, other = make_chain(2, self.main), make_chain(3, self.reserve)
        self.assertEqual(chain.check_extends(shorter, data), 'extends')
        self.assertEqual(chain.check_extends(data, data), 'same')
        with self.assertRaisesRegex(chain.ChainError, 'CHAIN-DOWNGRADE'):
            chain.check_extends(data, shorter)
        self.assertEqual(chain.check_extends(data, shorter, allow_downgrade=True), 'downgrade')
        with self.assertRaisesRegex(chain.ChainError, 'CHAIN-FORK'):
            chain.check_extends(data, other)


class TotpTests(unittest.TestCase):
    def test_rfc6238_sha1_vectors(self):
        key = b'12345678901234567890'
        for moment, expected in ((59, '94287082'), (1111111109, '07081804'), (1111111111, '14050471'),
                                 (1234567890, '89005924'), (2000000000, '69279037'), (20000000000, '65353130')):
            self.assertEqual(totp.totp(key, moment, digits=8), expected)

    def test_rfc4226_hotp_vectors(self):
        expected = ['755224', '287082', '359152', '969429', '338314', '254676', '287922', '162583', '399871', '520489']
        self.assertEqual([totp.hotp(b'12345678901234567890', counter) for counter in range(10)], expected)

    def test_gate_skew_replay_and_lockout(self):
        with tempfile.TemporaryDirectory() as directory:
            state = os.path.join(directory, 'state.json')
            seed = totp.new_seed()
            key = totp.seed_bytes(seed)
            now = 1_800_000_000
            self.assertEqual(totp.check_code(seed, totp.totp(key, now-30), state, now), now//30-1)
            with self.assertRaisesRegex(totp.TotpError, 'TOTP-REPLAYED'):
                totp.check_code(seed, totp.totp(key, now-30), state, now)
            totp.check_code(seed, totp.totp(key, now+30), state, now)
            with self.assertRaisesRegex(totp.TotpError, 'TOTP-WRONG-CODE'):
                totp.check_code(seed, totp.totp(key, now+90), state, now)
            with self.assertRaisesRegex(totp.TotpError, 'TOTP-CODE-FORMAT'):
                totp.check_code(seed, '12ab56', state, now)
            for _ in range(3):
                with self.assertRaisesRegex(totp.TotpError, 'TOTP-WRONG-CODE'):
                    totp.check_code(seed, '000000' if totp.totp(key, now+60) != '000000' else '111111', state, now+60)
            with self.assertRaisesRegex(totp.TotpError, 'TOTP-LOCKED'):
                totp.check_code(seed, '000000' if totp.totp(key, now+60) != '000000' else '111111', state, now+60)
            with self.assertRaisesRegex(totp.TotpError, 'TOTP-LOCKED'):
                totp.check_code(seed, totp.totp(key, now+90), state, now+90)
            self.assertTrue(totp.check_code(seed, totp.totp(key, now+700), state, now+700))
            with open(state, 'w') as stream:
                stream.write('{broken')
            with self.assertRaisesRegex(totp.TotpError, 'TOTP-LOCKED'):
                totp.check_code(seed, totp.totp(key, now+800), state, now+800)

    def test_otpauth_uri(self):
        uri = totp.otpauth_uri('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567')
        self.assertTrue(uri.startswith('otpauth://totp/HomenS.AI%20Auto%20VPN:release-signing?secret=ABCDEFGHIJKLMNOPQRSTUVWXYZ234567&issuer=HomenS.AI'))


class PayloadTests(unittest.TestCase):
    def test_round_trip_typo_and_layout(self):
        key = u.SecretKey.generate()
        text = keytool.secret_payload('reserve', key)
        self.assertRegex(text, r'^HSAI-SK1:RESERVE:[0-9A-F]{16}:[A-Z2-7]{52}:[A-Z2-7]{8}$')
        name, again = keytool.parse_payload(keytool.grouped(text).lower())
        self.assertEqual((name, again.public, again.key_id), ('reserve', key.public, key.key_id))
        for index in (20, 40, 80):
            broken = text[:index]+('A' if text[index] != 'A' else 'B')+text[index+1:]
            with self.assertRaises(ValueError):
                keytool.parse_payload(broken)

    def test_qr_alphanumeric_fits_paper(self):
        import qr
        matrix = qr.encode(keytool.secret_payload('main', u.SecretKey.generate()), ecc='Q')
        self.assertLessEqual(len(matrix), 41)  # version 6 or less at ECC Q


def fake_store(directory):
    # Reversible stand-in for DPAPI; never a real protection, only for tests.
    return secret_store.Store(directory, protect=lambda data: b'T'+data[::-1], unprotect=lambda blob: blob[1:][::-1])


class Console:
    def __init__(self, codes=(), secrets=()):
        self.codes, self.secrets, self.lines, self.qrs = list(codes), list(secrets), [], []

    def code(self, prompt=''):
        value = self.codes.pop(0)
        return value() if callable(value) else value

    def secret(self, prompt):
        return self.secrets.pop(0)

    def confirm(self, prompt):
        return ''

    def say(self, text=''):
        self.lines.append(text)

    def show_qr(self, text, mode, title):
        self.qrs.append(text)


@unittest.skipUnless(shutil.which('git'), 'git required')
class KeytoolTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)/'repo'
        (self.root/'releases').mkdir(parents=True)
        (self.root/'router-test-kit').mkdir()
        (self.root/'router-test-kit/02-install.sh').write_text("#!/bin/sh\nTRUSTED_KEYS=''\nREVOKED_KEYS=''\n")
        self.git('init', '-q')
        for index in (1, 2):
            payload = b'package %d\n' % index
            name = 'homensai-auto-vpn_1.0.0-alpha%d-1_all.ipk' % index
            (self.root/'releases'/name).write_bytes(payload)
            (self.root/'releases'/(name+'.sha256')).write_text(hashlib.sha256(payload).hexdigest()+'  '+name+'\n')
            self.git('add', '-A')
            self.git('commit', '-q', '-m', 'record %d' % index)
        self.store = fake_store(Path(self.directory.name)/'store')
        self.now = [1_900_000_000]
        patcher = mock.patch.object(totp.time, 'time', lambda: self.now[0])
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.name=QA', '-c', 'user.email=qa@example.invalid']+list(args), cwd=self.root,
                              capture_output=True, text=True, check=True, timeout=60).stdout.strip()

    def run_tool(self, argv, console):
        with mock.patch('sys.stderr') as stderr:
            code = keytool.main(argv, root=self.root, store=self.store, console=console)
        return code, ''.join(call.args[0] for call in stderr.write.call_args_list)

    def current_code(self):
        seed = self.store.read_secret('totp.seed.dpapi').decode()
        return totp.totp(totp.seed_bytes(seed), self.now[0])

    def enrol(self):
        def code():
            seed = totp.otpauth_uri  # noqa: F841 - the console saw the QR; derive the code from it
            secret = console.qrs[-1].split('secret=')[1].split('&')[0]
            return totp.totp(totp.seed_bytes(secret), self.now[0])
        console = Console(codes=[code])
        self.assertEqual(self.run_tool(['setup-totp'], console)[0], 0)
        return console

    def test_full_owner_flow(self):
        console = Console()
        self.assertEqual(self.run_tool(['new-keys'], console)[0], 0, console.lines)
        index = self.store.public_index()
        keys = keytool.trusted_keys(self.root)
        self.assertEqual(sorted(keys), sorted(index[name]['key_id'] for name in ('main', 'reserve')))
        entries, _ = keytool.verified_chain(self.root)
        self.assertEqual([entry['origin'] for entry in entries], ['imported', 'imported'])
        self.assertEqual(entries[0]['source_commit'], self.git('rev-list', '--max-parents=0', 'HEAD'))
        self.assertIn(keytool.kit_literals(self.root)[0], (self.root/'router-test-kit/02-install.sh').read_text())
        # Store holds only protected blobs; nothing secret in the repository.
        self.assertTrue(self.store.key_path('main').read_bytes().startswith(b'T'))
        for path in self.root.rglob('*'):
            if path.is_file() and '.git' not in path.parts:
                self.assertNotIn(b'BK', base64.b64decode(path.read_bytes().split(b'\n')[1]) if path.parent.name == 'keys' and path.name != 'revoked' else b'')
        # Second run refused.
        self.assertEqual(self.run_tool(['new-keys'], Console())[0], 2)
        # Reveal needs TOTP.
        code, error = self.run_tool(['reveal', '--key', 'reserve'], Console(codes=['123456']))
        self.assertIn('TOTP-NOT-ENROLLED', error)
        self.enrol()
        self.now[0] += 60
        console = Console(codes=[self.current_code()])
        self.assertEqual(self.run_tool(['reveal', '--key', 'reserve', '--qr', 'none'], console)[0], 0)
        payload = console.qrs[-1]
        name, key = keytool.parse_payload(payload)
        self.assertEqual(key.key_id.hex(), index['reserve']['key_id'])
        # Wrong code refused, replay refused.
        self.assertIn('TOTP-WRONG-CODE', self.run_tool(['reveal', '--key', 'main'], Console(codes=['000000' if self.current_code() != '000000' else '111111']))[1])
        self.assertIn('TOTP-REPLAYED', self.run_tool(['reveal', '--key', 'main'], Console(codes=[self.current_code()]))[1])
        # Import on a "new PC" restores the same key; a wrong name or foreign key is refused.
        self.store = fake_store(Path(self.directory.name)/'store2')
        self.assertIn('IMPORT-WRONG-KEY', self.run_tool(['import', '--key', 'main'], Console(secrets=[payload]))[1])
        self.assertIn('IMPORT-KEY-UNTRUSTED', self.run_tool(['import', '--key', 'main'], Console(secrets=[keytool.secret_payload('main', u.SecretKey.generate())]))[1])
        self.assertEqual(self.run_tool(['import', '--key', 'reserve'], Console(secrets=[payload]))[0], 0)
        self.assertEqual(u.SecretKey.from_file(self.store.read_secret('reserve.key.dpapi')).public, key.public)

    def test_sign_release_appends_signed_entry_and_stamps(self):
        self.run_tool(['new-keys'], Console())
        self.enrol()
        payload = b'package 3\n'
        name = 'homensai-auto-vpn_1.0.0-alpha3-1_all.ipk'
        (self.root/'releases'/name).write_bytes(payload)
        (self.root/'VERSION.json').write_text(json.dumps({'application': {'artifact': name, 'sha256': hashlib.sha256(payload).hexdigest()}}))
        source = self.git('rev-parse', 'HEAD')
        stamped = []

        def stamper(digest):
            stamped.append(digest)
            return b'proof', {'ok': ['https://calendar.example']}
        self.now[0] += 60
        args = keytool.parser().parse_args(['sign-release', '--artifact', 'releases/'+name, '--source-commit', source])
        keytool.cmd_sign_release(args, self.root, self.store, Console(codes=[self.current_code()]), stamper=stamper)
        report = keytool.verify_release(self.root, 'releases/'+name)
        self.assertEqual((report['entries'], report['head'], report['result']), (3, '1.0.0-alpha3-1', 'PASS'))
        entries, _ = keytool.verified_chain(self.root)
        self.assertEqual(entries[-1]['origin'], 'release')
        self.assertEqual(stamped, [hashlib.sha256(chain.canonical(entries[-1])).digest()])
        self.assertEqual((self.root/'releases/ots/1.0.0-alpha3-1.ots').read_bytes(), b'proof')
        # Same version twice, unknown commit, wrong VERSION.json hash: refused before any code is asked.
        self.assertIn('SIGN-ALREADY-IN-CHAIN', self.run_tool(['sign-release', '--artifact', 'releases/'+name, '--source-commit', source], Console())[1])
        self.assertIn('SIGN-SOURCE-COMMIT', self.run_tool(['sign-release', '--artifact', 'releases/'+name, '--source-commit', 'x'], Console())[1])
        # Tampered package after signing is caught by verify-release.
        (self.root/'releases'/name).write_bytes(b'evil\n')
        with self.assertRaisesRegex(ValueError, 'RELEASE-PACKAGE-MISMATCH'):
            keytool.verify_release(self.root)

    def test_calendar_failure_never_blocks_signing(self):
        self.run_tool(['new-keys'], Console())
        self.enrol()
        name = 'homensai-auto-vpn_1.0.0-alpha3-1_all.ipk'
        (self.root/'releases'/name).write_bytes(b'p\n')
        (self.root/'VERSION.json').write_text('{}')
        self.now[0] += 60
        console = Console(codes=[self.current_code()])
        args = keytool.parser().parse_args(['sign-release', '--artifact', 'releases/'+name, '--source-commit', self.git('rev-parse', 'HEAD')])
        keytool.cmd_sign_release(args, self.root, self.store, console, stamper=lambda digest: (None, {'failed': {'https://a': 'timeout'}}))
        self.assertTrue(any('OTS-PENDING-RETRY' in line for line in console.lines))
        self.assertTrue(Path(str(self.root/'releases'/name)+'.sig').exists())

    def test_reset_totp_needs_key_proof_and_emergency_rotation(self):
        self.run_tool(['new-keys'], Console())
        self.enrol()
        # Without --prove-key a code is the proof, so a wrong one changes nothing (qa/test_signing_recovery.py has the rest).
        seed = self.store.read_secret('totp.seed.dpapi')
        self.assertIn('TOTP-WRONG-CODE', self.run_tool(['reset-totp'], Console(codes=['000000' if self.current_code() != '000000' else '111111']))[1])
        self.assertEqual(self.store.read_secret('totp.seed.dpapi'), seed)
        self.assertIn('TOTP-EXISTS', self.run_tool(['setup-totp'], Console())[1])
        self.assertIn('IMPORT-CHECKSUM', self.run_tool(['reset-totp', '--prove-key', 'main'], Console(secrets=['HSAI-SK1:MAIN:'+'A'*16+':'+'A'*52+':AAAAAAAA']))[1])
        old = keytool.trusted_keys(self.root)
        # Everything lost: new keys without any old secret; old ids revoked from the next seq, kept for old history.
        console = Console()
        self.assertEqual(self.run_tool(['new-keys', '--emergency', '--skip-totp'], console)[0], 0, console.lines)
        revoked = keytool.revocations(self.root)
        self.assertEqual(revoked, {(key_id, 2) for key_id in old})
        self.assertEqual(len(keytool.trusted_keys(self.root)), 4)
        self.assertEqual(len(keytool.verified_chain(self.root)[0]), 2)
        self.assertTrue(list(self.store.root.glob('main.retired-*.key.dpapi')))
        self.assertFalse(self.store.has('totp.seed.dpapi'))
        self.assertIn("REVOKED_KEYS='", (self.root/'router-test-kit/02-install.sh').read_text())
        self.assertIn(':2', keytool.kit_literals(self.root)[1])

    def test_test_code_injection_needs_test_marker(self):
        with mock.patch.dict(os.environ, {keytool.TEST_ENV: ''}):
            with self.assertRaisesRegex(ValueError, 'TOTP-TEST-CODE-REFUSED'):
                keytool.Console('123456')
        with mock.patch.dict(os.environ, {keytool.TEST_ENV: '1'}):
            self.assertEqual(keytool.Console('123456').code(), '123456')


class RepositoryKeysTests(unittest.TestCase):
    def test_repository_chain_and_keys_verify(self):
        if not (ROOT/keytool.CHAIN).exists():
            self.skipTest('release chain not created yet')
        report = keytool.verify_release(ROOT)
        self.assertEqual(report['result'], 'PASS')
        self.assertEqual(len(report['trusted_keys']), 2)

    def test_no_secret_material_in_repository_key_folder(self):
        for path in (ROOT/keytool.KEYS_DIR).glob('*'):
            if path.name != 'revoked':
                self.assertEqual(len(base64.b64decode(path.read_bytes().split(b'\n')[1])), 42)


@unittest.skipUnless(sys.platform == 'win32', 'DPAPI exists only on Windows')
class DpapiTests(unittest.TestCase):
    def test_round_trip_and_wrong_entropy(self):
        blob = secret_store._dpapi(b'test only', True)
        self.assertNotIn(b'test only', blob)
        self.assertEqual(secret_store._dpapi(blob, False), b'test only')
        with mock.patch.object(secret_store, 'ENTROPY', b'other'):
            with self.assertRaises(secret_store.StoreError):
                secret_store._dpapi(blob, False)
