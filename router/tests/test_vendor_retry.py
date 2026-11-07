"""A failover the vendor aborted before COMMITTED is retried promptly, not after the cooldown.

MT3000 59-cycle primary-drop soak 03-04.11.2026 (2.1.0-alpha7, Lua runtime), cycle 28: primary VPN-003 at 7.06 s,
journal APPLYING at 19.11 s, BLOCKED VENDOR-WORKER-QUIET-UNVERIFIED and ROLLED-BACK at 20.43 s, then OBSERVING
PAIR-RATE-LIMIT with the primary still failed until ARMED at 81.43 s; COMMITTED at 86.9 s (traffic moved at 84.2 s;
the other 56 failovers 20-35 s). The dispatch charge of the aborted attempt stayed in the ledger and the next failover
waited max(cooldown, min_dwell) = 60 s. Now the charge of a vendor-aborted, rolled-back failover is refunded and the
retry waits a short doubling backoff (5, 10, 20, 40, 60 s); every vendor gate is unchanged.
Lua twin: tests/lua/test_vendor_retry.lua (vendor_retry_cases.json, the same decisions).
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
import telegram_report as report  # noqa: E402
from recovery_settings import normalized, stable_success, stable_seconds  # noqa: E402

CASES=json.loads((HERE/'vendor_retry_cases.json').read_text(encoding='utf-8'))['cases']
LOCK=json.loads((HERE/'vendor_lock_cases.json').read_text(encoding='utf-8'))
PRIMARY='wireguard:peer_2006';RESERVE='openvpn:40354_2029'
QUIET='VENDOR-WORKER-QUIET-UNVERIFIED'
RETRY_BASE=5  # pair_auto.RETRY_BASE (checked in Units); a literal here so the unfixed code fails on the timeline itself


class SharedCases(unittest.TestCase):
    def test_retry_wait_shared_cases(self):
        for case in CASES:
            with self.subTest(case['name']):
                self.assertEqual(pair.retry_wait(case['aborted'],case['events'],case['now'],normalized(case['settings'])),case['wait'])


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

    def ledger(self,value=None):
        if value is not None:agent.atomic_json(self.persist/'pair-auto-budget.json',value)
        return agent.read_json(self.persist/'pair-auto-budget.json',{'events':[]})


class Units(Base):
    def journal(self,**fields):
        value=dict({'phase':'ROLLED-BACK','failure_code':QUIET,'started':9000.0,'pair_transition':{'destination_role':'target'},
                    'rtp_dispatched':False,'forward_policy_touched':False},**fields)
        return patch.object(native,'journal_read',return_value=value)

    def test_charge_returns_its_stamp_and_keeps_the_abort_series(self):
        self.ledger({'events':[8500.0],'aborted':[9000.0]})
        with patch.object(pair.time,'time',return_value=9004.0):
            with self.assertRaisesRegex(native.Refused,'PAIR-RATE-LIMIT'):pair.charge_attempt({},self.revision,limited=False)
        with patch.object(pair.time,'time',return_value=9005.0):
            self.assertEqual(pair.charge_attempt({},self.revision,limited=False),9005.0)
        self.assertEqual(self.ledger(),{'events':[8500.0,9005.0],'aborted':[9000.0]})

    def test_backoff_constants(self):
        self.assertEqual((pair.RETRY_BASE,pair.ABORT_KEEP),(RETRY_BASE,16))
        self.assertEqual(pair.ABORT_REFUND_CODES,native.VERIFY_TRANSIENT,'exactly the transient vendor states of the verify wait')

    def test_no_abort_keeps_the_ledger_format(self):
        with patch.object(pair.time,'time',return_value=9000.0):pair.charge_attempt({},self.revision,limited=False)
        self.assertEqual(self.ledger(),{'events':[9000.0]})

    def test_refund_of_a_vendor_aborted_rolled_back_failover(self):
        self.ledger({'events':[8000.0,9001.0]})
        with self.journal(),patch.object(pair.time,'time',return_value=9002.5):
            self.assertTrue(pair.refund_abort(9001.0,QUIET))
        self.assertEqual(self.ledger(),{'events':[8000.0],'aborted':[9002.5]})

    def test_refund_needs_a_vendor_code_and_a_proven_rollback(self):
        refused=(('code not transient',{},'CLIENT-CONFIRMATION-TIMEOUT'),
                 ('journal committed',{'phase':'COMMITTED','confirmed':9003.0},QUIET),
                 ('rolled back after a confirmation',{'confirmed':9003.0},QUIET),
                 ('another failure',{'failure_code':'VENDOR-WORKER-BUSY'},QUIET),
                 ('not a pair transition',{'pair_transition':None},QUIET),
                 ('a newer transaction',{'started':9001.5},QUIET),
                 # review 04.11.2026 (finding 6): the vendor code came after the switch itself (the verify wait after rtp2,
                 # wait_quiet after the dispatch): two real kernel switches (there and back) are no abort
                 ('after the kernel switch',{'rtp_dispatched':True},QUIET),
                 ('after a policy write',{'forward_policy_touched':True},QUIET),
                 ('a journal without the dispatch flags',{'rtp_dispatched':None},QUIET))
        for name,fields,code in refused:
            with self.subTest(name):
                self.ledger({'events':[8000.0,9001.0]})
                with self.journal(**fields),patch.object(pair.time,'time',return_value=9002.5):
                    self.assertFalse(pair.refund_abort(9001.0,code))
                self.assertEqual(self.ledger(),{'events':[8000.0,9001.0]})
        with self.journal(),patch.object(pair.time,'time',return_value=9002.5):
            self.assertFalse(pair.refund_abort(9000.5,QUIET),'a charge that is not in the ledger')
        self.assertEqual(self.ledger(),{'events':[8000.0,9001.0]})

    def test_the_abort_list_stays_bounded(self):
        self.ledger({'events':[9100.0],'aborted':[8200.0+10*k for k in range(40)]})
        with self.journal(started=9100.0,failure_code='VENDOR-WORKER-BUSY'),patch.object(pair.time,'time',return_value=9101.0):
            self.assertTrue(pair.refund_abort(9100.0,'VENDOR-WORKER-BUSY'))
        aborted=self.ledger()['aborted']
        self.assertEqual(len(aborted),pair.ABORT_KEEP);self.assertEqual(aborted[-1],9101.0)


class Simulation(Base):
    """pair_auto.tick every `step` s. Real: tick's gates, the ledger, charge_attempt, refund_abort, return_hold and the
    committed return. Fake: the transaction (dispatch -> COMMITTED, or the vendor abort: ROLLED-BACK + Refused) and the
    vendor diagnostic (blockers while `busy`)."""
    START=300000.0

    def run_sim(self,primary_up,end,step=2.5,abort=None,busy=None,code=QUIET,settings=None,seen=None,roles=None):
        settings=dict({'pair_auto_mode':pair.MODE,'interval':'10','failure_model':'consecutive'},**(settings or {}))
        pair.request(self.revision)
        state=dict(id=pair.intent()['id'],phase='RUNNING',ran=True,owned=[],before_flags={'wgclient1':'0','ovpnclient1':'0'},network_identity='b'*64,
                   protected={},process_bindings=None,order=['a','b'],policy_hash='c'*64,revision=self.revision,started=self.START-1000)
        if roles:state['policy_roles']=roles
        pair.save(state)
        selection={'source':{'id':PRIMARY},'target':{'id':RESERVE},'vendor_identity':'d'*64,'order':['a','b']}
        sim={'now':self.START,'journal':{'phase':'ROLLED-BACK','started':self.START-2000},'samples':[],'dispatches':[],'aborts':[],
             'switches':[],'returns':[],'published':[],'busy_dispatch':[],'attempts':[]}
        busy=busy or (lambda t:False)
        abort=abort or (lambda sim:False)
        backend=Mock();backend.order.return_value=(state['order'],state['policy_hash'])
        if seen is not None:backend.vendor_busy_seen.side_effect=seen
        backend.diagnostic.side_effect=lambda:((['VENDOR-WORKER-BUSY'],selection) if busy(sim['now']-self.START) else ([],selection))
        backend.health.return_value=True;backend.recheck=None
        backend.recovery_ready.side_effect=lambda identifier,s:(identifier==PRIMARY and stable_success(
            sim['samples'],PRIMARY,normalized(s)['primary_successes'],stable_seconds(s),sim['now'],30))

        def streak(samples,identifier,count,now,age,good,profile=None):
            if identifier!=PRIMARY:return good  # the reserve stays healthy
            own=[x for x in sim['samples'] if x['id']==PRIMARY][-count:]
            return len(own)==count and all((x['code'] is None)==good for x in own)

        def attempt(*args,**kwargs):
            if kwargs.get('pair_return'):raise AssertionError('unexpected kernel-target return')
            sim['attempts'].append(sim['now']-self.START)
            kwargs['on_dispatch']()
            at=sim['now']-self.START
            sim['dispatches'].append(at)
            if busy(at):sim['busy_dispatch'].append(at)
            if abort(sim):
                # the apply step's first diagnostic refused: rolled back before any switch (transaction.lua apply_steps)
                sim['aborts'].append(at)
                sim['journal']={'phase':'ROLLED-BACK','reason':'TRANSACTION-FAILED','failure_code':code,'started':sim['now'],
                                'pair_transition':{'destination_role':'target'},'source':PRIMARY,'target':RESERVE,
                                'rtp_dispatched':False,'forward_policy_touched':False}  # as native_switch.attempt writes them; nothing dispatched
                raise native.Refused(code)
            sim['switches'].append(at)
            sim['journal']={'phase':'COMMITTED','source':PRIMARY,'target':RESERVE,'started':sim['now'],'confirmed':sim['now']}

        def finish(backend_,journal,reason):
            sim['returns'].append((sim['now']-self.START,reason));sim['journal']={'phase':'ROLLED-BACK','started':sim['now']};return True

        patches=[patch.object(pair.time,'time',side_effect=lambda:sim['now']),
                 patch.object(pair.time,'monotonic',side_effect=lambda:sim['now']),patch.object(pair,'_log',side_effect=sim.setdefault('log',[]).append),
                 patch.object(native,'journal_read',side_effect=lambda:dict(sim['journal'])),
                 patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=state['network_identity']),
                 patch.object(pair,'configs',return_value={}),patch.object(pair,'configure_lease',return_value=0),
                 patch('failover_plan.streak',side_effect=streak),patch.object(native,'streak',side_effect=streak),
                 patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}),
                 patch('failure_diagnosis.resolve_pair',return_value={'coordination':{'state':'READY'},'target':{'id':RESERVE},'source':{'id':PRIMARY}}),
                 patch.object(pair_policy,'current_role',side_effect=lambda j:'target' if j.get('phase')=='COMMITTED' else 'source'),
                 patch.object(pair_policy,'metadata',return_value=None),patch.object(pair_policy,'state_order_matches',return_value=True),
                 patch.object(native,'publish',side_effect=lambda value:sim['published'].append((sim['now']-self.START,value))),
                 patch.object(native,'attempt',side_effect=attempt),patch.object(native,'finish_committed',side_effect=finish),
                 patch('pair_manual.consume',return_value=False),patch('pair_manual.held_reserve',return_value=False),
                 patch.object(pair,'revive',return_value=False),patch.object(pair,'server_start',return_value=False)]
        for p in patches:p.start()
        try:
            while sim['now']<self.START+end:
                at=sim['now']-self.START;up=primary_up(at)
                sim['samples'].append({'id':PRIMARY,'time':sim['now'],'code':None if up else 'VPN-003','dns_ok':up,'https_success':2 if up else 0})
                sim['samples'].append({'id':RESERVE,'time':sim['now'],'code':None,'dns_ok':True,'https_success':2})
                pair.tick(backend,settings,self.revision)
                sim['now']+=step
        finally:
            for p in reversed(patches):p.stop()
        return sim


class Cycle28(Simulation):
    def test_cycle_28_vendor_aborted_failover_is_retried_within_seconds(self):
        """Primary cut at 0 s for 150 s; the first dispatched failover is refused by VENDOR-WORKER-QUIET-UNVERIFIED."""
        sim=self.run_sim(lambda t:not 0<=t<150,120,abort=lambda sim:len(sim['dispatches'])==1)
        self.assertEqual(sim['aborts'],[5.0],'detected after three failed samples, aborted by the vendor')
        self.assertEqual(len(sim['switches']),1,sim['dispatches'])
        moved=sim['switches'][0]
        self.assertLessEqual(moved-sim['aborts'][0],RETRY_BASE+2.5,'retried after the short backoff, not the cooldown (alpha7: 60 s)')
        self.assertGreaterEqual(moved-sim['aborts'][0],RETRY_BASE,'never hot: the backoff is kept')
        self.assertLessEqual(moved,35,'within the 20-35 s band of the other 56 soak failovers')
        held=[at for at,v in sim['published'] if v.get('state')=='OBSERVING' and v.get('reason')=='PAIR-RATE-LIMIT' and v.get('source_failures')]
        self.assertEqual(held,[7.5],'the one tick inside the backoff says why it waits')
        self.assertEqual(sim['attempts'],sim['dispatches'],'no transaction is started inside the backoff')
        # the aborted attempt is no switch: the ledger holds the one committed failover; the series is remembered
        ledger=self.ledger()
        self.assertEqual(ledger['events'],[self.START+moved]);self.assertEqual(ledger['aborted'],[self.START+5.0])

    def test_a_non_vendor_failure_still_waits_the_cooldown(self):
        """Only the transient vendor states are refunded: a reserve that never confirmed keeps the cooldown spacing."""
        sim=self.run_sim(lambda t:not 0<=t<150,120,abort=lambda sim:len(sim['dispatches'])==1,code='CLIENT-CONFIRMATION-TIMEOUT')
        self.assertEqual(sim['aborts'],[5.0])
        self.assertGreaterEqual(sim['switches'][0]-5.0,60)

    def test_vendor_busy_blocks_every_dispatch_and_the_retry_follows_when_it_ends(self):
        """After the abort the diagnostic reports VENDOR-WORKER-BUSY 5-40 s: no dispatch while busy, the retry right after."""
        sim=self.run_sim(lambda t:not 0<=t<150,120,abort=lambda sim:len(sim['dispatches'])==1,busy=lambda t:5<t<40)
        self.assertEqual(sim['busy_dispatch'],[])
        self.assertEqual(sim['dispatches'],[5.0,40.0])
        self.assertTrue(any(v.get('state')=='BLOCKED' and v.get('blockers')==['VENDOR-WORKER-BUSY'] for _,v in sim['published']))

    def test_a_vendor_that_never_settles_is_retried_with_a_growing_backoff_never_hot(self):
        sim=self.run_sim(lambda t:t<0,900,abort=lambda sim:True)
        gaps=[b-a for a,b in zip(sim['dispatches'],sim['dispatches'][1:])]
        self.assertEqual(sim['switches'],[])
        self.assertEqual(sim['attempts'],sim['dispatches'],'no transaction is started inside the backoff')
        self.assertTrue(all(g>=RETRY_BASE for g in gaps),gaps)
        self.assertEqual(gaps[:4],[5.0,10.0,20.0,40.0])
        self.assertTrue(all(g==60.0 for g in gaps[4:]),gaps)
        self.assertLessEqual(len(sim['dispatches']),20,'bounded: <= 5 + 15 per 15 min')
        ledger=self.ledger()
        self.assertEqual(ledger['events'],[],'no aborted attempt is counted as a switch')
        self.assertLessEqual(len(ledger['aborted']),pair.ABORT_KEEP)


DEAD={'kind':'rtp-lock-dead','mark':'rtp-lock:9:24680','pid':24680,'workers':1}
ROLES={'source_rule':'a','target_rule':'b','direction':'first','generic_rules':['a','b'],'source_id':PRIMARY,'target_id':RESERVE}


class LongVendorBusy(Simulation):
    """A long VENDOR-WORKER-BUSY: what was seen is visible; the blocker itself stays. Lua: lua/test_vendor_retry.lua."""
    def setUp(self):
        super().setUp()
        pair.BUSY_TRACK[0]=None

    def test_shared_cases(self):
        self.assertEqual((pair.BUSY_SEEN_SECONDS,pair.BUSY_SCAN_SECONDS),(120,30))
        for case in LOCK['cases']:
            with self.subTest(case['name']):
                track=None;got=[];scans=[];last=None
                for index,(now,busy,row) in enumerate(case['ticks']):
                    def observe(scan):
                        if scan:scans.append(index)
                        if row=='raise':raise ValueError('read failed')
                        return row
                    track,last=pair.busy_seen_step(track,busy,now,observe)
                    got.append(last['kind'] if last else None)
                self.assertEqual(got,case['expect']);self.assertEqual(scans,case['scans'])
                self.assertEqual(last.get('workers') if last else None,case['workers'])

    def test_every_kind_has_its_own_code(self):
        self.assertEqual(len(set(pair.BUSY_CODES.values())),5)
        self.assertEqual(pair.BUSY_CODES,{'rtp-lock-dead':'VENDOR-BUSY-RTP-LOCK-DEAD','rtp-lock-live':'VENDOR-BUSY-RTP-LOCK-LIVE',
                                          'tunnel-switch':'VENDOR-BUSY-TUNNEL-SWITCH','workers':'VENDOR-BUSY-WORKERS','unidentified':'VENDOR-BUSY-UNIDENTIFIED'})

    def check_dead_holder(self,roles):
        sim=self.run_sim(lambda t:t<0,1800,busy=lambda t:True,seen=lambda scan:DEAD,roles=roles)
        self.assertEqual((sim['dispatches'],sim['switches'],sim['attempts']),([],[],[]),'the blocker is not bypassed')
        for at,value in sim['published']:
            self.assertEqual(value['state'],'BLOCKED');self.assertEqual(value['blockers'],['VENDOR-WORKER-BUSY'])
            self.assertEqual((value['source'],value['target']),(PRIMARY,RESERVE))
            if at<120:
                self.assertIsNone(value.get('reason'),at);self.assertNotIn('vendor_lock_pid',value)
            else:
                self.assertEqual(value['reason'],'VENDOR-BUSY-RTP-LOCK-DEAD',at);self.assertEqual(value['vendor_lock_pid'],24680)
                self.assertGreaterEqual(value['busy_seconds'],120);self.assertEqual(value['vendor_workers'],1,'the child that still runs is shown')
        self.assertEqual(min(at for at,v in sim['published'] if v.get('reason')),120)
        self.assertEqual(len(sim['log']),1,'one log line, not one per tick')
        self.assertIn('VENDOR-BUSY-RTP-LOCK-DEAD: VENDOR-WORKER-BUSY for 120 s, lock pid 24680, vendor workers seen 1; observed only',sim['log'][0])

    def test_dead_primary_gone_holder_policy_roles_every_normal_session(self):
        self.check_dead_holder(ROLES)

    def test_dead_primary_gone_holder_without_policy_roles(self):
        self.check_dead_holder(None)

    def test_each_observed_cause_reaches_the_publication(self):
        for kind,code in pair.BUSY_CODES.items():
            pair.BUSY_TRACK[0]=None
            sim=self.run_sim(lambda t:t<0,125,busy=lambda t:True,seen=lambda scan,kind=kind:{'kind':kind,'mark':'k'})
            self.assertEqual(sim['published'][-1][1]['reason'],code);self.assertEqual(sim['dispatches'],[])

    def test_the_blocker_ends_the_failover_follows_at_once(self):
        sim=self.run_sim(lambda t:t<0,320,busy=lambda t:t<300,seen=lambda scan:DEAD)
        self.assertEqual(sim['switches'],[300.0])

    def test_one_free_tick_ends_the_episode_also_on_the_tick_path_with_no_blockers(self):
        sim=self.run_sim(lambda t:True,240,busy=lambda t:t<100 or t>=105,seen=lambda scan:DEAD)
        self.assertEqual(min(at for at,v in sim['published'] if v.get('reason')=='VENDOR-BUSY-RTP-LOCK-DEAD'),225,'120 s after the blocker came back')

    def test_a_failing_or_nonsense_observation_is_unidentified_and_changes_nothing(self):
        def failing(scan):raise ValueError('read failed')
        for seen in (failing,lambda scan:'nonsense'):
            pair.BUSY_TRACK[0]=None
            sim=self.run_sim(lambda t:t<0,125,busy=lambda t:True,seen=seen)
            self.assertEqual(sim['published'][-1][1]['reason'],'VENDOR-BUSY-UNIDENTIFIED');self.assertEqual(sim['dispatches'],[])

    def test_a_backend_without_the_observation_never_raises(self):
        value={'state':'BLOCKED'}
        self.assertIs(pair.busy_fields(object(),['VENDOR-WORKER-BUSY'],value),value)


class VendorNotice(Base):
    """The Telegram notice of a long VENDOR-WORKER-BUSY. Lua: lua/test_vendor_retry.lua, the same shared cases."""
    def native(self,reason,**fields):
        return {'native_failover':dict({'state':'BLOCKED','reason':reason,'time':1000.0,'busy_seconds':125,'vendor_lock_pid':24680,'vendor_workers':1},**fields)}

    def test_shared_text_and_key_every_code_has_a_text(self):
        for case in LOCK['notices']:
            self.assertEqual(report.vendor_notice_key(case['native'],1000),case['key'])
            self.assertEqual(report.vendor_notice_text(case['native']),case['text'])
        self.assertEqual(set(report.NOTICE_TEXT),set(pair.BUSY_CODES.values()))
        for text in report.NOTICE_TEXT.values():
            self.assertNotIn('quiet',text.lower());self.assertNotIn('stale',text.lower())

    def test_once_per_cause_and_pid_and_no_schedule_field_moves(self):
        state={'sent':990.0,'confirmed_reports':4}
        with patch.object(report,'send_message') as send:
            out=report.vendor_notice({},self.native('VENDOR-BUSY-RTP-LOCK-DEAD'),state,1001)
            self.assertEqual(send.call_count,1)
            self.assertEqual({k:out.get(k) for k in ('sent','attempt','confirmed_reports','period_keys')},{'sent':990.0,'attempt':None,'confirmed_reports':4,'period_keys':None})
            report.vendor_notice({},self.native('VENDOR-BUSY-RTP-LOCK-DEAD'),state,1002);self.assertEqual(send.call_count,1)
            report.vendor_notice({},self.native('VENDOR-BUSY-RTP-LOCK-DEAD',vendor_lock_pid=24681),state,1003);self.assertEqual(send.call_count,2)
            report.vendor_notice({},self.native('VENDOR-BUSY-RTP-LOCK-LIVE',vendor_lock_pid=24681),state,1004);self.assertEqual(send.call_count,3)
            report.vendor_notice({},{'native_failover':{'state':'OBSERVING','time':1005.0}},state,1005)
            self.assertFalse((self.runtime/report.NOTICE_FILE).exists())
            report.vendor_notice({},self.native('VENDOR-BUSY-RTP-LOCK-LIVE',vendor_lock_pid=24681),state,1006);self.assertEqual(send.call_count,4)

    CONFIG={'telegram_enabled':'1','telegram_chat':'-100','telegram_token':'123:synthetic','telegram_schedule':'interval','telegram_interval':'60','telegram_weekly':'0','telegram_monthly':'0'}

    def test_the_notice_goes_through_deliver_the_schedule_stays_a_backoff_holds_it(self):
        with patch.object(report,'config_snapshot',return_value=self.CONFIG),patch.object(report,'send_message') as send:
            public,state,sent=report.deliver(self.native('VENDOR-BUSY-RTP-LOCK-DEAD'),{'sent':990.0,'attempt':990.0,'retry_after':5.0},1001.0)
            self.assertEqual(send.call_count,1,'told at once');self.assertFalse(sent,'no report was sent');self.assertNotIn('code',public)
            self.assertEqual((state['sent'],state['attempt']),(990.0,990.0),'the report schedule did not move')
            import telegram_state
            self.assertTrue(telegram_state.valid(state),'the sender state keeps its schema')
            (self.runtime/report.NOTICE_FILE).unlink()
            report.deliver(self.native('VENDOR-BUSY-RTP-LOCK-DEAD'),{'sent':990.0,'attempt':1000.0,'retry_after':300.0},1001.0)
            self.assertEqual(send.call_count,1,'the Telegram backoff holds for a notice too')

    def test_only_for_a_fresh_blocked_with_one_of_the_codes(self):
        with patch.object(report,'send_message') as send:
            report.vendor_notice({},self.native('VENDOR-BUSY-WORKERS'),{},1000+report.NOTICE_MAX_AGE+1)
            report.vendor_notice({},self.native('PAIR-WAITING-PROBES'),{},1001)
            report.vendor_notice({},self.native('VENDOR-BUSY-WORKERS',state='ARMED'),{},1001)
            report.vendor_notice({},{},{},1001)
            send.assert_not_called()

    def test_a_failed_send_keeps_the_backoff_and_comes_again(self):
        with patch.object(report,'send_message',side_effect=report.rejection(429,600)):
            out=report.vendor_notice({},self.native('VENDOR-BUSY-WORKERS'),{},1001)
        self.assertEqual((out['last_code'],out['retry_after'],out['attempt'],out['known_failures']),('TELEGRAM-RATE-LIMIT',600,1001,1))
        self.assertFalse((self.runtime/report.NOTICE_FILE).exists())
        with patch.object(report,'send_message') as send:
            report.vendor_notice({},self.native('VENDOR-BUSY-WORKERS'),out,1010);report.vendor_notice({},self.native('VENDOR-BUSY-WORKERS'),out,1020)
            self.assertEqual(send.call_count,1)


class FlapStillDamped(Simulation):
    """Primary down 60 s / up 120 s, ten times, tick 10 s, 30 s stability base (as test_flap_damping): with the first
    failover of every outage aborted by the vendor the return is damped exactly as without the aborts."""
    DOWN=60;UP=120;CYCLES=10

    def up(self,t):
        offset=t-30
        return offset<0 or offset>=(self.DOWN+self.UP)*self.CYCLES or offset%(self.DOWN+self.UP)>=self.DOWN

    def flap(self,aborting):
        state={'last':None}
        def abort(sim):
            outage=int((sim['now']-self.START-30)//(self.DOWN+self.UP))
            first=state['last']!=outage;state['last']=outage
            return aborting and first
        end=30+(self.DOWN+self.UP)*self.CYCLES+300
        return self.run_sim(self.up,end,step=10,abort=abort,settings={'recovery_primary_stable':'30'})

    def on_reserve(self,sim,t):
        last_switch=max([x for x in sim['switches'] if x<=t],default=None)
        last_return=max([x for x,_ in sim['returns'] if x<=t],default=None)
        return last_switch is not None and (last_return is None or last_switch>last_return)

    def test_returns_are_damped_as_without_aborts_and_every_outage_is_left(self):
        plain=self.flap(False)
        self.tearDown_ledger()
        aborted=self.flap(True)
        self.assertTrue(aborted['aborts'],'the vendor aborted failovers')
        self.assertEqual([r for r,_ in aborted['returns']],[r for r,_ in plain['returns']],'the same damped returns')
        self.assertEqual(len(aborted['switches']),len(plain['switches']))
        self.assertLess(len(aborted['returns']),self.CYCLES,'damping kept the reserve through a recovery')
        for k in range(self.CYCLES):
            down=30+k*(self.DOWN+self.UP)
            with self.subTest(outage=down):
                # one tick later than without the abort at most (the 5 s backoff is shorter than a tick)
                self.assertTrue(all(self.on_reserve(aborted,t) for t in range(down+50,down+self.DOWN,10)))
        recovery=normalized({'recovery_primary_stable':'30'})
        holds=[pair.return_hold([self.START+x for x in aborted['switches'] if x<=at],self.START+at,recovery) for at,_ in aborted['returns']]
        self.assertTrue(any(h>=120 for h in holds),holds)

    def tearDown_ledger(self):
        (self.persist/'pair-auto-budget.json').unlink(missing_ok=True)
        pair.LATE_ABORTS.clear()


if __name__=='__main__':unittest.main()
