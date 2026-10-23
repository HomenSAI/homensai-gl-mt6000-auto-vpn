<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../../docs/CURRENT-STATUS.md) · [documentation index](../../docs/DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Complete 50-item review backlog

Original proposal numbering is preserved. P0 = reliability/security; P1 = product completeness; P2 = optional usability. These are audit targets, not blanket implementation or device authorization.

For every item, Claude must replace the starting assessment with DONE / PARTIAL / NOT DONE / UNVERIFIED / BLOCKED and cite file+line, test and receipt. Distinguish a missing feature from an existing feature that needs broader verification.

| ID | Priority | Work | Acceptance | Starting assessment |
| --- | --- | --- | --- | --- |
| A01 | P0 | Finish the current 12-hour test | Full observations, gaps, failures and independent cleanup are verified. | STOPPED by owner; full-duration acceptance incomplete. |
| A02 | P0 | Analyze the long-test result | Every deviation has timestamp, known/unknown cause, correction and recheck. | Partial stopped-run evidence available; independent audit pending. |
| A03 | P0 | Crash the observer itself | Producer loss cannot become PASS; watchdog bounds and cleans the clone. | Normal/smoke/cooperative cleanup verified; abrupt-death cases need review. |
| A04 | P0 | Test Windows sleep/resume | Unobserved time is marked as a gap. | Not claimed complete. |
| A05 | P0 | Test Docker stop/restart | Old receipts cannot be mistaken for new completion. | Not claimed complete. |
| A06 | P0 | Expand interrupted-upgrade stages | Additional file/config/cache write points recover with the latest known package. | Three controlled alpha1-4 lifecycle stages PASS; broader alpha2 interruption coverage pending. |
| A07 | P0 | Clean/repeated install and uninstall | Only own files/services are affected; unrelated configuration survives. | Installation/reinstallation evidence exists; complete lifecycle matrix needs audit. |
| A08 | P0 | Cross-version data migrations | Supported upgrade/downgrade preserves statistics; unsupported formats refuse. | Existing migration/restore tests; full version matrix needs audit. |
| A09 | P0 | State mandatory algorithm invariants | Auto OFF never mutates routes; unknown health never means healthy. | Existing guard/model tests; formal coverage reconciliation pending. |
| A10 | P0 | Enumerate controller state transitions | No illegal transition or stranded intermediate state. | Existing native/cascade models and tests; completeness not certified. |
| A11 | P0 | Concurrent controls | Double Start, Stop during transition and parallel requests have one consistent outcome. | Existing lease/control/UI tests; additional race coverage to assess. |
| A12 | P0 | Lost RPC acknowledgement | An already executed operation is not repeated by retry. | Publication resume verified; router RPC/state reconciliation needs separate audit. |
| A13 | P0 | Prevent repeated switching on flapping health | Oscillating health cannot cause uncontrolled ping-pong. | Existing cooldown/dwell/quarantine logic; expanded scenarios proposed. |
| A14 | P1 | Temporary exclusion of unstable servers | Exclusion expiry, recheck and operator restore are understandable. | Existing pure-model quarantine; native integration and UI coverage need audit. |
| A15 | P0 | Verify return to primary | Stable evidence, including required DNS/HTTPS checks, precedes return. | Existing return/recovery tests; physical certification remains separate. |
| A16 | P1 | Fresh multi-reserve protocol run | Server -> channel -> protocol exhaustion/recovery is verified on current models and separate protocol lab. | Older protocol runs are different sources/standalone selector; fresh integration proposed. |
| A17 | P0 | Audit every RPC permission | Unauthorized users cannot read protected data or mutate settings. | Existing ACL/guards; comprehensive matrix audit pending. |
| A18 | P0 | Session expiry | UI requests login and never claims unconfirmed save success. | Existing UI/RPC handling; full actual expiry matrix needs audit. |
| A19 | P0 | Cross-origin requests | Unrelated pages cannot enable Auto or change config. | Existing protections; explicit adverse-request coverage needs audit. |
| A20 | P0 | Hostile names/error text | HTML, quotes and special characters remain inert text. | Existing escaping/XSS checks; expanded inputs proposed. |
| A21 | P0 | Malformed/oversized requests | Type, size, depth and bounds reject safely with meaningful errors. | Existing bounds; systematic randomized boundary coverage proposed. |
| A22 | P0 | Secret-leak coverage | No tokens/keys in RPC, exceptions, logs, CSV/HTML/PDF or packages. | Privacy scans and report tests PASS; expand formats/encodings and failure paths. |
| A23 | P1 | Telegram token lifecycle | Store/replace/delete safely; stored value never returns to browser. | Empty-field privacy/refusal verified; complete lifecycle needs fake-backend tests. |
| A24 | P1 | Application backup restore | Validate before apply; corrupt archives cannot alter current settings. | Existing backup tooling; end-to-end restore assessment pending. |
| A25 | P1 | Define all metrics | Failure, attempt, switch, recovery and efficiency have precise denominators. | Existing metrics and scope labels; consolidated specification audit proposed. |
| A26 | P1 | Separate operator and automatic events | Forced Stop does not distort natural-failure statistics. | Trial/automatic history distinctions exist; operator-event accounting needs audit. |
| A27 | P1 | Large retained histories | Months of events cannot cause unbounded memory/RPC growth. | Existing retention/compaction tests; large-data stress proposed. |
| A28 | P1 | Time discontinuities | Bad dates, loss of sync, DST and timezone changes remain truthful. | Backward/forward synthetic times and boundary tests exist; broaden real-environment cases. |
| A29 | P1 | Counter reset/reconnect | Interface recreation cannot invent negative or inflated traffic. | Existing accounting tests; full lifecycle matrix needs audit. |
| A30 | P1 | Trustworthy ranking | Show sample count, period/freshness; one lucky test is not absolute leadership. | Current ranking exists; statistical-confidence UX proposed. |
| A31 | P1 | Speed-test impact | Respect quota, concurrency and active-traffic skip limits. | Existing bounded speed tests; expanded contention and load verification proposed. |
| A32 | P1 | Monitor cost | Measure CPU/RAM/history size/write rate with explicit virtual scope. | Short RSS samples and stopped partial endurance available; CPU/write-rate study incomplete. |
| A33 | P1 | Full installed identity | Show app version, package revision and frontend build. | Agent version displayed; complete revision/build presentation needs audit. |
| A34 | P1 | Component mismatch diagnosis | Explain stale JS/CSS or partial upgrades. | LuCI cache invalidation fixed; explicit mismatch UI proposed. |
| A35 | P1 | Recognize persisted preset on reopen | Saved values matching Stability show that preset; edited values show Custom. | In-wizard selection/back/manual-edit fix PASS; saved-value recognition remains to assess. |
| A36 | P1 | Save with lost response | Resolve whether settings applied without duplicate dangerous writes. | Existing typed acknowledgement/pending UI tests; actual reconciliation needs review. |
| A37 | P1 | Fake Telegram API wizard matrix | Success/refusal/timeout/retry without real token or delivery. | Actual missing-token case and local tests exist; standalone fake API coverage proposed. |
| A38 | P1 | Event filters | Filter by server/channel/protocol/code/period/event type. | Assess existing filters and missing combinations before implementing. |
| A39 | P2 | Persist table preferences | Restore filters, sorting and period after reopening. | Some preference persistence exists; complete coverage needs audit. |
| A40 | P1 | Accessibility | Keyboard/focus/screen reader/contrast/color-independent states are usable. | Existing labels/focus checks; comprehensive accessibility review proposed. |
| A41 | P1 | Native browser zoom | Test real 125/150/200 percent zoom separately from viewport geometry. | Not certified; viewport-only matrix is not native zoom. |
| A42 | P2 | Transition presentation | Show source/candidate/phase/wait/outcome and honor reduced motion. | Current diagrams/animation exist; clarity and reduced-motion audit proposed. |
| A43 | P1 | Large printable reports | Long names/many incidents/page breaks/truncation are clear. | Single converted page PASS; native browser local-file Print blocked; large pagination unverified. |
| A44 | P1 | Additional virtual OpenWrt/LuCI compatibility | Publish measured matrix without declaring untested hardware supported. | Current x86 21.02.7 verified; extra platforms proposed. |
| A45 | P0 | Detect unrelated remote-repo edits | Detect changes absent from local primary before publication; reconcile first. | Mid-operation moved-main refusal exists; pre-prepare unrelated-change protection needs audit. |
| A46 | P1 | Release signing/provenance | Users verify author identity as well as checksum. | Checksums/download verification exist; cryptographic signing not claimed. |
| A47 | P1 | Package composition/dependencies | Components/licenses/minimum requirements/release deltas are explicit. | MIT/dependencies/package manifest exist; consolidated inventory audit proposed. |
| A48 | P1 | Matching SDK build automation | Recipe verified against exact vendor target/feed/toolchain provenance. | BLOCKED: exact matched vendor SDK not established. |
| A49 | P1 | Server-side Gitea CI stand | Prove restricted permissions/failing jobs on separate stand; production activation needs access. | Local isolated CI verified; main server-triggered activation BLOCKED/unverified. |
| A50 | P1 | User and AI-install documentation | EN/RU setup/secrets/update/recovery/diagnostics and future device trial guide are current. | Existing bilingual install/AI docs; release consistency and complete walkthrough audit pending. |

Recommended order: resolve applicable P0 findings, then P1; choose P2 by value. Optional UX work is not automatically a blocker for a bounded device validation trial.
A completed 12-hour pass is unavailable because the owner stopped the run. Decide whether a rerun is necessary for the proposed test scope; do not restart it automatically.
