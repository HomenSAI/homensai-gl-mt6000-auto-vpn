"""Bounded one-minute HTTPS-latency aggregates for the last observed day.

No endpoints/secrets, invented samples, zero-valued failures or backwards fill.
Persistence follows the existing application checkpoint cadence.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import re

DAY=86400
MAX_ROWS=1441
MAX_BYTES=262144
IDENTIFIER=re.compile(r'^(?:openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$')
KINDS={'source','target','unknown','off','switching'}

def number(value):return type(value) in (int,float) and math.isfinite(value)
def checksum(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

class LatencyHistory:
    def __init__(self,data=None,notice=None):
        self.data=copy.deepcopy(data) if data is not None else {'version':1,'rows':[],'pairs':{},'current':None,'seen':{},'saved':None}
        self.notice=notice
        d=self.data
        if (not isinstance(d,dict) or set(d)!={'version','rows','pairs','current','seen','saved'} or d['version']!=1
                or not isinstance(d['rows'],list) or len(d['rows'])>MAX_ROWS or not isinstance(d['pairs'],dict) or len(d['pairs'])>32
                or not isinstance(d['seen'],dict) or len(d['seen'])>64 or d['saved'] is not None and not number(d['saved'])):
            raise ValueError('LATENCY-HISTORY-SCHEMA')
        for key,pair in d['pairs'].items():
            if not re.fullmatch('[a-f0-9]{16}',key) or not isinstance(pair,list) or len(pair)!=2 or pair[0]==pair[1] or any(not isinstance(v,str) or not IDENTIFIER.fullmatch(v) for v in pair):raise ValueError('LATENCY-HISTORY-PAIR')
            if key!=hashlib.sha256('\0'.join(pair).encode()).hexdigest()[:16]:raise ValueError('LATENCY-HISTORY-PAIR')
        if d['current'] is not None and d['current'] not in d['pairs']:raise ValueError('LATENCY-HISTORY-CURRENT')
        for key,stamp in d['seen'].items():
            if not IDENTIFIER.fullmatch(key) or not number(stamp):raise ValueError('LATENCY-HISTORY-SEEN')
        previous=-1
        for row in d['rows']:
            if (not isinstance(row,list) or len(row)!=7 or not number(row[0]) or row[0]<0 or row[0]<previous
                    or row[6] not in d['pairs'] or row[5] not in KINDS):raise ValueError('LATENCY-HISTORY-ROW')
            for value,count in [(row[1],row[3]),(row[2],row[4])]:
                if type(count)is not int or not 0<=count<=120 or (count==0)!=(value is None) or value is not None and (not number(value) or not 0<=value<=600000):raise ValueError('LATENCY-HISTORY-VALUE')
            previous=row[0]

    @classmethod
    def load(cls,path):
        path=Path(path)
        try:
            if not path.exists():return cls()
            if path.is_symlink() or path.stat().st_size>MAX_BYTES:raise ValueError('LATENCY-HISTORY-SIZE')
            value=json.loads(path.read_text(encoding='utf8'))
            if not isinstance(value,dict) or set(value)!={'data','sha256'} or value['sha256']!=checksum(value['data']):raise ValueError('LATENCY-HISTORY-CHECKSUM')
            return cls(value['data'])
        except (OSError,ValueError,TypeError,KeyError):return cls(notice='LATENCY-HISTORY-UNAVAILABLE')

    def observe(self,status,settings,now):
        if not number(now) or now<0:return
        d=self.data
        if d['rows'] and now<d['rows'][-1][0]:return
        native=status.get('native_failover',{})
        if not isinstance(native,dict):native={}
        trusted=(native.get('certified') is True or native.get('mode')=='continuous-pair' and native.get('proof_scope')=='router-probed-ipv4' and native.get('readiness_verified') is True)
        native_current=trusted and number(native.get('time')) and -5<=now-native['time']<=30 and native.get('state') in ('OBSERVING','COMMITTED','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE')
        ids=[native.get('source') if native_current else settings.get('plan_source'),native.get('target') if native_current else settings.get('plan_target')]
        if ids[0]==ids[1] or any(not isinstance(v,str) or not IDENTIFIER.fullmatch(v) for v in ids):return
        key=hashlib.sha256('\0'.join(ids).encode()).hexdigest()[:16]
        minute=int(now//60)*60
        d['rows']=[row for row in d['rows'] if row[0]>=now-DAY]
        used={row[6] for row in d['rows']}
        d['pairs']={k:v for k,v in d['pairs'].items() if k in used}
        if key not in d['pairs'] and len(d['pairs'])>=32:
            self.notice='LATENCY-PAIR-LIMIT';return
        d['pairs'][key]=ids;d['current']=key
        if not d['rows'] or d['rows'][-1][0]!=minute or d['rows'][-1][6]!=key:d['rows'].append([minute,None,None,0,0,'unknown',key])
        row=d['rows'][-1]
        from route_history import observed_route
        try:row[5]=observed_route(status,now)
        except (ValueError,TypeError,AttributeError):row[5]='unknown'
        if row[5] in ('source','target') and not native_current:row[5]='unknown'
        for index,identifier in enumerate(ids):
            profiles=status.get('profiles',[])
            if not isinstance(profiles,list):profiles=[]
            p=next((p for p in profiles if isinstance(p,dict) and p.get('id')==identifier),None)
            if not p or p.get('code') is not None or p.get('dns_ok') is not True or type(p.get('https_success'))is not int or p['https_success']<2 or p.get('vendor_state')!='SETTLED':continue
            stamp=p.get('time');rtt=p.get('rtt_ms')
            if not number(stamp) or not -5<=now-stamp<=90 or stamp<=d['seen'].get(identifier,-1) or not number(rtt) or not 0<=rtt<=600000:continue
            count=row[index+3]
            if count>=120:continue
            row[index+1]=((row[index+1] or 0)*count+rtt)/(count+1);row[index+3]=count+1;d['seen'][identifier]=stamp
        d['rows']=d['rows'][-MAX_ROWS:]
        valid_ids={v for pair in d['pairs'].values() for v in pair}
        d['seen']={k:v for k,v in d['seen'].items() if k in valid_ids}

    def public(self):
        d=self.data
        return {'version':1,'metric':'https-rtt-ms','resolution_seconds':60,'retention_seconds':DAY,
                'pair':list(d['pairs'].get(d['current'],[])),
                'rows':[[r[0],None if r[1] is None else round(r[1],1),None if r[2] is None else round(r[2],1),r[3],r[4],r[5]] for r in d['rows'] if r[6]==d['current']],
                'saved':d['saved'],'notice':self.notice,'scope':'observed minute means; gaps are unobserved; not ICMP or LAN proof'}

    def save(self,path,writer,now):
        if not number(now) or now<0:raise ValueError('LATENCY-HISTORY-TIME')
        if self.notice=='LATENCY-HISTORY-UNAVAILABLE':raise ValueError(self.notice)
        data=copy.deepcopy(self.data);data['saved']=now
        if len(json.dumps(data,separators=(',',':')).encode())>MAX_BYTES:raise ValueError('LATENCY-HISTORY-SIZE')
        writer(Path(path),{'data':data,'sha256':checksum(data)});self.data['saved']=now
        if self.notice=='LATENCY-HISTORY-WRITE-FAILED':self.notice=None
