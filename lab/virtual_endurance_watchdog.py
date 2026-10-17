"""Independent bounded cleanup witness for a single virtual endurance run."""
import argparse,json,subprocess,time
from pathlib import Path
CONTAINER='homensai-vpn-qemu-alpha7'
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--duration',type=int,required=True);p.add_argument('--leave-running',action='store_true');p.add_argument('--pause',action='store_true');a=p.parse_args()
if not 120<=a.duration<=86520 or not a.out.is_dir():raise ValueError('WATCHDOG-BOUNDS')
initial=json.loads((a.out/'status.json').read_text());deadline=time.monotonic()+a.duration
while time.monotonic()<deadline:
    try:
        current=json.loads((a.out/'status.json').read_text())
        if current.get('pid')!=initial['pid'] or current.get('source')!=initial['source']:raise ValueError('RUN-IDENTITY-CHANGED')
        if current['state'] in ('MEASUREMENTS-PASS','PASS','FAIL','STOPPED'):break
    except (OSError,ValueError):pass
    time.sleep(5)
result={'independent':True,'source':initial['source'],'confirmed':False,'leave_running':a.leave_running}
try:
    row=json.loads(subprocess.check_output(['docker','inspect',CONTAINER],timeout=20))[0]
    assert row['Id']==initial['container_id'] and row['HostConfig']['NetworkMode']=='none' and not row['HostConfig']['Privileged'] and not row['Mounts']
    if not a.leave_running:
        reply=json.loads(subprocess.check_output(['docker','exec',CONTAINER,'python3','/lab/qmp_clone.py','pause'],timeout=20));assert reply['status']['running'] is False
    result['confirmed']=True
except Exception as error:result['error']=type(error).__name__
(a.out/'independent-cleanup.json').write_text(json.dumps(result,indent=2))

current=json.loads((a.out/'status.json').read_text())
if current.get('pid')==initial['pid'] and current.get('source')==initial['source']:
    if current['state']=='MEASUREMENTS-PASS':
        current['state']='PASS' if result['confirmed'] else 'FAIL'
        current['independent_cleanup_confirmed']=result['confirmed']
    elif current['state']=='RUNNING':
        current.update(state='STOPPED',watchdog_reason='DEADLINE-WITHOUT-PRODUCER-COMPLETION')
    pending=a.out/'watchdog-status.pending';pending.write_text(json.dumps(current,indent=2));pending.replace(a.out/'status.json')
