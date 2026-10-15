# Журнал работы / Work log

## 2026-10-15 · 10:33–11:45 Europe/Berlin

- Пользователь разрешил автоматические стендовые испытания до 14:00 и попросил реализовать автопереключение; позже разрешил отключить мешающее ускорение. Затем приоритетом стала сохранность текущей удалённой рабочей связи. Последнее ограничение отменяет намеренные обрывы во время этой работы.
- До 14:00 запущен изолированный повторный прогон snapshot 386b4b3, niceness 15, новые seed в каждом цикле, остановка при первой ошибке. Никаких команд роутеру в этом стенде нет.
- Написан native_switch.py, внутренний Lua-инвентарь, отдельный procd supervisor, журнал с checksum/fsync, восстановление, ограничение числа попыток/дедлайна, внешнее подтверждение и ограниченный nft FORWARD guard. Область: две соседние общие VPN-политики уже подключённых интерфейсов. Не считать полноценной координацией всех vendor writers.
- Alpha1: установлен первый диагностический адаптер. Найдено, что наличие загруженного ускорителя нельзя считать доказательством его работы/отключения.
- Alpha2: добавлена проверка runtime HNAT и исправлен перезапуск именно собственного сервиса при обновлении. Без него одинаковая команда procd могла оставить старый Python-процесс.
- Alpha3: явная подготовка отключения ускорения, сохранение исходных параметров, ограничение повторов. Прямой commit через RPC запрещён; set не означал сохранение. Штатные apply с rollback и confirm прошли. Секреты не сохранялись в публичных файлах.
- Alpha4: не считать nonzero остановки уже остановленной службы окончательным результатом; проверять реальное состояние. Добавлены этапы диагностики. Три неудачи останавливают подготовку.
- Alpha5: обычная выгрузка только модулей ускорителей, без force; программный shortcut_fe выгружен. Пакеты сохранены. Mount/debugfs больше не добавляется автоматически новой процедурой.
- Alpha6: неизвестный формат hook не признаётся disabled; разрешён только обычный fallback, который ядро отклоняет при занятости модуля. mtkhnat остаётся загруженным; успешное аппаратное отключение не объявлялось.
- Alpha7: установлен на устройство; ограниченное чтение показало пустое тело hook_toggle. Три активных VPN продолжают проходить проверки. Подготовка остановлена, эксперимент явно выключен, запрос подготовки удалён.
- Alpha8: кандидат только для стенда. Добавлена диагностика свежих сообщений ядра при пустом debugfs; устаревшие сообщения и «going to disable» не являются доказательством. На роутер во время удалённой работы не установлен.
- Найдены и закрыты поздняя смена политики во время проверки выхода, повторный trial после рестарта, оставшиеся дочерние процессы после ошибки shell, отсутствие клиентского ACK, повреждение журнала. Проверки и ограничения описаны в NATIVE-EXPERIMENTAL.md.
- 52 теста native monitor/package и 9 тестов лабораторного контракта проходят. На промежуточном checkpoint: 21 цикл старого soak, 105 suite runs, 2100 новых seed, 945000 шагов, 37687012 assertions, 420 child-process crash cases, ошибок 0. Не выдавать за реальные аварии питания роутера или тест нового адаптера.
- Внешнее наблюдение за реальными статусами запущено каждые 30 секунд до 14:00; расписание текущего чата — каждые 5 минут до 14:00. Реальные наблюдения ограничены IPv4 HTTPS/DNS с роутера. Шлюз исполнения отличается от GL-MT6000; независимая клиентская проверка не выполнена. Автоматическое восстановление интернета не объявлялось.
- Локальный Git сначала: первый snapshot 0b8d9fe. Финальное исправление/документация — следующий отдельный коммит. Далее точный экспорт на GitHub; личные конфигурации, журналы устройства, адреса, токены, пароли и временные наблюдения исключаются.

Открыто: доказать отключение HNAT; подготовить независимый LAN-клиент и пользовательский trial wizard; проверить guard/apply/rollback на устройстве в отдельном окне; координация hotplug/vendor workers и реальные сбои питания/flash. Продукт остаётся monitor-first.

## 2026-10-15 · 11:46–11:50 Europe/Berlin

- Финальный исходный snapshot ab28c58 сохранён в локальном Gitea вместе с тегом v0.4.0-alpha8. Публичный экспорт дерева проверен идентичным; GitHub commit 45e0ebb, prerelease v0.4.0-alpha8 с IPK и SHA256 опубликован. Тег не передвигается после публикации.
- С 11:46 запущен второй независимый изолированный soak snapshot ab28c58 до 14:00, включая 52 новых monitor/package/controller tests, 9 lab tests и отдельные новые seed с 200001. Старый soak 386b4b3 продолжается отдельно. Их счётчики и области проверки не смешиваются.
- Наблюдение реальных статусов с роутера: отдельный процесс каждые 30 секунд, секреты только в памяти, обезличенные записи вне Git. Дополнительный heartbeat текущего чата каждые 5 минут до 14:00 проверяет свежесть, оба стенда и признаки сбоя; здоровое состояние не дублируется сообщениями.
- Состояние перед завершением публикации: на устройстве alpha7, native DISABLED; подготовительный запрос убран. Аппаратный ускоритель не объявляется выключенным; software shortcut_fe выгружен. Кандидат alpha8 не установлен из-за приоритета удалённой рабочей связи. Автоматическое восстановление интернета не обещается и не считается проверенным.

## 2026-10-15 · 12:27–13:30 Europe/Berlin · кандидат 0.5.0-alpha1

- Создан docs/TODO-WORKING-SYSTEM.md с условиями приёмки. Владелец подтвердил испытательное окно до 14:00 и потребовал сначала checkpoint/паузу соседних задач, затем испытание, восстановление и сообщение о продолжении. Рассылка в другие проекты отклонена автоматической проверкой; уточнение запрошено. Подтверждений паузы нет, сетевой эксперимент не начинался.
- Добавлены постоянная история с checksum и предыдущей исправной копией, bounded 500 записей / 18 месяцев, дедупликация, месячные счётчики. Из истории исключены tx, exit IP, пароль/токен и kernel log. Проверены новый процесс и четыре SIGKILL только собственных дочерних процессов на границах atomic replace; это не питание роутера.
- Отдельные native_confirm/native_stop RPC исключают применение UCI ради ACK: оно могло перезапустить ожидающий контроллер. Подтверждение принимается только для свежего ожидающего tx, совпадающего выхода и успешных клиентских DNS/HTTPS. Остановка привязана к текущему trial, сохраняется во flash и не снимается перезапуском.
- Исправлены отсутствие записи ошибок, сохранение guard после штатной остановки/истечения окна, слишком позднее разрешение рабочего процесса при отказе истории, и отсутствие метаданных кандидатов после Stop. Добавлены cooldown/attempt-limit регрессии. Настройки и guard не менялись на устройстве.
- Найдена проблема старого тестового harness: фиктивный PID 123 мог попасть в реальный killpg. Старый новый-кандидат soak ab28c58 остановлен после 18 завершённых циклов; результаты сохранены. Во всех таких тестах системный вызов теперь заменён mock. Фактов повреждения других процессов нет; роутер этим контейнерным тестом не управлялся. Повторные тесты alpha8 не рекомендованы до исправленного harness.
- Создан Windows LAN helper с приватным вводом пароля и безопасной проверкой шлюза/DNS/IPv6 до запуска. SelfTest пройден без сети; CheckOnly на компьютере исполнения корректно отказал CLIENT-GATEWAY-MISMATCH. Это не положительная LAN-проверка. Адрес управления и LAN-адрес проверены; прямого LAN-пути у исполнителя не подтверждено.
- UI EN/RU проверен на изолированной явно синтетической странице: кнопка Stop, инструкции, история и месячные счётчики. LuCI settings form в fixture не воспроизводилась; её реальная проверка открыта. Подправлена формулировка режима и добавлено оформление кнопок из существующих токенов стиля.
- Telegram formatter теперь получает native state/history до отправки; убрана безусловная фраза о выключенном переключении. Форматирование проверено без реальной отправки, с отдельными тестовыми/автоматическими результатами и исключением приватных полей.
- Финальные проверки этапа: 76 Python tests PASS; Lua 5.1 syntax/inventory/credential exclusion PASS в отдельном disposable container, общая среда не менялась; PowerShell 7 SelfTest PASS; негативный CheckOnly ожидаемо отказал. Положительное применение/откат на роутере не заявляется. Устройство пока alpha7/monitor/native disabled.

- Дополнительная проверка завершения выявила риск возврата на отказавший исходный VPN. finish_committed теперь возвращает исходный порядок только после свежей успешной проверки источника; иначе сохраняет резерв, отмечает original_restored=false и не выдаёт неизвестную связь за восстановленную. Коммит не отменяется автоматически при рестарте контроллера. Три регрессии пройдены. Клиентский helper дополнительно ждёт подтверждённый Stop и проверяет конечный путь; таймаут без результата не возвращает успешный exit code. ACK сверяется не только с публичным статусом, но и с checksummed private journal WAIT-CLIENT. Всего 76 тестов PASS.

## 2026-10-15 — 0.5.0-alpha2: router startup compatibility
SSH log confirmed native controller crash: Python on device lacks time.tzset. Added libc fallback matching existing monitor and three regression cases. Before fix only monitor was running; stale native status must not be treated as live. No successful switching trial claimed. Credentials and device identifiers excluded.

## 0.5.0-alpha3 — HNAT diagnostic compatibility
Fresh on-device debugfs read emits exact kernel message value=0, hook is disabled now! Recognise this response only with fresh kernel timestamp and consistent value/state; reject stale or inconsistent messages. Controller startup confirmed after alpha2. Actual switch still not tested.

## 0.5.0-alpha4 — kernel readback freshness
On-device printk and Python monotonic timestamps differ; comparing their values falsely rejects new HNAT responses. Read kernel ring before/after the hook and parse only appended entries. Ring replacement or unavailable baseline remains unknown. No stale response accepted.

## 0.5.0-alpha5 — bounded kernel ring rollover
Device ring is full: new hook records replace oldest entries. Match the unique prior tail record and parse only following new records; absent/ambiguous marker refuses. Three regression methods cover rollover, stale reuse and lost/ambiguous baseline. Actual trial pending.

## 0.5.0-alpha6 — Windows deadline / Python 3.9
Device traceback confirmed Python 3.9 rejects seven fractional digits emitted by Windows DateTimeOffset. Normalise excess fractional digits only when a timezone is present; malformed/missing timezone remains refused. Three regressions. Live switch did not start before this correction.

## 2026-10-15 — chronological real-device preparation and first attempted trial

| Step | Evidence/action | Outcome |
|---|---|---|
| LAN | Windows selected router gateway; router DNS and IPv6 prerequisite checked | Passed; secondary Wi-Fi route observed earlier, not assumed absent |
| SSH | Owner accepted observed host fingerprint; password login succeeded | Diagnostic session works; permanent admin key addition rejected by approval review and NOT applied |
| alpha1 startup | Device log AttributeError: time.tzset absent | Native process crash loop; monitor continued; old native status was stale |
| alpha2 | libc tzset fallback; 79 tests | Installed; both own processes observed running |
| alpha3 | Recognise exact hook readback value=0, hook is disabled now! | Installed; freshness check still rejected response |
| alpha4 | Replace cross-clock comparison with before/after ring comparison | Installed; full ring rollover invalidated simple prefix assumption |
| alpha5 | Unique old-tail marker establishes new records despite rollover; 82 tests | Installed; HNAT hook disabled verified; original driver remains loaded |
| Windows orchestration | Initial credential override scope failed; diagnostic helper prints only exception type/line, no credentials | Corrected in-memory override; no VPN switch at this stage |
| deadline preflight | Python 3.9 rejects seven decimal fraction digits from Windows | Controller ValueError; no switch |
| alpha6 | Normalise timezone-qualified deadline precision; 85 tests | Installed; fresh status had empty blockers |
| outage window | Owner explicitly approved next 10 minutes with possible interruption | Earlier attempts rejected by automatic approval review were NOT executed |
| real trial attempt | Controller reached APPLYING then GUARD-INSTALL-FAILED | Client helper requested Stop; no success claimed |
| state verification | Live policy order/hash equals journal BEFORE; differs from AFTER | No VPN rule reorder verified; client DNS successful and HTTPS 200 |
| guard diagnosis | nft -c -f - reports missing /dev/stdin on device | Root cause identified; fixed-path private temporary batch input required; not yet fixed/tested |
| safe hold | Own native_enabled saved 0 | Automatic mode off; journal closure and guard fix pending |

All observations above distinguish executed checks from planned work. No router power cut, successful automatic failover or verified native rollback is claimed. Source code commits: alpha2 55d7be1, alpha3 a547e64, alpha4 baee33d, alpha5 a19da23, alpha6 08bc611. Each was pushed to local Gitea before an identical source-tree snapshot was pushed to GitHub. No credentials, host fingerprint, exit IP, chat IDs, profile IDs or private router configuration are included in this log.

## 0.5.0-alpha7 — nft batch compatibility
Use private mode-0600 runtime temporary batch file, nft check before apply, and unconditional removal. Avoid missing /dev/stdin without changing device nodes. Regression verifies file permissions, check/apply order, cleanup and no apply on rejected check. Pending live acceptance.

## Подробный журнал инцидентов — 15.10.2026, Europe/Berlin (UTC+02:00)

Время ниже означает время события только при наличии отметки источника. Для восстановленных записей без точной отметки время не выдумывается. Формат последующих записей: дата/время → ошибка → причина → действие → проверка → оставшиеся ограничения.

### 15.10.2026 16:47:09 — падение native-контроллера (время из logread роутера)
- Ошибка: `AttributeError: module 'time' has no attribute 'tzset'`, `/usr/lib/homensai-vpn/native_switch.py`, строка 527. procd сообщил crash loop: 6 crashes; в списке процессов был только `agent.py daemon`.
- Причина: Python роутера не экспортирует `time.tzset`; контроллер безусловно вызывал его до входа в рабочий цикл. Системный Python не переустанавливался.
- Исправление alpha2: выделена `configure_timezone()`: использовать Python tzset при наличии, иначе `ctypes.CDLL(None).tzset()` как в работающем мониторе.
- Проверка: три регрессии для основного/резервного пути и ошибки libc; всего 79 тестов PASS. После установки оба процесса наблюдались на устройстве. Точное время установки в этой записи не сохранено.

### 15.10.2026 — HNAT ошибочно UNKNOWN (точное время диагностического чтения не сохранено)
- Ошибка: `HARDWARE-ACCELERATOR-UNVERIFIED` при фактическом ответе драйвера `value=0, hook is disabled now!`.
- Причина 1: парсер не принимал точный формат драйвера. alpha3 добавила строгую проверку согласованных value/state; старые и противоречивые ответы отвергаются.
- Причина 2: прямое измерение показало Python monotonic `64495.076409609`, последний свежий printk `64494.965555`; сравнивались разные часы. alpha4 заменила эту проверку сравнением журнала до/после чтения hook.
- Причина 3: кольцевой журнал заполнен: длина до/после 123214 байт, prefix=False. Новые записи вытесняют старые, поэтому alpha4 оставляла UNKNOWN.
- Исправление alpha5: найти уникальную последнюю строку предыдущего снимка в новом журнале; разбирать только строки после неё. Нет/несколько совпадений — UNKNOWN, без принятия старого ответа.
- Проверка: 82 теста PASS; после установки свежий native-status содержит `hnat_runtime=disabled`. Модуль mtkhnat остаётся загруженным: выгрузка драйвера не заявляется.

### 15.10.2026 — ошибка срока теста Windows (точное время обнаружения не сохранено)
- Ошибка: `ValueError: Invalid isoformat string: '2026-10-15T17:20:32.0404034+02:00'`, функция deadline, строка 76. Это значение срока, а не время возникновения ошибки.
- Причина: Windows DateTimeOffset отдаёт семь дробных знаков, Python 3.9 устройства их не принимает.
- Исправление alpha6: ограничить дробную часть шестью знаками только для строки с часовым поясом; некорректный/отсутствующий пояс не разрешать.
- Проверка: три регрессии; всего 85 PASS. После установки свежий статус DISABLED, blockers=[]; переход ещё не выполнялся.

### 15.10.2026 17:15:38 — отказ первой транзакции (время native-status)
- Ошибка: `GUARD-INSTALL-FAILED`, journal phase APPLYING; клиентский помощник сообщил `CONTROLLER-STOPPED-OR-BLOCKED` и запросил Stop.
- Причина: проверка `nft -c -f -` на устройстве вернула `Could not open file "/dev/stdin": No such file or directory`. Пакет nft читает '-' через отсутствующий узел, а не переданный pipe.
- Исправление alpha7: уникальный runtime batch-файл mode 0600 через mkstemp; сначала `nft -c -f <file>`, затем атомарный `nft -f <file>`; файл удаляется в finally. Узлы /dev, штатный firewall и пакеты не подменяются.
- Проверка на стенде: 87 PASS, включая порядок check/apply, права файла, очистку и отсутствие apply после провала check. Старая регрессия была адаптирована с stdin на файл, проверки области FORWARD/IPv6 и запрета flush ruleset сохранены.
- Проверка устройства после отказа: порядок и hash политики совпали с BEFORE, не с AFTER; guard-таблицы нет; дочернего PID нет; клиентский DNS успешен, HTTPS 200. Авто выключено.
- Завершение неуспешной попытки: только после этих проверок журнал переведён в ROLLED-BACK с причиной GUARD-FAILED-BEFORE-REORDER, без применения маршрутов. Это подтверждение отсутствия изменения, а не успешный тест отката после переключения.
- Остаток: alpha7 собрана и сохранена в Gitea; установка/живой guard-тест и автоматическое переключение ещё не подтверждены на момент этой записи.

### 15.10.2026 17:24:53 — nftables 0.9.6 отверг синтаксис guard (время из native-status)
- Ошибка: GUARD-CHECK-FAILED; прямой 
ft -c -f <temp> показал syntax error, unexpected end of file на однострочной конструкции таблицы.
- Причина: парсер 0.9.6 ожидает разделение table/chain и закрывающих блоков на отдельные строки.
- Исправление alpha8: формировать nft batch в многострочном формате, сохранить check перед apply, mode 0600 и очистку файла.
- Следующая проверка: тесты стенда и 
ft -c на самом роутере. Маршруты в этой попытке не менялись; guard не прошёл предварительную проверку.

### 15.10.2026 — повторные preflight останавливались старым Stop (точное время последней проверки не сохранено)
- Ошибка: CLIENT-STOPPED-OR-BLOCKED; native-status STOPPED/CLIENT-STOP сразу после старта helper. Порядок VPN и hash оставались BEFORE.
- Причина: helper создавал новый trial nonce только после preflight; старый nonce в native-stop.json совпадал с сохранённым trial, поэтому проверка видела latched Stop.
- Исправление alpha9: создать новый случайный nonce и сохранить его в конфигурации при native_enabled=0 до первой status-проверки. Реальное включение остаётся после успешного preflight и явного TEST.
- Проверка: source inspection показывает nonce до preflight; автоматическое применение ожидает установку и повторную проверку.

### 15.10.2026 17:58:26 Europe/Berlin — интернет по кабелю восстановлен
- Симптом: после последней попытки пользователь сообщил отсутствие интернета через GL-MT6000. Wi-Fi TP-Link сохранил связь.
- Диагностика по SSH: native state BLOCKED, код EXTERNAL-POLICY-CHANGE-GUARD-RETAINED; journal phase APPLYING; наша nft guard-таблица присутствовала; текущий порядок/hash не совпадал с сохранёнными BEFORE/AFTER. native_enabled был 1.
- Причина, подтверждённая сравнением секций: после перестановки анонимных UCI-секций изменились их автоматически вычисляемые идентификаторы. Текущие VPN-интерфейсы оказались привязаны к другим cfg-идентификаторам, поэтому сравнение raw order/hash ошибочно распознало собственное изменение как внешнее. Guard остался закрытым и блокировал клиентский трафик. Это дефект экспериментального контроллера.
- Восстановление: сохранены приватные резервные копии политики и журнала на устройстве; native_enabled=0; собственный сервис остановлен. По фактическому интерфейсу возвращён основной OpenVPN перед резервным WireGuard, выполнен штатный apply. До снятия guard проверены Kill Switch, запрет прямого WAN, здоровье источника и совпадение всех остальных семантических полей политики с состоянием до восстановления. Снята только наша nft-таблица.
- Дополнительная ошибка восстановления: nohup отсутствует на прошивке. Подготовленный скрипт запущен через subprocess.Popen(start_new_session=True), без замены системных компонентов.
- Подтверждение с ноутбука: временный /32 маршрут только к тестовому HTTPS-адресу через кабель; привязка клиента к кабельному IPv4. DNS через роутер — 2 A-ответа; HTTPS через кабель — 200, curl exit 0. Отдельно Wi-Fi HTTPS — 200. Временный маршрут удалён; Wi-Fi остаётся основным интернет-путём Windows.
- Журнал транзакции закрыт фазой RECOVERED-BY-OWNER с отдельным recovery hash; это ручное разрешённое восстановление, не успешный автоматический откат. Авто выключено. Нужны исправление идентификации анонимных секций и новый проверенный тест перед эксплуатацией.
