"""Diagnose real opkg refusal semantics; restore only the synthetic Auto flag."""
import json
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r'''import hashlib,json,re,subprocess
from pathlib import Path
def cmd(args):return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=60)
def signature():
 p=Path('/usr/lib/homensai-vpn/agent.py');s=p.stat()
 return (hashlib.sha256(p.read_bytes()).hexdigest(),s.st_ino,s.st_mtime_ns,s.st_size)
before=signature()
try:
 cmd(['uci','set','homensai_vpn.main.native_enabled=1']);cmd(['uci','commit','homensai_vpn'])
 result=subprocess.run(['opkg','--force-reinstall','install','/tmp/homensai-alpha7-package/candidate.ipk'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
 text=result.stdout.decode(errors='replace')
 report={'returncode':result.returncode,'guard_codes':re.findall(r'LIFECYCLE-[A-Z0-9-]+',text),
         'agent_bytes_inode_mtime_unchanged':signature()==before,
         'log_tail_sanitized':[line for line in text.splitlines() if any(word in line.lower() for word in ('prerm','preinst','failed','error','refus','upgrad','reinstall','remove'))][-12:]}
finally:
 cmd(['uci','set','homensai_vpn.main.native_enabled=0']);cmd(['uci','commit','homensai_vpn'])
report['scope']='force-reinstall diagnostic only; original and physical router untouched'
print('CLONE_JSON:'+json.dumps(report))'''
report=json_command(code,120)
Path('/lab/alpha7-guard-probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
