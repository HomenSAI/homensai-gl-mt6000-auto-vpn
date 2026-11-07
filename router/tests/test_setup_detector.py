"""The expert group "Detector and sensors" of the page: rpc setup_detector (setup_config.detector_payload) and the flap
damping fields of setup_recovery reach UCI only through the allow-listed writer, with the Auto-off rule where the
backend needs it (configuration_guard, CONFIG-STOP-AUTO-FIRST). No defaults change: the page sends only what the owner edits."""
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB));sys.path.insert(0,str(HERE))
import setup_config as setup
import recovery_settings

ALL={'retry_backoff':'fixed','probe_spread':False,'reserve_probe_interval':60,'parallel_recheck':False,'auto_event_wake':False,'wan_sensor':False,
     'wan_recover_grace':0,'wg_events':False,'stall_sensor':False,'stall_veto':False,'heartbeat_quorum':True,'server_key_pin':'enforce','probe_target_log':False}
FLAP={'flap_model':'halflife','flap_limit':3,'flap_window':30,'flap_halflife':900,'flap_suppress':2000,'flap_reuse':400}


class Payload(unittest.TestCase):
    def test_every_field_maps_to_its_own_option(self):
        main=setup.detector_payload(ALL)['main']
        self.assertEqual(main,{'retry_backoff':'fixed','probe_spread':'0','reserve_probe_interval':'60','parallel_recheck':'0','auto_event_wake':'0','wan_sensor':'0',
                               'wan_recover_grace':'0','wg_events':'0','stall_sensor':'0','stall_veto':'0','heartbeat_quorum':'1','server_key_pin':'enforce','probe_target_log':'0'})
        self.assertEqual(setup.detector_payload({'wan_sensor':True})['servers'],[])
        self.assertEqual(setup.detector_payload({'wan_sensor':True})['main'],{'wan_sensor':'1'})

    def test_a_subset_is_allowed_and_nothing_else(self):
        for good in ({'probe_spread':True},{'reserve_probe_interval':0},{'reserve_probe_interval':20},{'reserve_probe_interval':120},{'wan_recover_grace':120},{'server_key_pin':'off'}):
            setup.detector_payload(good)
        for bad in ({},[],None,{'interval':10},{'recovery_flap_limit':2},{'probe_spread':1},{'probe_spread':'1'},{'reserve_probe_interval':19},{'reserve_probe_interval':121},
                    {'reserve_probe_interval':True},{'reserve_probe_interval':60.0},{'wan_recover_grace':-1},{'wan_recover_grace':121},{'retry_backoff':'linear'},
                    {'server_key_pin':'ENFORCE'},{'server_key_pin':True},{'heartbeat_quorum':None}):
            with self.assertRaises(ValueError,msg=repr(bad)):setup.detector_payload(bad)

    def test_the_flap_fields_travel_with_the_recovery_rules(self):
        base={'failures':3,'successes':2,'cooldown':60,'min_dwell':60,'return_policy':'healthy_primary','primary_successes':2,'primary_stable':120}
        main=recovery_settings.payload(dict(base,**FLAP))['main']
        self.assertEqual({k:v for k,v in main.items() if k.startswith('recovery_flap_')},{'recovery_'+k:str(v) for k,v in FLAP.items()})
        for key,bad in (('flap_limit',0),('flap_limit',11),('flap_window',121),('flap_halflife',599),('flap_suppress',999),('flap_reuse',1001),('flap_model','x')):
            with self.assertRaises(ValueError,msg=key):recovery_settings.payload(dict(base,**{key:bad}))


class Save(unittest.TestCase):
    def run_save(self,arguments,blocked=None):
        ok=types.SimpleNamespace(returncode=0,stdout=b'OK')
        with patch.object(setup,'control_lock',return_value=nullcontext()),patch.object(setup.subprocess,'run',return_value=ok) as run,\
             patch('configuration_guard.blocked',return_value=blocked) as guard,patch.object(setup,'inventory',return_value={'settings':{}}),\
             patch('rpc_throttle.allow',return_value=True):
            answer=setup.save(arguments,'detector')
        return answer,run,guard

    def test_the_sensors_save_while_auto_works(self):
        sensors={k:v for k,v in ALL.items() if k not in setup.DETECTOR_STOP}
        answer,run,guard=self.run_save(sensors,blocked='CONFIG-STOP-AUTO-FIRST')
        self.assertTrue(answer['saved']);guard.assert_not_called()
        sent=json.loads(run.call_args.kwargs['input'])
        self.assertEqual(set(sent['main']),set(sensors));self.assertEqual(sent['servers'],[])

    def test_the_options_of_the_auto_loop_need_auto_off_and_say_so(self):
        for key in setup.DETECTOR_STOP:
            value='fixed' if key=='retry_backoff' else False
            answer,run,guard=self.run_save({key:value},blocked='CONFIG-STOP-AUTO-FIRST')
            self.assertEqual(answer,{'saved':False,'code':'CONFIG-STOP-AUTO-FIRST'},key);run.assert_not_called()
            answer,run,guard=self.run_save({key:value},blocked=None)
            self.assertTrue(answer['saved'],key);self.assertEqual(run.call_count,1)
        self.assertEqual(set(setup.DETECTOR_STOP),{'retry_backoff','parallel_recheck','auto_event_wake'})

    def test_invalid_input_never_calls_the_writer(self):
        with patch.object(setup.subprocess,'run') as writer:
            for bad in ({},{'probe_spread':'yes'},{'unknown':True}):
                with self.assertRaises(ValueError):setup.save(bad,'detector')
            writer.assert_not_called()

    def test_agent_routes_acl_and_lua_bridge_know_the_method(self):
        import agent
        text=(LIB/'agent.py').read_text(encoding='utf-8')
        self.assertIn("'setup_detector':'detector'",text);self.assertIn("'setup_response','setup_detector'",text)
        out=types.SimpleNamespace(parts=[]);
        with patch('builtins.print',lambda s:out.parts.append(s)):agent.rpc('list')
        listed=json.loads(out.parts[0])
        self.assertEqual(set(listed['setup_detector']),set(ALL))
        self.assertTrue(set(FLAP)<=set(listed['setup_recovery']),'the flap fields are declared')
        acl=json.loads((LIB.parents[1]/'share/rpcd/acl.d/luci-app-homensai-vpn.json').read_text())['luci-app-homensai-vpn']
        self.assertIn('setup_detector',acl['write']['ubus']['homensai-vpn']);self.assertNotIn('setup_detector',acl['read']['ubus']['homensai-vpn'])
        self.assertIn("'setup_detector'",(LIB/'lua/rpc.lua').read_text(encoding='utf-8').split('M.PAGE_SAMPLE_OMIT')[0])

    def test_the_writer_and_the_inventory_know_every_option(self):
        save=(LIB/'setup_save.lua').read_text(encoding='utf-8');inventory=(LIB/'inventory.lua').read_text(encoding='utf-8')
        for key in ALL:
            self.assertIn(key+'=true',save,key)
        # recovery_flap_*: read by the inventory; the writer's allow-list for setup_recovery is owned by fix/safety-review-a9-20261104
        for key in list(ALL)+['recovery_'+k for k in FLAP]:
            self.assertIn('main.'+key+'=',inventory,key)
        # the defaults of the inventory stay as they were
        for line in ("main.probe_spread=s.probe_spread~='0'","main.parallel_recheck=s.parallel_recheck=='1'","main.auto_event_wake=s.auto_event_wake~='0'",
                     "main.wan_sensor=s.wan_sensor~='0'","main.wg_events=s.wg_events~='0'","main.stall_sensor=s.stall_sensor~='0'","main.stall_veto=s.stall_veto~='0'",
                     "main.heartbeat_quorum=s.heartbeat_quorum=='1'","main.probe_target_log=s.probe_target_log~='0'","main.retry_backoff=s.retry_backoff=='fixed' and 'fixed' or 'fibonacci'",
                     "main.recovery_flap_model=s.recovery_flap_model=='halflife' and 'halflife' or 'double'","or 30","main.server_key_pin=(s.server_key_pin=='enforce' or s.server_key_pin=='off') and s.server_key_pin or 'warn'"):
            self.assertIn(line,inventory)


class Writer(unittest.TestCase):
    def test_the_lua_writer_accepts_the_new_keys_and_still_refuses_others(self):
        from test_lua_contracts import LuaContracts,LUA,LUAC
        if not (LUA and LUAC):self.skipTest('Lua 5.1 runtime absent')
        holder=types.SimpleNamespace()
        main=setup.detector_payload(ALL)['main']
        result,calls=LuaContracts.run_setup(holder,json.dumps({'main':main,'servers':[]}).encode(),pending=b'')
        self.assertEqual(result.stdout,b'OK')
        self.assertEqual({c['key']:c['value'] for c in calls if c['name']=='set'},main)
        result,calls=LuaContracts.run_setup(holder,json.dumps({'main':{'not_an_option':'1'},'servers':[]}).encode(),pending=b'')
        self.assertNotEqual(result.returncode,0);self.assertEqual(holder.executed,[])


if __name__=='__main__':
    unittest.main()
