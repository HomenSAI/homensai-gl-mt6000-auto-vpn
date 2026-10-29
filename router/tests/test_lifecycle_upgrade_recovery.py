"""Upgrade over an interrupted journal whose apply worker is provably gone.

The live MT3000 (alpha57) holds an APPLYING journal from a dead apply child
(pid 2392). Without this exception the new package can never be installed and
the old one can never recover it. Removal ('check') keeps refusing; the journal,
guard and pair record are never written by the lifecycle guard.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import lifecycle_guard as lifecycle

TX='b'*32
APPLY=('/usr/bin/python3\0/usr/lib/homensai-vpn/native_switch.py\0apply\0'+TX+'\0').encode()


class UpgradeOverInterruptedJournal(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.runtime=self.root/'var/run/homensai-vpn';self.persist=self.root/'etc/homensai-vpn'
        for path in (self.runtime,self.persist,self.root/'proc'):path.mkdir(parents=True)
        self.process(1,b'/sbin/procd\0');self.process(9082,b'/usr/bin/python3\0/usr/lib/homensai-vpn/native_switch.py\0')
        self.journal({'phase':'APPLYING','tx':TX,'pid':2392,'rtp_dispatched':True})
        self.write(self.persist/'pair-auto-state.json',{'data':{'phase':'HELD','recovery_error':'PAIR-RECOVERY-REQUIRED'},'sha256':'x'})
        self.write(self.runtime/'pair-auto-control.json',{'mode':'off','revision':'c'*32})
        self.write(self.runtime/'native-status.json',{'state':'BLOCKED','blockers':['PAIR-RECOVERY-REQUIRED'],'time':100})

    def write(self,path,value):path.write_text(json.dumps(value))

    def process(self,pid,command):
        directory=self.root/'proc'/str(pid);directory.mkdir(exist_ok=True);(directory/'cmdline').write_bytes(command)

    def journal(self,extra):
        data=dict({'before':['a','b','c'],'after':['b','a','c'],'hash':'f'*64},**extra)
        digest=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        self.write(self.persist/'native-transaction.json',{'schema':1,'data':data,'sha256':digest})

    def outcome(self,upgrade=True):
        try:return lifecycle.assess(*lifecycle.snapshot(self.root,upgrade=upgrade))
        except ValueError as error:return str(error)

    def files(self):
        return {str(p):p.read_bytes() for p in sorted(self.root.rglob('*')) if p.is_file()}

    def test_dead_incident_journal_allows_upgrade_and_writes_only_the_auto_options(self):
        self.assertIsNone(self.outcome())
        before=self.files();calls=[]
        def run(args,**kwargs):
            calls.append((args,kwargs.get('input')))
            return type('Reply',(),{'returncode':0,'stdout':b''})()
        real=lifecycle.snapshot
        with patch.object(lifecycle,'control_lock',nullcontext),patch.object(lifecycle.subprocess,'run',side_effect=run),\
                patch.object(lifecycle,'snapshot',side_effect=lambda upgrade=False:real(self.root,upgrade=upgrade)):
            lifecycle.main('prepare')
        self.assertEqual(self.files(),before,'journal, pair record and status stay byte-identical')
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][0],['/sbin/uci','-q','batch'])
        self.assertEqual(calls[0][1],b"set homensai_vpn.main.native_enabled='0'\nset homensai_vpn.main.native_until='0'\nset homensai_vpn.main.native_trial=''\ncommit homensai_vpn\n")

    def test_recorded_pid_reused_by_an_unrelated_process_is_dead_for_us(self):
        self.process(2392,b'/usr/sbin/dnsmasq\0');self.assertIsNone(self.outcome())

    def test_every_interrupted_phase_and_stopped_state_qualifies(self):
        for phase in sorted(lifecycle.INTERRUPTED):
            for state in ('BLOCKED','STOPPED'):
                self.journal({'phase':phase,'tx':TX,'pid':2392})
                self.write(self.runtime/'native-status.json',{'state':state,'time':100})
                with self.subTest(phase=phase,state=state):self.assertIsNone(self.outcome())

    def test_live_recorded_apply_child_refuses(self):
        self.process(2392,APPLY);self.assertIsNotNone(self.outcome())

    def test_any_other_live_apply_child_refuses(self):
        self.process(4444,('/usr/bin/python3\0/usr/lib/homensai-vpn/native_switch.py\0apply\0'+'d'*32+'\0').encode())
        self.assertIsNotNone(self.outcome())

    def test_unreadable_process_table_refuses(self):
        (self.root/'proc/1/cmdline').unlink();(self.root/'proc/1').rmdir();(self.root/'proc/9082/cmdline').unlink()
        (self.root/'proc/9082').rmdir();(self.root/'proc').rmdir()
        self.assertIsNotNone(self.outcome())

    def test_on_intent_or_unacknowledged_native_intent_refuses(self):
        self.write(self.runtime/'pair-auto-control.json',{'mode':'on','revision':'c'*32})
        self.assertEqual(self.outcome(),'LIFECYCLE-STOP-AUTO-FIRST')
        self.write(self.runtime/'pair-auto-control.json',{'mode':'off'})
        self.write(self.runtime/'auto-control.json',{'mode':'on','trial':'t','time':1})
        args=list(lifecycle.snapshot(self.root,upgrade=True));args[0]={'native_enabled':'0','native_trial':'t'}
        self.assertEqual(lifecycle.assess(*args),'LIFECYCLE-STOP-AUTO-FIRST')
        self.write(self.persist/'native-stop.json',{'trial':'t','requested':50})
        args=list(lifecycle.snapshot(self.root,upgrade=True));args[0]={'native_enabled':'0','native_trial':'t'}
        self.assertIsNone(lifecycle.assess(*args),'an acknowledged stop of that trial is accepted')

    def test_enabled_native_flag_without_ack_refuses(self):
        args=list(lifecycle.snapshot(self.root,upgrade=True));args[0]={'native_enabled':'1','native_trial':'t'}
        self.assertIsNotNone(lifecycle.assess(*args))

    def test_active_unknown_or_missing_native_state_refuses(self):
        for status in ({'state':'APPLYING'},{'state':'RESTORING'},{'state':'COMMITTED'},{'state':'STOPPED-ON-RESERVE'},
                       {'state':'UNKNOWN'},{'state':'BLOCKED','guard':'closed'},{}):
            self.write(self.runtime/'native-status.json',status)
            with self.subTest(status=status):self.assertIsNotNone(self.outcome())

    def test_unknown_or_committed_phase_refuses(self):
        for phase in ('COMMITTED','HELD-ON-RESERVE','RELEASE-PENDING','CORRUPT'):
            self.journal({'phase':phase,'tx':TX,'pid':2392})
            with self.subTest(phase=phase):self.assertIsNotNone(self.outcome())

    def test_starting_pair_session_refuses(self):
        self.write(self.persist/'pair-auto-state.json',{'data':{'phase':'STARTING'}})
        self.assertEqual(self.outcome(),'LIFECYCLE-STOP-AUTO-FIRST')

    def test_removal_check_keeps_refusing_the_same_incident(self):
        self.assertIsNone(self.outcome())
        self.assertIsNotNone(self.outcome(upgrade=False))
        before=self.files();real=lifecycle.snapshot
        with patch.object(lifecycle,'control_lock',nullcontext),patch.object(lifecycle.subprocess,'run') as run,\
                patch.object(lifecycle,'snapshot',side_effect=lambda upgrade=False:real(self.root,upgrade=upgrade)),\
                self.assertRaises(SystemExit):
            lifecycle.main('check')
        run.assert_not_called();self.assertEqual(self.files(),before)

    def test_package_hooks_use_prepare_for_install_and_check_for_removal(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from package_hooks import scripts
        hooks=scripts()
        self.assertIn('/usr/bin/python3 - prepare',hooks['preinst']);self.assertIn('/usr/bin/python3 - prepare',hooks['postinst'])
        self.assertIn('/usr/bin/python3 - "$action"',hooks['prerm']);self.assertNotIn('/usr/bin/python3 - prepare',hooks['prerm'])

    def test_old_prerm_passes_upgrade_only_for_opkg_upgrade_and_check_otherwise(self):
        # opkg (OpenWrt 21.02, 1bf042dd) runs the installed prerm with 'upgrade <new>'
        # before the new preinst and aborts the upgrade if it fails; removal passes 'remove'.
        import os,shlex,subprocess
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from package_hooks import scripts
        trace=self.root/'guard-trace';service=self.root/'service'
        guard=self.root/'guard';guard.write_text('#!/bin/sh\ncat >/dev/null\nprintf "%s\\n" "$2" >> '+shlex.quote(str(trace))+'\nexit 0\n')
        service.write_text('#!/bin/sh\nexit 0\n')
        body=scripts()['prerm'].replace('/usr/bin/python3','sh '+shlex.quote(str(guard))).replace('/etc/init.d/homensai-vpn','sh '+shlex.quote(str(service)))
        for argument,expected in ((['upgrade','0.9.1-alpha61-1'],'upgrade'),(['remove'],'check'),([],'check'),(['upgradex'],'check')):
            subprocess.run(['sh','-s','--']+argument,input=body,text=True,check=True,env=dict(os.environ,IPKG_INSTROOT=''),timeout=5)
            with self.subTest(argument=argument):self.assertEqual(trace.read_text().splitlines()[-1],expected)

    def test_upgrade_action_accepts_the_incident_without_any_write(self):
        before=self.files();real=lifecycle.snapshot
        with patch.object(lifecycle,'control_lock',nullcontext),patch.object(lifecycle.subprocess,'run') as run,\
                patch.object(lifecycle,'snapshot',side_effect=lambda upgrade=False:real(self.root,upgrade=upgrade)):
            lifecycle.main('upgrade')
        run.assert_not_called();self.assertEqual(self.files(),before)
        self.process(2392,APPLY)
        with patch.object(lifecycle,'control_lock',nullcontext),patch.object(lifecycle.subprocess,'run') as run,\
                patch.object(lifecycle,'snapshot',side_effect=lambda upgrade=False:real(self.root,upgrade=upgrade)),\
                self.assertRaises(SystemExit):
            lifecycle.main('upgrade')
        run.assert_not_called()


if __name__=='__main__':unittest.main()
