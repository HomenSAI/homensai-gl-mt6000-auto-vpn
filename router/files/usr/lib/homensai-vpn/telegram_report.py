"""Telegram delivery; credentials never appear in inventory, status or logs."""
import json
import hashlib
import math
import socket
import ssl
import uuid
import urllib.error
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta


def option(name):
    try:
        result = subprocess.run(['/sbin/uci', '-q', 'get', 'homensai_vpn.main.'+name],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ''
    return result.stdout.decode().strip() if result.returncode == 0 else ''


def format_report(status, minutes, now=None, items=None):
    from telegram_items import ITEMS
    items=ITEMS if items is None else items
    now=time.time() if now is None else now
    if tuple(items)==('brief',):
        from telegram_brief import format_brief
        return format_brief(status,now-minutes*60,now,now)
    lines = ['HomenSAI Auto VPN · monitoring', datetime.fromtimestamp(now).strftime('%d.%m.%Y %H:%M Europe/Berlin'),
             'Report interval: %s min' % minutes]
    if 'servers' in items:
        lines.append('Currently connected servers:')
        active = [p for p in status.get('profiles', []) if p.get('interface')]
        for p in active:
            role='Primary channel' if p.get('role')=='source' else 'Reserve channel' if p.get('role')=='target' else 'Profile outside the confirmed pair'
            lines.append('%s · %s · %s · %s · HTTPS %s ms' %
                         (role,p['name'], p['protocol'], p.get('code') or 'OK', p.get('rtt_ms', '—')))
        if not active:
            lines.append('No connected profiles found.')
    cutoff = now-minutes*60
    if 'events' in items:
        events = [e for e in status.get('events', []) if e.get('time', 0) >= cutoff]
        lines.append('State changes during the interval: %s' % len(events))
        for event in events[-20:]:
            role='Primary channel' if event.get('role')=='source' else 'Reserve channel' if event.get('role')=='target' else 'Channel not saved in event' if event.get('profile') else 'Service'
            lines.append('%s · %s · %s · %s' % (datetime.fromtimestamp(event['time']).strftime('%H:%M:%S'),
                                          role,event.get('profile', 'service'), event.get('code', 'OK')))
    accounting = status.get('accounting', {})
    month = datetime.fromtimestamp(now).strftime('%Y-%m')
    if 'traffic' in items:
        traffic = accounting.get('months', {}).get(month)
        if traffic:
            lines.append('VPN traffic %s: %.3f GB (since monitoring started)' %
                         (month, (traffic.get('rx', 0)+traffic.get('tx', 0))/1e9))
        else:
            lines.append('Traffic: no accumulated measurements yet.')
    native=status.get('native_failover',{})
    if 'controller' in items:
        state=native.get('state','UNKNOWN')
        if not isinstance(state,str) or not re.fullmatch(r'[A-Z0-9_-]{1,96}',state):state='UNKNOWN'
        lines.append('Native controller: %s (not proof of LAN availability).' % state)
    # An alarm is never optional: it says that automatic switching has stopped.
    alarm=native.get('alarm')
    if isinstance(alarm,str) and re.fullmatch(r'[A-Z0-9_-]{1,96}',alarm):lines.append('ALARM: %s. Automatic switching is stopped; see the Events page and Help.' % alarm)
    history=status.get('native_history',{})
    if 'controller_events' in items:
        if history.get('error'):lines.append('Controller history unavailable: HISTORY-001.')
        native_events=[e for e in history.get('events',[]) if isinstance(e.get('time'),(int,float)) and e['time']>=cutoff]
        lines.append('Controller events during the interval: %s' % len(native_events))
        for event in native_events[-10:]:
            event_state=event.get('state','UNKNOWN')
            if not isinstance(event_state,str) or not re.fullmatch(r'[A-Z0-9_-]{1,96}',event_state):event_state='UNKNOWN'
            codes=[c for c in event.get('codes',[]) if isinstance(c,str) and re.fullmatch(r'[A-Z0-9_-]{1,96}',c)]
            lines.append('%s · %s%s · %s' % (datetime.fromtimestamp(event['time']).strftime('%H:%M:%S'),event_state,' · trial' if event.get('trial') else '',', '.join(codes)))
    totals=history.get('months',{}).get(month)
    if totals and 'controller_totals' in items:
        lines.append('Controller %s, accumulated: attempts %s; trials passed %s; automatic commits %s; rollbacks %s. This is a partial month.' % (month,totals.get('attempts',0),totals.get('trials_passed',0),totals.get('committed',0),totals.get('rollbacks',0)))
    if 'gaps' in items:
        lines.extend(['Observation gaps: %s' % accounting.get('gaps', 0),
                      'Router-originated IPv4 checks. A failure cause is stated only when supported by evidence.'])
    return '\n'.join(lines)[:4000]


class DeliveryError(Exception):
    def __init__(self,code,uncertain=False,retry_after=300):
        self.code=code;self.uncertain=uncertain;self.retry_after=retry_after
        super().__init__(code)


def config_snapshot():
    result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/telegram_private.lua'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=3)
    if result.returncode or len(result.stdout)>16384:raise ValueError('TELEGRAM-CONFIG')
    data=json.loads(result.stdout)
    if not isinstance(data,dict):raise ValueError('TELEGRAM-CONFIG')
    return data


def rejection(code,retry_after=300):
    known={400:'TELEGRAM-REQUEST-REJECTED',401:'TELEGRAM-TOKEN-REJECTED',403:'TELEGRAM-PERMISSION',429:'TELEGRAM-RATE-LIMIT'}
    return DeliveryError(known.get(code,'TELEGRAM-DELIVERY-UNKNOWN'),code not in known,max(300,min(3600,retry_after)))


def send_message(config,text):
    from report_calendar import limited_text
    token=config.get('telegram_token','');chat=config.get('telegram_chat','')
    if not isinstance(token,str) or not isinstance(chat,str) or not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+',token) or not re.fullmatch(r'(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})',chat):
        raise DeliveryError('TELEGRAM-CONFIG')
    payload=json.dumps({'chat_id':chat,'text':limited_text(text)}).encode()
    request=urllib.request.Request('https://api.telegram.org/bot'+token+'/sendMessage',data=payload,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=15) as response:
            raw=response.read(65537)
        if len(raw)>65536:raise DeliveryError('TELEGRAM-DELIVERY-UNKNOWN',True)
        result=json.loads(raw)
        if not isinstance(result,dict):raise DeliveryError('TELEGRAM-DELIVERY-UNKNOWN',True)
        if result.get('ok') is not True:
            delay=(result.get('parameters') or {}).get('retry_after',300)
            raise rejection(result.get('error_code'),delay if type(delay) is int else 300)
    except urllib.error.HTTPError as error:raise rejection(error.code)
    except urllib.error.URLError as error:
        if isinstance(error.reason,ssl.SSLCertVerificationError):raise DeliveryError('TELEGRAM-TLS')
        if isinstance(error.reason,socket.gaierror):raise DeliveryError('TELEGRAM-DNS')
        raise DeliveryError('TELEGRAM-DELIVERY-UNKNOWN',True)
    except DeliveryError:raise
    except Exception:raise DeliveryError('TELEGRAM-DELIVERY-UNKNOWN',True)


def traffic_snapshot(status,now):
    accounting=status.get('accounting',{})
    def totals(data):return {key:row.get('rx',0)+row.get('tx',0) for key,row in data.get('months',{}).items()}
    return {'time':status.get('time',now),'vpn':totals(accounting),'wan':totals(accounting.get('wan') or {})}


def delta_lines(status,saved,now):
    old=saved.get('snapshot');current=traffic_snapshot(status,now)
    if not isinstance(old,dict):return ['Traffic delta: unavailable until the first confirmed report snapshot.']
    lines=['Traffic delta since last confirmed report (%s):' % datetime.fromtimestamp(old.get('time',now)).strftime('%Y-%m-%d %H:%M')]
    for key,label in (('wan','WAN'),('vpn','VPN interfaces')):
        threshold=(datetime.fromtimestamp(old.get('time',now)).date().replace(day=1)-timedelta(days=1)).strftime('%Y-%m')
        before={month:value for month,value in old.get(key,{}).items() if month>=threshold}
        if not before or not current[key]:lines.append(label+': no comparable counters.');continue
        if any(month not in current[key] or current[key][month]<value for month,value in before.items()):
            lines.append(label+': counter discontinuity; delta is unknown.');continue
        delta=sum(value-before.get(month,0) for month,value in current[key].items() if month>=min(before))
        lines.append('%s: %.3f GB (available interface counters).' % (label,delta/1e9))
    return lines


# A long VENDOR-WORKER-BUSY (pair_auto.busy_fields) is told at once, apart from the schedule: no report is moved, the sender state
# and flash are not touched. RAM key: one notice per cause and pid until the state ends; a failed send is tried again after the
# usual backoff. The text says what was observed, not that GL is idle. Lua: telegram.vendor_notice (the same text and file).
NOTICE_FILE='telegram-vendor-notice.json'
NOTICE_MAX_AGE=60
NOTICE_TEXT={
    'VENDOR-BUSY-RTP-LOCK-DEAD':'The GL.iNet rtp2 lock file names a process that is no longer running. This does not prove GL.iNet has finished: a killed rtp2 can leave its child commands running. A router reboot clears the file.',
    'VENDOR-BUSY-RTP-LOCK-LIVE':'An rtp2 process named in the GL.iNet lock file is running.',
    'VENDOR-BUSY-TUNNEL-SWITCH':'A GL.iNet tunnel-switch lock file is present.',
    'VENDOR-BUSY-WORKERS':'No GL.iNet lock file is visible, but GL.iNet workers or service queues are running.',
    'VENDOR-BUSY-UNIDENTIFIED':'The router reports GL.iNet busy and the cause could not be identified. A missing file does not prove GL.iNet is idle.'}


def vendor_notice_key(native,now):
    if not isinstance(native,dict) or native.get('state')!='BLOCKED' or native.get('reason') not in NOTICE_TEXT:return None
    stamp=native.get('time')
    if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or now-stamp>NOTICE_MAX_AGE:return None
    pid=native.get('vendor_lock_pid')
    return '%s:%d'%(native['reason'],pid if isinstance(pid,int) and not isinstance(pid,bool) else 0)


def vendor_notice_text(native):
    pid=native.get('vendor_lock_pid');workers=native.get('vendor_workers')
    return ('HomenSAI Auto VPN notice: %s\nObserved: Auto has been blocked by VENDOR-WORKER-BUSY for %d s. %s'%(native['reason'],native.get('busy_seconds') or 0,NOTICE_TEXT[native['reason']])
            +('\nLock pid: %d'%pid if isinstance(pid,int) else '')+'\nVendor workers seen: '+(str(workers) if isinstance(workers,int) else 'not read')
            +'\nAuto stays blocked and makes no switch attempt. It does not remove any lock.')


def vendor_notice(config,status,state,now):
    """-> state"""
    from agent import RUNTIME,atomic_json,read_json
    from auto_control import control_lock
    native=status.get('native_failover');path=RUNTIME/NOTICE_FILE
    key=vendor_notice_key(native,now)
    try:known=read_json(path,{}).get('key')
    except (OSError,ValueError,AttributeError):known=None
    if key is None:
        if known is not None:
            try:path.unlink()
            except OSError:pass
        return state
    if known==key:return state
    with control_lock(RUNTIME/'telegram-control'):
        try:send_message(config,vendor_notice_text(native))
        except DeliveryError as error:
            counter='unknown_deliveries' if error.uncertain else 'known_failures'
            return dict(state,attempt=now,last_code=error.code,retry_after=error.retry_after,**{counter:state.get(counter,0)+1})
        atomic_json(path,{'key':key})
    return dict(state,last_code='TELEGRAM-DELIVERED')


# Owner decision 07.11.2026: a HOLD or an automatic ADOPT of a change made outside the app is told (telegram_state's RAM
# ring, written by the pair when it decides, so a seconds-long ADOPT is not lost before this round). Gated exactly like
# the VENDOR-BUSY notice: only from deliver(), i.e. Telegram on with a valid chat and token; the usual backoff holds it.
# At most one message per class (HOLD, ADOPT, RELEASE) every OUTSIDE_INTERVAL s: decisions within the window are not dropped,
# the next message tells the newest one and how many came before it. Older than OUTSIDE_MAX_AGE: marked, not sent.
# Text: class, trigger, reason and package NAMES only (validated codes and names), EN then RU. The told keys and the
# last message time per class live in RUNTIME (OUTSIDE_SEEN, bounded by the ring). Lua: telegram.outside_notice.
OUTSIDE_INTERVAL=600
OUTSIDE_MAX_AGE=21600
OUTSIDE_HEAD={
    'HOLD':('Auto found a configuration change made outside the app and HOLDS it: the change was not adopted, Auto is blocked and makes no switch.',
            'Auto обнаружил изменение настроек, сделанное вне приложения, и УДЕРЖИВАЕТ его: изменение не принято, Auto заблокирован и не переключает каналы.'),
    'ADOPT':('Auto found a configuration change made outside the app and adopted it by itself: only Wi-Fi, DHCP, the GL DNS page or the network interface class changed. Auto continues.',
             'Auto обнаружил изменение настроек, сделанное вне приложения, и принял его сам: изменились только Wi-Fi, DHCP, страница GL DNS или класс сетевых интерфейсов. Auto продолжает работу.'),
    # owner decision 07.11.2026: the hold ended by the owner (class RELEASE; the variant is item['release'], see outside_variant)
    'RELEASE_STOP':('The outside-change hold ended: owner Stop. The change was not adopted and Auto is stopped.',
                    'Удержание изменения, сделанного вне приложения, завершено: «Стоп» владельца. Изменение не принято, Auto остановлен.'),
    'RELEASE_START':('The outside-change hold ended: owner Start, new configuration accepted. Auto starts a new session with it, after the usual start checks.',
                     'Удержание изменения, сделанного вне приложения, завершено: «Старт» владельца, новая конфигурация принята. Auto начинает новую сессию с ней, после обычных проверок запуска.')}
OUTSIDE_TODO={
    'HOLD':('What to do: check the change. If it is yours, press Stop, then Start: Start adopts the current configuration. Until then Auto stays blocked.',
            'Что сделать: проверьте изменение. Если оно ваше, нажмите «Стоп», затем «Старт»: «Старт» примет текущую конфигурацию. До этого Auto остаётся заблокированным.'),
    'ADOPT':('Nothing to do.','Ничего делать не нужно.'),
    'RELEASE_STOP':('What to do: press Start when you want Auto to run again; Start takes the current configuration.',
                    'Что сделать: когда нужно снова запустить Auto, нажмите «Старт»: «Старт» примет текущую конфигурацию.'),
    'RELEASE_START':('Nothing to do.','Ничего делать не нужно.')}
OUTSIDE_CODE={'HOLD':'PAIR-OUTSIDE-CHANGE-HELD','ADOPT':'PAIR-OUTSIDE-CHANGE-ADOPTED','RELEASE':'PAIR-OUTSIDE-CHANGE-RELEASED'}


def outside_variant(item):
    return 'RELEASE_'+item['release'] if item['decision']=='RELEASE' else item['decision']


def outside_text(item,more=0,since=None):
    code=OUTSIDE_CODE[item['decision']]
    when=datetime.fromtimestamp(item['time']).strftime('%d.%m.%Y %H:%M')
    first=datetime.fromtimestamp(since if since is not None else item['time']).strftime('%d.%m.%Y %H:%M')
    names=' '.join(item['packages']) or '-'
    head=OUTSIDE_HEAD[outside_variant(item)];todo=OUTSIDE_TODO[outside_variant(item)]
    en=['HomenSAI Auto VPN notice: '+code,head[0],'Time: '+when,'Trigger: '+item['trigger'],'Changed packages: '+names,'Class: '+item['why'],todo[0]]
    ru=['Уведомление HomenSAI Auto VPN: '+code,head[1],'Время: '+when,'Причина: '+item['trigger'],'Изменённые пакеты: '+names,'Класс: '+item['why'],todo[1]]
    if more:
        en.append('%d earlier decision(s) of this class since %s were not sent separately (at most one message per class every 10 min).'%(more,first))
        ru.append('Ещё решений этого класса с %s, не отправленных отдельно: %d (не чаще одного сообщения на класс в 10 минут).'%(first,more))
    return '\n'.join(en)+'\n\n'+'\n'.join(ru)


def _mono_now():
    import telegram_state
    try:return telegram_state._mono()
    except (OSError,ValueError):return None


def outside_notice(config,state,now):
    """-> state"""
    from agent import RUNTIME,atomic_json,read_json
    from auto_control import control_lock
    from telegram_state import OUTSIDE_FILE,OUTSIDE_SEEN,OUTSIDE_CLASSES,outside_items,outside_mono
    try:items=outside_items(read_json(RUNTIME/OUTSIDE_FILE,{}))
    except (OSError,ValueError):items=[]
    try:seen=read_json(RUNTIME/OUTSIDE_SEEN,{})
    except (OSError,ValueError):seen={}
    if not isinstance(seen,dict):seen={}
    keys={x['key'] for x in items}
    told=seen.get('done') if isinstance(seen.get('done'),list) else []
    old_done=[k for k in told if isinstance(k,str) and k in keys]  # bounded by the ring
    last=seen.get('last') if isinstance(seen.get('last'),dict) else {}
    old_last={c:float(last[c]) for c in OUTSIDE_CLASSES if isinstance(last.get(c),(int,float)) and not isinstance(last.get(c),bool) and math.isfinite(last[c])}
    done=list(old_done);stamps=dict(old_last);sent=False
    pending=[x for x in items if x['key'] not in old_done]
    # BH-05: the age by the monotonic clock when the item has it (same boot: the ring is RAM), else by the wall clock
    mono_now=outside_mono(_mono_now())
    def age(x):
        if mono_now is not None and 'mono' in x and mono_now>=x['mono']:return mono_now-x['mono']
        return now-x['time']
    done+=[x['key'] for x in pending if age(x)>OUTSIDE_MAX_AGE]
    def store():
        if (done,stamps)!=(told,old_last):
            try:atomic_json(RUNTIME/OUTSIDE_SEEN,{'done':done,'last':stamps})
            except (OSError,ValueError):pass
    for cls in OUTSIDE_CLASSES:
        # BH2-05: sorted() is stable, so equal times keep the ring (insertion) order; lua/telegram.lua compares the ring index
        group=sorted((x for x in pending if x['decision']==cls and x['key'] not in done),key=lambda x:x['time'])
        if not group:continue
        previous=stamps.get(cls)
        if previous is not None and 0<=now-previous<OUTSIDE_INTERVAL:continue  # told together after the window
        if sent:time.sleep(1.05)
        with control_lock(RUNTIME/'telegram-control'):
            try:send_message(config,outside_text(group[-1],len(group)-1,group[0]['time']))
            except DeliveryError as error:
                store()
                counter='unknown_deliveries' if error.uncertain else 'known_failures'
                return dict(state,attempt=now,last_code=error.code,retry_after=error.retry_after,**{counter:state.get(counter,0)+1})
        done+=[x['key'] for x in group];stamps[cls]=float(now);sent=True
        state=dict(state,last_code='TELEGRAM-DELIVERED')
    store()
    return state

def deliver(status,saved,now):
    from agent import RUNTIME, read_json
    from auto_control import control_lock
    from report_calendar import prepare,format_period,limited_text
    from telegram_state import valid
    if not valid(saved):return {'enabled':True,'code':'TELEGRAM-STATE-CORRUPT'},saved,False
    try:config=config_snapshot()
    except (OSError,ValueError,subprocess.SubprocessError):return {'enabled':True,'code':'TELEGRAM-CONFIG'},saved,False
    if config.get('telegram_enabled')!='1':return {'enabled':False},saved,False
    if not isinstance(config.get('telegram_chat'),str) or not isinstance(config.get('telegram_token'),str) or not re.fullmatch(r'-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31}',config['telegram_chat']) or not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+',config['telegram_token']):
        return {'enabled':True,'code':'TELEGRAM-CONFIG'},saved,False
    fingerprint=hashlib.sha256(config['telegram_chat'].encode()).hexdigest()
    state=dict(saved)
    if state.get('config_fingerprint') not in (None,fingerprint):state={}
    state['config_fingerprint']=fingerprint
    request=read_json(RUNTIME/'telegram-retry.json',{})
    if request.get('id') and request['id']!=state.get('retry_nonce'):
        state['uncertain']={};state['retry_nonce']=request['id'];state['retry_handled']=now
    try:jobs,state,public=prepare(config,state,now)
    except (ValueError,TypeError):return {'enabled':True,'code':'TELEGRAM-CONFIG'},state,False
    public.update(enabled=True,last_sent=state.get('confirmed_at',state.get('sent',0)),uncertain_reports=len(state.get('uncertain',{})))
    if state.get('sent',0)>now+5:return dict(public,code='TELEGRAM-CLOCK-BACKWARD'),state,False
    remaining=state.get('retry_after',300)-(now-state.get('attempt',0))
    if remaining>0 and state.get('attempt',0):return dict(public,code=state.get('last_code','TELEGRAM-RETRY'),retry_in=math.ceil(remaining)),state,False
    state=vendor_notice(config,status,state,now)
    if state.get('attempt')!=now:state=outside_notice(config,state,now)  # not right after a failed VENDOR-BUSY notice
    if not jobs:
        if state.get('uncertain'):public['code']='TELEGRAM-DELIVERY-UNKNOWN'
        return public,state,False
    sent=False
    from telegram_items import parse
    items=parse(config.get('telegram_items'))
    with control_lock(RUNTIME/'telegram-control'):
        for index,job in enumerate(jobs):
            if index:time.sleep(1.05)
            state=dict(state,attempt=now)
            try:
                text=(format_report(status,job['minutes'],now,items)+('\n'+'\n'.join(delta_lines(status,state,now)) if 'delta' in items else '')) if job['kind']=='interval' else format_period(status,job,now,items)
                if job['kind']=='interval':text='Report id: '+job['key']+'\n'+text
            except Exception:
                state['last_code']='TELEGRAM-FORMAT-FAILED'
                return dict(public,code='TELEGRAM-FORMAT-FAILED'),state,sent
            try:send_message(config,limited_text(text))
            except DeliveryError as error:
                state['last_code']=error.code;state['retry_after']=error.retry_after
                counter='unknown_deliveries' if error.uncertain else 'known_failures'
                state[counter]=state.get(counter,0)+1
                if error.uncertain:
                    uncertain=dict(state.get('uncertain',{}));uncertain[job['key']]=now
                    state['uncertain']=dict(sorted(uncertain.items(),key=lambda pair:pair[1])[-16:])
                return dict(public,code=error.code,last_sent=state.get('sent',0),uncertain_reports=len(state.get('uncertain',{}))),state,sent
            keys=dict(state.get('period_keys',{}));keys[job['kind']]=job['key'];state['period_keys']=keys
            confirmed=time.time()
            state.update(sent=confirmed,confirmed_at=confirmed,last_code='TELEGRAM-DELIVERED',retry_after=300,snapshot=traffic_snapshot(status,now))
            state['confirmed_reports']=state.get('confirmed_reports',0)+1;sent=True
    return dict(public,last_sent=state.get('confirmed_at',now),uncertain_reports=len(state.get('uncertain',{}))),state,sent


def retry_unknown():
    from agent import RUNTIME,atomic_json
    from auto_control import control_lock
    from rpc_throttle import allow
    if not allow('telegram_retry',10):return {'queued':False,'code':'RPC-RATE-LIMIT'}
    with control_lock(RUNTIME):atomic_json(RUNTIME/'telegram-retry.json',{'id':uuid.uuid4().hex,'time':time.time()})
    return {'queued':True,'may_duplicate_uncertain_delivery':True}


def send_test():
    from agent import RUNTIME,read_json,atomic_json
    from auto_control import control_lock
    with control_lock(RUNTIME/'telegram-control'):
        now=time.time();path=RUNTIME/'telegram-test.json';old=read_json(path,{})
        if now-old.get('attempt',0)<60:return {'delivered':False,'code':'TELEGRAM-TEST-RATE-LIMIT'}
        try:config=config_snapshot()
        except (OSError,ValueError,subprocess.SubprocessError):return {'delivered':False,'code':'TELEGRAM-CONFIG'}
        atomic_json(path,{'attempt':now})
        try:send_message(config,'HomenSAI Auto VPN: delivery test. This is not router measurement data.')
        except DeliveryError as error:return {'delivered':False,'code':error.code,'uncertain':error.uncertain}
        atomic_json(path,{'attempt':now,'confirmed':time.time()})
        return {'delivered':True,'code':'TELEGRAM-TEST-DELIVERED'}
