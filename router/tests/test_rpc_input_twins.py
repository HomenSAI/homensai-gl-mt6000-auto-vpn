"""BH2-04 (bug hunt 07.11.2026): the RPC input decoder twins answer the same code for the same request text.

Bridged methods answer from lua/rpc.lua when the Lua monitor is ready and from agent.py (rpc_input.decode_request)
otherwise. Deep nesting gave RPC-INPUT-COMPLEXITY in Lua (canon refuses beyond 64 levels) but RPC-INPUT-DEPTH in
Python when the C scanner hit RecursionError (~1000 levels). Both now answer RPC-INPUT-COMPLEXITY for every nesting
refusal. Shared vectors run through both decoders.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import rpc_input  # noqa: E402

LUA=shutil.which('lua5.1')

VECTORS=[b'['*60000, b'{"a":'*2000+b'1'+b'}'*2000, b'{"a":'*70+b'1'+b'}'*70, b'{"a":'+b'['*70+b']'*70+b'}',
         b'{"a":'*64+b'1'+b'}'*64, b'{"a":'*65+b'1'+b'}'*65, b'{"a":'+b'9'*5000+b'}', b'{"a":1e400}', b'{"a":1,"a":2}',
         b'{"a":', b'[]', b'x'*70000, b'{"a":[' + b','.join([b'1']*10001) + b']}', b'{"a":{"b":[1,2.5,"x",null,true]}}', b'',
         b'{"ubus_rpc_session":"s","n":3}']


def py_code(body):
    try:rpc_input.decode_request(body.decode('utf-8'));return 'ok'
    except ValueError as error:return str(error)


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:night')
class RpcInputTwins(unittest.TestCase):
    def test_same_code_for_the_same_request(self):
        with tempfile.TemporaryDirectory() as folder:
            for i,body in enumerate(VECTORS):(Path(folder)/('v%d'%i)).write_bytes(body)
            code=("package.path=arg[1]..'/?.lua;'..package.path\n"
                  "local rpc=require('rpc')\n"
                  "for i=0,tonumber(arg[3])-1 do\n"
                  " local f=io.open(arg[2]..'/v'..i,'rb');local s=f:read('*a');f:close()\n"
                  " local ok,e=pcall(rpc.decode_request,s)\n"
                  " print(ok and 'ok' or (type(e)=='table' and e.code or tostring(e)))\n"
                  "end\n")
            script=Path(folder)/'run.lua';script.write_text(code,encoding='utf-8')
            out=subprocess.run([LUA,str(script),str(LIB/'lua'),folder,str(len(VECTORS))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        self.assertEqual(out.returncode,0,out.stderr.decode())
        lua=out.stdout.decode().split()
        self.assertEqual(len(lua),len(VECTORS))
        for body,got in zip(VECTORS,lua):
            self.assertEqual(got,py_code(body),body[:40])
        # the deep cases are the same catalogue row, never RPC-INPUT-DEPTH
        self.assertEqual(lua[0],'RPC-INPUT-COMPLEXITY');self.assertEqual(lua[1],'RPC-INPUT-COMPLEXITY')
        self.assertEqual(py_code(VECTORS[0]),'RPC-INPUT-COMPLEXITY')


class PythonDeepNesting(unittest.TestCase):
    def test_recursion_error_is_the_complexity_code(self):
        for body in (b'['*60000, b'{"a":'*5000+b'1'+b'}'*5000):
            self.assertEqual(py_code(body),'RPC-INPUT-COMPLEXITY')
        self.assertNotIn("'RPC-INPUT-DEPTH'",(LIB/'rpc_input.py').read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
