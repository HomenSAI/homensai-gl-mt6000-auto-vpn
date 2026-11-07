"""Owner decision 07.11.2026 (F-80), the path WITHOUT an open journal: hold_reserve keeps a WORKING reserve only.

The session carries traffic on the reserve per selected_policy (after a boot, after an accepted manual selection) and no
transaction journal is open, so pair_auto.tick decides the return itself (not committed_recovery_decision). A reserve the
detector calls failed is probed once (backend.health); only a FRESH NEGATIVE probe opens the rescue rule (rescue_stable,
RESERVE-FAILED-PRIMARY-VERIFIED) through the same pair_return attempt, guards and cooldown as the planned return; an
unknown probe holds (RESERVE-HEALTH-UNKNOWN), an alive probe observes, a working reserve is never left.
Shared cases: rescue_no_journal_cases.json; Lua twin: tests/lua/test_rescue_no_journal.lua (pair.lua tick).
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import auto_control  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
import pair_policy  # noqa: E402
from recovery_settings import stable_seconds  # noqa: E402

CASES=json.loads((HERE/'rescue_no_journal_cases.json').read_text(encoding='utf-8'))['cases']
PRIMARY='wireguard:peer_2002';RESERVE='openvpn:40354_2016'
NOW=100000.0


class NoJournalRescue(unittest.TestCase):
    """Real: tick's gates, the ledger, return_rule, channel_failed over the fake streak. Fake: the backend, the attempt."""

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.runtime=root/'run';self.persist=root/'persist'
        self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,auto_control,native):
            for name,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,name):
                    p=patch.object(module,name,value);p.start();self.addCleanup(p.stop)
        self.revision=auto_control.current_revision()

    def run_case(self,case):
        settings=dict({'pair_auto_mode':pair.MODE,'interval':'10','failure_model':'consecutive'},**case.get('settings',{}))
        for folder in (self.runtime,self.persist):  # every case starts from a fresh session
            for path in folder.iterdir():path.unlink()
        self.revision=auto_control.current_revision()
        self.assertTrue(pair.request(self.revision).get('accepted'))
        selection={'source':{'id':PRIMARY},'target':{'id':RESERVE},'vendor_identity':'d'*64,'order':['b','a'],'source_rule':'a','target_rule':'b','direction':'first'}
        # the kernel order ['b','a'] puts the reserve rule first: the session carries traffic on the reserve (role target), no journal
        state=dict(id=pair.intent()['id'],phase='RUNNING',owned=[],before_flags={'wgclient1':'0','ovpnclient1':'0'},network_identity='b'*64,
                   protected={},process_bindings=None,order=['b','a'],policy_hash='c'*64,revision=self.revision,started=NOW-1000,
                   policy_roles=pair_policy.proof(selection),selected_policy={'role':'target','order':['b','a'],'hash':'c'*64,'since':NOW-1000})
        pair.save(state)
        agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':[NOW+x for x in case.get('events',[])]})
        kernel={'verified':True,'role':'target','order':['b','a'],'policy_hash':'c'*64,'kernel_fingerprint':'f'*64,'time':NOW-1000}
        good={PRIMARY:not case.get('primary_failed'),RESERVE:not case['reserve_failed']}
        health={PRIMARY:True,RESERVE:None if case.get('reserve_health')=='unknown' else case.get('reserve_health',True)}
        probes=[];asked=[];dispatched=[];published=[]
        backend=Mock();backend.diagnostic.return_value=([],selection);backend.order.return_value=(state['order'],state['policy_hash'])
        def probe(identifier):
            probes.append(identifier);return health[identifier]
        backend.health.side_effect=probe
        def recovery_ready(identifier,s):
            asked.append(stable_seconds(s));return identifier==PRIMARY and stable_seconds(s)<=case['ready_upto']
        backend.recovery_ready.side_effect=recovery_ready
        def streak(samples,identifier,count,now,age,wanted,profile=None):return good[identifier]==wanted
        def attempt(*args,**kwargs):
            kwargs['on_dispatch']();dispatched.append(kwargs)
        def observe(backend_,state_,settings_,revision_,journal_,observed=None):
            observed['kernel']=kernel;return False
        def write_samples():
            samples=[{'id':x,'time':NOW-i*10,'code':None if good[x] else 'VPN-003','dns_ok':good[x],'https_success':2 if good[x] else 0} for x in (PRIMARY,RESERVE) for i in range(3)]
            agent.atomic_json(self.runtime/'status.json',{'time':NOW,'samples':samples,'profiles':[]})
        patches=[patch.object(pair.time,'time',return_value=NOW),patch.object(native.time,'time',return_value=NOW),
                 patch.object(native,'journal_read',return_value={}),
                 patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=state['network_identity']),
                 patch.object(pair,'configs',return_value={}),patch.object(pair,'configure_lease',return_value=0),
                 patch.object(pair,'reapply_missing_policy',side_effect=observe),
                 patch('failover_plan.streak',side_effect=streak),patch.object(native,'streak',side_effect=streak),
                 patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),
                 patch('failure_diagnosis.resolve_pair',return_value={'coordination':{'state':'READY'},'target':{'id':RESERVE},'source':{'id':PRIMARY}}),
                 patch.object(pair_policy,'metadata',return_value=None),patch.object(pair_policy,'state_order_matches',return_value=True),
                 patch.object(native,'publish',side_effect=published.append),patch.object(native,'attempt',side_effect=attempt),
                 patch('pair_manual.consume',return_value=False),patch('pair_manual.held_reserve',return_value=False),
                 patch.object(pair,'revive',return_value=False),patch.object(pair,'server_start',return_value=False)]
        # BH-06: steps = [(monotonic seconds, reserve_failed), ...] ticks of one session; default one tick
        per_step=[]
        for mono,reserve_failed in case.get('steps') or [(None,case['reserve_failed'])]:
            good[RESERVE]=not reserve_failed;write_samples()
            extra=[patch.object(pair,'_uptime',return_value=mono)] if mono is not None else []
            for p in patches+extra:p.start()
            try:self.assertTrue(pair.tick(backend,settings,self.revision))
            finally:
                for p in reversed(patches+extra):p.stop()
            per_step.append(len([x for x in probes if x==RESERVE]))
        return dict(probes=probes,asked=asked,dispatched=dispatched,published=published,per_step=per_step)

    def test_shared_cases(self):
        for case in CASES:
            with self.subTest(case['name']):
                got=self.run_case(case)
                self.assertEqual([x for x in got['probes'] if x==RESERVE],[RESERVE] if case['probed'] else [],'the one fresh probe of the reserve')
                self.assertEqual(got['asked'][:1],[case['asked']] if case['asked'] is not None else [],'the stability asked of the primary')
                self.assertEqual(len(got['dispatched']),1 if case['dispatch'] else 0,got['published'][-1:] )
                if case['dispatch']:
                    sent=got['dispatched'][0]
                    self.assertTrue(sent.get('pair_return'));self.assertEqual(sent.get('pair_destination'),'source')
                    self.assertEqual(sent.get('pair_session_order'),['b','a'])
                    self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'][-1],NOW,'the return is charged (cooldown spacing)')
                else:
                    final=got['published'][-1]
                    self.assertEqual((final['state'],final['reason']),(case['state'],case['reason']))
                    self.assertFalse(final.get('blockers'))

    def test_the_rescue_waits_for_the_cooldown_after_its_own_dispatch(self):
        # the dispatch is charged like every return: a second tick inside the cooldown does not dispatch again
        case=dict(CASES[0]);got=self.run_case(case)
        self.assertEqual(len(got['dispatched']),1)
        again=dict(case,events=[0],dispatch=False)
        got=self.run_case(again)
        self.assertEqual(got['dispatched'],[]);self.assertEqual(got['probes'],[],'inside the cooldown nothing is probed')

    def test_bh06_a_dead_reserve_is_probed_once_per_interval_of_one_failure_episode(self):
        """BH-06: WAN down, held on the failed reserve (the primary not yet stable): ticks every 10 s probe once per
        RESCUE_PROBE_INTERVAL; a tick where the reserve is no longer failed ends the episode, the next failure probes at once."""
        interval=pair.RESCUE_PROBE_INTERVAL
        for health,reason in ((False,'RESERVE-FAILED'),('unknown','RESERVE-HEALTH-UNKNOWN')):
            with self.subTest(health):
                case={'name':'bh06','settings':{'recovery_return_policy':'hold_reserve'},'reserve_failed':True,'reserve_health':health,
                      'ready_upto':0,'dispatch':False,
                      'steps':[(1000.0,True),(1010.0,True),(1000.0+interval-1,True),(1000.0+interval,True),(1000.0+interval+5,True),
                               (1000.0+interval+10,False),(1000.0+interval+20,True)]}
                got=self.run_case(case)
                self.assertEqual(got['per_step'],[1,1,1,2,2,2,3])
                self.assertEqual(got['dispatched'],[])
                held=[x for x in got['published'] if x.get('reason')==reason]
                self.assertGreaterEqual(len(held),6,'the cached answer still holds with its reason')

    def test_bh06_another_session_probes_afresh(self):
        case={'name':'bh06','settings':{'recovery_return_policy':'hold_reserve'},'reserve_failed':True,'reserve_health':False,
              'ready_upto':0,'dispatch':False,'steps':[(5000.0,True)]}
        self.assertEqual(self.run_case(case)['per_step'],[1])
        self.assertEqual(self.run_case(case)['per_step'],[1],'a new session id is a new episode')


if __name__=='__main__':
    unittest.main()
