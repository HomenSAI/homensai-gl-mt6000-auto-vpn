"""A failed rollback must preserve its last readable transaction journal."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as n
import test_pair_manual_directions as fixture


class JournalWrites(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PairManualDirections();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.journal=self.case.request('primary');self.raw=n.JOURNAL.read_bytes()
        self.case.backend.apply.reset_mock();self.case.backend.reorder.reset_mock()

    def test_reader_and_writer_share_the_same_pure_validator(self):
        with patch.object(n,'atomic_json') as write:
            self.assertEqual(n.validate_journal(self.journal),self.journal)
            write.assert_not_called()
        self.assertEqual(n.journal_read(),self.journal)

    def test_foreign_restore_order_never_overwrites_readable_journal(self):
        bad=copy.deepcopy(self.journal);bad.update(phase='RESTORING',restore_before_order=['new_target','new_source'])
        with patch.object(n,'atomic_json') as write,self.assertRaises(n.Refused):n.journal_write(bad)
        write.assert_not_called();self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertEqual(n.journal_read(),self.journal)

    def test_foreign_live_identity_refuses_before_any_rollback_journal_mutation(self):
        self.case.current=['new_target','new_source']
        with self.assertRaises(n.Refused):n.rollback(self.case.backend,self.journal,'TRANSACTION-FAILED')
        self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertEqual(n.journal_read(),self.journal)
        self.case.backend.apply.assert_not_called();self.case.backend.reorder.assert_not_called()

    def test_non_dictionary_is_a_coded_refusal_before_io(self):
        with patch.object(n,'atomic_json') as write,self.assertRaises(n.Refused):n.journal_write([])
        write.assert_not_called();self.assertEqual(n.JOURNAL.read_bytes(),self.raw)

    def test_identity_changed_during_attestation_preserves_memory_and_durable_journal(self):
        expected=copy.deepcopy(self.journal);original=self.case.backend.attest_policy.side_effect
        def changed(*args):
            proof=original(*args);self.case.current=['new_target','new_source'];return proof
        self.case.backend.attest_policy.side_effect=changed
        with self.assertRaises(n.Refused):n.rollback(self.case.backend,self.journal,'TRANSACTION-FAILED')
        self.assertEqual(self.journal,expected);self.assertEqual(n.JOURNAL.read_bytes(),self.raw)
        self.case.backend.apply.assert_not_called()


if __name__=='__main__':unittest.main()
