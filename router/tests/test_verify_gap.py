"""Verification gap: no BLOCKED flicker right after a confirmed pass (MT3000 cut 07.11.2026, alpha8).

The owner's page showed BLOCKED without a reason, without an active channel, for 2-3 s about 12 s after COMMITTED and 27 s
after the return, then the confirmed state came back by itself. Cause: pair_auto.reapply_missing_policy (and the tick's own
diagnostic) published BLOCKED for a pass whose diagnostic() answered only a short vendor wait (VENDOR-WORKER-BUSY: a GL
worker holding its lock; the lock study of 05.11.2026 measured such episodes at 2.3 s at most). Now such a pass keeps the
last confirmed publication with verifying=True while the earlier kernel proof is inside its 15 s validity; a real blocker,
or a wait outliving the proof, is still published BLOCKED.
Shared cases: verify_gap_cases.json; Lua twin: tests/lua/test_verify_gap.lua (pair.lua, the same sequence through tick).
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import native_switch as n  # noqa: E402
import pair_auto as pair  # noqa: E402
import test_pair_manual_directions as fixture  # noqa: E402

REAL_PUBLISH=n.publish
DATA=json.loads((HERE/'verify_gap_cases.json').read_text(encoding='utf-8'))
NOW=fixture.NOW;SOURCE=fixture.SOURCE;TARGET=fixture.TARGET


def case_input(case):
    previous=copy.deepcopy(DATA['base']);previous.update(copy.deepcopy(case.get('previous',{})))
    previous['channel_path'].update(copy.deepcopy(case.get('path',{})))
    roles=case.get('roles',{'source_id':DATA['source'],'target_id':DATA['target']})
    return previous,case['blockers'],case['now'],roles


class SharedCases(unittest.TestCase):
    def test_shared_cases(self):
        for case in DATA['cases']:
            with self.subTest(case['name']):
                previous,blockers,now,roles=case_input(case)
                got=pair.verify_gap(previous,list(blockers),now,roles)
                want=case['expect']
                if want is None:
                    self.assertIsNone(got);continue
                self.assertEqual((got['state'],got['reason']),(want['state'],want['reason']))
                self.assertEqual((got['source'],got['target']),(previous['source'],previous['target']))
                self.assertEqual(got['blockers'],[],'a kept state carries no blocker (the page would show it blocked)')
                self.assertEqual(got['verify_blockers'],blockers)
                self.assertIs(got['verifying'],True)
                self.assertEqual(got['verifying_since'],want['since'])
                self.assertIs(got['readiness_verified'],False,'this pass verified nothing')
                self.assertIs(got['kernel_policy_verified'],False,'this pass verified nothing')
                proof=got['kernel_proof']
                self.assertEqual((proof['verified'],proof['role'],proof['time']),(True,want['role'],want['proof_time']),'the earlier proof, never renewed')
                self.assertEqual(proof['profile_id'],previous['channel_path']['active_profile_id'])
                for key in ('time','channel_path','transition_completed','route_changed','transition_outcome'):
                    self.assertNotIn(key,got)


class TickSequence(unittest.TestCase):
    """Real: pair_auto.tick, reapply_missing_policy, native_switch.publish (channel_path, history). Fake: the backend."""
    enterContext=fixture.PairManualDirections.enterContext

    def setUp(self):
        fixture.PairManualDirections.setUp(self)
        self.current=['s','t'];self.state['order']=list(self.current);pair.save(self.state);self.kernel_applied=True
        self.clock=[NOW]
        self.enterContext(patch('time.time',side_effect=lambda:self.clock[0]))
        self.enterContext(patch.object(n,'publish',side_effect=REAL_PUBLISH))
        self.blockers=[]
        self.backend.diagnostic.side_effect=lambda:(list(self.blockers),dict(copy.deepcopy(self.selection),order=list(self.current)))
        self.logged=self.enterContext(patch.object(pair,'_log'))

    kernel_proof=fixture.PairManualDirections.kernel_proof
    reorder=fixture.PairManualDirections.reorder
    apply=fixture.PairManualDirections.apply
    process=fixture.PairManualDirections.process

    def tick(self,advance=2.0,blockers=()):
        self.clock[0]+=advance;self.blockers=list(blockers)
        healthy=lambda samples,identifier,count,now,age,wanted,*a,**k:wanted is True  # noqa: E731
        with patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}),\
                patch('failover_plan.streak',side_effect=healthy),patch.object(n,'streak',side_effect=healthy),\
                patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}):
            self.assertTrue(pair.tick(self.backend,self.settings,self.revision))
        return agent.read_json(n.STATE,{})

    def assert_confirmed(self,status,checked_at):
        path=status['channel_path']
        self.assertEqual((path['confirmed'],path['kernel_policy_verified'],path['active_profile_id']),(True,True,SOURCE))
        self.assertEqual(path['checked_at'],checked_at)

    def test_short_vendor_wait_keeps_the_confirmed_state_then_a_long_one_blocks(self):
        status=self.tick(0)
        self.assertEqual((status['state'],status['reason']),('OBSERVING','PAIR-WATCHING'))
        self.assert_confirmed(status,self.clock[0]);proof=self.clock[0]
        # the MT3000 rows 210.0 (BLOCKED, reason None, no channel) and 212.0: one or two busy passes
        status=self.tick(2,['VENDOR-WORKER-BUSY'])
        self.assertEqual((status['state'],status.get('reason'),status['blockers']),('OBSERVING','PAIR-WATCHING',[]))
        self.assertEqual((status['verifying'],status['verify_blockers'],status['verifying_since']),(True,['VENDOR-WORKER-BUSY'],self.clock[0]))
        self.assertIs(status['kernel_policy_verified'],False);self.assertIs(status['readiness_verified'],False)
        self.assert_confirmed(status,proof);since=self.clock[0]
        status=self.tick(2,['VENDOR-WORKER-BUSY'])
        self.assertEqual((status['state'],status['verifying_since']),('OBSERVING',since));self.assert_confirmed(status,proof)
        self.assertEqual(self.logged.call_count,1,'one log line per gap')
        # the wait ends: the next pass attests again, without the flag
        status=self.tick(2)
        self.assertEqual((status['state'],status['reason']),('OBSERVING','PAIR-WATCHING'));self.assertNotIn('verifying',status)
        self.assert_confirmed(status,self.clock[0]);proof=self.clock[0]
        # a wait that outlives the 15 s proof validity is published BLOCKED, as before
        states=[self.tick(2,['VENDOR-WORKER-BUSY'])['state'] for _ in range(8)]
        self.assertEqual(states,['OBSERVING']*7+['BLOCKED'],'kept for 14 s of proof age, BLOCKED at 16 s')
        status=agent.read_json(n.STATE,{})
        self.assertEqual(status['blockers'],['VENDOR-WORKER-BUSY']);self.assertIsNone(status['channel_path']['active_profile_id'])
        self.assertGreater(self.clock[0]-proof,pair.VERIFY_GAP_SECONDS)
        # once BLOCKED, a further busy pass stays BLOCKED (never back to a kept state without a new attestation)
        self.assertEqual(self.tick(2,['VENDOR-WORKER-BUSY'])['state'],'BLOCKED')
        status=self.tick(2);self.assertEqual(status['state'],'OBSERVING');self.assert_confirmed(status,self.clock[0])

    def test_a_real_blocker_is_published_at_once(self):
        self.tick(0)
        status=self.tick(2,['TERMS-NOT-ACCEPTED'])
        self.assertEqual((status['state'],status['blockers']),('BLOCKED',['TERMS-NOT-ACCEPTED']))
        self.assertFalse(status['channel_path']['confirmed'])
        self.tick(2)
        status=self.tick(2,['VENDOR-WORKER-BUSY','VENDOR-CODE-CHANGED'])
        self.assertEqual(status['state'],'BLOCKED')

    def test_without_a_confirmed_pass_the_wait_is_blocked_as_before(self):
        agent.atomic_json(n.STATE,{'state':'OBSERVING','time':NOW,'source':SOURCE,'target':TARGET,'mode':'continuous-pair'})
        status=self.tick(2,['VENDOR-WORKER-BUSY'])
        self.assertEqual((status['state'],status['blockers']),('BLOCKED',['VENDOR-WORKER-BUSY']))
        self.assertIs(status['kernel_policy_verified'],False)


if __name__=='__main__':
    unittest.main()
