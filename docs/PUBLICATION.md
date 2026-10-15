# Publication workflow

1. Develop and verify in the local canonical Git repository/Gitea.
2. Record changes, version, checks, limitations and package SHA256 locally; commit and tag, then push to local Gitea.
3. Audit tracked files and every nested ipk archive for credentials and private material. Automated scanning supplements manual review; it is not a universal secrecy guarantee.
4. Export the verified local tag with `git archive`. The first public repository starts with this reviewed snapshot, without copying unreviewed historical commits. Record the canonical source commit in the public commit/release notes. Later public changes follow the same local-first process.
5. Publish the matching public GitHub tag and release assets. Verify repository visibility, release tag, files and checksums.

Keep configuration backups, captured status/logs, credentials, SSH keys, bot tokens/chat IDs, browser state and device screenshots outside the repository. Author biography/book links come only from the author's public website/profile.

There are two product modes in the roadmap: monitor (implemented) and operation/automatic failover (not implemented). Public documentation must never describe the planned mode as available or device-tested.

Repository names always start with `homensai-`: `homensai-gl-mt6000-auto-vpn`. Local Gitea first, GitHub second.
