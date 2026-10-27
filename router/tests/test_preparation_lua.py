"""Execute the real narrow writer in Lua 5.1 with an isolated UCI contract."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

LUA=shutil.which('lua5.1')
HELPER=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn/preparation_write.lua'


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; covered by Python 3.9/Lua CI')
class PreparationLuaTests(unittest.TestCase):
    def run_writer(self,patch_payload=None,failure='',second=False):
        with tempfile.TemporaryDirectory(prefix='homensai-preparation-test-') as directory:
            root=Path(directory);(root/'stage').mkdir();(root/'network').write_text('original bytes\n')
            calls=root/'calls';calls.write_text('')
            payload={'action':'wg-autostart','expected':'original bytes\n','stage':str(root/'stage'),
                     'changes':[{'section':'wgclient1','type':'interface','option':'auto','before':'1','after':'0'}]}
            if second:payload['action']='target-autostart';payload['changes'][0]['section']='ovpnclient2'
            if patch_payload:patch_payload(payload)
            state={'sections':[{'.name':'wgclient1','.type':'interface','proto':'wgclient','auto':'1','config':'peer_9','private_fixture':'DO-NOT-EMIT'},
                               {'.name':'lan','.type':'interface','proto':'static','ipaddr':'192.0.2.1'}]}
            if second:state['sections'][0].update({'.name':'ovpnclient2','proto':'ovpnclient'})
            prefix="local j=require('cjson');local state=j.decode([==["+json.dumps(state)+"]==]);local failure="+json.dumps(failure)+"\n"
            prefix+="local output="+json.dumps(str(calls))+";local config="+json.dumps(str(root/'network'))+"\n"
            prefix+=r'''
local saved=false;local committed=false
local function log(value)local f=assert(io.open(output,'a'));f:write(value..'\n');f:close()end
package.preload['uci']=function()
 return {cursor=function(base,stage)
  local c={}
  function c:changes(package)
   if failure=='pending'or failure=='delta-after-save'and saved then return {changed=true}end
   return {}
  end
  function c:get(package,name,key)
   if package=='homensai_vpn'and name=='main'and key=='plan_target_tunnel'then return 'openvpn:ovpnclient2'end
   if package~='network'then return nil end
   for _,row in ipairs(state.sections)do if row['.name']==name then return key and row[key]or row['.type']end end
  end
  function c:foreach(package,kind,callback)
   assert(package=='network');for _,row in ipairs(state.sections)do
    local clone={};for k,v in pairs(row)do clone[k]=v end;callback(clone)
   end
  end
  function c:set(package,name,key,value)
   assert(package=='network');log('set:'..name..':'..key)
   for _,row in ipairs(state.sections)do if row['.name']==name then row[key]=value;return true end end
   return false
  end
  function c:save(package)log('save');saved=true;return failure~='save-failed'end
  function c:commit(package)
   log('commit');committed=true;local f=assert(io.open(config,'w'));f:write('committed bytes\n');f:close()
   if failure=='unrelated-change'then state.sections[2].ipaddr='192.0.2.99'end
   return failure~='commit-unconfirmed'
  end
  return c
 end}
end
'''
            wrapper=root/'wrapper.lua';wrapper.write_text(prefix+'assert(loadfile('+json.dumps(str(HELPER))+'))()\n')
            run=subprocess.run([LUA,str(wrapper)],input=json.dumps(payload).encode(),capture_output=True,
                               env=dict(os.environ,HOMENSAI_PREPARATION_TEST_ROOT=str(root)),timeout=8)
            return run.returncode,run.stdout,run.stderr,calls.read_text(),(root/'network').read_text()

    def test_only_reviewed_autostart_option_is_committed_and_read_back(self):
        code,out,err,calls,raw=self.run_writer()
        self.assertEqual(code,0,err);self.assertEqual(out,b'OK')
        self.assertIn('set:wgclient1:auto',calls);self.assertNotIn('DO-NOT-EMIT',out.decode()+err.decode())
        self.assertNotEqual(raw,'original bytes\n')

    def test_extra_option_injected_command_and_stale_bytes_refuse_before_mutation(self):
        mutations=[lambda p:p.update(action='wg-autostart;reboot'),lambda p:p.update(expected='stale'),
                   lambda p:p['changes'][0].update(option='config'),lambda p:p['changes'][0].update(section='lan'),
                   lambda p:p['changes'][0].update(after='1'),lambda p:p.update(stage='/tmp/untrusted'),
                   lambda p:p['changes'].append(copy.deepcopy(p['changes'][0]))]
        for change in mutations:
            with self.subTest(change=change):
                code,out,err,calls,raw=self.run_writer(change)
                self.assertNotEqual(code,0);self.assertEqual(calls,'');self.assertEqual(raw,'original bytes\n');self.assertNotEqual(out,b'OK')

    def test_pending_changes_refuse_without_mutation(self):
        code,out,err,calls,raw=self.run_writer(failure='pending')
        self.assertNotEqual(code,0);self.assertEqual(calls,'');self.assertEqual(raw,'original bytes\n')

    def test_reviewed_reserve_startup_targets_its_current_second_slot(self):
        code,out,err,calls,raw=self.run_writer(second=True)
        self.assertEqual(code,0,err);self.assertEqual(out,b'OK');self.assertIn('set:ovpnclient2:auto',calls)
        code,out,err,calls,raw=self.run_writer(lambda q:q['changes'][0].update(section='ovpnclient1'),second=True)
        self.assertNotEqual(code,0);self.assertEqual(calls,'')

    def test_failed_stage_or_readback_is_never_a_success_ack(self):
        for failure in ('save-failed','delta-after-save','commit-unconfirmed','unrelated-change'):
            with self.subTest(failure=failure):
                code,out,err,calls,raw=self.run_writer(failure=failure)
                self.assertNotEqual(code,0);self.assertNotEqual(out,b'OK')
                if failure in ('save-failed','delta-after-save'):self.assertNotIn('commit',calls)


if __name__=='__main__':unittest.main()
