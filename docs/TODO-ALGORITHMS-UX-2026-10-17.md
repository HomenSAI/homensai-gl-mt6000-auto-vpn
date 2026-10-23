<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Algorithm and interaction review - approval checklist

Created: 2026-10-17 08:41:20 Europe/Berlin.
Status: APPROVED FOR LOCAL EXECUTION on 2026-10-17. Local implementation and offline checks completed; physical deployment and hardware interruption testing remain excluded.

This is an addendum to TODO-NEXT-STAGE.md, not a replacement. Reuse verified implementations; audit and extend them rather than recreate completed offline mechanisms. Virtual success does not close hardware acceptance tasks.

| ID | Priority | Work | Acceptance / purpose | Scope |
| --- | --- | --- | --- | --- |
| UX-01 | P1 | Rename Probe now to Check VPN connectivity / Проверить доступность VPN. | State explicitly: DNS and HTTPS through connected profiles; no speed test or Auto enablement. | Local UI |
| UX-02 | P1 | Add a complete asynchronous check lifecycle. | Queued, Checking, Completed or Failed; correlate completion with the requested measurement, show result time and prevent duplicate submissions. Never display the previous snapshot as the new result. | UI + RPC contract |
| UX-03 | P1 | Strengthen the Auto start/stop control. | Large bright raised button; distinguish starting, enabled, stopping, rollback and unavailable. Confirm actual controller state; clarify that stopping Auto does not stop monitoring. | Local UI |
| UX-04 | P1 | Clarify the router VPN-settings shortcut. | Large clearly visible left-aligned action, labelled Open router VPN settings; correct router origin, explicit navigation icon and disabled state if destination unknown. | Local UI |
| UX-05 | P1 | Separate speed testing from health checking. | Large action only on the speed/ranking page; show quota and potential traffic impact, progress, cancel and actual result. Reuse existing speed workflow. | Local UI / existing service |
| UX-06 | P1 | Isolate deliberate fault simulation. | Diagnostics-only action named Simulate server failure; display target and expected impact, confirm intent and offer cancellation/restoration. Do not disguise it as normal disconnect. | Local UI; real execution gated |
| UX-07 | P1 | Separate server connection, health and traffic selection. | Explicit labels for connected, Internet verified, selected for traffic, inactive and unknown; no implication that connected means healthy. | Local UI |
| UX-08 | P1 | Keep visual ordering distinct from configured priority. | Active/healthy cards may move left without editing priority; display both, preserve keyboard focus and avoid moving a control under the pointer during a click. | Local UI |
| VIS-01 | P1 | Make primary buttons brighter and visibly raised. | Use existing HomenS.AI style tokens; stronger state colours, controlled gradient, bevel/shadow, visible hover/focus and pressed state. Avoid making every action equally prominent. | Local design |
| VIS-02 | P1 | Enlarge the green server lamp and increase brightness. | Proposed 16-18 px lamp; subtle radial highlight and outer shadow for volume. Gentle pulse for fresh verified health; reduced-motion support. Text/icon also identifies state. | Local design |
| VIS-03 | P1 | Define a consistent state palette. | Green: fresh confirmed health; yellow: pending/checking; red: failure or explicitly inactive with a distinct label; grey: disabled/unknown/stale. No green pulse from old evidence. | Local design |
| VIS-04 | P1 | Place large actions where they help. | Overview: Auto and VPN connectivity check. Channels: router VPN settings. Speed/ranking: start speed test. Wizards: one primary Continue/Apply action per step. Destructive actions remain visually separate. | Local design |
| VIS-05 | P1 | Validate accessibility, mobile and languages. | Readable contrast, keyboard/focus, practical touch targets and no colour-only meaning; English default and complete Russian labels/statuses. Bright controls must not obscure data. | Local QA |
| ALG-01 | P0 | Validate the native server -> channel -> protocol cascade. | Reuse tested model/executor contracts. Verify actual GL.iNet worker coordination, per-edge readiness, exhaustion, rollback and management access before hardware acceptance. | Offline audit + later hardware |
| ALG-02 | P0 | Refine failure diagnosis before selecting a reserve. | Distinguish WAN failure, DNS failure, tunnel failure, route mismatch and stale observations. Bound attempts; do not cycle all VPNs when the shared uplink is down. | Offline implementation/QA |
| ALG-03 | P0 | Validate reserve probes without transferring user traffic. | Reuse isolated probe adapter; verify bound DNS/HTTPS and expected exit, concurrency/time/byte limits and no main-route change. Real vendor integration needs separate evidence. | Offline + later hardware |
| ALG-04 | P1 | Audit and extend repeated-failure quarantine. | Increasing bounded retry delays for repeatedly failing servers, successful probation and explicit recovery; avoid starvation and stale quarantine across configuration changes. | Offline algorithm |
| ALG-05 | P1 | Explain each switch and refusal. | Show observed source failures, reserve successes, hierarchy/priority decision and next action; preserve time, codes and reasons in diagnostics without secrets. | Algorithm + UI |
| ALG-06 | P0 | Verify the actual LAN client path after a switch. | DNS, HTTPS and exit/path confirmation from a LAN witness; explicit confirmation timeout and rollback. Router-only success must not certify client connectivity. | Offline contracts + later hardware |
| ALG-07 | P0 | Audit existing anti-flapping and primary-return policies. | Reuse consecutive checks, cooldown, minimum dwell and stable-primary checks. Test clock jumps, stale samples, repeated reserves failing, manual override and Stop during every phase. | Offline QA + later hardware |
| QA-01 | P1 | Validate queued/failed/unavailable UI interactions. | RPC failure, stopped monitor, delayed completion, stale state, repeated click, navigation and refresh must not falsely show success. Test actual packaged assets. | Local QA |
| DOC-01 | P1 | Record results, limits and a new release candidate. | Timestamped English cause/correction/check entries; privacy scan, package asset verification, local Git -> verified Gitea. GitHub migration/release remains separately unresolved. | Local packaging/docs |

## Approval and execution boundary

- The user approved local execution of every row. Existing mechanisms are reused; hardware acceptance remains separate.
- First implementation group after approval: UX-01/02/03/04, VIS-01/02/03/04/05 and QA-01. Then algorithm audit and validated extensions.
- No automatic fallback to unencrypted WAN is introduced. Wi-Fi/Ethernet are uplinks; OpenVPN/WireGuard are VPN protocols.
- Do not publish provider profiles, addresses, credentials, Telegram tokens or private evidence.
- Physical deployment and interruption testing require a new explicit instruction. The user approved implementation; the standing no-router-deployment instruction remains in force.


## Execution record

See [alpha8 execution report](ALPHA8-UX-ALGORITHMS-RESULTS.md). Local scope completed; device acceptance rows remain pending rather than checked off as production-ready.

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


## Publication update - 17 October 2026

GitHub main publication was approved and independently verified at 5e9f23486e05fe7037624a404a905c9d615436b5. Canonical source a514afa482792a6d630831dd8a822a18962fe47e has the same tree. Existing public ancestry and historical tags are preserved; canonical history remains in Gitea. This supersedes earlier GitHub-blocked status statements. Product/hardware limitations are unchanged.
