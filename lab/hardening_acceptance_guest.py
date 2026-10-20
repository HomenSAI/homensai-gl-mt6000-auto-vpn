"""Actual recovery/guard checks ONLY in a deliberately marked disposable x86 VM."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
import uuid

p=argparse.ArgumentParser();p.add_argument('--version',required=True);args=p.parse_args()
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
sys.path.insert(0,'/usr/lib/homensai-vpn')
import agent
import native_switch as native

checks=[]
def command(argv,timeout=30):
    return subprocess.check_output(argv,stderr=subprocess.DEVNULL,timeout=timeout)
def rpc(method,arguments=None):
    if method=='native_start' and arguments is None:
        import auto_control
        arguments={'control_revision':auto_control.public_status()['control_revision']}
    return json.loads(command(['ubus','-t','25','call','homensai-vpn',method,json.dumps(arguments or {})]))
def check(name,ok):
    if not ok:raise AssertionError(name)
    checks.append(name)
def protected():
    return hashlib.sha256(command(['uci','export','network'])+command(['uci','export','firewall'])+command(['ip','-4','route','show','table','main'])).hexdigest()

baseline=protected();journal=Path('/etc/homensai-vpn/native-transaction.json')
saved=journal.read_bytes() if journal.exists() else None
guard=None;guard_owned=False;timers=[];lock=None;service_stopped=False
instances=json.loads(command(['ubus','call','service','list','{"name":"homensai-vpn"}'])).get('homensai-vpn',{}).get('instances',{})
was_running=any(row.get('running') is True for row in instances.values())
result={'state':'RUNNING','scope':'actual disposable x86 RPC/lifecycle/nft/procd; no vendor or hardware acceptance'}
try:
    check('exact-agent-version',agent.VERSION==args.version)
    check('native-auto-off',command(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0')
    command(['/etc/init.d/homensai-vpn','stop']);service_stopped=True
    lock=open('/var/run/homensai-vpn/native.lock','a')
    # procd Stop acknowledges before the configured 70s native termination
    # window has necessarily finished. Never corrupt a live owner's journal.
    stopped_deadline=time.monotonic()+80
    while True:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
        except BlockingIOError:
            if time.monotonic()>=stopped_deadline:raise
            time.sleep(1)
    check('native-supervisor-stopped-and-lock-owned',True)
    for payload in ({'enabled':'false'},{'enabled':False,'extra':True}):
        answer=rpc('monitor_control',payload)
        check('malformed-monitor-control-'+str(len(checks)),answer.get('accepted') is False)
    journal.write_text('{}')
    answer=rpc('monitor_control',{'enabled':False})
    check('corrupt-journal-refuses-monitor-stop',answer.get('accepted') is False and answer.get('code')=='MONITOR-JOURNAL-UNVERIFIED')
    answer=rpc('native_start')
    check('corrupt-journal-refuses-auto',answer.get('accepted') is False and 'JOURNAL-INTEGRITY-FAILED' in answer.get('blockers',[]))
    refused=subprocess.run([sys.executable,'/usr/lib/homensai-vpn/lifecycle_guard.py','check'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
    check('actual-package-lifecycle-refuses-empty-journal',refused.returncode!=0)
    row={'phase':'RELEASE-PENDING','before':['a','b'],'after':['b','a'],'hash':'a'*64}
    journal.write_text(json.dumps({'schema':1,'data':row,'sha256':native.digest(row)}))
    answer=rpc('monitor_control',{'enabled':False})
    check('release-pending-refuses-monitor-stop',answer.get('accepted') is False)
    check('release-pending-refuses-auto',rpc('native_start').get('accepted') is False)
    if saved is None:journal.unlink()
    else:journal.write_bytes(saved)
    request={'jsonrpc':'2.0','id':1,'method':'call','params':['0'*32,'homensai-vpn','native_start',{}]}
    req=urllib.request.Request('http://127.0.0.1/ubus',json.dumps(request).encode(),{'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=10) as response:answer=json.loads(response.read(8192))
        denied=bool(answer.get('error')) or isinstance(answer.get('result'),list) and answer['result'][0]!=0
    except urllib.error.HTTPError as error:denied=error.code in (401,403)
    check('expired-session-cannot-start-auto',denied)
    with tempfile.TemporaryDirectory(prefix='hs-nft-hardening-') as directory:
        native.RUNTIME=Path(directory);native.TABLE='hs_recovery_'+uuid.uuid4().hex;native.GUARD_RELEASE_SECONDS=10
        guard=native.Linux()
        check('isolated-guard-table-initially-absent',not guard.guard_exists())
        guard_owned=True
        # Save only the independently started process returned by this exact call.
        popen=native.subprocess.Popen
        def spawn(*a,**kw):
            child=popen(*a,**kw)
            # subprocess.run uses this same module-level factory too. Track
            # only our independently session-owned cleanup shells, never nft
            # commands whose PID is not their process-group identity.
            argv=a[0] if a else kw.get('args',[])
            if kw.get('start_new_session') is True and argv[:2]==['sh','-c'] and argv[2].startswith('sleep '):timers.append(child)
            return child
        native.subprocess.Popen=spawn
        guard.guard()
        installed=command(['nft','list','table','inet',native.TABLE]).decode()
        check('actual-nft-timeout-set-installed',guard.guard_exists() and '"br-lan"' in installed and 'timeout' in installed)
        timer=timers.pop();os.killpg(timer.pid,signal.SIGKILL);timer.wait(timeout=5)
        time.sleep(11)
        table=command(['nft','list','table','inet',native.TABLE]).decode()
        check('kernel-releases-element-after-cleanup-process-loss','"br-lan"' not in table)
        guard.unguard();check('verified-guard-removal',not guard.guard_exists())
        # An old cleanup timer must never delete a replacement VPN-only guard.
        guard.guard();guard.guard(['eth0'])
        replacement=command(['nft','list','table','inet',native.TABLE])
        time.sleep(11)
        check('old-timer-preserves-replacement-guard',guard.guard_exists() and command(['nft','list','table','inet',native.TABLE])==replacement)
        guard.unguard()
    check('native-auto-still-off',command(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0')
    check('network-firewall-main-route-preserved',protected()==baseline)
    result.update(state='PASS',checks=checks,passed=len(checks))
except Exception as error:
    result.update(state='FAIL',checks=checks,passed=len(checks),exception_type=type(error).__name__,
                  failed_check=str(error) if isinstance(error,AssertionError) else 'VM-HARDENING-ERROR')
finally:
    try:
        if saved is None:
            try:journal.unlink()
            except FileNotFoundError:pass
        else:journal.write_bytes(saved)
        result['journal_restored']=True
    except Exception:result.update(state='FAIL',journal_restored=False)
    if guard is not None and guard_owned:
        try:guard.unguard();result['guard_cleanup_confirmed']=True
        except Exception:result.update(state='FAIL',guard_cleanup_confirmed=False)
    for child in timers:
        try:
            if child.poll() is None:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=5)
        except Exception:result.update(state='FAIL',timer_cleanup_confirmed=False)
    if 'popen' in globals():native.subprocess.Popen=popen
    if lock is not None:lock.close()
    if service_stopped and was_running:
        try:command(['/etc/init.d/homensai-vpn','start']);result['own_service_restart_requested']=True
        except Exception:result.update(state='FAIL',own_service_restart_requested=False)
    result['completed_at']=time.time()
    Path('/tmp/homensai-hardening-result.json').write_text(json.dumps(result))
    print(json.dumps(result))
raise SystemExit(0 if result['state']=='PASS' else 1)
