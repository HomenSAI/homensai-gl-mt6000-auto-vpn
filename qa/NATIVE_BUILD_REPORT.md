# Native OpenWrt build verification

Historical report dated 2026-10-14. Build: homensai-auto-vpn 0.1.0-alpha1-1, Architecture all, monitor mode. Later device results are recorded chronologically in docs/WORKLOG.md.

23 Python tests passed: device/mark socket binding, refusing unverified routes, HTTPS quorum/DNS classification, excluding unknown probes from ranking, Europe/Berlin month boundaries, kernel-counter resets, ifindex/gaps, checkpoint/backup, permissions/symlink protection, bounded RPC, one mocked service cycle, reproducibility and IPK structure.

Separately, luac -p under Lua 5.1 passed for inventory and legacy LuCI controller in a disposable Docker container. The UCI fixture returned two existing profiles/interfaces while excluding injected passwords, private keys, token and private-file path.

node --check passed for the LuCI view; sh -n passed for init service and RPC wrapper. At this historical stage the view/RPC had not been verified on GL-MT6000. The embedded demonstration and native view are separate pages; the former does not prove compatibility of the latter.

Only Software/Installed access was checked on the live router. Upload Package was available, Python was not found, and dependency-feed availability was unverified. No upload/install/update-lists operation occurred during this stage. Authentication details and keys were excluded from the report.

The package passed a parser test and reproducible rebuild. Actual opkg/SDK installation was unconfirmed then. Source had native_apply=false and no routing write commands; native failover remained incomplete.
