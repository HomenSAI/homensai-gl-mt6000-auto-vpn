import copy,json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair,pair_manual as manual

NOW=1792750000
SOURCE='wireguard:peer_3';TARGET='openvpn:1_2'


class Tests(unittest.TestCase):
    def enterContext(self,context):
        value=context.__enter__();self.addCleanup(context.__exit__,None,None,None);return value
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.runtime=self.root/'run';self.persist=self.root/'save';self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,n,auto_control):
            for key,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,key):self.enterContext(patch.object(module,key,value))
        for key,name in (('STATE','native-status.json'),('JOURNAL','native-transaction.json')):
            self.enterContext(patch.object(n,key,(self.runtime if key=='STATE' else self.persist)/name))
        self.enterContext(patch('pair_manual.time.time',return_value=NOW))
        self.revision=auto_control.current_revision()
        self.state={'id':'a'*32,'phase':'RUNNING','owned':['wgclient1','ovpnclient1'],'before_flags':{'wgclient1':'1','ovpnclient1':'1'},
            'network_identity':'b'*64,'protected':{},'process_bindings':{},'order':['s','t'],'policy_hash':'c'*64,'revision':self.revision}
        pair.save(self.state);agent.atomic_json(pair.paths()[0],{'mode':'on','id':self.state['id'],'revision':self.revision,'time':NOW})
        self.settings={'pair_auto_mode':pair.MODE,'recovery_cooldown':'60','recovery_min_dwell':'60'}
        self.selection={'hash':'c'*64,'settings_hash':'d'*64,'vendor_identity':'e'*64,'source':{'id':SOURCE},'target':{'id':TARGET}}
        self.backend=Mock();self.backend.policy.return_value={'settings':self.settings};self.backend.diagnostic.return_value=([],self.selection)
        self.backend.order.return_value=(['s','t'],'c'*64);self.backend.health.return_value=True
        self.enterContext(patch.object(n,'Linux',return_value=self.backend));self.journal={}
        self.enterContext(patch.object(n,'journal_read',side_effect=lambda:copy.deepcopy(self.journal)))
        self.publish=self.enterContext(patch.object(n,'publish'))
        agent.atomic_json(n.STATE,{'state':'OBSERVING','time':NOW,'source':SOURCE,'target':TARGET,'mode':'continuous-pair','readiness_verified':True})
        agent.atomic_json(self.runtime/'status.json',{'time':NOW,'profiles':[{'id':key,'time':NOW,'code':None,'dns_ok':True,'https_success':2} for key in (SOURCE,TARGET)]})

    def reserve_request(self):
        answer=manual.request('reserve',self.revision);self.assertTrue(answer['accepted'],answer);return answer

    def attempt(self,*args,**kw):
        self.journal={'phase':'HELD-ON-RESERVE','manual_request_id':kw['manual_request_id'],'confirmed':NOW,
            'tx':'f'*32,'source':SOURCE,'target':TARGET,'before':['s','t'],'after':['t','s'],'hash':'c'*64}
        self.backend.order.return_value=(['t','s'],'c'*64)

    def test_queued_reserve_runs_once_shares_budget_and_holds_without_stopping_auto(self):
        self.reserve_request()
        with patch.object(pair,'configure_lease',return_value=NOW+180),patch.object(n,'attempt',side_effect=self.attempt) as apply:
            self.assertTrue(manual.consume(self.backend,pair.read_state(),self.settings,self.revision))
            self.assertFalse(manual.consume(self.backend,pair.read_state(),self.settings,self.revision));apply.assert_called_once()
        self.assertEqual(manual.public()['state'],'COMPLETED');self.assertEqual(pair.read_state()['manual_hold'],'target')
        self.assertEqual(pair.intent()['mode'],'on');self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],[NOW])

    def test_manual_switch_uses_the_same_custom_attempt_window(self):
        self.settings.update(recovery_attempt_limit='1',recovery_attempt_window='5')
        agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':[NOW-200]})
        denied=manual.request('reserve',self.revision)
        self.assertFalse(denied['accepted']);self.assertIn('PAIR-RATE-LIMIT',denied['blockers'])
        self.settings['recovery_attempt_window']='1'
        self.assertTrue(manual.request('reserve',self.revision)['accepted'])
        self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],[NOW-200])

    def test_stop_before_claim_cancels_without_dispatch(self):
        self.reserve_request();auto_control.current_revision(rotate=True)
        with patch.object(n,'attempt') as apply:
            manual.consume(self.backend,pair.read_state(),self.settings,self.revision);apply.assert_not_called()
        self.assertEqual(manual.public()['state'],'CANCELLED')

    def test_stop_after_dispatched_work_never_reports_completed_or_saves_hold(self):
        self.reserve_request()
        def stopped(*a,**kw):self.attempt(*a,**kw);auto_control.current_revision(rotate=True)
        with patch.object(pair,'configure_lease',return_value=NOW+180),patch.object(n,'attempt',side_effect=stopped):
            manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'CANCELLED');self.assertNotIn('manual_hold',pair.read_state())

    def test_changed_configuration_refuses_before_budget_or_apply(self):
        self.reserve_request();self.backend.diagnostic.return_value=([],dict(self.selection,settings_hash='f'*64))
        with patch.object(n,'attempt') as apply:
            manual.consume(self.backend,pair.read_state(),self.settings,self.revision);apply.assert_not_called()
        self.assertEqual(manual.public()['code'],'MANUAL-CONFIG-CHANGED');self.assertFalse((self.persist/'pair-auto-budget.json').exists())

    def test_unhealthy_reserve_is_never_selected_or_charged(self):
        self.reserve_request();self.backend.health.return_value=False
        with patch.object(n,'attempt') as apply:
            manual.consume(self.backend,pair.read_state(),self.settings,self.revision);apply.assert_not_called()
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertFalse((self.persist/'pair-auto-budget.json').exists())

    def test_exhausted_budget_and_cooldown_are_not_bypassed(self):
        for events,code in (([NOW-30,NOW-20,NOW-10],'PAIR-RATE-LIMIT'),([NOW-10],'PAIR-MANUAL-COOLDOWN')):
            with self.subTest(code=code):
                manual.path().unlink(missing_ok=True);(self.persist/'pair-auto-budget.json').unlink(missing_ok=True)
                self.reserve_request();agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':events})
                with patch.object(n,'attempt') as apply:
                    manual.consume(self.backend,pair.read_state(),self.settings,self.revision);apply.assert_not_called()
                self.assertEqual(manual.public()['code'],code)

    def test_duplicate_pending_request_never_enqueues_a_second_action(self):
        answer=self.reserve_request();second=manual.request('reserve',self.revision)
        self.assertFalse(second['accepted']);self.assertEqual(manual.read()['id'],answer['request_id'])

    def test_expired_request_and_interrupted_claim_are_never_replayed(self):
        self.reserve_request()
        with patch('pair_manual.time.time',return_value=NOW+61):manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'CANCELLED')
        manual.path().unlink();self.reserve_request();row=manual.read();row['state']='CLAIMED';agent.atomic_json(manual.path(),row)
        manual.recover();self.assertEqual(manual.public()['state'],'UNCONFIRMED')
        with patch.object(n,'attempt') as apply:
            self.assertFalse(manual.consume(self.backend,pair.read_state(),self.settings,self.revision));apply.assert_not_called()

    def test_resume_only_releases_override_without_applying_or_disabling_auto(self):
        state=pair.read_state();state['manual_hold']='source';pair.save(state)
        self.assertTrue(manual.request('resume',self.revision)['accepted'])
        with patch.object(n,'attempt') as apply:
            manual.consume(self.backend,pair.read_state(),self.settings,self.revision);apply.assert_not_called()
        self.assertNotIn('manual_hold',pair.read_state());self.assertEqual(pair.intent()['mode'],'on');self.assertTrue(manual.public()['completed'])

    def test_primary_requires_correlated_return_and_verifies_order(self):
        self.journal={'phase':'HELD-ON-RESERVE','confirmed':NOW,'tx':'f'*32,'source':SOURCE,'target':TARGET,'before':['s','t'],'after':['t','s'],'hash':'c'*64}
        self.backend.order.return_value=(['t','s'],'c'*64)
        self.assertTrue(manual.request('primary',self.revision)['accepted'])
        def returned(*args,**kw):
            self.assertEqual(kw['control_revision'],self.revision)
            self.journal['phase']='ROLLED-BACK';self.backend.order.return_value=(['s','t'],'c'*64)
            agent.atomic_json(n.return_result_path(),{'ok':True,'code':'RETURNED','request':NOW,'time':NOW});return True,0
        with patch.object(n,'handle_return',side_effect=returned):manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(pair.read_state()['manual_hold'],'source');self.assertTrue(manual.public()['completed'])

    def test_invalid_records_and_off_pair_do_not_become_manual_permission(self):
        self.assertFalse(manual.valid({'direction':[]}))
        pair.stop_locked(self.revision);self.assertFalse(manual.controls()['available'])
        self.assertFalse(manual.request('reserve',self.revision)['accepted'])

    def test_unknown_held_identity_does_not_publish_a_healthy_commit_or_restore(self):
        self.state['manual_hold']='target'
        journal={'phase':'HELD-ON-RESERVE','confirmed':NOW,'source':SOURCE,'target':TARGET,'before':['s','t'],'after':['t','s'],'hash':'c'*64}
        self.backend.order.return_value=(['t','s'],'c'*64)
        with patch('failure_diagnosis.resolve_pair',return_value={'coordination':{'state':'UNKNOWN'},'target':None}),patch.object(n,'finish_committed') as restore:
            self.assertTrue(manual.held_reserve(self.backend,self.state,journal,self.settings,{}));restore.assert_not_called()
        self.assertEqual(self.publish.call_args[0][0]['state'],'DEGRADED-ON-RESERVE')

    def test_programmatic_test_override_is_not_attributed_to_operator(self):
        answer=manual.request('reserve',self.revision,request_source='test');self.assertTrue(answer['accepted'])
        self.assertEqual(manual.public()['request_source'],'test')
        with patch.object(pair,'configure_lease',return_value=NOW+180),patch.object(n,'attempt',side_effect=self.attempt) as apply:
            self.assertTrue(manual.consume(self.backend,pair.read_state(),self.settings,self.revision))
        self.assertEqual(apply.call_args.kwargs['request_source'],'test')
        self.assertEqual(self.publish.call_args[0][0]['transition_source'],'test')
        self.assertEqual(pair.read_state()['manual_hold_source'],'test')


if __name__=='__main__':unittest.main()
