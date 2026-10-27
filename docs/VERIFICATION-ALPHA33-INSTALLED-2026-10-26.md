# Alpha33 physical verification — 2026-10-26

**PASS for installed startup, bounded speed pause/restore and diagnostic payload.** Dedicated GL-MT3000, GL.iNet 4.11.0; dashboard109/ui81. Product source `67fc3b90c49d1b7629e948d3b8ff8a6dfa165bb4`, IPK 885910 bytes, SHA256 `0e15b065b0ce6bdb7fdfaeac76e8f5e3869bfa13172ca6cafe519d15f8fc38cf`. [Machine-readable receipt](../qa/MT3000-ALPHA33-2026-10-26.json) · [Frozen CI](../qa/DIAGNOSTICS-LAYOUT-ALPHA33-2026-10-26.json).

The owner requested a speed-test quiet window, a reference table that fits the screen, and diagnostic explanations that match observed evidence. All are included. Legacy expanded navigation and the new Minimum remain.

Normal opkg install verified 92 payload file hashes/modes, actual selected JS/CSS over HTTP, fresh RPC and two running own services. The original selected pair is wgclient1 / ovpnclient2. VPN keys, profiles, network/firewall/policy/Wi-Fi/DHCP/DNS settings, main routes and terms were retained; both encrypted exports were independently reopened/decrypted/tar-read. Original preparation records and the archived prior-boot session remain preserved.

The real two-profile speed request reserved 16 MiB payload (protocol overhead separate). Both directions produced valid samples. At 1.6 seconds both daemons acknowledged the pause; neither advanced its observation/decision timestamp during measurement. CPU measured after acknowledgement was 21.1%; mean monitor/native CPU during pause was 0.49% / 0.45% total capacity. Job completed DONE / SPEED-COMPLETE and recovered in 22.9 seconds total. Monitoring obtained a fresh result before Auto continued. Same process PIDs, Auto intent bytes and configuration hashes; no VPN reconnect or route reorder. These are bounded samples, not a capacity guarantee.

Actual alpha33 RPC contains all three per-endpoint results for each current profile: Cloudflare and Google HTTP200, Quad9 HTTP505 (unsupported HTTP). Overall DNS and the existing two-success HTTPS threshold pass. The alpha32 device test caught the observer dropping these details; alpha33 now explicitly sanitizes/preserves them for matching identity and removes stale-identity details. The diagnostic code does not assert total loss of traffic. Historical messages use only retained evidence. One probe's incident/monitor records correlate by original measurement time; different probes remain separate.

Native Chromium/CDP passed four RU/EN/theme/viewport groups ×46 checks, including table/disclosure/long-code widths and pause/resume. Screenshots were inspected. Python3.11/3.9 each passed 839 app / 113 QA tests (app skips 23/0, QA 2/17), plus 64 Node UI suites. No native physical browser was driven; physical evidence is installed bytes, HTTP/RPC and real speed job. External LAN, injected failover, reboot and long endurance remain untested. Main/stable, MT6000 and Windows networking were unchanged. [Release delivery metadata](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha33) records publication separately.

---

# Физическая проверка alpha33

Alpha33 установлена на выделенный MT3000. Проверены реальные файлы/HTTP/RPC и два замера скорости с паузой Auto и мониторинга. После теста они автоматически возобновились, настройки, намерение Auto и процессы служб сохранились. VPN не переподключались. Итог — RUNNING / OBSERVING, оба канала проходят DNS и две HTTPS-проверки.

Таблица справочника проверена без горизонтальной прокрутки на desktop/mobile, RU/EN. Сообщения различают частичную доступность, отсутствие подтверждённых ответов и недостающую информацию. HTTP505 Quad9 показывается как проблема проверочного адреса, а не как полное отсутствие VPN-трафика. Старые события не дополняются сегодняшними данными. Исправлены дубли одного замера и неточные примеры подтверждения LAN/Stop/ускорения.

Физическое аварийное переключение и внешний LAN-клиент не испытывались. После обновления используйте Ctrl+F5. Резервные копии, ключи и частные диагностические файлы не публикуются.
