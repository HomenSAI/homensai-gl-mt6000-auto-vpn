"""Parent timeout diagnostics preserve rollback and exclude private subprocess text."""
import json,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as n,pair_auto as pair,pair_manual as manual
import test_pair_manual_directions as fixture


class ParentDiagnostics(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PairManualDirections();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.case.enterContext(patch.object(n,'PROOF_SCOPE',n.PROOF_SCOPE))
        self.case.kernel_applied=True
        self.assertTrue(manual.request('reserve',self.case.revision)['accepted'])
        manual.consume(self.case.backend,pair.read_state(),self.case.settings,self.case.revision)
        self.assertEqual(manual.public()['code'],'MANUAL-ALREADY-SELECTED')
        self.case.backend.apply.reset_mock()

    def timeout_request(self):
        clock=[0.];process=self.case.process(['python','native_switch.py','apply','placeholder'])
        def wait(**kwargs):
            if 'timeout' not in kwargs:return 0
            journal=n.journal_read();n.child(journal['tx'])
            clock[0]+=kwargs['timeout']
            raise subprocess.TimeoutExpired(['PRIVATE_SENTINEL','--secret=PRIVATE_SENTINEL'],kwargs['timeout'],output=b'PRIVATE_SENTINEL',stderr=b'PRIVATE_SENTINEL')
        process.wait.side_effect=wait;self.case.spawn.side_effect=lambda *a,**kw:process
        with patch.object(n.time,'monotonic',side_effect=lambda:clock[0]),patch.object(n.time,'time',side_effect=lambda:fixture.NOW+clock[0]):
            self.assertTrue(manual.request('primary',self.case.revision)['accepted'])
            manual.consume(self.case.backend,pair.read_state(),self.case.settings,self.case.revision)
        return n.journal_read()

    def test_timed_out_parent_records_stage_type_frames_and_restores_verified_previous_target(self):
        journal=self.timeout_request();detail=journal['failure_detail']
        self.assertEqual(detail['stage'],'worker-wait');self.assertEqual(detail['error_type'],'TimeoutExpired')
        self.assertEqual(detail['worker_stage'],'done');self.assertEqual(detail['elapsed_ms'],(n.TRANSACTION_SECONDS+n.WORKER_WAIT_GRACE)*1000)
        self.assertEqual(detail['code'],'NATIVE-SYSTEM-001');self.assertNotIn('PRIVATE_SENTINEL',json.dumps(detail))
        self.assertLessEqual(len(detail['error_at']),5)
        self.assertTrue(all('/' not in row['file'] and '\\' not in row['file'] for row in detail['error_at']))
        self.assertEqual(json.loads((self.case.runtime/'native-attempt-result.json').read_bytes()),detail)
        self.assertEqual(journal['phase'],'ROLLED-BACK');self.assertEqual(self.case.current,['t','s'])
        self.assertEqual(pair.read_state()['manual_hold'],'target');self.assertTrue(self.case.kernel_proof()['verified'])
        self.assertEqual(self.case.backend.apply.call_count,2)

    def test_failed_diagnostic_file_write_never_prevents_existing_rollback(self):
        original=n.atomic_json
        def write(path,value):
            if Path(path).name in ('native-attempt-result.json','native-apply-progress.json'):raise OSError('PRIVATE_SENTINEL')
            return original(path,value)
        with patch.object(n,'atomic_json',side_effect=write):journal=self.timeout_request()
        self.assertEqual(journal['phase'],'ROLLED-BACK');self.assertEqual(journal['failure_detail']['error_type'],'TimeoutExpired')
        self.assertEqual(self.case.current,['t','s']);self.assertNotIn('PRIVATE_SENTINEL',json.dumps(journal['failure_detail']))

    def test_progress_from_another_transaction_is_never_attributed_to_this_failure(self):
        n.apply_progress('f'*32,'rtp-dispatch')
        try:raise OSError('PRIVATE_SENTINEL')
        except OSError as error:detail=n.record_attempt_failure('a'*32,'post-apply',error,n.time.monotonic())
        self.assertNotIn('worker_stage',detail);self.assertNotIn('PRIVATE_SENTINEL',json.dumps(detail))


if __name__=='__main__':unittest.main()
