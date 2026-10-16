import sys
from pathlib import Path
import unittest
import tempfile
import agent
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import telegram_report as report


class TelegramTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        patcher=patch.object(agent,'RUNTIME',Path(self.tmp.name));patcher.start();self.addCleanup(patcher.stop)

    def test_native_history_report_is_scoped_and_does_not_expose_private_fields(self):
        now=report.time.time();month=report.datetime.now().strftime('%Y-%m')
        status={'native_failover':{'state':'COMMITTED','tx':'PRIVATE_SENTINEL','expected_exit':'EXIT_SENTINEL','acceleration':{'hook_log':'KERNEL_SENTINEL'}},
                'native_history':{'events':[{'time':now,'state':'COMMITTED','codes':['CLIENT-CONFIRMED'],'trial':False,'token':'TOKEN_SENTINEL'}],
                                  'months':{month:{'attempts':2,'trials_passed':1,'committed':1,'rollbacks':1}}}}
        text=report.format_report(status,60)
        self.assertIn('COMMITTED',text);self.assertIn('partial month',text)
        self.assertNotIn('Automatic switching disabled',text)
        for secret in ('PRIVATE_SENTINEL','EXIT_SENTINEL','KERNEL_SENTINEL','TOKEN_SENTINEL'):self.assertNotIn(secret,text)

    def test_corrupt_native_history_is_reported_without_invented_counts(self):
        text=report.format_report({'native_failover':{'state':'bad value'},'native_history':{'error':'HISTORY-001'}},60)
        self.assertIn('HISTORY-001',text);self.assertIn('UNKNOWN',text)
        self.assertNotIn('automatic commits',text)

    def test_disabled_never_sends(self):
        with patch.object(report,'config_snapshot',return_value={'telegram_enabled':'0'}), patch.object(report.urllib.request, 'urlopen') as send:
            status, _, sent = report.deliver({}, {}, 10000)
            self.assertFalse(sent)
            self.assertFalse(status['enabled'])
            send.assert_not_called()

    def test_hourly_gate(self):
        options = {'telegram_enabled':'1','telegram_interval':'60','telegram_chat':'123','telegram_token':'123:synthetic'}
        with patch.object(report,'config_snapshot',return_value=options), patch.object(report.urllib.request, 'urlopen') as send:
            status, _, sent = report.deliver({}, {'sent':10000}, 11000)
            self.assertFalse(sent)
            self.assertEqual(status['interval_minutes'], 60)
            send.assert_not_called()

    def test_error_does_not_expose_secret(self):
        options = {'telegram_enabled':'1','telegram_interval':'60','telegram_chat':'123','telegram_token':'123:synthetic'}
        with patch.object(report,'config_snapshot',return_value=options), patch.object(report.urllib.request, 'urlopen', side_effect=ValueError('123:synthetic')):
            status, _, sent = report.deliver({}, {}, 10000)
            self.assertFalse(sent)
            self.assertNotIn('synthetic', str(status))

    def test_report_distinguishes_missing_data(self):
        self.assertIn('no accumulated', report.format_report({}, 60))
