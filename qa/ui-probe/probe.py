"""Loopback synthetic fixture + headless Edge page probe. No router access, no network beyond 127.0.0.1.
Usage: python qa/ui-probe/probe.py gate | matrix main | matrix more-a|more-b|more-c | scen
Results go to private/ui-probe/ (git-ignored). Each persona has a bounded timeout; a full 50-case run takes several minutes."""
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
FOOL=(HERE/'fool.js').read_text(encoding='utf8')
RESULTS={};EVENTS={}
FROZEN_PREVIEW=None
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
        if FROZEN_PREVIEW is not None and not p.startswith('/__probe/'):
            expected={'127.0.0.1:'+str(PORT),'localhost:'+str(PORT),'[::1]:'+str(PORT)}
            if self.headers.get('Host','').lower() not in expected or self.headers.get('Origin') and self.headers['Origin'] not in {'http://'+host for host in expected}:self.send_error(403);return
            from source_identity import content_type
            body=FROZEN_PREVIEW.get(p)
            if body is None:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',content_type(p));self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-HomenSAI-Preview','synthetic-only');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cross-Origin-Resource-Policy','same-origin')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'self'")
            self.end_headers();self.wfile.write(body);return
        if p.startswith('/__probe/'):
            kind,d,tab,theme,lang,w,h,qid=p.split('/')[2:10]
            js={'matrix':ANALYSE,'fool':FOOL}.get(kind,SCEN)
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
    if not got:return {'error':'TIMEOUT','cfg':[d,tab,theme,lang,w],'progress':RESULTS.pop('prog-'+qid,None)}
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


def fool(part,workers=2):
    """Persona numbers a-b. Each result retains its own failure; rerun selected cases as separate commands."""
    a,b=map(int,part.split('-'))
    if not 0<=a<=b<=49 or workers not in (1,2):raise ValueError('FOOL-RUN-BOUNDS')
    from datetime import datetime,timezone
    from source_identity import freeze_preview
    global FROZEN_PREVIEW
    FROZEN_PREVIEW,identity,manifest=freeze_preview(REPO)
    manifest['plan']={'personas':list(range(a,b+1)),'workers':workers,'per_case_timeout_seconds':120}
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (OUTDIR/('source-fool-%s-%s.json'%(part,stamp))).write_text(json.dumps(manifest,indent=1),encoding='utf-8')
    jobs=[('fool','abc'[(p//10+p)%3],str(p),'light','en',1280) for p in range(a,b+1)]
    sys.path.insert(0,str(HERE));import fool_check
    def one(job):
        case_path=OUTDIR/('case-fool-%s-%s.json'%(job[2],stamp))
        case_path.write_text(json.dumps([{'persona':int(job[2]),'error':'INCOMPLETE-ATTEMPT','verdict':'RUNNING','source_identity':identity}],indent=1),encoding='utf-8')
        try:row=run(*job,timeout=120)
        except Exception as error:row={'error':'HARNESS-'+type(error).__name__,'cfg':list(job[1:])}
        row['source_identity']=identity
        row['verdict']='FAIL' if fool_check.failed(fool_check.summarise([row])) else 'PASS'
        temporary=case_path.with_suffix('.json.tmp');temporary.write_text(json.dumps([row],indent=1),encoding='utf-8');temporary.replace(case_path)
        print('CASE',job[2],row['verdict'],'steps',row.get('steps',0),'calls',row.get('callCount',0),flush=True)
        return row
    with ThreadPoolExecutor(workers) as ex:res=list(ex.map(one,jobs))
    result_path=OUTDIR/('result-fool-%s-%s.json'%(part,stamp))
    result_path.write_text(json.dumps(res,indent=1),encoding='utf-8')
    summary=fool_check.summarise(res);fool_check.show(summary);print('RESULT',result_path)
    srv.shutdown();sys.exit(1 if fool_check.failed(summary) else 0)


if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='gate':gate()
    if mode=='fool':
        import argparse
        parser=argparse.ArgumentParser();parser.add_argument('part',nargs='?',default='0-49');parser.add_argument('--workers',type=int,choices=(1,2),default=2)
        args=parser.parse_args(sys.argv[2:]);fool(args.part,args.workers)
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
