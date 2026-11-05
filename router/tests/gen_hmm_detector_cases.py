"""HomenS.AI VPN - (C) 2026 Serhii Khomenko. Generates tests/hmm_detector_cases.json from the Python reference
(files/usr/lib/homensai-vpn/channel_model.py). The Lua twin (lua/channel_model.lua) must reproduce every number
within 1e-9 and every decision exactly: tests/lua/test_hmm_detector.lua; tests/test_hmm_detector.py checks that
this file is up to date. Run: python3 router/tests/gen_hmm_detector_cases.py [--write]
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'files/usr/lib/homensai-vpn'))
sys.path.insert(0, str(HERE))
import channel_model as C  # noqa: E402

TARGET = HERE / 'hmm_detector_cases.json'
PROFILE = {'id': 'wireguard:peer_1', 'protocol': 'wireguard', 'interface': 'wgclient1',
           'vendor_tunnel_id': 'wireguard:wgclient1', 'vendor_generation': '01' * 16, 'vendor_changed_at': 1000}
OTHER_GENERATION = '03' * 16
CODES = {'O': (None, True, 3), 'D': ('DNS-001', False, 3), 'H': ('VPN-003', True, 0), 'M': ('VPN-MTU', True, 3),
         'T': ('VPN-001', False, 0), 'C': ('CHECK-001', None, None), 'R': ('ROUTE-001', None, None)}


def row(t, kind, dense=None, gen=None, ident=None, https=None):
    code, dns, good = CODES[kind]
    out = {'t': t, 'code': code, 'dns_ok': dns, 'https': good if https is None else https}
    if dense is not None: out['dense'] = dense
    if gen is not None: out['gen'] = gen
    if ident is not None: out['id'] = ident
    return out


def sample(r):
    """A status.json sample of PROFILE from a compact case row (the Lua test builds the same)."""
    s = {'id': r.get('id', PROFILE['id']), 'time': r['t'], 'code': r['code'], 'dns_ok': r['dns_ok'],
         'https_success': r['https'], 'interface': PROFILE['interface'], 'vendor_tunnel_id': PROFILE['vendor_tunnel_id'],
         'vendor_generation': r.get('gen', PROFILE['vendor_generation'])}
    if 'dense' in r: s['dense'] = r['dense']
    return s


def view(v):
    if v is None: return None
    return {k: v[k] for k in ('pi', 'time', 'observations', 'persist', 'p_bad', 'p_healthy', 'remaining', 'failed', 'suspect', 'healthy')}


def series(start, step, kinds, dense=None):
    return [row(start + i * step, k, dense) for i, k in enumerate(kinds)]


def evaluate_cases():
    cases = []

    def add(name, rows, now, model='hmm', max_age=30, profile=True):
        samples = [sample(r) for r in rows]
        v = C.evaluate(samples, PROFILE['id'], now, max_age, model, PROFILE if profile else None)
        cases.append({'name': name, 'rows': rows, 'now': now, 'max_age': max_age, 'model': model, 'profile': profile, 'expect': view(v)})

    healthy = series(1100, 10, 'OOOO')
    add('healthy channel', healthy, 1135)
    add('healthy channel, fast preset', healthy, 1135, 'hmm-fast')
    add('one DNS failure on a healthy channel', healthy + series(1140, 10, 'DOO'), 1165)
    # a 15 s and a 20 s blackout seen by dense passes (4 s), then healthy: never decided
    for model in ('hmm', 'hmm-fast'):
        add('blackout 15 s, dense, ' + model, healthy + [row(1141.5, 'H', False)] + series(1147.5, 4, 'HHH', True) + series(1159.5, 4, 'OO', True), 1165, model)
        add('blackout 20 s at its last failure, ' + model, healthy + [row(1141.5, 'H', False)] + series(1147.5, 4, 'HHHH', True), 1165, model)
        add('blackout 40 s, dense, ' + model, healthy + [row(1141.5, 'H', False)] + series(1147.5, 4, 'HHHHHHHH', True), 1180.5, model)
    add('the same blackout without the dense flag (inferred from the 4 s gap)',
        healthy + [row(1141.5, 'H')] + series(1147.5, 4, 'HHHHHHHH'), 1180.5)
    add('DNS dead (DNS-001 every 10 s)', healthy + series(1140, 10, 'DDDDDD'), 1195)
    add('20 % loss pattern (O O D O D O O D O O)', healthy + series(1140, 10, 'OODODOODOO'), 1235)
    add('50 % loss pattern', healthy + series(1140, 10, 'HODHHOHDHO'), 1235)
    add('VPN-MTU black hole every 10 s', healthy + series(1140, 10, 'MMM'), 1165)
    add('VPN-001 tunnel down', healthy + series(1140, 10, 'TTT'), 1165)
    add('codes that are no observation are skipped', healthy + series(1140, 10, 'HCRH'), 1175)
    add('newest sample is no observation (CHECK-001): no decision', healthy + series(1140, 10, 'HHHC'), 1175)
    add('newest observation stale: no decision', healthy + series(1140, 10, 'HHHH'), 1210)
    add('the window keeps 600 s only', series(400, 10, 'H' * 30) + series(1050, 10, 'OOO'), 1080, profile=False)
    add('gap longer than 600 s is clamped', [row(100, 'H'), row(1000, 'H'), row(1010, 'H')], 1015, profile=False)
    add('a sample from the future is ignored', healthy + series(1140, 10, 'HH') + [row(1300, 'O')], 1155)
    add('duplicate stamps with the same health count once', healthy + series(1140, 10, 'HH') + [row(1150, 'H')], 1155)
    add('duplicate stamps that disagree: unknown', healthy + series(1140, 10, 'HH') + [row(1150, 'O')], 1155)
    add('duplicate stamps that disagree, without a profile: no view', healthy + series(1140, 10, 'HH') + [row(1150, 'O')], 1155, profile=False)
    add('another generation is not this channel', healthy + [dict(row(1140 + 10 * i, 'H'), gen=OTHER_GENERATION) for i in range(4)], 1175)
    add('samples before vendor_changed_at are not this binding', series(900, 10, 'HHHHHHHHH') + healthy, 1135)
    add('https_success 2 is healthy, 1 is not an observation without a code',
        [row(1100, 'O', https=2), dict(row(1110, 'O'), https=1), row(1120, 'O')], 1125)
    add('no samples', [], 1100)
    add('consecutive has no model view', healthy, 1135, 'consecutive')
    add('max_age 0 is refused', healthy, 1135, max_age=0)
    return cases


def step_cases():
    rng = random.Random(20261103)
    cases = []
    for model in ('hmm', 'hmm-fast'):
        p = C.params(model)
        for n in range(10):
            pi = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]; seq = []; pis = []; persist = []
            for _ in range(40):
                dt = rng.choice([0.0, 0.3, 2.5, 4.0, 6.0, 10.0, 10.5, 30.0, 600.0])
                obs = rng.choice([0, 0, 0, 1, 2, 2]); dense = rng.random() < 0.4
                pi = C.step(pi, dt, obs, dense, p)
                seq.append([dt, obs, dense]); pis.append(pi); persist.append(C.persist(pi, p))
            cases.append({'model': model, 'seq': seq, 'pi': pis, 'persist': persist, 'remaining': C.remaining(pi, p)})
    return cases


def decision_cases():
    out = {'channel_failed': [], 'return_ready': []}
    healthy = series(1100, 10, 'OOOO')
    for name, rows, now in (('three VPN-003 10 s apart', healthy + series(1140, 10, 'HHH'), 1165),
                            ('two VPN-003', healthy + series(1140, 10, 'HH'), 1155),
                            ('three DNS-001', healthy + series(1140, 10, 'DDD'), 1165),
                            ('a 15 s blackout in dense passes (three failures in a row)', healthy + [row(1141.5, 'H', False)] + series(1147.5, 4, 'HH', True), 1158),
                            ('five DNS-001', healthy + series(1140, 10, 'DDDDD'), 1185)):
        for model in ('consecutive', 'hmm', 'hmm-fast'):
            samples = [sample(r) for r in rows]
            out['channel_failed'].append({'name': name, 'model': model, 'rows': rows, 'now': now, 'count': 3, 'max_age': 30,
                                          'expect': C.channel_failed(samples, PROFILE['id'], 3, now, 30, {'failure_model': model}, PROFILE)})
    recovered = series(1100, 10, 'OOO') + series(1130, 10, 'H' * 12) + series(1250, 10, 'OOOO')
    lossy = series(1100, 10, 'ODOODOOODOODOOOD') + series(1260, 10, 'O' * 32)
    for name, rows, now in (('after a long outage, four healthy samples', recovered, 1285),
                            ('light loss, then 310 s of healthy samples (stable 300 s)', lossy, 1575),
                            ('light loss, then 200 s healthy only', lossy[:-11], 1465),
                            ('nothing fresh', recovered, 1500)):
        for model in ('consecutive', 'hmm', 'hmm-fast'):
            samples = [sample(r) for r in rows]
            out['return_ready'].append({'name': name, 'model': model, 'rows': rows, 'now': now, 'count': 2, 'max_age': 30,
                                        'expect': C.return_ready(samples, PROFILE['id'], 2, now, 30, {'failure_model': model}, PROFILE)})
    return out


def stream_cases():
    """Sample streams of the tick simulation: the Lua twin must take Auto's decision at the same publications."""
    import hmm_tick_sim as H
    out = []
    for name, model, make, seed in (('blackout 15 s', 'hmm', lambda r: H.Env(r, windows=[(0, 15, 1.0)]), 1),
                                    ('blackout 20 s', 'hmm', lambda r: H.Env(r, windows=[(0, 20, 1.0)]), 2),
                                    ('blackout 40 s', 'hmm', lambda r: H.Env(r, windows=[(0, 40, 1.0)]), 3),
                                    ('blackout 40 s, fast', 'hmm-fast', lambda r: H.Env(r, windows=[(0, 40, 1.0)]), 3),
                                    ('blackout 20 s, previous rule', 'consecutive', lambda r: H.Env(r, windows=[(0, 20, 1.0)]), 2),
                                    ('loss 40 %', 'hmm', lambda r: H.Env(r, windows=[(0, 150, 0.4)]), 4),
                                    ('loss 20 %', 'hmm', lambda r: H.Env(r, windows=[(0, 150, 0.2)]), 5),
                                    ('DNS blocked', 'hmm', lambda r: H.Env(r, dns_block=[(0, 150)]), 6)):
        rng = random.Random(seed); stream = []
        H.run(make(rng), model, -40.0, 160.0, rng, stream=stream)
        rows = []; decisions = []
        for s, pub, want in stream:
            r = {'t': round(s['time'], 6), 'code': s['code'], 'dns_ok': s['dns_ok'], 'https': s['https_success'], 'dense': s['dense']}
            rows.append(r); decisions.append([round(pub, 6), want])
        # re-evaluate with the rounded stamps (what the JSON carries)
        samples = []; checked = []
        for r, (pub, _) in zip(rows, decisions):
            samples.append(sample(r))
            checked.append([pub, C.channel_failed(samples, PROFILE['id'], 3, pub, 30, {'failure_model': model},
                                                  dict(PROFILE, vendor_changed_at=-1e6))])
        final = C.evaluate(samples, PROFILE['id'], decisions[-1][0], 30, model) if model != 'consecutive' else None
        out.append({'name': name, 'model': model, 'rows': rows, 'decisions': checked, 'final': view(final)})
    return out


def misc_cases():
    names = [[None, 'hmm'], ['hmm', 'hmm'], ['hmm-fast', 'hmm-fast'], ['consecutive', 'consecutive'], ['HMM', 'hmm'],
             ['streak', 'hmm'], [3, 'hmm'], ['', 'hmm']]
    publics = []
    for v in ({'model': 'hmm', 'pi': [0, 0, 0, 0, 0, 0], 'time': 1100.5, 'observations': 7, 'persist': 0.123456, 'p_bad': 0.98765,
               'p_healthy': 0.0123449, 'remaining': 812.3456, 'failed': False, 'suspect': True, 'healthy': False},
              {'model': 'hmm-fast', 'pi': [0, 0, 0, 0, 0, 0], 'time': None, 'observations': 0, 'persist': 0.0, 'p_bad': 0.0,
               'p_healthy': 1.0, 'remaining': 0.04, 'failed': False, 'suspect': False, 'healthy': False}):
        publics.append({'view': v, 'expect': C.public(v)})
    rows = series(1100, 10, 'OOOHHH')
    samples = [sample(r) for r in rows] + [dict(sample(row(1150, 'O')), vendor_generation=OTHER_GENERATION)]
    measured = dict(PROFILE)
    row_views = [{'model': m, 'rows': rows, 'other_generation_at': 1150, 'now': 1155, 'max_age': 30,
                  'expect': C.row_view(samples, measured, 1155, 30, {'failure_model': m})} for m in ('hmm', 'hmm-fast', 'consecutive')]
    return {'names': names, 'public': publics, 'row_view': row_views}


def constants():
    out = {}
    for model in ('hmm', 'hmm-fast'):
        p = C.params(model)
        out[model] = {k: p[k] for k in ('theta', 'dur', 'total', 'ratio', 'weight')}
    out['module'] = {k: getattr(C, k) for k in ('COST', 'SUSPECT', 'HEALTHY', 'CLEAN', 'FLOOR', 'WINDOW', 'FIRST_DT', 'DT_MAX',
                                                 'DENSE_GAP', 'HTTP_NORMAL', 'HTTP_DENSE', 'DNS_WAIT', 'PUBLISHED')}
    out['EMIS'] = C.EMIS; out['LAM'] = C.LAM
    return out


def build():
    return {'_comment': 'Generated by tests/gen_hmm_detector_cases.py from channel_model.py; do not edit. '
                        'Rows: t = sample time, https = https_success, dense optional, gen = another vendor generation.',
            'profile': PROFILE, 'other_generation': OTHER_GENERATION, 'tolerance': 1e-9, 'constants': constants(),
            'steps': step_cases(), 'evaluate': evaluate_cases(), **decision_cases(), **misc_cases(), 'streams': stream_cases()}


def text():
    return json.dumps(build(), indent=1, sort_keys=True) + '\n'


if __name__ == '__main__':
    if '--write' in sys.argv:
        TARGET.write_text(text(), encoding='utf-8', newline='\n')
        print('written', TARGET)
    else:
        print(text())
