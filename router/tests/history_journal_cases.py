"""Generated switch-history inputs for the journal tests (schema 2, HISTORY-JOURNAL-2026-11-01.ru.md).

events(seed, count, start) -> [(value, now)]: what native_switch hands History.record over a week of a busy pair -
switch transactions (ARMED, APPLYING, WAIT-CLIENT, COMMITTED, sometimes RESTORING/ROLLED-BACK) with phase evidence,
rule orders, probe evidence, the destination's saved HTTPS RTT, plus BLOCKED runs and repeated observations (which
the writer deduplicates). The MT3000 history of 30 Oct 2026 had 1288 events in 7 days, about 1 MB.
"""
import random

PAIRS = [('wireguard:peer_7', 'openvpn:1_2'), ('wireguard:peer_9', 'openvpn:1_2'), ('openvpn:1_3', 'wireguard:peer_7')]
RULES = ['vpn_rule_%d' % index for index in range(12)]


def _interface(profile):
    return 'wgclient1' if profile.startswith('wireguard:') else 'ovpnclient2'


def _switch(rng, now, source, target, manual, trial):
    """One transaction: [(value, now)]; the time advances by seconds between phases."""
    out = []
    phases = []
    before = rng.sample(RULES, rng.choice([4, 6, 8]))
    after = list(reversed(before))
    base = {'source': source, 'target': target, 'proof_scope': 'router-probed-ipv4', 'trial': trial,
            'transition_source': 'manual' if manual else 'automatic', 'mode': 'continuous-pair'}
    if manual:
        base['manual'] = True
    restore = rng.random() < 0.2
    plan = ['ARMED', 'APPLYING', 'WAIT-CLIENT', 'COMMITTED'] + (['RESTORING', 'ROLLED-BACK'] if restore else [])
    for state in plan:
        now += rng.choice([0.25, 1.5, 3.75, 12.0, 30.5])
        phases.append({'phase': state, 'time': now - 0.125})
        value = dict(base, state=state, reason='OPERATOR-MANUAL' if manual else 'SOURCE-FAILED',
                     phase_evidence=[dict(row) for row in phases])
        if state != 'ARMED':
            value.update(before_order=list(before), after_order=list(after), route_changed=True)
            value['probe_evidence'] = {'source_streak_met': True, 'required_failures': 3, 'required_successes': 2}
        if state == 'COMMITTED':
            value.update(transition_completed=True, transition_outcome='committed', transition_kind=rng.choice(['server', 'channel', 'protocol']),
                         destination_role='target', destination_profile_id=target, from_role='source', from_profile_id=source,
                         transition_metadata_present=True)
            if rng.random() < 0.8:
                value['latency'] = {'profile': target, 'metric': 'https-rtt-ms', 'time': now - 2.0,
                                    'rtt_ms': round(rng.uniform(20, 300), 1), 'interface': _interface(target),
                                    'generation': '%032x' % rng.getrandbits(128)}
        if state == 'RESTORING':
            value.update(transition_metadata_present=True, destination_role='source', destination_profile_id=source,
                         reason='PRIMARY-STABLY-RECOVERED')
        if state == 'ROLLED-BACK':
            value.update(transition_completed=True, transition_outcome='restored', original_restored=True,
                         from_role='target', from_profile_id=target, destination_role='source', destination_profile_id=source,
                         reason='PRIMARY-STABLY-RECOVERED', restored_order=list(before), transition_metadata_present=True)
        out.append((value, now))
    return out, now


def events(seed, count, start, spacing=465.0):
    """About count recorded events (each value is a new event except the deliberate repeats)."""
    rng = random.Random(seed)
    now = start
    out = []
    while len(out) < count:
        source, target = rng.choice(PAIRS)
        kind = rng.random()
        if kind < 0.6:
            rows, now = _switch(rng, now, source, target, manual=rng.random() < 0.1, trial=rng.random() < 0.05)
            out.extend(rows)
        elif kind < 0.8:
            blockers = sorted(rng.sample(['PAIR-RATE-LIMIT', 'TARGET-UNHEALTHY', 'OBSERVATION-STALE', 'VPN-003'], rng.choice([1, 2])))
            for _ in range(rng.choice([1, 2, 3])):
                now += 30.0
                out.append(({'state': 'BLOCKED', 'blockers': blockers, 'source': source, 'target': target,
                             'proof_scope': 'router-probed-ipv4'}, now))
        else:
            value = {'state': rng.choice(['OBSERVING', 'DEGRADED-ON-RESERVE', 'STOPPED']), 'reason': 'PAIR-WATCHING',
                     'source': source, 'target': target, 'proof_scope': 'router-probed-ipv4'}
            if value['state'] == 'STOPPED':
                value.update(control_action='stop', control_source='manual', control_time=now)
            out.append((value, now + 1.0))
            out.append((dict(value), now + 11.0))  # the same publication again: no new event
            now += 11.0
        now += rng.expovariate(1.0/spacing)
    return out[:count]
