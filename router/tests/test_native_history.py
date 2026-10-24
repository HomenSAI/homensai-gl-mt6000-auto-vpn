import json
import os
from pathlib import Path
import sys
import tempfile
import time
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from native_history import History, HistoryError, read_public
import native_switch as native


class HistoryTests(unittest.TestCase):
    def test_rich_phase_history_obeys_byte_bound_without_losing_aggregates(self):
        with tempfile.TemporaryDirectory() as d,patch.object(History,'RETENTION_BYTES',16000):
            h=History(d)
            for n in range(20):
                phases=[{'phase':'PHASE_'+str(i),'time':n*40+i} for i in range(32)]
                h.record({'state':'APPLYING' if n%2==0 else 'COMMITTED','phase_evidence':phases},n*40+32)
            data=h.load()
            self.assertEqual(data['sequence'],20)
            self.assertLess(len(data['events']),20)
            self.assertLess(h.path.stat().st_size,17000)
            self.assertEqual(sum(month['attempts'] for month in data['months'].values()),10)
            self.assertTrue(h.public()['event_history_truncated'])

    def test_corrupt_attempt_metadata_recovers_explicit_backup_without_private_fields(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);h.record({'state':'APPLYING'},100)
            row=h.load();row['active_attempt']['id']='PRIVATE_SENTINEL'
            h.path.write_text(json.dumps(h.envelope(row)))
            result=h.public()
            self.assertTrue(result['restored_from_backup'])
            self.assertNotIn('PRIVATE_SENTINEL',str(result))

    def test_public_attempt_retry_ids_and_probe_evidence_exclude_nonces(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d)
            base={'source':'openvpn:1_2','target':'wireguard:peer_3','trial':False}
            h.record(dict(base,state='ARMED',reason='SOURCE-FAILED',probe_evidence={'source_streak_met':True,'reserve_streak_met':True,'required_failures':3,'required_successes':2,'token':'PRIVATE_SENTINEL'}),100)
            h.record(dict(base,state='APPLYING',tx='PRIVATE_SENTINEL'),101)
            h.record(dict(base,state='WAIT-CLIENT'),102)
            h.record(dict(base,state='ROLLED-BACK',reason='TRANSACTION-FAILED'),103)
            h.record(dict(base,state='ARMED'),104)
            h.record(dict(base,state='APPLYING'),105)
            h.record(dict(base,state='COMMITTED',phase_evidence=[{'phase':'APPLYING','time':105,'token':'PRIVATE_SENTINEL'},{'phase':'COMMITTED','time':106},{'phase':'FUTURE','time':107}]),106)
            events=h.public()['events']
            self.assertEqual(len({r['attempt_id'] for r in events[:4]}),1)
            self.assertNotEqual(events[0]['attempt_id'],events[4]['attempt_id'])
            self.assertEqual(events[0]['retry_episode_id'],events[4]['retry_episode_id'])
            self.assertEqual(events[0]['probe_evidence']['required_failures'],3)
            self.assertNotIn('PRIVATE_SENTINEL',h.path.read_text())
            self.assertEqual(events[-1]['phase_evidence'],[{'phase':'APPLYING','time':105},{'phase':'COMMITTED','time':106}])
            self.assertFalse(h.record(dict(base,state='COMMITTED',phase_evidence=[{'phase':'APPLYING','time':105},{'phase':'COMMITTED','time':106}]),107))
            h.record(dict(base,state='ARMED'),108)
            self.assertNotEqual(h.public()['events'][-1]['retry_episode_id'],events[0]['retry_episode_id'])

    def test_history_survives_a_separate_process_exit(self):
        root=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
        with tempfile.TemporaryDirectory() as d:
            script="import sys,os;sys.path.insert(0,sys.argv[1]);from native_history import History;History(sys.argv[2]).record({'state':'APPLYING'},100);os._exit(0)"
            child=subprocess.run([sys.executable,'-c',script,str(root),d],timeout=10,check=True)
            self.assertEqual(History(d).public()['events'][0]['state'],'APPLYING')

    def test_own_child_crashes_at_atomic_replace_boundaries(self):
        root=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
        script='''import sys,os,signal
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from native_history import History
original=os.replace
stage=sys.argv[3]
def replace(src,dst):
 name=Path(dst).name
 kind='backup' if name=='native-history.backup.json' else 'primary'
 if stage==kind+'-before':os.kill(os.getpid(),signal.SIGKILL)
 original(src,dst)
 if stage==kind+'-after':os.kill(os.getpid(),signal.SIGKILL)
os.replace=replace
History(sys.argv[2]).record({'state':'APPLYING'},101)
'''
        for stage in ('backup-before','backup-after','primary-before','primary-after'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as d:
                History(d).record({'state':'DISABLED'},100)
                child=subprocess.run([sys.executable,'-c',script,str(root),d,stage],timeout=10,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                self.assertEqual(child.returncode,-9)
                restored=History(d).public()
                self.assertIn(restored['sequence'],(1,2));self.assertIn(restored['events'][-1]['state'],('DISABLED','APPLYING'))

    def test_restart_deduplicates_and_persists_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);self.assertTrue(h.record({'state':'DISABLED'},100))
            with patch('native_history.atomic') as write:
                self.assertFalse(History(d).record({'state':'DISABLED'},101));write.assert_not_called()
            History(d).record({'state':'APPLYING'},102)
            self.assertEqual(History(d).public()['sequence'],2)
            self.assertEqual(os.stat(h.path).st_mode&0o777,0o600)

    def test_bounded_events_keep_aggregate_counts(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d,limit=2)
            for n in range(10):h.record({'state':'APPLYING' if n%2==0 else 'COMMITTED'},1700000000+n)
            data=h.load();self.assertEqual(len(data['events']),2);self.assertEqual(data['sequence'],10)
            totals=next(iter(data['months'].values()));self.assertEqual(totals['attempts'],5);self.assertEqual(totals['committed'],5)

    def test_backup_is_previous_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);h.record({'state':'DISABLED'},100);h.record({'state':'APPLYING'},101)
            h.path.write_text('damaged')
            value=History(d).public();self.assertTrue(value['restored_from_backup']);self.assertEqual(value['sequence'],1)
            History(d).record({'state':'BLOCKED'},102)
            self.assertEqual(History(d).public()['sequence'],2)

    def test_both_corrupt_preserved_and_reported(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);h.path.write_text('bad');h.backup.write_text('bad-backup')
            with self.assertRaises(HistoryError):h.record({'state':'APPLYING'},100)
            self.assertEqual(h.path.read_text(),'bad');self.assertEqual(read_public(d)['error'],'HISTORY-001')

    def test_private_fields_are_not_stored(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);h.record({'state':'WAIT-CLIENT','source':'openvpn:1_2','target':'wireguard:peer_3','tx':'PRIVATE_SENTINEL','expected_exit':'EXIT_SENTINEL','token':'TOKEN_SENTINEL','acceleration':{'hook_log':'LOG_SENTINEL'}},100)
            text=h.path.read_text()
            for sentinel in ('PRIVATE_SENTINEL','EXIT_SENTINEL','TOKEN_SENTINEL','LOG_SENTINEL'):self.assertNotIn(sentinel,text)
            self.assertIn('openvpn:1_2',text)

    def test_trial_and_automatic_results_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);h.record({'state':'ARMED','reason':'TRIAL-PASSED','trial':True},100)
            h.record({'state':'COMMITTED','trial':False},101)
            totals=next(iter(h.load()['months'].values()))
            self.assertEqual(totals['trials_passed'],1);self.assertEqual(totals['committed'],1)

    def test_month_boundary_uses_berlin_timezone(self):
        previous=os.environ.get('TZ');os.environ['TZ']='CET-1CEST,M3.5.0,M10.5.0/3';__import__("timezone_compat").refresh_timezone()
        try:
            with tempfile.TemporaryDirectory() as d:
                h=History(d);h.record({'state':'APPLYING'},1793487599);h.record({'state':'COMMITTED'},1793487600)
                # UTC 2026-10-31 22:59:59/23:00:00 crosses Berlin midnight.
                self.assertEqual(set(h.load()['months']),{'2026-10','2026-11'})
        finally:
            if previous is None:os.environ.pop('TZ',None)
            else:os.environ['TZ']=previous
            __import__("timezone_compat").refresh_timezone()

    def test_history_failure_blocks_publish_but_reports_status(self):
        with tempfile.TemporaryDirectory() as d,patch.object(native,'PERSIST',Path(d)),patch.object(native,'STATE',Path(d)/'status'),patch.object(History,'record',side_effect=OSError('disk')):
            with self.assertRaisesRegex(native.Refused,'HISTORY-001'):native.publish({'state':'APPLYING'})
            self.assertEqual(json.loads(native.STATE.read_text())['blockers'],['HISTORY-001'])

    def test_control_context_survives_persistence_without_becoming_a_transition(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);value={'state':'APPLYING','control_action':'start','control_source':'manual','control_time':100,'transition_source':'automatic'}
            h.record(value,110);self.assertFalse(h.record(value,111))
            row=h.public()['events'][-1]
            self.assertEqual(row['control_source'],'manual');self.assertEqual(row['transition_source'],'automatic')
            self.assertEqual(row['control_time'],100)
            self.assertEqual(h.public()['totals']['attempts'],1)
            self.assertEqual(h.public()['totals']['automatic_attempts'],1)
            h.record(dict(value,control_source='PRIVATE_SENTINEL',transition_source='PRIVATE_SENTINEL'),112)
            self.assertNotIn('PRIVATE_SENTINEL',str(h.public()))

    def test_publish_preserves_independent_activation_and_switch_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);runtime=root/'run';persist=root/'persist';runtime.mkdir();persist.mkdir()
            (runtime/'auto-control.json').write_text(json.dumps({'mode':'on','time':100,'request_source':'manual'}))
            with patch.object(native,'RUNTIME',runtime),patch.object(native,'PERSIST',persist),patch.object(native,'STATE',runtime/'native-status.json'),patch.object(native.time,'time',return_value=110):
                native.publish({'state':'APPLYING','reason':'SOURCE-FAILED'})
            row=History(persist).public()['events'][-1]
            self.assertEqual(row['transition_source'],'automatic');self.assertEqual(row['control_source'],'manual')

    def test_switch_latency_is_bound_to_target_generation_and_event_time(self):
        from native_history import capture_transition_latency
        value={'state':'APPLYING','source':'wireguard:peer_1','target':'openvpn:1_1'}
        p={'id':'openvpn:1_1','protocol':'openvpn','interface':'ovpnclient1','vendor_tunnel_id':'openvpn:ovpnclient1','vendor_generation':'b'*32,'vendor_state':'SETTLED','time':109,'rtt_ms':26.4,'code':None,'dns_ok':True,'https_success':2}
        binding={key:p[key] for key in ('id','protocol','interface','vendor_tunnel_id','vendor_generation')}
        self.assertEqual(capture_transition_latency(value,{'time':110,'profiles':[p]},binding,110)['rtt_ms'],26.4)
        for changes in ({'time':1},{'vendor_generation':'c'*32},{'vendor_state':'CHANGING'},{'code':'DNS-001'},{'dns_ok':False},{'https_success':0},{'rtt_ms':float('nan')},{'rtt_ms':True}):
            bad=dict(p,**changes)
            self.assertIsNone(capture_transition_latency(value,{'time':110,'profiles':[bad]},binding,110),changes)
        self.assertIsNone(capture_transition_latency(value,{'time':1,'profiles':[p]},binding,110))
        self.assertIsNone(capture_transition_latency(value,{'time':110,'profiles':[p,p]},binding,110))
        self.assertIsNone(capture_transition_latency(dict(value,state='RESTORING'),{'time':110,'profiles':[p]},binding,110),'return must use primary, never reserve delay')

    def test_new_latency_sample_alone_does_not_write_another_transition(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);value={'state':'APPLYING','source':'wireguard:peer_1','target':'openvpn:1_1','latency':{'profile':'openvpn:1_1','metric':'https-rtt-ms','time':109,'rtt_ms':26.4,'interface':'ovpnclient1','generation':'b'*32,'extra':'PRIVATE_SENTINEL'}}
            self.assertTrue(h.record(value,110))
            changed=dict(value,latency=dict(value['latency'],time=111,rtt_ms=99))
            self.assertFalse(h.record(changed,112))
            self.assertEqual(h.public()['events'][-1]['latency']['rtt_ms'],26.4,'historical RTT remains the recorded observation')
            self.assertTrue(h.record(dict(changed,state='COMMITTED'),113))
            self.assertEqual(h.public()['events'][-1]['latency']['rtt_ms'],99)
            self.assertNotIn('PRIVATE_SENTINEL',str(h.public()))
            self.assertEqual(h.public()['totals']['attempts'],1)

    def test_publish_captures_actual_target_observation_without_network_probe(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);runtime=root/'run';persist=root/'persist';runtime.mkdir();persist.mkdir()
            p={'id':'openvpn:1_1','protocol':'openvpn','interface':'ovpnclient1','vendor_tunnel_id':'openvpn:ovpnclient1','vendor_generation':'b'*32,'vendor_state':'SETTLED','time':109,'rtt_ms':26.4,'code':None,'dns_ok':True,'https_success':2}
            value={'state':'COMMITTED','source':'wireguard:peer_1','target':'openvpn:1_1'}
            journal=dict(value,vendor_profiles={'target':{k:p[k] for k in ('id','protocol','interface','vendor_tunnel_id','vendor_generation')}})
            (runtime/'status.json').write_text(json.dumps({'time':110,'profiles':[p]}))
            with patch.object(native,'RUNTIME',runtime),patch.object(native,'PERSIST',persist),patch.object(native,'STATE',runtime/'native-status.json'),patch.object(native,'journal_read',return_value=journal),patch.object(native.time,'time',return_value=110):
                native.publish(value)
            self.assertEqual(History(persist).public()['events'][-1]['latency']['profile'],'openvpn:1_1')
            self.assertEqual(json.loads((runtime/'native-status.json').read_text())['latency']['rtt_ms'],26.4)


if __name__=='__main__':unittest.main()
