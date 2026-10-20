from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as native


class Backend:
    def __init__(self):self.current=['b','a'];self.calls=[]
    def guard(self,devices=None):self.calls.append('guard')
    def order(self):return list(self.current),'a'*64
    def reorder(self,order):self.calls.append('reorder');self.current=list(order)
    def apply(self):self.calls.append('apply')
    def devices(self):return ['fixture-tun']


class NativePhaseTests(unittest.TestCase):
    def journal(self):
        return dict(phase='ARMED',before=['a','b'],after=['b','a'],hash='a'*64)

    def test_phase_timeline_is_bounded_and_rollback_calls_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(native,'JOURNAL',Path(directory)/'journal'):
            row=self.journal()
            native.journal_write(row)
            row['phase']='APPLYING';native.journal_write(row)
            native.journal_write(row)
            self.assertEqual([p['phase'] for p in row['phase_evidence']],['ARMED','APPLYING'])
            backend=Backend();native.rollback(backend,row,'OPERATOR-STOP')
            self.assertEqual(backend.current,['a','b'])
            self.assertEqual(backend.calls,['guard','reorder','apply','guard'])
            self.assertEqual([p['phase'] for p in native.journal_read()['phase_evidence']],['ARMED','APPLYING','RESTORING','ROLLED-BACK'])
            for i in range(50):native.note_phase(row,'PHASE-'+str(i))
            self.assertLessEqual(len(row['phase_evidence']),32)

    def test_phase_logging_failure_never_prevents_the_existing_restore_operation(self):
        backend=Backend();row=self.journal();row['phase']='APPLYING'
        with patch.object(native,'journal_write',side_effect=OSError('synthetic disk failure')),self.assertRaises(OSError):
            native.rollback(backend,row,'OPERATOR-STOP')
        self.assertEqual(backend.current,['a','b'])
        self.assertIn('apply',backend.calls)
        self.assertEqual(backend.calls[0],'guard')


if __name__=='__main__':unittest.main()
