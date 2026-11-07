"""Minimal OpenTimestamps (OTS) client, pure Python 3.9+ standard library.

Purpose: anchor a 32-byte hash (the hash of a releases/CHAIN.jsonl entry) in the Bitcoin blockchain through public
OpenTimestamps calendars, and check such a proof later. Only the 32-byte SHA-256 digest ever leaves the PC: stamp()
sends sha256(digest || 16 random bytes) to the calendars, upgrade() sends that commitment back, verify() sends only a
block height to two block explorers.

The binary format is byte-compatible with python-opentimestamps / opentimestamps-client: a parsed proof is serialized
back identically (same sorted fork order). Layout (all integers are LEB128 "varuint", "varbytes" = varuint length + bytes):
  header   b'\\x00OpenTimestamps\\x00\\x00Proof\\x00\\xbf\\x89\\xe2\\xe8\\x84\\xe8\\x92\\x94' + varuint(1)
  file     hash-op tag (0x08 = SHA-256) + digest
  tree     node := {0xff fork-marker + item}* item      item := 0x00 attestation | op node
  op       0x08 sha256, 0x03 ripemd160, 0x02 sha1, 0x67 keccak256, 0xf0 append(varbytes), 0xf1 prepend(varbytes)
  attest.  8-byte tag + varbytes(payload): 83dfe30d2ef90c8e pending(varbytes uri), 0588960d73d71901 bitcoin(varuint height)

Trust model of verify() (no full node needed, therefore weaker than `ots verify` against Bitcoin Core): the proof tree
is checked locally (every hash/append/prepend step is recomputed from the file digest up to the attested message). The
final step "the Bitcoin block at height N has this merkle root and this time" is taken from two independent public
Esplora explorers (blockstream.info and mempool.space) over TLS; both must return the same merkle root and timestamp,
otherwise the result is 'unverified'. Proof-of-work and chain selection are NOT checked locally. A forged result needs
both explorers (or the TLS trust store of this PC) to lie. The calendars are not trusted at all: a wrong calendar reply
can only make a proof fail to verify, never verify falsely.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import struct
import sys
import urllib.error
import urllib.request

MAGIC = b'\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94'
MAJOR_VERSION = 1
TAG_ATTESTATION = 0x00
TAG_FORK = 0xff
OP_SHA1, OP_RIPEMD160, OP_SHA256, OP_KECCAK256 = 0x02, 0x03, 0x08, 0x67
OP_APPEND, OP_PREPEND = 0xf0, 0xf1
HASH_OPS = {OP_SHA1: 'sha1', OP_RIPEMD160: 'ripemd160', OP_SHA256: 'sha256', OP_KECCAK256: 'keccak256'}
BINARY_OPS = {OP_APPEND: 'append', OP_PREPEND: 'prepend'}
DIGEST_LEN = {OP_SHA1: 20, OP_RIPEMD160: 20, OP_SHA256: 32, OP_KECCAK256: 32}
TAG_PENDING = bytes.fromhex('83dfe30d2ef90c8e')
TAG_BITCOIN = bytes.fromhex('0588960d73d71901')

MAX_MSG_LENGTH = 4096      # same bounds as python-opentimestamps
MAX_PAYLOAD = 8192
MAX_URI = 1000
MAX_DEPTH = 256
MAX_NODES = 100000
MAX_FILE = 1 << 20
MAX_REPLY = 256 * 1024     # calendar replies are a few KB
MAX_JSON = 64 * 1024

DEFAULT_CALENDARS = (
    'https://a.pool.opentimestamps.org',
    'https://b.pool.opentimestamps.org',
    'https://a.pool.eternitywall.com',
    'https://ots.btc.catallaxy.com',
)
# Pools forward the commitment to the calendars behind them; their pending attestations name those hosts.
ALLOWED_CALENDAR_URIS = DEFAULT_CALENDARS + (
    'https://alice.btc.calendar.opentimestamps.org',
    'https://bob.btc.calendar.opentimestamps.org',
    'https://finney.calendar.eternitywall.com',
    'https://btc.calendar.catallaxy.com',      # what ots.btc.catallaxy.com answers with (seen in a real stamp)
)
ESPLORA_BASES = ('https://blockstream.info/api', 'https://mempool.space/api')
USER_AGENT = 'HomenS.AI-AutoVPN-ots/1.0 (minimal OpenTimestamps client; sends only a SHA-256 hash)'
ACCEPT = 'application/vnd.opentimestamps.v1'
TRUST_NOTE = ('merkle root and time of the Bitcoin block were confirmed by two independent explorers '
              '(blockstream.info, mempool.space); proof-of-work and chain selection are not checked locally')

_URI_RE = re.compile(r'^[-._/:A-Za-z0-9]+$')
_HEX64_RE = re.compile(r'^[0-9a-f]{64}$')


class OtsError(Exception):
    """Malformed proof or failed operation; .code is a short machine-readable reason."""
    def __init__(self, code, detail=''):
        Exception.__init__(self, code if not detail else '%s: %s' % (code, detail))
        self.code = code
        self.detail = detail


class HeaderError(OtsError):
    """Block header could not be obtained or the explorers disagree."""


# ---------------------------------------------------------------------------------------------------- hashes
def _rol32(x, i):
    return ((x << i) | ((x & 0xffffffff) >> (32 - i))) & 0xffffffff


_RMD_KL = (0, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E)
_RMD_KR = (0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0)
_RMD_ML = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8,
           3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12, 1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2,
           4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13)
_RMD_MR = (5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12, 6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2,
           15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13, 8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14,
           12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11)
_RMD_RL = (11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8, 7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12,
           11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5, 11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12,
           9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6)
_RMD_RR = (8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6, 9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11,
           9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5, 15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8,
           8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11)


def _rmd_f(x, y, z, i):
    if i == 0:
        return x ^ y ^ z
    if i == 1:
        return (x & y) | (~x & z)
    if i == 2:
        return (x | ~y) ^ z
    if i == 3:
        return (x & z) | (y & ~z)
    return x ^ (y | ~z)


def _ripemd160_pure(data):
    """RIPEMD-160 fallback for OpenSSL 3 builds without it (the OTS format uses it inside Bitcoin-style paths)."""
    m = 0xffffffff
    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    data = bytes(data) + b'\x80'
    data += b'\x00' * ((56 - len(data)) % 64) + struct.pack('<Q', (len(data) - 1) * 8)
    for off in range(0, len(data), 64):
        x = struct.unpack('<16I', data[off:off + 64])
        al, bl, cl, dl, el = h
        ar, br, cr, dr, er = h
        for j in range(80):
            r = j >> 4
            al = (_rol32(al + _rmd_f(bl, cl, dl, r) + x[_RMD_ML[j]] + _RMD_KL[r], _RMD_RL[j]) + el) & m
            al, bl, cl, dl, el = el, al, bl, _rol32(cl, 10), dl
            ar = (_rol32(ar + _rmd_f(br, cr, dr, 4 - r) + x[_RMD_MR[j]] + _RMD_KR[r], _RMD_RR[j]) + er) & m
            ar, br, cr, dr, er = er, ar, br, _rol32(cr, 10), dr
        h = [(h[1] + cl + dr) & m, (h[2] + dl + er) & m, (h[3] + el + ar) & m, (h[4] + al + br) & m, (h[0] + bl + cr) & m]
    return struct.pack('<5I', *h)


def _ripemd160(data):
    try:
        return hashlib.new('ripemd160', data).digest()
    except (ValueError, TypeError):
        return _ripemd160_pure(data)


_KECCAK_RC = (0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B,
              0x0000000080000001, 0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088,
              0x0000000080008009, 0x000000008000000A, 0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
              0x8000000000008003, 0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
              0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008)
_KECCAK_ROT = ((0, 36, 3, 41, 18), (1, 44, 10, 45, 2), (62, 6, 43, 15, 61), (28, 55, 25, 21, 56), (27, 20, 39, 8, 14))
_M64 = (1 << 64) - 1


def _rol64(x, n):
    n %= 64
    return ((x << n) | (x >> (64 - n))) & _M64 if n else x


def _keccak_f(a):
    for rc in _KECCAK_RC:
        c = [a[x] ^ a[x + 5] ^ a[x + 10] ^ a[x + 15] ^ a[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol64(c[(x + 1) % 5], 1) for x in range(5)]
        a = [a[i] ^ d[i % 5] for i in range(25)]
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol64(a[x + 5 * y], _KECCAK_ROT[x][y])
        a = [b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y]) for y in range(5) for x in range(5)]
        a[0] ^= rc
    return a


def _sponge256(data, pad):
    rate = 136
    data = bytearray(data) + bytes([pad])
    data += b'\x00' * ((-len(data)) % rate)
    data[-1] |= 0x80
    a = [0] * 25
    for off in range(0, len(data), rate):
        for i in range(rate // 8):
            a[i] ^= struct.unpack_from('<Q', data, off + 8 * i)[0]
        a = _keccak_f(a)
    return struct.pack('<4Q', *a[:4])


def _keccak256(data):
    """Original Keccak-256 (pad 0x01, as Ethereum/OTS), not NIST SHA3-256 (pad 0x06)."""
    return _sponge256(data, 0x01)


def _apply_hash(tag, msg):
    if tag == OP_SHA256:
        return hashlib.sha256(msg).digest()
    if tag == OP_SHA1:
        return hashlib.sha1(msg).digest()
    if tag == OP_RIPEMD160:
        return _ripemd160(msg)
    return _keccak256(msg)


# ---------------------------------------------------------------------------------------------------- tree
class Attestation(object):
    """An attestation leaf. Known kinds are decoded; unknown tags stay opaque (tag + raw payload)."""
    __slots__ = ('tag', 'payload', 'uri', 'height')

    def __init__(self, tag, payload):
        self.tag = bytes(tag)
        self.payload = bytes(payload)
        self.uri = None
        self.height = None
        if len(self.tag) != 8:
            raise OtsError('bad_attestation', 'tag length')
        if len(self.payload) > MAX_PAYLOAD:
            raise OtsError('bad_attestation', 'payload too long')
        if self.tag == TAG_PENDING:
            r = _Reader(self.payload)
            raw = r.varbytes(MAX_URI, 1)
            r.expect_end()
            try:
                uri = raw.decode('ascii')
            except UnicodeDecodeError:
                raise OtsError('bad_attestation', 'uri not ASCII')
            if not _URI_RE.match(uri):
                raise OtsError('bad_attestation', 'uri has illegal characters')
            self.uri = uri
        elif self.tag == TAG_BITCOIN:
            r = _Reader(self.payload)
            self.height = r.varuint()
            r.expect_end()

    @classmethod
    def pending(cls, uri):
        return cls(TAG_PENDING, _varbytes(uri.encode('ascii')))

    @classmethod
    def bitcoin(cls, height):
        return cls(TAG_BITCOIN, _varuint(height))

    @property
    def kind(self):
        return 'pending' if self.uri is not None else ('bitcoin' if self.height is not None else 'unknown')

    def sort_key(self):
        if self.uri is not None:
            return (self.tag, self.uri.encode('ascii'))
        if self.height is not None:
            return (self.tag, self.height.to_bytes(8, 'big'))
        return (self.tag, self.payload)

    def __eq__(self, other):
        return isinstance(other, Attestation) and self.tag == other.tag and self.payload == other.payload

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.tag, self.payload))

    def __repr__(self):
        if self.uri is not None:
            return 'PendingAttestation(%r)' % self.uri
        if self.height is not None:
            return 'BitcoinBlockHeaderAttestation(%d)' % self.height
        return 'UnknownAttestation(%s, %d bytes)' % (self.tag.hex(), len(self.payload))


class Node(object):
    """One message in the proof tree: attestations on it and ops leading to child nodes. ops key = (tag, arg|None)."""
    __slots__ = ('msg', 'attestations', 'ops')

    def __init__(self, msg):
        self.msg = bytes(msg)
        self.attestations = []
        self.ops = {}

    def add_op(self, tag, arg=None):
        key = (tag, arg)
        if key not in self.ops:
            self.ops[key] = Node(apply_op(tag, arg, self.msg))
        return self.ops[key]

    def add_attestation(self, att):
        if att not in self.attestations:
            self.attestations.append(att)

    def merge(self, other, _depth=0):
        if _depth > MAX_DEPTH:
            raise OtsError('recursion_limit')
        if other.msg != self.msg:
            raise OtsError('merge_msg_mismatch')
        for att in other.attestations:
            self.add_attestation(att)
        for key, child in other.ops.items():
            if key in self.ops:
                self.ops[key].merge(child, _depth + 1)
            else:
                self.ops[key] = child

    def walk(self):
        """Yield every node, depth first."""
        yield self
        for key in sorted(self.ops, key=_op_sort_key):
            for n in self.ops[key].walk():
                yield n


def _op_sort_key(key):
    return (key[0], key[1] or b'')


def apply_op(tag, arg, msg):
    if tag in HASH_OPS:
        out = _apply_hash(tag, msg)
    elif tag == OP_APPEND:
        out = msg + arg
    elif tag == OP_PREPEND:
        out = arg + msg
    else:
        raise OtsError('unknown_op', '0x%02x' % tag)
    if len(out) > MAX_MSG_LENGTH:
        raise OtsError('msg_too_long')
    return out


# ---------------------------------------------------------------------------------------------------- codec
def _varuint(n):
    if n < 0:
        raise ValueError('negative varuint')
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _varbytes(b):
    return _varuint(len(b)) + bytes(b)


class _Reader(object):
    def __init__(self, data):
        self.d = bytes(data)
        self.i = 0

    def read(self, n):
        if n < 0 or self.i + n > len(self.d):
            raise OtsError('truncated')
        out = self.d[self.i:self.i + n]
        self.i += n
        return out

    def byte(self):
        return self.read(1)[0]

    def varuint(self):
        value = shift = 0
        for _ in range(10):
            b = self.byte()
            value |= (b & 0x7f) << shift
            if not b & 0x80:
                return value
            shift += 7
        raise OtsError('bad_varuint')

    def varbytes(self, maxlen, minlen=0):
        n = self.varuint()
        if n > maxlen or n < minlen:
            raise OtsError('bad_length', '%d not in %d..%d' % (n, minlen, maxlen))
        return self.read(n)

    def expect_end(self):
        if self.i != len(self.d):
            raise OtsError('trailing_data')


def _read_node(r, msg, depth, budget):
    if depth > MAX_DEPTH:
        raise OtsError('recursion_limit')
    budget[0] -= 1
    if budget[0] < 0:
        raise OtsError('too_many_nodes')
    node = Node(msg)
    while True:
        tag = r.byte()
        last = tag != TAG_FORK
        if not last:
            tag = r.byte()
        if tag == TAG_ATTESTATION:
            att = Attestation(r.read(8), r.varbytes(MAX_PAYLOAD))
            if att in node.attestations:
                raise OtsError('duplicate_attestation')
            node.attestations.append(att)
        else:
            if tag in BINARY_OPS:
                arg = r.varbytes(MAX_MSG_LENGTH, 1)
            elif tag in HASH_OPS:
                arg = None
            else:
                raise OtsError('unknown_op', '0x%02x' % tag)
            key = (tag, arg)
            if key in node.ops:
                raise OtsError('duplicate_op')
            node.ops[key] = _read_node(r, apply_op(tag, arg, msg), depth + 1, budget)
        if last:
            return node


def parse_timestamp(data, msg):
    """Parse a bare serialized timestamp tree (calendar reply) whose root message is msg."""
    if len(data) > MAX_FILE:
        raise OtsError('too_large')
    r = _Reader(data)
    node = _read_node(r, msg, 0, [MAX_NODES])
    r.expect_end()
    return node


def _write_node(node, out):
    items = []
    for att in sorted(node.attestations, key=lambda a: a.sort_key()):
        items.append((0, att))
    for key in sorted(node.ops, key=_op_sort_key):
        items.append((1, key))
    if not items:
        raise OtsError('empty_node')
    for n, (kind, item) in enumerate(items):
        if n != len(items) - 1:
            out.append(b'\xff')
        if kind == 0:
            out.append(b'\x00' + item.tag + _varbytes(item.payload))
        else:
            out.append(bytes([item[0]]))
            if item[0] in BINARY_OPS:
                out.append(_varbytes(item[1]))
            _write_node(node.ops[item], out)


def serialize_timestamp(node):
    out = []
    _write_node(node, out)
    return b''.join(out)


class DetachedTimestamp(object):
    """A .ots file: the SHA-256 digest of the stamped data plus the proof tree rooted at it."""

    def __init__(self, digest, root=None, hash_tag=OP_SHA256):
        if hash_tag not in DIGEST_LEN or len(digest) != DIGEST_LEN[hash_tag]:
            raise OtsError('bad_file_hash')
        self.hash_tag = hash_tag
        self.digest = bytes(digest)
        self.root = root if root is not None else Node(self.digest)

    def serialize(self):
        return MAGIC + _varuint(MAJOR_VERSION) + bytes([self.hash_tag]) + self.digest + serialize_timestamp(self.root)


def parse(data):
    """Parse a .ots file. Raises OtsError with a code on anything malformed."""
    if len(data) > MAX_FILE:
        raise OtsError('too_large')
    r = _Reader(data)
    if r.read(len(MAGIC)) != MAGIC:
        raise OtsError('bad_magic')
    if r.varuint() != MAJOR_VERSION:
        raise OtsError('bad_version')
    tag = r.byte()
    if tag not in DIGEST_LEN:
        raise OtsError('bad_file_hash_op', '0x%02x' % tag)
    digest = r.read(DIGEST_LEN[tag])
    root = _read_node(r, digest, 0, [MAX_NODES])
    r.expect_end()
    return DetachedTimestamp(digest, root, tag)


# ---------------------------------------------------------------------------------------------------- network
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _default_opener():
    return urllib.request.build_opener(_NoRedirect())


def _http(opener, url, timeout, max_bytes, data=None, accept=ACCEPT):
    """One request. Returns (status, body); HTTP error statuses come back as (code, b''). Raises OtsError for
    network problems ('network_error') and oversized bodies ('oversized'). Never leaks other exceptions."""
    opener = opener or _default_opener()
    headers = {'Accept': accept, 'User-Agent': USER_AGENT}
    req = urllib.request.Request(url, data=data, headers=headers, method='POST' if data is not None else 'GET')
    try:
        resp = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        try:
            e.close()
        except Exception:
            pass
        return e.code, b''
    except Exception as e:
        raise OtsError('network_error', e.__class__.__name__)
    try:
        status = getattr(resp, 'status', None) or resp.getcode()
        body = resp.read(max_bytes + 1)
    except Exception as e:
        raise OtsError('network_error', e.__class__.__name__)
    finally:
        try:
            resp.close()
        except Exception:
            pass
    if len(body) > max_bytes:
        raise OtsError('oversized')
    return status, body


def _norm_uri(uri):
    return uri.rstrip('/')


def _is_allowed(uri, allowed):
    return _norm_uri(uri) in set(_norm_uri(a) for a in allowed)


def _commitment_of(digest32, nonce):
    return hashlib.sha256(digest32 + nonce).digest()


def stamp(digest32, calendars=DEFAULT_CALENDARS, timeout=10, opener=None, nonce=None):
    """Like `ots stamp` for a ready SHA-256 digest. Returns (ots_bytes or None, report). Network failures never raise:
    the result is None when no calendar answered. report = {'digest','commitment','nonce','ok':[...],'failed':{url:code}}."""
    if not isinstance(digest32, (bytes, bytearray)) or len(digest32) != 32:
        raise ValueError('digest32 must be 32 bytes')
    digest32 = bytes(digest32)
    nonce = os.urandom(16) if nonce is None else bytes(nonce)
    if not nonce:
        raise ValueError('nonce must not be empty')
    dt = DetachedTimestamp(digest32)
    tip = dt.root.add_op(OP_APPEND, nonce).add_op(OP_SHA256)
    commitment = tip.msg
    report = {'digest': digest32.hex(), 'nonce': nonce.hex(), 'commitment': commitment.hex(), 'ok': [], 'failed': {}}
    calendars = [_norm_uri(c) for c in calendars]

    def one(url):
        try:
            status, body = _http(opener, url + '/digest', timeout, MAX_REPLY, data=commitment)
            if status != 200:
                return url, None, 'http_%s' % status
            return url, parse_timestamp(body, commitment), None
        except OtsError as e:
            return url, None, e.code if e.code in ('oversized', 'network_error') else 'bad_reply:' + e.code

    if calendars:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(calendars)) as pool:
            results = list(pool.map(one, calendars))
        for url, node, err in results:
            if node is None:
                report['failed'][url] = err
            else:
                tip.merge(node)
                report['ok'].append(url)
    if not report['ok']:
        return None, report
    return dt.serialize(), report


def upgrade(ots_bytes, opener=None, timeout=10, allowed=None):
    """Ask the calendars for every pending attestation. Returns (new_bytes, report). A pending attestation is
    replaced when the calendar returns a Bitcoin attestation for it; 404 and network errors leave it pending.
    Only calendar URIs on the allow-list (default ALLOWED_CALENDAR_URIS) are ever contacted."""
    allowed = ALLOWED_CALENDAR_URIS if allowed is None else allowed
    dt = parse(ots_bytes)
    report = {'upgraded': 0, 'pending': [], 'rejected': [], 'errors': {}}
    todo = [(n, a) for n in dt.root.walk() for a in n.attestations if a.kind == 'pending']
    for node, att in todo:
        uri = _norm_uri(att.uri)
        if not _is_allowed(uri, allowed):
            report['rejected'].append(att.uri)
            continue
        try:
            status, body = _http(opener, '%s/timestamp/%s' % (uri, node.msg.hex()), timeout, MAX_REPLY)
            if status == 404:
                report['pending'].append(uri)
                continue
            if status != 200:
                report['errors'][uri] = 'http_%s' % status
                report['pending'].append(uri)
                continue
            new = parse_timestamp(body, node.msg)
        except OtsError as e:
            report['errors'][uri] = e.code
            report['pending'].append(uri)
            continue
        complete = any(n2.attestations and any(a.kind == 'bitcoin' for a in n2.attestations) for n2 in new.walk())
        node.merge(new)
        if complete:
            node.attestations.remove(att)
            report['upgraded'] += 1
        else:
            report['pending'].append(uri)
    new_bytes = dt.serialize()
    report['changed'] = new_bytes != ots_bytes
    return new_bytes, report


# ---------------------------------------------------------------------------------------------------- verify
def _get_text_json(opener, url, timeout, max_bytes, as_json):
    status, body = _http(opener, url, timeout, max_bytes, accept='application/json' if as_json else 'text/plain')
    if status != 200:
        raise OtsError('http_%s' % status)
    try:
        text = body.decode('ascii' if not as_json else 'utf-8')
        return json.loads(text) if as_json else text.strip()
    except (ValueError, UnicodeDecodeError):
        raise OtsError('bad_explorer_reply')


class EsploraHeaderSource(object):
    """Callable(height) -> (merkle_root_hex as displayed by explorers, unix block time). Every explorer must answer
    and all must agree; otherwise HeaderError('explorer_unavailable' | 'explorer_disagreement' | ...)."""

    def __init__(self, bases=ESPLORA_BASES, opener=None, timeout=10):
        self.bases = tuple(bases)
        self.opener = opener
        self.timeout = timeout

    def _one(self, base, height):
        h = _get_text_json(self.opener, '%s/block-height/%d' % (base, height), self.timeout, 256, False)
        if not _HEX64_RE.match(h):
            raise OtsError('bad_explorer_reply', 'block hash')
        j = _get_text_json(self.opener, '%s/block/%s' % (base, h), self.timeout, MAX_JSON, True)
        if not isinstance(j, dict) or j.get('id') != h or j.get('height') != height:
            raise OtsError('bad_explorer_reply', 'block id/height mismatch')
        root, ts = j.get('merkle_root'), j.get('timestamp')
        if not isinstance(root, str) or not _HEX64_RE.match(root) or not isinstance(ts, int) or isinstance(ts, bool):
            raise OtsError('bad_explorer_reply', 'merkle_root/timestamp')
        return root, ts

    def __call__(self, height):
        got, errors = {}, {}
        for base in self.bases:
            try:
                got[base] = self._one(base, height)
            except OtsError as e:
                errors[base] = e.code
        if errors:
            raise HeaderError('explorer_unavailable', json.dumps(errors, sort_keys=True))
        if len(set(got.values())) != 1:
            raise HeaderError('explorer_disagreement', json.dumps(got, sort_keys=True))
        return list(got.values())[0]


def _iso(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def verify(ots_bytes, digest32, header_source=None):
    """Check a .ots proof for digest32. Returns a dict with 'status':
      'confirmed'  - Bitcoin attestation recomputed from the digest and matched against the block (see module doc);
                     keys height (lowest verified), block_time (UTC ISO), merkle_root (explorer display order)
      'pending'    - only calendar promises so far; key calendars
      'invalid'    - code: bad proof file / digest_mismatch / merkle_root_mismatch / no_known_attestation ...
      'unverified' - structure fine but the block could not be checked (explorers down or disagreeing); code says why
    header_source(height) -> (merkle_root_hex_display_order, unix_time); raise HeaderError to signal 'unverified'."""
    try:
        dt = parse(ots_bytes)
    except OtsError as e:
        return {'status': 'invalid', 'code': 'bad_proof:' + e.code}
    if not isinstance(digest32, (bytes, bytearray)) or len(digest32) != 32:
        return {'status': 'invalid', 'code': 'bad_digest_argument'}
    if dt.hash_tag != OP_SHA256:
        return {'status': 'invalid', 'code': 'unsupported_file_hash'}
    if dt.digest != bytes(digest32):
        return {'status': 'invalid', 'code': 'digest_mismatch', 'digest': bytes(digest32).hex(),
                'proof_digest': dt.digest.hex()}
    bitcoin, pending, unknown = [], [], 0
    for n in dt.root.walk():
        for a in n.attestations:
            if a.kind == 'bitcoin':
                bitcoin.append((a.height, n.msg))
            elif a.kind == 'pending':
                pending.append(a.uri)
            else:
                unknown += 1
    if not bitcoin:
        if pending:
            return {'status': 'pending', 'code': 'pending_only', 'calendars': sorted(set(pending)), 'digest': dt.digest.hex()}
        return {'status': 'invalid', 'code': 'no_known_attestation', 'unknown_attestations': unknown}
    header_source = header_source or EsploraHeaderSource()
    problems = []
    for height, msg in sorted(set(bitcoin)):
        try:
            root_hex, ts = header_source(height)
        except HeaderError as e:
            problems.append(('unverified', e.code, height, e.detail))
            continue
        except OtsError as e:
            problems.append(('unverified', e.code, height, e.detail))
            continue
        try:
            internal = bytes.fromhex(root_hex)[::-1]   # explorers show the merkle root reversed (RPC byte order)
        except (ValueError, TypeError):
            internal = b''
        if len(internal) != 32 or not isinstance(ts, int):
            problems.append(('unverified', 'bad_header_data', height, ''))
        elif internal != msg:
            problems.append(('invalid', 'merkle_root_mismatch', height, ''))
        else:
            res = {'status': 'confirmed', 'code': 'ok', 'height': height, 'block_time': _iso(ts), 'block_time_unix': ts,
                   'merkle_root': root_hex, 'digest': dt.digest.hex(), 'trust': TRUST_NOTE}
            if problems:
                res['skipped'] = [{'height': p[2], 'code': p[1]} for p in problems]
            return res
    # nothing verified: any attestation we could not check makes it 'unverified', otherwise it is plainly wrong
    kinds = [p[0] for p in problems]
    first = problems[0]
    status = 'unverified' if 'unverified' in kinds else 'invalid'
    pick = [p for p in problems if p[0] == status][0] if status == 'unverified' else first
    return {'status': status, 'code': pick[1], 'height': pick[2], 'detail': pick[3],
            'attempts': [{'height': p[2], 'code': p[1]} for p in problems]}


# ---------------------------------------------------------------------------------------------------- info / CLI
def info(ots_bytes):
    dt = parse(ots_bytes)
    lines = ['File sha256 hash: ' + dt.digest.hex() if dt.hash_tag == OP_SHA256
             else 'File %s hash: %s' % (HASH_OPS[dt.hash_tag], dt.digest.hex()), 'Timestamp:']

    def show(node, indent):
        pad = ' ' * indent
        items = [('att', a) for a in sorted(node.attestations, key=lambda a: a.sort_key())]
        items += [('op', k) for k in sorted(node.ops, key=_op_sort_key)]
        for n, (kind, item) in enumerate(items):
            fork = len(items) > 1
            head = ' -> ' if fork else ''
            if kind == 'att':
                lines.append('%s%sverify %r' % (pad, head, item))
            else:
                name = HASH_OPS.get(item[0]) or BINARY_OPS[item[0]]
                lines.append('%s%s%s%s' % (pad, head, name, ' ' + item[1].hex() if item[1] is not None else ''))
                show(node.ops[item], indent + (4 if fork else 0))
    show(dt.root, 0)
    return '\n'.join(lines)


def _write_atomic(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)


def _file_digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.digest()


def main(argv=None):
    ap = argparse.ArgumentParser(description='Minimal OpenTimestamps client (only a SHA-256 hash leaves this PC).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('stamp', help='stamp sha256(FILE) with the public calendars')
    p.add_argument('file')
    p.add_argument('-o', '--out', required=True)
    p.add_argument('--timeout', type=int, default=10)
    p = sub.add_parser('upgrade', help='fetch Bitcoin attestations for pending calendar promises (rewrites the file)')
    p.add_argument('ots')
    p.add_argument('--timeout', type=int, default=10)
    p = sub.add_parser('verify', help='verify OTS against FILE (hash of FILE) using two block explorers')
    p.add_argument('ots')
    p.add_argument('file')
    p = sub.add_parser('info', help='print the proof tree')
    p.add_argument('ots')
    args = ap.parse_args(argv)
    try:
        if args.cmd == 'stamp':
            data, rep = stamp(_file_digest(args.file), timeout=args.timeout)
            print(json.dumps(rep, indent=2, sort_keys=True))
            if data is None:
                print('stamp FAILED: no calendar answered', file=sys.stderr)
                return 2
            _write_atomic(args.out, data)
            print('wrote %s (%d bytes, pending until a Bitcoin block includes it; run upgrade later)' % (args.out, len(data)))
            return 0
        if args.cmd == 'upgrade':
            with open(args.ots, 'rb') as f:
                old = f.read()
            new, rep = upgrade(old, timeout=args.timeout)
            print(json.dumps(rep, indent=2, sort_keys=True))
            if new != old:
                _write_atomic(args.ots, new)
                print('updated', args.ots)
            return 0
        if args.cmd == 'verify':
            with open(args.ots, 'rb') as f:
                res = verify(f.read(), _file_digest(args.file))
            print(json.dumps(res, indent=2, sort_keys=True))
            return {'confirmed': 0, 'pending': 3, 'unverified': 4}.get(res['status'], 1)
        with open(args.ots, 'rb') as f:
            print(info(f.read()))
        return 0
    except (OtsError, OSError) as e:
        print('error: %s' % e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
