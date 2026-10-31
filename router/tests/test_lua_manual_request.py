"""Plan item 4: the QUEUED click row written by the Lua monitor (lua/manual_request.lua) is a row the Python
supervisor and pair_manual.valid() accept, and the Lua suite for the request passes."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
LUA = shutil.which('lua5.1') or shutil.which('lua')


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaManualRequest(unittest.TestCase):
    def test_lua_suite(self):
        result = subprocess.run([LUA, str(HERE/'lua/test_manual_request.lua')], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=120)
        self.assertEqual(result.returncode, 0, (result.stdout+result.stderr).decode(errors='replace'))
        self.assertIn(b'tests OK', result.stdout)

    def test_written_row_is_valid_for_python(self):
        import pair_manual
        result = subprocess.run([LUA, str(HERE/'lua/test_manual_request.lua'), '--row'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        row = json.loads(result.stdout)
        self.assertTrue(pair_manual.valid(row), row)
        self.assertEqual(row['state'], 'QUEUED')
        self.assertIsInstance(row['requested'], float)


if __name__ == '__main__':
    unittest.main()
