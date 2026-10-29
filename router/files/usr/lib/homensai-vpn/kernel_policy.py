"""Read-only attestation of the pinned MT3000 FW3 catch-all packet-mark path.

The proof is for new IPv4 LAN flows with no saved VPN connmark. It is neither
an external-client probe nor proof that an existing connection changed exit.
Unknown chains/options fail closed; bound tunnel health is separate.
"""
import re
import shlex
import copy

MASK=0xf000


def static_bindings(selection,network):
    """Pinned setup_instance/RTP slot contract, including a client that has never been UP."""
    if not isinstance(network,list):raise ValueError('KERNEL-POLICY-UNVERIFIED')
    rows={row.get('.name'):row for row in network if isinstance(row,dict)}
    if len(rows)!=len(network):raise ValueError('KERNEL-POLICY-UNVERIFIED')
    result=copy.deepcopy(selection)
    for role in ('source','target'):
        profile=result[role];interface=profile.get('interface')
        match=re.fullmatch(r'(wgclient|ovpnclient)([1-5])',interface or '')
        if not match:raise ValueError('KERNEL-POLICY-UNVERIFIED')
        proto,index=match.group(1),int(match.group(2));protocol='wireguard' if proto=='wgclient' else 'openvpn'
        identifier=profile.get('id','');prefix=protocol+':'
        config=identifier[len(prefix):] if identifier.startswith(prefix) else ''
        if (not re.fullmatch(r'peer_[0-9]+' if protocol=='wireguard' else r'[0-9]+_[0-9]+',config)
                or profile.get('protocol')!=protocol or profile.get('vendor_tunnel_id')!=protocol+':'+interface):
            raise ValueError('KERNEL-POLICY-UNVERIFIED')
        expected_mark=((1 if proto=='wgclient' else 10)+index-1)<<12
        table=str((1000 if proto=='wgclient' else 1010)+index)
        row=rows.get(interface,{});rule=rows.get('rt_'+interface,{})
        if (row.get('.type')!='interface' or row.get('proto')!=proto or row.get('config')!=config or row.get('ip4table')!=table
                or rule.get('.type')!='rule' or numeric(str(rule.get('mark',''))) != str(expected_mark)+'/'+str(MASK)
                or str(rule.get('lookup'))!=table or str(rule.get('priority'))!='6000'):
            raise ValueError('KERNEL-POLICY-UNVERIFIED')
        binding=profile.get('kernel_binding',{})
        if binding.get('code')=='VPN-001':
            # The persistent declaration and live iprules/mark graph still have to agree below.
            profile['kernel_binding']={'code':None,'mark':expected_mark,'table':table,'declared_down':True}
        elif binding.get('code') is not None or binding.get('mark')!=expected_mark or binding.get('table')!=table:
            raise ValueError('KERNEL-POLICY-UNVERIFIED')
    return result


def number(value):
    if isinstance(value,int) and not isinstance(value,bool):return value
    if not isinstance(value,str) or not re.fullmatch(r'(?:0x[0-9a-fA-F]+|[0-9]+)',value):raise ValueError('KERNEL-POLICY-UNVERIFIED')
    return int(value,16 if value.startswith('0x') else 10)


def numeric(value):
    if '/' in value:
        a,b=value.split('/',1);return str(number(a))+'/'+str(number(b))
    return str(number(value))


def fields(tokens):
    result={};modules=[];index=0;negated=False
    unary={'--restore-mark','--save-mark','--clamp-mss-to-pmtu'}
    binary={'-i','-o','-p','-j','--dst-type','--dport','--mark','--set-xmark','--nfmask','--ctmask','--ctstate','--ttl-set','--ttl-inc','--ttl-dec','--tcp-flags','--set-mss'}
    while index<len(tokens):
        token=tokens[index];index+=1
        if token=='!':
            if negated:raise ValueError('KERNEL-POLICY-UNVERIFIED')
            negated=True;continue
        if token=='-m':
            if negated or index>=len(tokens):raise ValueError('KERNEL-POLICY-UNVERIFIED')
            module=tokens[index];index+=1
            if module=='comment':
                if tokens[index:index+1]!=['--comment'] or index+1>=len(tokens):raise ValueError('KERNEL-POLICY-UNVERIFIED')
                index+=2;continue
            modules.append(module);continue
        key=('! ' if negated else '')+token;negated=False
        if key in result:raise ValueError('KERNEL-POLICY-UNVERIFIED')
        if token in unary:result[key]=True
        elif token in binary:
            count=2 if token=='--tcp-flags' else 1
            if index+count>len(tokens):raise ValueError('KERNEL-POLICY-UNVERIFIED')
            value=' '.join(tokens[index:index+count]);index+=count
            if token in ('--mark','--set-xmark','--nfmask','--ctmask'):value=numeric(value)
            result[key]=value
        else:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    if negated or len(modules)!=len(set(modules)):raise ValueError('KERNEL-POLICY-UNVERIFIED')
    if modules:result['-m']=tuple(sorted(modules))
    return result


def parse_mangle(text):
    if not isinstance(text,str) or len(text)>2*1024*1024:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    chains={};opened=False;committed=False
    for line in text.splitlines():
        if not line or line.startswith('#'):continue
        if line=='*mangle':
            if opened:raise ValueError('KERNEL-POLICY-UNVERIFIED')
            opened=True;continue
        if line=='COMMIT':committed=True;continue
        if not opened or committed:raise ValueError('KERNEL-POLICY-UNVERIFIED')
        if line.startswith(':'):
            match=re.fullmatch(r':([A-Za-z0-9_-]{1,64}) (?:ACCEPT|DROP|-) \[[0-9]+:[0-9]+\]',line)
            if not match or match.group(1) in chains:raise ValueError('KERNEL-POLICY-UNVERIFIED')
            if match.group(1)=='PREROUTING' and line.split()[1]!='ACCEPT':raise ValueError('KERNEL-POLICY-UNVERIFIED')
            chains[match.group(1)]=[];continue
        tokens=shlex.split(line)
        if len(tokens)<4 or tokens[0]!='-A' or tokens[1] not in chains:raise ValueError('KERNEL-POLICY-UNVERIFIED')
        chains[tokens[1]].append(tokens[2:])
    if not opened or not committed:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    return chains


def unrouted(text):
    """True when no LAN packet can get a route mark: what rtp2.sh leaves after its
    flush but before it recreated any TUNNEL route chain. Nothing to preserve."""
    chains=parse_mangle(text)
    if any(name.startswith('TUNNEL') for name in chains):return False
    pending=['PREROUTING'];seen=set()
    while pending:
        chain=pending.pop()
        if chain in seen:continue
        seen.add(chain)
        for tokens in chains.get(chain,[]):
            for flag in ('-j','-g'):
                if flag in tokens:
                    index=tokens.index(flag)
                    if index+1>=len(tokens):return False
                    target=tokens[index+1]
                    if target=='MARK' or target.startswith('TUNNEL'):return False
                    if target in chains:pending.append(target)
    return True


def rule_bindings(selection,marks,ip_rules):
    if not isinstance(ip_rules,list) or len(ip_rules)>400:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    if any(not isinstance(row,dict) or type(row.get('priority')) is not int for row in ip_rules):raise ValueError('KERNEL-POLICY-UNVERIFIED')
    if [row['priority'] for row in ip_rules]!=sorted(row['priority'] for row in ip_rules):raise ValueError('KERNEL-POLICY-UNVERIFIED')
    for key in ('source','target'):
        profile=selection[key];binding=profile.get('kernel_binding',{})
        value=marks[selection[key+'_rule']]
        if binding.get('code') is not None or binding.get('mark')!=value or not isinstance(binding.get('table'),str):raise ValueError('KERNEL-POLICY-UNVERIFIED')
        matching=[]
        for index,row in enumerate(ip_rules):
            if row.get('fwmark') is None:continue
            raw=str(row['fwmark']);raw_mark,separator,raw_mask=raw.partition('/')
            if number(raw_mark)!=value:continue
            mask=number(raw_mask if separator else row.get('fwmask',0xffffffff))
            if (mask!=MASK or str(row.get('table'))!=binding['table'] or set(row)-{'priority','src','dst','fwmark','fwmask','table','protocol'}
                    or row['priority']>=9910
                    or row.get('src','all') not in ('all','0.0.0.0/0') or row.get('dst','all') not in ('all','0.0.0.0/0')):
                raise ValueError('KERNEL-POLICY-UNVERIFIED')
            matching.append(index)
        if len(matching)!=1:raise ValueError('KERNEL-POLICY-UNVERIFIED')
        for prior in ip_rules[:matching[0]]:
            if prior.get('fwmark') is not None:
                raw=str(prior['fwmark']);raw_mark,separator,raw_mask=raw.partition('/')
                mask=number(raw_mask if separator else prior.get('fwmask',0xffffffff))
                applies=value&mask==number(raw_mark)&mask
                if 'not' in prior:applies=not applies
                if not applies:continue
            if 'not' not in prior and isinstance(prior.get('iif'),str) and prior['iif']!='br-lan':continue
            if prior=={'priority':0,'src':'all','table':'local'}:continue
            if prior=={'priority':800,'src':'all','table':'9910','suppress_prefixlen':0}:continue
            raise ValueError('KERNEL-POLICY-UNVERIFIED')


def missing_only(policy,selection,mangle,ip_rules):
    """Only wholly absent stock chains with an otherwise understood LAN hook may be repaired."""
    from native_switch import section_id
    from process_policy import mark
    from pair_policy import proof,role
    identity=proof(selection);role(identity,selection['order'])
    chains=parse_mangle(mangle)
    if any(name in ('VPN_PREROUTING_HOOK','ROUTE_POLICY','LOCAL_POLICY','POST_ROUTE_POLICY') or name.startswith('TUNNEL') for name in chains):return False
    sections={section_id(row,selection.get('process_bindings')):row for row in policy['sections']}
    marks={key:mark(sections[key].get('mark')) for key in identity['generic_rules']}
    rule_bindings(selection,marks,ip_rules)
    def safe(chain,seen=()):
        if chain in seen or chain not in chains:return False
        for tokens in chains[chain]:
            entry=fields(tokens);target=entry.get('-j')
            if target in ('TTL','TCPMSS') or target=='RETURN' and chain!='PREROUTING':continue
            if target=='PORTAL_TTL' and safe(target,seen+(chain,)):continue
            return False
        return True
    return identity['direction']=='first' and safe('PREROUTING')


def attest(policy,selection,mangle,ip_rules):
    from native_switch import section_id
    from pair_policy import proof,role
    from process_policy import mark
    identity=proof(selection);selected=role(identity,selection['order'])
    if identity['direction']!='first':raise ValueError('KERNEL-POLICY-UNVERIFIED')  # Pinned FW3 zero-mark rules run in list order.
    chains=parse_mangle(mangle)
    if not isinstance(ip_rules,list) or len(ip_rules)>400:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    prerouting=[fields(tokens) for tokens in chains.get('PREROUTING',[])]
    if prerouting.count({'-j':'VPN_PREROUTING_HOOK'})!=1:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    def harmless(chain,seen=()):
        if chain in seen or chain not in chains:raise ValueError('KERNEL-POLICY-UNVERIFIED')
        for tokens in chains[chain]:
            entry=fields(tokens);target=entry.get('-j')
            if target in ('TTL','TCPMSS','RETURN'):continue
            if target not in ('PORTAL_TTL',):raise ValueError('KERNEL-POLICY-UNVERIFIED')
            harmless(target,seen+(chain,))
    for entry in prerouting:
        if entry=={'-j':'VPN_PREROUTING_HOOK'}:continue
        if entry.get('-j') in ('TCPMSS','TTL'):continue
        if entry.get('-j')=='PORTAL_TTL':harmless('PORTAL_TTL');continue
        raise ValueError('KERNEL-POLICY-UNVERIFIED')
    hook=[fields(tokens) for tokens in chains.get('VPN_PREROUTING_HOOK',[])]
    if hook.count({'-i':'br-lan','-j':'ROUTE_POLICY'})!=1:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    for entry in hook:
        if entry=={'-i':'br-lan','-j':'ROUTE_POLICY'}:continue
        target=entry.get('-j')
        if entry=={'-j':target} and target in ('vpn_in_new_mark','wan_in_new_mark'):
            if target not in chains:raise ValueError('KERNEL-POLICY-UNVERIFIED')
            for tokens in chains[target]:
                # These stock ingress rules are explicitly bound to a non-LAN device.
                ingress=fields(tokens);interface=ingress.get('-i')
                if not interface or interface=='br-lan' or not re.fullmatch(r'[A-Za-z0-9_.-]{1,15}',interface):raise ValueError('KERNEL-POLICY-UNVERIFIED')
            continue
        if target=='CONNMARK' and entry.get('--save-mark') is True and '--restore-mark' not in entry:continue
        if entry.get('-i') not in (None,'br-lan') and re.fullmatch(r'[A-Za-z0-9_.-]{1,15}',entry['-i']):continue
        raise ValueError('KERNEL-POLICY-UNVERIFIED')
    sections={section_id(row,selection.get('process_bindings')):row for row in policy['sections']}
    expected=[];marks={}
    for rule_id in sorted(identity['generic_rules'],key=selection['order'].index):
        row=sections[rule_id];tunnel=row.get('tunnel_id')
        if not isinstance(tunnel,str) or not re.fullmatch(r'[0-9]{1,12}',tunnel):raise ValueError('KERNEL-POLICY-UNVERIFIED')
        chain='TUNNEL'+tunnel+'_ROUTE_POLICY';expected.append({'-m':('addrtype',),'! --dst-type':'LOCAL','-j':chain})
        value=mark(row.get('mark'));marks[rule_id]=value
        zero='0/'+str(MASK)
        wanted=[{'-m':('mark',),'--mark':zero,'-j':'MARK','--set-xmark':str(value)+'/'+str(MASK)},
                {'-m':('mark',),'--mark':zero,'-j':'DROP'}]
        if [fields(tokens) for tokens in chains.get(chain,[])]!=wanted:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    route=[fields(tokens) for tokens in chains.get('ROUTE_POLICY',[])]
    restore={'-m':('connmark',),'! --mark':'0/'+str(MASK),'-j':'CONNMARK','--restore-mark':True,'--nfmask':str(MASK),'--ctmask':str(MASK)}
    dns={'-m':('addrtype','udp'),'--dst-type':'LOCAL','-p':'udp','--dport':'53','-j':'RETURN'}
    if route!=[restore,dns]+expected:raise ValueError('KERNEL-POLICY-UNVERIFIED')
    rule_bindings(selection,marks,ip_rules)
    return {'verified':True,'role':selected,'profile_id':selection[selected]['id'],
            'policy_hash':selection['hash'],'order':list(selection['order']),
            'scope':'new IPv4 LAN catch-all marking; no external-client proof'}
