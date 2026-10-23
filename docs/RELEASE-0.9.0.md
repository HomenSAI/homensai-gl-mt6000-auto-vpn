# Release 0.9.0 verification record

This numbered experimental release promotes the implemented alpha45 behavior onto main. Functional code is unchanged apart from synchronized version/UI asset identity; documentation and repository/release descriptions are refreshed. It does not claim newly completed LAN/24h/power-cut/MT6000-continuous-mode tests.

## Behavior baseline

Alpha45 product8ce0fb265623f2fb5abb08f461f6d177419e48b1:724 application/107 QA tests per runtime and39 UI suites PASS,84installed files/modes/protected configurations PASS, actual HTTPS/HTTP8080 assets PASS. Actual Start57.61s and owner reserve restoration34.73s with Auto ON; both selected VPN DNS/twoHTTPS checks healthy. Canonical-package EN/RU agreement→intro→wizard/help interaction tests and local browser screenshots PASS. [Machine record](../qa/MT3000-FIRST-RUN45-2026-10-23.json).

Earlier physical evidence includes controlled automatic failure/return cycles, native-process recovery, manual selection while Auto remains enabled and persistent statistics/export. These retain their actual version/time scope. [Validation](VALIDATION.md) · [23October matrix](MT3000-AUTO-TEST-REPORT-2026-10-23.md).

## Exact0.9.0 qualification

Exact software qualification **PASS** on source `2e69e867c876b64d3d0013cf03efdbbf5f0e63fa`: Python3.11.2 ran724 application/107 QA tests and39 UI suites; Python3.9.15 with Lua ran724 application/107 QA tests. The3.11 application run skipped16 Lua-dependent checks, which ran in3.9; the3.9 QA run skipped15 development-tool checks, which ran in3.11. Skips are retained in the [machine-readable record](../qa/RELEASE-0.9.0.json). Both isolated, network-disabled matrices produced the same deterministic package. The pre-crash incomplete CI attempt has no PASS receipt and remains incomplete; this is a fresh run.

Package `homensai-auto-vpn_0.9.0-1_all.ipk`: **769849bytes**, SHA256 `7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a`. Canonical Linux build and both CI runtimes agree. Complete-history privacy scan inspected2624 reachable blobs/85,478,439bytes, including supported nested archives, with no secret-pattern/private-path findings.170 Markdown files were audited; local documentation links resolve.

All85 selected payload files equal the physically checked alpha45 payload after replacing only the version and dashboard/CSS resource identity. There is no algorithm change. **0.9.0 was not installed on the router during this publication-only continuation**; installed/served-byte and Start/selection results above belong to alpha45. No new device acceptance is inferred from CI or byte comparison.

Final release-tag/main mappings, final tagged-source CI and independently downloaded GitHub/Gitea assets are verified during publication and recorded in the release verification asset and subsequent publication record. A prepared local package alone is not publication proof.

## Boundaries retained

Router-originated IPv4 scope only. Explicit Auto Start after restart. No independent LAN-client/current MT6000 continuous-mode/IPv6/full multireserve/24h/power-cut acceptance. Intermittent OpenVPN AUTH_FAILED and refused worker/readiness attempts remain documented. Successful retries do not erase earlier failures. No Windows networking or primary MT6000 changes are part of release qualification. Encrypted configuration/source recovery evidence remains private.
