"""Stage 3 of the best-server pick (2.1.0-alpha3), the owner's main scenario: the PRIMARY fails, Auto moves the traffic
to the reserve (a real transaction: journal COMMITTED), the supervisor changes the failed primary's server inside its
lock and re-binds its session AND the open journal; the real return (finish_committed -> rollback, every journal write
validated) then brings the traffic back to the primary on its new profile id - no PAIR-EXTERNAL-*, no readopt.
Lua twin: tests/lua/test_auto_server_pick.lua (stage 3 tests, the same decisions)."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as n  # noqa: E402
import pair_auto as pair  # noqa: E402
import pair_policy  # noqa: E402
import server_pick as S  # noqa: E402
import test_pair_manual_directions as directions  # noqa: E402

NOW=directions.NOW;SOURCE=directions.SOURCE;TARGET=directions.TARGET
NEW='wireguard:peer_2000'
UCI=("route_policy.cfg0456cd=rule\nroute_policy.cfg0456cd.tunnel_id='4192'\nroute_policy.cfg0456cd.via_type='openvpn'\n"
     "route_policy.cfg0456cd.via='ovpnclient1'\nroute_policy.cfg0456cd.group_id='1'\nroute_policy.cfg0456cd.client_id='2'\n"
     "route_policy.cfg0456cd.profiles='/etc/vpn_profiles.d/profile4192'\nroute_policy.cfg0456cd.mark='0xb000'\n"
     "route_policy.cfg0123ab=rule\nroute_policy.cfg0123ab.tunnel_id='5841'\nroute_policy.cfg0123ab.via_type='wireguard'\nroute_policy.cfg0123ab.via='wgclient1'\n"
     "route_policy.cfg0123ab.group_id='10004'\nroute_policy.cfg0123ab.peer_id='%s'\nroute_policy.cfg0123ab.profiles='/etc/vpn_profiles.d/profile5841'\n"
     "route_policy.cfg0123ab.mark='0x1000'\n")


def sha(text):return hashlib.sha256(text.encode()).hexdigest()


class Stage3(unittest.TestCase):
    """The real transaction fixture of test_pair_manual_directions (real journal file, real child, real rollback)."""
    enterContext=directions.PairManualDirections.enterContext
    reorder=directions.PairManualDirections.reorder
    apply=directions.PairManualDirections.apply
    process=directions.PairManualDirections.process

    def setUp(self):
        directions.PairManualDirections.setUp(self)
        self.clock=[NOW]
        self.enterContext(patch('pair_manual.time.time',side_effect=lambda:self.clock[0]))  # the shared time module
        self.peer='3';self.wgconfig='peer_3';self.wg_digest='0'*64;self.staged={};self.exec=[];self.files={};self.logs=[];self.ready=[]
        self.healthy={SOURCE:False,TARGET:True}
        self.backend.health.side_effect=lambda identifier:self.healthy.get(identifier)
        self.backend.recovery_ready.side_effect=lambda identifier,settings=None:(self.ready.append(identifier),self.healthy.get(identifier) is True)[1]
        self.io={'runtime':'/run','read':self.files.get,'write':self.write,'alive':lambda pid:False,'log':self.logs.append,'exec':self.uci}
        self.settings.update(server_pick='1',plan_source_tunnel='wireguard:wgclient1',plan_target_tunnel='openvpn:ovpnclient1')
        self.current=['s','t'];self.kernel_applied=True;self.kernel_order=None
        self.state.update(order=list(self.current),owned=[],interfaces={'wgclient1':'wgclient','ovpnclient1':'ovpnclient'},
                          network_identity=sha('net:peer_3'),protected={'route_policy':sha('rp:3'),'wireguard':'0'*64},
                          policy_roles=pair_policy.proof(self.selection))
        pair.save(self.state)
        rows=lambda:[{'.name':'wgclient1','config':self.wgconfig,'disabled':'0','proto':'wgclient','auto':'0'},
                     {'.name':'ovpnclient1','config':'1_2','disabled':'0','proto':'ovpnclient','auto':'0'}]
        self.enterContext(patch.object(pair,'SERVER_IO',self.io))
        self.enterContext(patch.object(pair,'_log',side_effect=self.logs.append))
        self.enterContext(patch.object(pair,'network',side_effect=rows))
        self.enterContext(patch.object(pair,'normalized_network',side_effect=lambda data,managed=None:sha('net:'+next(r['config'] for r in data if r['.name']=='wgclient1'))))
        self.enterContext(patch.object(pair,'configs',side_effect=lambda managed=None:{'route_policy':sha('rp:'+self.peer),'wireguard':self.wg_digest}))
        self.enterContext(patch.object(pair,'client_down',return_value=False))
        self.enterContext(patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}))
        # the return decision: the real one reads the monitor samples; here it asks the same fresh check of the
        # journal's source id that committed_recovery_decision asks (recovery_ready), then the REAL finish_committed runs
        self.decided=[]
        def decision(backend,journal,settings,samples,now,status=None,hold=None):
            self.decided.append(journal['source'])
            ready=backend.recovery_ready(journal['source'],settings) is True
            return {'action':'RESTORE-PRIMARY','reason':'PRIMARY-STABLY-RECOVERED'} if ready else {'action':'OBSERVE','reason':'CLIENT-CONFIRMED'}
        self.enterContext(patch.object(n,'committed_recovery_decision',side_effect=decision))

    def write(self,path,text):self.files[path]=text;return True

    def uci(self,argv,seconds):
        line=' '.join(argv);self.exec.append(line)
        if line=='uci -q -X show route_policy':return 0,UCI%self.peer
        if line.startswith('uci set route_policy.cfg0123ab.peer_id='):self.staged['peer']=line.rsplit('=',1)[1]
        if line.startswith('uci set network.wgclient1.config='):self.staged['config']=line.rsplit('=',1)[1]
        if argv[:2]==['sh','-c'] and argv[3]=='update_provider_config':self.wg_digest=sha('wg:'+argv[5])  # GL may rewrite wireguard
        if line=='uci commit route_policy' and 'peer' in self.staged:
            old=self.selection['source_rule'];self.peer=self.staged.pop('peer');new='s' if self.peer=='3' else 's_'+self.peer
            self.current=[new if x==old else x for x in self.current]
            if self.kernel_order is not None:self.kernel_order=[new if x==old else x for x in self.kernel_order]
            self.fingerprint='c'*64 if self.peer=='3' else sha('policy:'+self.peer)
            self.selection.update(source_rule=new,generic_rules=[new if x==old else x for x in self.selection['generic_rules']],hash=self.fingerprint)
        if line=='uci commit network' and 'config' in self.staged:
            self.wgconfig=self.staged.pop('config');self.selection['source']['id']='wireguard:'+self.wgconfig
            self.selection['source']['vendor_generation']='03'*16 if self.wgconfig!='peer_3' else self.generation
        return 0,''

    def kernel_proof(self,selection=None):
        actual=self.kernel_order if self.kernel_order is not None else self.current
        roles=pair_policy.proof(dict(copy.deepcopy(self.selection),order=list(self.current)))
        current=pair_policy.role(roles,actual)
        fingerprint=hashlib.sha256(repr((self.kernel_applied,actual if self.kernel_applied else None)).encode()).hexdigest()
        return {'verified':self.kernel_applied and actual==self.current,'repairable_missing':not self.kernel_applied,'role':current,
                'profile_id':self.selection['source']['id'] if current=='source' else TARGET,'order':list(self.current),'policy_hash':self.fingerprint,
                'time':n.time.time(),'kernel_fingerprint':fingerprint}

    def tick(self):
        with patch('failover_plan.streak',return_value=False):return pair.tick(self.backend,self.settings,self.revision)

    def published(self):return self.publish.call_args.args[0]

    def on_reserve(self):
        self.generation=self.selection['source']['vendor_generation']
        with patch('failover_plan.streak',return_value=True):
            self.assertTrue(pair.tick(self.backend,self.settings,self.revision))
        journal=n.journal_read()
        self.assertEqual(journal['phase'],'COMMITTED');self.assertEqual(self.current,['t','s']);self.assertEqual(journal['source'],SOURCE)
        self.assertIsNone(journal.get('manual_request_id'))
        self.assertTrue(self.tick());self.assertEqual((self.published()['state'],self.published()['reason']),('COMMITTED','CLIENT-CONFIRMED'))

    def request(self,**over):
        row={'time':self.clock[0],'tunnel_id':5841,'protocol':'wireguard','interface':'wgclient1','section':'cfg0123ab','from':'10004_3','to':'10004_2000',
             'group_id':'10004','profile_id':'2000','from_ms':None,'to_ms':35,'from_location':'Berlin','to_location':'Frankfurt'}
        row.update(over);self.files['/run/'+S.CHANGE]=json.dumps(row)

    def reserve_untouched(self):
        for line in self.exec:self.assertNotIn('ovpnclient1',line);self.assertNotIn('cfg0456cd.',line)

    def no_readopt(self):
        self.assertFalse((self.runtime/'pair-readopt.json').exists());self.assertEqual(pair.read_state()['id'],self.state['id'])
        self.assertEqual(pair.intent()['id'],self.state['id'])

    def test_primary_server_changed_on_the_reserve_and_the_return_comes_back_on_it(self):
        self.on_reserve();self.request()
        self.assertTrue(self.tick())
        self.assertEqual(self.exec,['uci -q -X show route_policy','uci set route_policy.cfg0123ab.peer_id=2000','uci -q delete route_policy.cfg0123ab.client_id',
                                    'uci set route_policy.cfg0123ab.group_id=10004','uci set network.wgclient1.config=peer_2000','uci set network.wgclient1.disabled=0',
                                    'uci commit route_policy','uci commit network','sh -c '+S.PROVIDER_SCRIPT+' update_provider_config 10004 2000 wgclient1',
                                    'ifdown wgclient1','ifup wgclient1'])
        self.reserve_untouched()
        state=pair.read_state();journal=n.journal_read()  # the real reader: validate_journal + pair metadata
        H3=sha('policy:2000')
        self.assertEqual(state['order'],['s_2000','t']);self.assertEqual(state['policy_hash'],H3)
        self.assertEqual(state['policy_roles'],pair_policy.proof(dict(self.selection,order=list(self.current))))
        self.assertEqual(state['policy_roles']['source_id'],NEW);self.assertEqual(state['selected_policy']['order'],['t','s_2000'])
        self.assertEqual(state['network_identity'],sha('net:peer_2000'))
        self.assertEqual(state['protected'],{'route_policy':sha('rp:2000'),'wireguard':sha('wg:2000')})
        self.assertEqual((state['server_change']['role'],state['server_change']['phase']),('source','CONNECTING'))
        self.assertEqual((journal['phase'],journal['source'],journal['target'],journal['hash']),('COMMITTED',NEW,TARGET,H3))
        self.assertEqual((journal['before'],journal['after']),(['s_2000','t'],['t','s_2000']))
        self.assertEqual(journal['pair_transition']['primary_order'],['s_2000','t']);self.assertEqual(journal['vendor_profiles']['source']['id'],NEW)
        self.assertTrue(pair_policy.state_order_matches(state,journal,self.backend.order()))
        self.assertEqual(self.kernel_proof()['role'],'target','the traffic stays on the reserve')
        self.assertEqual(self.published()['reason'],'SERVER-CHANGING')
        self.no_readopt()
        self.healthy[NEW]=True
        self.clock[0]+=5;self.assertTrue(self.tick());self.assertEqual(pair.read_state()['server_change']['phase'],'SETTLING')
        self.assertEqual(self.logs[-1],'SERVER-PICKED: server of the channel changed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms')
        self.clock[0]+=5;self.assertTrue(self.tick())
        self.assertNotIn('server_change',pair.read_state())
        self.assertEqual(n.journal_read()['vendor_profiles']['source']['vendor_generation'],'03'*16,'the journal records the observed profile')
        # the same pass went on with the normal return rules: the new id is ready -> back to the primary
        self.assertEqual(self.decided[-1],NEW);self.assertEqual(self.ready[-1],NEW)
        self.assertNotIn(SOURCE,self.ready[self.ready.index(NEW):],'the return never asks the old server again')
        journal=n.journal_read()
        self.assertEqual((journal['phase'],journal['restored_order']),('ROLLED-BACK',['s_2000','t']));self.assertEqual(self.current,['s_2000','t'])
        last=self.published()
        self.assertEqual((last['state'],last['reason'],last['source']),('ROLLED-BACK','PRIMARY-STABLY-RECOVERED',NEW))
        self.clock[0]+=5;self.assertTrue(self.tick())
        last=self.published()
        self.assertEqual((last['state'],last['reason'],last['source']),('OBSERVING','PAIR-WATCHING',NEW),'no EXTERNAL code after the return')
        self.assertEqual(pair.read_state()['phase'],'RUNNING');self.assertEqual(pair.read_state()['selected_policy']['role'],'source')
        self.no_readopt();self.reserve_untouched()

    def test_refused_during_transitions_holds_or_without_the_tunnel_anchor(self):
        self.on_reserve();self.request()
        journal=n.journal_read()
        for phase in ('APPLYING','WAIT-CLIENT','RESTORING','HELD-ON-RESERVE'):
            self.assertFalse(pair.server_start(self.backend,pair.read_state(),self.settings,self.revision,dict(journal,phase=phase)),phase)
        self.assertFalse(pair.server_start(self.backend,pair.read_state(),self.settings,self.revision,dict(journal,manual_request_id='ab'*16)),'a manual switch')
        state=pair.read_state();state['manual_hold']='target'
        self.assertFalse(pair.server_start(self.backend,state,self.settings,self.revision,journal),'a manual hold')
        self.assertFalse(pair.server_start(self.backend,pair.read_state(),dict(self.settings,plan_source_tunnel=''),self.revision,journal),'bound by profile id')
        self.request(tunnel_id=4192,protocol='openvpn',interface='ovpnclient1',section='cfg0456cd',**{'from':'1_2','to':'1_5'},group_id='1',profile_id='5')
        self.assertFalse(pair.server_start(self.backend,pair.read_state(),self.settings,self.revision,journal),'the carrying reserve')
        self.assertEqual([x for x in self.exec if not x.startswith('uci -q -X show')],[])
        self.request()
        self.assertTrue(pair.server_start(self.backend,pair.read_state(),self.settings,self.revision,journal))
        self.reserve_untouched()

    def test_a_new_primary_server_that_fails_the_check_is_rolled_back(self):
        self.on_reserve();self.request();self.assertTrue(self.tick())
        self.healthy[NEW]=False
        for _ in range(6):
            self.clock[0]+=10;self.assertTrue(self.tick())
        state=pair.read_state();journal=n.journal_read()
        self.assertTrue(state['server_change']['rolled_back']);self.assertEqual(state['order'],['s','t']);self.assertEqual(state['policy_hash'],'c'*64)
        self.assertEqual(state['policy_roles']['source_id'],SOURCE);self.assertEqual(state['protected']['wireguard'],sha('wg:3'))
        self.assertEqual((journal['phase'],journal['source'],journal['after'],journal['hash']),('COMMITTED',SOURCE,['t','s'],'c'*64))
        self.assertEqual(self.logs[-1],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms; rolled back')
        self.assertEqual(self.kernel_proof()['role'],'target')
        self.clock[0]+=95;self.assertTrue(self.tick())
        self.assertNotIn('server_change',pair.read_state())
        self.assertEqual((self.published()['state'],self.published()['reason']),('COMMITTED','CLIENT-CONFIRMED'))
        self.no_readopt();self.reserve_untouched()

    def applying(self,**over):
        """What server_start saved before its first write (the change record of the primary)."""
        state=pair.read_state()
        state['server_change']=dict({'tunnel_id':5841,'protocol':'wireguard','section':'cfg0123ab','interface':'wgclient1','phase':'APPLYING','role':'source',
                                     'from':{'group_id':'10004','profile_id':'3'},'to':{'group_id':'10004','profile_id':'2000','id':NEW},
                                     'started':self.clock[0],'deadline':self.clock[0]+60,'request':self.clock[0],'change':None},**over)
        pair.save(state)

    def boot(self):
        """The supervisor start after a power cut: Auto fenced, then the server change resume (native_switch.serve)."""
        pair.fence_recovery();return pair.server_resume_boot(self.backend)

    def restored(self):
        """The old primary server is live again and the session and the open journal name it (the reserve untouched)."""
        state=pair.read_state();journal=n.journal_read()
        self.assertEqual(self.peer,'3');self.assertEqual(self.wgconfig,'peer_3');self.assertNotIn('server_change',state)
        self.assertEqual((state['order'],state['policy_hash'],state['policy_roles']['source_id']),(['s','t'],'c'*64,SOURCE))
        self.assertEqual((journal['phase'],journal['source'],journal['after'],journal['hash']),('COMMITTED',SOURCE,['t','s'],'c'*64))
        self.assertTrue(pair_policy.state_order_matches(state,journal,self.backend.order()))
        self.assertEqual(self.kernel_proof()['role'],'target','the traffic stays on the reserve')
        self.reserve_untouched()

    def test_power_cut_between_the_uci_commits_and_the_session_write(self):
        self.on_reserve();self.applying()
        tunnel={'tunnel_id':5841,'protocol':'wireguard','section':'cfg0123ab','interface':'wgclient1'}
        self.assertEqual(S.execute(S.switch_plan(tunnel,{'group_id':'10004','profile_id':'2000'},True,True,False,False,1),self.io,True),S.PICKED)
        self.assertEqual(n.journal_read()['after'],['t','s'],'the journal still names the old rule')
        # the boot: the new server never passed its check -> the old one is restored before the COMMITTED journal is compared
        self.healthy[NEW]=True;self.exec.clear()
        self.assertTrue(self.boot())
        self.assertIn('uci set route_policy.cfg0123ab.peer_id=3',self.exec);self.restored()
        self.assertEqual(self.backend.order(),(n.journal_read()['after'],n.journal_read()['hash']),'native_switch.serve keeps the COMMITTED journal')
        self.assertEqual(self.logs[-1],'SERVER-PICK-RESUMED: adopted the recorded from server (the new one was not verified: restored)')
        # then the pair recovery (Auto fenced at boot): the cleanup returns to the primary on its old server
        self.healthy[SOURCE]=True;self.assertTrue(pair.recover(self.backend))
        journal=n.journal_read()
        self.assertEqual((journal['phase'],journal['source'],journal['restored_order']),('ROLLED-BACK',SOURCE,['s','t']))
        self.assertEqual(pair.read_state()['phase'],'STOPPED')
        # a cut between the two uci commits (route_policy only): not explainable, the normal checks decide
        state=pair.read_state();state['server_change']=dict(state.get('server_change') or {},tunnel_id=5841,protocol='wireguard',section='cfg0123ab',
            interface='wgclient1',phase='APPLYING',role='source',**{'from':{'group_id':'10004','profile_id':'3'},'to':{'group_id':'10004','profile_id':'2001'}})
        pair.save(state)
        self.uci(['uci','set','route_policy.cfg0123ab.peer_id=2001'],1);self.uci(['uci','commit','route_policy'],1)
        self.assertFalse(pair.server_resume(self.backend,pair.read_state()))
        self.assertNotIn('server_change',pair.read_state());self.assertEqual(n.journal_read()['source'],SOURCE)

    def test_power_cut_while_the_new_server_was_connecting_restores_the_old_one(self):
        self.on_reserve();self.request();self.assertTrue(self.tick())
        state=pair.read_state()
        self.assertEqual((state['server_change']['phase'],state['policy_roles']['source_id'],self.peer),('CONNECTING',NEW,'2000'))
        self.assertNotIn('verified',state['server_change'])
        self.exec.clear();self.assertTrue(self.boot())
        self.restored()
        self.assertEqual(self.exec[1:3],['uci set route_policy.cfg0123ab.peer_id=3','uci -q delete route_policy.cfg0123ab.client_id'])

    def test_power_cut_after_the_check_passed_keeps_the_new_server(self):
        self.on_reserve();self.request();self.assertTrue(self.tick())
        self.healthy[NEW]=True;self.clock[0]+=5;self.assertTrue(self.tick())
        self.assertEqual((pair.read_state()['server_change']['phase'],pair.read_state()['server_change']['verified']),('SETTLING',True))
        self.exec.clear();self.assertTrue(self.boot())
        state=pair.read_state();journal=n.journal_read()
        self.assertEqual(self.peer,'2000');self.assertEqual([x for x in self.exec if not x.startswith('uci -q -X show')],[],'nothing written')
        self.assertNotIn('server_change',state);self.assertEqual(state['policy_roles']['source_id'],NEW)
        self.assertEqual((journal['phase'],journal['source']),('COMMITTED',NEW));self.assertTrue(pair_policy.state_order_matches(state,journal,self.backend.order()))
        self.assertEqual(self.logs[-1],'SERVER-PICK-RESUMED: adopted the recorded to server')

    def test_an_unverified_new_server_whose_tunnel_carries_is_never_touched(self):
        self.on_reserve();self.request();self.assertTrue(self.tick())
        state=pair.read_state();state['server_change']['role']='target';pair.save(state)  # the kernel proves the traffic on this role
        self.exec.clear();self.boot()
        self.assertEqual(self.peer,'2000');self.assertEqual([x for x in self.exec if not x.startswith('uci -q -X show')],[],'nothing written')
        self.assertTrue(self.logs[-1].endswith('(not verified; its tunnel carries the traffic)'),self.logs[-1])

    def test_a_rollback_that_raised_after_its_uci_writes_is_resolved_by_the_next_tick(self):
        self.on_reserve();self.request();self.assertTrue(self.tick())
        self.healthy[NEW]=False;self.clock[0]+=61
        real=n.journal_write;calls=[]
        def broken(value):
            calls.append(value)
            if len(calls)==1:raise OSError('flash write failed')
            return real(value)
        with patch.object(n,'journal_write',side_effect=broken):self.assertTrue(self.tick())
        state=pair.read_state()
        self.assertEqual((state['server_change']['phase'],state['policy_roles']['source_id'],self.peer),('CONNECTING',NEW,'3'),'uci holds the old server, the session the new one')
        self.clock[0]+=5;self.assertTrue(self.tick())
        self.assertEqual((self.published()['state'],self.published()['reason']),('COMMITTED','CLIENT-CONFIRMED'),'no EXTERNAL code')
        self.restored();self.no_readopt()
        self.assertEqual(self.logs[-1],'SERVER-PICK-RESUMED: adopted the recorded from server')

    def test_provider_step_failing_both_ways_restores_the_old_server_without_a_restart(self):
        # MT3000 02.11.2026 23:36 (alpha5, Lua): the update_provider_config step raised (sys.exec refused its quotes) in
        # the change AND in its rollback; the log said `rollback failed` although uci and the session named peer 2002
        # again and wgclient1 was never restarted. The rollback restored the old server: say so.
        self.on_reserve();self.request()
        uci=self.uci
        def provider_raises(argv,seconds):
            if argv[:2]==['sh','-c']:self.exec.append(' '.join(argv));raise OSError('sys: unsafe command argument')
            return uci(argv,seconds)
        self.io['exec']=provider_raises
        self.assertTrue(self.tick())
        self.assertFalse(any(line.startswith(('ifdown','ifup')) for line in self.exec),'the tunnel was never restarted')
        self.assertEqual(sum(1 for line in self.exec if line.startswith('sh -c')),2,'the change and its rollback')
        self.assertEqual(self.logs[-1],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms; '
                                       'rolled back (the tunnel was not restarted)')
        state=pair.read_state();journal=n.journal_read()
        self.assertEqual((self.peer,self.wgconfig),('3','peer_3'))
        self.assertEqual((state['order'],state['policy_hash'],state['policy_roles']['source_id']),(['s','t'],'c'*64,SOURCE))
        self.assertEqual((journal['phase'],journal['source'],journal['after'],journal['hash']),('COMMITTED',SOURCE,['t','s'],'c'*64))
        self.assertTrue(state['server_change']['rolled_back']);self.reserve_untouched();self.no_readopt()

    def test_a_rollback_that_cannot_write_uci_is_a_failed_rollback(self):
        self.on_reserve();self.request()
        uci=self.uci;seen=[]
        def broken(argv,seconds):
            if argv[:2]==['sh','-c']:self.exec.append(' '.join(argv));return 1,''
            if argv[:3]==['uci','set','route_policy.cfg0123ab.peer_id=3']:seen.append(argv);self.exec.append(' '.join(argv));return 1,''
            return uci(argv,seconds)
        self.io['exec']=broken
        self.assertTrue(self.tick());self.assertEqual(len(seen),1)
        self.assertTrue(self.logs[-1].endswith('; rollback failed'),self.logs[-1])

    def test_a_change_whose_first_write_fails_changed_nothing(self):
        self.on_reserve();self.request()
        before=(pair.read_state(),n.journal_read())
        uci=self.uci
        def refused(argv,seconds):
            if argv[:2]==['uci','set']:self.exec.append(' '.join(argv));return 1,''
            return uci(argv,seconds)
        self.io['exec']=refused
        self.assertTrue(self.tick())  # the normal pass of the same tick
        self.assertEqual([line for line in self.exec if not line.startswith('uci -q -X show')],['uci set route_policy.cfg0123ab.peer_id=2000'],'no rollback')
        self.assertEqual(self.logs[-1],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 5841 wireguard): Berlin -> Frankfurt, ? -> 35 ms; not changed')
        state=pair.read_state();journal=n.journal_read()
        self.assertNotIn('server_change',state,'nothing to wait for')
        self.assertEqual((state['order'],state['policy_hash'],state['policy_roles']),(before[0]['order'],before[0]['policy_hash'],before[0]['policy_roles']))
        self.assertEqual((journal['phase'],journal['source'],journal['after']),(before[1]['phase'],before[1]['source'],before[1]['after']))
        self.assertEqual(json.loads(self.files['/run/'+S.EVENT])['tunnels'][0]['code'],S.FAILED)
        self.assertEqual(json.loads(self.files['/run/'+S.STATE])['changes']['5841'],[self.clock[0]],'counted for the hourly limit')
        self.clock[0]+=5;self.tick()
        self.assertEqual(sum(1 for line in self.exec if line.startswith('uci set')),1,'the hand-off is taken once')
        self.reserve_untouched();self.no_readopt()

if __name__=='__main__':unittest.main()
