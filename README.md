# HomenS.AI Auto VPN

[Русский](README.ru.md) · [English](README.md)

HomenS.AI Auto VPN watches two existing OpenVPN or WireGuard connections on a GL.iNet router. It checks whether the internet works through each connection, switches to a verified reserve when the primary fails, and follows the selected rule for returning to the primary. It also shows check history, traffic, speed measurements, Help and interactive training.

Author and copyright holder: **Serhii Khomenko / HomenS.AI** — [homensai.com](https://homensai.com).

**License:** [HomenSAI Personal & Commercial Source License v1.0](LICENSE) — source-available, not open source.

In short: free for private, non-commercial use of the unmodified software; business/organizational use requires a separate paid written license ([commercial licensing](COMMERCIAL-LICENSING.md), info@homensai.com). Modification or redistribution requires prior written consent. The license text governs.

The documented continuous Auto setup is the dedicated **GL-MT3000 with GL.iNet firmware 4.11.0**. Continuous mode on the MT6000 has not been accepted. The package architecture `all` does not qualify other hardware or firmware.

Choose an explicitly named version from [GitHub Releases](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases). Download its `.ipk` and checksum from that release. The router-test-kit is in the source archive for the same tag. Follow the [installation guide](docs/INSTALL.en.md): identify the intended router, verify an encrypted backup, stop Auto before upgrading, check the package hash, install the application and verify it. The `.ipk` is an application package, not router firmware. First-run terms are accepted by the person using it.

In the application, choose the primary and reserve VPNs and review the switching rules. Auto starts only through its control and the current readiness checks. While Auto is running, the router checks both channels; a failed primary triggers a guarded switch only after the reserve passes its checks. Stop ends automatic operation through the normal recovery procedure. Switching can interrupt an existing connection.

Switching time: on the MT3000 the channel change is a fast switch (measured 30 Oct 2026: the rule change took 8-33 ms and new connections used the new channel within 0.5 s, no failed request, no firewall reload, no DNS restart). If the router state is unexpected, or the owner turns the option off in Settings, it falls back to the GL rebuild (20-33 s, whole switch 53-60 s). On the Python layer the total time from a fault is dominated by detection (about 105 s); the Lua line below detects faster.

Runtime (Lua line, 2.0.0-alpha24 test build): Python 3.9 is the base and fallback layer; Lua 5.1 runs the monitor and Auto as two services; a C module (`canon_c.so`) does the canonical JSON inside Lua and the same code runs in pure Lua by itself if the module cannot load or fails its self-probe; if the Lua services fail repeatedly, Auto falls back to the Python supervisor. The switch history is an append-only journal. Fast detection is on by default (`option lua_fast_detect '0'` turns it off). Measured on the MT3000: a manual switch is done in about 0.7 s (traffic after about 0.5 s); the automatic decision comes 26-28 s after an outage with fast detection at probe level 1 (58-88 s before), and traffic moves 1.3-1.6 s after the decision. [Numbers per layer](docs/MEASUREMENTS.en.md#8-runtime-pyramid-and-switch-times). [Charts per version](docs/MEASUREMENTS.en.md#charts-how-switching-got-faster-version-by-version): a manual switch went from 42.2 s (1.0.0-beta7) to 0.7 s; a primary failure from 153 s (0.9.1-alpha82) to 21–36 s.

Router-probed IPv4 checks and actual switching have dedicated MT3000 evidence. That does not establish external LAN-client acceptance, a 24-hour soak, recovery after a physical power cut (an instant-reboot simulation in the middle of a switch recovered by itself), IPv6 acceptance or MT6000 continuous mode. The [current status](docs/CURRENT-STATUS.md) distinguishes source changes, tests, installed versions and published releases.

The response shown for each VPN is measured one way, chosen in Settings and shared by cards, graphs and statistics: by default a ping to 1.1.1.1 (or 8.8.8.8 / 9.9.9.9) through the tunnel, or alternatively the mean of three Google, Cloudflare and Wikipedia website checks. A website number requires all 3/3 responses; incomplete checks show a gap and coverage. Website timing includes fresh DNS, TCP, TLS and HTTP headers, not full page rendering. An optional comparison mode also measures the other methods, but switching uses only the chosen one. These are router-originated test requests, without observing personal traffic. On Overview a probe level 1-5 sets how often the channels are checked, with an optional automatic boost after a failed check. A manual channel switch does not turn Auto off: Auto keeps watching the chosen channel. [Formula and measurement scope](docs/WEBSITE-RESPONSE.md).

[Current guide](docs/CURRENT-STATE.en.md) · [Built-in Help](docs/BUILTIN-HELP.en.md) · [Training](docs/TRAINING.en.md) · [Error codes and remedies](docs/ERROR_CODES.md) · [Documentation index](docs/DOCUMENTATION-INDEX.md)

Release history is in the [release notes](releases) and dated verification reports. [HomenSAI Personal & Commercial Source License v1.0](LICENSE) · [Licensing guide](LICENSING.md) · [Commercial licensing](COMMERCIAL-LICENSING.md) · [Terms](DISCLAIMER.md).
