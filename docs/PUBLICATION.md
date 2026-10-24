# Branch, main and release publication — 24 October2026

Current owner scope: publish the reviewed training/documentation candidate and preceding VM report to **feature/owner-ui-20261023** on GitHub and Gitea. This is not a main merge, new stable release or physical-router installation. Public stablev0.9.0 is unchanged. [RU](CURRENT-STATE.ru.md) · [EN](CURRENT-STATE.en.md).

Preserve canonical Gitea history. Public snapshots may use the verified public branch as parent while reusing the exact canonical tree, avoiding exposure of unrelated local history. Verify both remote refs and complete file-tree equality; record canonical/public SHAs and the exact tested source. Use fast-forward updates and reconcile concurrent remote changes. Never force, mirror, delete old refs, overwrite tags/assets or bypass protected branches.

A future main/release operation needs its own applicable owner scope, exact checks, matching IPK/checksum/verification, privacy scan and independent readback. Existing dated release reports retain their test facts. Same reviewed content may have different commit SHAs because history differs.

Save recoverable source/evidence locally. Keys, passwords, tokens, raw device state and backups stay private. A successful branch push does not prove installation, native browser acceptance, external-model prompt execution or real LAN connectivity. Device work is separate; do not resume historical fault observers.
