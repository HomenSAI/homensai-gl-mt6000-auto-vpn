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
                                           or x < 0 for x in events)):
        raise ValueError('PAIR-BUDGET-UNVERIFIED')
    events = [min(x, now) for x in events]
    if type(window)is not int or not 60<=window<=900 or type(limit)is not int or not 1<=limit<=10:
        raise ValueError('PAIR-BUDGET-UNVERIFIED')
    # Keep the whole maximum window so later policy changes cannot erase attempts.
    kept = sorted(x for x in events if now - x < 900)
    count=sum(now-x<window for x in kept)
    return kept, count < limit and len(kept)<16


# Flap damping (MT3000 flap test 02.11.2026, primary 60 s down / 120 s up): the rolling attempt limit used to
# block the FAILOVER, so after three switches traffic stayed on a dead primary while every recovery still
# returned after ~70 s. Like RFC 2439/7196 route-flap damping and BFD/VRRP hold-down, leaving a failed
# primary is never limited (only the cooldown spacing bounds retries of a failed attempt); the RETURN is
# damped instead. HOLD_CAP is the longest primary stability the settings allow (recovery_settings.RANGES).
HOLD_CAP = 600


def return_hold(events, now, recovery):
    """Seconds the primary must be stably healthy before Auto returns to it.

    Below the attempt limit it is primary_stable. The failover that reaches the limit within the rolling
    window, and every further one, doubles it (capped at HOLD_CAP); as failovers age out of the window
    the hold decays back. Twin: pair.lua M.return_hold (tests/flap_damping_cases.json)."""
    window=recovery['attempt_window']*60
    count=sum(1 for x in events if 0<=now-x<window)
    excess=count-recovery['attempt_limit']+1
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
    kept = sorted(min(x, now) for x in raw if type(x) in (int, float) and math.isfinite(x) and x >= 0 and now - x < 900)
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
    keeps the charge: the cooldown spacing then applies as before. True when refunded."""
    from agent import PERSIST, read_json, atomic_json
    import native_switch as n
    if code not in ABORT_REFUND_CODES or type(stamp) not in (int, float):return False
    journal = n.journal_read()
    started = journal.get('started')
    if (journal.get('phase') != 'ROLLED-BACK' or journal.get('failure_code') != code or journal.get('confirmed') is not None
            or journal.get('pair_transition') is None or type(started) not in (int, float) or started > stamp):
        return False
    ledger = read_json(PERSIST/'pair-auto-budget.json', {'events': []})
    events = ledger.get('events') if isinstance(ledger, dict) else None
    if not isinstance(events, list) or stamp not in events:return False
    now = time.time()
    events = list(events);events.remove(stamp)
    atomic_json(PERSIST/'pair-auto-budget.json', {'events': events, 'aborted': (abort_stamps(ledger.get('aborted'), now)+[now])[-ABORT_KEEP:]})
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
# Failures the short live probe cannot see: VPN-MTU (mtu_check.py, large packets lost) passes DNS + HTTPS with small
# packets, and Auto's live probes never run the large-packet check. With such evidence only a newer healthy monitor
# sample (the monitor re-runs that check on every probe after a black hole) may stop the failover.
PROBE_BLIND_CODES = frozenset({'VPN-MTU'})
# source id -> the newest source sample stamp a recheck contradicted (memory only): the same evidence never
# starts a second decision; the monitor's next sample of the source decides again.
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


def late_recheck(backend, selection, evidence, evidence_code=None):
    """The last look at the source before a failover commits: (code, how) or None. evidence_code: the code of the
    decision's newest source sample; a PROBE_BLIND_CODES failure is never contradicted by the live probe."""
    from agent import RUNTIME, read_json
    identifier=selection['source']['id']
    try:status=read_json(RUNTIME/'status.json',{})
    except (OSError,ValueError,TypeError):status={}
    if isinstance(status,dict) and monitor_recovered(status.get('samples',[]),identifier,evidence,time.time(),selection['source']):
        return LATE_RECHECK_CODE,'monitor'
    check=None if evidence_code in PROBE_BLIND_CODES else getattr(backend,'recheck',None)
    if check is not None:
        try:healthy=check(identifier,RECHECK_SECONDS)
        except Exception:healthy=None  # any failure of the last look goes on with the switch
        if healthy is True:return LATE_RECHECK_CODE,'probe'
    return None


def ledger_hold(settings, now):
    """return_hold from the persistent failover ledger; an unreadable ledger holds the longest."""
    from agent import PERSIST,read_json
    from recovery_settings import normalized
    recovery=normalized(settings)
    try:events,_=budget(read_json(PERSIST/'pair-auto-budget.json',{'events':[]}).get('events'),now,recovery['attempt_window']*60,recovery['attempt_limit'])
    except (ValueError,TypeError,AttributeError,OSError):return HOLD_CAP
    return return_hold(events,now,recovery)


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


def outside_guard_reset():_outside_guard.clear()


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
        raise ValueError('PAIR-EXTERNAL-POLICY-CHANGE')
    # K11 (formal model 03.11.2026): the owner's Start hands a session HELD by an outside change over under the control
    # lock (release_for_start / request -> release_session: archived, STOPPED). A cleanup pass that read the record
    # before must not write its STOPPING over that hand-over (Start then refused PAIR-RECOVERY-REQUIRED and the session
    # stayed HELD). The record is read again under the same lock: another session or a finished one (the hand-over's
    # STOPPED) - this pass ends without a write.
    from auto_control import control_lock
    with control_lock():
        current=read_state()
        ours=not current or current.get('id')==state.get('id') and (current.get('phase') not in TERMINAL or state.get('phase') in TERMINAL)
        if ours:
            state['phase']='STOPPING';save(state)  # Route restoration does not complete interface ownership cleanup.
    if not ours:
        boot_step('pair cleanup superseded by a hand-over')
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


def charge_attempt(settings,revision,limited=True):
    """Record a dispatched automatic switch. limited=False (leaving a failed path) ignores the attempt count:
    only the cooldown spacing applies; it bounds retries of a failed attempt (<=15 per 15 min, the ledger size)."""
    from agent import PERSIST,read_json,atomic_json
    from recovery_settings import normalized
    import native_switch as n
    require_running(revision);now=time.time();policy=normalized(settings)
    ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]})
    events,allowed=budget(ledger.get('events'),now,policy['attempt_window']*60,policy['attempt_limit'])
    aborted=abort_stamps(ledger.get('aborted'),now)
    if (limited and not allowed or events and now-events[-1]<max(policy['cooldown'],policy['min_dwell'])
            or retry_wait(aborted,events,now,policy)>0):raise n.Refused('PAIR-RATE-LIMIT')
    # 'aborted' is kept: a refund of this charge must still see the earlier aborts of the series (retry_wait)
    atomic_json(PERSIST/'pair-auto-budget.json',dict({'events':events+[now]},**({'aborted':aborted} if aborted else {})))
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
    from agent import PERSIST,read_json,atomic_json
    blockers,selection=backend.diagnostic()
    if blockers or not selection:
        identity=state['policy_roles']
        n.publish({'state':'BLOCKED','mode':'continuous-pair','proof_scope':MODE,'source':identity['source_id'],'target':identity['target_id'],
                   'blockers':blockers or ['PAIR-POLICY-UNVERIFIED'],'readiness_verified':False,'kernel_policy_verified':False})
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
    events,allowed=budget(read_json(PERSIST/'pair-auto-budget.json',{'events':[]}).get('events'),now,recovery['attempt_window']*60,recovery['attempt_limit'])
    if not allowed or events and now-events[-1]<max(recovery['cooldown'],recovery['min_dwell']):
        n.publish({'state':'BLOCKED','reason':'KERNEL-POLICY-UNVERIFIED','blockers':['KERNEL-POLICY-UNVERIFIED','PAIR-RATE-LIMIT'],
                   'source':selection['source']['id'],'target':selection['target']['id'],'mode':'continuous-pair','proof_scope':MODE})
        return True
    until=configure_lease(state)
    def charge_dispatched():
        require_running(revision);stamp=time.time()
        charged,permitted=budget(read_json(PERSIST/'pair-auto-budget.json',{'events':[]}).get('events'),stamp,recovery['attempt_window']*60,recovery['attempt_limit'])
        if not permitted or charged and stamp-charged[-1]<max(recovery['cooldown'],recovery['min_dwell']):raise n.Refused('PAIR-RATE-LIMIT')
        atomic_json(PERSIST/'pair-auto-budget.json',{'events':charged+[stamp]})
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
    try:
        # K11 (formal model 03.11.2026): read and write under the control lock. The owner's Start hands a session HELD
        # by an outside change over under this lock (release_session: STOPPED); a HELD written from an older read
        # would undo that hand-over (the Start then refused PAIR-RECOVERY-REQUIRED). Lua: pair.publish_failure.
        from auto_control import control_lock
        with control_lock():
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
    from recovery_settings import normalized, return_rule
    from failover_plan import streak
    from channel_model import channel_failed, return_ready, name as failure_model
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
                resume_running(state)
                n.publish({'state': ('OBSERVING' if journal.get('activation_reapply') else 'COMMITTED') if decision['action']=='OBSERVE' else 'DEGRADED-ON-RESERVE',
                           'source': journal['source'], 'target': journal['target'], 'mode': 'continuous-pair',
                           'proof_scope':MODE,'readiness_verified':bool(kernel and kernel.get('verified') is True),
                           'kernel_policy_verified':bool(kernel and kernel.get('verified') is True),'kernel_proof':kernel,
                           'reason':'PAIR-WATCHING' if journal.get('activation_reapply') and decision['action']=='OBSERVE' else decision['reason'],'blockers':[]})
                return True
        blockers, selection = backend.diagnostic()
        if blockers:
            preparing=(0<=time.time()-state['started']<=180 and all(x in('VENDOR-SETTLING','OBSERVATION-STALE','PROFILE-IDENTITY-CHANGED','RESERVE-NOT-CONNECTED')for x in blockers))
            n.publish({'state': 'ARMED'if preparing else'BLOCKED', 'mode': 'continuous-pair', 'proof_scope': MODE,
                       'reason':'PAIR-WAITING-PROBES'if preparing else None,'blockers': blockers})
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
        failed = unstable or channel_failed(status.get('samples', []), selection['source']['id'], recovery['failures'], now, age, settings, selection['source'])
        healthy = streak(status.get('samples', []), selection['target']['id'], recovery['successes'], now, age, True, selection['target'])
        diagnosis = diagnose(status, selection['source']['id'], now, settings)
        if unstable and diagnosis.get('suppress_switch'):diagnosis = dict(diagnosis, suppress_switch=False)
        ledger = read_json(PERSIST / 'pair-auto-budget.json', {'events': []})
        events, _ = budget(ledger.get('events'), now, recovery['attempt_window']*60, recovery['attempt_limit'])
        dwell = not events or now - events[-1] >= max(recovery['cooldown'], recovery['min_dwell'])
        # a failover the vendor aborted is retried after its short backoff (retry_wait), not after the cooldown
        retry_ready = retry_wait(ledger.get('aborted'), events, now, recovery) <= 0
        # The one return rule (recovery_settings.return_rule, Lua pair.return_rule): a healthy reserve is left only
        # after the damped stable window AND, in the HMM modes, channel_model.return_ready; a reserve that failed itself
        # after the rescue stability min(primary_stable, rescue_stable) without the model gate; otherwise primary_stable.
        returning = (kernel and kernel.get('role')=='target' and not state.get('manual_hold') and recovery['return_policy']=='healthy_primary'
                     and now-state.get('selected_policy',{}).get('since',now)>=recovery['min_dwell'] and dwell)
        ready_settings, model_gate = settings, False
        if returning:
            reserve = ('planned' if healthy else 'failed' if channel_failed(status.get('samples', []), selection['target']['id'], recovery['failures'], now, age, settings, selection['target'])
                       else 'unknown')
            ready_settings, model_gate = return_rule(settings, reserve, return_hold(events, now, recovery) if healthy else None)
        if (returning
                and (not model_gate or return_ready(status.get('samples', []), selection['source']['id'], recovery['primary_successes'], now, age, settings, selection['source']))
                and backend.recovery_ready(selection['source']['id'],ready_settings) is True):
            until=configure_lease(state)
            blockers,fresh=backend.diagnostic()
            if blockers:raise ValueError('PAIR-READINESS-CHANGED')
            n.attempt(backend,fresh,until,False,control_revision=revision,pair_destination='source',pair_return=True,
                      pair_session_order=state['order'],on_dispatch=lambda:charge_attempt(settings,revision,limited=False))
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
            if state.get('manual_hold'):
                state.pop('manual_hold',None);save(state)
            until = configure_lease(state)
            blockers, selection = backend.diagnostic()
            if blockers:
                raise ValueError('PAIR-READINESS-CHANGED')
            if evidence is not None:
                late=late_recheck(backend,decided,evidence,evidence_code)
                if late:
                    LATE_ABORTS[decided['source']['id']]=evidence
                    return late_abort(late[1])
            LATE_ABORTS.pop(decided['source']['id'],None)
            charged=[]
            try:
                n.attempt(backend, selection, until, False,
                          probe_evidence={'source_streak_met': True, 'reserve_streak_met': True, 'failure_model': failure_model(settings),
                                          'required_failures': recovery['failures'], 'required_successes': recovery['successes']},
                          control_revision=revision,pair_session_order=state['order'],on_dispatch=lambda:charged.append(charge_attempt(settings,revision,limited=False)))
            except n.Refused as error:
                # a vendor-aborted, rolled-back failover is not a switch (refund_abort); the error is still published
                if charged:
                    try:refund_abort(charged[0],str(error))
                    except (OSError,ValueError,KeyError,TypeError,AttributeError):pass  # unproven: the charge stays
                raise
        else:
            n.publish({'state': 'OBSERVING', 'mode': 'continuous-pair', 'readiness_verified': True,
                       'certified': False, 'proof_scope': MODE, 'external_lan_verified': False,
                       'source': selection['source']['id'], 'target': selection['target']['id'],
                       'vendor_identity':selection.get('vendor_identity'),'kernel_proof':kernel,
                       'kernel_policy_verified':bool(kernel and kernel.get('verified') is True),
                       'source_failures': failed, 'reserve_healthy': healthy,
                       'reason': diagnosis.get('code') if diagnosis.get('suppress_switch') else 'PAIR-RATE-LIMIT' if failed and healthy and not (dwell and retry_ready) else 'PAIR-MANUAL-HOLD-PRIMARY' if state.get('manual_hold')=='source' else 'PAIR-WATCHING',
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


def server_rebind(backend,state,interface,protocol,role='target'):
    """This supervisor's own server change adopted by the session (server_pick.rebind); ValueError when the live
    change is not only the changed tunnel's (the normal checks then see an external change). The journal is written
    before the session (rebind accepts a journal already re-bound)."""
    import native_switch as n
    import server_pick
    from pair_interfaces import state as state_interfaces
    managed=state_interfaces(state)
    rows=network()
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
        done=server_pick.run_plan(plan,io,True)
        report.update(changed=done['changed'],committed=done['committed'],touched=done['touched'])
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
