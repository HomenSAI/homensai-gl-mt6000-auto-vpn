#!/bin/sh
# Fresh monitor-only installation review for the observed stock MT3000 family.
# Read-only/stdout-only: never installs, enables a service, edits UCI or creates
# files. External encrypted backup/decryption receipt is reviewed on the PC.
# Usage: sh 00-mt3000-monitor-preflight.sh --backup-receipt-sha256 HOST_RECEIPT_SHA
LC_ALL=C
export LC_ALL
FAIL=0
pass() { printf 'PASS\t%s\n' "$1"; }
bad() { printf 'BLOCKED\t%s\n' "$1"; FAIL=1; }
installed() {
    awk '$1=="Status:" { seen++; if (NF==4 && $2=="install" && ($3=="ok" || $3=="user") && $4=="installed") valid++ }
         END { exit !(seen==1 && valid==1) }'
}
if [ "$#" -ne 2 ] || [ "$1" != --backup-receipt-sha256 ]; then
    bad EXTERNAL-BACKUP-REVIEW-REQUIRED
else
    case "$2" in ''|*[!0-9a-f]*) bad EXTERNAL-BACKUP-REVIEW-REQUIRED;;
        *) if [ "${#2}" -eq 64 ]; then printf 'EXTERNAL-REVIEW-CLAIM\t%s\n' "$2"; else bad EXTERNAL-BACKUP-REVIEW-REQUIRED; fi;;
    esac
fi
for tool in ubus jsonfilter opkg uci python3 lua ip nft sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || bad "TOOL-MISSING:$tool"
done
board=$(ubus call system board 2>/dev/null)
[ "$(printf '%s' "$board" | jsonfilter -e '@.board_name' 2>/dev/null)" = glinet,mt3000-snand ] || bad TEST-BOARD-NOT-VERIFIED
[ "$(printf '%s' "$board" | jsonfilter -e '@.model' 2>/dev/null)" = 'GL.iNet GL-MT3000' ] || bad MODEL-NOT-VERIFIED
[ "$(printf '%s' "$board" | jsonfilter -e '@.release.target' 2>/dev/null)" = mediatek/mt7981 ] || bad STOCK-TARGET-NOT-VERIFIED
[ "$(cat /etc/glversion 2>/dev/null)" = 4.11.0 ] || bad FIRMWARE-NOT-VERIFIED
[ "$(uname -m)" = aarch64 ] || bad ARCHITECTURE-NOT-VERIFIED
[ "$(uname -r)" = 5.4.211 ] || bad KERNEL-NOT-VERIFIED
opkg print-architecture 2>/dev/null | grep -Eq '^arch aarch64_cortex-a53 [0-9]+$' || bad PACKAGE-ARCHITECTURE-NOT-VERIFIED
for package in python3 lua lua-cjson libuci-lua ip-full ubus rpcd luci-base ca-bundle; do
    opkg status "$package" 2>/dev/null | installed || bad "DEPENDENCY-MISSING:$package"
done
[ "$(uci -q get homensai_vpn.main.monitor_only 2>/dev/null)" = 1 ] || bad MONITOR-ONLY-NOT-ARMED
[ "$(uci -q get homensai_vpn.main.enabled 2>/dev/null)" = 1 ] || bad MONITOR-NOT-ENABLED
case "$(uci -q get homensai_vpn.main.native_enabled 2>/dev/null)" in ''|0) ;; *) bad AUTO-MUST-BE-OFF;; esac
for option in native_until native_trial native_prepare_acceleration; do
    [ -z "$(uci -q get "homensai_vpn.main.$option" 2>/dev/null)" ] || bad NATIVE-SCOPE-PRESENT
done
pending=$(uci -q changes homensai_vpn 2>/dev/null)
[ "$?" -eq 0 ] && [ -z "$pending" ] || bad OWN-CONFIG-DELTA-UNVERIFIED
for path in /etc/homensai-vpn /var/run/homensai-vpn; do
    if [ -e "$path" ] || [ -L "$path" ]; then bad OWN-STATE-PRESENT-FRESH-INSTALL-ONLY; fi
done
if opkg status homensai-auto-vpn 2>/dev/null | installed; then bad OWN-PACKAGE-PRESENT-FRESH-INSTALL-ONLY; fi
tables=$(nft list tables 2>/dev/null)
if [ "$?" -ne 0 ]; then bad NFT-TABLES-UNVERIFIED
elif printf '%s\n' "$tables" | grep -Eq '^table inet homensai_vpn_(guard|fault)([[:space:]]|$)'; then bad OWN-NFT-TABLE-PRESENT
fi
free=$(df -k /overlay 2>/dev/null | awk 'NR==2 {print $4}')
case "$free" in ''|*[!0-9]*) bad STORAGE-NOT-VERIFIED;; *) [ "$free" -ge 20480 ] || bad STORAGE-TOO-LOW;; esac
if PYTHONDONTWRITEBYTECODE=1 python3 -B - 2>/dev/null <<'PYTHON_MONITOR_CHECK'
import sys
if sys.version_info<(3,9):raise SystemExit(1)
import fcntl,ssl,socket,json,subprocess,hashlib,ipaddress,datetime,pathlib,time
from concurrent.futures import ThreadPoolExecutor
if not callable(getattr(time,'tzset',None)):
    import ctypes
    if not hasattr(ctypes.CDLL(None),'tzset'):raise SystemExit(1)
if not hasattr(socket,'SO_BINDTODEVICE') or not hasattr(socket.socket,'setsockopt'):raise SystemExit(1)
if ssl.create_default_context().cert_store_stats().get('x509_ca',0)<=0:raise SystemExit(1)
for args in (['ip','-4','-j','rule','show'],['ip','-4','-j','route','show','table','main']):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
    if result.returncode or len(result.stdout)>2097152 or not isinstance(json.loads(result.stdout),list):raise SystemExit(1)
PYTHON_MONITOR_CHECK
then pass PYTHON-MONITOR-PREREQUISITES; else bad PYTHON-MONITOR-PREREQUISITES; fi
if lua - 2>/dev/null <<'LUA_MONITOR_CHECK'
if not _VERSION:match('^Lua 5%.1$') then os.exit(1) end
local uci=require('uci');local json=require('cjson')
if type(uci.cursor)~='function' or json.decode(json.encode({probe=true})).probe~=true then os.exit(1) end
LUA_MONITOR_CHECK
then pass LUA-MONITOR-PREREQUISITES; else bad LUA-MONITOR-PREREQUISITES; fi
printf 'NATIVE-SWITCH\tREFUSED-UNCERTIFIED-TARGET\nINSTALLATION\tNOT-AUTHORIZED-BY-PREFLIGHT\n'
if [ "$FAIL" -eq 0 ]; then pass MONITOR-CANDIDATE-REVIEW; else bad MONITOR-CANDIDATE-BLOCKED; fi
exit "$FAIL"
