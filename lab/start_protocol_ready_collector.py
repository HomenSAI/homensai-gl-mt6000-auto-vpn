"""Start loss-aware collector after the owned producer creates its first status."""
from serial_clone import require_clone,json_command
from pathlib import Path
import json,re,hashlib
require_clone();start=json.loads(Path('/lab/protocol-soak-start.json').read_text());assert re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',start['root']) and re.fullmatch('[a-f0-9]{64}',start['source_sha256'])
collector_sha=hashlib.sha256(Path('/lab/assets/protocol_evidence_collector.py').read_bytes()).hexdigest()
code=r'''import hashlib,json,shlex,subprocess,sys
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
root=__ROOT__;sha=__SHA__
collector=Path('/tmp/hs-evidence-'+__COLLECTOR_SHA__[:16]+'.py');assert not collector.is_symlink()
if not collector.exists():
 r=subprocess.run(['wget','-q','-O',str(collector),'http://10.0.3.2:8088/protocol_evidence_collector.py'],timeout=15);assert r.returncode==0
assert hashlib.sha256(collector.read_bytes()).hexdigest()==__COLLECTOR_SHA__
args=[sys.executable,str(collector),'--root',root,'--source-sha256',sha]
command='for i in $(seq 1 120); do if test -f '+shlex.quote(root+'/status.json')+'; then exec '+shlex.join(args)+'; fi; sleep 1; done; exit 23'
log=open(root+'-collector.log','wb');child=subprocess.Popen(['sh','-c',command],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);log.close()
print('CLONE_JSON:'+json.dumps({'collector_pid':child.pid,'root':root,'producer_source_sha256':sha,'collector_sha256':hashlib.sha256(collector.read_bytes()).hexdigest(),'startup_wait_seconds':120,'physical_router_access':False}))'''.replace('__ROOT__',repr(start['root'])).replace('__SHA__',repr(start['source_sha256'])).replace('__COLLECTOR_SHA__',repr(collector_sha))
row=json_command(code,20);Path('/lab/protocol-ready-collector-start.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))