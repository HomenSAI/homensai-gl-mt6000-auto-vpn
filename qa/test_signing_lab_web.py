"""The web page of the signing lab: bind address, one-time token, cookie, CSRF, Origin and Host checks, one-shot secrets, no logs,
the real rate limit behind the page, and a drill walked over HTTP the way the owner does it. Offline, 127.0.0.1 only."""
import argparse
import http.client
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/signing'))
sys.path.insert(0, str(ROOT/'qa'))
import lab  # noqa: E402
import lab_drills  # noqa: E402
import lab_mode  # noqa: E402
import lab_web  # noqa: E402
import totp  # noqa: E402

CSP_OK = "default-src 'none'"


@unittest.skipUnless(shutil.which('git'), 'git needed')
class Web(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='hsai-lab-web-'))
        self.addCleanup(lab_mode.remove_tree, self.base)
        patcher = mock.patch.dict(os.environ, {lab_mode.TEST_ENV: '1'})
        patcher.start()
        self.addCleanup(patcher.stop)
        scrypt = mock.patch.object(totp, 'SCRYPT_N', 2**4)
        scrypt.start()
        self.addCleanup(scrypt.stop)
        self.lab = lab_mode.LabDir(self.base/'lab').ensure()
        self.session = lab_drills.Session(self.lab, clock=lab_drills.VirtualClock(), network=False)
        self.server, self.url = lab_web.make_server(self.lab, self.session)
        self.port = self.server.server_address[1]
        self.token = self.url.split('t=')[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.app = self.server.app
        self.cookie = None

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, method, path, body=None, headers=None, host=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        default = {'Host': host or '127.0.0.1:%d' % self.port}
        if self.cookie:
            default['Cookie'] = self.cookie
        default.update(headers or {})
        connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        data = None if body is None else json.dumps(body).encode()
        for name, value in default.items():
            if value is not None:
                connection.putheader(name, value)
        if data is not None:
            connection.putheader('Content-Length', str(len(data)))
        connection.endheaders(data)
        reply = connection.getresponse()
        payload = reply.read()
        connection.close()
        return reply, payload

    def login(self):
        reply, _ = self.request('GET', '/?t='+self.token)
        self.assertEqual(reply.status, 303)
        self.cookie = reply.getheader('Set-Cookie').split(';')[0]
        return reply

    def post(self, path, body=None, **overrides):
        headers = {'Content-Type': 'application/json', 'X-CSRF-Token': self.app.csrf, 'Origin': 'http://127.0.0.1:%d' % self.port}
        headers.update(overrides)
        return self.request('POST', path, {} if body is None else body, headers)

    def wait_op(self, op, answers=()):
        """Poll like the page; answer each prompt with the next value."""
        answers, seen, position = list(answers), [], 0
        deadline = time.time()+180
        while time.time() < deadline:
            reply, payload = self.request('GET', '/api/events?op=%s&after=%d' % (op, position))
            data = json.loads(payload)
            for event in data['events']:
                seen.append(event)
                if event['type'] == 'prompt' and answers:
                    value = answers.pop(0)
                    self.assertEqual(self.post('/api/answer', {'op': op, 'value': value(seen) if callable(value) else value})[0].status, 200)
            position = data['next']
            if data['done']:
                return seen
            time.sleep(0.02)
        self.fail('the drill did not finish: %s' % seen[-3:])

    # ---- bind, token, session -----------------------------------------------------------------------------------------
    def test_bound_to_loopback_only_on_a_system_port(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        self.assertNotEqual(self.port, 0)
        self.assertEqual(self.server.socket.family, socket.AF_INET)
        self.assertEqual(lab_web.HOST, '127.0.0.1')
        self.assertNotIn('host', {action.dest for action in lab.parser()._actions})

    def test_nothing_without_a_session(self):
        for path in ('/', '/api/state', '/report', '/api/events?op=x'):
            self.assertEqual(self.request('GET', path)[0].status, 403)

    def test_token_is_one_time_and_leaves_the_url(self):
        reply = self.login()
        self.assertEqual(reply.getheader('Location'), '/')
        cookie = reply.getheader('Set-Cookie')
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)
        self.assertNotIn(self.token, cookie)
        saved, self.cookie = self.cookie, None
        self.assertEqual(self.request('GET', '/?t='+self.token)[0].status, 403)
        self.cookie = saved
        self.assertEqual(self.request('GET', '/')[0].status, 200)

    def test_wrong_and_expired_tokens_open_nothing(self):
        self.assertEqual(self.request('GET', '/?t=wrong')[0].status, 403)
        self.app.token_born -= lab_web.TOKEN_SECONDS+1
        self.assertEqual(self.request('GET', '/?t='+self.token)[0].status, 403)

    def test_wrong_cookie_is_refused(self):
        self.login()
        self.cookie = lab_web.COOKIE+'=forged'
        self.assertEqual(self.request('GET', '/api/state')[0].status, 403)

    def test_foreign_host_header_is_refused(self):
        self.login()
        for host in ('evil.example:%d' % self.port, 'localhost:%d' % self.port, '127.0.0.1'):
            reply, payload = self.request('GET', '/api/state', host=host)
            self.assertEqual((reply.status, json.loads(payload)['error']), (403, 'LAB-HOST'))

    # ---- CSRF and friends ---------------------------------------------------------------------------------------------
    def expect(self, code, **overrides):
        reply, payload = self.post('/api/reset', {'confirm': 'RESET'}, **overrides)
        self.assertEqual((reply.status, json.loads(payload)['error']), (403, code))
        self.assertTrue(self.lab.repo.exists(), 'a refused request changed nothing')

    def test_post_needs_the_csrf_token(self):
        self.login()
        self.expect('LAB-CSRF', **{'X-CSRF-Token': None})
        self.expect('LAB-CSRF', **{'X-CSRF-Token': 'forged'})

    def test_post_needs_the_session(self):
        self.expect('LAB-NO-SESSION')

    def test_post_from_another_origin_is_refused(self):
        self.login()
        self.expect('LAB-ORIGIN', Origin='http://evil.example')
        self.expect('LAB-ORIGIN', Origin='null')
        self.expect('LAB-ORIGIN', **{'Sec-Fetch-Site': 'cross-site'})

    def test_post_needs_json_and_a_small_body(self):
        self.login()
        self.expect('LAB-CONTENT-TYPE', **{'Content-Type': 'text/plain'})
        reply, payload = self.post('/api/run', {'x': 'y'*(lab_web.MAX_BODY+1)})
        self.assertEqual((reply.status, json.loads(payload)['error']), (403, 'LAB-BAD-REQUEST'))

    # ---- page ---------------------------------------------------------------------------------------------------------
    def test_page_is_self_contained_and_shows_the_owner_attributes(self):
        self.login()
        reply, payload = self.request('GET', '/')
        policy = reply.getheader('Content-Security-Policy')
        self.assertIn(CSP_OK, policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertEqual(reply.getheader('Cache-Control'), 'no-store')
        self.assertEqual(reply.getheader('Referrer-Policy'), 'no-referrer')
        text = payload.decode('utf-8')
        self.assertNotRegex(text, r'<script[^>]+src=|<link |@import|url\(')
        self.assertEqual(set(re.findall(r'https?://[^"\' )]+', text)), {'https://homensai.com'})
        nonce = re.search(r"script-src 'nonce-([^']+)'", policy).group(1)
        self.assertEqual(len(re.findall('nonce="%s"' % re.escape(nonce), text)), 2)
        for needed in ('HomenS', 'GL.iNet GL-MT6000', 'Serhii Khomenko', 'HomenS.AI Style', lab_drills.program_version(), 'ТЕСТОВАЯ ЛАБОРАТОРИЯ', 'prefers-color-scheme', 'prefers-reduced-motion', 'max-width:900px'):
            self.assertIn(needed, text)
        self.assertNotIn('{{', text.replace('{{{', ''))

    def test_state_is_public_facts_only(self):
        self.login()
        reply, payload = self.request('GET', '/api/state')
        data = json.loads(payload)
        self.assertEqual((reply.status, data['keys'], data['chain']['entries']), (200, [], 0))
        self.assertFalse(data['totp']['enrolled'])

    # ---- a drill over HTTP --------------------------------------------------------------------------------------------
    def run_drill(self, drill, auto=True, answers=()):
        reply, payload = self.post('/api/run', {'drill': drill, 'auto': auto})
        self.assertEqual(reply.status, 200, payload)
        return self.wait_op(json.loads(payload)['op'], answers)

    @staticmethod
    def result(events):
        return next(event for event in events if event['type'] == 'result')

    def test_manual_enrolment_walks_prompts_and_secrets_come_once(self):
        self.login()
        self.assertEqual(self.result(self.run_drill('a'))['status'], 'PASS')

        def phone(seen):
            manual = next(event for event in seen if event['type'] == 'secret' and event['kind'] == 'manual')
            return totp.totp(totp.seed_bytes(manual['text'].replace(' ', '')), self.session.clock.now())
        with mock.patch.object(sys, 'stderr', io.StringIO()) as stderr, mock.patch.object(sys, 'stdout', io.StringIO()) as stdout:
            events = self.run_drill('b', auto=False, answers=[phone, ''])
        self.assertEqual(self.result(events)['status'], 'PASS', events[-4:])
        self.assertEqual((stderr.getvalue(), stdout.getvalue()), ('', ''), 'nothing is logged')
        codes = next(event for event in events if event['kind' if event['type'] == 'secret' else 'type'] == 'codes')['codes']
        self.assertEqual(len(codes), 10)
        self.assertEqual(sum(event['type'] == 'prompt' for event in events), 2)
        replay = json.loads(self.request('GET', '/api/events?op=%s&after=0' % self.app.active.id)[1])
        text = json.dumps(replay)
        self.assertNotIn(codes[0], text)
        self.assertIn('secret-shown', text)
        self.assertFalse(any(event['type'] == 'secret' for event in self.app.active.events))
        disk = self.lab.report.read_bytes()+self.lab.results.read_bytes()
        self.assertNotIn(codes[0].encode(), disk)
        state = json.loads(self.request('GET', '/api/state')[1])
        self.assertEqual((state['totp']['enrolled'], state['codes']['left']), (True, 10))

    def test_a_mistyped_enrolment_code_can_be_typed_again(self):
        self.login()
        self.assertEqual(self.result(self.run_drill('a'))['status'], 'PASS')

        def phone(seen):
            manual = next(event for event in seen if event['type'] == 'secret' and event['kind'] == 'manual')
            return totp.totp(totp.seed_bytes(manual['text'].replace(' ', '')), self.session.clock.now())
        events = self.run_drill('b', auto=False, answers=['000000', phone, ''])
        self.assertEqual(self.result(events)['status'], 'PASS', events[-4:])

    def test_answer_only_when_a_prompt_waits(self):
        self.login()
        self.assertEqual(self.post('/api/answer', {'op': 'nothing', 'value': '1'})[0].status, 409)

    def test_second_drill_is_refused_while_one_runs(self):
        self.login()
        release = threading.Event()
        self.app.start('x', lambda op: release.wait(20))
        reply, payload = self.post('/api/run', {'drill': 'a', 'auto': True})
        self.assertEqual((reply.status, 'LAB-BUSY' in payload.decode()), (409, True))
        self.assertEqual(self.post('/api/reset', {'confirm': 'RESET'})[0].status, 409)
        release.set()

    def test_unknown_drill_is_refused(self):
        self.login()
        self.assertEqual(self.post('/api/run', {'drill': 'zz'})[0].status, 409)

    def test_rate_limit_of_the_real_gate_holds_behind_the_page(self):
        self.login()
        self.assertEqual(self.result(self.run_drill('b', auto=True))['status'], 'PASS')
        stops = []
        for _ in range(4):
            events = self.run_drill('d', auto=False, answers=['000000', '000000'])
            stops += [event.get('text', '') for event in events]
            if any('TOTP-LOCKED' in line for line in stops):
                break
        self.assertTrue(any('TOTP-LOCKED' in line for line in stops), stops[-6:])

    def test_cancel_stops_a_waiting_prompt(self):
        self.login()
        self.assertEqual(self.result(self.run_drill('a'))['status'], 'PASS')
        reply, payload = self.post('/api/run', {'drill': 'b', 'auto': False})
        op = json.loads(payload)['op']
        deadline = time.time()+30
        while not self.app.active.waiting and time.time() < deadline:
            time.sleep(0.02)
        self.assertEqual(self.post('/api/cancel', {'op': op})[0].status, 200)
        events = self.wait_op(op)
        self.assertEqual(self.result(events)['status'], 'CANCELLED')
        self.assertFalse(self.lab.store().has('totp.seed.dpapi'), 'a cancelled enrolment saves nothing')

    def test_reset_needs_its_word_wipes_the_lab_only_and_starts_clean(self):
        self.login()
        self.assertEqual(self.result(self.run_drill('a'))['status'], 'PASS')
        beside = self.base/'beside.txt'
        beside.write_text('keep')
        self.assertEqual(self.post('/api/reset', {'confirm': 'yes'})[0].status, 400)
        self.assertEqual(self.post('/api/reset', {'confirm': 'RESET'})[0].status, 200)
        self.assertEqual(beside.read_text(), 'keep')
        self.assertEqual(json.loads(self.request('GET', '/api/state')[1])['keys'], [])
        self.assertTrue((self.lab.root/lab_mode.MARKER).is_file())

    def test_report_is_served_with_a_scriptless_policy(self):
        self.login()
        self.assertEqual(self.request('GET', '/report')[0].status, 404)
        self.run_drill('a')
        reply, payload = self.request('GET', '/report')
        self.assertEqual(reply.status, 200)
        self.assertIn(CSP_OK, reply.getheader('Content-Security-Policy'))
        self.assertIn('ТЕСТОВАЯ ЛАБОРАТОРИЯ', payload.decode('utf-8'))

    def test_quit_stops_the_server(self):
        self.login()
        self.assertEqual(self.post('/api/quit')[0].status, 200)
        self.thread.join(10)
        self.assertFalse(self.thread.is_alive())


class OpTests(unittest.TestCase):
    def test_secret_is_delivered_once(self):
        op = lab_web.Op('x')
        op.emit({'type': 'secret', 'text': 'value'})
        op.emit({'type': 'step'})
        rows, position, _ = op.read(0)
        self.assertEqual((rows[0]['text'], position), ('value', 2))
        self.assertNotIn('value', json.dumps(op.read(0)[0]))

    def test_handler_never_logs(self):
        with mock.patch.object(sys, 'stderr', io.StringIO()) as stderr:
            lab_web.Handler.log_message(mock.Mock(), '%s', 'GET /?t=secret')
        self.assertEqual(stderr.getvalue(), '')


class CommandLineShape(unittest.TestCase):
    def test_no_option_can_open_the_page_to_the_network(self):
        self.assertIsInstance(lab.parser(), argparse.ArgumentParser)
        flags = {flag for action in lab.parser()._actions for flag in action.option_strings}
        self.assertFalse(flags & {'--host', '--bind', '--port', '--listen'})


if __name__ == '__main__':
    unittest.main()
