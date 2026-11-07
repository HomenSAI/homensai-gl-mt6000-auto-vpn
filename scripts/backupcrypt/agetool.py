"""Portable encryption of the private backups with age (X25519), owner-held identity.

Guide: docs/architecture/AGE-TOFU-2026-11-04.ru.md. Same owner-held pattern as the release signing keys
(scripts/signing, branch feat/usign-signing-20261103): the secret lives only in the DPAPI store private/signing of the
main checkout (age-backup.identity.dpapi), is shown only after the authenticator code (one TOTP enrolment for both
tools: totp.seed.dpapi), goes into the owner's password manager / paper QR, and is imported back on a new PC.
The recipient (age1..., public) is in scripts/backupcrypt/recipients.txt AND pinned locally in the store
(age-backup.recipient.txt): encryption refuses when the two differ, so an edited repository file cannot redirect the
backups to somebody else's key. Encryption needs no secret, so the unattended USB backup can run it.

  new-identity [--replace]         create the identity (once; --replace retires the old one, never deletes it)
  setup-totp                       enrol the authenticator app if the signing tool has not done it yet
  reveal [--qr console|html|none]  show AGE-SECRET-KEY-1... for the password manager / paper (TOTP required)
  import [--replace]               put a pasted identity into this PC's DPAPI store (input hidden; must match the pin)
  recipients [--trust-repo]        show repository and pinned recipients; --trust-repo pins the repository list
  encrypt --in F --out F.age       encrypt any file to the pinned recipients (no secret needed)
  decrypt --in F.age --out F       decrypt with the stored identity, or a pasted one with --paste-identity
  secrets-archive --out DIR|FILE   the opt-in secrets archive of the USB backup (secrets_archive.py), JSON summary
          [--private P] [--also-json J] [--router-backups N]
  restore-secrets --archive F --into DIR [--paste-identity]   unpack it on a new PC (keys DPAPI-protected again)
  verify-archive --archive F [--list]   header check (no secret); --list decrypts in memory and prints names only
"""
import argparse
import getpass
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SIGNING = ROOT/'scripts'/'signing'
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(SIGNING))
import age_format as age  # noqa: E402
import lab_mode  # noqa: E402
import secrets_archive  # noqa: E402
import qr  # noqa: E402  (vendored byte-identical from feat/usign-signing-20261103)
import secret_store  # noqa: E402
import totp  # noqa: E402

IDENTITY = 'age-backup.identity.dpapi'
PIN = 'age-backup.recipient.txt'
REPO_RECIPIENTS = HERE/'recipients.txt'
TEST_ENV = 'HOMENSAI_SIGNING_TEST'


class ToolError(ValueError):
    pass


# ---- recipients ---------------------------------------------------------------------------------------------------

def parse_recipients(text):
    out = []
    for line in (text or '').splitlines():
        line = line.split('#', 1)[0].strip()
        if line:
            try:
                out.append(age.Recipient.parse(line))
            except age.AgeError as error:
                raise ToolError('RECIPIENTS-FORMAT: %s' % error) from None
    if len(set(out)) != len(out):
        raise ToolError('RECIPIENTS-DUPLICATE')
    return out


def repo_recipients(path=None):
    path = Path(path or REPO_RECIPIENTS)
    return parse_recipients(path.read_text(encoding='utf-8')) if path.is_file() else []


def pinned_recipients(store):
    path = store.path(PIN)
    return parse_recipients(path.read_text(encoding='utf-8')) if path.is_file() else []


def write_recipients(path, recipients, header):
    lines = [header] + [r.encode() for r in recipients]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(lines)+'\n')


REPO_HEADER = ('# Public age recipients of the HomenS.AI private backups (scripts/backupcrypt/agetool.py, '
               'docs/architecture/AGE-TOFU-2026-11-04.ru.md).\n# Encryption also checks the copy pinned in the '
               "owner's DPAPI store; edit only with `agetool.py recipients --trust-repo` after review.")
PIN_HEADER = '# Pinned copy of scripts/backupcrypt/recipients.txt (public). Written by agetool.py.'


def encryption_recipients(store, repo_path=None):
    """The recipients to encrypt to: the pinned set, which must equal the repository set."""
    pinned, repo = pinned_recipients(store), repo_recipients(repo_path)
    if not pinned:
        raise ToolError('RECIPIENTS-NOT-PINNED: run `agetool.py new-identity` (or import, then recipients --trust-repo)')
    if set(pinned) != set(repo):
        raise ToolError('RECIPIENTS-MISMATCH: scripts/backupcrypt/recipients.txt differs from the pinned copy in %s; '
                        'review the change, then `agetool.py recipients --trust-repo`' % store.root)
    return pinned


# ---- interaction ------------------------------------------------------------------------------------------------

class Console:
    """Owner interaction; tests replace it. A TOTP code may be injected only when HOMENSAI_SIGNING_TEST=1."""
    def __init__(self, test_code=None):
        if test_code is not None and os.environ.get(TEST_ENV) != '1':
            raise ToolError('TOTP-TEST-CODE-REFUSED: --test-totp-code works only in a test run (%s=1)' % TEST_ENV)
        self.test_code = test_code

    def code(self, prompt='Current 6-digit code from the authenticator app: '):
        return self.test_code if self.test_code is not None else input(prompt)

    def secret(self, prompt):
        return getpass.getpass(prompt)

    def say(self, text=''):
        print(text, flush=True)

    def show_qr(self, text, mode, title):
        if mode == 'none':
            return
        matrix = qr.encode(text, ecc='Q')
        if mode == 'console':
            self.say(qr.render_console(matrix, border=4))
            return
        handle, name = tempfile.mkstemp(prefix='homensai-qr-', suffix='.html')
        try:
            page = ('<!doctype html><meta charset="utf-8"><title>%s</title><style>body{font:16px sans-serif;margin:24px}'
                    'code{font-size:18px;word-break:break-all}</style><h1>%s</h1>%s<p><code>%s</code></p>'
                    '<p>Close this page after printing or scanning; the file is overwritten and deleted.</p>' %
                    (title, title, qr.render_svg(matrix, scale=8, border=4), text))
            with os.fdopen(handle, 'w', encoding='utf-8') as stream:
                stream.write(page)
            os.startfile(name)  # Windows only, like the DPAPI store.
            input('Press Enter when you have printed or scanned the QR (the page file is then wiped)... ')
        finally:
            secret_store.wipe(name)


def require_totp(store, console):
    if not store.has('totp.seed.dpapi'):
        raise ToolError('TOTP-NOT-ENROLLED: run `agetool.py setup-totp` (or `keytool.py setup-totp`) first')
    seed = store.read_secret('totp.seed.dpapi').decode('ascii')
    try:
        totp.check_code(seed, console.code(), str(store.path('totp-state.json')), getattr(console, 'now', lambda: None)())
    except totp.TotpError as error:
        raise ToolError(str(error)) from None


def load_identity(store):
    try:
        identity = age.Identity.parse(store.read_secret(IDENTITY).decode('ascii'))
    except secret_store.StoreError:
        raise ToolError('IDENTITY-MISSING: no age identity in %s (new-identity, or import on a new PC)' % store.root) from None
    return identity


def pasted_identity(console):
    text = console.secret('Paste the age identity (AGE-SECRET-KEY-1...; input is hidden): ')
    try:
        return age.Identity.parse(''.join(text.split()))
    except age.AgeError as error:
        raise ToolError('IMPORT-FORMAT: %s' % error) from None


# ---- commands -----------------------------------------------------------------------------------------------------

def cmd_new_identity(args, store, console):
    if store.has(IDENTITY) and not args.replace:
        raise ToolError('IDENTITY-EXISTS: an age identity already exists; --replace only if it is lost or stolen')
    identity = age.Identity.generate()
    store.write_secret(IDENTITY, identity.encode().encode('ascii'), replace=args.replace)
    recipients = [identity.recipient()]
    if store.has(PIN):
        store.retire(PIN)
    write_recipients(store.path(PIN), recipients, PIN_HEADER)
    write_recipients(args.repo_recipients or REPO_RECIPIENTS, recipients, REPO_HEADER)
    console.say('AGE-IDENTITY-CREATED recipient %s' % identity.recipient().encode())
    console.say('The secret is only in %s (DPAPI). Next: setup-totp (if not enrolled), then reveal, and commit '
                'scripts/backupcrypt/recipients.txt.' % store.root)
    if args.replace:
        console.say('Archives made for the old recipient still need the OLD identity (kept retired in the store and, '
                    'hopefully, in the password manager).')


def cmd_setup_totp(args, store, console):
    if store.has('totp.seed.dpapi'):
        raise ToolError('TOTP-EXISTS: the authenticator is already enrolled (shared with the release signing tool)')
    seed = totp.new_seed()
    console.say('Scan this QR with Google Authenticator (account "%s"):' % totp.ACCOUNT)
    console.show_qr(totp.otpauth_uri(seed), args.qr, 'HomenS.AI owner secrets - authenticator')
    console.say('Manual entry key: %s' % ' '.join(seed[i:i+4] for i in range(0, len(seed), 4)))
    code = console.code('Enter the 6-digit code the app now shows, to confirm: ')
    state = str(store.path('totp-state.json'))
    store.root.mkdir(parents=True, exist_ok=True)
    if os.path.exists(state):
        os.replace(state, state+'.retired')
    try:
        totp.check_code(seed, code, state)
    except totp.TotpError as error:
        raise ToolError('TOTP-ENROL-FAILED: %s (nothing was saved; run the command again)' % error) from None
    store.write_secret('totp.seed.dpapi', seed.encode('ascii'), replace=True)
    console.say('TOTP-ENROLLED: reveal (age and release keys) now asks for a code.')


def cmd_reveal(args, store, console):
    require_totp(store, console)
    identity = load_identity(store)
    payload = identity.encode()
    console.say('age identity for recipient %s' % identity.recipient().encode())
    console.say('Store this line in the password manager exactly (it also works with the official age tool):')
    console.say(payload)
    console.show_qr(payload, args.qr, 'HomenS.AI backup age identity')
    console.say('Never paste it into chats, tickets or the repository.')


def cmd_import(args, store, console):
    identity = pasted_identity(console)
    pinned = pinned_recipients(store) or repo_recipients(args.repo_recipients)
    if identity.recipient() not in pinned:
        raise ToolError('IMPORT-UNKNOWN-IDENTITY: its recipient %s is not in the pinned/repository recipients' %
                        identity.recipient().encode())
    store.write_secret(IDENTITY, identity.encode().encode('ascii'), replace=args.replace)
    if not store.has(PIN):
        write_recipients(store.path(PIN), pinned, PIN_HEADER)
    console.say('IMPORTED age identity for %s into %s (DPAPI)' % (identity.recipient().encode(), store.root))


def cmd_recipients(args, store, console):
    repo, pinned = repo_recipients(args.repo_recipients), pinned_recipients(store)
    console.say('repository: %s' % (', '.join(r.encode() for r in repo) or '-'))
    console.say('pinned:     %s' % (', '.join(r.encode() for r in pinned) or '-'))
    if args.trust_repo:
        if not repo:
            raise ToolError('RECIPIENTS-EMPTY: the repository lists no recipient')
        if store.has(PIN):
            store.retire(PIN)
        write_recipients(store.path(PIN), repo, PIN_HEADER)
        console.say('PINNED the repository recipients')
    else:
        console.say('MATCH' if repo and set(repo) == set(pinned) else 'MISMATCH-OR-EMPTY')


def cmd_encrypt(args, store, console):
    recipients = encryption_recipients(store, args.repo_recipients)
    data = Path(args.input).read_bytes()
    out = Path(args.out)
    if out.exists():
        raise ToolError('OUT-EXISTS: %s' % out)
    out.write_bytes(age.encrypt(data, recipients, armored=args.armor))
    console.say('ENCRYPTED %s -> %s for %d recipient(s)' % (args.input, out, len(recipients)))


def identities_for(args, store, console):
    return [pasted_identity(console)] if args.paste_identity else [load_identity(store)]


def cmd_decrypt(args, store, console):
    out = Path(args.out)
    if out.exists():
        raise ToolError('OUT-EXISTS: %s' % out)
    data = age.decrypt(Path(args.input).read_bytes(), identities_for(args, store, console))
    with open(out, 'xb') as stream:
        stream.write(data)
    console.say('DECRYPTED %s -> %s (%d bytes). It is plaintext now: keep it off shared folders.' % (args.input, out, len(data)))


def cmd_secrets_archive(args, store, console):
    recipients = encryption_recipients(store, args.repo_recipients)
    out = Path(args.out)
    if out.is_dir():
        out = out/secrets_archive.ARCHIVE_NAME
    extra = json.loads(Path(args.also_json).read_text(encoding='utf-8')) if args.also_json else []
    private = Path(args.private) if args.private else Path(secret_store.default_root()).parent
    summary = secrets_archive.create(private, out, recipients, extra, router_backups=args.router_backups)
    console.say(json.dumps(summary, ensure_ascii=False, sort_keys=True))


def cmd_restore_secrets(args, store, console):
    written = secrets_archive.restore(Path(args.archive).read_bytes(), identities_for(args, store, console), args.into)
    console.say('RESTORED %d file(s) into %s (DPAPI keys protected again for this Windows user)' % (len(written), args.into))


def cmd_verify_archive(args, store, console):
    data = Path(args.archive).read_bytes()
    count = age.header_recipient_count(data)
    console.say('HEADER-OK x25519_recipients=%d size=%d' % (count, len(data)))
    if args.list:
        for name in secrets_archive.list_names(data, identities_for(args, store, console)):
            console.say(name)


COMMANDS = {'new-identity': cmd_new_identity, 'setup-totp': cmd_setup_totp, 'reveal': cmd_reveal, 'import': cmd_import,
            'recipients': cmd_recipients, 'encrypt': cmd_encrypt, 'decrypt': cmd_decrypt,
            'secrets-archive': cmd_secrets_archive, 'restore-secrets': cmd_restore_secrets,
            'verify-archive': cmd_verify_archive}


def parser():
    p = argparse.ArgumentParser(description='HomenS.AI portable backup encryption (docs/architecture/AGE-TOFU-2026-11-04.ru.md)')
    p.add_argument('command', choices=sorted(COMMANDS))
    p.add_argument('--replace', action='store_true')
    p.add_argument('--qr', choices=('console', 'html', 'none'), default='console')
    p.add_argument('--trust-repo', action='store_true')
    p.add_argument('--in', dest='input')
    p.add_argument('--out')
    p.add_argument('--armor', action='store_true')
    p.add_argument('--paste-identity', action='store_true')
    p.add_argument('--private')
    p.add_argument('--also-json')
    p.add_argument('--router-backups', type=int, default=secrets_archive.ROUTER_BACKUPS_DEFAULT,
                   help='secrets-archive: newest encrypted router exports to include (-1 all, 0 none)')
    p.add_argument('--archive')
    p.add_argument('--into')
    p.add_argument('--list', action='store_true')
    p.add_argument('--repo-recipients', help=argparse.SUPPRESS)
    p.add_argument('--test-totp-code', help='test runs only (%s=1)' % TEST_ENV)
    p.add_argument('--lab', help='work on this test lab instead of the real identity (or %s)' % lab_mode.ENV_DIR)
    return p


REQUIRED = {'encrypt': ('input', 'out'), 'decrypt': ('input', 'out'), 'secrets-archive': ('out',),
            'restore-secrets': ('archive', 'into'), 'verify-archive': ('archive',)}


def main(argv=None, store=None, console=None):
    args = parser().parse_args(argv)
    try:
        missing = [name for name in REQUIRED.get(args.command, ()) if not getattr(args, name)]
        if missing:
            raise ToolError('ARGUMENTS: %s needs --%s' % (args.command, ' --'.join(m if m != 'input' else 'in' for m in missing)))
        lab = lab_mode.resolve(args.lab)
        console = console or Console(args.test_totp_code)
        if lab is not None:
            console.say('*** %s ***' % (lab_mode.BANNER % lab))
            store = store or lab.store()
            args.repo_recipients = args.repo_recipients or str(lab.recipients)
        store = store or secret_store.Store()
        COMMANDS[args.command](args, store, console)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        # ToolError, StoreError, TotpError, AgeError and ArchiveError are ValueErrors with a stable code first.
        print('STOP: %s' % error, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
