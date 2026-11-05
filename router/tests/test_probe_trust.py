"""Probe authenticity (probe_trust.py / lua/probe_trust.lua, docs/architecture/PROBE-AUTHENTICITY-2026-11-03.ru.md).

- the shared cases of probe_trust_cases.json in Python (Lua: lua/test_probe_trust.lua, run here and by the suite);
- the pinned anchor files: certificates only, SPKI sha256 equal to pins.json, current + backup roots per host,
  enough validity left (this test fails a year before a host would run out of anchors: rotate then);
- real TLS through agent.https_probe and native_switch.trace against a local server (no network): a certificate
  outside the host's anchors is untrusted even when the system store would accept it, a 302 is a portal
  redirect, a trace that does not echo the request nonce is stale; the pinned CA accepts the same server.
"""
from pathlib import Path
from unittest import mock
import base64
import datetime
import hashlib
import json
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
import probe_trust  # noqa: E402

CASES = json.loads((HERE/'probe_trust_cases.json').read_text(encoding='utf-8'))
LUA = shutil.which('lua5.1') or shutil.which('lua')
OPENSSL = shutil.which('openssl')
ANCHORS = LIB/'probe-anchors'
HOSTS = ('one.one.one.one', 'dns.google', 'dns.quad9.net')


def der_items(data, start, end):
    items = []
    while start < end:
        tag, length, offset = data[start], data[start+1], start+2
        if length & 0x80:
            count = length & 0x7f
            length = int.from_bytes(data[offset:offset+count], 'big')
            offset += count
        items.append((tag, offset, offset+length, start))
        start = offset+length
    return items


def spki_and_expiry(der):
    """An independent DER walk (not the build script): SPKI sha256 base64 and notAfter."""
    certificate = der_items(der, 0, len(der))[0]
    tbs = der_items(der, certificate[1], certificate[2])[0]
    fields = der_items(der, tbs[1], tbs[2])
    if fields[0][0] == 0xa0:
        fields = fields[1:]
    validity, spki = fields[3], fields[5]
    after = der_items(der, validity[1], validity[2])[1]
    text = der[after[1]:after[2]].decode('ascii')
    if after[0] == 0x17:
        text = ('19' if int(text[:2]) >= 50 else '20')+text
    return (base64.b64encode(hashlib.sha256(der[spki[3]:spki[2]]).digest()).decode(),
            datetime.date(int(text[:4]), int(text[4:6]), int(text[6:8])))


def pem_blocks(text):
    out = []
    for part in text.split('-----BEGIN CERTIFICATE-----')[1:]:
        out.append(base64.b64decode(''.join(part.split('-----END CERTIFICATE-----')[0].split())))
    return out


class SharedCases(unittest.TestCase):
    def test_fresh(self):
        self.assertGreaterEqual(len(CASES['fresh']), 25)
        for case in CASES['fresh']:
            with self.subTest(case['name']):
                got = probe_trust.fresh(case['body'].encode('latin-1'), case['agent'], case['wall'][0], case['wall'][1], case['elapsed'])
                self.assertEqual(got, case['expect'])
                self.assertEqual(probe_trust.fresh(case['body'], case['agent'], case['wall'][0], case['wall'][1], case['elapsed']), got)

    def test_dns_mode_redirect_anchor_file(self):
        for case in CASES['dns_mode']:
            self.assertEqual(probe_trust.dns_mode(case['text']), case['expect'], case['text'])
        for status, expected in CASES['redirect']:
            self.assertEqual(probe_trust.redirect(status), expected, status)
        for host, expected in CASES['anchor_file']:
            path = probe_trust.anchor_file(host)
            self.assertEqual(path is not None, expected, host)
            if path:
                self.assertEqual(Path(path), ANCHORS/(host+'.pem'))
        with mock.patch.object(probe_trust, 'ANCHORS', Path('/nonexistent')):
            self.assertIsNone(probe_trust.anchor_file('one.one.one.one'))

    def test_agent_and_untrusted(self):
        self.assertEqual(probe_trust.agent(b'\xab'*16), 'HomenSAI-probe/'+'ab'*16)
        a, b = probe_trust.agent(), probe_trust.agent()
        self.assertNotEqual(a, b)
        self.assertRegex(a, r'^HomenSAI-probe/[0-9a-f]{32}$')
        self.assertTrue(probe_trust.untrusted([{'result': 'tls-error', 'trust': 'untrusted-certificate'}]))
        self.assertFalse(probe_trust.untrusted([{'result': 'tls-error'}, {'trust': 'other'}, None]))

    def test_current_dns_mode_follows_the_file(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'homensai_vpn'
            with mock.patch.object(probe_trust, 'CONFIG', config), mock.patch.dict(probe_trust._MODE, {'key': None, 'value': 'udp'}):
                self.assertEqual(probe_trust.current_dns_mode(), 'udp', 'no file')
                config.write_text("config main 'main'\n\toption probe_dns 'doh'\n")
                self.assertEqual(probe_trust.current_dns_mode(), 'doh')
                config.unlink()
                config.write_text("config main 'main'\n\toption probe_dns 'udp'\n")
                self.assertEqual(probe_trust.current_dns_mode(), 'udp', 'a rewritten file (new inode) is read again')

    def test_python_sanitizer_keeps_the_reason(self):
        import vendor_observation
        clean = vendor_observation.probe_checks([{'target': 'dns.google', 'result': 'tls-error', 'trust': 'untrusted-certificate'},
                                                 {'target': 'dns.quad9.net', 'result': 'ok', 'trust': 'portal-redirect'},
                                                 {'target': 'one.one.one.one', 'result': 'timeout', 'trust': 'other'}])
        self.assertEqual([row.get('trust') for row in clean], ['untrusted-certificate', None, None])
        self.assertIn('probe_trust', vendor_observation.MEASUREMENT_FIELDS)
        self.assertIn('probe_trust', vendor_observation.HEALTH)

    @unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
    def test_lua_twin(self):
        result = subprocess.run([LUA, str(HERE/'lua/test_probe_trust.lua')], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(HERE), timeout=120)
        self.assertEqual(result.returncode, 0, (result.stdout+result.stderr).decode(errors='replace'))
        self.assertIn(b'tests OK', result.stdout)


class AnchorFiles(unittest.TestCase):
    def test_pins_match_the_certificates(self):
        pins = json.loads((ANCHORS/'pins.json').read_text(encoding='ascii'))
        self.assertEqual(sorted(pins['hosts']), sorted(HOSTS))
        self.assertEqual(sorted(p.name for p in ANCHORS.iterdir()), sorted([h+'.pem' for h in HOSTS]+['pins.json']))
        for host in HOSTS:
            with self.subTest(host):
                text = (ANCHORS/(host+'.pem')).read_text(encoding='ascii')
                self.assertNotIn('PRIVATE', text)
                self.assertEqual(text.count('-----BEGIN'), text.count('-----BEGIN CERTIFICATE-----'))
                facts = [spki_and_expiry(der) for der in pem_blocks(text)]
                rows = pins['hosts'][host]
                self.assertEqual([f[0] for f in facts], [r['spki_sha256'] for r in rows])
                self.assertEqual([f[1].isoformat() for f in facts], [r['not_after'] for r in rows])
                self.assertEqual(len(set(r['spki_sha256'] for r in rows)), len(rows), 'no duplicate anchor')
                roles = [r['role'] for r in rows]
                self.assertEqual(roles.count('current'), 1)
                self.assertGreaterEqual(roles.count('backup'), 3)

    def test_rotation_deadline(self):
        """Fails a year before any probe host would have fewer than two valid anchors: rotate the pins then."""
        pins = json.loads((ANCHORS/'pins.json').read_text(encoding='ascii'))
        horizon = (datetime.date.today()+datetime.timedelta(days=365)).isoformat()
        for host, rows in pins['hosts'].items():
            valid = [r for r in rows if r['not_after'] > horizon]
            self.assertGreaterEqual(len(valid), 2, '%s: rotate the probe anchors (scripts/build_probe_anchors.py)' % host)
            current = [r for r in rows if r['role'] == 'current'][0]
            self.assertGreater(current['not_after'], horizon, '%s: the current anchor expires within a year' % host)


# ---------------------------------------------------------------------------------------------------------------
# real TLS against a local server
# ---------------------------------------------------------------------------------------------------------------
def openssl(*args, cwd):
    subprocess.run([OPENSSL]+list(args), cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_pki(folder):
    """A private CA and a leaf for one.one.one.one signed by it, plus a self-signed 'portal' leaf for the same name."""
    ext = Path(folder)/'leaf.ext'
    ext.write_text('subjectAltName=DNS:one.one.one.one,DNS:dns.google\nbasicConstraints=CA:FALSE\n')
    openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1', '-nodes', '-keyout', 'ca.key',
            '-out', 'ca.pem', '-days', '2', '-subj', '/CN=Test Probe Root', cwd=folder)
    openssl('req', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1', '-nodes', '-keyout', 'leaf.key', '-out', 'leaf.csr',
            '-subj', '/CN=one.one.one.one', cwd=folder)
    openssl('x509', '-req', '-in', 'leaf.csr', '-CA', 'ca.pem', '-CAkey', 'ca.key', '-CAcreateserial', '-out', 'leaf.pem',
            '-days', '2', '-extfile', 'leaf.ext', cwd=folder)
    openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1', '-nodes', '-keyout', 'portal.key',
            '-out', 'portal.pem', '-days', '2', '-subj', '/CN=one.one.one.one', '-addext', 'subjectAltName=DNS:one.one.one.one', cwd=folder)


class Server:
    """One TLS listener on 127.0.0.1; reply(request_bytes) -> raw HTTP response."""
    def __init__(self, cert, key, reply):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(cert, key)
        self.reply = reply
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self.requests = []
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            try:
                raw, _ = self.sock.accept()
            except OSError:
                return
            try:
                with self.context.wrap_socket(raw, server_side=True) as conn:
                    data = b''
                    while b'\r\n\r\n' not in data:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    self.requests.append(data)
                    conn.sendall(self.reply(data))
            except (OSError, ssl.SSLError):
                raw.close()

    def close(self):
        self.sock.close()


def loopback(server):
    """agent.bound_socket stand-in: a TCP socket whose connect() goes to the local server whatever the address."""
    class Socket(socket.socket):
        def connect(self, address):
            return super().connect(('127.0.0.1', server.port))

    def bound(device, mark, udp=False):
        sock = Socket()
        sock.settimeout(3)
        return sock
    return bound


def http(status, body, extra=''):
    return ('HTTP/1.1 %d X\r\n%sContent-Length: %d\r\nConnection: close\r\n\r\n' % (status, extra, len(body))).encode()+body


def echo_trace(request):
    agent = [line[12:] for line in request.decode().split('\r\n') if line.startswith('User-Agent: ')][0]
    return http(200, ('fl=1\nh=one.one.one.one\nip=93.184.216.34\nts=1\nvisit_scheme=https\nuag=%s\nhttp=http/1.1\nloc=DE\n' % agent).encode())


@unittest.skipUnless(OPENSSL, 'openssl(1) absent')
class RealTls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.mkdtemp()
        make_pki(cls.folder)
        cls.pinned = Path(cls.folder)/'anchors'
        cls.pinned.mkdir()
        shutil.copy(Path(cls.folder)/'ca.pem', cls.pinned/'one.one.one.one.pem')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)

    def run_probe(self, cert, reply, anchors):
        import agent
        folder = Path(self.folder)
        server = Server(str(folder/(cert+'.pem')), str(folder/(cert+'.key')), reply)

        bound = loopback(server)
        sink, checks = {}, {}
        try:
            with mock.patch.object(agent, 'bound_socket', bound), mock.patch.object(probe_trust, 'ANCHORS', anchors):
                try:
                    value = agent.https_for_probe('wgclient1', 4096, ('127.0.0.1', 'one.one.one.one', '/cdn-cgi/trace', 'trace'), sink, checks, 3)
                except ssl.SSLCertVerificationError:
                    value = 'untrusted'
        finally:
            server.close()
        return value, checks['one.one.one.one'], sink, server.requests

    def test_pinned_ca_accepts_and_the_nonce_is_echoed(self):
        value, detail, sink, requests = self.run_probe('leaf', echo_trace, self.pinned)
        self.assertIsInstance(value, float)
        self.assertEqual(sink.get('wgclient1'), '93.184.216.34')
        self.assertRegex(requests[0].decode(), r'\r\nUser-Agent: HomenSAI-probe/[0-9a-f]{32}\r\n')
        self.assertNotIn('trust', detail)

    def test_the_real_anchors_refuse_a_certificate_of_another_ca(self):
        # the shipped one.one.one.one roots do not include the test CA: untrusted although the chain is complete
        value, _, _, _ = self.run_probe('leaf', echo_trace, ANCHORS)
        self.assertEqual(value, 'untrusted')

    def test_a_self_signed_portal_is_untrusted(self):
        value, _, _, requests = self.run_probe('portal', echo_trace, self.pinned)
        self.assertEqual(value, 'untrusted')
        self.assertEqual(requests, [], 'nothing is sent to an untrusted peer')

    def test_redirect_and_replayed_trace(self):
        value, detail, _, _ = self.run_probe('leaf', lambda r: http(302, b'', 'Location: http://portal.example/\r\n'), self.pinned)
        self.assertIsNone(value)
        self.assertEqual((detail['result'], detail['trust'], detail['http_status']), ('http-error', 'portal-redirect', 302))
        replay = http(200, b'fl=1\nip=93.184.216.34\nts=1\nuag=HomenSAI-probe/'+b'0'*32+b'\nhttp=http/1.1\n')
        value, detail, sink, _ = self.run_probe('leaf', lambda r: replay, self.pinned)
        self.assertIsNone(value)
        self.assertEqual((detail['result'], detail['trust']), ('invalid-response', 'stale-response'))
        self.assertEqual(sink, {}, 'no exit address from a replayed page')

    def test_https_for_probe_marks_the_untrusted_certificate(self):
        import agent
        folder = Path(self.folder)
        server = Server(str(folder/'portal.pem'), str(folder/'portal.key'), echo_trace)

        bound = loopback(server)
        checks = {}
        try:
            with mock.patch.object(agent, 'bound_socket', bound), mock.patch.object(probe_trust, 'ANCHORS', self.pinned):
                with self.assertRaises(ssl.SSLCertVerificationError):
                    agent.https_for_probe('wgclient1', 4096, ('127.0.0.1', 'one.one.one.one', '/cdn-cgi/trace', 'trace'), {}, checks, 3)
        finally:
            server.close()
        self.assertEqual((checks['one.one.one.one']['result'], checks['one.one.one.one']['trust']), ('tls-error', 'untrusted-certificate'))

    def test_native_switch_trace_requires_the_nonce(self):
        import native_switch
        folder = Path(self.folder)
        for reply, expected in ((echo_trace, '93.184.216.34'),
                                (lambda r: http(200, b'ip=93.184.216.34\nhttp=x\nuag=curl/7.83.1\n'), 'EXIT-TRACE-FAILED')):
            server = Server(str(folder/'leaf.pem'), str(folder/'leaf.key'), reply)

            bound = loopback(server)
            passing = {'code': None, 'dns_ok': True, 'https_success': 3, 'device': 'wgclient1', 'mark': 4096}
            try:
                with mock.patch.object(native_switch, 'bound_socket', bound), mock.patch.object(native_switch, 'probe', return_value=passing), \
                        mock.patch.object(probe_trust, 'ANCHORS', self.pinned):
                    try:
                        got = native_switch.trace({'id': 'wireguard:peer_1', 'interface': 'wgclient1'})
                    except native_switch.Refused as refused:
                        got = refused.args[0] if refused.args else str(refused)
            finally:
                server.close()
            self.assertEqual(got, expected)


if __name__ == '__main__':
    unittest.main()
