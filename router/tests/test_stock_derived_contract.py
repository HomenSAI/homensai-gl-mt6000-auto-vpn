"""Pinned stock bookkeeping is semantic; foreign routing changes stay visible."""
import copy,itertools,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as n,pair_auto as pair
from vendor_fixture import stamp

BINDINGS={'wgclient1':4096,'ovpnclient2':45056}


def rules():
    return [
        {'.name':'cfg1001','.anonymous':True,'.type':'rule','enabled':'1','killswitch':'1',
         'via':'wgclient1','mark':'0x1000','via_type':'wireguard','peer_id':'3','group_id':'1',
         'tunnel_id':'1001','profiles':'/etc/vpn_profiles.d/profile1001'},
        {'.name':'cfg1002','.anonymous':True,'.type':'rule','enabled':'1','killswitch':'1',
         'via':'ovpnclient2','mark':'0xb000','via_type':'openvpn','group_id':'2','client_id':'4',
         'tunnel_id':'1002','profiles':'/etc/vpn_profiles.d/profile1002'}]


def stock_data():
    rows=[{'.name':'global','.type':'policy','enabled':'1'},
          {'.name':'default','.type':'default','enabled':'0','via':'novpn'},
          {'.name':'gl_process_vpn','.type':'rule_process','enabled':'1','from_type':'process_gid',
           'from':['8000'],'via':'wgclient1','mark':'0x1000'}]+rules()
    profiles=[{'id':'wireguard:peer_3','interface':'wgclient1'},{'id':'openvpn:2_4','interface':'ovpnclient2'}]
    for profile in profiles:stamp(profile)
    return {'sections':rows,'settings':{'plan_source':profiles[0]['id'],'plan_target':profiles[1]['id'],
        'native_order_direction':'first'},'ipv6':'0','firewall_defaults':[{}]},profiles


class StockRuleOptions(unittest.TestCase):
    def test_exact_selected_no_override_literal_zero_preserves_ids_order_and_hash(self):
        old=rules();new=copy.deepcopy(old)
        for row in new:row['options_in_used']='0'
        self.assertEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))
        self.assertEqual(n.policy_order(old,BINDINGS),n.policy_order(new,BINDINGS))
        for before,after in zip(old,new):
            self.assertEqual(n.semantic_section(before,BINDINGS),n.semantic_section(after,BINDINGS))
            self.assertEqual(n.section_id(before,BINDINGS),n.section_id(after,BINDINGS))

    def test_no_binding_context_retains_zero_as_part_of_identity(self):
        old=rules();new=copy.deepcopy(old);new[0]['options_in_used']='0'
        self.assertNotEqual(n.policy_hash(old),n.policy_hash(new))
        self.assertNotEqual(n.section_id(old[0]),n.section_id(new[0]))

    def test_current_choose_and_live_order_keep_the_same_bound_identity_after_stock_write(self):
        old,profiles=stock_data();new=copy.deepcopy(old)
        for row in new['sections'][-2:]:row['options_in_used']='0'
        before=n.choose(old,profiles);after=n.choose(new,profiles)
        for key in ('source_rule','target_rule','order','hash','generic_rules','process_bindings'):
            self.assertEqual(before[key],after[key],key)
        backend=n.Linux();backend.use_process_bindings(before['process_bindings'])
        with patch.object(backend,'policy',return_value=new):self.assertEqual(backend.order(),(before['order'],before['hash']))

    def test_zero_normalization_does_not_mutate_policy_inputs(self):
        data=rules();data[0]['options_in_used']='0';saved=copy.deepcopy(data)
        n.policy_hash(data,BINDINGS);n.policy_order(data,BINDINGS);n.semantic_section(data[0],BINDINGS)
        self.assertEqual(data,saved)

    def test_existing_explicit_string_anonymous_marker_keeps_its_supported_semantics(self):
        old=rules();new=copy.deepcopy(old)
        for row in old+new:row['.anonymous']='1'
        for row in new:row['options_in_used']='0'
        self.assertEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))

    def test_wireguard_global_peer_identity_does_not_require_an_openvpn_group_anchor(self):
        old=rules();old[0].pop('group_id');new=copy.deepcopy(old);new[0]['options_in_used']='0'
        self.assertEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))

    def test_nonliteral_zero_and_one_are_never_silently_removed(self):
        base=rules()
        for value in ('1','00','false','',0,False,None,[],{}):
            changed=copy.deepcopy(base);changed[0]['options_in_used']=value
            with self.subTest(value=value):self.assertNotEqual(n.policy_hash(base,BINDINGS),n.policy_hash(changed,BINDINGS))

    def test_any_override_presence_keeps_the_options_flag_hashed(self):
        for key in ('mtu','masq','local_access'):
            for value in ('1500','0','',None):
                old=rules();old[0][key]=value;new=copy.deepcopy(old);new[0]['options_in_used']='0'
                with self.subTest(key=key,value=value):self.assertNotEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))

    def test_foreign_interface_or_wrong_bound_mark_keeps_the_flag_hashed(self):
        for change in ({'via':'wgclient3'},{'mark':'0x2000'},{'via':'ovpnclient2'},
                       {'via_type':'openvpn'},{'via_type':'autovpn'}):
            old=rules();old[0].update(change);new=copy.deepcopy(old);new[0]['options_in_used']='0'
            with self.subTest(change=change):self.assertNotEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))

    def test_named_disabled_nonrule_or_non_killswitch_rules_are_outside_the_exception(self):
        for change in ({'.anonymous':False},{'.anonymous':'true'},{'enabled':'0'},{'enabled':True},
                       {'.type':'rule_process'},{'killswitch':'0'}):
            old=rules();old[0].update(change);new=copy.deepcopy(old);new[0]['options_in_used']='0'
            with self.subTest(change=change):self.assertNotEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))

    def test_selector_constraints_are_outside_the_exception(self):
        for key,value in (('from_type','ip'),('from',['192.0.2.1']),('to_type','domain'),('to',['example.invalid']),
                          ('to_manual',['192.0.2.1']),('to_list_external',['list1'])):
            old=rules();old[0][key]=value;new=copy.deepcopy(old);new[0]['options_in_used']='0'
            with self.subTest(key=key):self.assertNotEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))

    def test_missing_or_malformed_protocol_anchors_are_outside_the_exception(self):
        for index,key,value in ((0,'peer_id',None),(0,'peer_id','not-an-id'),(0,'peer_id',3),(0,'peer_id',True),
                                (1,'group_id',None),(1,'group_id',2),(1,'client_id',None),
                                (1,'client_id',4),(1,'client_id','not-an-id')):
            old=rules()
            if value is None:old[index].pop(key,None)
            else:old[index][key]=value
            new=copy.deepcopy(old);new[index]['options_in_used']='0'
            with self.subTest(index=index,key=key,value=value):self.assertNotEqual(n.policy_hash(old,BINDINGS),n.policy_hash(new,BINDINGS))

    def test_unrelated_changes_are_visible_even_with_the_allowed_zero_flag(self):
        original=rules()
        for change in ({'mark':'0x2000'},{'peer_id':'4'},{'group_id':'5'},{'killswitch':'0'},
                       {'foreign_option':'1'},{'profiles':'/etc/vpn_profiles.d/profile2001'},
                       {'tunnel_id':'2001'},{'via':'wgclient3'}):
            changed=copy.deepcopy(original);changed[0].update(change,options_in_used='0')
            with self.subTest(change=change):self.assertNotEqual(n.policy_hash(original,BINDINGS),n.policy_hash(changed,BINDINGS))


class StockNetworkInterleaving(unittest.TestCase):
    def setUp(self):
        self.rules=[{'.name':'vpn_leak_block','.type':'rule','priority':'1000','action':'unreachable','mark':'0/0xf000'},
                    {'.name':'vpn_block_lan_leak','.type':'rule','priority':'1000','in':'br-lan','action':'unreachable'}]
        self.others=[{'.name':'lan','.type':'interface','proto':'static','ipaddr':'192.0.2.1'},
                     {'.name':'rt_vpn6','.type':'rule6','priority':'6000','lookup':'1001'},
                     {'.name':'wwan','.type':'interface','proto':'dhcp','metric':'20','mtu':'1500'}]
        self.base=[self.others[0],self.rules[0],self.others[1],self.rules[1],self.others[2]]

    def test_all_interleavings_preserve_both_subsequence_orders(self):
        expected=pair.normalized_network(self.base)
        for positions in itertools.combinations(range(5),2):
            rules_iter=iter(self.rules);other_iter=iter(self.others)
            observed=[next(rules_iter)if index in positions else next(other_iter)for index in range(5)]
            with self.subTest(positions=positions):self.assertEqual(expected,pair.normalized_network(observed))

    def test_equal_priority_ipv4_rule_order_is_not_sorted_away(self):
        changed=copy.deepcopy(self.base);changed[1],changed[3]=changed[3],changed[1]
        self.assertNotEqual(pair.normalized_network(self.base),pair.normalized_network(changed))

    def test_other_sections_keep_their_relative_order(self):
        changed=copy.deepcopy(self.base);changed[0],changed[4]=changed[4],changed[0]
        self.assertNotEqual(pair.normalized_network(self.base),pair.normalized_network(changed))

    def test_ipv6_rules_are_not_folded_into_the_ipv4_exception(self):
        changed=copy.deepcopy(self.base);changed[2],changed[4]=changed[4],changed[2]
        self.assertNotEqual(pair.normalized_network(self.base),pair.normalized_network(changed))

    def test_every_routing_option_change_stays_visible(self):
        for key,value in (('priority','1001'),('lookup','9910'),('action','lookup'),('mark','0x1000/0xf000'),
                          ('in','br-guest'),('suppress_prefixlength','0'),('invert','1'),('foreign_option','1')):
            changed=copy.deepcopy(self.base);changed[1][key]=value
            with self.subTest(key=key):self.assertNotEqual(pair.normalized_network(self.base),pair.normalized_network(changed))

    def test_interface_options_and_named_identity_remain_hashed(self):
        for change in ({'.name':'otherwan'},{'mtu':'1492'},{'metric':'21'},{'proto':'static'},{'foreign_option':'1'}):
            changed=copy.deepcopy(self.base);changed[4].update(change)
            with self.subTest(change=change):self.assertNotEqual(pair.normalized_network(self.base),pair.normalized_network(changed))

    def test_duplicates_and_unknown_sections_are_preserved_with_multiplicity(self):
        expected=pair.normalized_network(self.base)
        for row in (self.rules[0],self.others[0],{'.name':'foreign','.type':'unknown','value':'1'}):
            with self.subTest(row=row):self.assertNotEqual(expected,pair.normalized_network(self.base+[copy.deepcopy(row)]))
        duplicate=self.base+[copy.deepcopy(self.rules[0])]
        self.assertNotEqual(pair.normalized_network(duplicate),pair.normalized_network(duplicate[:-1]))

    def test_new_or_removed_ipv4_rules_are_not_treated_as_reordering(self):
        removed=copy.deepcopy(self.base);removed.pop(1)
        inserted=copy.deepcopy(self.base);inserted.append({'.name':'foreign','.type':'rule','priority':'999','lookup':'main'})
        self.assertNotEqual(pair.normalized_network(self.base),pair.normalized_network(removed))
        self.assertNotEqual(pair.normalized_network(self.base),pair.normalized_network(inserted))

    def test_network_normalization_does_not_mutate_inputs(self):
        saved=copy.deepcopy(self.base);pair.normalized_network(self.base)
        self.assertEqual(self.base,saved)

    def test_only_explicit_anonymous_generated_cfg_names_are_parser_metadata(self):
        for marker in (True,'1'):
            old=copy.deepcopy(self.base);new=copy.deepcopy(old)
            old[1].update({'.anonymous':marker,'.name':'cfg123abc'})
            new[1].update({'.anonymous':marker,'.name':'cfg456def'})
            with self.subTest(marker=marker):self.assertEqual(pair.normalized_network(old),pair.normalized_network(new))

    def test_named_or_malformed_anonymous_markers_do_not_hide_name_changes(self):
        for marker in (False,'0','true',1,None):
            old=copy.deepcopy(self.base);new=copy.deepcopy(old)
            old[1].update({'.anonymous':marker,'.name':'cfg123abc'})
            new[1].update({'.anonymous':marker,'.name':'cfg456def'})
            with self.subTest(marker=marker):self.assertNotEqual(pair.normalized_network(old),pair.normalized_network(new))
        old=copy.deepcopy(self.base);new=copy.deepcopy(old)
        old[1].update({'.anonymous':True,'.name':'operator_rule_a'})
        new[1].update({'.anonymous':True,'.name':'operator_rule_b'})
        self.assertNotEqual(pair.normalized_network(old),pair.normalized_network(new))

    def test_existing_selected_disabled_flag_exception_remains_scoped_to_the_pair(self):
        original=self.base+[{'.name':'wgclient1','.type':'interface','proto':'wgclient','disabled':'0'},
                            {'.name':'ovpnclient2','.type':'interface','proto':'ovpnclient','disabled':'0'},
                            {'.name':'otherwan','.type':'interface','proto':'dhcp','disabled':'0'}]
        managed={'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}
        changed=copy.deepcopy(original);changed[-3]['disabled']='1';changed[-2]['disabled']='1'
        self.assertEqual(pair.normalized_network(original,managed),pair.normalized_network(changed,managed))
        changed[-1]['disabled']='1'
        self.assertNotEqual(pair.normalized_network(original,managed),pair.normalized_network(changed,managed))


if __name__=='__main__':unittest.main()
