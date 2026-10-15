"""Reproducible interpreted OpenWrt 21.02 .ipk (outer gzip/tar, not Debian ar)."""
import gzip
import hashlib
import io
from pathlib import Path
import tarfile

ROOT = Path(__file__).parent
VERSION = '0.5.0-alpha5-1'
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
    return gzip.compress(raw.getvalue(), mtime=0)


def build(output=None):
    destination = Path(output) if output else ROOT/'dist'
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    for path in (ROOT/'files').rglob('*'):
        if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts:
            continue
        name = path.relative_to(ROOT/'files').as_posix()
        if '..' in Path(name).parts:
            raise ValueError('unsafe package member')
        payload = path.read_bytes()
        if '/style/' not in name and path.suffix.lower() not in ('.woff2','.woff','.ttf','.otf','.png','.jpg','.jpeg','.ico'):
            payload = payload.replace(b'\r\n', b'\n')
        files.append((name, payload, 0o755 if name in EXECUTABLE else 0o644))
    data = archive(files)
    control = ('Package: %s\nVersion: %s\nArchitecture: all\n'
               'Maintainer: HomenSAI <info@homensai.com>\n'
               'Depends: python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd, luci-base, ca-bundle\n'
               'Description: HomenSAI Auto VPN native monitor alpha; route changes disabled\n'
               'Source: https://homensai.com\nInstalled-Size: %d\n' % (NAME, VERSION, len(data))).encode()
    postinst = b'''#!/bin/sh
[ -n "$IPKG_INSTROOT" ] && exit 0
mkdir -p /etc/homensai-vpn
chmod 0700 /etc/homensai-vpn
/etc/init.d/homensai-vpn enable
/etc/init.d/homensai-vpn restart
if ! ubus -v list 'homensai-vpn' | grep -q 'native_confirm'; then
    /etc/init.d/rpcd reload
fi
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
