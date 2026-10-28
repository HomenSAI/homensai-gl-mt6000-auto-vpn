"""Real files, alpha53 hashes and self-invalid journal; no live router involved."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair,pair_policy,stock_recovery as recovery
import test_stock_derived_contract as stock


class StockRecovery(unittest.TestCase):
    def setUp(self):
        from contextlib import ExitStack
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        temporary=self.stack.enter_context(tempfile.TemporaryDirectory());self.root=Path(temporary)
        self.persist=self.root/'persist';self.runtime=self.root/'runtime';self.persist.mkdir();self.runtime.mkdir()
        for module in (agent,n,auto_control):
            for key,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,key):self.stack.enter_context(patch.object(module,key,value))
        self.stack.enter_context(patch.object(n,'JOURNAL',self.persist/'native-transaction.json'))
        self.stack.enter_context(patch.object(n,'STATE',self.runtime/'native-status.json'))
        self.stack.enter_context(patch('activation_recovery.platform_checked'))
        self.stack.enter_context(patch('native_platform.wait_quiet'))
        self.stack.enter_context(patch.object(recovery,'writers_quiet'))
        self.publish=self.stack.enter_context(patch.object(n,'publish'))
        self.revision=auto_control.current_revision();pair.stop_locked(self.revision)
        self.before,self.profiles=stock.stock_data();self.before['sections'][-2:]=reversed(self.before['sections'][-2:])
        self.selection=n.choose(self.before,self.profiles);managed={'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}
        self.old_network=[{'.name':name,'.type':'interface','proto':proto,'config':'fixture','auto':'0','disabled':'0'} for name,proto in managed.items()]
        self.old_network += [{'.name':'r1','.type':'rule','priority':'100','lookup':'1'},{'.name':'wwan','.type':'interface','proto':'dhcp'},{'.name':'r2','.type':'rule','priority':'100','lookup':'2'}]
        self.rows=self.old_network[:2]+[self.old_network[3],self.old_network[2],self.old_network[4]]
        self.current=copy.deepcopy(self.before)
        for row in self.current['sections'][-2:]:row['options_in_used']='0'
        self.state={'id':'a'*32,'phase':'HELD','revision':self.revision,'owned':[],'before_flags':{key:'0' for key in managed},'interfaces':managed,
                    'network_identity':recovery.legacy_network(self.old_network,managed),'protected':{},'process_bindings':stock.BINDINGS,
                    'order':self.selection['order'],'policy_hash':self.selection['hash'],'policy_roles':pair_policy.proof(self.selection)}
        pair.save(self.state)
        order=self.selection['order']
        self.journal={'tx':'b'*32,'phase':'RESTORING','source':self.selection['source']['id'],'target':self.selection['target']['id'],'before':order,'after':order,
                      'hash':self.selection['hash'],'started':1,'deadline':100000,'trial_nonce':'fixture','process_bindings':stock.BINDINGS,
                      'vendor_identity':self.selection['vendor_identity'],'pair_transition':pair_policy.transition(self.selection,order,'target'),
                      'activation_reapply':True,'rtp_dispatched':True,'kernel_before_verified':False,'restore_before_verified':True,
                      'restore_target_order':order,'restore_before_order':recovery.legacy_order(self.current['sections'])}
        agent.atomic_json(n.JOURNAL,{'schema':1,'data':self.journal,'sha256':n.digest(self.journal)})
        self.raw=n.JOURNAL.read_bytes();self.state_raw=pair.paths()[1].read_bytes()
        self.baseline={'network':self.old_network,'route_policy':self.before['sections']}
        self.backend=Mock();self.backend.policy.side_effect=lambda:self.current
        self.backend.order.side_effect=lambda:(n.policy_order(self.current['sections'],stock.BINDINGS),n.policy_hash(self.current['sections'],stock.BINDINGS))
        self.backend.diagnostic.side_effect=lambda:([],n.choose(self.current,self.profiles))
        self.backend.attest_policy.side_effect=lambda *a:{'verified':True,'role':'target','profile_id':self.selection['target']['id'],'order':order,'policy_hash':self.selection['hash'],'time':recovery.time.time(),'kernel_fingerprint':'f'*64}
        self.guarded=True;self.backend.guard_exists.side_effect=lambda:self.guarded
        self.backend.unguard.side_effect=lambda:setattr(self,'guarded',False)
        self.stack.enter_context(patch.object(pair,'network',side_effect=lambda:self.rows))
        self.stack.enter_context(patch.object(pair,'configs',return_value={}))

    def test_exact_known_pattern_archives_closes_and_completes_real_stop_without_rtp(self):
        with self.assertRaises(n.Refused):n.journal_read()
        result=recovery.recover(self.baseline,self.backend)
        self.assertEqual(result['result'],'KNOWN_STOCK_CHANGE_STOPPED');self.assertEqual(pair.read_state()['phase'],'STOPPED')
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertFalse(self.guarded)
        self.backend.apply.assert_not_called();self.backend.reorder.assert_not_called()
        archives=list((self.persist/'session-recovery').iterdir());self.assertEqual(len(archives),2)
        self.assertIn(self.raw,[p.read_bytes() for p in archives]);self.assertIn(self.state_raw,[p.read_bytes() for p in archives])
        after=(n.JOURNAL.read_bytes(),pair.paths()[1].read_bytes())
        self.assertEqual(recovery.recover(self.baseline,self.backend)['result'],'ALREADY_STOPPED')
        self.assertEqual(after,(n.JOURNAL.read_bytes(),pair.paths()[1].read_bytes()));self.assertEqual(len(list((self.persist/'session-recovery').iterdir())),2)

    def test_check_is_read_only_and_requires_real_independent_old_baseline(self):
        self.assertEqual(recovery.recover(self.baseline,self.backend,True)['result'],'READY_KNOWN_STOCK_CHANGE')
        self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertFalse((self.persist/'session-recovery').exists())
        with self.assertRaises(n.Refused):recovery.recover({'network':self.rows,'route_policy':self.current['sections']},self.backend)

    def test_foreign_rule_value_network_order_or_kernel_refuses_without_archive(self):
        for mutation in ('policy','network','kernel'):
            with self.subTest(mutation=mutation):
                old=copy.deepcopy(self.current);rows=copy.deepcopy(self.rows);proof=self.backend.attest_policy.side_effect
                if mutation=='policy':self.current['sections'][-1]['mark']='0x2000'
                elif mutation=='network':self.rows[-1],self.rows[-2]=self.rows[-2],self.rows[-1]
                else:self.backend.attest_policy.side_effect=lambda *a:{'verified':False}
                with self.assertRaises(n.Refused):recovery.recover(self.baseline,self.backend)
                self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertFalse((self.persist/'session-recovery').exists())
                self.current=old;self.rows=rows;self.backend.attest_policy.side_effect=proof

    def test_journal_replacement_during_proof_is_preserved(self):
        original=recovery.facts
        def changed(*args):
            result=original(*args);row=copy.deepcopy(self.journal);row['failure_code']='OTHER';agent.atomic_json(n.JOURNAL,{'schema':1,'data':row,'sha256':n.digest(row)});return result
        with patch.object(recovery,'facts',side_effect=changed),self.assertRaises(n.Refused):recovery.recover(self.baseline,self.backend)
        self.assertEqual(json.loads(n.JOURNAL.read_bytes())['data']['failure_code'],'OTHER');self.assertFalse((self.persist/'session-recovery').exists())

    def test_stop_epoch_change_before_unguard_retains_guard(self):
        original=self.backend.order.side_effect;calls=[0]
        def changed():
            result=original();calls[0]+=1
            if pair.read_state()['phase']=='STOPPING':auto_control.current_revision(rotate=True)
            return result
        self.backend.order.side_effect=changed
        with self.assertRaises(n.Refused):recovery.recover(self.baseline,self.backend)
        self.assertTrue(self.guarded);self.backend.unguard.assert_not_called()

    def test_partial_state_then_journal_commit_resumes_only_archived_original_transaction(self):
        budget=self.persist/'pair-auto-budget.json';agent.atomic_json(budget,{'events':[1,2,3]});old_budget=budget.read_bytes()
        with patch.object(n,'journal_write',side_effect=OSError('simulated interrupted second file')),self.assertRaises(OSError):
            recovery.recover(self.baseline,self.backend)
        self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertNotEqual(pair.paths()[1].read_bytes(),self.state_raw);self.assertTrue(self.guarded)
        self.assertEqual(recovery.recover(self.baseline,self.backend)['result'],'KNOWN_STOCK_CHANGE_STOPPED')
        self.assertEqual(budget.read_bytes(),old_budget);self.assertEqual(len(list((self.persist/'session-recovery').iterdir())),2)
        self.backend.apply.assert_not_called()

    def test_interruption_after_archiving_before_first_state_write_can_resume(self):
        original=recovery.facts;calls=[0]
        def interrupted(*args):
            answer=original(*args);calls[0]+=1
            if calls[0]==3:raise OSError('simulated interruption after durable archive')
            return answer
        with patch.object(recovery,'facts',side_effect=interrupted),self.assertRaises(OSError):recovery.recover(self.baseline,self.backend)
        self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertEqual(pair.paths()[1].read_bytes(),self.state_raw)
        self.assertEqual(recovery.recover(self.baseline,self.backend)['result'],'KNOWN_STOCK_CHANGE_STOPPED')
        self.assertEqual(len(list((self.persist/'session-recovery').iterdir())),2)

    def test_verified_but_different_kernel_after_archive_refuses_before_state_or_journal_commit(self):
        original=self.backend.attest_policy.side_effect;calls=[0]
        def changed(*args):
            answer=original(*args);calls[0]+=1
            if calls[0]>=3:answer['kernel_fingerprint']='e'*64
            return answer
        self.backend.attest_policy.side_effect=changed
        with self.assertRaises(n.Refused):recovery.recover(self.baseline,self.backend)
        self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertEqual(pair.paths()[1].read_bytes(),self.state_raw);self.assertTrue(self.guarded)
        with self.assertRaises(n.Refused):recovery.recover(self.baseline,self.backend)
        self.backend.unguard.assert_not_called()

    def test_publication_interruption_after_completed_stop_does_not_repeat_persistent_writes(self):
        self.publish.side_effect=OSError('simulated RAM publication failure')
        with self.assertRaises(OSError):recovery.recover(self.baseline,self.backend)
        self.assertEqual(pair.read_state()['phase'],'STOPPED');self.assertFalse(self.guarded)
        old=(n.JOURNAL.read_bytes(),pair.paths()[1].read_bytes())
        with patch.object(pair,'save') as save,patch.object(n,'journal_write') as write:
            self.assertEqual(recovery.recover(self.baseline,self.backend)['result'],'ALREADY_STOPPED')
            save.assert_not_called();write.assert_not_called()
        self.assertEqual(old,(n.JOURNAL.read_bytes(),pair.paths()[1].read_bytes()))

    def test_stale_kernel_timestamp_cannot_authorize_recovery(self):
        original=self.backend.attest_policy.side_effect
        self.backend.attest_policy.side_effect=lambda *args:dict(original(*args),time=recovery.time.time()-6)
        with self.assertRaises(n.Refused):recovery.recover(self.baseline,self.backend)
        self.assertFalse((self.persist/'session-recovery').exists());self.backend.unguard.assert_not_called()

    def test_archive_directory_is_synced_before_descriptor_or_any_target_write(self):
        import os,stat
        original=os.fsync;seen=[];directory=self.persist/'session-recovery'
        def synced(fd):
            info=os.fstat(fd)
            if directory.exists() and stat.S_ISDIR(info.st_mode) and info.st_ino==directory.stat().st_ino:
                self.assertFalse((self.persist/'stock-derived-recovery.json').exists())
                self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.assertEqual(pair.paths()[1].read_bytes(),self.state_raw)
                self.assertEqual(len(list(directory.iterdir())),2);seen.append(True)
            return original(fd)
        with patch.object(recovery.os,'fsync',side_effect=synced):recovery.recover(self.baseline,self.backend)
        self.assertEqual(seen,[True])


class WriterCoordination(unittest.TestCase):
    def test_real_process_and_procd_readers_require_native_instance_and_children_absent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=root/'proc'/'123';directory.mkdir(parents=True);cmdline=directory/'cmdline'
            cmdline.write_bytes(b'/usr/bin/python3\0/usr/lib/homensai-vpn/agent.py\0daemon\0')
            service={'homensai-vpn':{'instances':{'monitor':{'running':True}}}}
            with patch.object(recovery,'ROOT',root),patch.object(n,'command',side_effect=lambda *a:json.dumps(service).encode()):
                recovery.writers_quiet()
                service['homensai-vpn']['instances']['native']={'running':False}
                with self.assertRaises(n.Refused):recovery.writers_quiet()
                service['homensai-vpn']['instances'].pop('native')
                cmdline.write_bytes(b'/usr/bin/python3\0/usr/lib/homensai-vpn/native_switch.py\0apply\0fixture\0')
                with self.assertRaises(n.Refused):recovery.writers_quiet()


if __name__=='__main__':unittest.main()
