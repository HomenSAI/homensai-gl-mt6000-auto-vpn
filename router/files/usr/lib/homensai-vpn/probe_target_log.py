# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Per-target probe log: what each probe target answered, for the offline sensor-correlation study.

The monitor already computes one result per target in every pass (three HTTPS checks 1.1.1.1 / 8.8.8.8 / 9.9.9.9 with
their elapsed time, the UDP DNS check, the verdict) and, in the Lua monitor, the ICMP heartbeat counts its echoes per
target. Nothing recorded them, so the correlation between targets could not be measured
(private/math/sensor-correlation/REPORT.ru.html). This module writes them, nothing else: it measures NOTHING itself
(one source per reading: the numbers are the ones of the pass that decided the verdict).

Option probe_target_log (inventory.lua; default ON, '0' switches it off). Lua twin: lua/probe_target_log.lua, shared
cases router/tests/probe_target_log_cases.json. Design and numbers: docs/architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md.

File: RAM only (/var/run/homensai-vpn, tmpfs; never the flash), a ring of two append-only segments
probe-targets.log (current) and probe-targets.log.1 (previous), each at most SEGMENT bytes: 256 KiB in all. The
monitor is the only writer (one process, one thread); the RPC probe_targets and the soak kit only read.
One line per channel per pass, a JSON array of integers (and the profile id):

  [seq, t, "id", verdict, flags, [c1,l1, c2,l2, c3,l3], dns, [s1,m1, s2,m2, s3,m3, so,mo]]

  seq      1, 2, 3 ... continues after a monitor restart (read back from the ring); a smaller number than the reader's
           cursor means the router rebooted (the ring is gone): start again from 0
  t        probe time, whole seconds since the epoch
  verdict  0 ok, 1 DNS-001, 2 VPN-003, 3 VPN-001, 4 VPN-MTU, 5 ROUTE-001, 6 CHECK-001, 7 SYSTEM-001,
           8 VENDOR-IDENTITY-CHANGED, 9 any other code
  flags    bit 0: a dense confirmation pass
  c, l     result code and latency in whole ms of the HTTPS check of one.one.one.one, dns.google, dns.quad9.net
           (the order of TARGETS). Code: 0 ok, 1 timeout, 2 tls-error, 3 invalid-response, 4 transport-error,
           5 http-error, 6 http-unsupported, 7 unknown, 9 not measured in this pass; +10 when the answer was not
           authentic (portal redirect, foreign certificate, replayed page: probe_trust). Latency -1 = none
  dns      the UDP DNS check: 0 answered, 1 failed, 9 not measured (it has no latency of its own)
  s, m     ICMP heartbeat echoes sent and unanswered since the previous line of this channel, per target 1.1.1.1,
           8.8.8.8, 9.9.9.9 and all other pool targets together; [] when there is no heartbeat (the Python monitor has
           none; Lua with lua_fast_detect off)
"""
import math
import os
import re
import stat

OPTION = 'probe_target_log'
NAME = 'probe-targets.log'
SEGMENT = 128 * 1024             # bytes of one segment; the ring holds two
RING_BYTES = 2 * SEGMENT
FORMAT = 1
TARGETS = ('one.one.one.one', 'dns.google', 'dns.quad9.net')
HEARTBEAT_SLOTS = ('1.1.1.1', '8.8.8.8', '9.9.9.9')
RESULTS = {'ok': 0, 'timeout': 1, 'tls-error': 2, 'invalid-response': 3, 'transport-error': 4, 'http-error': 5,
           'http-unsupported': 6}
RESULT_UNKNOWN = 7
NOT_MEASURED = 9
UNTRUSTED = 10
TRUST_REASONS = ('untrusted-certificate', 'portal-redirect', 'stale-response')
VERDICTS = {'DNS-001': 1, 'VPN-003': 2, 'VPN-001': 3, 'VPN-MTU': 4, 'ROUTE-001': 5, 'CHECK-001': 6, 'SYSTEM-001': 7,
            'VENDOR-IDENTITY-CHANGED': 8}
VERDICT_OTHER = 9
MAX_MS = 600000
MAX_COUNT = 65535
MAX_STAMP = 999999999999
DEFAULT_ROWS = 200
MAX_ROWS = 1000
ID = re.compile(r'^[A-Za-z0-9_.:-]{1,64}$')
LINE = re.compile(r'^\[(\d{1,15}),(\d{1,12}),"([A-Za-z0-9_.:-]{1,64})",(\d{1,2}),(\d{1,3}),'
                  r'\[(\d{1,2},-?\d{1,6},\d{1,2},-?\d{1,6},\d{1,2},-?\d{1,6})\],(\d{1,2}),'
                  r'\[((?:\d{1,5}(?:,\d{1,5}){7})?)\]\]$', re.ASCII)


def enabled(settings):
    return isinstance(settings, dict) and settings.get(OPTION) is True


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def result_code(detail):
    """(code, latency ms) of one target's check detail {target, result, elapsed_ms, trust}; None = not measured."""
    if not isinstance(detail, dict):
        return NOT_MEASURED, -1
    result = detail.get('result')
    code = RESULTS.get(result, RESULT_UNKNOWN) if isinstance(result, str) else RESULT_UNKNOWN
    if detail.get('trust') in TRUST_REASONS:
        code += UNTRUSTED
    elapsed = _number(detail.get('elapsed_ms'))
    if elapsed is None:
        return code, -1
    return code, min(max(int(math.floor(elapsed + 0.5)), 0), MAX_MS)


def verdict_code(code):
    if code is None:
        return 0
    return VERDICTS.get(code, VERDICT_OTHER) if isinstance(code, str) else VERDICT_OTHER


def heartbeat_slot(target):
    return HEARTBEAT_SLOTS.index(target) if target in HEARTBEAT_SLOTS else len(HEARTBEAT_SLOTS)


def _heartbeat(hb):
    """The 8 counters, or the empty list: anything else than 8 integers 0..MAX_COUNT is no heartbeat data."""
    if isinstance(hb, (list, tuple)) and len(hb) == 8 and all(
            type(v) is int and 0 <= v <= MAX_COUNT for v in hb) and any(hb[0::2]):
        return list(hb)
    return []


def encode(seq, result, dense=False, hb=None, now=None):
    """One line (with the newline) for a probe result of the monitor, or None for a result that is no channel row."""
    if not isinstance(result, dict) or not isinstance(result.get('id'), str) or not ID.match(result['id']):
        return None
    stamp = _number(result.get('time'))
    if stamp is None:
        stamp = _number(now)
    if stamp is None or not 0 <= stamp <= MAX_STAMP:
        return None
    by_target = {}
    listed = result.get('probe_checks')
    for detail in listed if isinstance(listed, (list, tuple)) else ():
        if isinstance(detail, dict) and detail.get('target') in TARGETS:
            by_target[detail['target']] = detail
    checks = []
    for target in TARGETS:
        checks.extend(result_code(by_target.get(target)))
    dns = result.get('dns_ok')
    dns = 0 if dns is True else 1 if dns is False else NOT_MEASURED
    return '[%d,%d,"%s",%d,%d,[%s],%d,[%s]]\n' % (
        seq, int(math.floor(stamp)), result['id'], verdict_code(result.get('code')), 1 if dense else 0,
        ','.join(str(v) for v in checks), dns, ','.join(str(v) for v in _heartbeat(hb)))


def parse_line(line):
    """The row a line stands for (the JSON array), or None for anything that is not exactly a line of this format."""
    match = LINE.match(line)
    if not match:
        return None
    seq, stamp, ident, verdict, flags, checks, dns, hb = match.groups()
    return [int(seq), int(stamp), ident, int(verdict), int(flags), [int(v) for v in checks.split(',')], int(dns),
            [int(v) for v in hb.split(',')] if hb else []]


def complete_lines(text):
    """The complete lines of a segment: a last line without its newline is a torn write (or being written): dropped."""
    if not text:
        return []
    lines = text.split('\n')
    lines.pop()
    return lines


def last_seq(text):
    last = 0
    for line in complete_lines(text):
        row = parse_line(line)
        if row is not None:
            last = row[0]
    return last


def select(old, new, after=0, limit=DEFAULT_ROWS):
    """The reply of the RPC from the two segments (oldest first): rows with seq > after, at most limit."""
    rows = []
    first = last = 0
    more = False
    for text in (old, new):
        for line in complete_lines(text):
            row = parse_line(line)
            if row is None:
                continue
            if first == 0:
                first = row[0]
            last = row[0]
            if row[0] > after:
                if len(rows) < limit:
                    rows.append(row)
                else:
                    more = True
    return {'version': FORMAT, 'targets': list(TARGETS), 'heartbeat': list(HEARTBEAT_SLOTS) + ['other'],
            'first': first, 'last': last, 'count': len(rows), 'truncated': more, 'rows': rows}


def arguments(request):
    """(after, limit) from the RPC argument object. The refusals use the codes the page already explains: RPC-INPUT-OBJECT
    (not an object), RPC-UNEXPECTED-ARGS (another field), RPC-INPUT-INVALID (a value outside its form), all as ValueError."""
    if not isinstance(request, dict):
        raise ValueError('RPC-INPUT-OBJECT')
    if not set(request) <= {'after', 'limit'}:
        raise ValueError('RPC-UNEXPECTED-ARGS')
    after = request.get('after', 0)
    limit = request.get('limit', DEFAULT_ROWS)
    if (type(after) is not int or after < 0 or after > 10 ** 15
            or type(limit) is not int or not 1 <= limit <= MAX_ROWS):
        raise ValueError('RPC-INPUT-INVALID')
    return after, limit


def _read(path):
    """The text of a segment, '' when absent; a link or another non-file is refused (OSError)."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return ''
    if not stat.S_ISREG(info.st_mode) or info.st_size > SEGMENT * 2:
        raise OSError('probe target log: not a regular file or too large')
    with open(path, 'rb') as handle:
        return handle.read().decode('ascii', 'replace')


def read(directory, request=None):
    """The RPC probe_targets: read-only; works whichever monitor wrote the ring."""
    after, limit = arguments({} if request is None else request)
    directory = str(directory)
    return select(_read(directory + '/' + NAME + '.1'), _read(directory + '/' + NAME), after, limit)


class Writer:
    """The monitor's side: append the lines of a pass, rotate the ring. One instance, one thread."""

    def __init__(self, directory, segment=SEGMENT):
        self.path = str(directory) + '/' + NAME
        self.previous = self.path + '.1'
        self.segment = segment
        self.seq = None
        self.size = 0

    def _resume(self):
        current = _read(self.path)
        self.size = len(current)
        self.seq = last_seq(current) or last_seq(_read(self.previous))

    def record(self, results, hb=None, dense=False, now=None):
        """Append one line per result of this pass (hb: {profile id: 8 counters} of the heartbeat, or None).
        Returns the number of lines written. Raises OSError when the ring cannot be written: the caller goes on."""
        if self.seq is None:
            self._resume()
        lines = []
        seq = self.seq
        for result in results:
            line = encode(seq + 1, result, dense, (hb or {}).get(result.get('id')) if isinstance(result, dict) else None, now)
            if line is not None:
                seq += 1
                lines.append(line)
        if not lines:
            return 0
        data = ''.join(lines).encode('ascii')
        if self.size + len(data) > self.segment and self.size > 0:
            os.replace(self.path, self.previous)
            self.size = 0
        descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
                             | getattr(os, 'O_BINARY', 0), 0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError('probe target log: not a regular file')
            written = os.write(descriptor, data)
        finally:
            os.close(descriptor)
        if written != len(data):
            raise OSError('probe target log: short write')
        self.size += len(data)
        self.seq = seq
        return len(lines)
