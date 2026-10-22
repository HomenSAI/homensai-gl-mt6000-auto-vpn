# Alpha17 WIP checkpoint - 20 October 2026

Owner request: save all current statuses/TODOs and upload the current work to Git. This is an unfinished development checkpoint, not an alpha17 release or installation approval. The stable/public main release remains alpha16. Read this file before resuming implementation.

## Installed and published baseline

Alpha16 source `7e9b594193d206e0d6d722b67bd903ae5c3b9ec3`, public snapshot `ae00e444af5f324e2612687db58c141d18d5e64b`, tag `v0.9.0-alpha16`. Exact-source dual-runtime CI passed; the release IPK and checksum were downloaded and matched. Local Gitea and GitHub remote refs were independently verified. The portable GL-MT3000 has alpha16-1, dashboard67/ui44, monitor-only, Calm B default. Terms version1 is accepted by the owner; physical wizard Save remains incomplete. Both portable VPNs are saved disabled=1 after bounded testing; Auto/native/optional active functions remain off. No primary-router or Windows Wi-Fi changes.

Actual manual availability check on the installed alpha16 returned `RETURN-NOT-APPLICABLE`; no generic manual cross-channel operation exists there. Eight state checks passed with unchanged config and IPv4/IPv6 route/rule hashes. This is a negative availability check, not a completed channel transition. Existing WG/OpenVPN data checks and the bounded WG start/data/stop test remain separate evidence.

## Alpha17 development changes saved here

- New manual reserve/primary request RPC and explicit ACL; serialized revision-fenced RAM queue, no Auto enable and no UCI writes from the request handler.
- Supervisor dispatcher reuses the existing certified native transaction and actual LAN confirmation, distinguishes queue acceptance from completion, consumes the bounded attempt budget, correlates request/transaction IDs, and holds a completed manual reserve without automatic failback.
- Manual request recovery/Stop guards and optional native return revision fence; a known unconnected caller is listed below.
- Confirmed channel-path projection: only client-confirmed transaction + unchanged live policy order + fresh identity-bound measurement can select the active path. Queue acknowledgement never selects a channel.
- Shared A/B/C manual controls: selected working channel green, unused channel red with a separate 'not in use' label, verified transition yellow, stale/unknown grey. Colors swap only after confirmed path readback. A healthy unused channel is not reported as failed. Emergency Stop remains independent.
- Candidate page dashboard68 and stylesheet ui45 preserve Calm default, owner attribution and reduced-motion behavior.
- Separate read-only MT3000 manual-platform candidate collector/validator. It always reports not certified and never grants apply rights. It does not implement an MT3000 write adapter or bypass monitor-only/native platform guards.

No alpha17 IPK is release-approved, installed or published as a release. VERSION package SHA remains zero until a canonical final build; do not distribute an exploratory test build. Product source and tests are WIP.

## Validation status at freeze

| Check | Result and limit |
|---|---|
| Manual request module | 25/25 PASS on Python3.9 and3.11; isolated mocks, no device actions |
| Manual dispatcher | Latest focused12/12 PASS on both runtimes; later native-fence integration still needs regression coverage |
| MT3000 candidate validator | 11/11 PASS on both runtimes; no actual device preflight, no write adapter or certification |
| Channel path | Initial9/9 focused PASS; two later regression cases added and awaiting final rerun |
| UI | Two focused Node suites PASS, including200 path and864 traffic-light combinations; synthetic logic only |
| Owner attribution | Focused Node check PASS |
| Broad application run | FAILED exploratory mutable-source run:599 tests,4 failures,11 errors,15 skips. This is not exact-source CI. Failures involve new manual consumption touching unpatched `/var/run` in old supervisor fixtures and then masking expected existing refusal results. Package-staging emitted a faulthandler timeout diagnostic; the suite later terminated with failure, not a timeout PASS. |
| Frozen generated-page Edge DOM run | FAILED/INCOMPLETE:100s host deadline,0/6 DOM cases completed; readiness/completion UNKNOWN, no demonstrated product defect. Runner exited and owned Edge cleanup completed. Private result/source receipts retained. |
| Final full CI / canonical package | NOT DONE on this checkpoint |
| Actual manual channel transition | NOT DONE; MT3000 remains monitor-only and unsupported by the existing native apply adapter |

## Resume TODO, in order

1. Fix confirmed Stop race: `manual_dispatch.consume()` must pass `control_revision=record['control_revision']` into its `handle_return()` call. The optional native parameter exists, but the caller is not yet connected. Add a regression where Stop arrives during the source health check and prevents the requested return dispatch. Preserve trusted recovery behavior for existing callers.
2. Fix explicit runtime/persist wiring or avoid consuming an absent manual queue in the supervisor. New manual dispatch currently reaches `agent.RUNTIME` while older supervisor tests isolate `native_switch.RUNTIME`; do not weaken tests or suppress the original progress/expiry/Stop behavior. Rerun the failing supervisor/progress suites.
3. Test the native manual branch's Stop/crash boundaries: Stop after COMMITTED persistence, serialized HELD completion, supervisor restart before/after confirmation, no duplicate request replay, corrupted certificate, changed policy/identity, cancellation and shared attempt budget. Latest root code adds a control lock/revision check before HELD, but full acceptance is pending.
4. Rerun all focused path/manual/native suites, then all UI suites. Confirm final generated68 matches final source and inspect A/B/C at desktop/mobile sizes; retain all failed/incomplete browser receipts.
5. Add collector allowlist/deadline/failure regressions and execute the new MT3000 read-only preflight. Its candidate result must stay separate from actual apply permission.
6. Implement and independently review a real MT3000 manual transaction adapter before any route-write activation: exact vendor/firmware identity, valid FW3 runtime state, include reload=0, no existing vendor/firewall workers, exclusive own journal, independent cleanup, Stop fencing and verified rollback. Audited `rtp2.sh not_reload_network` outside an FW3 include is only a candidate primitive; it still changes DNS/firewall/conntrack. Do not remove board guards, fake LAN evidence, invoke inside FW3 restart, substitute direct ip-rule edits, or relabel interface startup as a route transition.
7. Prepare two actual distinct working channels and the selected source/reserve pair without overwriting the owner's unsaved wizard choices. Current device has both VPNs disabled and no app pair configured. An inactive OpenVPN start lifecycle has not been reviewed like the bounded WG lifecycle.
8. Owner scope currently permits router-only tests; no independent LAN client is available. Router-originated HTTPS/DNS does not certify client routing, IPv6, Kill Switch, special rules, acceleration or leak behavior. Do not enable persistent/native switching or green LAN claims on that evidence alone. Preserve Wi-Fi and primary GL-MT6000 isolation.
9. Once implementation is frozen, regenerate selected assets, record honest version/fingerprint, build canonical IPK, record its SHA and run exact-final-commit dual-runtime CI. Only a passing completed batch may become a release; a WIP backup branch is not release acceptance.
10. Save final reviewed source to Gitea, publish the approved reviewed snapshot/release, verify remote refs and downloaded assets, and create a restore-verified archive. D-copy remains pending the intended disk. Existing alpha16 archives are earlier checkpoints; keep WIP backups separate.

## Agent accounting at freeze

Three worker agents were used alongside root (four concurrent slots). Queue/backend:25 focused checks on two runtimes and12 dispatcher checks on two runtimes. UI:two focused Node suites, actual Edge fixture FAILED/INCOMPLETE (0/6,100s deadline), no DOM acceptance. Platform:11 focused checks on two runtimes. Workers made no router changes or publications. Their private receipts and raw evidence remain excluded from public Git source. The original stopped endurance observer remains STOPPED, not PASS.
