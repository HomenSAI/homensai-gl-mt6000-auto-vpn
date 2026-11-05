"""flow_reset.py + its two call sites in native_switch (attempt COMMITTED, rollback ROLLED-BACK). The decision cases are
shared with tests/lua/test_auto_flow_reset.lua (flow_reset_cases.json): Python and Lua drop exactly the same flows."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch,MagicMock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[0]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
import flow_reset as F
import native_switch as native
import retention_settings
from test_native_switch import Backend

CASES=json.loads((HERE/'flow_reset_cases.json').read_text(encoding='utf-8'))['cases']
CONFIG="config main 'main'\n"


class SharedCases(unittest.TestCase):
    def test_cases(self):
        for case in CASES:
            with self.subTest(case['name']):
                ran,logs=[],[]
                def execute(argv,case=case):
                    ran.append(argv)
                    if case['exec'].get('raise'):raise OSError('runner failed')
                    return case['exec']['rc'],case['exec']['out'],case['exec'].get('timed_out') is True
                result=F.run({'config':case['config'],'old_status':case['old'],'new_status':case['new'],'exec':execute,'log':logs.append})
                e=case['expect']
                self.assertEqual((result['code'],result['deleted'],result['address']),(e['code'],e['deleted'],e['address']))
                self.assertEqual(ran,[] if e['argv'] is None else [e['argv']])
                self.assertEqual(logs,[] if e['log'] is None else [e['log']])

    def test_the_command_names_only_the_old_nat_address(self):
        self.assertEqual(F.argv('10.5.0.2'),['conntrack','-D','-f','ipv4','--reply-dst','10.5.0.2','--src-nat'])
        self.assertEqual(F.TIMEOUT,1)

    def test_lua_twin_has_the_same_command_and_bounds(self):
        lua=(ROOT/'lua/flow_reset.lua').read_text(encoding='utf-8')
        self.assertIn("{'conntrack','-D','-f','ipv4','--reply-dst',address,'--src-nat'}",lua)
        self.assertIn('M.TIMEOUT=1',lua);self.assertIn("M.PREFIX='FLOW-RESET-'",lua)

    def test_execute_is_bounded_and_maps_a_missing_tool(self):
        with patch.object(F.subprocess,'run',side_effect=subprocess.TimeoutExpired(['conntrack'],1,output=b'a\n')) as run:
            self.assertEqual(F.execute(['conntrack']),(124,'a\n',True))
            self.assertEqual(run.call_args.kwargs['timeout'],1)
        with patch.object(F.subprocess,'run',side_effect=FileNotFoundError()):
            self.assertEqual(F.execute(['conntrack']),(127,'',False))
        with patch.object(F.subprocess,'run',return_value=MagicMock(returncode=0,stdout=b'x\ny\n')):
            self.assertEqual(F.execute(['conntrack']),(0,'x\ny\n',False))


class LinuxBackend(unittest.TestCase):
    PROFILES=[{'id':'wireguard:peer_2','interface':'wgclient1'},{'id':'openvpn:1_1','interface':'ovpnclient2'}]

    def statuses(self,args):
        name=args[2].split('.')[-1]
        address={'wgclient1':'10.5.0.2','ovpnclient2':'10.100.0.2'}[name]
        return json.dumps({'up':True,'l3_device':name,'ipv4-address':[{'address':address,'mask':32}]}).encode()

    def test_without_the_package_config_nothing_is_read_or_run(self):
        with patch.object(F,'read_config',return_value=None),patch.object(native,'command') as cmd,patch.object(F,'execute') as run:
            self.assertEqual(native.Linux().flow_reset('wireguard:peer_2','openvpn:1_1')['code'],'FLOW-RESET-OFF')
            cmd.assert_not_called();run.assert_not_called()

    def test_failover_deletes_by_the_old_tunnel_address(self):
        with patch.object(F,'read_config',return_value=CONFIG),patch.object(native,'inventory',return_value={'profiles':self.PROFILES}), \
             patch.object(native,'command',side_effect=self.statuses),patch.object(F,'execute',return_value=(0,'one\n',False)) as run, \
             patch.object(native.subprocess,'run') as logger:
            result=native.Linux().flow_reset('wireguard:peer_2','openvpn:1_1')
            self.assertEqual((result['code'],result['deleted'],result['address']),('FLOW-RESET-DONE',1,'10.5.0.2'))
            run.assert_called_once_with(['conntrack','-D','-f','ipv4','--reply-dst','10.5.0.2','--src-nat'])
            self.assertEqual(logger.call_args.args[0],['logger','-t','homensai-vpn','FLOW-RESET-DONE: address 10.5.0.2 deleted 1'])

    def test_unreadable_status_is_no_address_not_an_error(self):
        with patch.object(F,'read_config',return_value=CONFIG),patch.object(native,'inventory',return_value={'profiles':self.PROFILES}), \
             patch.object(native,'command',side_effect=OSError('ubus')),patch.object(F,'execute') as run,patch.object(native.subprocess,'run'):
            self.assertEqual(native.Linux().flow_reset('wireguard:peer_2','openvpn:1_1')['code'],'FLOW-RESET-NO-ADDRESS')
            run.assert_not_called()


class Recorder(Backend):
    def __init__(self):
        super().__init__();self.resets=[]
    def flow_reset(self,old_id,new_id):
        self.calls.append(('flow_reset',old_id,new_id));self.resets.append((old_id,new_id))
        return {'code':'FLOW-RESET-DONE','deleted':1}


class CallSites(unittest.TestCase):
    def setUp(self):
        for patcher in (patch.object(native.os,'killpg'),patch.object(native,'RETURN_PAUSE',0),
                        patch.object(native,'clear_native_options',return_value=True),
                        patch.object(retention_settings,'configured_days',return_value=7)):
            patcher.start();self.addCleanup(patcher.stop)

    def test_reset_old_flows_roles_and_failures(self):
        b=Recorder();journal={'source':'s','target':'t'}
        self.assertEqual(native.reset_old_flows(b,journal,'target'),'FLOW-RESET-DONE')
        self.assertEqual(native.reset_old_flows(b,journal,'source'),'FLOW-RESET-DONE')
        self.assertEqual(b.resets,[('s','t'),('t','s')])
        self.assertIsNone(native.reset_old_flows(b,journal,None));self.assertEqual(len(b.resets),2)
        self.assertIsNone(native.reset_old_flows(Backend(),journal,'target'))
        b.flow_reset=MagicMock(side_effect=native.Refused('COMMAND-FAILED'))
        self.assertEqual(native.reset_old_flows(b,journal,'target'),'FLOW-RESET-FAILED')

    def run_attempt(self,b,confirm=True,failing_reset=False):
        process=MagicMock(pid=123,returncode=0)
        def spawn(*a,**k):
            b.current[-2],b.current[-1]=b.current[-1],b.current[-2]
            if confirm:native.atomic_json(native.RUNTIME/'native-confirm.json',{'tx':'e'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'time':time.time()})
            return process
        if failing_reset:b.flow_reset=MagicMock(side_effect=RuntimeError('conntrack exploded'))
        with tempfile.TemporaryDirectory() as d,patch.object(native,'PERSIST',Path(d)),patch.object(native,'RUNTIME',Path(d)),patch.object(native,'JOURNAL',Path(d)/'journal'), \
             patch.object(native,'STATE',Path(d)/'status'),patch.object(native,'CERT',Path(d)/'cert'),patch.object(native.uuid,'uuid4',return_value=MagicMock(hex='e'*32)), \
             patch.object(native.subprocess,'Popen',side_effect=spawn),patch.object(native,'trace',return_value='9.9.9.9'), \
             patch.object(native,'transaction_expired',side_effect=lambda j:not confirm):
            try:native.attempt(b,b.selection,time.time()+120,False)
            finally:self.phase=native.journal_read()['phase']

    def test_committed_failover_resets_the_primary_flows_after_the_guard(self):
        b=Recorder();self.run_attempt(b)
        self.assertEqual(self.phase,'COMMITTED')
        self.assertEqual(b.resets,[(b.profiles[0]['id'],b.profiles[1]['id'])])
        names=[c[0] for c in b.calls]
        self.assertLess(names.index('guard'),names.index('flow_reset'))

    def test_a_failed_reset_never_fails_the_committed_switch(self):
        b=Recorder();self.run_attempt(b,failing_reset=True)
        self.assertEqual(self.phase,'COMMITTED');self.assertEqual(b.current[-2:],b.selection['order'][-2:][::-1])

    def test_rollback_after_a_failed_switch_resets_the_reserve_flows(self):
        b=Recorder()
        with self.assertRaisesRegex(native.Refused,'CONFIRMATION-TIMEOUT'):self.run_attempt(b,confirm=False)
        self.assertEqual(self.phase,'ROLLED-BACK')
        self.assertEqual(b.resets,[(b.profiles[1]['id'],b.profiles[0]['id'])])

    def test_rollback_resets_after_restoring_and_guarding(self):
        b=Recorder();before=b.current[:];after=before[:];after[-2],after[-1]=after[-1],after[-2];b.current=after
        with tempfile.TemporaryDirectory() as d,patch.object(native,'PERSIST',Path(d)),patch.object(native,'RUNTIME',Path(d)),patch.object(native,'JOURNAL',Path(d)/'tx.json'):
            native.rollback(b,{'before':before,'after':after,'hash':b.fingerprint,'source':'s','target':'t'},'PRIMARY-STABLY-RECOVERED')
            self.assertEqual(b.current,before)
        self.assertEqual(b.resets,[('t','s')])
        self.assertEqual(b.calls[-2:],[('guard',['wgclient1','tun0']),('flow_reset','t','s')])

    def test_failed_rollback_resets_nothing(self):
        b=Recorder();b.apply=MagicMock(side_effect=OSError('mock'))
        with self.assertRaises(OSError):native.rollback(b,{'hash':b.fingerprint,'before':b.current,'after':b.current,'source':'s','target':'t'},'test')
        self.assertEqual(b.resets,[])


if __name__=='__main__':
    unittest.main()
