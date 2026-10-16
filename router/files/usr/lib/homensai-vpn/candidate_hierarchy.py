"""Read-only hierarchy selection; eligibility never authorizes route writes."""
from failover_plan import streak


def rank_candidates(profiles, metadata, samples, source, now, max_age=90):
    """Same channel/protocol first, then other channel, then other VPN protocol.

    Only already-bound profiles with two fresh tunneled HTTPS/DNS successes
    are eligible. Operator metadata controls priority; latency never rewrites it.
    Wi-Fi/Ethernet are uplinks and are deliberately not accepted as protocols.
    """
    rows={p['id']:p for p in profiles}
    names={m['profile']:m for m in metadata}
    current=rows.get(source)
    if not current:return []
    origin=names.get(source,{})
    ranked=[]
    for identifier,row in rows.items():
        saved=names.get(identifier,{})
        if identifier==source or (metadata and (identifier not in names or not saved.get('enabled',True))):continue
        if row.get('protocol') not in ('openvpn','wireguard') or not row.get('interface'):continue
        if not streak(samples,identifier,2,now,max_age,True):continue
        same_protocol=row.get('protocol')==current.get('protocol')
        same_channel=saved.get('channel','default')==origin.get('channel','default')
        tier=0 if same_protocol and same_channel else 1 if same_protocol else 2
        priority=saved.get('priority',100)
        if type(priority) is not int or not 1<=priority<=1000:priority=100
        ranked.append({'id':identifier,'tier':tier,'priority':priority,
                       'transition':'server' if tier==0 else 'channel' if tier==1 else 'protocol',
                       'mode':'recommendation-only','requires_native_adapter_validation':True})
    return sorted(ranked,key=lambda item:(item['tier'],item['priority'],item['id']))
