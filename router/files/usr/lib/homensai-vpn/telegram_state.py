# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
"""Checksummed sender ledger with legacy migration and previous-good recovery."""
import math
import re
from agent import PERSIST, read_json, atomic_json, checksum


def valid(data):
    if not isinstance(data,dict):return False
    allowed={'sent','attempt','calendar_started','period_keys','uncertain','config_fingerprint','last_code',
             'snapshot','retry_handled','retry_nonce','retry_after','confirmed_at','confirmed_reports','known_failures','unknown_deliveries'}
    if set(data)-allowed:return False
    for key in ('sent','attempt','retry_handled','retry_after','confirmed_at','confirmed_reports','known_failures','unknown_deliveries'):
        value=data.get(key,0)
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:return False
    for key in ('calendar_started','period_keys','uncertain'):
        if not isinstance(data.get(key,{}),dict) or len(data.get(key,{}))>32:return False
    for key,value in data.get('period_keys',{}).items():
        if key not in ('interval','daily','weekly','monthly') or not isinstance(value,str) or len(value)>128 or not value.startswith(key+':'):return False
    if any(key not in ('daily','weekly','monthly') for key in data.get('calendar_started',{})):return False
    if any(not isinstance(key,str) or len(key)>128 or not re.fullmatch(r'(?:interval|daily|weekly|monthly):[0-9-]+',key) for key in data.get('uncertain',{})):return False
    for key in ('config_fingerprint','retry_nonce'):
        if key in data and (not isinstance(data[key],str) or not re.fullmatch(r'[a-f0-9]{32,64}',data[key])):return False
    for key in ('calendar_started','uncertain'):
        if any(not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 for value in data.get(key,{}).values()):return False
    if 'last_code' in data and (not isinstance(data['last_code'],str) or not re.fullmatch(r'TELEGRAM-[A-Z0-9_-]+',data['last_code'])):return False
    snapshot=data.get('snapshot')
    if snapshot is not None:
        if not isinstance(snapshot,dict) or set(snapshot)-{'time','wan','vpn'}:return False
        stamp=snapshot.get('time',0)
        if not isinstance(stamp,(int,float)) or not math.isfinite(stamp) or stamp<0:return False
        for key in ('wan','vpn'):
            rows=snapshot.get(key,{})
            if not isinstance(rows,dict) or len(rows)>18:return False
            if any(not isinstance(month,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}',month) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 for month,value in rows.items()):return False
    return True


def unwrap(raw):
    if isinstance(raw,dict) and raw.get('schema')==1:
        data=raw.get('data')
        if raw.get('sha256')!=checksum(data) or not valid(data):raise ValueError('TELEGRAM-STATE-CORRUPT')
        return data
    if valid(raw):return raw
    raise ValueError('TELEGRAM-STATE-CORRUPT')


def load(directory=None):
    directory=directory or PERSIST;found=False
    for index,name in enumerate(('telegram-state.json','telegram-state.backup.json')):
        try:
            raw=read_json(directory/name)
            if raw is None:continue
            found=True;data=unwrap(raw)
            return data,'TELEGRAM-STATE-RECOVERED' if index else None
        except (OSError,ValueError,TypeError):found=True
    return ({},'TELEGRAM-STATE-CORRUPT') if found else ({},None)


def save(data,directory=None):
    if not valid(data):raise ValueError('TELEGRAM-STATE-CORRUPT')
    directory=directory or PERSIST;path=directory/'telegram-state.json'
    try:
        old=read_json(path)
        if old is not None:unwrap(old);atomic_json(directory/'telegram-state.backup.json',old)
    except (OSError,ValueError,TypeError):pass
    atomic_json(path,{'schema':1,'data':data,'sha256':checksum(data)})
