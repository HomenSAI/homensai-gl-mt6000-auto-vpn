"""Event-time direction, completion and latency survive persistence and cheap projection."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,native_switch as n,native_history as history,auto_live
import test_pair_manual_directions as fixture
REAL_PUBLISH=n.publish
NOW=fixture.NOW;SOURCE=fixture.SOURCE;TARGET=fixture.TARGET


class PairEventHistory(unittest.TestCase):
    enterContext=fixture.PairManualDirections.enterContext
    def setUp(self):
        fixture.PairManualDirections.setUp(self)
        self.enterContext(patch('retention_settings.configured_days',return_value=7))
    reorder=fixture.PairManualDirections.reorder
    apply=fixture.PairManualDirections.apply
    process=fixture.PairManualDirections.process
    kernel_proof=fixture.PairManualDirections.kernel_proof
    request=fixture.PairManualDirections.request
    allow_next=fixture.PairManualDirections.allow_next

    def persist_calls(self):
        rows=[]
        for key,rtt in (('source',331),('target',129)):
            rows.append(dict(self.selection[key],time=NOW,rtt_ms=rtt,code=None,dns_ok=True,https_success=2))
        agent.atomic_json(self.runtime/'status.json',{'time':NOW,'profiles':rows})
        for call in self.publish.call_args_list:
            value=copy.deepcopy(call.args[0]);value.setdefault('proof_scope','router-probed-ipv4')
            REAL_PUBLISH(value)
        return history.History(self.persist).public(now=NOW)

    def test_primary_forward_completes_to_source_in_observing_and_uses_source_event_rtt(self):
        self.kernel_applied=True;self.request('primary')
        saved=self.persist_calls();terminal=[row for row in saved['events'] if row.get('transition_outcome')=='committed']
        self.assertTrue(terminal)
        row=terminal[-1]
        self.assertEqual(row['state'],'OBSERVING');self.assertTrue(row['transition_completed'])
        self.assertEqual(row['from_role'],'target');self.assertEqual(row['from_profile_id'],TARGET)
        self.assertEqual(row['destination_role'],'source');self.assertEqual(row['destination_profile_id'],SOURCE)
        self.assertEqual(row['before_order'],['t','s']);self.assertEqual(row['after_order'],['s','t']);self.assertEqual(row['session_order'],['t','s'])
        self.assertEqual(row['latency']['profile'],SOURCE);self.assertEqual(row['latency']['rtt_ms'],331)
        data=history.History(self.persist).load()
        self.assertTrue(data['active_attempt']['terminal']);self.assertEqual(data['totals']['manual_committed'],1)
        self.assertEqual(data['totals']['returns'],1,'return to configured primary is separate from restoring initial reserve-first session order')
        self.selection['source']['rtt_ms']=9999
        self.assertEqual(history.History(self.persist).public(now=NOW)['events'][-1]['latency']['rtt_ms'],331)

    def test_reapply_has_no_fake_switch_counters_arrow_or_destination_latency(self):
        import pair_auto as pair
        pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,{})
        self.persist_calls();data=history.History(self.persist).load()
        repairs=[row for row in data['events'] if row.get('activation_reapply')]
        self.assertTrue(repairs)
        self.assertTrue(all(row['route_changed'] is False and 'latency' not in row for row in repairs))
        self.assertEqual(data.get('totals',{}).get('committed',0),0)
        self.assertEqual(data.get('totals',{}).get('protocol_switches',0),0)

    def test_steady_new_mode_committed_row_is_explicitly_not_a_channel_transition(self):
        REAL_PUBLISH({'state':'COMMITTED','source':SOURCE,'target':TARGET,'mode':'continuous-pair','proof_scope':'router-probed-ipv4'})
        row=history.History(self.persist).public(now=NOW)['events'][-1]
        self.assertTrue(row['transition_metadata_present']);self.assertFalse(row['route_changed']);self.assertNotIn('latency',row)

    def test_auto_live_projects_original_kernel_time_without_probes_locks_or_renewal(self):
        self.kernel_applied=True;self.request('primary');self.persist_calls()
        with patch.object(auto_live.time,'time',return_value=NOW+10),patch.object(agent,'command') as command,patch.object(agent,'probe') as probe,patch('auto_control.current_revision') as revision,patch('auto_control.control_lock') as lock:
            live=auto_live.snapshot()
        self.assertTrue(live['channel_path']['confirmed']);self.assertEqual(live['channel_path']['active_profile_id'],SOURCE)
        self.assertEqual(live['channel_path']['checked_at'],NOW);self.assertEqual(live['channel_path']['valid_for'],15)
        self.assertEqual(live['auto_control'],{'requested':'on','pair_phase':'RUNNING'})
        command.assert_not_called();probe.assert_not_called();revision.assert_not_called();lock.assert_not_called()
        with patch.object(auto_live.time,'time',return_value=NOW+16):expired=auto_live.snapshot()
        self.assertFalse(expired['channel_path']['confirmed']);self.assertEqual(expired['channel_path']['checked_at'],NOW)

    def test_known_busy_invalidates_a_still_young_display_proof(self):
        self.kernel_applied=True;self.request('primary');self.persist_calls()
        value=agent.read_json(n.STATE);value.update(state='BLOCKED',blockers=['VENDOR-WORKER-BUSY']);agent.atomic_json(n.STATE,value)
        self.assertFalse(auto_live.snapshot()['channel_path']['confirmed'])

    def test_stop_records_actual_restore_to_initial_reserve_before_long_cleanup_without_early_ack(self):
        import pair_auto as pair
        self.kernel_applied=True;self.request('primary')
        state=pair.read_state();state['owned']=['wgclient1'];pair.save(state);pair.stop_locked(self.revision)
        def quiet(*args):
            self.assertEqual(pair.read_state()['phase'],'STOPPING');self.assertEqual(pair.public_phase(),'STOPPING')
            restored=[call.args[0] for call in self.publish.call_args_list if call.args[0].get('transition_outcome')=='restored']
            self.assertTrue(restored);self.assertEqual(restored[-1]['state'],'RESTORING')
        with patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}),patch.object(pair,'quiet',side_effect=quiet),patch.object(pair,'set_disabled'),patch.object(n,'command'):
            self.assertTrue(pair.cleanup(self.backend,pair.read_state()))
        self.assertEqual(pair.read_state()['phase'],'STOPPED')
        self.publish({'state':'STOPPED','reason':'CLIENT-STOP','original_restored':True,'mode':'continuous-pair','proof_scope':'router-probed-ipv4'})
        saved=self.persist_calls()
        restored=[row for row in saved['events'] if row.get('transition_outcome')=='restored']
        self.assertEqual(len(restored),1);row=restored[0]
        self.assertEqual(row['from_role'],'source');self.assertEqual(row['destination_role'],'target')
        self.assertEqual(row['before_order'],['s','t']);self.assertEqual(row['restored_order'],['t','s'])
        self.assertEqual(row['latency']['profile'],TARGET);self.assertEqual(row['latency']['rtt_ms'],129)
        self.assertTrue(row['original_restored']);self.assertFalse(saved['events'][-1]['route_changed'])

    def test_refused_primary_names_requested_primary_while_preserving_actual_reserve_order(self):
        import pair_auto as pair,pair_manual as manual
        original=self.process;foreign=[False]
        self.backend.attest_policy.side_effect=lambda selection=None:{'verified':False,'repairable_missing':False,'kernel_fingerprint':'f'*64} if foreign[0] else self.kernel_proof(selection)
        def spawn(*args,**kwargs):
            process=original(*args,**kwargs);wait=process.wait.side_effect
            def changed(**kwargs):foreign[0]=True;return wait(**kwargs)
            process.wait.side_effect=changed;return process
        self.spawn.side_effect=spawn
        self.assertTrue(manual.request('primary',self.revision)['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'REFUSED');self.backend.apply.assert_not_called()
        saved=self.persist_calls();refused=[row for row in saved['events'] if row.get('transition_outcome')=='refused']
        self.assertEqual(len(refused),1);row=refused[0]
        self.assertEqual(row['destination_role'],'source');self.assertEqual(row['destination_profile_id'],SOURCE)
        self.assertEqual(row['restored_order'],['t','s']);self.assertEqual(row['after_order'],['t','s'])
        self.assertFalse(row['route_changed']);self.assertNotIn('latency',row)


if __name__=='__main__':unittest.main()
