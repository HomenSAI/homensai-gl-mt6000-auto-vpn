"""Sanitized preflight of the marked virtual clone, never a router."""
import json
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r"""import hashlib,json,subprocess,time
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
def cmd(args):return subprocess.check_output(args,stderr=subprocess.DEVNULL,timeout=20)
def read_rpc(method):
 try:return json.loads(cmd(['ubus','-t','15','call','homensai-vpn',method,'{}']))
 except Exception:return {}
status=read_rpc('status')
package=cmd(['opkg','status','homensai-auto-vpn']).decode()
version=next((line.split(': ',1)[1] for line in package.splitlines() if line.startswith('Version: ')),None)
protected=hashlib.sha256(cmd(['uci','export','network'])+cmd(['uci','export','firewall'])+cmd(['ip','-4','route','show','table','main'])).hexdigest()
keys=['network','firewall','dhcp','wireless']
config_hashes={name:hashlib.sha256((Path('/etc/config')/name).read_bytes()).hexdigest() for name in keys if (Path('/etc/config')/name).is_file()}
row={'result':'PASS','package_version':version,'agent_version':status.get('version'),'status_error':status.get('error'),'profile_count':len(status.get('profiles',[])),'native_state':status.get('native_failover',{}).get('state'),'monitor_stamp':status.get('time'),'guest_time':time.time(),'protected_fingerprint':protected,'protected_config_hashes':config_hashes,'pending_own_uci_empty':cmd(['uci','changes','homensai_vpn']).strip()==b'','namespace_count':len(cmd(['ip','netns','list']).decode().splitlines()),'physical_router_access':False}
Path('/tmp/post-alpha10-preflight.json').write_text(json.dumps(row))
print('CLONE_JSON:'+json.dumps(row))"""
r=json_command(code,90)
Path('/lab/post-alpha10-preflight.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
