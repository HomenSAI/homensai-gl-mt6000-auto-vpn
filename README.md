# HomenS.AI Auto VPN

## Проверено и работает / Tested and operational

**Русский:** система **протестирована и работает на проверенной конфигурации GL-MT3000 с прошивкой GL.iNet 4.11.0**. Текущая проверенная версия — **0.9.1-alpha25** (prerelease). Подтверждены запуск Auto, работа через резервный VPN, DNS/HTTPS обоих каналов, сохранность настроек и истории. Пройдены CI двух сред и 57 наборов UI-проверок; детали пропусков тестов сохранены в отчётах. Нативная визуальная проверка и клики браузера отдельно не подтверждены.

**English:** the system is **tested and operational on the verified GL-MT3000 configuration running GL.iNet firmware 4.11.0**. The current verified version is **0.9.1-alpha25** (prerelease). Validation confirmed Auto startup, the reserve VPN path, DNS/HTTPS through both channels, and preservation of settings and history. Dual-runtime CI and 57 UI suites passed; per-runtime skips are recorded in the reports. Native browser visual/click acceptance remains unverified.

[Проверки / Verification](docs/MAIN-VALIDATION-2026-10-25.md) · [QA](qa/LEARN-ACTIONS-ALPHA25-2026-10-25.json) · [MT3000](qa/MT3000-ALPHA25-2026-10-25.json) · [Download / Скачать alpha25](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha25)

[Русский](README.ru.md) · [English](README.md)


Monitor an existing OpenVPN/WireGuard pair and switch a verified route. Eight lessons include interactive diagrams with playback, pause and step controls.

[Guide](docs/CURRENT-STATE.en.md) · [Install](docs/INSTALL.en.md) · [Latest changes RU→EN](docs/LATEST-CHANGES.md) · [Documentation index](docs/DOCUMENTATION-INDEX.md) · [VM audit](docs/handoff/VM-AUDIT-2026-10-24.md)

Experimental software; MIT License. [Terms RU](DISCLAIMER.ru.md) · [Terms EN](DISCLAIMER.md). Switching can interrupt sessions. Prepared MT3000/4.11.0 continuous Auto has separate hardware evidence; MT6000 continuous mode and external LAN/IPv6 acceptance are not established. Private keys, tokens and backups stay outside Git.
