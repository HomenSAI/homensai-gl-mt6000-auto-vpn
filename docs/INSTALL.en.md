# Installation and upgrade0.9.0

[Current status](CURRENT-STATUS.md) · [Quick start](AUTO-QUICKSTART.en.md) · [Terms](../DISCLAIMER.md)

1. Verify actual model/firmware. Continuous mode is tested on the prepared MT3000/4.11.0. Keep independent management access. Architecture:all does not mean universal compatibility.
2. Download `homensai-auto-vpn_0.9.0-1_all.ipk` and its `.ipk.sha256` from the same [release](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0). Verify SHA256 with `sha256sum <file>` or PowerShell `Get-FileHash <file> -Algorithm SHA256`. Stop on a mismatch.
3. Preserve a private, verified configuration/statistics backup. It may contain VPN keys, passwords and a Telegram token; never publish it.
4. Before upgrading, use ordinary Stop and wait for confirmed completion. If Stop/rollback is unconfirmed, do not bypass installation refusal or use force flags.
5. Install the application through LuCI → System → Software → Upload Package, or ordinary `opkg install /tmp/homensai-auto-vpn_0.9.0-1_all.ipk`. Never Flash Firmware. Use matching vendor dependencies:python3,lua,lua-cjson,libuci-lua,ip-full,ubus,rpcd,luci-base,ca-bundle. Do not replace feeds or mass-upgrade packages.
6. Open Services → HomenS.AI Auto VPN and refresh Ctrl+F5. Verify version 0.9.0 and advancing monitor data. Resolve a monitor error before starting Auto.
7. First entry: accept the agreement, read the illustrated explanation, press OK and review the eight setup steps. English/Russian preview is immediate. [Examples](FIRST-RUN-SETUP.md). Saving setup never starts Auto.
8. MT3000 needs separately verified [preparation](ROUTER-PREPARATION.md). Do not blindly copy old acceleration/DNS commands. Actual platform checks remain authoritative; choosing a model is not preparation.
9. In Overview check the saved pair, press Auto once and wait for actual readiness (about a minute on the tested router). Router/application restart requires explicit Start again. Read exact refusal codes; never reset budgets or change credentials to hide a failure.

The [router-test-kit](../router-test-kit/README.md) checks package/installation; that alone does not establish LAN connectivity. External client, IPv6, physical power and24-hour soak remain on the [roadmap](ROADMAP.md). Uninstall normally after confirmed Stop; preserve a private copy of needed settings/history.
