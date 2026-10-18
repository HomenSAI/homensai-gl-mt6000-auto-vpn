import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import telegram_items as items
import telegram_report as report
import report_calendar
import setup_config


def status(now):
    return {'profiles': [{'name': 'srv-a', 'protocol': 'openvpn', 'interface': 'vpn1', 'rtt_ms': 40}],
            'events': [{'time': now-10, 'profile': 'srv-a', 'code': 'DNS-001'}],
            'accounting': {'months': {time.strftime('%Y-%m', time.localtime(now)): {'rx': 5e8, 'tx': 5e8}}, 'gaps': 2},
            'native_failover': {'state': 'OBSERVING', 'alarm': 'ROLLBACK-GIVEN-UP'}, 'native_history': {}}


class TelegramItemTests(unittest.TestCase):
    def test_parse_and_encode(self):
        self.assertEqual(items.parse(None), items.ITEMS)
        self.assertEqual(items.parse(''), items.ITEMS)
        self.assertEqual(items.parse('none'), ())
        self.assertEqual(items.parse('events,servers,bogus'), ('servers', 'events'))
        self.assertEqual(items.encode('events,servers'), 'servers,events')
        self.assertEqual(items.encode('none'), 'none')
        for bad in ('', 'servers,servers', 'x', 'servers,;rm', 5, 'a'*300):
            with self.assertRaises(ValueError):items.encode(bad)

    def test_presets_are_known_items(self):
        for preset in items.PRESETS.values():self.assertTrue(set(preset) <= set(items.ITEMS))
        self.assertLess(len(items.PRESETS['minimum']), len(items.PRESETS['standard']))
        self.assertLessEqual(len(items.PRESETS['standard']), len(items.PRESETS['maximum']))

    def test_interval_report_contains_only_chosen_sections(self):
        now = time.time()
        full = report.format_report(status(now), 60, now)
        self.assertIn('srv-a', full);self.assertIn('State changes', full);self.assertIn('VPN traffic', full);self.assertIn('Observation gaps', full)
        small = report.format_report(status(now), 60, now, ('servers',))
        self.assertIn('srv-a', small)
        for gone in ('State changes', 'VPN traffic', 'Observation gaps', 'Native controller', 'Controller events'):self.assertNotIn(gone, small)
        nothing = report.format_report(status(now), 60, now, ())
        self.assertNotIn('srv-a', nothing);self.assertIn('Report interval', nothing)

    def test_alarm_is_never_optional(self):
        now = time.time()
        self.assertIn('ALARM: ROLLBACK-GIVEN-UP', report.format_report(status(now), 60, now, ()))

    def test_period_report_respects_choice(self):
        now = time.time();job = {'kind': 'daily', 'key': 'daily:x', 'start': now-86400, 'end': now}
        full = report_calendar.format_period(status(now), job, now)
        self.assertIn('WAN traffic', full);self.assertIn('Sampling discontinuities', full)
        small = report_calendar.format_period(status(now), job, now, ('gaps',))
        self.assertNotIn('WAN traffic', small);self.assertIn('Sampling discontinuities', small)
        none = report_calendar.format_period(status(now), job, now, ())
        self.assertNotIn('Sampling discontinuities', none);self.assertIn('Report id', none)

    def test_setup_payload_validates_items(self):
        base = {'token': '', 'chat': '@example_channel', 'enabled': True, 'interval': 60}
        self.assertEqual(setup_config.telegram_payload(dict(base, items='events,servers'))['main']['telegram_items'], 'servers,events')
        self.assertEqual(setup_config.telegram_payload(dict(base, items='none'))['main']['telegram_items'], 'none')
        self.assertNotIn('telegram_items', setup_config.telegram_payload(base)['main'])
        with self.assertRaises(ValueError):setup_config.telegram_payload(dict(base, items='servers,drop'))


if __name__ == '__main__':
    unittest.main()
