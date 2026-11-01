"""canon_c.so in the package: the recorded aarch64 build shipped byte for byte; canon.lua stays pure Lua without it."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import build_ipk

MODULE=ROOT/'files/usr/lib/lua/canon_c.so'
RECORD=ROOT/'native/canon_c.so.sha256'
LUA=shutil.which('lua5.1')


class CanonCModule(unittest.TestCase):
    def test_package_file_is_the_recorded_aarch64_build(self):
        data=MODULE.read_bytes()
        digest,name=RECORD.read_text(encoding='ascii').split()
        self.assertEqual(name,'canon_c.so')
        self.assertEqual(hashlib.sha256(data).hexdigest(),digest)
        self.assertEqual(data[:5],b'\x7fELF\x02')  # ELF64
        self.assertEqual(int.from_bytes(data[16:18],'little'),3)  # ET_DYN
        self.assertEqual(int.from_bytes(data[18:20],'little'),183)  # EM_AARCH64

    def test_ipk_keeps_the_module_bytes(self):
        files={name:(payload,mode) for name,payload,mode in build_ipk.selected_files()}
        self.assertEqual(files['usr/lib/lua/canon_c.so'],(MODULE.read_bytes(),0o644))

    @unittest.skipUnless(LUA,'Lua 5.1 runtime absent')
    def test_canon_without_a_loadable_module_is_pure_lua(self):
        lua_dir=json.dumps(str(ROOT/'files/usr/lib/homensai-vpn/lua'))
        code=("package.path=%s..'/?.lua;'..package.path;local c=require('canon');assert(c.c_module==nil)"
              ";assert(c.encode==c.lua_encode and c.decode==c.lua_decode and c.decode_keys==c.lua_decode_keys)"
              ";io.write(c.encode(c.decode('{\"b\":[1,2.5,null],\"a\":\"\\\\u00e9\"}')))" % lua_dir)
        # no module on the path; the aarch64 package file (cannot load on this host); the Lua-only switch
        for cpath,switch in (('',None),(str(ROOT/'files/usr/lib/lua')+'/?.so',None),(str(ROOT/'files/usr/lib/lua')+'/?.so','0')):
            with self.subTest(cpath=cpath,switch=switch):
                env={k:v for k,v in os.environ.items() if k not in ('LUA_CPATH','HOMENSAI_CANON_C')}
                env['LUA_CPATH']=cpath
                if switch is not None:env['HOMENSAI_CANON_C']=switch
                result=subprocess.run([LUA,'-e',code],capture_output=True,timeout=60,env=env)
                self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
                self.assertEqual(result.stdout.decode(),'{"a":"\\u00e9","b":[1,2.5,null]}')


if __name__=='__main__':
    unittest.main()
