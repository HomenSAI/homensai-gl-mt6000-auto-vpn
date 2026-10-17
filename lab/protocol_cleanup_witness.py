"""Independent cleanup witness for the marked immutable virtual protocol soak."""
import argparse,json,re
from datetime import datetime,timezone
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone();start=json.loads(Path('/lab/protocol-soak-start.json').read_text());assert re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',start['root']) and re.fullmatch('[a-f0-9]{64}',start['source_sha256']) and type(start['pid']) is int
p=argparse.ArgumentParser();p.add_argument('phase',choices=('before','after'));a=p.parse_args()
code=r'''import hashlib,json,subprocess
from pathlib import Path
root=Path(__ROOT__);sha=__SHA__;source=Path('/tmp/hs-protocol-'+sha[:16]+'.py');pid=__PID__
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
children=[];namespaces=[];cohort=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  argv=(proc/'cmdline').read_bytes().split(b'\0')
  if any(arg==str(root).encode() or arg.startswith((str(root)+'/').encode()) for arg in argv):cohort.append(int(proc.name))
  fields=(proc/'stat').read_text().rsplit(') ',1)[1].split()
  if int(fields[1])!=pid:continue
  children.append(int(proc.name));inode=(proc/'ns/net').stat().st_ino
  namespaces.extend(p.name for p in Path('/var/run/netns').iterdir() if p.stat().st_ino==inode)
 except (FileNotFoundError,ProcessLookupError,IndexError,ValueError):continue
fingerprint=hashlib.sha256(subprocess.check_output(['ip','-4','route','show','table','all'])+subprocess.check_output(['ip','-4','rule','show'])+subprocess.check_output(['uci','export','network'])+subprocess.check_output(['uci','export','firewall'])).hexdigest()
print('CLONE_JSON:'+json.dumps({'producer_state':json.loads((root/'status.json').read_text())['state'],'children':sorted(set(children)),'cohort_processes':sorted(set(cohort)),'namespaces':sorted(set(namespaces)),'private_key_files_remaining':len(list(root.glob('*.key')))+len(list(root.glob('*.secret')))+int((root/'key.pem').exists()),'root_fingerprint':fingerprint,'all_namespace_names':subprocess.check_output(['ip','netns','list']).decode().splitlines()}))'''.replace('__ROOT__',repr(start['root'])).replace('__SHA__',repr(start['source_sha256'])).replace('__PID__',str(start['pid']))
row=json_command(code,45);row['host_observed_at_utc']=datetime.now(timezone.utc).isoformat()
if a.phase=='before':
 assert row['producer_state']=='RUNNING' and row['children'] and row['namespaces'];Path('/lab/protocol-ready-cleanup-before.json').write_text(json.dumps(row,indent=2));print(json.dumps({'phase':'before','children':len(row['children']),'namespaces':len(row['namespaces']),'private_key_files_remaining':row['private_key_files_remaining']}))
else:
 before=json.loads(Path('/lab/protocol-ready-cleanup-before.json').read_text());current={line.split()[0] for line in row['all_namespace_names']};prefixes={name[:-1] for name in before['namespaces']};owned=[name for name in current if any(name.startswith(prefix) for prefix in prefixes)]
 row['owned_namespaces_remaining']=owned;row['root_checkpoint_unchanged']=row['root_fingerprint']==before['root_fingerprint'];row['result']='PASS' if row['producer_state'] in ('PASS','FAIL','STOPPED') and not row['children'] and not row['cohort_processes'] and not owned and row['private_key_files_remaining']==0 and row['root_checkpoint_unchanged'] else 'FAIL'
 Path('/lab/protocol-ready-cleanup-after.json').write_text(json.dumps(row,indent=2));print(json.dumps(row));raise SystemExit(0 if row['result']=='PASS' else 1)