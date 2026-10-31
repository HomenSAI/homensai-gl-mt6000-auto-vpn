# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Whitelisted own-configuration setup. VPN keys/routes are never edited."""
import hashlib
import json
import re
import subprocess
import unicodedata
from uci_result import failure_code
from agent import inventory
from auto_control import control_lock


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('SETUP-RANGE')
    return str(value)


def label(value):
    # No control, format (bidi/zero-width), line/paragraph separator, surrogate or unassigned characters, and not only blanks.
    if (not isinstance(value,str) or not 1 <= len(value) <= 64 or not value.strip()
            or any(unicodedata.category(c) in ('Cc','Cf','Cs','Co','Cn','Zl','Zp') for c in value)):
        raise ValueError('SETUP-NAME')
    return value


def system_payload(arguments, profiles, existing=None):
    if set(arguments) != {'source','target','interval','duration','session_loss','servers'}:
        raise ValueError('SETUP-FIELDS')
    ids={p['id'] for p in profiles}
    if not isinstance(arguments['source'],str) or not isinstance(arguments['target'],str) or arguments['source'] not in ids or arguments['target'] not in ids or arguments['source']==arguments['target']:
        raise ValueError('SETUP-PROFILES')
    if type(arguments['session_loss']) is not bool:
        raise ValueError('SETUP-FIELDS')
    rows=server_rows(arguments['servers'],profiles)
    enabled={row['profile'] for row in rows if row['enabled']=='1'}
    if arguments['source'] not in enabled or arguments['target'] not in enabled:raise ValueError('SETUP-PRIMARY-RESERVE-DISABLED')
    from vendor_observation import current_bindings, tunnel_identity
    by_id={profile['id']:profile for profile in profiles}
    bindings=current_bindings(profiles)
    existing=existing if isinstance(existing,dict) else {}
    def anchor(side):
        identifier=arguments[side];bound=tunnel_identity(by_id[identifier])
        if bound in bindings and bindings[bound]['id']==identifier:return bound
        previous=existing.get('plan_'+side+'_tunnel')
        # Keep an explicitly saved channel through a vendor's member change,
        # only while that exact tunnel still has a known configured member.
        if existing.get('plan_'+side)==identifier and isinstance(previous,str) and previous in bindings:return previous
        return ''
    source_anchor=anchor('source');target_anchor=anchor('target')
    if source_anchor and source_anchor==target_anchor:raise ValueError('SETUP-SAME-TUNNEL')
    return {'main':{'plan_source':arguments['source'],'plan_target':arguments['target'],
                    'plan_source_tunnel':source_anchor,'plan_target_tunnel':target_anchor,
                    'interval':integer(arguments['interval'],10,300),'native_duration':integer(arguments['duration'],1,240),
                    'native_session_loss':'1' if arguments['session_loss'] else '0','setup_complete':'1'},'servers':rows}


def server_rows(servers, profiles):
    """Validate own metadata independently of whether a usable pair exists yet."""
    if not isinstance(servers,list) or len(servers)>400:raise ValueError('SETUP-FIELDS')
    ids={p['id'] for p in profiles}
    rows=[];seen=set()
    for row in servers:
        if not isinstance(row,dict) or set(row) != {'profile','name','channel','priority','enabled'}:
            raise ValueError('SETUP-SERVER')
        if not isinstance(row['profile'],str) or row['profile'] not in ids or row['profile'] in seen or type(row['enabled']) is not bool:
            raise ValueError('SETUP-PROFILES')
        seen.add(row['profile'])
        rows.append({'section':'srv_'+hashlib.sha256(row['profile'].encode()).hexdigest()[:16],
                     'profile':row['profile'],'name':label(row['name']),'channel':label(row['channel']),
                     'priority':integer(row['priority'],1,1000),'enabled':'1' if row['enabled'] else '0'})
    return rows


def telegram_payload(arguments):
    if not {'token','chat','enabled','interval'}<=set(arguments) or set(arguments)-{'token','chat','enabled','interval','schedule','hour','weekly','monthly','items'} or type(arguments['enabled']) is not bool:
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
    if 'items' in arguments:
        from telegram_items import encode
        main['telegram_items']=encode(arguments['items'])
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


def probe_payload(arguments):
    from probe_policy import LEVELS
    if not isinstance(arguments,dict) or set(arguments)!={'level','boost'} or type(arguments['boost']) is not bool:
        raise ValueError('PROBE-SETTINGS-FIELDS')
    if type(arguments['level']) is not int or arguments['level'] not in LEVELS:raise ValueError('PROBE-SETTINGS-RANGE')
    interval,measure=LEVELS[arguments['level']]
    from probe_policy import FORCED_BOOST_LEVELS
    boost=arguments['boost'] or arguments['level'] in FORCED_BOOST_LEVELS
    return {'main':{'probe_level':str(arguments['level']),'probe_boost':'1' if boost else '0',
                    'interval':str(interval),'measure_interval':str(measure)},'servers':[]}


def response_payload(arguments):
    from probe_policy import RESPONSE_METRICS
    if (not isinstance(arguments,dict) or 'metric' not in arguments or not set(arguments)<={'metric','compare','fast_switch'}
            or arguments['metric'] not in RESPONSE_METRICS
            or any(key in arguments and type(arguments[key]) is not bool for key in ('compare','fast_switch'))):
        raise ValueError('RESPONSE-METRIC-INVALID')
    main={'response_metric':arguments['metric']}
    if 'compare' in arguments:main['response_compare']='1' if arguments['compare'] else '0'
    # Owner switch for the fast channel change (fast_policy); default on, off means every switch uses the GL rebuild.
    if 'fast_switch' in arguments:main['fast_switch']='1' if arguments['fast_switch'] else '0'
    return {'main':main,'servers':[]}


def monitor_payload(arguments, probe_max=16):
    required={'interval','checkpoint','probe_limit','planning_enabled'}
    if not required<=set(arguments) or set(arguments)-required-{'live_log_limit','history_days'} or type(arguments['planning_enabled']) is not bool:raise ValueError('MONITOR-PREFERENCES-FIELDS')
    main={'interval':integer(arguments['interval'],10,300),'checkpoint':integer(arguments['checkpoint'],300,3600),
          'probe_limit':integer(arguments['probe_limit'],1,probe_max),'plan_enabled':'1' if arguments['planning_enabled'] else '0'}
    for key,high in (('live_log_limit',2000),('history_days',7)):
        if key in arguments:main[key]=integer(arguments[key],1,high)
    return {'main':main,'servers':[]}


def onboarding_payload(arguments, profiles, existing=None):
    """One explicit, complete app-owned preference transaction; no runtime actions."""
    if (not isinstance(arguments,dict) or set(arguments)!={'system','monitor','recovery','speed','telegram','appearance'}
            or any(not isinstance(value,dict) for value in arguments.values())):
        raise ValueError('ONBOARDING-FIELDS')
    system=arguments['system']
    if (set(system)!={'defer_pair','source','target','duration','session_loss','servers'}
            or type(system['defer_pair']) is not bool or type(system['session_loss']) is not bool):
        raise ValueError('ONBOARDING-SYSTEM-FIELDS')
    # Inventory and the running monitor already support legacy values up to 32.
    main=monitor_payload(arguments['monitor'],probe_max=32)['main']
    if system['defer_pair']:
        if system['source']!='' or system['target']!='' or arguments['monitor']['planning_enabled']:
            raise ValueError('ONBOARDING-PAIR-DEFERRED')
        rows=server_rows(system['servers'],profiles)
        main.update(native_duration=integer(system['duration'],1,240),
                    native_session_loss='1' if system['session_loss'] else '0')
    else:
        paired=system_payload({key:value for key,value in system.items() if key!='defer_pair'} |
                              {'interval':arguments['monitor']['interval']},profiles,existing)
        main.update(paired['main']);rows=paired['servers']
    from recovery_settings import payload as recovery_payload
    # Onboarding owns the check interval in its monitoring section only.
    # Do not let a second copy override the value shown in its review.
    if 'interval' in arguments['recovery']:raise ValueError('ONBOARDING-FIELDS')
    for payload in (recovery_payload(arguments['recovery']),speed_payload(arguments['speed'])):
        main.update(payload['main'])
    appearance=arguments['appearance']
    if (not {'language','design','theme'} <= set(appearance) or set(appearance)-{'language','design','theme','router_model'} or appearance['language'] not in ('en','ru')
            or appearance['design'] not in ('a','b','c') or appearance['theme'] not in ('system','light','dark')):
        raise ValueError('ONBOARDING-APPEARANCE')
    main.update({'appearance_'+key:appearance[key] for key in ('language','design','theme')})
    if 'router_model' in appearance:
        from device_profile import validate
        detected = (existing or {}).get('detected_router_model', 'unknown')
        main['router_model'] = validate(appearance['router_model'], detected)
    telegram=arguments['telegram']
    if type(telegram.get('configure')) is not bool:raise ValueError('ONBOARDING-TELEGRAM-FIELDS')
    if telegram['configure']:
        if set(telegram)!={'configure','token','chat','enabled','interval','schedule','hour','weekly','monthly','items'}:
            raise ValueError('ONBOARDING-TELEGRAM-FIELDS')
        fields={key:value for key,value in telegram.items() if key!='configure'}
        # An optional, disabled destination may be left empty. Never invent one,
        # clear a stored secret, or allow a new token with no destination.
        empty_destination=fields['enabled'] is False and fields['chat']=='' and fields['token']==''
        if empty_destination:fields['chat']='0'
        main.update(telegram_payload(fields)['main'])
        if empty_destination:main['telegram_chat']=''
    elif set(telegram)!={'configure'}:raise ValueError('ONBOARDING-TELEGRAM-FIELDS')
    main.update(onboarding_version='1',onboarding_complete='1',
                onboarding_pair_deferred='1' if system['defer_pair'] else '0')
    payload={'main':main,'servers':rows}
    if len(json.dumps(payload,ensure_ascii=True).encode())>65536:raise ValueError('ONBOARDING-TOO-LARGE')
    return payload


def save_onboarding(arguments):
    # Profile identity and controller/recovery guards are checked in the same
    # lock as the single writer. Nothing here accepts terms or starts Auto.
    with control_lock():
        current=inventory()
        from configuration_guard import blocked
        try:reason=blocked(current.get('settings',{}))
        except (OSError,ValueError,TypeError,AttributeError):reason='CONFIG-RECOVERY-UNVERIFIED'
        if reason:return {'saved':False,'code':reason}
        payload=onboarding_payload(arguments,current['profiles'],current.get('settings'))
        if 'router_model' in payload['main']:
            from device_profile import detect, validate
            validate(payload['main']['router_model'], detect())
        telegram=arguments['telegram']
        if telegram['configure'] and telegram['enabled'] and not telegram['token']:
            from telegram_report import option
            try:existing=option('telegram_token')
            except (OSError,ValueError,subprocess.SubprocessError):existing=''
            if not isinstance(existing,str) or not re.fullmatch(r'[0-9]{6,15}:[A-Za-z0-9_-]{30,100}',existing):
                return {'saved':False,'code':'TELEGRAM-TOKEN-REQUIRED'}
        from rpc_throttle import allow
        if not allow('setup:onboarding',2):return {'saved':False,'code':'RPC-RATE-LIMIT'}
        try:
            result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'],
                input=json.dumps(payload,ensure_ascii=True).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        except (OSError,subprocess.SubprocessError):
            return {'saved':False,'code':'SETUP-SAVE-UNCONFIRMED'}
        if result.returncode or result.stdout.strip()!=b'OK':
            return {'saved':False,'code':failure_code(result,'SETUP-SAVE-UNCONFIRMED')}
    return {'saved':True,'onboarding_complete':True,'onboarding_version':1,
            'mode':'monitor','requires_lan_certification':True}


def save(arguments, kind):
    if kind=='onboarding':return save_onboarding(arguments)
    if kind=='system':payload=None  # derive profile/channel anchors from a fresh snapshot inside the lock
    elif kind=='telegram':payload=telegram_payload(arguments)
    elif kind=='speed':payload=speed_payload(arguments)
    elif kind=='monitor':payload=monitor_payload(arguments)
    elif kind=='probe':payload=probe_payload(arguments)
    elif kind=='response':payload=response_payload(arguments)
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
    elif kind=='stats':
        from stats_mode import payload as stats_payload
        payload=stats_payload(arguments)
    else:raise ValueError('SETUP-KIND')
    with control_lock():
        if kind=='system':
            current=inventory()
            payload=system_payload(arguments,current['profiles'],current.get('settings'))
        if kind=='probe':
            # Cadence is not part of the Auto session fingerprint: every decision recomputes
            # its windows from the current interval. Only an active switch or speed test waits.
            from speed_pause import public as pause_status
            if pause_status().get('active'):return {'saved':False,'code':'SPEED-BUSY'}
            from native_switch import journal_read, Refused
            try:phase=journal_read().get('phase')
            except Refused:return {'saved':False,'code':'CONFIG-RECOVERY-UNVERIFIED'}
            if phase in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):return {'saved':False,'code':'PROBE-SETTINGS-BUSY'}
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
            from native_switch import journal_read, Refused
            try:phase=journal_read().get('phase')
            except Refused:return {'saved':False,'code':'CONFIG-RECOVERY-UNVERIFIED'}
            if phase in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING'):
                return {'saved':False,'code':'SETUP-STOP-FIRST'}
        from rpc_throttle import allow
        if not allow('setup:'+kind,2):return {'saved':False,'code':'RPC-RATE-LIMIT'}
        # A hung or killed writer may or may not have committed: say so instead of failing without an answer.
        try:
            result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'],
                input=json.dumps(payload,ensure_ascii=True).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        except (OSError,subprocess.SubprocessError):
            return {'saved':False,'code':'SETUP-SAVE-UNCONFIRMED'}
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
    from rpc_throttle import allow
    if not allow('setup_check',2):return {'passed':False,'scope':'isolated-synthetic-UCI-config','code':'RPC-RATE-LIMIT'}
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
