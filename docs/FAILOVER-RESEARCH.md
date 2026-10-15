# Failover and rollback research

Historical report for 0.3.0-alpha1. Later native acceptance and current limits: STATE.md and WORKLOG.md.

## Implementations studied

1. [mwan3, OpenWrt 21.02 source](https://github.com/openwrt/packages/blob/openwrt-21.02/net/mwan3/files/lib/mwan3/mwan3.sh): separate tables, fwmark/mask, ip rules and batched updates. Do not layer it over GL.iNet marks without conflict checks. The 21.02 source is closer to the target than 24.10 instructions.
2. [VPN Guardian architecture](https://github.com/Yakwilik/openwrt-vpn-guardian/blob/main/docs/architecture.md): preactivation validation, direct/protected traffic separation, local/bootstrap DNS separation, backup and runtime restoration after failed self-check. Its Xray/v2rayA/nftables environment differs; it was not installed and dnsmasq was not replaced.
3. [GL.iNet dashboard](https://docs.gl-inet.com/router/en/4/interface_guide/vpn_dashboard/): within-group fallback does not establish cross-group switching. Kill Switch may deliberately block traffic after a failure.
4. Earlier read-only firmware audit: tunnel-switch.sh uses PID/noclobber locks including a network-switch lock; hotplug invokes vendor failover-trigger. rtp2.sh rebuilds routes, DNS and firewall. clean_conntrack removes DNS state on port 53/service ports and invokes VPN conntrack cleanup; it is not scoped only to a selected client class. Vendor sources/raw dumps are excluded publicly. These are static findings, not proof about current running writers.

Mechanisms were studied; third-party code was not copied. An own flock does not coordinate vendor writers. Creating a vendor PID lock under an unrelated process is unsafe because its owner check may treat it as stale.

## Implemented in 0.3.0-alpha1

- Existing status RPC exposes failover_plan without adding methods or expanding ACL.
- LuCI selects existing source/reserve profiles. Planner defaults off and recommends only.
- Require three consecutive confirmed source failures and two fresh successful reserve HTTPS/DNS probes. Stale/future/duplicate/unknown samples do not qualify; inactive reserves are not started.
- Every plan remains applied=false, ready_to_apply=false, native_apply=false; a plan is not permission to switch.
- lab/transaction_engine.py implements an executable contract with locks, durable journal/fsync, deadline, ownership checks, rollback/recovery and injected adapter. It is a laboratory contract, not an installed GL.iNet driver.

## Proposed live transaction requirements at that stage

1. Verify exact firmware/profile schema, affected traffic, special policies and independent LAN management.
2. Establish actual vendor-writer coordination, own lock and configuration generation; do not arbitrarily stop vendor services.
3. Save a minimal private snapshot and durable intent; exclude VPN keys from public reports.
4. Arm an independent watchdog before closing only the affected forwarding class; preserve local management and Kill Switch.
5. Apply through an adapter with generation/ownership checks. Do not stop a shared VPN interface serving special policies.
6. Clean only a verified conntrack class/mask. Do not promise session preservation around a global flush.
7. Verify actual client IPv4 path, IPv6 or proven IPv6 blocking, client DNS, Kill Switch, management and special rules. Router-originated requests alone are insufficient.
8. Commit, reopen protected traffic and disarm watchdog only after checks. Restore only owned changes, preserve newer external edits and retain blocking after unverifiable rollback. Never call unknown connectivity restored.

## Historical blocking conditions

The 0.3.0-alpha1 release lacked a native adapter with verified writer coordination, watchdog, scoped DNS/conntrack, management path, special rules and IPv6. Unknown prerequisites blocked apply. Direct-WAN fallback stayed off. Real tests required an agreed interruption window and independent management/recovery. Changing exit IP can break sessions; rollback cannot restore already lost TCP/UDP sessions.

## Tests

36 monitor/package tests and 9 Python transaction-contract tests passed, including 200 synthetic combinations of stage failures, checks, external writers, journal errors, deadlines, apply/recover competition and corruption. Within the 200, 60 crash combinations use BaseException simulation, not router SIGKILL or power cuts. The older JS laboratory and actual Docker child crashes are separate evidence.

The first run found a late gate-opening defect after rollback/open/disarm failure. Reclosing the gate fixed it; if closure also cannot be verified, result is UNVERIFIED. Final tests passed.

## Historical device integration

0.3.0-alpha1-1 installed on the reference device with opkg exit 0. Status reported agent 0.3.0-alpha1, planner DISABLED and native_apply=false. Telegram remained enabled. A temporary UCI planner test did not finish normally; independent committed-inventory reads verified planner off and source/target unset, matching original settings. Enabled-planner device operation was not claimed. Recommendation selection was covered by fixtures. This stage made no VPN/route/firewall/DNS writes.
