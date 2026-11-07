"""Network journal and advisor of the master slider (netjournal.py, advisor.py, advisor_control.py; 2.1.0-alpha9).
Lua twin: tests/lua/test_network_advisor.lua over the same tests/advisor_cases.json (generated from the Python
modules by tests/gen_advisor_cases.py; this file checks it is current).

Also: the journal's size and flash-write budget, determinism, golden section against the fine grid, the shift rule
(>= 5 % and >= 5 events), the replay against the study's numbers, the modes and the safety rules, alpha8 defaults
unchanged, the single writer, the RPC handlers (with fakes; no router).
"""
import json
import math
import random
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(HERE))
import advisor as A  # noqa: E402
import advisor_sim as S  # noqa: E402
import channel_model as C  # noqa: E402
import gen_advisor_cases as G  # noqa: E402
import netjournal as J  # noqa: E402

CASES=json.loads((HERE/'advisor_cases.json').read_text(encoding='utf-8'))
CURVE=A.load_curve()
NOW=S.BASE+7*86400+3.5*3600
_WEEKS={}


def week(name,days=7,offset=0):
    key=(name,days,offset)
    if key not in _WEEKS:_WEEKS[key]=S.build(S.scenario_days(name,days),offset)
    return _WEEKS[key]


class SharedCases(unittest.TestCase):
    def test_cases_file_is_current(self):
        self.assertEqual(json.loads(G.text()),CASES,'run: python3 router/tests/gen_advisor_cases.py --write')

    def test_curve_file_is_the_study(self):
        candidates=[HERE.parents[1]/'private/math/master-slider/curve.json',HERE.parents[2]/'math/master-slider/curve.json']
        study=next((p for p in candidates if p.exists()),None)
        if study is None:self.skipTest('the private study is not in this checkout')
        import importlib.util
        spec=importlib.util.spec_from_file_location('gen_slider_curve',HERE.parents[1]/'scripts/gen-slider-curve.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fast=study.parents[1]/'master-slider-fast'
        if not fast.exists():self.skipTest('the private fast study is not in this checkout')
        self.assertEqual(module.text(json.loads(study.read_text(encoding='utf-8')),str(fast)),(ROOT/'slider_curve.json').read_text(encoding='utf-8'))


class Journal(unittest.TestCase):
    def sample(self,identifier,t,fail,dense=False):
        return G.sample(identifier,t,fail,dense)

    def test_outage_estimate_bins_and_flags(self):
        j=J.new();t=S.BASE+1000
        for k in range(10):
            fail=3<=k<6
            J.observe(j,[self.sample(S.PRIMARY,t+10*k,fail)],S.PAIR,'source',t+10*k+8,0)
        # failed 30..50, healthy 20 and 60: lower 20, upper 40 -> 30 s, Fibonacci bin [21, 34)
        self.assertEqual(j['cur']['ch'][S.PRIMARY]['o'],[1030,30,1])
        self.assertEqual(j['cur']['ch'][S.PRIMARY]['oh'][J.EDGES.index(21)],1)
        self.assertEqual(J.bin_of(1),0);self.assertEqual(J.bin_of(20),J.EDGES.index(13));self.assertEqual(J.bin_of(5000),len(J.EDGES)-1)

    def test_loss_slot_packing(self):
        value=3*J.SHORTS+5*J.PACK+30
        self.assertEqual(J.unpack(value),(3,5,30))

    def test_size_budget(self):
        for name,build in CASES['builds'].items():
            self.assertLessEqual(max(build['sizes']),3300,name)   # ~3 KB a day for a pair
        # worst case: heavy loss all day long (hundreds of outages: capped) and a flap every few minutes
        events=[('loss',0,86400,40)]
        j=S.build([events]);size=len(J.encode(j['days'][0]))
        self.assertLessEqual(size,10000,size)
        self.assertEqual(len(j['days'][0]['ch'][S.PRIMARY]['o']),3*J.MAX_SHORT)
        self.assertGreater(j['days'][0]['ch'][S.PRIMARY]['ox'],1000)
        # 30 typical days of RAM / flash
        self.assertLessEqual(30*max(max(b['sizes']) for b in CASES['builds'].values()),100000)

    def test_flash_once_a_day_and_ram_once_a_minute(self):
        files={};counts={'flash':0,'ram':0};flash_days={}

        class IO:
            def read(self,p):return files.get(p)
            def write_ram(self,p,s):files[p]=s;counts['ram']+=1
            def write_flash(self,p,s):files[p]=s;counts['flash']+=1
        writer=J.Writer(IO(),'/run','/etc')
        events=S.SCENARIOS['long']
        for day in range(3):
            for k in range(8640):
                now=S.BASE+day*86400+10*k+8;before=counts['flash']
                writer.pass_([self.sample(S.PRIMARY,now-8,S.failing(events,'P',10*k))],S.PAIR,'source',now,0,now)
                if counts['flash']>before:flash_days[J.day_index(now,0)]=flash_days.get(J.day_index(now,0),0)+1
                if day==1 and k==4000:writer=J.Writer(IO(),'/run','/etc')   # monitor restart: RAM files kept
        self.assertEqual(sorted(flash_days.values()),[1,1])
        self.assertLessEqual(counts['ram'],3*1440+10)
        # a reboot: the RAM files are gone, the flash copy brings the completed days back (today is lost)
        boot=J.Writer(IO(),'/run2','/etc')
        self.assertEqual(J.days_text(boot.journal),J.days_text(writer.journal))
        self.assertIsNone(boot.journal['cur'])

    def test_unnecessary_failover_rules_one_by_one(self):
        """tests/gen_advisor_cases 'flap-false-short': each failover is unnecessary by exactly one rule."""
        name,offset,passes=next(x for x in G.journal_sequences() if x[0]=='flap-false-short')
        j=G.run_sequence(offset,passes)
        self.assertEqual((j['cur']['sw'],j['cur']['rt'],j['cur']['us']),(3,2,3))
        self.assertEqual(j['cur']['ch'][S.PRIMARY]['o'],[3630,50,1,3980,90,1])
        def us_after(k):
            j=J.new()
            for now,samples,route,pair in passes[:k]:J.observe(j,samples,pair,route,now,offset)
            return j['cur']['us']
        self.assertEqual(us_after(8),0)     # the first failover: its outage is still open
        self.assertEqual(us_after(9),1)     # ... it ended 12 s after the failover: did not pay
        self.assertEqual(us_after(43),2)    # a failover 300 s after the return: flap (its outage lasts 42 s more)
        self.assertEqual(us_after(120),2)
        self.assertEqual(us_after(121),3)   # no failed check of the primary in the last 60 s: false

    def test_retention_and_clock_back(self):
        self.assertEqual(J.RETENTION,30)
        j=J.new()
        for day in range(40):
            J.observe(j,[self.sample(S.PRIMARY,S.BASE+day*86400+5,False)],S.PAIR,'source',S.BASE+day*86400+10,0)
        self.assertEqual(len(j['days']),J.RETENTION)
        self.assertEqual(j['days'][-1]['d']-j['days'][0]['d'],J.RETENTION-1)
        d=j['cur']['d']
        J.observe(j,[self.sample(S.PRIMARY,S.BASE+5,False)],S.PAIR,'source',S.BASE+10,0)   # the clock went back
        self.assertEqual(j['cur']['d'],d)

    def test_damaged_files_are_not_trusted(self):
        j=J.load('{"v":1,"days":[{"d":3}]}','{"v":2}','not json')
        self.assertEqual(j['days'],[]);self.assertIsNone(j['cur'])

    def test_single_writer(self):
        """Only the monitor (monitor.lua / agent.monitor_loop through advisor.MonitorPart) writes the journal."""
        writers=[]
        for path in list(ROOT.glob('*.py'))+list((ROOT/'lua').glob('*.lua')):
            if path.stem=='netjournal':continue   # the module itself
            text=path.read_text(encoding='utf-8')
            if any(x in text for x in ('MonitorPart(','monitor_part(','J.Writer(','J.writer(','.observe(journal','J.observe(')):writers.append(path.name)
        self.assertEqual(sorted(writers),['advisor.lua','advisor.py','agent.py','monitor.lua'])
        self.assertIn('network_advisor_part()',(ROOT/'agent.py').read_text(encoding='utf-8'))
        self.assertIn("require('advisor').monitor_part(",(ROOT/'lua/monitor.lua').read_text(encoding='utf-8'))
        control=(ROOT/'advisor_control.py').read_text(encoding='utf-8')
        self.assertNotIn('write_ram',control);self.assertNotIn('observe(',control)


class Advisor(unittest.TestCase):
    def test_deterministic(self):
        days=week('blips')['days']
        a=A.recommend(CURVE,days,{'failure_model':'hmm'},NOW,0)
        b=A.recommend(CURVE,list(reversed(json.loads(json.dumps(days)))),{'failure_model':'hmm'},NOW,0)
        self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))

    def test_replay_matches_the_study(self):
        """Leave time and ride-out of the replay against the study's predictions at every anchor."""
        for anchor in CURVE['anchors']:
            p=dict(zip(CURVE['params'],anchor['p']));m=dict(zip(CURVE['metrics'],anchor['m']))
            ride,leave=A.behaviour(p['theta'],p['dur_b'])
            self.assertLessEqual(abs(leave-m['switch_after_s']),3.0,(anchor['t'],leave,m['switch_after_s']))
            self.assertLessEqual(abs(ride-m['rides_out_s']),4.0,(anchor['t'],ride,m['rides_out_s']))
        self.assertEqual(A.behaviour(0.8,4.0)[0],A.behaviour(0.6,8.0)[0])   # the study: alpha8 rides out like theta 0.6 / dur_B 8

    def random_events(self,rng):
        ev={'outages':[],'groups':{g:0.0 for g in A.TABLE_GROUPS},'n':0,'days':7,'weight_days':5.0,'counts':{},'durations':[]}
        kind=rng.choice(('short','blips','long','mixed'))
        for _ in range(rng.randint(3,60)):
            d={'short':rng.randint(1,18),'blips':rng.randint(15,32),'long':rng.randint(40,400)}.get(kind) or rng.choice((rng.randint(1,30),rng.randint(20,200)))
            ev['outages'].append((d,rng.choice((1.0,0.82,0.67,0.55))))
        for g in A.TABLE_GROUPS:
            if rng.random()<0.4:ev['groups'][g]=rng.random()*rng.choice((1,5,20))
        ev['n']=len(ev['outages'])
        return ev

    def test_golden_section_agrees_with_the_grid(self):
        rng=random.Random(20261104)
        grid=[i/100 for i in range(101)];golden=0;worst=0.0
        for _ in range(150):
            ev=self.random_events(rng)
            best=A.search(ev,CURVE,0.6)
            costs=[A.cost_at(ev,CURVE,t)[0] for t in grid]
            low=min(costs)
            self.assertLessEqual(best['cost'],low*1.005+1e-9,(best,low))   # within 0.5 % of the 0.01 grid
            worst=max(worst,(best['cost']-low)/low if low else 0.0)
            if best['method']=='golden':golden+=1
            self.assertEqual(best['method']=='golden',A.unimodal(best['anchor_costs']))
        self.assertGreater(golden,50)

    def test_golden_finds_the_minimum(self):
        for m in (0.0,0.13,0.37,0.5,0.81,1.0):
            t,n=A.golden(lambda x,m=m:(x-m)**2)
            self.assertLessEqual(abs(t-m),0.02,m);self.assertLessEqual(n,12)

    def test_replay_outcome_rules(self):
        k=20.0
        self.assertEqual(A.outcome(19,[k]),(19,0,0))                       # ended before the decision: rides out
        self.assertEqual(A.outcome(20,[k]),(20,0,0))
        self.assertEqual(A.outcome(21,[k]),(21+2*A.BLIP,1,1))              # ended before the traffic left: unnecessary
        self.assertEqual(A.outcome(k+A.EXEC,[k]),(k+A.EXEC+2*A.BLIP,1,1))
        self.assertEqual(A.outcome(k+A.EXEC+0.5,[k]),(k+A.EXEC+2*A.BLIP,0,1))
        self.assertEqual(A.outcome(300,[None]),(300,0,0))

    def test_flap_needs_three_outages(self):
        def day(outs):
            rec=J.new_tunnel(0)
            for s_,d in outs:rec['o'].extend([s_,d,1])
            return {'d':J.day_index(NOW,0)-1,'sw':0,'rt':0,'us':0,'ch':{S.PRIMARY:rec}}
        two=A.events([day([(1000,60),(1180,60)])],J.day_index(NOW,0),7)
        three=A.events([day([(1000,60),(1180,60),(1360,60)])],J.day_index(NOW,0),7)
        self.assertEqual((two['counts']['flaps'],two['counts']['outages']),(0,2))
        self.assertEqual((three['counts']['flaps'],three['counts']['outages']),(1,0))

    def test_shift_rule_needs_five_percent_and_five_events(self):
        days=week('blips')['days']
        r=A.recommend(CURVE,days,{'failure_model':'hmm'},NOW,0)
        self.assertEqual(r['state'],'shift');self.assertGreaterEqual(r['effect']['saving_pct'],5.0)
        # the same network, one day of four events: few data
        few=json.loads(json.dumps(days[-1:]))
        rec=few[0]['ch'][S.PRIMARY];rec['o']=rec['o'][:12]
        r=A.recommend(CURVE,few,{'failure_model':'hmm'},NOW,0)
        self.assertEqual((r['state'],r['events']),('few-data',4))
        self.assertIn('Мало данных: 4 события за 1 день',r['reason_ru'])
        # a quiet network: no shift (the saving is below 5 %)
        r=A.recommend(CURVE,week('quiet')['days'],{'failure_model':'hmm'},NOW,0)
        self.assertEqual(r['state'],'keep');self.assertLess(r['effect']['saving_pct'],5.0)
        r=A.recommend(CURVE,[],{'failure_model':'hmm'},NOW,0)
        self.assertEqual(r['state'],'no-data')

    def test_window_and_recent_days_weigh_more(self):
        self.assertEqual(A.day_weight(0,7),1.0);self.assertAlmostEqual(A.day_weight(3.5,7),0.5)
        self.assertGreater(A.day_weight(1,30),A.day_weight(1,7))
        days=week('long')['days']
        one=A.events(days,J.day_index(NOW,0),1);seven=A.events(days,J.day_index(NOW,0),7)
        self.assertEqual((one['days'],seven['days']),(1,7))
        self.assertEqual(seven['counts']['outages'],7*one['counts']['outages'])

    def test_texts(self):
        r=A.recommend(CURVE,week('blips')['days'],{'failure_model':'hmm'},NOW,0)
        self.assertTrue(r['reason_ru'].startswith('Рекомендовано на основании 7 дней: обрывов основного 84'),r['reason_ru'])
        self.assertIn('Предлагается положение 0,40 (сейчас: стандартные настройки)',r['reason_ru'])
        self.assertTrue(r['reason_en'].startswith('Recommended based on 7 days: 84 outages of the primary'),r['reason_en'])
        self.assertEqual([A.plural_ru(n,'день','дня','дней') for n in (1,2,5,11,21,22)],['день','дня','дней','дней','день','дня'])


class Safety(unittest.TestCase):
    def test_every_anchor_and_the_alpha8_default_are_safe(self):
        for anchor in CURVE['anchors']:
            self.assertEqual(A.safety(dict(zip(CURVE['params'],anchor['p']))),[],anchor['t'])
        for t in [i/100 for i in range(101)]:
            self.assertEqual(A.safety(A.interpolate(CURVE,t)),[],t)
        self.assertEqual(A.safety({'theta':0.8,'dur_b':4.0,'pg':0.9,'primary_stable':120,'rescue_stable':10}),[])

    def test_each_rule_is_enforced(self):
        base={'theta':0.8,'dur_b':4.0,'pg':0.9,'primary_stable':120,'rescue_stable':10}
        self.assertEqual(A.safety(dict(base,pg=0.7)),['ADVISOR-PG-BELOW-THETA'])
        self.assertEqual(A.safety(dict(base,rescue_stable=50,primary_stable=40)),['ADVISOR-RESCUE-ABOVE-STABLE'])
        self.assertEqual(A.safety(dict(base,theta=0.99,dur_b=15.0,pg=0.99)),['ADVISOR-RIDE-NOT-BELOW-LEAVE'])   # never leaves
        for key,bad in (('theta',0.4),('dur_b',16),('pg',1.2),('primary_stable',10),('rescue_stable',61),('theta',float('nan')),('dur_b',None)):
            self.assertEqual(A.safety(dict(base,**{key:bad})),['ADVISOR-OUT-OF-BOUNDS'],key)

    def test_curve_monotone_and_constraints(self):
        previous=None
        for t in [i/100 for i in range(101)]:
            p=A.interpolate(CURVE,t)
            self.assertGreaterEqual(p['pg'],p['theta']);self.assertLessEqual(p['rescue_stable'],p['primary_stable'])
            if previous:
                for k in ('theta','dur_b','pg','primary_stable','rescue_stable'):self.assertGreaterEqual(p[k],previous[k],(t,k))
            previous=p


class Modes(unittest.TestCase):
    calm={'open':[],'route':'source','native':'OBSERVING'}

    def step(self,settings,result=None,changes=(),calm=None,now=NOW):
        return A.auto_step(CURVE,result or {'state':'shift','t':0.2},dict(settings),list(changes),self.calm if calm is None else calm,now)

    def test_default_mode_is_advice_and_never_applies(self):
        self.assertEqual(A.mode({}),'advice');self.assertEqual(A.window({}),7)
        self.assertEqual(self.step({'failure_model':'hmm'})['code'],'ADVISOR-NOT-AUTO')
        self.assertEqual(self.step({'failure_model':'hmm','advisor_mode':'manual'})['code'],'ADVISOR-NOT-AUTO')

    def test_auto_one_step_once_a_day_never_busy(self):
        auto={'failure_model':'hmm','advisor_mode':'auto'}
        s=self.step(auto);self.assertEqual((s['apply'],s['t']),(True,0.5))     # nearest 0.6 -> one step 0.1
        attached=dict(auto,slider_t=0.5,hmm_theta=0.6,hmm_dur_b=5.0,return_pg=0.95)
        self.assertEqual(self.step(attached)['t'],0.4)
        self.assertEqual(self.step(attached,{'state':'shift','t':0.45})['t'],0.45)
        self.assertEqual(self.step(auto,changes=[{'time':NOW-3600,'source':'auto'}])['code'],'ADVISOR-ONCE-A-DAY')
        self.assertTrue(self.step(auto,changes=[{'time':NOW-21*3600,'source':'auto'}])['apply'])
        for calm,code in (({'open':['x'],'route':'source','native':'OBSERVING'},'ADVISOR-BUSY-OUTAGE'),
                          ({'open':[],'route':'switching','native':'OBSERVING'},'ADVISOR-BUSY-SWITCH'),
                          ({'open':[],'route':'down','native':'OBSERVING'},'ADVISOR-BUSY-SWITCH'),
                          ({'open':[],'route':'source','native':'WAIT-CLIENT'},'ADVISOR-BUSY-SWITCH'),
                          ({'open':[],'route':'source','native':'OBSERVING','phase':'APPLYING'},'ADVISOR-BUSY-SWITCH'),
                          ('nothing','ADVISOR-CALM-UNKNOWN')):
            self.assertEqual(self.step(auto,calm=calm)['code'],code)
        self.assertEqual(self.step(dict(auto,failure_model='consecutive'))['code'],'ADVISOR-MODEL-CONSECUTIVE')
        self.assertEqual(self.step(auto,{'state':'keep','t':None})['code'],'ADVISOR-NO-SHIFT')

    def test_current_position_labels(self):
        self.assertEqual(A.current({'failure_model':'hmm'},CURVE)['label'],'preset')
        point=A.interpolate(CURVE,0.75)
        attached={'failure_model':'hmm','slider_t':0.75,'hmm_theta':point['theta'],'hmm_dur_b':point['dur_b'],'return_pg':point['pg'],
                  'recovery_primary_stable':point['primary_stable'],'recovery_rescue_stable':point['rescue_stable']}
        self.assertEqual(A.current(attached,CURVE)['label'],'slider')
        # the owner changed primary_stable in the wizard afterwards: detached, «Пользовательская»
        self.assertEqual(A.current(dict(attached,recovery_primary_stable=120),CURVE)['label'],'custom')

    def test_job_schedule(self):
        key=A.settings_key({});today=J.day_index(NOW,0)
        self.assertTrue(A.job_due(None,key,NOW,0,None))
        self.assertFalse(A.job_due({'day':today,'key':key},key,NOW,0,None))
        self.assertTrue(A.job_due({'day':today-1,'key':key},key,NOW,0,None))           # 03:30 passed
        self.assertFalse(A.job_due({'day':today-1,'key':key},key,NOW-3600,0,None))     # 02:30
        self.assertTrue(A.job_due({'day':today,'key':'old'},key,NOW,0,None))           # settings changed
        self.assertFalse(A.job_due({'day':today,'key':'old'},key,NOW,0,NOW-60))        # ... at most every 10 min


class Alpha8Defaults(unittest.TestCase):
    def test_presets_unchanged(self):
        for model,(theta,dur_b) in (('hmm',(0.8,4.0)),('hmm-fast',(0.7,3.0))):
            p=C.resolve({'failure_model':model})
            self.assertEqual((p['theta'],p['dur'][2],p['healthy'],p['key']),(theta,dur_b,0.9,model))
            q=C.params(model)
            for key in ('theta','dur','total','ratio','weight'):self.assertEqual(p[key],q[key])
        self.assertIsNone(C.resolve({'failure_model':'consecutive','hmm_theta':0.6}))
        self.assertEqual(C.resolve({'failure_model':'hmm','hmm_theta':0.2,'hmm_dur_b':'4','return_pg':True})['key'],'hmm')

    def test_numeric_options_reach_the_decision(self):
        hcases=json.loads((HERE/'hmm_detector_cases.json').read_text(encoding='utf-8'))
        import gen_hmm_detector_cases as H
        profile=dict(H.PROFILE,vendor_changed_at=-1e6)
        for case in hcases['streams']:
            seen=[];plain=[];same=[];custom=[]
            for r,(pub,_) in zip(case['rows'],case['decisions']):
                seen.append(H.sample(r))
                plain.append(C.channel_failed(seen,profile['id'],3,pub,30,{'failure_model':case['model']},profile))
                preset=C.PRESETS.get(case['model'])
                if preset:
                    same.append(C.channel_failed(seen,profile['id'],3,pub,30,{'failure_model':case['model'],'hmm_theta':preset['theta'],'hmm_dur_b':preset['dur_b']},profile))
                    custom.append(C.channel_failed(seen,profile['id'],3,pub,30,{'failure_model':case['model'],'hmm_theta':0.99,'hmm_dur_b':15.0},profile))
            self.assertEqual(plain,[w for _,w in case['decisions']],case['name'])
            if same:
                self.assertEqual(same,plain,case['name'])
                self.assertFalse(any(custom),case['name'])   # a setting that never leaves never decides

    def test_the_replay_memory_tells_settings_apart(self):
        import gen_hmm_detector_cases as H
        rows=[H.sample({'t':t,'code':None,'dns_ok':True,'https':3}) for t in range(1000,1100,10)]
        rows+=[H.sample({'t':t,'code':'VPN-003','dns_ok':True,'https':0}) for t in range(1100,1130,4)]
        C._MEMO.clear()
        fast=C.evaluate(rows,H.PROFILE['id'],1130,30,C.resolve({'failure_model':'hmm'}))['pi']
        slow=C.evaluate(rows,H.PROFILE['id'],1130,30,C.resolve({'failure_model':'hmm','hmm_dur_b':8.0}))['pi']
        C._MEMO.clear()
        fresh=C.evaluate(rows,H.PROFILE['id'],1130,30,C.resolve({'failure_model':'hmm','hmm_dur_b':8.0}))['pi']
        self.assertEqual(slow,fresh);self.assertNotEqual(fast,slow)

    def test_return_pg_is_the_healthy_threshold(self):
        import gen_hmm_detector_cases as H
        rows=[H.sample({'t':t,'code':None,'dns_ok':True,'https':3}) for t in range(1000,1200,10)]
        rows+=[H.sample({'t':1200,'code':'VPN-003','dns_ok':True,'https':0})]+[H.sample({'t':t,'code':None,'dns_ok':True,'https':3}) for t in range(1210,1260,10)]
        view=C.evaluate(rows,H.PROFILE['id'],1255,30,C.resolve({'failure_model':'hmm'}))
        low=C.evaluate(rows,H.PROFILE['id'],1255,30,C.resolve({'failure_model':'hmm','return_pg':0.5}))
        high=C.evaluate(rows,H.PROFILE['id'],1255,30,C.resolve({'failure_model':'hmm','return_pg':0.99}))
        self.assertEqual(view['pi'],low['pi'])
        self.assertTrue(low['healthy']);self.assertFalse(high['healthy'])
        self.assertEqual(view['healthy'],view['pi'][0]>=0.9)

    def test_settings_path(self):
        inv=(ROOT/'inventory.lua').read_text(encoding='utf-8')
        for line in ("main.hmm_theta=ranged(s.hmm_theta,0.5,0.99)","main.hmm_dur_b=ranged(s.hmm_dur_b,1,15)",
                     "main.return_pg=ranged(s.return_pg,0.5,0.99)","main.slider_t=ranged(s.slider_t,-0.7,1)",
                     "main.advisor_mode=(s.advisor_mode=='auto' or s.advisor_mode=='manual') and s.advisor_mode or 'advice'"):
            self.assertIn(line,inv)
        save=(ROOT/'setup_save.lua').read_text(encoding='utf-8')
        for key in ('hmm_theta','hmm_dur_b','return_pg','slider_t','advisor_mode','advisor_window'):self.assertIn(key+'=true',save)
        self.assertIn("assert(key=='telegram_token' or key=='slider_t')",save)
        acl=json.loads((HERE.parent/'files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json').read_text(encoding='utf-8'))['luci-app-homensai-vpn']
        self.assertIn('advisor',acl['read']['ubus']['homensai-vpn'])
        self.assertTrue({'advisor_apply','advisor_settings'}<=set(acl['write']['ubus']['homensai-vpn']))
        self.assertEqual(C.NUMERIC,{'hmm_theta':(0.5,0.99),'hmm_dur_b':(1.0,15.0),'return_pg':(0.5,0.99)})


class Control(unittest.TestCase):
    """advisor_control with fakes: what is written, when it is refused."""
    def setUp(self):
        import advisor_control as AC
        self.AC=AC;self.saved=[];self.logged=[];self.rows=[];self.calm={'open':[],'route':'source','native':'OBSERVING','phase':None}
        self.settings={'failure_model':'hmm','advisor_mode':'advice'}
        @contextmanager
        def lock():yield
        self.deps={'paths':lambda:('/run','/etc'),'lock':lock,'settings':lambda:dict(self.settings),'calm':lambda r,n:dict(self.calm),
                   'allow':lambda *a:True,'save':lambda p:self.saved.append(p) or None,'write_changes':lambda p,rows:self.rows.extend(rows[len(self.rows):]),
                   'log':self.logged.append}
        self._changes=AC.changes;AC.changes=lambda persist:list(self.rows)

    def tearDown(self):
        self.AC.changes=self._changes

    def test_owner_apply_writes_the_interpolated_settings(self):
        r=self.AC.apply(0.25,'owner',now=NOW,deps=self.deps)
        self.assertTrue(r['saved'])
        self.assertEqual(self.saved[-1],{'main':{'hmm_theta':'0.6','hmm_dur_b':'3.5','return_pg':'0.9','recovery_primary_stable':'120',
                                                 'recovery_rescue_stable':'10','slider_t':'0.25'},'servers':[]})
        self.assertEqual(self.rows[-1]['source'],'owner');self.assertEqual(self.rows[-1]['to'],0.25)
        self.assertTrue(self.logged[-1].startswith('ADVISOR-APPLIED: slider - -> 0.25 (owner)'))

    def test_an_owner_click_in_flight_is_read_from_its_own_record(self):
        # review 04.11.2026 (finding 6): a slider move under a waiting click ended it in MANUAL-CONFIG-CHANGED
        with tempfile.TemporaryDirectory() as directory:
            with patch('route_history.observed_route',return_value='source'),patch('native_switch.journal_read',return_value={}):
                self.assertIsNone(self.AC.calm_now(directory,NOW)['manual'])
                self.assertEqual(self.AC.calm_now(directory,NOW)['phase'],None)
                for name,state,expected in (('pair-manual-control.json','QUEUED','QUEUED'),('pair-manual-control.json','CLAIMED','CLAIMED'),
                                            ('pair-manual-control.json','COMPLETED',None),('pair-manual-control.json','REFUSED',None),
                                            ('manual-control.json','APPLYING','APPLYING')):
                    Path(directory,name).write_text(json.dumps({'state':state}),encoding='utf-8')
                    self.assertEqual(self.AC.calm_now(directory,NOW)['manual'],expected,state)
                    self.assertEqual(bool(A.calm_codes(self.AC.calm_now(directory,NOW))),expected is not None,state)
                    Path(directory,name).unlink()

    def test_refusals(self):
        self.calm['manual']='QUEUED'  # review 04.11.2026: the slider never moves under the owner's click
        self.assertEqual(self.AC.apply(0.5,'owner',now=NOW,deps=self.deps)['code'],'ADVISOR-BUSY-SWITCH')
        self.calm['manual']=None
        self.calm['open']=['wireguard:peer_1']
        self.assertEqual(self.AC.apply(0.5,'owner',now=NOW,deps=self.deps)['code'],'ADVISOR-BUSY-OUTAGE')
        self.calm['open']=[];self.calm['native']='APPLYING'
        self.assertEqual(self.AC.apply(0.5,'owner',now=NOW,deps=self.deps)['code'],'ADVISOR-BUSY-SWITCH')
        self.calm['native']='OBSERVING'
        for bad in (-0.8,1.5,float('nan'),'0.5',True):
            self.assertEqual(self.AC.apply(bad,'owner',now=NOW,deps=self.deps)['code'],'ADVISOR-RANGE')
        self.assertEqual(self.AC.apply(-0.1,'owner',now=NOW,deps=self.deps)['code'],'ADVISOR-FAST-OFF')
        self.settings['failure_model']='consecutive'
        self.assertEqual(self.AC.apply(0.5,'owner',now=NOW,deps=self.deps)['code'],'ADVISOR-MODEL-CONSECUTIVE')
        self.assertEqual(self.saved,[])

    def test_auto_apply_only_in_auto_mode_and_once_a_day(self):
        result={'state':'shift','t':0.2,'reason_ru':'r','reason_en':'e'}
        self.assertEqual(self.AC.apply(0.5,'auto',result,now=NOW,deps=self.deps)['code'],'ADVISOR-NOT-AUTO')
        self.settings['advisor_mode']='auto'
        self.assertEqual(self.AC.apply(0.4,'auto',result,now=NOW,deps=self.deps)['code'],'ADVISOR-AUTO-STALE')
        self.assertTrue(self.AC.apply(0.5,'auto',result,now=NOW,deps=self.deps)['saved'])
        self.assertEqual(self.rows[-1]['reason_ru'],'r')
        self.assertEqual(self.AC.apply(0.5,'auto',result,now=NOW+3600,deps=self.deps)['code'],'ADVISOR-ONCE-A-DAY')
        self.assertEqual(len(self.saved),1)

    def test_apply_checks_safety_of_the_point(self):
        real=self.AC.A.interpolate
        def unsafe(curve,t):
            p=real(curve,t);p['pg']=p['theta']-0.1;return p
        self.AC.A.interpolate=unsafe
        try:self.assertEqual(self.AC.apply(0.5,'owner',now=NOW,deps=self.deps)['code'],'ADVISOR-PG-BELOW-THETA')
        finally:self.AC.A.interpolate=real
        self.assertEqual(self.saved,[])

    def test_manual_values_detach_the_slider(self):
        self.settings.update(slider_t=0.5)
        r=self.AC.manual({'theta':0.75,'dur_b':5.2,'pg':0.9},now=NOW,deps=self.deps)
        self.assertTrue(r['saved'])
        self.assertEqual(self.saved[-1],{'main':{'advisor_mode':'manual','hmm_theta':'0.75','hmm_dur_b':'5','return_pg':'0.9'},'servers':[],'delete':['slider_t']})
        self.assertEqual(self.AC.manual({'theta':0.9,'dur_b':5,'pg':0.8},now=NOW,deps=self.deps)['code'],'ADVISOR-PG-BELOW-THETA')
        self.assertEqual(self.AC.manual({'theta':0.99,'dur_b':15,'pg':0.99},now=NOW,deps=self.deps)['code'],'ADVISOR-RIDE-NOT-BELOW-LEAVE')

    def test_settings_reply(self):
        r=self.AC.settings_reply({'mode':'auto','window':30},deps=self.deps)
        self.assertEqual(self.saved[-1],{'main':{'advisor_mode':'auto','advisor_window':'30'},'servers':[]});self.assertTrue(r['saved'])
        for bad in ({'mode':'auto'},{'mode':'fast','window':7},{'mode':'auto','window':3},{'mode':'auto','window':7,'theta':0.7,'dur_b':4,'pg':0.9},
                    {'mode':'manual','window':7,'theta':0.7},{'mode':'auto','window':7,'x':1}):
            self.assertFalse(self.AC.settings_reply(bad,deps=self.deps)['saved'],bad)


if __name__=='__main__':
    unittest.main()
