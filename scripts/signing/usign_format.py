"""Ed25519 (RFC 8032) and the OpenWrt usign/signify file formats, pure Python 3.9+ standard library.

A signature written here verifies with the router's stock `usign -V`, and a usign signature verifies here (cross-checked
against the real usign of the pinned OpenWrt 21.02.7 SDK, docs/architecture/SIGNING-2026-11-03.ru.md). Not constant
time: it runs only on the owner's PC for a handful of release files, never on a network-facing path.

usign layouts (big-endian, base64 in a two-line text file: "untrusted comment: ..." then the base64 line):
  public key  42 bytes  'Ed' + key id (8) + public key (32)
  secret key 104 bytes  'Ed' + 'BK' + kdf rounds (4, 0 = unencrypted) + salt (16) + checksum (8, SHA-512(seckey)[:8])
                        + key id (8) + seckey (64 = seed 32 + public key 32)
  signature   74 bytes  'Ed' + key id (8) + Ed25519 signature (64)
The key id ("fingerprint" in usign) is 8 random bytes chosen at generation; it names the key, it does not prove it.
The full fingerprint used for manual comparison is SHA-256 of the public key's base64 line (full_fingerprint()).
"""
import base64
import hashlib
import hmac
import os
import re
import struct

P = 2**255-19
L = 2**252+27742317777372353535851937790883648493
D = -121665*pow(121666, P-2, P) % P
SQRT_M1 = pow(2, (P-1)//4, P)


def _inv(x):
    return pow(x, P-2, P)


def _add(a, b):
    # Extended twisted Edwards coordinates (X, Y, Z, T), RFC 8032 section 5.1.4.
    A = (a[1]-a[0])*(b[1]-b[0]) % P
    B = (a[1]+a[0])*(b[1]+b[0]) % P
    C = 2*a[3]*b[3]*D % P
    E = 2*a[2]*b[2] % P
    e, f, g, h = B-A, E-C, E+C, B+A
    return (e*f % P, g*h % P, f*g % P, e*h % P)


def _mul(scalar, point):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(a, b):
    return (a[0]*b[2]-b[0]*a[2]) % P == 0 and (a[1]*b[2]-b[1]*a[2]) % P == 0


def _recover_x(y, sign):
    if y >= P:
        return None
    x2 = (y*y-1)*_inv(D*y*y+1) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P+3)//8, P)
    if (x*x-x2) % P:
        x = x*SQRT_M1 % P
    if (x*x-x2) % P:
        return None
    return P-x if (x & 1) != sign else x


_GY = 4*_inv(5) % P
_GX = _recover_x(_GY, 0)
BASE = (_GX, _GY, 1, _GX*_GY % P)
_BASE_POWERS = []


def _mul_base(scalar):
    # Fixed-base multiplication with the 2^i*B table: one addition per set bit, no doublings (verifying a long
    # release chain stays fast).
    if not _BASE_POWERS:
        point = BASE
        for _ in range(256):
            _BASE_POWERS.append(point)
            point = _add(point, point)
    result, index = (0, 1, 1, 0), 0
    while scalar > 0:
        if scalar & 1:
            result = _add(result, _BASE_POWERS[index])
        scalar >>= 1
        index += 1
    return result


def _compress(point):
    zinv = _inv(point[2])
    x, y = point[0]*zinv % P, point[1]*zinv % P
    return (y | ((x & 1) << 255)).to_bytes(32, 'little')


def _decompress(data):
    if len(data) != 32:
        return None
    y = int.from_bytes(data, 'little')
    sign = y >> 255
    y &= (1 << 255)-1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x*y % P)


def _hash_int(*parts):
    return int.from_bytes(hashlib.sha512(b''.join(parts)).digest(), 'little') % L


def _expand(seed):
    if len(seed) != 32:
        raise ValueError('ED25519-SEED-LENGTH')
    digest = hashlib.sha512(seed).digest()
    scalar = int.from_bytes(digest[:32], 'little')
    scalar &= (1 << 254)-8
    scalar |= 1 << 254
    return scalar, digest[32:]


def public_key(seed):
    return _compress(_mul_base(_expand(seed)[0]))


def sign(seed, message):
    scalar, prefix = _expand(seed)
    public = _compress(_mul_base(scalar))
    r = _hash_int(prefix, message)
    point = _compress(_mul_base(r))
    s = (r+_hash_int(point, public, message)*scalar) % L
    return point+s.to_bytes(32, 'little')


def verify(public, message, signature):
    if len(public) != 32 or len(signature) != 64:
        return False
    a = _decompress(public)
    r = _decompress(signature[:32])
    s = int.from_bytes(signature[32:], 'little')
    if a is None or r is None or s >= L:
        return False
    h = _hash_int(signature[:32], public, message)
    return _equal(_mul_base(s), _add(r, _mul(h, a)))


# ---- usign files ------------------------------------------------------------------------------------------------

def key_id_hex(key_id):
    return key_id.hex()


def _text(comment, payload):
    if '\n' in comment or '\r' in comment:
        raise ValueError('USIGN-COMMENT')
    return ('untrusted comment: %s\n%s\n' % (comment, base64.b64encode(payload).decode())).encode()


def _payload(data, size, kind):
    """Second line of a usign file, base64-decoded; exactly `size` bytes (as usign's own b64_decode check)."""
    try:
        text = data.decode('ascii')
    except (UnicodeDecodeError, AttributeError):
        raise ValueError('USIGN-%s-ENCODING' % kind) from None
    lines = text.replace('\r\n', '\n').split('\n')
    if len(lines) < 2 or not lines[0].startswith('untrusted comment: ') or not re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', lines[1]):
        raise ValueError('USIGN-%s-FORMAT' % kind)
    try:
        raw = base64.b64decode(lines[1], validate=True)
    except ValueError:
        raise ValueError('USIGN-%s-FORMAT' % kind) from None
    if len(raw) != size or raw[:2] != b'Ed':
        raise ValueError('USIGN-%s-FORMAT' % kind)
    return raw


def clamp_seed(seed):
    """usign generate() runs ed25519_prepare() on its random seed; mirror it so our keys are indistinguishable."""
    seed = bytearray(seed)
    seed[0] &= 0xf8
    seed[31] &= 0x7f
    seed[31] |= 0x40
    return bytes(seed)


class SecretKey:
    def __init__(self, seed, key_id, salt=bytes(16)):
        if len(seed) != 32 or len(key_id) != 8 or len(salt) != 16:
            raise ValueError('USIGN-SECRET-FIELDS')
        self.seed, self.key_id, self.salt = bytes(seed), bytes(key_id), bytes(salt)
        self.public = public_key(self.seed)

    @classmethod
    def generate(cls, random=os.urandom):
        # Same order of random reads as usign generate(): key id, seed, salt.
        key_id = random(8)
        seed = clamp_seed(random(32))
        return cls(seed, key_id, random(16))

    def to_bytes(self):
        seckey = self.seed+self.public
        checksum = hashlib.sha512(seckey).digest()[:8]
        return b'Ed'+b'BK'+struct.pack('>I', 0)+self.salt+checksum+self.key_id+seckey

    def to_file(self, comment):
        return _text(comment, self.to_bytes())

    @classmethod
    def from_file(cls, data):
        raw = _payload(data, 104, 'SECRET')
        if raw[2:4] != b'BK':
            raise ValueError('USIGN-SECRET-FORMAT')
        if struct.unpack('>I', raw[4:8])[0] != 0:
            raise ValueError('USIGN-SECRET-PASSWORD-PROTECTED')
        salt, checksum, key_id, seckey = raw[8:24], raw[24:32], raw[32:40], raw[40:104]
        if not hmac.compare_digest(hashlib.sha512(seckey).digest()[:8], checksum):
            raise ValueError('USIGN-SECRET-CHECKSUM')
        key = cls(seckey[:32], key_id, salt)
        if not hmac.compare_digest(key.public, seckey[32:]):
            raise ValueError('USIGN-SECRET-PUBLIC-MISMATCH')
        return key

    def public_file(self, comment):
        return PublicKey(self.public, self.key_id).to_file(comment)

    def sign_file(self, message):
        """usign -S output: comment 'signed by key <id>' then 'Ed' + key id + signature."""
        payload = b'Ed'+self.key_id+sign(self.seed, message)
        return _text('signed by key %s' % key_id_hex(self.key_id), payload)


class PublicKey:
    def __init__(self, public, key_id):
        if len(public) != 32 or len(key_id) != 8:
            raise ValueError('USIGN-PUBLIC-FIELDS')
        self.public, self.key_id = bytes(public), bytes(key_id)

    def to_bytes(self):
        return b'Ed'+self.key_id+self.public

    def to_file(self, comment):
        return _text(comment, self.to_bytes())

    @classmethod
    def from_file(cls, data):
        raw = _payload(data, 42, 'PUBLIC')
        return cls(raw[10:], raw[2:10])

    def full_fingerprint(self):
        """SHA-256 of the base64 line (binds key id and key); the router computes it with sed + sha256sum."""
        return hashlib.sha256(base64.b64encode(self.to_bytes())).hexdigest()


def signature_key_id(data):
    return _payload(data, 74, 'SIGNATURE')[2:10]


def verify_file(public_keys, message, signature_data, revoked=()):
    """Verify like `usign -V -P <dir>`: choose the trusted key by the signature's key id. Returns the key id hex.

    public_keys: {key id hex: PublicKey}. Raises ValueError with a stable code on any failure."""
    raw = _payload(signature_data, 74, 'SIGNATURE')
    key_id = key_id_hex(raw[2:10])
    if key_id in set(revoked):
        raise ValueError('SIGNATURE-KEY-REVOKED')
    key = public_keys.get(key_id)
    if key is None:
        raise ValueError('SIGNATURE-KEY-UNTRUSTED')
    if not verify(key.public, message, raw[10:]):
        raise ValueError('SIGNATURE-INVALID')
    return key_id
