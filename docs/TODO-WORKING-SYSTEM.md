# Working-system completion checklist

Updated 2026-10-15. Check a task only after its stated evidence exists. Laboratory tests do not replace device acceptance. The detailed chronology is WORKLOG.md; exact firmware/model details are TESTED-ENVIRONMENT.en.md.

## Completed with stated scope

- [x] Preserve original own settings and recover Internet after the experimental UCI-alias defect; verify cable DNS/HTTPS and original exit/order, keeping Wi-Fi available.
- [x] Verify disabled HNAT hook at runtime without forced unload or package removal. Loaded mtkhnat is not claimed unloaded.
- [x] Correct anonymous-section identity, retaining all semantic policy fields and rejecting duplicates/real changes. 90 Python tests and actual reorder/return passed.
- [x] Persist bounded checksummed controller history with previous-good backup, deduplication and monthly counters; exclude credentials, transaction tokens, exit IP and kernel logs.
- [x] Implement typed client-confirmation and Stop RPC, durable stop latch, trial nonce, bounded deadline/attempt count/cooldown and a separate supervisor.
- [x] Verify one live client-confirmed transition/return, one controlled-failure automatic transition and independent rollback between two already connected profiles.
- [x] Add source-bound cable probe routes while Wi-Fi stays default; temporary routes are removed on completion. This verifies selected IPv4 probes only.
- [x] Record exact failures, causes, changes, timestamps and limits; local Gitea precedes an identical GitHub snapshot.
- [x] Translate work log, diagnostic catalogue, changelog and QA reports into English. English report text is tested but awaits next package deployment.

## Device and production acceptance still required

- [ ] Prove shared coordination with GL.iNet writers/hotplug, not merely a private lock plus before/after fingerprints.
- [ ] Test actual executor-crash recovery and independent rollback on device. Physical power cuts require their own explicit test and must not be inferred from Docker child crashes.
- [ ] Validate IPv6 handling/leak protection with an independent client; current acceptance is IPv4 with router IPv6 disabled.
- [ ] Diagnose the final CLIENT-CABLE-NOT-LOCAL in the bounded observation window. Adapters being up does not establish the selected client route.
- [ ] Verify final helper completion after transient-network retry changes. Independent router rollback passed, but a previous helper exit was not successful.
- [ ] Define and validate unattended production operation; current mode is a bounded, client-confirmed experiment.

## Interface and configuration

- [ ] Finish left navigation, real-data cards/charts, version top right and author-logo website link; verify desktop/mobile layouts.
- [ ] Verify English default, optional Russian switching and reload persistence on the actual LuCI page. Diagnostics remain English in either locale.
- [ ] Add table sorting/search and visual card order based on actual policy/confirmed health: selected healthy first, failed last; green/red/pale-yellow/neutral states must not equate Connected with Internet availability.
- [ ] Complete system wizard: import existing profiles, names, supported priorities, supported mode/return settings, readiness summary and explicit start/stop workflow.
- [ ] Complete Telegram-channel wizard: private token entry, destination, bot send permissions, deliberate test delivery and reporting schedule. Never prefill or publish a stored token.
- [ ] Ship a bounded operator fault button with independent cleanup and test it end-to-end. A manually executed test script is not a completed product feature.
- [ ] Extend native selection to server/channel/protocol hierarchy only after adapters and tests support it; do not imply Wi-Fi is a VPN protocol.
- [ ] Probe inactive profiles safely without disturbing normal traffic; current native adapter only uses already connected profiles.

## Release

- [ ] Update compatibility passport and installation/AI prompts after actual device acceptance, retaining truthful limits.
- [ ] Run change-appropriate checks, privacy audit, reproducible build and real UI verification; publish local Git/Gitea first, exact GitHub snapshot second.
- [ ] Install the checked UI/reporting package after the active test window has completed; preserve current settings and recoverable state.


## Local / virtual increment — 2026-10-16

- [x] Real x86 OpenWrt guest in isolated Docker/QEMU, official image checksum verified.
- [x] Actual UCI/RPC/procd integration (14 checks), package update preserves own configuration; native Start refuses unsupported environment.
- [x] Own monitor process crash and replacement by procd; fresh measurements resume; network/firewall/main IPv4 route preserved. This is not native-executor or Internet recovery acceptance.
- [x] Monitor lifecycle RPC and Settings action; active/unknown/corrupt native recovery state blocks shutdown.
- [x] EN/RU switching and reload checked in a labelled synthetic browser fixture; mobile Overview width checked. Actual LuCI form acceptance remains open above.
- [x] Remove retired generated UI assets from IPK without deleting source history; normalize gzip OS header for matching observed Python 3.9/3.11 builds.
- [ ] VM warm-reboot acceptance: kernel-decompression hang retained as a failure; preserved-disk cold starts work. Do not infer router hardware reboot behavior.
- [ ] Native switching on real VPN tunnels and proprietary GL.iNet worker behavior remain device-specific open criteria.

Detailed evidence and limits: ../qa/OPENWRT-VIRTUAL-REPORT.md. Physical router untouched in this increment.
