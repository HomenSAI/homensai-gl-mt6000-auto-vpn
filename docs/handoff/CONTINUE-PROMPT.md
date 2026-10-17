# Continuation prompt for a coding assistant

Continue HomenSAI Auto VPN from this real Git checkout. First read START-HERE.md, docs/handoff/README.md, STATUS.md, TODO.md, TEST-RESULTS.md, docs/STATE.md and the latest WORKLOG entries. Inspect current branch, dirty/staged files and remotes before editing.

The current local branch is feature/local-completion-alpha6; fix/committed-recovery-observation preserves alpha5. Gitea main contains the original prototype and Git workflow tooling; the preserved Windows main is an older GitHub snapshot; do not replace the native branch with main or discard preserved untracked files. Work on a separate feature/fix branch. Local Gitea is primary; save meaningful checked commits there. GitHub publication currently needs separate permission and history/tag reconciliation. Never force-push, rewrite tags or copy credentials.

Physical-router work is NOT authorized. Virtual testing was explicitly stopped and QEMU is paused; do not resume or run VM experiments without a new user instruction. Offline unit/model/UI development can continue. Keep English diagnostic codes, causes, corrections and dated logs; English is the UI default with optional Russian.

Priority: finish the multi-hop algorithm and root rollback model, then independent fault scenarios, mobile/all-page UI and wizard validation. Preserve LAN confirmation, Kill Switch, policy-generation checks, bounded leases and unknown-state blocking. Do not remove guards merely to make tests or demos green. Inactive-profile activation and true GL.iNet worker arbitration need verified adapters and later hardware acceptance.

Use scripts/test-local.ps1 to test this Windows checkout in a network-isolated Linux container after reviewing the script. The offline Windows bind-mount launcher and its failure propagation have been verified. Keep alpha6 offline results separate from earlier VM/device evidence.

For each task record: timestamp/timezone, concrete failure or gap, verified cause (or unknown), correction, test result, remaining limitation and Git commit. Do not claim full production readiness from simulations. Update docs/handoff and the approved checklist as evidence changes.
