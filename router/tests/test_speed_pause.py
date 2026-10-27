import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch,Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch,pair_auto,speed_pause as pause,speed_test as speed


class Tests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        for module in(pause,auto_control,speed):
            p=patch.object(module,'RUNTIME',self.root);p.start();self.addCleanup(p.stop)
        for key,value in [('JOB',self.root/'speed-job.json'),('CANCEL',self.root/'speed-cancel.json'),('PERSIST',self.root)]:
            p=patch.object(speed,key,value);p.start();self.addCleanup(p.stop)
        p=patch.object(pause,'boot',return_value='test-boot');p.start();self.addCleanup(p.stop)
        self.rev=auto_control.current_revision(self.root)
        agent.atomic_json(self.root/'pair-auto-control.json',{'mode':'on','revision':self.rev,'time':time.time()})
        self.owners={'auto':{'pid':41,'start':410},'monitor':{'pid':42,'start':420}}
        self.worker={'pid':43,'start':430}
        self.tx='a'*32

    def lease(self,**changes):
        row=dict(schema=1,tx=self.tx,boot='test-boot',worker=self.worker,owners=self.owners,acks={},
                 revision=self.rev,intents=pause.fingerprints(),phase='PAUSED',deadline=time.monotonic()+60,
                 auto_was_on=True)
        row.update(changes);agent.atomic_json(pause.path(),row);return row

    def gate(self,role):
        with patch.object(pause,'identity',return_value=self.owners[role]),patch.object(pause,'alive',return_value=True):
            return pause.gate(role)

    def fresh(self):
        row=pause.load();stamp=row['resume_time']+.1
        agent.atomic_json(self.root/'status.json',{'time':stamp,'profiles':[{'administrative_state':'enabled','time':stamp}]})

    def test_waits_for_both_safe_points_then_monitor_resumes_before_auto(self):
        job={'tx':self.tx,'monotonic_deadline':time.monotonic()+70};done=threading.Event();errors=[]
        def acquire():
            try:pause.acquire(job)
            except Exception as e:errors.append(e)
            finally:done.set()
        with patch.object(pause,'participants',return_value=self.owners),patch.object(pause,'identity',return_value=self.worker),patch.object(pause,'alive',return_value=True),patch.object(pair_auto,'read_state',return_value={'phase':'RUNNING'}),patch.object(pair_auto,'intent',return_value={'mode':'on'}):
            agent.atomic_json(self.root/'native-status.json',{'state':'OBSERVING'})
            thread=threading.Thread(target=acquire);thread.start()
            try:
                end=time.monotonic()+2
                while not pause.path().exists()and time.monotonic()<end:time.sleep(.01)
                with patch.object(pause,'identity',return_value=self.owners['auto']):self.assertTrue(pause.gate('auto'))
                self.assertFalse(done.wait(.25),'one acknowledgement must not admit measurement')
                with patch.object(pause,'identity',return_value=self.owners['monitor']):self.assertTrue(pause.gate('monitor'))
                self.assertTrue(done.wait(2));self.assertEqual(errors,[])
            finally:thread.join(3)
        original=(self.root/'pair-auto-control.json').read_bytes()
        with patch.object(pause,'alive',return_value=True):pause.release(self.tx)
        self.assertFalse(self.gate('monitor'));self.assertTrue(self.gate('auto'))
        self.fresh();self.assertFalse(self.gate('auto'));self.assertFalse(pause.path().exists())
        self.assertEqual((self.root/'pair-auto-control.json').read_bytes(),original)

    def test_manual_stop_supersedes_pause_and_is_never_undone(self):
        self.lease()
        with patch.object(agent,'command',return_value=b'{"settings":{}}'):
            result=auto_control.stop(runtime=self.root,persist=self.root,request_source='manual')
        self.assertTrue(result['queued']);stopped=(self.root/'pair-auto-control.json').read_bytes()
        self.assertEqual(json.loads(stopped)['mode'],'off');self.assertTrue(pause.interrupted(self.tx))
        with patch.object(pause,'alive',return_value=False):self.assertFalse(pause.gate('auto'))
        pause.release(self.tx);self.assertEqual((self.root/'pair-auto-control.json').read_bytes(),stopped)
        self.assertFalse(pause.path().exists())

    def test_original_off_is_preserved_and_absent_services_are_never_started(self):
        agent.atomic_json(self.root/'pair-auto-control.json',{'mode':'off','revision':self.rev,'time':time.time()})
        row=self.lease(auto_was_on=False,owners={})
        before=(self.root/'pair-auto-control.json').read_bytes()
        with patch.object(pause.subprocess,'run',side_effect=AssertionError('no service command')):
            pause.release(row['tx'])
        self.assertFalse(pause.path().exists());self.assertEqual((self.root/'pair-auto-control.json').read_bytes(),before)

    def test_worker_loss_releases_only_after_fresh_monitor_observation(self):
        self.lease()
        def alive(owner):return owner!=self.worker
        with patch.object(pause,'alive',side_effect=alive),patch.object(pause,'identity',return_value=self.owners['auto']):
            self.assertTrue(pause.gate('auto'));self.assertEqual(pause.load()['phase'],'RESUMING')
            self.fresh();self.assertFalse(pause.gate('auto'))
        self.assertFalse(pause.path().exists())

    def test_deadline_signals_only_matching_owned_worker(self):
        self.lease(deadline=time.monotonic()-1)
        agent.atomic_json(speed.JOB,{'tx':self.tx,'pid':43,'state':'RUNNING'})
        with patch.object(pause,'alive',return_value=True),patch.object(speed,'worker_alive',return_value=True),patch.object(pause.os,'kill')as kill:
            self.assertTrue(pause.gate('auto'));kill.assert_called_once_with(43,pause.signal.SIGTERM)
        with patch.object(pause,'alive',return_value=True),patch.object(pause,'identity',return_value=self.owners['auto']),patch.object(speed,'worker_alive',return_value=False),patch.object(pause.os,'kill')as kill:
            self.assertTrue(pause.gate('auto'));kill.assert_not_called()
            self.assertEqual(pause.load()['phase'],'RESUMING')

    def test_pid_reuse_cannot_receive_a_signal(self):
        self.lease(deadline=time.monotonic()-1)
        with patch.object(pause,'identity',return_value={'pid':43,'start':999}):self.assertFalse(pause.alive(self.worker))
        with patch.object(pause,'alive',return_value=False),patch.object(pause.os,'kill')as kill:
            pause.gate('auto');kill.assert_not_called()

    def test_resume_wait_is_bounded_when_monitor_disappears(self):
        self.lease();
        with patch.object(pause,'alive',return_value=True):pause.release(self.tx)
        row=pause.load();row['resume_deadline']=time.monotonic()-1;agent.atomic_json(pause.path(),row)
        self.assertFalse(self.gate('auto'));self.assertFalse(pause.path().exists())

    def test_monitor_only_installation_cleans_the_window(self):
        self.lease(owners={'monitor':self.owners['monitor']})
        with patch.object(pause,'alive',return_value=True):pause.release(self.tx)
        self.assertFalse(self.gate('monitor'));self.assertFalse(pause.path().exists())

    def test_public_pause_does_not_disclose_owners_revision_or_intent_fingerprints(self):
        self.lease(acks={'auto':{'owner':self.owners['auto'],'time':time.monotonic()}})
        value=pause.public();self.assertTrue(value['active']);self.assertTrue(value['auto_paused'])
        for key in('owners','worker','revision','intents','tx','pid'):self.assertNotIn(key,value)

    def test_corrupt_pause_cannot_freeze_control_or_authorize_measurement(self):
        agent.atomic_json(pause.path(),{'schema':1})
        self.assertEqual(pause.public(),{'active':False});self.assertFalse(pause.gate('auto'))
        with self.assertRaises(pause.PauseError):pause.load()

    def test_missing_acknowledgement_times_out_and_release_remains_available(self):
        clock=[100.0]
        agent.atomic_json(self.root/'native-status.json',{'state':'OBSERVING'})
        with patch.object(pause,'participants',return_value=self.owners),patch.object(pause,'identity',return_value=self.worker),patch.object(pause,'alive',return_value=True),patch.object(pair_auto,'read_state',return_value={'phase':'RUNNING'}),patch.object(pair_auto,'intent',return_value={'mode':'on'}),patch.object(pause.time,'monotonic',side_effect=lambda:clock[0]),patch.object(pause.time,'sleep',side_effect=lambda dt:clock.__setitem__(0,clock[0]+dt)):
            with self.assertRaisesRegex(pause.PauseError,'SPEED-PAUSE-TIMEOUT'):
                pause.acquire({'tx':self.tx,'monotonic_deadline':200})
            pause.release(self.tx);self.assertEqual(pause.load()['phase'],'RESUMING')

    def test_cpu_is_current_accounting_not_minute_load_average(self):
        with patch.object(pause,'cpu_snapshot',side_effect=[[0,0,0,100,0,0,0,0],[80,0,0,120,0,0,0,0]]),patch.object(pause.time,'sleep'),patch.object(os,'getloadavg',side_effect=AssertionError('not a CPU percentage')):
            self.assertEqual(pause.cpu_usage(),80)
        with patch.object(pause,'cpu_snapshot',side_effect=[[0,0,0,100,0,0,0,0],[0,0,0,100,0,0,0,0]]),patch.object(pause.time,'sleep'):
            with self.assertRaisesRegex(pause.PauseError,'SPEED-CPU-UNKNOWN'):pause.cpu_usage()

    def test_worker_finally_withdraws_pause_on_success_failure_cpu_refusal_and_cancel(self):
        for mode in('success','failure','busy','cancel','pause-failure'):
            with self.subTest(mode=mode):
                events=[];job={'tx':self.tx,'state':'QUEUED','profiles':['a'],'monotonic_deadline':time.monotonic()+60,'budget_mib':1,'duration':2,'streams':1}
                agent.atomic_json(speed.JOB,job)
                if speed.CANCEL.exists():speed.CANCEL.unlink()
                def acquire(job):
                    events.append('pause')
                    if mode=='pause-failure':raise pause.PauseError('SPEED-PAUSE-TIMEOUT')
                def measure(*args):
                    self.assertEqual(events,['pause','cpu']);events.append('measure')
                    if mode=='failure':raise speed.SpeedError('SPEED-NETWORK')
                    if mode=='cancel':agent.atomic_json(speed.CANCEL,{'tx':self.tx})
                    return {'id':'a','time':time.time(),'code':None}
                def cpu():events.append('cpu');return 90 if mode=='busy'else 2
                with patch.object(native_switch,'configure_timezone'),patch.object(pause,'acquire',side_effect=acquire),patch.object(pause,'cpu_usage',side_effect=cpu),patch.object(pause,'interrupted',return_value=False),patch.object(pause,'release',side_effect=lambda tx:events.append('release')),patch.object(speed,'inventory',return_value={'profiles':[{'id':'a','name':'A','protocol':'wireguard'}]}),patch.object(speed,'measure',side_effect=measure)as transfer,patch.object(speed,'append_history'):
                    speed.run(self.tx)
                self.assertEqual(events[-1],'release');result=agent.read_json(speed.JOB)
                self.assertEqual(result['state'],'DONE'if mode=='success'else'CANCELLED'if mode=='cancel'else'FAILED')
                if mode in('busy','pause-failure'):transfer.assert_not_called()


if __name__=='__main__':unittest.main()
