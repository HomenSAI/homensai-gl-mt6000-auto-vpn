"""Resume only our proven, unchanged pre-RTP rollback graph.

This never infers permission from a role or from a legacy journal. A recorded
full mangle/rule fingerprint, current tunnel bindings and the stopped owning
session must all agree before any retry can be dispatched.
"""
import re


def authorize(backend,journal):
    import native_switch as n
    import pair_auto as pair
    from agent import RUNTIME,read_json
    from pair_policy import metadata,proof
    from pair_interfaces import state as interfaces
    from failure_diagnosis import profile_identity

    def refuse():raise n.Refused('KERNEL-POLICY-UNVERIFIED')
    fingerprint=journal.get('restore_kernel_fingerprint')
    context=metadata(journal)
    if (journal.get('phase')!='RESTORING' or journal.get('restore_before_verified') is not True
            or context is None or not isinstance(fingerprint,str) or not re.fullmatch('[a-f0-9]{64}',fingerprint)
            or journal.get('restore_target_order') is None or journal.get('restore_before_order') is None):refuse()
    # A new supervisor revision fences the old operation. Its stopped intent
    # is observed, never replaced or rotated by this recovery helper.
    marker=read_json(RUNTIME/'auto-control-revision.json',{})
    revision=marker.get('revision') if isinstance(marker,dict) else None
    n.require_control_revision(revision)
    state=pair.read_state();requested=pair.intent()
    if (requested.get('mode')!='off' or requested.get('revision')!=revision
            or state.get('phase') not in ('RUNNING','HELD','STOPPING')
            or state.get('id')!=journal.get('trial_nonce')
            or state.get('revision')!=journal.get('control_revision')
            or state.get('process_bindings')!=journal.get('process_bindings')
            or state.get('order')!=context['session_order'] or state.get('policy_hash')!=journal.get('hash')
            or state.get('policy_roles')!={key:context[key] for key in ('source_rule','target_rule','direction','generic_rules','source_id','target_id')}):refuse()

    def check():
        n.require_control_revision(revision)
        if (pair.intent()!=requested or pair.read_state()!=state or n.journal_read()!=journal
                or backend.guard_exists() is not True):refuse()
        managed=interfaces(state)
        if (pair.normalized_network(pair.network(),managed)!=state['network_identity']
                or pair.changed(state,pair.configs(managed))):refuse()
        # diagnostic() validates each live route_binding (default route,
        # marked route lookups, device/ifindex/table/mark and profile epoch).
        # Missing/down or changed bindings never use this narrow exception.
        blockers,selection=backend.diagnostic()
        if (blockers or not isinstance(selection,dict) or proof(selection)!=state['policy_roles']
                or selection.get('hash')!=journal['hash']
                or selection.get('vendor_identity')!=journal.get('vendor_identity')
                or selection.get('process_bindings')!=journal.get('process_bindings')):refuse()
        for role in ('source','target'):
            current=selection.get(role,{})
            identity=profile_identity(current)
            if identity is None or identity!=(journal.get('vendor_profiles') or {}).get(role):refuse()
            binding=current.get('kernel_binding')
            if (not isinstance(binding,dict) or binding.get('code') is not None
                    or not isinstance(binding.get('device'),str) or not re.fullmatch('[A-Za-z0-9_]{1,15}',binding['device'])
                    or type(binding.get('mark')) is not int or binding['mark']<=0
                    or not isinstance(binding.get('table'),str) or not binding['table'].isdigit()
                    or type(binding.get('ifindex')) is not int or binding['ifindex']<=0):refuse()
        observed_identity=n.digest({role:{'profile':profile_identity(selection[role]),'kernel':selection[role]['kernel_binding']}
                                    for role in ('source','target')})
        if observed_identity!=journal['vendor_identity']:refuse()
        live=backend.order()
        # This exception starts only after the UCI reorder completed. It does
        # not authorize guessing ownership of an intermediate multi-rule move;
        # therefore the resumed rollback performs no further order writes.
        if (live!=(selection.get('order'),journal['hash'])
                or live[0]!=journal['restore_target_order']
                or backend.kernel_fingerprint()!=fingerprint):refuse()
        # Recheck the durable/Stop fence after the expensive read-only checks.
        n.require_control_revision(revision)
        if (pair.intent()!=requested or pair.read_state()!=state or n.journal_read()!=journal
                or backend.order()!=live or backend.guard_exists() is not True):refuse()

    check()
    return check,revision
