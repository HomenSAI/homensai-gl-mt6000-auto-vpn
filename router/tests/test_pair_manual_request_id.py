"""F-35: a caller-supplied request id makes the manual click idempotent; a delayed retry never clears a newer hold."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,native_switch as n,pair_auto as pair,pair_manual as manual
from test_pair_manual import Tests as Base,NOW

RESUME_ID='resume-click-0001';RESERVE_ID='reserve-click-0002'


class RequestIdTests(Base):
    # the inherited scenarios stay in test_pair_manual; only the request-id cases run here
    def run_resume(self,client=RESUME_ID):
        answer=manual.request('resume',self.revision,client_request_id=client);self.assertTrue(answer['accepted'],answer)
        with patch.object(n,'attempt') as apply:
            manual.consume(self.backend,pair.read_state(),self.settings,self.revision);apply.assert_not_called()
        return answer

    def test_retry_of_a_completed_resume_after_a_newer_hold_clears_nothing(self):
        state=pair.read_state();state['manual_hold']='source';pair.save(state)
        first=self.run_resume()
        self.assertNotIn('manual_hold',pair.read_state())
        # a newer manual hold (the owner's next click)
        state=pair.read_state();state['manual_hold']='target';pair.save(state)
        newer=manual.read()
        retry=manual.request('resume',self.revision,client_request_id=RESUME_ID)
        self.assertTrue(retry['replayed']);self.assertEqual(retry['request_id'],first['request_id'])
        self.assertEqual(manual.read(),newer)  # no second row queued
        with patch.object(n,'attempt') as apply:
            self.assertFalse(manual.consume(self.backend,pair.read_state(),self.settings,self.revision));apply.assert_not_called()
        self.assertEqual(pair.read_state()['manual_hold'],'target')

    def test_retry_while_queued_gets_the_same_acceptance_not_busy(self):
        first=manual.request('reserve',self.revision,client_request_id=RESERVE_ID);self.assertTrue(first['accepted'],first)
        again=manual.request('reserve',self.revision,client_request_id=RESERVE_ID)
        self.assertTrue(again['accepted']);self.assertTrue(again['replayed']);self.assertEqual(again['request_id'],first['request_id'])
        self.assertEqual(manual.read()['id'],first['request_id'])

    def test_a_refusal_is_replayed_so_a_late_retry_never_acts_later(self):
        refused=manual.request('resume',self.revision,client_request_id=RESUME_ID)  # no hold: resume not allowed
        self.assertFalse(refused['accepted'])
        state=pair.read_state();state['manual_hold']='target';pair.save(state)
        retry=manual.request('resume',self.revision,client_request_id=RESUME_ID)
        self.assertFalse(retry['accepted']);self.assertTrue(retry['replayed']);self.assertEqual(manual.read(),{})
        self.assertEqual(pair.read_state()['manual_hold'],'target')

    def test_bh07_a_transient_refusal_is_not_kept_the_retry_decides_afresh(self):
        with patch('speed_pause.public',return_value={'active':True}):
            busy=manual.request('reserve',self.revision,client_request_id=RESERVE_ID)
        self.assertEqual(busy['blockers'],['SPEED-BUSY']);self.assertNotIn('replayed',busy)
        self.assertEqual([e['client'] for e in manual.ledger_read()],[],'SPEED-BUSY is not kept for the id')
        retry=manual.request('reserve',self.revision,client_request_id=RESERVE_ID)  # the speed test has ended
        self.assertTrue(retry['accepted'],retry);self.assertNotIn('replayed',retry)
        again=manual.request('reserve',self.revision,client_request_id=RESERVE_ID)
        self.assertTrue(again['replayed']);self.assertEqual(again['request_id'],retry['request_id'],'no second row: no double switch')
        self.assertEqual(manual.read()['id'],retry['request_id'])

    def test_bh07_busy_and_unconfirmed_are_not_kept(self):
        self.reserve_request()  # a pending row without an id: the next click is PAIR-MANUAL-BUSY
        busy=manual.request('reserve',self.revision,client_request_id=RESUME_ID)
        self.assertEqual(busy['blockers'],['PAIR-MANUAL-BUSY'])
        with patch.object(manual,'_request',return_value={'accepted':False,'queued':False,'completed':False,'blockers':['PAIR-MANUAL-REQUEST-UNCONFIRMED']}):
            manual.request('reserve',self.revision,client_request_id=RESERVE_ID)
        self.assertEqual(manual.ledger_read(),[])

    def test_bh07_a_transient_refusal_kept_by_an_older_version_is_not_replayed(self):
        agent.atomic_json(manual.ledger_path(),{'entries':[{'client':RESERVE_ID,'reply':{'accepted':False,'queued':False,'completed':False,'blockers':['SPEED-BUSY']}}]})
        retry=manual.request('reserve',self.revision,client_request_id=RESERVE_ID)
        self.assertTrue(retry['accepted'],retry);self.assertNotIn('replayed',retry)
        self.assertEqual([e['reply'].get('accepted') for e in manual.ledger_read()],[True],'the acceptance replaces the old entry')
        self.assertTrue(manual.transient_refusal({'accepted':False,'blockers':['PAIR-MANUAL-BUSY']}))
        for reply in ({'accepted':True,'blockers':['SPEED-BUSY']},{'accepted':False,'blockers':['PAIR-MANUAL-COOLDOWN']},{'accepted':False},None):
            self.assertFalse(manual.transient_refusal(reply),reply)

    def test_without_an_id_nothing_changes(self):
        first=manual.request('reserve',self.revision);second=manual.request('reserve',self.revision)
        self.assertTrue(first['accepted']);self.assertNotIn('replayed',first)
        self.assertEqual(second['blockers'],['PAIR-MANUAL-BUSY']);self.assertFalse(manual.ledger_path().exists())

    def test_invalid_ids_and_a_damaged_ledger_are_refused(self):
        for bad in ('short','x'*65,'bad id with spaces',7,''):
            with self.subTest(bad=bad):
                self.assertEqual(manual.request('reserve',self.revision,client_request_id=bad)['blockers'],['PAIR-MANUAL-FIELDS'])
        agent.atomic_json(manual.ledger_path(),{'entries':'nope'})
        self.assertEqual(manual.request('reserve',self.revision,client_request_id=RESERVE_ID)['blockers'],['PAIR-MANUAL-STATE-UNVERIFIED'])
        self.assertEqual(manual.read(),{})

    def test_ledger_is_bounded(self):
        for index in range(manual.CLIENT_LEDGER_LIMIT+5):
            manual.request('resume',self.revision,client_request_id='bounded-%04d'%index)
        entries=manual.ledger_read()
        self.assertEqual(len(entries),manual.CLIENT_LEDGER_LIMIT);self.assertEqual(entries[-1]['client'],'bounded-%04d'%(manual.CLIENT_LEDGER_LIMIT+4))

    def test_agent_dispatch_passes_the_optional_id(self):
        state=pair.read_state();state['manual_hold']='source';pair.save(state)
        reply=agent.pair_manual_reply({'direction':'resume','control_revision':self.revision,'request_source':'manual','client_request_id':RESUME_ID})
        self.assertTrue(reply['accepted'],reply);self.assertEqual(manual.ledger_read()[0]['client'],RESUME_ID)
        self.assertEqual(agent.pair_manual_reply({'direction':'resume','control_revision':self.revision,'other':'x'})['blockers'],['PAIR-MANUAL-FIELDS'])


# do not re-run the inherited base scenarios from this module
for _name in [k for k in dir(Base) if k.startswith('test_')]:
    if not hasattr(RequestIdTests,_name) or getattr(RequestIdTests,_name) is getattr(Base,_name):
        setattr(RequestIdTests,_name,None)
del Base

if __name__=='__main__':unittest.main()
