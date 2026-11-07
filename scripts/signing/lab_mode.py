"""Test-lab mode of the signing tools: the same code on a separate, visibly fake set of keys.

Guide: docs/architecture/SIGNING-LAB-2026-11-04.ru.md. A lab directory holds everything the real tools keep in three
places (store/ = private/signing, repo/ = the repository tree with the trust list and the chain, reports next to them).
Nothing here copies logic from keytool.py: this module only decides WHERE the tools work and refuses to cross the line:

  lab -> real  a lab key id starts with KEY_ID_PREFIX; sign-release, trusted_keys() and publish-reviewed.py refuse such ids
               outside a lab tree. A lab secret line is tagged PAYLOAD_TAG. Lab DPAPI blobs use their own entropy, so the
               real tool cannot open them even when a file is copied over.
  real -> lab  a real Store() refuses a directory inside a lab, a lab refuses the real store and its parents, a real key id
               is refused inside a lab tree, and a pasted real secret is refused before it is stored.

The modes are told apart by MARKER, a public file at the top of a lab directory: a tree below a marker is a lab tree.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path

ENV_DIR = 'HOMENSAI_SIGNING_DIR'
ENV_STORE = 'HOMENSAI_SIGNING_STORE'
TEST_ENV = 'HOMENSAI_SIGNING_TEST'
MARKER = 'HOMENSAI-SIGNING-LAB.json'
KEY_ID_PREFIX = '1ab01ab0'
PAYLOAD_TAG = 'HSAI-SK1-LAB'
CHAIN_FILE = Path('releases/CHAIN-LAB.jsonl')
TOTP_ISSUER = 'HomenS.AI TEST LAB'
TOTP_ACCOUNT = 'HomenS.AI TEST LAB:signing-drills'
BANNER = 'TEST LAB %s: test keys only, they can never sign a real release'
DIR_NAME = 'signing-lab'
ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT/'router-test-kit/02-install.sh'
TRUST_TOOL = ROOT/'router/files/usr/sbin/homensai-vpn-trust-key'
HISTORY = ('0.0.1-alpha1-1', '0.0.2-alpha1-1')
GIT_ID = ('-c', 'user.name=HomenS.AI TEST LAB', '-c', 'user.email=lab@invalid', '-c', 'core.hooksPath=', '-c',
          'commit.gpgsign=false', '-c', 'core.autocrlf=false', '-c', 'init.defaultBranch=lab')


class LabRefused(ValueError):
    """A stable code first, like every other error of the signing tools."""


def is_lab_key_id(value):
    text = value.hex() if isinstance(value, (bytes, bytearray)) else str(value)
    return text.lower().startswith(KEY_ID_PREFIX)


def lab_ancestor(path):
    """The directory with MARKER at or above path, or None."""
    path = Path(path).absolute()
    for folder in [path]+list(path.parents):
        if (folder/MARKER).is_file():
            return folder
    return None


def is_lab_tree(root):
    return lab_ancestor(root) is not None


def refuse_lab_path(root):
    """The real tools never read a lab directory, marked or not yet."""
    path = Path(root).absolute()
    if lab_ancestor(path) or DIR_NAME in path.parts:
        raise LabRefused('STORE-LAB-DIR-REFUSED: %s is a test lab; the real tools do not read it' % path)


def require_lab_path(root):
    if not lab_ancestor(root):
        raise LabRefused('STORE-NOT-A-LAB: a lab store must be inside a lab directory')


def _checkout_parent():
    """The main checkout (private/ of it is shared by every worktree), or None outside a git tree."""
    try:
        common = subprocess.run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=str(ROOT),
                                capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(common).parent if common else None


def real_store_roots():
    found = []
    parent = _checkout_parent()
    if parent:
        found.append(parent/'private'/'signing')
    if os.environ.get(ENV_STORE):
        found.append(Path(os.environ[ENV_STORE]))
    return [path.resolve() for path in found]


def default_lab_root():
    parent = _checkout_parent()
    if parent is None:
        raise LabRefused('LAB-DIR-NEEDED: outside a git checkout name the lab with --lab or %s' % ENV_DIR)
    return parent/'private'/DIR_NAME


def check_lab_path(path):
    """Every way a lab directory could hit something that is not a lab. Runs before anything is created or deleted."""
    path = Path(path).resolve()
    for real in real_store_roots():
        if path == real or real in path.parents or path in real.parents:
            raise LabRefused('LAB-DIR-REAL-STORE: %s touches the real signing store' % path)
    if path == Path(path.anchor) or path == Path.home():
        raise LabRefused('LAB-DIR-UNSAFE: %s' % path)
    if (path/'.git').exists():
        raise LabRefused('LAB-DIR-IS-A-CHECKOUT: %s is a git working tree; resetting the lab would delete it' % path)
    if path.is_dir() and not (path/MARKER).is_file() and any(path.iterdir()):
        raise LabRefused('LAB-DIR-NOT-EMPTY: %s has files and no lab marker' % path)
    return path


def _make_writable(function, path, _):
    os.chmod(path, stat.S_IWRITE)
    function(path)


def remove_tree(path):
    if Path(path).exists():
        try:
            shutil.rmtree(path, onexc=_make_writable)
        except TypeError:  # Python before 3.12
            shutil.rmtree(path, onerror=_make_writable)


def test_protect(data):
    """No DPAPI off Windows: the Linux test runs of the lab use this reversible wrapper, gated by HOMENSAI_SIGNING_TEST."""
    return bytes(byte ^ 0x5a for byte in data)


class LabDir:
    def __init__(self, path):
        self.root = check_lab_path(path)
        self.store_dir = self.root/'store'
        self.repo = self.root/'repo'
        self.work = self.root/'work'
        self.report = self.root/'DRILLS.html'
        self.results = self.root/'drills.json'
        self.recipients = self.repo/'scripts/backupcrypt/recipients.txt'

    def __str__(self):
        return str(self.root)

    def ensure(self):
        """Create the lab once. A fresh lab has a small fake release history in a git tree of its own, so `new-keys` runs its
        real import of that history and `sign-release` its real commit check."""
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root/MARKER
        if not marker.is_file():
            marker.write_text(json.dumps({'lab': True, 'purpose': 'HomenS.AI signing drills: test keys only',
                                          'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())},
                                         indent=2)+'\n', encoding='utf-8')
        self.store_dir.mkdir(exist_ok=True)
        if not (self.repo/'.git').exists():
            self.bootstrap_repo()
        return self

    def git(self, *args):
        return subprocess.run(('git',)+GIT_ID+args, cwd=str(self.repo), capture_output=True, text=True, check=True,
                              timeout=120).stdout.strip()

    def bootstrap_repo(self):
        (self.repo/'releases').mkdir(parents=True, exist_ok=True)
        (self.repo/'router-test-kit').mkdir(parents=True, exist_ok=True)
        kit = KIT.read_bytes().replace(b'\r\n', b'\n')
        kit, count = re.subn(rb"(?m)^TRUSTED_KEYS='[^'\n]*'$", b"TRUSTED_KEYS=''", kit)
        if count != 1:
            raise LabRefused('KIT-LITERALS-MISSING')
        (self.repo/'router-test-kit/02-install.sh').write_bytes(kit)
        self.git('init', '-q')
        self.write_version(None, None)
        for package_version in HISTORY:
            self.add_package(package_version, record=True)

    def write_version(self, artifact, digest):
        (self.repo/'VERSION.json').write_text(json.dumps({'lab': True, 'application': {'artifact': artifact, 'sha256': digest}},
                                                         indent=2)+'\n', encoding='utf-8')

    def add_package(self, package_version, record=False):
        """A small fake .ipk committed to the lab tree; `record` also adds the .sha256 line the history import reads."""
        name = 'homensai-auto-vpn_%s_all.ipk' % package_version
        data = ('HomenS.AI TEST LAB fake package %s, not installable, %s\n' % (package_version, time.time())).encode('ascii')
        path = self.repo/'releases'/name
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        if record:
            path.with_name(name+'.sha256').write_text('%s  %s\n' % (digest, name), encoding='ascii')
        self.write_version(name, digest)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'lab: fake package %s' % package_version)
        return path, self.git('rev-parse', 'HEAD')

    def store(self):
        from secret_store import Store, StoreError
        if os.name == 'nt':
            return Store(self.store_dir, lab=True)
        if os.environ.get(TEST_ENV) != '1':
            raise StoreError('STORE-DPAPI-WINDOWS-ONLY')
        return Store(self.store_dir, protect=test_protect, unprotect=test_protect, lab=True)

    def reset(self):
        """Delete this lab and nothing else: the marker and the path checks run again right before the delete."""
        self.root = check_lab_path(self.root)
        if not (self.root/MARKER).is_file():
            raise LabRefused('LAB-RESET-NO-MARKER: %s' % self.root)
        remove_tree(self.root)


def resolve(value=None):
    """The lab named by --lab or HOMENSAI_SIGNING_DIR, created when new; None means the real tools."""
    value = value or os.environ.get(ENV_DIR)
    return LabDir(value).ensure() if value else None


def check_pair(root, store):
    """A lab store with a real tree, or the other way round, would mix the two worlds."""
    if is_lab_tree(root) != bool(getattr(store, 'lab', False)):
        raise LabRefused('LAB-MODE-MISMATCH: tree %s and store %s are not both real or both lab' % (root, store.root))


def new_key(lab, generate):
    """A lab key id carries the prefix; a real one never does, so the id alone tells the two apart forever."""
    key = generate()
    if lab:
        return type(key)(key.seed, bytes.fromhex(KEY_ID_PREFIX)+key.key_id[4:], key.salt)
    while is_lab_key_id(key.key_id):
        key = generate()
    return key


def require_same_world(key_id, lab, code):
    if is_lab_key_id(key_id) and not lab:
        raise LabRefused('%s-LAB-KEY-REFUSED: %s is a test key, it can never be used for a real release' % (code, key_id))
    if lab and not is_lab_key_id(key_id):
        raise LabRefused('%s-REAL-KEY-IN-LAB: %s is not a test key; real keys never enter the lab' % (code, key_id))


def lab_ids_in(names=(), chain_data=b'', signature_id=None):
    """Lab key ids in a list of key file names, in release chain bytes or a signature's key id (for publish-reviewed.py)."""
    found = {Path(name).name for name in names if is_lab_key_id(Path(name).name)}
    found |= set(re.findall(r'"key_id":"(%s[0-9a-f]{8})"' % KEY_ID_PREFIX, chain_data.decode('ascii', 'replace')))
    if signature_id is not None and is_lab_key_id(signature_id):
        found.add(signature_id)
    return sorted(found)


def refuse_in_publication(names=(), chain_data=b'', signature_id=None):
    found = lab_ids_in(names, chain_data, signature_id)
    if found:
        raise LabRefused('PUBLICATION-LAB-KEY: %s' % ', '.join(found))


def refuse_lab_environment():
    if os.environ.get(ENV_DIR):
        raise LabRefused('PUBLICATION-LAB-ENV: %s is set; a publication never runs in the signing lab' % ENV_DIR)
    value = os.environ.get(ENV_STORE)
    if value and (lab_ancestor(value) or DIR_NAME in Path(value).parts):
        raise LabRefused('PUBLICATION-LAB-ENV: %s points into the signing lab' % ENV_STORE)
