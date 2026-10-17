from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from candidate_runtime import CandidateSession, MemoryProfileBackend, ProbeScheduler
from cascade_executor import Refused


def binding(profile='b'):
    return dict(profile=profile, interface='test-tun', namespace='test-ns',
                mark=25, isolated=True, revision='r1')


class CandidateTests(unittest.TestCase):
    def backend(self):
        return MemoryProfileBackend(dict(a=dict(protocol='openvpn', state='connected', revision='a1'),
                                         b=dict(protocol='wireguard', state='inactive', revision='b1')))

    def test_connect_cancel_only_owned_profile(self):
        backend = self.backend()
        session = CandidateSession(backend, 'b', 1)
        self.assertEqual(session.poll(2), 'connecting')
        backend.profiles['b']['state'] = 'connected'
        self.assertEqual(session.poll(3), 'connected')
        self.assertEqual(session.cancel(), 'cancelled')
        self.assertEqual(backend.profiles['a']['state'], 'connected')
        self.assertEqual(backend.profiles['b']['state'], 'inactive')
        self.assertEqual(session.cancel(), 'cancelled')

    def test_timeout_failed_and_removed_do_not_stop_primary(self):
        for reason in ('timeout','failed','removed','edited'):
            backend = self.backend()
            session = CandidateSession(backend, 'b', 1)
            if reason == 'failed': backend.profiles['b']['state'] = 'failed'
            if reason == 'removed': del backend.profiles['b']
            if reason == 'edited': backend.profiles['b']['revision'] = 'external'
            if reason in ('removed','edited'):
                with self.assertRaises(Refused): session.poll(2)
                self.assertEqual(session.state, 'held')
            else:
                self.assertEqual(session.poll(21 if reason == 'timeout' else 2), reason)
            self.assertEqual(backend.profiles['a']['state'], 'connected')

    def test_start_busy_and_native_are_refused(self):
        backend = self.backend()
        with self.assertRaises(Refused): CandidateSession(backend, 'a', 1)
        CandidateSession(backend, 'b', 1)
        with self.assertRaises(Refused): CandidateSession(backend, 'b', 1)
        with self.assertRaises(Refused): CandidateSession(object(), 'b', 1)

    def test_probe_budgets_remain_charged_after_cancel_and_invalid_result(self):
        scheduler = ProbeScheduler(byte_budget=8192)
        handle = scheduler.reserve('b', binding(), 1)
        scheduler.cancel(handle)
        handle = scheduler.reserve('b', binding(), 2)
        with self.assertRaises(Refused):
            scheduler.finish(handle, binding(), 3, 4097, True, True)
        self.assertEqual(scheduler.charged, 8192)
        self.assertFalse(scheduler.active)
        with self.assertRaisesRegex(Refused, 'BUDGET'):
            scheduler.reserve('b', binding(), 3)

    def test_binding_limits_and_timeout(self):
        scheduler = ProbeScheduler()
        for changes in (dict(isolated=False), dict(mark=0), dict(mark=True),
                        dict(profile='a'), dict(namespace='')):
            changed = binding(); changed.update(changes)
            with self.assertRaises(Refused): scheduler.reserve('b', changed, 1)
        handle = scheduler.reserve('b', binding(), 1)
        scheduler.reserve('c', binding('c'), 1)
        with self.assertRaises(Refused): scheduler.reserve('d', binding('d'), 1)
        changed = binding(); changed['revision'] = 'r2'
        with self.assertRaises(Refused): scheduler.finish(handle, changed, 2, 20, True, True)
        self.assertEqual(scheduler.expire(11), 1)
        self.assertFalse(scheduler.active)

    def test_bound_result_and_replay(self):
        scheduler = ProbeScheduler()
        original = binding()
        handle = scheduler.reserve('b', original, 1)
        original['mark'] = 99
        with self.assertRaises(Refused): scheduler.finish(handle, original, 2, 20, True, True)
        handle = scheduler.reserve('b', binding(), 2)
        result = scheduler.finish(handle, binding(), 3, 100, True, False)
        self.assertEqual(result['scope'], 'offline-fixture')
        self.assertFalse(result['https'])
        with self.assertRaises(Refused): scheduler.finish(handle, binding(), 3, 100, True, True)


if __name__ == '__main__': unittest.main()
