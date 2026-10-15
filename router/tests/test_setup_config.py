import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import setup_config as setup


class SetupTests(unittest.TestCase):
    def system(self):
        return {'source':'a','target':'b','interval':30,'duration':10,'session_loss':False,
                'servers':[{'profile':'a','name':'Primary','channel':'Main','priority':1,'enabled':True}]}

    def test_system_only_writes_own_metadata_without_enabling_native(self):
        payload=setup.system_payload(self.system(),[{'id':'a'},{'id':'b'}])
        self.assertNotIn('native_enabled',payload['main'])
        self.assertEqual(payload['main']['plan_target'],'b')
        self.assertEqual(payload['servers'][0]['profile'],'a')

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

    def test_invalid_input_never_calls_writer(self):
        with patch.object(setup.subprocess,'run') as writer:
            with self.assertRaises(ValueError):setup.save({'token':'bad'},'telegram')
            writer.assert_not_called()
