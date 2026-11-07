"""Current UI browser gate: immutable inputs, one owned Edge tree, loopback only."""
import argparse
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import hashlib
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import urlsplit
import uuid
from source_identity import freeze_preview,content_type
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SURFACES=['home','settings','ch','auto','srv','log','sys']


def release_source(identity):
    return bool(identity.get('git_head') and identity.get('git_tracked_dirty') is False and identity.get('git_untracked_paths')==[])


def problems(result,groups):
    bad=[];rows=result.get('rows',[])
    for group in groups:
        own=[r for r in rows if r.get('group')==group]
        for surface in SURFACES:
            if sum(r.get('kind')=='page' and r.get('surface')==surface for r in own)!=1:bad.append('missing/duplicate page '+str(group)+' '+surface)
        for step in range(1,5):
            if sum(r.get('kind')=='wizard' and r.get('step')==step for r in own)!=1:bad.append('missing/duplicate wizard '+str(group)+' '+str(step))
        for role in ('primary','reserve'):
            if not any(r.get('kind')=='traffic' and r.get('role')==role for r in own):bad.append('missing traffic '+str(group)+' '+role)
        for boundary in ('same-pair-rejected','skip-without-start','save-without-start','running-suppresses-first-run','existing-pair-suppresses-first-run','explicit-wizard-running'):
            if sum(r.get('kind')=='boundary' and r.get('boundary')==boundary for r in own)!=1:bad.append('missing/duplicate boundary '+str(group)+' '+boundary)
        if not any(r.get('kind')=='modal' and r.get('modal')=='help' for r in own):bad.append('missing help modal '+str(group))
        for role in ('primary','reserve'):
            if not any(r.get('kind')=='traffic-console' and r.get('role')==role for r in own):bad.append('missing Console geometry '+str(group)+' '+role)
    if result.get('errors'):bad.append('browser/harness errors')
    if any(not r.get('pass') for r in rows):bad.append('failed assertion rows')
    if not result.get('complete'):bad.append('incomplete attempt')
    return bad


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--timeout',type=int,default=900)
    args=parser.parse_args()
    if args.port==18898 or args.port and not 1024<=args.port<=65535:parser.error('use ephemeral/dedicated port, never legacy 18898')
    if not 30<=args.timeout<=1800:parser.error('timeout must be 30..1800 seconds')
    frozen,identity,manifest=freeze_preview(ROOT)
    if not args.smoke and not release_source(identity):
        out=ROOT/'private/ui-probe';out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path=out/('preflight-current-'+stamp+'.json')
        path.write_text(json.dumps(dict(verdict='BLOCKED-NON_RELEASE',source_identity=identity),indent=2),encoding='utf-8')
        print('CURRENT-GATE BLOCKED-NON_RELEASE',str(path),flush=True)
        return 2
    groups=[dict(width=w,lang=l,theme=t) for w in (1440,390) for l in ('ru','en') for t in ('light','dark')]
    if args.smoke:groups=[dict(width=1440,lang='en',theme='light')]
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8]
    out=ROOT/'private/ui-probe';out.mkdir(parents=True,exist_ok=True)
    done=threading.Event();results={};requests=[];lock=threading.Lock()
    script=(HERE/'current_analyse.js').read_bytes()
    if hashlib.sha256(script).hexdigest()!=manifest['harness_files']['qa/ui-probe/current_analyse.js']:raise ValueError('CURRENT-GATE-HARNESS-CHANGED')
    app=json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
    class Handler(BaseHTTPRequestHandler):
        def allowed(self):
            host='127.0.0.1:'+str(self.server.server_port)
            return self.headers.get('Host')==host and (not self.headers.get('Origin') or self.headers['Origin']=='http://'+host)
        def do_GET(self):
            path=urlsplit(self.path).path
            if not self.allowed():self.send_error(403);return
            if path=='/__current/'+run:
                cfg=json.dumps(dict(run=run,groups=groups,version=app['version'],goldTolerance=.005))
                body=("<!doctype html><meta charset=utf-8><body style='margin:0'><iframe id=f style='border:0;width:1440px;height:1000px'></iframe><script>const CFG="+cfg+';</script><script src="/__current.js"></script>').encode();kind='text/html; charset=utf-8'
            elif path=='/__current.js':body=script;kind='application/javascript; charset=utf-8'
            else:body=frozen.get(path);kind=content_type(path)
            with lock:requests.append(dict(path=path,status=200 if body is not None else 404))
            if body is None:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'self'")
            self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if not self.allowed():self.send_error(403);return
            path=urlsplit(self.path).path
            if path not in ('/__row/'+run,'/__done/'+run):self.send_error(404);return
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=8*1024*1024:self.send_error(413);return
            value=json.loads(self.rfile.read(n))
            if path.startswith('/__row/'):
                with lock:number=results.get('row_count',0);results['row_count']=number+1
                (out/('case-current-'+run+'-'+str(number)+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
            else:results['result']=value;done.set()
            self.send_response(204);self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    manifest.update(plan=dict(groups=groups,surfaces=SURFACES,wizard_steps=[1,2,3,4],concurrency=1,smoke=args.smoke),
                    run=run,port=server.server_port,scope='synthetic current UI; no physical router acceptance')
    (out/('source-current-'+run+'.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    profile=out/'profiles'/('current-'+run)
    proc=None;started=time.monotonic()
    try:
        with (out/('edge-current-'+run+'.log')).open('wb') as log:
            proc=subprocess.Popen([str(edge),'--headless=new','--disable-gpu','--no-first-run','--inprivate','--disable-background-networking',
                '--renderer-process-limit=2','--user-data-dir='+str(profile),'--window-size=1500,1100',
                'http://127.0.0.1:'+str(server.server_port)+'/__current/'+run],stdout=log,stderr=log,creationflags=getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0))
            while not done.wait(.25):
                if proc.poll() is not None or time.monotonic()-started>args.timeout:break
    finally:
        if proc is not None and proc.poll() is None:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=30)
        server.shutdown();server.server_close()
    result=results.get('result',dict(complete=False,rows=[],errors=['TIMEOUT-OR-EARLY-EXIT']))
    failures=problems(result,groups)
    failed_requests=[r for r in requests if r['status']!=200 and r['path']!='/favicon.ico']
    if failed_requests:failures.append('resource requests failed')
    result.update(source_identity=identity,requests=requests,resource_failures=failed_requests,failures=failures,
                  classification='NON_RELEASE' if args.smoke else 'RELEASE',release_eligible=release_source(identity),
                  verdict='FAIL' if failures else 'NON_RELEASE-SMOKE' if args.smoke else 'PASS',elapsed_seconds=round(time.monotonic()-started,2),
                  owned_pid=proc.pid if proc else None,profile=str(profile),run=run)
    path=out/('result-current-'+run+'.json');path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('CURRENT-GATE',result['verdict'],'rows',len(result['rows']),str(path),flush=True)
    for failure in failures:print('FAIL',failure,flush=True)
    return 1 if failures else 0


if __name__=='__main__':raise SystemExit(main())
