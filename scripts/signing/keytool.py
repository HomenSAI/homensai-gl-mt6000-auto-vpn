"""Release signing on the owner's PC: keys, TOTP gate, signed release chain, OpenTimestamps anchoring.

Guide: docs/architecture/SIGNING-2026-11-03.ru.md. Every command is offline except the OpenTimestamps ones (they send
only a 32-byte hash). Secrets stay in the DPAPI store (secret_store.py) and are never printed except by `reveal`.
Wherever a command asks for the 6-digit code it also takes a one-time recovery code.

  new-keys [--emergency]           create main + reserve keys (once; --emergency replaces lost keys and revokes the old ids
                                   for every later release) and, the first time, sign the imported release history
  setup-totp                       enrol the authenticator app (Google Authenticator), confirm one code, get 10 recovery codes
  show-totp [--prove-key KEY]      show the enrolled TOTP QR again (needs a code, or a key secret if the phone is lost)
  reset-totp [--prove-key KEY]     new TOTP seed after a code (a recovery code if the phone is lost) or a main/reserve secret
  new-recovery-codes               replace the recovery codes (needs a code); every old recovery code stops working
  reveal --key main|reserve        show a secret for the password manager / paper (code required)
          [--qr console|html|none]
  import --key main|reserve        put a secret from the password manager back into the DPAPI store (new PC)
  sign-release --artifact releases/<ipk> --source-commit <sha> [--evidence DIR]
                                   TOTP, then <ipk>.sig, a new signed CHAIN.jsonl entry and its OpenTimestamps proof;
                                   with --evidence also DIR/EVIDENCE-MANIFEST.json.sig and the manifest hash in the entry
                                   (report_manifest.py builds the manifest and verifies it later)
  verify-release [--artifact ...]  check the whole chain, the package files and signatures (no secret needed)
  fingerprints                     key ids and full fingerprints of the trusted public keys
  ots-stamp | ots-upgrade | ots-status   anchor / complete / report the chain proofs in releases/ots/

--lab DIR (or HOMENSAI_SIGNING_DIR) runs every command on a test lab instead of the real keys: lab_mode.py,
docs/architecture/SIGNING-LAB-2026-11-04.ru.md. Test keys can never sign a real release.
"""
import argparse
import base64
import datetime
import getpass
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain  # noqa: E402
import lab_mode  # noqa: E402
import qr  # noqa: E402
import report_manifest  # noqa: E402
import secret_store  # noqa: E402
import totp  # noqa: E402
import usign_format  # noqa: E402

ROOT = HERE.parents[1]
KEYS_DIR = Path('router/files/etc/homensai-vpn/keys')
KIT = Path('router-test-kit/02-install.sh')
CHAIN = Path('releases/CHAIN.jsonl')
OTS_DIR = Path('releases/ots')
PAYLOAD = re.compile(r'(HSAI-SK1|%s):(MAIN|RESERVE):([0-9A-F]{16}):([A-Z2-7]{52}):([A-Z2-7]{8})' % lab_mode.PAYLOAD_TAG)
TEST_ENV = 'HOMENSAI_SIGNING_TEST'
ENROL_ATTEMPTS = 3


class ToolError(ValueError):
    pass


# ---- secret backup payload (password manager / QR / paper) ------------------------------------------------------

def _check(text):
    return base64.b32encode(hashlib.sha256(text.encode('ascii')).digest()[:5]).decode('ascii')


def secret_payload(name, key):
    """HSAI-SK1:<NAME>:<KEY ID>:<seed, base32>:<check>. Upper case only, so the QR uses the compact alphanumeric mode
    and a hand-typed copy is unambiguous; the check (SHA-256, 40 bits) catches a mistyped or misscanned character."""
    tag = lab_mode.PAYLOAD_TAG if lab_mode.is_lab_key_id(key.key_id) else 'HSAI-SK1'
    body = '%s:%s:%s:%s' % (tag, name.upper(), key.key_id.hex().upper(), base64.b32encode(key.seed).decode('ascii').rstrip('='))
    return body+':'+_check(body)


def parse_payload(text):
    compact = re.sub(r'\s+', '', text or '').upper()
    match = PAYLOAD.fullmatch(compact)
    if not match:
        raise ToolError('IMPORT-FORMAT: expected HSAI-SK1:<NAME>:<KEY ID>:<SECRET>:<CHECK>')
    body = compact.rsplit(':', 1)[0]
    if not hmac.compare_digest(_check(body), match.group(5)):
        raise ToolError('IMPORT-CHECKSUM: the text was mistyped or misscanned')
    if (match.group(1) == lab_mode.PAYLOAD_TAG) != lab_mode.is_lab_key_id(match.group(3)):
        raise ToolError('IMPORT-FORMAT: the line tag does not fit its key id')
    seed = base64.b32decode(match.group(4)+'====')
    key = usign_format.SecretKey(seed, bytes.fromhex(match.group(3)))
    return match.group(2).lower(), key


def grouped(text, size=4):
    return ' '.join(text[index:index+size] for index in range(0, len(text), size))


# ---- repository: trusted keys, revocations, install kit ---------------------------------------------------------

def chain_path(root):
    return root/(lab_mode.CHAIN_FILE if lab_mode.is_lab_tree(root) else CHAIN)


def trusted_keys(root):
    found = {}
    folder = root/KEYS_DIR
    lab = lab_mode.is_lab_tree(root)
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if re.fullmatch(r'[0-9a-f]{16}', path.name):
                lab_mode.require_same_world(path.name, lab, 'KEYS')
                key = usign_format.PublicKey.from_file(path.read_bytes())
                if key.key_id.hex() != path.name:
                    raise ToolError('KEYS-NAME-MISMATCH: %s' % path.name)
                found[path.name] = key
    return found


def revocations(root):
    path = root/KEYS_DIR/'revoked'
    return chain.parse_revocations(path.read_text(encoding='utf-8')) if path.is_file() else set()


def key_comment(name, key_id):
    if lab_mode.is_lab_key_id(key_id):
        return 'TEST LAB KEY, NEVER FOR A RELEASE: HomenS.AI test %s %s' % (name, key_id)
    return 'HomenS.AI Auto VPN release key %s %s' % (name, key_id)


def kit_literals(root):
    """TRUSTED_KEYS / REVOKED_KEYS lines of 02-install.sh from the repository key folder (one source of truth)."""
    keys = trusted_keys(root)
    trusted = ' '.join('%s:%s' % (key_id, base64.b64encode(key.to_bytes()).decode()) for key_id, key in sorted(keys.items()))
    revoked = ' '.join('%s:%d' % item for item in sorted(revocations(root)))
    return "TRUSTED_KEYS='%s'" % trusted, "REVOKED_KEYS='%s'" % revoked


def sync_kit(root):
    path = root/KIT
    text = path.read_text(encoding='utf-8')
    trusted, revoked = kit_literals(root)
    updated, one = re.subn(r"(?m)^TRUSTED_KEYS='[^'\n]*'$", trusted, text)
    updated, two = re.subn(r"(?m)^REVOKED_KEYS='[^'\n]*'$", revoked, updated)
    if one != 1 or two != 1:
        raise ToolError('KIT-LITERALS-MISSING')
    if updated != text:
        with path.open('w', encoding='utf-8', newline='') as stream:
            stream.write(updated)


def write_revocations(root, items):
    path = root/KEYS_DIR/'revoked'
    lines = ['# Revoked HomenS.AI release keys: "<key id>:<first chain seq>" (entries from that seq on are rejected).',
             '# Written by scripts/signing/keytool.py; see docs/architecture/SIGNING-2026-11-03.ru.md.']
    lines += ['%s:%d' % item for item in sorted(items)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(lines)+'\n')


def git(root, args):
    return subprocess.run(['git']+args, cwd=root, capture_output=True, text=True, check=True, timeout=120).stdout


def read_chain(root):
    path = chain_path(root)
    return path.read_bytes() if path.is_file() else b''


def verified_chain(root):
    data = read_chain(root)
    return chain.verify_chain(data, trusted_keys(root), revocations(root)), data


# ---- interaction ---------------------------------------------------------------------------------------------------

def recovery_page(codes, issued):
    rows = ''.join('<tr><td>%d</td><td class="code">%s</td><td class="box"></td></tr>' % (number, code)
                   for number, code in enumerate(codes, 1))
    return ('<!doctype html><meta charset="utf-8"><title>Recovery codes</title><style>body{font:14px sans-serif;margin:24px}'
            'table{border-collapse:collapse;margin:16px 0}td,th{border:1px solid #000;padding:8px 12px;text-align:left}'
            '.code{font:18px monospace;letter-spacing:1px}.box{width:64px}.note{color:#333}'
            '@media print{.screen{display:none}}</style>'
            '<h1>HomenS.AI Auto VPN: release signing recovery codes</h1>'
            '<p>Issued %s. Each code works once, instead of the 6-digit authenticator code. Tick a code after using it. '
            'Keep this sheet apart from the PC and the phone.</p>'
            '<p>Выдано %s. Каждый код работает один раз вместо 6-значного кода с телефона. Отметьте код после использования. '
            'Храните лист отдельно от ПК и телефона.</p>'
            '<table><tr><th>#</th><th>Code / Код</th><th>Used / Использован</th></tr>%s</table>'
            '<p class="note">Developer: Serhii Khomenko. Never paste these codes into chats, tickets or the repository.</p>'
            '<p class="screen"><b>Close this page after printing; the file is overwritten and deleted.</b></p>' %
            (issued, issued, rows))


def gate_clock(console):
    return getattr(console, 'now', lambda: None)()


class Console:
    """Owner interaction; tests replace it. A TOTP code may be injected only when HOMENSAI_SIGNING_TEST=1."""
    def __init__(self, test_code=None):
        if test_code is not None and os.environ.get(TEST_ENV) != '1':
            raise ToolError('TOTP-TEST-CODE-REFUSED: --test-totp-code works only in a test run (%s=1)' % TEST_ENV)
        self.test_code = test_code

    def code(self, prompt='Current 6-digit code from the authenticator app (or a recovery code if the phone is lost): '):
        return self.test_code if self.test_code is not None else input(prompt)

    def now(self):
        """The clock of the code gates: None is the real one. Only the lab's headless console has another."""
        return None

    def secret(self, prompt):
        return getpass.getpass(prompt)

    def confirm(self, prompt):
        return input(prompt)

    def say(self, text=''):
        print(text, flush=True)

    def show_qr(self, text, mode, title):
        if mode == 'none':
            return
        matrix = qr.encode(text, ecc='Q')
        if mode == 'console':
            self.say(qr.render_console(matrix, border=4))
            return
        self.show_page('<!doctype html><meta charset="utf-8"><title>%s</title><style>body{font:16px sans-serif;margin:24px}'
                       'code{font-size:18px;word-break:break-all}</style><h1>%s</h1>%s<p><code>%s</code></p>'
                       '<p>Close this page after printing or scanning; the file is overwritten and deleted.</p>' %
                       (title, title, qr.render_svg(matrix, scale=8, border=4), grouped(text)),
                       'Press Enter when you have printed or scanned the QR (the page file is then wiped)... ')

    def show_codes(self, codes, issued):
        self.show_page(recovery_page(codes, issued), 'Press Enter when you have printed the codes (the page file is then wiped)... ')

    def show_page(self, page, prompt):
        """The one way a secret reaches a file: a private temporary page, wiped however this ends."""
        handle, name = tempfile.mkstemp(prefix='homensai-qr-', suffix='.html')
        try:
            with os.fdopen(handle, 'w', encoding='utf-8') as stream:
                stream.write(page)
            os.startfile(name)  # Windows only, like the DPAPI store.
            input(prompt)
        finally:
            secret_store.wipe(name)


def report_recovery(codes, console, burned):
    left, problem = codes.remaining()
    if burned:
        console.say('RECOVERY-CODE-ACCEPTED: that code is used up and will never work again.')
    if problem:
        console.say('WARNING %s' % problem)
        return
    console.say('Recovery codes left: %d of %d.' % (left, totp.RECOVERY_COUNT))
    if left <= totp.RECOVERY_LOW:
        console.say('WARNING RECOVERY-CODES-LOW: only %d left; run `keytool.py new-recovery-codes`.' % left)


def require_totp(store, console, allow_no_seed=False):
    """The gate of every protected command: a 6-digit code or a recovery code. Prompts first, then takes the lock: the check
    and the burn are one step for other processes, and nothing protected runs before they are finished."""
    codes = totp.RecoveryCodes(store)
    seed = store.read_secret('totp.seed.dpapi').decode('ascii') if store.has('totp.seed.dpapi') else None
    if seed is None and not (allow_no_seed and codes.exists()):
        raise ToolError('TOTP-NOT-ENROLLED: run `keytool.py setup-totp` first')
    answer = console.code()
    try:
        with store.exclusive():
            method = totp.check_factor(seed, answer, str(store.path('totp-state.json')), codes, gate_clock(console))
    except totp.TotpError as error:
        raise ToolError(str(error)) from None
    report_recovery(codes, console, method == 'recovery')


def issue_recovery_codes(store, console):
    """Store first, show second: a crash can then cost a set nobody saw (the phone still works), never a set the owner
    wrote down but the store does not know. The codes appear here once and nowhere else."""
    plain = totp.new_recovery_codes()
    record = totp.recovery_record(plain)
    try:
        with store.exclusive():
            totp.RecoveryCodes(store).save(record, keep_old=True)
    except OSError:
        raise ToolError('RECOVERY-SAVE-FAILED: the new set could not be stored; any old set is unchanged. Run '
                        'new-recovery-codes again') from None
    console.say('RECOVERY CODES, shown only now. Each works once instead of the 6-digit code, for example if the phone is lost:')
    for number, code in enumerate(plain, 1):
        console.say('%2d. %s' % (number, code))
    console.say('Print them or write them down and keep them apart from this PC and the phone.')
    try:
        if console.confirm('Open a print-friendly page? The file is wiped afterwards. [y/N] ').strip().lower() in ('y', 'yes'):
            console.show_codes(plain, record['created_utc'])
        console.confirm('Press Enter when the codes are stored safely. They cannot be shown again... ')
    except EOFError:
        pass
    console.say('Only salted hashes are stored. `keytool.py new-recovery-codes` replaces the whole set.')


def otpauth(store, seed):
    return totp.otpauth_uri(seed, lab_mode.TOTP_ACCOUNT, lab_mode.TOTP_ISSUER) if store.lab else totp.otpauth_uri(seed)


def enrol_totp(store, console, qr_mode, keep_codes=False):
    """The confirmation runs on a trial state file: a failed enrolment leaves the seed, the lockout and the replay memory
    exactly as they were. A recovery code may already be burned by then, which is why a few attempts are allowed here."""
    seed = totp.new_seed()
    console.say('Scan this QR with Google Authenticator (account "%s"):' % (lab_mode.TOTP_ACCOUNT if store.lab else totp.ACCOUNT))
    console.show_qr(otpauth(store, seed), qr_mode, 'HomenS.AI release signing - authenticator')
    console.say('Manual entry key: %s' % grouped(seed))
    state = str(store.path('totp-state.json'))
    trial = state+'.enrol'
    store.root.mkdir(parents=True, exist_ok=True)
    try:
        for attempt in range(1, ENROL_ATTEMPTS+1):
            code = console.code('Enter the 6-digit code the app now shows, to confirm: ')
            try:
                totp.check_code(seed, code, trial, gate_clock(console))
                break
            except totp.TotpError as error:
                if attempt == ENROL_ATTEMPTS:
                    raise ToolError('TOTP-ENROL-FAILED: %s (nothing was saved; run the command again)' % error) from None
                console.say('That code did not confirm the new enrolment (%s). Try again.' % error)
        store.write_secret('totp.seed.dpapi', seed.encode('ascii'), replace=True)
        with store.exclusive():
            if os.path.exists(state):
                os.replace(state, state+'.retired-%d' % int(time.time()))
            os.replace(trial, state)
    finally:
        if os.path.exists(trial):
            os.remove(trial)
    console.say('TOTP-ENROLLED: every reveal and signing run now asks for a code.')
    codes = totp.RecoveryCodes(store)
    if keep_codes and codes.remaining()[0] > 0:
        report_recovery(codes, console, False)
    else:
        issue_recovery_codes(store, console)


def prove_key(root, store, console, name):
    """Ownership proof for TOTP recovery: the owner pastes the main or reserve secret from the password manager."""
    text = console.secret('Paste the %s key secret (HSAI-SK1:...) from the password manager: ' % name)
    named, key = parse_payload(text)
    lab_mode.require_same_world(key.key_id.hex(), store.lab, 'PROOF')
    if named != name:
        raise ToolError('PROOF-WRONG-KEY: this is the %s key' % named)
    trusted = trusted_keys(root).get(key.key_id.hex())
    if trusted is None or trusted.public != key.public:
        raise ToolError('PROOF-KEY-UNTRUSTED: the secret does not match a trusted public key')
    if any(key_id == key.key_id.hex() for key_id, _ in revocations(root)):
        raise ToolError('PROOF-KEY-REVOKED')
    return key


def load_secret(root, store, name):
    key = usign_format.SecretKey.from_file(store.read_secret(store.key_path(name).name))
    lab_mode.require_same_world(key.key_id.hex(), lab_mode.is_lab_tree(root), 'SIGN')
    trusted = trusted_keys(root).get(key.key_id.hex())
    if trusted is None or trusted.public != key.public:
        raise ToolError('SIGN-KEY-UNTRUSTED: the stored %s key is not a trusted repository key' % name)
    return key


# ---- commands ----------------------------------------------------------------------------------------------------

def utc(stamp=None):
    return datetime.datetime.fromtimestamp(time.time() if stamp is None else stamp, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def cmd_new_keys(args, root, store, console):
    existing = [name for name in secret_store.KEY_NAMES if store.key_path(name).exists()]
    old_ids = sorted(trusted_keys(root))
    if (existing or old_ids) and not args.emergency:
        raise ToolError('KEYS-EXIST: keys already exist; use --emergency only if every old secret is lost or stolen')
    entries = chain.verify_chain(read_chain(root), trusted_keys(root), revocations(root)) if read_chain(root) else []
    keys = {name: lab_mode.new_key(store.lab, usign_format.SecretKey.generate) for name in secret_store.KEY_NAMES}
    folder = root/KEYS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    for name, key in keys.items():
        (folder/key.key_id.hex()).write_bytes(key.public_file(key_comment(name, key.key_id.hex())))
    if args.emergency and old_ids:
        # Old keys stay in the trusted set for the history they signed; every entry from the next seq on is refused.
        write_revocations(root, revocations(root) | {(key_id, len(entries)) for key_id in old_ids})
    elif not (folder/'revoked').exists():
        write_revocations(root, set())
    for name, key in keys.items():
        store.write_secret(store.key_path(name).name, key.to_file(key_comment(name, key.key_id.hex())), replace=args.emergency)
    index = store.public_index()
    index.update({name: {'key_id': key.key_id.hex(), 'created_utc': utc(),
                         'full_fingerprint': usign_format.PublicKey(key.public, key.key_id).full_fingerprint()}
                  for name, key in keys.items()})
    store.write_public_index(index)
    sync_kit(root)
    if not entries and not read_chain(root):
        rows = chain.import_records(root, lambda argv: git(root, argv))
        lines, done = [], []
        for _, artifact, version, package_version, sha, size, commit, stamp in rows:
            entry = chain.next_entry(done, artifact, version, package_version, sha, size, commit, utc(stamp),
                                     keys['main'].key_id.hex(), origin='imported')
            lines.append(chain.make_line(entry, keys['main']))
            done.append(entry)
        chain_path(root).write_bytes(b'\n'.join(lines)+b'\n')
        chain.verify_chain(read_chain(root), trusted_keys(root), revocations(root))
        console.say('CHAIN-IMPORTED: %d historical releases signed by the new main key at import time' % len(lines))
    if args.emergency:
        store.retire('totp.seed.dpapi')
        store.retire(totp.RECOVERY_FILE)
    for name, key in keys.items():
        public = usign_format.PublicKey(key.public, key.key_id)
        console.say('KEY %s id=%s full_fingerprint=%s' % (name, key.key_id.hex(), public.full_fingerprint()))
    console.say('Secrets are only in %s (DPAPI). Next: setup-totp, then reveal --key main / --key reserve.' % store.root)
    if args.emergency:
        console.say('EMERGENCY: old key ids %s are revoked from chain seq %d. Routers that already trust the old keys need '
                    'the administrator to run homensai-vpn-trust-key with the new public key (or a factory reset).' %
                    (', '.join(old_ids) or '-', len(entries)))
        if not args.skip_totp:
            enrol_totp(store, console, args.qr)


def cmd_setup_totp(args, root, store, console):
    if store.has('totp.seed.dpapi'):
        raise ToolError('TOTP-EXISTS: use show-totp to add a phone, reset-totp to replace it')
    if store.has(totp.RECOVERY_FILE):
        # The seed vanished but its recovery set did not: a fresh enrolment here would need no proof at all.
        raise ToolError('TOTP-RECOVERY-EXISTS: use reset-totp with a recovery code, or reset-totp --prove-key main|reserve')
    enrol_totp(store, console, args.qr)


def cmd_show_totp(args, root, store, console):
    if args.prove_key:
        prove_key(root, store, console, args.prove_key)
    else:
        require_totp(store, console)
    seed = store.read_secret('totp.seed.dpapi').decode('ascii')
    console.show_qr(otpauth(store, seed), args.qr, 'HomenS.AI release signing - authenticator')
    console.say('Manual entry key: %s' % grouped(seed))


def cmd_reset_totp(args, root, store, console):
    if args.prove_key:
        prove_key(root, store, console, args.prove_key)
    else:
        require_totp(store, console, allow_no_seed=True)
    enrol_totp(store, console, args.qr, keep_codes=True)


def cmd_new_recovery_codes(args, root, store, console):
    require_totp(store, console)
    issue_recovery_codes(store, console)


def cmd_reveal(args, root, store, console):
    require_totp(store, console)
    key = usign_format.SecretKey.from_file(store.read_secret(store.key_path(args.key).name))
    payload = secret_payload(args.key, key)
    public = usign_format.PublicKey(key.public, key.key_id)
    console.say('Key %s, id %s, full fingerprint %s' % (args.key, key.key_id.hex(), public.full_fingerprint()))
    console.say('Store this line in the password manager (one line, spaces optional):')
    console.say(grouped(payload, 4))
    console.show_qr(payload, args.qr, 'HomenS.AI release key %s %s' % (args.key, key.key_id.hex()))
    console.say('Never paste it into chats, tickets or the repository.')


def cmd_import(args, root, store, console):
    named, key = parse_payload(console.secret('Paste the %s key secret (HSAI-SK1:...): ' % args.key))
    lab_mode.require_same_world(key.key_id.hex(), store.lab, 'IMPORT')
    if named != args.key:
        raise ToolError('IMPORT-WRONG-KEY: this is the %s key' % named)
    trusted = trusted_keys(root).get(key.key_id.hex())
    if trusted is None or trusted.public != key.public:
        raise ToolError('IMPORT-KEY-UNTRUSTED: no trusted public key %s with this value in %s' % (key.key_id.hex(), KEYS_DIR))
    store.write_secret(store.key_path(args.key).name, key.to_file(key_comment(args.key, key.key_id.hex())), replace=args.replace)
    index = store.public_index()
    index[args.key] = {'key_id': key.key_id.hex(), 'imported_utc': utc(), 'full_fingerprint': trusted.full_fingerprint()}
    store.write_public_index(index)
    console.say('IMPORTED %s key %s into %s (DPAPI)' % (args.key, key.key_id.hex(), store.root))


def cmd_sign_release(args, root, store, console, stamper=None):
    artifact = Path(args.artifact)
    artifact = artifact if artifact.is_absolute() else root/artifact
    match = re.fullmatch(r'homensai-auto-vpn_(%s)_all\.ipk' % chain.NAME, artifact.name)
    if not match or artifact.parent.resolve() != (root/'releases').resolve():
        raise ToolError('SIGN-ARTIFACT: expected releases/homensai-auto-vpn_<version>_all.ipk')
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_commit or ''):
        raise ToolError('SIGN-SOURCE-COMMIT: 40-hex tested source commit required')
    git(root, ['cat-file', '-e', args.source_commit+'^{commit}'])
    package_version = match.group(1)
    data = artifact.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    manifest = json.loads((root/'VERSION.json').read_text(encoding='utf-8-sig')).get('application', {})
    if manifest.get('artifact') == artifact.name and manifest.get('sha256') != digest:
        raise ToolError('SIGN-VERSION-MISMATCH: VERSION.json records another hash for this artifact')
    entries, _ = verified_chain(root)
    if any(entry['package_version'] == package_version for entry in entries):
        raise ToolError('SIGN-ALREADY-IN-CHAIN: %s' % package_version)
    evidence = report_manifest.prepare_signing(root, args.evidence, package_version, args.source_commit) if args.evidence else None
    require_totp(store, console)
    key = load_secret(root, store, args.key)
    revoked = revocations(root)
    if any(key_id == key.key_id.hex() and len(entries) >= first for key_id, first in revoked):
        raise ToolError('SIGN-KEY-REVOKED')
    declared = set()
    for entry in entries:
        declared |= chain.parse_revocations(entry['revoked'])
    pending = ' '.join('%s:%d' % item for item in sorted(revoked-declared))
    entry = chain.next_entry(entries, artifact.name, re.sub(r'-[0-9]+$', '', package_version), package_version, digest,
                             len(data), args.source_commit, utc(), key.key_id.hex(), revoked=pending,
                             evidence_sha256=evidence[1] if evidence else None)
    line = chain.make_line(entry, key)
    signature = key.sign_file(data)
    candidate = read_chain(root)+line+b'\n'
    chain.verify_chain(candidate, trusted_keys(root), revoked)
    chain_path(root).write_bytes(candidate)
    Path(str(artifact)+'.sig').write_bytes(signature)
    console.say('SIGNED %s with %s key %s; chain seq %d' % (artifact.name, args.key, key.key_id.hex(), entry['seq']))
    if evidence:
        Path(str(evidence[2])+'.sig').write_bytes(key.sign_file(evidence[0]))
        console.say('EVIDENCE-SIGNED %s sha256 %s, linked in chain seq %d' % (evidence[2], evidence[1], entry['seq']))
    if not args.no_ots:
        stamp_entries(root, console, [entry], stamper)


def stamp_entries(root, console, entries, stamper=None):
    import ots
    stamper = stamper or ots.stamp
    folder = root/OTS_DIR
    for entry in entries:
        target = folder/(entry['package_version']+'.ots')
        if target.exists():
            continue
        proof, report = stamper(hashlib.sha256(chain.canonical(entry)).digest())
        if proof is None:
            console.say('OTS-PENDING-RETRY %s: no calendar answered (%s); run `keytool.py ots-stamp` later' %
                        (entry['package_version'], ', '.join(sorted(report.get('failed', {})))))
            continue
        folder.mkdir(parents=True, exist_ok=True)
        target.write_bytes(proof)
        console.say('OTS-STAMPED %s via %s (pending Bitcoin confirmation; run ots-upgrade in a few hours)' %
                    (entry['package_version'], ', '.join(report.get('ok', []))))


def cmd_ots_stamp(args, root, store, console):
    entries, _ = verified_chain(root)
    wanted = [entry for entry in entries if entry['origin'] == 'release']
    imported = [entry for entry in entries if entry['origin'] == 'imported']
    stamp_entries(root, console, ([imported[-1]] if imported else [])+wanted)


def cmd_ots_upgrade(args, root, store, console):
    import ots
    for path in sorted((root/OTS_DIR).glob('*.ots')):
        data = path.read_bytes()
        new, report = ots.upgrade(data)
        if new != data:
            path.write_bytes(new)
        console.say('%s upgraded=%s pending=%s' % (path.name, report.get('upgraded'), len(report.get('pending', []))))


def ots_report(root, header_source=None):
    import ots
    entries, _ = verified_chain(root)
    rows = []
    for entry in entries:
        path = root/OTS_DIR/(entry['package_version']+'.ots')
        if path.exists():
            result = ots.verify(path.read_bytes(), hashlib.sha256(chain.canonical(entry)).digest(), header_source)
            rows.append(dict(package_version=entry['package_version'], seq=entry['seq'], **result))
    return rows


def cmd_ots_status(args, root, store, console):
    for row in ots_report(root):
        if row['status'] == 'confirmed':
            console.say('%s: confirmed in Bitcoin block %s at %s' % (row['package_version'], row.get('height'), row.get('time')))
        else:
            console.say('%s: %s (%s)' % (row['package_version'], row['status'], row.get('code')))


def verify_release(root, artifact=None):
    """Whole-chain check plus every package file that is in the repository. Raises ToolError/ChainError."""
    entries, data = verified_chain(root)
    keys, revoked = trusted_keys(root), revocations(root)
    checked = 0
    for entry in entries:
        package = root/'releases'/entry['artifact']
        if package.is_file():
            payload = package.read_bytes()
            if hashlib.sha256(payload).hexdigest() != entry['sha256'] or (entry['size'] is not None and len(payload) != entry['size']):
                raise ToolError('RELEASE-PACKAGE-MISMATCH: %s' % entry['artifact'])
            checked += 1
        signature = Path(str(package)+'.sig')
        if signature.is_file():
            usign_format.verify_file(keys, package.read_bytes(), signature.read_bytes(),
                                     [key_id for key_id, first in revoked if entry['seq'] >= first])
    head = entries[-1]
    if artifact:
        path = Path(artifact)
        path = path if path.is_absolute() else root/path
        named = re.fullmatch(r'homensai-auto-vpn_(%s)_all\.ipk' % chain.NAME, path.name)
        chain.check_head(entries, path.read_bytes(), named.group(1) if named else '-')
        if head['artifact'] != path.name:
            raise ToolError('RELEASE-HEAD-ARTIFACT: the newest chain entry is %s' % head['artifact'])
        signature = Path(str(path)+'.sig')
        if not signature.is_file():
            raise ToolError('SIGNATURE-MISSING: %s' % signature.name)
    return dict(result='PASS', entries=len(entries), head=head['package_version'], head_seq=head['seq'],
                packages_checked=checked, chain_sha256=hashlib.sha256(data).hexdigest(), trusted_keys=sorted(keys),
                revoked=sorted('%s:%d' % item for item in revoked))


def cmd_verify_release(args, root, store, console):
    console.say(json.dumps(verify_release(root, args.artifact), sort_keys=True))


def cmd_fingerprints(args, root, store, console):
    revoked = revocations(root)
    for key_id, key in sorted(trusted_keys(root).items()):
        comment = (root/KEYS_DIR/key_id).read_text(encoding='ascii').splitlines()[0]
        limit = [first for other, first in revoked if other == key_id]
        console.say('%s  full_fingerprint=%s  %s%s' % (key_id, key.full_fingerprint(), comment.replace('untrusted comment: ', ''),
                                                       '  REVOKED from seq %d' % min(limit) if limit else ''))


COMMANDS = {'new-keys': cmd_new_keys, 'setup-totp': cmd_setup_totp, 'show-totp': cmd_show_totp, 'reset-totp': cmd_reset_totp,
            'new-recovery-codes': cmd_new_recovery_codes, 'reveal': cmd_reveal, 'import': cmd_import, 'sign-release': cmd_sign_release, 'verify-release': cmd_verify_release,
            'fingerprints': cmd_fingerprints, 'ots-stamp': cmd_ots_stamp, 'ots-upgrade': cmd_ots_upgrade, 'ots-status': cmd_ots_status}


def parser():
    p = argparse.ArgumentParser(description='HomenS.AI release signing (docs/architecture/SIGNING-2026-11-03.ru.md)')
    p.add_argument('command', choices=sorted(COMMANDS))
    p.add_argument('--key', choices=secret_store.KEY_NAMES, default='main')
    p.add_argument('--prove-key', choices=secret_store.KEY_NAMES)
    p.add_argument('--qr', choices=('console', 'html', 'none'), default='console')
    p.add_argument('--emergency', action='store_true')
    p.add_argument('--skip-totp', action='store_true', help='new-keys --emergency: enrol the authenticator later')
    p.add_argument('--replace', action='store_true', help='import: replace an existing store entry (it is retired, not deleted)')
    p.add_argument('--artifact')
    p.add_argument('--source-commit')
    p.add_argument('--evidence', help='sign-release: folder with EVIDENCE-MANIFEST.json from report_manifest.py build')
    p.add_argument('--no-ots', action='store_true')
    p.add_argument('--test-totp-code', help='test runs only (%s=1)' % TEST_ENV)
    p.add_argument('--lab', help='work on this test lab instead of the real keys (or %s)' % lab_mode.ENV_DIR)
    return p


def main(argv=None, root=ROOT, store=None, console=None):
    args = parser().parse_args(argv)
    try:
        lab = lab_mode.resolve(args.lab)
        console = console or Console(args.test_totp_code)
        if lab is not None:
            console.say('*** %s ***' % (lab_mode.BANNER % lab))
            root, store = lab.repo, store or lab.store()
        store = store or secret_store.Store()
        lab_mode.check_pair(Path(root), store)
        COMMANDS[args.command](args, Path(root), store, console)
    except (ValueError, subprocess.CalledProcessError) as error:
        # ToolError, ChainError, StoreError, TotpError and usign format errors are all ValueErrors with a stable code.
        print('STOP: %s' % error, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
