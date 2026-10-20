"""Explicit internal monitor-only mode; no platform or recovery bypass."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'files/usr/lib/homensai-vpn'))
import native_switch as native


@unittest.skipUnless(os.name=='posix' and shutil.which('sh'),'POSIX procd harness required')
class MonitorDeploymentTests(unittest.TestCase):
    def instances(self,mode=None,enabled='1',listed=False,board='glinet,gl-mt6000'):
        script=(ROOT/'files/etc/init.d/homensai-vpn').read_text()
        stubs='''
chmod() { [ "$*" = "0600 /etc/config/homensai_vpn" ]; }
config_load() { [ "$1" = homensai_vpn ] || return 1; unset CONFIG_main_monitor_only CONFIG_main_monitor_only_LENGTH; if [ "$QA_ABSENT" != 1 ]; then CONFIG_main_monitor_only=$QA_MODE; fi; if [ "$QA_LIST" = 1 ]; then CONFIG_main_monitor_only_LENGTH=1; fi; }
config_get_bool() { eval "$1=\\${QA_ENABLED}"; }
config_get() { if [ "$QA_ABSENT" = 1 ]; then eval "$1=\\${4}"; else eval "$1=\\${QA_MODE}"; fi; }
procd_open_instance() { printf 'OPEN %s\\n' "$1"; }
procd_set_param() { printf 'PARAM %s\\n' "$*"; }
procd_close_instance() { printf 'CLOSE\\n'; }
ubus() { printf 'BOARD\\n'; }
jsonfilter() { cat >/dev/null; printf '%s\\n' "$QA_BOARD"; }
start_service
'''
        result=subprocess.run(['sh','-s'],input=script+'\n'+stubs,text=True,capture_output=True,timeout=5,
            env=dict(os.environ,QA_ENABLED=enabled,QA_MODE='' if mode is None else mode,QA_ABSENT='1' if mode is None else '0',QA_LIST='1' if listed else '0',QA_BOARD=board))
        self.assertEqual(result.returncode,0,result.stderr)
        return [line[5:] for line in result.stdout.splitlines() if line.startswith('OPEN ')],result.stderr

    def test_default_and_zero_preserve_existing_monitor_and_native_instances(self):
        for mode in (None,'0'):
            instances,diagnostic=self.instances(mode)
            self.assertEqual(instances,['monitor','native']);self.assertEqual(diagnostic,'')

    def test_exact_one_launches_monitor_without_native_instance(self):
        instances,diagnostic=self.instances('1')
        self.assertEqual(instances,['monitor']);self.assertEqual(diagnostic,'')

    def test_invalid_mode_fails_closed_for_native_and_has_explicit_diagnostic(self):
        for mode in ('','2','true','yes','1 0',' 1','01'):
            with self.subTest(mode=mode):
                instances,diagnostic=self.instances(mode)
                self.assertEqual(instances,['monitor']);self.assertIn('MONITOR-ONLY-INVALID',diagnostic)

    def test_disabled_service_does_not_launch_either_instance(self):
        self.assertEqual(self.instances('1',enabled='0')[0],[])

    def test_list_mode_cannot_masquerade_as_scalar_zero_or_one(self):
        for mode in ('0','1'):
            instances,diagnostic=self.instances(mode,listed=True)
            self.assertEqual(instances,['monitor']);self.assertIn('MONITOR-ONLY-INVALID',diagnostic)

    def test_sdk_wrapper_cannot_start_instances_after_failed_postinst_with_default_mode(self):
        for board in ('glinet,mt3000-snand','unknown',''):
            for mode in (None,'0'):
                instances,diagnostic=self.instances(mode,board=board)
                self.assertEqual(instances,[]);self.assertIn('MONITOR-ONLY-DEPLOYMENT',diagnostic)
            self.assertEqual(self.instances('1',board=board)[0],['monitor'])

    def test_native_diagnostic_blocks_explicit_or_invalid_mode_without_relaxing_model_pin(self):
        for mode,expected in ((None,None),('0',None),('1','MONITOR-ONLY-DEPLOYMENT'),('', 'MONITOR-ONLY-INVALID'),
                              ('yes','MONITOR-ONLY-INVALID'),(False,'MONITOR-ONLY-INVALID')):
            settings={'terms_version':native.TERMS_VERSION}
            if mode is not None:settings['monitor_only']=mode
            data={'settings':settings,'lan':'br-lan','hnat_enable':'0'}
            def read(path,*args,**kwargs):return '{}' if path.name=='native-audit-hashes.json' else '4.11.0'
            router=native.Linux()
            with ExitStack() as stack:
                stack.enter_context(patch.object(router,'policy',return_value=data))
                stack.enter_context(patch.object(router,'acceleration',return_value={'loaded':[],'hnat_runtime':'disabled'}))
                stack.enter_context(patch.object(native,'command',return_value=json.dumps({'board_name':'glinet,mt3000-snand'}).encode()))
                stack.enter_context(patch.object(native,'inventory',return_value={'profiles':[],'servers':[]}))
                stack.enter_context(patch.object(native,'choose',side_effect=native.Refused('SYNTHETIC-NO-SELECTION')))
                stack.enter_context(patch.object(Path,'read_text',read))
                stack.enter_context(patch.object(Path,'glob',return_value=[]))
                stack.enter_context(patch.object(Path,'exists',return_value=False))
                blockers,selection=router.diagnostic()
            self.assertIn('UNSUPPORTED-BOARD',blockers)
            if expected:self.assertIn(expected,blockers)
            else:self.assertFalse(any(code.startswith('MONITOR-ONLY-') for code in blockers))
            self.assertIsNone(selection)

    @unittest.skipUnless(shutil.which('lua5.1'),'Lua 5.1 runtime absent')
    def test_inventory_preserves_missing_empty_and_exact_mode_distinctions(self):
        fixture=(ROOT/'tests/test_inventory.lua').read_text()
        for mode,expected in ((None,'standard'),('0','standard'),('1','monitor-only'),('','invalid'),('yes','invalid')):
            option='' if mode is None else ",monitor_only='"+mode+"'"
            source=fixture.replace("['.type']='main',enabled='1'","['.type']='main',enabled='1'"+option)
            result=subprocess.run([shutil.which('lua5.1'),'-',str(ROOT/'files/usr/lib/homensai-vpn/inventory.lua')],
                                  input=source.encode(),capture_output=True,timeout=5,check=True)
            settings=json.loads(result.stdout)['settings']
            self.assertEqual(settings['deployment_mode'],expected)
            self.assertIs(settings['monitor_only'],mode=='1')

    @unittest.skipUnless(shutil.which('lua5.1'),'Lua 5.1 runtime absent')
    def test_private_policy_exports_mode_and_excludes_unrelated_secret(self):
        source="""package.preload['uci']=function()
return {cursor=function()return {
foreach=function()end,
get=function()return nil end,
get_all=function()return {monitor_only='1',telegram_token='PRIVATE_SENTINEL'}end
}end}end
dofile(arg[1])
"""
        result=subprocess.run([shutil.which('lua5.1'),'-',str(ROOT/'files/usr/lib/homensai-vpn/native_policy.lua')],
                              input=source.encode(),capture_output=True,timeout=5,check=True)
        self.assertEqual(json.loads(result.stdout)['settings']['monitor_only'],'1')
        self.assertNotIn(b'PRIVATE_SENTINEL',result.stdout)

    def postinst(self,board,mode,guard_failure=False):
        sys.path.insert(0,str(ROOT))
        from package_hooks import scripts
        body=scripts()['postinst'].replace('/usr/bin/python3','python_guard').replace('/etc/init.d/homensai-vpn','service_test').replace('/etc/init.d/rpcd','rpcd_test')
        functions=r'''
mkdir() { printf 'mkdir\n' >> "$QA_CALLS"; }
chmod() { printf 'chmod\n' >> "$QA_CALLS"; }
python_guard() { if [ "$1" = - ]; then cat >/dev/null; printf 'lifecycle\n' >> "$QA_CALLS"; [ "$QA_GUARD_FAIL" != 1 ]; else printf 'python-cache\n' >> "$QA_CALLS"; fi; }
ubus() { printf 'board\n' >> "$QA_CALLS"; printf 'BOARD\n'; }
jsonfilter() { cat >/dev/null; printf '%s\n' "$QA_BOARD"; }
uci() { printf 'mode\n' >> "$QA_CALLS"; [ "$QA_MODE" != MISSING ] || return 1; printf '%s\n' "$QA_MODE"; }
service_test() { printf 'service:%s\n' "$1" >> "$QA_CALLS"; }
rpcd_test() { printf 'rpcd:%s\n' "$1" >> "$QA_CALLS"; }
'''
        with tempfile.TemporaryDirectory() as directory:
            trace=Path(directory)/'trace'
            result=subprocess.run(['sh','-s'],input=functions+'\n'+body,text=True,capture_output=True,timeout=5,
                env=dict(os.environ,IPKG_INSTROOT='',QA_CALLS=str(trace),QA_BOARD=board,QA_MODE=mode,QA_GUARD_FAIL='1' if guard_failure else '0'))
            return result,trace.read_text().splitlines()

    def test_postinst_other_board_requires_marker_before_any_runtime_start(self):
        for board in ('glinet,mt3000-snand','unknown',''):
            for mode in ('MISSING','0','','yes'):
                result,trace=self.postinst(board,mode)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('MONITOR-ONLY-DEPLOYMENT',result.stderr)
                self.assertNotIn('python-cache',trace)
                self.assertFalse(any(line.startswith(('service:','rpcd:')) for line in trace))

    def test_postinst_supported_default_or_explicit_monitor_only_starts_after_lifecycle_guard(self):
        for board,mode in (('glinet,gl-mt6000','MISSING'),('glinet,mt3000-snand','1')):
            result,trace=self.postinst(board,mode)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertLess(trace.index('lifecycle'),trace.index('board'))
            self.assertIn('service:enable',trace);self.assertIn('service:restart',trace)
            self.assertIn('rpcd:reload',trace)

    def test_lifecycle_refusal_precedes_even_model_mode_read(self):
        result,trace=self.postinst('glinet,mt3000-snand','1',guard_failure=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('board',trace);self.assertNotIn('mode',trace)
        self.assertFalse(any(line.startswith('service:') for line in trace))


if __name__=='__main__':unittest.main()
