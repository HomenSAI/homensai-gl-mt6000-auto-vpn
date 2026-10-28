"""Actual QEMU/OpenWrt5.4 FW3 rules and actual product kernel attestor.

Pinned synthetic policy is applied only to the marked disposable OpenWrt guest.
The private serial is not a physical router. Exact iptables-save and ip-full
JSON rule output are consumed by the production kernel-policy attestor.
"""
import hashlib,json,os,re,shlex,subprocess,sys
from pathlib import Path
from qa_config import REPO,OUT as OUTPUT_DIR
sys.path.insert(0,str(REPO/'router/tests'))
from test_kernel_policy import fixture
import kernel_policy
LABEL=os.environ.get('QA_LABEL','baseline')
OUT=OUTPUT_DIR/('qemu-kernel-'+LABEL+'.json')
report={'scope':'Real disposable OpenWrt21.02.7 x86/64 kernel5.4.238 + iptables1.8.7; synthetic FW3 pair; actual product kernel_policy.attest; not GL.iNet/RTP/hardware acceptance','cases':[],'kernel_policy_sha256':hashlib.sha256((REPO/'router/files/usr/lib/homensai-vpn/kernel_policy.py').read_bytes()).hexdigest(),'host_etc_readonly':bool(os.statvfs('/etc').f_flag&os.ST_RDONLY),'host_run_readonly':bool(os.statvfs('/run').f_flag&os.ST_RDONLY)}
BASE="test -e /tmp/HOMENSAI_VIRTUAL_LAB || exit 99; . /etc/openwrt_release; [ \"$DISTRIB_TARGET\" = x86/64 ] || exit 98; "

from qemu_serial import execute
def serial(command):return execute(command)
def install(mangle):
    text=shlex.quote(mangle)
    serial("printf '%s' "+text+" >/tmp/qa-mangle; iptables-restore </tmp/qa-mangle")
def readback():
    raw=serial("printf '\\nQA_MANGLE_BEGIN\\n'; iptables-save -t mangle; printf 'QA_MANGLE_END\\nQA_RULES_BEGIN\\n'; ip -4 -j rule show; printf 'QA_RULES_END\\n'")
    mangle=re.search(r'\nQA_MANGLE_BEGIN\n(.*?)QA_MANGLE_END\n',raw,re.S)[1]
    rule_text=re.search(r'\nQA_RULES_BEGIN\n(.*?)QA_RULES_END\n',raw,re.S)[1]
    rules=json.loads(rule_text)
    return mangle,rules,rule_text
def record(name,passed,**detail):
    report['cases'].append({'name':name,'passed':passed,**detail});OUT.write_text(json.dumps(report,indent=2))

try:
    serial('while ip rule del priority 6000 2>/dev/null; do :; done; ip rule add priority 6000 fwmark 0x1000/0xf000 table 1001; ip rule add priority 6000 fwmark 0xb000/0xf000 table 1012')
    for reserve in(False,True):
        policy,selection,mangle,_=fixture(reserve);install(mangle)
        actual,rules,text=readback();result=kernel_policy.attest(policy,selection,actual,rules)
        expected='target'if reserve else'source'
        record('actual-fw3-'+expected,result['verified']and result['role']==expected,proof=result,mangle=actual,ip_rule_text=text,parsed_ip_rules=rules)
    policy,selection,mangle,_=fixture()
    for name,changed in(
        ('wrong-mark',mangle.replace('--set-xmark 0x1000/0xf000','--set-xmark 0xb000/0xf000')),
        ('missing-lan-hook',mangle.replace('-A VPN_PREROUTING_HOOK -i br-lan -j ROUTE_POLICY\n','')),
        ('missing-prerouting-hook',mangle.replace('-A PREROUTING -j VPN_PREROUTING_HOOK\n','')),
        ('wrong-mark-mask',mangle.replace('--set-xmark 0x1000/0xf000','--set-xmark 0x1000/0xff00')),
        ('foreign-prerouting-override',mangle.replace('COMMIT','-A PREROUTING -j MARK --set-xmark 0xb000/0xf000\nCOMMIT')),
    ):
        install(changed);actual,rules,text=readback()
        try:kernel_policy.attest(policy,selection,actual,rules);record('refuse-'+name,False)
        except ValueError as error:record('refuse-'+name,str(error)=='KERNEL-POLICY-UNVERIFIED',code=str(error))
    install(mangle);serial('ip rule add priority 5000 blackhole')
    actual,rules,text=readback()
    try:kernel_policy.attest(policy,selection,actual,rules);record('refuse-prior-blackhole',False)
    except ValueError as error:record('refuse-prior-blackhole',str(error)=='KERNEL-POLICY-UNVERIFIED',code=str(error),ip_rule_text=text)
    serial('ip rule del priority 5000');actual,rules,_=readback()
    record('restored-graph',kernel_policy.attest(policy,selection,actual,rules)['verified'])
except BaseException as error:
    report['error']={'type':type(error).__name__,'message':str(error)};raise
finally:
    report['verdict']='PASS'if report['cases']and all(x['passed']for x in report['cases'])and'error'not in report else'FAIL'
    OUT.write_text(json.dumps(report,indent=2));print(json.dumps({'verdict':report['verdict'],'cases':len(report['cases']),'path':str(OUT),'error':report.get('error')},indent=2))
