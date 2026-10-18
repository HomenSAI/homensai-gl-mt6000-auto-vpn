# HomenSAI Auto VPN — project entry point

Read the imported handoff before planning work. The owner requested a checkpoint for an independent Claude review on 17 October 2026.

Current scope: audit the repository and evidence, reconcile the 50-item backlog, and assess readiness for a future physical-router test. The owner stopped the running virtual endurance test. Do not resume it, start background tests, deploy to a physical router, enable Auto, change routes/DNS/firewall/acceleration, or alter Windows networking without a fresh direct user instruction.

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
