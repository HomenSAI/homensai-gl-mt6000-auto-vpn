"""2.0.0-lua-alpha1 wiring: the Python supervisor hands the write stage of the instant switch to lua/instant_switch.lua
only when the owner turned the Lua core on; the request carries the names and tunnel order the Lua side checks;
every Lua outcome maps back to the Python journal rules (ok / refused before a write / rollback required)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as n

SECTIONS=[{'.name':'gl_process_vpn','.type':'rule_process','tunnel_id':'10100'},
          {'.name':'cfg1','.type':'rule','.anonymous':'1','tunnel_id':'5841','enabled':'1','via':'wgclient1'},
          {'.name':'cfg2','.type':'rule','.anonymous':'1','tunnel_id':'4192','enabled':'1','via':'ovpnclient2'}]


class Flag(unittest.TestCase):
    def test_off_by_default_and_needs_the_lua_file(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=Path(folder)/'homensai_vpn';lua=Path(folder)/'instant_switch.lua'
            with patch.object(n,'FAST_SWITCH_CONFIG',cfg),patch.object(n,'LUA_CORE',lua):
                self.assertFalse(n.lua_core_enabled(),'no config')
                cfg.write_text("config main 'main'\n    option fast_switch '1'\n");self.assertFalse(n.lua_core_enabled(),'not set')
                cfg.write_text("config main 'main'\n    option lua_core '1'\n");self.assertFalse(n.lua_core_enabled(),'lua core not installed')
                lua.write_text('-- lua');self.assertTrue(n.lua_core_enabled())
                cfg.write_text("config main 'main'\n    option lua_core '0'\n");self.assertFalse(n.lua_core_enabled())


class Request(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.root=Path(folder.name)
        for name,value in (('RUNTIME',self.root),('LUA_REQUEST',self.root/'instant-request.json'),('LUA_CORE',self.root/'instant_switch.lua')):
            p=patch.object(n,name,value);p.start();self.addCleanup(p.stop)
        self.backend=n.Linux.__new__(n.Linux);self.backend.process_bindings=None
        self.backend.policy=lambda:{'sections':SECTIONS,'settings':{}}
        ids=n.policy_order(SECTIONS)
        self.after=[ids[0],ids[2],ids[1]]  # reserve (4192) first
        self.journal={'tx':'a'*32,'control_revision':'b'*32,'phase':'APPLYING'}
        self.calls=[]

    def fake_run(self,reply,returncode=0):
        def run(args,stdout=None,stderr=None,timeout=None):
            self.calls.append(args);request=json.loads(Path(args[3]).read_text())
            self.seen=request
            class P:pass
            p=P();p.returncode=returncode;p.stdout=(json.dumps(reply)+'\n').encode();return p
        return run

    def test_request_carries_names_and_tunnel_order(self):
        with patch.object(n.subprocess,'run',self.fake_run({'ok':True,'phase':'HELD-ON-RESERVE','stages':[['journal',0.1]]})):
            result=n.lua_instant_switch(self.backend,{},self.journal,'target',self.after)
        self.assertTrue(result['ok']);self.assertEqual(self.calls[0][:2],['/usr/bin/lua',str(self.root/'instant_switch.lua')]);self.assertEqual(self.calls[0][2],'reserve')
        self.assertEqual(self.seen['tunnel_order'],['4192','5841']);self.assertEqual(self.seen['control_revision'],'b'*32)
        self.assertEqual(set(self.seen['names'].values()),{'gl_process_vpn','cfg1','cfg2'})
        self.assertFalse((self.root/'instant-request.json').exists(),'the request file is removed afterwards')

    def test_refusal_keeps_the_lua_code_and_rollback_flag(self):
        with patch.object(n.subprocess,'run',self.fake_run({'ok':False,'code':'POLICY-REORDER-UNVERIFIED','rollback_required':True},2)):
            with self.assertRaises(n.Refused) as caught:n.lua_instant_switch(self.backend,{},self.journal,'source',[self.after[0],self.after[2],self.after[1]])
        self.assertEqual(str(caught.exception),'POLICY-REORDER-UNVERIFIED');self.assertTrue(caught.exception.lua_result['rollback_required'])

    def test_garbage_or_missing_lua_is_a_refusal_not_a_crash(self):
        with patch.object(n.subprocess,'run',side_effect=OSError('no lua')),self.assertRaisesRegex(n.Refused,'LUA-CORE-UNAVAILABLE'):
            n.lua_instant_switch(self.backend,{},self.journal,'target',self.after)
        def junk(args,**kw):
            class P:pass
            p=P();p.returncode=0;p.stdout=b'not json\n';return p
        with patch.object(n.subprocess,'run',junk),self.assertRaisesRegex(n.Refused,'LUA-CORE-UNAVAILABLE'):
            n.lua_instant_switch(self.backend,{},self.journal,'target',self.after)
        with patch.object(n.subprocess,'run',self.fake_run({'ok':False,'code':'bad code; rm'},2)),self.assertRaisesRegex(n.Refused,'LUA-CORE-UNAVAILABLE'):
            n.lua_instant_switch(self.backend,{},self.journal,'target',self.after)


if __name__=='__main__':unittest.main()
