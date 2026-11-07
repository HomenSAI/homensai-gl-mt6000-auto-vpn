"""The signing drills: every scenario of docs/architecture/SIGNING-LAB-2026-11-04.ru.md as a script over the real tools.

A drill calls keytool.main() / agetool.main() with --lab, exactly the command line the owner would type. Nothing is
reimplemented here: the only thing replaced is the console (the prompts). Passing a drill therefore proves the real code path.

Two kinds of answers reach a prompt:
  manual  the web page asks the owner (phone, paper, pasted line)
  auto    the lab computes the answer from the LAB seed. LabConsole accepts only a lab store, so this path cannot exist for the
          real keys. The headless run also uses a virtual clock, otherwise every code would wait for the next 30-second step.

Secrets: tool output passes mask() before it is kept anywhere. Secret values go to the page as one-shot events and stay in the
memory of this process only (Memory); reports, logs and drills.json hold masked text.
"""
import collections
import contextlib
import copy
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent/'backupcrypt'))
import agetool  # noqa: E402
import chain  # noqa: E402
import keytool  # noqa: E402
import lab_mode  # noqa: E402
import lab_router  # noqa: E402
import ots  # noqa: E402
import qr  # noqa: E402
import report_manifest  # noqa: E402
import secret_store  # noqa: E402
import totp  # noqa: E402
import usign_format  # noqa: E402

PASS, FAIL, SKIP, BLOCKED, CANCELLED = 'PASS', 'FAIL', 'SKIP', 'BLOCKED', 'CANCELLED'
MASKED = '•••'
RECOVERY_RE = r'[2-9A-HJ-NP-Z]{4}(?:-[2-9A-HJ-NP-Z]{4}){4}'
PATTERNS = [(re.compile(r'AGE-SECRET-KEY-1[0-9A-Za-z]+'), 'AGE-SECRET-KEY-1'+MASKED),
            (re.compile(r'otpauth://\S+'), 'otpauth://'+MASKED),
            (re.compile(r'\b%s\b' % RECOVERY_RE), 'XXXX-XXXX-XXXX-XXXX-'+MASKED),
            (re.compile(r'(Manual entry key: ).*'), r'\1'+MASKED),
            (re.compile(r'\b[A-Z2-7]{32,}\b'), MASKED)]
TITLES = (('a', 'Создать тестовые ключи main и reserve', 'Create the test main and reserve keys'),
          ('b', 'Привязать Google Authenticator', 'Enrol Google Authenticator'),
          ('c', '10 кодов восстановления и печать', 'The 10 recovery codes and the print view'),
          ('d', 'Показать тестовый секрет', 'Reveal a test secret'),
          ('e', 'Новый ПК: импорт секрета', 'New PC: import a secret'),
          ('f', 'Подписать тестовый пакет', 'Sign the fake package'),
          ('g', 'Учение: потерян телефон', 'Drill: phone lost'),
          ('h', 'Учение: коды кончились или утекли', 'Drill: codes used up or leaked'),
          ('i', 'Учение: потерян основной ключ', 'Drill: main key lost'),
          ('j', 'Учение: украден основной ключ', 'Drill: main key stolen'),
          ('k', 'Учение: потеряно всё', 'Drill: everything lost'),
          ('l', 'Откат и форк цепочки', 'Rollback and a forked chain'),
          ('m', 'OpenTimestamps: отметка тестового хеша', 'OpenTimestamps stamp of a test hash'),
          ('n', 'age: личность и тестовый архив', 'age: identity and a fake archive'),
          ('o', 'Учение: подмена отчёта', 'Drill: a test report is swapped'))

# Fake test evidence of the drill: the same kinds of files as a real release (docs/architecture/SIGNING-2026-11-03.ru.md, section 12).
FAKE_EVIDENCE = {
    'docs/TEST-HISTORY.html': b'<!doctype html><title>TEST LAB history</title><p>all tests passed (fake)</p>\n',
    'docs/test-history/results.json': b'{"lab": true, "passed": 100, "failed": 0}\n',
    'qa/FAKE-LOCAL-CI.json': b'{"lab": true, "ci": "pass", "tests": 100}\n',
    'private/soak-24h/report-fake/summary.ru.md': b'# FAKE soak: 24 h, 0 failures\n',
    'private/soak-24h/report-fake/cycles.json': b'{"lab": true, "cycles": 1440, "failures": 0}\n',
    'QUEUE-REPORT.md': b'# FAKE queue report: no growth\n',
    'tools/formal/REPORT.ru.md': b'# FAKE TLC: 0 violations\n'}


class DrillFailed(Exception):
    pass


class DrillSkipped(Exception):
    pass


class DrillBlocked(Exception):
    pass


class DrillCancelled(Exception):
    pass


def mask(text, known=()):
    """What may be kept: a line with a secret key line is replaced whole, because the tools print it in spaced groups."""
    text = str(text)
    squeezed = re.sub(r'\s+', '', text)
    if 'HSAI-SK1' in squeezed:
        return 'HSAI-SK1'+MASKED
    for value in known:
        if value and value in text:
            text = text.replace(value, MASKED)
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class VirtualClock:
    """Headless runs only: each generated code moves 31 s on, so the replay rule holds without real waiting."""
    def __init__(self):
        self.value = time.time()

    def now(self):
        return self.value

    def tick(self):
        self.value += 31
        return self.value


class Memory:
    """Held in this process only and gone when it ends: what the auto answers need."""
    def __init__(self):
        self.codes, self.payloads, self.age = [], {}, None

    def known(self):
        return list(self.codes)+list(self.payloads.values())+([self.age] if self.age else [])


class World:
    """One lab tree with its store: the main lab or a throwaway copy for a destructive drill."""
    def __init__(self, lab):
        self.lab = lab
        self.root = lab.repo
        self.store = lab.store()

    def chain_data(self):
        return keytool.read_chain(self.root)

    def entries(self):
        return keytool.verified_chain(self.root)[0]

    def key_id(self, name):
        return self.store.public_index()[name]['key_id']

    def kit(self):
        return self.root/keytool.KIT

    def seed(self):
        return self.store.read_secret('totp.seed.dpapi').decode('ascii') if self.store.has('totp.seed.dpapi') else None

    def has_keys(self):
        return bool(keytool.trusted_keys(self.root)) and self.store.key_path('main').exists()


class Session:
    """The lab of one process run."""
    def __init__(self, lab, clock=None, stamper=None, sandbox=None, network=True):
        self.lab = lab
        self.memory = Memory()
        self.clock = clock
        self.stamper = stamper
        self.sandbox = sandbox
        self.network = network

    def router(self, say=lambda text: None):
        if self.sandbox is None:
            self.sandbox = lab_router.Sandbox.detect(say)
        return self.sandbox


class Answer:
    """One expected prompt. `always` answers without asking even in manual mode (a deliberately wrong code, a pasted bad line)."""
    def __init__(self, ru, en, auto, kind='code', always=False, recovery=False, retry=False):
        self.ru, self.en, self.auto, self.kind, self.always, self.recovery, self.retry = ru, en, auto, kind, always, recovery, retry


class LabConsole(keytool.Console):
    """The console of every tool call in a drill. Refuses anything but a lab store, so the auto path cannot reach real keys."""
    def __init__(self, run):
        super().__init__()
        if not run.world.store.lab:
            raise lab_mode.LabRefused('LAB-CONSOLE-REAL-STORE')
        self.run = run

    def code(self, prompt=''):
        return self.run.answer('code', prompt)

    def secret(self, prompt):
        return self.run.answer('secret', prompt)

    def confirm(self, prompt):
        if 'print-friendly' in prompt:
            return 'n'   # the page has its own print view; no temporary file is needed
        self.run.acknowledge(prompt)
        return ''

    def now(self):
        return self.run.session.clock.now() if self.run.session.clock else None

    def say(self, text=''):
        self.run.tool_line(text)

    def show_qr(self, text, mode, title):
        self.run.tool_qr(text, title)


class Run:
    """One execution of one drill. `emit(event)` feeds the page; `ask(kind, ru, en, prompt)` blocks on the owner (manual mode)."""
    def __init__(self, session, drill, emit=None, ask=None, auto=True):
        self.session, self.drill, self.emit, self.ask, self.auto = session, drill, emit or (lambda event: None), ask, auto
        self.world = World(session.lab)
        self.memory = session.memory
        self.steps, self.notes = [], []
        self.queue = collections.deque()
        self.output, self.enrolled_seed, self.last_recovery = [], None, None
        self.force_auto = False
        self.again = None

    # ---- logging ------------------------------------------------------------------------------------------------------
    def known(self):
        return self.memory.known()

    def step(self, ru, en=None, ok=True):
        row = {'ok': ok, 'ru': ru, 'en': en or ru, 'output': []}
        self.steps.append(row)
        self.emit({'type': 'step', 'ok': ok, 'ru': ru, 'en': en or ru})
        return row

    def note(self, ru, en=None):
        self.notes.append({'ru': ru, 'en': en or ru})
        self.emit({'type': 'note', 'ru': ru, 'en': en or ru})

    def fail(self, ru, en=None):
        self.step(ru, en, ok=False)
        raise DrillFailed(ru)

    def check(self, condition, ru, en=None):
        if not condition:
            self.fail('Не выполнено: '+ru, 'Not met: '+(en or ru))
        self.step(ru, en)

    def show(self, event):
        """A secret for the owner's eyes. Secrets of a throwaway copy are nobody's: they stay in this process."""
        if not self.force_auto:
            self.emit(event)

    def tool_line(self, text):
        text = str(text)
        squeezed = re.sub(r'\s+', '', text)
        line = re.fullmatch(r' *\d+\. (%s)' % RECOVERY_RE, text)
        if 'HSAI-SK1' in squeezed:
            match = re.search(r'(?:HSAI-SK1|%s):(MAIN|RESERVE):' % lab_mode.PAYLOAD_TAG, squeezed)
            self.memory.payloads[match.group(1).lower()] = squeezed
            self.show({'type': 'secret', 'kind': 'line', 'label': match.group(1).lower(), 'text': squeezed})
        elif line:
            self.fresh_codes.append(line.group(1))
            if len(self.fresh_codes) == totp.RECOVERY_COUNT:
                self.memory.codes = list(self.fresh_codes)
                self.show({'type': 'secret', 'kind': 'codes', 'codes': list(self.fresh_codes)})
        elif text.startswith('Manual entry key: '):
            self.show({'type': 'secret', 'kind': 'manual', 'text': text.split(': ', 1)[1]})
        elif text.startswith('AGE-SECRET-KEY-1'):
            self.memory.age = text.strip()
            self.show({'type': 'secret', 'kind': 'line', 'label': 'age', 'text': text.strip()})
        masked = mask(text, self.known())
        self.output.append(masked)
        if self.steps:
            self.steps[-1]['output'].append(masked)
        self.emit({'type': 'tool', 'text': masked})

    def tool_qr(self, text, title):
        if text.startswith('otpauth://'):
            self.enrolled_seed = re.search(r'secret=([A-Z2-7]+)', text).group(1)
            self.show({'type': 'secret', 'kind': 'qr', 'label': 'totp', 'title': title, 'svg': qr.render_svg(qr.encode(text, ecc='Q'), scale=5)})
            return
        self.show({'type': 'secret', 'kind': 'qr', 'label': title, 'title': title, 'svg': qr.render_svg(qr.encode(text, ecc='Q'), scale=5)})

    # ---- answers ------------------------------------------------------------------------------------------------------
    def totp_code(self, seed=None):
        seed = seed or self.world.seed()
        clock = self.session.clock
        if clock:
            return totp.totp(totp.seed_bytes(seed), clock.tick())
        state = str(self.world.store.path('totp-state.json'))
        while int(time.time())//totp.PERIOD <= totp.load_state(state)['last_step']:
            self.emit({'type': 'tool', 'text': 'waiting for a fresh 30-second TOTP step...'})
            time.sleep(2)
        return totp.totp(totp.seed_bytes(seed), time.time())

    def wrong_code(self):
        """A 6-digit code that matches no step in the accepted window of the current seed."""
        seed, now = self.world.seed(), self.session.clock.now() if self.session.clock else time.time()
        good = {totp.hotp(totp.seed_bytes(seed), int(now)//totp.PERIOD+delta) for delta in range(-2, 3)}
        return next(code for code in ('000000', '111111', '222222', '333333', '444444', '555555') if code not in good)

    def phone(self):
        return Answer('Введите 6 цифр с телефона (запись HomenS.AI TEST LAB). Один код работает один раз: при повторе дождитесь нового',
                      'Enter the 6 digits from the phone (entry HomenS.AI TEST LAB). A code works once: wait for a new one if it repeats', self.totp_code)

    def new_phone(self):
        return Answer('Отсканируйте QR и введите 6 цифр с новой записи на телефоне', 'Scan the QR and enter the 6 digits of the new phone entry',
                      lambda: self.totp_code(self.enrolled_seed), retry=True)

    def paper(self):
        def auto():
            if not self.memory.codes:
                self.fail('В памяти нет кодов восстановления', 'No recovery codes in memory')
            return self.memory.codes.pop(0)
        return Answer('Введите один код восстановления с листа', 'Enter one recovery code from the sheet', auto, recovery=True)

    def fixed(self, value):
        return Answer('', '', lambda: value, always=True)

    def pasted(self, name):
        return Answer('', '', lambda: self.memory.payloads[name], kind='secret', always=True)

    def answer(self, kind, prompt):
        if not self.queue and self.again is not None:
            self.queue.append(self.again)   # the tool gives a mistyped enrolment code more attempts, and so does the owner
        if not self.queue:
            self.fail('Инструмент задал неожиданный вопрос: %s' % mask(prompt), 'The tool asked an unexpected question: %s' % mask(prompt))
        plan = self.queue.popleft()
        self.again = plan if plan.retry else None
        automatic = plan.always or self.auto or self.force_auto
        value = plan.auto() if automatic else self.ask(kind, plan.ru, plan.en, mask(prompt))
        if plan.recovery:
            self.last_recovery = value
        self.emit({'type': 'tool', 'text': '(%s: %s)' % ('answered automatically' if automatic else 'answered by the owner', MASKED)})
        return value

    def acknowledge(self, prompt):
        if self.auto or self.force_auto:
            return
        self.ask('ack', 'Сохраните показанное выше (лист или менеджер паролей) и подтвердите', 'Store what is shown above, then confirm', mask(prompt))

    def confirm_danger(self, ru, en):
        if self.auto or self.force_auto:
            return
        if self.ask('confirm', ru, en, '').strip().lower() != 'yes':
            raise DrillCancelled(ru)

    # ---- tools --------------------------------------------------------------------------------------------------------
    def tool(self, module, *argv, answers=()):
        """One real tool command line. Returns (exit code, output, the STOP line or '')."""
        self.queue = collections.deque(answers)
        self.output, self.fresh_codes, self.again = [], [], None
        console = LabConsole(self)
        captured = io.StringIO()
        arguments = [str(item) for item in argv]+['--lab', str(self.world.lab.root)]
        row = self.step('$ %s %s' % (module.__name__+'.py', ' '.join(self.printable(item) for item in argv)))
        try:
            with contextlib.redirect_stderr(captured):
                if module is keytool:
                    code = keytool.main(arguments, store=self.world.store, console=console)
                elif module is report_manifest:
                    code = report_manifest.main(arguments, store=self.world.store, console=console)
                else:
                    code = agetool.main(arguments, store=self.world.store, console=console)
        finally:
            self.queue.clear()
        stop = mask(captured.getvalue().strip(), self.known())
        if stop:
            row['output'].append(stop)
            self.emit({'type': 'tool', 'text': stop})
        return code, list(self.output), stop

    def printable(self, item):
        text = str(item)
        return Path(text).name if ('/' in text or '\\' in text) else text

    def ok(self, *argv, answers=(), module=keytool):
        code, output, stop = self.tool(module, *argv, answers=answers)
        if code:
            self.fail('Команда должна была пройти: %s' % stop, 'The command had to succeed: %s' % stop)
        return output

    def refused(self, expected, *argv, answers=(), module=keytool):
        code, output, stop = self.tool(module, *argv, answers=answers)
        if code == 0 or expected not in stop:
            self.fail('Ожидался отказ %s, получено: %s' % (expected, stop or 'успех'), 'Expected refusal %s, got: %s' % (expected, stop or 'success'))
        self.step('Отказ %s, как и должно быть' % expected, 'Refused with %s, as it must be' % expected)
        return stop

    def router_says(self, result, expected_code, expected_text=None, installed=None):
        for line in result.text.splitlines()[-6:]:
            self.emit({'type': 'tool', 'text': mask(line, self.known())})
            if self.steps:
                self.steps[-1]['output'].append(mask(line, self.known()))
        if result.code != expected_code or (expected_text and expected_text not in result.text) or (installed is not None and result.installed != installed):
            self.fail('Роутер: ожидался код %s %s, получено %s: %s' % (expected_code, expected_text or '', result.code, mask(result.text[-300:])),
                      'Router: expected exit %s %s, got %s: %s' % (expected_code, expected_text or '', result.code, mask(result.text[-300:])))
        self.step('Роутер: код %s %s' % (expected_code, expected_text or ''), 'Router: exit %s %s' % (expected_code, expected_text or ''))

    def sandbox(self):
        box = self.session.router(lambda text: self.emit({'type': 'tool', 'text': text}))
        if box.kind is None:
            raise DrillSkipped(box.label)
        self.step('Симулятор роутера: %s' % box.label, 'Router simulator: %s' % box.label)
        return box

    def router(self, label):
        folder = self.session.lab.work/('router-%s-%s' % (label, time.time_ns()))
        folder.mkdir(parents=True)
        self.routers.append(folder)
        return lab_router.SimRouter(self.sandbox(), folder)

    routers = None

    @contextlib.contextmanager
    def fork(self, label):
        """A destructive drill works on a copy of the lab, so the drills stay independent of each other and of the order. The owner's
        phone has no part in a copy: its codes are automatic, on a virtual clock that ends with the copy."""
        target = self.session.lab.work/('fork-%s-%s' % (label, time.time_ns()))
        target.mkdir(parents=True)
        shutil.copytree(self.world.lab.store_dir, target/'store')
        shutil.copytree(self.world.lab.repo, target/'repo')
        (target/lab_mode.MARKER).write_text('{"lab": true, "fork": true}\n', encoding='ascii')
        saved_world, saved_memory, saved_clock = self.world, self.memory, self.session.clock
        self.world, self.memory = World(lab_mode.LabDir(target)), copy.deepcopy(self.memory)
        self.session.clock = saved_clock or VirtualClock()
        self.force_auto = True
        self.step('Работаю на временной копии лаборатории, коды подставляются автоматически', 'Working on a throwaway copy of the lab, codes are automatic')
        try:
            yield self.world
        finally:
            self.world, self.memory, self.session.clock = saved_world, saved_memory, saved_clock
            self.force_auto = False
            lab_mode.remove_tree(target)

    # ---- prerequisites ------------------------------------------------------------------------------------------------
    def need_keys(self):
        if self.world.has_keys():
            return
        if not (self.auto or self.force_auto):
            raise DrillBlocked('Сначала выполните шаг a (тестовые ключи)')
        self.ok('new-keys')

    def need_totp(self):
        self.need_keys()
        if self.world.store.has('totp.seed.dpapi'):
            return
        if not (self.auto or self.force_auto):
            raise DrillBlocked('Сначала выполните шаг b (привязка телефона)')
        self.ok('setup-totp', answers=[self.new_phone()])

    def need_codes(self):
        self.need_totp()
        if (self.auto or self.force_auto) and len(self.memory.codes) < 2:
            self.ok('new-recovery-codes', answers=[self.phone()])

    def need_payloads(self):
        self.need_totp()
        for name in secret_store.KEY_NAMES:
            if name not in self.memory.payloads:
                self.ok('reveal', '--key', name, answers=[self.phone()])

    def package(self):
        """The next fake package of the world's tree: (path, source commit, package version)."""
        number = max(int(entry['package_version'].split('.')[2].split('-')[0]) for entry in self.world.entries())+1
        version = '0.0.%d-alpha1-1' % number
        path, commit = self.world.lab.add_package(version)
        self.step('Новый фиктивный пакет %s' % path.name, 'New fake package %s' % path.name)
        return path, commit, version

    def sign(self, key='main', answers=None):
        path, commit, version = self.package()
        self.ok('sign-release', '--artifact', path, '--source-commit', commit, '--key', key, '--no-ots', answers=answers or [self.phone()])
        return path, version

    def revoke(self, key_id):
        """The manual step of section 8 of the signing guide: a line in keys/revoked, and the kit literals follow it."""
        seq = len(self.world.entries())
        keytool.write_revocations(self.world.root, keytool.revocations(self.world.root) | {(key_id, seq)})
        keytool.sync_kit(self.world.root)
        self.step('Ключ %s отозван с записи %d' % (key_id, seq), 'Key %s revoked from entry %d' % (key_id, seq))
        return seq

    def keep_chain_while(self, data):
        """Temporarily put forged chain bytes where the verifier reads them."""
        path = keytool.chain_path(self.world.root)
        original = path.read_bytes()

        class Keeper:
            def __enter__(inner):
                path.write_bytes(data)

            def __exit__(inner, *_):
                path.write_bytes(original)
        return Keeper()

    def install(self, router, path, version, *flags, chain_data=None, signature=None, payload=None):
        signature = signature if signature is not None else Path(str(path)+'.sig').read_bytes()
        return router.install(self.world.kit(), path.name, payload if payload is not None else path.read_bytes(),
                              chain_data if chain_data is not None else self.world.chain_data(), signature, version, *flags)

    # ---- the drills ---------------------------------------------------------------------------------------------------
    def drill_a(self):
        if self.world.has_keys():
            self.refused('KEYS-EXIST', 'new-keys')
        else:
            self.ok('new-keys')
        ids = sorted(keytool.trusted_keys(self.world.root))
        self.check(len(ids) == 2 and all(lab_mode.is_lab_key_id(item) for item in ids), 'Два ключа с тестовым префиксом id', 'Two keys with the test id prefix')
        comments = [(self.world.root/keytool.KEYS_DIR/item).read_text(encoding='ascii').splitlines()[0] for item in ids]
        self.check(all('TEST LAB KEY, NEVER FOR A RELEASE' in line for line in comments), 'В .pub строка TEST LAB KEY', 'TEST LAB KEY comment in the .pub files')
        self.check(keytool.chain_path(self.world.root).name == 'CHAIN-LAB.jsonl', 'Своя цепочка CHAIN-LAB.jsonl', 'Own chain CHAIN-LAB.jsonl')
        self.ok('verify-release')
        real = {path.name for path in (lab_mode.ROOT/keytool.KEYS_DIR).iterdir()}
        self.check(not real.intersection(ids), 'Тестовых ключей нет в настоящем списке доверия', 'No test key in the real trust list')

    def drill_b(self):
        self.need_keys()
        if self.world.store.has('totp.seed.dpapi'):
            self.refused('TOTP-EXISTS', 'setup-totp')
            self.note('Телефон уже привязан. Заново привязать можно учением g или сбросом лаборатории.',
                      'The phone is already enrolled. Re-enrol with drill g or a lab reset.')
            return
        self.refused('TOTP-NOT-ENROLLED', 'reveal', '--key', 'main')
        self.ok('setup-totp', answers=[self.new_phone()])
        self.check(self.world.store.has('totp.seed.dpapi'), 'Семя сохранено под DPAPI', 'Seed stored under DPAPI')
        self.check(totp.RecoveryCodes(self.world.store).remaining()[0] == totp.RECOVERY_COUNT, 'Выдано 10 кодов восстановления', '10 recovery codes issued')

    def drill_c(self):
        self.need_totp()
        self.ok('new-recovery-codes', answers=[self.phone()])
        codes = list(self.memory.codes)
        self.check(len(set(codes)) == totp.RECOVERY_COUNT, 'Показаны 10 разных кодов', '10 different codes shown')
        record = totp.RecoveryCodes(self.world.store).load()
        self.check(record is not None and all('hash' in row and 'code' not in row for row in record['codes']), 'В хранилище только соли и хеши', 'Only salts and hashes are stored')
        stored = b''.join(path.read_bytes() for path in self.world.store.root.iterdir() if path.is_file())
        self.check(not any(code.encode('ascii') in stored for code in codes), 'Кодов нет на диске открытым текстом', 'No code on disk in plain text')

    def drill_d(self):
        self.need_totp()
        self.refused('TOTP-WRONG-CODE', 'reveal', '--key', 'main', answers=[self.fixed(self.wrong_code())])
        self.memory.payloads.pop('main', None)
        self.ok('reveal', '--key', 'main', answers=[self.phone()])
        self.ok('reveal', '--key', 'reserve', answers=[self.phone()])
        line = self.memory.payloads.get('main', '')
        self.check(line.startswith(lab_mode.PAYLOAD_TAG+':MAIN:'), 'Строка с тестовой меткой HSAI-SK1-LAB', 'A line with the HSAI-SK1-LAB test tag')
        named, key = keytool.parse_payload(line)
        self.check(key.key_id.hex() == self.world.key_id('main'), 'Строка относится к тестовому main', 'The line belongs to the test main key')
        self.check(line[20:44] not in json.dumps(self.steps), 'Секрет в журнал не попал', 'The secret is not in the log')

    def drill_e(self):
        self.need_totp()
        store = self.world.store
        for name in secret_store.KEY_NAMES:
            if self.auto:
                if name not in self.memory.payloads:
                    self.ok('reveal', '--key', name, answers=[self.phone()])
                continue
            text = self.ask('secret', 'Вставьте сохранённую строку ключа %s (из учения d)' % name, 'Paste the stored %s key line (from drill d)' % name, 'HSAI-SK1-LAB:...')
            self.memory.payloads[name] = re.sub(r'\s+', '', text).upper()
        for name in secret_store.KEY_NAMES:
            named, key = keytool.parse_payload(self.memory.payloads[name])
            trusted = keytool.trusted_keys(self.world.root).get(key.key_id.hex())
            self.check(named == name and trusted is not None and trusted.public == key.public, 'Строка %s проверена до очистки' % name, 'Line %s checked before the wipe' % name)
        before = self.memory.payloads['main']
        self.confirm_danger('Стереть хранилище лаборатории и изобразить новый ПК? Настоящее хранилище не затрагивается.',
                            'Wipe the lab store and simulate a new PC? The real store is not touched.')
        lab_mode.remove_tree(store.root)
        store.root.mkdir()
        self.step('Хранилище лаборатории стёрто: новый ПК', 'Lab store wiped: a new PC')
        self.refused('TOTP-NOT-ENROLLED', 'reveal', '--key', 'main')
        typo = before[:-1]+('A' if before[-1] != 'A' else 'B')
        self.refused('IMPORT-CHECKSUM', 'import', '--key', 'main', answers=[self.fixed(typo)])
        self.refused('IMPORT-KEY-UNTRUSTED', 'import', '--key', 'main',
                     answers=[self.fixed(keytool.secret_payload('main', lab_mode.new_key(True, usign_format.SecretKey.generate)))])
        self.refused('IMPORT-REAL-KEY-IN-LAB', 'import', '--key', 'main',
                     answers=[self.fixed(keytool.secret_payload('main', lab_mode.new_key(False, usign_format.SecretKey.generate)))])
        for name in secret_store.KEY_NAMES:
            self.ok('import', '--key', name, answers=[self.pasted(name)])
        self.ok('setup-totp', answers=[self.new_phone()])
        self.ok('reveal', '--key', 'main', answers=[self.phone()])
        self.check(self.memory.payloads['main'] == before, 'Показан тот же самый ключ', 'The very same key is shown')

    def drill_f(self):
        self.need_totp()
        path, version = self.sign()
        self.ok('verify-release', '--artifact', path)
        data, signature = path.read_bytes(), Path(str(path)+'.sig').read_bytes()
        keys = keytool.trusted_keys(self.world.root)
        self.check(usign_format.verify_file(keys, data, signature) == self.world.key_id('main'), 'Подпись проверена Python-верификатором', 'Signature verified by the Python verifier')
        try:
            usign_format.verify_file(keys, data+b'x', signature)
            self.fail('Изменённый пакет прошёл проверку', 'A changed package passed')
        except ValueError:
            self.step('Изменённый пакет отвергнут', 'A changed package is refused')
        try:
            box = self.sandbox()
        except DrillSkipped as why:
            self.note('Настоящий usign не проверялся: %s' % why, 'Real usign was not run: %s' % why)
            return
        router = self.router('f')
        router.put_file('message', data)
        router.put_file('message.sig', signature)
        router.put_file('tampered', data+b'x')
        folder = router.folder/'pub'
        folder.mkdir()
        for name in keys:
            shutil.copyfile(self.world.root/keytool.KEYS_DIR/name, folder/name)
        self.router_says(router.usign('-V', '-m', 'sim:message', '-x', 'sim:message.sig', '-P', 'sim:pub'), 0)
        self.router_says(router.usign('-V', '-q', '-m', 'sim:tampered', '-x', 'sim:message.sig', '-P', 'sim:pub'), 1)
        self.step('usign: %s' % ('настоящий OpenWrt' if box.real else 'Python-двойник'), 'usign: %s' % ('real OpenWrt' if box.real else 'Python twin'))
        if not box.real:
            self.note('Настоящего usign нет на этом ПК: проверено двойником.', 'No real usign on this PC: checked with the twin.')
        self.router_says(self.install(router, path, version), 0, 'release chain verified', installed=True)

    def drill_g(self):
        self.need_codes()
        store = self.world.store
        old_seed, left = self.world.seed(), totp.RecoveryCodes(store).remaining()[0]
        self.step('Телефон потерян: старое семя больше недоступно владельцу', 'Phone lost: the old seed is gone for the owner')
        self.ok('reset-totp', answers=[self.paper(), self.new_phone()])
        self.check(self.world.seed() != old_seed, 'Новое семя вместо старого', 'A new seed replaces the old one')
        self.check(totp.RecoveryCodes(store).remaining()[0] == left-1, 'Код восстановления сгорел, остальные живы', 'The recovery code burned, the rest still work')
        self.refused('RECOVERY-CODE-USED', 'reveal', '--key', 'main', answers=[self.fixed(self.last_recovery)])
        now = self.session.clock.now() if self.session.clock else time.time()
        self.refused('TOTP-WRONG-CODE', 'reveal', '--key', 'main', answers=[self.fixed(totp.totp(totp.seed_bytes(old_seed), now))])
        self.gate(self.phone())
        self.step('Новый телефон работает, старый нет', 'The new phone works, the old one does not')

    def drill_h(self):
        self.need_codes()
        leaked = list(self.memory.codes)
        self.step('Лист с кодами утёк: выпускаю новый набор', 'The sheet leaked: issuing a new set')
        self.ok('new-recovery-codes', answers=[self.phone()])
        fresh = list(self.memory.codes)
        self.check(not set(fresh).intersection(leaked), 'Новые коды не совпадают со старыми', 'The new codes differ from the old ones')
        if leaked:
            self.refused('RECOVERY-CODE-WRONG', 'reveal', '--key', 'main', answers=[self.fixed(leaked[0])])
        else:
            self.refused('RECOVERY-CODE-WRONG', 'reveal', '--key', 'main', answers=[self.paper()])
        with self.fork('h'):
            self.burn_all(fresh)

    def gate(self, answer):
        """The real gate of every protected command, without the command: nothing secret appears on the page."""
        self.queue = collections.deque([answer])
        self.output, self.fresh_codes = [], []
        try:
            keytool.require_totp(self.world.store, LabConsole(self))
        except ValueError as error:
            self.fail('Шлюз отказал: %s' % mask(error, self.known()), 'The gate refused: %s' % mask(error, self.known()))
        return list(self.output)

    def burn_all(self, codes):
        store = self.world.store
        self.step('Трачу все 10 кодов настоящим шлюзом', 'Spending all 10 codes through the real gate')
        warned = False
        for code in codes:
            warned = any('RECOVERY-CODES-LOW' in line for line in self.gate(self.fixed(code))) or warned
        self.check(warned, 'Предупреждение RECOVERY-CODES-LOW показано', 'RECOVERY-CODES-LOW warning shown')
        self.check(totp.RecoveryCodes(store).remaining()[0] == 0, 'Кодов не осталось', 'No codes left')
        self.refused('RECOVERY-CODE-USED', 'reveal', '--key', 'main', answers=[self.fixed(codes[-1])])
        self.ok('new-recovery-codes', answers=[self.phone()])
        self.check(totp.RecoveryCodes(store).remaining()[0] == totp.RECOVERY_COUNT, 'Новый набор из 10 кодов', 'A new set of 10 codes')

    def drill_i(self):
        self.need_totp()
        with self.fork('i') as world:
            main, reserve = world.key_id('main'), world.key_id('reserve')
            old_path, old_version = self.sign()
            box_router = None
            try:
                box_router = self.router('i')
            except DrillSkipped as why:
                self.note('Шаги роутера пропущены: %s' % why, 'Router steps skipped: %s' % why)
            if box_router:
                box_router.install_keys(world.root)
                self.router_says(self.install(box_router, old_path, old_version), 0, 'release chain verified')
            world.store.retire('main.key.dpapi')
            self.step('Секрет main потерян', 'The main secret is lost')
            path, commit, version = self.package()
            self.refused('STORE-MISSING', 'sign-release', '--artifact', path, '--source-commit', commit, '--no-ots', answers=[self.phone()])
            first = self.revoke(main)
            self.ok('sign-release', '--artifact', path, '--source-commit', commit, '--key', 'reserve', '--no-ots', answers=[self.phone()])
            head = world.entries()[-1]
            self.check(head['key_id'] == reserve and head['revoked'] == '%s:%d' % (main, first), 'Запись подписана reserve и несёт отзыв main', 'Entry signed by reserve, carrying the main revocation')
            self.ok('verify-release', '--artifact', path)
            self.check(any(entry['key_id'] == main for entry in world.entries()), 'Старые записи main остаются действительными', 'Older main entries stay valid')
            if box_router:
                self.router_says(self.install(box_router, path, version), 0, 'release chain extends the installed history', installed=True)
                self.step('Роутер принял релиз reserve без действий администратора', 'The router took the reserve release with no admin action')

    def forged_entry(self, world, stolen, name, payload):
        entries = world.entries()
        entry = chain.next_entry(entries, name+'.ipk', '6.6.6', '6.6.6-1', hashlib_hex(payload), len(payload), 'f'*40, keytool.utc(), stolen.key_id.hex())
        return world.chain_data()+chain.make_line(entry, stolen)+b'\n'

    def drill_j(self):
        self.need_totp()
        with self.fork('j') as world:
            main = world.key_id('main')
            stolen = keytool.load_secret(world.root, world.store, 'main')
            self.step('Злоумышленник получил секрет main', 'An attacker obtained the main secret')
            first_path, first_version = self.sign()
            before_revocation = world.chain_data()
            old_kit = world.lab.root/'kit-before-revocation.sh'
            shutil.copyfile(world.kit(), old_kit)
            self.revoke(main)
            path, version = self.sign('reserve')
            forged_chain = self.forged_entry(world, stolen, 'homensai-auto-vpn_6.6.6-1_all', b'evil package\n')
            try:
                chain.verify_chain(forged_chain, keytool.trusted_keys(world.root), keytool.revocations(world.root))
                self.fail('Поддельная запись прошла проверку', 'A forged entry passed')
            except chain.ChainError as error:
                self.check(error.code == 'CHAIN-KEY-REVOKED', 'Запись украденным ключом отвергнута: CHAIN-KEY-REVOKED', 'Entry by the stolen key refused: CHAIN-KEY-REVOKED')
            with self.keep_chain_while(forged_chain):
                self.refused('CHAIN-KEY-REVOKED', 'verify-release')
            revoked = [key_id for key_id, _ in keytool.revocations(world.root)]
            keys = keytool.trusted_keys(world.root)
            for signer, code in ((stolen, 'SIGNATURE-KEY-REVOKED'), (usign_format.SecretKey.generate(), 'SIGNATURE-KEY-UNTRUSTED')):
                try:
                    usign_format.verify_file(keys, b'evil package\n', signer.sign_file(b'evil package\n'), revoked)
                    self.fail('Поддельная подпись прошла проверку', 'A forged signature passed')
                except ValueError as error:
                    self.check(code in str(error), 'Поддельная подпись отвергнута: %s' % code, 'Forged signature refused: %s' % code)
            try:
                router = self.router('j')
            except DrillSkipped as why:
                self.note('Шаги роутера пропущены: %s' % why, 'Router steps skipped: %s' % why)
                return
            router.install_keys(world.root)
            self.router_says(self.install(router, path, version), 0, 'release chain verified', installed=True)
            evil = b'evil package\n'
            evil_name = 'homensai-auto-vpn_6.6.6-1_all.ipk'
            self.router_says(router.install(world.kit(), evil_name, evil, forged_chain, stolen.sign_file(evil), '6.6.6-1'), 25, 'CHAIN-KEY-REVOKED', installed=False)
            self.router_says(router.install(world.kit(), path.name, path.read_bytes(), world.chain_data(), stolen.sign_file(path.read_bytes()), version), 23, 'SIGNATURE-KEY-REVOKED', installed=False)
            fork_entries = chain.verify_chain(before_revocation, keys)
            entry = chain.next_entry(fork_entries, evil_name, '6.6.6', '6.6.6-1', hashlib_hex(evil), len(evil), 'f'*40, keytool.utc(), main)
            forked = before_revocation+chain.make_line(entry, stolen)+b'\n'
            self.router_says(router.install(world.kit(), evil_name, evil, forked, stolen.sign_file(evil), '6.6.6-1'), 25, 'CHAIN-KEY-REVOKED', installed=False)
            self.step('Форк от старой головы отвергнут списком отзыва. Дальше старый комплект без этого списка: остаётся история роутера',
                      'A fork from the old head is refused by the revocation list. Next an old kit without that list: the router history remains')
            router.put_file('etc/keys/revoked', b'')
            self.router_says(router.install(old_kit, evil_name, evil, forked, stolen.sign_file(evil), '6.6.6-1'), 27, 'CHAIN-FORK', installed=False)
            behind = self.router('j2')
            behind.install_keys(world.root, names=[main, world.key_id('reserve')])
            (behind.folder/'etc/keys/revoked').write_text('', encoding='ascii')
            self.router_says(behind.install(old_kit, first_path.name, first_path.read_bytes(), before_revocation, Path(str(first_path)+'.sig').read_bytes(), first_version),
                             0, 'release chain verified')
            result = behind.install(old_kit, evil_name, evil, forked, stolen.sign_file(evil), '6.6.6-1')
            self.router_says(result, 0, 'release chain verified')
            self.note('Известное ограничение: роутер, ещё не получивший релиз с отзывом, примет следующий релиз, подписанный украденным ключом. '
                      'Поэтому отзыв надо выпускать сразу. Это совпадает с разделом 1 руководства.',
                      'Known limit: a router that has not yet received the release with the revocation accepts the next release signed by the stolen key. '
                      'Publish the revocation at once. This matches section 1 of the guide.')

    def drill_k(self):
        self.need_totp()
        with self.fork('k') as world:
            old_ids = sorted(keytool.trusted_keys(world.root))
            router_path, router_version = self.sign()
            router = self.router('k')
            router.install_keys(world.root)
            self.router_says(self.install(router, router_path, router_version), 0, 'release chain verified', installed=True)
            lab_mode.remove_tree(world.store.root)
            world.store.root.mkdir()
            self.step('Потеряно всё: секреты, телефон, ПК (хранилище копии стёрто)', 'Everything lost: secrets, phone, PC (the copy of the store is wiped)')
            self.ok('new-keys', '--emergency', answers=[self.new_phone()])
            new_ids = sorted(set(keytool.trusted_keys(world.root))-set(old_ids))
            self.check(len(new_ids) == 2 and all(lab_mode.is_lab_key_id(item) for item in new_ids), 'Созданы новые main и reserve', 'New main and reserve created')
            revoked = {key_id for key_id, _ in keytool.revocations(world.root)}
            self.check(revoked == set(old_ids), 'Старые ключи отозваны со следующей записи', 'The old keys are revoked from the next entry')
            path, version = self.sign()
            self.ok('verify-release', '--artifact', path)
            self.router_says(self.install(router, path, version), 25, 'CHAIN-KEY-UNTRUSTED', installed=False)
            self.step('Без администратора роутер новый ключ не принимает', 'Without the administrator the router refuses the new key')
            key_id = world.key_id('main')
            router.put_file('new.pub', (world.root/keytool.KEYS_DIR/key_id).read_bytes())
            self.router_says(router.trust_key('add', 'sim:new.pub', input_text='wrong\n'), 3, 'TRUST-CANCELLED')
            self.router_says(router.trust_key('add', 'sim:new.pub', input_text=key_id+'\n'), 0, 'TRUSTED: '+key_id)
            self.router_says(self.install(router, path, version), 0, 'release chain extends the installed history', installed=True)
            shown = router.trust_key('show')
            self.check(shown.code == 0 and key_id in shown.stdout, 'homensai-vpn-trust-key show видит новый ключ', 'homensai-vpn-trust-key show lists the new key')

    def drill_l(self):
        self.need_totp()
        with self.fork('l') as world:
            first_path, first_version = self.sign()
            first_chain = world.chain_data()
            second_path, second_version = self.sign()
            head_chain = world.chain_data()
            try:
                chain.check_extends(head_chain, first_chain)
                self.fail('Python: откат принят', 'Python: rollback accepted')
            except chain.ChainError as error:
                self.check(error.code == 'CHAIN-DOWNGRADE', 'Python: откат отвергнут CHAIN-DOWNGRADE', 'Python: rollback refused CHAIN-DOWNGRADE')
            main_key = keytool.load_secret(world.root, world.store, 'main')
            entries = chain.verify_chain(first_chain, keytool.trusted_keys(world.root), keytool.revocations(world.root))
            other = b'other package of the same version\n'
            entry = chain.next_entry(entries, second_path.name, second_version[:-2], second_version, hashlib_hex(other), len(other), 'e'*40, keytool.utc(), main_key.key_id.hex())
            forked = first_chain+chain.make_line(entry, main_key)+b'\n'
            try:
                chain.check_extends(head_chain, forked)
                self.fail('Python: форк принят', 'Python: fork accepted')
            except chain.ChainError as error:
                self.check(error.code == 'CHAIN-FORK', 'Python: форк отвергнут CHAIN-FORK', 'Python: fork refused CHAIN-FORK')
            lines = head_chain.split(b'\n')
            lines[-2] = lines[-2].replace(b'"size":', b'"size":1', 1)
            with self.keep_chain_while(b'\n'.join(lines)):
                self.refused('CHAIN-SIGNATURE-INVALID', 'verify-release')
            try:
                router = self.router('l')
            except DrillSkipped as why:
                self.note('Шаги роутера пропущены: %s' % why, 'Router steps skipped: %s' % why)
                return
            router.install_keys(world.root)
            self.router_says(self.install(router, second_path, second_version), 0, 'release chain verified', installed=True)
            self.router_says(self.install(router, first_path, first_version, chain_data=first_chain), 28, 'CHAIN-DOWNGRADE', installed=False)
            self.router_says(router.install(world.kit(), second_path.name, other, forked, main_key.sign_file(other), second_version), 27, 'CHAIN-FORK', installed=False)

    def drill_m(self):
        self.need_keys()
        world = self.world
        if not self.session.network and not self.session.stamper:
            raise DrillSkipped('сеть выключена (--no-network)')
        self.step('К календарям уходит только 32-байтный хеш тестовой записи', 'Only a 32-byte hash of a test entry goes to the calendars')
        if self.session.stamper:
            keytool.stamp_entries(world.root, LabConsole(self), [world.entries()[-1]], self.session.stamper)
        else:
            self.ok('ots-stamp')
        if any('OTS-PENDING-RETRY' in line for line in self.output):
            raise DrillSkipped('календари OpenTimestamps недоступны')
        proofs = sorted((world.root/keytool.OTS_DIR).glob('*.ots'))
        self.check(bool(proofs), 'Доказательство сохранено в лаборатории', 'The proof is stored in the lab')
        rows = keytool.ots_report(world.root, header_source=no_headers)
        self.check(rows and all(row['status'] in ('pending', 'confirmed') for row in rows), 'Статус: %s' % ', '.join(row['status'] for row in rows), 'Status: %s' % ', '.join(row['status'] for row in rows))

    def drill_n(self):
        self.need_totp()
        store, age = self.world.store, agetool
        real = age.REPO_RECIPIENTS.read_bytes()
        if not store.has(age.IDENTITY):
            self.ok('new-identity', module=age)
        output = self.ok('recipients', module=age)
        self.check('MATCH' in output, 'Получатель закреплён', 'The recipient is pinned')
        self.check(age.REPO_RECIPIENTS.read_bytes() == real, 'Настоящий recipients.txt не изменён', 'The real recipients.txt is unchanged')
        self.memory.age = None
        self.ok('reveal', '--qr', 'none', answers=[self.phone()], module=age)
        identity = self.memory.age
        self.check(bool(identity) and identity.startswith('AGE-SECRET-KEY-1'), 'Личность показана после кода с телефона', 'The identity is shown after the phone code')
        with self.fork('n') as world:
            archive = world.lab.root/'fake-archive.tar'
            with tarfile.open(archive, 'w') as tar:
                payload = b'fake secret file of the drill\n'
                info = tarfile.TarInfo('fake/secret.txt')
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            data, sealed, opened = archive.read_bytes(), str(archive)+'.age', str(archive)+'.out'
            self.ok('encrypt', '--in', archive, '--out', sealed, module=age)
            self.ok('verify-archive', '--archive', sealed, module=age)
            world.store.retire(age.IDENTITY)
            self.step('Новый ПК: личности в хранилище нет', 'A new PC: no identity in the store')
            self.refused('IDENTITY-MISSING', 'decrypt', '--in', sealed, '--out', opened, module=age)
            stranger = agetool.age.Identity.generate().encode()
            self.memory.age = None
            self.refused('IMPORT-UNKNOWN-IDENTITY', 'import', answers=[self.fixed(stranger)], module=age)
            self.ok('import', answers=[self.fixed(identity)], module=age)
            self.ok('decrypt', '--in', sealed, '--out', opened, module=age)
            self.check(Path(opened).read_bytes() == data, 'Архив расшифрован байт в байт', 'The archive decrypts byte for byte')
            Path(opened).unlink()
            self.refused('STOP', 'decrypt', '--in', sealed, '--out', opened, '--paste-identity', answers=[self.fixed(stranger)], module=age)
            damaged = bytearray(Path(sealed).read_bytes())
            damaged[-1] ^= 1
            Path(sealed).write_bytes(bytes(damaged))
            self.refused('STOP', 'decrypt', '--in', sealed, '--out', opened, module=age)
            self.step('Чужая личность и испорченный архив отвергнуты', 'A foreign identity and a damaged archive are refused')
        self.memory.age = identity

    def drill_o(self):
        self.need_totp()
        with self.fork('o') as world:
            root = world.root
            path, commit, version = self.package()
            for name, data in FAKE_EVIDENCE.items():
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                (root/name).write_bytes(data)
            folder = root/'releases/evidence'/version
            self.step('Фиктивные отчёты: история тестов, CI, soak, очередь, формальная проверка', 'Fake reports: test history, CI, soak, queue, formal check')
            self.ok('build', '--out', folder, '--source-commit', commit, '--package-version', version, module=report_manifest)
            manifest = report_manifest.parse_manifest((folder/report_manifest.MANIFEST).read_bytes())
            self.check(sorted(row['path'] for row in manifest['files']) == sorted(FAKE_EVIDENCE) and not manifest['empty_categories'],
                       'Манифест перечисляет все %d файлов с SHA-256' % len(FAKE_EVIDENCE), 'The manifest lists all %d files with SHA-256' % len(FAKE_EVIDENCE))
            stop = self.refused('EVIDENCE-SIGNATURE-MISSING', 'verify', folder, module=report_manifest)
            self.check('EVIDENCE-NOT-IN-CHAIN' in stop, 'Неподписанный манифест не принят и не связан с цепочкой', 'An unsigned manifest is refused and not linked to the chain')
            self.ok('sign-release', '--artifact', path, '--source-commit', commit, '--evidence', folder, '--no-ots', answers=[self.phone()])
            self.check(any('EVIDENCE-SIGNED' in line for line in self.output), 'Манифест подписан тем же путём с кодом, хеш внутри записи цепочки',
                       'The manifest is signed by the same gated path, its hash is inside the chain entry')
            output = self.ok('verify', folder, module=report_manifest)
            self.check(any('"result": "PASS"' in line for line in output), 'Проверка честного комплекта: PASS', 'Verification of the honest set: PASS')
            self.ok('verify-release', '--artifact', path)
            try:
                router = self.router('o')
            except DrillSkipped as why:
                self.note('Шаги роутера пропущены: %s' % why, 'Router steps skipped: %s' % why)
            else:
                router.install_keys(world.root)
                self.router_says(self.install(router, path, version), 0, 'release chain verified', installed=True)
                self.step('Запись цепочки с evidence_sha256 принята строгим sed роутера', 'The router sed accepts a chain entry with evidence_sha256')
            honest = {name: (root/name).read_bytes() for name in FAKE_EVIDENCE}
            honest_manifest = (folder/report_manifest.MANIFEST).read_bytes()
            signature = (folder/(report_manifest.MANIFEST+'.sig')).read_bytes()
            target = root/'qa/FAKE-LOCAL-CI.json'

            def restore():
                for name, data in honest.items():
                    (root/name).parent.mkdir(parents=True, exist_ok=True)
                    (root/name).write_bytes(data)
                (folder/report_manifest.MANIFEST).write_bytes(honest_manifest)
                (folder/(report_manifest.MANIFEST+'.sig')).write_bytes(signature)

            # 1. one file edited: the verifier names exactly it
            target.write_bytes(honest['qa/FAKE-LOCAL-CI.json'].replace(b'"tests": 100', b'"tests": 999'))
            stop = self.refused('EVIDENCE-FILE-CHANGED: qa/FAKE-LOCAL-CI.json', 'verify', folder, module=report_manifest)
            self.check(stop.count('EVIDENCE-FILE-CHANGED') == 1 and 'EVIDENCE-FILE-MISSING' not in stop,
                       'Названа ровно одна изменённая запись: qa/FAKE-LOCAL-CI.json', 'Exactly one changed file is named: qa/FAKE-LOCAL-CI.json')
            restore()
            # 2. one file deleted
            (root/'private/soak-24h/report-fake/cycles.json').unlink()
            self.refused('EVIDENCE-FILE-MISSING: private/soak-24h/report-fake/cycles.json', 'verify', folder, module=report_manifest)
            restore()
            # 3. the forger also rewrites the manifest with the new hash: the signature and the chain link no longer fit
            changed = json.loads(honest_manifest)
            forged = honest['docs/test-history/results.json'].replace(b'"failed": 0', b'"failed": 7')
            (root/'docs/test-history/results.json').write_bytes(forged)
            for row in changed['files']:
                if row['path'] == 'docs/test-history/results.json':
                    row['sha256'] = hashlib_hex(forged)
            (folder/report_manifest.MANIFEST).write_bytes(chain.canonical(changed))
            stop = self.refused('EVIDENCE-SIGNATURE-INVALID', 'verify', folder, module=report_manifest)
            self.check('EVIDENCE-NOT-IN-CHAIN' in stop and 'EVIDENCE-FILE-CHANGED' not in stop,
                       'Манифест подогнан под файл, но подпись и ссылка в цепочке не сходятся', 'The manifest was fitted to the file, but the signature and the chain link do not fit')
            restore()
            # 4. a hand edit of the manifest bytes, even a newline
            (folder/report_manifest.MANIFEST).write_bytes(honest_manifest+b'\n')
            self.refused('EVIDENCE-MANIFEST-FORMAT', 'verify', folder, module=report_manifest)
            restore()
            # 5. the signature removed
            (folder/(report_manifest.MANIFEST+'.sig')).unlink()
            self.refused('EVIDENCE-SIGNATURE-MISSING', 'verify', folder, module=report_manifest)
            restore()
            # 6. a freshly built manifest of the swapped files, with the old signature copied over
            other = root/'releases/evidence'/(version+'-forged')
            target.write_bytes(honest['qa/FAKE-LOCAL-CI.json'].replace(b'"ci": "pass"', b'"ci": "fail"'))
            self.ok('build', '--out', other, '--source-commit', commit, '--package-version', version, module=report_manifest)
            (other/(report_manifest.MANIFEST+'.sig')).write_bytes(signature)
            stop = self.refused('EVIDENCE-SIGNATURE-INVALID', 'verify', other, module=report_manifest)
            self.check('EVIDENCE-NOT-IN-CHAIN' in stop, 'Новый манифест с чужой подписью не проходит и не найден в цепочке', 'A new manifest with the old signature fails and is not in the chain')
            restore()
            # 7. the chain without the signed release entry
            lines = world.chain_data().split(b'\n')
            with self.keep_chain_while(b'\n'.join(lines[:-2])+b'\n'):
                self.refused('EVIDENCE-NOT-IN-CHAIN', 'verify', folder, module=report_manifest)
            self.ok('verify', folder, module=report_manifest)
            self.step('Всё возвращено на место: проверка снова PASS', 'Everything put back: verification passes again')

    def execute(self):
        started = time.time()
        self.routers = []
        status, message = PASS, ''
        try:
            getattr(self, 'drill_'+self.drill)()
        except DrillFailed as error:
            status, message = FAIL, str(error)
        except DrillSkipped as error:
            status, message = SKIP, str(error)
        except DrillBlocked as error:
            status, message = BLOCKED, str(error)
        except DrillCancelled as error:
            status, message = CANCELLED, str(error)
        except Exception as error:  # a drill must report, and only masked text may leave it
            status, message = FAIL, '%s: %s' % (type(error).__name__, mask(error, self.known()))
            self.step(message, ok=False)
        finally:
            for folder in self.routers:
                lab_mode.remove_tree(folder)
            if self.session.lab.work.is_dir() and not any(self.session.lab.work.iterdir()):
                self.session.lab.work.rmdir()
        title = next(row for row in TITLES if row[0] == self.drill)
        result = {'id': self.drill, 'ru': title[1], 'en': title[2], 'status': status, 'message': mask(message, self.known()),
                  'steps': self.steps, 'notes': self.notes, 'seconds': round(time.time()-started, 1), 'mode': 'auto' if self.auto else 'manual',
                  'finished_utc': keytool.utc()}
        self.emit({'type': 'result', 'status': status, 'message': result['message']})
        return result


def hashlib_hex(data):
    return hashlib.sha256(data).hexdigest()


def no_headers(height):
    """The page and the drills never ask a block explorer: a proof that needs one stays 'unverified'."""
    raise ots.HeaderError('offline')


# ---- state, report ------------------------------------------------------------------------------------------------------

def safe(function, default=None):
    try:
        return function()
    except (ValueError, OSError, KeyError, IndexError) as error:
        return default if default is not None else {'error': mask(error)}


def lab_state(lab):
    """What the page shows: public facts only, no secret and no secret-derived value beyond what the tools print."""
    world = World(lab)
    store, root = world.store, world.root
    names = {value.get('key_id'): name for name, value in store.public_index().items()} if (store.root/'keys.json').is_file() else {}
    revoked = safe(lambda: keytool.revocations(root), set())

    def key_rows():
        rows = []
        for key_id, key in sorted(keytool.trusted_keys(root).items()):
            limits = [first for other, first in revoked if other == key_id]
            name = names.get(key_id, '')
            rows.append({'id': key_id, 'name': name, 'fingerprint': key.full_fingerprint(), 'revoked_from': min(limits) if limits else None,
                         'secret': bool(name) and store.key_path(name).exists(), 'comment': (root/keytool.KEYS_DIR/key_id).read_text(encoding='ascii').splitlines()[0][19:]})
        return rows

    def chain_row():
        data = keytool.read_chain(root)
        if not data:
            return {'entries': 0}
        entries = keytool.verified_chain(root)[0]
        head = entries[-1]
        return {'entries': len(entries), 'head': head['package_version'], 'signer': head['key_id'], 'sha256': chain.entry_hash(head), 'file': keytool.chain_path(root).name}

    def otp_row():
        state = totp.load_state(str(store.path('totp-state.json')))
        left = max(0, int(state['locked_until']-time.time()))
        return {'enrolled': store.has('totp.seed.dpapi'), 'locked_seconds': left, 'failures': state['failures']}

    def code_row():
        left, problem = totp.RecoveryCodes(store).remaining()
        return {'left': left, 'total': totp.RECOVERY_COUNT, 'problem': (problem or '').split(':')[0]}

    def ots_rows():
        rows = keytool.ots_report(root, header_source=no_headers) if keytool.read_chain(root) else []
        return [{'version': row['package_version'], 'status': row['status']} for row in rows]

    def age_row():
        recipients = agetool.pinned_recipients(store)
        return {'identity': store.has(agetool.IDENTITY), 'recipient': recipients[0].encode() if recipients else ''}

    results = safe(lambda: json.loads(lab.results.read_text(encoding='utf-8')), {}) if lab.results.is_file() else {}
    return {'lab': str(lab.root), 'keys': safe(key_rows, []), 'totp': safe(otp_row), 'codes': safe(code_row), 'chain': safe(chain_row),
            'revoked': sorted('%s:%d' % item for item in revoked), 'ots': safe(ots_rows, []), 'age': safe(age_row),
            'results': {key: {'status': value.get('status'), 'mode': value.get('mode'), 'finished_utc': value.get('finished_utc')} for key, value in results.items()}}


def save_result(lab, result):
    results = {}
    if lab.results.is_file():
        results = json.loads(lab.results.read_text(encoding='utf-8'))
    results[result['id']] = result
    lab.results.write_text(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')
    write_report(lab, results)


STATUS_RU = {PASS: 'ПРОЙДЕНО', FAIL: 'ОШИБКА', SKIP: 'ПРОПУЩЕНО', BLOCKED: 'НУЖЕН ПРЕДЫДУЩИЙ ШАГ', CANCELLED: 'ОТМЕНЕНО'}


def write_report(lab, results, version=None):
    rows, details = [], []
    for key, ru, _ in TITLES:
        row = results.get(key)
        status = row['status'] if row else 'НЕ ЗАПУСКАЛОСЬ'
        rows.append('<tr><td>%s</td><td>%s</td><td class="s %s">%s</td><td>%s</td><td>%s</td></tr>' % (
            key, html.escape(ru), html.escape(status), html.escape(STATUS_RU.get(status, status)),
            html.escape(row['mode'] if row else ''), html.escape(row['finished_utc'] if row else '')))
        if row:
            lines = []
            for step in row['steps']:
                mark = '✓' if step['ok'] else '✗'
                lines.append('<li class="%s">%s %s%s</li>' % ('' if step['ok'] else 'bad', mark, html.escape(step['ru']), ''.join(
                    '<pre>%s</pre>' % html.escape(line) for line in step['output'])))
            notes = ''.join('<p class="note">%s</p>' % html.escape(note['ru']) for note in row['notes'])
            message = '<p>%s</p>' % html.escape(row['message']) if row['message'] else ''
            details.append('<details%s><summary>%s. %s: %s (%s c)</summary>%s%s<ol>%s</ol></details>' % (
                ' open' if status not in (PASS,) else '', key, html.escape(ru), html.escape(STATUS_RU.get(status, status)), row['seconds'], message, notes, ''.join(lines)))
    page = REPORT % {'stamp': keytool.utc(), 'rows': ''.join(rows), 'details': ''.join(details), 'lab': html.escape(str(lab.root)),
                     'program': html.escape(version or program_version()), 'style': html.escape(style_version())}
    temporary = lab.report.with_name(lab.report.name+'.tmp')
    temporary.write_text(page, encoding='utf-8')
    os.replace(temporary, lab.report)


def program_version():
    try:
        return json.loads((lab_mode.ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']['version']
    except (OSError, ValueError, KeyError):
        return '-'


def style_version():
    try:
        text = (lab_mode.ROOT/'router/attribution_panel.inc.js').read_text(encoding='utf-8')
        return re.search(r"HV_STYLE_VERSION='([^']+)'", text).group(1)
    except (OSError, AttributeError):
        return 'HomenS.AI Style'


REPORT = '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signing Drills</title><style>
:root{--bg:#f3f5f8;--card:#fff;--ink:#14202c;--mute:#5a6774;--line:#dbe2ea;--ok:#1f9e4f;--bad:#d23b33;--warn:#c98a00;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0f151c;--card:#17202a;--ink:#e6edf4;--mute:#9aa8b6;--line:#2a3644;--ok:#43c873;--bad:#ff6b62;--warn:#f0b53a;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,"Segoe UI",Roboto,Arial,sans-serif;padding:16px}
main{max-width:980px;margin:0 auto}h1{font-size:1.4rem;margin:.2em 0}.banner{background:var(--warn);color:#14202c;padding:8px 12px;border-radius:9px;font-weight:700}
table{width:100%%;border-collapse:collapse;background:var(--card);margin:14px 0}td,th{border:1px solid var(--line);padding:6px 9px;text-align:left;overflow-wrap:anywhere}
.s{font-weight:700}.PASS{color:var(--ok)}.FAIL,.BLOCKED{color:var(--bad)}.SKIP,.CANCELLED{color:var(--warn)}
details{background:var(--card);border:1px solid var(--line);border-radius:9px;margin:8px 0;padding:8px 12px}summary{cursor:pointer;font-weight:600}
pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:2px 0;font:12.5px/1.4 ui-monospace,Consolas,monospace;color:var(--mute)}li.bad{color:var(--bad)}
.note{border-left:3px solid var(--warn);padding:4px 8px}footer{color:var(--mute);font-size:.82rem;margin-top:16px}a{color:inherit}
</style></head><body><main>
<p class="banner">ТЕСТОВАЯ ЛАБОРАТОРИЯ: ключи этого отчёта не годятся для настоящих релизов. Секреты в отчёт не попадают.</p>
<h1>HomenS.AI Auto VPN: учения по подписи</h1><p>Отчёт %(stamp)s. Лаборатория: %(lab)s</p>
<table><tr><th>#</th><th>Сценарий</th><th>Итог</th><th>Режим</th><th>Завершён (UTC)</th></tr>%(rows)s</table>
%(details)s
<footer>HomenS.AI Auto VPN · GL.iNet GL-MT6000 · Flint 2 · Программа %(program)s · %(style)s · Developer · <a href="https://homensai.com">Serhii Khomenko</a></footer>
</main></body></html>'''


def run_drill(session, drill, emit=None, ask=None, auto=True):
    result = Run(session, drill, emit, ask, auto).execute()
    save_result(session.lab, result)
    return result


def run_all(lab, only=None, emit=None, stamper=None, sandbox=None, network=True):
    """Every drill in order on a throwaway sub-lab with the virtual clock: the owner's lab stays as it is, the report is shared."""
    target = lab_mode.LabDir(lab.root/'work'/('headless-%s' % time.time_ns())).ensure()
    session = Session(target, clock=VirtualClock(), stamper=stamper, sandbox=sandbox, network=network)
    results = []
    try:
        for row in TITLES:
            if only and row[0] not in only:
                continue
            if emit:
                emit({'type': 'drill', 'id': row[0], 'ru': row[1], 'en': row[2]})
            result = Run(session, row[0], emit, None, True).execute()
            save_result(lab, result)
            results.append(result)
    finally:
        lab_mode.remove_tree(target.root)
        if lab.work.is_dir() and not any(lab.work.iterdir()):
            lab.work.rmdir()
    return results
