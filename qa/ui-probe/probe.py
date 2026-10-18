"""Loopback synthetic fixture + headless Edge page probe. No router access, no network beyond 127.0.0.1.
Usage: python qa/ui-probe/probe.py gate | matrix main | matrix more-a|more-b|more-c | scen
Results go to private/ui-probe/ (git-ignored). Keep each run under ~5 minutes."""
import importlib.util, json, re, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OUTDIR=REPO/'private'/'ui-probe';OUTDIR.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('prev',REPO/'scripts/serve-ui-preview.py');prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)
prev.discover_router_origin=lambda:None
PORT=18898
ANALYSE=(HERE/'analyse.js').read_text(encoding='utf8')
SCEN=(HERE/'scenarios.js').read_text(encoding='utf8')
RESULTS={};EVENTS={}
class H(prev.Handler):
    def do_POST(self):
        p=urlsplit(self.path).path
        n=int(self.headers.get('Content-Length','0'));data=self.rfile.read(n).decode('utf-8','replace')
        key=p.split('/')[-1];RESULTS[key]=data
        if key in EVENTS:EVENTS[key].set()
        self.send_response(204);self.end_headers()
    def send_header(self,k,v):
        if k=='Content-Security-Policy':v=v.replace("frame-ancestors 'none'","frame-ancestors 'self'")
        super().send_header(k,v)
    def do_GET(self):
        p=urlsplit(self.path).path
        if p.startswith('/__probe/'):
            kind,d,tab,theme,lang,w,h,qid=p.split('/')[2:10]
            js=(ANALYSE if kind=='matrix' else SCEN)
            body=("<!doctype html><meta charset=utf-8><body style='margin:0'><iframe id=f style='border:0;width:%spx;height:%spx'></iframe><pre id=result></pre><script>var CFG=%s;%s</script>"%(w,h,json.dumps(dict(design=d,tab=tab,theme=theme,lang=lang,w=int(w),h=int(h),id=self.path.split('/')[-1] if False else qid)),js)).encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
        return super().do_GET()
srv=ThreadingHTTPServer(('127.0.0.1',PORT),H);threading.Thread(target=srv.serve_forever,daemon=True).start()
EDGE=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
def run(kind,d,tab,theme,lang,w,h=900,budget=0,timeout=240):
    import uuid
    qid=uuid.uuid4().hex[:10];ev=threading.Event();EVENTS[qid]=ev
    prof=OUTDIR/'profiles'/qid
    url='http://127.0.0.1:%d/__probe/%s/%s/%s/%s/%s/%s/%s/%s'%(PORT,kind,d,tab,theme,lang,w,h,qid)
    cmd=[EDGE,'--headless=new','--disable-gpu','--no-first-run','--user-data-dir='+str(prof),'--window-size=%s,%s'%(w,h+40),url]
    proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        got=ev.wait(timeout)
    finally:
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    if not got:return {'error':'TIMEOUT','cfg':[d,tab,theme,lang,w]}
    try:out=json.loads(RESULTS.pop(qid));out['cfg']=[d,tab,theme,lang,w];return out
    except Exception as e:return {'error':'BAD-RESULT '+str(e)[:80],'cfg':[d,tab,theme,lang,w]}
TABS=['start','overview','channels','statistics','settings','help','learn','tests','traffic','services','events','readiness']
def gate_problems(x):
    """Hard failures of one matrix result: the owner attributes missing, a failed design view, script errors, overflow."""
    c='/'.join(map(str,x.get('cfg',[])))
    if x.get('error') or x.get('fatal') or not x.get('hasApp'):return [c+': no app ('+str(x.get('error') or x.get('fatal') or 'NO-APP')[:60]+')']
    bad=[]
    if not(x.get('attribution') and x.get('footer') and x.get('badge')):bad.append(c+': owner attributes missing')
    if x.get('designError'):bad.append(c+': DESIGN-VIEW-ERROR')
    if x.get('errors'):bad.append(c+': script errors '+str(x['errors'][:2]))
    if x.get('docOverflow',0)>0:bad.append(c+': horizontal overflow %s px'%x['docOverflow'])
    return bad


def gate():
    """Bounded gate for publication: 3 designs x 4 pages x 2 widths (about 3 minutes). A failing case is rerun once alone,
    because a slow stylesheet load under 4 parallel browsers gives false 'no app' and overflow results."""
    jobs=[('matrix',d,tab,'light','en',w) for d in 'abc' for tab in ('overview','channels','settings','events') for w in (1440,390)]
    with ThreadPoolExecutor(4) as ex:first=list(ex.map(lambda j:run(*j),jobs))
    problems=[]
    for job,x in zip(jobs,first):
        if gate_problems(x):
            again=run(*job);problems+=gate_problems(again)
    (OUTDIR/'result-gate.json').write_text(json.dumps(first,indent=1),encoding='utf-8')
    for line in problems:print('FAIL',line)
    print('GATE','FAIL' if problems else 'PASS',len(jobs),'cases')
    srv.shutdown();sys.exit(1 if problems else 0)


if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='gate':gate()
    jobs=[]
    part=sys.argv[2] if len(sys.argv)>2 else 'main'
    if mode=='matrix':
        if part=='main':   # every page x design, light EN desktop
            for d in 'abc':
                for tab in TABS:jobs.append(('matrix',d,tab,'light','en',1440))
        else:               # other conditions on the pages that differ most (part 'more-a' = design a only)
            for d in part.split('-')[1]:
                for tab in ['overview','channels','settings','events','statistics']:
                    jobs.append(('matrix',d,tab,'dark','en',1440));jobs.append(('matrix',d,tab,'light','ru',1440))
                    jobs.append(('matrix',d,tab,'light','en',900));jobs.append(('matrix',d,tab,'light','en',390))
    else:
        for d in 'abc':jobs.append(('scen',d,'overview','light','en',1280))
    res=[]
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda j:run(*j),jobs):res.append(r)
    (OUTDIR/('result-%s-%s.json'%(mode,part))).write_text(json.dumps(res,indent=1),encoding='utf-8')
    print('done',len(res),'errors',sum(1 for r in res if r.get('error')))
    srv.shutdown()
