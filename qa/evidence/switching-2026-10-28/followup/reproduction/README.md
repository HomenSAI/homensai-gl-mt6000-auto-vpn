# Повторная проверка оставшихся рисков

Этот набор продолжает исправления в PR #2. Прежние результаты не запускались заново без причины. Новые сценарии проверяют задержанный ответ статуса и остановку процесса между перестановками UCI. Они не заменяют основной отсутствующий handoff, утверждённый Docker CI и приёмку физического роутера.

## Браузер: задержанный ответ

`browser_delayed_status.js` открывает настоящий Chromium и точный generated dashboard. Он поднимает только статическую страницу на `127.0.0.1`; все RPC, профили, подтверждение ядра и измерения сайтов явно синтетические. Вызовы контроллера, QEMU и устройства этим скриптом не выполняются.

Сначала поступает свежий кадр: server time 1000, controller heartbeat 990, kernel proof 1000 с TTL 15 секунд, оба замера сайтов 975 с TTL 45 секунд. Следующий ответ содержит строго тот же кадр. Chromium выполняет 24 секунды собственных таймеров перед его доставкой — меньше 30-секундного RPC deadline. Проверяется, что доставка не делает доказательства свежими снова. Затем обычный браузерный клик открывает Minimum, где оба замера должны явно остаться просроченными.

Baseline dashboard133 SHA256 `6f6a44c98b638adb312300a4e10ddba4d8c92907beaa21efff7ee891af586779` воспроизвёл ложное обновление состояния. `browser-delayed-status-baseline.json` сохраняет первый прогон; `browser-delayed-status-baseline-verified.json` повторяет тот же сценарий с точной проверкой зелёного sidebar lamp вместо слишком узкой проверки буквальной строки «Auto works». Исходный неудачный результат не заменён. Исправленный dashboard134 SHA256 `161e4fdadd948d970d60931b0944a1b185c299da785ba1cc79ea992e65c274de` прошёл все 12 проверок. Fixture сообщает версию alpha59, что видно в footer.

```sh
export QA_REPO=/absolute/path/to/repository
export QA_OUTPUT=/absolute/path/to/new-evidence-directory
export QA_CHROMIUM=/absolute/path/to/chromium
export QA_PLAYWRIGHT=/absolute/path/to/node_modules/playwright
export QA_LABEL=alpha59-recheck
mkdir -p "$QA_OUTPUT"
qa_base="$QA_REPO/qa/evidence/switching-2026-10-28"
"$qa_base/reproduction/run_isolated.sh" node "$qa_base/followup/reproduction/browser_delayed_status.js"
```

Для сохранённого прежнего asset задайте `QA_DASHBOARD=/path/to/dashboard133-baseline.js` и `QA_APP_VERSION=0.9.1-alpha58`. Имя отчёта содержит `QA_LABEL`; не используйте одну метку для разных прогонов. `QA_HTTP_PORT` позволяет выбрать другой loopback-порт вместо 18987. Browser и статический сервер закрываются в `finally`.

## Процесс: авария внутри восстановления порядка

`real_rollback_crash.py` использует `router/tests/test_rollback_order_steps.py`. Третий generic rule находится между primary и reserve, поэтому восстановление исходного порядка сессии требует двух UCI moves.

Отдельный Linux-процесс, созданный через `fork`, исполняет настоящий `native_switch.rollback`. Адаптер останавливает только этот процесс сигналом SIGKILL после первого или второго move. Журнал записывается производственным кодом на диск; синтетические UCI-данные и pending delta также сохраняются на диск для передачи родительскому процессу. Родитель проверяет точку аварии, меняет control revision, записывает Stop/OFF и вызывает настоящее восстановление `SUPERVISOR-RECOVERY`.

В отдельном OpenWrt/QEMU реально читаются и меняются netfilter/IP rules. Production attestor проверяет точные результаты `iptables-save -t mangle` и `ip -4 -j rule show`. При аварии ядро обязано остаться неизменным; после успешного восстановления нужны точный записанный порядок, только оставшиеся moves, один commit pending delta, один vendor dispatch, подтверждённая итоговая роль, терминальный журнал и сохранённый Auto OFF.

UCI, vendor RTP compiler, health/diagnostic observations и nft guard остаются адаптерами. Это реальный process kill и реальное гостевое ядро, но не проверка `procd`, потери питания, физической прошивки GL.iNet или LAN-пакетов через VPN.

Нужен уже подготовленный disposable QEMU из основного [описания воспроизведения](../../reproduction/README.md). В каждый момент только один QA-процесс может менять его правила. Задайте `QA_QEMU_ROOT`, обеспечьте Lua5.1/cjson в `PATH`/`LUA_CPATH`, затем:

```sh
export QA_LABEL=alpha59-final
"$qa_base/reproduction/run_isolated.sh" python3 "$qa_base/followup/reproduction/real_rollback_crash.py"
```

Baseline использовал архив производственного кода commit `32b26f62f0c8db587bac065eae1c7e6d31404b44` и только новый test fixture. Его SHA записан в `source.extra_test_fixture_sha256`. Для такого архива задайте `QA_REPO` на архив, а `QA_REPRODUCTION` — на каталог общих QEMU helper scripts в проверяемом checkout. Никакие product-файлы baseline не исправлялись ради воспроизведения.

Все derived runtime/persistent paths перенаправлены в приватный временный каталог. Скрипт требует read-only host `/etc` и `/run`, а также нулевые effective capabilities. Нативные network commands направляются только в гостя с проверенным marker и x86/64 identity. Родитель ожидает завершение только собственного PID; тайм-аут ограничен. Полные снимки журналов, команд и правил сохраняются отдельно для каждого случая.

## Доступность обязательных проверок

`audit_followup.py` выполняет только локальное чтение и сохраняет `qa-followup-availability.json`. Он разделяет исходники committed HEAD и параллельные незакоммиченные изменения. Старый `real-child-crash-baseline.json` из `lab/test_process_crash.py` правильно учитывается как реальный SIGKILL файловой модели; он не запускает production rollback/UCI/kernel.

Утверждённые Docker images, daemon/OCI tools и делегированная cgroup-среда в этой сессии недоступны. Python3.11 Dockerfile использует два прежних локальных образа, а пересборка Python3.9 из публичной базы с неприкреплённым apt шагом не доказывает идентичность утверждённому образу. Отдельные portable Python3.9/3.11 прогоны этот gate не закрывают. Системный Docker, subuid/subgid, cgroups и host network не изменялись.

Приватный `private/ACTIVE-EXECUTOR.local.json` отсутствует. Физические адреса и учётные данные не угадывались; обращений к роутерам нет. Ранний синтетический certificate на executor host проверяется только по metadata/hash; файл не удаляется и не изменяется. Финальный followup summary указывает фактические hashes и cleanup, а выпуск и установка остаются заблокированы.
# Итог передачи: выполнено и осталось непроверенным

Окончательный UI: alpha59/dashboard134, SHA256 `ec7f62847a5ea87d6fbcd995a4088d2d282bb3826e0d9504519e0e081d7181a0`. `browser-delayed-status-alpha59-complete-final.json` — **16/16 PASS**, включает delayed-response и cross-tab feedback. Для этого запуска используется текущий `browser_delayed_status.js` с `QA_CROSS_TAB=1`. Его RPC/status явно синтетические; обычный browser click не отправляет команду production backend/ядру. Старый файл `browser-delayed-status-alpha59-final.json` сохраняет **промежуточные 12/12** на `161e4f…`, несмотря на слово final в историческом имени.

`real-rollback-crash-baseline.json` содержит два полностью выполненных отрицательных baseline с реальными отдельными процессами, SIGKILL и QEMU kernel: оба FAIL. **Финальные повторы этих двух сценариев и третий forward-proof promotion case не запускались: NOT_VERIFIED после автоматического прерывания QA-сессии сервисом.** Третий сценарий в независимый script ещё не добавлен. Ни описанные ниже ожидаемые результаты, ни unit tests не являются свидетельством успешного финального прогона.

Собственный гостевой QEMU после повторной проверки PID/executable/диска завершён. Новому исполнителю нужен новый явно изолированный disposable guest; прежний процесс не работает. Подробности: `../verification-summary.json`, `../qa-service-interruption.json`, `../qa-followup-cleanup.json`. Ни один физический роутер не опрашивался.

---
