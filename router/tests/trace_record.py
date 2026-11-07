#!/usr/bin/env python3
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Trace conformance, existing scenario tests (tools/formal/trace_check.py, 04.11.2026). Offline, no router.

Runs the unchanged scenario tests that drive the supervisor on the fake routers (test_boot_held, test_formal_fixes,
test_forward_resume) and records, from outside, the abstract state:
  * events: every outermost native.serve (up to the end of its recovery), pair.tick, native.attempt, auto_control.start
    and auto_control.stop, with the abstract state after it and how it ended;
  * reset points: a difference between two events that is not tunnel health was written by the test itself (its own
    arrangement of a scenario): the trace restarts there from every model state with that abstract state;
  * snapshots: the abstract state after every journal, session or fake-kernel write made inside such an event (a test's
    own arrangement in setUp or between the calls is not product behaviour), for the model invariants.

The mock-only tests (test_vendor_retry, test_rescue_stable, test_held_start_handover, the return rule cases) have no
fake kernel and no supervisor loop: they are decision tables, not traces, and are not recorded here.

Usage: python3 router/tests/trace_record.py out.json
"""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'files/usr/lib/homensai-vpn'))
sys.path.insert(0, str(HERE))
import agent  # noqa: E402
import auto_control  # noqa: E402
import boot_resume  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
import pair_policy  # noqa: E402
import test_boot_held as held  # noqa: E402
import test_failure_matrix as matrix  # noqa: E402
import test_formal_fixes as fixes  # noqa: E402
import test_forward_resume as forward  # noqa: E402
from trace_driver import JOURNAL_PHASES  # noqa: E402

MODULES = (held, fixes, forward)
HEALTH_FIELDS = ('pUp', 'rUp')


class Recorder:
    def __init__(self):
        self.tests = []
        self.current = None
        self.backend = None
        self.depth = 0
        self.recovering = 0
        self.busy = False

    # ---------------------------------------------------------------------------------------------- abstract state
    def role(self, order, expected, primary):
        b = self.backend
        if b.fingerprint != expected:
            return 'F'
        try:
            base = pair_policy.role(pair_policy.proof(b.selection), list(order))
        except (ValueError, TypeError, KeyError):
            base = None
        if primary is None:
            return {'source': 'P', 'target': 'R'}.get(base, 'F')
        if list(order) == list(primary):
            return 'P'
        return 'R' if sorted(order) == sorted(primary) else 'F'

    def observe(self):
        b = self.backend
        try:
            row = pair.intent()
        except (OSError, ValueError):
            row = {}
        try:
            state = pair.read_state()
        except (OSError, ValueError):
            state = {}
        try:
            journal = native.journal_read()
        except (native.Refused, OSError, ValueError):
            journal = {}
        try:
            revision = agent.read_json(native.RUNTIME / 'auto-control-revision.json', {}).get('revision')
        except (OSError, ValueError, AttributeError):
            revision = None
        on = row.get('mode') == 'on' and revision is not None and row.get('revision') == revision
        try:
            marker = boot_resume.wanted(native.PERSIST)[0] is True
            stopped = pair.owner_stopped(state)
        except (OSError, ValueError):
            marker, stopped = False, False
        try:
            events = agent.read_json(native.RUNTIME / 'pair-readopt.json', {}).get('events', [])
        except (OSError, ValueError, AttributeError):
            events = []
        expected = state.get('policy_hash') or b.fingerprint
        sel = b.selection
        try:
            p_up, r_up = b.health(sel['source']['id']) is True, b.health(sel['target']['id']) is True
        except (OSError, ValueError, KeyError, TypeError, native.Refused):
            p_up, r_up = True, True
        return {'intent': 'on' if on else 'off', 'fresh': bool(on and state.get('id') != row.get('id')), 'marker': marker,
                'stopped': bool(stopped), 'sess': state.get('phase') or 'NONE',
                'readopt_code': bool(state.get('phase') == 'HELD' and state.get('recovery_error') in pair.READOPT_CODES),
                'ran': bool(state.get('ran')), 'ho': 'handover' in state, 'kept': 'kept' in state,
                'jr': JOURNAL_PHASES.get(journal.get('phase'), 'NONE'), 'rtp': bool(journal.get('rtp_dispatched')),
                'fails': min(2, int(journal.get('rollback_failures', 0) or 0)), 'fres': 'forward_resumed' in journal,
                'failed': bool(journal.get('failure_code')), 'uci': self.role(b.current, expected, state.get('order')),
                'kern': self.role(getattr(b, 'kernel', b.current), expected, state.get('order')),
                'guard': {None: 'none', 'full': 'full', 'vpn-only': 'vpn'}.get(b.guarded, str(b.guarded)),
                'pUp': p_up, 'rUp': r_up, 'readopt': min(3, len(events)) if isinstance(events, list) else 0}

    def safe(self):
        """The observation must never change a test: any failure of it (a test's own mock) is no snapshot."""
        if self.backend is None or self.current is None or self.busy:
            return None
        self.busy = True
        try:
            return self.observe()
        except Exception:  # noqa: BLE001  (a test's mock may raise anything here)
            self.current['unobservable'] += 1
            return None
        finally:
            self.busy = False

    def wrote(self):
        if not 0 < self.depth < 100:
            return                  # the test's own arrangement, or the shutdown path after the traced recovery
        obs = self.safe()
        if obs is not None:
            self.current['snaps'].append({'obs': obs, 'recovering': self.recovering > 0})

    # ---------------------------------------------------------------------------------------------- events
    def enter(self):
        self.depth += 1
        if self.depth == 1:
            obs = self.safe()
            if obs is not None:
                self.current['events'].append({'event': 'observe', 'obs': obs})

    def leave(self, event, end, **extra):
        self.depth -= 1
        if self.depth == 0:
            obs = self.safe()
            if obs is not None:
                self.current['events'].append(dict({'event': event, 'end': end, 'obs': obs}, **extra))


REC = Recorder()


def wrap_writer(owner, name, backend_method):
    real = getattr(owner, name)

    def hooked(*a, **k):
        if backend_method:
            REC.backend = a[0]
        result = real(*a, **k)
        REC.wrote()
        return result
    setattr(owner, name, hooked)


def wrap_entry(owner, name, event, recovery=False):
    real = getattr(owner, name)

    def hooked(*a, **k):
        # the monitor's Start is the model's RESUME step, the owner's the OWNER Start
        label = 'resume' if event == 'start' and k.get('request_source') == 'programmatic' else event
        REC.enter()
        REC.recovering += 1 if recovery else 0
        try:
            result = real(*a, **k)
        except forward.Killed:
            REC.leave('crash', 'DOWN', mid=True)
            raise
        except BaseException as error:
            REC.leave(label, 'IDLE' if type(error).__name__ == 'LoopReached' else 'DOWN')
            raise
        finally:
            REC.recovering -= 1 if recovery else 0
        REC.leave(label, 'IDLE')
        return result
    setattr(owner, name, hooked)


def wrap_serve():
    real, token = native.serve, boot_resume.write_token

    def write_token(*a, **k):
        # the supervisor's recovery is over here; its loop in these tests only ends serve() (the service-stop path)
        if REC.depth == 1 and REC.current is not None and REC.serving:
            obs = REC.safe()
            if obs is not None:
                REC.current['events'].append({'event': 'recover', 'end': 'IDLE', 'obs': obs})
            REC.serving = False
            REC.depth = 100        # nothing of the shutdown path is an event
        return token(*a, **k)
    boot_resume.write_token = write_token

    def serve():
        depth = REC.depth
        REC.enter()
        REC.serving = True
        REC.recovering += 1
        try:
            return real()
        except forward.Killed:
            obs = REC.safe()
            if obs is not None and REC.serving:
                REC.current['events'].append({'event': 'crash', 'end': 'DOWN', 'mid': True, 'obs': obs})
            raise
        except Exception:
            obs = REC.safe()
            if obs is not None and REC.serving:
                REC.current['events'].append({'event': 'recover', 'end': 'DOWN', 'obs': obs})
            raise
        finally:
            REC.recovering -= 1
            REC.serving = False
            REC.depth = depth
            if REC.current is not None:
                REC.current['events'].append({'event': 'reset'})   # the loop's shutdown path is not traced
    native.serve = serve


class Result(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        REC.current = {'test': test.id(), 'events': [], 'snaps': [], 'unobservable': 0}
        REC.backend = None
        REC.depth = 0
        REC.recovering = 0

    def stopTest(self, test):
        super().stopTest(test)
        REC.tests.append(REC.current)
        REC.current = None


def main(argv):
    REC.serving = False
    for cls in (matrix.Backend, held.Router, fixes.GuardRouter, forward.ForwardRouter):
        for name in ('guard', 'unguard', 'reorder', 'apply'):
            if name in cls.__dict__:
                wrap_writer(cls, name, True)
    wrap_writer(native, 'journal_write', False)
    wrap_writer(pair, 'save', False)
    wrap_serve()
    wrap_entry(pair, 'tick', 'tick')
    wrap_entry(pair, 'begin', 'tick')
    wrap_entry(pair, 'recover', 'recover', recovery=True)
    wrap_entry(native, 'attempt', 'tick')
    wrap_entry(auto_control, 'start', 'start')
    wrap_entry(auto_control, 'stop', 'stop')
    original_init = matrix.Backend.__init__

    def init(self, *a, **k):
        original_init(self, *a, **k)
        REC.backend = self
    matrix.Backend.__init__ = init
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in MODULES)
    stream = open('/dev/null', 'w')
    result = unittest.TextTestRunner(stream=stream, resultclass=Result, verbosity=0).run(suite)
    Path(argv[1]).write_text(json.dumps({'tests': REC.tests, 'ran': result.testsRun, 'failures': len(result.failures),
                                         'errors': len(result.errors),
                                         'problems': [t.id() for t, _ in result.failures + result.errors]}), encoding='utf-8')
    print('TRACE-RECORD python: %d tests, %d failures, %d errors, %d events, %d snapshots' % (
        result.testsRun, len(result.failures), len(result.errors), sum(len(t['events']) for t in REC.tests),
        sum(len(t['snaps']) for t in REC.tests)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
