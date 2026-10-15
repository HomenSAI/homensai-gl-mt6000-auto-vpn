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
        previous=os.environ.get('TZ');os.environ['TZ']='CET-1CEST,M3.5.0,M10.5.0/3';time.tzset()
        try:
            with tempfile.TemporaryDirectory() as d:
                h=History(d);h.record({'state':'APPLYING'},1793487599);h.record({'state':'COMMITTED'},1793487600)
                # UTC 2026-10-31 22:59:59/23:00:00 crosses Berlin midnight.
                self.assertEqual(set(h.load()['months']),{'2026-10','2026-11'})
        finally:
            if previous is None:os.environ.pop('TZ',None)
            else:os.environ['TZ']=previous
            time.tzset()

    def test_history_failure_blocks_publish_but_reports_status(self):
        with tempfile.TemporaryDirectory() as d,patch.object(native,'PERSIST',Path(d)),patch.object(native,'STATE',Path(d)/'status'),patch.object(History,'record',side_effect=OSError('disk')):
            with self.assertRaisesRegex(native.Refused,'HISTORY-001'):native.publish({'state':'APPLYING'})
            self.assertEqual(json.loads(native.STATE.read_text())['blockers'],['HISTORY-001'])


if __name__=='__main__':unittest.main()
