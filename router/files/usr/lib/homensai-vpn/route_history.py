"""Compact observed route intervals for the last 24 hours, never filled backwards."""
import copy,math
DAY=86400
KINDS={'source','target','switching','unknown','off','blocked','down'}


class RouteHistory:
    def __init__(self,data=None):
        self.data=copy.deepcopy(data) if data else {'segments':[],'last':None,'since':None,'dropped':0}
        d=self.data
        if not isinstance(d,dict) or set(d)!={'segments','last','since','dropped'} or not isinstance(d['segments'],list) or len(d['segments'])>4096 or type(d['dropped']) is not int or d['dropped']<0:
            raise ValueError('STATISTICS-ROUTE-SCHEMA')
        previous=None
        for row in d['segments']:
            if not isinstance(row,dict) or set(row)!={'start','end','kind'} or row['kind'] not in KINDS or not self.stamp(row['start']) or not self.stamp(row['end']) or row['end']<row['start'] or previous is not None and row['start']<previous:
                raise ValueError('STATISTICS-ROUTE-SEGMENT')
            previous=row['end']
        if d['last'] is not None and (not isinstance(d['last'],dict) or set(d['last'])!={'time','kind'} or not self.stamp(d['last']['time']) or d['last']['kind'] not in KINDS):raise ValueError('STATISTICS-ROUTE-LAST')
        if d['since'] is not None and not self.stamp(d['since']):raise ValueError('STATISTICS-ROUTE-SINCE')

    @staticmethod
    def stamp(value):return type(value) in (int,float) and math.isfinite(value) and 0<=value<=253370764799

    def observe(self,kind,now,max_gap=90):
        if kind not in KINDS or not self.stamp(now):raise ValueError('STATISTICS-ROUTE-OBSERVATION')
        d=self.data;old=d['last']
        if old and now<=old['time']:return False
        changed=old is None or old['kind']!=kind
        if d['since'] is None:d['since']=now
        if old:
            interval_kind=old['kind'] if now-old['time']<=max_gap else 'unknown'
            rows=d['segments'];begin=max(old['time'],now-DAY)
            if rows and rows[-1]['kind']==interval_kind and rows[-1]['end']==begin:rows[-1]['end']=now
            else:rows.append({'start':begin,'end':now,'kind':interval_kind})
        d['last']={'time':now,'kind':kind}
        d['segments']=[dict(row,start=max(row['start'],now-DAY)) for row in d['segments'] if row['end']>now-DAY]
        if len(d['segments'])>4096:
            d['dropped']+=len(d['segments'])-4096;d['segments']=d['segments'][-4096:]
        return changed

    def export(self):return copy.deepcopy(self.data)


def observed_route(status,now):
    native=status.get('native_failover') if isinstance(status,dict) else None
    if not isinstance(native,dict) or not RouteHistory.stamp(native.get('time')) or not 0<=now-native['time']<=30:return 'unknown'
    state=native.get('state')
    if state in ('STOPPED','DISABLED','EXPIRED','SERVICE-STOPPED'):return 'off'
    if state in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):return 'switching'
    def failing(identifier):
        profile=next((row for row in status.get('profiles',[]) if row.get('id')==identifier),None) if identifier else None
        return bool(profile) and RouteHistory.stamp(profile.get('time')) and 0<=now-profile['time']<=90 and not (profile.get('code') is None and profile.get('dns_ok') is True and profile.get('https_success',0)>=2)
    # Same states as the live chart: both channels failing is an outage of its own.
    if native.get('source') and native.get('target') and native['source']!=native['target'] and failing(native['source']) and failing(native['target']):return 'down'
    role='target' if state in ('COMMITTED','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE') else 'source' if state=='OBSERVING' and (native.get('certified') is True or native.get('mode')=='continuous-pair' and native.get('readiness_verified') is True) else None
    # The route is drawn from fresh router data only; a failing selected channel still carries the route.
    if role:
        profile=next((row for row in status.get('profiles',[]) if row.get('id')==native.get(role)),None)
        if profile and RouteHistory.stamp(profile.get('time')) and 0<=now-profile['time']<=90:return role
        return 'unknown'
    if state in ('BLOCKED','FAILED'):return 'blocked'
    return 'unknown'
