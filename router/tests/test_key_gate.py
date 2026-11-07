"""The directional gate of the server keys (independent review of 71053c32, findings 1 and 2; option server_key_pin 'enforce').

SERVER-KEY-UNACCEPTED was a blocker of diagnostic(). With it a Stop on the reserve ended in ROLLBACK-UNVERIFIED with the
journal RESTORING after a 90 s wait (the route was already back), and every decision of a working pair stopped: a changed
key on the primary, the primary dies, a clean reserve stays unused, the VPN-only guard holds the LAN without internet. Now
diagnostic() proves the route and the vendor only; a key refuses a move ONTO its own channel. A Start (owner 05.11.2026) needs a
clean key only on the channel that carries the traffic after it. Lua twin: tests/lua/test_key_gate.lua.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'));sys.path.insert(0,str(HERE))
import agent  # noqa: E402
import auto_control  # noqa: E402
import forward_resume as fr  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
import pair_manual as manual  # noqa: E402
import pair_policy  # noqa: E402
import rollback_recovery  # noqa: E402
import server_pin  # noqa: E402
import test_late_switch as late  # noqa: E402
from vendor_fixture import attach  # noqa: E402

CODE='SERVER-KEY-UNACCEPTED'
PAIR={'source':{'id':'s','interface':'wgclient1'},'target':{'id':'t','interface':'ovpnclient1'},'order':['a','b'],'source_rule':'a','target_rule':'b',
      'direction':'first','generic_rules':['a','b']}


def enforce(case,runtime,*profiles,mode='enforce'):
    """option server_key_pin and a record 'changed' for each profile, as the monitor leaves them."""
    config=Path(runtime)/'homensai_vpn.config'
    config.write_text("config homensai_vpn 'main'\n\toption server_key_pin '%s'\n"%mode,encoding='utf-8')
    patcher=patch.object(server_pin,'CONFIG',str(config));patcher.start();case.addCleanup(patcher.stop)
    records={profile:{'profile':profile,'host':'h.example','protocol':'wireguard','fingerprint':'wg:a','observed':'wg:b','state':'changed',
                      'first_seen':1.0,'last_seen':2.0,'changed_at':2.0,'accepted_at':None} for profile in profiles}
    (Path(runtime)/server_pin.STATE).write_text(json.dumps({'schema':1,'records':records}),encoding='utf-8')


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


class Gate(Base):
    def test_only_the_named_profile_and_only_in_enforce(self):
        enforce(self,self.runtime,'s')
        self.assertEqual(native.key_unaccepted('s'),CODE)
        self.assertEqual(native.key_unaccepted('t','s'),CODE)
        self.assertIsNone(native.key_unaccepted('t'))
        self.assertIsNone(native.key_unaccepted(None),'no id, no gate')
        self.assertIsNone(native.key_unaccepted())
        for mode in ('warn','off'):
            enforce(self,self.runtime,'s',mode=mode);self.assertIsNone(native.key_unaccepted('s'),mode)

    def test_the_default_needs_no_file_at_all(self):
        with patch.object(server_pin,'CONFIG',str(self.runtime/'absent')):self.assertIsNone(native.key_unaccepted('s','t'))

    def test_after_a_reboot_the_flash_copy_counts(self):
        enforce(self,self.runtime,'s')
        (self.runtime/server_pin.STATE).rename(self.persist/server_pin.STATE)
        self.assertEqual(native.key_unaccepted('s'),CODE)

    def test_a_whole_pair_outside_a_session(self):
        enforce(self,self.runtime,'t')
        selection={'source':{'id':'s'},'target':{'id':'t'}}
        self.assertEqual(native.key_blockers([],selection),[CODE])
        self.assertEqual(native.key_blockers([CODE],selection),[CODE],'once')
        self.assertEqual(native.key_blockers(['X'],None),['X'],'no selection, nothing to compare')
        self.assertEqual(native.key_blockers([],{'source':{'id':'a'},'target':{'id':'b'}}),[])


class Carrying(Base):
    """The rule of a Start (owner 05.11.2026): the live order names the channel that must be clean."""
    def live(self,*order):
        backend=MagicMock();backend.order.return_value=(list(order),'h');return backend

    def test_the_source_carries_a_key_on_the_reserve_lets_the_start_go(self):
        enforce(self,self.runtime,'t');self.assertIsNone(native.carrying_unaccepted(self.live('a','b'),PAIR))
        enforce(self,self.runtime,'s');self.assertEqual(native.carrying_unaccepted(self.live('a','b'),PAIR),CODE)

    def test_the_reserve_carries_a_key_on_the_primary_lets_the_start_go(self):
        enforce(self,self.runtime,'s');self.assertIsNone(native.carrying_unaccepted(self.live('b','a'),PAIR))
        enforce(self,self.runtime,'t');self.assertEqual(native.carrying_unaccepted(self.live('b','a'),PAIR),CODE)

    def test_the_direction_of_the_order_counts(self):
        last=dict(PAIR,direction='last')
        enforce(self,self.runtime,'t');self.assertEqual(native.carrying_unaccepted(self.live('a','b'),last),CODE)
        self.assertIsNone(native.carrying_unaccepted(self.live('b','a'),last))

    def test_an_order_that_proves_no_role_counts_both_channels(self):
        refused=MagicMock();refused.order.side_effect=native.Refused('NATIVE-SYSTEM-001')
        broken=MagicMock();broken.order.side_effect=OSError('read')
        for changed in ('s','t'):
            enforce(self,self.runtime,changed)
            for backend,selection in ((refused,PAIR),(broken,PAIR),(self.live('x','y'),PAIR),(self.live('a','b'),{'source':{'id':'s'},'target':{'id':'t'}})):
                self.assertEqual(native.carrying_unaccepted(backend,selection),CODE,changed)

    def test_a_pair_without_keys_and_the_other_modes_pass(self):
        self.assertIsNone(native.carrying_unaccepted(self.live('a','b'),PAIR))
        for mode in ('warn','off'):
            enforce(self,self.runtime,'s',mode=mode);self.assertIsNone(native.carrying_unaccepted(self.live('a','b'),PAIR),mode)


class Rollback(Base):
    """Finding 1: reasons repro r1. The route is back; a key says nothing about it."""
    def context(self):
        before,after=['r1','r2','g'],['r2','r1','g']
        context={'source_rule':'r1','target_rule':'r2','direction':'first','generic_rules':['r1','r2'],'source_id':'s','target_id':'t',
                 'destination_role':'target','before_policy_role':'source','session_order':before,'primary_order':before}
        return before,after,context,{'pair_transition':context,'phase':'COMMITTED','before':before,'after':after,'source':'s','target':'t','hash':'h','tx':'x'}

    def run_rollback(self,reason):
        before,after,context,journal=self.context()
        backend=MagicMock()
        order=[after]
        backend.order.side_effect=lambda:(order[0],'h')
        backend.reorder.side_effect=lambda value,**k:order.__setitem__(0,value)
        backend.attest_policy.return_value={'verified':True,'role':'target','kernel_fingerprint':'f'*64,'order':after}
        backend.kernel_fingerprint.return_value='f'*64
        backend.devices.return_value=['wgclient1']
        backend.diagnostic.return_value=([],{'order':before})
        clock=[0.0]
        real=rollback_recovery.settled
        def settled(b,tolerated=None,**k):
            return real(b,clock=lambda:clock[0],sleep=lambda s:clock.__setitem__(0,clock[0]+s),tolerated=tolerated)
        def proof(selection=None):
            return {'verified':True,'role':'source' if order[0]==before else 'target','kernel_fingerprint':'f'*64,'order':order[0]}
        backend.attest_policy.side_effect=proof
        writes=[]
        with patch.object(rollback_recovery,'settled',side_effect=settled),patch.object(rollback_recovery,'vendor_settled'),\
             patch.object(rollback_recovery,'vendor_rebuild_applies',return_value=False),patch.object(pair_policy,'metadata',return_value=context),\
             patch.object(pair_policy,'validate',side_effect=lambda v,o:v),patch.object(native,'journal_write',side_effect=lambda j:writes.append(j.get('phase'))),\
             patch.object(native,'publish'),patch.object(native,'bind_policy_context'),patch.object(native,'note_phase'),\
             patch.object(native,'reset_old_flows'),patch('switch_timing.record'):
            native.rollback(backend,journal,reason,restore_order=before)
        return journal,clock[0],writes

    def test_stop_on_the_reserve_with_an_unaccepted_key_ends_rolled_back_at_once(self):
        for profiles in (('t',),('s',),('s','t')):
            with self.subTest(profiles=profiles):
                enforce(self,self.runtime,*profiles)
                journal,waited,writes=self.run_rollback('PAIR-STOPPED')
                self.assertEqual(journal['phase'],'ROLLED-BACK');self.assertEqual(waited,0,'no settling wait with the LAN blocked')
                self.assertEqual(writes,['RESTORING','ROLLED-BACK'])

    def test_a_stop_is_no_move_the_gate_refuses(self):
        # the end of a Stop that waited on the reserve goes through operator_return with its own reason
        enforce(self,self.runtime,'s')
        journal={'phase':'HELD-ON-RESERVE','source':'s','target':'t'}
        backend=MagicMock();backend.health.return_value=True
        with patch.object(native,'rollback') as rollback,patch('pair_policy.metadata',return_value=None):
            self.assertIsNone(native.operator_return(backend,journal,'PRIMARY-RECOVERED'))
            rollback.assert_called_once()
            self.assertEqual(native.operator_return(backend,journal),CODE,'the owner asking to move onto it is refused')
            rollback.assert_called_once()
            self.assertEqual(native.operator_return(backend,{'phase':'ROLLED-BACK','source':'s'}),'RETURN-NOT-APPLICABLE')


class Doors(Base):
    """Every forward door refuses before the first write and before a charge."""
    def selection(self):
        return {'source':{'id':'s'},'target':{'id':'t'},'order':['a','b'],'source_rule':'a','target_rule':'b','direction':'first','proof_scope':'router-probed-ipv4'}

    def test_attempt_refuses_a_move_onto_the_channel_and_touches_nothing(self):
        enforce(self,self.runtime,'t')
        backend=MagicMock();charged=[]
        with self.assertRaisesRegex(native.Refused,CODE):
            native.attempt(backend,self.selection(),time.time()+180,False,control_revision=self.revision,pair_session_order=['a','b'],on_dispatch=lambda:charged.append(1))
        self.assertEqual(backend.method_calls,[]);self.assertEqual(charged,[])

    def test_attempt_lets_a_move_away_from_it_and_a_repair_of_the_carrying_channel_through(self):
        enforce(self,self.runtime,'s')
        class Passed(Exception):pass
        def assert_selection(backend,selection):raise Passed
        with patch.object(native,'assert_selection',side_effect=assert_selection),patch.object(native,'bind_policy_context'):
            with self.assertRaises(Passed):native.attempt(MagicMock(),self.selection(),0,False,control_revision=self.revision)
            enforce(self,self.runtime,'s','t')
            with self.assertRaises(Passed):
                native.attempt(MagicMock(),self.selection(),0,False,control_revision=self.revision,pair_destination='source',pair_session_order=['a','b'],pair_reapply=True)
            with self.assertRaisesRegex(native.Refused,CODE):
                native.attempt(MagicMock(),self.selection(),0,False,control_revision=self.revision,pair_destination='source',pair_session_order=['a','b'],pair_return=True)

    def test_instant_manual_refuses_before_its_lease_is_used(self):
        enforce(self,self.runtime,'s')
        backend=MagicMock()
        with self.assertRaisesRegex(native.Refused,CODE):
            native.instant_manual(backend,self.selection(),0,self.revision,'a'*32,'manual','source',['a','b'])
        self.assertEqual(backend.method_calls,[])

    def test_the_committed_return_goes_to_a_clean_primary_only(self):
        source,target='openvpn:a','wireguard:b'
        rows=[{'id':target,'time':stamp,'code':'DNS-001'} for stamp in (940,970,990)]
        status=attach({'profiles':[{'id':source,'interface':'vpn1','protocol':'openvpn'},{'id':target,'interface':'vpn2','protocol':'wireguard','code':'DNS-001'}],'samples':rows})
        status['time']=1000;status['vendor_observation']['time']=1000
        for row in status['profiles']:row['time']=1000
        for group in status['vendor_observation']['groups']:group['time']=1000
        backend=MagicMock();backend.recovery_ready.return_value=True;backend.health.return_value=False
        journal={'source':source,'target':target,'confirmed':990}
        settings={'failure_model':'consecutive'}
        enforce(self,self.runtime,target)   # the reverse of finding 2: on the reserve with a changed key, the reserve dies, a clean primary
        self.assertEqual(native.committed_recovery_decision(backend,journal,settings,rows,1000,status),
                         {'action':'RESTORE-PRIMARY','reason':'RESERVE-FAILED-PRIMARY-VERIFIED'})
        enforce(self,self.runtime,source)   # the key of the primary: no return, the reason says why
        self.assertEqual(native.committed_recovery_decision(backend,journal,settings,rows,1000,status)['reason'],CODE)
        backend.health.return_value=True
        planned=dict(journal,confirmed=900)
        decided=native.committed_recovery_decision(backend,planned,settings,[],1000,status)
        self.assertEqual(decided['action'],'OBSERVE');self.assertEqual(decided['reason'],CODE,'a planned return that was due')
        backend.recovery_ready.return_value=False
        decided=native.committed_recovery_decision(backend,planned,settings,[],1000,status)
        self.assertEqual(decided['reason'],'CLIENT-CONFIRMED','nothing was due: nothing to explain')


class Session(Base):
    """reapply_missing_policy: the pass of a working pair goes on; a Start waits."""
    def reapply(self,state,journal=None,order=('a','b')):
        backend=MagicMock()
        selection=dict(PAIR,order=list(order))
        backend.diagnostic.return_value=([],selection)
        backend.order.return_value=(list(order),'h')
        backend.attest_policy.return_value={'verified':True,'role':'source','order':['a','b'],'policy_hash':'h','time':5.0}
        roles=pair_policy.proof(selection)
        full=dict({'id':'a'*32,'phase':'RUNNING','policy_roles':roles,'order':['a','b'],'policy_hash':'h'},**state)
        with patch.object(pair,'intent',return_value={'mode':'on','revision':'r','id':'a'*32}),\
             patch('pair_policy.state_order_matches',return_value=True),patch.object(pair,'remember_selected',return_value=True) as remembered,\
             patch.object(native,'publish') as publish:
            return pair.reapply_missing_policy(backend,full,{},'r',journal or {}),publish,remembered

    def test_a_working_pair_goes_on_with_either_key_unaccepted(self):
        for changed in ('s','t'):
            enforce(self,self.runtime,changed)
            ended,publish,_=self.reapply({'selected_policy':{'role':'source','order':['a','b'],'hash':'h','since':1.0}})
            self.assertIs(ended,False,changed);publish.assert_not_called()

    def test_a_start_waits_for_a_key_on_the_carrying_channel(self):
        # the open item of the second review: a key seen while the Start ran. On the carrying channel it waits for the owner...
        for changed,order in (('s',('a','b')),('t',('b','a'))):
            enforce(self,self.runtime,changed)
            ended,publish,remembered=self.reapply({},order=order)
            self.assertIs(ended,True,changed);remembered.assert_not_called()
            row=publish.call_args[0][0];self.assertEqual((row['state'],row['blockers']),('BLOCKED',[CODE]))
        enforce(self,self.runtime)
        ended,publish,remembered=self.reapply({});self.assertIs(ended,False);remembered.assert_called_once()

    def test_a_key_on_the_other_channel_leaves_no_blocked_session(self):
        # ...on the other channel it changes nothing: the first proof goes on, no BLOCKED with the guard up and no decisions
        enforce(self,self.runtime,'t')
        ended,publish,remembered=self.reapply({})
        self.assertIs(ended,False);publish.assert_not_called();remembered.assert_called_once()


class Start(Base):
    """Review 05.11.2026: a Start with an unaccepted key used to begin the session, raise both clients and set the VPN-only
    guard, then stand BLOCKED with no decisions. Owner 05.11.2026: only the channel that carries the traffic afterwards counts.
    Through the real request, tick and begin; Lua: test_key_gate.lua."""
    class Reached(Exception):
        pass

    def tick(self,network,revision,order=('a','b')):
        backend=MagicMock();backend.order.return_value=(list(order),'h')
        selection=dict(PAIR,order=list(order))
        with patch.object(pair,'preflight',return_value=selection),patch.object(pair,'network',side_effect=network) as read,patch.object(native,'publish') as publish,\
             patch.object(pair,'_outside_hold_safe'):
            result=pair.tick(backend,{'pair_auto_mode':pair.MODE},revision)
        return result,backend,read,publish

    def test_a_start_with_a_key_on_the_carrying_channel_takes_nothing_and_ends_with_its_code(self):
        for changed,order in (('s',('a','b')),('t',('b','a'))):
            with self.subTest(changed=changed):
                enforce(self,self.runtime,changed)
                revision=auto_control.current_revision()
                self.assertTrue(pair.request(revision,request_source='manual')['accepted'],'the click is queued as any other')
                request=pair.intent()
                ended,backend,network,publish=self.tick(None,revision,order)
                self.assertIs(ended,True)
                self.assertEqual([call[0] for call in backend.method_calls],['order'],'no guard, nothing but the read of the order');network.assert_not_called()
                self.assertEqual(pair.read_state(),{},'no session')
                row=pair.intent()
                self.assertEqual((row['mode'],row['failed_request_id'],row['failure_code']),('off',request['id'],CODE))
                self.assertEqual(pair.public_phase(),'FAILED')
                value=publish.call_args[0][0];self.assertEqual((value['state'],value['blockers']),('BLOCKED',[CODE]))
                ended,backend,network,publish=self.tick(None,revision)
                self.assertEqual(backend.method_calls,[],'the next pass begins nothing either')

    def test_a_key_on_the_channel_not_carrying_lets_the_start_go(self):
        for changed,order in (('t',('a','b')),('s',('b','a'))):
            with self.subTest(changed=changed):
                enforce(self,self.runtime,changed)
                revision=auto_control.current_revision()
                pair.request(revision,request_source='manual')
                with self.assertRaises(self.Reached):self.tick(self.Reached,revision,order)
                auto_control.stop(request_source='manual')

    def test_after_the_owner_s_word_a_new_start_goes_on(self):
        enforce(self,self.runtime,'s')
        revision=auto_control.current_revision()
        pair.request(revision,request_source='manual');self.tick(None,revision)
        enforce(self,self.runtime,'other')
        pair.request(revision,request_source='manual')
        with self.assertRaises(self.Reached):self.tick(self.Reached,revision)


class LegacyStart(Base):
    """auto_control.start outside pair mode: the Start only arms the watch; a trial moves at once and counts both channels."""
    def run_start(self,order,trial=None):
        backend=MagicMock();backend.policy.return_value={'settings':{}};backend.order.return_value=(list(order),'h')
        backend.diagnostic.return_value=([],dict(PAIR,order=list(order)))
        seen=[]
        def gate(*args):seen.append(list(args[-2] if trial is None else args[-3]));return ['HERE']
        with patch.object(native,'Linux',return_value=backend),patch.object(native,'journal_read',return_value={}),\
             patch.object(auto_control,'readiness',side_effect=gate),patch.object(auto_control,'trial_readiness',side_effect=gate),\
             patch('preparation_control.auto_blocker',return_value=None),patch('preparation_control.auto_prepare',return_value={}):
            reply=auto_control.start(auto_control.current_revision(),trial_nonce=trial,request_source='manual')
        self.assertEqual(reply,{'accepted':False,'blockers':['HERE']})
        return seen[0]

    def test_the_button_asks_for_the_carrying_channel(self):
        enforce(self,self.runtime,'t')
        self.assertEqual(self.run_start(('a','b')),[],'a key on the reserve does not stop a Start on the primary')
        self.assertEqual(self.run_start(('b','a')),[CODE],'the reserve carries')
        enforce(self,self.runtime,'s')
        self.assertEqual(self.run_start(('a','b')),[CODE])
        self.assertEqual(self.run_start(('b','a')),[])

    def test_a_trial_counts_both(self):
        for changed in ('s','t'):
            enforce(self,self.runtime,changed)
            self.assertEqual(self.run_start(('a','b'),trial='n'*32),[CODE],changed)


class Failover(late.Simulation):
    """Finding 2 through pair_auto.tick on the measured timing: the real gates and decision, a fake transaction."""
    def setUp(self):
        super().setUp()
        self.config=self.runtime/'homensai_vpn.config'

    def run_keyed(self,*profiles,**kw):
        enforce(self,self.runtime,*profiles)
        return self.run_fault(lambda o:not (0<=o<60),model='hmm',**kw)

    def test_a_changed_key_on_the_primary_does_not_keep_the_pair_on_it(self):
        sim=self.run_keyed(late.PROFILE['id'])
        self.assertTrue(sim['switches'],'the clean reserve takes over: finding 2')
        ledger=agent.read_json(self.persist/'pair-auto-budget.json')
        self.assertEqual(len(ledger['events']),1);self.assertNotIn('others',ledger,'finding 5: the failover of a tick counts as one')

    def test_a_changed_key_on_the_reserve_keeps_the_pair_off_it(self):
        sim=self.run_keyed(late.RESERVE['id'])
        self.assertFalse(sim['switches'])
        self.assertEqual(sim['leases'],0,'nothing was prepared')
        refused=[v for _,v in sim['published'] if v.get('reason')==CODE]
        self.assertTrue(refused,'published with its code')
        self.assertEqual((refused[0]['state'],refused[0]['blockers']),('BLOCKED',[CODE]))

    def test_a_refused_failover_keeps_the_owner_hold(self):
        self.assertEqual(self.run_keyed(late.RESERVE['id'],hold='source')['hold'],'source')

    def test_healthy_channels_with_a_changed_key_just_keep_watching(self):
        enforce(self,self.runtime,late.PROFILE['id'],late.RESERVE['id'])
        sim=self.run_fault(lambda o:True,model='hmm')
        self.assertFalse(sim['switches'])
        self.assertTrue(all(v['state']=='OBSERVING' for _,v in sim['published']),'no BLOCKED in a working pair')


class Buttons(Base):
    def setUp(self):
        super().setUp()
        self.native_state=patch.object(native,'STATE',self.runtime/'native-status.json');self.native_state.start();self.addCleanup(self.native_state.stop)
        agent.atomic_json(native.STATE,{'state':'OBSERVING','time':time.time(),'source':'s','target':'t'})
        agent.atomic_json(self.runtime/'status.json',{'profiles':[{'id':key,'time':time.time(),'code':None,'dns_ok':True,'https_success':3} for key in ('s','t')]})

    def test_light_gate_refuses_towards_the_channel_only(self):
        enforce(self,self.runtime,'t')
        with patch.object(native,'journal_read',return_value={}):
            self.assertEqual(manual.light_gate('reserve',{}),CODE)
            self.assertIsNone(manual.light_gate('primary',{}))


class ServerChange(Base):
    def test_a_hand_over_waits_for_the_owner(self):
        import server_pick as S
        enforce(self,self.runtime,'t')
        state={'phase':'RUNNING','policy_roles':{'source_id':'s','target_id':'t'},'order':['a','b'],'policy_hash':'h','id':'a'*32}
        backend=MagicMock()
        backend.attest_policy.return_value={'verified':True,'role':'source'}
        backend.order.return_value=(state['order'],state['policy_hash'])  # nothing else stands in the way of the change
        tunnel={'tunnel_id':'x','interface':'wgclient2','protocol':'wireguard'}
        row={'time':1000.0,'from':'a','to':'b'}
        gates=[]
        def gate(value):gates.append(value);return None
        with patch.object(S,'claim',return_value={'tunnel':tunnel,'target':{'group_id':'g','profile_id':'p'},'previous':{}}),\
             patch.object(S,'gate',side_effect=gate),patch.object(S,'role_of',return_value='target'),\
             patch.object(S,'changes_left',return_value=(1,None)),patch.object(S,'vendor_busy',return_value=False),\
             patch.object(S,'project_change') as project,patch.object(pair,'server_interfaces',return_value=('wgclient1','wgclient2',{'wgclient2'})),\
             patch.object(pair,'SERVER_IO',{'runtime':str(self.runtime),'read':lambda path:json.dumps(row) if path.endswith(S.CHANGE) else None}):
            self.assertIs(pair.server_start(backend,state,{'server_pick':'1'},'r',{}),False)
            self.assertTrue(gates,'the gate was reached');project.assert_not_called()


class Model(unittest.TestCase):
    """tools/formal/model.py --key-pin: what the blocker broke and what the directional gate keeps (the CI profile 'keys' is larger)."""
    def run_model(self,variant):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'result.json'
            subprocess.run([sys.executable,str(HERE.parents[1]/'tools/formal/model.py'),'--variant','fix2','--no-gl','--no-crash','--no-power','--no-expire',
                            '--key-pin',variant,'--json',str(out),'--out',os.devnull],check=True,stdout=subprocess.DEVNULL,timeout=280)
            return json.loads(out.read_text(encoding='utf-8'))[0]

    def test_the_model_names_the_carrying_channel_as_the_code_does(self):
        spec=importlib.util.spec_from_file_location('formal_model',HERE.parents[1]/'tools/formal/model.py');model=importlib.util.module_from_spec(spec)
        sys.modules['formal_model']=model;self.addCleanup(sys.modules.pop,'formal_model');spec.loader.exec_module(model)
        for uci,primary,reserve,carrying in (('P',True,False,True),('P',False,True,False),('R',True,False,False),('R',False,True,True),('F',True,False,True)):
            self.assertIs(model.key_on_carrying(SimpleNamespace(uci=uci,kp=primary,kr=reserve)),carrying,(uci,primary,reserve))

    def test_the_directional_gate_keeps_every_liveness_check(self):
        result=self.run_model('directional')
        self.assertEqual(result['ef_stuck'],0)
        self.assertGreater(result['liveness_failover']['start_states'],0)
        self.assertEqual((result['liveness_failover']['bad'],result['liveness_return']['bad'],result['liveness_stop_primary_up']['not_clean']),(0,0,0))
        self.assertNotIn('MOVE-ONTO-UNACCEPTED-KEY',result['transition'])
        self.assertNotIn('BEGIN-WITH-UNACCEPTED-KEY',result['transition'],'review 05.11.2026')
        self.assertGreater(result['begin_other_key'],0,'owner 05.11.2026: a Start with a key only on the other channel goes on')

    def test_the_blocker_before_the_fix_breaks_them(self):
        result=self.run_model('blocker')
        self.assertGreater(result['liveness_failover']['bad'],0,'finding 2')
        self.assertGreater(result['liveness_return']['bad'],0,'finding 2, the reverse')
        self.assertGreater(result['liveness_stop_primary_up']['not_clean'],0,'finding 1')
        self.assertGreater(result['transition']['BEGIN-WITH-UNACCEPTED-KEY'],0,'review 05.11.2026: the session began anyway')


@unittest.skipUnless(shutil.which('lua5.1'),'Lua 5.1 runtime absent')
class LuaTwin(unittest.TestCase):
    def test_lua_suite(self):
        done=subprocess.run(['lua5.1','lua/test_key_gate.lua'],cwd=HERE,capture_output=True,text=True,timeout=120)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)


if __name__=='__main__':
    unittest.main()
