#!/usr/bin/env python3
"""CI gate for the formal model of the Auto supervisor (tools/formal/model.py). Standard library only, Python 3.9+.

Runs the reduced CI profiles of the exhaustive explicit-state model (variant "fix" = the current released code) and
compares the set of violated properties ("signatures") with tools/formal/expected.json:

  * a violation that is not listed                         -> RED   (new violation, or a fixed K regressed)
  * a listed "xfail" (known, not yet fixed) that is gone  -> RED   (XPASS: the fix landed - flip it, see README.md)
  * everything else                                        -> GREEN (known and accepted-by-design findings are printed)

The model is a hand abstraction of the Lua/Python code; it does not read the code. Flipping a K therefore means
(1) the fix is in the code and (2) the model switch for that K is turned on via "fixed" in expected.json.

Usage:
  python3 tools/formal/ci_check.py                        # all profiles, 2 worker processes
  python3 tools/formal/ci_check.py --profile held         # one profile
  python3 tools/formal/ci_check.py --baseline             # print the observed signatures (to update expected.json)
Exit codes: 0 green, 1 red, 2 setup error (bad expected.json, model crash, timeout).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Reduced bounds: the full "everything on" profile has ~4.7 M states (20 min, ~3 GB). These stay below ~0.2 M states each
# and are chosen so that every known K is reachable in at least one of them (checked: see expected.json "profiles").
PROFILES = {
    'held': ['--no-crash', '--no-power', '--no-expire'],                 # outside change + owner actions (held start, K5)
    'restart': ['--no-gl'],                                              # crash + power cut + 90 s guard self-release (K2-K4)
    'faults': ['--no-gl', '--no-power', '--faults'],                     # rtp2/rollback failures, give_up (K6, K7)
    'faults-power': ['--no-gl', '--no-crash', '--faults'],               # power cut + failed kernel reload (K10)
    'server': ['--no-gl', '--no-power', '--server'],                     # server pick stages 2/3
    'glpower-net': ['--no-crash', '--no-expire', '--ext', 'net'],        # outside client change, then power cut (K9, K11; ~0.3 M states)
}
MIN_STATES = 50000   # a profile that explores far fewer states than designed means the model was broken, not "green"


def canon_family(label):
    return re.sub(r'[^a-z0-9]+', '-', label.split('(')[0].strip().lower()).strip('-')


def signatures(result):
    """Violated properties of one model result (the JSON the model writes) -> {signature: state/trace count}."""
    sig = {}
    for fam, n in (result.get('leak_families') or {}).items():
        sig['LEAK:' + canon_family(fam)] = n
    if 'INCONSISTENT' in (result.get('invariants') or {}):
        sig['INCONSISTENT'] = result['invariants']['INCONSISTENT']
    for name, n in (result.get('transition') or {}).items():
        sig['TRANSITION:' + name] = n
    if result.get('ef_stuck'):
        sig['EF-START'] = result['ef_stuck']
    if (result.get('liveness_failover') or {}).get('bad'):
        sig['LIVENESS:failover'] = result['liveness_failover']['bad']
    for which in ('up', 'down'):
        bad = (result.get('liveness_stop_primary_' + which) or {}).get('not_clean')
        if bad:
            sig['LIVENESS:stop-primary-' + which] = bad
    return sig


def load_expected(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    for key in ('variant', 'fixed', 'known'):
        if key not in data:
            raise ValueError('expected.json: missing "%s"' % key)
    if data['variant'] != 'fix':
        raise ValueError('expected.json: only variant "fix" is supported in CI (K switches go through "fixed")')
    for name, entry in data['known'].items():
        if entry.get('status') not in ('xfail', 'accepted'):
            raise ValueError('expected.json: %s: status must be xfail or accepted' % name)
        if entry['status'] == 'xfail' and not re.fullmatch(r'K\d+', entry.get('k', '')):
            raise ValueError('expected.json: %s: an xfail needs "k": "K<number>"' % name)
        if entry.get('k') in data['fixed']:
            raise ValueError('expected.json: %s belongs to %s, which is listed in "fixed": delete the entry' % (name, entry['k']))
    return data


def judge(expected, observed, check_xpass=True):
    """observed: {profile: {signature: count}}. -> (new_violations, xpass, notes) where each is a list of text lines."""
    known = expected['known']
    new, xpass, notes = [], [], []
    seen = {}
    for profile, sigs in sorted(observed.items()):
        for name, count in sorted(sigs.items()):
            entry = known.get(name)
            if entry is None:
                new.append('NEW VIOLATION %s in profile %s (%d): not listed in expected.json' % (name, profile, count))
                continue
            only = entry.get('profiles')
            if only and profile not in only:
                new.append('NEW VIOLATION %s in profile %s (%d): listed only for %s' % (name, profile, count, ','.join(only)))
                continue
            seen.setdefault(name, []).append(profile)
    for name, entry in sorted(known.items()):
        profiles = seen.get(name)
        scope = entry.get('profiles')
        ran = [p for p in observed if not scope or p in scope]
        if entry['status'] == 'xfail':
            if profiles:
                notes.append('XFAIL    %-42s %s (%s) in %s' % (name, entry['k'], entry.get('note', ''), ','.join(profiles)))
            elif ran and check_xpass:
                xpass.append('XPASS %s (%s) is no longer violated in %s: the fix landed, flip it (tools/formal/README.md)'
                             % (name, entry['k'], ','.join(ran)))
        elif profiles:
            notes.append('accepted %-42s %s in %s' % (name, entry.get('note', ''), ','.join(profiles)))
    return new, xpass, notes


def run_profile(model, name, variant_args, timeout, workdir):
    out_json = Path(workdir) / (name + '.json')
    cmd = [sys.executable, str(model)] + variant_args + ['--json', str(out_json), '--out', os.devnull]
    started = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return {'name': name, 'proc': proc, 'json': out_json, 'started': started, 'timeout': timeout, 'cmd': cmd}


def peak_rss_mb():
    """Peak resident size of finished child processes (POSIX; the CI container). None elsewhere."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        return round(usage / (1024.0 if sys.platform != 'darwin' else 1024.0 * 1024.0), 1)
    except ImportError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--expected', default=str(HERE / 'expected.json'))
    ap.add_argument('--model', default=str(HERE / 'model.py'))
    ap.add_argument('--profile', action='append', choices=sorted(PROFILES), help='run only these profiles (default: all)')
    ap.add_argument('--jobs', type=int, default=2, help='parallel model processes (CI container: 2 CPUs)')
    ap.add_argument('--timeout', type=int, default=600, help='seconds per profile')
    ap.add_argument('--baseline', action='store_true', help='print observed signatures as JSON and exit 0')
    ap.add_argument('--fixed', help='with --baseline only: override "fixed" (comma-separated K names) to see what a fix removes')
    args = ap.parse_args(argv)
    try:
        expected = load_expected(args.expected)
    except (OSError, ValueError) as e:
        print('FORMAL-CI setup error: %s' % e, file=sys.stderr)
        return 2
    names = args.profile or sorted(PROFILES)
    if args.fixed is not None and not args.baseline:
        print('FORMAL-CI setup error: --fixed is only for --baseline experiments; edit expected.json', file=sys.stderr)
        return 2
    fixed = expected['fixed'] if args.fixed is None else [x for x in args.fixed.split(',') if x]
    variant_args = ['--variant', 'fix']
    if fixed:
        variant_args += ['--fixed', ','.join(fixed)]
    observed, states, times = {}, {}, {}
    t0 = time.time()
    pending = list(names)
    running = []
    with tempfile.TemporaryDirectory() as workdir:
        while pending or running:
            while pending and len(running) < max(1, args.jobs):
                name = pending.pop(0)
                running.append(run_profile(args.model, name, variant_args + PROFILES[name], args.timeout, workdir))
            time.sleep(0.2)
            for job in list(running):
                code = job['proc'].poll()
                elapsed = time.time() - job['started']
                if code is None and elapsed > job['timeout']:
                    job['proc'].kill()
                    print('FORMAL-CI setup error: profile %s exceeded %d s' % (job['name'], job['timeout']), file=sys.stderr)
                    for other in running:
                        if other is not job:
                            other['proc'].kill()
                    return 2
                if code is None:
                    continue
                running.remove(job)
                err = job['proc'].stderr.read()
                if code != 0:
                    print('FORMAL-CI setup error: profile %s exited %d\n%s' % (job['name'], code, err[-2000:]), file=sys.stderr)
                    for other in running:
                        other['proc'].kill()
                    return 2
                result = json.loads(job['json'].read_text(encoding='utf-8'))[0]
                if result['states'] < MIN_STATES:
                    print('FORMAL-CI setup error: profile %s explored only %d states (< %d): the model is broken'
                          % (job['name'], result['states'], MIN_STATES), file=sys.stderr)
                    return 2
                observed[job['name']] = signatures(result)
                states[job['name']] = result['states']
                times[job['name']] = round(elapsed, 1)
                print('FORMAL-CI profile %-13s %8d states %6.1f s, %d violated properties' % (
                    job['name'], result['states'], elapsed, len(observed[job['name']])), flush=True)
    total = round(time.time() - t0, 1)
    rss = peak_rss_mb()
    if args.baseline:
        print('FORMAL-CI baseline: states=%d seconds=%s peak_child_rss_mb=%s' % (sum(states.values()), total, rss), file=sys.stderr)
        print(json.dumps({p: dict(sorted(s.items())) for p, s in sorted(observed.items())}, indent=1))
        return 0
    new, xpass, notes = judge(expected, observed, check_xpass=set(observed) == set(PROFILES))
    if set(observed) != set(PROFILES):
        print('FORMAL-CI note: a subset of profiles was run, the XPASS check (an xfail that vanished) is skipped')
    for line in notes:
        print('FORMAL-CI ' + line)
    for line in new + xpass:
        print('FORMAL-CI ' + line, file=sys.stderr)
    print('FORMAL-CI summary: profiles=%d states=%d seconds=%s peak_child_rss_mb=%s new=%d xpass=%d xfail=%d' % (
        len(observed), sum(states.values()), total, rss, len(new), len(xpass),
        sum(1 for n in expected['known'].values() if n['status'] == 'xfail')))
    return 1 if (new or xpass) else 0


if __name__ == '__main__':
    sys.exit(main())
