"""Separate-process SIGKILL during real native.rollback plus actual QEMU rules.

Only the marked disposable guest is mutated. UCI and vendor compilation are
explicit adapters; persistent journals, Lua parsing, recovery checks, process
termination and guest netfilter/ip rules are real. No procd/power-loss claim.
"""
import copy,hashlib,json,os,shlex,signal,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch

REPO=Path(os.environ['QA_REPO']).resolve();OUT=Path(os.environ['QA_OUTPUT']).resolve()
SCRIPTS=Path(os.environ.get('QA_REPRODUCTION',str(REPO/'qa/evidence/switching-2026-10-28/reproduction'))).resolve()
sys.path.insert(0,str(SCRIPTS));sys.path.insert(0,str(REPO/'router/tests'))
from test_rollback_order_steps import RestoreOrderSteps
import agent,auto_control,native_switch as native,pair_auto
from qemu_serial import execute

LABEL=os.environ.get('QA_LABEL','final')
REPORT=OUT/('real-rollback-crash-'+LABEL+'.json')
SOURCE=json.loads((REPO/'QA-SOURCE.json').read_text())if(REPO/'QA-SOURCE.json').exists()else{'source_commit':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()}
report={'scope':'Real separate Linux process executes production native.rollback and receives SIGKILL after a UCI move; real on-disk journal, Lua parser, recovery authorization and disposable QEMU/OpenWrt kernel readback. UCI pending deltas, vendor compiler, diagnostic health and nft guard are synthetic fixture adapters. No physical router, procd restart, power-cut or real VPN/LAN traffic is certified.',
 'source':SOURCE,'production_sha256':{name:hashlib.sha256((REPO/'router/files/usr/lib/homensai-vpn'/name).read_bytes()).hexdigest()for name in('native_switch.py','rollback_recovery.py','pair_auto.py','pair_manual.py','auto_control.py','kernel_policy.py')},
 'isolation':{'etc_readonly':bool(os.statvfs('/etc').f_flag&os.ST_RDONLY),'run_readonly':bool(os.statvfs('/run').f_flag&os.ST_RDONLY),'effective_capabilities':next(x.split(':',1)[1].strip()for x in Path('/proc/self/status').read_text().splitlines()if x.startswith('CapEff:'))},'cases':[],'errors':[]}
def save():REPORT.write_text(json.dumps(report,indent=2)+'\n')
def actual_kernel():return {'mangle':execute('iptables-save -t mangle'),'ip_rules':json.loads(execute('ip -4 -j rule show'))}
def kernel_identity(snapshot):
 from kernel_policy import parse_mangle
 return native.digest({'mangle':parse_mangle(snapshot['mangle']),'rules':snapshot['ip_rules']})

def run_case(moves_before_kill):
 test=RestoreOrderSteps();test.setUp();case=test.case
 row={'name':'SIGKILL-after-%d-UCI-move'%moves_before_kill,'checks':[],'snapshots':{},'recovery_error':None}
 report['cases'].append(row);save()
 def check(name,passed):row['checks'].append({'name':name,'passed':bool(passed)});save()
 try:
  for name,filename in(('CERT','native-certificate.json'),('ATTEMPTS','native-attempts.json'),('PREPARE','acceleration-prepare.json'),('JOURNAL_ALARM','native-journal-alarm.json')):
   case.enter(patch.object(native,name,case.persist/filename))
  import speed_pause
  case.enter(patch.object(speed_pause,'RUNTIME',case.runtime))
  shared=case.root/'synthetic-uci.json';commands=case.root/'platform-commands.jsonl';crash_snapshot=case.root/'crash-point.json'
  agent.atomic_json(shared,case.data)
  original_command=case.command;original_write=case.write
  phase=['setup'];kill_enabled=[False];move_count=[0];apply_count=[0]
  def install_kernel():
   text=case.kernel_text();execute("printf '%s' "+shlex.quote(text)+" >/tmp/qa-rollback-kernel; iptables-restore </tmp/qa-rollback-kernel")
  def command(args,timeout=5):
   if args[0]=='iptables-save':return execute('iptables-save -t mangle').encode()
   if args[:5]==['ip','-4','-j','rule','show']:return execute('ip -4 -j rule show').encode()
   return original_command(args,timeout)
  def write(args):
   result=original_write(args)
   agent.atomic_json(shared,case.data)
   with commands.open('a')as stream:stream.write(json.dumps({'phase':phase[0],'pid':os.getpid(),'argv':args})+'\n');stream.flush();os.fsync(stream.fileno())
   if args[:2]==['/usr/bin/rtp2.sh','not_reload_network']:
    install_kernel();apply_count[0]+=1
   if kill_enabled[0]and args[:2]==['uci','reorder']:
    move_count[0]+=1
    if move_count[0]==moves_before_kill:
     agent.atomic_json(crash_snapshot,{'pid':os.getpid(),'moves':move_count[0],'journal':native.journal_read(),'order':test.backend.order(),'uci_pending':case.data.get('pending'),'kernel':actual_kernel()})
     os.kill(os.getpid(),signal.SIGKILL)
   return result
  case.enter(patch.object(native,'command',side_effect=command));case.enter(patch.object(case,'write',side_effect=write))
  execute('while ip rule del priority 6000 2>/dev/null; do :; done; ip rule add priority 6000 fwmark 0x1000/0xf000 table 1001; ip rule add priority 6000 fwmark 0xb000/0xf000 table 1012; ip rule add priority 6000 fwmark 0x2000/0xf000 table 1002')
  install_kernel();before=actual_kernel();proof=test.backend.attest_policy()
  row['snapshots']['initial']={'kernel':before,'proof':proof,'order':test.backend.order(),'journal':native.journal_read(),'target_order':test.target}
  check('initial actual guest rules attest the selected primary',proof.get('verified')is True and proof.get('role')=='source')
  phase[0]='interrupted-child';kill_enabled[0]=True
  pid=os.fork()
  if pid==0:
   try:
    os.setsid();native.rollback(test.backend,native.journal_read(),'PAIR-STOPPED',restore_order=test.target)
   except BaseException as error:
    agent.atomic_json(case.root/'child-error.json',{'type':type(error).__name__,'message':str(error)})
    os._exit(75)
   os._exit(76)
  deadline=time.monotonic()+120
  while True:
   child,status=os.waitpid(pid,os.WNOHANG)
   if child:break
   if time.monotonic()>=deadline:
    os.kill(pid,signal.SIGKILL);os.waitpid(pid,0);raise TimeoutError('owned rollback child did not reach selected crash point')
   time.sleep(.05)
  kill_enabled[0]=False;row['child']={'pid':pid,'wait_status':status,'signal':os.WTERMSIG(status)if os.WIFSIGNALED(status)else None,'exit_status':os.WEXITSTATUS(status)if os.WIFEXITED(status)else None}
  if(crash_snapshot.exists()):row['snapshots']['crash_point']=json.loads(crash_snapshot.read_text())
  if(case.root/'child-error.json').exists():row['child']['error']=json.loads((case.root/'child-error.json').read_text())
  check('separate worker reached the selected move and died by SIGKILL',os.WIFSIGNALED(status)and os.WTERMSIG(status)==signal.SIGKILL and crash_snapshot.exists())
  case.data=agent.read_json(shared);current=test.backend.order();after_kill=actual_kernel()
  row['snapshots']['after_kill']={'order':current,'journal':native.journal_read(),'kernel':after_kill,'uci_pending':case.data.get('pending')}
  check('kernel graph and rule fingerprint stay unchanged before recovery',kernel_identity(before)==kernel_identity(after_kill))
  check('durable transaction records an unfinished restore',native.journal_read().get('phase')=='RESTORING')
  check('UCI delta remains pending at the injected process crash',bool(case.data.get('pending')))
  check('crash order is the concrete first-move intermediate or final uncommitted order',(current[0]not in(test.before,test.target))if moves_before_kill==1 else current[0]==test.target)
  revision=auto_control.current_revision(rotate=True);pair_auto.stop_locked(revision);phase[0]='recovery'
  row['snapshots']['stopped_intent']=pair_auto.intent();save()
  try:native.rollback(test.backend,native.journal_read(),'SUPERVISOR-RECOVERY')
  except Exception as error:
   row['recovery_error']={'type':type(error).__name__,'message':str(error)}
   if isinstance(error,subprocess.CalledProcessError):
    stderr=error.stderr or b''
    row['recovery_error']['stderr']=stderr.decode(errors='replace')if isinstance(stderr,bytes)else str(stderr)
  final=actual_kernel();final_proof=test.backend.attest_policy();all_commands=[json.loads(line)for line in commands.read_text().splitlines()]if commands.exists()else[]
  recovery_commands=[r['argv']for r in all_commands if r['phase']=='recovery']
  row['platform_commands']=all_commands
  row['snapshots']['after_recovery']={'order':test.backend.order(),'journal':native.journal_read(),'kernel':final,'proof':final_proof,'intent':pair_auto.intent(),'uci_pending':case.data.get('pending')}
  check('recovery restores the exact recorded session order',row['recovery_error']is None and test.backend.order()[0]==test.target)
  check('recovery performs only the remaining UCI move',sum(args[:2]==['uci','reorder']for args in recovery_commands)==2-moves_before_kill)
  check('owned pending UCI delta is committed once before vendor apply',sum(args[:3]==['uci','commit','route_policy']for args in recovery_commands)==1 and not case.data.get('pending'))
  check('exactly one vendor dispatch updates the actual guest graph',sum(args[0]=='/usr/bin/rtp2.sh'for args in recovery_commands)==1 and kernel_identity(final)!=kernel_identity(before))
  check('restored guest graph is independently attested as reserve',final_proof.get('verified')is True and final_proof.get('role')=='target')
  check('transaction is terminal ROLLED-BACK with exact restored order',native.journal_read().get('phase')=='ROLLED-BACK'and native.journal_read().get('restored_order')==test.target)
  check('recovery does not re-enable Auto or reuse its old control revision',pair_auto.intent().get('mode')=='off'and pair_auto.intent().get('revision')==revision)
  row['verdict']='PASS'if all(c['passed']for c in row['checks'])else'FAIL';save();print(json.dumps({'case':row['name'],'verdict':row['verdict'],'recovery_error':row['recovery_error']}),flush=True)
 finally:test.doCleanups()

try:
 if not(report['isolation']['etc_readonly']and report['isolation']['run_readonly']and set(report['isolation']['effective_capabilities'])=={'0'}):raise RuntimeError('READONLY_HOST_CAPABILITIES_REQUIRED')
 for moves in(1,2):run_case(moves)
except BaseException as error:report['errors'].append({'type':type(error).__name__,'message':str(error)});raise
finally:
 report['verdict']='PASS'if len(report['cases'])==2 and not report['errors']and all(r.get('verdict')=='PASS'for r in report['cases'])else'FAIL';save();print(json.dumps({'verdict':report['verdict'],'path':str(REPORT),'errors':report['errors']},indent=2))
if report['verdict']!='PASS':raise SystemExit(1)
