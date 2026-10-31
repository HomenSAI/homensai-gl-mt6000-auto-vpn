# Пункты 2–3 плана Lua: монитор и ответы странице (2.0.0-lua-alpha4)

Дата: 31.10.2026. Ветка: `feat/lua-monitor-20261030` (поверх Python 1.0.0-beta13 + Lua core alpha1 + Lua Auto alpha2 + монитор alpha3). На роутере ещё **не проверялось**; всё ниже, кроме фактов из `LUA-ROUTER-FACTS-2026-10-30.ru.md`, проверено только тестами на ПК.

Включается одним флагом `homensai_vpn.main.lua_monitor='1'` (по умолчанию выключен). Без флага поведение пакета прежнее: procd запускает `agent.py daemon`, rpcd-диспетчер отвечает как в beta13.

## 1. Что перенесено

| Часть | Python | Lua | Состояние |
|---|---|---|---|
| Проход монитора | `agent.monitor_loop` | `lua/monitor.lua` | асинхронный проход под uloop; 2 профиля одновременно (как пул из 2 потоков); сторож прохода 60 с |
| Проверки канала | `agent.dns_probe/https_probe/probe`, `icmp_ping` | `lua/probe.lua` + `lua/monitor_io.lua` | по фактам роутера, см. §2 |
| Эпохи туннелей | `vendor_observation.VendorObserver` | `lua/vendor.lua` | полный порт; сверка с Python на 7 сценариях даёт одинаковые группы, события и строки |
| Уровни проверок, усиление, журнал решений | `probe_policy.Booster` | `lua/probe_policy.lua` | полный порт (уровни 1–5, обязательное усиление на 1–2, `probe-boost.json` в ОЗУ, `probe-history.json` на флеше, завершение плотного эпизода); наблюдатель подозрений `suspicion.py` не перенесён, `suspect()` есть, но не вызывается |
| Режим статистики | `stats_mode` | `accounting.stats` (alpha3) | Работа/Диагностика; в Работе истории не пишутся |
| История пинга (Диагностика) | `ping_response_history` | `lua/response_history.lua` | файл `ping-response-history.json` тот же, сохраняется только в Диагностике по интервалу контрольной точки и при остановке; Python читает его с тем же публичным видом |
| Журнал событий для страницы | `native_history.read_public` | `monitor_status.native_history` | последние 100 событий и счётчики из файла на флеше; кэш в памяти по ключу файлов и часу |
| `switch_timing`, `auto_control`, `manual_switch` | `switch_timing.read`, `auto_control.public_status`, `pair_manual.public_for_status` | `lua/monitor_status.lua` | читаются те же файлы |
| `manual_switch_control`, `channel_path`, `speed_pause`, `scan`, `speed_tests` | `pair_manual.controls`, `channel_path.public_status` и др. | **временный мост** `status_bridge.py`, см. §5 | без свежего ответа моста — безопасные значения |
| Чтение для страницы | `status/events/history/auto_live/inventory` | `lua/rpc.lua` | из памяти монитора |
| Кнопки настроек | `setup_probe/setup_response/setup_stats` (`setup_config.save`) | `lua/setup.lua` | в Lua: те же коды проверки, те же ключи UCI, запись через libuci с проверкой новым курсором |

Версия монитора в `status.version`: `2.0.0-lua-alpha4`. Поле `status.lua_backend` содержит запись возможностей (`nixio`, `bindtodevice`, `raw_icmp`, `so_mark` — только как факт, `so_mark_required=false`, `tls`, `https='curl --interface'`, `curl`, `uloop`, `sha256`), какие методы отвечает Lua, какие Python, список мостов и неперенесённых частей.

## 2. Проверки по фактам роутера

- **DNS**: UDP-сокет nixio, `setopt('socket','bindtodevice',dev)`, запрос A для example.com на 9.9.9.9:53, ожидание через `uloop.fd_add`, срок 3 с. Метка (SO_MARK) не ставится.
- **ICMP**: сырой сокет nixio с `bindtodevice`, эхо на цель метрики (1.1.1.1 по умолчанию), срок 1 с, проверка ответа как в `icmp_ping.valid_reply`; время — по микросекундным часам.
- **HTTPS**: те же три цели и правила, что `agent.https_probe/probe` (успех при 2 из 3; иначе `VPN-003`; DNS не прошёл — `DNS-001`). Каждая проверка — дочерний `curl` без оболочки, из постоянного списка аргументов: `-q -s --http1.1 --proto =https --max-redirs 0 -m 6 --interface <dev> --resolve <host>:443:<addr> -H Accept:... --max-filesize 32769 -D <ram> -o <ram> https://<host><path>`. Сертификат проверяется по имени хоста (как `ssl.create_default_context` в Python). Запуск через `uloop.process`, срок + 0,5 с, затем `kill -9`; цикл не блокируется. Коды выхода curl: 28 → `timeout`, ошибки TLS/сертификата → `tls-error`, 63 → `invalid-response`, прочие → `transport-error`.
- **Адрес и страна выхода**: из `https://1.1.1.1/cdn-cgi/trace` (`ip=` только глобальный IPv4, как в Python; плюс `loc=` → `exit_country`, дополнение Lua).
- **Идентичность маршрута** до и после проверки (устройство, fwmark, таблица, ifindex) сравнивается как в Python: метка читается из правил ядра, но на сокеты не ставится.
- Отказ «нет SO_MARK → SYSTEM-001» из alpha3 удалён.
- Отличие: `elapsed_ms`/`rtt_ms` HTTPS включают запуск curl (оценка 10–40 мс на MT3000); на вердикты время не влияет.
- Короткие синхронные команды остались, как в Python: `ubus … status`, `ip -j route/rule/route get`, `inventory.lua` (до и после проверок).

## 3. Поля статуса

В `status.json` (проход): `profiles` (с `vendor_*`, `ping`, `exit_country`), `accounting`, `samples`, `events`, `vendor_observation`, `probe_policy`, `response_metric`, `stats_mode` (+`storage`), `website_response_history` (история пинга; при метрике «сайты» — запасной вид Python `WEBSITE-HISTORY-UNAVAILABLE`), `native_history`, `stats_reset`, `auto_control`, `lua_backend`, `uplink_observation`, `observation_valid_for`, `wan_devices`, `package`.

В ответе `status` дополнительно (как `agent.status_reply`): `native_failover`, `native_history` (события вынесены в `history`), `stats_reset`, `switch_timing`, `auto_control`, `manual_switch`, `manual_switch_control`, `channel_path`, `speed_pause`, `scan`, `speed_tests`, `server_time`, `history_split`.

`auto_live` дополнен `auto_control {requested,pair_phase}`, `channel_path` (кэшированная проекция супервизора), `manual_switch`, `speed_pause` — как `auto_live.snapshot`.

## 4. Ответы странице: выбранная схема (п. 3)

Страница и ACL не меняются: страница вызывает объект `homensai-vpn`, его держит rpcd (exec-плагин). Два процесса не могут зарегистрировать один ubus-объект, поэтому Lua-монитор регистрирует **`homensai-vpn-lua`** (только root, не в ACL rpcd), а rpcd-диспетчер `/usr/libexec/rpcd/homensai-vpn` выбирает отвечающего:

| Условие | Методы | Кто отвечает |
|---|---|---|
| есть маркер `/var/run/homensai-vpn/lua-monitor.ready` | `status`, `events`, `history`, `auto_live`, `inventory`, `setup_probe`, `setup_response`, `setup_stats` | Lua: `mktemp` ×2 в ОЗУ, запрос → файл, `ubus -t 15 call homensai-vpn-lua rpc {method,request_file,reply_file}`, ответ — канонический JSON из файла |
| Lua ответил `fallback`, или объекта нет (код ubus 4) | те же | `agent.py` с теми же байтами запроса |
| для чтения — любая другая ошибка | чтение | `agent.py` |
| для `setup_*` — таймаут/непонятный ответ | запись | `{"saved":false,"code":"SETUP-SAVE-UNCONFIRMED"}` (запись могла произойти, повтор не делается) |
| маркера нет (Python-монитор) | всё | как в beta13: `status_client.py` через `status.sock`, иначе `agent.py` |
| всегда | `pair_manual`, `native_start/stop`, `fault_start/cancel`, остальные `setup_*`, `statistics`, тест скорости, Telegram и т. д. | `agent.py` (или `status_client.py`, если работает Python-монитор) |

Почему файлы, а не ответ ubus: libubus-lua отбрасывает JSON `null`, может превращать пустой объект в массив и по-разному кодирует дробные числа; файл даёт байт-в-байт тот же JSON, что `json.dumps` Python (null, дроби, пустые объекты). Сырой текст запроса нужен и для тех же кодов проверки, что `rpc_input.decode_request` (дубликаты ключей, глубина, NaN), — ubus разобрал бы JSON раньше нас.

Стоимость: `sh` + 2×`mktemp` + `head` + `ubus` + `cat` — короткие процессы BusyBox [О: 20–40 мс], против 0,35 с Python-статуса. Lua сам Python не запускает: ни один обработчик ubus не ждёт дочерний процесс.

Отвергнутая альтернатива: Lua регистрирует `homensai-vpn` сам, rpcd-плагин удаляется. Нужен перезапуск rpcd, теряется мгновенный откат на Python, поведение libubus-lua с null/дробями не проверено. Вернуться к ней можно в п. 8 (единый `hv-core`) после замеров.

`setup_*` в Lua: проверка аргументов → (для `setup_probe`) нет `speed-pause.json` → неблокирующий `flock -n` на `auto-control.lock` → (`setup_probe`) фаза журнала (`CONFIG-RECOVERY-UNVERIFIED`, `PROBE-SETTINGS-BUSY`) → `rpc_throttle` (2 с, `RPC-RATE-LIMIT`) → запись libuci как `setup_save.lua` (`SETUP-PENDING-DELTA`, `SETUP-DELTA-UNVERIFIED`, `SETUP-SAVE-UNCONFIRMED`, иначе `SETUP-SAVE-FAILED`) → `{"saved":true,"mode":"monitor","requires_lan_certification":true}`. Если замок занят или есть пауза теста скорости, Lua отвечает `fallback`, и `agent.py` ждёт и решает как раньше: цикл Lua не ждёт никогда.

Остановка: `stop_service` в init-скрипте вызывает `ubus call homensai-vpn-lua shutdown` (сохранение учёта и, в Диагностике, истории пинга) до SIGTERM procd — у uloop в Lua 5.1 на OpenWrt 21.02 нет обработчика сигналов.

## 5. Временные мосты

1. **`status_bridge.py`** (Python, фоном, не на пути запроса): `manual_switch_control`, `channel_path`, `speed_pause`, `scan`, `speed_tests`. Нужна аттестация ядра бэкенда Linux, которой ещё нет в Lua (п. 1/4, `backend.lua`). Монитор запускает мост через `uloop.process` не чаще раза в 10 с и только пока страница опрашивает `status`; ответ используется 30 с. Без свежего ответа: кнопки ручного переключения заблокированы с `PAIR-MANUAL-STATE-UNVERIFIED` (`MANUAL-STATE-UNVERIFIED` вне пары), `channel_path` — кэшированная проекция супервизора из `native-status.json` или `KERNEL-POLICY-UNVERIFIED`; зелёного без доказательства нет. После открытия страницы кнопки становятся доступны через время работы моста (оценка 2–7 с на MT3000).
2. **Кнопки на Python**: `pair_manual`, `native_start`, `native_stop` — до п. 4; `fault_start`, `fault_cancel` — пока остаются на Python (по заданию на п. 2–3). Пока работает Lua-монитор, резидентного сокета Python нет, и каждая такая кнопка запускает `agent.py` (оценка 1–2 с на MT3000 вместо 0,2–0,3 с через сокет).
3. **`fallback` для `setup_*`**, см. §4.

## 6. Что не перенесено (поля отсутствуют или упрощены)

`decision_explanation` (failure_diagnosis), `failover_plan`, `candidate_recommendations`, наблюдатель подозрений, истории сайтов/задержки/сравнения, `accounting.reliability`, тест скорости и Telegram в мониторе, обработка `stats-reset-request.json` (кнопка «сбросить статистику» под Lua-монитором не применяется, пока не перенесён `stats_reset`), `scan_control` (новый `scan.request` только запускает проход сразу), `trim_status_reply`, `measurement_request_id`, `telegram`. Решения Auto (Python `native_switch.py`/`pair_auto.py`) берут из `status.json` строки профилей и выборки с `vendor_*` — они есть; `failover_plan` Auto из статуса не читает (`failover_plan.streak` — функция).

Дополнение 31.10.2026: `system_readiness` перенесён (`lua/readiness.lua`, те же коды, что `system_readiness.py`; обновление не чаще раза в 30 с, ответ `ubus call system board` — один раз на процесс; дифференциальный тест `tests/test_lua_readiness.py`).

Дополнение 31.10.2026 (адрес сервера): `profiles[].server_endpoint` перенесён (`lua/server_endpoint.lua`, те же поля, правила и отказы, что `server_endpoint.observe`: один пир или ничего, ifindex до и после, у OpenVPN — время старта процесса до и после чтения сокетов, предел 0,5 с). Поле ставится в пробе после повторной проверки маршрута, как в `agent.probe`. Стоимость: WireGuard вызывает `wg show <if> endpoints` только при смене эпохи туннеля (ifindex) или раз в 300 с (после пустого ответа — раз в 60 с), в остальных проходах — одно чтение sysfs; OpenVPN — только чтения `/proc` в каждом проходе. `response_metric` публикуется всегда (раньше — только при успешном усилителе), иначе страница показывала прочерк рядом с измеренным пингом. Тесты: `tests/lua/test_server_endpoint.lua`, `tests/test_lua_server_endpoint.py` (Python против Lua на одних фикстурах), `tests/test_server_endpoint_ui.js`.

## 7. Тесты на ПК

- Lua (lua5.1, подмены uci/ubus/nixio): `test_monitor_async`, `test_monitor_policy`, `test_monitor_setup`, `test_monitor_status`, `test_monitor_io`, обновлены `test_monitor_probe/pass/rpc`.
- Python: `test_lua_monitor_item2.py` — файлы Lua читаются Python-кодом (`PingResponseHistory.load`, `Booster`, `native_history.History`, `checkpoint_schema`, `switch_timing.read`) с тем же публичным видом; `vendor.lua` = `VendorObserver` на 7 сценариях; полезная нагрузка `setup_*` = `setup_config`/`stats_mode` (ключи, значения, коды) на 35 запросах; диспетчер rpcd (путь Lua, fallback, отсутствие объекта, таймаут записи, старый путь без маркера); init-скрипт (`lua_monitor` по умолчанию выкл., `1` → `lua …/monitor.lua daemon` только если файл есть).
- Полный прогон в `homensai-vpn-python39:local`: все Python-тесты и все `lua/test_*.lua` проходят.

## 8. Проверка на роутере (только MT3000)

Перед началом: `private/ACTIVE-EXECUTOR.local.json` и указание владельца; только выделенный MT3000; MT6000 и сеть Windows не трогаются. Установка пакета из этой ветки — отдельным разрешённым шагом с резервной копией по обычной процедуре.

**A. Установка, флаг выключен.** Ожидаемо: ничего не меняется.
```
uci -q get homensai_vpn.main.lua_monitor || echo off
ls /var/run/homensai-vpn/lua-monitor.ready 2>/dev/null || echo no-marker
pgrep -f 'agent.py daemon'
```

**B. Сравнение только для чтения (служба не меняется).** Запустить 3 раза с интервалом в несколько минут, при работающем Python-мониторе:
```
lua /usr/lib/homensai-vpn/lua/monitor.lua compare
ls /tmp/homensai-lua-compare | grep -c '^probe-' ; rm -rf /tmp/homensai-lua-compare
```
Каждая строка — профиль: `lua` и `python` с `code`, `https_success`, `dns_ok`, `rtt_ms`, `exit_country`, `vendor_state`, пинг; последняя строка — `pass_seconds`, `vm_rss_kb`, `lua_backend`. Все файлы этого запуска — в `/tmp/homensai-lua-compare`; ubus-объект не регистрируется; адрес выхода не печатается.
Критерии: коды и `dns_ok` совпадают (расхождение допустимо только при реальном изменении канала между замерами — повторить); `https_success` ≥ 2 там же, где у Python; `exit_country` = DE для `wgclient1`, UA для `ovpnclient2`; `lua_ping_after.state=ok`; `lua_backend.bindtodevice=true`, `raw_icmp=true`, `curl=true`; `pass_seconds` < 8; временных `probe-*` в `/tmp/homensai-lua-compare` после завершения 0. Результаты (вывод целиком) сохранить в отчёт.

**C. Включение Lua-монитора** (сначала с остановленным Auto):
```
uci set homensai_vpn.main.lua_monitor='1'; uci commit homensai_vpn; /etc/init.d/homensai-vpn restart
sleep 5; pgrep -f 'lua/monitor.lua daemon'; ls -l /var/run/homensai-vpn/lua-monitor.ready; ubus list homensai-vpn-lua
time ubus call homensai-vpn status >/dev/null
ubus call homensai-vpn status | jsonfilter -e '@.lua_backend.monitor' -e '@.version'
grep VmRSS /proc/$(pgrep -f 'lua/monitor.lua daemon')/status; top -b -n1 | grep 'monitor.lua'
logread -e hv-monitor | tail -20
```
Затем на странице: обзор, история, Auto live, смена уровня проверок, метрики ответа, режима статистики (каждое — проверить `uci get` и вернуть значение владельца). Замеры: время `status`, память, процессор в покое за 10 мин, кнопки. Потом Start Auto по указанию владельца: состояние OBSERVING, кнопки ручного переключения доступны после ответа моста (≤ 10–15 с), одно ручное переключение и возврат (идут через `agent.py`, это ожидаемо медленнее).

**D. Возврат на Python (основная команда):**
```
uci set homensai_vpn.main.lua_monitor='0'; uci commit homensai_vpn; /etc/init.d/homensai-vpn restart
```
Аварийно: удаление маркера сразу переводит страницу на Python, даже если Lua-процесс ещё жив:
```
rm -f /var/run/homensai-vpn/lua-monitor.ready
/etc/init.d/homensai-vpn stop; uci delete homensai_vpn.main.lua_monitor; uci commit homensai_vpn; /etc/init.d/homensai-vpn start
```
После остановки проверить, что `checkpoint.json` обновлён (`date -r /etc/homensai-vpn/checkpoint.json`), и что Python-монитор снова отвечает (`pgrep -f 'agent.py daemon'`, `ubus call homensai-vpn status | jsonfilter -e '@.version'` → 1.0.0-beta13).

## 9. Риски

| Риск | Что делаем |
|---|---|
| `uloop.fd_add` с числовым дескриптором nixio, `uloop.process` и его pid на 21.02 не проверены на роутере | шаг B покажет: при ошибке проверки дают `unavailable`/`SYSTEM-001`, а не зависание; сторож прохода 60 с |
| хранилище сертификатов curl | факт роутера: `curl --interface … https://1.1.1.1` работает; при `tls-error` у всех целей — проверить `/etc/ssl/certs` |
| 3 curl на профиль: память на пике | максимум 6 curl одновременно (2 профиля); замер `free` во время прохода в шаге C |
| мост на Python — пиковая нагрузка раз в 10 с, пока открыта страница | только пока страница открыта; уйдёт с п. 1/4 |
| кнопки `pair_manual`/`native_*` медленнее без резидентного сокета | ожидаемо до п. 4; замерить в шаге C |
| сброс статистики не работает под Lua-монитором | не нажимать в проверке; перенос `stats_reset` — следующий шаг |
| в Диагностике нет историй сайтов/задержки | показывается `WEBSITE-HISTORY-UNAVAILABLE` при метрике «сайты» |
| `ubus` выводит ответ с другими пробелами | диспетчер принимает `"ok": true` и `"ok":true`; тест на ПК; проверка в шаге C |

## 10. Шаг C на MT3000 (31.10.2026, 2.0.0-alpha7)

Auto на Lua, монитор переключён на Lua по шагу C (Auto остановлен → `lua_monitor=1` → перезапуск → Start).

| Что | Факт [Ф] |
|---|---|
| Процессы | `lua monitor.lua daemon` и `lua auto.lua daemon`, Python-служб нет |
| Память | монитор 12,1 МБ, Auto 10,6 МБ (Python: монитор ~37–42 МБ, Auto 40,6 МБ); свободно 106 МБ |
| Страница | маркер и объект `homensai-vpn-lua` появились позже 10 с после перезапуска; `status` 0,43 с (Python через резидентный сокет — 0,14 с) |
| Auto | OBSERVING через 184 с после Start, как с Python-монитором |
| Процессор (240 с) | монитор 24,8 % сам + 6,3 % дочерние; Auto 26,5 % + 5,4 % (Python-монитор: 5,6–8 %) |
| Ошибки | дважды за 5 мин «pass watchdog: probes did not finish in 60 s»; один раз `probe.lua:192: COMMAND-FAILED` (`sh: write error: Broken pipe`) |

Внешний канал в это время был деградирован (~400 мс до 1.1.1.1 и без туннеля). Монитор возвращён на Python (`luamon0`): `status` 0,14 с, Auto (Lua) OBSERVING.

Исправления в alpha8: объекты uloop (таймеры, наблюдение сокетов, дочерние процессы) удерживаются в `monitor_io.live` до завершения — в libubox-lua они отменяются сборщиком мусора, что в долгой службе приводит к зависшим проверкам (одноразовое сравнение шага B этого не видит); сторож пишет, какие профили не завершились и сколько объектов ждёт; профилировщик монитора по запросу (`lua-monitor-profile.request`). Предполагаемая причина нагрузки — запись `status.json` (141 КБ каждые ~10 с) точным кодировщиком JSON на Lua; подтвердить профилем.

## 11. alpha8–alpha9 на MT3000: монитор на Lua работает (31.10.2026)

Причины проблем шага C найдены профилировщиком и журналом на роутере [Ф]:
- **сторож прохода 60 с** — объекты uloop отменялись сборщиком мусора (alpha8: удерживаются до завершения); с alpha8 сторож не срабатывал;
- **~25 % процессора** — ~80 % времени уходило на текст дробных чисел в формате Python при каждой записи `status.json` (alpha9: текст числа запоминается, вывод байт в байт прежний);
- **`COMMAND-FAILED` + «Broken pipe»** — чтение вывода команды через трубу прерывалось сигналом SIGCHLD от собственных curl монитора (alpha9: вывод через файл в ОЗУ).

Честное сравнение (alpha9, одинаковые условия: уровень 1, проверка раз в 60 с, ускорение выключено, Auto на Lua, окно 240 с):

| Монитор | Процессор сам | Дочерние | Всего | Память | Ответ `status` |
|---|---|---|---|---|---|
| Python | 3,8 % | 0,8 % | 4,6 % | ~37 МБ | 0,14 с (резидентный сокет) |
| Lua | 1,9 % | 1,5 % | **3,4 %** (−26 %) | **8 МБ** | **0,09 с** |

Ручная кнопка при обеих службах на Lua, 3+3: запрос 1,2 с (идёт через `agent.py`, резидентного сокета нет), трафик 3,8 с (3,3–4,8), готово 6,0 с (5,5–6,9); все 6 завершены. С Python-монитором и Lua Auto было 0,3 / 2,6 / 4,0 с. Это ожидаемая цена моста до пункта 4 (кнопка в Lua).

Ещё через мост: `channel_path` на странице (активный канал) приходит от `status_bridge.py`, только пока страница открыта; без него — кэш супервизора или «не подтверждено».

## 12. alpha14: последние поля моста — в Lua, Python не запускается (31.10.2026, только ПК)

Факт [Ф] на MT3000 с alpha13 (обе службы на Lua): пока открыта страница, монитор запускал `status_bridge.py` каждые ~15 с (6 раз за 90 с), ~12 % ядра в дочерних процессах (запуск Python ~2 с процессора каждый). Мост к тому времени считал только `manual_switch_control` и `scan`.

Теперь оба поля считает монитор (`lua/page_controls.lua`), Python на опрос страницы не запускается:

| Поле | Python | Lua | Источник данных |
|---|---|---|---|
| `manual_switch_control` (пара) | `pair_manual.controls()` | `page_controls.pair_controls` | состояние пары (кэш по ключу файла), намерение, ревизия, `pair-manual-control.json`, `native-status.json`, статус монитора из памяти, журнал (кэш), бюджет попыток, настройки и порядок политики из уже кэшированного `native_policy.lua` (перечитывается только при изменении UCI) |
| `manual_switch_control` (без пары) | `manual_control.control_status()` | `page_controls.legacy_controls` | те же записи; диагностика — `display-diagnostic.json` моложе 15 с (общий файл с Python), иначе один раз диагностика Lua-бэкенда в процессе монитора (команды через файл в ОЗУ, не через трубу) |
| выбор между ними | `pair_manual.public_for_status` | `monitor_status.manual_switch` | тот же `native_failover`, что и в поле `manual_switch` |
| `scan` | `scan_control.public()` | `page_controls.scan_public` | `scan.state` (кэш по ключу файла) |

Одно сознательное отличие — доказательство ядра для кнопок пары: вместо собственной аттестации (`pair_manual.attested`, iptables-save + ip rule, ~5 с процессора) берётся аттестация супервизора этой сессии из `native-status.json` по тому же правилу, что и `channel_path` на странице (`channel_path.page_kernel`: подтверждена, та же пара, роль совпадает с живым порядком, не старше 15 с). Кнопки и «активный канал» опираются на одно чтение и не могут разойтись. Нет свежего доказательства — `KERNEL-POLICY-UNVERIFIED`, как у Python без проверенной аттестации; ложного «разрешено» нет.

`status_bridge.py` оставлен для линии Python и как запасной путь: монитор запускает его только если вычисление в Lua упало (не чаще раза в 10 с, никогда по таймеру); до ответа — прежние безопасные значения. `status.lua_backend.bridges` теперь пуст, `bridge_fallback` описывает запасной путь.

Проверка на ПК: `tests/test_lua_page_controls.py` — 104 случая: 54 пары, 36 без пары, 14 `scan` (пара без политики ролей и с ней, ожидающие/выполненные/неверные запросы, удержание вручную, аттестация ядра, мгновенное переключение, лимит и пауза попыток, журнал, без пары: сертификат, попытки, срок, Stop, Auto, ожидающий запрос; `scan`: пусто, идёт, готово, ошибка, срок) — ответ Lua байт в байт равен ответу Python (ключи, значения, int/float, коды); `tests/lua/test_page_controls.lua` — 6 проверок монитора (6 опросов за 90 с — 0 запусков Python; запасной мост только после сбоя Lua; повтор диагностики не чаще 15 с).

Ожидаемый эффект на MT3000 [О]: минус ~12 % ядра (дочерние процессы Python) при открытой странице; ответ `status` прибавляет чтение нескольких малых файлов в ОЗУ (единицы мс). Проверить на роутере: `top`/`/proc/<pid>/stat` монитора за 90–240 с при открытой странице, `ps` без `status_bridge.py`, кнопки ручного переключения доступны сразу после открытия страницы.
