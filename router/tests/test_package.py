import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ipk_builder',ROOT/'build_ipk.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    def test_version_and_menu_asset_alignment(self):
        import json,re
        version=re.search(r"^VERSION = '([^']+)'",(ROOT/'files/usr/lib/homensai-vpn/agent.py').read_text(),re.M)[1]
        make=re.search(r'^PKG_VERSION:=(.+)$',(ROOT/'Makefile').read_text(),re.M)[1]
        revision=re.search(r'^PKG_RELEASE:=(.+)$',(ROOT/'Makefile').read_text(),re.M)[1]
        self.assertRegex(revision,r'^[1-9][0-9]*$')
        self.assertEqual(builder.VERSION,version+'-'+revision);self.assertEqual(make,version)
        menu=json.loads((ROOT/'files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text())
        asset=menu['admin/services/homensai-vpn']['action']['path'].split('/')[-1]+'.js'
        source=(ROOT/'files/www/luci-static/resources/view/homensai-vpn'/asset).read_text()
        self.assertIn('loadInventory(0)',source);self.assertNotIn('new form.Map',source)
        self.assertIn('DEGRADED-ON-RESERVE',source)

    def test_actual_archive_references_present_selected_ui_and_legacy_controller(self):
        import json,re
        with tempfile.TemporaryDirectory() as directory:
            package=builder.build(directory).read_bytes()
        with tarfile.open(fileobj=io.BytesIO(package),mode='r:gz') as outer:data=outer.extractfile('./data.tar.gz').read()
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
            menu=json.loads(archive.extractfile('./usr/share/luci/menu.d/luci-app-homensai-vpn.json').read())
            target=menu['admin/services/homensai-vpn']['action']['path'];base='./www/luci-static/resources/view/'
            script=archive.extractfile(base+target+'.js').read().decode()
            for css in set(re.findall(r'\bui[0-9]+\.css\b',script)):self.assertIsNotNone(archive.extractfile(base+'homensai-vpn/'+css))
            controller=archive.extractfile('./usr/lib/lua/luci/controller/homensai_vpn.lua').read().decode();self.assertIn("view('"+target+"')",controller)
            self.assertIn('hv-server-lamp',script);self.assertIn('resolveRouterVpnUrl',script)
    def test_ui_selection_refuses_missing_unsafe_and_mismatched_resources(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);assets=root/'www/luci-static/resources/view/homensai-vpn';assets.mkdir(parents=True)
            menu=root/'usr/share/luci/menu.d/luci-app-homensai-vpn.json';menu.parent.mkdir(parents=True)
            def target(value):menu.write_text(json.dumps({'admin/services/homensai-vpn':{'action':{'path':value}}}))
            target('homensai-vpn/../../private');
            with self.assertRaisesRegex(ValueError,'UI-PATH'):builder.selected_ui(root)
            target('homensai-vpn/dashboard998')
            with self.assertRaisesRegex(ValueError,'UI-MISSING'):builder.selected_ui(root)
            (assets/'dashboard998.js').write_text("load('ui998.css')")
            with self.assertRaisesRegex(ValueError,'CSS-MISSING'):builder.selected_ui(root)
            (assets/'ui998.css').write_text('css')
            controller=root/'usr/lib/lua/luci/controller/homensai_vpn.lua';controller.parent.mkdir(parents=True);controller.write_text("view('homensai-vpn/dashboard1')")
            with self.assertRaisesRegex(ValueError,'LEGACY-UI-MISMATCH'):builder.selected_ui(root)
            controller.write_text("view('homensai-vpn/dashboard998')")
            self.assertEqual(builder.selected_ui(root),('dashboard998.js','ui998.css'))
    def test_binary_font_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'files/fonts').mkdir(parents=True)
            font=b'wOF2\x00\r\n\xff\x00'
            (root/'files/fonts/example.woff2').write_bytes(font)
            (root/'files/example.txt').write_bytes(b'line\r\n')
            with patch.object(builder,'ROOT',root):
                package=builder.build(root/'out').read_bytes()
            with tarfile.open(fileobj=io.BytesIO(package),mode='r:gz') as outer:
                data=outer.extractfile('./data.tar.gz').read()
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
                self.assertEqual(archive.extractfile('./fonts/example.woff2').read(),font)
                self.assertEqual(archive.extractfile('./example.txt').read(),b'line\n')

    def test_retired_generated_dashboards_do_not_enter_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);assets=root/'files/www/luci-static/resources/view/homensai-vpn';assets.mkdir(parents=True)
            for name in ('dashboard.js','dashboard15.js','dashboard997.js','dashboard25.js','dashboard26.js','dashboard27.js','dashboard28.js','ui11.css','ui13.css','ui14.css','ui15.css','ui997.css','client-test.ps1'):(assets/name).write_text('fixture')
            import json
            menu=root/'files/usr/share/luci/menu.d/luci-app-homensai-vpn.json';menu.parent.mkdir(parents=True);menu.write_text(json.dumps({'admin/services/homensai-vpn':{'action':{'path':'homensai-vpn/dashboard997'}}}))
            (assets/'dashboard997.js').write_text("load('ui997.css')")
            with patch.object(builder,'ROOT',root):package=builder.build(root/'out').read_bytes()
            with tarfile.open(fileobj=io.BytesIO(package),mode='r:gz') as outer:data=outer.extractfile('./data.tar.gz').read()
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
                names=[Path(name).name for name in archive.getnames() if archive.getmember(name).isfile()]
            self.assertEqual(sorted(name for name in names if name.endswith(('.js','.css','.ps1'))),['client-test.ps1','dashboard997.js','ui997.css'])

    def test_reproducible_ipk_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            first=builder.build(d).read_bytes();second=builder.build(d).read_bytes()
            self.assertEqual(first,second)
            self.assertEqual(first[9],255)
            with tarfile.open(fileobj=io.BytesIO(first),mode='r:gz') as outer:
                self.assertEqual(set(outer.getnames()),{'./debian-binary','./control.tar.gz','./data.tar.gz'})
                control=outer.extractfile('./control.tar.gz').read();data=outer.extractfile('./data.tar.gz').read()
                self.assertEqual(control[9],255);self.assertEqual(data[9],255)
            with tarfile.open(fileobj=io.BytesIO(control),mode='r:gz') as tar:
                metadata=tar.extractfile('./control').read().decode()
                self.assertIn('Architecture: all',metadata)
                self.assertIn('python3',metadata)
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
                names=tar.getnames()
                self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts for n in names))
                self.assertFalse(any('__pycache__' in n for n in names))
                self.assertEqual(tar.getmember('./usr/libexec/rpcd/homensai-vpn').mode,0o755)
                self.assertEqual(tar.getmember('./etc/config/homensai_vpn').mode,0o644)
                self.assertIn("option enabled '0'",tar.extractfile('./etc/config/homensai_vpn').read().decode())
                style=ROOT/'files/www/luci-static/resources/view/homensai-vpn/style'
                for resource in style.rglob('*'):
                    if resource.is_file():
                        member='./'+resource.relative_to(ROOT/'files').as_posix()
                        self.assertEqual(tar.extractfile(member).read(),resource.read_bytes())


if __name__=='__main__':unittest.main()
