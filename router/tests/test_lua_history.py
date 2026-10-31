"""Lua plan item 6: history and accounting written by the Lua monitor/Auto are the files Python writes.

Python and Lua get the same generated inputs (tests/lua/history_differential.lua runs the Lua side in one process)
and must produce the same canonical JSON (json.dumps(sort_keys=True, separators=(',',':'))) - same keys, same
values, same int/float types and float digits:
* agent.Accounting (traffic months/days, WAN, gaps, quality buckets, activity, retention, compaction, page view)
  with reliability.Reliability and route_history.RouteHistory, on random multi-day scenarios across a DST change
  and a month boundary (clock steps back, long gaps, counter resets, ifindex changes, retention changes);
* Reliability() validation codes, observed_route and active_controller on generated statuses;
* checkpoint.json + checkpoint.backup.json written by Lua equal what agent.checkpoint writes (canonically; agent's
  atomic_json keeps dict insertion order, Lua writes sorted keys, the sha256 is over the sorted text in both), and
  Lua restores a Python checkpoint (and a damaged main file from the backup) to the same model as agent.restore.
Runs where lua5.1 exists (homensai-vpn-python39:local).
"""
import copy
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
LIB = HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
LUA = shutil.which('lua5.1')
DRIVER = HERE/'lua/history_differential.lua'
TZ = 'CET-1CEST,M3.5.0,M10.5.0/3'
os.environ['TZ'] = TZ
time.tzset()

import agent  # noqa: E402
import checkpoint_schema  # noqa: E402
import reliability  # noqa: E402
import route_history  # noqa: E402


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def run_lua(cases):
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder)/'cases.json', Path(folder)/'results.json'
        source.write_text(json.dumps(cases))
        env = dict(os.environ, TZ=TZ, HOMENSAI_TEST_RUNTIME=folder)
        done = subprocess.run([LUA, str(DRIVER), str(source), str(target)], env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=600)
        if done.returncode:
            raise AssertionError(done.stderr.decode())
        return json.loads(target.read_text())


PROFILES = ['wireguard:peer_7', 'openvpn:1_2', 'wireguard:peer_9']
CODES = [None, None, None, 'VPN-003', 'DNS-001', 'VPN-001', 'CHECK-001', 'PROFILE-INACTIVE', 'SYSTEM-001']
STATES = ['OBSERVING', 'COMMITTED', 'DEGRADED-ON-RESERVE', 'APPLYING', 'BLOCKED', 'STOPPED', 'FAILED', 'STOPPED-ON-RESERVE']


def local(y, m, d, h=0, mi=0):
    return time.mktime((y, m, d, h, mi, 0, 0, 0, -1))


def native_for(rng, now, source, target):
    if rng.random() < 0.1:
        return None
    state = rng.choice(STATES)
    value = {'time': now - rng.choice([0.5, 3.0, 12.25, 45.0]), 'state': state, 'source': source, 'target': target}
    if rng.random() < 0.6:
        value.update(mode='continuous-pair', proof_scope='router-probed-ipv4')
        active = rng.choice([source, target, 'wireguard:peer_1'])
        value['channel_path'] = {'mode': 'continuous-pair', 'selection_proof': 'fw3-kernel-marking',
                                 'source_profile_id': source, 'target_profile_id': target, 'active_profile_id': active,
                                 'confirmed': rng.random() < 0.8, 'kernel_policy_verified': True,
                                 'checked_at': now - rng.choice([1.0, 5.5, 30.0]), 'transitioning': rng.random() < 0.1}
    else:
        value['certified'] = rng.random() < 0.7
    if rng.random() < 0.1:
        value['blockers'] = ['X']
    return value


def scenario(seed, start, steps, wan=True):
    rng = random.Random(seed)
    ops = []
    now = start
    rx = {'wgclient1': 1000, 'ovpnclient2': 50}
    ifindex = {'wgclient1': 21, 'ovpnclient2': 22}
    wan_rx = 10**9
    profiles = PROFILES[:2 + seed % 2]
    for step in range(steps):
        jump = rng.random()
        if jump < 0.03:
            now -= rng.choice([5.0, 40.0])          # the clock steps back
        elif jump < 0.07:
            now += rng.choice([200.0, 3700.0, 90000.0])  # a long gap (restart, sleep)
        else:
            now += rng.choice([10.0, 10.5, 30.0, 59.75, 60.0])
        for device in rx:
            if rng.random() < 0.02:
                ifindex[device] += 1
            if rng.random() < 0.02:
                rx[device] = rng.randrange(0, 100)
            else:
                rx[device] += rng.randrange(0, 2_000_000)
            ops.append({'op': 'sample', 'device': device, 'ifindex': ifindex[device], 'rx': rx[device],
                        'tx': rx[device]//3, 'now': now, 'max_gap': 90})
        if wan:
            wan_rx += rng.randrange(0, 10**7)
            ops.append({'op': 'wan_sample', 'device': 'eth0', 'ifindex': 2, 'rx': wan_rx, 'tx': wan_rx//7, 'now': now, 'max_gap': 90})
        rows = []
        for index, identifier in enumerate(profiles):
            code = rng.choice(CODES)
            row = {'id': identifier, 'name': 'Server %d' % index, 'protocol': identifier.split(':')[0],
                   'interface': None if code == 'PROFILE-INACTIVE' else ('wgclient1' if index != 1 else 'ovpnclient2'),
                   'code': code}
            rows.append(row)
        ops.append({'op': 'track', 'rows': rows, 'now': now, 'max_gap': 90})
        source, target = profiles[0], profiles[1]
        pair = rng.choice([{'source': source, 'target': target}, {}, {'source': target, 'target': source}])
        native = native_for(rng, now, source, target)
        probe_rows = []
        for row in rows + ([{'id': 'p0', 'code': None}] if step % 7 == 0 else []):
            code = row['code']
            stamp = now - rng.choice([0.0, 0.5, 1.25])
            result = {'id': row['id'], 'time': stamp, 'code': code,
                      'rtt_ms': round(rng.uniform(5, 400), 1) if code is None and rng.random() < 0.9 else (0.0 if code is None else None),
                      'dns_ok': code is None or rng.random() < 0.5, 'https_success': 3 if code is None else rng.choice([0, 1, 2])}
            if rng.random() < 0.05:
                result['administrative_state'] = 'disabled'
            probe_rows.append(dict(result, interface=row.get('interface')))
            ops.append({'op': 'observe', 'row': result, 'max_gap': 90, 'native': native, 'pair': pair})
        ops.append({'op': 'controller', 'active': rng.random() < 0.7, 'now': now, 'max_gap': 90})
        status = {'native_failover': native or {}, 'profiles': [dict(p, dns_ok=p['dns_ok']) for p in probe_rows]}
        ops.append({'op': 'route', 'status': status, 'now': now, 'max_gap': 90})
        if rng.random() < 0.03:
            ops.append({'op': 'retention', 'days': rng.randrange(1, 8), 'now': now})
        if rng.random() < 0.05:
            ops.append({'op': 'export'})
    ops.append({'op': 'export'})
    ops.append({'op': 'reliability_public'})
    ops.append({'op': 'public', 'now': now})
    return ops, now


def python_apply(acc, op):
    kind = op['op']
    if kind == 'sample':
        acc.sample(op['device'], op['ifindex'], op['rx'], op['tx'], op['now'], op['max_gap'])
    elif kind == 'wan_sample':
        if acc.wan is None:
            acc.wan = agent.Accounting()
        acc.wan.sample(op['device'], op['ifindex'], op['rx'], op['tx'], op['now'], op['max_gap'])
    elif kind == 'note_gap':
        acc.gaps += 1
        acc.note_gap(op['start'], op['end'])
    elif kind == 'track':
        acc.track_activity(copy.deepcopy(op['rows']), op['now'], op['max_gap'])
    elif kind == 'observe':
        acc.observe(copy.deepcopy(op['row']), max_gap=op['max_gap'], native=copy.deepcopy(op['native']), pair=copy.deepcopy(op['pair']))
    elif kind == 'retention':
        acc.apply_detail_retention(op['days'], op['now'])
    elif kind == 'controller':
        acc.reliability.controller(op['active'], op['now'], max_gap=op['max_gap'])
    elif kind == 'route':
        try:
            route = route_history.observed_route(copy.deepcopy(op['status']), op['now'])
        except (ValueError, TypeError, AttributeError):
            route = 'unknown'
        return [route, acc.reliability.routes.observe(route, op['now'], max_gap=op['max_gap'])]
    elif kind == 'compact':
        acc.compact(op['limit'])
    elif kind == 'export':
        return canonical(acc.export())
    elif kind == 'public':
        return canonical(acc.public_export())
    elif kind == 'reliability_public':
        return canonical(acc.reliability.public())
    else:
        raise ValueError(kind)
    return None


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class AccountingDifferential(unittest.TestCase):
    maxDiff = None

    def assert_same(self, ours, theirs, label):
        if ours != theirs:
            # name the first differing key path for a readable failure
            a, b = json.loads(ours) if isinstance(ours, str) else ours, json.loads(theirs) if isinstance(theirs, str) else theirs
            self.fail('%s differs: %s' % (label, first_difference(a, b)))

    def test_random_scenarios_produce_the_same_model(self):
        starts = [local(2026, 10, 24, 22), local(2026, 10, 31, 23, 30), local(2026, 3, 28, 23), local(2026, 12, 31, 23, 50)]
        cases, expected = [], []
        for seed in range(8):
            ops, _ = scenario(seed, starts[seed % len(starts)] + 0.25, 320, wan=seed % 3 != 2)
            cases.append({'initial': None, 'ops': ops})
            acc = agent.Accounting()
            expected.append([python_apply(acc, op) for op in ops])
        # a model restored from a Python export continues identically in Lua
        ops, last = scenario(100, local(2026, 10, 30, 12) + 0.5, 150)
        acc = agent.Accounting()
        for op in ops:
            python_apply(acc, op)
        initial = json.loads(json.dumps(acc.export()))
        more, _ = scenario(101, last + 30.0, 150)
        cases.append({'initial': initial, 'ops': more})
        restored = agent.Accounting(copy.deepcopy(initial))
        expected.append([python_apply(restored, op) for op in more])
        results = run_lua({'accounting': cases})['accounting']
        for index, (ours, theirs) in enumerate(zip(results, expected)):
            self.assertIsNone(ours['error'], 'case %d' % index)
            self.assertEqual(len(ours['outputs']), len(theirs))
            for position, (a, b) in enumerate(zip(ours['outputs'], theirs)):
                if b is None:
                    self.assertIsNone(a)
                elif isinstance(b, list):
                    self.assertEqual(a, b, 'case %d op %d route' % (index, position))
                else:
                    self.assert_same(a, b, 'case %d op %d (%s)' % (index, position, cases[index]['ops'][position]['op']))

    def test_compaction_and_aggregated_page_view(self):
        start = local(2026, 10, 25, 0) + 0.5
        ops = []
        for hour in range(160):
            for identifier in ['wireguard:peer_%d' % n for n in range(1, 30)]:
                ops.append({'op': 'observe', 'row': {'id': identifier, 'time': start + hour*3600.0, 'code': None, 'rtt_ms': 10.5 + hour,
                                                     'dns_ok': True, 'https_success': 3}, 'max_gap': 90, 'native': None, 'pair': {}})
        ops += [{'op': 'compact', 'limit': 200000}, {'op': 'export'}, {'op': 'public', 'now': start + 160*3600.0}]
        acc = agent.Accounting()
        expected = [python_apply(acc, op) for op in ops]
        ours = run_lua({'accounting': [{'initial': None, 'ops': ops}]})['accounting'][0]
        self.assertIsNone(ours['error'])
        self.assertTrue(json.loads(expected[-2])['retention']['quality_buckets_dropped'] > 0)
        for position in (-2, -1):
            self.assert_same(ours['outputs'][position], expected[position], 'op %d' % position)


    def test_page_view_aggregates_quality_above_500_kb(self):
        start = local(2026, 10, 25, 0) + 0.5
        ops = []
        for hour in range(40):
            for number in range(260):
                ops.append({'op': 'observe', 'row': {'id': 'probe-%d' % number, 'time': start + hour*3600.0, 'code': None, 'rtt_ms': 12.5,
                                                     'dns_ok': True, 'https_success': 3}, 'max_gap': 90, 'native': None, 'pair': {}})
        ops += [{'op': 'public', 'now': start + 40*3600.0}]
        acc = agent.Accounting()
        expected = [python_apply(acc, op) for op in ops]
        self.assertTrue(json.loads(expected[-1]).get('rpc_aggregated'), 'the 500 KB page budget is exceeded')
        ours = run_lua({'accounting': [{'initial': None, 'ops': ops}]})['accounting'][0]
        self.assertIsNone(ours['error'])
        self.assert_same(ours['outputs'][-1], expected[-1], 'aggregated page view')


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class ReliabilityDifferential(unittest.TestCase):
    def test_constructor_codes(self):
        good = reliability.Reliability()
        good.observe({'id': 'wireguard:peer_7', 'time': 1761900000.5, 'code': 'VPN-003'})
        base = good.export()
        variants = [None, {}, base]

        def mutate(fn):
            value = copy.deepcopy(base)
            fn(value)
            variants.append(value)
        mutate(lambda v: v.update(schema=2))
        mutate(lambda v: v.update(sequence=1.0))
        mutate(lambda v: v.update(extra=1))
        mutate(lambda v: v.update(since=-1))
        mutate(lambda v: v.update(details_dropped=-1))
        mutate(lambda v: v['months'].update({'2026-13': {}}))
        mutate(lambda v: v['events'][0].update(kind='OTHER'))
        mutate(lambda v: v['events'][0].update(code='CHECK-001'))
        mutate(lambda v: v['events'][0].update(sequence=5))
        mutate(lambda v: v['profiles']['wireguard:peer_7'].update(state='weird'))
        mutate(lambda v: v['profiles']['wireguard:peer_7'].update(state='OBSERVING'))  # legacy state migrated to 'down'
        mutate(lambda v: v.update(controller={'time': 1.0}))
        mutate(lambda v: v['totals'].update(other=1))
        mutate(lambda v: v['totals'].update(checks=-1))
        mutate(lambda v: v['route_history'].update(dropped=-1))
        mutate(lambda v: v['route_history']['segments'].append({'start': 5.0, 'end': 1.0, 'kind': 'source'}))
        mutate(lambda v: v['route_history'].update(last={'time': 1.0, 'kind': 'nowhere'}))
        mutate(lambda v: v['route_history'].update(since='x'))
        cases = [{'data': v, 'detail_days': 7} for v in variants] + [{'data': None, 'detail_days': 8}]
        expected = []
        for case in cases:
            try:
                expected.append(canonical(reliability.Reliability(copy.deepcopy(case['data']), detail_days=case['detail_days']).export()))
            except ValueError as error:
                expected.append('error:' + str(error))
        self.assertEqual(run_lua({'reliability_validate': cases})['reliability_validate'], expected)

    def test_observed_route_and_active_controller(self):
        rng = random.Random(7)
        now = 1761900000.5
        routes, controllers = [], []
        for _ in range(400):
            source, target = 'wireguard:peer_7', 'openvpn:1_2'
            native = native_for(rng, now, source, target) or {}
            if rng.random() < 0.2:
                native['transition_metadata_present'] = True
            profiles = []
            for identifier in (source, target):
                if rng.random() < 0.85:
                    profiles.append({'id': identifier, 'time': now - rng.choice([1.0, 30.0, 100.0]), 'code': rng.choice(CODES),
                                     'dns_ok': rng.random() < 0.8, 'https_success': rng.choice([0, 1, 2, 3])})
            routes.append({'status': {'native_failover': native, 'profiles': profiles}, 'now': now})
            state = {'phase': rng.choice(['RUNNING', 'STOPPED']), 'id': rng.choice(['a', 'b']), 'revision': rng.choice(['r1', 'r2'])}
            intent = {'mode': rng.choice(['on', 'off']), 'id': rng.choice(['a', 'b']), 'revision': rng.choice(['r1', 'r2'])}
            controllers.append({'native': native, 'state': state, 'intent': intent, 'now': now + rng.choice([0.0, 50.0, 95.0])})
        expected_routes = []
        for case in routes:
            try:
                expected_routes.append(route_history.observed_route(copy.deepcopy(case['status']), case['now']))
            except (TypeError, ValueError, AttributeError):
                expected_routes.append('error')
        expected_controllers = [reliability.active_controller(c['native'], c['state'], c['intent'], c['now']) for c in controllers]
        result = run_lua({'routes': routes, 'controllers': controllers})
        self.assertEqual(result['routes'], expected_routes)
        self.assertEqual(result['controllers'], expected_controllers)
        self.assertGreater(len(set(expected_routes)), 4)


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class CheckpointFiles(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def python_checkpoints(self, directory, stages):
        acc = agent.Accounting()
        directory.mkdir()
        with patch.object(agent, 'PERSIST', directory):
            for stage in stages:
                for op in stage['ops']:
                    python_apply(acc, op)
                with patch('time.time', return_value=stage['now']):
                    agent.checkpoint(acc)
        return acc

    def test_lua_writes_the_checkpoint_python_writes(self):
        ops, last = scenario(11, local(2026, 10, 30, 23) + 0.5, 200)
        more, end = scenario(12, last + 20.0, 100)
        stages = [{'ops': ops, 'now': last + 1.5}, {'ops': more, 'now': end + 2.5}]
        python_dir, lua_dir = self.folder/'python', self.folder/'lua'
        lua_dir.mkdir()
        self.python_checkpoints(python_dir, stages)
        result = run_lua({'checkpoints': [{'action': 'write', 'directory': str(lua_dir), 'now': 0, 'initial': None, 'stages': stages}]})
        self.assertEqual(len(result['checkpoints'][0]['exports']), 2)
        for name in ('checkpoint.json', 'checkpoint.backup.json'):
            ours = json.loads((lua_dir/name).read_text())
            theirs = json.loads((python_dir/name).read_text())
            checkpoint_schema.validate(ours)
            self.assertEqual(ours['sha256'], agent.checksum(ours['data']), name)
            self.assertEqual(canonical(ours), canonical(theirs), name)
            self.assertEqual((lua_dir/name).read_text(), canonical(theirs), 'Lua writes the sorted canonical text')

    def test_lua_restores_a_python_checkpoint_like_agent_restore(self):
        ops, last = scenario(21, local(2026, 10, 31, 22) + 0.5, 150)
        more, end = scenario(22, last + 20.0, 60)
        directory = self.folder/'python'
        self.python_checkpoints(directory, [{'ops': ops, 'now': last + 1.0}, {'ops': more, 'now': end + 1.0}])
        damaged = self.folder/'damaged'
        shutil.copytree(directory, damaged)
        text = (damaged/'checkpoint.json').read_text()
        (damaged/'checkpoint.json').write_text(text[:-20])  # a torn main file: the backup is restored
        cases, expected = [], []
        for folder in (directory, damaged):
            restore_at = end + 7200.25
            with patch.object(agent, 'PERSIST', folder), patch('time.time', return_value=restore_at):
                acc, notice = agent.restore()
            expected.append({'export': canonical(acc.export()), 'notice': notice})
            cases.append({'action': 'restore', 'directory': str(folder), 'now': restore_at})
        result = run_lua({'checkpoints': cases})['checkpoints']
        self.assertEqual(expected[1]['notice'], 'STORAGE-RECOVERED')
        for ours, theirs in zip(result, expected):
            self.assertEqual(ours['notice'], theirs['notice'])
            self.assertEqual(json.loads(ours['export']), json.loads(theirs['export']))
            self.assertEqual(ours['export'], theirs['export'])


def latency_status(rng, now, ids):
    native = {'time': now - rng.choice([0.0, 2.5, 40.0]), 'state': rng.choice(['OBSERVING', 'COMMITTED', 'APPLYING', 'BLOCKED', 'STOPPED']),
              'source': ids[0], 'target': ids[1]}
    if rng.random() < 0.5:
        native['certified'] = rng.random() < 0.8
    else:
        native.update(mode='continuous-pair', proof_scope='router-probed-ipv4', readiness_verified=rng.random() < 0.8)
        native['channel_path'] = {'mode': 'continuous-pair', 'selection_proof': 'fw3-kernel-marking', 'source_profile_id': ids[0],
                                  'target_profile_id': ids[1], 'active_profile_id': rng.choice(ids), 'confirmed': True,
                                  'kernel_policy_verified': True, 'checked_at': now - 2.0}
    profiles = []
    for identifier in ids:
        code = rng.choice([None, None, None, 'VPN-003'])
        profiles.append({'id': identifier, 'time': now - rng.choice([0.5, 3.25, 100.0]), 'code': code, 'dns_ok': code is None,
                         'https_success': 3 if code is None else 1, 'vendor_state': rng.choice(['SETTLED', 'SETTLED', 'OPENING']),
                         'rtt_ms': round(rng.uniform(8, 300), 1)})
    return {'native_failover': native, 'profiles': profiles}


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LatencyHistoryDifferential(unittest.TestCase):
    def test_minute_means_public_view_and_file(self):
        import latency_history
        from website_response_history import technical_history_tail
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(folder), True)
        cases, expected = [], []
        for seed in range(4):
            rng = random.Random(seed)
            now = 1761900000.25 + seed*1000
            ids = ['wireguard:peer_7', 'openvpn:1_2']
            settings = {'plan_source': ids[0], 'plan_target': ids[1], 'history_days': 7 if seed == 0 else rng.choice([1, '2', 7, 'x'])}
            ops = []
            steps = 3600 if seed == 0 else 300  # seed 0: more than 1441 rows -> rows_json
            for _ in range(steps):
                now += rng.choice([10.0, 20.5, 30.0, 61.0])
                if rng.random() < 0.02:
                    now -= 120.0
                if seed and rng.random() < 0.02:
                    ids = list(reversed(ids))
                status = latency_status(rng, now, ids)
                if rng.random() < 0.15:
                    status['native_failover']['state'] = 'BLOCKED'  # the 'blocked' route kind Python writes anyway
                ops.append({'status': status, 'settings': settings, 'now': now})
            history = latency_history.LatencyHistory()
            for op in ops:
                history.observe(copy.deepcopy(op['status']), op['settings'], op['now'])
            public = history.public()
            path = folder/('latency-%d.json' % seed)
            cases.append({'initial': None, 'ops': ops, 'now': now, 'save': str(path), 'load': str(path)})
            python_path = folder/('python-%d.json' % seed)
            history.save(python_path, agent.atomic_json, now)
            loaded = latency_history.LatencyHistory.load(python_path)
            expected.append({'data': canonical(dict(history.data, saved=None)), 'public': canonical(public),
                             'tail': canonical(technical_history_tail(public, now)), 'file': python_path, 'loaded': loaded})
        results = run_lua({'latency': cases})['latency']
        for index, (ours, theirs) in enumerate(zip(results, expected)):
            self.assertNotIn('error', ours, ours.get('error'))
            self.assertEqual(ours['data'], theirs['data'], 'case %d data' % index)
            self.assertEqual(ours['public'], theirs['public'], 'case %d public' % index)
            self.assertEqual(ours['tail'], theirs['tail'], 'case %d tail' % index)
            lua_file = json.loads(Path(cases[index]['save']).read_text())
            self.assertEqual(canonical(lua_file), canonical(json.loads(theirs['file'].read_text())), 'case %d file' % index)
            python_view = latency_history.LatencyHistory.load(cases[index]['save'])
            self.assertEqual(python_view.notice, theirs['loaded'].notice, 'Python reads the Lua file as its own')
            self.assertEqual(ours['notice'], theirs['loaded'].notice)
            if theirs['loaded'].notice is None:
                self.assertEqual(ours['loaded'], canonical(theirs['loaded'].data))
        self.assertIn('rows_json', json.loads(expected[0]['public']))
        self.assertTrue(any(e['loaded'].notice == 'LATENCY-HISTORY-UNAVAILABLE' for e in expected), 'the blocked-kind quirk is exercised')


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class TransitionLatency(unittest.TestCase):
    def test_capture_transition_latency(self):
        import native_history
        rng = random.Random(3)
        now = 1761900000.5
        cases = []
        for _ in range(3000):
            source, target = 'wireguard:peer_7', 'openvpn:1_2'
            value = {'state': rng.choice(['APPLYING', 'WAIT-CLIENT', 'COMMITTED', 'ROLLED-BACK', 'RESTORING', 'OBSERVING']),
                     'source': source, 'target': target, 'time': now}
            if rng.random() < 0.3:
                value.update(destination_role=rng.choice(['source', 'target']), transition_metadata_present=True)
                value['destination_profile_id'] = value[value['destination_role']] if rng.random() < 0.9 else source
            if rng.random() < 0.1:
                value['route_changed'] = False
            identifier = rng.choice([source, target])
            interface = 'wgclient1' if identifier.startswith('wireguard') else 'ovpnclient2'
            protocol = identifier.split(':')[0]
            row = {'id': identifier, 'code': rng.choice([None, None, None, 'VPN-003']), 'dns_ok': rng.random() < 0.9,
                   'https_success': rng.choice([3, 3, 2, 1, True]), 'vendor_state': rng.choice(['SETTLED', 'SETTLED', 'OPENING']),
                   'protocol': protocol, 'interface': interface, 'vendor_tunnel_id': protocol + ':' + interface,
                   'vendor_generation': rng.choice(['a'*32, 'b'*32]), 'time': now - rng.choice([0.5, 30.0, 100.0]),
                   'rtt_ms': rng.choice([42.5, 42.5, 17.0, 0.0, 700000.0, None])}
            status = {'time': now - rng.choice([1.0, 1.0, 1.0, 95.0]), 'profiles': [row] + ([dict(row)] if rng.random() < 0.05 else [])}
            if rng.random() < 0.05:
                status['error'] = 'SYSTEM-001'
            binding = {k: row[k] for k in ('id', 'protocol', 'interface', 'vendor_tunnel_id')}
            binding['vendor_generation'] = row['vendor_generation'] if rng.random() < 0.85 else 'c'*32
            cases.append({'value': value, 'status': status, 'binding': binding, 'now': now})
        expected = []
        for case in cases:
            found = native_history.capture_transition_latency(copy.deepcopy(case['value']), copy.deepcopy(case['status']), case['binding'], case['now'])
            expected.append(None if found is None else canonical(found))
        result = run_lua({'capture': cases})['capture']
        self.assertEqual(result, expected)
        self.assertGreater(sum(e is not None for e in expected), 30)


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class StatsResetDifferential(unittest.TestCase):
    """stats_reset.apply + agent.checkpoint (Python) against stats_reset.lua apply + save (Lua) on copies of one router."""

    def seed_router(self, folder, now):
        import native_history
        import ping_response_history
        import response_compare
        import website_response_history
        persist = folder/'persist'
        persist.mkdir(parents=True)
        history = native_history.History(persist, detail_days=7)
        for index, state in enumerate(['ARMED', 'APPLYING', 'WAIT-CLIENT', 'COMMITTED', 'BLOCKED']):
            history.record({'state': state, 'source': 'wireguard:peer_7', 'target': 'openvpn:1_2', 'reason': 'SOURCE-FAILED'}, now - 5000 + index*60.5)
        ping = ping_response_history.PingResponseHistory()
        ping.save(persist/'ping-response-history.json', agent.atomic_json, now - 100.0)
        website_response_history.WebsiteResponseHistory().save(persist/'website-response-history.json', agent.atomic_json, now - 100.0)
        compare = response_compare.ResponseCompare({'version': 1, 'rows': {'icmp-1.1.1.1': {'wireguard:peer_7': [[1761897600, 120, 3, 1]]}},
                                                   'seen': {'icmp-1.1.1.1|wireguard:peer_7': 1761897700.5}})
        compare.save(persist/'response-compare.json', agent.atomic_json, now - 100.0)
        speed = {'results': [{'time': now - 3600.5, 'down': 10.5}, {'time': now - 30*86400.0, 'down': 1.0}], 'history_truncated': 2}
        agent.atomic_json(persist/'speed-history.json', {'schema': 1, 'data': speed, 'sha256': agent.checksum(speed)})
        ops, _ = scenario(5, now - 3000.0, 80)
        acc = agent.Accounting()
        for op in ops:
            python_apply(acc, op)
        return persist, json.loads(json.dumps(acc.export()))

    def python_reset(self, persist, runtime, accounting, now):
        import stats_reset
        import latency_history
        import ping_response_history
        import response_compare
        import speed_test
        import website_response_history
        import contextlib
        acc = agent.Accounting(copy.deepcopy(accounting))
        with patch('time.time', return_value=now), patch.object(agent, 'PERSIST', persist), \
                patch.object(speed_test, 'HISTORY', persist/'speed-history.json'), \
                patch.object(speed_test, 'control_lock', contextlib.nullcontext), \
                patch('retention_settings.configured_days', return_value=7):
            histories = (latency_history.LatencyHistory.load(persist/'latency-history.json'),
                         website_response_history.WebsiteResponseHistory.load(persist/'website-response-history.json'),
                         ping_response_history.PingResponseHistory.load(persist/'ping-response-history.json'),
                         response_compare.ResponseCompare.load(persist/'response-compare.json'))
            request = stats_reset.pending(runtime)
            acc, reset_latency, result = stats_reset.apply(request, acc, histories[0], now, agent.atomic_json, persist=persist,
                                                           website_response=histories[1], ping_response=histories[2], compare_response=histories[3])
            if result.get('done'):
                agent.checkpoint(acc, reset_latency, *histories[1:])
        return result, acc

    def test_every_scope_resets_the_same_files(self):
        now = 1761903000.75
        for scope in ('latency', 'auto', 'traffic', 'quality', 'speed', 'ranking', 'all'):
            with self.subTest(scope=scope):
                folder = Path(tempfile.mkdtemp())
                self.addCleanup(shutil.rmtree, str(folder), True)
                persist, accounting = self.seed_router(folder/'python', now)
                shutil.copytree(folder/'python', folder/'lua')
                request = {'scope': scope, 'time': now - 1.0, 'nonce': 'a'*32}
                for side in ('python', 'lua'):
                    (folder/side/'runtime').mkdir()
                    (folder/side/'runtime'/'stats-reset-request.json').write_text(json.dumps(request))
                result, acc = self.python_reset(persist, folder/'python'/'runtime', accounting, now)
                lua_persist = folder/'lua'/'persist'
                ours = run_lua({'reset': [{'now': now, 'persist': str(lua_persist), 'runtime': str(folder/'lua'/'runtime'),
                                           'accounting': accounting}]})['reset'][0]
                self.assertNotIn('error', ours, ours.get('error'))
                self.assertTrue(result['done'], result)
                self.assertEqual(ours['result'], result)
                self.assertEqual(ours['accounting'], canonical(acc.export()))
                self.assertFalse((folder/'lua'/'runtime'/'stats-reset-request.json').exists())
                python_files = sorted(p.relative_to(persist).as_posix() for p in persist.rglob('*') if p.is_file() and not p.name.endswith('.lock'))
                lua_files = sorted(p.relative_to(lua_persist).as_posix() for p in lua_persist.rglob('*') if p.is_file() and not p.name.endswith('.lock'))
                self.assertEqual(lua_files, python_files)
                for name in python_files:
                    theirs = json.loads((persist/name).read_text())
                    mine = json.loads((lua_persist/name).read_text())
                    self.assertEqual(canonical(mine), canonical(theirs), '%s: %s' % (name, first_difference(mine, theirs)))


def first_difference(a, b, path='$'):
    if type(a) is not type(b):
        return '%s: %r (%s) != %r (%s)' % (path, a, type(a).__name__, b, type(b).__name__)
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                return '%s.%s missing on %s' % (path, key, 'lua' if key not in a else 'python')
            found = first_difference(a[key], b[key], path + '.' + key)
            if found:
                return found
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return '%s: length %d != %d' % (path, len(a), len(b))
        for index, (x, y) in enumerate(zip(a, b)):
            found = first_difference(x, y, '%s[%d]' % (path, index))
            if found:
                return found
        return None
    return None if a == b else '%s: %r != %r' % (path, a, b)


if __name__ == '__main__':
    unittest.main()
