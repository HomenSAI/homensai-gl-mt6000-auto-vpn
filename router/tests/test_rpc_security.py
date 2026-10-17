"""Adversarial RPC inputs; all state-writing operations are mocked and must remain untouched."""
import io,json,random,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
from rpc_input import decode_request
class RpcSecurityTests(unittest.TestCase):
    def refuse(self,body):
        with patch.object(agent.sys,'stdin',types.SimpleNamespace(buffer=io.BytesIO(body))),patch.object(agent,'atomic_json') as write,patch.object(agent.subprocess,'run') as command:
            with self.assertRaises(ValueError):agent.rpc('scan')
            write.assert_not_called();command.assert_not_called()
    def test_duplicate_fields_and_session_smuggling_refused(self):
        for body in (b'{"enabled":true,"enabled":false}',b'{"ubus_rpc_session":"a","ubus_rpc_session":"b"}',b'{"x":{"source":"a","source":"b"}}'):self.refuse(body)
    def test_bounded_depth_size_and_nonfinite_numbers(self):
        for body in (b' '*65537,b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e9999}',b'{"x":'+b'['*70+b'0'+b']'*70+b'}',b'{"x":'+b'['*1100+b'0'+b']'*1100+b'}',b'{"x":['+b'0,'*10000+b'0]}'):self.refuse(body)
    def test_256_deterministic_hostile_inputs_never_mutate(self):
        rng=random.Random(20261016)
        payloads=[b'null',b'[]',b'1',b'true',b'"string"',b'{',b'\xff',b'{"extra":"$(touch /tmp/pwn)"}',b'{"extra":";reboot"}',b'{"extra":"<img src=x onerror=alert(1)>"}']
        for case in range(256):
            with self.subTest(case=case):self.refuse(rng.choice(payloads))
    def test_session_is_removed_not_echoed(self):
        self.assertEqual(decode_request(b'{"ubus_rpc_session":"PRIVATE_SESSION_SENTINEL"}'),{})
    def test_acl_has_no_wildcards_or_anonymous_roles(self):
        path=Path(__file__).resolve().parents[1]/'files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json'
        value=json.loads(path.read_text());self.assertEqual(set(value),{'luci-app-homensai-vpn'});scope=value['luci-app-homensai-vpn']
        self.assertEqual(set(scope['write']),{'ubus'});self.assertEqual(set(scope['read']),{'ubus'})
        reads=scope['read']['ubus'];writes=scope['write']['ubus'];self.assertEqual(set(reads),{'homensai-vpn'});self.assertEqual(set(writes),{'homensai-vpn'})
        self.assertNotIn('*',json.dumps(value));self.assertNotIn('native_start',reads['homensai-vpn']);self.assertIn('native_start',writes['homensai-vpn'])
if __name__=='__main__':unittest.main()
