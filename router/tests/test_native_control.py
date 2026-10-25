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


TRIAL='c'*32


class ControlTests(unittest.TestCase):
    def setUp(self):
        # The configured private trial number as the root-only policy helper reports it.
        policy=patch.object(agent,'command',return_value=json.dumps({'settings':{'native_trial':TRIAL}}).encode())
        policy.start();self.addCleanup(policy.stop)

    def test_disabling_every_profile_does_not_fall_back_to_probing_all(self):
        data={'profiles':[{'id':'a'},{'id':'b'}],'servers':[{'profile':'a','enabled':False},{'profile':'b','enabled':False}]}
        self.assertEqual(agent.monitoring_profiles(data)[0],[])

    def test_empty_mapping_preserves_initial_discovery(self):
        data={'profiles':[{'id':'a'},{'id':'b'}],'servers':[]}
        self.assertEqual(len(agent.monitoring_profiles(data)[0]),2)

    def test_every_registered_rpc_has_an_explicit_application_acl(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):agent.rpc('list')
        methods=set(json.loads(out.getvalue()))
        root=Path(__file__).resolve().parents[1]/'files'
        acl=json.loads((root/'usr/share/rpcd/acl.d/luci-app-homensai-vpn.json').read_text())['luci-app-homensai-vpn']
        read=set(acl['read']['ubus']['homensai-vpn'])
        write=set(acl['write']['ubus']['homensai-vpn'])
        self.assertEqual(methods,read|write)
        self.assertEqual(read,{'inventory','status','events','priority_preview','auto_live','statistics','speed_live'})
        self.assertNotIn('speed_live',write)
        self.assertNotIn('*',write)
        self.assertEqual(set(acl['write']['ubus']),{'homensai-vpn'})

    def test_lua_empty_array_tables_normalize_before_first_profile_setup(self):
        with patch.object(agent,'command',return_value=b'{"profiles":{},"servers":{},"native_candidates":{},"settings":{}}'):
            data=agent.inventory()
        self.assertEqual(data['profiles'],[])
        self.assertEqual(data['servers'],[])
        self.assertEqual(data['native_candidates'],[])

    def test_nonempty_object_is_not_accepted_as_profile_array(self):
        with patch.object(agent,'command',return_value=b'{"profiles":{"bad":1},"settings":{}}'):
            with self.assertRaises(ValueError):agent.inventory()

    def test_exec_signature_uses_json_types_not_type_names(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):agent.rpc('list')
        methods=json.loads(out.getvalue())
        self.assertIs(type(methods['native_confirm']['dns_ok']),bool)
        self.assertIs(type(methods['setup_system']['interval']),int)
        self.assertIs(type(methods['setup_system']['session_loss']),bool)
        self.assertIs(type(methods['setup_system']['servers']),list)
        self.assertIs(type(methods['setup_telegram']['enabled']),bool)

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
            args={'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'trial':TRIAL,'ubus_rpc_session':'SESSION_SENTINEL'}
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
                args={'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'trial':TRIAL};args.update(mutation)
                with self.assertRaises(ValueError):self.invoke('native_confirm',args)
                self.assertFalse((Path(d)/'native-confirm.json').exists())
            pending['deadline']=time.time()-1;agent.atomic_json(Path(d)/'native-status.json',pending)
            tx=dict(pending,phase='WAIT-CLIENT');agent.atomic_json(Path(d)/'native-transaction.json',{'schema':1,'data':tx,'sha256':agent.checksum(tx)})
            with self.assertRaises(ValueError):self.invoke('native_confirm',{'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'trial':TRIAL})

    def test_confirmation_must_carry_the_private_trial_number(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'RUNTIME',Path(d)),patch.object(agent,'PERSIST',Path(d)):
            pending={'state':'WAIT-CLIENT','tx':'a'*32,'expected_exit':'9.9.9.9','deadline':time.time()+60}
            agent.atomic_json(Path(d)/'native-status.json',pending)
            tx=dict(pending,phase='WAIT-CLIENT');agent.atomic_json(Path(d)/'native-transaction.json',{'schema':1,'data':tx,'sha256':agent.checksum(tx)})
            good={'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'trial':TRIAL}
            for bad in ({'trial':'d'*32},{'trial':''},{'trial':None},{'trial':TRIAL.upper()},{'trial':'x'*500}):
                with self.assertRaises(ValueError):self.invoke('native_confirm',dict(good,**bad))
                self.assertFalse((Path(d)/'native-confirm.json').exists())
            missing=dict(good);del missing['trial']
            with self.assertRaises(ValueError):self.invoke('native_confirm',missing)
            # Without a configured private trial number nothing can be confirmed, whatever the caller sends.
            for configured in (b'{"settings":{}}',b'{"settings":{"native_trial":""}}',b'{"settings":{"native_trial":"short"}}'):
                with patch.object(agent,'command',return_value=configured):
                    with self.assertRaises(ValueError):self.invoke('native_confirm',good)
            self.assertFalse((Path(d)/'native-confirm.json').exists())
            self.assertTrue(self.invoke('native_confirm',good)['accepted'])

    def test_trial_number_is_never_returned_by_public_status_or_inventory(self):
        root=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
        self.assertNotIn('native_trial',(root/'inventory.lua').read_text())

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
            with self.assertRaises(ValueError):self.invoke('native_confirm',{'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'trial':TRIAL})
            self.assertFalse((Path(d)/'native-confirm.json').exists())


if __name__=='__main__':unittest.main()
