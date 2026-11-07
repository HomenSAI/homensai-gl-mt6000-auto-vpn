"""Comparison logic of the optional TLC cross-check (tools/formal/tla/tlc_check.py), tested with fake TLC output.

No docker, no java: everything here is pure text processing, so the always-on CI runs it.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
from unittest import mock

TLA = Path(__file__).resolve().parents[1] / 'formal' / 'tla'
spec = importlib.util.spec_from_file_location('tlc_check', TLA / 'tlc_check.py')
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)

# every profile of tools/formal/ci_check.py the spec re-states; the options that are not in the spec yet are named in gen_cfg.NOT_RESTATED
CI_CONFIGURATIONS = ['held-allfix', 'restart-allfix', 'faults-allfix', 'faults-power-allfix', 'server-allfix', 'glpower-net-allfix',
                     'rebuild-allfix', 'fast-allfix', 'fast-power-allfix', 'window-allfix', 'keys-allfix']
TLC_OK = '''TLC2 Version 2.20 of Day Month 20?? (rev: 1.7.4)
Parsing file /spec/Supervisor.tla
Starting... (2026-11-04 10:20:15)
<<"CENSUS-LEAK", "begin-instant">>
<<"CENSUS-LEAK", "begin-instant">>
<<"CENSUS-TRANS", "ROLLBACK-ONTO-DEAD-PRIMARY:crash">>
<<"CENSUS-STEP", "FRES:0:>RB:0:rec">>
<<"CENSUS-STEP", "IDLE:0:>BEGIN:0:">>
<<"CENSUS-STEP", "IDLE:0:>BEGIN:0:">>
Model checking completed. No error has been found.
  Estimates of the probability that TLC did not check all reachable states
11 states generated, 6 distinct states found, 0 states left on queue.
The depth of the complete state graph search is 4.
Finished in 01s at (2026-11-04 10:21:52)
'''
PY_OK = {'states': 6, 'transitions': 10, 'leak': {'LEAK:begin-instant': 2},
         'trans_edges': {'TRANSITION:ROLLBACK-ONTO-DEAD-PRIMARY:crash': 1}, 'inconsistent': 0,
         'steps': {'STEP:FRES:0:>RB:0:rec': 1, 'STEP:IDLE:0:>BEGIN:0:': 2}}


def parsed(text=TLC_OK):
    return tc.parse_tlc(text.splitlines())


class Parse(unittest.TestCase):
    def test_counts_and_census(self):
        t = parsed()
        self.assertEqual((t['generated'], t['distinct'], t['depth'], t['completed']), (11, 6, 4, True))
        self.assertEqual(t['census'], {'LEAK:begin-instant': 2, 'TRANSITION:ROLLBACK-ONTO-DEAD-PRIMARY:crash': 1,
                                       'STEP:FRES:0:>RB:0:rec': 1, 'STEP:IDLE:0:>BEGIN:0:': 2})
        self.assertEqual((t['violated'], t['errors']), ([], []))
        self.assertIn('1.7.4', t['version'])

    def test_thousands_separators(self):
        t = parsed('707,825 states generated, 123,144 distinct states found, 0 states left on queue.')
        self.assertEqual((t['generated'], t['distinct']), (707825, 123144))

    def test_inconsistent_census_line(self):
        self.assertEqual(parsed('<<"CENSUS-INV", "INCONSISTENT">>')['census'], {'INCONSISTENT': 1})

    def test_py_signatures(self):
        self.assertEqual(tc.py_signatures(dict(PY_OK, inconsistent=3)),
                         {'INCONSISTENT': 3, 'LEAK:begin-instant': 2, 'TRANSITION:ROLLBACK-ONTO-DEAD-PRIMARY:crash': 1,
                          'STEP:FRES:0:>RB:0:rec': 1, 'STEP:IDLE:0:>BEGIN:0:': 2})


class Compare(unittest.TestCase):
    def test_equal(self):
        self.assertEqual(tc.compare('held-allfix', parsed(), PY_OK), [])

    def test_transitions_are_generated_states_minus_the_initial_one(self):
        self.assertEqual(tc.compare('x', parsed(), dict(PY_OK, transitions=11))[0], 'x: transitions differ: TLC 10, model.py 11')

    def test_extra_state_in_model_py(self):
        problems = tc.compare('held-allfix', parsed(), dict(PY_OK, states=7))
        self.assertIn('held-allfix: states differ: TLC 6, model.py 7', problems)
        self.assertTrue(any('out of step' in p for p in problems))

    def test_signature_count_differs(self):
        py = dict(PY_OK, leak={'LEAK:begin-instant': 3})
        problems = tc.compare('x', parsed(), py)
        self.assertIn('x: violation signature LEAK:begin-instant differs: TLC 2, model.py 3', problems)

    def test_signature_only_on_one_side(self):
        self.assertTrue(any('LEAK:k3-held-on-reserve-without-guard differs: TLC 0, model.py 4' in p for p in
                            tc.compare('x', parsed(), dict(PY_OK, leak={'LEAK:begin-instant': 2, 'LEAK:k3-held-on-reserve-without-guard': 4}))))
        text = TLC_OK.replace('Model checking', '<<"CENSUS-LEAK", "other-running">>\nModel checking')
        self.assertTrue(any('LEAK:other-running differs: TLC 1, model.py 0' in p for p in tc.compare('x', parsed(text), PY_OK)))

    def test_inconsistent_only_in_model_py(self):
        self.assertTrue(any('INCONSISTENT differs: TLC 0, model.py 2' in p for p in tc.compare('x', parsed(), dict(PY_OK, inconsistent=2))))

    def test_an_edge_moved_to_another_reachable_state_is_red(self):
        # the same number of states, transitions and violations: only the pair of program counters tells (mutant spec-fres0)
        text = TLC_OK.replace('"FRES:0:>RB:0:rec"', '"FRES:0:>FRES:1:"')
        problems = tc.compare('x', parsed(text), PY_OK)
        self.assertIn('x: violation signature STEP:FRES:0:>FRES:1: differs: TLC 1, model.py 0', problems)
        self.assertIn('x: violation signature STEP:FRES:0:>RB:0:rec differs: TLC 0, model.py 1', problems)

    def test_a_census_without_steps_is_red(self):
        text = ''.join(line + '\n' for line in TLC_OK.splitlines() if 'CENSUS-STEP' not in line)
        problems = tc.compare('x', parsed(text), dict(PY_OK, steps={}))
        self.assertIn('x: TLC printed no CENSUS-STEP line: the step census is not running', problems)

    def test_tlc_invariant_violation_is_red(self):
        text = TLC_OK.replace('Model checking completed. No error has been found.',
                              'Error: Invariant TypeOK is violated.').replace('Starting', 'Starting')
        problems = tc.compare('x', parsed(text), PY_OK)
        self.assertTrue(any('violated invariant(s) TypeOK' in p for p in problems))

    def test_unfinished_run_is_red(self):
        text = TLC_OK.replace('Model checking completed. No error has been found.\n', '')
        self.assertTrue(any('did not finish' in p for p in tc.compare('x', parsed(text), PY_OK)))

    def test_missing_counts_is_red(self):
        problems = tc.compare('x', parsed('Model checking completed. No error has been found.'), PY_OK)
        self.assertTrue(any('counts are missing' in p for p in problems))

    def test_tlc_error_is_red(self):
        text = TLC_OK + 'Error: Deadlock reached.\n'
        self.assertTrue(any('TLC error: Error: Deadlock reached.' in p for p in tc.compare('x', parsed(text), PY_OK)))


class FixedSet(unittest.TestCase):
    def test_in_step(self):
        entries = tc.configurations()
        expected = json.loads((TLA.parent / 'expected.json').read_text(encoding='utf-8'))
        self.assertEqual(tc.check_fixed_set(expected['fixed'], entries), [])

    def test_a_new_fix_switch_without_a_spec_change_is_red(self):
        entries = [{'name': 'held-allfix', 'fixed': ['K1T', 'K2']}]
        self.assertTrue(tc.check_fixed_set(['K1T', 'K2', 'K12'], entries))


class Mirror(unittest.TestCase):
    def test_manifest_matches_the_files(self):
        self.assertEqual(tc.verify_manifest(), [], 'edited Supervisor.tla/gen_cfg.py/cfg: run tlc_check.py --update-manifest and the TLC check')

    def test_manifest_detects_an_edit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'cfg').mkdir()
            for name in tc.MIRROR_FILES:
                (root / name).write_bytes((TLA / name).read_bytes())
            (root / tc.MANIFEST).write_bytes((TLA / tc.MANIFEST).read_bytes())
            self.assertEqual(tc.verify_manifest(str(root)), [])
            (root / 'Supervisor.tla').write_text('edited', encoding='utf-8')
            problems = tc.verify_manifest(str(root))
            self.assertEqual(len(problems), 1)
            self.assertIn('Supervisor.tla changed', problems[0])
            (root / tc.MANIFEST).unlink()
            self.assertIn('is missing', tc.verify_manifest(str(root))[0])

    def test_manifest_ignores_checkout_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a', Path(d) / 'b'
            a.write_bytes(b'x\ny\n')
            b.write_bytes(b'x\r\ny\r\n')
            self.assertEqual(tc.file_sha256(str(a)), tc.file_sha256(str(b)))

    def test_generated_cfgs_equal_the_committed_ones(self):
        gen = tc.load_module('tla_gen_cfg_test', str(TLA / 'gen_cfg.py'))
        for e in gen.manifest_entries():
            self.assertEqual(gen.render(e['profile'], e['fixset']), (TLA / 'cfg' / (e['name'] + '.cfg')).read_bytes().decode().replace('\r\n', '\n'))

    def test_cfg_profiles_follow_the_ci_profiles_of_model_py(self):
        ci = tc.load_module('formal_ci_check_for_tla', str(TLA.parent / 'ci_check.py'))
        gen = tc.load_module('tla_gen_cfg_test2', str(TLA / 'gen_cfg.py'))
        for profile, args in gen.PY_ARGS.items():
            self.assertEqual(args, ci.PROFILES[profile], profile)

    def test_every_ci_profile_of_model_py_has_a_tlc_configuration(self):
        ci = tc.load_module('formal_ci_check_for_tla2', str(TLA.parent / 'ci_check.py'))
        gen = tc.load_module('tla_gen_cfg_test3', str(TLA / 'gen_cfg.py'))
        self.assertEqual(set(ci.PROFILES) - set(gen.PY_ARGS) - set(gen.NOT_RESTATED), set(),
                         'a new profile: re-state its option in Supervisor.tla and add it to gen_cfg.py PY_ARGS')
        self.assertEqual(set(gen.PY_ARGS) & set(gen.NOT_RESTATED), set(), 'a mirrored profile is still listed as not re-stated')
        for needed in ('fast', 'fast-power', 'rebuild', 'window', 'faults', 'faults-power', 'keys'):
            self.assertIn(needed, gen.PY_ARGS)
        self.assertNotIn('keys', gen.NOT_RESTATED)

    def test_the_constants_say_what_the_model_arguments_say(self):
        gen = tc.load_module('tla_gen_cfg_test4', str(TLA / 'gen_cfg.py'))
        switches = {'FastSwitch': '--fast-switch', 'Faults': '--faults', 'Rebuild': '--rebuild', 'Window': '--window', 'Server': '--server'}
        negative = {'GL': '--no-gl', 'Crash': '--no-crash', 'Power': '--no-power', 'Expire': '--no-expire'}
        for e in gen.manifest_entries():
            text = (TLA / 'cfg' / (e['name'] + '.cfg')).read_text(encoding='utf-8')
            for constant, flag in switches.items():
                self.assertIn('  %s = %s\n' % (constant, 'TRUE' if flag in e['py'] else 'FALSE'), text, e['name'])
            for constant, flag in negative.items():
                self.assertIn('  %s = %s\n' % (constant, 'FALSE' if flag in e['py'] else 'TRUE'), text, e['name'])
            pin = e['py'][e['py'].index('--key-pin') + 1] if '--key-pin' in e['py'] else 'off'
            self.assertIn('  KeyPin = "%s"\n' % pin, text, e['name'])

    def test_every_constant_of_the_spec_is_set_in_every_cfg(self):
        spec_text = (TLA / 'Supervisor.tla').read_text(encoding='utf-8')
        block = spec_text[spec_text.index('CONSTANTS'):spec_text.index('AllFixes ==')]
        constants = re.findall(r'^(?:CONSTANTS\s+|\s+)(\w+)\s*,?\s*\\\*', block, re.M)
        self.assertIn('FastSwitch', constants)
        for e in tc.configurations():
            text = (TLA / 'cfg' / (e['name'] + '.cfg')).read_text(encoding='utf-8')
            self.assertEqual(sorted(re.findall(r'^  (\w+) = ', text, re.M)), sorted(constants), e['name'])

    def test_the_fast_end_is_in_both_rules_of_the_spec(self):
        spec_text = (TLA / 'Supervisor.tla').read_text(encoding='utf-8')
        self.assertIn('(~y.pUp \\/ FastSwitch) /\\ y.rUp /\\ y.dwell', spec_text)   # tick: a live primary can be left
        self.assertIn('(IF ~x.pUp \\/ FastSwitch', spec_text)                         # FWD0: the recheck may have missed its recovery

    def test_the_key_gate_is_in_the_spec(self):
        spec_text = (TLA / 'Supervisor.tla').read_text(encoding='utf-8')
        for rule in ('kp |-> FALSE, kr |-> FALSE, kv |-> FALSE',                       # the fields
                     'ELSE IF Pin /\\ x.kr THEN Sup("FWD0 attempt refused',              # FWD0
                     '\\/ (Pin /\\ untouched /\\ ~forward /\\ x.kr)',                     # FRES0
                     '!.kv = FALSE',                                                   # TICK begin
                     'KeyOnCarrying(x) == IF x.uci = "R" THEN x.kr ELSE x.kp',           # owner: only the carrying channel gates Start
                     'Pin /\\ ((KeyPin = "blocker" /\\ (y.kp \\/ y.kr)) \\/ (~y.kv /\\ KeyOnCarrying(y)))',
                     '/\\ ~(Pin /\\ y.kp)', '/\\ ~(Pin /\\ y.kr)',                      # RESTORE, forward
                     '\\/ ActKey', 'OWNER accepts the server keys', 'MOVE-ONTO-UNACCEPTED-KEY',
                     'KeyPin = "directional" /\\ KeyOnCarrying(x)', 'BEGIN0 SERVER-KEY-UNACCEPTED',
                     '!.txrev = TRUE, !.kv = Pin, !.sup = IDLE',                         # handed-over Start retains the accepted proof
                     '"begin" \\in tags /\\ KeyOnCarrying(x)', 'BEGIN-WITH-UNACCEPTED-KEY',
                     '\\A e \\in sup : PrintT(<<"CENSUS-STEP"'):               # every configuration prints the pairs
            self.assertIn(rule, spec_text)

    def test_a_manual_configuration_is_outside_the_gate(self):
        gen = tc.load_module('tla_gen_cfg_test5', str(TLA / 'gen_cfg.py'))
        manual = [e['name'] for e in gen.manifest_entries() if not e['ci']]
        self.assertEqual(manual, ['keys-blocker-allfix'])
        self.assertIn('--key-pin', gen.MANUAL['keys-blocker'])
        self.assertIn('blocker', gen.MANUAL['keys-blocker'])

    def test_jar_pin_is_the_same_in_dockerfile_manifest_and_build_script(self):
        pin = tc.jar_sha256(str(TLA))
        self.assertRegex(pin, '^[0-9a-f]{64}$')
        self.assertIn('ARG JAR_SHA256=' + pin, (TLA / 'Dockerfile').read_text(encoding='utf-8'))
        self.assertIn('sha256sum -c', (TLA / 'Dockerfile').read_text(encoding='utf-8'))
        self.assertFalse(list(TLA.glob('*.jar')), 'the jar must not be vendored into git')

    def test_the_ci_configurations(self):
        names = [e['name'] for e in tc.configurations() if e['ci']]
        self.assertEqual(names, CI_CONFIGURATIONS)
        for e in tc.configurations():
            text = (TLA / 'cfg' / (e['name'] + '.cfg')).read_text(encoding='utf-8')
            self.assertEqual(re.findall(r'^INVARIANT (\w+)$', text, re.M), ['TypeOK', 'Census'])


class Census(unittest.TestCase):
    """py_census.py must really hand the options of a profile to model.py: without it TLC would be compared with the wrong graph."""
    TINY = ['--no-gl', '--no-crash', '--no-power', '--no-expire', '--variant', 'fix', '--fixed', 'K1T,K2,K3,K4,K5,K9,K11,K12']

    def census(self, *extra):
        c = tc.load_module('tla_py_census_test', str(TLA / 'py_census.py'))
        return c.census(c.model_cfg(self.TINY + list(extra)))

    def test_every_option_of_the_configurations_reaches_the_model(self):
        c = tc.load_module('tla_py_census_test2', str(TLA / 'py_census.py'))
        for e in tc.configurations():
            cfg = c.model_cfg(e['py'])
            for field, flag in (('fast_switch', '--fast-switch'), ('rebuild', '--rebuild'), ('window', '--window'),
                                ('faults', '--faults'), ('server', '--server')):
                self.assertEqual(getattr(cfg, field), flag in e['py'], (e['name'], field))
            self.assertEqual(cfg.key_pin, e['py'][e['py'].index('--key-pin') + 1] if '--key-pin' in e['py'] else None)

    def test_the_step_census_names_the_program_counters(self):
        c = self.census('--fast-switch')
        self.assertIn('STEP:IDLE:0:>BEGIN:0:', c['steps'])
        self.assertTrue(all(re.fullmatch(r'STEP:\w+:\d+:[\w-]*>\w+:\d+:[\w-]*', key) for key in c['steps']), c['steps'])
        self.assertLess(sum(c['steps'].values()), c['transitions'])    # the supervisor's edges, not the environment's

    def test_the_fast_end_changes_the_graph(self):
        self.assertGreater(self.census('--fast-switch')['transitions'], self.census()['transitions'])

    def test_the_key_gate_changes_the_graph_and_the_blocker_is_another_one(self):
        base = self.census()
        directional, blocker = self.census('--key-pin', 'directional'), self.census('--key-pin', 'blocker')
        self.assertGreater(directional['states'], base['states'])
        self.assertNotEqual((directional['states'], directional['transitions']), (blocker['states'], blocker['transitions']))

    def test_a_rebuild_and_faults_add_states(self):
        base = self.census()
        self.assertGreater(self.census('--rebuild')['states'], base['states'])
        self.assertGreater(self.census('--faults')['states'], base['states'])


class Schedule(unittest.TestCase):
    """The configurations run a few at a time on a shared machine, under one limit."""

    class FakeJob:
        running, peak, started, killed = 0, 0, 0, 0
        seconds_each = 0.02
        lock = threading.Lock()

        def __init__(self, argv, consume, container=None):
            self.consume, self.done_at, self.result, self.error, self.returncode, self.seconds = consume, None, None, None, 0, 0.0

        def start(self):
            cls = type(self)
            with cls.lock:
                cls.started += 1
                cls.running += 1
                cls.peak = max(cls.peak, cls.running)
            self.done_at = time.time() + cls.seconds_each
            self.closed = False

        def is_alive(self):
            if not self.closed and time.time() >= self.done_at:
                self.closed = True
                with type(self).lock:
                    type(self).running -= 1
            return not self.closed

        def join(self, timeout=None):
            pass

        def kill(self):
            type(self).killed += 1
            self.done_at = 0

    def run_with(self, seconds_each=0.02, timeout=60, jobs=2):
        job = type('Job', (self.FakeJob,), dict(running=0, peak=0, started=0, killed=0, seconds_each=seconds_each))
        with mock.patch.object(tc, 'Job', job), mock.patch.object(tc, 'image_state', return_value=('ok', tc.jar_sha256(str(TLA)))), \
                mock.patch.object(tc, 'compare', return_value=[]):
            return tc.run_check(str(TLA.parents[2]), 'img', '', timeout, 3, None, jobs), job

    def test_one_configuration_at_a_time(self):
        result, job = self.run_with(jobs=1)
        self.assertEqual(job.started, 2 * len(CI_CONFIGURATIONS))   # a TLC container and a model.py process each
        self.assertEqual(job.peak, 2)
        self.assertNotIn('time limit', ' '.join(result['problems']))

    def test_the_default_is_two_configurations(self):
        self.assertEqual(self.run_with()[1].peak, 4)

    def test_the_limit_stops_what_runs_and_starts_nothing_more(self):
        result, job = self.run_with(seconds_each=30, timeout=0, jobs=2)
        self.assertEqual((result['status'], result['reason']), ('FAIL', 'timeout'))
        self.assertEqual(job.killed, 4)
        self.assertEqual(job.started, 4)


class Skipped(unittest.TestCase):
    def source(self):
        return str(TLA.parents[2])

    def test_missing_image_is_skipped_not_failed(self):
        fake = mock.Mock(returncode=1, stdout='', stderr='Error response from daemon: No such image: homensai-tlc:local')
        with mock.patch.object(tc, 'docker', return_value=fake):
            r = tc.run_check(self.source(), 'homensai-tlc:local', '', 600, 3)
        self.assertEqual(r['status'], 'SKIPPED')
        self.assertIn('scripts/build-tlc-image.ps1', r['reason'])
        self.assertEqual(r['configs'], {})

    def test_missing_docker_is_skipped(self):
        with mock.patch.object(tc, 'docker', side_effect=FileNotFoundError):
            r = tc.run_check(self.source(), 'homensai-tlc:local', '', 600, 3)
        self.assertEqual((r['status'], r['reason']), ('SKIPPED', 'docker is not installed'))

    def test_unusable_daemon_is_skipped(self):
        fake = mock.Mock(returncode=1, stdout='', stderr='error during connect: the daemon is not running')
        with mock.patch.object(tc, 'docker', return_value=fake):
            self.assertEqual(tc.run_check(self.source(), 'x', '', 600, 3)['status'], 'SKIPPED')

    def test_image_with_another_jar_fails(self):
        fake = mock.Mock(returncode=0, stdout='0' * 64 + '\n', stderr='')
        with mock.patch.object(tc, 'docker', return_value=fake):
            r = tc.run_check(self.source(), 'homensai-tlc:local', '', 600, 3)
        self.assertEqual(r['status'], 'FAIL')
        self.assertIn('rebuild', r['problems'][0])

    def test_main_exit_codes(self):
        skipped = {'status': 'SKIPPED', 'reason': 'no image', 'configs': {}, 'problems': []}
        quiet = contextlib.redirect_stdout(io.StringIO())
        with quiet, mock.patch.object(tc, 'run_check', return_value=skipped):
            self.assertEqual(tc.main([]), 0)
        with quiet, mock.patch.object(tc, 'run_check', return_value=dict(skipped, status='FAIL', problems=['x'])):
            self.assertEqual(tc.main([]), 1)
        with quiet, mock.patch.object(tc, 'run_check', return_value=dict(skipped, status='PASS')):
            self.assertEqual(tc.main([]), 0)


class Argv(unittest.TestCase):
    def test_tlc_container_is_isolated_and_read_only(self):
        argv = tc.tlc_argv('homensai-tlc:local', '/src/tools/formal/tla', 'name', 'held-allfix', 3)
        for flag in ('--network=none', '--read-only', '--cap-drop=ALL', '--pull=never', '--user=65534:65534'):
            self.assertIn(flag, argv)
        self.assertIn('type=bind,source=/src/tools/formal/tla,target=/spec,readonly', argv)
        self.assertIn('/spec/cfg/held-allfix.cfg', argv)


if __name__ == '__main__':
    unittest.main()
