"""TOTP second factor for the signing step (RFC 6238 over RFC 4226 HOTP; SHA-1, 6 digits, 30 s: the Google Authenticator
defaults). Standard library only. The seed never leaves the DPAPI store except as the enrolment QR on the owner's screen.

The gate (check_code) allows one step of clock skew either way, refuses a code from a step already used (replay), counts
wrong codes and locks for LOCK_SECONDS after MAX_FAILURES in a row. The state file holds no secret.

Recovery codes (check_recovery) are the paper fallback for a lost phone, like the ones Google gives. Each is 80 random bits
plus a 20-bit check, written XXXX-XXXX-XXXX-XXXX-CCCC, and works once. Only per-code salted scrypt hashes are kept, inside a
DPAPI blob. They share the wrong-code counter and the lockout of the TOTP gate. The check catches typos before any hash is
computed, so a typo neither burns a code nor counts as a wrong one: it says nothing about the stored codes.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import time
from urllib.parse import quote

DIGITS, PERIOD, SKEW = 6, 30, 1
MAX_FAILURES, LOCK_SECONDS = 5, 600
ISSUER, ACCOUNT = 'HomenS.AI', 'HomenS.AI Auto VPN:release-signing'
# 32 symbols, so each one is exactly 5 random bits. No 0/O and no 1/I: they cannot be misread on paper.
RECOVERY_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
RECOVERY_BODY, RECOVERY_CHECK = 16, 4
RECOVERY_COUNT, RECOVERY_LOW = 10, 3
RECOVERY_FILE = 'recovery.codes.dpapi'
SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_LENGTH = 2**15, 8, 1, 32
STORE_CORRUPT = ('RECOVERY-STORE-CORRUPT: the recovery code store is damaged, so no recovery code works now; use the '
                 'authenticator code and run new-recovery-codes')


class TotpError(ValueError):
    pass


def hotp(key, counter, digits=DIGITS, digest=hashlib.sha1):
    mac = hmac.new(key, struct.pack('>Q', counter), digest).digest()
    offset = mac[-1] & 0x0f
    value = struct.unpack('>I', mac[offset:offset+4])[0] & 0x7fffffff
    return str(value % 10**digits).zfill(digits)


def totp(key, now, digits=DIGITS, period=PERIOD, digest=hashlib.sha1):
    return hotp(key, int(now)//period, digits, digest)


def new_seed():
    return base64.b32encode(os.urandom(20)).decode('ascii')


def seed_bytes(seed):
    text = seed.strip().replace(' ', '').upper()
    try:
        key = base64.b32decode(text+'='*(-len(text) % 8))
    except ValueError:
        raise TotpError('TOTP-SEED-FORMAT') from None
    if len(key) < 16:
        raise TotpError('TOTP-SEED-FORMAT')
    return key


def otpauth_uri(seed, account=ACCOUNT, issuer=ISSUER):
    return 'otpauth://totp/%s?secret=%s&issuer=%s&algorithm=SHA1&digits=%d&period=%d' % (
        quote(account, safe=':'), seed.rstrip('='), quote(issuer), DIGITS, PERIOD)


def load_state(path, now=None):
    try:
        with open(path, encoding='utf-8') as stream:
            state = json.load(stream)
        if not isinstance(state, dict):
            raise ValueError
        return {'failures': int(state.get('failures', 0)), 'locked_until': float(state.get('locked_until', 0)),
                'last_step': int(state.get('last_step', -1))}
    except FileNotFoundError:
        return {'failures': 0, 'locked_until': 0.0, 'last_step': -1}
    except (OSError, ValueError, TypeError):
        # A damaged state file must not open the gate: treat it as a fresh lockout.
        return {'failures': 0, 'locked_until': (time.time() if now is None else now)+LOCK_SECONDS, 'last_step': -1}


def save_state(path, state):
    temporary = path+'.tmp'
    with open(temporary, 'w', encoding='utf-8') as stream:
        json.dump(state, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def open_gate(state_path, now):
    """The lockout comes first for every kind of code, so a locked gate never looks at the code."""
    state = load_state(state_path, now)
    if state['locked_until'] > now:
        raise TotpError('TOTP-LOCKED: too many wrong codes; try again in %d s' % (state['locked_until']-now+1))
    return state


def count_failure(state, state_path, now, reason):
    """Record one wrong code and raise: `reason` with the attempts left, or TOTP-LOCKED on the last allowed one."""
    state['failures'] += 1
    left = MAX_FAILURES-state['failures']
    if left <= 0:
        state.update(failures=0, locked_until=now+LOCK_SECONDS)
        save_state(state_path, state)
        raise TotpError('TOTP-LOCKED: %d wrong codes; signing is locked for %d minutes' % (MAX_FAILURES, LOCK_SECONDS//60))
    save_state(state_path, state)
    raise TotpError('%s: %d attempt(s) left before a %d-minute lock' % (reason, left, LOCK_SECONDS//60))


def check_code(seed, code, state_path, now=None):
    """Accept the current 6-digit code or raise TotpError(TOTP-LOCKED / TOTP-CODE-FORMAT / TOTP-WRONG-CODE /
    TOTP-REPLAYED). Updates the state file either way."""
    now = time.time() if now is None else now
    state = open_gate(state_path, now)
    code = (code or '').strip().replace(' ', '')
    if len(code) != DIGITS or not code.isascii() or not code.isdigit():
        raise TotpError('TOTP-CODE-FORMAT: enter the 6 digits shown by the authenticator app')
    key = seed_bytes(seed)
    step = int(now)//PERIOD
    matched = None
    for candidate in range(step-SKEW, step+SKEW+1):
        if hmac.compare_digest(hotp(key, candidate), code):
            matched = candidate
    if matched is not None and matched <= state['last_step']:
        raise TotpError('TOTP-REPLAYED: this code was already used; wait for the next one')
    if matched is None:
        count_failure(state, state_path, now, 'TOTP-WRONG-CODE')
    state.update(failures=0, locked_until=0.0, last_step=matched)
    save_state(state_path, state)
    return matched


# ---- recovery codes ---------------------------------------------------------------------------------------------

def compact_code(code):
    """Upper case without spaces and dashes, including the typographic dashes a PDF or a word processor leaves."""
    return re.sub(r'[\s\-\u2010-\u2015]', '', code or '').upper()


def recovery_check(body):
    number = int.from_bytes(hashlib.sha256(b'HSAI-RC1:'+body.encode('ascii')).digest()[:4], 'big')
    return ''.join(RECOVERY_ALPHABET[(number >> shift) & 31] for shift in range(27, 27-5*RECOVERY_CHECK, -5))


def recovery_format(text):
    return '-'.join(text[index:index+4] for index in range(0, len(text), 4))


def new_recovery_codes():
    found = []
    while len(found) < RECOVERY_COUNT:
        body = ''.join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_BODY))
        code = recovery_format(body+recovery_check(body))
        if code not in found:
            found.append(code)
    return found


def recovery_well_formed(text):
    return (len(text) == RECOVERY_BODY+RECOVERY_CHECK and all(symbol in RECOVERY_ALPHABET for symbol in text)
            and hmac.compare_digest(recovery_check(text[:RECOVERY_BODY]), text[RECOVERY_BODY:]))


def recovery_hash(text, salt):
    return hashlib.scrypt(text.encode('ascii'), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_LENGTH,
                          maxmem=256*SCRYPT_R*SCRYPT_N)


def utc_stamp(now):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))


def recovery_record(codes, now=None):
    """What is stored for a set: salted slow hashes only, the plaintext codes stay in memory and on the owner's screen."""
    entries = []
    for code in codes:
        salt = os.urandom(16)
        entries.append({'salt': base64.b64encode(salt).decode('ascii'), 'used_utc': None,
                        'hash': base64.b64encode(recovery_hash(compact_code(code), salt)).decode('ascii')})
    return {'version': 1, 'kdf': 'scrypt', 'n': SCRYPT_N, 'r': SCRYPT_R, 'p': SCRYPT_P,
            'created_utc': utc_stamp(time.time() if now is None else now), 'codes': entries}


def parse_recovery(data):
    """Strict: anything but a complete set made with the current KDF cost is damaged, and a damaged set has no valid code."""
    try:
        record = json.loads(data.decode('ascii'))
        entries = record['codes']
        kdf = (record['version'], record['kdf'], record['n'], record['r'], record['p'])
        valid = kdf == (1, 'scrypt', SCRYPT_N, SCRYPT_R, SCRYPT_P)
        for entry in entries:
            valid = (valid and set(entry) == {'salt', 'hash', 'used_utc'} and isinstance(entry['used_utc'], (str, type(None)))
                     and len(base64.b64decode(entry['salt'], validate=True)) == 16
                     and len(base64.b64decode(entry['hash'], validate=True)) == SCRYPT_LENGTH)
        valid = valid and len({entry['salt'] for entry in entries}) == RECOVERY_COUNT
    except (ValueError, TypeError, KeyError, AttributeError):
        valid = False
    if not valid:
        raise TotpError(STORE_CORRUPT)
    return record


def unused(record):
    return sum(1 for entry in record['codes'] if entry['used_utc'] is None)


class RecoveryCodes:
    """The stored set. A missing set is None; a set that cannot be read or parsed raises, and never counts as valid."""
    def __init__(self, store):
        self.store = store

    def exists(self):
        return self.store.has(RECOVERY_FILE)

    def load(self):
        if not self.exists():
            return None
        try:
            data = self.store.read_secret(RECOVERY_FILE)
        except (ValueError, OSError):
            raise TotpError(STORE_CORRUPT) from None
        return parse_recovery(data)

    def save(self, record, keep_old=False):
        self.store.replace_secret(RECOVERY_FILE, json.dumps(record, sort_keys=True).encode('ascii'), keep_old=keep_old)

    def remaining(self):
        """(unused codes, the problem text or None). Never raises: this only informs the owner."""
        try:
            record = self.load()
        except TotpError as error:
            return 0, str(error)
        if record is None:
            return 0, 'RECOVERY-CODES-NONE: no recovery codes exist; run new-recovery-codes'
        return unused(record), None


def check_recovery(codes, code, state_path, now=None):
    """Accept an unused recovery code and burn it, or raise. The burn is on disk before this returns, so the action that
    follows cannot run with a code that still works, and a failed burn stops the action. Returns the unused count."""
    now = time.time() if now is None else now
    state = open_gate(state_path, now)
    text = compact_code(code)
    if not recovery_well_formed(text):
        raise TotpError('RECOVERY-CODE-TYPO: this recovery code has a typo (check it against the paper; the letters O and I '
                        'and the digits 0 and 1 are never used). The code was not used up')
    try:
        record = codes.load()
    except TotpError as error:
        count_failure(state, state_path, now, str(error))
    if record is None:
        count_failure(state, state_path, now, 'RECOVERY-CODES-NONE: no recovery codes exist')
    # Every slot is computed, used ones too: the time taken says nothing about which slot matched.
    matched = [entry for entry in record['codes'] if hmac.compare_digest(
        recovery_hash(text, base64.b64decode(entry['salt'])), base64.b64decode(entry['hash']))]
    if not matched:
        count_failure(state, state_path, now, 'RECOVERY-CODE-WRONG')
    if matched[0]['used_utc'] is not None:
        count_failure(state, state_path, now, 'RECOVERY-CODE-USED: this code was already used')
    matched[0]['used_utc'] = utc_stamp(now)
    try:
        codes.save(record)
    except (ValueError, OSError):
        raise TotpError('RECOVERY-BURN-FAILED: the code could not be marked as used, so nothing was done') from None
    state.update(failures=0, locked_until=0.0)
    save_state(state_path, state)
    return unused(record)


def check_factor(seed, code, state_path, codes, now=None):
    """One entry for every prompt: routes by shape to the TOTP gate or the recovery gate. Returns 'totp' or 'recovery'.
    Anything longer than a TOTP code is a recovery code, so a missed character is reported as a typo, not as a 6-digit error."""
    if len(compact_code(code)) > DIGITS:
        check_recovery(codes, code, state_path, now)
        return 'recovery'
    if seed is None:
        raise TotpError('TOTP-NOT-ENROLLED: no authenticator is enrolled, only a recovery code works here')
    check_code(seed, code, state_path, now)
    return 'totp'
