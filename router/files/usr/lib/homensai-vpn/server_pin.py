"""Trust on first use of the VPN servers' keys (lua/server_pin.lua is the same behaviour; shared cases
router/tests/server_pin_cases.json). Owner option, default warn:
    uci set homensai_vpn.main.server_key_pin='warn'|'enforce'|'off'; uci commit homensai_vpn

What is pinned, per SERVER IDENTITY = profile id + configured server host (never the resolved IP):
  * WireGuard: the peer public key the running tunnel really uses (`wg show <wgclientN> endpoints`, one peer);
    the host is the peer's uci end_point host, or its name for provider peers without end_point (NordVPN via GL:
    the name is the server host, server_pick.endpoints). A NordVPN/GL pool that hands the profile another server
    gives another host, so another identity: a first use, not a change. Only the SAME server with ANOTHER key is
    a change.
  * OpenVPN: SHA-256 of every CA certificate (DER) of the running client's config (/proc/<pid>/cmdline --config,
    inline <ca> or `ca <file>`, relative to --cd); the host is the config's first `remote`. The server's own
    certificate is checked by OpenVPN against that CA; a changed CA is what a substituted server needs.
When: only for a channel the monitor just measured healthy (its probe verdict code null), at most every RECHECK s per
profile and at once when its live server endpoint changed; network.<interface>.config must name the profile before and
after the reads (a profile replaced in between is not attributed).
States: first observation -> pinned (event SERVER-KEY-PINNED); same key -> nothing; another key -> changed (event
SERVER-KEY-CHANGED, status.server_keys lists it, every further different key is another event). A change is sticky
until the administrator accepts it (homensai-vpn-server-key accept <profile|all>; event SERVER-KEY-ACCEPTED) or forgets
the profile (forget: the next observation pins anew, event SERVER-KEY-FORGOTTEN). Mode enforce (native_switch.key_unaccepted,
review 04.11.2026): SERVER-KEY-UNACCEPTED while a profile has an unaccepted change. A Start waits for the channel that carries the
traffic afterwards (native_switch.carrying_unaccepted), a server hand-over for either; a working pair refuses only a move ONTO that channel, leaving it, the emergency return to a clean channel, a Stop and
every rollback stay free (GL's own tunnel is not stopped: the router keeps what the owner configured).
Storage: RUNTIME/server-keys.json (tmpfs, every change) and PERSIST/server-keys.json (flash): written at once for a
change, an acceptance or a forget, and at most every PERSIST_SPACING s for new first-use records; last_seen is RAM only.
A damaged file: SERVER-KEY-STATE-CORRUPT once, a copy in RUNTIME/server-keys.corrupt.json, pinning starts afresh.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

STATE = 'server-keys.json'
REQUEST = 'server-keys-accept.json'
CORRUPT_COPY = 'server-keys.corrupt.json'
CONFIG = '/etc/config/homensai_vpn'
PINNED = 'SERVER-KEY-PINNED'
CHANGED = 'SERVER-KEY-CHANGED'
ACCEPTED = 'SERVER-KEY-ACCEPTED'
FORGOTTEN = 'SERVER-KEY-FORGOTTEN'
BLOCKED = 'SERVER-KEY-UNACCEPTED'
CORRUPT = 'SERVER-KEY-STATE-CORRUPT'
MODES = ('off', 'warn', 'enforce')
DEFAULT_MODE = 'warn'
RECHECK = 600
PERSIST_SPACING = 600
MAX_RECORDS = 256
MAX_TEXT = 512
MAX_CONFIG = 262144
MAX_CA = 65536

_PROFILE = re.compile(r'(wireguard|openvpn):([A-Za-z0-9_]{1,64})')
_IFACE = re.compile(r'(wgclient|ovpnclient)[0-9]{1,4}')
_WG_KEY = re.compile(r'[A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=')
_MODE = re.compile(r"[ \t]*option[ \t]+server_key_pin[ \t]+'?([A-Za-z]+)'?[ \t]*")
_HOST = re.compile(r'[A-Za-z0-9.:-]{1,253}')
_B64 = re.compile(r'[A-Za-z0-9+/]+={0,2}')
BEGIN, END = '-----BEGIN CERTIFICATE-----', '-----END CERTIFICATE-----'
WS = ' \t\n\r\f\v'  # ASCII white space only, as Lua's %s (Python's own classes also match Unicode spaces)
_TOKEN = re.compile(r'[^ \t\n\r\f\v]+')


# ---- pure parsing (shared cases) -----------------------------------------------------------------------------

def mode(text):
    """The option of /etc/config/homensai_vpn; the last valid line wins, anything else is the default (warn)."""
    found = DEFAULT_MODE
    if not isinstance(text, str):
        return found
    for line in text.split('\n'):
        match = _MODE.fullmatch(line)
        if match and match.group(1) in MODES:
            found = match.group(1)
    return found


def wg_fingerprint(raw):
    """`wg show <if> endpoints` -> 'wg:<peer public key>' for exactly one peer, else None."""
    if not isinstance(raw, str) or len(raw) > 4096:
        return None
    lines = [line for line in raw.split('\n') if _TOKEN.search(line)]
    if len(lines) != 1:
        return None
    parts = _TOKEN.findall(lines[0])
    if len(parts) != 2 or not _WG_KEY.fullmatch(parts[0]):
        return None
    return 'wg:'+parts[0]


def cert_digests(text):
    """Sorted unique SHA-256 (hex) of the DER of every PEM certificate in `text`; None when there is none or one is
    malformed (a half-readable CA is never pinned)."""
    if not isinstance(text, str):
        return None
    out, pos = [], 0
    while True:
        start = text.find(BEGIN, pos)
        if start < 0:
            break
        end = text.find(END, start+len(BEGIN))
        if end < 0:
            return None
        body = re.sub(r'[ \t\n\r\f\v]', '', text[start+len(BEGIN):end])
        if not _B64.fullmatch(body) or len(body) % 4:
            return None
        out.append(hashlib.sha256(base64.b64decode(body)).hexdigest())
        pos = end+len(END)
    return sorted(set(out)) or None


def ovpn_parts(text):
    """(inline CA text | None, `ca` file | None, first `remote` host lower case | None) of an OpenVPN config."""
    if not isinstance(text, str):
        return None, None, None
    inline = None
    start = text.find('<ca>')
    if start >= 0:
        end = text.find('</ca>', start)
        if end > start:
            inline = text[start+4:end]
    ca, remote = None, None
    for line in text.split('\n'):
        parts = _TOKEN.findall(line)
        if len(parts) >= 2 and parts[0] == 'ca' and ca is None:
            ca = parts[1].strip('"\'')
        if len(parts) >= 2 and parts[0] == 'remote' and remote is None and _HOST.fullmatch(parts[1]):
            remote = parts[1].lower()
    return inline, ca, remote


def wg_host(uci_text, section):
    """The configured server host of a WireGuard peer from `uci -q show wireguard.<section>` (server_pick rules)."""
    import server_pick
    data = server_pick.parse_uci(uci_text) if isinstance(uci_text, str) else {}
    found = server_pick.endpoints('wireguard', (data.get('wireguard') or {}).get(section))
    host = found[0]['host'].lower() if found else None
    return host if host and _HOST.fullmatch(host) else None


def identity(profile, host):
    return '%s|%s' % (profile, host or '-')


# ---- state ---------------------------------------------------------------------------------------------------

def empty():
    return {'schema': 1, 'records': {}}


def _text(value):
    return isinstance(value, str) and 1 <= len(value.encode('utf-8', 'surrogatepass')) <= MAX_TEXT  # bytes, as Lua


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1e12


def _record_ok(record):
    return (isinstance(record, dict) and all(_text(record.get(k)) for k in ('profile', 'host', 'protocol', 'fingerprint', 'observed'))
            and record.get('state') in ('pinned', 'changed') and _number(record.get('first_seen')) and _number(record.get('last_seen'))
            and all(record.get(k) is None or _number(record.get(k)) for k in ('changed_at', 'accepted_at')))


def load(text):
    """(state, corrupt). A missing file is an empty state; anything malformed is reported once as corrupt."""
    if text is None:
        return empty(), False
    try:
        data = json.loads(text)
    except ValueError:
        return empty(), True
    if (not isinstance(data, dict) or not _number(data.get('schema')) or data['schema'] != 1
            or not isinstance(data.get('records'), dict)
            or len(data['records']) > 2*MAX_RECORDS or not all(_record_ok(r) for r in data['records'].values())):
        return empty(), True
    for record in data['records'].values():
        record.setdefault('changed_at', None)
        record.setdefault('accepted_at', None)
    return {'schema': 1, 'records': data['records']}, False


def _event(code, record, now):
    return {'time': now, 'code': code, 'profile': record['profile'], 'host': record['host'],
            'fingerprint': record['observed'], 'pinned': record['fingerprint']}


def evict(state):
    records = state['records']
    while len(records) > MAX_RECORDS:
        pinned = [key for key in records if records[key]['state'] == 'pinned']
        if not pinned:
            return
        del records[min(pinned, key=lambda k: (records[k]['last_seen'], k))]


def observe(state, live, now):
    """One live observation -> (events, urgency: 'urgent' | 'new' | None)."""
    records = state['records']
    key, fingerprint = live['identity'], live['fingerprint']
    record = records.get(key)
    if record is None:
        record = records[key] = {'profile': live['profile'], 'host': live['host'], 'protocol': live['protocol'],
                                 'fingerprint': fingerprint, 'observed': fingerprint, 'state': 'pinned',
                                 'first_seen': now, 'last_seen': now, 'changed_at': None, 'accepted_at': None}
        evict(state)
        return [_event(PINNED, record, now)], 'new'
    previous = record['observed']
    record['last_seen'] = now
    record['observed'] = fingerprint
    if fingerprint == record['fingerprint']:
        return [], None
    if record['state'] == 'pinned':
        record['state'] = 'changed'
        record['changed_at'] = now
        return [_event(CHANGED, record, now)], 'urgent'
    if fingerprint != previous:
        return [_event(CHANGED, record, now)], 'urgent'
    return [], None


def apply_request(state, request, now):
    """The administrator's accept/forget request (CLI) -> (events, urgency)."""
    if not isinstance(request, dict) or request.get('action') not in ('accept', 'forget'):
        return [], None
    target = request.get('profile')
    if not (target == '*' or isinstance(target, str) and _PROFILE.fullmatch(target)):
        return [], None
    # The page (rpc server_key_accept) names the key the administrator checked: a key that changed again after that
    # is not accepted (the CLI request has no 'observed' and accepts the key seen now, as before).
    seen = request.get('observed')
    records, events = state['records'], []
    for key in sorted(records):
        record = records[key]
        if target != '*' and record['profile'] != target:
            continue
        if request['action'] == 'accept':
            if record['state'] != 'changed' or (seen is not None and record['observed'] != seen):
                continue
            record.update(fingerprint=record['observed'], state='pinned', accepted_at=now, changed_at=None)
            events.append(_event(ACCEPTED, record, now))
        else:
            del records[key]
            events.append(_event(FORGOTTEN, record, now))
    return events, ('urgent' if events else None)


def blocker(state, mode_value, profiles):
    """SERVER-KEY-UNACCEPTED when enforcing and one of `profiles` has an unaccepted change, else None."""
    if mode_value != 'enforce' or not isinstance(state, dict):
        return None
    wanted = set(p for p in profiles if isinstance(p, str))
    for record in (state.get('records') or {}).values():
        if isinstance(record, dict) and record.get('state') == 'changed' and record.get('profile') in wanted:
            return BLOCKED
    return None


def public(state, mode_value):
    if mode_value == 'off':
        return {'mode': 'off'}
    records = state['records']
    changed = [{'profile': records[k]['profile'], 'host': records[k]['host'], 'pinned': records[k]['fingerprint'],
                'observed': records[k]['observed'], 'changed_at': records[k]['changed_at']}
               for k in sorted(records) if records[k]['state'] == 'changed']
    return {'mode': mode_value, 'pinned': len(records)-len(changed), 'changed': changed,
            'code': CHANGED if changed else None}


# ---- live reads ----------------------------------------------------------------------------------------------

def ovpn_live(interface, io):
    """(fingerprint, host) of the running OpenVPN client of `interface`, or (None, None)."""
    pid = (io['read']('/var/run/ovpnclient-'+interface+'.pid', 32) or '').strip(WS)
    if not re.fullmatch(r'[0-9]{1,10}', pid) or not 1 < int(pid) < 2**31:
        return None, None
    process = '/proc/'+pid
    if (io['read'](process+'/comm', 64) or '').strip(WS) != 'openvpn':
        return None, None
    args = (io['read'](process+'/cmdline', 16384) or '').strip('\0').split('\0')

    def value(flag):
        if args.count(flag) != 1 or args.index(flag)+1 >= len(args):
            return None
        return args[args.index(flag)+1]
    if value('--dev') != interface:
        return None, None
    config, cd = value('--config'), value('--cd')

    def resolve(path):
        if not path or '\n' in path:
            return None
        if path.startswith('/'):
            return path
        return cd.rstrip('/')+'/'+path if cd and cd.startswith('/') else None
    config = resolve(config)
    text = io['read'](config, MAX_CONFIG) if config else None
    inline, ca, host = ovpn_parts(text)
    if inline is None and ca is not None:
        path = resolve(ca)
        inline = io['read'](path, MAX_CA) if path else None
    digests = cert_digests(inline)
    return ('ovpn-ca:'+','.join(digests) if digests else None), host


def read_live(profile, io):
    """{profile, protocol, host, fingerprint, identity} of a healthy measured channel, or None (not attributable)."""
    if not isinstance(profile, dict):
        return None
    pid, interface = profile.get('id'), profile.get('interface')
    match = _PROFILE.fullmatch(pid) if isinstance(pid, str) else None
    if not match or not isinstance(interface, str) or not _IFACE.fullmatch(interface):
        return None
    protocol, section = match.group(1), match.group(2)
    if (protocol == 'wireguard') != interface.startswith('wgclient'):
        return None

    def bound():
        out = io['run'](['uci', '-q', 'get', 'network.'+interface+'.config'])
        return isinstance(out, str) and out.strip(WS) == section
    if not bound():
        return None
    if protocol == 'wireguard':
        fingerprint = wg_fingerprint(io['run'](['wg', 'show', interface, 'endpoints']))
        host = wg_host(io['run'](['uci', '-q', 'show', 'wireguard.'+section]), section)
    else:
        fingerprint, host = ovpn_live(interface, io)
    if fingerprint is None or not bound():
        return None
    return {'profile': pid, 'protocol': protocol, 'host': host or '-', 'fingerprint': fingerprint,
            'identity': identity(pid, host)}


# ---- the monitor's part ----------------------------------------------------------------------------------------

class Pins:
    """Held by the monitor (agent.py; lua/monitor.lua has the same object). io: read(path, limit) -> text | None,
    run(argv) -> stdout text | None (non-zero exit), write_ram(path, text), write_flash(path, text), remove(path)."""
    def __init__(self, runtime, persist, io):
        self.runtime, self.persist, self.io = runtime.rstrip('/'), persist.rstrip('/'), io
        self.checked, self.flash_at, self.dirty, self.notice = {}, None, False, None
        text = io['read'](self.runtime+'/'+STATE, 2*1024*1024)
        source = text if text is not None else io['read'](self.persist+'/'+STATE, 2*1024*1024)
        self.state, corrupt = load(source)
        if corrupt:
            self.notice = CORRUPT
            io['write_ram'](self.runtime+'/'+CORRUPT_COPY, source[:262144])

    def save(self, urgency, now):
        text = json.dumps(self.state, sort_keys=True, separators=(',', ':'))
        self.io['write_ram'](self.runtime+'/'+STATE, text)
        if urgency is not None:
            self.dirty = True
        due = self.flash_at is None or now < self.flash_at or now-self.flash_at >= PERSIST_SPACING
        if self.dirty and (urgency == 'urgent' or due):
            self.io['write_flash'](self.persist+'/'+STATE, text)
            self.flash_at, self.dirty = now, False

    def step(self, rows, mode_value, now):
        """-> (events, public block). rows: the pass's channel rows (id, interface, code, server_endpoint)."""
        now = int(now)
        events, urgency, touched = [], None, False

        def worse(a, b):
            return 'urgent' if 'urgent' in (a, b) else ('new' if 'new' in (a, b) else None)
        if self.notice:
            events.append({'time': now, 'code': self.notice})
            self.notice, urgency, touched = None, 'urgent', True
        request_path = self.runtime+'/'+REQUEST
        raw = self.io['read'](request_path, 4096)
        if raw is not None:
            try:
                request = json.loads(raw)
            except ValueError:
                request = None
            found, level = apply_request(self.state, request, now)
            events += found
            urgency, touched = worse(urgency, level), True
            self.io['remove'](request_path)
        if mode_value != 'off':
            for row in sorted((r for r in rows if isinstance(r, dict) and isinstance(r.get('id'), str)), key=lambda r: r['id']):
                if row.get('code') is not None:
                    continue
                endpoint = row.get('server_endpoint')
                signature = ('%s|%s' % (endpoint.get('host'), endpoint.get('port'))) if isinstance(endpoint, dict) else '-'
                last = self.checked.get(row['id'])
                if last and last[1] == signature and 0 <= now-last[0] < RECHECK:
                    continue
                self.checked[row['id']] = (now, signature)
                try:
                    live = read_live(row, self.io)
                except (OSError, ValueError, TypeError, KeyError):
                    live = None
                if live is None:
                    continue
                found, level = observe(self.state, live, now)
                events += found
                urgency, touched = worse(urgency, level), True
        if touched or self.dirty:
            self.save(urgency, now)
        return events, public(self.state, mode_value)


def router_io(runtime=None):
    def read(path, limit):
        try:
            with open(path, 'rb') as stream:
                data = stream.read(limit+1)
        except OSError:
            return None
        return None if len(data) > limit else data.decode('latin-1')

    def run(argv):
        try:
            out = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=2)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.decode('latin-1') if out.returncode == 0 else None

    def write(path, text, sync):
        directory = os.path.dirname(path)
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, pending = tempfile.mkstemp(dir=directory, prefix='.'+os.path.basename(path)+'.', suffix='.pending')
        try:
            with os.fdopen(fd, 'w', encoding='latin-1') as stream:
                stream.write(text)
                stream.flush()
                if sync:
                    os.fsync(stream.fileno())
            os.replace(pending, path)
            if sync and hasattr(os, 'O_DIRECTORY'):  # POSIX: the rename itself reaches the flash
                handle = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(handle)
                finally:
                    os.close(handle)
        finally:
            if os.path.exists(pending):
                os.unlink(pending)

    def remove(path):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    return {'read': read, 'run': run, 'write_ram': lambda p, t: write(p, t, False),
            'write_flash': lambda p, t: write(p, t, True), 'remove': remove}


def gate(read, runtime='/var/run/homensai-vpn', persist='/etc/homensai-vpn', profiles=()):
    """The Auto diagnostic's check (native_switch.diagnostic, lua backend.diagnostic): read(path) -> text | None.
    runtime/persist: directory text or a pathlib.Path (then the reader gets a Path)."""
    mode_value = mode(read(CONFIG))
    if mode_value != 'enforce':
        return None

    def at(base):
        return base/STATE if hasattr(base, 'joinpath') else base.rstrip('/')+'/'+STATE
    text = read(at(runtime))
    state, _ = load(text if text is not None else read(at(persist)))
    return blocker(state, mode_value, profiles)


# ---- the page: rpc server_key_accept (answered by agent.py whichever monitor runs) ----------------------------------

def rpc_accept(arguments, runtime='/var/run/homensai-vpn', persist='/etc/homensai-vpn', io=None, now=None):
    """The page's button "Accept the new key": {'profile': <profile id>, 'observed': <the key the administrator checked>}.
    Only a profile with an unaccepted change whose key is still that key is queued: the same request file as
    `homensai-vpn-server-key accept`, plus 'observed', applied by the running monitor (Lua or Python) at its next pass.
    -> {'queued': bool, 'code': None | code}."""
    io = io or router_io()
    now = time.time() if now is None else now
    if not isinstance(arguments, dict) or set(arguments) != {'profile', 'observed'}:
        return {'queued': False, 'code': 'RPC-UNEXPECTED-ARGS'}
    profile, observed = arguments['profile'], arguments['observed']
    if not (isinstance(profile, str) and _PROFILE.fullmatch(profile)) or not (isinstance(observed, str) and 0 < len(observed) <= MAX_TEXT):
        return {'queued': False, 'code': 'SERVER-KEY-PROFILE-INVALID'}
    text = io['read'](runtime+'/'+STATE, 2*1024*1024)
    state, _ = load(text if text is not None else io['read'](persist+'/'+STATE, 2*1024*1024))
    if not any(r['profile'] == profile and r['state'] == 'changed' and r['observed'] == observed for r in state['records'].values()):
        return {'queued': False, 'code': 'SERVER-KEY-NOT-CHANGED'}
    io['write_ram'](runtime+'/'+REQUEST, json.dumps({'action': 'accept', 'profile': profile, 'observed': observed,
                                                     'time': now}, sort_keys=True))
    return {'queued': True, 'code': None}


# ---- administrator command (/usr/sbin/homensai-vpn-server-key) ---------------------------------------------------

USAGE = ('usage: homensai-vpn-server-key list | accept <profile|all> [--offline] | forget <profile|all> [--offline]\n'
         '  list     pinned servers and unaccepted key changes (mode from option server_key_pin)\n'
         '  accept   trust the key now seen for a changed server (after checking it with the provider)\n'
         '  forget   drop the pins of a profile; its next healthy check pins anew (first use)\n'
         '  --offline  apply directly when the service is stopped (otherwise the monitor applies it at its next pass)')


def cli(argv, io=None, runtime='/var/run/homensai-vpn', persist='/etc/homensai-vpn', now=None, wait=60.0, out=print):
    io = io or router_io()
    now = time.time() if now is None else now
    args = [a for a in argv if a != '--offline']
    offline = '--offline' in argv
    if not args or args[0] not in ('list', 'accept', 'forget') or (args[0] != 'list') != (len(args) == 2) or len(args) > 2:
        out(USAGE)
        return 2
    if args[0] == 'list':
        text = io['read'](runtime+'/'+STATE, 2*1024*1024)
        state, corrupt = load(text if text is not None else io['read'](persist+'/'+STATE, 2*1024*1024))
        view = public(state, mode(io['read'](CONFIG, 65536)))
        view['records'] = [dict(state['records'][k], identity=k) for k in sorted(state['records'])]
        if corrupt:
            view['notice'] = CORRUPT
        out(json.dumps(view, indent=1, sort_keys=True))
        return 0
    target = '*' if args[1] == 'all' else args[1]
    if target != '*' and not _PROFILE.fullmatch(target):
        out('SERVER-KEY-PROFILE-INVALID: expected wireguard:<section>, openvpn:<section> or all')
        return 2
    request = {'action': args[0], 'profile': target, 'time': now}
    if offline:
        pins = Pins(runtime, persist, io)
        found, level = apply_request(pins.state, request, now)
        pins.save(level, now)
        for event in found:
            out('%s %s %s' % (event['code'], event['profile'], event['host']))
        out('APPLIED %d record(s)' % len(found))
        return 0 if found else 1
    io['write_ram'](runtime+'/'+REQUEST, json.dumps(request, sort_keys=True))
    deadline = time.monotonic()+wait
    while time.monotonic() < deadline:
        if io['read'](runtime+'/'+REQUEST, 4096) is None:
            out('APPLIED by the monitor (see list and the event history)')
            return 0
        time.sleep(1)
    out('REQUESTED: the monitor applies it at its next pass (service stopped? use --offline)')
    return 0


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    raise SystemExit(cli(sys.argv[1:]))
