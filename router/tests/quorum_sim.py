"""Heartbeat rule study: the current rule (one echo per beat, 1.1.1.1 / 8.8.8.8 alternating) against the k-of-n quorum
(quorum.py: 3 rotating targets, a beat is lost when 2 of 3 got no reply). Both use the unchanged suspicion rule of
fast_detect.lua: LOSSES (2) lost beats in a row of an armed channel; a suspect disarms the channel until a beat is
answered (one episode per outage). SIMULATOR, not the router. GL-SENSORS-2026-11-04.ru.md, item 4.

Scenarios (1 beat per second):
  healthy-p     tunnel up, every echo lost independently with probability p
  filtered      tunnel up, one target never answers (ICMP filtered on the path), the others lose p = 0.2 %
  flaky         tunnel up, one target loses 30 %, the others 0.2 %
  blackout      tunnel down from a random second: every echo lost -> detection delay in beats
  partial-q     tunnel loses every packet with probability q (both ways together) -> mean delay, detected within 10 s
Metrics: false suspects per day (healthy scenarios), detection delay (seconds from the outage start to the suspect),
echoes per beat (CPU and traffic). python router/tests/quorum_sim.py [days] -> table + JSON on stdout.
"""
import json
import random
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import quorum  # noqa: E402

LOSSES=2
ALT=('1.1.1.1','8.8.8.8')


class Alternating:
    echoes=1

    def __init__(self):
        self.round=0

    def beat(self,answer,now):
        target=ALT[self.round%2];self.round+=1
        return 'ok' if answer(target) else 'lost'


class Quorum:
    echoes=quorum.ACTIVE

    def __init__(self,rng):
        self.pool=quorum.Pool(start=rng.randrange(len(quorum.POOL)))

    def beat(self,answer,now):
        return self.pool.judge({t:answer(t) for t in self.pool.targets()},now)


def run(rule,answer_of,seconds,outage_at=None):
    """Returns (false suspects before outage_at, delay of the first suspect after outage_at or None)."""
    lost=0;armed=True;false=0
    for now in range(seconds):
        down=outage_at is not None and now>=outage_at
        verdict=rule.beat(lambda target:answer_of(target,down),now)
        if verdict=='ok':lost=0;armed=True
        else:lost+=1
        if armed and lost>=LOSSES:
            if down:return false,now-outage_at+1  # the beat's reply is read one second later
            false+=1;armed=False
    return false,None


def healthy(rule_factory,rng,days,loss_of):
    seconds=86400*days
    answer=lambda target,down:rng.random()>=loss_of(target)
    false,_=run(rule_factory(),answer,seconds)
    return false/days


def outage(rule_factory,rng,trials,q):
    delays=[];within=0
    for _ in range(trials):
        start=rng.randrange(30,90)
        answer=lambda target,down:not (down and rng.random()<q) and rng.random()>=0.002
        _,delay=run(rule_factory(),answer,start+300,outage_at=start)
        if delay is not None:
            delays.append(delay)
            if delay<=10:within+=1
    return {'mean_delay_s':round(sum(delays)/len(delays),2) if delays else None,'detected_10s':round(within/trials,3)}


def study(days=3,trials=400,seed=20261104):
    rng=random.Random(seed)
    rules={'current':lambda:Alternating(),'quorum':lambda:Quorum(rng)}
    result={}
    for name,factory in rules.items():
        row={'echoes_per_beat':factory().echoes}
        for p in (0.002,0.01,0.05):
            row['healthy_%g'%p]=round(healthy(factory,rng,days,lambda target,p=p:p),3)
        row['filtered']=round(healthy(factory,rng,days,lambda target:1.0 if target=='8.8.8.8' else 0.002),3)
        row['flaky']=round(healthy(factory,rng,days,lambda target:0.3 if target=='8.8.8.8' else 0.002),3)
        row['blackout']=outage(factory,rng,trials,1.0)
        for q in (0.3,0.5,0.8):row['partial_%g'%q]=outage(factory,rng,trials,q)
        result[name]=row
    return result


if __name__=='__main__':
    days=int(sys.argv[1]) if len(sys.argv)>1 else 3
    out=study(days=days)
    keys=[k for k in out['current'] if k!='echoes_per_beat']
    print('%-22s %14s %14s'%('metric','current','quorum 2/3'))
    print('%-22s %14s %14s'%('echoes per beat',out['current']['echoes_per_beat'],out['quorum']['echoes_per_beat']))
    for k in keys:
        a,b=out['current'][k],out['quorum'][k]
        if isinstance(a,dict):
            print('%-22s %14s %14s'%(k+' delay s',a['mean_delay_s'],b['mean_delay_s']))
            print('%-22s %14s %14s'%(k+' within 10 s',a['detected_10s'],b['detected_10s']))
        else:print('%-22s %14s %14s'%(k+' false/day',a,b))
    print(json.dumps(out,sort_keys=True))
