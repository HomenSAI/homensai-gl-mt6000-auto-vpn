"""Owner key ceremony: a local page that binds the phone, shows the release keys and the age identity once and prints paper sheets.

`ceremony.py --lab DIR` works on a test lab; the real store needs the explicit `--real`. It only calls the real tools
(keytool, agetool), so every code gate stays. 127.0.0.1 only, random port, a one-time link, a cookie, a CSRF token, an exact
Host check, no-store, a strict CSP and no request log. Secrets stay in the page memory: nothing is written here, and each
secret is dropped from the server the moment the page has read it.
"""
import argparse
import contextlib
import hmac
import html
import io
import json
import queue
import re
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent/'backupcrypt')]
import agetool  # noqa: E402
import keytool  # noqa: E402
import lab_mode  # noqa: E402
import qr  # noqa: E402
import secret_store  # noqa: E402

HOST = '127.0.0.1'
COOKIE = 'hsai_ceremony'
TOKEN_SECONDS = 300
ANSWER_SECONDS = 1800
MAX_BODY = 4096
CODE_LINE = re.compile(r'^\s*\d+\.\s+(\S.*)$')
SAFE_LINE = ('Key ', 'TOTP-', 'AGE-IDENTITY-CREATED', 'age identity for recipient', 'That code did not')


class Cancelled(Exception):
    pass


class Flow:
    def __init__(self):
        self.events = []
        self.lock = threading.Lock()
        self.answers = queue.Queue()
        self.running = False
        self.cancelled = False

    def emit(self, row):
        with self.lock:
            self.events.append(row)

    def read(self, after):
        """A secret leaves once: the stored copy is replaced before the reply goes out."""
        with self.lock:
            rows = self.events[max(0, after):]
            for index in range(max(0, after), len(self.events)):
                if self.events[index].get('secret'):
                    self.events[index] = {'type': 'gone'}
            return rows, len(self.events), self.running

    def ask(self, prompt):
        self.emit({'type': 'ask', 'prompt': prompt})
        deadline = time.monotonic()+ANSWER_SECONDS
        while True:
            if self.cancelled or time.monotonic() > deadline:
                raise Cancelled('CANCELLED')
            try:
                return self.answers.get(timeout=0.2)
            except queue.Empty:
                pass


class WebConsole(keytool.Console):
    """The console of the real tools. Output is dropped unless it is on the safe list; secrets arrive through show_qr only."""
    def __init__(self, flow, name):
        super().__init__()
        self.flow = flow
        self.name = name
        self.codes = []
        self.taking_codes = False

    def code(self, prompt=''):
        return self.flow.ask('code')

    def secret(self, prompt):
        raise Cancelled('SECRET-INPUT-NOT-USED')

    def confirm(self, prompt):
        return 'n' if 'print-friendly' in prompt else ''

    def say(self, text=''):
        if text.startswith('RECOVERY CODES'):
            self.taking_codes = True
            return
        match = CODE_LINE.match(text)
        if self.taking_codes and match:
            self.codes.append(match.group(1).strip())
            return
        if self.taking_codes:
            self.taking_codes = False
            self.flow.emit({'type': 'codes', 'secret': True, 'codes': list(self.codes)})
        if text.startswith('Manual entry key: '):
            self.flow.emit({'type': 'manual', 'secret': True, 'text': text.split(': ', 1)[1]})
        elif text.startswith(SAFE_LINE):
            self.flow.emit({'type': 'info', 'text': text})

    def show_qr(self, text, mode, title):
        svg = qr.render_svg(qr.encode(text, ecc='Q'), scale=4, border=4)
        self.flow.emit({'type': 'qr', 'secret': True, 'name': self.name, 'svg': svg, 'text': text})


class Ceremony:
    def __init__(self, lab=None):
        self.lab = lab
        self.store = lab.store() if lab else secret_store.Store()
        self.flow = Flow()

    def extra(self):
        return ['--lab', str(self.lab.root)] if self.lab else []

    def tool(self, module, name, *argv):
        console = WebConsole(self.flow, name)
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(io.StringIO()):
            code = module.main(list(argv)+self.extra(), store=self.store, console=console)
        if code:
            raise ValueError(captured.getvalue().strip().splitlines()[-1][:160] if captured.getvalue().strip() else 'TOOL-FAILED')

    def state(self):
        return {'real': self.lab is None, 'totp': self.store.has('totp.seed.dpapi'),
                'main': self.store.has('main.key.dpapi'), 'reserve': self.store.has('reserve.key.dpapi'),
                'age': self.store.has(agetool.IDENTITY), 'running': self.flow.running}

    def steps(self, step):
        if step == 'phone':
            self.tool(keytool, 'phone', 'setup-totp', '--qr', 'none')
        elif step == 'codes':
            self.tool(keytool, 'codes', 'new-recovery-codes')
        elif step == 'main' or step == 'reserve':
            self.tool(keytool, step, 'reveal', '--key', step, '--qr', 'none')
        elif step == 'age':
            if not self.store.has(agetool.IDENTITY):
                self.tool(agetool, 'age', 'new-identity')
            self.tool(agetool, 'age', 'reveal', '--qr', 'none')
        else:
            raise ValueError('UNKNOWN-STEP')

    def start(self, step):
        if self.flow.running:
            raise ValueError('BUSY')
        self.flow.running = True
        self.flow.cancelled = False

        def body():
            try:
                self.steps(step)
                self.flow.emit({'type': 'done', 'step': step})
            except (Cancelled, ValueError, OSError) as error:
                self.flow.emit({'type': 'error', 'text': str(error)[:200]})
            finally:
                self.flow.running = False
        threading.Thread(target=body, daemon=True).start()


class App:
    def __init__(self, ceremony):
        self.ceremony = ceremony
        self.token = secrets.token_urlsafe(32)
        self.born = time.monotonic()
        self.cookie = None
        self.csrf = secrets.token_urlsafe(32)

    def open_token(self, value):
        if self.token is None or not value or time.monotonic()-self.born > TOKEN_SECONDS or not hmac.compare_digest(self.token, value):
            return False
        self.token, self.cookie = None, secrets.token_urlsafe(32)
        return True

    def has_cookie(self, header):
        for part in (header or '').split(';'):
            name, _, value = part.strip().partition('=')
            if self.cookie and name == COOKIE and hmac.compare_digest(value, self.cookie):
                return True
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = 'HomenS.AI-ceremony'
    sys_version = ''
    protocol_version = 'HTTP/1.1'
    timeout = 60

    def log_message(self, *arguments):
        """Nothing is logged."""

    def send(self, status, body=b'', kind='application/json; charset=utf-8', extra=()):
        self.send_response(status)
        for name, value in (('Content-Type', kind), ('Content-Length', str(len(body))), ('Cache-Control', 'no-store'),
                            ('X-Content-Type-Options', 'nosniff'), ('X-Frame-Options', 'DENY'), ('Referrer-Policy', 'no-referrer'))+tuple(extra):
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def json(self, status, data):
        self.send(status, json.dumps(data, ensure_ascii=False).encode('utf-8'))

    @property
    def app(self):
        return self.server.app

    def host_ok(self):
        return self.headers.get('Host') == '%s:%d' % (HOST, self.server.server_address[1])

    def do_GET(self):
        if not self.host_ok():
            return self.json(403, {'error': 'HOST'})
        url = urlparse(self.path)
        if url.path == '/':
            token = parse_qs(url.query).get('t', [''])[0]
            if token and self.app.open_token(token):
                cookie = '%s=%s; HttpOnly; SameSite=Strict; Path=/' % (COOKIE, self.app.cookie)
                return self.send(303, extra=(('Location', '/'), ('Set-Cookie', cookie)))
            if not self.app.has_cookie(self.headers.get('Cookie')):
                return self.json(403, {'error': 'LINK-USED'})
            return self.page()
        if not self.app.has_cookie(self.headers.get('Cookie')):
            return self.json(403, {'error': 'FORBIDDEN'})
        if url.path == '/state':
            return self.json(200, self.app.ceremony.state())
        if url.path == '/events':
            after = int(parse_qs(url.query).get('after', ['0'])[0] or 0)
            rows, total, running = self.app.ceremony.flow.read(after)
            return self.json(200, {'events': rows, 'next': total, 'running': running})
        return self.json(404, {'error': 'NOT-FOUND'})

    def do_POST(self):
        origin = 'http://%s:%d' % (HOST, self.server.server_address[1])
        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_BODY:
            self.close_connection = True
            return self.json(413, {'error': 'TOO-LARGE'})
        raw = self.rfile.read(length)
        if (not self.host_ok() or self.headers.get('Origin') != origin or not self.app.has_cookie(self.headers.get('Cookie'))
                or self.headers.get('Content-Type') != 'application/json'
                or not hmac.compare_digest(self.headers.get('X-CSRF') or '', self.app.csrf)):
            return self.json(403, {'error': 'FORBIDDEN'})
        data = json.loads(raw or b'{}')
        flow = self.app.ceremony.flow
        try:
            if self.path == '/step':
                self.app.ceremony.start(str(data.get('step')))
            elif self.path == '/answer':
                flow.answers.put(str(data.get('value', ''))[:64])
            elif self.path == '/cancel':
                flow.cancelled = True
            else:
                return self.json(404, {'error': 'NOT-FOUND'})
        except ValueError as error:
            return self.json(409, {'error': str(error)})
        return self.json(200, {'ok': True})

    def page(self):
        nonce = secrets.token_urlsafe(16)
        real = self.app.ceremony.lab is None
        body = PAGE.replace('@NONCE@', nonce).replace('@CSRF@', self.app.csrf).replace('@MODE@', 'real' if real else 'test')
        policy = "default-src 'none'; script-src 'nonce-%s'; style-src 'nonce-%s'; img-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'" % (nonce, nonce)
        self.send(200, body.encode('utf-8'), 'text/html; charset=utf-8', (('Content-Security-Policy', policy),))


PAGE = r'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ключи HomenS.AI</title><style nonce="@NONCE@">
body{font:16px system-ui,sans-serif;margin:0;background:#f4f6f8;color:#16202a}main{max-width:860px;margin:auto;padding:16px}
.b{padding:10px 16px;font-weight:700;color:#fff;background:#b3261e}.b.test{background:#8a6d00}section{background:#fff;border-radius:12px;padding:16px;margin:12px 0}
button{min-height:44px;padding:8px 16px;border-radius:8px;border:1px solid #0b57d0;background:#0b57d0;color:#fff;font-size:15px;margin:4px 6px 4px 0}
button.s{background:#fff;color:#0b57d0}input{font-size:20px;padding:8px;width:200px}code{word-break:break-all}.e{color:#b3261e}.ok{color:#146c2e}.q svg{width:220px;height:220px}
#sheet{display:none}@media print{body{background:#fff}main,.b{display:none}#sheet{display:block;font:11pt sans-serif;color:#000}
.pg{page-break-after:always}.it{border:1px solid #000;padding:6pt;margin:6pt 0;page-break-inside:avoid;overflow:hidden}.it svg{float:right;width:38mm;height:38mm;margin-left:6pt}
.it code{font-size:9pt}ol{columns:2;margin:4pt 0;font:11pt monospace}h1{font-size:15pt;margin:0}h2{font-size:12pt;margin:0 0 3pt}p{margin:3pt 0}}
</style><div class="b" id="banner"></div><main><section><h2>Шаги</h2><p id="st"></p>
<p>Каждый шаг показывает секрет один раз. Перед шагом 2 дождись нового кода в Authenticator: один код работает один раз.</p>
<button data-s="phone">1. Привязать телефон и получить коды</button><button data-s="codes" class="s">Новые коды восстановления</button>
<button data-s="main">2. Показать main</button><button data-s="reserve">3. Показать reserve</button><button data-s="age">4. Создать и показать age</button>
<p id="ask" hidden><b>Введи 6 цифр из Authenticator:</b> <input id="code" inputmode="numeric" autocomplete="off"> <button id="send">Подтвердить</button> <button id="cancel" class="s">Отмена</button></p>
<p id="log"></p></section><section id="out"></section><section><h2>Печать</h2>
<p>Печатай только на своём принтере по кабелю, не в PDF и не в облачный принтер. Рекомендуется два листа в разных местах.</p>
<button id="p1">Лист 1: main, age, коды</button><button id="p2">Лист 2: reserve</button><button id="p3" class="s">Всё на одном листе</button>
<p>После печати и сохранения закрой вкладку: секреты живут только в памяти страницы.</p></section></main><div id="sheet"></div>
<script nonce="@NONCE@">
const MODE='@MODE@',CSRF='@CSRF@',$=i=>document.getElementById(i);let n=0,data={codes:[]};
const INFO={main:['Основной ключ подписи (main)','Подписывает каждое обновление HomenS.AI Auto VPN. Нужен, если этот ПК потерян: восстановление командой import. Если лист украден, сразу выпусти обновление с отзывом main ключом reserve.'],
reserve:['Резервный ключ подписи (reserve)','Не используется в обычной работе. Нужен только если main потерян или украден: подписывает обновление с отзывом main. Храни отдельно от main.'],
age:['Ключ шифрования резервных копий (age)','Открывает зашифрованные архивы проекта. Кодов восстановления у него нет: без этого ключа архивы не открыть никогда.']};
$('banner').textContent=MODE==='real'?'НАСТОЯЩИЕ КЛЮЧИ. Никому не показывай и не вставляй в чат.':'ТЕСТ: тестовые ключи лаборатории';$('banner').className=MODE==='real'?'b':'b test';
function post(p,b){return fetch(p,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':CSRF},body:JSON.stringify(b||{})})}
function log(t,c){const d=document.createElement('div');d.textContent=t;if(c)d.className=c;$('log').append(d)}
function svgNode(s){return new DOMParser().parseFromString(s,'image/svg+xml').documentElement}
function card(title,text,svg){const s=document.createElement('div');s.className='q';const h=document.createElement('h3');h.textContent=title;s.append(h);if(svg)s.append(svgNode(svg));const c=document.createElement('p');const k=document.createElement('code');k.textContent=text;c.append(k);s.append(c);$('out').append(s)}
function handle(e){if(e.type==='ask'){$('ask').hidden=false;$('code').value='';$('code').focus()}
else if(e.type==='qr'){const name=e.name==='phone'?'phone':e.name;if(name==='phone'){card('Сканируй этот QR в Google Authenticator','Это привязка телефона, на лист не печатается',e.svg)}else{data[name]=e;card(INFO[name][0],e.text,e.svg)}}
else if(e.type==='manual')card('Ручной ввод в Authenticator',e.text)
else if(e.type==='codes'){data.codes=e.codes;card('Коды восстановления',e.codes.join('  '))}
else if(e.type==='info')log(e.text)
else if(e.type==='error'){$('ask').hidden=true;log('Ошибка: '+e.text,'e')}
else if(e.type==='done'){$('ask').hidden=true;log('Готово: '+e.step,'ok');state()}}
async function poll(){try{const r=await(await fetch('/events?after='+n)).json();r.events.forEach(handle);n=r.next}catch(e){}setTimeout(poll,800)}
async function state(){const s=await(await fetch('/state')).json();$('st').textContent='Телефон: '+(s.totp?'привязан':'нет')+' · main: '+(s.main?'есть':'нет')+' · reserve: '+(s.reserve?'есть':'нет')+' · age: '+(s.age?'есть':'нет')}
document.querySelectorAll('[data-s]').forEach(b=>b.onclick=async()=>{const r=await post('/step',{step:b.dataset.s});if(!r.ok)log('Сейчас занято','e')});
$('send').onclick=()=>{post('/answer',{value:$('code').value});$('ask').hidden=true};$('cancel').onclick=()=>{post('/cancel');$('ask').hidden=true};
function item(k){const e=data[k],d=document.createElement('div');d.className='it';if(!e){d.textContent='НЕ ПОКАЗАН НА ЭКРАНЕ: '+INFO[k][0];return d}d.append(svgNode(e.svg));const h=document.createElement('h2');h.textContent=INFO[k][0];const p=document.createElement('p');p.textContent=INFO[k][1];const c=document.createElement('code');c.textContent=e.text;d.append(h,p,c);return d}
function codes(){const d=document.createElement('div');d.className='it';const h=document.createElement('h2');h.textContent='Коды восстановления телефона';const p=document.createElement('p');p.textContent='Если телефон потерян, каждый код один раз заменяет 6 цифр из Authenticator. Ключами они не являются.';const o=document.createElement('ol');data.codes.forEach(c=>{const l=document.createElement('li');l.textContent=c;o.append(l)});d.append(h,p,o);if(!data.codes.length)d.append('КОДЫ НЕ ПОКАЗАНЫ НА ЭКРАНЕ');return d}
function sheet(title,parts){const s=$('sheet');s.textContent='';const g=document.createElement('div');g.className='pg';const h=document.createElement('h1');h.textContent='HomenS.AI Auto VPN · '+title;const p=document.createElement('p');p.textContent=(MODE==='real'?'СЕКРЕТНО. Настоящие ключи. ':'ТЕСТ, не настоящие ключи. ')+'Дата: '+new Date().toLocaleDateString('ru')+'. Не фотографировать, не вставлять в чат. Разработчик · Serhii Khomenko · homensai.com';g.append(h,p);parts.forEach(x=>g.append(x));s.append(g);window.print()}
$('p1').onclick=()=>sheet('Лист 1: главное',[item('main'),item('age'),codes()]);$('p2').onclick=()=>sheet('Лист 2: резерв',[item('reserve')]);$('p3').onclick=()=>sheet('Все ключи',[item('main'),item('reserve'),item('age'),codes()]);
state();poll();
</script></html>'''


def serve(ceremony, port=0, opener=None):
    server = ThreadingHTTPServer((HOST, port), Handler)
    server.app = App(ceremony)
    url = 'http://%s:%d/?t=%s' % (HOST, server.server_address[1], server.app.token)
    return server, url


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--lab', help='work on this test lab')
    p.add_argument('--real', action='store_true', help='work on the real keys')
    p.add_argument('--no-browser', action='store_true')
    args = p.parse_args(argv)
    if bool(args.lab) == bool(args.real):
        p.error('choose exactly one: --lab DIR or --real')
    lab = lab_mode.resolve(args.lab) if args.lab else None
    if lab is not None:
        lab.ensure()
    ceremony = Ceremony(lab)
    if lab is not None and not ceremony.store.has('main.key.dpapi'):
        quiet = type('Quiet', (keytool.Console,), {'confirm': lambda self, prompt: 'yes', 'say': lambda self, text='': None})()
        keytool.main(['new-keys', '--skip-totp', '--emergency', '--lab', str(lab.root)], store=ceremony.store, console=quiet)
    server, url = serve(ceremony)
    print('Open this one-time link in the browser: %s' % url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    server.serve_forever()


if __name__ == '__main__':
    main()
