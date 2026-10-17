import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('preview',Path(__file__).resolve().parents[1]/'scripts/serve-ui-preview.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PreviewTests(unittest.TestCase):
    def test_private_git_traversal_and_unknown_paths_denied(self):
        for path in ('/.git/config','/private/file','/README.md',module.PREFIX+'../../../../../../../.git/config',module.PREFIX+'%2e%2e/%2e%2e/private/file'):
            with self.subTest(path=path):self.assertIsNone(module.resolve_public(path))
    def test_http_dns_rebinding_origin_and_private_paths_refused(self):
        import http.client,threading
        from http.server import ThreadingHTTPServer
        server=ThreadingHTTPServer(('127.0.0.1',0),module.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for path,headers,wanted in [('/',{'Host':'attacker.example'},403),('/',{'Origin':'https://attacker.example'},403),('/.git/config',{},404),('/private/backup.tar.gz',{},404),('/router/files/www/luci-static/resources/view/homensai-vpn/%2e%2e/%2e%2e/private.key',{},404),('/qa/ui-preview/index.html',{},200)]:
                with self.subTest(path=path,headers=headers):
                    client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2);client.request('GET',path,headers=headers);response=client.getresponse();self.assertEqual(response.status,wanted)
                    if wanted==200:self.assertEqual(response.getheader('Cross-Origin-Resource-Policy'),'same-origin');self.assertEqual(response.getheader('X-Content-Type-Options'),'nosniff')
                    response.read();client.close()
        finally:server.shutdown();server.server_close();thread.join()
    def test_fixture_and_selected_asset_are_bounded(self):
        self.assertEqual(module.resolve_public('/?lang=ru'),module.FIXTURE/'index.html')
        self.assertTrue(module.resolve_public(module.PREFIX+'ui15.css').is_relative_to(module.ASSETS))
        self.assertIn(b'autoWindowDeadline',module.preview_module())
if __name__=='__main__':unittest.main()
