import json
from serial_clone import json_command,require_clone
require_clone()
code=r'''import json,subprocess,uuid
from pathlib import Path
name='hsdiag'+uuid.uuid4().hex[:6];path=Path('/tmp/'+name+'.nft')
subprocess.check_call(['ip','netns','add',name]);rows=[]
try:
 for chain in ('out','lab_output'):
  script='table inet hs_lab_guard { chain '+chain+' { type filter hook output priority -300; policy accept; meta nfproto ipv6 counter drop; ip daddr 203.0.113.10 oifname != { "wg0", "wg1", "ovpn0", "ovpn1" } counter drop; }; }\n'
  path.write_text(script)
  r=subprocess.run(['ip','netns','exec',name,'nft','-c','-f',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  rows.append({'chain':chain,'rc':r.returncode,'error':r.stderr.decode(errors='replace')[:1200]})
 print('CLONE_JSON:'+json.dumps(rows))
finally:
 path.unlink();subprocess.check_call(['ip','netns','delete',name])'''
print(json.dumps(json_command(code,10),indent=2))
