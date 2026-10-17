"""Real opkg upgrade/guard acceptance in the marked x86 copy only."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shlex
from serial_clone import require_clone,run,json_command

require_clone()
code=r'''import hashlib,json,os,re,subprocess,time
from pathlib import Path
release=Path('/etc/openwrt_release').read_text()
assert "DISTRIB_TARGET='x86/64'" in release and "DISTRIB_RELEASE='21.02.7'" in release
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
checks=[]
def cmd(args):return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=90)
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append({'name':name,'result':'PASS'})
def rpc(method):return json.loads(cmd(['ubus','-t','15','call','homensai-vpn',method,'{}']))
def protected_hash():
 data=cmd(['uci','export','network'])+cmd(['uci','export','firewall'])+cmd(['ip','-4','route','show','table','main'])
 return hashlib.sha256(data).hexdigest()
baseline=protected_hash()
cmd(['uci','set','homensai_vpn.main.vm_upgrade_marker=retained-alpha7'])
cmd(['uci','set','homensai_vpn.main.telegram_enabled=0'])
cmd(['uci','set','homensai_vpn.main.telegram_token=VIRTUAL_PRIVATE_FIELD_SENTINEL'])
cmd(['uci','set','homensai_vpn.alpha7_retention=server'])
for key,value in {'profile':'wireguard:peer_9999','name':'VM retention fixture','channel':'VM retention','priority':'39','enabled':'0'}.items():
 cmd(['uci','set','homensai_vpn.alpha7_retention.'+key+'='+value])
cmd(['uci','commit','homensai_vpn'])
before=rpc('status');before_seq=before.get('native_history',{}).get('sequence',0)
check('actual-old-agent-before-upgrade',before.get('version')=='0.7.0-alpha5')
private_before=cmd(['uci','get','homensai_vpn.main.telegram_token']).strip()
work=Path('/tmp/homensai-alpha7-package');work.mkdir(mode=0o700,exist_ok=True)
package=work/'candidate.ipk'
cmd(['wget','-q','-O',str(package),'http://10.0.3.2:8088/homensai-auto-vpn_0.7.0-alpha7-1_all.ipk'])
check('candidate-sha256',hashlib.sha256(package.read_bytes()).hexdigest()=='a96aa7f785a78457fec48fadbcfda0c8e40074d72da787846e1b1f8f09e1cea4')
install=subprocess.run(['opkg','install',str(package)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=100)
if install.returncode:
 print('CLONE_INSTALL_ERROR:'+install.stdout.decode(errors='replace')[-2000:]);raise AssertionError('opkg-upgrade')
check('actual-opkg-upgrade',install.returncode==0)
check('private-field-preserved',cmd(['uci','get','homensai_vpn.main.telegram_token']).strip()==private_before)
check('configuration-marker-preserved',cmd(['uci','get','homensai_vpn.main.vm_upgrade_marker']).strip()==b'retained-alpha7')
check('display-name-priority-preserved',cmd(['uci','get','homensai_vpn.alpha7_retention.name']).strip()==b'VM retention fixture' and cmd(['uci','get','homensai_vpn.alpha7_retention.priority']).strip()==b'39')
check('auto-scope-disabled',cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0' and cmd(['uci','get','homensai_vpn.main.native_until']).strip()==b'0')
deadline=time.monotonic()+75;after={}
while time.monotonic()<deadline:
 try:
  after=rpc('status')
  if after.get('version')=='0.7.0-alpha7' and after.get('time',0)>time.time()-90:break
 except (OSError,ValueError,subprocess.SubprocessError):pass
 time.sleep(2)
check('installed-agent-version-and-fresh-status',after.get('version')=='0.7.0-alpha7' and after.get('time',0)>time.time()-90)
check('retained-history-sequence',after.get('native_history',{}).get('sequence',0)>=before_seq)
check('actual-auto-off',after.get('auto_control',{}).get('requested')=='off')
def code_signature():
 p=Path('/usr/lib/homensai-vpn/agent.py');s=p.stat()
 return (hashlib.sha256(p.read_bytes()).hexdigest(),s.st_ino,s.st_mtime_ns,s.st_size)
binary=code_signature();guard_codes=[];blocked_rc=None
try:
 cmd(['uci','set','homensai_vpn.main.native_enabled=1']);cmd(['uci','commit','homensai_vpn'])
 blocked=subprocess.run(['opkg','--force-reinstall','install',str(package)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=100)
 blocked_rc=blocked.returncode;guard_codes=re.findall(r'LIFECYCLE-[A-Z0-9-]+',blocked.stdout.decode(errors='replace'))
 check('unsafe-upgrade-guard-refused',bool(guard_codes))
 check('refused-upgrade-preserves-bytes-inode-mtime',code_signature()==binary)
finally:
 cmd(['uci','set','homensai_vpn.main.native_enabled=0']);cmd(['uci','commit','homensai_vpn'])
# Reassert desired install state after opkg's failed-removal diagnostic.
cmd(['opkg','install',str(package)])
check('network-firewall-main-route-preserved',protected_hash()==baseline)
result={'scope':'real x86 OpenWrt UCI/opkg/procd; private synthetic fixture; no physical router',
 'checks':checks,'passed':len(checks),'version':after.get('version'),'native_multi_hop_certified':False,
 'private_values_exported':False,'blocked_opkg_returncode':blocked_rc,'guard_codes':guard_codes,
 'opkg_exit_code_is_not_acceptance_proof':True,
 'guard_reinstall_scope':'force-reinstall used only in isolated fault test; no force-depends or guard bypass'}
print('CLONE_JSON:'+json.dumps(result))
'''
started=datetime.now(timezone.utc).isoformat()
try:
    result=json_command(code,120)
except RuntimeError as error:
    import re
    output=getattr(error,'output','')
    names=re.findall(r'AssertionError: ([A-Za-z0-9_-]+)',output)
    result={'result':'FAIL','failed_step':names[-1] if names else 'GUEST-COMMAND-FAILED',
            'guard_codes':re.findall(r'LIFECYCLE-[A-Z0-9-]+',output),
            'scope':'isolated x86 copy; no private output exported'}
    Path('/lab/alpha7-package-acceptance.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2));raise SystemExit(1)
result.update(started_at_utc=started,completed_at_utc=datetime.now(timezone.utc).isoformat())
Path('/lab/alpha7-package-acceptance.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
