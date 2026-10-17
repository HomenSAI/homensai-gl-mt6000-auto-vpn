# Start here — VS Code continuation

Working folder: `C:\homensai\homensai-gl-mt6000-auto-vpn`.

Open `homensai-gl-mt6000-auto-vpn.code-workspace` in VS Code.

1. Read [handoff overview](docs/handoff/README.md).
2. Read [verified status](docs/handoff/STATUS.md) and [remaining work with purpose](docs/handoff/TODO.md).
3. Read the [complete 24-task next-stage plan, including additional features](docs/TODO-NEXT-STAGE.md).
4. Read [test evidence and limits](docs/handoff/TEST-RESULTS.md).
5. For another coding assistant, use [continuation prompt](docs/handoff/CONTINUE-PROMPT.md).

The current offline-completion code is on `feature/local-completion-alpha6`; `fix/committed-recovery-observation` preserves the prior alpha5 checkpoint. Do not switch to main expecting the complete application: Gitea main contains the prototype plus Git workflow tooling; the preserved Windows main is the older GitHub snapshot. Native application history has intentionally not been merged into main automatically.

Physical-router work is not authorized in this handoff. Virtual tests were stopped at the user's request and QEMU is paused. Do not resume/deploy without a new instruction.

GitHub publication is withheld under the latest Git task. Local Git/Gitea is primary; existing unrelated GitHub history/tag collisions require reviewed reconciliation, not force-push.
