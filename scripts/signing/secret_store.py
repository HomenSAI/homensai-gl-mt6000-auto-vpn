"""The PC-side secret store: private/signing/ in the main checkout, every secret DPAPI-encrypted for the current Windows
user (*.dpapi; the USB backup excludes *.dpapi). Plaintext secrets exist only in memory, on the owner's screen during
reveal, or in a temporary QR page that is overwritten and deleted (wipe()).

Files:  main.key.dpapi, reserve.key.dpapi  usign secret key files (unencrypted usign format inside the DPAPI blob)
        totp.seed.dpapi                    the TOTP seed (base32)
        totp-state.json                    wrong-code counter, lockout, last used step (no secret)
        recovery.codes.dpapi               recovery codes: salted scrypt hashes and when each was used, never the codes
        second-factor.lock                 empty; serialises code checks so one code cannot be spent twice at once
        keys.json                          public: key name -> key id, creation time
        *.retired-<UTC>.*                  replaced material, kept (never deleted) after an emergency or reset
"""
import contextlib
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import lab_mode

try:
    import msvcrt
except ImportError:
    import fcntl
    msvcrt = None

ENTROPY = b'HomenS.AI Auto VPN release signing v1'
# Another entropy for the test lab: a lab blob cannot be opened by the real store, nor a real blob by the lab.
ENTROPY_LAB = b'HomenS.AI Auto VPN signing TEST LAB v1'
KEY_NAMES = ('main', 'reserve')
LOCK_FILE = 'second-factor.lock'


class StoreError(ValueError):
    pass


class _Blob(ctypes.Structure):
    _fields_ = [('cbData', ctypes.c_uint32), ('pbData', ctypes.POINTER(ctypes.c_char))]


def _blob(data):
    buffer = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _dpapi(data, protect, secondary=None):
    if os.name != 'nt':
        raise StoreError('STORE-DPAPI-WINDOWS-ONLY')
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    source, keep = _blob(data)
    entropy, keep_entropy = _blob(secondary or ENTROPY)
    output = _Blob()
    flags = 0x1  # CRYPTPROTECT_UI_FORBIDDEN; no LOCAL_MACHINE flag: only this Windows user can decrypt.
    if protect:
        ok = crypt32.CryptProtectData(ctypes.byref(source), 'HomenS.AI release signing', ctypes.byref(entropy), None, None,
                                      flags, ctypes.byref(output))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, ctypes.byref(entropy), None, None, flags,
                                        ctypes.byref(output))
    if not ok:
        raise StoreError('STORE-DPAPI-%s-FAILED' % ('PROTECT' if protect else 'UNPROTECT'))
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.memset(output.pbData, 0, output.cbData)
        kernel32.LocalFree(output.pbData)


def default_root():
    """private/signing of the main checkout (shared by every worktree), from git's common directory."""
    override = os.environ.get('HOMENSAI_SIGNING_STORE')
    if override:
        return Path(override)
    here = Path(__file__).resolve().parent
    common = subprocess.run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=here,
                            capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    return Path(common).parent/'private'/'signing'


def _lock(stream):
    if msvcrt:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(stream):
    if msvcrt:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class Store:
    def __init__(self, root=None, protect=None, unprotect=None, lab=False):
        self.root = Path(root) if root else default_root()
        self.lab = bool(lab)
        (lab_mode.require_lab_path if self.lab else lab_mode.refuse_lab_path)(self.root)
        secondary = ENTROPY_LAB if self.lab else None
        self.protect = protect or (lambda data: _dpapi(data, True, secondary))
        self.unprotect = unprotect or (lambda data: _dpapi(data, False, secondary))

    def path(self, name):
        return self.root/name

    def key_path(self, key):
        if key not in KEY_NAMES:
            raise StoreError('STORE-KEY-NAME')
        return self.path(key+'.key.dpapi')

    def has(self, name):
        return self.path(name).is_file()

    def write_secret(self, name, data, replace=False):
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.path(name)
        if target.exists() and not replace:
            raise StoreError('STORE-EXISTS: %s' % name)
        if target.exists():
            self.retire(name)
        blob = self.protect(data)
        temporary = target.with_name(target.name+'.tmp')
        temporary.write_bytes(blob)
        os.replace(temporary, target)
        if self.unprotect(target.read_bytes()) != data:
            raise StoreError('STORE-READBACK-MISMATCH: %s' % name)

    def replace_secret(self, name, data, keep_old=False):
        """Atomic replacement: a reader or a power cut sees the whole old file or the whole new one, never a mix or nothing.
        write_secret retires first, which is fine for keys; this is for a file whose loss would matter between two steps."""
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.path(name)
        blob = self.protect(data)
        temporary = target.with_name(target.name+'.tmp')
        try:
            with open(temporary, 'wb') as stream:
                stream.write(blob)
                stream.flush()
                os.fsync(stream.fileno())
            if keep_old and target.exists():
                shutil.copy2(target, self.retired_path(name))
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        if self.unprotect(target.read_bytes()) != data:
            raise StoreError('STORE-READBACK-MISMATCH: %s' % name)

    @contextlib.contextmanager
    def exclusive(self, wait=15.0):
        """One second-factor check at a time across processes. The operating system drops the lock when the process ends,
        so a crash cannot leave the gate stuck. Never hold it across a prompt."""
        self.root.mkdir(parents=True, exist_ok=True)
        with open(self.path(LOCK_FILE), 'a+b') as stream:
            deadline = time.monotonic()+wait
            while True:
                try:
                    _lock(stream)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise StoreError('STORE-BUSY: another signing command is checking a code') from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                _unlock(stream)

    def read_secret(self, name):
        try:
            blob = self.path(name).read_bytes()
        except FileNotFoundError:
            raise StoreError('STORE-MISSING: %s' % name) from None
        return self.unprotect(blob)

    def retired_path(self, name):
        stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        stem, _, suffix = name.partition('.')
        target, serial = self.path('%s.retired-%s.%s' % (stem, stamp, suffix)), 1
        while target.exists():
            serial += 1
            target = self.path('%s.retired-%s-%d.%s' % (stem, stamp, serial, suffix))
        return target

    def retire(self, name):
        """Keep replaced material (evidence, possible recovery); the suffix keeps the *.dpapi exclusion working."""
        source = self.path(name)
        if not source.exists():
            return None
        target = self.retired_path(name)
        os.replace(source, target)
        return target

    def public_index(self):
        try:
            return json.loads(self.path('keys.json').read_text(encoding='utf-8'))
        except FileNotFoundError:
            return {}

    def write_public_index(self, data):
        self.root.mkdir(parents=True, exist_ok=True)
        self.path('keys.json').write_text(json.dumps(data, indent=2, sort_keys=True)+'\n', encoding='utf-8')


def wipe(path):
    """Overwrite a temporary plaintext file with zeros, flush to disk, then delete it. On SSDs and journaling file
    systems this is best effort (wear levelling may keep old blocks), which is why the console QR is the default."""
    path = Path(path)
    try:
        size = path.stat().st_size
        with open(path, 'r+b') as stream:
            stream.write(b'\0'*size)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if path.exists():
            path.unlink()


def is_windows():
    return sys.platform == 'win32'
