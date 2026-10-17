"""Read only the marked virtual protocol lab status, never physical devices."""
import json
import argparse,re
from serial_clone import require_clone,json_command
require_clone()
parser=argparse.ArgumentParser();parser.add_argument('--root',default='/tmp/homensai-protocol-lab-smoke2');args=parser.parse_args()
if not re.fullmatch('/tmp/homensai-protocol-lab(?:-[a-z0-9]+)?',args.root):raise ValueError('LAB-ROOT')
code=r'''import json,subprocess
from pathlib import Path
p=Path('/tmp/homensai-protocol-lab-smoke/status.json')
row=json.loads(p.read_text()) if p.exists() else None
if row:row=dict(row,recent=row.get('recent',[])[-6:])
print('CLONE_JSON:'+json.dumps({'status':row,'log_tail':Path('/tmp/hs-protocol-smoke.log').read_text()[-1000:],'process_logs':{x.name:x.read_text(errors='replace')[-1200:] for x in Path('/tmp/homensai-protocol-lab-smoke').glob('process-*.log')},'namespaces':subprocess.check_output(['ip','netns','list']).decode(),'memory':[s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith(('MemAvailable:','MemFree:'))]}))'''
code=code.replace('/tmp/homensai-protocol-lab-smoke',args.root)
print(json.dumps(json_command(code,10),indent=2))
