"""New website metric persistence, coverage, original timestamps and reset ownership."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,stats_reset,website_response as web
from latency_history import LatencyHistory
from website_response_history import WebsiteResponseHistory,measurement,technical_history_tail,DAY

NOW=180000
SETTINGS={'plan_source':'wireguard:peer_1','plan_target':'openvpn:1_2'}


def snapshot(stamp=NOW,source=30,target=60,partial=False):
    rows=[]
    for identifier,protocol,interface,generation,delay in (
            (SETTINGS['plan_source'],'wireguard','wgclient1','a'*32,source),
            (SETTINGS['plan_target'],'openvpn','ovpnclient2','b'*32,target)):
        row={'id':identifier,'protocol':protocol,'interface':interface,'vendor_tunnel_id':protocol+':'+interface,
             'vendor_generation':generation,'vendor_state':'SETTLED','time':stamp,'code':None,'dns_ok':True,'https_success':2,'rtt_ms':999}
        results=[{'id':key,'url':'https://'+host+path,'state':'ok','elapsed_ms':delay,'code':None}for key,host,path,_ in web.TARGETS]
        if partial and not rows:results[-1].update(state='failed',elapsed_ms=None,code='WEBSITE-TIMEOUT')
        row['website_response']=web.public(row,'partial'if partial and not rows else'ok',None,stamp,results);rows.append(row)
    return {'time':stamp,'profiles':rows,'native_failover':{} }


class WebsiteHistoryTests(unittest.TestCase):
    def observe(self,h,s,now=None):h.observe(s,SETTINGS,s['time']if now is None else now)

    def test_new_history_starts_empty_and_never_relabels_old_https_data(self):
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'latency-history.json';old=LatencyHistory();old.save(path,agent.atomic_json,NOW);before=path.read_bytes()
            new=WebsiteResponseHistory.load(path)
            self.assertEqual(new.notice,'WEBSITE-HISTORY-UNAVAILABLE');self.assertEqual(new.public(NOW)['rows'],[])
            with self.assertRaises(ValueError):new.save(path,agent.atomic_json,NOW)
            self.assertEqual(path.read_bytes(),before)

    def test_complete_metric_is_independent_of_the_old_health_rtt(self):
        h=WebsiteResponseHistory();s=snapshot();s['profiles'][0].update(code='DNS-001',dns_ok=False,https_success=0,rtt_ms=9999)
        self.observe(h,s);self.assertEqual(h.public(NOW)['rows'][0][1:5],[300,600,1,1])
        self.assertEqual(h.public(NOW)['metric'],web.METRIC);self.assertEqual(h.public(NOW)['target_set'],web.TARGET_SET)

    def test_partial_cycle_is_a_gap_with_explicit_success_coverage(self):
        h=WebsiteResponseHistory();self.observe(h,snapshot(partial=True));p=h.public(NOW)
        self.assertEqual(p['rows'][0][1:5],[None,600,0,1]);self.assertEqual(p['coverage_rows'][0][1:],[2,3,3,3,1,0])
        self.assertEqual(p['statistics']['source']['cycles'],1);self.assertEqual(p['statistics']['source']['complete'],0)
        self.assertIsNone(p['statistics']['source']['avg_ms'])

    def test_repeated_cached_sample_is_not_counted_again_and_public_does_not_renew_time(self):
        h=WebsiteResponseHistory();s=snapshot();self.observe(h,s);self.observe(h,s,NOW+10)
        before=copy.deepcopy(h.data);h.public(NOW+100)
        self.assertEqual(h.data,before);self.assertEqual(h.public(NOW)['rows'][0][3:5],[1,1])

    def test_period_average_weights_original_complete_cycle_counts(self):
        h=WebsiteResponseHistory()
        for stamp,value in ((NOW,10),(NOW+30,30),(NOW+60,90)):self.observe(h,snapshot(stamp,value,value))
        stats=h.public(NOW+60)['statistics']['source']
        self.assertEqual(stats['complete_samples'],3);self.assertEqual(stats['sum_ms'],130);self.assertEqual(stats['avg_ms'],43.3)
        self.assertEqual(h.public(NOW+60)['rows'][0][1],400)

    def test_original_measurement_minute_is_used_even_when_first_published_later(self):
        h=WebsiteResponseHistory();s=snapshot(NOW+50);self.observe(h,s,NOW+65)
        rows=h.public(NOW+65)['rows'];self.assertEqual(rows[0][0],NOW);self.assertEqual(rows[0][1],300)
        self.assertEqual(rows[1][0],NOW+60);self.assertIsNone(rows[1][1])

    def test_mismatched_binding_or_metric_never_uses_the_old_rtt_fallback(self):
        mutations=[lambda p:p['website_response'].update(metric='https-rtt-ms'),
                   lambda p:p['website_response'].update(target_set='other'),
                   lambda p:p['website_response'].update(generation='f'*32),
                   lambda p:p['website_response'].update(interface='wgclient3'),
                   lambda p:p.update(vendor_state='CHANGING'),lambda p:p.update(administrative_state='disabled')]
        for mutate in mutations:
            h=WebsiteResponseHistory();s=snapshot();mutate(s['profiles'][0]);self.observe(h,s)
            with self.subTest(mutate=mutate):self.assertIsNone(h.public(NOW)['rows'][0][1])

    def test_stale_future_and_malformed_complete_results_are_rejected(self):
        for mutation in (lambda p:p['website_response'].update(time=NOW-46),lambda p:p['website_response'].update(time=NOW+1),
                         lambda p:p['website_response'].update(successes=2),lambda p:p['website_response'].update(avg_ms=1),
                         lambda p:p['website_response'].update(avg_ms=30.1),
                         lambda p:p['website_response']['results'][0].update(elapsed_ms=True),
                         lambda p:p['website_response']['results'][0].update(url='https://example.invalid/'),
                         lambda p:p['website_response']['results'].__setitem__(0,copy.deepcopy(p['website_response']['results'][1]))):
            s=snapshot();mutation(s['profiles'][0]);self.assertIsNone(measurement(s['profiles'][0],NOW))

    def test_partial_cannot_supply_a_quiet_two_site_average_or_timeout_zero(self):
        s=snapshot(partial=True);s['profiles'][0]['website_response']['avg_ms']=20
        self.assertIsNone(measurement(s['profiles'][0],NOW))
        s=snapshot(partial=True);s['profiles'][0]['website_response']['results'][-1]['elapsed_ms']=0
        self.assertIsNone(measurement(s['profiles'][0],NOW))

    def test_save_load_roundtrip_and_corrupt_file_is_preserved(self):
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'website-response-history.json';h=WebsiteResponseHistory();self.observe(h,snapshot())
            h.save(path,agent.atomic_json,NOW);loaded=WebsiteResponseHistory.load(path)
            self.assertEqual(loaded.public(NOW)['rows'],h.public(NOW)['rows'])
            path.write_bytes(b'failed evidence');loaded=WebsiteResponseHistory.load(path)
            with self.assertRaises(ValueError):loaded.save(path,agent.atomic_json,NOW+1)
            self.assertEqual(path.read_bytes(),b'failed evidence')

    def test_retention_and_long_week_transport_keep_coverage_aligned(self):
        h=WebsiteResponseHistory()
        for index in range(1450):self.observe(h,snapshot(NOW+index*60))
        p=h.public(NOW+1449*60)
        self.assertEqual(len(json.loads(p['rows_json'])),1450);self.assertEqual(len(json.loads(p['coverage_rows_json'])),1450)
        h.observe(snapshot(NOW+3*DAY),dict(SETTINGS,history_days='1'),NOW+3*DAY)
        self.assertTrue(all(r[0]>=NOW+2*DAY for r in h.data['rows']));h.validate()

    def test_unknown_pair_after_retention_does_not_leave_invalid_current_key(self):
        h=WebsiteResponseHistory();self.observe(h,snapshot())
        h.observe({'profiles':[]},{'history_days':'1'},NOW+3*DAY);h.validate();self.assertEqual(h.public(NOW+3*DAY)['pair'],[])

    def test_quality_reset_archives_before_watermark_and_preserves_chart_points(self):
        with tempfile.TemporaryDirectory()as directory:
            h=WebsiteResponseHistory();s=snapshot();self.observe(h,s);original=copy.deepcopy(h.data)
            accounting,old,result=stats_reset.apply({'scope':'quality','nonce':'a'*32},agent.Accounting(),LatencyHistory(),NOW+10,agent.atomic_json,persist=directory,website_response=h)
            self.assertTrue(result['done']);self.assertEqual(h.data['rows'],original['rows']);self.assertEqual(h.data['stats_since'],NOW+60)
            archived=json.loads((Path(directory)/'stats-archive'/result['archive']).read_text())
            self.assertEqual(archived['data']['website_response'],original)
            self.observe(h,s,NOW+20);self.assertEqual(h.public(NOW+20)['statistics']['source']['complete'],0)
            self.observe(h,snapshot(NOW+60));self.assertEqual(h.public(NOW+60)['statistics']['source']['complete'],1)

    def test_latency_reset_clears_both_series_only_after_archiving(self):
        with tempfile.TemporaryDirectory()as directory:
            h=WebsiteResponseHistory();self.observe(h,snapshot());old=LatencyHistory();old.data['seen']={'wireguard:peer_1':NOW}
            _,new_old,result=stats_reset.apply({'scope':'latency','nonce':'a'*32},agent.Accounting(),old,NOW,agent.atomic_json,persist=directory,website_response=h)
            self.assertTrue(result['done']);self.assertEqual(h.public(NOW)['rows'],[]);self.assertEqual(new_old.data['seen'],{})
            archived=json.loads((Path(directory)/'stats-archive'/result['archive']).read_text())['data']
            self.assertIn('latency',archived);self.assertIn('website_response',archived)

    def test_failed_reset_archive_preserves_both_data_and_quality_watermark(self):
        with tempfile.TemporaryDirectory()as directory:
            h=WebsiteResponseHistory();self.observe(h,snapshot());before=copy.deepcopy(h.data)
            def broken(*args):raise OSError('full')
            _,_,result=stats_reset.apply({'scope':'quality','nonce':'a'*32},agent.Accounting(),LatencyHistory(),NOW+10,broken,persist=directory,website_response=h)
            self.assertFalse(result['done']);self.assertEqual(h.data,before)

    def test_latency_reset_floor_survives_reload_and_rejects_old_cached_samples(self):
        with tempfile.TemporaryDirectory()as directory:
            h=WebsiteResponseHistory();cached=snapshot();self.observe(h,cached);h.clear(NOW+10)
            path=Path(directory)/'new.json';h.save(path,agent.atomic_json,NOW+10);h=WebsiteResponseHistory.load(path)
            self.observe(h,cached,NOW+20);self.assertTrue(all(r[1]is None for r in h.public(NOW+20)['rows']))
            self.observe(h,snapshot(NOW+30));self.assertEqual(h.public(NOW+30)['statistics']['source']['complete'],1)

    def test_schema_rejects_partial_cycles_claiming_three_successful_sites(self):
        h=WebsiteResponseHistory();self.observe(h,snapshot(partial=True));h.data['rows'][0][7]=3
        with self.assertRaises(ValueError):h.validate()

    def test_technical_rpc_tail_does_not_change_the_legacy_public_object_or_file(self):
        original={'metric':'https-rtt-ms','rows':[[NOW-2*DAY,9,9,1,1,'off'],[NOW,8,8,1,1,'off']],
                  'rows_count':10000,'rows_json':'full old week remains on flash'}
        before=copy.deepcopy(original);tail=technical_history_tail(original,NOW)
        self.assertEqual(original,before);self.assertNotIn('rows_json',tail);self.assertEqual(len(tail['rows']),1)
        self.assertEqual(tail['retained_rows_count'],10000);self.assertEqual(tail['served_rows_count'],1)
        self.assertTrue(tail['technical_history_tail_only']);self.assertEqual(tail['metric'],'https-rtt-ms')

    def test_full_new_week_survives_status_transport_with_max_live_samples_and_events(self):
        from website_response_history import MAX_ROWS
        h=WebsiteResponseHistory();self.observe(h,snapshot());key=h.data['current']
        epoch=1793197800
        h.data['rows']=[[epoch+i*60,6000,6000,3,3,'unknown',key,9,9,9,9,0,0]for i in range(MAX_ROWS)]
        last=epoch+(MAX_ROWS-1)*60;new=h.public(last)
        old=technical_history_tail({'metric':'https-rtt-ms','rows':new['rows'],'rows_count':MAX_ROWS,'rows_json':'old full history'},last)
        reply={'website_response_history':new,'latency_history':old,'profiles':snapshot(last)['profiles'],
               'accounting':{'quality':{'legacy_technical':{'rtt_sum':999}}},
               'samples':[{'time':last,'rtt_ms':999,'probe_checks':['x'*200]*3}for _ in range(1000)],
               'events':[{'time':last,'code':'OK','website_response':snapshot(last)['profiles'][0]['website_response']}for _ in range(300)],
               'native_history':{'events':[{'time':last,'codes':['PAIR-WATCHING'],'phase_evidence':['x'*100]*32}for _ in range(300)]}}
        agent.trim_status_reply(reply)
        self.assertLessEqual(len(json.dumps(reply,ensure_ascii=True).encode()),900000)
        self.assertEqual(json.loads(reply['website_response_history']['rows_json']),json.loads(new['rows_json']))
        self.assertEqual(json.loads(reply['website_response_history']['coverage_rows_json']),json.loads(new['coverage_rows_json']))

    def test_corrupt_new_store_refuses_reset_and_two_checkpoints_preserve_exact_bytes(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);path=root/'website-response-history.json';raw=b'corrupt website evidence';path.write_bytes(raw)
            h=WebsiteResponseHistory.load(path);accounting=agent.Accounting();old=LatencyHistory()
            for scope in ('latency','quality','ranking','all'):
                _,_,result=stats_reset.apply({'scope':scope,'nonce':'a'*32},accounting,old,NOW,agent.atomic_json,persist=root,website_response=h)
                self.assertFalse(result['done']);self.assertEqual(result['code'],'WEBSITE-HISTORY-UNAVAILABLE')
                self.assertFalse((root/'stats-archive').exists());self.assertEqual(path.read_bytes(),raw)
            with patch.object(agent,'PERSIST',root):
                agent.checkpoint(accounting,old,h);agent.checkpoint(accounting,old,h)
            self.assertEqual(h.notice,'WEBSITE-HISTORY-UNAVAILABLE');self.assertEqual(path.read_bytes(),raw)

    def test_transport_retains_original_tenths_sum_for_unequal_bucket_means(self):
        h=WebsiteResponseHistory()
        for stamp,value in ((NOW,10.1),(NOW+30,10.2),(NOW+60,10.1)):self.observe(h,snapshot(stamp,value,value))
        p=h.public(NOW+60);self.assertEqual(p['row_encoding'],'sum-tenths')
        self.assertEqual(p['rows'][0][1],203);self.assertEqual(p['rows'][1][1],101)
        total=sum(r[1]for r in p['rows']);count=sum(r[3]for r in p['rows'])
        self.assertEqual(web.mean_from_tenths(total,count),10.1);self.assertEqual(p['statistics']['source']['avg_ms'],10.1)
        self.assertEqual(p['statistics']['source']['sum_tenths'],304)

    def test_new_metric_rounds_exact_half_up_without_changing_legacy_health_rounding(self):
        self.assertEqual(web.round_ms(10.25),10.3);self.assertEqual(web.mean_from_tenths(205,2),10.3)
        h=WebsiteResponseHistory()
        self.observe(h,snapshot(NOW,10.2,10.2));self.observe(h,snapshot(NOW+30,10.3,10.3))
        self.assertEqual(h.public(NOW+30)['statistics']['source']['avg_ms'],10.3)


if __name__=='__main__':unittest.main()
