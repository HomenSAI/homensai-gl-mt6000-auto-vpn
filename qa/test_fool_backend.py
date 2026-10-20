import importlib.util
from pathlib import Path
import unittest

try:
    import fcntl  # noqa: F401 - the backend needs POSIX locking
except ImportError:
    fcntl = None

SPEC = importlib.util.spec_from_file_location('fool_backend', Path(__file__).with_name('fool_backend.py'))


@unittest.skipIf(fcntl is None, 'the router backend needs fcntl (Linux)')
class FoolBackendTests(unittest.TestCase):
    def test_all_fifty_personas_leave_no_bad_call(self):
        module = importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(module)
        tally, bad = module.run_all(per_method_calls=4)
        self.assertEqual([], [item[:5] for item in bad][:10])
        calls = sum(sum(c.values()) for c in tally.values())
        self.assertGreater(calls, 10000)
        accepted = sum(c['ACCEPTED'] for c in tally.values())
        self.assertGreater(accepted, 1000, 'valid requests must still be accepted')


if __name__ == '__main__':
    unittest.main()
