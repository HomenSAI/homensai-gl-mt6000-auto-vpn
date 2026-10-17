# GitHub main publication - preparation

Recorded: 2026-10-17T09:27:09.431921+02:00 Europe/Berlin.
Approval: user explicitly requested publishing the latest local project to GitHub main.
Repository: HomenSAI/homensai-gl-mt6000-auto-vpn (public); freshly verified main parent: 51982dd249fb4ea96fbd1573f35e01bdd9c538d5.

Canonical and public histories have different roots. Prepare a single reviewed snapshot commit on that public parent, preserving the complete canonical history in Gitea and existing public ancestry. No merge of unreviewed local history, force update, tag overwrite, deletion or router change.

Reviewed candidate: alpha8-1, package SHA256 da7f42716b3d35504be3f586a7ee1b18c8e75a8ec51c01e134dd24da3b182453. Source/package privacy and dual-runtime checks already passed. Before push, verify the exact publication snapshot and parent and save its branch to Gitea. Public release tag v0.7.0-alpha8 was absent at preflight; preserve all old tags and publish only the new public tag on the public commit.

Manual privacy pass found personal workspace context in two Markdown files. Replaced that context with a generic previous-private-workspace description; no product code or package changed. Known router-profile strings and direct private identifiers were not present in tracked text. Synthetic screenshots are labelled; runtime keys, tokens, backups and live data remain ignored/private. Automated scanning is an additional check, not proof against every possible secret.

This record is preparation, not confirmation of a completed push. Final result is recorded separately after remote verification.
