# Verified router and installation · 15 October 2026

[Russian](TESTED-ENVIRONMENT.ru.md) · [Machine-readable snapshot](tested-environment-2026-10-15.json)

These values were read from the **running router**, not inferred from the package's `Architecture: all` field. This is evidence for one tested configuration, not a compatibility guarantee for every GL.iNet/OpenWrt device.

| Item | Exact observed value | Source |
|---|---|---|
| Manufacturer / full model | GL.iNet GL-MT6000; product family Flint 2 | GL.iNet System → Overview; board API |
| Board identifier | `glinet,gl-mt6000` | `system.board` |
| Processor reported by firmware | `ARMv8 Processor rev 4`; 4 cores shown in panel | board API; GL.iNet Overview |
| OpenWrt target | `mediatek/mt7986` | board API |
| Package architecture | `aarch64_cortex-a53` | installed system packages |
| GL.iNet firmware / Admin Panel | **4.11.0** | GL.iNet header and System → Upgrade |
| Firmware type | **release** | GL.iNet System → Upgrade |
| Panel field “Update Time” | `2026-09-24 07:49:08 (UTC+00:00)` | GL.iNet System → Upgrade |
| OpenWrt distribution | **OpenWrt 21.02-SNAPSHOT** | board API; GL.iNet Overview |
| Full OpenWrt revision | **r15812+1095-46b6ee7ffc** | board API; GL.iNet Overview |
| Full distribution description | `OpenWrt 21.02-SNAPSHOT r15812+1095-46b6ee7ffc` | board API |
| Running Linux kernel | **5.4.238** | board API; GL.iNet Overview |
| Installed kernel package | `5.4.238-1-d4a7d36962bb6218ebd94bf040ac560e` | installed package database |
| LuCI branch | **LuCI openwrt-21.02 branch** | `/usr/lib/lua/luci/version.lua` |
| LuCI UI / luci-base | **git-22.335.71649-0ecaf74** | LuCI version file and installed package |
| libc package | `1.1.24-3` | installed package database |
| System-visible RAM | `1,037,365,248 bytes` = **989.31 MiB** | `system.info.memory.total` |
| Storage total displayed in panel | **7.28 GB** | GL.iNet Overview; UI units retained |
| Application package installed | **homensai-auto-vpn 0.2.0-alpha2-1**, architecture `all` | installed package database |
| Running application agent | **0.2.0-alpha2**, mode `monitor` | application status API |
| Embedded style | **HomenS.AI Style 1.14.3** | build manifest; packaged resources |

“Update Time” is copied as displayed. Its meaning was not independently established; it is **not** labelled here as firmware compilation time or the date this physical router was flashed. A separate vendor build identifier and hardware PCB revision were not obtained. The board API did not supply a root filesystem type. Those fields remain unknown rather than guessed.

## LuCI and supporting packages

LuCI is a collection of packages. The metapackage version is not interchangeable with the UI/base version.

| Package | Installed version |
|---|---|
| `luci` metapackage | `git-20.074.84698-ead5e81` |
| `luci-base` | `git-22.335.71649-0ecaf74` |
| `luci-mod-admin-full` metapackage | `git-19.253.48496-3f93650` |
| `luci-mod-status` | `git-22.089.70019-d4f0b06` |
| `luci-mod-system` | `git-22.264.46189-30ba277` |
| `rpcd` | `2022-02-19-8d26a1ba-1` |
| `rpcd-mod-luci` | `20210614` |
| `uhttpd` | `2021-03-21-15346de8-2` |
| `uhttpd-mod-ubus` | `2021-03-21-15346de8-2` |
| `python3` / `python3-base` | `3.9.15-1` |
| `openvpn-openssl` | `2.6.12-1` |
| `wireguard-tools` | `1.0.20210223-2` |
| `base-files` | `1453-r15812+1095-46b6ee7ffc` |
| `gl-sdk4-ui-core` | `git-2026.264.27863-0a182fe-1` |
| `gl-sdk4-utils` | `git-2026.253.06119-9584225-1` |

## What was actually installed and checked

- The versioned application ipk was installed through the router's authorised native opkg interface. The upgrade to **0.2.0-alpha2-1** completed with exit code **0**.
- A fresh installed-package query confirms that exact version. A live status query independently reports agent **0.2.0-alpha2**, mode **monitor**, and no service error.
- The monitor found **12 existing profiles**, with **3 connected**. Two OpenVPN and one WireGuard passed router-originated IPv4 HTTPS/DNS probes during the checks. This does not prove every configured inactive server works.
- Interface traffic and activity accumulators were observed. Telegram remained enabled with a **60-minute** interval and a recorded successful delivery. No bot credentials or recipient identifiers are included here.
- **33 local unit tests** passed, plus JavaScript syntax and EN/RU visual fixture checks. Fonts/style assets were checked for byte preservation in the package. Fixture images are synthetic, not live-router evidence.

## Boundaries

Native automatic VPN switching is **not implemented**: the running status reports `native_apply=false`. No live switch, rollback, power-loss, flash endurance, LAN-route or IPv6 validation is claimed. Full visual verification of the complete live LuCI settings/wizard after the browser-session issue remains incomplete; the branded UI was tested separately on a fixture.

This exact vendor OpenWrt 21.02 configuration must not be silently equated to generic OpenWrt 24.10 or another router model. No firmware update, factory reset, network/firewall change or package removal was performed for this inventory.

Serial number, device ID, MAC addresses, host identity, network addresses, keys, tokens, credentials, VPN server names and full raw configuration/log dumps are intentionally absent from this public record.
