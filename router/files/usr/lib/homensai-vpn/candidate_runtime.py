"""Isolated inactive-profile/probe contracts for offline adapters only.

No real namespace, route, DNS, key or service changes. An isolated route binding
is evidence supplied by the test double; Linux/device proof remains separate.
"""
import copy
import threading
import uuid
from cascade_executor import Refused, clock, identity, require


class MemoryProfileBackend:
    def __init__(self, profiles):
        require(isinstance(profiles, dict) and 1 <= len(profiles) <= 16,
                'CANDIDATE-PROFILE-COUNT')
        self.profiles = copy.deepcopy(profiles)
        for name, row in self.profiles.items():
            identity(name)
            require(set(row) == {'protocol', 'state', 'revision'} and
                    row['protocol'] in ('openvpn', 'wireguard') and
                    row['state'] in ('inactive', 'connected'), 'CANDIDATE-PROFILE')
            identity(row['revision'])
        self.handles = {}
        self.lock = threading.RLock()

    def start(self, profile):
        with self.lock:
            require(profile in self.profiles, 'CANDIDATE-PROFILE-REMOVED')
            require(len(self.handles) < 16, 'CANDIDATE-HANDLE-LIMIT')
            row = self.profiles[profile]
            require(row['state'] == 'inactive', 'CANDIDATE-PROFILE-BUSY')
            handle = uuid.uuid4().hex
            self.handles[handle] = dict(profile=profile, revision=row['revision'])
            row['state'] = 'connecting'
            return handle

    def observe(self, handle):
        with self.lock:
            require(handle in self.handles, 'CANDIDATE-HANDLE')
            owned = self.handles[handle]
            row = self.profiles.get(owned['profile'])
            require(row is not None and row['revision'] == owned['revision'],
                    'CANDIDATE-OWNERSHIP-LOST')
            return row['state']

    def cleanup(self, handle):
        with self.lock:
            self.observe(handle)
            row = self.handles.pop(handle)
            self.profiles[row['profile']]['state'] = 'inactive'


class CandidateSession:
    def __init__(self, backend, profile, now, timeout=20):
        require(type(backend) is MemoryProfileBackend, 'CANDIDATE-NATIVE-UNVERIFIED')
        clock(now)
        require(type(timeout) in (int, float) and 0 < timeout <= 60,
                'CANDIDATE-TIMEOUT')
        self.backend, self.profile = backend, profile
        self.last_time, self.deadline = now, now+timeout
        self.handle = backend.start(profile)
        self.state = 'connecting'

    def poll(self, now):
        clock(now)
        require(now >= self.last_time, 'CANDIDATE-CLOCK-REGRESSION')
        self.last_time = now
        if self.state not in ('connecting', 'connected'):
            return self.state
        try:
            observed = self.backend.observe(self.handle)
            if now >= self.deadline or observed == 'failed':
                self.backend.cleanup(self.handle)
                self.state = 'timeout' if now >= self.deadline else 'failed'
            else:
                require(observed in ('connecting', 'connected'), 'CANDIDATE-STATE')
                self.state = observed
        except Refused:
            self.state = 'held'
            raise
        return self.state

    def cancel(self):
        if self.state in ('connecting', 'connected'):
            try:
                self.backend.cleanup(self.handle)
            except Refused:
                self.state = 'held'
                raise
            self.state = 'cancelled'
        return self.state


class ProbeScheduler:
    """Bounded scheduler for fixture probes with certified isolated bindings.

    Byte reservations include both directions and remain charged after failure
    or cancellation, so retries cannot silently bypass the test's budget.
    """
    def __init__(self, concurrency=2, byte_budget=65536, duration=10):
        require(type(concurrency) is int and 1 <= concurrency <= 4,
                'CANDIDATE-CONCURRENCY')
        require(type(byte_budget) is int and 1024 <= byte_budget <= 1048576,
                'CANDIDATE-BYTE-LIMIT')
        require(type(duration) in (int, float) and 0 < duration <= 30,
                'CANDIDATE-PROBE-TIMEOUT')
        self.concurrency, self.budget, self.duration = concurrency, byte_budget, duration
        self.charged, self.last_time = 0, 0
        self.active = {}
        self.lock = threading.RLock()

    def _time(self, now):
        clock(now)
        require(now >= self.last_time, 'CANDIDATE-CLOCK-REGRESSION')
        self.last_time = now

    def reserve(self, profile, binding, now, byte_limit=4096):
        with self.lock:
            self._time(now)
            identity(profile)
            require(isinstance(binding, dict) and set(binding) == {
                'profile', 'interface', 'namespace', 'mark', 'isolated', 'revision'},
                'CANDIDATE-BINDING-SCHEMA')
            require(binding['profile'] == profile and binding['isolated'] is True,
                    'CANDIDATE-BINDING-UNVERIFIED')
            for key in ('interface', 'namespace', 'revision'):
                identity(binding[key])
            require(type(binding['mark']) is int and 1 <= binding['mark'] <= 0xffffffff,
                    'CANDIDATE-MARK')
            require(len(self.active) < self.concurrency, 'CANDIDATE-PROBE-BUSY')
            require(not any(row['profile'] == profile for row in self.active.values()),
                    'CANDIDATE-DUPLICATE-PROBE')
            require(type(byte_limit) is int and byte_limit > 0 and
                    self.charged+byte_limit <= self.budget, 'CANDIDATE-BUDGET')
            handle = uuid.uuid4().hex
            self.active[handle] = dict(profile=profile, binding=copy.deepcopy(binding),
                                       deadline=now+self.duration, started=now,
                                       byte_limit=byte_limit)
            self.charged += byte_limit
            return handle

    def finish(self, handle, binding, now, byte_count, dns, https):
        with self.lock:
            self._time(now)
            row = self.active.pop(handle, None)
            require(row is not None, 'CANDIDATE-PROBE-UNKNOWN')
            require(row['binding'] == binding, 'CANDIDATE-BINDING-CHANGED')
            require(now < row['deadline'], 'CANDIDATE-PROBE-EXPIRED')
            require(type(byte_count) is int and 0 <= byte_count <= row['byte_limit'],
                    'CANDIDATE-BUDGET-EXCEEDED')
            require(type(dns) is bool and type(https) is bool, 'CANDIDATE-PROBE-RESULT')
            return dict(profile=row['profile'], time=now, bound=True,
                        dns=dns, https=https, bytes=byte_count,
                        latency_ms=(now-row['started'])*1000, scope='offline-fixture')

    def cancel(self, handle):
        with self.lock:
            return self.active.pop(handle, None) is not None

    def expire(self, now):
        with self.lock:
            self._time(now)
            expired = [key for key, row in self.active.items() if now >= row['deadline']]
            for key in expired:
                del self.active[key]
            return len(expired)
