"""Loopback-only preview of the actual generated UI with synthetic RPC data."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse,json,re
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args):pass
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/':self.send_response(302);self.send_header('Location','/qa/ui-preview/index.html');self.end_headers();return
        if path=='/preview-module.js':
            menu=json.loads((ROOT/'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text(encoding='utf-8-sig'))
            name=menu['admin/services/homensai-vpn']['action']['path'].split('/')[-1]
            if not re.fullmatch(r'dashboard[0-9]+',name):self.send_error(404);return
            data=(ROOT/'router/files/www/luci-static/resources/view/homensai-vpn'/(name+'.js')).read_bytes()
            self.send_response(200);self.send_header('Content-Type','application/javascript; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        allowed=('/qa/ui-preview/','/router/files/www/luci-static/resources/view/homensai-vpn/')
        target=(ROOT/path.lstrip('/')).resolve()
        base=next(((ROOT/prefix.lstrip('/')).resolve() for prefix in allowed if path.startswith(prefix)),None)
        if base is None or not target.is_relative_to(base) or not target.is_file():self.send_error(404);return
        super().do_GET()
    def do_POST(self):self.send_error(405)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18884);args=p.parse_args()
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
