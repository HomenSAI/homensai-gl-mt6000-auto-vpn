import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import telegram_report as report


class TelegramTests(unittest.TestCase):
    def test_disabled_never_sends(self):
        with patch.object(report, 'option', return_value='0'), patch.object(report.urllib.request, 'urlopen') as send:
            status, _, sent = report.deliver({}, {}, 10000)
            self.assertFalse(sent)
            self.assertFalse(status['enabled'])
            send.assert_not_called()

    def test_hourly_gate(self):
        options = {'telegram_enabled':'1','telegram_interval':'60','telegram_chat':'123','telegram_token':'123:synthetic'}
        with patch.object(report, 'option', side_effect=lambda key:options[key]), patch.object(report.urllib.request, 'urlopen') as send:
            status, _, sent = report.deliver({}, {'sent':10000}, 11000)
            self.assertFalse(sent)
            self.assertEqual(status['interval_minutes'], 60)
            send.assert_not_called()

    def test_error_does_not_expose_secret(self):
        options = {'telegram_enabled':'1','telegram_interval':'60','telegram_chat':'123','telegram_token':'123:synthetic'}
        with patch.object(report, 'option', side_effect=lambda key:options[key]), patch.object(report.urllib.request, 'urlopen', side_effect=ValueError('123:synthetic')):
            status, _, sent = report.deliver({}, {}, 10000)
            self.assertFalse(sent)
            self.assertNotIn('synthetic', str(status))

    def test_report_distinguishes_missing_data(self):
        self.assertIn('нет накопленных', report.format_report({}, 60))
