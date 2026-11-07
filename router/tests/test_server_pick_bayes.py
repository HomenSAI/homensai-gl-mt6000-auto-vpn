"""server_pick.py: the Bayesian server pick (owner setting server_pick_model 'bayes'). The cases are shared with
tests/lua/test_server_pick_bayes.lua (server_pick_bayes_cases.json): Python and Lua update, decide, plan and publish
the same. Offline study (simple vs bayes): private/math/bayes-pick."""
import json
import math

from pathlib import Path
import random
import shutil
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import server_pick as S  # noqa: E402

CASES=json.loads((HERE/'server_pick_bayes_cases.json').read_text(encoding='utf-8'))
LUA=shutil.which('lua5.1')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def r(x,scale):return None if x is None else int(math.floor(x*scale+0.5))


class World:
    """The fake router of test_server_pick.World; a tcp value may be a list (one value per connect, then refused)."""
    def __init__(self,c):
        self.c=c;self.files=dict(c['files']);self.writes={};self.exec=[];self.logs=[];self.used={}
        def write(path,text):
            if path in c.get('write_fail',[]):return False
            self.files[path]=text;self.writes[path]=text;return True
        def run(argv,seconds):
            self.exec.append(list(argv))
            if argv[:4]==['uci','-q','-X','show']:
                text=c['uci'].get(argv[4]);return (0,text) if text is not None else (1,'')
            if argv[0]=='ping':
                text=c['ping'].get(argv[-1]);return (0 if text and 'round-trip' in text else 1,text or '')
            return c.get('rc',{}).get(' '.join(argv),0),''
        def tcp(host,port,timeout,device):
            self.exec.append(['tcp',host,str(port),device or ''])
            key='%s:%d'%(host,port);v=c['tcp'].get(key)
            if isinstance(v,list):
                i=self.used.get(key,0);self.used[key]=i+1
                return v[i] if i<len(v) else None
            return v
        self.io={'runtime':'/run','read':self.files.get,'write':write,'exec':run,'tcp':tcp,'alive':lambda pid:pid in c.get('alive',[]),
                 'wan':lambda:c.get('wan'),'active_mark':lambda:c.get('active_mark'),'log':self.logs.append}


class SharedCases(unittest.TestCase):
    def test_model_update(self):
        for c in CASES['model_update']:self.assertEqual(S.model_update(c['entry'],c['now'],c['samples']),c['expect'],c['name'])

    def test_posterior(self):
        for c in CASES['posterior']:
            st=S.model_state(c['entry'],c['now']);p=S.posterior(st)
            got={'mu_e6':None if p is None else r(p[0],1e6),'var_e9':None if p is None else r(p[1],1e9),
                 'availability_e6':r(S.availability(st),1e6) if st else None}
            self.assertEqual(got,c['expect'],c['name'])

    def test_probe_plan(self):
        for c in CASES['probe_plan']:
            self.assertEqual(S.probe_plan(c['rows'],[S.model_state(e,c['now']) for e in c['entries']],c['now']),c['expect'],c['name'])

    def test_decide(self):
        for c in CASES['decide']:
            t=S.decide_bayes(c['rows'],[S.model_state(e,c['now']) for e in c['entries']])
            self.assertEqual(None if t is None else t['profile'],c['expect'],c['name'])

    def test_model_file(self):
        for c in CASES['model_read']:
            files={} if c['text'] is None else {'/run/'+S.MODEL:c['text']}
            self.assertEqual(S.model_read({'runtime':'/run','read':files.get}),c['expect'],c['name'])
        for c in CASES['model_text']:self.assertEqual(S.model_text(c['model'],c['now']),c['expect'],c['name'])

    def test_jobs(self):
        for c in CASES['job']:
            with self.subTest(c['name']):
                w=World(c);result=S.job(w.io,c['request'],c['now'])
                self.assertEqual(canonical(result),canonical(c['expect']['result']))
                self.assertEqual(w.writes,c['expect']['writes']);self.assertEqual(w.exec,c['expect']['exec']);self.assertEqual(w.logs,c['expect']['logs'])
                self.assertEqual(canonical(S.project(json.loads(w.files['/run/server-pick.json']))),canonical(S.project(result)))


class HandChecked(unittest.TestCase):
    """Numbers computed by hand, independent of the generated expectations."""
    def test_conjugate_update_by_hand(self):
        self.assertEqual(S.model_update(None,1000,[60,60,60]),[1000,3000,round(math.log(60)*10000),0,1000,0,1])
        # (ln50, ln60, ln72): mean ln60 (50*72=60^2), SS = 2*ln(1.2)^2
        e=S.model_update(None,1000,[50,60,72]);self.assertEqual(e[2],40943);self.assertEqual(e[3],round(2*math.log(1.2)**2*10000))
        # one half-life later: n 3 -> 1.5, ok 1 -> 0.5; three samples of 30 ms move mu by 3/4.5 of the gap
        e=S.model_update([1000,3000,40943,0,1000,0,1],4600,[30,30,30])
        gap=math.log(30)-4.0943
        self.assertEqual(e[:6],[4600,4500,round((4.0943+gap*3/4.5)*10000),round(1.5*3*gap*gap/4.5*10000),1500,0])
        self.assertEqual(S.model_update([1000,3000,40943,0,1000,0,1],4600,None),[4600,1500,40943,0,500,1000,0])

    def test_posterior_by_hand(self):
        # NIG with alpha0=2, beta0=0.16: var(mu) = (0.16 + SS/2) / (n (1 + n/2))
        mu,var=S.posterior(S.model_state([1000,3000,40943,0,1000,0,1],1000))
        self.assertAlmostEqual(mu,4.0943);self.assertAlmostEqual(var,0.16/7.5)
        self.assertIsNone(S.posterior(S.model_state([1000,999,40943,0,1000,0,1],1000)),'less than one sample of evidence')
        self.assertAlmostEqual(S.availability(S.model_state([1000,3000,0,0,3000,1000,1],1000)),100*4/6)

    def test_95_percent_rule_by_hand(self):
        # two servers with exactly known variance v each: change iff (mu_cur - mu_cand) / sqrt(2v) >= 1.645
        def entries(cur,cand,n):return [S.model_state([1000,n*1000,round(math.log(cur)*10000),0,9000,0,1],1000),
                                        S.model_state([1000,n*1000,round(math.log(cand)*10000),0,9000,0,1],1000)]
        rows=[{'profile':'1_0','current':True,'alive':True},{'profile':'1_1','alive':True}]
        v=0.16/(30*(1+15))
        edge=math.exp(-1.645*math.sqrt(2*v))*60  # the candidate RTT at exactly z = 1.645
        self.assertEqual(S.decide_bayes(rows,entries(60,edge*0.99,30))['profile'],'1_1')
        self.assertIsNone(S.decide_bayes(rows,entries(60,edge*1.01,30)))

    def test_model_name(self):
        for value,expect in (('bayes','bayes'),('simple','simple'),(None,'simple'),('','simple'),('Bayes','simple'),(1,'simple')):
            self.assertEqual(S.model_name(value),expect)


class Invariants(unittest.TestCase):
    def test_bayes_never_executes_a_switch_nor_touches_the_supervisor_state(self):
        for c in CASES['job']:
            for argv in c['expect']['exec']:self.assertNotIn(argv[0],('ifdown','ifup'),c['name']);self.assertNotEqual(argv[:2],['uci','set'],c['name'])
            self.assertNotIn('/run/'+S.STATE,c['expect']['writes'],c['name'])

    def test_off_or_simple_writes_no_model(self):
        for c in CASES['job']:
            if c['request'].get('enabled') is not True or S.model_name(c['request'].get('model'))!='bayes':
                self.assertNotIn('/run/'+S.MODEL,c['expect']['writes'],c['name'])

    def test_bayes_never_probes_more_than_simple(self):
        """The same world in both modes: the bandit measures a subset (the dead-current pass at most all of them)."""
        for c in CASES['job']:
            if S.model_name(c['request'].get('model'))!='bayes' or c['request'].get('enabled') is not True:continue
            simple=json.loads(json.dumps(c));simple['request']['model']='simple'
            a=World(c);S.job(a.io,c['request'],c['now'])
            b=World(simple);S.job(b.io,simple['request'],simple['now'])
            self.assertLessEqual(sum(x[0]=='tcp' for x in a.exec),sum(x[0]=='tcp' for x in b.exec),c['name'])
            self.assertLessEqual(sum(x[0]=='ping' for x in a.exec),sum(x[0]=='ping' for x in b.exec),c['name'])

    def test_rate_limit_and_carrying_still_apply(self):
        warm=next(c for c in CASES['job'] if c['name'].startswith('bayes warm, a clearly faster'))
        limited=json.loads(json.dumps(warm));limited['files']['/run/'+S.STATE]=json.dumps({'changes':{'4192':[99000,99100,99200,99300]}})
        w=World(limited);res=S.job(w.io,limited['request'],limited['now'])
        self.assertEqual(res['tunnels'][0]['code'],S.LIMIT);self.assertNotIn('/run/'+S.CHANGE,w.writes)
        carrying=json.loads(json.dumps(warm));carrying['active_mark']=45056
        w=World(carrying);res=S.job(w.io,carrying['request'],carrying['now'])
        self.assertEqual(res['tunnels'][0]['code'],S.CARRYING);self.assertNotIn('/run/'+S.CHANGE,w.writes)

    def test_random_worlds_are_safe(self):
        """Random models and readings: every target answered this round, is switchable and is not the current one;
        a working current server is never left for a server whose posterior is not lower."""
        rng=random.Random(20261103)
        for _ in range(3000):
            n=rng.randint(1,6);cur=rng.randrange(n)
            rows=[{'profile':'1_%d'%i,'current':i==cur,'alive':rng.choice([True,True,False,None]),'switchable':rng.choice([True,True,False])} for i in range(n)]
            states=[None if rng.random()<0.15 else S.model_state([1000,rng.randint(0,90000),rng.randint(20000,60000),rng.randint(0,90000),
                                                                  rng.randint(0,9000),rng.randint(0,9000),rng.randint(0,1)],1000+rng.randint(0,20000)) for _ in rows]
            t=S.decide_bayes(rows,states)
            if t is None:continue
            i=rows.index(t)
            self.assertIs(t['alive'],True);self.assertIsNot(t['switchable'],False);self.assertFalse(t['current'])
            if rows[cur]['alive'] is True and S.posterior(states[cur]) is not None:
                self.assertLess(S.posterior(states[i])[0],S.posterior(states[cur])[0])
                self.assertGreaterEqual(S.availability(states[i]),S.AVAILABLE_PCT)
            plan=S.probe_plan(rows,states,30000)
            self.assertTrue(plan[cur] or cur>=S.MAX_MEASURED)

    def test_model_file_is_bounded(self):
        model={'4192:1_%d'%i:[1000+i,1,1,1,1,1,1] for i in range(200)}
        value=json.loads(S.model_text(model,2000))
        self.assertEqual(len(value['servers']),S.MODEL_MAX);self.assertIn('4192:1_199',value['servers'])
        self.assertLess(len(S.model_text(model,2000)),S.MODEL_MAX*80)


class Constants(unittest.TestCase):
    def test_lua_and_python_constants_match(self):
        lua=(LIB/'lua/server_pick.lua').read_text(encoding='utf-8')
        for name in ('HALF_LIFE','PRIOR_A','PRIOR_B_E4','MARGIN_PCT','Z_CHANGE_E3','Z_PLAUSIBLE_E3','STALE','AVAILABLE_PCT','MODEL_MAX','MODEL_AGE'):
            self.assertRegex(lua,'M[.]%s=%s[;\n]'%(name,getattr(S,name)),name)
        self.assertIn("M.MODEL='%s'"%S.MODEL,lua);self.assertIn('LN2=%r'%S.LN2,lua)

    def test_the_owner_setting_reaches_both_monitors(self):
        inventory=(LIB/'inventory.lua').read_text(encoding='utf-8')
        self.assertIn("main.server_pick_model=s.server_pick_model=='bayes' and 'bayes' or 'simple'",inventory)
        self.assertIn("model=sp.model_name(settings.server_pick_model)",(LIB/'lua/monitor.lua').read_text(encoding='utf-8'))
        self.assertIn("'model':server_pick.model_name(settings.get('server_pick_model'))",(LIB/'agent.py').read_text(encoding='utf-8'))

    @unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
    def test_inventory_reads_the_setting(self):
        for choice,expect in (('bayes','bayes'),('simple','simple'),('','simple'),('thompson','simple'),(None,'simple')):
            argv=[LUA,str(HERE/'test_inventory.lua'),str(LIB/'inventory.lua'),'b']+([choice] if choice is not None else [])
            data=json.loads(subprocess.check_output(argv,text=True))
            self.assertEqual(data['settings']['server_pick_model'],expect,choice)


if __name__=='__main__':
    unittest.main()
