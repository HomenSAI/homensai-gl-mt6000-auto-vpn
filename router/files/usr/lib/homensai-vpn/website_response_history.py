"""Separate observed website-response history. Old HTTPS/DoH history is never imported."""
import bisect,copy,hashlib,json,math,re
from pathlib import Path
from website_response import METRIC,TARGET_SET,VALID_FOR,MAX_MS,TARGETS,DEFINITION,mean_ms,mean_from_tenths

DAY=86400
WEEK=7*DAY
MAX_ROWS=7*1440+1
MAX_BYTES=2*1024*1024
IDENTIFIER=re.compile(r'^(?:openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$')
KINDS={'source','target','unknown','off','switching'}


def number(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False


def checksum(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def technical_history_tail(history,now):
    """Keep the full old file; bound only its explicitly technical RPC view."""
    if not isinstance(history,dict):return history
    result=dict(history);result.pop('rows_json',None)
    rows=result.get('rows',[]);rows=rows if isinstance(rows,list)else[]
    if number(now):rows=[row for row in rows if isinstance(row,list)and row and number(row[0])and now-DAY<=row[0]<=now]
    result['rows']=rows[-1441:]
    result['technical_history_tail_only']=True
    result['retained_rows_count']=history.get('rows_count',len(rows))
    result['served_rows_count']=len(result['rows'])
    return result


def measurement(profile,now):
    """Validate one original completed sample, independently of VPN health."""
    if (not isinstance(profile,dict)or not number(now)or profile.get('vendor_state')!='SETTLED'
            or profile.get('administrative_state')=='disabled'):return None
    sample=profile.get('website_response')
    if not isinstance(sample,dict) or sample.get('metric')!=METRIC or sample.get('target_set')!=TARGET_SET:return None
    if sample.get('state') not in ('ok','partial','failed'):return None
    stamp=sample.get('time');ttl=sample.get('valid_for')
    if not number(stamp) or not number(ttl) or not 0<ttl<=VALID_FOR or not 0<=now-stamp<=ttl:return None
    interface=profile.get('interface');tunnel=profile.get('vendor_tunnel_id');generation=profile.get('vendor_generation')
    if (not isinstance(interface,str) or not re.fullmatch(r'(?:wgclient|ovpnclient)[1-9][0-9]{0,3}',interface)
            or not isinstance(tunnel,str) or tunnel!=profile.get('protocol','')+':'+interface
            or not isinstance(generation,str) or not re.fullmatch('[a-f0-9]{32}',generation)
            or sample.get('interface')!=interface or sample.get('vendor_tunnel_id')!=tunnel or sample.get('generation')!=generation):return None
    results=sample.get('results');expected={identifier:'https://'+host+path for identifier,host,path,_ in TARGETS}
    if (type(sample.get('attempted'))is not int or sample['attempted']!=3 or type(sample.get('successes'))is not int
            or not 0<=sample['successes']<=3 or not isinstance(results,list) or len(results)!=3):return None
    seen=set();values=[]
    for result in results:
        if not isinstance(result,dict):return None
        identifier=result.get('id')
        if identifier not in expected or identifier in seen or result.get('url')!=expected[identifier]:return None
        seen.add(identifier)
        if result.get('state')=='ok':
            delay=result.get('elapsed_ms')
            if not number(delay) or not 0<=delay<=MAX_MS or result.get('code')is not None:return None
            values.append(delay)
        elif result.get('state') not in ('failed','unavailable') or result.get('elapsed_ms')is not None:return None
    complete=len(values)==3
    if len(values)!=sample['successes'] or sample['state']!=('ok'if complete else'partial'if values else'failed'):return None
    avg=sample.get('avg_ms')
    if complete:
        if not number(avg)or not 0<=avg<=MAX_MS or avg!=mean_ms(values):return None
    elif avg is not None:return None
    return {'metric':METRIC,'target_set':TARGET_SET,'time':stamp,'avg_ms':avg,'successes':len(values),'attempted':3,
            'state':sample['state'],'interface':interface,'vendor_tunnel_id':tunnel,'generation':generation}


class WebsiteResponseHistory:
    def __init__(self,data=None,notice=None):
        self.data=copy.deepcopy(data)if data is not None else self.empty()
        self.notice=notice;self.retention_seconds=WEEK;self.validate()

    @staticmethod
    def empty():return {'version':1,'metric':METRIC,'target_set':TARGET_SET,'rows':[],'pairs':{},'current':None,'seen':{},'saved':None,'stats_since':None,'reset_floor':None}

    def validate(self):
        d=self.data
        if (not isinstance(d,dict) or set(d)!=set(self.empty()) or type(d['version'])is not int or d['version']!=1
                or d['metric']!=METRIC or d['target_set']!=TARGET_SET or not isinstance(d['rows'],list)or len(d['rows'])>MAX_ROWS
                or not isinstance(d['pairs'],dict)or len(d['pairs'])>32 or not isinstance(d['seen'],dict)or len(d['seen'])>64
                or any(d[key]is not None and(not number(d[key])or d[key]<0)for key in ('saved','stats_since','reset_floor'))):raise ValueError('WEBSITE-HISTORY-SCHEMA')
        for key,pair in d['pairs'].items():
            if (not isinstance(key,str)or not re.fullmatch('[a-f0-9]{16}',key)or not isinstance(pair,list)or len(pair)!=2 or pair[0]==pair[1]
                    or any(not isinstance(v,str)or not IDENTIFIER.fullmatch(v)for v in pair)
                    or key!=hashlib.sha256('\0'.join(pair).encode()).hexdigest()[:16]):raise ValueError('WEBSITE-HISTORY-PAIR')
        if d['current']is not None and d['current']not in d['pairs']:raise ValueError('WEBSITE-HISTORY-PAIR')
        for key,stamp in d['seen'].items():
            if not isinstance(key,str)or not IDENTIFIER.fullmatch(key)or not number(stamp):raise ValueError('WEBSITE-HISTORY-SEEN')
        previous=-1
        for row in d['rows']:
            if (not isinstance(row,list)or len(row)!=13 or not number(row[0])or row[0]<previous or row[0]<0
                    or row[5]not in KINDS or row[6]not in d['pairs']):raise ValueError('WEBSITE-HISTORY-ROW')
            for side in (0,1):
                value,count,success,attempted,partial=row[1+side],row[3+side],row[7+side],row[9+side],row[11+side]
                if (any(type(v)is not int or v<0 for v in (count,success,attempted,partial))or count+partial>120
                        or attempted!=3*(count+partial)or not count*3<=success<=count*3+partial*2
                        or(count==0)!=(value is None)or value is not None and(not number(value)or not 0<=value<=MAX_MS)):
                    raise ValueError('WEBSITE-HISTORY-VALUE')
            previous=row[0]

    @classmethod
    def load(cls,path):
        path=Path(path)
        try:
            if not path.exists():return cls()
            if path.is_symlink()or not path.is_file()or path.stat().st_size>MAX_BYTES:raise ValueError('size')
            value=json.loads(path.read_text(encoding='utf8'))
            if not isinstance(value,dict)or set(value)!={'data','sha256'}or value['sha256']!=checksum(value['data']):raise ValueError('checksum')
            return cls(value['data'])
        except (OSError,ValueError,TypeError,KeyError,OverflowError):return cls(notice='WEBSITE-HISTORY-UNAVAILABLE')

    def observe(self,status,settings,now):
        if not isinstance(status,dict)or not number(now)or now<0:return
        from retention_settings import days
        self.retention_seconds=days(settings)*DAY;d=self.data
        if d['rows']and now<d['rows'][-1][0]:return
        d['rows']=[r for r in d['rows']if r[0]>=now-self.retention_seconds]
        used={r[6]for r in d['rows']};d['pairs']={k:v for k,v in d['pairs'].items()if k in used}
        if d['current']not in d['pairs']:d['current']=None
        native=status.get('native_failover',{});native=native if isinstance(native,dict)else{}
        trusted=(native.get('certified')is True or native.get('mode')=='continuous-pair'and native.get('proof_scope')=='router-probed-ipv4'and native.get('readiness_verified')is True)
        fresh=trusted and number(native.get('time'))and 0<=now-native['time']<=30
        plan=status.get('failover_plan',{});plan=plan if isinstance(plan,dict)else{}
        ids=[native.get(role)if fresh else plan.get(role,settings.get('plan_'+role))for role in ('source','target')]
        if ids[0]==ids[1]or any(not isinstance(v,str)or not IDENTIFIER.fullmatch(v)for v in ids):return
        key=hashlib.sha256('\0'.join(ids).encode()).hexdigest()[:16]
        if key not in d['pairs']and len(d['pairs'])>=32:self.notice='WEBSITE-HISTORY-PAIR-LIMIT';return
        d['pairs'][key]=ids;d['current']=key;minute=int(now//60)*60
        def bucket(stamp):
            found=next((r for r in reversed(d['rows'])if r[0]==stamp and r[6]==key),None)
            if found is not None:return found
            created=[stamp,None,None,0,0,'unknown',key,0,0,0,0,0,0]
            index=bisect.bisect_right([r[0]for r in d['rows']],stamp);d['rows'].insert(index,created);return created
        row=bucket(minute)
        from route_history import observed_route
        try:row[5]=observed_route(status,now)
        except (ValueError,TypeError,AttributeError):row[5]='unknown'
        profiles=status.get('profiles',[]);profiles=profiles if isinstance(profiles,list)else[]
        for side,identifier in enumerate(ids):
            matched=[p for p in profiles if isinstance(p,dict)and p.get('id')==identifier]
            sample=measurement(matched[0],now)if len(matched)==1 else None
            if (not sample or sample['time']<=d['seen'].get(identifier,-1)
                    or d['reset_floor']is not None and sample['time']<=d['reset_floor']):continue
            row=bucket(int(sample['time']//60)*60)
            if row[3+side]+row[11+side]>=120:continue
            row[7+side]+=sample['successes'];row[9+side]+=3;d['seen'][identifier]=sample['time']
            if sample['avg_ms']is None:row[11+side]+=1;continue
            count=row[3+side];row[1+side]=((row[1+side]or 0)*count+sample['avg_ms'])/(count+1);row[3+side]+=1
        d['rows']=d['rows'][-MAX_ROWS:]
        used={r[6]for r in d['rows']};d['pairs']={k:v for k,v in d['pairs'].items()if k in used}
        known={v for pair in d['pairs'].values()for v in pair};d['seen']={k:v for k,v in d['seen'].items()if k in known}

    def statistics(self,rows,side,since):
        rows=[r for r in rows if r[0]>=since];count=sum(r[3+side]for r in rows)
        total=sum(self.sum_tenths(r,side)for r in rows)
        return {'metric':METRIC,'target_set':TARGET_SET,'avg_ms':mean_from_tenths(total,count)if count else None,
                'complete_samples':count,'incomplete_samples':sum(r[11+side]for r in rows),
                'cycles':count+sum(r[11+side]for r in rows),'complete':count,'sum_ms':total/10,'sum_tenths':total,
                'successful_checks':sum(r[7+side]for r in rows),'attempted_checks':sum(r[9+side]for r in rows),'since':since}

    def public(self,now):
        d=self.data;rows=[r for r in d['rows']if r[6]==d['current']];since=d['stats_since']or 0
        packed=[[r[0],self.sum_tenths(r,0)if r[3]else None,self.sum_tenths(r,1)if r[4]else None,r[3],r[4],r[5]]for r in rows]
        coverage=[[r[0],r[7],r[8],r[9],r[10],r[11],r[12]]for r in rows]
        result={'version':1,'metric':METRIC,'target_set':TARGET_SET,'row_encoding':'sum-tenths','definition':DEFINITION,'resolution_seconds':60,
            'retention_seconds':self.retention_seconds,'pair':list(d['pairs'].get(d['current'],[])),'rows':packed[-1441:],
            'coverage_rows':coverage[-1441:],'rows_count':len(rows),'saved':d['saved'],'notice':self.notice,'stats_since':d['stats_since'],'reset_floor':d['reset_floor'],
            'statistics':{role:self.statistics(rows,side,since)for side,role in enumerate(('source','target'))},
            'scope':'only observed complete 3/3 means; partial checks are gaps; historical HTTPS/DoH and ICMP are separate'}
        result['profile_statistics']={identifier:result['statistics'][role]for identifier,role in zip(result['pair'],('source','target'))}
        if len(rows)>1441:result['rows_json']=json.dumps(packed,separators=(',',':'),allow_nan=False);result['coverage_rows_json']=json.dumps(coverage,separators=(',',':'))
        return result

    @staticmethod
    def sum_tenths(row,side):return int(math.floor((row[1+side]or 0)*row[3+side]*10+.5))

    def clear(self,now=None):
        if self.notice=='WEBSITE-HISTORY-UNAVAILABLE':raise ValueError(self.notice)
        floor=max(self.data['seen'].values(),default=0)if now is None else now
        if not number(floor)or floor<0:raise ValueError('WEBSITE-HISTORY-TIME')
        self.data=self.empty();self.data['reset_floor']=floor;self.notice=None

    def clear_statistics(self,now):
        if self.notice=='WEBSITE-HISTORY-UNAVAILABLE':raise ValueError(self.notice)
        if not number(now)or now<0:raise ValueError('WEBSITE-HISTORY-TIME')
        # Do not count a bucket containing pre-reset measurements. Keep its chart point.
        self.data['stats_since']=math.ceil(now/60)*60

    def save(self,path,writer,now):
        if not number(now)or now<0:raise ValueError('WEBSITE-HISTORY-TIME')
        if self.notice=='WEBSITE-HISTORY-UNAVAILABLE':raise ValueError(self.notice)
        self.validate();data=copy.deepcopy(self.data);data['saved']=now
        if len(json.dumps(data,separators=(',',':')).encode())>MAX_BYTES:raise ValueError('WEBSITE-HISTORY-SIZE')
        writer(Path(path),{'data':data,'sha256':checksum(data)});self.data['saved']=now
        if self.notice=='WEBSITE-HISTORY-WRITE-FAILED':self.notice=None
