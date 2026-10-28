import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import native_switch as native
import native_proof
import pair_auto as pair


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.runtime=root/'run';self.persist=root/'persist'
        self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,auto_control,native):
            for name,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,name):
                    p=patch.object(module,name,value);p.start();self.addCleanup(p.stop)
        self.revision=auto_control.current_revision()
        self.state=dict(id='a'*32,phase='RUNNING',owned=['wgclient1'],
            before_flags={'wgclient1':'1','ovpnclient1':'0'},network_identity='b'*64,
            protected={},process_bindings=None,order=['a','b'],policy_hash='c'*64,revision=self.revision)

    def test_pair_start_source_is_preserved_and_duplicate_cannot_relabel(self):
        self.assertTrue(pair.request(self.revision,request_source='test')['accepted'])
        self.assertEqual(pair.intent()['request_source'],'test')
        self.assertTrue(pair.request(self.revision,request_source='manual')['already_requested'])
        self.assertEqual(pair.intent()['request_source'],'test')
        self.assertEqual(auto_control.public_status()['activation_source'],'test')

    def test_retry_budget_is_rolling_and_survives_a_new_session(self):
        events=[100,200,300]
        kept,allowed=pair.budget(events,400)
        self.assertEqual(kept,events);self.assertFalse(allowed)
        self.assertEqual(pair.budget(events,1000),([200,300],True))
        self.assertEqual(pair.budget([401],400)[0],[400],'a future attempt (clock stepped back) counts as now');
        for bad in ([True],[float('nan')],None,[-1]):
            with self.assertRaises(ValueError):pair.budget(bad,400)

    def test_custom_window_preserves_attempts_for_later_policy_changes(self):
        events=[100,400,850];retained,allowed=pair.budget(events,1000,window=300,limit=2)
        self.assertEqual(retained,[400,850]);self.assertTrue(allowed)
        retained,allowed=pair.budget(retained,1000,window=900,limit=2)
        self.assertEqual(retained,[400,850]);self.assertFalse(allowed)
        self.assertTrue(pair.budget(retained,1000,window=900,limit=3)[1])
        for window,limit in ((59,3),(901,3),(900,0),(900,11),(True,3)):
            with self.assertRaises(ValueError):pair.budget(events,1000,window=window,limit=limit)

    def test_automatic_switch_uses_custom_attempt_policy_without_erasing_history(self):
        pair.request(self.revision);self.state['id']=pair.intent()['id'];pair.save(self.state)
        selection={'source':{'id':'a'},'target':{'id':'b'},'vendor_identity':'d'*64}
        backend=Mock();backend.diagnostic.return_value=([],selection);backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':[9800,9900]})
        settings={'pair_auto_mode':pair.MODE,'recovery_attempt_limit':'2','recovery_attempt_window':'5'}
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch('failover_plan.streak',return_value=True),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),patch.object(native,'publish'),patch.object(native,'attempt',side_effect=lambda *args,**kwargs:kwargs['on_dispatch']())as attempt,patch.object(pair,'configure_lease',return_value=20000):
            with patch.object(pair.time,'time',return_value=10000):pair.tick(backend,settings,self.revision)
            attempt.assert_not_called()
            with patch.object(pair.time,'time',return_value=10201):pair.tick(backend,settings,self.revision)
            attempt.assert_called_once()
        self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],[9800,9900,10201])

    def test_duplicate_start_is_idempotent_and_stop_revision_fences_it(self):
        first=pair.request(self.revision);saved=pair.intent()
        second=pair.request(self.revision)
        self.assertTrue(first['accepted']);self.assertTrue(second['already_requested'])
        self.assertEqual(pair.intent(),saved)
        new=auto_control.current_revision(rotate=True)
        self.assertFalse(pair.request(self.revision)['accepted'])
        with auto_control.control_lock():pair.stop_locked(new)
        self.assertIsNone(pair.public_intent())

    def test_display_phase_covers_queue_start_cleanup_and_terminal_failure(self):
        self.assertIsNone(pair.public_phase())
        pair.request(self.revision)
        self.assertEqual(pair.public_phase(),'STARTING')
        self.state.update(id=pair.intent()['id'],phase='STARTING')
        pair.save(self.state)
        self.assertEqual(pair.public_phase(),'STARTING')
        self.state['phase']='RUNNING';pair.save(self.state)
        self.assertEqual(pair.public_phase(),'RUNNING')
        with auto_control.control_lock():pair.stop_locked(self.revision)
        self.assertEqual(pair.public_phase(),'STOPPING')
        self.state['phase']='STOPPED';pair.save(self.state)
        self.assertEqual(pair.public_phase(),'STOPPED')
        pair.request(self.revision)
        self.assertEqual(pair.public_phase(),'STARTING')
        self.state.update(id=pair.intent()['id'],phase='FAILED');pair.save(self.state)
        self.assertEqual(pair.public_phase(),'FAILED')

    def test_unrecovered_owned_profiles_refuse_new_start(self):
        pair.save(self.state)
        self.assertIn('PAIR-RECOVERY-REQUIRED',pair.request(self.revision)['blockers'])

    def test_failed_start_stop_status_keeps_latest_request_timestamp(self):
        pair.request(self.revision)
        started=auto_control.public_status()
        self.assertEqual(started['requested'],'on')
        self.state.update(id=pair.intent()['id'],phase='STOPPED');pair.save(self.state)
        with auto_control.control_lock():pair.stop_locked(self.revision)
        stopped=auto_control.public_status()
        self.assertEqual(stopped['requested'],'off')
        self.assertEqual(stopped['pair_phase'],'STOPPED')
        self.assertGreaterEqual(stopped['requested_at'],started['requested_at'])
        self.assertEqual(stopped['requested_at'],pair.intent()['time'])

    def test_corrupt_state_never_becomes_fresh_start(self):
        pair.paths()[1].write_text('{"data":{},"sha256":"wrong"}')
        self.assertFalse(pair.request(self.revision)['accepted'])
        self.assertEqual(pair.paths()[1].read_text(),'{"data":{},"sha256":"wrong"}')

    def test_nested_invalid_ownership_refuses_even_with_valid_checksum(self):
        state=copy.deepcopy(self.state);state['owned']=[{}]
        pair.save(state)
        with self.assertRaisesRegex(ValueError,'PAIR-STATE-UNVERIFIED'):pair.read_state()

    def test_profile_identity_ignores_only_owned_disabled_flags(self):
        rows=[{'.name':'wgclient1','disabled':'1','config':'peer_1'},{'.name':'lan','ipaddr':'192.0.2.1'}]
        changed=copy.deepcopy(rows);changed[0]['disabled']='0'
        self.assertEqual(pair.normalized_network(rows),pair.normalized_network(changed))
        changed[0]['config']='peer_2'
        self.assertNotEqual(pair.normalized_network(rows),pair.normalized_network(changed))
        changed=copy.deepcopy(rows);changed[1]['ipaddr']='192.0.2.2'
        self.assertNotEqual(pair.normalized_network(rows),pair.normalized_network(changed))

    def test_external_policy_is_never_overwritten_by_stop(self):
        backend=Mock();backend.order.return_value=(['external','b'],'c'*64)
        with patch.object(native,'journal_read',return_value={}),patch.object(native,'command')as command:
            with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-POLICY-CHANGE'):pair.cleanup(backend,self.state)
            command.assert_not_called();backend.unguard.assert_not_called()

    def test_stop_on_unhealthy_primary_holds_reserve_and_never_stops_profiles(self):
        backend=Mock()
        with patch.object(native,'journal_read',return_value={'phase':'COMMITTED'}),patch.object(native,'finish_committed',return_value=False),patch.object(native,'command')as command:
            self.assertFalse(pair.cleanup(backend,self.state))
            self.assertEqual(pair.read_state()['phase'],'HELD')
            command.assert_not_called()

    def test_external_network_change_never_dispatches_ifdown(self):
        backend=Mock();backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[{'.name':'external'}]),patch.object(native,'command')as command:
            with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-NETWORK-CHANGE'):pair.cleanup(backend,self.state)
            command.assert_not_called()

    def test_restart_never_resumes_previous_intent(self):
        pair.request(self.revision);pair.save(self.state)
        with patch.object(pair,'cleanup')as cleanup:
            pair.recover(Mock())
        cleanup.assert_called_once();self.assertIsNone(pair.public_intent())

    def test_router_proof_never_matches_hosted_or_external(self):
        proof={'proof_scope':native_proof.ROUTER}
        for other in ({},{'proof_scope':native_proof.HOSTED}):
            self.assertFalse(native_proof.matches(proof,other))
            self.assertFalse(native_proof.matches(other,proof))
        with self.assertRaises(ValueError):native_proof.requested({'native_proof_scope':native_proof.ROUTER})
        self.assertEqual(native_proof.requested({'native_proof_scope':native_proof.ROUTER,'pair_auto_mode':pair.MODE}),pair.MODE)

    def test_observer_does_not_consume_an_attempt_or_claim_lan_certificate(self):
        self.state['id']=pair.request(self.revision)and pair.intent()['id'];pair.save(self.state)
        selection={'source':{'id':'a'},'target':{'id':'b'},'vendor_identity':'d'*64}
        backend=Mock();backend.diagnostic.return_value=([],selection)
        backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch('failover_plan.streak',return_value=False),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),patch.object(native,'publish')as publish,patch.object(native,'attempt')as attempt:
            self.assertTrue(pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision))
        attempt.assert_not_called();status=publish.call_args.args[0]
        self.assertEqual(status['state'],'OBSERVING');self.assertFalse(status['certified'])
        self.assertFalse(status['external_lan_verified']);self.assertTrue(status['readiness_verified'])
        self.assertFalse((self.persist/'pair-auto-budget.json').exists())

    def test_profile_ownership_is_durable_before_each_activation(self):
        request={'id':'a'*32,'revision':self.revision}
        selection={'source':{'id':'wireguard:peer_1','interface':'wgclient1'},'target':{'id':'openvpn:1_1','interface':'ovpnclient1'},
                   'source_rule':'a','target_rule':'b','direction':'first','process_bindings':None,'order':['a','b'],'hash':'c'*64}
        rows=[{'.name':k,'proto':v,'auto':'0','disabled':'1','config':'selected'}for k,v in pair.INTERFACES.items()]
        changed=[]
        def write(state,interface,value,revision):
            durable=pair.read_state()
            self.assertIn(interface,durable['owned']);self.assertEqual(durable['phase'],'STARTING')
            self.assertEqual(value,'0');changed.append(interface)
        backend=Mock();backend.devices.return_value=['wgclient1','ovpnclient1']
        with patch.object(pair,'preflight',return_value=selection),patch.object(pair,'network',return_value=rows),patch.object(pair,'configs',return_value={}),patch.object(pair,'quiet'),patch.object(pair,'set_disabled',side_effect=write),patch.object(native,'forward_dispatch')as dispatch:
            state=pair.begin(backend,{},request)
        self.assertEqual(changed,['wgclient1','ovpnclient1']);self.assertEqual(state['phase'],'RUNNING')
        self.assertEqual(dispatch.call_count,2)
        self.assertEqual([call.args[0] for call in dispatch.call_args_list],
                         [['ifup','-w','wgclient1'],['ifup','-w','ovpnclient1']])

    def test_stop_between_profile_starts_prevents_second_activation(self):
        request={'id':'a'*32,'revision':self.revision}
        selection={'source':{'id':'wireguard:peer_1','interface':'wgclient1'},'target':{'id':'openvpn:1_1','interface':'ovpnclient1'},
                   'source_rule':'a','target_rule':'b','direction':'first','process_bindings':None,'order':['a','b'],'hash':'c'*64}
        rows=[{'.name':k,'proto':v,'auto':'0','disabled':'1','config':'selected'}for k,v in pair.INTERFACES.items()]
        backend=Mock()
        with patch.object(pair,'preflight',return_value=selection),patch.object(pair,'network',return_value=rows),patch.object(pair,'configs',return_value={}),patch.object(pair,'quiet'),patch.object(pair,'set_disabled')as write,patch.object(native,'forward_dispatch',side_effect=lambda *a,**k:auto_control.current_revision(rotate=True)):
            with self.assertRaisesRegex(native.Refused,'CLIENT-STOP'):pair.begin(backend,{},request)
        self.assertEqual(write.call_count,1);self.assertEqual(pair.read_state()['owned'],['wgclient1'])

    def test_attempt_limit_recovers_with_time_without_reset_or_new_start(self):
        request=pair.request(self.revision);self.state['id']=pair.intent()['id'];pair.save(self.state)
        selection={'source':{'id':'a'},'target':{'id':'b'},'vendor_identity':'d'*64}
        backend=Mock();backend.diagnostic.return_value=([],selection)
        backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch('failover_plan.streak',return_value=True),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),patch.object(native,'publish'),patch.object(native,'attempt',side_effect=lambda *args,**kwargs:kwargs['on_dispatch']())as attempt,patch.object(pair,'configure_lease',return_value=20000):
            for stamp in (10000,10300,10600,10900,10901):
                with patch.object(pair.time,'time',return_value=stamp):pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision)
        # At the exact window boundary the oldest attempt expires. A new
        # Start does not grant a fresh budget; minimum dwell still applies.
        self.assertEqual(attempt.call_count,4)
        ledger=json.loads((self.persist/'pair-auto-budget.json').read_text())
        self.assertEqual(ledger['events'],[10300,10600,10900])

    def test_daemon_cli_and_imported_helpers_share_refused_and_stop(self):
        import subprocess
        root=Path(pair.__file__).parent
        code="""import sys,types,pathlib
sys.path.insert(0,sys.argv[1]);path=pathlib.Path(sys.argv[1])/'native_switch.py'
module=types.ModuleType('__main__');module.__file__=str(path);sys.modules['__main__']=module
sys.argv=[str(path),'invalid']
try:exec(compile(path.read_text(),str(path),'exec'),module.__dict__)
except SystemExit:pass
import native_switch,pair_auto
assert native_switch is module
module.STOP=True
try:pair_auto.require_running('invalid')
except module.Refused:pass
else:raise AssertionError('CLI/helper exceptions diverged')
"""
        result=subprocess.run([sys.executable,'-c',code,str(root)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def stopped_reserve(self,disabled='0',up=False,pending=False):
        """Running pair whose reserve client is enabled but not connected."""
        pair.request(self.revision);self.state.update(id=pair.intent()['id'],owned=[],started=1.0);pair.save(self.state)
        rows=[{'.name':'wgclient1','disabled':'0'},{'.name':'ovpnclient1','disabled':disabled}]
        status={'wgclient1':{'up':True},'ovpnclient1':{'up':up,'pending':pending,'available':True}}
        def ubus(args,timeout=5):return json.dumps(status[args[2].rsplit('.',1)[1]]).encode()
        backend=Mock();backend.devices.return_value=['wgclient1','ovpnclient1']
        backend.diagnostic.return_value=(['PROFILE-IDENTITY-CHANGED'],None)
        return backend,rows,ubus

    def tick_at(self,backend,rows,ubus,stamp,journal=None):
        with patch.object(native,'journal_read',return_value=journal or {}),patch.object(pair,'network',return_value=rows),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch.object(native,'command',side_effect=ubus),patch.object(native,'publish')as publish,patch.object(native,'forward_dispatch')as dispatch,patch.object(pair,'quiet')as quiet,patch.object(pair.time,'time',return_value=stamp):
            pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision)
        return dispatch,publish,quiet

    def test_enabled_but_stopped_reserve_is_started_instead_of_blocking_the_pair(self):
        backend,rows,ubus=self.stopped_reserve()
        dispatch,publish,quiet=self.tick_at(backend,rows,ubus,10000)
        dispatch.assert_called_once_with(['ifup','-w','ovpnclient1'],self.revision,timeout=20)
        quiet.assert_called_once_with(45,self.revision)
        backend.diagnostic.assert_not_called()
        backend.guard.assert_called_once_with(['wgclient1','ovpnclient1'],control_revision=self.revision)
        self.assertEqual(pair.read_state()['owned'],['ovpnclient1'])
        self.assertEqual(pair.read_state()['phase'],'RUNNING')

    def test_stopped_client_attempts_are_paused_and_bounded_then_recover_with_time(self):
        backend,rows,ubus=self.stopped_reserve()
        started=[]
        for stamp in (10000,10050,10121,10242,10363,10484,10901):
            dispatch,_,_=self.tick_at(backend,rows,ubus,stamp)
            if dispatch.called:started.append(stamp)
        # 10050 waits for the pause; 10484 hits the four-per-window limit;
        # the 10000 attempt leaves the 900 s window before 10901.
        self.assertEqual(started,[10000,10121,10242,10363,10901])

    def test_operator_disabled_or_connecting_client_is_never_started(self):
        for kwargs in ({'disabled':'1'},{'pending':True},{'up':True}):
            with self.subTest(kwargs):
                (self.runtime/'pair-revive.json').unlink(missing_ok=True)
                backend,rows,ubus=self.stopped_reserve(**kwargs)
                dispatch,_,_=self.tick_at(backend,rows,ubus,10000)
                dispatch.assert_not_called();backend.diagnostic.assert_called_once()

    def test_unconnected_reserve_is_waiting_during_start_window_then_a_real_blocker(self):
        backend,rows,ubus=self.stopped_reserve(up=True)
        backend.diagnostic.return_value=(['RESERVE-NOT-CONNECTED'],None)
        for started,expected in ((9950,'ARMED'),(1.0,'BLOCKED')):
            self.state['started']=started;pair.save(self.state)
            _,publish,_=self.tick_at(backend,rows,ubus,10000)
            self.assertEqual(publish.call_args.args[0]['state'],expected)
            self.assertEqual(publish.call_args.args[0]['blockers'],['RESERVE-NOT-CONNECTED'])

    def test_stopped_client_is_not_started_during_a_transaction(self):
        backend,rows,ubus=self.stopped_reserve()
        dispatch,_,_=self.tick_at(backend,rows,ubus,10000,journal={'phase':'APPLYING'})
        dispatch.assert_not_called()

    def test_failed_client_start_neither_fails_nor_blocks_the_running_pair(self):
        import subprocess
        backend,rows,ubus=self.stopped_reserve()
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=rows),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch.object(native,'command',side_effect=ubus),patch.object(native,'publish')as publish,patch.object(native,'forward_dispatch',side_effect=subprocess.CalledProcessError(1,'ifup')),patch.object(pair,'quiet')as quiet:
            self.assertTrue(pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision))
        publish.assert_not_called();quiet.assert_not_called()
        self.assertEqual(pair.read_state()['phase'],'RUNNING')

    def test_start_brings_up_an_enabled_but_stopped_client_and_restores_it_on_stop(self):
        request={'id':'a'*32,'revision':self.revision}
        selection={'source':{'id':'wireguard:peer_1','interface':'wgclient1'},'target':{'id':'openvpn:1_1','interface':'ovpnclient1'},
                   'source_rule':'a','target_rule':'b','direction':'first','process_bindings':None,'order':['a','b'],'hash':'c'*64}
        rows=[{'.name':k,'proto':v,'auto':'0','disabled':'0','config':'selected'}for k,v in pair.INTERFACES.items()]
        status={'wgclient1':{'up':True},'ovpnclient1':{'up':False,'pending':False}}
        def ubus(args,timeout=5):return json.dumps(status[args[2].rsplit('.',1)[1]]).encode()
        backend=Mock();backend.devices.return_value=['wgclient1']
        with patch.object(pair,'preflight',return_value=selection),patch.object(pair,'network',return_value=rows),patch.object(pair,'configs',return_value={}),patch.object(pair,'quiet'),patch.object(pair,'set_disabled')as write,patch.object(native,'command',side_effect=ubus),patch.object(native,'forward_dispatch')as dispatch:
            state=pair.begin(backend,{},request)
        write.assert_not_called()
        self.assertEqual([call.args[0] for call in dispatch.call_args_list],[['ifup','-w','ovpnclient1']])
        self.assertEqual(state['owned'],['ovpnclient1']);self.assertEqual(state['before_flags']['ovpnclient1'],'0')
        self.assertEqual(pair.read_state()['owned'],['ovpnclient1'])

    def test_vendor_exit_options_are_not_an_external_firewall_edit(self):
        base=b"config zone\n\toption name 'wan'\n\toption gl_wan_like '1'\nconfig zone\n\toption name 'ovpnclient2'\n"
        up=base+b"\toption gl_wan_like '1'\r\n\toption gl_bwa_managed '1'\n\toption gl_bwa_exit_id 'ovpnclient2'\n\toption gl_bwa_bridge_reject '0'\n"
        self.assertEqual(pair.config_digest('firewall',base),pair.config_digest('firewall',up))
        self.assertNotEqual(pair.config_digest('firewall',base),pair.config_digest('firewall',base+b"\toption src 'lan'\n"))
        self.assertNotEqual(pair.config_digest('firewall',base),pair.config_digest('firewall',base.replace(b'wan',b'lan')))
        self.assertNotEqual(pair.config_digest('network',base),pair.config_digest('network',up))

    def test_stop_lets_ifdown_undo_the_firewall_edit_but_not_other_config_drift(self):
        self.state.update(owned=['ovpnclient1'],protected={'firewall':'a'*64,'dhcp':'b'*64})
        backend=Mock();backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={'firewall':'c'*64,'dhcp':'b'*64}),patch.object(native,'command')as command,patch.object(pair,'quiet'),patch.object(pair,'set_disabled')as write:
            self.assertTrue(pair.cleanup(backend,self.state))
            command.assert_called_once_with(['ifdown','ovpnclient1'],timeout=20);write.assert_called_once()
        self.state.update(phase='RUNNING',owned=['ovpnclient1'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={'firewall':'a'*64,'dhcp':'d'*64}),patch.object(native,'command')as command,patch.object(pair,'quiet'):
            with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-CONFIG-CHANGE'):pair.cleanup(backend,self.state)
            command.assert_not_called()

    def test_stopped_stock_leftover_clients_do_not_count_as_external_network_change(self):
        managed={'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}
        net=[{'.name':'lan','ipaddr':'1'},{'.name':'ovpnclient1','disabled':'1'},{'.name':'wgclient1','disabled':'0'},{'.name':'ovpnclient2','disabled':'0'}]
        without=[net[0],net[2],net[3]]
        self.assertEqual(pair.normalized_network(net,managed),pair.normalized_network(without,managed))
        self.assertNotEqual(pair.normalized_network(net,managed),pair.normalized_network([net[0],net[1],net[2]],managed))
        self.assertNotEqual(pair.normalized_network([net[0],dict(net[1],disabled='0'),net[2],net[3]],managed),pair.normalized_network(without,managed))
        self.assertNotEqual(pair.normalized_network(net,managed),pair.normalized_network([dict(net[0],ipaddr='2')]+net[1:],managed))

    def test_stopped_stock_leftover_dnsmasq_sections_are_not_an_external_dhcp_edit(self):
        before=b"config dnsmasq 'lan'\n\toption port '53'\n\nconfig dnsmasq 'ovpnclient1'\n\toption port '4153'\n\toption disabled '1'\n\nconfig dnsmasq 'wgclient1'\n\toption port '4154'\n"
        after=b"config dnsmasq 'lan'\n\toption port '53'\n\nconfig dnsmasq 'wgclient1'\n\toption port '4154'\n"
        managed={'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}
        self.assertEqual(pair.config_digest('dhcp',before,managed),pair.config_digest('dhcp',after,managed))
        self.assertNotEqual(pair.config_digest('dhcp',before.replace(b"'1'",b"'0'"),managed),pair.config_digest('dhcp',after,managed))
        self.assertNotEqual(pair.config_digest('dhcp',after+b"\nconfig dnsmasq 'ovpnclient2'\n\toption disabled '1'\n",managed),pair.config_digest('dhcp',after,managed))
        self.assertNotEqual(pair.config_digest('dhcp',after.replace(b'4154',b'4155'),managed),pair.config_digest('dhcp',after,managed))

    def held_session(self,code='PAIR-EXTERNAL-POLICY-CHANGE'):
        pair.request(self.revision);self.state.update(id=pair.intent()['id'],phase='HELD',owned=[],recovery_error=code,started=1.0);pair.save(self.state)
        with auto_control.control_lock():pair.stop_locked(self.revision)

    def test_start_hands_over_a_session_held_only_by_an_outside_change(self):
        self.held_session()
        with patch.object(native,'journal_read',return_value={'phase':'ROLLED-BACK'}):
            reply=pair.request(self.revision)
        self.assertTrue(reply['accepted']);self.assertNotIn('blockers',reply)
        saved=pair.read_state();self.assertEqual(saved['phase'],'STOPPED');self.assertEqual(saved['owned'],[])
        self.assertEqual(saved['operator_resolution']['reason'],'AUTOMATIC-EXTERNAL-CHANGE-READOPT');self.assertFalse(saved['operator_resolution']['old_flags_restored'])
        archives=list((self.persist/'session-recovery').glob('pair-'+self.state['id']+'-readopt-*.json'));self.assertEqual(len(archives),1)
        self.assertEqual(json.loads(archives[0].read_text())['data']['phase'],'HELD')

    def test_handover_never_applies_to_a_reserve_hold_unknown_codes_or_an_exhausted_budget(self):
        for code,journal,events in (('PAIR-EXTERNAL-POLICY-CHANGE',{'phase':'HELD-ON-RESERVE'},[]),('PAIR-STATE-UNVERIFIED',{'phase':'ROLLED-BACK'},[]),('PAIR-EXTERNAL-POLICY-CHANGE',{'phase':'ROLLED-BACK'},[9990,9991,9992])):
            with self.subTest(code=code,journal=journal,events=events):
                (self.runtime/'pair-readopt.json').unlink(missing_ok=True)
                for path in pair.paths():path.unlink(missing_ok=True)
                if events:agent.atomic_json(self.runtime/'pair-readopt.json',{'events':events})
                self.held_session(code)
                with patch.object(native,'journal_read',return_value=journal),patch.object(pair.time,'time',return_value=10000):
                    self.assertEqual(pair.request(self.revision)['blockers'],['PAIR-RECOVERY-REQUIRED'])
                self.assertEqual(pair.read_state()['phase'],'HELD')

    def test_running_session_adopts_a_change_made_outside_the_app_and_starts_again_by_itself(self):
        pair.request(self.revision);first=pair.intent()['id'];self.state.update(id=first,phase='RUNNING',owned=[],started=1.0);pair.save(self.state)
        backend=Mock();backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value='f'*64),patch.object(pair,'configs',return_value={}),patch.object(native,'publish')as publish:
            self.assertTrue(pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision))
        self.assertEqual(pair.read_state()['phase'],'STOPPED')
        row=pair.intent();self.assertEqual(row['mode'],'on');self.assertNotEqual(row['id'],first);self.assertEqual(row['revision'],self.revision)
        self.assertEqual(publish.call_args.args[0]['reason'],'PAIR-READOPTED')
        # A persistent conflict is not retried forever: after the budget the ordinary held state returns.
        for _ in range(pair.READOPT_LIMIT+1):
            state=pair.read_state();pair.request(self.revision) if pair.intent().get('mode')!='on' else None
            state.update(id=pair.intent()['id'],phase='RUNNING',owned=[]);pair.save(state)
            with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value='f'*64),patch.object(pair,'configs',return_value={}),patch.object(native,'publish'):
                pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision)
        self.assertEqual(pair.read_state()['phase'],'HELD');self.assertEqual(pair.read_state()['recovery_error'],'PAIR-EXTERNAL-NETWORK-CHANGE')

    def test_renaming_a_tunnel_does_not_change_the_policy_identity(self):
        a={'.name':'cfg0592bd','.anonymous':True,'.type':'rule','name':'Tunnel 4','via':'ovpnclient2','enabled':'1','tunnel_id':'4192'}
        b=dict(a,name='OpenVPN');c=dict(a,via='wgclient1')
        self.assertEqual(native.policy_order([a]),native.policy_order([b]));self.assertEqual(native.policy_hash([a]),native.policy_hash([b]))
        self.assertNotEqual(native.policy_hash([a]),native.policy_hash([c]))


    def test_failed_start_and_held_session_name_their_code_in_the_public_status(self):
        pair.request(self.revision);row=pair.intent();self.state.update(id=row['id'],phase='STOPPED');pair.save(self.state)
        self.assertIsNone(auto_control.public_status()['failure'])
        self.assertTrue(pair.fail_request(row,self.revision,ValueError('PAIR-EXTERNAL-POLICY-CHANGE')))
        failure=auto_control.public_status()['failure'];self.assertEqual(failure['code'],'PAIR-EXTERNAL-POLICY-CHANGE');self.assertGreater(failure['time'],0)
        for path in pair.paths():path.unlink(missing_ok=True)
        self.state.update(phase='HELD',recovery_error='PAIR-EXTERNAL-NETWORK-CHANGE',started=5.0);pair.save(self.state)
        self.assertEqual(auto_control.public_status()['failure']['code'],'PAIR-EXTERNAL-NETWORK-CHANGE')


    def test_failed_primary_with_reserve_already_first_keeps_auto_running(self):
        pair.request(self.revision);self.state['id']=pair.intent()['id'];pair.save(self.state)
        selection={'source':{'id':'a'},'target':{'id':'b'},'vendor_identity':'d'*64,'order':['t','s'],'source_rule':'s','target_rule':'t','direction':'first'}
        backend=Mock();backend.diagnostic.return_value=([],selection);backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=self.state['network_identity']),patch.object(pair,'configs',return_value={}),patch('failover_plan.streak',return_value=True),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),patch.object(native,'publish')as publish,patch.object(native,'attempt')as attempt:
            self.assertTrue(pair.tick(backend,{'pair_auto_mode':pair.MODE},self.revision))
        attempt.assert_not_called();self.assertEqual(publish.call_args.args[0]['reason'],'RESERVE-ALREADY-FIRST');self.assertEqual(pair.intent()['mode'],'on')


if __name__=='__main__':unittest.main()
