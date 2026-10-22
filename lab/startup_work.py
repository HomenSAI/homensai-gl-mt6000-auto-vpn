"""Bounded fixed-profile startup work reducer; never a data/LAN certificate.

Aggregate count growth alone confuses normal service fan-out with deadlock.
Require known fresh workers, absolute/cumulative budgets, bounded progress and
stable quiet link generation; retain the independent actor's outside deadline.
"""
import math
import re

LIMITS={'FW3':4,'RTP':3,'PROTO':3,'HOOK':3,'NETWORK':2,'DNSMASQ':2,'CHECK':2}
SERVICES=frozenset(('FIREWALL','NETWORK','DNSMASQ'))


def finite(value):
    try:return type(value)in(int,float) and math.isfinite(value)
    except OverflowError:return False


def classify(rows,target,min_start,allow_dns_restart=False):
    """Keep only coded process identities; no argv/env/profile text leaves here."""
    if type(allow_dns_restart)is not bool:return [],True
    items=[];unknown=False
    for row in rows.values():
        if row.get('state')in('Z','X'):continue
        argv=row.get('argv',[]);exe=row.get('exe','');kind=None
        if exe in('/sbin/fw3','/usr/sbin/fw3'):
            kind='FW3'
            if not argv or argv[-1]!='reload' or any(a not in('fw3','/sbin/fw3','/usr/sbin/fw3','reload','-q','-4','-6','-v')for a in argv):unknown=True
        elif '/etc/init.d/firewall'in argv:
            # Source-pinned rc.common enabled() only checks the startup link.
            # It is a query, not an extra firewall reload worker.
            if exe=='/bin/busybox' and argv==['/bin/sh','/etc/rc.common','/etc/init.d/firewall','enabled']:continue
            kind='FW3';unknown=unknown or not argv or argv[-1]!='reload'
        elif '/etc/init.d/network'in argv:
            kind='NETWORK';unknown=unknown or not argv or argv[-1]!='reload'
        elif '/etc/init.d/dnsmasq'in argv:
            kind='DNSMASQ';expected_restart=allow_dns_restart and argv==['/bin/sh','/etc/rc.common','/etc/init.d/dnsmasq','restart']
            unknown=unknown or not argv or argv[-1]!='reload'and not expected_restart
        elif '/usr/bin/rtp2.sh'in argv:
            kind='RTP';tail=argv[argv.index('/usr/bin/rtp2.sh')+1:]
            unknown=unknown or tail not in (['interface_status_change',target,'up'],['interface_status_change',target,'down'])
        elif any(a in('/lib/netifd/proto/wgclient.sh','/lib/netifd/proto/ovpnclient.sh','./wgclient.sh','./ovpnclient.sh','wgclient.sh','ovpnclient.sh')for a in argv):
            kind='PROTO';relative=any(a in('./wgclient.sh','./ovpnclient.sh','wgclient.sh','ovpnclient.sh')for a in argv)
            unknown=unknown or target not in argv or row.get('proto_source_pinned')is not True or relative and row.get('proto_cwd_verified')is not True
        elif any(a in('/etc/openvpn/scripts/ovpnclient-up','/etc/openvpn/scripts/ovpnclient-down','/etc/openvpn/scripts/ovpnclient-ipchange')for a in argv):kind='HOOK'
        elif '/usr/bin/vpn-failover-trigger.sh'in argv:
            kind='CHECK';unknown=unknown or argv[-2:]!=['check',target]
        elif any(isinstance(a,str)and('rtp2.sh'in a or 'vpn-failover-'in a or 'tunnel-switch.sh'in a or 'wgclient.sh'in a or 'ovpnclient.sh'in a)for a in argv):unknown=True
        if kind:
            if exe not in('/bin/busybox','/sbin/fw3','/usr/sbin/fw3'):unknown=True
            start=row.get('start');pid=row.get('pid')
            if type(pid)is not int or pid<=1 or type(start)is not str or not re.fullmatch('[0-9]{1,24}',start)or int(start)<min_start:unknown=True
            else:items.append((pid,start,kind))
    return items,unknown


def describe(rows,target,min_start):
    """Allowlisted diagnosis of a refusal; never returns raw argv or env."""
    values=[]
    for row in rows.values():
        argv=row.get('argv',[])
        if not any(isinstance(a,str) and any(x in a for x in('rtp2.sh','wgclient.sh','ovpnclient.sh','vpn-failover-','/etc/init.d/firewall','/etc/init.d/network','/etc/init.d/dnsmasq'))for a in argv) and row.get('exe')not in('/sbin/fw3','/usr/sbin/fw3'):continue
        items,unknown=classify({row['pid']:row},target,min_start)
        start=row.get('start','');valid=type(start)is str and re.fullmatch('[0-9]{1,24}',start)is not None
        values.append(dict(pid=row['pid'],start=start if valid else'INVALID',min_start=min_start,
            started_before_trial=bool(valid and int(start)<min_start),unknown=unknown,
            kind=items[0][2]if items else'UNCLASSIFIED',target_token=target in argv,
            exact_proto_path=any(a in('/lib/netifd/proto/wgclient.sh','/lib/netifd/proto/ovpnclient.sh')for a in argv),
            relative_proto_path=any(a in('./wgclient.sh','./ovpnclient.sh','wgclient.sh','ovpnclient.sh')for a in argv),
            proto_cwd_verified=row.get('proto_cwd_verified')is True,proto_source_pinned=row.get('proto_source_pinned')is True,
            inline_proto=any('wgclient.sh'in a or'ovpnclient.sh'in a for a in argv if isinstance(a,str)and a not in('/lib/netifd/proto/wgclient.sh','/lib/netifd/proto/ovpnclient.sh')),
            firewall_reload=bool(argv and argv[-1]=='reload'),
            service_action=argv[-1] if argv and argv[-1] in ('reload','reload_service','start','stop','restart','running','status','service_triggers','validate','boot') else 'OTHER',
            service_argv_shape=[a if a in ('/bin/sh','/etc/rc.common','/etc/init.d/firewall','/sbin/fw3','/usr/sbin/fw3','fw3','reload','reload_service','start','stop','restart','running','status','service_triggers','validate','boot','enable','disable','enabled','triggers','depends','check','-q','-4','-6','-v','') else 'OTHER:'+str(len(a)) for a in argv] if items and items[0][2]=='FW3' else [],
            exe_kind='BUSYBOX'if row.get('exe')=='/bin/busybox'else'FW3'if row.get('exe')in('/sbin/fw3','/usr/sbin/fw3')else'OTHER'))
    return values[:64]


class StartupWork:
    def __init__(self,started,deadline,available_kib,allow_dns_restart=False):
        if not finite(started)or not finite(deadline)or not 0<=started<deadline or type(available_kib)is not int or available_kib<131072:raise ValueError('STARTUP-BOUNDARY')
        if type(allow_dns_restart)is not bool:raise ValueError('STARTUP-BOUNDARY')
        self.allow_dns_restart=allow_dns_restart
        self.started=started;self.deadline=deadline;self.available=available_kib
        self.last=started;self.progress_at=started;self.previous=None;self.seen=set();self.generation=None
        self.quiet_since=None;self.quiet_samples=0;self.lock_since=None;self.terminal=None

    def abort(self,code):
        self.terminal=code
        return code

    def feed(self,now,sample):
        if self.terminal:return self.terminal
        if not finite(now)or not self.last<now<self.deadline or not isinstance(sample,dict):return self.abort('STARTUP-EVIDENCE-INVALID')
        gap=now-self.last;self.last=now
        for key in('recursive','retry_workers','flock_waiters','available_kib'):
            if type(sample.get(key))is not int or sample[key]<0:return self.abort('STARTUP-EVIDENCE-INVALID')
        if sample['recursive']:return self.abort('FW3-RECURSION')
        if sample['retry_workers']:return self.abort('VENDOR-RETRY-WORKER')
        if sample['available_kib']<131072 or self.available-sample['available_kib']>=65536:return self.abort('MEMORY-ABORT')
        if sample['flock_waiters']:
            self.lock_since=now if self.lock_since is None else self.lock_since
            if now-self.lock_since>3:return self.abort('LOCK-WAIT-ABORT')
        else:self.lock_since=None
        if type(sample.get('unknown_work'))is not bool or sample['unknown_work']:return self.abort('STARTUP-WORK-UNVERIFIED')
        items=sample.get('work_items');queues=sample.get('service_queue_codes')
        if not isinstance(items,list)or not isinstance(queues,list)or len(queues)>4 or len(items)>16:return self.abort('STARTUP-WORK-BUDGET')
        counts={key:0 for key in LIMITS};identities=[]
        for row in items:
            if not isinstance(row,(list,tuple))or len(row)!=3:return self.abort('STARTUP-EVIDENCE-INVALID')
            pid,start,kind=row
            if type(pid)is not int or pid<=1 or type(start)is not str or not re.fullmatch('[0-9]{1,24}',start)or kind not in LIMITS:return self.abort('STARTUP-EVIDENCE-INVALID')
            counts[kind]+=1;identities.append((pid,start,kind))
        if len(set(identities))!=len(identities)or any(counts[k]>LIMITS[k]for k in LIMITS):return self.abort('STARTUP-WORK-BUDGET')
        self.seen.update(identities)
        if len(self.seen)>24:return self.abort('STARTUP-WORK-BUDGET')
        queue_keys=[]
        for q in queues:
            if not isinstance(q,dict)or q.get('service')not in SERVICES or not(q.get('action')=='RELOAD'or self.allow_dns_restart and q.get('service')=='DNSMASQ'and q.get('action')=='RESTART'):return self.abort('STARTUP-QUEUE-UNVERIFIED')
            queue_keys.append((q['service'],q['action']))
        if len(set(queue_keys))!=len(queue_keys):return self.abort('STARTUP-QUEUE-UNVERIFIED')
        fingerprint=(tuple(sorted(identities)),tuple(sorted(queue_keys)))
        busy=bool(items or queues or sample['flock_waiters'])
        if fingerprint!=self.previous:self.previous=fingerprint;self.progress_at=now
        if busy and now-self.progress_at>6:return self.abort('STARTUP-WORK-STALLED')
        ready=sample.get('link_ready')
        generation=sample.get('link_generation')
        if type(ready)is not bool:return self.abort('STARTUP-EVIDENCE-INVALID')
        if ready:
            if not isinstance(generation,str)or not 1<=len(generation)<=128:return self.abort('STARTUP-EVIDENCE-INVALID')
            if self.generation is not None and generation!=self.generation:return self.abort('STARTUP-GENERATION-CHANGED')
            self.generation=generation
        elif self.generation is not None:return self.abort('STARTUP-LINK-LOST')
        if busy or not ready or gap>2.5:
            self.quiet_since=None;self.quiet_samples=0
            return 'WAIT'
        if self.quiet_since is None:self.quiet_since=now
        self.quiet_samples+=1
        return 'LINK-SETTLED' if now-self.quiet_since>=3 and self.quiet_samples>=4 else 'WAIT'
