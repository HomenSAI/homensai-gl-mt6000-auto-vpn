"""Offline cascade executor contract; deliberately not wired to router services.

Only MemoryBackend is supported. Its cooperative lease is a test double, not
evidence that GL.iNet workers participate in arbitration. No network commands.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import uuid


class Refused(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Refused(code)


def clock(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            'CASCADE-CLOCK')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def identity(value):
    require(isinstance(value, str) and 0 < len(value) <= 128 and
            all(c.isalnum() or c in ':_.-' for c in value), 'CASCADE-IDENTITY')
    return value


class EdgeAuthority:
    """Ephemeral, single-use per-edge proofs. Restart invalidates all proofs.

    A proof is a lookup handle, not a self-signed caller-controlled dictionary.
    The caller must obtain evidence under the cooperative backend lease.
    """
    def __init__(self, max_pending=64):
        require(type(max_pending) is int and 1 <= max_pending <= 256,
                'CASCADE-PROOF-LIMIT')
        self.max_pending = max_pending
        self.pending = {}
        self.last_time = 0
        self.lock = threading.RLock()

    def _time(self, now):
        clock(now)
        require(now >= self.last_time, 'CASCADE-CLOCK-REGRESSION')
        self.last_time = now

    def issue(self, context, now, deadline):
        with self.lock:
            self._time(now)
            clock(deadline)
            require(now < deadline <= now + 60, 'CASCADE-PROOF-DEADLINE')
            self.pending = {k: v for k, v in self.pending.items()
                            if v['deadline'] > now}
            require(len(self.pending) < self.max_pending, 'CASCADE-PROOF-CAPACITY')
            self._validate_context(context)
            require(0 <= now-context['probe']['time'] <= 5, 'CASCADE-PROBE-STALE')
            token = uuid.uuid4().hex
            self.pending[token] = dict(context=copy.deepcopy(context), deadline=deadline)
            return token

    @staticmethod
    def _validate_context(ctx):
        require(isinstance(ctx, dict) and set(ctx) == {
            'source', 'target', 'transaction', 'generation', 'policy_hash',
            'metadata_revision', 'recovery_revision', 'root', 'before', 'after',
            'boot_id', 'lease_id', 'profile_revision', 'expected_interface', 'expected_exit',
            'probe'}, 'CASCADE-PROOF-SCHEMA')
        for key in ('source', 'target', 'transaction', 'generation',
                    'metadata_revision', 'recovery_revision', 'boot_id',
                    'lease_id', 'profile_revision', 'expected_interface', 'expected_exit'):
            identity(ctx[key])
        require(ctx['source'] != ctx['target'], 'CASCADE-SAME-EDGE')
        probe = ctx['probe']
        require(isinstance(probe, dict) and set(probe) == {
            'profile', 'bound', 'dns', 'https', 'time'}, 'CASCADE-PROBE-SCHEMA')
        clock(probe['time'])
        require(probe['profile'] == ctx['target'] and probe['bound'] is True and
                probe['dns'] is True and probe['https'] is True,
                'CASCADE-PROBE-UNVERIFIED')
        for key in ('root', 'before', 'after'):
            order = ctx[key]
            require(isinstance(order, list) and 2 <= len(order) <= 16,
                    'CASCADE-ORDER')
            for item in order:
                identity(item)
            require(len(set(order)) == len(order), 'CASCADE-ORDER')
        require(set(ctx['root']) == set(ctx['before']) == set(ctx['after']) and
                ctx['before'][0] == ctx['source'] and
                ctx['after'][0] == ctx['target'], 'CASCADE-EDGE-ORDER')
        require(isinstance(ctx['policy_hash'], str) and
                len(ctx['policy_hash']) == 64 and
                all(c in '0123456789abcdef' for c in ctx['policy_hash']),
                'CASCADE-POLICY-HASH')

    def consume(self, token, context, now):
        with self.lock:
            self._time(now)
            row = self.pending.pop(token, None)
            require(row is not None, 'CASCADE-PROOF-UNKNOWN-OR-REPLAYED')
            require(now < row['deadline'], 'CASCADE-PROOF-EXPIRED')
            self._validate_context(context)
            require(0 <= now-context['probe']['time'] <= 5, 'CASCADE-PROBE-STALE')
            require(row['context'] == context, 'CASCADE-PROOF-MISMATCH')
            return True


class Journal:
    """Bounded atomic private journal; separate original-root and pre-hop state.

    Checksum detects damage, not hostile filesystem edits. The caller supplies
    a dedicated private directory. No arbitrary VPN configuration is stored.
    """
    LIMIT = 32768
    PHASES = {'PREPARED', 'APPLYING', 'WAIT-CONFIRM', 'COMMITTED',
              'ROLLING-BACK', 'STOPPED', 'HELD'}

    def __init__(self, directory):
        self.directory = Path(directory)
        require(not self.directory.is_symlink(), 'CASCADE-JOURNAL-SYMLINK')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == 'posix':
            metadata = self.directory.stat()
            require(metadata.st_uid == os.geteuid() and metadata.st_mode & 0o077 == 0,
                    'CASCADE-JOURNAL-NOT-PRIVATE')
        self.path = self.directory / 'cascade.json'
        self.previous = self.directory / 'cascade.previous.json'

    @classmethod
    def encode(cls, row):
        require(isinstance(row, dict) and set(row) == {
            'schema', 'phase', 'context', 'selected', 'time'}, 'CASCADE-JOURNAL-SCHEMA')
        require(type(row['schema']) is int and row['schema'] == 1 and row['phase'] in cls.PHASES,
                'CASCADE-JOURNAL-PHASE')
        EdgeAuthority._validate_context(row['context'])
        require(row['selected'] in row['context']['root'], 'CASCADE-JOURNAL-SELECTED')
        clock(row['time'])
        data = json.dumps(dict(payload=row, checksum=digest(row)), sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode()
        require(len(data) <= cls.LIMIT, 'CASCADE-JOURNAL-SIZE')
        return data

    def _atomic(self, target, data):
        require(not target.is_symlink(), 'CASCADE-JOURNAL-SYMLINK')
        fd, name = tempfile.mkstemp(prefix='.cascade-', dir=str(self.directory))
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, target)
            if os.name == 'posix':
                directory_fd = os.open(str(self.directory), os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def read(self, previous=False):
        path = self.previous if previous else self.path
        require(path.is_file() and not path.is_symlink(), 'CASCADE-JOURNAL-MISSING')
        require(path.stat().st_size <= self.LIMIT, 'CASCADE-JOURNAL-SIZE')
        try:
            row = json.loads(path.read_bytes())
            require(set(row) == {'payload', 'checksum'} and
                    row['checksum'] == digest(row['payload']), 'CASCADE-JOURNAL-CHECKSUM')
            self.encode(row['payload'])
            return row['payload']
        except (TypeError, KeyError, UnicodeError, json.JSONDecodeError):
            raise Refused('CASCADE-JOURNAL-CORRUPT') from None

    def write(self, row):
        data = self.encode(row)
        if self.path.exists():
            # Never replace the known-good copy with an unreadable current file.
            old = self.read()
            self._atomic(self.previous, self.encode(old))
        self._atomic(self.path, data)


class MemoryBackend:
    """Cooperative worker/operator test double. No native capability claim."""
    def __init__(self, order):
        self.order = list(order)
        self.generation = 'g1'
        self.metadata_revision = 'm1'
        self.recovery_revision = 'r1'
        self.profile_revision = 'p1'
        self.boot_id = uuid.uuid4().hex
        self.policy_hash = digest({'selectors': 'fixture', 'dns': 'fixture',
                                   'kill_switch': True})
        self.lease = None
        self.last_time = 0
        self.lock = threading.RLock()
        self.writes = []
        self.write_count = 0
        self.probes = {}

    def record_probe(self, profile, now, dns=True, https=True, bound=True):
        with self.lock:
            self._time(now)
            require(profile in self.order, 'CASCADE-PROBE-PROFILE')
            self.probes[profile] = dict(profile=profile, time=now, dns=dns,
                                        https=https, bound=bound)

    def _time(self, now):
        clock(now)
        require(now >= self.last_time, 'CASCADE-CLOCK-REGRESSION')
        self.last_time = now

    def acquire(self, owner, now, duration=30):
        with self.lock:
            self._time(now)
            identity(owner)
            require(type(duration) in (int, float) and 0 < duration <= 60,
                    'CASCADE-LEASE-DURATION')
            require(self.lease is None or now >= self.lease['deadline'],
                    'CASCADE-LEASE-BUSY')
            self.lease = dict(id=uuid.uuid4().hex, owner=owner, deadline=now+duration)
            return self.lease['id']

    def check(self, lease, now):
        self._time(now)
        require(self.lease is not None and self.lease['id'] == lease and
                now < self.lease['deadline'], 'CASCADE-LEASE-LOST')

    def release(self, lease):
        with self.lock:
            require(self.lease is not None and self.lease['id'] == lease,
                    'CASCADE-LEASE-LOST')
            self.lease = None

    def external_edit(self, order, now):
        with self.lock:
            self._time(now)
            require(self.lease is None or now >= self.lease['deadline'],
                    'CASCADE-LEASE-BUSY')
            self.order = list(order)
            self.generation = uuid.uuid4().hex

    def context(self, transaction, root, before, after, lease, now):
        with self.lock:
            self.check(lease, now)
            require(after[0] in self.probes, 'CASCADE-PROBE-MISSING')
            return dict(source=before[0], target=after[0], transaction=transaction,
                        root=list(root), before=list(before), after=list(after),
                        generation=self.generation, policy_hash=self.policy_hash,
                        metadata_revision=self.metadata_revision,
                        recovery_revision=self.recovery_revision,
                        profile_revision=self.profile_revision, probe=copy.deepcopy(self.probes[after[0]]), expected_interface='lan-fixture',
                        expected_exit='exit-' + after[0],
                        boot_id=self.boot_id, lease_id=lease)

    def apply(self, context, expected, desired, now):
        with self.lock:
            self.check(context['lease_id'], now)
            actual = self.context(context['transaction'], context['root'],
                                  context['before'], context['after'],
                                  context['lease_id'], now)
            require(actual == context and self.order == expected,
                    'CASCADE-EXTERNAL-POLICY')
            self.order = list(desired)
            self.writes.append(list(desired))
            del self.writes[:-256]
            self.write_count += 1


class OfflineExecutor:
    """Drive model intents with proof/lease/journal; no router entry point."""
    def __init__(self, backend, journal, authority):
        require(type(backend) is MemoryBackend, 'CASCADE-NATIVE-UNVERIFIED')
        self.backend, self.journal, self.authority = backend, journal, authority
        self.root = None
        self.pending = None
        self.phase = 'STOPPED'

    def _save(self, phase, now, selected):
        self.journal.write(dict(schema=1, phase=phase, context=self.pending,
                                selected=selected, time=now))
        self.phase = phase

    def prepare(self, intent, now):
        require(self.phase in ('STOPPED', 'COMMITTED'), 'CASCADE-EXECUTOR-BUSY')
        require(isinstance(intent, dict) and intent.get('operation') == 'apply' and
                intent.get('model_only') is True, 'CASCADE-INTENT')
        before, after = intent['before'], intent['after']
        require(self.backend.order == before, 'CASCADE-EXTERNAL-POLICY')
        require(type(intent.get('id')) is int and intent['id'] > 0, 'CASCADE-INTENT-ID')
        transaction = identity('tx-' + str(intent['id']) + '-' + uuid.uuid4().hex)
        lease = self.backend.acquire(transaction, now)
        try:
            root = self.root if self.root is not None else list(before)
            ctx = self.backend.context(transaction, root, before, after, lease, now)
            token = self.authority.issue(ctx, now, now + 25)
            self.pending = ctx
            self._save('PREPARED', now, before[0])
            self.root = list(root)
            return token
        except Exception:
            self.backend.release(lease)
            self.phase = 'HELD'
            raise

    def apply(self, token, now):
        require(self.phase == 'PREPARED', 'CASCADE-EXECUTOR-PHASE')
        with self.backend.lock:
            ctx = self.pending
            actual = self.backend.context(ctx['transaction'], ctx['root'], ctx['before'],
                                          ctx['after'], ctx['lease_id'], now)
            self.authority.consume(token, actual, now)
            require(actual == ctx, 'CASCADE-EXTERNAL-POLICY')
            self._save('APPLYING', now, ctx['source'])
            self.backend.apply(ctx, ctx['before'], ctx['after'], now)
            self._save('WAIT-CONFIRM', now, ctx['target'])

    def confirm(self, witness, now):
        require(self.phase == 'WAIT-CONFIRM', 'CASCADE-EXECUTOR-PHASE')
        ctx = self.pending
        with self.backend.lock:
            self.backend.check(ctx['lease_id'], now)
            # Revalidate metadata AND semantic policy, even when order is unchanged.
            actual = self.backend.context(ctx['transaction'], ctx['root'], ctx['before'],
                                          ctx['after'], ctx['lease_id'], now)
            require(actual == ctx and self.backend.order == ctx['after'],
                    'CASCADE-EXTERNAL-POLICY')
            require(isinstance(witness, dict) and set(witness) == {
                'transaction', 'target', 'interface', 'expected_interface',
                'exit', 'expected_exit', 'dns', 'https', 'time'}, 'CASCADE-WITNESS-SCHEMA')
            clock(witness['time'])
            require(witness['transaction'] == ctx['transaction'] and
                    witness['target'] == ctx['target'] and
                    identity(witness['interface']) == witness['expected_interface'] == ctx['expected_interface'] and
                    identity(witness['exit']) == witness['expected_exit'] == ctx['expected_exit'] and
                    witness['dns'] is True and witness['https'] is True and
                    self.journal.read()['time'] <= witness['time'] <= now and
                    now-witness['time'] <= 5, 'CASCADE-WITNESS-INVALID')
            self._save('COMMITTED', now, ctx['target'])
            self.backend.release(ctx['lease_id'])

    def rollback(self, now):
        require(self.phase in ('PREPARED', 'APPLYING', 'WAIT-CONFIRM'),
                'CASCADE-EXECUTOR-PHASE')
        ctx = self.pending
        with self.backend.lock:
            self.backend.check(ctx['lease_id'], now)
            # PREPARED must never accept an externally predicted after-order.
            allowed = [ctx['before']] if self.phase == 'PREPARED' else [ctx['before'], ctx['after']]
            require(self.backend.order in allowed, 'CASCADE-EXTERNAL-POLICY')
            self._save('ROLLING-BACK', now, self.backend.order[0])
            self.backend.apply(ctx, self.backend.order, ctx['before'], now)
            self._save('STOPPED', now, ctx['source'])
            self.backend.release(ctx['lease_id'])

    def recover(self):
        # Recovery is observational. No automatic writes, enable or lease theft.
        self.phase = 'HELD'
        row = self.journal.read()
        self.root = list(row['context']['root'])
        self.pending = row['context']
        expected = {'PREPARED': [self.pending['before']],
                    'WAIT-CONFIRM': [self.pending['after']],
                    'COMMITTED': [self.pending['after']],
                    'STOPPED': [self.pending['before']]}.get(
                        row['phase'], [self.pending['before'], self.pending['after']])
        require(all(getattr(self.backend, key) == self.pending[key] for key in (
                    'generation', 'boot_id', 'policy_hash', 'metadata_revision',
                    'recovery_revision', 'profile_revision')) and
                self.backend.order in expected,
                'CASCADE-RECOVERY-EXTERNAL')
        return dict(phase='HELD', auto=False, prior_phase=row['phase'],
                    root=list(self.root), selected=self.backend.order[0],
                    client_confirmation_required=True, live_capability='UNVERIFIED')
