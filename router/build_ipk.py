"""Reproducible interpreted OpenWrt 21.02 .ipk (outer gzip/tar, not Debian ar)."""
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
import tarfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from package_hooks import scripts as lifecycle_scripts

ROOT = Path(__file__).parent
VERSION = '2.1.0-alpha6-1'
NAME = 'homensai-auto-vpn'
EXECUTABLE = {'etc/init.d/homensai-vpn', 'usr/libexec/rpcd/homensai-vpn', 'usr/sbin/homensai-vpn-emergency',
              'usr/sbin/homensai-vpn-integrity'}


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
    # Python 3.14+ changed gzip.compress's default level from 9 to 6.
    # Pin it so the Windows builder and the OpenWrt/CI runtimes emit one IPK.
    compressed=bytearray(gzip.compress(raw.getvalue(), compresslevel=9, mtime=0))
    # Python 3.11 may expose zlib's host OS byte; 3.9 writes unknown (255).
    # Normalize all nested gzip headers for cross-runtime reproducibility.
    compressed[9]=255
    return bytes(compressed)


def selected_ui(source):
    base=source/'www/luci-static/resources/view/homensai-vpn'
    if not base.exists():return None,None
    menu=source/'usr/share/luci/menu.d/luci-app-homensai-vpn.json'
    try:target=json.loads(menu.read_text(encoding='utf8'))['admin/services/homensai-vpn']['action']['path']
    except (OSError,ValueError,KeyError,TypeError):raise ValueError('PACKAGE-UI-MENU') from None
    if not isinstance(target,str) or not re.fullmatch(r'homensai-vpn/dashboard[0-9]+',target):raise ValueError('PACKAGE-UI-PATH')
    name=target.split('/')[-1]+'.js';script=base/name
    if not script.is_file() or script.is_symlink():raise ValueError('PACKAGE-UI-MISSING')
    css=set(re.findall(r'\bui[0-9]+\.css\b',script.read_text(encoding='utf8')))
    if len(css)!=1:raise ValueError('PACKAGE-UI-CSS-AMBIGUOUS')
    stylesheet=next(iter(css))
    if not (base/stylesheet).is_file() or (base/stylesheet).is_symlink():raise ValueError('PACKAGE-UI-CSS-MISSING')
    controller=source/'usr/lib/lua/luci/controller/homensai_vpn.lua'
    if controller.exists() and "view('"+target+"')" not in controller.read_text(encoding='utf8'):raise ValueError('PACKAGE-LEGACY-UI-MISMATCH')
    return name,stylesheet

# Design work for a future multi-channel cascade: kept in the source tree with its tests, never imported by the
# installed service, so it is not shipped to the router.
NOT_SHIPPED=frozenset('usr/lib/homensai-vpn/'+name+'.py' for name in ('cascade_model','cascade_executor','candidate_runtime','configuration_migrations'))

def selected_files(source=None):
    """The payload: the selected source files plus the integrity manifest (both builders, custom IPK and SDK)."""
    return with_manifest(selected_source_files(source))


def selected_source_files(source=None):
    files = []
    source=Path(source) if source is not None else ROOT/'files'
    selected_js,selected_css=selected_ui(source)
    lazy_root='www/luci-static/resources/homensai-vpn/'
    lazy_selected=set()
    if selected_js:
        script=(source/'www/luci-static/resources/view/homensai-vpn'/selected_js).read_text(encoding='utf8')
        references=set(re.findall(r"\bLAZY_HELP_NAME='(homensai-vpn\.help[0-9]+)'",script))
        for reference in references:
            name=reference.split('.')[-1]+'.js';path=source/lazy_root/name
            if not path.is_file() or path.is_symlink():raise ValueError('PACKAGE-LAZY-UI-MISSING')
            lazy_selected.add(name)
        if 'LAZY_HELP_NAME=' in script and len(references)!=1:raise ValueError('PACKAGE-LAZY-UI-AMBIGUOUS')
        # The server-pick panel (2.1.0) is a second optional module, also named per release: only the referenced one ships.
        picks=set(re.findall(r"\bLAZY_PICK_NAME='(homensai-vpn\.pick[0-9]+)'",script))
        for reference in picks:
            name=reference.split('.')[-1]+'.js';path=source/lazy_root/name
            if not path.is_file() or path.is_symlink():raise ValueError('PACKAGE-LAZY-UI-MISSING')
            lazy_selected.add(name)
        if 'LAZY_PICK_NAME=' in script and len(picks)!=1:raise ValueError('PACKAGE-LAZY-UI-AMBIGUOUS')
    for path in source.rglob('*'):
        if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts:
            continue
        name = path.relative_to(source).as_posix()
        if name in NOT_SHIPPED:continue
        if name.startswith(lazy_root) and '/' not in name[len(lazy_root):] and re.fullmatch(r'(?:help|pick)[0-9]+\.js',path.name) and path.name not in lazy_selected:continue
        ui_root='www/luci-static/resources/view/homensai-vpn/'
        if name.startswith(ui_root) and '/' not in name[len(ui_root):]:
            if re.fullmatch(r'dashboard[0-9]*\.js',path.name) and path.name!=selected_js:continue
            if re.fullmatch(r'ui[0-9]+\.css',path.name) and path.name!=selected_css:continue
        if '..' in Path(name).parts:
            raise ValueError('unsafe package member')
        payload = path.read_bytes()
        if '/style/' not in name and path.suffix.lower() not in ('.woff2','.woff','.ttf','.otf','.png','.jpg','.jpeg','.ico','.so'):
            payload = payload.replace(b'\r\n', b'\n')
        files.append((name, payload, 0o755 if name in EXECUTABLE else 0o644))
    return files


# Integrity manifest (TODO item 15, docs/architecture/INTEGRITY-MATRIX-2026-11-01.ru.md): a per-file sha256 + mode
# list of the payload, read by /usr/sbin/homensai-vpn-integrity at every service start. opkg 21.02 keeps only file names in
# /usr/lib/opkg/info/<pkg>.list (checksums only for conffiles), so a damaged installed file is invisible to it.
# Conffiles (the owner's config) are listed with mode only, never with a hash: they must never be auto-restored.
MANIFEST_PATH='usr/lib/homensai-vpn/integrity.sha256'
CONFFILES=('etc/config/homensai_vpn',)

def payload_manifest(files,version=VERSION):
    """Text of the manifest: header, then '<sha256> <octal mode> /<path>' per shipped file, sorted by path."""
    lines=['# homensai-auto-vpn payload manifest v1','# version '+version]
    for name,payload,mode in sorted(files):
        if name==MANIFEST_PATH:raise ValueError('PACKAGE-MANIFEST-SELF')
        if not re.fullmatch(r'[A-Za-z0-9_.+/-]+',name) or '..' in name:raise ValueError('PACKAGE-MANIFEST-PATH')
        digest='-'*64 if name in CONFFILES else hashlib.sha256(payload).hexdigest()
        lines.append('%s %04o /%s'%(digest,mode,name))
    return ('\n'.join(lines)+'\n').encode()

def with_manifest(files,version=VERSION):
    """files plus the manifest member."""
    return list(files)+[(MANIFEST_PATH,payload_manifest(files,version),0o644)]


def build(output=None):
    destination = Path(output) if output else ROOT/'dist'
    destination.mkdir(parents=True, exist_ok=True)
    files = selected_files()
    data = archive(files)
    # opkg reports Installed-Size as unpacked bytes, not the size of the compressed archive.
    unpacked = sum(len(payload) for _, payload, _ in files)
    control = ('Package: %s\nVersion: %s\nArchitecture: all\n'
               'Maintainer: HomenSAI <info@homensai.com>\nLicense: LicenseRef-HomenSAI-Personal-Commercial-1.0\n'
               'Depends: python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd, luci-base, ca-bundle\n'
               'Description: HomenSAI VPN monitor; bounded controlled native trials; optional speed tests\n'
               'Source: https://homensai.com\nInstalled-Size: %d\n' % (NAME, VERSION, unpacked)).encode()
    hooks=lifecycle_scripts()
    preinst=hooks['preinst'].encode();postinst=hooks['postinst'].encode();prerm=hooks['prerm'].encode()
    controls = archive([('control', control, 0o644), ('conffiles', b'/etc/config/homensai_vpn\n', 0o644),
                        ('preinst', preinst, 0o755), ('postinst', postinst, 0o755), ('prerm', prerm, 0o755)])
    package = archive([('debian-binary', b'2.0\n', 0o644), ('control.tar.gz', controls, 0o644), ('data.tar.gz', data, 0o644)])
    path = destination/('%s_%s_all.ipk' % (NAME, VERSION))
    path.write_bytes(package)
    path.with_suffix('.ipk.sha256').write_text(hashlib.sha256(package).hexdigest()+'  '+path.name+'\n')
    print(str(path), len(package), 'bytes', hashlib.sha256(package).hexdigest())
    return path


if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else None)
