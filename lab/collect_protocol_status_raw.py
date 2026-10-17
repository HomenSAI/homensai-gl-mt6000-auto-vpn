"""Read synthetic status JSON via cat, avoiding an extra cold guest Python launch."""
import argparse,json,re
from pathlib import Path
from datetime import datetime,timezone
from serial_clone import require_clone,run
require_clone();p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
if not re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',a.root) or not re.fullmatch('/lab/[a-z0-9-]+.json',a.output):raise ValueError('COLLECT-BOUNDS')
text=run('cat '+a.root+'/status.json',25);row,_=json.JSONDecoder().raw_decode(text[text.index('{'):]);row['host_observed_at_utc']=datetime.now(timezone.utc).isoformat();row['evidence_kind']='intermediate' if row['state']=='RUNNING' else 'terminal';Path(a.output).write_text(json.dumps(row,indent=2));print(json.dumps({key:row.get(key) for key in ('state','counts','cycles','error','cleanup_confirmed','elapsed_seconds')}))