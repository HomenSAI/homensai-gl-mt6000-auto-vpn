"""Kill only the proven own monitor in the marked OpenWrt VM; verify procd recovery."""
import json
import os
from pathlib import Path
import signal
import time
from openwrt_acceptance import command,rpc,wait_until,fingerprint

if not Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file() or "DISTRIB_TARGET='x86/64'" not in Path('/etc/openwrt_release').read_text():
    raise SystemExit('REFUSED: virtual lab required')
def instance():
    return json.loads(command(['ubus','call','service','list','{"name":"homensai-vpn"}'])).get('homensai-vpn',{}).get('instances',{}).get('monitor',{})
baseline=fingerprint()
assert rpc('monitor_control',{'enabled':True})['accepted']
old=wait_until(lambda:instance().get('pid'))
argv=Path('/proc/%d/cmdline'%old).read_bytes().split(b'\0')
assert argv[:3]==[b'/usr/bin/python3',b'/usr/lib/homensai-vpn/agent.py',b'daemon']
killed=time.time();os.kill(old,signal.SIGKILL)
new=wait_until(lambda:instance().get('pid') if instance().get('pid') not in (None,old) else False,timeout=35)
wait_until(lambda:rpc('status').get('time',0)>=killed,timeout=35)
assert rpc('inventory')['settings']['native_enabled'] is False
assert fingerprint()==baseline
result={'scope':'Own monitor process crash in marked x86 OpenWrt VM','result':'PASS',
        'process_replaced':new!=old,'fresh_measurements':True,'native_auto_enabled':False,
        'network_firewall_main_route_preserved':True,'recovery_seconds':round(time.time()-killed,2),
        'not_tested':['VPN executor crash','GL.iNet workers','Physical power loss']}
Path('/tmp/homensai-vm-recovery.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
