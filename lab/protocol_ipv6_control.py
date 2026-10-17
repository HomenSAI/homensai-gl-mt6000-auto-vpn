"""Read-only IPv6 transport/guard proof in the running marked synthetic cohort."""
import argparse,json,re
from datetime import datetime,timezone
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--sha256',required=True);p.add_argument('--pid',type=int,required=True);a=p.parse_args()
if not re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',a.root) or not re.fullmatch('[a-f0-9]{64}',a.sha256) or a.pid<2:raise ValueError('IPV6-CONTROL-BOUNDS')
code=r'''import hashlib,json,os,shlex,subprocess,uuid
from pathlib import Path
root=Path(__LAB_ROOT__);state=json.loads((root/'status.json').read_text());sha=__LAB_SHA__
assert state['state']=='RUNNING' and state['source_sha256']==sha
source='/tmp/hs-protocol-'+sha[:16]+'.py';assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==sha
parent=__LAB_PID__;argv=Path('/proc/'+str(parent)+'/cmdline').read_bytes().split(b'\0');assert source.encode() in argv and str(root).encode() in argv
children=[];servers={}
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  fields=(proc/'stat').read_text().rsplit(') ',1)[1].split()
  if int(fields[1])==parent:children.append(proc.name)
 except (FileNotFoundError,ProcessLookupError,ValueError,IndexError):continue
for child in children:
 try:args=Path('/proc/'+child+'/cmdline').read_bytes().split(b'\0')
 except FileNotFoundError:continue
 if source.encode() in args and b'--profile' in args:
  label=args[args.index(b'--profile')+1].decode();inode=Path('/proc/'+child+'/ns/net').stat().st_ino
  candidates=[p.name for p in Path('/var/run/netns').iterdir() if p.stat().st_ino==inode]
  assert len(candidates)==1;servers[label]=candidates[0]
assert all(x in servers for x in ('wga','wgb'))
client=servers['wga'][:-1]+'c';assert Path('/var/run/netns/'+client).is_file()
def ns(name,args,timeout=15):return subprocess.run(['ip','netns','exec',name]+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
probe=r"""import json,socket,ssl,uuid
nonce=uuid.uuid4().hex;row={'https':False,'error':None}
try:
 with socket.socket(socket.AF_INET6,socket.SOCK_STREAM) as raw:
  raw.settimeout(3);raw.bind((SOURCE,0));raw.connect(('fd77::12',443))
  with ssl.create_default_context(cafile=CERT).wrap_socket(raw,server_hostname='vpn.lab.test') as tls:
   tls.sendall(('GET /?nonce='+nonce+' HTTP/1.0\r\nHost: vpn.lab.test\r\n\r\n').encode());data=b''
   while len(data)<16384:
    part=tls.recv(min(4096,16384-len(data)))
    if not part:break
    data+=part
 value=json.loads(data.split(b'\r\n\r\n',1)[1]);row['https']=value.get('profile')=='wgb' and value.get('nonce')==nonce
except (OSError,ValueError) as error:row['error']=type(error).__name__
print(json.dumps(row))"""
def request(name,address):
 text=probe.replace('SOURCE',repr(address)).replace('CERT',repr(str(root/'cert.pem')))
 r=ns(name,['python3','-c',text],20);assert r.returncode==0;return json.loads(r.stdout)
def counter():
 r=ns(client,['nft','-j','list','table','inet','hs_lab_guard']);assert r.returncode==0
 table=json.loads(r.stdout)
 for obj in table['nftables']:
  rule=obj.get('rule',{});expr=rule.get('expr',[])
  if rule.get('chain')=='lab_output' and any(e.get('match',{}).get('right')=='ipv6' for e in expr):
   values=[e['counter']['packets'] for e in expr if 'counter' in e];assert len(values)==1;return values[0]
 raise ValueError('IPV6-GUARD-COUNTER-UNVERIFIED')
control=request(servers['wga'],'fd77::11');assert control['https'],'IPV6-POSITIVE-CONTROL-FAILED'
route=ns(client,['ip','-6','route','get','fd77::12']);assert route.returncode==0 and b'underlay' in route.stdout,'IPV6-ROUTE-MISSING'
before=counter();blocked=request(client,'fd77::10');after=counter()
assert not blocked['https'] and after>before,'IPV6-GUARD-NOT-PROVEN'
print('CLONE_JSON:'+json.dumps({'result':'PASS','scope':'synthetic namespace IPv6 TLS positive control and actual output guard; not GL.iNet forwarded IPv6 acceptance','producer_source_sha256':sha,'positive_ipv6_tls_control':True,'client_ipv6_route_present':True,'protected_ipv6_attempt_blocked':True,'guard_counter_delta':after-before,'configuration_writes':False,'physical_router_access':False}))'''.replace('__LAB_ROOT__',repr(a.root)).replace('__LAB_SHA__',repr(a.sha256)).replace('__LAB_PID__',str(a.pid))
compile(code,'<ipv6-control>','exec')
try:result=json_command(code,45)
except (RuntimeError,TimeoutError) as error:
 import re
 output=getattr(error,'output','');names=re.findall(r'(?:AssertionError|ValueError): ([A-Z0-9_-]+)',output)
 print(json.dumps({'development_error_lines':[line.strip() for line in output.splitlines() if ('Error:' in line or 'File \"<string>\"' in line)][-5:]}))
 result={'result':'FAIL','code':names[-1] if names else type(error).__name__,'scope':'synthetic IPv6 control; no physical router'}
result['host_observed_at_utc']=datetime.now(timezone.utc).isoformat();Path('/lab/protocol-ipv6-control.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
raise SystemExit(0 if result.get('result')=='PASS' else 1)
