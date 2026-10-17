# Alpha8 algorithm and UX execution report

Recorded: 2026-10-17T09:20:09.409763+02:00 Europe/Berlin.
Source tested: `aafdac37f0ed7a23364cd9f4f1e65bdefed32c91`.

The approved local implementation is complete within the statuses below. Rows requiring real vendor/LAN evidence remain explicitly blocked or pending; this report does not close physical acceptance. No physical router access, installation, route/firewall/VPN change or VM resumption occurred.

## Item-by-item result

| Item | Status | Evidence / remaining limit |
| --- | --- | --- |
| UX-01 | DONE LOCAL | Clear connectivity label and DNS/HTTPS scope. |
| UX-02 | DONE LOCAL | Request-correlated single-flight lifecycle, deadline, failure/empty counts; old snapshot cannot complete a new request. |
| UX-03 | DONE LOCAL | Bright confirmed Auto control; separate starting, switching, restoring and unknown states; unknown state cannot start Auto. |
| UX-04 | DONE LOCAL | Raised left-aligned router-settings action, explicit navigation and existing safe dynamic origin resolution. |
| UX-05 | DONE LOCAL | Separate large speed action; existing quota/review/cancel preserved. |
| UX-06 | DONE LOCAL; DEVICE PENDING | Diagnostics-only bounded failure action with target/review/cancel; no live execution this task. |
| UX-07 | DONE LOCAL | Connection, Internet health, traffic selection and configured priority are distinct labels. |
| UX-08 | DONE LOCAL | Copied visual sort does not edit priority; pointer-held redraw delayed and labelled keyboard focus restored. |
| VIS-01 | DONE LOCAL | Bright raised action gradients, shadows, hover/pressed/focus states using pinned Style palette. |
| VIS-02 | DONE LOCAL | 18 px computed lamp, radial highlight and glow; measured in browser. |
| VIS-03 | DONE LOCAL | Fresh healthy green, failure/inactive red with text, checking yellow, unknown grey; reduced-motion preserved. |
| VIS-04 | DONE LOCAL | Overview Auto/check, channels router setup, ranking speed, wizard primary actions; destructive action separately styled. |
| VIS-05 | DONE LOCAL | English/Russian section persistence, 414 px mobile nine-page overflow checks and desktop visual review. Blue text gradient min contrast 5.35:1; green power symbol min 3.49:1. |
| ALG-01 | OFFLINE PASS; HARDWARE BLOCKED | Existing cascade/executor contracts and lease/refusal tests pass. Real vendor arbitration/per-edge hardware proof not available and not bypassed. |
| ALG-02 | DONE LOCAL; HARDWARE PENDING | Fresh explicit configured-uplink down evidence suppresses cycling. Separate DNS/HTTPS/route/path/stale diagnoses; link-up is not Internet proof. |
| ALG-03 | OFFLINE PASS; HARDWARE BLOCKED | Existing CandidateSession/ProbeScheduler binding, budget, cancellation and route-isolation contracts verified by suite. Real vendor adapter remains gated. |
| ALG-04 | DONE MODEL; HARDWARE PENDING | Pure cascade failed-hop quarantine increases exponentially to 3600s cap, stronger probation, verified commit reset and backward-compatible journals. Not falsely claimed as native multi-hop production behavior. |
| ALG-05 | DONE LOCAL | Live-safe diagnosis and threshold explanation card; configured failure/success thresholds replace planner hardcoded counts. |
| ALG-06 | OFFLINE PASS; HARDWARE BLOCKED | LAN proof/transaction/timeouts/rollback contracts retained and tested. Actual LAN witness confirmation needs physical acceptance. |
| ALG-07 | OFFLINE PASS; HARDWARE PENDING | Existing cooldown/dwell/stable return and interruption tests pass; stronger failed-hop probation added. Real offload/vendor timing still unaccepted. |
| QA-01 | DONE LOCAL | 329 application tests/runtime, 30 QA tests/runtime, 12 UI suites; async race/expiry/corrupt state/RPC cases and mobile browser check. |
| DOC-01 | LOCAL/GITHUB SNAPSHOT READY | Alpha8-1 reproducible package and release notes, English work log and matrix. Local Git/Gitea first; GitHub main snapshot published; old historical tag collisions preserved without overwrite. |

## Verification

- Immutable dual-runtime CI: 329 application tests and 30 QA tests per runtime; 12 UI suites in the development image. Python 3.9/Lua zero skips; Python 3.11 control seven documented Lua skips. Both runtimes produced identical package bytes and passed source/nested-package privacy checks.
- Additional fault-model run: nine Python transaction/crash tests, seven Node transaction regressions and 200 cases / 1,737 assertions PASS. These are simulations, not power cuts or physical IPv6/worker proof.
- Browser: English/Russian switch preserved section, queued check could not show old result as complete, actual synthetic completion displayed checked/failed counts, failed RPC displayed unavailable with retry enabled. All nine Russian pages at 414x896 had no root horizontal overflow; check action appears only on Overview. Desktop 1280x900 measured 18px lamps and selected-first cards. Stored screenshot is explicitly synthetic, not a real router capture.
- New checks cover simultaneous enqueue, request expiry, late completion after replacement, corrupt state, empty/inactive profiles and result identity. Previous package UI references remain unchanged; selected menu/controller now both target dashboard38 and ui19.

## Candidate

`homensai-auto-vpn_0.7.0-alpha8-1_all.ipk`: 463,562 bytes.
SHA256: `da7f42716b3d35504be3f586a7ee1b18c8e75a8ec51c01e134dd24da3b182453`.
Local artifact: `releases/homensai-auto-vpn_0.7.0-alpha8-1_all.ipk`.
Receipt: `qa/ALPHA8-LOCAL-CI.json`; release notes: `releases/v0.7.0-alpha8.md`.

## Runtime contract

The `scan` RPC has no new user-controlled parameters. It returns `queued`, opaque `request_id`, `requested_at`, state and duplicate indication. `status.scan` tracks the exact request, and completion retains the matching published measurement identity/time plus checked/failed totals. A later background round cannot replace this manual result with an unrelated measurement. Completion means the measurement finished, not that every server is healthy. Empty results, RPC failure, stopped service, stale/overdue and superseded operations never certify success. Runtime request files stay under the owned runtime directory; no extra flash checkpointing or credentials are introduced.

## Remaining physical acceptance

Before any future installation/test: verify firmware/board and current routes, obtain a fresh backup, preserve a management/recovery path and independent client connection. Then test a separately certified source/reserve edge, real vendor arbitration, isolated reserve probes, transaction-bound LAN DNS/HTTPS/exit confirmation, rollback/Stop, and only then the whole hierarchy. Current mandatory guards and no-direct-WAN policy remain in place. Installation is not authorised by this offline completion report.

The older overnight protocol result remains valid for its exact producer and source; it is not an overnight soak of this new alpha8 application.


## Publication update - 17 October 2026

GitHub main publication was approved and independently verified at 5e9f23486e05fe7037624a404a905c9d615436b5. Canonical source a514afa482792a6d630831dd8a822a18962fe47e has the same tree. Existing public ancestry and historical tags are preserved; canonical history remains in Gitea. This supersedes earlier GitHub-blocked status statements. Product/hardware limitations are unchanged.
