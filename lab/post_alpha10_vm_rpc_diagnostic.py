import json
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r"""import json,subprocess,time,re
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
start=time.monotonic();r=subprocess.run(['ubus','-t','30','call','homensai-vpn','native_start','{}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
try:body=json.loads(r.stdout)
except Exception:body={}
known=['Permission denied','Request timed out','Method not found','Command failed']
row={'ubus_returncode':r.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'accepted':body.get('accepted'),'error_code':body.get('error'),'blockers':body.get('blockers',[]),'stderr_class':[x for x in known if x.encode() in r.stderr]}
print('CLONE_JSON:'+json.dumps(row))"""
r=json_command(code,60);Path('/lab/post-alpha10-rpc-diagnosis.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
