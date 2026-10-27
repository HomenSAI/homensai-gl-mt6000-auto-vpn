# Next agent — channel reconfiguration fixes / 26 October 2026

## English

The owner requested finding, testing and fixing related channel-removal bugs and adding concrete menu links/instructions for Auto blockers. Implementation and local validation are complete. Read [the fix report](../diagnostics/CHANNEL-RECONFIGURATION-FIX-2026-10-26.ru.md) and [receipt](../../qa/CHANNEL-RECONFIGURATION-ALPHA27-2026-10-26.json).

Product source: `601ad227deba89d367b26dab7a35129ee21af569`. Candidate `0.9.1-alpha27-1`, dashboard103/ui75, 871811 bytes, SHA256 `dba3827e0e3fdc8c0cc81504cdc4504da0d96da0def3fe670b582f7390d4e54f`. Later closure changes only metadata and evidence; compare actual product diff before reusing tests. Both Linux CI runtimes passed 787 app/113 QA tests with explicit complementary skips; 61 UI suites; Chromium 4×12 synthetic checks. No VM/device installation, failover or soak acceptance is claimed.

This candidate has NOT been published or installed. Main/stable/latest, router configuration/services, acceleration, Auto and Windows networking were not changed. Do not publish or install automatically to continue this handoff. Preserve the previously published alpha26 assets and physical alpha25 records.

Live MT3000 read-only finding: hardware acceleration is disabled (`hnat_enable=0`, runtime disabled); preparation fails WGCLIENT1-AUTOSTART and STOCK-VPN-BOOT. The installed native process has exit code 1. Durable RUNNING pair state predates boot and conflicts with network/policy/config. Saved reserve is ovpnclient1; enabled OpenVPN is ovpnclient2. Prepared continuous mode still verifies wgclient1/ovpnclient1 only. Do not silently select another tunnel or relax this platform check.

Recovery failures now retain ownership in HELD and publish a fresh BLOCKED reason rather than crashing. Start remains refused until the actual conflict is reconciled. Do not delete the pair state/journal, reset budgets, remove guards or restore old flags over newer owner configuration. A new physical task needs current identity/scope, verified private backup and a reviewed recovery/pair/startup plan before ordinary Stop/install/verify/explicit Start. The current code task did not grant a new physical failover test window.

Private evidence: `private/channel-removal-diagnostic-20261026/`; immutable CI archive/manifest/receipt in `.git/handoff/ci-601ad227*`. Preliminary failures are retained; only the final receipt is PASS. No new background monitor or VM was started.

## Русский

Исправления и локальные проверки завершены; повторять реализацию не нужно. Пакет alpha27 лежит в `releases/`, но не публиковался и не устанавливался. Установленная alpha25 и публикация alpha26 — отдельные состояния.

Важное уточнение владельцу: ускорение на MT3000 уже выключено. Реальные непрошедшие пункты подготовки — автозапуск WireGuard и штатного vpn-client. Дополнительно сохраняются старая сессия и несоответствие сохранённого резерва текущему включённому OpenVPN. Код теперь объясняет конкретную причину и даёт переход в нужное меню, сохраняя защитные отказы.

Для следующего физического действия сначала заново проверить устройство и текущую конфигурацию, сохранить проверенную приватную копию, согласовать восстановление старой сессии и выбранную поддерживаемую пару. Не выдавать локальный CI/браузерный стенд за физическую приёмку. Журналы/владение/бюджеты не удалять и проверки не ослаблять.
