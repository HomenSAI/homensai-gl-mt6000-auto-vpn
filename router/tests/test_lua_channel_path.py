"""Plan item 4: channel_path.snapshot / pair_snapshot in Lua (lua/channel_path.lua) give exactly Python's answer on
the same inputs (differential over the cases of test_channel_path.py and their mutations), and the Lua suite for
public_status (the supervisor's own kernel proof instead of a display-path attestation) passes."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'files/usr/lib/homensai-vpn'))
from channel_path import snapshot, pair_snapshot  # noqa: E402
from pair_policy import proof, transition  # noqa: E402

LUA = shutil.which('lua5.1') or shutil.which('lua')
NOW = 10000


def legacy_cases():
    identity = {'id': 'wireguard:b', 'protocol': 'wireguard', 'interface': 'wgclient1',
                'vendor_tunnel_id': 'wireguard:wgclient1', 'vendor_generation': 'a'*32}
    status = {'time': NOW, 'native_failover': {'time': NOW},
              'profiles': [dict(identity, time=NOW, code=None, dns_ok=True, https_success=2)]}
    journal = {'phase': 'COMMITTED', 'source': 'openvpn:a', 'target': 'wireguard:b', 'before': ['r1', 'r2'],
               'after': ['r2', 'r1'], 'hash': 'h', 'confirmed': NOW-5, 'vendor_profiles': {'target': identity}}
    live = [['r2', 'r1'], 'h']
    cases = [(status, journal, live)]
    def variant(edit):
        s, j, l = copy.deepcopy(status), copy.deepcopy(journal), copy.deepcopy(live)
        edit(s, j, l)
        cases.append((s, j, l))
    variant(lambda s, j, l: l.__setitem__(0, ['r1', 'r2']))
    variant(lambda s, j, l: l.__setitem__(1, 'x'))
    variant(lambda s, j, l: s.__setitem__('time', NOW-1000))
    variant(lambda s, j, l: s['native_failover'].__setitem__('time', NOW-31))
    variant(lambda s, j, l: s['profiles'][0].__setitem__('time', NOW-91))
    variant(lambda s, j, l: s['profiles'][0].__setitem__('vendor_generation', 'g2'))
    variant(lambda s, j, l: s['profiles'][0].__setitem__('code', 'DNS-001'))
    variant(lambda s, j, l: j.__setitem__('vendor_profiles', []))
    variant(lambda s, j, l: j.pop('confirmed'))
    variant(lambda s, j, l: j.__setitem__('confirmed', NOW-20000))
    variant(lambda s, j, l: s.__setitem__('rpc_error', 'X'))
    variant(lambda s, j, l: s['native_failover'].__setitem__('tx', 't1'))
    variant(lambda s, j, l: j.update(source='wireguard:b'))
    variant(lambda s, j, l: j.update(phase='HELD-ON-RESERVE'))
    variant(lambda s, j, l: j.update(phase='STOPPED'))
    for phase in ('ARMED', 'APPLYING', 'WAIT-CLIENT', 'RESTORING'):
        variant(lambda s, j, l, phase=phase: (j.update(phase=phase), s['native_failover'].update(state=phase)))
        variant(lambda s, j, l, phase=phase: (j.update(phase=phase), s['native_failover'].update(state='STOPPED')))
    def rollback(s, j, l):
        j.update(phase='ROLLED-BACK', source='wireguard:b', target='openvpn:a')
        j['vendor_profiles']['source'] = j['vendor_profiles'].pop('target')
        l[0] = ['r1', 'r2']
    variant(rollback)
    return [{'kind': 'snapshot', 'status': s, 'journal': j, 'live': l, 'now': NOW} for s, j, l in cases] + \
           [{'kind': 'snapshot', 'status': status, 'journal': {}, 'live': None, 'now': NOW},
            {'kind': 'snapshot', 'status': {}, 'journal': journal, 'live': live, 'now': NOW}]


def pair_cases():
    selection = {'source_rule': 'r1', 'target_rule': 'r2', 'direction': 'first', 'order': ['r1', 'r2'],
                 'source': {'id': 'openvpn:1_1'}, 'target': {'id': 'wireguard:peer_2'}}
    state = {'phase': 'RUNNING', 'order': ['r1', 'r2'], 'policy_hash': 'h', 'policy_roles': proof(selection)}
    status = {'time': NOW, 'native_failover': {'time': NOW, 'state': 'OBSERVING', 'source': 'openvpn:1_1', 'target': 'wireguard:peer_2'}}
    kernel = {'verified': True, 'time': NOW-2, 'role': 'source', 'profile_id': 'openvpn:1_1', 'policy_hash': 'h', 'order': ['r1', 'r2']}
    switched = dict(phase='COMMITTED', source='openvpn:1_1', target='wireguard:peer_2', before=['r1', 'r2'], after=['r2', 'r1'], hash='h',
                    pair_transition=transition(selection, ['r1', 'r2'], 'target'))
    base = [(status, state, {}, [['r1', 'r2'], 'h'], kernel),
            (status, dict(state, order=['r1', 'r2']), switched,
             [['r2', 'r1'], 'h'], dict(kernel, role='target', profile_id='wireguard:peer_2', order=['r2', 'r1']))]
    cases = []
    for s0, st0, j0, l0, k0 in base:
        cases.append((s0, st0, j0, l0, k0))
        def variant(edit, s0=s0, st0=st0, j0=j0, l0=l0, k0=k0):
            s, st, j, l, k = (copy.deepcopy(x) for x in (s0, st0, j0, l0, k0))
            k = edit(s, st, j, l, k) or k
            cases.append((s, st, j, l, k))
        variant(lambda s, st, j, l, k: None if k.update(verified=False) else k)
        variant(lambda s, st, j, l, k: None if k.update(time=NOW-16) else k)
        variant(lambda s, st, j, l, k: None if k.update(role='target' if k['role'] == 'source' else 'source') else k)
        variant(lambda s, st, j, l, k: None if k.update(profile_id='openvpn:9_9') else k)
        variant(lambda s, st, j, l, k: None if k.update(policy_hash='x') else k)
        variant(lambda s, st, j, l, k: None if k.update(order=['x', 'y']) else k)
        variant(lambda s, st, j, l, k: {'none': True})
        variant(lambda s, st, j, l, k: st.update(phase='STOPPING'))
        variant(lambda s, st, j, l, k: st.pop('policy_roles'))
        variant(lambda s, st, j, l, k: st['policy_roles'].update(source_id='openvpn:7_7'))
        variant(lambda s, st, j, l, k: s.update(time=NOW-91))
        variant(lambda s, st, j, l, k: s.update(rpc_error='X'))
        variant(lambda s, st, j, l, k: s['native_failover'].update(time=NOW-31))
        variant(lambda s, st, j, l, k: s['native_failover'].update(state='APPLYING'))
        variant(lambda s, st, j, l, k: s['native_failover'].update(state='BLOCKED'))
        variant(lambda s, st, j, l, k: s['native_failover'].update(blockers=['X']))
        variant(lambda s, st, j, l, k: s['native_failover'].update(target='openvpn:1_1'))
        variant(lambda s, st, j, l, k: s['native_failover'].update(source=''))
        variant(lambda s, st, j, l, k: l.__setitem__(1, 'other'))
        variant(lambda s, st, j, l, k: l.__setitem__(0, list(reversed(l[0]))))
    out = []
    for s, st, j, l, k in cases:
        kernel = None if isinstance(k, dict) and k.get('none') else k
        out.append({'kind': 'pair', 'status': s, 'state': st, 'journal': j, 'live': l, 'now': NOW, 'kernel': kernel})
    return out


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaChannelPath(unittest.TestCase):
    def test_lua_suite(self):
        result = subprocess.run([LUA, str(HERE/'lua/test_channel_path.lua')], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        self.assertEqual(result.returncode, 0, (result.stdout+result.stderr).decode(errors='replace'))
        self.assertIn(b'tests OK', result.stdout)

    def test_differential_with_python(self):
        cases = legacy_cases()+pair_cases()
        result = subprocess.run([LUA, str(HERE/'lua/test_channel_path.lua'), '--cases'], input=json.dumps(cases).encode(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        answers = json.loads(result.stdout)
        self.assertEqual(len(answers), len(cases))
        greens = 0
        for index, (case, lua) in enumerate(zip(cases, answers)):
            live = tuple(case['live']) if case['live'] is not None else None
            if case['kind'] == 'snapshot':
                expected = snapshot(copy.deepcopy(case['status']), copy.deepcopy(case['journal']), live, NOW)
            else:
                expected = pair_snapshot(copy.deepcopy(case['status']), copy.deepcopy(case['state']), copy.deepcopy(case['journal']),
                                         live, NOW, kernel=copy.deepcopy(case['kernel']))
            greens += bool(expected.get('confirmed'))
            self.assertEqual(lua, expected, 'case %d: %s' % (index, json.dumps(case)[:400]))
        self.assertGreaterEqual(greens, 4, 'the differential covers confirmed answers too')


if __name__ == '__main__':
    unittest.main()
