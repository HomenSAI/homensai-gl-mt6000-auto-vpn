# Main and release publication

The owner authorized the current0.9.0 release on main in GitHub and Gitea. Publish the reviewed source, user documentation, IPK/checksum and exact verification record. [Release evidence](RELEASE-0.9.0.md).

Preserve both existing histories. Current development descends from GitHub main; publish it by normal fast-forward only after full-history privacy review and exact tests. Canonical Gitea main has a different root but the previous main tree matched GitHub's. Integrate the new reviewed tree with both the old canonical main and the public release commit as parents; verify tree/package identity. Do not export unrelated, unaudited canonical history merely to make commit IDs equal. Equal reviewed trees/assets can have different main/tag SHAs, which must be recorded.

Respect branch protections and concurrent head changes; never force, mirror, delete old refs or overwrite tags/assets. Verify tag/main reachability, source/tree identity, metadata and independently downloaded assets. Existing releases remain historical; add a current-release notice without rewriting their test results or binaries. A new normal-numbered release retains experimental scope and does not imply external-LAN or unattended-production acceptance.

Use a private restore-verified source bundle and private encrypted device backup. Public files/assets must exclude keys, bot tokens, sessions, passwords, raw device state and backups. Device installation is a separate authorized task, never an automatic side effect of publication. The user's ongoing dedicated-MT3000 update request is recorded separately from this Git authorization.
