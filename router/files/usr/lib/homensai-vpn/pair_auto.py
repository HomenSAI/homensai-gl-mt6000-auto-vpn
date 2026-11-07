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
import threading
import time
import uuid

MODE = 'router-probed-ipv4'
TRANSIENT_START = ('VENDOR-WORKER-BUSY', 'VENDOR-SETTLING', 'OBSERVATION-STALE')  # retried, not terminal
TRANSIENT_START_SECONDS = 90
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
    if 'protected_static' in data and (not isinstance(data['protected_static'],dict) or set(data['protected_static'])!={'firewall'}
            or not isinstance(data['protected_static']['firewall'],str) or not re.fullmatch('[a-f0-9]{64}',data['protected_static']['firewall'])):
        raise ValueError('PAIR-STATE-UNVERIFIED')
    if any(key in data for key in ('kept','kept_flags','kept_at','kept_tx')):
        # the boot handover (boot_keep): only on a STOPPED session, owned clients with their flags before the session;
        # kept_tx: kept for the restart Start after this supervisor's forward resume of that transaction (no boot)
        kept,flags,at=data.get('kept'),data.get('kept_flags'),data.get('kept_at')
        tx=data.get('kept_tx')
        if (data['phase']!='STOPPED' or not isinstance(kept,list) or not kept or len(kept)!=len(set(map(str,kept)))
                or ('kept_tx' in data and (not isinstance(tx,str) or not re.fullmatch('[a-f0-9]{32}',tx)))
                or any(not isinstance(x,str) or x not in managed for x in kept) or not isinstance(flags,dict)
                or set(flags)!=set(kept) or any(v not in ('0','1') for v in flags.values())
                or type(at) not in (int,float) or not math.isfinite(at) or at<0):
            raise ValueError('PAIR-STATE-UNVERIFIED')
    if 'handover' in data:
        # the boot handover on the reserve (boot_handover): only on a STOPPED session, its own order and policy
        h=data['handover']
        if (data['phase']!='STOPPED' or not isinstance(h,dict) or set(h)!={'tx','order','policy_hash','at'}
                or not isinstance(h['tx'],str) or not re.fullmatch('[a-f0-9]{32}',h['tx']) or h['policy_hash']!=data.get('policy_hash')
                or not isinstance(h['order'],list) or h['order']!=data.get('order')
                or type(h['at']) not in (int,float) or not math.isfinite(h['at']) or h['at']<0):
            raise ValueError('PAIR-STATE-UNVERIFIED')
    if 'manual_hold' in data and data['manual_hold'] not in ('source','target'):raise ValueError('PAIR-MANUAL-HOLD-UNVERIFIED')
    if 'manual_hold_source' in data and data['manual_hold_source'] not in ('manual','test','programmatic','unknown'):raise ValueError('PAIR-MANUAL-HOLD-UNVERIFIED')
    if 'policy_roles' in data:
        from pair_policy import validate
        try:validate(data['policy_roles'],data.get('order'))
        except (ValueError,TypeError):raise ValueError('PAIR-STATE-UNVERIFIED') from None
    if 'selected_policy' in data:
        selected=data['selected_policy']
        from pair_policy import role
        if (not isinstance(selected,dict) or set(selected)!={'role','order','hash','since'}
                or selected.get('hash')!=data.get('policy_hash') or selected.get('role') not in ('source','target')
                or type(selected.get('since')) not in (int,float) or not math.isfinite(selected['since']) or selected['since']<=0
                or role(data.get('policy_roles'),selected.get('order'))!=selected['role']):raise ValueError('PAIR-STATE-UNVERIFIED')
    if 'manual_selection' in data:
        from failure_diagnosis import profile_identity
        selected=data['manual_selection']
        if (not isinstance(selected,dict) or set(selected)!={'request_id','role','order','hash','vendor_identity','profiles'}
                or not isinstance(selected.get('request_id'),str) or not re.fullmatch('[a-f0-9]{32}',selected['request_id'])
                or selected.get('role') not in ('source','target') or selected['role']!=data.get('manual_hold')
                or not isinstance(selected.get('order'),list) or selected['hash']!=data.get('policy_hash')
                or len(selected['order'])!=len(data.get('order',[])) or set(selected['order'])!=set(data['order'])
                or not isinstance(selected.get('vendor_identity'),str) or not re.fullmatch('[a-f0-9]{64}',selected['vendor_identity'])
                or not isinstance(selected.get('profiles'),dict) or set(selected['profiles'])!={'source','target'}
                or any(not isinstance(selected['profiles'][key],dict) or profile_identity(selected['profiles'][key])!=selected['profiles'][key]
                       for key in ('source','target'))):
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


# Settings changed outside the app (a tunnel renamed or reordered, a stock client tidied) must not leave Auto
# off for good. The saved session is handed over to the current configuration automatically: its original record
# is archived first, interface flags are never restored over the new configuration, and a fresh Start re-reads
# everything. Bounded so that a persistent conflict still ends in a visible refusal.
READOPT_CODES = ('PAIR-EXTERNAL-NETWORK-CHANGE', 'PAIR-EXTERNAL-CONFIG-CHANGE', 'PAIR-EXTERNAL-POLICY-CHANGE',
                 'SOURCE-ORDER-MISMATCH')
READOPT_LIMIT = 3

# Owner decision 07.11.2026 ('by risk + notification', review F-32 / A9 finding 2): a RUNNING session that meets a
# change made outside the app adopts the current configuration by itself only when the change is proven to touch
# nothing but these packages (Wi-Fi, DHCP, the GL DNS page) or the network interface/address class of
# PAIR-EXTERNAL-NETWORK-CHANGE (normalized_network without the pair's interfaces; unchanged, not widened). A change of
# the VPN profiles (wireguard, ovpnclient: keys, endpoints), of the firewall, of the pair's route_policy rules
# (PAIR-EXTERNAL-POLICY-CHANGE, SOURCE-ORDER-MISMATCH), of any other package, or one whose class cannot be read
# (unreadable digest, nothing found changed) is HELD: PAIR-OUTSIDE-CHANGE-HELD, the K9 guard stays, and only the
# owner's Start (release_for_start / request -> release_session) or Stop ends it. Every decision is told: a history
# event and the status field outside_change with the class and the package names (never a value or a key), one log
# line. Lua: pair.readopt_class / pair.changed_packages.
ADOPT_PACKAGES = ('wireless', 'dhcp', 'gl-dns-v2')
ADOPT_CODE = 'PAIR-OUTSIDE-CHANGE-ADOPTED'
HOLD_CODE = 'PAIR-OUTSIDE-CHANGE-HELD'


def changed_packages(state, observed):
    """Names of the protected packages whose digest differs (same rule as changed(), one package at a time)."""
    names = sorted(name for name in state['protected'] if name != 'route_policy')
    return [name for name in names if changed(state, observed, skip=tuple(x for x in names if x != name))]


def readopt_class(state, code, now=None):
    """-> {'decision': 'ADOPT'|'HOLD', 'trigger': code, 'packages': [...], 'why': ..., 'time': now}. Never raises."""
    from pair_interfaces import state as state_interfaces
    row = {'decision': 'HOLD', 'trigger': code, 'packages': [], 'why': 'UNCLASSIFIED', 'time': time.time() if now is None else now}
    if code not in ('PAIR-EXTERNAL-NETWORK-CHANGE', 'PAIR-EXTERNAL-CONFIG-CHANGE'):
        row.update(packages=['route_policy'], why='POLICY-OR-ORDER')  # the pair's own rules or their order: the owner decides
        return row
    try:
        packages = changed_packages(state, configs(state_interfaces(state)))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        row['why'] = 'UNREADABLE'
        return row
    if code == 'PAIR-EXTERNAL-NETWORK-CHANGE':
        packages = ['network'] + packages
    row['packages'] = packages
    if not packages:
        return row  # the trigger said changed and nothing is found changed: not proven, HOLD
    foreign = [name for name in packages if name not in ADOPT_PACKAGES and name != 'network']
    if foreign:
        row['why'] = 'FOREIGN-PACKAGES'
        return row
    row.update(decision='ADOPT', why='ADOPT-PACKAGES-ONLY')
    return row


def outside_change_log(verdict, adopted_by=None):
    try:
        _log('%s: %s by %s, packages %s (%s)' % (ADOPT_CODE if verdict['decision'] == 'ADOPT' else HOLD_CODE, verdict['trigger'],
                                                 adopted_by or 'automatic', ' '.join(verdict['packages']) or '-', verdict['why']))
    except (KeyError, TypeError):
        pass


def outside_notice(verdict):
    """Owner decision 07.11.2026: the decision goes to the Telegram sender's RAM ring (telegram_state.outside_record), told
    on its next round. One local write, never the network, never raises. Lua: pair.lua's outside_notice."""
    try:
        from telegram_state import outside_record
        outside_record(verdict)
    except Exception:  # noqa: BLE001 -- a notice must never stop Auto
        pass


def readopt_allowed(now):
    from agent import RUNTIME, read_json
    try:
        ledger = read_json(RUNTIME / 'pair-readopt.json', {})
    except (OSError, ValueError):
        ledger = {}
    events = ledger.get('events', []) if isinstance(ledger, dict) else []
    events = [x for x in events if type(x) in (int, float) and math.isfinite(x) and 0 <= now - x < 900] if isinstance(events, list) else []
    return events, len(events) < READOPT_LIMIT


def release_session(state, code, verdict=None, adopted_by='owner-start'):
    """verdict: readopt_class row of the automatic adoption; None for the owner's Start (recorded as such).
    adopted_by='owner-stop' (end_hold_on_stop): the owner's Stop ends the hold - no adoption, outside the readopt budget."""
    import native_switch as n
    from agent import PERSIST, RUNTIME, atomic_json
    now = time.time()
    stop = adopted_by == 'owner-stop'
    if verdict is None:
        verdict = {'decision': 'STOP' if stop else 'ADOPT', 'trigger': code, 'packages': [],
                   'why': 'OWNER-STOP' if stop else 'OWNER-START', 'time': now}
        if isinstance(state.get('outside_change'), dict) and isinstance(state['outside_change'].get('packages'), list):
            verdict['packages'] = list(state['outside_change']['packages'])  # the hold's classification, no values
    events, allowed = readopt_allowed(now)
    if (not allowed and not stop) or n.journal_read().get('phase') not in (None, 'ROLLED-BACK'):
        return False
    path = paths()[1]
    raw = path.read_bytes()
    directory = PERSIST / 'session-recovery'
    if directory.is_symlink():
        raise ValueError('PAIR-STATE-UNVERIFIED')
    directory.mkdir(mode=0o700, exist_ok=True)
    archive = directory / ('pair-' + state['id'] + ('-stop-' if stop else '-readopt-') + str(int(now)) + '.json')
    fd = os.open(str(archive), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if archive.read_bytes() != raw:
        raise ValueError('PAIR-STATE-UNVERIFIED')
    # Review F-37 (06.11.2026): the archive's directory entry is on flash before the ownership is retired below (the
    # Lua line's write_atomic does the same); a power cut can then never keep the retirement and lose the archive.
    handle = os.open(str(directory), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(handle)
    finally:
        os.close(handle)
    resolved = copy.deepcopy(state)
    resolved.update(phase='STOPPED', owned=[], original_restored=False, recovery_error=None,
                    operator_resolution={'reason': 'AUTOMATIC-EXTERNAL-CHANGE-READOPT', 'time': now, 'archive': archive.name,
                                         'trigger': code, 'original_sha256': hashlib.sha256(raw).hexdigest(),
                                         'retired_owned': state.get('owned', []), 'old_flags_restored': False,
                                         'adopted_by': adopted_by, 'outside_change': verdict})
    resolved.pop('outside_change', None)
    save(resolved)
    if not stop:  # the owner's Stop adopts nothing: it never spends (nor is refused by) the 3/900 s adoption budget
        atomic_json(RUNTIME / 'pair-readopt.json', {'events': events + [now]})
    outside_change_log(verdict, adopted_by)
    if adopted_by in ('owner-stop', 'owner-start'):  # owner decision 07.11.2026: the hold the owner ended is told (class RELEASE)
        outside_notice({'decision': 'RELEASE', 'release': 'STOP' if stop else 'START', 'trigger': code, 'why': verdict.get('why'),
                        'packages': verdict.get('packages', []), 'time': now})
    return True


def end_hold_on_stop(state):
    """Owner rule 07.11.2026 (T4-A, router/tests/T4A-NOTE.md): a session HELD by an outside change stays held until the
    owner presses Stop and then Start; the Stop itself ends STOPPED. Before, the Stop only released the K9 guard
    (outside_hold) and the record stayed HELD with its readopt code - since F-32 holds a foreign route_policy change
    instead of adopting it, every Stop after such a change ended HELD. The record is retired exactly as the owner's
    Start retires it (release_session: archived, owned=[] - a profile is never stopped after an outside change), under
    the control lock, only while Auto is off and this session's Stop latch stands, with a settled journal. Lua:
    pair.end_hold_on_stop."""
    from auto_control import control_lock
    with control_lock():
        try:
            current = read_state()
        except (OSError, ValueError, KeyError, TypeError):
            return False
        if (not current or current.get('id') != state.get('id') or current.get('phase') != 'HELD'
                or current.get('recovery_error') not in READOPT_CODES or intent().get('mode') == 'on'
                or not owner_stopped(current)):
            return False
        return release_session(current, current['recovery_error'], adopted_by='owner-stop')


def readopt_running(state, request_row, revision, code):
    """A running session met a change made outside the app: adopt the new configuration and start again by itself."""
    import native_switch as n
    from auto_control import control_lock, revision_locked
    from agent import RUNTIME, atomic_json
    verdict = readopt_class(state, code)
    if verdict['decision'] != 'ADOPT':
        # HOLD (owner decision 07.11.2026): the record says why under the control lock; publish_failure then writes the
        # same HELD code (no second write) and carries the class into the status. Start or Stop are the only ways out.
        with control_lock():
            try:
                pending = read_state()
            except (OSError, ValueError, KeyError, TypeError):
                pending = None
            if pending and pending.get('id') == state.get('id') and pending.get('phase') not in TERMINAL:
                pending.update(phase='HELD', recovery_error=code, outside_change=verdict)
                save(pending)
        outside_change_log(verdict)
        outside_notice(verdict)
        return False
    with control_lock():
        current = intent()
        if (revision_locked(RUNTIME) != revision or current.get('revision') != revision or current.get('mode') != 'on'
                or current.get('id') != request_row.get('id') or not release_session(state, code, verdict, 'automatic')):
            return False
        atomic_json(paths()[0], {'mode': 'on', 'revision': revision, 'time': time.time(), 'id': uuid.uuid4().hex,
                                 'request_source': current.get('request_source', 'unknown')})
    outside_notice(verdict)  # the ARMED status lasts seconds: the Telegram ring keeps the ADOPT for the next round
    n.publish({'state': 'ARMED', 'mode': 'continuous-pair', 'proof_scope': MODE, 'reason': 'PAIR-READOPTED', 'blockers': [],
               'outside_change': verdict})
    return True


def release_for_start(revision, settings, arrived):
    """The owner's Start on a session HELD only by a change made outside the app (03.11.2026, MT3000 alpha6).

    Preparation refuses any write while a session is HELD (preparation_control.guard), and the hand-over in
    request() is reached only after every preparation check passes - with a new GL client (auto unset) and the
    stock boot link back, Start refused PREPARATION-RECOVERY-REQUIRED for good. Here the same release_session
    runs first, under the control lock: the old record is archived, its interfaces are retired (flags are not
    restored over the new configuration), the journal must be absent or ROLLED-BACK and the readopt ledger
    must allow it. Nothing is started; preparation and request() follow with every check of a first Start.
    Returns None (nothing to hand over, or handed over) or a refusal code.
    """
    import native_switch as n
    from agent import PERSIST, RUNTIME, read_json, TERMS_VERSION
    from auto_control import control_lock, revision_locked
    if not isinstance(settings, dict) or settings.get('pair_auto_mode') != MODE or settings.get('terms_version') != TERMS_VERSION:
        return None
    with control_lock():
        # Stop rotates the revision under this lock: a Stop received since the Start arrived wins.
        if revision != revision_locked(RUNTIME):
            return 'CONTROL-REVISION-STALE'
        try:
            state = read_state()
            old = intent()
            stopped = read_json(PERSIST / 'native-stop.json', {})
        except (OSError, ValueError):
            return None  # the ordinary checks name it
        if not state or state.get('phase') != 'HELD' or state.get('recovery_error') not in READOPT_CODES:
            return None
        if old.get('mode') == 'on':
            return None
        epoch = stopped.get('requested') if isinstance(stopped, dict) else None
        if not isinstance(stopped, dict) or stopped.get('control_revision_failed') is True:
            return 'CONTROL-REVISION-STALE'
        if type(epoch) in (int, float) and math.isfinite(epoch) and epoch >= arrived:
            return 'STOP-SUPERSEDED-START'
        try:
            handed = release_session(state, state['recovery_error'])
        except (OSError, ValueError, KeyError, TypeError, n.Refused):
            handed = False
    return None if handed else 'PAIR-RECOVERY-REQUIRED'


def request(revision,request_source=None):
    from auto_control import control_lock, revision_locked, maintenance_blocker
    from agent import RUNTIME, atomic_json
    with control_lock():
        # Plan item 54 (F-16): the package hooks mark their operation under this lock before they assess
        maintenance=maintenance_blocker()
        if maintenance:return {'accepted':False,'blockers':[maintenance]}
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
        # Owner decision 31.10.2026: the owner's own Start is remembered on flash, so Auto comes back after a power cut.
        # Under the control lock with its intent, as control_request.lua (trace conformance 04.11.2026): a marker written
        # after the lock could land behind a Stop that came in between and outlive it.
        if source_label(request_source)=='manual':
            try:
                from boot_resume import remember
                remember()
            except (OSError,ValueError):pass
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


# The ledger keeps failovers longer than the rate limit looks back: the flap damping remembers them (return_hold, option
# recovery_flap_window up to 120 min, the half-life penalty several half-lives). LEDGER_SIZE bounds the file: failovers
# older than the 15 minutes of the rate limit give way first, and return_hold never needs more (limit 10 + 5 doublings).
RATE_MEMORY = 900
LEDGER_MEMORY = 14400
LEDGER_SIZE = 15


def budget(events, now, window=900, limit=3):
    """Configurable rolling limit over at most RATE_MEMORY s; the ledger lives longer, and never resets on Start."""
    if (not isinstance(events, list) or len(events) > 16 or type(now) not in (int, float)
            or not math.isfinite(now) or any(type(x) not in (int, float) or not math.isfinite(x)
                                           or x < 0 for x in events)):
        raise ValueError('PAIR-BUDGET-UNVERIFIED')
    events = [min(x, now) for x in events]
    if type(window)is not int or not 60<=window<=900 or type(limit)is not int or not 1<=limit<=10:
        raise ValueError('PAIR-BUDGET-UNVERIFIED')
    # Keep the whole maximum window so later policy changes cannot erase attempts.
    recent = sorted(x for x in events if now - x < RATE_MEMORY)
    count=sum(now-x<window for x in recent)
    older = sorted(x for x in events if RATE_MEMORY <= now - x < LEDGER_MEMORY)
    room = max(0, LEDGER_SIZE-len(recent))
    return (older[-room:] if room else [])+recent, count < limit and len(recent)<16


# BH3-03 (bug hunt 07.11.2026): the ledger stamps are wall time and budget() clamps a stamp in the future to "now", so after
# a backward clock step (sysfixtime on the RTC-less MT3000/MT6000 starts from the newest mtime under /etc, a bad NTP
# answer) the cooldown spacing never elapsed until the wall clock caught up: every failover from a dead primary was
# refused with PAIR-RATE-LIMIT for the size of the step. Ages are now measured on the monotonic clock inside one boot: each
# charge also notes its /proc/uptime second and boot_id in RAM (CLOCK_NAME, gone after a reboot). A stamp noted in this
# boot is at least uptime-now minus uptime-then old; a stamp more than CLOCK_SKEW s in the future without a note (another
# boot, or a ledger written before this change) has an unknown age and counts as old as the current uptime - at most one
# cooldown from now (a stamp of an earlier boot is at least that old anyway). The wall age still wins when it is larger,
# so nothing waits longer than before. charge_clock gives the stamps budget() then sees; the ledger file keeps its format.
# Lua twin: pair.charge_clock / pair.effective_events / pair.clock_note (tests/budget_clock_cases.json).
CLOCK_SKEW = 120
CLOCK_NAME = 'pair-budget-clock.json'
BOOT_ID = '/proc/sys/kernel/random/boot_id'
UPTIME = '/proc/uptime'


def boot_clock():
    """(uptime seconds, boot_id) of this boot; (None, None) when /proc cannot be read. The clock of the Lua twin
    (runner.clock: /proc/uptime, CLOCK_BOOTTIME)."""
    try:
        with open(UPTIME, encoding='ascii') as f:up = float(f.read().split()[0])
        with open(BOOT_ID, encoding='ascii') as f:boot = f.read().strip()
    except (OSError, ValueError, IndexError, UnicodeDecodeError):return None, None
    if not math.isfinite(up) or up < 0 or not re.fullmatch(r'[0-9a-f-]{8,64}', boot):return None, None
    return up, boot


def charge_clock(events, record, now, uptime, boot):
    """The ledger stamps as budget() should see them: a stamp whose monotonic age (record of this boot) or unknown age
    (in the future by more than CLOCK_SKEW, no record: the current uptime) is larger than its wall age becomes now - age.
    Anything that is not a valid stamp passes unchanged (budget() refuses it as before)."""
    if not isinstance(events, list):return events
    if type(uptime) not in (int, float) or not math.isfinite(uptime) or uptime < 0 or type(now) not in (int, float) or not math.isfinite(now):
        return list(events)
    noted = {}
    if (isinstance(record, dict) and isinstance(boot, str) and boot and record.get('boot') == boot
            and isinstance(record.get('at'), list)):
        for pair in record['at']:
            if (isinstance(pair, list) and len(pair) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in pair)
                    and pair[1] >= 0):
                noted[pair[0]] = pair[1]
    out = []
    for x in events:
        if type(x) not in (int, float) or not math.isfinite(x) or x < 0:
            out.append(x);continue
        age = now - x
        if x in noted:bound = uptime - noted[x] if uptime >= noted[x] else None
        elif age < -CLOCK_SKEW:bound = uptime
        else:bound = None
        out.append(now - bound if bound is not None and bound > age else x)
    return out


def effective_events(ledger, now):
    """charge_clock over the ledger's events with this boot's clock and the RAM notes."""
    from agent import RUNTIME, read_json
    events = ledger.get('events') if isinstance(ledger, dict) else None
    uptime, boot = boot_clock()
    if uptime is None:return events
    try:record = read_json(RUNTIME/CLOCK_NAME, {})
    except (OSError, ValueError, TypeError):record = {}
    return charge_clock(events, record, now, uptime, boot)


def clock_note(events, stamp):
    """Note the uptime second of the charge `stamp` (events: the ledger's events after it). Advisory RAM file: a failure
    only loses the monotonic age of this charge, never the charge itself."""
    from agent import RUNTIME, read_json, atomic_json
    uptime, boot = boot_clock()
    if uptime is None:return
    try:
        record = read_json(RUNTIME/CLOCK_NAME, {})
        at = record.get('at') if isinstance(record, dict) and record.get('boot') == boot else None
        kept = [p for p in at if isinstance(p, list) and len(p) == 2 and p[0] in events and p[0] != stamp] if isinstance(at, list) else []
        atomic_json(RUNTIME/CLOCK_NAME, {'boot': boot, 'at': (kept+[[stamp, uptime]])[-16:]})
    except (OSError, ValueError, TypeError):pass


# Flap damping (MT3000 flap test 02.11.2026, primary 60 s down / 120 s up): the rolling attempt limit used to
# block the FAILOVER, so after three switches traffic stayed on a dead primary while every recovery still
# returned after ~70 s. Like RFC 2439/7196 route-flap damping and BFD/VRRP hold-down, leaving a failed
# primary is never limited (only the cooldown spacing bounds retries of a failed attempt); the RETURN is
# damped instead. HOLD_CAP is the longest primary stability the settings allow (recovery_settings.RANGES).
HOLD_CAP = 600
PENALTY = 1000


def halflife_hold(events, now, recovery):
    """flap_model 'halflife' (RFC 2439 penalty, study wave 3): +PENALTY per failover, halved every flap_halflife s. A
    penalty above flap_suppress damps until it falls below flap_reuse: primary_stable + halflife*log2(penalty/reuse), at
    most HOLD_CAP. Replayed from the ledger on every call, so no new state: it survives restarts and a Lua/Python
    hand-over, and an aborted failover (refunded) never counted."""
    half=recovery['flap_halflife'];stable=recovery['primary_stable'];reuse=recovery['flap_reuse']
    penalty=0.0;last=None;suppressed=False
    for stamp in sorted(x for x in events if x<=now):
        penalty=penalty*0.5**((stamp-last)/half) if last is not None else 0.0
        if suppressed and penalty<reuse:suppressed=False
        penalty+=PENALTY;last=stamp
        if penalty>recovery['flap_suppress']:suppressed=True
    if last is None:return stable
    penalty*=0.5**((now-last)/half)
    if not suppressed or penalty<reuse:return stable
    return int(min(HOLD_CAP,max(stable,stable+half*math.log(penalty/reuse,2))))


def return_hold(events, now, recovery):
    """Seconds the primary must be stably healthy before Auto returns to it.

    flap_model 'double' (default): below flap_limit failovers within flap_window minutes it is primary_stable; the
    failover that reaches the limit, and every further one, doubles it (capped at HOLD_CAP); as failovers age out of the
    window the hold decays back. 'halflife': halflife_hold. Twin: pair.lua M.return_hold (tests/flap_damping_cases.json)."""
    if recovery['flap_model']=='halflife':return halflife_hold(events,now,recovery)
    window=recovery['flap_window']*60
    count=sum(1 for x in events if 0<=now-x<window)
    excess=count-recovery['flap_limit']+1
    if excess<=0:return recovery['primary_stable']
    return min(HOLD_CAP,recovery['primary_stable']*2**min(excess,6))


# Aborted failover retry (MT3000 59-cycle primary-drop soak 03-04.11.2026, 2.1.0-alpha7, cycle 28): the failover was
# dispatched (APPLYING, ledger charged), the apply step's first diagnostic saw VENDOR-WORKER-QUIET-UNVERIFIED and the
# transaction rolled back before any switch; the charge stayed, so the next failover waited the whole cooldown spacing
# (PAIR-RATE-LIMIT, ~60 s) while the primary was dead: traffic moved after 84 s instead of 20-35 s. A failover refused
# by a transient vendor state (ABORT_REFUND_CODES) whose journal is verifiably ROLLED-BACK and never COMMITTED is not a
# switch: its charge is refunded (neither the cooldown spacing nor the flap damping counts it) and the abort is kept
# under 'aborted'. While the primary stays failed the retry waits RETRY_BASE*2^(n-1) s after the n-th consecutive abort,
# capped at max(cooldown, min_dwell): 5, 10, 20, 40, 60 s - prompt, never hot. Every vendor gate stays as it was (the
# diagnostic before the decision, assert_selection, the apply step's diagnostic and wait_quiet): a busy vendor worker
# still refuses the switch itself. Lua twin: pair.lua M.retry_wait / M.refund_abort (tests/vendor_retry_cases.json).
ABORT_REFUND_CODES = frozenset({'VENDOR-WORKER-BUSY', 'VENDOR-SETTLING', 'VENDOR-WORKER-QUIET-UNVERIFIED'})
RETRY_BASE = 5
ABORT_KEEP = 16


def abort_stamps(raw, now):
    """The ledger's 'aborted' stamps inside the 900 s ledger window, oldest first, at most ABORT_KEEP. Lenient: a
    damaged entry is dropped (the next refund writes a clean list); a missing key is no abort."""
    if not isinstance(raw, list):return []
    # BH3-03: an abort stamp more than CLOCK_SKEW s in the future predates a backward clock step; clamped to now it would
    # restart the retry backoff on every call until the clock caught up. It is dropped (its backoff is at most 60 s).
    kept = sorted(min(x, now) for x in raw if type(x) in (int, float) and math.isfinite(x) and x >= 0 and now - x < 900 and x - now <= CLOCK_SKEW)
    return kept[-ABORT_KEEP:]


def retry_wait(aborted, events, now, recovery):
    """Seconds before a failover aborted by the vendor may be dispatched again (0: now). Only the aborts after the last
    charged switch count (a completed switch ends the series)."""
    last = max(events) if events else None
    recent = [x for x in abort_stamps(aborted, now) if last is None or x > last]
    if not recent:return 0
    wait = min(max(recovery['cooldown'], recovery['min_dwell']), RETRY_BASE*2**min(len(recent)-1, 8))
    return max(0, recent[-1]+wait-now)


def refund_abort(stamp, code):
    """The failover charged at `stamp` was refused by `code` and rolled back before COMMITTED: drop its charge and
    remember the abort. Anything unproven (other code, journal not ROLLED-BACK by this very failure, charge not found)
    keeps the charge: the cooldown spacing then applies as before. True when refunded.
    Review 04.11.2026 (finding 6): the same VENDOR-* codes also come AFTER the switch itself (the verify wait after the
    rtp2 dispatch, wait_quiet after it): that rollback followed a real kernel switch, so the charge stays. Refunded only
    when the journal proves that nothing was written: rtp_dispatched and forward_policy_touched both exactly False."""
    from agent import PERSIST, read_json, atomic_json
    import native_switch as n
    if code not in ABORT_REFUND_CODES or type(stamp) not in (int, float):return False
    journal = n.journal_read()
    started = journal.get('started')
    if (journal.get('phase') != 'ROLLED-BACK' or journal.get('failure_code') != code or journal.get('confirmed') is not None
            or journal.get('pair_transition') is None or type(started) not in (int, float) or started > stamp
            or journal.get('rtp_dispatched') is not False or journal.get('forward_policy_touched') is not False):
        return False
    ledger = read_json(PERSIST/'pair-auto-budget.json', {'events': []})
    events = ledger.get('events') if isinstance(ledger, dict) else None
    if not isinstance(events, list) or stamp not in events:return False
    now = time.time()
    events = list(events);events.remove(stamp)
    row = {'events': events, 'aborted': (abort_stamps(ledger.get('aborted'), now)+[now])[-ABORT_KEEP:]}
    if ledger.get('others'):row['others'] = ledger['others']
    atomic_json(PERSIST/'pair-auto-budget.json', row)
    return True


# Late-switch recheck (MT3000 phase 2, 02.11.2026, 2.1.0-alpha5): a 15 s blackout of the primary was left at
# about 20 s, after the primary had already recovered at 15 s. The streak was met by three dense samples whose
# checks all ran inside the blackout (started at about 3.5/7.5/11.5 s, published about 2.5 s later), and the tick
# that read them needed a few more seconds (diagnostics, lease, kernel proof) before APPLYING; the monitor's first
# healthy sample (started at 15.5 s) arrived only while the switch was already running. Right before the failover
# commits the source is therefore looked at once more: a healthy source sample the monitor published after the
# decision's evidence, else one bounded live probe (RECHECK_SECONDS per check). Only positive health evidence
# aborts (a dead primary can never pass DNS + 2 of 3 HTTPS); a timeout, an error or an unavailable probe goes on
# with the switch exactly as before. Lua twin: pair.lua M.late_recheck (tests/late_switch_cases.json).
LATE_RECHECK_CODE = 'PRIMARY-RECOVERED-BEFORE-SWITCH'
RECHECK_SECONDS = 1
# L2 (FAST-SWITCH-2026-11-04.ru.md): the live probe of the recheck starts with the decision and runs beside the preparation
# (lease, readiness), its answer is taken right before the failover commits; the monitor's newest sample is still read
# last. Owner 05.11.2026: off until measured on a router (option parallel_recheck '1' turns it on, a saved value stays). Never
# skipped: without the parallel start (the default, no start) the old sequential probe runs.
RECHECK_WAIT = 6        # seconds at most the answer of a parallel probe is waited for; then the switch goes on, as on a timeout
# Failures the short live probe cannot see: VPN-MTU (mtu_check.py, large packets lost) passes DNS + HTTPS with small
# packets, and Auto's live probes never run the large-packet check. With such evidence only a newer healthy monitor
# sample (the monitor re-runs that check on every probe after a black hole) may stop the failover.
PROBE_BLIND_CODES = frozenset({'VPN-MTU'})
# source id -> the newest source sample stamp a recheck contradicted (memory only): the same evidence never
# starts a second decision; the monitor's next sample of the source decides again.
# ('beat', source id) -> the `since` of the run of lost heartbeats a recheck contradicted (review 04.11.2026, finding 3).
# The rule 'heartbeat' speaks on healthy monitor samples, so with ICMP filtered on the primary's targets the next sample
# was new evidence for a verdict the live probe had just refuted: a lease on flash and a probe every pass, ~8640 writes a
# day. The refutation holds for the whole run; a new run, or a failure the monitor itself sees (rule 'model'/'streak'),
# decides again.
LATE_ABORTS = {}


def good_point(point):
    return (point.get('code') is None and point.get('dns_ok') is True
            and type(point.get('https_success')) is int and point['https_success']>=2)


def newest_sample(samples, identifier, profile=None):
    """The newest sample of identifier inside its profile generation; None without one or when two samples of one
    stamp disagree (failure_diagnosis.scoped_samples)."""
    from failure_diagnosis import finite,scoped_samples
    if profile is not None:samples=scoped_samples(samples,profile)
    if not isinstance(samples,list):return None
    best=None;seen={}
    for point in samples:
        if not isinstance(point,dict) or point.get('id')!=identifier or not finite(point.get('time')):continue
        health=tuple(point.get(key) for key in ('code','dns_ok','https_success'));stamp=point['time']
        if stamp in seen and seen[stamp]!=health:return None
        seen[stamp]=health
        if best is None or stamp>best['time']:best=point
    return best


def monitor_recovered(samples, identifier, evidence, now, profile=None):
    """The monitor published a healthy sample of the source newer than the decision's evidence (not from the future)."""
    from failure_diagnosis import finite
    if not finite(evidence) or not finite(now):return False
    point=newest_sample(samples,identifier,profile)
    return point is not None and evidence<point['time']<=now and good_point(point)


def same_evidence(aborted, evidence):
    """A recheck already contradicted this very evidence (no newer source sample since)."""
    from failure_diagnosis import finite
    return finite(aborted) and finite(evidence) and evidence<=aborted


def recheck_begin(backend, selection, evidence_code, settings):
    """L2: start the live probe of late_recheck now, beside the preparation -> (thread, box), or None (not started:
    late_recheck then probes sequentially, or not at all for a PROBE_BLIND_CODES failure, as before)."""
    check=getattr(backend,'recheck',None)
    if settings.get('parallel_recheck') not in (True,'1') or check is None or evidence_code in PROBE_BLIND_CODES:return None
    box={}
    def run():
        try:box['healthy']=check(selection['source']['id'],RECHECK_SECONDS)
        except Exception:box['healthy']=None  # any failure of the last look goes on with the switch
    thread=threading.Thread(target=run,daemon=True)
    try:thread.start()
    except RuntimeError:return None
    return thread,box


def late_recheck(backend, selection, evidence, evidence_code=None, parallel=None):
    """The last look at the source before a failover commits: (code, how) or None. evidence_code: the code of the
    decision's newest source sample; a PROBE_BLIND_CODES failure is never contradicted by the live probe. parallel: the
    probe recheck_begin started; its answer takes the place of a new one."""
    from agent import RUNTIME, read_json
    identifier=selection['source']['id']
    try:status=read_json(RUNTIME/'status.json',{})
    except (OSError,ValueError,TypeError):status={}
    if isinstance(status,dict) and monitor_recovered(status.get('samples',[]),identifier,evidence,time.time(),selection['source']):
        return LATE_RECHECK_CODE,'monitor'
    if parallel is not None:
        parallel[0].join(RECHECK_WAIT)
        return (LATE_RECHECK_CODE,'probe') if parallel[1].get('healthy') is True else None
    check=None if evidence_code in PROBE_BLIND_CODES else getattr(backend,'recheck',None)
    if check is not None:
        try:healthy=check(identifier,RECHECK_SECONDS)
        except Exception:healthy=None  # any failure of the last look goes on with the switch
        if healthy is True:return LATE_RECHECK_CODE,'probe'
    return None


def heartbeat_row():
    """The monitor's row for channel_model.heartbeat_failed; anything unreadable is no evidence (Lua: read_json_safe)."""
    from agent import RUNTIME, read_json
    from channel_model import WAKE_NAME
    try:return read_json(RUNTIME/WAKE_NAME,{})
    except (OSError,ValueError,TypeError):return None


def decision_timing(decided, prepared, rechecked, rule, parallel):
    """The router measurement of FAST-SWITCH-2026-11-04.ru.md (how much of the preparation is removable): the stamps of
    the last decision in RAM. Measurement only, never fails."""
    from agent import RUNTIME, atomic_json
    try:atomic_json(RUNTIME/'pair-decision-timing.json',{'decided':decided,'prepared':prepared,'rechecked':rechecked,'rule':rule,'parallel':parallel})
    except (OSError,ValueError,TypeError):pass


def failover_events(events, ledger):
    """What flap damping counts (review 04.11.2026, finding 5). The ledger's events are every charge, the rate limit and the
    cooldown need them all; the return of the pair_return path, a kernel repair and a manual switch are charges too but no
    failovers, and the documented hold (240 s for two failovers in an hour) was reached by one failover and one of those.
    They are listed under 'others'. A ledger written before this key has none: every charge counts, as it did. Lua: same name."""
    others=ledger.get('others') if isinstance(ledger,dict) else None
    return [x for x in events if x not in others] if isinstance(others,list) else events


def ledger_charge(events, stamp, failover=False):
    """Write one charge: events are the budget()ed stamps before it. 'aborted' and 'others' stay with the file, so that no
    writer loses what another one recorded. Lua: pair.ledger_charge."""
    from agent import PERSIST,read_json,atomic_json
    try:ledger=read_json(PERSIST/'pair-auto-budget.json',{})
    except (OSError,ValueError):ledger={}
    if not isinstance(ledger,dict):ledger={}
    aborted=abort_stamps(ledger.get('aborted'),stamp)
    others=[x for x in ledger.get('others') if x in events] if isinstance(ledger.get('others'),list) else []
    if not failover:others.append(stamp)
    row={'events':events+[stamp]}
    if aborted:row['aborted']=aborted  # a refund of this charge must still see the earlier aborts of the series (retry_wait)
    if others:row['others']=others
    atomic_json(PERSIST/'pair-auto-budget.json',row)
    clock_note(row['events'],stamp)  # BH3-03: the monotonic age of this charge


def ledger_hold(settings, now):
    """return_hold from the persistent failover ledger; an unreadable ledger holds the longest."""
    from agent import PERSIST,read_json
    from recovery_settings import normalized
    recovery=normalized(settings)
    try:
        ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]})
        events,_=budget(effective_events(ledger,now),now,recovery['attempt_window']*60,recovery['attempt_limit'])
    except (ValueError,TypeError,AttributeError,OSError):return HOLD_CAP
    return return_hold(failover_events(events,ledger),now,recovery)


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
    from stock_derived import network_partition
    return checksum(network_partition(rows))


# The stock client adds exit bookkeeping options to the firewall zone of a VPN
# client while its tunnel is up and removes them when it stops. Only those
# options, with the values the stock client writes, on a zone that names a VPN
# client interface are not an external edit (F-34): the same option on any
# other section - the WAN or LAN zone among them - is one, and so is a value
# the stock client never writes.
VENDOR_EXIT_OPTION = re.compile(rb"[ \t]*option[ \t]+gl_(wan_like|bwa_managed|bwa_exit_id|bwa_bridge_reject)[ \t]+'([^'\r\n]*)'[ \t]*")
# R4-05: the complete UCI header syntax - the type and the name each bare, in single or in double quotes, a trailing
# comment - and, conservatively, ANY line that begins with the word config starts a new section (UCI_SECTION_START):
# a header this filter cannot parse is a section of someone else, where nothing is ever filtered out.
UCI_SECTION_START = re.compile(rb"[ \t]*config(?:[ \t].*)?")
UCI_SECTION = re.compile(rb"[ \t]*config[ \t]+(?:'([A-Za-z0-9_-]+)'|\"([A-Za-z0-9_-]+)\"|([A-Za-z0-9_-]+))"
                         rb"(?:[ \t]+(?:'([A-Za-z0-9_]+)'|\"([A-Za-z0-9_]+)\"|([A-Za-z0-9_]+)))?[ \t]*(?:#.*)?")
ZONE_MEMBER = re.compile(rb"[ \t]*(?:option[ \t]+(?:name|network)|list[ \t]+network)[ \t]+'([^'\r\n]*)'[ \t]*")
VPN_CLIENT_NAME = re.compile(r'(?:wgclient|ovpnclient)(?:[1-9][0-9]{0,3})?')


def _section_header(line):
    """(type, name or None) of a UCI section header line; None when the line is not one this filter understands."""
    header = UCI_SECTION.fullmatch(line.rstrip(b'\r'))
    if header is None:
        return None
    kind = header.group(1) or header.group(2) or header.group(3)
    name = header.group(4) or header.group(5) or header.group(6)
    return kind, name


def _vpn_client_zone(lines):
    """True for a firewall zone section whose section name, name or network names a VPN client interface."""
    header = _section_header(lines[0])
    if header is None or header[0] != b'zone':
        return False
    names = [header[1].decode()] if header[1] else []
    for line in lines[1:]:
        match = ZONE_MEMBER.fullmatch(line.rstrip(b'\r'))
        if match:
            names.extend(match.group(1).decode('utf8', 'replace').split())
    return any(VPN_CLIENT_NAME.fullmatch(x) for x in names)


def _vendor_exit_value(option, value):
    if option == b'bwa_exit_id':
        return VPN_CLIENT_NAME.fullmatch(value.decode('utf8', 'replace')) is not None
    return value in (b'0', b'1')


def _firewall_sections(data):
    sections, current = [], []
    for line in data.split(b'\n'):
        if UCI_SECTION_START.fullmatch(line.rstrip(b'\r')) and current:
            sections.append(current)
            current = []
        current.append(line)
    sections.append(current)
    return sections


def firewall_without_vendor_exit(data):
    kept = []
    for lines in _firewall_sections(data):
        owned = _vpn_client_zone(lines)
        for line in lines:
            match = VENDOR_EXIT_OPTION.fullmatch(line.rstrip(b'\r'))
            if owned and match and _vendor_exit_value(match.group(1), match.group(2)):
                continue
            kept.append(line)
    return b'\n'.join(kept)


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
        data = firewall_without_vendor_exit(data)
    return hashlib.sha256(data).hexdigest()


# Every stock rtp2.sh run deletes and regenerates these vendor-owned sections.
GL_VPN_RULES = re.compile(rb"\n[ \t]*option[ \t]+gl_vpn_rules[ \t]+'1'[ \t]*\r?(?:\n|$)")


def firewall_bytes():
    path = Path('/etc/config/firewall')
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1048576:
        raise ValueError('PAIR-CONFIG-UNVERIFIED')
    return path.read_bytes()


def static_firewall_digest(data):
    """Firewall digest without the vendor-regenerated gl_vpn_rules sections."""
    kept = [block for block in re.split(rb'\n(?=config[ \t])', data) if not GL_VPN_RULES.search(b'\n' + block)]
    return config_digest('firewall', b'\n'.join(kept))


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
        if observed[name] != sha and not (name == 'firewall' and hashlib.sha256(firewall_bytes()).hexdigest() == sha):
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
    from agent import inventory, TERMS_VERSION
    from preparation_status import snapshot
    if settings.get('pair_auto_mode') != MODE or settings.get('terms_version') != TERMS_VERSION:
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
DEVICE_WAIT = 60  # seconds a recovery revive waits for a revived tunnel device (bounded; no guard meanwhile)


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


def _log(line):
    try:subprocess.run(['logger','-t','homensai-vpn',str(line)[:400]],timeout=5,check=False,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except (OSError,subprocess.SubprocessError):pass


# VENDOR-WORKER-BUSY has no timeout: with a dead primary Auto waits without an attempt for as long as it lasts, and a long wait
# looked like every short one. After BUSY_SEEN_SECONDS with the same thing in the way (the same file: inode and pid) the
# publication names what was seen: its own code per cause, one log line, one journal event, a Telegram notice. It changes no
# decision: the blocker stays, no lock is touched. The codes say what was observed, never that GL is idle. Lua: pair.busy_fields.
BUSY_SEEN_SECONDS = 120
BUSY_SCAN_SECONDS = 30  # seconds between worker scans; a longer gap in busy ends the episode
BUSY_CODES = {'rtp-lock-dead':'VENDOR-BUSY-RTP-LOCK-DEAD','rtp-lock-live':'VENDOR-BUSY-RTP-LOCK-LIVE','tunnel-switch':'VENDOR-BUSY-TUNNEL-SWITCH',
              'workers':'VENDOR-BUSY-WORKERS','unidentified':'VENDOR-BUSY-UNIDENTIFIED'}
BUSY_TRACK = [None]


def busy_seen_step(track, busy, now, observe):
    """-> track, row|None. observe(scan) -> vendor_busy_seen's row. Monotonic time, counted per mark: a new file or pid starts
    again. Without a file 'workers' stays once seen: each flip of the reason is a journal write."""
    if not busy:return None,None
    if track is not None and now-track['seen']>BUSY_SCAN_SECONDS:track=None
    if track is None:track={'since':now}
    track['seen']=now
    scan=now-track['since']>=BUSY_SEEN_SECONDS and ('scanned' not in track or now-track['scanned']>=BUSY_SCAN_SECONDS)
    if scan:track['scanned']=now
    try:row=observe(scan)
    except (OSError,ValueError,RuntimeError,TypeError):row=None
    if not isinstance(row,dict) or not isinstance(row.get('mark'),str) or row.get('kind') not in BUSY_CODES:row={'kind':'unidentified','mark':'no-file'}
    if row['mark']!=track.get('mark'):
        track.update(mark=row['mark'],mark_since=now,kind=row['kind'],pid=row.get('pid'),workers=None,logged=None)
    elif track['kind']=='unidentified' or row['kind']!='unidentified':track['kind']=row['kind']
    if scan:track['workers']=row.get('workers')
    if now-track['mark_since']<BUSY_SEEN_SECONDS:return track,None
    return track,{'kind':track['kind'],'pid':track['pid'],'workers':track['workers'],'seconds':int(now-track['mark_since'])}


def busy_fields(backend, blockers, value):
    """Adds the code to a BLOCKED publication once a busy lasted. Never raises: only a status text depends on it."""
    try:
        observe=getattr(backend,'vendor_busy_seen',lambda scan:None)
        track,row=busy_seen_step(BUSY_TRACK[0],'VENDOR-WORKER-BUSY' in blockers,time.monotonic(),observe)
        BUSY_TRACK[0]=track
        if row is None or value is None:return value
        code=BUSY_CODES[row['kind']]
        value.update(reason=code,busy_seconds=row['seconds'],vendor_lock_pid=row['pid'],vendor_workers=row['workers'])
        if track.get('logged')!=code:
            track['logged']=code
            _log('%s: VENDOR-WORKER-BUSY for %d s, lock pid %s, vendor workers seen %s; observed only, Auto stays blocked, no lock touched'%(code,row['seconds'],row['pid'],row['workers']))
    except (AttributeError,OSError,ValueError,TypeError,KeyError):pass
    return value


# Verification gap (MT3000 cut 07.11.2026, alpha8: the owner's lamp showed BLOCKED without a reason for 2-3 s about 12 s and
# 27 s after an own transition, then came back by itself). A pass whose diagnostic() answers only a short vendor or observation
# wait (a GL worker holding its tunnel-switch/rtp lock - the lock study of 05.11.2026 measured such only-this-blocker episodes
# at 2.3 s at most -, or the monitor's next write not there yet) ends before its attestation. Right after a CONFIRMED pass of
# the same session that pass now keeps the last confirmed publication (state, reason, roles) with verifying=True and the wait
# codes in verify_blockers; readiness_verified and kernel_policy_verified are False (this pass verified nothing), and the
# channel path carries the earlier kernel proof with its ORIGINAL time (never renewed). The gap lasts only while that proof
# is inside its 15 s validity (channel_path valid_for): after it, for any other blocker, or after a BLOCKED/transition,
# BLOCKED is published exactly as before. No decision is taken in a gap pass (it still ends there). Lua: pair.verify_gap.
VERIFY_GAP_SECONDS = 15
VERIFY_GAP_BLOCKERS = frozenset(('VENDOR-WORKER-BUSY','VENDOR-SETTLING','OBSERVATION-STALE','PROFILE-IDENTITY-CHANGED',
                                 'VENDOR-IDENTITY-UNKNOWN','RESERVE-NOT-CONNECTED'))
# IR-02 (integration review 07.11.2026): DEGRADED-ON-RESERVE is a confirmed publication too since the owner decisions of
# 07.11 (a held pass on the pinned reserve, RESERVE-FAILED / RESERVE-HEALTH-UNKNOWN, carries the kernel proof); without it
# a short wait right after that pass still fell through to BLOCKED without a reason. Lua: pair.VERIFY_GAP_STATES.
VERIFY_GAP_STATES = frozenset(('OBSERVING','COMMITTED','DEGRADED-ON-RESERVE'))
VERIFY_GAP_KEEP = ('state','reason','source','target','certified','external_lan_verified','vendor_identity','source_failures','reserve_healthy')


def _finite_number(value):
    return type(value) in (int,float) and math.isfinite(value)


def verify_gap(previous,blockers,now,roles):
    """The publication that keeps the confirmed state of a verification gap, or None (publish BLOCKED).

    previous: native-status.json as published; roles: the session's policy_roles (source_id/target_id)."""
    if not isinstance(blockers,list) or not blockers or any(code not in VERIFY_GAP_BLOCKERS for code in blockers):return None
    if not isinstance(previous,dict) or not isinstance(roles,dict):return None
    if previous.get('mode')!='continuous-pair' or previous.get('state') not in VERIFY_GAP_STATES or previous.get('blockers'):return None
    source,target=previous.get('source'),previous.get('target')
    if not isinstance(source,str) or source==target or source!=roles.get('source_id') or target!=roles.get('target_id'):return None
    path=previous.get('channel_path')
    if (not isinstance(path,dict) or path.get('confirmed') is not True or path.get('kernel_policy_verified') is not True
            or path.get('transitioning') is True or path.get('source_profile_id')!=source or path.get('target_profile_id')!=target):return None
    active=path.get('active_profile_id')
    role='source' if active==source else 'target' if active==target else None
    checked=path.get('checked_at')
    if role is None or not _finite_number(checked) or not _finite_number(now):return None
    age=now-checked
    if age<0 or age>VERIFY_GAP_SECONDS:return None
    value={'mode':'continuous-pair','proof_scope':MODE}
    value.update({key:previous[key] for key in VERIFY_GAP_KEEP if key in previous})
    since=previous.get('verifying_since')
    if previous.get('verifying') is not True or not _finite_number(since) or since>now or since<checked:since=now
    value.update(blockers=[],verifying=True,verifying_since=float(since),verify_blockers=list(blockers),readiness_verified=False,
                 kernel_policy_verified=False,kernel_proof={'verified':True,'time':checked,'role':role,'profile_id':active})
    return value


def verify_gap_publish(state,blockers,backend=None):
    """Publishes the kept state of a verification gap; False = publish BLOCKED. Never raises (only the status text depends
    on it); the first pass of a gap leaves one log line naming the wait."""
    import native_switch as n
    from agent import read_json
    try:
        previous=read_json(n.STATE,{})
        value=verify_gap(previous,blockers,time.time(),state.get('policy_roles') if isinstance(state,dict) else None)
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return False
    if value is None:return False
    age=time.time()-value['kernel_proof']['time']
    if backend is not None:busy_fields(backend,blockers,None)  # the busy episode is still measured
    try:n.publish(value)
    except (n.Refused,OSError,ValueError,TypeError,KeyError):return False
    if previous.get('verifying') is not True:
        _log('PAIR-VERIFY-GAP: %s; %s kept on the kernel proof of %.1f s ago (bounded %d s)'%(','.join(blockers),value.get('state'),age,VERIFY_GAP_SECONDS))
    return True


# 01.11.2026 boot recovery trace: one line per step of the supervisor recovery and the pair cleanup while the boot is
# young, so a power-cut soak separates our steps from the firmware's. Lua: durable.boot_step (same text).
BOOT_TRACE_UPTIME=600


def boot_step(step,uptime=None):
    try:now=_uptime() if uptime is None else uptime
    except (OSError,ValueError):return False
    if type(now) not in (int,float) or not math.isfinite(now) or not 0<=now<BOOT_TRACE_UPTIME:return False
    _log('BOOT-RECOVERY-STEP: %s at %.1f'%(step,now))
    return True


PROFILE_CONFIGS = ('wireguard', 'ovpnclient')
SKIP_LOG_EVERY = 300
_skip_logged = {}


def _revive_log(line, key=None):
    if key is not None:
        now=time.monotonic()
        if key in _skip_logged and now-_skip_logged[key]<SKIP_LOG_EVERY:return
        _skip_logged[key]=now
    _log(line)


def ensure_devices(backend, state):
    """Start the pair's two configured clients when a recovery needs a tunnel device and none is up.

    Power cut with a held/committed journal (MT3000 sysrq-b, 31.10.2026): after the boot the intent (RAM) is
    gone and the prepared router does not start the VPN clients itself (vendor autostart off; the pair starts
    them). The cleanup of a COMMITTED/HELD-ON-RESERVE journal ends with guard(devices()), which refuses an empty
    list (UNSAFE-GUARD-DEVICE): the journal stayed held and Start refused TRANSACTION-IN-PROGRESS forever.
    The interfaces are the pair state's `interfaces` (not only `owned`: clients already up when the session
    began are not owned - alpha14 cut). Checks as in begin(): each row exists with its protocol, auto='0' and
    disabled='0', netifd reports it stopped, and the profile definitions (wireguard/ovpnclient configs) are the
    session's. The whole-network identity and the other protected configs (wireless, dhcp, DNS - the vendor
    rewrites some at boot) are only logged. Stop-fenced ifup, shared pair-revive.json budget, bounded wait, no
    guard while waiting. A client the session did not own stays up after the cleanup (as before the session).
    Every skip is logged (PAIR-RECOVERY-REVIVE-SKIPPED, at most once per reason per 5 min). Returns the devices
    or None; never raises. Lua counterpart: pair.ensure_devices.
    """
    import native_switch as n
    try:
        devices=backend.devices()
        if devices:return devices
    except (n.Refused,OSError,ValueError,subprocess.SubprocessError):pass
    if n.STOP or not isinstance(state,dict) or not state:return None
    started=[]
    def skip(reason):_revive_log('PAIR-RECOVERY-REVIVE-SKIPPED: '+reason,reason)
    try:
        from agent import RUNTIME, atomic_json, read_json
        from auto_control import current_revision
        from pair_interfaces import state as state_interfaces
        managed=state_interfaces(state)
        rows=network()
        if normalized_network(rows,managed)!=state['network_identity']:
            _revive_log('PAIR-RECOVERY-REVIVE: network identity differs from the session (profiles checked one by one)','identity')
        others=tuple(name for name in state.get('protected',{}) if name not in PROFILE_CONFIGS)
        if changed(state,configs(managed),skip=('firewall',)+others):
            skip('PAIR-EXTERNAL-CONFIG-CHANGE');return None
        revision=current_revision(RUNTIME)
        now=time.time()
        path=RUNTIME/'pair-revive.json'
        try:ledger=read_json(path,{})
        except (OSError,ValueError):ledger={}
        if not isinstance(ledger,dict):ledger={}
        by_name={row.get('.name'):row for row in rows}
        for interface in sorted(managed):
            events=ledger.get(interface,[])
            events=[x for x in events if type(x) in (int,float) and math.isfinite(x) and 0<=now-x<900] if isinstance(events,list) else []
            row=by_name.get(interface)
            if not row or row.get('proto')!=managed[interface] or row.get('auto')!='0' or row.get('disabled')!='0':
                skip('PAIR-PROFILES-UNVERIFIED '+interface);continue
            if events and now-events[-1]<REVIVE_PAUSE or len(events)>=REVIVE_LIMIT:
                skip('REVIVE-BUDGET '+interface);continue
            if not client_down(interface):
                skip('NOT-STOPPED '+interface);continue
            ledger=dict(ledger,**{interface:events+[now]});atomic_json(path,ledger)
            started.append(interface)
            try:
                n.forward_dispatch(['ifup','-w',interface],revision,timeout=20)
                _revive_log('PAIR-RECOVERY-REVIVE: ifup '+interface)
            except (n.Refused,OSError,ValueError,subprocess.SubprocessError) as error:
                _revive_log('PAIR-RECOVERY-REVIVE: ifup '+interface+' failed '+str(getattr(error,'code',error)))
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        _revive_log('PAIR-RECOVERY-REVIVE: '+str(getattr(error,'code',error)))
    if not started:return None
    deadline=time.monotonic()+DEVICE_WAIT
    while True:
        try:
            devices=backend.devices()
            if devices:return devices
        except (n.Refused,OSError,ValueError,subprocess.SubprocessError):pass
        if n.STOP or time.monotonic()>=deadline:return None
        time.sleep(2)


def boot_devices(backend):
    """ensure_devices() for the pair session a boot recovery finds (none or a terminal one: None)."""
    try:state=read_state()
    except (OSError,ValueError,KeyError,TypeError):return None
    # K3 (formal model 03.11.2026): a session handed over on the reserve (STOPPED with handover) still owns its clients
    # until the Start adopts them: after a power cut they are started for the VPN-only guard of the held reserve
    if not state or state.get('phase') in TERMINAL and not has_handover(state):return None
    return ensure_devices(backend,state)


def begin(backend, settings, request):
    import native_switch as n
    selection = preflight(backend, settings)
    # Owner 05.11.2026: a Start with an unaccepted key on the channel that carries the traffic afterwards (the source, or the
    # reserve of a boot handover: n.carrying_unaccepted) takes nothing: no session, no guard, no ifup. A key on the other channel
    # lets it go, the directional gate keeps the pair off that channel. The owner's Start and the boot resume alike; the refusal
    # ends the request through fail_request. Lua: pair.begin.
    pinned=n.carrying_unaccepted(backend,selection)
    if pinned:raise n.Refused(pinned)
    from pair_interfaces import selection as selection_interfaces
    managed=selection_interfaces(selection)
    data = network()
    selected = {row['.name']: row for row in data if row.get('.name') in managed}
    if set(selected) != set(managed) or any(
            row.get('proto') != managed[name] or row.get('auto') != '0' or row.get('disabled') not in ('0', '1')
            for name, row in selected.items()):
        raise ValueError('PAIR-PROFILES-UNVERIFIED')
    flags={name: row['disabled'] for name, row in selected.items()}
    # variant D: a boot handover on the reserve is adopted only after a fresh check of everything (else the old path)
    handover=None
    try:hprior=read_state()
    except (OSError,ValueError):hprior={}
    if has_handover(hprior):
        try:held=n.journal_read()
        except (n.Refused,OSError,ValueError):held=None
        if handover_matches(hprior,held):
            try:kernel=adoptable(backend,selection,held,hprior)
            except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):kernel=None
            if kernel is None:
                release_handover(hprior);raise ValueError('BOOT-RESERVE-UNVERIFIED')
            handover={'prior':hprior,'journal':held,'kernel':kernel}
    # the clients a boot cleanup kept up for this Start (boot_keep) stay owned, with their flags before the old session:
    # a later Stop returns them exactly as the old cleanup would have. Everything else of the session is read fresh here.
    adopted=[]
    try:prior=read_state()
    except (OSError,ValueError):prior={}
    if has_kept(prior):
        for name in prior['kept']:
            if name in selected and selected[name].get('disabled')=='0':adopted.append(name);flags[name]=prior['kept_flags'][name]
    state = dict(id=request['id'], phase='STARTING', started=time.time(), revision=request['revision'],
                 network_identity=normalized_network(data,managed), interfaces=managed, protected=configs(managed), owned=adopted,
                 before_flags=flags,
                 process_bindings=selection['process_bindings'],
                 order=list(handover['prior']['handover']['order']) if handover else selection['order'], policy_hash=selection['hash'])
    # Lets a later recovery tell vendor-only gl_vpn_rules drift from a foreign edit.
    try:state['protected_static']={'firewall':static_firewall_digest(firewall_bytes())}
    except (OSError,ValueError):pass  # the full protected digest above still applies
    from pair_policy import proof
    state['policy_roles']=proof(selection)
    save(state)  # Durable ownership precedes any network write.
    # K4 (formal model 03.11.2026): the full block releases itself after GUARD_RELEASE_SECONDS (90 s), but bringing
    # both clients up takes up to ~170 s (quiet 20 + ifup -w + quiet 45 per role). The guard is therefore re-armed
    # before every bounded step (each well below 90 s): never a moment without a guard while the clients start, and
    # the kernel still releases the block 90 s after a lost process. A VPN-only guard already standing - the boot
    # handover's held reserve (proven up), or the outside-change hold this Start ends (K9) - is kept VPN-only on the
    # tunnels that are up, never downgraded to the self-releasing full block.
    keep_vpn=bool(handover) or (_outside_guard.get('mode')=='vpn' and backend.guard_exists())
    outside_guard_reset()
    def hold_guard():
        if keep_vpn:
            try:devices=backend.devices()
            except (n.Refused,OSError,ValueError,subprocess.SubprocessError):devices=None
            if devices:
                backend.guard(devices);return
        backend.guard()
    hold_guard()
    for index,role in enumerate(('source', 'target')):
        interface = selection[role]['interface']
        require_running(request['revision'])
        if index:hold_guard()
        quiet(20,request['revision'])
        if selected[interface]['disabled'] == '1':
            state['owned'].append(interface)
            save(state)
            hold_guard()
            set_disabled(state, interface, '0', request['revision'])
            # Stock -w suppresses unrelated Wi-Fi setup; it is not a wait flag.
            n.forward_dispatch(['ifup', '-w', interface], request['revision'], timeout=20)
            hold_guard()
            quiet(45,request['revision'])
        elif client_down(interface):
            # Enabled by the operator but stopped: Auto starts it and restores it on Stop.
            if interface not in state['owned']:
                state['owned'].append(interface)
                save(state)
            hold_guard()
            try:
                n.forward_dispatch(['ifup', '-w', interface], request['revision'], timeout=20)
            except subprocess.SubprocessError:
                pass  # The running supervisor retries within its bounded budget.
            hold_guard()
            quiet(45,request['revision'])
    state['phase'] = 'RUNNING'
    state['ran'] = True
    require_running(request['revision'])
    backend.guard(backend.devices(), control_revision=request['revision'])
    save(state)
    if handover:adopt_journal(state,handover['journal'],handover['kernel'],request['revision'])
    return state


# Owner decision 01.11.2026 (variant C, BOOT-RECOVERY-2026-11-01.ru.md; physical power cuts on beta1): the boot
# cleanup stopped the pair's two healthy clients (ifdown + vendor quiet, ~20 s) only for the boot resume's Start to
# bring them up again. Now, when the boot resume will press Start (the owner's marker, no newer Stop latch, the boot
# resume not finished, uptime below BOOT_KEEP_UPTIME) and every owned client is up, the cleanup keeps them: the route
# is restored and verified exactly as before, the session ends STOPPED and records the kept clients with their flags
# before the session. The next Start's begin() adopts them as owned and reads everything else fresh, so no tunnel
# identity of the old session is reused. Without that Start within KEEP_SECONDS (or after a Stop, a failed boot
# resume, the boot window) release_kept() stops them as the old cleanup would have. An owner Stop and any client
# that is not up keep the old behaviour. Lua: pair.boot_keep.
BOOT_KEEP_UPTIME=900   # boot_resume.UNTIL_UPTIME
KEEP_SECONDS=600


def _uptime():
    return time.monotonic()


# BH-06 (bug hunt 07.11.2026): the hold_reserve rescue probe of a reserve the detector calls failed (tick, path without an
# open journal) is a full live probe (DNS + HTTPS). During a total outage (WAN down) the precondition holds on every tick,
# so the dead reserve was probed afresh each tick, slowing the loop and repeating probe traffic. One probe result is now
# kept per failure episode (this session, this reserve) for RESCUE_PROBE_INTERVAL monotonic seconds; the episode ends
# (the memory is cleared) as soon as the precondition no longer holds. Twin: lua/pair.lua rescue_health (env.rescue_probe).
RESCUE_PROBE_INTERVAL = 60
RESCUE_PROBE = {}


def rescue_health(backend, state, target):
    key = (state.get('id'), target)
    mono = _uptime()
    row = RESCUE_PROBE.get('row')
    if row is not None and row['key'] == key and 0 <= mono - row['at'] < RESCUE_PROBE_INTERVAL:
        return row['health']
    health = backend.health(target)
    RESCUE_PROBE['row'] = {'key': key, 'at': mono, 'health': health}
    return health


def interface_up(interface):
    return Path('/sys/class/net',interface).exists() and not client_down(interface)


def has_kept(state):
    return isinstance(state,dict) and state.get('phase')=='STOPPED' and isinstance(state.get('kept'),list) and bool(state['kept'])


def _resume_pending(tx=None):
    """-> (pending, uptime, the reason when not pending: the handover refusal log).

    tx (03.11.2026, forward_resume.py): this supervisor's recovery finished the switch tx on the reserve after a restart
    without a boot; the monitor's restart resume (boot_resume token) presses Start for it, so neither the boot window
    nor this boot's resume state applies - only the owner's marker and Stop latch, and the marker's KEEP_SECONDS.
    """
    try:now=_uptime()
    except (OSError,ValueError):return False,None,'UPTIME'
    # (2.1.0-alpha7 fix, 03.11.2026: also a refused resume of tx - the restart Start comes all the same; the handover
    # itself still needs a finished one, see boot_handover)
    forward=False
    if tx is not None and type(now) in (int,float):
        from forward_resume import restarted
        forward=restarted(tx)
    if not forward and (type(now) not in (int,float) or not math.isfinite(now) or not 0<=now<BOOT_KEEP_UPTIME):return False,now,'UPTIME'
    import boot_resume
    from agent import RUNTIME,PERSIST,read_json
    try:wanted,why=boot_resume.wanted(PERSIST)
    except (OSError,ValueError):return False,now,'RESUME-MARKER-UNREADABLE'
    if not wanted:return False,now,str(why or 'AUTO-RESUME-NOT-REQUESTED')
    if forward:
        # the restart resume of this supervisor start (its token) that failed or skipped ends the wait
        try:row=read_json(RUNTIME/boot_resume.STATE,{})
        except (OSError,ValueError):row={}
        try:token=boot_resume.token(RUNTIME)
        except (OSError,ValueError):token=None
        if token is not None and isinstance(row,dict) and row.get('supervisor')==token and row.get('state') in ('FAILED','SKIPPED'):
            return False,now,'RESUME-'+row['state']
        return True,now,None
    try:row=read_json(RUNTIME/boot_resume.STATE,{})
    except (OSError,ValueError):row={}
    if isinstance(row,dict) and row.get('state') in ('FAILED','SKIPPED'):return False,now,'RESUME-'+row['state']
    return True,now,None


def boot_keep(state,stop_revision=None,tx=None):
    """tx: the journal's transaction; when this supervisor start ran its forward resume (forward_resume.restarted), the
    restart Start replaces the boot window (MT3000 2.1.0-alpha7: a refused resume tore the healthy reserve down)."""
    if stop_revision is not None or not state.get('owned') or not _resume_pending(tx)[0]:return False
    try:return all(interface_up(interface) for interface in state['owned'])
    except (OSError,ValueError,subprocess.SubprocessError):return False


def kept_valid(state,tx=None):
    pending,now,_=_resume_pending(tx)
    at=state.get('kept_at')
    return pending and type(at) in (int,float) and at<=now and now-at<KEEP_SECONDS


def release_kept(backend,state):
    """The kept clients are stopped and their flags restored, as the old boot cleanup would have done."""
    import native_switch as n
    from pair_interfaces import state as state_interfaces
    managed=state_interfaces(state)
    for interface in reversed(state['kept']):
        if normalized_network(network(),managed) != state['network_identity']:raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        if changed(state, configs(managed), skip=('firewall',)):raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
        n.command(['ifdown', interface], timeout=20)
        quiet(45)
        set_disabled(state, interface, state['kept_flags'][interface])
        if Path('/sys/class/net', interface).exists():raise ValueError('PAIR-PROFILE-STOP-UNVERIFIED')
    backend.unguard()
    for key in ('kept','kept_flags','kept_at','kept_tx'):state.pop(key,None)
    save(state)
    boot_step('pair kept clients released')


# Owner decision 01.11.2026 (variant D, BOOT-RECOVERY-2026-11-01.ru.md; physical power cuts on beta1): after a boot
# with a completed switch on the reserve (journal COMMITTED or HELD-ON-RESERVE, current role target) the cleanup
# waited ~60-130 s for the primary proof before it could end the session, and only then the boot resume's Start was
# accepted. Now, when the boot resume will press Start, the primary is not proven yet and the reserve route is proven
# freshly (attest_policy verified with role target, the reserve healthy by a fresh probe, the live order the
# journal's), the old session hands over: it ends STOPPED with handover={tx,order,policy_hash,at} (and its kept
# clients, variant C), the guard stays VPN-only, the journal is untouched. Start accepts exactly this journal; the
# new session's begin() checks everything again and then records the adoption in the journal (COMMITTED,
# BOOT-RESERVE-ADOPTED, boot_adopted={session,time,from_phase,from_reason}, confirmed=now so min_dwell counts from
# here, no manual request). The normal committed return policy brings it back to the primary. Any failed check, an
# owner Stop, no Start within KEEP_SECONDS, a failed boot resume: release_handover() and today's path. Interrupted
# switches never get here: they roll back as before (03.11.2026: unless forward_resume.py finished one after a restart
# without a boot; that COMMITTED journal gets its own handover, see _resume_pending). One handover per boot (RAM marker).
# Lua: pair.boot_handover.
HANDOVER_FILE='pair-handover.json'


def has_handover(state):
    return isinstance(state,dict) and state.get('phase')=='STOPPED' and isinstance(state.get('handover'),dict)


def handover_matches(state,journal):
    return (has_handover(state) and isinstance(journal,dict) and state['handover'].get('tx')==journal.get('tx')
            and journal.get('phase') in ('COMMITTED','HELD-ON-RESERVE'))


def _reserve_proven(backend,journal,selection=None):
    kernel=backend.attest_policy(selection)
    if not isinstance(kernel,dict) or kernel.get('verified') is not True or kernel.get('role')!='target':return None
    if backend.health(journal['target']) is not True:return None
    return kernel


# 01.11.2026 (MT3000 sysrq-b on beta3: no handover, no reason in the log): the checks run on every cleanup pass for
# at most HANDOVER_WAIT s from the first one, each refusal is logged once per reason (BOOT-RECOVERY-STEP: handover
# refused <reason>), and after the wait today's path goes on without further checks. The reserve health is the
# backend's live probe (health()), never the monitor samples. Only the reserve has to be up: the primary may still be
# connecting (all owned clients are kept and adopted). RAM marker HANDOVER_FILE: {state:'waiting',first} ->
# {state:'handed'|'refused'}. Lua: pair.boot_handover.
HANDOVER_WAIT=60
_handover_logged=[None]


def handover_log_reset():_handover_logged[0]=None


def _handover_refused(reason):
    if _handover_logged[0]!=reason:
        _handover_logged[0]=reason;boot_step('handover refused '+reason)
    return False


def handover_check(backend,state,journal,context):
    """-> (None, kernel) when the reserve route can be handed over, else (the refusal reason, None)."""
    from pair_policy import current_role,state_order_matches
    current=current_role(journal)
    if current!='target':return 'ROLE %s'%current,None
    if context['session_order']!=state['order']:return 'SESSION-ORDER',None
    # a primary already proven returns at once on today's path; the handover only replaces the wait for the proof.
    # K2 (formal model 03.11.2026): "proven" with the flap-damping hold of the failover ledger, as the running tick
    # (ledger_hold): a restart must not turn a flapping primary into a proven one
    from recovery_settings import normalized
    settings=backend.policy()['settings']
    hold=ledger_hold(settings,time.time())
    if hold>normalized(settings)['primary_stable']:settings=dict(settings,recovery_primary_stable=hold)
    if backend.recovery_ready(journal['source'],settings) is True:return 'PRIMARY-PROVEN',None
    if not state_order_matches(state,journal,backend.order()):return 'ORDER',None
    kernel=backend.attest_policy()
    if not isinstance(kernel,dict) or kernel.get('verified') is not True:
        return 'KERNEL %s'%(kernel.get('code') if isinstance(kernel,dict) and kernel.get('code') else 'UNVERIFIED'),None
    if kernel.get('role')!='target':return 'KERNEL-ROLE %s'%kernel.get('role'),None
    health=backend.health(journal['target'])
    if health is not True:return 'RESERVE-HEALTH %s'%('UNKNOWN' if health is None else str(health).lower()),None
    return None,kernel


def boot_handover(backend,state,journal,context,stop_revision=None):
    from agent import RUNTIME,atomic_json,read_json
    import native_switch as n
    if stop_revision is not None or context is None or journal.get('phase') not in ('COMMITTED','HELD-ON-RESERVE'):return False
    path=RUNTIME/HANDOVER_FILE
    try:marker=read_json(path,{})
    except (OSError,ValueError):marker={}
    if not isinstance(marker,dict):marker={}
    # one handover per boot; a switch this supervisor finished after a restart (forward_resume) gets its own one
    from forward_resume import marked
    forward=marked(journal.get('tx'))
    if forward and marker.get('tx')!=journal.get('tx'):marker={}
    if marker.get('state') in ('handed','refused'):return False
    pending,now,why=_resume_pending(journal.get('tx') if forward else None)
    if not pending:return _handover_refused(why)
    tx=journal.get('tx') if forward else None
    first=marker.get('first')
    if type(first) not in (int,float) or first>now:
        first=now;atomic_json(path,{'state':'waiting','first':float(now),'tx':tx})
    if now-first>=HANDOVER_WAIT:
        atomic_json(path,{'state':'refused','first':float(first),'reason':_handover_logged[0],'tx':tx})
        return _handover_refused('WAIT-OVER after %s'%_handover_logged[0])
    try:reason,_=handover_check(backend,state,journal,context)
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:reason='ERROR %s'%(error.args[0] if error.args else type(error).__name__)
    if reason is not None:return _handover_refused(reason)
    backend.guard(backend.devices())  # VPN-only on the running tunnels, as the held journal had
    atomic_json(path,{'state':'handed','first':float(first),'tx':journal['tx'],'time':time.time()})
    state['handover']={'tx':journal['tx'],'order':list(state['order']),'policy_hash':state['policy_hash'],'at':float(_uptime())}
    if state.get('owned'):
        state.update(kept=list(state['owned']),kept_flags={x:state['before_flags'][x] for x in state['owned']},kept_at=state['handover']['at'])
    state['phase']='STOPPED';save(state)
    boot_step('pair cleanup handover on the reserve '+journal['tx'])
    return True


def _handover_open(journal):
    """boot_handover may still act on this journal (a read of its first gates)."""
    from agent import RUNTIME,read_json
    from forward_resume import marked
    try:marker=read_json(RUNTIME/HANDOVER_FILE,{})
    except (OSError,ValueError):marker={}
    if not isinstance(marker,dict):marker={}
    forward=marked(journal.get('tx'))
    if forward and marker.get('tx')!=journal.get('tx'):marker={}
    if marker.get('state') in ('handed','refused'):return False
    return _resume_pending(journal.get('tx') if forward else None)[0]


def reserve_waits(backend,state,journal,context,stop_revision=None):
    """T4 (trace conformance 04.11.2026, as finding 3 for the outside-change hold): a session HELD on a HELD-ON-RESERVE journal
    that waits for its primary (a Stop on a dead primary, K8; also with an edit in the GL panel visible) wrote STOPPING, the
    journal and HELD on every pass, about every 2 s for as long as the primary was down. Read-only: True when this pass would
    change nothing (the cleanup then writes no file). Any doubt: False, the full cleanup. Lua: pair.reserve_waits."""
    import native_switch as n
    if (stop_revision is not None or context is None or state.get('phase')!='HELD' or 'server_change' in state
            or journal.get('phase')!='HELD-ON-RESERVE'):return False
    try:
        if not backend.devices() or _handover_open(journal):return False
        return n.hold_unchanged(backend,journal,'PAIR-STOPPED',state['order'],cleanup_hold(backend,state,journal,stop_revision))
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):return False


def release_handover(state):
    """Back to today's path: the old session is HELD again and the next cleanup waits for the primary proof."""
    for key in ('handover','kept','kept_flags','kept_at','kept_tx'):state.pop(key,None)
    state['phase']='HELD';save(state)
    boot_step('pair handover released')


def adoptable(backend,selection,journal,prior):
    """begin(): the fresh checks of the adoption; the kernel proof or None."""
    from pair_policy import metadata,proof,current_order,current_role
    ctx=metadata(journal)
    if ctx is None or selection['hash']!=journal['hash'] or selection['hash']!=prior['handover']['policy_hash']:return None
    if selection['source'].get('id')!=journal['source'] or selection['target'].get('id')!=journal['target']:return None
    if ctx['session_order']!=prior['handover']['order'] or sorted(selection['order'])!=sorted(prior['handover']['order']):return None
    if any(ctx.get(key)!=item for key,item in proof(selection).items()):return None
    if backend.order()!=(current_order(journal),journal['hash']) or current_role(journal)!='target':return None
    return _reserve_proven(backend,journal,selection)


def adopt_journal(state,journal,kernel,revision):
    """The new session's journal says where it started: on the reserve, adopted at this boot."""
    import native_switch as n
    now=time.time()
    journal['boot_adopted']={'session':state['id'],'time':now,'from_phase':journal['phase'],'from_reason':journal.get('reason')}
    journal.update(phase='COMMITTED',reason='BOOT-RESERVE-ADOPTED',confirmed=now,control_revision=revision)
    journal.pop('manual_request_id',None)
    n.journal_write(journal)
    try:remember_selected(state,kernel)
    except (OSError,ValueError,KeyError,TypeError):pass
    n.publish({'state':'COMMITTED','reason':'BOOT-RESERVE-ADOPTED','source':journal['source'],'target':journal['target'],'mode':'continuous-pair',
               'proof_scope':MODE,'readiness_verified':True,'kernel_policy_verified':True,'kernel_proof':kernel,'original_restored':False,'blockers':[]})
    boot_step('pair session adopted the reserve '+journal['tx'])


def owner_stopped(state=None):
    """A Stop (or a give-up) is newer than the last Start of this session: the stop latch native-stop.json against the
    later of the owner's resume marker auto-resume.json (boot_resume.wanted's decision) and the session's own start
    (state['started']: a programmatic Start leaves no marker, an older latch is not its Stop). A damaged latch is not a
    Stop (the guard of the outside-change hold is never dropped on a damaged file). Lua: pair.owner_stopped."""
    import boot_resume
    from agent import PERSIST,read_json
    try:latch=read_json(PERSIST/'native-stop.json',None)
    except (OSError,ValueError):return False
    stopped=latch.get('requested') if isinstance(latch,dict) else None
    if type(stopped) not in (int,float) or not math.isfinite(stopped):return False
    try:marker=read_json(PERSIST/boot_resume.MARKER,None)
    except (OSError,ValueError):marker=None
    at=marker.get('time') if isinstance(marker,dict) and marker.get('enabled') is True else None
    if type(at) not in (int,float) or not math.isfinite(at):at=None
    started=state.get('started') if isinstance(state,dict) else None
    if type(started) in (int,float) and math.isfinite(started) and (at is None or started>at):at=started
    return at is None or stopped>=at


def cleanup_hold(backend,state,journal,stop_revision=None):
    """K2 (formal model 03.11.2026): the cleanup of a committed/held reserve that no owner Stop asked for (a recovery
    after a crash or a power cut, a released handover) returns to the primary only after the flap-damping hold of the
    failover ledger, exactly as the running tick (ledger_hold, committed_recovery_decision): the restart must not
    reset a hold that was doubled by a flapping primary. A failing reserve is left without the damped hold (as the
    tick), and an owner Stop returns as before. None = no damping. Lua: pair.cleanup_hold."""
    from recovery_settings import normalized
    if stop_revision is not None or owner_stopped(state):return None
    settings=backend.policy().get('settings',{})
    hold=ledger_hold(settings,time.time())
    if hold<=normalized(settings)['primary_stable']:return None
    if backend.health(journal['target']) is not True:return None
    return hold


# K9, owner decision 03.11.2026 (formal model): a session HELD by a change made outside the app (a readopt code; the
# cleanup stops before its guard step) keeps the LAN behind the VPN-only guard until the owner presses Start
# (release_for_start hands it over) or Stop. Before, a power cut dropped the guard (RAM) and the recovery never put it
# back: the LAN went out through the GL configuration without the VPN. Only with a settled journal (none or
# ROLLED-BACK; a held journal keeps its own guard rules). VPN-only on the tunnels that are up; with no tunnel up the
# full block, re-armed every OUTSIDE_REARM s (it still releases itself 90 s after a lost process). The owner's Stop
# (owner_stopped) releases the guard. Called after a failed recovery or cleanup of a session that is not running;
# returns True when the session is such a hold. Lua: pair.outside_hold.
OUTSIDE_REARM=45
_outside_guard={}


def outside_guard_reset():_outside_guard.clear();_orphan_seen.clear()


def outside_hold(backend):
    import native_switch as n
    state=read_state()
    if not state or state.get('phase')!='HELD' or state.get('recovery_error') not in READOPT_CODES:return False
    if n.journal_read().get('phase') not in (None,'ROLLED-BACK'):return False
    if owner_stopped(state):
        _outside_guard.clear()
        if backend.guard_exists():
            backend.unguard()
            _log('PAIR-OUTSIDE-CHANGE-GUARD: released by the owner Stop')
        if end_hold_on_stop(state):  # T4-A: the Stop ends STOPPED; the next Start begins a new session
            n.publish({'state': 'STOPPED', 'mode': 'continuous-pair', 'proof_scope': MODE, 'original_restored': False, 'blockers': []})
        return True
    try:devices=backend.devices()
    except (n.Refused,OSError,ValueError,subprocess.SubprocessError):devices=None
    devices=sorted(devices) if devices else None
    now=time.monotonic()
    exists=backend.guard_exists()
    if devices:
        key=' '.join(devices)
        if not exists or _outside_guard.get('mode')!='vpn' or _outside_guard.get('key')!=key:
            backend.guard(devices);_outside_guard.clear();_outside_guard.update(mode='vpn',key=key,at=now)
            _log('PAIR-OUTSIDE-CHANGE-GUARD: VPN-only %s until Start or Stop'%key)
    elif not exists or _outside_guard.get('mode')!='full' or now-_outside_guard['at']>=OUTSIDE_REARM:
        first=_outside_guard.get('mode')!='full'
        backend.guard();_outside_guard.clear();_outside_guard.update(mode='full',at=now)
        if first:_log('PAIR-OUTSIDE-CHANGE-GUARD: no VPN tunnel up, LAN blocked until Start or Stop')
    return True


# Review 04.11.2026 (finding 5): a session that owns no interface (its clients were already up when it started) had no
# network/configuration check left in cleanup: a K9 hold with PAIR-EXTERNAL-NETWORK-/CONFIG-CHANGE ended STOPPED and
# unguarded on the next pass, against the owner decision "the guard stays until Start or Stop". Until the owner's Stop
# (or Start) the change is checked again exactly as for owned interfaces. Lua: pair.outside_recheck.
OUTSIDE_RECHECK_CODES=('PAIR-EXTERNAL-NETWORK-CHANGE','PAIR-EXTERNAL-CONFIG-CHANGE')


def outside_recheck(state,stop_revision=None):
    return (stop_revision is None and isinstance(state,dict) and state.get('phase')=='HELD'
            and state.get('recovery_error') in OUTSIDE_RECHECK_CODES and not owner_stopped(state))


def held_unchanged(backend,state,journal,context,stop_revision=None):
    """Review 04.11.2026 (finding 3): the refusal the cleanup of a session HELD by an outside change would raise before
    its first action, found read-only - or None (the full cleanup runs). Before, every pass of a stable hold wrote STOPPING
    and then HELD again (publish_failure), about every 2 s for as long as the hold lasted: flash writes, and the Lua
    supervisor's after-stop key (it holds the state file's identity) started python3 on every pass. Lua: pair.held_unchanged."""
    from pair_policy import state_order_matches
    from pair_interfaces import state as state_interfaces
    if (stop_revision is not None or state.get('phase')!='HELD' or state.get('recovery_error') not in READOPT_CODES
            or 'server_change' in state or journal.get('phase') not in (None,'ROLLED-BACK')):return None
    order=backend.order()
    if order!=(state['order'],state['policy_hash']):
        if context is not None and state_order_matches(state,journal,order):return None  # the cleanup rolls back
        return 'PAIR-EXTERNAL-POLICY-CHANGE'
    if not (state.get('owned') or outside_recheck(state)):return None
    managed=state_interfaces(state)
    if normalized_network(network(),managed)!=state['network_identity']:return 'PAIR-EXTERNAL-NETWORK-CHANGE'
    if changed(state,configs(managed),skip=('firewall',)):return 'PAIR-EXTERNAL-CONFIG-CHANGE'
    return None


# Review 04.11.2026 (finding 4): the owner's Start hands a session HELD by an outside change over (release_for_start:
# STOPPED, owned=[]) and the next session's begin() takes the K9 VPN-only guard over. A Start refused after that hand-over
# (preparation, SPEED-BUSY, CONTROL-REVISION-STALE) or ended before its request left the guard with no session at all:
# no internet on the LAN while it is routed via WAN, and the owner's Stop did not release it (the journal path of the
# supervisor needs the restored order). Now the refused Start releases it (auto_control.start) and the supervisor after
# the owner's Stop (once per handed-over record). Only that guard: a STOPPED handed-over record that owns nothing, no
# kept/handover clients, intent not 'on', journal absent or ROLLED-BACK. Lua: pair.release_orphan_guard.
_orphan_seen={}


def _orphan_candidate(state):
    resolution=state.get('operator_resolution') if isinstance(state,dict) else None
    return (isinstance(state,dict) and state.get('phase')=='STOPPED' and not state.get('owned')
            and not any(key in state for key in ('kept','handover'))
            and isinstance(resolution,dict) and resolution.get('reason')=='AUTOMATIC-EXTERNAL-CHANGE-READOPT')


def release_orphan_guard(backend,state=None,start_refused=False):
    """True when the guard of a handed-over session nobody took over was removed."""
    import native_switch as n
    from auto_control import control_lock
    if state is None:state=read_state()
    if not _orphan_candidate(state):return False
    key=None
    if not start_refused:
        key=(state.get('id'),state['operator_resolution'].get('time'))
        if _orphan_seen.get('key')==key:return False  # looked at once after the Stop: nothing installs this guard again
        if not owner_stopped(state):return False
    released=False
    with control_lock():
        current=read_state()
        if (_orphan_candidate(current) and intent().get('mode')!='on' and n.journal_read().get('phase') in (None,'ROLLED-BACK')
                and backend.guard_exists()):
            backend.unguard();released=True
    if key is not None:_orphan_seen['key']=key
    if released:
        _outside_guard.clear()
        _log('PAIR-OUTSIDE-CHANGE-GUARD: released, the handed-over session ended without a new one (%s)'
             %('Start refused' if start_refused else 'owner Stop'))
    return released


def _orphan_guard_safe(backend,state=None,start_refused=False):
    import native_switch as n
    try:return release_orphan_guard(backend,state,start_refused)
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):return False


def cleanup(backend, state, stop_revision=None):
    import native_switch as n
    from pair_interfaces import state as state_interfaces
    managed=state_interfaces(state)
    backend.use_process_bindings(state.get('process_bindings'))
    if 'server_change' in state:server_resume(backend,state)  # a server change cut short: adopt this supervisor's own write
    journal = n.journal_read()
    from pair_policy import metadata,role,state_order_matches
    context=metadata(journal)
    if context is not None and (context['session_order']!=state['order'] or journal.get('hash')!=state['policy_hash']):
        # T4 (trace conformance 04.11.2026): a finished journal of the policy before an outside change is no claim on this
        # session (the Start after the change adopted the new policy): its Stop ended HELD instead of STOPPED until the next
        # Start. Only a journal still in progress is one; the live order is checked below for both. Lua: pair.cleanup.
        if journal.get('phase') not in (None,'ROLLED-BACK'):raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
        context=None
    # K11 (formal model 03.11.2026): the owner's Start hands a session HELD by an outside change over under the control
    # lock (release_for_start / request -> release_session: archived, STOPPED). A cleanup pass that read the record
    # before must not write its STOPPING over that hand-over (Start then refused PAIR-RECOVERY-REQUIRED and the session
    # stayed HELD). The record is read again under the same lock: another session or a finished one (the hand-over's
    # STOPPED) - this pass ends without a write.
    recheck=outside_recheck(state,stop_revision)  # finding 5: read before the STOPPING write (phase HELD)
    unchanged=held_unchanged(backend,state,journal,context,stop_revision)  # finding 3
    waiting=unchanged is None and reserve_waits(backend,state,journal,context,stop_revision)  # T4
    from auto_control import control_lock
    with control_lock():
        current=read_state()
        ours=not current or current.get('id')==state.get('id') and (current.get('phase') not in TERMINAL or state.get('phase') in TERMINAL)
        if ours and unchanged is None and not waiting:
            state['phase']='STOPPING';save(state)  # Route restoration does not complete interface ownership cleanup.
    if not ours:
        boot_step('pair cleanup superseded by a hand-over')
        return False
    if unchanged is not None:raise ValueError(unchanged)  # the hold is unchanged: nothing written (publish_failure: same code)
    if waiting:
        backend.guard(backend.devices())  # the guard follows the tunnels as on every pass; no file is written
        return False
    boot_step('pair cleanup %s'%journal.get('phase'))
    if journal.get('phase') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):
        if journal.get('activation_reapply') is True and journal.get('before')==journal.get('after'):
            from activation_recovery import finalize
            finalize(backend,state,journal,allow_stopping=True)
        else:raise ValueError('PAIR-RECOVERY-REQUIRED')
    if journal.get('phase') in ('COMMITTED', 'HELD-ON-RESERVE'):
        ensure_devices(backend,state)  # finish_committed/rollback end with guard(devices()): the pair's own tunnels first
        if boot_handover(backend,state,journal,context,stop_revision):return True
        hold=cleanup_hold(backend,state,journal,stop_revision)
        finished=(n.finish_committed(backend,journal,'PAIR-STOPPED',restore_order=state['order'],hold=hold) if context is not None
                  else n.finish_committed(backend,journal,'PAIR-STOPPED',hold=hold))
        if not finished:
            state['phase'] = 'HELD'
            save(state)
            return False
    elif context is not None and state_order_matches(state,journal,backend.order()) and backend.order()!=(state['order'],state['policy_hash']):
        ensure_devices(backend,state)
        if backend.recovery_ready(journal[role(context,state['order'])],backend.policy()['settings']) is not True:raise ValueError('PAIR-RECOVERY-REQUIRED')
        n.rollback(backend,journal,'PAIR-STOPPED',restore_order=state['order'])
    if backend.order() != (state['order'], state['policy_hash']):
        raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
    if boot_keep(state,stop_revision,journal.get('tx')):
        if normalized_network(network(),managed) != state['network_identity']:raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        if changed(state, configs(managed), skip=('firewall',)):raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
        # the guard stays: the next session's begin() guards again, release_kept() removes it
        state.update(kept=list(state['owned']),kept_flags={x:state['before_flags'][x] for x in state['owned']},kept_at=float(_uptime()),phase='STOPPED')
        from forward_resume import restarted
        if isinstance(journal.get('tx'),str) and restarted(journal['tx']):state['kept_tx']=journal['tx']
        save(state)
        boot_step('pair cleanup kept '+' '.join(state['kept']))
        return True
    if recheck and not state['owned']:
        if normalized_network(network(),managed) != state['network_identity']:raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        if changed(state, configs(managed), skip=('firewall',)):raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
    for interface in reversed(state['owned']):
        # Never stop a profile after an external identity/configuration change.
        if normalized_network(network(),managed) != state['network_identity']:
            raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        # The stock client edits the firewall while a tunnel is up; ifdown undoes it,
        # and set_disabled below verifies the firewall again after the stop.
        if changed(state, configs(managed), skip=('firewall',)):
            raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
        boot_step('pair cleanup ifdown '+interface)
        n.command(['ifdown', interface], timeout=20)
        quiet(45)
        boot_step('pair cleanup quiet '+interface)
        set_disabled(state, interface, state['before_flags'][interface])
        if Path('/sys/class/net', interface).exists():
            raise ValueError('PAIR-PROFILE-STOP-UNVERIFIED')
    if stop_revision is None:
        backend.unguard();state['phase']='STOPPED';save(state)
    else:
        from auto_control import control_lock
        with control_lock():
            n.require_control_revision(stop_revision)
            if intent().get('mode')!='off' or intent().get('revision')!=stop_revision:raise n.Refused('CLIENT-STOP')
            backend.unguard();state['phase']='STOPPED';save(state)
    boot_step('pair cleanup done')
    return True


def fence_recovery():
    """Revoke pair intent and pending commands before guarded journal recovery."""
    from auto_control import control_lock, revision_locked
    from agent import RUNTIME
    from pair_manual import terminalize_pending_locked
    with control_lock():
        if paths()[0].exists():
            stop_locked(revision_locked(RUNTIME))
        try:terminalize_pending_locked('UNCONFIRMED','PAIR-MANUAL-RECOVERED')
        except (OSError,ValueError,TypeError,KeyError):
            pass  # Preserve the damaged command; it must not block journal recovery.


def recover(backend):
    """Called after core journal recovery on supervisor restart; never resumes."""
    import native_switch as n
    try:
        # Fence old intent even when its durable ownership can no longer be
        # reconciled. Retain that ownership and every recovery guard on failure.
        fence_recovery()
        state = read_state()
        if state and state['phase'] not in TERMINAL:
            if not cleanup(backend, state):
                publish_failure('PAIR-RECOVERY-REQUIRED')
                _outside_hold_safe(backend)
                return False
    except (n.Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        publish_failure(error)
        _outside_hold_safe(backend)  # K9: a session held by an outside change keeps its guard
        return False
    return True


def _outside_hold_safe(backend):
    import native_switch as n
    try:return outside_hold(backend)
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):return False


def resume_running(state):
    """A session held by a transient error returns to RUNNING once a full tick verified network, configs and policy."""
    if state.get('phase') == 'HELD' and state.get('ran') is True:
        state['phase'] = 'RUNNING'
        state.pop('recovery_error', None)
        save(state)


def remember_selected(state,kernel):
    if (kernel.get('verified') is not True or kernel.get('role') not in ('source','target')
            or kernel.get('policy_hash')!=state.get('policy_hash') or type(kernel.get('time')) not in (int,float)):
        raise ValueError('KERNEL-POLICY-UNVERIFIED')
    from pair_policy import role
    if role(state['policy_roles'],kernel.get('order'))!=kernel['role']:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    old=state.get('selected_policy',{})
    if old.get('role')==kernel['role'] and old.get('hash')==kernel['policy_hash'] and old.get('order')==kernel['order']:return False
    state['selected_policy']={'role':kernel['role'],'order':list(kernel['order']),'hash':kernel['policy_hash'],'since':kernel['time']}
    save(state);return True


def charge_attempt(settings,revision,limited=True,failover=True):
    """Record a dispatched automatic switch. limited=False (leaving a failed path) ignores the attempt count:
    only the cooldown spacing applies; it bounds retries of a failed attempt (<=15 per 15 min, the ledger size).
    failover=False: a charge flap damping does not count (failover_events): the return of the pair_return path."""
    from agent import PERSIST,read_json
    from recovery_settings import normalized
    import native_switch as n
    require_running(revision);now=time.time();policy=normalized(settings)
    ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]})
    events,allowed=budget(effective_events(ledger,now),now,policy['attempt_window']*60,policy['attempt_limit'])
    aborted=abort_stamps(ledger.get('aborted'),now)
    if (limited and not allowed or events and now-events[-1]<max(policy['cooldown'],policy['min_dwell'])
            or retry_wait(aborted,events,now,policy)>0):raise n.Refused('PAIR-RATE-LIMIT')
    ledger_charge(events,now,failover)
    return now


def source_unstable(selection):
    """The diagnostic accepted a source that keeps being rebuilt only to leave it (failure_diagnosis)."""
    from failure_diagnosis import SOURCE_UNSTABLE
    coordination=selection.get('coordination') if isinstance(selection,dict) else None
    return isinstance(coordination,dict) and coordination.get('code')==SOURCE_UNSTABLE


def reapply_missing_policy(backend,state,settings,revision,journal,observed=None):
    """A valid ON intent may repair absent compiled rules, without changing policy order."""
    if state.get('policy_roles') is None:return False
    import native_switch as n
    requested=intent()
    if requested.get('mode')!='on' or requested.get('revision')!=revision or requested.get('id')!=state.get('id'):
        raise n.Refused('CLIENT-STOP')
    from pair_policy import proof,role,state_order_matches
    from recovery_settings import normalized
    from agent import PERSIST,read_json
    blockers,selection=backend.diagnostic()
    if blockers==['RESERVE-NOT-CONNECTED'] and journal.get('phase') in ('COMMITTED','HELD-ON-RESERVE'):
        # T3 (trace conformance 04.11.2026): the traffic is on a reserve whose client is gone. This blocker used to end the
        # pass here, before the committed decision: no return while the primary was healthy, until the reserve came back.
        # Nothing to repair without a selection; the outside-change check stays and the decision below goes on.
        if not state_order_matches(state,journal,backend.order()):raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
        return False
    if blockers or not selection:
        if verify_gap_publish(state,blockers,backend):return True  # a short wait right after a confirmed pass
        identity=state['policy_roles']
        value={'state':'BLOCKED','mode':'continuous-pair','proof_scope':MODE,'source':identity['source_id'],'target':identity['target_id'],
               'blockers':blockers or ['PAIR-POLICY-UNVERIFIED'],'readiness_verified':False,'kernel_policy_verified':False}
        n.publish(busy_fields(backend,blockers,value))
        return True
    if 'selected_policy' not in state:
        # A Start does not begin with an unaccepted key on the carrying channel (begin; here: a key seen while it ran, which waits
        # for the owner's word); a key on the other channel changes nothing. A session that already proved its route goes on
        # working, only a move onto that channel is refused (native_switch.key_unaccepted).
        pinned=n.carrying_unaccepted(backend,selection)
        if pinned:
            n.publish({'state':'BLOCKED','mode':'continuous-pair','proof_scope':MODE,'source':selection['source']['id'],'target':selection['target']['id'],
                       'blockers':[pinned],'readiness_verified':False,'kernel_policy_verified':False})
            return True
    if proof(selection)!=state['policy_roles'] or not state_order_matches(state,journal,backend.order()):
        raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
    kernel=backend.attest_policy(selection)
    if kernel.get('verified') is True:
        remember_selected(state,kernel)
        # LAN DNS follows the verified active channel: repairs drift after a GL rebuild of dns_mark (fw3/vpn-client
        # reload, boot). Observation-grade: never fails the pass.
        follow=getattr(backend,'dns_mark_follow',None)
        if kernel.get('role') in ('source','target') and follow is not None:
            try:follow()
            except Exception:pass
        if observed is not None:observed.update(selection=selection,kernel=kernel)
        return False
    if kernel.get('repairable_missing') is not True:
        n.publish({'state':'BLOCKED','reason':'KERNEL-POLICY-UNVERIFIED','blockers':['KERNEL-POLICY-UNVERIFIED'],
                   'source':selection['source']['id'],'target':selection['target']['id'],'mode':'continuous-pair','proof_scope':MODE})
        return True
    destination=role(state['policy_roles'],selection['order'])
    # Never rebuild the policy towards a source the vendor keeps rebuilding: the decision below leaves it.
    if destination=='source' and source_unstable(selection):return False
    if state.get('manual_hold') not in (None,destination):raise n.Refused('PAIR-MANUAL-HOLD-UNVERIFIED')
    recovery=normalized(settings);now=time.time()
    events,allowed=budget(effective_events(read_json(PERSIST/'pair-auto-budget.json',{'events':[]}),now),now,recovery['attempt_window']*60,recovery['attempt_limit'])
    if not allowed or events and now-events[-1]<max(recovery['cooldown'],recovery['min_dwell']):
        n.publish({'state':'BLOCKED','reason':'KERNEL-POLICY-UNVERIFIED','blockers':['KERNEL-POLICY-UNVERIFIED','PAIR-RATE-LIMIT'],
                   'source':selection['source']['id'],'target':selection['target']['id'],'mode':'continuous-pair','proof_scope':MODE})
        return True
    until=configure_lease(state)
    def charge_dispatched():
        require_running(revision);stamp=time.time()
        charged,permitted=budget(effective_events(read_json(PERSIST/'pair-auto-budget.json',{'events':[]}),stamp),stamp,recovery['attempt_window']*60,recovery['attempt_limit'])
        if not permitted or charged and stamp-charged[-1]<max(recovery['cooldown'],recovery['min_dwell']):raise n.Refused('PAIR-RATE-LIMIT')
        ledger_charge(charged,stamp)
    require_running(revision)
    n.attempt(backend,selection,until,False,control_revision=revision,pair_destination=destination,
              pair_session_order=state['order'],pair_reapply=True,on_dispatch=charge_dispatched)
    # Success was kernel-attested inside the child and again before COMMITTED.
    resume_running(state)
    return True


def publish_failure(error):
    """Expected recovery conflicts are observable states, never daemon exits."""
    import native_switch as n
    code = str(error) if isinstance(error, (str, n.Refused, ValueError)) and n.re.fullmatch('[A-Z][A-Z0-9_-]{0,95}', str(error)) else 'PAIR-SYSTEM-001'
    outside = None
    try:
        # K11 (formal model 03.11.2026): read and write under the control lock. The owner's Start hands a session HELD
        # by an outside change over under this lock (release_session: STOPPED); a HELD written from an older read
        # would undo that hand-over (the Start then refused PAIR-RECOVERY-REQUIRED). Lua: pair.publish_failure.
        from auto_control import control_lock
        with control_lock():
            pending = read_state()
            # review 04.11.2026 (finding 3): an unchanged HELD record is not written again on every pass
            if pending and pending['phase'] not in TERMINAL and (pending['phase'], pending.get('recovery_error')) != ('HELD', code):
                pending.update(phase='HELD', recovery_error=code)
                save(pending)
            # owner decision 07.11.2026: a hold decided by readopt_class is named with its class (never a value)
            if (pending and pending.get('phase') == 'HELD' and isinstance(pending.get('outside_change'), dict)
                    and pending['outside_change'].get('trigger') == code):
                outside = pending['outside_change']
    except (OSError, ValueError, KeyError, TypeError):
        pass  # Never overwrite an unreadable ownership record.
    value = {'state': 'BLOCKED', 'mode': 'continuous-pair', 'proof_scope': MODE,
             'original_restored': False, 'blockers': [code]}
    if outside is not None:
        value.update(reason=HOLD_CODE, outside_change=outside)
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
    from recovery_settings import normalized, return_rule
    from failover_plan import streak
    from channel_model import channel_failed, heartbeat_k, leave_rule, return_ready, name as failure_model
    from failure_diagnosis import diagnose
    request_row={}
    try:
        request_row = intent()
        state = read_state()
        running = request_row.get('mode') == 'on' and request_row.get('revision') == revision
        if not running and has_handover(state):
            # the journal stays as the old session left it until the Start: nothing else may finish it meanwhile
            if kept_valid({'kept_at':state['handover']['at']},state['handover'].get('tx')):return True
            release_handover(state)
            return True
        if not running and has_kept(state):
            if kept_valid(state,state.get('kept_tx')):return False  # the boot (or restart) resume's Start is still coming
            release_kept(backend,state)
            n.publish({'state': 'STOPPED', 'mode': 'continuous-pair', 'proof_scope': MODE, 'original_restored': True, 'blockers': []})
            return True
        relevant = running or state and state['phase'] not in TERMINAL
        if not relevant:
            if not running and state:_orphan_guard_safe(backend,state)  # review 04.11.2026 (finding 4)
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
            # Plan item 54: no new session while a package operation runs; the Start stays queued (a stale marker never
            # blocks: maintenance.py). Nothing was acquired or written. Lua: pair.tick.
            from auto_control import maintenance_blocker
            maintenance=maintenance_blocker()
            if maintenance:
                n.publish({'state':'ARMED','mode':'continuous-pair','proof_scope':MODE,'reason':maintenance,'blockers':[maintenance]})
                return True
            state = begin(backend, settings, request_row)
        backend.use_process_bindings(state['process_bindings'])
        if settings.get('pair_auto_mode')!=MODE:
            raise ValueError('PAIR-MODE-NOT-CONFIGURED')
        from pair_interfaces import state as state_interfaces
        rows=network()
        pending=state.get('server_change')
        if isinstance(pending,dict) and (pending.get('phase')=='APPLYING' or normalized_network(rows,state_interfaces(state))!=state['network_identity']
                                         or changed(state,configs(state_interfaces(state)))):
            # a change cut short in any phase (a crash, a rollback that raised after its uci writes): resolved before the checks
            server_resume(backend,state,revision);rows=network()
        if normalized_network(rows,state_interfaces(state))!=state['network_identity']:
            raise ValueError('PAIR-EXTERNAL-NETWORK-CHANGE')
        current_configs=configs(state_interfaces(state))
        if changed(state,current_configs):
            raise ValueError('PAIR-EXTERNAL-CONFIG-CHANGE')
        journal = n.journal_read()
        status = read_json(RUNTIME / 'status.json', {})
        from pair_manual import consume as consume_manual,held_reserve
        if 'server_change' in state:
            if server_pending(backend,state,settings,revision):return True  # this session's own server change (stages 2, 3)
            journal=n.journal_read()  # a finished change may have re-bound or completed the journal
        if consume_manual(backend,state,settings,revision):return True
        if revive(backend,state,revision,journal,rows):return True
        if held_reserve(backend,state,journal,settings,status):return True
        if server_start(backend,state,settings,revision,journal):return True
        observed={}
        if reapply_missing_policy(backend,state,settings,revision,journal,observed):return True
        kernel=observed.get('kernel')
        from pair_policy import current_role,state_order_matches
        applied_target=(journal.get('phase') in ('COMMITTED','HELD-ON-RESERVE')
                        or journal.get('activation_reapply') is True and journal.get('phase')=='ROLLED-BACK'
                        and journal.get('trial_nonce')==state['id']
                        and journal.get('control_revision')==state['revision']==revision)
        if applied_target and current_role(journal)!='source':
            now=time.time()
            decision = n.committed_recovery_decision(backend, journal, settings, status.get('samples', []), now, status, hold=ledger_hold(settings,now))
            if decision['action'] == 'RESTORE-PRIMARY':
                from pair_policy import metadata
                context=metadata(journal)
                progress=dict(journal,restore_before_order=list(kernel['order']),restore_before_verified=True) if kernel else journal
                fields=n.pair_event_fields(progress,restoring=True,restore_order=context['primary_order']) if context else {}
                n.publish(dict(fields,state='RESTORING',mode='continuous-pair',proof_scope=MODE,
                               source=journal['source'],target=journal['target'],reason=decision['reason'],blockers=[]))
                if n.finish_committed(backend, journal, decision['reason']):
                    final_kernel=backend.attest_policy() if context else None
                    if context:
                        if (final_kernel.get('verified') is not True or final_kernel.get('role')!='source'
                                or final_kernel.get('order')!=context['primary_order']):raise n.Refused('ROLLBACK-UNVERIFIED')
                        remember_selected(state,final_kernel)
                    resume_running(state)
                    fields=n.pair_event_fields(journal,completed=True,outcome='restored',restoring=True) if context else {}
                    n.publish(dict(fields,state='ROLLED-BACK',reason=decision['reason'],source=journal['source'],target=journal['target'],
                                   original_restored=backend.order()==(state['order'],state['policy_hash']),mode='continuous-pair',proof_scope=MODE,kernel_proof=final_kernel))
                else:
                    n.publish({'state':'DEGRADED-ON-RESERVE','reason':journal.get('reason','SOURCE-NOT-VERIFIED'),
                               'source':journal['source'],'target':journal['target'],'mode':'continuous-pair',
                               'proof_scope':MODE,'original_restored':False,'blockers':[]})
                # This decision has been handled. Its kernel/order snapshot is
                # obsolete after a restore, including a refused fresh health check.
                return True
            else:
                if decision.get('rebind'):reserve_rebound(backend,revision)  # finding 7
                resume_running(state)
                n.publish({'state': ('OBSERVING' if journal.get('activation_reapply') else 'COMMITTED') if decision['action']=='OBSERVE' else 'DEGRADED-ON-RESERVE',
                           'source': journal['source'], 'target': journal['target'], 'mode': 'continuous-pair',
                           'proof_scope':MODE,'readiness_verified':bool(kernel and kernel.get('verified') is True),
                           'kernel_policy_verified':bool(kernel and kernel.get('verified') is True),'kernel_proof':kernel,
                           'reason':'PAIR-WATCHING' if journal.get('activation_reapply') and decision['action']=='OBSERVE' else decision['reason'],'blockers':[]})
                return True
        blockers, selection = backend.diagnostic()
        if not blockers:busy_fields(backend,blockers,None)
        if blockers:
            if verify_gap_publish(state,blockers,backend):return True  # a short wait right after a confirmed pass
            preparing=(0<=time.time()-state['started']<=180 and all(x in('VENDOR-SETTLING','OBSERVATION-STALE','PROFILE-IDENTITY-CHANGED','RESERVE-NOT-CONNECTED')for x in blockers))
            value={'state': 'ARMED'if preparing else'BLOCKED', 'mode': 'continuous-pair', 'proof_scope': MODE,
                   'reason':'PAIR-WAITING-PROBES'if preparing else None,'blockers': blockers}
            # the page names the pair that waits; a manual switch still meets the same blocker in its transaction
            if 'VENDOR-WORKER-BUSY' in blockers and selection:value.update(source=selection['source']['id'],target=selection['target']['id'])
            n.publish(busy_fields(backend,blockers,value))
            return True
        if not state_order_matches(state,journal,backend.order()):
            raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
        resume_running(state)
        now = time.time()
        recovery = normalized(settings)
        from observation_freshness import valid_for
        age = valid_for(settings)
        # An unstable source (no healthy observation for the whole bounded window, across its vendor rebuilds)
        # is the failure evidence itself: its generation-scoped streak restarts on every rebuild.
        unstable = source_unstable(selection)
        # The owner's failure model (channel_model: 'hmm' default, 'hmm-fast', or 'consecutive' = the streak).
        beat = heartbeat_row() if heartbeat_k(settings) is not None else None
        rule = 'unstable' if unstable else leave_rule(status.get('samples', []), selection['source']['id'], recovery['failures'], now, age, settings, selection['source'], selection['target']['id'], beat)
        failed = rule is not None
        healthy = streak(status.get('samples', []), selection['target']['id'], recovery['successes'], now, age, True, selection['target'])
        diagnosis = diagnose(status, selection['source']['id'], now, settings)
        if unstable and diagnosis.get('suppress_switch'):diagnosis = dict(diagnosis, suppress_switch=False)
        ledger = read_json(PERSIST / 'pair-auto-budget.json', {'events': []})
        events, _ = budget(effective_events(ledger, now), now, recovery['attempt_window']*60, recovery['attempt_limit'])
        dwell = not events or now - events[-1] >= max(recovery['cooldown'], recovery['min_dwell'])
        # a failover the vendor aborted is retried after its short backoff (retry_wait), not after the cooldown
        retry_ready = retry_wait(ledger.get('aborted'), events, now, recovery) <= 0
        # The one return rule (recovery_settings.return_rule, Lua pair.return_rule): a healthy reserve is left only
        # after the damped stable window AND, in the HMM modes, channel_model.return_ready; a reserve that failed itself
        # after the rescue stability min(primary_stable, rescue_stable) without the model gate; otherwise primary_stable.
        on_reserve = bool(kernel and kernel.get('role')=='target' and not state.get('manual_hold')
                          and now-state.get('selected_policy',{}).get('since',now)>=recovery['min_dwell'] and dwell)
        # Owner decision 07.11.2026 (F-80), the path without an open journal (traffic on the reserve per selected_policy
        # after a boot or an accepted manual selection): hold_reserve means "do not return from a WORKING reserve". A
        # reserve the detector calls failed is probed once per RESCUE_PROBE_INTERVAL s of one failure episode (BH-06:
        # rescue_health, backend.health); only a FRESH NEGATIVE probe opens the rescue
        # rule (rescue_stable, no model gate, RESERVE-FAILED-PRIMARY-VERIFIED) through the same attempt, guards and
        # cooldown as the planned return; an unknown probe holds (RESERVE-HEALTH-UNKNOWN), an alive probe observes.
        # Twin: native_switch.committed_recovery_decision (journal path), Lua pair.lua tick.
        reserve_health, held = None, None
        if on_reserve and recovery['return_policy']!='healthy_primary' and not healthy and channel_failed(status.get('samples', []), selection['target']['id'], recovery['failures'], now, age, settings, selection['target']):
            reserve_health = rescue_health(backend, state, selection['target']['id'])
            if reserve_health is False: held = 'RESERVE-FAILED'
            elif reserve_health is None: held = 'RESERVE-HEALTH-UNKNOWN'
        else:
            RESCUE_PROBE.clear()  # BH-06: the failure episode ended, the next one probes at once
        returning = on_reserve and (recovery['return_policy']=='healthy_primary' or reserve_health is False)
        ready_settings, model_gate = settings, False
        if returning:
            reserve = ('planned' if healthy else 'failed' if reserve_health is False or channel_failed(status.get('samples', []), selection['target']['id'], recovery['failures'], now, age, settings, selection['target'])
                       else 'unknown')
            ready_settings, model_gate = return_rule(settings, reserve, return_hold(failover_events(events, ledger), now, recovery) if healthy else None)
        if (returning
                and (not model_gate or return_ready(status.get('samples', []), selection['source']['id'], recovery['primary_successes'], now, age, settings, selection['source']))
                and not n.key_unaccepted(selection['source']['id'])
                and backend.recovery_ready(selection['source']['id'],ready_settings) is True):
            until=configure_lease(state)
            blockers,fresh=backend.diagnostic()
            if blockers:raise ValueError('PAIR-READINESS-CHANGED')
            n.attempt(backend,fresh,until,False,control_revision=revision,pair_destination='source',pair_return=True,
                      pair_session_order=state['order'],on_dispatch=lambda:charge_attempt(settings,revision,limited=False,failover=False))
            return True
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
                       'reason':'RESERVE-ALREADY-FIRST','blockers':[],'kernel_proof':kernel,'kernel_policy_verified':bool(kernel and kernel.get('verified') is True)})
            return True
        # Leaving a failed primary is never blocked by the attempt limit (flap damping slows the return instead).
        if failed and healthy and dwell and retry_ready and not diagnosis.get('suppress_switch'):
            pinned=n.key_unaccepted(selection['target']['id'])
            if pinned:
                # the owner's option: the reserve is not trusted, the pair stays where it is until he accepts the key
                n.publish({'state':'BLOCKED','mode':'continuous-pair','proof_scope':MODE,'reason':pinned,'blockers':[pinned],
                           'source':selection['source']['id'],'target':selection['target']['id'],'source_failures':failed,'reserve_healthy':healthy,
                           'kernel_proof':kernel,'kernel_policy_verified':bool(kernel and kernel.get('verified') is True)})
                return True
            # late-switch recheck (see late_recheck); an unstable source is left on its instability as before
            evidence=evidence_code=None
            if not unstable:
                newest=newest_sample(status.get('samples',[]),selection['source']['id'],selection['source'])
                evidence=newest['time'] if newest is not None else None
                evidence_code=newest.get('code') if newest is not None else None
            decided=selection
            def late_abort(how):
                n.publish({'state': 'OBSERVING', 'mode': 'continuous-pair', 'readiness_verified': True,
                           'certified': False, 'proof_scope': MODE, 'external_lan_verified': False,
                           'source': decided['source']['id'], 'target': decided['target']['id'],
                           'vendor_identity':decided.get('vendor_identity'),'kernel_proof':kernel,
                           'kernel_policy_verified':bool(kernel and kernel.get('verified') is True),
                           'source_failures': failed, 'reserve_healthy': healthy,
                           'reason': LATE_RECHECK_CODE, 'late_recheck': how, 'blockers': []})
                return True
            if evidence is not None and same_evidence(LATE_ABORTS.get(selection['source']['id']),evidence):return late_abort('same-evidence')
            beat_run=beat.get('since') if rule=='heartbeat' and isinstance(beat,dict) else None
            if beat_run is not None and LATE_ABORTS.get(('beat',selection['source']['id']))==beat_run:return late_abort('same-run')
            parallel = recheck_begin(backend,decided,evidence_code,settings) if evidence is not None else None
            until = configure_lease(state)
            blockers, selection = backend.diagnostic()
            if blockers:
                raise ValueError('PAIR-READINESS-CHANGED')
            prepared = time.time()
            if evidence is not None:
                late=late_recheck(backend,decided,evidence,evidence_code,parallel)
                decision_timing(now,prepared,time.time(),rule,parallel is not None)
                if late:
                    LATE_ABORTS[decided['source']['id']]=evidence
                    if beat_run is not None:LATE_ABORTS[('beat',decided['source']['id'])]=beat_run
                    return late_abort(late[1])
            LATE_ABORTS.pop(decided['source']['id'],None);LATE_ABORTS.pop(('beat',decided['source']['id']),None)
            # the owner's hold ends only when the traffic really moves: a refuted decision leaves it (review 04.11.2026, finding 3)
            if state.get('manual_hold'):
                state.pop('manual_hold',None);save(state)
            charged=[]
            try:
                n.attempt(backend, selection, until, False,
                          probe_evidence={'source_streak_met': True, 'reserve_streak_met': True, 'failure_model': failure_model(settings), 'failure_rule': rule,
                                          'required_failures': recovery['failures'], 'required_successes': recovery['successes']},
                          control_revision=revision,pair_session_order=state['order'],on_dispatch=lambda:charged.append(charge_attempt(settings,revision,limited=False)))
            except n.Refused as error:
                # a vendor-aborted, rolled-back failover is not a switch (refund_abort); the error is still published
                if charged:
                    try:refund_abort(charged[0],str(error))
                    except (OSError,ValueError,KeyError,TypeError,AttributeError):pass  # unproven: the charge stays
                raise
        else:
            # held: the pinned reserve failed (fresh probe false, the primary not yet rescue_stable) or its probe is unknown
            n.publish({'state': 'DEGRADED-ON-RESERVE' if held else 'OBSERVING', 'mode': 'continuous-pair', 'readiness_verified': True,
                       'certified': False, 'proof_scope': MODE, 'external_lan_verified': False,
                       'source': selection['source']['id'], 'target': selection['target']['id'],
                       'vendor_identity':selection.get('vendor_identity'),'kernel_proof':kernel,
                       'kernel_policy_verified':bool(kernel and kernel.get('verified') is True),
                       'source_failures': failed, 'reserve_healthy': healthy,
                       'reason': held if held else diagnosis.get('code') if diagnosis.get('suppress_switch') else 'PAIR-RATE-LIMIT' if failed and healthy and not (dwell and retry_ready) else 'PAIR-MANUAL-HOLD-PRIMARY' if state.get('manual_hold')=='source' else 'PAIR-WATCHING',
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
        if str(error)=='BOOT-RESERVE-UNVERIFIED' and request_row.get('mode')=='on':
            try:fail_request(request_row,revision,error)  # the old session is HELD again; today's path follows
            except (n.Refused, OSError, ValueError, KeyError, TypeError):pass
            publish_failure(error)
            return True
        if pending.get('phase') == 'STARTING':
            try:
                cleanup(backend, pending)
                pending=read_state()
            except (n.Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                pending['phase'] = 'HELD'
                save(pending)
        # A failed Start before durable acquisition has no STARTING state to
        # finish. Consume its exact request; a newer Stop/Start cannot be lost.
        # A session that already ran is not switched off by one more error: it stays HELD and resumes by itself.
        if (str(error) in TRANSIENT_START and pending.get('phase') in (None,'STOPPED','FAILED') and request_row.get('mode')=='on'
                and 0<=time.time()-(request_row.get('time') or 0)<=TRANSIENT_START_SECONDS):
            # GL is still bringing tunnels up (typical right after an upgrade or reboot): keep the Start
            # queued and let the next tick rerun the full preflight. Nothing was acquired or written.
            n.publish({'state':'ARMED','mode':'continuous-pair','proof_scope':MODE,'reason':'PAIR-WAITING-VENDOR','blockers':[str(error)]})
            return True
        if (pending.get('phase') in (None,'STOPPED','FAILED') or pending.get('phase')=='HELD' and not pending.get('ran')) and request_row.get('mode')=='on':
            fail_request(request_row,revision,error)
        # Leave unverified ownership intact. Stop is independent of this code.
        publish_failure(error)
        # K9: not running (after a recovery, or the owner's Stop): the outside-change hold keeps or releases its guard
        if not (request_row.get('mode')=='on' and request_row.get('revision')==revision):_outside_hold_safe(backend)
    return True


# ---- best server inside a channel, stages 2 and 3 (server_pick.py; SERVER-PICK-DESIGN-2026-11-02.ru.md) ----------
# MT3000 02.11.2026: a server change of the idle reserve made outside the pair (uci route_policy + network,
# ifdown/ifup) was an external change for this session - PAIR-READOPTED, a 7.1 s LAN stall on the WORKING channel,
# HELD after three in 15 min. Now this supervisor makes the change itself, inside its control lock, and re-binds its
# own session to it (network_identity, protected route_policy digest, order, policy_hash, policy_roles,
# selected_policy and the journal): no external code, no readopt. The monitor job only measures and writes the
# hand-off (server_pick.CHANGE). The record state['server_change'] (phase APPLYING -> CONNECTING -> SETTLING, role)
# keeps the pair waiting (reason SERVER-CHANGING, no switch decision) at most CONNECT_WAIT s for the tunnel to pass the
# pair's own health check (DNS + HTTPS through it), else the previous server comes back the same way; then at most
# SETTLE_WAIT s for the monitor to observe the new profile.
# Stage 2 (role 'target'): the idle reserve while the traffic is on the primary and the pair rests.
# Stage 3 (role 'source', the owner's main scenario): the failed primary while the traffic is on the reserve after a
# completed automatic switch (journal COMMITTED). The open journal is re-bound too (server_pick.rebind): the normal
# return rules (committed_recovery_decision -> finish_committed -> rollback to the context's primary_order) then bring
# the traffic back to the primary on its new server - the return reads the journal's source id, so the recovery
# streaks and the fresh return check follow the new profile id. The carrying reserve is never touched. Both tunnels
# are bound by tunnel id (plan_source_tunnel / plan_target_tunnel), never by a profile id.
# A crash or power cut inside a change (any phase, or a rollback that raised after its uci writes) leaves the record:
# server_resume() adopts the live `from`, or `to` once its check passed (`verified`); an unverified `to` is restored
# to `from` unless its tunnel carries the traffic. It runs before the boot recovery compares the journal with the
# live order (native_switch.serve / auto.recover), in the cleanup and in tick before the external-change checks;
# anything else stays an external change. The Lua twin is lua/pair.lua (same names).
SERVER_IO=None  # tests: a fake server_pick io


def _server_io():
    if SERVER_IO is not None:return SERVER_IO
    import server_pick
    from agent import RUNTIME
    return server_pick.router_io(str(RUNTIME))


def _server_enabled(settings):return isinstance(settings,dict) and settings.get('server_pick') in ('1',True)


def server_interfaces(state,settings):
    """(source interface, reserve interface, the interfaces bound by their tunnel id: plan_source_tunnel and
    plan_target_tunnel, alpha27). A tunnel chosen by its profile id would lose its binding with the new server's id."""
    from pair_interfaces import state as state_interfaces
    managed=state_interfaces(state)
    anchored={}
    for role in ('source','target'):
        anchor=settings.get('plan_'+role+'_tunnel') if isinstance(settings,dict) else None
        kind,_,name=anchor.partition(':') if isinstance(anchor,str) else ('','','')
        protocol={'wgclient':'wireguard','ovpnclient':'openvpn'}.get(managed.get(name))
        if protocol is not None and kind==protocol:anchored[role]=name
    names=sorted(managed);source,target=anchored.get('source'),anchored.get('target')
    if source is None and target is not None:source=next(x for x in names if x!=target)
    if target is None and source is not None:target=next(x for x in names if x!=source)
    if source is None or source==target:return None,None,()
    return source,target,tuple(sorted(set(anchored.values())))


def _server_tunnel(pending):
    return {key:pending.get(key) for key in ('tunnel_id','protocol','section','interface')}


def server_network_delta_only(state,rows,managed,interface,protocol):
    """F-27: the live network may differ from the session's identity only in the selected interface's `config` naming
    the recorded from/to server (server_pick.network_config, this supervisor's own write). Any other difference - a LAN
    setting, another profile's interface - is somebody else's edit and is never absorbed into the baseline."""
    import server_pick as S
    identity=state.get('network_identity')
    if normalized_network(rows,managed)==identity:return True
    pending=state.get('server_change')
    if not isinstance(pending,dict):return False
    for side in ('from','to'):
        server=pending.get(side)
        config=S.network_config(protocol,server.get('group_id'),server.get('profile_id')) if isinstance(server,dict) else None
        if config is None:continue
        trial=copy.deepcopy(rows)
        for row in trial:
            if row.get('.name')==interface:row['config']=config
        if normalized_network(trial,managed)==identity:return True
    return False


def server_rebind(backend,state,interface,protocol,role='target'):
    """This supervisor's own server change adopted by the session (server_pick.rebind); ValueError when the live
    change is not only the changed tunnel's (the normal checks then see an external change). The journal is written
    before the session (rebind accepts a journal already re-bound)."""
    import native_switch as n
    import server_pick
    from pair_interfaces import state as state_interfaces
    managed=state_interfaces(state)
    rows=network()
    if not server_network_delta_only(state,rows,managed,interface,protocol):raise ValueError(server_pick.FAILED)
    config=next((row.get('config') for row in rows if row.get('.name')==interface),None)
    profile=(('openvpn:' if protocol=='openvpn' else 'wireguard:')+config) if isinstance(config,str) else None
    order,hash_=backend.order()
    updated,journal=server_pick.rebind(state,n.journal_read(),order,hash_,profile,role)
    updated['network_identity']=normalized_network(rows,managed)
    protected=updated.get('protected')
    if isinstance(protected,dict):
        # route_policy always; wireguard after GL's update_provider_config step (server_pick.PROVIDER_SCRIPT)
        names=[name for name in ('route_policy','wireguard') if name in protected and (name=='route_policy' or protocol=='wireguard')]
        if names:
            current=configs(managed)
            for name in names:protected[name]=current[name]
    if journal is not None:n.journal_write(journal)
    state.clear();state.update(updated);save(state)


def server_apply(backend,state,revision,tunnel,target,io,role='target',outcome=None):
    """One server change of an idle tunnel (stage 1's steps) under the control lock, the session re-bound before the
    lock is released. -> server_pick.PICKED, or FAILED (a failed step, or a change the session cannot explain).
    revision None: a resume outside a running Auto (boot, cleanup) - refused while any Auto intent is on.
    outcome (a dict, optional) gets server_pick.run_plan's changed/committed/touched and rebound (the session re-bound)."""
    import native_switch as n
    import server_pick
    from agent import RUNTIME
    from auto_control import control_lock,revision_locked
    plan=server_pick.switch_plan(tunnel,target,True,True,False,False,1)
    report=outcome if isinstance(outcome,dict) else {}
    report.update(changed=False,committed=False,touched=False,rebound=False)
    if plan['code'] is not None:return server_pick.FAILED
    with control_lock():
        current=intent()
        if revision is None:
            if current.get('mode')=='on':raise n.Refused('CLIENT-STOP')
        elif (revision_locked(RUNTIME)!=revision or current.get('mode')!='on' or current.get('revision')!=revision
                or current.get('id')!=state.get('id')):raise n.Refused('CLIENT-STOP')
        # F-27: the route_policy sections before the change; afterwards only the tunnel's own rule may differ, and
        # only in the server fields the plan writes (server_pick.policy_delta_only). The record's policy_before
        # (server_start, before the first write) is the baseline of the change AND of every rollback or resume
        # restore of it: a foreign edit that landed meanwhile fails the rollback too instead of being adopted.
        policy=getattr(backend,'policy',None)
        pending=state.get('server_change') if isinstance(state,dict) else None
        snapshot=pending.get('policy_before') if isinstance(pending,dict) else None
        if not isinstance(snapshot,list):
            try:snapshot=policy()['sections'] if callable(policy) else None
            except (OSError,ValueError,TypeError,KeyError,n.Refused):snapshot=None
        done=server_pick.run_plan(plan,io,True)
        report.update(changed=done['changed'],committed=done['committed'],touched=done['touched'])
        if callable(policy):
            try:live=policy()['sections']
            except (OSError,ValueError,TypeError,KeyError,n.Refused):live=None
            if snapshot is None or live is None or not server_pick.policy_delta_only(snapshot,live,tunnel.get('section')):return server_pick.FAILED
        try:server_rebind(backend,state,tunnel['interface'],tunnel['protocol'],role)
        except (ValueError,TypeError,KeyError):return server_pick.FAILED
        report['rebound']=True
    return done['code']


def _server_publish(state,kernel=None):
    import native_switch as n
    import server_pick
    roles=state.get('policy_roles') or {}
    n.publish({'state':'OBSERVING','mode':'continuous-pair','proof_scope':MODE,'reason':server_pick.CHANGING,
               'source':roles.get('source_id'),'target':roles.get('target_id'),'readiness_verified':bool(kernel and kernel.get('verified') is True),
               'kernel_policy_verified':bool(kernel and kernel.get('verified') is True),'kernel_proof':kernel,'blockers':[]})


def server_start(backend,state,settings,revision,journal):
    """Takes a valid hand-off of the monitor job when the gate allows it. True: this pass changed a server."""
    import native_switch as n
    import server_pick as S
    from pair_policy import state_order_matches
    if not _server_enabled(settings):return False
    io=_server_io()
    try:row=json.loads(io['read'](io['runtime']+'/'+S.CHANGE) or 'null')
    except (ValueError,TypeError):row=None
    now=time.time()
    try:taken=json.loads(io['read'](io['runtime']+'/'+S.STATE) or '{}')
    except (ValueError,TypeError):taken=None
    history=taken.get('changes') if isinstance(taken,dict) else None
    taken=taken.get('taken') if isinstance(taken,dict) else None
    if isinstance(row,dict) and S._stamp(taken) and S._stamp(row.get('time')) and row['time']<=taken:return False  # taken once
    claimed=S.claim(io,row,now)
    if claimed is None:return False
    tunnel=claimed['tunnel']
    source,reserve,anchors=server_interfaces(state,settings)
    kernel=backend.attest_policy()
    left,_=S.changes_left(history if isinstance(history,dict) else {},tunnel['tunnel_id'],now)
    gate={'enabled':True,'phase':state.get('phase'),'journal_phase':journal.get('phase'),'journal_manual':journal.get('manual_request_id') is not None,
          'kernel_verified':isinstance(kernel,dict) and kernel.get('verified') is True,
          'kernel_role':kernel.get('role') if isinstance(kernel,dict) else None,'interface':tunnel['interface'],
          'source_interface':source,'target_interface':reserve,'manual_hold':state.get('manual_hold'),
          'pending':'server_change' in state,'anchored':tunnel['interface'] in anchors,'busy':S.vendor_busy(tunnel['tunnel_id'],io),'left':left}
    code=S.gate(gate);role=S.role_of(gate)
    if code is None:
        # a server change waits for the owner's word on a key of either channel (attest_policy used to refuse it as a blocker)
        roles=state.get('policy_roles') or {}
        if n.key_unaccepted(roles.get('source_id'),roles.get('target_id')):code=S.DEFERRED
    if code is None:
        live=backend.order()
        # stage 2: the live order is the session's; stage 3: the COMMITTED journal's, with the session's context
        if role=='target' and live!=(state.get('order'),state.get('policy_hash')):code=S.DEFERRED
        if role=='source' and not state_order_matches(state,journal,live):code=S.DEFERRED
    if code is not None:
        if code in S.EVENT_CODES:S.event(io,code,tunnel,now,request=row['time'])
        return False
    change=S.project_change({'time':now,'from':row['from'],'to':row['to'],'from_ms':row.get('from_ms'),'to_ms':row.get('to_ms'),
                             'from_location':row.get('from_location'),'to_location':row.get('to_location')})
    if change is False:change={'time':now,'from':row['from'],'to':row['to'],'from_ms':None,'to_ms':None,'from_location':None,'to_location':None}
    target=dict(claimed['target'],id=S.profile_id(tunnel['protocol'],claimed['target']['group_id'],claimed['target']['profile_id']))
    pending=dict(_server_tunnel(tunnel),phase='APPLYING',role=role,**{'from':claimed['previous'],'to':target,'started':now,
                 'deadline':now+S.CONNECT_WAIT,'request':row['time'],'change':change})
    # F-27: the route_policy sections before the first write, the baseline of the change and of its rollback/resume
    policy=getattr(backend,'policy',None)
    try:before=policy()['sections'] if callable(policy) else None
    except (OSError,ValueError,TypeError,KeyError,n.Refused):before=None
    if isinstance(before,list):pending['policy_before']=before
    state['server_change']=pending;save(state)  # before the first write: a crash in between is seen by server_resume()
    S.record(io,tunnel['tunnel_id'],now,taken=row['time'])  # every attempt counts for the hourly limit; taken once
    first={}
    if server_apply(backend,state,revision,tunnel,target,io,role,first)==S.PICKED:
        state['server_change']=dict(pending,phase='CONNECTING')
    elif first['changed'] is False:
        # nothing was written (the first uci step failed): nothing to roll back, no change to wait for
        S.event(io,S.FAILED,tunnel,now,change,row['time'],S.NOT_CHANGED)
        state.pop('server_change',None);save(state)
        return False
    else:
        back={}
        undone=server_apply(backend,state,revision,tunnel,claimed['previous'],io,role,back)==S.PICKED
        S.event(io,S.FAILED,tunnel,now,change,row['time'],S.rollback_note(undone,first,back))
        state['server_change']=dict(pending,phase='SETTLING',deadline=now+S.SETTLE_WAIT,rolled_back=True)
    save(state)
    _server_publish(state,kernel)
    return True


def reserve_rebound(backend,revision,settled=False):
    """Finding 7: a vendor rebuild of the reserve proven by committed_recovery_decision (rebind). The open journal records
    the live generations and vendor_identity the way attempt() records them at a switch, so forward_resume, channel_path
    and a later rollback compare the live profiles. Both roles: the vendor rebuilds the primary as well (the incident
    did) and vendor_identity covers both. Fresh diagnostic with no blocker, the same stable identity for both roles, under
    the control lock against a Stop. settled: a manual primary hold, its journal may be ROLLED-BACK. True when the journal
    was updated; False leaves the next pass to try again."""
    import native_switch as n
    from auto_control import control_lock
    from failure_diagnosis import profile_identity
    try:
        blockers,selection=backend.diagnostic()
        if blockers or not isinstance(selection,dict):return False
        live={role:profile_identity(selection.get(role)) for role in ('source','target')}
        identity=selection.get('vendor_identity')
        if any(row is None for row in live.values()) or not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{64}',identity):return False
        with control_lock():
            n.require_control_revision(revision)
            journal=n.journal_read()
            proofs=journal.get('vendor_profiles')
            phases=('COMMITTED','HELD-ON-RESERVE','ROLLED-BACK') if settled else ('COMMITTED','HELD-ON-RESERVE')
            if journal.get('phase') not in phases or not isinstance(proofs,dict):return False
            if any(not isinstance(proofs.get(role),dict) or any(live[role].get(key)!=proofs[role].get(key) for key in n.RESERVE_STABLE)
                   for role in ('source','target')):return False
            if proofs==live and journal.get('vendor_identity')==identity:return False
            n.journal_write(dict(journal,vendor_profiles=live,vendor_identity=identity))
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):return False
    _log('PAIR-RESERVE-REBOUND: the vendor rebuilt %s; the journal follows its new generation'%live['target'].get('id'))
    return True


def server_settled(selection):
    """Stage 3: once the monitor observes the new primary profile (a clear diagnostic), the open COMMITTED journal
    records its vendor identity (vendor_profiles.source, vendor_identity) the way attempt() records it at a switch,
    so a later interrupted return compares the live profile, not the old server's. The reserve's recorded identity
    must be unchanged. True when the journal was updated."""
    import native_switch as n
    from failure_diagnosis import profile_identity
    try:journal=n.journal_read()
    except n.Refused:return False
    proofs=journal.get('vendor_profiles')
    if journal.get('phase')!='COMMITTED' or not isinstance(proofs,dict) or not isinstance(selection,dict):return False
    source=profile_identity(selection.get('source'));target=profile_identity(selection.get('target'))
    if source is None or source.get('id')!=journal.get('source') or target is None or target!=proofs.get('target'):return False
    identity=selection.get('vendor_identity')
    identity=identity if isinstance(identity,str) and re.fullmatch('[a-f0-9]{64}',identity) else journal.get('vendor_identity')
    if proofs.get('source')==source and journal.get('vendor_identity')==identity:return False
    updated=dict(journal,vendor_profiles=dict(proofs,source=source))
    if identity is not None:updated['vendor_identity']=identity
    n.journal_write(updated)
    return True


def _server_carrying(backend,pending):
    """At a resume: True unless the kernel proves the traffic on the other tunnel (an unknown route is carrying)."""
    try:kernel=backend.attest_policy()
    except Exception:return True  # noqa: BLE001 - any failure is an unknown route
    role=pending.get('role') or 'target'
    return not (isinstance(kernel,dict) and kernel.get('verified') is True and kernel.get('role') in ('source','target') and kernel['role']!=role)


def server_resume(backend,state,revision=None):
    """A server change record a crash, a power cut or a rollback that raised left behind (any phase). The live server
    of the tunnel (route_policy and network both - this supervisor's own writes) is adopted (server_rebind) when it is
    the recorded `from`, or `to` after its CONNECTING check passed (`verified`). An unverified `to` is restored to
    `from` (server_apply, as a timeout rollback; revision None outside a running Auto) unless its tunnel now carries
    the traffic (then adopted and logged); a failed restore adopts what is live. Anything else (a mixed state between
    the two uci commits, an unreadable rule) is left to the normal checks, which see an external change. The record is
    removed either way. Never raises. -> True when the session (and its journal) were re-bound."""
    import native_switch as n
    import server_pick as S
    pending=state.get('server_change') if isinstance(state,dict) else None
    if pending is None:return False
    adopted=None;note=''
    errors=(n.Refused,OSError,ValueError,KeyError,TypeError,AttributeError,subprocess.SubprocessError)
    def live_side(io,tunnel):
        live=S.live_server(io,tunnel)
        config=next((row.get('config') for row in network() if row.get('.name')==tunnel['interface']),None)
        return next((side for side in ('to','from') if isinstance(pending.get(side),dict) and live is not None
                     and live==(pending[side].get('group_id'),pending[side].get('profile_id'))
                     and config==S.network_config(tunnel['protocol'],pending[side].get('group_id'),pending[side].get('profile_id'))),None)
    try:
        io=_server_io();tunnel=_server_tunnel(pending);role=pending.get('role') or 'target'
        side=live_side(io,tunnel)
        if side=='to' and pending.get('verified') is not True:
            if not isinstance(pending.get('from'),dict) or _server_carrying(backend,pending):note=' (not verified; its tunnel carries the traffic)'
            else:
                try:code=server_apply(backend,state,revision,tunnel,pending['from'],io,role)
                except errors:code=None
                if code==S.PICKED:adopted,side,note='from',None,' (the new one was not verified: restored)'
                else:side,note=live_side(io,tunnel),' (the unverified new one could not be restored)'
        if side is not None:
            server_rebind(backend,state,tunnel['interface'],tunnel['protocol'],role)
            adopted=side
    except errors:adopted=None
    try:
        state.pop('server_change',None);save(state)
    except (OSError,ValueError,TypeError):pass
    _log('SERVER-PICK-RESUMED: %s'%('adopted the recorded '+adopted+' server'+note if adopted else 'not explainable; the normal checks decide'+note))
    return adopted is not None


def server_resume_boot(backend):
    """The supervisor start (native_switch.serve, before it compares a COMMITTED journal with the live order)."""
    try:state=read_state()
    except (OSError,ValueError):return False
    if not isinstance(state,dict) or 'server_change' not in state:return False
    boot_step('server change resume')
    return server_resume(backend,state)


def server_pending(backend,state,settings,revision):
    """While this supervisor's own server change is pending: True = this pass waited (no other decision)."""
    import server_pick as S
    pending=state.get('server_change')
    if pending is None:return False
    now=time.time()
    stamps=[pending.get(key) for key in ('started','deadline')] if isinstance(pending,dict) else []
    if isinstance(pending,dict) and pending.get('phase')=='APPLYING':
        server_resume(backend,state,revision)  # a crash inside the change (the supervisor restarted mid-way)
        return False
    if (not isinstance(pending,dict) or pending.get('phase') not in ('CONNECTING','SETTLING') or len(stamps)!=2
            or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in stamps)
            or not isinstance(pending.get('to'),dict) or not isinstance(pending.get('from'),dict)
            or pending.get('role','target') not in ('source','target')):
        state.pop('server_change',None);save(state)  # a damaged record: the normal checks decide
        return False
    io=_server_io();tunnel=_server_tunnel(pending);role=pending.get('role','target')
    within=pending['started']<=now<pending['deadline']
    if pending['phase']=='CONNECTING':
        if backend.health(pending['to'].get('id')) is True:
            S.record(io,pending['tunnel_id'],now,pending.get('change'),count=False)
            S.event(io,S.PICKED,tunnel,now,pending.get('change'),pending.get('request'))
            state['server_change']=dict(pending,phase='SETTLING',deadline=now+S.SETTLE_WAIT,verified=True);save(state)  # a resume keeps `to`
        elif not within:
            undone=server_apply(backend,state,revision,tunnel,pending['from'],io,role)==S.PICKED
            S.event(io,S.FAILED,tunnel,now,pending.get('change'),pending.get('request'),'rolled back' if undone else 'rollback failed')
            state['server_change']=dict(pending,phase='SETTLING',deadline=now+S.SETTLE_WAIT,rolled_back=True);save(state)
        _server_publish(state)
        return True
    blockers,selection=backend.diagnostic()
    if not blockers or not within:
        if not blockers and role=='source':
            try:server_settled(selection)
            except (ValueError,TypeError,KeyError,OSError):pass  # observation-grade: the return compares ids and orders
        state.pop('server_change',None);save(state)
        return False
    _server_publish(state)
    return True
