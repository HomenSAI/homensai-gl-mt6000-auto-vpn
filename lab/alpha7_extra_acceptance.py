"""Extra actual checks of the alpha7 additions in the marked isolated x86 guest; never hardware.

Run after virtual_package_acceptance.py upgrade. Uses only synthetic values. A synthetic Telegram token is
stored and deleted again; it is never sent anywhere (the guest has no network and reports stay disabled)."""
import json
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r"""import json,re,subprocess,time
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
checks=[]
def run(args,timeout=40):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=timeout);return r.returncode,r.stdout
def rpc(method,payload=None):
 rc,out=run(['ubus','-t','30','call','homensai-vpn',method,json.dumps(payload or {})]);return rc,(json.loads(out) if out.strip() else {})
def check(name,condition):
 checks.append({'name':name,'result':'PASS' if condition else 'FAIL'})
 if not condition:raise AssertionError(name)
rc,status=rpc('status')
check('status-agent-version',status.get('version')=='0.8.0-alpha7')
check('status-package-version-from-opkg',status.get('package')=='0.8.0-alpha7-1')
rc,listing=run(['ubus','list','homensai-vpn']);rc2,verbose=run(['ubus','-v','list','homensai-vpn'])
text=verbose.decode()
for method in ('native_return','telegram_forget','native_confirm'):check('rpc-registered-'+method,'"'+method+'"' in text)
check('native-confirm-signature-has-trial','"trial":"String"' in text.replace(' ',''))
p=Path('/usr/sbin/homensai-vpn-emergency')
check('emergency-helper-installed-executable',p.is_file() and (p.stat().st_mode&0o111)!=0)
rc,out=run(['/usr/sbin/homensai-vpn-emergency','show'])
check('emergency-show-readonly-runs',rc==0 and b'owned guard table' in out)
rc,answer=rpc('native_return')
check('operator-return-refused-without-held-reserve',answer.get('accepted') is False and answer.get('code') in ('RETURN-NOT-APPLICABLE','JOURNAL-UNVERIFIED'))
rc,answer=rpc('native_confirm',{'tx':'a'*32,'exit_ipv4':'9.9.9.9','dns_ok':True,'https_ok':True,'trial':'b'*32})
check('confirmation-without-pending-transaction-refused',rc!=0 or answer.get('accepted') is not True)
# Token lifecycle with a synthetic value.
token='123456789:'+'A'*35
rc,saved=rpc('setup_telegram',{'token':token,'chat':'@example_channel','enabled':False,'interval':60,'schedule':'interval','hour':7,'weekly':False,'monthly':False})
check('synthetic-token-saved',saved.get('saved') is True)
rc,inventory=rpc('inventory')
check('token-reported-only-as-configured-flag',inventory.get('settings',{}).get('telegram_configured') is True and token not in json.dumps(inventory))
rc,forgotten=rpc('telegram_forget')
check('token-deleted',forgotten.get('saved') is True)
rc,inventory=rpc('inventory')
check('token-gone-and-reports-off',inventory.get('settings',{}).get('telegram_configured') is False and inventory.get('settings',{}).get('telegram_enabled') is False)
rc,config=run(['uci','show','homensai_vpn'])
check('token-absent-from-config',b'telegram_token' not in config and token.encode() not in config)
rc,again=rpc('telegram_forget')
second='saved' if again.get('saved') is True else 'refused:'+str(again.get('code'))
rc,pending=run(['uci','-q','changes','homensai_vpn'])
check('no-pending-uci-delta-left',pending.strip()==b'')
print('CLONE_JSON:'+json.dumps({'result':'PASS','passed':len(checks),'checks':checks,'second_forget_without_token':second,'scope':'actual isolated x86 RPC/UCI/files; synthetic token; no GL.iNet native or LAN acceptance','physical_router_access':False}))"""
r=json_command(code,90)
r['host_observed_at']=__import__('time').time()
Path('/lab/alpha7-extra-acceptance.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r.get('result')=='PASS' else 1)
