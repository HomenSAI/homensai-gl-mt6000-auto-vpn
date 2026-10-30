"""Resident read-only answers for the page: one root-only unix socket in RAM, owned by the monitor daemon.

Every page poll used to start python3, import the application and recompute the kernel attestation
projection and the manual-switch controls (1.7-3 s of router CPU per poll). The monitor process now
computes the same answers with the same functions (agent.status_reply/events_reply/history_reply and
auto_live.snapshot) and keeps the finished JSON in memory; the rpcd plugin reads it through a light client.

Safety contract:
- Only the read methods in METHODS with no arguments. Anything else, any malformed request and any
  failure while computing answers FALLBACK: the caller then runs agent.py exactly as before, so error
  codes, write methods and rpcd ACLs are unchanged.
- The page buttons in WRITERS (manual channel click, Start/Stop Auto, failure test, probe and response
  settings) are answered by the same functions agent.py calls, in this already running process (beta8
  measured 3.5 s of python start-up per click). They only queue or save; the supervisor validates and acts.
  FALLBACK is possible only before the function runs; once it ran, any failure is answered as unconfirmed,
  never repeated through agent.py.
- The socket is 0600 inside the 0700 runtime directory, peers must have this process' user id, and the
  socket is removed as soon as the monitor stops.
- A snapshot is served only while every control file (Auto/Stop requests, control revision, manual
  requests, journal, configuration) and the native controller state are unchanged since its computation
  began, and only while it is at most MAX_SERVE_AGE old. Otherwise the request waits for a computation
  that began after it arrived. Observations that change on every pass (status.json, histories) are
  refreshed shortly before the next expected poll, so one open page costs one computation per poll and
  several tabs share it. Without page polls nothing is computed.
- Display only: every write action still re-validates revision, kernel policy and health on its own.
"""
import json
import os
import socket
import stat
import struct
import threading
import time

METHODS = frozenset(('status', 'events', 'history', 'auto_live'))
WRITERS = frozenset(('pair_manual', 'native_start', 'native_stop', 'fault_start', 'fault_cancel', 'setup_probe', 'setup_response'))
WRITE_FAILED = {'pair_manual': {'accepted': False, 'queued': False, 'completed': False, 'blockers': ['PAIR-MANUAL-REQUEST-UNCONFIRMED']}}
WRITE_FAILED_DEFAULT = {'accepted': False, 'queued': False, 'saved': False, 'code': 'RPC-UNCONFIRMED', 'blockers': ['RPC-UNCONFIRMED']}
CACHED = ('status', 'events', 'history')
NAME = 'status.sock'
REQUEST_LIMIT = 65537 + 32       # method line plus the same 65537 request bytes agent.py reads
OK = b'OK\n'
FALLBACK = b'FALLBACK\n'
MAX_SERVE_AGE = 10.0             # an older snapshot is recomputed before it is answered
WAIT_LIMIT = 8.0                 # a request waits at most this long, then the caller runs agent.py
MIN_REFRESH = 3.0                # background computations of one method are at least this far apart
DEMAND_WINDOW = 60.0             # no poll for this long: no background work at all
WATCH_SECONDS = 1.0
CONNECTIONS = 8
IO_TIMEOUT = 2.0
NATIVE_LIMIT = 65536

# Written while answering (caches) or private to the RPC throttle: never a reason to recompute.
SELF_WRITTEN = frozenset(('pair-manual-kernel-cache.json', 'native-history-public.json', 'rpc-throttle.json',
                          'pair-manual-timing.json'))
# Rewritten by the two daemons on every pass/tick; they refresh on the poll schedule instead.
OBSERVATION = frozenset(('status.json', 'native-status.json', 'speed-traffic.json', 'checkpoint.json',
                         'checkpoint.backup.json', 'latency-history.json', 'ping-response-history.json',
                         'website-response-history.json', 'response-compare.json', 'probe-history.json',
                         'native-history.json', 'native-history.backup.json'))
CONFIGS = ('/etc/config/homensai_vpn', '/etc/config/route_policy', '/etc/config/network',
           '/etc/config/wireguard', '/etc/config/ovpnclient')
# native-status.json is rewritten with a new time on every controller tick; only these fields are state.
NATIVE_STATE = ('state', 'reason', 'mode', 'proof_scope', 'tx', 'source', 'target', 'blockers', 'alarm',
                'certified', 'readiness_verified', 'kernel_policy_verified', 'original_restored',
                'external_lan_verified', 'route_changed', 'transition_completed', 'transition_metadata_present',
                'destination_role', 'destination_profile_id', 'from_role', 'from_profile_id',
                'activation_reapply', 'expected_exit', 'deadline', 'request_id', 'manual_request_id')
PATH_STATE = ('confirmed', 'kernel_policy_verified', 'active_profile_id', 'source_profile_id',
              'target_profile_id', 'transitioning', 'code')
MISSING = object()


def splice(body, age):
    """Add the serving facts to a finished JSON object without re-encoding it."""
    extra = ('"served_from":"memory","served_age":%s' % json.dumps(round(max(0.0, age), 3))).encode('ascii')
    if not body.startswith(b'{') or not body.endswith(b'}'):
        return body
    return body[:-1] + (b',' if body != b'{}' else b'') + extra + b'}'


class Entry:
    __slots__ = ('signature', 'started', 'body', 'error')

    def __init__(self, signature, started, body, error):
        self.signature, self.started, self.body, self.error = signature, started, body, error


class StatusServer:
    def __init__(self, runtime, persist, builders, live, read_json, decode=None, stopping=None,
                 configs=CONFIGS, clock=time.monotonic, writers=None):
        self.runtime, self.persist = runtime, persist
        self.writers = {name: value for name, value in (writers or {}).items() if name in WRITERS}
        self.builders, self.live, self.read_json = dict(builders), live, read_json
        if decode is None:
            from rpc_input import decode_request as decode
        self.decode, self.stopping, self.configs, self.clock = decode, stopping, tuple(configs), clock
        self.path = runtime / NAME
        self._listener = None
        self._inode = None
        self._stopped = threading.Event()
        self._cond = threading.Condition()
        self._entries = {}
        self._wanted = {}
        self._last_request = {}
        self._period = {}
        self._duration = {}
        self._slots = threading.BoundedSemaphore(CONNECTIONS)
        self._monitor_lock = threading.Lock()
        self._monitor_key = None
        self._monitor_value = MISSING
        self._native_lock = threading.Lock()
        self._native_key = None
        self._native_digest = None
        self._threads = []

    # ---- lifecycle -------------------------------------------------------------------------------
    def start(self):
        self.runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.runtime.is_symlink():
            raise ValueError('symlink runtime refused')
        # Only the monitor holding agent.lock gets here: a leftover socket is from a killed predecessor.
        self._unlink(self.path)
        pending = self.runtime / ('.%s.%d' % (NAME, os.getpid()))
        self._unlink(pending)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            previous = os.umask(0o177)
            try:
                listener.bind(str(pending))
            finally:
                os.umask(previous)
            os.chmod(str(pending), 0o600)
            listener.listen(16)
            listener.settimeout(1.0)
            os.rename(str(pending), str(self.path))   # appears complete: bound, 0600, listening
            self._inode = os.lstat(str(self.path)).st_ino
        except BaseException:
            listener.close()
            self._unlink(pending)
            raise
        self._listener = listener
        for target, name in ((self._accept_loop, 'status-accept'), (self._refresh_loop, 'status-refresh')):
            thread = threading.Thread(target=target, name=name, daemon=True)
            self._threads.append(thread)
            thread.start()
        return self

    def close(self):
        if self._stopped.is_set() and self._listener is None:
            return
        self._stopped.set()
        with self._cond:
            self._cond.notify_all()
        self._remove_socket()
        listener, self._listener = self._listener, None
        if listener is not None:
            for finish in (lambda: listener.shutdown(socket.SHUT_RDWR), listener.close):
                try:
                    finish()        # shutdown wakes a blocked accept() at once
                except OSError:
                    pass
        for thread in self._threads:
            if thread is not threading.current_thread():
                thread.join(1)

    def _remove_socket(self):
        try:
            row = os.lstat(str(self.path))
            if self._inode is not None and row.st_ino == self._inode and stat.S_ISSOCK(row.st_mode):
                os.unlink(str(self.path))
        except OSError:
            pass

    @staticmethod
    def _unlink(path):
        try:
            os.unlink(str(path))
        except FileNotFoundError:
            pass

    def _stopping(self):
        if self._stopped.is_set():
            return True
        try:
            if self.stopping is not None and self.stopping():
                # The monitor is shutting down: new polls go straight to agent.py from now on.
                self._remove_socket()
                self._stopped.set()
                with self._cond:
                    self._cond.notify_all()
                return True
        except Exception:
            pass
        return False

    # ---- inputs ------------------------------------------------------------------------------------
    def load_monitor(self, default, copy=True):
        """read_json(RUNTIME/'status.json', default), parsed once per file version."""
        path = self.runtime / 'status.json'
        try:
            row = os.lstat(str(path))
        except FileNotFoundError:
            return default
        key = (row.st_mode, row.st_ino, row.st_size, row.st_mtime_ns)
        with self._monitor_lock:
            if self._monitor_key != key:
                value = self.read_json(path, MISSING)
                self._monitor_key, self._monitor_value = key, value
            value = self._monitor_value
        if value is MISSING:
            return default
        return json.loads(json.dumps(value)) if copy else value

    def native_digest(self):
        path = self.runtime / 'native-status.json'
        try:
            row = os.lstat(str(path))
        except FileNotFoundError:
            return None
        except OSError:
            return 'UNREADABLE'
        key = (row.st_mode, row.st_ino, row.st_size, row.st_mtime_ns)
        with self._native_lock:
            if key == self._native_key:
                return self._native_digest
            try:
                if not stat.S_ISREG(row.st_mode) or row.st_size > NATIVE_LIMIT:
                    digest = 'INVALID'
                else:
                    with open(str(path), 'rb') as stream:
                        value = json.loads(stream.read(NATIVE_LIMIT + 1))
                    if not isinstance(value, dict):
                        digest = 'INVALID'
                    else:
                        picked = {name: value.get(name) for name in NATIVE_STATE}
                        route = value.get('channel_path')
                        picked['channel_path'] = ({name: route.get(name) for name in PATH_STATE}
                                                  if isinstance(route, dict) else None)
                        digest = json.dumps(picked, sort_keys=True, default=repr)
            except (OSError, ValueError, RecursionError):
                digest = 'UNREADABLE'
            self._native_key, self._native_digest = key, digest
            return digest

    def signature(self):
        """Every control input of the answers; observation files are deliberately left out."""
        rows = []
        for directory in (self.runtime, self.persist):
            try:
                with os.scandir(str(directory)) as listing:
                    entries = sorted(listing, key=lambda entry: entry.name)
            except OSError:
                rows.append((str(directory), 'UNREADABLE'))
                continue
            for entry in entries:
                name = entry.name
                if (name.startswith('.') or name == NAME or name in SELF_WRITTEN or name in OBSERVATION
                        or name.endswith(('.lock', '.pending', '.tmp'))):
                    continue
                try:
                    row = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISDIR(row.st_mode):
                    continue
                rows.append((str(directory), name, row.st_mode, row.st_ino, row.st_size, row.st_mtime_ns))
        for path in self.configs:
            try:
                row = os.lstat(path)
                rows.append((path, row.st_mode, row.st_ino, row.st_size, row.st_mtime_ns))
            except OSError:
                rows.append((path, None))
        rows.append(('native-state', self.native_digest()))
        return tuple(rows)

    # ---- answers -----------------------------------------------------------------------------------
    def answer(self, method, request):
        """The reply bytes for one connection: OK + JSON line, or FALLBACK."""
        if method in self.writers:
            return self.write(method, request)
        if method not in METHODS or self._stopping():
            return FALLBACK
        try:
            if self.decode(request):
                return FALLBACK          # agent.py answers RPC-UNEXPECTED-ARGS exactly as before
        except ValueError:
            return FALLBACK              # and every request-format code
        if method == 'auto_live':
            try:
                started = self.clock()
                body = json.dumps(self.live(lambda default: self.load_monitor(default, copy=False))).encode('ascii')
            except Exception:
                return FALLBACK
            return OK + splice(body, self.clock() - started) + b'\n'
        arrived = self.clock()
        with self._cond:
            last = self._last_request.get(method)
            if last is not None and 1.0 <= arrived - last <= DEMAND_WINDOW:
                previous = self._period.get(method)
                interval = arrived - last
                self._period[method] = interval if previous is None else (previous + interval) / 2
            self._last_request[method] = arrived
        current = self.signature()
        deadline = arrived + WAIT_LIMIT
        with self._cond:
            while True:
                entry = self._entries.get(method)
                if entry is not None:
                    if entry.started >= arrived:
                        # Computed after this request arrived: as fresh as a per-call answer.
                        return FALLBACK if entry.error else OK + splice(entry.body, self.clock() - entry.started) + b'\n'
                    if (entry.error is None and entry.signature == current
                            and self.clock() - entry.started <= MAX_SERVE_AGE):
                        return OK + splice(entry.body, self.clock() - entry.started) + b'\n'
                if self._stopped.is_set() or not any(t.name == 'status-refresh' and t.is_alive() for t in self._threads):
                    return FALLBACK      # nobody would compute: answer through agent.py at once
                wanted = self._wanted.get(method)
                self._wanted[method] = arrived if wanted is None else min(wanted, arrived)
                self._cond.notify_all()
                remaining = deadline - self.clock()
                if remaining <= 0:
                    return FALLBACK
                self._cond.wait(remaining)

    def write(self, method, request):
        if self._stopping():
            return FALLBACK
        try:
            arguments = self.decode(request)
        except ValueError:
            return FALLBACK              # agent.py reports the request-format code
        if not isinstance(arguments, dict):
            return FALLBACK
        try:
            result = self.writers[method](arguments)
            body = json.dumps(result).encode('ascii')
            if not isinstance(result, dict):
                raise ValueError('reply')
        except Exception:
            body = json.dumps(WRITE_FAILED.get(method, WRITE_FAILED_DEFAULT)).encode('ascii')  # it may have acted: never twice
        return OK + body + b'\n'

    def compute(self, method):
        current = self.signature()
        started = self.clock()
        try:
            body = json.dumps(self.builders[method](self.load_monitor)).encode('ascii')
            error = None
        except Exception as problem:  # agent.py reproduces and reports it on the fallback path
            body, error = None, type(problem).__name__
        finished = self.clock()
        with self._cond:
            self._entries[method] = Entry(current, started, body, error)
            self._duration[method] = finished - started
            if method in self._wanted and self._wanted[method] <= started:
                del self._wanted[method]
            self._cond.notify_all()

    def _choose(self):
        with self._cond:
            if self._wanted:
                return min(self._wanted, key=self._wanted.get)
            if not self._last_request:
                return None
            now = self.clock()
            demanded = [m for m in CACHED if m in self._last_request and now - self._last_request[m] <= DEMAND_WINDOW]
        if not demanded:
            return None
        current = self.signature()
        now = self.clock()
        with self._cond:
            for method in demanded:
                entry = self._entries.get(method)
                if entry is None:
                    continue
                if now - entry.started < MIN_REFRESH:
                    continue
                if entry.signature != current:
                    return method        # a state change: recompute now, before the next poll asks
                period = self._period.get(method)
                if period is None:
                    continue             # a single poll so far: the next one computes on demand
                lead = min(5.0, max(1.0, 1.5 * self._duration.get(method, 1.0) + 0.5))
                window = self._last_request[method] + period - lead
                if now >= window and entry.started < window:
                    return method        # ready shortly before the expected next poll
        return None

    # ---- threads -----------------------------------------------------------------------------------
    def _refresh_loop(self):
        while not self._stopping():
            try:
                method = self._choose()
                if method is None:
                    with self._cond:
                        if not self._wanted and not self._stopped.is_set():
                            self._cond.wait(WATCH_SECONDS)
                    continue
                self.compute(method)
            except Exception:
                self._stopped.wait(WATCH_SECONDS)

    def _accept_loop(self):
        while not self._stopping():
            listener = self._listener
            if listener is None:
                return
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if self._stopped.wait(0.2):
                    return
                continue
            if not self._slots.acquire(blocking=False):
                connection.close()       # busy: the client runs agent.py
                continue
            try:
                threading.Thread(target=self._handle, args=(connection,), name='status-answer', daemon=True).start()
            except RuntimeError:
                connection.close()
                self._slots.release()

    def _handle(self, connection):
        try:
            connection.settimeout(IO_TIMEOUT)
            credentials = connection.getsockopt(socket.SOL_SOCKET, getattr(socket, 'SO_PEERCRED', 17),
                                                struct.calcsize('3i'))
            _, uid, _ = struct.unpack('3i', credentials)
            if uid != os.geteuid():
                return
            data = b''
            while len(data) <= REQUEST_LIMIT:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                data += chunk
            method, separator, request = data.partition(b'\n')
            if len(data) > REQUEST_LIMIT or not separator:
                reply = FALLBACK
            else:
                reply = self.answer(method.decode('ascii', 'replace'), request)
            connection.settimeout(30.0)
            connection.sendall(reply)
        except Exception:
            pass
        finally:
            try:
                connection.close()
            finally:
                self._slots.release()
