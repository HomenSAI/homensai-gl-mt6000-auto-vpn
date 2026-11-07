"""Per-target probe log (docs/architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md): what each probe target answered in
every pass, in a RAM ring, for the offline sensor-correlation study.

Shared cases: probe_target_log_cases.json (gen_probe_target_log_cases.py); the Lua twin replays them in
tests/lua/test_probe_target_log.lua (run here too when lua5.1 exists). The hand-written assertions state the meaning.
"""
from contextlib import ExitStack
import contextlib
import copy
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROUTER=HERE.parent
LIB=ROUTER/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB));sys.path.insert(0,str(HERE))
import agent  # noqa: E402
import gen_probe_target_log_cases  # noqa: E402
import probe_target_log as P  # noqa: E402

CASES=json.loads((HERE/'probe_target_log_cases.json').read_text(encoding='ascii'))
LUA=shutil.which('lua5.1')
T0=1762243200


def check(target,result='ok',ms=10.0,**extra):
    return dict({'target':target,'result':result,'elapsed_ms':ms},**extra)


def row(**extra):
    return dict({'id':'wireguard:peer_7','time':T0+0.5,'code':None,'dns_ok':True,
                 'probe_checks':[check('one.one.one.one',ms=143.5),check('dns.google',ms=61.2),check('dns.quad9.net',ms=88.0)]},**extra)


class SharedCases(unittest.TestCase):
    @unittest.skipIf(os.environ.get('PROBE_TARGET_LOG_MUTATION')=='1','mutation run: only the semantic tests may kill a mutant')
    def test_the_case_file_is_current(self):
        self.assertEqual((HERE/'probe_target_log_cases.json').read_text(encoding='ascii'),gen_probe_target_log_cases.text(),
                         'run python router/tests/gen_probe_target_log_cases.py')

    def test_enough_cases_of_every_kind(self):
        self.assertGreaterEqual(len(CASES['encode']),300);self.assertGreaterEqual(len(CASES['parse']),40)
        self.assertGreaterEqual(len(CASES['select']),80);self.assertGreaterEqual(len(CASES['arguments']),25)
        self.assertGreaterEqual(len(CASES['ring']),6)

    def test_encode_and_parse_replay(self):
        for case in CASES['encode']:
            self.assertEqual(P.encode(case['seq'],case['result'],case['dense'],case['hb'],case['now']),case['expected'],case['name'])
        for case in CASES['parse']:self.assertEqual(P.parse_line(case['line']),case['expected'],case['line'])

    def test_every_encoded_line_parses_back_to_the_same_numbers(self):
        for case in CASES['encode']:
            if case['expected'] is None:continue
            parsed=P.parse_line(case['expected'].rstrip('\n'))
            self.assertIsNotNone(parsed,case['name'])
            self.assertEqual(json.loads(case['expected']),parsed,case['name'])

    def test_select_and_arguments_replay(self):
        for case in CASES['select']:
            self.assertEqual(P.select(case['old'],case['new'],case['after'],case['limit']),case['expected'],case['name'])
        for case in CASES['arguments']:
            if isinstance(case['expected'],str):
                with self.assertRaises(ValueError,msg=str(case['request'])) as caught:P.arguments(case['request'])
                self.assertEqual(str(caught.exception),case['expected'])
            else:self.assertEqual(list(P.arguments(case['request'])),case['expected'],str(case['request']))

    def test_ring_scenarios_replay_through_real_files(self):
        for scenario in CASES['ring']:
            with tempfile.TemporaryDirectory() as directory:
                current=Path(directory)/P.NAME;previous=Path(directory)/(P.NAME+'.1')
                for key,path in (('current',current),('previous',previous)):
                    if scenario['initial'][key] is not None:path.write_bytes(scenario['initial'][key].encode('ascii'))
                writer=P.Writer(directory,scenario['segment'])
                for index,batch in enumerate(scenario['batches']):
                    state=scenario['states'][index]
                    self.assertEqual(writer.record(batch['results'],batch['hb'],batch['dense'],batch['now']),state['written'],scenario['name'])
                    self.assertEqual(current.read_bytes().decode('ascii') if current.exists() else None,state['current'],scenario['name'])
                    self.assertEqual(previous.read_bytes().decode('ascii') if previous.exists() else None,state['previous'],scenario['name'])


class Meaning(unittest.TestCase):
    """The important cases, stated by hand (a wrong generator cannot make these pass)."""
    def line(self,**extra):
        return P.encode(1,row(**extra))

    def test_a_healthy_channel_line(self):
        self.assertEqual(self.line(),'[1,%d,"wireguard:peer_7",0,0,[0,144,0,61,0,88],0,[]]\n'%T0)

    def test_the_result_codes_of_the_targets(self):
        for text,code in (('ok',0),('timeout',1),('tls-error',2),('invalid-response',3),('transport-error',4),('http-error',5),
                          ('http-unsupported',6),('unknown',7),('never-seen',7)):
            line=self.line(probe_checks=[check('dns.google',text,100.0)])
            self.assertEqual(json.loads(line)[5],[9,-1,code,100,9,-1],text)

    def test_an_inauthentic_answer_adds_ten(self):
        for reason in ('untrusted-certificate','portal-redirect','stale-response'):
            line=self.line(probe_checks=[check('one.one.one.one','tls-error',5.0,trust=reason)])
            self.assertEqual(json.loads(line)[5][:2],[12,5],reason)
        self.assertEqual(json.loads(self.line(probe_checks=[check('one.one.one.one','ok',5.0,trust='x')]))[5][:2],[0,5])

    def test_verdicts_and_dns(self):
        for code,number in ((None,0),('DNS-001',1),('VPN-003',2),('VPN-001',3),('VPN-MTU',4),('ROUTE-001',5),('CHECK-001',6),
                            ('SYSTEM-001',7),('VENDOR-IDENTITY-CHANGED',8),('PROFILE-INACTIVE',9)):
            self.assertEqual(json.loads(self.line(code=code))[3],number,str(code))
        self.assertEqual([json.loads(self.line(dns_ok=v))[6] for v in (True,False,None)],[0,1,9])

    def test_a_tunnel_that_was_not_probed_has_no_target_data(self):
        line=P.encode(3,{'id':'wireguard:peer_8','time':T0,'code':'VPN-001'})
        self.assertEqual(json.loads(line)[3:],[3,0,[9,-1,9,-1,9,-1],9,[]])

    def test_latency_rounds_half_up_and_clamps(self):
        got=json.loads(self.line(probe_checks=[check('one.one.one.one','ok',142.5),check('dns.google','ok',0.49),check('dns.quad9.net','ok',999999.0)]))[5]
        self.assertEqual(got,[0,143,0,0,0,600000])
        self.assertEqual(json.loads(self.line(probe_checks=[check('one.one.one.one','ok',-4.0)]))[5][:2],[0,0])
        self.assertEqual(json.loads(self.line(probe_checks=[check('one.one.one.one','timeout',None)]))[5][:2],[1,-1])

    def test_heartbeat_counters(self):
        self.assertEqual(json.loads(P.encode(1,row(),False,[10,0,10,1,0,0,0,0]))[7],[10,0,10,1,0,0,0,0])
        self.assertEqual(json.loads(P.encode(1,row(),False,[0,0,0,0,0,0,0,0]))[7],[],'no echo judged: no data')
        self.assertEqual(json.loads(P.encode(1,row(),False,[1,0,1]))[7],[])
        self.assertEqual(P.heartbeat_slot('1.1.1.1'),0);self.assertEqual(P.heartbeat_slot('9.9.9.9'),2);self.assertEqual(P.heartbeat_slot('8.8.4.4'),3)

    def test_dense_flag_and_time(self):
        self.assertEqual(json.loads(P.encode(1,row(),True))[4],1)
        self.assertEqual(json.loads(P.encode(1,row(time=T0+0.999)))[1],T0,'whole seconds cut')

    def test_no_line_for_what_is_no_channel_row(self):
        for bad in ('x',None,{},{'id':'a b','time':1},{'id':'a','time':-1},{'id':'a'*65,'time':1}):
            self.assertIsNone(P.encode(1,bad),str(bad))

    def test_the_line_stays_small(self):
        longest=P.encode(10**14,row(probe_checks=[check('one.one.one.one','timeout',600000.0,trust='portal-redirect')]*3,code='VPN-003'),True,
                         [65535]*8)
        self.assertLess(len(longest),400)
        self.assertLess(len(self.line(dns_ok=None,probe_checks=None)),100)


class Ring(unittest.TestCase):
    def test_the_ring_never_exceeds_256_kib_and_keeps_the_newest_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            writer=P.Writer(directory)
            peak=0
            for i in range(30000):
                writer.record([row(time=T0+i),row(id='wireguard:peer_8',time=T0+i)],{'wireguard:peer_7':[10,0,10,1,0,0,0,0]},False,T0+i)
                total=sum(p.stat().st_size for p in Path(directory).iterdir())
                peak=max(peak,total)
            self.assertLessEqual(peak,256*1024);self.assertGreater(peak,200*1024)
            reply=P.read(directory,{'limit':1000})
            self.assertEqual(reply['last'],60000);self.assertGreater(reply['first'],1)
            seqs=[r[0] for r in P.select((Path(directory)/(P.NAME+'.1')).read_text(),(Path(directory)/P.NAME).read_text(),0,10**6)['rows']]
            self.assertEqual(seqs,list(range(reply['first'],60001)),'no gap inside the ring')

    def test_files_are_private_and_nothing_else_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            P.Writer(directory).record([row()],None,False,T0)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()),[P.NAME])
            if os.name=='posix':self.assertEqual((Path(directory)/P.NAME).stat().st_mode&0o777,0o600)

    @unittest.skipUnless(hasattr(os,'symlink') and os.name=='posix','symbolic links: POSIX only')
    def test_a_symbolic_link_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'elsewhere';target.write_text('keep\n')
            (Path(directory)/P.NAME).symlink_to(target)
            with self.assertRaises(OSError):P.Writer(directory).record([row()],None,False,T0)
            with self.assertRaises(OSError):P.read(directory)
            self.assertEqual(target.read_text(),'keep\n')

    def test_a_restart_continues_the_sequence_and_a_missing_directory_is_an_error_not_a_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            first=P.Writer(directory);first.record([row(),row()],None,False,T0)
            second=P.Writer(directory);second.record([row()],None,False,T0)
            self.assertEqual([r[0] for r in P.read(directory)['rows']],[1,2,3])
            with self.assertRaises(OSError):P.Writer(directory+'/missing').record([row()],None,False,T0)

    def test_reader_works_without_any_file_and_survives_garbage(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(P.read(directory),{'version':1,'targets':list(P.TARGETS),'heartbeat':['1.1.1.1','8.8.8.8','9.9.9.9','other'],
                                                'first':0,'last':0,'count':0,'truncated':False,'rows':[]})
            (Path(directory)/P.NAME).write_bytes(b'\xff\xfe junk\n'+P.encode(1,row()).encode()+b'[1,2')
            reply=P.read(directory)
            self.assertEqual([r[0] for r in reply['rows']],[1],'garbage and the torn last line are dropped')

    def test_cursor_paging(self):
        with tempfile.TemporaryDirectory() as directory:
            writer=P.Writer(directory)
            for i in range(10):writer.record([row(time=T0+i)],None,False,T0)
            cursor=0;seen=[]
            while True:
                reply=P.read(directory,{'after':cursor,'limit':3})
                seen+= [r[0] for r in reply['rows']]
                if not reply['truncated']:break
                cursor=reply['rows'][-1][0]
            self.assertEqual(seen,list(range(1,11)))


class Wiring(unittest.TestCase):
    def test_option_default_on_and_only_an_explicit_zero_switches_it_off(self):
        text=(LIB/'inventory.lua').read_text(encoding='utf-8')
        self.assertIn("main.probe_target_log=s.probe_target_log~='0'",text)
        self.assertTrue(P.enabled({'probe_target_log':True}));self.assertFalse(P.enabled({'probe_target_log':False}))
        self.assertFalse(P.enabled({}));self.assertFalse(P.enabled(None));self.assertFalse(P.enabled({'probe_target_log':1}))
        self.assertEqual(P.OPTION,'probe_target_log')
        self.assertIn("M.OPTION='probe_target_log'",(LIB/'lua/probe_target_log.lua').read_text(encoding='utf-8'))

    def test_rpc_list_acl_and_dispatcher(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):agent.rpc('list')
        self.assertEqual(json.loads(out.getvalue())['probe_targets'],{'after':0,'limit':0})
        acl=json.loads((ROUTER/'files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json').read_text())['luci-app-homensai-vpn']
        self.assertIn('probe_targets',acl['read']['ubus']['homensai-vpn']);self.assertNotIn('probe_targets',acl['write']['ubus']['homensai-vpn'])
        plugin=(ROUTER/'files/usr/libexec/rpcd/homensai-vpn').read_text(encoding='utf-8')
        self.assertIn('call:probe_targets:2',plugin);self.assertIn('telegram_retry|probe_targets) ;;',plugin)
        lua=(LIB/'lua/rpc.lua').read_text(encoding='utf-8')
        self.assertIn("M.PROBE_LOG={'probe_targets'}",lua);self.assertIn('state.probe_targets(arguments)',lua)
        self.assertIn('target_log.read(runner.read_file,self.runtime,arguments)',(LIB/'lua/monitor.lua').read_text(encoding='utf-8'))

    def rpc(self,directory,body):
        out=io.StringIO()
        with patch.object(agent,'RUNTIME',Path(directory)),patch.object(agent.sys,'stdin',types.SimpleNamespace(buffer=io.BytesIO(body))),\
                contextlib.redirect_stdout(out):
            code=agent.call('probe_targets')
        return code,json.loads(out.getvalue())

    def test_agent_answers_the_read_only_rpc_from_the_ring(self):
        with tempfile.TemporaryDirectory() as directory:
            P.Writer(directory).record([row(),row(id='wireguard:peer_8')],None,False,T0)
            code,reply=self.rpc(directory,b'{"after":1,"limit":5,"ubus_rpc_session":"S"}')
            self.assertEqual((code,reply['count'],reply['rows'][0][2]),(0,1,'wireguard:peer_8'))
            code,reply=self.rpc(directory,b'')
            self.assertEqual((code,reply['count']),(0,2))
            for body,error in ((b'{"limit":0}','RPC-INPUT-INVALID'),(b'{"x":1}','RPC-UNEXPECTED-ARGS'),(b'[1]','RPC-INPUT-OBJECT'),
                               (b'{"after":-1}','RPC-INPUT-INVALID'),(b'{"limit":1.5}','RPC-INPUT-INVALID')):
                code,reply=self.rpc(directory,body)
                self.assertEqual((code,reply),(1,{'error':error}),str(body))
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()),[P.NAME],'a read creates nothing')

    def test_only_the_monitors_write_the_ring(self):
        # setup_config.py / setup_save.lua only write the option probe_target_log (the expert page, setup_detector); they never touch the ring
        allowed={'probe_target_log.py','agent.py','lua/probe_target_log.lua','lua/monitor.lua','lua/fast_detect.lua','lua/rpc.lua','inventory.lua','setup_config.py','setup_save.lua'}
        found=set()
        for path in list(LIB.rglob('*.py'))+list(LIB.rglob('*.lua')):
            text=path.read_text(encoding='utf-8',errors='replace')
            if re.search(r'probe_target_log|probe-targets',text):found.add(path.relative_to(LIB).as_posix())
        self.assertEqual(found,allowed)
        for name in ('agent.py','lua/monitor.lua'):
            self.assertEqual(len(re.findall(r'(?:probe_target_log|target_log)\.Writer\(',(LIB/name).read_text(encoding='utf-8'))),1,name+': one writer')  # the heartbeat RTT log has its own ring
        self.assertNotIn('Writer',(LIB/'lua/rpc.lua').read_text(encoding='utf-8'))

    def test_lua_twin_has_the_same_constants(self):
        text=(LIB/'lua/probe_target_log.lua').read_text(encoding='utf-8')
        self.assertIn('M.SEGMENT=128*1024',text);self.assertEqual(P.SEGMENT,128*1024)
        self.assertEqual(P.RING_BYTES,256*1024)
        self.assertIn('M.DEFAULT_ROWS=%d'%P.DEFAULT_ROWS,text);self.assertIn('M.MAX_ROWS=%d'%P.MAX_ROWS,text)
        self.assertIn("M.TARGETS={%s}"%','.join("'%s'"%t for t in P.TARGETS),text)
        self.assertIn("M.HEARTBEAT_SLOTS={%s}"%','.join("'%s'"%t for t in P.HEARTBEAT_SLOTS),text)
        results=re.search(r'local RESULTS=\{(.*?)\}\n',text).group(1)
        self.assertEqual({k.strip("[]'"):int(v) for k,v in (item.split('=') for item in results.split(','))},P.RESULTS)
        verdicts=re.search(r"local VERDICTS=\{(.*?)\}\n",text,re.S).group(1)
        self.assertEqual({k.strip("[]'"):int(v) for k,v in (item.split('=') for item in re.sub(r'\s+','',verdicts).split(','))},P.VERDICTS)
        self.assertIn('local RESULT_UNKNOWN,NOT_MEASURED,UNTRUSTED=7,9,10',text)
        self.assertEqual((P.RESULT_UNKNOWN,P.NOT_MEASURED,P.UNTRUSTED,P.VERDICT_OTHER),(7,9,10,9))
        self.assertIn("local MAX_MS,MAX_COUNT,MAX_STAMP=600000,65535,999999999999",text)
        self.assertEqual((P.MAX_MS,P.MAX_COUNT,P.MAX_STAMP),(600000,65535,999999999999))
        trust=re.findall(r"\['([a-z-]+)'\]=true",re.search(r'local TRUST_REASONS=\{(.*?)\}\n',text).group(1))
        self.assertEqual(tuple(trust),P.TRUST_REASONS)
        import probe_trust
        self.assertEqual(set(probe_trust.REASONS),set(P.TRUST_REASONS),'the reasons of probe_trust.py')

    def test_documentation_is_present(self):
        doc=(ROUTER.parent/'docs/architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md').read_text(encoding='utf-8')
        for word in ('probe_target_log','probe_targets','cycle_router.per-target.py','256','tmpfs'):self.assertIn(word,doc)


class PythonMonitorLoop(unittest.TestCase):
    """The real agent.monitor_loop with the probes faked at the socket level (as test_mtu_check.MonitorLoopIntegration)."""
    SOURCE,TARGET='wireguard:peer_7','wireguard:peer_8'

    def passes(self,option,faults,pair=True,dense=()):
        profiles=[dict(id=pid,section=pid.split(':')[1],name=pid,protocol='wireguard',interface=dev,administrative_state='enabled',
                       vendor_tunnel_id='wireguard:'+dev) for pid,dev in ((self.SOURCE,'wgclient1'),(self.TARGET,'wgclient2'))]
        profiles.append(dict(id='openvpn:1_2',section='1_2',name='Paris',protocol='openvpn',interface='ovpnclient1',administrative_state='enabled',
                             vendor_tunnel_id='openvpn:ovpnclient1'))
        settings={'interval':30,'checkpoint':900,'probe_limit':8,'plan_enabled':False,'probe_target_log':option}
        if pair:settings.update(plan_source=self.SOURCE,plan_target=self.TARGET,plan_source_tunnel='wireguard:wgclient1',plan_target_tunnel='wireguard:wgclient2')
        data={'profiles':profiles,'servers':[],'wan_interfaces':[],'settings':settings}
        statuses=[]
        bindings={'wgclient1':{'code':None,'device':'wgclient1','mark':4096,'table':'1001','ifindex':7},
                  'wgclient2':{'code':None,'device':'wgclient2','mark':8192,'table':'1002','ifindex':8},
                  'ovpnclient1':{'code':None,'device':'ovpnclient1','mark':12288,'table':'1003','ifindex':9}}
        by_interface={p['interface']:p for p in profiles}
        state={'pass':0}
        def route_binding(logical):return bindings[logical]
        def https(device,mark,target,seconds=None):
            fault=faults[min(state['pass'],len(faults)-1)]
            if fault.get('device')==device:
                if target[1] in fault['dead']:raise socket.timeout()
            time.sleep(0.002)  # a visible elapsed time
            return 20.0+len(target[1])
        def dns(device,mark,seconds=None):
            fault=faults[min(state['pass'],len(faults)-1)]
            return not (fault.get('device')==device and fault.get('dns_dead'))
        real_write=agent.atomic_json
        def write(path,value):
            real_write(path,value)
            if Path(path).name=='status.json':
                statuses.append(copy.deepcopy(value));state['pass']+=1
                if len(statuses)>=len(faults):agent.STOP=True
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory)
            for name,value in [('RUNTIME',root),('PERSIST',root),('STOP',False)]:stack.enter_context(patch.object(agent,name,value))
            stack.enter_context(patch('auto_control.RUNTIME',root));stack.enter_context(patch('auto_control.PERSIST',root))
            stack.enter_context(patch.object(agent,'route_binding',side_effect=route_binding))
            stack.enter_context(patch.object(agent,'https_probe',side_effect=https))
            stack.enter_context(patch.object(agent,'dns_probe',side_effect=dns))
            stack.enter_context(patch('server_endpoint.observe',return_value=None))
            stack.enter_context(patch.object(agent,'inventory',return_value=data))
            stack.enter_context(patch('website_response.WebsiteSampler'));stack.enter_context(patch('icmp_ping.PingSampler'))
            stack.enter_context(patch.object(agent,'restore',return_value=(agent.Accounting(),None)))
            stack.enter_context(patch.object(agent,'sample_counters'));stack.enter_context(patch.object(agent,'sample_wan_counters',return_value=[]))
            stack.enter_context(patch.object(agent,'checkpoint'))
            stack.enter_context(patch.object(agent,'monitor_poll_interval',return_value=0))
            stack.enter_context(patch('telegram_report.deliver',return_value=({'enabled':False},{},False)))
            stack.enter_context(patch('system_readiness.snapshot',return_value={}))
            stack.enter_context(patch('server_pick.job'))
            stack.enter_context(patch('probe_policy.Booster.dense',side_effect=lambda *a,**k:{'reason':'test'} if state['pass'] in dense else None))
            stack.enter_context(patch('speed_test.observe_traffic'));stack.enter_context(patch('speed_test.automatic_new',return_value=set()))
            stack.enter_context(patch('speed_test.active_job',return_value=False));stack.enter_context(patch('speed_test.cancel'))
            stack.enter_context(patch.object(agent,'atomic_json',side_effect=write))
            try:agent.monitor_loop()
            finally:agent.STOP=False
            ring=(root/P.NAME)
            text=ring.read_text() if ring.exists() else None
            files=sorted(p.name for p in root.iterdir() if p.name.startswith('probe-targets'))
        return text,files,statuses

    def test_option_on_logs_the_two_auto_channels_of_every_pass(self):
        text,files,statuses=self.passes(True,[{},{'device':'wgclient1','dead':['dns.google','dns.quad9.net']},{}])
        rows=[P.parse_line(line) for line in text.splitlines()]
        self.assertEqual(files,[P.NAME]);self.assertEqual(len(rows),6)
        self.assertEqual([r[0] for r in rows],[1,2,3,4,5,6])
        self.assertEqual([r[2] for r in rows],[self.SOURCE,self.TARGET]*3,'the third (OpenVPN) channel is not an Auto channel')
        self.assertEqual(rows[0][3:5],[0,0]);self.assertEqual(rows[0][5][0::2],[0,0,0]);self.assertTrue(all(ms>0 for ms in rows[0][5][1::2]))
        failing=rows[2]
        self.assertEqual((failing[3],failing[5][0::2]),(2,[0,1,1]),'VPN-003: two of three targets timed out')
        self.assertEqual(rows[3][3],0,'the other channel was healthy')
        self.assertEqual(rows[2][7],[],'the Python monitor has no heartbeat');self.assertEqual(rows[2][6],0)
        measured=statuses[1]['profiles'][0]
        self.assertEqual(rows[2][1],int(measured['time']),'the time of the probe in the status row')
        self.assertEqual(rows[2][5][1::2][0],int(math.floor(measured['probe_checks'][0]['elapsed_ms']+0.5)),'the same reading as the status row')

    def test_a_dense_confirmation_pass_is_flagged(self):
        text,_,_=self.passes(True,[{},{},{}],dense=(1,))
        rows=[P.parse_line(line) for line in text.splitlines()]
        self.assertEqual([r[4] for r in rows],[0,0,1,1,0,0])

    def test_a_dead_dns_is_a_dns_code(self):
        text,_,_=self.passes(True,[{'device':'wgclient2','dead':[],'dns_dead':True}])
        rows=[P.parse_line(line) for line in text.splitlines()]
        self.assertEqual((rows[1][3],rows[1][6],rows[1][5][0::2]),(1,1,[0,0,0]))

    def test_option_off_or_without_a_pair_writes_nothing(self):
        for option,pair in ((False,True),(True,False)):
            text,files,_=self.passes(option,[{},{}],pair)
            self.assertIsNone(text);self.assertEqual(files,[])

    def test_an_unwritable_ring_never_stops_the_monitor(self):
        with patch.object(P.Writer,'record',side_effect=OSError('read-only file system')),patch.object(agent.sys.stderr,'write') as stderr:
            text,files,statuses=self.passes(True,[{},{},{}])
        self.assertEqual(len(statuses),3);self.assertIsNone(text)
        logged=[call.args[0] for call in stderr.call_args_list if 'probe target log' in call.args[0]]
        self.assertEqual(len(logged),1,'the same fault is logged once')


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaTwin(unittest.TestCase):
    def test_the_lua_suite_passes(self):
        result=subprocess.run([LUA,str(HERE/'lua/test_probe_target_log.lua')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(HERE/'lua'),timeout=300)
        self.assertEqual(result.returncode,0,result.stdout.decode()+result.stderr.decode())


if __name__=='__main__':
    unittest.main()
