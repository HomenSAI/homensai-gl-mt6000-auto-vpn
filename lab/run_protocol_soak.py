"""Start immutable two-hour protocol soak in the marked isolated clone only."""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
p=argparse.ArgumentParser();p.add_argument('--sha256',required=True);p.add_argument('--duration',type=int,default=7200);p.add_argument('--root',default='/tmp/homensai-protocol-lab-soak20261016');a=p.parse_args()
if not re.fullmatch('[a-f0-9]{64}',a.sha256) or not 7200<=a.duration<=10800 or not re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',a.root):raise ValueError('SOAK-BOUNDS')
code=r'''import hashlib,json,subprocess,sys
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
root=Path(__LAB_ROOT__);assert not root.exists(),'SOAK-ROOT-EXISTS'
source=Path('/tmp/hs-protocol-'+__LAB_SHA__[:16]+'.py');assert not source.is_symlink()
if not source.exists():
 r=subprocess.run(['wget','-q','-O',str(source),'http://10.0.3.2:8088/protocol_namespace_lab.py'],timeout=15);assert r.returncode==0
assert hashlib.sha256(source.read_bytes()).hexdigest()==__LAB_SHA__,'SOAK-SOURCE-HASH'
source.chmod(0o600)
log=Path(str(root)+'-producer.log').open('xb')
child=subprocess.Popen([sys.executable,str(source),'--root',str(root),'--duration',str(__LAB_DURATION__)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
log.close()
print('CLONE_JSON:'+json.dumps({'started':True,'pid':child.pid,'root':str(root),'duration_seconds':__LAB_DURATION__,'source_sha256':__LAB_SHA__,'physical_router_access':False}))'''.replace('__LAB_ROOT__',repr(a.root)).replace('__LAB_SHA__',repr(a.sha256)).replace('__LAB_DURATION__',str(a.duration))
compile(code,'<immutable-soak-starter>','exec')
row=json_command(code,20);row['host_started_at_utc']=datetime.now(timezone.utc).isoformat()
Path('/lab/protocol-soak-start.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
