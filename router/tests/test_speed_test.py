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

    def test_elapsed_window_retains_only_completed_payload_instead_of_cancel_error(self):
        clock=[100.0];calls=[]
        def transfer(binding,address,direction,amount,deadline,cancelled):
            calls.append(amount)
            if len(calls)==1:clock[0]=101;return amount
            clock[0]=103;raise speed.SpeedError('SPEED-CANCELLED')
        with patch.object(speed.time,'monotonic',side_effect=lambda:clock[0]):
            row=speed.stage({},'9.9.9.9','download',2*speed.MIB,2,1,lambda:False,transfer)
        self.assertEqual(row['payload_bytes'],speed.MIB);self.assertEqual(row['seconds'],3)

    def fake_network(self,clock,requests,timeouts,cancel_at=None,cancelled=None):
        """Real request()/stage(); only the socket, the HTTP response and the monotonic clock are fakes. Each request
        is a list of (payload bytes, time the bytes arrive / the send completes); a step that would finish after the
        socket timeout raises socket.timeout exactly when that timeout ends (the clock moves to it)."""
        import socket
        plans=iter(requests)
        def step(sock,want):
            if not sock.plan:return b''
            size,at=sock.plan[0]
            limit=None if sock.timeout is None else clock[0]+sock.timeout
            if limit is not None and at>limit:clock[0]=limit;raise socket.timeout('timed out')
            sock.plan.pop(0);clock[0]=max(clock[0],at)
            if cancel_at is not None and clock[0]>=cancel_at:cancelled[0]=True
            return b'x'*min(size,want)
        class Sock:
            def __init__(self):self.plan=list(next(plans));self.timeout=None
            def settimeout(self,value):timeouts.append((clock[0],value));self.timeout=value
            def sendall(self,data):
                if not data.startswith((b'GET ',b'POST ')):step(self,len(data))
            def __enter__(self):return self
            def __exit__(self,*args):return False
        class Response:
            def __init__(self,sock):self.sock=sock;self.status=200
            def begin(self):pass
            def read1(self,amount):return step(self.sock,amount)
            def read(self,amount):return step(self.sock,amount) if self.sock.plan else b''
        return ExitStack(),Sock,Response

    def run_stage(self,direction,budget,duration,requests,cancel_at=None):
        clock=[0.0];timeouts=[];cancelled=[False];live=[]
        stack,Sock,Response=self.fake_network(clock,requests,timeouts,cancel_at,cancelled)
        with stack:
            stack.enter_context(patch.object(speed.time,'monotonic',side_effect=lambda:clock[0]))
            stack.enter_context(patch.object(speed,'connect',side_effect=lambda *args:Sock()))
            stack.enter_context(patch.object(speed.http.client,'HTTPResponse',Response))
            row=speed.stage({},'9.9.9.9',direction,budget,duration,1,lambda:cancelled[0],
                            progress=lambda mbps,total,elapsed:live.append(total))
        return row,timeouts,live

    def test_partial_payload_at_window_expiry_is_counted_once(self):
        # review F-49 oracle: 1 MiB completed + half of the next MiB inside a 3 s window. Payload moved inside the window
        # is 1,572,864 bytes; Mbps = 8 * 1,572,864 / (1e6 * 3) = 4.194304 -> 4.194. (Counting completed requests only
        # gave 1,048,576 bytes = 2.796 Mbps over the same 3 s, and the live progress already showed the 1.5 MiB.)
        first=[(65536,0.1*(i+1)) for i in range(16)]
        second=[(65536,1.7+0.1*i) for i in range(8)]+[(65536,3.5)]
        row,timeouts,live=self.run_stage('download',2*speed.MIB,3,[first,second])
        self.assertEqual(row,{'payload_bytes':1572864,'seconds':3.0,'mbps':4.194})
        self.assertEqual(live[-1],1572864,'live and final totals are the same bytes, counted once')

    def test_blocking_read_cannot_cross_the_deadline(self):
        # review F-50: a read that would block until 4.875 s must end at the 2 s deadline; the stage is 2 s, not 4.875 s
        # (old result: 1,048,576 bytes over 4.875 s = 1.721 Mbps). The time is not capped afterwards either.
        first=[(65536,0.05*(i+1)) for i in range(16)]
        row,timeouts,live=self.run_stage('download',2*speed.MIB,2,[first,[(65536,4.875)]])
        self.assertEqual(row,{'payload_bytes':speed.MIB,'seconds':2.0,'mbps':4.194})
        self.assertTrue(timeouts,'every blocking step sets a timeout')
        self.assertTrue(all(0<value<=2-now+1e-9 for now,value in timeouts),timeouts)

    def test_partial_upload_counts_completed_sends_inside_the_window(self):
        blocks=[(65536,0.2*(i+1)) for i in range(4)]+[(65536,1.5)]
        row,timeouts,live=self.run_stage('upload',speed.MIB,1,[blocks])
        self.assertEqual(row,{'payload_bytes':262144,'seconds':1.0,'mbps':2.097})

    def test_real_cancellation_inside_a_partial_request_is_not_a_window_expiry(self):
        first=[(65536,0.1*(i+1)) for i in range(16)]
        second=[(65536,1.7+0.1*i) for i in range(8)]
        with self.assertRaisesRegex(speed.SpeedError,'SPEED-CANCELLED'):
            self.run_stage('download',2*speed.MIB,3,[first,second],cancel_at=2.0)

    def test_real_cancel_after_completed_payload_still_cancels_the_measurement(self):
        cancelled=[False]
        def transfer(*args):cancelled[0]=True;return args[3]
        with self.assertRaisesRegex(speed.SpeedError,'SPEED-CANCELLED'):
            speed.stage({},'9.9.9.9','download',2*speed.MIB,2,1,lambda:cancelled[0],transfer)

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
        with patch.object(speed,'inventory',return_value=data),patch.object(speed.os,'getloadavg',side_effect=AssertionError('CPU admission must happen after the quiet window')),patch.object(speed.subprocess,'Popen',return_value=type('Child',(),{'pid':12345})()) as worker:
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
        with patch.object(speed,'inventory',return_value=data),patch.object(speed.os,'getloadavg',side_effect=AssertionError('CPU admission must happen after the quiet window')),patch.object(speed.subprocess,'Popen') as worker:
            result=speed.start({'profiles':['a'],'budget_mib':8,'duration':5,'streams':2})
            self.assertEqual(result['code'],'SPEED-TRAFFIC-BUSY');worker.assert_not_called()
            self.assertFalse(speed.LEDGER.exists())


if __name__=='__main__':unittest.main()
