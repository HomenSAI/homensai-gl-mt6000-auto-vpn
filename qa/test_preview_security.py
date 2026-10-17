from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import http.client,tempfile,threading,unittest
import ui_preview_server as preview
class PreviewSecurityTests(unittest.TestCase):
    def test_only_fixture_assets_are_served_and_posts_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'qa/ui-preview';folder.mkdir(parents=True);(folder/'index.html').write_text('fixture')
            (root/'private.txt').write_text('private');(folder/'escape.txt').symlink_to(root/'private.txt')
            with patch.object(preview,'ROOT',root):
                server=ThreadingHTTPServer(('127.0.0.1',0),preview.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    for method,path,wanted in [('GET','/qa/ui-preview/index.html',200),('GET','/.git/config',404),('GET','/qa/ui-preview/escape.txt',404),('POST','/qa/ui-preview/index.html',405)]:
                        client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2);client.request(method,path);response=client.getresponse();self.assertEqual(response.status,wanted);response.read();client.close()
                finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
