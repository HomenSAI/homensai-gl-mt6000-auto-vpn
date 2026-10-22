"""Display confirmed general VPN path; request acknowledgements are not proof.

Only a client-confirmed transaction, unchanged live policy order and fresh
generation-bound measurements can select a green channel. No route writes.
"""
import math
import subprocess
import time


def fresh(value, now, age):
    try:return type(value) in (int, float) and math.isfinite(value) and -5 <= now-value <= age
    except (OverflowError,TypeError):return False


def snapshot(status, journal, live_order, now=None):
    now = time.time() if now is None else now
    result = {'time': now, 'confirmed': False, 'active_profile_id': None,
              'source_profile_id': None, 'target_profile_id': None,
              'transitioning': False, 'scope': 'client-confirmed general VPN rule'}
    if not isinstance(status, dict) or not isinstance(journal, dict):
        return result
    source, target = journal.get('source'), journal.get('target')
    if not all(isinstance(x, str) and x for x in (source, target)) or source == target:
        return result
    result.update(source_profile_id=source, target_profile_id=target)
    controller = status.get('native_failover', {})
    if (status.get('rpc_error') or not fresh(status.get('time'), now, 90)
            or not isinstance(controller, dict) or not fresh(controller.get('time'), now, 30)):
        return result
    phase = journal.get('phase')
    if controller.get('tx') is not None and controller.get('tx') != journal.get('tx'):
        return result
    if phase in ('ARMED', 'APPLYING', 'WAIT-CLIENT', 'RESTORING'):
        if controller.get('state') != phase:
            return result
        result['transitioning'] = True
        return result
    if phase not in ('COMMITTED', 'HELD-ON-RESERVE', 'ROLLED-BACK'):
        return result
    if not fresh(journal.get('confirmed'), now, 14400):
        return result
    side = 'source' if phase == 'ROLLED-BACK' else 'target'
    expected = journal.get('before' if side == 'source' else 'after')
    if live_order != (expected, journal.get('hash')):
        return result
    profiles = status.get('profiles', [])
    if not isinstance(profiles, list):
        return result
    row = next((p for p in profiles if isinstance(p, dict) and p.get('id') == journal[side]), None)
    proofs = journal.get('vendor_profiles', {})
    proof = proofs.get(side) if isinstance(proofs, dict) else None
    if not row or not isinstance(proof, dict) or not fresh(row.get('time'), now, 90):
        return result
    from failure_diagnosis import profile_identity
    if not proof or profile_identity(row) != proof:
        return result
    # A failed selected path remains selected and red; success is evaluated by
    # the UI independently. Unknown health never becomes green.
    result.update(confirmed=True, active_profile_id=journal[side])
    return result


def public_status(status):
    try:
        from native_switch import Linux, journal_read, Refused
        journal = journal_read()
        return snapshot(status, journal, Linux().order() if journal else None)
    except (Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return snapshot({}, {}, None)
