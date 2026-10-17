"""Real pending-delta/package regression in marked isolated OpenWrt copy only."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from serial_clone import require_clone, json_command
require_clone()
expected=sys.argv[1]
if not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('PACKAGE-HASH')
code=r'''import hashlib,json,os,subprocess,time,uuid
from pathlib import Path
release=Path('/etc/openwrt_release').read_text()
assert "DISTRIB_TARGET='x86/64'" in release and "DISTRIB_RELEASE='21.02.7'" in release
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
checks=[]
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append({'name':name,'result':'PASS'})
def cmd(args):return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=90)
def protected():return hashlib.sha256(cmd(['uci','export','network'])+cmd(['uci','export','firewall'])+cmd(['ip','-4','route','show','table','main'])).hexdigest()
baseline=protected();config=Path('/etc/config/homensai_vpn');before=config.read_bytes()
assert cmd(['uci','-q','changes','homensai_vpn']).strip()==b''
package=Path('/tmp/homensai-alpha7-revision2.ipk')
cmd(['wget','-q','-O',str(package),'http://10.0.3.2:8088/homensai-auto-vpn_0.7.0-alpha7-2_all.ipk'])
check('exact-package-hash',hashlib.sha256(package.read_bytes()).hexdigest()==EXPECTED_HASH)
cmd(['opkg','install',str(package)])
check('revision-two-installed',b'0.7.0-alpha7-2' in cmd(['opkg','status','homensai-auto-vpn']))
check('auto-disabled',cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0')
check('private-field-retained',cmd(['uci','get','homensai_vpn.main.telegram_token']).strip()==b'VIRTUAL_PRIVATE_FIELD_SENTINEL')
check('names-priority-retained',cmd(['uci','get','homensai_vpn.alpha7_retention.name']).strip()==b'VM retention fixture' and cmd(['uci','get','homensai_vpn.alpha7_retention.priority']).strip()==b'39')
root=Path('/tmp/homensai-setup-test-'+uuid.uuid4().hex[:10]);(root/'config').mkdir(parents=True);(root/'delta').mkdir()
p=root/'config/homensai_vpn';p.write_text("config main 'main'\n option interval '30'\n")
env=dict(os.environ,HOMENSAI_SETUP_TEST_ROOT=str(root))
def writer():return subprocess.run(['lua','/usr/lib/homensai-vpn/setup_save.lua'],input=b'{"main":{"setup_complete":"1"},"servers":[]}',stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=10)
lua="local c=require('uci').cursor("+json.dumps(str(root/'config'))+","+json.dumps(str(root/'delta'))+");assert(c:set('homensai_vpn','main','interval','99'));assert(c:save('homensai_vpn'));os.exit(0)"
cmd(['lua','-e',lua]);pending=root/'delta/homensai_vpn';delta=pending.read_bytes();original=p.read_bytes()
reply=writer()
check('interrupted-save-followup-refused',reply.returncode!=0 and reply.stdout==b'SETUP-PENDING-DELTA')
check('committed-configuration-unchanged',p.read_bytes()==original)
check('operator-pending-delta-preserved',pending.read_bytes()==delta)
check('unrequested-option-not-committed',b'99' not in p.read_bytes() and b'setup_complete' not in p.read_bytes())
# Explicit operator discard in this synthetic fixture, never automatic recovery.
cmd(['lua','-e',"local c=require('uci').cursor("+json.dumps(str(root/'config'))+","+json.dumps(str(root/'delta'))+");assert(c:revert('homensai_vpn'))"])
reply=writer();check('clean-followup-saves',reply.returncode==0 and reply.stdout==b'OK' and b'setup_complete' in p.read_bytes() and b'99' not in p.read_bytes())
# Exercise the actual lifecycle against own VM config only; preserve its pending delta.
old=config.read_bytes();cmd(['uci','set','homensai_vpn.main.interval=99']);pending=Path('/tmp/.uci/homensai_vpn');delta=pending.read_bytes()
try:
 guard=subprocess.run(['python3','/usr/lib/homensai-vpn/lifecycle_guard.py','prepare'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
 check('lifecycle-pending-delta-refused',guard.returncode!=0 and guard.stderr.strip()==b'LIFECYCLE-PENDING-UCI-CHANGES')
 check('lifecycle-keeps-config-and-delta',config.read_bytes()==old and pending.read_bytes()==delta)
 file=Path('/usr/lib/homensai-vpn/setup_save.lua');oldfile=file.read_bytes()
 reinstall=subprocess.run(['opkg','--force-reinstall','install',str(package)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=100)
 check('opkg-pending-upgrade-refused-by-postconditions',b'LIFECYCLE-PENDING-UCI-CHANGES' in reinstall.stdout and file.read_bytes()==oldfile and config.read_bytes()==old and pending.read_bytes()==delta)
finally:cmd(['uci','revert','homensai_vpn'])
cmd(['opkg','install',str(package)])
check('lifecycle-clean-ready',cmd(['python3','/usr/lib/homensai-vpn/lifecycle_guard.py','check']).strip()==b'LIFECYCLE-READY')
check('protected-network-unchanged',protected()==baseline)
print('CLONE_JSON:'+json.dumps({'result':'PASS','scope':'actual x86 OpenWrt libuci and opkg; not physical GL.iNet acceptance','checks':checks,'passed':len(checks),'private_output_exported':False,'package_sha256':EXPECTED_HASH}))'''.replace('EXPECTED_HASH',repr(expected))
try:result=json_command(code,120)
except (RuntimeError,TimeoutError) as error:
 names=re.findall(r'AssertionError: ([A-Za-z0-9_-]+)',getattr(error,'output',''))
 result={'result':'FAIL','failed_step':names[-1] if names else type(error).__name__,'private_output_exported':False}
result['completed_at_utc']=datetime.now(timezone.utc).isoformat()
Path('/lab/alpha7-uci-delta-fixed.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('result')=='PASS' else 1)
