"""Read-only hierarchy selection; eligibility never authorizes route writes."""
from failover_plan import streak


def rank_candidates(profiles, metadata, samples, source, now, max_age=90,observation=None,settings=None):
    """Different tunnel on the same protocol, then another VPN protocol.

    Only already-bound profiles with two fresh tunneled HTTPS/DNS successes
    are eligible. Operator metadata controls priority; latency never rewrites it.
    Wi-Fi/Ethernet are uplinks and are deliberately not accepted as protocols.
    """
    from failure_diagnosis import resolve_pair,finite
    if not isinstance(profiles,list) or not isinstance(metadata,list):return []
    if any(not isinstance(p,dict) or not isinstance(p.get('id'),str) for p in profiles):return []
    rows={p['id']:p for p in profiles}
    if len(rows)!=len(profiles):return []
    names={m['profile']:m for m in metadata if isinstance(m,dict) and isinstance(m.get('profile'),str)}
    current=rows.get(source)
    if not current:return []
    settings=settings if isinstance(settings,dict) else {}
    ranked=[]
    for identifier,row in rows.items():
        saved=names.get(identifier,{})
        anchored_target=bool(settings.get('plan_target_tunnel') and row.get('vendor_tunnel_id')==settings['plan_target_tunnel'])
        if identifier==source or (metadata and (identifier not in names and not anchored_target or saved.get('enabled') is False)):continue
        if row.get('protocol') not in ('openvpn','wireguard') or not row.get('interface'):continue
        pair=resolve_pair({'time':now,'profiles':profiles,'vendor_observation':observation},
            {'plan_source':source,'plan_target':identifier},now,max_age,
            max(30,min(600,max_age*2/3)) if finite(max_age) and max_age>0 else 60)
        if pair['coordination']['state']!='READY':continue
        if not streak(samples,identifier,2,now,max_age,True,row):continue
        same_protocol=row.get('protocol')==current.get('protocol')
        tier=1 if same_protocol else 2
        channel_preference=names.get(settings.get('plan_target'),{}) if anchored_target else {}
        priority=saved.get('priority',channel_preference.get('priority',100))
        if type(priority) is not int or not 1<=priority<=1000:priority=100
        ranked.append({'id':identifier,'tier':tier,'priority':priority,
                       'transition':'channel' if tier==1 else 'protocol',
                       'vendor_tunnel_id':row.get('vendor_tunnel_id'),'can_apply':False,
                       'vendor_attempts_exhausted':None,'mode':'recommendation-only','requires_native_adapter_validation':True})
    return sorted(ranked,key=lambda item:(item['tier'],item['priority'],item['id']))
