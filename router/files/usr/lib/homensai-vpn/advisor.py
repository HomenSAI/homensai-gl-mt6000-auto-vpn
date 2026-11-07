"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
advisor.py: the network advisor of the master slider «Быстрая реакция ↔ Без лишних переключений» (2.1.0-alpha9,
owner design 04.11.2026). Pure functions + the nightly job (`advisor.py run`).

Lua twin: lua/advisor.lua (tests/advisor_cases.json, generated from this module by tests/gen_advisor_cases.py; the
same numbers within 1e-9 and the same decisions and texts). Design note: docs/architecture/NETWORK-ADVISOR-2026-11-04.ru.md.

Curve: slider_curve.json (the 11 anchors of the offline study private/math/master-slider; scripts/gen-slider-curve.py).
Between anchors every parameter is interpolated linearly and rounded to its product step (LOSSES to an integer), the
predicted metrics and the per-group numbers are interpolated.

Once a night the monitor starts `nice -n 19 ... run`: the journal (netjournal) of the window (1 / 7 / 30 completed
days, default 7, recent days weigh more: half-life window/2 days) is classified into events; the outages of the
primary are replayed through the real decision code (channel_model.step / persist with the candidate theta / dur_B),
the events the compressed journal cannot replay (loss episodes, flaps, reserve failures, noisy hours) take the
study's per-group numbers of the candidate t. Cost = downtime + LAMBDA (20 s) per unnecessary switch, as in the
study. Golden-section search over t when the cost over the 11 anchors is unimodal, else the best anchor; a shift
only when it saves >= 5 % against the current settings and the window has >= 5 events.

Fast end (FAST-SWITCH-2026-11-04.ru.md): the curve's fast_anchors t < 0 are steps, never interpolated (fast_anchor): -0.1 and
-0.2 add "or 3 / 2 failed samples in a row" (channel_model.leave_rule) and enter the search only when the owner enabled the
segment (option slider_fast, default off); t <= -0.3 is turbo (heartbeat verdict, dense 3 s): only the owner's explicit
opt-in (option slider_turbo) and position, never recommended; the advisor stays out of it while it runs.
"""
import json
import math
from pathlib import Path

import channel_model as C
import netjournal as J

HERE=Path(__file__).resolve().parent
CURVE_PATH=HERE/'slider_curve.json'
VERSION=1
MODES=('auto','advice','manual')
DEFAULT_MODE='advice'          # owner: auto becomes the default only after a 7-day advisor check on the router
WINDOWS=(1,7,30)
DEFAULT_WINDOW=7
MIN_EVENTS=5
MIN_SAVING=0.05
AUTO_STEP=0.1                  # auto mode: at most one anchor interval per change
AUTO_SPACING=20*3600           # ... and at most one change a day
RUN_AT=3*3600+30*60            # the nightly run, local time 03:30
RUN_SPACING=600                # a rerun after changed settings at most every 10 min
GOLDEN_TOL=0.02
# replay of one outage of the primary (calibrated against the study's leave / ride-out times, see the design note)
EXEC=2.0                       # decision -> traffic on the reserve
BLIP=1.5                       # LAN pause of one switch (the failover and the later return)
NORMAL=10.0                    # probe level 5: a check every 10 s
DENSE=(4.0,5.0,6.0)            # dense confirmation passes 4-6.5 s apart
PHASES=(0.0,2.0,4.0,6.0,8.0)   # where the outage begins between two normal checks
HISTORY=60.0                   # healthy checks before it
HORIZON=300.0
# classification of the journal
LOSSY=0.05;HEAVY=0.30;LOSSY_MIN_SAMPLES=5;LOSSY_MIN_SHORTS=2
FLAP_GAP=180;FLAP_MIN=3
NOISY_SHORT=15;NOISY_MIN=4
SHORT_MAX=15;MEDIUM_MAX=45
RESERVE_MIN=20
GROUPS=('short','medium','long','loss_light','loss_heavy','flap','reserve_fail','noisy')
TABLE_GROUPS=('loss_light','loss_heavy','flap','reserve_fail','noisy')
MIN_T=-0.7                     # the fastest position (turbo)
FAST_MIN_T=-0.2                # the fastest position without the turbo opt-in
SAFE={'theta':(0.5,0.99),'dur_b':(1.0,15.0),'pg':(0.5,0.99),'primary_stable':(30,600),'rescue_stable':(0,60)}
TRANSITION=('ARMED','APPLYING','WAIT-CLIENT','RESTORING')
RESULT_NAME='advisor.json'
REQUEST_NAME='advisor-request.json'
CHANGES_NAME='advisor-changes.json'
MAX_CHANGES=30


def floor(x):return int(math.floor(x))


def round2(x):return floor(x*100+0.5)/100


def number(v):
    return v if type(v) in (int,float) and math.isfinite(v) else None


def load_curve(path=None):
    curve=json.loads(Path(path or CURVE_PATH).read_text(encoding='utf-8'))
    anchors=curve.get('anchors')
    if not isinstance(anchors,list) or len(anchors)<2 or anchors[0]['t']!=0 or anchors[-1]['t']!=1:raise ValueError('ADVISOR-CURVE-INVALID')
    for a,b in zip(anchors,anchors[1:]):
        if not a['t']<b['t']:raise ValueError('ADVISOR-CURVE-INVALID')
    fast=curve.setdefault('fast_anchors',[])
    for a,b in zip([{'t':0}]+fast,fast):
        if not b['t']<a['t']:raise ValueError('ADVISOR-CURVE-INVALID')
    return curve


def round_step(x,step):
    value=floor(x/step+0.5)*step
    return int(floor(value+0.5)) if step>=1 else floor(value*100+0.5)/100


def lerp(a,b,f):
    if a is None or b is None:return None
    return a+f*(b-a)


def segment(curve,t):
    anchors=curve['anchors']
    t=min(1.0,max(0.0,t))
    i=0
    while i<len(anchors)-2 and anchors[i+1]['t']<=t:i+=1
    a,b=anchors[i],anchors[i+1]
    return a,b,(t-a['t'])/(b['t']-a['t'])


def fast_anchor(curve,t):
    """The step of a position t < 0: the fastest anchor it has reached, or None (not yet at -0.1: the anchor t = 0).
    A stricter detector turns on exactly at its anchor; nothing is interpolated here."""
    best=None
    for a in curve['fast_anchors']:
        if t<=a['t']+1e-9:best=a
    return best


def interpolate(curve,t):
    """Settings and predictions of the slider position t (<0 the fast steps, 0 fast reaction .. 1 no unnecessary switches)."""
    step=fast_anchor(curve,t) if t<0 else None
    if step is not None:
        out={'t':step['t']}
        for k,name in enumerate(curve['params']):out[name]=step['p'][k]
        out.update(zip(curve['fast_params'],step['x']))
        out['m']=list(step['m']);out['g']=[list(x) for x in step['g']]
        return out
    a,b,f=segment(curve,t)
    out={'t':round2(min(1.0,max(0.0,t)))}
    for k,name in enumerate(curve['params']):
        out[name]=round_step(lerp(a['p'][k],b['p'][k],f),curve['steps'][name])
    out['m']=[lerp(x,y,f) for x,y in zip(a['m'],b['m'])]
    out['g']=[[lerp(x[0],y[0],f),lerp(x[1],y[1],f)] for x,y in zip(a['g'],b['g'])]
    return out


# ------------------------------------------------------------------------------------------------------------
# replay of an outage through the decision code
# ------------------------------------------------------------------------------------------------------------
_KNOWN={}


def knowns(theta,dur_b,cons=None):
    """For every cadence variant: when the model decides on an outage that never ends (the time the deciding
    result became known, s after the outage began), or None within HORIZON. An outage of d s gives the same
    trajectory up to d, so this decides every d: a switch iff d > known (the late recheck cancels earlier).
    cons: the rule "or cons failed samples in a row" (channel_model.leave_rule)."""
    key=(theta,dur_b,cons)
    if key in _KNOWN:return _KNOWN[key]
    p=C.custom(theta,dur_b)
    out=[]
    for di in DENSE:
        for phase in PHASES:
            pi=[1.0,0.0,0.0,0.0,0.0,0.0];seen=None;tau=phase-HISTORY;dense=False;found=None;failed=0
            while tau<HORIZON:
                fail=tau>=0
                known=tau+((C.HTTP_DENSE if dense else C.HTTP_NORMAL) if fail else C.PUBLISHED)
                dt=C.FIRST_DT if seen is None else min(max(known-seen,0.0),C.DT_MAX)
                pi=C.step(pi,dt,2 if fail else 0,dense,p);seen=known
                if fail:failed+=1
                if fail and (C.persist(pi,p)>=theta or (cons is not None and failed>=cons)):
                    found=known;break
                suspect=1-pi[0]-pi[1]>=C.SUSPECT
                tau=max(tau+di,known) if suspect else tau+NORMAL
                dense=suspect
            out.append(found)
    if len(_KNOWN)>=64:_KNOWN.clear()
    _KNOWN[key]=out
    return out


def outcome(d,known):
    """Mean (downtime s, unnecessary switches, switches) of one outage of d s over the cadence variants."""
    down=0.0;unnecessary=0;switched=0
    for k in known:
        if k is not None and d>k:
            leave=k+EXEC;switched+=1
            down+=min(d,leave)+2*BLIP
            if d<=leave:unnecessary+=1
        else:down+=d
    n=len(known)
    return down/n,unnecessary/n,switched/n


_BEHAVIOUR={}


def behaviour(theta,dur_b,cons=None):
    """ride_out: the longest outage (s) the setting rides out in at least half of the cadence variants;
    leave: mean time from the outage start to the traffic on the reserve on a long outage (None: never leaves)."""
    key=(theta,dur_b,cons)
    if key in _BEHAVIOUR:return _BEHAVIOUR[key]
    known=knowns(theta,dur_b,cons)
    ride=0
    for d in range(1,int(HORIZON)+1):
        if outcome(d,known)[2]<0.5:ride=d
    leave=None
    if all(k is not None for k in known):leave=sum(k+EXEC for k in known)/len(known)
    if len(_BEHAVIOUR)>=64:_BEHAVIOUR.clear()
    _BEHAVIOUR[key]=(ride,leave)
    return ride,leave


def safety(params):
    """Violated safety rules of a setting (empty = safe): bounds, P(G) >= theta, rescue <= primary_stable and the
    ride-out shorter than the leave time (a setting that never leaves a dead channel is refused)."""
    codes=[]
    for key,(low,high) in SAFE.items():
        v=number(params.get(key))
        if v is None or not low<=v<=high:codes.append('ADVISOR-OUT-OF-BOUNDS');break
    if codes:return codes
    if params['pg']<params['theta']:codes.append('ADVISOR-PG-BELOW-THETA')
    if params['rescue_stable']>params['primary_stable']:codes.append('ADVISOR-RESCUE-ABOVE-STABLE')
    ride,leave=behaviour(params['theta'],params['dur_b'],params.get('cons_f'))
    if leave is None or not ride<leave:codes.append('ADVISOR-RIDE-NOT-BELOW-LEAVE')
    return codes


# ------------------------------------------------------------------------------------------------------------
# settings
# ------------------------------------------------------------------------------------------------------------
def option_int(settings,key,low,high,default):
    v=number(settings.get(key)) if isinstance(settings,dict) else None
    return int(v) if v is not None and v==int(v) and low<=v<=high else default


def mode(settings):
    v=settings.get('advisor_mode') if isinstance(settings,dict) else None
    return v if v in MODES else DEFAULT_MODE


def window(settings):
    v=settings.get('advisor_window') if isinstance(settings,dict) else None
    return v if type(v) is int and v in WINDOWS else DEFAULT_WINDOW


def slider_t(settings):
    v=number(settings.get('slider_t')) if isinstance(settings,dict) else None
    return round2(v) if v is not None and MIN_T<=v<=1 else None


def fast_enabled(settings):
    """The admin enabled the fast segment (option slider_fast, default off): the advisor may recommend -0.2 <= t < 0."""
    return isinstance(settings,dict) and settings.get('slider_fast') in (True,'1')


def t_floor(settings):
    """The fastest position allowed now: 0, FAST_MIN_T with the fast segment, MIN_T with the turbo opt-in on top."""
    if C.turbo_on(settings):return MIN_T
    return FAST_MIN_T if fast_enabled(settings) else 0


def nearest(curve,params):
    """The anchor that behaves most like a setting (ride-out and leave time, then the return parameters); ties -> the
    calmer end."""
    ride,leave=behaviour(params['theta'],params['dur_b'])
    best=None
    for a in curve['anchors']:
        p=dict(zip(curve['params'],a['p']))
        r,l=behaviour(p['theta'],p['dur_b'])
        dl=0.0 if leave is None and l is None else 100.0 if leave is None or l is None else (leave-l)/2
        dist=((ride-r)/2)**2+dl**2+((params['pg']-p['pg'])/0.05)**2+((params['primary_stable']-p['primary_stable'])/60)**2+((params['rescue_stable']-p['rescue_stable'])/5)**2
        if best is None or dist<=best[0]+1e-12:best=(dist,a['t'])
    return best[1]


def current(settings,curve):
    """What Auto runs with now and where it is on the slider."""
    model=C.name(settings)
    preset=C.PRESETS.get(model) or C.PRESETS['hmm']
    theta=C.numeric(settings,'hmm_theta');dur_b=C.numeric(settings,'hmm_dur_b');pg=C.numeric(settings,'return_pg')
    numeric=theta is not None or dur_b is not None or pg is not None
    params={'theta':preset['theta'] if theta is None else theta,'dur_b':preset['dur_b'] if dur_b is None else dur_b,
            'pg':C.HEALTHY if pg is None else pg,
            'primary_stable':option_int(settings,'recovery_primary_stable',30,600,120),
            'rescue_stable':option_int(settings,'recovery_rescue_stable',0,60,10)}
    t=slider_t(settings)
    extra=C.or_failures(settings);beats=C.heartbeat_k(settings)
    attached=False
    if t is not None and model!='consecutive':
        point=interpolate(curve,t)
        attached=all(abs(point[k]-params[k])<1e-9 for k in params) and extra==point.get('cons_f') and beats==point.get('beat_k')
    if attached:label='slider'
    elif not numeric and extra is None and beats is None and params['primary_stable']==120 and params['rescue_stable']==10:label='preset'
    else:label='custom'
    near=nearest(curve,params)
    return dict(params,failure_model=model,slider_t=t,attached=attached,label=label,nearest_t=near,
                t_ref=t if attached else near,or_failures=extra,beats=beats,fast=fast_enabled(settings),turbo=C.turbo_on(settings))


def settings_key(settings):
    cur=[mode(settings),window(settings),C.name(settings)]
    for key in ('hmm_theta','hmm_dur_b','return_pg','slider_t','recovery_primary_stable','recovery_rescue_stable'):
        v=number(settings.get(key)) if isinstance(settings,dict) else None
        cur.append('-' if v is None else '%g'%v)
    # the fast end only when it is in use (the key of every other router stays as it was)
    extra=C.or_failures(settings);beats=C.heartbeat_k(settings)
    if extra is not None or beats is not None or fast_enabled(settings):cur.append('fast%s/%s/%s'%(extra,beats,fast_enabled(settings)))
    return '|'.join(str(x) for x in cur)


# ------------------------------------------------------------------------------------------------------------
# journal -> events
# ------------------------------------------------------------------------------------------------------------
def day_weight(age,window_days):
    half=max(window_days/2.0,0.5)
    return 0.5**(age/half)


def triples(rec):
    o=rec.get('o') or []
    return [(o[i],o[i+1],o[i+2]) for i in range(0,len(o)-2,3)]


def events(days,today,window_days):
    """Weighted events of the window (completed days today-window .. today-1)."""
    ev={'outages':[],'groups':{g:0.0 for g in TABLE_GROUPS},'n':0,'days':0,'weight_days':0.0,
        'counts':{'outages':0,'short':0,'medium':0,'long':0,'loss_episodes':0,'flaps':0,'noisy_hours':0,'reserve_failures':0},
        'durations':[]}
    for day in sorted(days,key=lambda d:d['d']):
        age=today-1-day['d']
        if not 0<=age<window_days:continue
        w=day_weight(age,window_days)
        used=False
        for identifier in sorted(day['ch']):
            rec=day['ch'][identifier]
            outs=sorted(triples(rec))
            if rec.get('r')==1:
                for start,d,flags in outs:
                    if flags&1 and d>=RESERVE_MIN:
                        ev['groups']['reserve_fail']+=w;ev['counts']['reserve_failures']+=1;ev['n']+=1
                continue
            used=True
            ev['durations'].extend(d for _,d,_ in outs)
            # a loss slot: >= 5 % failed checks made of >= 2 short outages (a long outage or a flap is no loss)
            lossy=[False]*J.SLOTS
            for i,v in enumerate(rec['lp']):
                shorts,fails,total=J.unpack(v)
                lossy[i]=total>=LOSSY_MIN_SAMPLES and fails>=LOSSY*total and shorts>=LOSSY_MIN_SHORTS
            i=0
            while i<J.SLOTS:
                if not lossy[i]:
                    i+=1;continue
                j=i;fails=0;total=0
                while j<J.SLOTS and lossy[j]:
                    _,f,n=J.unpack(rec['lp'][j]);fails+=f;total+=n;j+=1
                group='loss_heavy' if fails>=HEAVY*total else 'loss_light'
                ev['groups'][group]+=w*2*(j-i);ev['counts']['loss_episodes']+=1;ev['n']+=1
                i=j
            rest=[(s,d) for s,d,_ in outs if not (d<=J.SHORT and lossy[min(J.SLOTS-1,max(0,floor(s/J.SLOT)))])]
            keep=[]
            k=0
            while k<len(rest):
                m=k
                while m+1<len(rest) and rest[m+1][0]-(rest[m][0]+rest[m][1])<FLAP_GAP:m+=1
                if m-k+1>=FLAP_MIN:
                    ev['groups']['flap']+=w;ev['counts']['flaps']+=1;ev['n']+=1
                else:keep.extend(rest[k:m+1])
                k=m+1
            hours={}
            for s,d in keep:
                if d<=NOISY_SHORT:hours[floor(s/3600)]=hours.get(floor(s/3600),0)+1
            noisy={h for h,c in hours.items() if c>=NOISY_MIN}
            for h in sorted(noisy):
                ev['groups']['noisy']+=w;ev['counts']['noisy_hours']+=1;ev['n']+=1
            for s,d in keep:
                if d<=NOISY_SHORT and floor(s/3600) in noisy:continue
                ev['outages'].append((d,w));ev['n']+=1;ev['counts']['outages']+=1
                ev['counts']['short' if d<=SHORT_MAX else 'medium' if d<=MEDIUM_MAX else 'long']+=1
        if used:
            ev['days']+=1;ev['weight_days']+=w
    ev['durations'].sort()
    ev['counts']['natural']=len(ev['durations'])
    return ev


def cost(ev,curve,theta,dur_b,t_table,cons=None):
    """(total, downtime, unnecessary) of the window's events for a setting: outages replayed with theta / dur_B (and
    the rule "or cons failed samples in a row"), the other groups from the curve at t_table."""
    known=knowns(theta,dur_b,cons)
    down=0.0;unnecessary=0.0
    for d,w in ev['outages']:
        a,b,_=outcome(d,known)
        down+=w*a;unnecessary+=w*b
    step=fast_anchor(curve,t_table) if t_table<0 else None
    a,b,f=(step,step,0.0) if step is not None else segment(curve,t_table)
    for index,group in enumerate(GROUPS):
        if group not in TABLE_GROUPS:continue
        weight=ev['groups'][group]
        if weight>0:
            down+=weight*lerp(a['g'][index][0],b['g'][index][0],f);unnecessary+=weight*lerp(a['g'][index][1],b['g'][index][1],f)
    return down+curve['lambda_s']*unnecessary,down,unnecessary


def cost_at(ev,curve,t):
    point=interpolate(curve,t)
    return cost(ev,curve,point['theta'],point['dur_b'],point['t'],point.get('cons_f'))


def unimodal(values,tol=1e-9):
    i=0
    while i+1<len(values) and values[i+1]<=values[i]+tol:i+=1
    while i+1<len(values) and values[i+1]>=values[i]-tol:i+=1
    return i==len(values)-1


def golden(f,a=0.0,b=1.0,tol=GOLDEN_TOL):
    """Golden-section search (the limit of Fibonacci search) of a unimodal f on [a, b]; f is evaluated at t rounded
    to 0.01. Returns (t, evaluations)."""
    g=(math.sqrt(5)-1)/2
    c=b-g*(b-a);d=a+g*(b-a)
    fc=f(round2(c));fd=f(round2(d));n=2
    while b-a>tol:
        if fc<=fd:
            b=d;d=c;fd=fc;c=b-g*(b-a);fc=f(round2(c))
        else:
            a=c;c=d;fc=fd;d=a+g*(b-a);fd=f(round2(d))
        n+=1
    return round2((a+b)/2),n


def search(ev,curve,t_ref,fast=False):
    """The cheapest slider position: golden section when the anchors' costs are unimodal, else the best anchor; the
    golden result also has to beat every anchor. Ties -> nearer the current position, then the faster end. fast: the
    steps -0.1 and -0.2 are candidates too (the search itself stays on t >= 0; turbo is never a candidate)."""
    anchors=[a['t'] for a in curve['anchors']]
    costs=[cost_at(ev,curve,t)[0] for t in anchors]
    candidates=list(zip(anchors,costs))
    method='anchors';evaluations=len(anchors)
    if fast:
        for a in curve['fast_anchors']:
            if a['t']>=FAST_MIN_T:
                candidates.append((a['t'],cost_at(ev,curve,a['t'])[0]));evaluations+=1
    if unimodal(costs):
        t,n=golden(lambda x:cost_at(ev,curve,x)[0])
        candidates.append((t,cost_at(ev,curve,t)[0]));method='golden';evaluations+=n+1
    best=None
    for t,c in candidates:
        if best is None or c<best[1]-1e-9 or (abs(c-best[1])<=1e-9 and (abs(t-t_ref),t)<(abs(best[0]-t_ref),best[0])):best=(t,c)
    return {'t':best[0],'cost':best[1],'method':method,'anchor_costs':costs,'evaluations':evaluations}


# ------------------------------------------------------------------------------------------------------------
# texts (RU / EN): the same bytes in both runtimes
# ------------------------------------------------------------------------------------------------------------
def plural_ru(n,one,few,many):
    if n%10==1 and n%100!=11:return one
    if 2<=n%10<=4 and not 12<=n%100<=14:return few
    return many


def fnum(x,digits,lang):
    text=('%.'+str(digits)+'f')%x
    if text.startswith('-') and float(text)==0:text=text[1:]
    return text.replace('.',',') if lang=='ru' else text


def signed(x,digits,lang):
    text=fnum(x,digits,lang)
    return text if text.startswith('-') or float(text.replace(',','.'))==0 else '+'+text


def where(cur,lang):
    if cur['attached']:return ('положение '+fnum(cur['slider_t'],2,lang)) if lang=='ru' else ('position '+fnum(cur['slider_t'],2,lang))
    if cur['label']=='preset':return 'стандартные настройки' if lang=='ru' else 'standard settings'
    return 'пользовательские настройки' if lang=='ru' else 'custom settings'


def facts(result,lang):
    c=result['counts'];n=result['days_used'];med=result['outage_median_s']
    m='-' if med is None else str(med)
    if lang=='ru':
        return ('на основании %d %s: обрывов основного %d (медиана %s с), эпизодов потерь %d, дребезга %d, отказов резерва %d'
                %(n,plural_ru(n,'дня','дней','дней'),c['natural'],m,c['loss_episodes'],c['flaps'],c['reserve_failures']))
    return ('based on %d day%s: %d outages of the primary (median %s s), %d loss episodes, %d flaps, %d reserve failures'
            %(n,'' if n==1 else 's',c['natural'],m,c['loss_episodes'],c['flaps'],c['reserve_failures']))


def reason(result,cur,lang):
    state=result['state']
    if state=='no-data':
        return ('Мало данных: журнал сети за выбранное окно пуст. Настройки не меняются.' if lang=='ru'
                else 'Not enough data: the network journal of the window is empty. Settings stay as they are.')
    if state=='few-data':
        n=result['events'];d=result['days_used']
        if lang=='ru':
            return ('Мало данных: %d %s за %d %s (нужно не меньше %d). Настройки не меняются.'
                    %(n,plural_ru(n,'событие','события','событий'),d,plural_ru(d,'день','дня','дней'),MIN_EVENTS))
        return ('Not enough data: %d event%s in %d day%s (at least %d needed). Settings stay as they are.'
                %(n,'' if n==1 else 's',d,'' if d==1 else 's',MIN_EVENTS))
    e=result['effect']
    if state=='inactive' and cur['beats'] is not None:
        return ('Турбо включён владельцем: советник его не рекомендует и не меняет.' if lang=='ru'
                else 'Turbo is on by the owner\'s choice: the advisor neither recommends nor changes it.')
    if state=='inactive':
        return ('Детектор «сбои подряд»: ползунок на него не действует, рекомендация не применяется.' if lang=='ru'
                else 'Detector "failures in a row": the slider does not apply to it; nothing is changed.')
    if state=='keep':
        if lang=='ru':
            return ('Оставить %s: %s. Лучшее положение %s сэкономило бы %s %% (нужно не меньше 5 %%).'
                    %(where(cur,'ru'),facts(result,'ru'),fnum(result['best_t'],2,'ru'),fnum(e['saving_pct'],1,'ru')))
        return ('Keep %s: %s. The best position %s would save %s %% (at least 5 %% needed).'
                %(where(cur,'en'),facts(result,'en'),fnum(result['best_t'],2,'en'),fnum(e['saving_pct'],1,'en')))
    if lang=='ru':
        return ('Рекомендовано %s. Предлагается положение %s (сейчас: %s). Ожидаемо за сутки: простой %s с, лишних переключений %s, экономия %s %%.'
                %(facts(result,'ru'),fnum(result['t'],2,'ru'),where(cur,'ru'),signed(-e['downtime_s_day'],1,'ru'),
                  signed(-e['unnecessary_per_day'],2,'ru'),fnum(e['saving_pct'],1,'ru')))
    return ('Recommended %s. Suggested position %s (now: %s). Expected per day: downtime %s s, unnecessary switches %s, saving %s %%.'
            %(facts(result,'en'),fnum(result['t'],2,'en'),where(cur,'en'),signed(-e['downtime_s_day'],1,'en'),
              signed(-e['unnecessary_per_day'],2,'en'),fnum(e['saving_pct'],1,'en')))


# ------------------------------------------------------------------------------------------------------------
# the recommendation
# ------------------------------------------------------------------------------------------------------------
def recommend(curve,days,settings,now,offset):
    today=J.day_index(now,offset)
    cur=current(settings,curve)
    w=window(settings)
    ev=events(days,today,w)
    durations=ev['durations']
    result={'version':VERSION,'day':today,'generated':float(now),'mode':mode(settings),'window_days':w,'key':settings_key(settings),
            'events':ev['n'],'days_used':ev['days'],'counts':ev['counts'],
            'outage_median_s':durations[(len(durations)-1)//2] if durations else None,
            'state':None,'t':None,'best_t':None,'method':None,'evaluations':0,'anchor_costs':None,
            'effect':None,'predicted':None}
    if ev['days']==0:result['state']='no-data'
    elif ev['n']<MIN_EVENTS:result['state']='few-data'
    else:
        best=search(ev,curve,cur['t_ref'],cur['fast'])
        total,down,unnecessary=cost(ev,curve,cur['theta'],cur['dur_b'],cur['t_ref'],cur['or_failures'])
        btotal,bdown,bunnecessary=cost_at(ev,curve,best['t'])
        saving=(total-btotal)/total if total>0 else 0.0
        wd=ev['weight_days']
        result.update(best_t=best['t'],method=best['method'],evaluations=best['evaluations'],
                      anchor_costs=[round2(c) for c in best["anchor_costs"]],
                      effect={'saving_pct':floor(saving*1000+0.5)/10,'downtime_s_day':floor((down-bdown)/wd*10+0.5)/10,
                              'unnecessary_per_day':floor((unnecessary-bunnecessary)/wd*100+0.5)/100,
                              'cost_now_s_day':floor(total/wd*10+0.5)/10,'cost_best_s_day':floor(btotal/wd*10+0.5)/10})
        moved=not (cur['attached'] and abs(best['t']-cur['slider_t'])<0.005)
        if cur['failure_model']=='consecutive' or cur['beats'] is not None:result['state']='inactive'
        elif saving>=MIN_SAVING and moved:result['state']='shift';result['t']=best['t']
        else:result['state']='keep';result['t']=cur['slider_t'] if cur['attached'] else None
        if result['t'] is not None:
            point=interpolate(curve,result['t'])
            result['predicted']=dict(zip(curve['metrics'],[None if x is None else floor(x*100+0.5)/100 for x in point['m']]))
    result['reason_ru']=reason(result,cur,'ru');result['reason_en']=reason(result,cur,'en')
    return result


def calm_codes(calm):
    """Why settings must not change now (empty = calm): an outage in progress or a switch. manual: the owner's click is
    waiting for the supervisor; a change of the settings now would end it in MANUAL-CONFIG-CHANGED (review 04.11.2026)."""
    if not isinstance(calm,dict):return ['ADVISOR-CALM-UNKNOWN']   # no evidence of calm is no calm
    # Review F-82 (06.11.2026): no fresh observation of the route (route_history.observed_route 'unknown', or none at
    # all) is no evidence of calm either; the other fields are read as they are (None = no such state).
    if calm.get('route') in (None,'unknown'):return ['ADVISOR-CALM-UNKNOWN']
    codes=[]
    if calm.get('open'):codes.append('ADVISOR-BUSY-OUTAGE')
    if (calm.get('route') in ('switching','down') or calm.get('native') in TRANSITION or calm.get('phase') in TRANSITION
            or calm.get('manual')):
        codes.append('ADVISOR-BUSY-SWITCH')
    return codes


def auto_step(curve,result,settings,changes,calm,now):
    """Auto mode: the next slider position (one AUTO_STEP toward the recommendation, at most once a day, never during
    an outage or a switch, always within the safety rules) -> {'apply': bool, 't', 'code'}."""
    cur=current(settings,curve)
    def no(code):return {'apply':False,'t':None,'code':code}
    if mode(settings)!='auto':return no('ADVISOR-NOT-AUTO')
    if cur['failure_model']=='consecutive':return no('ADVISOR-MODEL-CONSECUTIVE')
    if cur['beats'] is not None:return no('ADVISOR-TURBO')
    if not isinstance(result,dict) or result.get('state')!='shift' or number(result.get('t')) is None:return no('ADVISOR-NO-SHIFT')
    busy=calm_codes(calm)
    if busy:return no(busy[0])
    last=[c for c in (changes or []) if isinstance(c,dict) and c.get('source')=='auto' and number(c.get('time')) is not None]
    if last and now-max(c['time'] for c in last)<AUTO_SPACING:return no('ADVISOR-ONCE-A-DAY')
    start=cur['t_ref'];delta=min(AUTO_STEP,max(-AUTO_STEP,result['t']-start))
    t=round2(start+delta)
    if t<0 and not (cur['fast'] and t>=FAST_MIN_T):return no('ADVISOR-FAST-OFF')
    if cur['attached'] and abs(t-cur['slider_t'])<0.005:return no('ADVISOR-NO-SHIFT')
    if safety(interpolate(curve,t)):return no('ADVISOR-UNSAFE')
    return {'apply':True,'t':t,'code':None}


def job_due(result,key,now,offset,last_spawn):
    """The monitor starts the job: once a night after RUN_AT, without a result, or after changed advisor settings
    (at most every RUN_SPACING s)."""
    if last_spawn is not None and now-last_spawn<RUN_SPACING:return False
    if not isinstance(result,dict) or type(result.get('day')) is not int:return True
    if result.get('key')!=key:return True
    today=J.day_index(now,offset)
    return now+offset-today*J.DAY>=RUN_AT and result['day']!=today


# ------------------------------------------------------------------------------------------------------------
# public views (status field network_advisor and rpc advisor)
# ------------------------------------------------------------------------------------------------------------
def summary(days,cur_day,today,window_days):
    """Journal summary of the window and today: per tunnel loss, outages (histogram, median, P90 when n >= 100 -
    the survival-analysis rule), RTT by hour; failovers / returns / unnecessary failovers of the pair."""
    tunnels={};pair={'switches':0,'returns':0,'unnecessary':0};used=0
    for day in sorted(list(days)+([cur_day] if cur_day else []),key=lambda d:d['d']):
        if not 0<=today-day['d']<=window_days:continue
        used+=1
        pair['switches']+=day['sw'];pair['returns']+=day['rt'];pair['unnecessary']+=day['us']
        for identifier,rec in day['ch'].items():
            t=tunnels.setdefault(identifier,{'role':'primary','n':0,'f':0,'hist':[0]*len(J.EDGES),'d':[],'rs':[0]*J.HOURS,'rn':[0]*J.HOURS,'more':0})
            t['role']='reserve' if rec.get('r')==1 else 'primary'
            t['n']+=rec['n'];t['f']+=rec['f'];t['more']+=rec.get('ox',0)
            for i,v in enumerate(rec['oh']):t['hist'][i]+=v
            for i in range(J.HOURS):t['rs'][i]+=rec['rs'][i];t['rn'][i]+=rec['rn'][i]
            t['d'].extend(d for _,d,_ in triples(rec))
    out={}
    for identifier in sorted(tunnels):
        t=tunnels[identifier];d=sorted(t['d']);n=len(d)
        out[identifier]={'role':t['role'],'observations':t['n'],
                         'loss_pct':floor(1000*t['f']/t['n']+0.5)/10 if t['n'] else None,
                         'outages':sum(t['hist']),'outage_hist':t['hist'],
                         'outage_median_s':d[(n-1)//2] if n else None,
                         'outage_p90_s':d[int(math.ceil(0.9*n))-1] if n>=100 else None,
                         'survival_ready':n>=100,'durations_kept':n,
                         'rtt_by_hour_ms':[floor(t['rs'][i]/t['rn'][i]+0.5) if t['rn'][i] else None for i in range(J.HOURS)]}
    return {'days':used,'window_days':window_days,'edges_s':list(J.EDGES),'tunnels':out,'pair':pair}


def public_status(settings,curve,result,journal_summary,changes):
    cur=current(settings,curve)
    rec=None
    if isinstance(result,dict):
        rec={k:result.get(k) for k in ('state','t','best_t','method','effect','predicted','reason_ru','reason_en',
                                       'events','days_used','counts','generated','window_days','applied')}
    last=changes[-1] if changes else None
    return {'mode':mode(settings),'window_days':window(settings),'curve_version':curve.get('version'),
            'current':{k:cur[k] for k in ('t_ref','slider_t','attached','label','nearest_t','failure_model','theta','dur_b','pg','primary_stable','rescue_stable','or_failures','beats','fast','turbo')},
            'recommendation':rec,'journal':journal_summary,'last_change':last}


def public_curve(curve):
    return {'version':curve.get('version'),'params':curve['params'],'metrics':curve['metrics'],
            'anchors':[{'t':a['t'],'p':a['p'],'m':a['m']} for a in curve['anchors']],'alpha8':curve.get('alpha8'),
            'fast_params':curve.get('fast_params'),'fast_anchors':[{'t':a['t'],'p':a['p'],'x':a['x'],'m':a['m']} for a in curve['fast_anchors']]}


# ------------------------------------------------------------------------------------------------------------
# the nightly job
# ------------------------------------------------------------------------------------------------------------
def read_text(path):
    try:return Path(path).read_text(encoding='utf-8')
    except OSError:return None


def read_json(path,default=None):
    text=read_text(path)
    if text is None:return default
    try:return json.loads(text)
    except ValueError:return default


def load_days(runtime,persist):
    journal=J.load(read_text(runtime+'/'+J.DAYS_NAME),None,read_text(persist+'/'+J.FLASH_NAME))
    return journal['days']


def changes(persist):
    value=read_json(persist+'/'+CHANGES_NAME,{})
    rows=value.get('changes') if isinstance(value,dict) else None
    return [r for r in rows if isinstance(r,dict)] if isinstance(rows,list) else []


def run(runtime,persist,apply=None):
    """advisor.py run: the request the monitor left (settings, clock, calm state) -> runtime/advisor.json; in auto
    mode one step through apply(t, reason_ru, reason_en) (advisor_control.apply_auto)."""
    request=read_json(runtime+'/'+REQUEST_NAME,{})
    settings=request.get('settings') if isinstance(request.get('settings'),dict) else {}
    now=number(request.get('now'));offset=request.get('offset')
    if now is None or type(offset) is not int:raise SystemExit('ADVISOR-REQUEST-INVALID')
    curve=load_curve()
    result=recommend(curve,load_days(runtime,persist),settings,now,offset)
    step=auto_step(curve,result,settings,changes(persist),request.get('calm'),now)
    result['auto']=step
    if step['apply'] and apply is not None:
        result['applied']=apply(step['t'],result)
    from agent import atomic_json
    atomic_json(Path(runtime)/RESULT_NAME,result)
    return result


# ------------------------------------------------------------------------------------------------------------
# the monitor's part (single writer of the journal, starter of the nightly job, the status field)
# ------------------------------------------------------------------------------------------------------------
REQUEST_KEYS=('failure_model','hmm_theta','hmm_dur_b','return_pg','slider_t','advisor_mode','advisor_window',
              'recovery_primary_stable','recovery_rescue_stable','hmm_or_failures','turbo_beats','slider_fast','slider_turbo')


class MonitorPart:
    """io: read(path)->text|None, write_ram(path,text), write_flash(path,text), spawn()->bool (starts
    `advisor run` with low priority). One call per monitor pass; returns the status field network_advisor."""
    def __init__(self,io,runtime,persist,now,curve=None):
        self.io=io;self.runtime=runtime;self.persist=persist
        self.curve=curve or load_curve()
        self.writer=J.Writer(io,runtime,persist)
        self.last_spawn=now          # the first run waits RUN_SPACING after the monitor start
        self.summary_key=None;self.summary=None;self.changes_key=None;self.changes=[]

    def read_result(self):
        try:value=json.loads(self.io.read(self.runtime+'/'+RESULT_NAME) or 'null')
        except ValueError:value=None
        return value if isinstance(value,dict) else None

    def pass_(self,samples,pair,route,native_state,settings,now,offset,clock):
        journal=self.writer.journal
        self.writer.pass_(samples,pair,route,now,offset,clock)
        result=self.read_result()
        key=settings_key(settings)
        if job_due(result,key,now,offset,self.last_spawn):
            request={'settings':{k:settings.get(k) for k in REQUEST_KEYS if isinstance(settings,dict) and settings.get(k) is not None},
                     'now':float(now),'offset':offset,'key':key,
                     'calm':{'open':J.open_outages(journal),'route':route,'native':native_state}}
            self.io.write_ram(self.runtime+'/'+REQUEST_NAME,J.encode(request))
            if self.io.spawn():self.last_spawn=now
        w=window(settings);today=J.day_index(now,offset)
        skey=(len(journal['days']),journal['cur']['d'] if journal['cur'] else None,w,floor(now/60))
        if skey!=self.summary_key:
            self.summary=summary(journal['days'],journal['cur'],today,w);self.summary_key=skey
        ckey=floor(now/60)
        if ckey!=self.changes_key:
            value=None
            try:value=json.loads(self.io.read(self.persist+'/'+CHANGES_NAME) or 'null')
            except ValueError:pass
            rows=value.get('changes') if isinstance(value,dict) else None
            self.changes=[r for r in rows if isinstance(r,dict)] if isinstance(rows,list) else [];self.changes_key=ckey
        return public_status(settings,self.curve,result,self.summary,self.changes)


def main(argv):
    if len(argv)>=2 and argv[1]=='run':
        import os
        try:os.nice(19)
        except (AttributeError,OSError):pass
        from agent import RUNTIME,PERSIST
        from advisor_control import apply_auto
        run(str(RUNTIME),str(PERSIST),apply_auto)
        return 0
    raise SystemExit('usage: advisor.py run')


if __name__=='__main__':
    import sys
    sys.exit(main(sys.argv))
