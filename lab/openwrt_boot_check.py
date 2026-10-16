"""Reboot only the private QEMU guest and check actual boot/service continuity."""
import json
from pathlib import Path
import shlex
import subprocess
import time

ssh=['ssh','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/known_hosts','-o','BatchMode=yes','-o','ConnectTimeout=3','-p','2222','root@127.0.0.1']
code="""import json,subprocess,time
from pathlib import Path
service=json.loads(subprocess.check_output(['ubus','call','service','list','{\"name\":\"homensai-vpn\"}']))
p=Path('/var/run/homensai-vpn/status.json')
status=json.loads(p.read_text()) if p.exists() else {}
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':float(Path('/proc/uptime').read_text().split()[0]),'monitor':service.get('homensai-vpn',{}).get('instances',{}).get('monitor',{}).get('running',False),'fresh':bool(status.get('time') and 0<=time.time()-status['time']<35),'version':status.get('version'),'auto':status.get('auto_control',{}).get('requested'),'marker':subprocess.check_output(['uci','get','homensai_vpn.main.vm_upgrade_marker']).decode().strip(),'observed_gaps':status.get('accounting',{}).get('gaps')}))
"""
def sample():
    return json.loads(subprocess.check_output(ssh+['python3 -c '+shlex.quote(code)],stderr=subprocess.DEVNULL,timeout=12))
before=sample();start=time.monotonic()
subprocess.run(ssh+['sync; reboot'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=12)
end=start+180;last={}
while time.monotonic()<end:
    try:
        last=sample()
        if last['boot']!=before['boot'] and last['monitor'] and last['fresh']:
            assert last['marker']=='retained' and last['auto']=='off'
            result={'result':'PASS','scope':'Warm reboot of x86 QEMU OpenWrt guest, not hardware power loss','boot_changed':True,'monitor_autostart_confirmed':True,'fresh_measurements':True,'configuration_marker_preserved':True,'auto_requested':'off','version':last['version'],'host_wall_seconds':round(time.monotonic()-start,2),'guest_uptime_seconds':last['uptime'],'observation_gaps':last['observed_gaps']}
            Path('/lab/warm-reboot-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));break
    except (OSError,ValueError,subprocess.SubprocessError):pass
    time.sleep(3)
else:
    last.pop('boot',None);result={'result':'UNCONFIRMED','scope':'QEMU warm reboot','host_timeout_seconds':180,'last':last};Path('/lab/warm-reboot-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(1)
