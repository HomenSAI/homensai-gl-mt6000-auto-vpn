"""Reproducible interpreted OpenWrt 21.02 .ipk (outer gzip/tar, not Debian ar)."""
import gzip
import hashlib
import io
import re
from pathlib import Path
import tarfile

ROOT = Path(__file__).parent
VERSION = '0.7.0-alpha2-1'
NAME = 'homensai-auto-vpn'
EXECUTABLE = {'etc/init.d/homensai-vpn', 'usr/libexec/rpcd/homensai-vpn'}


def archive(items):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.GNU_FORMAT) as tar:
        directories = set()
        for name, _, _ in items:
            parent = Path(name).parent
            while parent.as_posix() != '.':
                directories.add(parent.as_posix())
                parent = parent.parent
        for directory in sorted(directories, key=lambda value: (value.count('/'), value)):
            info = tarfile.TarInfo('./'+directory+'/')
            info.type = tarfile.DIRTYPE
            info.mode, info.mtime = 0o755, 0
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            tar.addfile(info)
        for name, payload, mode in sorted(items):
            info = tarfile.TarInfo('./'+name)
            info.size, info.mode, info.mtime = len(payload), mode, 0
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            tar.addfile(info, io.BytesIO(payload))
    compressed=bytearray(gzip.compress(raw.getvalue(), mtime=0))
    # Python 3.11 may expose zlib's host OS byte; 3.9 writes unknown (255).
    # Normalize all nested gzip headers for cross-runtime reproducibility.
    compressed[9]=255
    return bytes(compressed)


def build(output=None):
    destination = Path(output) if output else ROOT/'dist'
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    for path in (ROOT/'files').rglob('*'):
        if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts:
            continue
        name = path.relative_to(ROOT/'files').as_posix()
        ui_root='www/luci-static/resources/view/homensai-vpn/'
        if name.startswith(ui_root) and '/' not in name[len(ui_root):]:
            if re.fullmatch(r'dashboard[0-9]*\.js',path.name) and path.name!='dashboard25.js':continue
            if re.fullmatch(r'ui[0-9]+\.css',path.name) and path.name!='ui13.css':continue
        if '..' in Path(name).parts:
            raise ValueError('unsafe package member')
        payload = path.read_bytes()
        if '/style/' not in name and path.suffix.lower() not in ('.woff2','.woff','.ttf','.otf','.png','.jpg','.jpeg','.ico'):
            payload = payload.replace(b'\r\n', b'\n')
        files.append((name, payload, 0o755 if name in EXECUTABLE else 0o644))
    data = archive(files)
    control = ('Package: %s\nVersion: %s\nArchitecture: all\n'
               'Maintainer: HomenSAI <info@homensai.com>\nLicense: MIT\n'
               'Depends: python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd, luci-base, ca-bundle\n'
               'Description: HomenSAI VPN monitor; bounded controlled native trials; optional speed tests\n'
               'Source: https://homensai.com\nInstalled-Size: %d\n' % (NAME, VERSION, len(data))).encode()
    postinst = b'''#!/bin/sh
[ -n "$IPKG_INSTROOT" ] && exit 0
mkdir -p /etc/homensai-vpn
chmod 0700 /etc/homensai-vpn
/usr/bin/python3 -c "from pathlib import Path; p=Path('/usr/lib/homensai-vpn/__pycache__'); [x.unlink() for x in p.glob('*.pyc') if x.is_file() and not x.is_symlink()]"
/etc/init.d/homensai-vpn enable
/etc/init.d/homensai-vpn restart
/etc/init.d/rpcd reload
rm -f /tmp/luci-indexcache
exit 0
'''
    prerm = b'''#!/bin/sh
[ -n "$IPKG_INSTROOT" ] && exit 0
/etc/init.d/homensai-vpn stop
/etc/init.d/homensai-vpn disable
exit 0
'''
    controls = archive([('control', control, 0o644), ('conffiles', b'/etc/config/homensai_vpn\n', 0o644),
                        ('postinst', postinst, 0o755), ('prerm', prerm, 0o755)])
    package = archive([('debian-binary', b'2.0\n', 0o644), ('control.tar.gz', controls, 0o644), ('data.tar.gz', data, 0o644)])
    path = destination/('%s_%s_all.ipk' % (NAME, VERSION))
    path.write_bytes(package)
    path.with_suffix('.ipk.sha256').write_text(hashlib.sha256(package).hexdigest()+'  '+path.name+'\n')
    print(str(path), len(package), 'bytes', hashlib.sha256(package).hexdigest())
    return path


if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else None)
