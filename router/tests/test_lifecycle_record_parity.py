"""The embedded lifecycle guard refuses every journal and pair record the controllers refuse to read (audit 06.11.2026,
F-15): a record native_switch.validate_journal or pair_auto.read_state rejects cannot be recovered by the new supervisor,
so neither removal nor an upgrade may rely on it. Also F-18: a live Lua Auto supervisor counts as a live apply worker."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import lifecycle_guard as lifecycle
import native_switch
import pair_auto

JOURNAL={'before':['a','b','c'],'after':['b','a','c'],'hash':'f'*64,'phase':'APPLYING','tx':'b'*32,'pid':2392,
         'rtp_dispatched':True,'source':'wireguard:1','target':'openvpn:2','trial_nonce':'n'*16,'started':90,'deadline':200}
PAIR={'phase':'STOPPED','id':'a'*32,'owned':['wgclient1'],'before_flags':{'wgclient1':'0','ovpnclient1':'1'},'network_identity':'e'*64}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def changed(base,**changes):
    value=copy.deepcopy(base)
    for key,item in changes.items():
        if item is KeyError:value.pop(key,None)
        else:value[key]=item
    return value


JOURNAL_DEFECTS=[
    ('proof_scope',dict(proof_scope='invalid')),('proof_scope type',dict(proof_scope=1)),
    ('empty process_bindings',dict(process_bindings={})),('duplicate marks',dict(process_bindings={'wgclient1':1,'ovpnclient1':1})),
    ('foreign binding',dict(process_bindings={'lan':1,'ovpnclient1':2})),('phase',dict(phase='CORRUPT')),
    ('negative started',dict(started=-1)),('deadline before start',dict(deadline=10)),('pid 1',dict(pid=1)),
    ('trial type',dict(trial='yes')),('control revision',dict(control_revision='x')),('vendor identity',dict(vendor_identity='F'*64)),
    ('same source and target',dict(target='wireguard:1')),('missing nonce',dict(trial_nonce=KeyError)),
    ('rollback failures',dict(rollback_failures=3)),('restore order',dict(restore_before_order=['a','b'])),
    ('bool flag',dict(kernel_before_verified=1)),('missing started',dict(started=KeyError)),
]
PAIR_DEFECTS=[
    ('phase',dict(phase='PAUSED')),('id',dict(id='a'*31)),('owned foreign',dict(owned=['lan'])),('owned duplicate',dict(owned=['wgclient1','wgclient1'])),
    ('flags keys',dict(before_flags={'wgclient1':'0'})),('flag value',dict(before_flags={'wgclient1':'2','ovpnclient1':'1'})),
    ('network identity',dict(network_identity=KeyError)),('interfaces',dict(interfaces={'wgclient1':'openvpn','ovpnclient1':'ovpnclient'})),
]


class RecordParity(unittest.TestCase):
    def controller_journal(self,value):
        try:native_switch.validate_journal(copy.deepcopy(value));return True
        except native_switch.Refused:return False

    def controller_pair(self,envelope):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pair-auto-state.json';path.write_text(json.dumps(envelope))
            with patch.object(pair_auto,'paths',return_value=(Path(directory)/'control.json',path)):
                try:pair_auto.read_state();return True
                except ValueError:return False

    def guard(self,journal=None,pair=None):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);persist=root/'etc/homensai-vpn';persist.mkdir(parents=True);(root/'proc').mkdir()
            if journal is not None:(persist/'native-transaction.json').write_text(json.dumps({'schema':1,'data':journal,'sha256':digest(journal)}))
            if pair is not None:(persist/'pair-auto-state.json').write_text(json.dumps(pair))
            try:lifecycle.snapshot(root,upgrade=True);return True
            except ValueError:return False

    def test_valid_records_pass_both(self):
        self.assertTrue(self.controller_journal(JOURNAL));self.assertTrue(self.guard(journal=JOURNAL))
        envelope={'data':PAIR,'sha256':digest(PAIR)}
        self.assertTrue(self.controller_pair(envelope));self.assertTrue(self.guard(pair=envelope))

    def test_journals_the_controller_refuses_are_refused_by_the_guard(self):
        for label,defect in JOURNAL_DEFECTS:
            journal=changed(JOURNAL,**defect)
            with self.subTest(label=label):
                self.assertFalse(self.controller_journal(journal),'fixture: the controller refuses it')
                self.assertFalse(self.guard(journal=journal),'the guard must refuse it as well')

    def test_pair_records_the_controller_refuses_are_refused_by_the_guard(self):
        cases=[('corrupt checksum of a STOPPED session',{'data':PAIR,'sha256':'0'*64}),('no checksum',{'data':PAIR}),
               ('no data',{'sha256':digest(PAIR)})]
        cases+=[(label,{'data':changed(PAIR,**defect),'sha256':digest(changed(PAIR,**defect))}) for label,defect in PAIR_DEFECTS]
        for label,envelope in cases:
            with self.subTest(label=label):
                self.assertFalse(self.controller_pair(envelope),'fixture: the controller refuses it')
                self.assertFalse(self.guard(pair=envelope),'the guard must refuse it as well')


TRANSITION={'source_rule':'a','target_rule':'b','direction':'first','generic_rules':['a','b'],'source_id':'wireguard:1',
            'target_id':'openvpn:2','destination_role':'target','before_policy_role':'source','session_order':['b','a','c'],
            'primary_order':['a','b','c']}
PAIRED=changed(JOURNAL,pair_transition=TRANSITION)
RESTORING=changed(PAIRED,phase='RESTORING',restore_before_verified=True,restore_kernel_fingerprint='c'*64,
                  restore_before_order=['b','a','c'],restore_target_order=['a','b','c'],
                  restore_order_step={'version':1,'kind':'reorder','before':['b','a','c'],'after':['a','b','c'],'section':'a','index':0})
PROFILES={'source':{'id':'wireguard:1','protocol':'wireguard','interface':'1','vendor_tunnel_id':'wireguard:1','vendor_generation':'d'*32},
          'target':{'id':'openvpn:2','protocol':'openvpn','interface':'2','vendor_tunnel_id':'openvpn:2','vendor_generation':'e'*32}}
HELD=changed(PAIR,phase='HELD',protected_static={'firewall':'9'*64})
# Records the readers accept: the guard must accept them too, or upgrades would be refused for nothing.
NESTED_VALID=[('pair transition',PAIRED),('restore step',RESTORING),
              ('commit step',changed(RESTORING,restore_order_step={'version':1,'kind':'commit','before':['a','b','c'],'after':['a','b','c']})),
              ('vendor profiles',changed(JOURNAL,vendor_profiles=PROFILES)),('null pair transition',changed(JOURNAL,pair_transition=None))]
# Delegated rules (pair_policy.metadata, rollback_recovery.validate_step, failure_diagnosis.profile_identity) the guard skipped
# before 07.11.2026 (N3 item 3).
NESTED_DEFECTS=[
    ('empty pair transition',dict(pair_transition={})),
    ('pair transition wrong source id',dict(pair_transition=dict(TRANSITION,source_id='wireguard:9'))),
    ('pair transition after mismatch',dict(pair_transition=dict(TRANSITION,destination_role='source'))),
    ('pair transition unknown generic rule',dict(pair_transition=dict(TRANSITION,generic_rules=['a','z']))),
    ('empty restore step',dict(restore_order_step={})),
    ('restore proof source alone',dict(restore_proof_source='forward')),
    ('restore order origin alone',dict(restore_order_origin=['b','a','c'])),
    ('vendor profile without generation',dict(vendor_profiles={'source':{'id':'wireguard:1'},'target':{'id':'openvpn:2'}})),
    ('vendor profile extra key',dict(vendor_profiles=dict(PROFILES,source=dict(PROFILES['source'],extra=1)))),
]
NESTED_STEP_DEFECTS=[
    ('step on APPLYING phase',dict(phase='APPLYING')),
    ('step not a canonical move',dict(restore_order_step=dict(RESTORING['restore_order_step'],index=1))),
    ('step without verified before',dict(restore_before_verified=False)),
    ('restore target outside policy',dict(restore_target_order=['c','b','a'])),
]
PAIR_NESTED_DEFECTS=[
    ('empty protected_static on HELD',dict(protected_static={})),('protected_static bad hash',dict(protected_static={'firewall':'x'})),
    ('kept on a HELD session',dict(kept=['wgclient1'],kept_flags={'wgclient1':'0'},kept_at=5)),
    ('handover on a HELD session',dict(handover={'tx':'a'*32,'order':['a','b'],'policy_hash':'f'*64,'at':5})),
    ('manual hold value',dict(manual_hold='both')),('manual hold source',dict(manual_hold_source='rpc')),
    ('policy roles empty',dict(policy_roles={},order=['a','b'])),
    ('selected policy without roles',dict(selected_policy={'role':'source','order':['a','b'],'hash':None,'since':5})),
    ('manual selection empty',dict(manual_selection={})),
]


class NestedRecordParity(RecordParity):
    def both(self,journal,pair):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);persist=root/'etc/homensai-vpn';persist.mkdir(parents=True);(root/'proc').mkdir()
            (persist/'native-transaction.json').write_text(json.dumps({'schema':1,'data':journal,'sha256':digest(journal)}))
            (persist/'pair-auto-state.json').write_text(json.dumps(pair))
            try:lifecycle.snapshot(root,upgrade=True);return True
            except ValueError:return False

    def test_valid_nested_records_pass_both(self):
        for label,journal in NESTED_VALID:
            with self.subTest(label=label):
                self.assertTrue(self.controller_journal(journal),'fixture: the controller reads it')
                self.assertTrue(self.guard(journal=journal))
        envelope={'data':HELD,'sha256':digest(HELD)}
        self.assertTrue(self.controller_pair(envelope))
        self.assertTrue(self.both(JOURNAL,envelope),'a readable HELD pair beside a dead interrupted journal')

    def test_nested_journal_defects_are_refused_by_both(self):
        cases=[(label,changed(JOURNAL,**defect)) for label,defect in NESTED_DEFECTS]
        cases+=[(label,changed(RESTORING,**defect)) for label,defect in NESTED_STEP_DEFECTS]
        for label,journal in cases:
            with self.subTest(label=label):
                self.assertFalse(self.controller_journal(journal),'fixture: the controller refuses it')
                self.assertFalse(self.guard(journal=journal),'the guard must refuse it as well')

    def test_nested_pair_defects_are_refused_by_both(self):
        for label,defect in PAIR_NESTED_DEFECTS:
            data=changed(HELD,**defect);envelope={'data':data,'sha256':digest(data)}
            with self.subTest(label=label):
                self.assertFalse(self.controller_pair(envelope),'fixture: the controller refuses it')
                self.assertFalse(lifecycle.valid_pair_state(envelope))
                self.assertFalse(self.both(JOURNAL,envelope),'an upgrade must not rely on it')

    def test_delegated_copies_match_the_real_validators(self):
        import failure_diagnosis,pair_policy,rollback_recovery
        orders=[['a','b','c'],['b','a','c'],['c','b','a'],['a','c','b']]
        for before in orders:
            for target in orders:
                self.assertEqual(lifecycle.order_steps(before,target),list(rollback_recovery.order_steps(before,target)))
            for direction in ('first','last'):
                value=dict(TRANSITION,direction=direction)
                for destination in ('source','target'):
                    self.assertEqual(lifecycle.desired_order(value,before,destination),pair_policy.desired_order(value,before,destination))
        for profile in list(PROFILES.values())+[dict(PROFILES['source'],section='1'),dict(PROFILES['source'],section='2'),
                                                 dict(PROFILES['source'],vendor_generation='D'*32),dict(PROFILES['source'],id='wireguard:'),
                                                 dict(PROFILES['source'],vendor_tunnel_id='openvpn:1'),None,{}]:
            self.assertEqual(lifecycle.profile_identity(profile),failure_diagnosis.profile_identity(profile))


class LuaSupervisorIsAWorker(unittest.TestCase):
    def table(self,*commands):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name)
        for pid,command in enumerate(commands,start=100):
            (root/'proc'/str(pid)).mkdir(parents=True);(root/'proc'/str(pid)/'cmdline').write_bytes(command)
        return root

    def test_lua_supervisors_count_as_alive_monitor_does_not(self):
        for command in (b'/usr/bin/lua\0/usr/lib/homensai-vpn/lua/auto.lua\0daemon\0',
                        b'/usr/bin/lua\0/usr/lib/homensai-vpn/lua/hv_core.lua\0daemon\0'):
            with self.subTest(command=command):self.assertTrue(lifecycle.apply_worker_alive(self.table(b'/sbin/procd\0',command)))
        self.assertFalse(lifecycle.apply_worker_alive(self.table(b'/sbin/procd\0',b'/usr/bin/lua\0/usr/lib/homensai-vpn/lua/monitor.lua\0daemon\0',
                                                                 b'/usr/bin/python3\0/usr/lib/homensai-vpn/native_switch.py\0daemon\0')))

    def test_hv_core_standby_counts_only_after_a_fallback(self):
        # N3 item 4 (07.11.2026): the standby applies nothing; it may exec into auto.lua only once the fallback file exists.
        root=self.table(b'/sbin/procd\0',STANDBY)
        self.assertFalse(lifecycle.apply_worker_alive(root))
        runtime=root/'var/run/homensai-vpn';runtime.mkdir(parents=True);(runtime/'hv-core-fallback.json').write_text('{}')
        self.assertTrue(lifecycle.apply_worker_alive(root))


STANDBY=b'/usr/bin/lua\0/usr/lib/homensai-vpn/lua/hv_core.lua\0standby\0'
AUTO=b'/usr/bin/lua\0/usr/lib/homensai-vpn/lua/auto.lua\0daemon\0'
GIVEN_UP=changed(JOURNAL,phase='RESTORING',rollback_failures=2,pid=None)
NOW=1_000_000.0
ALARM={'state':'BLOCKED','alarm':'ROLLBACK-GIVEN-UP','blockers':['ROLLBACK-GIVEN-UP'],'original_restored':False,
       'source':'wireguard:1','target':'openvpn:2','guard':'VPN-only; IPv6 forwarded traffic blocked','time':NOW-8}


class GiveUpQuiescence(unittest.TestCase):
    """N3 item 4 (07.11.2026): a Lua supervisor idle in rollback.give_up (ROLLBACK-GIVEN-UP) must not block the upgrade
    that repairs it; an actual writer, an active transaction or missing evidence still blocks."""
    def root(self,status=ALARM,commands=(AUTO,),marker=False,raw_status=None):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name);runtime=root/'var/run/homensai-vpn';runtime.mkdir(parents=True)
        for pid,command in enumerate(commands,start=100):
            (root/'proc'/str(pid)).mkdir(parents=True);(root/'proc'/str(pid)/'cmdline').write_bytes(command)
        if raw_status is not None:(runtime/'native-status.json').write_text(raw_status)
        elif status is not None:(runtime/'native-status.json').write_text(json.dumps(status))
        if marker:(runtime/'writer-unresolved').write_text('4242')
        return root

    def test_idle_give_up_supervisor_does_not_block(self):
        for commands in ((AUTO,),(b'/usr/bin/lua\0/usr/lib/homensai-vpn/lua/hv_core.lua\0daemon\0',),(AUTO,STANDBY)):
            with self.subTest(commands=commands):
                self.assertFalse(lifecycle.apply_worker_alive(self.root(commands=commands),GIVEN_UP,now=NOW))

    def test_snapshot_reaches_the_upgrade_exception(self):
        root=self.root();persist=root/'etc/homensai-vpn';persist.mkdir(parents=True)
        (persist/'native-transaction.json').write_text(json.dumps({'schema':1,'data':GIVEN_UP,'sha256':digest(GIVEN_UP)}))
        with patch.object(lifecycle.time,'time',return_value=NOW):
            interrupted=lifecycle.snapshot(root,upgrade=True)[-1]
        self.assertIs(interrupted,True)

    def test_missing_or_contrary_evidence_keeps_refusing(self):
        cases=[('unresolved writer marker',self.root(marker=True),GIVEN_UP),
               ('no status',self.root(status=None),GIVEN_UP),
               ('unreadable status',self.root(raw_status='{"state":'),GIVEN_UP),
               ('stale alarm',self.root(status=dict(ALARM,time=NOW-600)),GIVEN_UP),
               ('future alarm',self.root(status=dict(ALARM,time=NOW+600)),GIVEN_UP),
               ('other alarm',self.root(status=dict(ALARM,alarm='JOURNAL-INTEGRITY-FAILED')),GIVEN_UP),
               ('not blocked',self.root(status=dict(ALARM,state='RESTORING')),GIVEN_UP),
               ('alarm of another journal',self.root(status=dict(ALARM,target='openvpn:9')),GIVEN_UP),
               ('rollback attempts left',self.root(),changed(GIVEN_UP,rollback_failures=1)),
               ('no failure count',self.root(),changed(GIVEN_UP,rollback_failures=KeyError)),
               ('finished journal',self.root(),changed(GIVEN_UP,phase='COMMITTED')),
               ('no journal',self.root(),None),
               ('python apply child',self.root(commands=(AUTO,b'/usr/bin/python3\0/usr/lib/homensai-vpn/native_switch.py\0apply\0x\0')),GIVEN_UP)]
        for label,root,journal in cases:
            with self.subTest(label=label):
                self.assertTrue(lifecycle.apply_worker_alive(root,journal,now=NOW))


if __name__=='__main__':unittest.main()
