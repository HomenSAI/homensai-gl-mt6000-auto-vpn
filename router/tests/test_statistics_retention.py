import copy,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
from reliability import Reliability,WEEK,active_controller
from native_history import History
from statistics_export import page

BASE=1792750000
def probe(stamp,code=None):return {'id':'wireguard:peer_3','time':stamp,'code':code,'dns_ok':code is None,'https_success':2 if code is None else 0}


class ReliabilityTests(unittest.TestCase):
    def test_outage_is_one_episode_and_probe_failures_are_separate(self):
        r=Reliability();r.observe(probe(BASE));r.observe(probe(BASE+10,'VPN-003'));r.observe(probe(BASE+20,'VPN-003'));r.observe(probe(BASE+30))
        totals=r.public()['totals']
        self.assertEqual((totals['checks'],totals['failed_checks'],totals['outages'],totals['recoveries']),(4,2,1,1))
        self.assertEqual([e['kind'] for e in r.data['events']],['FAILURE','RECOVERY'])
        self.assertEqual(r.data['events'][-1]['observed_duration_seconds'],20)
        r.observe(probe(BASE+30));self.assertEqual(r.public()['totals'],totals)

    def test_open_outage_survives_checkpoint_and_restart_without_recount(self):
        a=agent.Accounting();a.observe(probe(BASE,'DNS-001'))
        with tempfile.TemporaryDirectory() as folder,patch.object(agent,'PERSIST',Path(folder)),patch('agent.time.time',return_value=BASE+1):
            agent.checkpoint(a);restored,error=agent.restore();self.assertIsNone(error)
            restored.observe(probe(BASE+10,'DNS-001'));restored.observe(probe(BASE+20))
            self.assertEqual(restored.reliability.public()['totals']['outages'],1)
            self.assertEqual(restored.reliability.public()['totals']['recoveries'],1)

    def test_unknown_gap_is_never_healthy_or_an_exact_outage_duration(self):
        r=Reliability();r.observe(probe(BASE,'VPN-003'));r.observe(probe(BASE+1000,'VPN-003'));r.observe(probe(BASE+1010))
        self.assertEqual(r.data['totals']['observed_down_seconds'],10)
        self.assertEqual(r.data['totals']['unknown_intervals'],1)
        self.assertNotIn('observed_duration_seconds',r.data['events'][-1])

    def test_week_detail_expires_but_month_and_lifetime_counters_stay(self):
        r=Reliability();r.observe(probe(BASE,'VPN-003'));r.observe(probe(BASE+10));r.observe(probe(BASE+WEEK+11,'DNS-001'))
        self.assertEqual(len(r.data['events']),1)
        self.assertEqual(r.data['totals']['outages'],2)
        self.assertEqual(sum(m.get('outages',0) for m in r.data['months'].values()),2)

    def test_storage_limit_preserves_aggregates_and_reports_missing_details(self):
        with patch.object(Reliability,'MAX_EVENTS',2):
            r=Reliability()
            for i in range(8):r.observe(probe(BASE+i*10,'VPN-003' if i%2==0 else None))
            self.assertEqual(len(r.data['events']),2);self.assertEqual(r.data['totals']['outages'],4)
            self.assertEqual(r.data['details_dropped'],6)

    def test_inactive_unknown_does_not_become_an_outage(self):
        r=Reliability();r.observe(probe(BASE,'PROFILE-INACTIVE'));r.observe(probe(BASE+10,'VENDOR-IDENTITY-UNKNOWN'))
        self.assertEqual(r.data['totals'].get('outages',0),0)
        self.assertEqual(r.data['totals'].get('failed_checks',0),0)

    def test_auto_time_uses_observed_active_intervals_only(self):
        r=Reliability();r.controller(True,BASE);r.controller(True,BASE+10);r.controller(True,BASE+1000);r.controller(False,BASE+1010)
        self.assertEqual(r.data['totals']['auto_observed_seconds'],10)

    def test_stopped_held_stale_and_malformed_controller_do_not_invent_runtime(self):
        state={'phase':'RUNNING','id':'a'*32,'revision':'r'};intent={'mode':'on','id':'a'*32,'revision':'r'}
        native={'mode':'continuous-pair','state':'OBSERVING','time':BASE}
        self.assertTrue(active_controller(native,state,intent,BASE+10))
        for override in ({'time':None},{'time':True},{'time':'bad'},{'time':BASE-100},{'state':'STOPPED-ON-RESERVE'}):
            self.assertFalse(active_controller(dict(native,**override),state,intent,BASE+10))
        self.assertFalse(active_controller(native,state,dict(intent,mode='off'),BASE+10))

    def test_corrupt_or_secret_bearing_retained_schema_is_rejected(self):
        r=Reliability();r.observe(probe(BASE,'DNS-001'));data=r.export()
        for mutate in (lambda d:d['events'][0].update(token='SECRET'),lambda d:d['totals'].update(outages=True),lambda d:d['profiles']['wireguard:peer_3'].update(state='garbage')):
            broken=copy.deepcopy(data);mutate(broken)
            with self.assertRaises(ValueError):Reliability(broken)


class TransitionStatisticsTests(unittest.TestCase):
    def base(self,state,**kw):return dict(state=state,source='wireguard:peer_3',target='openvpn:1_2',proof_scope='router-probed-ipv4',**kw)

    def test_commit_is_counted_once_across_status_oscillation_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            for offset,state in enumerate(('APPLYING','COMMITTED','DEGRADED-ON-RESERVE','COMMITTED','RESTORING','COMMITTED')):
                History(d).record(self.base(state,reason='SOURCE-FAILED' if state=='APPLYING' else 'CLIENT-CONFIRMED'),BASE+offset)
            h=History(d).public()
            self.assertEqual(h['totals']['attempts'],1);self.assertEqual(h['totals']['automatic_committed'],1)
            self.assertEqual(h['weekly']['automatic_committed'],1)

    def test_complete_legacy_history_replay_corrects_inflated_commit_counts(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d)
            for offset,state in enumerate(('APPLYING','COMMITTED','DEGRADED-ON-RESERVE','COMMITTED')):h.record(self.base(state),BASE+offset)
            old=h.load()
            for key in ('counter_version','counted','counted_state','counted_reason','totals','legacy_months'):old.pop(key,None)
            for event in old['events']:event.pop('counted_metrics',None)
            for month in old['months'].values():month['committed']=9;month['automatic_committed']=9
            h.path.write_text(json.dumps(h.envelope(old)))
            result=History(d).public()
            self.assertEqual(result['totals']['automatic_committed'],1)
            self.assertEqual(sum(m['automatic_committed'] for m in result['months'].values()),1)
            self.assertIn('complete',result['counter_accuracy'])

    def test_partial_legacy_counts_are_explicit_not_invented_exact(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d,limit=2)
            for i,state in enumerate(('APPLYING','COMMITTED','APPLYING','COMMITTED')):h.record(self.base(state),BASE+i)
            old=h.load();old.pop('counter_version');h.path.write_text(json.dumps(h.envelope(old)))
            result=History(d).public();self.assertIn('legacy partial',result['counter_accuracy'])

    def test_confirmed_return_has_its_own_counter(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);h.record(self.base('APPLYING'),BASE);h.record(self.base('COMMITTED'),BASE+1)
            h.record(self.base('ROLLED-BACK',original_restored=True,reason='PRIMARY-STABLY-RECOVERED'),BASE+2)
            h.record(self.base('OBSERVING'),BASE+3)
            self.assertEqual(h.public()['totals']['returns'],1)

    def test_manual_commit_is_not_counted_again_when_auto_resumes_observing_it(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d);h.record(self.base('APPLYING',reason='OPERATOR-MANUAL'),BASE)
            h.record(self.base('COMMITTED',manual=True),BASE+1)
            h.record(self.base('COMMITTED',reason='CLIENT-CONFIRMED'),BASE+2)
            totals=h.public()['totals']
            self.assertEqual(totals['committed'],1);self.assertEqual(totals['manual_committed'],1)
            self.assertEqual(totals['automatic_committed'],0)

    def test_week_pagination_is_bounded_and_uses_a_snapshot_watermark(self):
        with tempfile.TemporaryDirectory() as d:
            h=History(d)
            for i in range(130):h.record(self.base('APPLYING' if i%2==0 else 'COMMITTED'),BASE+i)
            first=page(Path(d),{'kind':'controller','after':0,'until':0},BASE+200)
            self.assertEqual(len(first['events']),100);self.assertTrue(first['has_more'])
            h.record(self.base('APPLYING'),BASE+201)
            second=page(Path(d),{'kind':'controller','after':first['next_after'],'until':first['until']},BASE+202)
            self.assertEqual(len(second['events']),30);self.assertFalse(second['has_more']);self.assertEqual(second['until'],130)
            expired=page(Path(d),{'kind':'controller','after':0,'until':0},BASE+WEEK+300)
            self.assertEqual(expired['events'],[]);self.assertEqual(expired['summary']['totals']['committed'],65)

    def test_rpc_rejects_bool_negative_extra_and_unknown_kind_without_writes(self):
        with tempfile.TemporaryDirectory() as d:
            args={'kind':'controller','after':0,'until':0}
            for override in ({'after':True},{'after':-1},{'until':True},{'kind':'raw'},{'secret':'x'}):
                with self.subTest(override=override),self.assertRaises(ValueError):page(Path(d),dict(args,**override),BASE)
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_failed_check_export_reads_real_durable_checkpoint(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'PERSIST',Path(d)),patch('agent.time.time',return_value=BASE+30):
            a=agent.Accounting();a.observe(probe(BASE,'DNS-001'));a.observe(probe(BASE+10));agent.checkpoint(a)
            result=page(Path(d),{'kind':'failures','after':0,'until':0},BASE+30)
            self.assertEqual([row['kind'] for row in result['events']],['FAILURE','RECOVERY'])
            self.assertEqual(result['summary']['totals']['outages'],1)
            self.assertIsNone(result['storage_notice'])


if __name__=='__main__':unittest.main()
