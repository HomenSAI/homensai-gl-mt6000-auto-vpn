"""Signed test evidence of a release: a manifest that cannot be quietly edited. Guide: docs/architecture/SIGNING-2026-11-03.ru.md, section 12.

  report_manifest.py build  --out DIR --source-commit <40 hex> [--package-version V] [--root REPO] [--copy] [--spec FILE]
                            [--add category=glob ...] [--require category ...]
        Hash the test evidence of a release (test history, CI receipts, soak reports, queue report, formal/TLC/trace results)
        and write DIR/EVIDENCE-MANIFEST.json. No secret is involved and nothing is signed yet.
  keytool.py sign-release ... --evidence DIR
        The same TOTP gate as every signature: DIR/EVIDENCE-MANIFEST.json.sig (usign, same key as the chain entry) and the
        manifest's SHA-256 inside the signed chain entry (optional field evidence_sha256).
  report_manifest.py verify DIR [--root REPO] [--base DIR]
        No secret needed. Checks the manifest format, its signature, its link in the release chain and every file; every problem
        is printed with the file name (EVIDENCE-FILE-CHANGED / -MISSING / -EXTRA ...). Exit 0 = PASS, 1 = not verified, 2 = usage.

Manifest = canonical JSON (sorted keys, no spaces, ASCII, no trailing newline), the same rule as a chain entry, so any edit,
even a re-indent, changes its bytes. Fields: base, created_utc, empty_categories, files [{category, path, sha256, size}],
package_version, schema, source_commit, version. `base` is where the file paths start, relative to the manifest's folder:
"files" (a bundle copied by --copy), "." or a path such as "../../.." (the repository root, the usual case).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain  # noqa: E402
import lab_mode  # noqa: E402
import usign_format  # noqa: E402

ROOT = HERE.parents[1]
SCHEMA = 'homensai-evidence-1'
MANIFEST = 'EVIDENCE-MANIFEST.json'
BUNDLE = 'files'
FIELDS = ('base', 'created_utc', 'empty_categories', 'files', 'package_version', 'schema', 'source_commit', 'version')
FILE_FIELDS = ('category', 'path', 'sha256', 'size')
CATEGORY = re.compile(r'[a-z][a-z0-9_]{0,31}')
DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z')
HEX64 = re.compile(r'[0-9a-f]{64}')
# What counts as the test evidence of a release when nothing else is said. Globs are relative to the repository root.
# Narrow them with --spec / --add for one release; a category without a match is recorded as empty (a signed statement).
DEFAULT_SPEC = {
    'test_history': ['docs/TEST-HISTORY.html', 'docs/test-history/results.json'],
    'ci_receipts': ['qa/*CI*.json'],
    'soak': ['private/soak-24h/report*/summary.ru.md', 'private/soak-24h/report*/cycles.json'],
    'queue_report': ['QUEUE-REPORT.md', 'docs/QUEUE-REPORT.md', 'qa/QUEUE-REPORT.md', 'private/QUEUE-REPORT.md'],
    'formal': ['tools/formal/REPORT.ru.md', 'tools/formal/expected.json', 'tools/formal/trace_expected.json',
               'tools/formal/*.out', 'qa/formal/*.json', 'qa/formal/*.out'],
}
DEFAULT_REQUIRED = ('test_history',)


class ReportError(ValueError):
    def __init__(self, code, detail=None):
        ValueError.__init__(self, code if detail is None else '%s: %s' % (code, detail))
        self.code = code


# ---- hashing and names ---------------------------------------------------------------------------------------------

def sha256_file(path):
    digest, size = hashlib.sha256(), 0
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def clean_relative(text, code='EVIDENCE-PATH'):
    """A relative POSIX path of plain names: no '..', no drive, no backslash, no control characters."""
    if not isinstance(text, str) or not text or text.startswith('/') or '\\' in text or ':' in text or any(ord(c) < 32 for c in text):
        raise ReportError(code, repr(text))
    parts = text.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ReportError(code, text)
    return text


def clean_base(text):
    if text == '.':
        return text
    if not isinstance(text, str) or not text or text.startswith('/') or '\\' in text or ':' in text or any(ord(c) < 32 for c in text):
        raise ReportError('EVIDENCE-BASE', repr(text))
    parts = text.split('/')
    if any(part in ('', '.') for part in parts):
        raise ReportError('EVIDENCE-BASE', text)
    return text


def utc(stamp=None):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() if stamp is None else stamp))


# ---- collecting and building -----------------------------------------------------------------------------------------

def collect(root, spec, required=DEFAULT_REQUIRED, skip=None):
    """{category: [relative paths]} for the globs of `spec` (category -> patterns). Symlinks and files outside root are refused."""
    root = Path(root).resolve()
    found, missing = {}, []
    for category, patterns in sorted(spec.items()):
        if not CATEGORY.fullmatch(category):
            raise ReportError('EVIDENCE-CATEGORY', category)
        names = set()
        for pattern in patterns:
            clean_relative(pattern.replace('*', 'x'), 'EVIDENCE-PATTERN')
            hits = 0
            for path in sorted(root.glob(pattern)):
                if path.is_symlink():
                    raise ReportError('EVIDENCE-SYMLINK', path.relative_to(root).as_posix())
                if not path.is_file():
                    continue
                resolved = path.resolve()
                if root not in resolved.parents:
                    raise ReportError('EVIDENCE-OUTSIDE-ROOT', str(path))
                if skip is not None and (skip == resolved or skip in resolved.parents):
                    continue
                names.add(clean_relative(resolved.relative_to(root).as_posix()))
                hits += 1
            if not hits and category in required:
                missing.append('%s: %s' % (category, pattern))
        found[category] = sorted(names)
    if missing:
        raise ReportError('EVIDENCE-REQUIRED-MISSING', '; '.join(missing))
    return found


def build(root, out, source_commit, package_version=None, spec=None, required=DEFAULT_REQUIRED, copy=False, now=None):
    """Write OUT/EVIDENCE-MANIFEST.json for the evidence under `root`. Returns the manifest dict."""
    root, out = Path(root).resolve(), Path(out).resolve()
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit or ''):
        raise ReportError('EVIDENCE-SOURCE-COMMIT', '40-hex tested source commit required')
    if package_version is None:
        package_version = json.loads((root/'VERSION.json').read_text(encoding='utf-8-sig'))['application']['package_version']
    if not re.fullmatch(chain.NAME, package_version):
        raise ReportError('EVIDENCE-VERSION', package_version)
    target = out/MANIFEST
    if target.exists() or Path(str(target)+'.sig').exists():
        raise ReportError('EVIDENCE-EXISTS', 'refusing to replace %s: evidence is never overwritten, build into a new folder' % target)
    groups = collect(root, DEFAULT_SPEC if spec is None else spec, required, skip=out)
    out.mkdir(parents=True, exist_ok=True)
    if copy:
        base = BUNDLE
    else:
        try:
            base = Path(os.path.relpath(root, out)).as_posix()
        except ValueError:
            raise ReportError('EVIDENCE-BASE', 'no relative path from the evidence folder to the repository; use --copy') from None
    rows = []
    for category, names in groups.items():
        for name in names:
            source = root/name
            if copy:
                destination = out/BUNDLE/name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                source = destination
            digest, size = sha256_file(source)
            rows.append(dict(category=category, path=name, sha256=digest, size=size))
    seen = {}
    for row in rows:
        if row['path'] in seen:
            raise ReportError('EVIDENCE-DUPLICATE', '%s is in %s and %s' % (row['path'], seen[row['path']], row['category']))
        seen[row['path']] = row['category']
    rows.sort(key=lambda row: row['path'])
    manifest = dict(base=clean_base(base), created_utc=utc(now), empty_categories=sorted(c for c, names in groups.items() if not names),
                    files=rows, package_version=package_version, schema=SCHEMA, source_commit=source_commit,
                    version=re.sub(r'-[0-9]+$', '', package_version))
    parse_manifest(chain.canonical(manifest))   # what we write must pass what we verify
    target.write_bytes(chain.canonical(manifest))
    return manifest


# ---- reading and checking --------------------------------------------------------------------------------------------

def parse_manifest(data):
    """Manifest bytes -> dict. The bytes must be exactly the canonical form of what they say."""
    try:
        manifest = json.loads(data.decode('ascii'))
    except (UnicodeDecodeError, ValueError):
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'not ASCII JSON') from None
    if not isinstance(manifest, dict) or tuple(sorted(manifest)) != FIELDS:
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'fields')
    if chain.canonical(manifest) != data:
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'not the canonical form (edited or re-saved by hand)')
    if manifest['schema'] != SCHEMA:
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'schema')
    for field in ('package_version', 'version'):
        if not isinstance(manifest[field], str) or not re.fullmatch(chain.NAME, manifest[field]):
            raise ReportError('EVIDENCE-MANIFEST-FORMAT', field)
    if not isinstance(manifest['source_commit'], str) or not re.fullmatch(r'[0-9a-f]{40}', manifest['source_commit']):
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'source_commit')
    if not isinstance(manifest['created_utc'], str) or not DATE.fullmatch(manifest['created_utc']):
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'created_utc')
    clean_base(manifest['base'])
    empty = manifest['empty_categories']
    if not isinstance(empty, list) or empty != sorted(set(empty)) or not all(isinstance(c, str) and CATEGORY.fullmatch(c) for c in empty):
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'empty_categories')
    files = manifest['files']
    if not isinstance(files, list):
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'files')
    paths = []
    for row in files:
        if not isinstance(row, dict) or tuple(sorted(row)) != FILE_FIELDS:
            raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'file row')
        clean_relative(row['path'], 'EVIDENCE-MANIFEST-FORMAT')
        if (not isinstance(row['category'], str) or not CATEGORY.fullmatch(row['category']) or row['category'] in empty
                or not isinstance(row['sha256'], str) or not HEX64.fullmatch(row['sha256'])
                or type(row['size']) is not int or row['size'] < 0):
            raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'file row %s' % row['path'])
        paths.append(row['path'])
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        raise ReportError('EVIDENCE-MANIFEST-FORMAT', 'files not sorted or not unique')
    return manifest


def base_directory(directory, manifest, override=None):
    return Path(override) if override else (Path(directory)/manifest['base']).resolve()


def check_files(directory, manifest, override=None):
    """Problems [(code, path, detail)] of the files against the manifest: changed, missing, and (in a bundle) extra."""
    base = base_directory(directory, manifest, override)
    problems = []
    for row in manifest['files']:
        path = base/row['path']
        if path.is_symlink() or not path.is_file():
            problems.append(('EVIDENCE-FILE-MISSING', row['path'], 'not found under %s' % base))
            continue
        try:
            digest, size = sha256_file(path)
        except OSError as error:
            problems.append(('EVIDENCE-FILE-MISSING', row['path'], 'unreadable: %s' % error.__class__.__name__))
            continue
        if digest != row['sha256'] or size != row['size']:
            problems.append(('EVIDENCE-FILE-CHANGED', row['path'], 'sha256 expected %s..., found %s...; size expected %d, found %d' % (
                row['sha256'][:16], digest[:16], row['size'], size)))
    if override is None and manifest['base'] == BUNDLE and base.is_dir():
        known = {row['path'] for row in manifest['files']}
        for path in sorted(base.rglob('*')):
            if path.is_file() or path.is_symlink():
                name = path.relative_to(base).as_posix()
                if name not in known:
                    problems.append(('EVIDENCE-FILE-EXTRA', name, 'in the bundle but not in the signed manifest'))
    return problems


def prepare_signing(root, directory, package_version, source_commit):
    """Everything sign-release checks before it asks for the code: (manifest bytes, manifest sha256, path)."""
    path = Path(directory)/MANIFEST
    if not path.is_file():
        raise ReportError('EVIDENCE-MANIFEST-MISSING', str(path))
    if Path(str(path)+'.sig').exists():
        raise ReportError('EVIDENCE-ALREADY-SIGNED', 'build a new folder for another release')
    data = path.read_bytes()
    manifest = parse_manifest(data)
    if manifest['package_version'] != package_version or manifest['source_commit'] != source_commit:
        raise ReportError('EVIDENCE-RELEASE-MISMATCH', 'the manifest is for %s at %s' % (manifest['package_version'], manifest['source_commit'][:12]))
    problems = check_files(directory, manifest)
    if problems:
        raise ReportError(problems[0][0], '%s: %s (the evidence changed after the manifest was built; build it again)' % (problems[0][1], problems[0][2]))
    return data, hashlib.sha256(data).hexdigest(), path


def verify_dir(directory, root, base_override=None):
    """Full verification. Returns {'result': 'PASS'|'FAIL', 'problems': [{code, path, detail}], ...}; never raises on bad evidence."""
    import keytool   # imported late: keytool imports this module
    directory = Path(directory)
    problems = []

    def add(code, path='', detail=''):
        problems.append(dict(code=code, path=path, detail=detail))
    report = dict(directory=str(directory), result='FAIL', problems=problems)
    path = directory/MANIFEST
    if not path.is_file():
        add('EVIDENCE-MANIFEST-MISSING', MANIFEST, 'no %s in %s' % (MANIFEST, directory))
        return report
    data = path.read_bytes()
    report['manifest_sha256'] = hashlib.sha256(data).hexdigest()
    try:
        manifest = parse_manifest(data)
    except ReportError as error:
        add(error.code, MANIFEST, str(error))
        return report
    report.update(package_version=manifest['package_version'], source_commit=manifest['source_commit'], files=len(manifest['files']))
    # 1. the files: all problems, each with its name
    for code, name, detail in check_files(directory, manifest, base_override):
        add(code, name, detail)
    # 2. the chain: the manifest's hash must be inside a signed release entry of this very release
    entry = None
    try:
        entries, _ = keytool.verified_chain(Path(root))
    except (ValueError, OSError) as error:
        add('EVIDENCE-CHAIN-INVALID', '', str(error))
        entries = []
    for candidate in entries:
        if candidate.get(chain.EVIDENCE_KEY) == report['manifest_sha256']:
            entry = candidate
    if entry is None and entries:
        add('EVIDENCE-NOT-IN-CHAIN', MANIFEST, 'no signed release-chain entry carries evidence_sha256 %s...' % report['manifest_sha256'][:16])
    elif entry is not None:
        report['chain_seq'] = entry['seq']
        if entry['package_version'] != manifest['package_version'] or entry['source_commit'] != manifest['source_commit']:
            add('EVIDENCE-CHAIN-MISMATCH', MANIFEST, 'the chain entry is for %s at %s' % (entry['package_version'], entry['source_commit'][:12]))
    # 3. the signature over the manifest bytes: a trusted, not revoked key, the same one that signed the chain entry
    signature = Path(str(path)+'.sig')
    if not signature.is_file():
        add('EVIDENCE-SIGNATURE-MISSING', signature.name, 'no signature next to the manifest')
    else:
        try:
            revoked = set(keytool.revocations(Path(root)))
            for each in entries:
                revoked |= chain.parse_revocations(each['revoked'])
            seq = entry['seq'] if entry else len(entries)
            signer = usign_format.verify_file(keytool.trusted_keys(Path(root)), data, signature.read_bytes(),
                                              [key_id for key_id, first in revoked if seq >= first])
            report['signer'] = signer
            if entry is not None and entry['key_id'] != signer:
                add('EVIDENCE-SIGNER-MISMATCH', signature.name, 'signed by %s, the chain entry by %s' % (signer, entry['key_id']))
        except ValueError as error:
            add('EVIDENCE-SIGNATURE-INVALID', signature.name, str(error))
    report['result'] = 'FAIL' if problems else 'PASS'
    return report


# ---- command line ----------------------------------------------------------------------------------------------------

class PlainConsole:
    def say(self, text=''):
        print(text, flush=True)


def load_spec(path, additions):
    spec = {name: list(patterns) for name, patterns in DEFAULT_SPEC.items()}
    if path:
        loaded = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if not isinstance(loaded, dict) or not all(isinstance(v, list) and all(isinstance(p, str) for p in v) for v in loaded.values()):
            raise ReportError('EVIDENCE-SPEC', 'expected {"category": ["glob", ...]}')
        spec = loaded
    for item in additions or ():
        name, _, pattern = item.partition('=')
        if not name or not pattern:
            raise ReportError('EVIDENCE-SPEC', '--add expects category=glob')
        spec.setdefault(name, []).append(pattern)
    return spec


def cmd_build(args, root, console):
    spec = load_spec(args.spec, args.add)
    required = tuple(args.require) if args.require else DEFAULT_REQUIRED
    manifest = build(root, args.out, args.source_commit, args.package_version, spec, required, args.copy)
    console.say('EVIDENCE-MANIFEST %s: %d files, base "%s", empty categories: %s' % (
        Path(args.out)/MANIFEST, len(manifest['files']), manifest['base'], ', '.join(manifest['empty_categories']) or 'none'))
    console.say('Not signed yet: `keytool.py sign-release ... --evidence %s` signs it and links it into the release chain.' % args.out)
    return 0


def cmd_verify(args, root, console):
    report = verify_dir(args.directory, root, args.base)
    console.say(json.dumps(report, sort_keys=True))
    for problem in report['problems']:
        print('%s: %s%s' % (problem['code'], problem['path'], ' (%s)' % problem['detail'] if problem['detail'] else ''), file=sys.stderr)
    if report['problems']:
        print('STOP: EVIDENCE-VERIFY-FAILED: %d problem(s)' % len(report['problems']), file=sys.stderr)
        return 1
    return 0


def parser():
    p = argparse.ArgumentParser(description='HomenS.AI signed test evidence (docs/architecture/SIGNING-2026-11-03.ru.md, section 12)')
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build', help='hash the evidence and write the manifest (unsigned)')
    b.add_argument('--out', required=True, help='evidence folder, for example releases/evidence/<package version>')
    b.add_argument('--source-commit', required=True)
    b.add_argument('--package-version')
    b.add_argument('--root', help='repository root (default: this checkout)')
    b.add_argument('--copy', action='store_true', help='copy the files into OUT/files so the folder is self-contained')
    b.add_argument('--spec', help='JSON {"category": ["glob", ...]} instead of the defaults')
    b.add_argument('--add', action='append', help='category=glob, added to the spec')
    b.add_argument('--require', action='append', help='category that must match every pattern (default: test_history)')
    b.add_argument('--lab', help='work on the test lab tree')
    v = sub.add_parser('verify', help='check manifest, signature, chain link and every file')
    v.add_argument('directory')
    v.add_argument('--root', help='repository with the keys and the release chain (default: this checkout)')
    v.add_argument('--base', help='take the files from this folder instead of the manifest base')
    v.add_argument('--lab', help='verify against the test lab tree')
    return p


def main(argv=None, root=ROOT, store=None, console=None):
    args = parser().parse_args(argv)
    try:
        console = console or PlainConsole()
        lab = lab_mode.resolve(args.lab)
        if lab is not None:
            console.say('*** %s ***' % (lab_mode.BANNER % lab))
            root = lab.repo
        elif args.root:
            root = Path(args.root)
        return {'build': cmd_build, 'verify': cmd_verify}[args.command](args, Path(root), console)
    except (ValueError, OSError) as error:
        print('STOP: %s' % error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
