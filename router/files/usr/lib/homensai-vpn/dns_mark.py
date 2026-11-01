"""LAN DNS follows the active channel (lua/dns_mark.lua, the same behaviour).

GL's kernel module dns_mark marks every LAN DNS query sent to the router; the mark then selects the per-tunnel
dnsmasq in `iptables -t nat policy_redirect` (0x1000 -> :2153 wgclient1, 0xb000 -> :4253 ovpnclient2). Its rules
(/proc/dns_mark/rule<tunnel_id>/mark) have empty blacklists, so the FIRST rule of /proc/dns_mark/dump wins. The fast
switch reorders only ROUTE_POLICY, so after a switch LAN DNS kept the primary tunnel (measured 01.11.2026: 0 of 6
lookups during a primary outage). sync() writes the active route's mark into EVERY rule's `mark` file:
  * never `clear`/`create` (between them unmarked DNS would reach the main dnsmasq and leak to the WAN);
  * writes only a differing value, then reads every rule back;
  * /proc/dns_mark absent (other firmware): no-op, code DNS-MARK-UNAVAILABLE;
  * a write or read-back failure: code DNS-MARK-UNVERIFIED - logged, never a reason to roll a traffic switch back;
  * values are 0x[0-9a-f]+, rule names rule[0-9]+; no shell.
active_from_chains(chains): the mark of the tunnel whose ROUTE_POLICY jump is first (the kernel's live choice).
"""
import copy
import re

ROOT='/proc/dns_mark'
UNAVAILABLE='DNS-MARK-UNAVAILABLE'
UNVERIFIED='DNS-MARK-UNVERIFIED'
MAX_RULES=64
LAST=None  # the last sync() result in this process (native-status channel_path.dns_mark); never UNAVAILABLE

_VALUE=re.compile(r'0x[0-9a-f]{1,8}')
_RULE=re.compile(r'rule[0-9]{1,12}')
_DUMP=re.compile(r'^\s*Rule\s+([0-9]+):')


def valid_value(value):return isinstance(value,str) and _VALUE.fullmatch(value) is not None


def valid_rule(name):return isinstance(name,str) and _RULE.fullmatch(name) is not None


def format_mark(number):
    """number -> '0x..' (lower case), None when not a positive 31-bit integer."""
    if isinstance(number,bool) or not isinstance(number,int) or not 0<number<=0x7fffffff:return None
    return '0x%x'%number


def parse(text):
    """The text of a `mark` file -> int or None ('0x1000', '4096', 'Mark: 0xb000', with any whitespace)."""
    if not isinstance(text,str) or len(text)>256:return None
    s=text.strip()
    match=re.fullmatch(r'(?:[Mm]ark:\s*)?0[xX]([0-9a-fA-F]+)',s)
    if match:
        if len(match.group(1))>8:return None
        return int(match.group(1),16)
    if re.fullmatch(r'[0-9]{1,10}',s):return int(s,10)
    return None


def rules_of(dump):
    """Rule names in dump order ("Rule 5841: ... Mark: 0x1000"), each once."""
    out=[]
    for line in dump.split('\n'):
        match=_DUMP.match(line)
        if match:
            name='rule'+match.group(1)
            if valid_rule(name) and name not in out:out.append(name)
    return out


def default_read(path):
    try:
        with open(path,'rb') as stream:return stream.read(4096).decode('ascii','replace')
    except OSError:return None


def default_write(path,text):
    try:
        with open(path,'w',encoding='ascii') as stream:stream.write(text)
        return True
    except OSError:return False


def available(root=None,read=None):
    """The module's dump is readable (callers skip their iptables read otherwise)."""
    try:return isinstance((read or default_read)((ROOT if root is None else str(root))+'/dump'),str)
    except Exception:return False


def failed():
    """The result of a sync that could not run to its end (an unexpected error)."""
    global LAST
    LAST={'active':None,'rules':[],'verified':False,'code':UNVERIFIED,'written':0}
    return LAST


def sync(active,root=None,read=None,write=None):
    """-> {'active','rules':[{'rule','mark'}],'verified','code','written'}; never raises for I/O."""
    global LAST
    root=ROOT if root is None else str(root)
    read=read or default_read;write=write or default_write
    result={'active':active if valid_value(active) else None,'rules':[],'verified':False,'code':None,'written':0}
    def done(code=None):
        global LAST
        result.update(code=code,verified=code is None)
        if code!=UNAVAILABLE:LAST=result  # other firmware publishes nothing
        return result
    try:dump=read(root+'/dump')
    except Exception:dump=None
    if not isinstance(dump,str):return done(UNAVAILABLE)
    if not valid_value(active):return done(UNVERIFIED)
    want=int(active[2:],16)
    names=rules_of(dump)
    if len(names)>MAX_RULES:return done(UNVERIFIED)
    failed=False
    for name in names:
        path=root+'/'+name+'/mark'
        try:current=parse(read(path))
        except Exception:current=None
        if current!=want:
            try:wrote=write(path,active+'\n')
            except Exception:wrote=False
            if wrote:result['written']+=1
            else:failed=True
            try:current=parse(read(path))
            except Exception:current=None
        if current!=want:failed=True
        result['rules'].append({'rule':name,'mark':format_mark(current) if current else None})
    return done(UNVERIFIED if failed else None)


def active_from_chains(chains,fields):
    """chains: kernel_policy.parse_mangle(); the mark ('0x..') of the first TUNNEL<id>_ROUTE_POLICY jump, or None."""
    if not isinstance(chains,dict) or not isinstance(chains.get('ROUTE_POLICY'),list):return None
    for tokens in chains['ROUTE_POLICY']:
        try:entry=fields(tokens)
        except (ValueError,TypeError,KeyError,IndexError):return None
        target=entry.get('-j')
        if isinstance(target,str) and re.fullmatch(r'TUNNEL[0-9]+_ROUTE_POLICY',target):
            for rule in chains.get(target) or []:
                try:found=fields(rule)
                except (ValueError,TypeError,KeyError,IndexError):return None
                if found.get('-j')=='MARK' and isinstance(found.get('--set-xmark'),str):
                    match=re.fullmatch(r'([0-9]+)/[0-9]+',found['--set-xmark'])
                    return format_mark(int(match.group(1))) if match else None
            return None
    return None


def project(value):
    """The checked copy of a published dns_mark block (native-status channel_path.dns_mark), or None.
    The page and the bench read only this shape: {active, rules:[{rule, mark}], verified, code, written}."""
    if not isinstance(value,dict) or not isinstance(value.get('rules'),list) or len(value['rules'])>MAX_RULES:return None
    active=value.get('active');code=value.get('code');written=value.get('written')
    if active is not None and not valid_value(active):return None
    if code not in (None,UNVERIFIED,UNAVAILABLE):return None
    if isinstance(written,bool) or not isinstance(written,int) or not 0<=written<=MAX_RULES:return None
    if value.get('verified') is not (code is None):return None
    rules=[]
    for row in value['rules']:
        if not isinstance(row,dict) or not valid_rule(row.get('rule')) or (row.get('mark') is not None and not valid_value(row.get('mark'))):return None
        rules.append({'rule':row['rule'],'mark':row.get('mark')})
    return {'active':active,'rules':rules,'verified':value['verified'],'code':code,'written':written}


def view():
    """The published view of the last result (copy), or None."""
    return copy.deepcopy(LAST) if LAST is not None else None
