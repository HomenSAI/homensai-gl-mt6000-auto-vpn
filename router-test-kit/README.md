# HomenSAI Auto VPN router test kit (monitor-only, Auto OFF)

> ## ⚠ Experimental software: use at your own risk
>
> HomenS.AI Auto VPN is an **experimental alpha release** for the GL.iNet GL-MT6000. It can interrupt your internet connection and it changes router VPN settings. It is provided **"AS IS", without warranty of any kind** (MIT License). **You install and use it entirely at your own risk and responsibility.** Make a backup first and keep another way to reach the internet and the router. Read the full [terms of use](../DISCLAIMER.md). The program shows the same terms the first time you open it and does not allow Auto until you accept them.

Package: `homensai-auto-vpn_0.8.0-alpha17-1_all.ipk`, 562624 bytes,
SHA256 `6a296290e3192755abb2dc3018dc629564bce1f6139b25063278c3cbe374df9b` (alpha4: plain-language texts, Auto prerequisites checklist, regrouped Settings; checked by isolated CI only, never run on a router).
Target: GL.iNet GL-MT6000 / Flint 2, firmware 4.11.0. Experimental alpha: not a production release.

Phases 1-2 below install and verify the **monitor**; they do not enable Auto, change routes, DNS, firewall or
acceleration, and never restart network services. Phase 3 makes the Auto button work and DOES switch VPN routes briefly.

## Before you start (5 minutes)

- Keep a second way to reach the internet and the router that does NOT depend on this router (phone hotspot, other router, console).
  The installation does not interrupt traffic, but you need this if anything goes wrong.
- The router's current package may be 0.7.0-alpha7-2 (last known). The upgrade 0.7 -> 0.8 has been tested only in a virtual OpenWrt.
- Backups contain secrets (VPN configs, Telegram token). Keep them private; never upload them.

## Steps (PowerShell on your PC; replace `ROUTER` with the router LAN address)

```powershell
cd C:\homensai\homensai-gl-mt6000-auto-vpn\router-test-kit

# 0. Verify the package on the PC
(Get-FileHash .\homensai-auto-vpn_0.8.0-alpha17-1_all.ipk -Algorithm SHA256).Hash   # must equal the SHA256 above (case-insensitive)

# 1. Upload kit (OpenWrt dropbear needs scp -O)
scp -O 01-preflight.sh 02-install.sh 03-verify.sh 04-uninstall.sh 05-emergency.sh homensai-auto-vpn_0.8.0-alpha17-1_all.ipk root@ROUTER:/tmp/

# 2. Private full configuration backup, streamed to the PC (use cmd /c: PowerShell redirection would corrupt binary data)
cmd /c "ssh root@ROUTER ""tar czf - /etc/config /etc/homensai-vpn /etc/glversion"" > ..\private\router-backup.tgz"
#    The folder ..\private is ignored by Git. Check the file is >100 KB.

# 3. Preflight (read-only). Must end with READY
ssh root@ROUTER "cd /tmp && sh 01-preflight.sh"

# 4. Install (monitor only)
ssh root@ROUTER "cd /tmp && sh 02-install.sh /tmp/homensai-auto-vpn_0.8.0-alpha17-1_all.ipk"

# 5. Verify (wait up to 90 s for the first sample). Must end with RESULT: PASS
ssh root@ROUTER "cd /tmp && sh 03-verify.sh wait"
```

If step 5 reports `monitor processes: 0`, open LuCI -> Services -> HomenS.AI Auto VPN -> Settings -> **Start monitor**
(or `ssh root@ROUTER "ubus call homensai-vpn monitor_control '{\"enabled\":true}'"`), then repeat step 5.

## First start: accept the terms

The first time you open Services -> HomenS.AI Auto VPN a full-page screen shows the experimental-software terms ([DISCLAIMER.md](../DISCLAIMER.md)). Tick both boxes and press **Accept and continue**. Until you do, the controller refuses to switch anything and Auto cannot be started.

## What to look at in LuCI

Services -> HomenS.AI Auto VPN: version `0.8.0-alpha17` top right; Overview shows your existing profiles, health lamps
and the Auto button (leave it OFF). Run the System setup wizard only if you want names/channels/priorities.
After an upgrade sign out of LuCI and back in (new ACL), and hard-refresh the browser (Ctrl+F5).

## Suggested monitor-only test (about 1-24 hours)

1. Leave it running. Look at it periodically: `ssh root@ROUTER "sh /tmp/03-verify.sh"` should keep passing (status fresh, one process).
2. Note the memory/CPU effect: `ssh root@ROUTER "top -bn1 | head -15; ps w | grep homensai"`.
   The native supervisor also runs (diagnostics every 5 s) even with Auto OFF; its CPU cost on hardware is not yet measured, so please report it.
3. Check the profiles you actually use are listed, show healthy only when connected, and the statistics grow.
4. Save the report: `scp root@ROUTER:/tmp/homensai-kit/preflight.txt .` (contains no secrets).

## Roll back / remove

- Stop only the monitor: LuCI Settings -> Stop monitor, or `ssh root@ROUTER "/etc/init.d/homensai-vpn stop"`.
- Remove the application (config and history are kept): `ssh root@ROUTER "sh /tmp/04-uninstall.sh"`.
- Go back to the previous version: reinstall the earlier `.ipk` from `..\releases\` with `opkg install --force-downgrade <file>`
  after Auto is OFF; or restore only `/etc/config/homensai_vpn` from the backup.
- If LAN clients lose internet: read `EMERGENCY.md`.

## Troubleshooting

| Symptom | Action |
|---|---|
| `ubus ... status` not found right after install | `/etc/init.d/rpcd reload`, wait 10 s, sign in to LuCI again |
| LuCI shows old page or 404 for dashboard JS | Ctrl+F5; the package invalidates its LuCI caches, a stale browser may remain |
| `running agent '0.7...'` in verify | `/etc/init.d/homensai-vpn restart` (only own service) |
| opkg printed an error but exit 0 | Trust `03-verify.sh`, not the exit code |
| fingerprint CHANGED | A VPN reconnect can change routes. Compare with `ip route`; the package itself never writes routes |

## Phase 3: make the Auto button work (bounded switching; short interruption)

The Auto button is accepted only after a LAN trial has passed for the chosen primary/reserve pair. The Overview page now
shows a checklist with the exact missing step. Do this only in a window you chose, with another way to the internet.

Before: Phase 2 PASS; both VPN profiles connected in GL.iNet VPN Dashboard (two general all-traffic rules, Kill Switch on,
direct-internet fallback off, IPv6 off, HNAT/flow offload off); a Windows computer on the LAN with PowerShell 7 connected
by cable; the pre-start backup saved on your PC; `05-emergency.sh` copied to the router.

1. LuCI -> Services -> HomenS.AI Auto VPN -> Settings -> **1 System**: choose primary and a different reserve,
   tick "accept session reconnection", review, save. Then **Start monitor** if needed.
2. Overview: read the checklist. Every step except "LAN trial passed" must be green. A red technical item lists
   the exact router condition (for example HNAT or IPv6) with a plain explanation; fix it in the GL.iNet settings.
3. Settings -> **Download LAN helper** (`client-test.ps1`). Run on the cable-connected computer:
   `pwsh -NoProfile -File .\client-test.ps1 -Router http://<router-ip>:8080/ -CheckOnly` (read-only; the default router
   is http://192.168.8.1:8080/). If Wi-Fi is your normal path and the cable is only for the test, add
   `-CableInterface <Ethernet ifIndex>`. Then run it without `-CheckOnly`; the window defaults to 10 minutes
   (`-Until '<ISO time with offset>'` to change it, see docs/CLIENT-TRIAL.md). It asks for the router password locally and
   for you to type TEST before it starts.
   It switches to the reserve, verifies DNS, HTTPS and the exit IP from the LAN, then returns. Keep the helper running:
   it keeps confirming for the rest of the window, and closing it requests Stop. It changes Windows routing temporarily and
   removes it in `finally`.
4. When the trial passes, the checklist turns fully green ("Ready to start"). Press the round **Start** button: the
   controller then watches the primary, and on three confirmed failures switches to the reserve. Each automatic switch
   still needs the helper running on the LAN computer to confirm it; without it the router rolls back after 90 s.
   The window lasts at most 4 hours and 3 attempts; then start a new trial.
5. Press **Stop** (or the helper's Stop) to end Auto; verify the primary exit and LAN internet. If a state like
   STOPPED-ON-RESERVE or a retained guard appears, follow `EMERGENCY.md`.

Known limits (honest): untested on the physical router in this repository; held-reserve exit is manual; the confirmation
is made by the helper you run, not cryptographically bound to the LAN computer; continuous unattended operation is not supported.
