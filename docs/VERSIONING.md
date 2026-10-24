<!-- doc-role: current -->
# Version, cache and artifact identity

[VERSION.json](../VERSION.json) is the source-candidate metadata. [CURRENT-STATUS](CURRENT-STATUS.md) separately records what was actually installed/published. A handoff version is not an application version.

Runtime, package builder/Makefile, selected LuCI controller/menu, immutable module/CSS path, candidate install kit and artifact must agree. `scripts/bump-version.py --check` refuses changed product source with a stale fingerprint. Product/operator-text/helper changes require a new application candidate; a prose-only documentation closure does not require another router install.

Advance selected module/CSS identities for new shipped UI content before generating the candidate. `scripts/bump-version.py` rebuilds the selected page and advances the prerelease when stale. Do not overwrite old released assets/tags or patch installed version bytes in place. `--fingerprint-only` is for reconciling an unreleased reviewed candidate, not hiding post-release changes.

Build canonical artifacts from one committed archive in pinned Linux CI environments and require matching SHA256. Explicit gzip level alone does not make every host zlib implementation byte-identical; Windows Python3.15/zlib-ng can emit different compression for equivalent payloads. Use the verified canonical package, never silently relabel another package as passed.

Record package bytes/hash in the manifest and matching install kit. Verify downloaded/installed/served content separately. [CI boundary](CI-PRIMARY.md) · [Publication](PUBLICATION.md).
