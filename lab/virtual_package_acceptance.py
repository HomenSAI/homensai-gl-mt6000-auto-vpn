"""Actual upgrade/rollback in marked isolated x86 guest; never hardware."""
import argparse,json,re,hashlib,textwrap
from pathlib import Path
from datetime import datetime,timezone
from serial_clone import require_clone,json_command
require_clone()
p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--sha256',required=True);p.add_argument('--dashboard',type=int,required=True);p.add_argument('phase',choices=('upgrade','rollback','reupgrade','verify'));p.add_argument('--status',action='store_true');a=p.parse_args()
if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-alpha[0-9]+-[0-9]+',a.version) or not re.fullmatch('[a-f0-9]{64}',a.sha256) or not 16<=a.dashboard<=999:raise ValueError('PACKAGE-CANDIDATE-BOUNDS')
version=a.version
sha=a.sha256
agent=version.rsplit('-',1)[0]
code=r"""import hashlib,json,subprocess,time,re
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
checks=[];step='preflight';last_command=None;last_returncode=None;work=Path('/tmp/candidate-package-'+__VERSION__);work.mkdir(mode=0o700,exist_ok=True)
def cmd(args,timeout=35):
 global last_command,last_returncode
 last_command=str(args[0]);last_returncode=None
 result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=timeout);last_returncode=result.returncode
 if result.returncode:raise RuntimeError('GUEST-COMMAND-FAILED')
 return result.stdout
def check(name,condition):
 global step
 step=name
 if not condition:raise AssertionError(name)
 checks.append({'name':name,'result':'PASS'})
 (work/(__PHASE__+'-progress.json')).write_text(json.dumps({'state':'RUNNING','step':step,'passed':len(checks)}))
def rpc(method,args=None):return json.loads(cmd(['ubus','-t','30','call','homensai-vpn',method,json.dumps(args or {})]))
def protected():return hashlib.sha256(cmd(['uci','export','network'])+cmd(['uci','export','firewall'])+cmd(['ip','-4','route','show','table','main'])).hexdigest()
def live():
 try:return rpc('status')
 except Exception:return {}
base=protected();config=Path('/etc/config/homensai_vpn').read_bytes()
check('preflight-no-pending-uci',cmd(['uci','changes','homensai_vpn']).strip()==b'')
check('preflight-auto-disabled',cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0')
if __PHASE__!='verify':
 package=work/(__VERSION__+'.ipk');step='local-asset-download'
 cmd(['wget','-q','-O',str(package),'http://10.0.3.2:8088/homensai-auto-vpn_'+__VERSION__+'_all.ipk'])
 check('candidate-sha256',hashlib.sha256(package.read_bytes()).hexdigest()==__SHA__)
 step='opkg-install'
 args=['opkg']+(['--force-downgrade'] if __PHASE__=='rollback' else ['--force-reinstall'] if __PHASE__=='reupgrade' else [])+['install',str(package)]
 with (work/(__PHASE__+'-install.log')).open('wb') as log:
  result=subprocess.run(args,stdout=log,stderr=log,timeout=90)
 check('actual-opkg-'+__PHASE__,result.returncode==0)
check('installed-version',('Version: '+__VERSION__).encode() in cmd(['opkg','status','homensai-auto-vpn']))
check('own-config-preserved',Path('/etc/config/homensai_vpn').read_bytes()==config)
check('protected-network-firewall-preserved',protected()==base)
check('auto-stays-off',cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0' and cmd(['uci','get','homensai_vpn.main.native_until']).strip()==b'0')
step='fresh-agent-wait';until=time.monotonic()+60;status={}
while time.monotonic()<until:
 status=live()
 if status.get('version')==__AGENT__ and not status.get('error') and 0<=time.time()-status.get('time',0)<90:break
 time.sleep(1)
check('fresh-upgraded-agent',status.get('version')==__AGENT__ and not status.get('error') and 0<=time.time()-status.get('time',0)<90)
instances=json.loads(cmd(['ubus','call','service','list','{"name":"homensai-vpn"}'])).get('homensai-vpn',{}).get('instances',{})
check('actual-procd-monitor',instances.get('monitor',{}).get('running') is True)
menu=json.loads(Path('/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text());view=menu['admin/services/homensai-vpn']['action']['path']
check('actual-selected-ui-file',Path('/www/luci-static/resources/view/'+view+'.js').is_file())
if True:
 check('actual-candidate-ui',view=='homensai-vpn/dashboard'+str(__DASHBOARD__))
 queued=rpc('scan');check('actual-scan-id-ack',queued.get('queued') is True and re.fullmatch('[a-f0-9]{32}',queued.get('request_id','')) is not None)
 step='scan-completion-wait';until=time.monotonic()+45
 while time.monotonic()<until:
  status=live();scan=status.get('scan',{})
  if scan.get('request_id')==queued['request_id'] and scan.get('state') in ('COMPLETED','FAILED'):break
  time.sleep(1)
 check('actual-correlated-scan-completion',scan.get('request_id')==queued['request_id'] and scan.get('state')=='COMPLETED' and scan.get('measurement_request_id')==queued['request_id'])
 check('no-fake-active-profiles',type(scan.get('checked')) is int and scan['checked']>=0)
 step='native-start-refusal';revision=live().get('auto_control',{}).get('control_revision');check('live-control-revision',isinstance(revision,str) and re.fullmatch('[a-f0-9]{32}',revision) is not None)
 refused=rpc('native_start',{'control_revision':revision});check('generic-board-auto-refused',refused.get('accepted') is False and bool(refused.get('blockers')) and 'CONTROL-REVISION-STALE' not in refused['blockers'])
check('final-protected-state-preserved',protected()==base)
result={'result':'PASS','phase':__PHASE__,'package_version':__VERSION__,'package_sha256':__SHA__,'passed':len(checks),'checks':checks,'agent_version':status.get('version'),'protected_unchanged':True,'private_values_exported':False,'scope':'actual isolated x86 opkg/RPC/procd/UI files; no GL.iNet native or LAN acceptance','physical_router_access':False}
""".replace('__VERSION__',repr(version)).replace('__SHA__',repr(sha)).replace('__PHASE__',repr(a.phase)).replace('__AGENT__',repr(agent)).replace('__DASHBOARD__',repr(a.dashboard))
status_path='/tmp/candidate-package-'+version+'/'+a.phase+'-result.json'
progress_path='/tmp/candidate-package-'+version+'/'+a.phase+'-progress.json'
if a.status:
 query="import json;from pathlib import Path;p=Path("+repr(status_path)+");q=Path("+repr(progress_path)+");r=json.loads(p.read_text()) if p.exists() else json.loads(q.read_text()) if q.exists() else {'state':'STARTING'};print('CLONE_JSON:'+json.dumps(r))"
 r=json_command(query,30)
else:
 prefix="import json,time,subprocess,hashlib;from pathlib import Path\n"
 failure="\nexcept Exception as error:\n result={'result':'FAIL','phase':"+repr(a.phase)+",'failed_step':globals().get('step','BOOTSTRAP'),'exception_type':type(error).__name__,'last_command':globals().get('last_command'),'last_returncode':globals().get('last_returncode'),'passed':len(globals().get('checks',[])),'physical_router_access':False,'private_values_exported':False}\n"
 finish="\nresult['guest_completed_at']=time.time()\nPath("+repr(status_path)+").write_text(json.dumps(result))\nprint('CLONE_JSON:'+json.dumps(result))\n"
 payload=prefix+'try:\n'+textwrap.indent(code,' ')+failure+finish
 compile(payload,'<post-alpha10-guest>','exec')
 digest=hashlib.sha256(payload.encode()).hexdigest();name='post-alpha10-'+a.phase+'-'+digest[:16]+'.py'
 source=Path('/lab/assets')/name
 if source.exists():assert source.read_bytes()==payload.encode()
 else:source.write_bytes(payload.encode())
 launch="""import json,hashlib,subprocess,sys
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
p=Path('/tmp/"""+name+"""');r=subprocess.run(['wget','-q','-O',str(p),'http://10.0.3.2:8088/"""+name+"""'],timeout=15);assert r.returncode==0
assert hashlib.sha256(p.read_bytes()).hexdigest()=="""+repr(digest)+"""
root=Path('/tmp/candidate-package-"""+version+"""');root.mkdir(mode=0o700,exist_ok=True)
job=root/'active-job.json'
if job.exists():
 old=json.loads(job.read_text());cmd=Path('/proc/'+str(old.get('pid'))+'/cmdline')
 assert not cmd.exists() or old.get('source','').encode() not in cmd.read_bytes(),'POST-JOB-BUSY'
result=root/"""+repr(a.phase+'-result.json')+""";assert not result.exists(),'POST-RESULT-EXISTS'
log=(root/"""+repr(a.phase+'-job.log')+""").open('wb');child=subprocess.Popen([sys.executable,str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);log.close()
row={'state':'STARTED','phase':"""+repr(a.phase)+""",'pid':child.pid,'source':str(p),'source_sha256':"""+repr(digest)+""",'physical_router_access':False};job.write_text(json.dumps(row));print('CLONE_JSON:'+json.dumps(row))"""
 r=json_command(launch,30)
r['host_observed_at_utc']=datetime.now(timezone.utc).isoformat()
Path('/lab/candidate-'+version+'-'+a.phase+('-start' if not a.status else '-latest')+'.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(1 if r.get('result')=='FAIL' else 0)
