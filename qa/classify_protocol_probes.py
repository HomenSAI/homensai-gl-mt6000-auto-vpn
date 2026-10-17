"""Account for every raw probe against the frozen final-soak scenario, not retry assumptions."""
import argparse,csv,io,json,tarfile
from collections import Counter
from pathlib import Path
PROFILES=('wga','wgb','ova','ovb')

def classify(archive,observation):
 with tarfile.open(archive,'r:gz') as tar:rows=[json.loads(line) for line in tar.extractfile('probe-observations.jsonl').read().splitlines()]
 producer=observation['producer'];series=observation['series'];assert producer['state']==series['producer_state']=='PASS'
 result=[];at=0;selected=Counter();standby=Counter();rounds=0
 def take(profile,bound,kind,expected=None):
  nonlocal at
  row=rows[at];at+=1;sample=row['sample'];assert row['expected_profile']==profile and row['bound'] is bound
  healthy=sample['https'] is True and sample['dns'] is True and sample['profile']==profile and sample['error'] is None
  if expected is not None:assert healthy is expected
  result.append({'index':at,'class':kind,'profile':profile,'bound':bound,'dns_ok':sample['dns'],'https_ok':sample['https'],'error':sample['error'] or '', 'phase':sample['phase'],'elapsed_ms':sample['elapsed_ms'],'guest_timestamp':row['time']})
  return healthy
 def wait(profile,prefix):
  count=0
  while True:
   good=take(profile,True,prefix);count+=1;result[-1]['class']+='-success' if good else '-retry-negative'
   if good:return
   assert count<100
 def faults():
  nonlocal rounds
  rounds+=1
  take('wga',False,'fault-path-success',True);take('wga',True,'injected-negative',False)
  take('wgb',True,'fault-path-success',True);take('wgb',False,'fault-path-success',True);take('ova',False,'fault-path-success',True)
  wait('wga','recovery-wait');take('wga',False,'fault-path-success',True);take('wga',True,'injected-negative',False);take('ovb',True,'fault-path-success',True);take('wga',False,'injected-negative',False)
  for profile in PROFILES:take(profile,False,'fault-path-success',True)
 for profile in PROFILES:wait(profile,'startup-wait')
 faults()
 for cycle in range(producer['cycles']):
  if cycle and cycle%25==0:faults()
  profile=rows[at]['expected_profile'];take(profile,False,'soak-selected',True);selected[profile]+=1
  reserve=rows[at]['expected_profile'];assert reserve!=profile;take(reserve,True,'soak-standby',True);standby[reserve]+=1
 assert at==len(rows) and dict(selected)==series['selected_verified'] and dict(standby)==series['standby_verified']
 assert rounds==series['by_check']['root-network-unchanged-after-faults']['PASS']
 counts=Counter(row['class'] for row in result)
 summary={'result':'PASS','raw_probe_records':len(rows),'classes':dict(counts),'fault_rounds':rounds,'steady_state_probes':counts['soak-selected']+counts['soak-standby'],'steady_state_failures':0,'source_sha256':producer['source_sha256'],'scope':'raw synthetic scenario accounting; retry negatives are bounded startup/restoration only, never retry masking in steady-state soak','guest_timestamps_are_not_host_wall_clock':True,'physical_router_access':False}
 return result,summary

def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--observation',required=True);p.add_argument('--csv',required=True);p.add_argument('--summary',required=True);a=p.parse_args()
 rows,summary=classify(a.archive,json.loads(Path(a.observation).read_text()))
 with Path(a.csv).open('w',newline='',encoding='utf8') as stream:
  writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 Path(a.summary).write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':main()