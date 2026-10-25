<!-- doc-role: current -->
# Publication policy

The owner's **latest applicable instruction** determines allowed delivery. Previously authorized operations do not need repeated permission; an old dated report is not new authorization. Feature-branch save, prerelease publication, main/stable changes and physical installation are distinct facts.

Canonical Gitea history is preserved. A public snapshot can parent the existing verified public branch while reusing the exact reviewed canonical tree, avoiding unrelated private history. Record canonical/public commits, complete tree equality and the tested product source. Fast-forward only: never force/mirror/delete old refs or replace published tags/assets. A docs-only closure can follow a tested product commit if the product fingerprint/code are unchanged and that distinction is recorded.

For a release, use one immutable tag, matching canonical IPK/checksum/verification and same-tag kit. Privacy-scan the complete public tree and archives, publish draft/prerelease/stable flags deliberately, independently download every attachment and verify SHA256. A manifest tag or branch push alone is not a server Release. Stable/main remain unchanged unless the owner actually included them.

Keep credentials, raw configuration, private transaction data and unencrypted backups out of Git/releases. A reviewed source save does not prove physical installation, browser rendering, external-model execution or LAN connectivity. Device work follows its own current identity/backup/lifecycle verification; never resume old observers automatically.

[Versioning](VERSIONING.md) · [CI](CI-PRIMARY.md) · [Actual current delivery](CURRENT-STATUS.md).
