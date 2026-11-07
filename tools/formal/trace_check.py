#!/usr/bin/env python3
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Trace conformance of the product code against the formal model (tools/formal/model.py), 04.11.2026.

model.py is a hand abstraction of the supervisor; ci_check.py proves properties of the *model*. This check asks the
other question: does the *code* only make the transitions the model allows? Drivers run the real supervisor on fake
routers and record the abstract state after every scenario event (router/tests/trace_driver.py for Python,
router/tests/lua/trace_driver.lua for Lua; same scenarios, same projection of the product files):

  intent, fresh, marker     pair-auto-control.json (mode on with the current revision; id != session id), auto-resume.json
                            against native-stop.json (boot_resume.wanted)
  sess, readopt_code, ran, ho   pair-auto-state.json phase, recovery_error in READOPT_CODES, ran, handover
  jr, rtp, fails, fres, failed  native-transaction.json phase/rtp_dispatched/rollback_failures/forward_resumed/failure_code
  uci, kern                 the fake UCI order / kernel order: P primary first, R reserve first, F foreign (other policy)
  guard                     the fake nft guard: none / full / vpn (VPN-only)
  pUp, rUp, readopt         the driver's tunnel health, pair-readopt.json entries younger than 900 s

Hidden model fields (supervisor program counter, ghost Stop flag, outside-change kind, time abstractions pStable/
pHold/dwell, boot, resume window, revision freshness) are existentially quantified: the checker keeps the set of all
model states consistent with the trace so far. For every recorded step it searches the model successors allowed for
that event kind (a supervisor pass: supervisor steps only; an owner Start: one OWNER Start or a refusal stutter; a
crash: the interrupted pass then CRASH; ...; time/vendor steps are always allowed) and keeps the states whose projection
equals the recorded abstract state and whose program counter matches how the pass ended (loop / process exit /
give-up). An empty set is a NON-CONFORMING step: a product bug or a model gap (see trace_expected.json). Every
matched state is also checked against the model invariants (leak families of model.leak, consistency at rest).

Usage:
  python3 tools/formal/trace_check.py                 # fast profile: generate, run both drivers, check, compare
  python3 tools/formal/trace_check.py --profile full  # more scenarios (manual)
  python3 tools/formal/trace_check.py --check traces-python.json [traces-lua.json]   # only check recorded traces
Exit codes: 0 conforming (only listed gaps), 1 a non-conforming step not listed in trace_expected.json (or a parity
difference not listed), 2 setup error (driver crash, missing runtime when required).
"""
import argparse
import collections
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import model as M  # noqa: E402

PROFILES = {'fast': {'scenarios': 40, 'length': 26, 'seed': 20261104},
            'full': {'scenarios': 400, 'length': 40, 'seed': 20261104}}
HIDDEN = frozenset({'time', 'vendor', 'expire'})
HEALTH = ('pUp', 'rUp')
SINGLE = {
    'start': lambda label, tags: label.startswith('OWNER Start'),
    'stop': lambda label, tags: label == 'OWNER Stop',
    'p_down': lambda label, tags: label == 'ENV primary tunnel fails',
    'p_up': lambda label, tags: label == 'ENV primary tunnel recovers',
    'r_down': lambda label, tags: label == 'ENV reserve tunnel fails',
    'r_up': lambda label, tags: label == 'ENV reserve tunnel recovers',
    'r_lost': lambda label, tags: label == 'ENV reserve tunnel fails',
    'gl_pol': lambda label, tags: label == 'OWNER changes route policy in the GL panel',
    'gl_net': lambda label, tags: label.startswith('OWNER changes VPN clients'),
    'crash': lambda label, tags: 'crash' in tags,
    'power': lambda label, tags: 'power' in tags,
}
OBS_FIELDS = ('intent', 'fresh', 'marker', 'sess', 'readopt_code', 'ran', 'ho', 'kept', 'jr', 'rtp', 'fails', 'fres', 'failed',
              'uci', 'kern', 'guard', 'pUp', 'rUp', 'readopt')


# --------------------------------------------------------------------------------------------------------- projection
def project(s):
    """Model state -> the abstract fields the drivers read from the product (None = not compared in this state)."""
    rec = s.jr in M.RECOVERY
    return {
        'intent': s.intent,
        'fresh': s.intent == 'on' and s.fresh,
        'marker': s.marker,
        'sess': s.sess,
        'readopt_code': s.sess == 'HELD' and s.code == 'READOPT',
        'ran': s.ran if s.sess == 'HELD' else None,
        'ho': s.ho,
        'kept': s.kept if not s.ho else None,      # a hand-over records the clients it keeps too; not in the model
        'jr': s.jr,
        'rtp': s.rtp if rec else None,
        'fails': s.fails if rec else None,
        'fres': s.fres if s.jr != 'NONE' else None,
        'failed': s.failed if rec else None,
        'uci': s.uci,
        'kern': s.kern,
        'guard': s.guard,
        'pUp': s.pUp,
        'rUp': s.rUp,
        'readopt': s.readopt,
    }


def matches(proj, obs):
    for key, value in proj.items():
        if value is not None and obs.get(key) != value:
            return False
    return True


def diff(proj, obs):
    return {k: (v, obs.get(k)) for k, v in proj.items() if v is not None and obs.get(k) != v}


def adopt(s, obs):
    """Re-synchronise after a non-conforming step: the model state with the observed abstract fields."""
    fields = dict(intent=obs['intent'], fresh=obs['intent'] == 'on' and obs['fresh'], marker=obs['marker'], sess=obs['sess'],
                  ho=obs['ho'], kept=bool(obs.get('kept')) and not obs['ho'], jr={'RP': 'RB'}.get(obs['jr'], obs['jr']), uci=obs['uci'], kern=obs['kern'], guard=obs['guard'],
                  pUp=obs['pUp'], rUp=obs['rUp'], readopt=obs['readopt'], fres=obs['fres'])
    if fields['jr'] not in M.RECOVERY | M.TERM | {'COMMITTED', 'HOR', 'RB', 'NONE'}:
        fields['jr'] = 'NONE'
    if obs['sess'] in M.NONTERM:
        fields.update(ran=obs['ran'])
    if obs['sess'] == 'HELD':
        fields.update(code='READOPT' if obs['readopt_code'] else ('OTHER' if s.code == 'READOPT' or s.code == '-' else s.code))
    if fields['jr'] in M.RECOVERY:
        fields.update(rtp=obs['rtp'], fails=obs['fails'], failed=obs['failed'])
    if not obs['pUp']:
        fields.update(pStable=False, pHold=False)
    if obs['marker']:
        fields.update(stopped=False)
    return s._replace(**fields)


# --------------------------------------------------------------------------------------------------------- one step
def end_ok(s, end):
    if end == 'IDLE':
        return s.sup == M.IDLE
    if end == 'DOWN':
        return s.sup == M.DOWN
    if end == 'GIVEUP':
        return s.sup == M.BLOCKED
    raise ValueError(end)


def step(cfg, cands, row, limit=200000):
    """-> (matched states, reached states with the right program counter, explored count)."""
    event, end, obs = row['event'], row['end'], row['obs']
    # a failed vendor write the driver injected, or a failed proof after it (ROLLBACK-/KERNEL-POLICY-UNVERIFIED): model FAULT steps
    # (a give-up is the last failed rollback: its pass ends without an error)
    fault = bool(row.get('fault')) or 'UNVERIFIED' in str(row.get('error') or '') or row['end'] == 'GIVEUP'
    sup_ok = event in ('tick', 'recover', 'boot') or (event in ('crash', 'power') and row.get('mid'))
    single = SINGLE.get(event)

    def allowed(label, tags, phase):
        if 'fault' in tags and not fault:
            return None
        if phase == 0 and single is not None and single(label, tags):
            return 1                                            # the event's own action, once
        if tags <= HIDDEN | {'fault'} and tags & HIDDEN:
            return phase
        if event == 'resume' and label.startswith('RESUME'):
            return phase
        if row.get('env_health') and tags & {'health-good', 'health-bad'}:
            return phase                                        # a test's fake: a client it starts is a healthy tunnel
        if sup_ok and phase == 0 and 'sup' in tags and not label.startswith('RESUME'):
            return phase
        return None

    start_phase = 0
    seen = set()
    queue = collections.deque()
    for s in cands:
        if (s, start_phase) not in seen:
            seen.add((s, start_phase))
            queue.append((s, start_phase))
    reached, good, partial = [], [], []
    mid = event in ('crash', 'power') and row.get('mid')
    while queue:
        s, phase = queue.popleft()
        mandatory = event in ('crash', 'power', 'gl_pol', 'gl_net')   # start/stop/health may be a no-op (refusal, same value)
        if (phase == 1 or not mandatory) and end_ok(s, end):
            reached.append(s)
            if matches(project(s), obs):
                good.append(s)
        if len(seen) > limit:
            break
        for label, n, tags in M.successors(s, cfg):
            p = allowed(label, tags, phase)
            if p is None:
                continue
            if mid and phase == 0 and p == 0 and 'sup' in tags:
                # SIGKILL / power cut between two product writes of ONE model step s -> n: each abstract field is still
                # s's or already n's (the product splits the step into several durable writes)
                partial.extend(after_action(cfg, mix(s, n, obs), single, obs, end))
            key = (n, p)
            if key not in seen:
                seen.add(key)
                queue.append(key)
    if not good and partial:
        return partial, reached, len(seen), True
    return good, reached, len(seen), False


ATTR_OF = {'intent': 'intent', 'fresh': 'fresh', 'marker': 'marker', 'sess': 'sess', 'readopt_code': 'code', 'ran': 'ran',
           'ho': 'ho', 'kept': 'kept', 'jr': 'jr', 'rtp': 'rtp', 'fails': 'fails', 'fres': 'fres', 'failed': 'failed', 'uci': 'uci',
           'kern': 'kern', 'guard': 'guard', 'readopt': 'readopt'}


def mix(a, n, obs):
    pa, pn = project(a), project(n)
    take = {}
    for key, attr in ATTR_OF.items():
        if getattr(a, attr) != getattr(n, attr) and obs.get(key) == pa[key] and obs.get(key) != pn[key]:
            take[attr] = getattr(a, attr)
    return n._replace(**take)


def after_action(cfg, m, single, obs, end):
    out = []
    for label, n, tags in M.successors(m, cfg):
        if single is None or not single(label, tags):
            continue
        seen, queue = {n}, collections.deque([n])
        while queue:
            s = queue.popleft()
            if end_ok(s, end) and matches(project(s), obs):
                out.append(s)
            for label2, n2, tags2 in M.successors(s, cfg):
                if tags2 <= HIDDEN and tags2 and n2 not in seen and len(seen) < 200:
                    seen.add(n2)
                    queue.append(n2)
    return out


def invariants(states):
    """Leak family of the matched states (model.leak/family; reported when every candidate leaks) and consistency."""
    out = []
    leaks = [M.leak(s) for s in states]
    if states and all(leaks):
        fam = collections.Counter(M.family(s, k) for s, k in zip(states, leaks))
        out.append('LEAK:' + canon(fam.most_common(1)[0][0]))
    rest = [s for s in states if s.sup == M.IDLE]
    if rest and not any(M.consistent(s) for s in rest):  # at rest the journal and the kernel tell different routes
        out.append('INCONSISTENT')
    return out


def canon(label):
    import re
    return re.sub(r'[^a-z0-9]+', '-', label.split('(')[0].strip().lower()).strip('-')


def check_trace(cfg, trace, accepted_leaks):
    """-> dict(steps, conforming, findings[list], leaks Counter)."""
    findings = []
    partials = []
    write_leaks = {}
    leaks = collections.Counter()
    cands = {M.INIT._replace(sup=M.DOWN)}      # the scenario starts with the supervisor's first start on a quiet router
    steps = trace['steps']
    prev = None
    for i, row in enumerate(steps):
        if i == 0 and row['event'] != 'boot':
            raise ValueError('a trace starts with the boot event')
        good, reached, explored, split = step(cfg, cands, row)
        if split:
            partials.append({'scenario': trace['name'], 'index': i, 'event': row['event'],
                             'history': [s['event'] for s in steps[max(0, i - 6):i + 1]]})
        if good:
            cands = set(good)
        else:
            delta = {k for k in OBS_FIELDS if prev is not None and prev.get(k) != row['obs'].get(k)}
            # closest model state: fewest differing fields, preferring one that reproduces what the product changed
            closest = sorted(reached, key=lambda s: (len(diff(project(s), row['obs'])), len(set(diff(project(s), row['obs'])) & delta)))[:5]
            best = closest[0] if closest else (next(iter(cands)) if cands else M.INIT)
            follow = bool(findings) and findings[-1]['index'] == i - 1
            findings.append({'scenario': trace['name'], 'index': i, 'event': row['event'], 'end': row['end'], 'follow_up': follow,
                             'before': prev, 'after': row['obs'], 'reply': row.get('reply'), 'error': row.get('error'),
                             'diff': {k: list(v) for k, v in diff(project(best), row['obs']).items()} if closest else 'no state reachable',
                             'model_closest': M.fmt_state(best) if closest else None,
                             'history': [s['event'] + ('/' + s['end'] if s['end'] != 'IDLE' else '') for s in steps[max(0, i - 8):i + 1]]})
            base = closest or list(cands) or [M.INIT]
            cands = {adopt(s, row['obs'])._replace(sup={'IDLE': M.IDLE, 'DOWN': M.DOWN, 'GIVEUP': M.BLOCKED}[row['end']]) for s in base}
        for name in invariants(list(cands)):
            leaks[name] += 1
            if name == 'INCONSISTENT' and len(write_leaks.setdefault(name, [])) < 3:
                write_leaks[name].append({'scenario': trace['name'], 'index': i, 'write': -1, 'event': row['event'], 'snap': row['obs'],
                                          'history': [x['event'] for x in steps[max(0, i - 6):i + 1]]})
        # write-level snapshots inside the step: leak windows between two product writes (informational)
        last = prev or {}
        for w, snap in enumerate(row.get('writes') or []):
            for s in list(cands)[:1]:
                if row['event'] in ('recover', 'boot'):
                    pc = ('REC', 1, '')
                elif snap['sess'] == 'STARTING' and last.get('sess') != 'STARTING':
                    pc = ('BEGIN', 2, '')         # begin(): the STARTING record is written, its guard() is the next write
                else:
                    pc = M.IDLE
                t = adopt(s, snap)._replace(sup=pc)
                kind = M.leak(t)
                if kind:
                    name = 'WRITE-LEAK:' + canon(M.family(t, kind))
                    leaks[name] += 1
                    if len(write_leaks.setdefault(name, [])) < 3:
                        write_leaks[name].append({'scenario': trace['name'], 'index': i, 'write': w, 'event': row['event'],
                                                  'snap': snap, 'history': [x['event'] for x in steps[max(0, i - 6):i + 1]]})
            last = snap
        prev = row['obs']
    return {'steps': len(steps), 'findings': findings, 'leaks': leaks, 'partials': partials, 'write_leaks': write_leaks}


def signature(f):
    """Stable identity of a non-conforming step for trace_expected.json: event + changed fields + the abstract delta."""
    d = f['diff'] if isinstance(f['diff'], dict) else {}
    keys = ','.join('%s:%s->%s' % (k, v[0], v[1]) for k, v in sorted(d.items()))
    return '%s/%s|%s' % (f['event'], f['end'], keys or 'unreachable')


# --------------------------------------------------------------------------------------------------------- scenarios
EVENTS = [('tick', 30), ('start', 6), ('stop', 4), ('resume', 3), ('crash', 2), ('crash@', 3), ('power', 2), ('power@', 3),
          ('p_down', 6), ('p_up', 5), ('r_down', 2), ('r_lost', 1), ('r_up', 3), ('gl_pol', 1), ('gl_net', 1), ('busy', 2),
          ('wait', 5), ('wait_long', 3)]
SEEDED = [  # hand-written scenarios: the paths the counterexamples K1-K11 and the existing scenario tests exercise
    ('switch-and-return', 'tick start tick tick p_down tick tick wait p_up wait_long tick tick stop tick tick'),
    ('crash-mid-switch', 'tick start tick tick p_down crash@3 resume tick tick tick'),
    ('crash-each-write', 'tick start tick tick p_down crash@6 tick resume tick tick tick'),
    ('power-on-reserve', 'tick start tick tick p_down tick tick power resume tick tick tick wait_long tick p_up wait_long tick tick'),
    ('power-mid-return', 'tick start tick p_down tick tick p_up wait_long power@2 resume tick tick tick'),
    ('gl-policy-held', 'tick start tick tick gl_pol tick tick start tick tick tick stop tick'),
    ('gl-net-power', 'tick start tick tick gl_net tick tick power resume tick tick start tick tick'),
    ('stop-on-dead-primary', 'tick start tick tick p_down tick tick stop tick tick wait_long tick'),
    ('busy-vendor', 'tick start tick tick busy p_down tick tick tick wait tick tick'),
    ('reserve-fails-on-reserve', 'tick start tick tick p_down tick tick r_down tick p_up tick tick wait_long tick tick'),
    ('stop-start-race', 'tick start stop tick start tick tick stop start tick tick'),
    ('double-power', 'tick start tick tick p_down tick power power resume tick tick'),
    ('power-between-uci-and-rtp', 'tick start tick tick p_down p_down power@5 tick tick'),
    ('second-stop-power', 'tick start tick tick stop tick tick start tick tick stop tick tick power resume tick tick'),
    ('reserve-lost-stop-return', 'tick start tick tick p_down tick tick stop tick r_lost p_up wait_long tick tick tick'),
    ('reserve-lost-running', 'tick start tick tick p_down tick tick r_lost tick p_up wait_long tick tick r_up tick tick'),
]


def generate(profile):
    p = PROFILES[profile]
    rng = random.Random(p['seed'])
    names, weights = zip(*EVENTS)
    out = [{'name': name, 'events': text.split()} for name, text in SEEDED]
    for n in range(p['scenarios']):
        events = ['tick', 'start', 'tick', 'tick'] if rng.random() < 0.8 else ['tick']
        gl_used = False
        while len(events) < p['length']:
            e = rng.choices(names, weights)[0]
            if e in ('gl_pol', 'gl_net'):
                if gl_used:
                    continue        # the model has one outside change at a time (ext none -> net|pol until a begin)
                gl_used = True
            if e.endswith('@'):
                e += str(rng.randint(1, 12))
            events.append(e)
        out.append({'name': 'random-%03d' % n, 'events': events})
    return out


# --------------------------------------------------------------------------------------------------------- drivers
def run_python(scenarios, workdir, timeout):
    src, dst = Path(workdir) / 'scenarios-python.json', Path(workdir) / 'traces-python.json'
    src.write_text(json.dumps(scenarios), encoding='utf-8')
    proc = subprocess.run([sys.executable, str(ROOT / 'router/tests/trace_driver.py'), str(src), str(dst)],
                          capture_output=True, text=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError('python driver exit %d\n%s' % (proc.returncode, (proc.stdout + proc.stderr)[-3000:]))
    return json.loads(dst.read_text(encoding='utf-8'))


def run_lua(scenarios, workdir, timeout):
    lua = shutil.which('lua5.1') or shutil.which('lua')
    if lua is None:
        return None
    src, dst = Path(workdir) / 'scenarios-lua.json', Path(workdir) / 'traces-lua.json'
    src.write_text(json.dumps(scenarios), encoding='utf-8')
    ram = tempfile.mkdtemp(prefix='trace-lua-')   # canon's sha256sum pipe file: never on a slow mount
    env = dict(os.environ, HOMENSAI_TEST_RUNTIME=ram)
    proc = subprocess.run([lua, 'trace_driver.lua', str(src), str(dst)], cwd=str(ROOT / 'router/tests/lua'),
                          capture_output=True, text=True, timeout=timeout, env=env)
    if proc.returncode:
        raise RuntimeError('lua driver exit %d\n%s' % (proc.returncode, (proc.stdout + proc.stderr)[-3000:]))
    return json.loads(dst.read_text(encoding='utf-8'))


def run_record(workdir, timeout):
    dst = Path(workdir) / 'existing-tests.json'
    proc = subprocess.run([sys.executable, str(ROOT / 'router/tests/trace_record.py'), str(dst)], capture_output=True, text=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError('recorder exit %d\n%s' % (proc.returncode, (proc.stdout + proc.stderr)[-3000:]))
    return json.loads(dst.read_text(encoding='utf-8'))


def parity(py, lu):
    """Identical scenarios: the abstract traces of both runtimes, step by step (event kind, how the pass ended, fields)."""
    out = []
    lua = {t['name']: t for t in lu}
    for t in py:
        other = lua.get(t['name'])
        if other is None:
            out.append({'scenario': t['name'], 'index': -1, 'what': 'missing in lua'})
            continue
        for i, (a, b) in enumerate(zip(t['steps'], other['steps'])):
            fields = [k for k in OBS_FIELDS if a['obs'].get(k) != b['obs'].get(k)]
            if a['event'] != b['event'] or a['end'] != b['end'] or fields:
                # the Lua monitor/buttons hand some Starts to agent.py (control_request FALLBACK: the outside-change
                # hand-over, preparation repairs) - there the Lua line has no own behaviour to compare
                out.append({'scenario': t['name'], 'index': i, 'event': a['event'] + '/' + b['event'], 'delegated': bool(b.get('fallback')),
                            'end': a['end'] + '/' + b['end'], 'fields': {k: [a['obs'].get(k), b['obs'].get(k)] for k in fields},
                            'history': [s['event'] for s in t['steps'][max(0, i - 6):i + 1]]})
                break                                   # the first difference per scenario (later steps follow from it)
        else:
            if len(t['steps']) != len(other['steps']):
                out.append({'scenario': t['name'], 'index': min(len(t['steps']), len(other['steps'])), 'what': 'length %d/%d' % (len(t['steps']), len(other['steps']))})
    return out


def model_cfg():
    expected = json.loads((HERE / 'expected.json').read_text(encoding='utf-8'))
    import argparse as _a
    cfg = _a.Namespace(fix=True, fixed=frozenset(expected['fixed']), faults=True, server=False, gl=True, ext='both',
                       crash=True, power=True, expire=True, rebuild=False, window=True, fast_switch=False)
    accepted = {k[5:] for k, v in expected['known'].items() if k.startswith('LEAK:') and v['status'] == 'accepted'}
    return cfg, accepted


def check_runtime(cfg, accepted, traces):
    result = {'traces': 0, 'steps': 0, 'findings': [], 'leaks': collections.Counter(), 'driver_errors': [], 'partials': [], 'write_leaks': {}}
    for t in traces:
        if t.get('driver_error'):
            result['driver_errors'].append({'scenario': t['name'], 'error': t['driver_error']})
            continue
        r = check_trace(cfg, t, accepted)
        result['traces'] += 1
        result['steps'] += r['steps']
        result['findings'].extend(r['findings'])
        result['leaks'].update(r['leaks'])
        result['partials'].extend(r['partials'])
        for k, v in r['write_leaks'].items():
            have = result['write_leaks'].setdefault(k, [])
            have.extend(v[:max(0, 3 - len(have))])
    return result


def seeds(obs):
    """Every model state with this abstract state: the hidden fields of a test's own arrangement are unknown."""
    base = adopt(M.INIT, obs)._replace(stopped=bool(obs.get('stopped')))
    out = set()
    for sup in (M.IDLE, M.DOWN):
        for stable, hold in ((True, True), (True, False), (False, False)) if obs['pUp'] else ((False, False),):
            for dwell in (True, False):
                for boot in (True, False):
                    for resume in (True, False):
                        for ext in ('pol',) if 'F' in (obs['uci'], obs['kern']) else ('none',):
                            for young in (True, False):
                                out.add(base._replace(sup=sup, pStable=stable, pHold=hold, dwell=dwell, boot=boot, resume=resume,
                                                      young=young, txrev=True, prep=ext == 'pol', ext=ext))
    return out


def check_recorded(cfg, data):
    """The existing scenario tests (router/tests/trace_record.py): events between the tests' own arrangements, invariants
    on every snapshot. A test arranges states the model may never reach, so its findings are reported for triage."""
    out = {'tests': data['ran'], 'failures': data['failures'] + data['errors'], 'events': 0, 'segments': 0, 'snapshots': 0,
           'findings': [], 'leaks': collections.Counter(), 'problems': data['problems'], 'unobservable': 0, 'leak_examples': {}}
    compare = OBS_FIELDS + ('stopped',)
    for test in data['tests']:
        out['unobservable'] += test['unobservable']
        cands, last = None, None
        for row in test['events']:
            if row['event'] == 'reset':
                cands, last = None, None
            elif row['event'] == 'observe':
                obs = row['obs']
                changed = [k for k in compare if last is not None and last.get(k) != obs.get(k)]
                if cands is None or set(changed) - set(HEALTH):
                    cands = seeds(obs)
                    out['segments'] += 1
                else:
                    for field in changed:          # the test changed a tunnel's health between two calls
                        names = {'pUp': ('p_down', 'p_up'), 'rUp': ('r_down', 'r_up')}[field]
                        interim = dict(last, **{field: obs[field]})
                        good, _, _, _ = step(cfg, cands, {'event': names[1 if obs[field] else 0], 'end': 'IDLE', 'obs': interim})
                        cands = set(good) or seeds(obs)
                        last = interim
                last = obs
            else:
                if cands is None:
                    continue
                out['events'] += 1
                moved = last is not None and any(last.get(k) != row['obs'].get(k) for k in HEALTH)
                good, reached, _, _ = step(cfg, cands, dict(row, env_health=moved))
                if good:
                    cands = set(good)
                else:
                    closest = sorted(reached, key=lambda s: len(diff(project(s), row['obs'])))[:1]
                    out['findings'].append({'test': test['test'], 'event': row['event'], 'end': row['end'], 'before': last, 'after': row['obs'],
                                            'diff': {k: list(v) for k, v in diff(project(closest[0]), row['obs']).items()} if closest else 'no state reachable',
                                            'model_closest': M.fmt_state(closest[0]) if closest else None})
                    cands = None
                last = row['obs']
        prior = None
        for snap in test['snaps']:
            out['snapshots'] += 1
            obs = snap['obs']
            pc = ('REC', 1, '') if snap['recovering'] else ('BEGIN', 2, '') if obs['sess'] == 'STARTING' and prior != 'STARTING' else M.IDLE
            t = adopt(M.INIT, obs)._replace(sup=pc, stopped=bool(obs.get('stopped')))
            prior = obs['sess']
            kind = M.leak(t)
            if kind:
                name = 'LEAK:' + canon(M.family(t, kind))
                out['leaks'][name] += 1
                out['leak_examples'].setdefault(name, {'test': test['test'], 'obs': obs})
    return out


def selftest(cfg, accepted, traces):
    """The check must not be vacuous: mutated copies of conforming recorded steps have to be rejected.
    -> list of failure lines (empty: every applicable mutation was caught)."""
    import copy
    mutations = (
        ('the supervisor turns the intent on by itself', lambda prev, row: row['event'] == 'tick' and prev['intent'] == 'off',
         {'intent': 'on'}),
        ('the guard of a carrying reserve disappears', lambda prev, row: row['event'] == 'tick' and row['obs']['uci'] == 'R'
         and row['obs']['jr'] in ('COMMITTED', 'HOR') and row['obs']['guard'] == 'vpn', {'guard': 'none'}),
        ('a switch while the primary is healthy', lambda prev, row: row['event'] == 'tick' and prev['jr'] in ('NONE', 'RB')
         and prev['uci'] == 'P' and prev['pUp'] and row['obs']['pUp'] and row['obs']['jr'] in ('NONE', 'RB'),
         {'jr': 'COMMITTED', 'uci': 'R', 'kern': 'R'}),
    )
    caught, failures = 0, []
    for name, applies, change in mutations:
        done = False
        for trace in traces:
            if done or trace.get('driver_error'):
                continue
            steps = trace['steps']
            for i in range(1, len(steps)):
                if applies(steps[i - 1]['obs'], steps[i]):
                    clean = check_trace(cfg, dict(trace, steps=steps[:i + 1]), accepted)
                    if clean['findings']:
                        break                         # the prefix itself does not conform: try another trace
                    mutated = copy.deepcopy(dict(trace, steps=steps[:i + 1]))
                    mutated['steps'][i]['obs'].update(change)
                    r = check_trace(cfg, mutated, accepted)
                    if any(f['index'] == i for f in r['findings']):
                        caught += 1
                    else:
                        failures.append('SELFTEST mutation not rejected: %s (%s step %d)' % (name, trace['name'], i))
                    done = True
                    break
    return caught, failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--profile', choices=sorted(PROFILES), default='fast')
    ap.add_argument('--check', nargs='+', help='check recorded trace files instead of running the drivers')
    ap.add_argument('--expected', default=str(HERE / 'trace_expected.json'))
    ap.add_argument('--require-lua', action='store_true', help='fail when lua5.1 is missing (the full CI image has it)')
    ap.add_argument('--json', help='write the full result here')
    ap.add_argument('--keep', help='keep scenarios and traces in this directory')
    ap.add_argument('--timeout', type=int, default=900)
    args = ap.parse_args(argv)
    t0 = time.time()
    existing = None
    cfg, accepted = model_cfg()
    expected = json.loads(Path(args.expected).read_text(encoding='utf-8')) if Path(args.expected).exists() else {'known': {}}
    try:
        if args.check:
            runs = {('python' if i == 0 else 'lua'): json.loads(Path(p).read_text(encoding='utf-8')) for i, p in enumerate(args.check)}
        else:
            scenarios = generate(args.profile)
            work = args.keep or tempfile.mkdtemp(prefix='trace-check-')
            Path(work).mkdir(parents=True, exist_ok=True)
            if args.require_lua and not (shutil.which('lua5.1') or shutil.which('lua')):
                print('TRACE-CHECK setup error: lua5.1 not found', file=sys.stderr)
                return 2
            # both runtimes at once (the CI container has 2 CPUs); each driver is one sequential process
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(3) as pool:
                py_job = pool.submit(run_python, scenarios, work, args.timeout)
                lua_job = pool.submit(run_lua, scenarios, work, args.timeout)
                record_job = pool.submit(run_record, work, args.timeout)
                runs = {'python': py_job.result()}
                lua = lua_job.result()
                existing = record_job.result()
            if lua is not None:
                runs['lua'] = lua
            elif args.require_lua:
                print('TRACE-CHECK setup error: lua5.1 not found', file=sys.stderr)
                return 2
            if not args.keep:
                shutil.rmtree(work, ignore_errors=True)
    except (RuntimeError, subprocess.TimeoutExpired, OSError, ValueError) as error:
        print('TRACE-CHECK setup error: %s' % error, file=sys.stderr)
        return 2
    known = expected.get('known', {})
    red = []
    report = {'profile': args.profile, 'runtimes': {}}
    for runtime, traces in runs.items():
        r = check_runtime(cfg, accepted, traces)
        # the step right after a non-conforming one starts from re-synchronised model states: reported, never gating
        primary = [f for f in r['findings'] if not f['follow_up']]
        sigs = collections.Counter(signature(f) for f in primary)
        first = {}
        for f in primary:
            first.setdefault(signature(f), f)
        print('TRACE-CHECK %-6s traces=%d steps=%d non-conforming=%d (%d kinds, +%d follow-up steps) split-step-kills=%d driver-errors=%d' % (
            runtime, r['traces'], r['steps'], len(primary), len(sigs), len(r['findings']) - len(primary), len(r['partials']),
            len(r['driver_errors'])), flush=True)
        for sig, n in sorted(sigs.items()):
            entry = known.get(sig)
            scope = entry.get('runtimes') if entry else None
            status = entry['verdict'] if entry and (not scope or runtime in scope) else 'NEW'
            print('  %-11s %4d x %s%s' % (status, n, sig, ' [%s]' % entry['id'] if entry and status != 'NEW' else ''))
            if status == 'NEW':
                f = first[sig]
                red.append('%s: %s (e.g. %s step %d, history %s)' % (runtime, sig, f['scenario'], f['index'], ' '.join(f['history'])))
        for name, n in sorted(r['leaks'].items()):
            ok = name.startswith('WRITE-LEAK:') or name[5:] in accepted or name in expected.get('invariants', {})
            print('  %-11s %4d x %s' % ('leak-ok' if ok else 'LEAK', n, name))
            if not ok:
                red.append('%s: model invariant %s on a matched state' % (runtime, name))
        for e in r['driver_errors']:
            print('  DRIVER-ERROR %s\n%s' % (e['scenario'], e['error'][-1500:]))
        report['runtimes'][runtime] = {'traces': r['traces'], 'steps': r['steps'], 'non_conforming': len(primary),
                                       'follow_up': len(r['findings']) - len(primary),
                                       'signatures': dict(sigs), 'examples': list(first.values()), 'leaks': dict(r['leaks']),
                                       'split_step_kills': r['partials'], 'write_leak_examples': r['write_leaks'],
                                       'driver_errors': r['driver_errors']}
        if r['driver_errors']:
            red.append('%s: %d driver errors' % (runtime, len(r['driver_errors'])))
    if 'python' in runs and 'lua' in runs:
        diffs = parity(runs['python'], runs['lua'])
        allowed = expected.get('parity', {})
        report['parity'] = diffs
        same = len(runs['python']) - len({d['scenario'] for d in diffs})
        print('TRACE-CHECK parity: %d of %d scenarios give identical abstract traces' % (same, len(runs['python'])))
        delegated = sum(1 for d in diffs if d.get('delegated'))
        print('TRACE-CHECK parity: %d differ at a Start the Lua line delegates to agent.py (FALLBACK), %d otherwise' % (delegated, len(diffs) - delegated))
        for d in diffs:
            listed = d['scenario'] in allowed or d.get('delegated')
            print('  %-8s %s step %s %s %s' % ('agent.py' if d.get('delegated') else 'known' if listed else 'DIFF', d['scenario'],
                                              d.get('index'), d.get('event', ''), json.dumps(d.get('fields', d.get('what')))))
            if not listed:
                red.append('parity: %s step %s' % (d['scenario'], d.get('index')))
    else:
        print('TRACE-CHECK parity: skipped (one runtime only)')
    caught, failures = selftest(cfg, accepted, runs.get('python') or next(iter(runs.values())))
    print('TRACE-CHECK selftest: %d mutated steps rejected, %d not' % (caught, len(failures)))
    red.extend(failures)
    if caught == 0:
        red.append('selftest: no mutation applicable (traces too short?)')
    seconds = round(time.time() - t0, 1)
    if existing is not None:
        e = check_recorded(cfg, existing)
        report['existing'] = dict(e, leaks=dict(e['leaks']))
        kinds = collections.Counter('%s/%s|%s' % (f['event'], f['end'], ','.join(sorted(f['diff'])) if isinstance(f['diff'], dict) else 'unreachable') for f in e['findings'])
        print('TRACE-CHECK existing tests: %d run, %d failed, %d events in %d segments, %d snapshots, %d unobservable, %d steps outside the model (%d kinds, for triage)' % (
            e['tests'], e['failures'], e['events'], e['segments'], e['snapshots'], e['unobservable'], len(e['findings']), len(kinds)))
        for name, n in sorted(kinds.items()):
            print('  triage     %4d x %s' % (n, name))
        for name, n in sorted(e['leaks'].items()):
            ok = name[5:] in accepted or name in expected.get('existing_leaks', {})
            print('  %-11s %4d x %s' % ('leak-ok' if ok else 'LEAK', n, name))
            if not ok:
                red.append('existing tests: invariant %s (e.g. %s)' % (name, e['leak_examples'][name]['test']))
        if e['failures']:
            red.append('existing tests failed under the recorder: %s' % ', '.join(e['problems'][:5]))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1, default=str), encoding='utf-8')
    for line in red:
        print('TRACE-CHECK RED ' + line)
    print('TRACE-CHECK summary: runtimes=%s steps=%d seconds=%s new=%d' % (
        ','.join(sorted(runs)), sum(v['steps'] for v in report['runtimes'].values()), seconds, len(red)))
    return 1 if red else 0


if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    sys.exit(main())
