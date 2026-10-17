"""Freshness-aware read-only snapshot of the marked ready protocol soak."""
from serial_clone import require_clone,run
from datetime import datetime,timezone
from pathlib import Path
import json,re,shlex
require_clone();start=json.loads(Path('/lab/protocol-soak-start.json').read_text());root=start['root'];sha=start['source_sha256']
assert re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',root) and re.fullmatch('[a-f0-9]{64}',sha)
def read(name):
 text=run('cat '+root+'/'+name,20);return json.JSONDecoder().raw_decode(text[text.index('{'):])[0]
p=read('status.json');s=read('series.json')
assert p['source_sha256']==s['source_sha256']==sha
age_code='import os,time; print(int(time.time())); print(int(os.stat('+repr(root+'/status.json')+').st_mtime)); print(int(os.stat('+repr(root+'/series.json')+').st_mtime))'
ages=run('python3 -c '+shlex.quote(age_code),20)
values=[int(x) for x in re.findall(r'(?m)^([0-9]{9,12})\r?$',ages)];assert len(values)==3
age={'producer_seconds':values[0]-values[1],'collector_seconds':values[0]-values[2]}
row={'host_observed_at_utc':datetime.now(timezone.utc).isoformat(),'producer':p,'series':s,'observation_age':age,'fresh':all(0<=v<=90 for v in age.values()),'physical_router_access':False}
Path('/lab/protocol-ready-observation.json').write_text(json.dumps(row,indent=2));print(json.dumps({'state':p['state'],'counts':p['counts'],'elapsed_seconds':p['elapsed_seconds'],'cycles':p['cycles'],'missing_events':s['missing_events'],'coverage_complete':s['coverage_complete'],'selected_verified':s['selected_verified'],'error':p.get('error'),'observation_age':age,'fresh':row['fresh']}))