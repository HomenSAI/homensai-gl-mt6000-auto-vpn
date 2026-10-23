"""Seven-day incident detail, compact monthly and lifetime observed counters.

No raw probes, addresses, names or secrets. Unknown/unobserved time is never up.
The monitor checkpoints this model; incident edges request an immediate checkpoint.
"""
import copy
from datetime import datetime
import json
import math
import re
import time

WEEK=7*86400
PROFILE=re.compile(r'^(?:openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$')
BAD={'VPN-001','VPN-003','DNS-001'}
METRICS=('checks','failed_checks','outages','recoveries','observed_up_seconds',
         'observed_down_seconds','unknown_intervals','auto_observed_seconds')


def finite(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0


def active_controller(native,state,intent,now):
    if not all(isinstance(value,dict) for value in (native,state,intent)):return False
    stamp=native.get('time')
    return (state.get('phase')=='RUNNING' and intent.get('mode')=='on'
            and isinstance(state.get('id'),str) and state['id']==intent.get('id')
            and state.get('revision')==intent.get('revision')
            and native.get('mode')=='continuous-pair'
            and native.get('state') in ('OBSERVING','COMMITTED','DEGRADED-ON-RESERVE','ARMED','APPLYING','WAIT-CLIENT','RESTORING','BLOCKED')
            and finite(stamp) and finite(now) and 0<=now-stamp<90)


class Reliability:
    MAX_EVENTS=10000
    DETAIL_BYTES=1024*1024

    def __init__(self,data=None):
        self.data=copy.deepcopy(data) if data else {'schema':1,'since':None,'sequence':0,
            'totals':{},'months':{},'events':[],'profiles':{},'details_dropped':0}
        d=self.data
        if (not isinstance(d,dict) or d.get('schema')!=1 or type(d.get('sequence')) is not int
                or not 0<=d['sequence']<2**53 or not isinstance(d.get('totals'),dict)
                or not isinstance(d.get('months'),dict) or len(d['months'])>1200
                or not isinstance(d.get('events'),list) or len(d['events'])>self.MAX_EVENTS
                or not isinstance(d.get('profiles'),dict) or len(d['profiles'])>400):
            raise ValueError('STATISTICS-SCHEMA')
        if set(d)-{'schema','since','sequence','totals','months','events','profiles','details_dropped','controller','route_history'}:
            raise ValueError('STATISTICS-FIELDS')
        if d.get('since') is not None and not finite(d['since']):raise ValueError('STATISTICS-SINCE')
        if type(d.get('details_dropped')) is not int or d['details_dropped']<0:raise ValueError('STATISTICS-RETENTION')
        for month in d['months']:
            if not re.fullmatch(r'[0-9]{4}-(?:0[1-9]|1[0-2])',month):raise ValueError('STATISTICS-MONTH')
        last=0
        for row in d['events']:
            if (not isinstance(row,dict) or set(row)-{'sequence','time','profile','kind','code','observed_duration_seconds'}
                    or type(row.get('sequence')) is not int or not last<row['sequence']<=d['sequence']
                    or not finite(row.get('time')) or not PROFILE.fullmatch(str(row.get('profile','')))
                    or row.get('kind') not in ('FAILURE','RECOVERY','DISABLED') or 'code' in row and row['code'] not in BAD
                    or 'observed_duration_seconds' in row and not finite(row['observed_duration_seconds'])):
                raise ValueError('STATISTICS-EVENT')
            last=row['sequence']
        for key,row in d['profiles'].items():
            if (not PROFILE.fullmatch(key) or not isinstance(row,dict) or set(row)-{'time','state','opened','opened_observed'}
                    or not finite(row.get('time')) or row.get('state') not in ('up','down','off','unknown')
                    or row.get('opened') is not None and not finite(row['opened'])):
                raise ValueError('STATISTICS-PROFILE')
        old=d.get('controller')
        if old is not None and (not isinstance(old,dict) or set(old)!={'time','active'} or not finite(old['time']) or type(old['active']) is not bool):
            raise ValueError('STATISTICS-CONTROLLER')
        for totals in [d['totals']]+list(d['months'].values()):
            if not isinstance(totals,dict) or any(k not in METRICS or not finite(v) for k,v in totals.items()):
                raise ValueError('STATISTICS-COUNTERS')
        self.critical=False
        from route_history import RouteHistory
        self.routes=RouteHistory(d.get('route_history'))

    def add(self,key,value,now):
        month=datetime.fromtimestamp(now).strftime('%Y-%m')
        for totals in (self.data['totals'],self.data['months'].setdefault(month,{})):
            totals[key]=totals.get(key,0)+value

    def seconds(self,key,start,end):
        while start<end:
            local=datetime.fromtimestamp(start)
            year,month=(local.year+1,1) if local.month==12 else (local.year,local.month+1)
            boundary=time.mktime((year,month,1,0,0,0,0,0,-1))
            stop=min(end,boundary);self.add(key,stop-start,start);start=stop

    def event(self,profile,kind,now,code=None,duration=None):
        d=self.data;d['sequence']+=1
        item={'sequence':d['sequence'],'time':now,'profile':profile,'kind':kind}
        if code in BAD:item['code']=code
        if finite(duration):item['observed_duration_seconds']=duration
        d['events'].append(item);self.critical=True

    def prune(self,now):
        d=self.data
        d['events']=[row for row in d['events'] if now-WEEK<=row['time']<=now]
        overflow=max(0,len(d['events'])-self.MAX_EVENTS)
        while len(d['events'])-overflow>1 and len(json.dumps(d['events'][overflow:],separators=(',',':')).encode())>self.DETAIL_BYTES:
            overflow+=max(1,(len(d['events'])-overflow)//10)
        if overflow:
            d['events']=d['events'][overflow:];d['details_dropped']+=overflow
        for month in sorted(d['months'])[:-1200]:del d['months'][month]
        d['profiles']={key:value for key,value in d['profiles'].items() if now-value['time']<=WEEK}

    def observe(self,row,max_gap=90):
        key=row.get('id');now=row.get('time')
        if not isinstance(key,str) or not PROFILE.fullmatch(key) or not finite(now) or now>253370764799:return False
        d=self.data;previous=d['profiles'].get(key)
        if previous and now<=previous['time']:return False
        if d['since'] is None:d['since']=now
        code=row.get('code')
        state='off' if row.get('administrative_state')=='disabled' or code=='PROFILE-INACTIVE' else 'down' if code in BAD else 'up' if code is None and row.get('dns_ok') is True and row.get('https_success',0)>=2 else 'unknown'
        if state!='off':self.add('checks',1,now)
        if state=='down':self.add('failed_checks',1,now)
        contiguous=previous and 0<now-previous['time']<=max_gap
        if contiguous and previous['state'] in ('up','down'):
            self.seconds('observed_'+previous['state']+'_seconds',previous['time'],now)
        elif previous and (not contiguous or previous['state']=='unknown'):self.add('unknown_intervals',1,now)
        # An open outage survives restart/unknown samples; recovery needs fresh success.
        opened=previous.get('opened') if previous else None
        observed=bool(previous and previous.get('opened_observed') and contiguous and state!='unknown')
        if state=='off' and opened is not None:
            self.event(key,'DISABLED',now);opened=None;observed=False
        elif state=='down' and opened is None:
            self.add('outages',1,now);self.event(key,'FAILURE',now,code);opened=now;observed=True
        elif state=='up' and opened is not None:
            self.add('recoveries',1,now)
            self.event(key,'RECOVERY',now,duration=now-opened if observed else None);opened=None
        d['profiles'][key]={'time':now,'state':state,'opened':opened,'opened_observed':observed}
        if len(d['profiles'])>400:
            oldest=min(d['profiles'],key=lambda k:d['profiles'][k]['time']);del d['profiles'][oldest]
        self.prune(now)
        return self.critical

    def controller(self,active,now,max_gap=90):
        if not finite(now):return
        old=self.data.get('controller')
        if old and now<=old['time']:return
        if old and old['active'] and active and now-old['time']<=max_gap:
            self.seconds('auto_observed_seconds',old['time'],now)
        self.data['controller']={'time':now,'active':active is True}

    def export(self):
        data=copy.deepcopy(self.data);data['route_history']=self.routes.export();return data

    def public(self):
        d=self.data
        return {'since':d['since'],'totals':copy.deepcopy(d['totals']),
                'weekly':None if d['details_dropped'] else {'outages':sum(row['kind']=='FAILURE' for row in d['events']),
                          'recoveries':sum(row['kind']=='RECOVERY' for row in d['events'])},
                'months':copy.deepcopy(d['months']),'events':copy.deepcopy(d['events'][-100:]),
                'sequence':d['sequence'],'detail_days':7,'details_dropped':d['details_dropped'],
                'route_history':self.routes.export(),
                'scope':'observed VPN checks and outage edges; not LAN availability',
                'checkpointed':True}
