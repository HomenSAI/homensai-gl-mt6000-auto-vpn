import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as n
import process_policy as p

BINDINGS={'wgclient1':4096,'ovpnclient1':40960}
def sections():
    return [{'.name':'gl_process_vpn','.type':'rule_process','enabled':'1','from_type':'process_gid','from':['8000'],'via':'wgclient1','mark':'0x1000'},
            {'.name':'cfg1','.anonymous':True,'.type':'rule','enabled':'1','via':'wgclient1','mark':'0x1000','killswitch':'1'},
            {'.name':'cfg2','.anonymous':True,'.type':'rule','enabled':'1','via':'ovpnclient1','mark':'0xa000','killswitch':'1'}]

class Tests(unittest.TestCase):
    def test_only_pair_derived_binding_changes_preserve_context_hash(self):
        a=sections();b=copy.deepcopy(a);b[1:]=reversed(b[1:]);b[0].update(via='ovpnclient1',mark='0xa000')
        self.assertEqual(n.policy_hash(a,BINDINGS),n.policy_hash(b,BINDINGS))
        self.assertNotEqual(n.policy_hash(a),n.policy_hash(b))
        self.assertNotEqual(n.policy_order(a),n.policy_order(b))
        self.assertEqual(p.selected_bindings(a,tuple(BINDINGS)),BINDINGS)

    def test_foreign_interface_mark_and_static_process_fields_remain_visible(self):
        original=sections();wanted=n.policy_hash(original,BINDINGS)
        for change in ({'via':'wgclient2','mark':'0x2000'},{'mark':'0xa000'},{'enabled':'0'},{'from':['0']},{'from_type':'ip'}):
            changed=copy.deepcopy(original);changed[0].update(change)
            self.assertNotEqual(wanted,n.policy_hash(changed,BINDINGS))
        for change in ({'via':'wgclient2'},{'mark':'0xa000'}):
            changed=sections();changed[0].update(change)
            with self.assertRaises(ValueError):p.selected_bindings(changed,tuple(BINDINGS))

    def test_exact_context_and_generic_fields_are_bound(self):
        a=sections();b=copy.deepcopy(a);b[2]['killswitch']='0'
        self.assertNotEqual(n.policy_hash(a,BINDINGS),n.policy_hash(b,BINDINGS))
        self.assertNotEqual(n.policy_hash(a,BINDINGS),n.policy_hash(a,dict(BINDINGS,ovpnclient1=8192)))

    def test_regenerated_anonymous_names_do_not_change_semantics(self):
        a=sections();b=copy.deepcopy(a);b[1]['.name']='cfgNEWA';b[2]['.name']='cfgNEWB'
        self.assertEqual(n.policy_hash(a,BINDINGS),n.policy_hash(b,BINDINGS));self.assertEqual(n.policy_order(a),n.policy_order(b))

    def test_after_apply_binding_must_match_first_enabled_vpn_rule(self):
        a=sections();self.assertTrue(p.applied(a,BINDINGS));a[1:]=reversed(a[1:]);self.assertFalse(p.applied(a,BINDINGS))
        a[0].update(via='ovpnclient1',mark='40960');self.assertTrue(p.applied(a,BINDINGS))
        backend=n.Linux();backend.use_process_bindings(BINDINGS)
        with patch.object(n,'command'),patch.object(backend,'policy',return_value={'sections':a}):backend.apply()
        a[0]['via']='wgclient1'
        with patch.object(n,'command'),patch.object(backend,'policy',return_value={'sections':a}),self.assertRaises(n.Refused):backend.apply()

    def test_invalid_recovery_context_cannot_be_loaded(self):
        for value in ({},[],{'wgclient1':True,'ovpnclient1':40960},{'wgclient1':4096,'ovpnclient1':4096},{'wgclient1':4096,'novpn':40960},{'wgclient1':4096,'ovpnclient1':10**100}):
            with self.assertRaises(n.Refused):n.Linux().use_process_bindings(value)

    def test_known_stale_process_binding_is_synchronized_before_stock_apply(self):
        stale=sections();stale[1:]=reversed(stale[1:])
        after=copy.deepcopy(stale);after[0].update(via='ovpnclient1',mark='0xa000')
        backend=n.Linux();backend.use_process_bindings(BINDINGS)
        with patch.object(n,'command')as command,patch.object(backend,'policy',side_effect=[{'sections':stale},{'sections':after}]):backend.apply()
        calls=command.call_args_list
        self.assertEqual(calls[0].args[0][:2],['lua','-e'])
        self.assertEqual(calls[1].args[0],['/usr/bin/rtp2.sh','not_reload_network'])
        self.assertTrue(p.applied(after,BINDINGS))
        self.assertEqual(n.policy_hash(stale,BINDINGS),n.policy_hash(after,BINDINGS))

    def test_sync_never_retargets_a_foreign_process_or_generic_rule(self):
        for change in({'via':'wgclient2','mark':'0x2000'},{'via':'wgclient1','mark':'0xa000'},{'from_type':'ip'}):
            rows=sections();rows[1:]=reversed(rows[1:]);rows[0].update(change)
            with self.assertRaises(ValueError):p.synchronization_script(rows,BINDINGS,'/tmp/test-stage')
        rows=sections();rows[1:]=reversed(rows[1:]);rows[1].update(via='wgclient2',mark='0x2000')
        with self.assertRaises(ValueError):p.synchronization_script(rows,BINDINGS,'/tmp/test-stage')

    def test_aligned_or_absent_owned_process_context_requires_no_write(self):
        self.assertIsNone(p.synchronization_script(sections(),BINDINGS,'/tmp/test-stage'))
        self.assertIsNone(p.synchronization_script(sections(),None,'/tmp/test-stage'))

    def test_recovery_rehydrates_exact_journal_context_before_reading_order(self):
        seen=[]
        class Backend:
            def use_process_bindings(self,value):seen.append(copy.deepcopy(value))
            def order(self):
                self.assert_bound();return ['original'],'hash'
            def assert_bound(self):self_test.assertEqual(seen,[BINDINGS])
        self_test=self
        journal={'phase':'ARMED','pid':None,'before':['original'],'hash':'hash','process_bindings':BINDINGS}
        with patch.object(n,'note_phase'),patch.object(n,'journal_write'):n.rollback(Backend(),journal,'TEST')
        self.assertEqual(journal['phase'],'ROLLED-BACK')

if __name__=='__main__':unittest.main()
