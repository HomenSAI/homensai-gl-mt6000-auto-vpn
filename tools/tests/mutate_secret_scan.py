"""Mutation check of the secret scanner and its wiring (security audit 04.11.2026): every mutant must make
tools/tests/test_secret_scan.py fail. Each mutant is applied in place, the suite runs, the file is restored (also on error).
Run on a COPY of the checkout, never in the working tree you are editing:
  python tools/tests/mutate_secret_scan.py    -> one line per mutant, exit 1 when a mutant survives
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITE = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tools/tests', '-p', 'test_secret_scan.py', '-q']

MUTANTS = [
    # scanner rules
    ('scripts/secret_scan.py', "([A-Za-z0-9_-]{35})(?![A-Za-z0-9_-])", "([A-Za-z0-9_-]{36})(?![A-Za-z0-9_-])"),
    ('scripts/secret_scan.py', "[AEIMQUYcgkosw048]=)", "[Z]=)"),
    ('scripts/secret_scan.py', "('url_credentials', re.compile(rb'https?://[^/\\s:@]+:([^/\\s:@]{3,})@'), 1, 'value'),",
     "('url_credentials', re.compile(rb'(?!x)x'), 1, 'value'),"),
    ('scripts/secret_scan.py', "    if PLACEHOLDER.search(value):\n        return False\n", ""),
    ('scripts/secret_scan.py', "    if len(set(value)) <= 3:\n        return False\n", ""),
    ('scripts/secret_scan.py', "        if MARKER in data[start:end if end >= 0 else len(data)]:\n                continue\n", ""),
    ('scripts/secret_scan.py', "    elif base not in BAD_NAME_ALLOW and any(fnmatch.fnmatchcase(base, g) for g in (MEMBER_BAD_GLOBS if member else BAD_NAME_GLOBS)):",
     "    elif False:"),
    ('scripts/secret_scan.py', "    if any(d in BAD_DIRS for d in dirs)", "    if False"),
    ('scripts/secret_scan.py', "    elif base not in BAD_NAME_ALLOW and any(", "    elif any("),
    ('scripts/secret_scan.py', "    out = name_findings(path, allow, member=depth > 0)", "    out = name_findings(path, allow, member='!' in path)"),
    ('scripts/secret_scan.py', "BAD_NAME_ALLOW = ['.env.example']", "BAD_NAME_ALLOW = ['.env.example', '.env']"),
    # allowlist
    ('scripts/secret_scan.py', "        return any(fnmatch.fnmatchcase(path, glob) and ('*' in rules or rule in rules) for glob, rules in self.paths)",
     "        return any(fnmatch.fnmatchcase(path, glob) for glob, rules in self.paths)"),
    ('scripts/secret_scan.py', "            if not row.get('reason'):\n                raise ValueError('ALLOWLIST-REASON-MISSING')", "            pass"),
    ('scripts/secret_scan.py', "globs is None or any(fnmatch.fnmatchcase(path, g) for g in globs)", "True"),
    # archives and modes
    ('scripts/secret_scan.py', "    if is_zip or is_gz or is_tar:\n        if depth >= MAX_DEPTH:", "    if False:\n        if depth >= MAX_DEPTH:"),
    ('scripts/secret_scan.py', "            return out + incomplete(path, 'archive_too_deep', allow)", "            return out"),
    ('scripts/secret_scan.py', "                return incomplete(path + '!' + name, 'archive_member_too_large', allow)", "                return []"),
    ('scripts/secret_scan.py', "            return out + incomplete(path, 'archive_unreadable', allow)", "            return out"),
    ('scripts/secret_scan.py', "        return out + scan_text(path, data, allow, BINARY_KINDS)", "        return out"),
    ('scripts/secret_scan.py', "        if text is not None:\n            return out + scan_text(path, text, allow)", "        if False:\n            return out + scan_text(path, text, allow)"),
    ('scripts/secret_scan.py', "    raw = git(['diff', '--cached', '--name-only', '-z', '--diff-filter=ACMR'], repo, git_dir)",
     "    raw = git(['diff', '--name-only', '-z', '--diff-filter=ACMR'], repo, git_dir)"),
    ('scripts/secret_scan.py', "    raw = git(['rev-list', '--objects'] + args, repo, git_dir)", "    raw = git(['rev-list', '--objects'] + [a for a in args if a != '--not'], repo, git_dir)"),
    ('scripts/secret_scan.py', "        elif a.tree:\n            files, findings = scan_entries(tree_entries(a.tree, repo, a.git_dir), repo, a.git_dir, allow)",
     "        elif a.tree:\n            files, findings = 0, []"),
    ('scripts/secret_scan.py', "            files, findings = scan_files(names, a.root, allow)\n            label = 'manifest'", "            files, findings = 0, []\n            label = 'manifest'"),
    ('scripts/secret_scan.py', "    if findings:\n        print('SECRET-SCAN-FAIL", "    if False:\n        print('SECRET-SCAN-FAIL"),
    # wiring
    ('tools/gitflow.py', "        if found:raise FlowError('SECRET-PATTERN-STAGED')\n    def save_primary", "        if False:raise FlowError('SECRET-PATTERN-STAGED')\n    def save_primary"),
    ('tools/gitflow.py', "                    if found:raise FlowError('SECRET-PATTERN-IN-PUBLICATION')", "                    pass"),
    ('scripts/publish-reviewed.py', "    scan_secrets('--tree', source, repo=repo)", "    pass"),
    ('scripts/publish-reviewed.py', "    scan_secrets('--range', public, '--not', parent, repo=repo)", "    pass"),
    ('scripts/publish-reviewed.py', "    if reply.returncode:\n        sys.stderr.write", "    if False:\n        sys.stderr.write"),
    ('scripts/publish-reviewed.py', "    scan_publication(a.source,[f for f in (a.artifact,a.notes) if f]+list(signed.values()))\n", ""),
    ('qa/run_offline_ci.py', "    check([sys.executable,'scripts/secret_scan.py','--manifest',str(args.manifest),'--root','.'])\n", ""),
    ('.githooks/pre-commit', "fi\npython scripts/secret_scan.py --staged || { echo \"pre-commit: secret scan failed, nothing committed\" >&2; exit 1; }",
     "fi\npython scripts/secret_scan.py --staged || true"),
    ('.githooks/pre-commit', "if [ ! -f scripts/secret_scan.py ]; then", "if false; then"),
    ('.gitignore', "*.dpapi\n", ""),
    ('.gitignore', ".claude/worktrees/\n", ""),
]


def run(mutant):
    name, old, new = mutant
    path = ROOT / name
    text = path.read_bytes().decode('utf-8').replace('\r\n', '\n')
    if text.count(old) != 1:
        return 'BROKEN (pattern found %d times)' % text.count(old)
    try:
        path.write_bytes(text.replace(old, new, 1).encode('utf-8'))
        result = subprocess.run(SUITE, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
        return 'killed' if result.returncode != 0 else 'SURVIVED'
    finally:
        path.write_bytes(text.encode('utf-8'))


def main():
    bad = 0
    for mutant in MUTANTS:
        verdict = run(mutant)
        print('%-9s %s: %s' % (verdict.split()[0], mutant[0], mutant[1][:70].replace('\n', ' ')))
        if verdict != 'killed':
            bad += 1
    print('mutants %d, not killed %d' % (len(MUTANTS), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
