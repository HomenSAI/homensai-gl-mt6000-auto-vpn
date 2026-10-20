# HomenSAI Auto VPN — project entry point

Active continuation, 20 October 2026: the owner explicitly resumed implementation/local tests, requested D-drive archives and Git saves, and selected the mobile GL-MT3000 for future physical trials. It is not yet connected. Read docs/handoff/ACTIVE-STATE-2026-10-20.json and docs/handoff/RECOVERY-TODO-2026-10-20.md first; older review imports below are historical. Do not infer an available management path or bypass model/vendor guards. The primary physical GL-MT6000 remains excluded from tests/writes.

Read the imported handoff before planning work. The owner requested a checkpoint for an independent Claude review on 17 October 2026.

Historical 17 October scope: audit the repository/evidence and reconcile the 50-item backlog. The owner stopped that virtual endurance run; it remains STOPPED. The later 20 October continuation authorizes local implementation/tests and separate disposable VM copies, not resumption of an old run or access to the primary router. Keep physical GL-MT3000 work dependent on its actual connection/identity/backup and verified platform adapter; never bypass technical guards or alter Windows networking implicitly.

Use the current checkout as the source of truth. Keep evidence, assumptions and unverified device claims separate. Reports/work logs and diagnostic codes are English; English is the UI default with Russian available.

Never publish credentials, private run directories, disk images, raw sessions or full local history. Git/Gitea is primary; GitHub receives a reviewed snapshot on its existing public history. No force pushes or historical tag replacement.

Standing publication rule (owner, 18 October 2026): after a finished batch of changes Claude publishes it itself to local Git, Gitea and the public GitHub repository through scripts/offline-ci.ps1, scripts/save-gitea.ps1 and scripts/publish-reviewed.py (CI PASS on the exact commit, package hash equal to the CI hash, one release per batch, verify with git ls-remote). The limits above still apply, and the physical router, Auto and the LAN-trial confirmation still need the owner's direct instruction.

Standing UI rule (owner, 18 October 2026): every page in every design (A/B/C and any future one) always shows the owner attributes: HomenS.AI Auto VPN name, GL.iNet GL-MT6000 · Flint 2, Developer · Serhii Khomenko (homensai.com), program version + package + page build, HomenS.AI Style version, the header version badge and the author footer. A design may move them, never hide them; router/tests/test_attribution_ui.js enforces it. See docs/PRODUCT_REQUIREMENTS.md.

Standing UI rule (owner, 18 October 2026): every status lamp blinks gently in every page and design (green slow, yellow fast, red medium; grey does not blink; prefers-reduced-motion keeps lamps still). New status elements get the same small animation by default. See docs/PRODUCT_REQUIREMENTS.md.

Standing versioning rule (owner, 18 October 2026): the version shown on every page must always follow the code. VERSION.json records a fingerprint of the product source; when the source changes the version is advanced automatically (python scripts/bump-version.py; the pre-commit hook in .githooks does it and `git config core.hooksPath .githooks` enables it; qa/test_version_current.py fails CI if a change has no new version). Never publish a changed source under an old version.

@.claude/handoff/START-HERE.md
@.claude/handoff/STATE.md
@.claude/handoff/TODO-50.md
@.claude/handoff/REVIEW-PROMPT.md
