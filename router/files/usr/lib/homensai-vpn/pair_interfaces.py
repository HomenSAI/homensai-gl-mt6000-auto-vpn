"""Bounded configured client identities, independent of their numeric slot."""
import re

LEGACY={'wgclient1':'wgclient','ovpnclient1':'ovpnclient'}


def protocol(name):
    if not isinstance(name,str):raise ValueError('PAIR-PROFILES-UNVERIFIED')
    match=re.fullmatch(r'(wgclient|ovpnclient)([1-9][0-9]{0,3})',name)
    if not match:raise ValueError('PAIR-PROFILES-UNVERIFIED')
    return match[1]


def validate(values):
    if not isinstance(values,dict) or len(values)!=2:raise ValueError('PAIR-PROFILES-UNVERIFIED')
    if any(protocol(name)!=proto for name,proto in values.items()):raise ValueError('PAIR-PROFILES-UNVERIFIED')
    return dict(values)


def roles(settings):
    result={}
    for role,legacy in (('source','wgclient1'),('target','ovpnclient1')):
        anchor=settings.get('plan_'+role+'_tunnel')
        if not anchor:result[role]=legacy;continue
        if not isinstance(anchor,str) or anchor.count(':')!=1:raise ValueError('PAIR-PROFILES-UNVERIFIED')
        kind,name=anchor.split(':');proto=protocol(name)
        if kind!=('wireguard' if proto=='wgclient' else 'openvpn'):raise ValueError('PAIR-PROFILES-UNVERIFIED')
        result[role]=name
    validate({name:protocol(name) for name in result.values()})
    return result


def selection(rows):
    result={}
    for role in ('source','target'):
        row=rows.get(role,{})
        if not isinstance(row,dict):raise ValueError('PAIR-PROFILES-UNVERIFIED')
        name=row.get('interface');proto=protocol(name)
        if row.get('protocol') not in (None,'wireguard' if proto=='wgclient' else 'openvpn'):
            raise ValueError('PAIR-PROFILES-UNVERIFIED')
        result[name]=proto
    return validate(result)


def state(value):
    return validate(value.get('interfaces',LEGACY))
