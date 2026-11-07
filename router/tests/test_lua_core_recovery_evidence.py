"""Review 06.11.2026, findings F-20..F-26 (the Lua write stage, durability and Stop).

F-20: a lost answer of the Lua helper after the dispatch never terminalizes an APPLYING journal as ROLLED-BACK without
rollback evidence (native_switch.lua_rollback_required). F-26: Stop still writes the durable latch when the volatile pair
intent write fails (auto_control.stop). F-21, F-22, F-23, F-25 and the Lua side of F-26 are Lua edits that this host
cannot run (no Lua interpreter): the tests below pin the source of each so that the mirror of the Python logic cannot be
reverted unnoticed; the Lua suites of router/tests/lua still run them where lua5.1 exists.
"""
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

LIB=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import agent
import auto_control as control
import native_switch as n

TX='a'*32


class LostLuaAnswerTests(unittest.TestCase):
    def lost(self):return n.Refused('LUA-CORE-UNAVAILABLE')   # timeout, killed helper, unparseable output: no lua_result

    def test_lost_answer_with_an_applying_journal_of_this_transaction_needs_rollback(self):
        # F-20: the helper wrote its fenced APPLYING journal and may have changed UCI or the kernel before it stalled.
        self.assertTrue(n.lua_rollback_required(self.lost(),{'tx':TX,'phase':'APPLYING'},TX))

    def test_a_missing_or_settled_journal_is_the_proof_that_nothing_was_written(self):
        for saved in ({},{'tx':'b'*32,'phase':'APPLYING'},{'tx':TX,'phase':'ROLLED-BACK'},None,[]):
            with self.subTest(saved=saved):self.assertFalse(n.lua_rollback_required(self.lost(),saved,TX))

    def test_a_parsed_answer_decides_by_its_own_flag(self):
        said_no=n.Refused('POLICY-REORDER-UNVERIFIED');said_no.lua_result={'ok':False,'rollback_required':False}
        self.assertFalse(n.lua_rollback_required(said_no,{'tx':TX,'phase':'APPLYING'},TX))
        said_yes=n.Refused('FAST-PATH-UNVERIFIED');said_yes.lua_result={'ok':False,'rollback_required':True}
        self.assertTrue(n.lua_rollback_required(said_yes,{},TX))
        self.assertTrue(n.lua_rollback_required(OSError('attestation failed after ok'),{'tx':TX,'phase':'APPLYING'},TX))

    def test_instant_manual_consults_the_evidence_rule(self):
        source=(LIB/'native_switch.py').read_text(encoding='utf-8')
        branch=source[source.index('result=lua_instant_switch(backend'):source.index('with control_lock(RUNTIME):\n        require_control_revision(control_revision)\n        journal_write(journal)')]
        self.assertIn("if lua_rollback_required(error,saved,tx) or journal.get('phase')=='HELD-ON-RESERVE':",branch)
        self.assertNotIn("(getattr(error,'lua_result',None) or {}).get('rollback_required')",branch)


class StopDurableLatchTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.path=Path(folder.name)
        for module,name in ((control,'RUNTIME'),(control,'PERSIST'),(agent,'RUNTIME'),(agent,'PERSIST')):
            active=patch.object(module,name,self.path);active.start();self.addCleanup(active.stop)

    def test_a_failed_volatile_pair_write_still_writes_the_durable_latch(self):
        # F-26: the RAM write of pair-auto-control.json fails; the revision is rotated and native-stop.json written anyway.
        agent.atomic_json(self.path/'pair-auto-control.json',{'mode':'on','revision':'r'*32,'time':1.0,'id':'c'*32})
        real=control.atomic_json
        def failing(path,value):
            if path.name=='pair-auto-control.json':raise OSError(28,'ENOSPC')
            return real(path,value)
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'),patch.object(control,'atomic_json',side_effect=failing):
            reply=control.stop(runtime=self.path,persist=self.path,request_source='manual')
        self.assertTrue(reply['queued']);self.assertIs(reply.get('pair_intent_unverified'),True)
        latch=agent.read_json(self.path/'native-stop.json')
        self.assertEqual(latch['trial'],'nonce');self.assertEqual(latch['request_source'],'manual')
        self.assertTrue(re.fullmatch('[a-f0-9]{32}',agent.read_json(self.path/'auto-control-revision.json')['revision']))
        self.assertEqual(agent.read_json(self.path/'pair-auto-control.json')['mode'],'on','the RAM write really failed')
        # the same failure on a repeated Stop: already latched, still reported
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'),patch.object(control,'atomic_json',side_effect=failing):
            again=control.stop(runtime=self.path,persist=self.path)
        self.assertTrue(again['already_requested']);self.assertIs(again.get('pair_intent_unverified'),True)

    def test_a_working_volatile_write_reports_nothing_extra(self):
        agent.atomic_json(self.path/'pair-auto-control.json',{'mode':'on','revision':'r'*32,'time':1.0,'id':'c'*32})
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'):
            reply=control.stop(runtime=self.path,persist=self.path)
        self.assertEqual(reply,{'queued':True});self.assertEqual(agent.read_json(self.path/'pair-auto-control.json')['mode'],'off')


class LuaMirrorSourceTests(unittest.TestCase):
    """The Lua twins cannot run here: their source must carry the same logic as Python (not verified by execution)."""
    def read(self,name):return (LIB/'lua'/name).read_text(encoding='utf-8')

    def test_f21_instant_switch_marks_the_write_before_the_first_write(self):
        source=self.read('instant_switch.lua')
        fenced=source[source.index("run.fenced(req.revision,function()\n      -- review F-21"):source.index("-- read back by content")]
        self.assertLess(fenced.index('if #moves>0 then wrote=true end'),fenced.index('M.uci_apply(run,cursor,moves,req.names)'))
        self.assertLess(fenced.index('not M.applied(sections_of(cursor),bindings) then wrote=true end'),fenced.index('M.synchronize_process(run,cursor,bindings)'))
        self.assertNotIn("if M.uci_apply(run,cursor,moves,req.names)>0 then wrote=true end",source)

    def test_f22_manual_final_checks_live_inside_the_recovery_branch(self):
        source=self.read('manual.lua')
        start=source.index('local result=instant.switch(env.run,request,request.direction')
        body=source[start:source.index("T.manual_stamp(env,'verified')",start)]
        self.assertIn("vok,verr=pcall(function()",body)
        for check in ("refuse('POLICY-CHANGED-DURING-APPLY')","refuse('KERNEL-POLICY-UNVERIFIED')","env.backend.guard(env.backend.devices(),revision)"):
            self.assertLess(body.index(check),body.index('if result.ok~=true or not vok then'),check)
        self.assertIn("if result.rollback_required or value.phase=='HELD-ON-RESERVE' then",body)
        self.assertIn("require('rollback').rollback_counted(env,value,'TRANSACTION-FAILED')",body)

    def test_f23_uci_commands_are_dispatched_under_the_fence_and_awaited_outside(self):
        source=self.read('backend.lua')
        self.assertIn("uci_dispatch({'uci','reorder','route_policy.'..section..'='..position})",source)
        self.assertIn("uci_dispatch({'uci','commit','route_policy'})",source)
        self.assertNotIn("function() sys.command({'uci','reorder'",source);self.assertNotIn("function() sys.command({'uci','commit','route_policy'}) end",source)
        dispatch=source[source.index('local function uci_dispatch(argv)'):source.index('function B.forward_dispatch')]
        # R2-01: the wait goes through await_writer (terminate + confirmed exit, or WRITER-UNRESOLVED), never a bare sys.wait
        # R4-01: the spawn carries the status path of the flash writer record written just before it
        self.assertIn('sys.spawn(argv,{timeout=UCI_TIMEOUT,status=status})',dispatch);self.assertIn('await_writer(handle,UCI_TIMEOUT+5)',dispatch);self.assertNotIn('sys.wait(',dispatch)
        # F-24: the pair network write goes through the same bounded dispatch (record, spawn, await_writer), never sys.chunk
        net=self.read('net.lua')
        # the call is wrapped in pcall so the stage directory is cleaned up whatever the writer did (F-41 merge)
        self.assertNotIn("sys.chunk,'pair_network_write'",net);self.assertIn('pcall(env.backend.network_dispatch,argv,revision,M.WRITE_TIMEOUT)',net);self.assertIn('M.WRITE_TIMEOUT=8',net)
        network=source[source.index('function B.network_dispatch'):source.index('function B.reorder')]
        self.assertIn('record_writer(argv)',network);self.assertIn('await_writer(handle,(timeout or 5)+5)',network);self.assertNotIn('sys.wait(',network)
        self.assertIn("sys.command({'uci','commit','route_policy'},{timeout=UCI_TIMEOUT})",source)
        # every caller of backend.reorder unwraps a function result (the awaited part runs outside the lock)
        for name,marker in (('transaction.lua',"if type(result)=='function' then result=result() end"),('rollback.lua',"if type(result)=='function' then result=result() end"),
                            ('recovery.lua',"if type(result)=='function' then result=result() end"),('forward_resume.lua',"if type(result)=='function' then result=result() end")):
            self.assertIn(marker,self.read(name),name)

    def test_f25_durable_propagates_a_failed_directory_sync(self):
        source=self.read('durable.lua')
        self.assertEqual(source.count("not ops.sync_all() then error('durable: directory fsync unavailable',0) end"),3)
        self.assertIn("not M.ops.sync_all() then error('durable: directory fsync unavailable',0) end",source)
        self.assertNotIn("if not M.sync_directory(directory) then ops.sync_all() end",source)
        self.assertNotIn("if created_directory then M.sync_directory(string.match(directory,'^(.*)/[^/]+$') or '/') end",source)
        self.assertNotIn("if created and not M.sync_directory(directory) then ops.sync_all() end",source)
        self.assertNotIn("if not M.in_ram(to) and not M.sync_directory(directory) then M.ops.sync_all() end",source)

    def test_f26_lua_stop_keeps_the_durable_latch_after_a_failed_volatile_write(self):
        source=self.read('control_request.lua')
        stop=source[source.index('function M.stop(deps,arguments)'):source.index('-- failure test (fault_control)')]
        self.assertIn("local vok,verr=pcall(function()",stop)
        self.assertLess(stop.index("write_json(deps,runtime..'/pair-auto-control.json'"),stop.index("if not vok then volatile_error=verr or 'pair-intent' end"))
        self.assertIn("if volatile_error~=nil then extra.pair_intent_unverified=true end",stop)
        self.assertLess(stop.index("if volatile_error~=nil then extra.pair_intent_unverified=true end"),stop.index("write_json(deps,persist..'/native-stop.json',record)"))


if __name__=='__main__':unittest.main()
