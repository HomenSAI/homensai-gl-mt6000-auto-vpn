"""Review R3-06: PRINCIPLES-SCIENCE names the real configuration options of the return pause (recovery_flap_*),
not the internal policy fields, and the RU and EN texts stay in step."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'router' / 'files' / 'usr' / 'lib' / 'homensai-vpn'))


class PrinciplesConfigNames(unittest.TestCase):
    def test_flap_options_are_the_configuration_names(self):
        source = (ROOT / 'router/files/usr/lib/homensai-vpn/recovery_settings.py').read_text(encoding='utf-8')
        fields = re.search(r"^FLAP_FIELDS=\(([^)]*)\)", source, re.M).group(1)
        options = {'recovery_' + name.strip(" '") for name in fields.split(',')}
        inventory = (ROOT / 'router/files/usr/lib/homensai-vpn/inventory.lua').read_text(encoding='utf-8')
        for lang in ('en', 'ru'):
            text = (ROOT / ('docs/PRINCIPLES-SCIENCE.%s.md' % lang)).read_text(encoding='utf-8')
            named = set(re.findall(r'`(recovery_flap_[a-z]+)`', text))
            self.assertGreaterEqual(named, {'recovery_flap_model', 'recovery_flap_limit', 'recovery_flap_window'}, lang)
            self.assertLessEqual(named, options, lang)
            for option in named:self.assertIn('main.' + option + '=', inventory, option)
            self.assertNotIn('(`flap_model` = `halflife`)', text, lang)
            self.assertNotIn('(`flap_limit`, `flap_window`)', text, lang)
        en = (ROOT / 'docs/PRINCIPLES-SCIENCE.en.md').read_text(encoding='utf-8')
        ru = (ROOT / 'docs/PRINCIPLES-SCIENCE.ru.md').read_text(encoding='utf-8')
        self.assertEqual(sorted(re.findall(r'`recovery_[a-z_]+`', en)), sorted(re.findall(r'`recovery_[a-z_]+`', ru)))


if __name__ == '__main__':
    unittest.main()
