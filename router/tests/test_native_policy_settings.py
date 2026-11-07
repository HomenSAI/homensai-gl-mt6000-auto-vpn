"""The supervisor decides with the owner's settings (independent review 04.11.2026, finding 2).

Auto's settings come from native_policy.lua: native_switch.Linux.policy() (Python supervisor) and backend.B.policy()
(Lua supervisor) run the same helper. Its key list had recovery_rescue_stable but not failure_model, so
channel_model.name() fell back to 'hmm': the owner's 'consecutive' or 'hmm-fast' was shown by the monitor and the page
(inventory.lua) but ignored by pair.tick / committed_recovery_decision / return_ready. Here the real helper runs under
Lua 5.1 with a fake UCI and its output goes through the deciders of the Python line; the Lua line reads the same output
in tests/lua/test_native_policy.lua. A numeric detector option (channel_model.NUMERIC, 2.1.0-alpha9) must reach the
supervisor the same way: the test checks every key of that table when it exists.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import channel_model  # noqa: E402
import native_switch  # noqa: E402
import recovery_settings  # noqa: E402
import server_pick  # noqa: E402

LUA=shutil.which('lua5.1')
HELPER=LIB/'native_policy.lua'


def lua_string(value):return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'


def runner(directory,main):
    """A Lua file that installs a fake `uci` (homensai_vpn.main = main) and runs the helper given as arg[1]."""
    fields=','.join('[%s]=%s'%(lua_string(k),lua_string(v)) for k,v in sorted(main.items()))
    text=("package.preload['uci']=function() return {cursor=function() return {\n"
          " foreach=function() end,\n"
          " get_all=function(_,package,section) if package=='homensai_vpn' and section=='main' then return {%s} end end,\n"
          " get=function() return nil end} end} end\n"
          "local helper=arg[1];arg={[0]=helper};dofile(helper)\n")%fields
    path=Path(directory)/'run_policy.lua';path.write_text(text,encoding='utf-8')
    return path


def helper_settings(main):
    with tempfile.TemporaryDirectory() as directory:
        out=subprocess.run([LUA,str(runner(directory,main)),str(HELPER)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=True)
    return json.loads(out.stdout.decode().strip().splitlines()[-1])['settings']


OWNER={'pair_auto_mode':'router-probed-ipv4','failure_model':'consecutive','server_pick_model':'bayes','server_pick':'1',
       'interval':'20','recovery_failures':'4','recovery_successes':'3','recovery_cooldown':'90','recovery_min_dwell':'120',
       'recovery_return_policy':'hold_reserve','recovery_primary_successes':'3','recovery_primary_stable':'200',
       'recovery_rescue_stable':'15','recovery_attempt_limit':'5','recovery_attempt_window':'10',
       'recovery_flap_model':'halflife','recovery_flap_limit':'4','recovery_flap_window':'30'}
# a value inside each numeric option's range (channel_model.NUMERIC exists from 2.1.0-alpha9 on)
NUMERIC={key:str((low+high)/2) for key,(low,high) in getattr(channel_model,'NUMERIC',{}).items()}


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python311:local')
class SupervisorSettings(unittest.TestCase):
    def test_every_owner_model_reaches_the_deciders(self):
        for model in channel_model.MODELS:
            with self.subTest(model):
                settings=helper_settings(dict(OWNER,failure_model=model))
                self.assertEqual(channel_model.name(settings),model,'the supervisor decided with hmm before the fix')
        self.assertEqual(channel_model.name(helper_settings(dict(OWNER,failure_model='typo'))),channel_model.DEFAULT)

    def test_the_server_pick_model_and_the_recovery_options_arrive(self):
        settings=helper_settings(OWNER)
        self.assertEqual(server_pick.model_name(settings.get('server_pick_model')),'bayes')
        self.assertEqual(recovery_settings.normalized(settings),
                         {'failures':4,'successes':3,'cooldown':90,'min_dwell':120,'return_policy':'hold_reserve','primary_successes':3,
                          'primary_stable':200,'attempt_limit':5,'attempt_window':10,'rescue_stable':15,
                          'flap_model':'halflife','flap_limit':4,'flap_window':30,'flap_halflife':1800,'flap_suppress':1500,'flap_reuse':500})
        self.assertEqual(settings.get('interval'),'20')

    def test_the_numeric_detector_options_arrive(self):
        if not NUMERIC:self.skipTest('no numeric detector options in this release (channel_model.NUMERIC: 2.1.0-alpha9)')
        settings=helper_settings(dict(OWNER,failure_model='hmm',**NUMERIC))
        for key,value in NUMERIC.items():
            with self.subTest(key):
                self.assertEqual(channel_model.numeric(settings,key),float(value),'absent or not a number for the supervisor')

    def test_the_numeric_options_are_numbers_for_the_supervisor(self):
        # channel_model.numeric accepts numbers only: the helper converts the UCI strings as inventory.lua does
        settings=helper_settings(dict(OWNER,hmm_theta='0.9',hmm_dur_b='junk',return_pg='nan'))
        self.assertEqual(settings.get('hmm_theta'),0.9)
        self.assertNotIn('hmm_dur_b',settings);self.assertNotIn('return_pg',settings)

    def test_the_python_supervisor_reads_them_through_linux_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            path=runner(directory,dict(OWNER,failure_model='hmm-fast'))
            def command(argv,*args,**kwargs):
                self.assertEqual(argv,['/usr/bin/lua',native_switch.HELPER])
                return subprocess.run([LUA,str(path),str(HELPER)],stdout=subprocess.PIPE,timeout=30,check=True).stdout
            with patch.object(native_switch,'command',side_effect=command):
                settings=native_switch.Linux().policy()['settings']
        self.assertEqual(channel_model.name(settings),'hmm-fast')


if __name__=='__main__':
    unittest.main()
