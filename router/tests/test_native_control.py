import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent


class ControlTests(unittest.TestCase):
    def invoke(self,method,payload):
        incoming=types.SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))
        out=io.StringIO()
        with patch.object(agent.sys,'stdin',incoming),contextlib.redirect_stdout(out):agent.rpc(method)
        return json.loads(out.getvalue())

    def test_confirm_only_matches_live_pending_transaction(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'RUNTIME',Path(d)),patch.object(agent,'PERSIST',Path(d)):
            pending={'state':'WAIT-CLIENT','tx':'a'*32,'expected_exit':'9.9.9.9','deadline':time.time()+60}
            agent.atomic_json(Path(d)/'native-status.json',pending)
            tx=dict(pending,phase='WAIT-CLIENT');agent.atomic_json(Path(d)/'native-transaction.json',{'schema':1,'data':tx,'sha256':agent.checksum(tx)})
            args={'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'ubus_rpc_session':'SESSION_SENTINEL'}
            self.assertTrue(self.invoke('native_confirm',args)['accepted'])
            value=json.loads((Path(d)/'native-confirm.json').read_text())
            self.assertNotIn('ubus_rpc_session',value);self.assertEqual(value['tx'],'a'*32)

    def test_invalid_or_expired_confirm_never_written(self):
        mutations=[{'tx':'b'*32},{'exit_ipv4':'8.8.8.8'},{'dns_ok':False},{'https_ok':False},{'exit_ipv4':'192.168.1.2'},{'tx':'../evil'},{'extra':'x'}]
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'RUNTIME',Path(d)),patch.object(agent,'PERSIST',Path(d)):
            pending={'state':'WAIT-CLIENT','tx':'a'*32,'expected_exit':'9.9.9.9','deadline':time.time()+60}
            agent.atomic_json(Path(d)/'native-status.json',pending)
            tx=dict(pending,phase='WAIT-CLIENT');agent.atomic_json(Path(d)/'native-transaction.json',{'schema':1,'data':tx,'sha256':agent.checksum(tx)})
            for mutation in mutations:
                args={'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True};args.update(mutation)
                with self.assertRaises(ValueError):self.invoke('native_confirm',args)
                self.assertFalse((Path(d)/'native-confirm.json').exists())
            pending['deadline']=time.time()-1;agent.atomic_json(Path(d)/'native-status.json',pending)
            tx=dict(pending,phase='WAIT-CLIENT');agent.atomic_json(Path(d)/'native-transaction.json',{'schema':1,'data':tx,'sha256':agent.checksum(tx)})
            with self.assertRaises(ValueError):self.invoke('native_confirm',{'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True})

    def test_stop_targets_configured_trial_even_before_first_attempt(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'RUNTIME',Path(d)/'run'),patch.object(agent,'PERSIST',Path(d)/'persist'),patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"new-trial"}}'):
            self.assertTrue(self.invoke('native_stop',{})['queued'])
            self.assertEqual(json.loads((Path(d)/'persist/native-stop.json').read_text())['trial'],'new-trial')
            self.assertFalse((Path(d)/'run/native-stop.json').exists())

    def test_stale_public_wait_cannot_confirm_a_rolled_back_private_transaction(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'RUNTIME',Path(d)),patch.object(agent,'PERSIST',Path(d)):
            pending={'state':'WAIT-CLIENT','tx':'a'*32,'expected_exit':'9.9.9.9','deadline':time.time()+60}
            agent.atomic_json(Path(d)/'native-status.json',pending)
            tx=dict(pending,phase='ROLLED-BACK')
            agent.atomic_json(Path(d)/'native-transaction.json',{'schema':1,'data':tx,'sha256':agent.checksum(tx)})
            with self.assertRaises(ValueError):self.invoke('native_confirm',{'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True})
            self.assertFalse((Path(d)/'native-confirm.json').exists())


if __name__=='__main__':unittest.main()
