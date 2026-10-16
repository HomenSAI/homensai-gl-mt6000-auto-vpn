"""Review/apply own display priorities with stale-snapshot protection; no route writes."""
import hashlib
import json
import re
import subprocess
from agent import inventory
from auto_control import control_lock
from configuration_guard import blocked


def snapshot(data):
    profiles={p['id']:p for p in data['profiles']}
    stored={s['profile']:s for s in data.get('servers',[])}
    rows=[]
    for identifier,profile in profiles.items():
        custom=stored.get(identifier,{})
        priority=custom.get('priority',100)
        if type(priority) is not int or not 1<=priority<=1000:priority=100
        rows.append({'profile':identifier,'name':custom.get('name') or profile['name'],
                     'channel':custom.get('channel') or 'default','priority':priority,
                     'enabled':custom.get('enabled',True) is not False,'protocol':profile.get('protocol','unknown')})
    rows.sort(key=lambda row:(row['priority'],row['profile']))
    raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return rows,hashlib.sha256(raw).hexdigest()


def proposed(data,ordered):
    rows,revision=snapshot(data)
    if not isinstance(ordered,list) or not 1<=len(ordered)<=400 or any(not isinstance(x,str) for x in ordered) or len(set(ordered))!=len(ordered):
        raise ValueError('PRIORITY-INVALID-SELECTION')
    known={row['profile']:row for row in rows}
    if any(identifier not in known or known[identifier]['enabled'] is False for identifier in ordered):raise ValueError('PRIORITY-PROFILE-INELIGIBLE')
    order=ordered+[row['profile'] for row in rows if row['profile'] not in ordered]
    result=[dict(known[identifier],priority=index+1) for index,identifier in enumerate(order)]
    return result,revision


def preview(arguments):
    if set(arguments)!={'ordered'}:return {'accepted':False,'code':'PRIORITY-FIELDS'}
    try:rows,revision=proposed(inventory(),arguments['ordered'])
    except ValueError as error:return {'accepted':False,'code':str(error)}
    return {'accepted':True,'revision':revision,'rows':rows,'scope':'own metadata only; no live route change'}


def apply(arguments):
    if set(arguments)!={'ordered','revision'} or not isinstance(arguments['revision'],str) or not re.fullmatch(r'[a-f0-9]{64}',arguments['revision']):
        return {'saved':False,'code':'PRIORITY-FIELDS'}
    with control_lock():
        data=inventory();reason=blocked(data.get('settings',{}))
        if reason:return {'saved':False,'code':reason}
        try:rows,revision=proposed(data,arguments['ordered'])
        except ValueError as error:return {'saved':False,'code':str(error)}
        if revision!=arguments['revision']:return {'saved':False,'code':'PRIORITY-STALE-REVIEW'}
        payload={'main':{},'servers':[]}
        for row in rows:
            payload['servers'].append({'section':'srv_'+hashlib.sha256(row['profile'].encode()).hexdigest()[:16],
                **{key:row[key] for key in ('profile','name','channel')},'priority':str(row['priority']),'enabled':'1' if row['enabled'] else '0'})
        result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'],input=json.dumps(payload,ensure_ascii=True).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        if result.returncode or result.stdout.strip()!=b'OK':return {'saved':False,'code':'PRIORITY-SAVE-FAILED'}
        return {'saved':True,'code':'PRIORITY-SAVED','route_changed':False,'count':len(rows)}
