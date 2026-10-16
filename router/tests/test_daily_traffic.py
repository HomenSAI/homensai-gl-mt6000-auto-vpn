import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from agent import Accounting, trim_status_reply, sample_wan_counters
import agent


class DailyTrafficTests(unittest.TestCase):
    def test_wan4_and_wan6_on_same_device_are_counted_once(self):
        values={'rx_bytes':'100','tx_bytes':'200','ifindex':'7'}
        def read(path,*args,**kwargs):return values[path.name]
        with patch.object(agent,'command',return_value=b'{"up":true,"proto":"dhcp","l3_device":"eth1"}'),patch.object(Path,'read_text',read):
            acc=Accounting();source={'wan_interfaces':['wan','wan6']}
            devices=sample_wan_counters(source,acc,1792000000)
            values.update(rx_bytes='200',tx_bytes='400')
            sample_wan_counters(source,acc,1792000030)
        self.assertEqual(len(devices),1)
        self.assertEqual(sum(x['rx'] for x in acc.wan.months.values()),100)
        self.assertEqual(acc.months,{})

    def test_vpn_protocol_in_wan_zone_is_not_double_counted_as_wan(self):
        with patch.object(agent,'command',return_value=b'{"up":true,"proto":"wgclient","l3_device":"wgclient1"}'):
            acc=Accounting();devices=sample_wan_counters({'wan_interfaces':['wan']},acc,1792000000)
        self.assertEqual(devices,[]);self.assertIsNone(acc.wan)

    def test_daily_split_reconciles_with_monthly_total(self):
        stamp=time.mktime((2026,10,14,23,59,45,0,0,-1))
        acc=Accounting();acc.sample('tun0',1,0,0,stamp);acc.sample('tun0',1,300,600,stamp+30)
        self.assertEqual(acc.days['2026-10-14']['rx'],150)
        self.assertEqual(acc.days['2026-10-15']['rx'],150)
        self.assertEqual(sum(row['tx'] for row in acc.days.values()),acc.months['2026-10']['tx'])

    def test_gap_only_day_is_not_reported_as_measured_zero(self):
        stamp=time.mktime((2026,10,14,12,0,0,0,0,-1))
        acc=Accounting();acc.note_gap(stamp,stamp+86400)
        self.assertFalse(acc.days['2026-10-14']['observed'])
        self.assertFalse(acc.days['2026-10-15']['observed'])
        self.assertEqual(acc.months,{})

    def test_counter_reset_is_a_gap_not_negative_traffic(self):
        stamp=time.mktime((2026,10,14,12,0,0,0,0,-1))
        acc=Accounting();acc.sample('tun0',1,100,100,stamp);acc.sample('tun0',1,10,10,stamp+30)
        self.assertEqual(acc.gaps,1)
        self.assertFalse(acc.days['2026-10-14']['observed'])
        self.assertEqual(acc.months,{})

    def test_checkpoint_extension_is_backward_compatible(self):
        acc=Accounting({'months':{'2026-10':{'rx':123,'tx':456,'seconds':30}},'gaps':2})
        self.assertEqual(acc.days,{})
        self.assertEqual(acc.export()['months']['2026-10']['rx'],123)

    def test_retention_budget_keeps_traffic_totals_and_marks_removed_history(self):
        acc=Accounting();acc.months={'2026-10':{'rx':123,'tx':456,'seconds':30}}
        acc.quality={'a':{'last':None,'buckets':{str(i):{'n':1,'success':1,'rtt_sum':30,'unknown':0} for i in range(1000)}}}
        acc.compact(limit=8000)
        self.assertEqual(acc.months['2026-10']['rx'],123)
        self.assertGreater(acc.retention['quality_buckets_dropped'],0)
        self.assertLessEqual(len(json.dumps(acc.export(),ensure_ascii=True).encode()),8000)

    def test_rpc_reduction_preserves_current_profiles(self):
        status={'profiles':[{'id':'a','name':'Example'}],'samples':[{'time':i,'text':'x'*200} for i in range(1000)]}
        value=trim_status_reply(status,limit=10000)
        self.assertEqual(value['profiles'][0]['name'],'Example')
        self.assertTrue(value['rpc_history_reduced'])
        self.assertLess(len(json.dumps(value).encode()),10000)
