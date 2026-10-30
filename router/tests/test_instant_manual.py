"""Instant owner switch with Auto running: a live, recently probed channel is chosen at once (no child, no wait)."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,native_switch as n,pair_auto as pair,pair_manual as manual
import test_pair_manual as fixture
import test_pair_manual_directions as directions

NOW=fixture.NOW;SOURCE=fixture.SOURCE;TARGET=fixture.TARGET


class InstantManual(unittest.TestCase):
    # The direction suite's real fixture (journal, kernel model, pair state), without re-running its tests.
    enterContext=directions.PairManualDirections.enterContext
    reorder=directions.PairManualDirections.reorder;kernel_proof=directions.PairManualDirections.kernel_proof
    process=directions.PairManualDirections.process;request=directions.PairManualDirections.request
    apply=directions.PairManualDirections.apply

    def setUp(self):
        directions.PairManualDirections.setUp(self)
        self.enterContext(patch.object(n,'fast_switch_enabled',return_value=True))
        self.writes=[]
        self.enterContext(patch.object(n,'forward_dispatch',side_effect=lambda args,revision,timeout=5:self.writes.append(args[0]) or b''))
        self.backend.guard_exists.return_value=True
        self.backend.apply.side_effect=self.fast_apply
        self.backend.health.side_effect=AssertionError('a recent successful probe is enough: no fresh probe')

    def fast_apply(self,write_command=None,**kwargs):
        if n.journal_read().get('phase')!='APPLYING':return self.apply(**kwargs)  # a rollback restore, as in the direction suite
        write_command(['iptables-restore','--noflush','/tmp/x'])
        self.kernel_applied=True;self.kernel_order=list(self.current)

    def test_switch_is_done_in_the_supervisor_without_child_trace_or_confirmation_wait(self):
        journal=self.request('primary')
        self.assertEqual(journal['phase'],'HELD-ON-RESERVE');self.assertTrue(journal['manual_instant'])
        self.assertEqual(journal['before'],['t','s']);self.assertEqual(journal['after'],['s','t'])
        self.assertTrue(journal['rtp_dispatched']);self.assertIsNone(journal['pid']);self.assertTrue(journal['confirmed'])
        self.spawn.assert_not_called();self.probe.assert_not_called();self.assertEqual(self.writes,['iptables-restore'])
        stages=[name for name,_ in agent.read_json(self.runtime/'pair-manual-timing.json')['stages']]
        self.assertEqual(stages,['claimed','diagnosed','attested','lease','journal','reordered','switched','verified','held','saved','done'])
        self.assertEqual(pair.read_state()['manual_hold'],'source');self.assertEqual(pair.intent()['mode'],'on')
        self.assertFalse((self.persist/'pair-auto-budget.json').exists(),'an owner click is not an automatic attempt')

    def test_back_and_forth_needs_no_cooldown_or_free_budget(self):
        agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':[NOW-30,NOW-20,NOW-10]})
        self.request('primary')
        second=self.request('reserve')
        self.assertEqual(second['after'],['t','s']);self.assertEqual(pair.read_state()['manual_hold'],'target')
        self.assertEqual(self.current,['t','s'])

    def test_request_rpc_runs_no_diagnostic(self):
        self.backend.diagnostic.reset_mock()
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'],answer)
        self.backend.diagnostic.assert_not_called()
        self.assertEqual(manual.read()['selection'],{'tx':None})

    def test_target_without_a_recent_success_gets_a_fresh_probe_and_dead_is_refused(self):
        agent.atomic_json(self.runtime/'status.json',{'time':NOW,'profiles':[{'id':SOURCE,'time':NOW,'code':'VPN-001'},
                                                                          {'id':TARGET,'time':NOW,'code':None,'dns_ok':True,'https_success':2}]})
        self.assertEqual(manual.request('primary',self.revision)['blockers'],['SOURCE-NOT-HEALTHY'],'the button itself is refused')
        agent.atomic_json(self.runtime/'status.json',{'time':NOW,'profiles':[{'id':key,'time':NOW,'code':None,'dns_ok':True,'https_success':2} for key in (SOURCE,TARGET)]})
        self.assertTrue(manual.request('primary',self.revision)['accepted'])
        agent.atomic_json(self.runtime/'status.json',{'time':NOW,'profiles':[{'id':SOURCE,'time':NOW,'code':'VPN-001'}]})
        self.backend.health.side_effect=None;self.backend.health.return_value=False
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertEqual(manual.public()['code'],'SOURCE-NOT-HEALTHY')
        self.backend.health.assert_called_once_with(SOURCE);self.backend.reorder.assert_not_called();self.assertEqual(self.current,['t','s'])

    def test_failure_after_the_write_restores_the_previous_order_and_holds_nothing(self):
        self.backend.guard_exists.side_effect=n.Refused('GUARD-QUERY-FAILED')
        manual.request('primary',self.revision)
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertNotIn('manual_hold',pair.read_state())
        journal=n.journal_read()
        self.assertEqual(journal['phase'],'ROLLED-BACK');self.assertEqual(journal['restored_order'],['t','s']);self.assertEqual(self.current,['t','s'])
        self.assertEqual(journal['failure_code'],'GUARD-QUERY-FAILED')

    def test_a_kernel_that_did_not_follow_is_never_held(self):
        def broken(**kwargs):
            self.fast_apply(**kwargs);self.kernel_order=['t','s']  # kernel did not follow the committed order
        self.backend.apply.side_effect=broken
        manual.request('primary',self.revision)
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertNotEqual(manual.public()['state'],'COMPLETED');self.assertNotIn('manual_hold',pair.read_state())
        self.assertNotIn(n.journal_read()['phase'],('COMMITTED','HELD-ON-RESERVE'))
        self.assertEqual(n.journal_read()['failure_code'],'KERNEL-POLICY-UNVERIFIED')

    def test_failure_before_any_write_closes_the_journal_without_rollback(self):
        self.backend.reorder.side_effect=n.Refused('POLICY-IDENTITY-CHANGED')
        with patch.object(n,'rollback_counted',side_effect=AssertionError('nothing was written')):
            manual.request('primary',self.revision)
            manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        journal=n.journal_read()
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertEqual(journal['phase'],'ROLLED-BACK')
        self.assertEqual(journal['reason'],'FAILED-BEFORE-APPLY')

    def test_stop_after_the_write_restores_the_previous_order(self):
        def stopped(**kwargs):
            self.fast_apply(**kwargs)
            import auto_control;auto_control.current_revision(rotate=True)
        self.backend.apply.side_effect=stopped
        manual.request('primary',self.revision)
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'CANCELLED');self.assertNotIn('manual_hold',pair.read_state())
        self.assertEqual(self.current,['t','s'])


class OneDurableJournalWrite(unittest.TestCase):
    def test_instant_journal_marks_both_writers_at_once(self):
        source=Path(n.__file__).read_text(encoding='utf-8')
        body=source[source.index('def instant_manual('):source.index('def manual_stamp(')]
        self.assertIn("'forward_policy_touched':True,'rtp_dispatched':True",body)
        self.assertNotIn("journal[key]=True",body,'no extra flash write per dispatched writer')


class Nap(unittest.TestCase):
    def test_a_queued_click_ends_the_pause_at_once(self):
        import tempfile,time
        with tempfile.TemporaryDirectory() as folder,patch.object(n,'RUNTIME',Path(folder)),patch.object(n,'STOP',False):
            agent.atomic_json(Path(folder)/'pair-manual-control.json',{'state':'QUEUED'})
            started=time.monotonic();n.nap(5);self.assertLess(time.monotonic()-started,1)
            agent.atomic_json(Path(folder)/'pair-manual-control.json',{'state':'COMPLETED'})
            started=time.monotonic();n.nap(.5);self.assertGreaterEqual(time.monotonic()-started,.45)


class Lease(unittest.TestCase):
    def test_current_lease_is_reused_only_while_it_covers_a_whole_transaction(self):
        state={'id':'a'*32}
        with patch.object(manual.time,'time',return_value=NOW):
            self.assertEqual(manual.lease_until({'native_trial':'a'*32,'native_until':str(NOW+600)},state),NOW+600)
            self.assertEqual(manual.lease_until({'native_trial':'a'*32,'native_until':str(NOW+100)},state),NOW+100)
            self.assertIsNone(manual.lease_until({'native_trial':'a'*32,'native_until':str(NOW+20)},state))
            self.assertIsNone(manual.lease_until({'native_trial':'b'*32,'native_until':str(NOW+600)},state))
            self.assertIsNone(manual.lease_until({'native_trial':'a'*32,'native_until':'x'},state))


if __name__=='__main__':unittest.main()
