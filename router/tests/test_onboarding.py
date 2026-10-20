"""First-run transaction boundaries; no router or host configuration access."""
import copy
from contextlib import contextmanager, nullcontext
import json
from pathlib import Path
import subprocess
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import setup_config as setup
import configuration_guard as guard
import recovery_settings


def arguments():
    return {
        'system':{'defer_pair':False,'source':'a','target':'b','duration':17,'session_loss':True,
                  'servers':[{'profile':name,'name':'Server '+name,'channel':'Channel '+name,
                              'priority':index+3,'enabled':True} for index,name in enumerate('ab')]},
        'monitor':{'interval':42,'checkpoint':1200,'probe_limit':23,'planning_enabled':True},
        'recovery':dict(recovery_settings.DEFAULTS,failures=5,return_policy='hold_reserve'),
        'speed':{'enabled':False,'auto_new':True,'budget_mib':12,'duration':9,'streams':3,
                 'daily_mib':256,'busy_mbps':18},
        'telegram':{'configure':False},
        'appearance':{'language':'ru','design':'c','theme':'dark'}}


class OnboardingTests(unittest.TestCase):
    def payload(self,args=None,profiles=None):
        return setup.onboarding_payload(arguments() if args is None else args,
                                        [{'id':'a'},{'id':'b'}] if profiles is None else profiles)

    def test_complete_transaction_has_all_supported_preferences_without_runtime_actions(self):
        payload=self.payload();main=payload['main']
        expected={'plan_source':'a','plan_target':'b','interval':'42','native_duration':'17',
                  'native_session_loss':'1','setup_complete':'1','checkpoint':'1200','probe_limit':'23',
                  'plan_enabled':'1','appearance_language':'ru','appearance_design':'c','appearance_theme':'dark',
                  'onboarding_version':'1','onboarding_complete':'1','onboarding_pair_deferred':'0'}
        for key,value in expected.items():self.assertEqual(main[key],value,key)
        for key,value in arguments()['speed'].items():
            self.assertEqual(main['speed_'+key],str(int(value)) if type(value) is bool else str(value))
        for key,value in arguments()['recovery'].items():self.assertEqual(main['recovery_'+key],str(value))
        self.assertEqual(len(payload['servers']),2)
        self.assertFalse({'terms_version','terms_time','enabled','native_enabled','native_until','native_trial'} & set(main))
        self.assertFalse(any(key.startswith('telegram_') for key in main))
        self.assertNotIn('delete',payload)

    def test_defer_zero_or_one_profile_never_manufactures_pair_or_legacy_completion(self):
        for count in (0,1):
            args=arguments();args['system'].update(defer_pair=True,source='',target='')
            args['system']['servers']=args['system']['servers'][:count]
            args['monitor']['planning_enabled']=False
            main=self.payload(args,[{'id':'a'}][:count])['main']
            self.assertEqual(main['onboarding_pair_deferred'],'1')
            self.assertEqual(main['plan_enabled'],'0')
            self.assertFalse({'plan_source','plan_target','setup_complete'} & set(main))
        for change in ({'source':'a'},{'target':'b'}):
            bad=copy.deepcopy(args);bad['system'].update(change)
            with self.assertRaisesRegex(ValueError,'PAIR-DEFERRED'):self.payload(bad,[{'id':'a'}])
        args['monitor']['planning_enabled']=True
        with self.assertRaisesRegex(ValueError,'PAIR-DEFERRED'):self.payload(args,[{'id':'a'}])

    def test_telegram_keep_is_exact_and_optional_disabled_destination_is_supported(self):
        args=arguments();args['telegram']={'configure':False,'token':''}
        with self.assertRaisesRegex(ValueError,'TELEGRAM-FIELDS'):self.payload(args)
        args['telegram']={'configure':True,'token':'','chat':'','enabled':False,'interval':75,
                          'schedule':'daily','hour':8,'weekly':False,'monthly':True,'items':'servers,traffic'}
        main=self.payload(args)['main']
        self.assertEqual(main['telegram_chat'],'');self.assertEqual(main['telegram_enabled'],'0')
        self.assertEqual(main['telegram_items'],'servers,traffic')
        self.assertNotIn('telegram_token',main)
        args['telegram']['token']='123456:'+'X'*30
        with self.assertRaisesRegex(ValueError,'DESTINATION'):self.payload(args)

    def test_extra_fields_cannot_accept_terms_or_enable_auto_in_any_branch(self):
        for branch in ('system','monitor','recovery','speed','telegram','appearance'):
            for key in ('terms_version','native_enabled'):
                args=arguments();args[branch][key]='1'
                with self.subTest(branch=branch,key=key),self.assertRaises(ValueError):self.payload(args)
        args=arguments();args['terms']={'version':'1'}
        with self.assertRaisesRegex(ValueError,'ONBOARDING-FIELDS'):self.payload(args)

    def test_expanded_unicode_payload_is_refused_before_writer(self):
        args=arguments();args['system']['defer_pair']=True;args['system']['source']='';args['system']['target']=''
        args['monitor']['planning_enabled']=False
        args['system']['servers']=[{'profile':str(index),'name':'Имя'*21,'channel':'Канал'*12,
                                    'priority':index+1,'enabled':True} for index in range(200)]
        with self.assertRaisesRegex(ValueError,'ONBOARDING-TOO-LARGE'):
            self.payload(args,[{'id':str(index)} for index in range(200)])

    def test_profile_snapshot_validation_and_only_writer_are_inside_same_lock(self):
        entered=[]
        @contextmanager
        def lock():
            entered.append(True)
            try:yield
            finally:entered.pop()
        def inventory():
            self.assertEqual(entered,[True]);return {'profiles':[{'id':'a'},{'id':'b'}],'settings':{}}
        def writer(*args,**kwargs):
            self.assertEqual(entered,[True]);self.assertEqual(len(args[0]),2)
            self.assertEqual(args[0][1],'/usr/lib/homensai-vpn/setup_save.lua')
            data=json.loads(kwargs['input']);self.assertEqual(data['main']['onboarding_complete'],'1')
            return SimpleNamespace(returncode=0,stdout=b'OK')
        with patch.object(setup,'control_lock',side_effect=lock),patch.object(setup,'inventory',side_effect=inventory),\
                patch.object(guard,'blocked',return_value=None),patch('rpc_throttle.allow',return_value=True),\
                patch.object(setup.subprocess,'run',side_effect=writer) as run:
            result=setup.save(arguments(),'onboarding')
        self.assertTrue(result['saved']);self.assertTrue(result['onboarding_complete']);self.assertEqual(run.call_count,1)

    def test_failed_acknowledgement_never_claims_completion_or_returns_child_output(self):
        for response in (SimpleNamespace(returncode=0,stdout=b''),SimpleNamespace(returncode=1,stdout=b'PRIVATE_SENTINEL'),
                         SimpleNamespace(returncode=1,stdout=b'SETUP-SAVE-UNCONFIRMED'),
                         subprocess.TimeoutExpired('lua',10)):
            with patch.object(setup,'control_lock',return_value=nullcontext()),\
                    patch.object(setup,'inventory',return_value={'profiles':[{'id':'a'},{'id':'b'}],'settings':{}}),\
                    patch.object(guard,'blocked',return_value=None),patch('rpc_throttle.allow',return_value=True),\
                    patch.object(setup.subprocess,'run',side_effect=response if isinstance(response,Exception) else None,
                                 return_value=response) as run:
                result=setup.save(arguments(),'onboarding')
            self.assertEqual(result,{'saved':False,'code':'SETUP-SAVE-UNCONFIRMED'});self.assertEqual(run.call_count,1)

    def test_malformed_guard_json_fails_closed_for_all_edit_callers(self):
        for bad in ([],True,'broken',None):
            for journal,state,intent in ((bad,{},{}),({},bad,{}),({},{},bad)):
                with patch.object(guard,'journal_read',return_value=journal),patch.object(guard,'read_json',side_effect=[state,intent]):
                    self.assertEqual(guard.blocked({}),'CONFIG-RECOVERY-UNVERIFIED')

    def test_rpc_and_acl_expose_aggregate_without_raw_uci_permission(self):
        import agent
        import io
        from contextlib import redirect_stdout
        output=io.StringIO()
        with redirect_stdout(output):agent.rpc('list')
        self.assertEqual(set(json.loads(output.getvalue())['setup_onboarding']),set(arguments()))
        path=Path(__file__).resolve().parents[1]/'files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json'
        acl=json.loads(path.read_text())['luci-app-homensai-vpn']
        self.assertIn('setup_onboarding',acl['write']['ubus']['homensai-vpn'])
        self.assertNotIn('uci',acl['write']);self.assertNotIn('setup_onboarding',acl['read']['ubus']['homensai-vpn'])

    @unittest.skipUnless(shutil.which('lua5.1'),'Lua 5.1 runtime absent')
    def test_inventory_completion_requires_own_current_marker_and_never_emits_token(self):
        root=Path(__file__).resolve().parents[1]
        fixture=(root/'tests/test_inventory.lua').read_text()
        for version,complete,expected in (('', '', False),('1','0',False),('2','1',False),('1','1',True)):
            own=("['.type']='main',enabled='1',setup_complete='1',onboarding_version='"+version+
                 "',onboarding_complete='"+complete+"',appearance_language='ru',appearance_design='b',"+
                 "appearance_theme='dark',telegram_token='PRIVATE_SECRET_SENTINEL',telegram_chat='12345'")
            script=fixture.replace("['.type']='main',enabled='1'",own)
            result=subprocess.run([shutil.which('lua5.1'),'-',str(root/'files/usr/lib/homensai-vpn/inventory.lua')],
                                  input=script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=True)
            self.assertNotIn(b'PRIVATE_SECRET_SENTINEL',result.stdout)
            settings=json.loads(result.stdout)['settings']
            self.assertIs(settings['setup_complete'],True)
            self.assertIs(settings['onboarding_complete'],expected)
            self.assertEqual(settings['appearance_language'],'ru')
            self.assertEqual(settings['appearance_design'],'b')
            self.assertEqual(settings['appearance_theme'],'dark')


if __name__=='__main__':unittest.main()
