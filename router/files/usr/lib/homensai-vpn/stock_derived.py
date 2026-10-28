"""Narrow semantics of the pinned GL.iNet no-override rule preparation.

Inputs, other interfaces and relative routing-rule order remain significant.
"""
import copy
import re


def anonymous(value):
    return value is True or type(value) is str and value=='1'


def no_override_options(section,bindings):
    from process_policy import mark,validate
    try:bindings=validate(bindings)
    except ValueError:return False
    via=section.get('via')
    if (bindings is None or via not in bindings or not anonymous(section.get('.anonymous'))
            or section.get('.type')!='rule' or section.get('enabled')!='1' or section.get('killswitch')!='1'
            or section.get('options_in_used')!='0'
            or any(key in section for key in ('mtu','masq','local_access'))
            or any(section.get(key) not in (None,'',[]) for key in ('from_type','from','to_type','to','to_manual','to_list_external'))):return False
    try:
        if mark(section.get('mark'))!=bindings[via]:return False
    except ValueError:return False
    def digits(value):return isinstance(value,str) and re.fullmatch(r'[0-9]{1,10}',value)
    if section.get('via_type')=='wireguard':
        return bool(re.fullmatch(r'wgclient[1-5]',via) and digits(section.get('peer_id')))
    if section.get('via_type')=='openvpn':
        return bool(re.fullmatch(r'ovpnclient[1-5]',via) and digits(section.get('group_id'))
                    and digits(section.get('client_id',section.get('peer_id'))))
    return False


def network_partition(rows):
    """Ignore only interleaving of IPv4 rules with non-rule sections.

Each subsequence retains every value, duplicate and relative position. UCI's
generated anonymous names are parser identities, not configured names.
"""
    result={'ipv4_rules':[],'other_sections':[]}
    for original in rows:
        row=copy.deepcopy(original)
        if anonymous(row.get('.anonymous')) and isinstance(row.get('.name'),str) and re.fullmatch(r'cfg[0-9a-fA-F]{6,16}',row['.name']):
            row.pop('.name')
        result['ipv4_rules' if row.get('.type')=='rule' else 'other_sections'].append(row)
    return result
