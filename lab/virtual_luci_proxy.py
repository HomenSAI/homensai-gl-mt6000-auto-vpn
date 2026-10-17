"""Bounded loopback-only proxy to the marked isolated clone, no body/cookie logs."""
import argparse,base64,http.server,json,subprocess,time
from urllib.parse import unquote,urlsplit
CONTAINER='homensai-vpn-qemu-alpha7'
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def request(self):
  origin=self.headers.get('Origin');host=self.headers.get('Host','');expected='127.0.0.1:'+str(self.server.server_port)
  if host not in (expected,'localhost:'+str(self.server.server_port)) or origin not in (None,'http://'+expected,'http://localhost:'+str(self.server.server_port)) or self.headers.get('Sec-Fetch-Site')=='cross-site':self.send_error(403);return
  if self.path=='/':self.send_response(302);self.send_header('Location','/cgi-bin/luci/');self.end_headers();return
  uri=urlsplit(self.path);normalized=uri.path
  for _ in range(4):normalized=unquote(normalized)
  allowed=normalized in ('/cgi-bin/luci','/ubus') or normalized.startswith(('/cgi-bin/luci/','/luci-static/','/ubus/'))
  if uri.scheme or uri.netloc or not allowed or any(x in normalized for x in ('..',chr(92),chr(0),chr(13),chr(10))):self.send_error(404);return
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<=length<=2*1024*1024:raise ValueError()
   body=self.rfile.read(length) if length else b''
   request={'method':self.command,'path':self.path,'headers':dict(self.headers),'body':base64.b64encode(body).decode()}
   child=subprocess.run(['docker','exec','-i',CONTAINER,'python3','/lab/clone_http_bridge.py'],input=json.dumps(request).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=45,check=True)
   response=json.loads(child.stdout);payload=base64.b64decode(response['body'],validate=True)
  except Exception:self.send_error(502,'ISOLATED-VIRTUAL-LUCI-UNAVAILABLE');return
  self.send_response(response['status'])
  for key,value in response['headers']:
   if key.lower() not in ('transfer-encoding','connection','content-length'):self.send_header(key,value)
  self.send_header('X-HomenSAI-Virtual-Lab','isolated-x86-clone');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers()
  if self.command!='HEAD':self.wfile.write(payload)
 do_GET=request
 do_POST=request
 do_HEAD=request
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18900);p.add_argument('--seconds',type=int,default=3600);a=p.parse_args();assert 1024<=a.port<=65535 and 60<=a.seconds<=10800
 info=json.loads(subprocess.check_output(['docker','inspect',CONTAINER],text=True))[0];assert info['HostConfig']['NetworkMode']=='none' and not info['HostConfig']['Privileged'] and not info['Mounts']
 end=time.monotonic()+a.seconds
 with http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler) as server:
  server.timeout=.5
  while time.monotonic()<end:server.handle_request()
