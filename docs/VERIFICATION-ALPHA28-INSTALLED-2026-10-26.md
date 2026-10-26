# Installed alpha28 / Установка alpha28 — 26 October 2026

## English

**PASS_INSTALL:** dedicated GL-MT3000 (`glinet,mt3000-snand`, firmware 4.11.0) upgraded from alpha25-1 to **0.9.1-alpha28-1**. Product source `7ff1b81f89b83d6fb4bd0bc6e6327df7bc7eb8b4`; IPK 884115 bytes, SHA256 `58610b1c3355668b9a1de8f20c7dc8d7ca802c6860c3d35ca459ce00558a1ab3`. Ordinary opkg install, no force, dependency upgrade or firmware replacement. Package status is `install user installed`.

All 90 payload files/modes were read back; the retained own conffile is correctly 0600. Actual user-facing HTTP8080 serves canonical dashboard104/ui76 bytes. Fresh RPC reports alpha28, five-section UI and read-only preparation preview are installed. Exactly one monitor and one native controller run. Auto is OFF; no owned guard exists. Both currently enabled VPNs passed router-bound DNS and two HTTPS probes. This is not external LAN/failover/soak acceptance.

The owner explicitly approved resolving a previous-boot RUNNING ownership record after ordinary Stop could not finish with a dead alpha25 controller. Preconditions verified no active controller/apply worker, no owned guard, a ROLLED-BACK native journal, no pending commands/UCI changes, quiet vendor workers and preserved current config. The original pair record was copied into private router session-recovery storage, hash/readback verified, and ownership explicitly handed back to the current external configuration. Old interface flags were not restored. The original native journal, budgets and current VPN/route-policy configuration were retained. Lifecycle checks then passed normally; hooks/guards were not disabled or force-bypassed.

Supported sysupgrade configuration exports before/after have 193/194 entries, independently decrypted and read after encrypted persistence. No plaintext backup or recovery key was logged. The after-export includes the exact archived original session. These are configuration exports, not full-flash/bootloader images.

[Receipt](../qa/MT3000-ALPHA28-2026-10-26.json) · [Next agent](handoff/NEXT-AI-ALPHA28-INSTALLED-2026-10-26.md).

## Русский

### Что сделано

- Установлена **0.9.1-alpha28-1** на выделенный GL-MT3000; новый интерфейс — **dashboard104/ui76**.
- Пакет до передачи и в отдельной `/tmp`-папке роутера совпал по размеру/SHA256. SFTP на устройстве отсутствует; использован существующий SSH/Python-транспорт.
- Резервная копия до изменений зашифрована AES-GCM с ключом под Windows DPAPI; после сохранения независимо расшифрована и полностью прочитана в памяти.
- Обычный Stop принят, но старый контроллер не работал, а сохранённая сессия оставалась RUNNING. Штатный lifecycle вернул `LIFECYCLE-STOP-AUTO-FIRST`.
- После отдельного явного ответа владельца «Да, сохранить текущие VPN и продолжить» исходная запись сессии сохранена в `/etc/homensai-vpn/session-recovery/`, проверена по SHA256 и чтением. Завершено только прежнее владение, без отката устаревших флагов поверх новой конфигурации. Состояние отмечено STOPPED с явной записью ручного согласования и `original_restored=false`; исходник не удалён.
- Повторная штатная lifecycle-проверка прошла. Выполнен обычный `opkg install` без force-флагов.

### Доказательства после установки

| Проверка | Результат |
|---|---|
| opkg | `install user installed`, версия 0.9.1-alpha28-1 |
| Файлы и права | 90 файлов проверены; собственный conffile сохранён с правами 0600 |
| HTTP | dashboard104.js и ui76.css: 200, хэши совпадают с IPK |
| RPC | Свежая alpha28, новые методы подготовки доступны; read-only preview проверен |
| Службы | Ровно один monitor и один native, оба работают и публикуют свежий статус |
| Auto | OFF / STOPPED; запуска не было |
| Защитная nft-таблица | Отсутствует |
| Текущие включённые VPN | Два; оба прошли DNS и по две HTTPS-проверки с роутера |
| Сеть, Wi-Fi, DHCP, firewall, VPN-профили, route_policy, HNAT | Конфигурационные хэши сохранены |
| Параметры приложения и соглашение | Семантически сохранены; исключения — ожидаемая очистка native_enabled/native_until/native_trial штатными hooks |
| Исходная старая сессия | Архивирована побайтно и включена в новую зашифрованную копию |

Первая дополнительная проверка после opkg ожидала архивные права conffile; учтены штатные 0600, после чего выполнена независимая полная read-only проверка. Повторная установка ради этого не запускалась.

### Сохранность и границы

Копия до обновления: 193 записи, encrypted SHA256 `864700d8252402bd6f6ff5ed3da2f96f31591f97e51115d1c6534e43a4f10305`. После: 194 записи, encrypted SHA256 `9828ed234003b23cf7ac83e7c4f69e8da71c4b95376c014840c6f31f1bff1f30`. Обе независимо прочитаны после расшифровки в памяти. Ключи DPAPI/архивы находятся только в приватной папке установки.

Неизменность живого main-route hash проверена в фазе согласования старой сессии. Отдельный свежий pre-opkg receipt этого runtime-хэша не сохранён; через установку доказана неизменность сетевой и маршрутной конфигурации. Не выдавать это за отдельный внешний LAN-тест или полноценное доказательство всех динамических маршрутов.

Для Auto остаются диагностические условия **FW3-SELECTED-ZONE-UNVERIFIED** и **PROFILES-NOT-GENERIC-RULES**: сохранённая пара не соответствует текущему составу действующих VPN-политик. Настройки пары, автозапуска и ускорения при обновлении не исправлялись и кнопки применения подготовки не нажимались. Действующие VPN сохранены, Auto не включён.

Не проводились перезагрузка, speed test, fault injection, внешний LAN failover, питание/суточный тест или native-browser визуальная приёмка. Основной MT6000, Windows-сеть, main/stable и внешняя публикация не изменялись.

Приватные материалы: `private/alpha28-install-20261026/`, включая owner-consent, исходную диагностику, encrypted backup-before/after, handoff, verify/http/postcheck и FINAL. Для просмотра нового меню обновить страницу LuCI через Ctrl+F5; `#home` открывает новый «Минимум» и при выключенном Auto.
