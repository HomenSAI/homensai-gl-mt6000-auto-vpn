import json
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
code=r"""import json,subprocess,time
from pathlib import Path
def call(args):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20);return r.returncode,r.stdout
rc,opkg=call(['opkg','status','homensai-auto-vpn']);version=next((x.split(': ',1)[1] for x in opkg.decode().splitlines() if x.startswith('Version: ')),None)
rpc_rc,raw=call(['ubus','-t','15','call','homensai-vpn','status','{}'])
try:status=json.loads(raw)
except Exception:status={}
log=Path('/tmp/post-alpha10-package/upgrade-install.log');text=log.read_text(errors='replace') if log.exists() else ''
row={'installed_version':version,'opkg_status_rc':rc,'rpc_status_rc':rpc_rc,'agent_version':status.get('version'),'status_error':status.get('error'),'scan_state':status.get('scan',{}).get('state'),'install_log_exists':log.exists(),'install_log_bytes':log.stat().st_size if log.exists() else 0,'install_log_indicators':{word:word in text.lower() for word in ('error','failed','installed','configuring','upgrading')},'candidate_present':Path('/tmp/post-alpha10-package/0.7.0-alpha10-1.ipk').exists(),'auto_enabled_rc':call(['uci','get','homensai_vpn.main.native_enabled'])[0],'auto_until_rc':call(['uci','get','homensai_vpn.main.native_until'])[0]}
print('CLONE_JSON:'+json.dumps(row))"""
try:r=json_command(code,60)
except Exception as e:
 Path('/lab/post-alpha10-diagnostic-private.log').write_text(getattr(e,'output',''))
 r={'diagnostic_error':type(e).__name__,'private_output_exported':False}
Path('/lab/post-alpha10-diagnosis.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
