"""Resident history copy for its writer: one full flash write per event, the backup by rename, a full load only after
another writer changed a file (MT3000, 30 Oct 2026: the 1.27 MB file cost ~2 s and 2.5 MB of flash per event)."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_history as h

EVENT={'state':'OBSERVING','reason':'PAIR-WATCHING','source':'wireguard:peer_1','target':'openvpn:1_2'}


class WriterCache(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.root=Path(folder.name)
        self.addCleanup(h._WRITER_CACHE.clear)
        self.history=lambda:h.History(self.root,detail_days=7)

    def record(self,state,now):
        return self.history().record(dict(EVENT,state=state),now=now)

    def test_envelope_bytes_equal_the_encoded_envelope(self):
        data={'b':[1,2],'a':{'x':'y'}}
        self.assertEqual(h.envelope_bytes(h.encoded(data)),h.encoded(self.history().envelope(data)))

    def test_next_event_reuses_the_resident_copy_and_renames_main_to_backup(self):
        self.assertTrue(self.record('ARMED',1000))
        main=self.root/'native-history.json'
        before=main.read_bytes()
        with patch.object(h.History,'load',side_effect=AssertionError('no full load for our own last write')):
            self.assertTrue(self.record('APPLYING',1001))
        self.assertEqual((self.root/'native-history.backup.json').read_bytes(),before,'backup is the previous main, byte for byte')
        loaded=self.history().load()
        self.assertEqual([row['state'] for row in loaded['events']],['ARMED','APPLYING'])

    def test_another_writer_forces_a_full_load(self):
        self.record('ARMED',1000)
        other=self.history();data=other.load();data['events'][0]['state']='RESTORING'
        h.atomic(other.path,other.envelope(data))  # e.g. a statistics reset in another process
        calls=[]
        real=h.History.load
        def counted(self):calls.append(1);return real(self)
        with patch.object(h.History,'load',counted):self.record('APPLYING',1001)
        self.assertEqual(len(calls),1)
        self.assertEqual([row['state'] for row in self.history().load()['events']],['RESTORING','APPLYING'])

    def test_a_failed_record_drops_the_resident_copy(self):
        self.record('ARMED',1000)
        with patch.object(h,'atomic_bytes',side_effect=OSError('flash full')),self.assertRaises(OSError):
            self.record('APPLYING',1001)
        self.assertNotIn(str(self.root/'native-history.json'),h._WRITER_CACHE)
        events=[row['state'] for row in self.history().load()['events']]
        self.assertEqual(events,['ARMED'],'the backup (previous main) still holds the last complete history')

    def test_unchanged_event_keeps_the_copy(self):
        self.record('OBSERVING',1000)
        self.assertFalse(self.record('OBSERVING',1001))
        with patch.object(h.History,'load',side_effect=AssertionError('still resident')):
            self.assertTrue(self.record('ARMED',1002))


if __name__=='__main__':unittest.main()
