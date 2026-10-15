"""Crash only our child helper in a Linux container. No router commands."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

STAGES = ['intent-write', 'intent-sync', 'intent-replace', 'intent-rename', 'v4', 'v6',
          'config-write', 'config-sync', 'config-replace', 'config-rename', 'commit-write',
          'commit-sync', 'commit-replace', 'commit-rename', 'release']


def atomic_write(path, data, prefix, stop=None):
    pending = path.with_suffix('.pending')
    with pending.open('w', encoding='utf-8') as stream:
        json.dump(data, stream)
        stream.flush()
        crash(prefix + '-write', stop)
        os.fsync(stream.fileno())
        crash(prefix + '-sync', stop)
    os.replace(pending, path)
    crash(prefix + '-replace', stop)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    crash(prefix + '-rename', stop)


def crash(stage, stop):
    if stage == stop:
        os.kill(os.getpid(), signal.SIGKILL)


def helper(directory, stage):
    directory = Path(directory)
    atomic_write(directory / 'journal.json', {'phase': 'intent', 'before': 'primary', 'target': 'backup'}, 'intent', stage)
    atomic_write(directory / 'kernel.json', {'v4': 'backup', 'v6': 'primary'}, 'kernel')
    crash('v4', stage)
    atomic_write(directory / 'kernel.json', {'v4': 'backup', 'v6': 'backup'}, 'kernel')
    crash('v6', stage)
    atomic_write(directory / 'config.json', {'profile': 'backup'}, 'config', stage)
    atomic_write(directory / 'journal.json', {'phase': 'committed', 'target': 'backup'}, 'commit', stage)
    crash('release', stage)


def main():
    if sys.platform != 'linux':
        raise SystemExit('Run this test inside the existing Linux Docker container.')
    results = []
    for index in range(20):
        stage = STAGES[index % len(STAGES)]
        with tempfile.TemporaryDirectory(prefix='homensai-crash-') as directory:
            directory = Path(directory)
            atomic_write(directory / 'config.json', {'profile': 'primary'}, 'initial')
            atomic_write(directory / 'journal.json', {'phase': 'committed', 'target': 'primary'}, 'initial')
            child = subprocess.run([sys.executable, __file__, '--child', str(directory), stage],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            try:
                assert child.returncode == -signal.SIGKILL, 'Child did not stop at injected crash'
                journal = json.loads((directory / 'journal.json').read_text(encoding='utf-8'))
                config = json.loads((directory / 'config.json').read_text(encoding='utf-8'))
                chosen = journal['before'] if journal['phase'] == 'intent' else journal['target']
                # Reconciliation models a closed forwarding gate, not a live firewall operation.
                recovered = {'profile': chosen, 'v4': chosen, 'v6': chosen, 'verified': True}
                atomic_write(directory / 'config.json', recovered, 'recovery')
                expected = 'backup' if stage in ('commit-replace', 'commit-rename', 'release') else 'primary'
                assert chosen == expected, 'Incorrect recovery decision'
                assert recovered['v4'] == recovered['v6'] == recovered['profile']
                # Ignore .pending files; stable JSON paths must always contain complete documents.
                assert all(isinstance(json.loads(p.read_text()), dict) for p in directory.glob('*.json'))
                results.append({'case': index + 1, 'stage': stage, 'passed': True,
                                'config_before_recovery': config['profile'], 'recovered': chosen})
            except (AssertionError, ValueError) as error:
                results.append({'case': index + 1, 'stage': stage, 'passed': False, 'error': str(error)})
    report = {'suite': 'linux-child-process-crash', 'mode': 'real-process-filesystem-test-not-power-loss',
              'cases': len(results), 'passed': sum(r['passed'] for r in results),
              'failed': sum(not r['passed'] for r in results), 'results': results}
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report['failed']))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        helper(sys.argv[2], sys.argv[3])
    else:
        main()
