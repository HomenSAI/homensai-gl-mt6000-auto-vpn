"""Actual Lua/CJSON execution with a deliberately mocked UCI cursor."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

LUA=shutil.which('lua5.1')
LUAC=shutil.which('luac5.1')
ROOT=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'


@unittest.skipUnless(LUA and LUAC,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaContracts(unittest.TestCase):
    def run_setup(self,payload,failure='',testroot=None,pending=None,board=None):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'calls.json'
            delta=Path(directory)/'delta';delta.mkdir()
            if pending is not None:(delta/'homensai_vpn').write_bytes(pending)
            prelude='''
local json=require('cjson')
local calls={}
local output=OUTPUT
local failure=FAILURE
local function record(name,config,section,key,value)
  assert(config=='homensai_vpn','unexpected UCI config')
  calls[#calls+1]={name=name,config=config,section=section,key=key,value=value}
  local f=assert(io.open(output,'w'));f:write(json.encode(calls));f:close()
end
package.preload['uci']=function()
 local function copy(value)
  if type(value)~='table' then return value end
  local out={};for key,item in pairs(value) do out[key]=copy(item) end;return out
 end
 local committed={main={['.type']='main'},cfg_existing={['.type']='server',profile='wireguard:peer_7'}}
 local cursor_count=0
 local function cursor()
 cursor_count=cursor_count+1
 local current_cursor=cursor_count
 local staged=copy(committed)
 local c={}
 function c:get_savedir() if failure=='savedir' then return nil end;return DELTA end
 function c:set(config,section,key,value)
  record('set',config,section,key,value);if failure=='set' then return nil end
  if value==nil then staged[section]={['.type']=key}
  else staged[section]=staged[section] or {};staged[section][key]=value end
  return true
 end
 function c:get(config,section,key)
  assert(config=='homensai_vpn')
  if current_cursor>1 and failure=='readback_error' then error('PRIVATE_SENTINEL') end
  local row=staged[section];if not row then return nil end
  if key then return row[key] end;return row['.type']
 end
 function c:foreach(config,kind,callback)
  assert(config=='homensai_vpn' and kind=='server')
  for name,row in pairs(staged) do if row['.type']=='server' then local value=copy(row);value['.name']=name;callback(value) end end
 end
 function c:save(config) record('save',config);if failure=='save' then return nil end;return true end
 function c:commit(config)
  record('commit',config);if failure=='commit' then return nil end
  committed=copy(staged)
  if failure=='readback_main' then committed.main.interval='PRIVATE_SENTINEL' end
  if failure=='readback_server' then committed.cfg_existing.name='PRIVATE_SENTINEL' end
  if failure=='readback_marker' then committed.main.onboarding_complete=nil end
  return true
 end
 function c:revert(config) record('revert',config);staged=copy(committed);return true end
 function c:delete(config,section,key)
  record('delete',config,section,key);if failure=='delete' then return nil end
  if staged[section] then staged[section][key]=nil end;return true
 end
 return c
 end
 return {cursor=cursor}
end
'''.replace('OUTPUT',json.dumps(str(output))).replace('FAILURE',json.dumps(failure)).replace('DELTA',json.dumps(str(delta)))
            environment=dict(os.environ)
            if board is not None:
                prelude += "\nlocal original_open=io.open;io.open=function(path,mode) if path=='/tmp/sysinfo/board_name' then local f=io.tmpfile();f:write("+json.dumps(board)+");f:seek('set');return f end;return original_open(path,mode) end\n"
            if testroot is not None:environment['HOMENSAI_SETUP_TEST_ROOT']=testroot
            result=subprocess.run([LUA,'-e',prelude,str(ROOT/'setup_save.lua')],
                                  input=payload,capture_output=True,env=environment,timeout=5)
            calls=json.loads(output.read_text()) if output.exists() else []
            return result,calls

    def payload(self):
        return json.dumps(dict(main={'interval':'30'},servers=[dict(section='srv_new',
            profile='wireguard:peer_7',name='Имя пользователя',channel='Main',priority='2',enabled='1')])).encode()

    def test_model_is_verified_before_any_uci_change(self):
        for board, selected, expected in (
                ('glinet,mt3000-snand\n', 'mt3000', True),
                ('glinet,gl-mt6000\n', 'mt6000', True),
                ('glinet,mt3000-snand\n', 'mt6000', False),
                ('unknown\n', 'mt3000', False),
                ('unknown\n', 'auto', True),
                ('glinet,mt3000-snand\n', 'bad', False)):
            payload=json.dumps({'main':{'router_model':selected},'servers':[]}).encode()
            result,calls=self.run_setup(payload,board=board)
            self.assertEqual(result.returncode==0, expected, (board,selected,result.stderr))
            if not expected:
                self.assertFalse(any(call['name'] in ('set','save','commit') for call in calls))

    def test_pending_delta_refuses_without_writes_or_revert(self):
        for pending in (b"homensai_vpn.main.interval='99'\n",b'\x00'):
            result,calls=self.run_setup(self.payload(),pending=pending)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(result.stdout,b'SETUP-PENDING-DELTA')
            self.assertEqual(calls,[])

    def test_unknown_savedir_fails_closed_and_empty_delta_is_allowed(self):
        result,calls=self.run_setup(self.payload(),failure='savedir')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(result.stdout,b'SETUP-DELTA-UNVERIFIED')
        self.assertEqual(calls,[])
        result,calls=self.run_setup(self.payload(),pending=b'')
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout,b'OK')

    def test_only_the_telegram_token_can_be_deleted_and_failure_reverts(self):
        ok=json.dumps({'main':{'telegram_enabled':'0'},'servers':[],'delete':['telegram_token']}).encode()
        result,calls=self.run_setup(ok,pending=b'')
        self.assertEqual(result.stdout,b'OK')
        self.assertIn(('delete','main','telegram_token'),[(c['name'],c.get('section'),c.get('key')) for c in calls])
        for key in ('telegram_chat','enabled','interval','../x'):
            bad=json.dumps({'main':{},'servers':[],'delete':[key]}).encode()
            result,calls=self.run_setup(bad,pending=b'')
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('delete',[c['name'] for c in calls]);self.assertIn('revert',[c['name'] for c in calls])
        result,calls=self.run_setup(ok,failure='delete',pending=b'')
        self.assertNotEqual(result.returncode,0);self.assertIn('revert',[c['name'] for c in calls]);self.assertNotIn('commit',[c['name'] for c in calls])

    def test_terms_keys_are_writable_and_arbitrary_keys_are_not(self):
        result,calls=self.run_setup(json.dumps({'main':{'terms_version':'1','terms_time':'1792000000'},'servers':[]}).encode(),pending=b'')
        self.assertEqual(result.stdout,b'OK');self.assertEqual({c['key'] for c in calls if c['name']=='set'},{'terms_version','terms_time'})
        result,calls=self.run_setup(json.dumps({'main':{'terms_accepted_by':'x'},'servers':[]}).encode(),pending=b'')
        self.assertNotEqual(result.returncode,0)

    def test_onboarding_marker_and_all_preferences_use_exactly_one_commit(self):
        payload=json.loads(self.payload())
        payload['main'].update(onboarding_version='1',onboarding_complete='1',onboarding_pair_deferred='1')
        result,calls=self.run_setup(json.dumps(payload).encode(),pending=b'')
        self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,b'OK')
        self.assertEqual([row['name'] for row in calls].count('commit'),1)
        marker_positions=[index for index,row in enumerate(calls) if row.get('key') in
                          ('onboarding_version','onboarding_complete','onboarding_pair_deferred')]
        self.assertEqual(len(marker_positions),3)
        self.assertLess(max(marker_positions),next(index for index,row in enumerate(calls) if row['name']=='commit'))

    def test_fresh_committed_cursor_must_confirm_main_server_and_marker(self):
        payload=json.loads(self.payload())
        payload['main'].update(onboarding_version='1',onboarding_complete='1',onboarding_pair_deferred='1')
        for failure in ('readback_main','readback_server','readback_marker','readback_error'):
            with self.subTest(failure=failure):
                result,calls=self.run_setup(json.dumps(payload).encode(),failure=failure,pending=b'')
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(result.stdout,b'SETUP-SAVE-UNCONFIRMED')
                self.assertNotIn(b'PRIVATE_SENTINEL',result.stdout)
                self.assertEqual([row['name'] for row in calls].count('commit'),1)

    def test_all_packaged_lua_parses(self):
        for path in ROOT.glob('*.lua'):
            with self.subTest(file=path.name):
                result=subprocess.run([LUAC,'-p',str(path)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_existing_section_identity_and_unicode_are_preserved(self):
        result,calls=self.run_setup(self.payload())
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout,b'OK')
        server=[row for row in calls if row.get('key')=='name'][0]
        self.assertEqual(server['section'],'cfg_existing')
        self.assertEqual(server['value'],'Имя пользователя')
        self.assertEqual(calls[-1]['name'],'commit')
        self.assertFalse(any(row.get('section')=='srv_new' for row in calls))

    def test_unknown_fields_and_malformed_json_revert_without_commit(self):
        for payload in (b'{broken',b'{"main":{"network":"bad"},"servers":[]}',
                        b'{"main":null,"servers":[]}',b'{"main":{"interval":30},"servers":[]}'):
            with self.subTest(payload=payload):
                result,calls=self.run_setup(payload)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(any(row['name']=='commit' for row in calls))
                self.assertEqual(calls[-1]['name'],'revert')

    def test_set_save_commit_failures_are_reported_and_reverted(self):
        for failure in ('set','save','commit'):
            result,calls=self.run_setup(self.payload(),failure)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn(b'OK',result.stdout)
            self.assertEqual(calls[-1]['name'],'revert')
            self.assertTrue(all(row['config']=='homensai_vpn' for row in calls))

    def test_size_and_test_root_reject_before_uci_writes(self):
        for payload,testroot in ((b'x'*65537,None),(self.payload(),'/tmp/unapproved-root')):
            result,calls=self.run_setup(payload,testroot=testroot)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
