"""Proof scopes cannot be silently promoted from hosted tests to external LAN."""
EXTERNAL='external-lan'
HOSTED='router-hosted-ipv4'
ROUTER='router-probed-ipv4'


def requested(settings):
    if not isinstance(settings,dict):raise ValueError('LAN-TRIAL-REQUIRED')
    value=settings.get('native_proof_scope',EXTERNAL)
    if type(value)is not str or value not in(EXTERNAL,HOSTED,ROUTER):raise ValueError('LAN-TRIAL-REQUIRED')
    if value==ROUTER and settings.get('pair_auto_mode')!=ROUTER:raise ValueError('PAIR-MODE-NOT-CONFIGURED')
    return value


def matches(first,second):
    if not isinstance(first,dict)or not isinstance(second,dict):return False
    a=first.get('proof_scope',EXTERNAL);b=second.get('proof_scope',EXTERNAL)
    return type(a)is str and a in(EXTERNAL,HOSTED,ROUTER)and a==b
