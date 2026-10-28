"""Resume only our proven, unchanged pre-RTP rollback graph.

This never infers permission from a role or from a legacy journal. A recorded
full mangle/rule fingerprint, current tunnel bindings and the stopped owning
session must all agree before any retry can be dispatched.
"""
import copy
import re


def order_steps(before,target):
    """The minimal left-to-right UCI moves used by Linux.reorder()."""
    if (not isinstance(before,list) or not isinstance(target,list) or not 2<=len(before)<=400
            or len(before)!=len(target) or any(not isinstance(x,str) for x in before+target)
            or len(set(before))!=len(before) or set(before)!=set(target)):
        raise ValueError('JOURNAL-INTEGRITY-FAILED')
    current=list(before)
    for index,identifier in enumerate(target):
        if current[index]==identifier:continue
        previous=list(current);current.remove(identifier);current.insert(index,identifier)
        yield {'version':1,'kind':'reorder','before':previous,'after':list(current),'section':identifier,'index':index}


def validate_step(journal):
    """A new checkpoint grants only one canonical before/after transition."""
    before=restore_origin(journal);target=journal.get('restore_target_order')
    if 'restore_order_step' not in journal:return None
    step=journal['restore_order_step']
    if (not isinstance(step,dict) or type(step.get('version')) is not int or step['version']!=1
            or journal.get('phase') not in ('RESTORING','ROLLED-BACK','RELEASE-PENDING')
            or journal.get('restore_before_verified') is not True
            or not isinstance(journal.get('restore_kernel_fingerprint'),str)
            or not re.fullmatch('[a-f0-9]{64}',journal['restore_kernel_fingerprint'])
            or journal.get('restore_before_order') not in (journal.get('before'),journal.get('after'),journal.get('restored_order'))):
        raise ValueError('JOURNAL-INTEGRITY-FAILED')
    moves=list(order_steps(before,target))
    commit={'version':1,'kind':'commit','before':target,'after':target}
    if step==commit:return step
    if type(step.get('index')) is int and any(step==expected for expected in moves):return step
    raise ValueError('JOURNAL-INTEGRITY-FAILED')


def restore_origin(journal):
    """Keep the UCI plan separate from the order proven by the actual kernel."""
    if 'restore_proof_source' not in journal and 'restore_order_origin' not in journal:return journal.get('restore_before_order')
    if (journal.get('restore_proof_source')!='forward' or journal.get('restore_order_origin')!=journal.get('after')
            or journal.get('restore_before_order')!=journal.get('before') or journal.get('restore_target_order')!=journal.get('before')
            or journal.get('before')==journal.get('after') or journal.get('kernel_before_verified') is not True
            or journal.get('restore_before_verified') is not True or journal.get('rtp_dispatched') is not True
            or journal.get('forward_policy_touched') is not True or journal.get('confirmed') is not None
            or journal.get('kernel_confirmed') is not None or 'restore_order_step' not in journal
            or journal.get('restore_kernel_fingerprint')!=journal.get('kernel_before_fingerprint')):
        raise ValueError('JOURNAL-INTEGRITY-FAILED')
    return journal['restore_order_origin']


def order_allowed(journal,order):
    step=validate_step(journal)
    return order in (step['before'],step['after']) if step is not None else order==journal.get('restore_target_order')


def record_step(backend,journal,args):
    """Persist a verified pending UCI write before dispatch, never infer a lost step."""
    import native_switch as n
    if args[:2]!=['uci','reorder'] and args!=['uci','commit','route_policy']:return
    if journal.get('restore_before_verified') is not True:return
    if n.journal_read()!=journal:raise n.Refused('JOURNAL-INTEGRITY-FAILED')
    sections=backend.policy()['sections'];bindings=journal.get('process_bindings')
    live=n.policy_order(sections,bindings)
    if n.policy_hash(sections,bindings)!=journal['hash']:raise n.Refused('POLICY-IDENTITY-CHANGED')
    target=journal['restore_target_order']
    if args==['uci','commit','route_policy']:
        if live!=target:raise n.Refused('POLICY-IDENTITY-CHANGED')
        step={'version':1,'kind':'commit','before':list(live),'after':list(live)}
    else:
        step=next((row for row in order_steps(restore_origin(journal),target) if row['before']==live),None)
        names={n.section_id(row,bindings):row['.name'] for row in sections}
        if step is None or args!=['uci','reorder','route_policy.'+names[step['section']]+'='+str(step['index'])]:
            raise n.Refused('POLICY-IDENTITY-CHANGED')
    if n.journal_read()!=journal or backend.order()!=(live,journal['hash']):raise n.Refused('POLICY-IDENTITY-CHANGED')
    journal['restore_order_step']=step
    n.journal_write(journal)
    if n.journal_read()!=journal or backend.order()!=(live,journal['hash']):raise n.Refused('POLICY-IDENTITY-CHANGED')


def forward_proof(journal):
    return (journal.get('phase') in ('APPLYING','WAIT-CLIENT') and journal.get('rtp_dispatched') is True
            and journal.get('forward_policy_touched') is True and journal.get('kernel_before_verified') is True
            and journal.get('confirmed') is None and journal.get('kernel_confirmed') is None
            and journal.get('before')!=journal.get('after')
            and not any(key.startswith('restore') for key in journal))


def authorize(backend,journal,forward=False):
    import native_switch as n
    import pair_auto as pair
    from agent import RUNTIME,read_json
    from pair_policy import metadata,proof
    from pair_interfaces import state as interfaces
    from failure_diagnosis import profile_identity

    def refuse():raise n.Refused('KERNEL-POLICY-UNVERIFIED')
    fingerprint=journal.get('kernel_before_fingerprint' if forward else 'restore_kernel_fingerprint')
    context=metadata(journal)
    if context is None or not isinstance(fingerprint,str) or not re.fullmatch('[a-f0-9]{64}',fingerprint):refuse()
    if forward:
        if not forward_proof(journal):refuse()
    elif (journal.get('phase')!='RESTORING' or journal.get('restore_before_verified') is not True
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
        # Old proofs still require the completed order. A new durable step
        # permits only its exact before/after, never any other permutation or
        # an invented checkpoint for a legacy interrupted multi-rule move.
        if (live!=(selection.get('order'),journal['hash'])
                or (live[0]!=journal['after'] if forward else not order_allowed(journal,live[0]))
                or backend.kernel_fingerprint()!=fingerprint):refuse()
        # Recheck the durable/Stop fence after the expensive read-only checks.
        n.require_control_revision(revision)
        if (pair.intent()!=requested or pair.read_state()!=state or n.journal_read()!=journal
                or backend.order()!=live or backend.guard_exists() is not True):refuse()

    check()
    return check,revision


def promote_forward(backend,journal,target):
    """Reuse an existing full forward proof only after Stop, never infer one."""
    import native_switch as n
    import pair_auto as pair
    from agent import RUNTIME
    from auto_control import control_lock
    if target!=journal.get('before'):raise n.Refused('KERNEL-POLICY-UNVERIFIED')
    check,revision=authorize(backend,journal,forward=True)
    state=pair.read_state();requested=pair.intent()
    pending=copy.deepcopy(journal)
    pending.update(phase='RESTORING',restore_proof_source='forward',restore_order_origin=list(journal['after']),
                   restore_before_order=list(journal['before']),restore_before_verified=True,restore_target_order=list(target),
                   restore_kernel_fingerprint=journal['kernel_before_fingerprint'])
    pending['restore_order_step']=next(order_steps(pending['restore_order_origin'],target))
    check()  # Repeat the live graph/bindings proof before the bounded durable CAS.
    with control_lock(RUNTIME):
        n.require_control_revision(revision)
        if n.journal_read()!=journal or pair.read_state()!=state or pair.intent()!=requested:
            raise n.Refused('JOURNAL-INTEGRITY-FAILED')
        n.journal_write(pending)
        if n.journal_read()!=pending:raise n.Refused('JOURNAL-INTEGRITY-FAILED')
    journal.clear();journal.update(pending)
    return authorize(backend,journal)
