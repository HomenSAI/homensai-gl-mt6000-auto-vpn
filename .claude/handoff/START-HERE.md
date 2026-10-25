<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](../../docs/CURRENT-STATUS.md) · [documentation index](../../docs/DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Start here: independent review checkpoint 1.0.0

Historical review package. Active 20 October continuation: ../../docs/handoff/ACTIVE-STATE-2026-10-20.json and ../../docs/handoff/RECOVERY-TODO-2026-10-20.md. Read those first; the stopped run described here remains historical and was not resumed.

## Read order

1. STATE.md — current product, completed evidence, stopped run and limitations.
2. TODO-50.md — every proposed follow-up, original numbering preserved. This is a review backlog, not an instruction to implement all items.
3. ROUTER-READINESS.md — distinguish read-only device preparation, monitor installation, bounded switching trial and unattended operation.
4. REVIEW-PROMPT.md — requested review outputs and scope.
5. EVIDENCE.json and the referenced qa/ receipts; verify claims against code and tests.

Root CLAUDE.md imports this overview, state, full backlog and review prompt. Claude Code should load that project file when launched in the repository; confirm using /context. A normal Claude web conversation does not automatically read local folders: attach these files or paste REVIEW-PROMPT.md.

Official instruction-loading documentation: https://code.claude.com/docs/en/memory . Imports are context, not a security enforcement boundary; existing tool/user permissions still apply.

## Locations

- Canonical Windows checkout: C:/homensai/homensai-gl-mt6000-auto-vpn.
- All handoff paths are relative to the repository; no second working copy should silently replace it.
- Development branch: feature/local-completion-alpha6.
- Private raw stopped-run evidence: private/virtual-hardening-20261017/endurance-alpha2-12h.
- Local disk checkpoints, instrumented packages and full Git bundles remain private/ or .git/handoff/. Do not stage or upload them.
- Docker local-codex is used by the existing Git/Gitea transport. Its presence does not mean it contains current Windows working edits.

## Current authorization

The owner asked to stop tests, record a checkpoint and let Claude independently assess what is done and whether physical testing may begin. Review first. Do not treat historical approvals or the backlog as current permission to restart tests or manipulate a device. A later direct user instruction can authorize a specific next step.

The virtual clone is paused, test processes have exited, and no new long test is scheduled. Do not resume it merely to inspect code. The physical router was not accessed or modified during this handoff.

Version identity: repository VERSION.json declares handoff 1.0.0 separately from application 0.8.0-alpha2/package 0.8.0-alpha2-1. See docs/VERSIONING.md. No stopped test is resumed by this documentation release.
