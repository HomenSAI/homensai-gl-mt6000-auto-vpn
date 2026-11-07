"""Offline tests for scripts/signing/ots.py (minimal OpenTimestamps client). No network: calendars and block
explorers are mocked through the injectable opener / header_source. One real vector is included: the official
example proof examples/hello-world.txt.ots of github.com/opentimestamps/opentimestamps-client (Bitcoin block 358391)."""
import contextlib
import hashlib
import io
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'signing'))

import ots  # noqa: E402

# ---- real vector: opentimestamps-client/examples/hello-world.txt(.ots), 688 bytes, attested in Bitcoin block 358391
OFFICIAL_FILE = b'Hello World!\n'
OFFICIAL_OTS = bytes.fromhex(
    "004f70656e54696d657374616d7073000050726f6f6600bf89e2e884e89294010803ba204e50d126e4674c005e04d82e"
    "84c21366780af1f43bd54a37816b6ab34003f1c8010100000001e482f9d32ecc3ba657b69d898010857b54457a904979"
    "82ff56f97c4ec58e6f98010000006b483045022100b253add1d1cf90844338a475a04ff13fc9e7bd242b07762dea07f5"
    "608b2de367022000b268ca9c3342b3769cdd062891317cdcef87aac310b6855e9d93898ebbe8ec0121020d8e4d107d2b"
    "339b0050efdd4b4a09245aa056048f125396374ea6a2ab0709c6ffffffff026533e605000000001976a9140bf057d40f"
    "bba6744862515f5b55a2310de5772f88aca0860100000000001976a914f00688ac000000000808f120a987f716c53391"
    "3c314c78e35d35884cac943fa42cac49d2b2c69f4003f85f880808f120dec55b3487e1e3f722a49b55a7783215862785"
    "f4a3acb392846019f71dc64a9d0808f120b2ca18f485e080478e025dab3d464b416c0e1ecb6629c9aefce8c8214d0424"
    "320808f02011b0e90661196ff4b0813c3eda141bab5e91604837bdf7a0c9df37db0e3a11980808f020c34bc1a4a1093f"
    "fd148c016b1e664742914e939efabe4d3d356515914b26d9e20808f020c3e6e7c38c69f6af24c2be34ebac48257ede61"
    "ec0a21b9535e4443277be306460808f1200798bf8606e00024e5d5d54bf0c960f629dfb9dad69157455b6f2652c0e8de"
    "810808f0203f9ada6d60baa244006bb0aad51448ad2fafb9d4b6487a0999cff26b91f0f5360808f120c703019e959a8d"
    "d3faef7489bb328ba485574758e7091f01464eb65872c975c80808f020cbfefff513ff84b915e3fed6f9d799676630f8"
    "364ea2a6c7557fad94a5b5d7880808f1200be23709859913babd4460bbddf8ed213e7c8773a4b1face30f8acfdf093b7"
    "050808000588960d73d7190103f7ef15"
)
OFFICIAL_HEIGHT = 358391
# Fetched once from blockstream.info and cross-checked on mempool.space (2026-11-03):
#   GET /api/block-height/358391 -> 000000000000000003e892881a8cdcdc117c06d444057c98b6f04a9ee75a2319
#   GET /api/block/<hash>        -> merkle_root (as displayed by explorers, reversed vs. the header bytes), timestamp
OFFICIAL_MERKLE_ROOT_DISPLAY = '8a1b66ecb7cbd07d8139a7e7d7f2c41aab1f5009b8364aaf61d03ad245e47e00'
OFFICIAL_BLOCK_TIME = 1432827678            # 2015-05-28T15:41:18Z
OFFICIAL_BLOCK_HASH = '000000000000000003e892881a8cdcdc117c06d444057c98b6f04a9ee75a2319'

DIGEST = hashlib.sha256(b'HomenS.AI Auto VPN OTS test 2026-11-03').digest()
NONCE = bytes(range(16))
ALICE = 'https://alice.btc.calendar.opentimestamps.org'


class FakeResponse(object):
    def __init__(self, body, status=200):
        self._body = body
        self.status = status

    def read(self, n=-1):
        return self._body if n is None or n < 0 else self._body[:n]

    def close(self):
        pass


class FakeOpener(object):
    """handler(method, url, data) -> bytes | FakeResponse | Exception instance (raised)."""
    def __init__(self, handler):
        self.handler = handler
        self.requests = []
        self.lock = threading.Lock()

    def open(self, req, timeout=None):
        with self.lock:
            self.requests.append({'method': req.get_method(), 'url': req.full_url, 'data': req.data,
                                  'headers': dict((k.lower(), v) for k, v in req.header_items()), 'timeout': timeout})
        out = self.handler(req.get_method(), req.full_url, req.data)
        if isinstance(out, Exception):
            raise out
        return out if isinstance(out, FakeResponse) else FakeResponse(out)


def http_error(url, code):
    return urllib.error.HTTPError(url, code, 'err', {}, None)


def pending_reply(commitment, uri, salt=b'cal'):
    """What a calendar answers to POST /digest: a bare tree commitment -> append salt -> sha256 -> pending(uri)."""
    n = ots.Node(commitment)
    n.add_op(ots.OP_APPEND, salt).add_op(ots.OP_SHA256).add_attestation(ots.Attestation.pending(uri))
    return ots.serialize_timestamp(n)


def pending_msg(commitment, salt=b'cal'):
    return hashlib.sha256(commitment + salt).digest()


def bitcoin_reply(msg, height, salt=b'btc'):
    n = ots.Node(msg)
    tip = n.add_op(ots.OP_APPEND, salt).add_op(ots.OP_SHA256)
    tip.add_attestation(ots.Attestation.bitcoin(height))
    return ots.serialize_timestamp(n), tip.msg


def display(root_internal):
    return root_internal[::-1].hex()


def stamp_ok(calendars=ots.DEFAULT_CALENDARS):
    def handler(method, url, data):
        return pending_reply(data, ALICE)
    return ots.stamp(DIGEST, calendars=calendars, opener=FakeOpener(handler), nonce=NONCE)


class TestPrimitives(unittest.TestCase):
    def test_varuint_known_vector(self):
        self.assertEqual(ots._varuint(358391), bytes.fromhex('f7ef15'))
        self.assertEqual(ots._Reader(bytes.fromhex('f7ef15')).varuint(), 358391)
        self.assertEqual(ots._varuint(0), b'\x00')
        self.assertEqual(ots._varuint(127), b'\x7f')
        self.assertEqual(ots._varuint(128), b'\x80\x01')

    def test_fallback_hashes_match_published_vectors(self):
        self.assertEqual(ots._ripemd160_pure(b'abc').hex(), '8eb208f7e05d987a9b044a8e98c6b087f15a0bfc')
        self.assertEqual(ots._ripemd160_pure(b'').hex(), '9c1185a5c5e9fc54612808977ee8f548b2258d31')
        self.assertEqual(ots._keccak256(b'').hex(), 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470')
        # same permutation with NIST padding must equal hashlib's sha3_256
        self.assertEqual(ots._sponge256(b'abc' * 100, 0x06), hashlib.sha3_256(b'abc' * 100).digest())

    def test_ops_evaluate(self):
        self.assertEqual(ots.apply_op(ots.OP_APPEND, b'xy', b'ab'), b'abxy')
        self.assertEqual(ots.apply_op(ots.OP_PREPEND, b'xy', b'ab'), b'xyab')
        self.assertEqual(ots.apply_op(ots.OP_SHA1, None, b'abc'), hashlib.sha1(b'abc').digest())
        self.assertEqual(ots.apply_op(ots.OP_SHA256, None, b'abc'), hashlib.sha256(b'abc').digest())
        self.assertEqual(len(ots.apply_op(ots.OP_RIPEMD160, None, b'abc')), 20)
        with self.assertRaises(ots.OtsError) as c:
            ots.apply_op(0xf2, None, b'abc')
        self.assertEqual(c.exception.code, 'unknown_op')
        with self.assertRaises(ots.OtsError) as c:
            ots.apply_op(ots.OP_APPEND, b'x' * 5000, b'')
        self.assertEqual(c.exception.code, 'msg_too_long')


class TestFormat(unittest.TestCase):
    def test_official_example_roundtrip_is_byte_identical(self):
        dt = ots.parse(OFFICIAL_OTS)
        self.assertEqual(dt.serialize(), OFFICIAL_OTS)
        self.assertEqual(dt.digest, hashlib.sha256(OFFICIAL_FILE).digest())
        atts = [a for n in dt.root.walk() for a in n.attestations]
        self.assertEqual([repr(a) for a in atts], ['BitcoinBlockHeaderAttestation(358391)'])

    def test_official_example_info(self):
        text = ots.info(OFFICIAL_OTS)
        self.assertIn('File sha256 hash: ' + hashlib.sha256(OFFICIAL_FILE).hexdigest(), text)
        self.assertIn('verify BitcoinBlockHeaderAttestation(358391)', text)

    def test_serialization_is_sorted_and_unknown_attestation_is_kept(self):
        unknown = ots.Attestation(bytes.fromhex('0102030405060708'), b'\xde\xad')
        n = ots.Node(DIGEST)
        n.add_attestation(ots.Attestation.pending('https://b.example/x'))
        n.add_attestation(unknown)
        n.add_attestation(ots.Attestation.bitcoin(7))
        n.add_attestation(ots.Attestation.pending('https://a.example/x'))
        for tag, arg in ((ots.OP_PREPEND, b'\x01'), (ots.OP_APPEND, b'\x02'), (ots.OP_SHA256, None)):
            n.add_op(tag, arg).add_attestation(ots.Attestation.bitcoin(1))
        raw = ots.DetachedTimestamp(DIGEST, n).serialize()
        back = ots.parse(raw)
        self.assertEqual(back.serialize(), raw)
        kinds = [repr(a) for a in sorted(back.root.attestations, key=lambda a: a.sort_key())]
        self.assertEqual(kinds, ['UnknownAttestation(0102030405060708, 2 bytes)', 'BitcoinBlockHeaderAttestation(7)',
                                 "PendingAttestation('https://a.example/x')", "PendingAttestation('https://b.example/x')"])
        # ops sorted by tag: sha256 (08) < append (f0) < prepend (f1); the last item has no 0xff marker
        leaf = b'\x00' + ots.TAG_BITCOIN + b'\x01\x01'
        self.assertTrue(raw.endswith(b'\xff\x08' + leaf + b'\xff\xf0\x01\x02' + leaf + b'\xf1\x01\x01' + leaf))

    def test_reject_clean_errors(self):
        def code(data):
            with self.assertRaises(ots.OtsError) as c:
                ots.parse(data)
            return c.exception.code
        self.assertEqual(code(b'nope'), 'truncated')
        self.assertEqual(code(b'x' * len(ots.MAGIC)), 'bad_magic')
        self.assertEqual(code(ots.MAGIC + b'\x02'), 'bad_version')
        self.assertEqual(code(ots.MAGIC + b'\x01\x09'), 'bad_file_hash_op')
        head = ots.MAGIC + b'\x01\x08' + DIGEST
        self.assertEqual(code(head + b'\xf2'), 'unknown_op')
        self.assertEqual(code(head + b'\xf0\x01\x00' + b'\x00' + ots.TAG_BITCOIN + b'\x01\x05' + b'\x00'), 'trailing_data')
        self.assertEqual(code(head + b'\xf0\x00'), 'bad_length')                      # empty append argument
        self.assertEqual(code(head + b'\xf0\xff\xff\x7f'), 'bad_length')              # absurd length
        bad_uri = b'\x04ab c'
        self.assertEqual(code(head + b'\x00' + ots.TAG_PENDING + bytes([len(bad_uri)]) + bad_uri), 'bad_attestation')
        self.assertEqual(code(head + b'\x00' + ots.TAG_BITCOIN + b'\x03\x80\x80\x80'), 'truncated')  # payload ends inside the varuint
        dup = b'\xff\x08' + b'\x00' + ots.TAG_BITCOIN + b'\x01\x05' + b'\x08' + b'\x00' + ots.TAG_BITCOIN + b'\x01\x05'
        self.assertEqual(code(head + dup), 'duplicate_op')

    def test_every_truncation_of_a_real_file_fails_cleanly(self):
        for n in range(len(OFFICIAL_OTS)):
            with self.assertRaises(ots.OtsError):
                ots.parse(OFFICIAL_OTS[:n])
        with self.assertRaises(ots.OtsError):
            ots.parse(OFFICIAL_OTS + b'\x00')

    def test_recursion_depth_is_bounded(self):
        head = ots.MAGIC + b'\x01\x08' + DIGEST
        leaf = b'\x00' + ots.TAG_BITCOIN + b'\x01\x05'
        ok = head + b'\x08' * ots.MAX_DEPTH + leaf
        ots.parse(ok)
        with self.assertRaises(ots.OtsError) as c:
            ots.parse(head + b'\x08' * (ots.MAX_DEPTH + 5) + leaf)
        self.assertEqual(c.exception.code, 'recursion_limit')

    def test_size_bounds(self):
        with self.assertRaises(ots.OtsError) as c:
            ots.parse(b'\x00' * (ots.MAX_FILE + 1))
        self.assertEqual(c.exception.code, 'too_large')
        # a wide tree (300 sibling forks) parses and re-serializes stably
        head = ots.MAGIC + b'\x01\x08' + DIGEST
        body = b''.join(b'\xff\xf0\x02' + (i.to_bytes(2, 'big')) + b'\x00' + ots.TAG_BITCOIN + b'\x01\x05' for i in range(300))
        tree = head + body + b'\x08\x00' + ots.TAG_BITCOIN + b'\x01\x05'
        self.assertEqual(ots.parse(tree).serialize(), ots.parse(ots.parse(tree).serialize()).serialize())


class TestStamp(unittest.TestCase):
    def test_success_all_calendars_and_request_shape(self):
        opener = FakeOpener(lambda m, u, d: pending_reply(d, ALICE))
        data, rep = ots.stamp(DIGEST, opener=opener, nonce=NONCE, timeout=7)
        commitment = hashlib.sha256(DIGEST + NONCE).digest()
        self.assertEqual(rep['commitment'], commitment.hex())
        self.assertEqual(sorted(rep['ok']), sorted(ots.DEFAULT_CALENDARS))
        self.assertEqual(rep['failed'], {})
        self.assertEqual(sorted(r['url'] for r in opener.requests), sorted(c + '/digest' for c in ots.DEFAULT_CALENDARS))
        for r in opener.requests:
            self.assertEqual(r['method'], 'POST')
            self.assertEqual(r['data'], commitment)          # only the 32-byte commitment is sent
            self.assertEqual(len(r['data']), 32)
            self.assertEqual(r['headers']['accept'], 'application/vnd.opentimestamps.v1')
            self.assertIn('homens.ai', r['headers']['user-agent'].lower())
            self.assertEqual(r['timeout'], 7)
        dt = ots.parse(data)
        self.assertEqual(dt.serialize(), data)
        self.assertEqual(dt.digest, DIGEST)
        # structure: digest -> append(nonce) -> sha256 -> (merged calendar replies)
        (k1, n1), = dt.root.ops.items()
        self.assertEqual(k1, (ots.OP_APPEND, NONCE))
        (k2, n2), = n1.ops.items()
        self.assertEqual(k2, (ots.OP_SHA256, None))
        self.assertEqual(n2.msg, commitment)
        # all four calendars returned the same tree: merged, not duplicated
        self.assertEqual([repr(a) for n in dt.root.walk() for a in n.attestations], ["PendingAttestation('%s')" % ALICE])

    def test_distinct_calendar_replies_become_forks(self):
        def handler(method, url, data):
            return pending_reply(data, 'https://cal%d.example' % (len(url) % 7), salt=url.encode())
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(handler), nonce=NONCE)
        dt = ots.parse(data)
        self.assertEqual(len(dt.root.ops[(ots.OP_APPEND, NONCE)].ops[(ots.OP_SHA256, None)].ops), 4)
        self.assertEqual(dt.serialize(), data)

    def test_one_calendar_down(self):
        def handler(method, url, data):
            if url.startswith('https://a.pool.opentimestamps.org'):
                return urllib.error.URLError('connection refused')
            if url.startswith('https://b.pool.opentimestamps.org'):
                return http_error(url, 500)
            return pending_reply(data, ALICE)
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(handler), nonce=NONCE)
        self.assertIsNotNone(data)
        self.assertEqual(sorted(rep['ok']), ['https://a.pool.eternitywall.com', 'https://ots.btc.catallaxy.com'])
        self.assertEqual(rep['failed']['https://a.pool.opentimestamps.org'], 'network_error')
        self.assertEqual(rep['failed']['https://b.pool.opentimestamps.org'], 'http_500')

    def test_all_down_returns_none_and_never_raises(self):
        for failure in (urllib.error.URLError('dns'), socket.timeout('t'), ConnectionResetError(), ValueError('boom'),
                        RuntimeError('x'), http_error('u', 503)):
            data, rep = ots.stamp(DIGEST, opener=FakeOpener(lambda m, u, d, f=failure: f), nonce=NONCE)
            self.assertIsNone(data)
            self.assertEqual(rep['ok'], [])
            self.assertEqual(len(rep['failed']), 4)

    def test_read_failure_is_a_network_error(self):
        class Broken(FakeResponse):
            def read(self, n=-1):
                raise socket.timeout('read timed out')
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(lambda m, u, d: Broken(b'')), nonce=NONCE)
        self.assertIsNone(data)
        self.assertEqual(set(rep['failed'].values()), {'network_error'})

    def test_garbage_and_oversized_replies(self):
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(lambda m, u, d: b'<html>captive portal</html>'), nonce=NONCE)
        self.assertIsNone(data)
        self.assertTrue(all(v.startswith('bad_reply:') for v in rep['failed'].values()), rep)
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(lambda m, u, d: b'\x08' * (ots.MAX_REPLY + 1)), nonce=NONCE)
        self.assertIsNone(data)
        self.assertEqual(set(rep['failed'].values()), {'oversized'})

    def test_reply_with_trailing_junk_or_wrong_status_is_rejected(self):
        good = lambda d: pending_reply(d, ALICE)
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(lambda m, u, d: good(d) + b'junk'), nonce=NONCE)
        self.assertIsNone(data)
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(lambda m, u, d: FakeResponse(good(d), 202)), nonce=NONCE)
        self.assertIsNone(data)
        self.assertEqual(set(rep['failed'].values()), {'http_202'})

    def test_one_bad_reply_does_not_poison_the_good_ones(self):
        def handler(method, url, data):
            return b'\xff\xff' if 'catallaxy' in url else pending_reply(data, ALICE)
        data, rep = ots.stamp(DIGEST, opener=FakeOpener(handler), nonce=NONCE)
        self.assertEqual(len(rep['ok']), 3)
        self.assertIn('https://ots.btc.catallaxy.com', rep['failed'])
        self.assertEqual(ots.parse(data).serialize(), data)

    def test_random_nonce_by_default_and_argument_checks(self):
        opener = FakeOpener(lambda m, u, d: pending_reply(d, ALICE))
        _, r1 = ots.stamp(DIGEST, opener=opener)
        _, r2 = ots.stamp(DIGEST, opener=opener)
        self.assertEqual(len(bytes.fromhex(r1['nonce'])), 16)
        self.assertNotEqual(r1['nonce'], r2['nonce'])
        with self.assertRaises(ValueError):
            ots.stamp(b'short', opener=opener)

    def test_no_calendars_is_a_failure_not_an_exception(self):
        data, rep = ots.stamp(DIGEST, calendars=(), opener=FakeOpener(lambda m, u, d: b''), nonce=NONCE)
        self.assertIsNone(data)


class TestUpgrade(unittest.TestCase):
    def setUp(self):
        self.stamped, self.rep = stamp_ok()
        self.commitment = hashlib.sha256(DIGEST + NONCE).digest()
        self.cal_msg = pending_msg(self.commitment)

    def test_pending_becomes_bitcoin(self):
        reply, tip = bitcoin_reply(self.cal_msg, 800000)
        calls = []

        def handler(method, url, data):
            calls.append((method, url))
            return reply
        new, rep = ots.upgrade(self.stamped, opener=FakeOpener(handler))
        self.assertEqual(calls, [('GET', '%s/timestamp/%s' % (ALICE, self.cal_msg.hex()))])
        self.assertEqual(rep['upgraded'], 1)
        self.assertTrue(rep['changed'])
        dt = ots.parse(new)
        self.assertEqual(dt.serialize(), new)
        atts = [repr(a) for n in dt.root.walk() for a in n.attestations]
        self.assertEqual(atts, ['BitcoinBlockHeaderAttestation(800000)'])   # the pending promise is replaced
        # and the result verifies end to end against a header source returning the computed root
        res = ots.verify(new, DIGEST, header_source=lambda h: (display(tip), 1700000000))
        self.assertEqual((res['status'], res['height']), ('confirmed', 800000))

    def test_404_and_network_errors_keep_pending(self):
        for out in (http_error('u', 404), urllib.error.URLError('x'), b'garbage', http_error('u', 500)):
            new, rep = ots.upgrade(self.stamped, opener=FakeOpener(lambda m, u, d, o=out: o))
            self.assertEqual(new, self.stamped)
            self.assertFalse(rep['changed'])
            self.assertEqual(rep['upgraded'], 0)
            self.assertEqual(rep['pending'], [ALICE])
            self.assertEqual(ots.verify(new, DIGEST)['status'], 'pending')

    def test_pending_reply_stays_pending_but_merges(self):
        n = ots.Node(self.cal_msg)
        n.add_op(ots.OP_APPEND, b'z').add_attestation(ots.Attestation.pending('https://bob.btc.calendar.opentimestamps.org'))
        new, rep = ots.upgrade(self.stamped, opener=FakeOpener(lambda m, u, d: ots.serialize_timestamp(n)))
        self.assertEqual(rep['upgraded'], 0)
        pend = sorted(a.uri for x in ots.parse(new).root.walk() for a in x.attestations)
        self.assertEqual(pend, [ALICE, 'https://bob.btc.calendar.opentimestamps.org'])

    def test_allow_list_blocks_foreign_and_downgraded_uris(self):
        for uri in ('https://evil.example', 'http://alice.btc.calendar.opentimestamps.org',
                    'https://alice.btc.calendar.opentimestamps.org.evil.example', 'https://169.254.169.254/latest',
                    'file:///etc/passwd'):
            n = ots.Node(DIGEST)
            n.add_attestation(ots.Attestation.pending(uri))
            raw = ots.DetachedTimestamp(DIGEST, n).serialize()
            opener = FakeOpener(lambda m, u, d: b'')
            new, rep = ots.upgrade(raw, opener=opener)
            self.assertEqual(opener.requests, [], uri)
            self.assertEqual(rep['rejected'], [uri])
            self.assertEqual(new, raw)

    def test_allow_list_accepts_trailing_slash_and_explicit_list(self):
        n = ots.Node(DIGEST)
        n.add_attestation(ots.Attestation.pending('https://a.pool.opentimestamps.org/'))
        raw = ots.DetachedTimestamp(DIGEST, n).serialize()
        opener = FakeOpener(lambda m, u, d: http_error(u, 404))
        ots.upgrade(raw, opener=opener)
        self.assertEqual(opener.requests[0]['url'], 'https://a.pool.opentimestamps.org/timestamp/' + DIGEST.hex())
        opener = FakeOpener(lambda m, u, d: http_error(u, 404))
        _, rep = ots.upgrade(raw, opener=opener, allowed=('https://other.example',))
        self.assertEqual(opener.requests, [])

    def test_default_allow_list_covers_default_calendars(self):
        for c in ots.DEFAULT_CALENDARS:
            self.assertIn(c, ots.ALLOWED_CALENDAR_URIS)
        # hosts the pools were seen to hand out in a real stamp (2026-11-03)
        for c in ('https://alice.btc.calendar.opentimestamps.org', 'https://bob.btc.calendar.opentimestamps.org',
                  'https://finney.calendar.eternitywall.com', 'https://btc.calendar.catallaxy.com'):
            self.assertIn(c, ots.ALLOWED_CALENDAR_URIS)

    def test_upgrade_of_garbage_input_raises_otserror(self):
        with self.assertRaises(ots.OtsError):
            ots.upgrade(b'not an ots file')


class TestVerify(unittest.TestCase):
    def confirmed_proof(self, height=800000):
        stamped, _ = stamp_ok()
        commitment = hashlib.sha256(DIGEST + NONCE).digest()
        reply, tip = bitcoin_reply(pending_msg(commitment), height)
        new, _ = ots.upgrade(stamped, opener=FakeOpener(lambda m, u, d: reply))
        return new, tip

    def test_confirmed(self):
        proof, root = self.confirmed_proof()
        seen = []

        def hs(height):
            seen.append(height)
            return display(root), 1700000000
        res = ots.verify(proof, DIGEST, header_source=hs)
        self.assertEqual(res['status'], 'confirmed')
        self.assertEqual(res['height'], 800000)
        self.assertEqual(res['block_time'], '2023-11-14T22:13:20Z')
        self.assertEqual(res['merkle_root'], display(root))
        self.assertIn('two independent explorers', res['trust'])
        self.assertEqual(seen, [800000])

    def test_pending(self):
        stamped, _ = stamp_ok()
        called = []
        res = ots.verify(stamped, DIGEST, header_source=lambda h: called.append(h))
        self.assertEqual(res['status'], 'pending')
        self.assertEqual(res['calendars'], [ALICE])
        self.assertEqual(called, [])

    def test_tampered_digest(self):
        proof, root = self.confirmed_proof()
        other = hashlib.sha256(b'something else').digest()
        res = ots.verify(proof, other, header_source=lambda h: (display(root), 1))
        self.assertEqual((res['status'], res['code']), ('invalid', 'digest_mismatch'))
        res = ots.verify(proof, b'short')
        self.assertEqual((res['status'], res['code']), ('invalid', 'bad_digest_argument'))

    def test_tampered_proof_bytes(self):
        proof, root = self.confirmed_proof()
        i = proof.index(b'btc')                 # inside an append argument: changes the computed merkle root
        bad = proof[:i] + b'xtc' + proof[i + 3:]
        res = ots.verify(bad, DIGEST, header_source=lambda h: (display(root), 1700000000))
        self.assertEqual((res['status'], res['code']), ('invalid', 'merkle_root_mismatch'))

    def test_garbage_proof(self):
        res = ots.verify(b'garbage', DIGEST)
        self.assertEqual(res['status'], 'invalid')
        self.assertTrue(res['code'].startswith('bad_proof:'))

    def test_wrong_root_wrong_byte_order(self):
        proof, root = self.confirmed_proof()
        res = ots.verify(proof, DIGEST, header_source=lambda h: (root.hex(), 1700000000))  # not reversed
        self.assertEqual((res['status'], res['code']), ('invalid', 'merkle_root_mismatch'))

    def test_header_source_failure_is_unverified(self):
        proof, root = self.confirmed_proof()

        def hs(height):
            raise ots.HeaderError('explorer_unavailable', 'x')
        res = ots.verify(proof, DIGEST, header_source=hs)
        self.assertEqual((res['status'], res['code']), ('unverified', 'explorer_unavailable'))

    def test_garbage_from_header_source_is_unverified(self):
        proof, root = self.confirmed_proof()
        for bad in (('zz', 1), ('00' * 31, 1), (display(root), 'x')):
            res = ots.verify(proof, DIGEST, header_source=lambda h, b=bad: b)
            self.assertEqual(res['status'], 'unverified', bad)

    def test_lowest_confirmed_height_wins_and_forged_lower_is_skipped(self):
        _, tip1 = bitcoin_reply(DIGEST, 1, b'one')
        n = ots.Node(DIGEST)
        for salt, h in ((b'one', 100), (b'two', 200)):
            n.add_op(ots.OP_APPEND, salt).add_op(ots.OP_SHA256).add_attestation(ots.Attestation.bitcoin(h))
        raw = ots.DetachedTimestamp(DIGEST, n).serialize()
        roots = {100: hashlib.sha256(DIGEST + b'one').digest(), 200: hashlib.sha256(DIGEST + b'two').digest()}
        res = ots.verify(raw, DIGEST, header_source=lambda h: (display(roots[h]), 1600000000 + h))
        self.assertEqual((res['status'], res['height']), ('confirmed', 100))
        wrong100 = lambda h: (display(roots[h] if h == 200 else b'\x01' * 32), 1600000000)
        res = ots.verify(raw, DIGEST, header_source=wrong100)
        self.assertEqual((res['status'], res['height']), ('confirmed', 200))
        self.assertEqual(res['skipped'], [{'height': 100, 'code': 'merkle_root_mismatch'}])

    def test_no_known_attestation(self):
        n = ots.Node(DIGEST)
        n.add_attestation(ots.Attestation(bytes.fromhex('0102030405060708'), b'x'))
        res = ots.verify(ots.DetachedTimestamp(DIGEST, n).serialize(), DIGEST)
        self.assertEqual((res['status'], res['code']), ('invalid', 'no_known_attestation'))


class TestExplorers(unittest.TestCase):
    ROOT_A = '11' * 32
    ROOT_B = '22' * 32
    H = 'ab' * 32

    def opener(self, roots=None, down=(), time=(1, 1), bad_id=False):
        roots = roots or {'blockstream.info': self.ROOT_A, 'mempool.space': self.ROOT_A}
        times = dict(zip(('blockstream.info', 'mempool.space'), time))

        def handler(method, url, data):
            host = url.split('/')[2]
            if host in down:
                return urllib.error.URLError('down')
            if url.endswith('/block-height/5'):
                return self.H.encode()
            if url.endswith('/block/' + self.H):
                return json.dumps({'id': ('cd' * 32) if bad_id else self.H, 'height': 5, 'merkle_root': roots[host],
                                   'timestamp': times[host]}).encode()
            return http_error(url, 404)
        return FakeOpener(handler)

    def test_agreeing_explorers(self):
        op = self.opener()
        root, ts = ots.EsploraHeaderSource(opener=op)(5)
        self.assertEqual((root, ts), (self.ROOT_A, 1))
        self.assertEqual(sorted(r['url'] for r in op.requests), sorted([
            'https://blockstream.info/api/block-height/5', 'https://blockstream.info/api/block/' + self.H,
            'https://mempool.space/api/block-height/5', 'https://mempool.space/api/block/' + self.H]))

    def test_disagreement_and_unavailable(self):
        with self.assertRaises(ots.HeaderError) as c:
            ots.EsploraHeaderSource(opener=self.opener({'blockstream.info': self.ROOT_A, 'mempool.space': self.ROOT_B}))(5)
        self.assertEqual(c.exception.code, 'explorer_disagreement')
        with self.assertRaises(ots.HeaderError) as c:
            ots.EsploraHeaderSource(opener=self.opener(time=(1, 2)))(5)
        self.assertEqual(c.exception.code, 'explorer_disagreement')
        with self.assertRaises(ots.HeaderError) as c:
            ots.EsploraHeaderSource(opener=self.opener(down=('mempool.space',)))(5)
        self.assertEqual(c.exception.code, 'explorer_unavailable')
        with self.assertRaises(ots.HeaderError) as c:
            ots.EsploraHeaderSource(opener=self.opener(bad_id=True))(5)
        self.assertEqual(c.exception.code, 'explorer_unavailable')

    def test_verify_with_default_source_class_disagreement(self):
        n = ots.Node(DIGEST)
        n.add_op(ots.OP_SHA256).add_attestation(ots.Attestation.bitcoin(5))
        raw = ots.DetachedTimestamp(DIGEST, n).serialize()
        msg = hashlib.sha256(DIGEST).digest()
        good, bad = display(msg), self.ROOT_B
        ok = ots.verify(raw, DIGEST, header_source=ots.EsploraHeaderSource(
            opener=self.opener({'blockstream.info': good, 'mempool.space': good})))
        self.assertEqual((ok['status'], ok['height']), ('confirmed', 5))
        res = ots.verify(raw, DIGEST, header_source=ots.EsploraHeaderSource(
            opener=self.opener({'blockstream.info': good, 'mempool.space': bad})))
        self.assertEqual((res['status'], res['code']), ('unverified', 'explorer_disagreement'))


class TestOfficialVector(unittest.TestCase):
    def source(self, root=OFFICIAL_MERKLE_ROOT_DISPLAY):
        return lambda h: (root, OFFICIAL_BLOCK_TIME) if h == OFFICIAL_HEIGHT else (_ for _ in ()).throw(AssertionError(h))

    def test_confirmed_against_real_block_data(self):
        res = ots.verify(OFFICIAL_OTS, hashlib.sha256(OFFICIAL_FILE).digest(), header_source=self.source())
        self.assertEqual(res['status'], 'confirmed', res)
        self.assertEqual(res['height'], OFFICIAL_HEIGHT)
        self.assertEqual(res['block_time'], '2015-05-28T15:41:18Z')

    def test_real_block_with_other_root_is_invalid(self):
        res = ots.verify(OFFICIAL_OTS, hashlib.sha256(OFFICIAL_FILE).digest(), header_source=self.source('00' * 32))
        self.assertEqual((res['status'], res['code']), ('invalid', 'merkle_root_mismatch'))

    def test_real_proof_with_other_content(self):
        res = ots.verify(OFFICIAL_OTS, hashlib.sha256(b'Hello World?\n').digest(), header_source=self.source())
        self.assertEqual((res['status'], res['code']), ('invalid', 'digest_mismatch'))

    def test_real_block_through_esplora_class_with_recorded_replies(self):
        def handler(method, url, data):
            if url.endswith('/block-height/%d' % OFFICIAL_HEIGHT):
                return OFFICIAL_BLOCK_HASH.encode()
            if url.endswith('/block/' + OFFICIAL_BLOCK_HASH):
                return json.dumps({'id': OFFICIAL_BLOCK_HASH, 'height': OFFICIAL_HEIGHT, 'timestamp': OFFICIAL_BLOCK_TIME,
                                   'merkle_root': OFFICIAL_MERKLE_ROOT_DISPLAY}).encode()
            return http_error(url, 404)
        res = ots.verify(OFFICIAL_OTS, hashlib.sha256(OFFICIAL_FILE).digest(),
                         header_source=ots.EsploraHeaderSource(opener=FakeOpener(handler)))
        self.assertEqual(res['status'], 'confirmed')

    def test_upgrade_of_complete_proof_is_a_noop(self):
        new, rep = ots.upgrade(OFFICIAL_OTS, opener=FakeOpener(lambda m, u, d: self.fail('no request expected')))
        self.assertEqual(new, OFFICIAL_OTS)
        self.assertFalse(rep['changed'])


class TestCli(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ots.main(list(args))
        return rc, out.getvalue(), err.getvalue()

    def test_info_and_errors(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'x.ots')
            with open(p, 'wb') as f:
                f.write(OFFICIAL_OTS)
            rc, out, _ = self.run_cli('info', p)
            self.assertEqual(rc, 0)
            self.assertIn('BitcoinBlockHeaderAttestation(358391)', out)
            bad = os.path.join(d, 'bad.ots')
            with open(bad, 'wb') as f:
                f.write(b'junk')
            rc, _, err = self.run_cli('info', bad)
            self.assertEqual(rc, 1)
            self.assertIn('error', err)

    def test_stamp_and_upgrade_cli_with_patched_network(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'chain-entry.json')
            with open(src, 'wb') as f:
                f.write(b'{"v":1}\n')
            out = os.path.join(d, 'e.ots')
            real_stamp = ots.stamp
            try:
                ots.stamp = lambda digest, **kw: real_stamp(digest, opener=FakeOpener(lambda m, u, dd: pending_reply(dd, ALICE)),
                                                            nonce=NONCE, **kw)
                rc, text, _ = self.run_cli('stamp', src, '-o', out)
                self.assertEqual(rc, 0)
                with open(out, 'rb') as f:
                    dt = ots.parse(f.read())
                self.assertEqual(dt.digest, hashlib.sha256(b'{"v":1}\n').digest())
                ots.stamp = lambda digest, **kw: real_stamp(digest, opener=FakeOpener(lambda m, u, dd: http_error(u, 500)), **kw)
                os.remove(out)
                rc, _, err = self.run_cli('stamp', src, '-o', out)
                self.assertEqual(rc, 2)
                self.assertFalse(os.path.exists(out))
            finally:
                ots.stamp = real_stamp


if __name__ == '__main__':
    unittest.main()
