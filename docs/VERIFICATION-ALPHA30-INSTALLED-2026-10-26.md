# Alpha30 installed and ordinary Auto Start verified — 2026-10-26

**PASS:** dedicated GL-MT3000, GL.iNet 4.11.0; package 0.9.1-alpha30-1, dashboard106/ui78. Tested product source `3e92dd9f6c585ee035d9f67be80387aa75b08513`. IPK 876827 bytes, SHA256 `2c95d1cb1f3d369a691950c25c137c44f7e3ebfd32a608fc5aba6f12babe9f41`.

The owner requested the former expanded interface and the new Minimum together. The expanded Overview, twelve destinations, additional-navigation group, original content and A/B/C appearance choice are restored. Both views share the actual Auto button. A fresh preflight refusal terminates the matching request instead of leaving “Turning Auto on”; newer Start/Stop requests remain protected.

The live failure had three linked causes: saved reserve pointed to the old ovpnclient1; preparation checked fixed slot names; guard discovery queried that disabled client although its ubus interface no longer existed. Alpha29 real Start exposed the final error (ubus exit 4, PAIR-SYSTEM-001) without changing VPN connections/routes. Alpha30 excludes administratively disabled clients from discovery. A missing/malformed enabled client still refuses with GUARD-DEVICE-UNVERIFIED.

Actual app pair is wgclient1 / ovpnclient2. Reviewed preparation saved original values, set auto=0 only for these two interfaces and removed only the competing vpn-client startup S-link. No running VPN service or network restart. Seven preparation checks passed; existing hardware acceleration was already disabled. Normal opkg installation verified 91 payload files/modes, current HTTP assets, fresh RPC and one native plus one monitor process. Profiles, keys, firewall, Wi-Fi, DHCP, policy, main routes and unchanged terms were preserved. Full encrypted configuration exports before/after were independently reopened, decrypted and read; no plaintext backup was persisted.

Ordinary Start reached RUNNING / OBSERVING in 24.5 seconds; readiness_verified=true, no blockers. Both selected VPNs passed fresh DNS plus two HTTPS probes. Existing connected tunnels were reused (owned=[]), no ifup/reconnection or rule reorder. Follow-up snapshot retained matching network, policy and all protected configuration hashes. Auto is left ON as requested.

Frozen dual Linux CI: 820 application / 113 QA tests each; application skips 23/0 and QA skips 2/17 are complementary platform limits. Node: 63 UI suites. Native Chromium: 4 synthetic viewport/language/theme groups × 33 checks. [CI receipt](../qa/HYBRID-ALPHA30-2026-10-26.json) · [Physical receipt](../qa/MT3000-ALPHA30-2026-10-26.json).

Limits: no external LAN browser/path witness, injected physical failover, reboot, IPv6 or long unattended endurance acceptance. Native browser checks use synthetic RPC; physical verification uses actual installed payload, HTTP and RPC. Main/stable, MT6000 and Windows networking were not changed. Publication is a separate delivery stage; use actual [GitHub prerelease metadata](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha30) for its state.

---

# Alpha30 установлена, обычный запуск Auto проверен

На выделенном MT3000 установлен alpha30-1. Возвращены прежний расширенный «Обзор», 12 разделов и выбор оформления; новый «Минимум» сохранён. Оба экрана используют одну кнопку Auto. Отказ Start теперь завершает ожидание с конкретной причиной.

Проверка выявила старую привязку резерва к ovpnclient1 и обращение защиты к этому уже отключённому интерфейсу. Сохранена текущая пара wgclient1 / ovpnclient2; подготовка относится к этим интерфейсам. Отключён только мешающий автозапуск, исходные значения сохранены. VPN и сеть не перезапускались; ключи и защищённые настройки сохранены.

Реальный Start за 24,5 с подтвердил RUNNING / OBSERVING, блокировок нет. Оба канала проходят свежие DNS и две HTTPS-проверки. Auto оставлен включённым. Проверены пакет/HTTP/RPC и резервные копии с независимой расшифровкой. Физическое аварийное переключение, внешний LAN-клиент, перезагрузка и длительный прогон не испытывались. После обновления страницы используйте Ctrl+F5.
