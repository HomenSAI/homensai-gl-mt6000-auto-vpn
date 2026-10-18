# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
"""Calendar report planning; process TZ is configured as Europe/Berlin by agent."""
from datetime import datetime, timedelta
import time


def midnight(day):
    return time.mktime((day.year,day.month,day.day,0,0,0,0,0,-1))


def at_hour(day,hour):
    return time.mktime((day.year,day.month,day.day,hour,0,0,0,0,-1))


def enabled(value,default=False):
    return default if value in (None,'') else value in ('1',True)


def prepare(options,saved,now):
    mode=options.get('telegram_schedule') or 'interval'
    if mode not in ('interval','daily'):raise ValueError('TELEGRAM-SCHEDULE')
    minutes=max(5,min(10080,int(options.get('telegram_interval') or '60')))
    hour=int(options.get('telegram_hour') or '7')
    if not 0<=hour<=23:raise ValueError('TELEGRAM-SCHEDULE')
    local=datetime.fromtimestamp(now);today=local.date()
    jobs=[];state=dict(saved)
    starts=dict(saved.get('calendar_started',{}));confirmed=saved.get('period_keys',{})
    unknown=saved.get('uncertain',{})
    if mode=='interval' and now-saved.get('sent',0)>=minutes*60:
        key='interval:'+str(int(now//(minutes*60)))
        if key not in unknown:jobs.append({'kind':'interval','key':key,'minutes':minutes,'start':now-minutes*60,'end':now})
    for kind,wanted in (('daily',mode=='daily'),('weekly',enabled(options.get('telegram_weekly'),True)),('monthly',enabled(options.get('telegram_monthly'),True))):
        if not wanted:continue
        if kind not in starts:starts[kind]=now
        if kind=='daily':
            end=today;due=at_hour(end,hour)
            if now<due:end-=timedelta(days=1);due=at_hour(end,hour)
            start=end-timedelta(days=1)
        elif kind=='weekly':
            end=today-timedelta(days=today.weekday());due=at_hour(end,hour)
            if now<due:end-=timedelta(days=7);due=at_hour(end,hour)
            start=end-timedelta(days=7)
        else:
            end=today.replace(day=1);due=at_hour(end,hour)
            if now<due:end=(end-timedelta(days=1)).replace(day=1);due=at_hour(end,hour)
            start=(end-timedelta(days=1)).replace(day=1)
        key=kind+':'+start.isoformat()
        # New schedules start at their next slot. Restarts retain starts/keys and catch up once.
        if due>=starts[kind] and confirmed.get(kind)!=key and key not in unknown:
            jobs.append({'kind':kind,'key':key,'start':midnight(start),'end':midnight(end)})
    state['calendar_started']=starts
    return jobs,state,{'schedule':mode,'hour':hour,'interval_minutes':minutes,
                      'weekly':enabled(options.get('telegram_weekly'),True),'monthly':enabled(options.get('telegram_monthly'),True)}


def limited_text(text,units=4000):
    """Telegram entity offsets use UTF-16; keep headroom without splitting a pair."""
    raw=text.encode('utf-16-le')
    return text if len(raw)<=units*2 else raw[:(units-1)*2].decode('utf-16-le','ignore')+'…'


def traffic_lines(accounting,start,end,monthly=False):
    first=datetime.fromtimestamp(start).strftime('%Y-%m-%d')
    last=datetime.fromtimestamp(end-1).strftime('%Y-%m-%d')
    if monthly:
        item=accounting.get('months',{}).get(first[:7])
        if not item:return ['No measured monthly traffic.']
        return ['%.3f GB; partial collection, interface overhead included.' % ((item.get('rx',0)+item.get('tx',0))/1e9)]
    rows=[value for day,value in accounting.get('days',{}).items() if first<=day<=last and value.get('observed')]
    if not rows:return ['No daily traffic samples for this period.']
    amount=sum(value.get('rx',0)+value.get('tx',0) for value in rows)
    expected=(datetime.fromtimestamp(end-1).date()-datetime.fromtimestamp(start).date()).days+1
    gaps=sum(value.get('gaps',0) for value in rows)
    return ['%.3f GB; observed days %d/%d; sampling discontinuities %d. Missing data is not reconstructed.' % (amount/1e9,len(rows),expected,gaps)]


def format_period(status,job,now,items=None):
    from telegram_items import ITEMS
    items=ITEMS if items is None else items
    start,end=job['start'],job['end'];first=datetime.fromtimestamp(start).strftime('%Y-%m-%d');last=datetime.fromtimestamp(end-1).strftime('%Y-%m-%d')
    accounting=status.get('accounting',{});history=status.get('native_history',{})
    lines=['HomenSAI Auto VPN · '+job['kind'].title()+' summary','Report id: '+job['key'],
           'Period: %s to %s · Europe/Berlin' % (first,last),
           'Generated: '+datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M'),
           'Scope: router-originated measurements; LAN uptime is not verified.']
    if 'traffic' in items:
        lines.append('WAN traffic through this router:');lines+=traffic_lines(accounting.get('wan') or {},start,end,job['kind']=='monthly')
        lines.append('VPN interface traffic:');lines+=traffic_lines(accounting,start,end,job['kind']=='monthly')
    if 'servers' in items:
        profiles=[]
        for identifier,profile in accounting.get('activity',{}).items():
            total={key:0 for key in ('up','down','unknown','connections','failures')}
            dates=[]
            for day,bucket in profile.get('days',{}).items():
                if first<=day<=last:
                    dates.append(day)
                    for key in total:total[key]+=bucket.get(key,0)
            if dates:profiles.append((identifier,profile,total))
        if profiles:
            lines.append('Monitored server-hours (sum across servers): healthy %.2f; failed %.2f; unknown %.2f.' %
                         tuple(sum(row[2][key] for row in profiles)/3600 for key in ('up','down','unknown')))
            lines.append('Server observations · up/down/unknown hours · connections · failure episodes:')
            for _,profile,total in sorted(profiles,key=lambda row:row[2]['down'],reverse=True)[:10]:
                lines.append('%s · %.2f/%.2f/%.2f h · %d · %d' % (profile.get('name','server'),total['up']/3600,total['down']/3600,total['unknown']/3600,total['connections'],total['failures']))
            if len(profiles)>10:lines.append('Showing 10 of %d observed servers; detailed history is available in the dashboard.' % len(profiles))
        else:lines.append('No server activity observations for this period.')
    if 'controller_events' in items:
        totals={key:0 for key in ('attempts','committed','trials_passed','rollbacks','blocked_episodes','automatic_attempts','automatic_committed','server_switches','channel_switches','protocol_switches')}
        for day,value in history.get('days',{}).items():
            if first<=day<=last:
                for key in totals:totals[key]+=value.get(key,0)
        since=history.get('daily_since')
        if since is None:lines.append('Daily controller counters: unavailable before the accounting upgrade.')
        else:
            lines.append('Recorded controller activity: attempts %d; commits %d; passed trials %d; restorations/rollbacks %d; blocked episodes %d.' % tuple(totals[key] for key in ('attempts','committed','trials_passed','rollbacks','blocked_episodes')))
            lines.append('Automatic transitions: successful %d/%d; server/channel/protocol kinds %d/%d/%d. Kind categories are not summed with the total.' % tuple(totals[key] for key in ('automatic_committed','automatic_attempts','server_switches','channel_switches','protocol_switches')))
            if since>start:lines.append('Controller daily/kind counters are partial: collected since '+datetime.fromtimestamp(since).strftime('%Y-%m-%d %H:%M')+'.')
    if 'controller_totals' in items and job['kind']=='monthly' and first[:7] in history.get('months',{}):
        value=history['months'][first[:7]]
        lines.append('Retained monthly controller totals: attempts %s; commits %s; trials %s; rollbacks %s.' % tuple(value.get(key,0) for key in ('attempts','committed','trials_passed','rollbacks')))
    events=[event for event in status.get('events',[]) if isinstance(event.get('time'),(int,float)) and start<=event['time']<end]
    if 'events' in items and events:lines.append('Retained measurement state changes in period: %d (bounded event history).' % len(events))
    if 'gaps' in items:
        lines.append('Sampling discontinuities, cumulative: %s. Unknown causes and unobserved intervals remain unknown.' % accounting.get('gaps',0))
        if accounting.get('retention'):lines.append('History retention limits were applied; some historical observations are unavailable.')
    return limited_text('\n'.join(lines))
