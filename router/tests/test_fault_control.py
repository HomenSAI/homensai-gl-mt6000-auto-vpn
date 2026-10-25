from contextlib import nullcontext,contextmanager,ExitStack
from pathlib import Path
import copy
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import fault_control as fault
import recovery_settings as recovery
from test_native_switch import fixture
import native_switch as native

class FaultTests(unittest.TestCase):
    @contextmanager
    def pair_context(self,reserve=False):
        import pair_auto as pair,pair_manual,auto_control
        from failure_diagnosis import profile_identity
        data,status,state,settings,selection,certificate=self.context()
        settings['pair_auto_mode']=pair.MODE
        state.update(state='COMMITTED' if reserve else 'OBSERVING',certified=False,readiness_verified=not reserve)
        owned={'phase':'RUNNING','id':'e'*32,'revision':'d'*32,'process_bindings':{},'network_identity':'network',
               'protected':{'vpn':'config'},'order':['primary','reserve'],'policy_hash':'hash'}
        requested={'mode':'on','id':'e'*32,'revision':'d'*32}
        journal={'phase':'COMMITTED','confirmed':990,'control_revision':'d'*32,'after':['reserve','primary'],'hash':'hash',
                 'source':selection['source']['id'],'target':selection['target']['id'],
                 'vendor_profiles':{k:profile_identity(selection[k]) for k in ('source','target')}} if reserve else {}
        backend=MagicMock();backend.order.return_value=(journal['after'] if reserve else owned['order'],'hash')
        with ExitStack() as stack:
            for obj,name,kwargs in ((pair,'read_state',{'return_value':owned}),(pair,'intent',{'return_value':requested}),
                    (pair,'network',{'return_value':{}}),(pair,'normalized_network',{'return_value':'network'}),
                    (pair,'configs',{'return_value':{'vpn':'config'}}),(pair_manual,'read',{'return_value':{}}),
                    (auto_control,'current_revision',{'return_value':'d'*32}),(native,'Linux',{'return_value':backend}),
                    (native,'journal_read',{'return_value':journal})):
                stack.enter_context(patch.object(obj,name,**kwargs))
            yield data,status,state,settings,selection,owned,requested,journal,backend

    def test_pair_fault_automatically_uses_actual_primary_or_reserve_without_lan_certificate(self):
        for reserve in (False,True):
            with self.subTest(reserve=reserve),self.pair_context(reserve) as ctx:
                data,status,state,settings,selection,*_=ctx
                selected='target' if reserve else 'source';args=dict(self.args(),profile=selection[selected]['id'])
                rows=fault.eligibility(args,data,status,state,settings,selection,[],1000,{})
                self.assertEqual([p['id'] for p in rows],[args['profile']])
                wrong=dict(args,profile=selection['source' if reserve else 'target']['id'])
                with self.assertRaisesRegex(fault.FaultError,'NOT-CURRENT'):
                    fault.eligibility(wrong,data,status,state,settings,selection,[],1000,{})

    def test_pair_fault_rejects_stopped_intent_changed_policy_and_unconfirmed_reserve(self):
        for case in ('stop','policy','unconfirmed','generation','health'):
            with self.subTest(case=case),self.pair_context(True) as ctx:
                data,status,state,settings,selection,owned,requested,journal,backend=ctx
                if case=='stop':requested['mode']='off'
                if case=='policy':backend.order.return_value=(['unexpected'],'hash')
                if case=='unconfirmed':journal['confirmed']=None
                if case=='generation':journal['vendor_profiles']['target']['vendor_generation']='f'*32
                if case=='health':status['profiles'][0]['code']='DNS-001'
                with self.assertRaises(fault.FaultError):
                    fault.eligibility(dict(self.args(),profile=selection['target']['id']),data,status,state,settings,selection,[],1000,{})

    def test_transition_needs_fresh_opposite_health_and_private_route_confirmation(self):
        from failure_diagnosis import profile_identity
        for reserve in (False,True):
            with self.subTest(reserve=reserve),self.pair_context(reserve) as ctx:
                data,status,state,settings,selection,owned,requested,journal,backend=ctx
                # This context represents the destination after switching.
                if not reserve:journal['phase']='ROLLED-BACK'
                value={'phase':'ACTIVE','pair_mode':True,'started':980,'control_revision':'d'*32,
                       'fault_role':'source' if reserve else 'target',
                       'vendor_profiles':{k:profile_identity(selection[k]) for k in ('source','target')}}
                def read(path,default=None):return state if path.name=='native-status.json' else status
                with patch.object(fault,'read_json',side_effect=read):
                    self.assertTrue(fault.transition_confirmed(value,1000))
                    destination=1 if reserve else 0
                    status['profiles'][destination]['time']=970
                    self.assertFalse(fault.transition_confirmed(value,1000),'pre-test sample cannot prove transition')
                    status['profiles'][destination]['time']=1000
                    backend.order.return_value=(['external'],'changed')
                    self.assertFalse(fault.transition_confirmed(value,1000),'UI/native hints alone cannot prove actual policy')

    def test_only_active_unexpired_uncancelled_fault_marks_a_tested_profile(self):
        value={'phase':'ACTIVE','pair_mode':True,'nonce':'a'*32,'control_revision':'d'*32,
               'monotonic_until':200,'profiles':['current'],'control_settings':{}}
        with patch.object(fault,'load',return_value=value),patch.object(fault,'require_revision'),patch.object(fault,'require_auto_on'),patch.object(fault.time,'monotonic',return_value=100),patch.object(fault,'read_json',return_value={}) as read:
            self.assertTrue(fault.testing_profile('current'));self.assertFalse(fault.testing_profile('other'))
            value['phase']='ARMED';self.assertFalse(fault.testing_profile('current'))
            value['phase']='ACTIVE';value['monotonic_until']=100;self.assertFalse(fault.testing_profile('current'))
            value['monotonic_until']=200;read.return_value={'nonce':'a'*32};self.assertFalse(fault.testing_profile('current'))

    def args(self):return {'profile':'wireguard:peer_1','scope':'profile','duration':60}
    def context(self):
        from vendor_fixture import attach
        rows=[{'id':'wireguard:peer_'+str(i),'section':'peer_'+str(i),'protocol':'wireguard','interface':'wg'+str(i),
               'channel':'Main' if i==1 else 'Reserve','code':None,'dns_ok':True,'https_success':2,
               'device':'wg'+str(i),'mark':4096*i,'table':str(1000+i),'ifindex':i+6} for i in (1,2)]
        status=attach({'profiles':rows},1000)
        selection={'source':copy.deepcopy(rows[0]),'target':copy.deepcopy(rows[1]),'vendor_identity':'a'*64,
                   'hash':'b'*64,'direction':'first','settings_hash':'c'*64}
        for role in ('source','target'):
            selection[role]['kernel_binding']={key:selection[role][key] for key in ('device','mark','table','ifindex')}
        state={'state':'OBSERVING','certified':True,'time':995,'source':rows[0]['id'],'target':rows[1]['id'],'vendor_identity':'a'*64}
        settings={'native_session_loss':'1','native_until':'2000','interval':30,'plan_source':rows[0]['id'],'plan_target':rows[1]['id'],
                  'plan_source_tunnel':'wireguard:wg1','plan_target_tunnel':'wireguard:wg2','native_enabled':'1','native_trial':'trial'}
        certificate={key:selection[key] for key in ('vendor_identity','hash','direction','settings_hash')}
        certificate.update(source=rows[0]['id'],target=rows[1]['id'],until=2000)
        return {'profiles':copy.deepcopy(rows)},status,state,settings,selection,certificate
    def eligibility(self,args=None,mutation=None):
        data,status,state,settings,selection,certificate=self.context()
        if mutation:mutation(status,state,settings,selection)
        return fault.eligibility(args or self.args(),data,status,state,settings,selection,[],1000,certificate)
    def test_only_certified_fresh_current_source_with_healthy_reserve(self):
        self.assertEqual(self.eligibility()[0]['id'],'wireguard:peer_1')
        mutations=[lambda s,n,c,p:n.update(certified=False),lambda s,n,c,p:n.update(state='COMMITTED'),lambda s,n,c,p:s.update(time=1),lambda s,n,c,p:c.update(native_session_loss='0'),lambda s,n,c,p:c.update(native_until='1050'),lambda s,n,c,p:s['profiles'][1].update(code='VPN-003'),lambda s,n,c,p:p['source'].update(id='b')]
        for mutation in mutations:
            with self.assertRaises(fault.FaultError):self.eligibility(mutation=mutation)
    def test_same_editable_label_on_other_tunnel_does_not_expand_fault_scope(self):
        rows=self.eligibility(dict(self.args(),scope='channel'),lambda s,n,c,p:s['profiles'][1].update(channel='Main'))
        self.assertEqual([row['id'] for row in rows],['wireguard:peer_1'])
    def test_bad_scope_duration_or_extra_fields_rejected(self):
        for changes in ({'duration':181},{'duration':True},{'duration':10},{'scope':'wan'},{'extra':1}):
            with self.assertRaises(fault.FaultError):self.eligibility(dict(self.args(),**changes))
    def test_stale_certificate_conflicting_binding_and_generation_are_refused(self):
        for mode in ('certificate','binding','generation'):
            data,status,state,settings,selection,certificate=self.context()
            if mode=='certificate':certificate['vendor_identity']='f'*64
            if mode=='binding':data['profiles'].append(dict(data['profiles'][0],id='wireguard:peer_3',section='peer_3'))
            if mode=='generation':selection['source']['vendor_generation']='f'*32
            with self.subTest(mode=mode),self.assertRaises(fault.FaultError):
                fault.eligibility(self.args(),data,status,state,settings,selection,[],1000,certificate)
    def test_vendor_new_current_member_needs_new_matching_certificate(self):
        data,status,state,settings,selection,certificate=self.context()
        for row in (data['profiles'][0],status['profiles'][0],selection['source']):row.update(id='wireguard:peer_3',section='peer_3')
        group=status['vendor_observation']['groups'][0];group.update(current_profile='wireguard:peer_3',active_profiles=['wireguard:peer_3'])
        with self.assertRaisesRegex(fault.FaultError,'NOT-CURRENT'):
            fault.eligibility(self.args(),data,status,state,settings,selection,[],1000,certificate)
        with self.assertRaisesRegex(fault.FaultError,'CERTIFICATE'):
            fault.eligibility(dict(self.args(),profile='wireguard:peer_3'),data,status,state,settings,selection,[],1000,certificate)

    @contextmanager
    def launch(self,stop_at=None,watchdog=True,apply_error=False,old=None,pair_role=None):
        data,status,state,settings,selection,certificate=self.context();held=[];current=[copy.deepcopy(old) or {}]
        if pair_role:
            settings['pair_auto_mode']='router-probed-ipv4'
            state.update(state='COMMITTED' if pair_role=='target' else 'OBSERVING',certified=False,readiness_verified=pair_role=='source')
        files={'auto-control-revision.json':{'revision':'d'*32},'status.json':status,'native-status.json':state,
               'native-certificate.json':certificate}
        calls={'applied':0,'cleanups':[],'diagnostic':0}
        @contextmanager
        def lock():
            self.assertFalse(held);held.append(True)
            try:yield
            finally:held.pop()
        def stop():files['auto-control-revision.json']={'revision':'e'*32}
        def read(path,default=None):
            if path.name=='fault-ready.json':return {'nonce':current[0]['nonce'],'pid':321} if watchdog else {}
            return copy.deepcopy(files.get(path.name,default))
        def store(value):current[0]=copy.deepcopy(value)
        def write(path,value):files[path.name]=copy.deepcopy(value)
        def snapshot():self.assertFalse(held);return copy.deepcopy(data)
        def diagnostic():
            self.assertFalse(held);calls['diagnostic']+=1
            if stop_at=='diagnostic':stop()
            return [],copy.deepcopy(selection)
        def binding(logical):
            self.assertFalse(held)
            return dict(next(row for row in selection.values() if isinstance(row,dict) and row.get('interface')==logical)['kernel_binding'],code=None)
        class Engine:
            def cleanup(inner,nonce,**kwargs):self.assertFalse(held);calls['cleanups'].append(nonce);return True
            def apply(inner,devices,duration,nonce,commit_guard):
                self.assertFalse(held)
                calls['devices']=devices
                if stop_at=='preflight':stop()
                with commit_guard():
                    self.assertTrue(held);calls['applied']+=1
                    if apply_error:raise fault.FaultError('FAULT-TIMEOUT-RULE-FAILED')
                if stop_at=='after_apply':stop()
        backend=MagicMock();backend.diagnostic.side_effect=diagnostic;backend.policy.return_value={'settings':settings}
        backend.order.return_value=(['reserve','primary'] if pair_role=='target' else ['primary','reserve'],'hash')
        worker=MagicMock(pid=321);worker.poll.return_value=None if watchdog else 0
        with ExitStack() as stack:
            for obj,name,kwargs in ((fault,'control_lock',{'side_effect':lock}),(fault,'load',{'side_effect':lambda:copy.deepcopy(current[0])}),
                    (fault,'store',{'side_effect':store}),(fault,'read_json',{'side_effect':read}),(fault,'atomic_json',{'side_effect':write}),
                    (fault,'inventory',{'side_effect':snapshot}),(fault,'route_binding',{'side_effect':binding}),
                    (fault,'Nft',{'return_value':Engine()}),(fault,'event',{'return_value':None}),
                    (native,'Linux',{'return_value':backend}),(fault.time,'time',{'return_value':1000}),
                    (fault.time,'monotonic',{'return_value':100}),(fault.subprocess,'Popen',{'return_value':worker})):
                stack.enter_context(patch.object(obj,name,**kwargs))
            stack.enter_context(patch('auto_control.revision_locked',return_value='d'*32))
            yield calls,current,files

    def test_slow_preflight_is_unlocked_and_one_install_is_fenced_by_claim(self):
        with self.launch() as (calls,current,files):answer=fault.start(self.args())
        self.assertTrue(answer['accepted']);self.assertEqual(calls['applied'],1);self.assertEqual(current[0]['phase'],'ACTIVE')
    def test_pair_launch_blocks_only_actual_selected_device_in_both_directions(self):
        for reserve in (False,True):
            with self.subTest(reserve=reserve),self.pair_context(reserve),self.launch(pair_role='target' if reserve else 'source') as (calls,current,files):
                answer=fault.start(dict(self.args(),profile='wireguard:peer_2' if reserve else 'wireguard:peer_1'))
                self.assertTrue(answer['accepted']);self.assertEqual(calls['devices'],['wg2' if reserve else 'wg1'])
                self.assertEqual(current[0]['fault_role'],'target' if reserve else 'source')
    def test_stop_during_checks_or_before_dispatch_prevents_install_and_releases_claim(self):
        for when in ('diagnostic','preflight'):
            with self.subTest(when=when),self.launch(stop_at=when) as (calls,current,files):
                with self.assertRaises(fault.FaultError):fault.start(self.args())
                self.assertEqual(calls['applied'],0)
                self.assertIs(files['fault-result.json']['cleaned'],True)
                self.assertEqual(files['fault-result.json']['nonce'],current[0]['nonce'])
    def test_stop_after_dispatched_install_cleans_inflight_generation_without_active_ack(self):
        with self.launch(stop_at='after_apply') as (calls,current,files):
            with self.assertRaises(fault.FaultError):fault.start(self.args())
            self.assertEqual(calls['applied'],1);self.assertIs(files['fault-result.json']['cleaned'],True)
            self.assertNotEqual(current[0]['phase'],'ACTIVE')
    def test_watchdog_failure_and_apply_failure_release_owned_claim(self):
        for kwargs in ({'watchdog':False},{'apply_error':True}):
            with self.subTest(kwargs=kwargs),self.launch(**kwargs) as (calls,current,files):
                with self.assertRaises(fault.FaultError):fault.start(self.args())
                self.assertIs(files['fault-result.json']['cleaned'],True)
                self.assertNotEqual(current[0]['phase'],'ACTIVE')
    def test_concurrent_live_claim_is_not_overwritten(self):
        old={'nonce':'f'*32,'phase':'PREPARING','monotonic_until':200}
        with self.launch(old=old) as (calls,current,files):answer=fault.start(self.args())
        self.assertEqual(answer,{'accepted':False,'code':'FAULT-ALREADY-ACTIVE'})
        self.assertEqual(current[0],old);self.assertEqual(calls['applied'],0)
    def test_stop_latch_blocks_old_certified_public_hint(self):
        with self.launch() as (calls,current,files):
            files['native-stop.json']={'trial':'trial','requested':999}
            with self.assertRaisesRegex(fault.FaultError,'CERTIFIED-AUTO'):fault.start(self.args())
            self.assertEqual(calls['applied'],0);self.assertIs(files['fault-result.json']['cleaned'],True)
    def test_missing_or_corrupt_control_marker_never_mints_a_new_fault_claim(self):
        for marker in ({},{'revision':'bad'},[],{'revision':'d'*32,'extra':True}):
            with self.subTest(marker=marker),self.launch() as (calls,current,files):
                files['auto-control-revision.json']=marker
                with self.assertRaisesRegex(fault.FaultError,'CONTROL-CHANGED'):fault.start(self.args())
                self.assertEqual(current[0],{});self.assertEqual(calls['applied'],0)
    def test_real_nft_dispatch_is_locked_but_preflight_and_wait_are_not(self):
        held=[];calls=[]
        @contextmanager
        def guard():
            held.append(True)
            try:yield
            finally:held.pop()
        def preflight(*args,**kwargs):
            self.assertFalse(held);calls.append('preflight');return MagicMock(returncode=0)
        def spawn(*args,**kwargs):
            self.assertTrue(held);calls.append('spawn')
            process=MagicMock()
            def wait(**kw):self.assertFalse(held);calls.append('wait');return 0
            process.wait.side_effect=wait
            return process
        with tempfile.TemporaryDirectory() as directory,patch.object(fault,'RUNTIME',Path(directory)),\
                patch.object(fault.Nft,'contents',side_effect=[None,fault.MARKER+'a'*32]),\
                patch.object(fault.subprocess,'run',side_effect=preflight),patch.object(fault.subprocess,'Popen',side_effect=spawn):
            fault.Nft().apply(['wg0'],60,'a'*32,commit_guard=guard)
        self.assertEqual(calls,['preflight','spawn','wait'])
    def test_cleanup_cannot_delete_a_replacement_claim(self):
        with patch.object(fault.Nft,'contents',return_value=fault.MARKER+'a'*32),\
                patch.object(fault,'control_lock',return_value=nullcontext()),\
                patch.object(fault,'load',return_value={'nonce':'b'*32,'phase':'ACTIVE'}),\
                patch.object(fault.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(fault.FaultError,'CLAIM-STALE'):fault.Nft().cleanup('a'*32)
        spawn.assert_not_called()
    def test_active_worker_cleans_original_scope_when_identity_is_gone(self):
        value={'nonce':'a'*32,'monotonic_until':200,'control_revision':'d'*32}
        with patch.object(fault,'load',return_value=value),patch.object(fault.time,'monotonic',return_value=100),\
                patch.object(fault,'control_lock',return_value=nullcontext()),patch.object(fault,'atomic_json') as write,\
                patch.object(fault,'read_json',return_value={}),patch.object(fault,'require_revision'),\
                patch.object(fault,'verify_bindings',side_effect=fault.FaultError('FAULT-IDENTITY-GONE')),\
                patch.object(fault,'event'),patch.object(fault,'Nft') as engine:
            fault.worker('a'*32)
        engine.return_value.cleanup.assert_called_once_with('a'*32)
        self.assertEqual(write.call_args.args[1]['code'],'FAULT-IDENTITY-GONE')
        self.assertIs(write.call_args.args[1]['cleaned'],True)
    def test_nft_timeout_wait_and_kill_are_bounded_and_never_confirm_install(self):
        import subprocess
        process=MagicMock();process.wait.side_effect=subprocess.TimeoutExpired('owned-nft',5)
        with self.assertRaisesRegex(fault.FaultError,'COMMAND-UNCONFIRMED'):fault.wait_nft(process)
        self.assertEqual([call.kwargs['timeout'] for call in process.wait.call_args_list],[5,1])
        process.kill.assert_called_once_with()
    def test_kernel_timeout_present_on_every_drop_scope_and_no_input_chain(self):
        value=fault.script(['wg0','tun0'],60,'a'*32)
        self.assertNotIn('set devices',value);self.assertIn('set fault_devs',value)
        self.assertIn('flags timeout',value);self.assertIn('"wg0" timeout 60s',value);self.assertIn('"tun0" timeout 60s',value)
        self.assertNotIn('hook input',value);self.assertIn('iifname "br-lan"',value);self.assertIn('meta nfproto ipv4',value)
    def test_unsafe_device_never_enters_nft_script(self):
        for devices in ([],['wg0;flush ruleset'],['wg0\n'],['x'*16]):
            with self.assertRaises(fault.FaultError):fault.script(devices,60,'a'*32)
    def test_foreign_table_never_deleted(self):
        with patch.object(fault.Nft,'contents',return_value='foreign'),patch.object(fault.subprocess,'run') as run:
            with self.assertRaisesRegex(fault.FaultError,'FOREIGN'):fault.Nft().cleanup('a'*32)
        run.assert_not_called()
    def test_nft_timeout_preflight_failure_never_applies_unbounded_fallback(self):
        with tempfile.TemporaryDirectory() as d,patch.object(fault,'RUNTIME',Path(d)),patch.object(fault.Nft,'contents',return_value=None),patch.object(fault.subprocess,'run',return_value=MagicMock(returncode=1)) as run:
            with self.assertRaisesRegex(fault.FaultError,'TIMEOUT-RULE'):fault.Nft().apply(['wg0'],60,'a'*32)
            self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[0][1],'-c')
    def test_watchdog_cleans_owned_table_even_without_parent(self):
        value={'nonce':'a'*32,'monotonic_until':1}
        with patch.object(fault,'load',return_value=value),patch.object(fault,'control_lock',return_value=nullcontext()),patch.object(fault,'atomic_json') as write,patch.object(fault,'Nft') as engine:
            fault.worker('a'*32)
        engine.return_value.cleanup.assert_called_once_with('a'*32);self.assertTrue(write.call_args.args[1]['cleaned'])
    def test_public_status_excludes_watchdog_nonce_and_devices(self):
        value={'nonce':'a'*32,'phase':'ACTIVE','monotonic_until':time.monotonic()+20,'until':time.time()+20,'profiles':['a'],'devices':['wg0'],'scope':'profile'}
        with patch.object(fault,'load',return_value=value),patch.object(fault,'read_json',return_value={}):result=fault.public_status()
        self.assertNotIn('nonce',result);self.assertNotIn('devices',result)
    def test_corrupt_intent_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as d,patch.object(fault,'RUNTIME',Path(d)):
            (Path(d)/'fault-intent.json').write_text(json.dumps({'data':{'nonce':'a'*32},'sha256':'incorrect'}))
            with self.assertRaises(fault.FaultError):fault.load()

class RecoveryObservationTests(unittest.TestCase):
    def samples(self):return [{'id':'a','time':1000-i*20,'code':None,'dns_ok':True,'https_success':2} for i in range(5)]
    def test_return_needs_success_count_and_stable_span(self):
        self.assertTrue(recovery.stable_success(self.samples(),'a',3,60,1000))
        self.assertFalse(recovery.stable_success(self.samples()[:3],'a',3,60,1000))
    def test_failure_gap_stale_future_and_duplicate_do_not_make_stable_return(self):
        points=self.samples();points[1]['code']='DNS-001';self.assertFalse(recovery.stable_success(points,'a',3,60,1000))
        self.assertFalse(recovery.stable_success(self.samples(),'a',3,60,2000))
        self.assertFalse(recovery.stable_success(self.samples()*3,'a',10,60,1000))
    def test_general_policy_allows_third_connected_generic_without_moving_special_rules(self):
        from vendor_fixture import stamp
        data,profiles=fixture();profiles.append(stamp({'id':'openvpn:3_3','interface':'ovpnclient3'}));data['sections'].append({'.name':'c','.type':'rule','enabled':'1','killswitch':'1','via':'ovpnclient3'});data['settings']['plan_target']='openvpn:3_3'
        result=native.choose(data,profiles);self.assertEqual(result['target_rule'],'c');self.assertEqual(result['order'][:3],['global','default','special'])
