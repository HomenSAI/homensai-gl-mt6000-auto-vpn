<!-- doc-role: current -->
# Installation and upgrade

[Current source/delivered state](CURRENT-STATUS.md) · [Quick start](AUTO-QUICKSTART.en.md) · [Terms](../DISCLAIMER.md)

Use the [full AI prompt](AI-INSTALL.en.md) with an agent that actually has terminal/router access, or follow the manual sequence. A normal chat cannot install software. Never include secrets in the prompt.

## Select one immutable release

Recommended for the GL-MT3000 (main line since 01.11.2026): [v2.0.0-beta1](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v2.0.0-beta1), `homensai-auto-vpn_2.0.0-beta1-1_all.ipk`, 1453760 bytes, SHA256 `b27e1cc31612981fd051c817b82afb5cb31e346895f663162e61b3fada4e0076` — the Lua line (Lua services and the C JSON module by default, Python fallback); take its `.sha256` and the router-test-kit from the **same tag**. Owner live-test guide: [OWNER-LIVE-TEST.ru.md](OWNER-LIVE-TEST.ru.md).

Previous stable: [v0.9.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0), `homensai-auto-vpn_0.9.0-1_all.ipk`,769849bytes, SHA256 `7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a`. Obtain its checksum, verification JSON and **same-tag** router-test-kit.

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

Lua line (2.0.0-alpha packages): the package contains the Lua services and the C module `/usr/lib/lua/canon_c.so`; the Lua services need `lua`, `lua-cjson` and `libuci-lua` from step 6 and run by default since 2.0.0-alpha24 (`option lua_monitor '0'` / `option lua_auto '0'` return to the Python services). If the C module cannot load, the Lua code runs by itself. The first history write after an upgrade migrates `native-history.json` to schema 2 (a small state file plus `native-history.events.jsonl`) and keeps the old file as `native-history.v1.json`. To return to an older package: normal Stop, then `cp /etc/homensai-vpn/native-history.v1.json /etc/homensai-vpn/native-history.json`, then install the older package; events recorded after the migration are lost.

[LAN helper](LAN-HELPER.en.md) is optional for prepared router-probed Auto and mandatory for its separate client-confirmed trial. Read its mode boundaries. [Emergency/uninstall](../router-test-kit/EMERGENCY.md) are deliberate operations after verified recovery, not universal Internet repairs. A generic x86 VM may test monitor-only installation only in its explicitly marked isolated scope; never spoof hardware or bypass a real-device refusal.
