# HomenSAI Auto VPN · GL-MT6000

[English](README.md) · [Русский](README.ru.md) · [Developer: Serhii Khomenko / HomenS.AI](https://homensai.com)

[Exact verified router/firmware/LuCI versions and installation proof](docs/TESTED-ENVIRONMENT.en.md)

**0.5.0-alpha12 prerelease: native monitoring and bounded two-profile failover. A real automatic transition and independent rollback were verified on the reference device; unattended production operation remains unvalidated. English diagnostics and report text are the default.**

## Why it exists

The idea came from a real troubleshooting session: VPN profiles showed Connected while internet access stopped. The standard interface and noisy logs did not clearly show which server/path was healthy or how connections changed. We needed coordinated switching between servers and between OpenVPN and WireGuard. Trustworthy monitoring comes first; automatic switching is the next development stage. Wi-Fi is an access medium and a firewall controls traffic; they are not VPN protocols.

| Mode | Implementation status |
|---|---|
| Monitor | Working native service: existing profiles, IPv4 HTTPS/DNS probes, latency, traffic, events and Telegram. |
| Operation / automatic failover | Bounded client-confirmed experiment verified for two already connected profiles. Generic production `native_apply=false` remains intentional; inactive-profile startup and a full server/channel/protocol hierarchy are unfinished. See [current state](docs/STATE.md). |

## Interface and statistics

English by default, explicit English/Russian selector. Server cards, real HTTPS-latency chart, grouped OpenVPN/WireGuard histograms for today, last seven calendar days and current calendar month. Green: healthy observed time; red: confirmed failed time; grey: unobserved time. Inactive reserve profiles are excluded. Counts mean observed inactive-to-active transitions and distinct failure episodes, not probe counts. Startup is not a new connection. Durations are estimates between probes. New history starts with this release.

Calendar-month accounting sums unique VPN interfaces, including overhead, starting when monitoring begins. It is not all WAN traffic or a complete previous month. Simultaneous connected tunnels do not prove which one carried a LAN client's traffic. Checkpoints default to 15 minutes; power loss can lose the latest interval. Monitor events are mostly RAM-only; bounded native-controller history has a checksummed persistent backup.

Telegram is optional: setup wizard, private token, personal chat ID and configurable report interval. The token is required even for sending. Router backups may contain it: keep them private.

## Installation and test evidence

[Install (EN)](docs/INSTALL.en.md) · [Установка (RU)](docs/INSTALL.ru.md) · [AI installation prompt](docs/AI-INSTALL.en.md) · [Промпт для AI](docs/AI-INSTALL.ru.md) · [Validation](docs/VALIDATION.md) · [Changelog](CHANGELOG.md)

Download matching `.ipk` and `.ipk.sha256` from release assets or `releases/`. This is NOT a firmware image. Target: **GL.iNet GL-MT6000, GL.iNet 4.11.0, OpenWrt 21.02-SNAPSHOT, LuCI openwrt-21.02 git-22.335.71649-0ecaf74, vendor Python 3.9.15**. Development/tests use Linux Docker on Windows. `Architecture: all` means interpreted files, not universal router compatibility. Other hardware/firmware is untested.

Earlier releases verified installation, three connected OpenVPN/WireGuard probe paths, accounting and Telegram delivery. On 15 Oct 2026, alpha10 verified a real client-confirmed transition/return and a separate automatic transition under controlled primary traffic failure, followed by independent rollback. Helper completion errors and later checks are documented without being counted as successful helper exits. See [work log](docs/WORKLOG.md) and [validation](docs/VALIDATION.md). Simulation reports under `qa/` are separate evidence.

## Privacy

Public files exclude the author's live router/VPN configuration, Telegram token/chat ID, private keys, passwords, browser sessions, logs, firmware dumps and screenshots. Runtime secrets belong only on the router. Router probes do not validate LAN routing; IPv6, inactive-server bandwidth tests and automatic operation are unavailable.

## Author, book and related work

**Serhii Khomenko | HomenS.AI** combines mechanical engineering, project leadership, IT infrastructure and local AI. Public profile: practical tools, automation, Docker and local models. [Website/profile](https://homensai.com/profile.html) · [GitHub](https://github.com/HomenSAI) · [ORCID](https://orcid.org/0009-0009-5371-9717).

Book: **Two Worlds. One Mind.**, edition 1.1, a handbook connecting mechanical engineering, software and AI. [Book repository](https://github.com/HomenSAI/two-worlds-one-mind) · [Zenodo / DOI 10.5281/zenodo.23160031](https://zenodo.org/records/23160031). Other public work: [local AI lab](https://github.com/HomenSAI/homensai-local-ai-lab), [RTX 3080 benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks).

Independent project, not an official GL.iNet/OpenWrt product. Licensed under [MIT](LICENSE): use, modify and redistribute, including commercially, while retaining the author/site notice and licence. See [licensing scope and third-party notices](LICENSING.md).

Current device status: 0.4.0-alpha7 is installed in monitor mode, native switching disabled. Three active probe paths were verified; HNAT disable and client-path validation remain unresolved. Alpha8 is a lab candidate. Branded UI was visually checked on an isolated synthetic fixture; full live LuCI UI verification remains pending.

[Failover planner and rollback contract / Планировщик и откат](docs/FAILOVER-RESEARCH.md): read-only planner integrated; native automatic application still unavailable.

[Native controller, actual device results and restrictions](docs/NATIVE-EXPERIMENTAL.md) · [Work log](docs/WORKLOG.md)

[Working-system TODO / План доведения](docs/TODO-WORKING-SYSTEM.md) · [Client trial / Клиентское испытание](docs/CLIENT-TRIAL.md). Candidate 0.5.0-alpha1 adds persistent history and a client workflow; positive device acceptance remains pending.
