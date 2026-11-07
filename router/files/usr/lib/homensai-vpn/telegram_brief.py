"""Explicit Russian brief. Measurements are the page's channelReliability samples.

The five-minute percentage is a current snapshot, never a period uptime claim.
"""
from collections import Counter
from datetime import datetime
import math
import re


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def channel_reliability(status, identifier, now):
    # Keep in lockstep with channel_guidance.inc.js: channelReliability.
    rows = [s for s in status.get('samples', []) if s.get('id') == identifier
            and finite(s.get('time')) and -5 <= now-s['time'] <= 300
            and s.get('code') not in ('CHECK-001', 'CHECK-LIMIT', 'PROFILE-INACTIVE')]
    if len(rows) < 6:
        return None
    bad = sum(not (s.get('code') is None and s.get('dns_ok') is True
                   and s.get('https_success', 0) >= 2) for s in rows)
    return {'n': len(rows), 'bad': bad, 'loss': 100*bad/len(rows)}


def format_brief(status, start, end, now, key=None):
    native = status.get('native_failover', {})
    history = status.get('native_history', {})
    reliability = status.get('accounting', {}).get('reliability', {})
    alarm = native.get('alarm')
    valid = lambda c: isinstance(c, str) and re.fullmatch(r'[A-Z0-9_-]{1,96}', c)
    alarm = alarm if valid(alarm) else None
    lines = ['HomenSAI Auto VPN · кратко',
             'Период: %s — %s · Европа/Берлин' % tuple(datetime.fromtimestamp(t).strftime('%d.%m %H:%M') for t in (start, end))]
    if key:
        lines.append('Отчёт: '+key)
    # Put the mandatory alarm before bounded detail, so truncation cannot hide it.
    lines.append('Авария: '+(alarm+' · автопереключение остановлено' if alarm else 'нет'))
    errors = Counter()
    for event in reliability.get('events', []):
        if event.get('kind') == 'FAILURE' and finite(event.get('time')) and start <= event['time'] < end:
            code = event.get('code')
            if valid(code) and code != alarm:
                errors[code] += 1
    # Controller codes include successes; only explicit blocked episodes are errors.
    for event in history.get('events', []):
        if event.get('state') in ('BLOCKED', 'FAILED') and finite(event.get('time')) and start <= event['time'] < end:
            for code in set(event.get('codes', [])):
                if valid(code) and code != alarm:
                    errors[code] += 1
    if history.get('error'):
        errors['HISTORY-001'] += 1
    error_text = '; '.join(c+(' ×%d' % n if n > 1 else '') for c, n in sorted(errors.items())) or 'нет'
    # Bound this detail separately: switching and reliability lines must survive.
    from report_calendar import limited_text
    lines.append('Ошибки: '+limited_text(error_text, 1800))
    # Count real, completed route changes once, including restored returns.
    switches = set()
    for e in history.get('events', []):
        if not finite(e.get('time')) or not start <= e['time'] < end or e.get('trial'):
            continue
        if (e.get('transition_completed') is True and e.get('route_changed') is True
                and e.get('transition_outcome') in ('committed', 'restored')
                and not e.get('activation_reapply')):
            switches.add((e.get('attempt_id', e.get('sequence')), e.get('transition_outcome'), e.get('destination_role')))
    lines.append('Переключения: '+(str(len(switches))+' (сохранённые события)' if not history.get('error') else 'нет данных'))
    percentages = []
    for role, label in (('source', 'основной'), ('target', 'резервный')):
        identifier = next((p.get('id') for p in status.get('profiles', []) if p.get('role') == role), None) or native.get(role)
        r = channel_reliability(status, identifier, now) if identifier else None
        # Match JS Math.round(loss), then complement the displayed loss.
        percentages.append(label+': '+('%d%%' % (100-math.floor(r['loss']+0.5)) if r else 'нет данных'))
    lines.append('Надёжность сейчас, 5 мин: '+'; '.join(percentages))
    return limited_text('\n'.join(lines))
