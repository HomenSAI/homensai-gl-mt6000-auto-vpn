"""Actual controller must not replace a foreign mark in our disposable QEMU.

Run only after browser_end_to_end.js finishes, never concurrently with a route
scenario. The fixture is restored in finally; no host kernel is configured.
"""
import json,shlex,sys,urllib.request
from qa_config import OUT,HTTP_PORT,REPO
sys.path.insert(0,str(REPO/'router/files/usr/lib/homensai-vpn'))
from kernel_policy import parse_mangle
from qemu_serial import execute
base='http://127.0.0.1:%d/__qa/'%HTTP_PORT
report={'scope':'Actual pair_auto.tick and attestor refusal for a deliberately injected foreign PREROUTING mark in the marked disposable OpenWrt guest; no physical router','checks':[]}

def request(path,value=None):
    req=urllib.request.Request(base+path,data=json.dumps(value).encode()if value is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120)as result:return json.load(result)

def check(name,value):report['checks'].append({'name':name,'passed':bool(value)})

before=None
try:
    report['before']=request('state');before=execute('iptables-save -t mangle')
    report['original_iptables_save']=before
    execute('iptables -t mangle -A PREROUTING -j MARK --set-xmark 0xb000/0xf000')
    injected=execute('iptables-save -t mangle');report['injected_iptables_save']=injected
    injected_state=request('state');report['injected_kernel_proof']=injected_state['model_kernel']
    request('auto_tick',{'primary':'healthy'});after=request('state');report['blocked']=after
    raw=execute('iptables-save -t mangle');report['after_tick_iptables_save']=raw
    check('production attestor rejects actual foreign graph',after['model_kernel'].get('verified')is False and after['model_kernel'].get('repairable_missing')is False)
    check('actual Auto reports a kernel-policy blocker',after['status']['native_failover']['state']=='BLOCKED'and'KERNEL-POLICY-UNVERIFIED'in after['status']['native_failover'].get('blockers',[]))
    check('Auto never invokes the vendor apply adapter on foreign graph',len(after['kernel_applications'])==len(report['before']['kernel_applications']))
    check('Auto retains the foreign graph and kernel fingerprint unchanged',parse_mangle(injected)==parse_mangle(raw)and isinstance(after['model_kernel'].get('kernel_fingerprint'),str)and after['model_kernel']['kernel_fingerprint']==injected_state['model_kernel'].get('kernel_fingerprint'))
    check('Auto preserves attempt budget and UCI order',after['budget']==report['before']['budget']and after['model_order']==report['before']['model_order'])
except BaseException as error:report['error']={'type':type(error).__name__,'message':str(error)}
finally:
    if before is not None:
        execute("printf '%s' "+shlex.quote(before)+" >/tmp/qa-foreign-original; iptables-restore </tmp/qa-foreign-original")
        request('auto_tick',{'primary':'healthy'});restored=request('state');report['restored']=restored
        check('restored fixture resumes normal observation',restored['model_kernel'].get('verified')is True and restored['status']['native_failover']['state']=='OBSERVING'and restored['pair']['phase']=='RUNNING')
    report['verdict']='PASS'if'error'not in report and report['checks']and all(c['passed']for c in report['checks'])else'FAIL'
    (OUT/'auto-foreign-kernel-final.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k]for k in ('verdict','checks')},indent=2))
