from pathlib import Path
import random,sys,time,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from agent import Accounting

class StatisticsBoundaryTests(unittest.TestCase):
    def row(self,code=None):return {'id':'a','interface':'tun0','name':'Synthetic','protocol':'openvpn','code':code}
    def total(self,acc,key):return sum(day.get(key,0) for profile in acc.activity.values() for day in profile['days'].values())
    def test_activity_clock_regression_does_not_double_count(self):
        acc=Accounting();start=1792000000
        for delta in [0,30,20,40]:acc.track_activity([self.row()],start+delta)
        self.assertEqual(self.total(acc,'up'),40);self.assertEqual(acc.gaps,1)
    def test_duplicate_activity_and_counter_sample_is_idempotent(self):
        acc=Accounting();start=1792000000
        for delta in [0,30,30,60]:
            acc.track_activity([self.row()],start+delta);acc.sample('tun0',1,delta*10,delta*20,start+delta)
        self.assertEqual(self.total(acc,'up'),60);self.assertEqual(acc.gaps,0)
        self.assertEqual(sum(x['rx'] for x in acc.months.values()),600)
    def test_counter_clock_regression_discards_baseline_instead_of_double_counting(self):
        acc=Accounting();start=1792000000
        for delta,rx in [(0,1000),(30,1300),(20,1200),(40,1400),(60,1600)]:acc.sample('tun0',1,rx,rx,start+delta)
        self.assertEqual(sum(x['rx'] for x in acc.months.values()),500)
        self.assertEqual(acc.gaps,1)
    def test_month_and_year_boundaries_conserve_bytes(self):
        for calendar in [(2026,10,31),(2026,12,31),(2028,2,29)]:
            start=time.mktime((*calendar,23,59,45,0,0,-1));acc=Accounting()
            acc.sample('tun0',1,0,0,start);acc.sample('tun0',1,300,600,start+30)
            self.assertEqual(sum(x['rx'] for x in acc.months.values()),300)
            self.assertEqual(sum(x['tx'] for x in acc.days.values()),600)
            self.assertEqual(len(acc.months),2)
    def test_dst_23_and_25_hour_days_keep_actual_elapsed_duration(self):
        for start_day,end_day,hours in [((2026,3,29),(2026,3,30),23),((2026,10,25),(2026,10,26),25)]:
            start=time.mktime((*start_day,0,0,0,0,0,-1));end=time.mktime((*end_day,0,0,0,0,0,-1))
            self.assertEqual(end-start,hours*3600)
            acc=Accounting();acc.track_activity([self.row()],start)
            acc.track_activity([self.row()],end,max_gap=26*3600)
            self.assertEqual(self.total(acc,'up'),hours*3600)
    def test_200_seeded_duration_and_failure_accounting_sequences(self):
        for seed in range(200):
            rng=random.Random(seed);acc=Accounting();now=1792000000;total=0;prior=None;episodes=0
            for step in range(60):
                down=rng.random()<.25;code='DNS-001' if down else None
                if prior is not None:
                    total+=30
                    if down and not prior:episodes+=1
                acc.track_activity([self.row(code)],now);prior=down;now+=30
            self.assertEqual(self.total(acc,'up')+self.total(acc,'down'),total)
            self.assertEqual(self.total(acc,'failures'),episodes)
            self.assertEqual(self.total(acc,'unknown'),0)
    def test_restart_gap_is_unknown_and_does_not_create_connections(self):
        acc=Accounting();now=1792000000;acc.track_activity([self.row()],now)
        restored=Accounting(acc.export());restored.track_activity([self.row()],now+3600)
        self.assertEqual(self.total(restored,'unknown'),3600);self.assertEqual(self.total(restored,'connections'),0)

if __name__=='__main__':unittest.main()
