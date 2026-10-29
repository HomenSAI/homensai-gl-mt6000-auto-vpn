"""Display confirmed general VPN path; request acknowledgements are not proof.

Only a client-confirmed transaction, unchanged live policy order and fresh
generation-bound measurements can select a green channel. No route writes.
"""
import math
import subprocess
import time
import re

PROFILE=re.compile(r'^(?:openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$')


def from_kernel(kernel,source,target,now=None):
    """Observational projection only; never renew the original proof timestamp."""
    now=time.time() if now is None else now
    result={'mode':'continuous-pair','selection_proof':'fw3-kernel-marking','valid_for':15,'time':None,'checked_at':None,
            'confirmed':False,'kernel_policy_verified':False,'active_profile_id':None,'transitioning':False,
            'source_profile_id':source if isinstance(source,str) and PROFILE.fullmatch(source) else None,
            'target_profile_id':target if isinstance(target,str) and PROFILE.fullmatch(target) else None,
            'code':'KERNEL-POLICY-UNVERIFIED','scope':'new IPv4 LAN catch-all marking; Internet health is separate; no external-client proof'}
    if not isinstance(kernel,dict):return result
    stamp=kernel.get('time');role=kernel.get('role')
    if type(stamp) in (int,float) and math.isfinite(stamp) and 0<=stamp<=now+5:result.update(time=stamp,checked_at=stamp)
    expected=source if role=='source' else target if role=='target' else None
    if (kernel.get('verified') is not True or role not in ('source','target') or not expected
            or kernel.get('profile_id')!=expected or not result['source_profile_id'] or not result['target_profile_id']
            or source==target or not fresh(stamp,now,15)):return result
    result.update(confirmed=True,kernel_policy_verified=True,active_profile_id=expected,code=None)
    return result


def cached_projection(value,now=None):
    now=time.time() if now is None else now
    if not isinstance(value,dict):return from_kernel(None,None,None,now)
    source=value.get('source_profile_id');target=value.get('target_profile_id')
    if value.get('mode')!='continuous-pair' or value.get('selection_proof')!='fw3-kernel-marking':return from_kernel(None,source,target,now)
    active=value.get('active_profile_id');role='source' if active==source else 'target' if active==target else None
    kernel={'verified':value.get('confirmed') is True and value.get('kernel_policy_verified') is True,
            'time':value.get('checked_at'),'role':role,'profile_id':active}
    result=from_kernel(kernel,source,target,now)
    result['transitioning']=value.get('transitioning') is True
    if result['transitioning']:result.update(confirmed=False,kernel_policy_verified=False,active_profile_id=None)
    return result


def observed_pair_role(native,now=None):
    """Read-only event-time classification; phase and channel health are never a role proof."""
    if not isinstance(native,dict) or native.get('state') in ('BLOCKED','ARMED','APPLYING','WAIT-CLIENT','RESTORING') or native.get('blockers'):return None
    path=cached_projection(native.get('channel_path'),now)
    if (not path['confirmed'] or path.get('source_profile_id')!=native.get('source')
            or path.get('target_profile_id')!=native.get('target')):return None
    for role in ('source','target'):
        if path['active_profile_id']==native.get(role):return role
    return None


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
    from pair_policy import metadata,current_role,current_order
    try:pair_context=metadata(journal)
    except (ValueError,TypeError,KeyError):return result
    side = current_role(journal) if pair_context is not None else 'source' if phase == 'ROLLED-BACK' else 'target'
    expected = current_order(journal) if pair_context is not None else journal.get('before' if side == 'source' else 'after')
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


def pair_snapshot(status, state, journal, live_order, now=None, kernel=None):
    """Verify selected policy independently of the selected VPN's Internet health."""
    now = time.time() if now is None else now
    result = snapshot({}, {}, None, now)
    result.update(from_kernel(None,None,None,now))
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
    if result['transitioning'] or native.get('state')=='BLOCKED' or native.get('blockers'):return result
    from pair_policy import role,state_order_matches,metadata,current_order
    identity=state.get('policy_roles')
    if identity is None:return result  # A historical baseline never proves that the primary was selected.
    try:
        if (identity.get('source_id')!=source or identity.get('target_id')!=target
                or not state_order_matches(state,journal,live_order)):return result
        selected=role(identity,live_order[0])
        result['configured_profile_id']=identity[selected+'_id']
        if (not isinstance(kernel,dict) or kernel.get('verified') is not True or not fresh(kernel.get('time'),now,15)
                or kernel.get('role')!=selected or kernel.get('profile_id')!=identity[selected+'_id']
                or kernel.get('policy_hash')!=state['policy_hash'] or kernel.get('order')!=live_order[0]):
            result.update(kernel_policy_verified=False,code='KERNEL-POLICY-UNVERIFIED')
            return result
        result.update(from_kernel(kernel,source,target,now))
    except (ValueError,TypeError,KeyError):return result
    return result


def public_status(status):
    native=status.get('native_failover',{}) if isinstance(status,dict) else {}
    required=native.get('mode')=='continuous-pair' or native.get('proof_scope')=='router-probed-ipv4'
    try:
        from native_switch import Linux, journal_read, Refused
        from pair_auto import read_state
        journal = journal_read()
        required=required or journal.get('pair_transition') is not None or journal.get('proof_scope')=='router-probed-ipv4'
        state = read_state()
        backend = Linux()
        pair_mode=(state.get('policy_roles') is not None or journal.get('pair_transition') is not None
                   or journal.get('proof_scope')=='router-probed-ipv4' or status.get('native_failover',{}).get('mode')=='continuous-pair')
        if pair_mode:
            if native.get('state')=='BLOCKED' or native.get('blockers'):return from_kernel(None,native.get('source'),native.get('target'))
            backend.use_process_bindings(state.get('process_bindings'))
            kernel=None
            if state.get('phase')=='RUNNING':
                # Display only: share the 15 s attestation with the manual buttons; every switch re-attests itself.
                from pair_manual import attested
                kernel=attested(backend,journal)
            return pair_snapshot(status,state,journal,backend.order(),kernel=kernel)
        return snapshot(status, journal, backend.order() if journal else None)
    except (Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return from_kernel(None,native.get('source'),native.get('target')) if required else snapshot({}, {}, None)
