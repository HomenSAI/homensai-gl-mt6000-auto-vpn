# Verify a downloaded release

1. Confirm the release tag0.9.0 and matching package/checksum names. Verify SHA256 locally before upload.
2. Read [current scope](CURRENT-STATUS.md) and [exact release record](RELEASE-0.9.0.md); passing source tests alone are not device acceptance.
3. Installation verification checks package version, all immutable payload hashes/modes, protected router settings and actual served JavaScript/CSS.
4. Confirm advancing monitor data and DNS/twoHTTPS for the selected saved pair. A queue ACK is not Start or switch completion.
5. Record final Auto/selected-route state, test cleanup and private recovery backup. Never claim an external-LAN certificate from router probes.

For maintainers, `scripts/offline-ci.ps1` runs both preinstalled isolated runtimes from a committed Git archive and records a source-bound receipt. Matching deterministic package bytes and source fingerprint are mandatory. [Publication](PUBLICATION.md) · [CI isolation](CI-PRIMARY.md).
