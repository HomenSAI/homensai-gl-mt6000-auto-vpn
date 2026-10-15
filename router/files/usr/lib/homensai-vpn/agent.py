#!/usr/bin/python3
"""OpenWrt monitor alpha. No route/firewall/VPN write commands exist here."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import fcntl
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import socket
import ssl
import struct
import subprocess
import sys
import time

VERSION = '0.3.0-alpha1'
RUNTIME = Path('/var/run/homensai-vpn')
PERSIST = Path('/etc/homensai-vpn')
INVENTORY = '/usr/lib/homensai-vpn/inventory.lua'
SAFE = re.compile(r'^[A-Za-z0-9_.:-]{1,96}$')
SO_MARK = getattr(socket, 'SO_MARK', 36)
SO_BINDTODEVICE = getattr(socket, 'SO_BINDTODEVICE', 25)
STOP = False


def command(args, timeout=5):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=timeout, check=True)
    if len(result.stdout) > 2 * 1024 * 1024:
        raise ValueError('oversize command response')
    return result.stdout


def inventory():
    data = json.loads(command(['/usr/bin/lua', INVENTORY]))
    data['profiles'] = [p for p in data.get('profiles', [])
                        if SAFE.fullmatch(p.get('id', '')) and SAFE.fullmatch(p.get('section', ''))]
    # Inventory is already allowlisted by Lua; this guard also bounds names/amounts.
    for p in data['profiles']:
        p['name'] = str(p.get('name', p['id']))[:64]
        if p.get('interface') and not SAFE.fullmatch(p['interface']):
            p['interface'] = None
    data['profiles'] = data['profiles'][:400]
    return data


def atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError('symlink storage refused')
    pending = path.with_name(path.name + '.pending')
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(str(pending), flags, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(pending), str(path))
    directory = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def read_json(path, default=None):
    if path.is_symlink():
        raise ValueError('symlink storage refused')
    try:
        if path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError('oversize state')
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Accounting:
    def __init__(self, data=None):
        self.months = data.get('months', {}) if data else {}
        self.previous = {}  # Never carry kernel counter baselines across reboot.
        self.gaps = int(data.get('gaps', 0)) if data else 0
        self.quality = data.get('quality', {}) if data else {}
        self.activity = data.get('activity', {}) if data else {}
        self.activity_previous = {}

    def track_activity(self, rows, now, max_gap=90):
        for item in rows:
            key = item['id']
            profile = self.activity.setdefault(key, {'days': {}, 'last_seen': now})
            profile.update(name=item.get('name', key), protocol=item.get('protocol', 'unknown'))
            code = item.get('code')
            state = ('idle' if not item.get('interface') else 'up' if not code else
                     'down' if code in ('VPN-001', 'VPN-003', 'DNS-001') else 'unknown')
            previous = self.activity_previous.get(key)
            beginning = previous[0] if previous else profile.get('last_seen', now)
            interval_state = previous[1] if previous and 0 < now-beginning <= max_gap else 'unknown'
            cursor = max(beginning, now-32*86400)
            while cursor < now:
                local = datetime.fromtimestamp(cursor)
                tomorrow = local.date()+timedelta(days=1)
                end = min(now, time.mktime((tomorrow.year,tomorrow.month,tomorrow.day,0,0,0,0,0,-1)))
                day = local.strftime('%Y-%m-%d')
                bucket = profile['days'].setdefault(day, {'up':0,'down':0,'idle':0,'unknown':0,'connections':0,'failures':0})
                bucket[interval_state] += end-cursor
                cursor = end
            day = datetime.fromtimestamp(now).strftime('%Y-%m-%d')
            bucket = profile['days'].setdefault(day, {'up':0,'down':0,'idle':0,'unknown':0,'connections':0,'failures':0})
            active = bool(item.get('interface'))
            if previous and 0 < now-previous[0] <= max_gap:
                if active and not previous[2]:
                    bucket['connections'] += 1
                if state == 'down' and previous[1] != 'down':
                    bucket['failures'] += 1
            self.activity_previous[key] = (now, state, active)
            profile['last_seen'] = now
            cutoff = datetime.fromtimestamp(now-32*86400).strftime('%Y-%m-%d')
            profile['days'] = {d:b for d,b in profile['days'].items() if d >= cutoff}
        self.activity = {k:v for k,v in self.activity.items() if v.get('last_seen',0) >= now-32*86400}
        if len(self.activity)>400:
            keep=sorted(self.activity,key=lambda k:self.activity[k]['last_seen'],reverse=True)[:400]
            self.activity={k:self.activity[k] for k in keep}

    def sample(self, device, ifindex, rx, tx, now, max_gap=90):
        if not SAFE.fullmatch(device) or min(rx, tx) < 0:
            raise ValueError('invalid interface counter')
        previous = self.previous.get(device)
        self.previous[device] = (ifindex, rx, tx, now)
        if not previous:
            return
        old_index, old_rx, old_tx, old_time = previous
        if old_index != ifindex or rx < old_rx or tx < old_tx or now <= old_time or now-old_time > max_gap:
            self.gaps += 1
            return
        cursor = old_time
        while cursor < now:
            local = datetime.fromtimestamp(cursor)
            year, month = local.year, local.month
            next_year, next_month = (year+1, 1) if month == 12 else (year, month+1)
            boundary = time.mktime((next_year, next_month, 1, 0, 0, 0, 0, 0, -1))
            end = min(now, boundary)
            weight = (end-cursor)/(now-old_time)
            key = '%04d-%02d' % (year, month)
            record = self.months.setdefault(key, {'rx': 0, 'tx': 0, 'seconds': 0, 'boundary_estimated': False})
            record['rx'] += (rx-old_rx)*weight
            record['tx'] += (tx-old_tx)*weight
            record['seconds'] += end-cursor
            if boundary < now:
                record['boundary_estimated'] = True
            cursor = end
        for key in sorted(self.months)[:-18]:
            del self.months[key]

    def observe(self, result):
        identifier, stamp = result['id'], result['time']
        self.quality = {key: value for key, value in self.quality.items() if (value.get('last') or {}).get('time', 0) >= stamp-7*86400}
        bucket = str(int(stamp//3600))
        profile = self.quality.setdefault(identifier, {'buckets': {}, 'last': None})
        profile['last'] = {k: result.get(k) for k in ('time','code','rtt_ms')}
        row = profile['buckets'].setdefault(bucket, {'n': 0, 'success': 0, 'rtt_sum': 0, 'unknown': 0})
        if result.get('code') in ('CHECK-001','SYSTEM-001','ROUTE-001','PROFILE-INACTIVE','CHECK-LIMIT'):
            row['unknown'] += 1
        else:
            row['n'] += 1
            if result.get('code') is None:
                row['success'] += 1
                row['rtt_sum'] += result.get('rtt_ms') or 0
        for key in list(profile['buckets']):
            if int(key)*3600 < stamp-7*86400:
                del profile['buckets'][key]

        if len(self.quality) > 400:
            keep = sorted(self.quality, key=lambda key: (self.quality[key].get('last') or {}).get('time', 0), reverse=True)[:400]
            self.quality = {key: self.quality[key] for key in keep}

    def export(self):
        return {'months': self.months, 'gaps': self.gaps, 'quality': self.quality, 'activity': self.activity}


def bound_socket(device, mark, udp=False):
    if not SAFE.fullmatch(device) or len(device) > 15 or not isinstance(mark, int) or not 0 < mark <= 0xFFFFFFFF:
        raise ValueError('invalid socket binding')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if udp else socket.SOCK_STREAM)
    try:
        sock.settimeout(3)
        sock.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, device.encode('ascii')+b'\0')
        sock.setsockopt(socket.SOL_SOCKET, SO_MARK, mark)
        return sock
    except BaseException:
        sock.close()
        raise


def dns_question():
    token = os.urandom(2)
    name = b'\x07example\x03com\0'
    question = name + struct.pack('!HH', 1, 1)
    return token, struct.pack('!2sHHHHH', token, 0x100, 1, 0, 0, 0) + question, question


def valid_dns(data, token):
    if len(data) < 12:
        return False
    received, flags, questions, answers, _, _ = struct.unpack('!2sHHHHH', data[:12])
    return received == token and bool(flags & 0x8000) and not flags & 0x020F and questions == 1 and answers > 0


def dns_probe(device, mark):
    token, packet, question = dns_question()
    with bound_socket(device, mark, udp=True) as sock:
        sock.connect(('9.9.9.9', 53))
        sock.send(packet)
        data = sock.recv(4096)
    return valid_dns(data, token) and data[12:12+len(question)] == question


def https_probe(device, mark, target):
    address, hostname, path, kind = target
    ipaddress.IPv4Address(address)
    started = time.monotonic()
    token = None
    if kind == 'dns-wire':
        token, packet, _ = dns_question()
        path += '?dns=' + base64.urlsafe_b64encode(packet).decode().rstrip('=')
    raw = bound_socket(device, mark)
    try:
        raw.connect((address, 443))
        with ssl.create_default_context().wrap_socket(raw, server_hostname=hostname) as sock:
            sock.sendall(('GET %s HTTP/1.1\r\nHost: %s\r\nAccept: application/dns-json, application/dns-message, text/plain\r\nConnection: close\r\n\r\n' % (path, hostname)).encode('ascii'))
            response = http.client.HTTPResponse(sock)
            response.begin()
            body = response.read(32769)
            if response.status != 200 or len(body) > 32768:
                return None
            if kind == 'trace':
                valid = b'\nip=' in b'\n'+body and b'\nhttp=' in b'\n'+body
            elif kind == 'dns-json':
                payload = json.loads(body)
                valid = payload.get('Status') == 0 and bool(payload.get('Answer'))
            else:
                valid = valid_dns(body, token)
            return round((time.monotonic()-started)*1000, 1) if valid else None
    finally:
        raw.close()


TARGETS = [('1.1.1.1', 'one.one.one.one', '/cdn-cgi/trace', 'trace'),
           ('8.8.8.8', 'dns.google', '/resolve?name=example.com&type=A', 'dns-json'),
           ('9.9.9.9', 'dns.quad9.net', '/dns-query', 'dns-wire')]


def route_binding(logical):
    status = json.loads(command(['ubus', 'call', 'network.interface.'+logical, 'status']))
    if not status.get('up'):
        return {'code': 'VPN-001'}
    device = status.get('l3_device', '')
    if not SAFE.fullmatch(device) or len(device) > 15:
        return {'code': 'ROUTE-001'}
    routes = json.loads(command(['ip', '-4', '-j', 'route', 'show', 'table', 'all']))
    tables = {str(r.get('table', 'main')) for r in routes if r.get('dev') == device and r.get('dst') == 'default'}
    rules = json.loads(command(['ip', '-4', '-j', 'rule', 'show']))
    candidates = []
    for rule in rules:
        if str(rule.get('table')) not in tables or not rule.get('fwmark'):
            continue
        mark = int(str(rule['fwmark']), 0)
        if mark > 0:
            candidates.append((mark, str(rule['table'])))
    candidates = list(set(candidates))
    if len(candidates) != 1:
        return {'code': 'CHECK-001', 'device': device}
    mark, table = candidates[0]
    for address, _, _, _ in TARGETS:
        answer = json.loads(command(['ip', '-4', '-j', 'route', 'get', address, 'mark', str(mark)]))
        if len(answer) != 1 or answer[0].get('dev') != device or str(answer[0].get('table', 'main')) != table:
            return {'code': 'ROUTE-001', 'device': device}
    return {'code': None, 'device': device, 'mark': mark, 'table': table}


def probe(profile):
    result = {'id': profile['id'], 'time': time.time(), 'code': 'CHECK-001',
              'scope': 'router-originated', 'lan_path_verified': False}
    if not profile.get('interface'):
        result['code'] = 'PROFILE-INACTIVE'
        return result
    try:
        binding = route_binding(profile['interface'])
        result.update(binding)
        if binding['code']:
            return result
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(https_probe, binding['device'], binding['mark'], t) for t in TARGETS]
            dns = pool.submit(dns_probe, binding['device'], binding['mark'])
            times = []
            for future in futures:
                try:
                    value = future.result()
                    if value is not None:
                        times.append(value)
                except (OSError, ValueError, http.client.HTTPException):
                    pass
            try:
                dns_ok = dns.result()
            except (OSError, ValueError):
                dns_ok = False
        result.update({'https_success': len(times), 'dns_ok': dns_ok,
                       'rtt_ms': round(sum(times)/len(times), 1) if times else None,
                       'code': 'VPN-003' if len(times) < 2 else 'DNS-001' if not dns_ok else None})
    except (OSError, ValueError, subprocess.SubprocessError):
        result['code'] = 'SYSTEM-001'
    return result


def sample_counters(profiles, accounting, now, max_gap):
    devices = set()
    for p in profiles:
        device = p.get('device')
        if not device or device in devices or not SAFE.fullmatch(device):
            continue
        devices.add(device)
        root = Path('/sys/class/net') / device
        try:
            accounting.sample(device, int((root/'ifindex').read_text()),
                              int((root/'statistics/rx_bytes').read_text()),
                              int((root/'statistics/tx_bytes').read_text()), now, max_gap)
        except (OSError, ValueError):
            accounting.gaps += 1


def checkpoint(accounting):
    payload = {'version': 1, 'saved': time.time(), 'accounting': accounting.export()}
    old = read_json(PERSIST/'checkpoint.json')
    if old and old.get('sha256') == checksum(old.get('data')):
        atomic_json(PERSIST/'checkpoint.backup.json', old)
    atomic_json(PERSIST/'checkpoint.json', {'data': payload, 'sha256': checksum(payload)})


def restore():
    seen_error = False
    for filename in ('checkpoint.json', 'checkpoint.backup.json'):
        try:
            raw = read_json(PERSIST/filename)
            if raw is None:
                continue
            if raw.get('sha256') != checksum(raw.get('data')):
                seen_error = True
                continue
            if raw['data'].get('version') != 1:
                seen_error = True
                continue
            acc = Accounting(raw['data']['accounting'])
            acc.gaps += 1
            return acc, 'STORAGE-RECOVERED' if seen_error else None
        except (OSError, ValueError, KeyError, TypeError):
            seen_error = True
    return Accounting(), 'STORAGE-001' if seen_error else None


def serve():
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = os.open(str(RUNTIME/'agent.lock'), os.O_CREAT|os.O_RDWR|getattr(os, 'O_NOFOLLOW', 0), 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        accounting, storage_error = restore()
    except (OSError, ValueError, KeyError, TypeError):
        accounting, storage_error = Accounting(), 'STORAGE-001'
    events, samples, last_save = [], [], time.monotonic()
    from telegram_report import deliver
    from failover_plan import plan
    telegram_saved = read_json(PERSIST/'telegram-state.json', {})
    while not STOP:
        started = time.monotonic()
        try:
            data = inventory()
            settings = data['settings']
            profiles = data['profiles']
            selected = {s['profile']: s for s in data.get('servers', []) if s.get('enabled')}
            observed = [p for p in profiles if p['id'] in selected] if selected else profiles
            bound = [p for p in observed if p.get('interface')][:settings['probe_limit']]
            with ThreadPoolExecutor(max_workers=2) as pool:
                measured = list(pool.map(probe, bound))
            mapped = {p['id']: p for p in measured}
            rows = []
            for p in observed:
                row = dict(p)
                row.update(mapped.get(p['id'], {'code': 'PROFILE-INACTIVE' if not p.get('interface') else 'CHECK-LIMIT'}))
                custom = selected.get(p['id'], {})
                row['name'] = custom.get('name') or p['name']
                row['channel'] = custom.get('channel') or 'default'
                rows.append(row)
            if time.time() >= 1704067200:
                sample_counters(measured, accounting, time.time(), settings['interval']*3)
                accounting.track_activity(rows, time.time(), settings['interval']*3)
            else:
                storage_error = 'CLOCK-001'
            for row in measured:
                accounting.observe(row)
                samples.append({k: row.get(k) for k in ('id','time','code','rtt_ms','https_success','dns_ok')})
            samples = [s for s in samples if (s.get('time') or 0) >= time.time()-86400*7][-10000:]
            current = {p['id']: p.get('code') for p in rows}
            previous = read_json(RUNTIME/'status.json', {}).get('profiles', [])
            old = {p['id']: p.get('code') for p in previous}
            for key, code in current.items():
                if key not in old or old[key] != code:
                    events.append({'time': time.time(), 'profile': key, 'code': code or 'OK'})
            if storage_error:
                events.append({'time': time.time(), 'code': storage_error})
            status = {'version': VERSION, 'mode': 'monitor', 'time': time.time(), 'profiles': rows,
                      'accounting': accounting.export(), 'samples': samples[-1000:], 'events': events[-300:],
                      'capabilities': {'native_apply': False, 'reason': 'GL.iNet worker/firewall transaction is not device-validated'},
                      'scope': 'IPv4 router-originated HTTPS/DNS, not LAN/IPv6 validation',
                      'storage_error': storage_error}
            status['telegram'], telegram_saved, delivered = deliver(status, telegram_saved, time.time())
            status['failover_plan']=plan(status,settings,time.time())
            if delivered:
                atomic_json(PERSIST/'telegram-state.json', telegram_saved)
            atomic_json(RUNTIME/'status.json', status)
            if time.monotonic()-last_save >= settings['checkpoint']:
                try:
                    checkpoint(accounting);storage_error = None;last_save = time.monotonic()
                except (OSError, ValueError):
                    storage_error = 'STORAGE-001'
            events = events[-1000:]
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            atomic_json(RUNTIME/'status.json', {'version': VERSION, 'mode': 'monitor', 'error': 'SYSTEM-001', 'time': time.time()})
            settings = {'interval': 30}
        # A scan request is bounded metadata, never an arbitrary command/path.
        while not STOP and time.monotonic()-started < settings['interval']:
            request = RUNTIME/'scan.request'
            if request.exists() and not request.is_symlink():
                request.unlink();break
            time.sleep(1)
    try:
        checkpoint(accounting)
    except (OSError, ValueError):
        pass


def rpc(method):
    if method == 'list':
        print(json.dumps({'status': {}, 'inventory': {}, 'scan': {}, 'events': {}}));return
    request = sys.stdin.buffer.read(65537)
    if len(request) > 65536:
        raise ValueError('oversize RPC input')
    arguments = json.loads(request) if request.strip() else {}
    if not isinstance(arguments, dict):
        raise ValueError('invalid RPC arguments')
    arguments.pop('ubus_rpc_session', None)  # rpcd injects this; never persist or echo it.
    if arguments:
        raise ValueError('unexpected RPC arguments')
    if method == 'inventory':
        print(json.dumps(inventory(), ensure_ascii=True))
    elif method == 'scan':
        atomic_json(RUNTIME/'scan.request', {'requested': time.time()})
        print('{"queued":true}')
    elif method in ('status', 'events'):
        status = read_json(RUNTIME/'status.json', {'mode': 'monitor', 'error': 'SERVICE-STOPPED'})
        print(json.dumps({'events': status.get('events', [])} if method == 'events' else status))
    else:
        raise ValueError('unknown RPC method')


def main():
    global STOP
    os.environ['TZ'] = 'CET-1CEST,M3.5.0,M10.5.0/3'
    if hasattr(time, 'tzset'):
        time.tzset()
    else:
        import ctypes
        ctypes.CDLL(None).tzset()
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['daemon','list','call','preflight'])
    parser.add_argument('method', nargs='?')
    args = parser.parse_args()
    if args.action == 'preflight':
        result = {'version': VERSION, 'python': sys.version.split()[0], 'profiles': len(inventory()['profiles']),
                  'mode': 'monitor', 'native_apply': False}
        print(json.dumps(result));return
    if args.action in ('list','call'):
        rpc('list' if args.action == 'list' else args.method);return
    def stop(*_):
        global STOP
        STOP = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    serve()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError):
        print('{"error":"SYSTEM-001"}')
        raise SystemExit(1)
