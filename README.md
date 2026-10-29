# HomenS.AI Auto VPN

[Русский](README.ru.md) · [English](README.md)

HomenS.AI Auto VPN watches two existing OpenVPN or WireGuard connections on a GL.iNet router. It checks whether the internet works through each connection, switches to a verified reserve when the primary fails, and follows the selected rule for returning to the primary. It also shows check history, traffic, speed measurements, Help and interactive training.

Author and copyright holder: **Serhii Khomenko / HomenS.AI** — [homensai.com](https://homensai.com).

The documented continuous Auto setup is the dedicated **GL-MT3000 with GL.iNet firmware 4.11.0**. Continuous mode on the MT6000 has not been accepted. The package architecture `all` does not qualify other hardware or firmware.

Choose an explicitly named version from [GitHub Releases](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases). Download its `.ipk` and checksum from that release. The router-test-kit is in the source archive for the same tag. Follow the [installation guide](docs/INSTALL.en.md): identify the intended router, verify an encrypted backup, stop Auto before upgrading, check the package hash, install the application and verify it. The `.ipk` is an application package, not router firmware. First-run terms are accepted by the person using it.

In the application, choose the primary and reserve VPNs and review the switching rules. Auto starts only through its control and the current readiness checks. While Auto is running, the router checks both channels; a failed primary triggers a guarded switch only after the reserve passes its checks. Stop ends automatic operation through the normal recovery procedure. Switching can interrupt an existing connection.

Router-probed IPv4 checks and actual switching have dedicated MT3000 evidence. That does not establish external LAN-client acceptance, a 24-hour soak, recovery after a power cut, IPv6 acceptance or MT6000 continuous mode. The [current status](docs/CURRENT-STATUS.md) distinguishes source changes, tests, installed versions and published releases.

The response shown for each VPN is measured one way, chosen in Settings and shared by cards, graphs and statistics: by default a ping to 1.1.1.1 (or 8.8.8.8 / 9.9.9.9) through the tunnel, or alternatively the mean of three Google, Cloudflare and Wikipedia website checks. A website number requires all 3/3 responses; incomplete checks show a gap and coverage. Website timing includes fresh DNS, TCP, TLS and HTTP headers, not full page rendering. An optional comparison mode also measures the other methods, but switching uses only the chosen one. These are router-originated test requests, without observing personal traffic. On Overview a probe level 1-5 sets how often the channels are checked, with an optional automatic boost after a failed check. A manual channel switch does not turn Auto off: Auto keeps watching the chosen channel. [Formula and measurement scope](docs/WEBSITE-RESPONSE.md).

[Current guide](docs/CURRENT-STATE.en.md) · [Built-in Help](docs/BUILTIN-HELP.en.md) · [Training](docs/TRAINING.en.md) · [Error codes and remedies](docs/ERROR_CODES.md) · [Documentation index](docs/DOCUMENTATION-INDEX.md)

Release history is in the [release notes](releases) and dated verification reports. [MIT License](LICENSE) · [Terms](DISCLAIMER.md).
