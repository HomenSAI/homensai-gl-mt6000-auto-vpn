from pathlib import Path
import copy,random,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from cascade_model import CascadeModel,ModelError

def fixture(**options):
    return CascadeModel([dict(id=p,protocol=proto,channel=ch,priority=rank,enabled=True,connected=True) for p,proto,ch,rank in [('a','openvpn','main',1),('b','openvpn','main',2),('c','openvpn','reserve',1),('d','wireguard','other',1)]],'a',list('abcd'),'generation-1',**options)
def observe(model,now,failed):
    for p in model.profiles:
        for stamp in (now-2,now-1,now):model.probe(p,stamp,p not in failed)
def commit(model,tx,now):
    model.begin(tx['id'],now,tx['before'],model.generation)
    model.applied(tx['id'],now+1,tx['after'],model.generation)
    model.confirm(tx['id'],now+2,tx['after'],model.generation,True)

class CascadeTests(unittest.TestCase):
    def test_full_hierarchy_and_exhaustion(self):
        m=fixture();dead=set()
        for now,wanted in [(10,'b'),(80,'c'),(150,'d')]:
            dead.add(m.current);observe(m,now,dead);tx=m.plan(now,m.order,m.generation)
            self.assertEqual(tx['target'],wanted);commit(m,tx,now)
        dead.add('d');observe(m,220,dead);self.assertIsNone(m.plan(220,m.order,m.generation))
        self.assertEqual(m.phase,'EXHAUSTED');self.assertEqual([x['transition'] for x in m.history],['server','channel','protocol']);self.assertEqual(m.root,list('abcd'))
    def test_root_return_after_multiple_hops_preserves_original_order(self):
        m=fixture();observe(m,10,{'a'});commit(m,m.plan(10,m.order,m.generation),10)
        observe(m,80,{'a','b'});commit(m,m.plan(80,m.order,m.generation),80)
        for stamp in (100,130):m.probe('a',stamp,True)
        tx=m.plan(150,m.order,m.generation);self.assertTrue(tx['root_restore']);commit(m,tx,150)
        self.assertEqual(m.order,m.root);self.assertEqual(m.current,'a')
    def test_failed_hop_rolls_back_only_to_previous_hop(self):
        m=fixture();observe(m,10,{'a'});commit(m,m.plan(10,m.order,m.generation),10)
        observe(m,80,{'a','b'});tx=m.plan(80,m.order,m.generation);m.begin(tx['id'],80,tx['before'],m.generation)
        intent=m.applied(tx['id'],81,tx['after'],m.generation,False)
        self.assertEqual(intent['operation'],'restore-hop');self.assertTrue(m.rolled_back(tx['id'],82,tx['before'],m.generation))
        self.assertEqual(m.current,'b');self.assertEqual(m.root,list('abcd'));self.assertNotEqual(m.order,m.root)
    def test_target_is_rechecked_before_apply(self):
        m=fixture();observe(m,10,{'a'});tx=m.plan(10,m.order,m.generation);m.probe('b',11,False)
        self.assertIsNone(m.begin(tx['id'],11,m.order,m.generation));self.assertIsNone(m.pending)
    def test_delayed_confirmation_requests_hop_rollback(self):
        m=fixture();observe(m,10,{'a'});tx=m.plan(10,m.order,m.generation);m.begin(tx['id'],10,m.order,m.generation);m.applied(tx['id'],11,tx['after'],m.generation)
        self.assertEqual(m.confirm(tx['id'],41,tx['after'],m.generation,True)['operation'],'restore-hop')
    def test_rpc_loss_and_external_change_fail_closed(self):
        for issue in ('rpc','generation','order'):
            m=fixture();observe(m,10,{'a'});tx=m.plan(10,m.order,m.generation)
            self.assertIsNone(m.begin(tx['id'],11,list(reversed(m.order)) if issue=='order' else m.order,'other' if issue=='generation' else m.generation,rpc=issue!='rpc'))
            self.assertEqual(m.guard,'closed');self.assertIsNone(m.stop(12,m.order,m.generation))
    def test_operator_busy_never_prepares(self):
        m=fixture();observe(m,10,{'a'});self.assertIsNone(m.plan(10,m.order,m.generation,worker_busy=True));self.assertIsNone(m.pending)
    def test_stale_unbound_unknown_and_future_data_do_not_promote(self):
        for bad in ('stale','unbound','unknown','future'):
            m=fixture();observe(m,10,{'a','c','d'});m.samples['b']=[]
            for stamp in (1,2,3):m.probe('b',stamp+200 if bad=='future' else stamp,None if bad=='unknown' else True,bound=bad!='unbound')
            now=120 if bad=='stale' else 10
            if bad=='stale':
                for p in 'acd':
                    for stamp in (118,119,120):m.probe(p,stamp,False)
            self.assertIsNone(m.plan(now,m.order,m.generation));self.assertEqual(m.phase,'EXHAUSTED')
    def test_stop_holds_healthy_reserve_when_primary_is_not_verified(self):
        m=fixture();observe(m,10,{'a'});commit(m,m.plan(10,m.order,m.generation),10)
        m.stop(20,m.order,m.generation);self.assertEqual(m.phase,'STOPPED-ON-RESERVE');self.assertNotEqual(m.order,m.root)
    def test_stop_mid_apply_and_unverified_rollback(self):
        m=fixture();observe(m,10,{'a'});tx=m.plan(10,m.order,m.generation);m.begin(tx['id'],10,m.order,m.generation)
        self.assertEqual(m.stop(11,tx['after'],m.generation)['operation'],'restore-hop');self.assertFalse(m.rolled_back(tx['id'],12,tx['after'],m.generation));self.assertEqual(m.phase,'RECOVERY-REQUIRED')
    def test_stale_ack_cannot_commit_new_transaction(self):
        m=fixture();observe(m,10,{'a'});tx=m.plan(10,m.order,m.generation);m.begin(tx['id'],10,m.order,m.generation);m.applied(tx['id'],11,tx['after'],m.generation)
        with self.assertRaises(ModelError):m.confirm(999,12,tx['after'],m.generation,True)
        self.assertEqual(m.current,'a')
    def test_corrupt_journal_and_restart_do_not_resume_writes(self):
        m=fixture();observe(m,10,{'a'});m.plan(10,m.order,m.generation);snapshot=m.snapshot();restored=CascadeModel.recover(snapshot)
        self.assertEqual(restored.phase,'RECOVERY-REQUIRED');self.assertIsNone(restored.plan(11,restored.order,restored.generation))
        snapshot['data']['order'].reverse()
        with self.assertRaises(ModelError):CascadeModel.recover(snapshot)
    def test_clock_regression_and_expiry(self):
        m=fixture(lease=100);observe(m,10,{'a'});commit(m,m.plan(10,m.order,m.generation),10)
        self.assertIsNone(m.plan(9,m.order,m.generation));self.assertEqual(m.guard,'closed')
        m=fixture(lease=100);self.assertIsNone(m.plan(100,m.order,m.generation));self.assertEqual(m.phase,'STOPPED')
    def test_attempt_budget_and_no_oscillation_during_cooldown(self):
        m=fixture(max_attempts=1);observe(m,10,{'a'});commit(m,m.plan(10,m.order,m.generation),10);observe(m,80,{'a','b'})
        self.assertIsNone(m.plan(80,m.order,m.generation));self.assertEqual(m.reason,'MODEL-ATTEMPT-LIMIT')
    def test_256_seeded_failure_and_concurrency_scenarios(self):
        for seed in range(256):
            rng=random.Random(seed);m=fixture();now=10;root=list(m.root)
            for step in range(8):
                dead={p for p in m.profiles if rng.random()<.6};observe(m,now,dead)
                tx=m.plan(now,m.order,m.generation,worker_busy=rng.random()<.2)
                if tx:
                    m.begin(tx['id'],now,tx['before'],m.generation)
                    m.applied(tx['id'],now+1,tx['after'],m.generation)
                    result=m.confirm(tx['id'],now+2,tx['after'],m.generation,rng.random()<.7)
                    if result:m.rolled_back(tx['id'],now+3,tx['before'],m.generation)
                self.assertEqual(m.root,root);self.assertEqual(set(m.order),set(root));self.assertFalse(m.pending);now+=70
    def test_external_predicted_order_before_apply_is_still_external(self):
        m=fixture();observe(m,10,{'a'});tx=m.plan(10,m.order,m.generation)
        self.assertIsNone(m.begin(tx['id'],11,tx['after'],m.generation));self.assertEqual(m.phase,'BLOCKED')
    def test_unknown_rpc_or_worker_cannot_authorize_a_transition(self):
        for value in (None,'false',0):
            m=fixture();observe(m,10,{'a'})
            self.assertIsNone(m.plan(10,m.order,m.generation,rpc=value))
            m=fixture();observe(m,10,{'a'})
            self.assertIsNone(m.plan(10,m.order,m.generation,worker_busy=value))
    def test_primary_return_is_not_blocked_by_forward_attempt_budget(self):
        m=fixture(max_attempts=1);observe(m,10,{'a'});commit(m,m.plan(10,m.order,m.generation),10)
        for stamp in (80,110):m.probe('a',stamp,True)
        tx=m.plan(120,m.order,m.generation);self.assertTrue(tx['root_restore'])
    def test_restart_reconciliation_needs_fresh_bound_and_client_health(self):
        m=fixture();observe(m,10,{'a'});tx=m.plan(10,m.order,m.generation)
        restored=CascadeModel.recover(m.snapshot())
        self.assertFalse(restored.reconcile(20,tx['after'],m.generation,'b',True))
        for stamp in (20,21):restored.probe('b',stamp,True)
        self.assertFalse(restored.reconcile(22,tx['after'],m.generation,'b',None))
        self.assertTrue(restored.reconcile(22,tx['after'],m.generation,'b',True))
        self.assertEqual(restored.phase,'STOPPED-ON-RESERVE');self.assertIsNone(restored.plan(23,restored.order,m.generation));self.assertEqual(restored.root,list('abcd'))

    def test_invalid_profile_and_probe_data(self):
        m=fixture()
        for value in (float('nan'),-1,True):
            with self.assertRaises(ModelError):m.probe('a',value,True)
        with self.assertRaises(ModelError):m.probe('a',1,1)

if __name__=='__main__':unittest.main()


class AdaptiveQuarantineTests(unittest.TestCase):
    def test_failed_hops_backoff_and_probation(self):
        m=fixture()
        for now,delay in ((40,60),(160,120)):
            for p in m.profiles:
                for stamp in (now-32,now-2,now-1,now):
                    if not m.samples[p] or stamp>m.samples[p][-1]['time']:m.probe(p,stamp,p!='a')
            # All timestamps in the first round must be non-negative.
            tx=m.plan(now,m.order,m.generation)
            self.assertEqual(tx['target'],'b')
            m.begin(tx['id'],now,tx['before'],m.generation);m.applied(tx['id'],now+1,tx['after'],m.generation)
            m.confirm(tx['id'],now+2,tx['after'],m.generation,False)
            self.assertTrue(m.rolled_back(tx['id'],now+3,tx['before'],m.generation))
            self.assertEqual(m.quarantine['b'],now+3+delay)
            self.assertFalse(m._ready('b',now+4))
    def test_legacy_journal_and_invalid_counter(self):
        from cascade_model import checksum
        m=fixture();envelope=m.snapshot();envelope['data'].pop('quarantine_failures');envelope['sha256']=checksum(envelope['data'])
        self.assertEqual(CascadeModel.recover(envelope).quarantine_failures,{})
        envelope=m.snapshot();envelope['data']['quarantine_failures']={'b':-1};envelope['sha256']=checksum(envelope['data'])
        with self.assertRaises(ModelError):CascadeModel.recover(envelope)
