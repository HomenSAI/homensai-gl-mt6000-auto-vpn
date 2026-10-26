"""Keeps the version honest. The product source (router/files, the page sources and build scripts) has a fingerprint recorded in
VERSION.json. If the source changed and the fingerprint did not, the version is stale: this script advances the prerelease
number (0.9.0-alphaN -> alphaN+1, package revision 1), rewrites every version literal, rebuilds the page so that the version shown
on the pages is the new one, and records the new fingerprint.

  python scripts/bump-version.py --check    exit 1 and say so when the source changed without a version change
  python scripts/bump-version.py            bump when needed (does nothing when the version is current)
  python scripts/bump-version.py --fingerprint-only   record the fingerprint without changing the version (after a release build)

Offline: reads and writes files in this checkout only."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'VERSION.json'
SOURCE_DIRS = ('router/files',)
SOURCE_GLOBS = ('router/*.inc.js', 'router/*.py', 'router/*.css', 'router/*.lua')
SKIP_PARTS = {'__pycache__', 'dist', 'tests'}
# Files that carry the version as a literal (everything else, such as docs and release notes, is written by hand at release time).
LITERAL_FILES = ('router/Makefile', 'router/build_ipk.py', 'router/files/usr/lib/homensai-vpn/agent.py',
                 'router/files/usr/lib/lua/luci/controller/homensai_vpn.lua', 'router-test-kit/02-install.sh',
                 'router-test-kit/03-verify.sh', 'lab/storage_adversity_guest.py')


def source_files():
    found = set()
    for directory in SOURCE_DIRS:
        found.update(path for path in (ROOT/directory).rglob('*') if path.is_file())
    for pattern in SOURCE_GLOBS:
        found.update(path for path in ROOT.glob(pattern) if path.is_file())
    # Sort by the POSIX text of the relative path: Windows sorts Path objects case-insensitively, Linux does not.
    return sorted((path for path in found if not SKIP_PARTS & set(path.relative_to(ROOT).parts) and path.suffix != '.pyc'),
                  key=lambda path: path.relative_to(ROOT).as_posix())


def fingerprint(version, package):
    """SHA-256 over the product source with the current version strings neutralised, so that bumping the version does not change it."""
    digest = hashlib.sha256()
    for path in source_files():
        data = path.read_bytes().replace(b'\r\n', b'\n')
        for text in (package, version):
            data = data.replace(text.encode(), b'@VERSION@')
        digest.update(str(path.relative_to(ROOT)).replace('\\', '/').encode() + b'\0' + data + b'\0')
    return digest.hexdigest()


def load():
    return json.loads(MANIFEST.read_text(encoding='utf-8-sig'))


def next_version(version):
    match = re.fullmatch(r'([0-9]+\.[0-9]+\.[0-9]+)-(alpha|beta)([0-9]+)', version)
    if not match:
        raise SystemExit('VERSION-NOT-A-PRERELEASE: advance the version by hand')
    return '%s-%s%d' % (match.group(1), match.group(2), int(match.group(3))+1)


def rewrite(old_version, old_package, new_version, new_package):
    for name in LITERAL_FILES:
        path = ROOT/name
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        updated = text.replace(old_package, new_package).replace(old_version, new_version)
        if name == 'router/Makefile':
            updated, count = re.subn(r'(?m)^PKG_RELEASE:=[1-9][0-9]*$', 'PKG_RELEASE:=1', updated)
            if count != 1:
                raise ValueError('VERSION-MAKEFILE-REVISION')
        if updated != text:
            with path.open('w', encoding='utf-8', newline='') as stream:
                stream.write(updated)


def main(argv):
    data = load()
    app = data['application']
    current = fingerprint(app['version'], app['package_version'])
    stale = app.get('source_fingerprint') != current
    if '--check' in argv:
        if stale:
            print('VERSION-STALE: the product source changed but the version did not. Run: python scripts/bump-version.py')
            return 1
        print('VERSION-CURRENT', app['package_version'])
        return 0
    if '--fingerprint-only' in argv:
        app['source_fingerprint'] = current
        MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        print('FINGERPRINT-RECORDED', current[:12])
        return 0
    if not stale:
        print('VERSION-CURRENT', app['package_version'])
        return 0
    old_version, old_package = app['version'], app['package_version']
    new_version = next_version(old_version)
    new_package = new_version+'-1'
    rewrite(old_version, old_package, new_version, new_package)
    app.update(version=new_version, package_revision=1, package_version=new_package, release_tag='v'+new_version,
               artifact='homensai-auto-vpn_%s_all.ipk' % new_package, sha256='0'*64)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    # The page shows the version it was built with: rebuild it, then record the fingerprint of the rebuilt source.
    subprocess.run([sys.executable, str(ROOT/'router/build_sidebar_ui.py')], check=True, stdout=subprocess.DEVNULL)
    data = load()
    data['application']['source_fingerprint'] = fingerprint(new_version, new_package)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('VERSION-BUMPED %s -> %s (package %s); sha256 is recorded after the package build' % (old_version, new_version, new_package))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
