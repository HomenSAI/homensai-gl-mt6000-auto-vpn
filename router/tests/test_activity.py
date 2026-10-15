import sys
from pathlib import Path
import unittest
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from agent import Accounting


class ActivityTests(unittest.TestCase):
    def row(self, code=None, active=True):
        return {'id':'wireguard:peer_1','name':'Example','protocol':'wireguard','interface':'wgclient1' if active else None,'code':code}

    def totals(self, acc):
        return {k:sum(d[k] for d in acc.activity['wireguard:peer_1']['days'].values()) for k in ('up','down','unknown','connections','failures')}

    def test_duration_and_failure_count(self):
        acc=Accounting();now=1792000000
        for delta,code in [(0,None),(30,None),(60,'VPN-003'),(90,'VPN-003'),(120,None)]:
            acc.track_activity([self.row(code)],now+delta)
        self.assertEqual(self.totals(acc),{'up':60,'down':60,'unknown':0,'connections':0,'failures':1})

    def test_inactive_is_not_failure_and_start_is_not_connection(self):
        acc=Accounting();now=1792000000
        acc.track_activity([self.row(active=False)],now)
        acc.track_activity([self.row()],now+30)
        acc.track_activity([self.row()],now+60)
        self.assertEqual(self.totals(acc)['connections'],1)
        self.assertEqual(self.totals(acc)['failures'],0)

    def test_gap_and_restart_are_unknown(self):
        acc=Accounting();now=1792000000
        acc.track_activity([self.row()],now)
        restored=Accounting(acc.export())
        restored.track_activity([self.row()],now+300)
        self.assertEqual(self.totals(restored)['unknown'],300)
        self.assertEqual(self.totals(restored)['connections'],0)

    def test_interval_splits_at_calendar_midnight(self):
        acc=Accounting();stamp=time.mktime((2026,10,14,23,59,45,0,0,-1))
        acc.track_activity([self.row()],stamp)
        acc.track_activity([self.row()],stamp+30)
        days=acc.activity['wireguard:peer_1']['days']
        self.assertEqual(days['2026-10-14']['up'],15)
        self.assertEqual(days['2026-10-15']['up'],15)
