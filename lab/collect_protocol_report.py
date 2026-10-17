"""Collect bounded synthetic protocol evidence from the marked virtual copy."""
import argparse,json,re
from datetime import datetime,timezone
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone();parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
if not re.fullmatch('/tmp/homensai-protocol-lab(?:-[a-z0-9]+)?',args.root) or not re.fullmatch(r'/lab/[A-Za-z0-9_-]+\.json',args.output):raise ValueError('LAB-COLLECT-BOUNDS')
code='import json;from pathlib import Path;p=Path('+json.dumps(args.root+'/status.json')+');print("CLONE_JSON:"+json.dumps(json.loads(p.read_text())))'
row=json_command(code,10);row['host_observed_at_utc']=datetime.now(timezone.utc).isoformat();row['evidence_kind']='intermediate' if row['state']=='RUNNING' else 'terminal'
Path(args.output).write_text(json.dumps(row,indent=2));print(json.dumps({'state':row['state'],'counts':row.get('counts'),'error':row.get('error'),'evidence_kind':row['evidence_kind']}))
