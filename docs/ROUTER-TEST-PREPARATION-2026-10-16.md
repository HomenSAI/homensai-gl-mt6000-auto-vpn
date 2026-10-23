<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Cable correction and active primary — 2026-10-16T19:14:13.5975777+02:00

Owner authorised cable 10051 correction and active main VPN selection for a later test. No failover, Auto enablement or package installation performed.

| Check | Result |
|---|---|
| Root cause | Ethernet IgnoreDefaultRoutes Enabled caused interface-bound network-unreachable / Windows 10051 despite a visible default route |
| Windows change | IgnoreDefaultRoutes Disabled, ActiveStore only; Ethernet metrics 500 retained |
| Wi-Fi | Ordinary default traffic still selects Wi-Fi interface 15; no adapter, DNS, weak-host or NordVPN changes |
| Cable validation | DNS PASS; explicit source/interface-bound TLS/HTTPS on two endpoints PASS, ~375 ms each |
| Actual client exit | Same exit for both endpoints; matches selected main VPN |
| Main test profile | Active generic OpenVPN Germany, ovpnclient2 |
| Reserve | Active generic WireGuard Germany, wgclient1, unchanged |
| Router change | Exactly main.plan_source changed semantically; other own settings/section identities preserved |
| Native precheck | No blockers; accepted selection |
| Safety postconditions | Auto off, pending UCI empty, eight non-own critical configs unchanged |
| Installed package | Still 0.6.0-alpha5-1; alpha7-2 not deployed |

Windows correction is session-only; no persistence after reboot/adapter recreation claimed. No new host routes or default route/metric edits. Wi-Fi is preferred but still shares the GL-MT6000 gateway: independent outage recovery Internet is not established.

Router write held the own Auto-control lock and required Auto off, stopped/rolled-back controller state, no pending delta, fresh healthy eligible generic Kill Switch profiles. A private temporary savedir isolated the UCI write and was removed. No live VPN restart, route_policy/special-policy reorder, firewall or acceleration change.

After commit, an exact exported-text assertion failed (UNEXPECTED-CONFIG-DIFF). No second mutation was attempted. Full before/after section identity and option-map comparison proved only main.plan_source changed. A failed post-write assertion must not be interpreted as no write.

Sanitised evidence: ../qa/router-preparation-2026-10-16.json. Exact before/after own config, Windows pre-change snapshot, exits and original archive remain in ACL-restricted ignored private/router-readonly-2026-10-16/. Eight protected configs match original backup; the own config differs intentionally.

Rollback only if owner requests it: restore original Ethernet IgnoreDefaultRoutes Enabled in ActiveStore after confirming interface identity (this deliberately restores former default-ignore behaviour). Do not change Wi-Fi defaults. Saved own metadata can restore the prior primary, but that profile is inactive and not a healthy baseline.

Next: ROUTER-AUTO-TEST-PLAN-2026-10-16.md. Require agreed independent recovery/test window and fresh policy/journal/client exit checks before outage. Historical original_restored=false is not retroactively certified. Full native cascade/deployment remain separate unexecuted acceptance stages.
