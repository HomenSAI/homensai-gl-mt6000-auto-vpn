"""Exact derived GL.iNet process binding, scoped to the selected VPN pair.

Audited RTP sets gl_process_vpn to the first enabled VPN rule. The controller
hashes its other fields and the exact pair; a third interface/mark is foreign.
"""
import re


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
