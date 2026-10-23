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


def pair_snapshot(status, state, journal, live_order, now=None):
    """Verify selected policy independently of the selected VPN's Internet health."""
    now = time.time() if now is None else now
    result = snapshot({}, {}, None, now)
    result['scope'] = 'verified live router policy selection; Internet health is separate'
    native = status.get('native_failover', {})
    if (state.get('phase') != 'RUNNING' or status.get('rpc_error')
            or not fresh(status.get('time'), now, 90) or not isinstance(native, dict)
            or not fresh(native.get('time'), now, 30)):
        return result
    source, target = native.get('source'), native.get('target')
    if not all(isinstance(x, str) and x for x in (source, target)) or source == target:
        return result
    result.update(source_profile_id=source, target_profile_id=target,
                  transitioning=native.get('state') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'))
    active = source if live_order == (state.get('order'), state.get('policy_hash')) else None
    if (active is None and journal.get('source') == source and journal.get('target') == target
            and journal.get('before') == state.get('order') and journal.get('hash') == state.get('policy_hash')
            and live_order == (journal.get('after'), journal.get('hash'))):
        active = target
    if active is not None:
        result.update(confirmed=True, active_profile_id=active)
    return result


def public_status(status):
    try:
        from native_switch import Linux, journal_read, Refused
        from pair_auto import read_state
        journal = journal_read()
        state = read_state()
        backend = Linux()
        if state.get('phase') == 'RUNNING':
            backend.use_process_bindings(state.get('process_bindings'))
            return pair_snapshot(status, state, journal, backend.order())
        return snapshot(status, journal, backend.order() if journal else None)
    except (Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return snapshot({}, {}, None)
