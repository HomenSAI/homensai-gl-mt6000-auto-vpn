<!-- doc-role: current -->
# Licensing transition record — 2026-10-31

Project: HomenSAI/homensai-gl-mt6000-auto-vpn.

## GitHub source changes

- [x] Root LICENSE replaced with **HomenSAI Personal & Commercial Source License v1.0**.
- [x] Original MIT text preserved verbatim in `LICENSE-MIT-LEGACY`.
- [x] Root licensing guide, commercial licensing page and README references updated.
- [x] Package license files and custom-package/SDK license metadata updated to `LicenseRef-HomenSAI-Personal-Commercial-1.0`.
- [x] Future source-side operational terms updated in English/Russian, and terms-version constant advanced to **2** for a future newly generated application build.
- [x] Existing author hyperlink in About/attribution is preserved.
- [x] Upstream style license and IBM Plex OFL files were not rewritten; historical project-specific MIT grant is expressly preserved.

## Not completed by this repository-only change

- [ ] **Generated immutable LuCI assets:** regenerate a *new* versioned dashboard/help module from `router/terms_panel.inc.js` and both disclaimers; do not overwrite previously published versioned UI assets.
- [ ] **Version and fingerprint:** use the normal project version-bump and manifest pipeline; do not publish an IPK labelled with an unchanged previously published version.
- [ ] **Build and tests:** run `scripts/bump-version.py --check`, documented local CI and Python/JS/package parity checks, including actual IPK control metadata, license copies and in-app displayed text.
- [ ] **Acceptance verification:** confirm a clean-install terms gate (version 2), existing acceptance invalidation and safe Auto refusal, on an isolated test device or representative environment.
- [ ] **Rights audit:** review all contributors, third-party code and original-owner claims before relying on the new license for any particular file; compare current source with pre-transition MIT history.
- [ ] **Professional review:** obtain German IP/software licensing advice before issuing commercial agreements; set prices, taxes, invoices, consumer protection and jurisdiction clauses in individual contracts.
- [ ] **Publish a new versioned release:** build, sign/checksum and verify release assets using the project's release process; never modify existing tags/assets or installed routers without explicit separate authorization.

**Hard boundary:** This commit does not retroactively remove MIT rights, make a new release, install software on a router, verify legal enforceability, or prove that the newly edited source builds successfully. Every unperformed check above remains openly marked unverified.
