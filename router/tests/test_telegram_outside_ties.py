"""BH2-05 (bug hunt 07.11.2026): equal-time outside-change decisions are ordered the same way by both twins.

The sender tells the newest decision of a class (group[-1] / group[#group]). telegram_report.outside_notice sorts by time
with Python's stable sorted(), so equal times keep the ring (insertion) order; lua/telegram.lua sorted equal times by
key (alphabetical DECISION:TRIGGER:time), so with two HOLDs stamped in the same second Lua could name the older one
as the newest. Both now keep the ring order: the decision recorded last is told. The same ring file is fed to both.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

TESTS=Path(__file__).resolve().parent
LIB=TESTS.parents[0]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
os.environ['TZ']='CET-1CEST,M3.5.0,M10.5.0/3'
time.tzset()

import agent  # noqa: E402
import telegram_report as report  # noqa: E402
import telegram_state  # noqa: E402

CONFIG={'telegram_enabled':'1','telegram_chat':'-100123','telegram_token':'123456:SYNTHETICtokenNOTREAL'}
T0=1794040000.0
LUA=shutil.which('lua5.1')


def verdict(decision,trigger,t,packages):
    return {'decision':decision,'trigger':trigger,'packages':list(packages),'why':'FOREIGN-PACKAGES' if decision=='HOLD' else 'ADOPT-PACKAGES-ONLY','time':t}


# recorded in this order; the alphabetical key order is the reverse within each tie
RING=[verdict('HOLD','PAIR-Z-FIRST',T0,('firewall',)),verdict('HOLD','PAIR-A-SECOND',T0,('wireguard',)),
      verdict('ADOPT','PAIR-Z-FIRST',T0+1,('dhcp',)),verdict('ADOPT','PAIR-A-SECOND',T0+1,('wireless',))]


def ring_text():
    ring={}
    for v in RING:ring=telegram_state.outside_push(ring,v)
    return json.dumps(ring)


def python_sent(text,now):
    sent=[]
    with tempfile.TemporaryDirectory() as folder:
        runtime=Path(folder);(runtime/telegram_state.OUTSIDE_FILE).write_text(text)
        with patch.object(agent,'RUNTIME',runtime),patch.object(report,'send_message',side_effect=lambda c,t:sent.append(t)),\
             patch.object(report.time,'sleep'):
            report.outside_notice(dict(CONFIG),{},now)
    return sent


def lua_sent(text,now):
    script=("package.path=%r..'/?.lua;'..package.path\n"
            "local canon=require('canon');local tg=require('telegram')\n"
            "local d={runtime='/run/hv',files={},sent={}}\n"
            "d.files['/run/hv/'..tg.OUTSIDE_FILE]=io.read('*a')\n"
            "d.read=function(p) return d.files[p] end;d.size=function(p) return d.files[p] and #d.files[p] or nil end\n"
            "d.is_link=function() return false end;d.write=function(p,t) d.files[p]=t end;d.remove=function(p) d.files[p]=nil end\n"
            "d.lock=function(fn) return fn() end;d.sleep=function() end;d.send=function(_,t) d.sent[#d.sent+1]=t end\n"
            "d.clock=function() return nil end\n"
            "tg.outside_notice(d,canon.object({}),canon.object({}),%r)\n"
            "io.write(canon.encode(canon.array(d.sent)))\n")%(str(LIB/'lua'),now)
    out=subprocess.run([LUA,'-e',script],input=text.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,
                       env=dict(os.environ,TZ='CET-1CEST,M3.5.0,M10.5.0/3'))
    if out.returncode:raise AssertionError(out.stderr.decode(errors='replace'))
    return json.loads(out.stdout.decode('utf-8'))


class PythonTieOrder(unittest.TestCase):
    def test_the_last_recorded_of_equal_times_is_told(self):
        sent=python_sent(ring_text(),T0+30)
        self.assertEqual(len(sent),2)
        self.assertIn('Trigger: PAIR-A-SECOND',sent[0]);self.assertIn('Changed packages: wireguard',sent[0])
        self.assertIn('Trigger: PAIR-A-SECOND',sent[1]);self.assertIn('Changed packages: wireless',sent[1])
        self.assertIn('1 earlier decision(s)',sent[0])


@unittest.skipUnless(LUA,'lua5.1 is not installed')
class LuaTwinTieOrder(unittest.TestCase):
    def test_same_messages_for_the_same_ring(self):
        text=ring_text()
        self.assertEqual(lua_sent(text,T0+30),python_sent(text,T0+30))
        # the reverse recording order: the other trigger is the newest, in both
        global RING
        saved=RING
        try:
            RING=[saved[1],saved[0],saved[3],saved[2]];text=ring_text()
            lua,py=lua_sent(text,T0+30),python_sent(text,T0+30)
            self.assertEqual(lua,py);self.assertIn('Trigger: PAIR-Z-FIRST',lua[0])
        finally:
            RING=saved


def release_verdict(kind,trigger,t,packages):
    return {'decision':'RELEASE','release':kind,'trigger':trigger,'packages':list(packages),'why':'OWNER-'+kind,'time':t}


# owner decision 07.11.2026 (class RELEASE): a hold ended by the owner's Stop or Start, with the other classes in one ring
MIXED=[verdict('HOLD','PAIR-A-SECOND',T0,('wireguard',)),release_verdict('STOP','PAIR-Z-FIRST',T0+1,('firewall',)),
       release_verdict('START','PAIR-A-SECOND',T0+1,('wireguard',)),verdict('ADOPT','PAIR-A-SECOND',T0+2,('dhcp',))]


def mixed_text(order):
    ring={}
    for i in order:ring=telegram_state.outside_push(ring,MIXED[i])
    return json.dumps(ring)


class PythonReleaseOrder(unittest.TestCase):
    def test_classes_go_in_order_and_the_last_recorded_release_of_a_tie_is_told(self):
        sent=python_sent(mixed_text(range(4)),T0+30)
        self.assertEqual(len(sent),3)
        self.assertIn('PAIR-OUTSIDE-CHANGE-HELD',sent[0]);self.assertIn('PAIR-OUTSIDE-CHANGE-ADOPTED',sent[1]);self.assertIn('PAIR-OUTSIDE-CHANGE-RELEASED',sent[2])
        self.assertIn('owner Start, new configuration accepted',sent[2]);self.assertIn('1 earlier decision(s)',sent[2])
        self.assertNotIn('PAIR-Z-FIRST',sent[2])


@unittest.skipUnless(LUA,'lua5.1 is not installed')
class LuaTwinReleaseOrder(unittest.TestCase):
    def test_same_messages_for_the_same_ring(self):
        for order in (range(4),(2,1,0,3),(1,2),(2,1),(1,),(2,)):
            text=mixed_text(order)
            self.assertEqual(lua_sent(text,T0+30),python_sent(text,T0+30),order)


if __name__=='__main__':
    unittest.main()
