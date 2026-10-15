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
    lines = ['HomenSAI Auto VPN · мониторинг', datetime.now().strftime('%d.%m.%Y %H:%M Europe/Berlin'),
             'Интервал отчёта: %s мин' % minutes, 'Текущие подключённые серверы:']
    active = [p for p in status.get('profiles', []) if p.get('interface')]
    for p in active:
        lines.append('%s · %s · %s · HTTPS %s мс' %
                     (p['name'], p['protocol'], p.get('code') or 'OK', p.get('rtt_ms', '—')))
    if not active:
        lines.append('Подключённые профили не обнаружены.')
    cutoff = time.time()-minutes*60
    events = [e for e in status.get('events', []) if e.get('time', 0) >= cutoff]
    lines.append('Изменения состояния за интервал: %s' % len(events))
    for event in events[-20:]:
        lines.append('%s · %s · %s' % (datetime.fromtimestamp(event['time']).strftime('%H:%M:%S'),
                                      event.get('profile', 'служба'), event.get('code', 'OK')))
    accounting = status.get('accounting', {})
    month = datetime.now().strftime('%Y-%m')
    traffic = accounting.get('months', {}).get(month)
    if traffic:
        lines.append('VPN-трафик %s: %.3f GB (с начала наблюдения)' %
                     (month, (traffic.get('rx', 0)+traffic.get('tx', 0))/1e9))
    else:
        lines.append('Трафик: пока нет накопленных измерений.')
    lines.extend(['Пропуски наблюдения: %s' % accounting.get('gaps', 0),
                  'Проверки с роутера, IPv4. Причина сбоя определяется только при наличии данных.',
                  'Автоматическое переключение выключено.'])
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
