#!/usr/bin/env python3
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Trace-conformance driver, Python line (tools/formal/trace_check.py, 04.11.2026). Offline, no router.

Runs the real supervisor (native_switch.serve, pair_auto, forward_resume, auto_control, boot_resume) on the fake
router of tests/test_forward_resume.py (UCI order and kernel order kept apart, the apply child in this process) and
applies a scenario of abstract events between the loop passes (the scheduler is the loop's speed_pause.gate):

  tick                one pass of the supervisor loop
  start / stop        the owner's Start (manual) / Stop (auto_control)
  resume              the monitor's boot/restart resume (boot_resume.run after a power cut, else watch)
  crash               SIGKILL between two passes; crash@N: during the next pass right after its N-th product write
  power               power cut between two passes (RAM files, guard, in-process state lost, tunnels down after the
                      boot); power@N: during the next pass after its N-th product write
  p_down/p_up/r_down/r_up   primary/reserve tunnel health (the monitor's probes, the confirmation probes)
  r_lost              the reserve client is not connected at all: like r_down, and diagnostic() answers
                      RESERVE-NOT-CONNECTED (native_switch.Linux.diagnostic: VPN-001 live and measured); r_up ends it
  gl_pol / gl_net     the owner edits the route policy / the VPN clients in the GL panel
  busy                the vendor is busy: the next kernel write (rtp2) fails once
  wait / wait_long    time passes (60 s / 700 s)

After every event the abstract state is read back from the product files (journal, pair session, intent, resume
marker, readopt ledger) and the fake kernel (UCI order, kernel order, nft guard): tools/formal/trace_check.py
projects model.py states onto the same fields and checks every step. Usage (Linux, the CI container):

  python3 router/tests/trace_driver.py scenarios.json traces.json
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
from unittest.mock import patch, MagicMock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'files/usr/lib/homensai-vpn'))
sys.path.insert(0, str(HERE))
import agent  # noqa: E402
import auto_control  # noqa: E402
import boot_resume  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
import test_boot_held as held  # noqa: E402
from test_forward_resume import ForwardRouter  # noqa: E402

JOURNAL_PHASES = {None: 'NONE', 'ARMED': 'ARMED', 'APPLYING': 'APPLYING', 'WAIT-CLIENT': 'WAIT', 'COMMITTED': 'COMMITTED',
                  'HELD-ON-RESERVE': 'HOR', 'RESTORING': 'RESTORING', 'ROLLED-BACK': 'RB', 'RELEASE-PENDING': 'RP'}
REAL_TIME, REAL_MONO, REAL_SLEEP = time.time, time.monotonic, time.sleep


class Killed(BaseException):
    """SIGKILL / power cut: never caught by the code under test."""


class ScenarioEnd(BaseException):
    """No event left."""


class Hung(BaseException):
    """A scenario ran longer than its wall-clock budget (a loop that never ends)."""


class Clock:
    """One fake clock for time.time/time.monotonic: sleeps advance it, the driver's waits too."""
    def __init__(self):
        self.wall = REAL_TIME()
        self.mono = 5000.0
        self.boot = 0.0          # mono at the last power-on (uptime = mono - boot)

    def time(self):
        return self.wall

    def monotonic(self):
        return self.mono

    def sleep(self, seconds):
        self.advance(min(max(float(seconds or 0), 0.0), 120.0))

    def advance(self, seconds):
        self.wall += seconds
        self.mono += seconds


class Driver(held.Fixture):
    """test_boot_held.Fixture (temporary router files, ubus/ifup fakes) with the fake kernel of test_forward_resume."""
    INTERFACES = dict(pair.INTERFACES)

    def runTest(self):  # unittest.TestCase needs a method; the driver calls setUp/run_scenario/doCleanups itself
        pass

    # ---------------------------------------------------------------------------------------------------- setup
    def setUp(self):
        super().setUp()
        self.clock = Clock()
        st = self.stack
        # RAM (RUNTIME) apart from flash (PERSIST): the fixture shares one directory, a power cut empties RUNTIME only
        self.ram = self.dir / 'run'
        self.ram.mkdir()
        for module in list(sys.modules.values()):
            if getattr(module, 'RUNTIME', None) == self.dir:
                st.enter_context(patch.object(module, 'RUNTIME', self.ram))
        st.enter_context(patch.object(time, 'time', side_effect=self.clock.time))
        st.enter_context(patch.object(time, 'monotonic', side_effect=self.clock.monotonic))
        st.enter_context(patch.object(native.time, 'sleep', side_effect=self.clock.sleep))
        self.b = ForwardRouter(self.RENAME)
        b = self.b
        b.up = {name: True for name in b.up}
        self.source, self.target = b.selection['source']['id'], b.selection['target']['id']
        b.health_of = {self.source: True, self.target: True}
        self.base_order = self.before[:]
        self.identity = held.IDENTITY
        st.enter_context(patch.object(native, 'Linux', return_value=b))
        st.enter_context(patch.object(native.os, 'killpg'))
        ids = iter('%032x' % n for n in range(1, 100000))
        st.enter_context(patch.object(native.uuid, 'uuid4', side_effect=lambda: MagicMock(hex=next(ids))))
        st.enter_context(patch.object(pair, '_uptime', side_effect=lambda: self.clock.mono - self.clock.boot))
        st.enter_context(patch.object(pair, 'interface_up', side_effect=lambda name: b.up.get(name, False)))
        st.enter_context(patch.object(pair, 'normalized_network', side_effect=lambda *a: self.identity))
        import rtp_boot
        st.enter_context(patch.object(rtp_boot, 'contract'))
        st.enter_context(patch.object(rtp_boot, 'checked', return_value=MagicMock()))
        st.enter_context(patch('rollback_recovery.vendor_settled'))
        st.enter_context(patch.object(native, 'trace', side_effect=self.exit_of))
        st.enter_context(patch.object(native, 'probe', side_effect=self.probe))
        # the router-probed decision inputs follow the abstract tunnel health (the monitor's samples are not simulated)
        import channel_model
        import failover_plan
        import failure_diagnosis
        st.enter_context(patch.object(channel_model, 'channel_failed', side_effect=lambda samples, identifier, *a, **k: not self.healthy(identifier)))
        st.enter_context(patch.object(channel_model, 'return_ready', side_effect=lambda samples, identifier, *a, **k: self.healthy(identifier)))
        st.enter_context(patch.object(failover_plan, 'streak', side_effect=self.streak))
        if hasattr(native, 'streak'):
            st.enter_context(patch.object(native, 'streak', side_effect=self.streak))
        st.enter_context(patch.object(failure_diagnosis, 'diagnose', return_value={'suppress_switch': False}))
        st.enter_context(patch.object(failure_diagnosis, 'resolve_pair', side_effect=self.resolve_pair))
        st.enter_context(patch.object(pair, 'source_unstable', return_value=False))
        st.enter_context(patch.object(pair, 'preflight', side_effect=self.preflight))
        st.enter_context(patch('pair_interfaces.selection', return_value=dict(self.INTERFACES)))
        st.enter_context(patch.object(pair, 'client_down', side_effect=lambda name: not b.up.get(name, False)))
        b.diagnostic = self.diagnostic
        b.recovery_ready = lambda identifier, settings: self.healthy(identifier)
        b.health = lambda identifier: self.healthy(identifier)
        dispatch = native.forward_dispatch   # test_boot_held's ifup fake (Stop-fenced)

        def forward(args, revision, timeout=5):
            if args[0] in ('uci', 'iptables-restore', '/usr/bin/rtp2.sh'):
                native.require_control_revision(revision)
                return b''
            if args[0] == 'lua':          # pair.configure_lease: the lease lands in the settings the backend reads
                native.require_control_revision(revision)
                script = Path(args[1]).read_text()
                for key in ('native_trial', 'native_until'):
                    found = re.search(r"'%s',(\"[^\"]*\")" % key, script)
                    if found:
                        b.data['settings'][key] = json.loads(found.group(1))
                return b''
            return dispatch(args, revision, timeout)
        st.enter_context(patch.object(native, 'forward_dispatch', side_effect=forward))
        ubus = native.command

        def command(args, timeout=5):
            if args[0] in ('uci', 'iptables-restore', '/usr/bin/rtp2.sh'):
                return b''
            return ubus(args, timeout=timeout)
        st.enter_context(patch.object(native, 'command', side_effect=command))
        st.enter_context(patch.object(agent, 'command', side_effect=lambda argv, *a, **k: json.dumps({'settings': b.data['settings']}).encode()))
        st.enter_context(patch.object(native.subprocess, 'Popen', side_effect=self.popen))
        st.enter_context(patch('speed_pause.gate', side_effect=self.gate))
        st.enter_context(patch('preparation_control.auto_blocker', return_value=None))
        st.enter_context(patch('preparation_control.auto_prepare', side_effect=self.auto_prepare))
        real_give_up = native.give_up

        def give_up(*a, **k):
            self.gave_up = True
            native.STOP = True             # one publish, then back (the alarm loop waits for the operator)
            return real_give_up(*a, **k)
        st.enter_context(patch.object(native, 'give_up', side_effect=give_up))
        self.install_write_hooks()
        b.data['settings'].update(failure_model='consecutive', native_trial='0' * 32, native_session_loss='1',
                                  terms_version=agent.TERMS_VERSION)
        # the scenario starts on a quiet router: no journal, no session, no intent, no marker, primary first
        for path in (native.JOURNAL, pair.paths()[1], self.dir / boot_resume.MARKER, pair.paths()[0], self.dir / 'pair-auto-control.json'):
            try:
                path.unlink()
            except OSError:
                pass
        self.gave_up = False
        self.reserve_lost = False
        self.in_pass = False
        self.dead = False
        self.prep = False
        self.fault = 0
        self.fault_fired = False
        self.kill_at = None
        self.writes = 0
        self.snaps = []
        self.trace = []
        self.handled = None
        self.booted = False
        self.current = 'boot'

    # ---------------------------------------------------------------------------------------------------- fakes
    def healthy(self, identifier):
        return self.b.health_of.get(identifier, True) is True

    def streak(self, samples, identifier, count, now, max_age, good, *a, **k):
        return self.healthy(identifier) is bool(good)

    def resolve_pair(self, status, settings, *a, **k):
        sel = self.b.selection
        return {'coordination': {'state': 'READY'}, 'source': dict(sel['source']), 'target': dict(sel['target'])}

    def exit_of(self, profile):
        return {self.source: '198.51.100.1', self.target: '203.0.113.5'}.get(profile['id'])

    def probe(self, profile):
        if self.healthy(profile.get('id')):
            return {'code': None, 'dns_ok': True, 'https_success': 2}
        return {'code': 'VPN-001', 'dns_ok': False, 'https_success': 0}

    def live_selection(self):
        b = self.b
        sel = dict(b.selection, order=b.current[:], hash=b.fingerprint)
        sel['vendor_identity'] = sel.get('vendor_identity') or 'e' * 64
        return sel

    def diagnostic(self):
        blockers = ['RESERVE-NOT-CONNECTED'] if self.reserve_lost else []
        return blockers, self.live_selection()

    def preflight(self, backend, settings):
        if self.prep:
            raise ValueError('PREP-TARGET-AUTOSTART')
        if self.b.kernel != self.b.current:
            raise ValueError('KERNEL-POLICY-UNVERIFIED')
        return self.live_selection()

    def auto_prepare(self, settings, revision):
        """preparation_control.auto_prepare on the abstract 'prep' flag (a GL edit re-enabled a stock autostart)."""
        if not self.prep:
            return {}
        try:
            mode = pair.intent().get('mode')
            phase = pair.read_state().get('phase')
        except (OSError, ValueError):
            return {'code': 'PREPARATION-STATE-UNVERIFIED'}
        if mode == 'on':
            return {'code': 'PREPARATION-STOP-AUTO-FIRST'}
        if phase not in (None, 'STOPPED', 'FAILED'):
            return {'code': 'PREPARATION-RECOVERY-REQUIRED'}
        self.prep = False
        return {'repaired': ['target-autostart']}

    def popen(self, args, *a, **k):
        if len(args) >= 3 and args[1:3] == [native.__file__, 'apply']:
            tx = args[3]

            process = MagicMock(pid=os.getpid(), returncode=0)

            def wait(timeout=None):
                # the apply child of native_switch.main: a refusal ends the child with its code in native-apply-result.json
                try:
                    native.child(tx)
                except (native.Refused, OSError, ValueError, subprocess.SubprocessError) as error:
                    code = str(error) if isinstance(error, native.Refused) else 'NATIVE-SYSTEM-001'
                    self.alive()
                    agent.atomic_json(native.RUNTIME / 'native-apply-result.json', {'tx': tx, 'code': code, 'time': time.time()})
                    process.returncode = 1
                    return 1
                return 0
            process.wait.side_effect = wait
            process.poll.return_value = 0
            return process
        process = MagicMock(pid=4242, returncode=0)
        process.communicate.return_value = (b'', b'')
        process.wait.return_value = 0
        process.poll.return_value = 0
        return process

    def install_write_hooks(self):
        """Every product write is a crash point (crash@N / power@N) and a fine-grained snapshot for the invariants."""
        b = self.b
        for name in ('guard', 'unguard', 'reorder', 'apply'):
            real = getattr(b, name)

            def hooked(*a, _real=real, _name=name, **k):
                self.alive()
                if _name == 'apply' and self.fault:
                    self.fault -= 1
                    self.fault_fired = True
                    raise subprocess.CalledProcessError(1, 'rtp2.sh')   # the vendor rebuild failed (busy)
                result = _real(*a, **k)
                self.wrote(_name)
                return result
            setattr(b, name, hooked)
        real_journal = native.journal_write

        def journal_write(value, *a, **k):
            self.alive()
            result = real_journal(value, *a, **k)
            self.wrote('journal')
            return result
        self.stack.enter_context(patch.object(native, 'journal_write', side_effect=journal_write))
        real_save = pair.save

        def save(state):
            self.alive()
            result = real_save(state)
            self.wrote('state')
            return result
        self.stack.enter_context(patch.object(pair, 'save', side_effect=save))
        real_atomic = agent.atomic_json

        def atomic(path, value, *a, **k):
            self.alive()
            result = real_atomic(path, value, *a, **k)
            if Path(path).name in ('pair-auto-control.json', 'native-stop.json', boot_resume.MARKER):
                self.wrote(Path(path).name)
            return result
        for module in (agent, auto_control, native):     # auto_control/native bound agent.atomic_json at import
            self.stack.enter_context(patch.object(module, 'atomic_json', side_effect=atomic))
        real_failure = native.record_attempt_failure

        def record_failure(*a, **k):
            self.alive()
            return real_failure(*a, **k)
        self.stack.enter_context(patch.object(native, 'record_attempt_failure', side_effect=record_failure))

    def alive(self):
        # after SIGKILL nothing more is written (BaseException handlers of the code under test included)
        if self.dead:
            raise Killed()

    def wrote(self, what):
        self.writes += 1
        self.snaps.append(self.observe())
        if self.kill_at is not None and self.in_pass and self.writes >= self.kill_at:
            self.kill_at = None
            self.dead = True
            raise Killed()

    # ---------------------------------------------------------------------------------------------------- abstract state
    def role(self, order, policy_hash, expected_hash, primary):
        # P is the order the session started on (a Start after an outside change adopts whatever order it finds), as in the model
        if policy_hash != expected_hash:
            return 'F'
        if list(order) == list(primary):
            return 'P'
        return 'R' if sorted(order) == sorted(primary) else 'F'

    def observe(self):
        b = self.b
        try:
            row = pair.intent()
        except (OSError, ValueError):
            row = {'mode': 'BAD'}
        try:
            state = pair.read_state()
        except (OSError, ValueError):
            state = {'phase': 'BAD'}
        try:
            journal = native.journal_read()
        except (native.Refused, OSError, ValueError):
            journal = {'phase': 'BAD'}
        try:
            revision = agent.read_json(self.ram / 'auto-control-revision.json', {}).get('revision')
        except (OSError, ValueError):
            revision = None
        on = row.get('mode') == 'on' and revision is not None and row.get('revision') == revision
        try:
            marker = boot_resume.wanted(self.dir)[0] is True
        except (OSError, ValueError):
            marker = False
        try:
            ledger = agent.read_json(self.ram / 'pair-readopt.json', {})
            events = [x for x in ledger.get('events', []) if 0 <= self.clock.wall - x < 900]
        except (OSError, ValueError, AttributeError):
            events = []
        expected = state.get('policy_hash') if state.get('policy_hash') else self.base_hash
        phase = journal.get('phase')
        return {
            'intent': 'on' if on else 'off',
            'fresh': bool(on and state.get('id') != row.get('id')),
            'marker': marker,
            'sess': state.get('phase') or 'NONE',
            'readopt_code': bool(state.get('phase') == 'HELD' and state.get('recovery_error') in pair.READOPT_CODES),
            'ran': bool(state.get('ran')),
            'ho': 'handover' in state,
            'kept': 'kept' in state,
            'jr': JOURNAL_PHASES.get(phase, 'BAD:' + str(phase)),
            'rtp': bool(journal.get('rtp_dispatched')),
            'fails': min(2, int(journal.get('rollback_failures', 0) or 0)),
            'fres': 'forward_resumed' in journal,
            'failed': bool(journal.get('failure_code')),
            'uci': self.role(b.current, b.fingerprint, expected, state.get('order') or self.base_order),
            'kern': self.role(b.kernel, b.fingerprint, expected, state.get('order') or self.base_order),
            'guard': {None: 'none', 'full': 'full', 'vpn-only': 'vpn'}.get(b.guarded, str(b.guarded)),
            'pUp': self.healthy(self.source),
            'rUp': self.healthy(self.target),
            'readopt': min(3, len(events)),
            'sc': '-' if 'server_change' not in state else state['server_change'].get('phase', '?'),
        }

    def record(self, event, end, **extra):
        row = {'event': event, 'end': end, 'obs': self.observe(), 'writes': self.snaps, 'n_writes': self.writes, 't': self.clock.wall}
        if self.fault_fired:
            row['fault'] = True
        row.update(extra)
        self.trace.append(row)
        self.snaps = []
        self.writes = 0
        self.fault_fired = False

    # ---------------------------------------------------------------------------------------------------- RAM loss
    def lose_process(self):
        """In-process state of the killed supervisor (module globals)."""
        self.dead = False
        pair.handover_log_reset()
        pair.outside_guard_reset()
        pair._skip_logged.clear()
        pair.LATE_ABORTS.clear()
        native.STOP = False

    def power_cut(self):
        import shutil
        shutil.rmtree(self.ram)
        self.ram.mkdir()
        for name in self.b.up:
            self.b.up[name] = False          # the prepared router starts no VPN client by itself
        self.b.guarded = None                # nft is RAM
        self.b.kernel = self.b.current[:]    # the kernel is rebuilt from UCI at the boot
        self.clock.wall += 60
        self.clock.mono = 40.0               # the monotonic clock starts again at the boot
        self.clock.boot = 0.0
        self.booted = False

    # ---------------------------------------------------------------------------------------------------- events
    def apply(self, event):
        b = self.b
        if event in ('start', 'stop'):
            self.clock.advance(1)             # an owner click is never in the same instant as the previous one
        if event == 'start':
            reply = auto_control.start(control_revision=auto_control.current_revision(), request_source='manual')
            return {'reply': (reply.get('blockers') or ['accepted' if reply.get('accepted') else '?'])[0]}
        if event == 'stop':
            try:
                reply = auto_control.stop(request_source='manual')
            except (OSError, ValueError) as error:
                return {'reply': 'error ' + type(error).__name__}
            return {'reply': 'already_requested' if reply.get('already_requested') else 'queued'}
        if event == 'resume':
            sleep = self.clock.sleep
            if not self.booted and self.clock.mono - self.clock.boot < boot_resume.BOOT_AGE:
                self.booted = True
                state = boot_resume.run(self.ram, self.dir, sleep=sleep, uptime=self.clock.mono - self.clock.boot,
                                        clock=self.clock.monotonic)
                handled = None
                try:
                    handled = agent.read_json(self.ram / boot_resume.STATE, {}).get('supervisor')
                except (OSError, ValueError):
                    pass
                self.handled = handled or self.handled
                return {'reply': str(state)}
            boot_resume.watch(self.ram, self.dir, sleep=sleep, clock=self.clock.monotonic, handled=self.handled, rounds=1)
            try:
                row = agent.read_json(self.ram / boot_resume.STATE, {})
                self.handled = row.get('supervisor') or self.handled
                return {'reply': row.get('state')}
            except (OSError, ValueError):
                return {}
        if event in ('p_down', 'p_up'):
            b.health_of[self.source] = event == 'p_up'
            return {}
        if event in ('r_down', 'r_up', 'r_lost'):
            b.health_of[self.target] = event == 'r_up'
            self.reserve_lost = event == 'r_lost' or (self.reserve_lost and event == 'r_down')
            return {}
        if event == 'gl_pol':                 # a foreign route policy (new rule identity) in UCI and the kernel
            b.fingerprint = hashlib.sha256((b.fingerprint + 'gl').encode()).hexdigest()
            self.prep = True
            return {}
        if event == 'gl_net':                 # the VPN clients were edited: another network identity
            self.identity = hashlib.sha256((self.identity + 'gl').encode()).hexdigest()
            self.prep = True
            return {}
        if event == 'busy':
            self.fault = 1
            return {}
        if event == 'wait':
            self.clock.advance(60)
            return {}
        if event == 'wait_long':
            self.clock.advance(700)
            return {}
        raise Hung('unknown event ' + event)   # a BaseException: a scenario typo is a driver error, never a supervisor death

    def gate(self, name):
        """speed_pause.gate: called at the top of every loop pass - the end of the previous serve-side event."""
        if self.current == 'boot':
            self.handled = boot_resume.token(self.ram)   # the monitor starts with the router: not a restart
        if self.kill_at is not None:      # crash@N / power@N: the pass made fewer writes, it was an ordinary pass
            self.kill_at = None
            self.current = 'tick'
            self.mid = None
        self.in_pass = False
        self.record(self.current, 'IDLE')
        while True:
            if not self.pending:
                raise ScenarioEnd()
            event = self.pending.pop(0)
            kind, _, at = event.partition('@')
            if kind == 'tick':
                self.current = 'tick'
                self.in_pass = True
                return False
            if kind in ('crash', 'power'):
                if at:
                    self.kill_at = int(at)
                    self.current = kind          # recorded when the write hook kills the pass (else as a tick)
                    self.mid = kind
                    self.in_pass = True
                    return False
                self.current = kind
                raise Killed()
            extra = self.apply(kind)
            self.record(kind, 'IDLE', **extra)

    def serve_once(self):
        native.STOP = False
        try:
            native.serve()
        except Killed:
            raise
        except ScenarioEnd:
            raise
        except Exception as error:          # the supervisor died: procd restarts it
            return 'DOWN', '%s: %s' % (type(error).__name__, error)
        return ('GIVEUP' if self.gave_up else 'DOWN'), None

    def run_scenario(self, events):
        self.pending = list(events)
        self.base_hash = self.b.fingerprint
        self.mid = None
        while True:
            try:
                end, error = self.serve_once()
                if self.kill_at is not None:      # crash@N / power@N not reached: the pass was an ordinary tick
                    self.kill_at = None
                    self.current = 'tick'
                extra = {'error': error} if error else {}
                self.record(self.current, end, **extra)
                if end == 'GIVEUP':
                    break
                self.lose_process()
                self.current = 'recover'
            except Killed:
                kind = self.current if self.current in ('crash', 'power') else 'crash'
                self.kill_at = None
                if kind == 'power':
                    self.power_cut()
                self.lose_process()
                self.record(kind, 'DOWN', mid=self.mid is not None)
                self.mid = None
                self.current = 'recover'
            except ScenarioEnd:
                break
        return self.trace


def run(scenarios, budget=60):
    import signal

    def hung(signum, frame):
        raise Hung('scenario over %d s' % budget)
    signal.signal(signal.SIGALRM, hung)
    out = []
    for scenario in scenarios:
        signal.alarm(budget)
        driver = Driver()
        started = REAL_TIME()
        try:
            driver.setUp()
            trace = driver.run_scenario(scenario['events'])
            out.append({'name': scenario['name'], 'runtime': 'python', 'steps': trace, 'seconds': round(REAL_TIME() - started, 2)})
        except BaseException as error:  # a driver bug is reported, not hidden
            out.append({'name': scenario['name'], 'runtime': 'python', 'steps': driver.trace, 'driver_error': traceback.format_exc()[-3000:]})
            if isinstance(error, KeyboardInterrupt):
                raise
        finally:
            signal.alarm(0)
            driver.doCleanups()
    return out


def main(argv):
    scenarios = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    traces = run(scenarios)
    Path(argv[2]).write_text(json.dumps(traces), encoding='utf-8')
    errors = sum(1 for t in traces if 'driver_error' in t)
    print('TRACE-DRIVER python: %d scenarios, %d steps, %d driver errors' % (len(traces), sum(len(t['steps']) for t in traces), errors))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
