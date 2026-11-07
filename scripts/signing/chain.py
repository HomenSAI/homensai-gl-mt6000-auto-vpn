"""Hash-chained, signed release history: releases/CHAIN.jsonl (docs/architecture/SIGNING-2026-11-03.ru.md).

One line per release, oldest first, byte-exact (the router's 02-install.sh parses it with one strict sed expression):
  {"entry":<canonical entry>,"sig":"<base64 of the 74-byte usign signature over the canonical entry bytes>"}
canonical entry = JSON with sorted keys, no spaces, ASCII only:
  artifact, date_utc, key_id, origin ('imported' | 'release'), package_version, prev (SHA-256 hex of the previous
  entry's canonical bytes, 64 zeros for seq 0), revoked ('<key id>:<first seq> ...' or ''), seq (0, 1, 2 ...),
  sha256 (of the .ipk), size (bytes, null only for an imported record whose .ipk is not in the repository),
  source_commit (40 hex), version.
Optional, only in entries that carry it (older entries stay valid byte for byte): evidence_sha256, the SHA-256 of the signed
test-evidence manifest of the release (scripts/signing/report_manifest.py). It sorts between date_utc and key_id.
The signature covers the entry only, so `prev` links entries, and the key id inside the entry must equal the key id of
the signature. A revocation '<key id>:<n>' rejects every entry with seq >= n signed by that key; entries before n stay
valid (the history signed before a key was lost is not rewritten).
"""
import base64
import hashlib
import json
import re

import usign_format

GENESIS_PREV = '0'*64
NAME = r'[A-Za-z0-9._+-]+'
ENTRY_KEYS = ('artifact', 'date_utc', 'key_id', 'origin', 'package_version', 'prev', 'revoked', 'seq', 'sha256',
              'size', 'source_commit', 'version')
EVIDENCE_KEY = 'evidence_sha256'
ENTRY_KEYS_WITH_EVIDENCE = tuple(sorted(ENTRY_KEYS+(EVIDENCE_KEY,)))
# The same shape 02-install.sh checks with sed: anything else is CHAIN-FORMAT.
LINE = re.compile(r'\{"entry":(\{"artifact":"%(n)s","date_utc":"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",'
                  r'(?:"evidence_sha256":"[0-9a-f]{64}",)?"key_id":"[0-9a-f]{16}","origin":"(?:imported|release)","package_version":"%(n)s",'
                  r'"prev":"[0-9a-f]{64}","revoked":"(?:[0-9a-f]{16}:[0-9]{1,9}(?: [0-9a-f]{16}:[0-9]{1,9})*)?",'
                  r'"seq":(?:0|[1-9][0-9]{0,8}),"sha256":"[0-9a-f]{64}","size":(?:null|0|[1-9][0-9]{0,11}),'
                  r'"source_commit":"[0-9a-f]{40}","version":"%(n)s"\})'
                  r',"sig":"([A-Za-z0-9+/]{99}=)"\}' % {'n': NAME})


class ChainError(ValueError):
    def __init__(self, code, seq=None):
        ValueError.__init__(self, code if seq is None else '%s at seq %s' % (code, seq))
        self.code, self.seq = code, seq


def canonical(entry):
    return json.dumps(entry, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def entry_hash(entry):
    return hashlib.sha256(canonical(entry)).hexdigest()


def parse_revocations(text):
    """'<key id>:<first seq>' items separated by spaces, commas or new lines; '#' starts a comment."""
    found = set()
    for line in text.splitlines():
        for item in re.split(r'[\s,]+', line.split('#', 1)[0].strip()):
            if not item:
                continue
            match = re.fullmatch(r'([0-9a-f]{16}):([0-9]{1,9})', item)
            if not match:
                raise ChainError('CHAIN-REVOCATION-FORMAT')
            found.add((match.group(1), int(match.group(2))))
    return found


def make_line(entry, secret):
    if tuple(sorted(entry)) not in (ENTRY_KEYS, ENTRY_KEYS_WITH_EVIDENCE) or entry['key_id'] != secret.key_id.hex():
        raise ChainError('CHAIN-ENTRY-FIELDS')
    body = canonical(entry)
    signature = b'Ed'+secret.key_id+usign_format.sign(secret.seed, body)
    line = b'{"entry":'+body+b',"sig":"'+base64.b64encode(signature)+b'"}'
    if not LINE.fullmatch(line.decode('ascii')):
        raise ChainError('CHAIN-ENTRY-FIELDS', entry.get('seq'))
    return line


def read_lines(data):
    if not data:
        return []
    if not data.endswith(b'\n') or b'\r' in data:
        raise ChainError('CHAIN-FORMAT')
    return data[:-1].split(b'\n')


def verify_chain(data, keys, revoked=()):
    """Check every line of CHAIN.jsonl bytes. keys: {key id hex: usign_format.PublicKey}; revoked: {(key id, first seq)}.

    Returns the entries (dicts). Raises ChainError with a distinct code: CHAIN-EMPTY, CHAIN-FORMAT, CHAIN-SEQ-GAP,
    CHAIN-PREV-MISMATCH, CHAIN-DUPLICATE-VERSION, CHAIN-KEY-MISMATCH, CHAIN-KEY-REVOKED, CHAIN-KEY-UNTRUSTED,
    CHAIN-SIGNATURE-INVALID."""
    lines = read_lines(data)
    if not lines:
        raise ChainError('CHAIN-EMPTY')
    parsed = []
    for index, raw in enumerate(lines):
        try:
            text = raw.decode('ascii')
        except UnicodeDecodeError:
            raise ChainError('CHAIN-FORMAT', index) from None
        match = LINE.fullmatch(text)
        if not match:
            raise ChainError('CHAIN-FORMAT', index)
        entry = json.loads(match.group(1))
        if canonical(entry) != match.group(1).encode('ascii'):
            raise ChainError('CHAIN-FORMAT', index)
        parsed.append((entry, match.group(1).encode('ascii'), base64.b64decode(match.group(2))))
    # Revocations declared anywhere in the chain apply to the whole chain (two passes, as on the router).
    revoked = set(revoked)
    for entry, _, _ in parsed:
        revoked |= parse_revocations(entry['revoked'])
    prev, versions = GENESIS_PREV, set()
    for index, (entry, body, signature) in enumerate(parsed):
        if entry['seq'] != index:
            raise ChainError('CHAIN-SEQ-GAP', index)
        if entry['prev'] != prev:
            raise ChainError('CHAIN-PREV-MISMATCH', index)
        if entry['package_version'] in versions:
            raise ChainError('CHAIN-DUPLICATE-VERSION', index)
        versions.add(entry['package_version'])
        if entry['size'] is None and entry['origin'] != 'imported':
            raise ChainError('CHAIN-FORMAT', index)
        if EVIDENCE_KEY in entry and entry['origin'] != 'release':
            raise ChainError('CHAIN-FORMAT', index)   # history imported later has no test evidence to link
        signer = signature[2:10].hex()
        if signature[:2] != b'Ed' or signer != entry['key_id']:
            raise ChainError('CHAIN-KEY-MISMATCH', index)
        if any(key == signer and index >= first for key, first in revoked):
            raise ChainError('CHAIN-KEY-REVOKED', index)
        key = keys.get(signer)
        if key is None:
            raise ChainError('CHAIN-KEY-UNTRUSTED', index)
        if not usign_format.verify(key.public, body, signature[10:]):
            raise ChainError('CHAIN-SIGNATURE-INVALID', index)
        prev = hashlib.sha256(body).hexdigest()
    return [entry for entry, _, _ in parsed]


def check_head(entries, package, package_version=None):
    """The package being installed must be the newest entry (bytes, or a (sha256, size) pair)."""
    head = entries[-1]
    if isinstance(package, (bytes, bytearray)):
        package = (hashlib.sha256(package).hexdigest(), len(package))
    if head['sha256'] != package[0] or head['size'] != package[1] or (package_version and head['package_version'] != package_version):
        raise ChainError('CHAIN-HEAD-MISMATCH', head['seq'])
    return head


def check_extends(installed, new, allow_downgrade=False):
    """installed/new: CHAIN.jsonl bytes. The installed history must be a prefix of the new one (same lines, byte for
    byte). A new chain that is a strict prefix of the installed one is a rollback: refused unless allow_downgrade."""
    old, fresh = read_lines(installed), read_lines(new)
    if fresh[:len(old)] == old:
        return 'extends' if len(fresh) > len(old) else 'same'
    if old[:len(fresh)] == fresh:
        if allow_downgrade:
            return 'downgrade'
        raise ChainError('CHAIN-DOWNGRADE', len(fresh)-1)
    raise ChainError('CHAIN-FORK')


def next_entry(entries, artifact, version, package_version, sha256, size, source_commit, date_utc, key_id,
               origin='release', revoked='', evidence_sha256=None):
    seq = len(entries)
    prev = GENESIS_PREV if not entries else entry_hash(entries[-1])
    entry = dict(artifact=artifact, date_utc=date_utc, key_id=key_id, origin=origin, package_version=package_version,
                 prev=prev, revoked=revoked, seq=seq, sha256=sha256, size=size, source_commit=source_commit, version=version)
    if evidence_sha256 is not None:
        entry[EVIDENCE_KEY] = evidence_sha256   # make_line refuses anything that is not 64 lower-case hex
    return entry


def _version_key(package_version):
    match = re.fullmatch(r'([0-9]+)\.([0-9]+)\.([0-9]+)(?:-(alpha|beta|rc)([0-9]+))?-([0-9]+)', package_version)
    if not match:
        raise ChainError('CHAIN-IMPORT-VERSION')
    stage = {'alpha': 0, 'beta': 1, 'rc': 2, None: 3}[match.group(4)]
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)), stage, int(match.group(5) or 0), int(match.group(6)))


def import_records(root, git):
    """Historical entries from releases/*.ipk.sha256 (+ the .ipk when it is in the repository), oldest version first.

    git(args) -> stdout text. source_commit/date_utc = the commit that first added the checksum record. Records whose
    .ipk disagrees with its checksum are refused (CHAIN-IMPORT-HASH): history is never silently repaired."""
    rows = []
    for record in sorted((root/'releases').glob('homensai-auto-vpn_*_all.ipk.sha256')):
        text = record.read_text(encoding='utf-8').strip()
        match = re.fullmatch(r'([0-9a-f]{64}) [ *](homensai-auto-vpn_(%s)_all\.ipk)' % NAME, text)
        if not match or match.group(2)+'.sha256' != record.name:
            raise ChainError('CHAIN-IMPORT-RECORD')
        sha, artifact, package_version = match.groups()
        package = root/'releases'/artifact
        size = None
        if package.is_file():
            data = package.read_bytes()
            if hashlib.sha256(data).hexdigest() != sha:
                raise ChainError('CHAIN-IMPORT-HASH')
            size = len(data)
        found = git(['log', '--diff-filter=A', '--format=%H %ct', '--', 'releases/'+record.name]).split()
        if len(found) < 2:
            raise ChainError('CHAIN-IMPORT-COMMIT')
        commit, stamp = found[-2], int(found[-1])
        version = re.sub(r'-[0-9]+$', '', package_version)
        rows.append((_version_key(package_version), artifact, version, package_version, sha, size, commit, stamp))
    rows.sort()
    return rows
