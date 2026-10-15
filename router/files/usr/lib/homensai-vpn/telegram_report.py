"""Telegram delivery; credentials never appear in inventory, status or logs."""
import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime


def option(name):
    try:
        result = subprocess.run(['/sbin/uci', '-q', 'get', 'homensai_vpn.main.'+name],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ''
    return result.stdout.decode().strip() if result.returncode == 0 else ''


def format_report(status, minutes):
    lines = ['HomenSAI Auto VPN · monitoring', datetime.now().strftime('%d.%m.%Y %H:%M Europe/Berlin'),
             'Report interval: %s min' % minutes, 'Currently connected servers:']
    active = [p for p in status.get('profiles', []) if p.get('interface')]
    for p in active:
        lines.append('%s · %s · %s · HTTPS %s ms' %
                     (p['name'], p['protocol'], p.get('code') or 'OK', p.get('rtt_ms', '—')))
    if not active:
        lines.append('No connected profiles found.')
    cutoff = time.time()-minutes*60
    events = [e for e in status.get('events', []) if e.get('time', 0) >= cutoff]
    lines.append('State changes during the interval: %s' % len(events))
    for event in events[-20:]:
        lines.append('%s · %s · %s' % (datetime.fromtimestamp(event['time']).strftime('%H:%M:%S'),
                                      event.get('profile', 'service'), event.get('code', 'OK')))
    accounting = status.get('accounting', {})
    month = datetime.now().strftime('%Y-%m')
    traffic = accounting.get('months', {}).get(month)
    if traffic:
        lines.append('VPN traffic %s: %.3f GB (since monitoring started)' %
                     (month, (traffic.get('rx', 0)+traffic.get('tx', 0))/1e9))
    else:
        lines.append('Traffic: no accumulated measurements yet.')
    native=status.get('native_failover',{})
    state=native.get('state','UNKNOWN')
    if not isinstance(state,str) or not re.fullmatch(r'[A-Z0-9_-]{1,96}',state):state='UNKNOWN'
    lines.append('Native controller: %s (not proof of LAN availability).' % state)
    history=status.get('native_history',{})
    if history.get('error'):lines.append('Controller history unavailable: HISTORY-001.')
    native_events=[e for e in history.get('events',[]) if isinstance(e.get('time'),(int,float)) and e['time']>=cutoff]
    lines.append('Controller events during the interval: %s' % len(native_events))
    for event in native_events[-10:]:
        event_state=event.get('state','UNKNOWN')
        if not isinstance(event_state,str) or not re.fullmatch(r'[A-Z0-9_-]{1,96}',event_state):event_state='UNKNOWN'
        codes=[c for c in event.get('codes',[]) if isinstance(c,str) and re.fullmatch(r'[A-Z0-9_-]{1,96}',c)]
        lines.append('%s · %s%s · %s' % (datetime.fromtimestamp(event['time']).strftime('%H:%M:%S'),event_state,' · trial' if event.get('trial') else '',', '.join(codes)))
    totals=history.get('months',{}).get(month)
    if totals:
        lines.append('Controller %s, accumulated: attempts %s; trials passed %s; automatic commits %s; rollbacks %s. This is a partial month.' % (month,totals.get('attempts',0),totals.get('trials_passed',0),totals.get('committed',0),totals.get('rollbacks',0)))
    lines.extend(['Observation gaps: %s' % accounting.get('gaps', 0),
                  'Router-originated IPv4 checks. A failure cause is stated only when supported by evidence.'])
    return '\n'.join(lines)[:4000]


def deliver(status, saved, now):
    if option('telegram_enabled') != '1':
        return {'enabled': False}, saved, False
    try:
        minutes = max(5, min(10080, int(option('telegram_interval') or '60')))
        chat = option('telegram_chat')
        token = option('telegram_token')
        if not re.fullmatch(r'-?[0-9]{1,20}', chat) or not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token):
            return {'enabled': True, 'code': 'TELEGRAM-CONFIG'}, saved, False
        last = saved.get('sent', 0)
        if now-last < minutes*60:
            return {'enabled': True, 'last_sent': last, 'interval_minutes': minutes}, saved, False
        if now-saved.get('attempt', 0) < 300:
            return {'enabled': True, 'code': 'TELEGRAM-RETRY'}, saved, False
        saved = dict(saved, attempt=now)
        payload = json.dumps({'chat_id': chat, 'text': format_report(status, minutes)}).encode()
        request = urllib.request.Request('https://api.telegram.org/bot'+token+'/sendMessage',
                                         data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read(65536))
        if not result.get('ok'):
            raise ValueError('delivery rejected')
        saved['sent'] = now
        return {'enabled': True, 'last_sent': now, 'interval_minutes': minutes}, saved, True
    except Exception:
        return {'enabled': True, 'code': 'TELEGRAM-SEND-FAILED'}, saved, False
