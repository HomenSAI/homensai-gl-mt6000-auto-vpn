"""Power-cut integrity on the Python side (POWER-CUT-INTEGRITY-2026-10-31.ru.md): leftover .pending files of an
interrupted write are swept at start (only old ones), switch-timing.json is replaced with fsync like atomic_json,
and the journal written by the Lua line reads as JOURNAL-INTEGRITY-FAILED (never an uncaught error) for every
truncation, zero fill and flipped byte."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import agent
import switch_timing
import native_switch as n


class SweepPending(unittest.TestCase):
    def test_only_old_pending_files_are_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);now=time.time()
            old=folder/'.native-transaction.json.ab12_x.pending';old.write_text('{"half')
            future=folder/'.checkpoint.json.0a1b-3.pending';future.write_text('')
            fresh=folder/'.native-history.json.k9.pending';fresh.write_text('x')
            target=folder/'native-transaction.json';target.write_text('{}')
            foreign=folder/'notes.pending';foreign.write_text('x')
            os.utime(str(old),(now-600,now-600));os.utime(str(future),(now+5000,now+5000))
            os.utime(str(foreign),(now-600,now-600))
            self.assertEqual(agent.sweep_pending(folder,now=now),2)
            self.assertEqual(sorted(p.name for p in folder.iterdir()),['.native-history.json.k9.pending','native-transaction.json','notes.pending'])
            self.assertEqual(agent.sweep_pending(folder/'missing'),0,'never raises')

    def test_a_directory_is_not_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);(folder/'.x.json.y.pending').mkdir()
            self.assertEqual(agent.sweep_pending(folder,max_age=-1),0)


class SwitchTiming(unittest.TestCase):
    def test_record_fsyncs_the_file_then_the_directory_and_leaves_no_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            calls=[];real=os.fsync
            def spy(fd):
                calls.append(os.path.isdir('/proc/self/fd/%d'%fd) if os.path.exists('/proc/self/fd/%d'%fd) else None)
                return real(fd)
            with patch.object(switch_timing.os,'fsync',spy):
                value=switch_timing.record(folder,4.2,now=1.0)
            self.assertEqual(value['count'],1)
            self.assertEqual(len(calls),2,'file then directory')
            if calls[0] is not None:self.assertEqual(calls,[False,True])
            self.assertEqual(os.listdir(folder),['switch-timing.json'])
            self.assertEqual(switch_timing.read(folder)['count'],1)

    def test_a_damaged_timing_file_is_ignored_and_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            for damaged in ('',' '*10,'\0'*64,'{"avg_seconds":4'):
                Path(folder,'switch-timing.json').write_text(damaged)
                self.assertIsNone(switch_timing.read(folder))
                self.assertEqual(switch_timing.record(folder,5,now=2.0)['count'],1)


class JournalDamage(unittest.TestCase):
    def test_every_damaged_form_is_an_integrity_failure(self):
        value={'tx':'a'*32,'phase':'COMMITTED','before':['r1','r2'],'after':['r2','r1'],'hash':'ab'*32,'source':'wireguard:peer_1',
               'target':'openvpn:1_1','trial_nonce':'cd'*16,'started':1.0,'deadline':2.0}
        n.validate_journal(value)
        good=json.dumps({'schema':1,'data':value,'sha256':n.digest(value)},separators=(',',':')).encode()
        forms=[good[:i] for i in range(len(good))]+[b'\0'*len(good),good[:40]+bytes([good[40]^1])+good[41:]]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'native-transaction.json'
            with patch.object(n,'JOURNAL',path):
                for raw in forms:
                    path.write_bytes(raw)
                    with self.assertRaises(n.Refused) as caught:n.journal_read()
                    self.assertEqual(str(caught.exception),'JOURNAL-INTEGRITY-FAILED')
                path.write_bytes(good);self.assertEqual(n.journal_read()['phase'],'COMMITTED')
                path.unlink();self.assertEqual(n.journal_read(),{})


if __name__=='__main__':
    unittest.main()
