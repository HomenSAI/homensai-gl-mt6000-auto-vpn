#!/bin/sh
# HomenSAI Auto VPN test kit, step 1: READ-ONLY preflight. Changes nothing on the router
# except writing files under /tmp/homensai-kit. Prints no keys, tokens or passwords.
# Run on the router:  sh 01-preflight.sh
KIT=/tmp/homensai-kit
mkdir -p "$KIT" && chmod 700 "$KIT"
OUT="$KIT/preflight.txt"
FAIL=0
say() { echo "$*" | tee -a "$OUT"; }
: > "$OUT"
ok()   { say "PASS  $*"; }
bad()  { say "FAIL  $*"; FAIL=1; }
warn() { say "WARN  $*"; }

say "== HomenSAI preflight $(date -u '+%Y-%m-%dT%H:%M:%SZ') (read-only) =="

# 1. Exact device identity (gate 1)
BOARD=$(ubus call system board 2>/dev/null)
NAME=$(echo "$BOARD" | jsonfilter -e '@.board_name' 2>/dev/null)
case "$NAME" in glinet,gl-mt6000|glinet,mt3000-snand) ok "board_name=$NAME";; *) bad "board_name='$NAME' (expected verified MT6000 or MT3000)";; esac
GLV=$(cat /etc/glversion 2>/dev/null | tr -d '\n')
[ "$GLV" = "4.11.0" ] && ok "GL.iNet firmware=$GLV" || bad "GL.iNet firmware='$GLV' (native controller pins 4.11.0; monitor still works)"
say "INFO  kernel=$(uname -r) openwrt=$(echo "$BOARD" | jsonfilter -e '@.release.description' 2>/dev/null)"
say "INFO  python3=$(python3 --version 2>&1) lua=$(lua -v 2>&1 | head -1)"

# 2. Currently installed application
INST=$(opkg status homensai-auto-vpn 2>/dev/null | sed -n 's/^Version: //p')
say "INFO  installed homensai-auto-vpn: ${INST:-none}"

# 3. Dependencies
for p in python3 lua lua-cjson libuci-lua ip-full ubus rpcd luci-base ca-bundle; do
  opkg status "$p" 2>/dev/null | grep -q '^Status:.*installed' && ok "dependency $p" || bad "dependency $p missing"
done

# 4. Storage / memory
FREE_KB=$(df -k /overlay 2>/dev/null | awk 'NR==2{print $4}')
[ -z "$FREE_KB" ] && FREE_KB=$(df -k /etc | awk 'NR==2{print $4}')
if [ "${FREE_KB:-0}" -ge 20480 ]; then ok "free writable storage ${FREE_KB} KiB"; else bad "free writable storage ${FREE_KB:-?} KiB (<20480)"; fi
say "INFO  MemAvailable=$(awk '/MemAvailable/{print $2" kB"}' /proc/meminfo)"

# 5. Vendor files pinned by the native controller (info only; Auto stays OFF in this kit)
check_hash() { # path expected
  if [ ! -f "$1" ]; then warn "vendor file missing: $1"; return; fi
  H=$(sha256sum "$1" | cut -d' ' -f1)
  [ "$H" = "$2" ] && ok "vendor hash $1" || warn "vendor hash differs: $1 (native switching would be blocked VENDOR-CODE-CHANGED)"
}
check_hash /usr/bin/rtp2.sh d6863630241e0bc68f56cc1eb8ccca45006083c1166e742e8500b28b5e2a544e
check_hash /usr/bin/setup_instance_via.lua d18e9659bed098ad3f381a921888429f8a50f314a21748eaa566db0d74ca37f8
check_hash /lib/functions/vpn_func/route_policy_func.sh 25a74cb70c609e3229a2f99ff2253171dc4ec3f491ffd2e140928f1b11f6c5a8
check_hash /lib/functions/vpn_func/global_leak_drop.sh b324ae48bd31190d7d00833c906e15a43a6f2bf10147eb892ac16fd594a71782

# 6. Acceleration / IPv6 (info)
say "INFO  mtkhnat.global.enable=$(uci -q get mtkhnat.global.enable) glipv6.globals.enabled=$(uci -q get glipv6.globals.enabled)"
say "INFO  flow_offloading: $(uci -q show firewall | grep -E 'flow_offloading' | tr '\n' ' ')"

# 7. Own configuration: non-secret native_* options only
if [ -f /etc/config/homensai_vpn ]; then
  for k in enabled monitor_only native_enabled native_until native_proof_scope native_order_direction; do
    say "INFO  homensai_vpn.main.$k=$(uci -q get homensai_vpn.main.$k)"
  done
  [ "$(uci -q get homensai_vpn.main.native_enabled)" = "1" ] && bad "native_enabled=1 (Auto must be OFF before installing)"
  [ -n "$(uci -q get homensai_vpn.main.native_prepare_acceleration)" ] && bad "native_prepare_acceleration is set (remove before installing)"
  [ -n "$(uci -q changes homensai_vpn)" ] && bad "pending uci changes for homensai_vpn (commit or revert deliberately first)"
fi

# 8. Controller / guard state
if nft list table inet homensai_vpn_guard >/dev/null 2>&1; then bad "owned nft guard table present: LAN forwarding may be blocked (see EMERGENCY.md)"; else ok "no owned nft guard table"; fi
if [ -f /etc/homensai-vpn/native-transaction.json ]; then
  PH=$(sed -n 's/.*"phase": *"\([A-Z-]*\)".*/\1/p' /etc/homensai-vpn/native-transaction.json | head -1)
  say "INFO  native journal phase=${PH:-unparsed}"
  case "$PH" in ARMED|APPLYING|WAIT-CLIENT|COMMITTED|HELD-ON-RESERVE|RESTORING) bad "active native journal phase $PH";; esac
fi
[ -f /var/run/homensai-vpn/native-status.json ] && say "INFO  native-status: $(sed -n 's/.*"state": *"\([A-Z-]*\)".*/\1/p' /var/run/homensai-vpn/native-status.json | head -1)"

# 9. Fingerprint of protected network state (hash only, nothing printed)
( uci export network; uci export firewall; ip -4 route show table main ) 2>/dev/null | sha256sum | cut -d' ' -f1 > "$KIT/fingerprint.before"
ok "protected fingerprint saved ($(cut -c1-12 "$KIT/fingerprint.before")...)"

say "== RESULT: $([ $FAIL -eq 0 ] && echo 'READY to continue' || echo 'NOT READY, fix FAIL lines') =="
say "Report: $OUT (contains no secrets; copy it to your PC to keep it)"
exit $FAIL
