#!/bin/sh
# HomenSAI Auto VPN test kit, step 4 (optional): remove ONLY this application. Config/history are kept.
# Usage: sh 04-uninstall.sh
die() { echo "STOP: $*" >&2; exit 1; }
nft list table inet homensai_vpn_guard >/dev/null 2>&1 && die "owned nft guard present; see EMERGENCY.md first"
[ "$(uci -q get homensai_vpn.main.native_enabled)" = "1" ] && die "native_enabled=1; stop Auto first"
echo "removing homensai-auto-vpn only (shared dependencies are never removed)"
opkg remove homensai-auto-vpn
# opkg returns 0 even when the prerm guard refuses; check the real result.
if opkg status homensai-auto-vpn 2>/dev/null | grep -q '^Status:.*installed'; then
  echo "NOT REMOVED: the lifecycle guard refused (see message above). Nothing was forced."; exit 1
fi
echo "removed. /etc/config/homensai_vpn and /etc/homensai-vpn are kept intentionally."
echo "check: sh 03-verify.sh will now FAIL on package, which is expected."
