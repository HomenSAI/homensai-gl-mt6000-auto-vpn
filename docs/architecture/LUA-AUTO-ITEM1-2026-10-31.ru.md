<!-- doc-role: design -->
# Lua-план, пункт 1: супервизор Auto на Lua запускается на роутере

Дата: 31.10.2026 · Ветка: `feat/lua-core-20261030` · Линия: `2.0.0-lua-alpha2` · План: `LUA-PLAN-2026-10-30.ru.md`, строка 1.

Пометки: **[Ф]** — факт (код, тест на ПК), **[О]** — оценка, **[П]** — проверить на MT3000.

Статус: код и тесты готовы на ПК; **на роутере не запускался**. По умолчанию ничего не меняется: Python-супервизор работает как раньше, пока владелец не включит `option lua_auto '1'`.

## 1. Что сделано

`lua/auto.lua` (alpha2: цикл `serve()`, транзакция, откат, пара, ручные нажатия, история) получил то, чего ему не хватало для запуска: порт `native_switch.Linux` и восстановления, запуск под procd.

| Файл `router/files/usr/lib/homensai-vpn/lua/` | Порт чего |
|---|---|
| `backend.lua` | `native_switch.Linux`: `policy()`, `candidates()`, `acceleration()`, `diagnostic()`, `order()`, `kernel_fingerprint()`, `attest_policy()`, `reorder()`, `apply()` + `apply_fast()`, `guard()`/`guard_exists()`/`unguard()`/`devices()`, `recovery_ready()`, `health()`; плюс `agent.inventory/route_binding`, `pair_auto.configure_lease` (запись аренды), `clear_native_options`, `lua_instant_switch` (запрос мгновенного переключения), `pair_auto.preflight`, `forward_dispatch` |
| `identity.lua` | `process_policy` (mark/validate/recognizes/selected_bindings/applied), `stock_derived` (no_override_options, network_partition), `semantic_section`/`section_id`/`policy_order`/`policy_hash`/`choose`, `native_proof.requested`, `vendor_observation.tunnel_identity`, `failure_diagnosis.profile_identity`, `pair_interfaces`, `device_profile`, `recovery_settings.fingerprint` |
| `diagnosis.lua` | `failure_diagnosis`: `resolve_pair`, `diagnose`, `scoped_samples`, `fresh` |
| `attest.lua` | `kernel_policy`: `attest`, `missing_only`, `static_bindings`, `rule_bindings`, `unrouted` (поверх `kernel.lua`) |
| `platform.lua` | `native_platform.assess/wait_quiet/PINS`, `mt3000_manual_platform._read/_zones/_held_firewall_locks/_workers`, `Linux.acceleration` (+ чтение состояния hnat из dmesg), `slot_contract_verified`, `preparation_control.auto_blocker`, `preparation_status.snapshot`, `rollback_recovery.vendor_lock_pid/rtp_lock_busy`, `rtp_boot` (assess/ready/prepare) |
| `net.lua` | сетевая часть `pair_auto` (`env.net` для `pair.lua`): `network`, `normalized_network`, `configs`/`config_digest`, `changed`, `static_firewall_digest`, `set_disabled` (тот же Lua-скрипт NETWORK_WRITE), `client_down`, `ifup`, `ifdown`, `quiet`, `interface_exists` |
| `recovery.lua` | `rollback_recovery` целиком: `order_steps`, `validate_step`, `restore_origin`, `order_allowed`, `record_step`, `forward_proof`, `authorize`, `promote_forward`, `vendor_rebuild_applies`, `settled`, `vendor_settled`, `rebuild`; `activation_recovery.finalize` (с `facts`, `platform_checked`, архивом журнала) |
| `deps.lua` | `env.deps`: перечисленное выше + `switch_timing.record`, `manual_control.valid_record/publish_result`, `fault_control.testing_profile`, `channel_path.from_kernel` |
| `sys.lua` | весь ввод-вывод на роутере (в тестах заменяется подделкой) |
| `py.lua` | семантика значений Python (`==`, `bool()`, `str()`, `int()`) над canon-значениями |

Изменены (alpha2): `auto.lua` (режим `daemon` с `native.lock`, режим `check`, корректное завершение по SIGTERM через uloop, запасной блокирующий цикл без uloop), `transaction.lua`/`rollback.lua` (команда, отправленная под замком, ждётся вне замка, как `forward_dispatch`; `record_step` получает данные о ходе UCI), `history.lua` (резидентная копия), `auto_control.lua` (кэш `status.json`), `canon.lua` (память sha256 малых текстов), `runner.lua` (`fs.key`).

Записи и проверки — те же, что в Python, с теми же кодами отказа. Сознательные отличия формы:
- UCI-ходы — тем же `uci reorder`/`uci commit` (процесс, как в Python); выравнивание `gl_process_vpn` — тот же CAS двух полей, но в процессе Lua через libuci (Python запускал `lua -e` со скриптом).
- `native_policy.lua`, `inventory.lua` и NETWORK_READ/NETWORK_WRITE исполняются в процессе Lua с перехватом `print`/`io.read`: JSON тот же, что Python получает через `json.loads(command(['lua',...]))`.
- Ошибка команды, которую Python поднял бы как `CalledProcessError` (в журнале — `NATIVE-SYSTEM-001`), здесь — код `COMMAND-FAILED` (он уже есть в таблице ошибок с alpha1).
- `rtp2.sh` и `ifup -w` запускаются под замком управления, ждутся вне его (как Python): Stop не блокируется на 45 с.

## 2. Нагрузка процессора: что сделано, чтобы «пустой» проход стоил миллисекунды

Python в покое — 43 % ядра: каждый проход (2 с) заново запускал `lua`-помощники, `iptables-save`, `ip`, `ubus`, считал sha256 десяти файлов, разбирал `status.json` и всю историю. В Lua каждое входное значение кэшируется по дешёвому ключу, каждое вычисление — по точным входам [Ф]:

| Что | Ключ кэша |
|---|---|
| `native_policy.lua`, `inventory.lua`, сеть UCI | inode/размер/mtime/ctime `/etc/config/<пакет>` и незакоммиченной дельты `/tmp/.uci/<пакет>`; любая собственная запись сбрасывает кэш |
| sha256 файлов производителя (10 шт.) | inode/размер/mtime/ctime файла |
| `status.json` (backend и `auto_control.read_json`) | ключ файла: монитор каждый раз переименовывает новый файл |
| дайджесты секций (`section_id`) | канонический текст секции |
| `kernel_fingerprint` и `attest` | текст `iptables-save` без комментариев и счётчиков + текст `ip -j rule` + политика + используемые поля выбора |
| `ip route get` (3 адреса) | тексты `ip route show table all` и `ip rule` |
| история `native-history.json` | ключи основного и резервного файла: пока они не менялись, данные не читаются и не пересчитываются (в Lua разбор 280 КБ истории стоит ~44 мс на ПК [Ф], на A53 в разы больше [О]) |
| sha256 малых текстов (журнал, состояние пары) | сам текст (≤16 КБ, 64 записи) |
| плата (`ubus system board`), `nft --version` | один раз на процесс; ускорители — раз в 60 с, как в Python |

Каждый проход по-прежнему читает вживую: `iptables-save`, `ip -j rule/route` (маленькие процессы), состояние netifd (libubus в процессе), процессы производителя в `/proc`, часы. Кэш отвечает только тогда, когда ключ прочитан заново и совпал. Ожидание [О]: пустой проход пары — около 10 запусков маленьких процессов (`flock`, `ip` ×2 на диагностику, `iptables-save`/`ip rule` ×2 на аттестацию) и чтение `/proc`, единицы процентов ядра вместо 43 %. Замер — шаг 4 ниже.

## 3. Временный мост (до пункта 2 плана)

`health()`, подтверждение WAIT-CLIENT и `trace()` нуждаются в живой пробе профиля (DNS + 2 HTTPS через туннель). До Lua-монитора они идут через `/usr/lib/homensai-vpn/lua_bridge.py probe|trace <файл>`: Lua пишет профиль в свой файл в ОЗУ (0600), Python-скрипт вызывает `agent.probe(profile)` или `native_switch.trace(profile)` и печатает одну строку JSON. Мост только читает. Файл запроса принимается лишь по шаблону `/var/run/homensai-vpn/.bridge-*.json`.

Цена: один процесс Python (~2 с ЦП) на вызов. Он нужен только при ручном нажатии, подтверждении переключения и проверке готовности основного канала к возврату. Отрицательный ответ `health()` держится 10 с, чтобы основной канал, который монитор считает живым, а пробa — нет, не запускал Python на каждом проходе. Положительный ответ всегда свежий: он разрешает переключение.

## 4. Что пока не перенесено (известные пробелы)

| Пробел | Что видно при `lua_auto=1` |
|---|---|
| `speed_pause.gate('auto')` | тест скорости отказывает `SPEED-PAUSE-UNVERIFIED` (монитор ищет `native_switch.py` в команде экземпляра `native`) — пункт 7 |
| `disable_acceleration` (`native_prepare_acceleration`) | отказ `ACCELERATION-PREPARE-UNAVAILABLE` |
| старая ручная очередь `manual-control.json` (`manual_dispatch.consume`, не парный режим) | запросы не выполняются; парная кнопка (`pair-manual-control.json`) работает; прерванная старая заявка закрывается при старте (`recover_pending`) |
| `capture_latency`/`capture_website`/`clean_website_response` | события переключения в истории без замеров задержки/сайтов |
| `validate_delegated` | вложенные записи журнала проверяет `pair.policy.metadata`, как в alpha2 |
| флаг Stop внутри прохода | SIGTERM завершает `uloop.run()` после текущего прохода; длинные ожидания внутри прохода (до 90 с) его не видят, procd ждёт до 300 с |

## 5. Проверка на роутере (MT3000; только по указанию владельца и при свободном `ACTIVE-EXECUTOR`)

### Шаг 1. Только чтение, Python Auto продолжает работать

1. Скопировать `router/files/usr/lib/homensai-vpn/lua/` в `/tmp/hvlua/` (пакет не ставить).
2. Среда:
   ```sh
   lua -e "for _,m in ipairs({'uloop','ubus','uci','nixio','nixio.fs','cjson'}) do print(m,(pcall(require,m))) end"
   command -v flock timeout setsid sha256sum nft
   ```
   Нужно: все модули `true` (без `nixio.fs` кэши по ключу файла не работают и каждый ключ стоит процесса — тогда пункт не включать), все команды найдены.
3. Lua: `for i in 1 2 3; do time lua /tmp/hvlua/auto.lua check; done`. Замок не берётся, состояние не пишется (кроме временного файла `sha256sum` в ОЗУ, если в `nixio.crypto` нет sha256). Печатается одна строка JSON: `blockers`, `order`, `hash`, `kernel_fingerprint`, `selection` (hash, vendor_identity, settings_hash, process_bindings, source/target, привязки), `attest` (verified, role, kernel_fingerprint, repairable_missing, code), время каждого вызова в двух проходах (`*_ms_2` — с кэшем) и `memory`.
4. Python на тех же данных, сразу после шага 3:
   ```sh
   python3 - <<'EOF'
   import sys,json,time;sys.path.insert(0,'/usr/lib/homensai-vpn')
   import native_switch as n
   b=n.Linux();t=time.monotonic();bl,sel=b.diagnostic();d=round((time.monotonic()-t)*1000,1)
   o,h=b.order();k=b.kernel_fingerprint();a=b.attest_policy(sel);s=sel or {}
   src=s.get('source') or {};dst=s.get('target') or {}
   print(json.dumps({'diagnostic_ms':d,'blockers':bl,'order':o,'hash':h,'kernel_fingerprint':k,
     'selection':{'hash':s.get('hash'),'vendor_identity':s.get('vendor_identity'),'settings_hash':s.get('settings_hash'),
       'process_bindings':s.get('process_bindings'),'source':src.get('id'),'target':dst.get('id'),
       'source_binding':src.get('kernel_binding'),'target_binding':dst.get('kernel_binding')},
     'attest':{x:a.get(x) for x in ('verified','role','kernel_fingerprint','repairable_missing','code')}},sort_keys=True))
   EOF
   ```
   Совпасть должны все поля, кроме времени. `vendor_identity` меняется, если монитор между запусками обновил поколение — повторить пару 3 раза подряд. Любое расхождение — стоп, пункт не включать, сохранить оба вывода.

### Шаг 2. Установка

Пакет линии `2.0.0-lua` из этой ветки (сборка — отдельный шаг владельца) с `lua/*.lua`, `lua_bridge.py` и новым `/etc/init.d/homensai-vpn`. До установки — резервная копия `/etc/homensai-vpn` и `/etc/config/homensai_vpn`. После установки `lua_auto` выключен: всё работает на Python, как раньше.

### Шаг 3. Включение

Auto остановлен со страницы, журнал завершён (`native-transaction.json`: фазы нет, `ROLLED-BACK` или `COMMITTED`/`HELD-ON-RESERVE` без незавершённого шага).
```sh
uci set homensai_vpn.main.lua_auto='1'; uci commit homensai_vpn     # procd перезапускает службу
ubus call service list '{"name":"homensai-vpn"}' | jsonfilter -e '@["homensai-vpn"].instances.native.command'
pgrep -af auto.lua; cat /var/run/homensai-vpn/native-status.json
```
Ожидается команда `/usr/bin/lua /usr/lib/homensai-vpn/lua/auto.lua daemon`, состояние `DISABLED`/`STOPPED` без новых блокировок.

**Возврат к Python (в любой момент):**
```sh
uci set homensai_vpn.main.lua_auto='0'; uci commit homensai_vpn; /etc/init.d/homensai-vpn restart
```
Журнал, ревизия управления, состояние пары и история — общие файлы; Python-супервизор восстанавливает их при старте так же, как после перезагрузки. Оба супервизора держат `/var/run/homensai-vpn/native.lock`, поэтому одновременно работать не могут (проверено тестом [Ф]).

### Шаг 4. Замеры и проверки строки 1 плана

1. Процессор в покое: Auto включён, пара наблюдает (`OBSERVING`). 5 минут: `pid=$(pgrep -f 'auto.lua daemon'); a=$(cut -d' ' -f14,15 /proc/$pid/stat); sleep 300; b=$(cut -d' ' -f14,15 /proc/$pid/stat)` — сумма тиков ÷ (300 × 100) = доля ядра; плюс `VmRSS` из `/proc/$pid/status`. Сравнить с Python 43 %.
2. Ручное переключение 3+3 со страницы.
3. Восстановление: `kill -9` процесса Lua во время APPLYING и во время WAIT-CLIENT (procd перезапускает) — журнал `ROLLED-BACK`, `SUPERVISOR-RECOVERY`, порядок основного канала, VPN-only guard.
4. Stop со страницы во время переключения — `CLIENT-STOP`, основной канал восстановлен.
5. Два автосбоя (тест сбоя со страницы): переключение на резерв и возврат.
После каждого шага — сохранить `native-status.json`, `native-transaction.json` и `logread -e homensai`. Неудача — возврат к Python командой выше, данные сохранить.

## 6. Тесты на ПК [Ф]

```
MSYS_NO_PATHCONV=1 docker run --rm --user 1000:1000 -v "$(pwd -W):/s" -w /s homensai-vpn-python39:local sh -c \
 'python3 -m unittest discover -s router/tests; cd router/tests && for f in lua/test_*.lua; do lua5.1 $f >/dev/null 2>&1 || echo LUAFAIL $f; done'
```
Итог 31.10.2026: 1427 тестов Python OK, все Lua-наборы OK.

- `test_lua_backend.py` + `lua/backend_differential.lua`: 545 случаев, Python против Lua на одних входах — `section_id/policy_order/policy_hash` (именованные, анонимные, с привязкой процесса, со списками и юникодом), `choose` (41 вариант, в т.ч. все отказы), `resolve_pair`/`diagnose`/`scoped_samples`, `attest`/`missing_only`/`unrouted`/дайджест ядра на всех мутациях из `test_kernel_policy.py`, `static_bindings`, `normalized_network`/`config_digest`/`static_firewall_digest`, `recovery_settings.fingerprint`, шаги и доказательства `rollback_recovery`, `from_kernel`, `_zones`, чтение состояния hnat, `valid_record`; и 50 вызовов целых методов `Linux` на одном поддельном роутере (Python — с подменой `command`/`Path`/времени, Lua — `backend_fake.lua`): `diagnostic()` в 23 вариантах (блокировки, выбор, `vendor_identity`, `settings_hash`, `coordination`), `kernel_fingerprint()`, `attest_policy()` (в т.ч. «verified» и «repairable_missing»), `order()`, `candidates()`, запрос мгновенного переключения, текст nft guard.
- `lua/test_backend.lua` (15): кэши отвечают только на неизменённые чтения, второй `diagnostic()` без скриптов/процессов, ходы `reorder` и данные для `record_step`, guard, мост и память отрицательного `health`, `clear_native_options`, `apply` через `rtp2.sh`, `record_step`, разбор `/proc` и `/proc/locks`.
- `lua/test_auto_recovery.lua` (8): рестарт в WAIT-CLIENT с настоящими помощниками восстановления, записанный шаг без авторизации — отказ и счётчик, `order_allowed`, `vendor_rebuild_applies`, отказ `finalize`, Stop во время переключения, резидентная история и кэш `status.json`.
- `test_lua_auto_service.py` (6): init-скрипт (по умолчанию и `lua_auto='0'` — Python, `'1'` — Lua в том же экземпляре `native`, без файлов Lua — Python), мост (только свои файлы ОЗУ; ответы probe/trace), взаимное исключение `native.lock` Python ↔ Lua.

## 7. Риски

| Риск | Чем закрыт / что проверить |
|---|---|
| Порт расходится с Python на живых данных роутера | шаг 1 (сравнение до включения); 545 случаев на ПК [Ф] |
| Части, проверенные только Lua-тестами или не проверенные: `_workers` на настоящем `/proc`, dmesg/hnat, `preparation_status`, `rtp_boot` (права через busybox `stat`), `set_disabled` в процессе, CAS `gl_process_vpn` через libuci, фоновое снятие guard через `setsid`, `spawn/wait`, SIGTERM в uloop | [П] шаги 1–4; при любом отказе — возврат к Python |
| SIGTERM прерывает чтение вывода команды (EINTR) | команда считается неудачной → обычный отказ/откат (в безопасную сторону) |
| Резидентная история +1–2 МБ памяти; повтор inode за ту же секунду при двух чужих перезаписях | [О] практически исключено; сброс статистики меняет ключ |
| Без `nixio.fs` каждый ключ кэша — процесс `stat` | шаг 1 п. 2: без `nixio.fs` пункт не включать |
| `rollback_package` = `2.0.0-lua-alpha2`: при смене линии счётчик неудачных откатов сбрасывается один раз | так задумано и в Python (другая версия пакета → свежий бюджет) |

## 7. Первые запуски на MT3000 (31.10.2026) и что исправлено

Все запуски — с откатом к Python; после каждого сбоя Auto снова работает на Python (OBSERVING).

| Сборка | Что произошло на роутере [Ф] | Причина | Исправление |
|---|---|---|---|
| 2.0.0-alpha1 | при старте Auto процесс Lua упал с `sys: unsafe command argument`; procd перезапустил его, журнал восстановлен в STOPPED, защита LAN не осталась | задание снятия защиты LAN содержит `'{ "br-lan" }'` (как в Python), а `quote()` не пропускает кавычку | alpha2: задание передаётся в `sh -c` с экранированными кавычками; тест на настоящем `sys.lua` |
| 2.0.0-alpha2 | Auto на Lua дошёл до OBSERVING за 138 с (как Python), затем процесс начал падать каждые ~13 с (86 перезапусков) с `bad argument #2 to 'mkdir'`; Auto ушёл в остановку и застрял в PAIR-CLEANUP; возврат к Python восстановил STOPPED за 13 с | nixio принимает права только строкой (`'700'`), а не числом; `nixio.open` не принимает флаги `'wx'`; на роутере нет `stat(1)`, поэтому `lstat_exact` всегда возвращал nil | alpha3: права строкой; `O_CREAT|O_EXCL` через `nixio.open_flags`; `lstat_exact` через nixio (права из `modestr`, сверка с `modedec`) |
| 2.0.0-alpha3 | без падений: в покое 22,5 % ядра и 12,1 МБ (Python: 55,7 % и 40,6 МБ); 6 из 6 ручных переключений (трафик 2,6 с, кнопка 4,0 с); 2 из 2 автосбоев с возвратом; kill во время APPLYING → журнал откатан за 7,4 с (SUPERVISOR-RECOVERY), Auto выключен по замыслу (как в Python: `fence_recovery` не возобновляет), но уборка пары 8 мин отказывала `PAIR-NETWORK-WRITE-FAILED`; Python убрал за 22 с | `sys.chunk` не передавал stdin: `NETWORK_WRITE` читает задание через `io.read('*a')` и получал пустой stdin процесса | alpha4: `io.read` внутри чанка отдаёт его stdin; самопроверка выполняет настоящие NETWORK_READ/NETWORK_WRITE в процессе на копии `/etc/config/network` |

Уроки и защита в alpha3:
- **Самопроверка `sys.lua` на роутере** (`router/tests/lua/router_sys_selftest.lua`): копия в `/tmp`, все вызовы `sys` на настоящих nixio/libubus/libuci в отдельной папке, служба не затрагивается. Запускается перед каждым включением `lua_auto`. На alpha2 нашла все три ошибки; на исправленном коде — 15 из 15; с alpha4 — 17 проверок, включая запись сети на копии.
- **Страховка от падений:** ошибка Lua (не отказ) записывается в `RUNTIME/lua-auto-crashes.json`; при третьей за 10 минут процесс отпускает `native.lock` и заменяет себя супервизором Python (`nixio.exec`, тот же pid — Stop от procd доходит), в журнал системы пишется `LUA-AUTO-FALLBACK`, подробности — в `RUNTIME/lua-auto-fallback.json`. Python остаётся до перезапуска службы.
- Ошибки Lua теперь пишутся с местом возникновения (`debug.traceback`), а не только со строкой `auto.lua:240`.
- На роутере нет команд `stat` и `setsid` (проверено); остальные команды, которые вызывает Lua, есть.
