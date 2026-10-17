# Installation and upgrades — monitor-only deployment

> ## ⚠ Experimental software: use at your own risk
>
> HomenS.AI Auto VPN is an **experimental alpha release** for the GL.iNet GL-MT6000. It can interrupt your internet connection and it changes router VPN settings. It is provided **"AS IS", without warranty of any kind** (MIT License). **You install and use it entirely at your own risk and responsibility.** Make a backup first and keep another way to reach the internet and the router. Read the full [terms of use](../DISCLAIMER.md). The program shows the same terms the first time you open it and does not allow Auto until you accept them.

[Russian](INSTALL.ru.md) · [Environment passport](TESTED-ENVIRONMENT.en.md) · [Next-stage evidence](NEXT-STAGE-RESULTS.md)

The current development candidate is **0.8.0-alpha8-1**. Use a published, verified
version and its matching checksum; a development branch or a passing model test
is not a production acceptance certificate. Local Gitea is primary. Public GitHub
publishes reviewed snapshots on its own preserved history; use the release asset and checksum, not an arbitrary branch build.

## Supported evidence and boundaries

The historical physical passport records GL.iNet **GL-MT6000 / Flint 2**, firmware
**4.11.0**, OpenWrt **21.02-SNAPSHOT r15812+1095-46b6ee7ffc**, Linux **5.4.238**,
architecture **aarch64_cortex-a53**, LuCI openwrt-21.02 / luci-base
**git-22.335.71649-0ecaf74**. It is a dated observation, not today's device query.
The last separately recorded physical checkpoint is alpha7-2 with Auto OFF;
alpha8 local evidence does not mean it was installed on that router.

Python **3.9.15** and Lua **5.1.5/CJSON** are checked in isolated Linux containers.
The UCI cursor in those contract tests is mocked. Generic x86 OpenWrt, a matching
vendor SDK build, proprietary GL.iNet workers and physical LAN/IPv6/offload behavior
are separate acceptance steps. Never force compatibility with another image/model.

## Steps

1. Confirm the model/firmware and local LuCI access. Keep an independent management
   path. Obtain a separately authorised window before device installation/testing.
2. Obtain `.ipk` and `.ipk.sha256` from the **same verified release**. For alpha8,
   the expected filename is `homensai-auto-vpn_0.8.0-alpha8-1_all.ipk`. Compare
   `Get-FileHash .\homensai-auto-vpn_0.8.0-alpha8-1_all.ipk -Algorithm SHA256`
   or `sha256sum homensai-auto-vpn_0.8.0-alpha8-1_all.ipk` with that release's
   checksum. Stop if the asset/checksum is absent or different.
3. Keep a **private** configuration/history backup and check available storage/RAM.
   Backups can contain secrets. Never upload them, bot tokens, sessions, passwords
   or VPN keys to GitHub, reports or AI chats.
4. Use original vendor package feeds only. Required packages are listed by the
   release metadata: python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd,
   luci-base and ca-bundle. Python can occupy much more space than the application.
   Do not replace feeds, mass-upgrade, force dependencies or remove shared packages.
5. LuCI → System → Software → Upload Package → review dependencies → Install.
   This is a software package, **never Flash Firmware**. Stop on an opkg error.
6. Services → HomenS.AI Auto VPN: verify the version at the top right and advancing
   timestamps. Settings → Start monitor enables observation; keep **Auto OFF**.
   A queued/accepted request alone is not proof that a service started.
7. Run the System setup wizard: choose existing registered primary/reserve profiles,
   display names, channels, priorities and monitored servers. Both selected profiles
   must remain enabled for monitoring. Review before saving. This does not import
   keys, start inactive VPNs or certify a new native transition.
8. Optional Telegram wizard: use **your own** bot, send `/start`, obtain the receiving
   chat/channel ID, enter its token **only in the local router form**, select interval
   or daily Europe/Berlin hour and weekly/monthly summaries. Save, test delivery and
   verify the actual last-success timestamp. A bot ID is not a personal chat ID.

English is the UI default; Russian controls are optional. Diagnostic/error codes
and export column names remain English. The logo links to https://homensai.com.

## Auto, statistics and diagnostics

The existing native controller supports only a separately certified bounded pair.
Start Auto can be refused by readiness, expired-window, HNAT/IPv6, worker or LAN
guards. Never remove those guards to make Start turn green. The new multi-hop
executor accepts **test doubles only** and is not wired to router service writes.

The LAN helper requires PowerShell 7. `-SelfTest` makes no network calls or route
changes. A real trial requires separate approval, the exact interface and the local
TEST confirmation. DNS uses a source-bound UDP socket; HTTPS is source-bound to the
same IPv4 address. Changed interfaces, stale/replayed proofs or wrong exits refuse
confirmation. This does not certify all application traffic or IPv6.

The diagram shows controller-selected state and uncertified candidate suggestions.
Green health requires fresh probes; connected/unknown/inactive are not measured
success. Recovery statistics use retained controller observations, explicit unknown
gaps and Europe/Berlin calendar boundaries. They are not full LAN uptime. Retry IDs
are local sequential analysis identifiers, not authentication sessions; backup
recovery can lose the newest observations. CSV exports whitelist fields and protect
spreadsheet formulas. Transition/failure exports follow the selected recovery period;
ranking is current and traffic exports contain retained monthly interface counters.

## Upgrade, rollback and stopping

Stop Auto and **verify** the reported restoration or explicitly retained reserve
before stopping monitoring/upgrading. A retained reserve is not a restored original
route. Never restart network/firewall or unrelated services as an installation step.

The new versioned migration contract preserves full private own-config options,
existing UCI section identities, names/priorities and statistics. Removed profiles
are retained disabled; migration/rollback clears Auto enablement. Private snapshot
conversion is implemented, but real UCI/package interruption acceptance remains
NEXT-24. Do not migrate from public/redacted inventory or hand-edit a checksum.

On 403, test a private window and clear **only the router's site data** if needed.
Do not weaken authentication/TLS, expose WAN administration or loop RPC restarts.
Record only the redacted code and time if access still fails.

Use the independent path if Stop/restoration cannot be confirmed. Removal needs a
separate owner decision: remove only the application, never auto-remove shared
dependencies. Configuration/history are intentionally retained; their deletion is
a separate decision. No unattended production claim follows from this guide.

## First start: the terms of use

The first time you open Services → HomenS.AI Auto VPN after installing, a full-page screen shows the [terms of use](../DISCLAIMER.md): the software is experimental, can interrupt your internet, changes router VPN settings, is provided "AS IS" and is used at your own risk. Tick both boxes and press **Accept and continue**. The acceptance (terms version and time) is stored on the router. Until it is stored the controller refuses to switch anything (`TERMS-NOT-ACCEPTED`) and Auto cannot be started. The same text stays available on the Help page. If you do not accept, remove the package (`opkg remove homensai-auto-vpn`).

## Installing with the router test kit

`router-test-kit/` contains a read-only preflight, an install script that checks the package hash, a verification script, an uninstall script and an emergency helper. Follow [router-test-kit/README.md](../router-test-kit/README.md): upload, private backup, preflight, install, verify. The package also installs `/usr/sbin/homensai-vpn-emergency`; the Help page explains every recovery step. Making Auto work needs a LAN trial with the helper (phase 3 of the kit) and is a separate, deliberate step with a short interruption.
