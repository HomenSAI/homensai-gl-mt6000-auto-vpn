"""Fast channel switch on the GL-MT3000: apply the already committed route_policy order to the kernel directly.

Measured on the MT3000 (30 Oct 2026): the vendor rebuild (/usr/bin/rtp2.sh) takes 20-33 s and restarts the
firewall and every dnsmasq, but the only kernel change a switch needs is the order of the two tunnel jumps in
mangle ROUTE_POLICY and the mark of the router's own VPN process rule (TUNNELxxx_LOCAL_POLICY of gl_process_vpn).
One `iptables-restore --noflush` replaces both chains atomically (8-33 ms); LAN clients moved in under 0.5 s
with no failed request. The UCI order is committed first, so any later vendor rebuild produces the same result.

Anything unexpected in the chains raises Unsupported and the caller uses the vendor rebuild instead.
"""
import re

MARK=re.compile(r'^0x[0-9a-f]{1,8}$')
TUNNEL_ID=re.compile(r'^[0-9]{1,8}$')
JUMP=re.compile(r'^-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL([0-9]{1,8})_ROUTE_POLICY$')


class Unsupported(ValueError):
    pass


def uci_rules(text):
    """(enabled rule tunnel ids in order, gl_process_vpn tunnel id, gl_process_vpn mark) from `uci show route_policy`."""
    rules={};local={}
    for line in text.splitlines():
        match=re.match(r"^route_policy\.@rule\[([0-9]+)\]\.(tunnel_id|enabled)='([^']*)'$",line)
        if match:rules.setdefault(int(match.group(1)),{})[match.group(2)]=match.group(3);continue
        match=re.match(r"^route_policy\.gl_process_vpn\.(tunnel_id|mark|enabled)='([^']*)'$",line)
        if match:local[match.group(1)]=match.group(2)
    order=[rules[i]['tunnel_id'] for i in sorted(rules) if rules[i].get('enabled','1')!='0' and 'tunnel_id' in rules[i]]
    if len(order)!=2 or len(set(order))!=2 or not all(TUNNEL_ID.fullmatch(t) for t in order):raise Unsupported('FAST-RULES')
    if (local.get('enabled')=='0' or not TUNNEL_ID.fullmatch(local.get('tunnel_id','')) or not MARK.fullmatch(local.get('mark',''))):
        raise Unsupported('FAST-LOCAL-RULE')
    return order,local['tunnel_id'],local['mark']


def plan(mangle,order,local_tunnel,local_mark):
    """Return (payload, old_first_tunnel, changed) for one atomic iptables-restore --noflush of the two chains."""
    route=[l for l in mangle.splitlines() if l.startswith('-A ROUTE_POLICY ')]
    jumps=[i for i,l in enumerate(route) if '_ROUTE_POLICY' in l.split(' -j ')[-1]]
    found=[JUMP.fullmatch(route[i]) for i in jumps]
    if len(jumps)!=2 or not all(found) or sorted(m.group(1) for m in found)!=sorted(order) or jumps[1]!=jumps[0]+1:
        raise Unsupported('FAST-ROUTE-CHAIN')
    old_first=found[0].group(1)
    by_id={m.group(1):route[i] for m,i in zip(found,jumps)}
    new_route=list(route);new_route[jumps[0]]=by_id[order[0]];new_route[jumps[1]]=by_id[order[1]]
    name='TUNNEL%s_LOCAL_POLICY'%local_tunnel
    local=[l for l in mangle.splitlines() if l.startswith('-A %s '%name)]
    setters=[i for i,l in enumerate(local) if ' -j MARK --set-xmark ' in l]
    if len(setters)!=1 or not re.search(r' -j MARK --set-xmark 0x[0-9a-f]{1,8}/0xf000$',local[setters[0]]):raise Unsupported('FAST-LOCAL-CHAIN')
    new_local=list(local);new_local[setters[0]]=re.sub(r'--set-xmark 0x[0-9a-f]{1,8}/0xf000$','--set-xmark %s/0xf000'%local_mark,local[setters[0]])
    changed=new_route!=route or new_local!=local
    payload='*mangle\n:ROUTE_POLICY - [0:0]\n'+'\n'.join(new_route)+'\n:%s - [0:0]\n'%name+'\n'.join(new_local)+'\nCOMMIT\n'
    return payload,old_first,changed


def mark_of(mangle,tunnel):
    for line in mangle.splitlines():
        match=re.match(r'^-A TUNNEL%s_ROUTE_POLICY .* -j MARK --set-xmark (0x[0-9a-f]{1,8})/0xf000$'%tunnel,line)
        if match:return match.group(1)
    raise Unsupported('FAST-MARK')
