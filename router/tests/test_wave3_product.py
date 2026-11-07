"""Wave 3 study winners in the product (docs/architecture/WAVE3-PRODUCT-2026-11-04.ru.md): the ledger behind the flap damping,
the pause after a failed supervisor pass, the pass plan (absolute grid, phases, reserve budget) and what they do to the
failover path. Shared cases: probe_plan_cases.json, retry_policy_cases.json, flap_damping_cases.json.
Lua twin: tests/lua/test_wave3_product.lua (run here through lua5.1 when it is installed).
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import agent  # noqa: E402
import failover_plan  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
import probe_plan  # noqa: E402
import recovery_settings as recovery  # noqa: E402
import retry_policy  # noqa: E402

PLAN=json.loads((HERE/'probe_plan_cases.json').read_text(encoding='utf-8'))
RETRY=json.loads((HERE/'retry_policy_cases.json').read_text(encoding='utf-8'))
SOURCE='wireguard:peer_1';TARGET='openvpn:1_1'


class SharedPlan(unittest.TestCase):
    def test_plan(self):
        for case in PLAN['plan']:
            with self.subTest(case['name']):
                got=probe_plan.plan(case['ids'],case['context'],case['settings'])
                self.assertEqual((got['skip'],got['order'],got['offsets']),(case['skip'],case['order'],case['offsets']))

    def test_effective(self):
        for case in PLAN['effective']:
            self.assertEqual(probe_plan.effective_reserve(case['settings'],case['interval'],case['valid_for']),case['every'],case)

    def test_slots(self):
        for case in PLAN['next_slot']:
            planned,delay=probe_plan.next_slot(case['slot'],case['interval'],case['now'])
            self.assertEqual(planned,case['next'],case['name']);self.assertAlmostEqual(delay,case['delay'],places=9)
        for case in PLAN['begin_slot']:
            self.assertEqual(probe_plan.begin_slot(case['expected'],case['now']),case['slot'],case['name'])

    def test_clean_and_carried(self):
        for case in PLAN['clean']:
            self.assertEqual(probe_plan.clean(case['row']),case['clean'],case['name'])
        for case in PLAN['carried']:
            got=probe_plan.carried(case['row'],{'groups':case['groups']})
            self.assertEqual(got is not None,case['kept'],case['name'])


class SharedRetry(unittest.TestCase):
    def test_cases(self):
        for case in RETRY['base']:self.assertEqual(retry_policy.base(case['n']),case['base'])
        for case in RETRY['pause']:
            self.assertAlmostEqual(retry_policy.pause(case['n'],case['settings'],lambda:case['u']),case['pause'],places=9)
        for case in RETRY['count']:
            self.assertEqual(retry_policy.count(case['failures'],case['last'],case['now']),(case['count'],case['now']),case['name'])

    def test_real_draws_stay_inside_the_bounds(self):
        for n in range(1,9):
            for _ in range(200):
                value=retry_policy.pause(n,{})
                self.assertTrue(retry_policy.FLOOR<=value<=retry_policy.base(n),(n,value))

    def test_the_series_of_a_lasting_failure_is_the_study_one(self):
        self.assertEqual([retry_policy.base(n) for n in range(1,8)],[2,2,4,6,10,15,15])


class Ledger(unittest.TestCase):
    """The rate limit and the memory of the damping share one file: neither may disturb the other."""
    def test_the_rate_limit_still_looks_back_15_minutes(self):
        now=100000
        kept,allowed=pair.budget([now-3000,now-2000,now-1000],now,900,3)
        self.assertEqual(kept,[now-3000,now-2000,now-1000],'older failovers stay for the damping')
        self.assertTrue(allowed,'failovers older than 15 min do not count against the rate limit')
        self.assertFalse(pair.budget([now-800,now-500,now-100],now,900,3)[1])

    def test_a_long_flap_can_never_overflow_the_ledger(self):
        # 60 s spacing for two hours, the unlimited failover path: 120 charges. budget refuses a ledger above 16.
        events=[];start=100000
        for index in range(120):
            now=start+60*index
            events,_=pair.budget(events,now,900,3)
            events=events+[now]
            self.assertLessEqual(len(events),16)
        kept,allowed=pair.budget(events,start+60*120,900,3)
        self.assertEqual(len(kept),pair.LEDGER_SIZE)

    def test_a_flap_never_blocks_the_rate_limited_paths_for_an_hour(self):
        # 16 failovers in the hour, none in the last 15 min: manual and the kernel repair are free again
        now=100000;events=[now-3400+100*i for i in range(16)]
        self.assertTrue(pair.budget([x for x in events if now-x>=900],now,900,3)[1])

    def test_failovers_inside_the_rate_window_are_never_dropped_for_older_ones(self):
        now=100000;older=[now-3000-60*i for i in range(14)];recent=[now-100,now-200]
        kept,_=pair.budget(sorted(older+recent),now,900,3)
        self.assertEqual(kept[-2:],[now-200,now-100]);self.assertEqual(len(kept),pair.LEDGER_SIZE)

    def test_older_than_the_memory_is_gone(self):
        now=100000
        self.assertEqual(pair.budget([now-pair.LEDGER_MEMORY,now-pair.LEDGER_MEMORY+1],now)[0],[now-pair.LEDGER_MEMORY+1])

    def test_the_hold_sees_the_memory_through_the_ledger(self):
        # the real chain: ledger -> budget -> return_hold over 59 minutes
        now=100000;settings=recovery.normalized({})
        kept,_=pair.budget([now-3540,now-60],now,900,3)
        self.assertEqual(pair.return_hold(kept,now,settings),240)

    def test_only_failovers_count_for_the_hold(self):
        # review 04.11.2026 (finding 5): [failover, return, failover] over 50 min is two failovers, the documented 240 s, not 480 s
        now=100000;settings=recovery.normalized({})
        events,_=pair.budget([now-3000,now-2800,now-200],now,900,3)
        self.assertEqual(pair.return_hold(events,now,settings),480,'as every charge: the bug')
        self.assertEqual(pair.return_hold(pair.failover_events(events,{'events':events,'others':[now-2800]}),now,settings),240)
        self.assertEqual(pair.failover_events(events,{'events':events}),events,'a ledger of an older package: every charge counts')
        self.assertEqual(pair.failover_events(events,None),events)
        self.assertEqual(pair.failover_events(events,{'others':'junk'}),events)

    def test_the_charges_keep_their_kind_through_the_file(self):
        with tempfile.TemporaryDirectory() as directory:
            persist=Path(directory);revision='r'
            with patch.object(agent,'PERSIST',persist),patch.object(pair,'require_running'),patch.object(pair.time,'time') as clock:
                settings={'recovery_cooldown':'60','recovery_min_dwell':'60'}
                clock.return_value=1000.0;pair.charge_attempt(settings,revision,limited=False)
                clock.return_value=1200.0;pair.charge_attempt(settings,revision,limited=False,failover=False)
                pair.ledger_charge(pair.budget(agent.read_json(persist/'pair-auto-budget.json')['events'],1300.0)[0],1300.0)
                clock.return_value=1400.0;pair.charge_attempt(settings,revision,limited=False)
                row=agent.read_json(persist/'pair-auto-budget.json')
                self.assertEqual(row['events'],[1000.0,1200.0,1300.0,1400.0]);self.assertEqual(row['others'],[1200.0,1300.0])
                self.assertEqual(pair.ledger_hold(settings,1500.0),240,'two failovers: one doubling, not three')
                self.assertEqual(pair.budget(row['events'],1500.0,900,4)[1],False,'the rate limit still sees every charge')
                # an entry that left the events leaves 'others' with it; 'aborted' survives every writer
                agent.atomic_json(persist/'pair-auto-budget.json',{'events':[1200.0],'others':[1200.0,1100.0],'aborted':[1450.0]})
                pair.ledger_charge([1200.0],1500.0,failover=True)
                row=agent.read_json(persist/'pair-auto-budget.json')
                self.assertEqual((row['others'],row['aborted']),([1200.0],[1450.0]))
                pair.ledger_charge([],1600.0)  # the plain charges of the first failover writes no key at all
                agent.atomic_json(persist/'pair-auto-budget.json',{'events':[]})
                pair.ledger_charge([],1700.0,failover=True)
                self.assertEqual(agent.read_json(persist/'pair-auto-budget.json'),{'events':[1700.0]})

    def test_the_supervisors_name_what_is_no_failover(self):
        # the source: the pair_return charge and, in Lua, the kernel repair (the Python repair and the manual charges use ledger_charge)
        python=(LIB/'pair_auto.py').read_text(encoding='utf-8');lua=(LIB/'lua/pair.lua').read_text(encoding='utf-8')
        self.assertIn('pair_return=True,\n                      pair_session_order=state[\'order\'],on_dispatch=lambda:charge_attempt(settings,revision,limited=False,failover=False))',python)
        self.assertIn('pair_return=true,pair_session_order=state.order,\n        on_dispatch=function() M.charge_attempt(env,settings,revision,false,false) end})',lua)
        self.assertIn('pair_reapply=true,\n    on_dispatch=function() M.charge_attempt(env,settings,revision,nil,false) end})',lua)

    def test_a_refund_keeps_the_kinds(self):
        with tempfile.TemporaryDirectory() as directory:
            persist=Path(directory)
            agent.atomic_json(persist/'pair-auto-budget.json',{'events':[1000.0,1200.0],'others':[1000.0]})
            code=next(iter(pair.ABORT_REFUND_CODES))
            journal={'phase':'ROLLED-BACK','failure_code':code,'confirmed':None,'pair_transition':{},'started':1100.0,'rtp_dispatched':False,'forward_policy_touched':False}
            with patch.object(agent,'PERSIST',persist),patch.object(native,'journal_read',return_value=journal),patch.object(pair.time,'time',return_value=1300.0):
                self.assertTrue(pair.refund_abort(1200.0,code))
            self.assertEqual(agent.read_json(persist/'pair-auto-budget.json')['others'],[1000.0])


class Settings(unittest.TestCase):
    def test_defaults(self):
        policy=recovery.normalized({})
        self.assertEqual((policy['flap_model'],policy['flap_limit'],policy['flap_window'],policy['flap_halflife'],policy['flap_suppress'],policy['flap_reuse']),
                         ('double',2,60,1800,1500,500))
        self.assertEqual((policy['attempt_limit'],policy['attempt_window']),(3,15),'the rate limit stays: manual switches and the kernel repair')

    def test_the_page_may_omit_every_flap_field(self):
        values={k:v for k,v in recovery.DEFAULTS.items() if k not in recovery.FLAP_FIELDS}
        self.assertNotIn('recovery_flap_limit',recovery.payload(values)['main'])
        saved=recovery.payload(dict(values,flap_model='halflife',flap_limit=4))['main']
        self.assertEqual((saved['recovery_flap_model'],saved['recovery_flap_limit']),('halflife','4'))
        for bad in ({'flap_model':'fibonacci'},{'flap_window':121},{'flap_limit':0},{'flap_reuse':100}):
            with self.assertRaises(ValueError):recovery.payload(dict(values,**bad))

    def test_saved_ranges(self):
        policy=recovery.normalized({'recovery_flap_halflife':'60','recovery_flap_suppress':'9000','recovery_flap_reuse':'1'})
        self.assertEqual((policy['flap_halflife'],policy['flap_suppress'],policy['flap_reuse']),(600,3000,200))
        self.assertEqual(recovery.normalized({'recovery_flap_model':'fibonacci'})['flap_model'],'double')

    def test_a_preset_saved_by_the_page_does_not_turn_the_damping_back(self):
        # recovery_presets.json (baked into the page) holds attempt_limit 3 / attempt_window 15
        policy=recovery.normalized({'recovery_attempt_limit':'3','recovery_attempt_window':'15'})
        self.assertEqual(pair.return_hold([4000,4900],5000,policy),240)


def good(identifier,stamp):
    return {'id':identifier,'time':stamp,'code':None,'dns_ok':True,'https_success':3}


def bad(identifier,stamp):
    return {'id':identifier,'time':stamp,'code':'VPN-003','dns_ok':False,'https_success':0}


class FailoverPath(unittest.TestCase):
    """Failover impact of the pass plan, measured over many phases of the failure against the plan switched off.
    Real: probe_plan.plan/clean, failover_plan.streak over the published samples with the product age. The failure rule is
    the streak (recovery_failures 3, successes 2), which is the slowest rule; a dense episode only makes the passes denser.
    T=10, valid_for 30, a pass takes PROBE s; the status is published when the pass ends."""
    T=10;AGE=30;PROBE=1.0;FAILED_PROBE=6.0

    def run_timeline(self,settings,death,reserve_dies=None,horizon=240):
        """-> (the time Auto may leave the primary, reserve probes per hour until death, age of the reserve evidence then)"""
        t=0.0;samples=[];source_clean=target_clean=True;reserve_time=None;probes=0;measured_until_death=0
        slot=None;rows_time=None
        while t<horizon:
            context={'interval':self.T,'valid_for':self.AGE,'now':t,'source':SOURCE,'target':TARGET,'native':'OBSERVING',
                     'dense':False,'boost':False,'waiting':False,'source_clean':source_clean,'target_clean':target_clean,
                     'reserve_time':reserve_time}
            plan=probe_plan.plan([SOURCE,TARGET],context,settings)
            end=t
            for identifier,offset in zip(plan['order'],plan['offsets']):
                start=t+offset;probes+=1
                if t<death:measured_until_death+=1
                if identifier==SOURCE:
                    point=good(SOURCE,start) if start<death else bad(SOURCE,start)
                    source_clean=start<death
                else:
                    alive=reserve_dies is None or start<reserve_dies
                    point=good(TARGET,start) if alive else bad(TARGET,start)
                    target_clean=alive;reserve_time=start
                # a failed check waits for its HTTPS answers (6 s), a healthy one takes a second
                end=max(end,start+(self.PROBE if point['code'] is None else self.FAILED_PROBE))
                samples.append(point)
            # the supervisor reads the status published at the end of the pass
            failed=failover_plan.streak(samples,SOURCE,3,end,self.AGE,False)
            healthy=failover_plan.streak(samples,TARGET,2,end,self.AGE,True)
            if failed and healthy:return end,measured_until_death,None
            if failed and not healthy and reserve_dies is not None and end>reserve_dies+60:return None,measured_until_death,None
            slot,delay=probe_plan.next_slot(t if slot is None else slot,self.T,end)
            t=slot
        return None,measured_until_death,None

    def test_the_spread_costs_the_failover_nothing_on_average_and_never_more_than_the_phase(self):
        old=new=0.0;n=0;worst=0.0
        for tenth in range(600,1000,3):
            death=tenth/10.0
            a,_,_=self.run_timeline({'probe_spread':False},death)
            b,_,_=self.run_timeline({},death)
            self.assertIsNotNone(a);self.assertIsNotNone(b)
            old+=a-death;new+=b-death;n+=1;worst=max(worst,b-a)
        print('\nfailover time from the failure, s: spread off %.2f, on %.2f (mean over %d phases), worst one case +%.1f'%(old/n,new/n,n,worst))
        self.assertLessEqual(worst,probe_plan.SPREAD_CAP+.01)
        self.assertLessEqual(new/n,old/n+.5,'a phase shift does not slow periodic sampling on average')

    def test_the_reserve_budget_never_delays_the_failover(self):
        worst=0.0;saved=[]
        for tenth in range(600,1000,3):
            death=tenth/10.0
            a,_,_=self.run_timeline({},death)
            b,probes,_=self.run_timeline({'reserve_probe_interval':60},death)
            self.assertIsNotNone(b);worst=max(worst,b-a);saved.append(probes)
        print('reserve budget R=60 at T=10: worst extra delay of a failover %.1f s'%worst)
        self.assertLessEqual(worst,0.01,'the primary keeps its phase and the reserve evidence stays valid across a skip')

    def test_a_reserve_that_died_in_the_gap_is_never_chosen(self):
        # the reserve dies between its measurements, the primary right after: Auto must not leave for it
        for tenth in range(600,1000,7):
            death=tenth/10.0
            leave,_,_=self.run_timeline({'reserve_probe_interval':60},death,reserve_dies=death-1.0)
            self.assertIsNone(leave,'left for a dead reserve at death=%s'%death)

    def test_the_budget_really_saves_probes(self):
        _,base,_=self.run_timeline({'probe_spread':False},10**6,horizon=3600)
        _,less,_=self.run_timeline({'reserve_probe_interval':60},10**6,horizon=3600)
        print('probes per hour at T=10: every pass %d, R=60 cut to 20 s: %d (-%.0f %%)'%(base,less,100*(1-less/base)))
        self.assertLess(less,base*0.8)
        self.assertGreater(less,base*0.7)

    def test_the_grid_does_not_drift(self):
        # every timer fires 300 ms late: the pass starts stay on the grid; the old rule walks away with the lateness
        slot=None;now=0.0;late=.3;last=None
        for _ in range(1000):
            slot=probe_plan.begin_slot(slot,now);last=slot
            planned,delay=probe_plan.next_slot(slot,self.T,now+1.0)
            slot=planned;now=now+1.0+delay+late
        self.assertAlmostEqual(last,999*self.T,places=6)
        now=0.0
        for _ in range(1000):now=now+1.0+max(1,self.T-1.0)+late
        self.assertGreater(now,1000*self.T+250,'sanity: the former formula drifts')


class Vendor:
    """Every tunnel settled from the first pass: the monitor's own identity check is covered by test_lua/vendor tests."""
    generation='g1'

    def observe(self,before,after,measured,now):
        rows=[dict(row,vendor_tunnel_id=row['id'],vendor_generation=Vendor.generation,vendor_state='SETTLED',vendor_changed_at=1.0,
                   interface=row.get('interface')) for row in measured]
        groups=[{'id':p['id'],'state':'SETTLED','current_profile':p['id'],'generation':Vendor.generation,'changed_at':1.0} for p in before['profiles']]
        return {'version':1,'time':now,'groups':groups,'events':[]},rows


class MonitorWiring(unittest.TestCase):
    """agent.monitor_loop with the real plan; the network is a fake probe. Lua twin: lua/test_wave3_monitor.lua."""
    def passes(self,count,settings=None,fail=None,hook=None,cap=.05):
        import agent
        import icmp_ping
        from contextlib import ExitStack
        import tempfile
        import threading
        import time
        from unittest.mock import patch
        def profile(identifier,interface):
            return dict(id=identifier,section=interface,name=interface,protocol='wireguard',interface=interface,administrative_state='enabled',
                        vendor_tunnel_id=identifier)
        data={'profiles':[profile(SOURCE,'wgclient1'),profile(TARGET,'wgclient2')],'servers':[],'wan_interfaces':[],
              'settings':dict({'interval':10,'checkpoint':900,'probe_limit':4,'plan_enabled':False},**(settings or {}))}
        log=[];statuses=[];current=[0];lock=threading.Lock()
        def probe(item,*args,**kwargs):
            bad=fail is not None and fail(current[0],item['id'])
            with lock:log.append((current[0],item['id'],time.monotonic()))
            return dict(id=item['id'],time=time.time(),device=item['interface'],mark=4096,table='1001',ifindex=7,administrative_state='enabled',
                        code='VPN-003' if bad else None,dns_ok=not bad,https_success=0 if bad else 3,rtt_ms=None if bad else 25)
        real_write=agent.atomic_json
        def write(path,value):
            real_write(path,value)
            if Path(path).name=='status.json' and isinstance(value,dict) and value.get('profiles'):
                statuses.append(value);current[0]+=1
                if hook:hook(current[0],statuses)
                if current[0]>=count:agent.STOP=True
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory)
            for name,value in [('RUNTIME',root),('PERSIST',root),('STOP',False)]:stack.enter_context(patch.object(agent,name,value))
            stack.enter_context(patch('auto_control.RUNTIME',root));stack.enter_context(patch('auto_control.PERSIST',root))
            stack.enter_context(patch.object(agent,'inventory',return_value=data))
            stack.enter_context(patch('website_response.WebsiteSampler'))
            stack.enter_context(patch.object(icmp_ping,'PingSampler'))
            stack.enter_context(patch.object(agent,'probe',side_effect=probe))
            stack.enter_context(patch.object(agent,'restore',return_value=(agent.Accounting(),None)))
            stack.enter_context(patch.object(agent,'sample_counters'));stack.enter_context(patch.object(agent,'sample_wan_counters',return_value=[]))
            stack.enter_context(patch.object(agent,'checkpoint'))
            stack.enter_context(patch.object(agent,'monitor_poll_interval',return_value=0))
            stack.enter_context(patch('telegram_report.deliver',return_value=({'enabled':False},{},False)))
            stack.enter_context(patch('vendor_observation.VendorObserver',Vendor))
            stack.enter_context(patch('reliability.failure_pair_context',return_value={'source':SOURCE,'target':TARGET}))
            stack.enter_context(patch.object(agent,'atomic_json',side_effect=write))
            stack.enter_context(patch.object(probe_plan,'SPREAD_CAP',cap))
            real_write(root/'native-status.json',{'state':'OBSERVING','mode':'continuous-pair','time':time.time()})
            agent.monitor_loop()
        return log,statuses

    def test_the_primary_is_measured_last_at_its_phase(self):
        log,statuses=self.passes(3,cap=1.0)
        first=[x[1] for x in log if x[0]==0];second=[x for x in log if x[0]==1]
        self.assertEqual(first,[SOURCE,TARGET],'no previous pass: as before')
        self.assertEqual([x[1] for x in second],[TARGET,SOURCE])
        self.assertGreaterEqual(second[1][2]-second[0][2],.3)
        self.assertEqual(statuses[1]['probe_plan']['order'],[TARGET,SOURCE])

    def test_option_off_keeps_the_former_order_and_no_phase(self):
        log,statuses=self.passes(3,{'probe_spread':False})
        self.assertEqual(statuses[1]['probe_plan']['offsets'],[0.0,0.0])

    def test_the_reserve_is_carried_with_its_real_time_and_no_invented_sample(self):
        log,statuses=self.passes(3,{'reserve_probe_interval':60})
        self.assertEqual([x[1] for x in log if x[0]==1],[SOURCE],'skipped')
        row=next(r for r in statuses[1]['profiles'] if r['id']==TARGET)
        earlier=next(r for r in statuses[0]['profiles'] if r['id']==TARGET)
        self.assertEqual(row['time'],earlier['time']);self.assertIsNone(row['code'])
        self.assertEqual(len([s for s in statuses[1]['samples'] if s['id']==TARGET]),1)

    def test_a_failed_primary_brings_the_reserve_back_out_of_turn(self):
        log,statuses=self.passes(4,{'reserve_probe_interval':60},fail=lambda index,identifier:index==1 and identifier==SOURCE)
        self.assertEqual([x[1] for x in log if x[0]==1],[SOURCE])
        self.assertEqual(sorted(x[1] for x in log if x[0]==2),sorted([SOURCE,TARGET]))

    def test_a_moved_tunnel_never_keeps_the_old_success(self):
        def hook(done,statuses):
            if done==1:Vendor.generation='g2'
        Vendor.generation='g1'
        try:log,statuses=self.passes(3,{'reserve_probe_interval':60},hook=hook)
        finally:Vendor.generation='g1'
        row=next(r for r in statuses[1]['profiles'] if r['id']==TARGET)
        self.assertEqual(row['code'],'CHECK-LIMIT')
        self.assertIn(TARGET,[x[1] for x in log if x[0]==2])


class FailedPassRest(unittest.TestCase):
    def test_stop_and_a_queued_click_end_the_pause(self):
        import tempfile
        import time
        from unittest.mock import patch
        import native_switch as native
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(native,'RUNTIME',root),patch.object(native,'QUEUED_SEEN',[None]):
                (root/'pair-manual-control.json').write_text('{"state":"QUEUED","id":"a"}',encoding='utf-8')
                started=time.monotonic();native.failed_pass_rest(5);self.assertLess(time.monotonic()-started,1)
                # review 04.11.2026 (finding 4): the same row ends one pause only; a pass failing before consume keeps it
                # QUEUED, and the old fast exit made it a pass right after the other. The test above used to pin that exit.
                started=time.monotonic();native.failed_pass_rest(.5);self.assertGreaterEqual(time.monotonic()-started,.45)
                (root/'pair-manual-control.json').write_text('{"state":"QUEUED","id":"b"}',encoding='utf-8')
                started=time.monotonic();native.failed_pass_rest(5);self.assertLess(time.monotonic()-started,1,'a new click still ends it')
                (root/'pair-manual-control.json').write_text('{"state":"DONE"}',encoding='utf-8')
                started=time.monotonic();native.failed_pass_rest(.5);self.assertGreaterEqual(time.monotonic()-started,.45)
                with patch.object(native,'STOP',True):
                    started=time.monotonic();native.failed_pass_rest(5);self.assertLess(time.monotonic()-started,1)


class QueuedClickExpiry(unittest.TestCase):
    """review 04.11.2026 (finding 4): a pass that fails before consume never reached its 60 s expiry."""
    def setUp(self):
        import pair_manual
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.manual=pair_manual
        for item in (patch.object(agent,'RUNTIME',self.root),):
            item.start();self.addCleanup(item.stop)

    def row(self,state,requested):
        value={'id':'a'*32,'pair':'b'*32,'revision':'c'*32,'direction':'reserve','state':state,'requested':requested,'updated':requested,
               'selection':{'tx':None},'code':None}
        agent.atomic_json(self.manual.path(),value)
        return value

    def test_an_old_queued_click_ends_with_the_code_of_consume(self):
        import auto_control
        now=2000.0
        self.row('QUEUED',now-61)
        with patch.object(self.manual.time,'time',return_value=now),patch.object(auto_control,'RUNTIME',self.root):
            self.assertTrue(self.manual.expire_queued())
        row=self.manual.read();self.assertEqual((row['state'],row['code']),('CANCELLED','PAIR-MANUAL-EXPIRED'))

    def test_a_fresh_click_a_claim_and_a_finished_row_stay(self):
        now=2000.0
        for state,requested in (('QUEUED',now-59),('CLAIMED',now-120),('COMPLETED',now-120)):
            before=self.row(state,requested)
            with patch.object(self.manual.time,'time',return_value=now):self.assertFalse(self.manual.expire_queued(),state)
            self.assertEqual(self.manual.read(),before,state)

    def test_a_damaged_record_never_fails_the_pass(self):
        self.manual.path().write_text('{"state":"QUEUED"}',encoding='utf-8')
        self.assertFalse(self.manual.expire_queued())
        self.manual.path().unlink();self.assertFalse(self.manual.expire_queued())


class FailedPassLoop(unittest.TestCase):
    """The source of native_switch.serve: the failed pass takes the series, not the former flat 5 s."""
    def test_the_loop_counts_and_rests(self):
        text=(LIB/'native_switch.py').read_text(encoding='utf-8')
        self.assertIn('failed_passes,failed_at=retry_policy.count(failed_passes,failed_at,time.monotonic())',text)
        tail=text.split('fence_recovery()\n                    return\n                # A failed pass',1)[1]
        self.assertLess(tail.index('failed_pass_rest(retry_policy.pause(failed_passes,settings))'),tail.index('continue'))
        self.assertLess(tail.index('continue'),tail.index('time.sleep(5)'))


class SharedSources(unittest.TestCase):
    def test_every_new_option_reaches_the_supervisor_and_the_monitor(self):
        policy=(LIB/'native_policy.lua').read_text(encoding='utf-8')
        inventory=(LIB/'inventory.lua').read_text(encoding='utf-8')
        for name in ('recovery_flap_model','recovery_flap_limit','recovery_flap_window','recovery_flap_halflife','recovery_flap_suppress',
                     'recovery_flap_reuse','retry_backoff'):
            self.assertIn("'"+name+"'",policy);self.assertIn('main.'+name+'=',inventory)
        for name in ('probe_spread','reserve_probe_interval'):self.assertIn('main.'+name+'=',inventory)


@unittest.skipUnless(shutil.which('lua5.1'),'Lua 5.1 runtime absent')
class LuaTwin(unittest.TestCase):
    def test_lua_suite(self):
        for name in ('lua/test_wave3_product.lua','lua/test_wave3_monitor.lua'):
            done=subprocess.run(['lua5.1',name],cwd=HERE,capture_output=True,text=True,timeout=120)
            self.assertEqual(done.returncode,0,done.stdout+done.stderr)


if __name__=='__main__':
    unittest.main()
