"""Hardware preference cannot grant capabilities or silently select a different board."""
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files/usr/lib/homensai-vpn'))
import device_profile
import setup_config
from test_onboarding import arguments


class DeviceProfileTests(unittest.TestCase):
    def test_exact_boards_and_missing_unknown_oversized_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'board'
            self.assertEqual(device_profile.detect(path), 'unknown')
            for board, model in (('glinet,gl-mt6000\n', 'mt6000'),
                                 ('glinet,mt3000-snand\n', 'mt3000'),
                                 ('glinet,mt3000', 'unknown'), ('x' * 1000, 'unknown')):
                path.write_text(board, encoding='ascii')
                self.assertEqual(device_profile.detect(path), model)
            path.write_bytes(b'\xff')
            self.assertEqual(device_profile.detect(path), 'unknown')

    def test_explicit_model_requires_actual_same_hardware(self):
        for actual in ('mt6000', 'mt3000', 'unknown'):
            self.assertEqual(device_profile.validate('auto', actual), 'auto')
            for selected in ('mt6000', 'mt3000'):
                if selected == actual:
                    self.assertEqual(device_profile.validate(selected, actual), selected)
                else:
                    with self.assertRaisesRegex(ValueError, 'DEVICE-MODEL-MISMATCH'):
                        device_profile.validate(selected, actual)
        for selected in (None, True, [], {}, 'MT3000', 'mt3000;bad'):
            with self.assertRaisesRegex(ValueError, 'DEVICE-MODEL-INVALID'):
                device_profile.validate(selected, 'mt3000')

    def test_legacy_client_preserves_model_and_new_request_stores_only_own_metadata(self):
        profiles = [{'id': 'a'}, {'id': 'b'}]
        old = setup_config.onboarding_payload(arguments(), profiles)
        self.assertNotIn('router_model', old['main'])
        for selected in ('auto', 'mt3000'):
            args = arguments()
            args['appearance']['router_model'] = selected
            result = setup_config.onboarding_payload(args, profiles, {'detected_router_model': 'mt3000'})
            self.assertEqual(result['main']['router_model'], selected)
            self.assertNotIn('appearance_router_model', result['main'])
            self.assertNotIn('monitor_only', result['main'])
            self.assertNotIn('native_enabled', result['main'])
            args['appearance']['router_model'] = 'mt6000'
            with self.assertRaisesRegex(ValueError, 'DEVICE-MODEL-MISMATCH'):
                setup_config.onboarding_payload(args, profiles, {'detected_router_model': 'mt3000'})

    def test_fresh_hardware_read_fences_stale_inventory_before_writer(self):
        args = arguments()
        args['appearance']['router_model'] = 'mt3000'
        current = {'profiles': [{'id': 'a'}, {'id': 'b'}], 'settings': {'detected_router_model': 'mt3000'}}
        with patch.object(setup_config, 'control_lock', return_value=nullcontext()), \
                patch.object(setup_config, 'inventory', return_value=current), \
                patch('configuration_guard.blocked', return_value=None), \
                patch.object(device_profile, 'detect', return_value='mt6000'), \
                patch.object(setup_config.subprocess, 'run') as writer:
            with self.assertRaisesRegex(ValueError, 'DEVICE-MODEL-MISMATCH'):
                setup_config.save_onboarding(args)
            writer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
