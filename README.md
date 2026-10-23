# HomenS.AI Auto VPN

[English](README.md) · [Русский](README.ru.md) · [HomenS.AI / Serhii Khomenko](https://homensai.com)

**Release 0.9.0 — 23 October 2026.** A router application for monitoring existing OpenVPN/WireGuard profiles and automatic switching between a primary and a reserve VPN. Continuous two-channel Auto is tested on the prepared **GL.iNet GL-MT3000 / firmware 4.11.0**. MT6000 identification and historical monitoring/native results are separate evidence; the current continuous mode is not hardware-qualified on MT6000.

**Experimental software, MIT License, use at your own risk.** Switching can interrupt calls and sessions. Version 0.9.0 is a numbered release, not a claim of unattended production certification. Read [terms](DISCLAIMER.md) and [supported scope](docs/CURRENT-STATUS.md).

## Download and start

Download the matching `.ipk` and `.ipk.sha256` from [v0.9.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0). This is an application package, **not a firmware image**. Verify the checksum, preserve a private backup and [follow installation](docs/INSTALL.en.md). Do not force board/firmware/readiness checks.

First entry: agreement → two paragraphs and three diagrams explaining operation → OK → eight-step setup. English/Russian are available. Setup Help gives examples for every step. The green escape below Cancel/Next opens the dashboard with existing router settings unchanged; it does not save the draft, reset defaults or start Auto. Later changes belong in Settings → All application settings.

## What works

- Continuous router-originated IPv4 DNS/HTTPS checks; two VPNs are measured in parallel. Startup temporarily targets 2-second rounds, then returns to the configured interval (10 seconds on the tested router). Slow checks can take longer; rounds do not overlap.
- Auto starts the saved primary/reserve pair on the explicitly prepared MT3000, fails over after repeated failures and returns after stable recovery under the selected policy. Short failures need not switch. Stop, worker/readiness checks, rollback and a rolling attempt budget remain enforced.
- Operator primary/reserve selection while Auto stays enabled. A healthy operator preference remains preferred; confirmed failure can trigger recovery. A queued command is not proof of a completed switch.
- Live route chart and stored history with a 1–24-hour slider; exactly primary/reserve/off levels, with gaps for missing observations. Visible sidebar channel lamps, animated healthy selected cards and static inactive/error cards.
- Detailed seven-day controller/failure history, calendar-month aggregates, lifetime counters and paginated export. Failed checks, outage episodes, attempts, successful switches and returns are different quantities. Storage limits/truncation are explicit.
- Traffic accounting, diagnostics/error explanations, optional bounded speed tests and optional Telegram reports. Tokens and VPN credentials stay private.

Both stock GL.iNet tunnels may show Connected while only one carries the selected common traffic. The application changes verified routing-policy selection; it need not disconnect the standby tunnel or rename Tunnel 1/2.

## Evidence and limits

The alpha45 behavior baseline passed 724 application tests and 107 QA tests in each of two runtime environments plus 39 UI suites. Actual MT3000 tests include controlled failures, automatic failover/return, operator switching with Auto on, native-process recovery, installation/served-file checks and statistics persistence. [Release evidence](docs/RELEASE-0.9.0.md) distinguishes the exact 0.9.0 checks from earlier physical runs.

Independent external-LAN acceptance, a completed 24-hour traffic soak, physical power-cut testing, MT6000 continuous-mode acceptance, IPv6 failover and unrestricted multi-reserve hierarchy are not established. Auto requires explicit Start after a router/application restart. Some OpenVPN starts previously received AUTH_FAILED and safely stopped; no provider root cause is claimed.

## Documentation

[Quick start](docs/AUTO-QUICKSTART.en.md) · [Eight setup steps](docs/FIRST-RUN-SETUP.md) · [How it works](docs/HOW-IT-WORKS.en.md) · [Install](docs/INSTALL.en.md) · [Current status](docs/CURRENT-STATUS.md) · [Statistics](docs/STATISTICS-RETENTION.md) · [Roadmap](docs/ROADMAP.md) · [Complete documentation index](docs/DOCUMENTATION-INDEX.md) · [Changelog](CHANGELOG.md)

Private configurations, keys, bot tokens, sessions and backups are excluded from public source and release assets. Historical reports are dated evidence, not current installation instructions. Independent project; not an official GL.iNet/OpenWrt product. [MIT](LICENSE) · [third-party notices](LICENSING.md).
