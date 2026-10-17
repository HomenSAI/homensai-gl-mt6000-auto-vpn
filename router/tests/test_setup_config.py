import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import setup_config as setup


class SetupTests(unittest.TestCase):
    def system(self):
        return {'source':'a','target':'b','interval':30,'duration':10,'session_loss':False,
                'servers':[{'profile':'a','name':'Primary','channel':'Main','priority':1,'enabled':True},{'profile':'b','name':'Reserve','channel':'Backup','priority':2,'enabled':True}]}

    def test_system_only_writes_own_metadata_without_enabling_native(self):
        payload=setup.system_payload(self.system(),[{'id':'a'},{'id':'b'}])
        self.assertNotIn('native_enabled',payload['main'])
        self.assertEqual(payload['main']['plan_target'],'b')
        self.assertEqual(payload['servers'][0]['profile'],'a')

    def test_disabled_or_omitted_selected_profile_is_rejected(self):
        for omitted in (False,True):
            args=self.system()
            if omitted:args['servers'].pop()
            else:args['servers'][1]['enabled']=False
            with self.assertRaisesRegex(ValueError,'PRIMARY-RESERVE-DISABLED'):setup.system_payload(args,[{'id':'a'},{'id':'b'}])

    def test_unknown_same_and_duplicate_profiles_rejected(self):
        for mutation in ({'target':'a'},{'source':'unknown'}):
            args=self.system();args.update(mutation)
            with self.assertRaises(ValueError):setup.system_payload(args,[{'id':'a'},{'id':'b'}])
        args=self.system();args['servers']*=2
        with self.assertRaises(ValueError):setup.system_payload(args,[{'id':'a'},{'id':'b'}])

    def test_shell_characters_in_names_remain_data(self):
        args=self.system();args['servers'][0]['name']='$(touch example); "operator"'
        value=setup.system_payload(args,[{'id':'a'},{'id':'b'}])
        self.assertEqual(value['servers'][0]['name'],args['servers'][0]['name'])

    def test_control_chars_and_oversized_names_rejected(self):
        for name in ('bad\nname','x'*65,''):
            args=self.system();args['servers'][0]['name']=name
            with self.assertRaises(ValueError):setup.system_payload(args,[{'id':'a'},{'id':'b'}])

    def test_ranges_booleans_and_extra_settings_rejected(self):
        for key,value in (('interval',9),('duration',241),('interval',True),('session_loss','yes'),('native_enabled',True)):
            args=self.system();args[key]=value
            with self.assertRaises(ValueError):setup.system_payload(args,[{'id':'a'},{'id':'b'}])

    def test_public_channel_and_numeric_destination_supported(self):
        for chat in ('@example_channel','-1001234567','12345'):
            payload=setup.telegram_payload({'token':'','chat':chat,'enabled':True,'interval':60})
            self.assertEqual(payload['main']['telegram_chat'],chat)
            self.assertNotIn('telegram_token',payload['main'])

    def test_telegram_rejects_url_and_unsafe_parameters_before_save(self):
        for chat in ('https://example.com','@bad/name',''):
            with self.assertRaises(ValueError):setup.telegram_payload({'token':'','chat':chat,'enabled':True,'interval':60})
        with self.assertRaises(ValueError):setup.telegram_payload({'token':'secret-invalid','chat':'123','enabled':True,'interval':60})

    def test_pending_delta_is_explicit_and_arbitrary_output_is_redacted(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        args={'enabled':False,'auto_new':False,'budget_mib':1,'duration':2,'streams':1,'daily_mib':2,'busy_mbps':10}
        for output,expected in ((b'SETUP-PENDING-DELTA','SETUP-PENDING-DELTA'),(b'PRIVATE_SENTINEL','SETUP-SAVE-FAILED')):
            with patch.object(setup,'control_lock',return_value=nullcontext()),patch.object(setup.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout=output)) as run:
                answer=setup.save(args,'speed')
                self.assertFalse(answer['saved']);self.assertEqual(answer['code'],expected)
                self.assertEqual(run.call_count,1)

    def test_forgetting_the_token_deletes_only_it_and_turns_reports_off(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        with patch.object(setup,'control_lock',return_value=nullcontext()),patch.object(setup.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'OK')) as run:
            self.assertTrue(setup.save({},'forget')['saved'])
            sent=json.loads(run.call_args.kwargs['input'])
        self.assertEqual(sent,{'main':{'telegram_enabled':'0'},'servers':[],'delete':['telegram_token']})
        with patch.object(setup.subprocess,'run') as writer:
            with self.assertRaises(ValueError):setup.save({'token':'x'},'forget')
            writer.assert_not_called()

    def test_invalid_input_never_calls_writer(self):
        with patch.object(setup.subprocess,'run') as writer:
            with self.assertRaises(ValueError):setup.save({'token':'bad'},'telegram')
            writer.assert_not_called()
