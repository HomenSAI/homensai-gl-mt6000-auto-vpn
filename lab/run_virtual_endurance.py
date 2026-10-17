"""Host-deadline observer of marked isolated QEMU; no physical router operations."""
import argparse,hashlib,json,os,re,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from endurance_state import sample_errors,verdict,slept
CONTAINER='homensai-vpn-qemu-alpha7'

def utc():return datetime.now(timezone.utc).isoformat()
def atomic(path,value):
    pending=path.with_suffix('.pending')
    with pending.open('w',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(pending,path)

def inspect():
    row=json.loads(subprocess.check_output(['docker','inspect',CONTAINER],timeout=20))[0]
    if row['HostConfig']['NetworkMode']!='none' or row['HostConfig']['Privileged'] or row['Mounts']:raise ValueError('CLONE-ISOLATION')
    return row['Id']

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--duration',type=int,default=43200);p.add_argument('--interval',type=int,default=60);p.add_argument('--smoke',action='store_true');p.add_argument('--leave-running',action='store_true');a=p.parse_args()
    repo=a.repo.resolve();out=a.out.resolve()
    if not out.is_relative_to((repo/'private').resolve()) or out.exists():raise ValueError('PRIVATE-FRESH-OUTPUT')
    if not 30<=a.interval<=300 or not (60<=a.duration<=180 if a.smoke else 43200<=a.duration<=86400):raise ValueError('ENDURANCE-BOUNDS')
    expected=json.loads(a.manifest.read_text());source=expected['source']
    if not re.fullmatch('[a-f0-9]{40}',source) or subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()!=source:raise ValueError('ENDURANCE-SOURCE')
    for name in ('run_virtual_endurance.py','endurance_state.py','virtual_endurance_watchdog.py'):
        committed=subprocess.check_output(['git','show',source+':lab/'+name],cwd=repo)
        if hashlib.sha256(committed).digest()!=hashlib.sha256(Path(__file__).with_name(name).read_bytes()).digest():raise ValueError('ENDURANCE-RUNNER-SOURCE-MISMATCH')
    identity=inspect();out.mkdir(parents=True)
    lease=repo/'.git/handoff/virtual-endurance.lock';lease.parent.mkdir(exist_ok=True)
    fd=os.open(lease,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,str(os.getpid()).encode());os.close(fd)
    started=time.monotonic();baseline=None;state={'state':'RUNNING','scope':'virtual x86 monitor endurance; no real provider/native/LAN acceptance','source':source,'package_sha256':expected['package_sha256'],'version':expected['version'],'duration_seconds':a.duration,'interval_seconds':a.interval,'started_at_utc':utc(),'deadline_epoch':time.time()+a.duration,'pid':os.getpid(),'container_id':identity,'samples':0,'failures':0,'gaps':0,'max_rss_bytes':0,'smoke':a.smoke,'physical_router_access':False,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    atomic(out/'status.json',state)
    # Independent process checks terminal cleanup or pauses the same clone after deadline/producer exit.
    watch=Path(__file__).with_name('virtual_endurance_watchdog.py')
    flags=0x08000000 if os.name=='nt' else 0
    with (out/'watchdog.log').open('wb') as log:
        subprocess.Popen([sys.executable,str(watch),'--out',str(out),'--duration',str(a.duration+120),'--leave-running' if a.leave_running else '--pause'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,start_new_session=os.name!='nt')
    code=r"""import hashlib,json,subprocess,time
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
probe=__PROBE__
print(json.dumps(json_command(probe,45)))"""
    probe=r"""import hashlib,json,os,subprocess,time
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
s=json.loads(Path('/var/run/homensai-vpn/status.json').read_text())
def cmd(args):return subprocess.check_output(args,stderr=subprocess.DEVNULL,timeout=5)
protected=hashlib.sha256(cmd(['uci','export','network'])+cmd(['uci','export','firewall'])+cmd(['ip','-4','route','show','table','main'])).hexdigest()
pids=[]
for entry in list(Path('/proc').iterdir())[:256]:
 if not entry.name.isdigit():continue
 try:
  parts=(entry/'cmdline').read_bytes().split(bytes([0]))
  if b'/usr/lib/homensai-vpn/agent.py' in parts and b'daemon' in parts:
   rss=next((int(line.split()[1])*1024 for line in (entry/'status').read_text().splitlines() if line.startswith('VmRSS:')),0);pids.append(rss)
 except OSError:pass
files=__FILES__
row={'version':s.get('version'),'age':time.time()-s.get('time',0),'error':s.get('error'),'guest_time':time.time(),'profile_count':len(s.get('profiles',[])),'monitor_instances':len(pids),'rss_bytes':max(pids or [0]),'protected':protected,'own_config':hashlib.sha256(Path('/etc/config/homensai_vpn').read_bytes()).hexdigest(),'auto_off':cmd(['uci','get','homensai_vpn.main.native_enabled']).strip()==b'0','code_hashes':{name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in files}}
print('CLONE_JSON:'+json.dumps(row))""".replace('__FILES__',repr(list(expected['code_hashes'])))
    code=code.replace('__PROBE__',repr(probe));last=None;stopped=False
    try:
        while time.monotonic()-started<a.duration:
            if (out/'STOP').exists():stopped=True;break
            at=time.monotonic();errors=[]
            now=(time.time(),at)
            if last is not None and (at-last[1]>a.interval+60 or slept(last,now,a.interval)):state['gaps']+=1
            last=now
            try:
                if inspect()!=identity:raise ValueError('CLONE-IDENTITY-CHANGED')
                reply=subprocess.run(['docker','exec','-i',CONTAINER,'python3','-'],input=code,capture_output=True,text=True,timeout=60,check=True)
                sample=json.loads(reply.stdout);errors=sample_errors(sample,expected,baseline)
                if baseline is None and not errors:baseline=sample
                state['max_rss_bytes']=max(state['max_rss_bytes'],sample.get('rss_bytes',0));state['last_sample']=sample
            except Exception as error:errors=['OBSERVATION-'+type(error).__name__]
            state['samples']+=1;state['failures']+=bool(errors);state['elapsed_seconds']=round(time.monotonic()-started,3);state['updated_at_utc']=utc()
            with (out/'events.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps({'at_utc':utc(),'sample':state['samples'],'errors':errors})+'\n')
            atomic(out/'status.json',state)
            remaining=min(a.interval-(time.monotonic()-at),a.duration-(time.monotonic()-started))
            while remaining>0 and not (out/'STOP').exists():time.sleep(min(1,remaining));remaining=min(a.interval-(time.monotonic()-at),a.duration-(time.monotonic()-started))
        state['elapsed_seconds']=round(time.monotonic()-started,3)
        state['state']=verdict(state['elapsed_seconds'],a.duration,state['samples'],state['failures'],state['gaps'],a.interval,stopped)
        if state['state']=='PASS':state['state']='MEASUREMENTS-PASS'
    except Exception as error:state.update(state='FAIL',runner_error=type(error).__name__)
    finally:
        cleanup={'scope':'marked isolated clone only','leave_running':a.leave_running,'at_utc':utc(),'confirmed':False}
        try:
            if inspect()!=identity:raise ValueError('CLONE-IDENTITY-CHANGED')
            if not a.leave_running:
                reply=json.loads(subprocess.check_output(['docker','exec',CONTAINER,'python3','/lab/qmp_clone.py','pause'],timeout=20));cleanup['confirmed']=reply['status']['running'] is False
            else:cleanup['confirmed']=True
        except Exception as error:cleanup['error']=type(error).__name__;state['state']='FAIL'
        atomic(out/'producer-cleanup.json',cleanup);state['finished_at_utc']=utc();atomic(out/'status.json',state)
        if lease.read_text()==str(os.getpid()):lease.unlink()
    return 0 if state['state']=='MEASUREMENTS-PASS' else 1
if __name__=='__main__':raise SystemExit(main())
