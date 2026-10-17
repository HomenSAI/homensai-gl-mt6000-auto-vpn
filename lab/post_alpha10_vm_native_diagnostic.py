import json
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r"""import json,sys,time,traceback,re,subprocess
from pathlib import Path
sys.path.insert(0,'/usr/lib/homensai-vpn')
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
start=time.monotonic()
try:
 import auto_control
 result=auto_control.start()
 row={'native_start_returned':True,'accepted':result.get('accepted'),'blockers':result.get('blockers',[])}
except Exception as e:
 frames=traceback.extract_tb(e.__traceback__)
 row={'native_start_returned':False,'exception_type':type(e).__name__,'frames':[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in frames]}
 text=str(e)
 if re.fullmatch('[A-Z0-9_-]{1,96}',text):row['code']=text
row['elapsed_seconds']=round(time.monotonic()-start,3)
print('CLONE_JSON:'+json.dumps(row))"""
r=json_command(code,90);Path('/lab/post-alpha10-native-diagnosis.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
