# Project state

Updated: 2026-10-15, Europe/Berlin. This file separates device evidence, laboratory evidence and unfinished product work.

## Device and software

- GL.iNet GL-MT6000 / Flint 2; GL.iNet firmware 4.11.0; OpenWrt 21.02-SNAPSHOT r15812+1095-46b6ee7ffc; kernel 5.4.238; aarch64_cortex-a53; Python 3.9.15.
- LuCI base git-22.335.71649-0ecaf74. Exact recorded environment: TESTED-ENVIRONMENT.en.md and the redacted JSON passport.
- Installed application: 0.5.0-alpha12. Version and English formatter verified on the device after installation; native_enabled=0, journal ROLLED-BACK, own guard absent. HomenS.AI Style core 1.14.3 assets are pinned and retain their original licences.
- The sidebar dashboard15/ui13 is a local candidate under development; it is not yet the installed router interface. Its fixture is explicitly synthetic and does not verify a real LuCI settings form.
- No router packages were removed. mtkhnat remains loaded; runtime hook disable was verified. Kill Switch remained enabled and direct-WAN fallback disabled during accepted tests.

## Confirmed live results

- Anonymous UCI sections now use semantic identities excluding generated .name/.index metadata. Reordering resolves current names and checks the stable order/fingerprint after commit. Real changes and indistinguishable duplicates refuse application.
- 18:21:20–18:22:03: client-confirmed transition to reserve and original-path return passed.
- 18:23:37: controlled primary-path traffic failure; 18:24:53 automatic APPLYING; 18:25:20 COMMITTED/CLIENT-CONFIRMED. Approximately 76.15 seconds to apply start and 102.43 seconds to reserve confirmation; these are not continuously measured application downtime.
- 18:26:07: independent fault timer removed its test rule. 18:27:26: independent rollback completed. Separate client checks confirmed original exit/order, DNS/HTTPS and no guard. The first helper completion reported CLIENT-CHECK-FAILED and is not counted as a successful helper exit.
- A second bounded automatic observation window was started until 19:07:56. Its final helper check reported CLIENT-CABLE-NOT-LOCAL. At 19:09 the router independently reported STOPPED, journal ROLLED-BACK and guard absent. Both Windows adapters were up; the precise client-route-change cause remains unknown. Own automation configuration was then saved disabled.
- NordVPN on Windows blocked port-53 replies through its DNS Leak Protection WFP filter. The owner approved a temporary service stop; DNS immediately worked. The service was restarted after testing and Running was verified. Wi-Fi remained the default communications path, while only selected cable probes used temporary /32 routes.
- Successful network transition/rollback is a narrow two-connected-profile result. It does not certify production unattended operation, arbitrary topologies, inactive-profile startup, full IPv6 leak protection or physical power-loss recovery.

## Laboratory evidence

- 90 Python unit tests passed after the UCI identity correction. Windows SelfTest and cable CheckOnly passed. Six Telegram formatter/delivery tests passed after English-text changes; the updated formatter is installed and English default output was verified on device; a new live-delivery acknowledgement is not claimed.
- Historical model/stress reports are in qa/. Synthetic combinations and Docker child-process crashes are not router power failures or complete native driver acceptance.
- The old ab28c58 soak was deliberately stopped after discovery that a fake PID could reach real killpg. Tests now mock that syscall. Preserve that limitation with the old release evidence.

## Remaining work

1. Finish/deploy the sidebar UI using the pinned Style core; verify actual LuCI language switching, reload persistence, forms, sorting, operator controls and selected/failed-card order.
2. Complete system and Telegram-channel wizards, preserving secret-field exclusion and distinguishing supported modes from planned hierarchy.
3. Add an authenticated, bounded operator failure test with independent cleanup and real acceptance. The manually run timed failure script is not yet a shipped RPC/button.
4. Extend selection from the currently supported pair to server → channel → protocol only after native adapters and tests cover that hierarchy. Wi-Fi/Ethernet are uplinks, not VPN protocols.
5. Validate external-writer coordination, actual executor-crash recovery, IPv6 and broader device compatibility before calling the system production-ready.
6. Keep diagnostics, error histories, fixes and test reports in English. English is the first-entry UI default; optional Russian UI and installation guides are separate. Never translate operator-supplied profile/channel names automatically.

## Publication discipline

Canonical local Git/Gitea first, then an identical verified public GitHub tree. Public repository: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn. Do not publish private configuration, passwords, tokens, sessions, host fingerprints, exit IPs, device identifiers or packet/log captures. Published release tags remain immutable.
