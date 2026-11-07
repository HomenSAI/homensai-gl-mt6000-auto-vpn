"""Bounded alpha9 semantic mutations, exclusively in a new git-archive snapshot.

Run with Python 3.9+ and git, node, lua5.1/luac5.1 available (CI tools image).
  python router/tests/mutate_alpha9_final.py --commit FULL_SHA --scratch /tmp/a9-new --report /tmp/a9.json
No implicit HEAD, no checkout edits, no router/network. Scratch must not exist.
The owner-decision inventory is read as AST without executing its legacy main.
"""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time

REPO = Path(__file__).resolve().parents[2]
LIB = 'router/files/usr/lib/homensai-vpn/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory='+str(REPO), '-C', str(REPO), *args])


def inventory(root, include_codecs=False):
    source = root/'router/tests/mutate_owner_decisions.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                 and isinstance(n.value.func, ast.Name) and n.value.func.id == 'main')]
    previous = sys.argv
    try:
        sys.argv = [str(source), str(root)]
        ns = {'__name__': 'inventory_only', '__file__': str(source)}
        exec(compile(tree, str(source), 'exec'), ns)
    finally:
        sys.argv = previous
    rows = []
    for name, path, old, new, steps in ns['MUTANTS']:
        rows.append(dict(name='owner: '+name, path=Path(path).relative_to(root).as_posix(),
                         old=old, new=new, steps=steps))
    def add(name, path, old, new, steps):
        rows.append(dict(name=name, path=path, old=old, new=new, steps=steps))
    pybrief = [(['python3', '-m', 'unittest', 'test_telegram_brief', '-q'], 'router/tests')]
    luabrief = [(['python3', '-m', 'unittest', 'test_lua_speed_telegram.TelegramMatchesPython.test_explicit_russian_brief',
                 'test_lua_speed_telegram.TelegramMatchesPython.test_brief_actual_route_changes_asymmetric', '-q'], 'router/tests')]
    ui = [(['node', 'router/tests/test_auto_state_table_ui.js'], '.'),
          (['node', 'router/tests/test_auto_signal_ui.js'], '.')]
    for label, old, new in [
        ('checking light', "checking:{lamp:'yellow'", "checking:{lamp:'red'"),
        ('failure keeps owner on', "failure:{lamp:'red',enabled:true", "failure:{lamp:'red',enabled:false"),
        ('off light', "off:{lamp:'off'", "off:{lamp:'green'"),
        ('wait gate', 'var waitingNow=sessionRuns&&blockers.length&&blockers.every(', 'var waitingNow=false&&blockers.length&&blockers.every('),
        ('priority real failure', 'return AUTO_TRANSIENT.indexOf(code)<0;', 'return false;'),
    ]:
        add('signal: '+label, 'router/auto_panel.inc.js', old, new, ui)
    for label, old, new in [
        ('population window', "-5 <= now-s['time'] <= 300", "-5 <= now-s['time'] <= 30"),
        ('minimum samples', 'if len(rows) < 6:', 'if len(rows) < 1:'),
        ('failures only', "event.get('kind') == 'FAILURE'", "event.get('kind') == 'RECOVERY'"),
        ('real route changes', "e.get('route_changed') is True", "e.get('route_changed') is not True"),
        ('exclude trials', "or e.get('trial'):", 'or False:'),
        ('mandatory alarm', "lines.append('Авария: '+(alarm+' · автопереключение остановлено' if alarm else 'нет'))", 'pass'),
    ]:
        add('brief py: '+label, LIB+'telegram_brief.py', old, new, pybrief)
    for label, old, new in [
        ('population window', 'now-fnum(row.time)<=300', 'now-fnum(row.time)<=30'),
        ('minimum samples', 'if n<6 then return nil end', 'if n<1 then return nil end'),
        ('failures only', "e.kind=='FAILURE' and inside(e)", "e.kind=='RECOVERY' and inside(e)"),
        ('real route changes', 'e.route_changed==true', 'e.route_changed~=true'),
        ('exclude trials', 'not truthy(e.trial) and e.transition_completed', 'true and e.transition_completed'),
    ]:
        add('brief lua: '+label, LIB+'lua/telegram.lua', old, new, luabrief)
    add('traceback: mask dynamic frame tokens', LIB+'lua/loop_guard.lua',
        "and string.gsub(masked,'[%w%+/=_%-]+',token) or '(frame withheld)'",
        "and masked or '(frame withheld)'", [(['lua5.1', 'router/tests/lua/test_monitor_guard.lua'], '.')])
    publication = [(['python3', '-m', 'unittest', 'discover', '-s', 'qa', '-p', 'test_publication*.py', '-q'], '.')]
    for label, old, new in [
        ('append-only notes', 'not new_notes.startswith(old_notes)', 'False'),
        ('asset git identity', "raise ValueError('PUBLICATION-SIGNED-ASSET-MISMATCH')", 'pass'),
        ('Lua receipt', "raise ValueError('PUBLICATION-CI-LUA')", 'pass'),
        ('runtime bool', "if type(row.get('runtime_only')) is not bool:", 'if False:'),
    ]:
        add('publication: '+label, 'scripts/publish-reviewed.py', old, new, publication)
    if include_codecs:
        codecs = [(['python3', '-m', 'unittest', 'discover', '-s', 'qa', '-p', 'test_publication_record.py',
                    '-k', 'PublicationCodecs', '-q'], '.')]
        add('codec: locale default instead of explicit UTF8', 'scripts/publish-reviewed.py',
            "encoding='utf-8',errors='strict'", "encoding=None,errors='strict'", codecs)
        add('codec: missing reader output accepted', 'scripts/publish-reviewed.py',
            'if reply.stdout is None or reply.stderr is None:', 'if False:', codecs)
    return rows


def command(argv, cwd, timeout=600):
    argv = [sys.executable if a in ('python3', 'python') else a for a in argv]
    try:
        done = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        output = done.stdout.decode('utf-8', 'replace')
        # unittest success with skipped Lua/Node coverage is never a baseline PASS.
        skipped = bool(re.search(r'OK \(skipped=|Ran 0 tests|skipped [1-9]', output))
        return dict(code=done.returncode, skipped=skipped, output=output)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(code=None, skipped=False, output=type(error).__name__)


def suites(root, steps):
    result = []
    for argv, directory in steps:
        row = command(argv, root/directory)
        result.append(dict(argv=argv, cwd=directory, **row))
        if row['code'] != 0 or row['skipped']:
            break
    return result


def classify(check, steps):
    if check['code'] != 0:
        return 'INVALID'  # includes unavailable compiler; never semantic KILLED
    if any(s['code'] is None or s['skipped'] for s in steps):
        return 'INCONCLUSIVE'
    failures = [s for s in steps if s['code'] != 0]
    if not failures:
        return 'SURVIVED'
    text = '\n'.join(s['output'] for s in failures)
    if re.search(r'SyntaxError|IndentationError|ImportError|ModuleNotFoundError|cannot find module|Cannot find module|error loading module', text):
        return 'INVALID'
    # Require evidence of a reached assertion, not merely nonzero exit.
    return 'KILLED' if re.search(r'AssertionError|FAIL:|not equal|expected.*got|: got .*expected|expected:|assertion failed', text, re.I) else 'INCONCLUSIVE'


def syntax(root, path):
    if path.suffix == '.py':
        try:
            compile(path.read_text(encoding='utf-8'), str(path), 'exec')
            return dict(code=0, output='Python compile PASS')
        except SyntaxError as error:
            return dict(code=1, output=str(error))
    if path.suffix == '.lua':
        return command(['luac5.1', '-p', str(path)], root)
    return command(['node', '--check', str(path)], root)


def selftest():
    ok = dict(code=0)
    assert classify(dict(code=1), []) == 'INVALID'
    assert classify(ok, [dict(code=1, skipped=False, output='SyntaxError')]) == 'INVALID'
    assert classify(ok, [dict(code=1, skipped=False, output='AssertionError: route')]) == 'KILLED'
    assert classify(ok, [dict(code=0, skipped=False, output='OK')]) == 'SURVIVED'
    assert classify(ok, [dict(code=None, skipped=False, output='TimeoutExpired')]) == 'INCONCLUSIVE'
    assert classify(ok, [dict(code=0, skipped=True, output='OK (skipped=1)')]) == 'INCONCLUSIVE'
    assert classify(ok, [dict(code=1, skipped=False, output='failed to start')]) == 'INCONCLUSIVE'
    assert classify(ok, [dict(code=1, skipped=False, output='FAIL mask: got 8, expected nil')]) == 'KILLED'
    print('runner classification selftest PASS (8 cases; no application mutation executed)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit')
    parser.add_argument('--scratch', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--filter', default='')
    parser.add_argument('--inventory-only', action='store_true')
    parser.add_argument('--include-codecs', action='store_true', help='add two explicit UTF8/reader-output guard mutations (49 total)')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    if args.selftest:
        selftest(); return 0
    if not args.commit or not re.fullmatch('[0-9a-f]{40}', args.commit) or not args.scratch or not args.report:
        parser.error('--commit FULL_SHA --scratch NEW_DIRECTORY --report FILE required')
    scratch = args.scratch.resolve()
    if scratch.exists():
        parser.error('scratch already exists; choose a new disposable path')
    sha = git('rev-parse', args.commit+'^{commit}').decode().strip()
    archive = git('archive', '--format=tar', sha)
    scratch.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk() or not (scratch/member.name).resolve().is_relative_to(scratch):
                raise ValueError('unsafe archive member')
        tar.extractall(scratch)
    report = dict(source=sha, tree=git('rev-parse', sha+'^{tree}').decode().strip(),
                  archive_sha256=digest(archive), runner_sha256=digest(Path(__file__).read_bytes()),
                  scratch=str(scratch), baseline=[], mutants=[], scope='bounded alpha9; no full CI or physical acceptance',
                  untested=['all other legacy mutant inventories', 'physical router', 'full semantic branch completeness'])
    def save():
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = [r for r in inventory(scratch, args.include_codecs) if args.filter in r['name']]
    report['inventory'] = [dict(name=r['name'], path=r['path'], occurrences=(scratch/r['path']).read_text(encoding='utf-8').count(r['old'])) for r in rows]
    if args.inventory_only:
        report['verdict'] = 'INVENTORY-ONLY'; save(); return 0
    baseline_steps = []
    for row in rows:
        for step in row['steps']:
            if step not in baseline_steps:
                baseline_steps.append(step)
    report['baseline'] = suites(scratch, [([sys.executable, 'router/build_sidebar_ui.py'], '.')] + baseline_steps)
    if any(s['code'] != 0 or s['skipped'] for s in report['baseline']):
        report['verdict'] = 'BASELINE-FAILED'; save(); return 2
    for row in rows:
        path = scratch/row['path']; raw = path.read_bytes()
        text = raw.decode('utf-8').replace('\r\n', '\n')
        result = dict(name=row['name'], path=row['path'], source_sha256=digest(raw), occurrences=text.count(row['old']))
        if result['occurrences'] != 1:
            result['verdict'] = 'NOT-APPLIED'
        else:
            started = time.monotonic()
            try:
                path.write_bytes(text.replace(row['old'], row['new'], 1).encode('utf-8'))
                result['syntax'] = syntax(scratch, path)
                result['steps'] = []
                if result['syntax']['code'] == 0:
                    if path.suffix == '.js':
                        result['build'] = command([sys.executable, 'router/build_sidebar_ui.py'], scratch)
                        if result['build']['code'] != 0:
                            result['syntax'] = result['build']
                    if result['syntax']['code'] == 0:
                        result['steps'] = suites(scratch, row['steps'])
                result['verdict'] = classify(result['syntax'], result['steps'])
            finally:
                path.write_bytes(raw)
                if path.suffix == '.js':
                    restored = command([sys.executable, 'router/build_sidebar_ui.py'], scratch)
                    if restored['code'] != 0:
                        raise RuntimeError('restored generated UI failed to build')
            result['seconds'] = round(time.monotonic()-started, 3)
        report['mutants'].append(result)
        print(result['verdict'], result['name'], flush=True)
        save()
    counts = {key: sum(r['verdict'] == key for r in report['mutants']) for key in
              ('KILLED', 'SURVIVED', 'NOT-APPLIED', 'INVALID', 'INCONCLUSIVE')}
    report['counts'] = counts
    report['verdict'] = 'PASS-BOUNDED' if rows and counts['KILLED'] == len(rows) else 'INCOMPLETE'
    save()
    return 0 if report['verdict'] == 'PASS-BOUNDED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
