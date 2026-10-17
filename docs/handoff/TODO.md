# Remaining work — what and why

Complete next-stage backlog: [24 tasks with priorities, dependencies and acceptance criteria](../TODO-NEXT-STAGE.md), including additional features NEXT-16 through NEXT-20. All are planned; this link does not claim implementation.

## Offline scope completed — alpha6

- [x] Full multi-hop state machine: server within channel -> another channel -> another VPN protocol. Retain a validated root policy snapshot and distinguish rollback of one hop from restoration of the original route. Purpose: recover after more than one reserve fails without losing the original configuration.
- [x] Expand model/fault-injection coverage: cancellation at each phase, RPC failures, stale health, clock jumps, changing policies, repeated reserve failure and corrupted journals. Purpose: prove decisions and invariants before device access. These are simulations, not hardware proof.
- [x] Design vendor-adapter arbitration and per-edge certification. Purpose: avoid racing GL.iNet workers. A private lock or pre/post hashes alone are insufficient; do not remove that blocker to make a demo pass.
- [x] Complete mobile UI, table filters/sorting persistence, all-page translations and state color/visual-order checks. Purpose: make the installed interface usable and consistent while polling.
- [x] Complete wizard validation/review matrix, including unsupported choices and RPC-save failure contracts; actual UCI failure injection remains device-specific. Purpose: prevent an invalid configuration from appearing successful.
- [x] Extend statistical boundary tests and freshness/unknown-state labels. Purpose: distinguish exact observations, estimates, inactive profiles and missing periods.
- [x] Validate the Windows VS Code offline Docker launcher against the new checkout. Purpose: ensure future edits, rather than the older Docker copy, are actually tested.
- [x] Review SDK staging parity and retired asset handling. Purpose: keep SDK-built and custom-built packages consistent; SDK version is aligned, full SDK build was not run.
- [ ] Complete Git history reconciliation plan and release metadata migration proposal. Purpose: retain original objects/tags and both histories. No public sync before explicit permission.

Full code/proof references: ../OFFLINE-COMPLETION.md and ../../qa/ALPHA6-LOCAL-REPORT.json. SDK payload parity passed; an external SDK build remains unrun. GitHub migration remains approval-gated.

## Only after a new VM-test instruction

- [ ] Confirm cold recovery from the preserved disk, then explicitly resume the paused VM.
- [ ] Investigate warm-reboot kernel-decompression failure. Cache limiting reduced RAM use but did not make warm reboot pass.
- [ ] Run actual responsive/wizard/error-path browser tests and controlled virtual tunnel tests. Generic x86 OpenWrt cannot certify proprietary GL.iNet behavior.

## Requires an authorized physical GL-MT6000 window

- [ ] Validate shared vendor-worker/hotplug/operator arbitration.
- [ ] Exercise each supported real VPN transition and root rollback from a source-bound LAN client, including DNS and Kill Switch.
- [ ] Verify acceleration handling, inactive-profile startup and isolated parallel candidate probes.
- [ ] Test IPv6, executor-crash recovery, actual reboot and separately agreed physical power loss.
- [ ] Confirm opt-in speed-test routing/quotas and Telegram delivery to the approved destination.
- [ ] Approve unattended production only after the supported matrix and recovery behavior pass.

Use the detailed approved checklist in ../COMPLETION-PLAN.md. Do not check a hardware criterion because a model or VM test passed.


## New review request - 17 October 2026

Proposed algorithm, button interaction and brighter raised-control work: [approval checklist](../TODO-ALGORITHMS-UX-2026-10-17.md). Status: awaiting review, no UI implementation or physical deployment in this request. Existing completed work remains completed within its documented scope.


## Alpha8 execution result - 17 October 2026

The newly approved checklist has been executed in the documented local scope: [results and hardware gates](../ALPHA8-UX-ALGORITHMS-RESULTS.md). This supersedes its earlier awaiting-review label. Real worker/LAN acceptance and GitHub reconciliation remain pending.
