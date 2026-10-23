# Release 0.9.0 verification record

This numbered experimental release promotes the implemented alpha45 behavior onto main. Functional code is unchanged apart from synchronized version/UI asset identity; documentation and repository/release descriptions are refreshed. It does not claim newly completed LAN/24h/power-cut/MT6000-continuous-mode tests.

## Behavior baseline

Alpha45 product8ce0fb265623f2fb5abb08f461f6d177419e48b1:724 application/107 QA tests per runtime and39 UI suites PASS,84installed files/modes/protected configurations PASS, actual HTTPS/HTTP8080 assets PASS. Actual Start57.61s and owner reserve restoration34.73s with Auto ON; both selected VPN DNS/twoHTTPS checks healthy. Canonical-package EN/RU agreement→intro→wizard/help interaction tests and local browser screenshots PASS. [Machine record](../qa/MT3000-FIRST-RUN45-2026-10-23.json).

Earlier physical evidence includes controlled automatic failure/return cycles, native-process recovery, manual selection while Auto remains enabled and persistent statistics/export. These retain their actual version/time scope. [Validation](VALIDATION.md) · [23October matrix](MT3000-AUTO-TEST-REPORT-2026-10-23.md).

## Exact0.9.0 qualification

The final source SHA, deterministic package hash/size, exact-source dual-runtime CI receipts, installed/served-byte and Start/selection verification, release/main/tag tree mappings and independently downloaded assets are recorded in the release-specific QA receipt and publication record added after the checks complete. Until that record is present, this section is preparation rather than a completed publication claim.

## Boundaries retained

Router-originated IPv4 scope only. Explicit Auto Start after restart. No independent LAN-client/current MT6000 continuous-mode/IPv6/full multireserve/24h/power-cut acceptance. Intermittent OpenVPN AUTH_FAILED and refused worker/readiness attempts remain documented. Successful retries do not erase earlier failures. No Windows networking or primary MT6000 changes are part of release qualification. Encrypted configuration/source recovery evidence remains private.
