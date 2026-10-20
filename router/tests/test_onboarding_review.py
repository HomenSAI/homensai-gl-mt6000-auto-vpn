"""Independent aggregate first-run boundary checks; no UCI, network or files written."""
import copy
from contextlib import ExitStack, contextmanager, nullcontext
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import configuration_guard
import setup_config as setup
from recovery_settings import DEFAULTS
import telegram_report


class OnboardingReview(unittest.TestCase):
    def arguments(self):
        return {
            'system': {'defer_pair': True, 'source': '', 'target': '', 'duration': 10,
                       'session_loss': False, 'servers': []},
            'monitor': {'interval': 30, 'checkpoint': 900, 'probe_limit': 16,
                        'planning_enabled': False},
            'recovery': dict(DEFAULTS),
            'speed': {'enabled': False, 'auto_new': False, 'budget_mib': 8,
                      'duration': 5, 'streams': 2, 'daily_mib': 128, 'busy_mbps': 2},
            'telegram': {'configure': False},
            'appearance': {'language': 'en', 'design': 'a', 'theme': 'system'},
        }

    def inventory(self, count=0):
        identifiers = ['wireguard:peer_1', 'openvpn:1_2'][:count]
        return {'profiles': [{'id': identifier, 'name': 'Profile '+str(index),
                              'protocol': identifier.split(':')[0]}
                             for index, identifier in enumerate(identifiers)],
                'servers': [], 'settings': {'native_enabled': False,
                                            'telegram_configured': False}}

    def rows(self, data):
        return [{'profile': profile['id'], 'name': profile['name'], 'channel': 'Main',
                 'priority': index+1, 'enabled': True}
                for index, profile in enumerate(data['profiles'])]

    def telegram(self, enabled=False, token='', chat=''):
        return {'configure': True, 'token': token, 'chat': chat, 'enabled': enabled,
                'interval': 60, 'schedule': 'interval', 'hour': 7,
                'weekly': True, 'monthly': True, 'items': 'servers,events'}

    @contextmanager
    def isolated(self, data=None, response=None, guard=None, token='', error=None):
        with ExitStack() as stack:
            stack.enter_context(patch.object(setup, 'control_lock', return_value=nullcontext()))
            stack.enter_context(patch.object(setup, 'inventory', return_value=data or self.inventory()))
            blocked = stack.enter_context(patch.object(configuration_guard, 'blocked',
                                                       return_value=guard))
            stack.enter_context(patch('rpc_throttle.allow', return_value=True))
            stack.enter_context(patch.object(telegram_report, 'option', return_value=token))
            writer = stack.enter_context(patch.object(setup.subprocess, 'run',
                return_value=response or SimpleNamespace(returncode=0, stdout=b'OK'),
                side_effect=error))
            yield writer, blocked

    def rejected(self, arguments, data=None):
        with self.isolated(data) as (writer, unused):
            with self.assertRaises(ValueError):
                setup.save(arguments, 'onboarding')
            writer.assert_not_called()

    def test_zero_profiles_can_finish_without_inventing_pair_or_starting_services(self):
        with self.isolated() as (writer, unused):
            answer = setup.save(self.arguments(), 'onboarding')
        self.assertIs(answer.get('saved'), True)
        self.assertEqual(writer.call_count, 1)
        self.assertEqual(writer.call_args.args[0],
                         ['/usr/bin/lua', '/usr/lib/homensai-vpn/setup_save.lua'])
        payload = json.loads(writer.call_args.kwargs['input'])
        self.assertEqual(payload['main']['onboarding_version'], '1')
        self.assertEqual(payload['main']['onboarding_complete'], '1')
        self.assertEqual(payload['main']['onboarding_pair_deferred'], '1')
        self.assertEqual(payload['servers'], [])
        for key in ('native_enabled', 'native_trial', 'native_ack', 'enabled',
                    'terms_version', 'terms_time', 'setup_complete', 'telegram_token'):
            self.assertNotIn(key, payload['main'])
        self.assertNotIn('delete', payload)

    def test_one_profile_metadata_can_be_saved_while_pair_is_deferred(self):
        arguments = self.arguments(); data = self.inventory(1)
        arguments['system']['servers'] = self.rows(data)
        with self.isolated(data) as (writer, unused):
            answer = setup.save(arguments, 'onboarding')
        self.assertIs(answer.get('saved'), True)
        payload = json.loads(writer.call_args.kwargs['input'])
        self.assertEqual(len(payload['servers']), 1)
        self.assertEqual(payload['servers'][0]['profile'], data['profiles'][0]['id'])
        self.assertEqual(payload['main']['onboarding_pair_deferred'], '1')

    def test_explicit_pair_and_marker_share_the_only_writer_payload(self):
        arguments = self.arguments(); data = self.inventory(2)
        arguments['system'].update(defer_pair=False,
            source=data['profiles'][0]['id'], target=data['profiles'][1]['id'],
            servers=self.rows(data))
        with self.isolated(data) as (writer, unused):
            answer = setup.save(arguments, 'onboarding')
        self.assertIs(answer.get('saved'), True)
        self.assertEqual(writer.call_count, 1)
        payload = json.loads(writer.call_args.kwargs['input'])
        self.assertEqual(payload['main']['plan_source'], arguments['system']['source'])
        self.assertEqual(payload['main']['plan_target'], arguments['system']['target'])
        self.assertEqual(payload['main']['onboarding_pair_deferred'], '0')
        self.assertEqual(payload['main']['onboarding_complete'], '1')
        self.assertEqual(len(payload['servers']), 2)

    def test_deferred_pair_cannot_hide_a_selection_or_enabled_planning(self):
        for section, field, value in [('system', 'source', 'wireguard:peer_1'),
                                      ('system', 'target', 'openvpn:1_2'),
                                      ('monitor', 'planning_enabled', True)]:
            with self.subTest(section=section, field=field):
                arguments = self.arguments(); arguments[section][field] = value
                self.rejected(arguments, self.inventory(2))

    def test_unknown_fields_cannot_inject_terms_auto_or_credentials(self):
        for branch in [None, 'system', 'monitor', 'recovery', 'speed', 'telegram', 'appearance']:
            for key in ('terms_version', 'native_enabled', 'onboarding_complete'):
                with self.subTest(branch=branch, key=key):
                    arguments = self.arguments()
                    (arguments if branch is None else arguments[branch])[key] = '1'
                    self.rejected(arguments)

    def test_malformed_nested_types_and_bool_numbers_never_reach_writer(self):
        for branch in ('system', 'monitor', 'recovery', 'speed', 'telegram', 'appearance'):
            for value in (None, [], True, 'malformed'):
                with self.subTest(branch=branch, value=value):
                    arguments = self.arguments(); arguments[branch] = value
                    self.rejected(arguments)
        for branch, key, value in [('system', 'duration', True),
                ('monitor', 'interval', True), ('recovery', 'failures', True),
                ('speed', 'budget_mib', True), ('telegram', 'configure', 0),
                ('system', 'defer_pair', 'true'), ('system', 'servers', {}),
                ('appearance', 'theme', 'custom'), ('speed', 'duration', float('inf'))]:
            with self.subTest(branch=branch, key=key):
                arguments = self.arguments(); arguments[branch][key] = value
                self.rejected(arguments)

    def test_unknown_removed_or_disabled_profile_cannot_be_saved_as_pair(self):
        data = self.inventory(2)
        for mode in ('unknown', 'missing', 'disabled'):
            arguments = self.arguments()
            arguments['system'].update(defer_pair=False,
                source=data['profiles'][0]['id'], target=data['profiles'][1]['id'],
                servers=self.rows(data))
            if mode == 'unknown': arguments['system']['target'] = 'wireguard:peer_999'
            if mode == 'missing': arguments['system']['servers'].pop()
            if mode == 'disabled': arguments['system']['servers'][1]['enabled'] = False
            with self.subTest(mode=mode): self.rejected(arguments, data)

    def test_disabled_blank_telegram_is_explicitly_supported_without_secret(self):
        arguments = self.arguments(); arguments['telegram'] = self.telegram()
        with self.isolated() as (writer, unused):
            answer = setup.save(arguments, 'onboarding')
        self.assertIs(answer.get('saved'), True)
        payload = json.loads(writer.call_args.kwargs['input'])
        self.assertEqual(payload['main']['telegram_enabled'], '0')
        self.assertNotIn('telegram_token', payload['main'])
        self.assertNotIn('delete', payload)

    def test_unconfigured_telegram_preserves_every_existing_option_by_omission(self):
        with self.isolated(token='123456789:'+'S'*35) as (writer, unused):
            answer = setup.save(self.arguments(), 'onboarding')
        self.assertIs(answer.get('saved'), True)
        payload = json.loads(writer.call_args.kwargs['input'])
        self.assertFalse(any(key.startswith('telegram_') for key in payload['main']))

    def test_blank_enabled_telegram_keeps_secret_and_never_returns_it(self):
        secret = '123456789:'+'PRIVATE_SECRET_SENTINEL_'*2
        arguments = self.arguments(); arguments['telegram'] = self.telegram(True, chat='12345')
        with self.isolated(token=secret) as (writer, unused):
            answer = setup.save(arguments, 'onboarding')
        self.assertIs(answer.get('saved'), True)
        self.assertNotIn(secret, json.dumps(answer))
        self.assertNotIn('telegram_token', json.loads(writer.call_args.kwargs['input'])['main'])

    def test_active_controller_refuses_before_writer_and_completion_marker(self):
        for code in ('CONFIG-STOP-AUTO-FIRST', 'CONFIG-RECOVERY-UNVERIFIED'):
            with self.isolated(guard=code) as (writer, blocked):
                answer = setup.save(self.arguments(), 'onboarding')
            self.assertIs(answer.get('saved'), False)
            self.assertEqual(answer.get('code'), code)
            blocked.assert_called_once(); writer.assert_not_called()

    def test_unconfirmed_partial_readback_or_timeout_never_claims_saved(self):
        for response in (SimpleNamespace(returncode=1, stdout=b'SETUP-SAVE-UNCONFIRMED'),
                         SimpleNamespace(returncode=0, stdout=b'OK PRIVATE_SECRET_SENTINEL'),
                         SimpleNamespace(returncode=1, stdout=b'PRIVATE_SECRET_SENTINEL')):
            with self.subTest(response=response):
                with self.isolated(response=response) as (writer, unused):
                    answer = setup.save(self.arguments(), 'onboarding')
                self.assertIs(answer.get('saved'), False)
                self.assertNotIn('PRIVATE_SECRET_SENTINEL', json.dumps(answer))
                self.assertEqual(writer.call_count, 1)
        with self.isolated(error=subprocess.TimeoutExpired('synthetic-writer', 10)) as (writer, unused):
            answer = setup.save(self.arguments(), 'onboarding')
        self.assertIs(answer.get('saved'), False)
        self.assertEqual(answer.get('code'), 'SETUP-SAVE-UNCONFIRMED')
        self.assertEqual(writer.call_count, 1)


if __name__ == '__main__':
    unittest.main()
