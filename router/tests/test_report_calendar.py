from datetime import datetime
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from report_calendar import prepare, limited_text, format_period
import telegram_state
from agent import atomic_json


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.old=os.environ.get('TZ');os.environ['TZ']='CET-1CEST,M3.5.0,M10.5.0/3';time.tzset()
    def tearDown(self):
        if self.old is None:os.environ.pop('TZ',None)
        else:os.environ['TZ']=self.old
        time.tzset()
    def stamp(self,text):return datetime.strptime(text,'%Y-%m-%d %H:%M').timestamp()

    def daily(self,text,confirmed):
        now=self.stamp(text)
        options={'telegram_schedule':'daily','telegram_hour':'7','telegram_weekly':'0','telegram_monthly':'0'}
        saved={'calendar_started':{'daily':self.stamp('2026-01-01 00:00')},'period_keys':{'daily':confirmed}}
        return prepare(options,saved,now)[0]

    def test_daily_slot_is_exactly_seven_local(self):
        self.assertEqual(self.daily('2026-10-15 06:59','daily:2026-10-13'),[])
        job=self.daily('2026-10-15 07:00','daily:2026-10-13')[0]
        self.assertEqual(job['key'],'daily:2026-10-14')

    def test_dst_spring_and_fall_do_not_shift_seven(self):
        for day,prior in [('2026-03-29','2026-03-27'),('2026-10-25','2026-10-23')]:
            self.assertEqual(self.daily(day+' 06:59','daily:'+prior),[])
            self.assertEqual(len(self.daily(day+' 07:00','daily:'+prior)),1)

    def test_calendar_day_can_have_twenty_three_or_twenty_five_hours(self):
        for day,prior,hours in [('2026-03-30','2026-03-28',23),('2026-10-26','2026-10-24',25)]:
            job=self.daily(day+' 07:00','daily:'+prior)[0]
            self.assertEqual(job['end']-job['start'],hours*3600)

    def test_weekly_report_catches_up_once_after_restart(self):
        now=self.stamp('2026-10-20 09:00')
        options={'telegram_weekly':'1','telegram_monthly':'0'}
        saved={'sent':now,'calendar_started':{'weekly':self.stamp('2026-10-15 00:00')}}
        jobs,state,_=prepare(options,saved,now)
        self.assertEqual(jobs[0]['key'],'weekly:2026-10-12')
        state['period_keys']={'weekly':jobs[0]['key']}
        self.assertEqual(prepare(options,state,now+60)[0],[])

    def test_monthly_report_uses_previous_calendar_month(self):
        now=self.stamp('2026-11-01 07:00')
        jobs,_,_=prepare({'telegram_weekly':'0','telegram_monthly':'1'},
                        {'sent':now,'calendar_started':{'monthly':self.stamp('2026-10-15 00:00')}},now)
        self.assertEqual(jobs[0]['key'],'monthly:2026-10-01')
        self.assertEqual(jobs[0]['end']-jobs[0]['start'],(31*24+1)*3600)

    def test_new_schedule_does_not_send_retroactive_summaries(self):
        now=self.stamp('2026-10-15 18:00')
        self.assertEqual(prepare({}, {'sent':now},now)[0],[])

    def test_utf16_limit_does_not_split_emoji_pair(self):
        text=limited_text('🙂'*5000)
        self.assertLessEqual(len(text.encode('utf-16-le')),8000)
        self.assertTrue(text.endswith('…'))

    def test_missing_daily_samples_are_not_reported_as_zero_traffic(self):
        now=self.stamp('2026-10-15 07:00');job=self.daily('2026-10-15 07:00','daily:2026-10-13')[0]
        text=format_period({'accounting':{'days':{'2026-10-14':{'observed':False,'rx':0,'tx':0}}}},job,now)
        self.assertIn('No daily traffic samples',text)
        self.assertNotIn('0.000 GB',text)


class SenderLedgerTests(unittest.TestCase):
    def test_previous_good_sender_state_recovers(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            telegram_state.save({'sent':100},path);telegram_state.save({'sent':200},path)
            (path/'telegram-state.json').write_text('broken')
            state,notice=telegram_state.load(path)
            self.assertEqual(state['sent'],100);self.assertEqual(notice,'TELEGRAM-STATE-RECOVERED')

    def test_legacy_sender_state_migrates_without_changing_sent_time(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);atomic_json(path/'telegram-state.json',{'sent':100,'attempt':90})
            state,notice=telegram_state.load(path)
            self.assertEqual(state['sent'],100);self.assertIsNone(notice)
            telegram_state.save(state,path)
            self.assertEqual(telegram_state.load(path)[0]['sent'],100)

    def test_secret_fields_are_never_valid_sender_ledger_data(self):
        self.assertFalse(telegram_state.valid({'token':'PRIVATE_SENTINEL'}))
        self.assertFalse(telegram_state.valid({'snapshot':{'token':'PRIVATE_SENTINEL'}}))
