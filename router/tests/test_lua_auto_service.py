"""Plan item 1 wiring: option lua_auto selects the Lua supervisor for the procd `native` instance (default off,
the Python command unchanged); the Lua and the Python supervisor exclude each other through native.lock; the
temporary probe bridge (lua_bridge.py) accepts only its own RAM request files and never writes."""
import fcntl
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
LIB=ROOT/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import lua_bridge
import native_switch as n

LUA=shutil.which('lua5.1')
CONDITION='[ -x /usr/bin/lua ] && [ -f /usr/lib/homensai-vpn/lua/auto.lua ] && [ -f /usr/lib/homensai-vpn/lua/backend.lua ]'
STUBS='''
chmod() { :; }
config_load() { CONFIG_main_monitor_only=0; }
config_get_bool() { eval "$1=1"; }
config_get() { if [ "$3" = lua_auto ]; then if [ "$QA_LUA_AUTO" = unset ]; then eval "$1=\\${4}"; else eval "$1=\\${QA_LUA_AUTO}"; fi; else eval "$1=\\${4}"; fi; }
procd_open_instance() { printf 'OPEN %s\\n' "$1"; }
procd_set_param() { printf 'PARAM %s\\n' "$*"; }
procd_close_instance() { printf 'CLOSE\\n'; }
ubus() { :; }
jsonfilter() { cat >/dev/null; printf 'glinet,mt3000-snand\\n'; }
start_service
'''


class InitScript(unittest.TestCase):
    def run_start(self,lua_auto,installed=True):
        script=(ROOT/'files/etc/init.d/homensai-vpn').read_text()
        self.assertIn(CONDITION,script)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            if installed:
                for name in ('lua','auto.lua','backend.lua'):(folder/name).write_text('x')
                (folder/'lua').chmod(0o755)
                if not os.access(str(folder/'lua'),os.X_OK):
                    # The offline CI sandbox mounts its tmpfs noexec: `[ -x ]` can never pass there.
                    self.skipTest('temporary directory is mounted noexec')
            body=script.replace(CONDITION,'[ -x %s/lua ] && [ -f %s/auto.lua ] && [ -f %s/backend.lua ]'%(folder,folder,folder))
            body=body.split('\n',1)[1]  # drop the rc.common shebang
            result=subprocess.run(['sh','-c',body+STUBS],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,QA_LUA_AUTO=lua_auto),timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout.decode()

    def test_default_and_off_keep_the_python_supervisor(self):
        for value in ('unset','0','yes',''):
            with self.subTest(value=value):
                out=self.run_start(value)
                self.assertIn('PARAM command /usr/bin/python3 /usr/lib/homensai-vpn/native_switch.py daemon',out)
                self.assertNotIn('auto.lua',out)
                self.assertIn('PARAM command /usr/bin/python3 /usr/lib/homensai-vpn/agent.py daemon',out,'the monitor is untouched')

    def test_lua_auto_runs_the_lua_supervisor_in_the_same_native_instance(self):
        out=self.run_start('1')
        native=out[out.index('OPEN native'):]
        self.assertIn('PARAM command /usr/bin/lua /usr/lib/homensai-vpn/lua/auto.lua daemon',native)
        self.assertIn("TZ=CET-1CEST,M3.5.0,M10.5.0/3",native)
        self.assertNotIn('native_switch.py',native)
        self.assertIn('PARAM term_timeout 300',native,'same stop budget as Python')

    def test_lua_auto_without_the_lua_files_falls_back_to_python(self):
        out=self.run_start('1',installed=False)
        self.assertIn('native_switch.py daemon',out);self.assertNotIn('auto.lua',out)


CORE_CONDITION=('[ -x /usr/bin/lua ] && [ -f /usr/lib/homensai-vpn/lua/hv_core.lua ] && [ -f /usr/lib/homensai-vpn/lua/auto.lua ]'
                ' && [ -f /usr/lib/homensai-vpn/lua/backend.lua ]')
CORE_STUBS='''
chmod() { :; }
config_load() {
    CONFIG_main_monitor_only=$QA_MONITOR_ONLY
    [ "$QA_LUA_MONITOR" = unset ] || CONFIG_main_lua_monitor=$QA_LUA_MONITOR
    [ "$QA_CORE" = unset ] || CONFIG_main_lua_core_process=$QA_CORE
}
config_get_bool() { eval "$1=1"; }
config_get() { if [ "$3" = lua_auto ]; then eval "$1=\\${QA_LUA_AUTO}"; else eval "$1=\\${4}"; fi; }
procd_open_instance() { printf 'OPEN %s\\n' "$1"; }
procd_set_param() { printf 'PARAM %s\\n' "$*"; }
procd_close_instance() { printf 'CLOSE\\n'; }
ubus() { :; }
jsonfilter() { cat >/dev/null; printf 'glinet,mt3000-snand\\n'; }
start_service
'''


class HvCoreInit(unittest.TestCase):
    """Lua plan item 8: option lua_core_process '1' puts the Lua monitor and the Lua Auto supervisor in one
    process (hv_core.lua daemon, instance `monitor`); `native` stands by. Default and every other case: unchanged."""
    def run_start(self,core='1',lua_monitor='1',lua_auto='1',monitor_only='0',installed=True):
        script=(ROOT/'files/etc/init.d/homensai-vpn').read_text()
        self.assertIn(CORE_CONDITION,script)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            if installed:
                for name in ('hv_core.lua','auto.lua','backend.lua'):(folder/name).write_text('x')
            body=script.replace(CORE_CONDITION,'[ -x /bin/sh ] && [ -f %s/hv_core.lua ] && [ -f %s/auto.lua ] && [ -f %s/backend.lua ]'%(folder,folder,folder))
            body=body.replace(CONDITION,'[ -x /bin/sh ] && [ -f %s/auto.lua ] && [ -f %s/backend.lua ]'%(folder,folder))
            body=body.replace('[ -f /usr/lib/homensai-vpn/lua/monitor.lua ]','[ -f /bin/sh ]')
            body=body.replace('rm -f /var/run/homensai-vpn/lua-monitor.ready',':')
            body=body.split('\n',1)[1]
            env=dict(os.environ,QA_CORE=core,QA_LUA_MONITOR=lua_monitor,QA_LUA_AUTO=lua_auto,QA_MONITOR_ONLY=monitor_only)
            result=subprocess.run(['sh','-c',body+CORE_STUBS],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        out=result.stdout.decode()
        instances={}
        for block in out.split('OPEN ')[1:]:
            name,rest=block.split('\n',1)
            instances[name]=[line[6:] for line in rest.splitlines() if line.startswith('PARAM ')]
        return instances

    def test_one_runs_hv_core_in_the_monitor_instance_and_a_standby_in_native(self):
        instances=self.run_start()
        self.assertIn('command /usr/bin/lua /usr/lib/homensai-vpn/lua/hv_core.lua daemon',instances['monitor'])
        self.assertIn('term_timeout 300',instances['monitor'],'hv-core ends the running Auto pass before it exits')
        self.assertIn('respawn 3600 5 0',instances['monitor'])
        self.assertIn('file /etc/config/homensai_vpn',instances['monitor'])
        self.assertTrue(any(p.startswith('env TZ=') and 'LUA_PATH=' in p for p in instances['monitor']))
        self.assertIn('command /usr/bin/lua /usr/lib/homensai-vpn/lua/hv_core.lua standby',instances['native'])
        self.assertIn('respawn 3600 5 0',instances['native']);self.assertIn('term_timeout 300',instances['native'])
        self.assertEqual(sorted(instances),['monitor','native'],'the same two procd instances')

    def test_default_and_other_values_keep_two_processes(self):
        for core in ('unset','0','','yes','2'):
            with self.subTest(core=core):
                instances=self.run_start(core=core)
                self.assertIn('command /usr/bin/lua /usr/lib/homensai-vpn/lua/monitor.lua daemon',instances['monitor'])
                self.assertIn('term_timeout 15',instances['monitor'])
                self.assertIn('command /usr/bin/lua /usr/lib/homensai-vpn/lua/auto.lua daemon',instances['native'])

    def test_hv_core_needs_both_lua_halves_installed_and_the_supervisor(self):
        cases=(('python monitor',dict(lua_monitor='0'),'/usr/lib/homensai-vpn/agent.py daemon','/usr/lib/homensai-vpn/lua/auto.lua daemon'),
               ('python auto',dict(lua_auto='0'),'/usr/lib/homensai-vpn/lua/monitor.lua daemon','native_switch.py daemon'),
               ('not installed',dict(installed=False),'/usr/lib/homensai-vpn/lua/monitor.lua daemon','native_switch.py daemon'))
        for label,kwargs,monitor,native in cases:
            with self.subTest(label):
                instances=self.run_start(**kwargs)
                self.assertTrue(any(p.startswith('command') and p.endswith(monitor) for p in instances['monitor']),instances)
                self.assertTrue(any(p.startswith('command') and p.endswith(native) for p in instances['native']),instances)
                self.assertNotIn('hv_core',repr(instances))
        instances=self.run_start(monitor_only='1')
        self.assertEqual(sorted(instances),['monitor'],'monitor-only: no supervisor, no hv-core')
        self.assertIn('command /usr/bin/lua /usr/lib/homensai-vpn/lua/monitor.lua daemon',instances['monitor'])

    def test_stop_saves_first_and_ends_a_fallback(self):
        text=(ROOT/'files/etc/init.d/homensai-vpn').read_text()
        stop=text[text.index('stop_service()'):]
        self.assertLess(stop.index('call homensai-vpn-lua shutdown'),stop.index('hv-core-fallback.json'))
        for name in ('hv-core-fallback.json','hv-core.json','hv-core-watchdog.json'):self.assertIn(name,stop)


class Bridge(unittest.TestCase):
    def call(self,*argv):
        buffer=io.StringIO()
        with redirect_stdout(buffer):code=lua_bridge.main(['lua_bridge.py']+list(argv))
        return code,json.loads(buffer.getvalue().strip().splitlines()[-1])

    def test_only_own_ram_request_files(self):
        for argv in (('probe','/etc/passwd'),('probe','/var/run/homensai-vpn/../x.json'),('shell','/var/run/homensai-vpn/.bridge-1.json'),('probe',)):
            with self.subTest(argv=argv):self.assertEqual(self.call(*argv),(2,{'code':'BRIDGE-REQUEST-INVALID'}))

    def test_probe_and_trace_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            path='/var/run/homensai-vpn/.bridge-0a1b-1.json'
            real_open=open
            def fake_open(name,*args,**kwargs):
                return real_open(Path(folder)/'r.json',*args,**kwargs) if name==path else real_open(name,*args,**kwargs)
            (Path(folder)/'r.json').write_text(json.dumps({'id':'wireguard:peer_1','interface':'wgclient1'}))
            with patch('builtins.open',fake_open),patch('agent.probe',return_value={'id':'wireguard:peer_1','code':None,'dns_ok':True,'https_success':2}):
                self.assertEqual(self.call('probe',path),(0,{'code':None,'dns_ok':True,'https_success':2,'id':'wireguard:peer_1'}))
            with patch('builtins.open',fake_open),patch.object(n,'trace',side_effect=n.Refused('EXIT-TRACE-FAILED')):
                self.assertEqual(self.call('trace',path),(0,{'code':'EXIT-TRACE-FAILED'}))
            with patch('builtins.open',fake_open),patch.object(n,'trace',return_value='198.51.100.7'):
                self.assertEqual(self.call('trace',path),(0,{'exit':'198.51.100.7'}))


@unittest.skipUnless(LUA and shutil.which('flock'),'Lua 5.1 and flock(1) required')
class NativeLock(unittest.TestCase):
    def hold(self,folder):
        code=("package.path='%s/lua/?.lua;'..package.path;require('canon').configure({runtime='%s'});"
              "local A=require('auto');local f,fd=A.hold_native_lock('%s');print(fd or 'busy')")%(LIB,folder,folder)
        return subprocess.run([LUA,'-e',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20).stdout.decode().strip()

    def test_python_and_lua_supervisors_exclude_each_other(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(Path(folder)/'native.lock','a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertEqual(self.hold(folder),'busy','Python holds it: the Lua supervisor must not start')
            self.assertRegex(self.hold(folder),r'^\d+$','free: Lua takes it')


if __name__=='__main__':
    unittest.main()
