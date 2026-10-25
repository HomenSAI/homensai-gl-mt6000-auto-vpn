<!-- doc-role: current -->
# Installation and upgrade

[Current source/delivered state](CURRENT-STATUS.md) · [Quick start](AUTO-QUICKSTART.en.md) · [Terms](../DISCLAIMER.md)

Use the [full AI prompt](AI-INSTALL.en.md) with an agent that actually has terminal/router access, or follow the manual sequence. A normal chat cannot install software. Never include secrets in the prompt.

## Select one immutable release

Stable default: [v0.9.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0), `homensai-auto-vpn_0.9.0-1_all.ipk`,769849bytes, SHA256 `7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a`. Obtain its checksum, verification JSON and **same-tag** router-test-kit.

For an explicitly chosen prerelease, use its own version/name/size/hash/evidence and same-tag scripts. This checkout's kit follows VERSION.json and may be newer than stable. Do not mix the branch kit with stable0.9.0 or downgrade a newer installed version. A source-candidate tag in VERSION.json does not by itself prove a server Release exists.

## Manual sequence

1. Verify the actual named router, firmware and management path/host key before credentials. A same-IP device through another adapter is not the target. Keep independent access; no silent host-network changes.
2. Inspect installed/running versions, pending work, writable filesystem/space and dependencies. Prepared continuous mode is qualified on documented MT3000/4.11.0; architecture `all` and a model selector do not qualify another platform. The install preflight requires20MiB free writable storage; runtime storage checks have their own smaller threshold.
3. Preserve a private supported configuration export plus necessary app data; encrypt it, protect the key separately, and verify archive/decrypt/read. No raw backups, tokens or VPN keys in Git/chat/releases.
4. For an upgrade, normal Stop must finish managed recovery/cleanup before opkg. ACK is not completion. Keep refused/retained outcomes; never force installation, delete journals/guards or reset budgets to bypass lifecycle checks.
5. Obtain and read `01-preflight.sh`, `02-install.sh`, `03-verify.sh` from the chosen tag. Verify package name/size/SHA256 locally and after transfer. `02-install.sh /tmp/<matching-package>.ipk` pins expected values; alternatively use the documented normal `opkg install` path. The package is an application, **not Flash Firmware**.
6. Install missing dependencies only from that firmware's original vendor feeds: python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd, luci-base, ca-bundle. Do not mass-upgrade or replace feeds; stop on ABI/signature/dependency conflicts.
7. Run `03-verify.sh wait`. Check package/runtime versions, advancing timestamps, services and actual served module/CSS against the verified payload where possible. An opkg exit0, cached page or green lamp alone is insufficient. A stale RPC registration may need a deliberate documented reload/login.
8. Open Services → HomenS.AI Auto VPN, refresh cache, and complete first-run terms/introduction/setup. The human accepts terms; existing acceptance of the same terms version is preserved. Saving setup never starts Auto or sends a Telegram test.
9. Separate [platform preparation](ROUTER-PREPARATION.md) from installation. Start Auto only for the requested outcome and current readiness. During an authorized upgrade that preserves previous Auto/channel, restore and verify that state through normal controls; report safe refusal if it cannot be restored.

[LAN helper](LAN-HELPER.en.md) is optional for prepared router-probed Auto and mandatory for its separate client-confirmed trial. Read its mode boundaries. [Emergency/uninstall](../router-test-kit/EMERGENCY.md) are deliberate operations after verified recovery, not universal Internet repairs. A generic x86 VM may test monitor-only installation only in its explicitly marked isolated scope; never spoof hardware or bypass a real-device refusal.
