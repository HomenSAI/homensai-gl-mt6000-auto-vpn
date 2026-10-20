"""One-shot operator requests. Only the existing native supervisor applies routes.

This RAM queue never enables Auto, creates a certificate, starts a tunnel or
changes UCI. Its acknowledgement proves a request, never traffic completion.
"""
import math
import re
import subprocess
import time
import uuid

PENDING = frozenset(('QUEUED', 'CLAIMED', 'APPLYING', 'WAIT-CLIENT'))
STATES = PENDING | frozenset(('COMPLETED', 'REFUSED', 'CANCELLED', 'UNCONFIRMED'))
FIELDS = frozenset(('schema', 'state', 'direction', 'request_id', 'control_revision',
    'requested_at', 'updated_at', 'trial', 'until', 'source_id', 'target_id',
    'transaction_id', 'selection_hash', 'vendor_identity', 'settings_hash', 'code'))


def _hex(value, size=32):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{%d}' % size, value) is not None


def _stamp(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def valid_record(record):
    if not isinstance(record, dict) or set(record) != FIELDS:
        return False
    return (type(record['schema']) is int and record['schema'] == 1
        and isinstance(record['state'], str) and record['state'] in STATES
        and isinstance(record['direction'], str) and record['direction'] in ('reserve', 'primary')
        and _hex(record['request_id']) and _hex(record['control_revision'])
        and _stamp(record['requested_at']) and _stamp(record['updated_at'])
        and record['updated_at'] >= record['requested_at']
        and _stamp(record['until']) and record['until'] > record['requested_at']
        and isinstance(record['trial'], str) and bool(record['trial'])
        and all(isinstance(record[k], str) and 0 < len(record[k]) <= 128
                for k in ('source_id', 'target_id'))
        and record['source_id'] != record['target_id']
        and (record['transaction_id'] is None or _hex(record['transaction_id']))
        and all(_hex(record[k], 64) for k in ('selection_hash', 'vendor_identity', 'settings_hash'))
        and (record['code'] is None or isinstance(record['code'], str)
             and re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}', record['code']) is not None))


def refusal(*codes):
    return {'accepted': False, 'queued': False, 'completed': False,
            'blockers': sorted(set(codes))}


def validate_arguments(direction, control_revision):
    if direction not in ('reserve', 'primary') or not isinstance(direction, str):
        return 'MANUAL-DIRECTION-INVALID'
    if not _hex(control_revision):
        return 'CONTROL-REVISION-STALE'
    return None


def claim_reason(record, settings, revision, stopped, now):
    """Pure final fence; a stopped, expired or already claimed request never runs."""
    if not valid_record(record):
        return 'MANUAL-STATE-UNVERIFIED'
    if record['state'] != 'QUEUED':
        return 'MANUAL-ALREADY-CLAIMED'
    if not _stamp(now) or not record['requested_at'] <= now <= record['requested_at'] + 60:
        return 'MANUAL-REQUEST-EXPIRED'
    if revision != record['control_revision']:
        return 'CONTROL-REVISION-STALE'
    from auto_control import valid_stop
    if not valid_stop(stopped) or stopped.get('control_revision_failed') is True:
        return 'MANUAL-STATE-UNVERIFIED'
    if stopped.get('requested', 0) >= record['requested_at']:
        return 'STOP-SUPERSEDED-MANUAL'
    if not isinstance(settings, dict):
        return 'MANUAL-STATE-UNVERIFIED'
    if settings.get('monitor_only') not in (None, '0'):
        return 'MONITOR-ONLY-DEPLOYMENT'
    if record['direction'] == 'reserve':
        from native_switch import deadline, Refused
        try:
            until = deadline(settings.get('native_until'))
        except (Refused, TypeError, ValueError):
            return 'BOUNDED-DEADLINE-REQUIRED'
        if not now < until == record['until']:
            return 'BOUNDED-DEADLINE-REQUIRED'
        if settings.get('native_trial') != record['trial']:
            return 'MANUAL-CONFIG-CHANGED'
    if (settings.get('plan_source') != record['source_id']
            or settings.get('plan_target') != record['target_id']):
        return 'MANUAL-CONFIG-CHANGED'
    return None


def _preflight(direction, settings, blockers, selection, journal, state, auto,
               stopped, certificate, consumed, now):
    """Shared eligibility for request and read-only controls; no route probes."""
    from auto_control import readiness, effective_intent, valid_stop
    reasons = list(blockers)
    if any(not isinstance(row, dict) for row in (settings, journal, state, auto, stopped)):
        return ['MANUAL-STATE-UNVERIFIED']
    if settings.get('monitor_only') not in (None, '0'):
        reasons.append('MONITOR-ONLY-DEPLOYMENT')
    if not _stamp(state.get('time')) or not 0 <= now-state['time'] <= 30:
        reasons.append('MANUAL-SUPERVISOR-UNAVAILABLE')
    if not valid_stop(stopped) or stopped.get('control_revision_failed') is True:
        reasons.append('MANUAL-STATE-UNVERIFIED')
    if effective_intent(settings, stopped, auto, now)[0]:
        reasons.append('MANUAL-STOP-AUTO-FIRST')
    if auto.get('mode') not in (None, 'on', 'off'):
        reasons.append('MANUAL-STATE-UNVERIFIED')
    if not isinstance(selection, dict):
        reasons.append('MANUAL-SELECTION-UNVERIFIED')
    if reasons:
        return sorted(set(reasons))
    if direction == 'reserve':
        if journal.get('phase') not in (None, 'ROLLED-BACK'):
            return ['TRANSACTION-IN-PROGRESS']
        reasons = readiness(settings, certificate, consumed, selection, [], now)
        if (not isinstance(certificate, dict)
                or certificate.get('vendor_identity') != selection.get('vendor_identity')
                or not _hex(selection.get('vendor_identity'), 64)):
            reasons.append('LAN-TRIAL-REQUIRED')
        return sorted(set(reasons))
    if (journal.get('phase') not in ('COMMITTED', 'HELD-ON-RESERVE')
            or not _hex(journal.get('tx'))
            or journal.get('source') != selection.get('source', {}).get('id')
            or journal.get('target') != selection.get('target', {}).get('id')):
        return ['RETURN-NOT-APPLICABLE']
    return []


def request(direction, control_revision):
    from agent import RUNTIME, PERSIST, read_json, atomic_json
    from auto_control import control_lock, revision_locked, readiness, effective_intent
    from native_switch import Linux, journal_read, deadline, Refused
    invalid = validate_arguments(direction, control_revision)
    if invalid:
        return refusal(invalid)
    arrived = time.time()
    try:
        with control_lock():
            if control_revision != revision_locked(RUNTIME):
                return refusal('CONTROL-REVISION-STALE')
        # Slow diagnostics do not hold Stop's lock. A later Stop invalidates
        # this request at the second fence before anything is queued.
        backend = Linux()
        policy = backend.policy()
        settings = policy['settings']
        blockers, selection = backend.diagnostic()
        journal = journal_read()
        state = read_json(RUNTIME/'native-status.json', {})
        auto = read_json(RUNTIME/'auto-control.json', {})
        stopped = read_json(PERSIST/'native-stop.json', {})
        reasons = _preflight(direction, settings, blockers, selection, journal, state,
            auto, stopped, read_json(PERSIST/'native-certificate.json', {}),
            read_json(PERSIST/'native-attempts.json', {}), time.time())
        if reasons:
            return refusal(*reasons)
        with control_lock():
            if control_revision != revision_locked(RUNTIME):
                return refusal('CONTROL-REVISION-STALE')
            current_policy = backend.policy()
            current_journal = journal_read()
            current_stop = read_json(PERSIST/'native-stop.json', {})
            current_auto = read_json(RUNTIME/'auto-control.json', {})
            if current_policy != policy or current_journal != journal:
                return refusal('MANUAL-CONFIG-CHANGED')
            if current_stop != stopped or current_auto != auto:
                return refusal('STOP-SUPERSEDED-MANUAL')
            prior = read_json(RUNTIME/'manual-control.json', {})
            if prior != {} and not valid_record(prior):
                return refusal('MANUAL-STATE-UNVERIFIED')
            if prior and prior['state'] in PENDING and prior['control_revision'] == control_revision:
                return refusal('MANUAL-REQUEST-PENDING')
            now = time.time()
            until = deadline(settings.get('native_until')) if direction == 'reserve' else now + 60
            if not arrived <= now < until <= now + 14400:
                return refusal('BOUNDED-DEADLINE-REQUIRED')
            revision = revision_locked(RUNTIME, rotate=True)
            record = {'schema': 1, 'state': 'QUEUED', 'direction': direction,
                'request_id': uuid.uuid4().hex, 'control_revision': revision,
                'requested_at': now, 'updated_at': now, 'until': until,
                'trial': settings.get('native_trial') or journal.get('trial_nonce') or 'recovery',
                'source_id': selection['source']['id'], 'target_id': selection['target']['id'],
                'transaction_id': journal.get('tx') if direction == 'primary' else None,
                'selection_hash': selection.get('hash'), 'vendor_identity': selection.get('vendor_identity'),
                'settings_hash': selection.get('settings_hash'), 'code': None}
            if not valid_record(record):
                return refusal('MANUAL-SELECTION-UNVERIFIED')
            atomic_json(RUNTIME/'manual-control.json', record)
            return {'accepted': True, 'queued': True, 'completed': False,
                    'request_id': record['request_id'], 'control_revision': revision}
    except Refused:
        return refusal('MANUAL-STATE-UNVERIFIED')
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
        return refusal('MANUAL-REQUEST-UNCONFIRMED')


def claim_pending(settings, revision, stopped, now=None, runtime=None):
    """Supervisor only: durably claim once before invoking the native attempt.

    The supervisor still rechecks diagnostics/certification and owns the native
    transaction lock. A crash after CLAIMED is never replayed as QUEUED.
    """
    from agent import RUNTIME, read_json, atomic_json
    from auto_control import control_lock, revision_locked
    runtime = runtime or RUNTIME
    now = time.time() if now is None else now
    with control_lock(runtime):
        record = read_json(runtime/'manual-control.json', {})
        if record == {}:
            return None, None
        current_revision = revision_locked(runtime)
        if (valid_record(record) and record['state'] in PENDING
                and record['control_revision'] != current_revision):
            record.update(state='CANCELLED', updated_at=max(now, record['requested_at']),
                          code='CONTROL-REVISION-STALE')
            atomic_json(runtime/'manual-control.json', record)
            return None, 'CONTROL-REVISION-STALE'
        reason = claim_reason(record, settings,
                              current_revision if revision == current_revision else None,
                              stopped, now)
        if reason:
            if valid_record(record) and record['state'] == 'QUEUED':
                record.update(state='CANCELLED' if reason in
                    ('CONTROL-REVISION-STALE', 'STOP-SUPERSEDED-MANUAL') else 'REFUSED',
                    updated_at=max(now, record['requested_at']), code=reason)
                atomic_json(runtime/'manual-control.json', record)
            return None, reason
        record.update(state='CLAIMED', updated_at=now)
        atomic_json(runtime/'manual-control.json', record)
        return record, None


def publish_result(request_id, state, code=None, tx=None, runtime=None):
    from agent import RUNTIME, read_json, atomic_json
    from auto_control import control_lock
    runtime = runtime or RUNTIME
    if not _hex(request_id) or state not in STATES or state == 'QUEUED':
        raise ValueError('MANUAL-RESULT-INVALID')
    if code is not None and (not isinstance(code, str) or not re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}', code)):
        raise ValueError('MANUAL-RESULT-INVALID')
    if tx is not None and not _hex(tx):
        raise ValueError('MANUAL-RESULT-INVALID')
    with control_lock(runtime):
        record = read_json(runtime/'manual-control.json', {})
        if not valid_record(record) or record['request_id'] != request_id:
            return False
        if record['state'] not in PENDING:
            return False
        # A mere queue acknowledgement is not allowed to report completion.
        if state == 'COMPLETED' and (record['state'] == 'QUEUED' or tx is None):
            raise ValueError('MANUAL-COMPLETION-UNVERIFIED')
        record.update(state=state, updated_at=max(time.time(), record['requested_at']), code=code)
        if tx is not None:
            record['transaction_id'] = tx
        atomic_json(runtime/'manual-control.json', record)
        return True


def public_status(runtime=None):
    from agent import RUNTIME, read_json
    runtime = runtime or RUNTIME
    try:
        record = read_json(runtime/'manual-control.json', {})
    except (OSError, ValueError):
        return {'state': 'UNCONFIRMED', 'completed': False, 'code': 'MANUAL-STATE-UNVERIFIED'}
    if record == {}:
        return {'state': 'IDLE', 'completed': False}
    if not valid_record(record):
        return {'state': 'UNCONFIRMED', 'completed': False, 'code': 'MANUAL-STATE-UNVERIFIED'}
    return dict({key: record[key] for key in ('state', 'direction', 'request_id',
        'requested_at', 'updated_at', 'source_id', 'target_id', 'transaction_id', 'code')},
        completed=record['state'] == 'COMPLETED')


def control_status():
    """Read-only control eligibility. Diagnostic blockers never grant a bypass."""
    from agent import RUNTIME, PERSIST, read_json
    from auto_control import current_revision
    from native_switch import Linux, journal_read, Refused
    now = time.time()
    result = {'time': now, 'control_revision': None, 'available': False,
              'blockers': ['MANUAL-STATE-UNVERIFIED']}
    try:
        backend = Linux()
        settings = backend.policy()['settings']
        state = read_json(RUNTIME/'native-status.json', {})
        # No native supervisor runs in monitor-only deployments. Avoid the
        # heavier diagnostic entirely when this cheap gate already refuses.
        if isinstance(settings, dict) and settings.get('monitor_only') not in (None, '0'):
            reasons = ['MONITOR-ONLY-DEPLOYMENT']
            result.update(blockers=reasons, reserve={'allowed': False, 'blockers': reasons},
                          primary={'allowed': False, 'blockers': reasons})
            return result
        revision = current_revision()
        blockers, selection = backend.diagnostic()
        journal = journal_read()
        auto = read_json(RUNTIME/'auto-control.json', {})
        stopped = read_json(PERSIST/'native-stop.json', {})
        certificate = read_json(PERSIST/'native-certificate.json', {})
        consumed = read_json(PERSIST/'native-attempts.json', {})
        pending = read_json(RUNTIME/'manual-control.json', {})
        extra = []
        if pending != {} and not valid_record(pending):
            extra = ['MANUAL-STATE-UNVERIFIED']
        elif pending and pending['state'] in PENDING and pending['control_revision'] == revision:
            extra = ['MANUAL-REQUEST-PENDING']
        for direction in ('reserve', 'primary'):
            reasons = sorted(set(extra + _preflight(direction, settings, blockers, selection,
                journal, state, auto, stopped, certificate, consumed, now)))
            result[direction] = {'allowed': not reasons, 'blockers': reasons}
        result.update(control_revision=revision,
            available=result['reserve']['allowed'] or result['primary']['allowed'],
            blockers=[] if result['reserve']['allowed'] or result['primary']['allowed'] else
                     sorted(set(result['reserve']['blockers'] + result['primary']['blockers'])))
    except (Refused, OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
        result.update(reserve={'allowed': False, 'blockers': ['MANUAL-STATE-UNVERIFIED']},
                      primary={'allowed': False, 'blockers': ['MANUAL-STATE-UNVERIFIED']})
    return result
