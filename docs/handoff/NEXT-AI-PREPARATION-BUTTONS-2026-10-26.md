# Next agent — preparation buttons / 26 October 2026

## English

Owner requested buttons to disable router settings blocking Auto, including on the main router. Implementation/local validation is complete. Do not repeat the implementation. Read [the report](../diagnostics/PREPARATION-BUTTONS-2026-10-26.ru.md), [preparation scope](../ROUTER-PREPARATION.md) and [receipt](../../qa/PREPARATION-BUTTONS-ALPHA28-2026-10-26.json).

Product source `7ff1b81f89b83d6fb4bd0bc6e6327df7bc7eb8b4`; alpha28-1, dashboard104/ui76; IPK 884115 bytes, SHA256 `58610b1c3355668b9a1de8f20c7dc8d7ca802c6860c3d35ca459ce00558a1ab3`. Later closure changes only metadata/evidence. Dual immutable CI passed 807 app/113 QA per runtime with explicit complementary skips, 62 UI suites, Chromium 4×22 synthetic checks. No physical or VM installation/acceptance occurred.

Seven allowlisted preparation actions: wg/ovpn autostart, vpn-client/shortcut-fe startup, HNAT, firewall flow flags and exact SFE autoload preservation. Read-only preview and explicit Apply; writes bind config/control/boot identity, preserve original safe values, reject active Auto or retained ownership, and require actual readback. No service Stop, interface reconnect, firewall/network reload, forced module removal, Auto Start or reboot is dispatched. Same-boot restart-required records and unconfirmed preparation records block Auto. Do not delete preparation-changes records to bypass guards.

The writer verifies actual GL-MT3000/GL-MT6000 firmware 4.11.0; this does not add an unsupported Auto mode or pair. Tests use temporary model fixtures, real Lua with mocked UCI, and synthetic browser RPC. Current physical state was not refreshed in this task; the last device inspection belongs to the alpha27 report. No new authorization to automatically install, publish, reboot or press a physical preparation button is implied by this handoff. Honor any later explicit device instruction on its own scope, not older historical exclusions.

Private evidence: `private/preparation-buttons-20261026/`; exact CI archives and receipt in `.git/handoff/ci-7ff1b81*`. Canonical package is in releases; not published or installed. Main/stable, host networking and physical configuration untouched. No new monitor/VM was started.

## Русский

Кнопки готовы и проверены локально; повторять разработку не нужно. Для каждого пункта сначала показывается модель и точное изменение, затем отдельное подтверждение. Исходные значения сохраняются до записи; результат читается заново. Незавершённое восстановление, новый Stop, чужая правка или неизвестная привязка запрещают применение.

Пакет alpha28 лежит в releases, но не публиковался и не устанавливался. На физическом роутере новые кнопки пока не появились. При следующей отдельной установке/проверке сначала заново проверить устройство и сохранность текущей конфигурации. Нельзя удалять старое владение/журнал или preparation-changes ради зелёного состояния. Смена boot-флагов не означает выключение уже работающего ускорения; при требуемой перезагрузке Auto остаётся заблокирован до неё.
