# Versioning and release policy

VERSION.json declares the current application/package/UI identities and the independently versioned Claude review bundle. Validate it with python qa/check_versions.py using an approved local Python runtime. The validator is read-only; it does not build, install, run a router test or publish anything.

## Application

- Format MAJOR.MINOR.PATCH, optionally -alphaN or -betaN; GitHub product tag v<application-version>.
- MAJOR: incompatible behavior/configuration or supported-interface changes.
- MINOR: compatible product capabilities.
- PATCH: compatible product fixes.
- While the current line is experimental, advance the prerelease sequence for a new reviewed candidate. Never promote a candidate to stable based only on virtual/model evidence.
- Package revision is the positive OpenWrt PKG_RELEASE integer. Package identity is <application-version>-<revision>. Advance it for a repackaging/lifecycle correction within the same candidate; never replace existing package bytes.
- Keep VERSION.json, router/Makefile, router/build_ipk.py and agent.py consistent. Versioned JS/CSS/menu addresses must agree with the selected frontend recorded in VERSION.json.
- Product code changes require the appropriate existing checks and fresh release evidence. Documentation-only changes do not fabricate a new tested application version.

## Review/handoff bundle

- Format MAJOR.MINOR.PATCH; separate tag handoff-v<version>.
- MAJOR: incompatible review structure/scope.
- MINOR: additional compatible review sections or evidence.
- PATCH: corrections/clarifications without scope changes.
- Current handoff 1.0.0 reviews application 0.8.0-alpha2 / package 0.8.0-alpha2-1. It does not claim new application code or new device acceptance.
- Handoff release assets are a public sanitized context ZIP, checksum and version manifest. The ZIP is not a router installation package and does not contain the complete application source; use the corresponding GitHub source checkout for code audit.
- A handoff release remains a prerelease in this experimental repository and must not supersede a stable product release designation.

## Publication and immutability

Every reviewed change gets a local commit and CHANGELOG entry where relevant; save local Git/Gitea before the identical reviewed GitHub snapshot. Canonical and public histories differ. Existing tags/assets are immutable; no force push, tag replacement, bulk canonical-tag publication or upload --clobber.

Application tag guards in existing scripts support their documented v... forms. Handoff tags use a separately reviewed explicit-ref publication path; do not weaken product-tag guards merely to make a handoff tag pass. Map public tags separately under refs/homensai-public/tags/.

Validate metadata, document/archive references, secret exclusion and exact downloaded asset hashes for handoff-only releases. Do not restart stopped long-running or physical-router tests for a documentation release. Record the actual validation scope, not a fabricated fresh full-suite PASS.

## Automatic tracking

VERSION.json holds `source_fingerprint`, a SHA-256 over router/files, the page sources and the build scripts with the version strings neutralised. `python scripts/bump-version.py --check` fails when the source changed without a new version; running it without arguments advances the prerelease number, resets the package revision to 1, rewrites every version literal, rebuilds the page (so the pages show the new version) and records the fingerprint. The package hash is recorded after the package build (zeros until then). The pre-commit hook in .githooks runs it on every commit, and qa/test_version_current.py keeps CI honest.
