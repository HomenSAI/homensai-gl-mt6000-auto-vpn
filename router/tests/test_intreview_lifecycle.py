"""Integration review 07.11.2026 (private/integration-review-20261107/FINDINGS.md), lifecycle_guard findings.

IR-04: opkg runs the OLD prerm 'upgrade' and then the NEW preinst/postinst ('prepare'); the prepare re-marked the package
operation as 'install', so status.maintenance.action and a MAINTENANCE-INTERRUPTED record named an interrupted upgrade
an install. A prepare that finds this boot's live upgrade mark now keeps action=upgrade.
Fixture: test_lifecycle_guard.MaintenanceMarkerTests (temporary root, proc files, the real main()).
"""
import json
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import lifecycle_guard as lifecycle  # noqa: E402
import maintenance  # noqa: E402
import test_lifecycle_guard as base  # noqa: E402

BOOT=base.BOOT

OTHER_BOOT='11111111-2222-4333-8444-555555555555'


class Fixture(base.MaintenanceMarkerTests):
    pass


for _name in [n for n in dir(base.MaintenanceMarkerTests) if n.startswith('test_')]:
    setattr(Fixture,_name,None)  # only the fixture is reused here; the original tests run in their own module
del _name


class UpgradeActionIsKept(Fixture):
    def write_mark(self,**row):
        self.marker.parent.mkdir(parents=True,exist_ok=True)
        self.marker.write_text(json.dumps(row))

    def upgrade_sequence(self):
        """old prerm (first guard), the stop guard, new preinst, new postinst: the action each step leaves."""
        seen=[]
        for action in ('upgrade','upgrade-stopped','prepare','prepare'):
            if action.endswith('-stopped'):
                from unittest.mock import patch
                with patch.object(lifecycle,'wait_service_exit'):code,_=self.run_guard(action)
            else:code,_=self.run_guard(action)
            self.assertEqual(code,0,action)
            seen.append(json.loads(self.marker.read_text())['action'])
        return seen

    def test_an_upgrade_stays_an_upgrade_through_preinst_and_postinst(self):
        self.assertEqual(self.upgrade_sequence(),['upgrade','upgrade','upgrade','upgrade'])
        view=maintenance.current(self.marker.parent,self.root/'proc',time.time())
        self.assertEqual((view['state'],view['action']),('active','upgrade'))

    def test_an_interrupted_upgrade_is_recorded_as_an_upgrade(self):
        self.upgrade_sequence()
        (self.root/'proc/sys/kernel/random/boot_id').write_text(OTHER_BOOT+'\n')  # power cut mid-upgrade
        record=maintenance.clear_stale(self.marker.parent,self.root/'proc',time.time())
        self.assertEqual((record['code'],record['reason'],record['action']),('MAINTENANCE-INTERRUPTED','reboot','upgrade'))

    def test_a_fresh_install_is_an_install(self):
        self.assertEqual(self.run_guard('prepare')[0],0)
        self.assertEqual(json.loads(self.marker.read_text())['action'],'install')

    def test_only_a_live_upgrade_mark_of_this_boot_counts(self):
        now=time.time()
        cases=(
            ('another boot',{'action':'upgrade','time':now,'boot_id':OTHER_BOOT,'uptime':300.0},'install'),
            ('older than the limit',{'action':'upgrade','time':now,'boot_id':BOOT,'uptime':0.0,'_proc_uptime':'901.5 1.0'},'install'),
            ('exactly at the limit',{'action':'upgrade','time':now,'boot_id':BOOT,'uptime':1.5,'_proc_uptime':'901.5 1.0'},'upgrade'),
            ('uptime ahead of this boot',{'action':'upgrade','time':now,'boot_id':BOOT,'uptime':400.0},'install'),
            ('a removal mark',{'action':'remove','time':now,'boot_id':BOOT,'uptime':300.0},'install'),
            ('live, same boot',{'action':'upgrade','time':now,'boot_id':BOOT,'uptime':300.0},'upgrade'),
            ('no boot id, recent wall clock',{'action':'upgrade','time':now-10},'upgrade'),
            ('no boot id, old wall clock',{'action':'upgrade','time':now-1000},'install'),
        )
        for name,row,want in cases:
            with self.subTest(name):
                row=dict(row);(self.root/'proc/uptime').write_text(row.pop('_proc_uptime','321.5 100.0')+'\n')
                self.write_mark(**row)
                self.assertEqual(self.run_guard('prepare')[0],0)
                self.assertEqual(json.loads(self.marker.read_text())['action'],want)

    def test_a_symlinked_or_damaged_mark_is_never_followed(self):
        target=self.root/'elsewhere.json'
        target.write_text(json.dumps({'action':'upgrade','time':time.time(),'boot_id':BOOT,'uptime':300.0}))
        self.marker.parent.mkdir(parents=True,exist_ok=True)
        self.marker.symlink_to(target)
        self.assertFalse(lifecycle.live_upgrade_mark(self.root,BOOT,321.5,time.time()))
        self.marker.unlink();self.marker.write_text('{"action":')
        self.assertFalse(lifecycle.live_upgrade_mark(self.root,BOOT,321.5,time.time()))


class KilledSupervisorIsRefused(Fixture):
    """IR-05 (F-17): an absent supervisor-shutdown.json passed the second guard, and the first guard removed the older
    one, so a supervisor SIGKILLed by procd after term_timeout (it writes nothing) passed with an unfinished recovery."""
    def setUp(self):
        super().setUp()
        self.record=self.runtime/'supervisor-shutdown.json'

    def stopped_guard(self,action='upgrade-stopped'):
        from unittest.mock import patch
        with patch.object(lifecycle,'wait_service_exit'),patch('sys.stderr') as err:
            code,_=self.run_guard(action)
        return code,''.join(call.args[0] for call in err.write.call_args_list)

    def kill(self,pid):
        entry=self.root/'proc'/str(pid)
        for child in entry.iterdir():child.unlink()
        entry.rmdir()

    def test_a_supervisor_killed_without_its_record_is_refused(self):
        for argv in (('/usr/bin/python3','/usr/lib/homensai-vpn/native_switch.py','daemon'),
                     ('/usr/bin/lua','/usr/lib/homensai-vpn/lua/auto.lua','daemon'),
                     ('/usr/bin/lua','/usr/lib/homensai-vpn/lua/hv_core.lua','daemon')):
            with self.subTest(argv[1]):
                self.proc(30,*argv)
                self.assertEqual(self.run_guard('upgrade')[0],0)
                row=json.loads(self.record.read_text())
                self.assertEqual((row['ok'],row['code'],row['expected']),(False,'LIFECYCLE-RECOVERY-UNFINISHED',True))
                self.kill(30)  # SIGKILL after term_timeout: no record of its own
                code,text=self.stopped_guard()
                self.assertEqual(code,1)
                self.assertIn('LIFECYCLE-RECOVERY-UNFINISHED',text)
                self.assertFalse(self.marker.exists(),'the refusal ends the package operation')

    def test_the_supervisors_own_ok_replaces_the_expected_record(self):
        import agent
        import native_switch
        from unittest.mock import patch
        self.proc(31,'/usr/bin/python3','/usr/lib/homensai-vpn/native_switch.py','daemon')
        self.assertEqual(self.run_guard('check')[0],0)
        self.assertIs(json.loads(self.record.read_text())['ok'],False)
        with patch.object(native_switch,'RUNTIME',self.runtime),patch.object(agent,'RUNTIME',self.runtime):
            native_switch.shutdown_record(True)  # the end of serve() after the shutdown recovery
        self.kill(31)
        self.assertEqual(self.stopped_guard('check-stopped')[0],0)

    def test_without_a_supervisor_nothing_is_expected(self):
        # monitor only (mode no-auto, monitor_only), the standby, an rpcd call, an apply child: no shutdown record comes
        self.proc(40,'/usr/bin/python3','/usr/lib/homensai-vpn/agent.py','daemon')
        self.proc(41,'/usr/bin/lua','/usr/lib/homensai-vpn/lua/monitor.lua','daemon')
        self.proc(42,'/usr/bin/lua','/usr/lib/homensai-vpn/lua/hv_core.lua','standby')
        self.proc(43,'/usr/bin/python3','/usr/lib/homensai-vpn/agent.py','call','status')
        self.proc(44,'/usr/bin/python3','/usr/lib/homensai-vpn/native_switch.py','apply','x')
        self.assertEqual(lifecycle.service_processes(self.root,supervisors=True),[])
        self.record.write_text('{"ok":false}')  # an older shutdown's record is forgotten as before
        self.assertEqual(self.run_guard('upgrade')[0],0)
        self.assertFalse(self.record.exists())
        for pid in (40,41,42,43,44):self.kill(pid)
        self.assertEqual(self.stopped_guard()[0],0)

    def test_an_unreadable_proc_expects_the_record(self):
        from unittest.mock import patch
        with patch.object(lifecycle,'service_processes',return_value=None):
            self.assertEqual(self.run_guard('upgrade')[0],0)
        self.assertIs(json.loads(self.record.read_text())['ok'],False)

    def test_a_planted_symlink_is_never_followed(self):
        self.proc(32,'/usr/bin/lua','/usr/lib/homensai-vpn/lua/auto.lua','daemon')
        victim=self.root/'victim';victim.write_text('keep')
        (self.runtime/'.supervisor-shutdown.json.new').symlink_to(victim)
        self.assertEqual(self.run_guard('upgrade')[0],0)
        self.assertEqual(victim.read_text(),'keep')
        self.assertIs(json.loads(self.record.read_text())['ok'],False)


if __name__=='__main__':unittest.main()
