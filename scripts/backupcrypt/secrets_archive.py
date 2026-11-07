"""The secrets the USB backup leaves out, as ONE age-encrypted archive (opt-in; never plaintext on any medium).

What goes in (paths relative to private/ of the main checkout; names only ever reach logs and manifests):
  * portable-router-access*/            router access material (SSH key blob, known_hosts, *.key.dpapi keys,
                                         receipts, local state); without the vendored python/, python-ipks/, feeds/,
                                         static/, rtp-libraries/ trees, __pycache__ and other files > 1 MB (payload
                                         scripts and logs, not secrets)
  * router-backup-*.tgz                  router configuration exports kept at the top of private/
  * */<file>.key.dpapi (two levels deep) the AES keys of the encrypted router configuration backups made during
                                         acceptance/installation runs, with their .enc/.aesgcm/.receipt.json siblings
  * extra paths given by the caller      backup_usb.py passes the files its own secret filter skipped in work.zip
Encrypted router configuration exports (*.enc, *.aesgcm, about 2.4 MB each, ~140 MB in total on 04.11.2026): only
the newest ROUTER_BACKUPS_DEFAULT by modification time (router_backups=-1 takes all, 0 none); every key is kept, so
an older export copied elsewhere can still be opened. Hard limit 20 MB per file, 512 MB in total.
Never: private/signing/ (release keys, the age identity itself, the TOTP seed: those are owner-revealed into the
password manager), git worktrees (a directory with .git), symlinks, anything outside private/.

DPAPI blobs are useless on another PC, so every *.dpapi blob found is unprotected IN MEMORY (current Windows user, no
entropy: the portable_key.py format) and stored in the archive as <name>.plain (e.g. x.key.dpapi -> x.key.plain);
`agetool.py restore-secrets` protects them again with DPAPI on the new PC. A blob that cannot be unprotected is kept
as is and listed in the summary. Plaintext exists only in this process's memory: the tar is built in a BytesIO and
encrypted before anything is written.
"""
import ctypes
import datetime
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

MAX_FILE = 20 * 1024 * 1024
ACCESS_MAX_FILE = 1024 * 1024
ROUTER_BACKUPS_DEFAULT = 6
BLOB_SUFFIXES = ('.enc', '.aesgcm')
MAX_TOTAL = 512 * 1024 * 1024
ACCESS_PREFIX = 'portable-router-access'
ACCESS_SKIP_DIRS = {'python', 'python-ipks', 'feeds', 'static', 'rtp-libraries', '__pycache__', '.git'}
NEVER_TOP = {'signing', 'signing-lab', 'signing-lab-tools'}
KEY_SIBLINGS = ('.enc', '.aesgcm', '.receipt.json')
ARCHIVE_NAME = 'secrets.tar.age'
INNER_MANIFEST = 'SECRETS-MANIFEST.json'


class ArchiveError(ValueError):
    pass


# ---- DPAPI without entropy (portable_key.transform format) ----------------------------------------------------

class _Blob(ctypes.Structure):
    _fields_ = [('cbData', ctypes.c_uint32), ('pbData', ctypes.POINTER(ctypes.c_char))]


def dpapi(data, protect):
    """CryptProtectData / CryptUnprotectData for the current Windows user, no entropy, UI forbidden."""
    if os.name != 'nt':
        raise ArchiveError('DPAPI-WINDOWS-ONLY')
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    buffer = ctypes.create_string_buffer(data, len(data))
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    output = _Blob()
    call = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    ok = call(ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(output))
    if not ok:
        raise ArchiveError('DPAPI-%s-FAILED' % ('PROTECT' if protect else 'UNPROTECT'))
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.memset(output.pbData, 0, output.cbData)
        kernel32.LocalFree(output.pbData)


# ---- selection --------------------------------------------------------------------------------------------------

def _is_worktree(path):
    return (path/'.git').exists()


def _forbidden(rel):
    parts = rel.split('/')
    return (parts[0] in NEVER_TOP or '.git' in parts or rel.endswith('.identity.dpapi') or '..' in parts
            or rel.startswith('/'))


def select(private, extra=(), router_backups=ROUTER_BACKUPS_DEFAULT):
    """Sorted unique relative paths (POSIX) of the files to archive, and the skipped ones with a reason."""
    private = Path(private)
    chosen, skipped, blobs = set(), [], {}

    def take(path, limit=None):
        rel = path.relative_to(private).as_posix()
        if _forbidden(rel):
            skipped.append('%s [never]' % rel)
            return
        try:
            if path.is_symlink() or not path.is_file():
                return
            size = path.stat().st_size
        except OSError as error:
            skipped.append('%s [%s]' % (rel, error.__class__.__name__))
            return
        if size > MAX_FILE:
            skipped.append('%s [>20 MB]' % rel)
            return
        if rel.endswith(BLOB_SUFFIXES):
            blobs[rel] = path.stat().st_mtime
            return
        if limit is not None and size > limit:
            skipped.append('%s [>1 MB, not key material]' % rel)
            return
        chosen.add(rel)

    if not private.is_dir():
        raise ArchiveError('PRIVATE-MISSING: %s' % private)
    for top in sorted(private.iterdir()):
        name = top.name
        if name in NEVER_TOP or top.is_symlink():
            continue
        if top.is_file():
            if name.startswith('router-backup-') and name.endswith('.tgz'):
                take(top)
            continue
        if not top.is_dir() or _is_worktree(top):
            continue
        if name.startswith(ACCESS_PREFIX):
            for directory, dirnames, filenames in os.walk(top):
                dirnames[:] = sorted(d for d in dirnames if d not in ACCESS_SKIP_DIRS
                                     and not os.path.islink(os.path.join(directory, d)))
                for filename in sorted(filenames):
                    path = Path(directory)/filename
                    take(path, None if filename.endswith('.dpapi') else ACCESS_MAX_FILE)
            continue
        candidates = []
        try:
            for child in top.iterdir():
                if child.is_dir() and not child.is_symlink() and not _is_worktree(child):
                    candidates += [p for p in child.iterdir()]
                else:
                    candidates.append(child)
        except OSError:
            continue
        names = {p.name for p in candidates}
        for path in candidates:
            if path.name.endswith('.key.dpapi'):
                take(path)
                stem = path.name[:-len('.key.dpapi')]
                for suffix in KEY_SIBLINGS:
                    if stem+suffix in names:
                        take(path.with_name(stem+suffix))
    for rel in extra:
        rel = str(rel).replace('\\', '/').split(' [', 1)[0].strip()
        if not rel:
            continue
        path = private/rel
        try:
            path.resolve().relative_to(private.resolve())
        except ValueError:
            skipped.append('%s [outside private]' % rel)
            continue
        take(path)
    newest = sorted(blobs, key=lambda rel: (-blobs[rel], rel))
    keep = newest if router_backups < 0 else newest[:router_backups]
    chosen.update(keep)
    skipped += ['%s [older router backup; router_backups=%d]' % (rel, router_backups) for rel in sorted(set(newest)-set(keep))]
    return sorted(chosen), skipped


# ---- archive ----------------------------------------------------------------------------------------------------

def _add(tar, name, data, mtime):
    info = tarfile.TarInfo(name)
    info.size, info.mtime, info.mode = len(data), int(mtime), 0o600
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    tar.addfile(info, io.BytesIO(data))


def build_tar(private, paths, unprotect=None):
    """In-memory tar of `paths` (DPAPI blobs unwrapped), and the inner manifest. Returns (bytes, summary)."""
    private = Path(private)
    unprotect = unprotect or (lambda blob: dpapi(blob, False))
    buffer, total = io.BytesIO(), 0
    entries, unwrap_failed = [], []
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
        for rel in paths:
            path = private/rel
            data = path.read_bytes()
            mtime = path.stat().st_mtime
            name = rel
            if rel.endswith('.dpapi'):
                try:
                    data = unprotect(data)
                    name = rel[:-len('.dpapi')]+'.plain'
                except (ArchiveError, OSError):
                    unwrap_failed.append(rel)
            total += len(data)
            if total > MAX_TOTAL:
                raise ArchiveError('ARCHIVE-TOO-LARGE')
            _add(tar, name, data, mtime)
            entries.append({'name': name, 'source': rel, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        manifest = {'schema': 1, 'kind': 'homensai-private-secrets', 'created_utc':
                    datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'entries': entries, 'unwrap_failed': unwrap_failed,
                    'restore': 'py -3.14 scripts/backupcrypt/agetool.py restore-secrets --archive <file> --into <dir>'}
        _add(tar, INNER_MANIFEST, json.dumps(manifest, indent=1, sort_keys=True).encode('utf-8'), 0)
    return buffer.getvalue(), manifest


def create(private, out, recipients, extra=(), unprotect=None, age=None, router_backups=ROUTER_BACKUPS_DEFAULT):
    """Select, tar in memory, encrypt to `recipients`, write `out` atomically. Returns a summary with names only."""
    if age is None:
        import age_format as age
    if not recipients:
        raise ArchiveError('NO-RECIPIENTS')
    paths, skipped = select(private, extra, router_backups)
    plain, manifest = build_tar(private, paths, unprotect)
    try:
        sealed = age.encrypt(plain, recipients)
    finally:
        plain = None
    out = Path(out)
    temporary = out.with_name(out.name+'.partial')
    temporary.write_bytes(sealed)
    os.replace(temporary, out)
    return {'result': 'OK', 'file': out.name, 'size': len(sealed), 'sha256': hashlib.sha256(sealed).hexdigest(),
            'recipients': [r.encode() for r in recipients], 'entries': len(manifest['entries']),
            'names': [e['name'] for e in manifest['entries']], 'unwrapped': sum(1 for p in paths if p.endswith('.dpapi'))
            - len(manifest['unwrap_failed']), 'unwrap_failed': manifest['unwrap_failed'], 'skipped': skipped,
            'backend': age.backend_name()}


def _safe_name(name):
    parts = name.split('/')
    return (name and not name.startswith('/') and '\\' not in name and ':' not in name
            and all(p not in ('', '.', '..') for p in parts))


def _redirected(path):
    """True for a symlink, a Windows junction or any other reparse point: such a path may lead outside `into`."""
    if path.is_symlink():
        return True
    is_junction = getattr(path, 'is_junction', None)
    if is_junction is not None and is_junction():
        return True
    try:
        attributes = getattr(os.lstat(path), 'st_file_attributes', 0)
    except FileNotFoundError:
        return False
    return bool(attributes & 0x400)                         # FILE_ATTRIBUTE_REPARSE_POINT


def _fresh_destination(into):
    """`into` must be a new or empty real directory (not a link); returns its resolved path."""
    into = Path(into)
    if os.path.lexists(into):
        if _redirected(into) or not into.is_dir():
            raise ArchiveError('RESTORE-DESTINATION-UNSAFE')
        if any(into.iterdir()):
            raise ArchiveError('RESTORE-DESTINATION-NOT-EMPTY')
    else:
        into.mkdir(parents=True)
    if _redirected(into):
        raise ArchiveError('RESTORE-DESTINATION-UNSAFE')
    return into.resolve(strict=True)


def _safe_parent(root, name):
    """Create the parent directories of `name` under `root` one by one, refusing any link on the way and checking that
    the result still resolves inside `root`. Returns the absolute target path."""
    current = root
    for part in name.split('/')[:-1]:
        current = current/part
        if os.path.lexists(current):
            if _redirected(current) or not current.is_dir():
                raise ArchiveError('RESTORE-PATH-REDIRECTED: %s' % name)
        else:
            current.mkdir()
            if _redirected(current):
                raise ArchiveError('RESTORE-PATH-REDIRECTED: %s' % name)
    if current.resolve(strict=True) != root.joinpath(*name.split('/')[:-1]):
        raise ArchiveError('RESTORE-PATH-REDIRECTED: %s' % name)
    return current/name.split('/')[-1]


def restore(sealed, identities, into, protect=None, age=None):
    """Decrypt and unpack into `into`, which must be a new or empty directory (an existing linked subdirectory cannot
    redirect the secrets elsewhere). *.plain keys are DPAPI-protected again (written as *.dpapi); nothing is
    overwritten and no symlink or junction is followed. Returns the list of written relative paths."""
    if age is None:
        import age_format as age
    protect = protect or (lambda data: dpapi(data, True))
    plain = age.decrypt(sealed, identities)
    written = []
    with tarfile.open(fileobj=io.BytesIO(plain), mode='r') as tar:
        members = tar.getmembers()
        for member in members:
            if not member.isfile() or not _safe_name(member.name):
                raise ArchiveError('RESTORE-UNSAFE-ENTRY: %s' % member.name)
        root = _fresh_destination(into)
        for member in members:
            if member.name == INNER_MANIFEST:
                continue
            data = tar.extractfile(member).read()
            name = member.name
            if name.endswith('.plain'):
                name, data = name[:-len('.plain')]+'.dpapi', protect(data)
            target = _safe_parent(root, name)
            if os.path.lexists(target):
                raise ArchiveError('RESTORE-EXISTS: %s' % name)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
            with os.fdopen(os.open(target, flags, 0o600), 'wb') as stream:
                stream.write(data)
            os.utime(target, (member.mtime, member.mtime))
            written.append(name)
    return written


def list_names(sealed, identities, age=None):
    if age is None:
        import age_format as age
    plain = age.decrypt(sealed, identities)
    with tarfile.open(fileobj=io.BytesIO(plain), mode='r') as tar:
        return [m.name for m in tar.getmembers()]
