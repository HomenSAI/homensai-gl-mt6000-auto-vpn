import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VersionCurrentTests(unittest.TestCase):
    def test_version_follows_the_product_source(self):
        """A change to the product source must come with a new version (python scripts/bump-version.py does it)."""
        result = subprocess.run([sys.executable, str(ROOT/'scripts/bump-version.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_manifest_agrees_with_literals(self):
        result = subprocess.run([sys.executable, str(ROOT/'qa/check_versions.py')], capture_output=True, text=True)
        self.assertIn('"result": "PASS"', result.stdout)


if __name__ == '__main__':
    unittest.main()
