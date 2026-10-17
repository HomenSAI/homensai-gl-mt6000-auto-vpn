"""Destructive only to the marked disposable x86 guest's own package; recover each trial."""
import hashlib,json,os,signal,subprocess,time
from pathlib import Path
ROOT=Path('/tmp/homensai-upgrade-interruption')
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
ROOT.mkdir(mode=0o700,exist_ok=False)

def cmd(args,timeout=30):
    return subprocess.check_output(args,stderr=subprocess.DEVNULL,timeout=timeout)

def download(name,sha):
    target=ROOT/name
    cmd(['wget','-q','-O',str(target),'http://10.0.3.2:8088/'+name],20)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==sha,'ASSET-HASH'
    return target

def protected():
    return hashlib.sha256(cmd(['uci','export','network'])+cmd(['uci','export','firewall'])+cmd(['ip','-4','route','show','table','main'])).hexdigest()

manifest=json.loads(cmd(['wget','-q','-O','-','http://10.0.3.2:8088/interruption-manifest.json'],20))
assert manifest['package_version']=='0.8.0-alpha1-4'
assert cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0'
original_config=Path('/etc/config/homensai_vpn').read_bytes();baseline=protected()
recovery=download('homensai-auto-vpn_0.8.0-alpha1-4_all.ipk',manifest['recovery_sha256'])
rows=[];result={'state':'RUNNING','scope':'controlled opkg lifecycle interruption; not physical power loss or mid-flash atomicity','physical_router_access':False}

def publish():
    result['trials']=rows;result['updated_at']=time.time();(ROOT/'status.json').write_text(json.dumps(result))

try:
    for trial in manifest['stages']:
        stage=trial['stage'];assert stage in ('preinst','postinst','before_rpc_reload')
        candidate=download(trial['filename'],trial['sha256'])
        ready=ROOT/'ready'
        if ready.exists():ready.unlink()
        row={'stage':stage,'state':'RUNNING','started_at':time.time(),'instrumented_sha256':trial['sha256']};rows.append(row);publish()
        with (ROOT/(stage+'.log')).open('wb') as log:
            child=subprocess.Popen(['opkg','--force-reinstall','install',str(candidate)],stdout=log,stderr=log,start_new_session=True)
            try:
                until=time.monotonic()+60
                while time.monotonic()<until and child.poll() is None:
                    if ready.exists() and ready.read_text()==stage:break
                    time.sleep(.25)
                assert ready.exists() and ready.read_text()==stage and child.poll() is None,'CHECKPOINT-NOT-REACHED'
                parts=Path('/proc/'+str(child.pid)+'/cmdline').read_bytes().split(bytes([0]))
                assert b'opkg' in parts and str(candidate).encode() in parts and os.getpgid(child.pid)==child.pid,'OWNED-PROCESS-IDENTITY'
                os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5);row['interrupted']=True
            finally:
                if child.poll() is None:
                    os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
                restored=subprocess.run(['opkg','--force-reinstall','install',str(recovery)],stdout=log,stderr=log,timeout=120)
                row['recovery_exit']=restored.returncode
        assert row.get('interrupted') is True and row['recovery_exit']==0,'RECOVERY-FAILED'
        assert Path('/etc/config/homensai_vpn').read_bytes()==original_config,'CONFIG-CHANGED'
        assert protected()==baseline,'PROTECTED-STATE-CHANGED'
        until=time.monotonic()+90;fresh=False
        while time.monotonic()<until:
            try:
                status=json.loads(cmd(['ubus','-t','10','call','homensai-vpn','status'],15))
                fresh=status.get('version')=='0.8.0-alpha1' and 0<=time.time()-status.get('time',0)<90
                if fresh:break
            except (OSError,ValueError,subprocess.SubprocessError):pass
            time.sleep(1)
        assert fresh,'RESTORED-MONITOR-NOT-FRESH'
        assert cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0','AUTO-ENABLED'
        row.update(state='PASS',configuration_preserved=True,protected_unchanged=True,fresh_monitor=True,auto_off=True,completed_at=time.time());publish()
    result['state']='PASS'
except Exception as error:
    result.update(state='FAIL',exception_type=type(error).__name__,code=str(error) if isinstance(error,AssertionError) else 'LAB-COMMAND-FAILED')
finally:
    result['completed_at']=time.time();publish()
print(json.dumps(result))
raise SystemExit(0 if result['state']=='PASS' else 1)
