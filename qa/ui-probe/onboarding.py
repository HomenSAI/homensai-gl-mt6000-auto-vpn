"""Frozen synthetic first-run browser checks; no router, credentials or external API."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid

from source_identity import content_type, freeze_preview

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to((ROOT/'private').resolve()) or out.exists():
        raise ValueError('FRESH-PRIVATE-OUTPUT-REQUIRED')
    frozen, identity, manifest = freeze_preview(ROOT)
    script = (Path(__file__).with_suffix('.js')).read_bytes()
    groups = [dict(design=d, lang=lang, width=w) for d in 'abc'
              for lang in ('en', 'ru') for w in (1440, 390)]
    if args.quick:
        groups = [groups[0], groups[-1]]
    run_id = uuid.uuid4().hex
    received = {}
    states = {}
    requests = {}
    event = threading.Event()
    out.mkdir(parents=True)
    manifest['scope'] = 'synthetic first-run fixture; no router or real terms acceptance'
    manifest['groups'] = groups
    manifest['runner_sha256'] = hashlib.sha256(script).hexdigest()
    (out/'source.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')

    class Handler(BaseHTTPRequestHandler):
        def allowed(self):
            origin = 'http://127.0.0.1:'+str(self.server.server_port)
            return (self.headers.get('Host') == origin[7:] and
                    self.headers.get('Origin', origin) == origin)

        def send(self, body, kind):
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            try:
                self.wfile.write(body)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                # Navigation cancels old assets; this is not a test verdict.
                pass

        def do_GET(self):
            if not self.allowed():
                self.send_error(403)
                return
            path = self.path.split('?', 1)[0]
            requests[path] = requests.get(path, 0)+1
            if path == '/__onboarding/runner':
                cfg = json.dumps(dict(id=run_id, groups=groups))
                self.send(('<!doctype html><meta charset=utf-8><body style="margin:0">'
                           '<iframe id=f style="border:0"></iframe><script>const CFG='+
                           cfg+';').encode()+script+b'</script>', 'text/html; charset=utf-8')
                return
            body = frozen.get(path)
            if body is None:
                self.send_error(404)
                return
            if path == '/qa/ui-preview/stub.js':
                query = parse_qs(urlsplit(self.headers.get('Referer', '')).query)
                case = query.get('case', [''])[0]
                if query.get('fixtureBackend') == [run_id] and case in {str(i) for i in range(len(groups))}:
                    prefix = ('window.fixtureOnboardingSaved='+json.dumps(states.get(case))+';'
                              'window.fixtureOnboardingBackend='+json.dumps('/__onboarding/save/'+run_id+'/'+case)+';\n')
                    body = prefix.encode()+body
            self.send(body, content_type(path))

        def do_POST(self):
            save_prefix = '/__onboarding/save/'+run_id+'/'
            saving = self.path.startswith(save_prefix) and self.path[len(save_prefix):] in {str(i) for i in range(len(groups))}
            if not self.allowed() or not (saving or self.path == '/__onboarding/result/'+run_id):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 256*1024:
                    raise ValueError()
                value = json.loads(self.rfile.read(length))
                if saving:
                    if not isinstance(value, list) or len(value) != 6 or not all(isinstance(part, dict) for part in value):
                        raise ValueError()
                    system, monitor, recovery, speed, telegram, appearance = value
                    settings = dict(onboarding_complete=True, onboarding_version=1,
                                    onboarding_pair_deferred=system['defer_pair'],
                                    appearance_language=appearance['language'], appearance_design=appearance['design'],
                                    appearance_theme=appearance['theme'], interval=monitor['interval'],
                                    checkpoint=monitor['checkpoint'], probe_limit=monitor['probe_limit'],
                                    plan_enabled=monitor['planning_enabled'],
                                    native_duration=system['duration'], native_session_loss=system['session_loss'])
                    if not system['defer_pair']:
                        settings.update(plan_source=system['source'], plan_target=system['target'], setup_complete=True)
                    settings.update({'recovery_'+key: item for key, item in recovery.items()})
                    settings.update({'speed_'+key: item for key, item in speed.items()})
                    # The synthetic backend never stores tokens or echoes request bodies.
                    if telegram.get('configure'):
                        settings.update({'telegram_'+key: item for key, item in telegram.items()
                                         if key not in ('configure', 'token', 'chat')})
                        settings['telegram_destination'] = telegram.get('chat', '')
                        settings['telegram_configured'] = bool(telegram.get('chat'))
                    states[self.path[len(save_prefix):]] = dict(settings=settings, servers=system['servers'])
                else:
                    if not isinstance(value, dict):
                        raise ValueError()
                    received.update(value)
            except (ValueError, OSError, KeyError, TypeError):
                self.send_error(400)
                return
            if saving:
                self.send(b'{"saved":true,"onboarding_complete":true,"onboarding_version":1}', 'application/json')
                return
            event.set()
            self.send_response(204)
            self.end_headers()

        def log_message(self, *unused):
            pass

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        child = subprocess.Popen([str(edge), '--headless=new', '--inprivate', '--disable-gpu',
                                  '--no-first-run', '--disable-background-networking',
                                  '--user-data-dir='+str(out/'browser-profile'),
                                  '--window-size=1600,1000',
                                  'http://127.0.0.1:'+str(server.server_port)+'/__onboarding/runner'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic()+min(1200, len(groups)*90+30)
            finished = False
            while time.monotonic() < deadline:
                if event.wait(1):
                    finished = True
                    break
                if child.poll() is not None:
                    received['errors'] = ['BROWSER-EXITED-BEFORE-RESULT']
                    break
        finally:
            subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            server.shutdown()
            worker.join(timeout=10)
    received.update(source_identity=identity, completed_at_utc=datetime.now(timezone.utc).isoformat())
    received.update(browser_exit_code=child.poll(), request_counts=requests)
    rows = received.get('rows', [])
    passed = (finished and not received.get('errors') and len(rows) == len(groups)
              and all(row.get('result') == 'PASS' for row in rows))
    received['result'] = 'PASS' if passed else 'FAIL'
    if not finished and not received.get('errors'):
        received['errors'] = ['BROWSER-HOST-DEADLINE']
    (out/'result.json').write_text(json.dumps(received, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(result=received['result'], cases=len(rows),
                          failures=[row for row in rows if row.get('result') != 'PASS'],
                          evidence=str(out/'result.json'))))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
