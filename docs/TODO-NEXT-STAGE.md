<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Full next-stage to-do, including additional features

Recorded at the user's request on 2026-10-16, Europe/Berlin.
Status: IN PROGRESS — implementation and evidence: [next-stage results](NEXT-STAGE-RESULTS.md).
Baseline: alpha6 offline completion; see [verified results](OFFLINE-COMPLETION.md) and [report](../qa/ALPHA6-LOCAL-REPORT.json).

This is the complete next-stage list discussed in chat. Completed alpha6 work remains completed; this file does not reopen it or certify production readiness. Tasks 16–20 are explicitly included additional features.

## Scope and priorities

- P0: safety and native-executor foundations. P1: integration, compatibility and usability. P2: further analysis/export/documentation.
- Tasks 01–20 can be developed/reviewed without the physical router. They do not authorize live route writes.
- The user has now instructed execution of the entire list. Virtual tasks 21–24 proceed only after an immutable checkpoint, in a separate isolated copy; preserve the originally paused guest and do not touch the physical router.
- Physical deployment, actual GL.iNet acceptance, public GitHub migration and destructive ref changes remain separately gated.
- Preserve English diagnostics/work logs, English-first UI with optional Russian, author/site attribution and private-token handling.

## A. Development and offline checks

- [x] **NEXT-01 — Native cascade adapter (P0).** Connect the tested pure model to a separate executor interface, with injectable backends and explicit capability/readiness checks. **Purpose:** prepare server -> channel -> protocol execution without treating a model intent as permission. **Done when:** mock integration covers the full cascade, exhaustion, root return and failed-hop rollback; live writes remain refused when vendor/client proof is absent. **Depends on:** 02, 03, 04; hardware acceptance remains separate.

- [x] **NEXT-02 — Per-edge certification (P0).** Store and validate a separate proof for each source/target edge, including profile identity, policy generation, metadata/recovery revision, deadline and exact transaction identity. **Purpose:** certification of one pair must not authorize a different transition. **Done when:** stale, changed, expired, mismatched and replayed proofs are refused by tests; certificates and public status expose no credentials. **Depends on:** [adapter contract](CASCADE-ADAPTER-CONTRACT.md).

- [x] **NEXT-03 — Persistent multi-hop journal (P0).** Retain the original root snapshot independently of each immediate pre-hop snapshot; atomically record prepare/apply/confirm/rollback and a previous-good recovery copy. **Purpose:** recover the correct level after several switches. **Done when:** every interrupted phase, missing/corrupt journal and changed external generation is tested; unknown state retains the guard and cannot overwrite an external policy. **Depends on:** 02, 06.

- [x] **NEXT-04 — Vendor arbitration implementation on test doubles (P0).** Implement the cooperative lease/adapter boundary for workers, hotplug and operator edits on mocked vendor APIs. **Purpose:** prepare genuine ownership rather than relying on a private PID lock. **Done when:** contention, lease loss and edits during apply/confirm/rollback are refused; the real vendor capability remains UNVERIFIED until device evidence exists. **Depends on:** adapter contract; do not impersonate vendor processes.

- [x] **NEXT-05 — Multi-transition LAN witness (P0).** Extend the helper to confirm DNS, HTTPS and expected exit for each transaction, bound to the intended client interface. **Purpose:** prevent Wi-Fi connectivity or an old acknowledgement from being mistaken for cable/VPN success. **Done when:** interface changes, stale acknowledgements, wrong exit, DNS failure, cancellation and multiple sequential transitions pass mocked integration tests. **Depends on:** 01–03; actual client-path acceptance is separate.

- [x] **NEXT-06 — Controller/executor restart matrix (P0).** Expand failure injection across preparation, applying, confirmation, committed reserve operation and restoration. **Purpose:** prove restart recovery without silently resuming Auto. **Done when:** simulated process death, delayed RPC, corrupt state and Stop at every phase preserve the root snapshot and end in an explicit verified stopped/held/blocked state. **Depends on:** 03; simulated crashes are not physical power-loss evidence.

- [x] **NEXT-07 — Inactive-profile adapter (P1).** Prepare start/stop/cancel/timeout logic for existing registered profiles using mocked supported APIs. **Purpose:** make currently inactive reserves usable without importing or exposing VPN keys. **Done when:** connecting, failed start, cancellation, profile removal and cleanup contracts pass; the live adapter remains blocked without route/DNS/vendor proof. **Depends on:** 01, 04, 06.

- [x] **NEXT-08 — Isolated reserve-probe execution (P1).** Prepare separate routing/mark/namespace boundaries and a bounded probe scheduler. **Purpose:** examine candidates without replacing the current traffic path. **Done when:** offline tests reject unproven bindings, enforce concurrency/byte/time limits, cancel cleanly and never change a host/default route. **Depends on:** 04, 07; actual network tests belong to 22–23.

- [x] **NEXT-09 — Exact runtime compatibility (P1).** Check new code against Python 3.9 and the documented Lua/CJSON/UCI interfaces, using compatible local runtimes where available. **Purpose:** close the gap between current development runtimes and the firmware environment. **Done when:** a versioned runtime matrix records PASS/FAIL/BLOCKED for all relevant tests; no system Python replacement or unsupported compatibility claim. **Depends on:** documented environment passport.

- [ ] **NEXT-10 — Full matching OpenWrt SDK build (P1).** Build through an SDK appropriate to the documented target, beyond the already passed payload-staging parity tests. **Purpose:** check the complete packaging path and dependency metadata. **Done when:** SDK provenance/version, build log, selected payload, modes, dependency metadata and artifact hashes are recorded; differences are explained. **Depends on:** 09; SDK availability is a prerequisite, not an assumed success.

- [x] **NEXT-11 — Configuration/statistics migrations (P1).** Add versioned upgrade/downgrade handling, including deleted/renamed profiles and rollback of an unsuccessful migration. **Purpose:** preserve names, priorities, history and secret fields without silently enabling Auto. **Done when:** old/current/partial/invalid fixtures round-trip or refuse safely, token fields remain private, and failed writes cannot be reported as saved. **Depends on:** 03, 09.

- [x] **NEXT-12 — Resource/load budgets (P1).** Measure CPU, RAM, retained journals and write frequency over prolonged offline runs at supported profile counts. **Purpose:** select explicit limits and avoid recovery loops or excessive flash writes. **Done when:** repeatable reports include workload, runtime, peaks, retention/compaction and enforced limits; host numbers are not presented as router benchmarks. **Depends on:** 01, 06, 08, 11.

- [ ] **NEXT-13 — Automated primary-Gitea checks (P1).** Prepare commit/PR-triggered tests, privacy audit and reproducible packaging around existing local tools. **Purpose:** reduce manual verification while keeping GitHub optional. **Done when:** a deliberately failing check blocks the pipeline, passing artifacts are traceable to exact source, runner permissions are limited and no router or secret-bearing job is executed. **Depends on:** 09–10; no duplicate recurring chat notifications.

- [x] **NEXT-14 — Gitea/GitHub reconciliation and metadata migration plan (P1).** Produce an exact ref-by-ref plan for both histories, conflicting tags and release descriptions/assets. **Purpose:** preserve original objects and avoid another independent copied-tree history. **Done when:** dry-run reports collisions and proposed preserved namespaces, migration/recovery steps and required approvals; no force/mirror push, deletion or tag overwrite. **Gate:** actual public publication requires separate explicit permission.

- [x] **NEXT-15 — Additional executor/recovery review (P0 before enablement).** Review the implementation independently of its passing tests and inspect the meaningful diff/PR. **Purpose:** find unsafe assumptions in ownership, rollback and proof handling. **Done when:** findings are classified, fixes/retests are recorded and unresolved blockers remain visible. **Depends on:** 01–06; review does not itself approve device deployment or unrelated-history merging.

## B. Additional features — included in the full plan

- [x] **NEXT-16 — Full path diagram (P1).** Extend Overview from the current pair diagram to protocol/channel/server groups, current route, next reserve and rejected candidates. **Purpose:** make the cascade understandable. **Done when:** selected/connecting/failed/unknown states and exclusion reasons match supplied evidence, model-only data is labelled, and EN/RU/mobile layouts pass. **Depends on:** 01–02; never infer the selected route from Connected alone.

- [x] **NEXT-17 — Transition detail/timeline (P1).** Show cause -> probes -> preparation -> apply -> client confirmation -> rollback/hold, with timestamps and English codes. **Purpose:** explain each attempt and its resolution. **Done when:** UI/export retain retry/outage identity, distinguish attempts from successful transitions and exclude tokens, session IDs and private configuration. **Depends on:** 03, 05–06.

- [x] **NEXT-18 — Recovery effectiveness aggregates (P2).** Add median/P95/worst recovery time, success ratio and repeated-failure summaries by server/channel/protocol and day/week/month. **Purpose:** compare operational quality rather than raw probe counts. **Done when:** denominators, observation coverage, unknown periods, sample age and overlapping categories are explicit and deterministic tests reconcile the totals. **Depends on:** 03, 17.

- [x] **NEXT-19 — CSV export (P2).** Export server ranking, traffic, failures and transitions for external comparison. **Purpose:** support spreadsheet analysis. **Done when:** UTF-8, separators, quotes/newlines, units/timezone and unknown values are tested; text cells cannot become spreadsheet formulas; no keys, tokens or sessions are exported. **Depends on:** 17–18 and existing privacy contract.

- [x] **NEXT-20 — Updated installation and AI-assisted guides (P1).** Extend EN/RU instructions and the continuation prompt for cascade configuration, upgrades, rollback and diagnostics. **Purpose:** make the next release installable in a guided, reviewable way. **Done when:** a fresh synthetic walkthrough follows the instructions, asks for private data only through appropriate local setup, distinguishes monitor/bounded/unsupported modes and does not claim unaccepted native operation. **Depends on:** 01–11 and verified release evidence.

## C. Virtual-network acceptance — isolated copy after the offline checkpoint

- [x] **NEXT-21 — Restore/resume VM and diagnose warm reboot (P0, VM gate).** Confirm cold recovery from the preserved disk and separately investigate the unresolved warm-reboot readiness failure. **Purpose:** restore a dependable acceptance environment. **Done when:** exact image/kernel/runtime, preserved settings, fresh monitor state and boot results are recorded; failed warm-boot reports are retained. **Gate:** explicit instruction to resume VM testing; do not treat reduced QEMU memory use as a reboot fix.

- [ ] **NEXT-22 — Local real-protocol tunnel matrix (P1, VM gate).** Start several isolated OpenVPN/WireGuard tunnel endpoints using synthetic local keys and controlled failures. **Purpose:** exercise actual protocol/network transitions without the physical router. **Done when:** same-channel, inter-channel, cross-protocol, reserve exhaustion, return and rollback paths are checked from an isolated client with separate evidence. **Depends on:** 01–08, 21; no user's production VPN credentials or host-LAN bridge.

- [ ] **NEXT-23 — Linux DNS/firewall/IPv6/conntrack behavior (P0 before hardware acceptance, VM gate).** Test path binding, leaks, DNS failure and scoped cleanup in a private virtual network. **Purpose:** go beyond Boolean/model outcomes. **Done when:** failure/recovery captures and unchanged management/host routing are demonstrated; generic Linux results are not presented as GL.iNet worker or hardware-offload proof. **Depends on:** 08, 21–22; host networking remains untouched.

- [ ] **NEXT-24 — Actual virtual UCI/package interruption tests (P1, VM gate).** Test installation, upgrade, rollback, failed/interrupted own-configuration writes and restoration. **Purpose:** verify real UCI/procd/package behavior after the new implementation. **Done when:** settings/history preservation, explicit failed-save results, rollback and clean restart are demonstrated with injected failures; simulation is not called a physical power cut. **Depends on:** 09–11, 21.

## Completion rules and suggested sequence

Suggested sequence: 02–04 -> 01, 05–06 -> 07–12 -> 15 -> 16–20, with 13–14 alongside; 21–24 only after their gate is explicitly opened.

Check a task only when its implementation and stated evidence exist. Record timestamp/timezone, observed error or gap, cause or uncertainty, correction, checks, limitations and local/Gitea commit. Preserve alpha6 and existing published tags. Add new release versions only at meaningful verified checkpoints.

Physical GL-MT6000 acceptance remains outside this list: vendor workers/hotplug, source-bound LAN path, actual DNS/Kill Switch, acceleration, inactive real profiles, IPv6, executor/power-loss recovery and unattended production must pass a separately authorized device matrix.


## Current execution boundaries

NEXT-01 through NEXT-09, NEXT-11/12 and NEXT-14 through NEXT-20 are completed in the documented offline/contract scope. NEXT-10 is BLOCKED on verified matching SDK provenance; see SDK-ACCEPTANCE.md. NEXT-13 has a local immutable-source CI launcher prepared; restricted automatic Gitea runner activation remains BLOCKED, see CI-PRIMARY.md. NEXT-21 through NEXT-24 are the next isolated virtual phase, not completed evidence. No physical deployment or GitHub write is authorised by this status.

NEXT-21 infrastructure acceptance: separate preserved-disk copy cold-boots and direct-kernel warm-boots successfully; see ../qa/alpha7-warm-reboot-baseline.json. Baseline installed application was alpha5. Original GRUB failure is not claimed fixed; alpha7 installation/reboot belongs to NEXT-24. Original guest remains paused.


## Pause checkpoint — 2026-10-16T17:26:04.3633100+02:00
NEXT-11 and NEXT-15 reopened: actual libuci pending-delta merge bug reproduced; unverified fix drafts retained outside package inputs. NEXT-24 partial (13 package and 11 UCI/procd checks passed, but pending-delta and alpha7 reboot/interruption acceptance unfinished). NEXT-22/23 not run. Earlier broad completion statements are superseded by docs/handoff/PAUSED-STATE-2026-10-16.md. Both guests paused; resume only after user instruction.



## UCI finding closed — 2026-10-16T17:46:34.8839610+02:00
NEXT-11/15 returned to complete within their offline/review scope: pending-delta correction verified by 301 application tests, 15 actual libuci/package checks, 11 UCI/procd checks, 13 rollback/reupgrade checks and alpha7-2 warm reboot. NEXT-24 remains partial; NEXT-22/23 remain outstanding. See UCI-FIX-RESULTS-2026-10-16.md and handoff/STATUS.md. No physical deployment.

