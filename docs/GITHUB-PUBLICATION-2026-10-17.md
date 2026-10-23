<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# GitHub main publication - preparation

Recorded: 2026-10-17T09:27:09.431921+02:00 Europe/Berlin.
Approval: user explicitly requested publishing the latest local project to GitHub main.
Repository: HomenSAI/homensai-gl-mt6000-auto-vpn (public); freshly verified main parent: 51982dd249fb4ea96fbd1573f35e01bdd9c538d5.

Canonical and public histories have different roots. Prepare a single reviewed snapshot commit on that public parent, preserving the complete canonical history in Gitea and existing public ancestry. No merge of unreviewed local history, force update, tag overwrite, deletion or router change.

Reviewed candidate: alpha8-1, package SHA256 da7f42716b3d35504be3f586a7ee1b18c8e75a8ec51c01e134dd24da3b182453. Source/package privacy and dual-runtime checks already passed. Before push, verify the exact publication snapshot and parent and save its branch to Gitea. Public release tag v0.7.0-alpha8 was absent at preflight; preserve all old tags and publish only the new public tag on the public commit.

Manual privacy pass found personal workspace context in two Markdown files. Replaced that context with a generic previous-private-workspace description; no product code or package changed. Known router-profile strings and direct private identifiers were not present in tracked text. Synthetic screenshots are labelled; runtime keys, tokens, backups and live data remain ignored/private. Automated scanning is an additional check, not proof against every possible secret.

This record is preparation, not confirmation of a completed push. Final result is recorded separately after remote verification.


## Verified first publication

- GitHub main: 5e9f23486e05fe7037624a404a905c9d615436b5, directly verified through the GitHub API after normal push.
- Canonical source: a514afa482792a6d630831dd8a822a18962fe47e; public tree exactly matches it.
- Previous public main 51982dd249fb4ea96fbd1573f35e01bdd9c538d5 is the sole parent; no canonical historical commit is introduced as a parent.
- Exact public snapshot passed dual-runtime CI and nested privacy checks; package SHA256 da7f42716b3d35504be3f586a7ee1b18c8e75a8ec51c01e134dd24da3b182453. Publication branch was saved and verified in Gitea first.
- Historical tag refs retained for before/after comparison. No force, mirror, old-tag push or router change.

A documentation-only follow-up records this completed operation; its final SHA and release response remain in the local verification receipt.


## Release verified

GitHub prerelease: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.7.0-alpha8. Public tag target: a0fbd054f30e887b9b276399027d3ba31b33e21e. Canonical tag remains 22b75b8500acc6bb13af302b0cbea0124f440a66; public mapping is stored separately, without overwriting either history.

Both release assets were downloaded again: IPK 463562 bytes, SHA256 da7f42716b3d35504be3f586a7ee1b18c8e75a8ec51c01e134dd24da3b182453; downloaded checksum matches. All 13 pre-existing tag refs, including peeled annotation refs, are unchanged. Release is prerelease=true and draft=false. Reviewed verification receipt: qa/GITHUB-ALPHA8-PUBLICATION.json.

A final documentation/transport follow-up can advance main beyond the release tag; product/package bytes remain identical. It does not move the immutable release tag or install anything on a router.
