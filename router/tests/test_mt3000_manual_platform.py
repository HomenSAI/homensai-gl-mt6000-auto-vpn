"""Candidate readiness must never become route permission or a LAN certificate."""
import copy
import json
from pathlib import Path
import sys
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


if __name__ == '__main__':
    unittest.main()
