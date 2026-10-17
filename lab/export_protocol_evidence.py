"""Export only public synthetic evidence after terminal state, never key files."""
import base64,hashlib,io,json,re,tarfile,shlex
from collections import Counter
from pathlib import Path
from serial_clone import require_clone,run
require_clone();start=json.loads(Path('/lab/protocol-soak-start.json').read_text());root=start['root'];assert re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',root)
archive=root+'-public-evidence.tar.gz'
encode_code='import base64,pathlib,sys;sys.stdout.write(base64.encodebytes(pathlib.Path('+repr(archive)+').read_bytes()).decode())'
command="(test -f "+archive+" || tar -czf "+archive+" -C "+root+" status.json series.json probe-observations.jsonl) && printf 'PAYLOAD_BEGIN\\n' && python3 -c "+shlex.quote(encode_code)+" && printf '\\nPAYLOAD_END\\n'"
text=run(command,60);match=re.search(r'(?m)^PAYLOAD_BEGIN\n(.*?)\nPAYLOAD_END',text,re.S);assert match,'EXPORT-FRAME'
data=base64.b64decode(re.sub(r'\s','',match.group(1)),validate=True);assert len(data)<1024*1024
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
 members=tar.getmembers();assert {m.name for m in members}=={'status.json','series.json','probe-observations.jsonl'} and all(m.isfile() and m.size<=4*1024*1024 for m in members)
 status=json.loads(tar.extractfile('status.json').read());series=json.loads(tar.extractfile('series.json').read());rows=[json.loads(line) for line in tar.extractfile('probe-observations.jsonl').read().splitlines()]
 assert status['state']==series['producer_state']=='PASS' and status['source_sha256']==series['source_sha256']==start['source_sha256']
 assert status['elapsed_seconds']>=start['duration_seconds']
 for row in rows:
  assert set(row)=={'expected_profile','bound','sample','socket_timeout_seconds','time'} and row['expected_profile'] in ('wga','wgb','ova','ovb') and row['socket_timeout_seconds']==3
  sample=row['sample'];assert set(sample)=={'dns','https','profile','error','phase','elapsed_ms'}
  if sample['https']:assert sample['dns'] and sample['profile']==row['expected_profile'] and sample['error'] is None
 errors=Counter(row['sample']['error'] for row in rows if row['sample']['error'])
 summary={'result':'PASS','raw_probe_records':len(rows),'successful_dns_tls_records':sum(row['sample']['https'] for row in rows),'negative_probe_records':sum(errors.values()),'negative_codes_including_injected_failures':dict(errors),'socket_timeout_seconds':3,'archive_bytes':len(data),'archive_sha256':hashlib.sha256(data).hexdigest(),'archive_members':sorted(m.name for m in members),'source_sha256':start['source_sha256'],'scope':'synthetic probes, including intentional DNS/interface/guard failures; not production incident statistics','physical_router_access':False}
Path('/lab/protocol-final-public-evidence.tar.gz').write_bytes(data);Path('/lab/protocol-final-raw-probes-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))