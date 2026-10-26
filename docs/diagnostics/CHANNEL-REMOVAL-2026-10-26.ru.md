# Диагностика после изменения VPN-каналов — 26.10.2026

## English

Read-only inspection of the screenshot target, GL-MT3000 at 192.168.11.1, running alpha25. Monitor is running; native controller is stopped with exit code 1. The retained RUNNING pair state predates the current boot and differs from the current network and policy. Installed recovery code propagates PAIR-EXTERNAL-POLICY-CHANGE before entering the controller loop. This failure was reproduced offline against the installed source; no historical startup traceback remains in the available log.

Three bound profiles remain: disabled ovpnclient1 and enabled ovpnclient2/wgclient1. With probe_limit=2, the disabled first entry consumes a slot and wgclient1 is omitted as CHECK-LIMIT. UI channel cells include every bound profile, including the disabled entry. Saved Auto reserve still targets ovpnclient1, whereas the enabled OpenVPN is ovpnclient2. Current alpha26 source retains the same pair recovery code and probe selection, so the new design release alone does not resolve this case.

No router configuration, service, Auto state, routing or firewall was changed. Primary MT6000 was not inspected. Evidence and downloaded application code are private; no credentials were exported.

## Русский

Проверен **роутер со скриншота: GL-MT3000, 192.168.11.1, 0.9.1-alpha25**. Это не проверка отдельного основного MT6000. Последний снимок: `2026-10-26T13:43:07Z`, 14:43 Europe/Berlin. Время хоста и роутера различается примерно на 15 секунд; вывод основан на свежем чтении состояния, не на часах скриншота.

### 1. Лишняя запись существует в текущей конфигурации

| Интерфейс | Профиль | Состояние конфигурации | Последний мониторинг |
|---|---|---|---|
| ovpnclient1 | openvpn:40354_2005 | disabled | PROFILE-INACTIVE |
| ovpnclient2 | openvpn:40354_2020 | enabled | DNS успешно, 2 HTTPS успешно |
| wgclient1 | wireguard:peer_2002 | enabled | CHECK-LIMIT |

Таким образом, два интерфейса включены, но третий всё ещё привязан к серверному профилю в UCI. Это не только старый браузерный кэш. Инвентаризация правильно читает его как отключённый; следующие слои неправильно смешивают наличие привязки и участие в проверке.

Остальные сохранённые серверные профили без интерфейса — каталог импортированных серверов. Их наличие само по себе не означает существование дополнительных работающих каналов. Записей собственных `homensai_vpn server` сейчас нет.

### 2. Отключённый канал расходует лимит проверок

В установленном `agent.py:679` выбираются первые профили с непустым `interface`, затем применяется `probe_limit`. Флаг `administrative_state` при отборе не учитывается.

Фактический лимит — **2**. Порядок: `ovpnclient1`, `ovpnclient2`, `wgclient1`. Первые два занимают лимит; WireGuard получает `CHECK-LIMIT`, хотя включён. Поэтому его работоспособность этим мониторингом **не установлена**, считать его неисправным нельзя.

В `router/connectivity_panel.inc.js` список ячеек также фильтруется только по наличию `interface`. Отключённый канал остаётся на экране. Сохранённый результат ручной проверки и текущий список ячеек могут относиться к разным моментам; исходный RPC скриншота не захвачен, поэтому конкретное происхождение знаменателя «из 2» не установлено.

### 3. Пара Auto больше не соответствует двум включённым каналам

Сохранено:

- основной профиль `wireguard:peer_2003`, туннель `wireguard:wgclient1`;
- резервный профиль `openvpn:40354_2005`, туннель `openvpn:ovpnclient1`.

Сейчас `wgclient1` привязан к `wireguard:peer_2002`; включённый OpenVPN находится на `ovpnclient2`. Выбор контроллера учитывает туннельную привязку, поэтому устаревший ID основного профиля сам по себе ещё не доказывает отказ выбора. Однако сохранённый резервный туннель действительно указывает на старый отключённый интерфейс. Автоматически переименовывать новый канал в резерв без решения владельца нельзя.

### 4. Контроллер Auto остановлен, мониторинг работает

Живой `ubus service list`:

- `monitor`: running=true, PID 16548, статус обновляется;
- `native`: running=false, exit_code=1;
- текущего `native-status.json` нет;
- текущего запроса `pair-auto-control.json` нет;
- постоянный `pair-auto-state.json` остался в фазе `RUNNING`, с владением `wgclient1`/`ovpnclient1`; файл старше текущей загрузки.

Чтение с корректным `process_bindings` подтвердило несовпадение сохранённых порядка/хэша политики, идентичности сети и части защищённых конфигураций.

Механизм ошибки в **скачанном установленном коде**:

1. `native_switch.py:1171` вызывает `pair_recover(backend)` до защищённого основного цикла.
2. `pair_auto.py:355` вызывает cleanup для старой фазы RUNNING.
3. `pair_auto.py:327` при несовпадении политики выбрасывает `ValueError('PAIR-EXTERNAL-POLICY-CHANGE')`.
4. Этот вызов восстановления не перехватывает ошибку и не публикует понятное состояние BLOCKED. Процесс может завершиться вместо продолжения диагностики.

Именно этот путь воспроизведён локально на установленном исходнике с подставными данными и запретом записи. На роутере восстановление и перезапуск **не запускались**. Исторический traceback запуска отсутствует в доступном журнале; механизм подтверждён исходником, текущими несовпадениями и локальным воспроизведением, а не сохранённым traceback реального падения.

Код pair_auto.py в текущей ветке alpha26 совпадает с установленным. Отбор проверяемых профилей и фильтр ячеек также сохраняют описанную логику. Обновление только дизайна не является исправлением этих причин.

### Направление исправления

- Отбирать включённые/пригодные к проверке каналы до применения лимита; отключённый каталог отображать отдельно от текущего результата проверки.
- При изменении состава каналов явно показывать, что сохранённая пара требует повторного выбора, с актуальными именами и привязками.
- Перехватывать конфликт восстановления и публиковать устойчивое диагностическое состояние, сохраняя старую транзакцию для разбора. Не восстанавливать поверх изменённой конфигурации старые сетевые параметры.
- После отдельного исправления проверить сценарии 4→2, смены профиля на том же туннеле и перезагрузки с незавершённой сохранённой сессией.

### Доказательства и границы

Локальные файлы: `private/channel-removal-diagnostic-20261026/live-read.json`, `reproduction.json`, `read_device.py`, `reproduce.py`, `installed-*.py`/`installed-inventory.lua`/`installed-init`.

Результат локального воспроизведения: **REPRODUCED**, `PAIR-EXTERNAL-POLICY-CHANGE`; лимит подтвердил пропуск `wgclient1`. Роутер при воспроизведении не использовался. Диагностика не выполняла тестов скорости, переключений, перезапусков, установки пакетов, изменения конфигурации, сети Windows или состояния Auto. Исправление на устройстве не выполнено.
