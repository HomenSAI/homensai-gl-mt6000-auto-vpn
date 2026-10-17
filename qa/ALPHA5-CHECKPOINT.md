# Alpha5 local candidate — 2026-10-16

## Verified scope

- Debian: 202 Python tests pass; five Node suites passed for the recovery correction (Auto has 15 state/confirmation invariants).
- Actual isolated x86 OpenWrt 21.02.7: alpha5 package installed; native auto remains disabled; network/firewall exports unchanged.
- Actual LuCI browser: English -> Russian -> English selection changes the URL and rendered headings/menu; English was restored.
- Sidebar sections verified: channels, operator tests, statistics, ranking, monthly traffic, service monitor, events and overview. Settings exposes system, Telegram and recovery wizards.
- Wizards were opened and cancelled without saving. Telegram token field was blank; no delivery was attempted.
- Logo/author link targets https://homensai.com. Version is shown in the upper right.
- Alpha4 VM final evidence is stored separately: 194 tests passed, exact release package hash reproduced, network/firewall unchanged.

## Artifact

Local candidate: homensai-auto-vpn_0.7.0-alpha5-1_all.ipk
Size: 425976 bytes
SHA256: a14d1c6bae2be64eb398fa8873b2cabb53589d988655ce93cb93982fbb34cd6a

A new dashboard26 module URL avoids reusing the alpha4 dashboard25 URL. Previous VM page failed with uci/get permission denied while the installed alpha4 file already lacked a raw form. The page opened after upgrading to a fresh module URL and logging in again, without adding UCI permissions. Those combined actions do not establish which cache/session component was solely responsible.

## Not yet accepted

The full alpha5 guest Python suite passed: 202 tests in 68.269 guest seconds; exact candidate package hash reproduced, network/firewall unchanged, native Auto disabled. Receipt: openwrt-vm-alpha5-final.json. Neither this VM nor its inactive synthetic profiles proves real GL.iNet VPN switching. Full hierarchy cascade, inactive-profile activation, native-worker coordination, IPv6 and warm reboot remain open. No physical-router installation or new GitHub publication is authorized now. This is a local prerelease candidate, not a production-readiness declaration.
