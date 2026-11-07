#!/usr/bin/env python3
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Reference census from model.py (tools/formal/model.py, one directory up).

model.py's own JSON truncates the per-class transition violation lists at 3 entries; to compare with TLC's census
(one line per violating edge) this script re-runs the same BFS with model.py's successors()/leak()/family()/
consistent()/transition_checks() and counts everything: states, transitions, per-family leak states (canonical CI
signature), violating edges per transition class, inconsistent states, supervisor edges per (program counter before,
program counter after).  Standard library only.

Copy of private/math/formal-tlc/py_census.py reading tools/formal/model.py.
Usage: py -3 -I py_census.py <out.json> <model.py args...>   (e.g. --variant fix --fixed K2 --no-gl)
"""
import argparse
import collections
import importlib.util
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('model', os.path.join(HERE, os.pardir, 'model.py'))
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def canon(label):
    return re.sub(r'[^a-z0-9]+', '-', label.split('(')[0].strip().lower()).strip('-')


def model_cfg(argv):
    """model.py arguments -> its cfg object (the options tools/formal/tla/gen_cfg.py uses)."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', choices=['alpha6', 'fix'], default='fix')
    ap.add_argument('--fixed', default='')
    ap.add_argument('--faults', action='store_true')
    ap.add_argument('--server', action='store_true')
    ap.add_argument('--fast-switch', action='store_true')
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--window', action='store_true')
    ap.add_argument('--key-pin', choices=['directional', 'blocker'])
    ap.add_argument('--no-gl', action='store_true')
    ap.add_argument('--ext', default='both')
    ap.add_argument('--no-crash', action='store_true')
    ap.add_argument('--no-power', action='store_true')
    ap.add_argument('--no-expire', action='store_true')
    a = ap.parse_args(argv)
    fixed = frozenset(x for x in a.fixed.split(',') if x) if a.variant == 'fix' else frozenset()
    return argparse.Namespace(fix=a.variant == 'fix', fixed=fixed, faults=a.faults, server=a.server, fast_switch=a.fast_switch, rebuild=a.rebuild, window=a.window, key_pin=a.key_pin, gl=not a.no_gl,
                              ext=a.ext, crash=not a.no_crash, power=not a.no_power, expire=not a.no_expire)


def census(cfg):
    t0 = time.time()
    seen = {model.INIT: 0}
    q = collections.deque([model.INIT])
    edges = 0
    leak = collections.Counter()
    trans = collections.Counter()
    steps = collections.Counter()
    incons = 0
    while q:
        s = q.popleft()
        lk = model.leak(s)
        if lk:
            leak['LEAK:' + canon(model.family(s, lk))] += 1
        if not model.consistent(s):
            incons += 1
        for label, n, tags in model.successors(s, cfg):
            edges += 1
            if 'sup' in tags:                     # sup_steps: every one of its edges has this tag, the others never
                steps['STEP:%s:%d:%s>%s:%d:%s' % (s.sup + n.sup)] += 1
            for v in model.transition_checks(s, n, label, tags):
                trans['TRANSITION:' + v] += 1
            if n not in seen:
                seen[n] = len(seen)
                q.append(n)
    return {'states': len(seen), 'transitions': edges, 'leak': dict(sorted(leak.items())),
            'trans_edges': dict(sorted(trans.items())), 'steps': dict(sorted(steps.items())), 'inconsistent': incons,
            'seconds': round(time.time() - t0, 1)}


def main():
    res = census(model_cfg(sys.argv[2:]))
    res['args'] = sys.argv[2:]
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res))


if __name__ == '__main__':
    main()
