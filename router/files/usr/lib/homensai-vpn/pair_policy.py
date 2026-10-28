"""Configured pair roles and honest before/after orders for either manual direction.

These identities describe the policy; successful tunnel probes alone never
establish which rule handles general traffic.
"""


def proof(selection):
    value={key:selection.get(key) for key in ('source_rule','target_rule','direction')}
    value['generic_rules']=sorted(selection.get('generic_rules',[value['source_rule'],value['target_rule']]))
    value['source_id']=selection.get('source',{}).get('id')
    value['target_id']=selection.get('target',{}).get('id')
    validate(value,selection.get('order'))
    return value


def validate(value,order):
    if (not isinstance(value,dict) or not isinstance(order,list) or not 2<=len(order)<=400
            or any(not isinstance(key,str) or not key for key in order) or len(order)!=len(set(order))
            or value.get('direction') not in ('first','last')
            or not all(isinstance(value.get(key),str) and value[key] for key in ('source_rule','target_rule','source_id','target_id'))
            or value['source_rule']==value['target_rule'] or value['source_id']==value['target_id']
            or not isinstance(value.get('generic_rules'),list) or not 2<=len(value['generic_rules'])<=16
            or any(not isinstance(key,str) or key not in order for key in value['generic_rules'])
            or len(value['generic_rules'])!=len(set(value['generic_rules']))
            or any(value[role+'_rule'] not in value['generic_rules'] for role in ('source','target'))):
        raise ValueError('PAIR-POLICY-UNVERIFIED')
    return value


def role(value,order):
    validate(value,order)
    generic=sorted(value['generic_rules'],key=order.index)
    chosen=generic[0] if value['direction']=='first' else generic[-1]
    for key in ('source','target'):
        if value[key+'_rule']==chosen:return key
    raise ValueError('PAIR-POLICY-UNVERIFIED')


def desired_order(value,order,destination):
    if destination not in ('source','target'):raise ValueError('PAIR-POLICY-UNVERIFIED')
    current=role(value,order)
    result=list(order)
    if current!=destination:
        a=result.index(value['source_rule']);b=result.index(value['target_rule'])
        result[a],result[b]=result[b],result[a]
    if role(value,result)!=destination:raise ValueError('PAIR-POLICY-UNVERIFIED')
    return result


def transition(selection,session_order,destination):
    identity=proof(selection);before=selection['order']
    if not isinstance(session_order,list) or len(session_order)!=len(before) or set(session_order)!=set(before):
        raise ValueError('PAIR-POLICY-UNVERIFIED')
    if session_order not in (desired_order(identity,before,'source'),desired_order(identity,before,'target')):
        raise ValueError('PAIR-POLICY-UNVERIFIED')
    return dict(identity,destination_role=destination,before_policy_role=role(identity,before),
                session_order=list(session_order),primary_order=desired_order(identity,before,'source'))


def metadata(journal):
    value=journal.get('pair_transition')
    if value is None:return None
    if not isinstance(value,dict) or set(value)!={'source_rule','target_rule','direction','generic_rules','source_id','target_id',
                                                'destination_role','before_policy_role','session_order','primary_order'}:
        raise ValueError('PAIR-POLICY-UNVERIFIED')
    identity=validate(value,journal.get('before'))
    if (identity['source_id']!=journal.get('source') or identity['target_id']!=journal.get('target')
            or value.get('destination_role') not in ('source','target')
            or value.get('before_policy_role')!=role(identity,journal['before'])
            or journal.get('after')!=desired_order(identity,journal['before'],value['destination_role'])
            or any(not isinstance(value.get(key),list) or len(value[key])!=len(journal['before'])
                   or set(value[key])!=set(journal['before']) for key in ('session_order','primary_order'))
            or value['primary_order']!=desired_order(identity,journal['before'],'source')
            or value['session_order'] not in (desired_order(identity,journal['before'],'source'),desired_order(identity,journal['before'],'target'))):
        raise ValueError('PAIR-POLICY-UNVERIFIED')
    for key in ('restored_order','restore_target_order'):
        restored=journal.get(key)
        if restored is not None and restored not in (journal['before'],value['primary_order'],value['session_order']):
            raise ValueError('PAIR-POLICY-UNVERIFIED')
    return value


def current_order(journal):
    if journal.get('phase') in ('COMMITTED','HELD-ON-RESERVE'):return journal.get('after')
    if journal.get('phase')=='ROLLED-BACK':return journal.get('restored_order',journal.get('before'))
    return None


def current_role(journal):
    value=metadata(journal);order=current_order(journal)
    return role(value,order) if value is not None and order is not None else None


def state_order_matches(state,journal,live):
    try:value=metadata(journal)
    except (ValueError,TypeError):return False
    if live==(state.get('order'),state.get('policy_hash')) and journal.get('phase') in (None,'ROLLED-BACK'):return True
    identity=state.get('policy_roles')
    return bool(value is not None and value['session_order']==state.get('order')
                and journal.get('hash')==state.get('policy_hash')
                and (identity is None or all(value.get(key)==item for key,item in identity.items()))
                and live==(current_order(journal),journal.get('hash')))
