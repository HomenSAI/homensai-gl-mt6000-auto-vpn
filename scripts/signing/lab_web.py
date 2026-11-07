"""Local web page of the signing lab: stdlib http.server on 127.0.0.1 and a random port, nothing else. No --host option exists.

Access: a one-time token in the first URL becomes an HttpOnly SameSite=Strict cookie and is burned; POSTs also need the CSRF
token of the page, a matching Origin and application/json. Every request must carry Host 127.0.0.1:<port> (DNS rebinding).
The handler logs nothing. Answers travel in POST bodies only. A secret event is delivered once and then dropped from memory
of the event list; drills.json and DRILLS.html hold masked text only (lab_drills.mask). The rate limit of the codes is the
real gate of totp.py, because every code goes through the real tools.
"""
import hmac
import json
import queue
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_drills  # noqa: E402
import lab_mode  # noqa: E402

HOST = '127.0.0.1'
COOKIE = 'hsai_lab'
PAGE = Path(__file__).resolve().parent/'lab_ui.html'
MAX_BODY = 8192
TOKEN_SECONDS = 300
IDLE_SECONDS = 4*3600
PROMPT_SECONDS = 1800


class Op:
    """One running drill: the event list the page polls and the queue its answers arrive in."""
    def __init__(self, target):
        self.id = secrets.token_hex(8)
        self.target = target
        self.events = []
        self.answers = queue.Queue()
        self.lock = threading.Lock()
        self.waiting = False
        self.cancelled = False
        self.done = False

    def emit(self, event):
        with self.lock:
            self.events.append(event)

    def ask(self, kind, ru, en, prompt):
        self.waiting = True
        self.emit({'type': 'prompt', 'kind': kind, 'ru': ru, 'en': en, 'prompt': prompt})
        deadline = time.monotonic()+PROMPT_SECONDS
        try:
            while True:
                if self.cancelled or time.monotonic() > deadline:
                    raise lab_drills.DrillCancelled('Отменено')
                try:
                    return self.answers.get(timeout=0.2)
                except queue.Empty:
                    pass
        finally:
            self.waiting = False

    def read(self, after):
        """Events after `after`. A secret leaves here once: the stored event is replaced before the reply is sent."""
        rows = []
        with self.lock:
            for index in range(max(0, after), len(self.events)):
                rows.append(self.events[index])
                if self.events[index]['type'] == 'secret':
                    self.events[index] = {'type': 'secret-shown'}
            return rows, len(self.events), self.done


class App:
    def __init__(self, lab, session=None):
        self.lab = lab
        self.session = session or lab_drills.Session(lab)
        self.token = secrets.token_urlsafe(32)
        self.token_born = time.monotonic()
        self.cookie = None
        self.csrf = secrets.token_urlsafe(32)
        self.ops = {}
        self.active = None
        self.touched = time.monotonic()
        self.port = None
        self.server = None

    def open_token(self, value):
        """The token works once and only for a short time."""
        if self.token is None or not value or time.monotonic()-self.token_born > TOKEN_SECONDS:
            return False
        if not hmac.compare_digest(self.token, value):
            return False
        self.token = None
        self.cookie = secrets.token_urlsafe(32)
        return True

    def has_cookie(self, header):
        if not self.cookie:
            return False
        for part in (header or '').split(';'):
            name, _, value = part.strip().partition('=')
            if name == COOKIE and hmac.compare_digest(value, self.cookie):
                return True
        return False

    def start(self, target, work):
        if self.active is not None and not self.active.done:
            raise ValueError('LAB-BUSY: another drill is running')
        op = Op(target)
        self.ops = {op.id: op}
        self.active = op

        def body():
            try:
                work(op)
            except Exception as error:  # the page must learn the end of a run; the text is masked
                op.emit({'type': 'result', 'status': lab_drills.FAIL, 'message': lab_drills.mask(error, self.session.memory.known())})
            finally:
                op.done = True
        threading.Thread(target=body, daemon=True).start()
        return op

    def run_drill(self, drill, auto):
        if drill not in {row[0] for row in lab_drills.TITLES}:
            raise ValueError('LAB-UNKNOWN-DRILL')
        return self.start(drill, lambda op: lab_drills.run_drill(self.session, drill, op.emit, op.ask, auto))

    def run_all(self):
        return self.start('all', lambda op: lab_drills.run_all(self.lab, emit=op.emit, sandbox=self.session.sandbox, network=self.session.network))

    def reset(self):
        if self.active is not None and not self.active.done:
            raise ValueError('LAB-BUSY: another drill is running')
        self.lab.reset()
        self.lab.ensure()
        self.session.memory = lab_drills.Memory()
        self.ops, self.active = {}, None

    def state(self):
        row = lab_drills.lab_state(self.lab)
        row['sandbox'] = self.session.sandbox.label if self.session.sandbox else ''
        row['busy'] = self.active.target if self.active and not self.active.done else ''
        return row


class Handler(BaseHTTPRequestHandler):
    server_version = 'HomenS.AI-lab'
    sys_version = ''
    protocol_version = 'HTTP/1.1'
    timeout = 60

    def log_message(self, *arguments):
        """Nothing is logged: not the token, not a path, not an address."""

    @property
    def app(self):
        return self.server.app

    def send(self, status, body=b'', content_type='application/json; charset=utf-8', extra=()):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Pragma', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        for name, value in extra:
            self.send_header(name, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def json(self, status, data):
        self.send(status, json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def host_ok(self):
        return self.headers.get('Host') == '%s:%d' % (HOST, self.server.server_address[1])

    def refuse(self, status=403, code='LAB-FORBIDDEN'):
        self.json(status, {'error': code})

    def authorised(self):
        return self.app.has_cookie(self.headers.get('Cookie'))

    def page(self):
        nonce = secrets.token_urlsafe(16)
        drills = [{'id': row[0], 'ru': row[1], 'en': row[2]} for row in lab_drills.TITLES]
        text = PAGE.read_text(encoding='utf-8')
        for name, value in (('NONCE', nonce), ('CSRF', self.app.csrf), ('PROGRAM', lab_drills.program_version()), ('STYLE', lab_drills.style_version()),
                            ('DRILLS', json.dumps(drills, ensure_ascii=False))):
            text = text.replace('{{%s}}' % name, value)
        policy = ("default-src 'none'; script-src 'nonce-%s'; style-src 'nonce-%s'; img-src data:; connect-src 'self'; "
                  "base-uri 'none'; form-action 'none'; frame-ancestors 'none'" % (nonce, nonce))
        self.send(200, text.encode('utf-8'), 'text/html; charset=utf-8', [('Content-Security-Policy', policy)])

    def do_GET(self):
        self.app.touched = time.monotonic()
        if not self.host_ok():
            return self.refuse(403, 'LAB-HOST')
        path, _, query = self.path.partition('?')
        arguments = dict(item.partition('=')[::2] for item in query.split('&') if item)
        if path == '/' and 't' in arguments:
            if not self.app.open_token(arguments['t']):
                return self.send(403, 'Ссылка уже использована или устарела. Запустите lab.py заново.'.encode('utf-8'), 'text/plain; charset=utf-8')
            cookie = '%s=%s; HttpOnly; SameSite=Strict; Path=/' % (COOKIE, self.app.cookie)
            return self.send(303, b'', 'text/plain', [('Location', '/'), ('Set-Cookie', cookie)])
        if not self.authorised():
            return self.refuse(403, 'LAB-NO-SESSION')
        if path == '/':
            return self.page()
        if path == '/api/state':
            return self.json(200, self.app.state())
        if path == '/api/events':
            op = self.app.ops.get(arguments.get('op'))
            if op is None:
                return self.refuse(404, 'LAB-NO-OP')
            try:
                after = int(arguments.get('after', '0'))
            except ValueError:
                return self.refuse(400, 'LAB-BAD-REQUEST')
            rows, position, done = op.read(after)
            return self.json(200, {'events': rows, 'next': position, 'done': done})
        if path == '/report':
            if not self.app.lab.report.is_file():
                return self.send(404, 'Отчёта пока нет'.encode('utf-8'), 'text/plain; charset=utf-8')
            return self.send(200, self.app.lab.report.read_bytes(), 'text/html; charset=utf-8',
                             [('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'")])
        return self.refuse(404, 'LAB-NOT-FOUND')

    def post_ok(self):
        """Host, session, CSRF token, Origin, content type and size. Any miss refuses before the body is looked at."""
        port = self.server.server_address[1]
        origin = self.headers.get('Origin')
        if not self.host_ok() or origin not in (None, 'http://%s:%d' % (HOST, port)):
            return 'LAB-ORIGIN'
        if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
            return 'LAB-ORIGIN'
        if not self.authorised():
            return 'LAB-NO-SESSION'
        if not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), self.app.csrf):
            return 'LAB-CSRF'
        if (self.headers.get('Content-Type') or '').split(';')[0].strip() != 'application/json':
            return 'LAB-CONTENT-TYPE'
        return None

    def do_POST(self):
        self.app.touched = time.monotonic()
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            length = -1
        problem = self.post_ok() or ('LAB-BAD-REQUEST' if not 0 <= length <= MAX_BODY else None)
        if problem:
            self.rfile.read(min(max(length, 0), 2*MAX_BODY))  # unread bytes would turn the refusal into a connection reset
            self.close_connection = True
            return self.refuse(403, problem)
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self.refuse(400, 'LAB-BAD-REQUEST')
        try:
            return self.route(self.path, body)
        except ValueError as error:
            return self.json(409, {'error': lab_drills.mask(error, self.app.session.memory.known())})

    def route(self, path, body):
        app = self.app
        if path == '/api/run':
            op = app.run_drill(str(body.get('drill')), bool(body.get('auto')))
            return self.json(200, {'op': op.id})
        if path == '/api/run-all':
            return self.json(200, {'op': app.run_all().id})
        if path == '/api/answer':
            op = app.ops.get(body.get('op'))
            if op is None or not op.waiting:
                return self.refuse(409, 'LAB-NO-PROMPT')
            op.answers.put(str(body.get('value', '')))
            return self.json(200, {'ok': True})
        if path == '/api/cancel':
            op = app.ops.get(body.get('op'))
            if op:
                op.cancelled = True
            return self.json(200, {'ok': True})
        if path == '/api/reset':
            if body.get('confirm') != 'RESET':
                return self.refuse(400, 'LAB-CONFIRM')
            app.reset()
            return self.json(200, {'ok': True})
        if path == '/api/quit':
            self.json(200, {'ok': True})
            threading.Thread(target=app.server.shutdown, daemon=True).start()
            return None
        return self.refuse(404, 'LAB-NOT-FOUND')


def make_server(lab, session=None):
    """Bound to 127.0.0.1 only, port chosen by the system. Returns (server, one-time URL)."""
    app = App(lab, session)
    server = ThreadingHTTPServer((HOST, 0), Handler)
    server.daemon_threads = True
    server.app = app
    app.server = server
    app.port = server.server_address[1]
    return server, 'http://%s:%d/?t=%s' % (HOST, app.port, app.token)


def serve(lab, browser=True):
    server, url = make_server(lab)

    def watchdog():
        while True:
            time.sleep(30)
            if time.monotonic()-server.app.touched > IDLE_SECONDS:
                server.shutdown()
                return
    threading.Thread(target=watchdog, daemon=True).start()
    print('*** %s ***' % (lab_mode.BANNER % lab), flush=True)
    opened = browser and webbrowser.open(url)
    if not opened:
        print('Open this one-time link in the browser: %s' % url, flush=True)
    else:
        print('The page is open in the browser. Press Ctrl+C or the "Stop" button to end.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
