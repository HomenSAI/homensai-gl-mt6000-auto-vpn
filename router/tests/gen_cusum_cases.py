"""Generate router/tests/cusum_cases.json: the shared cases of the CUSUM trigger (CUSUM-TRIGGER-2026-11-04.ru.md).

The expected values come from the Python modules (cusum.py, probe_policy.py); test_cusum.py checks that the file is
current AND states the meaning of the important cases by hand; tests/lua/test_cusum.lua replays every case against the
Lua twins. Run: python router/tests/gen_cusum_cases.py
"""
import json
import math
import random
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import cusum  # noqa: E402
import probe_policy  # noqa: E402

OUT=HERE/'cusum_cases.json'
SEED=20261104
A,B='1.1.1.1','8.8.8.8'
SOURCE,TARGET='wireguard:peer_7','wireguard:peer_8'
PAIR={'source':SOURCE,'target':TARGET}
SETTINGS={'interval':10,'probe_level':5}


def alternate(pattern):
    """'.'=answered, 'x'=lost echo of the target of its turn, '#'=lost without a target (refused send, missing link)."""
    return [[1 if c!='.' else 0,None if c=='#' else (A if i%2==0 else B)] for i,c in enumerate(pattern)]


def loss_cases():
    rng=random.Random(SEED)
    named=[
        ('nothing lost','.'*30),
        ('one lost echo','....x....'),
        ('two lost in a row stay below H','....xx........'),
        ('a blackout of any length never reaches H','..'+'x'*200+'..'),
        ('all refused never reaches H','..'+'#'*50),
        ('three of five lost fires','..xx.x....'),
        ('every second echo lost (one target only): gated','.x'*30),
        ('every second echo lost, then the other target too','.x.x.x.x.x'+'x.x.x.x'),
        ('lost with no target passes the gate','..##.#....'),
        ('a fire restarts the sum','..xx.x..xx.x..'),
        ('a long run counts twice only, the answers decay it','xxxxxx.x.......x'),
        ('sparse loss decays between losses','x'+'.'*7+'x'+'.'*7+'x'+'.'*7+'x'),
    ]
    beats=[(name,alternate(pattern)) for name,pattern in named]
    # the gate window to the beat: the run keeps the sum at 7.82 (capped losses add 0 and do not decay it), one target lost
    # exactly GATE beats before the fire is outside, GATE-1 beats before is inside
    lead=[[1,A],[1,A]]
    beats.append(('the other target lost exactly GATE beats ago is outside',lead+[[1,B]]+[[1,A]]*3+[[0,A]]*4+[[1,A]]))
    beats.append(('the other target lost GATE-1 beats ago is inside',lead+[[1,A],[1,B]]+[[1,A]]*2+[[0,A]]*4+[[1,A]]))
    for share in (0.002,0.01,0.05,0.1,0.2,0.3,0.4,0.5,0.8):
        for k in range(3):
            pattern=''.join('x' if rng.random()<share else '.' for _ in range(400))
            beats.append(('random %.3f #%d'%(share,k),alternate(pattern)))
    cases=[]
    for name,seq in beats:
        c=cusum.LossCusum();fired=[]
        trace=[]
        for i,(lost,target) in enumerate(seq):
            if c.feed(lost==1,target):fired.append(i)
            trace.append(round(c.s,9))
        cases.append({'name':name,'beats':seq,'fired':fired,'trace':trace,'gated':c.gated,'count':c.fired})
    return cases


def rtt_trace(rng,kind):
    """(rtt or None, target) per beat: log-normal noise, two targets with different distances."""
    out=[]
    for i in range(1500):
        target=A if i%2==0 else B
        level=(20.0 if target==A else 45.0)
        t=i-400
        factor=1.0
        if kind=='creep120' and t>0:factor=3.0**min(t/120.0,1.0)
        elif kind=='creep600' and t>0:factor=3.0**min(t/600.0,1.0)
        elif kind=='pulse' and 0<t<200:factor=4.0
        elif kind=='step' and t>0:factor=3.0
        rtt=level*factor*math.exp(rng.gauss(0.0,0.2))
        if rng.random()<0.005:rtt*=rng.uniform(2.0,5.0)
        if rng.random()<0.01:rtt=None
        out.append([None if rtt is None else round(rtt,3),target])
    return out


def rtt_cases():
    rng=random.Random(SEED+1)
    cases=[]
    for kind in ('flat','creep120','creep600','pulse'):
        cases.append(('%s'%kind,rtt_trace(rng,kind)))
    cases.append(('a level that stays is the new normal',rtt_trace(rng,'step')+[[round(60.0*math.exp(rng.gauss(0,0.2)),3),A if i%2==0 else B] for i in range(2600)]))
    cases.append(('no answers at all',[[None,A]]*200))
    cases.append(('single target',[[round(30.0*math.exp(rng.gauss(0,0.1)),3),A] for _ in range(300)]))
    cases.append(('a target with too few answers gets no base',[[round(30.0*math.exp(rng.gauss(0,0.1)),3),A if i%40 else 'x'] for i in range(300)]))
    cases.append(('garbage values are no answers',[[0,A],[-5,A],[None,A]]*50))
    out=[]
    for name,seq in cases:
        w=cusum.RttWatch();states=[]
        for rtt,target in seq:states.append(w.feed(rtt,target))
        # run-length form of the states: the file stays small and every change of state is pinned
        runs=[]
        for s in states:
            if runs and runs[-1][0]==s:runs[-1][1]+=1
            else:runs.append([s,1])
        out.append({'name':name,'beats':seq,'states':runs,'raised':w.raised,'relearned':w.relearned,
                    'z':round(w.z,9),'drift':round(w.drift,9),'learning':w.base is None})
    return out


class Memory:
    """Booster with its files in RAM (the same steps replay against the Lua twin)."""
    def __init__(self):
        self.tmp=tempfile.TemporaryDirectory()
        path=Path(self.tmp.name)
        self.b=probe_policy.Booster(path,path,lambda p,v:None,lambda p,d:d)


def row(profile,good):
    if good:return {'id':profile,'code':None,'dns_ok':True,'https_success':3}
    return {'id':profile,'code':'VPN-003','dns_ok':True,'https_success':0}


def snapshot(b,started):
    state=b.state;dense=state.get('dense')
    rest=(state.get('suspicion_rest') or {}).get(SOURCE) or {}
    records=state.get('cusum_at') if isinstance(state.get('cusum_at'),dict) else {}
    forced=records.get(SOURCE) if isinstance(records.get(SOURCE),dict) else {}
    return {'started':started,'records':len(records),'reason':dense.get('reason') if dense else None,'bad':bool(dense.get('bad')) if dense else None,
            'rest_until':rest.get('until'),'alarms':rest.get('false_alarms'),'at':forced.get('at'),'clean':forced.get('clean')}


def play(steps):
    memory=Memory();b=memory.b;out=[]
    for step in steps:
        kind=step[0]
        if kind=='suspect':
            _,now,reason,models,native=step
            started=b.suspect(SETTINGS,[{'profile':SOURCE,'reason':reason,'evidence':{'losses':0,'cause':'cusum','other':1}}],PAIR,native,now,models)
        elif kind=='observe':
            _,now,good,native,models=step
            started=None
            b.observe(SETTINGS,[row(SOURCE,good),row(TARGET,True)],PAIR,native,now,models)
        else:
            _,key,value=step
            started=None
            b.state[key]=value
        out.append(snapshot(b,started))
    return out


def S(now,reason='cusum-loss',models=None,native='OBSERVING'):return ['suspect',now,reason,models,native]
def O(now,good=True,native='OBSERVING',models=None):return ['observe',now,good,native,models]


def clean_episode(now):
    return [S(now),O(now+4),O(now+8)]


def booster_cases():
    named={}
    named['the rest stops an ordinary reason, not the CUSUM reason']=[
        S(1000,'rx-stall'),O(1004),O(1008),S(1010,'rx-stall'),S(1011)]
    named['a running episode declines everything']=[S(1000),S(1001),S(1002,'rx-stall')]
    named['outside the watching states nothing starts']=[S(1000,native='APPLYING'),S(1001,native='BLOCKED')]
    named['three failed checks: nothing to add']=[O(1000,False),O(1010,False),O(1020,False),S(1021)]
    named['the decided failure model declines the CUSUM reason only']=[
        S(1000,models={SOURCE:{'failed':True}}),S(1001,'rx-stall',models={SOURCE:{'failed':True}})]
    named['the undecided failure model does not decline']=[S(1000,models={SOURCE:{'failed':False}})]
    # clean episodes: two free, then 60, 120, 240, 480, 600, 600 s after the end of the episode
    steps=[];now=1000
    for gap in (0,0,0,60,120,240,480,600,600):
        steps+=[S(now+gap-1)] if gap else []
        steps+=clean_episode(now+gap)
        now=now+gap+8
    named['clean episodes lengthen the gap']=steps
    named['a failed dense check clears the count']=clean_episode(1000)+clean_episode(1010)+clean_episode(1020)+[
        S(1029),S(1089)]+[O(1093,False),O(1097),O(1101),S(1102)]
    named['an episode of another reason with a failed check clears it too']=clean_episode(1000)+clean_episode(1010)+clean_episode(1020)+[
        O(1090),S(1200,'rx-stall'),O(1204,False),O(1208),O(1212),S(1213)]
    named['an episode of another reason ending clean counts nothing']=clean_episode(1000)+[S(2000,'rx-stall'),O(2004),O(2008)]
    named['an expired episode counts as clean']=[S(1000),O(1061,False),S(1062)]+[O(1066),O(1070),S(1071)]
    named['a switch ends the episode without a found failure']=[S(1000),O(1004,native='APPLYING')]
    named['a wall clock stepped back does not lock the channel']=clean_episode(5000)+clean_episode(5010)+clean_episode(5020)+[S(100)]
    for name,value in (('text','x'),('number',5),('without at',{SOURCE:{'clean':3}}),('negative',{SOURCE:{'at':1.0,'clean':-1}}),
                       ('float clean',{SOURCE:{'at':1.0,'clean':1.5}}),('boolean at',{SOURCE:{'at':True,'clean':4}}),('text at',{SOURCE:{'at':'1','clean':4}})):
        named['a damaged record counts as none: '+name]=[['set','cusum_at',value],S(1000)]
    named['a record of a channel outside the pair is dropped']=[['set','cusum_at',{'other:1':{'at':1.0,'clean':1}}],S(1000)]
    out=[]
    for name,steps in named.items():
        out.append({'name':name,'steps':steps,'expected':play(steps)})
    return out


def main():
    # floats are rounded: the last digits of log and exp differ between C libraries, and the file must be the same on all
    data={'seed':SEED,'constants':{'lost_step':round(cusum.LOST_STEP,12),'kept_step':round(cusum.KEPT_STEP,12),'h':cusum.H,'cap':cusum.CAP,'gate':cusum.GATE,
                                   'p0':cusum.P0,'p1':cusum.P1},
          'gaps':[[clean,probe_policy.cusum_gap(clean)] for clean in range(0,12)],
          'loss':loss_cases(),'rtt':rtt_cases(),'booster':booster_cases()}
    text=json.dumps(data,ensure_ascii=False,separators=(',',':'),sort_keys=True)+'\n'
    if len(sys.argv)>1 and sys.argv[1]=='--text':return text
    with open(str(OUT),'w',encoding='utf-8',newline='\n') as handle:handle.write(text)
    print(OUT,len(text))
    return text


if __name__=='__main__':
    main()
