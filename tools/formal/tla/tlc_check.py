#!/usr/bin/env python3
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""OPTIONAL CI cross-check: TLC (TLA+ spec Supervisor.tla) against the Python model tools/formal/model.py.

For every CI configuration (one per profile of tools/formal/ci_check.py; see gen_cfg.py) this runs
  * TLC 1.7.4 in the pre-built docker image homensai-tlc:local (--network none, read-only, no jar in git; see README.md),
  * the reference census of model.py (py_census.py, counts every state, edge and violating edge),
and compares the number of distinct states, the number of transitions, the violation signatures (LEAK:*, TRANSITION:*,
INCONSISTENT with their counts) and the supervisor edges per (program counter before, after) (STEP:*: an edge that moves to another
reachable state changes no other count).  Any difference means Supervisor.tla and model.py were edited out of step: red.

Result states:
  PASS     every configuration agrees exactly
  SKIPPED  docker or the image is not available: nothing was run and nothing is claimed (exit code 0)
  FAIL     a difference, a TLC error, a timeout or a broken image/manifest (exit code 1; 2 = usage/setup error)

Usage:
  python tools/formal/tla/tlc_check.py [--source REPO_ROOT] [--image homensai-tlc:local] [--py-image IMAGE]
                                       [--timeout 1500] [--workers 3] [--jobs 2] [--result result.json] [--only NAME ...]
  python tools/formal/tla/tlc_check.py --verify-manifest    # offline: SHA256SUMS of the mirror files
  python tools/formal/tla/tlc_check.py --update-manifest    # after an intended edit of Supervisor.tla / gen_cfg.py / cfg
The last line of a run is   TLC-CROSSCHECK {json}   (the same JSON goes to --result).  Standard library only.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMAGE = 'homensai-tlc:local'
DEFAULT_TIMEOUT = 1500
DEFAULT_JOBS = 2         # configurations at the same time; each one is a TLC container and a model.py process
JAR_LABEL = 'org.homensai.tla2tools.sha256'
MANIFEST = 'SHA256SUMS'
CENSUS_RE = re.compile(r'<<"CENSUS-(LEAK|TRANS|INV|STEP)", "([^"]+)">>')
CENSUS_PREFIX = {'LEAK': 'LEAK:', 'TRANS': 'TRANSITION:', 'INV': '', 'STEP': 'STEP:'}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configurations():
    return load_module('tla_gen_cfg', os.path.join(HERE, 'gen_cfg.py')).manifest_entries()


MIRROR_FILES = ('Supervisor.tla', 'gen_cfg.py', 'py_census.py') + tuple('cfg/%s.cfg' % e['name'] for e in configurations())


# ---------------------------------------------------------------- parsing and comparison (pure, unit-tested)

def parse_tlc(lines):
    """TLC console output (any iterable of lines) -> the facts the comparison needs."""
    census = {}
    out = {'generated': None, 'distinct': None, 'depth': None, 'completed': False, 'errors': [], 'violated': [], 'version': None}
    for raw in lines:
        line = raw.strip()
        m = CENSUS_RE.match(line)
        if m:
            key = CENSUS_PREFIX[m.group(1)] + m.group(2)
            census[key] = census.get(key, 0) + 1
            continue
        m = re.match(r'([\d,]+) states generated, ([\d,]+) distinct states found', line)
        if m:
            out['generated'] = int(m.group(1).replace(',', ''))
            out['distinct'] = int(m.group(2).replace(',', ''))
        m = re.match(r'The depth of the complete state graph search is (\d+)', line)
        if m:
            out['depth'] = int(m.group(1))
        m = re.match(r'Error: Invariant (\w+) is violated', line)
        if m:
            out['violated'].append(m.group(1))
        if (line.startswith('Error:') and not line.startswith('Error: Invariant')) or line.startswith('TLC threw an unexpected exception'):
            out['errors'].append(line[:200])
        if line.startswith('Model checking completed. No error has been found.'):
            out['completed'] = True
        m = re.match(r'TLC2 Version (.+)', line)
        if m:
            out['version'] = m.group(1)
    out['census'] = dict(sorted(census.items()))
    return out


def py_signatures(py):
    """py_census.py JSON -> {signature: count}, the same naming as the TLC census."""
    sig = dict(py.get('leak') or {})
    sig.update(py.get('trans_edges') or {})
    sig.update(py.get('steps') or {})
    if py.get('inconsistent'):
        sig['INCONSISTENT'] = py['inconsistent']
    return dict(sorted(sig.items()))


def compare(name, tlc, py):
    """-> list of problem lines (empty = TLC and model.py agree exactly)."""
    problems = []
    if tlc.get('violated'):
        problems.append('%s: TLC reports violated invariant(s) %s (TypeOK/Census are part of the spec: the spec itself is broken)'
                        % (name, ','.join(tlc['violated'])))
    if tlc.get('errors'):
        problems.append('%s: TLC error: %s' % (name, tlc['errors'][0]))
    if not tlc.get('completed') and not tlc.get('violated') and not tlc.get('errors'):
        problems.append('%s: TLC did not finish ("Model checking completed" is missing from its output)' % name)
    if tlc.get('distinct') is None or tlc.get('generated') is None:
        problems.append('%s: TLC state counts are missing from its output' % name)
        return problems
    tlc_transitions = tlc['generated'] - 1   # TLC counts the initial state as one generated state
    if tlc['distinct'] != py['states']:
        problems.append('%s: states differ: TLC %d, model.py %d' % (name, tlc['distinct'], py['states']))
    if tlc_transitions != py['transitions']:
        problems.append('%s: transitions differ: TLC %d, model.py %d' % (name, tlc_transitions, py['transitions']))
    a, b = tlc.get('census') or {}, py_signatures(py)
    if not any(key.startswith('STEP:') for key in a):
        problems.append('%s: TLC printed no CENSUS-STEP line: the step census is not running' % name)
    for sig in sorted(set(a) | set(b)):
        if a.get(sig, 0) != b.get(sig, 0):
            problems.append('%s: violation signature %s differs: TLC %d, model.py %d' % (name, sig, a.get(sig, 0), b.get(sig, 0)))
    if problems:
        problems.append('%s: Supervisor.tla and tools/formal/model.py are out of step: change both (tools/formal/tla/README.md)' % name)
    return problems


def check_fixed_set(expected_fixed, entries):
    """The K fixes switched on in tools/formal/expected.json must be exactly the ones of the TLC configurations."""
    problems = []
    for e in entries:
        if sorted(e['fixed']) != sorted(expected_fixed):
            problems.append('%s: TLC cfg switches on fixes %s, tools/formal/expected.json "fixed" is %s: update gen_cfg.py ALL, cfg/ and '
                            'Supervisor.tla together with the model' % (e['name'], ','.join(sorted(e['fixed'])), ','.join(sorted(expected_fixed))))
    return problems


# ---------------------------------------------------------------- manifest of the mirror files

def file_sha256(path):
    with open(path, 'rb') as f:
        data = f.read().replace(b'\r\n', b'\n')   # a Windows checkout may have CRLF; the repository stores LF
    return hashlib.sha256(data).hexdigest()


def manifest_lines(root=HERE):
    return ['%s *%s' % (file_sha256(os.path.join(root, name)), name) for name in MIRROR_FILES]


def verify_manifest(root=HERE):
    """-> list of problem lines."""
    path = os.path.join(root, MANIFEST)
    if not os.path.exists(path):
        return ['%s is missing (run: python tools/formal/tla/tlc_check.py --update-manifest)' % MANIFEST]
    recorded = {}
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    for line in lines:
        m = re.fullmatch(r'([0-9a-f]{64}) \*(\S+)', line.strip())
        if m:
            recorded[m.group(2)] = m.group(1)
    problems = []
    for name in MIRROR_FILES:
        if name not in recorded:
            problems.append('%s: %s is not listed' % (MANIFEST, name))
        elif recorded[name] != file_sha256(os.path.join(root, name)):
            problems.append('%s: %s changed since the manifest was written (intended? run --update-manifest and re-run the TLC check)' % (MANIFEST, name))
    return problems


def jar_sha256(root=HERE):
    with open(os.path.join(root, 'TLA2TOOLS.sha256'), encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'\b([0-9a-f]{64})\b', text)
    if not m:
        raise ValueError('TLA2TOOLS.sha256 has no sha256')
    return m.group(1)


# ---------------------------------------------------------------- docker

def docker(args, timeout=30):
    return subprocess.run(['docker'] + args, capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, MSYS_NO_PATHCONV='1'))


def image_state(image):
    """-> ('ok', label) | ('skipped', reason)."""
    try:
        p = docker(['image', 'inspect', image, '--format', '{{index .Config.Labels "%s"}}' % JAR_LABEL])
    except FileNotFoundError:
        return 'skipped', 'docker is not installed'
    except subprocess.TimeoutExpired:
        return 'skipped', 'docker does not answer'
    if p.returncode != 0:
        err = (p.stderr or '').strip().splitlines()
        if err and 'No such image' not in err[-1] and 'No such object' not in err[-1]:
            return 'skipped', 'docker is not usable: ' + err[-1][:200]
        return 'skipped', 'docker image %s not found; build it once with scripts/build-tlc-image.ps1 (tools/formal/tla/README.md)' % image
    return 'ok', p.stdout.strip()


class Job(threading.Thread):
    """One subprocess whose stdout is consumed line by line (TLC prints ~100 000 census lines) and parsed by `consume`."""

    def __init__(self, argv, consume, container=None):
        super().__init__(daemon=True)
        self.argv, self.consume, self.container = argv, consume, container
        self.result = None
        self.error = None
        self.returncode = None
        self.seconds = None
        self.process = None

    def run(self):
        started = time.time()
        try:
            self.process = subprocess.Popen(self.argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace',
                                            env=dict(os.environ, MSYS_NO_PATHCONV='1'))
            self.result = self.consume(self.process.stdout)
            self.returncode = self.process.wait()
        except Exception as exc:   # noqa: BLE001 - reported as a FAIL with the text
            self.error = '%s: %s' % (type(exc).__name__, exc)
        self.seconds = round(time.time() - started, 1)

    def kill(self):
        if self.container:
            try:
                docker(['kill', self.container], timeout=30)   # only containers this run started (unique name)
            except Exception:   # noqa: BLE001
                pass
        if self.process and self.process.poll() is None:
            self.process.kill()


def parse_py_stdout(stream):
    text = stream.read()
    for line in reversed(text.splitlines()):
        if line.startswith('{'):
            return json.loads(line)
    raise ValueError('py_census.py printed no JSON: ' + text[-300:])


def tlc_argv(image, source_tla_dir, container, cfg_name, workers):
    heap = '-Xmx1500m'
    return ['docker', 'run', '--rm', '--pull=never', '--name', container, '--network=none', '--read-only', '--cap-drop=ALL',
            '--security-opt=no-new-privileges', '--user=65534:65534', '--pids-limit=256', '--memory=2g', '--cpus=%d' % workers,
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=512m,mode=1777',
            '--mount', 'type=bind,source=%s,target=/spec,readonly' % source_tla_dir, '--workdir', '/tmp',
            image, 'java', '-XX:+UseParallelGC', heap, '-cp', '/opt/tlc/tla2tools.jar', 'tlc2.TLC', '-workers', str(workers),
            '-metadir', '/tmp/meta', '-config', '/spec/cfg/%s.cfg' % cfg_name, '/spec/Supervisor.tla']


def py_argv(py_image, source_tla_dir, entry):
    if py_image:
        return ['docker', 'run', '--rm', '--pull=never', '--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                '--user=65534:65534', '--memory=1g', '--cpus=1', '--env', 'PYTHONDONTWRITEBYTECODE=1',
                '--mount', 'type=bind,source=%s,target=/formal,readonly' % os.path.dirname(source_tla_dir), '--entrypoint', 'python3',
                py_image, '-I', '/formal/tla/py_census.py', '/dev/null'] + entry['py']
    return [sys.executable, '-I', os.path.join(source_tla_dir, 'py_census.py'), os.devnull] + entry['py']


def run_check(source, image, py_image, timeout, workers, only=None, jobs=DEFAULT_JOBS):
    """-> result dict (status PASS/SKIPPED/FAIL)."""
    started = time.time()
    tla_dir = os.path.abspath(os.path.join(source, 'tools', 'formal', 'tla'))
    result = {'status': None, 'reason': '', 'image': image, 'timeout_seconds': timeout, 'configs': {}, 'problems': [], 'seconds': 0}

    def finish(status, reason=''):
        result['status'], result['reason'] = status, reason
        result['seconds'] = round(time.time() - started, 1)
        return result

    state, info = image_state(image)
    if state == 'skipped':
        return finish('SKIPPED', info)
    jar = jar_sha256(tla_dir)
    result['jar_sha256'] = jar
    if info != jar:
        result['problems'].append('image %s has jar sha256 label "%s", expected %s: rebuild with scripts/build-tlc-image.ps1' % (image, info, jar))
        return finish('FAIL', 'wrong TLC image')
    try:
        with open(os.path.join(source, 'tools', 'formal', 'expected.json'), encoding='utf-8') as f:
            expected = json.load(f)
    except (OSError, ValueError) as exc:
        result['problems'].append('tools/formal/expected.json unreadable: %s' % exc)
        return finish('FAIL', 'setup')
    entries = [e for e in configurations() if (e['name'] in only if only else e['ci'])]
    if not entries:
        result['problems'].append('no such configuration: %s' % ','.join(only or []))
        return finish('FAIL', 'setup')
    result['problems'] += check_fixed_set(expected['fixed'], entries)
    result['problems'] += verify_manifest(tla_dir)
    if result['problems']:
        return finish('FAIL', 'the TLA+ mirror is not in step with the repository')
    token = '%d-%d' % (os.getpid(), int(started))
    runs = {}
    waiting, active = list(entries), []
    deadline = started + timeout
    while waiting or active:                 # at most `jobs` configurations at a time: the machine is shared, the limit is one
        while waiting and len(active) < max(1, jobs):
            e = waiting.pop(0)
            container = 'homensai-tlc-ci-%s-%s' % (token, e['name'])
            pair = (Job(tlc_argv(image, tla_dir, container, e['name'], workers), parse_tlc, container),
                    Job(py_argv(py_image, tla_dir, e), parse_py_stdout))
            runs[e['name'], 'tlc'], runs[e['name'], 'py'] = pair
            for job in pair:
                job.start()
            active.append(pair)
        active = [pair for pair in active if any(job.is_alive() for job in pair)]
        if time.time() >= deadline and (waiting or active):
            for pair in active:
                for job in pair:
                    job.kill()
            for pair in active:
                for job in pair:
                    job.join(30)
            result['problems'].append('time limit of %d s exceeded: the runs were stopped' % timeout)
            return finish('FAIL', 'timeout')
        time.sleep(0.2)
    for e in entries:
        name = e['name']
        t, p = runs[name, 'tlc'], runs[name, 'py']
        if t.error or p.error or p.returncode != 0 or t.result is None or p.result is None:
            tail = t.error or p.error or ('py_census exit %s' % p.returncode if p.returncode else 'no output')
            result['problems'].append('%s: could not run: %s' % (name, tail))
            continue
        problems = compare(name, t.result, p.result)
        result['problems'] += problems
        signatures = py_signatures(p.result)
        result['configs'][name] = {
            'tlc_states': t.result['distinct'], 'tlc_transitions': (t.result['generated'] or 1) - 1, 'tlc_depth': t.result['depth'],
            'py_states': p.result['states'], 'py_transitions': p.result['transitions'],
            'signatures': {k: v for k, v in signatures.items() if not k.startswith('STEP:')},
            'step_pairs': sum(1 for k in signatures if k.startswith('STEP:')),
            'step_edges': sum(v for k, v in signatures.items() if k.startswith('STEP:')),
            'tlc_seconds': t.seconds, 'py_seconds': p.seconds,
            'tlc_version': t.result['version'], 'equal': not problems}
    return finish('FAIL' if result['problems'] else 'PASS', result['problems'][0] if result['problems'] else '')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--source', default=os.path.abspath(os.path.join(HERE, '..', '..', '..')), help='repository root to check (default: this one)')
    ap.add_argument('--image', default=DEFAULT_IMAGE)
    ap.add_argument('--py-image', default='', help='run model.py in this docker image instead of the local python')
    ap.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT, help='seconds for the whole check (default %d)' % DEFAULT_TIMEOUT)
    ap.add_argument('--workers', type=int, default=3, help='TLC workers (= docker cpus) per configuration')
    ap.add_argument('--jobs', type=int, default=DEFAULT_JOBS, help='configurations at the same time')
    ap.add_argument('--result', default='', help='also write the result JSON here')
    ap.add_argument('--only', nargs='*', help='configuration names (default: the CI gate; a manual one is run by its name)')
    ap.add_argument('--verify-manifest', action='store_true')
    ap.add_argument('--update-manifest', action='store_true')
    a = ap.parse_args(argv)
    if a.update_manifest:
        with open(os.path.join(HERE, MANIFEST), 'w', newline='\n', encoding='utf-8') as f:
            f.write('\n'.join(manifest_lines()) + '\n')
        print('wrote ' + MANIFEST)
        return 0
    if a.verify_manifest:
        problems = verify_manifest()
        print('\n'.join(problems) if problems else 'manifest ok')
        return 1 if problems else 0
    result = run_check(a.source, a.image, a.py_image, a.timeout, a.workers, a.only, a.jobs)
    for name, c in sorted(result['configs'].items()):
        print('%-15s states TLC %d / model.py %d, transitions TLC %d / model.py %d, signatures %s, step pairs %d (%d edges), TLC %.1f s, model.py %.1f s: %s'
              % (name, c['tlc_states'], c['py_states'], c['tlc_transitions'], c['py_transitions'],
                 ','.join('%s=%d' % kv for kv in c['signatures'].items()) or '-', c['step_pairs'], c['step_edges'], c['tlc_seconds'], c['py_seconds'],
                 'EQUAL' if c['equal'] else 'DIFFERENT'))
    for line in result['problems']:
        print('PROBLEM ' + line)
    if result['status'] == 'SKIPPED':
        print('SKIPPED: %s (this check is optional; nothing was verified)' % result['reason'])
    line = 'TLC-CROSSCHECK ' + json.dumps(result, sort_keys=True)
    if a.result:
        with open(a.result, 'w', encoding='utf-8') as f:
            json.dump(result, f, sort_keys=True, indent=1)
    print(line)
    return 1 if result['status'] == 'FAIL' else 0


if __name__ == '__main__':
    sys.exit(main())
