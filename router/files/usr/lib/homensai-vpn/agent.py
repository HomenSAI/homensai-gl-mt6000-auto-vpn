#!/usr/bin/python3
# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
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
import math
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
from threading import local
from probe_deadline import DeadlineSocket, HTTP_SECONDS, remaining

VERSION = '0.9.0-alpha44'
RUNTIME = Path('/var/run/homensai-vpn')
PERSIST = Path('/etc/homensai-vpn')
INVENTORY = '/usr/lib/homensai-vpn/inventory.lua'
SAFE = re.compile(r'^[A-Za-z0-9_.:-]{1,96}$')
SO_MARK = getattr(socket, 'SO_MARK', 36)
SO_BINDTODEVICE = getattr(socket, 'SO_BINDTODEVICE', 25)
TERMS_VERSION = '1'  # bump when DISCLAIMER.md changes; the UI gate and the controller both compare it
STOP = False
EXIT_SEEN = {}
EXIT_CONTEXT = local()


PACKAGE_CONTROL = Path('/usr/lib/opkg/info/homensai-auto-vpn.control')


def package_version(control=None):
    """Installed package version from opkg's control file; None when unknown (never guessed)."""
    try:
        control = control or PACKAGE_CONTROL
        if control.is_symlink() or control.stat().st_size > 8192:
            return None
        for line in control.read_text(encoding='utf-8', errors='replace').splitlines():
            if line.startswith('Version: '):
                value = line[9:].strip()
                return value if re.fullmatch(r'[0-9A-Za-z.+~_-]{1,48}', value) else None
    except OSError:
        return None
    return None


def remember_exit(device, body):
    """Cloudflare trace reports the address the destination sees; keep a global IPv4 only."""
    for line in body.decode('ascii', 'replace').splitlines():
        if line.startswith('ip='):
            try:
                address = ipaddress.IPv4Address(line[3:].strip())
            except ValueError:
                return
            if address.is_global:
                getattr(EXIT_CONTEXT,'sink',EXIT_SEEN)[device] = str(address)
            return


def command(args, timeout=5):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=timeout, check=True)
    if len(result.stdout) > 2 * 1024 * 1024:
        raise ValueError('oversize command response')
    return result.stdout


def inventory():
    data = json.loads(command(['/usr/bin/lua', INVENTORY]))
    # Lua cjson represents an empty table as {}, including empty array fields.
    for key in ('profiles','servers','native_candidates','wan_interfaces'):
        value=data.get(key,[])
        if value=={}:value=[]
        if not isinstance(value,list):raise ValueError('invalid inventory array')
        data[key]=value
    if any(not isinstance(p,dict) for p in data['profiles']):raise ValueError('invalid profile row')
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
        def number(raw):
            value = float(raw) if any(c in raw for c in '.eE') else int(raw)
            if not math.isfinite(value):
                raise ValueError('nonfinite state number')
            return value
        def pairs(items):
            row = {}
            for key, value in items:
                if key in row:
                    raise ValueError('duplicate state field')
                row[key] = value
            return row
        def constant(raw):
            raise ValueError('nonfinite state number')
        value = json.loads(path.read_text(encoding='utf-8'), parse_int=number,
                           parse_float=number, parse_constant=constant, object_pairs_hook=pairs)
        # Existing schemas use only a few levels. Bound recursive consumers too,
        # including checksums, after decoding without recursively walking here.
        pending = [(iter((value,)), 0)]
        while pending:
            items, depth = pending[-1]
            try:row = next(items)
            except StopIteration:
                pending.pop();continue
            if depth > 64:
                raise ValueError('state nesting limit')
            if isinstance(row, (dict, list)):
                pending.append((iter(row.values() if isinstance(row, dict) else row), depth + 1))
        return value
    except FileNotFoundError:
        return default
    except (RecursionError, OverflowError):
        raise ValueError('invalid state JSON') from None


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Accounting:

    def __init__(self, data=None, _nested=False):
        self.months = data.get('months', {}) if data else {}
        self.days = data.get('days', {}) if data else {}
        self.retention = data.get('retention', {}) if data else {}
        self.wan=Accounting(data['wan'],_nested=True) if not _nested and data and isinstance(data.get('wan'),dict) else None
        self.previous = {}  # Never carry kernel counter baselines across reboot.
        self.gaps = int(data.get('gaps', 0)) if data else 0
        self.quality = data.get('quality', {}) if data else {}
        self.activity = data.get('activity', {}) if data else {}
        self.activity_previous = {}
        from reliability import Reliability
        self.reliability=Reliability(data.get('reliability') if data else None)

    def track_activity(self, rows, now, max_gap=90):
        for item in rows:
            key = item['id']
            profile = self.activity.setdefault(key, {'days': {}, 'last_seen': now})
            profile.update(name=item.get('name', key), protocol=item.get('protocol', 'unknown'))
            code = item.get('code')
            state = ('idle' if not item.get('interface') else 'up' if not code else
                     'down' if code in ('VPN-001', 'VPN-003', 'DNS-001') else 'unknown')
            previous = self.activity_previous.get(key)
            if previous and now<=previous[0]:
                if now<previous[0]:self.gaps+=1
                continue  # Never move a baseline backwards or double-count time.
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
        if now<=old_time:
            if now==old_time and rx==old_rx and tx==old_tx:
                self.previous[device]=previous;return
            self.previous.pop(device,None);self.gaps+=1;self.note_gap(old_time,now);return
        if old_index != ifindex or rx < old_rx or tx < old_tx or now <= old_time or now-old_time > max_gap:
            self.gaps += 1
            self.note_gap(old_time,now)
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
        cursor=old_time
        while cursor<now:
            local=datetime.fromtimestamp(cursor);tomorrow=local.date()+timedelta(days=1)
            boundary=time.mktime((tomorrow.year,tomorrow.month,tomorrow.day,0,0,0,0,0,-1))
            end=min(now,boundary);weight=(end-cursor)/(now-old_time);key=local.strftime('%Y-%m-%d')
            record=self.days.setdefault(key,{'rx':0,'tx':0,'seconds':0,'boundary_estimated':False,'gaps':0,'observed':False})
            record.update(observed=True,first_sample=min(record.get('first_sample',cursor),cursor),last_sample=max(record.get('last_sample',end),end))
            record['rx']+=(rx-old_rx)*weight;record['tx']+=(tx-old_tx)*weight;record['seconds']+=end-cursor
            if boundary<now:record['boundary_estimated']=True
            cursor=end
        for key in sorted(self.days)[:-400]:del self.days[key]
        current_month=datetime.fromtimestamp(now).strftime('%Y-%m')
        others=[key for key in sorted(self.months) if key!=current_month]
        keep=17 if current_month in self.months else 18
        for key in others[:-keep]:del self.months[key]

    def note_gap(self,start,end):
        # No traffic is invented for missing intervals; gap-only days are unobserved.
        cursor=min(start,end);finish=max(start,end)
        cursor=max(cursor,finish-400*86400)
        while True:
            local=datetime.fromtimestamp(cursor);key=local.strftime('%Y-%m-%d')
            row=self.days.setdefault(key,{'rx':0,'tx':0,'seconds':0,'boundary_estimated':False,'gaps':0,'observed':False})
            row['gaps']=row.get('gaps',0)+1
            tomorrow=local.date()+timedelta(days=1)
            boundary=time.mktime((tomorrow.year,tomorrow.month,tomorrow.day,0,0,0,0,0,-1))
            if boundary>=finish:break
            cursor=boundary
        for key in sorted(self.days)[:-400]:del self.days[key]

    def compact(self,limit=3*1024*1024):
        while len(json.dumps(self.export(),ensure_ascii=True).encode())>limit:
            buckets=sorted((int(key),profile,key) for profile,value in self.quality.items() for key in value.get('buckets',{}))
            if buckets:
                take=max(1,len(buckets)//2)
                for _,profile,key in buckets[:take]:del self.quality[profile]['buckets'][key]
                self.retention['quality_buckets_dropped']=self.retention.get('quality_buckets_dropped',0)+take
                continue
            days=sorted((key,profile) for profile,value in self.activity.items() for key in value.get('days',{}))
            if not days:raise ValueError('accounting retention budget exceeded')
            take=max(1,len(days)//4)
            for key,profile in days[:take]:del self.activity[profile]['days'][key]
            self.retention['activity_days_dropped']=self.retention.get('activity_days_dropped',0)+take

    def public_export(self):
        self.compact();data=dict(self.export())
        data['reliability']=self.reliability.public()
        if len(json.dumps(data,ensure_ascii=True).encode())<=500*1024:return data
        quality={}
        for identifier,value in self.quality.items():
            totals={'n':0,'success':0,'rtt_sum':0,'unknown':0}
            for bucket in value.get('buckets',{}).values():
                for key in totals:totals[key]+=bucket.get(key,0)
            quality[identifier]={'last':value.get('last'),'buckets':{'summary':totals}}
        data['quality']=quality;data['rpc_aggregated']=True
        if len(json.dumps(data,ensure_ascii=True).encode())<=500*1024:return data
        today=datetime.now().date();week=(today-timedelta(days=6)).isoformat();month=today.strftime('%Y-%m')
        activity={}
        for identifier,value in self.activity.items():
            periods={}
            for period in ('day','week','month'):
                total={key:0 for key in ('up','down','idle','unknown','connections','failures')}
                for day,bucket in value.get('days',{}).items():
                    included=day==today.isoformat() if period=='day' else week<=day<=today.isoformat() if period=='week' else day[:7]==month and day<=today.isoformat()
                    if included:
                        for key in total:total[key]+=bucket.get(key,0)
                periods[period]=total
            activity[identifier]={'name':value.get('name',identifier),'protocol':value.get('protocol','unknown'),'days':{},'periods':periods}
        data['activity']=activity;return data

    def observe(self, result, max_gap=90):
        self.reliability.observe(result,max_gap=max_gap)
        identifier, stamp = result['id'], result['time']
        self.quality = {key: value for key, value in self.quality.items() if (value.get('last') or {}).get('time', 0) >= stamp-7*86400}
        bucket = str(int(stamp//3600))
        profile = self.quality.setdefault(identifier, {'buckets': {}, 'last': None})
        profile['last'] = {k: result.get(k) for k in ('time','code','rtt_ms')}
        row = profile['buckets'].setdefault(bucket, {'n': 0, 'success': 0, 'rtt_sum': 0, 'unknown': 0})
        if result.get('code') in ('CHECK-001','SYSTEM-001','ROUTE-001','PROFILE-INACTIVE','CHECK-LIMIT',
                                  'VENDOR-IDENTITY-CHANGED','VENDOR-IDENTITY-UNKNOWN'):
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
        return {'months':self.months,'days':self.days,'gaps':self.gaps,'quality':self.quality,'activity':self.activity,'retention':self.retention,'reliability':self.reliability.export(),'wan':self.wan.export() if self.wan else None}


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
    end = started + HTTP_SECONDS
    token = None
    if kind == 'dns-wire':
        token, packet, _ = dns_question()
        path += '?dns=' + base64.urlsafe_b64encode(packet).decode().rstrip('=')
    raw = bound_socket(device, mark)
    try:
        raw.settimeout(remaining(end))
        raw.connect((address, 443))
        raw.settimeout(remaining(end))
        with ssl.create_default_context().wrap_socket(raw, server_hostname=hostname) as sock:
            sock.settimeout(remaining(end))
            sock.sendall(('GET %s HTTP/1.1\r\nHost: %s\r\nAccept: application/dns-json, application/dns-message, text/plain\r\nConnection: close\r\n\r\n' % (path, hostname)).encode('ascii'))
            response = http.client.HTTPResponse(DeadlineSocket(sock,end))
            response.begin()
            body = response.read(32769)
            remaining(end)
            if response.status != 200 or len(body) > 32768:
                return None
            if kind == 'trace':
                valid = b'\nip=' in b'\n'+body and b'\nhttp=' in b'\n'+body
                if valid:remember_exit(device, body)
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
    ifindex=int((Path('/sys/class/net')/device/'ifindex').read_text())
    if ifindex<=0:return {'code':'CHECK-001','device':device}
    return {'code': None, 'device': device, 'mark': mark, 'table': table,'ifindex':ifindex}


def https_for_probe(device,mark,target,sink):
    # The trace belongs to this one probe, even when two logical tunnels share
    # a device or a late worker finishes after another measurement started.
    EXIT_CONTEXT.sink=sink
    try:return https_probe(device,mark,target)
    finally:del EXIT_CONTEXT.sink


def probe(profile):
    result = {'id': profile['id'], 'time': time.time(), 'code': 'CHECK-001',
              'scope': 'router-originated', 'lan_path_verified': False}
    administrative_state=profile.get('administrative_state','unknown')
    if administrative_state in ('enabled','disabled','unknown'):result['administrative_state']=administrative_state
    if not profile.get('interface') or administrative_state=='disabled':
        result['code'] = 'PROFILE-INACTIVE'
        return result
    try:
        binding = route_binding(profile['interface'])
        result.update(binding)
        if binding['code']:
            return result
        exit_seen={}
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(https_for_probe, binding['device'], binding['mark'], t,exit_seen) for t in TARGETS]
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
        # A successful socket quorum cannot survive a kernel route/device epoch
        # change during the measurement. Configuration is checked by the scan too.
        after=route_binding(profile['interface'])
        if after.get('code') or any(after.get(key)!=binding.get(key) for key in ('device','mark','table','ifindex')):
            for key in ('https_success','dns_ok','rtt_ms','exit_ip'):result.pop(key,None)
            result['code']='VENDOR-IDENTITY-CHANGED'
            return result
        exit_ip = exit_seen.pop(binding['device'], None)
        if exit_ip and not result['code']:
            result['exit_ip'] = exit_ip  # shown only in the authenticated UI; never in reports or history
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


def sample_wan_counters(data,accounting,now,max_gap=90):
    # WAN firewall-zone interfaces are explicit sources, not guessed default routes.
    devices=[];seen=set();links=[]
    for logical in data.get('wan_interfaces',[]):
        if not isinstance(logical,str) or not SAFE.fullmatch(logical):continue
        try:
            interface=json.loads(command(['ubus','call','network.interface.'+logical,'status']))
            links.append(interface.get('up') if type(interface.get('up')) is bool else None)
            if not interface.get('up') or interface.get('proto') in ('ovpnclient','wgclient','openvpn','wireguard'):continue
            device=interface.get('l3_device','')
            if not SAFE.fullmatch(device) or len(device)>15 or device in seen:continue
            seen.add(device);root=Path('/sys/class/net')/device
            if accounting.wan is None:accounting.wan=Accounting()
            accounting.wan.sample(device,int((root/'ifindex').read_text()),int((root/'statistics/rx_bytes').read_text()),int((root/'statistics/tx_bytes').read_text()),now,max_gap)
            devices.append({'device':device})
        except (OSError,ValueError,subprocess.SubprocessError):
            links.append(None)
            if accounting.wan:accounting.wan.gaps+=1;accounting.wan.note_gap(now,now)
    data['uplink_observation']={'time':now,'state':'DOWN' if links and all(v is False for v in links) else 'LINK-UP' if any(v is True for v in links) else 'UNKNOWN','scope':'configured WAN-zone interface link state; not Internet proof'}
    return devices


def checkpoint(accounting):
    accounting.compact()
    payload = {'version': 1, 'saved': time.time(), 'accounting': accounting.export()}
    try:old = read_json(PERSIST/'checkpoint.json')
    except (ValueError,TypeError):old=None
    if old:
        from checkpoint_schema import validate
        try:
            validate(old)
            if old.get('sha256') == checksum(old.get('data')):atomic_json(PERSIST/'checkpoint.backup.json', old)
        except (ValueError,TypeError,KeyError,OverflowError):pass
    atomic_json(PERSIST/'checkpoint.json', {'data': payload, 'sha256': checksum(payload)})


def restore():
    seen_error = False
    for filename in ('checkpoint.json', 'checkpoint.backup.json'):
        try:
            raw = read_json(PERSIST/filename)
            if raw is None:
                continue
            from checkpoint_schema import validate
            validate(raw)
            if raw.get('sha256') != checksum(raw.get('data')):
                seen_error = True
                continue
            if raw['data'].get('version') != 1:
                seen_error = True
                continue
            acc = Accounting(raw['data']['accounting'])
            acc.gaps += 1
            acc.note_gap(raw['data'].get('saved',time.time()),time.time())
            if acc.wan:
                acc.wan.gaps+=1;acc.wan.note_gap(raw['data'].get('saved',time.time()),time.time())
            return acc, 'STORAGE-RECOVERED' if seen_error else None
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            seen_error = True
    return Accounting(), 'STORAGE-001' if seen_error else None


def monitoring_profiles(data):
    selected={s['profile']:s for s in data.get('servers',[]) if s.get('enabled')}
    profiles=data.get('profiles',[])
    from vendor_observation import current_bindings
    settings=data.get('settings',{})
    anchors={settings.get('plan_'+side+'_tunnel') for side in ('source','target')
             if isinstance(settings.get('plan_'+side+'_tunnel'),str)}
    disabled={s['profile'] for s in data.get('servers',[]) if s.get('enabled') is False}
    follow={p['id'] for tunnel,p in current_bindings(profiles).items() if tunnel in anchors and p['id'] not in disabled}
    observed=[p for p in profiles if p['id'] in selected or p['id'] in follow] if data.get('servers') else profiles
    return observed,selected


def monitor_poll_interval(settings, now=None):
    """Accelerate only a correlated bounded startup; never overlap probe rounds."""
    normal = settings['interval']
    now = time.time() if now is None else now
    try:
        import pair_auto
        state, request = pair_auto.read_state(), pair_auto.intent()
        if (request.get('mode') != 'on' or state.get('id') != request.get('id')
                or state.get('revision') != request.get('revision')):
            return normal
        began = state.get('started')
        if type(began) not in (int, float) or not math.isfinite(began) or not 0 <= now-began <= 180:
            return normal
        preparing = state.get('phase') == 'STARTING'
        if state.get('phase') == 'RUNNING':
            native = read_json(RUNTIME/'native-status.json', {})
            observed = native.get('time')
            preparing = (native.get('state') == 'ARMED' and native.get('mode') == 'continuous-pair'
                         and native.get('reason') in ('PAIR-CONNECTING', 'PAIR-WAITING-PROBES')
                         and type(observed) in (int, float) and math.isfinite(observed)
                         and -5 <= now-observed <= 30)
        return min(normal, 2) if preparing else normal
    except (OSError, ValueError, TypeError, KeyError):
        return normal


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
    from telegram_state import load as load_telegram_state, save as save_telegram_state
    telegram_saved,telegram_notice=load_telegram_state(PERSIST)
    speed_previous=None
    from vendor_observation import VendorObserver
    vendor_observer=VendorObserver()
    from scan_control import begin as begin_scan, finish as finish_scan
    while not STOP:
        scan_id=begin_scan(RUNTIME,read_json,atomic_json)
        started = time.monotonic()
        try:
            data = inventory()
            settings = data['settings']
            profiles = data['profiles']
            selected = {s['profile']: s for s in data.get('servers', []) if s.get('enabled')}
            observed = monitoring_profiles(data)[0]
            bound = [p for p in observed if p.get('interface')][:settings['probe_limit']]
            with ThreadPoolExecutor(max_workers=2) as pool:
                measured = list(pool.map(probe, bound))
            # Read metadata again after the network observations. Never attach a
            # former configured profile's success to its replacement on a tunnel.
            after_inventory=inventory()
            vendor_observation,measured=vendor_observer.observe(data,after_inventory,measured,time.time())
            mapped = {p['id']: p for p in measured}
            rows = []
            for p in observed:
                row = dict(p)
                row.update(mapped.get(p['id'], {'code': 'PROFILE-INACTIVE' if not p.get('interface') else 'CHECK-LIMIT'}))
                custom = selected.get(p['id'], {})
                row['router_name'] = p['name']  # the provider/router profile name; the UI derives the country from it
                row['name'] = custom.get('name') or p['name']
                row['channel'] = custom.get('channel') or 'default'
                row['priority'] = custom.get('priority',100)
                rows.append(row)
            wan_devices=[]
            if time.time() >= 1704067200:
                wan_devices=sample_wan_counters(data,accounting,time.time(),settings['interval']*3)
                sample_counters(measured, accounting, time.time(), settings['interval']*3)
                accounting.track_activity(rows, time.time(), settings['interval']*3)
            else:
                storage_error = 'CLOCK-001'
            for row in measured:
                accounting.observe(row,max_gap=settings['interval']*3)
                samples.append({k: row.get(k) for k in ('id','time','code','rtt_ms','https_success','dns_ok',
                    'interface','vendor_tunnel_id','vendor_generation')})
            samples = [s for s in samples if (s.get('time') or 0) >= time.time()-86400*7][-10000:]
            try:
                from speed_test import observe_traffic, automatic_new, active_job, cancel as cancel_speed, SpeedError
                observe_traffic(wan_devices or measured,scope='wan' if wan_devices else 'vpn')
                if active_job() and any(p.get('code') in ('VPN-001','VPN-003','DNS-001') for p in measured):cancel_speed()
                speed_previous=automatic_new(rows,speed_previous)
            except Exception:events.append({'time':time.time(),'code':'SPEED-MONITOR-UNAVAILABLE'})
            current = {p['id']: p.get('code') for p in rows}
            previous = read_json(RUNTIME/'status.json', {}).get('profiles', [])
            old = {p['id']: p.get('code') for p in previous}
            for key, code in current.items():
                if key not in old or old[key] != code:
                    events.append({'time': time.time(), 'profile': key, 'code': code or 'OK'})
            if storage_error:
                events.append({'time': time.time(), 'code': storage_error})
            status = {'version': VERSION, 'mode': 'monitor', 'time': time.time(), 'profiles': rows,
                      'accounting': accounting.public_export(), 'samples': samples[-1000:], 'events': events[-300:],
                      'capabilities': {'native_apply': False, 'reason': 'GL.iNet worker/firewall transaction is not device-validated'},
                      'scope': 'IPv4 router-originated HTTPS/DNS, not LAN/IPv6 validation',
                      'storage_error': storage_error}
            status['uplink_observation']=data.get('uplink_observation',{'state':'UNKNOWN'})
            status['vendor_observation']=vendor_observation
            status['package']=package_version()
            from failure_diagnosis import explain
            status['decision_explanation']=explain(status,settings,time.time())
            status['failover_plan']=plan(status,settings,time.time())
            from candidate_hierarchy import rank_candidates
            status['candidate_recommendations']=rank_candidates(rows,data.get('servers',[]),samples,status['failover_plan'].get('source',settings.get('plan_source','')),time.time(),max_age=settings.get('interval',30)*3,observation=vendor_observation,settings=settings)
            status['native_failover']=read_json(RUNTIME/'native-status.json', {'state':'SERVICE-STOPPED'})
            native=status['native_failover']
            from reliability import active_controller
            from pair_auto import read_state as pair_state, intent as pair_intent
            try:active=active_controller(native,pair_state(),pair_intent(),time.time())
            except (OSError,ValueError,TypeError):active=False
            accounting.reliability.controller(active,time.time(),max_gap=settings['interval']*3)
            from route_history import observed_route
            if accounting.reliability.routes.observe(observed_route(status,time.time()),time.time(),max_gap=settings['interval']*3):accounting.reliability.critical=True
            status['accounting']['reliability']=accounting.reliability.public()
            from native_history import read_public
            status['native_history']=read_public(PERSIST)
            from auto_control import public_status
            status['auto_control']=public_status()
            from system_readiness import snapshot as readiness_snapshot
            status['system_readiness']=readiness_snapshot()
            try:
                from speed_test import public_status as speed_status
                status['speed_tests']=speed_status()
            except (OSError,ValueError,KeyError):status['speed_tests']={'code':'SPEED-STATUS-UNAVAILABLE','results':[]}
            before_telegram=telegram_saved
            if telegram_notice=='TELEGRAM-STATE-CORRUPT':
                status['telegram']={'enabled':bool(settings.get('telegram_enabled')),'code':telegram_notice}
            else:
                try:
                    status['telegram'],telegram_saved,delivered=deliver(dict(status,accounting=accounting.export()),telegram_saved,time.time())
                    if telegram_notice:status['telegram']['storage_notice']=telegram_notice
                    if telegram_saved!=before_telegram:
                        try:save_telegram_state(telegram_saved,PERSIST);telegram_notice=None
                        except (OSError,ValueError):status['telegram']['storage_error']='TELEGRAM-STATE-WRITE-FAILED'
                except Exception:
                    status['telegram']={'enabled':bool(settings.get('telegram_enabled')),'code':'TELEGRAM-REPORT-UNAVAILABLE'}
            status['measurement_request_id']=scan_id
            atomic_json(RUNTIME/'status.json', status)
            finish_scan(RUNTIME,read_json,atomic_json,scan_id,snapshot=status)
            if accounting.reliability.critical or time.monotonic()-last_save >= settings['checkpoint']:
                try:
                    checkpoint(accounting);storage_error = None;last_save = time.monotonic();accounting.reliability.critical=False
                except (OSError, ValueError):
                    storage_error = 'STORAGE-001'
            events = events[-1000:]
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            atomic_json(RUNTIME/'status.json', {'version': VERSION, 'mode': 'monitor', 'error': 'SYSTEM-001', 'time': time.time()})
            finish_scan(RUNTIME,read_json,atomic_json,scan_id,'SCAN-MEASUREMENT-FAILED')
            settings = {'interval': 30}
        # A scan request is bounded metadata, never an arbitrary command/path.
        while not STOP and time.monotonic()-started < monitor_poll_interval(settings):
            request = RUNTIME/'scan.request'
            if request.exists() and not request.is_symlink():
                break
            time.sleep(1)
    try:
        from speed_test import cancel as cancel_speed
        cancel_speed()
    except (OSError,ValueError):pass
    try:
        checkpoint(accounting)
    except (OSError, ValueError):
        pass


def trim_status_reply(status,limit=900000):
    if len(json.dumps(status,ensure_ascii=True).encode())<=limit:return status
    for row in status.get('profiles',[]):
        for key in ('section','group_id','profile_id','device','mark','table','scope','lan_path_verified'):row.pop(key,None)
    collections=[(status,'samples'),(status,'events'),(status.get('native_history',{}),'events'),(status.get('speed_tests',{}),'results')]
    while len(json.dumps(status,ensure_ascii=True).encode())>limit:
        changed=False
        for parent,key in collections:
            rows=parent.get(key,[])
            if len(rows)>2:parent[key]=rows[-max(2,len(rows)//2):];changed=True
        if not changed:break
    status['rpc_history_reduced']=True
    return status


def rpc(method):
    if method == 'list':
        print(json.dumps({'status': {}, 'auto_live': {}, 'statistics': {'kind':'','after':0,'until':0}, 'pair_manual':{'direction':'','control_revision':''}, 'inventory': {}, 'scan': {}, 'events': {},
                          'native_confirm': {'tx':'','exit_ipv4':'','dns_ok':False,'https_ok':False,'trial':''},
                          'native_trial_start': {'control_revision':'','trial':''},
                          'fault_start':{'profile':'','scope':'','duration':0},'fault_cancel':{},'priority_preview':{'ordered':[]},'priority_apply':{'ordered':[],'revision':''},
                          'setup_monitor':{'interval':0,'checkpoint':0,'probe_limit':0,'planning_enabled':False},
                          'setup_onboarding':{'system':{},'monitor':{},'recovery':{},'speed':{},'telegram':{},'appearance':{}},
                          'setup_recovery':{'failures':0,'successes':0,'cooldown':0,'min_dwell':0,'return_policy':'','primary_successes':0,'primary_stable':0},
                          'monitor_control': {'enabled':False}, 'manual_switch': {'direction':'','control_revision':''}, 'native_stop': {}, 'native_start': {'control_revision':''}, 'native_return': {}, 'telegram_forget': {}, 'terms_accept': {'version':''}, 'telegram_test': {}, 'telegram_retry': {}, 'setup_check': {}, 'speed_cancel': {},
                          'speed_start':{'profiles':[],'budget_mib':0,'duration':0,'streams':0},
                          'setup_speed':{'enabled':False,'auto_new':False,'budget_mib':0,'duration':0,'streams':0,'daily_mib':0,'busy_mbps':0},
                          'setup_system':{'source':'','target':'','interval':0,'duration':0,'session_loss':False,'servers':[]},
                          'setup_telegram':{'token':'','chat':'','enabled':False,'interval':0,'schedule':'','hour':0,'weekly':False,'monthly':False,'items':''}}));return
    request = sys.stdin.buffer.read(65537)
    from rpc_input import decode_request
    arguments=decode_request(request)
    if method=='statistics':
        from statistics_export import page
        print(json.dumps(page(PERSIST,arguments)));return
    if method=='pair_manual':
        from pair_manual import request
        print(json.dumps(request(arguments['direction'],arguments['control_revision']) if set(arguments)=={'direction','control_revision'} else {'accepted':False,'blockers':['PAIR-MANUAL-FIELDS']}));return
    if method=='native_confirm':
        if set(arguments)!= {'tx','exit_ipv4','dns_ok','https_ok','trial'}:
            raise ValueError('RPC-CONFIRM-FIELDS')
        # The trial number is private (never in status, inventory or history): only the helper that started the trial knows it.
        import hmac
        configured=json.loads(command(['/usr/bin/lua','/usr/lib/homensai-vpn/native_policy.lua'])).get('settings',{}).get('native_trial')
        if (not isinstance(arguments['trial'],str) or not isinstance(configured,str) or not re.fullmatch(r'[a-f0-9]{32}',configured)
                or not hmac.compare_digest(arguments['trial'].encode('ascii','replace'),configured.encode('ascii','replace'))):
            raise ValueError('RPC-CONFIRM-TRIAL')
        if not isinstance(arguments['tx'],str) or not re.fullmatch(r'[a-f0-9]{32}',arguments['tx']):
            raise ValueError('RPC-CONFIRM-TRANSACTION')
        # Only a dotted-quad string: IPv4Address(int) would accept 134744072 as 8.8.8.8.
        if not isinstance(arguments['exit_ipv4'],str) or not re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]{1,3}){3}',arguments['exit_ipv4']):
            raise ValueError('RPC-CONFIRM-ADDRESS')
        address=ipaddress.IPv4Address(arguments['exit_ipv4'])
        if not address.is_global or arguments['dns_ok'] is not True or arguments['https_ok'] is not True:
            raise ValueError('RPC-CONFIRM-UNVERIFIED')
        pending=read_json(RUNTIME/'native-status.json',{})
        if pending.get('state')!='WAIT-CLIENT' or pending.get('tx')!=arguments['tx'] or pending.get('expected_exit')!=str(address) or time.time()>pending.get('deadline',0):
            raise ValueError('RPC-CONFIRM-NO-PENDING')
        envelope=read_json(PERSIST/'native-transaction.json',{})
        transaction=envelope.get('data')
        if (envelope.get('schema')!=1 or not isinstance(transaction,dict)
                or envelope.get('sha256')!=checksum(transaction)
                or transaction.get('phase')!='WAIT-CLIENT' or transaction.get('tx')!=arguments['tx']
                or transaction.get('expected_exit')!=str(address) or time.time()>transaction.get('deadline',0)):
            raise ValueError('RPC-CONFIRM-NO-PENDING')
        if transaction.get('monotonic_deadline') is not None and time.monotonic()>=transaction['monotonic_deadline']:
            raise ValueError('RPC-CONFIRM-EXPIRED')
        if transaction.get('proof_scope','external-lan')!='external-lan':raise ValueError('RPC-CONFIRM-UNVERIFIED')
        atomic_json(RUNTIME/'native-confirm.json',dict(arguments,time=time.time()))
        print('{"accepted":true}');return
    if method in ('fault_start','fault_cancel'):
        from fault_control import start,cancel,FaultError
        try:result=start(arguments) if method=='fault_start' else cancel() if not arguments else {'queued':False,'code':'FAULT-FIELDS'}
        except FaultError as error:result={'accepted':False,'code':str(error)}
        print(json.dumps(result));return
    if method in ('priority_preview','priority_apply'):
        from priority_config import preview,apply
        print(json.dumps(preview(arguments) if method=='priority_preview' else apply(arguments)));return
    if method=='monitor_control':
        from monitor_control import change
        print(json.dumps(change(arguments)));return
    if method=='terms_accept':
        from setup_config import save
        try:result=save(arguments,'terms')
        except ValueError as error:
            result={'saved':False,'code':str(error) if re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',str(error)) else 'SETUP-INVALID'}
        print(json.dumps(result));return
    if method=='telegram_forget':
        from setup_config import save
        try:result=save(arguments,'forget')
        except ValueError as error:
            result={'saved':False,'code':str(error) if re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',str(error)) else 'SETUP-INVALID'}
        print(json.dumps(result));return
    if method in ('setup_system','setup_telegram','setup_speed','setup_recovery','setup_monitor','setup_onboarding'):
        from setup_config import save
        try:result=save(arguments,{'setup_system':'system','setup_telegram':'telegram','setup_speed':'speed','setup_recovery':'recovery','setup_monitor':'monitor','setup_onboarding':'onboarding'}[method])
        except ValueError as error:
            code=str(error) if re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',str(error)) else 'SETUP-INVALID'
            result={'saved':False,'code':code}
        print(json.dumps(result));return
    if method=='speed_start':
        from speed_test import start, SpeedError
        try:result=start(arguments)
        except SpeedError as error:result={'accepted':False,'code':error.code}
        print(json.dumps(result));return
    if method=='manual_switch':
        from manual_control import request,refusal
        result=request(arguments['direction'],arguments['control_revision']) if set(arguments)=={'direction','control_revision'} else refusal('MANUAL-FIELDS')
        print(json.dumps(result));return
    if arguments and method not in('native_start','native_trial_start'):
        raise ValueError('RPC-UNEXPECTED-ARGS')
    if method=='telegram_retry':
        from telegram_report import retry_unknown
        print(json.dumps(retry_unknown()));return
    elif method=='speed_cancel':
        from speed_test import cancel
        print(json.dumps(cancel()));return
    elif method == 'setup_check':
        from setup_config import self_test
        print(json.dumps(self_test()));return
    elif method == 'telegram_test':
        from telegram_report import send_test
        print(json.dumps(send_test()));return
    elif method == 'inventory':
        print(json.dumps(inventory(), ensure_ascii=True))
    elif method == 'scan':
        from scan_control import enqueue
        print(json.dumps(enqueue(RUNTIME,read_json,atomic_json)))
    elif method in ('native_start','native_trial_start','native_stop','native_return'):
        from auto_control import start, stop, return_request
        if method=='native_stop':
            # A failure-simulation test is cleaned up even when the stop latch itself cannot be written.
            try:result=stop(runtime=RUNTIME,persist=PERSIST)
            except (OSError,ValueError,subprocess.SubprocessError):result={'queued':False,'code':'STOP-UNCONFIRMED'}
        elif method=='native_start':
            result=start(arguments['control_revision']) if set(arguments)=={'control_revision'} else {'accepted':False,'blockers':['CONTROL-REVISION-STALE']}
        elif method=='native_trial_start':
            valid=(set(arguments)=={'control_revision','trial'}and isinstance(arguments['trial'],str)and re.fullmatch('[a-f0-9]{32}',arguments['trial']))
            result=start(arguments['control_revision'],trial_nonce=arguments['trial']) if valid else {'accepted':False,'blockers':['LAN-TRIAL-REQUIRED']}
        else:result=return_request()
        if method=='native_stop' and (RUNTIME/'fault-intent.json').exists():
            from fault_control import cancel,FaultError
            try:result['fault_cleanup']=cancel().get('cleaned',False)
            except (FaultError,OSError,ValueError,subprocess.SubprocessError):result['fault_cleanup']=False
        print(json.dumps(result));return
    elif method=='auto_live':
        from auto_live import snapshot
        print(json.dumps(snapshot()))
    elif method in ('status', 'events'):
        status = read_json(RUNTIME/'status.json', {'version':VERSION,'mode': 'monitor', 'error': 'SERVICE-STOPPED'})
        if method == 'status':
            from scan_control import public as scan_public
            status['scan']=scan_public(RUNTIME,read_json)
            from native_history import read_public
            status['native_failover']=read_json(RUNTIME/'native-status.json', {'state':'SERVICE-STOPPED'})
            status['native_history']=read_public(PERSIST)
            from auto_control import public_status
            status['auto_control']=public_status()
            from manual_control import public_status as manual_status, control_status
            from channel_path import public_status as path_status
            from pair_manual import controls as pair_controls,public as pair_status
            pair_control=pair_controls()
            if pair_control.get('available'):
                status['manual_switch_control']=pair_control;status['manual_switch']=pair_status()
            else:
                status['manual_switch']=manual_status();status['manual_switch_control']=control_status()
            status['channel_path']=path_status(status)
            try:
                from speed_test import public_status as speed_status
                status['speed_tests']=speed_status()
            except (OSError,ValueError,KeyError):status['speed_tests']={'code':'SPEED-STATUS-UNAVAILABLE','results':[]}
            status['server_time']=time.time()
        print(json.dumps({'events': status.get('events', [])} if method=='events' else trim_status_reply(status)))
    else:
        raise ValueError('RPC-UNKNOWN-METHOD')


def rpc_error_code(error):
    """Only a deliberate diagnostic code of ours is shown; any other text (paths, library messages) becomes SYSTEM-001."""
    text = str(error) if isinstance(error, ValueError) else ''
    return text if re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}', text) else 'SYSTEM-001'


def call(method):
    """One command-line RPC: always a JSON line on stdout, never a traceback for input problems."""
    try:
        rpc(method)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': rpc_error_code(error)}))
        return 1


def main():
    global STOP
    os.environ['TZ'] = 'CET-1CEST,M3.5.0,M10.5.0/3'
    from timezone_compat import refresh_timezone
    refresh_timezone()
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['daemon','list','call','preflight'])
    parser.add_argument('method', nargs='?')
    args = parser.parse_args()
    if args.action == 'preflight':
        result = {'version': VERSION, 'python': sys.version.split()[0], 'profiles': len(inventory()['profiles']),
                  'mode': 'monitor', 'native_apply': False}
        print(json.dumps(result));return
    if args.action in ('list','call'):
        if args.action == 'list':
            rpc('list');return
        raise SystemExit(call(args.method))

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
