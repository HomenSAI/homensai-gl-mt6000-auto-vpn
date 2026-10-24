#!/bin/sh
# HomenSAI Auto VPN test kit: emergency helper. Use ONLY if LAN clients lost internet after a native
# transaction (owned nft guard left closed) or the monitor misbehaves. Needs SSH/console to the router.
#   sh 05-emergency.sh show            read-only: guard, journal, current policy order
#   sh 05-emergency.sh stop-auto       stop own services, disable own Auto flag; managed rollback may restore policies/interfaces
#   sh 05-emergency.sh remove-guard    delete ONLY the owned nft table, after printing state
#   sh 05-emergency.sh start           start the own monitor and controller again
# Stop delegates managed restoration to the native controller. See EMERGENCY.md; verify the resulting route.
TABLE=homensai_vpn_guard
case "$1" in
show)
  echo "-- owned guard table:"; nft list table inet $TABLE 2>&1 | head -20
  echo "-- native status:"; cat /var/run/homensai-vpn/native-status.json 2>/dev/null | head -c 600; echo
  echo "-- journal (order before/after, phase):"
  sed 's/"sha256".*//' /etc/homensai-vpn/native-transaction.json 2>/dev/null | head -c 1500; echo
  echo "-- current route_policy section order:"
  uci show route_policy 2>/dev/null | grep -E "^route_policy\.[^.=]+=|\.via=|\.enabled=" | head -60
  ;;
start)
  /etc/init.d/homensai-vpn start && echo "own services started; Auto and connectivity still require separate confirmation"
  ;;
stop-auto)
  if ! /etc/init.d/homensai-vpn stop; then echo "STOP: service stop failed; saved Auto flag was not changed. Inspect managed recovery before retrying."; exit 1; fi
  if [ -n "$(uci -q changes homensai_vpn)" ]; then echo "STOP: own services stopped; pending homensai_vpn changes remain uncommitted. Resolve them before changing the saved Auto flag."; exit 1; fi
  uci set homensai_vpn.main.native_enabled=0 && uci commit homensai_vpn && echo "native_enabled=0 committed"
  ;;
close-journal)
  # Only for a stale journal after YOU restored the VPN rules by hand. Archives it, never deletes evidence.
  nft list table inet $TABLE >/dev/null 2>&1 && { echo "STOP: guard still present; run remove-guard first"; exit 1; }
  ps w | grep -q "[n]ative_switch.py daemon" && { echo "STOP: controller is running; run stop-auto first"; exit 1; }
  J=/etc/homensai-vpn/native-transaction.json
  [ -f "$J" ] || { echo "no journal"; exit 0; }
  A=/etc/homensai-vpn/native-transaction.closed-$(date +%Y%m%d-%H%M%S).json
  mv "$J" "$A" && echo "journal archived as $A (rule order must already be the original one)"
  ;;
remove-guard)
  nft list table inet $TABLE >/dev/null 2>&1 || { echo "no owned guard table"; exit 0; }
  nft list table inet $TABLE | grep -q homensai-owned-guard || { echo "STOP: table is not ours"; exit 1; }
  echo "Own services must be stopped first (sh 05-emergency.sh stop-auto) or the supervisor recreates the guard."
  /etc/init.d/homensai-vpn stop
  nft delete table inet $TABLE && echo "owned guard removed"
  echo "Verify: the VPN rule order equals the journal 'before' list (sh 05-emergency.sh show) and the LAN client has internet."
  ;;
*) echo "usage: sh 05-emergency.sh show|start|stop-auto|close-journal|remove-guard"; exit 2;;
esac
