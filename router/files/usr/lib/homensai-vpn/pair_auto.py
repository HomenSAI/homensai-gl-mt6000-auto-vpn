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
from pathlib import Path
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
    if (not isinstance(data, dict) or envelope.get('sha256') != checksum(data)
            or data.get('phase') not in {'STARTING', 'RUNNING', 'STOPPING', 'HELD', 'STOPPED', 'FAILED'}
            or not isinstance(data.get('id'), str) or not __import__('re').fullmatch('[a-f0-9]{32}', data['id'])
            or not isinstance(data.get('owned'), list) or any(not isinstance(x,str) for x in data['owned'])
            or len(data['owned']) != len(set(data['owned']))
            or any(x not in INTERFACES for x in data['owned'])
            or not isinstance(data.get('before_flags'), dict) or set(data['before_flags']) != set(INTERFACES)
            or any(x not in ('0', '1') for x in data['before_flags'].values())
            or not isinstance(data.get('network_identity'), str) or not __import__('re').fullmatch('[a-f0-9]{64}', data['network_identity'])):
        raise ValueError('PAIR-STATE-UNVERIFIED')
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


def request(revision):
    from auto_control import control_lock, revision_locked
    from agent import RUNTIME, atomic_json
    with control_lock():
        if revision != revision_locked(RUNTIME):
            return {'accepted': False, 'blockers': ['CONTROL-REVISION-STALE']}
        try:
            state = read_state()
            old = intent()
        except (OSError, ValueError):
            return {'accepted': False, 'blockers': ['PAIR-STATE-UNVERIFIED']}
        if state and state.get('phase') not in TERMINAL and not (
                old.get('mode')=='on' and old.get('revision')==revision and old.get('id')==state.get('id')):
            return {'accepted': False, 'blockers': ['PAIR-RECOVERY-REQUIRED']}
        if old.get('mode') == 'on' and old.get('revision') == revision:
            return {'accepted': True, 'queued': True, 'already_requested': True}
        atomic_json(paths()[0], {'mode': 'on', 'revision': revision, 'time': time.time(), 'id': uuid.uuid4().hex})
    return {'accepted': True, 'queued': True, 'mode': 'continuous-pair', 'proof_scope': MODE,
            'external_lan_verified': False}


def stop_locked(revision):
    from agent import atomic_json
    atomic_json(paths()[0], {'mode': 'off', 'revision': revision, 'time': time.time()})


def public_intent():
    try:
        row = intent()
    except (OSError, ValueError):
        return None
    return row if row.get('mode') == 'on' else None


def budget(events, now, window=900, limit=3):
    """Three attempts per rolling 15 min; a new Start never resets this ledger."""
    if (not isinstance(events, list) or len(events) > 16 or type(now) not in (int, float)
            or not math.isfinite(now) or any(type(x) not in (int, float) or not math.isfinite(x)
                                           or x < 0 or x > now for x in events)):
        raise ValueError('PAIR-BUDGET-UNVERIFIED')
    kept = sorted(x for x in events if now - x < window)
    return kept, len(kept) < limit


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
assert(q.interface=='wgclient1'or q.interface=='ovpnclient1','interface')
assert(q.value=='0'or q.value=='1','value')
assert(c:set('network',q.interface,'disabled',q.value));assert(c:save('network'));assert(c:commit('network'))
"""


def network():
    from native_switch import command
    data = json.loads(command(['lua', '-e', NETWORK_READ]))
    if not isinstance(data, list) or not 1 <= len(data) <= 400:
        raise ValueError('PAIR-NETWORK-UNVERIFIED')
    return data


def normalized_network(data):
    from agent import checksum
    rows = copy.deepcopy(data)
    for row in rows:
        if row.get('.name') in INTERFACES:
            row.pop('disabled', None)
    return checksum(rows)


def configs():
    result = {}
    for name in ('wireguard', 'ovpnclient', 'firewall', 'route_policy', 'wireless', 'dhcp', 'gl-dns-v2'):
        p = Path('/etc/config') / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 1048576:
            raise ValueError('PAIR-CONFIG-UNVERIFIED')
        result[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def set_disabled(state, interface, value, revision=None):
    from agent import RUNTIME
    import native_switch as n
    data = network()
    if normalized_network(data) != state['network_identity']:
        raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
    # RTP legitimately derives gl_process_vpn; the native semantic policy hash
    # separately binds that rule. Never accept edits to profile credentials.
    observed_configs = configs()
    for name, sha in state['protected'].items():
        if name == 'route_policy':
            continue
        if observed_configs[name] != sha:
            raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
    with tempfile.TemporaryDirectory(prefix='pair-uci-', dir=str(RUNTIME)) as stage:
        payload = json.dumps({'stage': stage, 'expected': data, 'interface': interface, 'value': value}).encode()
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
    if normalized_network(after) != state['network_identity'] or row.get('disabled') != value:
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
    if Path('/etc/glversion').read_text().strip() != '4.11.0' or snapshot()['state'] != 'pass':
        raise ValueError('PAIR-PREPARATION-REQUIRED')
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
    if {selection[k]['interface'] for k in ('source', 'target')} != set(INTERFACES):
        raise ValueError('PAIR-PROFILES-UNVERIFIED')
    backend.use_process_bindings(selection['process_bindings'])
    return selection


def begin(backend, settings, request):
    import native_switch as n
    selection = preflight(backend, settings)
    data = network()
    selected = {row['.name']: row for row in data if row.get('.name') in INTERFACES}
    if set(selected) != set(INTERFACES) or any(
            row.get('proto') != INTERFACES[name] or row.get('auto') != '0' or row.get('disabled') not in ('0', '1')
            for name, row in selected.items()):
        raise ValueError('PAIR-PROFILES-UNVERIFIED')
    state = dict(id=request['id'], phase='STARTING', started=time.time(), revision=request['revision'],
                 network_identity=normalized_network(data), protected=configs(), owned=[],
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
    state['phase'] = 'RUNNING'
    require_running(request['revision'])
    backend.guard(backend.devices(), control_revision=request['revision'])
    save(state)
    return state


def cleanup(backend, state):
    import native_switch as n
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
        if normalized_network(network()) != state['network_identity']:
            raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        observed_configs = configs()
        for name, sha in state['protected'].items():
            if name != 'route_policy' and observed_configs[name] != sha:
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
    state = read_state()
    if state and state['phase'] not in TERMINAL:
        cleanup(backend, state)
    from auto_control import control_lock, revision_locked
    from agent import RUNTIME
    if paths()[0].exists():
        with control_lock():
            stop_locked(revision_locked(RUNTIME))


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
    state = read_state()
    request_row = intent()
    running = request_row.get('mode') == 'on' and request_row.get('revision') == revision
    relevant = running or state and state['phase'] not in TERMINAL
    if not relevant:
        return False
    try:
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
        if normalized_network(network())!=state['network_identity']:
            raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        current_configs=configs()
        if any(current_configs.get(name)!=sha for name,sha in state['protected'].items()if name!='route_policy'):
            raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
        journal = n.journal_read()
        status = read_json(RUNTIME / 'status.json', {})
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
            preparing=(0<=time.time()-state['started']<=180 and all(x in('VENDOR-SETTLING','OBSERVATION-STALE','PROFILE-IDENTITY-CHANGED')for x in blockers))
            n.publish({'state': 'ARMED'if preparing else'BLOCKED', 'mode': 'continuous-pair', 'proof_scope': MODE,
                       'reason':'PAIR-WAITING-PROBES'if preparing else None,'blockers': blockers})
            return True
        if backend.order() != (state['order'], state['policy_hash']):
            raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
        now = time.time()
        recovery = normalized(settings)
        age = max(30, min(900, int(settings.get('interval', 30)) * 3))
        failed = streak(status.get('samples', []), selection['source']['id'], recovery['failures'], now, age, False, selection['source'])
        healthy = streak(status.get('samples', []), selection['target']['id'], recovery['successes'], now, age, True, selection['target'])
        diagnosis = diagnose(status, selection['source']['id'], now)
        ledger = read_json(PERSIST / 'pair-auto-budget.json', {'events': []})
        events, permitted = budget(ledger.get('events'), now)
        dwell = not events or now - events[-1] >= max(recovery['cooldown'], recovery['min_dwell'])
        if failed and healthy and permitted and dwell and not diagnosis.get('suppress_switch'):
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
                       'reason': 'PAIR-RATE-LIMIT' if not permitted else diagnosis.get('code') if diagnosis.get('suppress_switch') else 'PAIR-WATCHING',
                       'blockers': []})
    except (n.Refused, OSError, ValueError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, (n.Refused, ValueError)) and n.re.fullmatch('[A-Z][A-Z0-9_-]{0,95}', str(error)) else 'PAIR-SYSTEM-001'
        pending = read_state()
        if pending.get('phase') == 'STARTING':
            try:
                cleanup(backend, pending)
                from auto_control import control_lock
                with control_lock():
                    stop_locked(revision)
            except (OSError, ValueError, subprocess.SubprocessError):
                pending['phase'] = 'HELD'
                save(pending)
        # Leave unverified ownership intact. Stop is independent of this code.
        n.publish({'state': 'BLOCKED', 'mode': 'continuous-pair', 'proof_scope': MODE, 'blockers': [code]})
    return True
