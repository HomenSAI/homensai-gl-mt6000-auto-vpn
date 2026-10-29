"""Separate-process SIGKILL during real native.rollback plus actual QEMU rules.

Only the marked disposable guest is mutated. UCI and vendor compilation are
explicit adapters; persistent journals, Lua parsing, recovery checks, process
termination and guest netfilter/ip rules are real. No procd/power-loss claim.

Cases: SIGKILL after the first / the last of two reverse UCI moves during an
owned restore, and (case 3) a forward manual RTP that fails without changing
the guest kernel, a Stop, the forward-proof promotion inside a separate
recovery process and SIGKILL after the last reverse move before commit.
Case 4 (vendor): a real vendor stand-in process is SIGKILLed mid-rebuild
(guest TUNNEL route chains flushed, one gl_vpn_rules forwarding missing,
stale lock); the supervisor finishes the own rebuild. QA_CASES (comma list of
move1,move2,forward,vendor) selects cases; default all four.
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
 'source':SOURCE,'production_sha256':{name:(hashlib.sha256((REPO/'router/files/usr/lib/homensai-vpn'/name).read_bytes()).hexdigest()if(REPO/'router/files/usr/lib/homensai-vpn'/name).exists()else None)for name in('native_switch.py','rollback_recovery.py','pair_auto.py','pair_manual.py','auto_control.py','kernel_policy.py')},
 'isolation':{'etc_readonly':bool(os.statvfs('/etc').f_flag&os.ST_RDONLY),'run_readonly':bool(os.statvfs('/run').f_flag&os.ST_RDONLY),'effective_capabilities':next(x.split(':',1)[1].strip()for x in Path('/proc/self/status').read_text().splitlines()if x.startswith('CapEff:'))},'cases':[],'errors':[]}
def save():REPORT.write_text(json.dumps(report,indent=2)+'\n')
def actual_kernel():return {'mangle':execute('iptables-save -t mangle'),'ip_rules':json.loads(execute('ip -4 -j rule show'))}
def kernel_identity(snapshot):
 from kernel_policy import parse_mangle
 return native.digest({'mangle':parse_mangle(snapshot['mangle']),'rules':snapshot['ip_rules']})

def run_case(moves_before_kill,forward=False):
 test=RestoreOrderSteps();test.setUp();case=test.case
 row={'name':('forward-RTP-failure-promotion-SIGKILL-after-last-reverse-move' if forward else 'SIGKILL-after-%d-UCI-move'%moves_before_kill),'checks':[],'snapshots':{},'recovery_error':None}
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
  expected_order=test.target;failed_forward=None
  if forward:
   failed_forward=forward_failure(test,case,row,check,phase,before)
   expected_order=failed_forward['before']
  phase[0]='interrupted-child';kill_enabled[0]=True
  pid=os.fork()
  if pid==0:
   try:
    os.setsid()
    if forward:native.rollback(test.backend,native.journal_read(),'SUPERVISOR-RECOVERY')
    else:native.rollback(test.backend,native.journal_read(),'PAIR-STOPPED',restore_order=test.target)
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
  check('crash order is the concrete first-move intermediate or final uncommitted order',(current[0]not in(test.before,test.target))if moves_before_kill==1 else current[0]==expected_order)
  if forward:
   saved=native.journal_read()
   check('crash journal holds the promoted forward proof with the original UCI origin and kernel fingerprint',
         saved.get('restore_proof_source')=='forward'and saved.get('restore_order_origin')==failed_forward['after']
         and saved.get('restore_before_order')==failed_forward['before']
         and saved.get('restore_kernel_fingerprint')==failed_forward['kernel_before_fingerprint'])
  ledger=agent.read_json(case.persist/'pair-auto-budget.json',{})
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
  check('recovery restores the exact recorded session order',row['recovery_error']is None and test.backend.order()[0]==expected_order)
  check('recovery performs only the remaining UCI move',sum(args[:2]==['uci','reorder']for args in recovery_commands)==2-moves_before_kill)
  check('owned pending UCI delta is committed once before vendor apply',sum(args[:3]==['uci','commit','route_policy']for args in recovery_commands)==1 and not case.data.get('pending'))
  if forward:
   check('exactly one vendor dispatch reproduces the unchanged original guest graph',sum(args[0]=='/usr/bin/rtp2.sh'for args in recovery_commands)==1 and kernel_identity(final)==kernel_identity(before))
   check('restored guest graph is independently attested as the original primary',final_proof.get('verified')is True and final_proof.get('role')=='source')
   fields={}
   if native.journal_read().get('phase')=='ROLLED-BACK':
    fields=native.pair_event_fields(native.journal_read(),completed=True,outcome='restored',restoring=True)
   row['snapshots']['restored_event_fields']=fields
   check('restored event reports an unchanged real channel (route_changed false)',fields.get('route_changed')is False)
   check('recovery spends no switching budget',agent.read_json(case.persist/'pair-auto-budget.json',{})==ledger)
  else:
   check('exactly one vendor dispatch updates the actual guest graph',sum(args[0]=='/usr/bin/rtp2.sh'for args in recovery_commands)==1 and kernel_identity(final)!=kernel_identity(before))
   check('restored guest graph is independently attested as reserve',final_proof.get('verified')is True and final_proof.get('role')=='target')
  check('transaction is terminal ROLLED-BACK with exact restored order',native.journal_read().get('phase')=='ROLLED-BACK'and native.journal_read().get('restored_order')==expected_order)
  check('recovery does not re-enable Auto or reuse its old control revision',pair_auto.intent().get('mode')=='off'and pair_auto.intent().get('revision')==revision)
  row['verdict']='PASS'if all(c['passed']for c in row['checks'])else'FAIL';save();print(json.dumps({'case':row['name'],'verdict':row['verdict'],'recovery_error':row['recovery_error']}),flush=True)
 finally:test.doCleanups()

def forward_failure(test,case,row,check,phase,initial_kernel):
 """A real manual request whose forward RTP fails before any kernel write, then Stop."""
 import pair_manual as manual
 phase[0]='forward';writer=case.write;failed=[False]
 def fail_rtp(args):
  if args[0]=='/usr/bin/rtp2.sh'and not failed[0]:
   failed[0]=True;raise native.Refused('VENDOR-APPLY-FAILED')
  return writer(args)
 agent.atomic_json(case.persist/'pair-auto-budget.json',{'events':[]})
 accepted=manual.request('reserve',case.revision);row['snapshots']['manual_request']=accepted
 try:
  with patch.object(case,'write',side_effect=fail_rtp):
   manual.consume(test.backend,pair_auto.read_state(),case.data['settings'],case.revision)
 except Exception as error:row['forward_consume_error']={'type':type(error).__name__,'message':str(error)}
 saved=native.journal_read();kernel=actual_kernel()
 row['snapshots']['after_forward_failure']={'journal':saved,'order':test.backend.order(),'kernel':kernel,'proof':test.backend.attest_policy(),'pair_state':pair_auto.read_state()}
 check('manual request accepted and forward RTP dispatch actually failed',accepted.get('accepted')is True and failed[0])
 check('failed forward journal stays APPLYING with dispatched/touched flags and full verified kernel_before proof',
       saved.get('phase')=='APPLYING'and saved.get('rtp_dispatched')is True and saved.get('forward_policy_touched')is True
       and saved.get('kernel_before_verified')is True and isinstance(saved.get('kernel_before_fingerprint'),str)
       and not any(k.startswith('restore')for k in saved))
 check('UCI is at the forward target while the real guest graph is unchanged',test.backend.order()[0]==saved.get('after')and kernel_identity(kernel)==kernel_identity(initial_kernel))
 check('mismatched UCI/kernel is not attested',test.backend.attest_policy().get('verified')is not True)
 revision=auto_control.current_revision(rotate=True);pair_auto.stop_locked(revision)
 row['snapshots']['forward_stop_intent']=pair_auto.intent();case.commands.clear();save()
 return saved

ORIGINAL_FW=(b"config defaults\n\toption input 'ACCEPT'\n\n"
             b"config zone\n\toption name 'lan'\n\toption network 'lan'\n\n"
             b"config zone 'wgclient1'\n\toption name 'wgclient1'\n\toption gl_vpn_rules '1'\n\n"
             b"config forwarding 'lan2wgclient1'\n\toption src 'lan'\n\toption dest 'wgclient1'\n\toption gl_vpn_rules '1'\n\n"
             b"config forwarding 'lan2ovpnclient2'\n\toption src 'lan'\n\toption dest 'ovpnclient2'\n\toption gl_vpn_rules '1'\n\n"
             b"config forwarding 'guest2ovpnclient2'\n\toption src 'guest'\n\toption dest 'ovpnclient2'\n\toption gl_vpn_rules '1'\n")
PARTIAL_FW=ORIGINAL_FW.split(b"\nconfig forwarding 'guest2ovpnclient2'")[0]+b'\n'


def run_vendor_case():
 """Case 4: a real vendor stand-in process is SIGKILLed mid-rebuild (guest mangle
 flushed of its TUNNEL route chains, one gl_vpn_rules forwarding missing, stale
 lock left behind); the supervisor then finishes the own rebuild or refuses."""
 test=RestoreOrderSteps();test.setUp();case=test.case
 row={'name':'vendor-RTP-SIGKILLed-mid-rebuild-then-supervisor-rebuild','checks':[],'snapshots':{},'recovery_error':None}
 report['cases'].append(row);save()
 def check(name,passed):row['checks'].append({'name':name,'passed':bool(passed)});save()
 try:
  for name,filename in(('CERT','native-certificate.json'),('ATTEMPTS','native-attempts.json'),('PREPARE','acceleration-prepare.json'),('JOURNAL_ALARM','native-journal-alarm.json')):
   case.enter(patch.object(native,name,case.persist/filename))
  import speed_pause
  case.enter(patch.object(speed_pause,'RUNTIME',case.runtime))
  lock=Path('/tmp/run/rtp2.lock');lock.parent.mkdir(exist_ok=True)
  if lock.exists():raise RuntimeError('unexpected vendor lock in private /tmp')
  fw=[ORIGINAL_FW]
  case.enter(patch.object(pair_auto,'firewall_bytes',side_effect=lambda:fw[0],create=True))  # absent on alpha57
  case.enter(patch.object(pair_auto,'configs',side_effect=lambda interfaces=None:{'firewall':pair_auto.config_digest('firewall',fw[0])}))
  state=pair_auto.read_state();state['protected']={'firewall':pair_auto.config_digest('firewall',ORIGINAL_FW)};pair_auto.save(state)
  commands=case.root/'platform-commands.jsonl';phase=['setup'];original_command=case.command;original_write=case.write
  def install(text):execute("printf '%s' "+shlex.quote(text)+" >/tmp/qa-rollback-kernel; iptables-restore </tmp/qa-rollback-kernel")
  def partial_text():return ''.join(line+'\n' for line in case.kernel_text().splitlines() if 'TUNNEL' not in line)
  def command(args,timeout=5):
   if args[0]=='iptables-save':return execute('iptables-save -t mangle').encode()
   if args[:5]==['ip','-4','-j','rule','show']:return execute('ip -4 -j rule show').encode()
   if args==['uci','-q','changes']:return b"route_policy.cfg000002='rule'\n" if case.data.get('pending') else b''
   return original_command(args,timeout)
  died=[False];stand_in={}
  def write(args):
   with commands.open('a')as stream:stream.write(json.dumps({'phase':phase[0],'argv':args})+'\n')
   if args[0]=='/usr/bin/rtp2.sh' and not died[0]:
    died[0]=True
    # Real separate process takes the vendor lock like rtp2.sh ($$), then dies by SIGKILL mid-rebuild.
    worker=subprocess.Popen(['sh','-c','echo $$ > /tmp/run/rtp2.lock; exec sleep 60'],start_new_session=True)
    for _ in range(100):
     if lock.exists()and lock.read_text().strip()==str(worker.pid):break
     time.sleep(.05)
    install(partial_text());fw[0]=PARTIAL_FW
    os.kill(worker.pid,signal.SIGKILL);status=worker.wait()
    stand_in.update(pid=worker.pid,returncode=status,lock=lock.read_text().strip()if lock.exists()else None)
    raise native.Refused('NATIVE-SYSTEM-001')
   result=original_write(args)
   if args[0]=='/usr/bin/rtp2.sh':install(case.kernel_text());fw[0]=ORIGINAL_FW
   return result
  case.enter(patch.object(native,'command',side_effect=command));case.enter(patch.object(case,'write',side_effect=write))
  execute('while ip rule del priority 6000 2>/dev/null; do :; done; ip rule add priority 6000 fwmark 0x1000/0xf000 table 1001; ip rule add priority 6000 fwmark 0xb000/0xf000 table 1012; ip rule add priority 6000 fwmark 0x2000/0xf000 table 1002')
  install(case.kernel_text());before=actual_kernel();proof=test.backend.attest_policy()
  row['snapshots']['initial']={'kernel':before,'proof':proof,'order':test.backend.order(),'firewall':ORIGINAL_FW.decode()}
  check('initial actual guest rules attest the selected primary',proof.get('verified')is True and proof.get('role')=='source')
  import pair_manual as manual
  agent.atomic_json(case.persist/'pair-auto-budget.json',{'events':[]});phase[0]='forward'
  accepted=manual.request('reserve',case.revision)
  manual.consume(test.backend,pair_auto.read_state(),case.data['settings'],case.revision)
  saved=native.journal_read();damaged=actual_kernel()
  unrouted=lambda text:'TUNNEL' not in text and '-j MARK' not in text  # harness-side, independent of product code
  row['snapshots']['after_vendor_kill']={'journal':saved,'order':test.backend.order(),'kernel':damaged,'proof':test.backend.attest_policy(),'stand_in':stand_in,'firewall':fw[0].decode()}
  check('manual request accepted and the vendor stand-in really died by SIGKILL',accepted.get('accepted')is True and stand_in.get('returncode')==-signal.SIGKILL)
  check('stale vendor lock names the dead stand-in pid',stand_in.get('lock')==str(stand_in.get('pid'))and lock.exists()and not Path('/proc',str(stand_in.get('pid'))).exists())
  check('journal stays APPLYING at worker stage rtp-dispatch with the full forward proof',saved.get('phase')=='APPLYING'and saved.get('rtp_dispatched')is True
        and (saved.get('failure_detail')or{}).get('worker_stage')=='rtp-dispatch'and not any(k.startswith('restore')for k in saved))
  check('actual guest graph changed to an unrouted vendor intermediate',kernel_identity(damaged)!=kernel_identity(before)and unrouted(damaged['mangle']))
  check('one gl_vpn_rules forwarding is missing from the firewall',fw[0]==PARTIAL_FW)
  check('mismatched graph is not attested',test.backend.attest_policy().get('verified')is not True)
  ledger=agent.read_json(case.persist/'pair-auto-budget.json',{})
  revision=auto_control.current_revision(rotate=True);pair_auto.stop_locked(revision);case.commands.clear();phase[0]='recovery'
  try:native.rollback(test.backend,native.journal_read(),'SUPERVISOR-RECOVERY')
  except Exception as error:row['recovery_error']={'type':type(error).__name__,'message':str(error)}
  final=actual_kernel();final_proof=test.backend.attest_policy()
  all_commands=[json.loads(line)for line in commands.read_text().splitlines()]if commands.exists()else[]
  recovery_commands=[r['argv']for r in all_commands if r['phase']=='recovery'];row['platform_commands']=all_commands
  journal=native.journal_read()
  row['snapshots']['after_recovery']={'order':test.backend.order(),'journal':journal,'kernel':final,'proof':final_proof,'intent':pair_auto.intent(),'firewall':fw[0].decode(),'lock_exists':lock.exists()}
  check('recovery closes the own rebuild as ROLLED-BACK vendor-rebuild with the original order',row['recovery_error']is None and journal.get('phase')=='ROLLED-BACK'
        and journal.get('restore_proof_source')=='vendor-rebuild'and journal.get('restored_order')==saved['before']and test.backend.order()[0]==saved['before'])
  check('only the allowed writes ran: two reverse moves, one commit, process sync, one vendor rebuild',
        [a[0]if a[0]!='uci'else' '.join(a[:2])for a in recovery_commands]==['uci reorder','uci reorder','uci commit','lua','/usr/bin/rtp2.sh'])
  check('rebuilt actual guest graph equals the original and is attested as primary',kernel_identity(final)==kernel_identity(before)and final_proof.get('verified')is True and final_proof.get('role')=='source')
  check('firewall equals the protected original and the stale lock is gone',fw[0]==ORIGINAL_FW and not lock.exists())
  check('no budget spent, Auto stays OFF with the new revision',agent.read_json(case.persist/'pair-auto-budget.json',{})==ledger and pair_auto.intent().get('mode')=='off'and pair_auto.intent().get('revision')==revision)
  recovered=pair_auto.recover(test.backend)
  check('pair ownership then ends STOPPED without a new start',recovered is True and pair_auto.read_state().get('phase')=='STOPPED'and pair_auto.intent().get('mode')=='off')
  row['verdict']='PASS'if all(c['passed']for c in row['checks'])else'FAIL';save();print(json.dumps({'case':row['name'],'verdict':row['verdict'],'recovery_error':row['recovery_error']}),flush=True)
 finally:
  try:Path('/tmp/run/rtp2.lock').unlink()
  except FileNotFoundError:pass
  test.doCleanups()


try:
 if not(report['isolation']['etc_readonly']and report['isolation']['run_readonly']and set(report['isolation']['effective_capabilities'])=={'0'}):raise RuntimeError('READONLY_HOST_CAPABILITIES_REQUIRED')
 selected=[x.strip()for x in os.environ.get('QA_CASES','move1,move2,forward,vendor').split(',')if x.strip()]
 report['selected_cases']=selected
 for name in selected:
  if name=='move1':run_case(1)
  elif name=='move2':run_case(2)
  elif name=='forward':run_case(2,forward=True)
  elif name=='vendor':run_vendor_case()
  else:raise ValueError('unknown QA case '+name)
except BaseException as error:report['errors'].append({'type':type(error).__name__,'message':str(error)});raise
finally:
 report['verdict']='PASS'if report['cases']and len(report['cases'])==len(report.get('selected_cases',[]))and not report['errors']and all(r.get('verdict')=='PASS'for r in report['cases'])else'FAIL';save();print(json.dumps({'verdict':report['verdict'],'path':str(REPORT),'errors':report['errors']},indent=2))
if report['verdict']!='PASS':raise SystemExit(1)
