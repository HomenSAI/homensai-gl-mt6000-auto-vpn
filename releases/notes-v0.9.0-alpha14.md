# HomenS.AI Auto VPN 0.9.0-alpha14

After the separate terms screen, first entry opens one complete eight-stage setup wizard: language and appearance defaults, monitoring, existing VPN profiles and trial preferences, server metadata, recovery rules, optional speed tests, optional Telegram reports, and a full review. The same editor remains under Settings after completion. An independent Emergency Stop stays available through every stage and pending save. An explicit one-entry dashboard link keeps recovery/Return controls reachable while setup remains incomplete; a fresh entry opens the unfinished wizard again.

All application preferences and a separate first-run completion marker are saved in one own-UCI transaction. A new cursor verifies the committed values before success is acknowledged. A failed or unconfirmed response retains the draft. No-profile installations can explicitly defer the VPN pair. Blank Telegram secrets are retained without being returned, shown in the review, or stored in browser persistence. Existing configured values are loaded before any edits.

Validation: 45 focused Python 3.9/Lua checks, 31 Node UI suites, and 12 frozen browser combinations (three designs, English/Russian, desktop/narrow). Browser checks cover invalid input, Back, pause/resume, duplicate pending Save, failure/retry, every-step geometry, persistence after clearing browser storage, later Settings editing, independent Stop during pending Save, and recovery escape without a completion write. Publication additionally requires exact-commit dual-runtime CI and a package hash match.

Canonical IPK: 670588 bytes, SHA256 `8f312a60ab8ef10a866a29d2765982d83a4a0f4c75eac7f7591477ffd174f2d9`.

This is a development prerelease. Completing setup does not start Auto, import VPN credentials, accept terms, run a speed test, or certify a router. Physical GL-MT3000/vendor/LAN acceptance remains pending. The existing alpha12 endurance observation keeps its original source and is not alpha13 acceptance evidence. See the active handoff and first-run validation report for scope and retained failures.
