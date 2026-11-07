"""age v1 implementation (scripts/backupcrypt/age_format.py): known answers of the primitives, every C2SP/CCTV age
test vector (qa/vectors/age-cctv, commit b88c4b206254ac543df240097e0f1fcc6a664821, 0BSD/CC0) and round trips.
The vectors run with the pure-Python primitives; when `cryptography` is importable they run a second time with it."""
import hashlib
import importlib
import os
import sys
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT/'qa'/'vectors'/'age-cctv'
sys.path.insert(0, str(ROOT/'scripts'/'backupcrypt'))


def load(pure):
    previous = os.environ.get('HOMENSAI_AGE_PURE')
    os.environ['HOMENSAI_AGE_PURE'] = '1' if pure else '0'
    try:
        import age_format
        return importlib.reload(age_format)
    finally:
        if previous is None:
            os.environ.pop('HOMENSAI_AGE_PURE', None)
        else:
            os.environ['HOMENSAI_AGE_PURE'] = previous


age = load(True)


def parse_vector(raw):
    head, _, body = raw.partition(b'\n\n')
    fields = {}
    for line in head.split(b'\n'):
        key, _, value = line.decode('utf-8').partition(': ')
        fields.setdefault(key, []).append(value)
    if fields.get('compressed') == ['zlib']:
        body = zlib.decompress(body)
    return fields, body


UNSUPPORTED_IDENTITY = 'AGE-SECRET-KEY-PQ-1'  # mlkem768x25519 (post-quantum hybrid) is out of scope


def run_vector(module, name):
    fields, body = parse_vector((VECTORS/name).read_bytes())
    expect = fields['expect'][0]
    identities = []
    for text in fields.get('identity', []):
        if text.startswith(UNSUPPORTED_IDENTITY):
            continue
        identities.append(module.Identity.parse(text))
    identities += [module.ScryptIdentity(p) for p in fields.get('passphrase', [])]
    if not identities:
        if fields.get('identity'):
            return 'skipped', None  # only post-quantum identities
        identities = [module.Identity.generate()]  # e.g. `empty`: the file must fail before any identity is used
    released = hashlib.sha256()
    outcome = 'success'
    try:
        if fields.get('armored') == ['yes'] and not module.is_armored(body):
            raise module.ArmorError('ARMOR-EXPECTED')
        for chunk in module.decrypt_iter(body, identities):
            released.update(chunk)
    except module.AgeError as error:
        outcome = error.kind
    payload = fields.get('payload', [None])[0]
    return (outcome, expect), (payload is None or released.hexdigest() == payload)


class Primitives(unittest.TestCase):
    def test_x25519_rfc7748(self):
        # RFC 7748 section 5.2 and the section 6.1 Diffie-Hellman example
        k = bytes.fromhex('a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4')
        u = bytes.fromhex('e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c')
        self.assertEqual(age._x25519_pure(k, u).hex(), 'c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552')
        a = bytes.fromhex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a')
        b = bytes.fromhex('5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb')
        self.assertEqual(age.x25519_public(a).hex(), '8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a')
        self.assertEqual(age.x25519(a, age.x25519_public(b)).hex(),
                         '4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742')

    def test_x25519_iterated(self):
        k = u = age.BASEPOINT
        for _ in range(1000):
            k, u = age._x25519_pure(k, u), k
        self.assertEqual(k.hex(), '684cf59ba83309552800ef566f2f4d3c1c3887c49360e3875f2eb94d99532c51')

    def test_chacha20_rfc8439_block(self):
        key = bytes(range(32))
        nonce = bytes.fromhex('000000090000004a00000000')
        self.assertEqual(age.chacha20_keystream(key, 1, nonce, 1).hex(),
                         '10f1e7e4d13b5915500fdd1fa32071c4c7d1f4c733c068030422aa9ac3d46c4e'
                         'd2826446079faa0914c2d705d98b02a2b5129cd1de164eb9cbd083e8a2503c4e')

    def test_chacha20_lanes_match_single_blocks(self):
        key, nonce = os.urandom(32), os.urandom(12)
        many = age.chacha20_keystream(key, 7, nonce, 37)
        self.assertEqual(many, b''.join(age.chacha20_keystream(key, 7+i, nonce, 1) for i in range(37)))

    def test_aead_rfc8439(self):
        key = bytes.fromhex('808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f')
        nonce = bytes.fromhex('070000004041424344454647')
        aad = bytes.fromhex('50515253c0c1c2c3c4c5c6c7')
        plain = (b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, "
                 b"sunscreen would be it.")
        sealed = age.aead_encrypt(key, nonce, plain, aad)
        self.assertEqual(sealed[-16:].hex(), '1ae10b594f09e26a7e902ecbd0600691')
        self.assertEqual(sealed[:16].hex(), 'd31a8d34648e60db7b86afbc53ef7ec2')
        self.assertEqual(age.aead_decrypt(key, nonce, sealed, aad), plain)
        broken = bytearray(sealed)
        broken[3] ^= 1
        self.assertIsNone(age.aead_decrypt(key, nonce, bytes(broken), aad))

    def test_poly1305_rfc8439(self):
        key = bytes.fromhex('85d6be7857556d337f4452fe42d506a80103808afb0db2fd4abff6af4149f51b')
        self.assertEqual(age.poly1305(key, b'Cryptographic Forum Research Group').hex(), 'a8061dc1305136c6c22b8baf0c0127a9')

    def test_hkdf_rfc5869_case1(self):
        okm = age.hkdf(bytes.fromhex('0b'*22), bytes.fromhex('000102030405060708090a0b0c'),
                       bytes.fromhex('f0f1f2f3f4f5f6f7f8f9'), 42)
        self.assertEqual(okm.hex(), '3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865')

    def test_bech32_bip173(self):
        for valid in ('A12UEL5L', 'abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw', '?1ezyfcl'):
            age.bech32_decode(valid)
        for invalid in ('A1G7SGD8', 'a12UEL5L', 'x1b4n0q5v', 'li1dgmt3', '10a06t8'):
            with self.assertRaises(ValueError):
                age.bech32_decode(invalid)

    def test_identity_recipient_known_pair(self):
        # the pair of the age README / CCTV x25519 vector family
        identity = age.Identity.parse('AGE-SECRET-KEY-1EGTZVFFV20835NWYV6270LXYVK2VKNX2MMDKWYKLMGR48UAWX40Q2P2LM0')
        self.assertTrue(identity.recipient().encode().startswith('age1'))
        self.assertEqual(age.Recipient.parse(identity.recipient().encode()), identity.recipient())
        self.assertNotIn('AGE-SECRET', repr(identity))
        self.assertNotIn('AGE-SECRET', str(identity))

    def test_recipient_rejects_uppercase_and_identity(self):
        identity = age.Identity.generate()
        with self.assertRaises(age.AgeError):
            age.Recipient.parse(identity.recipient().encode().upper())
        with self.assertRaises(age.AgeError):
            age.Recipient.parse(identity.encode())
        with self.assertRaises(age.AgeError):
            age.Identity.parse(identity.recipient().encode())


class Vectors(unittest.TestCase):
    def check_all(self, module):
        names = sorted(p.name for p in VECTORS.iterdir())
        self.assertEqual(len(names), 147)
        checked, skipped, wrong = 0, [], []
        for name in names:
            result, payload_ok = run_vector(module, name)
            if result == 'skipped':
                skipped.append(name)
                continue
            checked += 1
            outcome, expect = result
            if outcome != expect or not payload_ok:
                wrong.append((name, outcome, expect, payload_ok))
        self.assertEqual(wrong, [])
        # only the post-quantum hybrid vectors without an X25519/scrypt identity are out of scope
        self.assertTrue(all(name.startswith(('hybrid', 'armor_hybrid')) for name in skipped), skipped)
        self.assertEqual(checked, 129)  # 147 vectors - 18 that carry only post-quantum identities
        return checked

    def test_vectors_pure_python(self):
        self.check_all(load(True))

    def test_vectors_cryptography_backend(self):
        module = load(False)
        if module.BACKEND is None:
            self.skipTest('cryptography is not installed here (docker CI installs it for this test)')
        self.check_all(module)


class RoundTrip(unittest.TestCase):
    def test_sizes_around_chunk_boundaries(self):
        identity = age.Identity.generate()
        other = age.Identity.generate()
        for size in (0, 1, 15, 16, 17, 65535, 65536, 65537, 2*65536, 2*65536+1):
            data = os.urandom(size)
            sealed = age.encrypt(data, [other.recipient(), identity.recipient()])
            self.assertEqual(age.decrypt(sealed, [identity]), data)
            self.assertEqual(age.decrypt(sealed, [other]), data)
            self.assertEqual(age.header_recipient_count(sealed), 2)
            self.assertEqual(age.decrypt(age.encrypt(data, [identity.recipient()], armored=True), [identity]), data)

    def test_wrong_identity_and_tampering(self):
        identity, stranger = age.Identity.generate(), age.Identity.generate()
        sealed = bytearray(age.encrypt(b'secret material' * 1000, [identity.recipient()]))
        with self.assertRaises(age.NoMatchError):
            age.decrypt(bytes(sealed), [stranger])
        sealed[-1] ^= 1
        with self.assertRaises(age.PayloadError):
            age.decrypt(bytes(sealed), [identity])

    def test_header_tampering_is_hmac_failure(self):
        identity = age.Identity.generate()
        sealed = age.encrypt(b'x', [identity.recipient()])
        tampered = sealed.replace(b'-> X25519 ', b'-> grease z\n\n-> X25519 ', 1)
        with self.assertRaises(age.HmacError):
            age.decrypt(tampered, [identity])

    def test_body_line_of_65_columns_is_refused_as_such(self):
        header = b'age-encryption.org/v1\n-> x\n' + b'A'*65 + b'\n\n--- ' + b'A'*43 + b'\n'
        with self.assertRaises(age.HeaderError) as caught:
            age.parse_header(header)
        self.assertIn('STANZA-LINE-LENGTH', str(caught.exception))
        stanzas = age.parse_header(b'age-encryption.org/v1\n-> x\n' + b'A'*64 + b'\n\n--- ' + b'A'*43 + b'\n')[0]
        self.assertEqual(len(stanzas[0].body), 48)

    def test_no_recipients_refused(self):
        with self.assertRaises(age.AgeError):
            age.encrypt(b'x', [])


if __name__ == '__main__':
    unittest.main()
