"""Exact derived GL.iNet process binding, scoped to the selected VPN pair.

The adapter aligns gl_process_vpn with the first enabled VPN rule before RTP;
the observed stock reload can otherwise retain its earlier binding. Other
fields and the exact pair stay hashed; a third interface/mark is foreign.
"""
import re
import json


def mark(value):
    if type(value) is not str or not re.fullmatch(r'(?:0x[0-9a-fA-F]{1,8}|[0-9]{1,10})', value):
        raise ValueError('POLICY-IDENTITY-CHANGED')
    number=int(value,16 if value.startswith('0x') else 10)
    if not 0<number<=0xffffffff:raise ValueError('POLICY-IDENTITY-CHANGED')
    return number


def validate(bindings):
    if bindings is None:return None
    if (not isinstance(bindings,dict) or len(bindings)!=2
            or any(type(k)is not str or not re.fullmatch(r'(?:wgclient|ovpnclient)[0-9]{1,4}',k)
                   or type(v)is not int or not 0<v<=0xffffffff for k,v in bindings.items())
            or len(set(bindings.values()))!=2):
        raise ValueError('POLICY-IDENTITY-CHANGED')
    return dict(bindings)


def system_section(section):
    return (section.get('.name')=='gl_process_vpn' and section.get('.type')=='rule_process'
            and section.get('enabled')=='1' and section.get('from_type')=='process_gid')


def recognizes(section,bindings):
    try:
        return (bindings is not None and system_section(section)
                and section.get('via') in bindings and mark(section.get('mark'))==bindings[section['via']])
    except ValueError:return False


def selected_bindings(sections,interfaces):
    system=[s for s in sections if s.get('.name')=='gl_process_vpn']
    if not system or not system_section(system[0]):return None
    if len(system)!=1:raise ValueError('POLICY-DUPLICATE-IDENTITY')
    result={}
    for interface in interfaces:
        rows=[s for s in sections if s.get('.type')=='rule' and s.get('enabled')=='1' and s.get('via')==interface]
        if len(rows)!=1:raise ValueError('POLICY-IDENTITY-CHANGED')
        result[interface]=mark(rows[0].get('mark'))
    result=validate(result)
    if not recognizes(system[0],result):raise ValueError('POLICY-IDENTITY-CHANGED')
    return result


def applied(sections,bindings):
    """After RTP, require its deterministic first enabled VPN rule binding."""
    if bindings is None:return True
    first=next((s for s in sections if s.get('.type')=='rule' and s.get('enabled')=='1' and s.get('via')!='novpn'),None)
    system=next((s for s in sections if s.get('.name')=='gl_process_vpn'),None)
    return bool(first and system and recognizes(system,bindings)
                and system.get('via')==first.get('via') and mark(system.get('mark'))==mark(first.get('mark')))


def synchronization_script(sections,bindings,stage):
    """CAS only the two already-owned derived fields before stock RTP.

    The observed FW3 order can preserve the old process rule on RTP reload.
    Both values must change atomically: an intermediate new-via/old-mark pair
    is deliberately foreign to the policy identity checks.
    """
    bindings=validate(bindings)
    if bindings is None or applied(sections,bindings):return None
    system=next((s for s in sections if s.get('.name')=='gl_process_vpn'),None)
    first=next((s for s in sections if s.get('.type')=='rule'and s.get('enabled')=='1'and s.get('via')!='novpn'),None)
    if (not system or not recognizes(system,bindings)or not first or first.get('via')not in bindings
            or mark(first.get('mark'))!=bindings[first['via']]):
        raise ValueError('POLICY-IDENTITY-CHANGED')
    if not isinstance(stage,str)or not re.fullmatch(r'/[A-Za-z0-9_./-]{1,240}',stage):
        raise ValueError('POLICY-IDENTITY-CHANGED')
    # Only validated interface names and mark literals enter this Lua source.
    values=[stage,system['via'],system['mark'],first['via'],first['mark']]
    quoted=[json.dumps(x)for x in values]
    return """local u=require('uci')
local pending=u.cursor():changes('route_policy');assert(not pending or next(pending)==nil,'pending')
local c=u.cursor('/etc/config',%s)
local s=c:get_all('route_policy','gl_process_vpn')
assert(s and s['.type']=='rule_process'and s.enabled=='1'and s.from_type=='process_gid','identity')
assert(s.via==%s and s.mark==%s,'changed')
local first=nil
c:foreach('route_policy','rule',function(r)if not first and r.enabled=='1'and r.via~='novpn'then first=r end end)
assert(first and first.via==%s and first.mark==%s,'order')
assert(c:set('route_policy','gl_process_vpn','via',first.via))
assert(c:set('route_policy','gl_process_vpn','mark',first.mark))
assert(c:save('route_policy'));assert(c:commit('route_policy'))
local fresh=u.cursor('/etc/config',%s)
assert(fresh:get('route_policy','gl_process_vpn','via')==first.via and fresh:get('route_policy','gl_process_vpn','mark')==first.mark,'readback')
""" % tuple(quoted+[quoted[0]])
