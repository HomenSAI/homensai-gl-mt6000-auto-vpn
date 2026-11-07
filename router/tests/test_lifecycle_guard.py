from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import nullcontext
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import lifecycle_guard as lifecycle
from agent import RUNTIME


class LifecycleTests(unittest.TestCase):
    def test_guard_reads_actual_agent_runtime_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);runtime=root/RUNTIME.relative_to('/')
            runtime.mkdir(parents=True)
            (runtime/'native-status.json').write_text(json.dumps({'state':'APPLYING'}))
            self.assertIsNotNone(lifecycle.assess(*lifecycle.snapshot(root)))

    def test_pending_uci_changes_refuse_before_reading_settings(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=root/'etc/config/homensai_vpn'
            config.parent.mkdir(parents=True);config.write_text("config main 'main'\n")
            for reply,code in ((SimpleNamespace(returncode=0,stdout=b"homensai_vpn.main.interval='99'"),'LIFECYCLE-PENDING-UCI-CHANGES'),
                               (SimpleNamespace(returncode=1,stdout=b''),'LIFECYCLE-CONFIG-UNVERIFIED')):
                with patch.object(lifecycle.subprocess,'run',return_value=reply) as run:
                    with self.assertRaisesRegex(ValueError,code):lifecycle.snapshot(root)
                    self.assertEqual(run.call_args.args[0],['/sbin/uci','-q','changes','homensai_vpn'])
                    self.assertEqual(run.call_count,1)

    def test_active_unknown_and_held_policies_refuse_upgrade(self):
        for state in lifecycle.ACTIVE|{'STOPPED-ON-RESERVE','UNKNOWN'}:
            self.assertIsNotNone(lifecycle.assess({}, {'state':state},{},{},{}))
        self.assertIsNotNone(lifecycle.assess({}, {'guard':'closed'},{},{},{}))
        self.assertIsNotNone(lifecycle.assess({}, {},{'phase':'CORRUPT'},{},{}))
        self.assertIsNotNone(lifecycle.assess({'native_enabled':1},{},{},{},{}))

    def test_factory_monitor_and_explicit_ack_are_safe(self):
        self.assertIsNone(lifecycle.assess({}, {},{},{},{}))
        self.assertIsNone(lifecycle.assess({'native_enabled':'0'}, {'state':'DISABLED'},{},{},{}))
        self.assertIsNone(lifecycle.assess({}, {'state':'STOPPED','time':4,'original_restored':True},
            {'phase':'ROLLED-BACK'},{'mode':'on','trial':'t','time':1},{'trial':'t','requested':3}))

    def test_private_trial_invalidation_refuses_silent_resume(self):
        self.assertIsNone(lifecycle.assess({'native_enabled':'0','native_trial':''},{'state':'DISABLED'},
            {},{'mode':'on','trial':'old','time':1},{}))
        self.assertIsNotNone(lifecycle.assess({'native_enabled':False},{'state':'DISABLED'},
            {},{'mode':'on','trial':'old','time':1},{}))

    def test_legacy_enable_requires_current_private_trial_and_controller_ack(self):
        status={'state':'STOPPED','time':4,'original_restored':True}
        stopped={'trial':'legacy','requested':3}
        self.assertIsNone(lifecycle.assess({'native_enabled':'1','native_trial':'legacy'},status,{'phase':'ROLLED-BACK'},{},stopped))
        self.assertIsNotNone(lifecycle.assess({'native_enabled':'1','native_trial':'new'},status,{'phase':'ROLLED-BACK'},{},stopped))
        self.assertIsNotNone(lifecycle.assess({'native_enabled':'1'},status,{'phase':'ROLLED-BACK'},{},stopped))

    def test_corrupt_checksum_never_becomes_an_empty_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'etc/homensai-vpn';target.mkdir(parents=True)
            (target/'native-transaction.json').write_text(json.dumps({'schema':1,'data':{'phase':'ROLLED-BACK'},'sha256':'wrong'}))
            with self.assertRaises(ValueError):lifecycle.snapshot(root)

    def test_prepare_changes_only_own_auto_scope_and_failed_write_is_not_ready(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        with patch.object(lifecycle,'ROOT',Path(directory.name)),patch.object(lifecycle,'control_lock',return_value=nullcontext()),patch.object(lifecycle,'snapshot',return_value=({},{},{},{},{})),patch.object(lifecycle.subprocess,'run') as run:
            run.return_value.returncode=0
            lifecycle.main('prepare')
            self.assertEqual(run.call_args.args[0],['/sbin/uci','-q','batch'])
            batch=run.call_args.kwargs['input']
            self.assertEqual(batch.count(b'\n'),4)
            self.assertNotIn(b'token',batch);self.assertNotIn(b'network',batch)
            run.return_value.returncode=1
            with self.assertRaises(SystemExit):lifecycle.main('prepare')


BOOT='0f0e0d0c-0b0a-4908-8706-050403020100'


class MaintenanceMarkerTests(unittest.TestCase):
    """Plan item 54 (audit F-16/F-17): every guard run marks the package operation before it assesses; a refusal removes
    the mark; after the stop the guard waits for the service processes and reads the supervisor's shutdown record."""
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.root=Path(directory.name)
        (self.root/'proc/sys/kernel/random').mkdir(parents=True)
        (self.root/'proc/sys/kernel/random/boot_id').write_text(BOOT+'\n')
        (self.root/'proc/uptime').write_text('321.5 100.0\n')
        self.runtime=self.root/'var/run/homensai-vpn';self.runtime.mkdir(parents=True)
        self.marker=self.root/'etc/homensai-vpn/maintenance.json'
        for target in (patch.object(lifecycle,'ROOT',self.root),patch.object(lifecycle,'control_lock',return_value=nullcontext())):
            target.start();self.addCleanup(target.stop)

    def run_guard(self,action,snapshot=None,assess=None):
        seen={}
        def snap(**kwargs):
            seen['marker']=json.loads(self.marker.read_text()) if self.marker.exists() else None
            if isinstance(snapshot,Exception):raise snapshot
            return ({},{},{},{},{},False) if kwargs.get('upgrade') else ({},{},{},{},{})
        with patch.object(lifecycle,'snapshot',side_effect=snap),patch.object(lifecycle,'assess',return_value=assess),\
                patch.object(lifecycle.subprocess,'run') as run:
            run.return_value.returncode=0
            try:lifecycle.main(action);code=0
            except SystemExit as exit_:code=exit_.code
        return code,seen.get('marker')

    def test_the_mark_is_written_under_the_lock_before_the_assessment(self):
        for action,kind in (('check','remove'),('upgrade','upgrade'),('prepare','install')):
            with self.subTest(action=action):
                # IR-04: each action from a clean start (a prepare after a live upgrade mark keeps 'upgrade')
                if self.marker.exists():self.marker.unlink()
                code,seen=self.run_guard(action)
                self.assertEqual(code,0)
                self.assertEqual({k:seen[k] for k in ('action','boot_id','uptime')},{'action':kind,'boot_id':BOOT,'uptime':321.5})
                self.assertTrue(self.marker.exists(),'a passed guard keeps the mark for the rest of the package operation')
                # the readers see exactly this record as an active package operation
                sys.path.insert(0,str(Path(lifecycle.__file__).parent))
                import maintenance
                self.assertEqual(maintenance.current(self.marker.parent,self.root/'proc',seen['time'])['state'],'active')

    def test_any_refusal_removes_the_mark(self):
        for snapshot,assess in ((ValueError('LIFECYCLE-STOP-AUTO-FIRST'),None),(None,'LIFECYCLE-JOURNAL-ACTIVE'),(OSError('io'),None)):
            with self.subTest(snapshot=snapshot,assess=assess):
                code,seen=self.run_guard('upgrade',snapshot,assess)
                self.assertEqual(code,1)
                self.assertIsNotNone(seen,'the mark existed during the assessment')
                self.assertFalse(self.marker.exists())

    def test_a_mark_that_cannot_be_written_refuses(self):
        (self.root/'etc').mkdir();(self.root/'etc/homensai-vpn').write_text('not a directory')
        with patch('sys.stderr') as err:
            code,_=self.run_guard('upgrade')
        self.assertEqual(code,1)
        self.assertIn('LIFECYCLE-MAINTENANCE-FAILED',''.join(call.args[0] for call in err.write.call_args_list))

    def proc(self,pid,*argv):
        entry=self.root/'proc'/str(pid);entry.mkdir()
        (entry/'cmdline').write_bytes(b'\0'.join(a.encode() for a in argv)+b'\0')
        return entry

    def test_after_the_stop_the_guard_waits_for_every_service_process(self):
        self.proc(10,'/usr/bin/lua','/usr/lib/homensai-vpn/lua/auto.lua','daemon')
        self.proc(11,'/usr/bin/python3','/usr/lib/homensai-vpn/agent.py','call','status')   # an rpcd call: not the service
        self.proc(12,'/bin/sh','/usr/lib/opkg/info/homensai-auto-vpn.prerm','upgrade')
        self.assertEqual(lifecycle.service_processes(self.root),[10])
        apply=self.proc(13,'/usr/bin/python3','/usr/lib/homensai-vpn/native_switch.py','apply','x')
        self.assertEqual(sorted(lifecycle.service_processes(self.root)),[10,13])
        clock=[0.0];naps=[]
        def sleep(seconds):
            naps.append(seconds);clock[0]+=seconds
            if len(naps)==3:
                for pid in (10,13):
                    for child in (self.root/'proc'/str(pid)).iterdir():child.unlink()
                    (self.root/'proc'/str(pid)).rmdir()
        lifecycle.wait_service_exit(self.root,limit=10,sleep=sleep,clock=lambda:clock[0])
        self.assertEqual(len(naps),3)
        self.proc(20,'/usr/bin/lua','/usr/lib/homensai-vpn/lua/hv_core.lua','standby')
        with self.assertRaisesRegex(ValueError,'LIFECYCLE-STOP-UNFINISHED'):
            lifecycle.wait_service_exit(self.root,limit=2,sleep=lambda s:clock.__setitem__(0,clock[0]+s),clock=lambda:clock[0])
        with self.assertRaisesRegex(ValueError,'LIFECYCLE-STOP-UNFINISHED'):
            lifecycle.wait_service_exit(self.root/'nowhere',limit=2)
        del apply

    def test_a_service_still_running_after_the_stop_refuses_and_removes_the_mark(self):
        self.marker.parent.mkdir(parents=True);self.marker.write_text('{}')
        with patch.object(lifecycle,'wait_service_exit',side_effect=ValueError('LIFECYCLE-STOP-UNFINISHED')):
            code,seen=self.run_guard('upgrade-stopped')
        self.assertEqual((code,seen),(1,None),'refused before the lock: nothing assessed')
        self.assertFalse(self.marker.exists())

    def test_the_shutdown_record_must_say_the_recovery_finished(self):
        record=self.runtime/'supervisor-shutdown.json'
        with patch.object(lifecycle,'wait_service_exit') as wait:
            for body,expected in (('{"ok":true,"time":5}',0),('{"ok":false,"code":"PAIR-RECOVERY-REQUIRED","time":5}',1),('{"ok":',1),(None,0)):
                with self.subTest(body=body):
                    if body is None:
                        if record.exists():record.unlink()
                    else:record.write_text(body)
                    code,_=self.run_guard('check-stopped')
                    self.assertEqual(code,expected)
                    self.assertEqual(self.marker.exists(),expected==0)
            self.assertTrue(wait.called)
        # the first guard of prerm forgets an older record, so after the stop only this shutdown's record counts
        record.write_text('{"ok":false}')
        self.assertEqual(self.run_guard('check')[0],0)
        self.assertFalse(record.exists())

    def test_an_unknown_action_is_refused(self):
        with self.assertRaises(SystemExit):lifecycle.main('prepare-stopped')
        self.assertFalse(self.marker.exists())


if __name__=='__main__':unittest.main()
