"""Bounded loopback-only proxy to the marked isolated clone, no body/cookie logs."""
import argparse,base64,http.server,json,re,subprocess,time
from urllib.parse import unquote,urlsplit
from endurance_state import container_name
CONTAINER='homensai-vpn-qemu-alpha7'

def clone_identity(container):
 row=json.loads(subprocess.check_output(['docker','inspect',container],text=True,timeout=10))[0]
 if (row['HostConfig']['NetworkMode']!='none' or row['HostConfig']['Privileged'] or row['Mounts'] or not row['State']['Running']
     or not isinstance(row.get('Id'),str) or not re.fullmatch(r'[a-f0-9]{64}',row['Id'])):
  raise ValueError('VIRTUAL-PROXY-ISOLATION')
 return row['Id']

def allowed_request(method,path,host,origin,site,port):
 expected=('127.0.0.1:'+str(port),'localhost:'+str(port))
 if host not in expected or origin not in (None,)+tuple('http://'+h for h in expected) or site=='cross-site':return False
 if method not in ('GET','POST','HEAD'):return False
 uri=urlsplit(path);normalized=uri.path
 for _ in range(4):normalized=unquote(normalized)
 allowed=normalized in ('/','/cgi-bin/luci','/ubus') or normalized.startswith(('/cgi-bin/luci/','/luci-static/','/ubus/'))
 return bool(not uri.scheme and not uri.netloc and allowed and not any(x in normalized for x in ('..','%',chr(92),chr(0),chr(13),chr(10))))

def rpc_codes(payload):
 """Ephemeral envelope parsing; never retain arguments, sessions or bodies."""
 try:
  body=json.loads(payload)
  codes=[]
  for row in (body if isinstance(body,list) else [body])[:16]:
   if not isinstance(row,dict):continue
   result=row.get('result');error=row.get('error')
   code=result[0] if isinstance(result,list) and result else None
   error=error.get('code') if isinstance(error,dict) else None
   codes.append({'result':code if type(code) is int and -1000000<=code<=1000000 else None,
                 'error':error if type(error) is int and -1000000<=error<=1000000 else None})
  return codes
 except (ValueError,RecursionError,UnicodeError):return [{'malformed':True}]

def rpc_path(path):
 path=urlsplit(path).path
 return path in ('/ubus','/cgi-bin/luci/admin/ubus') or path.startswith(('/ubus/','/cgi-bin/luci/admin/ubus/'))

class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def handle(self):
  try:super().handle()
  except (ConnectionError,TimeoutError) as error:
   if hasattr(self.server,'observed'):self.server.observed.append({'kind':'disconnect','status':0,'error_type':type(error).__name__})
 def setup(self):
  super().setup();self.connection.settimeout(10)
 def forward_request(self):
  started=time.monotonic();stage='policy'
  kind='asset' if self.path.startswith('/luci-static/') else 'rpc' if '/ubus' in self.path else 'luci'
  def observed(status,**extra):
   if hasattr(self.server,'observed'):self.server.observed.append(dict(kind=kind,status=status,stage=stage,elapsed_ms=round((time.monotonic()-started)*1000),**extra))
  if not allowed_request(self.command,self.path,self.headers.get('Host',''),self.headers.get('Origin'),self.headers.get('Sec-Fetch-Site'),self.server.server_port):observed(403);self.send_error(403);return
  if self.path=='/':self.send_response(302);self.send_header('Location','/cgi-bin/luci/');self.end_headers();return
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<=length<=2*1024*1024:raise ValueError()
  except ValueError:self.send_error(400);return
  try:
   stage='identity'
   target=self.server.clone_id
   if not isinstance(target,str) or not re.fullmatch(r'[a-f0-9]{64}',target):raise ValueError('VIRTUAL-PROXY-PIN-INVALID')
   stage='bridge'
   body=self.rfile.read(length) if length else b''
   extended=self.command=='POST' and rpc_path(self.path) and getattr(self.server,'rpc_timeout_seconds',20)==60
   request={'method':self.command,'path':self.path,'headers':dict(self.headers),'body':base64.b64encode(body).decode(),'timeout':65 if extended else 35}
   child=subprocess.run(['docker','exec','-i',target,'python3','/lab/clone_http_bridge.py'],input=json.dumps(request).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=70 if extended else 45,check=True)
   response=json.loads(child.stdout);payload=base64.b64decode(response['body'],validate=True)
  except Exception as error:
   observed(502,error_type=type(error).__name__)
   self.send_error(502,'ISOLATED-VIRTUAL-LUCI-UNAVAILABLE');return
  self.send_response(response['status'])
  observed(response['status'],bytes=len(payload),**({'rpc_codes':rpc_codes(payload)} if kind=='rpc' else {}))
  for key,value in response['headers']:
   if key.lower() not in ('transfer-encoding','connection','content-length'):self.send_header(key,value)
  self.send_header('X-HomenSAI-Virtual-Lab','isolated-x86-clone');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers()
  if self.command!='HEAD':self.wfile.write(payload)
 do_GET=forward_request
 do_POST=forward_request
 do_HEAD=forward_request
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18900);p.add_argument('--seconds',type=int,default=3600);p.add_argument('--container',default=CONTAINER);a=p.parse_args();assert 1024<=a.port<=65535 and 60<=a.seconds<=10800
 container=container_name(a.container);identity=clone_identity(container)
 subprocess.run(['docker','exec',identity,'python3','-c','from serial_clone import require_clone;require_clone()'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
 end=time.monotonic()+a.seconds
 with http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler) as server:
  server.container=container;server.clone_id=identity
  server.timeout=.5
  while time.monotonic()<end:server.handle_request()
