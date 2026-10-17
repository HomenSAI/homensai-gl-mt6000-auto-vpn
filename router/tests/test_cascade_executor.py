from pathlib import Path
import copy
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files/usr/lib/homensai-vpn'))
from cascade_executor import EdgeAuthority, Journal, MemoryBackend, OfflineExecutor, Refused
from cascade_model import CascadeModel


def intent(before, target, sequence=1):
    return dict(id=sequence, operation='apply', model_only=True,
                before=list(before), after=[target]+[p for p in before if p != target])


def witness(executor, now, **changes):
    ctx = executor.pending
    row = dict(transaction=ctx['transaction'], target=ctx['target'],
               interface='lan-fixture', expected_interface='lan-fixture',
               exit='exit-'+ctx['target'], expected_exit='exit-'+ctx['target'],
               dns=True, https=True, time=now)
    row.update(changes)
    return row


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backend = MemoryBackend(list('abcd'))
        self.journal = Journal(self.tmp.name)
        self.authority = EdgeAuthority()
        self.executor = OfflineExecutor(self.backend, self.journal, self.authority)

    def prepared(self, target='b', at=1):
        self.backend.record_probe(target, at)
        return self.executor.prepare(intent(self.backend.order, target), at)

    def committed(self, target='b', at=1):
        token = self.prepared(target, at)
        self.executor.apply(token, at+1)
        self.executor.confirm(witness(self.executor, at+2), at+2)

    def test_real_model_intents_full_hierarchy_and_root_return(self):
        profiles = [dict(id=p, protocol=protocol, channel=channel, priority=1,
                         enabled=True, connected=True) for p, protocol, channel in
                    [('a','openvpn','main'), ('b','openvpn','main'),
                     ('c','openvpn','reserve'), ('d','wireguard','other')]]
        model = CascadeModel(profiles, 'a', list('abcd'), 'g1')
        dead = set()
        for at, expected in ((10,'b'), (80,'c'), (150,'d')):
            dead.add(model.current)
            for p in model.profiles:
                for t in (at-2, at-1, at):
                    model.probe(p, t, p not in dead)
            tx = model.plan(at, self.backend.order, 'g1')
            self.assertEqual(tx['target'], expected)
            self.backend.record_probe(expected, at)
            token = self.executor.prepare(tx, at)
            model.begin(tx['id'], at, self.backend.order, 'g1')
            self.executor.apply(token, at+1)
            model.applied(tx['id'], at+1, self.backend.order, 'g1')
            self.executor.confirm(witness(self.executor, at+2), at+2)
            model.confirm(tx['id'], at+2, self.backend.order, 'g1', True)
        self.assertEqual([e['transition'] for e in model.history], ['server','channel','protocol'])
        self.assertEqual(self.executor.root, list('abcd'))
        # Stable root health is necessary to obtain a model return intent.
        for p in model.profiles:
            for t in (180,181,182):model.probe(p,t,False)
        self.assertIsNone(model.plan(220,self.backend.order,'g1'))
        self.assertEqual(model.phase,'EXHAUSTED')
        self.assertEqual(self.backend.write_count,3)
        for t in (230,260):
            model.probe('a', t, True)
        tx = model.plan(270, self.backend.order, 'g1')
        self.assertTrue(tx['root_restore'])
        self.backend.record_probe('a', 270)
        token = self.executor.prepare(tx, 270)
        self.executor.apply(token, 271)
        self.executor.confirm(witness(self.executor, 272), 272)
        self.assertEqual(self.backend.order, list('abcd'))

    def test_failed_second_hop_preserves_original_root(self):
        self.committed()
        token = self.prepared('c', 10)
        self.executor.apply(token, 11)
        with self.assertRaises(Refused):
            self.executor.confirm(witness(self.executor, 12, dns=False), 12)
        self.executor.rollback(13)
        self.assertEqual(self.backend.order, list('bacd'))
        self.assertEqual(self.journal.read()['context']['root'], list('abcd'))
        self.assertEqual(self.executor.phase, 'STOPPED')

    def test_each_proof_dimension_is_bound(self):
        token = self.prepared()
        ctx = self.executor.pending
        for key in ('source','target','transaction','generation','policy_hash',
                    'metadata_revision','recovery_revision','boot_id','lease_id',
                    'profile_revision','expected_interface','expected_exit',
                    'root','before','after'):
            with self.subTest(key=key):
                authority = EdgeAuthority()
                token = authority.issue(ctx, 1, 20)
                changed = copy.deepcopy(ctx)
                if isinstance(changed[key], list):
                    changed[key] = list(reversed(changed[key]))
                elif key == 'policy_hash':
                    changed[key] = '0'*64
                else:
                    changed[key] += '-changed'
                with self.assertRaises(Refused):
                    authority.consume(token, changed, 2)
                # Failed consumption burns the handle too.
                with self.assertRaises(Refused):
                    authority.consume(token, ctx, 2)

    def test_replay_expiry_and_restart_are_refused(self):
        token = self.prepared()
        ctx = self.executor.pending
        self.authority.consume(token, ctx, 2)
        with self.assertRaises(Refused):
            self.authority.consume(token, ctx, 2)
        token = self.authority.issue(ctx, 2, 3)
        with self.assertRaises(Refused):
            self.authority.consume(token, ctx, 3)
        with self.assertRaises(Refused):
            EdgeAuthority().consume(token, ctx, 3)

    def test_changed_metadata_blocks_apply_without_write(self):
        for index, key in enumerate(('generation', 'metadata_revision', 'recovery_revision',
                    'profile_revision', 'policy_hash', 'boot_id')):
            with self.subTest(key=key):
                original = getattr(self.backend, key)
                at = 1 + index*3
                token = self.prepared(at=at)
                setattr(self.backend, key, 'changed')
                with self.assertRaises(Refused):
                    self.executor.apply(token, at+1)
                self.assertEqual(self.backend.writes, [])
                setattr(self.backend, key, original)
                self.backend.release(self.executor.pending['lease_id'])
                self.executor.phase = 'STOPPED'

    def test_operator_and_worker_contend_for_same_lease(self):
        self.prepared()
        with self.assertRaisesRegex(Refused, 'LEASE-BUSY'):
            self.backend.external_edit(list('cadb'), 2)
        with self.assertRaisesRegex(Refused, 'LEASE-BUSY'):
            self.backend.acquire('worker', 2)
        self.assertEqual(self.backend.order, list('abcd'))

    def test_lease_contenders_only_one_winner(self):
        winners = []
        barrier = threading.Barrier(8)
        def contender(i):
            barrier.wait()
            try:
                winners.append(self.backend.acquire('worker-'+str(i), 1))
            except Refused:
                pass
        threads = [threading.Thread(target=contender, args=(i,)) for i in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(len(winners), 1)

    def test_expired_lease_never_overwrites_operator_edit(self):
        token = self.prepared()
        self.executor.apply(token, 2)
        self.backend.external_edit(list('cadb'), 32)
        with self.assertRaises(Refused):
            self.executor.rollback(33)
        self.assertEqual(self.backend.order, list('cadb'))
        self.assertEqual(len(self.backend.writes), 1)

    def test_witness_cannot_self_declare_expected_path(self):
        token = self.prepared()
        self.executor.apply(token, 2)
        for changes in (dict(interface='wifi', expected_interface='wifi'),
                        dict(exit='wrong', expected_exit='wrong'),
                        dict(dns=1), dict(https=False), dict(time=1),
                        dict(time=4), dict(transaction='old'), dict(target='c')):
            with self.subTest(changes=changes), self.assertRaises(Refused):
                self.executor.confirm(witness(self.executor, 3, **changes), 3)
        self.executor.confirm(witness(self.executor, 3), 3)

    def test_confirmation_rechecks_policy_not_only_order(self):
        token = self.prepared()
        self.executor.apply(token, 2)
        self.backend.metadata_revision = 'externally-changed'
        with self.assertRaises(Refused):
            self.executor.confirm(witness(self.executor, 3), 3)
        with self.assertRaises(Refused):
            self.executor.rollback(3)
        self.assertEqual(len(self.backend.writes), 1)

    def test_crash_at_each_phase_recovers_held_without_writes(self):
        for phase in Journal.PHASES:
            with self.subTest(phase=phase):
                if self.backend.lease:
                    self.backend.release(self.backend.lease['id'])
                self.executor.phase = 'STOPPED'
                self.prepared(at=10)
                if phase in ('WAIT-CONFIRM', 'COMMITTED'):
                    self.backend.order = list(self.executor.pending['after'])
                self.executor._save(phase, 10, self.backend.order[0])
                writes = copy.deepcopy(self.backend.writes)
                restarted = OfflineExecutor(self.backend, self.journal, EdgeAuthority())
                report = restarted.recover()
                self.assertEqual(report['phase'], 'HELD')
                self.assertFalse(report['auto'])
                self.assertEqual(report['prior_phase'], phase)
                self.assertEqual(self.backend.writes, writes)
                self.backend.order = list('abcd')

    def test_corrupt_missing_and_oversized_journals_do_not_change_policy(self):
        self.prepared()
        good = self.journal.path.read_bytes()
        for data in (b'not-json', b'{}', b'x'*(Journal.LIMIT+1)):
            self.journal.path.write_bytes(data)
            with self.assertRaises(Refused): self.executor.recover()
            self.assertEqual(self.backend.writes, [])
        self.journal.path.write_bytes(good)
        self.journal.path.unlink()
        with self.assertRaises(Refused): self.executor.recover()

    def test_previous_good_is_retained_if_current_corrupt(self):
        token = self.prepared()
        self.executor.apply(token, 2)
        previous = self.journal.previous.read_bytes()
        self.journal.path.write_text('broken')
        with self.assertRaises(Refused):
            self.executor._save('STOPPED', 3, 'a')
        self.assertEqual(self.journal.previous.read_bytes(), previous)
        self.assertEqual(self.journal.read(previous=True)['phase'], 'APPLYING')

    def test_restart_changed_generation_is_blocked(self):
        self.prepared()
        self.backend.generation = 'external'
        with self.assertRaisesRegex(Refused, 'RECOVERY-EXTERNAL'):
            self.executor.recover()
        self.assertEqual(self.backend.writes, [])

    def test_journal_rejects_secrets_unknown_fields_and_bad_checksum(self):
        self.prepared()
        row = self.journal.read()
        row['token'] = 'synthetic-not-a-real-token'
        with self.assertRaises(Refused): self.journal.write(row)
        data = json.loads(self.journal.path.read_text())
        data['payload']['context']['root'].reverse()
        self.journal.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(Refused, 'CHECKSUM'): self.journal.read()

    def test_no_native_backend_or_clock_regression(self):
        with self.assertRaisesRegex(Refused, 'NATIVE-UNVERIFIED'):
            OfflineExecutor(object(), self.journal, self.authority)
        token = self.prepared(at=3)
        with self.assertRaisesRegex(Refused, 'CLOCK-REGRESSION'):
            self.executor.apply(token, 2)
        self.assertEqual(self.backend.writes, [])

    def test_stop_before_apply_does_not_accept_predicted_external_order(self):
        self.prepared()
        self.backend.order = list('bacd')
        with self.assertRaisesRegex(Refused, 'EXTERNAL-POLICY'):
            self.executor.rollback(2)
        self.assertEqual(self.backend.writes, [])

    def test_probe_must_be_recent_bound_and_successful(self):
        for index, changes in enumerate((dict(dns=False), dict(https=False),
                                        dict(bound=False), dict(dns=1))):
            at = 1 + index*3
            self.backend.record_probe('b', at, **changes)
            with self.assertRaisesRegex(Refused, 'PROBE-UNVERIFIED'):
                self.executor.prepare(intent(self.backend.order, 'b'), at)
            self.executor.phase = 'STOPPED'
        self.backend.record_probe('b', 20)
        with self.assertRaisesRegex(Refused, 'PROBE-STALE'):
            self.executor.prepare(intent(self.backend.order, 'b'), 26)
        self.assertEqual(self.backend.writes, [])

    def test_delayed_apply_rejects_aged_probe_even_with_live_lease(self):
        token = self.prepared()
        with self.assertRaisesRegex(Refused, 'PROBE-STALE'):
            self.executor.apply(token, 7)
        self.assertEqual(self.backend.writes, [])

    def test_recovery_checks_metadata_and_phase_not_only_generation(self):
        self.prepared()
        self.backend.metadata_revision = 'changed'
        with self.assertRaisesRegex(Refused, 'RECOVERY-EXTERNAL'):
            self.executor.recover()
        self.backend.metadata_revision = 'm1'
        self.backend.order = list('bacd')
        with self.assertRaisesRegex(Refused, 'RECOVERY-EXTERNAL'):
            self.executor.recover()

    def test_process_death_before_and_after_each_journal_replace(self):
        # Actually interrupt transitions, rather than inventing only phase labels.
        for wanted in ('PREPARED', 'APPLYING', 'WAIT-CONFIRM', 'COMMITTED',
                       'ROLLING-BACK', 'STOPPED'):
            for when in ('before', 'after'):
                with self.subTest(phase=wanted, when=when):
                    directory = Path(self.tmp.name) / (wanted+'-'+when)
                    backend = MemoryBackend(list('abcd'))
                    journal = Journal(directory)
                    executor = OfflineExecutor(backend, journal, EdgeAuthority())
                    backend.record_probe('b', 1)
                    original_write = journal.write
                    def interrupted(row):
                        if row['phase'] == wanted and when == 'before':
                            raise SystemExit('simulated process death')
                        original_write(row)
                        if row['phase'] == wanted and when == 'after':
                            raise SystemExit('simulated process death')
                    journal.write = interrupted
                    with self.assertRaises(SystemExit):
                        token = executor.prepare(intent(backend.order, 'b'), 1)
                        executor.apply(token, 2)
                        if wanted in ('ROLLING-BACK', 'STOPPED'):
                            executor.rollback(3)
                        else:
                            executor.confirm(witness(executor, 3), 3)
                    before = copy.deepcopy(backend.writes)
                    recovered = OfflineExecutor(backend, journal, EdgeAuthority())
                    if not journal.path.exists():
                        with self.assertRaises(Refused): recovered.recover()
                    else:
                        self.assertFalse(recovered.recover()['auto'])
                    self.assertEqual(recovered.phase, 'HELD')
                    self.assertEqual(backend.writes, before)

    def test_stop_during_prepared_and_wait_confirm_is_explicitly_stopped(self):
        self.prepared()
        self.executor.rollback(2)
        self.assertEqual(self.executor.phase, 'STOPPED')
        self.assertEqual(self.backend.order, list('abcd'))
        token = self.prepared(at=4)
        self.executor.apply(token, 5)
        self.executor.rollback(6)
        self.assertEqual(self.executor.phase, 'STOPPED')
        self.assertEqual(self.backend.order, list('abcd'))

    @unittest.skipUnless(os.name == 'posix', 'POSIX directory ownership')
    def test_existing_public_journal_directory_is_refused(self):
        public = Path(self.tmp.name) / 'public'
        public.mkdir(mode=0o755)
        with self.assertRaisesRegex(Refused, 'JOURNAL-NOT-PRIVATE'):
            Journal(public)

    def test_rpc_timeout_before_and_after_write_never_resumes_auto(self):
        for applied in (False,True):
            with self.subTest(applied=applied):
                backend=MemoryBackend(list('abcd'));backend.record_probe('b',1)
                journal=Journal(Path(self.tmp.name)/('timeout-'+str(applied)))
                executor=OfflineExecutor(backend,journal,EdgeAuthority())
                token=executor.prepare(intent(backend.order,'b'),1)
                original=backend.apply
                def timeout(*args,**kwargs):
                    if applied:original(*args,**kwargs)
                    raise TimeoutError('synthetic RPC timeout')
                with patch.object(backend,'apply',side_effect=timeout),self.assertRaises(TimeoutError):
                    executor.apply(token,2)
                before=copy.deepcopy(backend.writes)
                restarted=OfflineExecutor(backend,journal,EdgeAuthority())
                self.assertFalse(restarted.recover()['auto'])
                self.assertEqual(restarted.phase,'HELD')
                self.assertEqual(backend.writes,before)

    def test_operator_stop_during_apply_after_transport_failure(self):
        token=self.prepared()
        with patch.object(self.backend,'apply',side_effect=TimeoutError),self.assertRaises(TimeoutError):
            self.executor.apply(token,2)
        self.assertEqual(self.executor.phase,'APPLYING')
        self.executor.rollback(3)
        self.assertEqual(self.executor.phase,'STOPPED')
        self.assertEqual(self.backend.order,list('abcd'))


if __name__ == '__main__':
    unittest.main()
