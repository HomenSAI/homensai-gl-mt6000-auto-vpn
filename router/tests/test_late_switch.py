"""Late-switch recheck: never leave a primary that already recovered before the failover commits.

MT3000 phase 2, 02.11.2026 (2.1.0-alpha5, report-phase2-alpha5-pass1): a 15 s blackout of the primary was left at
~20 s (APPLYING at 18.7 s), after the primary had recovered at 15 s - an unnecessary switch and a later return;
blackouts of 20-40 s were left at 20-22 s (correct). The three failed dense samples that met the streak all started
inside the blackout (about 3.5/7.5/11.5 s); the monitor's first healthy one (started 15.5 s, published ~18 s) came
while the switch was already running. Now the source is looked at once more right before the failover commits.
Lua twin: tests/lua/test_late_switch.lua (late_switch_cases.json, the same decisions).
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

CASES=json.loads((HERE/'late_switch_cases.json').read_text(encoding='utf-8'))
PROFILE=CASES['profile']
SIM=CASES['simulation']
RESERVE={'id':'openvpn:1_1','protocol':'openvpn','interface':'ovpnclient1','vendor_tunnel_id':'openvpn:ovpnclient1',
         'vendor_generation':'02'*16,'vendor_changed_at':PROFILE['vendor_changed_at']}


def row(profile,r):
    return {'id':profile['id'],'time':r['t'],'code':r['code'],'dns_ok':r['dns_ok'],'https_success':r['https'],'interface':profile['interface'],
            'vendor_tunnel_id':profile['vendor_tunnel_id'],'vendor_generation':r.get('gen',profile['vendor_generation'])}


class SharedCases(unittest.TestCase):
    def test_monitor_recovered_shared_cases(self):
        for case in CASES['recovered']:
            with self.subTest(case['name']):
                samples=[row(PROFILE,r) for r in case['rows']]
                self.assertIs(pair.monitor_recovered(samples,PROFILE['id'],case['evidence'],case['now'],PROFILE),case['result'])

    def test_same_evidence_shared_cases(self):
        for case in CASES['same_evidence']:
            with self.subTest(case['name']):
                self.assertIs(pair.same_evidence(case['aborted'],case['evidence']),case['result'])

    def test_newest_sample_without_a_profile(self):
        good={'id':'a','time':5,'code':None,'dns_ok':True,'https_success':3}
        bad={'id':'a','time':5,'code':'VPN-003','dns_ok':False,'https_success':0}
        old={'id':'a','time':1,'code':'VPN-003','dns_ok':False,'https_success':0}
        self.assertIs(pair.newest_sample([old,good,{'id':'b','time':9}],'a'),good)
        self.assertIsNone(pair.newest_sample([old,good,bad],'a'),'two disagreeing samples of one stamp')
        self.assertIsNone(pair.newest_sample([{'id':'a','time':'x'}],'a'))
        self.assertIsNone(pair.newest_sample(None,'a'))

    def test_constants(self):
        self.assertEqual((pair.LATE_RECHECK_CODE,pair.RECHECK_SECONDS),('PRIMARY-RECOVERED-BEFORE-SWITCH',1))


class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.runtime=root/'run';self.persist=root/'persist'
        self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,auto_control,native):
            for name,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,name):
                    p=patch.object(module,name,value);p.start();self.addCleanup(p.stop)
        self.revision=auto_control.current_revision()
        pair.LATE_ABORTS.clear();self.addCleanup(pair.LATE_ABORTS.clear)


class Units(Base):
    def selection(self):
        return {'source':dict(PROFILE),'target':dict(RESERVE)}

    def status(self,rows):
        agent.atomic_json(self.runtime/'status.json',{'samples':[row(PROFILE,r) for r in rows]})

    def test_monitor_sample_aborts_without_probing(self):
        self.status([{'t':1011.5,'code':'VPN-003','dns_ok':False,'https':0},{'t':1015.5,'code':None,'dns_ok':True,'https':3}])
        backend=Mock()
        with patch.object(pair.time,'time',return_value=1018.5):
            self.assertEqual(pair.late_recheck(backend,self.selection(),1011.5),('PRIMARY-RECOVERED-BEFORE-SWITCH','monitor'))
        backend.recheck.assert_not_called()

    def test_probe_aborts_only_on_a_true_answer(self):
        self.status([{'t':1011.5,'code':'VPN-003','dns_ok':False,'https':0}])
        backend=Mock()
        with patch.object(pair.time,'time',return_value=1018.5):
            backend.recheck.return_value=True
            self.assertEqual(pair.late_recheck(backend,self.selection(),1011.5),('PRIMARY-RECOVERED-BEFORE-SWITCH','probe'))
            backend.recheck.assert_called_with(PROFILE['id'],1)
            for answer in (False,None,1,'yes'):
                backend.recheck.return_value=answer
                self.assertIsNone(pair.late_recheck(backend,self.selection(),1011.5),answer)
            backend.recheck.side_effect=OSError('probe')
            self.assertIsNone(pair.late_recheck(backend,self.selection(),1011.5),'a failing probe never stops a failover')
        self.assertIsNone(pair.late_recheck(object(),self.selection(),1011.5),'a backend without the probe goes on')

    def test_a_large_packet_failure_is_never_contradicted_by_the_short_probe(self):
        # VPN-MTU (mss-sqm): small DNS/HTTPS checks pass on a black hole, so only the monitor's own reading may abort
        self.status([{'t':1011.5,'code':'VPN-MTU','dns_ok':True,'https':3}])
        backend=Mock();backend.recheck.return_value=True
        with patch.object(pair.time,'time',return_value=1018.5):
            self.assertIsNone(pair.late_recheck(backend,self.selection(),1011.5,'VPN-MTU'))
            backend.recheck.assert_not_called()
            self.assertEqual(pair.late_recheck(backend,self.selection(),1011.5,'VPN-003'),('PRIMARY-RECOVERED-BEFORE-SWITCH','probe'))
        self.status([{'t':1011.5,'code':'VPN-MTU','dns_ok':True,'https':3},{'t':1015.5,'code':None,'dns_ok':True,'https':3}])
        with patch.object(pair.time,'time',return_value=1018.5):
            self.assertEqual(pair.late_recheck(backend,self.selection(),1011.5,'VPN-MTU'),('PRIMARY-RECOVERED-BEFORE-SWITCH','monitor'))

    def test_unreadable_status_goes_on(self):
        (self.runtime/'status.json').write_text('{',encoding='utf-8')
        backend=Mock();backend.recheck.return_value=False
        with patch.object(pair.time,'time',return_value=1018.5):
            self.assertIsNone(pair.late_recheck(backend,self.selection(),1011.5))

    def test_backend_recheck_uses_the_short_probe(self):
        linux=native.Linux.__new__(native.Linux)
        profile=dict(PROFILE)
        with patch.object(native,'inventory',return_value={'profiles':[profile]}),patch.object(native,'probe') as probe:
            probe.return_value={'code':None,'dns_ok':True,'https_success':2};self.assertIs(linux.recheck(PROFILE['id'],1),True)
            probe.assert_called_with(profile,1)
            probe.return_value={'code':None,'dns_ok':True,'https_success':1};self.assertIs(linux.recheck(PROFILE['id'],1),False)
            probe.return_value={'code':'SYSTEM-001'};self.assertIs(linux.recheck(PROFILE['id'],1),False)
            self.assertIs(linux.recheck('openvpn:missing',1),False)

    def test_agent_probe_short_wait_reaches_every_check(self):
        binding={'code':None,'device':'wg0','mark':4096,'table':'1','ifindex':7}
        seen=[]
        def https(device,mark,target,*rest):seen.append(('https',rest));return 20
        def dns(device,mark,*rest):seen.append(('dns',rest));return True
        with patch.object(agent,'route_binding',return_value=binding),patch.object(agent,'https_probe',side_effect=https),patch.object(agent,'dns_probe',side_effect=dns):
            self.assertIsNone(agent.probe({'id':'x','interface':'wgclient1'},1)['code'])
            self.assertEqual(sorted(seen),[('dns',(1,))]+[('https',(1,))]*3)
            seen.clear();agent.probe({'id':'x','interface':'wgclient1'})
            self.assertEqual(sorted(seen),[('dns',())]+[('https',())]*3,'the usual probe is unchanged')
            seen.clear();agent.probe({'id':'x','interface':'wgclient1'},6)
            self.assertEqual(sorted(seen),[('dns',())]+[('https',())]*3,'no longer than the usual wait')


class Simulation(Base):
    """pair_auto.tick against the measured MT3000 timing (late_switch_cases.json 'simulation').

    Real: tick's gates, failover_plan.streak over the published samples, late_recheck, the abort memory.
    Fake: the transaction (attempt -> COMMITTED), the vendor diagnostic (costs diagnostic_seconds) and the probe."""
    START=1761830400.0

    def run_blackout(self,seconds,recheck=True):
        return self.run_fault(lambda offset:not (0<=offset<seconds),recheck)

    def run_fault(self,healthy_at,recheck=True,mtu=False):
        settings={'pair_auto_mode':pair.MODE,'interval':'10'}
        (self.persist/'pair-auto-budget.json').unlink(missing_ok=True)  # every run is a fresh outage: no cooldown from the last one
        pair.LATE_ABORTS.clear()
        start=self.START;changed=start-1000
        source=dict(PROFILE,vendor_changed_at=changed);target=dict(RESERVE,vendor_changed_at=changed)
        selection={'source':source,'target':target,'vendor_identity':'d'*64,'order':['a','b'],'source_rule':'a','target_rule':'b','direction':'first'}
        pair.request(self.revision)
        state=dict(id=pair.intent()['id'],phase='RUNNING',owned=[],before_flags={'wgclient1':'0','ovpnclient1':'0'},network_identity='b'*64,
                   protected={},process_bindings=None,order=['a','b'],policy_hash='c'*64,revision=self.revision)
        pair.save(state)
        sim={'now':start-30,'journal':{},'switches':[],'published':[],'rechecks':[]}
        up=lambda t:healthy_at(t-start)
        starts=[start+x for x in SIM['normal_passes']]
        x=SIM['dense_first']
        while x<SIM['end']:starts.append(start+x);x+=SIM['dense_every']
        def published(now):
            rows=[]
            for s in starts:
                if s+SIM['publish_after']<=now:
                    ok=up(s)
                    small=ok or mtu  # a large-packet black hole still answers the small DNS/HTTPS checks
                    rows.append({'id':source['id'],'time':s,'code':None if ok else 'VPN-MTU' if mtu else 'VPN-003','dns_ok':small,'https_success':3 if small else 0,
                                 'interface':source['interface'],'vendor_tunnel_id':source['vendor_tunnel_id'],'vendor_generation':source['vendor_generation']})
                    rows.append({'id':target['id'],'time':s,'code':None,'dns_ok':True,'https_success':3,
                                 'interface':target['interface'],'vendor_tunnel_id':target['vendor_tunnel_id'],'vendor_generation':target['vendor_generation']})
            return rows
        backend=Mock(spec=['diagnostic','order','use_process_bindings','recovery_ready','health','recheck'])
        def diagnostic():
            sim['now']+=SIM['diagnostic_seconds'];return ([],selection)
        backend.diagnostic.side_effect=diagnostic
        backend.order.return_value=(state['order'],state['policy_hash'])
        backend.recovery_ready.return_value=False
        def probe(identifier,wait):
            sim['rechecks'].append(sim['now']-start)
            healthy=up(sim['now']) or mtu  # the short probe never sees large-packet loss
            sim['now']+=SIM['probe_up_seconds'] if healthy else wait
            return healthy
        backend.recheck.side_effect=probe
        if not recheck:del backend.recheck
        def attempt(*args,**kwargs):
            kwargs['on_dispatch']()
            sim['switches'].append(sim['now']-start)
            sim['journal']={'phase':'COMMITTED','source':source['id'],'target':target['id'],'started':sim['now'],'confirmed':sim['now']}
        patches=[patch.object(pair.time,'time',side_effect=lambda:sim['now']),
                 patch.object(native,'journal_read',side_effect=lambda:dict(sim['journal'])),
                 patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=state['network_identity']),
                 patch.object(pair,'configs',return_value={}),patch.object(pair,'configure_lease',return_value=0),
                 patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),
                 patch.object(pair_policy,'current_role',side_effect=lambda j:'target' if j.get('phase')=='COMMITTED' else 'source'),
                 patch.object(pair_policy,'metadata',return_value=None),patch.object(pair_policy,'state_order_matches',return_value=True),
                 patch.object(native,'publish',side_effect=lambda value:sim['published'].append((round(sim['now']-start,2),value))),
                 patch.object(native,'attempt',side_effect=attempt),
                 patch('pair_manual.consume',return_value=False),patch('pair_manual.held_reserve',return_value=False),
                 patch.object(pair,'revive',return_value=False),patch.object(pair,'server_start',return_value=False)]
        if not recheck:patches.append(patch.object(pair,'late_recheck',return_value=None))
        for p in patches:p.start()
        try:
            tick=start-30
            while tick<start+SIM['end'] and not sim['switches']:
                sim['now']=max(sim['now'],tick)
                agent.atomic_json(self.runtime/'status.json',{'samples':published(sim['now'])})
                pair.tick(backend,settings,self.revision)
                tick=max(tick+SIM['tick_every'],sim['now'])
        finally:
            for p in reversed(patches):p.stop()
        return sim

    def test_blackouts_against_the_unfixed_decision(self):
        for case in SIM['blackouts']:
            with self.subTest(blackout=case['seconds']):
                pair.LATE_ABORTS.clear()
                before=self.run_blackout(case['seconds'],recheck=False)
                pair.LATE_ABORTS.clear()
                after=self.run_blackout(case['seconds'])
                self.assertEqual(bool(before['switches']),case['baseline_switch'],'the unfixed decision reproduces the router')
                self.assertEqual(bool(after['switches']),case['switch'],after['published'][-3:])
                if case['switch']:
                    # the same tick decides; the only delay is the recheck probe of a dead primary
                    added=after['switches'][0]-before['switches'][0]
                    self.assertGreaterEqual(added,0)
                    self.assertLessEqual(added,SIM['max_added_seconds']+1e-9,(before['switches'],after['switches']))
                    self.assertEqual(len(after['rechecks']),1)
                else:
                    aborted=[(t,v) for t,v in after['published'] if v.get('reason')=='PRIMARY-RECOVERED-BEFORE-SWITCH']
                    self.assertTrue(aborted,'the abort is published with its code')
                    self.assertEqual(aborted[0][1]['state'],'OBSERVING')
                    self.assertIn(aborted[0][1]['late_recheck'],('probe','monitor'))
                    self.assertLessEqual(len(after['rechecks']),1,'the same evidence is never probed twice')
                    self.assertEqual(after['published'][-1][1]['reason'],'PAIR-WATCHING','back to watching once the monitor saw the recovery')

    def test_a_primary_that_dies_again_is_left_on_new_evidence(self):
        # down 0-15 s, up 15-17 s (the recheck sees it working), down again from 17 s: the abort memory only waits
        # for the monitor's next samples; three new failures (19.5/23.5/27.5 s, published by 30 s) leave it
        sim=self.run_fault(lambda o:not (0<=o<15 or o>=17))
        self.assertTrue(sim['switches'],sim['published'][-3:])
        self.assertTrue(any(v.get('reason')=='PRIMARY-RECOVERED-BEFORE-SWITCH' for _,v in sim['published']))
        self.assertLessEqual(sim['switches'][0],27.5+SIM['publish_after']+SIM['tick_every']+3*SIM['diagnostic_seconds']+1+1e-9,sim['switches'])

    def test_a_dead_primary_is_never_held_by_a_failing_probe(self):
        sim=self.run_fault(lambda o:o<0)  # down for the whole run
        self.assertTrue(sim['switches'])
        self.assertFalse([v for _,v in sim['published'] if v.get('reason')=='PRIMARY-RECOVERED-BEFORE-SWITCH'])

    def test_a_large_packet_black_hole_is_left_without_a_contradicting_probe(self):
        # mss-sqm x late-switch: the short probe passes on a VPN-MTU primary; it must not hold the failover
        sim=self.run_fault(lambda o:o<0,mtu=True)
        self.assertTrue(sim['switches'],sim['published'][-3:])
        self.assertEqual(sim['rechecks'],[],'the live probe is not asked')
        self.assertFalse([v for _,v in sim['published'] if v.get('reason')=='PRIMARY-RECOVERED-BEFORE-SWITCH'])

if __name__=='__main__':unittest.main()
