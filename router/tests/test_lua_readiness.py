"""status.system_readiness from the Lua monitor (lua/readiness.lua) equals system_readiness.snapshot (Python) on the
same router facts: codes, order, states, board allowlist/bounds, storage rules and the record fields.

Each case is one fake router. Python answers with its file/process/statvfs calls replaced by the case; the Lua
driver (tests/lua/test_readiness.lua --cases) gets the same facts through its sys view. The preparation part has
its own tests (test_preparation_status.py / platform.lua) and is the same fixed record on both sides here."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
LUA=shutil.which('lua5.1') or shutil.which('lua')
spec=importlib.util.spec_from_file_location('system_readiness_lua_diff',LIB/'system_readiness.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
PREPARATION={'scope':'persistent-mt3000-preparation','state':'unsupported','checks':[],'native_permission':False,'external_lan_verified':False}
BOARD=b'{"model":"GL.iNet GL-MT3000","board_name":"glinet,mt3000-snand","serial":"S","release":{"version":"23.05"}}'
ALL=['ubus','uci','lua','ip']
FILES=['/usr/libexec/rpcd/homensai-vpn','/etc/ssl/certs/ca-certificates.crt']


def case(**overrides):
    row={'now':1761825600.5,'binaries':ALL,'files':FILES,'python_minor':11,'free':31457280,'writable':True,
         'glversion':'4.11.0\n','board_rc':0,'board_out':BOARD.decode()}
    row.update(overrides)
    return row


CASES=[
    case(),
    case(python_minor=8),
    case(binaries=['ubus','lua']),
    case(files=[]),
    case(free=1048575),
    case(writable=False),
    case(free=None,writable=None),
    case(free=None,writable=True),
    case(glversion='4.11.0;reboot'),
    case(glversion='x'*300),
    case(glversion=None),
    case(board_rc=1),
    case(board_out='null'),
    case(board_out='[]'),
    case(board_out='{"release":null}'),
    case(board_out='{"model":"x86","board_name":"generic","release":{"version":"21.02"},"hostname":"h"}'),
    case(board_out='{"model":"'+'m'*120+'","board_name":7,"release":{"version":"'+'v'*80+'"}}'),
    case(board_out='x'*32769),
    case(board_out='{bad'),
]


def python_snapshot(c):
    class FakePath:
        def __init__(self,path):self.path=str(path)
        def is_file(self):return self.path in c['files']
        def stat(self):
            if self.path!='/etc/glversion' or c['glversion'] is None:raise FileNotFoundError(self.path)
            return SimpleNamespace(st_size=len(c['glversion'].encode()))
        def read_text(self,encoding=None):
            if c['glversion'] is None:raise FileNotFoundError(self.path)
            return c['glversion']
    def run(argv,**kwargs):
        assert argv==['ubus','call','system','board'] and kwargs.get('check') is True
        if c['board_rc']:raise subprocess.CalledProcessError(c['board_rc'],argv)
        return subprocess.CompletedProcess(argv,0,c['board_out'].encode())
    def disk_usage(path):
        if c['free'] is None:raise OSError('statvfs')
        return SimpleNamespace(free=c['free'])
    def statvfs(path):
        if c['writable'] is None:raise OSError('statvfs')
        return SimpleNamespace(f_flag=0 if c['writable'] else 1)
    fake_preparation=SimpleNamespace(snapshot=lambda settings=None:dict(PREPARATION))
    with patch.object(module,'Path',FakePath),\
         patch.object(module.subprocess,'run',run),\
         patch.object(module.shutil,'which',lambda name:'/usr/bin/'+name if name in c['binaries'] else None),\
         patch.object(module.shutil,'disk_usage',disk_usage),\
         patch.object(module.os,'statvfs',statvfs,create=True),\
         patch.object(module.os,'access',lambda path,mode:True),\
         patch.object(module,'sys',SimpleNamespace(version_info=(3,c['python_minor']))),\
         patch.dict(sys.modules,{'preparation_status':fake_preparation}):
        return json.loads(json.dumps(module.snapshot(c['now'],settings={})))


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; covered by Python 3.9/Lua CI')
class LuaReadinessDifferential(unittest.TestCase):
    def test_lua_equals_python_on_every_case(self):
        run=subprocess.run([LUA,str(HERE/'lua/test_readiness.lua'),'--cases'],input=json.dumps(CASES).encode(),
                           capture_output=True,timeout=30,cwd=str(HERE.parent.parent))
        self.assertEqual(run.returncode,0,run.stderr.decode())
        lines=run.stdout.decode().splitlines()
        self.assertEqual(len(lines),len(CASES))
        for c,line in zip(CASES,lines):
            with self.subTest(case={k:v for k,v in c.items() if k!='board_out'},board=c['board_out'][:40]):
                self.assertEqual(json.loads(line),python_snapshot(c))

    def test_status_text_never_carries_board_secrets(self):
        run=subprocess.run([LUA,str(HERE/'lua/test_readiness.lua'),'--cases'],input=json.dumps(CASES[:1]).encode(),
                           capture_output=True,timeout=30,cwd=str(HERE.parent.parent))
        self.assertNotIn('"S"',run.stdout.decode());self.assertNotIn('serial',run.stdout.decode())


if __name__=='__main__':unittest.main()
