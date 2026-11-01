"""The last status_bridge.py fields in Lua (lua/page_controls.lua): manual_switch_control (pair_manual.controls /
manual_control.control_status, chosen like status_reply) and scan (scan_control.public) give exactly Python's
answer - fields, values, int/float types and codes - on the same files and inputs.

Each case is built in a temporary runtime/persist directory with the Python writers (pair_auto.save, atomic_json);
Python answers through status_bridge.compute / scan_control.public with the router-only parts replaced (the
policy helper, the journal, the kernel attestation, the fast-switch option, the clock); the Lua driver
(tests/lua/test_page_controls.lua --cases) gets the same file texts and the same replaced inputs."""
import contextlib
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'files/usr/lib/homensai-vpn'))
import agent, auto_control, native_switch as n, pair_auto as pair, pair_manual, scan_control, status_bridge  # noqa: E402,E401
from pair_policy import proof, transition  # noqa: E402

LUA = shutil.which('lua5.1') or shutil.which('lua')
NOW = 1792750000.5
SOURCE, TARGET = 'wireguard:peer_3', 'openvpn:1_2'
STATE_ID = 'a'*32
HASH = 'c'*64
SELECTION = {'source_rule': 's', 'target_rule': 't', 'direction': 'first', 'order': ['s', 't'],
             'source': {'id': SOURCE}, 'target': {'id': TARGET}}


class Backend:
    """native_switch.Linux for the display path: the policy helper and the live order are inputs."""
    def __init__(self, case):
        self.case, self.process_bindings = case, None

    def use_process_bindings(self, bindings):
        from process_policy import validate
        try:
            self.process_bindings = validate(bindings)
        except ValueError:
            raise n.Refused('POLICY-IDENTITY-CHANGED') from None

    def policy(self):
        if self.case.get('settings_error'):
            raise ValueError('POLICY-READ-FAILED')
        return {'settings': copy.deepcopy(self.case['settings']), 'sections': []}

    def order(self):
        return list(self.case['order'][0]), self.case['order'][1]

    def diagnostic(self):
        raise AssertionError('the display diagnostic comes from display-diagnostic.json in these cases')


class Case:
    def __init__(self, name, kind='controls'):
        self.name, self.kind = name, kind
        self.files = {}           # ('run'|'save', name) -> value (None: absent), written after the pair state
        self.state = None         # pair state data (None: no pair state file)
        self.intent = True        # True: 'on' for this state and revision, dict: as given, None: absent
        self.inputs = {'settings': {'pair_auto_mode': pair.MODE, 'interval': '10'}, 'order': [['s', 't'], HASH],
                       'journal': {}, 'kernel': {}, 'fast': False, 'settings_error': False}


def pair_case(name, general=False, **edits):
    case = Case(name)
    case.state = {'id': STATE_ID, 'phase': 'RUNNING', 'owned': ['wgclient1', 'ovpnclient1'],
                  'before_flags': {'wgclient1': '1', 'ovpnclient1': '1'}, 'network_identity': 'b'*64, 'protected': {},
                  'order': ['s', 't'], 'policy_hash': HASH}
    if general:
        case.state['policy_roles'] = proof(SELECTION)
    case.files[('run', 'native-status.json')] = {'state': 'OBSERVING', 'time': NOW-1, 'source': SOURCE, 'target': TARGET,
                                                 'mode': 'continuous-pair'}
    case.files[('run', 'status.json')] = {'time': NOW-1, 'profiles': [
        {'id': key, 'time': NOW-1, 'code': None, 'dns_ok': True, 'https_success': 2} for key in (SOURCE, TARGET)]}
    for key, value in edits.items():
        if key in case.inputs:
            case.inputs[key] = value
        elif key == 'state':
            case.state.update(value)
        elif key == 'intent':
            case.intent = value
        else:
            raise KeyError(key)
    return case


def manual_row(state='QUEUED', **extra):
    row = {'id': 'd'*32, 'pair': STATE_ID, 'revision': '{revision}', 'direction': 'reserve', 'state': state,
           'requested': NOW-1, 'updated': NOW-1, 'selection': {'tx': None}, 'code': None, 'request_source': 'manual'}
    row.update(extra)
    return row


def pair_cases():
    cases = [pair_case('non-general quiet')]
    def add(name, general=False, files=None, **edits):
        case = pair_case(name, general, **edits)
        for key, value in (files or {}).items():
            case.files[key] = value
        cases.append(case)
    run, save = 'run', 'save'
    add('held on reserve', journal={'phase': 'HELD-ON-RESERVE', 'tx': 'f'*32})
    add('committed', journal={'phase': 'COMMITTED', 'tx': 'f'*32})
    add('applying journal', journal={'phase': 'APPLYING'})
    add('pending request', files={(run, 'pair-manual-control.json'): manual_row()})
    add('claimed request', files={(run, 'pair-manual-control.json'): manual_row('CLAIMED')})
    add('completed request', files={(run, 'pair-manual-control.json'): manual_row('COMPLETED', code='MANUAL-ALREADY-SELECTED')})
    add('invalid request', files={(run, 'pair-manual-control.json'): {'state': 'X'}})
    add('stale supervisor', files={(run, 'native-status.json'): {'state': 'OBSERVING', 'time': NOW-31, 'source': SOURCE, 'target': TARGET}})
    add('supervisor in the future', files={(run, 'native-status.json'): {'state': 'OBSERVING', 'time': NOW+3, 'source': SOURCE, 'target': TARGET}})
    add('supervisor applying', files={(run, 'native-status.json'): {'state': 'APPLYING', 'time': NOW-1, 'source': SOURCE, 'target': TARGET}})
    add('no supervisor status', files={(run, 'native-status.json'): None})
    add('no monitor status', files={(run, 'status.json'): None})
    add('source unhealthy', files={(run, 'status.json'): {'profiles': [
        {'id': SOURCE, 'time': NOW-1, 'code': 'DNS-001', 'dns_ok': False, 'https_success': 0},
        {'id': TARGET, 'time': NOW-1, 'code': None, 'dns_ok': True, 'https_success': 3}]}})
    add('target one https', files={(run, 'status.json'): {'profiles': [
        {'id': SOURCE, 'time': NOW-1, 'code': None, 'dns_ok': True, 'https_success': 2},
        {'id': TARGET, 'time': NOW-1, 'code': None, 'dns_ok': True, 'https_success': 1}]}})
    add('target too old', files={(run, 'status.json'): {'profiles': [
        {'id': SOURCE, 'time': NOW-1, 'code': None, 'dns_ok': True, 'https_success': 2},
        {'id': TARGET, 'time': NOW-91, 'code': None, 'dns_ok': True, 'https_success': 2}]}})
    add('longer interval keeps it', settings={'pair_auto_mode': pair.MODE, 'interval': '40'}, files={(run, 'status.json'): {'profiles': [
        {'id': SOURCE, 'time': NOW-1, 'code': None, 'dns_ok': True, 'https_success': 2},
        {'id': TARGET, 'time': NOW-91, 'code': None, 'dns_ok': True, 'https_success': 2}]}})
    add('cooldown', files={(save, 'pair-auto-budget.json'): {'events': [NOW-10]}})
    add('cooldown over', files={(save, 'pair-auto-budget.json'): {'events': [NOW-100]}})
    add('rate limit', files={(save, 'pair-auto-budget.json'): {'events': [NOW-300, NOW-200, NOW-100]}})
    add('custom window limits', settings={'pair_auto_mode': pair.MODE, 'recovery_attempt_limit': '1', 'recovery_attempt_window': '5'},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-200]}})
    add('custom window lets go', settings={'pair_auto_mode': pair.MODE, 'recovery_attempt_limit': '1', 'recovery_attempt_window': '1'},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-200]}})
    add('custom cooldown', settings={'pair_auto_mode': pair.MODE, 'recovery_cooldown': '300'},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-200]}})
    add('broken ledger', files={(save, 'pair-auto-budget.json'): {'events': None}})
    add('ledger without events', files={(save, 'pair-auto-budget.json'): {}})
    add('Auto off', intent={'mode': 'off', 'id': STATE_ID, 'revision': '{revision}', 'time': NOW-5})
    add('no intent', intent=None)
    add('other revision', intent={'mode': 'on', 'id': STATE_ID, 'revision': 'e'*32, 'time': NOW-5})
    add('invalid intent', intent={'mode': 'maybe'})
    add('stopping', state={'phase': 'STOPPING'})
    add('manual hold target', state={'manual_hold': 'target', 'manual_hold_source': 'manual'})
    add('manual hold while busy', state={'manual_hold': 'source'}, files={(run, 'pair-manual-control.json'): manual_row()})
    add('process bindings', state={'process_bindings': {'wgclient1': 1, 'ovpnclient1': 2}})
    add('bad process bindings', state={'process_bindings': {}})
    add('policy helper fails', settings_error=True)
    # general pair sessions (policy roles): kernel proof, instant switch, transactions
    add('general verified source instant', True, kernel={'verified': True, 'role': 'source'}, fast=True)
    add('general verified target', True, kernel={'verified': True, 'role': 'target'})
    add('general unverified', True, kernel={'verified': False, 'code': 'KERNEL-POLICY-UNVERIFIED'})
    add('general no proof', True, kernel={})
    add('general repairable', True, kernel={'verified': False, 'repairable_missing': True})
    add('general other role name', True, kernel={'verified': True, 'role': 'other'})
    add('general applying', True, journal={'phase': 'APPLYING'}, kernel={'verified': True, 'role': 'source'})
    add('general order changed', True, order=[['t', 's'], HASH], kernel={'verified': True, 'role': 'source'})
    add('general hash changed', True, order=[['s', 't'], 'x'*64], kernel={'verified': True, 'role': 'source'})
    add('general rate limit on source', True, kernel={'verified': True, 'role': 'source'},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-300, NOW-200, NOW-100]}})
    add('general rate limit on target', True, kernel={'verified': True, 'role': 'target'},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-300, NOW-200, NOW-100]}})
    add('general rate limit unknown', True, kernel={'verified': False, 'repairable_missing': True},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-300, NOW-200, NOW-100]}})
    add('general rate limit instant', True, kernel={'verified': True, 'role': 'source'}, fast=True,
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-300, NOW-200, NOW-100]}})
    add('general cooldown on source', True, kernel={'verified': True, 'role': 'source'},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-10]}})
    add('general cooldown on target', True, kernel={'verified': True, 'role': 'target'},
        files={(save, 'pair-auto-budget.json'): {'events': [NOW-10]}})
    add('general hold source', True, kernel={'verified': True, 'role': 'source'}, state={'manual_hold': 'source', 'manual_hold_source': 'test'})
    switched = dict(phase='COMMITTED', tx='f'*32, source=SOURCE, target=TARGET, before=['s', 't'], after=['t', 's'], hash=HASH,
                    confirmed=NOW-50, pair_transition=transition(SELECTION, ['s', 't'], 'target'))
    add('general switched to reserve', True, journal=switched, order=[['t', 's'], HASH], kernel={'verified': True, 'role': 'target'})
    add('general switched, order back', True, journal=switched, order=[['s', 't'], HASH], kernel={'verified': True, 'role': 'target'})
    add('general switched, held', True, journal=dict(switched, phase='HELD-ON-RESERVE'), order=[['t', 's'], HASH],
        kernel={'verified': True, 'role': 'target'}, state={'manual_hold': 'target'})
    return cases


LEGACY_SELECTION = {'hash': '1'*64, 'source': {'id': SOURCE}, 'target': {'id': TARGET}, 'direction': 'first',
                    'settings_hash': 'd'*64, 'vendor_identity': 'e'*64}


def legacy_case(name, **edits):
    case = Case(name)
    case.intent = None
    case.inputs['settings'] = {'native_trial': 'trial-1', 'native_until': NOW+3600, 'native_session_loss': '1'}
    case.files[('run', 'native-status.json')] = {'state': 'DISABLED', 'time': NOW-1}
    case.files[('run', 'display-diagnostic.json')] = {'time': NOW-1, 'blockers': [], 'selection': copy.deepcopy(LEGACY_SELECTION)}
    case.files[('save', 'native-certificate.json')] = {'hash': '1'*64, 'source': SOURCE, 'target': TARGET, 'direction': 'first',
                                                       'until': NOW+7200, 'settings_hash': 'd'*64, 'vendor_identity': 'e'*64}
    case.files[('save', 'native-attempts.json')] = {'trial': 'trial-1', 'count': 0}
    for key, value in edits.items():
        if key in case.inputs:
            case.inputs[key] = value
        elif key == 'files':
            case.files.update(value)
        else:
            raise KeyError(key)
    return case


def legacy_record(**extra):
    row = {'schema': 1, 'state': 'QUEUED', 'direction': 'reserve', 'request_id': '9'*32, 'control_revision': '{revision}',
           'requested_at': NOW-2, 'updated_at': NOW-2, 'until': NOW+60, 'trial': 'trial-1', 'source_id': SOURCE,
           'target_id': TARGET, 'transaction_id': None, 'selection_hash': '1'*64, 'vendor_identity': 'e'*64,
           'settings_hash': 'd'*64, 'code': None}
    row.update(extra)
    return row


def legacy_cases():
    run, save = 'run', 'save'
    base = dict(LEGACY_SELECTION)
    diag = lambda **kw: {(run, 'display-diagnostic.json'): dict({'time': NOW-1, 'blockers': [], 'selection': base}, **kw)}
    settings = lambda **kw: dict({'native_trial': 'trial-1', 'native_until': NOW+3600, 'native_session_loss': '1'}, **kw)
    return [
        legacy_case('legacy ready'),
        legacy_case('legacy monitor only', settings=settings(monitor_only='1')),
        legacy_case('legacy monitor only invalid', settings=settings(monitor_only='x')),
        legacy_case('legacy no selection', files=diag(selection=None)),
        legacy_case('legacy diagnostic blockers', files=diag(blockers=['VENDOR-WORKER-BUSY', 'NFT-GUARD-UNAVAILABLE'])),
        legacy_case('legacy certificate for another hash', files={(save, 'native-certificate.json'): {
            'hash': '2'*64, 'source': SOURCE, 'target': TARGET, 'direction': 'first', 'until': NOW+7200,
            'settings_hash': 'd'*64, 'vendor_identity': 'e'*64}}),
        legacy_case('legacy certificate too short', files={(save, 'native-certificate.json'): {
            'hash': '1'*64, 'source': SOURCE, 'target': TARGET, 'direction': 'first', 'until': NOW+60,
            'settings_hash': 'd'*64, 'vendor_identity': 'e'*64}}),
        legacy_case('legacy certificate other scope', files={(save, 'native-certificate.json'): {
            'hash': '1'*64, 'source': SOURCE, 'target': TARGET, 'direction': 'first', 'until': NOW+7200,
            'settings_hash': 'd'*64, 'vendor_identity': 'e'*64, 'proof_scope': 'router-hosted-ipv4'}}),
        legacy_case('legacy no certificate', files={(save, 'native-certificate.json'): None}),
        legacy_case('legacy attempts used', files={(save, 'native-attempts.json'): {'trial': 'trial-1', 'count': 3}}),
        legacy_case('legacy attempts float', files={(save, 'native-attempts.json'): {'trial': 'trial-1', 'count': 1.0}}),
        legacy_case('legacy attempts other trial', files={(save, 'native-attempts.json'): {'trial': 'trial-0', 'count': 0}}),
        legacy_case('legacy session loss refused', settings=settings(native_session_loss='0')),
        legacy_case('legacy no deadline', settings=settings(native_until='')),
        legacy_case('legacy bad deadline', settings=settings(native_until='soon')),
        legacy_case('legacy deadline without zone', settings=settings(native_until='2026-11-01T10:00:00')),
        legacy_case('legacy deadline iso', settings=settings(native_until='2026-10-31T23:00:00+00:00')),
        legacy_case('legacy no trial', settings=settings(native_trial='')),
        legacy_case('legacy returned', files={**diag(), (save, 'native-transaction.json'): None}, journal={
            'phase': 'COMMITTED', 'tx': 'f'*32, 'source': SOURCE, 'target': TARGET}),
        legacy_case('legacy committed other pair', journal={'phase': 'COMMITTED', 'tx': 'f'*32, 'source': TARGET, 'target': SOURCE}),
        legacy_case('legacy pending request', files={(run, 'manual-control.json'): legacy_record()}),
        legacy_case('legacy pending other revision', files={(run, 'manual-control.json'): legacy_record(control_revision='8'*32)}),
        legacy_case('legacy completed request', files={(run, 'manual-control.json'): legacy_record(state='COMPLETED')}),
        legacy_case('legacy invalid request', files={(run, 'manual-control.json'): {'schema': 2}}),
        legacy_case('legacy supervisor stale', files={(run, 'native-status.json'): {'state': 'DISABLED', 'time': NOW-40}}),
        legacy_case('legacy supervisor missing', files={(run, 'native-status.json'): None}),
        legacy_case('legacy auto mode invalid', files={(run, 'auto-control.json'): {'mode': 'sometimes'}}),
        legacy_case('legacy auto enabled in config', settings=settings(native_enabled='1')),
        legacy_case('legacy auto started', files={(run, 'auto-control.json'): {
            'mode': 'on', 'trial': 'trial-1', 'until': NOW+3600, 'time': NOW-30}}),
        legacy_case('legacy stop latch', files={(save, 'native-stop.json'): {'requested': NOW-20, 'trial': 'trial-1'}}),
        legacy_case('legacy broken stop', files={(save, 'native-stop.json'): {'requested': 'x'}}),
        legacy_case('legacy stop revision failed', files={(save, 'native-stop.json'): {'requested': NOW-20, 'all_trials': True,
                                                                                         'control_revision_failed': True}}),
        legacy_case('legacy policy helper fails', settings_error=True),
        legacy_case('legacy pair mode supervisor', files={(run, 'native-status.json'): {
            'state': 'STOPPED', 'mode': 'continuous-pair', 'time': NOW-1}}),
        legacy_case('legacy older than a pair request', files={
            (run, 'pair-manual-control.json'): manual_row('COMPLETED', requested=NOW-5, updated=NOW-4),
            (run, 'manual-control.json'): legacy_record(state='COMPLETED', requested_at=NOW-9, updated_at=NOW-8)}),
        legacy_case('legacy newer than a pair request', files={
            (run, 'pair-manual-control.json'): manual_row('COMPLETED', requested=NOW-50, updated=NOW-49),
            (run, 'manual-control.json'): legacy_record(state='COMPLETED', requested_at=NOW-9, updated_at=NOW-8)}),
    ]


def scan_cases():
    rid = '7'*32
    rows = [None, {}, {'request_id': 'x'}, {'request_id': rid.upper(), 'state': 'QUEUED', 'requested_at': NOW},
            {'request_id': rid, 'state': 'WAITING', 'requested_at': NOW}, {'request_id': rid, 'state': 'QUEUED', 'requested_at': 'now'},
            {'request_id': rid, 'state': 'QUEUED', 'requested_at': True}, {'request_id': rid, 'state': 'QUEUED', 'requested_at': NOW-1},
            {'request_id': rid, 'state': 'QUEUED', 'requested_at': NOW-301}, {'request_id': rid, 'state': 'RUNNING', 'requested_at': NOW+2,
                                                                              'started_at': NOW+2},
            {'request_id': rid, 'state': 'RUNNING', 'requested_at': NOW-20, 'started_at': NOW-19.25},
            {'request_id': rid, 'state': 'COMPLETED', 'requested_at': NOW-900, 'started_at': NOW-899, 'finished_at': NOW-880,
             'measurement_request_id': rid, 'measured_at': NOW-881, 'checked': 2, 'failed': 1, 'other': 'x'},
            {'request_id': rid, 'state': 'FAILED', 'requested_at': NOW-60, 'finished_at': NOW-1, 'code': 'SCAN-MEASUREMENT-FAILED'},
            {'request_id': rid, 'state': 'COMPLETED', 'requested_at': 1792750000, 'code': None}]
    cases = []
    for index, row in enumerate(rows):
        case = Case('scan %d' % index, 'scan')
        case.files[('run', 'scan.state')] = row
        cases.append(case)
    return cases


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaPageControls(unittest.TestCase):
    def test_lua_suite(self):
        result = subprocess.run([LUA, str(HERE/'lua/test_page_controls.lua')], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        self.assertEqual(result.returncode, 0, (result.stdout+result.stderr).decode(errors='replace'))
        self.assertIn(b'tests OK', result.stdout)

    def build(self, case):
        """Writes the case, answers it with Python, returns (expected, lua case)."""
        with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
            root = Path(temp)
            runtime, persist = root/'run', root/'save'
            runtime.mkdir()
            persist.mkdir()
            for module in (agent, n, auto_control):
                for key, value in (('RUNTIME', runtime), ('PERSIST', persist)):
                    if hasattr(module, key):
                        stack.enter_context(patch.object(module, key, value))
            for key, name in (('STATE', 'native-status.json'), ('JOURNAL', 'native-transaction.json')):
                stack.enter_context(patch.object(n, key, (runtime if key == 'STATE' else persist)/name))
            revision = auto_control.current_revision()
            def fill(value):
                return json.loads(json.dumps(value).replace('{revision}', revision))
            if case.state is not None:
                pair.save(fill(dict(case.state, revision=revision)))
            if case.intent is True:
                agent.atomic_json(pair.paths()[0], {'mode': 'on', 'id': STATE_ID, 'revision': revision, 'time': NOW-5})
            elif case.intent is not None:
                agent.atomic_json(pair.paths()[0], fill(case.intent))
            for (where, name), value in case.files.items():
                if value is not None:
                    agent.atomic_json((runtime if where == 'run' else persist)/name, fill(value))
            inputs = fill(case.inputs)
            stack.enter_context(patch.object(n, 'Linux', side_effect=lambda: Backend(inputs)))
            stack.enter_context(patch.object(n, 'journal_read', side_effect=lambda: copy.deepcopy(inputs['journal'])))
            stack.enter_context(patch.object(n, 'fast_switch_enabled', return_value=inputs['fast']))
            stack.enter_context(patch.object(pair_manual, 'attested', side_effect=lambda *a, **kw: copy.deepcopy(inputs['kernel'])))
            stack.enter_context(patch('time.time', return_value=NOW))
            if case.kind == 'scan':
                expected = scan_control.public(runtime, agent.read_json, NOW)
            else:
                answer = status_bridge.compute(runtime, agent.read_json)
                self.assertIn('manual_switch_control', answer, case.name)
                expected = answer['manual_switch_control']
            files = {}
            for where, directory in (('run', runtime), ('save', persist)):
                for path in directory.iterdir():
                    if path.is_file() and path.suffix == '.json' or path.name == 'scan.state':
                        files[where+'/'+path.name] = path.read_text(encoding='utf8')
            lua_case = dict(inputs, kind=case.kind, files=files, now=NOW)
            return expected, lua_case

    def test_differential_with_python(self):
        cases = pair_cases()+legacy_cases()+scan_cases()
        built = [self.build(case) for case in cases]
        result = subprocess.run([LUA, str(HERE/'lua/test_page_controls.lua'), '--cases'],
                                input=json.dumps([lua for _, lua in built]).encode(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        answers = json.loads(result.stdout)
        self.assertEqual(len(answers), len(cases))
        allowed = legacy = 0
        for case, (expected, _), lua in zip(cases, built, answers):
            # exact text: the same keys, values and int/float types as json.dumps of the Python answer
            self.assertEqual(json.dumps(lua, sort_keys=True), json.dumps(expected, sort_keys=True), case.name)
            if isinstance(expected, dict) and any(isinstance(expected.get(k), dict) and expected[k].get('allowed') for k in ('primary', 'reserve', 'resume')):
                allowed += 1
            legacy += case.kind == 'controls' and 'mode' not in expected
        self.assertGreaterEqual(allowed, 10, 'the differential covers allowed buttons too')
        self.assertGreaterEqual(legacy, 20, 'and the legacy control_status')


if __name__ == '__main__':
    unittest.main()
