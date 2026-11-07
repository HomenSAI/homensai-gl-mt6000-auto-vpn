"""Keeps the version honest. The product source (router/files, the page sources and build scripts) has a fingerprint recorded in
VERSION.json. If the source changed and the fingerprint did not, the version is stale: this script advances the prerelease
number (0.9.0-alphaN -> alphaN+1, package revision 1), rewrites every version literal, rebuilds the page so that the version shown
on the pages is the new one, and records the new fingerprint.

  python scripts/bump-version.py --check    exit 1 and say so when the source changed without a version change
  python scripts/bump-version.py            bump when needed (does nothing when the version is current)
  python scripts/bump-version.py --fingerprint-only   record the fingerprint without changing the version (after a release build)
  python scripts/bump-version.py --help     print this usage and exit without touching anything

Arguments are parsed strictly: an unknown or misspelled argument exits non-zero BEFORE anything is read or written (an unknown
argument used to fall through to the bump mode and advanced the version by accident).

Offline: reads and writes files in this checkout only."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'VERSION.json'
# router/ui holds the editable page sources (views.js, bridge.js, advisor.js, mockup CSS): a change there is a product change.
SOURCE_DIRS = ('router/files', 'router/ui')
SOURCE_GLOBS = ('router/*.inc.js', 'router/*.py', 'router/*.css', 'router/*.lua', 'qa/export_lazy_titles.js', 'qa/export_documentation.js')
SKIP_PARTS = {'__pycache__', 'dist', 'tests'}
# Files that carry the version as a literal (everything else, such as docs and release notes, is written by hand at release time).
LITERAL_FILES = ('router/Makefile', 'router/build_ipk.py', 'router/files/usr/lib/homensai-vpn/agent.py',
                 'router/files/usr/lib/lua/luci/controller/homensai_vpn.lua', 'router-test-kit/02-install.sh',
                 'router-test-kit/03-verify.sh', 'lab/storage_adversity_guest.py',
                 'router/files/usr/lib/homensai-vpn/lua/version.lua',
                 # the page preview fixture reports the current version, or the page tests see a version mismatch
                 'qa/ui-preview/fixture-pair.js')


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


KIT = 'router-test-kit/02-install.sh'
UNBUILT_SHA = '0'*64


def mark_kit_unavailable():
    """Hash and size of the previous package never stay next to a new version: zero them (the kit then stops with
    KIT-UNAVAILABLE) until the release record fills both from the built package."""
    path = ROOT/KIT
    text = path.read_text(encoding='utf-8')
    updated, sha = re.subn(r'(?m)^EXPECTED_SHA=.*$', 'EXPECTED_SHA='+UNBUILT_SHA, text)
    updated, size = re.subn(r'(?m)^EXPECTED_SIZE=.*$', 'EXPECTED_SIZE=0', updated)
    if sha != 1 or size != 1:
        raise SystemExit('VERSION-KIT-LITERALS')
    with path.open('w', encoding='utf-8', newline='') as stream:
        stream.write(updated)


def shipped_lazy_modules():
    """The optional page modules the package builder actually selects, as VERSION.json names them."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT/'router'))
    try:
        from build_ipk import selected_source_files
    finally:
        sys.path.pop(0)
    lazy = 'www/luci-static/resources/homensai-vpn/'
    return sorted('homensai-vpn/'+name[len(lazy):] for name, _, _ in selected_source_files(ROOT/'router/files')
                  if name.startswith(lazy) and re.fullmatch(r'(?:help|pick)[0-9]+\.js', name[len(lazy):]))


def next_ui(app):
    """Each release ships its page under a new file name, so browsers never run a cached older page."""
    build = ROOT/'router/build_sidebar_ui.py'
    text = build.read_bytes().decode('utf-8')
    old_js, old_css = app['ui_module'], app['ui_stylesheet']
    js = re.fullmatch(r'dashboard([0-9]+)', old_js); css = re.fullmatch(r'ui([0-9]+)\.css', old_css)
    if not js or not css or text.count("UI_MODULE='%s'" % old_js) != 1 or text.count("'%s'" % old_css) != 2:
        raise SystemExit('UI-MODULE-NAME-UNVERIFIED: VERSION.json and router/build_sidebar_ui.py disagree')
    new_js, new_css = 'dashboard%d' % (int(js.group(1))+1), 'ui%d.css' % (int(css.group(1))+1)
    text = text.replace("UI_MODULE='%s'" % old_js, "UI_MODULE='%s'" % new_js).replace("'%s'" % old_css, "'%s'" % new_css)
    build.write_bytes(text.encode('utf-8'))
    return new_js, new_css


def parse_arguments(argv):
    """Strict parsing: --help exits 0, any unknown argument exits 2; both happen before any file is read or written."""
    parser = argparse.ArgumentParser(prog='bump-version.py', allow_abbrev=False,
                                     description='Keeps the version honest (see the module docstring). Without arguments: the '
                                                 'deliberate release bump (advances the prerelease number when the source changed).')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='exit 1 when the source changed without a version change; writes nothing')
    mode.add_argument('--fingerprint-only', action='store_true',
                      help='record the source fingerprint in VERSION.json without changing the version')
    return parser.parse_args(argv)


def main(argv):
    arguments = parse_arguments(argv)
    data = load()
    app = data['application']
    current = fingerprint(app['version'], app['package_version'])
    stale = app.get('source_fingerprint') != current
    if arguments.check:
        if stale:
            print('VERSION-STALE: the product source changed but the version did not. Run: python scripts/bump-version.py')
            return 1
        print('VERSION-CURRENT', app['package_version'])
        return 0
    if arguments.fingerprint_only:
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
    ui_module, ui_stylesheet = next_ui(app)
    app.update(ui_module=ui_module, ui_stylesheet=ui_stylesheet)
    app.update(version=new_version, package_revision=1, package_version=new_package, release_tag='v'+new_version,
               artifact='homensai-auto-vpn_%s_all.ipk' % new_package, sha256='0'*64)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    # The page shows the version it was built with: rebuild it, then record the fingerprint of the rebuilt source.
    subprocess.run([sys.executable, str(ROOT/'router/build_sidebar_ui.py')], check=True, stdout=subprocess.DEVNULL)
    data = load()
    # The new version has no built package yet: the install kit says so instead of keeping the previous hash and size.
    mark_kit_unavailable()
    # Declare exactly the optional modules the package ships (the ones the selected page loads), never a generated module
    # the page does not reference (pick*.js is generated for the legacy reference only).
    data['application']['ui_lazy_modules']=shipped_lazy_modules()
    if not any(re.fullmatch(r'homensai-vpn/help[0-9]+\.js',name) for name in data['application']['ui_lazy_modules']):
        raise SystemExit('UI-LAZY-MODULE-MISSING')
    data['application']['source_fingerprint'] = fingerprint(new_version, new_package)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('VERSION-BUMPED %s -> %s (package %s); sha256 is recorded after the package build' % (old_version, new_version, new_package))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
