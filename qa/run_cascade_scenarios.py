"""Reproducible offline cascade scenarios. All profiles/outcomes are synthetic."""
from pathlib import Path
import hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'router/files/usr/lib/homensai-vpn'))
from cascade_model import CascadeModel

def model():
    rows=[dict(id=p,protocol=proto,channel=channel,priority=rank,enabled=True,connected=True) for p,proto,channel,rank in [('a','openvpn','main',1),('b','openvpn','main',2),('c','openvpn','reserve',1),('d','wireguard','other',1)]]
    return CascadeModel(rows,'a',list('abcd'),'synthetic-generation')
def feed(m,now,failed):
    for identifier in m.profiles:
        for stamp in (now-2,now-1,now):m.probe(identifier,stamp,identifier not in failed)
def accept(m,tx,now,success=True):
    m.begin(tx['id'],now,tx['before'],m.generation);m.applied(tx['id'],now+1,tx['after'],m.generation)
    rollback=m.confirm(tx['id'],now+2,tx['after'],m.generation,success)
    if rollback:m.rolled_back(tx['id'],now+3,tx['before'],m.generation)
def run(count=256):
    totals={'series':count,'steps':0,'commits':0,'hop_rollbacks':0,'rpc_or_external_blocks':0,'invariant_failures':0}
    for seed in range(count):
        rng=random.Random(seed);m=model()
        for step in range(8):
            now=10+step*70;feed(m,now,{p for p in m.profiles if rng.random()<.6})
            rpc=rng.random()>.05;generation=m.generation if rng.random()>.03 else 'operator-edited'
            tx=m.plan(now,m.order,generation,rpc=rpc,worker_busy=rng.random()<.2)
            if tx:accept(m,tx,now,rng.random()>.3)
            totals['steps']+=1
            assert m.root==list('abcd') and set(m.order)==set(m.root)
        totals['commits']+=sum(e['type']=='commit' for e in m.history)
        totals['hop_rollbacks']+=sum(e['type']=='rollback-hop' for e in m.history)
        totals['rpc_or_external_blocks']+=m.phase in ('BLOCKED','RECOVERY-REQUIRED')
    example=model();chain=[]
    for now,dead in [(10,{'a'}),(80,{'a','b'}),(150,{'a','b','c'})]:
        feed(example,now,dead);tx=example.plan(now,example.order,example.generation);chain.append(tx['target']);accept(example,tx,now)
    for stamp in (220,250):example.probe('a',stamp,True)
    tx=example.plan(260,example.order,example.generation);accept(example,tx,260);chain.append(example.current)
    assert chain==list('bcda') and example.order==example.root
    return {'scope':'Synthetic pure model; no router, VPN or RPC transport','result':'PASS','seed_range':[0,count-1],**totals,'example_targets':chain,'example_root_restored':True,'model_sha256':hashlib.sha256((ROOT/'router/files/usr/lib/homensai-vpn/cascade_model.py').read_bytes()).hexdigest()}
if __name__=='__main__':print(json.dumps(run(),indent=2))
