"""Power cut with a held journal (MT3000 sysrq-b, 31.10.2026, evidence-alpha13-powercut-held.json), Python line.

Before the cut Auto was on, the journal HELD-ON-RESERVE (OPERATOR-MANUAL), the pair session RUNNING. After the
boot the intent (RAM) is gone, the prepared router leaves the VPN clients down (vendor autostart off; the pair
starts them) and the guard refuses an empty device list (UNSAFE-GUARD-DEVICE). Before the fix the pair cleanup
failed on every pass, the journal stayed held and Start/boot resume was refused TRANSACTION-IN-PROGRESS forever.
Now the supervisor starts the pair's own clients, the journal settles without owner action and Start succeeds.
Lua counterpart: tests/lua/test_boot_held.lua.
"""
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch, MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import agent
import auto_control
import boot_resume
import native_switch as native
import pair_auto as pair
import retention_settings
from test_failure_matrix import Backend, TX

IDENTITY='b'*64


class Router(Backend):
    """The failure-matrix router with real tunnel devices: down after the boot, the guard refuses an empty list."""
    def __init__(self,rename=None):
        super().__init__()
        rename=rename or {}
        names={role:rename.get(self.selection[role]['interface'],self.selection[role]['interface']) for role in ('source','target')}
        self.up={name:False for name in names.values()}
        self.iface={self.selection[role]['id']:names[role] for role in ('source','target')}
        self.data['settings']['pair_auto_mode']=pair.MODE
    def devices(self):return sorted(name for name,up in self.up.items() if up)
    def guard(self,devices=None,control_revision=None):
        if devices is not None and not devices:raise native.Refused('UNSAFE-GUARD-DEVICE')
        super().guard(devices,control_revision)
    def health(self,identifier):return self.up.get(self.iface.get(identifier),False)
    def use_process_bindings(self,bindings):pass


class Fixture(unittest.TestCase):
    INTERFACES=dict(pair.INTERFACES)   # the pair state's two clients
    RENAME={}                          # fixture interface -> router interface
    OWNED=('wgclient1','ovpnclient1')
    PHASE='HELD-ON-RESERVE'
    STATE_PHASE='RUNNING'
    PROTECTED={}

    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(retention_settings,'configured_days',return_value=7))
        self.dir=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for name,value in (('PERSIST',self.dir),('RUNTIME',self.dir),('JOURNAL',self.dir/'journal'),('STATE',self.dir/'status'),
                           ('CERT',self.dir/'cert'),('ATTEMPTS',self.dir/'attempts'),('PREPARE',self.dir/'prepare'),('JOURNAL_ALARM',self.dir/'journal-alarm')):
            self.stack.enter_context(patch.object(native,name,value))
            if name in ('RUNTIME','PERSIST'):
                for module in (agent,auto_control):self.stack.enter_context(patch.object(module,name,value))
        self.stack.enter_context(patch.object(native,'RETURN_PAUSE',0))
        self.stack.enter_context(patch.object(native,'STOP',False))
        self.stack.enter_context(patch.object(native,'clear_native_options',return_value=True))
        self.stack.enter_context(patch.object(native.uuid,'uuid4',return_value=MagicMock(hex=TX)))
        self.stack.enter_context(patch.object(native.time,'sleep',lambda s:None))
        self.b=Router(self.RENAME);self.before=self.b.current[:]
        self.ifup=[];self.ifdown=[];self.lines=[];self.live=dict(self.PROTECTED)
        self.rows=rows=[{'.name':name,'proto':proto,'auto':'0','disabled':'0'} for name,proto in self.INTERFACES.items()]
        pair._skip_logged.clear()
        def ubus(args,timeout=5):
            if args[0]=='ifdown':self.ifdown.append(args[1]);self.b.up[args[1]]=False;return b''
            return json.dumps({'up':self.b.up[args[2].rsplit('.',1)[1]],'pending':False}).encode()
        def ifup(argv,revision,timeout=20):
            native.require_control_revision(revision)  # Stop-fenced like the real dispatch
            self.ifup.append(argv[2]);self.b.up[argv[2]]=True
        for target,kwargs in ((pair,dict(network=lambda:[dict(r) for r in rows])),(pair,dict(normalized_network=lambda *a:IDENTITY)),
                              (pair,dict(configs=lambda *a:dict(self.live))),(pair,dict(quiet=lambda *a,**k:None)),(pair,dict(set_disabled=lambda *a,**k:None)),
                              (pair,dict(_log=self.lines.append)),(native,dict(command=ubus)),(native,dict(forward_dispatch=ifup))):
            for name,value in kwargs.items():self.stack.enter_context(patch.object(target,name,side_effect=value))
        # before the cut: the owner's manual switch held on the reserve inside a RUNNING pair session
        self.revision=auto_control.current_revision()
        value={'tx':TX,'phase':self.PHASE,'reason':'OPERATOR-MANUAL' if self.PHASE=='HELD-ON-RESERVE' else None,'before':self.before,
               'after':self.before[:-2]+[self.before[-1],self.before[-2]],'hash':self.b.fingerprint,
               'source':self.b.selection['source']['id'],'target':self.b.selection['target']['id'],
               'deadline':time.time()+60,'monotonic_deadline':None,'trial':False,'pid':None,'started':time.time(),
               'trial_nonce':self.b.data['settings']['native_trial'],'confirmed':time.time()}
        if self.PHASE=='HELD-ON-RESERVE':value['manual_request_id']='ab'*16
        native.journal_write(value);self.b.current=value['after'][:]
        state=dict(id='a'*32,phase=self.STATE_PHASE,ran=True,started=time.time()-600,revision=self.revision,network_identity=IDENTITY,
                   interfaces=dict(self.INTERFACES),protected=dict(self.PROTECTED),owned=list(self.OWNED),
                   before_flags={name:'0' for name in self.INTERFACES},process_bindings=None,order=self.before,policy_hash=self.b.fingerprint)
        if self.STATE_PHASE=='HELD':state['recovery_error']='UNSAFE-GUARD-DEVICE'
        pair.save(state)
        boot_resume.remember(self.dir,now=time.time()-900)
        # the boot: RAM empty (no intent, a new revision), no guard; the tunnels are already down
        (self.dir/'auto-control-revision.json').unlink()
        self.stack.enter_context(patch.object(native,'Linux',return_value=self.b))
        self.stack.enter_context(patch('speed_pause.public',return_value={}))
        self.stack.enter_context(patch('speed_pause.gate',side_effect=self.stop_loop))
        self.stack.enter_context(patch('preparation_control.auto_blocker',return_value=None))
        self.stack.enter_context(patch('preparation_control.auto_prepare',return_value={}))

    def stop_loop(self,name):
        native.STOP=True;return True  # the first loop pass ends serve(): only the boot recovery is under test

    def state(self):return json.loads(native.STATE.read_text())

    def start(self):return auto_control.start(control_revision=auto_control.current_revision(),request_source='programmatic')


class BootHeld(Fixture):

    def test_control_without_the_revive_the_journal_stays_held_and_start_is_refused(self):
        with patch.object(pair,'ensure_devices',return_value=None),patch.object(pair,'boot_devices',return_value=None):
            native.serve()
            for _ in range(5):native.STOP=False;pair.recover(self.b)
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE')
        self.assertEqual(self.state()['blockers'],['UNSAFE-GUARD-DEVICE'])
        self.assertEqual(self.start()['blockers'],['TRANSACTION-IN-PROGRESS'])

    def test_boot_recovery_starts_the_pair_clients_settles_the_journal_and_start_succeeds(self):
        native.serve()
        self.assertEqual(self.ifup,['ovpnclient1','wgclient1'],'the pair started its own two clients')
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('ROLLED-BACK','PAIR-STOPPED'))
        self.assertEqual(self.b.current,self.before)
        self.assertEqual(pair.read_state()['phase'],'STOPPED')
        self.assertEqual(self.ifdown,['ovpnclient1','wgclient1'],'and returned them to the state before the session')
        self.assertNotEqual(self.b.guarded,'full')
        native.STOP=False
        self.assertTrue(self.start()['accepted'])
        self.assertEqual(pair.intent()['mode'],'on')

    def test_boot_resume_waits_for_the_supervisor_and_survives_an_ntp_step(self):
        # the supervisor has not settled the journal yet when the boot resume first presses Start
        mono=[40.0];slept=[]
        def sleep(seconds):
            slept.append(seconds);mono[0]+=seconds
            if len(slept)==2:
                native.STOP=False;pair.recover(self.b)  # the supervisor's pass: revive + cleanup
        real=time.time
        with patch.object(boot_resume.time,'time',side_effect=lambda:real()+(4*3600 if slept else 0)):
            result=boot_resume.run(self.dir,self.dir,sleep=sleep,uptime=40.0,clock=lambda:mono[0])
        self.assertEqual(result,'RESUMED')
        row=json.loads((self.dir/boot_resume.STATE).read_text())
        self.assertEqual((row['state'],row['attempts']),('RESUMED',3))
        self.assertEqual(pair.intent()['mode'],'on')

    def test_a_changed_profile_definition_is_not_acted_on(self):
        state=pair.read_state();state['protected']={'wireguard':'a','ovpnclient':'b'};pair.save(state)
        self.live.update(wireguard='changed',ovpnclient='b')
        native.serve()
        self.assertEqual(self.ifup,[])
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE')
        self.assertIn('PAIR-RECOVERY-REVIVE-SKIPPED: PAIR-EXTERNAL-CONFIG-CHANGE',self.lines)

    def test_a_disabled_or_foreign_row_is_never_started(self):
        self.rows[0]['disabled']='1';self.rows[1]['proto']='static'
        native.serve()
        self.assertEqual(self.ifup,[])
        self.assertTrue(any('PAIR-PROFILES-UNVERIFIED' in line for line in self.lines),self.lines)

    def test_a_client_that_never_comes_up_is_bounded(self):
        clock=[0.0]
        def tick(seconds):clock[0]+=seconds
        with patch.object(native,'forward_dispatch',side_effect=lambda argv,revision,timeout=20:self.ifup.append(argv[2])),\
             patch.object(pair.time,'monotonic',side_effect=lambda:clock[0]),patch.object(pair.time,'sleep',side_effect=tick):
            native.serve()
            for _ in range(5):native.STOP=False;pair.recover(self.b)
        self.assertEqual(self.ifup,['ovpnclient1','wgclient1'],'one attempt per client inside the revive pause')
        self.assertLessEqual(clock[0],pair.DEVICE_WAIT*6+12)
        self.assertNotEqual(self.b.guarded,'full','the LAN is never blocked while waiting')
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE')

    def test_owner_decision_extension_supervisor_restart_resumes_unless_stopped(self):
        ids=iter('%032x'%n for n in range(1,100))
        self.stack.enter_context(patch.object(native.uuid,'uuid4',side_effect=lambda:MagicMock(hex=next(ids))))
        native.serve()
        first=json.loads((self.dir/boot_resume.SUPERVISOR).read_text())['id']
        native.STOP=False
        self.assertTrue(self.start()['accepted']);self.assertEqual(pair.intent()['mode'],'on')
        # kill -9 in idle: procd restarts the supervisor; its recovery fences the intent and writes a fresh token
        native.STOP=False;native.serve()
        self.assertEqual(pair.intent()['mode'],'off')
        self.assertNotEqual(json.loads((self.dir/boot_resume.SUPERVISOR).read_text())['id'],first)
        native.STOP=False
        boot_resume.watch(self.dir,self.dir,sleep=lambda s:None,handled=first,rounds=1)
        self.assertEqual(pair.intent()['mode'],'on','the monitor resumed the owner Auto')
        handled=json.loads((self.dir/boot_resume.STATE).read_text())['supervisor']
        # a deliberate Stop, then another kill: Auto stays off
        native.stop_latch(None)
        native.STOP=False;native.serve()
        native.STOP=False
        boot_resume.watch(self.dir,self.dir,sleep=lambda s:None,handled=handled,rounds=1)
        self.assertEqual(json.loads((self.dir/boot_resume.STATE).read_text())['code'],'AUTO-RESUME-STOPPED')
        self.assertEqual(pair.intent()['mode'],'off')


class VariantC(Fixture):
    """Owner decision 01.11.2026 (variant C): healthy clients kept across the boot cleanup for the boot resume Start.
    Lua counterpart: the variant C tests of tests/lua/test_boot_held.lua."""

    def setUp(self):
        super().setUp()
        self.uptime=[40.0]
        self.stack.enter_context(patch.object(pair,'_uptime',side_effect=lambda:self.uptime[0]))
        self.stack.enter_context(patch.object(pair,'interface_up',side_effect=lambda name:self.b.up.get(name,False)))

    def test_boot_cleanup_keeps_the_healthy_clients_and_the_guard(self):
        native.serve()
        self.assertEqual(self.ifup,['ovpnclient1','wgclient1'])
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('ROLLED-BACK','PAIR-STOPPED'),'the route is restored as before')
        self.assertEqual(self.b.current,self.before)
        state=pair.read_state()
        self.assertEqual(state['phase'],'STOPPED')
        self.assertEqual(self.ifdown,[],'kept for the boot resume Start')
        self.assertEqual((state['kept'],state['kept_flags']),(['wgclient1','ovpnclient1'],{'wgclient1':'0','ovpnclient1':'0'}))
        self.assertEqual(self.b.guarded,'vpn-only','the guard stays')
        self.assertIn('BOOT-RECOVERY-STEP: pair cleanup kept wgclient1 ovpnclient1 at 40.0',self.lines)
        native.STOP=False
        self.assertTrue(self.start()['accepted'])

    def test_the_next_start_adopts_the_kept_clients(self):
        native.serve()
        old=pair.read_state()
        selection={'process_bindings':None,'order':self.before,'hash':self.b.fingerprint,
                   'source':{'interface':'wgclient1'},'target':{'interface':'ovpnclient1'}}
        with patch.object(pair,'preflight',return_value=selection),patch('pair_interfaces.selection',return_value=dict(self.INTERFACES)),\
             patch('pair_policy.proof',return_value=None),patch.object(pair,'require_running'),patch.object(pair,'client_down',side_effect=lambda n:not self.b.up[n]):
            state=pair.begin(self.b,self.b.data['settings'],{'id':'c'*32,'revision':self.revision})
        self.assertNotEqual(state['id'],old['id']);self.assertNotIn('kept',state)
        self.assertEqual(state['owned'],['wgclient1','ovpnclient1'],'still owned: a later Stop returns them')
        self.assertEqual(state['before_flags'],{'wgclient1':'0','ovpnclient1':'0'})
        self.assertEqual(self.ifup,['ovpnclient1','wgclient1'],'no second ifup')

    def test_no_marker_a_newer_stop_or_a_client_down_keeps_the_old_cleanup(self):
        for case in ('no-marker','stop','down'):
            with self.subTest(case=case):
                self.tearDown();self.setUp()
                if case=='no-marker':(self.dir/boot_resume.MARKER).unlink()
                if case=='stop':agent.atomic_json(self.dir/'native-stop.json',{'requested':time.time(),'trial':None})
                if case=='down':self.stack.enter_context(patch.object(pair,'interface_up',side_effect=lambda name:name!='ovpnclient1'))
                native.serve()
                state=pair.read_state()
                self.assertEqual(state['phase'],'STOPPED');self.assertNotIn('kept',state)
                self.assertEqual(self.ifdown,['ovpnclient1','wgclient1'])
                self.assertIsNone(self.b.guarded)

    def test_without_the_start_the_kept_clients_are_released(self):
        for case in ('expiry','stop','failed'):
            with self.subTest(case=case):
                self.tearDown();self.setUp()
                native.serve()
                self.assertEqual(len(pair.read_state()['kept']),2)
                settings=self.b.data['settings']
                self.assertFalse(pair.tick(self.b,settings,auto_control.current_revision()),'kept while the Start is still coming')
                self.assertEqual(self.ifdown,[])
                if case=='expiry':self.uptime[0]+=pair.KEEP_SECONDS
                if case=='stop':agent.atomic_json(self.dir/'native-stop.json',{'requested':time.time(),'trial':None})
                if case=='failed':agent.atomic_json(self.dir/boot_resume.STATE,{'state':'FAILED'})
                self.assertTrue(pair.tick(self.b,settings,auto_control.current_revision()))
                state=pair.read_state()
                self.assertEqual(self.ifdown,['ovpnclient1','wgclient1']);self.assertNotIn('kept',state);self.assertEqual(state['phase'],'STOPPED')
                self.assertIsNone(self.b.guarded)

    def test_the_kept_fields_are_validated(self):
        state=pair.read_state()
        state.update(kept=['wgclient1'],kept_flags={'wgclient1':'0'},kept_at=1.0)
        pair.save(state)
        with self.assertRaisesRegex(ValueError,'PAIR-STATE-UNVERIFIED'):pair.read_state()  # RUNNING
        state['phase']='STOPPED';state['kept_flags']={'wgclient1':'2'};pair.save(state)
        with self.assertRaisesRegex(ValueError,'PAIR-STATE-UNVERIFIED'):pair.read_state()
        state['kept_flags']={'wgclient1':'1'};pair.save(state)
        self.assertEqual(pair.read_state()['kept_flags'],{'wgclient1':'1'})


class VariantD(Fixture):
    """Owner decision 01.11.2026 (variant D): a completed switch on the reserve is handed over to the boot resume Start.
    Lua counterpart: the variant D tests of tests/lua/test_boot_held.lua."""

    def setUp(self):
        super().setUp()
        import pair_policy
        self.policy=pair_policy
        self.uptime=[40.0];self.primary_ok=False
        pair.handover_log_reset()
        self.stack.enter_context(patch.object(pair,'_uptime',side_effect=lambda:self.uptime[0]))
        self.stack.enter_context(patch.object(pair,'interface_up',side_effect=lambda name:self.b.up.get(name,False)))
        # the held journal of a pair session (pair_transition), traffic on the reserve
        sel=self.b.selection
        journal=native.journal_read()
        ctx=pair_policy.transition(sel,self.before,'target')
        journal.update(pair_transition=ctx,after=pair_policy.desired_order(ctx,self.before,'target'))
        native.journal_write(journal);self.b.current=journal['after'][:];self.held=journal
        state=pair.read_state();state['policy_roles']=pair_policy.proof(sel);pair.save(state)
        source,target=sel['source']['id'],sel['target']['id']
        def health(identifier):
            if identifier==target:return self.b.up[self.b.iface[target]]
            return self.primary_ok and self.b.up[self.b.iface[source]]
        self.b.health=health
        self.b.recovery_ready=lambda identifier,settings:health(identifier) is True
        self.b.attest_policy=lambda selection=None:{'verified':self.b.current==self.held['after'] or self.b.current==self.before,
            'role':pair_policy.role(pair_policy.proof(sel),self.b.current),'kernel_fingerprint':'f'*64,'order':self.b.current[:],
            'policy_hash':self.b.fingerprint,'time':time.time()}

    def begin(self):
        selection=dict(self.b.selection,process_bindings=None)
        with patch.object(pair,'preflight',return_value=selection),patch('pair_interfaces.selection',return_value=dict(self.INTERFACES)),\
             patch.object(pair,'require_running'),patch.object(pair,'client_down',side_effect=lambda n:not self.b.up[n]):
            return pair.begin(self.b,self.b.data['settings'],{'id':'c'*32,'revision':auto_control.current_revision()})

    def test_the_held_reserve_is_handed_over_and_the_start_adopts_it(self):
        native.serve()
        old=pair.read_state();held=native.journal_read()
        self.assertEqual(old['phase'],'STOPPED');self.assertEqual(old['handover']['tx'],held['tx'])
        self.assertEqual(old['handover']['order'],self.before)
        self.assertEqual((held['phase'],held['reason']),('HELD-ON-RESERVE','OPERATOR-MANUAL'),'the journal is untouched until the Start')
        self.assertEqual(self.b.current,self.held['after'],'traffic stays on the reserve');self.assertEqual(self.b.guarded,'vpn-only')
        self.assertEqual(self.ifdown,[])
        self.assertTrue(pair.tick(self.b,self.b.data['settings'],auto_control.current_revision()),'waits, touches nothing')
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE')
        native.STOP=False
        self.assertTrue(self.start()['accepted'],'Start accepted without the primary proof')
        state=self.begin()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason'],journal['tx']),('COMMITTED','BOOT-RESERVE-ADOPTED',held['tx']))
        self.assertEqual(journal['boot_adopted']['session'],state['id'])
        self.assertEqual((journal['boot_adopted']['from_phase'],journal['boot_adopted']['from_reason']),('HELD-ON-RESERVE','OPERATOR-MANUAL'))
        self.assertNotIn('manual_request_id',journal)
        self.assertEqual(state['order'],self.before,'the old session order');self.assertEqual(state['owned'],['wgclient1','ovpnclient1'])
        self.assertNotIn('handover',pair.read_state())
        self.assertEqual(self.b.current,self.held['after']);self.assertEqual(self.ifup,['ovpnclient1','wgclient1'],'no second ifup')

    def test_today_s_path_when_the_reserve_or_kernel_is_not_proven_the_primary_is_or_no_marker(self):
        for case in ('reserve-down','kernel','primary-proven','no-marker'):
            with self.subTest(case=case):
                self.tearDown();self.setUp()
                if case=='reserve-down':self.b.health=lambda identifier:False
                if case=='kernel':self.b.attest_policy=lambda selection=None:{'verified':False,'role':None}
                if case=='primary-proven':self.primary_ok=True
                if case=='no-marker':(self.dir/boot_resume.MARKER).unlink()
                with patch.object(native,'finish_committed',return_value=False):native.serve()
                state=pair.read_state()
                self.assertNotIn('handover',state);self.assertEqual(state['phase'],'HELD')
                self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE')

    def test_a_reserve_that_fails_the_fresh_check_at_start_falls_back(self):
        native.serve()
        self.assertIn('handover',pair.read_state())
        self.b.health=lambda identifier:False
        with self.assertRaisesRegex(ValueError,'BOOT-RESERVE-UNVERIFIED'):self.begin()
        state=pair.read_state()
        self.assertEqual(state['phase'],'HELD');self.assertNotIn('handover',state)
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE','not adopted')

    def test_stop_failed_resume_or_expiry_release_the_handover(self):
        for case in ('stop','failed','expiry'):
            with self.subTest(case=case):
                self.tearDown();self.setUp()
                native.serve()
                self.assertIn('handover',pair.read_state())
                if case=='stop':agent.atomic_json(self.dir/'native-stop.json',{'requested':time.time(),'trial':None})
                if case=='failed':agent.atomic_json(self.dir/boot_resume.STATE,{'state':'FAILED'})
                if case=='expiry':self.uptime[0]+=pair.KEEP_SECONDS
                self.assertTrue(pair.tick(self.b,self.b.data['settings'],auto_control.current_revision()))
                state=pair.read_state()
                self.assertNotIn('handover',state);self.assertEqual(state['phase'],'HELD')
                native.STOP=False
                self.assertEqual(self.start()['blockers'],['TRANSACTION-IN-PROGRESS'])

    def test_interrupted_switch_never_and_start_accepts_only_the_handed_over_journal(self):
        journal=dict(self.held,phase='WAIT-CLIENT')
        self.assertFalse(pair.boot_handover(self.b,pair.read_state(),journal,self.policy.metadata(journal)))
        native.serve()
        state=pair.read_state()
        self.assertTrue(pair.handover_matches(state,native.journal_read()))
        self.assertFalse(pair.handover_matches(state,dict(native.journal_read(),tx='9'*32)))
        self.assertFalse(pair.handover_matches(state,dict(native.journal_read(),phase='WAIT-CLIENT')))

    # 01.11.2026 (MT3000 beta3 cut: no handover, no reason): bounded retry on every cleanup pass, each refusal logged once
    def refusals(self):
        return [m.group(1) for m in (re.match('^BOOT-RECOVERY-STEP: handover refused (.*) at ',l) for l in self.lines) if m]

    def cleanup_pass(self,seconds):
        self.uptime[0]+=seconds
        pair.tick(self.b,self.b.data['settings'],auto_control.current_revision())

    def test_retry_the_reserve_not_healthy_at_the_first_pass_is_handed_over_later(self):
        probe=self.b.health;ready=[False];target=self.b.selection['target']['id']
        self.b.health=lambda identifier:None if identifier==target and not ready[0] else probe(identifier)
        with patch.object(native,'finish_committed',return_value=False):
            native.serve()
            self.assertNotIn('handover',pair.read_state())
            for _ in range(3):self.cleanup_pass(2)
            self.assertEqual(self.refusals(),['RESERVE-HEALTH UNKNOWN'],'one line per reason, not per pass')
            ready[0]=True
            self.cleanup_pass(2)
        state=pair.read_state()
        self.assertEqual(state['phase'],'STOPPED');self.assertIn('handover',state)
        self.assertEqual(json.loads((self.dir/pair.HANDOVER_FILE).read_text())['state'],'handed')

    def test_retry_the_primary_client_still_connecting_does_not_block(self):
        self.stack.enter_context(patch.object(pair,'interface_up',side_effect=lambda name:name!='wgclient1'))
        native.serve()
        state=pair.read_state()
        self.assertIn('handover',state);self.assertEqual(state['kept'],['wgclient1','ovpnclient1'])

    def test_retry_is_bounded_then_today_s_path(self):
        probe=self.b.health;ready=[False];target=self.b.selection['target']['id']
        self.b.health=lambda identifier:False if identifier==target and not ready[0] else probe(identifier)
        with patch.object(native,'finish_committed',return_value=False):
            native.serve()
            for _ in range(8):self.cleanup_pass(10)
            self.assertEqual(json.loads((self.dir/pair.HANDOVER_FILE).read_text())['state'],'refused')
            ready[0]=True
            self.cleanup_pass(2)
        state=pair.read_state()
        self.assertNotIn('handover',state);self.assertEqual(state['phase'],'HELD')
        self.assertEqual(self.refusals(),['RESERVE-HEALTH false','WAIT-OVER after RESERVE-HEALTH false'])

    def test_every_refusal_names_its_reason(self):
        for case,want in (('kernel','KERNEL '),('primary','PRIMARY-PROVEN'),('marker','AUTO-RESUME-NOT-REQUESTED')):
            with self.subTest(case=case):
                self.tearDown();self.setUp()
                if case=='kernel':self.b.attest_policy=lambda selection=None:{'verified':False,'code':'KERNEL-POLICY-UNVERIFIED'}
                if case=='primary':self.primary_ok=True
                if case=='marker':(self.dir/boot_resume.MARKER).unlink()
                with patch.object(native,'finish_committed',return_value=False):native.serve()
                self.assertTrue(self.refusals() and self.refusals()[0].startswith(want),self.refusals())

    def test_the_handover_fields_are_validated(self):
        state=pair.read_state()
        state['handover']={'tx':'a'*32,'order':state['order'],'policy_hash':state['policy_hash'],'at':1.0}
        pair.save(state)
        with self.assertRaisesRegex(ValueError,'PAIR-STATE-UNVERIFIED'):pair.read_state()  # RUNNING
        state['phase']='STOPPED';state['handover']['order']=list(reversed(state['order']));pair.save(state)
        with self.assertRaisesRegex(ValueError,'PAIR-STATE-UNVERIFIED'):pair.read_state()
        state['handover']['order']=state['order'];pair.save(state)
        self.assertEqual(pair.read_state()['handover']['tx'],'a'*32)


class Alpha14PowerCut(Fixture):
    """evidence-alpha14-powercut-committed.json: COMMITTED journal (reason null), pair HELD with owned [],
    both clients (wgclient1, ovpnclient2) down, no revive ledger; the vendor rewrote wireless and the network."""
    INTERFACES={'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}
    RENAME={'ovpnclient1':'ovpnclient2'}
    OWNED=()
    PHASE='COMMITTED'
    STATE_PHASE='HELD'
    PROTECTED={'wireguard':'w1','ovpnclient':'o1','wireless':'before','dhcp':'d','gl-dns-v2':'g'}

    def test_settles_without_owner_action_and_start_succeeds(self):
        self.live['wireless']='rewritten-by-the-repeater-at-boot'
        self.assertFalse((self.dir/'pair-revive.json').exists())
        with patch.object(pair,'normalized_network',return_value='c'*64):
            native.serve()
        self.assertEqual(self.ifup,['ovpnclient2','wgclient1'],self.lines)
        self.assertIn('PAIR-RECOVERY-REVIVE: ifup ovpnclient2',self.lines)
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('ROLLED-BACK','PAIR-STOPPED'))
        self.assertEqual(self.b.current,self.before)
        self.assertEqual(pair.read_state()['phase'],'STOPPED')
        self.assertEqual(self.ifdown,[],'clients the session did not own stay up, as before the session')
        native.STOP=False
        self.assertTrue(self.start()['accepted'])

    def test_control_without_the_revive_stays_committed(self):
        with patch.object(pair,'ensure_devices',return_value=None),patch.object(pair,'boot_devices',return_value=None):
            with self.assertRaises(native.Refused):native.serve()  # the COMMITTED guard refuses: procd restart loop
        self.assertEqual(native.journal_read()['phase'],'COMMITTED')
        native.STOP=False
        self.assertEqual(self.start()['blockers'],['TRANSACTION-IN-PROGRESS'])


class NtpWindow(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for module in (agent,auto_control):
            p=patch.object(module,'RUNTIME',self.root);p.start();self.addCleanup(p.stop)
            if hasattr(module,'PERSIST'):p=patch.object(module,'PERSIST',self.root);p.start();self.addCleanup(p.stop)
        p=patch.object(pair,'intent',return_value={'mode':'off'});p.start();self.addCleanup(p.stop)
        p=patch.object(auto_control,'current_revision',return_value='a'*32);p.start();self.addCleanup(p.stop)
        boot_resume.remember(self.root,now=500)

    def test_a_forward_wall_clock_step_does_not_end_the_window(self):
        busy={'accepted':False,'blockers':['TRANSACTION-IN-PROGRESS']}
        replies=[busy]*5+[{'accepted':True}]
        mono=[60.0]
        def sleep(s):mono[0]+=s
        real=time.time
        with patch.object(auto_control,'start',side_effect=lambda **kw:replies.pop(0)) as start,\
             patch.object(time,'time',side_effect=lambda:real()+(5*3600 if mono[0]>60 else 0)):
            self.assertEqual(boot_resume.run(self.root,self.root,sleep=sleep,uptime=60.0,clock=lambda:mono[0]),'RESUMED')
        self.assertEqual(start.call_count,6)

    def test_window_lasts_until_fifteen_minutes_of_uptime(self):
        busy={'accepted':False,'blockers':['PAIR-RECOVERY-REQUIRED']}
        mono=[60.0]
        def sleep(s):mono[0]+=s
        with patch.object(auto_control,'start',return_value=busy):
            self.assertEqual(boot_resume.run(self.root,self.root,sleep=sleep,uptime=60.0,clock=lambda:mono[0]),'FAILED')
        self.assertGreater(mono[0],boot_resume.UNTIL_UPTIME)
        self.assertLessEqual(mono[0],boot_resume.UNTIL_UPTIME+boot_resume.EVERY)


if __name__=='__main__':
    unittest.main()
