from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import time
import subprocess
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import speed_test as speed
import auto_control
from agent import atomic_json, read_json


class SpeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        for module,name,value in [(speed,'RUNTIME',self.path),(speed,'PERSIST',self.path),(auto_control,'RUNTIME',self.path),
                (speed,'JOB',self.path/'job'),(speed,'CANCEL',self.path/'cancel'),(speed,'HISTORY',self.path/'history'),(speed,'LEDGER',self.path/'quota')]:
            item=patch.object(module,name,value);item.start();self.addCleanup(item.stop)

    def test_parallel_reservations_never_exceed_payload_budget(self):
        budget=speed.Budget(100003)
        def take():return sum(budget.take(4096) for _ in range(100))
        with ThreadPoolExecutor(max_workers=8) as pool:
            total=sum(pool.map(lambda _:take(),range(8)))
        self.assertEqual(total,100003);self.assertEqual(budget.remaining,0)

    def test_parallel_stage_accounts_actual_payload_once(self):
        amounts=[]
        def transfer(binding,address,direction,amount,deadline,cancelled):amounts.append(amount);return amount
        value=speed.stage({},'9.9.9.9','download',2500000,2,4,lambda:False,transfer)
        self.assertEqual(value['payload_bytes'],2500000)
        self.assertEqual(sum(amounts),2500000)
        self.assertGreater(value['mbps'],0)

    def test_cancelled_stage_never_opens_transport(self):
        transport=MagicMock()
        with self.assertRaises(speed.SpeedError):speed.stage({},'9.9.9.9','download',1000,2,2,lambda:True,transport)
        transport.assert_not_called()

    def test_invalid_and_oversized_requests_rejected(self):
        good={'profiles':['a'],'budget_mib':8,'duration':5,'streams':2}
        self.assertEqual(speed.validate_request(good,[{'id':'a'}]),good)
        for update in ({'profiles':['a','a']},{'profiles':['unknown']},{'streams':5},{'budget_mib':True},{'duration':16}):
            args=dict(good,**update)
            with self.assertRaises(speed.SpeedError):speed.validate_request(args,[{'id':'a'}])

    def test_failed_attempt_reservation_is_not_refunded(self):
        now=time.time();speed.reserve_quota(8,10,now)
        with self.assertRaises(speed.SpeedError):speed.reserve_quota(3,10,now)
        self.assertEqual(next(iter(read_json(speed.LEDGER)['data'].values())),8)

    def test_corrupt_quota_blocks_instead_of_resetting(self):
        atomic_json(speed.LEDGER,{'data':{'bad':'value'},'sha256':'wrong'})
        with self.assertRaises(speed.SpeedError):speed.reserve_quota(1,10,time.time())

    def test_history_checksum_backup_and_retention(self):
        now=time.time();speed.append_history([{'time':now,'id':'a','code':None}])
        speed.append_history([{'time':now+1,'id':'b','code':'SPEED-NETWORK'}])
        speed.HISTORY.write_text('corrupt')
        recovered=speed.load_history()
        self.assertEqual(recovered['results'][0]['id'],'a')

    def test_route_mismatch_refuses_before_socket_creation(self):
        binding={'device':'tun0','mark':1,'table':'100'}
        with patch.object(speed,'command',return_value=b'[{"dev":"eth0","table":100}]'),patch.object(speed,'bound_socket') as socket:
            with self.assertRaises(speed.SpeedError):speed.connect(binding,'9.9.9.9','example.com',time.monotonic()+3)
            socket.assert_not_called()

    def test_private_endpoint_address_is_rejected(self):
        with patch.object(speed,'command') as command:
            with self.assertRaises(speed.SpeedError):speed.verify_route({'device':'tun0','mark':1,'table':'100'},'192.168.1.1')
            command.assert_not_called()

    def test_timeout_never_signals_unrelated_pid(self):
        atomic_json(speed.JOB,{'state':'RUNNING','tx':'a'*32,'pid':12345,'monotonic_deadline':0})
        with patch.object(speed,'worker_alive',return_value=False),patch.object(speed.os,'kill') as kill:
            speed.expire_worker();kill.assert_not_called()

    def test_proven_worker_timeout_cannot_be_overwritten_by_late_success(self):
        job={'state':'RUNNING','tx':'a'*32,'pid':12345,'monotonic_deadline':0}
        atomic_json(speed.JOB,job)
        with patch.object(speed,'worker_alive',return_value=True),patch.object(speed.os,'kill') as kill:
            speed.expire_worker();kill.assert_called_once_with(12345,speed.signal.SIGTERM)
        self.assertFalse(speed.publish_job(dict(job,state='DONE')))
        self.assertEqual(read_json(speed.JOB)['code'],'SPEED-WORKER-TIMEOUT')

    def test_disabled_feature_never_starts_a_worker(self):
        with patch.object(speed,'inventory',return_value={'profiles':[],'settings':{}}),patch.object(speed.subprocess,'Popen') as worker:
            self.assertEqual(speed.start({})['code'],'SPEED-DISABLED');worker.assert_not_called()

    def test_admitted_job_reserves_quota_and_records_only_owned_worker(self):
        data={'profiles':[{'id':'a'}],'settings':{'speed_enabled':True}}
        atomic_json(self.path/'speed-traffic.json',{'monotonic':time.monotonic(),'rate_bps':0})
        with patch.object(speed,'inventory',return_value=data),patch.object(speed.os,'getloadavg',return_value=(0,0,0)),patch.object(speed.subprocess,'Popen',return_value=type('Child',(),{'pid':12345})()) as worker:
            result=speed.start({'profiles':['a'],'budget_mib':8,'duration':5,'streams':2})
            self.assertTrue(result['accepted']);worker.assert_called_once()
        job=read_json(speed.JOB)
        self.assertEqual(job['pid'],12345);self.assertEqual(job['quota_reserved_bytes'],8*speed.MIB)
        self.assertEqual(job['state'],'QUEUED')

    def test_real_isolated_owned_process_timeout(self):
        # This child only sleeps; it performs no network or router operation.
        script=self.path/'speed_test.py';script.write_text('import time\ntime.sleep(20)\n')
        tx='c'*32
        process=subprocess.Popen([sys.executable,str(script),'run',tx],start_new_session=True)
        try:
            atomic_json(speed.JOB,{'state':'RUNNING','tx':tx,'pid':process.pid,'monotonic_deadline':0})
            with patch.object(speed,'__file__',str(script)):
                limit=time.monotonic()+2
                while not speed.worker_alive(read_json(speed.JOB)) and time.monotonic()<limit:time.sleep(.01)
                self.assertTrue(speed.worker_alive(read_json(speed.JOB)))
                speed.expire_worker()
            process.wait(timeout=3)
            self.assertEqual(read_json(speed.JOB)['code'],'SPEED-WORKER-TIMEOUT')
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=3)

    def test_busy_network_does_not_reserve_quota_or_spawn(self):
        data={'profiles':[{'id':'a'}],'settings':{'speed_enabled':True}}
        atomic_json(self.path/'speed-traffic.json',{'monotonic':time.monotonic(),'rate_bps':3e6})
        with patch.object(speed,'inventory',return_value=data),patch.object(speed.os,'getloadavg',return_value=(0,0,0)),patch.object(speed.subprocess,'Popen') as worker:
            result=speed.start({'profiles':['a'],'budget_mib':8,'duration':5,'streams':2})
            self.assertEqual(result['code'],'SPEED-TRAFFIC-BUSY');worker.assert_not_called()
            self.assertFalse(speed.LEDGER.exists())


if __name__=='__main__':unittest.main()
