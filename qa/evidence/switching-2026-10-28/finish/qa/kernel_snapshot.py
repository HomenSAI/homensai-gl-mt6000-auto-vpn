"""READ-ONLY router snapshot for HomenS.AI Auto VPN switching evidence.

Run on the router (python3 stdlib only), typically piped over SSH:
    ssh ... 'python3 - before-to-reserve' < kernel_snapshot.py > before.json
Optional second argument: a salt for masking public IPv4 addresses consistently
between the before/after snapshots of one run (default: no masking of raw text,
see --mask below). Usage:  python3 - <label> [mask-salt]

It never writes files, never imports product modules except the pure parser
kernel_policy.parse_mangle (with bytecode writing disabled), never calls uci
set/commit/reorder, nft add/delete, ip rule add/del or iptables -A/-D.
Commands executed: uci -q show route_policy; iptables-save -t mangle;
ip -4 -j rule show; ip -4 route show table <T>; nft list table inet homensai_vpn_guard;
plus reads of the app's runtime/persist JSON files.
"""
import hashlib, json, os, re, subprocess, sys, time

sys.dont_write_bytecode = True
RUNTIME = '/var/run/homensai-vpn'
PERSIST = '/etc/homensai-vpn'
APP_LIB = '/usr/lib/homensai-vpn'
GUARD_TABLE = 'homensai_vpn_guard'
SECRET = re.compile(r'^(?:.*[_-])?(?:token|secret|password|passwd|psk|private_?key|preshared_?key|cookie|sysauth\w*|stok|api_?key|auth_?key|bot_?token|chat_?id)$', re.I)
LABEL = sys.argv[1] if len(sys.argv) > 1 else ''
SALT = sys.argv[2] if len(sys.argv) > 2 else None


def sha(text):
    return hashlib.sha256(text.encode('utf-8') if isinstance(text, str) else text).hexdigest()


def digest(value):
    # Same canonical form as native_switch.digest.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def private_v4(a):
    p = [int(x) for x in a.split('.')]
    if any(x > 255 for x in p):
        return True
    x, y = p[0], p[1]
    return (x in (0, 10, 127) or x >= 224 or (x == 169 and y == 254) or (x == 172 and 16 <= y <= 31)
            or (x == 192 and y == 168) or (x == 100 and 64 <= y <= 127))


def mask(text):
    if SALT is None or not isinstance(text, str):
        return text
    return re.sub(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b',
                  lambda m: m.group(1) if private_v4(m.group(1)) else 'pubip-' + sha(SALT + ':' + m.group(1))[:10], text)


def redact(value, depth=0):
    if depth > 40:
        return '[depth]'
    if isinstance(value, dict):
        return {k: ('[redacted]' if SECRET.match(str(k)) and v not in (None, '') else redact(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, depth + 1) for v in value]
    return mask(value) if isinstance(value, str) else value


def run(argv, timeout=10):
    started = time.time()
    try:
        r = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {'rc': r.returncode, 'out': r.stdout.decode('utf-8', 'replace'), 'err': r.stderr.decode('utf-8', 'replace')[:400],
                'ms': int((time.time() - started) * 1000)}
    except (OSError, subprocess.SubprocessError) as e:
        return {'rc': None, 'out': '', 'err': type(e).__name__ + ': ' + str(e)[:300], 'ms': int((time.time() - started) * 1000)}


def read_json(path, limit=1024 * 1024):
    row = {'path': path, 'exists': os.path.exists(path)}
    if not row['exists']:
        return row
    try:
        st = os.lstat(path)
        row.update(size=st.st_size, mtime=st.st_mtime, symlink=os.path.islink(path))
        if row['symlink'] or st.st_size > limit:
            row['error'] = 'SKIPPED-SYMLINK-OR-LARGE'
            return row
        with open(path, 'rb') as f:
            raw = f.read()
        row['sha256'] = sha(raw)
        row['data'] = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError, UnicodeError) as e:
        row['error'] = type(e).__name__
    return row


def uci_route_policy():
    r = run(['uci', '-q', 'show', 'route_policy'])
    sections, order = {}, []
    for line in r['out'].splitlines():
        m = re.match(r"^route_policy\.([^.=]+)(?:\.([^=]+))?=(.*)$", line)
        if not m:
            continue
        name, option, value = m.group(1), m.group(2), m.group(3)
        if option is None:
            if name not in sections:
                order.append(name)
            sections.setdefault(name, {'type': value, 'options': {}})
        else:
            sections.setdefault(name, {'type': None, 'options': {}})['options'][option] = sha(value)[:16]
    return {'rc': r['rc'], 'err': r['err'] or None, 'order': order, 'output_sha256': sha(r['out']), 'lines': len(r['out'].splitlines()),
            'sections': [{'name': n, 'type': sections[n]['type'], 'option_value_sha256_16': sections[n]['options'],
                          'section_sha256_16': sha(json.dumps(sections[n], sort_keys=True))[:16]} for n in order],
            'note': 'values hashed only; order is the uci section order; this is NOT the product policy_hash (which uses process bindings)'}


def mangle():
    r = run(['iptables-save', '-t', 'mangle'])
    # Chain packet/byte counters change constantly; normalise them for equality comparison.
    normal = '\n'.join(re.sub(r'\[\d+:\d+\]', '[0:0]', l) for l in r['out'].splitlines() if not l.startswith('#'))
    out = {'rc': r['rc'], 'err': r['err'] or None, 'raw': mask(r['out']), 'normalized_sha256': sha(normal), 'rules': sum(1 for l in r['out'].splitlines() if l.startswith('-A '))}
    return out, r['out']


def product_fingerprint(mangle_text, rules):
    """Same digest as native_switch.Linux.kernel_fingerprint, using the installed pure parser."""
    try:
        if APP_LIB not in sys.path:
            sys.path.insert(0, APP_LIB)
        from kernel_policy import parse_mangle  # stdlib-only module (re, shlex, copy)
        return {'value': digest({'mangle': parse_mangle(mangle_text), 'rules': rules}), 'source': APP_LIB + '/kernel_policy.py'}
    except Exception as e:  # noqa: BLE001 - evidence must not crash
        return {'value': None, 'error': type(e).__name__ + ': ' + str(e)[:200]}


def main():
    started = time.time()
    snap = {'schema': 'homensai-kernel-snapshot/1', 'label': LABEL, 'time': started, 'monotonic': time.monotonic(),
            'read_only': True, 'public_ipv4_masked': SALT is not None}
    try:
        with open('/proc/sys/kernel/hostname') as f:
            snap['hostname'] = f.read().strip()
        with open('/etc/openwrt_release') as f:
            snap['openwrt_release'] = dict(re.findall(r"^(\w+)='?([^'\n]*)'?$", f.read(), re.M))
        with open('/tmp/sysinfo/model') as f:
            snap['model'] = f.read().strip()
    except OSError:
        pass
    snap['uci_route_policy'] = uci_route_policy()
    snap['mangle'], mangle_text = mangle()
    rr = run(['ip', '-4', '-j', 'rule', 'show'])
    try:
        rules = json.loads(rr['out'])
    except ValueError:
        rules = None
    snap['ip_rules'] = {'rc': rr['rc'], 'err': rr['err'] or None, 'rules': redact(rules), 'sha256': digest(rules) if rules is not None else None}
    snap['product_kernel_fingerprint'] = product_fingerprint(mangle_text, rules) if rules is not None and rr['rc'] == 0 else {'value': None, 'error': 'RULES-UNREADABLE'}
    tables = []
    for rule in rules or []:
        t = rule.get('table')
        if t is not None and str(t) not in ('local',) and str(t) not in tables:
            tables.append(str(t))
    snap['routes'] = {}
    for t in tables:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', t):
            continue
        r = run(['ip', '-4', 'route', 'show', 'table', t])
        snap['routes'][t] = {'rc': r['rc'], 'raw': mask(r['out']), 'sha256': sha(r['out'])}
    g = run(['nft', 'list', 'table', 'inet', GUARD_TABLE])
    snap['owned_guard'] = {'rc': g['rc'], 'exists': g['rc'] == 0, 'owned_marker': 'homensai-owned-guard' in g['out'],
                           'raw': mask(g['out']) if g['rc'] == 0 else None, 'err': (g['err'] or None) if g['rc'] not in (0, 1) else None}
    journal = read_json(PERSIST + '/native-transaction.json')
    data = journal.get('data') if isinstance(journal.get('data'), dict) else None
    inner = data.get('data') if data and isinstance(data.get('data'), dict) else None
    if inner is not None:
        journal['envelope_digest_ok'] = data.get('sha256') == digest(inner)
        journal['summary'] = {k: inner.get(k) for k in ('phase', 'tx', 'manual_request_id', 'control_revision', 'revision', 'confirmed', 'trial',
                                                       'hash', 'restore_proof_source', 'kernel_before_fingerprint', 'time', 'updated') if k in inner}
        journal['summary']['before'] = inner.get('before')
        journal['summary']['after'] = inner.get('after')
    snap['journal'] = redact(journal)
    files = {}
    for base, name in ((RUNTIME, 'pair-manual-control.json'), (RUNTIME, 'pair-auto-control.json'), (PERSIST, 'pair-auto-state.json'),
                       (PERSIST, 'pair-auto-budget.json'), (RUNTIME, 'native-status.json'), (RUNTIME, 'native-apply-progress.json'),
                       (RUNTIME, 'native-attempt-result.json'), (PERSIST, 'native-stop.json'), (RUNTIME, 'native-return.json'),
                       (RUNTIME, 'native-return-result.json'), (PERSIST, 'native-journal-alarm.json'), (RUNTIME, 'auto-control.json')):
        files[name] = redact(read_json(base + '/' + name))
    budget = files['pair-auto-budget.json'].get('data')
    if isinstance(budget, dict) and isinstance(budget.get('events'), list):
        files['pair-auto-budget.json']['events_count'] = len(budget['events'])
        nums = [e for e in budget['events'] if isinstance(e, (int, float))]
        files['pair-auto-budget.json']['last_event'] = max(nums) if nums else None
    snap['app_files'] = files
    status = read_json(RUNTIME + '/status.json', limit=8 * 1024 * 1024)
    sdata = status.pop('data', None)
    if isinstance(sdata, dict):
        status['subset'] = redact({k: sdata.get(k) for k in ('version', 'package', 'time', 'channel_path', 'native_failover', 'auto_control',
                                                            'manual_switch', 'manual_switch_control') if k in sdata})
    snap['status_json'] = status
    snap['vendor_locks'] = {'tunnel_switch_locks': sorted(p for p in os.listdir('/var/run') if p.startswith('tunnel-switch') and p.endswith('.lock')) if os.path.isdir('/var/run') else [],
                            'rtp2_lock': os.path.exists('/tmp/run/rtp2.lock')}
    snap['elapsed_ms'] = int((time.time() - started) * 1000)
    print(json.dumps(snap, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
