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


def failure_pair_context(before,after):
    """Capture roles from two matching configured snapshots, never route health."""
    from vendor_observation import current_bindings,tunnel_identity
    def pair(data):
        if not isinstance(data,dict):return None
        settings=data.get('settings',{});rows=data.get('profiles',[])
        if not isinstance(settings,dict) or not isinstance(rows,list):return None
        bindings=current_bindings(rows);result={};anchors=[]
        for role in ('source','target'):
            anchor=settings.get('plan_'+role+'_tunnel')
            if not anchor:
                matches=[r for r in rows if isinstance(r,dict) and r.get('id')==settings.get('plan_'+role)]
                anchor=tunnel_identity(matches[0]) if len(matches)==1 else None
            row=bindings.get(anchor)
            if not row or not PROFILE.fullmatch(str(row.get('id',''))):return None
            result[role]=row['id'];anchors.append(anchor)
        return dict(result,anchors=anchors) if len(set(anchors))==2 and result['source']!=result['target'] else None
    left,right=pair(before),pair(after)
    return {role:left[role] for role in ('source','target')} if left and left==right else {}


class Reliability:
    MAX_EVENTS=10000
    DETAIL_BYTES=1024*1024

    def __init__(self,data=None,detail_days=7):
        if type(detail_days) is not int or not 1<=detail_days<=7:raise ValueError("STATISTICS-RETENTION")
        self.detail_days=detail_days
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
            if (not isinstance(row,dict) or set(row)-{'sequence','time','profile','kind','code','observed_duration_seconds','role','selected'}
                    or type(row.get('sequence')) is not int or not last<row['sequence']<=d['sequence']
                    or not finite(row.get('time')) or not PROFILE.fullmatch(str(row.get('profile','')))
                    or row.get('kind') not in ('FAILURE','RECOVERY','DISABLED') or 'code' in row and row['code'] not in BAD
                    or 'observed_duration_seconds' in row and not finite(row['observed_duration_seconds'])
                    or 'role' in row and row['role'] not in ('source','target','unknown')
                    or 'selected' in row and row['selected'] not in ('source','target','off','unknown')):
                raise ValueError('STATISTICS-EVENT')
            last=row['sequence']
        for key,row in d['profiles'].items():
            if (isinstance(row,dict) and row.get('state') not in ('up','down','off','unknown')
                    and row.get('state') in (None,'OBSERVING','COMMITTED','ARMED','APPLYING','WAIT-CLIENT','RESTORING','BLOCKED','STOPPED','STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE','DISABLED','EXPIRED','SERVICE-STOPPED')
                    and row.get('opened')==row.get('time') and row.get('opened_observed') is True
                    and any(e.get('profile')==key and e.get('time')==row.get('time') and e.get('kind')=='FAILURE' and e.get('code') in BAD and 'role' in e for e in d['events'])):
                row['state']='down'
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

    def event_context(self,key,now,native,pair):
        # Both outage edges retain their own event-time role, never today's pair.
        event=self.data['events'][-1];event.update(role='unknown',selected='unknown')
        if isinstance(pair,dict) and pair.get('source')!=pair.get('target'):
            event['role']='source' if key==pair.get('source') else 'target' if key==pair.get('target') else 'unknown'
        if (isinstance(native,dict) and finite(native.get('time')) and -5<=now-native['time']<=30
                and (pair is None or all(native.get(role)==pair.get(role) for role in ('source','target')))):
            if pair is None and native.get('source')!=native.get('target'):
                event['role']='source' if key==native.get('source') else 'target' if key==native.get('target') else 'unknown'
            native_state=native.get('state')
            event['selected']='target' if native_state in ('COMMITTED','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE') else 'source' if native_state=='OBSERVING' and (native.get('certified') is True or native.get('readiness_verified') is True) else 'off' if native_state in ('STOPPED','DISABLED','EXPIRED','SERVICE-STOPPED') else 'unknown'

    def prune(self,now):
        d=self.data
        d['events']=[row for row in d['events'] if now-self.detail_days*86400<=row['time']<=now]
        overflow=max(0,len(d['events'])-self.MAX_EVENTS)
        while len(d['events'])-overflow>1 and len(json.dumps(d['events'][overflow:],separators=(',',':')).encode())>self.DETAIL_BYTES:
            overflow+=max(1,(len(d['events'])-overflow)//10)
        if overflow:
            d['events']=d['events'][overflow:];d['details_dropped']+=overflow
        for month in sorted(d['months'])[:-1200]:del d['months'][month]
        d['profiles']={key:value for key,value in d['profiles'].items() if now-value['time']<=self.detail_days*86400}

    def observe(self,row,max_gap=90,native=None,pair=None):
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
            self.event_context(key,now,native,pair)
        elif state=='up' and opened is not None:
            self.add('recoveries',1,now)
            self.event(key,'RECOVERY',now,duration=now-opened if observed else None);opened=None
            self.event_context(key,now,native,pair)
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
                'sequence':d['sequence'],'detail_days':self.detail_days,'details_dropped':d['details_dropped'],
                'route_history':self.routes.export(),
                'failure_history':{'events':[[e['time'],e.get('role','unknown'),e.get('selected','unknown')] for e in d['events'] if e['kind']=='FAILURE' and e['time']>=max((p['time'] for p in d['profiles'].values()),default=0)-86400],
                                   'since':d['since'],'details_dropped':d['details_dropped']},
                'scope':'observed VPN checks and outage edges; not LAN availability',
                'checkpointed':True}
