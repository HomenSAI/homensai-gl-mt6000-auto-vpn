"""Safe status/evidence collection for the marked isolated protocol soak."""
import json
from datetime import datetime,timezone
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r'''import hashlib,json
from pathlib import Path
root=Path('/tmp/homensai-protocol-lab-soak20261016');p=root/'status.json';row=json.loads(p.read_text())
series=root/'series.json';e=json.loads(series.read_text()) if series.exists() else None
collector=Path('/tmp/hs-evidence.py')
print('CLONE_JSON:'+json.dumps({'producer':row,'series':e,'collector_sha256':hashlib.sha256(collector.read_bytes()).hexdigest() if collector.exists() else None,'collector_error_tail':Path('/tmp/hs-evidence.log').read_text()[-300:]}))'''
row=json_command(code,15);row['host_observed_at_utc']=datetime.now(timezone.utc).isoformat()
Path('/lab/protocol-soak-latest.json').write_text(json.dumps(row,indent=2))
p=row['producer'];e=row['series'] or {}
print(json.dumps({'state':p['state'],'elapsed_seconds':p['elapsed_seconds'],'cycles':p['cycles'],'counts':p['counts'],'missing_events':e.get('missing_events'),'coverage_complete':e.get('coverage_complete'),'selected_verified':e.get('selected_verified'),'cleanup_confirmed':p.get('cleanup_confirmed'),'error':p.get('error'),'collector_error':row['collector_error_tail']}))
