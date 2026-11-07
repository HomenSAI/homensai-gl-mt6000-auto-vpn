"""End to end on a fresh lab: the real tools, the real HTTP gates, real one-time codes from the seed of the test QR."""
import json
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import ceremony
import keytool
import lab_mode
import totp

root = Path(sys.argv[1])
if root.exists():
    shutil.rmtree(root, ignore_errors=True)
lab = lab_mode.resolve(str(root))
lab.ensure()
c = ceremony.Ceremony(lab)
assert keytool.main(['new-keys', '--skip-totp', '--emergency', '--lab', str(root)], store=c.store,
                    console=type('C', (keytool.Console,), {'confirm': lambda s, p: 'yes', 'say': lambda s, t='': None})()) in (0, 2)
if not c.store.has('main.key.dpapi'):
    raise SystemExit('lab keys not created')
server, url = ceremony.serve(c)
threading.Thread(target=server.serve_forever, daemon=True).start()
port = server.server_address[1]
base = 'http://127.0.0.1:%d' % port


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)
try:
    opener.open(url)
except urllib.error.HTTPError as e:
    assert e.code == 303, e.code
    cookie = e.headers['Set-Cookie'].split(';')[0]
try:
    urllib.request.urlopen(url)
    raise SystemExit('used link opened again')
except urllib.error.HTTPError as e:
    assert e.code == 403
H = {'Cookie': cookie}


def get(path):
    return urllib.request.urlopen(urllib.request.Request(base+path, headers=H)).read()


page = get('/').decode()
csrf = re.search(r"CSRF='([^']+)'", page).group(1)


def post(path, body, csrf_value=None, origin=None):
    r = urllib.request.Request(base+path, json.dumps(body).encode(), {**H, 'Content-Type': 'application/json',
                               'Origin': origin or base, 'X-CSRF': csrf_value or csrf}, method='POST')
    return urllib.request.urlopen(r).read()


for bad in ({'csrf_value': 'x'}, {'origin': 'http://evil'}):
    try:
        post('/step', {'step': 'main'}, **bad)
        raise SystemExit('forged POST accepted')
    except urllib.error.HTTPError as e:
        assert e.code == 403
at = 0
seed = None
store = c.store
got = {}


def drive(step):
    global at, seed
    post('/step', {'step': step})
    deadline = time.time()+150
    while time.time() < deadline:
        data = json.loads(get('/events?after=%d' % at))
        again = json.loads(get('/events?after=%d' % at))
        at = data['next']
        for e in data['events']:
            if e['type'] == 'qr':
                assert 'svg' in e and e['text'], e
                if e['name'] == 'phone':
                    seed = parse_qs(urlparse(unquote(e['text'])).query)['secret'][0]
                else:
                    got[e['name']] = e['text']
                    assert all(r.get('type') != 'qr' or r['name'] != e['name'] for r in again['events']), 'secret served twice'
            elif e['type'] == 'codes':
                got['codes'] = e['codes']
            elif e['type'] == 'ask':
                step_now = int(time.time()//30)
                while getattr(drive, 'last', None) == step_now:
                    time.sleep(1)
                    step_now = int(time.time()//30)
                drive.last = step_now
                post('/answer', {'value': totp.totp(totp.seed_bytes(seed), time.time())})
            elif e['type'] == 'error':
                raise SystemExit('step %s failed: %s' % (step, e['text']))
            elif e['type'] == 'done':
                return
        time.sleep(0.5)
    raise SystemExit('timeout in %s' % step)


drive('phone')
assert len(set(got['codes'])) == 10, got.get('codes')
drive('main')
drive('reserve')
drive('age')
assert got['main'].startswith(lab_mode.PAYLOAD_TAG+':MAIN:')
assert got['reserve'].startswith(lab_mode.PAYLOAD_TAG+':RESERVE:')
assert got['age'].startswith('AGE-SECRET-KEY-1')
state = json.loads(get('/state'))
assert state['totp'] and state['age'] and not state['real']
disk = b''.join(p.read_bytes() for p in Path(store.root).rglob('*') if p.is_file())
assert got['main'].encode() not in disk and got['codes'][0].encode() not in disk
print('CEREMONY-LAB-PASS: phone, 10 codes, main, reserve, age; link one-time; forged POST refused; secrets served once; none in clear on disk')
server.shutdown()
