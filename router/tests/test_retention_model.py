"""Statistics retention by time or by size (owner, 31 Oct 2026): options, legacy mapping, size model, setup_stats
payload codes, the size-mode trim, 30-day caps of every consumer, and the Lua line (lua/retention.lua, the monitor's
consumers) against the Python code on the same inputs (runs where lua5.1 exists: homensai-vpn-python39:local)."""
import copy
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(ROOT))
import retention_settings as R  # noqa: E402
import stats_mode  # noqa: E402
import setup_config  # noqa: E402

LUA=shutil.which('lua5.1')
DRIVER=Path(__file__).resolve().parent/'lua/retention_driver.lua'
A,B='wireguard:peer_1','openvpn:1_1'


def lua_driver(cases):
    reply=subprocess.run([LUA,str(DRIVER)],input=json.dumps(cases).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=300)
    return json.loads(reply.stdout.decode())


def minute_rows(kind,count,start=1793000040,seed=1):
    rng=random.Random(seed);key=__import__('hashlib').sha256((A+'\0'+B).encode()).hexdigest()[:16];rows=[]
    for i in range(count):
        if kind=='latency':
            a=rng.uniform(10,400);b=rng.uniform(10,400)
            rows.append([start+60*i,(a*2+b)/3,(b*3+a)/4,3,4,'source',key])
        else:
            rows.append([start+60*i,round(rng.uniform(10,600),1),None if i%5==0 else round(rng.uniform(10,600),1),1,0 if i%5==0 else 1,'target',key,3,0 if i%5==0 else 3,3,3,0,1 if i%5==0 else 0])
    return key,rows


def latency_data(count,**kw):
    key,rows=minute_rows('latency',count,**kw)
    return {'version':1,'rows':rows,'pairs':{key:[A,B]},'current':key,'seen':{A:1793000000.5,B:1793000001.25},'saved':None}


def ping_data(count,**kw):
    from ping_response_history import PingResponseHistory
    key,rows=minute_rows('ping',count,**kw)
    data=PingResponseHistory.empty();data.update(rows=rows,pairs={key:[A,B]},current=key,seen={A:1793000000.5,B:1793000001.25})
    return data


SETTINGS=[{},{'history_days':3},{'history_days':'5'},{'history_days':'x'},{'history_days':9},{'history_days':True},
          {'stats_retention_mode':'time','stats_retention_days':14},{'stats_retention_mode':'time','stats_retention_days':'30'},
          {'stats_retention_mode':'time','stats_retention_days':8,'history_days':2},{'stats_retention_mode':'other','stats_retention_days':30,'history_days':4},
          {'stats_retention_mode':'size','stats_retention_mb':4,'interval':10},{'stats_retention_mode':'size','stats_retention_mb':'1','interval':300},
          {'stats_retention_mode':'size','stats_retention_mb':32,'interval':60,'response_compare':True},
          {'stats_retention_mode':'size','stats_retention_mb':33,'interval':10},{'stats_retention_mode':'size','stats_retention_mb':0},
          {'stats_retention_mode':'size','stats_retention_mb':2,'interval':45,'response_compare':'1','response_metric':'websites'},
          {'stats_retention_mode':'time','stats_retention_days':7,'interval':5},{'stats_retention_mode':'time','stats_retention_days':1,'interval':'120'}]
PAYLOADS=['{"mode":"retention","retention":"time","days":1}','{"mode":"retention","retention":"time","days":7}',
          '{"mode":"retention","retention":"time","days":14}','{"mode":"retention","retention":"time","days":30}',
          '{"mode":"retention","retention":"size","mb":1}','{"mode":"retention","retention":"size","mb":32}',
          '{"mode":"retention","retention":"time","days":8}','{"mode":"retention","retention":"time","days":0}',
          '{"mode":"retention","retention":"time","days":7.0}','{"mode":"retention","retention":"time","days":"7"}',
          '{"mode":"retention","retention":"time","days":true}','{"mode":"retention","retention":"time"}',
          '{"mode":"retention","retention":"time","days":7,"mb":4}','{"mode":"retention","retention":"size","mb":0}',
          '{"mode":"retention","retention":"size","mb":33}','{"mode":"retention","retention":"size","mb":4.5}',
          '{"mode":"retention","retention":"size","days":7}','{"mode":"retention","retention":"other","days":7}',
          '{"mode":"retention"}','{"mode":"retention","retention":["time"],"days":7}']


def python_payload(text):
    try:return 'OK',stats_mode.payload(json.loads(text),1000.0)['main']
    except ValueError as error:return 'ERR',str(error)


class RetentionModel(unittest.TestCase):
    def test_default_and_legacy_mapping_keep_todays_behaviour(self):
        self.assertEqual(R.choice({}),('time',7,4));self.assertEqual(R.days({}),7);self.assertEqual(R.days(None),7)
        for raw,days in ((1,1),('2',2),(7,7),(8,7),('x',7),(True,7),(2.0,7)):
            self.assertEqual(R.days({'history_days':raw}),days,raw)
        self.assertEqual(R.days({'history_days':2,'stats_retention_mode':'time','stats_retention_days':30}),30,'the new option wins')
        self.assertEqual(R.days({'history_days':2,'stats_retention_mode':'time','stats_retention_days':9}),2,'an invalid stop falls back to the old option')
        self.assertEqual(R.days({'history_days':2,'stats_retention_days':30}),2,'days without a mode do not count')

    def test_size_model_numbers(self):
        self.assertEqual(R.estimate({'interval':10},7),{'flash':2468732,'ram':13196722,'work_flash':976892,'work_ram':3419122})
        self.assertEqual(R.estimate({'interval':60,'response_compare':True},30),{'flash':9666301,'ram':56770133,'work_flash':4186680,'work_ram':14653380})
        self.assertEqual([R.size_days({'interval':10},mb) for mb in (1,2,4,8,12,32)],[2,5,11,23,30,30])
        self.assertEqual(R.size_days({'interval':300},1),5);self.assertEqual(R.size_days({'interval':10,'response_compare':True},1),2)
        resolved=R.resolve({'interval':10,'stats_retention_mode':'size','stats_retention_mb':4})
        self.assertEqual(resolved,{'mode':'size','days':7,'mb':4,'effective_days':11,'latency_bytes':1352924,'response_bytes':1181668})
        self.assertLessEqual(resolved['latency_bytes']+resolved['response_bytes']+2*11*R.MODEL['accounting_day_flash'],4*R.MIB)
        public=R.public({'interval':10});self.assertEqual(public['day_stops'],[1,2,3,4,5,6,7,14,30]);self.assertEqual(public['model'],R.MODEL)
        self.assertEqual(public['estimate'],R.estimate({'interval':10},7))
        json.dumps(public,allow_nan=False)

    def test_setup_stats_payload_and_codes(self):
        self.assertEqual(python_payload(PAYLOADS[3]),('OK',{'stats_retention_mode':'time','stats_retention_days':'30','history_days':'7'}))
        self.assertEqual(python_payload(PAYLOADS[0]),('OK',{'stats_retention_mode':'time','stats_retention_days':'1','history_days':'1'}))
        self.assertEqual(python_payload(PAYLOADS[5]),('OK',{'stats_retention_mode':'size','stats_retention_mb':'32'}))
        codes={text:python_payload(text)[1] for text in PAYLOADS[6:]}
        self.assertEqual(set(codes.values()),{'STATS-RETENTION-DAYS','STATS-RETENTION-SIZE','STATS-RETENTION-FIELDS'})
        self.assertEqual(codes['{"mode":"retention","retention":"time","days":7.0}'],'STATS-RETENTION-DAYS')
        self.assertEqual(codes['{"mode":"retention","retention":"size","mb":33}'],'STATS-RETENTION-SIZE')
        self.assertEqual(codes['{"mode":"retention","retention":"time","days":7,"mb":4}'],'STATS-RETENTION-FIELDS')
        # Work/Diagnostics and the old wizard keep their exact rules.
        self.assertEqual(stats_mode.payload({'mode':'work'})['main'],{'stats_mode':'work','stats_until':'0'})
        with self.assertRaises(ValueError):setup_config.monitor_payload(dict(interval=30,checkpoint=900,probe_limit=2,planning_enabled=False,history_days=14))
        # Every key the payload writes is allowed by the UCI writer.
        allowed=(ROOT/'setup_save.lua').read_text()
        for key in ('stats_retention_mode','stats_retention_days','stats_retention_mb','history_days'):self.assertIn(key+'=true',allowed)

    def test_trim_drops_only_the_oldest_rows_until_the_budget_fits(self):
        data=latency_data(3000);before=copy.deepcopy(data)
        size=len(json.dumps(data,separators=(',',':')).encode())
        self.assertEqual(R.trim_to_budget(data,None),0);self.assertEqual(data,before)
        self.assertEqual(R.trim_to_budget(data,size),0)
        dropped=R.trim_to_budget(data,size//3)
        self.assertGreater(dropped,0);self.assertEqual(data['rows'],before['rows'][dropped:])
        self.assertLessEqual(len(json.dumps(data,separators=(',',':')).encode()),size//3)
        self.assertEqual(R.trim_to_budget(data,10),len(before['rows'])-dropped);self.assertEqual(data['rows'],[])

    def test_size_mode_save_keeps_the_file_within_its_share(self):
        from latency_history import LatencyHistory
        from ping_response_history import PingResponseHistory
        from agent import atomic_json
        with tempfile.TemporaryDirectory() as d:
            h=LatencyHistory(latency_data(5000));h.byte_budget=100000;h.save(Path(d)/'l.json',atomic_json,1793400000.0)
            self.assertLessEqual(len(json.dumps(h.data,separators=(',',':')).encode()),100000)
            self.assertIsNone(LatencyHistory.load(Path(d)/'l.json').notice)
            p=PingResponseHistory(ping_data(5000));p.byte_budget=50000;p.save(Path(d)/'p.json',atomic_json,1793400000.0)
            loaded=PingResponseHistory.load(Path(d)/'p.json');self.assertIsNone(loaded.notice);self.assertEqual(loaded.data['rows'],p.data['rows'])
            self.assertLess(len(p.data['rows']),5000)

    def test_thirty_days_are_accepted_by_every_consumer(self):
        from latency_history import LatencyHistory,MAX_ROWS
        from website_response_history import MAX_ROWS as RESPONSE_ROWS
        from reliability import Reliability
        from native_history import History
        self.assertEqual((MAX_ROWS,RESPONSE_ROWS),(30*1440+1,30*1440+1))
        Reliability(detail_days=30);History(tempfile.mkdtemp(),detail_days=30)
        for bad in (0,31):
            with self.assertRaises(ValueError):Reliability(detail_days=bad)
        month=LatencyHistory(latency_data(30*1440));self.assertEqual(len(month.data['rows']),30*1440)
        public=month.public();self.assertEqual(public['rows_count'],30*1440);self.assertEqual(len(json.loads(public['rows_json'])),7*1440+1,'the transport carries the newest week')


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class RetentionLuaDifferential(unittest.TestCase):
    def test_choice_days_model_public_and_budgets(self):
        cases=[{'op':'public','settings':s} for s in SETTINGS]+[{'op':'estimate','settings':s,'days':d} for s in SETTINGS[10:13] for d in R.DAY_STOPS]
        cases+=[{'op':'size_days','settings':{'interval':i,'response_compare':c},'mb':mb} for i in (10,59,60,120,300) for c in (False,True) for mb in (1,3,8,32)]
        for case,actual in zip(cases,lua_driver(cases)):
            with self.subTest(case=case):
                s=case['settings']
                expected={'public':lambda:R.public(s),'estimate':lambda:R.estimate(s,case['days']),'size_days':lambda:R.size_days(s,case['mb'])}[case['op']]()
                self.assertEqual(actual,json.loads(json.dumps(expected)))

    def test_setup_stats_payload_codes(self):
        cases=[{'op':'payload','request':text} for text in PAYLOADS]
        for case,actual in zip(cases,lua_driver(cases)):
            with self.subTest(request=case['request']):
                kind,expected=python_payload(case['request'])
                self.assertEqual(actual,{'kind':kind,'value':expected})

    def test_trim_drops_the_same_rows(self):
        datasets=[('latency',latency_data(1500,seed=s)) for s in (1,2)]+[('ping',ping_data(1500,seed=s)) for s in (3,4)]
        cases=[];expected=[]
        for kind,data in datasets:
            size=len(json.dumps(data,separators=(',',':')).encode())
            for budget in (size,size-1,size//2,size//7,1000,0):
                cases.append({'op':'trim','data':data,'budget':budget});copy_=copy.deepcopy(data)
                dropped=R.trim_to_budget(copy_,budget);expected.append({'dropped':dropped,'rows':len(copy_['rows']),'first':copy_['rows'][0][0] if copy_['rows'] else None})
        self.assertEqual(lua_driver(cases),expected)

    def test_monitor_consumers_follow_the_choice(self):
        """lua latency/ping observe prune to the same window as Python; monitor.retention_days = retention_settings.days."""
        from latency_history import LatencyHistory
        cases=[{'op':'days','settings':s} for s in SETTINGS]
        self.assertEqual(lua_driver(cases),[R.days(s) for s in SETTINGS])
        settings={'stats_retention_mode':'time','stats_retention_days':14,'plan_source':A,'plan_target':B}
        data=latency_data(20*1440,start=1793000040);now=data['rows'][-1][0]+30
        h=LatencyHistory(copy.deepcopy(data));h.observe({'profiles':[]},settings,now)
        [lua]=lua_driver([{'op':'latency_observe','data':data,'settings':settings,'now':now}])
        self.assertEqual(lua,{'rows':len(h.data['rows']),'retention_seconds':h.retention_seconds})
        self.assertEqual(h.retention_seconds,14*86400)


if __name__=='__main__':
    unittest.main()
