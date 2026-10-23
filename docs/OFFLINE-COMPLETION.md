<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Offline completion: alpha6

## Scope

All six locally testable work areas are implemented and checked. This does not enable a new native adapter, resume QEMU, deploy to the physical router or certify unattended production. The full cascade is a pure executable model; existing on-device route permissions remain unchanged.

## Work completed and why

| Area | Change | Purpose / evidence |
|---|---|---|
| Cascade model | Same-channel server -> other channel -> other protocol; exhaustion; per-hop rollback; original-root return | Keep the original policy across multiple hops; 20 focused tests and 256 seeded series |
| Algorithm protection | Monotonic time, bounded lease/attempts, stale/unbound/unknown health, phase-specific order ownership, RPC/worker refusal, stop and restart reconciliation | Unknown state cannot authorize writes or silently resume Auto |
| Interface | Selected healthy first, failed last, verified freshness colors, stable sort/filter keys, mobile widths | 54 browser checks: nine pages x EN/RU x 360/768/1280; no global horizontal overflow |
| Wizards | Selected primary/reserve must remain monitored; control characters/ranges rejected; reviewed save, error/retry and single-flight commit | A disabled reserve or double click cannot become a successful setup |
| Statistics | Regressive timestamps cannot double-count duration/bytes; duplicates are idempotent; calendar/DST tests | Seven boundary/property tests, including 200 seeded 60-step series |
| Git/package | Shared SDK/IPK byte-and-mode selection; bounded nested TAR/IPK/ZIP scan; offline launcher and exact-SHA Gitea relay | Preserve author assets, avoid obsolete UI payloads, refuse secret-bearing archives and unsafe staging |

## Reproduce without any router

```powershell
./scripts/test-local.ps1
```

This runs a disposable Linux container from an existing local image, with external networking disabled and this checkout mounted read-only. The QEMU router is not involved. A failure returns a failing PowerShell result (verified with injected exit 17).

For optional visual work:

```powershell
python qa/ui_preview_server.py
```

Open http://127.0.0.1:18884/qa/ui-preview/index.html?lang=en. Every value is synthetic and the banner states that explicitly. The server binds loopback, serves only fixture/UI asset trees and refuses POST and symlink escapes. Stop that server when finished; it is not the router service.

For reproducible scenario output, run `python qa/run_cascade_scenarios.py` inside Linux or host Python (the pure model has no Linux-only imports).

## Save and release

Commit reviewed explicit paths, then run `./scripts/save-gitea.ps1`. The command relays exact committed objects through the existing verified Docker SSH transport. It does not disable host checking or copy keys. Direct Windows SSH previously refused an unknown local Gitea host key; that failed before upload. GitHub remains withheld pending permission/history reconciliation.

After a meaningful checked release tag exists locally, use `./scripts/save-gitea.ps1 -Tags v0.7.0-alpha6`. No force, deletion or tag overwrite is used. Private bundles are retained under .git/handoff and independent storage for recovery.

SDK staging uses host Python 3 and refuses a nonempty destination. Tests verify identical names, bytes and file modes to the actual IPK. A complete external OpenWrt SDK build was not run and is not claimed.

## Still requires separate acceptance

Actual GL.iNet worker arbitration, native multi-hop execution, inactive-profile activation, LAN/DNS/Kill Switch, acceleration, IPv6, reboot/power loss and unattended operation need their authorized device test matrix. QEMU remains paused; its earlier warm reboot failure remains unresolved. No local model or screenshot replaces those results.
