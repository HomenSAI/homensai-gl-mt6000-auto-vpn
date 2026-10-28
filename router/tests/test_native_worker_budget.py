"""Bounded real Linux/Lua reorder work and the existing native worker lease.

The shared platform fixture parses native_policy.lua and executes the actual
UCI synchronization Lua. No order/hash equality is mocked.
"""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_policy
import test_pair_manual_bound_context as platform_fixture
NOW=platform_fixture.NOW
LUA=platform_fixture.LUA


@unittest.skipUnless(LUA,'Actual Lua 5.1 runtime required')
class NativeWorkerBudget(unittest.TestCase):
    def setUp(self):
        self.case=platform_fixture.BoundManualContext();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.backend=n.Linux();n.bind_policy_context(self.backend,self.case.state)
        self.before,self.fingerprint=self.backend.order()

    def desired(self):return pair_policy.desired_order(self.case.state['policy_roles'],self.before,'target')

    def write(self,args,timeout=5):return self.case.dispatch(args,self.case.revision,timeout)

    def check(self):n.require_control_revision(self.case.revision)

    def inject_on_second_policy_read(self,mutate):
        original=self.case.command;count=[0]
        def command(args,timeout=5):
            if args[0]=='/usr/bin/lua':
                count[0]+=1
                if count[0]==2:mutate()
            return original(args,timeout)
        return patch.object(n,'command',side_effect=command)

    def test_already_correct_order_has_zero_writes_commit_or_write_hooks(self):
        before=copy.deepcopy(self.case.data)
        with patch.object(self,'check',wraps=self.check)as check:
            self.backend.reorder(self.before,before_write=check,write_command=self.write)
        self.assertEqual(self.case.commands,[]);check.assert_not_called();self.assertEqual(self.case.data,before)

    def test_adjacent_generic_swap_moves_only_one_section_then_commits_once(self):
        desired=self.desired()
        with patch.object(self,'check',wraps=self.check)as check:
            self.backend.reorder(desired,before_write=check,write_command=self.write)
        self.assertEqual(self.backend.order(),(desired,self.fingerprint))
        self.assertEqual([command[:2]for command in self.case.commands],[['uci','reorder'],['uci','commit']])
        self.assertEqual(check.call_count,2,'every real move and commit retains its write guard')
        self.assertTrue(self.case.commands[0][2].startswith('route_policy.cfg000002='))

    def test_mixed_named_and_anonymous_metadata_uses_fresh_uci_names(self):
        desired=self.desired()
        def renamed():
            self.case.data['sections'][-1]['.name']='cfgffffff'
            self.case.data['sections'][-1]['name']='display-only name'
            self.case.data['sections'][-1]['.index']=999
        with self.inject_on_second_policy_read(renamed):self.backend.reorder(desired,before_write=self.check,write_command=self.write)
        self.assertEqual(self.backend.order(),(desired,self.fingerprint))
        self.assertEqual(len(self.case.commands),2);self.assertIn('route_policy.cfgffffff=',self.case.commands[0][2])

    def test_multiple_moves_preserve_the_expected_sequence_and_bounded_move_count(self):
        desired=[self.before[-1],self.before[2],self.before[0],self.before[1],self.before[-2]]
        self.backend.reorder(desired,before_write=self.check,write_command=self.write)
        self.assertEqual(self.backend.order(),(desired,self.fingerprint))
        moves=[command for command in self.case.commands if command[:2]==['uci','reorder']]
        self.assertEqual(len(moves),2);self.assertEqual(self.case.commands[-1],['uci','commit','route_policy'])

    def test_foreign_hash_before_first_actual_move_refuses_without_writes(self):
        with self.inject_on_second_policy_read(lambda:self.case.data['sections'][-1].update(foreign_option='1')):
            with self.assertRaises(n.Refused):self.backend.reorder(self.desired(),before_write=self.check,write_command=self.write)
        self.assertEqual(self.case.commands,[])

    def test_foreign_order_with_the_same_hash_is_not_adopted_before_first_move(self):
        def reordered():self.case.data['sections'][0],self.case.data['sections'][1]=self.case.data['sections'][1],self.case.data['sections'][0]
        desired=self.desired()
        with self.inject_on_second_policy_read(reordered),self.assertRaises(n.Refused):self.backend.reorder(desired,before_write=self.check,write_command=self.write)
        self.assertEqual(self.backend.order()[1],self.fingerprint,'semantic hash intentionally excludes ordering')
        self.assertEqual(self.case.commands,[])

    def test_foreign_hash_after_move_refuses_before_commit(self):
        def write(args,timeout=5):
            answer=self.write(args,timeout)
            if args[:2]==['uci','reorder']:self.case.data['sections'][-1]['foreign_option']='1'
            return answer
        with self.assertRaises(n.Refused):self.backend.reorder(self.desired(),before_write=self.check,write_command=write)
        self.assertEqual(len(self.case.commands),1);self.assertEqual(self.case.commands[0][:2],['uci','reorder'])

    def test_foreign_order_after_move_refuses_before_commit(self):
        def write(args,timeout=5):
            answer=self.write(args,timeout)
            if args[:2]==['uci','reorder']:self.case.data['sections'][0],self.case.data['sections'][1]=self.case.data['sections'][1],self.case.data['sections'][0]
            return answer
        with self.assertRaises(n.Refused):self.backend.reorder(self.desired(),before_write=self.check,write_command=write)
        self.assertEqual(len(self.case.commands),1)

    def test_stop_after_first_real_move_blocks_commit_and_later_writes(self):
        def write(args,timeout=5):
            answer=self.write(args,timeout)
            if args[:2]==['uci','reorder']:auto_control.current_revision(rotate=True)
            return answer
        with self.assertRaisesRegex(n.Refused,'CLIENT-STOP'):self.backend.reorder(self.desired(),before_write=self.check,write_command=write)
        self.assertEqual(len(self.case.commands),1);self.assertEqual(self.case.commands[0][:2],['uci','reorder'])

    def test_invalid_target_permutation_refuses_before_any_mutation(self):
        for desired in (self.before[:-1],self.before+[self.before[-1]],['foreign']+self.before[1:]):
            with self.subTest(desired=desired),self.assertRaises(n.Refused):self.backend.reorder(desired,before_write=self.check,write_command=self.write)
        self.assertEqual(self.case.commands,[])

    def wait_budget(self,spent):
        # The declared 90-second whole transaction is not silently extended.
        # Current policy caps the apply child at 50; profiling may justify a separate reviewed policy change.
        clock=[100.0];waits=[];process=self.case.process
        def spawn(args,**kwargs):
            result=process(args,**kwargs)
            if len(args)>=4 and args[0]==sys.executable and args[-2]=='apply':
                wait=result.wait.side_effect
                def observed(**options):waits.append(options.get('timeout'));return wait(**options)
                result.wait.side_effect=observed
            return result
        with patch.object(n.time,'monotonic',side_effect=lambda:clock[0]),patch.object(n.subprocess,'Popen',side_effect=spawn):
            n.attempt(self.backend,self.case.selection,NOW+180,False,control_revision=self.case.revision,
                      manual_request_id='c'*32,pair_destination='target',pair_session_order=self.case.state['order'],
                      on_dispatch=lambda:clock.__setitem__(0,100.0+spent))
        return waits,n.journal_read()

    def test_worker_wait_cap_uses_the_shorter_remaining_journal_budget(self):
        waits,journal=self.wait_budget(70)
        self.assertEqual(waits,[20.0]);self.assertEqual(journal['monotonic_deadline'],190.0)
        self.assertEqual(n.journal_read()['deadline'],NOW+90)

    def test_worker_wait_cap_is_not_silently_increased_to_the_entire_transaction(self):
        waits,journal=self.wait_budget(0)
        self.assertEqual(waits,[50]);self.assertEqual(journal['monotonic_deadline'],190.0)
        self.assertEqual(journal['deadline'],NOW+90)


if __name__=='__main__':unittest.main()
