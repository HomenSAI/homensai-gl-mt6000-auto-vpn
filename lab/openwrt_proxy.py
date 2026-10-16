"""Loopback-only proxy to the disposable VM's actual LuCI. No cookie/body logs."""
import base64
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import subprocess

class Proxy(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def handle_request(self):
        length=int(self.headers.get('Content-Length',0))
        if not 0<=length<=2*1024*1024:self.send_error(413);return
        body=self.rfile.read(length) if length else b''
        request={'method':self.command,'path':self.path,'headers':dict(self.headers),'body':base64.b64encode(body).decode()}
        try:
            run=subprocess.run(['docker','exec','-i','homensai-vpn-qemu','python3','/lab/openwrt_http_bridge.py'],input=json.dumps(request).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=40,check=True)
            response=json.loads(run.stdout);payload=base64.b64decode(response['body'],validate=True)
        except (OSError,ValueError,subprocess.SubprocessError):self.send_error(502,'Virtual lab bridge unavailable');return
        self.send_response(response['status'])
        for key,value in response['headers']:
            if key.lower() not in ('transfer-encoding','connection','content-length'):self.send_header(key,value)
        self.send_header('Content-Length',str(len(payload)));self.end_headers()
        if self.command!='HEAD':self.wfile.write(payload)
    do_GET=handle_request
    do_POST=handle_request
    do_HEAD=handle_request

if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',18882),Proxy).serve_forever()
