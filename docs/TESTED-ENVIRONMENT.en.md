<!-- doc-role: current -->
# Tested environment and limits

The authoritative current delivered version is [CURRENT-STATUS](CURRENT-STATUS.md). Source-candidate documentation is not acceptance of a new package. Each versioned receipt retains its own scope.

| Evidence | What it establishes | What it does not establish |
|---|---|---|
|Exact-source dual-runtime CI|The named committed code/tests and matching canonical artifact in the stated runtimes|Physical device, browser visuals or LAN|
|Source/DOM and synthetic browser personas|Guarded UI/validation behavior against frozen fixtures|Real firmware/VPN routing, autonomous external models|
|Actual isolated x86 OpenWrt VM|Its install/files/UCI/RPC/HTTP/kernel/lifecycle cases|A spoofed GL hardware pass or real external LAN|
|Named MT3000/4.11.0 receipt|That package's actual installed/served bytes, controlled operation and measured router IPv4 state|Every provider, MT6000 continuous mode, IPv6/KillSwitch/day-long/power-cut acceptance|
|Lua-line release notes, MT3000 (alpha22 and alpha23, 01.11.2026)|Install over the previous version with Auto on; an instant reboot (`sysrq-b`) during a switch recovered 2 of 2; 3-hour fault soaks on Lua and with the C module; manual and automatic switch times ([measurements](MEASUREMENTS.en.md#8-runtime-pyramid-and-switch-times))|A physical power cut, a 24-hour soak, external LAN, IPv6, MT6000, the alpha24 timing changes (3 s HTTPS wait, 45 s vendor settle)|
|LAN helper SelfTest/CheckOnly|The stated offline or prerequisite mode|A completed Internet/switching trial|

[Alpha13 delivery and preserved failures](VERIFICATION-ALPHA13-2026-10-24.md) is a versioned example. Its first60s VM reboot window failed; a longer bounded observation confirmed eventual fresh monitoring and preserved configuration. It is not a guaranteed startup SLA. [Alpha10 VM/prompt recipes](handoff/VM-AUDIT-2026-10-24.md) are historical, not the new source's acceptance.

External-LAN/IPv6/KillSwitch/native physical-browser visual and autonomous ChatGPT/Claude execution remain separate unless explicitly evidenced in a newer receipt. No matrix proves every possible network/firmware/power combination. [Roadmap](ROADMAP.md).
