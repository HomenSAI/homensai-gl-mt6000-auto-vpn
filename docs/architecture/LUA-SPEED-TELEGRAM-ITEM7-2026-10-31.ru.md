<!-- doc-role: design -->
# Lua-план, пункт 7: тест скорости и отчёты Telegram на Lua

Дата: 31.10.2026 · Ветка: `lua/agent-speedtg-20261031` (поверх `feat/lua-core-20261030`, 2.0.0-alpha11) · План: `LUA-PLAN-2026-10-30.ru.md`, строка 7.

Пометки: **[Ф]** — факт (код, тест на ПК), **[О]** — оценка, **[П]** — проверить на MT3000.

Статус: код и тесты готовы на ПК; **на роутере не запускался**, пакет не собирался, версия не менялась. Реальные сообщения в Telegram не отправлялись: отправитель и curl в тестах — подделки.

## 1. Известная ошибка, которая исправлена

С `lua_auto=1` тест скорости отказывал `SPEED-PAUSE-UNVERIFIED` [Ф]:
1. `speed_pause.participants()` признавал участником окна тишины только `native_switch.py daemon` (роль `auto`) и `agent.py daemon` (роль `monitor`); под Lua в командной строке экземпляров procd стоят `lua/auto.lua daemon` и `lua/monitor.lua daemon`.
2. Lua Auto вызывал `backend.speed_gate('auto')`, но в `backend.lua` такой функции не было, поэтому подтверждения паузы никто не писал (ожидание кончалось бы `SPEED-PAUSE-TIMEOUT`).
3. Lua-монитор тоже не вызывал `gate('monitor')` и не писал `speed-traffic.json`, поэтому даже через `agent.py` тест получил бы `SPEED-TRAFFIC-UNKNOWN`.

Исправлено:
- `speed_pause.py`: `COMMANDS` — для каждой роли допустимы обе командные строки (Python и Lua), по-прежнему точное совпадение элемента argv и `daemon`.
- `speed_test.worker_alive`: принимает и Python-рабочего, и Lua-рабочего (`lua/speed.lua run <tx>`), так что Python-сторона (откат, `agent.py`) не объявит Lua-тест потерянным.
- `lua/speed_pause.lua`: порт `gate/load/unchanged/public/acquire/interrupted/release/cpu_usage` — тот же файл `speed-pause.json`, те же поля, проверки, тайм-ауты (25 с ожидания подтверждений, 3 с свежести подтверждения, 25 с возобновления, 360 с предела срока), тот же замок `auto-control.lock`.
- `backend.lua`: `B.speed_gate(role)` → `speed_pause.gate` (замок блокирующий, как в Python; вызывается в начале каждого прохода `auto.lua`, вне транзакции и замка).
- `monitor.lua`: `gate('monitor')` перед каждым проходом; подтверждение только когда нет прохода и нет ICMP-пинга в полёте (`probe.PingSampler:idle()`), как `website_sampler.idle() and ping_sampler.idle()` в `agent.py`; при появлении `speed-pause.json` сторожевой таймер (1 с) сразу вызывает проверку. Замок в мониторе — неблокирующий (`try_lock`): занят → «молчим» и смотрим через секунду, цикл не ждёт.

Проверка на ПК реальными процессами [Ф]: Python `acquire()` ждёт, Lua-процесс с настоящими зависимостями (`/proc`, boot_id, flock, sha256sum) делает `gate('auto')`; окно переходит в `PAUSED` с подтверждением Lua-владельца, `release()` → Lua-супервизор убирает файл и продолжает (`test_lua_speed_telegram.RealProcessInterop`).

## 2. Что перенесено в Lua

| Файл | Порт чего | Где работает |
|---|---|---|
| `lua/speed_pause.lua` | `speed_pause.py` целиком | Lua Auto, Lua-монитор, Lua-рабочий |
| `lua/speed.lua` | `speed_test.py`: настройки, проверка запроса, квота дня, история (конверт с sha256 + резервная копия), `start/cancel/active_job/publish_job/expire_worker`, `observe_traffic`, `automatic_new`, `public_live/public_status`, рабочий `run` (`measure/stage/resolve_endpoint/verify_route`) | монитор (RPC и проход), отдельный процесс-рабочий |
| `lua/telegram.lua` | `telegram_report.py` (`format_report`, `delta_lines`, `traffic_snapshot`, `deliver`, `send_message`, `send_test`, `retry_unknown`), `report_calendar.py` (`prepare`, `format_period`, `traffic_lines`, `limited_text`), `telegram_items.parse`, `telegram_state.py` (`valid`, `load`, `save`), `telegram_private.lua` (чтение uci в процессе) | дочерний процесс монитора (`telegram.lua deliver`), CLI для rpcd (`telegram.lua call telegram_test`) |

Маршрутизация (только при `lua_monitor=1`, маркер `lua-monitor.ready`):

| Вызов страницы | Кто отвечает | Возврат к Python |
|---|---|---|
| `speed_start`, `speed_cancel`, `speed_live`, `telegram_retry` | Lua-монитор (`rpc.lua` → `Monitor:speed_rpc`) | `fallback`, если `auto-control.lock` занят; нет объекта/тайм-аут ubus → `agent.py` с теми же байтами запроса |
| `telegram_test` | `lua telegram.lua call telegram_test` отдельным процессом (отправка до 15 с не должна стоять в цикле монитора) | нет ответа (Lua упал до вывода) → `agent.py` |
| поля `status.speed_pause`, `status.speed_tests`, `status.telegram` | Lua-монитор сам (мост `status_bridge.py` их больше не считает) | — |
| без Lua-монитора | всё как раньше: `agent.py` (не `status_client.py`) | — |

Lua-рабочий запускается отдельным процессом `lua /usr/lib/homensai-vpn/lua/speed.lua run <tx>` (pid из `$!`, `nixio.setsid` как `start_new_session`); дескриптор удерживаемого замка в него не наследуется (`speed.closing`) — иначе flock держался бы всю жизнь рабочего.

Отчёты Telegram: как в `agent.py` — одна доставка за раз на копии прохода, результат применяется в следующем проходе. Вместо потока — дочерний процесс `lua telegram.lua deliver <in> <out>` (`uloop.process`, предел 300 с); изменённое состояние отправителя он **сохраняет сам** (`telegram-state.json` + резервная копия), поэтому перезапуск монитора во время отправки не теряет подтверждённую доставку (Python в этом случае ждал поток до 10 с).

## 3. Одинаковость с Python (дифференциальные тесты)

`router/tests/test_lua_speed_telegram.py` + `router/tests/lua/speedtg_fixture.lua`: каждый случай выполняется Python-модулем и Lua-модулем на одинаковых входных файлах; сравниваются ответ, код ошибки и итоговые файлы как отсортированный JSON (int не выдаёт себя за float) [Ф]:
- окно тишины: 50 случаев `gate/public/load/interrupted/release` (подтверждения, отзыв подтверждения, смена намерения владельца, срок и сигнал своему рабочему — Python и Lua, возобновление, 10 видов испорченного файла), `participants` (Lua/Python/смешанные демоны, отказ при подмене);
- тест скорости: проверка запроса, квота (7 дней, лимит, порча), история (добавление, срок хранения, предел 500, восстановление из копии, порча), `start` (19 исходов: все коды отказа и успешный запуск с файлом задания), `cancel`, `active_job`, `public_live` (отбраковка точек), `public_status`, `observe_traffic`, `automatic_new`, `is_global`;
- Telegram: тексты `format_report` (наборы пунктов, обрезка 4000, эмодзи/кириллица, сводки за день/неделю/месяц, 12 серверов, дельта трафика), календарь `prepare` (9 моментов, включая переходы на летнее/зимнее время × 5 настроек), `limited_text`, `telegram_items`, `telegram_state` (валидность, загрузка с резервной копией/старым форматом, сохранение), 17 сценариев `deliver/send_test/retry_unknown`, классификация ответов (`classify` против `send_message` поверх urllib на 12 ответах).

Lua-тесты: `test_speed_telegram.lua` (рабочий целиком с поддельными curl и демонами; монитор: трафик, RPC, окно тишины, раунд Telegram), `test_speed_shell.lua` (настоящие обёртки sh: фоновый curl, kill, файл -K с токеном 0600 и его удаление, нулевой файл выгрузки, закрытие дескриптора замка).

## 4. Сознательные отличия от Python

- HTTPS через `curl --interface <dev> --resolve host:443:<адрес>` (у nixio нет TLS и SO_MARK); маршрут метки туннеля проверяется перед каждым запросом (`ip -4 -j route get <адрес> mark <m>`), как `verify_route`.
- `latency_ms` — медиана `time_total` curl трёх запросов по 0 байт (Python: время вокруг connect+TLS+запроса вместе с `ip route get`). Ожидаемо на 10–40 мс меньше [О].
- Живые точки графика — по завершении каждого запроса (≤ 1 МиБ), а не каждые 64 КиБ; при скорости < 5 Мбит/с точки реже [О].
- При ошибке одного потока Lua сразу останавливает остальные (Python ждал их до конца окна); код ошибки тот же, если ошибка одна.
- Сводка за период при равенстве часов сбоя упорядочивает серверы по id (Python — по порядку ключей словаря; у файла, записанного Lua, он тоже отсортирован).
- Очистка истории по сроку хранения — раз в 10 минут (Python — раз в минуту): строки стареют сутками, а разбор и sha256 истории на MT3000 стоят процесса `sha256sum`.
- `automatic_new`: если замок занят, новые профили остаются «новыми» до следующего прохода (Python ждал замок).

## 5. Как проверить на MT3000 (без реальной отправки в Telegram до разрешения владельца)

Сборка и установка — по обычной процедуре линии 2.0.0-lua; ниже только проверки пункта 7.
1. `lua_monitor=1`, `lua_auto=1`, Auto включён (наблюдение пары). `ubus call service list '{"name":"homensai-vpn"}'` — у `monitor` и `native` команды `lua/monitor.lua daemon` и `lua/auto.lua daemon`.
2. Тест скорости одной кнопкой на странице (1 профиль, 1 МиБ, 2 с, 1 поток). Ожидание [П]: `speed_live` проходит `pausing` → `testing` → `DONE`, в `speed-pause.json` во время теста `phase=PAUSED` и оба подтверждения (`acks.auto`, `acks.monitor`), после — `RESUMING` и файл исчезает в пределах 25 с; строка истории в `/etc/homensai-vpn/speed-history.json` с полями `download/upload/latency_ms`.
3. Отмена во время теста → `CANCELLED`; смена режима Auto/ручное нажатие во время теста → тест прерывается (`speed-cancel.json`), Auto продолжает.
4. `ps w | grep speed.lua` во время теста — один рабочий; после теста не остаются процессы curl и файлы `.speed-*` в `/var/run/homensai-vpn`.
5. Telegram без отправки: оставить `telegram_enabled=0` → `status.telegram = {"enabled": false}`. Отправку (тест и отчёты) проверять только после разрешения владельца: `telegram_test` из страницы, затем `telegram-state.json` (`last_code=TELEGRAM-DELIVERED`).
6. Возврат: `uci set homensai_vpn.main.lua_monitor='0'` — страница снова отвечает через `agent.py`; файлы теста скорости/Telegram общие для обеих линий.

## 6. Риски и что не сделано

- [П] Часы: `/proc/uptime` (CLOCK_BOOTTIME) в Lua и `time.monotonic()` в Python сравниваются в одном файле; на роутере без сна совпадают (как и в пунктах 1–4).
- [П] Нагрузка: при включённом Telegram монитор каждый проход запускает дочерний `lua telegram.lua deliver`, даже если отчёт не нужен (Python тоже запускал каждый проход процесс `lua telegram_private.lua` из потока). Если на MT3000 это заметно — перенести проверку «ничего не пора» в монитор.
- [П] `status.speed_tests` перечитывает историю с флеша не чаще раза в минуту или при изменении файла (sha256 через `sha256sum`).
- Не перенесено: Python `speed_test.py`/`telegram_report.py` остаются для отката и для запросов, на которые Lua ответил `fallback`.
