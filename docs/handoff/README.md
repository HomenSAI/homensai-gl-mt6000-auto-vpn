# Handoff — 2026-10-16, Europe/Berlin

This folder is the entry point for continuing in VS Code. It records what exists, what was checked, why remaining work matters, and where evidence lives. It does not declare production readiness.

## Locations and branches

- Working Windows checkout: `C:\homensai\homensai-gl-mt6000-auto-vpn`. It already contained a clean GitHub-derived main at 843743f47828d8d1b9ab0955c5193a5d81ad236f. Preserve that main and its tags; import canonical Gitea history from a complete local bundle and select the native correction branch. The old shared-workspace source mirror is retained.
- Canonical development checkout used so far: `local-codex:/workspace/gl-mt6000-alta-vpn`.
- Current application branch: `feature/local-completion-alpha6`; prior alpha5: `fix/committed-recovery-observation`.
- Previous application branch: `feature/openwrt-native-alpha`, alpha4 checkpoint f320f7fd90cbb69b63fc9fd24caab6f1acc4dc17.
- Recovery correction: f09101c0560a29ae8712daa3a80934ab19159694; alpha5 source/UI checkpoint: 894ad03f670d6d74353031f23f50dc85fbe389eb. Later handoff/artifact commits are visible in `git log`.
- Gitea main is the original prototype plus tested Git tooling, not the full native candidate. The pre-existing Windows main is a separate older GitHub-derived snapshot and remains preserved. Preserve this distinction until a reviewed integration.
- Git tooling worktree: `local-codex:/workspace/gl-mt6000-gitflow`; archive-privacy branch `fix/gitflow-archive-privacy`, checkpoint 40dabd0f851fd413dfe3301876c2a7af76591ea7.

The Windows checkout and Docker checkout do not synchronize edits automatically. Pick one working tree per task. The local test launcher mounts the current Windows repository read-only, so it tests VS Code edits rather than an older Docker copy.

## Git and privacy

Primary Gitea: http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn
Windows primary remote name: gitea
Windows primary SSH remote: ssh://git@127.0.0.1:2223/localadmin/homensai-gl-mt6000-auto-vpn.git
Existing origin remains the GitHub fetch remote; do not assume origin is primary.
Secondary GitHub: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn

New GitHub publication is not authorized. Ordinary origin push is disabled in this checkout. Canonical tag objects are retained under refs/homensai-canonical/tags/* to avoid overwriting existing GitHub-derived tags. Do not overwrite tags, join unrelated histories automatically, force-push or mirror-push. Gitea and GitHub already have different roots and nine tag collisions; see the tooling main branch's audit/workflow documents.

The Git bundle transfers history, not credentials, SSH configuration, releases metadata or server databases. Host SSH push is not certified by the Docker transport result. Use an existing approved host key/profile if available; do not copy private keys into this repository. The prior Docker Gitea transport was verified separately.

Private snapshots are outside Git on independent restricted storage. Do not publish router backups, tokens, chat IDs, sessions, private keys or live configuration. No such secrets are needed for the offline tests.

## Run local checks

PowerShell 7 and Docker Desktop with Linux containers:

```powershell
./scripts/test-local.ps1
```

The launcher uses the already installed `local-dev-tools:installed` image, never pulls an image, disables external networking and mounts this checkout read-only. The launcher was executed successfully against this Windows checkout: 232 application tests, 5 QA tests and 8 Node suites; an injected exit 17 was correctly propagated. Alpha5 VM evidence is separate.

Do not run all Linux-specific tests directly in Windows Python: the controller uses Linux facilities such as fcntl. Browser smoke testing requires a labelled local fixture or explicitly authorized VM resume.

## Scope at pause

The physical router was not queried or modified during this local window. Its last recorded application is 0.6.0-alpha5; that is historical evidence. Alpha5 in these files means 0.7.0-alpha5 tested in an isolated x86 VM.

The VM is paused, with its disk/RAM retained. The last warm reboot failed its 180-second readiness window; cold recovery was interrupted at the user's stop request before its final acceptance. Do not claim the current paused guest is healthy merely from the earlier package-suite PASS.
