# Воспроизведение переключений: браузер → backend → ядро QEMU

Это локальная QA-связка для исходников. Она не выпускает пакет и не устанавливает Auto VPN на роутер. Основной handoff `docs/handoff/TODO-CLAUDE-SWITCHING-2026-10-28.ru.md` отсутствовал в доступной истории; этот стенд не заменяет его обязательные проверки.

## Что действительно выполняется

- Chromium загружает текущий сгенерированный LuCI dashboard и делает обычные браузерные клики по Primary/Reserve/Resume Auto.
- Python вызывает настоящие `pair_manual.request`, `consume`, `recover`, `pair_auto.tick`, `streak`, `diagnose`, `Linux.recovery_ready`, `native_switch.attempt` и код `native_switch.child`.
- Настоящий Lua 5.1/cjson разбирает policy; производственные order/hash/CAS и журналы операций используются без подмены решений.
- В отдельной виртуальной машине OpenWrt 21.02.7 x86/64, Linux 5.4.238, iptables 1.8.7 реально меняется mangle graph. Производственный attestor читает точные `iptables-save -t mangle` и `ip -4 -j rule show` из гостевого ядра. Каждый apply сохраняет эти правила рядом с transaction journal.
- Полный browser-сценарий проверяет оба ручных направления, потерянный ACK, восстановление очереди без повторного apply, Resume, автоматический failover/failback, минимальный dwell, последующий tick и сохранение лимита попыток.

## Где используются синтетические данные

UCI inventory и vendor RTP compiler представлены адаптером на основе `test_pair_manual_bound_context.BoundManualContext`. DNS/HTTPS health, exit address, netifd client-up, guard/device operations и запуск worker — синтетические. Код native child выполняется, но отдельный процесс native supervisor/procd здесь не запускается. Health/history samples контролируются тестом; функции принятия решения не подменяются. Доказательством считается конфигурация реального гостевого ядра, а не передача пакетов физического LAN-клиента.

`browser_presentation.js` отдельно использует явно синтетические RPC/status overlays для состояния DEGRADED, неполного отклика, истечения таймера и коррекции часов. Эти проверки не отправляют переключение в Python/QEMU.

Это не проверка физического GL-MT3000, его прошивки, штатного `/usr/bin/rtp2.sh`, tunnel workers, реальных VPN-соединений, LAN DNS/HTTPS/exit, power-cut и штатной установки пакета. Она также не заменяет утверждённые Docker CI images Python 3.9/3.11.

## Требования и параметры

Нужны Python 3.11, Lua 5.1 с cjson, `bwrap`, QEMU x86_64, Node.js с Playwright и Chromium. В выполненном прогоне использовались Python 3.11.17, Chromium 156.0.8078.73, Playwright 1.62.1, QEMU 8.2.2. OpenWrt image/kernel и IPK фиксированы SHA-256 в скриптах и manifest.

Все пути задаются окружением; скрипты не содержат пути к рабочей машине автора. `QA_REPO` — checkout исходников, `QA_OUTPUT` — каталог evidence, `QA_QEMU_ROOT` — отдельный каталог гостевых файлов, `QA_CHROMIUM` — executable Chromium, `QA_PLAYWRIGHT` — путь к установленному модулю Playwright при необходимости. Для отдельного сравнения UI можно задать `QA_ASSETS_REPO` на checkout прежней версии: runtime-код всё равно берётся из `QA_REPO`, что явно отражено hashes в отчёте.

```sh
export QA_REPO="$PWD"
export QA_OUTPUT="$QA_REPO/qa/evidence/switching-2026-10-28"
export QA_QEMU_ROOT="/absolute/path/to/disposable-qa-qemu"
export QA_CHROMIUM="/absolute/path/to/chrome"
export QA_PLAYWRIGHT="/absolute/path/to/node_modules/playwright"
export QA_REAL_KERNEL=1
export QA_LABEL=kernel-final
qa_scripts="$QA_OUTPUT/reproduction"
```

`lua5.1` должен быть в PATH, а `LUA_CPATH` должен находить `cjson.so`. Порты по умолчанию: QA HTTP 127.0.0.1:18988, QEMU serial 127.0.0.1:14555. Их можно изменить через `QA_HTTP_PORT` и `QA_QEMU_SERIAL_PORT`. Адрес serial намеренно ограничен loopback; параметры реального роутера не поддерживаются.

## Подготовка одноразового гостя

```sh
python3 "$qa_scripts/prepare_qemu.py" --download
python3 "$qa_scripts/qemu_launch.py"
```

В другом терминале, после загрузки OpenWrt:

```sh
python3 "$qa_scripts/prepare_qemu.py" --bootstrap
```

Launcher использует установленный `qemu-system-x86_64` либо извлечённый binary под `QA_QEMU_ROOT/root`. Он работает через TCG, private serial/QMP и user-mode NAT; TAP/bridge/host firewall не используются. Guest image никогда не является диском физического роутера. Bootstrap сверяет PID нашего QEMU, путь его диска/serial и точную guest release/kernel, затем создаёт marker `/tmp/HOMENSAI_VIRTUAL_LAB`. Public IPK передаются с временного loopback HTTP 18989, SHA проверяется и на host, и в guest. До завершения bootstrap нужен свободный порт 18989. Скрипты правил требуют marker и x86/64 target перед каждой командой.

## Последовательность проверок

Сначала отрицательные проверки ядра, пока browser bridge не работает:

```sh
QA_LABEL=final "$qa_scripts/run_isolated.sh" python3 "$qa_scripts/qemu_kernel_roundtrip.py"
```

Ожидаются 9 PASS: две рабочие роли, отказ при неверном mark/mask, отсутствии LAN/PREROUTING hook, чужом PREROUTING mark, раннем blackhole и подтверждение восстановленного графа. Не запускайте этот сценарий параллельно с browser bridge: оба управляют одним одноразовым guest graph.

Затем отдельным процессом запустите bridge **с read-only host filesystem**:

```sh
"$qa_scripts/run_isolated.sh" python3 "$qa_scripts/browser_backend.py"
```

И из другого терминала:

```sh
node "$qa_scripts/browser_end_to_end.js"
QA_LABEL=final node "$qa_scripts/browser_presentation.js"
"$qa_scripts/run_isolated.sh" python3 "$qa_scripts/auto_foreign_kernel.py"
```

`auto_foreign_kernel.py` запускайте последним, после завершения полного browser-сценария. Он проверяет конкретный отказ `KERNEL-POLICY-UNVERIFIED`, неизменный граф/fingerprint, отсутствие apply и сохранение бюджета, затем восстанавливает fixture. Исчерпанный бюджет не принимается за доказательство запрета чужого графа.

Для финальной правки только текста применяется отдельный `browser_copy_smoke.js` на заново запущенном bridge: он проверяет render, один настоящий click и подтверждённый переход в QEMU. Его новый asset SHA хранится отдельно от полного предшествующего сценария; вся матрица на новом тексте не считается повторённой.

`run_isolated.sh` создаёт private user/mount namespace, делает host filesystem read-only, даёт запись только в `QA_OUTPUT`, выделяет private `/tmp` и снимает capabilities. Сеть namespace общая только ради loopback QA HTTP/serial; скрипт не имеет host network privileges. Отчёт сохраняет readonly flags `/etc` и `/run`, effective capabilities, commit и SHA загруженных модулей. Любой product-путь, не перенаправленный в fixture, должен отказать в записи; read-only ограничения ради зелёного теста не снимаются.

Для отдельного Auto smoke можно на свежем bridge использовать `auto_api_probe.py`. Для stale-poll regression `browser_race.js` рассчитан на свежий **model** bridge (`QA_REAL_KERNEL=0`), где исходно выбран reserve; этот вариант доказывает browser/queue correlation и не доказывает ядро. Полный real-kernel сценарий выбирает направление динамически.

Укажите уникальный `QA_LABEL` перед повторным запуском: отчёты и screenshots с тем же именем перезаписываются. Запускайте browser bridge заново после изменения кода — Python и generated JS замораживаются на старте. Не используйте уже отработавшую очередь/бюджет для нового полного сценария.

## Известная ошибка раннего QA harness

Ранний fixture перенаправлял `PERSIST`, но не производную константу `CERT`, и оставил синтетический certificate на executor host. Его содержимое не включено в evidence; metadata/hash и исправление описаны в `../qa-isolation-incident.json`. После этого все derived paths перенаправлены и финальные bridge-прогоны требуют read-only host `/etc` и `/run`. Только финальные isolated отчёты считаются итоговой проверкой.

Останавливайте собственные QA HTTP процессы после завершения. Гостю можно дать `sync; poweroff` через приватный serial; при необходимости завершить только PID QEMU, записанный launcher. Физический роутер эти команды не адресуют.
