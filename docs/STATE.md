# Project state

Updated 2026-10-16, Europe/Berlin. Keep physical-device evidence, virtual OpenWrt evidence and synthetic UI fixtures distinct.

## Physical device — historical record only

Last installed application recorded in this task: 0.6.0-alpha5 on GL.iNet GL-MT6000 / Flint 2, GL.iNet 4.11.0, OpenWrt 21.02-SNAPSHOT r15812+1095-46b6ee7ffc, kernel 5.4.238, Python 3.9.15, LuCI git-22.335.71649-0ecaf74. This work window did not query or change the device.

Previous bounded IPv4 transitions and rollback were demonstrated between two already-connected catchall VPN profiles. This is not acceptance of arbitrary hierarchy, unattended production, IPv6 or power-loss recovery. The historical CLIENT-CABLE-NOT-LOCAL and browser HTTP 403 causes remain unresolved. See the timestamped WORKLOG and TESTED-ENVIRONMENT.en.md.

## Current local candidate

0.7.0-alpha2: sidebar dashboard25/ui13, English default with optional Russian, Auto state/power control, system/Telegram wizards, calendar reports, bound speed tests with conservative quotas, daily WAN/VPN accounting, read-only hierarchy recommendations and guarded monitor lifecycle control. Speed testing is off by default. Monitor start is separate from native Auto start. Native switching remains bounded and client-certified.

No router installation is authorized now. Continue local Git/Gitea first, then the identical reviewed GitHub tree; do not deploy without a new device window.

## Virtual acceptance

Actual OpenWrt 21.02.7 x86/64 under QEMU TCG inside isolated Docker, kernel 5.4.238 / Python 3.9.16. Installation, typed RPC, real UCI writer, profile-metadata save, monitor start/stop/fresh data, configuration preservation and own-monitor process recovery passed. The guest and Debian suites each passed 169 tests. Exact scope and unresolved warm-reboot behavior: ../qa/OPENWRT-VIRTUAL-REPORT.md.

The native adapter refuses this generic board and missing vendor environment. No real VPN tunnel transition was performed in this virtual acceptance. Do not equate the 256 read-only hierarchy combinations with native switching.

## Remaining

- Complete actual LuCI forms/browser acceptance and all responsive sections; current browser language/layout checks use a visibly labelled synthetic fixture.
- Operator fault button with independent cleanup, native hierarchy adapters, safe inactive-profile activation and vendor writer coordination.
- Explicit application of ranked priorities and full recovery-settings wizard.
- Native executor crash, IPv6, router reboot and physical power-loss acceptance in an authorized device window.
- Telegram delivery acknowledgement and calendar reports against an approved destination; local tests do not send messages.

No full production-readiness claim is justified.
