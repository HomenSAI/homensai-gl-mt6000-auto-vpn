import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import kernel_policy as k,native_switch as n
from vendor_fixture import stamp


def fixture(reserve_first=False):
    profiles=[stamp({'id':'wireguard:peer_2002','interface':'wgclient1'}),stamp({'id':'openvpn:40354_2020','interface':'ovpnclient2'})]
    rules=[{'.name':'s','.type':'rule','enabled':'1','killswitch':'1','via':'wgclient1','mark':'0x1000','tunnel_id':'5841'},
           {'.name':'t','.type':'rule','enabled':'1','killswitch':'1','via':'ovpnclient2','mark':'0xb000','tunnel_id':'4192'}]
    if reserve_first:rules.reverse()
    policy={'sections':[{'.name':'global','.type':'policy','enabled':'1'},{'.name':'default','.type':'default','enabled':'0'}]+rules,
            'ipv6':'0','settings':{'plan_source':profiles[0]['id'],'plan_target':profiles[1]['id'],'native_order_direction':'first'}}
    selection=n.choose(policy,profiles)
    for role,value,table in (('source',4096,'1001'),('target',45056,'1012')):
        selection[role]['kernel_binding']={'code':None,'mark':value,'table':table,'device':selection[role]['interface'],'ifindex':10 if role=='source' else 11}
    chains=['PREROUTING','VPN_PREROUTING_HOOK','vpn_in_new_mark','wan_in_new_mark','ROUTE_POLICY','PORTAL_TTL','TUNNEL5841_ROUTE_POLICY','TUNNEL4192_ROUTE_POLICY']
    lines=['*mangle']+[':'+chain+(' ACCEPT' if chain=='PREROUTING' else ' -')+' [0:0]' for chain in chains]
    lines+=['-A PREROUTING -j PORTAL_TTL','-A PREROUTING -j VPN_PREROUTING_HOOK',
            '-A VPN_PREROUTING_HOOK -j vpn_in_new_mark','-A VPN_PREROUTING_HOOK -j wan_in_new_mark','-A VPN_PREROUTING_HOOK -i br-lan -j ROUTE_POLICY',
            '-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000',
            '-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN']
    for rule in rules:lines+=['-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL'+rule['tunnel_id']+'_ROUTE_POLICY']
    for rule in rules:
        chain='TUNNEL'+rule['tunnel_id']+'_ROUTE_POLICY'
        lines+=['-A '+chain+' -m comment --comment "TUNNEL'+rule['tunnel_id']+' rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark '+rule['mark']+'/0xf000',
                '-A '+chain+' -m mark --mark 0x0/0xf000 -j DROP']
    lines+=['COMMIT']
    ip_rules=[{'priority':6000,'src':'all','fwmark':'0x1000','fwmask':'0xf000','table':'1001'},
              {'priority':6000,'src':'all','fwmark':'0xb000','fwmask':'0xf000','table':'1012'}]
    return policy,selection,'\n'.join(lines)+'\n',ip_rules


def network_fixture(selection):
    rows=[]
    for key in ('source','target'):
        profile=selection[key];name=profile['interface'];wireguard=name.startswith('wgclient');index=int(name[-1])
        mark=((1 if wireguard else 10)+index-1)<<12;table=str((1000 if wireguard else 1010)+index)
        rows+=[{'.name':name,'.type':'interface','proto':'wgclient' if wireguard else 'ovpnclient',
                'config':profile['id'].split(':',1)[1],'ip4table':table,'auto':'0','disabled':'0'},
               {'.name':'rt_'+name,'.type':'rule','mark':hex(mark)+'/0xf000','lookup':table,'priority':'6000'}]
    return rows


class KernelPolicyTests(unittest.TestCase):
    def test_pinned_fw3_mark_graph_attests_each_actual_configured_direction(self):
        for reserve in (False,True):
            data,selection,mangle,rules=fixture(reserve)
            result=k.attest(data,selection,mangle,rules)
            self.assertTrue(result['verified']);self.assertEqual(result['role'],'target' if reserve else 'source')
            self.assertIn('no external-client proof',result['scope'])

    def reject(self,change):
        data,selection,mangle,rules=fixture();changed=change(mangle)
        with self.assertRaises(ValueError):k.attest(data,selection,changed,rules)

    def test_live_failure_shape_no_packetmark_chains_is_not_tunnel_selection(self):
        self.reject(lambda _: '*mangle\n:PREROUTING ACCEPT [100:1000]\n:PORTAL_TTL - [0:0]\nCOMMIT\n')
        data,selection,_,rules=fixture()
        absent='*mangle\n:PREROUTING ACCEPT [100:1000]\n:PORTAL_TTL - [0:0]\nCOMMIT\n'
        self.assertTrue(k.missing_only(data,selection,absent,rules),'only the understood wholly absent stock graph is repairable')

    def test_foreign_or_partial_graph_is_never_classified_as_missing(self):
        data,selection,mangle,rules=fixture()
        self.assertFalse(k.missing_only(data,selection,mangle,rules))
        partial='*mangle\n:PREROUTING ACCEPT [0:0]\n:ROUTE_POLICY - [0:0]\nCOMMIT\n'
        self.assertFalse(k.missing_only(data,selection,partial,rules))
        foreign='*mangle\n:PREROUTING ACCEPT [0:0]\n-A PREROUTING -j MARK --set-xmark 0x8000/0xf000\nCOMMIT\n'
        self.assertFalse(k.missing_only(data,selection,foreign,rules))
    def test_missing_prerouting_jump_refused(self):self.reject(lambda s:s.replace('-A PREROUTING -j VPN_PREROUTING_HOOK\n',''))
    def test_missing_lan_mount_refused(self):self.reject(lambda s:s.replace('-i br-lan -j ROUTE_POLICY','-i guest -j ROUTE_POLICY'))
    def test_changed_generic_order_refused(self):
        self.reject(lambda s:s.replace('! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY','! --dst-type LOCAL -j TEMP').replace('! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY','! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY').replace('-j TEMP','-j TUNNEL4192_ROUTE_POLICY'))
    def test_wrong_mark_refused(self):self.reject(lambda s:s.replace('--set-xmark 0x1000/0xf000','--set-xmark 0xb000/0xf000'))
    def test_wrong_mask_refused(self):self.reject(lambda s:s.replace('--set-xmark 0x1000/0xf000','--set-xmark 0x1000/0xff00'))
    def test_conditional_mark_is_not_generic(self):self.reject(lambda s:s.replace('-j MARK --set-xmark 0x1000','-i guest -j MARK --set-xmark 0x1000'))
    def test_prerouting_override_refused(self):self.reject(lambda s:s.replace('COMMIT','-A PREROUTING -j MARK --set-xmark 0xb000/0xf000\nCOMMIT'))
    def test_missing_killswitch_fallback_refused(self):self.reject(lambda s:s.replace('-A TUNNEL5841_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP\n',''))
    def test_lan_ingress_connmark_override_refused(self):
        self.reject(lambda s:s.replace('COMMIT','-A vpn_in_new_mark -i br-lan -j CONNMARK --set-xmark 0xb000/0xf000\nCOMMIT'))
        self.reject(lambda s:s.replace('COMMIT','-A vpn_in_new_mark ! -i eth0 -j CONNMARK --set-xmark 0xb000/0xf000\nCOMMIT'))
    def test_duplicate_rule_tables_masks_or_selectors_cannot_attest(self):
        for change in (lambda r:r.append(copy.deepcopy(r[0])),lambda r:r[0].update(table='1012'),
                       lambda r:r[0].update(fwmask='0xff00'),lambda r:r[0].update(iif='lo'),lambda r:r[0].update(priority=10000),
                       lambda r:r[0].update(uidrange='0-0'),lambda r:r[0].update(tos='0x10'),lambda r:r[0].update({'not':None})):
            data,selection,mangle,rules=fixture();change(rules)
            with self.assertRaises(ValueError):k.attest(data,selection,mangle,rules)

    def test_earlier_lan_blackhole_or_foreign_lookup_cannot_be_hidden_by_bound_router_probes(self):
        for prior in ({'priority':5000,'src':'all','iif':'br-lan','action':'blackhole'},
                      {'priority':5000,'src':'all','table':'9999'}):
            data,selection,mangle,rules=fixture();rules.insert(0,prior)
            with self.assertRaises(ValueError):k.attest(data,selection,mangle,rules)
        data,selection,mangle,rules=fixture()
        rules[:0]=[{'priority':0,'src':'all','table':'local'},{'priority':1,'src':'all','iif':'lo','table':'16800'},
                   {'priority':800,'src':'all','table':'9910','suppress_prefixlen':0}]
        self.assertTrue(k.attest(data,selection,mangle,rules)['verified'])

    def test_unparsed_or_incomplete_data_is_not_accepted(self):
        for value in ('',None,'*mangle\n:PREROUTING ACCEPT [0:0]\n','*mangle\nCOMMIT\n-A PREROUTING -j ROUTE_POLICY'):
            with self.assertRaises(ValueError):k.parse_mangle(value)

    def test_counter_changes_do_not_change_mark_graph(self):
        _,_,mangle,_=fixture();self.assertEqual(k.parse_mangle(mangle),k.parse_mangle(mangle.replace('[0:0]','[1234:100000]')))

    def test_never_up_primary_binding_is_proven_by_exact_pinned_persistent_declaration(self):
        data,selection,mangle,rules=fixture();rows=network_fixture(selection)
        selection['source'].update(code='VPN-001',dns_ok=False,https_success=0,kernel_binding={'code':'VPN-001'})
        declared=k.static_bindings(selection,rows)
        self.assertEqual(declared['source']['kernel_binding']['mark'],4096)
        self.assertEqual(declared['source']['kernel_binding']['table'],'1001')
        self.assertTrue(k.attest(data,declared,mangle,rules)['verified'])
        self.assertEqual(selection['source']['kernel_binding'],{'code':'VPN-001'},'read-only adapter cannot rewrite measured failure')

    def test_static_declaration_cannot_mask_route_drift_foreign_slot_or_profile(self):
        _,selection,_,_=fixture()
        for change in (lambda s,r:s['source'].update(kernel_binding={'code':'ROUTE-001'}),
                       lambda s,r:r[0].update(ip4table='9999'),lambda s,r:r[0].update(config='peer_9999'),
                       lambda s,r:r[1].update(mark='0xb000/0xf000'),lambda s,r:r[1].update(lookup='1012'),
                       lambda s,r:r[1].update(priority='5000'),lambda s,r:s['source'].update(interface='wgclient6')):
            chosen=copy.deepcopy(selection);rows=network_fixture(chosen);change(chosen,rows)
            with self.assertRaises(ValueError):k.static_bindings(chosen,rows)

    def test_read_only_adapter_requires_same_rules_and_policy_on_both_sides(self):
        data,selection,mangle,rules=fixture();backend=n.Linux()
        def command(args):return mangle.encode() if args[0]=='iptables-save' else json.dumps(rules).encode()
        with patch.object(backend,'policy',return_value=data),patch.object(n,'command',side_effect=command),patch.object(n,'slot_contract_verified',return_value=True),patch('pair_auto.network',return_value=network_fixture(selection)):
            self.assertTrue(backend.attest_policy(selection)['verified'])
        replies=iter([mangle.encode(),json.dumps(rules).encode(),mangle.replace('--set-xmark 0x1000','--set-xmark 0xb000').encode()])
        with patch.object(backend,'policy',return_value=data),patch.object(n,'command',side_effect=lambda args:next(replies)),patch.object(n,'slot_contract_verified',return_value=True),patch('pair_auto.network',return_value=network_fixture(selection)):
            self.assertFalse(backend.attest_policy(selection)['verified'])

    def test_adapter_refuses_unverified_stock_programs_before_accepting_formula(self):
        data,selection,_,_=fixture();backend=n.Linux()
        with patch.object(n,'slot_contract_verified',return_value=False),patch.object(backend,'policy',return_value=data),patch.object(n,'command') as command:
            self.assertFalse(backend.attest_policy(selection)['verified']);command.assert_not_called()


if __name__=='__main__':unittest.main()
