"""Evidence driver (not a unit test): break one verification step at a time in a COPY of the tree and prove the signing
tests fail. Run inside a throwaway Linux container:  python3 mutation_driver.py <copy of the repo>  (prints JSON)."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
MUTATIONS = [
    ('ed25519-accept-any', 'scripts/signing/usign_format.py', '    return _equal(_mul_base(s), _add(r, _mul(h, a)))', '    return True', 'test_signing_core.py'),
    ('chain-skip-signature', 'scripts/signing/chain.py', 'if not usign_format.verify(key.public, body, signature[10:]):', 'if False:', 'test_signing_core.py'),
    ('chain-skip-prev-link', 'scripts/signing/chain.py', "if entry['prev'] != prev:", 'if False:', 'test_signing_core.py'),
    ('chain-ignore-revocation', 'scripts/signing/chain.py', 'if any(key == signer and index >= first for key, first in revoked):', 'if False:', 'test_signing_core.py'),
    ('chain-ignore-key-id', 'scripts/signing/chain.py', "if signature[:2] != b'Ed' or signer != entry['key_id']:", "if signature[:2] != b'Ed':", 'test_signing_core.py'),
    ('payload-skip-checksum', 'scripts/signing/keytool.py', 'if not hmac.compare_digest(_check(body), match.group(5)):', 'if False:', 'test_signing_core.py'),
    ('totp-no-replay', 'scripts/signing/totp.py', "if matched is not None and matched <= state['last_step']:", 'if False:', 'test_signing_core.py'),
    ('totp-no-lockout', 'scripts/signing/totp.py', "    if state['locked_until'] > now:", '    if False:', 'test_signing_core.py'),
    ('kit-skip-chain-signature', 'router-test-kit/02-install.sh', 'usign -V -q -m "$work/entry" -x "$work/entry.sig" -p "$TRUST/$1" ||', 'true ||', 'test_signing_install.py'),
    ('kit-skip-package-signature', 'router-test-kit/02-install.sh', 'usign -V -q -m "$1" -x "$2" -p "$TRUST/$SIGNER" ||', 'true ||', 'test_signing_install.py'),
    ('kit-skip-prev-link', 'router-test-kit/02-install.sh', '[ "$3" = "$prev" ] ||', 'true ||', 'test_signing_install.py'),
    ('kit-ignore-revocations', 'router-test-kit/02-install.sh', '[ "${item%%:*}" = "$1" ] && [ "$2" -ge "${item#*:}" ] && return 0', ':', 'test_signing_install.py'),
    ('kit-no-head-check', 'router-test-kit/02-install.sh', '[ "$HEAD_SHA" = "$SHA" ] && [ "$HEAD_SIZE" = "$SIZE" ] && [ "$HEAD_VERSION" = "$EXPECTED_VERSION" ] ||', 'true ||', 'test_signing_install.py'),
    ('kit-no-fork-check', 'router-test-kit/02-install.sh', 'refuse CHAIN-FORK "the release history differs from the one installed on this router" 27', ':', 'test_signing_install.py'),
    ('kit-missing-signature-allowed', 'router-test-kit/02-install.sh', '[ "$ALLOW_UNSIGNED" = 1 ] || refuse SIGNATURE-MISSING', 'true || refuse SIGNATURE-MISSING', 'test_signing_install.py'),
    ('kit-trust-kit-on-upgrade', 'router-test-kit/02-install.sh', '  if [ "$TRUST_MODE" = first-install ]; then\n    for item in $TRUSTED_KEYS', '  if true; then\n    for item in $TRUSTED_KEYS', 'test_signing_install.py'),
    ('trust-key-no-confirmation', 'router/files/usr/sbin/homensai-vpn-trust-key', '[ "$ANSWER" = "$ID" ] ||', 'true ||', 'test_signing_install.py'),
    ('publication-skip-signatures', 'scripts/publish-reviewed.py', '        if extra:checked_signatures(parent,source,package_path,app[\'package_version\'])', '        pass', 'test_publication_record.py'),
]
results = []
for name, path, old, new, test in MUTATIONS:
    target = root/path
    original = target.read_text(encoding='utf-8')
    if original.count(old) != 1:
        results.append({'mutation': name, 'result': 'NOT-APPLIED'})
        continue
    target.write_text(original.replace(old, new), encoding='utf-8')
    try:
        run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'qa', '-p', test], cwd=root,
                             capture_output=True, text=True, timeout=1800)
        tail = run.stderr.strip().splitlines()[-1] if run.stderr.strip() else ''
        results.append({'mutation': name, 'test': test, 'result': 'KILLED' if run.returncode else 'SURVIVED', 'summary': tail})
    finally:
        target.write_text(original, encoding='utf-8')
print(json.dumps({'killed': sum(row['result'] == 'KILLED' for row in results), 'total': len(results), 'rows': results}, indent=2))
