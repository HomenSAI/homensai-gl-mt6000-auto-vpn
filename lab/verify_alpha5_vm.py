import subprocess,json,time,hashlib,shlex,sys
from pathlib import Path
ssh=['ssh','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/known_hosts','-o','BatchMode=yes','-o','ConnectTimeout=5','-p','2222','root@127.0.0.1']
def remote(command,timeout=120):
    r=subprocess.run(ssh+[command],capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError('VM command failed: '+r.stdout[-1500:]+r.stderr[-700:])
    return r.stdout+r.stderr
release=remote('cat /etc/openwrt_release; test -f /tmp/HOMENSAI_VIRTUAL_LAB')
if "DISTRIB_TARGET='x86/64'" not in release:raise SystemExit('Wrong target; refused')
before=remote('uci export network; uci export firewall')
for local,target in [('/lab/alpha5-final.ipk','/tmp/alpha5-final.ipk'),('/lab/alpha5-tests-final.tar.gz','/tmp/alpha5-tests-final.tar.gz')]:
    payload=Path(local).read_bytes()
    p=subprocess.run(ssh+['cat > '+target],input=payload,capture_output=True,timeout=60)
    if p.returncode:raise SystemExit('VM transfer failed')
install=remote("echo 'a14d1c6bae2be64eb398fa8873b2cabb53589d988655ce93cb93982fbb34cd6a  /tmp/alpha5-final.ipk' | sha256sum -c - && opkg install --force-reinstall /tmp/alpha5-final.ipk",180)
log='' if '--install-only' in sys.argv else remote('mkdir -p /tmp/homensai-alpha5-final && tar -xzf /tmp/alpha5-tests-final.tar.gz -C /tmp/homensai-alpha5-final && cd /tmp/homensai-alpha5-final && python3 -m unittest discover -s router/tests -q',240)
after=remote('uci export network; uci export firewall')
result={'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'Isolated QEMU x86 OpenWrt; no real VPN profiles','package_sha256':'a14d1c6bae2be64eb398fa8873b2cabb53589d988655ce93cb93982fbb34cd6a','install_pass':True,'python_suite_pass':'--install-only' not in sys.argv,'network_firewall_unchanged':before==after,'native_enabled':remote('uci -q get homensai_vpn.main.native_enabled || printf 0').strip(),'test_output':log[-1400:]}
Path('/lab/alpha5-final-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


