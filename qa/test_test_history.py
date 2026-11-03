"""Checks for scripts/build_test_history.py and docs/test-history/results.json."""
import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_test_history as th  # noqa: E402

RESULTS = ROOT / 'docs' / 'test-history' / 'results.json'


class TestHistoryBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page, cls.versions, cls.data, cls.problems = th.build()

    def test_two_builds_are_identical(self):
        again = th.build()[0]
        self.assertEqual(self.page, again)

    def test_committed_inputs_pass_the_privacy_scan(self):
        self.assertEqual(self.problems, [])

    def test_every_release_note_and_package_appears(self):
        listed = {v['version'] for v in self.versions}
        expected = set()
        for p in (ROOT / 'releases').iterdir():
            m = re.fullmatch(r'(?:notes-)?v(.+)\.md', p.name) or re.fullmatch(r'homensai-auto-vpn_(.+)-\d+_all\.ipk', p.name)
            if m and th.VERSION_RX.fullmatch(m.group(1)):
                expected.add(m.group(1))
        self.assertTrue(expected)
        self.assertEqual(expected - listed, set())
        for v in expected:
            self.assertIn('<span class="ver">%s</span>' % v, self.page)
        app = json.loads((ROOT / 'VERSION.json').read_text(encoding='utf-8'))['application']['version']
        self.assertEqual(self.versions[-1]['version'], app)

    def test_versions_are_sorted_oldest_first(self):
        for v in self.versions:
            m = th.VERSION_RX.fullmatch(v['version'])
            self.assertTrue(m and int(m.group(1)) < 10, v['version'])
        keys = [th.vkey(v['version']) for v in self.versions]
        self.assertEqual(keys, sorted(keys))
        self.assertLess(th.vkey('2.0.0-alpha9'), th.vkey('2.0.0-alpha10'))
        self.assertLess(th.vkey('1.0.0-beta15'), th.vkey('2.0.0-alpha1'))
        self.assertLess(th.vkey('0.9.0-alpha35'), th.vkey('0.9.0'))

    def test_owner_attributes_and_license(self):
        for text in ('HomenS.AI Auto VPN', 'Serhii Khomenko | HomenS.AI', th.LICENSE_LINE.replace('&', '&amp;'),
                     self.versions[-1]['version'], 'prefers-color-scheme:dark', 'name="viewport"'):
            self.assertIn(text, self.page)
        self.assertIsNone(re.search(r'\bMIT\b', self.page))
        self.assertNotRegex(self.page, r'<(?:script|link|img)[^>]+(?:src|href)=["\']?https?:')

    def test_results_schema(self):
        data = json.loads(RESULTS.read_text(encoding='utf-8'))
        th.validate_results(data)
        self.assertGreater(len(data['results']), 0)
        self.assertEqual(sorted(m['phase'] for m in data['matrix']), list(range(10)))
        bad = copy.deepcopy(data)
        bad['results'][0]['kind'] = 'guess'
        bad['results'][1]['metrics'] = {'detect_s': {'median': 'fast'}}
        bad['results'].append(dict(bad['results'][2]))
        with self.assertRaises(ValueError) as cm:
            th.validate_results(bad)
        msg = str(cm.exception)
        self.assertIn('unknown', msg)
        self.assertIn('not a number', msg)
        self.assertIn('duplicate id', msg)


class Charts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(RESULTS.read_text(encoding='utf-8'))
        cls.page = th.build()[0]

    def test_at_least_three_charts_each_with_measured_history(self):
        charts = self.data['charts']
        self.assertGreaterEqual(len(charts), 3)
        for c in charts:
            pts = sorted((p for s in c['series'] for p in s['points'] if p.get('value') is not None),
                         key=lambda p: th.vkey(p['version']))
            self.assertGreaterEqual(len(pts), 2, c['id'])
            self.assertLess(th.vkey(pts[0]['version']), th.vkey(pts[-1]['version']), c['id'])
            for s in c['series']:
                valued = [p for p in s['points'] if p.get('value') is not None]
                if len(valued) >= 2:
                    first = min(valued, key=lambda p: th.vkey(p['version']))
                    last = max(valued, key=lambda p: th.vkey(p['version']))
                    self.assertLess(th.vkey(first['version']), th.vkey(last['version']))

    def test_chart_points_reference_known_results_or_documents(self):
        ids = {r['id'] for r in self.data['results']}
        for c in self.data['charts']:
            for s in c['series']:
                for p in s['points']:
                    for ref in p['ref'].split(','):
                        self.assertIn(ref, ids, '%s %s' % (c['id'], ref))

    def test_charts_are_inline_and_static_files_match(self):
        files = th.chart_files(self.data)
        for c in self.data['charts']:
            self.assertIn('class="ch-%s"' % c['id'], self.page)
            path = ROOT / 'docs' / 'charts' / (c['id'] + '.svg')
            self.assertTrue(path.exists(), path)
            self.assertEqual(path.read_bytes(), files[c['id'] + '.svg'].encode('utf-8'))
            svg = files[c['id'] + '.svg']
            self.assertIn('prefers-color-scheme:dark', svg)
            self.assertNotRegex(svg, r'(?:href|src)=')
            self.assertEqual(th.privacy_findings(svg), [])
        self.assertEqual(files, th.chart_files(self.data))

    def test_chart_validation_rejects_invented_or_bad_points(self):
        bad = copy.deepcopy(self.data['charts'])
        bad[0]['series'][0]['points'][0]['value'] = 0
        bad[0]['series'][0]['points'][1]['stat'] = 'guess'
        bad[1]['series'][0]['points'][0].pop('source')
        bad[2]['series'][0]['points'][0]['value'] = None
        bad[2]['series'][0]['points'][0]['stat'] = 'median'
        errs = '\n'.join(th.validate_charts(bad))
        for text in ('positive numbers', 'stat must be', 'source must be text', 'without a value'):
            self.assertIn(text, errs)


class PrivacyScan(unittest.TestCase):
    def kinds(self, text):
        return {k for k, _ in th.privacy_findings(text)}

    def test_planted_values_are_caught(self):
        self.assertIn('ipv4', self.kinds('exit 10.20.30.40 seen'))
        self.assertIn('ipv4', self.kinds('net 10.5.0.2/16'))
        self.assertIn('ipv6', self.kinds('addr fe80::1 here'))
        self.assertIn('ipv6', self.kinds('addr 2001:db8:0:1:2:3:4:5'))
        self.assertIn('mac', self.kinds('aa:bb:cc:dd:ee:ff'))
        self.assertIn('vpn-host', self.kinds('de1552.nordvpn.com'))
        self.assertIn('email', self.kinds('someone@example.org'))
        self.assertIn('lan-host', self.kinds('router.lan'))
        self.assertIn('word', self.kinds('a Telegram token'))
        self.assertIn('word', self.kinds('-----BEGIN KEY'))
        self.assertIn('word', self.kinds('PRIVATE'))

    def test_versions_times_and_contact_are_allowed(self):
        self.assertEqual(self.kinds('2.1.0 0.9.1-alpha26 v2.0.0-beta4 12:34:56 2026-11-02 1.0.0.dev info@homensai.com 4.11.0'), set())

    def test_sanitize_removes_planted_values(self):
        raw = 'Server de1552.nordvpn.com at 192.168.12.250, fe80::1, mac aa:bb:cc:dd:ee:ff, mail x@y.org, token kept.'
        clean = th.sanitize(raw)
        self.assertEqual(th.privacy_findings(clean), [])
        self.assertIn('NordVPN Berlin server', clean)

    def test_build_refuses_to_write_a_page_with_a_planted_ip(self):
        data = json.loads(RESULTS.read_text(encoding='utf-8'))
        data['results'][0]['note'] = 'exit address 187.40.16.19'
        with tempfile.TemporaryDirectory() as tmp:
            res = Path(tmp) / 'results.json'
            res.write_text(json.dumps(data), encoding='utf-8')
            out = Path(tmp) / 'out.html'
            rc = th.main(['--results', str(res), '--out', str(out)])
            self.assertEqual(rc, 2)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
