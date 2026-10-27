"""Explicit two-channel Auto with router-bound IPv4 evidence, never a LAN proof.

Intent is volatile: reboot/process recovery never silently resumes Auto. Profile
ownership and the rolling retry budget survive a crash. Existing native journal,
Stop revision, independent procd recovery and bounded per-transition leases stay
authoritative. No system routing, credentials or profile selection are imported.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid

MODE = 'router-probed-ipv4'
TERMINAL = {'STOPPED', 'FAILED'}
INTERFACES = {'wgclient1': 'wgclient', 'ovpnclient1': 'ovpnclient'}


def require_running(revision):
    import native_switch as n
    n.require_control_revision(revision)
    if n.STOP:
        raise n.Refused('CLIENT-STOP')


def quiet(seconds, revision=None):
    import native_switch as n
    from native_platform import wait_quiet
    from mt3000_manual_platform import _workers
    last=[0.0]
    def sample(end):
        if revision is not None:
            require_running(revision)
        now=time.monotonic()
        if now-last[0]>=4:
            n.publish({'state':'ARMED' if revision else 'RESTORING','reason':'PAIR-CONNECTING' if revision else 'PAIR-CLEANUP',
                       'mode':'continuous-pair','proof_scope':MODE,'blockers':[]})
            last[0]=now
        return _workers(end)
    wait_quiet(seconds,sample=sample)


def paths():
    from agent import RUNTIME, PERSIST
    return RUNTIME / 'pair-auto-control.json', PERSIST / 'pair-auto-state.json'


def read_state():
    from agent import read_json, checksum
    _, path = paths()
    if path.is_symlink():
        raise ValueError('PAIR-STATE-UNVERIFIED')
    envelope = read_json(path, {})
    if not envelope:
        return {}
    data = envelope.get('data') if isinstance(envelope, dict) else None
    from pair_interfaces import state as state_interfaces
    try:managed=state_interfaces(data) if isinstance(data,dict) else {}
    except (ValueError,TypeError):raise ValueError('PAIR-STATE-UNVERIFIED') from None
    if (not isinstance(data, dict) or envelope.get('sha256') != checksum(data)
            or not isinstance(data.get('phase'), str)
            or data.get('phase') not in {'STARTING', 'RUNNING', 'STOPPING', 'HELD', 'STOPPED', 'FAILED'}
            or not isinstance(data.get('id'), str) or not __import__('re').fullmatch('[a-f0-9]{32}', data['id'])
            or not isinstance(data.get('owned'), list) or any(not isinstance(x,str) for x in data['owned'])
            or len(data['owned']) != len(set(data['owned']))
            or any(x not in managed for x in data['owned'])
            or not isinstance(data.get('before_flags'), dict) or set(data['before_flags']) != set(managed)
            or any(x not in ('0', '1') for x in data['before_flags'].values())
            or not isinstance(data.get('network_identity'), str) or not __import__('re').fullmatch('[a-f0-9]{64}', data['network_identity'])):
        raise ValueError('PAIR-STATE-UNVERIFIED')
    if 'manual_hold' in data and data['manual_hold'] not in ('source','target'):raise ValueError('PAIR-MANUAL-HOLD-UNVERIFIED')
    if 'manual_hold_source' in data and data['manual_hold_source'] not in ('manual','test','programmatic','unknown'):raise ValueError('PAIR-MANUAL-HOLD-UNVERIFIED')
    return data


def save(state):
    from agent import atomic_json, checksum
    atomic_json(paths()[1], {'data': state, 'sha256': checksum(state)})


def intent():
    from agent import read_json
    row = read_json(paths()[0], {})
    if not isinstance(row, dict):
        raise ValueError('PAIR-INTENT-UNVERIFIED')
    if row and (row.get('mode') not in ('on', 'off') or not isinstance(row.get('revision'), str)
                or type(row.get('time')) not in (int, float) or not math.isfinite(row['time'])):
        raise ValueError('PAIR-INTENT-UNVERIFIED')
    return row


# Settings changed outside the app (a tunnel renamed or reordered, a stock client tidied) must not leave Auto
# off for good. The saved session is handed over to the current configuration automatically: its original record
# is archived first, interface flags are never restored over the new configuration, and a fresh Start re-reads
# everything. Bounded so that a persistent conflict still ends in a visible refusal.
READOPT_CODES = ('PAIR-EXTERNAL-NETWORK-CHANGE', 'PAIR-EXTERNAL-CONFIG-CHANGE', 'PAIR-EXTERNAL-POLICY-CHANGE',
                 'SOURCE-ORDER-MISMATCH')
READOPT_LIMIT = 3


def readopt_allowed(now):
    from agent import RUNTIME, read_json
    try:
        ledger = read_json(RUNTIME / 'pair-readopt.json', {})
    except (OSError, ValueError):
        ledger = {}
    events = ledger.get('events', []) if isinstance(ledger, dict) else []
    events = [x for x in events if type(x) in (int, float) and math.isfinite(x) and 0 <= now - x < 900] if isinstance(events, list) else []
    return events, len(events) < READOPT_LIMIT


def release_session(state, code):
    import native_switch as n
    from agent import PERSIST, RUNTIME, atomic_json
    now = time.time()
    events, allowed = readopt_allowed(now)
    if not allowed or n.journal_read().get('phase') not in (None, 'ROLLED-BACK'):
        return False
    path = paths()[1]
    raw = path.read_bytes()
    directory = PERSIST / 'session-recovery'
    if directory.is_symlink():
        raise ValueError('PAIR-STATE-UNVERIFIED')
    directory.mkdir(mode=0o700, exist_ok=True)
    archive = directory / ('pair-' + state['id'] + '-readopt-' + str(int(now)) + '.json')
    fd = os.open(str(archive), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if archive.read_bytes() != raw:
        raise ValueError('PAIR-STATE-UNVERIFIED')
    resolved = copy.deepcopy(state)
    resolved.update(phase='STOPPED', owned=[], original_restored=False, recovery_error=None,
                    operator_resolution={'reason': 'AUTOMATIC-EXTERNAL-CHANGE-READOPT', 'time': now, 'archive': archive.name,
                                         'trigger': code, 'original_sha256': hashlib.sha256(raw).hexdigest(),
                                         'retired_owned': state.get('owned', []), 'old_flags_restored': False})
    save(resolved)
    atomic_json(RUNTIME / 'pair-readopt.json', {'events': events + [now]})
    return True


def readopt_running(state, request_row, revision, code):
    """A running session met a change made outside the app: adopt the new configuration and start again by itself."""
    import native_switch as n
    from auto_control import control_lock, revision_locked
    from agent import RUNTIME, atomic_json
    with control_lock():
        current = intent()
        if (revision_locked(RUNTIME) != revision or current.get('revision') != revision or current.get('mode') != 'on'
                or current.get('id') != request_row.get('id') or not release_session(state, code)):
            return False
        atomic_json(paths()[0], {'mode': 'on', 'revision': revision, 'time': time.time(), 'id': uuid.uuid4().hex,
                                 'request_source': current.get('request_source', 'unknown')})
    n.publish({'state': 'ARMED', 'mode': 'continuous-pair', 'proof_scope': MODE, 'reason': 'PAIR-READOPTED', 'blockers': []})
    return True


def request(revision,request_source=None):
    from auto_control import control_lock, revision_locked
    from agent import RUNTIME, atomic_json
    with control_lock():
        from speed_pause import public as pause_status
        if pause_status().get('active'):return {'accepted':False,'blockers':['SPEED-BUSY']}
        if revision != revision_locked(RUNTIME):
            return {'accepted': False, 'blockers': ['CONTROL-REVISION-STALE']}
        try:
            state = read_state()
            old = intent()
        except (OSError, ValueError):
            return {'accepted': False, 'blockers': ['PAIR-STATE-UNVERIFIED']}
        if state and state.get('phase') not in TERMINAL and not (
                old.get('mode')=='on' and old.get('revision')==revision and old.get('id')==state.get('id')):
            # A session held only because settings changed outside the app is handed over automatically.
            try:
                handed=state.get('phase')=='HELD' and state.get('recovery_error') in READOPT_CODES and release_session(state,state['recovery_error'])
            except (OSError, ValueError, KeyError, TypeError):
                handed=False
            if not handed:
                return {'accepted': False, 'blockers': ['PAIR-RECOVERY-REQUIRED']}
        if old.get('mode') == 'on' and old.get('revision') == revision:
            return {'accepted': True, 'queued': True, 'already_requested': True}
        from auto_control import normalize_request_source as source_label
        atomic_json(paths()[0], {'mode': 'on', 'revision': revision, 'time': time.time(), 'id': uuid.uuid4().hex,'request_source':source_label(request_source)})
    return {'accepted': True, 'queued': True, 'mode': 'continuous-pair', 'proof_scope': MODE,
            'external_lan_verified': False}


def stop_locked(revision,request_source="programmatic"):
    from agent import atomic_json
    from auto_control import normalize_request_source
    atomic_json(paths()[0], {'mode': 'off', 'revision': revision, 'time': time.time(),'request_source':normalize_request_source(request_source)})


def public_intent():
    try:
        row = intent()
    except (OSError, ValueError):
        return None
    return row if row.get('mode') == 'on' else None


def public_phase():
    """Display phase includes queued work before the supervisor consumes it."""
    try:
        requested = intent()
        state = read_state()
    except (OSError, ValueError):
        return 'UNKNOWN'
    if requested.get('mode') == 'on':
        if state.get('id') != requested.get('id') or state.get('revision') != requested.get('revision'):
            return 'STARTING'
        return state.get('phase', 'STARTING')
    if (requested.get('mode')=='off' and isinstance(requested.get('failed_request_id'),str)
            and __import__('re').fullmatch('[a-f0-9]{32}',requested['failed_request_id'])
            and isinstance(requested.get('failure_code'),str)
            and __import__('re').fullmatch('[A-Z][A-Z0-9_-]{0,95}',requested['failure_code'])
            and state.get('phase') in (None,'STOPPED','FAILED')):
        return 'FAILED'
    if state.get('phase') in ('STARTING', 'RUNNING', 'STOPPING'):
        return 'STOPPING'
    return state.get('phase')


def fail_request(request,revision,error):
    """A refused preflight is terminal, not an indefinitely queued Start."""
    import native_switch as n
    from auto_control import control_lock,revision_locked
    from agent import atomic_json,RUNTIME
    code=str(error) if isinstance(error,(n.Refused,ValueError)) and n.re.fullmatch('[A-Z][A-Z0-9_-]{0,95}',str(error)) else 'PAIR-SYSTEM-001'
    with control_lock():
        current=intent()
        if (revision_locked(RUNTIME)!=revision or current.get('revision')!=revision
                or current.get('mode')!='on' or current.get('id')!=request.get('id')):
            return False
        atomic_json(paths()[0],{'mode':'off','revision':revision,'time':time.time(),
                    'failed_request_id':request['id'],'failure_code':code,'request_source':current.get('request_source','unknown')})
    return True


def budget(events, now, window=900, limit=3):
    """Configurable rolling limit; retain 15 minutes, and never reset on Start."""
    if (not isinstance(events, list) or len(events) > 16 or type(now) not in (int, float)
            or not math.isfinite(now) or any(type(x) not in (int, float) or not math.isfinite(x)
                                           or x < 0 or x > now for x in events)):
        raise ValueError('PAIR-BUDGET-UNVERIFIED')
    if type(window)is not int or not 60<=window<=900 or type(limit)is not int or not 1<=limit<=10:
        raise ValueError('PAIR-BUDGET-UNVERIFIED')
    # Keep the whole maximum window so later policy changes cannot erase attempts.
    kept = sorted(x for x in events if now - x < 900)
    count=sum(now-x<window for x in kept)
    return kept, count < limit and len(kept)<16


NETWORK_READ = r"""
local c=require('uci').cursor();local j=require('cjson');local sections={}
local pending=c:changes('network');assert(not pending or next(pending)==nil,'pending')
c:foreach('network',nil,function(s) s['.index']=nil;sections[#sections+1]=s end)
print(j.encode(sections))
"""
NETWORK_WRITE = r"""
local j=require('cjson');local u=require('uci');local q=j.decode(io.read('*a'))
local c=u.cursor('/etc/config',q.stage);local all={}
for _,p in ipairs({'network','wireguard','ovpnclient','route_policy','homensai_vpn'})do
 local x=u.cursor():changes(p);assert(not x or next(x)==nil,'pending')end
c:foreach('network',nil,function(s)s['.index']=nil;all[#all+1]=s end)
local function eq(a,b)
 if type(a)~=type(b)then return false end
 if type(a)~='table'then return a==b end
 for k,v in pairs(a)do if not eq(v,b[k])then return false end end
 for k in pairs(b)do if a[k]==nil then return false end end return true end
assert(eq(all,q.expected),'changed')
assert(type(q.managed)=='table'and q.managed[q.interface],'interface')
local count=0
for name,proto in pairs(q.managed)do
 assert(name:match('^wgclient[1-9]%d*$')and proto=='wgclient'or name:match('^ovpnclient[1-9]%d*$')and proto=='ovpnclient','interface')
 assert(#name<=14,'interface');count=count+1
end
assert(count==2,'interface')
assert(q.value=='0'or q.value=='1','value')
assert(c:set('network',q.interface,'disabled',q.value));assert(c:save('network'));assert(c:commit('network'))
"""


def network():
    from native_switch import command
    data = json.loads(command(['lua', '-e', NETWORK_READ]))
    if not isinstance(data, list) or not 1 <= len(data) <= 400:
        raise ValueError('PAIR-NETWORK-UNVERIFIED')
    return data


# A stopped client the pair does not use is a stock leftover that the firmware
# may tidy on its first route change; it is not part of the selected pair.
ORPHAN_CLIENT = re.compile(r'(?:wgclient|ovpnclient)[1-9][0-9]{0,3}')
ORPHAN_DNSMASQ = re.compile(rb"config[ \t]+dnsmasq[ \t]+'((?:wgclient|ovpnclient)[1-9][0-9]{0,3})'")
DISABLED_OPTION = re.compile(rb"\n[ \t]*option[ \t]+disabled[ \t]+'1'")


def normalized_network(data, interfaces=None):
    from agent import checksum
    managed = INTERFACES if interfaces is None else interfaces
    rows = []
    for row in copy.deepcopy(data):
        name = row.get('.name')
        if name in managed:
            row.pop('disabled', None)
        elif isinstance(name, str) and ORPHAN_CLIENT.fullmatch(name) and row.get('disabled') == '1':
            continue
        rows.append(row)
    return checksum(rows)


# The stock client adds exit bookkeeping options to a firewall zone while a
# tunnel is up and removes them when it stops. They are not an external edit.
VENDOR_EXIT_OPTIONS = re.compile(rb'[ \t]*option[ \t]+gl_(?:wan_like|bwa_managed|bwa_exit_id|bwa_bridge_reject)[ \t].*')


def config_digest(name, data, interfaces=None):
    if name == 'dhcp':
        managed = INTERFACES if interfaces is None else interfaces
        kept = []
        for block in re.split(rb'\n(?=config )', data):
            match = ORPHAN_DNSMASQ.match(block)
            if match and match.group(1).decode() not in managed and DISABLED_OPTION.search(block):
                continue
            kept.append(block)
        data = b'\n'.join(kept)
    if name == 'firewall':
        data = b'\n'.join(line for line in data.split(b'\n') if not VENDOR_EXIT_OPTIONS.fullmatch(line.rstrip(b'\r')))
    return hashlib.sha256(data).hexdigest()


def configs(interfaces=None):
    result = {}
    for name in ('wireguard', 'ovpnclient', 'firewall', 'route_policy', 'wireless', 'dhcp', 'gl-dns-v2'):
        p = Path('/etc/config') / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 1048576:
            raise ValueError('PAIR-CONFIG-UNVERIFIED')
        result[name] = config_digest(name, p.read_bytes(), interfaces)
    return result


def changed(state, observed, skip=()):
    """Protected configuration drift. Sessions saved by alpha36 and older hold the raw firewall digest."""
    for name, sha in state['protected'].items():
        if name == 'route_policy' or name in skip:
            continue
        if observed[name] != sha and not (name == 'firewall' and hashlib.sha256(Path('/etc/config/firewall').read_bytes()).hexdigest() == sha):
            return True
    return False


def set_disabled(state, interface, value, revision=None):
    from agent import RUNTIME
    import native_switch as n
    data = network()
    from pair_interfaces import state as state_interfaces
    managed=state_interfaces(state)
    if interface not in managed:raise ValueError('PAIR-PROFILES-UNVERIFIED')
    if normalized_network(data,managed) != state['network_identity']:
        raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
    # RTP legitimately derives gl_process_vpn; the native semantic policy hash
    # separately binds that rule. Never accept edits to profile credentials.
    if changed(state, configs(managed)):
        raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
    with tempfile.TemporaryDirectory(prefix='pair-uci-', dir=str(RUNTIME)) as stage:
        payload = json.dumps({'stage': stage, 'expected': data, 'interface': interface, 'value': value,'managed':managed}).encode()
        if revision is None:
            reply = subprocess.run(['lua', '-e', NETWORK_WRITE], input=payload, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=8)
            if reply.returncode:
                raise ValueError('PAIR-NETWORK-WRITE-FAILED')
        else:
            require_running(revision)
            from auto_control import control_lock, revision_locked
            with control_lock():
                if revision_locked(RUNTIME) != revision:
                    raise ValueError('CONTROL-REVISION-STALE')
                reply = subprocess.run(['lua', '-e', NETWORK_WRITE], input=payload, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=8)
            if reply.returncode:
                raise ValueError('PAIR-NETWORK-WRITE-FAILED')
            require_running(revision)
    after = network()
    row = next((r for r in after if r.get('.name') == interface), {})
    if normalized_network(after,managed) != state['network_identity'] or row.get('disabled') != value:
        raise ValueError('PAIR-NETWORK-WRITE-UNVERIFIED')


def preflight(backend, settings):
    import native_switch as n
    from agent import inventory
    from preparation_status import snapshot
    if settings.get('pair_auto_mode') != MODE or settings.get('terms_version') != '1':
        raise ValueError('PAIR-MODE-NOT-CONFIGURED')
    if settings.get('native_session_loss') != '1':
        raise ValueError('SESSION-LOSS-NOT-ACCEPTED')
    if Path('/tmp/sysinfo/board_name').read_text().strip() != 'glinet,mt3000-snand':
        raise ValueError('PAIR-PLATFORM-UNVERIFIED')
    if Path('/etc/glversion').read_text().strip() != '4.11.0':
        raise ValueError('UNSUPPORTED-FIRMWARE')
    preparation = snapshot(settings=settings)
    if preparation['state'] != 'pass':
        failed = [row['code'] for row in preparation.get('checks', []) if row.get('state') != 'pass']
        raise ValueError(failed[0] if failed else 'PAIR-PREPARATION-REQUIRED')
    from device_profile import detect,validate
    validate(settings.get('router_model','auto'),detect())
    from native_platform import PINS
    pins = dict(PINS)
    pins.update(json.loads(Path(n.__file__).with_name('native-audit-hashes.json').read_text()))
    for name, sha in pins.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha:
            raise ValueError('VENDOR-CODE-CHANGED')
    acceleration = backend.acceleration()
    if any(x in acceleration['loaded'] for x in ('shortcut_fe', 'fast_classifier')) or (
            any(x in acceleration['loaded'] for x in ('mtkhnat', 'mtk_hnat')) and acceleration['hnat_runtime'] != 'disabled'):
        raise ValueError('PAIR-PREPARATION-REQUIRED')
    data = backend.policy()
    from native_platform import assess
    board=json.loads(n.command(['ubus','call','system','board']))
    errors=assess(board,data)
    # The selected firewall zones may only appear when the inactive clients
    # start. Every firmware/source/worker guard remains mandatory beforehand;
    # the complete diagnostic, including zones, is required before switching.
    errors=[code for code in errors if code!='FW3-SELECTED-ZONE-UNVERIFIED']
    if errors:
        raise ValueError(errors[0])
    selection = n.choose(data, inventory()['profiles'])
    from pair_interfaces import selection as selection_interfaces
    selection_interfaces(selection)
    backend.use_process_bindings(selection['process_bindings'])
    return selection


REVIVE_PAUSE = 120
REVIVE_LIMIT = 4
REVIVE_PHASES = (None, 'ROLLED-BACK', 'COMMITTED', 'HELD-ON-RESERVE')


def client_down(interface):
    """True only for a client netifd reports stopped, never one still connecting."""
    import native_switch as n
    try:
        status = json.loads(n.command(['ubus', 'call', 'network.interface.' + interface, 'status']))
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return (isinstance(status, dict) and status.get('up') is False and not status.get('pending')
            and status.get('available', True) is not False)


def revive(backend, state, revision, journal, rows):
    """Start an operator-enabled client that is down, so a free channel never waits.

    A client can be enabled yet stopped (no boot start, an earlier stop, a
    dropped reconnect). Link-down on the target would then block the pair
    forever. One bounded, Stop-fenced attempt per client; a client the
    operator disabled is never touched.
    """
    import native_switch as n
    from agent import RUNTIME, atomic_json, read_json
    from pair_interfaces import state as state_interfaces
    from speed_pause import public as pause_status
    if journal.get('phase') not in REVIVE_PHASES or pause_status().get('active'):
        return False
    if list(Path('/var/run').glob('tunnel-switch*.lock')) or Path('/tmp/run/rtp2.lock').exists():
        return False
    now = time.time()
    path = RUNTIME / 'pair-revive.json'
    try:
        ledger = read_json(path, {})
    except (OSError, ValueError):
        ledger = {}
    if not isinstance(ledger, dict):
        ledger = {}
    by_name = {row.get('.name'): row for row in rows}
    for interface in sorted(state_interfaces(state)):
        events = ledger.get(interface, [])
        events = [x for x in events if type(x) in (int, float) and math.isfinite(x) and 0 <= now - x < 900] if isinstance(events, list) else []
        if by_name.get(interface, {}).get('disabled') != '0':
            continue
        if events and now - events[-1] < REVIVE_PAUSE or len(events) >= REVIVE_LIMIT:
            continue
        if not client_down(interface):
            continue
        atomic_json(path, dict(ledger, **{interface: events + [now]}))
        if interface not in state['owned']:
            state['owned'].append(interface)
            save(state)
        try:
            n.forward_dispatch(['ifup', '-w', interface], revision, timeout=20)
        except subprocess.SubprocessError:
            return True  # Counted attempt; the next one waits for the pause.
        quiet(45, revision)
        backend.guard(backend.devices(), control_revision=revision)
        return True
    return False


def begin(backend, settings, request):
    import native_switch as n
    selection = preflight(backend, settings)
    from pair_interfaces import selection as selection_interfaces
    managed=selection_interfaces(selection)
    data = network()
    selected = {row['.name']: row for row in data if row.get('.name') in managed}
    if set(selected) != set(managed) or any(
            row.get('proto') != managed[name] or row.get('auto') != '0' or row.get('disabled') not in ('0', '1')
            for name, row in selected.items()):
        raise ValueError('PAIR-PROFILES-UNVERIFIED')
    state = dict(id=request['id'], phase='STARTING', started=time.time(), revision=request['revision'],
                 network_identity=normalized_network(data,managed), interfaces=managed, protected=configs(managed), owned=[],
                 before_flags={name: row['disabled'] for name, row in selected.items()},
                 process_bindings=selection['process_bindings'], order=selection['order'], policy_hash=selection['hash'])
    save(state)  # Durable ownership precedes any network write.
    backend.guard()
    for role in ('source', 'target'):
        interface = selection[role]['interface']
        require_running(request['revision'])
        quiet(20,request['revision'])
        if selected[interface]['disabled'] == '1':
            state['owned'].append(interface)
            save(state)
            set_disabled(state, interface, '0', request['revision'])
            # Stock -w suppresses unrelated Wi-Fi setup; it is not a wait flag.
            n.forward_dispatch(['ifup', '-w', interface], request['revision'], timeout=20)
            quiet(45,request['revision'])
        elif client_down(interface):
            # Enabled by the operator but stopped: Auto starts it and restores it on Stop.
            state['owned'].append(interface)
            save(state)
            try:
                n.forward_dispatch(['ifup', '-w', interface], request['revision'], timeout=20)
            except subprocess.SubprocessError:
                pass  # The running supervisor retries within its bounded budget.
            quiet(45,request['revision'])
    state['phase'] = 'RUNNING'
    require_running(request['revision'])
    backend.guard(backend.devices(), control_revision=request['revision'])
    save(state)
    return state


def cleanup(backend, state):
    import native_switch as n
    from pair_interfaces import state as state_interfaces
    managed=state_interfaces(state)
    backend.use_process_bindings(state.get('process_bindings'))
    journal = n.journal_read()
    if journal.get('phase') in ('COMMITTED', 'HELD-ON-RESERVE'):
        if not n.finish_committed(backend, journal, 'PAIR-STOPPED'):
            state['phase'] = 'HELD'
            save(state)
            return False
    if backend.order() != (state['order'], state['policy_hash']):
        raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
    state['phase'] = 'STOPPING'
    save(state)
    for interface in reversed(state['owned']):
        # Never stop a profile after an external identity/configuration change.
        if normalized_network(network(),managed) != state['network_identity']:
            raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        # The stock client edits the firewall while a tunnel is up; ifdown undoes it,
        # and set_disabled below verifies the firewall again after the stop.
        if changed(state, configs(managed), skip=('firewall',)):
            raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
        n.command(['ifdown', interface], timeout=20)
        quiet(45)
        set_disabled(state, interface, state['before_flags'][interface])
        if Path('/sys/class/net', interface).exists():
            raise ValueError('PAIR-PROFILE-STOP-UNVERIFIED')
    backend.unguard()
    state['phase'] = 'STOPPED'
    save(state)
    return True


def recover(backend):
    """Called after core journal recovery on supervisor restart; never resumes."""
    import native_switch as n
    from auto_control import control_lock, revision_locked
    from agent import RUNTIME
    try:
        # Fence old intent even when its durable ownership can no longer be
        # reconciled. Retain that ownership and every recovery guard on failure.
        if paths()[0].exists():
            with control_lock():
                stop_locked(revision_locked(RUNTIME))
        state = read_state()
        from pair_manual import recover as recover_manual
        recover_manual()
        if state and state['phase'] not in TERMINAL:
            if not cleanup(backend, state):
                publish_failure('PAIR-RECOVERY-REQUIRED')
                return False
    except (n.Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        publish_failure(error)
        return False
    return True


def publish_failure(error):
    """Expected recovery conflicts are observable states, never daemon exits."""
    import native_switch as n
    code = str(error) if isinstance(error, (str, n.Refused, ValueError)) and n.re.fullmatch('[A-Z][A-Z0-9_-]{0,95}', str(error)) else 'PAIR-SYSTEM-001'
    try:
        pending = read_state()
        if pending and pending['phase'] not in TERMINAL:
            pending.update(phase='HELD', recovery_error=code)
            save(pending)
    except (OSError, ValueError, KeyError, TypeError):
        pass  # Never overwrite an unreadable ownership record.
    value = {'state': 'BLOCKED', 'mode': 'continuous-pair', 'proof_scope': MODE,
             'original_restored': False, 'blockers': [code]}
    try:
        n.publish(value)
    except n.Refused:
        # A damaged history must not hide the live recovery error.
        from agent import atomic_json
        atomic_json(n.STATE, dict(value, time=time.time(), history_error='HISTORY-001'))


def configure_lease(state):
    """A fresh bounded transaction lease, not an expiring controller session."""
    import native_switch as n
    from agent import RUNTIME
    require_running(state['revision'])
    until = time.time() + 180
    with tempfile.TemporaryDirectory(prefix='pair-lease-', dir=str(RUNTIME)) as stage:
        script = ("local c=require('uci').cursor('/etc/config',%s);"
                  "c:set('homensai_vpn','main','native_proof_scope','router-probed-ipv4');"
                  "c:set('homensai_vpn','main','native_trial',%s);"
                  "c:set('homensai_vpn','main','native_until',%s);"
                  "assert(c:save('homensai_vpn'));assert(c:commit('homensai_vpn'))") % (
                      json.dumps(stage), json.dumps(state['id']), json.dumps(str(until)))
        path = Path(stage) / 'lease.lua'
        path.write_text(script, encoding='utf8')
        n.forward_dispatch(['lua', str(path)], state['revision'], timeout=8)
    return until


def tick(backend, settings, revision):
    import native_switch as n
    from agent import RUNTIME, PERSIST, read_json, atomic_json
    from recovery_settings import normalized
    from failover_plan import streak
    from failure_diagnosis import diagnose
    request_row={}
    try:
        request_row = intent()
        state = read_state()
        running = request_row.get('mode') == 'on' and request_row.get('revision') == revision
        relevant = running or state and state['phase'] not in TERMINAL
        if not relevant:
            return False
        if not running:
            if state and state['phase'] not in TERMINAL:
                if not cleanup(backend, state):
                    return True
            n.publish({'state': 'STOPPED', 'mode': 'continuous-pair', 'proof_scope': MODE,
                       'original_restored': not state or state['phase'] == 'STOPPED', 'blockers': []})
            return True
        if not state or state['id'] != request_row['id']:
            if settings.get('pair_auto_mode')!=MODE:
                raise ValueError('PAIR-MODE-NOT-CONFIGURED')
            if state and state['phase'] not in TERMINAL:
                raise ValueError('PAIR-RECOVERY-REQUIRED')
            state = begin(backend, settings, request_row)
        backend.use_process_bindings(state['process_bindings'])
        if settings.get('pair_auto_mode')!=MODE:
            raise ValueError('PAIR-MODE-NOT-CONFIGURED')
        from pair_interfaces import state as state_interfaces
        rows=network()
        if normalized_network(rows,state_interfaces(state))!=state['network_identity']:
            raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        current_configs=configs(state_interfaces(state))
        if changed(state,current_configs):
            raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
        journal = n.journal_read()
        status = read_json(RUNTIME / 'status.json', {})
        from pair_manual import consume as consume_manual,held_reserve
        if consume_manual(backend,state,settings,revision):return True
        if held_reserve(backend,state,journal,settings,status):return True
        if revive(backend,state,revision,journal,rows):return True
        if journal.get('phase') in ('COMMITTED', 'HELD-ON-RESERVE'):
            decision = n.committed_recovery_decision(backend, journal, settings, status.get('samples', []), time.time(), status)
            if decision['action'] == 'RESTORE-PRIMARY':
                n.publish({'state': 'RESTORING', 'mode': 'continuous-pair', 'proof_scope': MODE,
                           'source': journal['source'], 'target': journal['target'],
                           'reason': decision['reason'], 'blockers': []})
                if n.finish_committed(backend, journal, decision['reason']):
                    n.publish({'state':'ROLLED-BACK','reason':decision['reason'],
                               'source':journal['source'],'target':journal['target'],
                               'original_restored':True,'mode':'continuous-pair','proof_scope':MODE})
            else:
                n.publish({'state': 'COMMITTED' if decision['action'] == 'OBSERVE' else 'DEGRADED-ON-RESERVE',
                           'source': journal['source'], 'target': journal['target'], 'mode': 'continuous-pair',
                           'proof_scope': MODE, 'reason': decision['reason'], 'blockers': []})
                return True
        blockers, selection = backend.diagnostic()
        if blockers:
            preparing=(0<=time.time()-state['started']<=180 and all(x in('VENDOR-SETTLING','OBSERVATION-STALE','PROFILE-IDENTITY-CHANGED','RESERVE-NOT-CONNECTED')for x in blockers))
            n.publish({'state': 'ARMED'if preparing else'BLOCKED', 'mode': 'continuous-pair', 'proof_scope': MODE,
                       'reason':'PAIR-WAITING-PROBES'if preparing else None,'blockers': blockers})
            return True
        if backend.order() != (state['order'], state['policy_hash']):
            raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
        now = time.time()
        recovery = normalized(settings)
        age = max(30, min(900, int(settings.get('interval', 10)) * 3))
        failed = streak(status.get('samples', []), selection['source']['id'], recovery['failures'], now, age, False, selection['source'])
        healthy = streak(status.get('samples', []), selection['target']['id'], recovery['successes'], now, age, True, selection['target'])
        diagnosis = diagnose(status, selection['source']['id'], now)
        ledger = read_json(PERSIST / 'pair-auto-budget.json', {'events': []})
        events, permitted = budget(ledger.get('events'), now, recovery['attempt_window']*60, recovery['attempt_limit'])
        dwell = not events or now - events[-1] >= max(recovery['cooldown'], recovery['min_dwell'])
        order = selection.get('order') or []
        reserve_first = (selection.get('direction', 'first') == 'first' and selection.get('source_rule') in order
                         and selection.get('target_rule') in order
                         and order.index(selection['target_rule']) < order.index(selection['source_rule']))
        if failed and healthy and reserve_first:
            # The router already sends traffic through the reserve first (its VPN priority list was
            # changed outside the app): there is nothing to switch, and Auto keeps watching.
            n.publish({'state': 'OBSERVING', 'mode': 'continuous-pair', 'readiness_verified': True,
                       'certified': False, 'proof_scope': MODE, 'external_lan_verified': False,
                       'source': selection['source']['id'], 'target': selection['target']['id'],
                       'reason': 'RESERVE-ALREADY-FIRST', 'blockers': []})
            return True
        if failed and healthy and permitted and dwell and not diagnosis.get('suppress_switch'):
            if state.get('manual_hold'):
                state.pop('manual_hold',None);save(state)
            atomic_json(PERSIST / 'pair-auto-budget.json', {'events': events + [now]})
            until = configure_lease(state)
            blockers, selection = backend.diagnostic()
            if blockers:
                raise ValueError('PAIR-READINESS-CHANGED')
            n.attempt(backend, selection, until, False,
                      probe_evidence={'source_streak_met': True, 'reserve_streak_met': True,
                                      'required_failures': recovery['failures'], 'required_successes': recovery['successes']},
                      control_revision=revision)
        else:
            n.publish({'state': 'OBSERVING', 'mode': 'continuous-pair', 'readiness_verified': True,
                       'certified': False, 'proof_scope': MODE, 'external_lan_verified': False,
                       'source': selection['source']['id'], 'target': selection['target']['id'],
                       'vendor_identity':selection.get('vendor_identity'),
                       'source_failures': failed, 'reserve_healthy': healthy,
                       'reason': 'PAIR-RATE-LIMIT' if not permitted else diagnosis.get('code') if diagnosis.get('suppress_switch') else 'PAIR-MANUAL-HOLD-PRIMARY' if state.get('manual_hold')=='source' else 'PAIR-WATCHING',
                       'blockers': []})
    except (n.Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        try:pending = read_state()
        except (OSError, ValueError, KeyError, TypeError):pending = {}
        if pending.get('phase') == 'RUNNING' and str(error) in READOPT_CODES and request_row.get('mode') == 'on':
            try:
                if readopt_running(pending, request_row, revision, str(error)):
                    return True
            except (n.Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                pass  # Falls back to the ordinary held state below.
        if pending.get('phase') == 'STARTING':
            try:
                cleanup(backend, pending)
                pending=read_state()
            except (n.Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                pending['phase'] = 'HELD'
                save(pending)
        # A failed Start before durable acquisition has no STARTING state to
        # finish. Consume its exact request; a newer Stop/Start cannot be lost.
        if pending.get('phase') in (None,'STOPPED','FAILED','HELD') and request_row.get('mode')=='on':
            fail_request(request_row,revision,error)
        # Leave unverified ownership intact. Stop is independent of this code.
        publish_failure(error)
    return True
