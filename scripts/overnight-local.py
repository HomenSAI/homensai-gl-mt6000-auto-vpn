"""Bounded, local-only overnight acceptance runner. Never contacts a router."""
import argparse, hashlib, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTAINER = 'homensai-vpn-qemu-alpha7'
SHA = '94376a1842bab35d37f1d9c67980f0c98cc5062e4a4a4ab88b8fb55d3c3a2513'
SHELL = r'C:\Program Files\PowerShell\7\pwsh.exe'


def utc():
    return datetime.now(timezone.utc)


def enough_time(deadline, seconds, reserve=300):
    return (deadline - utc()).total_seconds() >= seconds + reserve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--until', required=True, help='Explicit ISO timestamp with timezone')
    args = parser.parse_args()
    deadline = datetime.fromisoformat(args.until)
    if deadline.tzinfo is None or not 0 < (deadline-utc()).total_seconds() <= 12*3600:
        raise ValueError('NIGHT-DEADLINE-BOUNDS')
    out = REPO / 'private' / ('overnight-' + utc().strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(parents=True, exist_ok=False)
    lock = REPO / '.git' / 'handoff' / 'overnight-local.lock'
    lock.parent.mkdir(exist_ok=True)
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, str(os.getpid()).encode()); os.close(fd)
    state = {'state':'RUNNING', 'started_at_utc':utc().isoformat(), 'deadline':deadline.isoformat(),
             'pid':os.getpid(), 'output':str(out), 'physical_router_access':False, 'runs':[], 'errors':[]}
    active = False
    log = (out/'commands.log').open('a', encoding='utf-8')

    def save():
        state['updated_at_utc'] = utc().isoformat()
        temp=out/'status.tmp'; temp.write_text(json.dumps(state, indent=2), encoding='utf-8')
        temp.replace(out/'status.json')

    def event(action, result, detail=''):
        row={'time_utc':utc().isoformat(),'action':action,'result':result,'detail':detail}
        with (out/'events.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row)+'\n')
        save()

    def run(argv, timeout=150):
        log.write('\n'+utc().isoformat()+' '+json.dumps(argv)+'\n'); log.flush()
        result=subprocess.run(argv,cwd=REPO,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,
                              env={**os.environ,'PYTHONUTF8':'1'})
        log.flush()
        if result.returncode: raise RuntimeError(f'COMMAND-EXIT-{result.returncode}: {argv[:4]}')

    def docker(script, *args, timeout=150):
        run(['docker','exec',CONTAINER,'python3','/lab/'+script,*args],timeout)

    def copy(name, folder):
        run(['docker','cp',CONTAINER+':/lab/'+name,str(folder/name)])

    def stop_owned():
        # The helper validates clone identity and uses the current owned receipt only.
        docker('stop_overnight_protocol.py')

    try:
        save();event('overnight-start','RUNNING','Two bounded 7200-second protocol runs, then offline suites until deadline.')
        assert hashlib.sha256((REPO/'lab/protocol_namespace_lab.py').read_bytes()).hexdigest()==SHA
        inspect=json.loads(subprocess.check_output(['docker','inspect',CONTAINER],text=True))[0]
        assert inspect['HostConfig']['NetworkMode']=='none' and not inspect['HostConfig']['Privileged'] and not inspect['Mounts']
        for name in ['run_protocol_soak.py','start_protocol_ready_collector.py','export_protocol_evidence.py','stop_overnight_protocol.py']:
            run(['docker','cp',str(REPO/'lab'/name),CONTAINER+':/lab/'+name])
        docker('qmp_clone.py','resume')
        for number in range(1,3):
            if not enough_time(deadline,7200,600):
                event('protocol-run-'+str(number),'NOT_STARTED','Insufficient time for full duration and cleanup.');break
            folder=out/('protocol-'+str(number));folder.mkdir()
            root='/tmp/homensai-protocol-lab-night'+utc().strftime('%Y%m%d%H%M%S')+str(number)
            docker('run_protocol_soak.py','--sha256',SHA,'--duration','7200','--root',root)
            active=True
            copy('protocol-soak-start.json',folder)
            docker('start_protocol_ready_collector.py')
            copy('protocol-ready-collector-start.json',folder)
            time.sleep(60)
            docker('protocol_cleanup_witness.py','before')
            copy('protocol-ready-cleanup-before.json',folder)
            event('protocol-run-'+str(number),'RUNNING',root)
            errors=0
            while utc()<deadline:
                try:
                    docker('protocol_ready_status.py')
                    copy('protocol-ready-observation.json',folder)
                    observation=json.loads((folder/'protocol-ready-observation.json').read_text())
                    state['current_protocol']={'number':number,'state':observation['producer']['state'],
                        'counts':observation['producer']['counts'],'elapsed_seconds':observation['producer']['elapsed_seconds'],
                        'fresh':observation['fresh'],'missing_events':observation['series']['missing_events']}
                    save()
                    if not observation['fresh']: raise RuntimeError('STALE-PRODUCER-OR-COLLECTOR')
                    errors=0
                    if observation['producer']['state'] in ('PASS','FAIL','STOPPED') and observation['series']['producer_state']==observation['producer']['state'] and observation['series']['counts']==observation['producer']['counts']: break
                except Exception as exc:
                    errors+=1;event('protocol-observation','ERROR',str(exc))
                    if errors>=3: raise RuntimeError('THREE-CONSECUTIVE-OBSERVATION-ERRORS') from exc
                time.sleep(min(60,max(0,(deadline-utc()).total_seconds())))
            else:
                stop_owned();time.sleep(15);docker('protocol_ready_status.py');copy('protocol-ready-observation.json',folder)
                observation=json.loads((folder/'protocol-ready-observation.json').read_text())
            time.sleep(10)
            docker('protocol_cleanup_witness.py','after');copy('protocol-ready-cleanup-after.json',folder)
            active=False
            terminal=observation['producer']['state']
            if terminal=='PASS':
                docker('export_protocol_evidence.py');copy('protocol-final-public-evidence.tar.gz',folder)
                copy('protocol-final-raw-probes-summary.json',folder)
                run([sys.executable,'qa/verify_protocol_soak.py','--observation',str(folder/'protocol-ready-observation.json'),
                    '--start',str(folder/'protocol-soak-start.json'),'--cleanup',str(folder/'protocol-ready-cleanup-after.json'),
                    '--output',str(folder/'verification.json')])
                run([sys.executable,'qa/classify_protocol_probes.py','--archive',str(folder/'protocol-final-public-evidence.tar.gz'),
                    '--observation',str(folder/'protocol-ready-observation.json'),'--csv',str(folder/'probes.csv'),
                    '--summary',str(folder/'classification.json')])
            state['runs'].append({'number':number,'terminal':terminal,'output':str(folder),'cleanup':'PASS'})
            event('protocol-run-'+str(number),terminal,'Independent cleanup PASS; public evidence verified only for PASS.')
        docker('qmp_clone.py','pause')
        # No guest workload overlaps these CPU-intensive suites.
        if enough_time(deadline,900,0):
            run([SHELL,'-NoProfile','-File','scripts/offline-ci.ps1'],timeout=min(900,(deadline-utc()).total_seconds()))
            event('exact-committed-snapshot-offline-ci','PASS')
        iteration=0
        while enough_time(deadline,180,0):
            iteration+=1
            run([SHELL,'-NoProfile','-File','scripts/test-local.ps1','-CheckCommand',
                 'set -eu; cd lab; python3 -m unittest test_transaction_engine test_process_crash -q; node test_transaction_regressions.js; node test_router_faults.js'],
                timeout=min(180,(deadline-utc()).total_seconds()))
            state['offline_model_iterations']=iteration;event('offline-model-iteration-'+str(iteration),'PASS','Repeated suite, not additional unique coverage.')
            time.sleep(min(180,max(0,(deadline-utc()).total_seconds())))
        state['state']='COMPLETED' if all(r['terminal']=='PASS' for r in state['runs']) and len(state['runs'])==2 else 'INCOMPLETE'
    except Exception as exc:
        state['state']='FAIL';state['errors'].append({'time_utc':utc().isoformat(),'error':str(exc)})
        event('overnight-runner','FAIL',str(exc))
    finally:
        if active:
            try:
                stop_owned();time.sleep(20);docker('protocol_cleanup_witness.py','after')
                copy('protocol-ready-cleanup-after.json',out)
                active=False;event('emergency-owned-cleanup','PASS')
            except Exception as exc:
                state['errors'].append({'cleanup_error':str(exc)});event('emergency-owned-cleanup','UNCONFIRMED',str(exc))
        if not active:
            try: docker('qmp_clone.py','pause');event('clone-paused','PASS')
            except Exception as exc: state['errors'].append({'pause_error':str(exc)})
        state['finished_at_utc']=utc().isoformat();save();log.close();lock.unlink(missing_ok=True)
    return 0 if state['state']=='COMPLETED' else 1

if __name__=='__main__':
    raise SystemExit(main())
