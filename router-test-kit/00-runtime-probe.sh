#!/bin/sh
# Supplemental read-only/stdout-only facts. No install, cache refresh, service,
# interface, firewall, route, file creation, credentials or network requests.
# Run only on a deliberately selected test device; capture stdout on the PC.
LC_ALL=C
export LC_ALL
field() { printf '%s\t%s\n' "$1" "$(printf '%s' "$2" | tr '\t\r\n' '   ' | cut -c1-180)"; }
installed() {
    awk '$1=="Status:" { seen++; if (NF==4 && $2=="install" && ($3=="ok" || $3=="user") && $4=="installed") valid++ }
         END { exit !(seen==1 && valid==1) }'
}
field supplemental_schema 1
for tool in python3 lua opkg apk ip nft fw4 rpcd ubus uhttpd; do
    if command -v "$tool" >/dev/null 2>&1; then field "tool_$tool" PRESENT; else field "tool_$tool" MISSING; fi
done
if command -v opkg >/dev/null 2>&1; then
    for package in python3 python3-light python3-openssl python3-ctypes lua libuci-lua lua-cjson ip-full rpcd rpcd-mod-luci luci-base uhttpd ca-bundle firewall firewall4 nftables nftables-json kmod-nft-core; do
        status=$(opkg status "$package" 2>/dev/null)
        if printf '%s\n' "$status" | installed; then
            field "package_version:$package" "$(printf '%s\n' "$status" | sed -n 's/^Version: //p' | head -n 1)"
        else field "package_version:$package" MISSING; fi
    done
fi
if command -v python3 >/dev/null 2>&1; then
    PYTHONDONTWRITEBYTECODE=1 python3 -B - <<'PYTHON_RUNTIME_FACTS'
import sys
def field(key,value):
    print(key+'\t'+str(value))
field('python_runtime_version','.'.join(str(v) for v in sys.version_info[:3]))
for module in ('fcntl','ssl','socket','hashlib','json','subprocess','concurrent.futures','ipaddress','datetime','pathlib'):
    try:__import__(module);result='PRESENT'
    except Exception:result='MISSING'
    field('python_import:'+module,result)
try:
    import socket
    field('python_socket_binding_api','PRESENT' if hasattr(socket,'SO_BINDTODEVICE') and hasattr(socket.socket,'setsockopt') else 'MISSING')
except Exception:field('python_socket_binding_api','MISSING')
try:
    import ssl
    context=ssl.create_default_context()
    field('python_tls_ca_store','PRESENT' if context.cert_store_stats().get('x509_ca',0)>0 else 'EMPTY')
except Exception:field('python_tls_ca_store','UNVERIFIED')
try:
    {'a':1}|{'b':2}
    field('python_dictionary_union','PRESENT')
except Exception:field('python_dictionary_union','MISSING')
try:
    import time
    if callable(getattr(time,'tzset',None)):backend='NATIVE'
    else:
        import ctypes
        backend='CTYPES' if hasattr(ctypes.CDLL(None),'tzset') else 'MISSING'
    field('python_timezone_api',backend)
except Exception:field('python_timezone_api','MISSING')
try:
    import os
    field('process_privilege','ROOT' if os.geteuid()==0 else 'NON_ROOT')
except Exception:field('process_privilege','UNKNOWN')
try:
    import json,subprocess
    for name,args,expected in (
        ('ip_rules_json',['ip','-4','-j','rule','show'],list),
        ('ip_main_routes_json',['ip','-4','-j','route','show','table','main'],list),
        ('nft_tables_json',['nft','-j','list','tables'],dict)):
        try:
            result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
            valid=result.returncode==0 and len(result.stdout)<=2097152 and isinstance(json.loads(result.stdout),expected)
        except Exception:valid=False
        field(name,'READABLE' if valid else 'UNVERIFIED')
    try:
        result=subprocess.run(['ubus','list'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
        objects=result.stdout.decode('ascii','ignore').splitlines() if result.returncode==0 and len(result.stdout)<=262144 else []
    except Exception:objects=[]
    for name in ('session','file'):field('ubus_object:'+name,'PRESENT' if name in objects else 'UNVERIFIED')
except Exception:
    for name in ('ip_rules_json','ip_main_routes_json','nft_tables_json'):field(name,'UNVERIFIED')
    for name in ('session','file'):field('ubus_object:'+name,'UNVERIFIED')
PYTHON_RUNTIME_FACTS
else field python_runtime MISSING; fi
if command -v lua >/dev/null 2>&1; then
    lua - <<'LUA_RUNTIME_FACTS'
local function field(key,value) print(key..'\t'..value) end
local uci_ok,uci=pcall(require,'uci')
field('lua_uci_import',uci_ok and 'PRESENT' or 'MISSING')
field('lua_uci_cursor_api',uci_ok and type(uci.cursor)=='function' and 'PRESENT' or 'MISSING')
local json_ok,json=pcall(require,'cjson')
local roundtrip=false
if json_ok then
  local ok,value=pcall(function() return json.decode(json.encode({probe=true})).probe end)
  roundtrip=ok and value==true
end
field('lua_cjson_roundtrip',roundtrip and 'PRESENT' or 'MISSING')
LUA_RUNTIME_FACTS
else field lua_runtime MISSING; fi
field installation NOT_AUTHORIZED_BY_PROBE
field native_switch REFUSED_UNCERTIFIED_TARGET
field kernel_timeout_set_test NOT_PERFORMED
field network_policy_test NOT_PERFORMED
