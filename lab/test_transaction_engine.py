import itertools
from pathlib import Path
import tempfile
import unittest
import fcntl
import os
from unittest.mock import patch
from transaction_engine import Engine,Journal,Blocked,GATES,CHECKS


class Crash(BaseException):
    pass


class RouterAdapter:
    """Fault-injection backend. Not a GL.iNet driver."""
    def __init__(self,fault=None,bad_check=None,external=False):
        self.profile='primary';self.generation=0;self.writer=None
        self.gate=True;self.management=True;self.watchdog=False
        self.dns='primary';self.killswitch=True;self.special='unchanged'
        self.fault=fault;self.bad_check=bad_check;self.external=external;self.calls=[]
    def event(self,name):
        self.calls.append(name)
        if self.fault==name:self.fault=None;raise RuntimeError(name)
        if self.fault=='crash:'+name:self.fault=None;raise Crash(name)
    def preflight(self,scope):return {k:True for k in GATES}
    def snapshot(self,scope):return {'profile':self.profile,'generation':self.generation,'dns':self.dns,'special':self.special,'killswitch':self.killswitch}
    def arm_watchdog(self,*args):self.watchdog=True;self.event('arm')
    def close_gate(self,scope):self.gate=False;self.event('close')
    def apply(self,tx,target,generation):
        self.event('apply_before')
        if generation!=self.generation:raise Blocked('GENERATION')
        self.profile=target;self.dns=target;self.generation+=1;self.writer=tx
        if self.external:self.writer='external';self.generation+=1
        self.event('apply_after')
    def owns(self,tx):return self.writer==tx
    def owns_or_unchanged(self,tx,before):return self.owns(tx) or self.generation==before['generation']
    def flush_scoped(self,scope):self.event('flush')
    def verify(self,profile):
        self.event('verify')
        checks={k:self.profile==profile and self.dns==profile and self.management and self.killswitch and self.special=='unchanged' for k in CHECKS}
        if profile=='backup' and self.bad_check:checks[self.bad_check]=False
        return checks
    def commit(self,tx,target):self.event('commit')
    def open_gate(self,scope):self.gate=True;self.event('open')
    def disarm_watchdog(self,tx):self.event('disarm');self.watchdog=False
    def restore(self,tx,before):
        self.event('restore');self.profile=before['profile'];self.dns=before['dns'];self.special=before['special'];self.killswitch=before['killswitch'];self.generation+=1;self.writer=tx


class TransactionTests(unittest.TestCase):
    def test_recovery_does_not_reopen_after_external_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=RouterAdapter();journal=Journal(Path(directory)/'tx.json');engine=Engine(adapter,journal)
            self.assertEqual(engine.run('backup','common',True)['state'],'COMMITTED')
            adapter.writer='operator';adapter.generation+=1
            self.assertEqual(engine.recover()['reason'],'EXTERNAL-WRITER')
            self.assertFalse(adapter.gate);self.assertTrue(adapter.management)
            self.assertNotIn('restore',adapter.calls)

    def test_deadline_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=RouterAdapter();ticks=iter([0,100])
            engine=Engine(adapter,Journal(Path(directory)/'tx.json'),clock=lambda:next(ticks))
            self.assertEqual(engine.run('backup','common',True)['state'],'ROLLED-BACK')
            self.assertEqual(adapter.profile,'primary')

    def test_failed_intent_write_never_mutates_and_late_write_rolls_back(self):
        for failure in (1,2,3):
            with self.subTest(write=failure),tempfile.TemporaryDirectory() as directory:
                adapter=RouterAdapter();journal=Journal(Path(directory)/'tx.json');engine=Engine(adapter,journal)
                original=journal.write;calls=[0]
                def write(value):
                    calls[0]+=1
                    if calls[0]==failure:raise OSError('simulated ENOSPC')
                    original(value)
                with patch.object(journal,'write',side_effect=write):
                    if failure==1:
                        with self.assertRaises(OSError):engine.run('backup','common',True)
                        self.assertEqual(adapter.calls,[])
                    else:self.assertEqual(engine.run('backup','common',True)['state'],'ROLLED-BACK')

    def test_apply_and_recovery_share_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            journal=Journal(Path(directory)/'tx.json');adapter=RouterAdapter();engine=Engine(adapter,journal)
            fd=os.open(str(journal.path.with_suffix('.lock')),os.O_CREAT|os.O_RDWR,0o600)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(Blocked):engine.run('backup','common',True)
                with self.assertRaises(Blocked):engine.recover()
                self.assertEqual(adapter.calls,[])
            finally:os.close(fd)

    def test_verified_commit_and_every_required_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=RouterAdapter();engine=Engine(adapter,Journal(Path(directory)/'tx.json'))
            self.assertEqual(engine.run('backup','common',True)['state'],'COMMITTED')
            self.assertTrue(adapter.gate);self.assertTrue(adapter.management)
            self.assertFalse(adapter.watchdog)
        for gate in GATES:
            with self.subTest(gate=gate),tempfile.TemporaryDirectory() as directory:
                adapter=RouterAdapter();adapter.preflight=lambda scope:{k:k!=gate for k in GATES}
                engine=Engine(adapter,Journal(Path(directory)/'tx.json'))
                with self.assertRaises(Blocked):engine.run('backup','common',True)
                self.assertEqual(adapter.calls,[])

    def test_external_writer_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=RouterAdapter(external=True);engine=Engine(adapter,Journal(Path(directory)/'tx.json'))
            self.assertEqual(engine.run('backup','common',True)['state'],'BLOCKED')
            self.assertNotIn('restore',adapter.calls)
            self.assertFalse(adapter.gate);self.assertTrue(adapter.management)
            self.assertTrue(adapter.watchdog)

    def test_late_external_writer_after_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=RouterAdapter();original=adapter.verify
            def verify(profile):
                value=original(profile)
                if profile=='backup':adapter.writer='operator';adapter.generation+=1
                return value
            adapter.verify=verify
            engine=Engine(adapter,Journal(Path(directory)/'tx.json'))
            self.assertEqual(engine.run('backup','common',True)['state'],'BLOCKED')
            self.assertNotIn('restore',adapter.calls);self.assertFalse(adapter.gate)
            self.assertTrue(adapter.management)

    def test_200_fault_combinations(self):
        scenarios=list(itertools.product([None,'arm','close','apply_before','apply_after','flush','verify','commit','open','disarm'],[None]+list(CHECKS),[False,True]))
        # All 140 distinct stage/check/writer combinations, plus 60 distinct
        # crash cases. No live router, DNS service or firewall is touched.
        scenarios += [('crash:'+stage,check,False) for stage in ('arm','close','apply_before','apply_after','flush','verify','commit','open','disarm','restore') for check in CHECKS]
        self.assertEqual(len(scenarios),200)
        for index,(fault,bad,external) in enumerate(scenarios):
            with self.subTest(case=index),tempfile.TemporaryDirectory() as directory:
                adapter=RouterAdapter(fault,bad,external);journal=Journal(Path(directory)/'tx.json');engine=Engine(adapter,journal)
                try:outcome=engine.run('backup','common',True)
                except Crash:
                    outcome=Engine(adapter,Journal(journal.path)).recover()
                self.assertTrue(adapter.management)
                self.assertTrue(adapter.killswitch)
                self.assertEqual(adapter.special,'unchanged')
                if outcome['state']=='COMMITTED':
                    self.assertEqual(adapter.profile,'backup');self.assertTrue(adapter.gate)
                elif outcome['state']=='ROLLED-BACK':
                    self.assertEqual(adapter.profile,'primary');self.assertEqual(adapter.dns,'primary');self.assertTrue(adapter.gate)
                else:
                    self.assertEqual(outcome['state'],'BLOCKED');self.assertFalse(adapter.gate)

    def test_corrupt_journal_and_unapproved_session_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'tx.json';journal=Journal(path);adapter=RouterAdapter();engine=Engine(adapter,journal)
            with self.assertRaises(Blocked):engine.run('backup','common')
            self.assertEqual(adapter.calls,[])
            path.write_text('{broken')
            with self.assertRaises(Blocked):engine.recover()
            self.assertEqual(adapter.calls,[])
