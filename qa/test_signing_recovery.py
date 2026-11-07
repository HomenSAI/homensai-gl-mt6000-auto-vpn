"""One-time recovery codes of the signing second factor: format, burn, replay, typo, lockout, atomic update, regeneration,
corrupt store, no plaintext on disk, and every keytool command that takes a code.

Offline. The DPAPI store is replaced by the reversible test protector of test_signing_core (real DPAPI only on Windows). The
scrypt cost is lowered for speed in most tests; ProductionCostTests runs the real one."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/signing'))
sys.path.insert(0, str(ROOT/'qa'))
import keytool  # noqa: E402
import secret_store  # noqa: E402
import test_signing_core as core  # noqa: E402
import totp  # noqa: E402
import usign_format as u  # noqa: E402

CODE = re.compile(r'[2-9A-HJ-NP-Z]{4}(-[2-9A-HJ-NP-Z]{4}){4}')
NOW = 1_900_000_000
BODY = 'A2B3C4D5E6F7G8H9'  # fixed, so the exhaustive typo sweep is deterministic


class Console(core.Console):
    def __init__(self, codes=(), secrets=(), answers=()):
        super().__init__(codes, secrets)
        self.answers, self.pages, self.prompts = list(answers), [], []

    def code(self, prompt=''):
        self.prompts.append(prompt)
        return super().code(prompt)

    def confirm(self, prompt):
        return self.answers.pop(0) if self.answers else ''

    def show_codes(self, codes, issued):
        self.pages.append(list(codes))

    def shown_codes(self):
        return [line.split()[1] for line in self.lines if re.fullmatch(r'\s*\d+\. \S+', line)]


class Cheap(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(totp, 'SCRYPT_N', 2**4)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = core.fake_store(Path(self.directory.name)/'store')
        self.store.root.mkdir(parents=True)
        self.state = str(self.store.path('totp-state.json'))
        self.codes = totp.RecoveryCodes(self.store)

    def issue(self):
        plain = totp.new_recovery_codes()
        self.codes.save(totp.recovery_record(plain, NOW))
        return plain

    def failures(self):
        return json.loads(Path(self.state).read_text())['failures'] if os.path.exists(self.state) else 0

    def stored(self):
        return self.store.path(totp.RECOVERY_FILE).read_bytes()


class FormatTests(Cheap):
    def test_shape_entropy_and_alphabet(self):
        self.assertEqual(len(totp.RECOVERY_ALPHABET), 32)
        self.assertEqual(len(set(totp.RECOVERY_ALPHABET)), 32)
        self.assertFalse(set('01OI') & set(totp.RECOVERY_ALPHABET))
        self.assertGreaterEqual(totp.RECOVERY_BODY*5, 80)
        plain = totp.new_recovery_codes()
        self.assertEqual(len(set(plain)), 10)
        for code in plain:
            self.assertTrue(CODE.fullmatch(code), code)
            self.assertTrue(totp.recovery_well_formed(totp.compact_code(code)))

    def test_codes_use_the_whole_alphabet_evenly(self):
        seen = {}
        for _ in range(60):
            for code in totp.new_recovery_codes():
                for symbol in totp.compact_code(code)[:totp.RECOVERY_BODY]:
                    seen[symbol] = seen.get(symbol, 0)+1
        self.assertEqual(set(seen), set(totp.RECOVERY_ALPHABET))
        expected = 60*10*16/32
        self.assertLess(max(abs(count-expected)/expected for count in seen.values()), 0.35)

    def test_check_is_pinned(self):
        # Printed codes must stay valid across versions of the tool.
        digest = int.from_bytes(hashlib.sha256(b'HSAI-RC1:'+BODY.encode()).digest()[:4], 'big')
        expected = ''.join(totp.RECOVERY_ALPHABET[(digest >> shift) & 31] for shift in (27, 22, 17, 12))
        self.assertEqual(totp.recovery_check(BODY), expected)

    def test_every_single_typo_and_swap_is_detected(self):
        text = BODY+totp.recovery_check(BODY)
        self.assertTrue(totp.recovery_well_formed(text))
        for position in range(len(text)):
            for symbol in totp.RECOVERY_ALPHABET:
                if symbol != text[position]:
                    self.assertFalse(totp.recovery_well_formed(text[:position]+symbol+text[position+1:]), (position, symbol))
        for position in range(len(text)-1):
            if text[position] != text[position+1]:
                swapped = text[:position]+text[position+1]+text[position]+text[position+2:]
                self.assertFalse(totp.recovery_well_formed(swapped), position)

    def test_input_forms(self):
        text = BODY+totp.recovery_check(BODY)
        for typed in (totp.recovery_format(text), totp.recovery_format(text).lower(), ' '.join(totp.recovery_format(text).split('-')),
                      totp.recovery_format(text).replace('-', '\u2013'), text.lower()+'\n'):
            self.assertTrue(totp.recovery_well_formed(totp.compact_code(typed)), typed)
        for broken in ('', text[:-1], text+'2', '0'*20, 'I'*20, '\u0663'*20):
            self.assertFalse(totp.recovery_well_formed(totp.compact_code(broken)), broken)


class GateTests(Cheap):
    def test_burn_once_and_replay_refused(self):
        plain = self.issue()
        self.assertEqual(totp.check_recovery(self.codes, plain[3], self.state, NOW), 9)
        self.assertEqual(self.codes.remaining(), (9, None))
        record = self.codes.load()
        self.assertEqual([index for index, entry in enumerate(record['codes']) if entry['used_utc']], [3])
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-USED'):
            totp.check_recovery(self.codes, plain[3], self.state, NOW+1)
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-USED'):
            totp.check_recovery(self.codes, plain[3].lower().replace('-', ' '), self.state, NOW+2)
        self.assertEqual(self.codes.remaining(), (9, None))
        self.assertEqual(self.failures(), 2)

    def test_typo_is_detected_burns_nothing_and_is_not_counted(self):
        plain = self.issue()
        before = self.stored()
        replacement = 'B' if plain[0][0] != 'B' else 'C'
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-TYPO'):
            totp.check_recovery(self.codes, replacement+plain[0][1:], self.state, NOW)
        self.assertEqual(self.stored(), before)
        self.assertEqual(self.failures(), 0)
        totp.check_recovery(self.codes, plain[0], self.state, NOW)

    def test_wrong_codes_lock_the_shared_gate_and_a_locked_gate_burns_nothing(self):
        plain = self.issue()
        wrong = totp.new_recovery_codes()
        seed = totp.new_seed()
        bad_totp = '000000' if totp.totp(totp.seed_bytes(seed), NOW) != '000000' else '111111'
        for index in range(2):
            with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-WRONG'):
                totp.check_recovery(self.codes, wrong[index], self.state, NOW)
        with self.assertRaisesRegex(totp.TotpError, 'TOTP-WRONG-CODE'):
            totp.check_code(seed, bad_totp, self.state, NOW)
        self.assertEqual(self.failures(), 3)
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-WRONG: 1 attempt'):
            totp.check_recovery(self.codes, wrong[3], self.state, NOW)
        with self.assertRaisesRegex(totp.TotpError, 'TOTP-LOCKED'):
            totp.check_recovery(self.codes, wrong[4], self.state, NOW)
        before = self.stored()
        with self.assertRaisesRegex(totp.TotpError, 'TOTP-LOCKED'):
            totp.check_recovery(self.codes, plain[0], self.state, NOW+1)
        with self.assertRaisesRegex(totp.TotpError, 'TOTP-LOCKED'):
            totp.check_factor(seed, plain[0], self.state, self.codes, NOW+1)
        self.assertEqual(self.stored(), before)
        self.assertEqual(self.codes.remaining(), (10, None))
        # The lock ends on time and a good code then clears the counter.
        totp.check_recovery(self.codes, plain[0], self.state, NOW+totp.LOCK_SECONDS+1)
        self.assertEqual(self.failures(), 0)

    def test_accepted_code_clears_the_wrong_code_counter(self):
        plain = self.issue()
        for code in totp.new_recovery_codes()[:3]:
            with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-WRONG'):
                totp.check_recovery(self.codes, code, self.state, NOW)
        self.assertEqual(self.failures(), 3)
        totp.check_recovery(self.codes, plain[0], self.state, NOW)
        self.assertEqual(self.failures(), 0)

    def test_damaged_state_file_locks_recovery_too(self):
        plain = self.issue()
        Path(self.state).write_text('{broken')
        with self.assertRaisesRegex(totp.TotpError, 'TOTP-LOCKED'):
            totp.check_recovery(self.codes, plain[0], self.state, NOW)
        self.assertEqual(self.codes.remaining(), (10, None))

    def test_failed_burn_stops_and_keeps_the_old_file(self):
        plain = self.issue()
        before = self.stored()
        with mock.patch.object(secret_store.os, 'replace', side_effect=OSError('disk')):
            with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-BURN-FAILED'):
                totp.check_recovery(self.codes, plain[0], self.state, NOW)
        self.assertEqual(self.stored(), before)
        self.assertEqual(sorted(path.name for path in self.store.root.iterdir()), [totp.RECOVERY_FILE])
        original = self.store.protect
        self.store.protect = mock.Mock(side_effect=secret_store.StoreError('STORE-DPAPI-PROTECT-FAILED'))
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-BURN-FAILED'):
            totp.check_recovery(self.codes, plain[0], self.state, NOW)
        self.store.protect = original
        self.assertEqual(self.stored(), before)
        self.assertEqual(totp.check_recovery(self.codes, plain[0], self.state, NOW), 9)

    def test_interrupted_write_leaves_the_complete_old_file(self):
        plain = self.issue()
        before = self.stored()

        def dies(*_):
            self.assertEqual(self.stored(), before)
            raise OSError('power cut before the rename')
        with mock.patch.object(secret_store.os, 'fsync', side_effect=dies):
            with self.assertRaises(OSError):
                self.codes.save(self.codes.load())
        self.assertEqual(self.stored(), before)
        self.assertFalse(list(self.store.root.glob('*.tmp')))
        self.assertEqual(self.codes.remaining(), (10, None))
        self.assertEqual(totp.check_recovery(self.codes, plain[1], self.state, NOW), 9)

    def test_readback_mismatch_is_not_success(self):
        plain = self.issue()
        original = self.store.unprotect
        calls = []

        def lies(blob):
            calls.append(blob)
            return original(blob) if len(calls) == 1 else b'other'
        self.store.unprotect = lies
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-BURN-FAILED'):
            totp.check_recovery(self.codes, plain[0], self.state, NOW)

    def test_two_runs_cannot_spend_one_code(self):
        plain = self.issue()
        self.store.write_secret('totp.seed.dpapi', totp.new_seed().encode('ascii'))
        # Five runs: one spends the code, four replays stay below the lockout that a fifth would trigger.
        results, barrier = [], threading.Barrier(5)

        def spend():
            barrier.wait()
            try:
                keytool.require_totp(self.store, Console(codes=[plain[0]]))
                results.append('ok')
            except keytool.ToolError as error:
                results.append(str(error).split(':')[0])
        threads = [threading.Thread(target=spend) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results.count('ok'), 1, results)
        self.assertEqual(results.count('RECOVERY-CODE-USED'), 4, results)
        self.assertEqual(self.codes.remaining(), (9, None))

    def test_busy_lock_is_a_clear_refusal(self):
        with self.store.exclusive():
            with self.assertRaisesRegex(secret_store.StoreError, 'STORE-BUSY'):
                with self.store.exclusive(wait=0.05):
                    self.fail('entered a held lock')
        with self.store.exclusive(wait=0.05):
            pass

    def test_no_store_means_no_recovery(self):
        code = totp.new_recovery_codes()[0]
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODES-NONE'):
            totp.check_recovery(self.codes, code, self.state, NOW)
        self.assertEqual(self.failures(), 1)
        self.assertEqual(self.codes.remaining()[0], 0)
        self.assertIn('RECOVERY-CODES-NONE', self.codes.remaining()[1])

    def test_routing_by_shape(self):
        plain = self.issue()
        seed = totp.new_seed()
        now = NOW
        self.assertEqual(totp.check_factor(seed, totp.totp(totp.seed_bytes(seed), now), self.state, self.codes, now), 'totp')
        self.assertEqual(totp.check_factor(seed, plain[0], self.state, self.codes, now), 'recovery')
        self.assertEqual(totp.check_factor(None, plain[1], self.state, self.codes, now), 'recovery')
        with self.assertRaisesRegex(totp.TotpError, 'TOTP-NOT-ENROLLED'):
            totp.check_factor(None, '123456', self.state, self.codes, now)
        for junk in ('', 'abc', '12345', '\u0663'*6):
            with self.assertRaisesRegex(totp.TotpError, 'TOTP-CODE-FORMAT'):
                totp.check_factor(seed, junk, self.state, self.codes, now)
        # A code with a missed character, or a pasted key line, must not be answered with "enter 6 digits".
        for junk in (plain[2][:-1], 'HSAI-SK1:MAIN:', '1234567'):
            with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-TYPO'):
                totp.check_factor(seed, junk, self.state, self.codes, now)
        self.assertEqual(self.codes.remaining(), (8, None))

    def test_every_error_keeps_the_typed_code_out_of_the_message(self):
        plain = self.issue()
        wrong = totp.new_recovery_codes()[0]
        for typed in (wrong, plain[0][:-1]+('2' if plain[0][-1] != '2' else '3')):
            with self.assertRaises(totp.TotpError) as caught:
                totp.check_recovery(self.codes, typed, self.state, NOW)
            self.assertNotIn(typed, str(caught.exception))


class CorruptStoreTests(Cheap):
    def variants(self, record):
        weak = json.loads(json.dumps(record))
        weak['n'] = 2
        missing = json.loads(json.dumps(record))
        missing['codes'] = missing['codes'][:9]
        empty = json.loads(json.dumps(record))
        empty['codes'] = []
        shallow = json.loads(json.dumps(record))
        shallow['codes'][0]['hash'] = base64.b64encode(b'x').decode()
        twin = json.loads(json.dumps(record))
        twin['codes'][1] = twin['codes'][0]
        kind = json.loads(json.dumps(record))
        kind['codes'][0]['used_utc'] = 5
        return {'not-json': b'garbage', 'empty-file': b'', 'wrong-root': b'[]', 'weak-kdf': json.dumps(weak).encode(),
                'nine-codes': json.dumps(missing).encode(), 'no-codes': json.dumps(empty).encode(),
                'short-hash': json.dumps(shallow).encode(), 'same-salt': json.dumps(twin).encode(),
                'used-type': json.dumps(kind).encode(), 'not-ascii': '{"codes":"\u044f"}'.encode()}

    def test_every_damage_means_no_codes_and_never_a_bypass(self):
        plain = self.issue()
        record = self.codes.load()
        for name, data in self.variants(record).items():
            with self.subTest(name):
                Path(self.state).unlink(missing_ok=True)
                self.store.path(totp.RECOVERY_FILE).write_bytes(self.store.protect(data))
                before = self.stored()
                with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-STORE-CORRUPT'):
                    totp.check_recovery(self.codes, plain[0], self.state, NOW)
                self.assertEqual(self.stored(), before)
                self.assertEqual(self.failures(), 1)
                self.assertEqual(self.codes.remaining()[0], 0)
                self.assertIn('RECOVERY-STORE-CORRUPT', self.codes.remaining()[1])

    def test_undecryptable_blob_is_corrupt_too(self):
        plain = self.issue()
        self.store.unprotect = mock.Mock(side_effect=secret_store.StoreError('STORE-DPAPI-UNPROTECT-FAILED'))
        with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-STORE-CORRUPT'):
            totp.check_recovery(self.codes, plain[0], self.state, NOW)
        self.assertEqual(self.failures(), 1)

    def test_a_used_code_cannot_be_revived_by_damage(self):
        plain = self.issue()
        totp.check_recovery(self.codes, plain[0], self.state, NOW)
        self.store.path(totp.RECOVERY_FILE).write_bytes(self.stored()[:-8])
        for code in plain[:2]:
            with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-STORE-CORRUPT'):
                totp.check_recovery(self.codes, code, self.state, NOW)


class ProductionCostTests(unittest.TestCase):
    def test_real_cost_is_slow_and_runs(self):
        self.assertGreaterEqual(totp.SCRYPT_N, 2**15)
        self.assertGreaterEqual(totp.SCRYPT_R, 8)
        self.assertGreaterEqual(totp.SCRYPT_P, 1)
        with tempfile.TemporaryDirectory() as directory:
            store = core.fake_store(Path(directory))
            codes = totp.RecoveryCodes(store)
            plain = totp.new_recovery_codes()
            codes.save(totp.recovery_record(plain, NOW))
            record = codes.load()
            self.assertEqual((record['kdf'], record['n'], record['r'], record['p']), ('scrypt', 2**15, 8, 1))
            salts = [entry['salt'] for entry in record['codes']]
            self.assertEqual(len(set(salts)), 10)
            # Recomputed here with the plain library call: the stored value really is that scrypt output, not a fast hash.
            for code, entry in zip(plain, record['codes']):
                expected = hashlib.scrypt(code.replace('-', '').encode(), salt=base64.b64decode(entry['salt']), n=2**15, r=8, p=1,
                                          dklen=32, maxmem=2**26)
                self.assertEqual(base64.b64decode(entry['hash']), expected)
            self.assertEqual(totp.check_recovery(codes, plain[9], str(Path(directory)/'state.json'), NOW), 9)


@unittest.skipUnless(shutil.which('git'), 'git required')
class CommandTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(totp, 'SCRYPT_N', 2**4)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)/'repo'
        (self.root/'releases').mkdir(parents=True)
        (self.root/'router-test-kit').mkdir()
        (self.root/'router-test-kit/02-install.sh').write_text("#!/bin/sh\nTRUSTED_KEYS=''\nREVOKED_KEYS=''\n")
        self.git('init', '-q')
        payload = b'package 1\n'
        name = 'homensai-auto-vpn_1.0.0-alpha1-1_all.ipk'
        (self.root/'releases'/name).write_bytes(payload)
        (self.root/'releases'/(name+'.sha256')).write_text(hashlib.sha256(payload).hexdigest()+'  '+name+'\n')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'record')
        self.store = core.fake_store(Path(self.directory.name)/'store')
        self.now = [NOW]
        clock = mock.patch.object(totp.time, 'time', lambda: self.now[0])
        clock.start()
        self.addCleanup(clock.stop)
        self.assertEqual(self.run_tool(['new-keys'], Console())[0], 0)
        self.plain = self.enrol()

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.name=QA', '-c', 'user.email=qa@example.invalid']+list(args), cwd=self.root,
                              capture_output=True, text=True, check=True, timeout=60).stdout.strip()

    def run_tool(self, argv, console):
        with mock.patch('sys.stderr') as stderr:
            code = keytool.main(argv, root=self.root, store=self.store, console=console)
        return code, ''.join(call.args[0] for call in stderr.write.call_args_list)

    def scanned(self, console):
        return lambda: totp.totp(totp.seed_bytes(console.qrs[-1].split('secret=')[1].split('&')[0]), self.now[0])

    def enrol(self):
        console = Console()
        console.codes = [self.scanned(console)]
        self.assertEqual(self.run_tool(['setup-totp'], console)[0], 0)
        self.last_setup = console
        return console.shown_codes()

    def current(self):
        self.now[0] += 60
        return totp.totp(totp.seed_bytes(self.store.read_secret('totp.seed.dpapi').decode()), self.now[0])

    def left(self):
        return totp.RecoveryCodes(self.store).remaining()

    def test_setup_shows_ten_codes_once_after_the_confirmation(self):
        console = self.last_setup
        self.assertEqual(len(self.plain), 10)
        for code in self.plain:
            self.assertTrue(CODE.fullmatch(code), code)
        self.assertEqual(self.left(), (10, None))
        joined = '\n'.join(console.lines)
        self.assertLess(joined.index('TOTP-ENROLLED'), joined.index(self.plain[0]))
        self.assertEqual(console.pages, [])
        # Nothing can print them again.
        console = Console(codes=[self.current()])
        self.assertEqual(self.run_tool(['show-totp', '--qr', 'none'], console)[0], 0)
        self.assertFalse(set(self.plain) & set(re.findall(CODE.pattern.replace('(-', '(?:-'), '\n'.join(console.lines))))

    def test_failed_confirmation_saves_and_shows_nothing(self):
        store = core.fake_store(Path(self.directory.name)/'store-fresh')
        self.store, kept = store, self.store
        console = Console(codes=['000000', '000000', '000000'])
        with mock.patch.object(totp, 'hotp', return_value='999999'):
            self.assertIn('TOTP-ENROL-FAILED', self.run_tool(['setup-totp'], console)[1])
        self.assertFalse(store.has('totp.seed.dpapi'))
        self.assertFalse(store.has(totp.RECOVERY_FILE))
        self.assertEqual(console.shown_codes(), [])
        self.store = kept

    def test_print_page_is_offered_only_on_request(self):
        store = core.fake_store(Path(self.directory.name)/'store-page')
        self.store = store
        console = Console(answers=['y'])
        console.codes = [self.scanned(console)]
        self.assertEqual(self.run_tool(['setup-totp'], console)[0], 0)
        self.assertEqual(console.pages, [console.shown_codes()])

    def test_every_prompt_takes_a_recovery_code(self):
        console = Console(codes=[self.plain[0]])
        self.assertEqual(self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[0], 0)
        self.assertTrue(keytool.parse_payload(console.qrs[-1]))
        self.assertIn('RECOVERY-CODE-ACCEPTED', '\n'.join(console.lines))
        self.assertIn('Recovery codes left: 9 of 10.', console.lines)
        console = Console(codes=[self.plain[1]])
        self.assertEqual(self.run_tool(['show-totp', '--qr', 'none'], console)[0], 0)
        self.assertEqual(self.left(), (8, None))
        name = 'homensai-auto-vpn_1.0.0-alpha2-1_all.ipk'
        (self.root/'releases'/name).write_bytes(b'package 2\n')
        (self.root/'VERSION.json').write_text('{}')
        console = Console(codes=[self.plain[2]])
        self.assertEqual(self.run_tool(['sign-release', '--artifact', 'releases/'+name, '--no-ots', '--source-commit',
                                        self.git('rev-parse', 'HEAD')], console)[0], 0)
        self.assertEqual(keytool.verify_release(self.root, 'releases/'+name)['result'], 'PASS')
        self.assertEqual(self.left(), (7, None))

    def test_default_prompt_names_both_kinds_of_code(self):
        import inspect
        prompt = inspect.signature(keytool.Console.code).parameters['prompt'].default
        self.assertIn('6-digit', prompt)
        self.assertIn('recovery code', prompt)

    def test_burn_happens_before_the_action(self):
        seen = []
        original = keytool.usign_format.SecretKey.from_file

        def spying(data):
            seen.append(self.left()[0])
            return original(data)
        with mock.patch.object(keytool.usign_format.SecretKey, 'from_file', spying):
            self.assertEqual(self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], Console(codes=[self.plain[0]]))[0], 0)
        self.assertEqual(seen, [9])

    def test_failed_burn_runs_no_action(self):
        console = Console(codes=[self.plain[0]])
        with mock.patch.object(secret_store.os, 'replace', side_effect=OSError('disk')):
            self.assertIn('RECOVERY-BURN-FAILED', self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[1])
        self.assertEqual(console.qrs, [])
        self.assertEqual(self.left(), (10, None))

    def test_replay_and_wrong_code_run_no_action(self):
        self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], Console(codes=[self.plain[0]]))
        console = Console(codes=[self.plain[0]])
        self.assertIn('RECOVERY-CODE-USED', self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[1])
        self.assertEqual(console.qrs, [])
        console = Console(codes=[totp.new_recovery_codes()[0]])
        self.assertIn('RECOVERY-CODE-WRONG', self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[1])
        self.assertEqual(console.qrs, [])

    def test_lockout_through_the_command_line_path(self):
        console_lines = []
        for index in range(5):
            console = Console(codes=[totp.new_recovery_codes()[0]])
            console_lines.append(self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[1])
        self.assertIn('TOTP-LOCKED', console_lines[-1])
        console = Console(codes=[self.plain[0]])
        self.assertIn('TOTP-LOCKED', self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[1])
        self.assertEqual(console.qrs, [])
        self.assertEqual(self.left(), (10, None))

    def test_remaining_and_low_warning(self):
        for index in range(6):
            console = Console(codes=[self.plain[index]])
            self.assertEqual(self.run_tool(['show-totp', '--qr', 'none'], console)[0], 0)
        self.assertIn('Recovery codes left: 4 of 10.', console.lines)
        self.assertFalse(any('RECOVERY-CODES-LOW' in line for line in console.lines))
        console = Console(codes=[self.plain[6]])
        self.run_tool(['show-totp', '--qr', 'none'], console)
        self.assertIn('Recovery codes left: 3 of 10.', console.lines)
        self.assertTrue(any('RECOVERY-CODES-LOW: only 3 left' in line for line in console.lines))
        # The warning also reaches the owner who signs in with the phone.
        console = Console(codes=[self.current()])
        self.run_tool(['show-totp', '--qr', 'none'], console)
        self.assertTrue(any('RECOVERY-CODES-LOW: only 3 left' in line for line in console.lines))
        self.assertFalse(any('RECOVERY-CODE-ACCEPTED' in line for line in console.lines))
        for index in (7, 8, 9):
            console = Console(codes=[self.plain[index]])
            self.assertEqual(self.run_tool(['show-totp', '--qr', 'none'], console)[0], 0)
        self.assertTrue(any('RECOVERY-CODES-LOW: only 0 left' in line for line in console.lines))
        self.assertIn('RECOVERY-CODE-USED', self.run_tool(['show-totp', '--qr', 'none'], Console(codes=[self.plain[9]]))[1])

    def test_regeneration_needs_a_code_and_invalidates_the_old_set(self):
        before = self.store.path(totp.RECOVERY_FILE).read_bytes()
        wrong = '000000' if self.current() != '000000' else '111111'
        self.assertIn('TOTP-WRONG-CODE', self.run_tool(['new-recovery-codes'], Console(codes=[wrong]))[1])
        self.assertEqual(self.store.path(totp.RECOVERY_FILE).read_bytes(), before)
        console = Console(codes=[self.current()])
        self.assertEqual(self.run_tool(['new-recovery-codes'], console)[0], 0)
        fresh = console.shown_codes()
        self.assertEqual(len(fresh), 10)
        self.assertFalse(set(fresh) & set(self.plain))
        self.assertEqual(self.left(), (10, None))
        self.assertTrue(list(self.store.root.glob('recovery.retired-*.codes.dpapi')))
        console = Console(codes=[self.plain[0]])
        self.assertIn('RECOVERY-CODE-WRONG', self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[1])
        self.assertEqual(console.qrs, [])
        self.assertEqual(self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], Console(codes=[fresh[0]]))[0], 0)
        # A recovery code may authorise the next set: it is burned first, then its whole set is replaced.
        console = Console(codes=[fresh[1]])
        self.assertEqual(self.run_tool(['new-recovery-codes'], console)[0], 0)
        self.assertEqual(self.left(), (10, None))
        self.assertIn('RECOVERY-CODE-WRONG', self.run_tool(['show-totp', '--qr', 'none'], Console(codes=[fresh[2]]))[1])
        self.assertEqual(len(list(self.store.root.glob('recovery.retired-*.codes.dpapi'))), 2)

    def test_regeneration_keeps_the_old_set_until_the_new_one_is_stored(self):
        console = Console(codes=[self.current()])
        real = os.replace

        def refuses_the_set(source, target):
            if str(target).endswith(totp.RECOVERY_FILE):
                raise OSError('disk')
            return real(source, target)
        with mock.patch.object(secret_store.os, 'replace', refuses_the_set):
            with self.assertRaisesRegex(keytool.ToolError, 'RECOVERY-SAVE-FAILED'):
                keytool.cmd_new_recovery_codes(None, self.root, self.store, console)
        self.assertEqual(console.shown_codes(), [])
        self.assertEqual(self.left(), (10, None))
        self.assertEqual(self.run_tool(['show-totp', '--qr', 'none'], Console(codes=[self.plain[0]]))[0], 0)

    def test_reset_with_a_recovery_code_needs_no_key_secret(self):
        old_seed = self.store.read_secret('totp.seed.dpapi')
        old_code = self.current()
        console = Console()
        console.codes = [self.plain[0], self.scanned(console)]
        self.assertEqual(self.run_tool(['reset-totp', '--qr', 'none'], console)[0], 0, console.lines)
        self.assertEqual(console.secrets, [])
        new_seed = self.store.read_secret('totp.seed.dpapi')
        self.assertNotEqual(old_seed, new_seed)
        self.assertTrue(list(self.store.root.glob('totp.retired-*.seed.dpapi')))
        self.assertEqual(self.left(), (9, None))
        self.assertEqual(console.shown_codes(), [])
        self.assertEqual(self.run_tool(['show-totp', '--qr', 'none'], Console(codes=[self.plain[1]]))[0], 0)
        self.assertEqual(self.run_tool(['show-totp', '--qr', 'none'], Console(codes=[self.current()]))[0], 0)
        wrong_old = old_code if old_code != self.current() else '000000'
        self.assertIn('TOTP-WRONG-CODE', self.run_tool(['show-totp', '--qr', 'none'], Console(codes=[wrong_old]))[1])

    def test_reset_with_key_proof_still_works(self):
        reveal = Console(codes=[self.current()])
        self.run_tool(['reveal', '--key', 'reserve', '--qr', 'none'], reveal)
        console = Console(secrets=[reveal.qrs[-1]])
        console.codes = [self.scanned(console)]
        self.assertEqual(self.run_tool(['reset-totp', '--prove-key', 'reserve', '--qr', 'none'], console)[0], 0, console.lines)
        self.assertEqual(self.left(), (10, None))

    def test_reset_without_any_proof_is_refused(self):
        seed = self.store.read_secret('totp.seed.dpapi')
        wrong = '000000' if self.current() != '000000' else '111111'
        for typed in (wrong, totp.new_recovery_codes()[0], ''):
            console = Console(codes=[typed])
            self.assertEqual(self.run_tool(['reset-totp', '--qr', 'none'], console)[0], 2)
            self.assertEqual(console.qrs, [])
        self.assertEqual(self.store.read_secret('totp.seed.dpapi'), seed)

    def test_failed_reset_confirmation_changes_nothing_but_the_burned_code(self):
        seed = self.store.read_secret('totp.seed.dpapi')
        state = self.store.path('totp-state.json').read_bytes()
        console = Console()
        console.codes = [self.plain[0], 'bad', 'bad', 'bad']
        code, error = self.run_tool(['reset-totp', '--qr', 'none'], console)
        self.assertIn('TOTP-ENROL-FAILED', error)
        self.assertEqual(self.store.read_secret('totp.seed.dpapi'), seed)
        self.assertEqual(self.store.path('totp-state.json').read_bytes().replace(b' ', b''), state.replace(b' ', b''))
        self.assertFalse(self.store.path('totp-state.json.enrol').exists())
        self.assertEqual(self.left(), (9, None))

    def test_second_confirmation_attempt_saves_a_burned_code(self):
        console = Console()
        console.codes = [self.plain[0], 'bad', self.scanned(console)]
        self.assertEqual(self.run_tool(['reset-totp', '--qr', 'none'], console)[0], 0)

    def test_reset_issues_a_set_when_none_is_left(self):
        self.store.path(totp.RECOVERY_FILE).write_bytes(self.store.protect(b'broken'))
        console = Console()
        console.codes = [self.current(), self.scanned(console)]
        self.assertEqual(self.run_tool(['reset-totp', '--qr', 'none'], console)[0], 0, console.lines)
        self.assertEqual(len(console.shown_codes()), 10)
        self.assertEqual(self.left(), (10, None))
        self.assertTrue(list(self.store.root.glob('recovery.retired-*.codes.dpapi')))

    def test_lost_seed_recovers_only_with_a_recovery_code(self):
        self.store.retire('totp.seed.dpapi')
        self.assertIn('TOTP-RECOVERY-EXISTS', self.run_tool(['setup-totp'], Console())[1])
        self.assertIn('TOTP-NOT-ENROLLED', self.run_tool(['reveal', '--key', 'main'], Console(codes=[self.plain[0]]))[1])
        self.assertEqual(self.left(), (10, None))
        self.assertIn('TOTP-NOT-ENROLLED', self.run_tool(['reset-totp', '--qr', 'none'], Console(codes=['123456']))[1])
        console = Console()
        console.codes = [self.plain[0], self.scanned(console)]
        self.assertEqual(self.run_tool(['reset-totp', '--qr', 'none'], console)[0], 0, console.lines)
        self.assertTrue(self.store.has('totp.seed.dpapi'))
        self.assertEqual(self.left(), (9, None))

    def test_corrupt_store_never_bypasses_and_the_phone_still_works(self):
        self.store.path(totp.RECOVERY_FILE).write_bytes(b'junk')
        console = Console(codes=[self.plain[0]])
        code, error = self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)
        self.assertEqual(code, 2)
        self.assertIn('RECOVERY-STORE-CORRUPT', error)
        self.assertEqual(console.qrs, [])
        console = Console(codes=[self.current()])
        self.assertEqual(self.run_tool(['reveal', '--key', 'main', '--qr', 'none'], console)[0], 0)
        self.assertTrue(any('WARNING RECOVERY-STORE-CORRUPT' in line for line in console.lines))
        console = Console(codes=[self.current()])
        self.assertEqual(self.run_tool(['new-recovery-codes'], console)[0], 0)
        self.assertEqual(self.left(), (10, None))
        retired = list(self.store.root.glob('recovery.retired-*.codes.dpapi'))
        self.assertEqual([path.read_bytes() for path in retired], [b'junk'])

    def test_emergency_retires_the_codes_with_the_seed(self):
        self.assertEqual(self.run_tool(['new-keys', '--emergency', '--skip-totp'], Console())[0], 0)
        self.assertFalse(self.store.has(totp.RECOVERY_FILE))
        self.assertTrue(list(self.store.root.glob('recovery.retired-*.codes.dpapi')))
        self.assertIn('TOTP-NOT-ENROLLED', self.run_tool(['reveal', '--key', 'main'], Console(codes=[self.plain[0]]))[1])
        self.assertEqual(len(self.enrol()), 10)

    def test_no_plaintext_on_disk(self):
        self.run_tool(['show-totp', '--qr', 'none'], Console(codes=[self.plain[0]]))
        record = json.loads(self.store.read_secret(totp.RECOVERY_FILE))
        self.assertEqual(set(record['codes'][0]), {'salt', 'hash', 'used_utc'})
        needles = []
        for code in self.plain:
            compact = code.replace('-', '')
            needles += [code, compact, compact[:16], base64.b64encode(compact.encode()).decode(), hashlib.sha256(compact.encode()).hexdigest()]
        self.assertTrue(self.store.path(totp.RECOVERY_FILE).read_bytes().startswith(b'T'))
        for folder in (self.store.root, self.root):
            for path in folder.rglob('*'):
                if path.is_file() and '.git' not in path.parts:
                    raw = path.read_bytes()
                    views = [raw, raw[::-1]]
                    if path.suffix == '.dpapi':
                        views.append(self.store.unprotect(raw))
                    for view in views:
                        for needle in needles:
                            self.assertNotIn(needle.encode(), view, path.name)

    def test_no_option_takes_a_recovery_code_on_the_command_line(self):
        for action in keytool.parser()._actions:
            self.assertNotIn('recovery', ' '.join(action.option_strings))


class PrintPageTests(unittest.TestCase):
    def run_page(self, finish):
        captured = {}

        def opened(path):
            captured['path'] = path
            captured['text'] = Path(path).read_text(encoding='utf-8')
        plain = totp.new_recovery_codes()
        with mock.patch.object(keytool.os, 'startfile', opened, create=True), mock.patch('builtins.input', finish):
            console = keytool.Console()
            try:
                console.show_codes(plain, '2026-11-04T00:00:00Z')
            except KeyboardInterrupt:
                captured['interrupted'] = True
        return plain, captured

    def test_page_is_printable_self_contained_and_wiped(self):
        plain, captured = self.run_page(lambda prompt: '')
        for code in plain:
            self.assertIn(code, captured['text'])
        self.assertIn('@media print', captured['text'])
        self.assertNotRegex(captured['text'], r'(?i)(src|href)=|https?:|<script')
        self.assertFalse(os.path.exists(captured['path']))

    def test_page_is_wiped_when_the_owner_interrupts(self):
        def stop(prompt):
            raise KeyboardInterrupt
        _, captured = self.run_page(stop)
        self.assertTrue(captured['interrupted'])
        self.assertFalse(os.path.exists(captured['path']))

    def test_wipe_overwrites_before_deleting(self):
        handle, name = tempfile.mkstemp()
        os.write(handle, b'SECRET')
        os.close(handle)
        seen = []
        with mock.patch.object(secret_store.os, 'fsync', lambda _: seen.append(Path(name).read_bytes())):
            secret_store.wipe(name)
        self.assertEqual(seen, [b'\0'*6])
        self.assertFalse(os.path.exists(name))

    def test_end_of_input_does_not_lose_the_stored_set(self):
        class Closed(Console):
            def confirm(self, prompt):
                raise EOFError
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(totp, 'SCRYPT_N', 2**4):
            store = core.fake_store(Path(directory))
            console = Closed()
            keytool.issue_recovery_codes(store, console)
            self.assertEqual(totp.RecoveryCodes(store).remaining(), (10, None))
            self.assertEqual(len(console.shown_codes()), 10)


class SameSecondRetireTests(unittest.TestCase):
    def test_retired_files_never_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(secret_store.time, 'gmtime', lambda: secret_store.time.struct_time((2026, 11, 4, 0, 0, 0, 0, 0, 0))):
            store = core.fake_store(Path(directory))
            for index in range(3):
                store.write_secret('a.b.dpapi', b'%d' % index, replace=True)
            self.assertEqual(len(list(Path(directory).glob('a.retired-*.b.dpapi'))), 2)
            self.assertTrue(all(path.name.endswith('.dpapi') for path in Path(directory).iterdir()))


@unittest.skipUnless(sys.platform == 'win32', 'DPAPI exists only on Windows')
class RealDpapiTests(unittest.TestCase):
    def test_codes_work_through_the_real_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = secret_store.Store(Path(directory))
            codes = totp.RecoveryCodes(store)
            plain = totp.new_recovery_codes()
            codes.save(totp.recovery_record(plain, NOW))
            blob = store.path(totp.RECOVERY_FILE).read_bytes()
            self.assertNotIn(b'scrypt', blob)
            self.assertEqual(totp.check_recovery(codes, plain[0], str(Path(directory)/'state.json'), NOW), 9)
            with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-CODE-USED'):
                totp.check_recovery(codes, plain[0], str(Path(directory)/'state.json'), NOW)
            store.path(totp.RECOVERY_FILE).write_bytes(blob[:-1]+bytes([blob[-1] ^ 1]))
            self.assertEqual(codes.remaining()[0], 0)
            with self.assertRaisesRegex(totp.TotpError, 'RECOVERY-STORE-CORRUPT'):
                totp.check_recovery(codes, plain[1], str(Path(directory)/'state.json'), NOW)


if __name__ == '__main__':
    unittest.main()
