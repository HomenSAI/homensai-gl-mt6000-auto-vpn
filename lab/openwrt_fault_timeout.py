"""Kernel timeout test in the disposable x86 OpenWrt VM, without any watchdog."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

if not Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file() or "DISTRIB_TARGET='x86/64'" not in Path('/etc/openwrt_release').read_text():raise SystemExit('REFUSED: marked x86 VM required')
sys.path.insert(0,'/usr/lib/homensai-vpn')
spec=importlib.util.spec_from_file_location('fault_under_test','/tmp/fault_control.py');fault=importlib.util.module_from_spec(spec);spec.loader.exec_module(fault)
def ping():return subprocess.run(['ping','-c','1','-W','1','127.0.0.1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=4).returncode==0
before=hashlib.sha256(subprocess.check_output(['uci','export','firewall'])).hexdigest()
assert ping(),'baseline loopback ping failed'
engine=fault.Nft();nonce=uuid.uuid4().hex;start=time.monotonic();result={}
try:
    engine.apply(['lo'],8,nonce)
    assert not ping(),'fault did not block loopback IPv4'
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if ping():break
        time.sleep(.5)
    else:raise AssertionError('kernel did not expire the fault without watchdog')
    assert before==hashlib.sha256(subprocess.check_output(['uci','export','firewall'])).hexdigest()
    result={'result':'PASS','scope':'Actual nftables ifname-set expiry in marked x86 VM; loopback test only','watchdog_running':False,'traffic_block_confirmed':True,'kernel_timeout_restored_traffic':True,'firewall_configuration_preserved':True,'elapsed_guest_seconds':round(time.monotonic()-start,2),'vpn_failover_tested':False}
finally:engine.cleanup(nonce)
assert engine.contents() is None
result['owned_table_removed']=True
Path('/tmp/homensai-kernel-fault-test.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
