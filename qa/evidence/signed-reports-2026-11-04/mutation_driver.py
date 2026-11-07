"""Evidence driver (not a unit test): break one guard of the signed test-evidence path at a time in a COPY of the tree and prove the
tests fail. Run inside a throwaway Linux container:  python3 mutation_driver.py <copy of the repo> [names]
(prints JSON, exit 1 on a survivor). Rows named *@drill rerun the same mutation against the lab drills (test_signing_lab.AllDrills)."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
RM, CHAIN, TOOL, KIT = 'scripts/signing/report_manifest.py', 'scripts/signing/chain.py', 'scripts/signing/keytool.py', 'router-test-kit/02-install.sh'
REPORT = ('test_signing_report',)
INSTALL = ('test_signing_install.InstallSignatureTests', 'test_signing_install.KitConsistencyTests')
DRILLS = ('test_signing_lab.AllDrills',)
MUTATIONS = [
    # -- the manifest: format, files, signature, chain link
    ('manifest-bytes-not-canonical-checked', RM, "    if chain.canonical(manifest) != data:\n", "    if False:\n", REPORT),
    ('manifest-schema-unchecked', RM, "    if manifest['schema'] != SCHEMA:\n", "    if False:\n", REPORT),
    ('file-hash-ignored', RM, "if digest != row['sha256'] or size != row['size']:", "if size != row['size']:", REPORT),
    ('file-missing-ignored', RM, "            problems.append(('EVIDENCE-FILE-MISSING', row['path'], 'not found under %s' % base))\n            continue\n",
     "            continue\n", REPORT),
    ('bundle-extra-file-ignored', RM, "                if name not in known:\n", "                if False:\n", REPORT),
    ('signature-not-verified', RM, "            signer = usign_format.verify_file(keytool.trusted_keys(Path(root)), data, signature.read_bytes(),\n"
     "                                              [key_id for key_id, first in revoked if seq >= first])\n",
     "            signer = next(iter(keytool.trusted_keys(Path(root))))\n", REPORT),
    ('revoked-signer-accepted', RM, "[key_id for key_id, first in revoked if seq >= first])", "[])", REPORT),
    ('signer-may-differ-from-chain-entry', RM, "            if entry is not None and entry['key_id'] != signer:\n", "            if False:\n", REPORT),
    ('missing-signature-accepted', RM, "    if not signature.is_file():\n        add('EVIDENCE-SIGNATURE-MISSING'", "    if False:\n        add('EVIDENCE-SIGNATURE-MISSING'", REPORT),
    ('chain-link-not-required', RM, "    if entry is None and entries:\n", "    if False:\n", REPORT),
    ('chain-link-any-hash', RM, "candidate.get(chain.EVIDENCE_KEY) == report['manifest_sha256']", "candidate.get(chain.EVIDENCE_KEY) is not None", REPORT),
    ('chain-entry-release-unchecked', RM, "        if entry['package_version'] != manifest['package_version'] or entry['source_commit'] != manifest['source_commit']:\n",
     "        if False:\n", REPORT),
    ('chain-errors-swallowed', RM, "        add('EVIDENCE-CHAIN-INVALID', '', str(error))\n", "        pass\n", REPORT),
    # -- the manifest rules
    ('path-dotdot-allowed', RM, "    if any(part in ('', '.', '..') for part in parts):\n        raise ReportError(code, text)\n", "", REPORT),
    ('path-unsorted-allowed', RM, "    if paths != sorted(paths) or len(set(paths)) != len(paths):\n", "    if False:\n", REPORT),
    ('empty-category-contradiction-allowed', RM, " or row['category'] in empty", "", REPORT),
    ('symlink-followed', RM, "                if path.is_symlink():\n                    raise ReportError('EVIDENCE-SYMLINK'", "                if False:\n                    raise ReportError('EVIDENCE-SYMLINK'", REPORT),
    ('required-category-optional', RM, "            if not hits and category in required:\n", "            if False:\n", REPORT),
    ('evidence-overwritten', RM, "    if target.exists() or Path(str(target)+'.sig').exists():\n", "    if False:\n", REPORT),
    ('duplicate-paths-allowed', RM, "        if row['path'] in seen:\n", "        if False:\n", REPORT),
    # -- signing
    ('sign-evidence-hash-not-in-entry', TOOL, "evidence_sha256=evidence[1] if evidence else None)", "evidence_sha256=None)", REPORT),
    ('sign-manifest-signature-not-written', TOOL, "        Path(str(evidence[2])+'.sig').write_bytes(key.sign_file(evidence[0]))\n", "        pass\n", REPORT),
    ('sign-changed-files-accepted', RM, "    problems = check_files(directory, manifest)\n    if problems:\n        raise ReportError(problems[0][0]",
     "    problems = []\n    if problems:\n        raise ReportError(problems[0][0]", REPORT),
    ('sign-other-release-accepted', RM, "    if manifest['package_version'] != package_version or manifest['source_commit'] != source_commit:\n", "    if False:\n", REPORT),
    ('sign-already-signed-accepted', RM, "    if Path(str(path)+'.sig').exists():\n        raise ReportError('EVIDENCE-ALREADY-SIGNED'",
     "    if False:\n        raise ReportError('EVIDENCE-ALREADY-SIGNED'", REPORT),
    # -- the chain field
    ('chain-evidence-field-not-parsed', CHAIN, '(?:"evidence_sha256":"[0-9a-f]{64}",)?', '', REPORT+INSTALL),
    ('chain-evidence-upper-case-allowed', CHAIN, '"evidence_sha256":"[0-9a-f]{64}"', '"evidence_sha256":"[0-9a-fA-F]{64}"', REPORT),
    ('chain-evidence-in-imported-history', CHAIN, "        if EVIDENCE_KEY in entry and entry['origin'] != 'release':\n", "        if False:\n", REPORT),
    ('chain-evidence-key-not-writable', CHAIN, "not in (ENTRY_KEYS, ENTRY_KEYS_WITH_EVIDENCE)", "not in (ENTRY_KEYS,)", REPORT),
    ('chain-evidence-silently-dropped', CHAIN, "    if evidence_sha256 is not None:\n        entry[EVIDENCE_KEY] = evidence_sha256", "    if False:\n        entry[EVIDENCE_KEY] = evidence_sha256", REPORT),
    # -- the router kit
    ('kit-does-not-strip-evidence', KIT, 'EVID_RE=\'\\("date_utc":"[0-9TZ:-]*",\\)"evidence_sha256":"[0-9a-f]\\{64\\}",\'',
     'EVID_RE=\'\\("date_utc":"[0-9TZ:-]*",\\)"evidence_sha256":"[0-9a-f]\\{65\\}",\'', INSTALL),
    ('kit-evidence-upper-case-allowed', KIT, 'EVID_RE=\'\\("date_utc":"[0-9TZ:-]*",\\)"evidence_sha256":"[0-9a-f]\\{64\\}",\'',
     'EVID_RE=\'\\("date_utc":"[0-9TZ:-]*",\\)"evidence_sha256":"[0-9a-fA-F]\\{64\\}",\'', INSTALL),
    ('kit-signs-the-stripped-entry', KIT, 'printf \'%s\\n\' "$line" | sed -n "s|$ENTRY_RE|\\1|p"', 'printf \'%s\\n\' "$plain" | sed -n "s|$ENTRY_RE|\\1|p"', INSTALL),
    ('kit-revocations-miss-evidence-lines', KIT, 'add_revocations "$(sed "s|$EVID_RE|\\1|" "$CHAIN" | sed -n "s|$LINE_RE|\\5|p")"',
     'add_revocations "$(sed -n "s|$LINE_RE|\\5|p" "$CHAIN")"', INSTALL),
    # -- the same guards, caught by the lab drill itself
    ('file-hash-ignored@drill', RM, "if digest != row['sha256'] or size != row['size']:", "if size != row['size']:", DRILLS),
    ('file-missing-ignored@drill', RM, "            problems.append(('EVIDENCE-FILE-MISSING', row['path'], 'not found under %s' % base))\n            continue\n",
     "            continue\n", DRILLS),
    ('chain-link-not-required@drill', RM, "    if entry is None and entries:\n", "    if False:\n", DRILLS),
    ('signature-not-verified@drill', RM, "            signer = usign_format.verify_file(keytool.trusted_keys(Path(root)), data, signature.read_bytes(),\n"
     "                                              [key_id for key_id, first in revoked if seq >= first])\n",
     "            signer = next(iter(keytool.trusted_keys(Path(root))))\n", DRILLS),
    ('manifest-bytes-not-canonical-checked@drill', RM, "    if chain.canonical(manifest) != data:\n", "    if False:\n", DRILLS),
    ('kit-does-not-strip-evidence@drill', KIT, 'EVID_RE=\'\\("date_utc":"[0-9TZ:-]*",\\)"evidence_sha256":"[0-9a-f]\\{64\\}",\'',
     'EVID_RE=\'\\("date_utc":"[0-9TZ:-]*",\\)"evidence_sha256":"[0-9a-f]\\{65\\}",\'', DRILLS),
]
results = []
for name, path, old, new, tests in MUTATIONS:
    if len(sys.argv) > 2 and name not in sys.argv[2].split(','):
        continue
    target = root/path
    original = target.read_bytes().decode('utf-8')
    if original.count(old) != 1:
        results.append({'mutation': name, 'result': 'NOT-APPLIED'})
        print(name, 'NOT-APPLIED', file=sys.stderr, flush=True)
        continue
    target.write_bytes(original.replace(old, new, 1).encode('utf-8'))
    try:
        run = subprocess.run([sys.executable, '-m', 'unittest']+list(tests), cwd=root/'qa', capture_output=True, text=True, timeout=3000,
                             env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'PYTHONDONTWRITEBYTECODE': '1'})
        tail = run.stderr.strip().splitlines()[-1] if run.stderr.strip() else ''
        results.append({'mutation': name, 'tests': list(tests), 'result': 'KILLED' if run.returncode else 'SURVIVED', 'summary': tail})
    finally:
        target.write_bytes(original.encode('utf-8'))
    print(results[-1]['mutation'], results[-1]['result'], file=sys.stderr, flush=True)
killed = sum(row['result'] == 'KILLED' for row in results)
print(json.dumps({'killed': killed, 'total': len(results), 'rows': results}, indent=1))
raise SystemExit(0 if killed == len(results) else 1)
