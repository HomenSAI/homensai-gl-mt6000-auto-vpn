"""Review 06.11.2026, finding F-30: one monotonic deadline for every waiting stage of the apply worker.

The A9 review's fake-clock scenario: RTP admitted at +44 s (75 s reserve), RTP 44 s, wait_quiet 19 s, the transient wait
of the verify step 20 s: verification ended at +127 s, after the parent's +125 s (deadline 120 + grace 5), and a vendor
apply that had succeeded was killed mid-verify. Now wait_quiet and the transient wait are cut to what the journal's
monotonic deadline leaves after POST_APPLY_RESERVE (native_switch.stage_budget); the limits themselves are unchanged.
The Lua twins (transaction.lua verify step, forward_resume.lua) cannot run here: their source is pinned below.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

LIB=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import native_switch as n


class StageBudgetTests(unittest.TestCase):
    def test_the_review_scenario_ends_inside_the_parent_wait(self):
        start=1000.0;journal={'monotonic_deadline':start+n.TRANSACTION_SECONDS}
        dispatch=start+44
        self.assertGreaterEqual(journal['monotonic_deadline']-dispatch,n.RTP_DISPATCH_RESERVE,'RTP admitted at +44 s as before')
        after_rtp=dispatch+44
        quiet=n.stage_budget(journal,n.WAIT_QUIET_SECONDS,now=after_rtp)
        self.assertEqual(quiet,20)   # +88 .. +108: the quiet wait fits
        verify=n.stage_budget(journal,n.VERIFY_VENDOR_WAIT,now=after_rtp+quiet)
        self.assertEqual(verify,2)   # +108 .. +110: cut from 20 to what is left before the reserve
        self.assertLessEqual(after_rtp+quiet+verify+n.POST_APPLY_RESERVE,journal['monotonic_deadline'])
        self.assertLess(journal['monotonic_deadline'],journal['monotonic_deadline']+n.WORKER_WAIT_GRACE)

    def test_budget_never_exceeds_the_wish_and_never_goes_negative(self):
        journal={'monotonic_deadline':200.0}
        self.assertEqual(n.stage_budget(journal,20,now=100.0),20)
        self.assertEqual(n.stage_budget(journal,20,now=185.0),5)
        self.assertEqual(n.stage_budget(journal,20,now=195.0),0)
        self.assertEqual(n.stage_budget(journal,20,now=400.0),0)
        self.assertEqual(n.stage_budget(journal,20,reserve=0,now=190.0),10)

    def test_without_a_monotonic_deadline_the_old_limit_stays(self):
        for journal in ({},{'monotonic_deadline':None},{'monotonic_deadline':'x'},None):
            self.assertEqual(n.stage_budget(journal,20,now=0.0),20)

    def test_child_and_forward_resume_bound_their_waits_by_the_journal(self):
        source=(LIB/'native_switch.py').read_text(encoding='utf-8')
        child=source[source.index('def child(tx):'):source.index('def transition_kind(')]
        self.assertIn('backend.stage_budget=lambda want:stage_budget(journal,want)',child)
        self.assertIn('waited_until=time.monotonic()+stage_budget(journal,VERIFY_VENDOR_WAIT)',child)
        self.assertNotIn('waited_until=time.monotonic()+VERIFY_VENDOR_WAIT',child)
        forward=(LIB/'forward_resume.py').read_text(encoding='utf-8')
        self.assertIn('backend.stage_budget=lambda want:n.stage_budget(journal,want)',forward)
        self.assertIn('current=_settled_selection(backend,journal)',forward)


class ApplyQuietBudgetTests(unittest.TestCase):
    def apply(self,budget=None):
        backend=n.Linux.__new__(n.Linux);backend.process_bindings=None
        backend.policy=lambda:{'sections':[],'settings':{}}
        backend.dns_mark_sync=lambda *a,**k:{}
        if budget is not None:backend.stage_budget=budget
        waited=[]
        with patch('device_profile.detect',return_value='mt3000'),patch('rtp_boot.ready'),\
                patch('process_policy.synchronization_script',return_value=None),patch('process_policy.applied',return_value=True),\
                patch.object(n,'fast_switch_enabled',return_value=False),patch('native_platform.wait_quiet',side_effect=lambda seconds=20:waited.append(seconds)):
            backend.apply(write_command=lambda args,timeout=5:b'')
        return waited

    def test_the_worker_budget_cuts_the_quiet_wait(self):
        self.assertEqual(self.apply(budget=lambda want:min(want,7)),[7])

    def test_without_a_budget_the_full_quiet_wait_stays(self):
        self.assertEqual(self.apply(),[n.WAIT_QUIET_SECONDS])


class LuaMirrorSourceTests(unittest.TestCase):
    """Not verified by execution (no Lua on this host): the twins must carry the same bound and the same checks."""
    def read(self,name):return (LIB/'lua'/name).read_text(encoding='utf-8')

    def test_f30_lua_verify_step_is_bound_by_the_journal_deadline(self):
        source=self.read('transaction.lua')
        self.assertIn('M.POST_APPLY_RESERVE=10',source)
        self.assertIn('budget=math.max(0,math.min(budget,num(md)-M.POST_APPLY_RESERVE-mono(env)))',source)
        self.assertIn('local waited_until=mono(env)+budget',source)
        self.assertNotIn('local waited_until=mono(env)+M.VERIFY_VENDOR_WAIT',source)

    def test_f28_f29_lua_forward_resume_checks_ownership_and_the_deadline_before_commit(self):
        source=self.read('forward_resume.lua')
        resume=source[source.index('function M.resume(env,value)'):]
        self.assertIn("if n.identity(n.network(),managed)~=state.network_identity then refuse('PAIR-EXTERNAL-NETWORK-CHANGE') end",resume)
        self.assertIn("if n.changed(state,n.configs(managed),{firewall=true}) then refuse('PAIR-EXTERNAL-CONFIG-CHANGE') end",resume)
        first_write=resume.index('value.forward_resumed=canon.object(')
        self.assertLess(resume.index('local ook,oerr=pcall(owned)'),first_write)
        commit=resume.index("value.phase='COMMITTED'")
        self.assertLess(resume.index('owned()  -- F-28'),commit)
        self.assertLess(resume.index("if T.transaction_expired(env,value) then refuse('TRANSACTION-EXPIRED') end",commit-400),commit)


if __name__=='__main__':unittest.main()
