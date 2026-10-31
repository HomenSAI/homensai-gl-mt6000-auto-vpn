"""The Lua monitor's peer address (lua/server_endpoint.lua) gives exactly what server_endpoint.observe gives on
the same router view: WireGuard `wg show <if> endpoints` variants (IPv4, IPv6, mapped, hostname, none, several
peers, refusals), OpenVPN /proc fixtures (owned socket, established TCP only, restarted process, foreign
descriptors) and interface epoch changes. Python reads a real file tree; Lua reads the same world as JSON."""
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'files/usr/lib/homensai-vpn'))
import server_endpoint as endpoint

LUA = shutil.which('lua5.1') or shutil.which('lua')
SUITE = HERE/'lua/test_server_endpoint.lua'

WG = {'id': 'wireguard:peer_1', 'protocol': 'wireguard', 'interface': 'wgclient1'}
OVPN = {'id': 'openvpn:1_1', 'protocol': 'openvpn', 'interface': 'ovpnclient1'}
STAT = '4242 (openvpn) S 1 4242 4242 0 -1 4194560 300 0 0 0 5 7 0 0 20 0 1 0 12345 5000000 900 4294967295'
HEADER = '  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n'


def sock(local, remote, state, inode):
    return '   1: %s %s %s 00000000:00000000 00:00000000 00000000     0        0 %s 2 00000000 0\n' % (local, remote, state, inode)


def wg_case(name, output, ifindex='7\n', profile=WG):
    return {'name': name, 'profile': profile, 'now': 1761830400.25,
            'world': {'files': {'/sys/class/net/wgclient1/ifindex': ifindex}, 'links': {}, 'wg': output}}


def ovpn_case(name, files=None, links=None, profile=OVPN):
    world = {'files': {'/sys/class/net/ovpnclient1/ifindex': '9\n', '/var/run/ovpnclient-ovpnclient1.pid': '4242\n',
                       '/proc/4242/comm': 'openvpn\n', '/proc/4242/stat': STAT,
                       '/proc/4242/cmdline': '/usr/sbin/openvpn\0--cd\0/etc/openvpn\0--dev\0ovpnclient1\0--config\0x.ovpn\0',
                       '/proc/4242/net/udp': HEADER+sock('0200A8C0:A1B2', '086433C6:04AA', '01', 55)+sock('00000000:0035', '00000000:0000', '07', 77)},
             'links': {'/proc/4242/fd/0': '/dev/null', '/proc/4242/fd/3': 'socket:[55]', '/proc/4242/fd/4': 'anon_inode:[eventfd]',
                       '/proc/4242/fd/5': '/dev/net/tun'},
             'wg': None}
    for key, value in (files or {}).items():
        if value is None:
            world['files'].pop(key, None)
        else:
            world['files'][key] = value
    world['links'].update(links or {})
    return {'name': name, 'profile': profile, 'now': 5, 'world': world}


def cases():
    rows = []
    for name, output in [
            ('ipv4', 'public-key-not-exported\t198.51.100.2:51820\n'), ('ipv6', 'k\t[2001:db8:0:0:0:0:0:1]:51820\n'),
            ('ipv6-upper', 'k\t[2001:DB8::A]:443\n'), ('ipv6-zero-runs', 'k\t[1:0:0:2:0:0:3:4]:9\n'), ('ipv6-tail', 'k\t[1:0:0:2:0:0:0:0]:9\n'),
            ('ipv6-head', 'k\t[0:0:0:2:0:0:3:4]:9\n'), ('ipv6-single-zero', 'k\t[1:0:2:3:4:5:6:7]:9\n'), ('ipv6-v4-tail', 'k\t[::1.2.3.4]:9\n'),
            ('mapped', 'k\t[::ffff:198.51.100.7]:51820\n'), ('mapped-loopback', 'k\t[::ffff:127.0.0.1]:51820\n'), ('scope', 'k\t[fe80::1%wg0]:51820\n'),
            ('hostname', 'k\tvpn.example.com:51820\n'), ('none', 'k\t(none)\n'), ('empty', ''), ('two-peers', 'a\t198.51.100.2:51820\nb\t198.51.100.3:51820\n'),
            ('same-peer-twice', 'a\t198.51.100.2:51820\nb\t198.51.100.2:51820\n'), ('three-fields', 'a\t198.51.100.2:51820\tx\n'),
            ('blank-line', 'a\t198.51.100.2:51820\n\n'), ('crlf', 'a\t198.51.100.2:51820\r\n'), ('loopback', 'a\t127.0.0.1:51820\n'),
            ('v6-loopback', 'a\t[::1]:51820\n'), ('unspecified', 'a\t0.0.0.0:51820\n'), ('multicast', 'a\t224.0.0.5:51820\n'),
            ('v6-multicast', 'a\t[ff02::1]:51820\n'), ('port-zero', 'a\t198.51.100.2:0\n'), ('port-high', 'a\t198.51.100.2:65536\n'),
            ('leading-zero', 'a\t198.051.100.2:51820\n'), ('unbracketed-v6', 'a\t2001:db8::1:51820\n'), ('non-ascii', 'a\t198.51.100.2:51820 é\n'),
            ('oversize', 'a\t198.51.100.2:51820\n'+'#'*4100), ('failed', None)]:
        rows.append(wg_case('wg-'+name, output))
    rows.append(wg_case('wg-ifindex-changed', 'a\t198.51.100.2:51820\n', ifindex=['7\n', '8\n']))
    missing = wg_case('wg-no-interface', 'a\t198.51.100.2:51820\n')
    missing['world']['files'] = {}
    rows.append(missing)
    for interface in ['wgclient1; reboot', 'eth0', '../../etc/shadow', 'wgclient10000', 'wgclient']:
        rows.append(wg_case('wg-bad-interface-'+interface, 'a\t198.51.100.2:51820\n', profile=dict(WG, interface=interface)))
    rows.append(wg_case('wg-id-protocol-mismatch', 'a\t198.51.100.2:51820\n', profile=dict(WG, id='openvpn:1_1')))
    rows.append(wg_case('wg-protocol-interface-mismatch', 'a\t198.51.100.2:51820\n', profile=dict(WG, interface='ovpnclient1')))

    rows.append(ovpn_case('ovpn-udp4'))
    rows.append(ovpn_case('ovpn-udp6', files={'/proc/4242/net/udp': None, '/proc/4242/net/udp6': HEADER+sock(
        '00000000000000000000000000000000:A1B2', 'B80D0120000000000000000001000000:CA6C', '01', 55)}))
    rows.append(ovpn_case('ovpn-udp6-mapped', files={'/proc/4242/net/udp': None, '/proc/4242/net/udp6': HEADER+sock(
        '00000000000000000000000000000000:A1B2', '0000000000000000FFFF0000086433C6:01BB', '01', 55)}))
    rows.append(ovpn_case('ovpn-tcp-established', files={'/proc/4242/net/udp': None, '/proc/4242/net/tcp': HEADER+sock(
        '0200A8C0:A1B2', '146433CB:01BB', '01', 55)}))
    rows.append(ovpn_case('ovpn-tcp-not-established', files={'/proc/4242/net/udp': None, '/proc/4242/net/tcp': HEADER+sock(
        '0200A8C0:A1B2', '146433CB:01BB', '02', 55)}))
    rows.append(ovpn_case('ovpn-unconnected-udp', files={'/proc/4242/net/udp': HEADER+sock('0200A8C0:A1B2', '00000000:0000', '07', 55)}))
    rows.append(ovpn_case('ovpn-two-connections', files={'/proc/4242/net/tcp': HEADER+sock('0200A8C0:A1B2', '146433CB:01BB', '01', 56)},
                          links={'/proc/4242/fd/6': 'socket:[56]'}))
    rows.append(ovpn_case('ovpn-foreign-socket', files={'/proc/4242/net/tcp': HEADER+sock('0200A8C0:A1B2', '146433CB:01BB', '01', 99)}))
    rows.append(ovpn_case('ovpn-restarted', files={'/proc/4242/stat': [STAT, STAT.replace('12345', '12399')]}))
    rows.append(ovpn_case('ovpn-cpu-counters-move', files={'/proc/4242/stat': [STAT, STAT.replace(' 5 7 ', ' 9 9 ')]}))
    rows.append(ovpn_case('ovpn-stat-truncated', files={'/proc/4242/stat': '4242 (openvpn) S 1'}))
    rows.append(ovpn_case('ovpn-comm', files={'/proc/4242/comm': 'sh\n'}))
    rows.append(ovpn_case('ovpn-dev-other', files={'/proc/4242/cmdline': 'openvpn\0--dev\0ovpnclient2\0'}))
    rows.append(ovpn_case('ovpn-dev-twice', files={'/proc/4242/cmdline': 'openvpn\0--dev\0ovpnclient1\0--dev\0ovpnclient1\0'}))
    rows.append(ovpn_case('ovpn-dev-last', files={'/proc/4242/cmdline': 'openvpn\0--dev\0'}))
    rows.append(ovpn_case('ovpn-cmdline-nuls', files={'/proc/4242/cmdline': '\0\0openvpn\0--dev\0ovpnclient1\0\0'}))
    rows.append(ovpn_case('ovpn-pid-1', files={'/var/run/ovpnclient-ovpnclient1.pid': '1\n'}))
    rows.append(ovpn_case('ovpn-pid-text', files={'/var/run/ovpnclient-ovpnclient1.pid': 'abc\n'}))
    rows.append(ovpn_case('ovpn-pid-missing', files={'/var/run/ovpnclient-ovpnclient1.pid': None}))
    rows.append(ovpn_case('ovpn-no-socket-tables', files={'/proc/4242/net/udp': None}))
    rows.append(ovpn_case('ovpn-ifindex-changed', files={'/sys/class/net/ovpnclient1/ifindex': ['9\n', '10\n']}))
    rows.append(ovpn_case('ovpn-256-descriptors', links={'/proc/4242/fd/%d' % i: '/dev/null' for i in range(6, 258)}))
    rows.append(ovpn_case('ovpn-257-descriptors', links={'/proc/4242/fd/%d' % i: '/dev/null' for i in range(6, 259)}))
    rows.append(ovpn_case('ovpn-oversize-table', files={'/proc/4242/net/tcp': HEADER+'x'*65600}))
    return rows


def run_python(case, directory):
    root = Path(directory)
    world = case['world']
    sequences = {path: value for path, value in world['files'].items() if isinstance(value, list)}
    for path, value in world['files'].items():
        target = root/path.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((value[0] if isinstance(value, list) else value).encode('utf-8'))
    for path, value in world['links'].items():
        target = root/path.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(value, str(target))
    original = endpoint._read
    counts = {}

    def read(path, limit):
        relative = '/'+str(Path(path).relative_to(root))
        if relative in sequences:
            counts[relative] = counts.get(relative, 0)+1
            data = sequences[relative][min(counts[relative], len(sequences[relative]))-1].encode('utf-8')
            if len(data) > limit:
                raise ValueError('ENDPOINT-READ-LIMIT')
            return data.decode('ascii')
        return original(path, limit)

    def runner(argv):
        if world['wg'] is None:
            raise subprocess.CalledProcessError(1, argv)
        return world['wg'].encode('utf-8')
    with mock.patch.object(endpoint, '_read', read):
        return endpoint.observe(case['profile'], case['now'], root, runner)


def lua_world(case):
    world = json.loads(json.dumps(case['world']))
    dirs = {}
    for path in sorted(world['links']):
        directory, name = path.rsplit('/', 1)
        dirs.setdefault(directory, []).append(name)
    world['dirs'] = dirs
    return dict(case, world=world)


def lua(mode, payload):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as stream:
        json.dump(payload, stream)
    try:
        result = subprocess.run([LUA, str(SUITE), mode, stream.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(HERE), timeout=120)
    finally:
        Path(stream.name).unlink()
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode(errors='replace'))
    return json.loads(result.stdout)


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
@unittest.skipUnless(hasattr(os, 'symlink') and os.name == 'posix', 'the Python side reads a real /proc-like tree with symlinks')
class LuaServerEndpoint(unittest.TestCase):
    def test_lua_suite(self):
        result = subprocess.run([LUA, str(SUITE)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(HERE), timeout=180)
        self.assertEqual(result.returncode, 0, (result.stdout+result.stderr).decode(errors='replace'))
        self.assertIn(b'tests OK', result.stdout)

    def test_observe_matches_python_on_the_same_fixtures(self):
        rows = cases()
        answers = lua('--observe', [lua_world(case) for case in rows])
        self.assertEqual(len(answers), len(rows))
        seen = set()
        for case, answer in zip(rows, answers):
            with self.subTest(case['name']), tempfile.TemporaryDirectory() as directory:
                expected = run_python(case, directory)
                self.assertEqual(answer, expected)
                seen.add(expected is not None)
        self.assertEqual(seen, {True, False}, 'fixtures cover found and refused peers')
        found = {case['name'] for case, answer in zip(rows, answers) if answer}
        self.assertTrue({'wg-ipv4', 'wg-ipv6', 'wg-mapped', 'ovpn-udp4', 'ovpn-udp6', 'ovpn-tcp-established', 'ovpn-cpu-counters-move'} <= found, found)
        self.assertGreaterEqual(len(rows), 60)

    def test_address_matches_python_ipaddress(self):
        if sys.version_info[:2] != (3, 9):
            self.skipTest('compared with the router runtime, Python 3.9 (IPv6 scope ids and formatting)')
        texts = ['198.51.100.8:1194', '[2001:db8::1]:51820', '(none)', 'host.example:443', 'user:secret@198.51.100.1:443',
                 '127.0.0.1:7505', '0.0.0.0:0', '198.51.100.1:65536', 'https://198.51.100.1:443', '[::1]:5', '[::]:5', '1.2.3.4:+5',
                 '1.2.3.4:0005', '1.2.3.4:5_0', '1.2.3.4:5__0', '1.2.3.4:_5', '1.2.3.4: 5', '[1.2.3.4]:5', '[]:5', '[:]:5', '[::]:',
                 '[fe80::1%]:5', '[fe80::1%a%b]:5', '[fe80::1%eth0]:5', '[::ffff:0.0.0.0]:5', '[::ffff:1.2.3]:5', '[1:2:3:4:5:6:1.2.3.4]:5',
                 '[1:2:3:4:5:6:7:1.2.3.4]:5', '[::1:2:3:4:5:6:7]:5', '[1:2:3:4:5:6:7::]:5', '[1::2:3:4:5:6:7:8]:5', '[:1::2]:5', '[1::2:]:5',
                 '[12345::1]:5', '[g::1]:5', '1.2.3.4:5]:6', '[1.2.3.4:5', '1.2.3.4/32:5', '[2001:db8::1/64]:5', 'a'*101, '1'*100]
        hextets = ['0', '1', 'ffff', 'ABCD', '00', '0000', '10']
        rng = random.Random(20261031)
        for _ in range(1500):
            parts = [rng.choice(hextets) for _ in range(rng.choice([7, 8, 8, 8, 9]))]
            text = ':'.join(parts)
            if rng.random() < .5:
                start = rng.randrange(len(parts))
                stop = rng.randrange(start, len(parts)+1)
                text = ':'.join(parts[:start])+'::'+':'.join(parts[stop:])
            texts.append('['+text+']:'+str(rng.choice([1, 443, 51820, 65535, 0, 70000])))
        for a, b, c, d in itertools.product((0, 1, 127, 128, 223, 224, 239, 240, 255), (0, 1), (0, 255), (0, 1)):
            texts.append('%d.%d.%d.%d:%d' % (a, b, c, d, 1194))
        answers = lua('--address', texts)
        self.assertEqual(len(answers), len(texts))
        for text, answer in zip(texts, answers):
            try:
                expected = list(endpoint.address(text))
            except ValueError:
                expected = None
            self.assertEqual(answer, expected, text)


if __name__ == '__main__':
    unittest.main()
