"""HomenS.AI VPN - (C) 2026 Serhii Khomenko. End-to-end tick simulation of the channel-failure detector.

The packet-level channel model and the monitor/Auto timing of the offline study (private/math/detection/simulator.py,
calibrated on the MT3000 soak logs: DNS = one UDP datagram with a 3 s wait; HTTPS = 3 parallel requests of 6 egress
packets, SYN retransmits at 1/3/7 s, data at 0.6 s x (1, 3, 7, ...), wait 6 s normal / 3 s dense; ICMP heartbeat
once a second, 3 lost in a row = suspicion; Auto ticks every 2 s, APPLYING 3.5 s after the tick, traffic 1.3 s later)
driving the PRODUCT code: channel_model (the decision and the return gate over status-style samples, with the
`dense` flag the monitor publishes), probe_policy.Booster (dense episodes: heartbeat suspicion, the model's
suspicion, the model-decided episode end), the late-switch recheck rule (a newer healthy monitor sample, else one
live probe with the 1 s wait), pair_auto.return_hold (flap damping) and recovery_settings.stable_success.

Used by tests/test_hmm_detector.py (scenario outcomes) and tests/gen_hmm_detector_cases.py (sample streams the Lua
twin replays). `python3 hmm_tick_sim.py --table [n]` prints the before/after table of the design note.
The reserve is always healthy; only the primary is faulted.
"""
import bisect
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'files/usr/lib/homensai-vpn'))
import channel_model as C  # noqa: E402
import probe_policy  # noqa: E402

TICK = 2.0; APPLY = 3.5; MOVE = 1.3
NORMAL = 10.0; DENSE_MAX = 60.0
HTTP_NORMAL = 6.0; HTTP_DENSE = 3.0; DNS_WAIT = 3.0; PUBLISH_MIN = 2.5; RTT = 0.05
STEPS = 6; RTO = 0.6
MAX_AGE = 30.0           # observation_freshness.valid_for(interval 10)
PRIMARY = {'id': 'wireguard:peer_1', 'protocol': 'wireguard', 'interface': 'wgclient1',
           'vendor_tunnel_id': 'wireguard:wgclient1', 'vendor_generation': '01' * 16, 'vendor_changed_at': -1e6}
RESERVE = {'id': 'openvpn:1_1', 'protocol': 'openvpn', 'interface': 'ovpnclient1',
           'vendor_tunnel_id': 'openvpn:ovpnclient1', 'vendor_generation': '02' * 16, 'vendor_changed_at': -1e6}
RECOVERY = {'failures': 3, 'successes': 2, 'cooldown': 60, 'min_dwell': 60, 'primary_successes': 2,
            'primary_stable': 30, 'attempt_limit': 3, 'attempt_window': 15, 'return_policy': 'healthy_primary'}
# Integration 2.1.0-alpha8: rescue-tune changed the defaults (primary_stable 120 s; the Lua heartbeat suspects after 2 lost
# echoes, lua/fast_detect.lua M.LOSSES) - RECOVERY_MERGED/HB_LOSSES_MERGED are those shipped defaults. The reserve is
# always healthy here, so rescue_stable (a FAILED reserve) never applies in this simulation.
RECOVERY_MERGED = dict(RECOVERY, primary_stable=120)
HB_LOSSES = 3; HB_LOSSES_MERGED = 2


class Env:
    """Egress loss of the primary. windows [(a, b, p)]; blips [(a, b)] total loss; dns_block [(a, b)];
    d0 healthy DNS failure per sample, r0 per HTTPS request, hb0 ICMP loss (measured MT3000 rates)."""

    def __init__(self, rng, windows=(), blips=(), dns_block=(), d0=0.0008, r0=0.0004, hb0=0.002, base_loss=0.0):
        self.rng = rng; self.windows = list(windows); self.blips = sorted(blips)
        self._start = [a for a, _ in self.blips]; self.dns_block = list(dns_block)
        self.d0, self.r0, self.hb0, self.base = d0, r0, hb0, base_loss

    def p_at(self, t):
        p = self.base
        for a, b, q in self.windows:
            if a <= t < b: p = max(p, q)
        if self.blips:
            i = bisect.bisect_right(self._start, t) - 1
            if i >= 0 and t < self.blips[i][1]: return 1.0
        return p

    def lost(self, t):
        p = self.p_at(t)
        return p >= 1.0 or (p > 0 and self.rng.random() < p)


def https_request(env, s, wait):
    deadline = s + wait; t = None
    for off in (0.0, 1.0, 3.0, 7.0):
        if s + off + RTT > deadline: break
        if not env.lost(s + off): t = s + off + RTT; break
    if t is None: return False, wait
    for _ in range(STEPS - 1):
        sent = None; k = 0; off = 0.0
        while t + off + RTT <= deadline:
            if not env.lost(t + off): sent = t + off + RTT; break
            k += 1; off = RTO * (2 ** k - 1)
        if sent is None: return False, wait
        t = sent
    if env.r0 and env.rng.random() < env.r0: return False, wait
    return True, t - s


def probe(env, s, wait):
    """One monitor pass of the primary: (sample fields, published_at)."""
    dns_ok = not any(a <= s < b for a, b in env.dns_block) and not env.lost(s)
    if dns_ok and env.d0 and env.rng.random() < env.d0: dns_ok = False
    dt = RTT if dns_ok else DNS_WAIT; good = 0
    for _ in range(3):
        ok, sec = https_request(env, s, wait); good += ok; dt = max(dt, sec)
    code = 'VPN-003' if good < 2 else (None if dns_ok else 'DNS-001')
    return {'code': code, 'dns_ok': dns_ok, 'https_success': good}, s + max(PUBLISH_MIN, dt)


def sample(profile, t, fields, dense):
    row = {'id': profile['id'], 'time': t, 'rtt_ms': None, 'dense': dense}
    row.update(fields)
    for key in ('interface', 'vendor_tunnel_id', 'vendor_generation'): row[key] = profile[key]
    return row


class Memory:
    """In-memory files for probe_policy.Booster."""

    def __init__(self): self.files = {}
    def atomic_json(self, path, value): self.files[str(path)] = value
    def read_json(self, path, default): return self.files.get(str(path), default)


def run(env, model, start, end, rng, stop_after_switch=True, stop_after_return=False, stream=None, return_gate=True,
        recovery=None, hb_losses=HB_LOSSES):
    """Simulate the monitor + Auto for the faulted primary. Returns {'switches': [traffic moved s],
    'returns': [...], 'aborts': n, 'samples': n, 'dense': n, 'on_reserve': s, 'checks': [(t, failed, view)]}.
    stream: a list that receives (sample, publish time, Auto's decision) for every primary sample in source mode.
    return_gate=False leaves out channel_model.return_ready (only to measure what the gate changes).
    recovery / hb_losses: the recovery settings (default RECOVERY, primary_stable 30 s) and the heartbeat's lost echoes in a
    row that make a suspect (default 3, alpha7; 2 since rescue-tune)."""
    RECOVERY = recovery or globals()['RECOVERY']
    from pair_auto import return_hold
    from recovery_settings import stable_success
    settings = {'failure_model': model, 'interval': 10}
    mem = Memory()
    booster = probe_policy.Booster(Path('/run'), Path('/persist'), mem.atomic_json, mem.read_json)
    pair = {'source': PRIMARY['id'], 'target': RESERVE['id']}
    samples = []; events = []
    out = {'switches': [], 'returns': [], 'aborts': 0, 'samples': 0, 'dense': 0, 'on_reserve': 0.0}
    mode = 'source'; reserve_since = None; busy_until = -1e18
    tick_phase = rng.random() * TICK; beat_phase = rng.random()
    next_pass = start + rng.random() * NORMAL; pending = []; running_until = -1e18   # passes never overlap
    lost_run = 0; last_beat_lost = None; armed = True
    beat = math.floor(start) + beat_phase; next_tick = start + tick_phase
    reserve_row = lambda t: sample(RESERVE, t, {'code': None, 'dns_ok': True, 'https_success': 3}, False)
    while True:
        t = min(beat if mode == 'source' else 1e18, next_pass, min((p[0] for p in pending), default=1e18),
                next_tick if mode == 'reserve' else 1e18)
        if t >= end: break
        if mode == 'source' and t == beat:
            beat += 1.0
            if last_beat_lost is not None:
                if last_beat_lost: lost_run += 1
                else: lost_run = 0; armed = True
            last_beat_lost = env.lost(t) or rng.random() < env.hb0
            if armed and lost_run >= hb_losses:
                armed = False
                if booster.suspect(settings, [{'profile': PRIMARY['id'], 'reason': 'rx-stall'}], pair, 'OBSERVING', t):
                    next_pass = max(min(next_pass, t + 0.5), running_until)   # a running pass schedules the dense one
            continue
        if t == next_pass:
            dense = booster.dense(t) is not None
            fields, pub = probe(env, t, HTTP_DENSE if dense else HTTP_NORMAL)
            pending.append((pub, sample(PRIMARY, t, fields, dense)))
            out['samples'] += 1; out['dense'] += dense
            next_pass = max(t + booster.interval(settings, t), pub); running_until = pub
            continue
        if mode == 'reserve' and t == next_tick:
            next_tick += TICK
            if t < busy_until: continue
            visible = samples
            hold = return_hold(events, t, RECOVERY)
            if (t - reserve_since >= RECOVERY['min_dwell'] and (not events or t - events[-1] >= 60)
                    and (not return_gate or C.return_ready(visible, PRIMARY['id'], RECOVERY['primary_successes'], t, MAX_AGE, settings, PRIMARY))
                    and stable_success(visible, PRIMARY['id'], RECOVERY['primary_successes'], hold, t, MAX_AGE)):
                fields, _ = probe(env, t, HTTP_NORMAL)                       # recovery_ready: fresh live check
                if fields['code'] is None:
                    back = t + APPLY + MOVE
                    out['returns'].append(back); events.append(t); out['on_reserve'] += back - reserve_since
                    mode = 'source'; busy_until = back; lost_run = 0; armed = True
                    beat = math.floor(back) + beat_phase
                    if stop_after_return: break
            continue
        pending.sort(key=lambda p: p[0]); pub, row = pending.pop(0)
        samples.append(row)
        if len(samples) > 400: samples = [s for s in samples if pub - s['time'] <= C.WINDOW + 60]
        state = 'OBSERVING' if mode == 'source' and pub >= busy_until else 'COMMITTED'
        view = C.evaluate(samples, PRIMARY['id'], pub, MAX_AGE, model, PRIMARY) if model != 'consecutive' else None
        models = {PRIMARY['id']: C.public(view)} if view is not None else None
        booster.observe(settings, [row, reserve_row(row['time'])], pair, state, pub, models)
        if state != 'OBSERVING': continue
        if model == 'consecutive':
            want = C.channel_failed(samples, PRIMARY['id'], RECOVERY['failures'], pub, MAX_AGE, settings, PRIMARY)
        else:
            want = view['failed']
        if stream is not None: stream.append((row, pub, want))
        if not want: continue
        k = math.ceil((pub - tick_phase) / TICK); apply_t = tick_phase + k * TICK + APPLY
        if events and apply_t - events[-1] < 60: continue
        newer_ok = any(p[0] <= apply_t and p[1]['code'] is None for p in pending)
        if not newer_ok:
            fields, _ = probe(env, apply_t, 1.0)
            newer_ok = fields['code'] is None and row['code'] != 'VPN-MTU'
        if newer_ok: out['aborts'] += 1; continue
        moved = apply_t + MOVE
        out['switches'].append(moved); events.append(apply_t); events = [x for x in events if apply_t - x < 900]
        if stop_after_switch: break
        mode = 'reserve'; reserve_since = moved; busy_until = moved
        next_tick = tick_phase + math.ceil((moved - tick_phase) / TICK) * TICK
    if mode == 'reserve' and reserve_since is not None: out['on_reserve'] += end - reserve_since
    return out


def blips_env(rng, base=0.0, day=86400.0, per_day=12):
    blips = []; t = 0.0
    while True:
        t += rng.expovariate(per_day / day)
        if t >= day: break
        blips.append((t, t + rng.uniform(2, 12)))
    return Env(rng, blips=blips, base_loss=base)


def noisy_env(rng, day=86400.0):
    blips = []; t = 0.0
    while True:
        t += rng.expovariate(4 / 3600.0)
        if t >= day: break
        blips.append((t, t + min(15.0, rng.expovariate(1 / 5.0))))
    return Env(rng, blips=blips, d0=0.01, r0=0.005, hb0=0.01)


def flap_env(rng, down=60, up=120, cycles=10):
    return Env(rng, windows=[(i * (down + up), i * (down + up) + down, 1.0) for i in range(cycles)])


def fault(model, make, n, seed, end, **options):
    """P(switch) and the median / max traffic-moved time over n runs of one fault starting at 0."""
    rng = random.Random(seed); times = []
    for _ in range(n):
        r = run(make(rng), model, -40.0, end, rng, **options)
        if r['switches']: times.append(r['switches'][0])
    times.sort()
    return {'n': n, 'switched': len(times), 'p': len(times) / n,
            'median': times[len(times) // 2] if times else None, 'max': times[-1] if times else None}


BLACKOUTS = (5, 10, 15, 20, 25, 40, 150)
LOSSES = (0.10, 0.20, 0.30, 0.40, 0.50, 0.80)


def table(n=100):
    rows = []
    models = ('consecutive', 'hmm', 'hmm-fast')
    for L in BLACKOUTS:
        rows.append(['blackout %d s' % L] + [fault(m, lambda r, L=L: Env(r, windows=[(0, L, 1.0)]), n, 100 + L, max(L + 60.0, 100.0)) for m in models])
    for p in LOSSES:
        rows.append(['loss %d %% 150 s' % (p * 100)] + [fault(m, lambda r, p=p: Env(r, windows=[(0, 150, p)]), n, 200 + int(p * 100), 150.0) for m in models])
    print('| fault | ' + ' | '.join(models) + ' |'); print('|---|---|---|---|')
    for name, *cells in rows:
        print('| %s | %s |' % (name, ' | '.join('%.2f (%s)' % (c['p'], '%.1f' % c['median'] if c['median'] is not None else '-') for c in cells)))
    print()
    for name, make, days in (('flap 60/120 x10', lambda r: flap_env(r), None), ('healthy 24 h + 12 blips', lambda r: blips_env(r), 1),
                             ('noisy 24 h', noisy_env, 1), ('loss 30 % 24 h', lambda r: blips_env(r, 0.30), 1)):
        cells = []
        for m in models:
            rng = random.Random(9); sw = ret = 0; k = n // 20 if days is None else 1
            for _ in range(max(1, k)):
                r = run(make(rng), m, -40.0, 2400.0 if days is None else 86400.0 * days, rng, stop_after_switch=False)
                sw += len(r['switches']); ret += len(r['returns'])
            cells.append('%.1f / %.1f' % (sw / max(1, k), ret / max(1, k)))
        print('| %s (switches / returns per run) | %s |' % (name, ' | '.join(cells)))


# The three columns of the integration report: alpha7 as released, the merged defaults (HMM standard, primary_stable 120 s,
# heartbeat 2 lost echoes, return gate) and the merged fast preset.
MERGED_COLUMNS = (('alpha7 (3 in a row, 30 s, HB 3)', 'consecutive', dict(recovery=RECOVERY, hb_losses=HB_LOSSES, return_gate=False)),
                  ('merged default (hmm, 120 s, HB 2)', 'hmm', dict(recovery=RECOVERY_MERGED, hb_losses=HB_LOSSES_MERGED)),
                  ('merged hmm-fast', 'hmm-fast', dict(recovery=RECOVERY_MERGED, hb_losses=HB_LOSSES_MERGED)))


def table_merged(n=100):
    rows = []
    for L in BLACKOUTS:
        rows.append(['blackout %d s' % L] + [fault(m, lambda r, L=L: Env(r, windows=[(0, L, 1.0)]), n, 100 + L, max(L + 60.0, 100.0), **o) for _, m, o in MERGED_COLUMNS])
    for p in LOSSES:
        rows.append(['loss %d %% 150 s' % (p * 100)] + [fault(m, lambda r, p=p: Env(r, windows=[(0, 150, p)]), n, 200 + int(p * 100), 150.0, **o) for _, m, o in MERGED_COLUMNS])
    print('| fault | ' + ' | '.join(c[0] for c in MERGED_COLUMNS) + ' |'); print('|---|---|---|---|')
    for name, *cells in rows:
        print('| %s | %s |' % (name, ' | '.join('%.2f (%s)' % (c['p'], '%.1f' % c['median'] if c['median'] is not None else '-') for c in cells)))
    print()
    for name, make, days in (('flap 60/120 x10', lambda r: flap_env(r), None), ('healthy 24 h + 12 blips', lambda r: blips_env(r), 1),
                             ('noisy 24 h', noisy_env, 1), ('loss 30 % 24 h', lambda r: blips_env(r, 0.30), 1)):
        cells = []
        for _, m, o in MERGED_COLUMNS:
            rng = random.Random(9); sw = ret = 0; k = n // 20 if days is None else 1
            for _ in range(max(1, k)):
                r = run(make(rng), m, -40.0, 2400.0 if days is None else 86400.0 * days, rng, stop_after_switch=False, **o)
                sw += len(r['switches']); ret += len(r['returns'])
            cells.append('%.1f / %.1f' % (sw / max(1, k), ret / max(1, k)))
        print('| %s (switches / returns per run) | %s |' % (name, ' | '.join(cells)))


def return_delays(model, make, fault_end, n, seed, **options):
    """Median / P95 seconds from the end of the fault to the traffic being back on the primary (runs that switched)."""
    rng = random.Random(seed); delays = []
    for _ in range(n):
        r = run(make(rng), model, -40.0, fault_end + 1200.0, rng, stop_after_switch=False, stop_after_return=True, **options)
        if r['switches'] and r['returns']: delays.append(r['returns'][0] - fault_end)
    delays.sort()
    if not delays: return None
    return delays[len(delays) // 2], delays[min(len(delays) - 1, int(math.ceil(0.95 * len(delays))) - 1)], len(delays)


def table_return(n=100, thresholds=(0.95, 0.90)):
    """The return gate's threshold (channel_model.HEALTHY): return delay after a fault and switches a day at a
    persistent 30 % loss, for the merged defaults (primary_stable 120 s) and the design-note settings (30 s)."""
    faults = (('blackout 40 s', lambda r: Env(r, windows=[(0, 40, 1.0)]), 40.0, 140),
              ('loss 40 % 150 s', lambda r: Env(r, windows=[(0, 150, 0.40)]), 150.0, 240),
              ('loss 50 % 150 s', lambda r: Env(r, windows=[(0, 150, 0.50)]), 150.0, 250))
    saved = C.HEALTHY
    try:
        for label, recovery in (('primary_stable 120 s (merged default)', RECOVERY_MERGED), ('primary_stable 30 s (design note)', RECOVERY)):
            print('### %s, hmm standard: return delay median / P95 s (runs)' % label)
            print('| fault | ' + ' | '.join('P(G) >= %.2f' % h for h in thresholds) + ' |'); print('|---|' + '---|' * len(thresholds))
            for name, make, end, seed in faults:
                cells = []
                for h in thresholds:
                    C.HEALTHY = h
                    d = return_delays('hmm', make, end, n, seed, recovery=recovery, hb_losses=HB_LOSSES_MERGED)
                    cells.append('%.1f / %.1f (%d)' % d if d else '-')
                print('| %s | %s |' % (name, ' | '.join(cells)))
            cells = []
            for h in thresholds:
                C.HEALTHY = h; rng = random.Random(9)
                r = run(blips_env(rng, 0.30), 'hmm', -40.0, 86400.0, rng, stop_after_switch=False, recovery=recovery, hb_losses=HB_LOSSES_MERGED)
                cells.append('%d / %d (%.1f %% on reserve)' % (len(r['switches']), len(r['returns']), 100 * r['on_reserve'] / 86400.0))
            print('| persistent loss 30 %%, 24 h: switches / returns | %s |' % ' | '.join(cells))
            print()
    finally:
        C.HEALTHY = saved


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--table':
        table(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    elif len(sys.argv) > 1 and sys.argv[1] == '--merged':
        table_merged(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    elif len(sys.argv) > 1 and sys.argv[1] == '--return':
        table_return(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
