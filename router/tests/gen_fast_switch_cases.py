"""Shared cases of the fast end of Auto (FAST-SWITCH-2026-11-04.ru.md): channel_model.leave_rule and friends, probe_policy
dense_interval / wake_row, the stepped segment and the fast / turbo gates of the advisor. Generated from the Python modules;
tests/test_fast_switch.py checks the file is current, tests/lua/test_fast_switch.lua that the Lua twins give the same.

    python3 router/tests/gen_fast_switch_cases.py --write
"""
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import advisor as A  # noqa: E402
import channel_model as C  # noqa: E402
import probe_policy as P  # noqa: E402

TARGET=HERE/'fast_switch_cases.json'
PROFILE={'id':'wireguard:peer_1','protocol':'wireguard','interface':'wgclient1','vendor_tunnel_id':'wireguard:wgclient1','vendor_generation':'01'*16,'vendor_changed_at':100}
RESERVE='openvpn:1_1'
GOOD={'code':None,'dns_ok':True,'https':3}
BAD={'code':'VPN-003','dns_ok':False,'https':0}
DNS={'code':'DNS-001','dns_ok':False,'https':3}
OTHER={'code':'CHECK-001','dns_ok':None,'https':None}
HMM={'failure_model':'hmm'}
T2=dict(hmm_or_failures=2)
T3=dict(hmm_or_failures=3)
LATE=dict(hmm_theta=0.99)    # the model decides late, so the rule of the case is the one that speaks
TURBO=dict(hmm_or_failures=2,slider_turbo=True,turbo_beats=5)
NOW=1000.0


def rows(*items):
    return [dict(health,t=t) for t,health in items]


def beat(**over):
    return dict({'reason':'heartbeat','time':NOW-1,'id':PROFILE['id'],'target':RESERVE,'target_ok':True,'lost':5},**over)


def sample(r):
    return {'id':PROFILE['id'],'time':r['t'],'code':r['code'],'dns_ok':r['dns_ok'],'https_success':r['https'],'interface':PROFILE['interface'],
            'vendor_tunnel_id':PROFILE['vendor_tunnel_id'],'vendor_generation':r.get('gen',PROFILE['vendor_generation'])}


def leave_cases():
    two=rows((960,GOOD),(970,GOOD),(985,BAD),(995,BAD))
    three=rows((960,GOOD),(975,BAD),(985,BAD),(995,BAD))
    one=rows((960,GOOD),(970,GOOD),(980,GOOD),(995,BAD))
    mixed=rows((960,GOOD),(975,BAD),(985,GOOD),(995,BAD))
    gapped=rows((800,BAD),(995,BAD))
    fresh=rows((960,GOOD),(975,GOOD),(990,GOOD))
    stale=rows((900,GOOD),(910,GOOD))
    dns=rows((960,GOOD),(975,GOOD),(985,DNS),(995,DNS))
    unobserved=rows((960,GOOD),(985,BAD),(995,OTHER))
    foreign=rows((960,GOOD),(985,dict(BAD,gen='02'*16)),(995,BAD))
    cases=[('two failures, no option: the model alone',two,{},None),
           ('two failures with N=2: the streak',two,T2,None),
           ('two failures with N=3: not yet',two,T3,None),
           ('three failures with N=3: the streak',three,dict(T3,**LATE),None),
           ('one failure with N=2: not yet',one,T2,None),
           ('good between two failures: no streak',mixed,T2,None),
           ('two DNS failures with N=2: the streak',dns,T2,None),
           ('a newest sample that is no observation: no streak',unobserved,T2,None),
           ('the older failure of another generation: no streak',foreign,T2,None),
           ('two failures 195 s apart: no streak',gapped,dict(T2,**LATE),None),
           ('N=2 is ignored in the consecutive model',two,dict(T2,failure_model='consecutive'),None),
           ('consecutive: its own streak of 3',three,{'failure_model':'consecutive'},None),
           ('heartbeat: k reached, fresh sample',fresh,TURBO,beat()),
           ('heartbeat without the opt-in',fresh,dict(TURBO,slider_turbo=False),beat()),
           ('heartbeat: no turbo_beats',fresh,dict(slider_turbo=True),beat()),
           ('heartbeat below k',fresh,TURBO,beat(lost=4)),
           ('heartbeat row too old',fresh,TURBO,beat(time=NOW-2.6)),
           ('heartbeat row from the future',fresh,TURBO,beat(time=NOW+1)),
           ('heartbeat of another channel',fresh,TURBO,beat(id='wireguard:peer_2')),
           ('heartbeat for another reserve',fresh,TURBO,beat(target='openvpn:2_2')),
           ('heartbeat: the reserve is silent too (a WAN outage)',fresh,TURBO,beat(target_ok=False)),
           ('heartbeat: a wake row, no verdict',fresh,TURBO,beat(reason='sample')),
           ('heartbeat: no fresh sample of the channel, no evidence for the recheck',stale,TURBO,beat()),
           ('heartbeat: no sample at all',[],TURBO,beat()),
           ('heartbeat in the consecutive model: ignored',fresh,dict(TURBO,failure_model='consecutive'),beat()),
           ('no row at all',fresh,TURBO,None)]
    out=[]
    for name,points,options,row in cases:
        settings=dict(HMM,**options)
        expect=C.leave_rule([sample(r) for r in points],PROFILE['id'],3,NOW,30,settings,PROFILE,RESERVE,row)
        out.append({'name':name,'rows':points,'settings':settings,'beat':row,'expect':expect})
    return out


def option_cases():
    out=[]
    for settings in ({},{'hmm_or_failures':2},{'hmm_or_failures':'3'},{'hmm_or_failures':1},{'hmm_or_failures':11},{'hmm_or_failures':0},
                     {'hmm_or_failures':'x'},{'hmm_or_failures':2.5},{'hmm_or_failures':2,'failure_model':'consecutive'},
                     {'slider_turbo':True},{'slider_turbo':'1','turbo_beats':'5'},{'slider_turbo':False,'turbo_beats':5},{'slider_turbo':'0','turbo_beats':5},
                     {'turbo_beats':5},{'slider_turbo':True,'turbo_beats':2},{'slider_turbo':True,'turbo_beats':9},{'slider_turbo':True,'turbo_beats':3},
                     {'slider_turbo':True,'turbo_beats':8},{'slider_turbo':True,'turbo_beats':5,'failure_model':'consecutive'}):
        out.append({'settings':settings,'or_failures':C.or_failures(settings),'turbo_on':C.turbo_on(settings),'heartbeat_k':C.heartbeat_k(settings),
                    'dense':P.dense_interval(settings)})
    return out


def wake_cases():
    pair={'source':'a','target':'b'}
    good={'id':'a','code':None,'dns_ok':True,'https_success':3}
    bad={'id':'a','code':'VPN-003','dns_ok':False,'https_success':0}
    other={'id':'c','code':'VPN-003','dns_ok':False,'https_success':0}
    reserve={'id':'b','code':'DNS-001','dns_ok':False,'https_success':3}
    cases=[({},[good],pair),({},[bad],pair),({},[other],pair),({},[reserve],pair),({'auto_event_wake':'0'},[bad],pair),({'auto_event_wake':False},[bad],pair),
           ({'auto_event_wake':True},[bad],pair),({},[bad],None),({},[],pair)]
    return [{'settings':s,'rows':r,'pair':p,'expect':P.wake_row(s,r,p,NOW)} for s,r,p in cases]


def point(curve,t):
    p=A.interpolate(curve,t)
    return {k:p.get(k) for k in ('t','theta','dur_b','pg','primary_stable','rescue_stable','cons_f','beat_k','dense_interval')}


def event_record():
    """Hand-made window events: heavy hour-long loss and a few outages (the fast steps pay), and a calm network."""
    def ev(outages,groups):
        return {'outages':outages,'groups':dict({g:0.0 for g in A.TABLE_GROUPS},**groups),'n':len(outages)+int(sum(groups.values())),'days':7,'weight_days':7.0,
                'counts':{'outages':len(outages),'short':0,'medium':0,'long':0,'loss_episodes':0,'flaps':0,'noisy_hours':0,'reserve_failures':0,'natural':len(outages)},'durations':[]}
    return {'lossy':ev([[40,1.0],[90,1.0]],{'loss_heavy':4.0,'loss_light':4.0}),'calm':ev([[6,1.0],[7,1.0],[9,1.0],[12,1.0],[30,1.0]],{})}


def advisor_cases():
    curve=A.load_curve()
    out={'steps':[point(curve,t) for t in (1,0.5,0,-0.01,-0.05,-0.09,-0.1,-0.15,-0.2,-0.25,-0.3,-0.35,-0.4,-0.5,-0.6,-0.7,-0.75)]}
    out['floors']=[{'settings':s,'floor':A.t_floor(s),'fast':A.fast_enabled(s)} for s in ({},{'slider_fast':True},{'slider_fast':'1'},{'slider_fast':'0'},{'slider_turbo':True},{'slider_fast':True,'slider_turbo':'1'})]
    out['safety']=[{'t':t,'codes':A.safety(A.interpolate(curve,t))} for t in (0,-0.1,-0.2,-0.3,-0.5,-0.7)]
    out['behaviour']=[{'theta':a,'dur_b':b,'cons':c,'value':list(A.behaviour(a,b,c))} for a,b,c in ((0.6,3,None),(0.6,3,3),(0.6,3,2),(0.8,4,2),(0.5,2.5,2))]
    base={'failure_model':'hmm','hmm_theta':0.6,'hmm_dur_b':3,'return_pg':0.8,'recovery_primary_stable':120,'recovery_rescue_stable':5}
    out['current']=[]
    for name,options in (('t=0',dict(slider_t=0)),('t=-0.1',dict(slider_t=-0.1,hmm_or_failures=3,slider_fast=True)),('t=-0.2',dict(slider_t=-0.2,hmm_or_failures=2,slider_fast=True)),
                         ('position without its detector',dict(slider_t=-0.2,slider_fast=True)),('detector without a position',dict(hmm_or_failures=2)),
                         ('turbo',dict(slider_t=-0.5,hmm_theta=0.5,hmm_dur_b=2,hmm_or_failures=2,turbo_beats=5,slider_fast=True,slider_turbo=True)),
                         ('turbo beats without the opt-in',dict(slider_t=-0.5,hmm_theta=0.5,hmm_dur_b=2,hmm_or_failures=2,turbo_beats=5)),
                         ('alpha8',{})):
        settings=dict(base,**options) if options else {}
        cur=A.current(settings,curve)
        out['current'].append({'name':name,'settings':settings,'key':A.settings_key(settings),
                               'current':{k:cur[k] for k in ('slider_t','attached','label','t_ref','or_failures','beats','fast','turbo')}})
    events=event_record()
    out['events']=events
    out['search']=[]
    for name,fast in (('lossy',False),('lossy',True),('calm',False),('calm',True)):
        best=A.search(events[name],curve,0,fast)
        out['search'].append({'events':name,'fast':fast,'t':best['t'],'cost':best['cost'],'method':best['method'],'evaluations':best['evaluations']})
    out['costs']=[{'events':name,'t':t,'value':list(A.cost_at(events[name],curve,t))} for name in events for t in (0,-0.1,-0.2,-0.5)]
    calm={'open':[],'route':'source','native':'OBSERVING','phase':None}
    out['auto']=[]
    fast_on=dict(base,advisor_mode='auto',slider_t=0,slider_fast=True)
    for name,settings,t in (('fast off: the step stops at 0',dict(base,advisor_mode='auto',slider_t=0.05),-0.2),
                            ('fast on: one step',fast_on,-0.2),
                            ('fast on: -0.1 to -0.2',dict(base,advisor_mode='auto',slider_t=-0.1,hmm_or_failures=3,slider_fast=True),-0.2),
                            ('turbo is never a step',dict(base,advisor_mode='auto',slider_t=-0.2,hmm_or_failures=2,slider_fast=True),-0.5),
                            ('back from a fast step',dict(base,advisor_mode='auto',slider_t=-0.2,hmm_or_failures=2,slider_fast=True),0.5),
                            ('auto leaves turbo alone',dict(base,advisor_mode='auto',slider_t=-0.5,hmm_theta=0.5,hmm_dur_b=2,hmm_or_failures=2,turbo_beats=5,slider_fast=True,slider_turbo=True),0)):
        step=A.auto_step(curve,{'state':'shift','t':t},settings,[],calm,NOW)
        out['auto'].append({'name':name,'settings':settings,'t':t,'apply':step['apply'],'to':step['t'],'code':step['code']})
    return out


def build():
    return {'_comment':'Generated by tests/gen_fast_switch_cases.py from channel_model.py, probe_policy.py and advisor.py; shared with tests/lua/test_fast_switch.lua.',
            'tolerance':1e-9,'now':NOW,'profile':PROFILE,'reserve':RESERVE,'options':option_cases(),'leave':leave_cases(),'wake':wake_cases(),'advisor':advisor_cases()}


def text():
    return json.dumps(build(),ensure_ascii=True,sort_keys=True,indent=0)+'\n'


if __name__=='__main__':
    if '--write' in sys.argv:
        with open(TARGET,'w',encoding='utf-8',newline='\n') as f:f.write(text())
    print(TARGET,len(text()))
