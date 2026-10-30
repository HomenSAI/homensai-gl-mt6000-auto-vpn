"""beta10: page buttons answered by the running monitor give agent.py's exact answer; light click gate; fast parsers."""
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,kernel_policy,native_switch as n,pair_manual as manual


class SameAnswer(unittest.TestCase):
    def rpc(self,method,arguments):
        output=io.StringIO()
        stdin=type('Stdin',(),{'buffer':io.BytesIO(json.dumps(arguments).encode())})()
        with patch.object(agent.sys,'stdin',stdin),redirect_stdout(output):
            agent.rpc(method)
        return json.loads(output.getvalue())

    def test_each_button_gives_the_same_answer_both_ways(self):
        cases={'fault_cancel':({},'fault_control.cancel',{'cleaned':True}),
               'setup_probe':({'level':3,'boost':True},'setup_config.save',{'saved':True,'mode':'monitor'}),
               'native_start':({'control_revision':'a'*32},'auto_control.start',{'accepted':True,'queued':True})}
        for method,(arguments,target,answer) in cases.items():
            with self.subTest(method=method),patch(target,return_value=answer):
                self.assertEqual(agent.control_reply(method,dict(arguments)),answer)
                self.assertEqual(self.rpc(method,arguments),answer)

    def test_stop_cleans_a_running_failure_test_both_ways(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(agent,'RUNTIME',Path(folder)), \
                patch('auto_control.stop',side_effect=lambda **kwargs:{'queued':True}),patch('fault_control.cancel',return_value={'cleaned':True}):
            (Path(folder)/'fault-intent.json').write_text('{}')
            self.assertEqual(agent.control_reply('native_stop',{}),{'queued':True,'fault_cleanup':True})
            self.assertEqual(self.rpc('native_stop',{}),{'queued':True,'fault_cleanup':True})

    def test_unknown_or_extra_input_is_refused(self):
        with self.assertRaises(ValueError):agent.control_reply('native_stop',{'x':1})
        with self.assertRaises(ValueError):agent.control_reply('setup_system',{})


class LightGate(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.run_dir=Path(folder.name)
        for target in (agent,n):
            p=patch.object(target,'RUNTIME',self.run_dir);p.start();self.addCleanup(p.stop)
        p=patch.object(n,'STATE',self.run_dir/'native-status.json');p.start();self.addCleanup(p.stop)
        p=patch.object(n,'journal_read',return_value={'phase':'ROLLED-BACK'});p.start();self.addCleanup(p.stop)
        self.now=manual.time.time()
        agent.atomic_json(n.STATE,{'state':'OBSERVING','time':self.now,'source':'wireguard:peer_1','target':'openvpn:1_2'})
        self.status({'id':'wireguard:peer_1','time':self.now,'code':None,'dns_ok':True,'https_success':2},
                    {'id':'openvpn:1_2','time':self.now,'code':None,'dns_ok':True,'https_success':2})

    def status(self,*rows):
        agent.atomic_json(self.run_dir/'status.json',{'profiles':list(rows)})

    def test_live_targets_pass_without_the_full_button_model(self):
        with patch.object(manual,'controls',side_effect=AssertionError('no full model')):
            self.assertIsNone(manual.light_gate('reserve',{'interval':'10'}))
            self.assertIsNone(manual.light_gate('primary',{'interval':'10'}))

    def test_dead_busy_or_stale_is_refused_at_once(self):
        self.status({'id':'openvpn:1_2','time':self.now,'code':'VPN-001'})
        self.assertEqual(manual.light_gate('reserve',{'interval':'10'}),'PAIR-MANUAL-TARGET-UNHEALTHY')
        self.assertEqual(manual.light_gate('primary',{'interval':'10'}),'SOURCE-NOT-HEALTHY')
        agent.atomic_json(n.STATE,{'state':'APPLYING','time':self.now})
        self.assertEqual(manual.light_gate('reserve',{'interval':'10'}),'PAIR-MANUAL-BUSY')
        agent.atomic_json(n.STATE,{'state':'OBSERVING','time':self.now-120})
        self.assertEqual(manual.light_gate('reserve',{'interval':'10'}),'PAIR-MANUAL-STALE')


class FastParsers(unittest.TestCase):
    def test_read_json_keeps_its_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'x.json'
            path.write_text('{"a":1,"b":2.5,"c":[1e3,-7]}');value=agent.read_json(path)
            self.assertEqual(value,{'a':1,'b':2.5,'c':[1000.0,-7]});self.assertIs(type(value['a']),int)
            for bad in ('{"a":1e999}','{"a":NaN}','{"a":Infinity}','{"a":1,"a":2}'):
                path.write_text(bad)
                with self.assertRaises(ValueError):agent.read_json(path)

    def test_mangle_parse_is_the_same_with_the_line_cache(self):
        text='*mangle\n:PREROUTING ACCEPT [0:0]\n:X - [0:0]\n-A PREROUTING -j X\n-A X -m comment --comment "a b" -j MARK --set-xmark 0x1/0xf\nCOMMIT\n'
        kernel_policy._TOKENS.clear()
        first=kernel_policy.parse_mangle(text);second=kernel_policy.parse_mangle(text)
        self.assertEqual(first,second)
        self.assertEqual(first['X'],[['-m','comment','--comment','a b','-j','MARK','--set-xmark','0x1/0xf']])
        first['X'][0].append('mutated');self.assertNotIn('mutated',kernel_policy.parse_mangle(text)['X'][0])


if __name__=='__main__':unittest.main()
