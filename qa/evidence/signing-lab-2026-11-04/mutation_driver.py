"""Evidence driver (not a unit test): break one guard of the signing lab at a time in a COPY of the tree and prove the tests fail.
Run inside a throwaway Linux container:  python3 mutation_driver.py <copy of the repo> [names]  (prints JSON, exit 1 on a survivor)."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
MODE, STORE, TOOL, PUBLISH, WEB, DRILLS = ('scripts/signing/lab_mode.py', 'scripts/signing/secret_store.py', 'scripts/signing/keytool.py', 'scripts/publish-reviewed.py',
                                           'scripts/signing/lab_web.py', 'scripts/signing/lab_drills.py')
LAB = ('test_signing_lab.RealRefusesLab', 'test_signing_lab.LabRefusesReal', 'test_signing_lab.ResetTests', 'test_signing_lab.MaskTests')
WEBT = ('test_signing_lab_web',)
ALL = ('test_signing_lab.AllDrills',)
PUB = ('test_publication_record',)
MUTATIONS = [
    ('real-store-reads-lab', STORE, '(lab_mode.require_lab_path if self.lab else lab_mode.refuse_lab_path)(self.root)', 'pass', LAB),
    ('real-store-no-marker-check', MODE, 'if lab_ancestor(path) or DIR_NAME in path.parts:\n        raise LabRefused(\'STORE-LAB', 'if DIR_NAME in path.parts:\n        raise LabRefused(\'STORE-LAB', LAB),
    ('real-store-no-name-check', MODE, 'if lab_ancestor(path) or DIR_NAME in path.parts:\n        raise LabRefused(\'STORE-LAB', 'if lab_ancestor(path):\n        raise LabRefused(\'STORE-LAB', LAB),
    ('lab-store-anywhere', MODE, "    if not lab_ancestor(root):\n        raise LabRefused('STORE-NOT-A-LAB", "    if False:\n        raise LabRefused('STORE-NOT-A-LAB", LAB),
    ('lab-takes-real-store', MODE, 'if path == real or real in path.parents or path in real.parents:', 'if False:', LAB),
    ('lab-takes-store-parent', MODE, 'if path == real or real in path.parents or path in real.parents:', 'if path == real or path in real.parents:', LAB),
    ('lab-takes-store-child', MODE, 'if path == real or real in path.parents or path in real.parents:', 'if path == real or real in path.parents:', LAB),
    ('lab-takes-a-checkout', MODE, "if (path/'.git').exists():", 'if False:', LAB),
    ('lab-takes-used-folder', MODE, 'if path.is_dir() and not (path/MARKER).is_file() and any(path.iterdir()):', 'if False:', LAB),
    ('lab-takes-home', MODE, 'if path == Path(path.anchor) or path == Path.home():', 'if False:', LAB),
    ('reset-without-marker', MODE, "if not (self.root/MARKER).is_file():\n            raise LabRefused('LAB-RESET", "if False:\n            raise LabRefused('LAB-RESET", LAB),
    ('reset-no-recheck', MODE, 'self.root = check_lab_path(self.root)\n        if not', 'if not', LAB),
    ('lab-key-accepted-as-real', MODE, 'if is_lab_key_id(key_id) and not lab:', 'if False:', LAB),
    ('real-key-accepted-in-lab', MODE, 'if lab and not is_lab_key_id(key_id):', 'if False:', LAB),
    ('trust-list-unchecked', TOOL, "lab_mode.require_same_world(path.name, lab, 'KEYS')", 'pass', LAB),
    ('sign-unchecked', TOOL, "lab_mode.require_same_world(key.key_id.hex(), lab_mode.is_lab_tree(root), 'SIGN')", 'pass', LAB),
    ('import-unchecked', TOOL, "lab_mode.require_same_world(key.key_id.hex(), store.lab, 'IMPORT')", 'pass', LAB),
    ('tag-unchecked', TOOL, 'if (match.group(1) == lab_mode.PAYLOAD_TAG) != lab_mode.is_lab_key_id(match.group(3)):', 'if False:', LAB),
    ('pair-unchecked', MODE, "if is_lab_tree(root) != bool(getattr(store, 'lab', False)):", 'if False:', LAB),
    ('lab-keys-unprefixed', MODE, "return type(key)(key.seed, bytes.fromhex(KEY_ID_PREFIX)+key.key_id[4:], key.salt)", 'return key', LAB),
    ('real-keys-may-get-prefix', MODE, 'while is_lab_key_id(key.key_id):', 'while False:', LAB),
    ('same-entropy', STORE, 'secondary = ENTROPY_LAB if self.lab else None', 'secondary = None', LAB),
    ('lab-otpauth-looks-real', TOOL, 'return totp.otpauth_uri(seed, lab_mode.TOTP_ACCOUNT, lab_mode.TOTP_ISSUER) if store.lab else totp.otpauth_uri(seed)', 'return totp.otpauth_uri(seed)', LAB),
    ('auto-answers-for-real-store', DRILLS, "if not run.world.store.lab:", 'if False:', LAB),
    ('mask-keeps-key-line', DRILLS, "    if 'HSAI-SK1' in squeezed:\n        return 'HSAI-SK1'+MASKED\n", '', LAB),
    ('mask-keeps-recovery', DRILLS, "(re.compile(r'\\b%s\\b' % RECOVERY_RE), 'XXXX-XXXX-XXXX-XXXX-'+MASKED),", '', LAB),
    ('mask-keeps-age', DRILLS, "PATTERNS = [(re.compile(r'AGE-SECRET-KEY-1[0-9A-Za-z]+'), 'AGE-SECRET-KEY-1'+MASKED),\n            ", 'PATTERNS = [', LAB),
    ('publish-takes-lab-key', PUBLISH, "lab_mode.refuse_in_publication(keys,git_blob(source,'releases/CHAIN.jsonl'),", "(lambda *args:None)(keys,git_blob(source,'releases/CHAIN.jsonl'),", PUB),
    ('publish-code-swallowed', PUBLISH, '    except lab_mode.LabRefused:\n        raise\n', '', PUB),
    ('publish-in-lab-env', PUBLISH, '    lab_mode.refuse_lab_environment()\n', '', PUB),
    ('publish-chain-ids-unseen', MODE, "found |= set(re.findall(r'\"key_id\":\"(%s[0-9a-f]{8})\"' % KEY_ID_PREFIX, chain_data.decode('ascii', 'replace')))", 'pass', LAB),
    ('web-binds-everywhere', WEB, "HOST = '127.0.0.1'", "HOST = '0.0.0.0'", WEBT),
    ('web-any-host-header', WEB, "return self.headers.get('Host') == '%s:%d' % (HOST, self.server.server_address[1])", 'return True', WEBT),
    ('web-no-csrf', WEB, "if not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), self.app.csrf):", 'if False:', WEBT),
    ('web-any-origin', WEB, "if not self.host_ok() or origin not in (None, 'http://%s:%d' % (HOST, port)):", 'if not self.host_ok():', WEBT),
    ('web-cross-site-fetch', WEB, "if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):", 'if False:', WEBT),
    ('web-any-content-type', WEB, "if (self.headers.get('Content-Type') or '').split(';')[0].strip() != 'application/json':", 'if False:', WEBT),
    ('web-post-without-session', WEB, "        if not self.authorised():\n            return 'LAB-NO-SESSION'\n", '', WEBT),
    ('web-get-without-session', WEB, "        if not self.authorised():\n            return self.refuse(403, 'LAB-NO-SESSION')\n", '', WEBT),
    ('web-token-reusable', WEB, '        self.token = None\n        self.cookie = secrets.token_urlsafe(32)', '        self.cookie = secrets.token_urlsafe(32)', WEBT),
    ('web-token-never-expires', WEB, ' or time.monotonic()-self.token_born > TOKEN_SECONDS', '', WEBT),
    ('web-cookie-readable-by-script', WEB, '; HttpOnly; SameSite=Strict', '; SameSite=Strict', WEBT),
    ('web-secret-stays', WEB, "                    self.events[index] = {'type': 'secret-shown'}\n", '                    pass\n', WEBT),
    ('web-logs', WEB, '        """Nothing is logged: not the token, not a path, not an address."""', '        BaseHTTPRequestHandler.log_message(self, *arguments)', WEBT),
    ('web-reset-without-word', WEB, "if body.get('confirm') != 'RESET':", 'if False:', WEBT),
    ('web-two-drills-at-once', WEB, "        if self.active is not None and not self.active.done:\n            raise ValueError('LAB-BUSY: another drill is running')\n        op = Op(target)", '        op = Op(target)', WEBT),
    ('web-no-csp', WEB, "[('Content-Security-Policy', policy)]", '[]', WEBT),
    ('drill-refusal-ignored', DRILLS, "if code == 0 or expected not in stop:", 'if False:', ALL),
    ('drill-check-ignored', DRILLS, "        if not condition:\n            self.fail('Не выполнено: '+ru", "        if False:\n            self.fail('Не выполнено: '+ru", LAB),
]
results = []
for name, path, old, new, tests in MUTATIONS:
    if len(sys.argv) > 2 and name not in sys.argv[2].split(','):
        continue
    target = root/path
    original = target.read_text(encoding='utf-8')
    if original.count(old) != 1:
        results.append({'mutation': name, 'result': 'NOT-APPLIED'})
        continue
    target.write_text(original.replace(old, new, 1), encoding='utf-8')
    try:
        run = subprocess.run([sys.executable, '-m', 'unittest']+list(tests), cwd=root/'qa', capture_output=True, text=True, timeout=1800, env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'PYTHONDONTWRITEBYTECODE': '1'})
        tail = run.stderr.strip().splitlines()[-1] if run.stderr.strip() else ''
        results.append({'mutation': name, 'tests': list(tests), 'result': 'KILLED' if run.returncode else 'SURVIVED', 'summary': tail})
    finally:
        target.write_text(original, encoding='utf-8')
    print(results[-1]['mutation'], results[-1]['result'], file=sys.stderr, flush=True)
killed = sum(row['result'] == 'KILLED' for row in results)
print(json.dumps({'killed': killed, 'total': len(results), 'rows': results}, indent=1))
raise SystemExit(0 if killed == len(results) else 1)
