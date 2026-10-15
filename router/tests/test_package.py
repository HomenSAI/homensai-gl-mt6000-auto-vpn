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

    def test_reproducible_ipk_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            first=builder.build(d).read_bytes();second=builder.build(d).read_bytes()
            self.assertEqual(first,second)
            with tarfile.open(fileobj=io.BytesIO(first),mode='r:gz') as outer:
                self.assertEqual(set(outer.getnames()),{'./debian-binary','./control.tar.gz','./data.tar.gz'})
                control=outer.extractfile('./control.tar.gz').read();data=outer.extractfile('./data.tar.gz').read()
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
