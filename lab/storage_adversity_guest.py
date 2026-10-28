"""Actual disposable tmpfs ENOSPC and corruption; no real configuration writes."""
import errno,hashlib,json,subprocess,sys,tempfile,time
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
sys.path.insert(0,'/usr/lib/homensai-vpn');import agent
assert agent.VERSION=='0.9.1-alpha49'
checks=[];mounted=False;result={'state':'RUNNING','scope':'disposable 64KiB tmpfs and synthetic timestamps; not physical flash wear','physical_router_access':False}
def protected():
 return hashlib.sha256(subprocess.check_output(['uci','export','network'])+subprocess.check_output(['uci','export','firewall'])+subprocess.check_output(['ip','-4','route','show','table','main'])).hexdigest()
base=protected()
try:
 with tempfile.TemporaryDirectory(prefix='hs-storage-') as d:
  root=Path(d)
  try:
   subprocess.run(['mount','-t','tmpfs','-o','size=64k,nosuid,nodev','tmpfs',d],check=True,timeout=5);mounted=True;agent.PERSIST=root
   acc=agent.Accounting();agent.checkpoint(acc);acc.gaps=2;agent.checkpoint(acc)
   known=(root/'checkpoint.json').read_bytes()
   with (root/'filler').open('wb',buffering=0) as fill:
    try:
     while True:fill.write(bytes(4096));fill.flush()
    except OSError as error:assert error.errno==errno.ENOSPC
   try:agent.checkpoint(acc);raise AssertionError('FULL-FILESYSTEM-NOT-REFUSED')
   except OSError as error:assert error.errno==errno.ENOSPC
   assert (root/'checkpoint.json').read_bytes()==known;checks.append('ENOSPC-known-checkpoint-preserved')
   (root/'filler').unlink();agent.checkpoint(acc);checks.append('write-recovers-after-space-freed')
   bad={'version':1,'saved':time.time(),'accounting':{'months':[]}}
   (root/'checkpoint.json').write_text(json.dumps({'data':bad,'sha256':agent.checksum(bad)}))
   restored,error=agent.restore();assert error=='STORAGE-RECOVERED' and isinstance(restored.months,dict);checks.append('checksummed-invalid-schema-recovers-backup')
   agent.checkpoint(restored);assert agent.restore()[1] is None;checks.append('corrupt-current-replaced-safely')
   stamp=time.time();a=agent.Accounting()
   for at,rx in [(stamp,100),(stamp+30,400),(stamp+20,300),(stamp+50,600),(stamp+86400,900)]:a.sample('tun0',1,rx,rx,at)
   assert a.gaps>=2 and sum(row['rx'] for row in a.months.values())==300;checks.append('backward-forward-clock-gaps-no-invented-bytes')
  finally:
   if mounted:subprocess.run(['umount',d],check=True,timeout=5);mounted=False
 assert protected()==base;checks.append('protected-config-network-unchanged')
 result.update(state='PASS',checks=checks,temporary_mount_cleaned=True)
except Exception as error:result.update(state='FAIL',checks=checks,exception_type=type(error).__name__,errno=getattr(error,'errno',None),code=str(error) if isinstance(error,AssertionError) else 'STORAGE-LAB-ERROR',temporary_mount_cleaned=not mounted)
result['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
Path('/tmp/hs-storage-adversity-result.json').write_text(json.dumps(result));print(json.dumps(result));raise SystemExit(0 if result['state']=='PASS' else 1)
