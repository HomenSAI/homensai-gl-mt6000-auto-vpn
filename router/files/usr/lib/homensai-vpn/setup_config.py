# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
"""Whitelisted own-configuration setup. VPN keys/routes are never edited."""
import hashlib
import json
import re
import subprocess
from uci_result import failure_code
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
    enabled={row['profile'] for row in rows if row['enabled']=='1'}
    if arguments['source'] not in enabled or arguments['target'] not in enabled:raise ValueError('SETUP-PRIMARY-RESERVE-DISABLED')
    return {'main':{'plan_source':arguments['source'],'plan_target':arguments['target'],
                    'interval':integer(arguments['interval'],10,300),'native_duration':integer(arguments['duration'],1,240),
                    'native_session_loss':'1' if arguments['session_loss'] else '0','setup_complete':'1'},'servers':rows}


def telegram_payload(arguments):
    if not {'token','chat','enabled','interval'}<=set(arguments) or set(arguments)-{'token','chat','enabled','interval','schedule','hour','weekly','monthly'} or type(arguments['enabled']) is not bool:
        raise ValueError('TELEGRAM-SETUP-FIELDS')
    token=arguments['token'];chat=arguments['chat']
    if not isinstance(token,str) or (token and not re.fullmatch(r'[0-9]{6,15}:[A-Za-z0-9_-]{30,100}',token)):
        raise ValueError('TELEGRAM-TOKEN-FORMAT')
    # Private/group/channel numeric IDs or a public channel username.
    if not isinstance(chat,str) or not re.fullmatch(r'(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})',chat):
        raise ValueError('TELEGRAM-DESTINATION-FORMAT')
    main={'telegram_chat':chat,'telegram_enabled':'1' if arguments['enabled'] else '0',
          'telegram_interval':integer(arguments['interval'],5,10080)}
    if 'schedule' in arguments:
        if arguments['schedule'] not in ('interval','daily'):raise ValueError('TELEGRAM-SCHEDULE')
        main['telegram_schedule']=arguments['schedule']
    if 'hour' in arguments:main['telegram_hour']=integer(arguments['hour'],0,23)
    for flag in ('weekly','monthly'):
        if flag in arguments:
            if type(arguments[flag]) is not bool:raise ValueError('TELEGRAM-SCHEDULE')
            main['telegram_'+flag]='1' if arguments[flag] else '0'
    if token:main['telegram_token']=token
    return {'main':main,'servers':[]}


def speed_payload(arguments):
    fields={'enabled','auto_new','budget_mib','duration','streams','daily_mib','busy_mbps'}
    if set(arguments)!=fields or type(arguments['enabled']) is not bool or type(arguments['auto_new']) is not bool:
        raise ValueError('SPEED-CONFIG-FIELDS')
    main={'speed_enabled':'1' if arguments['enabled'] else '0','speed_auto_new':'1' if arguments['auto_new'] else '0'}
    for key,low,high in (('budget_mib',1,32),('duration',2,15),('streams',1,4),('daily_mib',1,1024),('busy_mbps',1,1000)):
        main['speed_'+key]=integer(arguments[key],low,high)
    if arguments['budget_mib']>arguments['daily_mib']:raise ValueError('SPEED-DAILY-LIMIT')
    return {'main':main,'servers':[]}


def monitor_payload(arguments):
    if set(arguments)!={'interval','checkpoint','probe_limit','planning_enabled'} or type(arguments['planning_enabled']) is not bool:raise ValueError('MONITOR-PREFERENCES-FIELDS')
    return {'main':{'interval':integer(arguments['interval'],10,300),'checkpoint':integer(arguments['checkpoint'],300,3600),
                    'probe_limit':integer(arguments['probe_limit'],1,16),'plan_enabled':'1' if arguments['planning_enabled'] else '0'},'servers':[]}


def save(arguments, kind):
    if kind=='system':payload=system_payload(arguments,inventory()['profiles'])
    elif kind=='telegram':payload=telegram_payload(arguments)
    elif kind=='speed':payload=speed_payload(arguments)
    elif kind=='monitor':payload=monitor_payload(arguments)
    elif kind=='terms':
        from agent import TERMS_VERSION
        import time
        # Only the exact current terms version can be accepted; the time is the router's, never the caller's.
        if set(arguments)!={'version'} or arguments['version']!=TERMS_VERSION:raise ValueError('TERMS-VERSION')
        payload={'main':{'terms_version':TERMS_VERSION,'terms_time':str(int(time.time()))},'servers':[]}
    elif kind=='forget':
        if arguments:raise ValueError('SETUP-FIELDS')
        # Deleting the stored token also turns reports off, so nothing keeps failing without it.
        payload={'main':{'telegram_enabled':'0'},'servers':[],'delete':['telegram_token']}
    elif kind=='recovery':
        from recovery_settings import payload as recovery_payload
        payload=recovery_payload(arguments)
    else:raise ValueError('SETUP-KIND')
    with control_lock():
        if kind in ('recovery','monitor'):
            from configuration_guard import blocked
            reason=blocked(inventory().get('settings',{}))
            if reason:return {'saved':False,'code':reason}
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
            return {'saved':False,'code':failure_code(result,'SETUP-SAVE-FAILED')}
    if kind=='speed' and not arguments['enabled']:
        from speed_test import cancel
        try:cancel()
        except (OSError,ValueError):return {'saved':True,'code':'SPEED-CANCEL-UNVERIFIED','cancel_requested':False}
    return {'saved':True,'mode':'monitor','requires_lan_certification':True}


def self_test():
    """Exercise the installed raw UCI writer against a synthetic temp config only."""
    import os
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory(prefix='homensai-setup-test-',dir='/tmp') as directory:
        root=Path(directory);(root/'config').mkdir();(root/'delta').mkdir()
        path=root/'config/homensai_vpn';path.write_text("config main 'main'\n option enabled '1'\n")
        payload={'main':{'interval':'30','setup_complete':'1'},'servers':[
            {'section':'srv_example','profile':'openvpn:1_1','name':'Example','channel':'Main','priority':'1','enabled':'1'}]}
        environment=dict(os.environ,HOMENSAI_SETUP_TEST_ROOT=directory)
        result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'],input=json.dumps(payload).encode(),
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,env=environment)
        text=path.read_text()
        passed=result.returncode==0 and result.stdout.strip()==b'OK' and 'srv_example' in text and 'openvpn:1_1' in text
        return {'passed':passed,'scope':'isolated-synthetic-UCI-config','code':'SETUP-CHECK-OK' if passed else 'SETUP-CHECK-FAILED'}
