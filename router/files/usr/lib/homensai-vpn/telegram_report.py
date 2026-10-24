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
