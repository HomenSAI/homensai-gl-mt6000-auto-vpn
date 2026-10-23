# Tested environments —23 October 2026

Current continuous mode was tested on a dedicated GL.iNet GL-MT3000/Beryl AX, GL.iNet 4.11.0, OpenWrt 21.02-SNAPSHOT, mediatek/mt7981, kernel 5.4.211. Evidence is router-originated IPv4 DNS/twoHTTPS probes and actual route-policy selection. [Exact release evidence](RELEASE-0.9.0.md).

Historical MT6000/Flint2:GL.iNet 4.11.0, OpenWrt 21.02-SNAPSHOT, kernel 5.4.238; the15October passport remains in tested-environment-2026-10-15.json. It is not a current primary-MT6000 query or current continuous-mode acceptance on that device.

Isolated builds/checks use Python 3.11 and Python 3.9.15/Lua 5.1/CJSON. Generic x86/QEMU results are separate lab evidence. IPK Architecture:all describes interpreted files, not universal hardware compatibility; actual model/firmware/native-component checks still apply.

No independent LAN client, IPv6 failover,24-hour soak, physical power-cut or arbitrary other-firmware acceptance is claimed. [Current status](CURRENT-STATUS.md).
