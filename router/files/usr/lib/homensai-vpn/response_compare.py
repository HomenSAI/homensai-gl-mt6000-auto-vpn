"""Owner-optional comparison of every response method for the Auto pair.

When "measure all methods" is on, each check also pings the other public DNS addresses and opens the three
websites. This keeps 7 days of hourly means per method and channel for the ranking table. Display only:
health, Auto and the chart of the chosen metric never read it.
"""
import copy,hashlib,json,math,re
from pathlib import Path

HOUR=3600
KEEP=7*24*HOUR
MAX_BYTES=512*1024
METHODS=('icmp-1.1.1.1','icmp-8.8.8.8','icmp-9.9.9.9','websites')
TARGETS=('1.1.1.1','8.8.8.8','9.9.9.9')
IDENTIFIER=re.compile(r'^(?:openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$')


def number(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False


def checksum(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def enabled(settings):
    return isinstance(settings,dict) and settings.get('response_compare') is True


def fresh(sample,now):
    stamp=sample.get('time');ttl=sample.get('valid_for')
    return number(stamp) and number(ttl) and 0<ttl<=900 and 0<=now-stamp<=ttl


def samples(row,now):
    """(method, measured_at, ms or None for a failed check) for every completed sample on this channel."""
    found=[]
    pings=[row.get('ping')]+list((row.get('ping_compare') or {}).values()) if isinstance(row.get('ping_compare') or {},dict) else [row.get('ping')]
    for sample in pings:
        if (not isinstance(sample,dict) or sample.get('metric')!='icmp-rtt-ms' or sample.get('state') not in ('ok','failed')
                or sample.get('interface')!=row.get('interface') or not fresh(sample,now)):continue
        method='icmp-'+str(sample.get('target'))
        if method not in METHODS:continue
        value=sample.get('rtt_ms') if sample['state']=='ok' else None
        if value is not None and (not number(value) or not 0<=value<=60000):continue
        found.append((method,sample['time'],value))
    site=row.get('website_response')
    if (isinstance(site,dict) and site.get('state') in ('ok','partial','failed') and site.get('interface')==row.get('interface')
            and fresh(site,now)):
        value=site.get('avg_ms') if site['state']=='ok' else None
        if value is None or number(value) and 0<=value<=60000:found.append(('websites',site['time'],value))
    return found


class ResponseCompare:
    def __init__(self,data=None,notice=None):
        self.data=copy.deepcopy(data) if data is not None else {'version':1,'rows':{},'seen':{}}
        self.notice=notice;self.validate()

    def validate(self):
        d=self.data
        if not isinstance(d,dict) or set(d)!={'version','rows','seen'} or d['version']!=1 or not isinstance(d['rows'],dict) or not isinstance(d['seen'],dict):
            raise ValueError('RESPONSE-COMPARE-SCHEMA')
        for method,profiles in d['rows'].items():
            if method not in METHODS or not isinstance(profiles,dict) or len(profiles)>32:raise ValueError('RESPONSE-COMPARE-SCHEMA')
            for identifier,rows in profiles.items():
                if not IDENTIFIER.fullmatch(identifier) or not isinstance(rows,list) or len(rows)>7*24+1:raise ValueError('RESPONSE-COMPARE-SCHEMA')
                for row in rows:
                    if (not isinstance(row,list) or len(row)!=4 or not number(row[0]) or any(type(v) is not int or v<0 for v in row[1:])
                            or row[2]==0 and row[1]!=0):raise ValueError('RESPONSE-COMPARE-VALUE')
        if len(d['seen'])>256 or any(not isinstance(k,str) or not number(v) for k,v in d['seen'].items()):raise ValueError('RESPONSE-COMPARE-SCHEMA')

    @classmethod
    def load(cls,path):
        path=Path(path)
        try:
            if not path.exists():return cls()
            if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_BYTES:raise ValueError('size')
            value=json.loads(path.read_text(encoding='utf8'))
            if not isinstance(value,dict) or set(value)!={'data','sha256'} or value['sha256']!=checksum(value['data']):raise ValueError('checksum')
            return cls(value['data'])
        except (OSError,ValueError,TypeError,KeyError,OverflowError):return cls(notice='RESPONSE-COMPARE-UNAVAILABLE')

    def observe(self,status,pair,now):
        if not number(now) or not isinstance(status,dict) or not isinstance(pair,dict):return
        d=self.data;ids={pair.get('source'),pair.get('target')}-{None}
        for row in status.get('profiles') or []:
            if not isinstance(row,dict) or row.get('id') not in ids or not IDENTIFIER.fullmatch(str(row.get('id'))):continue
            for method,stamp,value in samples(row,now):
                key=method+'|'+row['id']
                if stamp<=d['seen'].get(key,-1):continue
                d['seen'][key]=stamp
                rows=d['rows'].setdefault(method,{}).setdefault(row['id'],[])
                hour=int(stamp//HOUR)*HOUR
                if not rows or rows[-1][0]!=hour:rows.append([hour,0,0,0])
                bucket=rows[-1]
                if value is None:bucket[3]+=1
                else:bucket[1]+=int(math.floor(value*10+.5));bucket[2]+=1
        floor=now-KEEP
        for method in list(d['rows']):
            for identifier in list(d['rows'][method]):
                kept=[r for r in d['rows'][method][identifier] if r[0]>=floor][-(7*24+1):]
                if kept:d['rows'][method][identifier]=kept
                else:del d['rows'][method][identifier]
            if not d['rows'][method]:del d['rows'][method]
        known={m+'|'+i for m,p in d['rows'].items() for i in p}
        d['seen']={k:v for k,v in d['seen'].items() if k in known}

    def public(self,now):
        result={'version':1,'methods':[m for m in METHODS if m in self.data['rows']],'profiles':{},'notice':self.notice,'retention_seconds':KEEP,
                'scope':'hourly means of every response method for the Auto pair; display only, never used for switching'}
        for method,profiles in self.data['rows'].items():
            for identifier,rows in profiles.items():
                good=sum(r[2] for r in rows);failed=sum(r[3] for r in rows);total=sum(r[1] for r in rows)
                result['profiles'].setdefault(identifier,{})[method]={'avg_ms':round(total/good/10,1) if good else None,'ok':good,'failed':failed}
        return result

    def clear(self):
        if self.notice=='RESPONSE-COMPARE-UNAVAILABLE':raise ValueError(self.notice)
        self.data={'version':1,'rows':{},'seen':{}}

    def save(self,path,writer,now):
        if self.notice=='RESPONSE-COMPARE-UNAVAILABLE':raise ValueError(self.notice)
        self.validate();data=copy.deepcopy(self.data)
        if len(json.dumps(data,separators=(',',':')).encode())>MAX_BYTES:raise ValueError('RESPONSE-COMPARE-SIZE')
        writer(Path(path),{'data':data,'sha256':checksum(data)})
        if self.notice=='RESPONSE-COMPARE-WRITE-FAILED':self.notice=None
