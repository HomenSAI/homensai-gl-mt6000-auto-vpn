from contextlib import nullcontext
from pathlib import Path
import json
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import monitor_control as monitor

class MonitorTests(unittest.TestCase):
    def run_change(self,args,settings=None,status=None,intent=None,transaction=None,result=None):
        def read(path,default):return intent or {} if path.name=='auto-control.json' else status or {}
        with patch.object(monitor,'control_lock',return_value=nullcontext()),patch.object(monitor,'inventory',return_value={'settings':settings or {}}),patch.object(monitor,'read_json',side_effect=read),patch.object(monitor,'journal_read',return_value=transaction or {}),patch.object(monitor.subprocess,'run',side_effect=result or [types.SimpleNamespace(returncode=0,stdout=b'OK'),types.SimpleNamespace(returncode=0)]) as run:
            answer=monitor.change(args);return answer,run.call_args_list

    def test_fresh_start_only_own_service_and_config(self):
        answer,calls=self.run_change({'enabled':True})
        self.assertTrue(answer['accepted']);self.assertFalse(answer['auto_started']);self.assertFalse(answer['running_confirmed'])
        payload=json.loads(calls[0].kwargs['input']);self.assertEqual(payload,{'main':{'enabled':'1'},'servers':[]})
        self.assertEqual(calls[1].args[0],['/etc/init.d/homensai-vpn','start'])

    def test_stop_only_when_auto_is_safe(self):
        answer,calls=self.run_change({'enabled':False});self.assertTrue(answer['accepted']);self.assertEqual(calls[1].args[0][-1],'stop')
        for context in ({'settings':{'native_enabled':True}},{'status':{'state':'WAIT-CLIENT'}},{'intent':{'mode':'on'}},{'transaction':{'phase':'RESTORING'}},{'transaction':{'phase':'UNKNOWN'}},{'status':{'guard':'closed'}},{'status':{'state':'STOPPED-ON-RESERVE'}}):
            answer,calls=self.run_change({'enabled':False},**context);self.assertFalse(answer['accepted']);self.assertEqual(calls,[])

    def test_invalid_fields_never_write(self):
        for args in ({},{'enabled':'true'},{'enabled':True,'native_enabled':True}):
            answer,calls=self.run_change(args);self.assertFalse(answer['accepted']);self.assertEqual(calls,[])

    def test_failed_writer_never_starts_service(self):
        answer,calls=self.run_change({'enabled':True},result=[types.SimpleNamespace(returncode=1,stdout=b'')]);self.assertFalse(answer['accepted']);self.assertEqual(len(calls),1)

    def test_corrupt_journal_cannot_stop_recovery_service(self):
        with patch.object(monitor,'control_lock',return_value=nullcontext()),patch.object(monitor,'inventory',return_value={'settings':{}}),patch.object(monitor,'read_json',return_value={}),patch.object(monitor,'journal_read',side_effect=monitor.Refused('JOURNAL-INTEGRITY-FAILED')),patch.object(monitor.subprocess,'run') as run:
            result=monitor.change({'enabled':False})
        self.assertEqual(result['code'],'MONITOR-JOURNAL-UNVERIFIED');run.assert_not_called()
