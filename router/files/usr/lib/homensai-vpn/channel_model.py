"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
channel_model.py: the channel-failure detector of Auto (owner decision 03.11.2026). Read-only, pure functions.

Lua twin: lua/channel_model.lua (tests/hmm_detector_cases.json, generated from this module by
tests/gen_hmm_detector_cases.py; both runtimes give the same probabilities within 1e-9 and the same decisions).
Study: private/math/detection/REPORT.ru.md (section 6 is the specification implemented here);
design note: docs/architecture/HMM-DETECTOR-2026-11-03.ru.md.

option failure_model (inventory.lua):
  'hmm'          default, "standard": 6-state hidden Markov model (Gilbert-Elliott channel with several kinds of
                 "bad"); leave the channel when P(the failure lasts >= 20 s more) >= 0.8, short blackout mean 4 s;
  'hmm-fast'     "fast": the same model, theta 0.7 and short blackout mean 3 s (leaves ~4 s earlier, but also on
                 ~70 % of 20 s blackouts);
  'consecutive'  the previous rule: recovery_failures (3) failed samples in a row (failover_plan.streak).

States G healthy | L light loss (stay) | M heavy loss (leave) | B short blackout (transient) | X long outage (leave)
| N DNS dead, HTTPS works (leave). Star-shaped continuous-time chain: G -> s at LAM[s] per second, s -> G with mean
duration DUR[s]. Between two observations dt seconds apart (dt = clamp(known - last known, 0, 600), the first one 10;
known = sample time + delay(): when the result became known - a VPN-003 waited 6 s (dense 3 s), a DNS-001 3 s,
anything else 2.5 s - the clock of the calibrated study):
    g = exp(-sum(LAM) dt);  e_s = exp(-dt / DUR[s])
    pi'_G = pi_G g + sum_s pi_s (1 - e_s);   pi'_s = pi_s e_s + pi_G (LAM[s] / sum(LAM)) (1 - g)
then pi'_s *= EMIS[s][cadence][obs], normalise, floor 1e-9, normalise again (renormalised every step: numerically
stable, no state ever becomes impossible). Decision: persist = sum over M, B, X, N of pi_s exp(-20 / DUR[s]) (the
probability that the failure goes on for at least the 20 s a switch costs); leave iff persist >= theta.
Observation of a sample (the monitor's code): O healthy (code null, DNS ok, >= 2 of 3 HTTPS), D DNS-001,
H VPN-003 / VPN-001 / VPN-MTU (the large-packet black hole is a hard failure of user traffic); any other code is
not an observation (the state is not advanced). Cadence: the sample's `dense` flag (the monitor's dense
confirmation pass, 3 s HTTPS wait) or, without it, a gap of at most DENSE_GAP s to the channel's previous sample.

State per channel = the 6 probabilities + the newest observation time. It is never stored separately: it is
replayed from the generation-scoped samples of the last WINDOW seconds in status.json (the monitor's own RAM file),
starting from G - deterministic like streak(), identical after an Auto restart or a Lua/Python handover, and reset
to "healthy" only together with the evidence itself (reboot, new vendor generation), where streak() resets too.
"""
import math

MODELS=('hmm','hmm-fast','consecutive')
DEFAULT='hmm'
STATES=('G','L','M','B','X','N')
BAD=(2,3,4,5)                # M, B, X, N: the states Auto leaves for (B only when it lasts)
OBS={'O':0,'D':1,'H':2}
HARD=frozenset({'VPN-003','VPN-001','VPN-MTU'})
# EMIS[state] = (normal pass O, D, H, dense pass O, D, H): calibrated on the MT3000 soak logs (study section 2.3)
EMIS=((0.994,0.004,0.002,0.994,0.004,0.002),
      (0.8717,0.1233,0.0050,0.8647,0.1209,0.0144),
      (0.2520,0.2087,0.5393,0.1042,0.0784,0.8174),
      (0.010,0.010,0.980,0.010,0.010,0.980),
      (0.010,0.010,0.980,0.010,0.010,0.980),
      (0.020,0.970,0.010,0.020,0.970,0.010))
LAM=(1/7200.0,1/21600.0,4/21600.0,1/21600.0,1/604800.0)    # L M B X N, per second
DUR=(1800.0,1800.0,4.0,900.0,1800.0)                          # L M B X N, seconds (B: the preset's dur_B)
PRESETS={'hmm':{'theta':0.8,'dur_b':4.0},'hmm-fast':{'theta':0.7,'dur_b':3.0}}
COST=20.0          # seconds a switch costs: leave only for a failure expected to outlast it
SUSPECT=0.2        # 1 - pi_G - pi_L: the monitor runs dense confirmation passes from here on
HEALTHY=0.90       # pi_G a primary needs before a planned return from a healthy reserve (owner 03.11.2026: 0.95 -> 0.9)
CLEAN=300          # ... or that many seconds of consecutive healthy samples (bounds the wait after heavy loss)
FLOOR=1e-9
WINDOW=600.0       # seconds of samples replayed
FIRST_DT=10.0
DT_MAX=600.0
DENSE_GAP=7.0      # normal passes are >= 10 s apart, dense ones 4-6.5 s
HTTP_NORMAL=6.0;HTTP_DENSE=3.0;DNS_WAIT=3.0;PUBLISHED=2.5   # probe_deadline / agent.dns_probe waits; usual publication


def name(settings):
    value=settings.get('failure_model') if isinstance(settings,dict) else None
    return value if value in MODELS else DEFAULT


def params(model):
    """The constants of one HMM preset (None for 'consecutive')."""
    preset=PRESETS.get(model)
    if preset is None:return None
    dur=(DUR[0],DUR[1],preset['dur_b'],DUR[3],DUR[4])
    total=LAM[0]+LAM[1]+LAM[2]+LAM[3]+LAM[4]
    return {'model':model,'theta':preset['theta'],'dur':dur,'lam':LAM,'total':total,
            'ratio':tuple(x/total for x in LAM),'weight':tuple(math.exp(-COST/d) for d in dur)}


def observation(sample):
    """0 O / 1 D / 2 H, or None when the sample is not an observation of the channel's health."""
    code=sample.get('code')
    if code is None:
        https=sample.get('https_success')
        return 0 if sample.get('dns_ok') is True and type(https) is int and https>=2 else None
    if code=='DNS-001':return 1
    if code in HARD:return 2
    return None


def step(pi,dt,obs,dense,p):
    """One predict + update. pi: 6 probabilities (G L M B X N). Returns a new list (the Lua twin updates in place)."""
    g=math.exp(-p['total']*dt)
    gone=1-g
    out0=pi[0]*g
    out=[0.0]*6
    for i in range(1,6):
        e=math.exp(-dt/p['dur'][i-1])
        out0+=pi[i]*(1-e)
        out[i]=pi[i]*e+pi[0]*p['ratio'][i-1]*gone
    out[0]=out0
    k=obs+(3 if dense else 0)
    z=0.0
    for i in range(6):
        out[i]*=EMIS[i][k]
        z+=out[i]
    if not z>0:z=1.0
    w=0.0
    for i in range(6):
        out[i]=max(FLOOR,out[i]/z)
        w+=out[i]
    for i in range(6):out[i]/=w
    return out


def persist(pi,p):
    """P(the failure lasts at least COST more seconds)."""
    w=p['weight']
    return pi[2]*w[1]+pi[3]*w[2]+pi[4]*w[3]+pi[5]*w[4]


def remaining(pi,p):
    """Expected remaining failure seconds (memoryless; reported, not used for the decision)."""
    d=p['dur']
    return pi[2]*d[1]+pi[3]*d[2]+pi[4]*d[3]+pi[5]*d[4]


def delay(code,dense):
    """Seconds after the sample's start when its result is known (the study's timing): a VPN-003 waited the
    whole HTTPS wait (6 s, dense 3 s), a DNS-001 the DNS wait (3 s), anything else the usual publication delay."""
    if code=='VPN-003':return HTTP_DENSE if dense else HTTP_NORMAL
    if code=='DNS-001':return DNS_WAIT
    return PUBLISHED


def replay(points,p):
    """points: one channel's samples, ascending, unique stamps. -> (pi, newest observation time, observations).
    The model's clock is when each result became known (sample time + delay), as in the calibrated study."""
    pi=[1.0,0.0,0.0,0.0,0.0,0.0]
    last=None;seen=None;previous=None;count=0
    for point in points:
        t=point['time']
        obs=observation(point)
        if obs is not None:
            dense=point.get('dense')
            if type(dense) is not bool:dense=previous is not None and t-previous<=DENSE_GAP
            known=t+delay(point.get('code'),dense)
            dt=FIRST_DT if seen is None else min(max(known-seen,0.0),DT_MAX)
            pi=step(pi,dt,obs,dense,p)
            last=t;seen=known;count+=1
        previous=t
    return pi,last,count


def window(samples,identifier,now):
    """The channel's samples of the last WINDOW s, ascending, one per stamp; None when two disagree."""
    from failure_diagnosis import finite
    if not isinstance(samples,list) or not finite(now):return None
    seen={};points=[]
    for point in samples:
        if not isinstance(point,dict) or point.get('id')!=identifier:continue
        t=point.get('time')
        if not finite(t) or not 0<=now-t<=WINDOW:continue
        health=(point.get('code'),point.get('dns_ok'),point.get('https_success'))
        if t in seen:
            if seen[t]!=health:return None
            continue
        seen[t]=health;points.append(point)
    points.sort(key=lambda s:s['time'])
    return points


_MEMO={}


def evaluate(samples,identifier,now,max_age,model,profile=None):
    """The channel's model view now: dict, or None for 'consecutive', unknown or conflicting evidence.
    failed/suspect/healthy are False when the newest observation is older than max_age or the channel's newest
    sample is no observation (like streak)."""
    from failure_diagnosis import finite,scoped_samples
    p=params(model)
    if p is None or not finite(max_age) or max_age<=0:return None
    if profile is not None:samples=scoped_samples(samples,profile)
    points=window(samples,identifier,now)
    if points is None:return None
    # Auto ticks every 2 s, samples arrive every 4-10 s: the replay of an unchanged window is remembered
    # (published samples never change; the key changes with every new or expired sample).
    key=(model,identifier,len(points),sum(s['time'] for s in points),
         sum(i*(4+(observation(s) if observation(s) is not None else 3)+(8 if s.get('dense') is True else 0)+16*delay(s.get('code'),True)) for i,s in enumerate(points,1)))
    if key in _MEMO:pi,last,count=_MEMO[key]
    else:
        pi,last,count=replay(points,p)
        if len(_MEMO)>=16:_MEMO.clear()
        _MEMO[key]=(tuple(pi),last,count)
    pi=list(pi)
    # like streak(): a newest sample that is no observation (CHECK-001, ROUTE-001, ...) leaves no decision
    fresh=last is not None and now-last<=max_age and observation(points[-1]) is not None
    chance=persist(pi,p);bad=1-pi[0]-pi[1]
    return {'model':model,'pi':pi,'time':last,'observations':count,'persist':chance,'p_bad':bad,
            'p_healthy':pi[0],'remaining':remaining(pi,p),
            'failed':fresh and chance>=p['theta'],'suspect':fresh and bad>=SUSPECT,'healthy':fresh and pi[0]>=HEALTHY}


def channel_failed(samples,identifier,count,now,max_age,settings,profile=None):
    """Auto's "the channel carrying traffic failed": the owner's model (failover_plan.streak for 'consecutive')."""
    model=name(settings)
    if model=='consecutive':
        from failover_plan import streak
        return streak(samples,identifier,count,now,max_age,False,profile)
    view=evaluate(samples,identifier,now,max_age,model,profile)
    return bool(view and view['failed'])


def return_ready(samples,identifier,count,now,max_age,settings,profile=None):
    """The extra gate of a planned return from a healthy reserve (HMM modes only; 'consecutive' always True):
    pi_G >= HEALTHY of the primary, or the primary stably healthy for CLEAN seconds (count successes, the
    recovery_settings.stable_success rule). Stops the return to a primary that keeps losing ~30 % (simulated:
    31 -> 1 switches a day); returns after blackouts and DNS failures are not delayed; after heavy loss the
    model may still see "light loss", so CLEAN bounds that wait (docs/architecture/HMM-DETECTOR-2026-11-03.ru.md)."""
    model=name(settings)
    if model=='consecutive':return True
    view=evaluate(samples,identifier,now,max_age,model,profile)
    if view and view['healthy']:return True
    from failure_diagnosis import scoped_samples
    from recovery_settings import stable_success
    points=scoped_samples(samples,profile) if profile is not None else samples
    if not isinstance(points,list):return False
    return stable_success([p for p in points if isinstance(p,dict)],identifier,count,CLEAN,now,max_age)


IDENTITY=('interface','vendor_tunnel_id','vendor_generation')


def row_view(samples,row,now,max_age,settings):
    """The monitor's public view of one measured channel (its current binding only), or None ('consecutive')."""
    model=name(settings)
    if model=='consecutive' or not isinstance(row,dict) or not isinstance(samples,list):return None
    identifier=row.get('id')
    points=[s for s in samples if isinstance(s,dict) and s.get('id')==identifier and all(s.get(k)==row.get(k) for k in IDENTITY)]
    return public(evaluate(points,identifier,now,max_age,model))


def public(view):
    """The status row field failure_model (one source for the page and the history)."""
    if not view:return None
    def rounded(x,scale):return math.floor(x*scale+0.5)/scale   # the Lua twin rounds the same way
    return {'model':view['model'],'p_bad':rounded(view['p_bad'],10000),'p_healthy':rounded(view['p_healthy'],10000),
            'persist':rounded(view['persist'],10000),'remaining_s':rounded(view['remaining'],10),'failed':view['failed'],
            'suspect':view['suspect'],'time':view['time'],'observations':view['observations']}
