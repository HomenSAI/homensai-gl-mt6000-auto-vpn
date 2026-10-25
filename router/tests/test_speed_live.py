from pathlib import Path
import sys,tempfile,time,threading,socket,http.server,json,unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import speed_test as speed
from agent import atomic_json,read_json

class LiveTests(unittest.TestCase):
    def test_real_local_http_bytes_emit_both_directions_without_network_or_quota_writes(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                amount=262144;self.send_response(200);self.send_header('Content-Length',str(amount));self.end_headers()
                for _ in range(amount//8192):self.wfile.write(b'x'*8192);self.wfile.flush();time.sleep(.02)
            def do_POST(self):
                remaining=int(self.headers['Content-Length'])
                while remaining:part=self.rfile.read(min(8192,remaining));remaining-=len(part);time.sleep(.02)
                self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'OK')
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def connect(*_):
            sock=socket.create_connection(server.server_address,timeout=3);sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096);return sock
        try:
            with patch.object(speed,'connect',side_effect=connect),patch.object(speed,'reserve_quota') as quota:
                for direction in ['download','upload']:
                    points=[];result=speed.stage({},'unused',direction,262144,3,1,lambda:False,progress=lambda *point:points.append(point))
                    self.assertEqual(result['payload_bytes'],262144);self.assertTrue(points);self.assertEqual(points[-1][1],262144)
                    self.assertTrue(all(p[0]>0 and p[2]>0 for p in points));self.assertEqual(sorted(p[1] for p in points),[p[1] for p in points])
                quota.assert_not_called()
        finally:server.shutdown();server.server_close();thread.join(3)

    def test_parallel_payload_progress_counts_actual_bytes_once(self):
        points=[]
        def transport(binding,address,direction,amount,deadline,cancelled,progress):
            for _ in range(8):progress(amount//8)
            return amount
        result=speed.stage({},'unused','download',speed.MIB*4,3,4,lambda:False,transport,lambda *p:points.append(p))
        self.assertEqual(points[-1][1],result['payload_bytes']);self.assertEqual(result['payload_bytes'],4*speed.MIB)

    def test_job_generation_bound_progress_and_bounded_safe_public_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'job';job={'tx':'a'*32,'profiles':['wireguard:peer_1','openvpn:1_2'],'state':'RUNNING','pid':123}
            with patch.object(speed,'JOB',path),patch.object(speed,'control_lock'),patch.object(speed,'worker_alive',return_value=True):
                atomic_json(path,job);live=speed.LiveProgress(job);live.phase('wireguard:peer_1','download')
                for n in range(150):live.sample('wireguard:peer_1','download',n+1,n*8192)
                live.finish('wireguard:peer_1');live.phase('openvpn:1_2','upload');live.sample('openvpn:1_2','upload',20,8192)
                public=speed.public_live();self.assertEqual(public['run_id'],'a'*32);self.assertEqual(len(public['profiles'][0]['samples']),128)
                self.assertIsNone(public['profiles'][1]['samples'][0][1]);self.assertEqual(public['profiles'][1]['samples'][0][2],20)
                self.assertNotIn('pid',public);self.assertNotIn('quota',public)
                newer=dict(job,tx='b'*32);atomic_json(path,newer);live.sample('openvpn:1_2','upload',21,16384);self.assertEqual(read_json(path)['tx'],'b'*32)
                with patch.object(speed,'load_history',side_effect=AssertionError('must not read flash history')),patch.object(speed,'inventory',side_effect=AssertionError('must not probe')):speed.public_live()

    def test_bad_payload_and_missing_worker_are_not_live_success_or_zeros(self):
        job={'tx':'a'*32,'state':'RUNNING','profiles':['wireguard:peer_1'],'live':[{'id':'wireguard:peer_1','phase':'download','samples':[[1,20,None],[2,None,None],[3,float('nan'),None],[4,True,None],[5,1,2]],'download_mbps':'10'}]}
        with patch.object(speed,'worker_alive',return_value=False):public=speed.public_live(job)
        self.assertEqual(public['state'],'FAILED');self.assertEqual(public['code'],'SPEED-WORKER-LOST');self.assertEqual(public['profiles'][0]['samples'],[[1,20,None]]);self.assertNotIn('download_mbps',public['profiles'][0])
        for bad in [None,{},dict(job,profiles=[[]]),dict(job,tx='wrong')]:
            with patch.object(speed,'read_json',return_value=bad):self.assertEqual(speed.public_live()['state'],'IDLE')

if __name__=='__main__':unittest.main()
