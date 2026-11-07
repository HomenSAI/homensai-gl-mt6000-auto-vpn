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

    def test_help_and_unknown_arguments_never_bump(self):
        """07.11.2026: `bump-version.py --help` advanced the version twice (an unknown argument fell through to the bump).
        Now --help exits 0 and an unknown argument exits non-zero, both before any file is read or written. Runs on a copy
        of the script in a scratch tree, so the real checkout can never be bumped by this test."""
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            shutil.copyfile(ROOT/'scripts/bump-version.py', root/'scripts/bump-version.py')
            manifest = root/'VERSION.json'
            original = '{"application": {"version": "9.9.9-alpha1", "package_version": "9.9.9-alpha1-1"}}\n'
            manifest.write_text(original, encoding='utf-8')
            before = sorted(str(path.relative_to(root)) for path in root.rglob('*'))
            cases = [(['--help'], 0), (['-h'], 0), (['--bogus'], 2), (['help'], 2), (['--fingerprint-onl'], 2),
                     (['--chec'], 2), (['--check', '--fingerprint-only'], 2), (['--check', 'extra'], 2)]
            for argv, code in cases:
                with self.subTest(argv=argv):
                    result = subprocess.run([sys.executable, '-B', str(root/'scripts/bump-version.py')]+argv,
                                            capture_output=True, text=True, cwd=str(root))
                    self.assertEqual(result.returncode, code, result.stdout+result.stderr)
                    if code == 0:
                        self.assertIn('usage:', result.stdout)
                    self.assertNotIn('VERSION-BUMPED', result.stdout)
                    self.assertEqual(manifest.read_text(encoding='utf-8'), original)
                    self.assertEqual(sorted(str(path.relative_to(root)) for path in root.rglob('*')), before)

    def test_manifest_agrees_with_literals(self):
        result = subprocess.run([sys.executable, str(ROOT/'qa/check_versions.py')], capture_output=True, text=True)
        self.assertIn('"result": "PASS"', result.stdout)


def load(name, relative):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IDENTITY_FILES = ('VERSION.json', 'router/Makefile', 'router/build_ipk.py', 'router/files/usr/lib/homensai-vpn/agent.py',
                  'router/files/usr/lib/homensai-vpn/lua/version.lua', 'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json',
                  'router/files/usr/lib/lua/luci/controller/homensai_vpn.lua', 'router/files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json',
                  'router/files/usr/libexec/rpcd/homensai-vpn', 'router-test-kit/02-install.sh', 'router-test-kit/03-verify.sh')


class ReleaseIdentityTests(unittest.TestCase):
    """Audit 06.11.2026: F-10 (kit version/hash/size), F-94 (fingerprint covers router/ui), F-95 (declared lazy modules),
    F-96 (identities a substitution could change unnoticed)."""

    def copy_tree(self, root):
        import json
        import shutil
        data = json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
        view = 'router/files/www/luci-static/resources/view/homensai-vpn/'
        for name in IDENTITY_FILES+(view+data['ui_module']+'.js', view+data['ui_stylesheet']):
            target = root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)

    def test_substituted_identities_are_refused(self):
        import tempfile
        from unittest.mock import patch
        checker = load('check_versions_identity', 'qa/check_versions.py')
        shipped = checker.lazy_selection(ROOT)
        mutations = [
            ('router/build_ipk.py', "NAME = 'homensai-auto-vpn'", "NAME = 'homensai-auto-vpm'"),
            ('router/Makefile', 'PKG_NAME:=homensai-auto-vpn', 'PKG_NAME:=other-package'),
            ('router/files/usr/lib/homensai-vpn/lua/version.lua', "return '", "return '9"),
            ('router/files/usr/lib/lua/luci/controller/homensai_vpn.lua', '-- UI resource for ', '-- UI resource for 9'),
            ('router/files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json', '"luci-app-homensai-vpn": {', '"luci-app-other": {'),
            ('router/files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json', '"homensai-vpn": [\n          "status"', '"system": [\n          "status"'),
            ('router-test-kit/02-install.sh', 'EXPECTED_VERSION=', 'EXPECTED_VERSION=0.0.1-alpha1-1#'),
            ('router-test-kit/02-install.sh', 'EXPECTED_SIZE=0', 'EXPECTED_SIZE=1519009'),
            ('router-test-kit/02-install.sh', 'EXPECTED_SHA=0000', 'EXPECTED_SHA=2be1'),
            ('router-test-kit/03-verify.sh', 'EXPECTED_VERSION=', 'EXPECTED_VERSION=9'),
            ('VERSION.json', '"homensai-vpn/help', '"homensai-vpn/pick999.js", "homensai-vpn/help'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_tree(root)
            with patch.object(checker, 'lazy_selection', return_value=shipped):
                self.assertEqual(checker.validate(root/'VERSION.json', root)['result'], 'PASS')
                for name, old, new in mutations + [('page', "HV_AGENT='", "HV_AGENT='9")]:
                    if name == 'page':
                        import json
                        app = json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
                        name = 'router/files/www/luci-static/resources/view/homensai-vpn/'+app['ui_module']+'.js'
                    path = root/name
                    original = path.read_bytes()
                    text = original.decode('utf-8')
                    self.assertEqual(text.count(old), 1, (name, old))
                    path.write_bytes(text.replace(old, new).encode('utf-8'))
                    try:
                        with self.subTest(name=name, old=old), self.assertRaises((ValueError, KeyError)):
                            checker.validate(root/'VERSION.json', root)
                    finally:
                        path.write_bytes(original)

    def test_declared_lazy_modules_are_the_shipped_ones(self):
        import json
        checker = load('check_versions_lazy', 'qa/check_versions.py')
        declared = json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']['ui_lazy_modules']
        self.assertEqual(sorted(declared), checker.lazy_selection(ROOT))
        self.assertTrue(any(name.startswith('homensai-vpn/help') for name in declared))

    def test_fingerprint_covers_the_editable_ui_sources(self):
        import tempfile
        from unittest.mock import patch
        module = load('version_bump_ui', 'scripts/bump-version.py')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('router/files/a.txt', 'router/ui/views.js', 'router/ui/mockup/core.css'):
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                (root/name).write_text('x\n')
            with patch.object(module, 'ROOT', root):
                first = module.fingerprint('1.0.0-alpha1', '1.0.0-alpha1-1')
                (root/'router/ui/views.js').write_text('changed\n')
                second = module.fingerprint('1.0.0-alpha1', '1.0.0-alpha1-1')
                (root/'router/ui/mockup/core.css').write_text('changed\n')
                third = module.fingerprint('1.0.0-alpha1', '1.0.0-alpha1-1')
        self.assertNotEqual(first, second)
        self.assertNotEqual(second, third)

    def test_bump_marks_the_kit_unavailable(self):
        import tempfile
        from unittest.mock import patch
        module = load('version_bump_kit', 'scripts/bump-version.py')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kit = root/'router-test-kit/02-install.sh'
            kit.parent.mkdir(parents=True)
            kit.write_text('EXPECTED_SHA='+'ab'*32+'\nEXPECTED_SIZE=1519009\nEXPECTED_VERSION=2.1.0-alpha10-1\n')
            with patch.object(module, 'ROOT', root):
                module.mark_kit_unavailable()
            self.assertEqual(kit.read_text(), 'EXPECTED_SHA='+'0'*64+'\nEXPECTED_SIZE=0\nEXPECTED_VERSION=2.1.0-alpha10-1\n')

    def test_unbuilt_kit_refuses_before_anything_else(self):
        import shutil
        import tempfile
        if not shutil.which('sh'):
            self.skipTest('POSIX sh is needed to run the kit')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'kit').mkdir()
            (root/'kit/fingerprint.before').write_text('baseline\n')
            package = root/'homensai-auto-vpn_test_all.ipk'
            package.write_bytes(b'not a package')
            script = root/'02-install.sh'
            script.write_bytes((ROOT/'router-test-kit/02-install.sh').read_bytes().replace(b'\r\n', b'\n'))
            env = dict(__import__('os').environ, HOMENSAI_KIT=str(root/'kit'), HOMENSAI_KEYS=str(root/'keys'),
                       HOMENSAI_LOCAL_KEYS=str(root/'keys.local'), HOMENSAI_CHAIN=str(root/'chain.jsonl'), PATH='/usr/bin:/bin')
            result = subprocess.run(['sh', str(script), str(package)], cwd=str(root), capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
        self.assertIn('KIT-UNAVAILABLE', result.stderr)


if __name__ == '__main__':
    unittest.main()
