import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess

path=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn/system_readiness.py'
spec=importlib.util.spec_from_file_location('system_readiness',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ReadinessTests(unittest.TestCase):
    def test_board_allowlist_and_no_permission(self):
        reply=subprocess.CompletedProcess([],0,b'{"model":"x86","board_name":"generic","serial":"private","release":{"version":"21.02"},"hostname":"private"}')
        with patch.object(module.subprocess,'run',return_value=reply):s=module.snapshot(100)
        self.assertEqual(s['board'],{'model':'x86','board_name':'generic','firmware':'unknown','openwrt':'21.02'})
        self.assertEqual(s['native_permission'],'not_assessed');self.assertNotIn('private',str(s))
    def test_unavailable_board_is_unknown(self):
        with patch.object(module.subprocess,'run',side_effect=OSError):s=module.snapshot(100)
        self.assertEqual(s['board']['model'],'unknown');self.assertEqual(s['native_permission'],'not_assessed')
    def test_malformed_board_bounded(self):
        for value in [b'null',b'[]',b'x'*32769,b'{"release":null}']:
            with patch.object(module.subprocess,'run',return_value=subprocess.CompletedProcess([],0,value)):
                self.assertEqual(module.snapshot(100)['native_permission'],'not_assessed')

class PresetTests(unittest.TestCase):
    def test_presets_match_backend_bounds_and_do_not_enable_auto(self):
        import json,sys
        sys.path.insert(0,str(path.parent))
        from recovery_settings import payload,DEFAULTS
        presets=json.loads((path.parent/'recovery_presets.json').read_text())
        self.assertEqual(set(presets),{'stability','fast_recovery','hold_reserve'})
        for draft in presets.values():
            self.assertEqual(set(draft),set(DEFAULTS));saved=payload(draft)
            self.assertFalse(any('native' in key for key in saved['main']))
        self.assertEqual(presets['hold_reserve']['return_policy'],'hold_reserve')

class CachedReadinessTests(unittest.TestCase):
    def test_status_rpc_uses_daemon_snapshot(self):
        source=(path.parent/'agent.py').read_text(encoding='utf-8')
        rpc=source.split("elif method in ('status', 'events'):",1)[1]
        self.assertNotIn('readiness_snapshot()',rpc)
        self.assertIn("status['system_readiness']=readiness_snapshot()",source)
