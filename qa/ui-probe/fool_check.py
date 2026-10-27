"""Evaluates the "clueless user" persona results: out-of-range values the page was willing to send, script errors, storms of calls,
event-loop lags, leaks. Bounds mirror the backend validators (router/files/usr/lib/homensai-vpn)."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'router/files/usr/lib/homensai-vpn'))
try:
    from recovery_settings import RANGES as RECOVERY
except Exception:  # the check still works without the recovery table
    RECOVERY = {}
BOUNDS = {
    'setup_telegram': {'interval': (5, 10080), 'hour': (0, 23)},
    'setup_system': {'interval': (10, 300), 'duration': (1, 240)},
    'setup_speed': {'budget_mib': (1, 32), 'duration': (2, 15), 'streams': (1, 4), 'daily_mib': (1, 1024), 'busy_mbps': (1, 1000)},
    'setup_monitor': {'interval': (10, 300), 'checkpoint': (300, 3600), 'probe_limit': (1, 16),'live_log_limit':(1,2000),'history_days':(1,7)},
    'setup_recovery': dict({k: tuple(v) for k, v in RECOVERY.items()},interval=(10,300)),
    'speed_start': {'budget_mib': (1, 32), 'duration': (2, 15), 'streams': (1, 4)},
    'fault_start': {'duration': (1, 180)},
}


def out_of_range(call):
    """[(method, parameter, value)] for numeric parameters outside the backend's range or not whole numbers."""
    method, params, args = call.get('m'), call.get('p') or [], call.get('a') or []
    bad = []
    for name, value in zip(params, args):
        low_high = BOUNDS.get(method, {}).get(name)
        if low_high is None:
            continue
        if type(value) is not int or isinstance(value, bool) or not low_high[0] <= value <= low_high[1]:
            bad.append((method, name, value))
    return bad


def summarise(results):
    errors = Counter();bad_values = defaultdict(Counter);storms = [];lags = [];growth = [];dead = [];overflow = []
    per_kind = defaultdict(lambda: Counter())
    for r in results:
        if r.get('error') or r.get('fatal'):
            dead.append((r.get('cfg'), r.get('error') or r['fatal']));continue
        kind = r.get('kind')
        per_kind[kind]['personas'] += 1
        per_kind[kind]['clicks'] += r.get('clicks', 0)
        per_kind[kind]['typed'] += r.get('typed', 0)
        per_kind[kind]['calls'] += r.get('callCount', 0)
        for e in r.get('errors', []):
            errors[e[:110]] += 1
        for c in r.get('calls', []):
            for method, name, value in out_of_range(c):
                bad_values[method+'.'+name][repr(value)[:40]] += 1
        if r.get('callCount', 0) > 150:
            storms.append((r['persona'], kind, r['callCount']))
        if r.get('maxLag', 0) > 1500:
            lags.append((r['persona'], kind, r['maxLag']))
        if r.get('nodesEnd', 0) > 3*max(1, r.get('nodesStart', 1)):
            growth.append((r['persona'], kind, r['nodesStart'], r['nodesEnd']))
        if not (r.get('appAlive') and r.get('attribution') and r.get('footer')):
            dead.append((r.get('persona'), 'APP-DEAD-OR-OWNER-ATTRIBUTES-MISSING'))
        if r.get('steps', 0) <= 0 or r.get('interactionStarted') is False or r.get('readinessFailed'):
            dead.append((r.get('persona'), 'INTERACTION-NOT-PROVEN'))
        if r.get('layoutReady') is False:
            dead.append((r.get('persona'), 'HARNESS-FRAME-NOT-VISIBLE'))
        if r.get('modalOpen'):
            per_kind[kind]['modal_left_open'] += 1
        if r.get('docOverflow', 0) > 0:
            per_kind[kind]['overflow'] += 1
            overflow.append((r.get('persona'), r['docOverflow']))
    return {'count':len(results),'errors': errors, 'out_of_range': bad_values, 'storms': storms, 'lags': lags, 'growth': growth, 'dead': dead, 'overflow': overflow, 'per_kind': per_kind}


def failed(summary):
    return not summary['count'] or any(summary[key] for key in ('errors', 'out_of_range', 'storms', 'lags', 'growth', 'dead', 'overflow'))


def show(s):
    print('PERSONAS BY KIND'); [print(' ', k, dict(v)) for k, v in s['per_kind'].items()]
    print('SCRIPT ERRORS (%d distinct)' % len(s['errors'])); [print(' ', n, e) for e, n in s['errors'].most_common(15)]
    print('OUT-OF-RANGE VALUES THE PAGE WOULD SEND'); [print(' ', k, dict(v.most_common(6))) for k, v in s['out_of_range'].items()] or None
    print('CALL STORMS (>150 calls)', s['storms'][:10]); print('LAGS >1.5 s', s['lags'][:10]); print('DOM GROWTH x3', s['growth'][:10]); print('DEAD', s['dead'][:10])
    print('HORIZONTAL OVERFLOW', s['overflow'][:10]);print('FOOL', 'FAIL' if failed(s) else 'PASS')


if __name__ == '__main__':
    rows = []
    for name in sys.argv[1:]:
        rows += json.load(sys.stdin) if name=='-' else json.loads(Path(name).read_text(encoding='utf-8'))
    summary=summarise(rows);show(summary);sys.exit(1 if failed(summary) else 0)
