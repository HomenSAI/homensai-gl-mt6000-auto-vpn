"""Prevent scheduling short runs or reusing a previous run's public archive."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('overnight_local',ROOT/'scripts/overnight-local.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
class OvernightBounds(unittest.TestCase):
    def test_full_duration_and_cleanup_reserve_required(self):
        now=datetime(2026,10,17,tzinfo=timezone.utc)
        with patch.object(runner,'utc',return_value=now):
            self.assertFalse(runner.enough_time(now+timedelta(seconds=7499),7200))
            self.assertTrue(runner.enough_time(now+timedelta(seconds=7500),7200))
            self.assertFalse(runner.enough_time(now-timedelta(seconds=1),7200))
    def test_public_archive_is_per_run(self):
        source=(ROOT/'lab/export_protocol_evidence.py').read_text()
        self.assertIn("archive=root+'-public-evidence.tar.gz'",source)
        self.assertNotIn("archive='/tmp/homensai-final-public-evidence.tar.gz'",source)
    def test_collector_reuse_is_hash_verified_and_not_symlink(self):
        source=(ROOT/'lab/start_protocol_ready_collector.py').read_text()
        self.assertIn('assert not collector.is_symlink()',source)
        self.assertIn('hashlib.sha256(collector.read_bytes()).hexdigest()==__COLLECTOR_SHA__',source)
if __name__=='__main__': unittest.main()
