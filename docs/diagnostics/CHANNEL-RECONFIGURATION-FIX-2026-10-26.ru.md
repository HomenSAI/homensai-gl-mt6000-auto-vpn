# Channel reconfiguration / Исправление смены каналов — alpha27

## English

Local candidate `0.9.1-alpha27-1`, product source `601ad227deba89d367b26dab7a35129ee21af569`, dashboard103/ui75. This candidate is not published or installed. Current physical MT3000 remains alpha25; no router configuration, service, acceleration, firewall or Auto state was changed.

Fixed live probe allocation after channel removal, historical scan totals, role labels after rebinding, settings defaults after profile replacement, startup/shutdown recovery exceptions, corrupt persisted phases, continuous-mode dependence on legacy trial deadlines, false RUNNING presentation while blocked, and package revision/Python 3.9 version-tool compatibility.

Expected recovery conflicts now produce a fresh BLOCKED status and retain durable ownership, original settings, journals and budgets. They do not authorize restoring an obsolete configuration, discarding ownership, starting Auto, or silently choosing another tunnel. The prepared MT3000 controller still requires its existing verified wgclient1/ovpnclient1 pair; supporting another pair is not implied by this patch.

Actionable EN/RU remedies appear on Minimum, Start refusal, preparation failures, the error dictionary and Help. The acceleration link uses the router hostname and default GL panel port, not the LuCI port: `/#/netnat`. This route was found in installed vendor UI references; the menu path is also documented by GL.iNet.

Validation: immutable-source dual CI passed on Python 3.11.2 and 3.9.15: 787 application / 113 QA tests each, with explicit complementary skips (application 16/0; QA 2/17), 61 Node UI suites and four native Chromium groups (12 checks per group). Both CI package hashes match the separately built candidate. Earlier failed attempts remain private.

## Русский

### Что исправлено

- Отключённые каналы больше не расходуют лимит живых проверок. Выбранные туннели получают приоритет перед посторонними каналами; каталог серверов сохраняется отдельно.
- После перехода 4→2 старый итог ручной проверки больше не подменяет актуальное количество каналов. При изменившемся составе и отсутствии нового результата показывается просьба повторить проверку.
- Названия «Основной/Резерв» следуют точной привязке туннеля после смены сервера. Удалённый резерв не превращается автоматически в другой туннель. Начальные значения формы настроек учитывают текущую привязку.
- Ошибки восстановления при изменении политики, сети или конфигурации публикуются как BLOCKED. Контроллер больше не падает на этом пути при запуске и завершении. Старая сессия сохраняется в HELD с конкретным кодом; прежнее намерение запуска отменяется. Владение, снимки, журналы и бюджет попыток не сбрасываются.
- Повреждённая фаза сохранённой сессии, в том числе с правильной контрольной суммой, не ломает статус и не разрешает Start.
- Непрерывный режим сначала обрабатывает собственное состояние; устаревшее окно прежнего LAN-теста не блокирует его раньше времени.
- Сохранённая фаза RUNNING больше не означает работающий Auto, если свежий контроллер сообщает BLOCKED. Простой экран показывает причину и инструкцию.
- Неуспешная подготовка возвращает конкретный код пункта вместо общего `PAIR-PREPARATION-REQUIRED`.
- Новый prerelease сбрасывает номер пакета с 2 на 1; вспомогательная запись файла совместима с Python 3.9.

### Где теперь видна инструкция

Одинаковые инструкции используются на главной, в отказе Start, в таблице подготовки, в раскрытии «Как исправить» и в разделе «Помощь». Для аппаратного ускорения:

**GL.iNet → Сеть → Сетевое ускорение / Network Acceleration → выключить Enable → Apply.**

Кнопка открывает штатную страницу этого роутера `/#/netnat`. Отдельно доступна [официальная инструкция GL.iNet](https://docs.gl-inet.com/router/en/4/interface_guide/network_acceleration/). Выбор режима Auto/Hardware/Software не равен выключению общего переключателя. Если настройка выключена, причина работающего модуля и причина сохранённого автозапуска рассматриваются отдельно.

Для `FLOW-OFFLOAD-ENABLED` указаны **LuCI → Сеть → Межсетевой экран → Общие настройки → Routing/NAT Offloading**, оба переключателя и Save & Apply.

Для автозапуска интерфейса указаны **LuCI → Сеть → Интерфейсы → wgclient1/ovpnclient1 → Изменить → Основные настройки → Bring up on boot**. Для конкурирующей службы — **LuCI → Система → Автозагрузка → vpn-client → Disable**. Инструкция отличает отключение автозапуска от остановки работающей службы и требует сначала подтвердить завершение восстановления Auto.

### Что действительно происходит на проверенном роутере

Дополнительное чтение `2026-10-26T14:25:59Z` подтвердило:

- Аппаратное ускорение **уже выключено**: `hnat_enable=0`, `hnat_runtime=disabled`. Само наличие загруженного `mtkhnat` не означает, что ускорение работает.
- `PREP-HNAT-CONFIG`, OpenVPN autostart и проверки SFE — PASS.
- `PREP-WGCLIENT1-AUTOSTART` и `PREP-STOCK-VPN-BOOT` — FAIL. Поэтому общее сообщение о подготовке нельзя объяснять только аппаратным ускорением.
- Отдельно остаётся старая сессия, не совпадающая с текущей конфигурацией; native-контроллер установленной alpha25 остановлен. Включены wgclient1/ovpnclient2, а сохранённый резерв указывает на ovpnclient1.

Исправление сообщений не устраняет эти настройки само по себе. Физическое восстановление старой сессии, выбор поддерживаемой пары, изменение автозапуска, установка пакета и явный Start не выполнялись.

### Проверки и пакет

Новые регрессии проверяют 4→2, лимит проверок, замену профиля в туннеле, исчезновение резервной привязки, ошибки восстановления при перезапуске и завершении, сохранность владения/бюджета, повреждённые состояния и отсутствие зависимости непрерывного режима от прежнего срока теста.

61 Node-набор PASS. Настоящий Chromium: EN/RU, ширины 320/375/1366, светлая/тёмная тема; 4 группы × 12 проверок PASS. RPC в браузере синтетический; это не физическая приёмка. Проверены отображение причины, инструкции/ссылки, актуальное число каналов, переходы в диагностику, отсутствие записей при навигации и горизонтального переполнения после загрузки шрифтов. Просмотрены контрольные изображения мобильного и настольного экрана.

Итоговый dual-runtime CI: **PASS точного коммита `601ad227deba89d367b26dab7a35129ee21af569`**. На Python 3.11.2 и 3.9.15: по 787 тестов приложения и 113 QA. Явные пропуски приложения 16/0 и QA 2/17 сохранены: окружения дополняют друг друга. 61 UI-набор PASS.

[Пакет alpha27](../../releases/homensai-auto-vpn_0.9.1-alpha27-1_all.ipk): **871811 байт**, SHA256 `dba3827e0e3fdc8c0cc81504cdc4504da0d96da0def3fe670b582f7390d4e54f`. Обе CI-сборки и отдельно сохранённый IPK совпали. [Общий receipt](../../qa/CHANNEL-RECONFIGURATION-ALPHA27-2026-10-26.json). Метаданные версии, установочный hash/size и текущие справочники согласованы. Это локальный проверенный кандидат, не опубликованный релиз и не доказательство установки.

Частные материалы: `private/channel-removal-diagnostic-20261026/`; штатный receipt — `.git/handoff/ci-601ad227deba89d367b26dab7a35129ee21af569-e06af324c2a04a03966e7af7ebffcf0a.receipt.json`. Неудачные предварительные прогоны не являются PASS: сохранены ошибки изменяемого bind-mount/root-среды, ревизии пакета, справочника/зависимостей тестов и совместимости вспомогательного скрипта Python 3.9. Первое наблюдение переполнения во время загрузки шрифтов сохранено; финальные проверки выполнялись после готовности шрифтов.
