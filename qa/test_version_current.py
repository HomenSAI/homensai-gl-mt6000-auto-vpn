import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VersionCurrentTests(unittest.TestCase):
    def test_new_prerelease_resets_a_previous_package_revision(self):
        import importlib.util
        import tempfile
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('version_bump',ROOT/'scripts/bump-version.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'router').mkdir()
            make=root/'router/Makefile';make.write_text('PKG_VERSION:=0.9.1-alpha26\nPKG_RELEASE:=2\n')
            with patch.object(module,'ROOT',root),patch.object(module,'LITERAL_FILES',('router/Makefile',)):
                module.rewrite('0.9.1-alpha26','0.9.1-alpha26-2','0.9.1-alpha27','0.9.1-alpha27-1')
            self.assertEqual(make.read_text(),'PKG_VERSION:=0.9.1-alpha27\nPKG_RELEASE:=1\n')

    def test_version_follows_the_product_source(self):
        """A change to the product source must come with a new version (python scripts/bump-version.py does it)."""
        result = subprocess.run([sys.executable, str(ROOT/'scripts/bump-version.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_manifest_agrees_with_literals(self):
        result = subprocess.run([sys.executable, str(ROOT/'qa/check_versions.py')], capture_output=True, text=True)
        self.assertIn('"result": "PASS"', result.stdout)


if __name__ == '__main__':
    unittest.main()
