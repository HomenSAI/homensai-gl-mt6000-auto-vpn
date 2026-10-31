<!-- doc-role: design -->
# Lua-план, пункт 6: история и учёт на Lua

Дата: 31.10.2026 · Ветка: `lua/agent-history-20261031` (поверх `feat/lua-core-20261030`, 2.0.0-alpha11) · План: `LUA-PLAN-2026-10-30.ru.md`, строка 6.

Пометки: **[Ф]** — факт (код, тест на ПК), **[О]** — оценка, **[П]** — проверить на MT3000. На роутере этот шаг **не проверялся**; пакет не собирался, версия не менялась.

## 1. Кто что пишет при `lua_auto=1` и `lua_monitor=1` (обе службы на Lua)

Процессы procd: `lua monitor.lua daemon` (экземпляр `monitor`) и `lua auto.lua daemon` (экземпляр `native`). Python-служб нет; Python запускается только коротко (см. «Python ещё пишет»).

| Файл | До пункта 6 (alpha11) | После (эта ветка) |
|---|---|---|
| `/var/run/homensai-vpn/status.json` (ОЗУ) | Lua-монитор, каждый проход | то же; добавлены `accounting.reliability` (публичный вид модели надёжности) и `latency_history` (как у Python) |
| `checkpoint.json` + `checkpoint.backup.json` (флеш) | Lua-монитор, **без `accounting.reliability`**: после двух сохранений Lua история сбоев, счётчики проверок/сбоев по месяцам и маршрут за 24 ч пропадали и для Python-линии (резервная копия тоже переписывалась без ключа) — **регресс** [Ф] | Lua-монитор с моделью `reliability` (+ `route_history`) как `agent.Accounting.export()`; типы чисел как у Python |
| `latency-history.json` (флеш, только «Диагностика») | **никто** — регресс в Диагностике | Lua-монитор (`latency_history.lua`), при каждом сохранении учёта |
| `ping-response-history.json` (флеш, только «Диагностика») | Lua-монитор | то же; тип маршрута минуты — полный `observed_route` (с доказательством ядра), был упрощённый |
| `native-history.json` + `.backup.json` (флеш) | Lua Auto (`history.lua`) на каждое событие перехода; события **без `latency`** | то же + `latency` (HTTPS RTT канала назначения из `status.json`, `capture_transition_latency`) |
| `stats-archive/*.json`, `stats-reset-result.json` (ОЗУ) и сброс `native-history`, `speed-history`, `latency/ping/website-response-history`, `response-compare`, `checkpoint` | **никто**: запрос кнопки «сбросить статистику» ставил `agent.py`, но Lua-монитор его не применял — страница ждала вечно, регресс [Ф] | Lua-монитор (`stats_reset.lua`) в начале прохода, как `agent.monitor_loop` |
| `probe-history.json` (флеш), `probe-boost.json` (ОЗУ) | Lua-монитор (`probe_policy.lua`) | без изменений |
| `native-transaction.json`, `pair-auto-state.json`, `switch-timing.json`, `native-status.json` | Lua Auto | без изменений (не история/учёт этого пункта) |

**Python ещё пишет** (каждый раз отдельный короткий процесс, не служба):

| Что | Процесс | Пишет |
|---|---|---|
| кнопка «сбросить статистику» (`stats_reset`) | `agent.py` через rpcd | только запрос в ОЗУ (`stats-reset-request.json`); применяет теперь Lua |
| экспорт статистики (`statistics`: controller/failures/probe) | `agent.py` через rpcd | ничего (только чтение; `failures` снова видит модель надёжности в `checkpoint.json`) |
| тест скорости | `agent.py`/`speed_test.py` | `speed-history.json`, `speed-quota.json` (пункт 7) |
| `fault_start/fault_cancel` | `agent.py` | `fault-history.json` |
| мосты | `status_bridge.py` (пока страница открыта), `lua_bridge.py` (живая проба Auto) | только ОЗУ |

**Не пишется вовсе** (остаётся после пункта 6):
- `website-response-history.json`, `response-compare.json` — нужен замер сайтов/сравнения методов в Lua-мониторе (сейчас его нет; только метрика ping). Файлы загружаются, сбрасываются и сохраняются Lua только при сбросе статистики.
- `telegram-state*.json` и сами отчёты Telegram — `agent.monitor_loop` делал это в проходе; пункт 7.
- Обрезка `speed-history.json` по возрасту (Python делал раз в 60 с в проходе) — при Lua-мониторе только при новом тесте скорости или сбросе; пункт 7.

## 2. Что сделано

| Файл `router/files/usr/lib/homensai-vpn/lua/` | Порт чего |
|---|---|
| `reliability.lua` (новый) | `reliability.Reliability` (события сбоев/восстановлений за 1–7 дней, счётчики по месяцам и за всё время, `event_context`, `controller`, `prune` с бюджетом 1 МБ, `public`, проверка структуры с теми же кодами `STATISTICS-*`), `route_history.RouteHistory` и `observed_route`, `channel_path.observed_pair_role`, `reliability.active_controller` |
| `accounting.lua` | хранит типы Python (int — число Lua, float — `canon.float`): доли трафика, секунды и все метки времени — float, счётчики — int; модель надёжности в `export/checkpoint/validate/restore`; бюджеты 3 МБ и 500 КБ меряются как `json.dumps` с разделителями `', '`/`': '` (у Python так, у alpha11 было без пробелов) |
| `latency_history.lua` (новый) | `latency_history.LatencyHistory` + `technical_history_tail` |
| `stats_reset.lua` (новый) | `stats_reset.pending/archive/apply/reset_native_history/reset_speed_history` и сброс файлов сайтов/сравнения (`ResponseCompare` — загрузка, очистка, сохранение) |
| `response_history.lua` | полный `observed_route`; спецификация метрики (файл сайтов); `clear/clear_statistics` |
| `history.lua`, `deps.lua` | `capture_transition_latency` → `env.deps.capture_latency` |
| `monitor.lua` | `observe(row, max_gap, native, pair)`; `controller` и история маршрута в каждом проходе; `status.accounting.reliability`, `status.latency_history`; в «Диагностике» раннее сохранение после края сбоя или смены маршрута не чаще раза в 60 с (`CRITICAL_SAVE_SPACING`); сброс статистики в начале прохода; новый запрос сброса запускает проход сразу (по ключу файла) |
| `rpc.lua` | разделение истории в ответе больше не вынимает `reliability.events` из опубликованного статуса |
| `monitor_io.lua` | `list_dir` (nixio.fs.dir, без процесса), `unsafe_directory` |

Сброс статистики никогда не ждёт замок: `native-history.lock` (scope `auto`/`all`) и `auto-control.lock` (`speed`/`ranking`/`all`) берутся через неблокирующий `flock -n`; если замок занят, запрос остаётся в очереди и применяется следующим проходом (Python ждал).

## 3. Совпадение с Python

Сравнение — канонический JSON (`json.dumps(sort_keys=True, separators=(',',':'))`): те же ключи, значения, int/float и цифры дробей. Файлы с сортированными ключами у Python (`native-history.json`, конверты с `sha256`) совпадают побайтно; файлы через `agent.atomic_json` (`checkpoint*.json`, истории, архив сброса) у Python пишутся в порядке вставки ключей, у Lua — отсортированными: текст отличается порядком ключей, разбор и `sha256` одинаковы, каждая линия читает файл другой [Ф].

Сознательные отличия (в коде описаны):
- при ровно равных временах последнего наблюдения двух профилей предел в 400 профилей убирает наименьший по имени (Python — первый вставленный);
- `observed_route` при нечисловом `https_success` даёт `unknown` (Python падал бы `TypeError` и пропускал проход);
- сброс: «поздние изменения» сравниваются по каноническому JSON (Python — равенством словарей).

Сохранённая особенность Python: минута истории задержки с маршрутом `blocked`/`down` пишется, хотя схема их не допускает, и следующая загрузка файла даёт `LATENCY-HISTORY-UNAVAILABLE` — так же у Python (ошибка Python-линии, для отдельного исправления в обеих линиях).

## 4. Запись на флеш

| Файл | Python (`agent.py`) | Lua до пункта 6 | Lua после |
|---|---|---|---|
| `checkpoint.json` + backup | «Работа»: раз в сутки + остановка; «Диагностика»: каждые `checkpoint` с (900) + раннее после края сбоя/маршрута ≥ 60 с | «Работа» так же; «Диагностика» только по интервалу (без раннего сохранения) | как Python |
| `latency-history.json` | «Диагностика»: с каждым сохранением учёта | не писался | как Python |
| `native-history.json` | на событие: переименование main→backup + одна полная запись | так же | так же |
| сброс статистики | архив + затронутые файлы, один раз на нажатие | не применялся | как Python |

Итог: в режиме «Работа» (у владельца) частота записи на флеш не меняется — 2 файла учёта раз в сутки и при остановке, история переходов на событие. В «Диагностике» добавляются `latency-history.json` к каждому сохранению и ранние сохранения при сбоях (как у Python). Размер `checkpoint.json` вырастает на модель надёжности: ~16 КБ за типичную неделю, до ~1 МБ событий в худшем случае (ограничение Python) [Ф: тест-стенд].

## 5. Процессор

Замер на ПК (lua5.1, две линии, проход раз в минуту, `scratchpad` бенчмарк) [Ф]:
- два `observe` за проход: 0,3–0,9 мс даже при 1 600–6 600 событиях (до оптимизации — десятки мс: каждый раз пересобирался список и кодировался до 1 МБ);
- публичный вид учёта + кодирование статуса за типичную неделю: того же порядка, что alpha11 (25–45 мс на ПК у обеих версий, замер шумный — параллельно шли другие сборки); основное — кодирование `status.json`, которое было и раньше;
- худший случай (1 600 событий, 240 КБ учёта) — ~30 мс на проход после оптимизации.
[П] на MT3000: процессор монитора за 10 мин в «Работе» и в «Диагностике», сравнить с 3,4 % alpha9.

## 6. Тесты на ПК [Ф]

- `tests/test_lua_history.py` + `tests/lua/history_differential.lua` (+ `history_differential_extra.lua`): 8 случайных многодневных сценариев (переход на зимнее время 25.10, границы месяца и года, шаг часов назад, длинные паузы, сброс счётчиков, смена ifindex, смена срока хранения) + продолжение модели из Python-экспорта — канонический экспорт после каждого шага совпадает; сжатие до бюджета и агрегированный вид > 500 КБ; 21 вариант конструктора `Reliability` (коды ошибок, миграция старого состояния); 400 статусов для `observed_route` и `active_controller`; `checkpoint.json`/`backup` от Lua = от `agent.checkpoint`; восстановление Python-файла (и повреждённого основного из резервного) = `agent.restore`; история задержки (4 сценария, > 1441 строк, `rows_json`, файл, загрузка); 3 000 случаев `capture_transition_latency`; все 7 областей сброса статистики на копиях одного «роутера» — результат, учёт и все файлы (архивы, native/speed/latency/ping/website/compare, checkpoint) совпадают.
- `tests/lua/test_monitor_history.lua`: модель в статусе и файле, раннее сохранение в «Диагностике» (не раньше 60 с, не повторно без нового края), «Работа» без раннего сохранения, сброс в начале прохода, занятый замок оставляет запрос, неверный запрос удаляется, архивов не больше 10.
- Обновлены `test_lua_monitor.py`, `lua/test_monitor_accounting.lua`, `lua/test_monitor_pass.lua` (модель надёжности теперь есть).

## 7. Проверка на роутере (MT3000; только по указанию владельца и при свободном `ACTIVE-EXECUTOR`)

1. Установить пакет с этой веткой, оставить «Работу». До установки — копия `/etc/homensai-vpn`.
2. Через 2–3 прохода: `ubus call homensai-vpn status | jsonfilter -e '@.accounting.reliability.totals' -e '@.latency_history.metric'`.
3. `ubus call homensai-vpn-lua checkpoint` → `jsonfilter -i /etc/homensai-vpn/checkpoint.json -e '@.data.accounting.reliability.schema'` = 1; `python3 -c` с `checkpoint_schema.validate` и `agent.checksum` — проходит.
4. Сброс статистики со страницы (область «задержка» или «качество»): `stats-reset-result.json` с `done:true` за ≤ 1 проход, новый файл в `/etc/homensai-vpn/stats-archive/`.
5. Ручное переключение: последнее событие `native-history.json` содержит `latency` (если монитор видел канал назначения живым ≤ 90 с назад).
6. Процессор монитора 10 мин (как в п. 2 плана) в «Работе»; затем «Диагностика» на 1 день — `latency-history.json` появляется с первым сохранением.
Возврат: прежняя процедура (`lua_monitor=0`), файлы общие с Python-линией.

## 8. Риски

| Риск | Что делаем |
|---|---|
| `checkpoint.json` больше на модель надёжности (обычно десятки КБ, до ~1 МБ) | так же у Python; [П] размер в шаге 3 |
| кодирование статуса дороже на `accounting.reliability` (≤ 100 событий + маршрут 24 ч) | замер [П] шаг 6; при необходимости — не публиковать неизменённую модель каждый проход |
| `flock -n` через `popen` при сбросе (сигнал SIGCHLD прерывает чтение) | при сбое замок считается занятым → повтор следующим проходом, данные не трогаются |
| `nixio.fs.dir` нет → архивы не обрезаются по 10/12 МБ | на MT3000 nixio.fs есть [Ф: LUA-ROUTER-FACTS]; [П] шаг 4 |
| порядок ключей в файлах `atomic_json` отличается | разбор и `sha256` одинаковы; тесты читают файлы другой линией |

## 9. Не сделано

- Замер сайтов и сравнение методов в Lua-мониторе (истории `website-response-history`/`response-compare`) — отдельная работа над пробами.
- Telegram и обрезка истории скорости по возрасту — пункт 7.
- Экспорт статистики (`statistics`) и постановка запроса сброса (`stats_reset`) остаются в `agent.py` (коротко, только чтение/запись запроса в ОЗУ); перенос в `rpc.lua` — вместе с пунктом 4/8.
- Проверка на роутере.
