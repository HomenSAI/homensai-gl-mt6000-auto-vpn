# Release 0.9.0 verification record

This numbered experimental release promotes the implemented alpha45 behavior onto main. Functional code is unchanged apart from synchronized version/UI asset identity; documentation and repository/release descriptions are refreshed. It does not claim newly completed LAN/24h/power-cut/MT6000-continuous-mode tests.

## Behavior baseline

Alpha45 product8ce0fb265623f2fb5abb08f461f6d177419e48b1:724 application/107 QA tests per runtime and39 UI suites PASS,84installed files/modes/protected configurations PASS, actual HTTPS/HTTP8080 assets PASS. Actual Start57.61s and owner reserve restoration34.73s with Auto ON; both selected VPN DNS/twoHTTPS checks healthy. Canonical-package EN/RU agreement→intro→wizard/help interaction tests and local browser screenshots PASS. [Machine record](../qa/MT3000-FIRST-RUN45-2026-10-23.json).

Earlier physical evidence includes controlled automatic failure/return cycles, native-process recovery, manual selection while Auto remains enabled and persistent statistics/export. These retain their actual version/time scope. [Validation](VALIDATION.md) · [23October matrix](MT3000-AUTO-TEST-REPORT-2026-10-23.md).

## Exact0.9.0 qualification

Exact software qualification **PASS** on source `2e69e867c876b64d3d0013cf03efdbbf5f0e63fa`: Python3.11.2 ran724 application/107 QA tests and39 UI suites; Python3.9.15 with Lua ran724 application/107 QA tests. The3.11 application run skipped16 Lua-dependent checks, which ran in3.9; the3.9 QA run skipped15 development-tool checks, which ran in3.11. Skips are retained in the [machine-readable record](../qa/RELEASE-0.9.0.json). Both isolated, network-disabled matrices produced the same deterministic package. The pre-crash incomplete CI attempt has no PASS receipt and remains incomplete; this is a fresh run.

Package `homensai-auto-vpn_0.9.0-1_all.ipk`: **769849bytes**, SHA256 `7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a`. Canonical Linux build and both CI runtimes agree. Complete-history privacy scan inspected2624 reachable blobs/85,478,439bytes, including supported nested archives, with no secret-pattern/private-path findings.170 Markdown files were audited; local documentation links resolve.

All85 selected payload files equal the physically checked alpha45 payload after replacing only the version and dashboard/CSS resource identity. There is no algorithm change. **0.9.0 was not installed on the router during this publication-only continuation**; installed/served-byte and Start/selection results above belong to alpha45. No new device acceptance is inferred from CI or byte comparison.

## Published release — PASS

[GitHub v0.9.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0) and [Gitea v0.9.0](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0) are published normal releases: no Draft and no Pre-release. GitHub marks0.9.0 Latest. Each includes the IPK, matching checksum and [final-source verification JSON](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/v0.9.0/release-v0.9.0-verification.json). All three assets were independently downloaded from both hosts and their hashes match.

GitHub tag/main at publication: `f0678decee7e932edb313efecc9e4697cb0569c1`. Canonical Gitea tag/main at publication: `5f7ea5089d82ad1544792c0dac9ee9be3027101f`. Both release trees are `14fdf2aac62bea80cf3deb3caf3057afc3825a4c`. Each exact tagged commit passed the full dual-runtime724application/107QA-per-runtime/39UI matrix. The Gitea merge retains both its former main and the public release as parents; no history was forced or exported to GitHub to equalize SHAs.

Both repository descriptions now describe implemented primary/reserve Auto. Current-release notices were added to40 historical GitHub releases and4 Gitea releases; original notes remain below the notices and asset identities are unchanged. A19,933,974byte private source bundle was restored and both histories/HEADs/full fsck verified. The crash-damaged index of an old temporary worktree was backed up and rebuilt without modifying worktree files; full repository fsck now passes.

See the [publication record](../qa/RELEASE-0.9.0-PUBLICATION.json). A subsequent documentation-only verification commit may advance main while the release tags and package bytes remain immutable.

## Boundaries retained

Router-originated IPv4 scope only. Explicit Auto Start after restart. No independent LAN-client/current MT6000 continuous-mode/IPv6/full multireserve/24h/power-cut acceptance. Intermittent OpenVPN AUTH_FAILED and refused worker/readiness attempts remain documented. Successful retries do not erase earlier failures. No Windows networking or primary MT6000 changes are part of release qualification. Encrypted configuration/source recovery evidence remains private.
