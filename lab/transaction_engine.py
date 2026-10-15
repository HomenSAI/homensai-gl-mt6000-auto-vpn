"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
Executable transaction contract for a verified adapter. No native adapter exists.
No shell commands. Tests use an in-memory router and durable temporary journal.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

GATES=('adapter_verified','workers_coordinated','management_independent','watchdog_independent',
       'dns_scoped','killswitch_preserved','ipv6_verified','conntrack_scoped','special_rules_preserved')
CHECKS=('client_v4','client_v6_or_blocked','client_dns','killswitch','management','special_rules')


class Blocked(RuntimeError):
    pass


class Journal:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise Blocked('JOURNAL-SYMLINK')

    def write(self,data):
        raw=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
        record=json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'data':data},sort_keys=True).encode()
        pending=self.path.with_suffix('.pending')
        fd=os.open(str(pending),os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(record);stream.flush();os.fsync(stream.fileno())
        os.replace(str(pending),str(self.path))
        fd=os.open(str(self.path.parent),os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def read(self):
        if self.path.is_symlink():raise Blocked('JOURNAL-SYMLINK')
        if not self.path.exists():return None
        if self.path.stat().st_size>1024*1024:raise Blocked('JOURNAL-OVERSIZE')
        try:
            record=json.loads(self.path.read_text())
            raw=json.dumps(record['data'],sort_keys=True,separators=(',',':')).encode()
            if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError()
            return record['data']
        except (ValueError,KeyError,TypeError):raise Blocked('JOURNAL-CORRUPT')


class Engine:
    def __init__(self,adapter,journal,clock=time.monotonic):
        self.adapter,self.journal,self.clock=adapter,journal,clock

    def _verify(self,target):
        checks=self.adapter.verify(target)
        if any(checks.get(key) is not True for key in CHECKS):
            raise Blocked('VERIFY-FAILED')

    def run(self,target,scope,allow_session_loss=False,timeout=30):
        # The lock coordinates our executor only. Adapter preflight MUST establish
        # real agreement with stock workers; a private mutex is insufficient.
        lock_path=self.journal.path.with_suffix('.lock')
        fd=os.open(str(lock_path),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Blocked('TRANSACTION-BUSY')
            old=self.journal.read()
            if old and old['state'] not in ('COMMITTED','ROLLED-BACK'):
                raise Blocked('RECOVERY-REQUIRED')
            capabilities=self.adapter.preflight(scope)
            if any(capabilities.get(key) is not True for key in GATES):
                raise Blocked('ADAPTER-GATES-FAILED')
            if not allow_session_loss:raise Blocked('SESSION-LOSS-NOT-APPROVED')
            before=self.adapter.snapshot(scope)
            tx=uuid.uuid4().hex
            record={'id':tx,'state':'INTENT','target':target,'scope':scope,'before':before}
            deadline=self.clock()+timeout
            self.journal.write(record)  # No mutation if durable intent fails.
            try:
                self.adapter.arm_watchdog(tx,before,deadline)
                self.adapter.close_gate(scope)  # Must never close management.
                self.adapter.apply(tx,target,before['generation'])
                if self.clock()>deadline:raise Blocked('DEADLINE')
                if not self.adapter.owns(tx):raise Blocked('EXTERNAL-WRITER')
                self.adapter.flush_scoped(scope)
                self._verify(target)
                if self.clock()>deadline:raise Blocked('DEADLINE')
                if not self.adapter.owns(tx):raise Blocked('EXTERNAL-WRITER')
                record['state']='VERIFIED';self.journal.write(record)
                self.adapter.commit(tx,target)
                record['state']='COMMITTED';self.journal.write(record)
                self.adapter.open_gate(scope)
                self.adapter.disarm_watchdog(tx)
                return {'state':'COMMITTED','applied':True,'transaction':tx}
            except Exception:
                return self._rollback(record)
        finally:
            os.close(fd)

    def _rollback(self,record):
        # Never overwrite a newer external operator/worker configuration.
        try:
            self.adapter.close_gate(record['scope'])
            if not self.adapter.owns_or_unchanged(record['id'],record['before']):
                raise Blocked('EXTERNAL-WRITER')
            self.adapter.restore(record['id'],record['before'])
            self._verify(record['before']['profile'])
            record=dict(record,state='ROLLED-BACK');self.journal.write(record)
            self.adapter.open_gate(record['scope'])
            self.adapter.disarm_watchdog(record['id'])
            return {'state':'ROLLED-BACK','applied':False,'transaction':record['id']}
        except Exception:
            # Independent watchdog remains armed; do not claim restored Internet.
            try:self.adapter.close_gate(record['scope'])
            except Exception:
                return {'state':'UNVERIFIED','applied':False,'transaction':record['id'],
                        'reason':'TRAFFIC-GATE-UNVERIFIED','watchdog_required':True}
            return {'state':'BLOCKED','applied':False,'transaction':record['id'],
                    'reason':'ROLLBACK-UNVERIFIED','watchdog_required':True}

    def recover(self):
        fd=os.open(str(self.journal.path.with_suffix('.lock')),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Blocked('TRANSACTION-BUSY')
            record=self.journal.read()
            if not record:return {'state':'NO-TRANSACTION'}
            if record['state'] in ('COMMITTED','ROLLED-BACK') and not self.adapter.owns(record['id']):
                self.adapter.close_gate(record['scope'])
                return {'state':'BLOCKED','applied':False,'reason':'EXTERNAL-WRITER'}
            if record['state']=='COMMITTED':
                try:self._verify(record['target'])
                except Blocked:
                    self.adapter.close_gate(record['scope'])
                    return {'state':'BLOCKED','applied':False,'reason':'COMMITTED-PATH-UNHEALTHY'}
                self.adapter.open_gate(record['scope']);self.adapter.disarm_watchdog(record['id'])
                return {'state':'COMMITTED','applied':True}
            if record['state']=='ROLLED-BACK':
                try:self._verify(record['before']['profile'])
                except Blocked:
                    self.adapter.close_gate(record['scope'])
                    return {'state':'BLOCKED','applied':False,'reason':'RESTORED-PATH-UNHEALTHY'}
                self.adapter.open_gate(record['scope']);self.adapter.disarm_watchdog(record['id'])
                return {'state':'ROLLED-BACK','applied':False}
            return self._rollback(record)
        finally:os.close(fd)
