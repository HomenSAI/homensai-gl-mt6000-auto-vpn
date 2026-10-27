"""Two-level planning and native pre-write identity boundaries, offline only."""
import copy
import json
import subprocess
from pathlib import Path
import sys
import unittest
import tempfile
from contextlib import ExitStack,contextmanager
from types import SimpleNamespace
from unittest.mock import patch,MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from failover_plan import plan,streak
from failure_diagnosis import diagnose,resolve_pair
from candidate_hierarchy import rank_candidates
import native_switch as native
from vendor_fixture import attach
from test_native_switch import Backend


def fixture():
    source='openvpn:1_1';target='wireguard:peer_2';now=1000
    samples=[{'id':source,'time':stamp,'code':'DNS-001'} for stamp in (940,970,1000)]
    samples += [{'id':target,'time':stamp,'code':None,'dns_ok':True,'https_success':2} for stamp in (970,1000)]
    status=attach({'profiles':[{'id':source,'interface':'vpn1','protocol':'openvpn','code':'DNS-001'},
                              {'id':target,'interface':'vpn2','protocol':'wireguard'}],'samples':samples},now)
    settings={'plan_enabled':True,'plan_source':source,'plan_target':target,'interval':30}
    return status,settings,now


class TunnelCoordination(unittest.TestCase):
    def test_ready_is_advisory_and_never_claims_vendor_retry_exhaustion(self):
        status,settings,now=fixture();result=plan(status,settings,now)
        self.assertEqual(result['state'],'SWITCH-RECOMMENDED')
        self.assertEqual(result['coordination']['state'],'READY')
        self.assertIs(result['coordination']['can_apply'],False)
        self.assertIsNone(result['coordination']['vendor_attempts_exhausted'])
        self.assertEqual(result['coordination']['vendor_reason'],'UNOBSERVED')

    def test_same_provider_can_have_two_independent_same_protocol_channels(self):
        status,settings,now=fixture();target=status['profiles'][1];old=target['id']
        target.update(id='openvpn:1_2',protocol='openvpn',vendor_profile_group_id='openvpn:1')
        status['profiles'][0]['vendor_profile_group_id']='openvpn:1'
        for point in status['samples']:
            if point['id']==old:point['id']=target['id']
        settings['plan_target']=target['id'];attach(status,now)
        result=plan(status,settings,now)
        self.assertEqual(result['state'],'SWITCH-RECOMMENDED')
        self.assertEqual(result['coordination']['transition'],'channel')

    def test_same_tunnel_is_vendor_owned_even_with_different_editable_labels(self):
        status,settings,now=fixture()
        settings.update(plan_source_tunnel='openvpn:vpn1',plan_target_tunnel='openvpn:vpn1')
        status['profiles'][0]['channel']='Primary';status['profiles'][1]['channel']='Reserve'
        result=plan(status,settings,now)
        self.assertEqual(result['coordination']['code'],'VENDOR-SAME-TUNNEL')
        self.assertIsNone(result['recommendation'])

    def test_renaming_metadata_cannot_change_routing_identity_or_tier(self):
        status,settings,now=fixture();before=plan(status,settings,now)
        for row in status['profiles']:row.update(channel='SAME EDITABLE LABEL',name='Renamed')
        after=plan(status,settings,now)
        self.assertEqual(before['coordination'],after['coordination'])
        self.assertEqual(before['recommendation'],after['recommendation'])

    def test_pending_or_fast_stable_snapshots_do_not_finish_vendor_window(self):
        for mode in ('PENDING','too-soon'):
            status,settings,now=fixture();group=status['vendor_observation']['groups'][0]
            if mode=='PENDING':group['state']='PENDING'
            else:
                group['changed_at']=990;status['profiles'][0]['vendor_changed_at']=990
            result=plan(status,settings,now)
            self.assertEqual(result['coordination']['code'],'VENDOR-SETTLING')
            self.assertIsNone(result['recommendation'])

    def test_rebound_same_profile_cannot_reuse_old_generation_success_or_failure(self):
        for index in (0,1):
            status,settings,now=fixture()
            status['profiles'][index]['vendor_generation']='f'*32
            status['vendor_observation']['groups'][index]['generation']='f'*32
            self.assertIsNone(plan(status,settings,now)['recommendation'])

    def test_durable_tunnel_anchor_resolves_current_vendor_selected_profile(self):
        status,settings,now=fixture();old=settings['plan_source'];new='openvpn:1_9'
        settings.update(plan_source_tunnel='openvpn:vpn1',plan_target_tunnel='wireguard:vpn2')
        status['profiles'][0]['id']=new
        for point in status['samples']:
            if point['id']==old:point['id']=new
        attach(status,now)
        result=plan(status,settings,now)
        self.assertEqual(result['source'],new);self.assertEqual(result['configured_source'],old)
        self.assertEqual(result['state'],'SWITCH-RECOMMENDED')

    def test_missing_legacy_binding_cannot_be_guessed_from_provider_or_labels(self):
        status,settings,now=fixture();status['profiles'][0]['interface']=None
        status['profiles'][0].update(channel='main',vendor_profile_group_id='openvpn:1')
        self.assertIsNone(plan(status,settings,now)['recommendation'])

    def test_fresh_wan_link_down_suppresses_candidates_without_calling_it_vpn_failure(self):
        status,settings,now=fixture();status['uplink_observation']={'state':'DOWN','time':now}
        result=plan(status,settings,now)
        self.assertEqual(result['state'],'UPLINK-LINK-DOWN');self.assertIsNone(result['recommendation'])

    def test_conflicting_duplicate_timestamps_do_not_make_a_streak(self):
        status,settings,now=fixture();point=copy.deepcopy(status['samples'][-1]);point['code']='DNS-001'
        status['samples'].insert(0,point)
        self.assertIsNone(plan(status,settings,now)['recommendation'])

    def test_typed_stale_future_nan_and_ambiguous_evidence_fail_closed(self):
        for value in (None,[],True,{'time':float('nan')},{'time':1000,'profiles':[None]}):
            with self.subTest(value=value):
                self.assertIsNone(plan(value,fixture()[1],1000)['recommendation'])
                self.assertTrue(diagnose(value,'openvpn:1_1',1000)['suppress_switch'])
        for mutation in ('future','duplicate','generation','malformed-uplink'):
            status,settings,now=fixture()
            if mutation=='future':status['time']=now+1
            if mutation=='duplicate':status['profiles'].append(copy.deepcopy(status['profiles'][0]))
            if mutation=='generation':status['vendor_observation']['groups'][1]['generation']=None
            if mutation=='malformed-uplink':status['uplink_observation']=[];status['profiles'][0]['https_success']='2';status['profiles'][0]['code']=None
            self.assertIsNone(plan(status,settings,now)['recommendation'])

    def test_ranking_never_offers_vendor_owned_server_actions(self):
        status,settings,now=fixture()
        rows=rank_candidates(status['profiles'],[],status['samples'],settings['plan_source'],now,
                             observation=status['vendor_observation'])
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['transition'],'protocol')
        self.assertIs(rows[0]['can_apply'],False)
        self.assertEqual(rank_candidates(status['profiles'],[],status['samples'],settings['plan_source'],now),[])

    def test_native_forward_write_rejects_identity_change_before_spawn_or_journal(self):
        backend=Backend();selection=copy.deepcopy(backend.selection)
        backend.selection['vendor_identity']='f'*64
        with patch('auto_control.current_revision',return_value='c'*32),patch.object(native,'require_control_revision'),patch.object(native,'journal_write') as writer,patch.object(native.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(native.Refused,'PROFILE-IDENTITY-CHANGED'):
                native.attempt(backend,selection,2000,False)
        writer.assert_not_called();spawn.assert_not_called();self.assertEqual(backend.calls,[])

    def test_native_anchor_resolution_and_same_tunnel_refusal_do_not_weaken_policy(self):
        backend=Backend();data=backend.data;profiles=backend.profiles
        data['settings']['plan_source_tunnel']=profiles[0]['vendor_tunnel_id']
        data['settings']['plan_source']='openvpn:old_inactive'
        self.assertEqual(native.choose(data,profiles)['source']['id'],profiles[0]['id'])
        data['settings']['plan_target_tunnel']=profiles[0]['vendor_tunnel_id']
        with self.assertRaises(native.Refused):native.choose(data,profiles)
        data['ipv6']='1'
        with self.assertRaisesRegex(native.Refused,'IPV6-NOT-EXPLICITLY-DISABLED'):native.choose(data,profiles)

    def test_stop_during_slow_trace_prevents_journal_and_spawn_even_when_latch_deduplicates(self):
        for old_epoch in (0,5000):
            with self.subTest(old_epoch=old_epoch),tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
                root=Path(directory);backend=Backend();calls=[]
                stack.enter_context(patch.object(native,'RUNTIME',root))
                stack.enter_context(patch.object(native,'PERSIST',root))
                native.atomic_json(root/'auto-control-revision.json',{'revision':'c'*32})
                if old_epoch:native.atomic_json(root/'native-stop.json',{'requested':old_epoch,'trial':'old'})
                def trace(profile):
                    calls.append(profile['id'])
                    # This is the RAM effect of Stop; a future durable epoch
                    # may already exist and legitimately remain deduplicated.
                    native.atomic_json(root/'auto-control-revision.json',{'revision':'d'*32})
                    return '8.8.8.8'
                stack.enter_context(patch.object(native,'trace',side_effect=trace))
                writer=stack.enter_context(patch.object(native,'journal_write'))
                spawn=stack.enter_context(patch.object(native.subprocess,'Popen'))
                with self.assertRaisesRegex(native.Refused,'CLIENT-STOP'):
                    native.attempt(backend,backend.selection,2000,True,control_revision='c'*32)
                self.assertEqual(calls,[backend.profiles[0]['id']]);writer.assert_not_called();spawn.assert_not_called()
                self.assertEqual(backend.calls,[])

    def test_missing_or_corrupt_revision_never_authorizes_forward_work(self):
        for record in (None,[],{'revision':'d'*32},{'revision':'c'*32,'extra':True}):
            with self.subTest(record=record),patch.object(native,'read_json',return_value=record):
                with self.assertRaisesRegex(native.Refused,'CLIENT-STOP'):native.require_control_revision('c'*32)

    def test_every_reorder_command_and_commit_have_a_forward_only_check(self):
        backend=Backend();router=native.Linux();checks=[]
        def before_write():
            checks.append(True)
            if len(checks)==2:raise native.Refused('CLIENT-STOP')
        with patch.object(router,'policy',return_value=backend.data),patch.object(native,'command') as command:
            with self.assertRaisesRegex(native.Refused,'CLIENT-STOP'):
                router.reorder(backend.selection['order'],before_write=before_write)
        self.assertEqual(len(checks),2);self.assertEqual(command.call_count,1)
        self.assertEqual(command.call_args.args[0][:2],['uci','reorder'])

    def test_completed_stop_between_validation_and_dispatch_prevents_new_command(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(native,'RUNTIME',Path(directory)):
            path=Path(directory)/'auto-control-revision.json'
            native.atomic_json(path,{'revision':'c'*32})
            native.require_control_revision('c'*32)
            @contextmanager
            def stopped_before_gate(unused):
                native.atomic_json(path,{'revision':'d'*32})
                yield
            with patch('auto_control.control_lock',side_effect=stopped_before_gate),patch.object(native.subprocess,'Popen') as spawn:
                with self.assertRaisesRegex(native.Refused,'CLIENT-STOP'):
                    native.forward_dispatch(['uci','commit','route_policy'],'c'*32)
            spawn.assert_not_called()

    def test_command_dispatch_is_locked_but_command_wait_is_not(self):
        held=[]
        @contextmanager
        def gate(unused):
            held.append(True)
            try:yield
            finally:held.pop()
        def communicate(timeout):
            self.assertFalse(held,'Stop must not wait for a vendor command')
            return b'bounded-output',None
        process=SimpleNamespace(returncode=0,communicate=communicate)
        def spawn(*args,**kwargs):
            self.assertTrue(held,'revision check and dispatch must share the short lock')
            self.assertNotIn('start_new_session',kwargs,'inherit owned apply group for cleanup')
            return process
        with patch('auto_control.control_lock',side_effect=gate),patch.object(native,'require_control_revision') as revision,patch.object(native.subprocess,'Popen',side_effect=spawn):
            self.assertEqual(native.forward_dispatch(['uci','commit','route_policy'],'c'*32),b'bounded-output')
        revision.assert_called_once_with('c'*32)

    def test_timeout_cleanup_remains_bounded_when_descendant_keeps_pipe_open(self):
        from contextlib import nullcontext
        process=MagicMock()
        process.communicate.side_effect=subprocess.TimeoutExpired('synthetic-vendor-child',1)
        with patch('auto_control.control_lock',return_value=nullcontext()),patch.object(native,'require_control_revision'),patch.object(native.subprocess,'Popen',return_value=process):
            with self.assertRaises(subprocess.TimeoutExpired):
                native.forward_dispatch(['synthetic-vendor-child'],'c'*32,timeout=5)
        self.assertEqual([call.kwargs['timeout'] for call in process.communicate.call_args_list],[5,1])
        process.kill.assert_called_once();process.stdout.close.assert_called_once();process.stderr.close.assert_called_once()

    def test_old_reserve_profile_failure_cannot_describe_rebound_current_channel(self):
        status,settings,now=fixture();journal={'source':settings['plan_source'],'target':settings['plan_target'],'confirmed':900}
        settings.update(plan_source_tunnel='openvpn:vpn1',plan_target_tunnel='wireguard:vpn2')
        old=settings['plan_target'];status['profiles'][1]['id']='wireguard:peer_99'
        for point in status['samples']:
            if point['id']==old:point['id']='wireguard:peer_99'
        attach(status,now);backend=Backend()
        with patch.object(backend,'health') as health,patch.object(backend,'recovery_ready') as ready:
            result=native.committed_recovery_decision(backend,journal,settings,status['samples'],now,status)
        self.assertEqual(result,{'action':'HOLD','reason':'RESERVE-IDENTITY-UNKNOWN','reserve_healthy':None})
        health.assert_not_called();ready.assert_not_called()

    def test_live_kernel_drift_blocks_before_monitor_generation_is_updated(self):
        backend=Backend();now=1000
        status=attach({'profiles':copy.deepcopy(backend.profiles),'samples':[]},now)
        for index,row in enumerate(status['profiles']):row.update(device='vpn'+str(index),mark=index+1,table=str(100+index),ifindex=index+10)
        data={'profiles':copy.deepcopy(backend.profiles),'servers':[]}
        for drift in (False,True):
            router=native.Linux()
            def binding(logical):
                row=next(row for row in status['profiles'] if row['interface']==logical)
                value={key:row[key] for key in ('device','mark','table','ifindex')};value['code']=None
                if drift:value['ifindex']+=1
                return value
            with patch.object(router,'policy',return_value=backend.data),patch.object(router,'acceleration',return_value={'loaded':[],'hnat_runtime':'disabled'}),patch.object(native,'inventory',return_value=data),patch.object(native,'read_json',return_value=status),patch.object(native,'route_binding',side_effect=binding),patch.object(native.time,'time',return_value=now),patch.object(native,'command',return_value=json.dumps({'board_name':'glinet,gl-mt6000'}).encode()):
                blockers,selection=router.diagnostic()
            if drift:
                self.assertIn('PROFILE-IDENTITY-CHANGED',blockers);self.assertIsNone(selection)
            else:
                self.assertNotIn('PROFILE-IDENTITY-CHANGED',blockers);self.assertIsNotNone(selection)

    def test_stopped_reserve_has_its_own_blocker_and_is_not_a_changed_profile(self):
        backend=Backend();now=1000
        data={'profiles':copy.deepcopy(backend.profiles),'servers':[]}
        for down,expected in (('target','RESERVE-NOT-CONNECTED'),('source',None)):
            status=attach({'profiles':copy.deepcopy(backend.profiles),'samples':[]},now)
            for index,row in enumerate(status['profiles']):row.update(device='vpn'+str(index),mark=index+1,table=str(100+index),ifindex=index+10)
            interface=backend.selection[down]['interface']
            for row in status['profiles']:
                if row['interface']==interface:
                    row['code']='VPN-001'
                    for key in ('device','mark','table','ifindex'):row.pop(key)
            router=native.Linux()
            def binding(logical):
                row=next(row for row in status['profiles'] if row['interface']==logical)
                if logical==interface:return {'code':'VPN-001'}
                value={key:row[key] for key in ('device','mark','table','ifindex')};value['code']=None
                return value
            with patch.object(router,'policy',return_value=backend.data),patch.object(router,'acceleration',return_value={'loaded':[],'hnat_runtime':'disabled'}),patch.object(native,'inventory',return_value=data),patch.object(native,'read_json',return_value=status),patch.object(native,'route_binding',side_effect=binding),patch.object(native.time,'time',return_value=now),patch.object(native,'command',return_value=json.dumps({'board_name':'glinet,gl-mt6000'}).encode()):
                blockers,selection=router.diagnostic()
            self.assertNotIn('PROFILE-IDENTITY-CHANGED',blockers)
            if expected:self.assertIn(expected,blockers);self.assertIsNone(selection)
            else:self.assertNotIn('RESERVE-NOT-CONNECTED',blockers)


if __name__=='__main__':unittest.main()
