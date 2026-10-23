# Active MT3000 fault matrix and statistics/UI batch — 23 October 2026

Owner requested continued real fault simulation, runtime/switch/no-switch reporting, seven-day detail/monthly/lifetime statistics, scroll/error reading preservation, a persistent 24-hour route chart, primary/reserve/standby labels, a separate manual panel, manual override during Auto, smaller WAN/VPN selection text and visible transition badges.

## Verified device baseline

Installed alpha35 remains running on the dedicated MT3000. Fresh initial read found the same session still RUNNING, roughly 2h55 after its earlier Start. Capture before upgrade at 10:41 UTC found session age 11893.32 seconds (3h18m13s). This is session age, not proof of every intervening minute of LAN availability.

Retained pre-simulation samples cover about 67 minutes: 386 checks per profile, primary WG 32 failed checks in three observed episodes (1,30,1), reserve OpenVPN one isolated failed check. Native history records one unique spontaneous APPLYING/COMMITTED transaction and subsequent RESTORING/OBSERVING during that session before this matrix. Repeated COMMITTED observations belong to the same attempt and must not be counted as multiple switches.

Actual alpha35 matrix completed PASS: 1162.72 seconds, 100 monitor samples, 9 scenarios, 3 verified reserve commits and 3 verified returns. No-switch cases: healthy baseline, 8-second primary fault, reserve-only failure, both paths failed, rolling attempt limit, final stability. One switching case also failed the reserve while primary was down and verified no unsafe return. All uniquely owned temporary fault tables were removed. Kernel timeouts and independent cleanup bounded every fault. External LAN remains excluded by the owner's answer.

Private evidence namespace: `private/auto-matrix-20261023T101626Z/`. A fresh 189-entry encrypted/decrypt-read-verified export was saved before the proposed upgrade. Primary MT6000 and Windows networking untouched.

## Unreleased alpha36 source checkpoint

Implemented statistics model and event-counter deduplication/migration; same-transaction COMMITTED oscillation is counted once. Weekly events, lifetime/monthly counters, read-only cursor export, outage/recovery immediate checkpoints and UI summary/download are present. A persistent 24-hour interval model and graph, route role/standby lamps, viewport preservation, error-table expansion, traffic font sizing, separated manual panel and controller transition badges were added after the first focused run.

Earlier focused statistics/native-history/agent/analytics checks passed. A later full application run passed 696 tests with 16 environment skips. UI checks ran until a missing root DISCLAIMER fixture in a reduced test archive; this is incomplete coverage, not full CI. New UI and day-history additions still need their own complete verification.

An earlier alpha36 build (749210 bytes, SHA d952a89c1608fa73e29e9bbf5d752da0842fe852f4600154449da07f596c0ecb) predates the newest UI changes and MUST NOT be installed. VERSION SHA remains a placeholder until the final source is frozen. There is no alpha36 hardware/release acceptance yet.

## Work still in progress

1. Implement fenced manual primary/reserve override plus explicit Resume Auto, sharing the rolling attempt budget and Stop revision. Preserve all legacy certificate/board guards; never enable an unsupported path.
2. Add/run meaningful day-history, viewport/error-state, role/standby, badge and manual concurrency/restart tests. Verify an actual browser across multiple 10-second redraws.
3. Regenerate the selected assets, freeze alpha36 fingerprint, canonical build/hash/install-kit pins and exact-source dual-runtime CI. Retain failed/incomplete runs.
4. Stop through the ordinary RPC, verify cleanup, install the exact accepted package with protected config/history preservation, verify every installed file and served UI asset.
5. Run fresh actual statistics/manual/fault tests; compare counter deltas with real confirmed transitions and verify persistence/export/restart. Leave requested Auto on after final acceptance.
6. Produce English durable evidence plus a Russian owner report with durations, scenarios, counts, refusal reasons and limits; save local Git/Gitea and a restore-verified checkpoint. No claim of external-LAN/MT6000/24h traffic-soak acceptance.
