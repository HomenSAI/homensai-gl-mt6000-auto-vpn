"""Saved website response is a separate event-time metric, never an RTT relabel."""
import copy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_history as h
from test_website_response_history import snapshot,NOW,SETTINGS


def event(stamp=NOW):
    return {'state':'COMMITTED','time':stamp,'tx':'a'*32,'trial':False,'source':SETTINGS['plan_source'],'target':SETTINGS['plan_target'],
            'transition_metadata_present':True,'destination_role':'target','destination_profile_id':SETTINGS['plan_target'],
            'from_role':'source','from_profile_id':SETTINGS['plan_source'],'route_changed':True,
            'transition_completed':True,'transition_outcome':'committed','mode':'continuous-pair','proof_scope':'router-probed-ipv4'}


class WebsiteEventHistory(unittest.TestCase):
    def capture(self,status=None,value=None):
        status=snapshot()if status is None else status;value=event()if value is None else value
        return h.capture_website_response(value,status,status['profiles'][1],NOW)

    def test_saved_complete_sample_has_new_metric_and_original_timestamp(self):
        captured=self.capture();self.assertEqual(captured['avg_ms'],60);self.assertEqual(captured['time'],NOW)
        self.assertEqual(captured['metric'],'websites-https-mean-ms-v1');self.assertEqual(captured['site_ms'],[60,60,60])
        self.assertNotIn('rtt_ms',captured);self.assertNotIn('url',str(captured))

    def test_partial_destination_is_saved_as_explicit_coverage_without_mean(self):
        status=snapshot(partial=True);value=event();value.update(destination_role='source',destination_profile_id=SETTINGS['plan_source'])
        saved=h.capture_website_response(value,status,status['profiles'][0],NOW)
        self.assertIsNone(saved['avg_ms']);self.assertEqual(saved['successes'],2);self.assertEqual(saved['site_ms'],[30,30,None])

    def test_unknown_destination_reapply_or_unchanged_has_no_fabricated_sample(self):
        for change in ({'route_changed':False},{'activation_reapply':True},{'destination_profile_id':'wireguard:peer_99'}):
            value=event();value.update(change)
            with self.subTest(change=change):self.assertIsNone(self.capture(value=value))

    def test_snapshot_rejects_foreign_generation_stale_or_wrong_site_arithmetic(self):
        status=snapshot();binding=copy.deepcopy(status['profiles'][1]);binding['vendor_generation']='f'*32
        self.assertIsNone(h.capture_website_response(event(),status,binding,NOW))
        saved=self.capture()
        for change in ({'metric':'https-rtt-ms'},{'time':NOW-46},{'time':NOW+1},{'avg_ms':1},{'successes':2},
                       {'site_ms':[60,60,None]},{'site_ms':[True,60,60]}):
            raw=dict(saved,**change)
            with self.subTest(change=change):self.assertIsNone(h.clean_website_response(raw,event(),NOW))

    def test_record_preserves_old_technical_metric_and_new_metric_separately(self):
        with tempfile.TemporaryDirectory()as directory,patch('retention_settings.configured_days',return_value=7):
            history=h.History(directory);value=event();value['website_response']=self.capture()
            value['latency']={'profile':SETTINGS['plan_target'],'metric':'https-rtt-ms','time':NOW,'rtt_ms':999,'interface':'ovpnclient2','generation':'b'*32}
            history.record(value,now=NOW)
            saved=history.public(now=NOW)['events'][-1]
            self.assertEqual(saved['latency']['rtt_ms'],999);self.assertEqual(saved['website_response']['avg_ms'],60)
            value['website_response']['site_ms'][0]=500
            self.assertEqual(history.public(now=NOW)['events'][-1]['website_response']['site_ms'],[60,60,60])

    def test_new_website_sample_alone_does_not_write_or_count_a_second_transition(self):
        with tempfile.TemporaryDirectory()as directory,patch('retention_settings.configured_days',return_value=7):
            history=h.History(directory);value=event();value['website_response']=self.capture();history.record(value,now=NOW)
            path=Path(directory)/'native-history.json';before=path.read_bytes();totals=copy.deepcopy(history.load()['totals'])
            newer=copy.deepcopy(value);newer['time']=NOW+10;newer['website_response'].update(time=NOW+10,avg_ms=70,site_ms=[70,70,70])
            with patch.object(h,'atomic',wraps=h.atomic)as writes:history.record(newer,now=NOW+10)
            self.assertEqual(writes.call_count,0);self.assertEqual(path.read_bytes(),before);self.assertEqual(history.load()['totals'],totals)


if __name__=='__main__':unittest.main()
