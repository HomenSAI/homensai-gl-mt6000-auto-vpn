"""Scratch QA: real app JS -> HTTP -> real manual queue/transaction code.

UCI and VPN probes are explicit fixtures. QA_REAL_KERNEL=1 uses actual
disposable QEMU guest netfilter/ip rules; otherwise kernel readback is a model.
No physical router, credentials, host network writes or deployment are used.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from http.server import HTTPServer
from urllib.parse import urlsplit
from unittest.mock import patch

from qa_config import REPO,OUT,HTTP_PORT
LABEL=os.environ.get('QA_LABEL','baseline')
ASSETS_REPO=Path(os.environ.get('QA_ASSETS_REPO',str(REPO))).resolve()
VERSION=json.loads((ASSETS_REPO/'VERSION.json').read_text())['application']['version']
sys.path.insert(0,str(REPO/'router/tests'))
from test_pair_manual_directions import PairManualDirections,NOW,SOURCE,TARGET
import agent,auto_control,native_switch as native,pair_auto,pair_manual,channel_path,website_response
spec=importlib.util.spec_from_file_location('qa_preview',ASSETS_REPO/'scripts/serve-ui-preview.py')
preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)
preview.discover_router_origin=lambda:None

if os.environ.get('QA_REAL_KERNEL')=='1':
    from browser_kernel_fixture import QemuFixture
    test=QemuFixture();test.setUp();SOURCE=test.profiles[0]['id'];TARGET=test.profiles[1]['id']
else:
    test=PairManualDirections();test.setUp()
samples=[];probe_health={SOURCE:True,TARGET:True}
clock=[NOW];test.enterContext(patch('pair_manual.time.time',side_effect=lambda:clock[0]))
test.kernel_applied=True
events=[]
replay=[]
captured=[]
MODULE=preview.preview_module()
IDENTITY={'mode':'synthetic-platform-real-python-manual-queue-and-native-transaction',
          'generated_dashboard_sha256':hashlib.sha256(MODULE).hexdigest(),
          'kernel':'MODEL ONLY: PairManualDirections fixture',
          'device':'NONE','epoch':NOW,'version':VERSION,'repository_commit':__import__('subprocess').check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
          'python_source_sha256':{name:hashlib.sha256((REPO/'router/files/usr/lib/homensai-vpn'/name).read_bytes()).hexdigest()for name in('pair_manual.py', 'pair_auto.py', 'native_switch.py', 'channel_path.py', 'kernel_policy.py', 'pair_policy.py', 'recovery_settings.py', 'failure_diagnosis.py', 'failover_plan.py', 'auto_control.py', 'manual_control.py', 'manual_dispatch.py', 'agent.py', 'website_response.py', 'website_publication.py', 'rollback_recovery.py')}}
IDENTITY['isolation']={'etc_readonly':bool(os.statvfs('/etc').f_flag&os.ST_RDONLY),'run_readonly':bool(os.statvfs('/run').f_flag&os.ST_RDONLY),'mount_namespace':os.readlink('/proc/self/ns/mnt'),'effective_capabilities':next(line.split(':',1)[1].strip()for line in Path('/proc/self/status').read_text().splitlines()if line.startswith('CapEff:'))}
if os.environ.get('QA_REAL_KERNEL')=='1':
    IDENTITY.update(mode='actual-python-manual-api-lua-parser-native-transaction-and-qemu-kernel',kernel='Actual OpenWrt21.02.7/kernel5.4.238/iproute5.11/iptables1.8.7 via private serial',device='Disposable x86/64 QEMU; synthetic UCI inventory/vendor RTP compiler/tunnel health/worker launch; not physical GL.iNet')

def persist_evidence():
    (OUT/('browser-backend-events-'+LABEL+'.json')).write_text(json.dumps({'identity':IDENTITY,'events':events},indent=2))

def publish(value):
    row=copy.deepcopy(value);row.setdefault('time',clock[0]);row.setdefault('source',SOURCE);row.setdefault('target',TARGET)
    agent.atomic_json(native.STATE,row)
    events.append({'kind':'native-publish','time':clock[0],'value':row})
test.publish.side_effect=publish

def status():
    profiles=[]
    for index,role in enumerate(('source','target')):
        row=copy.deepcopy(test.selection[role]);row.update(code=None if probe_health[row['id']] else 'VPN-003',dns_ok=True,https_success=2 if probe_health[row['id']] else 0);row.update(name='Synthetic '+('WireGuard primary'if index==0 else'OpenVPN reserve'),time=clock[0])
        rows=[{'id':target[0],'url':'https://'+target[1]+target[2],'state':'ok','elapsed_ms':(100 if index==0 else 200)+value,
               'http_status':target[3],'code':None}for value,target in zip((0,10,20),website_response.TARGETS)]
        row['website_response']=website_response.public(row,'ok',None,clock[0],rows)
        profiles.append(row)
    native_state=agent.read_json(native.STATE,{})
    native_state.update(time=clock[0],source=SOURCE,target=TARGET,mode='continuous-pair',proof_scope=pair_auto.MODE)
    agent.atomic_json(native.STATE,native_state)
    value={'version':VERSION,'time':clock[0],'profiles':profiles,'samples':copy.deepcopy(samples),
           'native_failover':native_state,'auto_control':{'requested':'on','requested_at':NOW-10,
               'control_revision':test.revision,'pair_phase':pair_auto.read_state()['phase']},
           'events':[],'native_history':{'available':False,'events':[]},'speed_tests':{'results':[]}}
    from vendor_fixture import attach
    attach(value,clock[0])
    agent.atomic_json(agent.RUNTIME/'status.json',value)
    value['channel_path']=channel_path.pair_snapshot(value,pair_auto.read_state(),native.journal_read(),test.backend.order(),clock[0],test.kernel_proof())
    value['manual_switch_control']=pair_manual.controls();value['manual_switch']=pair_manual.public()
    return value

def inventory():
    value=status()
    return {'profiles':value['profiles'],'servers':[{'profile':row['id'],'name':row['name'],'priority':i+1,'enabled':True}for i,row in enumerate(value['profiles'])],
            'settings':{**test.settings,'terms_version':'1','setup_complete':True,'onboarding_complete':True,'onboarding_version':1,
                        'enabled':True,'plan_source':SOURCE,'plan_target':TARGET,'interval':30,'checkpoint':900,
                        'telegram_enabled':False,'native_duration':10}}

BRIDGE=r'''
const fixtureRPC=window.rpc;
window.rpc={declare:spec=>{
 const fallback=fixtureRPC.declare(spec);
 return (...args)=>{
  if(['inventory','status','pair_manual'].includes(spec.method)){
   window.fixtureCalls.push({method:spec.method,params:spec.params,args});
   return fetch('/__qa/rpc/'+spec.method,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(args)}).then(r=>{if(!r.ok)throw new Error('QA-BRIDGE-HTTP-'+r.status);return r.json();});
  }
  return fallback(...args);
 };
}};
window.__qaSnapshot=()=>fetch('/__qa/state').then(r=>r.json());
'''

class Handler(preview.Handler):
    def send_bytes(self,body,kind='application/json'):
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def json(self,value):self.send_bytes(json.dumps(value).encode())
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/__qa/state':
            self.json({'identity':IDENTITY,'status':status(),'pair':pair_auto.read_state(),'journal':native.journal_read(),
                       'model_order':test.current,'model_kernel':test.kernel_proof(),
                       'kernel_applications':getattr(test,'kernel_applications',[]),'native_worker_calls':getattr(test,'spawned',None),
                       'events':len(events),'budget':agent.read_json(agent.PERSIST/'pair-auto-budget.json',{})});return
        if path=='/preview-module.js':self.send_bytes(MODULE,'application/javascript');return
        if path=='/qa/ui-preview/stub.js':
            body=(ASSETS_REPO/'qa/ui-preview/stub.js').read_text()
            anchor="fetch('/preview-module.js',{cache:'no-store'})"
            assert body.count(anchor)==1
            body=body.replace(anchor,BRIDGE+'\n'+anchor)
            self.send_bytes(body.encode(),'application/javascript');return
        super().do_GET()
    def do_POST(self):
        path=urlsplit(self.path).path
        try:
            data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0')))or'[]')
            if path=='/__qa/rpc/status':result=replay.pop(0) if replay else status()
            elif path=='/__qa/rpc/inventory':result=inventory()
            elif path=='/__qa/rpc/pair_manual':
                before=pair_manual.public();result=pair_manual.request(*data)
                events.append({'kind':'browser-rpc','time':clock[0],'args':data,'before':before,'answer':result,'after':pair_manual.public()})
            elif path=='/__qa/consume':
                result=pair_manual.consume(test.backend,pair_auto.read_state(),test.settings,test.revision)
                events.append({'kind':'consume','time':clock[0],'returned':result,'public':pair_manual.public(),
                               'journal':native.journal_read(),'model_order':test.current,'model_kernel':test.kernel_proof()})
                result={'consumed':result,'status':status()}
            elif path=='/__qa/auto_tick':
                primary_good=data.get('primary')!='failed';probe_health[SOURCE]=primary_good;test.health_values[SOURCE]=primary_good
                samples[:]=[dict(id=identifier,time=clock[0]-delay,code=None if probe_health[identifier] else 'VPN-003',dns_ok=True,https_success=2 if probe_health[identifier] else 0) for identifier in (SOURCE,TARGET) for delay in (0,15,30)]
                status();before=len(test.kernel_applications);handled=pair_auto.tick(test.backend,test.settings,test.revision)
                result={'handled':handled,'status':status(),'applications_before':before,'applications_after':len(test.kernel_applications)}
                events.append({'kind':'auto-tick','time':clock[0],'controlled_primary':data.get('primary'),'result':result,'journal':native.journal_read()})
            elif path=='/__qa/capture':
                captured[:]=[copy.deepcopy(status())];result={'captured':True}
            elif path=='/__qa/replay':
                replay.extend(copy.deepcopy(captured[0])for _ in range(int(data.get('count',1))));result={'replay':len(replay)}
            elif path=='/__qa/advance':
                clock[0]+=float(data['seconds']);result={'epoch':clock[0],'status':status()}
            elif path=='/__qa/orphan':
                row=pair_manual.read();row['state']='CLAIMED';agent.atomic_json(pair_manual.path(),row)
                result={'status':status()};events.append({'kind':'inject-interrupted-claim','time':clock[0]})
            elif path=='/__qa/recover':
                pair_manual.recover();result={'status':status()};events.append({'kind':'recover','time':clock[0],'public':pair_manual.public()})
            else:self.send_error(404);return
            persist_evidence();self.json(result)
        except BaseException as error:
            events.append({'kind':'harness-error','error':type(error).__name__+': '+str(error)});persist_evidence()
            self.send_error(500,type(error).__name__)

try:
    persist_evidence()
    with HTTPServer(('127.0.0.1',HTTP_PORT),Handler)as server:
        print('QA bridge on loopback %d; no physical device; generated module frozen'%HTTP_PORT,flush=True)
        server.serve_forever()
finally:
    test.doCleanups()
