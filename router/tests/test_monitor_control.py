from contextlib import nullcontext
from pathlib import Path
import json
import re
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import monitor_control as monitor


class MonitorTests(unittest.TestCase):
    """Owner main rule 07.11.2026: the monitor ALWAYS runs. A stop is refused with MONITOR-ALWAYS-ON whatever Auto does;
    only the start (recovery of an error stop) is accepted."""
    def run_change(self,args,result=None):
        with patch.object(monitor,'control_lock',return_value=nullcontext()),patch('rpc_throttle.allow',return_value=True),patch.object(monitor.subprocess,'run',side_effect=result or [types.SimpleNamespace(returncode=0,stdout=b'OK'),types.SimpleNamespace(returncode=0)]) as run:
            answer=monitor.change(args);return answer,run.call_args_list

    def test_fresh_start_only_own_service_and_config(self):
        answer,calls=self.run_change({'enabled':True})
        self.assertTrue(answer['accepted']);self.assertFalse(answer['auto_started']);self.assertFalse(answer['running_confirmed'])
        self.assertEqual(answer['code'],'MONITOR-START-REQUESTED')
        payload=json.loads(calls[0].kwargs['input']);self.assertEqual(payload,{'main':{'enabled':'1'},'servers':[]})
        self.assertEqual(calls[1].args[0],['/etc/init.d/homensai-vpn','start'])

    def test_stop_is_refused_with_auto_off(self):
        answer,calls=self.run_change({'enabled':False})
        self.assertEqual((answer['accepted'],answer['code']),(False,'MONITOR-ALWAYS-ON'));self.assertEqual(calls,[])
        self.assertFalse(answer['auto_started'])

    def test_stop_is_refused_with_auto_on_in_every_state(self):
        """Pair supervisor running, not running or unreadable: the same refusal; nothing is read, written or stopped
        (the module no longer even looks at the journal for a stop)."""
        import configuration_guard
        for pair_state in (False,True):
            with patch.object(configuration_guard,'pair_active',return_value=pair_state):
                answer,calls=self.run_change({'enabled':False})
            self.assertEqual((answer['accepted'],answer['code']),(False,'MONITOR-ALWAYS-ON'));self.assertEqual(calls,[])
        with patch.object(configuration_guard,'pair_active',side_effect=ValueError('PAIR-STATE-UNVERIFIED')):
            answer,calls=self.run_change({'enabled':False})
        self.assertEqual(answer['code'],'MONITOR-ALWAYS-ON');self.assertEqual(calls,[])

    def test_stop_refusal_does_not_take_the_lock_or_the_rate_limit(self):
        with patch.object(monitor,'control_lock',side_effect=AssertionError('lock')),patch('rpc_throttle.allow',side_effect=AssertionError('rate')),patch.object(monitor.subprocess,'run',side_effect=AssertionError('run')):
            for _ in range(10):self.assertEqual(monitor.change({'enabled':False})['code'],'MONITOR-ALWAYS-ON')

    def test_start_is_allowed_with_auto_running_or_held(self):
        """Starting recovers an error stop; it is never blocked by Auto, a pair session or a retained reserve."""
        import configuration_guard
        for pair_state in (False,True):
            with patch.object(configuration_guard,'pair_active',return_value=pair_state):
                answer,calls=self.run_change({'enabled':True})
            self.assertTrue(answer['accepted']);self.assertEqual(calls[-1].args[0][-1],'start')

    def test_start_refused_while_a_package_operation_holds_the_maintenance_marker(self):
        """IR-01: prerm stopped the service and opkg unpacks; a start would run a half-unpacked tree. Refused under the
        control lock, nothing written, no service command (postinst starts the service when the operation ends)."""
        import auto_control
        with patch.object(auto_control,'maintenance_blocker',return_value='MAINTENANCE-IN-PROGRESS'):
            answer,calls=self.run_change({'enabled':True})
        self.assertEqual(answer,{'accepted':False,'code':'MAINTENANCE-IN-PROGRESS','configured':False,'auto_started':False})
        self.assertEqual(calls,[])
        with patch.object(auto_control,'maintenance_blocker',return_value=None):
            answer,calls=self.run_change({'enabled':True})
        self.assertTrue(answer['accepted']);self.assertEqual(calls[-1].args[0],['/etc/init.d/homensai-vpn','start'])

    def test_start_reads_the_real_marker(self):
        """The same with a real active marker in PERSIST (maintenance.blocker classification, this boot)."""
        import tempfile,auto_control,maintenance
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(auto_control,'PERSIST',Path(directory)),patch.object(maintenance,'current',return_value={'state':'active'}):
                answer,calls=self.run_change({'enabled':True})
        self.assertEqual(answer['code'],'MAINTENANCE-IN-PROGRESS');self.assertEqual(calls,[])

    def test_module_has_no_stop_command(self):
        source=Path(monitor.__file__).read_text(encoding='utf-8')
        self.assertNotIn("'stop'",source);self.assertNotIn('MONITOR-STOP-REQUESTED',source);self.assertNotIn('MONITOR-STOP-AUTO-FIRST',source)

    def test_the_page_never_sends_a_monitor_stop(self):
        """Every monitor_control call the shipped page makes is a start (true); no off control exists."""
        root=Path(__file__).resolve().parents[1]
        app=json.loads((root.parent/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
        page=(root/'files/www/luci-static/resources/view/homensai-vpn'/(app['ui_module']+'.js')).read_text(encoding='utf-8')
        sent=re.findall(r"monitor_control['\"][^)]*\)\)?\(([^)]*)\)",page)
        self.assertTrue(sent);self.assertEqual(set(sent),{'true'},sent)
        for text in ('Stop monitor','Остановить мониторинг'):self.assertNotIn(text,page)

    def test_invalid_fields_never_write(self):
        for args in ({},{'enabled':'true'},{'enabled':None},{'enabled':1},{'enabled':True,'native_enabled':True}):
            answer,calls=self.run_change(args);self.assertFalse(answer['accepted']);self.assertEqual(answer['code'],'MONITOR-INVALID');self.assertEqual(calls,[])

    def test_pending_delta_refusal_never_starts_service(self):
        for code in ('SETUP-PENDING-DELTA','SETUP-DELTA-UNVERIFIED'):
            answer,calls=self.run_change({'enabled':True},result=[types.SimpleNamespace(returncode=1,stdout=code.encode())])
            self.assertFalse(answer['accepted']);self.assertEqual(answer['code'],code)
            self.assertEqual(len(calls),1)

    def test_failed_writer_never_starts_service(self):
        answer,calls=self.run_change({'enabled':True},result=[types.SimpleNamespace(returncode=1,stdout=b'')]);self.assertFalse(answer['accepted']);self.assertEqual(len(calls),1)


if __name__=='__main__':
    unittest.main()
