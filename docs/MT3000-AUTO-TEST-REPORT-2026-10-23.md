# MT3000 automatic switching acceptance — 23 October 2026

## Scope and result

Dedicated GL-MT3000, firmware 4.11.0, two existing owner VPN profiles: WireGuard primary and OpenVPN reserve. This report covers router-originated IPv4 DNS/HTTPS and actual route-policy selection. The owner explicitly selected router-only verification. Windows networking and the primary MT6000 were not changed.

Installed candidate: **0.9.0-alpha37-1**, source `c477c5d041f93740e6ec0df65f84d77850b0f3b9`, 759490 bytes, SHA256 `c5f5d50ff29f789d0765380eaee33cd2647d9805ecbd8582aff263f1c1e60ee7`. Installation verified 84 immutable files and modes, with protected router configuration unchanged. Actual HTTPS-served JavaScript and CSS match the canonical package.

## Measured operation

The earlier alpha35 Auto session ran from 07:23:30 UTC until at least the final pre-Stop capture at 11:32:00 UTC: **4h08m30s session age**. This is controller session age, not continuous proof of end-client Internet availability. Retained pre-simulation observations cover about 67 minutes, 386 checks per profile: WireGuard had 32 failed checks across three observed episodes (1,30,1); OpenVPN had one isolated failed check. One unique spontaneous failover and later return occurred in that session. Repeated COMMITTED messages were the same transaction.

The separate instrumented alpha35 matrix ran **1162.72 seconds (19m23s)**, with 100 monitor samples and a maximum polling gap of 10.23 seconds:

| Scenario | Seconds | Confirmed reserve switches / returns | Result |
|---|---:|---:|---|
| Healthy baseline | 183.046 | 0 / 0 | PASS |
| Brief, eight-second primary failure | 54.551 | 0 / 0 | PASS |
| Reserve-only failure | 81.750 | 0 / 0 | PASS |
| Both paths failed | 92.013 | 0 / 0 | PASS |
| Primary failure and recovery, cycle 1 | 147.414 | 1 / 1 | PASS |
| Reserve also fails while primary is down | 174.882 | 1 / 1 | PASS; no unsafe return |
| Primary failure and recovery, cycle 3 | 138.347 | 1 / 1 | PASS |
| Rolling attempt limit | 106.569 | 0 / 0 | PASS; PAIR-RATE-LIMIT retained |
| Final stability | 184.035 | 0 / 0 | PASS |

Total: **three confirmed failovers, three returns, six scenarios without a switch**. Faults used unique owned nftables tables, kernel expiry, an independent cleanup process and final cleanup. All test tables were removed; attempt budgets were never reset to make a test pass.

After the upgrade, alpha37 Start passed in 56.07 seconds. Its actual primary-failure/return cycle passed in **133.01 seconds**. DNS and two HTTPS requests passed through each selected channel; distinct exits and actual before/after policy order were checked. Persisted counter deltas were exactly one automatic commit, zero manual commits and one confirmed return.

## Delivered interface and statistics

- Weekly controller/failure detail, compact calendar-month summaries and lifetime counters, with paginated JSON export. Failed checks, outage episodes, attempts, automatic/manual commits and confirmed returns are separate quantities.
- Seven-day detail expires; aggregate counters remain. Event-storm storage limits are explicit: 10000 events and 1 MiB failure / 2 MiB controller detail; truncation is reported rather than shown as a complete week. Routine observations follow the checkpoint interval, while incident edges request immediate checkpointing.
- A stored 24-hour route graph below the unchanged live graph. Pre-installation and unobserved periods remain unknown.
- Primary/reserve labels across designs and Channels. Green means selected healthy traffic; yellow means healthy standby; red means known off/failure; grey means unknown/stale. Connected tunnels alone do not prove selected traffic.
- Scroll position, expanded sections and error-table state survive redraws and are remembered per page/session. A smaller WAN/VPN selector, separate bordered manual card and visible confirmed 1 → 2 / 2 → 1 history badges are included.
- Manual primary/reserve commands during Auto share its Stop revision, budget and health fences. Successful manual choice holds the healthy channel; Resume returns control to Auto. Confirmed failure can release the hold for guarded recovery. Commands never create an external-LAN certificate.

## Verification and retained failures

Exact-source offline CI passed 717 application and 107 QA tests per Python runtime (3.11 and 3.9), plus 37 UI suites. Environment-specific skips are complementary: Lua checks run under 3.9; QA tooling checks run under 3.11. These are software checks, not additional physical-router tests.

Alpha36 installation testing exposed false outages for administratively disabled profiles. Alpha37 classifies them as off and skips those probes. The exact known pre-Start test window contained two false outages, 142 failed checks and 1501.62 summed profile-down seconds; original evidence is preserved. An initial one-time correction was overwritten by an exiting monitor and is retained as a failed durability check. A second correction waits for all own daemons to exit and verifies the persisted result after service startup. Real observed fault records and native transition history are not reset.

## Acceptance boundaries

Router-only automatic operation is the accepted scope. No independent LAN client, actual browser interaction, completed 24-hour traffic soak or physical power-cut test is claimed. Browser inventory had no connected surface; UI state behavior has automated tests and served-file verification only. A monitor/native restart or reboot requires a fresh explicit Start; unattended boot auto-resume is not implemented. Upstream OpenVPN AUTH_FAILED startup refusals remain a documented limitation; one also occurred during this final post-service-restart Start. The automatic startup safely cleaned up instead of falsely claiming readiness. Credentials were not changed to hide it.

The stock GL.iNet dashboard shows established tunnels and routing policies. Both tunnels may remain Connected while one carries the selected common traffic. Switching changes actual policy order; it need not disconnect the standby tunnel or rename Tunnel 1 / Tunnel 2. Exact stock-dashboard priority rendering was not browser-verified.

Machine-readable results: [QA evidence](../qa/MT3000-AUTO-MATRIX-2026-10-23.json). Previous crash/Stop tests: [recovery report](handoff/RECOVERY-2026-10-23.md). Statistics semantics and export: [retention documentation](STATISTICS-RETENTION.md).

## Post-upgrade manual and persistence acceptance

Actual manual test PASS in **181.84 seconds**: reserve selected, healthy manual hold lasted 90 seconds, primary restored, Resume returned to normal Auto observation. A real failed reserve was refused with PAIR-MANUAL-TARGET-UNHEALTHY; route order and rolling budget were unchanged. Exactly one manual commit and one return were counted, with zero automatic commits in this test and no certificate promotion.

Ordinary Stop PASS in 16.07 seconds, restoring both owned profiles off and removing the guard. After complete daemon quiescence, the known false alpha36 test records were corrected and verified after startup. A subsequent graceful application restart/persistence test PASS in **8.43 seconds**: all counters preserved, no switch replay, configurations unchanged, Auto safely off. Complete weekly controller export used three pages (271 events before / 272 after restart, including its status event); failure export used one page (eight events). Previously stored daily route intervals were preserved.

At that persistence checkpoint, retained controller lifetime totals were 19 attempts, 12 confirmed commits (11 automatic, one manual), seven rollbacks and two explicitly tracked confirmed returns. These include earlier sessions; they are not the totals of today's nine-case matrix. Return counting begins with the new counter version. Reliability since first new-model observation, after removal of the exact false test window, was 128 checks, 11 failed checks, four observed availability episodes, two recoveries and 115.58 summed profile-down seconds. Shutdown-transition episodes can close as DISABLED rather than RECOVERY; these quantities must not be described as four unexpected provider outages.

## Final handover

The first post-restart Start safely refused after upstream OpenVPN AUTH_FAILED (243.00-second observation/cleanup run). After a pause, unchanged-config retry PASS in **58.07 seconds**. Final active acceptance PASS in **37.42 seconds / seven observations**: Auto RUNNING/OBSERVING, main selected, no manual hold, both profiles pass DNS/two HTTPS probes, test fault tables absent. The normal VPN-only allow guard remains valid; it is not a temporary full-block fault. The first handover harness incorrectly required this guard to be absent and failed; its corrected read-only check passed. Both results remain in private evidence.

Across this expanded batch: **four automatic reserve commits, one manual reserve commit and five confirmed returns**, excluding the earlier spontaneous transition. Final retained lifetime totals remain 19 attempts, 12 commits (11 automatic / one manual) and two returns counted since the new return-counter version. Do not compare that two-return new-model total with older alpha35 returns as if they covered the same period. Reliability final checkpoint: 150 checks,16 failed checks,five observed episodes,two recoveries,167.90 summed profile-down seconds,633.37 seconds of adjacent fresh active-controller observations. This includes controlled faults, shutdown and the rejected startup, not just unexpected outages.

A final 189-entry supported configuration export was encrypted, DPAPI-decrypt/read verified and kept private. Complete tracked source and this report are saved to the owner-authorized Gitea feature branch; no private files, credentials or configuration backups are uploaded. No GitHub/main/tag update is claimed. Recovery bundle verification and restore check are retained privately.

**Auto is left ON.** Refresh the application with Ctrl+F5 to load the installed interface. It is usable now in the verified router-probed IPv4 scope. Remaining acceptance boundaries above prevent claiming fully unattended production readiness.
