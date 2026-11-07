"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
Embed the master-slider curve of the offline studies (private/math/master-slider/curve.json, 03.11.2026, and
private/math/master-slider-fast, 04.11.2026) into the package as the compact lookup table
router/files/usr/lib/homensai-vpn/slider_curve.json (read by advisor.py and lua/advisor.lua). The 11 anchors (parameters,
predicted metrics, per-group numbers), the alpha8 default marker and the steps t < 0 (fast_anchors) are kept; numbers are
rounded to 4 decimals.

    python scripts/gen-slider-curve.py <study curve.json> --fast <folder of master-slider-fast> [--check]

The fast study ran on other seed sets, so its anchors enter as paired differences to its own t = 0, added to the row t = 0 of
the curve (a step never jumps just because of the seeds). The per-group numbers are the mean per event of the study's
scenarios (stageH.jsonl) with the rates of msim.MIX, as in master-slider/analyze.py. Two values follow the product, not the
study: theta stops at its product minimum 0.5 and the dense interval at 3 s (owner decision: turbo = DENSE_INTERVAL 3 s; with
"2 in a row" and the heartbeat verdict the model never decides first there, see docs/architecture/FAST-SWITCH-2026-11-04.ru.md).
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode=True
TARGET = Path(__file__).resolve().parents[1]/'router/files/usr/lib/homensai-vpn/slider_curve.json'
PARAMS = ('theta', 'dur_b', 'losses', 'pg', 'primary_stable', 'rescue_stable')
METRICS = ('downtime_s_day', 'unnecessary_per_day', 'failovers_per_day', 'switch_after_s', 'rides_out_s',
           'return_after_40s_blackout_s', 'reserve_failure_worst_downtime_s')
GROUPS = ('short', 'medium', 'long', 'loss_light', 'loss_heavy', 'flap', 'reserve_fail', 'noisy')
FAST_PARAMS = ('cons_f', 'beat_k', 'dense_interval')
THETA_MIN = 0.5    # channel_model.NUMERIC
TURBO_DENSE = 3    # probe_policy.TURBO_DENSE
# master-slider/analyze.py GROUPS: the scenarios of each group
SCENARIOS = {'short': ('blackout:5', 'blackout:10', 'blackout:15', 'microblip:2', 'microblip:4', 'microblip:7', 'microblip:12'),
             'medium': ('blackout:20', 'blackout:30', 'blackout:45'),
             'long': ('blackout:60', 'blackout:90', 'blackout:120', 'blackout:150'),
             'loss_light': ('loss:5', 'loss:10', 'loss:20', 'ge:light', 'ploss:20'),
             'loss_heavy': ('loss:30', 'loss:50', 'loss:80', 'ge:heavy', 'ploss:30', 'dns:150'),
             'flap': ('flap:10/20/20', 'flap:60/120/10'),
             'reserve_fail': ('reservefail:150', 'reservefail:450', 'reservefail:600'),
             'noisy': ('noisy:3600',)}
FAST_METRICS = {'downtime_s_day': 'downtime_s_day', 'unnecessary_per_day': 'unnecessary_per_day', 'failovers_per_day': 'failovers_per_day',
                'switch_after_s': 'switch_40_s', 'rides_out_s': 'rides_out_s', 'reserve_failure_worst_downtime_s': 'reserve_failure_worst_downtime_s'}


def r4(x):
    if x is None:return None
    value = round(float(x), 4)
    return int(value) if value == int(value) else value


def group_means(folder, rate):
    """{t: {group: [downtime, unnecessary] per event}} of the study's final anchor runs (return 120 s)."""
    runs = {}
    for line in (Path(folder)/'stageH.jsonl').read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        runs.setdefault(round(row['v']['t'], 2), []).append(row['rows'][0]['sc'])
    out = {}
    for t, sets in runs.items():
        out[t] = {}
        for group, names in SCENARIOS.items():
            weight = sum(rate[n] for n in names)
            out[t][group] = [sum(rate[n]*s[n][k] for n in names for s in sets)/(weight*len(sets)) for k in (0, 4)]
    return out


def mean(value):
    """The study's value [mean, 95 % half-width], or a plain number."""
    return value[0] if isinstance(value, list) else value


def fast_anchors(base, folder):
    """The steps t < 0 on top of the row t = 0 of the curve (paired differences to the study's own t = 0)."""
    sys.path.insert(0, str(Path(folder).parent/'master-slider'))
    import msim
    rate = {n: w for n, w, _ in msim.MIX}
    means = group_means(folder, rate)
    study = json.loads((Path(folder)/'curve-fast.json').read_text(encoding='utf-8'))['anchors']
    zero = next(a for a in study if a['t'] == 0)
    row = base['anchors'][0]
    out = []
    for a in sorted((x for x in study if x['t'] < 0), key=lambda x: -x['t']):
        params = dict(a['params'], theta=max(a['params']['theta'], THETA_MIN))
        metric = []
        for name in METRICS:
            value = row['predicted'].get(name)
            key = FAST_METRICS.get(name)
            if key is not None and value is not None:value = max(0.0, value+mean(a['predicted'][key])-mean(zero['predicted'][key]))
            metric.append(r4(value))
        groups = []
        for g in GROUPS:
            mine, ref = means[round(a['t'], 2)][g], means[0.0][g]
            groups.append([r4(max(0.0, row['groups'][g]['downtime']+mine[0]-ref[0])), r4(max(0.0, row['groups'][g]['unnec']+mine[1]-ref[1]))])
        beat = a['params']['beat_k']
        out.append({'t': r4(a['t']), 'p': [r4(params[k]) for k in PARAMS], 'm': metric, 'g': groups,
                    'x': [a['params']['cons_f'], beat, TURBO_DENSE if beat is not None else a['params']['dense_interval']]})
    return out


def build(curve, folder=None):
    anchors = []
    for a in curve['anchors']:
        anchors.append({'t': r4(a['t']), 'p': [r4(a['params'][k]) for k in PARAMS],
                        'm': [r4(a['predicted'].get(k)) for k in METRICS],
                        'g': [[r4(a['groups'][g]['downtime']), r4(a['groups'][g]['unnec'])] for g in GROUPS]})
    default = next(m for m in curve['markers'] if m['label'] == 'default')
    return {'about': 'HomenS.AI Auto VPN master slider (fast reaction t=0 .. no unnecessary switches t=1): the 11 anchors '
                     'of the offline study private/math/master-slider (03.11.2026, MT3000-calibrated model, not router '
                     'measurements) and the steps t<0 of private/math/master-slider-fast (04.11.2026). Generated by '
                     'scripts/gen-slider-curve.py; do not edit by hand.',
            'version': curve['version'], 'lambda_s': r4(curve['auto_adapt']['lambda_s_per_unnecessary_switch']),
            'steps': {k: r4(curve['steps'][k]) for k in PARAMS}, 'params': list(PARAMS), 'metrics': list(METRICS),
            'groups': list(GROUPS), 'anchors': anchors, 'fast_params': list(FAST_PARAMS),
            'fast_anchors': fast_anchors(curve, folder) if folder else [],
            'alpha8': {'p': [r4(default['settings'][k]) for k in PARAMS],
                       'm': [r4(default['predicted'].get(k)) for k in METRICS]}}  # the study has no ride/leave for it


def text(curve, folder=None):
    return json.dumps(build(curve, folder), ensure_ascii=True, separators=(',', ':'), sort_keys=True) + '\n'


def main():
    if len(sys.argv) < 2:raise SystemExit(__doc__)
    folder = sys.argv[sys.argv.index('--fast')+1] if '--fast' in sys.argv else None
    want = text(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')), folder)
    if '--check' in sys.argv[2:]:
        raise SystemExit(0 if TARGET.read_text(encoding='utf-8') == want else 'slider_curve.json is not current')
    with open(TARGET, 'w', encoding='utf-8', newline='\n') as f:f.write(want)
    print(TARGET, len(want), 'bytes')


if __name__ == '__main__':
    main()
