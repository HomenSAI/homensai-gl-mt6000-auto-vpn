"""Loopback-only synthetic UI preview; no access to private/Git files or router."""
import argparse
import ipaddress
import subprocess
import sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import time
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'router/files/www/luci-static/resources/view/homensai-vpn'
FIXTURE=ROOT/'qa/ui-preview'
PREFIX='/router/files/www/luci-static/resources/view/homensai-vpn/'

def resolve_public(path):
    path=unquote(urlsplit(path).path)
    if path in ('/','/qa/ui-preview/index.html'):return FIXTURE/'index.html'
    if path=='/qa/ui-preview/stub.js':return FIXTURE/'stub.js'
    if path.startswith(PREFIX):
        target=(ASSETS/path[len(PREFIX):]).resolve()
        if target.is_relative_to(ASSETS.resolve()) and target.suffix.lower() in ('.js','.css','.svg','.png','.woff','.woff2','.ttf') and target.is_file():return target
    return None

def preview_module():
    data=json.loads((ROOT/'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text(encoding='utf8'))
    selected=data['admin/services/homensai-vpn']['action']['path'].split('/')[-1]
    if not __import__('re').fullmatch('dashboard[0-9]+',selected):raise ValueError('PREVIEW-ASSET')
    return (ASSETS/(selected+'.js')).read_bytes()

def discover_router_origin():
    if sys.platform!='win32':return None
    command="Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' | Where-Object {$_.NextHop -ne '0.0.0.0'} | Sort-Object @{Expression={if($_.InterfaceAlias -like 'Ethernet*'){0}else{1}}},RouteMetric | Select-Object -First 1 -ExpandProperty NextHop"
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=15)
        if result.returncode:return None
        address=ipaddress.ip_address(result.stdout.strip())
        if address.version!=4 or not address.is_private or address.is_loopback or address.is_unspecified:return None
        return 'http://'+str(address)
    except (OSError,ValueError,subprocess.TimeoutExpired):return None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        expected={'127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port),'[::1]:'+str(self.server.server_port)}
        if self.headers.get('Host','').lower() not in expected:
            self.send_error(403,'PREVIEW-HOST-REFUSED');return
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+host for host in expected}:
            self.send_error(403,'PREVIEW-ORIGIN-REFUSED');return
        try:
            if urlsplit(self.path).path=='/preview-router.js':body=('window.HOMENSAI_PREVIEW_ROUTER_ORIGIN='+json.dumps(discover_router_origin())+';').encode();kind='application/javascript'
            elif urlsplit(self.path).path=='/preview-module.js':body=preview_module();kind='application/javascript'
            else:
                target=resolve_public(self.path)
                if target is None:self.send_error(404);return
                body=target.read_bytes();kind=mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
                if target.name=='stub.js':body=body.replace(b"version:'0.8.0-alpha2'",('version:'+json.dumps(json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']['version'])).encode())  # the fixture reports the real current version
            self.send_response(200);self.send_header('Content-Type',kind+'; charset=utf-8' if kind.startswith(('text/','application/javascript')) else kind)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-HomenSAI-Preview','synthetic-only');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cross-Origin-Resource-Policy','same-origin')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(body)
        except (OSError,ValueError,KeyError):self.send_error(500,'PREVIEW-ASSET-UNAVAILABLE')
    def log_message(self,*args):pass

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=18886);parser.add_argument('--seconds',type=int,default=10800);args=parser.parse_args()
    if not 1024<=args.port<=65535 or not 60<=args.seconds<=10800:raise ValueError('PREVIEW-BOUNDS')
    end=time.monotonic()+args.seconds
    with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
        server.timeout=.5
        print('SYNTHETIC-UI-PREVIEW 127.0.0.1:'+str(args.port),flush=True)
        while time.monotonic()<end:server.handle_request()
if __name__=='__main__':main()
