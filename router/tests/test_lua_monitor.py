"""The Lua monitor's files are accepted by the Python validators: checkpoint.json by checkpoint_schema.validate,
agent.read_json and agent.checksum; status.json by agent.read_json with the fields the page reads; the canonical
JSON of canon.lua is byte-identical to json.dumps(sort_keys=True, separators=(',',':')); rpc.decode_request gives
the codes of rpc_input.decode_request. Runs where lua5.1 exists (homensai-vpn-python39:local)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

LUA=shutil.which('lua5.1')
ROOT=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
FIXTURE=Path(__file__).resolve().parent/'lua/monitor_fixture.lua'
sys.path.insert(0,str(ROOT))
import checkpoint_schema  # noqa: E402
import rpc_input  # noqa: E402
spec=importlib.util.spec_from_file_location('monitor_agent',ROOT/'agent.py')
agent=importlib.util.module_from_spec(spec);spec.loader.exec_module(agent)


def lua(*args):
    return subprocess.run([LUA,str(FIXTURE),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=120).stdout.decode()


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaMonitorFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.mkdtemp()
        output=lua(cls.directory)
        assert output.strip()=='ok',output

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory,ignore_errors=True)

    def test_checkpoint_envelope_passes_python_validation_and_digest(self):
        for name in ('checkpoint.json','checkpoint.backup.json'):
            path=Path(self.directory)/name
            envelope=agent.read_json(path)
            data=checkpoint_schema.validate(envelope)
            self.assertEqual(envelope['sha256'],agent.checksum(data),name)
            self.assertEqual(data['version'],1)
            self.assertIsInstance(data['saved'],float)
            restored=agent.Accounting(data['accounting'])
            self.assertEqual(restored.gaps,data['accounting']['gaps'])
        checkpoint=agent.read_json(Path(self.directory)/'checkpoint.json')['data']['accounting']
        month=next(iter(checkpoint['months']))
        self.assertEqual(checkpoint['months'][month]['rx'],12345)
        self.assertEqual(checkpoint['wan']['months'][month]['rx'],999)
        self.assertIn('wireguard:peer_7',checkpoint['quality'])
        self.assertIn('wireguard:peer_7',checkpoint['activity'])
        import reliability
        model=reliability.Reliability(checkpoint['reliability'])  # item 6: the Lua monitor keeps the reliability model
        self.assertEqual(model.public()['totals']['outages'],2)
        self.assertEqual([e['kind'] for e in checkpoint['reliability']['events']],['FAILURE','FAILURE','RECOVERY','RECOVERY'])

    def test_status_json_fields(self):
        status=agent.read_json(Path(self.directory)/'status.json')
        for key in ('version','mode','time','profiles','accounting','samples','events','native_failover','probe_policy','stats_mode',
                    'capabilities','scope','storage_error','observation_valid_for','uplink_observation','package'):
            self.assertIn(key,status,key)
        self.assertEqual(status['mode'],'monitor')
        self.assertEqual(status['version'],agent.VERSION,'the Lua monitor reports the package version')
        self.assertEqual(status['native_failover']['state'],'OBSERVING')
        self.assertEqual([p['id'] for p in status['profiles']],['wireguard:peer_7','wireguard:peer_8'])
        self.assertEqual([p['role'] for p in status['profiles']],['source','target'])
        self.assertIsNone(status['profiles'][0]['code'])
        self.assertEqual(status['profiles'][0]['ping']['metric'],'icmp-rtt-ms')
        codes=[e['code'] for e in status['events']]
        self.assertEqual(codes,['OK','OK','VPN-003','VPN-003','OK','OK'])
        self.assertEqual(status['probe_policy']['levels']['5'],[10,30])
        self.assertEqual(status['stats_mode']['hours'],[24,72,168,336])
        self.assertEqual(status['stats_mode']['mode'],'diagnostic')
        self.assertEqual(len(status['samples']),6)
        self.assertEqual(set(status['samples'][0]),{'id','time','code','rtt_ms','https_success','dns_ok','interface','vendor_tunnel_id','vendor_generation'})
        public_model=status['accounting'].pop('reliability')  # the page view (Reliability.public), not the saved model
        self.assertTrue(public_model['checkpointed'])
        checkpoint_schema.accounting(status['accounting'])
        self.assertEqual(status['storage_error'],None)
        self.assertEqual(status['uplink_observation']['state'],'LINK-UP')

    def test_status_reply_and_auto_live_shapes(self):
        reply=json.loads((Path(self.directory)/'status_reply.json').read_text())
        self.assertEqual(reply['history_split'],['accounting.quality','accounting.reliability.events','native_history.events'])
        self.assertNotIn('quality',reply['accounting'])
        self.assertNotIn('interface',reply['samples'][0])
        self.assertIn('server_time',reply)
        live=json.loads((Path(self.directory)/'auto_live.json').read_text())
        self.assertEqual(live['native_failover']['state'],'OBSERVING')
        self.assertEqual(live['native_failover']['source'],'wireguard:peer_7')
        self.assertEqual([p['id'] for p in live['profiles']],['wireguard:peer_7','wireguard:peer_8'])
        self.assertEqual(live['observation_valid_for'],30)

    def test_canonical_json_matches_python(self):
        samples=[{'b':1,'a':[1,2.5,3.0,None,True,False,'x/ "\\\x01\x7f'],'Я':{},'Z':[]},
                 {'saved':1761825600.1234567,'rx':12345.0,'tiny':1e-05,'big':1e22,'neg':-0.0,'int':9007199254740992},
                 {'nested':{'k':[{'q':[[]]}]},'s':'\U0001f600'}]
        for value in samples:
            text=json.dumps(value,sort_keys=True,separators=(',',':'))
            output=lua('encode',text).splitlines()
            self.assertEqual(output[0],text)
            self.assertEqual(output[1],hashlib.sha256(text.encode()).hexdigest())
            self.assertEqual(output[1],agent.checksum(value))

    def test_decode_request_codes_match_rpc_input(self):
        cases=['','{"direction":"reserve","ubus_rpc_session":"s"}','{"a":1,"a":2}','[1]','{"a":NaN}','{"a":1e999}','{bad',
               '{"a":'+'['*70+']'*70+'}','"x"']
        for request in cases:
            try:expected='OK '+json.dumps(rpc_input.decode_request(request.encode()),sort_keys=True,separators=(',',':'))
            except ValueError as error:expected='ERR '+str(error)
            actual=lua('decode_request',request).strip()
            if expected.startswith('ERR RPC-INPUT-INVALID') or expected.startswith('ERR RPC-NONFINITE'):
                # Python's json raises before our walker for NaN/1e999 text in different places; both refuse.
                self.assertTrue(actual.startswith('ERR RPC-'),(request,actual))
            else:
                self.assertEqual(actual,expected,request)


if __name__=='__main__':
    unittest.main()
