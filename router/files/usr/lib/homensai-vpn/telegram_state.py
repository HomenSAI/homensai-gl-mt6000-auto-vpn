# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Checksummed sender ledger with legacy migration and previous-good recovery."""
import math
import time
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


# Owner decision 07.11.2026: a HOLD (PAIR-OUTSIDE-CHANGE-HELD) or an automatic ADOPT (PAIR-OUTSIDE-CHANGE-ADOPTED) of a
# change made outside the app is told in Telegram. An ADOPT lasts seconds in the status (ARMED), so the pair records
# every decision when it is made in a bounded RAM ring (RUNTIME, the last OUTSIDE_KEEP, deduplicated by class, trigger
# and time); the sender (telegram_report.outside_notice) tells what it has not told yet on its next round. The item
# keeps the class, the trigger code, the reason code and the package NAMES only, never a value, key or endpoint.
# Lua: telegram.outside_entry / outside_items / outside_push, pair.lua's outside_notice (the same file and format).
OUTSIDE_FILE='telegram-outside-change.json'
OUTSIDE_SEEN='telegram-outside-notice.json'
OUTSIDE_KEEP=16
OUTSIDE_CLASSES=('HOLD','ADOPT','RELEASE')
OUTSIDE_RELEASES=('STOP','START')  # RELEASE (owner decision 07.11.2026): the owner's Stop / Start ended an outside-change HOLD
OUTSIDE_PACKAGES=12
# BH-05 (bug hunt 07.11.2026): each item also keeps 'mono', the monotonic seconds (CLOCK_MONOTONIC = /proc/uptime on a
# router that never suspends) when the decision was recorded. The ring lives in RAM, so its items never cross a boot and
# the sender ages them by this clock: a wall-clock step (boot before NTP, sysfixtime hours behind) no longer makes a
# fresh HOLD look older than OUTSIDE_MAX_AGE. Items without 'mono' keep the wall-clock age.
_mono=time.monotonic


def outside_mono(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:return None
    return float(value)


def outside_entry(verdict):
    """readopt_class row (or a stored item) -> the notice item, or None when it is not a valid decision."""
    if not isinstance(verdict,dict):return None
    decision=verdict.get('decision');trigger=verdict.get('trigger');why=verdict.get('why');stamp=verdict.get('time')
    if decision not in OUTSIDE_CLASSES or not isinstance(trigger,str) or not re.fullmatch(r'[A-Z0-9_-]{1,96}',trigger):return None
    release=verdict.get('release')
    if decision=='RELEASE' and release not in OUTSIDE_RELEASES:return None
    if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp) or stamp<=0:return None
    if not isinstance(why,str) or not re.fullmatch(r'[A-Z0-9_-]{1,96}',why):why='UNCLASSIFIED'
    packages=verdict.get('packages')
    names=[x for x in packages if isinstance(x,str) and re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,31}',x)][:OUTSIDE_PACKAGES] if isinstance(packages,list) else []
    stamp=float(stamp)
    item={'key':'%s:%s:%.3f'%(decision,trigger,stamp),'decision':decision,'trigger':trigger,'why':why,'packages':names,'time':stamp}
    if decision=='RELEASE':item['key']='RELEASE-%s:%s:%.3f'%(release,trigger,stamp);item['release']=release
    mono=outside_mono(verdict.get('mono'))
    if mono is not None:item['mono']=mono
    return item


def outside_items(ring):
    rows=ring.get('items') if isinstance(ring,dict) else None
    out=[];keys=set()
    for row in rows if isinstance(rows,list) else []:
        item=outside_entry(row)
        if item is not None and item['key'] not in keys:keys.add(item['key']);out.append(item)
    return out[-OUTSIDE_KEEP:]


def outside_push(ring,verdict,mono=None):
    items=outside_items(ring);item=outside_entry(verdict)
    if item is not None and 'mono' not in item and outside_mono(mono) is not None:item['mono']=float(mono)
    if item is not None and all(x['key']!=item['key'] for x in items):items.append(item)
    return {'items':items[-OUTSIDE_KEEP:]}


def outside_record(verdict):
    """The pair's hook: one local RAM write, no network, no lock, never raises (a lost notice never stops Auto)."""
    try:
        import agent
        path=agent.RUNTIME/OUTSIDE_FILE
        try:ring=read_json(path,{})
        except (OSError,ValueError):ring={}
        try:mono=_mono()
        except (OSError,ValueError):mono=None
        atomic_json(path,outside_push(ring,verdict,mono))
    except Exception:  # noqa: BLE001 -- a notice must never break the supervisor
        pass
