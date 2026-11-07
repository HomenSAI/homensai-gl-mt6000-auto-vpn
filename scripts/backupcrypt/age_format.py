"""age v1 file encryption (https://age-encryption.org/v1, C2SP age), pure Python 3.9+ standard library.

Used on the owner's PC to make the private backup bundles portable: an archive is encrypted to the owner's X25519
recipient (public, in the repository) and can be decrypted on any computer with the owner's identity
(AGE-SECRET-KEY-1..., kept in the password manager) by this module OR by the official `age`/`rage` tools.

Scope (exactly the spec; checked against all C2SP/CCTV age test vectors in qa/vectors/age-cctv and the real `age`
binary, qa/evidence/age-tofu-2026-11-04):
  * recipients/identities: X25519 (encrypt + decrypt), scrypt passphrase (decrypt only, work factor <= 22, the
    reference implementation's limit); the post-quantum mlkem768x25519 type is NOT implemented (its stanzas are
    ignored like any unknown stanza, so a file that also has an X25519 stanza still decrypts);
  * header: strict canonical parsing (LF only, canonical unpadded base64, 64-column bodies, VCHAR arguments),
    HMAC-SHA-256 over the header, constant-time comparison;
  * payload: STREAM with ChaCha20-Poly1305, 64 KiB chunks, last-chunk flag, the empty-last-chunk and trailing-data
    rules; plaintext is released chunk by chunk only after its tag verified;
  * ASCII armor (encode and strict decode).
Primitives (RFC 7748 X25519, RFC 8439 ChaCha20-Poly1305, RFC 5869 HKDF, BIP-173 Bech32) are implemented here and
known-answer tested (qa/test_backupcrypt_age.py). ChaCha20 runs all blocks of a chunk at once in big-integer lanes
(no per-block Python loop), which makes a 64 MB archive a matter of seconds. When the vetted `cryptography`
package is importable it is used for ChaCha20-Poly1305 and X25519 instead (same results; the tests run both);
HOMENSAI_AGE_PURE=1 forces the pure code.

Not constant time (Python big integers): fine for the owner's own PC encrypting to a public key and decrypting
interactively; not meant for a server answering attacker-chosen ciphertexts at volume.
"""
import base64
import binascii
import hashlib
import hmac
import os
import re
import struct

VERSION_LINE = b'age-encryption.org/v1'
CHUNK = 64 * 1024
TAG = 16
MAX_SCRYPT_LOG_N = 22
ARMOR_BEGIN = b'-----BEGIN AGE ENCRYPTED FILE-----'
ARMOR_END = b'-----END AGE ENCRYPTED FILE-----'


class AgeError(ValueError):
    kind = 'error'


class HeaderError(AgeError):
    kind = 'header failure'


class NoMatchError(AgeError):
    kind = 'no match'


class HmacError(AgeError):
    kind = 'HMAC failure'


class PayloadError(AgeError):
    kind = 'payload failure'


class ArmorError(AgeError):
    kind = 'armor failure'


# ---- optional vetted backend ----------------------------------------------------------------------------------

def _load_backend():
    if os.environ.get('HOMENSAI_AGE_PURE') == '1':
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
        from cryptography.exceptions import InvalidTag
    except Exception:
        return None
    return {'aead': ChaCha20Poly1305, 'priv': X25519PrivateKey, 'pub': X25519PublicKey, 'invalid': InvalidTag}


BACKEND = _load_backend()


def backend_name():
    return 'cryptography' if BACKEND else 'pure-python'


# ---- X25519 (RFC 7748) -----------------------------------------------------------------------------------------

_P = 2**255 - 19
_A24 = 121665


def _clamp(scalar):
    k = bytearray(scalar)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    return int.from_bytes(bytes(k), 'little')


def _x25519_pure(scalar, u_bytes):
    if len(scalar) != 32 or len(u_bytes) != 32:
        raise ValueError('X25519 inputs must be 32 bytes')
    k = _clamp(scalar)
    u = int.from_bytes(u_bytes, 'little') & ((1 << 255) - 1)
    x1, x2, z2, x3, z3, swap = u, 1, 0, u, 1, 0
    for t in range(254, -1, -1):
        bit = (k >> t) & 1
        swap ^= bit
        if swap:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = bit
        a, b = (x2 + z2) % _P, (x2 - z2) % _P
        aa, bb = a * a % _P, b * b % _P
        e = (aa - bb) % _P
        c, d = (x3 + z3) % _P, (x3 - z3) % _P
        da, cb = d * a % _P, c * b % _P
        x3 = (da + cb) % _P
        x3 = x3 * x3 % _P
        z3 = (da - cb) % _P
        z3 = x1 * (z3 * z3 % _P) % _P
        x2 = aa * bb % _P
        z2 = e * (aa + _A24 * e) % _P
    if swap:
        x2, z2 = x3, z3
    return (x2 * pow(z2, _P - 2, _P) % _P).to_bytes(32, 'little')


def x25519(scalar, u_bytes):
    if BACKEND:
        try:
            return BACKEND['priv'].from_private_bytes(scalar).exchange(BACKEND['pub'].from_public_bytes(u_bytes))
        except ValueError:
            return b'\0' * 32  # cryptography refuses the all-zero result; the caller rejects it the same way
    return _x25519_pure(scalar, u_bytes)


BASEPOINT = (9).to_bytes(32, 'little')


def x25519_public(scalar):
    return x25519(scalar, BASEPOINT)


# ---- ChaCha20 (RFC 8439), lane-parallel ------------------------------------------------------------------------

_LANE = 8  # bytes per lane while the rounds run: a 32-bit word plus room for the shifted-out bits
_masks = {}


def _lane_constants(lanes):
    """(mask of the low 32 bits of every lane, multiplier that copies a word into every lane)"""
    cached = _masks.get(lanes)
    if cached is None:
        if len(_masks) > 8:
            _masks.clear()
        cached = _masks[lanes] = (int.from_bytes(bytes([255, 255, 255, 255, 0, 0, 0, 0]) * lanes, 'little'),
                                  int.from_bytes(bytes([1, 0, 0, 0, 0, 0, 0, 0]) * lanes, 'little'))
    return cached


def chacha20_keystream(key, counter, nonce, blocks):
    """`blocks` consecutive 64-byte ChaCha20 blocks starting at `counter` (32-bit counter, 96-bit nonce).
    Every state word is one big integer holding that word of all blocks (8-byte lanes), so one Python operation
    advances all blocks; the words are interleaved back into 64-byte blocks at the end."""
    if len(key) != 32 or len(nonce) != 12 or blocks < 1 or counter + blocks > 2**32:
        raise ValueError('ChaCha20 parameters')
    lanes = blocks
    mask, ones = _lane_constants(lanes)
    words = struct.unpack('<4I', b'expand 32-byte k') + struct.unpack('<8I', key) + (0,) + struct.unpack('<3I', nonce)
    state = [w * ones for w in words]
    state[12] = int.from_bytes(b''.join(struct.pack('<II', counter + j, 0) for j in range(lanes)), 'little')
    x = list(state)

    def quarter(a, b, c, d):
        xa, xb, xc, xd = x[a], x[b], x[c], x[d]
        xa = (xa + xb) & mask
        xd ^= xa
        xd = ((xd << 16) | (xd >> 16)) & mask
        xc = (xc + xd) & mask
        xb ^= xc
        xb = ((xb << 12) | (xb >> 20)) & mask
        xa = (xa + xb) & mask
        xd ^= xa
        xd = ((xd << 8) | (xd >> 24)) & mask
        xc = (xc + xd) & mask
        xb ^= xc
        xb = ((xb << 7) | (xb >> 25)) & mask
        x[a], x[b], x[c], x[d] = xa, xb, xc, xd

    for _ in range(10):
        quarter(0, 4, 8, 12)
        quarter(1, 5, 9, 13)
        quarter(2, 6, 10, 14)
        quarter(3, 7, 11, 15)
        quarter(0, 5, 10, 15)
        quarter(1, 6, 11, 12)
        quarter(2, 7, 8, 13)
        quarter(3, 4, 9, 14)
    out = bytearray(64 * lanes)
    for i in range(16):
        word = ((x[i] + state[i]) & mask).to_bytes(_LANE * lanes, 'little')
        for byte in range(4):
            out[4 * i + byte::64] = word[byte::_LANE]
    return bytes(out)


def chacha20_xor(key, counter, nonce, data):
    if not data:
        return b''
    stream = chacha20_keystream(key, counter, nonce, (len(data) + 63) // 64)
    return (int.from_bytes(data, 'little') ^ int.from_bytes(stream[:len(data)], 'little')).to_bytes(len(data), 'little')


# ---- Poly1305 and the AEAD ------------------------------------------------------------------------------------

_P1305 = (1 << 130) - 5


def poly1305(key, message):
    r = int.from_bytes(key[:16], 'little') & 0x0ffffffc0ffffffc0ffffffc0fffffff
    s = int.from_bytes(key[16:32], 'little')
    acc = 0
    full = len(message) - len(message) % 16
    view = memoryview(message)
    high = 1 << 128
    for offset in range(0, full, 16):
        acc = (acc + int.from_bytes(view[offset:offset + 16], 'little') + high) * r % _P1305
    if full != len(message):
        tail = bytes(view[full:])
        acc = (acc + int.from_bytes(tail + b'\x01', 'little')) * r % _P1305
    return ((acc + s) & ((1 << 128) - 1)).to_bytes(16, 'little')


def _pad16(n):
    return b'\0' * (-n % 16)


def _aead_tag(key, nonce, aad, ciphertext):
    otk = chacha20_keystream(key, 0, nonce, 1)[:32]
    mac_data = aad + _pad16(len(aad)) + ciphertext + _pad16(len(ciphertext)) + struct.pack('<QQ', len(aad), len(ciphertext))
    return poly1305(otk, mac_data)


def aead_encrypt(key, nonce, plaintext, aad=b''):
    if BACKEND:
        return BACKEND['aead'](key).encrypt(nonce, plaintext, aad or None)
    ciphertext = chacha20_xor(key, 1, nonce, plaintext)
    return ciphertext + _aead_tag(key, nonce, aad, ciphertext)


def aead_decrypt(key, nonce, data, aad=b''):
    """Plaintext or None when the tag does not verify (nothing is released)."""
    if len(data) < TAG:
        return None
    if BACKEND:
        try:
            return BACKEND['aead'](key).decrypt(nonce, bytes(data), aad or None)
        except BACKEND['invalid']:
            return None
    ciphertext, tag = bytes(data[:-TAG]), bytes(data[-TAG:])
    if not hmac.compare_digest(_aead_tag(key, nonce, aad, ciphertext), tag):
        return None
    return chacha20_xor(key, 1, nonce, ciphertext)


# ---- HKDF-SHA-256 (RFC 5869) ------------------------------------------------------------------------------------

def hkdf(ikm, salt, info, length=32):
    prk = hmac.new(salt if salt else b'\0' * 32, ikm, hashlib.sha256).digest()
    out, block, counter = b'', b'', 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


# ---- Bech32 (BIP-173, no 90-character limit as in age) ----------------------------------------------------------

_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
_GEN = (0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)


def _polymod(values):
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= _GEN[i] if (top >> i) & 1 else 0
    return chk


def _expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convert(data, frombits, tobits, pad):
    acc, bits, out, maxv = 0, 0, [], (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            out.append((acc >> bits) & maxv)
    if pad:
        if bits:
            out.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise ValueError('BECH32-PADDING')
    return out


def bech32_encode(hrp, data):
    words = _convert(data, 8, 5, True)
    checksum = _polymod(_expand(hrp) + words + [0] * 6) ^ 1
    words += [(checksum >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + '1' + ''.join(_CHARSET[w] for w in words)


def bech32_decode(text):
    if text.lower() != text and text.upper() != text:
        raise ValueError('BECH32-MIXED-CASE')
    text = text.lower()
    pos = text.rfind('1')
    if pos < 1 or pos + 7 > len(text) or any(ord(c) < 33 or ord(c) > 126 for c in text):
        raise ValueError('BECH32-FORMAT')
    hrp, words = text[:pos], []
    for c in text[pos + 1:]:
        index = _CHARSET.find(c)
        if index < 0:
            raise ValueError('BECH32-CHARACTER')
        words.append(index)
    if _polymod(_expand(hrp) + words) != 1:
        raise ValueError('BECH32-CHECKSUM')
    return hrp, bytes(_convert(words[:-6], 5, 8, False))


# ---- keys ---------------------------------------------------------------------------------------------------

class Identity:
    """An X25519 identity (the owner's secret). `str()` deliberately does not reveal it; use .encode()."""
    def __init__(self, secret):
        if len(secret) != 32:
            raise ValueError('IDENTITY-LENGTH')
        self._secret = bytes(secret)
        self.public = x25519_public(self._secret)

    @classmethod
    def generate(cls):
        return cls(os.urandom(32))

    @classmethod
    def parse(cls, text):
        try:
            hrp, data = bech32_decode(text.strip())
        except ValueError as error:
            raise AgeError('IDENTITY-FORMAT: %s' % error) from None
        if hrp != 'age-secret-key-' or len(data) != 32:
            raise AgeError('IDENTITY-FORMAT: not an age X25519 identity')
        return cls(data)

    def encode(self):
        return bech32_encode('age-secret-key-', self._secret).upper()

    def recipient(self):
        return Recipient(self.public)

    def __repr__(self):
        return '<age Identity for %s>' % self.recipient().encode()

    __str__ = __repr__

    def unwrap(self, stanza):
        """File key, or None when the stanza is not for this identity. Raises HeaderError for a malformed stanza."""
        if stanza.type != 'X25519':
            return None
        if len(stanza.args) != 1:
            raise HeaderError('X25519-ARGUMENTS')
        share = b64decode(stanza.args[0].encode('ascii'))
        if len(share) != 32:
            raise HeaderError('X25519-SHARE-LENGTH')
        if len(stanza.body) != 32:
            raise HeaderError('X25519-BODY-LENGTH')
        shared = x25519(self._secret, share)
        if shared == b'\0' * 32:
            raise HeaderError('X25519-LOW-ORDER')
        key = hkdf(shared, share + self.public, b'age-encryption.org/v1/X25519')
        return aead_decrypt(key, b'\0' * 12, stanza.body)


class Recipient:
    def __init__(self, public):
        if len(public) != 32:
            raise ValueError('RECIPIENT-LENGTH')
        self.public = bytes(public)

    @classmethod
    def parse(cls, text):
        try:
            hrp, data = bech32_decode(text.strip())
        except ValueError as error:
            raise AgeError('RECIPIENT-FORMAT: %s' % error) from None
        if hrp != 'age' or len(data) != 32 or text.strip() != text.strip().lower():
            raise AgeError('RECIPIENT-FORMAT: not an age1... X25519 recipient')
        return cls(data)

    def encode(self):
        return bech32_encode('age', self.public)

    def __eq__(self, other):
        return isinstance(other, Recipient) and other.public == self.public

    def __hash__(self):
        return hash(self.public)

    def wrap(self, file_key):
        ephemeral = os.urandom(32)
        share = x25519_public(ephemeral)
        shared = x25519(ephemeral, self.public)
        if shared == b'\0' * 32:
            raise AgeError('RECIPIENT-LOW-ORDER')
        key = hkdf(shared, share + self.public, b'age-encryption.org/v1/X25519')
        return Stanza('X25519', [b64encode(share).decode('ascii')], aead_encrypt(key, b'\0' * 12, file_key))


class ScryptIdentity:
    """Passphrase identity (decryption only here; the backup tool never encrypts with a passphrase)."""
    def __init__(self, passphrase, max_log_n=MAX_SCRYPT_LOG_N):
        self.passphrase = passphrase.encode('utf-8') if isinstance(passphrase, str) else bytes(passphrase)
        self.max_log_n = max_log_n

    def unwrap(self, stanza):
        if stanza.type != 'scrypt':
            return None
        if len(stanza.args) != 2:
            raise HeaderError('SCRYPT-ARGUMENTS')
        salt = b64decode(stanza.args[0].encode('ascii'))
        if len(salt) != 16:
            raise HeaderError('SCRYPT-SALT-LENGTH')
        if not re.fullmatch(r'[1-9][0-9]*', stanza.args[1]) or len(stanza.args[1]) > 2:
            raise HeaderError('SCRYPT-WORK-FACTOR-FORMAT')
        log_n = int(stanza.args[1])
        if log_n > self.max_log_n:
            raise HeaderError('SCRYPT-WORK-FACTOR-TOO-HIGH')
        if len(stanza.body) != 32:
            raise HeaderError('SCRYPT-BODY-LENGTH')
        key = hashlib.scrypt(self.passphrase, salt=b'age-encryption.org/v1/scrypt' + salt, n=1 << log_n, r=8, p=1,
                             maxmem=(128 * 8 * (1 << log_n)) + (1 << 24), dklen=32)
        return aead_decrypt(key, b'\0' * 12, stanza.body)


# ---- base64 as age uses it -------------------------------------------------------------------------------------

_B64 = re.compile(rb'[A-Za-z0-9+/]*')


def b64encode(data):
    return base64.b64encode(data).rstrip(b'=')


def b64decode(text):
    """Canonical unpadded standard base64 only (the spec: decoders MUST reject non-canonical encodings)."""
    if not _B64.fullmatch(text) or len(text) % 4 == 1:
        raise HeaderError('BASE64-FORMAT')
    try:
        data = base64.b64decode(text + b'=' * (-len(text) % 4), validate=True)
    except binascii.Error:
        raise HeaderError('BASE64-FORMAT') from None
    if b64encode(data) != text:
        raise HeaderError('BASE64-NOT-CANONICAL')
    return data


# ---- header -------------------------------------------------------------------------------------------------------

class Stanza:
    def __init__(self, type_, args, body):
        self.type, self.args, self.body = type_, list(args), bytes(body)

    def encode(self):
        out = b'-> ' + ' '.join([self.type] + self.args).encode('ascii') + b'\n'
        encoded = b64encode(self.body)
        for i in range(0, len(encoded), 64):
            out += encoded[i:i + 64] + b'\n'
        if len(encoded) % 64 == 0:
            out += b'\n'
        return out


def _header_mac(file_key, header_without_mac):
    return hmac.new(hkdf(file_key, b'', b'header'), header_without_mac, hashlib.sha256).digest()


def _arg_ok(arg):
    return arg != '' and all(0x21 <= ord(c) <= 0x7e for c in arg)


def parse_header(data):
    """-> (stanzas, header bytes up to and including '---', mac, offset of the payload). HeaderError on any defect."""
    pos = 0

    def line():
        nonlocal pos
        end = data.find(b'\n', pos)
        if end < 0:
            raise HeaderError('HEADER-TRUNCATED')
        text = data[pos:end]
        start, pos = pos, end + 1
        return text, start

    first, _ = line()
    if first != VERSION_LINE:
        if first.startswith(b'age-encryption.org/'):
            raise HeaderError('VERSION-UNSUPPORTED')
        raise HeaderError('NOT-AN-AGE-FILE')
    stanzas = []
    while True:
        text, start = line()
        if text.startswith(b'--- ') or text == b'---':
            if not text.startswith(b'--- '):
                raise HeaderError('MAC-MISSING')
            mac = b64decode(text[4:])
            if len(mac) != 32:
                raise HeaderError('MAC-LENGTH')
            return stanzas, data[:start + 3], mac, pos
        if not text.startswith(b'-> '):
            raise HeaderError('STANZA-START')
        try:
            parts = text[3:].decode('ascii').split(' ')
        except UnicodeDecodeError:
            raise HeaderError('STANZA-CHARACTER') from None
        if not parts or not all(_arg_ok(p) for p in parts):
            raise HeaderError('STANZA-ARGUMENTS')
        body = b''
        while True:
            chunk, _ = line()
            if len(chunk) > 64:
                raise HeaderError('STANZA-LINE-LENGTH')
            body += chunk
            if len(chunk) < 64:
                break
        stanzas.append(Stanza(parts[0], parts[1:], b64decode(body)))


def encode_header(file_key, stanzas):
    head = VERSION_LINE + b'\n' + b''.join(s.encode() for s in stanzas) + b'---'
    return head + b' ' + b64encode(_header_mac(file_key, head)) + b'\n'


def unwrap_file_key(stanzas, identities):
    if any(s.type == 'scrypt' for s in stanzas) and len(stanzas) != 1:
        raise HeaderError('SCRYPT-NOT-ALONE')
    for stanza in stanzas:
        for identity in identities:
            file_key = identity.unwrap(stanza)
            if file_key is not None:
                if len(file_key) != 16:
                    raise HeaderError('FILE-KEY-LENGTH')
                return file_key
    raise NoMatchError('NO-IDENTITY-MATCHED')


# ---- payload (STREAM) -------------------------------------------------------------------------------------------

def _stream_nonce(counter, last):
    if counter >= 1 << 88:
        raise PayloadError('STREAM-COUNTER-OVERFLOW')
    return counter.to_bytes(11, 'big') + (b'\x01' if last else b'\x00')


def encrypt_chunks(file_key, plaintext_chunks):
    """Header-less payload generator: nonce, then sealed chunks. `plaintext_chunks` yields bytes of any size."""
    nonce = os.urandom(16)
    key = hkdf(file_key, nonce, b'payload')
    yield nonce
    pending, counter = b'', 0
    for piece in plaintext_chunks:
        pending += piece
        while len(pending) > CHUNK:
            yield aead_encrypt(key, _stream_nonce(counter, False), pending[:CHUNK])
            pending, counter = pending[CHUNK:], counter + 1
    yield aead_encrypt(key, _stream_nonce(counter, True), pending)


def decrypt_payload(file_key, payload):
    """Generator of verified plaintext chunks; raises PayloadError at the first defect (earlier chunks were valid).
    The reference reader's rules: a short chunk is the last one (empty only when it is the only one); a full-size
    chunk is opened as a middle chunk, else as a full-size last chunk; data after the last chunk, or no last chunk
    before the end, is an error (the chunks already authenticated were released, as the reference does)."""
    if len(payload) < 16:
        raise HeaderError('STREAM-NONCE-MISSING')  # the nonce belongs to the header in the reference reader
    key = hkdf(file_key, bytes(payload[:16]), b'payload')
    view, pos, counter = memoryview(payload), 16, 0
    while True:
        remaining = len(view) - pos
        if remaining < TAG:
            raise PayloadError('STREAM-TRUNCATED')
        if remaining < CHUNK + TAG:
            if remaining == TAG and counter > 0:
                raise PayloadError('STREAM-LAST-CHUNK-EMPTY')
            plain = aead_decrypt(key, _stream_nonce(counter, True), view[pos:])
            if plain is None:
                raise PayloadError('STREAM-TAG')
            yield plain
            return
        sealed = view[pos:pos + CHUNK + TAG]
        last = False
        plain = aead_decrypt(key, _stream_nonce(counter, False), sealed)
        if plain is None:
            last = True
            plain = aead_decrypt(key, _stream_nonce(counter, True), sealed)
            if plain is None:
                raise PayloadError('STREAM-TAG')
        yield plain
        pos += CHUNK + TAG
        counter += 1
        if last:
            if pos != len(view):
                raise PayloadError('STREAM-TRAILING-DATA')
            return


# ---- armor ---------------------------------------------------------------------------------------------------

def armor(data):
    encoded = base64.b64encode(data)
    lines = [encoded[i:i + 64] for i in range(0, len(encoded), 64)]
    return ARMOR_BEGIN + b'\n' + b''.join(l + b'\n' for l in lines) + ARMOR_END + b'\n'


def is_armored(data):
    return data.lstrip(b' \t\r\n').startswith(ARMOR_BEGIN)


def dearmor(data):
    """Strict decoding as the reference implementation: whitespace around the block and CRLF line ends are
    tolerated; inside, every line but the last has exactly 64 columns, canonical padded base64, nothing else."""
    text = data.strip(b' \t\r\n')
    lines = text.split(b'\n')
    lines = [l[:-1] if l.endswith(b'\r') else l for l in lines]
    if len(lines) < 2 or lines[0] != ARMOR_BEGIN or lines[-1] != ARMOR_END:
        raise ArmorError('ARMOR-FRAME')
    body = lines[1:-1]
    for index, l in enumerate(body):
        last = index == len(body) - 1
        if (not last and len(l) != 64) or (last and not 0 < len(l) <= 64):
            raise ArmorError('ARMOR-LINE-LENGTH')
    joined = b''.join(body)
    if len(joined) % 4:
        raise ArmorError('ARMOR-PADDING')
    try:
        decoded = base64.b64decode(joined, validate=True)
    except binascii.Error:
        raise ArmorError('ARMOR-BASE64') from None
    if base64.b64encode(decoded) != joined:
        raise ArmorError('ARMOR-NOT-CANONICAL')
    return decoded


# ---- whole files ------------------------------------------------------------------------------------------------

def encrypt(plaintext, recipients, armored=False):
    if not recipients:
        raise AgeError('NO-RECIPIENTS')
    file_key = os.urandom(16)
    header = encode_header(file_key, [r.wrap(file_key) for r in recipients])
    out = header + b''.join(encrypt_chunks(file_key, [plaintext]))
    return armor(out) if armored else out


def decrypt_iter(data, identities):
    """Yields verified plaintext chunks; raises HeaderError / NoMatchError / HmacError / PayloadError / ArmorError."""
    if is_armored(data):
        data = dearmor(data)
    stanzas, head, mac, offset = parse_header(data)
    file_key = unwrap_file_key(stanzas, identities)
    if not hmac.compare_digest(_header_mac(file_key, head), mac):
        raise HmacError('HEADER-MAC')
    yield from decrypt_payload(file_key, memoryview(data)[offset:])


def decrypt(data, identities):
    return b''.join(decrypt_iter(data, identities))


def header_recipient_count(data):
    """Number of X25519 stanzas (public information; no secret needed)."""
    if is_armored(data):
        data = dearmor(data)
    stanzas = parse_header(data)[0]
    return sum(1 for s in stanzas if s.type == 'X25519')
