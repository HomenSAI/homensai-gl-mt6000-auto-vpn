"""Restore only the already identified private VM after its recorded failed reboot."""
import json,socket,subprocess,time,shlex
from pathlib import Path
assert json.loads(Path('/lab/warm-reboot-result.json').read_text())['result']=='UNCONFIRMED'
assert Path('/lab/openwrt.img').is_file() and Path('/lab/run-cache128.py').is_file()
with socket.socket(socket.AF_UNIX) as s:
 s.settimeout(5);s.connect('/lab/qmp.sock');f=s.makefile('rwb',buffering=0);json.loads(f.readline())
 for name in ['qmp_capabilities','quit']:
  f.write((json.dumps({'execute':name})+'\n').encode())
  while True:
   row=f.readline()
   if not row:break
   value=json.loads(row)
   if 'error' in value:raise SystemExit('Private QMP refused restoration')
   if 'return' in value:break
end=time.monotonic()+15
while time.monotonic()<end:
 with socket.socket() as p:
  if p.connect_ex(('127.0.0.1',2222))!=0:break
 time.sleep(.5)
else:raise SystemExit('Refused duplicate VM')
log=open('/lab/qemu-cache128-restored.log','ab')
subprocess.Popen(['python3','/lab/run-cache128.py','--direct-kernel'],stdout=log,stderr=log,start_new_session=True)
ssh=['ssh','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/known_hosts','-o','BatchMode=yes','-o','ConnectTimeout=3','-p','2222','root@127.0.0.1']
code="""import json,time,subprocess
from pathlib import Path
p=Path('/var/run/homensai-vpn/status.json');status=json.loads(p.read_text())
marker=subprocess.check_output(['uci','get','homensai_vpn.main.vm_upgrade_marker']).decode().strip()
assert status.get('version')=='0.7.0-alpha5' and 0<=time.time()-status.get('time',0)<35 and marker=='retained'
assert status.get('auto_control',{}).get('requested')=='off'
Path('/tmp/HOMENSAI_VIRTUAL_LAB').touch()
print(json.dumps({'result':'PASS','scope':'Recovery by cold start of preserved isolated QEMU disk','fresh_monitor':True,'version':status['version'],'own_marker_retained':True,'auto_requested':'off','warm_reboot_passed':False}))
"""
end=time.monotonic()+180
while time.monotonic()<end:
 try:
  r=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=12)
  if r.returncode==0:
   result=json.loads(r.stdout);Path('/lab/cache128-cold-restoration.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));break
 except (OSError,ValueError,subprocess.SubprocessError):pass
 time.sleep(3)
else:raise SystemExit('Cold restoration remains unconfirmed')
