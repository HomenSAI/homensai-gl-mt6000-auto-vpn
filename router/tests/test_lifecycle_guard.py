from pathlib import Path
import json
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
        with patch.object(lifecycle,'control_lock',return_value=nullcontext()),patch.object(lifecycle,'snapshot',return_value=({},{},{},{},{})),patch.object(lifecycle.subprocess,'run') as run:
            run.return_value.returncode=0
            lifecycle.main('prepare')
            self.assertEqual(run.call_args.args[0],['/sbin/uci','-q','batch'])
            batch=run.call_args.kwargs['input']
            self.assertEqual(batch.count(b'\n'),4)
            self.assertNotIn(b'token',batch);self.assertNotIn(b'network',batch)
            run.return_value.returncode=1
            with self.assertRaises(SystemExit):lifecycle.main('prepare')


if __name__=='__main__':unittest.main()
