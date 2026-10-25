<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# UCI pending-change refusal

The settings writer and package lifecycle must not silently commit a previous process's saved changes.

- `SETUP-PENDING-DELTA`: the own-config saved delta is nonempty. No requested settings were written and the pending changes were not discarded.
- `SETUP-DELTA-UNVERIFIED`: the saved-delta location or read could not be verified. The operation was refused.
- `LIFECYCLE-PENDING-UCI-CHANGES`: installation/removal preparation found pending own-config changes. No automatic reset/commit is performed.

Setup, priority and monitor APIs return these fixed codes without exposing child output or private configuration. A refused monitor save must not start/stop the service. Success still requires both writer exit code zero and exact `OK` output.

## Operator resolution

Keep Auto stopped. Review the pending changes locally with an authenticated administrator. UCI output can include private tokens: do not copy it into public logs, issues, screenshots or chat. Decide explicitly whether to commit the reviewed changes or discard them. Neither action is performed automatically by this program. Retry the original request only after the pending changes have been resolved.

Do not treat an opkg exit status alone as proof of installation. The isolated OpenWrt version was observed returning zero despite a failed package-removal hook. Verify guard codes, installed package revision and unchanged files/configuration.

## Scope

Own application operations use the shared Auto-control lock. An external root process that ignores this lock is outside the cooperative-lock contract; these tests do not certify arbitrary concurrent administrator writes. No UCI or package preflight certifies GL.iNet workers, routes, DNS, Kill Switch, IPv6, LAN failover or physical flash/power-loss safety.

Historical draft files under handoff/pending-uci-fix are preserved as the previous checkpoint. Active implementation is under router/files/usr/lib/homensai-vpn; drafts are not package inputs.
