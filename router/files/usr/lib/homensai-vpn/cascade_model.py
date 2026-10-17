"""Pure failover transaction model. It never runs commands or changes routes.

All times are caller-provided monotonic seconds. HTTPS/DNS probe outcomes must
be explicitly bound to a profile. Native adaptation requires separate proof.
"""
import copy
import hashlib
import json
import math
import re

class ModelError(ValueError):
    pass


def finite(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0


def checksum(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class CascadeModel:
    MAX_PROFILES=16
    def __init__(self,profiles,primary,order,generation,failures=3,successes=2,stable=30,dwell=60,cooldown=60,timeout=30,lease=3600,max_attempts=16):
        if not isinstance(profiles,list) or not 2<=len(profiles)<=self.MAX_PROFILES:raise ModelError('MODEL-PROFILE-COUNT')
        self.profiles={}
        for row in profiles:
            identifier=row.get('id')
            if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9:_.-]{1,80}',identifier) or identifier in self.profiles:raise ModelError('MODEL-PROFILE-ID')
            if row.get('protocol') not in ('openvpn','wireguard'):raise ModelError('MODEL-PROTOCOL')
            if not isinstance(row.get('channel'),str) or not row['channel']:raise ModelError('MODEL-CHANNEL')
            if type(row.get('priority')) is not int or not 1<=row['priority']<=1000:raise ModelError('MODEL-PRIORITY')
            if any(type(row.get(k)) is not bool for k in ('enabled','connected')):raise ModelError('MODEL-PROFILE-FLAGS')
            self.profiles[identifier]=copy.deepcopy(row)
        if not isinstance(order,list) or len(order)!=len(set(order)) or set(order)!=set(self.profiles) or primary not in self.profiles or order[0]!=primary:raise ModelError('MODEL-ROOT-ORDER')
        if not isinstance(generation,str) or not generation:raise ModelError('MODEL-GENERATION')
        if type(failures) is not int or not 3<=failures<=10 or type(successes) is not int or not 2<=successes<=10:raise ModelError('MODEL-THRESHOLD')
        if not all(finite(v) and v>0 for v in (stable,dwell,cooldown,timeout)):raise ModelError('MODEL-TIMING')
        if not finite(lease) or lease>14400 or type(max_attempts) is not int or not 1<=max_attempts<=64:raise ModelError('MODEL-LEASE')
        self.config=dict(failures=failures,successes=successes,stable=stable,dwell=dwell,cooldown=cooldown,timeout=timeout,lease=lease,max_attempts=max_attempts)
        self.root=list(order);self.order=list(order);self.primary=primary;self.current=primary;self.generation=generation
        self.phase='OBSERVING';self.reason='INITIAL';self.guard='vpn-only';self.pending=None;self.samples={p:[] for p in self.profiles}
        self.quarantine={};self.quarantine_failures={};self.history=[];self.last_now=0;self.last_switch=None;self.last_attempt=None;self.sequence=0;self.stopping=False
    def probe(self,identifier,at,healthy,bound=True):
        if identifier not in self.profiles or not finite(at) or healthy not in (True,False,None) or type(bound) is not bool:raise ModelError('MODEL-PROBE')
        if healthy is not None and type(healthy) is not bool:raise ModelError('MODEL-PROBE')
        rows=self.samples[identifier]
        if rows and at<=rows[-1]['time']:raise ModelError('MODEL-PROBE-ORDER')
        rows.append({'time':at,'healthy':healthy if bound else None});del rows[:-64]
    def _streak(self,identifier,healthy,now,count=None,span=0):
        row=self.profiles[identifier]
        if not row['enabled'] or not row['connected']:return False
        points=self.samples[identifier];count=count or self.config['successes'];good=[];previous=None
        for point in reversed(points):
            stamp=point['time']
            if stamp>now or (previous is None and now-stamp>90) or (previous is not None and previous-stamp>90):break
            if point['healthy'] is not healthy:break
            good.append(stamp);previous=stamp
            if len(good)>=count and good[0]-good[-1]>=span:return True
        return False
    def _ready(self,identifier,now):
        failures=self.quarantine_failures.get(identifier,0)
        return now>=self.quarantine.get(identifier,0) and self._streak(identifier,True,now,self.config['successes']+min(failures,3),self.config['stable'] if failures else 0)
    def _root_ready(self,now):return now>=self.quarantine.get(self.primary,0) and self._streak(self.primary,True,now,self.config['successes']+min(self.quarantine_failures.get(self.primary,0),3),span=self.config['stable'])
    def _event(self,event,now):
        self.history.append(dict(event,time=now));del self.history[:-256]
    def _context(self,now,actual,generation,rpc=True):
        if not finite(now) or now<self.last_now:
            self.phase='BLOCKED';self.reason='MODEL-CLOCK-REGRESSION';self.guard='closed';return False
        self.last_now=now
        if self.phase in ('BLOCKED','RECOVERY-REQUIRED'):return False
        if type(rpc) is not bool or not rpc:
            self.reason='MODEL-RPC-UNAVAILABLE'
            if self.pending:self.phase='RECOVERY-REQUIRED';self.guard='closed'
            return False
        allowed=[self.order]
        if self.pending:
            allowed=[self.pending['before']] if self.phase=='PREPARED' else [self.pending['after']] if self.phase=='WAIT-CONFIRM' else [self.pending['before'],self.pending['after']]
        if generation!=self.generation or actual not in allowed:
            self.phase='BLOCKED';self.reason='MODEL-EXTERNAL-POLICY';self.guard='closed';return False
        return True
    def transition(self,source,target):
        a,b=self.profiles[source],self.profiles[target]
        return 'protocol' if a['protocol']!=b['protocol'] else 'channel' if a['channel']!=b['channel'] else 'server'
    def candidates(self,now):
        origin=self.profiles[self.current];rows=[]
        for identifier,row in self.profiles.items():
            if identifier==self.current or not self._ready(identifier,now) or now<self.quarantine.get(identifier,0):continue
            same=row['protocol']==origin['protocol'];tier=0 if same and row['channel']==origin['channel'] else 1 if same else 2
            rows.append({'id':identifier,'tier':tier,'priority':row['priority'],'transition':('server','channel','protocol')[tier]})
        return sorted(rows,key=lambda x:(x['tier'],x['priority'],x['id']))
    def _prepare(self,target,now,root=False):
        after=list(self.root) if root else [target]+[p for p in self.order if p!=target]
        self.sequence+=1
        self.pending={'id':self.sequence,'source':self.current,'target':target,'before':list(self.order),'after':after,'root_restore':root,'created':now,'deadline':now+self.config['timeout']}
        self.phase='PREPARED';self.reason='MODEL-RETURN-PRIMARY' if root else 'MODEL-FAILOVER';self.last_attempt=now
        return self.intent()
    def intent(self):
        if not self.pending:return None
        return dict(copy.deepcopy(self.pending),operation='restore-hop' if self.phase=='ROLLING-BACK' else 'apply',model_only=True)
    def plan(self,now,actual,generation,rpc=True,worker_busy=False):
        if not self._context(now,actual,generation,rpc):return None
        if self.phase in ('BLOCKED','RECOVERY-REQUIRED') or self.stopping:return None
        if self.pending:
            if now>=self.pending['deadline']:
                if self.phase=='PREPARED' and actual==self.pending['before']:
                    self.pending=None;self.phase='OBSERVING';self.reason='MODEL-PREPARE-EXPIRED'
                else:return self._rollback(now,'MODEL-CONFIRM-TIMEOUT')
            return None
        if now>=self.config['lease']:return self.stop(now,actual,generation,rpc)
        if worker_busy is not False:self.reason='MODEL-WORKER-BUSY';return None
        if self.current!=self.primary and self._root_ready(now) and (self.last_switch is None or now-self.last_switch>=self.config['dwell']):return self._prepare(self.primary,now,True)
        if self.sequence>=self.config['max_attempts']:self.phase='EXHAUSTED';self.reason='MODEL-ATTEMPT-LIMIT';return None
        if not self._streak(self.current,False,now,self.config['failures']):self.phase='OBSERVING';self.reason='MODEL-NO-CONFIRMED-FAILURE';return None
        if self.last_attempt is not None and now-self.last_attempt<self.config['cooldown']:self.reason='MODEL-COOLDOWN';return None
        rows=self.candidates(now)
        if not rows:self.phase='EXHAUSTED';self.reason='MODEL-NO-HEALTHY-RESERVE';self.guard='closed';return None
        return self._prepare(rows[0]['id'],now)
    def begin(self,transaction,now,actual,generation,rpc=True,worker_busy=False):
        if not self._context(now,actual,generation,rpc):return None
        if not self.pending or transaction!=self.pending['id'] or self.phase!='PREPARED':raise ModelError('MODEL-STALE-TRANSACTION')
        if worker_busy is not False or actual!=self.pending['before'] or now>=self.pending['deadline'] or not (self._root_ready(now) if self.pending['root_restore'] else self._ready(self.pending['target'],now)):
            self.pending=None;self.phase='OBSERVING';self.reason='MODEL-PREPARE-REVALIDATION';return None
        self.phase='APPLYING';return self.intent()
    def applied(self,transaction,now,actual,generation,success=True,rpc=True):
        if not self._context(now,actual,generation,rpc):return None
        if not self.pending or transaction!=self.pending['id'] or self.phase!='APPLYING':raise ModelError('MODEL-STALE-TRANSACTION')
        if actual==self.pending['after'] and success is True and now<self.pending['deadline']:
            self.phase='WAIT-CONFIRM';return None
        return self._rollback(now,'MODEL-APPLY-FAILED')
    def _rollback(self,now,reason):
        self.phase='ROLLING-BACK';self.reason=reason;self.guard='closed';return self.intent()
    def confirm(self,transaction,now,actual,generation,healthy):
        if not self._context(now,actual,generation):return None
        if not self.pending or transaction!=self.pending['id'] or self.phase!='WAIT-CONFIRM':raise ModelError('MODEL-STALE-TRANSACTION')
        if healthy is not True or actual!=self.pending['after'] or now>=self.pending['deadline']:return self._rollback(now,'MODEL-CLIENT-NOT-CONFIRMED')
        hop=self.pending;self.current=hop['target'];self.order=list(hop['after']);self.pending=None;self.last_switch=now;self.guard='vpn-only'
        self.quarantine_failures.pop(self.current,None);self.quarantine.pop(self.current,None)
        self._event({'type':'commit','source':hop['source'],'target':self.current,'root_restore':hop['root_restore'],'transition':self.transition(hop['source'],self.current)},now)
        self.phase='STOPPED' if self.stopping else 'OBSERVING';self.reason='MODEL-CLIENT-CONFIRMED'
        return None
    def rolled_back(self,transaction,now,actual,generation,rpc=True):
        if not self._context(now,actual,generation,rpc):return False
        if not self.pending or transaction!=self.pending['id'] or self.phase!='ROLLING-BACK':raise ModelError('MODEL-STALE-TRANSACTION')
        if actual!=self.pending['before']:self.phase='RECOVERY-REQUIRED';self.reason='MODEL-ROLLBACK-UNVERIFIED';return False
        hop=self.pending;self.order=list(hop['before']);self.current=hop['source'];self.pending=None
        count=min(8,self.quarantine_failures.get(hop['target'],0)+1);self.quarantine_failures[hop['target']]=count
        self.quarantine[hop['target']]=now+min(3600,self.config['cooldown']*(2**(count-1)));self.guard='vpn-only'
        self._event({'type':'rollback-hop','target':hop['target']},now)
        self.phase='STOPPED' if self.stopping else 'OBSERVING';self.reason='MODEL-HOP-RESTORED';return True
    def stop(self,now,actual,generation,rpc=True):
        self.stopping=True
        if not self._context(now,actual,generation,rpc):return None
        if self.pending:
            if self.phase=='PREPARED' and actual==self.pending['before']:
                self.pending=None
            else:return self._rollback(now,'MODEL-OPERATOR-STOP')
        if self.current==self.primary and actual==self.root:
            self.phase='STOPPED';self.reason='MODEL-ROOT-UNCHANGED';return None
        if self._root_ready(now):return self._prepare(self.primary,now,True)
        healthy=self._ready(self.current,now);self.phase='STOPPED-ON-RESERVE' if healthy else 'STOPPED-NO-HEALTHY-PATH'
        self.reason='MODEL-PRIMARY-UNVERIFIED';self.guard='vpn-only' if healthy else 'closed';return None
    def reconcile(self,now,actual,generation,client_profile,healthy,worker_busy=False):
        """Explicit operator/client reconciliation after restart; never resumes Auto."""
        if self.phase!='RECOVERY-REQUIRED':raise ModelError('MODEL-RECONCILIATION-NOT-REQUIRED')
        allowed=[self.order]
        if self.pending:allowed=[self.pending['before'],self.pending['after']]
        if not finite(now) or generation!=self.generation or actual not in allowed or worker_busy is not False or healthy is not True or client_profile!=actual[0] or not self._ready(client_profile,now):
            self.reason='MODEL-RECONCILIATION-REFUSED';return False
        self.order=list(actual);self.current=client_profile;self.pending=None;self.stopping=True;self.last_now=now;self.last_attempt=now;self.last_switch=now
        self.phase='STOPPED' if self.order==self.root else 'STOPPED-ON-RESERVE';self.reason='MODEL-CLIENT-RECONCILED';self.guard='vpn-only'
        self._event({'type':'operator-reconciled','target':client_profile},now);return True
    def snapshot(self):
        data={k:copy.deepcopy(getattr(self,k)) for k in ('profiles','config','root','order','primary','current','generation','phase','reason','guard','pending','quarantine','quarantine_failures','history','last_now','last_switch','last_attempt','sequence','stopping')}
        return {'schema':1,'data':data,'sha256':checksum(data)}
    @classmethod
    def recover(cls,envelope):
        if not isinstance(envelope,dict):raise ModelError('MODEL-JOURNAL-INTEGRITY')
        data=envelope.get('data')
        if envelope.get('schema')!=1 or not isinstance(data,dict) or checksum(data)!=envelope.get('sha256'):raise ModelError('MODEL-JOURNAL-INTEGRITY')
        expected={'profiles','config','root','order','primary','current','generation','phase','reason','guard','pending','quarantine','quarantine_failures','history','last_now','last_switch','last_attempt','sequence','stopping'}
        if 'quarantine_failures' not in data:data=dict(data,quarantine_failures={})
        if set(data)!=expected or not isinstance(data['profiles'],dict) or not isinstance(data['config'],dict):raise ModelError('MODEL-JOURNAL-SCHEMA')
        failures=data['quarantine_failures']
        if not isinstance(failures,dict) or any(k not in data['profiles'] or type(v) is not int or not 1<=v<=8 for k,v in failures.items()):raise ModelError('MODEL-JOURNAL-QUARANTINE')
        result=cls(list(data['profiles'].values()),data['primary'],data['root'],data['generation'],**data['config'])
        if set(data['order'])!=set(data['root']) or len(data['order'])!=len(data['root']) or data['current'] not in result.profiles:raise ModelError('MODEL-JOURNAL-ORDER')
        for key in data:setattr(result,key,copy.deepcopy(data[key]))
        result.samples={p:[] for p in result.profiles}
        result.phase='RECOVERY-REQUIRED';result.reason='MODEL-RESTART-REQUIRES-RECONCILIATION';result.guard='closed'
        return result
