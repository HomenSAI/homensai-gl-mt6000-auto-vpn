"""Review 06.11.2026, the smaller findings F-36, F-37, F-46, F-47 and F-82.

F-36: stats_reset.pending claims the request by one atomic rename before reading it. F-37: the readopt archive's directory
is fsynced before the ownership is retired. F-46: one grammar for the recovery settings in Python and Lua. F-47: the Lua
server pick reads client_id for OpenVPN only. F-82: the advisor treats an unknown route as no evidence of calm. The Lua
twins cannot run on this host (no Lua interpreter): their source is pinned.
"""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

LIB=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import advisor
import agent
import pair_auto
import recovery_settings
import stats_reset


class StatsResetClaimTests(unittest.TestCase):
    def test_a_request_queued_during_the_read_is_not_deleted(self):
        # F-36: A is read while B arrives; the old read-then-unlink removed B unseen
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)
            agent.atomic_json(runtime/stats_reset.REQUEST,{'scope':'latency','time':1.0,'nonce':'a'*32})
            real=json.loads
            def loads(text):
                agent.atomic_json(runtime/stats_reset.REQUEST,{'scope':'speed','time':2.0,'nonce':'b'*32})
                return real(text)
            with patch.object(stats_reset.json,'loads',side_effect=loads):
                first=stats_reset.pending(runtime)
            self.assertEqual(first['nonce'],'a'*32)
            second=stats_reset.pending(runtime)
            self.assertIsNotNone(second,'the request queued meanwhile survives the claim of the first');self.assertEqual(second['nonce'],'b'*32)
            self.assertIsNone(stats_reset.pending(runtime));self.assertEqual(sorted(p.name for p in runtime.iterdir()),[])

    def test_claim_rejects_symlinks_and_oversize_without_touching_the_queue_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)
            (runtime/stats_reset.REQUEST).write_text('{'+'"x":1,'*600+'"scope":"latency"}')
            self.assertIsNone(stats_reset.pending(runtime));self.assertFalse((runtime/stats_reset.REQUEST).exists())
            self.assertIsNone(stats_reset.pending(runtime))


class ReadoptArchiveDurabilityTests(unittest.TestCase):
    def test_the_archive_directory_is_fsynced_before_the_ownership_is_retired(self):
        # F-37: a power cut between the archive write and the STOPPED save must never keep the retirement without the archive
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for module in (agent,):
                for name in ('RUNTIME','PERSIST'):
                    active=patch.object(module,name,root);active.start();self.addCleanup(active.stop)
            state={'id':'a'*32,'phase':'HELD','owned':['wgclient1'],'recovery_error':'PAIR-EXTERNAL-CONFIG-CHANGE'}
            agent.atomic_json(root/'pair-auto-state.json',{'data':state,'sha256':agent.checksum(state)})
            events=[];real_fsync=os.fsync;real_save=pair_auto.save
            def fsync(fd):
                info=os.fstat(fd)
                if stat.S_ISDIR(info.st_mode):
                    try:target=os.readlink('/proc/self/fd/%d'%fd)
                    except OSError:target='?'
                    events.append(('fsync-dir',Path(target).name))
                return real_fsync(fd)
            def save(value):events.append(('save',value['phase']));return real_save(value)
            with patch('native_switch.journal_read',return_value={}),patch.object(pair_auto.os,'fsync',side_effect=fsync),patch.object(pair_auto,'save',side_effect=save):
                self.assertTrue(pair_auto.release_session(dict(state),'PAIR-EXTERNAL-CONFIG-CHANGE'))
            self.assertIn(('fsync-dir','session-recovery'),events)
            self.assertLess(events.index(('fsync-dir','session-recovery')),events.index(('save','STOPPED')))
            self.assertEqual(len(list((root/'session-recovery').glob('pair-*-readopt-*.json'))),1)


class RecoverySettingGrammarTests(unittest.TestCase):
    def test_python_and_lua_read_the_same_values(self):
        # F-46: '3_0' was 30 for Python (int() accepts underscores) and the default for Lua
        for raw,expected in (('3_0',120),(30,30),('30','30'),(' 30 ',30),('+45',45),(30.5,120),(True,120),('abc',120),(None,120),('',120)):
            with self.subTest(raw=raw):
                self.assertEqual(recovery_settings.normalized({'recovery_primary_stable':raw})['primary_stable'],int(expected))
        self.assertEqual(recovery_settings.normalized({'recovery_cooldown':'1_000'})['cooldown'],60)
        lua=(LIB/'lua/pair.lua').read_text(encoding='utf-8')
        self.assertIn("if type(value)=='number' and value%1==0 then number=value",lua)
        self.assertNotIn("if type(value)=='number' then number=value<0 and -math.floor(-value) or math.floor(value)",lua)


class ServerPickProfileKeyTests(unittest.TestCase):
    def test_lua_openvpn_reads_client_id_only(self):
        # F-47: not verified by execution; the Lua line must not fall through to peer_id for OpenVPN
        source=(LIB/'lua/server_pick.lua').read_text(encoding='utf-8')
        self.assertNotIn("digits(protocol=='openvpn' and s.client_id or s.peer_id)",source)
        self.assertIn("digits(protocol=='openvpn' and s.client_id or protocol~='openvpn' and s.peer_id or nil)",source)


class AdvisorCalmEvidenceTests(unittest.TestCase):
    def test_an_unknown_or_missing_route_is_no_calm(self):
        # F-82: no fresh observation of the route is no evidence that nothing is switching
        for calm in ({'open':[],'route':'unknown','native':'OBSERVING'},{'open':[],'native':'OBSERVING'},{'open':[],'route':None,'native':None}):
            with self.subTest(calm=calm):self.assertEqual(advisor.calm_codes(calm),['ADVISOR-CALM-UNKNOWN'])
        self.assertEqual(advisor.calm_codes({'open':[],'route':'source','native':'OBSERVING'}),[])
        self.assertEqual(advisor.calm_codes({'open':[],'route':'off','native':None,'phase':None,'manual':None}),[])
        self.assertEqual(advisor.calm_codes({'open':[],'route':'switching','native':'OBSERVING'}),['ADVISOR-BUSY-SWITCH'])

    def test_lua_advisor_mirrors_the_rule(self):
        source=(LIB/'lua/advisor.lua').read_text(encoding='utf-8')
        self.assertIn("if calm.route==nil or calm.route==NULL or calm.route=='unknown' then return {'ADVISOR-CALM-UNKNOWN'} end",source)


if __name__=='__main__':unittest.main()
