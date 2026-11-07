"""Owner decision 07.11.2026: a HOLD (PAIR-OUTSIDE-CHANGE-HELD) or an automatic ADOPT (PAIR-OUTSIDE-CHANGE-ADOPTED) of a
change made outside the app is told in Telegram. The pair writes each decision into a bounded RAM ring
(telegram_state.outside_record); deliver() tells it on its next round (telegram_report.outside_notice), at most one
message per class every 10 min, gated like the VENDOR-BUSY notice. Fake sender only: no network, no real token.
Lua twin: lua/test_telegram_outside.lua (the same file format; the text is compared below where lua5.1 exists)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

TESTS=Path(__file__).resolve().parent
ROOT=TESTS.parents[0]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(ROOT))
os.environ['TZ']='CET-1CEST,M3.5.0,M10.5.0/3'
time.tzset()

import agent  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
import telegram_report as report  # noqa: E402
import telegram_state  # noqa: E402
import test_outside_change_policy as policy  # noqa: E402  (module import: its TestCases are not collected here)
import test_pair_auto  # noqa: E402
import test_formal_fixes as formal  # noqa: E402  (module import; its OutsideChange fixture is reached through K9's base below)

CASES=policy.CASES

CONFIG={'telegram_enabled':'1','telegram_chat':'-100123','telegram_token':'123456:SYNTHETICtokenNOTREAL','telegram_schedule':'interval',
        'telegram_interval':'60','telegram_weekly':'0','telegram_monthly':'0'}
T0=1794040000.0  # 07.11.2026, a fixed clock


def hold(t,packages=('wireguard','firewall'),trigger='PAIR-EXTERNAL-CONFIG-CHANGE'):
    return {'decision':'HOLD','trigger':trigger,'packages':list(packages),'why':'FOREIGN-PACKAGES','time':t}


def adopt(t,packages=('dhcp','wireless')):
    return {'decision':'ADOPT','trigger':'PAIR-EXTERNAL-CONFIG-CHANGE','packages':list(packages),'why':'ADOPT-PACKAGES-ONLY','time':t}


def release(t,kind='STOP',packages=('wireguard','firewall'),trigger='PAIR-EXTERNAL-CONFIG-CHANGE'):
    """Owner decision 07.11.2026: the owner's Stop / Start ended an outside-change hold (class RELEASE)."""
    return {'decision':'RELEASE','release':kind,'trigger':trigger,'packages':list(packages),'why':'OWNER-'+kind,'time':t}


class Base(unittest.TestCase):
    """test_pair_auto's temporary RUNTIME/PERSIST and test_outside_change_policy's running session, without their tests."""
    setUp=test_pair_auto.Tests.setUp
    running=policy.RunningSession.running
    tick=policy.RunningSession.tick


class Ring(Base):
    """The pair's side: the ring is bounded, deduplicated, names only, and a write failure never reaches Auto."""
    def ring(self):
        return agent.read_json(self.runtime/telegram_state.OUTSIDE_FILE,{})

    def test_bounded_and_deduplicated(self):
        for i in range(40):telegram_state.outside_record(hold(T0+i))
        telegram_state.outside_record(hold(T0+39))
        items=self.ring()['items']
        self.assertEqual(len(items),telegram_state.OUTSIDE_KEEP);self.assertEqual(items[-1]['time'],T0+39);self.assertEqual(items[0]['time'],T0+24)

    def test_only_codes_and_names_never_a_value(self):
        telegram_state.outside_record(dict(hold(T0,packages=('wireguard','key=AAAA/BBBB+=','endpoint 1.2.3.4:51820','Wireguard')),
                                           token='123456:SYNTHETICtokenNOTREAL',endpoint='1.2.3.4:51820',why='bad why'))
        telegram_state.outside_record({'decision':'HOLD','trigger':'123:abc/def','packages':[],'why':'X','time':T0})  # not a code: dropped
        telegram_state.outside_record({'decision':'ELSE','trigger':'PAIR-X','packages':[],'why':'X','time':T0})
        items=self.ring()['items']
        self.assertEqual(len(items),1);self.assertEqual(items[0]['packages'],['wireguard']);self.assertEqual(items[0]['why'],'UNCLASSIFIED')
        text=json.dumps(items)
        for secret in ('SYNTHETIC','1.2.3.4','AAAA','endpoint','token'):self.assertNotIn(secret,text)

    def test_a_failing_write_never_raises(self):
        with patch.object(telegram_state,'atomic_json',side_effect=OSError('read-only')):
            telegram_state.outside_record(hold(T0))
            pair.outside_notice(hold(T0))
        pair.outside_notice(None)

    def test_tick_hold_and_adopt_go_into_the_ring(self):
        protected=dict(CASES['protected'])
        backend,_=self.running(protected)
        self.tick(backend,lambda *_:dict(protected,wireless='l2',dhcp='d2'))
        items=self.ring()['items'];self.assertEqual([(x['decision'],x['packages']) for x in items],[('ADOPT',['dhcp','wireless'])])
        for path in pair.paths():path.unlink(missing_ok=True)
        (self.runtime/'pair-readopt.json').unlink(missing_ok=True)
        backend,_=self.running(protected)
        self.tick(backend,lambda *_:dict(protected,wireguard='zz'))
        self.tick(backend,lambda *_:dict(protected,wireguard='zz'))  # the next pass keeps the hold: no second item
        items=self.ring()['items'];self.assertEqual([(x['decision'],x['packages']) for x in items],[('ADOPT',['dhcp','wireless']),('HOLD',['wireguard'])])
        self.assertNotIn('zz',json.dumps(items))


class ReleaseRing(Base):
    """RELEASE entries: validated like the others, the STOP/START kind is required, codes and names only."""
    def ring(self):
        return agent.read_json(self.runtime/telegram_state.OUTSIDE_FILE,{})

    def test_stop_and_start_entries_are_kept_with_their_kind(self):
        telegram_state.outside_record(release(T0,'STOP'));telegram_state.outside_record(release(T0,'START'))
        telegram_state.outside_record(release(T0,'START'))  # the same decision twice: one item
        items=self.ring()['items']
        self.assertEqual([(x['decision'],x['release'],x['why'],x['packages']) for x in items],
                         [('RELEASE','STOP','OWNER-STOP',['wireguard','firewall']),('RELEASE','START','OWNER-START',['wireguard','firewall'])])
        self.assertEqual(len({x['key'] for x in items}),2,'a Stop and a Start of the same instant are different decisions')

    def test_a_release_without_a_valid_kind_is_dropped_and_no_secret_is_kept(self):
        for kind in (None,'ADOPT','stop',1,True):telegram_state.outside_record(dict(release(T0),release=kind))
        v=release(T0,'START',packages=('wireguard','key=AAAA/BBBB+=','endpoint 1.2.3.4:51820'));v['token']='123456:SYNTHETICtokenNOTREAL'
        telegram_state.outside_record(v)
        items=self.ring()['items']
        self.assertEqual(len(items),1);self.assertEqual(items[0]['packages'],['wireguard'])
        for secret in ('SYNTHETIC','1.2.3.4','AAAA','endpoint','token'):self.assertNotIn(secret,json.dumps(items))
        telegram_state.outside_record({'decision':'STOP','trigger':'PAIR-EXTERNAL-CONFIG-CHANGE','packages':[],'why':'OWNER-STOP','time':T0})
        self.assertEqual(len(self.ring()['items']),1,'only the RELEASE class is a ring class; a bare STOP verdict is not an entry')


class Delivery(Base):
    """The sender's side through deliver(): the fake sender records every text."""
    def setUp(self):
        super().setUp()
        self.sent=[]
        for p in (patch.object(report,'config_snapshot',side_effect=lambda:dict(self.config)),
                  patch.object(report,'send_message',side_effect=self.send),patch.object(report.time,'sleep'),
                  patch.object(telegram_state,'_mono',side_effect=lambda:self.mono)):
            p.start();self.addCleanup(p.stop)
        self.config=dict(CONFIG);self.fail=None
        self.mono=None  # no monotonic clock: the items keep the wall-clock age (the cases above BH-05)

    def send(self,config,text):
        if self.fail is not None:raise self.fail
        self.sent.append(text)

    def deliver(self,now,saved=None,status=None):
        # the report schedule is not due (sent a moment ago): only notices go out
        saved=dict({'sent':now-1.0},**(saved or {}))
        return report.deliver(status or {'native_failover':{'state':'OBSERVING','time':now}},saved,now)

    def test_hold_one_message_with_packages_and_what_to_do(self):
        telegram_state.outside_record(hold(T0))
        public,state,sent=self.deliver(T0+30)
        self.assertEqual(len(self.sent),1);self.assertFalse(sent,'no report was due')
        text=self.sent[0]
        for part in ('PAIR-OUTSIDE-CHANGE-HELD','Changed packages: wireguard firewall','Trigger: PAIR-EXTERNAL-CONFIG-CHANGE','press Stop, then Start',
                     'Изменённые пакеты: wireguard firewall','«Стоп», затем «Старт»'):
            self.assertIn(part,text)
        self.assertTrue(telegram_state.valid(state));self.assertEqual(state['last_code'],'TELEGRAM-DELIVERED')
        self.deliver(T0+90);self.deliver(T0+900);self.assertEqual(len(self.sent),1,'told once')

    def test_release_stop_text_en_then_ru_with_privacy(self):
        telegram_state.outside_record(release(T0,'STOP'))
        self.deliver(T0+30)
        self.assertEqual(len(self.sent),1);text=self.sent[0]
        for part in ('PAIR-OUTSIDE-CHANGE-RELEASED','hold ended: owner Stop','Trigger: PAIR-EXTERNAL-CONFIG-CHANGE','Changed packages: wireguard firewall',
                     'Class: OWNER-STOP','press Start','Удержание изменения, сделанного вне приложения, завершено: «Стоп» владельца',
                     'Изменённые пакеты: wireguard firewall','Класс: OWNER-STOP','«Старт»'):
            self.assertIn(part,text)
        self.assertLess(text.index('hold ended: owner Stop'),text.index('«Стоп» владельца'),'EN first, then RU')
        for secret in (CONFIG['telegram_token'],CONFIG['telegram_chat']):self.assertNotIn(secret,text)
        self.deliver(T0+90);self.deliver(T0+900);self.assertEqual(len(self.sent),1,'told once')

    def test_release_start_text(self):
        telegram_state.outside_record(release(T0,'START'))
        self.deliver(T0+30)
        self.assertEqual(len(self.sent),1);text=self.sent[0]
        for part in ('PAIR-OUTSIDE-CHANGE-RELEASED','hold ended: owner Start, new configuration accepted','Class: OWNER-START',
                     'Удержание изменения, сделанного вне приложения, завершено: «Старт» владельца, новая конфигурация принята','Класс: OWNER-START'):
            self.assertIn(part,text)
        self.assertNotIn('press Start',text)

    def test_release_has_its_own_rate_limit_bucket(self):
        telegram_state.outside_record(hold(T0));self.deliver(T0+5);self.assertEqual(len(self.sent),1)
        telegram_state.outside_record(release(T0+10,'STOP'));self.deliver(T0+20)
        self.assertEqual(len(self.sent),2,'a HOLD message does not hold back a RELEASE');self.assertIn('RELEASED',self.sent[1])
        telegram_state.outside_record(release(T0+100,'START',packages=('firewall',)));telegram_state.outside_record(release(T0+200,'STOP',packages=('dhcp',)))
        self.deliver(T0+300);self.assertEqual(len(self.sent),2,'held back inside the RELEASE window')
        self.deliver(T0+700)
        self.assertEqual(len(self.sent),3);self.assertIn('Changed packages: dhcp',self.sent[2]);self.assertIn('owner Stop',self.sent[2])
        self.assertIn('1 earlier decision(s) of this class since',self.sent[2])
        telegram_state.outside_record(adopt(T0+710));self.deliver(T0+720)
        self.assertEqual(len(self.sent),4,'an ADOPT is not held back by RELEASE messages')

    def test_adopt_seen_only_while_armed_is_still_delivered_on_the_next_round(self):
        protected=dict(CASES['protected'])
        backend,_=self.running(protected)
        self.tick(backend,lambda *_:dict(protected,wireless='l2',dhcp='d2'))  # ARMED for seconds; the next status is OBSERVING
        self.deliver(time.time()+300,status={'native_failover':{'state':'OBSERVING','reason':'PAIR-WATCHING'}})
        self.assertEqual(len(self.sent),1)
        self.assertIn('PAIR-OUTSIDE-CHANGE-ADOPTED',self.sent[0]);self.assertIn('Changed packages: dhcp wireless',self.sent[0]);self.assertIn('Nothing to do.',self.sent[0])

    def test_rate_limit_one_per_class_per_10_min_with_a_summary(self):
        telegram_state.outside_record(hold(T0));self.deliver(T0+5);self.assertEqual(len(self.sent),1)
        telegram_state.outside_record(hold(T0+60,packages=('firewall',)));telegram_state.outside_record(hold(T0+120,packages=('ovpnclient',)))
        self.deliver(T0+130);self.deliver(T0+400);self.assertEqual(len(self.sent),1,'held back inside the window')
        telegram_state.outside_record(adopt(T0+410));self.deliver(T0+420)
        self.assertEqual(len(self.sent),2,'another class has its own window');self.assertIn('ADOPTED',self.sent[1])
        self.deliver(T0+606)
        self.assertEqual(len(self.sent),3);self.assertIn('Changed packages: ovpnclient',self.sent[2])
        self.assertIn('1 earlier decision(s) of this class since',self.sent[2]);self.assertIn('не отправленных отдельно: 1',self.sent[2])
        self.deliver(T0+2000);self.assertEqual(len(self.sent),3)

    def test_no_secret_in_any_text(self):
        telegram_state.outside_record(dict(hold(T0,packages=('wireguard','private_key=QUJDRA==')),endpoint='203.0.113.7:51820'))
        telegram_state.outside_record(dict(adopt(T0+1),key='QUJDRA=='))
        self.deliver(T0+10)
        self.assertEqual(len(self.sent),2)
        for text in self.sent:
            for secret in (CONFIG['telegram_token'],CONFIG['telegram_chat'],'QUJDRA','203.0.113.7','private_key'):self.assertNotIn(secret,text)

    def test_telegram_off_or_unconfigured_no_message(self):
        telegram_state.outside_record(hold(T0))
        for change in ({'telegram_enabled':'0'},{'telegram_enabled':''},{'telegram_token':''},{'telegram_chat':'not a chat'}):
            self.config=dict(CONFIG,**change);self.deliver(T0+10)
        self.assertEqual(self.sent,[])
        self.config=dict(CONFIG);self.deliver(T0+20);self.assertEqual(len(self.sent),1,'told once Telegram is on')

    def test_a_failed_send_keeps_the_backoff_and_is_not_lost(self):
        telegram_state.outside_record(hold(T0))
        self.fail=report.rejection(429,600)
        _,state,_=self.deliver(T0+10)
        self.assertEqual((state['last_code'],state['retry_after'],state['attempt']),('TELEGRAM-RATE-LIMIT',600,T0+10))
        self.fail=None
        _,state,_=self.deliver(T0+300,saved={k:state[k] for k in ('attempt','retry_after','last_code','known_failures')})
        self.assertEqual(self.sent,[],'the backoff holds')
        self.deliver(T0+700);self.assertEqual(len(self.sent),1)

    def test_an_old_decision_is_marked_not_sent(self):
        telegram_state.outside_record(hold(T0))
        self.deliver(T0+report.OUTSIDE_MAX_AGE+1);self.assertEqual(self.sent,[])
        self.deliver(T0+report.OUTSIDE_MAX_AGE+700);self.assertEqual(self.sent,[])

    def test_bh05_a_wall_clock_step_does_not_drop_a_fresh_hold(self):
        """BH-05: HOLD stamped before NTP (sysfixtime hours behind), NTP then steps the clock +10 h before the round."""
        self.mono=50.0
        telegram_state.outside_record(hold(T0))
        self.assertEqual(agent.read_json(self.runtime/telegram_state.OUTSIDE_FILE,{})['items'][0]['mono'],50.0)
        self.mono=80.0
        self.deliver(T0+10*3600)
        self.assertEqual(len(self.sent),1);self.assertIn('PAIR-OUTSIDE-CHANGE-HELD',self.sent[0])
        self.mono=200.0;self.deliver(T0+10*3600+900);self.assertEqual(len(self.sent),1,'told once')

    def test_bh05_old_by_the_monotonic_clock_is_marked_not_sent(self):
        self.mono=50.0
        telegram_state.outside_record(hold(T0))
        self.mono=50.0+report.OUTSIDE_MAX_AGE+1
        self.deliver(T0+5);self.assertEqual(self.sent,[],'the monotonic age wins over a wall clock that stepped back')
        self.mono=50.0+report.OUTSIDE_MAX_AGE+700;self.deliver(T0+700);self.assertEqual(self.sent,[])

    def test_bh05_no_or_unusable_monotonic_now_falls_back_to_the_wall_clock(self):
        self.mono=50.0
        telegram_state.outside_record(hold(T0))
        self.mono=10.0  # behind the stamp (cannot happen within one boot): the wall clock decides
        self.deliver(T0+report.OUTSIDE_MAX_AGE+1);self.assertEqual(self.sent,[])
        self.mono=50.0;telegram_state.outside_record(hold(T0+1,packages=('firewall',)))
        self.mono=None;self.deliver(T0+30);self.assertEqual(len(self.sent),1)

    def test_the_seen_file_stays_bounded(self):
        for i in range(40):
            telegram_state.outside_record(hold(T0+i*700));self.deliver(T0+i*700+5)
        self.assertEqual(len(self.sent),40)
        seen=agent.read_json(self.runtime/telegram_state.OUTSIDE_SEEN,{})
        self.assertLessEqual(len(seen['done']),telegram_state.OUTSIDE_KEEP)


@unittest.skipUnless(shutil.which('lua5.1'),'lua5.1 is not installed')
class LuaTwinText(unittest.TestCase):
    """The same item gives the same ring entry and the same text in Lua."""
    def lua(self,verdict,more,since):
        script=("package.path='%s/lua/?.lua;'..package.path\nlocal canon=require('canon')\nlocal tg=require('telegram')\n"
                "local item=tg.outside_entry(canon.decode(io.read('*a')))\n"
                "io.write(canon.encode(canon.object({item=item,text=tg.outside_text(item,%d,%r)})))\n")%(ROOT.as_posix(),more,since)
        out=subprocess.run(['lua5.1','-e',script],input=json.dumps(verdict).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,
                           env=dict(os.environ,TZ='CET-1CEST,M3.5.0,M10.5.0/3'))
        self.assertEqual(out.returncode,0,out.stderr.decode(errors='replace'))
        return json.loads(out.stdout.decode('utf-8'))

    def test_same_item_and_text(self):
        for verdict,more,since in ((hold(T0+0.25),0,T0),(adopt(T0+59.5,packages=('network','dhcp')),3,T0-3600.0),
                                   (dict(hold(T0,packages=()),why='UNREADABLE'),1,T0-61.0),
                                   (dict(hold(T0),mono=1234.5),0,T0),(dict(hold(T0),mono=-1),0,T0),(dict(hold(T0),mono=True),0,T0)):
            got=self.lua(verdict,more,since)
            item=telegram_state.outside_entry(verdict)
            self.assertEqual(got['item'],item)
            self.assertEqual(got['text'],report.outside_text(item,more,since))

    def test_same_release_item_and_text(self):
        for verdict,more,since in ((release(T0+0.25,'STOP'),0,T0),(release(T0+59.5,'START',packages=('network','dhcp')),2,T0-3600.0),
                                   (dict(release(T0,'STOP',packages=()),mono=12.5),1,T0-61.0)):
            got=self.lua(verdict,more,since)
            item=telegram_state.outside_entry(verdict)
            self.assertEqual(got['item'],item)
            self.assertEqual(got['text'],report.outside_text(item,more,since))
        for bad in (dict(release(T0,'START'),release='ADOPT'),dict(release(T0,'START'),release=None),dict(release(T0,'START'),release=True)):
            self.assertIsNone(telegram_state.outside_entry(bad));self.assertIsNone(self.lua_entry(bad),'both twins drop a RELEASE without a valid kind')

    def lua_entry(self,verdict):
        script=("package.path='%s/lua/?.lua;'..package.path\nlocal canon=require('canon')\nlocal tg=require('telegram')\n"
                "local item=tg.outside_entry(canon.decode(io.read('*a')))\n"
                "io.write(item==nil and 'null' or canon.encode(item))\n")%ROOT.as_posix()
        out=subprocess.run(['lua5.1','-e',script],input=json.dumps(verdict).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        self.assertEqual(out.returncode,0,out.stderr.decode(errors='replace'))
        return json.loads(out.stdout.decode('utf-8'))


class ReleaseNotice(formal.K9.__bases__[0]):  # test_formal_fixes.OutsideChange (deleted from its namespace there, base only)
    """The pair's release paths record the RELEASE entry: the owner's Stop (end_hold_on_stop) and the owner's Start
    (release_session hand-over), under the control lock, names and codes only. Lua twin: lua/test_telegram_outside.lua."""
    def ring(self):
        return agent.read_json(agent.RUNTIME/telegram_state.OUTSIDE_FILE,{}).get('items',[])

    def test_owner_stop_records_a_stop_release(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertEqual(self.ring(),[],'a hold that is only standing records no RELEASE')
        held=pair.read_state()
        self.assertFalse(pair.end_hold_on_stop(held));self.assertEqual(self.ring(),[],'no Stop: nothing ended, nothing told')
        native.stop_latch(None)
        self.tick()
        self.assertEqual(pair.read_state()['phase'],'STOPPED')
        items=self.ring()
        self.assertEqual([(x['decision'],x['release'],x['trigger'],x['why']) for x in items],[('RELEASE','STOP','PAIR-EXTERNAL-NETWORK-CHANGE','OWNER-STOP')])
        self.tick();self.assertEqual(len(self.ring()),1,'a later pass tells nothing more')

    def test_owner_start_records_a_start_release(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertTrue(pair.release_session(pair.read_state(),'PAIR-EXTERNAL-NETWORK-CHANGE'))
        items=self.ring()
        self.assertEqual([(x['decision'],x['release'],x['trigger'],x['why']) for x in items],[('RELEASE','START','PAIR-EXTERNAL-NETWORK-CHANGE','OWNER-START')])
        self.assertNotIn('ADOPT',[x['decision'] for x in items],'the owner Start is a RELEASE, not an automatic ADOPT')

    def test_the_automatic_adoption_is_not_a_release(self):
        state=pair.read_state()
        verdict=pair.readopt_class(state,'PAIR-EXTERNAL-NETWORK-CHANGE')
        self.assertTrue(pair.release_session(state,'PAIR-EXTERNAL-NETWORK-CHANGE',verdict,'automatic'))
        self.assertEqual(self.ring(),[])

    def test_a_failing_ring_write_never_stops_the_release(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        with patch.object(telegram_state,'atomic_json',side_effect=OSError('read-only')):
            self.assertTrue(pair.release_session(pair.read_state(),'PAIR-EXTERNAL-NETWORK-CHANGE'))
        self.assertEqual(pair.read_state()['phase'],'STOPPED')


if __name__=='__main__':
    unittest.main()
