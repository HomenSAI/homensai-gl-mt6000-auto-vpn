from contextlib import nullcontext
from pathlib import Path
import copy
import json
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import priority_config as priorities
import recovery_settings as recovery
import configuration_guard as guard


def inventory():
    return {'settings':{},'profiles':[{'id':x,'name':'Server '+x,'protocol':'openvpn'} for x in 'abc'],
            'servers':[{'profile':x,'name':'Name '+x,'channel':'Main','priority':i+1,'enabled':x!='c'} for i,x in enumerate('abc')]}

class PriorityTests(unittest.TestCase):
    def test_pending_delta_failure_is_propagated_without_success(self):
        data=inventory();_,revision=priorities.snapshot(data)
        with patch.object(priorities,'control_lock',return_value=nullcontext()),patch.object(priorities,'inventory',return_value=data),patch.object(priorities,'blocked',return_value=None),patch.object(priorities.subprocess,'run',return_value=types.SimpleNamespace(returncode=1,stdout=b'SETUP-PENDING-DELTA')) as run:
            answer=priorities.apply({'ordered':['b'],'revision':revision})
            self.assertFalse(answer['saved']);self.assertEqual(answer['code'],'SETUP-PENDING-DELTA')
            self.assertEqual(run.call_count,1)

    def test_explicit_order_preserves_names_disabled_flags_and_unselected_order(self):
        data=inventory();before=copy.deepcopy(data);rows,_=priorities.proposed(data,['b'])
        self.assertEqual([r['profile'] for r in rows],['b','a','c']);self.assertEqual([r['priority'] for r in rows],[1,2,3])
        self.assertEqual(rows[-1]['enabled'],False);self.assertEqual(rows[0]['name'],'Name b');self.assertEqual(data,before)
    def test_stale_or_disabled_selection_is_rejected(self):
        for ordered in ([],['a','a'],['missing'],['c'],'abc',[{}]):
            with self.subTest(ordered=ordered),self.assertRaises(ValueError):priorities.proposed(inventory(),ordered)
    def test_revision_changes_on_priority_name_channel_enable_or_profile_changes(self):
        original=inventory();_,revision=priorities.snapshot(original)
        for key,value in (('priority',99),('name','Changed'),('channel','Other'),('enabled',False)):
            changed=copy.deepcopy(original);changed['servers'][0][key]=value
            self.assertNotEqual(priorities.snapshot(changed)[1],revision)
    def test_preview_cannot_write(self):
        with patch.object(priorities,'inventory',return_value=inventory()),patch.object(priorities.subprocess,'run') as run:
            result=priorities.preview({'ordered':['b']})
        self.assertTrue(result['accepted']);run.assert_not_called()
    def test_apply_only_own_uci_and_no_route_or_service_commands(self):
        data=inventory();revision=priorities.snapshot(data)[1]
        with patch.object(priorities,'inventory',return_value=data),patch.object(priorities,'blocked',return_value=None),patch.object(priorities,'control_lock',return_value=nullcontext()),patch.object(priorities.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=b'OK')) as run:
            result=priorities.apply({'ordered':['b'],'revision':revision})
        self.assertTrue(result['saved']);self.assertFalse(result['route_changed']);self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0],['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'])
        self.assertEqual(json.loads(run.call_args.kwargs['input'])['main'],{})
    def test_changed_review_or_active_auto_never_writes(self):
        for reason,revision in ((None,'0'*64),('CONFIG-STOP-AUTO-FIRST',priorities.snapshot(inventory())[1])):
            with patch.object(priorities,'inventory',return_value=inventory()),patch.object(priorities,'blocked',return_value=reason),patch.object(priorities,'control_lock',return_value=nullcontext()),patch.object(priorities.subprocess,'run') as run:
                result=priorities.apply({'ordered':['b'],'revision':revision})
            self.assertFalse(result['saved']);run.assert_not_called()

class RecoveryTests(unittest.TestCase):
    def test_owner_defaults_and_atomic_extended_settings(self):
        self.assertEqual(recovery.normalized({}),{'failures':3,'successes':2,'cooldown':60,'min_dwell':60,
            'return_policy':'healthy_primary','primary_successes':2,'primary_stable':30,'attempt_limit':3,'attempt_window':15})
        values=dict(recovery.DEFAULTS,interval=10,attempt_limit=4,attempt_window=8)
        saved=recovery.payload(values)['main']
        self.assertEqual((saved['interval'],saved['recovery_attempt_limit'],saved['recovery_attempt_window']),('10','4','8'))
        self.assertNotIn('native_enabled',saved)
        legacy={k:v for k,v in recovery.DEFAULTS.items()if k not in('attempt_limit','attempt_window')}
        old=recovery.payload(legacy)['main']
        self.assertNotIn('recovery_attempt_limit',old);self.assertNotIn('recovery_attempt_window',old)
        for value in (9,301,True,'10'):
            with self.assertRaises(ValueError):recovery.payload(dict(values,interval=value))
        for bad in (True,'bad','999',0):
            policy=recovery.normalized({'recovery_attempt_limit':bad,'recovery_attempt_window':bad})
            self.assertEqual((policy['attempt_limit'],policy['attempt_window']),(3,15))

    def test_only_supported_bounded_fields(self):
        result=recovery.payload(dict(recovery.DEFAULTS));self.assertEqual(result['servers'],[])
        self.assertNotIn('native_enabled',result['main'])
        for key,(lo,hi) in recovery.RANGES.items():
            for value in (lo-1,hi+1,True,'3'):
                args=dict(recovery.DEFAULTS,**{key:value})
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):recovery.payload(args)
    def test_unattended_or_unknown_return_modes_rejected(self):
        for args in (dict(recovery.DEFAULTS,return_policy='direct_wan'),dict(recovery.DEFAULTS,reboot_auto=True)):
            with self.assertRaises(ValueError):recovery.payload(args)
    def test_fingerprint_changes_with_recovery_settings(self):
        self.assertNotEqual(recovery.fingerprint({}),recovery.fingerprint({'recovery_failures':'5'}))
    def test_config_guard_blocks_corrupt_or_unknown_transactions(self):
        with patch.object(guard,'journal_read',side_effect=guard.Refused('JOURNAL-INTEGRITY-FAILED')):
            self.assertEqual(guard.blocked({}),'CONFIG-RECOVERY-UNVERIFIED')
        with patch.object(guard,'journal_read',return_value={'phase':'UNKNOWN'}),patch.object(guard,'read_json',return_value={}):
            self.assertEqual(guard.blocked({}),'CONFIG-STOP-AUTO-FIRST')

class MonitorPreferencesTests(unittest.TestCase):
    def test_only_bounded_own_monitor_preferences(self):
        import setup_config
        values={'interval':30,'checkpoint':900,'probe_limit':16,'planning_enabled':False}
        payload=setup_config.monitor_payload(values)
        self.assertNotIn('native_enabled',payload['main']);self.assertNotIn('enabled',payload['main'])
        for mutation in ({'checkpoint':299},{'probe_limit':17},{'interval':True},{'planning_enabled':'yes'},{'native_enabled':True}):
            with self.assertRaises(ValueError):setup_config.monitor_payload(dict(values,**mutation))
    def test_application_acl_never_grants_raw_uci_access(self):
        root=Path(__file__).resolve().parents[1]/'files'
        acl=json.loads((root/'usr/share/rpcd/acl.d/luci-app-homensai-vpn.json').read_text())['luci-app-homensai-vpn']
        self.assertNotIn('uci',acl['read']);self.assertNotIn('uci',acl['write'])
