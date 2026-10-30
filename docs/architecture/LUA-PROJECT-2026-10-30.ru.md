# Проект программы на Lua: HomenS.AI Auto VPN, линия 2.0

Дата: 30.10.2026. Ветка: `feat/lua-core-20261030`. Основная Python-линия (1.0.0-betaN) продолжает жить отдельно; к ней можно вернуться переустановкой пакета.

Пометки: **[Ф]** — факт из замеров на MT3000 или из кода, **[О]** — оценка.

## 1. Зачем и что должно получиться

Что мы измерили на Python-версии (1.0.0-beta10) [Ф]:

| Показатель | Сейчас (Python) | Цель Lua |
|---|---|---|
| Память службы мониторинга | 48 МБ (из них 6,8 МБ общие библиотеки Python) | 3–5 МБ [О] |
| Память службы Auto | 41 МБ | 2–4 МБ [О] |
| Ручное переключение, от нажатия до готово | 5,4 с (4,2–6,6) | < 1 с [О] |
| Сама смена маршрута в ядре | 0,14–0,27 с | та же |
| Ответ статуса странице | 0,2–0,36 с | < 0,05 с [О] |
| Ответ кнопки | 0,2–0,3 с | < 0,05 с [О] |
| Автоматическое переключение: от сбоя до резерва | 129–136 с | не меняется языком; это задача быстрого обнаружения (отдельная ветка) |

Почему Lua, а не Go/Rust/C [Ф]:
- Lua 5.1 уже стоит на роутере; на нём написан весь интерфейс GL и LuCI.
- Готовые привязки на роутере: `uci` (libuci-lua), `ubus` (libubus-lua), `nixio` (сокеты, файлы, fork), `luci.jsonc` (JSON), `uloop` (цикл событий).
- Один процесс Lua с нашим кодом: 1–3 МБ [О]; Python 3.9 на musl копирует 40 МБ процесса при каждом запуске внешней программы (fork без vfork) [Ф].
- Переписать на Lua можно постепенно, модуль за модулем, сохраняя форматы файлов.

## 2. Процессы и взаимодействие

### 2.1 Два демона, как сейчас

| Демон | Lua-файл | Задачи | Почему отдельно |
|---|---|---|---|
| `hv-monitor` | `/usr/lib/homensai-vpn/lua/monitor.lua` | проверки каналов (DNS, HTTPS, пинг), наблюдение, учёт, статус для страницы, ubus-объект `homensai-vpn` | падение страницы или долгой проверки не должно трогать Auto |
| `hv-auto` | `/usr/lib/homensai-vpn/lua/auto.lua` | решения о переключении, транзакции, журнал, откат, ручные нажатия | тот же принцип безопасности, что и в Python-версии |

Оба под procd (`/etc/init.d/homensai-vpn`, `respawn`), оба на `uloop`. Каждый демон занимает около 1,5–2,5 МБ [О]: интерпретатор ~200 КБ, библиотеки ~1 МБ, наш код и данные ~0,5–1 МБ.

### 2.2 ubus вместо rpcd-плагина и сокета

Сейчас страница ходит через rpcd → наш shell-диспетчер → `status_client.py` → unix-сокет монитора [Ф]. В Lua монитор сам регистрирует ubus-объект `homensai-vpn` с теми же методами и теми же аргументами, что перечислены в `agent.rpc('list')`. Страница не меняется, ACL `luci-app-homensai-vpn.json` не меняется.

Методы (имена и поля как сейчас):
- чтение: `status`, `events`, `history`, `auto_live`, `inventory`, `speed_live`, `statistics`;
- кнопки: `pair_manual`, `native_start`, `native_stop`, `fault_start`, `fault_cancel`, `setup_probe`, `setup_response`, `setup_stats`, `setup_*`, `stats_reset`, `speed_start`, `speed_cancel`, `telegram_*`, `terms_accept`.

Готовый JSON статуса держится в памяти монитора и отдаётся без пересчёта: ответ < 50 мс [О]. Монитор уведомляет `hv-auto` о нажатии кнопки через ubus `notify` (замена сегодняшнего пробуждения по файлу `pair-manual-control.json`).

### 2.3 Блокировки и единственный владелец журнала

- `control_lock` остаётся flock-файлом `/var/run/homensai-vpn/auto-control.lock`. Внимание: `nixio.File:lock` — это `lockf`, он **не** исключает `flock` Python; поэтому берётся настоящий `flock(1)` на дескрипторе, который держит Lua (реализовано в `control.lua`, взаимное исключение с Python проверено тестом в обе стороны).
- Журнал транзакции `/etc/homensai-vpn/native-transaction.json` пишет только `hv-auto`. Формат остаётся: `{"schema":1,"data":{...},"sha256":"..."}`, где sha256 считается по каноническому JSON (ключи отсортированы, разделители `,` и `:`). Канонический сериализатор делаем свой (jsonc порядок ключей не гарантирует) и проверяем тестом против Python `encoded()`.
- sha256 на Lua: нужен для журнала, истории и контрольных точек. `nixio.crypto`, по исходникам, умеет только md5/sha1, поэтому он принимается лишь после проверки на контрольном примере `sha256("abc")`; иначе `sha256sum` через pipe (один вызов, ~10 мс). Чистая Lua-реализация отвергнута: 45 мс на 4 КБ. Одна реализация — `canon.sha256`.

### 2.4 Файлы состояния: форматы не меняются

| Файл | Где | Пишет | Формат |
|---|---|---|---|
| `status.json` | ОЗУ | монитор | как сейчас |
| `native-status.json` | ОЗУ | Auto | как сейчас |
| `native-transaction.json` | флеш | Auto | как сейчас (envelope + sha256) |
| `pair-auto-state.json`, `pair-auto-control.json`, `auto-control-revision.json` | флеш/ОЗУ | Auto | как сейчас |
| `native-history.json` + backup | флеш | Auto, только при событии | как сейчас |
| `checkpoint.json` + backup | флеш | монитор, по режиму статистики | как сейчас |
| `/etc/config/homensai_vpn` | флеш | через libuci-lua | как сейчас |

Это и есть условие отката: Python-пакет, поставленный поверх, читает те же файлы.

## 3. Карта модулей: Python → Lua

| Python-модуль | Lua-модуль | Куда | Размер [О] | Примечание |
|---|---|---|---|---|
| agent.py (цикл монитора, пробы, учёт, RPC) | `monitor.lua`, `probe.lua`, `accounting.lua`, `rpc.lua` | Lua | 1200 строк | ubus вместо rpcd-плагина |
| status_server.py, status_client.py | — | убираем | — | ubus-объект делает это сам |
| native_switch.py (супервизор, транзакции, откат) | `auto.lua`, `transaction.lua`, `rollback.lua`, `journal.lua` | Lua | 1500 строк | фазы ARMED/APPLYING/WAIT-CLIENT/COMMITTED/RESTORING/ROLLED-BACK без изменений |
| fast_policy.py | `fast_policy.lua` | Lua | 120 строк | уже портируется, тест-эквивалентность с Python |
| kernel_policy.py (разбор iptables-save, attest) | `kernel.lua` | Lua | 400 строк | |
| pair_auto.py, pair_policy.py, pair_interfaces.py | `pair.lua` | Lua | 900 строк | |
| pair_manual.py, manual_dispatch.py | `manual.lua` | Lua | 350 строк | мгновенное переключение по тем же правилам |
| rollback_recovery.py, activation_recovery.py, stock_recovery.py | `recovery.lua` | Lua | 600 строк | |
| native_history.py, switch_timing.py | `history.lua` | Lua | 400 строк | один файл, копия переименованием |
| probe_policy.py, suspicion.py | `probe_policy.lua`, `suspicion.lua` | Lua | 500 строк | счётчики sysfs читаются без процессов |
| icmp_ping.py | `ping.lua` | Lua | 200 строк | сырой ICMP-сокет через nixio, см. §4 |
| website_response*.py, ping_response_history.py, response_compare.py, latency_history.py | `response_history.lua` | Lua | 400 строк | один класс с параметрами, как в Python |
| stats_mode.py, stats_reset.py, statistics_export.py | `stats.lua` | Lua | 300 строк | режимы «Работа»/«Диагностика» |
| setup_config.py, setup_save.lua, inventory.lua, native_policy.lua | `config.lua` | Lua | 500 строк | три Lua-скрипта уже есть, объединяем |
| fault_control.py | `fault.lua` | Lua | 250 строк | |
| auto_control.py, recovery_settings.py, retention_settings.py | `control.lua`, `settings.lua` | Lua | 300 строк | |
| failure_diagnosis.py, failover_plan.py, candidate_*.py, cascade_*.py | `diagnosis.lua` | Lua | 600 строк | |
| speed_test.py, speed_pause.py | `speed.lua` | Lua, alpha2 | 400 строк | тяжёлая загрузка через `uclient-fetch` дочерним процессом |
| telegram_report.py, telegram_*.py, report_calendar.py | `telegram.lua` | Lua, alpha2 | 500 строк | HTTPS через `uclient-fetch`/curl дочерним процессом |
| device_profile.py, system_readiness.py, native_platform.py, mt3000_manual_platform.py | `platform.lua` | Lua | 400 строк | |
| rtp_boot.py, vendor_observation.py, lifecycle_guard.py | `vendor.lua` | Lua | 300 строк | |
| rpc_input.py, rpc_throttle.py | внутри `rpc.lua` | Lua | 100 строк | ubus сам разбирает JSON |
| preparation_*.py, priority_config.py, configuration_*.py | `preparation.lua` | Lua, вторая очередь | 400 строк | |
| scan_control.py, monitor_control.py, observation_freshness.py, route_history.py, reliability.py, channel_path.py, server_endpoint.py | в `monitor.lua`/`accounting.lua` | Lua | 600 строк | |

Итого ~10 000 строк Lua против ~22 000 строк Python [О]. Lua компактнее не из-за языка, а потому что уходят сокет-сервер, троттлинг RPC и запуск внешних программ.

## 4. Проверки и работа с ядром без лишних процессов

| Операция | Сейчас (Python) | В Lua | Выигрыш [О] |
|---|---|---|---|
| Пинг через туннель | подпроцесс `ping` или сокет Python | nixio raw-сокет ICMP, `setsockopt SO_BINDTODEVICE` и `SO_MARK` (nixio `setopt` поддерживает `bindtodevice`; `SO_MARK` проверить, иначе `so_mark` через fallback на `ping -I`) | без fork |
| DNS-проверка | сокет Python | UDP через nixio, свой запрос A-записи (как `dns_question()` сейчас) | без fork |
| HTTPS-проверка | ssl Python | `uclient-fetch -O /dev/null --timeout` дочерним процессом Lua (fork маленького процесса ~2 МБ, не 40) или nixio.tls, если есть на роутере | в 10–20 раз дешевле fork |
| iptables-save / restore | подпроцесс | `io.popen('iptables-save -t mangle')` и `io.popen('iptables-restore --noflush','w')` | fork маленького процесса |
| conntrack -D | подпроцесс | `os.execute` один раз за переключение | то же |
| uci reorder/commit | подпроцесс `uci` | libuci-lua в процессе | без fork, ~1 мс вместо ~50 мс |
| ip -j rule / route | подпроцесс | `io.popen('ip -j ...')` | fork маленького процесса |
| счётчики интерфейсов, `wg show` | чтение sysfs / подпроцесс | чтение sysfs файлами; `wg show` раз в минуту | без fork |
| sha256 | hashlib | nixio.crypto или `sha256sum` pipe | |

Ожидаемое время мгновенного ручного переключения [О], по этапам сегодняшних 5,4 с [Ф]:

| Этап | Python | Lua |
|---|---|---|
| Запрос кнопки | 0,6 с | 0,02 с (ubus напрямую) |
| Ожидание Auto | 0,9 с | 0,05 с (ubus notify, uloop) |
| Проверки до (диагностика + ядро) | 1,5 с | 0,2 с (разбор iptables-save в Lua, uci в процессе) |
| Смена маршрута (uci reorder + commit + restore) | 1,1 с | 0,2 с |
| Проверки после | 0,3 с | 0,1 с |
| Запись и отображение | 0,9 с | 0,1 с (история без полного перечитывания) |
| **Итого** | **5,4 с** | **~0,7 с** |

## 5. Правила безопасности: переносятся без изменений

- Журнал с фазами и отпечатком ядра до записи; при перезапуске — откат или завершение, как в `serve()` сейчас.
- Stop-ограждение: ревизия управления `auto-control-revision.json` проверяется перед каждой записью.
- Лимит попыток и пауза между переключениями для автоматики; ручная кнопка без лимита, но только на живой канал по последней проверке.
- Подтверждение автоматического переключения: реальные неудачные полные проверки источника и живой резерв; возврат на основной только после устойчивого восстановления.
- Режимы статистики «Работа»/«Диагностика», согласие на диагностику, автовозврат.
- Никаких записей секретов в историю; те же коды ошибок (таблица `error_rows` остаётся общей).

## 6. План версий

| Версия | Что входит | Проверка на роутере |
|---|---|---|
| 2.0.0-lua-alpha1 | `fast_policy.lua`, `kernel.lua`, `journal.lua`; Python-супервизор вызывает Lua только для смены маршрута (как сейчас вызывает `native_policy.lua`) | 3+3 ручных переключения, сверка журнала с Python |
| alpha2 | `hv-auto` целиком на Lua; тест скорости и Telegram на Lua (решение владельца: сразу); монитор пока Python | тесты сбоев уровня 3, откат при перезапуске, Stop во время переключения, отправка отчёта |
| alpha3 | `hv-monitor` на Lua с ubus-объектом; rpcd-плагин и сокет убираются | статус/кнопки со страницы, память, нагрузка |
| alpha4 | статистика, подготовка, приоритеты | полный регресс |
| 2.0.0-beta1 | две линии одинаковы по функциям | сутки параллельного сравнения с 1.0 на том же роутере (поочерёдно) |

Пакет: `homensai-auto-vpn-lua` с `Conflicts: homensai-auto-vpn`, чтобы на роутере стояла ровно одна линия; состояние в `/etc/homensai-vpn` общее. Откат: `opkg install` Python-пакета.

Тесты на ПК: `lua5.1` есть в нашем docker-образе [Ф]; модули uci/ubus/nixio на ПК подменяются заглушками, логика проверяется теми же фикстурами, что и Python (`test_lua_fast_policy.py` уже сверяет результаты двух реализаций).

## 7. Риски и открытые вопросы

| Риск | Как снимаем |
|---|---|
| nixio может не дать `SO_MARK` для сырого сокета | проверить на роутере в alpha1; запасной путь — `ping -I <dev>` дочерним процессом |
| TLS в Lua: nixio.tls может отсутствовать | `uclient-fetch` дочерним процессом; это тот же путь, что у прошивки GL |
| Канонический JSON и sha256 должны совпадать с Python байт в байт | тест-эквивалентность на одних файлах; иначе откат на Python сломается |
| Lua 5.1 без целочисленных типов: большие счётчики байт (трафик > 2^53) | хранить как строки или две части; трафик за месяц до 9 ПБ помещается в double точно |
| Один поток: долгая проверка HTTPS блокирует цикл | дочерние процессы через `nixio.fork`/uloop process, не блокирующие вызовы |
| Объём переписывания ~10 000 строк | поэтапно по версиям, Python-линия остаётся рабочей |

Решения владельца (30.10.2026):
- Lua-линия публикуется на GitHub только после тестов, но в отдельной ветке `feat/lua-core-20261030` — сохранность кода при поломке компьютера. Выпусков (releases) из неё до беты нет.
- Тест скорости и Telegram переносятся на Lua сразу, в alpha1–alpha2, а не в alpha4.
