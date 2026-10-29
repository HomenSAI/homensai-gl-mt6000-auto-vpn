"""Our own vendor RTP died mid-rebuild: finish it narrowly or refuse.

Models the live MT3000 incident (alpha57, 28 Oct 2026): the apply worker
group was SIGKILLed at stage rtp-dispatch; rtp2.sh had flushed its mangle
route chains and deleted every gl_vpn_rules firewall section, recreated some
of them, left /tmp/run/rtp2.lock behind and never rebuilt the TUNNEL chains.
Actual Linux order/hash, Lua parser and production recovery code run; the
UCI delta, vendor compiler and firewall file are fixture adapters.
"""
import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair
import pair_manual as manual
import rollback_recovery as recovery
import test_pair_manual_bound_context as platform
import test_rollback_order_steps as order_fixture  # not imported by name: its tests stay in their module

ORIGINAL=(b"config defaults\n\toption input 'ACCEPT'\n\n"
          b"config zone\n\toption name 'lan'\n\toption network 'lan'\n\n"
          b"config redirect\n\toption name 'keep'\n\toption src 'wan'\n\n"
          b"config zone 'wgclient1'\n\toption name 'wgclient1'\n\toption gl_vpn_rules '1'\n\n"
          b"config forwarding 'lan2wgclient1'\n\toption src 'lan'\n\toption dest 'wgclient1'\n\toption gl_vpn_rules '1'\n\n"
          b"config forwarding 'lan2ovpnclient2'\n\toption src 'lan'\n\toption dest 'ovpnclient2'\n\toption gl_vpn_rules '1'\n\n"
          b"config forwarding 'guest2ovpnclient2'\n\toption src 'guest'\n\toption dest 'ovpnclient2'\n\toption gl_vpn_rules '1'\n")
PARTIAL=ORIGINAL.split(b"\nconfig forwarding 'guest2ovpnclient2'")[0]+b'\n'


@unittest.skipUnless(platform.LUA,'Actual Lua 5.1 runtime required')
class VendorRebuildRecovery(unittest.TestCase):
    def setUp(self):
        self.steps=order_fixture.RestoreOrderSteps('test_restart_resumes_only_remaining_move_after_first_move_crash')
        self.steps.setUp();self.addCleanup(self.steps.doCleanups)
        case=self.case=self.steps.case;self.backend=self.steps.backend
        self.fw=ORIGINAL;self.wireguard='c'*64;self.partial=False;self.extra_changes=b''
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.lock=Path(temporary.name)/'rtp2.lock'
        case.enter(patch.object(recovery,'VENDOR_LOCK',str(self.lock)))
        case.enter(patch.object(recovery,'SETTLE_SECONDS',0))  # settle waits are tested explicitly
        case.enter(patch.object(pair,'firewall_bytes',side_effect=lambda:self.fw))
        case.enter(patch.object(pair,'configs',side_effect=lambda interfaces=None:
            {'firewall':pair.config_digest('firewall',self.fw),'wireguard':self.wireguard}))
        state=pair.read_state()
        state['protected']={'firewall':pair.config_digest('firewall',ORIGINAL),'wireguard':'c'*64}
        pair.save(state)
        base=n.command
        def command(args,timeout=5):
            if args==['uci','-q','changes']:
                own=b"route_policy.cfg000002='rule'\n" if case.data.get('pending') else b''
                return own+self.extra_changes
            if args[0]=='iptables-save' and self.partial:
                return ''.join(line+'\n' for line in case.kernel_text().splitlines() if 'TUNNEL' not in line).encode()
            return base(args,timeout)
        case.enter(patch.object(n,'command',side_effect=command))

    def static(self):
        state=pair.read_state();state['protected_static']={'firewall':pair.static_firewall_digest(ORIGINAL)};pair.save(state)

    def interrupted(self):
        """Real manual request; the vendor stand-in dies after flushing and half the firewall rewrite."""
        writer=self.case.write;died=[False]
        def vendor(args):
            if args[0]=='/usr/bin/rtp2.sh' and not died[0]:
                died[0]=True;self.partial=True;self.fw=PARTIAL
                self.lock.write_text('999999\n')  # its EXIT trap never ran; no such pid
                raise n.Refused('NATIVE-SYSTEM-001')
            if args[0]=='/usr/bin/rtp2.sh':
                self.assertFalse(self.lock.exists(),'a proven-stale lock is removed before the rebuild')
                self.partial=False;self.fw=ORIGINAL  # a complete rebuild regenerates the vendor sections
            return writer(args)
        agent.atomic_json(self.case.persist/'pair-auto-budget.json',{'events':[]})
        self.assertTrue(manual.request('reserve',self.case.revision)['accepted'])
        self.case.enter(patch.object(self.case,'write',side_effect=vendor))
        manual.consume(self.backend,pair.read_state(),self.case.data['settings'],self.case.revision)
        saved=n.journal_read()
        self.assertTrue(died[0]);self.assertEqual(saved['phase'],'APPLYING');self.assertTrue(saved['rtp_dispatched'])
        self.assertEqual(saved['failure_detail']['worker_stage'],'rtp-dispatch')
        self.assertNotEqual(self.backend.kernel_fingerprint(),saved['kernel_before_fingerprint'])
        self.assertFalse(self.backend.attest_policy()['verified'])
        self.assertEqual(self.backend.order()[0],saved['after'])
        self.revision=auto_control.current_revision(rotate=True);pair.stop_locked(self.revision)
        self.case.commands.clear();self.ledger=agent.read_json(self.case.persist/'pair-auto-budget.json')
        return saved

    def snapshot(self):
        return (n.JOURNAL.read_bytes(),self.backend.order(),n.command(['iptables-save','-t','mangle']),self.fw,self.lock.exists())

    def refused_without_writes(self):
        before=self.snapshot()
        with self.assertRaises(n.Refused):n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.case.commands,[]);self.assertEqual(self.snapshot(),before)
        self.assertEqual(agent.read_json(self.case.persist/'pair-auto-budget.json'),self.ledger)

    def assert_recovered(self,original):
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertEqual(n.journal_read()['restore_proof_source'],'vendor-rebuild')
        self.assertEqual(n.journal_read()['restored_order'],original['before'])
        self.assertEqual(self.backend.order()[0],original['before'])
        proof=self.backend.attest_policy();self.assertTrue(proof['verified']);self.assertEqual(proof['role'],'source')
        self.assertEqual(self.backend.kernel_fingerprint(),original['kernel_before_fingerprint'])
        self.assertEqual(self.fw,ORIGINAL);self.assertFalse(self.lock.exists())
        self.assertEqual(pair.intent()['mode'],'off')
        self.assertEqual(agent.read_json(self.case.persist/'pair-auto-budget.json'),self.ledger)

    def test_live_incident_legacy_session_rebuilds_and_requires_exact_protected_config(self):
        original=self.interrupted()
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assert_recovered(original)
        commands=self.case.commands
        self.assertEqual(sum(args[:2]==['uci','reorder'] for args in commands),2)
        self.assertEqual(sum(args[:3]==['uci','commit','route_policy'] for args in commands),1)
        self.assertEqual(sum(args[0]=='/usr/bin/rtp2.sh' for args in commands),1)
        self.assertTrue(pair.recover(self.backend));self.assertEqual(pair.read_state()['phase'],'STOPPED')
        self.assertEqual(pair.intent()['mode'],'off')

    def test_session_with_static_digest_rebuilds_vendor_only_drift(self):
        self.static();original=self.interrupted()
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assert_recovered(original)

    def test_crash_after_first_reverse_move_resumes_the_recorded_rebuild(self):
        original=self.interrupted();writer=self.case.write;moves=[]
        def killed(args):
            result=writer(args)
            if args[:2]==['uci','reorder']:
                moves.append(args)
                if len(moves)==1:raise RuntimeError('worker killed')
            return result
        with patch.object(self.case,'write',side_effect=killed),self.assertRaises(RuntimeError):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        saved=n.journal_read()
        self.assertEqual(saved['phase'],'RESTORING');self.assertEqual(saved['restore_proof_source'],'vendor-rebuild')
        self.assertEqual(saved['restore_order_origin'],original['after'])
        self.revision=auto_control.current_revision(rotate=True);pair.stop_locked(self.revision);self.case.commands.clear()
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assert_recovered(original)
        self.assertEqual(sum(args[:2]==['uci','reorder'] for args in self.case.commands),1)

    def test_resume_before_own_rtp_refuses_a_routed_graph_that_appeared_meanwhile(self):
        self.interrupted();writer=self.case.write
        def killed(args):
            result=writer(args)
            if args[:2]==['uci','reorder']:raise RuntimeError('worker killed')
            return result
        with patch.object(self.case,'write',side_effect=killed),self.assertRaises(RuntimeError):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertNotIn('restore_rtp_dispatched',n.journal_read())
        self.revision=auto_control.current_revision(rotate=True);pair.stop_locked(self.revision);self.case.commands.clear()
        self.partial=False  # someone else installed a complete, routed graph
        self.refused_without_writes()

    def test_foreign_firewall_section_zone_or_redirect_refuses_before_any_write(self):
        self.static();self.interrupted();partial=self.fw
        for name,edited in (('rule',partial+b"\nconfig rule\n\toption name 'foreign'\n"),
                            ('zone',partial.replace(b"option network 'lan'",b"option network 'lan wan'")),
                            ('redirect',partial.replace(b"option name 'keep'",b"option name 'open'"))):
            self.fw=edited
            with self.subTest(change=name):self.refused_without_writes()
        self.fw=partial

    def test_monitor_restart_renews_generation_but_not_the_tunnel_identity(self):
        # Upgrade/reboot restarts the monitor: every vendor_generation is new.
        original=self.interrupted()
        for profile in self.case.profiles:profile['vendor_generation']=os.urandom(16).hex()
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assert_recovered(original)

    def test_renewed_generation_with_changed_tunnel_identity_refuses_before_any_write(self):
        self.interrupted();profiles=copy.deepcopy(self.case.profiles)
        for field,value in (('interface','wgclient9'),('vendor_tunnel_id','wireguard:wgclient9')):
            self.case.profiles=copy.deepcopy(profiles)
            for profile in self.case.profiles:profile['vendor_generation']='e'*32
            self.case.profiles[0][field]=value
            with self.subTest(field=field):self.refused_without_writes()

    def unsettled(self,calls):
        """The monitor was just restarted: the first diagnostics are not ready yet."""
        real=self.backend.diagnostic;count=[0]
        def diagnostic():
            count[0]+=1
            return (['VENDOR-SETTLING'],None) if count[0]<=calls else real()
        self.case.enter(patch.object(self.backend,'diagnostic',side_effect=diagnostic))
        now=[0.0];settled=recovery.settled
        self.case.enter(patch.object(recovery,'settled',side_effect=lambda backend:settled(backend,clock=lambda:now[0],
            sleep=lambda seconds:now.__setitem__(0,now[0]+seconds))))
        self.case.enter(patch.object(recovery,'SETTLE_SECONDS',90))
        return count

    def test_supervisor_restart_waits_for_the_monitor_to_settle_before_any_write(self):
        original=self.interrupted();count=self.unsettled(5)
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertGreater(count[0],5);self.assert_recovered(original)

    def test_a_pair_that_never_settles_refuses_before_any_write(self):
        self.interrupted();count=self.unsettled(10**6)
        self.refused_without_writes()
        self.assertLessEqual(count[0],32)  # bounded: 90 s at a 3 s poll

    def test_credential_change_refuses_before_any_write(self):
        self.interrupted();self.wireguard='d'*64;self.refused_without_writes()

    def test_live_vendor_lock_refuses_before_any_write(self):
        self.interrupted()
        worker=subprocess.Popen(['sh','-c','sleep 30','rtp2.sh'])
        try:
            self.lock.write_text(str(worker.pid)+'\n');self.refused_without_writes()
        finally:worker.kill();worker.wait()

    def test_malformed_lock_refuses(self):
        self.interrupted()
        for content in ('','not-a-pid','0','1'*40):
            self.lock.write_text(content)
            with self.subTest(content=content):self.refused_without_writes()

    def test_pending_foreign_uci_change_refuses_before_any_write(self):
        self.interrupted();self.extra_changes=b"firewall.cfg01=redirect\n";self.refused_without_writes()

    def test_wrong_revision_owner_or_on_intent_refuses(self):
        self.interrupted();state=pair.read_state();intent=pair.intent()
        for mode in ('state-revision','pair-id','on-intent','stale-marker'):
            pair.save(state);agent.atomic_json(pair.paths()[0],intent)
            agent.atomic_json(self.case.runtime/'auto-control-revision.json',{'revision':self.revision})
            if mode=='state-revision':pair.save(dict(state,revision='f'*32))
            elif mode=='pair-id':pair.save(dict(state,id='f'*32))
            elif mode=='on-intent':agent.atomic_json(pair.paths()[0],dict(intent,mode='on'))
            else:agent.atomic_json(self.case.runtime/'auto-control-revision.json',{'revision':'e'*32})
            with self.subTest(mode=mode):self.refused_without_writes()

    def test_order_neither_before_nor_after_refuses(self):
        original=self.interrupted();rows={n.section_id(row,self.case.bindings):row for row in self.case.data['sections']}
        step=next(recovery.order_steps(original['after'],original['before']))
        self.case.data['sections']=[rows[key] for key in step['after']]
        self.refused_without_writes()

    def test_routed_foreign_graph_is_never_rebuilt(self):
        self.interrupted();self.partial=False
        self.case.mangle=self.case.mangle.replace('--set-xmark 0x1000/0xf000','--set-xmark 0x3000/0xf000')
        self.refused_without_writes()

    def test_tampered_or_unproven_worker_stage_never_selects_the_rebuild(self):
        original=self.interrupted()
        for detail in ({},dict(original['failure_detail'],worker_stage='rtp-returned'),None):
            row=copy.deepcopy(original)
            if detail is None:row.pop('failure_detail')
            else:row['failure_detail']=detail
            n.journal_write(row)
            with self.subTest(detail=detail):self.refused_without_writes()
            self.assertNotIn('restore_proof_source',n.journal_read())

    def test_post_rebuild_firewall_mismatch_never_closes_the_journal(self):
        self.interrupted()
        writer=self.case.write
        def regenerate_foreign(args):
            result=writer(args)
            if args[0]=='/usr/bin/rtp2.sh':self.fw=ORIGINAL+b"\nconfig rule\n\toption name 'foreign'\n"
            return result
        with patch.object(self.case,'write',side_effect=regenerate_foreign),self.assertRaisesRegex(n.Refused,'PAIR-EXTERNAL-CONFIG-CHANGE'):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        commands=self.case.commands
        self.assertEqual([args[0] if args[0]!='uci' else ' '.join(args[:2]) for args in commands],
                         ['uci reorder','uci reorder','uci commit','lua','/usr/bin/rtp2.sh'])  # lua: apply's own process-rule sync
        self.assertEqual(n.journal_read()['phase'],'RESTORING');self.assertTrue(n.journal_read()['restore_rtp_dispatched'])

    def test_stale_lock_relaxation_is_limited_to_the_proven_pid(self):
        self.lock.write_text('999999\n')
        self.assertTrue(recovery.rtp_lock_busy())
        recovery.ALLOWED_STALE_LOCK[0]=999999
        try:
            self.assertFalse(recovery.rtp_lock_busy())
            self.lock.write_text('999998\n');self.assertTrue(recovery.rtp_lock_busy())
        finally:recovery.ALLOWED_STALE_LOCK[0]=None
        self.lock.unlink();self.assertFalse(recovery.rtp_lock_busy())


class VendorStop(unittest.TestCase):
    def test_rtp_gets_sigterm_first_so_its_trap_removes_the_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            lock=Path(directory)/'lock'
            script='trap \'rm -f "$1"; exit\' EXIT INT TERM; echo $$ > "$1"; sleep 30 & wait'
            process=subprocess.Popen(['sh','-c',script,'sh',str(lock)])
            for _ in range(50):
                if lock.exists():break
                __import__('time').sleep(.05)
            self.assertTrue(lock.exists())
            n.stop_vendor(process,['/usr/bin/rtp2.sh','not_reload_network'])
            self.assertIsNotNone(process.poll());self.assertFalse(lock.exists())

    def test_other_commands_are_killed_immediately(self):
        process=subprocess.Popen(['sh','-c','trap "" TERM; sleep 30'])
        n.stop_vendor(process,['ifup','wgclient1']);process.wait(timeout=5)
        self.assertEqual(process.returncode,-9)


# Minimal structure derived from the dedicated MT3000 incident graph (28 Oct
# 2026, rtp2.sh killed inside deal_instance for ovpnclient2): counters, FW3
# MTU rules and ipset bypass rules dropped; chains, hooks and mark rules kept.
LIVE_INCIDENT_MANGLE='''*mangle
:PREROUTING ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
:LOCAL_POLICY - [0:0]
:PORTAL_TTL - [0:0]
:POST_ROUTE_POLICY - [0:0]
:ROUTE_POLICY - [0:0]
:VPN_LOCAL_POLICY_DROP - [0:0]
:VPN_PREROUTING_HOOK - [0:0]
:vpn_in_new_mark - [0:0]
:wan_in_new_mark - [0:0]
-A PREROUTING -j VPN_PREROUTING_HOOK
-A OUTPUT -j LOCAL_POLICY
-A POSTROUTING -j POST_ROUTE_POLICY
-A LOCAL_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000
-A LOCAL_POLICY -m mark --mark 0x0/0xf000 -m owner --gid-owner 2100 -j MARK --set-xmark 0x1000/0xf000
-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000
-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN
-A VPN_LOCAL_POLICY_DROP -o br-lan -j RETURN
-A VPN_LOCAL_POLICY_DROP -j DROP
-A VPN_PREROUTING_HOOK -j vpn_in_new_mark
-A VPN_PREROUTING_HOOK -j wan_in_new_mark
-A VPN_PREROUTING_HOOK -i br-lan -j ROUTE_POLICY
-A vpn_in_new_mark -i wgclient1 -p tcp -m conntrack --ctstate NEW -m connmark ! --mark 0x1000/0xf000 -j CONNMARK --set-xmark 0x1000/0xf000
-A wan_in_new_mark -i apcli0 -p tcp -m conntrack --ctstate NEW -m connmark ! --mark 0x8000/0xf000 -j CONNMARK --set-xmark 0x8000/0xf000
COMMIT
'''


class LiveIncidentGraph(unittest.TestCase):
    """CONNMARK --restore-mark only re-applies a mark an existing connection already
    carries, and inbound CONNMARK --set-xmark only tags replies of connections that
    arrived on a tunnel/WAN; a new LAN connection gets no route mark at all and is
    blackholed by the VPN-only guard (fail closed). Only MARK or a TUNNEL route
    jump reachable from PREROUTING is new LAN routing. Router-local LOCAL_POLICY
    marking hangs off OUTPUT and is not LAN routing."""

    def journal(self):
        order=['global','default','a_primary','middle','a_reserve']
        return {'phase':'APPLYING','tx':'b'*32,'pid':2392,'before':order,'after':['global','default','a_reserve','middle','a_primary'],
                'rtp_dispatched':True,'forward_policy_touched':True,'kernel_before_verified':True,'kernel_before_fingerprint':'b'*64,
                'confirmed':None,'kernel_confirmed':None,'failure_code':'NATIVE-SYSTEM-001','rollback_failures':1,
                'failure_detail':{'stage':'worker-wait','error_type':'TimeoutExpired','worker_stage':'rtp-dispatch','elapsed_ms':56742}}

    def decide(self,text,journal=None):
        class Backend:
            def kernel_fingerprint(self):return 'a'*64
        with patch.object(n,'command',side_effect=lambda args,timeout=5:text.encode()):
            return recovery.vendor_rebuild_applies(Backend(),journal or self.journal())

    def test_live_incident_graph_is_unrouted_and_selects_the_rebuild(self):
        from kernel_policy import unrouted
        self.assertTrue(unrouted(LIVE_INCIDENT_MANGLE))
        self.assertTrue(self.decide(LIVE_INCIDENT_MANGLE))

    def test_any_new_lan_route_mark_or_tunnel_jump_is_routed(self):
        from kernel_policy import unrouted
        for extra in ('-A ROUTE_POLICY -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x1000/0xf000',
                      '-A ROUTE_POLICY -j FOREIGN','-A VPN_PREROUTING_HOOK -g FOREIGN'):
            text=LIVE_INCIDENT_MANGLE.replace(':wan_in_new_mark - [0:0]',':wan_in_new_mark - [0:0]\n:FOREIGN - [0:0]')
            text=text.replace('COMMIT',extra+'\n-A FOREIGN -j MARK --set-xmark 0x2000/0xf000\nCOMMIT')
            with self.subTest(extra=extra):
                self.assertFalse(unrouted(text));self.assertFalse(self.decide(text))
        tunnel=LIVE_INCIDENT_MANGLE.replace(':wan_in_new_mark - [0:0]',':wan_in_new_mark - [0:0]\n:TUNNEL4192_ROUTE_POLICY - [0:0]')
        self.assertFalse(unrouted(tunnel));self.assertFalse(self.decide(tunnel))

    def test_live_facts_with_unchanged_kernel_or_other_stage_do_not_select_the_rebuild(self):
        class Same:
            def kernel_fingerprint(self):return 'b'*64
        with patch.object(n,'command',side_effect=lambda args,timeout=5:LIVE_INCIDENT_MANGLE.encode()):
            self.assertFalse(recovery.vendor_rebuild_applies(Same(),self.journal()))
        for detail in ({'worker_stage':'rtp-returned'},{}):
            self.assertFalse(self.decide(LIVE_INCIDENT_MANGLE,dict(self.journal(),failure_detail=detail)))
        self.assertFalse(self.decide(LIVE_INCIDENT_MANGLE,dict(self.journal(),restore_before_order=self.journal()['before'])))


if __name__=='__main__':unittest.main()
