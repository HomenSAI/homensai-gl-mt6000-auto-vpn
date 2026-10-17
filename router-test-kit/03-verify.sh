#!/bin/sh
# HomenSAI Auto VPN test kit, step 3: READ-ONLY post-install verification.
# Usage: sh 03-verify.sh            (add "wait" to give the monitor up to 90 s to produce a first sample)
KIT=/tmp/homensai-kit
EXPECTED_VERSION=0.8.0-alpha14
FAIL=0
ok()  { echo "PASS  $*"; }
bad() { echo "FAIL  $*"; FAIL=1; }

INST=$(opkg status homensai-auto-vpn 2>/dev/null | sed -n 's/^Version: //p')
[ "$INST" = "${EXPECTED_VERSION}-1" ] && ok "package $INST" || bad "package '$INST' (expected ${EXPECTED_VERSION}-1)"

if [ "$1" = "wait" ]; then
  i=0; while [ $i -lt 18 ] && [ ! -s /var/run/homensai-vpn/status.json ]; do sleep 5; i=$((i+1)); done
fi

ST=$(ubus call homensai-vpn status 2>/dev/null)
if [ -z "$ST" ]; then
  bad "ubus homensai-vpn status unavailable (rpcd not reloaded? try: /etc/init.d/rpcd reload; log out/in of LuCI)"
else
  V=$(echo "$ST" | jsonfilter -e '@.version')
  [ "$V" = "$EXPECTED_VERSION" ] && ok "running agent version $V" || bad "running agent '$V' (stale bytecode? see README troubleshooting)"
  ERR=$(echo "$ST" | jsonfilter -e '@.error')
  [ -z "$ERR" ] && ok "no service error" || bad "service error: $ERR"
  T=$(echo "$ST" | jsonfilter -e '@.time' | cut -d. -f1)
  NOW=$(date +%s)
  if [ -n "$T" ] && [ $((NOW - T)) -le 90 ] && [ $((NOW - T)) -ge -5 ]; then ok "status fresh ($((NOW - T)) s old)"; else bad "status not fresh (time=$T now=$NOW; router clock correct? monitor enabled?)"; fi
  echo "INFO  profiles seen: $(echo "$ST" | jsonfilter -e '@.profiles[*].id' | wc -l)"
  echo "INFO  auto_control: $(echo "$ST" | jsonfilter -e '@.auto_control.requested')"
  echo "INFO  native state: $(echo "$ST" | jsonfilter -e '@.native_failover.state')"
fi

[ "$(uci -q get homensai_vpn.main.native_enabled)" != "1" ] && ok "Auto (native_enabled) is OFF" || bad "native_enabled=1"
nft list table inet homensai_vpn_guard >/dev/null 2>&1 && bad "owned nft guard present" || ok "no owned nft guard"

N=$(ps w 2>/dev/null | grep -c '[h]omensai-vpn/agent.py daemon')
[ "$N" = "1" ] && ok "one monitor process" || bad "monitor processes: $N (enable in LuCI Settings -> Start monitor)"

if [ -f "$KIT/fingerprint.before" ]; then
  NOWFP=$( ( uci export network; uci export firewall; ip -4 route show table main ) 2>/dev/null | sha256sum | cut -d' ' -f1)
  [ "$NOWFP" = "$(cat "$KIT/fingerprint.before")" ] && ok "network/firewall/main-route fingerprint unchanged" || bad "protected fingerprint CHANGED (VPN reconnects can change routes; compare before blaming the package)"
else
  echo "WARN  no baseline fingerprint (run 01-preflight.sh before installing)"
fi
echo "== RESULT: $([ $FAIL -eq 0 ] && echo PASS || echo FAIL) =="
exit $FAIL
