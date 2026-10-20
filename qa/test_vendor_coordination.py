"""Independent read-only observation -> current-member -> reserve-plan checks."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'router/files/usr/lib/homensai-vpn'))
from vendor_observation import VendorObserver
from failure_diagnosis import resolve_pair
from failover_plan import plan
from candidate_hierarchy import rank_candidates


def profile(identifier, logical, protocol='openvpn', provider='openvpn:10'):
    return dict(id=identifier, section=identifier.split(':', 1)[-1], name=identifier,
                protocol=protocol, interface=logical,
                vendor_tunnel_id=protocol+':'+logical if logical else None,
                vendor_profile_group_id=provider)


class CoordinationPipeline(unittest.TestCase):
    def setUp(self):
        self.observer = VendorObserver()
        self.settings = dict(plan_enabled=True, plan_source='openvpn:10_1',
                             plan_target='openvpn:10_2', interval=30,
                             plan_source_tunnel='openvpn:ovpnclient1',
                             plan_target_tunnel='openvpn:ovpnclient2')
        self.profiles = [profile('openvpn:10_1', 'ovpnclient1'),
                         profile('openvpn:10_2', 'ovpnclient2')]
        self.samples = []

    def data(self):
        return dict(settings=copy.deepcopy(self.settings), profiles=copy.deepcopy(self.profiles))

    def measurements(self, data, at):
        values = []
        for item in data['profiles']:
            if not item.get('interface'):
                continue
            source = item['vendor_tunnel_id'] == self.settings['plan_source_tunnel']
            values.append(dict(id=item['id'], time=at, device='tun'+item['interface'],
                               mark='0x10', table=100, ifindex=7,
                               code='VPN-003' if source else None,
                               dns_ok=True, https_success=0 if source else 2,
                               rtt_ms=20, exit_ip='203.0.113.1'))
        return values

    def scan(self, at, after=None, alter_measurements=None):
        before = self.data()
        measured = self.measurements(before, at)
        if alter_measurements:
            alter_measurements(measured)
        observation, clean = self.observer.observe(before, after or before, measured, at)
        rows = []
        for item in (after or before)['profiles']:
            row = dict(item)
            row.update(next((entry for entry in clean if entry['id'] == item['id']),
                            dict(code='PROFILE-INACTIVE')))
            rows.append(row)
        self.samples.extend(copy.deepcopy(clean))
        return dict(time=at, profiles=rows, samples=copy.deepcopy(self.samples),
                    vendor_observation=observation)

    def stable(self):
        status = None
        for at in (1000, 1030, 1060, 1090):
            status = self.scan(at)
        return status

    def test_same_provider_distinct_tunnels_are_channel_candidates(self):
        status = self.stable()
        answer = plan(status, self.settings, 1090)
        self.assertEqual(answer['state'], 'SWITCH-RECOMMENDED')
        self.assertEqual(answer['recommendation']['transition'], 'channel')
        self.assertFalse(answer['ready_to_apply'])
        self.assertIs(answer['coordination']['can_apply'], False)
        self.assertIsNone(answer['coordination']['vendor_attempts_exhausted'])

    def test_protocol_fallback_is_classified_from_actual_protocol(self):
        self.profiles[1] = profile('wireguard:peer_3', 'wgclient1', 'wireguard', 'wireguard:20')
        self.settings.update(plan_target='wireguard:peer_3', plan_target_tunnel='wireguard:wgclient1')
        answer = plan(self.stable(), self.settings, 1090)
        self.assertEqual(answer['state'], 'SWITCH-RECOMMENDED')
        self.assertEqual(answer['recommendation']['transition'], 'protocol')

    def test_editable_labels_cannot_change_transition_ownership(self):
        status = self.stable()
        for labels in (('same', 'same'), ('Ukraine', 'Germany'), ('', 'new name')):
            metadata = [dict(profile=item['id'], channel=label, priority=1, enabled=True)
                        for item, label in zip(self.profiles, labels)]
            rows = rank_candidates(status['profiles'], metadata, status['samples'],
                                   self.settings['plan_source'], 1090,
                                   observation=status['vendor_observation'])
            self.assertEqual([item['id'] for item in rows], ['openvpn:10_2'])
            self.assertEqual(rows[0]['transition'], 'channel')

    def test_same_tunnel_pair_is_vendor_owned_even_with_different_labels(self):
        status = self.stable()
        self.settings['plan_target_tunnel'] = self.settings['plan_source_tunnel']
        answer = plan(status, self.settings, 1090)
        self.assertEqual(answer['coordination']['code'], 'VENDOR-SAME-TUNNEL')
        self.assertIsNone(answer['recommendation'])

    def test_saved_tunnel_anchor_follows_new_member_without_old_health(self):
        self.stable()
        self.profiles[0]['interface'] = None
        self.profiles[0]['vendor_tunnel_id'] = None
        self.profiles.append(profile('openvpn:10_9', 'ovpnclient1'))
        status = self.scan(1120)
        self.assertIsNone(plan(status, self.settings, 1120)['recommendation'])
        for at in (1150, 1180):
            status = self.scan(at)
        pair = resolve_pair(status, self.settings, 1180)
        self.assertEqual(pair['source']['id'], 'openvpn:10_9')
        answer = plan(status, self.settings, 1180)
        self.assertEqual(answer['source'], 'openvpn:10_9')
        self.assertEqual(answer['configured_source'], 'openvpn:10_1')
        self.assertEqual(answer['state'], 'SWITCH-RECOMMENDED')

    def test_restart_cannot_borrow_ready_epochs_from_prior_monitor(self):
        self.stable()
        self.observer = VendorObserver()
        status = self.scan(1120)
        self.assertIsNone(plan(status, self.settings, 1120)['recommendation'])
        self.assertEqual(status['vendor_observation']['groups'][0]['state'], 'PENDING')

    def test_kernel_rebind_invalidates_successes_on_unchanged_profile(self):
        status = self.stable()
        old = status['profiles'][1]['vendor_generation']
        status = self.scan(1120, alter_measurements=lambda rows: rows[1].update(ifindex=8))
        self.assertNotEqual(status['profiles'][1]['vendor_generation'], old)
        self.assertIsNone(plan(status, self.settings, 1120)['recommendation'])

    def test_binding_change_during_measurements_strips_all_health_and_exit(self):
        self.stable()
        after = self.data()
        after['profiles'][0]['interface'] = None
        after['profiles'][0]['vendor_tunnel_id'] = None
        after['profiles'].append(profile('openvpn:10_9', 'ovpnclient1'))
        before = self.data()
        unused, clean = self.observer.observe(before, after, self.measurements(before, 1120), 1120)
        for key in ('dns_ok', 'https_success', 'rtt_ms', 'exit_ip'):
            self.assertNotIn(key, clean[0])

    def test_wan_failure_and_stale_evidence_never_recommend_a_reserve(self):
        baseline = self.stable()
        status = copy.deepcopy(baseline)
        status['uplink_observation'] = dict(state='DOWN', time=1090)
        self.assertIsNone(plan(status, self.settings, 1090)['recommendation'])
        self.assertIsNone(plan(baseline, self.settings, 2000)['recommendation'])

    def test_duplicate_active_binding_is_unknown_instead_of_last_wins(self):
        self.stable()
        self.profiles.append(profile('openvpn:10_9', 'ovpnclient1'))
        status = self.scan(1120)
        self.assertIsNone(plan(status, self.settings, 1120)['recommendation'])
        group = next(item for item in status['vendor_observation']['groups']
                     if item['id'] == 'openvpn:ovpnclient1')
        self.assertEqual(group['state'], 'UNKNOWN')

    def test_inventory_secrets_never_enter_identity_events(self):
        self.profiles[0].update(password='PRIVATE_SENTINEL', endpoint='PRIVATE_SENTINEL')
        status = self.stable()
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(status['vendor_observation']))
        self.assertTrue(all(item['cause'] == 'UNOBSERVED'
                            for item in status['vendor_observation']['events']))

    def test_duplicate_conflicting_and_future_sample_cannot_make_reserve_ready(self):
        baseline = self.stable()
        for mode in ('duplicate-conflict', 'future', 'old-generation', 'missing-identity'):
            status = copy.deepcopy(baseline)
            candidates = [item for item in status['samples'] if item['id'] == 'openvpn:10_2']
            if mode == 'duplicate-conflict':
                status['samples'].append(dict(candidates[-1], code='DNS-001'))
            elif mode == 'future':
                for item in candidates:
                    item['time'] = 1091
            elif mode == 'old-generation':
                for item in candidates:
                    item['vendor_generation'] = '0'*32
            else:
                for item in candidates:
                    item.pop('vendor_tunnel_id', None)
            with self.subTest(mode=mode):
                self.assertIsNone(plan(status, self.settings, 1090)['recommendation'])


if __name__ == '__main__':
    unittest.main()
