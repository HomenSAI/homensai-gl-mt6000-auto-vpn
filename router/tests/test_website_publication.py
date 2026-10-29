"""Async results must reach both live channels and history before the next scan."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import website_response as W
from website_publication import publish_completed
from website_response_history import WebsiteResponseHistory
from agent import atomic_json,read_json
from test_icmp_ping import row,QueuedThread
from test_website_response import result


class Publication(unittest.TestCase):
    def setUp(self):
        QueuedThread.instances=[]
        self.profiles=[row(),row(id='openvpn:1_2',protocol='openvpn',interface='ovpnclient1',
            vendor_tunnel_id='openvpn:ovpnclient1',device='tun0',mark=8192,table='2001')]
        self.pair=dict(source=self.profiles[0]['id'],target=self.profiles[1]['id'])
        self.settings=dict(interval=300,plan_source=self.pair['source'],plan_target=self.pair['target'])
        self.sampler=W.WebsiteSampler(lambda:{},lambda _: {})
        self.history=WebsiteResponseHistory()
        with patch.object(W,'Thread',QueuedThread),patch.object(W.time,'monotonic',return_value=100):
            self.sampler.apply(self.profiles,self.pair,1000)
        self.status=dict(time=1000,profiles=copy.deepcopy(self.profiles),samples=[{'time':1000}],
            observation_valid_for=900,measurement_request_id='health-scan-1')
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.file=Path(self.directory.name)/'status.json'
        atomic_json(self.file,self.status)
        self.writes=0

    def completed(self,profile):
        return W.public(profile,'ok',None,1001,[result(t,100 if profile['id']==self.pair['source'] else 200) for t in W.TARGETS])

    def finish_batch(self):
        with patch.object(self.sampler,'measure',side_effect=self.completed):QueuedThread.instances[-1].run()

    def write(self,value):
        self.writes+=1;atomic_json(self.file,value)

    def publish(self,now=1002,writer=None):
        return publish_completed(self.status,self.pair,self.settings,self.sampler,self.history,
            writer or self.write,lambda:{},now)

    def test_both_completed_channels_reach_real_status_file_before_300_second_scan(self):
        self.finish_batch();original=copy.deepcopy(self.status)
        self.status=self.publish()
        saved=read_json(self.file)
        self.assertEqual([p['website_response']['avg_ms'] for p in saved['profiles']],[100,200])
        for field in ('time','samples','measurement_request_id','observation_valid_for'):
            self.assertEqual(saved[field],original[field])
        for before,after in zip(original['profiles'],saved['profiles']):
            self.assertEqual({k:v for k,v in before.items() if k!='website_response'},
                {k:v for k,v in after.items() if k!='website_response'})
        self.assertEqual(saved['website_response_history']['statistics']['source']['complete_samples'],1)
        self.assertEqual(saved['website_response_history']['statistics']['target']['complete_samples'],1)
        self.assertEqual(len(QueuedThread.instances),1)

    def test_no_write_or_probe_when_batch_has_not_finished(self):
        self.assertIs(self.publish(),self.status);self.assertEqual(self.writes,0)
        self.assertEqual(len(QueuedThread.instances),1)

    def test_first_channel_is_published_while_second_is_still_waiting(self):
        first=self.profiles[0]
        self.sampler.cache[W.signature(first)]=self.completed(first)
        self.status=self.publish()
        self.assertEqual([p['website_response']['state'] for p in self.status['profiles']],['ok','checking'])
        self.finish_batch();self.status=self.publish()
        self.assertEqual([p['website_response']['state'] for p in self.status['profiles']],['ok','ok'])
        self.assertEqual(self.history.data['seen'],{p['id']:1001 for p in self.profiles})

    def test_repeated_collection_never_duplicates_history_or_disk_writes(self):
        self.finish_batch();self.status=self.publish()
        for _ in range(3):self.status=self.publish()
        self.assertEqual(self.writes,1)
        self.assertEqual(self.history.public(1002)['statistics']['source']['complete_samples'],1)

    def test_failed_ram_write_keeps_snapshot_retryable_and_history_count_exact(self):
        self.finish_batch();original=copy.deepcopy(self.status)
        with self.assertRaises(OSError):self.publish(writer=Mock(side_effect=OSError('full')))
        self.assertEqual(self.status,original);self.assertEqual(read_json(self.file),original)
        self.status=self.publish()
        self.assertEqual(self.history.public(1002)['statistics']['target']['complete_samples'],1)

    def test_expired_measurement_loses_number_without_refreshing_health_clock(self):
        self.finish_batch();self.status=self.publish();self.status=self.publish(now=1047)
        self.assertEqual([p['website_response']['state'] for p in self.status['profiles']],['stale','stale'])
        self.assertTrue(all(p['website_response']['avg_ms'] is None for p in self.status['profiles']))
        self.assertEqual(self.status['time'],1000)
        self.assertEqual(self.history.public(1047)['statistics']['source']['complete_samples'],1)

    def test_generation_pair_or_binding_change_cannot_publish_old_results(self):
        self.finish_batch()
        for change in ({'vendor_generation':'b'*32},{'mark':65536},{'administrative_state':'disabled'}):
            with self.subTest(change=change):
                rows=[dict(p,**change) for p in self.profiles]
                self.assertFalse(self.sampler.collect(rows,self.pair,1002))
        self.assertFalse(self.sampler.collect(self.profiles,{'source':'wireguard:peer_99'},1002))

    def test_pause_and_shutdown_do_not_publish_late_results(self):
        self.finish_batch();self.sampler.paused=lambda:True
        self.assertIs(self.publish(),self.status)
        self.sampler.paused=lambda:False;self.sampler.close()
        self.assertIs(self.publish(),self.status);self.assertEqual(self.writes,0)

    def test_transient_history_failure_retries_same_measurement_once(self):
        self.finish_batch();observe=self.history.observe
        with patch.object(self.history,'observe',side_effect=OSError('transient')):
            self.status=self.publish()
        self.assertEqual(self.status['website_response_history']['notice'],'WEBSITE-HISTORY-UNAVAILABLE')
        with patch.object(self.history,'observe',wraps=observe) as retry:
            self.status=self.publish(now=1003)
            self.status=self.publish(now=1004)
        retry.assert_called_once();self.assertEqual(self.writes,2)
        self.assertIsNone(self.status['website_response_history']['notice'])
        self.assertEqual(self.status['website_response_history']['statistics']['source']['complete_samples'],1)
        self.assertEqual(len(QueuedThread.instances),1)

    def test_public_history_failure_after_observe_never_counts_sample_twice(self):
        self.finish_batch()
        with patch.object(self.history,'public',side_effect=ValueError('transient')):
            self.status=self.publish()
        self.status=self.publish(now=1003)
        for role in ('source','target'):
            self.assertEqual(self.status['website_response_history']['statistics'][role]['complete_samples'],1)

    def test_persistent_history_error_retries_without_duplicate_status_writes(self):
        self.finish_batch()
        with patch.object(self.history,'observe',side_effect=OSError('unavailable')) as retry:
            for stamp in (1002,1003,1004):self.status=self.publish(now=stamp)
        self.assertEqual(retry.call_count,3);self.assertEqual(self.writes,1)
        self.assertEqual(len(QueuedThread.instances),1)

    def test_failed_ram_write_during_history_retry_remains_retryable(self):
        self.finish_batch()
        with patch.object(self.history,'observe',side_effect=OSError('transient')):
            self.status=self.publish()
        original=copy.deepcopy(self.status)
        with self.assertRaises(OSError):self.publish(now=1003,writer=Mock(side_effect=OSError('full')))
        self.assertEqual(self.status,original)
        self.status=self.publish(now=1004)
        self.assertIsNone(self.status['website_response_history']['notice'])
        self.assertEqual(self.status['website_response_history']['statistics']['source']['complete_samples'],1)

    def test_outstanding_history_retry_obeys_pause_and_reset_floor(self):
        self.finish_batch()
        with patch.object(self.history,'observe',side_effect=OSError('transient')):
            self.status=self.publish()
        self.sampler.paused=lambda:True
        with patch.object(self.history,'observe') as observe:
            self.assertIs(self.publish(now=1003),self.status)
        observe.assert_not_called();self.assertEqual(self.writes,1)
        self.sampler.paused=lambda:False;self.history.clear(now=1003)
        self.status=self.publish(now=1004)
        self.assertIsNone(self.status['website_response_history']['notice'])
        self.assertEqual(self.status['website_response_history']['statistics']['source']['complete_samples'],0)

    def test_expiry_stays_final_after_wall_clock_backwards_in_collect_and_apply(self):
        with patch.object(W.time,'monotonic',return_value=101):
            self.finish_batch();self.status=self.publish()
            self.status=self.publish(now=1047);self.status=self.publish(now=1040)
            self.assertTrue(all(p['website_response']['state']=='stale' for p in self.status['profiles']))
            profiles=[dict(p,time=1040) for p in self.profiles]
            self.sampler.apply(profiles,self.pair,1040)
        self.assertTrue(all(p['website_response']['state']=='stale' for p in profiles))
        self.assertEqual(len(QueuedThread.instances),1)

    def test_monotonic_lifetime_expires_even_if_wall_clock_has_not_reached_ttl(self):
        with patch.object(W.time,'monotonic',return_value=101):self.finish_batch()
        with patch.object(W.time,'monotonic',return_value=102):self.status=self.publish()
        with patch.object(W.time,'monotonic',return_value=147):self.status=self.publish(now=1030)
        self.assertTrue(all(p['website_response']['state']=='stale' for p in self.status['profiles']))
        self.assertEqual(self.status['time'],1000)
        # A genuinely new result can replace the expired one after clock repair.
        def fresh(profile):return dict(self.completed(profile),time=1011)
        with patch.object(W.time,'monotonic',return_value=148),patch.object(self.sampler,'measure',side_effect=fresh):
            self.sampler.run_batch([(W.signature(p),p) for p in self.profiles])
        with patch.object(W.time,'monotonic',return_value=149):self.status=self.publish(now=1012)
        self.assertTrue(all(p['website_response']['state']=='ok' for p in self.status['profiles']))
        self.assertTrue(all(p['website_response']['valid_for']==45 for p in self.status['profiles']))

    def test_expiry_first_seen_by_apply_is_also_final(self):
        with patch.object(W.time,'monotonic',return_value=101):
            self.finish_batch()
            profiles=[dict(p,time=1047) for p in self.profiles]
            self.sampler.apply(profiles,self.pair,1047)
            self.assertTrue(all(p['website_response']['state']=='stale' for p in profiles))
            self.status=self.publish(now=1040)
        self.assertTrue(all(p['website_response']['state']=='stale' for p in self.status['profiles']))


if __name__=='__main__':unittest.main()
