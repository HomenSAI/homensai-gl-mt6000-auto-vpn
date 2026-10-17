"""Loss-aware cumulative evidence for the isolated protocol soak only."""
import argparse,json,math,os,re,time
from pathlib import Path

class Evidence:
    def __init__(self):
        self.seen=set();self.last_total=0;self.missing=0;self.by_check={};self.selected={p:0 for p in ('wga','wgb','ova','ovb')};self.standby=dict(self.selected)
    def observe(self,row):
        counts=row.get('counts',{})
        if not isinstance(counts,dict) or any(k not in ('PASS','FAIL') or type(v) is not int or not 0<=v<=10000000 for k,v in counts.items()):raise ValueError('EVIDENCE-COUNTER-TYPE')
        total=sum(counts.get(k,0) for k in ('PASS','FAIL'))
        if type(total) is not int or total<self.last_total:raise ValueError('EVIDENCE-COUNTER-RESET')
        fresh=[]
        for event in row.get('recent',[]):
            stamp=event.get('time');name=event.get('check');result=event.get('result')
            if type(stamp) not in (int,float) or not math.isfinite(stamp) or not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',name) or result not in ('PASS','FAIL'):raise ValueError('EVIDENCE-EVENT')
            key=(stamp,name,result)
            if key not in self.seen:self.seen.add(key);fresh.append(event)
        expected=total-self.last_total
        if len(fresh)>expected:raise ValueError('EVIDENCE-INCONSISTENT')
        self.missing+=expected-len(fresh);self.last_total=total
        for event in fresh:
            name=event['check'];result=event['result'];value=self.by_check.setdefault(name,{'PASS':0,'FAIL':0});value[result]+=1
            for prefix,target in (('soak-selected-',self.selected),('soak-parallel-reserve-',self.standby)):
                if name.startswith(prefix) and result=='PASS' and name[len(prefix):] in target:target[name[len(prefix):]]+=1
        if len(self.seen)>30000:raise ValueError('EVIDENCE-RETENTION-BOUND')
    def public(self,row):
        return {'producer_state':row['state'],'source_sha256':row['source_sha256'],'cycles':row.get('cycles',0),'counts':row.get('counts',{}),'observed_events':len(self.seen),'missing_events':self.missing,'coverage_complete':self.missing==0,'selected_verified':self.selected,'standby_verified':self.standby,'by_check':self.by_check,'scope':'synthetic namespace traffic only; not physical router statistics','physical_router_access':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--source-sha256',required=True);args=parser.parse_args()
    if not re.fullmatch('/tmp/homensai-protocol-lab-[a-z0-9]+',args.root) or not re.fullmatch('[a-f0-9]{64}',args.source_sha256):raise ValueError('COLLECTOR-BOUNDS')
    if "DISTRIB_TARGET='x86/64'" not in Path('/etc/openwrt_release').read_text() or not Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file():raise ValueError('ISOLATED-GUEST-REQUIRED')
    root=Path(args.root)
    if root.is_symlink() or not root.is_dir() or root.stat().st_uid!=os.geteuid():raise ValueError('COLLECTOR-ROOT')
    os.umask(0o077);value=Evidence();until=time.monotonic()+10800;last=None
    while time.monotonic()<until:
        path=root/'status.json'
        if path.is_symlink() or path.stat().st_size>1024*1024:raise ValueError('PRODUCER-BOUNDS')
        row=json.loads(path.read_text())
        if row.get('source_sha256')!=args.source_sha256:raise ValueError('PRODUCER-SOURCE-CHANGED')
        value.observe(row);last=value.public(row);last['collector_monotonic']=time.monotonic()
        temp=root/'series.tmp';temp.write_text(json.dumps(last,indent=2));os.replace(str(temp),str(root/'series.json'))
        if row['state'] in ('PASS','FAIL','STOPPED'):return
        time.sleep(5)
    raise RuntimeError('COLLECTOR-DEADLINE-UNCONFIRMED')
if __name__=='__main__':main()
