#!/usr/bin/env python3
"""Build docs/TEST-HISTORY.html: every release and every measured test result in one self-contained page.

Python 3.9+, standard library only, offline. The output is deterministic: it depends only on the repository
(release notes, packages, CHANGELOG, git tag/commit dates) and on docs/test-history/results.json.

Privacy: text from release notes is sanitized, and a final scan refuses to write the page (exit code 2) when the
page or results.json contains an IPv4/IPv6 address, a MAC address, a VPN server host name, an e-mail address other
than info@homensai.com, an SSH key or fingerprint, or the words BEGIN, PRIVATE or token.

Usage:
  python3 scripts/build_test_history.py            # write docs/TEST-HISTORY.html
  python3 scripts/build_test_history.py --check    # fail when the committed page is out of date
"""
import argparse
import html
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCT = 'HomenS.AI Auto VPN'
AUTHOR = 'Serhii Khomenko | HomenS.AI'
LICENSE_LINE = 'HomenSAI Personal & Commercial Source License v1.0 — source-available, not open source'
CONTACT = 'info@homensai.com'
VERSION_RX = re.compile(r'(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)(\d+))?')
STAGES = {'alpha': 0, 'beta': 1, 'rc': 2, None: 3}
RESULT_KINDS = ('soak', 'lan-client', 'auto-switch', 'manual-switch', 'power-cut', 'benchmark', 'virtual',
                'acceptance', 'experiment', 'security', 'fault-sweep')
METRIC_ORDER = ('detect_s', 'decision_s', 'confirming_s', 'switch_itself_s', 'traffic_moved_s', 'total_to_reserve_s',
                'committed_s', 'manual_traffic_s', 'manual_done_s', 'lan_stall_s', 'lan_stall_all_events_s', 'dns_stall_s',
                'tcp_gap_s', 'new_exit_s', 'recover_s', 'on_reserve_s', 'vendor_blocked_s', 'return_s', 'boot_to_normal_s',
                'ssh_back_s')
STAT_KEYS = ('value', 'n', 'min', 'mean', 'median', 'p95', 'max')
MONTHS = {m: i + 1 for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                         'september', 'october', 'november', 'december'))}

# ---------------------------------------------------------------- privacy

_OCTET = r'(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)'
IPV4_RX = re.compile(r'(?<![\w.])' + r'\.'.join([_OCTET] * 4) + r'(?:/\d{1,2})?(?![\w.]*\d)')
IPV6_RX = re.compile(r'(?<![\w:])(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])|(?<![\w:])[0-9A-Fa-f]{0,4}::[0-9A-Fa-f]{1,4}\b')
MAC_RX = re.compile(r'\b[0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}\b')
EMAIL_RX = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
NORD_RX = re.compile(r'\b([a-z]{2})\d+\.nordvpn\.com\b', re.I)
LANHOST_RX = re.compile(r'\b[\w-]+\.(?:lan|local|home\.arpa|internal)\b', re.I)
SSHKEY_RX = re.compile(r'SHA256:[A-Za-z0-9+/]{43}|ssh-(?:rsa|ed25519|dss)\s+AAAA|ecdsa-sha2-nistp\d+\s+AAAA')
WORD_RX = re.compile(r'BEGIN|PRIVATE|token', re.I)
NORD_CITY = {'de': 'NordVPN Berlin server', 'ua': 'NordVPN Kyiv server'}


def _ipv6_like(m):
    s = m.group(0)
    if '::' in s:
        return bool(re.search(r'[0-9A-Fa-f]', s.replace('::', '')))
    groups = s.split(':')
    return len(groups) >= 5 or (len(groups) >= 3 and re.search(r'[A-Fa-f]', s) is not None)


def privacy_findings(text):
    """Return a sorted list of (kind, match) that must never be published."""
    found = set()
    for m in IPV4_RX.finditer(text):
        found.add(('ipv4', m.group(0)))
    for m in IPV6_RX.finditer(text):
        if _ipv6_like(m):
            found.add(('ipv6', m.group(0)))
    for m in MAC_RX.finditer(text):
        found.add(('mac', m.group(0)))
    for m in EMAIL_RX.finditer(text):
        if m.group(0).lower() != CONTACT:
            found.add(('email', m.group(0)))
    for rx, kind in ((NORD_RX, 'vpn-host'), (LANHOST_RX, 'lan-host'), (SSHKEY_RX, 'ssh-key')):
        for m in rx.finditer(text):
            found.add((kind, m.group(0)))
    for m in re.finditer(r'BEGIN|PRIVATE', text):
        found.add(('word', m.group(0)))
    for m in re.finditer(r'token', text, re.I):
        found.add(('word', m.group(0)))
    for m in re.finditer(r'\bMIT\b', text):
        found.add(('license', m.group(0)))
    return sorted(found)


def sanitize(text):
    """Make free text from release notes publishable; the final scan still checks the result."""
    text = NORD_RX.sub(lambda m: NORD_CITY.get(m.group(1).lower(), 'NordVPN server'), text)
    text = EMAIL_RX.sub(lambda m: m.group(0) if m.group(0).lower() == CONTACT else '[e-mail]', text)
    text = IPV4_RX.sub('[address]', text)
    text = IPV6_RX.sub(lambda m: '[address]' if _ipv6_like(m) else m.group(0), text)
    text = MAC_RX.sub('[mac]', text)
    text = LANHOST_RX.sub('[host]', text)
    text = SSHKEY_RX.sub('[key]', text)
    text = re.sub(r'\btokens\b', 'keys', text, flags=re.I)
    text = re.sub(r'token', 'key', text, flags=re.I)
    text = text.replace('BEGIN', 'Begin').replace('PRIVATE', 'Private')
    # the old license name is not repeated here; only the current license is named on the page
    text = ' '.join(s for s in re.split(r'(?<=[.!?])\s+', text) if not re.search(r'\bMIT\b', s))
    return text


# ---------------------------------------------------------------- versions

def vkey(v):
    m = VERSION_RX.fullmatch(v)
    if not m:
        return (999, 0, 0, 9, 0, v)
    a, b, c, st, n = m.groups()
    return (int(a), int(b), int(c), STAGES[st], int(n or 0), v)


def git(*args):
    try:
        out = subprocess.run(['git', '-C', str(ROOT)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=120, check=False)
    except (OSError, subprocess.SubprocessError):
        return ''
    return out.stdout.decode('utf-8', 'replace') if out.returncode == 0 else ''


def git_dates():
    tags = {}
    for line in git('for-each-ref', 'refs/tags', '--format=%(refname:short)|%(creatordate:short)').splitlines():
        name, _, date = line.partition('|')
        if name.startswith('v') and VERSION_RX.fullmatch(name[1:]):
            tags[name[1:]] = date
    added = {}
    date = None
    for line in git('log', '--diff-filter=A', '--format=@%cs', '--name-only', '--', 'releases').splitlines():
        if line.startswith('@'):
            date = line[1:]
        elif line.strip() and date:
            name = line.strip().split('/')[-1]
            if name not in added or date < added[name]:
                added[name] = date
    return tags, added


def strip_md(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'https?://\S+', '', s)
    s = s.replace('**', '').replace('`', '')
    return re.sub(r'\s+', ' ', s).strip()


def english_part(text):
    """The English part of a bilingual note: the '## English' section when present, else the text before Russian."""
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    lines = [l for l in text.splitlines() if not l.startswith('>')]
    for i, l in enumerate(lines):
        if re.match(r'#+\s*English\b', l):
            out = []
            for x in lines[i + 1:]:
                if re.match(r'#+\s*(Русский|Russian)', x):
                    break
                out.append(x)
            return out
    out = []
    for l in lines:
        if l.strip() == '---' or re.match(r'\*\*(Что|Изменения|Ядро)', l.strip()) or re.match(r'#+\s*(Русский|Изменения)', l):
            break
        out.append(l)
    if not any(x.strip() and not x.startswith('#') for x in out):
        return lines
    return out


SKIP_HEAD = re.compile(r'verification|limits|install|sha|license|checks|evidence|how long|measured|known|not proven', re.I)


def summarize(text, limit=900):
    """Intro paragraph plus the first bullets of the 'Changes since' list, as plain text."""
    lines = english_part(text)
    paras, cur = [], []
    for l in lines:
        if l.startswith('#'):
            if cur:
                paras.append(cur)
            cur = []
            # the document title (level 1) is not a section heading
            paras.append(['#' + ('' if l.startswith('# ') else l.lstrip('#').strip())])
            continue
        if not l.strip():
            if cur:
                paras.append(cur)
            cur = []
            continue
        cur.append(l)
    if cur:
        paras.append(cur)
    intro, bullets, heading, in_changes = '', [], '', False
    for p in paras:
        head = p[0].strip()
        if head.startswith('#'):
            heading = head
            in_changes = bool(re.search(r'chang|new|since|what', head, re.I))
            continue
        if head.startswith('|'):
            continue
        if re.match(r'\*\*(Runtime|License|Install|SHA|Ядро|Лиценз)', head) or head.startswith('SHA256'):
            continue
        if re.match(r'\*\*[^*]*(Changes|since|new)[^*]*\*\*', head, re.I):
            in_changes = True
            p = p[1:]
            if not p:
                continue
        skip = bool(SKIP_HEAD.search(heading)) and not in_changes
        items = [x for x in p if re.match(r'\s*[-*]\s+', x)]
        if items:
            if not skip and (in_changes or not bullets):
                for x in items:
                    if not re.match(r'\s{2,}', x):
                        bullets.append(strip_md(re.sub(r'^\s*[-*]\s+', '', x)))
            continue
        if not intro and not skip:
            intro = strip_md(' '.join(p))
    summary = intro
    if bullets:
        summary = (summary + ' ' if summary else '') + ' • '.join(bullets[:6])
    summary = sanitize(summary)
    if len(summary) > limit:
        cut = summary[:limit].rsplit(' ', 1)[0]
        summary = cut + ' …'
    return summary


def measured_lines(text, limit=3):
    lines = english_part(text)
    body = strip_md(' '.join(l for l in lines if not l.startswith('#')))
    out = []
    for s in re.split(r'(?<=[.!?])\s+', body):
        if re.search(r'\b(measured|on the router|on the MT3000|GL-MT3000|router check|soak)\b', s, re.I) and re.search(r'\d', s):
            s = sanitize(re.sub(r'^[-*\s]+', '', s.strip()))
            if s and s not in out and len(s) < 400:
                out.append(s)
        if len(out) >= limit:
            break
    return out


def changelog_sections():
    path = ROOT / 'CHANGELOG.md'
    if not path.exists():
        return {}
    secs, cur, body = {}, None, []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            if cur:
                secs.setdefault(cur[0], (cur[1], '\n'.join(body)))
            m = re.match(r'##\s+v?(' + VERSION_RX.pattern + r')(?![\d.])', line)
            cur, body = None, []
            if m:
                v = m.group(1)
                date = ''
                d = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                if d:
                    date = d.group(1)
                else:
                    d = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', line) or None
                    if d:
                        date = '%s-%02d-%02d' % (d.group(3), int(d.group(2)), int(d.group(1)))
                    else:
                        d = re.search(r'(\d{1,2})\s*([A-Za-z]+)\s*(\d{4})', line)
                        if d and d.group(2).lower() in MONTHS:
                            date = '%s-%02d-%02d' % (d.group(3), MONTHS[d.group(2).lower()], int(d.group(1)))
                title = line.split('—', 1)[1].strip() if '—' in line else ''
                if re.fullmatch(r'[\d.\s/-]*|[\d\s]*[A-Za-z]+\s*\d{4}.*', title):
                    title = ''
                cur = (v, (date, title))
            continue
        if cur:
            body.append(line)
    if cur:
        secs.setdefault(cur[0], (cur[1], '\n'.join(body)))
    return secs


def collect_versions():
    rel = ROOT / 'releases'
    tags, added = git_dates()
    clog = changelog_sections()
    versions = set(tags) | set(clog)
    notes, pkgs = {}, {}
    for p in sorted(rel.glob('*.md')):
        m = re.fullmatch(r'(?:notes-)?v(.+)\.md', p.name)
        if m and VERSION_RX.fullmatch(m.group(1)):
            v = m.group(1)
            versions.add(v)
            if not p.name.startswith('notes-') or v not in notes:
                notes[v] = p
    for p in sorted(rel.glob('homensai-auto-vpn_*_all.ipk')):
        m = re.fullmatch(r'homensai-auto-vpn_(.+)-(\d+)_all\.ipk', p.name)
        if m and VERSION_RX.fullmatch(m.group(1)):
            v, revision = m.group(1), int(m.group(2))
            versions.add(v)
            if v not in pkgs or revision > pkgs[v][1]:
                pkgs[v] = (p, revision)
    app = json.loads((ROOT / 'VERSION.json').read_text(encoding='utf-8'))['application']['version']
    versions.add(app)
    out = []
    for v in sorted(versions, key=vkey):
        e = {'version': v, 'date': '', 'title': '', 'summary': '', 'measured': [], 'package': None,
             'note_file': '', 'tagged': v in tags}
        if v in notes:
            text = notes[v].read_text(encoding='utf-8')
            e['note_file'] = 'releases/' + notes[v].name
            first = next((l for l in text.splitlines() if l.startswith('# ')), '')
            t = re.sub(r'^#\s*', '', first)
            t = re.sub(r'^(HomenS\.AI\s+)?(Auto VPN\s+)?v?' + re.escape(v) + r'\s*', '', t).strip(' —-:()')
            e['title'] = sanitize(strip_md(t))
            e['summary'] = summarize(text)
            e['measured'] = measured_lines(text)
        elif v in clog:
            e['title'] = sanitize(strip_md(clog[v][0][1]))
            e['summary'] = summarize(clog[v][1])
            e['note_file'] = 'CHANGELOG.md'
        if v in pkgs:
            p, revision = pkgs[v]
            sha = ''
            sp = p.with_name(p.name + '.sha256')
            if sp.exists():
                sha = sp.read_text(encoding='utf-8').split()[0] if sp.read_text(encoding='utf-8').split() else ''
            e['package'] = {'file': p.name, 'size': p.stat().st_size, 'sha256': sha}
        e['date'] = (tags.get(v) or (added.get(notes[v].name) if v in notes else '') or
                     (added.get(pkgs[v][0].name) if v in pkgs else '') or (clog[v][0][0] if v in clog else ''))
        out.append(e)
    return out, app


# ---------------------------------------------------------------- results

def validate_results(data):
    """Raise ValueError with every schema problem found."""
    errs = []
    if data.get('schema') != 1:
        errs.append('schema must be 1')
    for key in ('results', 'matrix', 'issues', 'features'):
        if not isinstance(data.get(key), list):
            errs.append('%s must be a list' % key)
    ids = set()
    for i, r in enumerate(data.get('results') or []):
        where = 'results[%d]' % i
        for f, t in (('id', str), ('run', str), ('run_label', str), ('date', str), ('version', str), ('kind', str),
                     ('scenario', str), ('platform', str), ('note', str), ('source', str), ('metrics', dict)):
            if not isinstance(r.get(f), t):
                errs.append('%s.%s must be %s' % (where, f, t.__name__))
        if r.get('id') in ids:
            errs.append('%s: duplicate id %s' % (where, r.get('id')))
        ids.add(r.get('id'))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(r.get('date'))):
            errs.append('%s.date must be YYYY-MM-DD' % where)
        if not VERSION_RX.fullmatch(str(r.get('version'))):
            errs.append('%s.version is not a version' % where)
        if r.get('kind') not in RESULT_KINDS:
            errs.append('%s.kind %r unknown' % (where, r.get('kind')))
        for f in ('n', 'passed', 'failed'):
            if not isinstance(r.get(f), int) or isinstance(r.get(f), bool) or r.get(f) < 0:
                errs.append('%s.%s must be a non-negative integer' % (where, f))
        if r.get('pass') not in (True, False, None):
            errs.append('%s.pass must be true, false or null' % where)
        if r.get('leaks') is not None and (not isinstance(r.get('leaks'), int) or isinstance(r.get('leaks'), bool)):
            errs.append('%s.leaks must be an integer or null' % where)
        for name, m in (r.get('metrics') or {}).items():
            if not re.fullmatch(r'[a-z0-9_]+', name) or not isinstance(m, dict) or not m:
                errs.append('%s.metrics.%s is malformed' % (where, name))
                continue
            for k, v in m.items():
                if k not in STAT_KEYS or not isinstance(v, (int, float)) or isinstance(v, bool):
                    errs.append('%s.metrics.%s.%s is not a number' % (where, name, k))
    for i, m in enumerate(data.get('matrix') or []):
        if not isinstance(m.get('phase'), int) or not isinstance(m.get('percent'), int) or not 0 <= m.get('percent') <= 100:
            errs.append('matrix[%d] needs integer phase and percent 0-100' % i)
        for f in ('title_ru', 'title_en', 'status', 'note'):
            if not isinstance(m.get(f), str):
                errs.append('matrix[%d].%s must be text' % (i, f))
    for i, m in enumerate(data.get('issues') or []):
        for f in ('id', 'title_ru', 'title_en', 'evidence', 'idea', 'status'):
            if not isinstance(m.get(f), str):
                errs.append('issues[%d].%s must be text' % (i, f))
    for i, m in enumerate(data.get('features') or []):
        for f in ('version', 'ru', 'en'):
            if not isinstance(m.get(f), str):
                errs.append('features[%d].%s must be text' % (i, f))
    errs += validate_charts(data.get('charts'))
    if errs:
        raise ValueError('\n'.join(errs))


def fmt_num(x):
    if isinstance(x, float):
        s = ('%.2f' % x).rstrip('0').rstrip('.')
        return s
    return str(x)


def fmt_metric(m):
    if 'value' in m:
        return fmt_num(m['value'])
    if 'median' in m and m.get('n') == 1:
        return fmt_num(m['median'])
    if 'median' in m and 'n' in m:
        s = '%s / %s / %s / %s' % (m['n'], fmt_num(m['median']), fmt_num(m.get('p95', m['median'])), fmt_num(m.get('max', m['median'])))
        return s
    parts = []
    if 'min' in m and 'max' in m:
        parts.append('%s–%s' % (fmt_num(m['min']), fmt_num(m['max'])))
    if 'mean' in m:
        parts.append('mean %s' % fmt_num(m['mean']))
    if 'median' in m:
        parts.append('median %s' % fmt_num(m['median']))
    return ', '.join(parts) or '—'


def unit_of(name, units):
    for suf, u in sorted(units.items(), key=lambda kv: -len(kv[0])):
        if name.endswith(suf):
            return u
    return ''


# ---------------------------------------------------------------- HTML

E = html.escape

CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#16202a;--muted:#5b6773;--line:#dde3ea;--accent:#0b6e8a;--accent2:#e8f4f8;
--ok:#1d7a3e;--okbg:#e6f4ea;--bad:#b3261e;--badbg:#fbe9e7;--na:#6b6b6b;--nabg:#eeeeee;--bar:#0b6e8a}
@media (prefers-color-scheme:dark){:root{--bg:#0f1418;--card:#161d23;--ink:#e6edf3;--muted:#9aa7b3;--line:#2a343d;
--accent:#5cc3df;--accent2:#14303a;--ok:#6fd08c;--okbg:#14301e;--bad:#ff8a80;--badbg:#3a1714;--na:#b0b0b0;--nabg:#262b30;--bar:#5cc3df}}
*{box-sizing:border-box}
body{margin:0;overflow-wrap:anywhere;background:var(--bg);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header,main,footer{max-width:1100px;margin:0 auto;padding:16px}
header{border-bottom:1px solid var(--line)}
h1{font-size:1.5rem;margin:.2rem 0}h2{font-size:1.2rem;margin:2rem 0 .6rem;padding-top:.4rem;border-top:2px solid var(--accent)}
h3{font-size:1rem;margin:.2rem 0}
.attr{color:var(--muted);font-size:.9rem;display:flex;flex-wrap:wrap;gap:.3rem 1rem}
.attr b{color:var(--ink)}
nav{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.6rem}
nav a{color:var(--accent);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:.15rem .7rem;font-size:.85rem;background:var(--card)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.6rem}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.6rem .8rem}
.stat .v{font-size:1.4rem;font-weight:600}.stat .l{color:var(--muted);font-size:.8rem}
.tools{display:flex;flex-wrap:wrap;gap:.5rem;margin:.5rem 0}
input,select{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.35rem .6rem;min-width:0}
input[type=search]{flex:1 1 220px}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:.4rem 0;padding:.2rem .8rem}
summary{cursor:pointer;padding:.35rem 0;list-style-position:outside}
summary .ver{font-weight:600}summary .date,.muted{color:var(--muted);font-size:.85rem}
.pkg{font-family:ui-monospace,Consolas,monospace;font-size:.78rem;color:var(--muted);word-break:break-all}
.tbl{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.86rem;margin:.3rem 0 .6rem}
th,td{border-bottom:1px solid var(--line);padding:.3rem .4rem;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;white-space:nowrap}
td.num{white-space:nowrap;font-variant-numeric:tabular-nums}
.b{display:inline-block;border-radius:999px;padding:0 .5rem;font-size:.78rem;font-weight:600;white-space:nowrap}
.b.ok{color:var(--ok);background:var(--okbg)}.b.bad{color:var(--bad);background:var(--badbg)}.b.na{color:var(--na);background:var(--nabg)}
.prog{background:var(--nabg);border-radius:6px;height:.6rem;min-width:80px;overflow:hidden}
.prog i{display:block;height:100%;background:var(--bar)}
ul.feat{padding-left:1.1rem}ul.feat li{margin:.15rem 0}
.tag{font-family:ui-monospace,Consolas,monospace;font-size:.82rem;background:var(--accent2);border-radius:5px;padding:0 .3rem}
.hidden{display:none}
footer{color:var(--muted);font-size:.85rem;border-top:1px solid var(--line);margin-top:2rem}
@media (max-width:600px){body{font-size:14px}header,main,footer{padding:12px 16px}h1{font-size:1.25rem}}
.chart{margin:.8rem 0 1.4rem;max-width:100%;min-width:0}.chart-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}
.chart-scroll svg{display:block;width:100%;min-width:620px;height:auto}
.chart-table{margin-top:.3rem}
@media print{nav,.tools{display:none}details{break-inside:avoid}}
"""

JS = """
(function(){
function norm(s){return (s||'').toLowerCase();}
function bind(inputId,selectId,itemSel){
  var q=document.getElementById(inputId),f=selectId?document.getElementById(selectId):null;
  var items=document.querySelectorAll(itemSel);
  function run(){
    var t=norm(q.value).trim(),g=f?f.value:'',shown=0;
    for(var i=0;i<items.length;i++){
      var el=items[i],ok=(!t||norm(el.textContent).indexOf(t)>=0)&&(!g||(' '+el.getAttribute('data-group')+' ').indexOf(' '+g+' ')>=0);
      el.classList.toggle('hidden',!ok);if(ok)shown++;
    }
    var c=document.getElementById(inputId+'-count');if(c)c.textContent=shown;
  }
  q.addEventListener('input',run);if(f)f.addEventListener('change',run);run();
}
bind('vq','vf','#versions .ver-item');
bind('rq','rf','#results .run-item');
})();
"""


def badge(r):
    if r.get('pass') is True:
        return '<span class="b ok">PASS</span>'
    if r.get('pass') is False:
        return '<span class="b bad">FAIL</span>'
    return '<span class="b na">INFO</span>'


def line_of(v):
    m = VERSION_RX.fullmatch(v)
    return '%s.%s' % (m.group(1), m.group(2)) if m else 'other'


def render(versions, app_version, data):
    labels = data.get('metric_labels') or {}
    units = data.get('metric_units') or {}
    results = sorted(data['results'], key=lambda r: (r['date'], vkey(r['version']), r['id']))
    runs = {}
    for r in results:
        runs.setdefault(r['run'] + '|' + r['version'], []).append(r)
    run_order = sorted(runs, key=lambda k: (runs[k][0]['date'], vkey(runs[k][0]['version']), k))
    total_cycles = sum(r['n'] for r in results)
    passed = sum(1 for r in results if r['pass'] is True)
    failed = sum(1 for r in results if r['pass'] is False)
    first, last = versions[0], versions[-1]
    as_of = max([v['date'] for v in versions if v['date']] + [r['date'] for r in results])
    o = []
    w = o.append
    w('<!doctype html><html lang="ru"><head><meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width,initial-scale=1">')
    w('<meta name="color-scheme" content="light dark">')
    w('<meta name="author" content="%s">' % E(AUTHOR))
    w('<title>%s — Test history</title>' % E(PRODUCT))
    w('<style>%s</style></head><body>' % CSS)
    w('<header><h1>%s — история версий и испытаний / Version and test history</h1>' % E(PRODUCT))
    w('<div class="attr"><span><b>%s</b></span><span>Автор / Author: <b>%s</b></span><span>Версия / Version: <b>%s</b></span>'
      '<span>Данные по / Data as of: <b>%s</b></span></div>' % (E(PRODUCT), E(AUTHOR), E(app_version), E(as_of)))
    w('<div class="attr"><span>Лицензия / License: %s</span><span>Contact: %s</span></div>' % (E(LICENSE_LINE), E(CONTACT)))
    w('<nav><a href="#overview">Обзор / Overview</a><a href="#features">Новые функции / Features</a>'
      '<a href="#charts">Графики / Charts</a><a href="#versions">Версии / Versions</a><a href="#results">Результаты / Results</a>'
      '<a href="#matrix">Матрица / Test matrix</a><a href="#issues">Открытые вопросы / Open issues</a>'
      '<a href="#method">Методика / Method</a></nav></header><main>')

    # overview
    w('<section id="overview"><h2>Обзор / Overview</h2><div class="stats">')
    for val, lab in ((len(versions), 'версий / versions (%s → %s)' % (first['version'], last['version'])),
                     (len(results), 'записей результатов / result records'),
                     (len(runs), 'прогонов / test runs'),
                     (total_cycles, 'циклов и замеров / cycles and samples'),
                     (passed, 'PASS'), (failed, 'FAIL (сохранены / kept as evidence)')):
        w('<div class="stat"><div class="v">%s</div><div class="l">%s</div></div>' % (E(str(val)), E(lab)))
    w('</div><p class="muted">Все измерения выполнены на выделенном тестовом роутере GL.iNet GL-MT3000, если не указано иное '
      '(виртуальная OpenWrt или Docker отмечены отдельно). Неуспешные результаты не удаляются. / All measurements come from the '
      'dedicated GL.iNet GL-MT3000 test router unless marked otherwise (virtual OpenWrt and Docker runs are marked). Failed results '
      'are kept.</p></section>')

    # charts
    w('<section id="charts"><h2>Как ускорялось переключение / How switching got faster</h2>')
    w('<p class="muted">Только измеренные значения: пропуск \u2014 в этой версии такой замер не делался. Маркер \u2014 медиана '
      '(или среднее, или один прогон), усы \u2014 P95 или min\u2013max. Наведите или сфокусируйте точку, чтобы увидеть '
      'число и источник. Полый маркер \u2014 стенд или виртуальная машина, сплошной \u2014 роутер GL-MT3000. / Measured values '
      'only: a gap means the version was not measured that way. Marker = median (or mean, or one run), whisker = P95 or '
      'min\u2013max. Hover or focus a point for the number and source. Hollow marker = lab/virtual, filled = GL-MT3000 router.</p>')
    for c in data['charts']:
        w('<figure class="chart"><div class="chart-scroll">%s</div>%s</figure>' % (chart_svg(c), chart_table(c)))
    w('</section>')

    # features
    w('<section id="features"><h2>Новые функции по версиям / New features by version</h2><ul class="feat">')
    for f in sorted(data['features'], key=lambda f: vkey(f['version'])):
        w('<li><span class="tag">%s</span> %s <span class="muted">/ %s</span></li>' % (E(f['version']), E(sanitize(f['ru'])), E(sanitize(f['en']))))
    w('</ul></section>')

    # versions
    lines = sorted({line_of(v['version']) for v in versions}, key=lambda s: tuple(int(x) for x in s.split('.')) if s != 'other' else (999,))
    w('<section id="versions"><h2>Все версии, от первой до текущей / Every version, first to current</h2>')
    w('<div class="tools"><input type="search" id="vq" placeholder="Поиск / Search" aria-label="Search versions">'
      '<select id="vf" aria-label="Release line"><option value="">Все линии / All lines</option>%s</select>'
      '<span class="muted">показано / shown: <span id="vq-count">%d</span></span></div>' % (
          ''.join('<option value="%s">%s.x</option>' % (E(l), E(l)) for l in lines), len(versions)))
    for v in versions:
        w('<details class="ver-item" data-group="%s"><summary><span class="ver">%s</span> <span class="date">%s</span> %s</summary>' % (
            E(line_of(v['version'])), E(v['version']), E(v['date'] or 'date unknown'), E(v['title'])))
        if v['summary']:
            w('<p>%s</p>' % E(v['summary']))
        else:
            w('<p class="muted">Нет описания в репозитории (только пакет или тег). / No notes in the repository (package or tag only).</p>')
        if v['measured']:
            w('<p class="muted"><b>Проверено / Checked:</b> %s</p>' % E(' '.join(v['measured'])))
        if v['package']:
            p = v['package']
            w('<p class="pkg">%s · %s bytes · SHA256 %s</p>' % (E(p['file']), '{:,}'.format(p['size']), E(p['sha256'] or 'n/a')))
        if v['note_file']:
            w('<p class="muted">Source: %s</p>' % E(v['note_file']))
        w('</details>')
    w('</section>')

    # results
    kinds = sorted({r['kind'] for r in results})
    w('<section id="results"><h2>Результаты испытаний на роутере / Router test results</h2>')
    w('<p class="muted">Ячейки вида <b>n / медиана / P95 / max</b> — распределение по циклам; одно число — один замер; '
      '«–» — диапазон. Время в секундах от начала сбоя или нажатия. / Cells <b>n / median / P95 / max</b> are a '
      'distribution over cycles; one number is one sample; a dash range is min–max. Times are seconds from the fault start or the click.</p>')
    w('<div class="tools"><input type="search" id="rq" placeholder="Поиск: версия, сбой… / Search: version, fault…" aria-label="Search results">'
      '<select id="rf" aria-label="Kind"><option value="">Все виды / All kinds</option>%s</select>'
      '<span class="muted">прогонов показано / runs shown: <span id="rq-count">%d</span></span></div>' % (
          ''.join('<option value="%s">%s</option>' % (E(k), E(k)) for k in kinds), len(runs)))
    for key in run_order:
        rs = runs[key]
        r0 = rs[0]
        n = sum(r['n'] for r in rs)
        ok = sum(r['passed'] for r in rs)
        bad = [r for r in rs if r['pass'] is False]
        status = '<span class="b bad">FAIL %d</span>' % len(bad) if bad else ('<span class="b ok">PASS</span>' if any(r['pass'] for r in rs) else '<span class="b na">INFO</span>')
        w('<details class="run-item" data-group="%s"><summary>%s <span class="ver">%s</span> <span class="date">%s · %s</span> '
          '%s <span class="muted">(%d/%d)</span></summary>' % (
              E(' '.join(sorted({r['kind'] for r in rs}))), status, E(r0['version']), E(r0['date']), E(r0['platform']),
              E(sanitize(r0['run_label'])), ok, n))
        mnames = sorted({k for r in rs for k in r['metrics']},
                        key=lambda k: (METRIC_ORDER.index(k) if k in METRIC_ORDER else len(METRIC_ORDER), k))
        w('<div class="tbl"><table><thead><tr><th>Сценарий / Scenario</th><th>n</th><th>OK</th><th>Итог</th>')
        for k in mnames:
            lab = labels.get(k, [k, k])
            u = unit_of(k, units)
            w('<th title="%s">%s / %s%s</th>' % (E(k), E(lab[0]), E(lab[1]), (', ' + E(u)) if u else ''))
        w('<th>Утечки / Leaks</th><th>Примечание / Note</th></tr></thead><tbody>')
        for r in rs:
            w('<tr><td>%s</td><td class="num">%d</td><td class="num">%d</td><td>%s</td>' % (E(sanitize(r['scenario'])), r['n'], r['passed'], badge(r)))
            for k in mnames:
                w('<td class="num">%s</td>' % (E(fmt_metric(r['metrics'][k])) if k in r['metrics'] else '—'))
            w('<td class="num">%s</td><td>%s<br><span class="muted">%s</span></td></tr>' % (
                '—' if r['leaks'] is None else r['leaks'], E(sanitize(r['note'])), E(sanitize(r['source']))))
        w('</tbody></table></div></details>')
    w('</section>')

    # matrix
    w('<section id="matrix"><h2>Матрица испытаний: фазы 0–9 / Test matrix: phases 0–9</h2>')
    w('<div class="tbl"><table><thead><tr><th>Фаза</th><th>Что / What</th><th>%</th><th>Статус / Status</th><th>Комментарий / Note</th></tr></thead><tbody>')
    for m in sorted(data['matrix'], key=lambda m: m['phase']):
        w('<tr><td class="num">%d</td><td>%s<br><span class="muted">%s</span></td><td><div class="prog" role="img" aria-label="%d%%"><i style="width:%d%%"></i></div>%d%%</td>'
          '<td>%s</td><td>%s</td></tr>' % (m['phase'], E(sanitize(m['title_ru'])), E(sanitize(m['title_en'])), m['percent'], m['percent'],
                                          m['percent'], E(m['status']), E(sanitize(m['note']))))
    total = sum(m['percent'] for m in data['matrix']) / max(1, len(data['matrix']))
    w('</tbody></table></div><p class="muted">Среднее по фазам / Mean over phases: %d%%</p></section>' % round(total))

    # issues
    w('<section id="issues"><h2>Открытые вопросы и идеи улучшений / Open issues and improvement candidates</h2>')
    w('<div class="tbl"><table><thead><tr><th>ID</th><th>Вопрос / Issue</th><th>Наблюдение / Evidence</th><th>Идея / Idea</th><th>Статус / Status</th></tr></thead><tbody>')
    for m in data['issues']:
        st = m['status']
        cls = 'ok' if st == 'resolved' else 'bad' if st == 'open' else 'na'
        w('<tr><td>%s</td><td>%s<br><span class="muted">%s</span></td><td>%s</td><td>%s</td><td><span class="b %s">%s</span></td></tr>' % (
            E(m['id']), E(sanitize(m['title_ru'])), E(sanitize(m['title_en'])), E(sanitize(m['evidence'])), E(sanitize(m['idea'])), cls, E(st)))
    w('</tbody></table></div></section>')

    # method
    w('<section id="method"><h2>Методика и обозначения / Method and terms</h2><ul class="feat">')
    for k in sorted(labels):
        u = unit_of(k, units)
        w('<li><span class="tag">%s</span> %s / %s%s</li>' % (E(k), E(labels[k][0]), E(labels[k][1]), (' (' + E(u) + ')') if u else ''))
    w('</ul><p class="muted">Soak: роутер сам вносит сбой (блок трафика туннеля, netem, остановка процесса, sysrq-b) и снимает его; '
      'отчёт считает время по журналу состояний Auto. LAN client: тестовый клиент в отдельном сетевом пространстве на LAN роутера '
      'считает простой HTTP/DNS, старые TCP/UDP потоки и пакеты мимо VPN. / Soak: the router injects a fault (tunnel traffic block, '
      'netem, process stop, sysrq-b) and removes it; timings come from the Auto state timeline. LAN client: a test client in its own '
      'network namespace on the router LAN measures HTTP/DNS stalls, old TCP/UDP flows and packets that bypass the VPN.</p>'
      '<p class="muted">Приватность: адреса, имена серверов и узлов, ключи и сырые журналы не публикуются; страница проверяется сканером '
      'при сборке. / Privacy: addresses, server and host names, keys and raw logs are not published; the build scans the page.</p></section>')
    w('</main><footer>%s · %s · %s · %s<br>Generated by scripts/build_test_history.py from releases/, CHANGELOG.md and '
      'docs/test-history/results.json.</footer>' % (E(PRODUCT), E(AUTHOR), E(app_version), E(LICENSE_LINE)))
    w('<script>%s</script></body></html>\n' % JS)
    return '\n'.join(o)


# ---------------------------------------------------------------- charts (inline SVG, no libraries)

# Validated categorical slots 1-3 (light / dark), all-pairs CVD-safe; text never uses these colors.
CHART_LIGHT = {'s1': '#2a78d6', 's2': '#eb6834', 's3': '#1baf7a', 'ink': '#0b0b0b', 'ink2': '#52514e', 'mut': '#6f6d68',
               'grid': '#e1e0d9', 'axis': '#c3c2b7', 'surf': '#fcfcfb', 'era': '#f1f0ec'}
CHART_DARK = {'s1': '#3987e5', 's2': '#d95926', 's3': '#199e70', 'ink': '#f0efec', 'ink2': '#c3c2b7', 'mut': '#a3a19a',
              'grid': '#2c2c2a', 'axis': '#383835', 'surf': '#1a1a19', 'era': '#222220'}
CHART_STATS = ('median', 'mean', 'single', 'approx', 'range', 'max')
CHART_W, CHART_H = 760, 440


def validate_charts(charts):
    errs = []
    if not isinstance(charts, list) or not charts:
        return ['charts must be a non-empty list']
    ids = set()
    for ci, c in enumerate(charts):
        w = 'charts[%d]' % ci
        if not isinstance(c.get('id'), str) or not re.fullmatch(r'[a-z0-9-]+', c.get('id') or '') or c['id'] in ids:
            errs.append(w + '.id must be a unique lower-case slug')
        ids.add(c.get('id'))
        for f in ('title_ru', 'title_en', 'note_ru', 'note_en', 'unit'):
            if not isinstance(c.get(f), str):
                errs.append('%s.%s must be text' % (w, f))
        series = c.get('series')
        if not isinstance(series, list) or not 1 <= len(series) <= 3:
            errs.append(w + '.series must hold 1-3 series (three validated colors)')
            continue
        for si, s in enumerate(series):
            for f in ('id', 'label_ru', 'label_en'):
                if not isinstance(s.get(f), str):
                    errs.append('%s.series[%d].%s must be text' % (w, si, f))
            seen = set()
            for pi, p in enumerate(s.get('points') or []):
                pw = '%s.series[%d].points[%d]' % (w, si, pi)
                if not VERSION_RX.fullmatch(str(p.get('version'))):
                    errs.append(pw + '.version is not a version')
                if p.get('version') in seen:
                    errs.append(pw + ': two points for one version')
                seen.add(p.get('version'))
                if p.get('stat') not in CHART_STATS:
                    errs.append(pw + '.stat must be one of ' + '/'.join(CHART_STATS))
                if p.get('platform') not in ('router', 'lab'):
                    errs.append(pw + '.platform must be router or lab')
                for f in ('source', 'ref'):
                    if not isinstance(p.get(f), str) or not p.get(f):
                        errs.append('%s.%s must be text' % (pw, f))
                if not isinstance(p.get('n'), int) or p.get('n') < 1:
                    errs.append(pw + '.n must be a positive integer')
                nums = [p.get(k) for k in ('value', 'p95', 'min', 'max') if p.get(k) is not None]
                if any(not isinstance(x, (int, float)) or isinstance(x, bool) or x <= 0 for x in nums):
                    errs.append(pw + ': values must be positive numbers (log scale)')
                if p.get('value') is None and not (p.get('stat') == 'range' and p.get('min') and p.get('max')):
                    errs.append(pw + ': a point without a value must be a min-max range')
    return errs


def _ticks(lo, hi):
    out = []
    e = int(math.floor(math.log10(lo)))
    while 10 ** e <= hi * 1.0001:
        for m in (1, 2, 5):
            v = m * 10 ** e
            if lo * 0.9999 <= v <= hi * 1.0001:
                out.append(round(v, 6))
        e += 1
    return out


def _fmt_s(v):
    return ('%g' % float('%.3g' % v)) if v < 1000 else '{:,}'.format(int(round(v)))


def _point_text(p, label, unit):
    if p.get('value') is None:
        main = '%s–%s %s (range)' % (_fmt_s(p['min']), _fmt_s(p['max']), unit)
    else:
        main = '%s %s (%s)' % (_fmt_s(p['value']), unit, {'single': 'one run', 'approx': 'approximate'}.get(p['stat'], p['stat']))
        extra = []
        if p.get('p95') is not None:
            extra.append('P95 %s' % _fmt_s(p['p95']))
        if p.get('min') is not None and p.get('max') is not None:
            extra.append('%s–%s' % (_fmt_s(p['min']), _fmt_s(p['max'])))
        elif p.get('max') is not None and p['stat'] != 'max':
            extra.append('max %s' % _fmt_s(p['max']))
        if extra:
            main += ', ' + ', '.join(extra)
    plat = 'GL-MT3000 router' if p['platform'] == 'router' else 'lab / virtual'
    t = '%s — %s: %s; n=%d; %s; source: %s' % (p['version'], label, main, p['n'], plat, p['source'])
    if p.get('note'):
        t += '; ' + p['note']
    return t


def _marker(shape, x, y, cls, hollow):
    fill = 'srf' if hollow else cls.replace('s', 'f')
    ring = 'ring' if not hollow else cls
    if shape == 0:
        return '<circle cx="%.1f" cy="%.1f" r="4.5" class="%s %s"/>' % (x, y, fill, ring)
    if shape == 1:
        return '<rect x="%.1f" y="%.1f" width="9" height="9" rx="1.5" class="%s %s"/>' % (x - 4.5, y - 4.5, fill, ring)
    return '<path d="M%.1f %.1fl5.5 5.5-5.5 5.5-5.5-5.5z" class="%s %s"/>' % (x, y - 5.5, fill, ring)


def chart_svg(c, standalone=False):
    """One chart as a self-contained SVG: log y axis, versions on x, median/mean markers with P95 or min-max whiskers."""
    cid = 'ch-' + c['id']
    unit = c['unit']
    series = c['series']
    versions = sorted({p['version'] for s in series for p in s['points']}, key=vkey)
    vals = []
    for s in series:
        for p in s['points']:
            vals += [p[k] for k in ('value', 'p95', 'min', 'max') if p.get(k) is not None]
    lo = 10 ** math.floor(math.log10(min(vals)))
    # headroom above the largest value for its direct label: the next 1-2-5 step at least 1.6x above it
    e = math.floor(math.log10(max(vals)))
    hi = next(m * 10 ** k for k in (e, e + 1, e + 2) for m in (1, 2, 5) if m * 10 ** k >= max(vals) * 1.6)
    if lo * 2 <= min(vals) / 1.15:
        lo *= 2
    rows = len(series) if len(series) > 1 else 0  # one series: the title names it, no legend box
    left, right = 58, 92
    top = 92 + rows * 19
    bottom = CHART_H - 92
    pw, ph = CHART_W - left - right, bottom - top
    band = pw / len(versions)
    X = {v: left + band * (i + 0.5) for i, v in enumerate(versions)}

    def Y(v):
        return bottom - (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * ph

    o = []
    w = o.append
    if standalone:
        w('<?xml version="1.0" encoding="UTF-8"?>')
    w('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" class="%s" role="img" aria-labelledby="%s-t %s-d" '
      'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">' % (CHART_W, CHART_H, cid, cid, cid))
    w('<title id="%s-t">%s / %s</title>' % (cid, E(c['title_ru']), E(c['title_en'])))
    w('<desc id="%s-d">%s %s Log scale, seconds. %s</desc>' % (cid, E(c['note_ru']), E(c['note_en']), E(PRODUCT)))

    def css(t):
        return ('.{0}{{--s1:{s1};--s2:{s2};--s3:{s3};--ink:{ink};--ink2:{ink2};--mut:{mut};--grid:{grid};--axis:{axis};'
                '--surf:{surf};--era:{era}}}').format(cid, **t)
    w('<style>%s@media (prefers-color-scheme:dark){{%s}}'
      '.{0} .bg{{fill:var(--surf)}}.{0} .era{{fill:var(--era)}}.{0} .gr{{stroke:var(--grid);stroke-width:1}}'
      '.{0} .ax{{stroke:var(--axis);stroke-width:1}}.{0} text{{fill:var(--ink2);font-size:11.5px}}'
      '.{0} .h1{{fill:var(--ink);font-size:16px;font-weight:600}}.{0} .h2{{fill:var(--ink2);font-size:13px}}'
      '.{0} .nt{{fill:var(--mut);font-size:12px}}.{0} .lg{{fill:var(--ink);font-size:12.5px}}.{0} .tk{{fill:var(--mut);font-size:11px}}'
      '.{0} .dl{{fill:var(--ink);font-size:12px;font-weight:600}}.{0} .s1{{stroke:var(--s1)}}.{0} .s2{{stroke:var(--s2)}}'
      '.{0} .s3{{stroke:var(--s3)}}.{0} .f1{{fill:var(--s1)}}.{0} .f2{{fill:var(--s2)}}.{0} .f3{{fill:var(--s3)}}'
      '.{0} .srf{{fill:var(--surf)}}.{0} .ring{{stroke:var(--surf);stroke-width:2}}.{0} .ln{{fill:none;stroke-width:2;'
      'stroke-linejoin:round;stroke-linecap:round}}.{0} .gap{{fill:none;stroke-width:1;opacity:.35}}'
      '.{0} .wh{{stroke-width:1.5;stroke-linecap:round}}.{0} .hit{{fill:transparent}}.{0} .pt:focus{{outline:none}}'
      '.{0} .pt:focus .hit,.{0} .pt:hover .hit{{fill:var(--grid)}}</style>'.format(cid) % (css(CHART_LIGHT), css(CHART_DARK)))
    w('<rect class="bg" x="0" y="0" width="%d" height="%d" rx="10"/>' % (CHART_W, CHART_H))
    w('<text class="h1" x="16" y="26">%s</text>' % E(c['title_ru']))
    w('<text class="h2" x="16" y="45">%s</text>' % E(c['title_en']))
    w('<text class="nt" x="16" y="64">%s</text>' % E(c['note_ru']))
    w('<text class="nt" x="16" y="80">%s</text>' % E(c['note_en']))
    for si, s in enumerate(series if rows else []):
        ly = 98 + si * 19
        k = 's%d' % (si + 1)
        w('<line x1="18" y1="%d" x2="40" y2="%d" class="ln %s"/>' % (ly, ly, k))
        w(_marker(si, 29, ly, k, False))
        w('<text class="lg" x="48" y="%d">%s / %s</text>' % (ly + 4, E(s['label_ru']), E(s['label_en'])))
    # runtime eras (Python before 2.0.0, Lua from 2.0.0) as a faint band behind the plot
    lua = [v for v in versions if vkey(v)[0] >= 2]
    if lua and len(lua) < len(versions):
        x0 = X[lua[0]] - band / 2
        w('<rect class="era" x="%.1f" y="%d" width="%.1f" height="%d"/>' % (x0, top, left + pw - x0, ph))
        w('<text class="tk" x="%.1f" y="%d">Python</text>' % (left + 6, bottom - 6))
        w('<text class="tk" x="%.1f" y="%d">Lua (+C)</text>' % (x0 + 6, bottom - 6))
    elif lua:
        w('<text class="tk" x="%.1f" y="%d">Lua (+C)</text>' % (left + 6, bottom - 6))
    for t in _ticks(lo, hi):
        y = Y(t)
        w('<line class="gr" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (left, y, left + pw, y))
        w('<text class="tk" x="%d" y="%.1f" text-anchor="end">%s %s</text>' % (left - 6, y + 4, _fmt_s(t), E(unit)))
    w('<line class="ax" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (left, bottom, left + pw, bottom))
    for v in versions:
        w('<text class="tk" text-anchor="end" transform="translate(%.1f %d) rotate(-40)">%s</text>' % (X[v] + 3, bottom + 14, E(v)))
    w('<text class="tk" x="%d" y="%d">%s</text>' % (left, CHART_H - 10,
      E('Версия (старые слева) / Version (oldest left) · логарифмическая шкала / log scale · GL-MT3000')))
    idx = {v: i for i, v in enumerate(versions)}
    for si, s in enumerate(series):
        k = 's%d' % (si + 1)
        pts = sorted(s['points'], key=lambda p: vkey(p['version']))
        valued = [p for p in pts if p.get('value') is not None]
        for a, b in zip(valued, valued[1:]):
            cls = 'ln' if idx[b['version']] - idx[a['version']] == 1 else 'gap'
            w('<line class="%s %s" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (
                cls, k, X[a['version']], Y(a['value']), X[b['version']], Y(b['value'])))
    for si, s in enumerate(series):
        k = 's%d' % (si + 1)
        pts = sorted(s['points'], key=lambda p: vkey(p['version']))
        label = s['label_en']
        for p in pts:
            x = X[p['version']]
            w('<g class="pt" tabindex="0"><title>%s</title>' % E(_point_text(p, label, unit)))
            lo_w = p.get('min') if p.get('min') is not None else p.get('value')
            hi_w = p.get('p95') if p.get('p95') is not None else p.get('max')
            if p['stat'] == 'max':
                lo_w = hi_w = None
            if lo_w is not None and hi_w is not None and hi_w > lo_w:
                w('<line class="wh %s" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (k, x, Y(lo_w), x, Y(hi_w)))
                for yv in (lo_w, hi_w):
                    w('<line class="wh %s" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (k, x - 4, Y(yv), x + 4, Y(yv)))
            yc = Y(p['value']) if p.get('value') is not None else Y(math.sqrt(p['min'] * p['max']))
            w('<circle class="hit" cx="%.1f" cy="%.1f" r="12"/>' % (x, yc))
            if p.get('value') is not None:
                w(_marker(si, x, yc, k, p['platform'] == 'lab'))
            w('</g>')
        # selective direct labels: the oldest and the newest measured value of each series
        if valued_pts(pts):
            first, last = valued_pts(pts)[0], valued_pts(pts)[-1]
            dy = (-11, 21, -11)[si]
            w('<text class="dl" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (X[first['version']], Y(first['value']) + dy, E(_fmt_s(first['value']) + ' ' + unit)))
            if last is not first:
                w('<text class="dl" x="%.1f" y="%.1f">%s</text>' % (X[last['version']] + 9, Y(last['value']) + 4 + (0, 12, -12)[si], E(_fmt_s(last['value']) + ' ' + unit)))
    w('</svg>')
    return '\n'.join(o) + ('\n' if standalone else '')


def valued_pts(pts):
    return [p for p in pts if p.get('value') is not None]


def chart_table(c):
    o = ['<details class="chart-table"><summary>Таблица значений / Data table</summary><div class="tbl"><table><thead><tr>'
         '<th>Версия / Version</th><th>Ряд / Series</th><th>Значение / Value</th><th>P95 / диапазон</th><th>n</th>'
         '<th>Где / Where</th><th>Источник / Source</th></tr></thead><tbody>']
    rows = []
    for s in c['series']:
        for p in s['points']:
            rows.append((vkey(p['version']), s['label_en'], p))
    for _, lab, p in sorted(rows, key=lambda r: (r[0], r[1])):
        val = '—' if p.get('value') is None else '%s %s (%s)' % (_fmt_s(p['value']), c['unit'], p['stat'])
        rng = []
        if p.get('p95') is not None:
            rng.append('P95 ' + _fmt_s(p['p95']))
        if p.get('min') is not None and p.get('max') is not None:
            rng.append('%s–%s' % (_fmt_s(p['min']), _fmt_s(p['max'])))
        o.append('<tr><td>%s</td><td>%s</td><td class="num">%s</td><td class="num">%s</td><td class="num">%d</td><td>%s</td><td>%s%s</td></tr>' % (
            E(p['version']), E(lab), E(val), E(', '.join(rng) or '—'), p['n'],
            'GL-MT3000' if p['platform'] == 'router' else 'lab', E(sanitize(p['source'])),
            (' — ' + E(sanitize(p['note']))) if p.get('note') else ''))
    o.append('</tbody></table></div></details>')
    return ''.join(o)


def chart_files(data):
    """Static copies of the charts for the documentation: docs/charts/<id>.svg."""
    return {c['id'] + '.svg': chart_svg(c, standalone=True) for c in data['charts']}


def build(results_path=None):
    results_path = Path(results_path or ROOT / 'docs' / 'test-history' / 'results.json')
    raw = results_path.read_text(encoding='utf-8')
    data = json.loads(raw)
    validate_results(data)
    versions, app = collect_versions()
    page = render(versions, app, data)
    problems = privacy_findings(page) + privacy_findings(raw)
    for text in chart_files(data).values():
        problems += privacy_findings(text)
    return page, versions, data, sorted(set(problems))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--results', default=None)
    ap.add_argument('--out', default=str(ROOT / 'docs' / 'TEST-HISTORY.html'))
    ap.add_argument('--charts-dir', default=str(ROOT / 'docs' / 'charts'))
    ap.add_argument('--check', action='store_true', help='fail when the output file is out of date')
    a = ap.parse_args(argv)
    try:
        page, versions, data, problems = build(a.results)
    except ValueError as e:
        print('results.json is invalid:\n%s' % e, file=sys.stderr)
        return 3
    if problems:
        print('PRIVACY SCAN FAILED, nothing written:', file=sys.stderr)
        for kind, text in problems:
            print('  %s: %s' % (kind, text), file=sys.stderr)
        return 2
    out = Path(a.out)
    data_bytes = page.encode('utf-8')
    files = {Path(a.charts_dir) / name: text.encode('utf-8') for name, text in sorted(chart_files(data).items())}
    if a.check:
        stale = [str(p) for p, b in [(out, data_bytes)] + list(files.items()) if not p.exists() or p.read_bytes() != b]
        if stale:
            print('out of date: %s; run scripts/build_test_history.py' % ', '.join(stale), file=sys.stderr)
            return 1
        print('up to date: %d versions, %d results' % (len(versions), len(data['results'])))
        return 0
    Path(a.charts_dir).mkdir(parents=True, exist_ok=True)
    for path, body in list(files.items()) + [(out, data_bytes)]:
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_bytes(body)
        os.replace(str(tmp), str(path))
    print('wrote %s: %d bytes, %d versions, %d results, %d charts, privacy scan clean' % (
        out, len(data_bytes), len(versions), len(data['results']), len(files)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
