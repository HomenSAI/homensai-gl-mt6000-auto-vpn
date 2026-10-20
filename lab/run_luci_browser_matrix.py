"""Headless InPrivate browser through a pinned, loopback-only disposable-VM proxy."""
import argparse
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
import json
import re
from pathlib import Path
import subprocess
import threading
import uuid

from virtual_luci_proxy import Handler,allowed_request,clone_identity
from endurance_state import container_name

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--container',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--port',type=int,default=18902);p.add_argument('--quick',action='store_true')
    p.add_argument('--expected-agent-version');p.add_argument('--expected-package-version')
    p.add_argument('--rpc-timeout-seconds',type=int,choices=(20,60),default=20)
    p.add_argument('--accept-terms-version',choices=('1',));p.add_argument('--terms-only',action='store_true');a=p.parse_args()
    if a.terms_only and a.accept_terms_version is not None:raise ValueError('READ-ONLY-TERMS-MODE-CANNOT-ACCEPT')
    for version in (a.expected_agent_version,a.expected_package_version):
        if version is not None and not re.fullmatch(r'[0-9A-Za-z.+~_-]{1,48}',version):raise ValueError('EXPECTED-VERSION-INVALID')
    out=a.out.resolve()
    if not out.is_relative_to((ROOT/'private').resolve()) or out.exists():raise ValueError('PRIVATE-FRESH-OUTPUT-REQUIRED')
    if not 1024<=a.port<=65535:raise ValueError('LOCAL-PORT-INVALID')
    name=container_name(a.container);identity=clone_identity(name)
    subprocess.run(['docker','exec',identity,'python3','-c','from serial_clone import require_clone;require_clone()'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not edge.is_file():raise ValueError('EDGE-NOT-AVAILABLE')
    groups=[dict(design=d,lang=lang,width=w,height=840 if w>500 else 740) for d in 'abc' for lang in ('en','ru') for w in (1440,390)]
    if a.quick:groups=[groups[0],groups[7]]
    out.mkdir(parents=True)
    run_id=uuid.uuid4().hex;event=threading.Event();received={}
    script=(ROOT/'lab/luci_browser_matrix.js').read_text(encoding='utf-8')
    class MatrixHandler(Handler):
        def do_GET(self):
            if self.path=='/__lab/runner':
                if not allowed_request('GET','/',self.headers.get('Host',''),self.headers.get('Origin'),self.headers.get('Sec-Fetch-Site'),self.server.server_port):self.send_error(403);return
                body=('<!doctype html><meta charset=utf-8><body style="margin:0"><iframe id=lab-frame style="border:0"></iframe><script>const CFG='+json.dumps({'id':run_id,'groups':groups,'expectedAgent':a.expected_agent_version,'expectedPackage':a.expected_package_version,'rpcTimeout':a.rpc_timeout_seconds,'acceptTermsVersion':a.accept_terms_version,'termsOnly':a.terms_only})+';'+script+'</script>').encode()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
            return self.forward_request()
        def do_POST(self):
            if self.path=='/__lab/result/'+run_id:
                if not allowed_request('POST','/',self.headers.get('Host',''),self.headers.get('Origin'),self.headers.get('Sec-Fetch-Site'),self.server.server_port):self.send_error(403);return
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=256*1024:raise ValueError()
                    row=json.loads(self.rfile.read(length));received.update(row);event.set()
                except (ValueError,OSError):self.send_error(400);return
                self.send_response(204);self.end_headers();return
            return self.forward_request()
    with ThreadingHTTPServer(('127.0.0.1',a.port),MatrixHandler) as server:
        server.container=name;server.clone_id=identity;server.observed=[];server.rpc_timeout_seconds=a.rpc_timeout_seconds
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        args=[str(edge),'--headless=new','--inprivate','--disable-gpu','--no-first-run','--disable-background-networking',
              '--user-data-dir='+str(out/'browser-profile'),'--window-size=1600,1000','http://127.0.0.1:'+str(a.port)+'/__lab/runner']
        child=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        host_budget=1800 if not a.quick and a.rpc_timeout_seconds==60 else min(3600,len(groups)*300+30)
        try:finished=event.wait(host_budget)
        finally:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
            server.shutdown();worker.join(timeout=10)
    received.update(container_id=identity,host_head_at_observation=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    host_worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                    expected_agent=a.expected_agent_version,expected_package=a.expected_package_version,
                    host_deadline_seconds=host_budget,rpc_deadline_seconds=a.rpc_timeout_seconds,
                    completed_at_utc=datetime.now(timezone.utc).isoformat(),transport=server.observed)
    passed=finished and not received.get('errors') and len(received.get('rows',[]))==len(groups)*(1 if a.terms_only else 12) and all(r.get('result')=='PASS' for r in received.get('rows',[]))
    received['result']='PASS' if passed else 'FAIL'
    if not finished:received['errors']=['ACTUAL-BROWSER-HOST-DEADLINE']
    (out/'result.json').write_text(json.dumps(received,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':received['result'],'cases':len(received.get('rows',[])),'errors':received.get('errors'),
                      'failures':[{k:r.get(k) for k in ('design','lang','width','tab','reason','overflow','opened','badge','footer')} for r in received.get('rows',[]) if r.get('result')!='PASS'],'evidence':str(out/'result.json')}))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
