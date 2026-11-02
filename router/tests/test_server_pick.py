"""server_pick.py: the best server inside a channel (2.1.0). The cases are shared with tests/lua/test_server_pick.lua
(server_pick_cases.json): Python and Lua read, rank, order, plan and publish the same."""
import json
from pathlib import Path
import socket
import sys
import threading
import unittest

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import server_pick as S  # noqa: E402

CASES=json.loads((HERE/'server_pick_cases.json').read_text(encoding='utf-8'))


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


class World:
    def __init__(self,case):
        self.case=case;self.files=dict(case['files']);self.writes={};self.exec=[];self.logs=[]
        c=case
        def write(path,text):
            if path in c.get('write_fail',[]):return False
            self.files[path]=text;self.writes[path]=text;return True
        def run(argv,seconds):
            self.exec.append(list(argv))
            if argv[:4]==['uci','-q','-X','show']:
                text=c['uci'].get(argv[4]);return (0,text) if text is not None else (1,'')
            if argv[0]=='ping':
                text=c['ping'].get(argv[-1]);return (0 if text and 'round-trip' in text else 1,text or '')
            return c.get('rc',{}).get(' '.join(argv),0),''
        def tcp(host,port,timeout,device):
            self.exec.append(['tcp',host,str(port),device or ''])
            return c['tcp'].get('%s:%d'%(host,port))
        self.io={'runtime':'/run','read':self.files.get,'write':write,'exec':run,'tcp':tcp,'alive':lambda pid:pid in c.get('alive',[]),
                 'wan':lambda:c.get('wan'),'active_mark':lambda:c.get('active_mark'),'log':self.logs.append}


class SharedCases(unittest.TestCase):
    def test_parsers(self):
        for c in CASES['uci_values']:self.assertEqual(S.uci_values(c['raw']),c['expect'],c['raw'])
        for c in CASES['parse_profiles']:self.assertEqual(S.parse_profiles(c['text']),c['expect'])
        for c in CASES['tunnels']:self.assertEqual(S.tunnels(S.parse_uci(c['uci'])),c['expect'])
        for c in CASES['candidates']:self.assertEqual(S.candidates(c['tunnel'],c['profiles'],S.parse_uci(c['uci'])),c['expect'])
        for c in CASES['parse_ping']:self.assertEqual(S.parse_ping(c['text']),c['expect'])
        for c in CASES['endpoints']:self.assertEqual(S.endpoints(c['protocol'],c['section']),c['expect'],c['section'])
        for c in CASES['pick_uplink']:self.assertEqual(S.pick_uplink(c['rows']),c['expect'])

    def test_rank_decide_order(self):
        for c in CASES['rank_decide']:
            ranked=S.rank(c['rows'])
            self.assertEqual([r['profile'] for r in ranked],c['expect_rank'])
            self.assertEqual((S.decide(ranked) or {}).get('profile'),c['expect_target'])
        for c in CASES['plan_order']:self.assertEqual(S.plan_profiles_order(c['text'],c['current'],c['ranked']),c['expect'])

    def test_switch_plan_and_gate(self):
        for c in CASES['switch_plan']:
            self.assertEqual(S.switch_plan(c['tunnel'],c['target'],c['enabled'],c['auto_on'],c['carrying'],c['busy'],c['left']),c['expect'])
        ran=[]
        io={'exec':lambda argv,seconds:(ran.append(argv),(0,''))[1]}
        plan=S.switch_plan({'section':'cfg1','protocol':'wireguard','interface':'wgclient1'},{'group_id':'1','profile_id':'2'},True,True,False,False,4)
        self.assertEqual(S.execute(plan,io,False),S.OFF);self.assertEqual(S.execute(plan,io,'1'),S.OFF);self.assertEqual(ran,[])
        self.assertEqual(S.execute(plan,io,True),S.PICKED);self.assertEqual(len(ran),10,'WireGuard: update_provider_config as in tunnel-switch.sh')
        self.assertEqual(ran[7],['sh','-c',S.PROVIDER_SCRIPT,'update_provider_config','1','2','wgclient1'])
        io['exec']=lambda argv,seconds:(1 if '-q' in argv else 0,'')
        self.assertEqual(S.execute(plan,io,True),S.PICKED,'an absent option to delete is not a failure')
        def boom(argv,seconds):raise OSError('boom')
        io['exec']=boom;self.assertEqual(S.execute(plan,io,True),S.FAILED)

    def test_monitor_side(self):
        for c in CASES['due']:self.assertEqual(S.due(c['last'],c['previous'],c['failed'],c['clock']),c['expect'])
        for c in CASES['carrying_retry']:self.assertEqual(S.carrying_retry(c['picked'],c['previous'],c['retried'],c['last'],c['clock']),c['expect'])
        for c in CASES['failed_interfaces']:self.assertEqual(S.failed_interfaces(c['profiles']),c['expect'])
        for c in CASES['project']:self.assertEqual(canonical(S.project(c['value'])),canonical(c['expect']))
        for c in CASES['events']:self.assertEqual(S.events(c['result'],c['seen']),c['expect'])

    def test_jobs(self):
        for c in CASES['job']:
            with self.subTest(c['name']):
                w=World(c);result=S.job(w.io,c['request'],c['now'])
                self.assertEqual(canonical(result),canonical(c['expect']['result']))
                self.assertEqual(w.writes,c['expect']['writes']);self.assertEqual(w.exec,c['expect']['exec']);self.assertEqual(w.logs,c['expect']['logs'])
                self.assertEqual(canonical(S.project(json.loads(w.files['/run/server-pick.json']))),canonical(result))

    def test_off_never_measures_writes_or_switches(self):
        for c in CASES['job']:
            if c['request'].get('enabled') is not True:
                self.assertEqual([a for a in c['expect']['exec'] if a[:4]!=['uci','-q','-X','show']],[])
                self.assertEqual(list(c['expect']['writes']),['/run/server-pick.json'])

    def test_stage2_hand_off_gate_and_rebind(self):
        for c in CASES['request_valid']:self.assertEqual(S.request_valid(c['row'],c['now']),c['expect'],c['name'])
        for c in CASES['claim']:
            ran=[]
            io={'exec':lambda argv,seconds,c=c:(ran.append(argv),(c['rc'],c['uci']))[1]}
            self.assertEqual(S.claim(io,c['row'],100100),c['expect'],c['name']);self.assertEqual(ran,c['exec'],c['name'])
        for c in CASES['gate']:self.assertEqual(S.gate(c['ctx']),c['expect'],c['name'])
        for c in CASES['rebind']:
            with self.subTest(c['name']):
                if 'error' in c['expect']:
                    with self.assertRaises(ValueError) as caught:S.rebind(c['state'],c['journal'],c['order'],c['hash'],c['target_id'],c.get('role','target'))
                    self.assertEqual(str(caught.exception),c['expect']['error'])
                else:
                    state,journal=S.rebind(c['state'],c['journal'],c['order'],c['hash'],c['target_id'],c.get('role','target'))
                    self.assertEqual(canonical(state),canonical(c['expect']['state']));self.assertEqual(canonical(journal),canonical(c['expect']['journal']))
        self.assertEqual(S.profile_id('openvpn','40354','2016'),'openvpn:40354_2016');self.assertEqual(S.profile_id('wireguard','10004','2000'),'wireguard:peer_2000')
        self.assertIsNone(S.profile_id('openvpn','x','1'))

    def test_stage2_job_never_executes_a_switch(self):
        for c in CASES['job']:
            for argv in c['expect']['exec']:self.assertNotIn(argv[0],('ifdown','ifup'),c['name']);self.assertNotEqual(argv[:2],['uci','set'],c['name'])
            self.assertNotIn('/run/'+S.STATE,c['expect']['writes'],c['name'])

    def test_stage2_record_and_event_once(self):
        files={};logs=[]
        io={'runtime':'/run','read':files.get,'write':lambda path,text:files.__setitem__(path,text) is None,'log':logs.append}
        self.assertTrue(S.record(io,4192,1000));self.assertTrue(S.record(io,4192,1100,{'time':1100,'from':'1_1','to':'1_2'},count=False))
        state=json.loads(files['/run/'+S.STATE])
        self.assertEqual(state['changes'],{'4192':[1000]});self.assertEqual(state['last']['4192']['to'],'1_2')
        tunnel={'tunnel_id':4192,'protocol':'openvpn'}
        self.assertTrue(S.event(io,S.LIMIT,tunnel,1200,request=999));self.assertFalse(S.event(io,S.LIMIT,tunnel,1210,request=999),'the same refusal once')
        self.assertTrue(S.event(io,S.FAILED,tunnel,1220,{'from':'1_1','to':'1_2','from_ms':48,'to_ms':None},999,'rolled back'))
        self.assertEqual(S.events(json.loads(files['/run/'+S.EVENT]),1210),[{'time':1220,'code':S.FAILED,'tunnel_id':4192}])
        self.assertEqual(logs[-1],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 4192 openvpn): 1_1 -> 1_2, 48 -> ? ms; rolled back')
        self.assertEqual(len(logs),2)

    def test_lua_and_python_constants_match(self):
        lua=(LIB/'lua/server_pick.lua').read_text(encoding='utf-8')
        for code,text in S.TEXT.items():self.assertIn("]='%s'"%text,lua,code)
        for name in ('MEASURE_EVERY','CHANGES','WINDOW','TCP_ATTEMPTS','PING_SECONDS','EXEC_SECONDS','MAX_TUNNELS','MAX_CANDIDATES','MAX_MEASURED','MAX_ENDPOINTS',
                     'REQUEST_AGE','CONNECT_WAIT','SETTLE_WAIT'):
            self.assertIn('M.%s=%s'%(name,getattr(S,name)),lua,name)
        self.assertIn("M.PING={%s}"%','.join("'%s'"%a for a in S.PING),lua)


class RouterIo(unittest.TestCase):
    def test_tcp_connect_time_and_refusal(self):
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
        port=server.getsockname()[1]
        accepted=threading.Thread(target=lambda:server.accept()[0].close(),daemon=True);accepted.start()
        io=S.router_io('/nonexistent')
        try:
            ms=io['tcp']('127.0.0.1',port,1.5,None)
            self.assertIsNotNone(ms);self.assertLess(ms,1500)
        finally:accepted.join(2);server.close()  # the accept thread must let go of the socket first (CI 02.11.2026)
        self.assertIsNone(io['tcp']('127.0.0.1',port,0.5,None))


if __name__=='__main__':
    unittest.main()
