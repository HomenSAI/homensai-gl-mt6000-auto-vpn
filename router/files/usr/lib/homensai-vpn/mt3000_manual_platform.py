"""Read-only MT3000 manual-adapter candidate evidence. Never grants route rights.

This module has no apply/start/stop/commit operation. Passing its candidate
checks is not a native certificate, a LAN test, or permission to bypass the
existing native controller's platform/deployment guards.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import time


EXPECTED_VENDOR = {
    '/usr/bin/rtp2.sh': 'd6863630241e0bc68f56cc1eb8ccca45006083c1166e742e8500b28b5e2a544e',
    '/usr/bin/setup_instance_via.lua': 'd18e9659bed098ad3f381a921888429f8a50f314a21748eaa566db0d74ca37f8',
    '/lib/functions/vpn_func/route_policy_func.sh': '25a74cb70c609e3229a2f99ff2253171dc4ec3f491ffd2e140928f1b11f6c5a8',
    '/lib/functions/vpn_func/global_leak_drop.sh': 'b324ae48bd31190d7d00833c906e15a43a6f2bf10147eb892ac16fd594a71782',
}
PROOF_SCOPE = 'router-only-readiness-candidate'
NOT_CERTIFIED = 'MT3000-MANUAL-ADAPTER-NOT-CERTIFIED'
PROC_ROOT = Path('/proc')
RUN_ROOT = Path('/var/run')
RTP_LOCK = Path('/tmp/run/rtp2.lock')
FIREWALL_LOCKS = (Path('/tmp/run/fw3.lock'), Path('/tmp/lock/procd_firewall.lock'))
COLLECTION_ERRORS = frozenset(('MT3000-COLLECTION-DEADLINE', 'MT3000-COLLECTION-CLOCK-CHANGED',
                               'MT3000-READ-TIMEOUT', 'MT3000-READ-FAILED', 'MT3000-READ-UNVERIFIED'))


class _CollectionError(ValueError):
    pass


def _decode(raw):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('nonfinite JSON value')
    value = json.loads(raw, object_pairs_hook=object_pairs, parse_constant=constant)
    _bounded(value)
    return value


def _bounded(value, depth=0, budget=None):
    budget = [20000] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        raise ValueError('evidence bounds')
    if isinstance(value, dict):
        if any(not isinstance(key, str) or len(key) > 256 for key in value):
            raise ValueError('evidence keys')
        for item in value.values():
            _bounded(item, depth + 1, budget)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth + 1, budget)
    elif isinstance(value, str):
        if len(value) > 131072:
            raise ValueError('evidence string')
    elif type(value) in (int, float):
        try:
            if not math.isfinite(value):
                raise ValueError('evidence finite')
        except OverflowError:
            raise ValueError('evidence finite') from None
    elif value is not None and type(value) is not bool:
        raise ValueError('evidence type')


def _zones(text):
    if not isinstance(text, str) or not 0 < len(text) <= 65536:
        raise ValueError('state size')
    zones = []
    defaults = 0
    section = None
    options = {}
    named = set()
    package = False
    count = 0
    def finish():
        if section == 'zone':
            name = options.get('name')
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', name):
                raise ValueError('state zone name')
            zones.append(name)
    for line in text.splitlines():
        words = shlex.split(line, comments=True)
        if not words:
            continue
        if words[0] == 'package':
            if words != ['package', 'fw3_state'] or package or section is not None:
                raise ValueError('state package')
            package = True
        elif words[0] == 'config':
            finish()
            count += 1
            if not package or not 2 <= len(words) <= 3 or words[1] not in ('defaults', 'zone', 'ipset') or count > 1024:
                raise ValueError('state section')
            if len(words) == 3:
                if words[2] in named:
                    raise ValueError('state duplicate section')
                named.add(words[2])
            section, options = words[1], {}
            defaults += section == 'defaults'
        else:
            if section is None or len(words) != 3 or words[0] not in ('option', 'list'):
                raise ValueError('state option')
            if words[0] == 'option':
                if words[1] in options:
                    raise ValueError('state duplicate')
                options[words[1]] = words[2]
            else:
                if words[1] in options and not isinstance(options[words[1]], list):
                    raise ValueError('state mixed option')
                options.setdefault(words[1], []).append(words[2])
    finish()
    if defaults != 1 or len(zones) != len(set(zones)) or not {'lan', 'wan'}.issubset(zones):
        raise ValueError('state zones')
    return set(zones)


def assess(evidence, now=None):
    """Classify bounded JSON evidence without performing I/O or changing it."""
    result = {
        'version': 1, 'eligibility': 'BLOCKED', 'can_apply': False,
        'available': False, 'candidate_checks_passed': False,
        'proof_scope': PROOF_SCOPE, 'native_certified': False,
        'lan_verified': False, 'vendor_attempts_exhausted': None,
        'blockers': [NOT_CERTIFIED], 'candidate_blockers': [],
    }
    reasons = result['candidate_blockers']
    def refuse(code):
        if code not in reasons:
            reasons.append(code)
    try:
        _bounded(evidence)
        if not isinstance(evidence, dict):
            raise ValueError('evidence object')
        errors = evidence.get('collection_errors', [])
        if not isinstance(errors, list) or any(not isinstance(code, str) or code not in COLLECTION_ERRORS for code in errors):
            raise ValueError('collection error')
        for code in errors:
            refuse(code)
        now = time.time() if now is None else now
        if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
            raise ValueError('clock')
        board = evidence.get('board')
        if not isinstance(board, dict) or board.get('board_name') != 'glinet,mt3000-snand' or board.get('model') != 'GL.iNet GL-MT3000':
            refuse('MT3000-PLATFORM-UNVERIFIED')
        release = board.get('release', {}) if isinstance(board, dict) else {}
        if (not isinstance(release, dict) or release.get('target') != 'mediatek/mt7981'
                or evidence.get('firmware') != '4.11.0' or evidence.get('kernel') != '5.4.211'
                or evidence.get('architecture') != 'aarch64'):
            refuse('MT3000-FIRMWARE-UNVERIFIED')
        hashes = evidence.get('vendor_hashes')
        if not isinstance(hashes, dict) or any(hashes.get(path) != sha for path, sha in EXPECTED_VENDOR.items()):
            refuse('VENDOR-CODE-UNVERIFIED')
        if evidence.get('journal_absent') is not True or evidence.get('own_guard_absent') is not True:
            refuse('MANUAL-TRANSACTION-STATE-UNVERIFIED')
        if evidence.get('fw4_absent') is not True:
            refuse('MT3000-FIREWALL-UNVERIFIED')
        if evidence.get('fw4_config') not in (None, '0'):
            refuse('MT3000-FIREWALL-UNVERIFIED')
        include = evidence.get('include')
        if (not isinstance(include, dict) or include.get('path') != '/usr/bin/rtp2.sh'
                or include.get('type') != 'script' or include.get('reload') != '0'
                or include.get('enabled') not in (None, '1')):
            refuse('FW3-INCLUDE-CONTRACT-UNVERIFIED')
        try:
            zones = _zones(evidence.get('fw3_state'))
        except (ValueError, TypeError):
            zones = set()
            refuse('FW3-RUNTIME-STATE-UNVERIFIED')
        workers = evidence.get('workers')
        if (not isinstance(workers, list) or len(workers) != 2
                or any(not isinstance(row, dict) or type(row.get('time')) not in (int, float)
                       or not 0 <= now-row['time'] <= 30
                       or type(row.get('busy')) is not int or row['busy'] != 0
                       or row.get('verified') is not True for row in workers)
                or workers[0]['time'] > workers[1]['time']):
            refuse('VENDOR-WORKER-QUIET-UNVERIFIED')
        policy = evidence.get('policy')
        metadata = evidence.get('inventory')
        if not isinstance(policy, dict) or not isinstance(metadata, dict):
            raise ValueError('policy metadata')
        if policy != evidence.get('policy_after'):
            refuse('POLICY-CHANGED-DURING-PREFLIGHT')
        settings = policy.get('settings')
        if not isinstance(settings, dict):
            raise ValueError('settings')
        if settings.get('monitor_only') == '1':
            refuse('MONITOR-ONLY-DEPLOYMENT')
        elif settings.get('monitor_only') != '0':
            refuse('MONITOR-ONLY-INVALID')
        if settings.get('native_enabled') != '0':
            refuse('NATIVE-CONTROLLER-STATE-UNVERIFIED')
        from agent import TERMS_VERSION
        if settings.get('terms_version') != TERMS_VERSION:
            refuse('TERMS-NOT-ACCEPTED')
        if policy.get('lan') != 'br-lan':
            refuse('LAN-LAYOUT-UNSUPPORTED')
        from native_switch import choose, Refused
        try:
            selection = choose(policy, metadata.get('profiles'))
        except Refused as error:
            selection = None
            refuse(str(error))
        if selection is not None:
            try:
                after = choose(evidence['policy_after'], evidence['inventory_after']['profiles'])
                if (after['hash'] != selection['hash'] or after['order'] != selection['order']
                        or any(any(after[role].get(k) != selection[role].get(k)
                                   for k in ('id', 'protocol', 'interface', 'vendor_tunnel_id'))
                               for role in ('source', 'target'))):
                    refuse('PROFILE-IDENTITY-CHANGED')
            except (Refused, KeyError, TypeError):
                refuse('PROFILE-IDENTITY-CHANGED')
            a, b = selection['order'].index(selection['source_rule']), selection['order'].index(selection['target_rule'])
            if abs(a-b) != 1:
                refuse('SELECTED-RULES-NOT-ADJACENT')
            from failure_diagnosis import resolve_pair, profile_identity
            pair = resolve_pair(evidence.get('status'), settings, now)
            if pair['coordination']['state'] != 'READY':
                refuse(pair['coordination']['code'])
            else:
                bindings = evidence.get('bindings')
                if not isinstance(bindings, dict):
                    raise ValueError('bindings')
                proof = {}
                for role in ('source', 'target'):
                    selected, observed = selection[role], pair[role]
                    if any(selected.get(k) != observed.get(k) for k in ('id', 'protocol', 'interface', 'vendor_tunnel_id')):
                        refuse('PROFILE-IDENTITY-CHANGED')
                    live = bindings.get(selected.get('interface'))
                    if (not isinstance(live, dict) or live.get('up') is not True
                            or live.get('pending') is not False or live.get('code') is not None
                            or not isinstance(live.get('device'), str) or not re.fullmatch(r'[A-Za-z0-9_]{1,15}', live['device'])
                            or not isinstance(live.get('table'), str) or not re.fullmatch(r'[0-9]{1,10}', live['table'])
                            or type(live.get('ifindex')) is not int or live['ifindex'] <= 0
                            or type(live.get('mark')) is not int or live['mark'] <= 0
                            or any(live.get(k) != observed.get(k) for k in ('device', 'mark', 'table', 'ifindex'))):
                        refuse('EXISTING-TUNNEL-BINDING-UNVERIFIED')
                    if selected.get('interface') not in zones:
                        refuse('FW3-SELECTED-ZONE-UNVERIFIED')
                    proof[role] = profile_identity(observed)
                source_live = bindings.get(selection['source']['interface'])
                target_live = bindings.get(selection['target']['interface'])
                if isinstance(source_live, dict) and isinstance(target_live, dict) and (
                        source_live.get('device') == target_live.get('device')
                        or source_live.get('ifindex') == target_live.get('ifindex')
                        or (source_live.get('mark'), source_live.get('table')) == (target_live.get('mark'), target_live.get('table'))):
                    refuse('SHARED-KERNEL-BINDING')
                target = pair['target']
                if (target.get('code') is not None or target.get('dns_ok') is not True
                        or type(target.get('https_success')) is not int or target['https_success'] < 2):
                    refuse('TARGET-ROUTER-PATH-UNVERIFIED')
                result['selection_digest'] = hashlib.sha256(json.dumps(
                    {'policy': selection['hash'], 'profiles': proof, 'bindings': bindings},
                    sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError, RecursionError):
        refuse('MT3000-EVIDENCE-UNVERIFIED')
    result['candidate_checks_passed'] = not reasons
    result['blockers'] += reasons
    return result


def _read(path, maximum=131072):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('unverified file')
    with path.open('rb') as stream:
        value = stream.read(maximum+1)
    if len(value) > maximum:
        raise ValueError('oversize file')
    return value


def _held_firewall_locks():
    targets = set()
    for path in FIREWALL_LOCKS:
        if path.is_symlink():
            raise ValueError('unverified lock path')
        try:
            metadata = path.stat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError('unverified lock file')
        targets.add((os.major(metadata.st_dev), os.minor(metadata.st_dev), metadata.st_ino))
    held = 0
    for line in _read(PROC_ROOT/'locks', 131072).decode('ascii').splitlines():
        words = line.split()
        offset = 2 if len(words) > 1 and words[1] == '->' else 1
        if len(words) != offset+7 or words[offset] not in ('FLOCK', 'POSIX', 'OFDLCK', 'LEASE'):
            raise ValueError('unverified lock record')
        parts = words[offset+4].split(':')
        if len(parts) != 3:
            raise ValueError('unverified lock identity')
        identity = (int(parts[0], 16), int(parts[1], 16), int(parts[2]))
        if identity in targets:
            held += 1
    return held


def _rtp_lock_busy():
    """The one stale lock a vendor-rebuild proof has just proven dead is not a worker."""
    import rollback_recovery as recovery
    if recovery.ALLOWED_STALE_LOCK[0] is None or str(RTP_LOCK) != recovery.VENDOR_LOCK:
        return True
    return recovery.rtp_lock_busy()


def _workers(deadline=None):
    """Two sampled quiet reads are evidence only, never worker arbitration."""
    if deadline is not None and time.monotonic() >= deadline:
        raise _CollectionError('MT3000-COLLECTION-DEADLINE')
    busy = _held_firewall_locks()
    entries = list(PROC_ROOT.iterdir())
    if len(entries) > 4096:
        raise ValueError('process limit')
    for path in entries:
        if deadline is not None and time.monotonic() >= deadline:
            raise _CollectionError('MT3000-COLLECTION-DEADLINE')
        if not path.name.isdigit():
            continue
        try:
            raw = _read(path/'stat', 8192).decode()
            tail = raw[raw.rindex(') ')+2:].split()
            if raw.split(' ', 1)[0] != path.name or len(tail) < 20:
                raise ValueError('process identity')
            if tail[0] in ('Z', 'X') or int(tail[6]) & 0x00200000:
                continue
            command = _read(path/'cmdline', 8192)
            if not command or not command.endswith(b'\0'):
                raise ValueError('process command')
            args = command[:-1].decode('utf8', 'replace').split('\0')
            wchan = _read(path/'wchan', 256).decode().strip()
            after = _read(path/'stat', 8192).decode()
            after_tail = after[after.rindex(') ')+2:].split()
            if len(after_tail) < 20 or after_tail[19] != tail[19] or after_tail[1] != tail[1]:
                raise ValueError('process identity changed')
            names = {Path(arg).name for arg in args}
            if (names.intersection({'fw3', 'rtp2.sh', 'gl_block_wan_access_exit', 'tunnel-switch.sh',
                                    'vpn-failover-trigger.sh', 'vpn-failover-watcher.sh', 'wgclient.sh',
                                    'hotplug-call','ovpnclient.sh'})
                    or any(name in args for name in('/etc/init.d/firewall','/etc/init.d/dnsmasq','/etc/init.d/network')) or wchan == 'locks_lock_inode_wait'):
                busy += 1
        except (OSError, ValueError, IndexError):
            if path.exists():
                raise ValueError('process read unverified') from None
    if list(RUN_ROOT.glob('tunnel-switch*.lock')) or RTP_LOCK.is_symlink() or RTP_LOCK.exists() and _rtp_lock_busy():
        busy += 1
    return {'time': time.time(), 'busy': busy, 'verified': True}


def preflight():
    """Collect bounded local read commands; no sockets, probes or route writes."""
    from agent import read_json, RUNTIME, TARGETS
    from native_switch import HELPER, JOURNAL, TABLE, choose, Refused
    evidence = {}
    started = time.monotonic()
    wall = time.time()
    end = started+20
    def remaining():
        now = time.monotonic()
        if not math.isfinite(now) or now < started:
            raise _CollectionError('MT3000-COLLECTION-CLOCK-CHANGED')
        if now >= end:
            raise _CollectionError('MT3000-COLLECTION-DEADLINE')
        return end-now
    def error(code):
        errors = evidence.setdefault('collection_errors', [])
        if code not in errors:
            errors.append(code)
    try:
        def output(args):
            left = remaining()
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, timeout=min(3, left), check=True)
            if len(result.stdout) > 131072:
                raise ValueError('command response')
            remaining()
            return result.stdout
        def query(args):
            return _decode(output(args))
        def policy():
            return query(['/usr/bin/lua', HELPER])
        def metadata():
            value = query(['/usr/bin/lua', '/usr/lib/homensai-vpn/inventory.lua'])
            if value.get('profiles') == {}:
                value['profiles'] = []
            return value
        def binding(interface):
            if not isinstance(interface, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,64}', interface):
                raise ValueError('interface')
            status = query(['ubus', '-t', '2', 'call', 'network.interface.'+interface, 'status'])
            if status.get('up') is not True or status.get('pending') is not False:
                return {'up': status.get('up'), 'pending': status.get('pending'), 'code': 'VPN-001'}
            device = status.get('l3_device')
            if not isinstance(device, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,15}', device):
                raise ValueError('device')
            routes = query(['ip', '-4', '-j', 'route', 'show', 'table', 'all'])
            rules = query(['ip', '-4', '-j', 'rule', 'show'])
            tables = {str(row.get('table', 'main')) for row in routes
                      if row.get('dev') == device and row.get('dst') == 'default'}
            candidates = {(int(str(row['fwmark']), 0), str(row.get('table'))) for row in rules
                          if str(row.get('table')) in tables and row.get('fwmark')}
            if len(candidates) != 1:
                raise ValueError('route candidates')
            mark, table = candidates.pop()
            if mark <= 0:
                raise ValueError('route mark')
            ifindex = int(_read(Path('/sys/class/net')/device/'ifindex', 64))
            for address, _, _, _ in TARGETS:
                route = query(['ip', '-4', '-j', 'route', 'get', address, 'mark', str(mark)])
                if len(route) != 1 or route[0].get('dev') != device or str(route[0].get('table', 'main')) != table:
                    raise ValueError('route mismatch')
            after = query(['ubus', '-t', '2', 'call', 'network.interface.'+interface, 'status'])
            if (after.get('up') is not True or after.get('pending') is not False
                    or after.get('l3_device') != device
                    or int(_read(Path('/sys/class/net')/device/'ifindex', 64)) != ifindex):
                raise ValueError('binding changed')
            return {'up': True, 'pending': False, 'code': None, 'device': device,
                    'mark': mark, 'table': table, 'ifindex': ifindex}
        evidence['workers'] = [_workers(end)]
        evidence.update(board=query(['ubus', '-t', '3', 'call', 'system', 'board']),
                        firmware=_read('/etc/glversion').decode().strip(),
                        kernel=os.uname().release, architecture=os.uname().machine,
                        vendor_hashes={path: hashlib.sha256(_read(path)).hexdigest() for path in EXPECTED_VENDOR},
                        journal_absent=not JOURNAL.exists() and not JOURNAL.is_symlink(),
                        fw4_absent=not any(Path(p).exists() for p in ('/sbin/fw4', '/usr/sbin/fw4')),
                        fw3_state=_read('/var/run/fw3.state', 65536).decode(),
                        policy=policy(), inventory=metadata(),
                        status=read_json(RUNTIME/'status.json', {}))
        lua = "local c=require('uci').cursor(); print(require('cjson').encode({include=c:get_all('firewall','vpnclient') or {},fw4_config=c:get('route_policy','global','use_fw4')}))"
        include = query(['/usr/bin/lua', '-e', lua])
        evidence.update(include)
        tables = output(['nft', 'list', 'tables']).decode().splitlines()
        if any(not re.fullmatch(r'table (?:inet|ip|ip6|arp|bridge|netdev) [A-Za-z0-9_]+', row) for row in tables):
            raise ValueError('table listing')
        evidence['own_guard_absent'] = 'table inet '+TABLE not in tables
        evidence['bindings'] = {}
        try:
            selected = choose(evidence['policy'], evidence['inventory']['profiles'])
        except Refused:
            selected = None  # assess returns the precise policy refusal.
        if selected:
            for role in ('source', 'target'):
                interface = selected[role]['interface']
                evidence['bindings'][interface] = binding(interface)
        evidence.update(policy_after=policy(), inventory_after=metadata())
    except _CollectionError as exc:
        error(str(exc))
    except subprocess.TimeoutExpired:
        error('MT3000-READ-TIMEOUT')
    except subprocess.CalledProcessError:
        error('MT3000-READ-FAILED')
    except Exception:
        # Never expose private policy/profile contents through exception text.
        error('MT3000-READ-UNVERIFIED')
    finally:
        try:
            evidence.setdefault('workers', []).append(_workers(end))
            remaining()
            if abs((time.time()-wall)-(time.monotonic()-started)) > 2:
                error('MT3000-COLLECTION-CLOCK-CHANGED')
        except _CollectionError as exc:
            error(str(exc))
        except (OSError, ValueError):
            error('MT3000-READ-UNVERIFIED')
    return assess(evidence)


if __name__ == '__main__':
    print(json.dumps(preflight(), sort_keys=True))
