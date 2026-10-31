"""The Lua supervisor (files/usr/lib/homensai-vpn/lua: auto, transaction, rollback, pair, manual, history,
auto_control) against the Python state-file contracts.

tests/lua/auto_fixture.lua runs a full guarded transaction with fakes and writes real files; Python then
reads them with the real code: native_switch.validate_journal / journal_read on the journal (incl. the
envelope sha256, pair_policy.metadata and failure_diagnosis.profile_identity of the delegated records),
native_history.History.load on the history (envelope, checksum, counters), auto_control.valid_stop and
pair_auto.read_state-style checks on the control files. Also runs the plain Lua suites tests/lua/test_auto*.lua.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import native_switch as n
import native_history as h
import auto_control
import pair_policy
from agent import read_json

LUA=shutil.which('lua5.1') or shutil.which('lua')
FIXTURE=HERE/'lua'/'auto_fixture.lua'


def lua_env():
    env=dict(os.environ)
    env.setdefault('HOMENSAI_TEST_RUNTIME',tempfile.gettempdir())
    return env


@unittest.skipIf(LUA is None,'lua5.1 is not installed')
class LuaAutoFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=Path(tempfile.mkdtemp(prefix='lua-auto-'))
        result=subprocess.run([LUA,str(FIXTURE),str(cls.directory)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=lua_env(),timeout=120)
        if result.returncode:
            raise AssertionError('fixture failed:\n'+result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
        cls.summary=json.loads(result.stdout.decode().strip().splitlines()[-1])
        cls.persist=cls.directory/'etc';cls.runtime=cls.directory/'run'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory,ignore_errors=True)

    def test_journal_is_accepted_by_python(self):
        path=self.persist/'native-transaction.json'
        envelope=json.loads(path.read_text(encoding='utf8'))
        self.assertEqual(envelope['schema'],1)
        self.assertEqual(envelope['sha256'],n.digest(envelope['data']))
        value=n.validate_journal(envelope['data'])  # pair_transition -> pair_policy.metadata, vendor_profiles -> profile_identity
        self.assertEqual(value['phase'],'ROLLED-BACK')
        self.assertEqual(value['restored_order'],['r1','r2'])
        self.assertEqual(value['after'],['r2','r1'])
        self.assertIsNotNone(pair_policy.metadata(value))
        self.assertEqual(pair_policy.current_role(value),'source')
        self.assertEqual([row['phase'] for row in value['phase_evidence']],['ARMED','APPLYING','WAIT-CLIENT','COMMITTED','RESTORING','ROLLED-BACK'])
        self.assertIsInstance(value['started'],float);self.assertIsInstance(value['confirmed'],float)
        self.assertIsNone(value['pid'])
        with patch.object(n,'JOURNAL',path):
            same=n.journal_read()
        self.assertEqual(same,value)

    def test_history_is_loaded_by_python(self):
        history=h.History(self.persist,detail_days=7)
        data=history.load()
        self.assertFalse(history.restored)
        self.assertEqual(data['counter_version'],2)
        states=[row['state'] for row in data['events']]
        self.assertEqual(states,['ARMED','APPLYING','WAIT-CLIENT','COMMITTED','RESTORING','ROLLED-BACK'])
        self.assertEqual(data['sequence'],6)
        self.assertEqual(data['totals']['attempts'],1);self.assertEqual(data['totals']['committed'],1)
        self.assertEqual(data['totals']['automatic_committed'],1);self.assertEqual(data['totals']['protocol_switches'],1)
        self.assertEqual(data['totals']['rollbacks'],1);self.assertEqual(data['totals']['returns'],1)
        self.assertEqual({row['attempt_id'] for row in data['events'][:4]},{1})
        self.assertEqual(data['events'][4]['attempt_id'],5)
        # the backup is the previous main and loads too
        backup=h.History(self.persist,detail_days=7)
        (self.persist/'native-history.json').unlink()
        self.assertEqual(backup.load()['sequence'],5);self.assertTrue(backup.restored)
        public=history.public(data,now=data['last_time'])
        self.assertEqual(public['sequence'],6)
        self.assertEqual(public['weekly']['committed'],1)

    def test_control_files(self):
        revision=read_json(self.runtime/'auto-control-revision.json',{})
        self.assertEqual(set(revision),{'revision'})
        with patch.object(n,'RUNTIME',self.runtime):n.require_control_revision(revision['revision'])
        status=read_json(self.runtime/'native-status.json',{})
        self.assertEqual(status['state'],'ROLLED-BACK');self.assertEqual(status['mode'],'continuous-pair')
        self.assertEqual(status['transition_outcome'],'restored');self.assertEqual(status['original_restored'],True)
        certificate=read_json(self.persist/'native-certificate.json',{})
        self.assertEqual(certificate['proof_scope'],'router-probed-ipv4')
        lease=read_json(self.runtime/'native-lease.json',{})
        self.assertEqual(lease['sha256'],n.digest(lease['data']))
        self.assertTrue(auto_control.valid_stop({}))

    def test_require_control_revision_rejects_other(self):
        with patch.object(n,'RUNTIME',self.runtime):
            with self.assertRaises(n.Refused):n.require_control_revision('0'*32)


@unittest.skipIf(LUA is None,'lua5.1 is not installed')
class LuaSuites(unittest.TestCase):
    def test_lua_auto_suites(self):
        for path in sorted((HERE/'lua').glob('test_auto*.lua')):
            with self.subTest(suite=path.name):
                result=subprocess.run([LUA,str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=lua_env(),timeout=300)
                self.assertEqual(result.returncode,0,path.name+'\n'+result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))


if __name__=='__main__':
    unittest.main()
