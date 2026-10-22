"""Exercise real native attempt boundaries with fake vendor/kernel operations."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import native_switch as native
from test_native_switch import Backend


class ManualNativeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for module in (agent,native):
            for name in ('RUNTIME','PERSIST'):
                self.stack.enter_context(patch.object(module,name,self.root))
        for name,file in (('JOURNAL','journal'),('STATE','status'),('CERT','certificate')):
            self.stack.enter_context(patch.object(native,name,self.root/file))
        self.stack.enter_context(patch.object(native,'STOP',False))
        self.stack.enter_context(patch.object(native.os,'killpg'))
        self.stack.enter_context(patch.object(native,'clear_native_options',return_value=True))
        self.stack.enter_context(patch.object(native.uuid,'uuid4',return_value=MagicMock(hex='e'*32)))
        self.backend=Backend();self.before=self.backend.current[:]
        self.process=MagicMock(pid=123,returncode=0)
        self.confirm=True
        def spawn(*args,**kwargs):
            self.backend.current[-2],self.backend.current[-1]=self.backend.current[-1],self.backend.current[-2]
            if self.confirm:
                native.atomic_json(self.root/'native-confirm.json',{'tx':'e'*32,'exit_ipv4':'9.9.9.9',
                    'dns_ok':True,'https_ok':True,'time':time.time()})
            return self.process
        self.stack.enter_context(patch.object(native.subprocess,'Popen',side_effect=spawn))
        self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        self.revision=auto_control.current_revision(self.root)

    def attempt(self):
        native.attempt(self.backend,self.backend.selection,time.time()+120,False,
            control_revision=self.revision,manual_request_id='a'*32)

    def test_client_confirmed_manual_holds_without_enabling_auto_or_minting_certificate(self):
        self.attempt();j=native.journal_read()
        self.assertEqual(j['phase'],'HELD-ON-RESERVE');self.assertEqual(j['manual_request_id'],'a'*32)
        self.assertNotEqual(self.backend.current,self.before)
        self.assertFalse(native.CERT.exists());self.assertFalse((self.root/'auto-control.json').exists())
        self.assertEqual(agent.read_json(native.STATE)['state'],'STOPPED-ON-RESERVE')

    def test_stop_after_committed_write_rolls_back_instead_of_claiming_manual_success(self):
        original=native.journal_write;rotated=[]
        def write(j):
            original(j)
            if j.get('phase')=='COMMITTED' and not rotated:
                # uuid is shared by native and auto_control. The fixed native
                # transaction fixture must not also freeze Stop's new epoch.
                with patch.object(auto_control.uuid,'uuid4',return_value=MagicMock(hex='f'*32)):
                    rotated.append(auto_control.current_revision(self.root,rotate=True))
        with patch.object(native,'journal_write',side_effect=write):
            with self.assertRaises(native.Refused):self.attempt()
        self.assertEqual(self.backend.current,self.before)
        self.assertNotEqual(rotated[0],self.revision)
        self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
        self.assertFalse(native.CERT.exists())

    def test_stop_ordered_after_held_completion_does_not_invent_rollback_success(self):
        original=native.publish
        def publish(value):
            original(value)
            if value.get('reason')=='OPERATOR-MANUAL' and value.get('state')=='STOPPED-ON-RESERVE':
                with patch.object(auto_control.uuid,'uuid4',return_value=MagicMock(hex='f'*32)):
                    auto_control.current_revision(self.root,rotate=True)
        with patch.object(native,'publish',side_effect=publish):self.attempt()
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE')
        self.assertFalse(agent.read_json(native.STATE)['original_restored'])
        self.assertNotEqual(self.backend.current,self.before)

    def test_router_probe_without_client_ack_is_not_manual_switch_success(self):
        self.confirm=False
        with patch.object(native,'transaction_expired',return_value=True):
            with self.assertRaises(native.Refused):self.attempt()
        self.assertEqual(self.backend.current,self.before)
        self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
        self.assertFalse(native.CERT.exists())

    def test_manual_id_cannot_convert_a_trial_into_a_privileged_manual_request(self):
        with self.assertRaisesRegex(native.Refused,'MANUAL-REQUEST-INVALID'):
            native.attempt(self.backend,self.backend.selection,time.time()+120,True,
                control_revision=self.revision,manual_request_id='a'*32)
        self.assertEqual(self.backend.current,self.before);self.assertFalse(native.JOURNAL.exists())


if __name__=='__main__':unittest.main()
