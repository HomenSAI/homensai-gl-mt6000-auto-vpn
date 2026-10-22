"""Supervisor-only consumption of one explicit, certified manual request."""
import subprocess
import math
import re
import time


def _confirmed_return(record, result, journal, live_order, now):
    """Correlate the exact reply with the restored live transaction, not old OK."""
    def stamp(value):
        try:return type(value) in (int, float) and math.isfinite(value)
        except OverflowError:return False
    return (isinstance(result, dict) and result.get('ok') is True
        and result.get('code') == 'RETURNED'
        and result.get('request') == record['requested_at']
        and stamp(result.get('time')) and record['requested_at'] <= result['time'] <= now
        and journal.get('tx') == record['transaction_id']
        and journal.get('phase') == 'ROLLED-BACK'
        and journal.get('source') == record['source_id']
        and journal.get('target') == record['target_id']
        and live_order == (journal.get('before'), journal.get('hash')))


def _confirmed_reserve(record, journal, live_order):
    return (record['direction'] == 'reserve'
        and journal.get('manual_request_id') == record['request_id']
        and journal.get('phase') == 'HELD-ON-RESERVE' and journal.get('confirmed')
        and journal.get('source') == record['source_id']
        and journal.get('target') == record['target_id']
        and journal.get('hash') == record['selection_hash']
        and journal.get('vendor_identity') == record['vendor_identity']
        and journal.get('started', 0) >= record['requested_at']
        and journal.get('confirmed', 0) >= journal.get('started', 0)
        and live_order == (journal.get('after'), journal.get('hash')))


def consume(backend, settings, revision, stopped, runtime=None, persist=None):
    from agent import RUNTIME, PERSIST, read_json, atomic_json
    from auto_control import readiness, effective_intent
    from manual_control import claim_pending, publish_result
    from native_switch import (Refused, journal_read, require_control_revision,
        progress_read, attempt, handle_return, deadline)
    runtime = RUNTIME if runtime is None else runtime
    persist = PERSIST if persist is None else persist
    pending = read_json(runtime/'manual-control.json', {})
    # An ordinary supervisor tick must not create a control directory, lock or
    # revision just to discover that there is no request. Terminal requests
    # likewise need no claim or write. A malformed record still fails closed
    # inside the serialized claimant.
    if pending == {} or isinstance(pending, dict) and pending.get('state') in (
            'COMPLETED', 'REFUSED', 'CANCELLED', 'UNCONFIRMED'):
        return False
    record, reason = claim_pending(settings, revision, stopped, runtime=runtime)
    if record is None:
        return False
    request_id = record['request_id']
    def publish(state, **kwargs):
        return publish_result(request_id, state, runtime=runtime, **kwargs)
    try:
        require_control_revision(record['control_revision'])
        current = backend.policy()['settings']
        blockers, selection = backend.diagnostic()
        if blockers or not isinstance(selection, dict):
            raise Refused(blockers[0] if blockers else 'MANUAL-SELECTION-UNVERIFIED')
        if (selection.get('hash') != record['selection_hash']
                or selection.get('settings_hash') != record['settings_hash']
                or selection.get('vendor_identity') != record['vendor_identity']
                or selection.get('source', {}).get('id') != record['source_id']
                or selection.get('target', {}).get('id') != record['target_id']):
            raise Refused('MANUAL-CONFIG-CHANGED')
        auto = read_json(runtime/'auto-control.json', {})
        stopped = read_json(persist/'native-stop.json', {})
        if effective_intent(current, stopped, auto, time.time())[0]:
            raise Refused('MANUAL-STOP-AUTO-FIRST')
        require_control_revision(record['control_revision'])
        journal = journal_read()
        if record['direction'] == 'primary':
            if journal.get('tx') != record['transaction_id']:
                raise Refused('RETURN-TRANSACTION-MISMATCH')
            publish('APPLYING', tx=journal['tx'])
            handled, _ = handle_return(backend, journal,
                {'time': record['requested_at'], 'tx': record['transaction_id']}, 0,
                control_revision=record['control_revision'])
            result = read_json(runtime/'native-return-result.json', {})
            restored = journal_read()
            if not handled or not _confirmed_return(record, result, restored, backend.order(), time.time()):
                code = result.get('code') if isinstance(result, dict) else None
                raise Refused(code if isinstance(code, str) and code != 'RETURNED' else 'RETURN-UNCONFIRMED')
            publish('COMPLETED', tx=journal['tx'])
            return True
        if journal.get('phase') not in (None, 'ROLLED-BACK'):
            raise Refused('TRANSACTION-IN-PROGRESS')
        if deadline(current.get('native_until')) != record['until']:
            raise Refused('MANUAL-CONFIG-CHANGED')
        attempts_path = persist/'native-attempts.json'
        consumed = progress_read(attempts_path, 'attempts')
        certificate = read_json(persist/'native-certificate.json', {})
        reasons = readiness(current, certificate, consumed, selection, [], time.time())
        if (not isinstance(certificate, dict)
                or certificate.get('vendor_identity') != selection.get('vendor_identity')
                or current.get('native_trial') != record['trial']):
            reasons.append('LAN-TRIAL-REQUIRED')
        if reasons:
            raise Refused(reasons[0])
        # Consume the shared bounded attempt budget before dispatch; a crash
        # never resets it and no automatic retry of this request is permitted.
        require_control_revision(record['control_revision'])
        consumed.update(until=record['until'],trial=record['trial'],
            count=consumed.get('count',0)+1,time=time.time())
        atomic_json(attempts_path, consumed)
        publish('APPLYING')
        attempt(backend, selection, record['until'], False,
                control_revision=record['control_revision'], manual_request_id=request_id)
        journal = journal_read()
        if not _confirmed_reserve(record, journal, backend.order()):
            raise Refused('MANUAL-COMPLETION-UNVERIFIED')
        publish('COMPLETED', tx=journal['tx'])
    except (Refused, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as error:
        text = str(error) if isinstance(error, Refused) else ''
        code = text if re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}', text) else 'MANUAL-RESULT-UNCONFIRMED'
        publish('REFUSED' if isinstance(error, Refused) else 'UNCONFIRMED', code=code)
    return True


def recover_pending(backend, runtime=None, persist=None):
    """Report interrupted claimed work; never replay it after supervisor death."""
    from agent import RUNTIME, read_json
    from manual_control import valid_record, publish_result
    from native_switch import journal_read
    runtime = RUNTIME if runtime is None else runtime
    # persist is accepted alongside runtime so the native caller supplies one
    # explicit scope; this read-only recovery needs only its existing journal.
    record = read_json(runtime/'manual-control.json', {})
    if not valid_record(record) or record['state'] not in ('CLAIMED','APPLYING','WAIT-CLIENT'):
        return
    journal = journal_read()
    verified = _confirmed_reserve(record, journal, backend.order())
    publish_result(record['request_id'], 'COMPLETED' if verified else 'UNCONFIRMED',
        tx=journal.get('tx') if verified else None,
        code=None if verified else 'MANUAL-SUPERVISOR-RECOVERED', runtime=runtime)
