"""Bounded warm-boot test of the isolated copy; never exports boot identity."""
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from serial_clone import require_clone,run,json_command

require_clone()
code='''import json,subprocess,time
from pathlib import Path
service=json.loads(subprocess.check_output(['ubus','call','service','list','{"name":"homensai-vpn"}']))
p=Path('/var/run/homensai-vpn/status.json');status=json.loads(p.read_text()) if p.exists() else {}
config=subprocess.check_output(['sha256sum','/etc/config/homensai_vpn']).decode().split()[0]
print('CLONE_JSON:'+json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'config_hash':config,'uptime':float(Path('/proc/uptime').read_text().split()[0]),'monitor':service.get('homensai-vpn',{}).get('instances',{}).get('monitor',{}).get('running',False),'fresh':bool(status.get('time') and 0<=time.time()-status['time']<90),'version':status.get('version'),'auto':status.get('auto_control',{}).get('requested')}))'''
before=json_command(code);started=datetime.now(timezone.utc).isoformat();start=time.monotonic()
run('( sleep 2; sync; reboot ) >/tmp/clone-reboot.log 2>&1 </dev/null & echo REBOOT_REQUESTED',5)
print('WARM-REBOOT-REQUESTED: isolated copy only',flush=True)
last={};attempts=0;result=None
while time.monotonic()-start<120:
    attempts+=1
    try:
        current=json_command(code,3)
        last={key:value for key,value in current.items() if key not in ('boot','config_hash')}
        if current['boot']!=before['boot'] and current['monitor'] and current['fresh']:
            result=dict(result='PASS',boot_changed=True,configuration_preserved=current['config_hash']==before['config_hash'],
                        monitor_autostart=True,fresh_measurements=True,auto_off=current['auto']=='off',last=last)
            break
    except (OSError,ValueError,RuntimeError,TimeoutError):pass
    time.sleep(2)
if result is None:result=dict(result='UNCONFIRMED',last=last,host_deadline_seconds=120)
result.update(scope='direct-kernel cold-recovered x86 copy; not original GRUB or physical power loss',
              started_at_utc=started,completed_at_utc=datetime.now(timezone.utc).isoformat(),
              host_wall_seconds=round(time.monotonic()-start,3),attempts=attempts,original_guest_untouched=True)
Path('/lab/alpha7-warm-reboot.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
raise SystemExit(0 if result['result']=='PASS' and result['configuration_preserved'] and result['auto_off'] else 1)
