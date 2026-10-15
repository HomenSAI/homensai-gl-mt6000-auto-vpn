import threading
import unittest
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from server import Handler


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_index_has_restrictive_browser_policy(self):
        with urlopen(self.url) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("connect-src 'none'", response.headers['Content-Security-Policy'])
            self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_only_allowlisted_assets_are_served(self):
        for path in ('/server.py', '/test_server.py', '/../README.md', '/%2e%2e/.git/config'):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.url + path)
            self.assertEqual(error.exception.code, 404)

    def test_posts_cannot_apply_configuration(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url + '/api/apply', method='POST', data=b'{}'))
        self.assertEqual(error.exception.code, 501)

    def test_javascript_served_with_correct_type(self):
        with urlopen(self.url + '/model.js?v=1') as response:
            self.assertIn('text/javascript', response.headers['Content-Type'])
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')


if __name__ == '__main__':
    unittest.main()
