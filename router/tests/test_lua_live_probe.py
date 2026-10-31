"""Plan item 4: the Lua Auto supervisor's native live probe (lua/live_probe.lua) gives the fields and codes that
lua_bridge.py gives for the same channel answers: agent.probe() through `probe`, native_switch.trace() through
`trace`. Python runs its real probe code over fake sockets (route binding, UDP DNS, TCP+TLS+HTTP); Lua runs the
same scenario through tests/lua/test_live_probe.lua --scenario. Times are compared only as present/absent."""
from pathlib import Path
from unittest import mock
import base64
import contextlib
import copy
import io
import json
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
LUA = shutil.which('lua5.1') or shutil.which('lua')
SUITE = HERE/'lua/test_live_probe.lua'

ADDRESS = {'1.1.1.1': 'one.one.one.one', '8.8.8.8': 'dns.google', '9.9.9.9': 'dns.quad9.net'}
TRACE = 'fl=1\nh=one.one.one.one\nip=93.184.216.34\nts=1761830400.1\nvisit_scheme=https\nuag=curl\ncolo=FRA\nhttp=http/1.1\nloc=DE\n'
DNS_JSON = '{"Status":0,"Answer":[{"name":"example.com.","type":1,"TTL":60,"data":"93.184.216.34"}]}'
BINDING = {'code': None, 'device': 'wgclient1', 'mark': 4096, 'table': '1001', 'ifindex': 12}
PROFILE = {'id': 'wireguard:peer_2002', 'interface': 'wgclient1', 'administrative_state': 'enabled', 'protocol': 'wireguard'}


def dns_answer(packet, mode='ok'):
    token, question = packet[:2], packet[12:]
    flags, answers = 0x8180, 1
    if mode == 'bad-rcode':
        flags = 0x8182
    if mode == 'no-answer':
        answers = 0
    if mode == 'wrong-question':
        question = b'\x07example\x03org\x00' + struct.pack('!HH', 1, 1)
    return (token + struct.pack('!HHHHH', flags, 1, answers, 0, 0) + question + b'\xc0\x0c' + struct.pack('!HHIH', 1, 1, 60, 4)
            + bytes([93, 184, 216, 34]))


def http(status, body):
    return ('HTTP/1.1 %d X\r\nContent-Length: %d\r\nConnection: close\r\n\r\n' % (status, len(body))).encode() + body


class World:
    def __init__(self, scenario):
        self.scenario = scenario
        self.queues = {host: list(rows) for host, rows in scenario['https'].items()}
        self.bindings = list(scenario.get('bindings', [BINDING]))
        self.lock = threading.Lock()

    def next(self, host):
        with self.lock:
            rows = self.queues.get(host) or [{'kind': 'transport'}]
            return rows.pop(0) if len(rows) > 1 else rows[0]

    def route_binding(self, logical):
        with self.lock:
            row = self.bindings.pop(0) if len(self.bindings) > 1 else self.bindings[0]
        if 'error' in row:
            raise OSError('fake command failure')
        return dict(row)

    def bound_socket(self, device, mark, udp=False):
        return FakeSocket(self, udp)


class FakeSocket:
    def __init__(self, world, udp):
        self.world, self.udp, self.spec, self.packet = world, udp, None, None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def settimeout(self, _):
        pass

    def close(self):
        pass

    def connect(self, address):
        if self.udp:
            return
        self.spec = self.world.next(ADDRESS[address[0]])
        if self.spec['kind'] == 'timeout':
            raise socket.timeout('fake timeout')
        if self.spec['kind'] == 'transport':
            raise ConnectionRefusedError('fake refused')

    def send(self, packet):
        self.packet = packet
        return len(packet)

    def recv(self, _):
        mode = self.world.scenario.get('dns', 'ok')
        if mode == 'timeout':
            raise socket.timeout('fake dns timeout')
        if mode == 'refused':
            raise ConnectionRefusedError('fake dns refused')
        return dns_answer(self.packet, mode)


class FakeContext:
    def wrap_socket(self, raw, server_hostname=None):
        if raw.spec['kind'] == 'tls':
            raise ssl.SSLError('fake tls')
        return FakeTLS(raw.spec)


class FakeTLS:
    def __init__(self, spec):
        self.spec, self.data = spec, b''

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def settimeout(self, _):
        pass

    def sendall(self, request):
        path = request.split(b' ')[1].decode()
        if self.spec['kind'] == 'oversize':
            self.data = http(200, b'x'*40000)
            return
        body = self.spec['body']
        if body in ('@DNSWIRE', '@DNSWIRE-BAD'):
            wire = re.search(r'\?dns=(.*)$', path).group(1)
            packet = base64.urlsafe_b64decode(wire + '='*(-len(wire) % 4))
            self.data = http(self.spec['status'], dns_answer(packet, 'ok' if body == '@DNSWIRE' else 'bad-rcode'))
        else:
            self.data = http(self.spec['status'], body.encode())

    def recv_into(self, buffer):
        count = min(len(buffer), len(self.data))
        buffer[:count] = self.data[:count]
        self.data = self.data[count:]
        return count


def python_bridge(action, scenario):
    """lua_bridge.main itself (the contract the Lua supervisor read) over the fake world."""
    import agent
    import lua_bridge
    import native_switch
    world = World(scenario)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'request.json'
        path.write_text(json.dumps(scenario['profile']))
        output = io.StringIO()
        with mock.patch.object(lua_bridge, 'RUNTIME_FILE', re.compile(r'.*')), \
                mock.patch.object(agent, 'route_binding', world.route_binding), \
                mock.patch.object(agent, 'bound_socket', world.bound_socket), \
                mock.patch.object(native_switch, 'bound_socket', world.bound_socket), \
                mock.patch('ssl.create_default_context', lambda: FakeContext()), \
                mock.patch('server_endpoint.observe', lambda *_: None), \
                contextlib.redirect_stdout(output):
            lua_bridge.main(['lua_bridge.py', action, str(path)])
    return json.loads(output.getvalue().strip().splitlines()[-1])


def lua_scenario(scenario):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as stream:
        json.dump(scenario, stream)
    try:
        result = subprocess.run([LUA, str(SUITE), '--scenario', stream.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=str(HERE), timeout=60)
    finally:
        Path(stream.name).unlink()
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode(errors='replace'))
    return json.loads(result.stdout)


def comparable(result):
    result = copy.deepcopy(result)
    result.pop('time', None)
    if 'rtt_ms' in result:
        result['rtt_ms'] = result['rtt_ms'] is not None
    for check in result.get('probe_checks', []):
        check['elapsed_ms'] = isinstance(check.get('elapsed_ms'), float)
    return result


def ok_https():
    return {'one.one.one.one': [{'kind': 'http', 'status': 200, 'body': TRACE}],
            'dns.google': [{'kind': 'http', 'status': 200, 'body': DNS_JSON}],
            'dns.quad9.net': [{'kind': 'http', 'status': 200, 'body': '@DNSWIRE'}]}


def scenarios():
    def make(name, https=None, **extra):
        row = {'name': name, 'profile': dict(PROFILE), 'https': https or ok_https()}
        row.update(extra)
        return row
    rows = [make('pass')]
    for kind in ('timeout', 'tls', 'transport', 'oversize'):
        https = ok_https()
        https['one.one.one.one'] = [{'kind': kind}]
        rows.append(make('trace-' + kind, https))
        https = ok_https()
        https['dns.google'] = [{'kind': kind}]
        https['dns.quad9.net'] = [{'kind': kind}]
        rows.append(make('vpn003-' + kind, https))
    for status in (426, 505, 503, 404):
        https = ok_https()
        https['dns.google'] = [{'kind': 'http', 'status': status, 'body': 'x'}]
        rows.append(make('status-%d' % status, https))
    https = ok_https()
    https['one.one.one.one'] = [{'kind': 'http', 'status': 503, 'body': 'x'}, {'kind': 'http', 'status': 200, 'body': TRACE}]
    rows.append(make('trace-fetch-after-probe-503', https))
    https = ok_https()
    https['one.one.one.one'] = [{'kind': 'http', 'status': 200, 'body': 'ip=93.184.216.34\nloc=DE\n'}]
    rows.append(make('trace-body-without-http-line', https))
    for body in ('ip=10.1.2.3\nhttp=http/1.1\n', 'ip=100.64.1.1\nhttp=x\n', 'ip=93.184.216.034\nhttp=x\n',
                 'h=x\nip= 93.184.216.34 \r\nhttp=x\n', 'ip=10.0.0.1\nip=93.184.216.34\nhttp=x\n',
                 'ip=93.184.216.34\nhttp=x\nip=10.0.0.1\n', 'ip=224.0.0.9\nhttp=x\n'):
        https = ok_https()
        https['one.one.one.one'] = [{'kind': 'http', 'status': 200, 'body': body}]
        rows.append(make('trace-body ' + repr(body), https))
    https = ok_https()
    https['dns.google'] = [{'kind': 'http', 'status': 200, 'body': '{"Status":2,"Answer":[]}'}]
    https['dns.quad9.net'] = [{'kind': 'http', 'status': 200, 'body': '@DNSWIRE-BAD'}]
    rows.append(make('invalid-dns-bodies', https))
    for mode in ('timeout', 'refused', 'bad-rcode', 'no-answer', 'wrong-question'):
        rows.append(make('dns-' + mode, dns=mode))
    for after in ({'code': None, 'device': 'wgclient1', 'mark': 8192, 'table': '1001', 'ifindex': 12},
                  {'code': None, 'device': 'wgclient1', 'mark': 4096, 'table': '1001', 'ifindex': 13}, {'code': 'VPN-001'}):
        rows.append(make('epoch-change %s' % after, bindings=[BINDING, after]))
    for code in ('VPN-001', 'ROUTE-001', 'CHECK-001'):
        rows.append(make('route ' + code, bindings=[{'code': code, 'device': 'wgclient1'} if code != 'VPN-001' else {'code': code}]))
    rows.append(make('binding-failure', bindings=[{'error': 'x'}]))
    rows.append(make('after-binding-failure', bindings=[BINDING, {'error': 'x'}]))
    rows.append(make('inactive', profile=dict(PROFILE, interface=None)))
    rows.append(make('disabled', profile=dict(PROFILE, administrative_state='disabled')))
    profile = dict(PROFILE)
    del profile['administrative_state']
    rows.append(make('no-state', profile=profile))
    rows.append(make('null-state', profile=dict(PROFILE, administrative_state=None)))
    return rows


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaLiveProbe(unittest.TestCase):
    def test_lua_suite(self):
        result = subprocess.run([LUA, str(SUITE)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(HERE), timeout=180)
        self.assertEqual(result.returncode, 0, (result.stdout+result.stderr).decode(errors='replace'))
        self.assertIn(b'tests OK', result.stdout)

    def test_probe_and_trace_match_the_python_bridge(self):
        rows = scenarios()
        for scenario in rows:
            with self.subTest(scenario['name']):
                lua = lua_scenario(scenario)
                self.assertEqual(comparable(lua['probe']), comparable(python_bridge('probe', scenario)))
                self.assertEqual(lua['trace'], python_bridge('trace', scenario))
        self.assertGreaterEqual(len(rows), 40)

    def test_ipv4_rules_match_python_ipaddress(self):
        import ipaddress
        if sys.version_info[:2] != (3, 9):
            # The router runs Python 3.9; ipaddress.is_global changed for 192.0.0.0/24 in later versions.
            self.skipTest('is_global is compared with the router runtime, Python 3.9')
        texts = ['93.184.216.34', '1.1.1.1', '0.0.0.0', '10.0.0.1', '100.63.255.255', '100.64.0.0', '100.127.255.255',
                 '100.128.0.0', '127.0.0.1', '169.254.1.1', '172.15.255.255', '172.16.0.0', '172.31.255.255', '172.32.0.0',
                 '192.0.0.0', '192.0.0.7', '192.0.0.8', '192.0.0.9', '192.0.0.170', '192.0.0.171', '192.0.0.172', '192.0.2.1',
                 '192.88.99.1', '192.168.1.1', '198.17.255.255', '198.18.0.0', '198.19.255.255', '198.20.0.0', '198.51.100.7',
                 '203.0.113.9', '224.0.0.1', '239.255.255.255', '240.0.0.1', '255.255.255.255', '01.2.3.4', '1.2.3', '1.2.3.4.5',
                 '256.1.1.1', '1..2.3', '', ' 1.2.3.4', '1.2.3.4 ', '+1.2.3.4', '1.2.3.0x4', '1.2.3.1234', '١.2.3.4']
        texts += ['%d.%d.%d.%d' % (a, b, c, d) for a in (0, 9, 10, 11, 100, 126, 127, 128, 169, 172, 191, 192, 198, 203, 223, 224, 240, 255)
                  for b in (0, 15, 16, 31, 32, 51, 63, 64, 88, 127, 128, 168, 254, 255) for c in (0, 2, 99, 100, 113) for d in (0, 7, 8, 170, 171, 255)]
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as stream:
            json.dump(texts, stream)
        try:
            result = subprocess.run([LUA, str(SUITE), '--ipv4', stream.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(HERE), timeout=60)
        finally:
            Path(stream.name).unlink()
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        lua = json.loads(result.stdout)
        for text, (parsed, global_) in zip(texts, lua):
            try:
                address = ipaddress.IPv4Address(text)
                expected = [True, address.is_global]
            except ValueError:
                expected = [False, False]
            self.assertEqual([parsed, global_], expected, text)
        self.assertEqual(len(lua), len(texts))


if __name__ == '__main__':
    unittest.main()
