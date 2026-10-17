import importlib.util
from pathlib import Path
import tempfile,unittest
path=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn/luci_cache.py'
spec=importlib.util.spec_from_file_location('luci_cache',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CacheTests(unittest.TestCase):
    def test_hashed_indices_and_only_owned_controller(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);directory=root/'luci-modulecache';directory.mkdir()
            own=directory/'luci.controller.homensai_vpn'.encode().hex().upper();own.write_text('old')
            other=directory/'other';other.write_text('keep')
            for n in ('luci-indexcache','luci-indexcache.abc..lua','luci-indexcache.abc..json'):(root/n).write_text('old')
            unrelated=root/'luci-indexcache.notes';unrelated.write_text('keep')
            self.assertEqual(m.invalidate(root),4);self.assertTrue(other.exists());self.assertTrue(unrelated.exists());self.assertEqual(m.invalidate(root),0)
    def test_symlink_not_followed(self):
        import os
        if os.name=='nt':self.skipTest('Unix symlink safety covered by Linux CI')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);outside=root/'preserve';outside.write_text('keep');(root/'luci-indexcache').symlink_to(outside)
            m.invalidate(root);self.assertEqual(outside.read_text(),'keep')
