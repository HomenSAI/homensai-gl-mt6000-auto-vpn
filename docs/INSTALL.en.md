# Installation · 0.3.0-alpha1

[Русский](INSTALL.ru.md)

## Exact tested configuration

[Verified installation passport](TESTED-ENVIRONMENT.en.md): GL.iNet GL-MT6000 (Flint 2), vendor 4.11.0 release, OpenWrt 21.02-SNAPSHOT r15812+1095-46b6ee7ffc, Linux 5.4.238, aarch64_cortex-a53, LuCI openwrt-21.02 / luci-base git-22.335.71649-0ecaf74. Application 0.3.0-alpha1-1 was installed and the running monitor independently verified. Other combinations are not implicitly certified.

1. Confirm GL-MT6000, GL.iNet 4.11.0 / OpenWrt 21.02-SNAPSHOT and working local LuCI. Other models/releases are untested: assess compatibility; never force installation. This is a monitor, not firmware or a VPN subscription. Reuse existing VPN profiles.
2. Download `.ipk` and `.ipk.sha256` from the same version. Verify with PowerShell `Get-FileHash .\homensai-auto-vpn_0.3.0-alpha1-1_all.ipk -Algorithm SHA256` or Linux `sha256sum homensai-auto-vpn_0.3.0-alpha1-1_all.ipk`. Stop on mismatch.
3. Make a private configuration backup and check RAM/storage. Backups may contain VPN keys and Telegram tokens: do not upload them to AI chats/GitHub.
4. LuCI → System → Software: refresh the original vendor feeds. Dependencies: python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd, luci-base, ca-bundle. Full Python uses much more space than this small ipk. Do not replace feeds, mass-upgrade, force dependencies, flash firmware or delete existing packages.
5. Software → Upload Package → select ipk → review dependencies → Install. Never use Flash Firmware. Stop on opkg errors.
6. Services → HomenSAI Auto VPN: check the top-right version. A new installation is disabled. Enable monitoring, probe interval 30 seconds and checkpoint 900 seconds, Save & Apply. If needed, start only `homensai-vpn` via Startup; do not restart network/firewall/unrelated services.
7. Verify advancing timestamps and real connected-profile results. Do not launch inactive profiles. Test a LAN client's DNS/HTTPS separately with approval: router probes do not prove its path.
8. Optional Telegram wizard: create YOUR bot with BotFather, send /start, get YOUR personal chat ID (not the bot ID), enter token only in the router form, select report interval and enable. Save & Apply; verify actual last successful delivery. Never paste secrets into public issues, AI chats or screenshots.

UI starts in English; use the language selector. Edit display names in settings. Selecting a subset limits observation to that subset. Histogram history starts at installation; green/red/grey describe observed/failed/unknown time. Do not infer historic uptime or throughput. Checkpoints can lose the latest interval on power loss.

For 403/Session expired, test a fresh private window; if it works, clear only the router's site data. Do not disable access controls, expose WAN admin or repeatedly reload RPC. If still blocked, stop and collect redacted error/time. Missing menu requires compatibility/installation diagnosis, not reflashing. Never disable TLS verification for Telegram.

SSH is optional and requires independently verified host key and an existing authorised login. Read-only checks: `python3 /usr/lib/homensai-vpn/agent.py preflight`, `ubus call homensai-vpn status '{}'`. Do not publish raw dumps.

Stop by disabling monitoring or stopping only its Startup service. Upgrade after backup/checksum using Software. Automatic operation is not enabled by upgrading. Removal requires the owner's explicit decision: remove only `homensai-auto-vpn`; never auto-remove shared dependencies. `/etc/homensai-vpn` and `/etc/config/homensai_vpn` are retained intentionally; deleting history/config/secrets requires a separate decision.
