"""Probe real Auto tick/transactions against isolated bridge with synthetic health."""
import json,urllib.request
from pathlib import Path
from qa_config import OUT,HTTP_PORT
base='http://127.0.0.1:%d/__qa/'%HTTP_PORT
out=OUT/'auto-api-kernel-probe.json'
report={'scope':'Actual production tick/streak/diagnosis/recovery_ready/native child + real QEMU kernel; synthetic UCI and DNS/HTTPS probe values','steps':[],'checks':[]}
def request(path,value=None):
 r=urllib.request.Request(base+path,data=json.dumps(value).encode() if value is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(r,timeout=120)as result:return json.load(result)
def snapshot(name):
 state=request('state');report['steps'].append({'name':name,'state':state});out.write_text(json.dumps(report,indent=2));return state
def check(name,value):report['checks'].append({'name':name,'passed':bool(value)})
try:
 first=snapshot('initial')
 result=request('auto_tick',{'primary':'failed'});failed=snapshot('automatic-failover')
 check('primary failure automatically selects actual reserve kernel',failed['model_kernel']['verified']and failed['model_kernel']['role']=='target')
 check('auto forward consumes one attempt',len(failed['budget'].get('events',[]))==1)
 check('auto completed journal is committed',failed['journal']['phase']=='COMMITTED')
 request('auto_tick',{'primary':'healthy'});early=snapshot('healthy-before-dwell')
 check('healthy primary before dwell does not return yet',early['model_kernel']['role']=='target'and len(early['kernel_applications'])==len(failed['kernel_applications']))
 request('advance',{'seconds':61});request('auto_tick',{'primary':'healthy'});back=snapshot('automatic-failback')
 check('stable recovered primary returns actual kernel',back['model_kernel']['verified']and back['model_kernel']['role']=='source')
 check('restoration does not charge forward budget',len(back['budget'].get('events',[]))==1)
 check('recovery journal records actual primary order',back['journal']['phase']=='ROLLED-BACK'and back['journal'].get('restored_order')==back['model_order'])
 check('verified automatic return leaves controller running without false blockers',back['pair']['phase']=='RUNNING'and back['status']['native_failover']['state']in('OBSERVING','ROLLED-BACK')and not back['status']['native_failover'].get('blockers'))
 report['verdict']='PASS'if all(c['passed']for c in report['checks'])else'FAIL'
except BaseException as e:report['verdict']='FAIL';report['error']={'type':type(e).__name__,'message':str(e)}
finally:out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='steps'},indent=2))
