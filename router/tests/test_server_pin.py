"""Trust on first use of VPN server keys (server_pin.py): the shared cases of server_pin_cases.json (the same as
lua/test_server_pin.lua), the real file writes in a temp directory, the administrator command, the Auto gate."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
import server_pin as sp  # noqa: E402

RAW = json.loads((HERE/'server_pin_cases.json').read_text(encoding='utf8'))


def expand(value):
    if isinstance(value, str):
        for name, pem in RAW['certs'].items():
            value = value.replace(name, pem)
        return value
    if isinstance(value, list):
        return [expand(v) for v in value]
    if isinstance(value, dict):
        return {k: expand(v) for k, v in value.items()}
    return value


CASES = expand({k: v for k, v in RAW.items() if k != 'certs'})


class Fake:
    def __init__(self, files=None, run=None):
        self.files = dict(files or {})
        self.answers = dict(run or {})
        self.flash, self.ram, self.calls = [], [], []

    def read(self, path, limit=10**9):
        text = self.files.get(path)
        return None if text is None or len(text) > limit else text

    def run(self, argv):
        self.calls.append(' '.join(argv))
        value = self.answers.get(' '.join(argv))
        if isinstance(value, list):  # successive answers; the last one repeats
            return value.pop(0) if len(value) > 1 else value[0]
        return value

    def write_ram(self, path, text):
        self.ram.append(path)
        self.files[path] = text

    def write_flash(self, path, text):
        self.flash.append(path)
        self.files[path] = text

    def remove(self, path):
        self.files.pop(path, None)

    def io(self):
        return {'read': self.read, 'run': self.run, 'write_ram': self.write_ram, 'write_flash': self.write_flash,
                'remove': self.remove}


class Shared(unittest.TestCase):
    def test_mode(self):
        for text, expected in CASES['mode']:
            self.assertEqual(sp.mode(text), expected, repr(text))

    def test_wg(self):
        for raw, expected in CASES['wg']:
            self.assertEqual(sp.wg_fingerprint(raw), expected, repr(raw))

    def test_cert_digests(self):
        for text, expected in CASES['cert_digests']:
            self.assertEqual(sp.cert_digests(text), expected, repr(text)[:80])

    def test_digests_match_openssl(self):
        self.assertEqual(sp.cert_digests(RAW['certs']['@CA1@']), [RAW['digests']['ca1']])
        self.assertEqual(sp.cert_digests(RAW['certs']['@CA2@']), [RAW['digests']['ca2']])

    def test_ovpn_parts(self):
        for text, has_inline, ca, remote in CASES['ovpn_parts']:
            inline, got_ca, got_remote = sp.ovpn_parts(text)
            self.assertEqual((inline is not None, got_ca, got_remote), (has_inline, ca, remote), repr(text))

    def test_wg_host(self):
        for text, section, host in CASES['wg_host']:
            self.assertEqual(sp.wg_host(text, section), host, repr(text))

    def test_load(self):
        for text, corrupt, count in CASES['load']:
            state, bad = sp.load(text)
            self.assertEqual((bad, len(state['records'])), (corrupt, count), repr(text))

    def test_sequence(self):
        state = sp.empty()
        for step in CASES['sequence']:
            op = step['op']
            if op == 'observe':
                events, urgency = sp.observe(state, step['live'], step['now'])
            elif op == 'request':
                events, urgency = sp.apply_request(state, step['request'], step['now'])
            elif op == 'blocker':
                self.assertEqual(sp.blocker(state, step['mode'], step['profiles']), step['expect'], step)
                continue
            else:
                self.assertEqual(sp.public(state, step['mode']), step['expect'], step)
                continue
            self.assertEqual([e['code'] for e in events], step['events'], step)
            self.assertEqual(urgency, step['urgency'], step)
            if 'record' in step:
                key, status, pinned, observed = step['record']
                record = state['records'][key]
                self.assertEqual((record['state'], record['fingerprint'], record['observed']), (status, pinned, observed), step)
            self.assertEqual(sp.load(json.dumps(state))[1], False)

    def test_evict(self):
        original = sp.MAX_RECORDS
        sp.MAX_RECORDS = CASES['evict']['max']
        try:
            state = sp.empty()
            for live, now in CASES['evict']['steps']:
                sp.observe(state, live, now)
        finally:
            sp.MAX_RECORDS = original
        self.assertEqual(sorted(state['records']), CASES['evict']['expect'])

    def test_gate(self):
        for case in CASES['gate']:
            files = {sp.CONFIG: case['config'], '/r/'+sp.STATE: case['ram'], '/p/'+sp.STATE: case['flash']}
            self.assertEqual(sp.gate(files.get, '/r', '/p', case['profiles']), case['expect'], case['name'])

    def test_live(self):
        for case in CASES['live']:
            fake = Fake(case['files'], copy.deepcopy(case['run']))
            self.assertEqual(sp.read_live(case['profile'], fake.io()), case['expect'], case['name'])

    def test_pins(self):
        for case in CASES['pins']:
            fake = Fake({k: v for k, v in case['files'].items() if v is not None}, case['run'])
            pins = sp.Pins('/var/run/homensai-vpn', '/etc/homensai-vpn', fake.io())
            for step in case['steps']:
                fake.answers.update(step.get('set_run', {}))
                for path, text in step.get('set_files', {}).items():
                    if text is None:
                        fake.files.pop(path, None)
                    else:
                        fake.files[path] = text
                events, public = pins.step(copy.deepcopy(step['rows']), step['mode'], step['now'])
                where = '%s @%s' % (case['name'], step['now'])
                self.assertEqual([e['code'] for e in events], step['events'], where)
                self.assertEqual(len(fake.flash), step['flash'], where)
                if 'public' in step:
                    self.assertEqual(public, step['public'], where)
                for path, text in [step['file']] if 'file' in step else []:
                    self.assertEqual(fake.files.get(path), text, where)
                for path in step.get('absent', []):
                    self.assertNotIn(path, fake.files, where)
                for text, profiles, expected in step.get('gate', []):
                    reader = dict(fake.files, **{sp.CONFIG: text})
                    self.assertEqual(sp.gate(reader.get, profiles=profiles), expected, where)
                for event in events:
                    self.assertEqual(event['time'], step['now'])


class RealFiles(unittest.TestCase):
    def test_router_io_writes_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, persist = os.path.join(tmp, 'run'), os.path.join(tmp, 'etc')
            rio = sp.router_io()
            fake = Fake(run={'uci -q get network.wgclient1.config': 'peer_1\n',
                             'wg show wgclient1 endpoints': 'q3Yp1E6rM2u1Lr0m8X4h6c8w2T5fW1kJ9Zx0bVnAs0E=\t1.1.1.1:51820\n'})
            io_ = dict(rio, run=fake.run)
            pins = sp.Pins(runtime, persist, io_)
            events, _ = pins.step([{'id': 'wireguard:peer_1', 'interface': 'wgclient1', 'code': None}], 'warn', 100)
            self.assertEqual([e['code'] for e in events], ['SERVER-KEY-PINNED'])
            self.assertTrue(os.path.isfile(os.path.join(persist, sp.STATE)))
            self.assertEqual(os.listdir(persist), [sp.STATE])  # no .pending left
            fake.answers['wg show wgclient1 endpoints'] = 'Bz7Q0mYk4sV8pT2xR6wN1cL5dH9fJ3gA0eU7iO4yK2w=\t1.1.1.1:51820\n'
            events, public = pins.step([{'id': 'wireguard:peer_1', 'interface': 'wgclient1', 'code': None}], 'warn', 800)
            self.assertEqual([e['code'] for e in events], ['SERVER-KEY-CHANGED'])
            out = []
            cfg = dict(io_, read=lambda path, limit=10**9: "\toption server_key_pin 'enforce'\n" if path == sp.CONFIG else rio['read'](path, limit))
            self.assertEqual(sp.cli(['list'], cfg, runtime, persist, out=out.append), 0)
            listed = json.loads(out[-1])
            self.assertEqual(listed['mode'], 'enforce')
            self.assertEqual(len(listed['changed']), 1)
            self.assertEqual(sp.gate(lambda p: cfg['read'](p), runtime, persist, ['wireguard:peer_1']), sp.BLOCKED)
            # online request: nobody applies it within the wait
            self.assertEqual(sp.cli(['accept', 'wireguard:peer_1'], cfg, runtime, persist, wait=0, out=out.append), 0)
            self.assertIn('REQUESTED', out[-1])
            self.assertTrue(os.path.isfile(os.path.join(runtime, sp.REQUEST)))
            events, public = pins.step([], 'warn', 900)
            self.assertEqual([e['code'] for e in events], ['SERVER-KEY-ACCEPTED'])
            self.assertFalse(os.path.exists(os.path.join(runtime, sp.REQUEST)))
            self.assertIsNone(sp.gate(lambda p: cfg['read'](p), runtime, persist, ['wireguard:peer_1']))
            # offline forget
            self.assertEqual(sp.cli(['forget', 'all', '--offline'], cfg, runtime, persist, out=out.append), 0)
            self.assertEqual(json.loads(open(os.path.join(persist, sp.STATE)).read())['records'], {})

    def test_page_accept_rpc(self):
        """rpc server_key_accept (2.1.0-alpha9): only a changed profile whose key is still the one the administrator
        checked is queued; the monitor applies it at its next pass; a key that changed again is not accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            runtime, persist = os.path.join(tmp, 'run'), os.path.join(tmp, 'etc')
            rio = sp.router_io()
            fake = Fake(run={'uci -q get network.wgclient1.config': 'peer_1\n',
                             'wg show wgclient1 endpoints': 'q3Yp1E6rM2u1Lr0m8X4h6c8w2T5fW1kJ9Zx0bVnAs0E=\t1.1.1.1:51820\n'})
            io_ = dict(rio, run=fake.run)
            pins = sp.Pins(runtime, persist, io_)
            row = [{'id': 'wireguard:peer_1', 'interface': 'wgclient1', 'code': None}]
            pins.step(row, 'warn', 100)
            accept = lambda args: sp.rpc_accept(args, runtime, persist, io_, 150)
            self.assertEqual(accept({'profile': 'wireguard:peer_1', 'observed': 'x'}), {'queued': False, 'code': 'SERVER-KEY-NOT-CHANGED'})
            current = next(iter(pins.state['records'].values()))['observed']
            self.assertEqual(accept({'profile': 'wireguard:peer_1', 'observed': current})['code'], 'SERVER-KEY-NOT-CHANGED', 'a pinned key is no change')
            fake.answers['wg show wgclient1 endpoints'] = 'Bz7Q0mYk4sV8pT2xR6wN1cL5dH9fJ3gA0eU7iO4yK2w=\t1.1.1.1:51820\n'
            _, public = pins.step(row, 'warn', 800)
            seen = public['changed'][0]['observed']
            for bad in ({}, {'profile': 'wireguard:peer_1'}, {'profile': 'wireguard:peer_1', 'observed': seen, 'x': 1}):
                self.assertEqual(accept(bad), {'queued': False, 'code': 'RPC-UNEXPECTED-ARGS'}, bad)
            for bad in ({'profile': 'wireguard:peer 1', 'observed': seen}, {'profile': '*', 'observed': seen},
                        {'profile': 'wireguard:peer_1', 'observed': ''}, {'profile': 'wireguard:peer_1', 'observed': 5}):
                self.assertEqual(accept(bad), {'queued': False, 'code': 'SERVER-KEY-PROFILE-INVALID'}, bad)
            self.assertEqual(accept({'profile': 'wireguard:peer_2', 'observed': seen})['code'], 'SERVER-KEY-NOT-CHANGED')
            self.assertFalse(os.path.exists(os.path.join(runtime, sp.REQUEST)))
            self.assertEqual(accept({'profile': 'wireguard:peer_1', 'observed': seen}), {'queued': True, 'code': None})
            request = json.loads(open(os.path.join(runtime, sp.REQUEST)).read())
            self.assertEqual(request, {'action': 'accept', 'profile': 'wireguard:peer_1', 'observed': seen, 'time': 150})
            # the key changes again: the pass first applies the queued acceptance of the key the administrator
            # checked, then observes the third key as a new change; a page that still shows the old key is refused
            fake.answers['wg show wgclient1 endpoints'] = 'Zm9vYmFyYmF6cXV4cXV1eGNvcmdlZ3JhdWx0Z2FycGg=\t1.1.1.2:51820\n'
            events, public = pins.step([dict(row[0], server_endpoint={'host': '1.1.1.2', 'port': 51820})], 'warn', 900)
            self.assertEqual([e['code'] for e in events], ['SERVER-KEY-ACCEPTED', 'SERVER-KEY-CHANGED'])
            self.assertFalse(os.path.exists(os.path.join(runtime, sp.REQUEST)), 'the request file is consumed')
            self.assertEqual((public['changed'][0]['pinned'], public['code']), (seen, 'SERVER-KEY-CHANGED'))
            self.assertEqual(accept({'profile': 'wireguard:peer_1', 'observed': seen})['code'], 'SERVER-KEY-NOT-CHANGED')
            third = public['changed'][0]['observed']
            self.assertEqual(accept({'profile': 'wireguard:peer_1', 'observed': third})['queued'], True)
            events, public = pins.step([], 'warn', 950)
            self.assertEqual([e['code'] for e in events], ['SERVER-KEY-ACCEPTED'])
            self.assertEqual(public['changed'], [])

    def test_cli_usage(self):
        out = []
        for argv in ([], ['accept'], ['list', 'x'], ['delete', 'all'], ['accept', 'a', 'b']):
            self.assertEqual(sp.cli(argv, Fake().io(), out=out.append), 2, argv)
        self.assertEqual(sp.cli(['accept', 'wireguard:peer 1'], Fake().io(), out=out.append), 2)
        self.assertIn('SERVER-KEY-PROFILE-INVALID', out[-1])


class NativeDiagnosticGate(unittest.TestCase):
    """native_switch.diagnostic wiring: a changed, unaccepted key of the pair blocks only in enforce mode."""
    def diagnostic(self, tmp, config, state):
        from unittest.mock import patch
        import native_switch as native
        from vendor_fixture import attach
        from test_native_switch import Backend
        backend = Backend()
        now = 1000
        status = attach({'profiles': copy.deepcopy(backend.profiles), 'samples': []}, now)
        for index, row in enumerate(status['profiles']):
            row.update(device='vpn'+str(index), mark=index+1, table=str(100+index), ifindex=index+10)
        data = {'profiles': copy.deepcopy(backend.profiles), 'servers': []}
        runtime = Path(tmp)/'run'
        runtime.mkdir(exist_ok=True)
        (Path(tmp)/'homensai_vpn').write_text(config)
        if state is not None:
            (runtime/sp.STATE).write_text(json.dumps(state))
        router = native.Linux()

        def binding(logical):
            row = next(row for row in status['profiles'] if row['interface'] == logical)
            value = {key: row[key] for key in ('device', 'mark', 'table', 'ifindex')}
            value['code'] = None
            return value
        patches = [patch.object(router, 'policy', return_value=backend.data),
                   patch.object(router, 'acceleration', return_value={'loaded': [], 'hnat_runtime': 'disabled'}),
                   patch.object(native, 'inventory', return_value=data), patch.object(native, 'read_json', return_value=status),
                   patch.object(native, 'route_binding', side_effect=binding), patch.object(native.time, 'time', return_value=now),
                   patch.object(native, 'command', return_value=json.dumps({'board_name': 'glinet,gl-mt6000'}).encode()),
                   patch.object(native, 'RUNTIME', runtime), patch.object(sp, 'CONFIG', str(Path(tmp)/'homensai_vpn'))]
        for item in patches:
            item.start()
        try:
            blockers, selection = router.diagnostic()
        finally:
            for item in patches:
                item.stop()
        self.assertIsNotNone(selection)
        return blockers, selection

    def test_enforce_blocks_a_changed_pair_profile_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            blockers, selection = self.diagnostic(tmp, '', None)
            self.assertNotIn(sp.BLOCKED, blockers)
            source = selection['source']['id']
            record = {'profile': source, 'host': 'h.example', 'protocol': source.split(':')[0], 'fingerprint': 'wg:A',
                      'observed': 'wg:B', 'state': 'changed', 'first_seen': 1, 'last_seen': 2, 'changed_at': 2, 'accepted_at': None}
            state = {'schema': 1, 'records': {source+'|h.example': record}}
            enforce = "\toption server_key_pin 'enforce'\n"
            # changed deliberately (review 04.11.2026, findings 1, 2): this pinned the code as a blocker of the diagnostic; a key
            # is the separate gate of a move onto its channel, tests/test_key_gate.py
            self.assertNotIn(sp.BLOCKED, self.diagnostic(tmp, enforce, state)[0])
            self.assertNotIn(sp.BLOCKED, self.diagnostic(tmp, "\toption server_key_pin 'warn'\n", state)[0])
            other = dict(record, profile='wireguard:peer_999')
            self.assertNotIn(sp.BLOCKED, self.diagnostic(tmp, enforce, {'schema': 1, 'records': {'x': other}})[0])
            self.assertNotIn(sp.BLOCKED, self.diagnostic(tmp, enforce, {'schema': 1, 'records': {'x': dict(record, state='pinned')}})[0])


class BothDiagnostics(unittest.TestCase):
    """lua backend.diagnostic and native_switch.diagnostic on the same fake router (tests/test_lua_backend.py): the same
    blockers, never SERVER-KEY-UNACCEPTED (changed deliberately, review 04.11.2026, findings 1 and 2: this test pinned the
    code as a blocker of the diagnostic; the proof of a route knows nothing of keys, tests/test_key_gate.py). The separate gate of
    both runtimes answers exactly for the profile with a changed key, in enforce only."""
    def test_lua_and_python_gate_the_same(self):
        import shutil
        lua = shutil.which('lua5.1')
        if not lua:
            self.skipTest('Lua 5.1 runtime absent; use homensai-vpn-python39:local')
        import test_lua_backend as tlb
        selection = tlb.py_diagnostic(tlb.base_world())[1]
        self.assertIsNotNone(selection)
        source, target = selection['source']['id'], selection['target']['id']

        def record(profile, state):
            return {'profile': profile, 'host': 'h.example', 'protocol': profile.split(':')[0], 'fingerprint': 'wg:A',
                    'observed': 'wg:B', 'state': state, 'first_seen': 1, 'last_seen': 2, 'changed_at': 2, 'accepted_at': None}

        def world(config, records):
            w = tlb.base_world()
            text = json.dumps({'schema': 1, 'records': {r['profile']+'|h.example': r for r in records}}).encode()
            w['vendor'] = dict(w['vendor'], **{sp.CONFIG: config.encode(), '/run/'+sp.STATE: text, '/run/hv/'+sp.STATE: text})
            return w
        enforce, warn = "\toption server_key_pin 'enforce'\n", "\toption server_key_pin 'warn'\n"
        code = sp.BLOCKED
        worlds = [(world(enforce, [record(target, 'changed')]), [None, code, [code]]), (world(enforce, [record(source, 'changed')]), [code, None, [code]]),
                  (world(warn, [record(target, 'changed')]), [None, None, []]), (world(enforce, [record(target, 'pinned')]), [None, None, []]),
                  (world(enforce, [record('wireguard:peer_999', 'changed')]), [None, None, []]), (world('', []), [None, None, []])]
        cases = [('diagnostic', {'world': tlb.lua_world(w)}, lambda w=w: tlb.py_diagnostic(w)) for w, _ in worlds]
        results = tlb.run_lua(cases)
        for (kind, data, fn), lua_result in zip(cases, results):
            python = tlb.outcome(fn)
            self.assertTrue(tlb.same(kind, python, lua_result), (python, lua_result))
            self.assertEqual(python['ok'][0], [], python)
            self.assertEqual(python['ok'][1], selection, 'the same selection as without a key')
        profiles = [source, target]
        cases = [('key_gate', {'world': tlb.lua_world(w), 'profiles': profiles}, lambda w=w: tlb.py_key_gate(w, profiles)) for w, _ in worlds]
        results = tlb.run_lua(cases)
        for (kind, data, fn), lua_result, (_, expected) in zip(cases, results, worlds):
            self.assertEqual(tlb.outcome(fn)['ok'], expected)
            self.assertEqual(lua_result['ok'], expected)


if __name__ == '__main__':
    unittest.main()
