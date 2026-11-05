# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Probe authenticity: what makes a channel check an answer of the real endpoint for THIS request.

Twin: lua/probe_trust.lua (same rules, shared cases tests/probe_trust_cases.json). Design, threats and the pin
rotation path: docs/architecture/PROBE-AUTHENTICITY-2026-11-03.ru.md.

- Trust anchors: each fixed probe host (one.one.one.one, dns.google, dns.quad9.net) is verified against its own
  small set of root certificates (probe-anchors/<host>.pem, current + backup roots, all taken from the firmware's
  own ca-bundle), not against the whole system store: a certificate from any other CA - a captive portal, a DPI
  box, a mis-issuing or national CA - is untrusted. A missing anchor file falls back to the system store (the
  check of 2.1.0-alpha7), never to no verification.
- Request nonce: every HTTPS check sends `User-Agent: HomenSAI-probe/<32 hex>`; Cloudflare's /cdn-cgi/trace echoes
  it as `uag=`. A trace whose uag differs is a replayed or foreign page. A trace without uag is accepted only with
  `ts=` within FRESH_SECONDS of the router clock and no clock jump during the request.
- Reasons (per check `trust`, never a new verdict code): untrusted-certificate, portal-redirect, stale-response.
  The verdict stays VPN-003 (fewer than 2 valid answers); `probe_trust: untrusted` says that the failure was an
  authenticity failure.
"""
from pathlib import Path
import os
import re
import ssl

ANCHORS = Path(__file__).resolve().with_name('probe-anchors')
CONFIG = Path('/etc/config/homensai_vpn')
AGENT_PREFIX = 'HomenSAI-probe/'
FRESH_SECONDS = 60      # |trace ts - router time| allowed when the trace carries no uag echo
JUMP_SECONDS = 2        # wall clock moved this much more/less than the monotonic clock during the request
UNTRUSTED = 'untrusted-certificate'
REDIRECT = 'portal-redirect'
STALE = 'stale-response'
REASONS = (UNTRUSTED, REDIRECT, STALE)
DNS_OPTION = 'probe_dns'
# option probe_dns 'doh': the DNS check is an RFC 8484 query to dns.google over the tunnel (pinned TLS, the same
# random transaction id and question checks) instead of the plain UDP question to 9.9.9.9:53. Default 'udp'.
DOH_TARGET = ('8.8.8.8', 'dns.google', '/dns-query', 'dns-wire')
HOST = re.compile(r'^[a-z0-9.-]{1,64}$')
TS = re.compile(r'^[0-9]{1,12}(\.[0-9]{1,9})?$')
SECTION = re.compile(r'''^\s*config\s+\S+\s+["']?([A-Za-z0-9_]+)["']?\s*$''')
OPTION = re.compile(r'''^\s*option\s+'''+DNS_OPTION+r'''\s+["']?([^"'\s]*)["']?\s*$''')


def anchor_file(hostname):
    """The pinned root file of a probe host, or None (unknown host or file absent: the system store is used)."""
    if not isinstance(hostname, str) or not HOST.fullmatch(hostname) or '..' in hostname:
        return None
    path = ANCHORS/(hostname+'.pem')
    return str(path) if path.is_file() else None


def context(hostname):
    """Strict TLS for one probe host: certificate chain to the host's own anchors and the hostname checked."""
    cafile = anchor_file(hostname)
    return ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()


def agent(token=None):
    """The User-Agent with a fresh 128-bit nonce (token: 16 random bytes)."""
    token = os.urandom(16) if token is None else token
    return AGENT_PREFIX+token.hex()


def redirect(status):
    return type(status) is int and 300 <= status <= 399


def fresh(body, expected, wall_start, wall_end, elapsed):
    """None when a /cdn-cgi/trace body answers this very request, else the reason:
    nonce-mismatch (uag differs), no-freshness (neither uag nor one plain ts), clock-jump, stale-time."""
    text = body.decode('ascii', 'replace') if isinstance(body, bytes) else str(body)
    agents, stamps = [], []
    for line in text.split('\n'):
        if line.endswith('\r'):
            line = line[:-1]
        if line.startswith('uag='):
            agents.append(line[4:])
        elif line.startswith('ts='):
            stamps.append(line[3:])
    if agents:
        return None if all(value == expected for value in agents) else 'nonce-mismatch'
    if len(stamps) != 1 or not TS.fullmatch(stamps[0]):
        return 'no-freshness'
    if abs((wall_end-wall_start)-elapsed) > JUMP_SECONDS:
        return 'clock-jump'
    stamp = float(stamps[0])
    return None if wall_start-FRESH_SECONDS <= stamp <= wall_end+FRESH_SECONDS else 'stale-time'


def dns_mode(text):
    """'doh' when `option probe_dns 'doh'` is set in config main 'main' (the last value wins, as in uci), else 'udp'."""
    if not isinstance(text, str):
        return 'udp'
    section, found = None, None
    for line in text.split('\n'):
        match = SECTION.match(line)
        if re.match(r'^\s*config\s', line):
            section = match.group(1) if match else None
        elif section == 'main':
            value = OPTION.match(line)
            if value:
                found = value.group(1)
    return 'doh' if found == 'doh' else 'udp'


_MODE = {'key': None, 'value': 'udp'}


def current_dns_mode():
    """dns_mode() of the router configuration, re-read only when the file changed; unreadable = 'udp'."""
    try:
        status = CONFIG.stat()
        key = (status.st_mtime_ns, status.st_size, status.st_ino)
    except OSError:
        return 'udp'
    if key != _MODE['key']:
        try:
            value = dns_mode(CONFIG.read_text(encoding='utf-8', errors='replace'))
        except OSError:
            return 'udp'
        _MODE.update(key=key, value=value)
    return _MODE['value']


def untrusted(checks):
    """True when at least one check failed for an authenticity reason."""
    return any(isinstance(row, dict) and row.get('trust') in REASONS for row in checks or ())
