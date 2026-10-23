<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../CURRENT-STATUS.md) · [documentation index](../DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Resume TODO - owner pause checkpoint, 20 October 2026

LATEST STOP21October: read [STOP-2026-10-21.md](STOP-2026-10-21.md) FIRST. Owner is rebooting the PC; new uncommitted fixes and test results are saved there. Ask the deferred Wi-Fi/gateway question only after the owner returns. No automatic resume.

Status: SAVED FOR THE NEXT OWNER-STARTED SESSION. The owner asked to record all remaining work, plans and design considerations, then continue after the next start. Do not resume implementation, agents, tests, router actions or old observers until the owner resumes. This document is the starting point; older documents retain their original scope and are not current readiness claims.

## 1. Exact saved state

- Installed/published stable version: alpha16-1, dashboard67/ui44, Calm B default. Source `7e9b594193d206e0d6d722b67bd903ae5c3b9ec3`; public main/tag snapshot `ae00e444af5f324e2612687db58c141d18d5e64b`.
- Unfinished alpha17 source checkpoint: `8febc9dfa1eb6b5e9d4eda54982ed01675e49c17`, Gitea branch `feature/checkpoint-alpha17-wip-20261020`.
- Reviewed public WIP snapshot: `9a7ab758135132c761da2973206f0be809b4d06d`, GitHub branch `backup/alpha17-wip-20261020`. Its source tree equals the source checkpoint; no private local history was uploaded. Remote branch refs were checked. No alpha17 release/tag/IPK was published. Main remains alpha16.
- This resume document is a later local documentation update. Do not claim it is on the remote merely because checkpoint8febc9d was uploaded; verify the actual remote SHA if asked to upload the new document.
- Alpha17 candidate sources include dashboard68/ui45 and manual controls, but the candidate is NOT installed, fully tested, packaged for release or hardware-certified. VERSION package SHA is a placeholder. No manual channel transition on MT3000 has passed.
- Last verified portable state: GL-MT3000, `glinet,mt3000-snand`, GL4.11.0/OpenWrt21.02-SNAPSHOT, mediatek/mt7981, kernel5.4.211. Monitor-only; native/Auto/planning/speed/Telegram off. Both selected WG/OpenVPN clients saved disabled=1; original stock VPN startup link restored. Owner terms1 accepted; physical first-run wizard Save still incomplete. These are last observations, not a new live read.
- Primary GL-MT6000 and PC Wi-Fi are excluded from changes. Portable access is cable-only. No Windows NIC/address/default-route edits. User currently allows router-only testing; no independent LAN client is available.
- Workers are frozen and reported no owned running jobs after final cleanup. Original stopped endurance observer stays STOPPED, not PASS; do not restart old namespaces/disks.

Detailed implementation/evidence: [alpha17 checkpoint](ALPHA17-WIP-CHECKPOINT-2026-10-20.md), [physical router-only evidence](../PHYSICAL-ROUTER-ONLY-2026-10-20.md). Private current state: `private/portable-router-access-2026-10-20/CURRENT.local.json`, `ALPHA17-WIP-STATE.local.json` and `FINAL-STATE.local.md`.

## 2. First actions after the owner resumes

1. Read this file, CLAUDE.md, the alpha17 checkpoint, actual branch/HEAD/status and private current receipts. Preserve newer owner edits. Do not overwrite WIP with alpha16 or assume the public snapshot SHA is the local source SHA.
2. Confirm there is no old test/executor/cleanup job. Reuse available agents with disjoint file ownership; maximum four concurrent including root, so the requested five roles must run in waves. Report files/tests/results, never invented memory or token statistics.
3. Recheck cable identity, host Wi-Fi gateway, actual portable board/firmware/version and protected state before physical work. Reuse the pinned, source-bound, DPAPI-key management helper. Do not print credentials, raw profile configs or keys. Do not reuse old PIDs, transaction IDs or cleanup commands.
4. Continue with the software P0 fixes below. Do not start by activating VPNs, clearing journals, enabling native mode, completing the owner's wizard or changing acceleration.

## 3. P0 - finish manual control integration

- [ ] **Connect the missing return fence.** In `manual_dispatch.consume()`, pass `control_revision=record['control_revision']` to `handle_return()`. Root added the optional native parameter and checks it after the source health probe; the caller is still missing it. Test Stop arriving during that probe, before any requested route write. Existing trusted recovery callers keep their default recovery behavior.
- [ ] **Fix runtime/persistence ownership.** New consumption reads `agent.RUNTIME` while older supervisor tests isolate `native_switch.RUNTIME`. It reaches real `/var/run`, then masks existing progress/Stop/expiry behavior. Pass paths explicitly or skip consumption when no manual queue exists, with equivalent isolation for recovery. Do not weaken old tests or catch the failure and pretend it passed.
- [ ] **Recheck the final manual commit boundary.** Stop after COMMITTED persistence must not produce an unverified HELD success. Root added a control lock + revision check before HELD. Add meaningful regressions for Stop on both sides of that boundary and verify the intended linear order.
- [ ] **Test restart/crash states.** QUEUED/CLAIMED/APPLYING/WAIT-CLIENT/COMMITTED/HELD/RESTORING: no duplicate execution, no replay after process death, correct rollback/hold, no permanently busy stale queue after Stop. Interrupted progress must be explicit UNCONFIRMED/REFUSED/CANCELLED, never inferred success.
- [ ] **Retain all fences at actual dispatch.** Revalidate source/target, policy hash, settings hash, vendor generation, certificate, deadline, Stop revision and shared attempt budget immediately before forward work. Changed external policy must never be overwritten on rollback. A queued acknowledgement is not a transition.
- [ ] **Correlate primary completion.** Keep request timestamp, transaction ID, RETURNED result, restored live order and journal phase checks. A previous `ok:true` result must not complete a new request. Keep recovery available after the old native trial lease expires.
- [ ] **Keep manual separate from Auto.** One manual command means one transition, not enabling Auto or automatic failback. Preserve Emergency Stop independently of UI/RPC busy flags. A successful manual reserve hold must not rewrite a LAN certificate or become automatic mode silently.
- [ ] **Validate path projection defensively.** Check actual live order, client-confirmed journal, matching identity/generation, fresh monitor/controller/profile data and matching transition state/transaction. Unknown, malformed, future/stale or unrelated state cannot choose a green route. Two newly added path regressions await the final rerun.

Exploratory broad run was FAILED:599 total,4 failures,11 errors,15 skips, on mutable sources. Final immutable-source CI has not run. Focused passes: manual queue25 and dispatcher12 on Python3.9/3.11; initial path9; platform validator11 on both runtimes; two UI Node suites. These scopes are not full acceptance.

## 4. User-visible colors and controls

- [ ] Finish and inspect A/B/C manual reserve/primary controls and confirmed path colors, including no selected pair, missing/stale controller, RPC refusal/lost acknowledgement, repeated clicks, Stop while busy and late polling replies.
- [ ] Selected path with fresh confirmed connectivity: green. Other unused path: red with explicit 'not in use'; healthy standby must not be called broken. Confirmed failed path: red with the actual failure. A real transition: yellow. Unknown/stale/unverified path: grey.
- [ ] After a confirmed transition, green/red swap according to the actual route; never swap optimistically on click or a queue acknowledgement. Health lamps and traffic-selection labels must remain distinct.
- [ ] Preserve Calm B first-load default; explicit saved A/C/browser/router preferences remain respected. Keep attribution/version/package/page/style identity on every page and gentle lamp blinking; reduced-motion stays still.
- [ ] Fix/re-run the generated-page Edge harness:100s host deadline,0/6 completed, FAIL/INCOMPLETE, no established DOM acceptance. Diagnose readiness/completion/cleanup using the frozen run evidence; do not assume a product defect or just increase deadlines and relabel the old attempt PASS. Test A/B/C at mobile/desktop sizes, EN/RU, keyboard/focus, overflow and saved settings.
- [ ] Verify actual native125/150/200% browser zoom separately from viewport/CSS equivalence, plus accessibility and color-independent labels.

Browser evidence: `private/manual-ui-alpha17-browser/result.json`, `source.json`, `run.py`. Runner exited; owned Edge cleanup completed. No new tests are running.

## 5. Real MT3000 adapter - substantial unfinished work

- [ ] Finish read-only candidate collector regressions: allowlisted output/no secrets, global deadline across subprocesses, failed/oversized/malformed reads, duplicate/ambiguous bindings, clock changes, busy workers, unknown locks and FW3 state parsing. Execute actual read-only preflight only after the owner resumes and device identity is refreshed.
- [ ] Implement an actual MT3000 manual transaction adapter with its own reviewed deployment/capability boundary. `mt3000_manual_platform.py` currently only reports readiness candidates; it always refuses apply and is not a write adapter. Do not bypass `monitor_only=1` or the MT6000 native board guard.
- [ ] Require exact firmware/vendor hashes, complete FW3 runtime state, include reload=0, known policy shape, no existing FW3/vendor/hotplug/lock backlog, bounded RAM/work queues and exclusive transaction ownership. Private locks and pre/post hashes alone do not prove cooperation with GL.iNet writers.
- [ ] Candidate apply primitive to investigate: audited `rtp2.sh not_reload_network` invoked OUTSIDE an FW3 include or held firewall lock. It still changes DNS/firewall/conntrack; it is not firewall-free and is not yet an accepted adapter. Normal reload with missing FW3 state can fall back to start and re-enter the include. Never invoke this blindly to make a demo work.
- [ ] Before any forward write, arm independent cleanup, durably capture exact original policy/order and profile identity, fence children against late commits, preserve management INPUT access, bound apply/rollback time and memory, and pin only owned process identities. Never kill arbitrary vendor writers, unlink locks, flush the firewall or use stale recovery PIDs.
- [ ] Verify rollback and any LAN guard through the actual kernel, including cleanup actor/SSH/foreground loss. Existing isolated19-check WG harness evidence is not a physical process-loss or native adapter proof.
- [ ] Prepare two distinct existing working channels and the app's source/reserve selection without overwriting the owner's unsaved wizard choices. Current saved clients are both off; application pair is unconfigured. WG activation was bounded and verified, but an inactive OpenVPN activation lifecycle still needs its own reviewed start/stop/cancel/timeout path.
- [ ] Test manual source->reserve, reserve->source and failed target with explicit expected outcome, bound DNS/HTTPS/exit and policy readback, cancellation/Stop at every phase, unavailable WAN, external edits and failed rollback. Do not substitute interface startup or router-local probes for a client traffic transition.
- [ ] **External prerequisite:** a separate LAN client is needed to certify client DNS/HTTPS/exit, IPv6, Kill Switch, special rules and acceleration. Owner currently chose router-only tests. Continue useful software/read-only work, but do not forge a LAN acknowledgement, redirect the working PC Wi-Fi or silently change its routes.

## 6. Firmware defects, recovery and monitoring

- [ ] Permanent stock FW3 restart recursion/deadlock repair remains OPEN. Earlier bounded process recovery is complete, but no vendor patch was accepted. Helper-only candidate had a counterexample; do not install it or describe normal reload=0 as unconditional permanent recursion.
- [ ] Review/test latent IPv4 global DNAT ACCEPT ordering before MAC-block/zone checks. Recorded snapshots had no DNAT entries, so no currently reachable leak was demonstrated. Keep future DNAT/MAC-block behavior open; no broad policy-equivalence claim.
- [ ] Verify acceleration state/runtime and conntrack effects with the supported adapter. Loaded module is not proof of acceleration being disabled; do not force-unload drivers or alter PC networking.
- [ ] Observe firmware-owned server changes within each tunnel: current member, generation, reason if actually known, fresh health and continuity. Do not implement a competing server-selection loop merely because the app coordinates channels. Provider group names and editable labels do not establish a tunnel identity.
- [ ] Review anti-flapping thresholds, failures/successes, minimum dwell/cooldown/backoff, primary recovery/hold preference, reserve exhaustion and full-root return. Simulated cascade support is not real vendor multihop acceptance.
- [ ] Preserve monitor-only mode and low-cost probes while diagnosing. Verify RPC concurrency/default deadlines, monitor restart, real CPU/RAM/flash-write budgets, retention and observation gaps on hardware. x86 VM/host timings are separate evidence.
- [ ] Clock correction was verified once; NTP/reboot retention is unknown. Independently test restart, actual reboot and separately authorized power/recovery; bootloader and actual recovery procedure remain untested despite matching downloaded recovery image.
- [ ] Hardware24-48h and unattended acceptance remain undone. A fresh agreed run needs new namespace/source/manifest and explicit stop/cleanup reporting; old stopped12h runs remain STOPPED.

## 7. Master setup, settings and remaining product acceptance

- [ ] Owner-selected physical first-run Save -> reload -> Settings edit -> reload round trip. Preserve terms1 and all drafts; never auto-accept old disposable-VM terms or mark onboarding complete without the actual save. Check atomicity, partial/lost response reconciliation, KEEP/clear secret semantics and cancellation.
- [ ] Reconcile ranking, recommendation application, event filters and persisted table choices against actual current implementation. Visual order must not change configured priority or move controls under a pointer; current/period samples, gaps and confidence remain explicit.
- [ ] Verify interface/monthly/calendar counters, resets/reconnect, renamed/deleted profiles, upgrades/downgrades, retained histories and time/DST discontinuities. Do not double-count one shared device or reconstruct unobserved traffic.
- [ ] Speed-test acceptance: chosen VPN binding, endpoint/method, byte/time/concurrency budget, cancel, busy/metered deferral and ranking impact. Optional/automatic tests remain off until deliberately configured.
- [ ] Telegram acceptance: fake API lifecycle first; token replacement/forget/failed write/expired response/deduplication/timezone schedule. Real test delivery requires the approved destination and explicit messaging instruction; keys/tokens never enter status/log/export/Git.
- [ ] Large incident/CSV/HTML/print/PDF reports, formula injection/escaping/redaction, page breaks, downloads and very long names. Prior one-page or synthetic passes do not cover large native printing.
- [ ] Security acceptance: exact RPC ACL/schema/type/size/freshness, concurrent controls, session expiry/CSRF/cross-origin, hostile names/errors, no secret-bearing status/exports/nested archives, lost acknowledgements and storage errors. Reuse existing regressions and extend changed surfaces.

## 8. Broader backlog - retain all prior plans without reopening passed scope

- [ ] Reconcile every A01-A50 item in [the50-item audit](../../.claude/handoff/TODO-50.md) against latest file/test/receipt evidence; mark implementation, virtual acceptance, physical acceptance and external blockers separately. Do not carry forward stale model/device/version claims or check off an item because a neighboring test passed. The title 'finish12h test' does not authorize resuming its stopped run.
- [ ] Carry forward NEXT-10 / POST-07 / A48: genuine exact-target vendor SDK/feed/toolchain provenance and full build. Existing payload staging and bounded child-target repeatability do not establish a complete matching vendor firmware SDK build.
- [ ] Carry forward NEXT-13 / POST-09 / A49: restricted server-triggered Gitea CI on a separate stand, exact source receipts, credential-free jobs, deliberately failing checks, permissions and review. Local isolated CI exists; server activation is not verified.
- [ ] Carry forward NEXT-22/23: isolated actual WG/OpenVPN endpoint matrix and real Linux DNS/firewall/IPv6/conntrack behavior using synthetic keys, independent clients and no host bridge. Generic Linux proof does not certify GL.iNet workers.
- [ ] Carry forward partial NEXT-24: actual virtual UCI/procd/package install/upgrade/rollback/interruption at all stages and config/history preservation. Preserve original stopped disks; a fresh disposable copy is distinct from resuming them.
- [ ] Audit existing completed NEXT/POST/UX/VIS work before extending it. Do not rebuild features already proven in their stated offline scope. Cross-check latest status suffixes because older checklist headers are historical.
- [ ] Preserve publication-parent/tree checks, unrelated remote edits, immutable tags and both histories. Optional signing/provenance, consolidated component/license/dependency inventory and additional actual compatibility targets remain review work, not unearned support claims.

Backlog sources: [NEXT01-24](../TODO-NEXT-STAGE.md), [POST01-15](../TODO-POST-ALPHA10.md), [algorithm/UX additions](../TODO-ALGORITHMS-UX-2026-10-17.md), [completion matrix](../COMPLETION-PLAN.md), [recovery TODO](RECOVERY-TODO-2026-10-20.md). The linked detailed tasks remain part of this resume list.

## 9. Final validation, installation and saving

- [ ] Freeze the implementation after meaningful review. Run focused changed-surface tests on Python3.9/Lua and3.11/Node, then the full application/QA/UI matrix on an immutable source. Retain all failed runs; do not call skipped coverage PASS without the other runtime's evidence.
- [ ] Regenerate only the new selected dashboard/CSS assets; preserve old release assets. Verify VERSION source fingerprint and visible package/page/style identity. Alpha17 is unreleased WIP; avoid accidental alpha18 bumps during checkpoint commits.
- [ ] Build the canonical Linux IPK from the reviewed committed source, record bytes/SHA in manifests and notes, verify reproducibility and exact payload/modes. Replace alpha16-only hardcoded installation/upload templates with a reviewed exact alpha17 package identity; never blindly reuse their SHA or rollback path.
- [ ] Before a physical upgrade, refresh encrypted recovery exports and independent in-memory decrypt/read verification, preserve known_hosts/DPAPI management key, confirm actual board/config/current transactions, and review rollback. No plaintext device configuration, sessions or credentials in the archive or Git.
- [ ] Install only the supported reviewed mode, then verify all installed program files and actually served assets, protected and own configuration across upgrade, sole expected service, terms/setup preservation and no unexpected VPN/Auto enable. Monitor-only visual improvement must not imply real manual switching is ready.
- [ ] Save local Git -> Gitea -> approved reviewed GitHub snapshot on public history, exact tree and remote-ref verification. Completed release additionally needs exact-commit CI, matching IPK SHA and downloaded asset verification. The prior explicit approvals named alpha16 and checkpoint8febc9d; do not assume a future alpha17 release was separately approved if automatic review requires its exact payload/destination.
- [ ] Create restore-verified local Git bundle/source/archive receipts. D: remains absent/pending the owner's intended disk; copy and verify when available, without touching unrelated disks. An old D backup or a local archive is not proof of a current D copy.
- [ ] Finish with a clear done/not-done report and agent statistics. Do not call Auto, manual switching, LAN safety or unattended operation working until their respective real acceptance passes.

## 10. Saved evidence and restart prompt

Local base WIP archive: `private/alpha17-wip-checkpoint-20261020-8febc9d/checkpoint.zip`, SHA256 `7ea20a0f960112ca9ac6e4ecf22e8fe2f889e01a95a0a240952f4d079713705a`; source/tree restore, fsck and8entry hashes verified. Later `git-upload-handoff.zip` supplements the earlier pending-upload state; its receipt proves the actual completed WIP upload. Device backups are separately encrypted and DPAPI-protected.

Suggested owner resume instruction: 'Continue from docs/handoff/RESUME-TODO.md. Start with the confirmed manual return Stop fence and runtime integration failures. Use agents within the available slots, preserve PC Wi-Fi and the primary router, and keep actual MT3000/LAN readiness separate from software tests.'
