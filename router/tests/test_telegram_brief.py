import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'files/usr/lib/homensai-vpn'))
from telegram_brief import channel_reliability
from telegram_report import format_report
from report_calendar import format_period


def sample_status(now):
    event = {'time': now-10, 'sequence': 3, 'attempt_id': 1, 'state': 'COMMITTED', 'transition_completed': True,
             'transition_outcome': 'committed', 'route_changed': True, 'destination_role': 'target'}
    return {'native_failover': {'alarm': 'ROLLBACK-GIVEN-UP', 'source': 'p', 'target': 'q'},
            'accounting': {'reliability': {'events': [{'kind': 'FAILURE', 'time': now-10, 'code': 'DNS-001'}]*2 +
                          [{'kind': 'RECOVERY', 'time': now-9, 'code': 'VPN-001'}, {'kind': 'FAILURE', 'time': now, 'code': 'VPN-003'}]}},
            'native_history': {'events': [event, dict(event, sequence=4), dict(event, attempt_id=2, trial=True),
                              dict(event, attempt_id=3, activation_reapply=True), dict(event, attempt_id=4, route_changed=False),
                              {'time': now-1, 'state': 'BLOCKED', 'codes': ['AUTH-001', 'AUTH-001', 'ROLLBACK-GIVEN-UP']}]}}


class BriefTests(unittest.TestCase):
    def test_errors_once_switches_actual_alarm_always(self):
        now = 1761825600
        text = format_report(sample_status(now), 60, now, ('brief',))
        self.assertIn('DNS-001 ×2', text)
        self.assertEqual(text.count('DNS-001'), 1)
        self.assertEqual(text.count('AUTH-001'), 1)
        self.assertEqual(text.count('ROLLBACK-GIVEN-UP'), 1)
        self.assertNotIn('VPN-001', text)
        self.assertNotIn('VPN-003', text)
        self.assertIn('Переключения: 1', text)
        restored=sample_status(now)
        event=restored['native_history']['events'][0]
        restored['native_history']['events'] += [dict(event, attempt_id=8, transition_outcome='restored', destination_role='source'), dict(event, attempt_id=9, transition_outcome='refused'), dict(event, attempt_id=10, time=now), dict(event, attempt_id=11, time=now-3601)]
        self.assertIn('Переключения: 2', format_report(restored, 60, now, ('brief',)))
        self.assertIn('Надёжность сейчас, 5 мин: основной: нет данных; резервный: нет данных', text)
        self.assertIn('Авария: нет', format_report({}, 60, now, ('brief',)))
        self.assertIn('monitoring', format_report({}, 60, now))
        self.assertNotIn('кратко', format_report({}, 60, now))

    def test_period_boundaries_and_unknown_history(self):
        now = 1761825600
        data = sample_status(now)
        for kind in ('daily', 'weekly', 'monthly'):
            text = format_period(data, {'kind': kind, 'key': kind+':x', 'start': now-86400, 'end': now}, now, ('brief',))
            self.assertIn('Отчёт: '+kind+':x', text)
            self.assertIn('DNS-001 ×2', text)
            self.assertNotIn('VPN-003', text)
        data['native_history']['error'] = 'broken'
        text = format_report(data, 60, now, ('brief',))
        self.assertIn('HISTORY-001', text)
        self.assertIn('Переключения: нет данных', text)

    def test_large_error_detail_preserves_mandatory_lines(self):
        now = 1761825600
        data = sample_status(now)
        data['accounting']['reliability']['events'] = [{'kind': 'FAILURE', 'time': now-1, 'code': 'ERROR-%04d'%i} for i in range(600)]
        text = format_report(data, 60, now, ('brief',))
        self.assertIn('Авария: ROLLBACK-GIVEN-UP', text)
        self.assertIn('Переключения:', text)
        self.assertIn('Надёжность сейчас, 5 мин:', text)
        self.assertLess(len(text.encode('utf-16-le')), 8000)

    @unittest.skipUnless(shutil.which('node'), 'node runtime required to compare shipped UI source')
    def test_channel_percent_matches_actual_page_population(self):
        fixtures = json.loads((ROOT/'tests/fixtures/telegram_brief.json').read_text())
        script = "const fs=require('fs'),vm=require('vm');let c={};vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);let cases=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(cases.map(f=>c.channelReliability({id:f.id},f.status,f.now))))"
        ui = json.loads(subprocess.check_output(['node', '-e', script, str(ROOT/'channel_guidance.inc.js')], input=json.dumps(fixtures).encode()))
        for fixture, expected in zip(fixtures, ui):
            actual = channel_reliability(fixture['status'], fixture['id'], fixture['now'])
            if expected:
                self.assertEqual(actual, {k: expected[k] for k in ('n', 'bad', 'loss')}, fixture['name'])
            else:
                self.assertIsNone(actual, fixture['name'])
        self.assertEqual(ui[0]['loss'], 0)
        self.assertIsNone(ui[1])
        self.assertEqual(ui[2]['n'], 6)
        self.assertIsNone(ui[3])
        self.assertAlmostEqual(ui[4]['loss'], 100/3)
        self.assertIsNone(ui[5])


if __name__ == '__main__':
    unittest.main()
