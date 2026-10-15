"""Whitelisted own-configuration setup. VPN keys/routes are never edited."""
import hashlib
import json
import re
import subprocess
from agent import inventory
from auto_control import control_lock


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('SETUP-RANGE')
    return str(value)


def label(value):
    if not isinstance(value,str) or not 1 <= len(value) <= 64 or any(ord(c)<32 for c in value):
        raise ValueError('SETUP-NAME')
    return value


def system_payload(arguments, profiles):
    if set(arguments) != {'source','target','interval','duration','session_loss','servers'}:
        raise ValueError('SETUP-FIELDS')
    ids={p['id'] for p in profiles}
    if not isinstance(arguments['source'],str) or not isinstance(arguments['target'],str) or arguments['source'] not in ids or arguments['target'] not in ids or arguments['source']==arguments['target']:
        raise ValueError('SETUP-PROFILES')
    if type(arguments['session_loss']) is not bool or not isinstance(arguments['servers'],list) or len(arguments['servers'])>400:
        raise ValueError('SETUP-FIELDS')
    rows=[];seen=set()
    for row in arguments['servers']:
        if not isinstance(row,dict) or set(row) != {'profile','name','channel','priority','enabled'}:
            raise ValueError('SETUP-SERVER')
        if not isinstance(row['profile'],str) or row['profile'] not in ids or row['profile'] in seen or type(row['enabled']) is not bool:
            raise ValueError('SETUP-PROFILES')
        seen.add(row['profile'])
        rows.append({'section':'srv_'+hashlib.sha256(row['profile'].encode()).hexdigest()[:16],
                     'profile':row['profile'],'name':label(row['name']),'channel':label(row['channel']),
                     'priority':integer(row['priority'],1,1000),'enabled':'1' if row['enabled'] else '0'})
    return {'main':{'plan_source':arguments['source'],'plan_target':arguments['target'],
                    'interval':integer(arguments['interval'],10,300),'native_duration':integer(arguments['duration'],1,240),
                    'native_session_loss':'1' if arguments['session_loss'] else '0','setup_complete':'1'},'servers':rows}


def telegram_payload(arguments):
    if set(arguments) != {'token','chat','enabled','interval'} or type(arguments['enabled']) is not bool:
        raise ValueError('TELEGRAM-SETUP-FIELDS')
    token=arguments['token'];chat=arguments['chat']
    if not isinstance(token,str) or (token and not re.fullmatch(r'[0-9]{6,15}:[A-Za-z0-9_-]{30,100}',token)):
        raise ValueError('TELEGRAM-TOKEN-FORMAT')
    # Private/group/channel numeric IDs or a public channel username.
    if not isinstance(chat,str) or not re.fullmatch(r'(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})',chat):
        raise ValueError('TELEGRAM-DESTINATION-FORMAT')
    main={'telegram_chat':chat,'telegram_enabled':'1' if arguments['enabled'] else '0',
          'telegram_interval':integer(arguments['interval'],5,10080)}
    if token:main['telegram_token']=token
    return {'main':main,'servers':[]}


def save(arguments, kind):
    payload=system_payload(arguments,inventory()['profiles']) if kind=='system' else telegram_payload(arguments)
    with control_lock():
        if kind=='telegram' and not arguments['token']:
            from telegram_report import option
            if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+',option('telegram_token')):
                return {'saved':False,'code':'TELEGRAM-TOKEN-REQUIRED'}
        if kind=='system':
            from agent import RUNTIME, read_json
            if read_json(RUNTIME/'native-status.json',{}).get('state') in ('OBSERVING','ARMED','APPLYING','WAIT-CLIENT','COMMITTED'):
                return {'saved':False,'code':'SETUP-STOP-FIRST'}
            from native_switch import journal_read
            if journal_read().get('phase') in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING'):
                return {'saved':False,'code':'SETUP-STOP-FIRST'}
        result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'],
            input=json.dumps(payload,ensure_ascii=True).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        if result.returncode or result.stdout.strip()!=b'OK':
            return {'saved':False,'code':'SETUP-SAVE-FAILED'}
    return {'saved':True,'mode':'monitor','requires_lan_certification':True}
