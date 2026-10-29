"""Candidate readiness must never become route permission or a LAN certificate."""
import copy
from contextlib import contextmanager
from collections import namedtuple
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
import mt3000_manual_platform as platform
from vendor_fixture import attach


def fixture():
    profiles = [
        {'id': 'openvpn:1_1', 'protocol': 'openvpn', 'interface': 'ovpnclient1'},
        {'id': 'wireguard:peer_2', 'protocol': 'wireguard', 'interface': 'wgclient1'},
    ]
    status = attach({'profiles': profiles}, 1000)
    bindings = {}
    for index, row in enumerate(profiles):
        values = {'device': row['interface'], 'mark': 4096*(index+1),
                  'table': str(1001+index), 'ifindex': 7+index}
        row.update(values)
        bindings[row['interface']] = dict(values, up=True, pending=False, code=None)
    policy = {
        'sections': [
            {'.name': 'global', '.type': 'policy', 'enabled': '1'},
            {'.name': 'default', '.type': 'default', 'enabled': '0'},
            {'.name': 'special', '.type': 'rule', 'enabled': '1', 'killswitch': '1',
             'via': 'ovpnclient2', 'to_type': 'domain'},
            {'.name': 'a', '.type': 'rule', 'enabled': '1', 'killswitch': '1', 'via': 'ovpnclient1'},
            {'.name': 'b', '.type': 'rule', 'enabled': '1', 'killswitch': '1', 'via': 'wgclient1'},
        ],
        'settings': {'plan_source': profiles[0]['id'], 'plan_target': profiles[1]['id'],
                     'native_order_direction': 'first', 'monitor_only': '0',
                     'native_enabled': '0', 'terms_version': '1'},
        'ipv6': '0', 'lan': 'br-lan', 'firewall_defaults': [{}],
    }
    metadata = {'profiles': copy.deepcopy(profiles)}
    return {
        'board': {'board_name': 'glinet,mt3000-snand', 'model': 'GL.iNet GL-MT3000',
                  'release': {'target': 'mediatek/mt7981'}},
        'firmware': '4.11.0', 'kernel': '5.4.211', 'architecture': 'aarch64',
        'vendor_hashes': dict(platform.EXPECTED_VENDOR),
        'journal_absent': True, 'own_guard_absent': True, 'fw4_absent': True,
        'fw4_config': '0',
        'include': {'path': '/usr/bin/rtp2.sh', 'type': 'script', 'reload': '0'},
        'fw3_state': "package fw3_state\nconfig defaults\n" + ''.join(
            "config zone\noption name '%s'\n" % name for name in ('lan', 'wan', 'ovpnclient1', 'wgclient1')),
        'workers': [{'time': 999, 'busy': 0, 'verified': True},
                    {'time': 1000, 'busy': 0, 'verified': True}],
        'policy': policy, 'policy_after': copy.deepcopy(policy),
        'inventory': metadata, 'inventory_after': copy.deepcopy(metadata),
        'status': status, 'bindings': bindings,
    }


class CollectorFixture:
    """No command reaches the host; every permitted read has an exact reply."""
    def __init__(self):
        self.evidence = fixture()
        self.mono = 100.0
        self.calls = []
        self.inventory_calls = 0
        self.policy_calls = 0
        self.fault = None
        self.last_read_jump = False
        self.vendor = {path: ('vendor-fixture:'+path).encode() for path in platform.EXPECTED_VENDOR}

    def read(self, path, maximum=131072):
        path = str(path)
        if path in self.vendor:
            return self.vendor[path]
        if path == '/etc/glversion':
            return b'4.11.0\n'
        if path == '/var/run/fw3.state':
            return self.evidence['fw3_state'].encode()
        for interface, row in self.evidence['bindings'].items():
            if path == '/sys/class/net/'+interface+'/ifindex':
                return str(row['ifindex']).encode()
        raise AssertionError('unexpected file read '+path)

    def workers(self, *args, **kwargs):
        return {'time': 1000+self.mono-100, 'busy': 0, 'verified': True}

    def run(self, args, **kwargs):
        self.calls.append((args, kwargs))
        self.mono += .05
        if self.fault:
            value = self.fault(args)
            if value is not None:
                return subprocess.CompletedProcess(args, 0, value)
        e = self.evidence
        if args == ['ubus', '-t', '3', 'call', 'system', 'board']:
            reply = e['board']
        elif args == ['/usr/bin/lua', '/usr/lib/homensai-vpn/native_policy.lua']:
            self.policy_calls += 1
            reply = e['policy'] if self.policy_calls == 1 else e['policy_after']
        elif args == ['/usr/bin/lua', '/usr/lib/homensai-vpn/inventory.lua']:
            self.inventory_calls += 1
            reply = e['inventory'] if self.inventory_calls == 1 else e['inventory_after']
            if self.inventory_calls == 2 and self.last_read_jump:
                self.mono += 21
        elif args[:2] == ['/usr/bin/lua', '-e']:
            if 'c:get_all' not in args[2] or 'c:set' in args[2] or 'commit' in args[2]:
                raise AssertionError('unexpected Lua operation')
            reply = {'include': e['include'], 'fw4_config': '0'}
        elif args == ['nft', 'list', 'tables']:
            return subprocess.CompletedProcess(args, 0, b'')
        elif args[:4] == ['ubus', '-t', '2', 'call'] and args[-1] == 'status':
            interface = args[4].removeprefix('network.interface.') if hasattr(str, 'removeprefix') else args[4][18:]
            row = e['bindings'][interface]
            reply = {'up': row['up'], 'pending': row['pending'], 'l3_device': row['device']}
        elif args == ['ip', '-4', '-j', 'route', 'show', 'table', 'all']:
            reply = [{'dst': 'default', 'dev': row['device'], 'table': row['table']}
                     for row in e['bindings'].values()]
        elif args == ['ip', '-4', '-j', 'rule', 'show']:
            reply = [{'fwmark': hex(row['mark']), 'table': row['table']}
                     for row in e['bindings'].values()]
        elif args[:5] == ['ip', '-4', '-j', 'route', 'get']:
            row = next(row for row in e['bindings'].values() if row['mark'] == int(args[-1]))
            reply = [{'dev': row['device'], 'table': row['table']}]
        else:
            raise AssertionError('unallowlisted command '+repr(args))
        return subprocess.CompletedProcess(args, 0, json.dumps(reply).encode())

    @contextmanager
    def patched(self):
        import agent
        expected = {path: hashlib.sha256(raw).hexdigest() for path, raw in self.vendor.items()}
        with patch.object(platform, '_read', side_effect=self.read), \
                patch.object(platform, '_workers', side_effect=self.workers), \
                patch.object(platform, 'EXPECTED_VENDOR', expected), \
                patch.object(platform.os, 'uname', return_value=namedtuple('Uname', 'system node release version machine')('Linux', 'fixture', '5.4.211', 'fixture', 'aarch64')), \
                patch.object(platform.time, 'monotonic', side_effect=lambda: self.mono), \
                patch.object(platform.time, 'time', side_effect=lambda: 1000+self.mono-100), \
                patch.object(agent, 'read_json', return_value=self.evidence['status']), \
                patch.object(platform.subprocess, 'run', side_effect=self.run):
            yield


class ManualPlatformTests(unittest.TestCase):
    def assess(self, evidence):
        return platform.assess(evidence, now=1000)

    def test_verified_candidate_remains_blocked_and_does_not_mutate_evidence(self):
        evidence = fixture(); original = copy.deepcopy(evidence)
        with patch('subprocess.run', side_effect=AssertionError('pure assessment did I/O')):
            result = self.assess(evidence)
        self.assertEqual(evidence, original)
        self.assertTrue(result['candidate_checks_passed'])
        self.assertEqual(result['blockers'], [platform.NOT_CERTIFIED])
        for key in ('can_apply', 'available', 'native_certified', 'lan_verified'):
            self.assertIs(result[key], False)
        self.assertEqual(result['eligibility'], 'BLOCKED')
        self.assertEqual(result['proof_scope'], platform.PROOF_SCOPE)
        self.assertIsNone(result['vendor_attempts_exhausted'])

    def test_exact_platform_and_all_four_hashes_are_required(self):
        changes = [lambda e: e['board'].update(board_name='glinet,gl-mt6000'),
                   lambda e: e['board']['release'].update(target='mediatek/filogic'),
                   lambda e: e.update(kernel='5.4.212'), lambda e: e.update(firmware='4.11.1'),
                   lambda e: e.update(architecture='x86_64')]
        for change in changes:
            with self.subTest(change=change):
                evidence = fixture(); change(evidence)
                self.assertFalse(self.assess(evidence)['candidate_checks_passed'])
        for name in platform.EXPECTED_VENDOR:
            evidence = fixture(); evidence['vendor_hashes'][name] = '0'*64
            self.assertIn('VENDOR-CODE-UNVERIFIED', self.assess(evidence)['blockers'])

    def test_monitor_only_terms_and_native_guards_are_not_waived(self):
        for key, value, reason in [('monitor_only', '1', 'MONITOR-ONLY-DEPLOYMENT'),
                                   ('monitor_only', None, 'MONITOR-ONLY-INVALID'),
                                   ('native_enabled', '1', 'NATIVE-CONTROLLER-STATE-UNVERIFIED'),
                                   ('terms_version', '0', 'TERMS-NOT-ACCEPTED')]:
            with self.subTest(key=key, value=value):
                evidence = fixture(); evidence['policy']['settings'][key] = value
                evidence['policy_after'] = copy.deepcopy(evidence['policy'])
                self.assertIn(reason, self.assess(evidence)['blockers'])

    def test_native_certificate_is_not_created_or_native_board_guard_changed(self):
        import native_switch
        old = native_switch.Linux.diagnostic
        result = self.assess(fixture())
        self.assertIs(native_switch.Linux.diagnostic, old)
        self.assertNotIn('certificate', result)
        self.assertFalse(hasattr(platform, 'apply'))
        self.assertFalse(hasattr(platform, 'start'))

    def test_fw3_state_reload_and_transaction_absence_are_required(self):
        changes = [lambda e: e.update(fw3_state=''),
                   lambda e: e.update(fw3_state=e['fw3_state']+"config zone\noption name 'lan'\n"),
                   lambda e: e['include'].update(reload='1'),
                   lambda e: e['include'].update(path='/other.sh'),
                   lambda e: e.update(fw4_absent=False), lambda e: e.update(fw4_config='1'),
                   lambda e: e.update(journal_absent=False), lambda e: e.update(own_guard_absent=False)]
        for change in changes:
            evidence = fixture(); change(evidence)
            self.assertFalse(self.assess(evidence)['candidate_checks_passed'])

    def test_quiet_requires_two_verified_fresh_zero_samples(self):
        for samples in ([], [{}], [{'time': 1000, 'busy': 0, 'verified': True}],
                        [{'time': 1000, 'busy': False, 'verified': True}]*2,
                        [{'time': 1001, 'busy': 0, 'verified': True}]*2,
                        [{'time': 1000, 'busy': 1, 'verified': True}]*2,
                        [{'time': 1000, 'busy': 0, 'verified': False}]*2):
            evidence = fixture(); evidence['workers'] = samples
            self.assertIn('VENDOR-WORKER-QUIET-UNVERIFIED', self.assess(evidence)['blockers'])

    def test_existing_native_policy_safety_subset_is_reused(self):
        for change, reason in [
            (lambda e: e['policy'].update(ipv6='1'), 'IPV6-NOT-EXPLICITLY-DISABLED'),
            (lambda e: e['policy']['sections'][1].update(enabled='1'), 'DIRECT-WAN-FALLBACK'),
            (lambda e: e['policy']['sections'][3].update(killswitch='0'), 'KILLSWITCH-NOT-ENABLED'),
            (lambda e: e['policy']['sections'].append({'.name': 'late', '.type': 'rule',
                 'enabled': '1', 'killswitch': '1', 'to_type': 'domain'}), 'SPECIAL-RULES-MUST-PRECEDE-GENERIC'),
            (lambda e: e['policy']['firewall_defaults'][0].update(flow_offloading='1'), 'FLOW-OFFLOAD-ENABLED')]:
            evidence = fixture(); change(evidence)
            self.assertIn(reason, self.assess(evidence)['blockers'])

    def test_same_tunnel_inactive_and_stale_profiles_cannot_qualify(self):
        for change in [lambda e: e['inventory']['profiles'][1].update(interface=None),
                       lambda e: e['status'].update(time=800),
                       lambda e: e['status']['profiles'][1].update(vendor_generation='0'*32),
                       lambda e: e['status']['vendor_observation']['groups'][1].update(state='PENDING'),
                       lambda e: e['policy']['settings'].update(plan_target=e['policy']['settings']['plan_source'])]:
            evidence = fixture(); change(evidence)
            self.assertFalse(self.assess(evidence)['candidate_checks_passed'])

    def test_policy_or_binding_rebound_is_refused(self):
        changes = [lambda e: e['policy_after']['sections'][3].update(via='wgclient1'),
                   lambda e: e['inventory_after']['profiles'][0].update(id='openvpn:1_2'),
                   lambda e: e['bindings']['wgclient1'].update(ifindex=99),
                   lambda e: e['bindings']['wgclient1'].update(up='true'),
                   lambda e: e['bindings']['wgclient1'].update(pending=None),
                   lambda e: e['bindings']['wgclient1'].update(table=None)]
        for change in changes:
            evidence = fixture(); change(evidence)
            self.assertFalse(self.assess(evidence)['candidate_checks_passed'])

    def test_failed_target_is_not_working_and_raw_private_evidence_is_not_exposed(self):
        evidence = fixture(); evidence['status']['profiles'][1]['dns_ok'] = False
        evidence['inventory']['profiles'][0]['private_test_sentinel'] = 'DO-NOT-EXPOSE'
        result = self.assess(evidence)
        self.assertIn('TARGET-ROUTER-PATH-UNVERIFIED', result['blockers'])
        self.assertNotIn('DO-NOT-EXPOSE', json.dumps(result))
        self.assertNotIn('sections', result)

    def test_malformed_nonfinite_and_deep_evidence_fail_closed(self):
        for value in (None, [], 'bad', {'policy': []}, {'time': float('nan')}, {'time': float('inf')}):
            self.assertIn('MT3000-EVIDENCE-UNVERIFIED', self.assess(value)['blockers'])
        evidence = fixture(); nested = []
        for _ in range(40):
            nested = [nested]
        evidence['extra'] = nested
        self.assertIn('MT3000-EVIDENCE-UNVERIFIED', self.assess(evidence)['blockers'])

    def test_two_logical_tunnels_cannot_share_one_kernel_binding(self):
        evidence = fixture()
        shared = evidence['bindings']['ovpnclient1']
        evidence['bindings']['wgclient1'] = copy.deepcopy(shared)
        evidence['status']['profiles'][1].update({key: shared[key] for key in ('device', 'mark', 'table', 'ifindex')})
        result = self.assess(evidence)
        self.assertIn('SHARED-KERNEL-BINDING', result['blockers'])

    def test_incomplete_duplicate_and_mixed_fw3_states_do_not_qualify(self):
        good = fixture()['fw3_state']
        invalid = [good+'config zone\n', good+"config zone\nlist name 'guest'\n",
                   good+"config zone 'same'\noption name 'guest'\nconfig zone 'same'\noption name 'iot'\n",
                   good+"config zone\noption name 'guest'\nlist name 'iot'\n",
                   good+"package fw3_state\n", good.replace('package fw3_state\n', ''),
                   good+"config unknown\n", good+"config zone\noption name '\n"]
        for text in invalid:
            with self.subTest(text=text):
                evidence = fixture(); evidence['fw3_state'] = text
                self.assertIn('FW3-RUNTIME-STATE-UNVERIFIED', self.assess(evidence)['blockers'])

    def test_future_backward_clock_and_nonfinite_workers_do_not_qualify(self):
        for clock in (float('nan'), float('inf'), -1, 900):
            result = platform.assess(fixture(), now=clock)
            self.assertFalse(result['candidate_checks_passed'])
        evidence = fixture(); evidence['workers'][1]['time'] = float('nan')
        self.assertIn('MT3000-EVIDENCE-UNVERIFIED', self.assess(evidence)['blockers'])


class CollectorTests(unittest.TestCase):
    def test_collector_uses_only_allowlisted_reads_and_never_returns_private_fields(self):
        harness = CollectorFixture()
        harness.evidence['inventory']['profiles'][0]['private_test_sentinel'] = 'PRIVATE-SENTINEL'
        harness.evidence['inventory_after'] = copy.deepcopy(harness.evidence['inventory'])
        with harness.patched():
            result = platform.preflight()
        self.assertTrue(result['candidate_checks_passed'], result)
        self.assertEqual(result['blockers'], [platform.NOT_CERTIFIED])
        self.assertNotIn('PRIVATE-SENTINEL', json.dumps(result))
        self.assertGreater(len(harness.calls), 10)
        for args, kwargs in harness.calls:
            self.assertFalse({'add', 'del', 'delete', 'replace', 'reorder', 'commit', 'up', 'down', 'restart', 'reload'}.intersection(args))
            self.assertIs(kwargs['stdin'], subprocess.DEVNULL)
            self.assertIs(kwargs['check'], True)
            self.assertLessEqual(kwargs['timeout'], 3)

    def test_total_deadline_is_checked_after_last_read_not_only_before_spawn(self):
        harness = CollectorFixture(); harness.last_read_jump = True
        with harness.patched():
            result = platform.preflight()
        self.assertFalse(result['candidate_checks_passed'], result)
        self.assertIn('MT3000-COLLECTION-DEADLINE', result['blockers'])

    def test_timeout_failed_oversize_and_malformed_outputs_refuse_without_leaking(self):
        for failure in ('timeout', 'failed', 'oversize', 'malformed', 'duplicate'):
            with self.subTest(failure=failure):
                harness = CollectorFixture()
                def fault(args):
                    if args[-2:] != ['system', 'board']:
                        return None
                    if failure == 'timeout':
                        raise subprocess.TimeoutExpired(args, 1, output=b'PRIVATE-SENTINEL')
                    if failure == 'failed':
                        raise subprocess.CalledProcessError(1, args, output=b'PRIVATE-SENTINEL')
                    if failure == 'oversize':
                        return b'PRIVATE-SENTINEL'+b'x'*131072
                    if failure == 'malformed':
                        return b'PRIVATE-SENTINEL'
                    return b'{"board_name":"PRIVATE-SENTINEL",'+json.dumps(harness.evidence['board'])[1:].encode()
                harness.fault = fault
                with harness.patched():
                    result = platform.preflight()
                self.assertFalse(result['candidate_checks_passed'], result)
                self.assertNotIn('PRIVATE-SENTINEL', json.dumps(result))

    def test_nft_command_failure_is_not_absence_proof(self):
        harness = CollectorFixture()
        def fault(args):
            if args == ['nft', 'list', 'tables']:
                raise subprocess.CalledProcessError(1, args)
        harness.fault = fault
        with harness.patched():
            result = platform.preflight()
        self.assertFalse(result['candidate_checks_passed'])
        self.assertIn('MANUAL-TRANSACTION-STATE-UNVERIFIED', result['blockers'])

    def test_ambiguous_routes_and_binding_rebound_fail_closed(self):
        for fault_kind in ('second_mark', 'wrong_route', 'changed_ifindex'):
            harness = CollectorFixture()
            def fault(args):
                if fault_kind == 'second_mark' and args == ['ip', '-4', '-j', 'rule', 'show']:
                    return b'[{"fwmark":"0x1000","table":"1001"},{"fwmark":"0x3000","table":"1001"}]'
                if fault_kind == 'wrong_route' and args[:5] == ['ip', '-4', '-j', 'route', 'get']:
                    return b'[{"dev":"wrong","table":"1001"}]'
                if fault_kind == 'changed_ifindex' and args[:5] == ['ip', '-4', '-j', 'route', 'get']:
                    harness.evidence['bindings']['ovpnclient1']['ifindex'] = 88
            harness.fault = fault
            with harness.patched():
                result = platform.preflight()
            self.assertFalse(result['candidate_checks_passed'], (fault_kind, result))

    def test_unconfigured_pair_returns_its_reason_and_keeps_quiet_evidence(self):
        harness = CollectorFixture()
        for key in ('policy', 'policy_after'):
            harness.evidence[key]['settings']['plan_source'] = ''
        with harness.patched():
            result = platform.preflight()
        self.assertIn('SOURCE-RESERVE-NOT-CONFIGURED', result['blockers'])
        self.assertNotIn('VENDOR-WORKER-QUIET-UNVERIFIED', result['blockers'])

    def test_clock_jump_during_collection_is_not_a_fresh_snapshot(self):
        harness = CollectorFixture()
        with harness.patched(), patch.object(platform.time, 'time', side_effect=lambda: 1000+(0 if harness.mono == 100 else 10)+harness.mono-100):
            result = platform.preflight()
        self.assertFalse(result['candidate_checks_passed'])
        self.assertIn('MT3000-COLLECTION-CLOCK-CHANGED', result['blockers'])

    def test_unknown_worker_read_failure_refuses_without_private_exception_text(self):
        harness = CollectorFixture()
        with harness.patched(), patch.object(platform, '_workers', side_effect=ValueError('PRIVATE-SENTINEL')):
            result = platform.preflight()
        self.assertFalse(result['candidate_checks_passed'])
        self.assertIn('MT3000-READ-UNVERIFIED', result['blockers'])
        self.assertNotIn('PRIVATE-SENTINEL', json.dumps(result))


class WorkerAndFileTests(unittest.TestCase):
    @contextmanager
    def environment(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); proc = root/'proc'; proc.mkdir()
            run = root/'run'; run.mkdir(); locks = proc/'locks'; locks.write_text('')
            firewall = root/'fw3.lock'; firewall.write_text('')
            with patch.object(platform, 'PROC_ROOT', proc), patch.object(platform, 'RUN_ROOT', run), \
                    patch.object(platform, 'RTP_LOCK', root/'rtp2.lock'), \
                    patch.object(platform, 'FIREWALL_LOCKS', (firewall,)):
                yield root, proc, locks, firewall

    def process(self, proc, name='unrelated', wchan='do_wait'):
        path = proc/'777'; path.mkdir()
        tail = ['0']*20; tail[0] = 'S'; tail[1] = '1'; tail[2] = '777'; tail[6] = '0'; tail[19] = '123'
        (path/'stat').write_text('777 (fixture) '+' '.join(tail)+'\n')
        (path/'cmdline').write_bytes(('/bin/sh\0/usr/bin/'+name+'\0').encode())
        (path/'wchan').write_text(wchan)
        return path

    def test_held_firewall_lock_by_unknown_process_is_busy(self):
        with self.environment() as (_, proc, locks, firewall):
            self.process(proc)
            metadata = firewall.stat()
            identity = '%x:%x:%d' % (os.major(metadata.st_dev), os.minor(metadata.st_dev), metadata.st_ino)
            locks.write_text('1: FLOCK ADVISORY WRITE 777 '+identity+' 0 EOF\n')
            self.assertGreater(platform._workers()['busy'], 0)

    def test_known_worker_unknown_waiter_and_stale_ownership_lock_are_busy(self):
        for worker, wait in [('rtp2.sh', 'do_wait'), ('vpn-failover-watcher.sh', 'do_wait'),
                             ('unknown', 'locks_lock_inode_wait')]:
            with self.environment() as (_, proc, _, _):
                self.process(proc, worker, wait)
                self.assertGreater(platform._workers()['busy'], 0)
        with self.environment() as (root, _, _, _):
            (root/'rtp2.lock').symlink_to(root/'missing')
            self.assertGreater(platform._workers()['busy'], 0)

    def test_only_the_proven_stale_rtp_lock_is_quiet_during_a_vendor_rebuild_proof(self):
        import rollback_recovery as recovery
        with self.environment() as (root, _, _, _):
            lock = root/'rtp2.lock'; lock.write_text('999999\n')  # dead pid, EXIT trap never ran
            self.assertGreater(platform._workers()['busy'], 0)
            with patch.object(recovery, 'VENDOR_LOCK', str(lock)), patch.object(recovery, 'ALLOWED_STALE_LOCK', [999999]):
                self.assertEqual(platform._workers()['busy'], 0)
                lock.write_text('999998\n'); self.assertGreater(platform._workers()['busy'], 0)
            with patch.object(recovery, 'ALLOWED_STALE_LOCK', [999999]):
                lock.write_text('999999\n'); self.assertGreater(platform._workers()['busy'], 0)  # other path: unproven

    def test_stock_hotplug_callback_is_busy_before_it_spawns_firewall_work(self):
        for event in ('iface', 'wireguard'):
            with self.environment() as (_, proc, _, _):
                path = self.process(proc)
                (path/'cmdline').write_bytes(('/bin/sh\0/sbin/hotplug-call\0'+event+'\0').encode())
                result = platform._workers()
                self.assertEqual(result['busy'], 1)
                self.assertIs(result['verified'], True)

    def test_malformed_locks_and_live_process_read_errors_are_unknown_not_quiet(self):
        with self.environment() as (_, _, locks, _):
            locks.write_text('PRIVATE-SENTINEL malformed lock')
            with self.assertRaises(ValueError):
                platform._workers()
        with self.environment() as (_, proc, _, _):
            path = self.process(proc); (path/'stat').write_text('malformed')
            with self.assertRaises(ValueError):
                platform._workers()

    def test_process_identity_change_and_global_deadline_refuse(self):
        with self.environment() as (_, proc, _, _):
            path = self.process(proc); original = platform._read; count = [0]
            def read(name, maximum=131072):
                value = original(name, maximum)
                if Path(name) == path/'stat':
                    count[0] += 1
                    if count[0] == 2:
                        return value.replace(b'123\n', b'124\n')
                return value
            with patch.object(platform, '_read', side_effect=read), self.assertRaises(ValueError):
                platform._workers()
            with patch.object(platform.time, 'monotonic', return_value=10), self.assertRaisesRegex(ValueError, 'DEADLINE'):
                platform._workers(deadline=9)

    def test_file_reads_reject_symlink_nonregular_and_oversize(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); value = root/'value'; value.write_bytes(b'12345')
            link = root/'link'; link.symlink_to(value)
            self.assertEqual(platform._read(value, 5), b'12345')
            for path, size in ((value, 4), (link, 8), (root, 8)):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    platform._read(path, size)


if __name__ == '__main__':
    unittest.main()
