#!/usr/bin/env python3
"""Offline secret scanner (stdlib only). Values are NEVER printed: a finding is path, line, rule and value length.

Modes (one of):
  --staged                 files in the git index (pre-commit, gitflow privacy)
  --tree REV               every file of a commit's tree (publication, release)
  --range REVARG...        objects that are new in a rev-list range (new commits before a push); everything after
                           --range goes to git rev-list, so it must be the last option, for example:
                           --range NEW1 NEW2 --not OLD      or      --range A..B      or      --range --all
  --manifest FILE --root D files listed (JSON array of relative paths) under directory D (offline CI)
  --paths FILE...          explicit files

Options: --repo DIR | --git-dir DIR (default: current directory), --allowlist FILE.

Exit: 0 clean, 1 findings, 2 usage or git error.

Known test placeholders are allowed by scripts/secret_scan_allowlist.json (value regexes and path globs, each with a
reason) or by the marker "secret-scan: allow" on the same line. Everything else blocks."""
import argparse
import bz2
import fnmatch
import gzip
import hashlib
import io
import json
import lzma
import math
import os
import re
import subprocess
import sys
import tarfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
DEFAULT_ALLOWLIST = HERE / 'secret_scan_allowlist.json'
MARKER = b'secret-scan: allow'
MAX_LINE = 20000
MAX_FILE = 64 * 1024 * 1024
ARCHIVE_BUDGET = 128 * 1024 * 1024
MAX_DEPTH = 3                                               # ipk -> data.tar.gz -> file
ZIP_MAGIC = (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')
# Content the scanner could not fully read is a finding (fail closed), never a silent "clean".
INCOMPLETE = ('archive_too_deep', 'archive_member_too_large', 'archive_unreadable', 'archive_budget', 'too_large_to_scan')
# Rules that stay meaningful inside binary content (structural markers and exact-format tokens).
BINARY_KINDS = frozenset(('hdr', 'token'))

# name -> (regex over one line, group holding the value or 0 for "the match itself", kind)
# kind "hdr": structural marker, always a finding; "value": placeholder-filtered; "token": exact format token
RULES_SRC = [
    ('pem_private_key', re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED |PGP )?PRIVATE KEY'), 0, 'hdr'),
    ('age_secret', re.compile(rb'AGE-SECRET-KEY-1[A-Z0-9]{20,}'), 0, 'token'),
    ('usign_secret', re.compile(rb'(?i)untrusted comment:[^\n]*secret key'), 0, 'hdr'),  # secret-scan: allow (the rule's own source)
    ('openvpn_inline', re.compile(rb'(?i)^\s*<(?:key|tls-crypt|tls-auth|secret)>\s*$'), 0, 'hdr'),
    ('openvpn_auth_file', re.compile(rb'(?i)^\s*auth-user-pass\s+\S+'), 0, 'hdr'),
    ('telegram_token', re.compile(rb'(?<![0-9])(\d{8,10}):([A-Za-z0-9_-]{35})(?![A-Za-z0-9_-])'), 0, 'token'),
    ('github_token', re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})'), 0, 'token'),
    ('api_key_token', re.compile(rb'\b(?:sk-or-v1-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}\b|xox[abprs]-[A-Za-z0-9-]{10,})'), 0, 'token'),
    ('bearer', re.compile(rb'(?i)authorization:\s*bearer\s+([A-Za-z0-9._~+/=-]{20,})'), 1, 'value'),
    ('wg_key', re.compile(rb'(?i)(?:private[_ ]?key|preshared[_ ]?key|psk)["\'\s:=]+([A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=)'), 1, 'value'),
    ('psk_hex', re.compile(rb'(?i)\bpsk=([0-9a-f]{64})\b'), 1, 'value'),
    ('uci_option_secret', re.compile(rb'(?i)^\s*(?:option|list)\s+(?:key|psk|sae_password|password|passwd|private_key|preshared_key|'
                                     rb'telegram_token|bot_token|token|secret|auth_pass|api_key)\s+[\'"]?([^\'"\s]{4,})'), 1, 'value'),
    ('uci_dotted_secret', re.compile(rb'(?i)\b[\w@\[\]-]+\.(?:key|psk|password|passwd|private_key|preshared_key|telegram_token|bot_token|token|secret)'
                                     rb'\s*=\s*\'([^\']{4,})\''), 1, 'value'),
    ('kv_secret', re.compile(rb'(?i)\b(?:password|passwd|passphrase|bot_token|telegram_token|api[_-]?key|secret|token|private_key)\b["\']?\s*[:=]\s*["\']([^"\'\s]{8,})["\']'), 1, 'value'),
    ('url_credentials', re.compile(rb'https?://[^/\s:@]+:([^/\s:@]{3,})@'), 1, 'value'),
    ('shadow_hash', re.compile(rb'\$(?:1|5|6|y)\$[./A-Za-z0-9]{2,16}\$[./A-Za-z0-9]{20,}'), 0, 'token'),
]
RULES = [(n, re.compile(rx.pattern, rx.flags | re.M), g, k) for n, rx, g, k in RULES_SRC]
# cheap literal prefilter (lower-case): a rule runs only when one of its hints occurs in the blob; speed only, no effect on results
HINTS = {
    'pem_private_key': (b'private key',), 'age_secret': (b'age-secret-key-1',), 'usign_secret': (b'secret key',),
    'openvpn_inline': (b'<key>', b'<tls-crypt>', b'<tls-auth>', b'<secret>'), 'openvpn_auth_file': (b'auth-user-pass',),
    'github_token': (b'ghp_', b'gho_', b'ghu_', b'ghs_', b'ghr_', b'github_pat_'),
    'api_key_token': (b'sk-', b'akia', b'xox'), 'bearer': (b'bearer',),
    'wg_key': (b'private', b'preshared', b'psk'), 'psk_hex': (b'psk=',),
    'url_credentials': (b'://',), 'shadow_hash': (b'$1$', b'$5$', b'$6$', b'$y$'),
    'uci_option_secret': (b'option', b'list'), 'uci_dotted_secret': (b'.key', b'.psk', b'.password', b'.passwd', b'.private_key',
                                                                     b'.preshared_key', b'.telegram_token', b'.bot_token', b'.token', b'.secret'),
    'kv_secret': (b'password', b'passwd', b'passphrase', b'bot_token', b'telegram_token', b'api_key', b'api-key', b'apikey',
                  b'secret', b'token', b'private_key'),
}
# value-bearing rules are skipped when the value is plainly a placeholder, a variable reference or a code expression
PLACEHOLDER = re.compile(rb'(?i)(example|placeholder|dummy|fake|xxxx|\*\*\*|<.*>|\$\{|\$\(|redacted|changeme|your[_-]|sample|todo|'
                         rb'^\^|^none$|^null$|^true$|^false$|\{\{|^\$|^%|^\[|\(\)|\.\.\.|^[a-z_][a-z0-9_]*\(|^[a-z_][a-z0-9_.]*\[)')

# file names that must never be tracked or published (content is irrelevant)
BAD_NAME_GLOBS = ['*.dpapi', '*.enc', '*.tgz', '*.tar.gz', '*.private.*', '*.local.*', 'router-backup*', '*.ovpn', '*.key',
                  '*.p12', '*.pfx', '*.kdbx', 'id_rsa', 'id_rsa.*', 'id_ed25519', 'id_ed25519.*', 'id_ecdsa', 'id_ecdsa.*',
                  '.env', '.env.*', '*.sqlite', '*.sqlite3', 'cookies.txt']
BAD_NAME_ALLOW = ['.env.example']
BAD_DIRS = ('private', '.ssh', '.gnupg', 'secrets', 'router-backups', 'portable-router-access')


class Finding:
    __slots__ = ('path', 'line', 'rule', 'length')

    def __init__(self, path, line, rule, length):
        self.path, self.line, self.rule, self.length = path, line, rule, length

    def key(self):
        return (self.path, self.line, self.rule)

    def __str__(self):
        where = self.path + (':%d' % self.line if self.line else '')
        return 'SECRET-SCAN %s %s%s' % (where, self.rule, ' len=%d' % self.length if self.length else '')


class Allowlist:
    """Reasoned exceptions for known test placeholders. Every row needs a "reason".
    values: {"rules": [...], "regex": "...", "paths": [globs] (optional), "reason": "..."}  - a value that matches
    paths:  {"glob": "...", "rules": [...], "reason": "..."}                                - a whole file for some rules"""

    def __init__(self, data=None):
        data = data or {}
        self.raw = data
        self.values = [(set(r.get('rules', ['*'])), re.compile(r['regex'].encode()), r.get('paths'))
                       for r in data.get('values', [])]
        self.paths = [(r['glob'], set(r.get('rules', ['*']))) for r in data.get('paths', [])]
        for row in list(data.get('values', [])) + list(data.get('paths', [])):
            if not row.get('reason'):
                raise ValueError('ALLOWLIST-REASON-MISSING')

    @classmethod
    def load(cls, path=None):
        path = Path(path) if path else DEFAULT_ALLOWLIST
        if not path.is_file():
            return cls()
        return cls(json.loads(path.read_text(encoding='utf-8-sig')))

    def value_ok(self, rule, value, path):
        for rules, rx, globs in self.values:
            if ('*' in rules or rule in rules) and rx.search(value) and (
                    globs is None or any(fnmatch.fnmatchcase(path, g) for g in globs)):
                return True
        return False

    def path_ok(self, path, rule):
        return any(fnmatch.fnmatchcase(path, glob) and ('*' in rules or rule in rules) for glob, rules in self.paths)


def entropy(value):
    if not value:
        return 0.0
    counts = {}
    for b in value:
        counts[b] = counts.get(b, 0) + 1
    return -sum(c / len(value) * math.log2(c / len(value)) for c in counts.values())


def looks_like_secret_value(value):
    """True for a value that could be real: not a placeholder phrase, not a code expression, not a trivial repeat."""
    if PLACEHOLDER.search(value):
        return False
    if len(set(value)) <= 3:
        return False
    return True


# Archive members follow the same name and directory rules; only nested package containers (control.tar.gz,
# data.tar.gz) are allowed as names, because their content is opened and scanned like any other member.
MEMBER_BAD_GLOBS = [g for g in BAD_NAME_GLOBS if g not in ('*.tgz', '*.tar.gz')]


def name_findings(path, allow, member=False, inner=None):
    """member and inner (the member's own name inside its archive) are passed explicitly by the archive walker; a '!' in
    an ordinary file name, or inside a member name (R4-08: private/notes!public.txt), changes nothing. A member whose own
    name was not passed is judged by the whole label, outer directories included (conservative)."""
    inner = (inner if inner is not None else path) if member else path
    parts = PurePosixPath(inner).parts or ('',)
    base = parts[-1].lower()
    dirs = [p.lower() for p in parts[:-1]]
    out = []
    # Directories first: an allowed basename such as .env.example never exempts private/ or secrets/.
    if any(d in BAD_DIRS for d in dirs) or (len(dirs) > 1 and dirs[0] == '.claude' and dirs[1] == 'worktrees') or (
            len(dirs) == 1 and dirs[0] == '.claude' and base == 'worktrees'):
        out.append(Finding(path, 0, 'forbidden_dir', 0))
    elif base not in BAD_NAME_ALLOW and any(fnmatch.fnmatchcase(base, g) for g in (MEMBER_BAD_GLOBS if member else BAD_NAME_GLOBS)):
        out.append(Finding(path, 0, 'forbidden_name', 0))
    return [f for f in out if not allow.path_ok(path, f.rule)]


NL = b'\n'
_RAW_CACHE = {}


def raw_findings(data, allow, kinds=None):
    """(line, rule, value_length, value, match) for a text blob, independent of its path. Identical blobs (the same file inside many
    packages) are scanned once. kinds limits the rules (binary content: structural markers and exact tokens only)."""
    key = (hashlib.sha1(data).digest(), kinds)
    if key in _RAW_CACHE:
        return _RAW_CACHE[key]
    out = []
    seen = set()
    low = data.lower()
    for rule, rx, group, kind in RULES:
        if kinds is not None and kind not in kinds:
            continue
        hints = HINTS.get(rule)
        if hints and not any(h in low for h in hints):
            continue
        for m in rx.finditer(data):
            value = m.group(group) if group else m.group(0)
            if kind == 'value' and not looks_like_secret_value(value):
                continue
            start = data.rfind(NL, 0, m.start()) + 1
            end = data.find(NL, m.end())
            if MARKER in data[start:end if end >= 0 else len(data)]:
                continue
            number = data.count(NL, 0, m.start()) + 1
            if (number, rule) in seen:
                continue
            seen.add((number, rule))
            out.append((number, rule, len(value) if kind != 'hdr' else 0, value, m.group(0)))
    if len(_RAW_CACHE) > 4000:
        _RAW_CACHE.clear()
    _RAW_CACHE[key] = out
    return out


def scan_text(path, data, allow, kinds=None):
    return [Finding(path, n, rule, ln) for n, rule, ln, value, whole in raw_findings(data, allow, kinds)
            if not allow.path_ok(path, rule) and not allow.value_ok(rule, value, path) and not allow.value_ok(rule, whole, path)]


def incomplete(path, rule, allow):
    return [] if allow.path_ok(path, rule) else [Finding(path, 0, rule, 0)]


def utf16_text(data):
    """UTF-16 text (with a BOM, or with NUL bytes in every other position) re-encoded as UTF-8; None otherwise."""
    if data[:2] in (b'\xff\xfe', b'\xfe\xff'):
        codec, body = ('utf-16-le' if data[:2] == b'\xff\xfe' else 'utf-16-be'), data[2:]
    else:
        sample = data[:8000]
        even, odd = sample[0::2], sample[1::2]
        if len(sample) < 8:
            return None
        if odd.count(0) >= 0.4 * len(odd) and even.count(0) <= 0.05 * len(even):
            codec, body = 'utf-16-le', data
        elif even.count(0) >= 0.4 * len(even) and odd.count(0) <= 0.05 * len(odd):
            codec, body = 'utf-16-be', data
        else:
            return None
    return body[:len(body) - len(body) % 2].decode(codec, 'replace').encode('utf-8', 'replace')


def plain_stream(data):
    """The decompressor of a plain (non-tar) gzip, bzip2 or xz stream and its label; None for other content (R4-08:
    content-based, like qa/privacy_audit.decompress)."""
    if data[:2] == b'\x1f\x8b':
        return gzip.GzipFile(fileobj=io.BytesIO(data)), '<gunzip>'
    if data[:3] == b'BZh':
        return bz2.BZ2File(io.BytesIO(data)), '<bunzip2>'
    if data[:6] == b'\xfd7zXZ\x00':
        return lzma.LZMAFile(io.BytesIO(data)), '<unxz>'
    return None


def scan_blob(path, data, allow, budget=None, depth=0, member_name=None):
    """Findings for one file. Archives (ipk, tar, tgz, gz, bz2, xz, zip) are opened in memory and every member scanned.
    Anything that could not be read completely (too deep, too large, unreadable, over budget) is a finding."""
    out = name_findings(path, allow, member=depth > 0, inner=member_name)
    if len(data) > MAX_FILE:
        return out + incomplete(path, 'too_large_to_scan', allow)
    budget = budget if budget is not None else [ARCHIVE_BUDGET]
    is_zip = data[:4] in ZIP_MAGIC
    is_gz = plain_stream(data) is not None
    is_tar = data[257:262] == b'ustar'
    if is_zip or is_gz or is_tar:
        if depth >= MAX_DEPTH:
            return out + incomplete(path, 'archive_too_deep', allow)
        if depth == 0:
            budget[0] -= len(data)                          # members are charged with their expanded size below
        if budget[0] < 0:
            return out + incomplete(path, 'archive_budget', allow)

        def member(name, size, read):
            if size > MAX_FILE:
                return incomplete(path + '!' + name, 'archive_member_too_large', allow)
            budget[0] -= size
            if budget[0] < 0:
                return incomplete(path + '!' + name, 'archive_budget', allow)
            return scan_blob(path + '!' + name, read(), allow, budget, depth + 1, name)
        try:
            if is_zip:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        if info.flag_bits & 1:              # encrypted member: its content cannot be checked
                            out += name_findings(path + '!' + info.filename, allow, member=True, inner=info.filename)
                            out += incomplete(path + '!' + info.filename, 'archive_unreadable', allow)
                            continue
                        out += member(info.filename, info.file_size, lambda info=info: z.read(info))
                return out
            try:
                with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as t:
                    for m in t:
                        if m.isdir():
                            continue
                        if not m.isfile():                  # links and devices carry no content, but names still count
                            out += name_findings(path + '!' + m.name, allow, member=True, inner=m.name)
                            continue
                        out += member(m.name, m.size, lambda m=m: t.extractfile(m).read())
                return out
            except tarfile.ReadError:
                if not is_gz or is_tar:
                    raise
            # A plain gzip/bzip2/xz stream (not a tar): decompress with the same bounds and scan its content.
            stream, label = plain_stream(data)
            with stream:
                inner = stream.read(MAX_FILE + 1)
            return out + member(label, len(inner), lambda: inner)
        except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError, RuntimeError, zlib.error, lzma.LZMAError, ValueError):
            return out + incomplete(path, 'archive_unreadable', allow)
    if b'\0' in data[:8000]:
        text = utf16_text(data)
        if text is not None:
            return out + scan_text(path, text, allow)
        # Binary content: structural markers and exact-format tokens are still found (a NUL byte hides nothing).
        return out + scan_text(path, data, allow, BINARY_KINDS)
    return out + scan_text(path, data, allow)


# ----------------------------------------------------------------------------- git sources
def git(args, repo=None, git_dir=None, data=None):
    cmd = ['git', '-c', 'core.quotepath=false']
    if git_dir:
        cmd += ['--git-dir', str(git_dir)]
    elif repo:
        cmd += ['-C', str(repo)]
    r = subprocess.run(cmd + args, input=data, capture_output=True, timeout=1800)
    if r.returncode:
        raise RuntimeError('GIT-FAILED: ' + ' '.join(args[:3]))
    return r.stdout


def cat_blobs(entries, repo, git_dir):
    """entries: list of (sha, path). Yields (path, data). One cat-file --batch call."""
    if not entries:
        return
    out = git(['cat-file', '--batch'], repo, git_dir, data=('\n'.join(e[0] for e in entries) + '\n').encode())
    pos = 0
    for sha, path in entries:
        nl = out.index(b'\n', pos)
        header = out[pos:nl].split()
        if len(header) < 3:                                 # "<sha> missing"
            pos = nl + 1
            continue
        size = int(header[2])
        yield path, out[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1


def staged_entries(repo, git_dir):
    raw = git(['diff', '--cached', '--name-only', '-z', '--diff-filter=ACMR'], repo, git_dir)
    names = [n for n in raw.decode('utf-8', 'replace').split('\0') if n]
    if not names:
        return []
    ls = git(['ls-files', '-s', '-z', '--'] + names, repo, git_dir).decode('utf-8', 'replace').split('\0')
    entries = []
    for row in ls:
        if not row:
            continue
        meta, _, path = row.partition('\t')
        mode, sha = meta.split()[:2]
        if mode in ('100644', '100755'):
            entries.append((sha, path))
    return entries


def tree_entries(rev, repo, git_dir):
    raw = git(['ls-tree', '-r', '-z', rev], repo, git_dir).decode('utf-8', 'replace').split('\0')
    entries = []
    for row in raw:
        if not row:
            continue
        meta, _, path = row.partition('\t')
        mode, kind, sha = meta.split()[:3]
        if kind == 'blob' and mode in ('100644', '100755'):
            entries.append((sha, path))
    return entries


def range_entries(args, repo, git_dir):
    raw = git(['rev-list', '--objects'] + args, repo, git_dir).decode('utf-8', 'replace').splitlines()
    shas = {}
    for row in raw:
        sha, _, path = row.partition(' ')
        if path:
            shas.setdefault(sha, path)
    if not shas:
        return []
    checked = git(['cat-file', '--batch-check'], repo, git_dir, data=('\n'.join(shas) + '\n').encode()).decode().splitlines()
    return [(row.split()[0], shas[row.split()[0]]) for row in checked if len(row.split()) == 3 and row.split()[1] == 'blob']


def _init_worker(directory):
    if directory not in sys.path:
        sys.path.insert(0, directory)


def _batch_scan(args):
    """Worker: (raw_allowlist, [(path, data)]) -> [(path, line, rule, length)]."""
    raw, items = args
    allow = Allowlist(raw)
    return [(f.path, f.line, f.rule, f.length) for path, data in items for f in scan_blob(path, data, allow)]


def scan_entries(entries, repo, git_dir, allow, parallel_bytes=24 * 1024 * 1024):
    """Blobs are read in batches; a big scan (more than parallel_bytes of content) is spread over processes."""
    findings = []
    files = 0
    batches, current, size = [], [], 0
    for start in range(0, len(entries), 500):
        for path, data in cat_blobs(entries[start:start + 500], repo, git_dir):
            files += 1
            current.append((path, data))
            size += len(data)
            if size >= 8 * 1024 * 1024:
                batches.append(current)
                current, size = [], 0
    if current:
        batches.append(current)
    total = sum(len(d) for b in batches for _, d in b)
    if total > parallel_bytes and len(batches) > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 2, 8), initializer=_init_worker, initargs=(str(HERE),)) as pool:
            for rows in pool.map(_batch_scan, [(allow.raw, b) for b in batches]):
                findings += [Finding(*row) for row in rows]
    else:
        for b in batches:
            for path, data in b:
                findings += scan_blob(path, data, allow)
    seen = set()
    unique = []
    for f in findings:
        if f.key() not in seen:
            seen.add(f.key())
            unique.append(f)
    return files, unique


def scan_files(paths, root, allow):
    findings = []
    files = 0
    for rel in paths:
        target = Path(root) / rel
        if target.is_symlink() or not target.is_file():
            continue
        files += 1
        findings += scan_blob(PurePosixPath(rel).as_posix(), target.read_bytes(), allow)
    return files, findings


def report(files, findings, label, stream=None):
    stream = stream or sys.stdout
    for f in sorted(findings, key=lambda x: (x.path, x.line, x.rule)):
        print(str(f), file=stream)
    if findings:
        print('SECRET-SCAN-FAIL %s findings=%d files=%d (values are never printed; fix, or add a reasoned entry to '
              'scripts/secret_scan_allowlist.json for a known test placeholder)' % (label, len(findings), files), file=stream)
        return 1
    print('SECRET-SCAN-OK %s files=%d' % (label, files), file=stream)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--staged', action='store_true')
    mode.add_argument('--tree')
    mode.add_argument('--range', nargs=argparse.REMAINDER, metavar='REVARG')
    mode.add_argument('--manifest', type=Path)
    mode.add_argument('--paths', nargs='+')
    p.add_argument('--repo', default=None)
    p.add_argument('--git-dir', default=None)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--allowlist', default=None)
    a = p.parse_args(argv)
    try:
        allow = Allowlist.load(a.allowlist)
        repo = a.repo or ('.' if not a.git_dir else None)
        if a.staged:
            files, findings = scan_entries(staged_entries(repo, a.git_dir), repo, a.git_dir, allow)
            label = 'staged'
        elif a.tree:
            files, findings = scan_entries(tree_entries(a.tree, repo, a.git_dir), repo, a.git_dir, allow)
            label = 'tree ' + a.tree[:12]
        elif a.range is not None:
            revargs = [x for x in a.range if x != '--']
            files, findings = scan_entries(range_entries(revargs, repo, a.git_dir), repo, a.git_dir, allow)
            label = 'range'
        elif a.manifest:
            names = json.loads(a.manifest.read_text(encoding='utf-8-sig'))
            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                raise ValueError('MANIFEST-FORMAT')
            files, findings = scan_files(names, a.root, allow)
            label = 'manifest'
        else:
            files, findings = scan_files(a.paths, a.root, allow)
            label = 'paths'
    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as error:
        print('SECRET-SCAN-ERROR %s' % error.__class__.__name__, file=sys.stderr)
        return 2
    return report(files, findings, label)


if __name__ == '__main__':
    sys.exit(main())
