"""Bounded cold-Python startup timing in an owned isolated guest namespace."""
import json
from pathlib import Path
from datetime import datetime,timezone
from serial_clone import require_clone,json_command
require_clone()
code=r'''import json,subprocess,time,uuid,hashlib
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
name='hb'+uuid.uuid4().hex[:8];rows=[]
def run(args):
 start=time.monotonic()
 try:
  r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=22)
  return {'seconds':round(time.monotonic()-start,3),'returncode':r.returncode,'stderr_tail':r.stderr.decode(errors='replace')[-180:]}
 except subprocess.TimeoutExpired:return {'seconds':round(time.monotonic()-start,3),'timeout':True}
before=subprocess.check_output(['ip','-4','route','show','table','all'])
subprocess.run(['ip','netns','add',name],check=True,timeout=5)
try:
 for scope,prefix in [('root',[]),('namespace',['ip','netns','exec',name])]:
  for kind,script in [('minimal','print("READY")'),('imports','import argparse,http.server,ssl,secrets,threading;print("READY")')]:
   row=run(prefix+['python3','-c',script]);row.update(scope=scope,kind=kind);rows.append(row)
finally:subprocess.run(['ip','netns','delete',name],check=True,timeout=5)
print('CLONE_JSON:'+json.dumps({'rows':rows,'root_routes_unchanged':before==subprocess.check_output(['ip','-4','route','show','table','all']),'owned_namespace_removed':name not in subprocess.check_output(['ip','netns','list']).decode().split(),'physical_router_access':False}))'''
row=json_command(code,115);row['host_observed_at_utc']=datetime.now(timezone.utc).isoformat();Path('/lab/protocol-boot-diagnostic.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))