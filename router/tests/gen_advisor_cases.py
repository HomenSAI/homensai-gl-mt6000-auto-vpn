"""Shared cases of the network journal and the advisor (netjournal.py / advisor.py and their Lua twins
lua/netjournal.lua / lua/advisor.lua). Generated from the Python modules; tests/test_network_advisor.py checks the
file is current and tests/lua/test_network_advisor.lua checks the Lua twins give the same records, numbers within
`tolerance`, the same decisions and the same texts.

    python3 router/tests/gen_advisor_cases.py --write
"""
import json
import math
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
sys.path.insert(0,str(HERE))
import advisor as A  # noqa: E402
import advisor_sim as S  # noqa: E402
import netjournal as J  # noqa: E402

TARGET=HERE/'advisor_cases.json'
NOW_AFTER=lambda days:S.BASE+days*86400+3.5*3600  # noqa: E731  the nightly run after `days` simulated days


def fingerprint(day):
    """A compact exact view of one day record (all integers)."""
    out={'d':day['d'],'sw':day['sw'],'rt':day['rt'],'us':day['us'],'ch':{}}
    for identifier,rec in day['ch'].items():
        out['ch'][identifier]={'r':rec['r'],'n':rec['n'],'f':rec['f'],'lp_sum':sum(rec['lp']),
                               'lp_w':sum(i*v for i,v in enumerate(rec['lp'])),'rs_sum':sum(rec['rs']),'rn_sum':sum(rec['rn']),
                               'rs_w':sum(i*v for i,v in enumerate(rec['rs'])),'oh':rec['oh'],'o':rec['o'],'ox':rec['ox']}
    return out


def sample(identifier,t,fail,dense=False,rtt=40,code=None):
    s=dict(S.health(fail),id=identifier,time=t,rtt_ms=None if fail else rtt,dense=dense)
    if code is not None:s['code']=code
    return s


def journal_sequences():
    """Small explicit monitor-pass sequences: [name, offset, passes [[now, samples, route]]]."""
    P,R=S.PRIMARY,S.RESERVE
    base=S.BASE
    seqs=[]
    # an outage across midnight (offset 7200: the local day starts at 22:00 UTC), dense checks, a failover
    passes=[];t=base+86400-7200-60
    for k in range(20):
        now=t+10*k;fail=50<=10*k<110
        passes.append([now+8,[sample(P,now,fail),sample(R,now+0.5,False,rtt=55)]+([sample(P,now+4,fail,True)] if fail else []),
                       'target' if 80<=10*k<200 else 'source'])
    seqs.append(['midnight-outage-failover',7200,passes])
    # a failover whose outage ends 12 s later (did not pay for itself); a flap: a failover 300 s after a return (its
    # outage is real and pays); a false failover without any failed check
    passes=[];t=base+3600
    plan=([('source',False)]*3+[('source',True)]*3+[('target',True)]*2+[('target',False)]*4+[('source',False)]*26+[('source',True)]*4
          +[('target',True)]*5+[('target',False)]*3+[('source',False)]*70+[('target',False)])
    for k,(route,fail) in enumerate(plan):
        now=t+10*k
        passes.append([now+8,[sample(P,now,fail),sample(R,now+0.5,False)],route])
    seqs.append(['flap-false-short',0,passes])
    # a stale previous success (monitor gap), other codes, an unknown tunnel, 5 tunnels (cap 4), the clock back
    passes=[];t=base+7200
    passes.append([t+8,[sample(P,t,False),sample('wireguard:peer_9',t,True)],'source'])
    passes.append([t+408,[sample(P,t+400,True),sample(R,t+400.5,False,code='CHECK-001')],'unknown'])
    passes.append([t+418,[sample(P,t+410,False,rtt=61.6)],'source'])
    passes.append([t+300,[sample(P,t+292,True)],'source'])
    passes.append([t+428,[sample(P,t+420,False,rtt=0.4)],'switching'])
    seqs.append(['stale-codes-clock',0,passes])
    # a reserve outage while it carries the traffic, then the pair changes (the reserve's open outage is dropped)
    passes=[];t=base+20000
    for k in range(12):
        now=t+10*k
        passes.append([now+8,[sample(P,now,False),sample(R,now+0.5,2<=k<9)],'target'])
    passes.append([t+130,[sample(P,t+122,False),sample(R,t+122.5,True)],'target',{'source':P,'target':'openvpn:1_3'}])
    seqs.append(['reserve-outage-pair-change',0,passes])
    return [[name,offset,[p if len(p)==4 else p+[S.PAIR] for p in passes]] for name,offset,passes in seqs]


def run_sequence(offset,passes):
    journal=J.new()
    for now,samples,route,pair in passes:J.observe(journal,samples,pair,route,now,offset)
    return journal


def built(name,days,offset=0):
    return S.build(S.scenario_days(name,days),offset)


def ev_view(ev):
    return {'n':ev['n'],'days':ev['days'],'weight_days':ev['weight_days'],'groups':ev['groups'],'counts':ev['counts'],
            'outages':[list(o) for o in ev['outages']],'durations':ev['durations']}


RESULT_KEYS=('version','day','mode','window_days','key','events','days_used','counts','outage_median_s','state','t','best_t',
             'method','evaluations','anchor_costs','effect','predicted','reason_ru','reason_en')
SETTINGS=[
    {'failure_model':'hmm'},
    {'failure_model':'hmm','slider_t':0.5,'hmm_theta':0.6,'hmm_dur_b':5.0,'return_pg':0.95,'recovery_primary_stable':120,'recovery_rescue_stable':10},
    {'failure_model':'hmm-fast','advisor_mode':'auto','advisor_window':30},
    {'failure_model':'consecutive','advisor_window':1},
    {'failure_model':'hmm','hmm_theta':0.7,'recovery_primary_stable':200,'advisor_mode':'manual'},
    {'failure_model':'hmm','slider_t':0.4,'advisor_mode':'auto'},   # slider_t without its values: detached
]


def cases():
    curve=A.load_curve()
    out={'tolerance':1e-9,'pair':S.PAIR,'base':S.BASE,'scenarios':S.SCENARIOS}
    out['interpolate']=[{'t':t,'expect':A.interpolate(curve,t)} for t in (0,0.05,0.1,0.13,0.25,0.333,0.5,0.62,0.75,0.8,0.99,1,-0.5,1.7)]
    pairs=[(0.6,3.0),(0.6,3.5),(0.6,5.0),(0.6,8.0),(0.8,4.0),(0.7,3.0),(0.9,3.0),(0.95,8.0),(0.99,15.0),(0.5,1.0)]
    out['behaviour']=[{'theta':a,'dur_b':b,'knowns':A.knowns(a,b),'ride':A.behaviour(a,b)[0],'leave':A.behaviour(a,b)[1]} for a,b in pairs]
    out['outcome']=[{'d':d,'theta':a,'dur_b':b,'expect':list(A.outcome(d,A.knowns(a,b)))} for d in (1,5,12,17,19.5,20,21,22,23,24,25,26,30,45,120,301,5000) for a,b in pairs[:5]]
    safety=[dict(zip(curve['params'],x['p'])) for x in curve['anchors']]+[
        {'theta':0.8,'dur_b':4,'pg':0.9,'primary_stable':120,'rescue_stable':10},
        {'theta':0.8,'dur_b':4,'pg':0.7,'primary_stable':120,'rescue_stable':10},
        {'theta':0.8,'dur_b':4,'pg':0.9,'primary_stable':40,'rescue_stable':50},
        {'theta':0.99,'dur_b':15,'pg':0.99,'primary_stable':120,'rescue_stable':10},
        {'theta':0.4,'dur_b':4,'pg':0.9,'primary_stable':120,'rescue_stable':10},
        {'theta':0.8,'dur_b':4,'pg':0.9,'primary_stable':700,'rescue_stable':10},
        {'theta':0.8,'dur_b':None,'pg':0.9,'primary_stable':120,'rescue_stable':10}]
    out['safety']=[{'params':p,'codes':A.safety(p)} for p in safety]
    keys=('theta','dur_b','pg','primary_stable','rescue_stable','failure_model','slider_t','attached','label','nearest_t','t_ref')
    current_settings=SETTINGS+[{'failure_model':'hmm','hmm_theta':0.2,'hmm_dur_b':'4','return_pg':True,'recovery_primary_stable':5000},
                               {'failure_model':'hmm','slider_t':0.75,'hmm_theta':0.6,'hmm_dur_b':8.0,'return_pg':0.95,'recovery_primary_stable':240,'recovery_rescue_stable':15},
                               {'advisor_mode':'bogus','advisor_window':5,'slider_t':1.5}]
    out['current']=[{'settings':s,'expect':{k:A.current(s,curve)[k] for k in keys},'key':A.settings_key(s),'mode':A.mode(s),
                     'window':A.window(s)} for s in current_settings]
    out['unimodal']=[[v,A.unimodal(v)] for v in ([1,2,3],[3,2,1],[3,1,2],[1,2,1],[2,2,2],[3,1,1,2,2,5],[1,3,2,4],[5,4,4,6,5])]
    goldens=[]
    for m in (0.0,0.13,0.37,0.5,0.81,1.0):
        for kind in ('quad','steps'):
            f=(lambda t,m=m:(t-m)**2) if kind=='quad' else (lambda t,m=m:math.floor(abs(t-m)*20)/20)
            goldens.append({'m':m,'kind':kind,'expect':list(A.golden(f))})
    out['golden']=goldens
    out['plural']=[[n,A.plural_ru(n,'день','дня','дней')] for n in (0,1,2,4,5,11,12,14,21,22,25,101,111,112)]
    seqs=journal_sequences()
    out['journal']=[]
    for name,offset,passes in seqs:
        journal=run_sequence(offset,passes)
        out['journal'].append({'name':name,'offset':offset,'passes':passes,'days':[fingerprint(d) for d in journal['days']],
                               'cur':fingerprint(journal['cur']),'open':J.open_outages(journal),'route':journal['st']['route'],
                               'flash_due':J.flash_due(journal,passes[-1][0],offset),'text':J.days_text(journal)})
    out['builds']={}
    journals={}
    for name in S.SCENARIOS:
        journal=built(name,7);journals[name]=journal
        out['builds'][name]={'days':7,'offset':0,'fingerprints':[fingerprint(d) for d in journal['days']],
                             'sizes':[len(J.encode(d)) for d in journal['days']]}
    shifted=built('blips',2,offset=3600)
    out['builds']['blips@3600']={'name':'blips','days':2,'offset':3600,'fingerprints':[fingerprint(d) for d in shifted['days']],
                                 'sizes':[len(J.encode(d)) for d in shifted['days']]}
    now=NOW_AFTER(7);today=J.day_index(now,0)
    out['events']=[{'scenario':name,'window':w,'today':today,'expect':ev_view(A.events(journals[name]['days'],today,w))}
                   for name in S.SCENARIOS for w in (1,7,30)]
    out['recommend']=[]
    for name in S.SCENARIOS:
        for s in SETTINGS:
            r=A.recommend(curve,journals[name]['days'],s,now,0)
            out['recommend'].append({'scenario':name,'settings':s,'now':now,'offset':0,'expect':{k:r[k] for k in RESULT_KEYS}})
    # few data / no data
    for days,label in ((1,'one-day'),(0,'empty')):
        j=journals['quiet']['days'][-days:] if days else []
        r=A.recommend(curve,j,SETTINGS[0],now,0)
        out['recommend'].append({'scenario':'quiet','tail':days,'settings':SETTINGS[0],'now':now,'offset':0,'expect':{k:r[k] for k in RESULT_KEYS}})
    out['summary']=[{'scenario':name,'window':w,'today':today,'expect':A.summary(journals[name]['days'],None,today,w)}
                    for name in ('long','flappy') for w in (1,7)]
    shift={'state':'shift','t':0.2}
    auto=[]
    def add(name,result,settings,changes,calm,t_now):
        auto.append({'name':name,'result':result,'settings':settings,'changes':changes,'calm':calm,'now':t_now,
                     'expect':A.auto_step(curve,result,settings,changes,calm,t_now)})
    calm={'open':[],'route':'source','native':'OBSERVING'}
    add('advice-mode',shift,{'failure_model':'hmm'},[],calm,now)
    add('auto-from-preset',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],calm,now)
    add('auto-attached',{'state':'shift','t':0.9},dict(SETTINGS[1],advisor_mode='auto'),[],calm,now)
    add('auto-small-step',{'state':'shift','t':0.45},dict(SETTINGS[1],advisor_mode='auto'),[],calm,now)
    add('auto-busy-outage',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],{'open':[S.PRIMARY],'route':'source','native':'OBSERVING'},now)
    add('auto-busy-switch',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],{'open':[],'route':'switching','native':'OBSERVING'},now)
    add('auto-busy-native',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],{'open':[],'route':'source','native':'APPLYING'},now)
    add('auto-busy-phase',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],{'open':[],'route':'source','native':'OBSERVING','phase':'RESTORING'},now)
    add('auto-once-a-day',shift,{'failure_model':'hmm','advisor_mode':'auto'},[{'time':now-3600,'source':'auto'}],calm,now)
    add('auto-owner-change-today',shift,{'failure_model':'hmm','advisor_mode':'auto'},[{'time':now-3600,'source':'owner'}],calm,now)
    add('auto-yesterday',shift,{'failure_model':'hmm','advisor_mode':'auto'},[{'time':now-21*3600,'source':'auto'}],calm,now)
    add('auto-consecutive',shift,{'failure_model':'consecutive','advisor_mode':'auto'},[],calm,now)
    add('auto-keep',{'state':'keep','t':None},{'failure_model':'hmm','advisor_mode':'auto'},[],calm,now)
    add('manual',shift,{'failure_model':'hmm','advisor_mode':'manual'},[],calm,now)
    add('auto-no-calm-record',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],None,now)
    add('auto-owner-click-queued',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],dict(calm,manual='QUEUED'),now)
    add('auto-owner-click-claimed',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],dict(calm,manual='CLAIMED'),now)
    add('auto-no-owner-click',shift,{'failure_model':'hmm','advisor_mode':'auto'},[],dict(calm,manual=None),now)
    out['auto_step']=auto
    key=A.settings_key(SETTINGS[0])
    due=[]
    for result,k,t_now,offset,last in (
            (None,key,now,0,None),({'day':today,'key':key},key,now,0,None),({'day':today-1,'key':key},key,now,0,None),
            ({'day':today-1,'key':key},key,S.BASE+7*86400+3*3600,0,None),({'day':today,'key':'other'},key,now,0,None),
            ({'day':today,'key':'other'},key,now,0,now-300),({'day':today-1,'key':key},key,now,0,now-700),
            ({'day':today-1,'key':key},key,S.BASE+7*86400+1*3600,7200,None),({'day':'x','key':key},key,now,0,None)):
        due.append({'result':result,'key':k,'now':t_now,'offset':offset,'last':last,'expect':A.job_due(result,k,t_now,offset,last)})
    out['job_due']=due
    return out


def text():
    return json.dumps(cases(),ensure_ascii=False,sort_keys=True,indent=None,separators=(',',':'))+'\n'


if __name__=='__main__':
    data=text()
    if '--write' in sys.argv:
        with open(TARGET,'w',encoding='utf-8',newline='\n') as f:f.write(data)
        print(TARGET,len(data),'bytes')
    else:print(len(data),'bytes (dry run; --write to save)')
