"""Failure matrix for switching, rollback, buttons and the supervisor.

Offline only: the vendor policy, nft, probes, processes and files are simulated. Each test injects one
fault (hang, timeout, stop, external change, broken rollback, corrupt files, malformed network reply,
unreadable settings) and checks that the route ends on a known order, the LAN is never left fully
blocked by a finished step, and the public state says what happened.
"""
import http.client
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch, MagicMock

ROOT=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(ROOT))
import native_switch as native
import auto_control

TX='t'*32


def fixture():
    profiles=[{'id':'openvpn:1_1','interface':'ovpnclient1'},{'id':'wireguard:peer_2','interface':'wgclient1'}]
    sections=[{'.name':'global','.type':'policy','enabled':'1'},
              {'.name':'default','.type':'default','enabled':'0','via':'novpn'},
              {'.name':'a','.type':'rule','enabled':'1','killswitch':'1','via':'ovpnclient1'},
              {'.name':'b','.type':'rule','enabled':'1','killswitch':'1','via':'wgclient1'}]
    return {'sections':sections,'settings':{'plan_source':profiles[0]['id'],'plan_target':profiles[1]['id'],
        'native_order_direction':'first','native_baseline_exit':'8.8.8.8','native_trial':'a'*32},'ipv6':'0','lan':'br-lan','firewall_defaults':[{}]},profiles


class Backend:
    """Simulated router: order of two VPN rules, guard state and the calls made."""
    def __init__(self):
        self.data,self.profiles=fixture();self.selection=native.choose(self.data,self.profiles)
        self.current=self.selection['order'][:];self.fingerprint=self.selection['hash'];self.calls=[]
        self.guarded=None;self.fail_reorder=0;self.fail_apply=False;self.blockers=[];self.healthy=True
    def policy(self):return self.data
    def order(self):return self.current[:],self.fingerprint
    def guard(self,devices=None):self.calls.append(('guard',devices));self.guarded='full' if devices is None else 'vpn-only'
    def unguard(self):self.calls.append(('unguard',));self.guarded=None
    def reorder(self,order):
        self.calls.append(('reorder',order))
        if self.fail_reorder:self.fail_reorder-=1;raise native.Refused('POLICY-IDENTITY-CHANGED')
        self.current=list(order)
    def apply(self):
        self.calls.append(('apply',))
        if self.fail_apply:raise subprocess.CalledProcessError(1,'rtp2.sh')
    def devices(self):return ['wgclient1','tun0']
    def diagnostic(self):return list(self.blockers),self.selection
    def health(self,identifier):return self.healthy
    def recovery_ready(self,identifier,settings):return self.health(identifier) is True
    def candidates(self):return []
    def acceleration(self):return {'loaded':[],'hnat_runtime':'unknown'}


class Matrix(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.dir=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for name,value in (('PERSIST',self.dir),('RUNTIME',self.dir),('JOURNAL',self.dir/'journal'),('STATE',self.dir/'status'),
                           ('CERT',self.dir/'cert'),('ATTEMPTS',self.dir/'attempts'),('PREPARE',self.dir/'prepare'),('JOURNAL_ALARM',self.dir/'journal-alarm')):
            self.stack.enter_context(patch.object(native,name,value))
        self.killpg=self.stack.enter_context(patch.object(native.os,'killpg'))
        self.stack.enter_context(patch.object(native,'RETURN_PAUSE',0))
        self.stack.enter_context(patch.object(native,'clear_native_options',return_value=True))
        self.stack.enter_context(patch.object(native.uuid,'uuid4',return_value=MagicMock(hex=TX)))
        self.stack.enter_context(patch.object(native.time,'sleep',lambda s:None))
        self.b=Backend();self.before=self.b.current[:]

    def state(self):return json.loads(native.STATE.read_text())

    def spawn(self,process,after_spawn=None):
        def run(*a,**k):
            self.b.current[-2],self.b.current[-1]=self.b.current[-1],self.b.current[-2]
            if after_spawn:after_spawn()
            return process
        return self.stack.enter_context(patch.object(native.subprocess,'Popen',side_effect=run))

    def confirm(self,**over):
        value=dict({'tx':TX,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'time':time.time()},**over)
        native.atomic_json(native.RUNTIME/'native-confirm.json',value)

    def assert_restored(self):
        self.assertEqual(self.b.current,self.before,'original route order is back')
        self.assertNotEqual(self.b.guarded,'full','a finished step never leaves the whole LAN blocked')
        self.assertFalse(native.CERT.exists(),'no certificate from a failed attempt')

    # ---- hangs and timeouts ----
    def test_hung_vendor_apply_is_killed_and_rolled_back(self):
        process=MagicMock(pid=4321,returncode=None)
        process.wait.side_effect=[subprocess.TimeoutExpired('rtp2.sh',50),None]
        self.spawn(process);self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        with self.assertRaises(subprocess.TimeoutExpired):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.killpg.assert_called_with(4321,native.signal.SIGKILL)
        self.assert_restored();self.assertEqual(self.state()['state'],'ROLLED-BACK');self.assertEqual(self.state()['blockers'],['NATIVE-SYSTEM-001'])

    def test_no_client_answer_times_out_and_rolls_back(self):
        process=MagicMock(pid=123,returncode=0);self.spawn(process)
        self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        clock=iter([False]*5+[True]*50)
        self.stack.enter_context(patch.object(native,'transaction_expired',side_effect=lambda *a,**k:next(clock)))
        with self.assertRaisesRegex(native.Refused,'CLIENT-CONFIRMATION-TIMEOUT'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assert_restored();self.assertEqual(self.state()['blockers'],['CLIENT-CONFIRMATION-TIMEOUT'])

    # ---- operator buttons during a switch ----
    def test_stop_pressed_while_waiting_for_the_client_rolls_back(self):
        process=MagicMock(pid=123,returncode=0)
        self.spawn(process,lambda:native.atomic_json(native.PERSIST/'native-stop.json',{'requested':time.time()+1,'trial':'x'}))
        self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        with self.assertRaisesRegex(native.Refused,'CLIENT-STOP'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assert_restored()

    def test_service_stop_signal_rolls_back_instead_of_committing(self):
        process=MagicMock(pid=123,returncode=0);self.spawn(process,self.confirm)
        self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        self.stack.enter_context(patch.object(native,'STOP',True))
        with self.assertRaisesRegex(native.Refused,'CLIENT-CONFIRMATION-TIMEOUT'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assert_restored()

    # ---- wrong or late confirmations ----
    def test_confirmation_that_does_not_match_is_never_accepted(self):
        for over in ({'tx':'f'*32},{'exit_ipv4':'1.2.3.4'},{'dns_ok':False},{'https_ok':False},{'time':time.time()-31},{'time':time.time()+60}):
            with self.subTest(over=over):
                self.setUp()
                process=MagicMock(pid=123,returncode=0);self.spawn(process,lambda:self.confirm(**over))
                self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
                clock=iter([False]*3+[True]*50)
                self.stack.enter_context(patch.object(native,'transaction_expired',side_effect=lambda *a,**k:next(clock)))
                with self.assertRaisesRegex(native.Refused,'CLIENT-CONFIRMATION-TIMEOUT'):native.attempt(self.b,self.b.selection,time.time()+120,False)
                self.assert_restored()

    def test_exit_changing_at_confirmation_rolls_back(self):
        process=MagicMock(pid=123,returncode=0);self.spawn(process,self.confirm)
        self.stack.enter_context(patch.object(native,'trace',side_effect=['9.9.9.9','7.7.7.7']))
        with self.assertRaisesRegex(native.Refused,'EXIT-CHANGED'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assert_restored()

    def test_new_blocker_after_apply_rolls_back(self):
        process=MagicMock(pid=123,returncode=0);self.spawn(process,lambda:setattr(self.b,'blockers',['VENDOR-WORKER-BUSY']))
        self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        with self.assertRaisesRegex(native.Refused,'VENDOR-WORKER-BUSY'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assert_restored()

    def test_reserve_probe_failure_after_apply_rolls_back(self):
        process=MagicMock(pid=123,returncode=0);self.spawn(process)
        self.stack.enter_context(patch.object(native,'trace',side_effect=native.Refused('TARGET-HTTPS-DNS-FAILED')))
        with self.assertRaisesRegex(native.Refused,'TARGET-HTTPS-DNS-FAILED'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assert_restored()

    def test_successful_switch_commits_only_after_matching_confirmation(self):
        process=MagicMock(pid=123,returncode=0);self.spawn(process,self.confirm)
        self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assertNotEqual(self.b.current,self.before);self.assertEqual(self.state()['state'],'COMMITTED')
        self.assertEqual(self.b.guarded,'vpn-only');self.assertEqual(native.journal_read()['phase'],'COMMITTED')

    # ---- rollback itself fails ----
    def test_failing_rollback_keeps_the_transaction_for_supervisor_recovery(self):
        process=MagicMock(pid=123,returncode=1);self.spawn(process)
        self.b.fail_reorder=1
        with self.assertRaisesRegex(native.Refused,'POLICY-IDENTITY-CHANGED'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        # The journal still names the unfinished step, so the restarted supervisor rolls back again.
        self.assertIn(native.journal_read()['phase'],('APPLYING','WAIT-CLIENT'))
        self.assertEqual(self.b.guarded,'full','the timed full block stays until recovery (released by its own 90 s timer)')
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertEqual(self.b.current,self.before);self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
        self.assertEqual(self.b.guarded,'vpn-only')

    def test_unverified_rollback_never_leaves_the_lan_closed(self):
        process=MagicMock(pid=123,returncode=1);self.spawn(process)
        real=self.b.order;calls={'n':0}
        def order():
            calls['n']+=1
            value=real()
            return (list(reversed(value[0])),value[1]) if calls['n']>=2 else value
        self.b.order=order
        with self.assertRaisesRegex(native.Refused,'ROLLBACK-UNVERIFIED'):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assertEqual(self.b.guarded,'vpn-only')

    # ---- supervisor restart (crash, reboot, power loss) ----
    def write_journal(self,phase,order=None):
        value={'tx':TX,'phase':phase,'before':self.before,'after':self.before[:-2]+[self.before[-1],self.before[-2]],
               'hash':self.b.fingerprint,'source':self.b.selection['source']['id'],'target':self.b.selection['target']['id'],
               'deadline':time.time()+60,'monotonic_deadline':None,'trial':False,'pid':None,'started':time.time(),
               'trial_nonce':self.b.data['settings']['native_trial']}
        native.journal_write(value);return value

    def test_restart_in_every_unfinished_phase_restores_the_original_route(self):
        for phase in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):
            with self.subTest(phase=phase):
                self.setUp();journal=self.write_journal(phase)
                self.b.current=journal['after'][:] if phase!='ARMED' else self.before[:]
                with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
                self.assertEqual(self.b.current,self.before);self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
                self.assertNotEqual(self.b.guarded,'full')

    def test_restart_after_commit_with_foreign_change_releases_the_guard(self):
        journal=self.write_journal('COMMITTED');self.b.current=journal['after'][:];self.b.fingerprint='changed-by-someone-else'
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertIsNone(self.b.guarded);self.assertEqual(self.state()['state'],'STOPPED')
        self.assertIs(self.state()['original_restored'],False)

    def test_corrupt_journal_blocks_the_lan_once_then_only_vpn_only(self):
        native.JOURNAL.write_text('{"schema":1,"data":{"phase":"APPLYING"},"sha256":"bad"}')
        for start in (1,2,3):
            self.b.calls.clear()
            with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
            self.assertEqual(self.state()['blockers'],['JOURNAL-INTEGRITY-FAILED']);self.assertEqual(self.state()['alarm'],'JOURNAL-INTEGRITY-FAILED')
            full=[c for c in self.b.calls if c==('guard',None)]
            self.assertEqual(len(full),1 if start==1 else 0,'start %d: full block count'%start)
            self.assertEqual(self.b.guarded,'vpn-only')
        self.assertTrue(native.JOURNAL_ALARM.exists())

    def test_give_up_latch_really_holds_even_with_an_empty_journal(self):
        """After give_up() with an unreadable journal, Auto must stay off for the configured trial, also if uci options could not be cleared."""
        native.JOURNAL.write_text('garbage')
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True),patch.object(native,'clear_native_options',return_value=False):
            native.serve()
        self.assertIn('AUTO-OPTIONS-NOT-CLEARED',self.state()['blockers'])
        stopped=json.loads((native.PERSIST/'native-stop.json').read_text())
        settings={'native_trial':'a'*32,'native_until':str(time.time()+600),'native_enabled':'1'}
        request={'mode':'on','time':time.time()-30,'trial':'a'*32,'until':float(settings['native_until'])}
        self.assertEqual(auto_control.effective_intent(settings,stopped,request,time.time()),(False,True))

    def test_unreadable_alarm_marker_counts_as_already_blocked(self):
        native.JOURNAL.write_text('garbage');native.JOURNAL_ALARM.write_text('not json')
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertNotIn(('guard',None),self.b.calls,'no new full block when the marker cannot be read')
        self.assertEqual(self.state()['alarm'],'JOURNAL-INTEGRITY-FAILED')

    def test_journal_os_error_is_an_integrity_failure(self):
        with patch.object(native,'read_json',side_effect=OSError('EIO')):
            with self.assertRaises(native.Refused) as caught:native.journal_read()
        self.assertEqual(str(caught.exception),'JOURNAL-INTEGRITY-FAILED')

    def test_status_does_not_claim_a_guard_that_failed(self):
        native.JOURNAL.write_text('garbage')
        def broken(devices=None):
            if devices is not None:raise native.Refused('GUARD-INSTALL-FAILED')
            self.b.calls.append(('guard',None))
        self.b.guard=broken
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertNotIn('VPN-only; IPv6',self.state()['guard'])

    def test_alarm_ends_when_the_journal_is_closed_and_the_supervisor_restarts_normally(self):
        native.JOURNAL.write_text('garbage')
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        native.JOURNAL.unlink()
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertFalse(native.JOURNAL_ALARM.exists())

    def test_rollback_that_fails_twice_is_given_up_without_new_full_blocks(self):
        process=MagicMock(pid=123,returncode=1);self.spawn(process);self.b.fail_reorder=99
        with self.assertRaises(native.Refused):native.attempt(self.b,self.b.selection,time.time()+120,False)
        self.assertEqual(native.journal_read()['rollback_failures'],1)
        # second failure: the supervisor's recovery; it gives up at the limit
        self.b.calls.clear()
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertEqual(native.journal_read()['rollback_failures'],2)
        self.assertEqual(self.state()['alarm'],'ROLLBACK-GIVEN-UP');self.assertEqual(self.b.guarded,'vpn-only')
        # third start: no rollback attempt, no full block, Auto stopped
        self.b.calls.clear()
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertNotIn(('reorder',self.before),self.b.calls);self.assertNotIn(('guard',None),self.b.calls)
        self.assertEqual(self.state()['blockers'],['ROLLBACK-GIVEN-UP'])
        self.assertTrue((native.PERSIST/'native-stop.json').exists())

    def test_one_failed_rollback_still_recovers_on_the_next_start(self):
        process=MagicMock(pid=123,returncode=1);self.spawn(process);self.b.fail_reorder=1
        with self.assertRaises(native.Refused):native.attempt(self.b,self.b.selection,time.time()+120,False)
        with patch.object(native,'Linux',return_value=self.b),patch.object(native,'STOP',True):native.serve()
        self.assertEqual(self.b.current,self.before);self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')

    def test_truncated_or_unreadable_journal_is_never_treated_as_empty_success(self):
        for raw in ('{"schema":1','\x00\x00','[]'):
            with self.subTest(raw=raw):
                native.JOURNAL.write_text(raw)
                try:value=native.journal_read()
                except (native.Refused,ValueError):value='refused'
                self.assertNotEqual(value,{'phase':'COMMITTED'})

    # ---- malformed network replies while measuring the exit ----
    def trace_with(self,read=None,status=200,error=None):
        sock=MagicMock();sock.__enter__=lambda s:s;sock.__exit__=lambda *a:False
        ctx=MagicMock();ctx.wrap_socket.return_value=sock
        response=MagicMock(status=status)
        if error:response.read.side_effect=error
        else:response.read.return_value=read
        with patch.object(native,'probe',return_value={'dns_ok':True,'https_success':2,'device':'wg0','mark':1}),\
             patch.object(native,'bound_socket',return_value=MagicMock()),\
             patch.object(native.ssl,'create_default_context',return_value=ctx),\
             patch.object(native.http.client,'HTTPResponse',return_value=response):
            return native.trace({'id':'x'})

    def test_malformed_exit_trace_is_a_coded_refusal(self):
        cases=[('no ip',dict(read=b'fl=1\nh=x\n')),('ipv6 exit',dict(read=b'ip=2001:db8::1\n')),('binary',dict(read=b'ip=\xff\xfe\n')),
               ('private ip',dict(read=b'ip=10.0.0.1\n')),('http 500',dict(read=b'ip=9.9.9.9\n',status=500)),
               ('cut reply',dict(error=http.client.IncompleteRead(b'ip=9'))),('bad status line',dict(error=http.client.BadStatusLine('x')))]
        for name,kwargs in cases:
            with self.subTest(name):
                with self.assertRaises(native.Refused) as caught:self.trace_with(**kwargs)
                self.assertRegex(str(caught.exception),r'^EXIT-')
        self.assertEqual(self.trace_with(read=b'ip=9.9.9.9\n'),'9.9.9.9')


class Buttons(unittest.TestCase):
    """Start / Stop / Return requests from the page, with broken parts underneath."""
    def setUp(self):
        self.dir=Path(tempfile.mkdtemp())

    def test_stop_still_latches_when_router_settings_cannot_be_read(self):
        runtime=self.dir/'run';persist=self.dir/'persist';runtime.mkdir();persist.mkdir()
        until=time.time()+600
        auto_control.atomic_json(runtime/'auto-control.json',{'mode':'on','time':time.time()-5,'trial':'b'*32,'until':until})
        with patch('agent.command',side_effect=subprocess.CalledProcessError(1,'lua')):
            result=auto_control.stop(runtime=runtime,persist=persist)
        stopped=json.loads((persist/'native-stop.json').read_text())
        self.assertTrue(result['queued']);self.assertEqual(stopped['trial'],'b'*32);self.assertTrue(result.get('settings_unverified'))
        # The latch is newer than the start request, so the supervisor treats Auto as stopped.
        self.assertEqual(auto_control.effective_intent({'native_trial':'b'*32,'native_until':repr(until)},stopped,
                         json.loads((runtime/'auto-control.json').read_text()),time.time()),(False,True))

    def test_stop_is_written_once_and_repeated_presses_change_nothing(self):
        runtime=self.dir/'run';persist=self.dir/'persist';runtime.mkdir();persist.mkdir()
        with patch('agent.command',return_value=json.dumps({'settings':{'native_trial':'c'*32}}).encode()):
            first=auto_control.stop(runtime=runtime,persist=persist);stamp=(persist/'native-stop.json').read_text()
            second=auto_control.stop(runtime=runtime,persist=persist)
        self.assertEqual(first,{'queued':True});self.assertTrue(second['already_requested']);self.assertEqual((persist/'native-stop.json').read_text(),stamp)

    def test_stop_button_cleans_a_running_fault_test_even_if_stop_itself_fails(self):
        import agent
        runtime=self.dir/'run';runtime.mkdir();(runtime/'fault-intent.json').write_text('{}')
        cancel=MagicMock(return_value={'cleaned':True})
        out=io.StringIO()
        with patch.object(agent,'RUNTIME',runtime),patch('auto_control.stop',side_effect=OSError('flash')),\
             patch('fault_control.cancel',cancel),patch.object(sys,'stdin',MagicMock(buffer=io.BytesIO(b'{}'))),patch('sys.stdout',out):
            agent.rpc('native_stop')
        cancel.assert_called_once()
        reply=json.loads(out.getvalue())
        self.assertEqual(reply['code'],'STOP-UNCONFIRMED');self.assertFalse(reply['queued']);self.assertTrue(reply['fault_cleanup'])

    def test_start_is_refused_while_any_step_of_a_switch_is_open(self):
        backend=MagicMock();backend.policy.return_value={'settings':{}};backend.diagnostic.return_value=([],None)
        for phase in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING'):
            with self.subTest(phase=phase),patch('native_switch.Linux',return_value=backend),patch('native_switch.journal_read',return_value={'phase':phase}),\
                 patch.object(auto_control,'RUNTIME',self.dir):
                self.assertEqual(auto_control.start(),{'accepted':False,'blockers':['TRANSACTION-IN-PROGRESS']})

    def test_start_with_unreadable_journal_does_not_start(self):
        backend=MagicMock();backend.policy.return_value={'settings':{}};backend.diagnostic.return_value=([],None)
        with patch('native_switch.Linux',return_value=backend),patch('native_switch.journal_read',side_effect=native.Refused('JOURNAL-INTEGRITY-FAILED')),\
             patch.object(auto_control,'RUNTIME',self.dir):
            self.assertEqual(auto_control.start(),{'accepted':False,'blockers':['JOURNAL-INTEGRITY-FAILED']})
        self.assertFalse((self.dir/'auto-control.json').exists())

    def test_return_button_only_acts_on_a_held_or_committed_reserve(self):
        for phase,accepted in (('HELD-ON-RESERVE',True),('COMMITTED',True),('WAIT-CLIENT',False),('ROLLED-BACK',False),(None,False)):
            with self.subTest(phase=phase),patch('native_switch.journal_read',return_value={'phase':phase,'tx':TX} if phase else {}):
                result=auto_control.return_request(runtime=self.dir)
                self.assertEqual(result['accepted'],accepted)


class Settings(unittest.TestCase):
    """Saving settings while the writer hangs, fails or a switch is open."""
    def setUp(self):
        self.dir=Path(tempfile.mkdtemp())
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(auto_control,'RUNTIME',self.dir))
        import setup_config,monitor_control,priority_config
        self.setup,self.monitor,self.priority=setup_config,monitor_control,priority_config

    def monitor_args(self):return {'interval':30,'checkpoint':900,'probe_limit':8,'planning_enabled':True}

    def test_hung_settings_writer_answers_unconfirmed(self):
        self.stack.enter_context(patch.object(self.setup,'inventory',return_value={'settings':{},'profiles':[]}))
        self.stack.enter_context(patch('configuration_guard.blocked',return_value=None))
        with patch.object(self.setup.subprocess,'run',side_effect=subprocess.TimeoutExpired('lua',10)):
            self.assertEqual(self.setup.save(self.monitor_args(),'monitor'),{'saved':False,'code':'SETUP-SAVE-UNCONFIRMED'})
        with patch.object(self.setup.subprocess,'run',side_effect=OSError('no lua')):
            self.assertEqual(self.setup.save(self.monitor_args(),'monitor')['code'],'SETUP-SAVE-UNCONFIRMED')

    def test_writer_refusal_is_reported_with_its_code(self):
        self.stack.enter_context(patch.object(self.setup,'inventory',return_value={'settings':{},'profiles':[]}))
        self.stack.enter_context(patch('configuration_guard.blocked',return_value=None))
        with patch.object(self.setup.subprocess,'run',return_value=MagicMock(returncode=1,stdout=b'SETUP-PENDING-DELTA')):
            result=self.setup.save(self.monitor_args(),'monitor')
        self.assertEqual(result,{'saved':False,'code':'SETUP-PENDING-DELTA'})

    def test_profiles_cannot_change_while_a_switch_is_open(self):
        profiles=[{'id':'a'},{'id':'b'}]
        args={'source':'a','target':'b','interval':30,'duration':60,'session_loss':True,
              'servers':[{'profile':'a','name':'A','channel':'Main','priority':1,'enabled':True},{'profile':'b','name':'B','channel':'Main','priority':2,'enabled':True}]}
        self.stack.enter_context(patch.object(self.setup,'inventory',return_value={'settings':{},'profiles':profiles}))
        writer=self.stack.enter_context(patch.object(self.setup.subprocess,'run'))
        for phase in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING'):
            with self.subTest(phase=phase),patch('native_switch.journal_read',return_value={'phase':phase}),patch('agent.read_json',return_value={}):
                self.assertEqual(self.setup.save(args,'system'),{'saved':False,'code':'SETUP-STOP-FIRST'})
        writer.assert_not_called()

    def test_monitor_switch_with_hung_writer_or_active_auto(self):
        self.stack.enter_context(patch.object(self.monitor,'inventory',return_value={'settings':{}}))
        self.stack.enter_context(patch.object(self.monitor,'read_json',return_value={}))
        self.stack.enter_context(patch.object(self.monitor,'journal_read',return_value={}))
        with patch.object(self.monitor,'assess',return_value=None),patch.object(self.monitor.subprocess,'run',side_effect=subprocess.TimeoutExpired('lua',10)):
            self.assertEqual(self.monitor.change({'enabled':False}),{'accepted':False,'code':'SETUP-SAVE-UNCONFIRMED'})
        with patch.object(self.monitor,'assess',return_value='LIFECYCLE-STOP-AUTO-FIRST'),patch.object(self.monitor.subprocess,'run') as writer:
            self.assertEqual(self.monitor.change({'enabled':False})['code'],'MONITOR-STOP-AUTO-FIRST');writer.assert_not_called()
        with patch.object(self.monitor,'journal_read',side_effect=native.Refused('JOURNAL-INTEGRITY-FAILED')):
            self.assertEqual(self.monitor.change({'enabled':False})['code'],'MONITOR-JOURNAL-UNVERIFIED')


if __name__=='__main__':
    unittest.main()
