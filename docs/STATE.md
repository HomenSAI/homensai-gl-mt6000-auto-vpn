# Project state - 17 October 2026

## Current release candidate

Alpha8-1, dashboard38 / ui19. Brighter raised actions, 18px health indicators, request-correlated manual checks with explicit empty/failure results, separate connection/health/selected states, failure diagnosis, configured-threshold explanations and adaptive failed-hop quarantine in the pure cascade model. English default, optional Russian.

Exact tested code snapshot: aafdac37f0ed7a23364cd9f4f1e65bdefed32c91. Final candidate/package snapshot 22b75b8500acc6bb13af302b0cbea0124f440a66 also passed immutable CI. 329 application and 30 QA tests per runtime, 12 UI suites; Python 3.9/Lua zero skips, Python 3.11 control seven Lua skips. Additional 200-case fault-model suite PASS. See ALPHA8-UX-ALGORITHMS-RESULTS.md.

## Physical device - historical, not rechecked

Last separately recorded hardware installation: alpha7-2, Auto OFF; no alpha8 installation or physical test occurred during this local/publication task. Device: GL.iNet GL-MT6000 / Flint 2, firmware 4.11.0, OpenWrt 21.02-SNAPSHOT r15812+1095-46b6ee7ffc, kernel 5.4.238. Complete environment evidence remains in TESTED-ENVIRONMENT.en.md and timestamped WORKLOG.

Earlier bounded transitions/rollback between two already-connected catchall profiles do not certify arbitrary multi-hop hierarchy, unattended production, real inactive-provider startup, IPv6 or hardware power recovery. Historical HTTP 403 and cable-path causes remain bounded by their actual evidence.

## Virtual evidence

Isolated OpenWrt 21.02.7 x86/64 VM installation/UCI/procd/package checks and later local protocol runs have separate evidence. Overnight protocol runs used four real local synthetic tunnels and a standalone namespace selector, not the GL.iNet native adapter and not alpha8's current source. Preserve all earlier FAIL/STOPPED records and unknown causes. See OVERNIGHT-TEST-REPORT-2026-10-17.md and PROTOCOL-SOAK-FINAL-2026-10-17.md.

## Remaining acceptance

Actual vendor worker arbitration, per-edge native hierarchy, isolated provider probes, transaction-bound LAN DNS/HTTPS/exit witness and real rollback/offload behavior need a new physical test window. Guards remain enabled. No direct-WAN fallback is introduced. Physical deployment remains separate from the user's approved GitHub main publication.

## Publication

The user approved GitHub main publication on 17 October 2026. Preserve existing public history using a reviewed canonical snapshot with GitHub main as parent, save locally/Gitea first, then normal non-forced push. Historical conflicting tags remain unchanged; public release mapping is separate. See PUBLICATION.md.
