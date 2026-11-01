"""Real minimal RTP boot preparation in an isolated temporary filesystem."""
import hashlib,json,os,stat,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair,rtp_boot as boot

ACTUAL_PINS=dict(boot.PINS)


class BootContract(unittest.TestCase):
    def enter(self,context):
        result=context.__enter__();self.addCleanup(context.__exit__,None,None,None);return result

    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name)
        self.root=self.base/'router';self.root.mkdir();self.runtime=self.base/'runtime';self.runtime.mkdir()
        self.persist=self.base/'persist';self.persist.mkdir()
        for module in (agent,n,auto_control):
            self.enter(patch.object(module,'RUNTIME',self.runtime))
            if hasattr(module,'PERSIST'):self.enter(patch.object(module,'PERSIST',self.persist))
        self.enter(patch.object(boot,'ROOT',self.root))
        self.commands=self.enter(patch.object(n,'command',side_effect=AssertionError('No router command is allowed')))
        self.spawn=self.enter(patch.object(n.subprocess,'Popen',side_effect=AssertionError('No subprocess is allowed')))
        self.revision=auto_control.current_revision()
        self.state={'id':'a'*32,'phase':'RUNNING','owned':[],
            'before_flags':{'wgclient1':'1','ovpnclient1':'1'},'network_identity':'b'*64,
            'protected':{},'process_bindings':None,'order':['s','t'],'policy_hash':'c'*64,'revision':self.revision}
        pair.save(self.state)
        agent.atomic_json(pair.paths()[0],{'mode':'on','id':self.state['id'],'revision':self.revision,'time':1})
        for name in ('tmp/run','tmp/sysinfo','etc/init.d','usr/bin'):
            (self.root/name).mkdir(parents=True,exist_ok=True)
        (self.root/'tmp').chmod(0o1777)
        self.sources={'/etc/init.d/vpn-client':b'#!/bin/sh\nboot() { :; }\n','/usr/bin/rtp2.sh':b'#!/bin/sh\n[ -f /tmp/run/vpn-client-booted ] || exit 0\n'}
        for name,source in self.sources.items():(self.root/name.lstrip('/')).write_bytes(source)
        self.enter(patch.object(boot,'PINS',{name:hashlib.sha256(source).hexdigest()for name,source in self.sources.items()}))
        (self.root/'tmp/sysinfo/board_name').write_text('glinet,mt3000-snand\n')
        (self.root/'etc/glversion').write_text('4.11.0\n')
        self.marker=self.root/'tmp/run/vpn-client-booted'
        self.directories=[self.root/'tmp/resolv.conf.d',self.root/'tmp/hosts.vpn']
        self.record=self.runtime/'rtp-boot-preparation.json'

    def assert_no_preparation(self):
        self.assertFalse(self.record.exists())
        self.assertFalse(self.directories[0].exists())
        self.assertFalse(self.directories[1].exists())
        self.assertFalse(self.marker.exists())
        self.commands.assert_not_called();self.spawn.assert_not_called()

    def test_readonly_assess_distinguishes_safe_missing_prefix_from_ready(self):
        self.assertEqual(boot.assess(self.root),{'safe':True,'ready':False,'kernel_verified':False})
        with self.assertRaisesRegex(ValueError,boot.CODE):boot.ready(self.root)
        self.assert_no_preparation()

    def test_recovery_prefix_after_power_cut_needs_no_auto_intent(self):
        # soak trial 31.10.2026: after a power cut the intent (RAM) is gone and the prefix too; the supervisor's
        # rollback must still find the stock prefix, created exactly as prepare() creates it, and nothing else.
        agent.atomic_json(pair.paths()[0],{'mode':'off','id':self.state['id'],'revision':self.revision,'time':1})
        self.assertTrue(boot.recovery_prefix(self.root))
        self.assertEqual(self.marker.read_bytes(),b'');self.assertEqual(stat.S_IMODE(self.marker.stat().st_mode),0o600)
        for path in self.directories:self.assertTrue(path.is_dir());self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o755)
        self.assertFalse(self.record.exists())
        self.assertTrue(boot.recovery_prefix(self.root))  # idempotent
        self.commands.assert_not_called();self.spawn.assert_not_called()

    def test_recovery_prefix_refuses_a_foreign_contract(self):
        (self.root/'etc/glversion').write_text('4.12.0\n')
        with self.assertRaisesRegex(ValueError,boot.CODE):boot.recovery_prefix(self.root)
        self.assert_no_preparation()

    def test_cold_prefix_creates_only_runtime_dirs_and_empty_gate_without_kernel_claim(self):
        answer=boot.prepare(self.revision,self.root)
        self.assertEqual(answer,{'prepared':True,'changed':True,'kernel_verified':False})
        self.assertEqual(self.marker.read_bytes(),b'');self.assertEqual(stat.S_IMODE(self.marker.stat().st_mode),0o600)
        for path in self.directories:self.assertTrue(path.is_dir());self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o755)
        self.assertEqual(boot.assess(self.root),{'safe':True,'ready':True,'kernel_verified':False})
        self.assertTrue(boot.ready(self.root));self.assertEqual(agent.read_json(self.record)['state'],'VERIFIED')
        self.commands.assert_not_called();self.spawn.assert_not_called()

    def test_idempotent_prepare_does_not_rewrite_record_marker_or_runtime_dirs(self):
        boot.prepare(self.revision,self.root)
        before={path:(path.stat().st_ino,path.stat().st_mtime_ns,path.read_bytes()if path.is_file()else None)
                for path in [self.record,self.marker]+self.directories}
        with patch.object(agent,'atomic_json',wraps=agent.atomic_json)as writes:
            self.assertEqual(boot.prepare(self.revision),{'prepared':True,'changed':False,'kernel_verified':False})
        writes.assert_not_called()
        self.assertEqual(before,{path:(path.stat().st_ino,path.stat().st_mtime_ns,path.read_bytes()if path.is_file()else None)for path in before})

    def test_partial_safe_prefix_preserves_existing_directory_contents(self):
        self.directories[0].mkdir();keep=self.directories[0]/'existing.conf';keep.write_bytes(b'preserve')
        boot.prepare(self.revision,self.root)
        self.assertEqual(keep.read_bytes(),b'preserve');self.assertTrue(boot.ready(self.root))

    def test_both_real_firmware_pins_match_the_public_audit_manifest(self):
        audit=json.loads((Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn/native-audit-hashes.json').read_text())
        self.assertEqual(set(ACTUAL_PINS),{'/etc/init.d/vpn-client','/usr/bin/rtp2.sh'})
        self.assertEqual(ACTUAL_PINS,{name:audit[name]for name in ACTUAL_PINS})

    def test_changed_or_missing_each_pinned_script_refuses_before_any_mutation(self):
        for name,source in self.sources.items():
            path=self.root/name.lstrip('/')
            with self.subTest(name=name):
                path.write_bytes(source+b'# foreign\n')
                with self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
                self.assert_no_preparation();path.unlink()
                with self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
                self.assert_no_preparation();path.write_bytes(source)

    def test_wrong_model_or_firmware_refuses_before_any_mutation(self):
        for name,wrong in (('tmp/sysinfo/board_name','glinet,gl-mt6000'),('etc/glversion','4.10.0')):
            path=self.root/name;original=path.read_bytes();path.write_text(wrong)
            with self.subTest(name=name),self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
            self.assert_no_preparation();path.write_bytes(original)

    def test_marker_symlink_and_nonempty_or_directory_gate_are_never_accepted(self):
        outside=self.base/'outside';outside.write_bytes(b'owner-data')
        for kind in ('symlink','nonempty','directory'):
            with self.subTest(kind=kind):
                if kind=='symlink':self.marker.symlink_to(outside)
                elif kind=='directory':self.marker.mkdir()
                else:self.marker.write_bytes(b'foreign')
                with self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
                self.assertFalse(self.record.exists());self.assertFalse(self.directories[0].exists());self.assertFalse(self.directories[1].exists())
                self.assertEqual(outside.read_bytes(),b'owner-data')
                if kind=='directory':self.marker.rmdir()
                else:self.marker.unlink()

    def test_unsafe_second_optional_directory_is_checked_before_first_is_created(self):
        self.directories[1].write_bytes(b'foreign')
        with self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
        self.assertFalse(self.directories[0].exists());self.assertFalse(self.marker.exists());self.assertFalse(self.record.exists())
        self.assertEqual(self.directories[1].read_bytes(),b'foreign')

    def test_optional_directory_symlink_cannot_redirect_a_write(self):
        outside=self.base/'outside';outside.mkdir();self.directories[1].symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
        self.assertEqual(list(outside.iterdir()),[]);self.assertFalse(self.directories[0].exists());self.assertFalse(self.record.exists())

    def test_runtime_parent_symlink_is_rejected(self):
        run=self.root/'tmp/run';run.rmdir();outside=self.base/'outside';outside.mkdir();run.symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
        self.assertEqual(list(outside.iterdir()),[]);self.assertFalse(self.record.exists())

    def test_group_or_world_writable_runtime_paths_are_rejected(self):
        for name in ('tmp/run','tmp/resolv.conf.d','tmp/hosts.vpn','tmp/run/vpn-client-booted'):
            path=self.root/name;created=not path.exists()
            if created:
                if name.endswith('booted'):path.touch()
                else:path.mkdir()
            original=stat.S_IMODE(path.stat().st_mode);path.chmod(0o777 if path.is_dir()else 0o666)
            with self.subTest(name=name),self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
            self.assertFalse(self.record.exists());path.chmod(original)
            if created:
                if path.is_dir():path.rmdir()
                else:path.unlink()

    def test_tmp_requires_sticky_world_writable_directory_contract(self):
        for mode in (0o777,0o755,0o1775):
            (self.root/'tmp').chmod(mode)
            with self.subTest(mode=mode),self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
            self.assert_no_preparation()

    def test_foreign_owner_is_not_treated_as_our_preparation(self):
        original=Path.lstat;target=self.root/'tmp/run'
        def foreign(path,*args,**kwargs):
            info=original(path,*args,**kwargs)
            if path==target:
                values=list(info);values[4]=os.geteuid()+1;return os.stat_result(values)
            return info
        with patch.object(Path,'lstat',foreign),self.assertRaisesRegex(n.Refused,boot.CODE):boot.prepare(self.revision,self.root)
        self.assert_no_preparation()

    def test_stale_revision_refuses_before_any_prefix_mutation(self):
        auto_control.current_revision(rotate=True)
        with self.assertRaisesRegex(n.Refused,'CLIENT-STOP'):boot.prepare(self.revision,self.root)
        self.assert_no_preparation()

    def test_off_or_foreign_session_or_terminal_state_refuses_with_current_revision(self):
        record=agent.read_json(pair.paths()[0])
        for changed in (dict(record,mode='off'),dict(record,id='f'*32),dict(record,revision='f'*32)):
            agent.atomic_json(pair.paths()[0],changed)
            with self.subTest(intent=changed),self.assertRaisesRegex(n.Refused,'CLIENT-STOP'):boot.prepare(self.revision,self.root)
            self.assert_no_preparation()
        agent.atomic_json(pair.paths()[0],record)
        for phase in ('STOPPING','STOPPED','FAILED'):
            pair.save(dict(self.state,phase=phase))
            with self.subTest(phase=phase),self.assertRaisesRegex(n.Refused,'CLIENT-STOP'):boot.prepare(self.revision,self.root)
            self.assert_no_preparation()

    def test_revision_is_rechecked_before_each_mutation_and_final_acknowledgement(self):
        real=n.require_control_revision
        # First check authorizes the record, checks 2/3 authorize each directory,
        # check 4 the marker, and the last check the VERIFIED acknowledgement.
        for stop_at in (2,3,4,5):
            calls=[0]
            def stopped(revision):
                calls[0]+=1
                if calls[0]==stop_at:raise n.Refused('CLIENT-STOP')
                return real(revision)
            with self.subTest(stop_at=stop_at),patch.object(n,'require_control_revision',side_effect=stopped):
                with self.assertRaisesRegex(n.Refused,'CLIENT-STOP'):boot.prepare(self.revision,self.root)
            self.assertEqual(agent.read_json(self.record)['state'],'PREPARED')
            self.assertEqual([path.exists()for path in self.directories],[stop_at>2,stop_at>3])
            self.assertEqual(self.marker.exists(),stop_at>4)
            if self.marker.exists():self.marker.unlink()
            for path in reversed(self.directories):
                if path.exists():path.rmdir()
            self.record.unlink()
        self.commands.assert_not_called();self.spawn.assert_not_called()


if __name__=='__main__':unittest.main()
