"""Classify stdout from 00-platform-probe.sh; never connects to or writes a router."""
import json
from pathlib import Path
import re
import sys

PACKAGES=('python3','lua','lua-cjson','libuci-lua','ip-full','ubus','rpcd','luci-base','ca-bundle')
TOOLS=('opkg','apk','python3','lua','nft','ubus','rpcd','jsonfilter','sha256sum')
VENDOR_PATHS=('/usr/bin/rtp2.sh','/usr/bin/setup_instance_via.lua',
              '/lib/functions/vpn_func/route_policy_func.sh','/lib/functions/vpn_func/global_leak_drop.sh')
REQUIRED={'schema','board_name','model','gl_firmware','openwrt_target','openwrt_version','kernel',
          'architecture','python_version','lua_version','nft_version','package_architectures',
          'overlay_free_kib','memory_available_kib','bootloader_partition','bootloader_version',
          'recovery_backup','native_switch','installation'} | {'tool_'+x for x in TOOLS} | {
          'package_'+x for x in PACKAGES} | {'sha256:'+x for x in VENDOR_PATHS}

def classify(text):
    if len(text)>16384:raise ValueError('PLATFORM-REPORT-SIZE')
    rows={}
    for line in text.splitlines():
        if not line or line.count('\t')!=1:raise ValueError('PLATFORM-REPORT-FORMAT')
        key,value=line.split('\t')
        if key in rows or key not in REQUIRED or len(value)>180 or any(ord(c)<32 or ord(c)>126 for c in value):
            raise ValueError('PLATFORM-REPORT-FORMAT')
        rows[key]=value
    if rows.get('schema')!='1':raise ValueError('PLATFORM-REPORT-SCHEMA')
    reasons=[]
    if REQUIRED-rows.keys():reasons.append('OBSERVATIONS-MISSING')
    if rows.get('board_name')!='glinet,gl-mt3000':reasons.append('TEST-BOARD-NOT-VERIFIED')
    if not re.fullmatch(r'GL\.iNet GL-MT3000(?: \(Beryl AX\))?',rows.get('model','')):reasons.append('MODEL-NOT-VERIFIED')
    if not re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[-A-Za-z0-9.]*)',rows.get('gl_firmware','')):
        reasons.append('FIRMWARE-FAMILY-UNKNOWN')
    if rows.get('openwrt_target')!='mediatek/filogic':reasons.append('OPENWRT-TARGET-REQUIRES-REVIEW')
    if rows.get('tool_opkg')!='PRESENT' or rows.get('tool_apk')!='MISSING':reasons.append('PACKAGE-MANAGER-REQUIRES-REVIEW')
    if rows.get('architecture')!='aarch64':reasons.append('ARCHITECTURE-REQUIRES-REVIEW')
    for name in TOOLS:
        if name not in ('opkg','apk') and rows.get('tool_'+name)!='PRESENT':reasons.append('TOOL-MISSING:'+name)
    for name in PACKAGES:
        if rows.get('package_'+name)!='INSTALLED':reasons.append('DEPENDENCY-MISSING:'+name)
    for key,pattern in (('python_version',r'Python 3\.[0-9]+\.[0-9]+'),
                        ('lua_version',r'Lua 5\.[0-9]+\.[0-9]+(?: .*)?'),
                        ('nft_version',r'nftables v[0-9]+\.[0-9]+\.[0-9]+(?: .*)?'),
                        ('kernel',r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+A-Za-z0-9._]*)'),
                        ('openwrt_version',r'[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[-A-Za-z0-9._]*)')):
        if not re.fullmatch(pattern,rows.get(key,'')):reasons.append('VERSION-NOT-VERIFIED:'+key)
    if not re.search(r'(?:^|;)arch aarch64(?:_[A-Za-z0-9_-]+)? [0-9]+(?:;|$)',rows.get('package_architectures','')):
        reasons.append('PACKAGE-ARCHITECTURE-NOT-VERIFIED')
    if not rows.get('overlay_free_kib','').isdigit() or int(rows['overlay_free_kib'])<20480:
        reasons.append('STORAGE-NOT-VERIFIED')
    if not rows.get('memory_available_kib','').isdigit() or int(rows['memory_available_kib'])<=0:
        reasons.append('MEMORY-NOT-VERIFIED')
    for path in VENDOR_PATHS:
        if not re.fullmatch(r'[a-f0-9]{64}',rows.get('sha256:'+path,'')):reasons.append('VENDOR-HASH-NOT-OBSERVED:'+path)
    if rows.get('bootloader_partition') not in ('PRESENT','UNKNOWN') or rows.get('bootloader_version')!='UNKNOWN' or rows.get('recovery_backup')!='NOT_OBTAINED':
        reasons.append('RECOVERY-OBSERVATIONS-REQUIRE-REVIEW')
    if rows.get('native_switch')!='REFUSED_UNCERTIFIED_TARGET' or rows.get('installation')!='NOT_AUTHORIZED_BY_PROBE':
        reasons.append('AUTHORIZATION-MARKERS-INVALID')
    return {'result':'BLOCKED' if reasons else 'MONITOR-CANDIDATE-REVIEW',
            'blockers':reasons,'native_switch':'REFUSED_UNCERTIFIED_TARGET',
            'installation_authorized':False,'bootloader_verified':False,'backup_verified':False,
            'scope':'reported prerequisites only; no installation, device acceptance or adapter certification'}


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python scripts/classify-platform.py PRIVATE_PLATFORM.tsv')
    print(json.dumps(classify(Path(sys.argv[1]).read_text(encoding='utf-8')),indent=2))
