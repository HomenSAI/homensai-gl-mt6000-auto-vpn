# Publication workflow

Develop in the canonical local repository and save the exact reviewed commit to primary Gitea before GitHub publication. Scan tracked files and every nested package/archive for credentials/private material; keep backups, runtime state, tokens, sessions, private manifests and personal workspace details out of public snapshots. Author attribution and links use public author information.

## Independent history boundary

The canonical Gitea development history and the existing GitHub main have different roots. Publish a reviewed snapshot as a new commit whose parent is the freshly fetched GitHub main. Preserve the full canonical development history in Gitea. Record canonical source SHA, public parent, tree identity and artifact hashes. This retains public history without making unreviewed canonical historical objects public.

Do not force-push, mirror, delete old refs or overwrite tags. Save the exact publication branch to Gitea first, then use a normal fast-forward-only push to GitHub main. If main moves or protection refuses the push, stop and rebase/review the publication candidate or use the required PR flow. User approval for publication does not authorize bypassing branch protection.

A public release tag must reference the public snapshot commit. Local canonical tags may point to different history objects with the same reviewed product content; keep the public tag mapping in a separate namespace and never push canonical tags in bulk. Verify new public tag availability before creation, and preserve all historical public release/tag objects.

## Validation and product claims

Verify remote main SHA, published tree, release target, downloaded asset SHA256 and versioned notes. Automated scanning supplements manual review, not a universal guarantee. Monitor is implemented; native operation is a bounded client-certified experiment. Pure cascade/model and virtual tunnel results are not certification of full native multi-hop production, real vendor arbitration, IPv6 or power recovery. Never deploy a release to a router as part of GitHub publication.

Repository names start with homensai-: homensai-gl-mt6000-auto-vpn. Local/Gitea first, GitHub second. Default interface and diagnostics are English; optional Russian remains available.
