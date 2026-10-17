"""Inspect and test disposable namespace capability in the isolated copy."""
import json
from pathlib import Path
from serial_clone import require_clone,run,json_command

require_clone()
run('set -eu; . /etc/openwrt_release; [ "$DISTRIB_TARGET" = "x86/64" ]; [ "$DISTRIB_RELEASE" = "21.02.7" ]; : > /tmp/HOMENSAI_VIRTUAL_LAB',5)
code='''import gzip,json,shutil,subprocess,uuid
from pathlib import Path
tools={name:bool(shutil.which(name)) for name in ('ip','wg','openvpn','openssl','conntrack','nft','iptables','ip6tables')}
config={}
if Path('/proc/config.gz').exists():
 for line in gzip.open('/proc/config.gz','rt'):
  for name in ('CONFIG_NET_NS','CONFIG_TUN','CONFIG_WIREGUARD','CONFIG_VETH','CONFIG_IPV6'):
   if line.startswith(name+'=') or line.strip()=='# '+name+' is not set':config[name]=line.strip()
name='hsalpha7-'+uuid.uuid4().hex[:8]
result={'tools':tools,'kernel_config':config,'tun_device':Path('/dev/net/tun').exists()}
if tools['ip']:
 added=subprocess.run(['ip','netns','add',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 result.update(netns_add_rc=added.returncode,netns_error=added.stderr.decode(errors='replace')[:200])
 if added.returncode==0:
  removed=subprocess.run(['ip','netns','delete',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  result['netns_delete_rc']=removed.returncode
print('CLONE_JSON:'+json.dumps(result))'''
result=json_command(code,15)
result.update(scope='OpenWrt x86 isolated copy; no physical router or host namespace changes')
Path('/lab/alpha7-kernel-probe.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
