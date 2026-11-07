"""Review 06.11.2026, findings F-11..F-14 (configuration, pair ownership, monitor, Telegram destination).

F-11: configuration_guard.blocked consults the durable pair ownership through the validated reader and treats an
unreadable or invalid pair record as blocking, not as "Auto off". F-12: monitor_control applies the same strict pair
check before stopping the service. F-13: the system save passes the common recovery guard inside its control lock.
F-14: the read-ACL inventory shows only a mask of the Telegram destination; the full value is a write-ACL method.
"""
from contextlib import nullcontext, redirect_stdout
from pathlib import Path
import io
import json
import sys
import types
import unittest
from unittest.mock import patch

LIB=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import agent
import configuration_guard as guard
import monitor_control as monitor
import pair_auto
import setup_config as setup

OFF={'mode':'off','revision':'r1','time':1.0}
ON={'mode':'on','revision':'r1','time':1.0,'id':'a'*32}
HELD={'phase':'HELD','id':'a'*32,'owned':['wgclient1'],'recovery_error':'PAIR-EXTERNAL-CONFIG-CHANGE'}


def pair(intent=OFF,state=None,intent_error=None,state_error=None):
    """The pair records as the validated readers answer them (or raise)."""
    stack=[patch('speed_pause.public',return_value={'active':False})]
    stack.append(patch.object(pair_auto,'intent',side_effect=intent_error) if intent_error else patch.object(pair_auto,'intent',return_value=dict(intent)))
    stack.append(patch.object(pair_auto,'read_state',side_effect=state_error) if state_error else patch.object(pair_auto,'read_state',return_value=dict(state or {})))
    return stack


class ConfigurationGuardTests(unittest.TestCase):
    def blocked(self,**context):
        patches=pair(**context)+[patch.object(guard,'journal_read',return_value={}),patch.object(guard,'read_json',return_value={})]
        for active in patches:active.start();self.addCleanup(active.stop)
        return guard.blocked({})

    def test_held_ownership_with_intent_off_blocks_every_edit(self):
        # F-11: intent off, a valid HELD ownership record, no journal: the edit must wait for Start or Stop.
        self.assertEqual(self.blocked(state=HELD),'CONFIG-STOP-AUTO-FIRST')
        for phase in ('STARTING','RUNNING','STOPPING'):
            with self.subTest(phase=phase):
                self.assertEqual(self.blocked(state=dict(HELD,phase=phase)),'CONFIG-STOP-AUTO-FIRST')

    def test_terminal_or_absent_ownership_with_intent_off_allows_the_edit(self):
        for state in ({},dict(HELD,phase='STOPPED'),dict(HELD,phase='FAILED')):
            with self.subTest(state=state.get('phase')):self.assertIsNone(self.blocked(state=state))

    def test_pair_intent_on_blocks_whatever_the_ownership_says(self):
        self.assertEqual(self.blocked(intent=ON,state={}),'CONFIG-STOP-AUTO-FIRST')

    def test_unreadable_or_invalid_pair_records_block_instead_of_counting_as_off(self):
        for context in (dict(intent_error=ValueError('PAIR-INTENT-UNVERIFIED')),dict(intent_error=OSError(5,'EIO')),
                        dict(state_error=ValueError('PAIR-STATE-UNVERIFIED')),dict(state_error=OSError(5,'EIO'))):
            with self.subTest(context=context):self.assertEqual(self.blocked(**context),'CONFIG-RECOVERY-UNVERIFIED')

    def test_pair_active_is_fail_closed_and_reads_both_records(self):
        for active in pair(state=HELD):active.start();self.addCleanup(active.stop)
        self.assertTrue(guard.pair_active())
        with patch.object(pair_auto,'intent',return_value=[]):
            with self.assertRaises(ValueError):guard.pair_active()


class MonitorStopTests(unittest.TestCase):
    def change(self,arguments,**context):
        patches=pair(**context)+[patch.object(monitor,'control_lock',return_value=nullcontext()),patch('rpc_throttle.allow',return_value=True)]
        for active in patches:active.start();self.addCleanup(active.stop)
        with patch.object(monitor.subprocess,'run',side_effect=[types.SimpleNamespace(returncode=0,stdout=b'OK'),types.SimpleNamespace(returncode=0)]) as run:
            return monitor.change(arguments),run.call_args_list

    def test_stop_is_refused_with_every_pair_state(self):
        # Owner main rule 07.11.2026: the monitor always runs. The pair state no longer matters: a stop is always refused.
        for context in (dict(intent=ON),dict(state=HELD),dict(state=dict(HELD,phase='RUNNING')),dict(state=dict(HELD,phase='STOPPED')),
                        dict(state_error=ValueError('PAIR-STATE-UNVERIFIED')),dict(state_error=OSError(5,'EIO'))):
            with self.subTest(context=context):
                answer,calls=self.change({'enabled':False},**context)
                self.assertEqual((answer['accepted'],answer['code']),(False,'MONITOR-ALWAYS-ON'));self.assertEqual(calls,[])

    def test_start_with_a_held_pair_still_works(self):
        # Starting the service is what recovers a HELD session: never refused by the pair check.
        answer,calls=self.change({'enabled':True},state=HELD)
        self.assertTrue(answer['accepted']);self.assertEqual(calls[-1].args[0][-1],'start')


class SystemSaveTests(unittest.TestCase):
    def save(self,journal=None,intent=None,**context):
        args={'source':'a','target':'b','interval':30,'duration':10,'session_loss':False,
              'servers':[{'profile':'a','name':'A','channel':'Main','priority':1,'enabled':True},{'profile':'b','name':'B','channel':'Main','priority':2,'enabled':True}]}
        def read(path,default=None):return dict(intent or {}) if path.name=='auto-control.json' else {}
        patches=pair(**context)+[patch.object(setup,'control_lock',return_value=nullcontext()),
                 patch.object(setup,'inventory',return_value={'settings':{},'profiles':[{'id':'a'},{'id':'b'}]}),
                 patch('native_switch.journal_read',return_value=dict(journal or {})),patch.object(guard,'journal_read',return_value=dict(journal or {})),
                 patch.object(agent,'read_json',side_effect=read),patch.object(guard,'read_json',side_effect=read),patch('rpc_throttle.allow',return_value=True)]
        for active in patches:active.start();self.addCleanup(active.stop)
        with patch.object(setup.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=b'OK')) as run:
            return setup.save(args,'system'),run.call_count

    def test_setup_system_refuses_queued_native_start(self):
        # F-13: a Start already queued in auto-control.json passed the system-only checks before.
        answer,calls=self.save(intent={'mode':'on','time':5.0,'trial':'t'})
        self.assertEqual(answer,{'saved':False,'code':'CONFIG-STOP-AUTO-FIRST'});self.assertEqual(calls,0)

    def test_setup_system_refuses_release_pending(self):
        answer,calls=self.save(journal={'phase':'RELEASE-PENDING','tx':'b'*32})
        self.assertEqual(answer,{'saved':False,'code':'CONFIG-STOP-AUTO-FIRST'});self.assertEqual(calls,0)

    def test_setup_system_refuses_a_held_pair_and_unreadable_pair_records(self):
        answer,calls=self.save(state=HELD)
        self.assertEqual(answer,{'saved':False,'code':'CONFIG-STOP-AUTO-FIRST'});self.assertEqual(calls,0)
        answer,calls=self.save(state_error=ValueError('PAIR-STATE-UNVERIFIED'))
        self.assertEqual(answer,{'saved':False,'code':'CONFIG-RECOVERY-UNVERIFIED'});self.assertEqual(calls,0)

    def test_setup_system_still_saves_when_nothing_is_active(self):
        answer,calls=self.save()
        self.assertTrue(answer['saved']);self.assertEqual(calls,1)


class TelegramDestinationTests(unittest.TestCase):
    RAW=('-1001234567890','@example_channel','123456789')

    def test_masked_destination_rule(self):
        # owner decision 07.11.2026: first two and last two characters around '…' (e.g. 12…89)
        self.assertEqual(agent.masked_destination('-1001234567890'),'-1…90')
        self.assertEqual(agent.masked_destination('@example_channel'),'@e…el')
        self.assertEqual(agent.masked_destination('123456789'),'12…89')
        self.assertEqual(agent.masked_destination('1234567'),'…')   # shorter than eight characters: nothing around it
        self.assertEqual(agent.masked_destination(''),'');self.assertEqual(agent.masked_destination(None),'')
        self.assertEqual(agent.masked_destination('abcdрусс'),'…')
        # the mask is never written as a destination: it means "keep the stored one" (checked in save under the lock)
        for raw in self.RAW:
            payload=setup.telegram_payload({'token':'','chat':agent.masked_destination(raw),'enabled':False,'interval':60})
            self.assertNotIn('telegram_chat',payload['main'])

    def test_inventory_never_returns_the_raw_destination_to_readers(self):
        # F-14: whichever inventory.lua answered, the Python reader masks the destination and keeps the flag.
        for raw in self.RAW:
            reply={'profiles':[],'servers':[],'settings':{'telegram_destination':raw,'telegram_configured':True}}
            with patch.object(agent,'command',return_value=json.dumps(reply).encode()):
                data=agent.inventory()
            text=json.dumps(data,ensure_ascii=True)
            self.assertNotIn(raw,text);self.assertNotIn(raw[1:],text)
            self.assertEqual(data['settings']['telegram_destination'],agent.masked_destination(raw))
            self.assertIs(data['settings']['telegram_configured'],True)
        # inventory.lua's mask is kept as it is; anything else that carries the mask character becomes '…'
        for given,expected in (('-1…90','-1…90'),('…','…'),('',''),('-100…7890','…'),('x…','…'),('<b>…</b>','…')):
            reply={'profiles':[],'servers':[],'settings':{'telegram_destination':given}}
            with patch.object(agent,'command',return_value=json.dumps(reply).encode()):
                self.assertEqual(agent.inventory()['settings']['telegram_destination'],expected,given)

    def test_inventory_lua_masks_at_the_source(self):
        # No Lua interpreter on the host: the source itself must carry the mask rule and not the raw assignment.
        source=(LIB/'inventory.lua').read_text(encoding='utf-8')
        self.assertNotIn("main.telegram_destination=s.telegram_chat or ''",source)
        self.assertIn("(head..'\\226\\128\\166'..tail)",source)
        self.assertIn("if #chat>=8 then head,tail=chat:sub(1,2),chat:sub(-2) end",source)

    def test_inventory_lua_and_agent_mask_the_same_way(self):
        # the twin rule, run with lua5.1 when it is installed (CI container): the snippet of inventory.lua itself
        import shutil,subprocess
        lua=shutil.which('lua5.1')
        if not lua:self.skipTest('needs lua5.1')
        source=(LIB/'inventory.lua').read_text(encoding='utf-8')
        start=source.index("  local chat=type(s.telegram_chat)");end=source.index('\n',source.index('  main.telegram_destination='))
        for raw in self.RAW+('1234567','12345678','@ab_cd','abcdрусс','-1','ab"cdefgh'):
            code='local s={telegram_chat=%s} local main={}\n%s\nio.write(main.telegram_destination)'%(
                '"'+''.join('\\%d'%b for b in raw.encode('utf-8'))+'"',source[start:end])
            out=subprocess.run([lua,'-e',code],capture_output=True,timeout=10)
            self.assertEqual(out.stdout.decode('utf-8'),agent.masked_destination(raw),raw)

    def saved(self,arguments,stored,kind='telegram'):
        def option(name):return stored if name=='telegram_chat' else '123456:'+'A'*40
        with patch.object(setup,'control_lock',return_value=nullcontext()),patch('telegram_report.option',side_effect=option),\
                patch('rpc_throttle.allow',return_value=True),\
                patch.object(setup.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=b'OK')) as run:
            answer=setup.save(arguments,kind)
        return answer,[json.loads(call.kwargs['input']) for call in run.call_args_list]

    def test_the_mask_sent_back_keeps_the_stored_destination(self):
        arguments={'token':'','chat':'-1…90','enabled':True,'interval':60}
        answer,sent=self.saved(arguments,'-1001234567890')
        self.assertTrue(answer['saved']);self.assertEqual(len(sent),1)
        self.assertNotIn('telegram_chat',sent[0]['main']);self.assertEqual(sent[0]['main']['telegram_enabled'],'1')
        # the mask of another destination, a mask with nothing stored: refused without a write
        for stored in ('-1001234561234',''):
            answer,sent=self.saved(arguments,stored)
            self.assertEqual(answer,{'saved':False,'code':'TELEGRAM-DESTINATION-FORMAT'});self.assertEqual(sent,[])
        # a real destination is still written as before
        answer,sent=self.saved(dict(arguments,chat='-1001234567890'),'')
        self.assertTrue(answer['saved']);self.assertEqual(sent[0]['main']['telegram_chat'],'-1001234567890')

    def test_the_wizard_path_keeps_the_stored_destination_the_same_way(self):
        telegram={'configure':True,'token':'','chat':'-1…90','enabled':True,'interval':60,'schedule':'interval','hour':7,'weekly':True,'monthly':True,'items':'brief'}
        payload={'main':setup.telegram_payload({k:v for k,v in telegram.items() if k!='configure'})['main'],'servers':[]}
        self.assertNotIn('telegram_chat',payload['main'])
        for stored,expected in (('-1001234567890',True),('-1001234561234',False)):
            def option(name):return stored if name=='telegram_chat' else '123456:'+'A'*40
            with patch.object(setup,'control_lock',return_value=nullcontext()),patch.object(setup,'inventory',return_value={'profiles':[],'settings':{}}),\
                    patch.object(guard,'blocked',return_value=None),patch.object(setup,'onboarding_payload',return_value=payload),\
                    patch('telegram_report.option',side_effect=option),patch('rpc_throttle.allow',return_value=True),\
                    patch.object(setup.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=b'OK')) as run:
                answer=setup.save({'telegram':telegram},'onboarding')
            self.assertEqual(answer['saved'],expected,stored);self.assertEqual(run.call_count,1 if expected else 0)
            if not expected:self.assertEqual(answer['code'],'TELEGRAM-DESTINATION-FORMAT')

    def test_full_destination_is_a_write_method_only(self):
        acl=json.loads((LIB.parents[1]/'share/rpcd/acl.d/luci-app-homensai-vpn.json').read_text())['luci-app-homensai-vpn']
        self.assertIn('telegram_destination',acl['write']['ubus']['homensai-vpn'])
        self.assertNotIn('telegram_destination',acl['read']['ubus']['homensai-vpn'])
        self.assertIn('inventory',acl['read']['ubus']['homensai-vpn'])
        out=io.StringIO()
        with redirect_stdout(out):agent.rpc('list')
        self.assertIn('telegram_destination',json.loads(out.getvalue()))
        for stored,expected in (('-1001234567890',{'destination':'-1001234567890','configured':True,'masked':'-1…90'}),
                                ('',{'destination':'','configured':False,'masked':''}),
                                ('not a destination',{'destination':'','configured':False,'masked':''})):
            out=io.StringIO()
            with patch('telegram_report.option',return_value=stored),patch.object(sys,'stdin',io.TextIOWrapper(io.BytesIO(b'{}'))),redirect_stdout(out):
                agent.rpc('telegram_destination')
            self.assertEqual(json.loads(out.getvalue()),expected)
        self.assertIn("'telegram_destination'",(LIB/'lua/rpc.lua').read_text(encoding='utf-8'))


if __name__=='__main__':unittest.main()
