"""Revision rollback/reupgrade in isolated clone; old package remains lab-only."""
from datetime import datetime,timezone
import json
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r'''import hashlib,json,subprocess,time
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
def cmd(args):return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=90)
def protected():return hashlib.sha256(cmd(['uci','export','network'])+cmd(['uci','export','firewall'])+cmd(['ip','-4','route','show','table','main'])).hexdigest()
checks=[]
def check(name,value):
 if not value:raise AssertionError(name)
 checks.append({'name':name,'result':'PASS'})
base=protected();cfg=Path('/etc/config/homensai_vpn').read_bytes()
history=Path('/etc/homensai-vpn/native-history.json');oldhistory=history.read_bytes() if history.exists() else None
assert cmd(['uci','changes','homensai_vpn']).strip()==b''
for revision,sha in ((1,'a96aa7f785a78457fec48fadbcfda0c8e40074d72da787846e1b1f8f09e1cea4'),(2,'9f8e952873dd236bbb6470bfffcbcb4e0daeb7501335f6ab2472cab6e19725ac')):
 p=Path('/tmp/homensai-revision-'+str(revision)+'.ipk')
 cmd(['wget','-q','-O',str(p),'http://10.0.3.2:8088/homensai-auto-vpn_0.7.0-alpha7-'+str(revision)+'_all.ipk'])
 check('revision-'+str(revision)+'-hash',hashlib.sha256(p.read_bytes()).hexdigest()==sha)
 args=['opkg']+(['--force-downgrade'] if revision==1 else [])+['install',str(p)]
 cmd(args)
 check('revision-'+str(revision)+'-installed',('Version: 0.7.0-alpha7-'+str(revision)).encode() in cmd(['opkg','status','homensai-auto-vpn']))
 check('revision-'+str(revision)+'-configuration-preserved',Path('/etc/config/homensai_vpn').read_bytes()==cfg)
 check('revision-'+str(revision)+'-history-preserved',(history.read_bytes() if history.exists() else None)==oldhistory)
 check('revision-'+str(revision)+'-auto-off',cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0')
 check('revision-'+str(revision)+'-expected-writer',('SETUP-PENDING-DELTA' in Path('/usr/lib/homensai-vpn/setup_save.lua').read_text())==(revision==2))
check('network-firewall-routing-preserved',protected()==base)
print('CLONE_JSON:'+json.dumps({'result':'PASS','passed':len(checks),'checks':checks,'scope':'isolated x86 package rollback/reupgrade only; old revision is not recommended for deployment','private_values_exported':False}))'''
try:result=json_command(code,120)
except (RuntimeError,TimeoutError) as error:
 import re
 names=re.findall(r'AssertionError: ([A-Za-z0-9_-]+)',getattr(error,'output',''))
 result={'result':'FAIL','failed_step':names[-1] if names else type(error).__name__,'private_values_exported':False}
result['completed_at_utc']=datetime.now(timezone.utc).isoformat()
Path('/lab/alpha7-revision2-rollback.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('result')=='PASS' else 1)
