"""Real UCI/rpcd/procd acceptance in an explicitly marked x86 OpenWrt VM.

Does not enable native VPN switching or send Telegram messages. Synthetic
profile metadata is used only to exercise the actual UCI writer.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time


def command(args,timeout=40):
    return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=timeout).decode()


def rpc(method,arguments=None):
    return json.loads(command(['ubus','-t','30','call','homensai-vpn',method,json.dumps(arguments or {})]))


def wait_until(check,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            result=check()
            if result:return result
        except (OSError,ValueError,subprocess.SubprocessError):pass
        time.sleep(1)
    raise AssertionError('bounded readiness wait expired')


def fingerprint():
    parts=[command(['uci','export',name]) for name in ('network','firewall')]
    parts.append(command(['ip','-4','route','show','table','main']))
    return hashlib.sha256('\n'.join(parts).encode()).hexdigest()


def main():
    release=Path('/etc/openwrt_release').read_text()
    if "DISTRIB_TARGET='x86/64'" not in release or not Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file():
        raise SystemExit('REFUSED: explicit x86 virtual lab required')
    checks=[]
    def test(name,check):
        check();checks.append({'name':name,'result':'PASS'})
    def expect(condition):
        if not condition:raise AssertionError('acceptance condition failed')
    baseline=fingerprint()
    test('actual-rpc-ready',lambda:wait_until(lambda:rpc('inventory')))
    test('actual-isolated-UCI-writer',lambda:expect(rpc('setup_check')['passed'] is True))
    test('fresh-monitor-default-off',lambda:expect(rpc('inventory')['settings']['enabled'] is False))
    test('uncertified-native-start-refused',lambda:expect(rpc('native_start')['accepted'] is False))
    test('speed-default-disabled',lambda:expect(rpc('speed_start')['code']=='SPEED-DISABLED'))
    test('invalid-Telegram-token-refused-without-send',lambda:expect(rpc('setup_telegram',{'token':'invalid','chat':'@example_channel','enabled':False,'interval':60})['saved'] is False))
    for config,section,kind in (('ovpnclient','1_1','client'),('wireguard','peer_2','peer')):
        path=Path('/etc/config')/config
        if not path.exists():path.write_text('')
        command(['uci','set',config+'.'+section+'='+kind]);command(['uci','set',config+'.'+section+'.name=VM fixture']);command(['uci','commit',config])
    args={'source':'openvpn:1_1','target':'wireguard:peer_2','interval':10,'duration':1,'session_loss':False,
          'servers':[{'profile':'openvpn:1_1','name':'VM primary','channel':'Main','priority':1,'enabled':True},
                     {'profile':'wireguard:peer_2','name':'VM reserve','channel':'Reserve','priority':2,'enabled':True}]}
    test('actual-system-metadata-save',lambda:expect(rpc('setup_system',args)['saved'] is True))
    test('metadata-save-does-not-enable-Auto',lambda:expect(rpc('inventory')['settings']['native_enabled'] is False))
    test('monitor-start-RPC',lambda:expect(rpc('monitor_control',{'enabled':True})['accepted'] is True))
    test('monitor-procd-running',lambda:wait_until(lambda:json.loads(command(['ubus','call','service','list','{"name":"homensai-vpn"}'])).get('homensai-vpn',{}).get('instances',{}).get('monitor',{}).get('running')))
    test('monitor-fresh-measurement',lambda:wait_until(lambda:rpc('status').get('time',0)>time.time()-35))
    test('monitor-stop-RPC',lambda:expect(rpc('monitor_control',{'enabled':False})['accepted'] is True))
    test('monitor-stop-confirmed-by-procd',lambda:wait_until(lambda:not json.loads(command(['ubus','call','service','list','{"name":"homensai-vpn"}'])).get('homensai-vpn',{}).get('instances',{})))
    test('network-firewall-main-route-preserved',lambda:expect(fingerprint()==baseline))
    result={'scope':'OpenWrt x86 QEMU in isolated Docker; real UCI/rpcd/procd, synthetic profile metadata',
            'time':time.time(),'checks':checks,'passed':len(checks),'vpn_switching_certified':False,
            'limits':['No GL.iNet proprietary workers','No real VPN server sessions','No GL-MT6000 hardware validation','No Telegram delivery attempted']}
    Path('/tmp/homensai-vm-acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
