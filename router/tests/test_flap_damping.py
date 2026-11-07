"""Flap damping: the attempt limit never blocks leaving a failed primary; it slows the return instead.

MT3000 flap test 02.11.2026 (2.1.0-alpha5, primary WireGuard 60 s down / 120 s up, 10 times): Auto switched at
~30, 217 and 395 s and came back after ~70-80 s of primary health each time; the persistent budget (3 failovers per
15 minutes) was then exhausted and the outages at ~547, 728 and 906 s were NOT left (traffic stayed on the dead
primary, PAIR-RATE-LIMIT) until the oldest failover aged out (933 s). Like RFC 2439/7196 route-flap damping the
failover is now always made and the hold before the RETURN grows instead.
Lua twin: tests/lua/test_flap_damping.lua (flap_damping_cases.json, the same decisions).
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
from recovery_settings import normalized, stable_success, stable_seconds  # noqa: E402

CASES=json.loads((HERE/'flap_damping_cases.json').read_text(encoding='utf-8'))['cases']
PRIMARY='wireguard:peer_2002';RESERVE='openvpn:40354_2016'


class SharedCases(unittest.TestCase):
    def test_return_hold_shared_cases(self):
        for case in CASES:
            with self.subTest(case['name']):
                self.assertEqual(pair.return_hold(case['events'],case['now'],normalized(case['settings'])),case['hold'])


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

    def ledger(self,events=None):
        if events is not None:agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':events})
        return agent.read_json(self.persist/'pair-auto-budget.json',{'events':[]})['events']


class Units(Base):
    def test_charge_without_limit_keeps_cooldown_spacing_only(self):
        self.ledger([9000,9100,9200])
        with patch.object(pair.time,'time',return_value=9300):
            with self.assertRaisesRegex(native.Refused,'PAIR-RATE-LIMIT'):pair.charge_attempt({},self.revision)
            pair.charge_attempt({},self.revision,limited=False)
        self.assertEqual(self.ledger(),[9000,9100,9200,9300])
        with patch.object(pair.time,'time',return_value=9359):
            with self.assertRaisesRegex(native.Refused,'PAIR-RATE-LIMIT'):pair.charge_attempt({},self.revision,limited=False)
        self.assertEqual(self.ledger(),[9000,9100,9200,9300],'a failed attempt is still retried at most once per cooldown')

    def test_ledger_hold_reads_the_ledger_and_an_unreadable_one_holds_longest(self):
        self.assertEqual(pair.ledger_hold({},5000),120,'default primary_stable 120 s since 03.11.2026')
        self.assertEqual(pair.ledger_hold({'recovery_primary_stable':'30'},5000),30)
        self.ledger([4600,4900]);self.assertEqual(pair.ledger_hold({},5000),240,'the second failover within the hour (wave 3)')
        self.assertEqual(pair.ledger_hold({'recovery_primary_stable':'30'},5000),60)
        self.ledger([-1]);self.assertEqual(pair.ledger_hold({},5000),pair.HOLD_CAP)

    def decision_backend(self,ready):
        backend=Mock();backend.health.return_value=True
        backend.recovery_ready.side_effect=lambda identifier,settings:ready(stable_seconds(settings))
        return backend

    def decide(self,backend,hold,now=1000,reserve_failed=False,settings=None):
        journal={'source':PRIMARY,'target':RESERVE,'confirmed':900}
        with patch('failure_diagnosis.resolve_pair',return_value={'coordination':{'state':'READY'},'target':{'id':RESERVE},'source':{'id':PRIMARY}}), \
             patch.object(native,'streak',return_value=reserve_failed):
            settings=dict({'failure_model':'consecutive'},**(settings or {'recovery_primary_stable':'30'}))  # native.streak is stubbed: the previous rule
            return native.committed_recovery_decision(backend,journal,settings,[],now,{},hold=hold)

    def test_damped_return_needs_the_longer_stability_and_reports_the_hold(self):
        backend=self.decision_backend(lambda stable:stable<=60)
        self.assertEqual(self.decide(backend,30)['reason'],'PRIMARY-STABLY-RECOVERED')
        self.assertEqual(self.decide(backend,60)['reason'],'PRIMARY-STABLY-RECOVERED')
        self.assertEqual(self.decide(backend,120),{'action':'OBSERVE','reason':'PAIR-RATE-LIMIT'})
        self.assertEqual(backend.recovery_ready.call_args[0][1]['recovery_primary_stable'],120)
        self.assertEqual(self.decide(backend,None)['reason'],'PRIMARY-STABLY-RECOVERED','legacy callers are unchanged')

    def test_a_failing_reserve_is_left_without_the_damped_hold(self):
        backend=self.decision_backend(lambda stable:stable<=30)
        self.assertEqual(self.decide(backend,600,reserve_failed=True)['reason'],'RESERVE-FAILED-PRIMARY-VERIFIED')

    def test_planned_return_also_waits_for_the_cooldown(self):
        backend=self.decision_backend(lambda stable:True)
        settings={'recovery_cooldown':'300','recovery_primary_stable':'30'}
        self.assertEqual(self.decide(backend,30,now=1100,settings=settings)['action'],'OBSERVE')
        self.assertEqual(self.decide(backend,30,now=1200,settings=settings)['action'],'RESTORE-PRIMARY')
        self.assertEqual(self.decide(backend,None,now=1100,settings=settings)['action'],'RESTORE-PRIMARY','legacy: min_dwell only')


class FlapSimulation(Base):
    """pair_auto.tick every 10 s against a primary that is down 60 s / up 120 s, ten times (the router test).

    Real: tick's gates, the ledger, return_hold, committed_recovery_decision and stable_success over the samples.
    Fake: the transaction (attempt -> COMMITTED, finish_committed -> ROLLED-BACK) and the vendor diagnostic."""
    START=100000.0;DOWN=60;UP=120;CYCLES=10

    def primary_up(self,t):
        offset=t-self.START-30
        return offset<0 or offset>=(self.DOWN+self.UP)*self.CYCLES or offset%(self.DOWN+self.UP)>=self.DOWN

    def run_flaps(self,settings=None,base=None):
        # the damping mechanism is checked on its 30 s base (the default before 03.11.2026); base={} = today's defaults;
        # failure_model 'consecutive': streak is stubbed (the previous rule decides)
        settings=dict({'pair_auto_mode':pair.MODE,'interval':'10','failure_model':'consecutive'},**({'recovery_primary_stable':'30'} if base is None else base),**(settings or {}))
        pair.request(self.revision)
        state=dict(id=pair.intent()['id'],phase='RUNNING',owned=[],before_flags={'wgclient1':'0','ovpnclient1':'0'},network_identity='b'*64,
                   protected={},process_bindings=None,order=['a','b'],policy_hash='c'*64,revision=self.revision)
        pair.save(state)
        selection={'source':{'id':PRIMARY},'target':{'id':RESERVE},'vendor_identity':'d'*64,'order':['a','b']}
        sim={'now':self.START,'journal':{},'samples':[],'switches':[],'returns':[],'published':[]}
        backend=Mock();backend.diagnostic.return_value=([],selection);backend.order.return_value=(state['order'],state['policy_hash'])
        backend.health.return_value=True
        backend.recovery_ready.side_effect=lambda identifier,s:(identifier==PRIMARY and stable_success(
            sim['samples'],PRIMARY,normalized(s)['primary_successes'],stable_seconds(s),sim['now'],30))

        def streak(samples,identifier,count,now,age,good,profile=None):
            if identifier!=PRIMARY:return good  # the reserve stays healthy
            own=[x for x in sim['samples'] if x['id']==PRIMARY][-count:]
            return len(own)==count and all((x['code'] is None)==good for x in own)

        def attempt(*args,**kwargs):
            kwargs['on_dispatch']()
            if kwargs.get('pair_return'):raise AssertionError('unexpected kernel-target return')
            sim['switches'].append(sim['now'])
            sim['journal']={'phase':'COMMITTED','source':PRIMARY,'target':RESERVE,'started':sim['now'],'confirmed':sim['now']}

        def finish(backend_,journal,reason):
            sim['returns'].append((sim['now'],reason));sim['journal']={'phase':'ROLLED-BACK'};return True

        patches=[patch.object(pair.time,'time',side_effect=lambda:sim['now']),
                 patch.object(native,'journal_read',side_effect=lambda:dict(sim['journal'])),
                 patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=state['network_identity']),
                 patch.object(pair,'configs',return_value={}),patch.object(pair,'configure_lease',return_value=0),
                 patch('failover_plan.streak',side_effect=streak),patch.object(native,'streak',side_effect=streak),
                 patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),
                 patch('failure_diagnosis.resolve_pair',return_value={'coordination':{'state':'READY'},'target':{'id':RESERVE},'source':{'id':PRIMARY}}),
                 patch.object(pair_policy,'current_role',side_effect=lambda j:'target' if j.get('phase')=='COMMITTED' else 'source'),
                 patch.object(pair_policy,'metadata',return_value=None),patch.object(pair_policy,'state_order_matches',return_value=True),
                 patch.object(native,'publish',side_effect=lambda value:sim['published'].append((sim['now'],value))),
                 patch.object(native,'attempt',side_effect=attempt),patch.object(native,'finish_committed',side_effect=finish),
                 patch('pair_manual.consume',return_value=False),patch('pair_manual.held_reserve',return_value=False),
                 patch.object(pair,'revive',return_value=False),patch.object(pair,'server_start',return_value=False)]
        for p in patches:p.start()
        try:
            end=self.START+30+(self.DOWN+self.UP)*self.CYCLES+300
            while sim['now']<end:
                up=self.primary_up(sim['now'])
                sim['samples'].append({'id':PRIMARY,'time':sim['now'],'code':None if up else 'VPN-003','dns_ok':up,'https_success':2 if up else 0})
                sim['samples'].append({'id':RESERVE,'time':sim['now'],'code':None,'dns_ok':True,'https_success':2})
                pair.tick(backend,settings,self.revision)
                sim['now']+=10
        finally:
            for p in reversed(patches):p.stop()
        return sim

    def outages(self):
        period=self.DOWN+self.UP
        return [self.START+30+k*period for k in range(self.CYCLES)]

    def on_reserve(self,sim,t):
        """Traffic is on the reserve at t: the last switch before t is after the last return before t."""
        last_switch=max([x for x in sim['switches'] if x<=t],default=None)
        last_return=max([x for x,_ in sim['returns'] if x<=t],default=None)
        return last_switch is not None and (last_return is None or last_switch>last_return)

    def test_every_outage_is_left_for_the_reserve(self):
        sim=self.run_flaps()
        for down in self.outages():
            # Detection needs 3 failed checks (<=30 s); after that traffic is never on the dead primary.
            with self.subTest(outage=down-self.START):
                self.assertTrue(all(self.on_reserve(sim,t) for t in range(int(down)+40,int(down)+self.DOWN,10)),
                                'traffic stayed on the dead primary: switches %s'%[x-self.START for x in sim['switches']])
        self.assertFalse([v for _,v in sim['published'] if v.get('reason')=='PAIR-RATE-LIMIT' and v.get('state')=='OBSERVING' and v.get('source_failures')],
                         'the limit never holds traffic on a failed primary')

    def test_returns_wait_progressively_longer_and_never_ping_pong_faster_than_the_hold(self):
        sim=self.run_flaps()
        recovery=normalized({'recovery_primary_stable':'30'})
        holds=[]
        for at,reason in sim['returns']:
            self.assertEqual(reason,'PRIMARY-STABLY-RECOVERED')
            switch=max(x for x in sim['switches'] if x<at)
            # The hold that applied: the ledger as it was when the return was decided.
            events=[x for x in sim['switches'] if x<=at]
            hold=pair.return_hold(events,at,recovery);holds.append(hold)
            healthy_since=at
            while self.primary_up(healthy_since-10):healthy_since-=10
            self.assertGreaterEqual(at-healthy_since,hold,'returned after %s s of primary health, hold %s'%(at-healthy_since,hold))
            self.assertGreaterEqual(at-switch,60,'minimum dwell')
        self.assertIn(30,holds);self.assertTrue(any(h>=120 for h in holds),holds)
        # Damping kept traffic on the reserve through at least one 120 s recovery instead of returning each time.
        self.assertLess(len(sim['returns']),self.CYCLES,sim['returns'])
        self.assertEqual(len(sim['switches']),len(sim['returns'])+(1 if self.on_reserve(sim,sim['now']) else 0))
        # Damping decays: after the quiet tail the primary is back.
        self.assertFalse(self.on_reserve(sim,sim['now']),'returned after the flaps stopped')

    def test_default_120_s_stability_stays_on_the_reserve_through_the_whole_flap(self):
        """Defaults of 03.11.2026 (primary_stable 120 s): the 120 s recoveries are never long enough to return into the
        next 60 s outage - one failover, every outage covered, one return after the flaps stop (study: 8 -> 1)."""
        sim=self.run_flaps(base={})
        for down in self.outages():
            with self.subTest(outage=down-self.START):
                self.assertTrue(all(self.on_reserve(sim,t) for t in range(int(down)+40,int(down)+self.DOWN,10)))
        self.assertEqual(len(sim['switches']),1,[x-self.START for x in sim['switches']])
        self.assertEqual([r for _,r in sim['returns']],['PRIMARY-STABLY-RECOVERED'])
        self.assertFalse(self.on_reserve(sim,sim['now']),'returned after the flaps stopped')

    def test_strictest_limit_still_leaves_every_outage_and_keeps_the_ledger_bounded(self):
        sim=self.run_flaps({'recovery_flap_limit':'1'})
        for down in self.outages():
            with self.subTest(outage=down-self.START):
                self.assertTrue(all(self.on_reserve(sim,t) for t in range(int(down)+40,int(down)+self.DOWN,10)))
        self.assertLessEqual(len(self.ledger()),15)


if __name__=='__main__':unittest.main()
