import copy,json,os
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import pair_auto
LUA=shutil.which('lua5.1')


@unittest.skipUnless(LUA,'Lua runtime covered by Python 3.9 CI')
class PairNetworkLuaTests(unittest.TestCase):
    def run_writer(self,mutate=None):
        rows=[{'.name':'wgclient1','proto':'wgclient','disabled':'0','config':'peer_2'},
              {'.name':'ovpnclient1','proto':'ovpnclient','disabled':'1','config':'old'},
              {'.name':'ovpnclient2','proto':'ovpnclient','disabled':'1','config':'current'}]
        request={'stage':'/tmp/private-stage','expected':copy.deepcopy(rows),'interface':'ovpnclient2','value':'0','managed':{'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}}
        if mutate:mutate(request)
        prefix="local j=require('cjson');local rows=j.decode([==["+json.dumps(rows)+"]==])\n"
        prefix+=r'''
package.preload['uci']=function()return {cursor=function()
 local c={}
 function c:changes(p)return {}end
 function c:foreach(p,kind,callback)assert(p=='network');for _,row in ipairs(rows)do local clone={};for k,v in pairs(row)do clone[k]=v end;callback(clone)end end
 function c:set(p,name,key,value)assert(p=='network'and key=='disabled');for _,row in ipairs(rows)do if row['.name']==name then row[key]=value;return true end end;return false end
 function c:save()return true end;function c:commit()return true end;return c
end}end
'''
        code=prefix+'assert(loadstring([====['+pair_auto.NETWORK_WRITE+']====]))()\nprint(j.encode(rows))\n'
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'writer.lua';script.write_text(code)
            return subprocess.run([LUA,str(script)],input=json.dumps(request).encode(),capture_output=True,timeout=8)

    def test_only_managed_second_interface_is_changed(self):
        result=self.run_writer();self.assertEqual(result.returncode,0,result.stderr)
        rows=json.loads(result.stdout);self.assertEqual([row['disabled']for row in rows],['0','1','0'])
        self.assertEqual(rows[2]['config'],'current')

    def test_unmanaged_interface_wrong_proto_and_external_edit_refuse(self):
        for change in (lambda q:q.update(interface='ovpnclient1'),lambda q:q['managed'].update(wgclient1='ovpnclient'),lambda q:q['expected'][0].update(config='changed')):
            result=self.run_writer(change);self.assertNotEqual(result.returncode,0);self.assertFalse(result.stdout.strip())
