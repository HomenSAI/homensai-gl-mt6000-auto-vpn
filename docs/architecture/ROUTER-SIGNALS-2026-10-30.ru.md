<!-- doc-role: proposal -->
# Сигналы роутера: каталог источников событий и состояния для ускорения Auto VPN

Дата: 30.10.2026 · База: исходники 0.9.1-alpha82 (`work/switching-finish-20261028`) · Устройство: GL-MT3000 (MT7981, GL 4.11.0 / OpenWrt 21.02, ядро 5.4.211, procd/ubus/rpcd/netifd, fw3 + iptables, nftables 0.9.6, dnsmasq, `rtp2.sh`, mtkhnat).

Статус: **исследование и предложение, без реализации и без работы с устройством.** Факты о ядре/OpenWrt — из документации и исходников upstream; факты о GL-специфике (имена демонов, lock-файлы, кто вызывает `rtp2.sh`) частично известны из нашего кода (`mt3000_manual_platform._workers`, `rollback_recovery.vendor_lock_pid`, `native_platform.wait_quiet`) и статического аудита (`docs/FAILOVER-RESEARCH.md`), остальное помечено **«проверить пробой»**. Для проверки написан read-only скрипт `private/claude-beta1-install/signals_probe.py` (см. §6).

Связанный документ: `docs/architecture/NEW-CORE-2026-10-30.ru.md` (резидентное ядро, быстрый путь переключения, §3.3 быстрое обнаружение). Этот каталог — «сырьё» для его наблюдателей W1–W3.

---

## 1. Откуда сейчас берутся задержки (замеры alpha77–82)

| Этап | Сейчас | Чем ждём | Механизм ожидания в коде |
|---|---|---|---|
| Переключение APPLYING→COMMITTED | 46–76 с (ср. 63) | `rtp2.sh` 10–15 с + 5–7 полных диагностик + `wait_quiet` | `native_platform.wait_quiet`: скан всего `/proc` каждые 0,75 с, нужно ≥3 с и ≥4 «тихих» выборок подряд; `vendor_settled`: `kernel_fingerprint()` (2× `iptables-save`, 2× `ip rule`) каждые 3 с до двух одинаковых подряд, до 60 с |
| Обнаружение отказа | 30–60 с + ≈55 с подтверждения | только полная квора DNS + 3×HTTPS по интервалу | `agent.serve` / `probe_policy.Booster` |
| Возврат | 38–57 с | то же, что переключение | — |
| После обновления пакета | Auto ждёт 2–4 мин `VENDOR-SETTLING` | `VendorObserver`: `stable>=2` проходов монитора (60 с на уровне 1) | `vendor_observation.py`, `observation_freshness.settle_for` |
| Блокеры `VENDOR-WORKER-BUSY` / `OBSERVATION-STALE` | возникают вокруг активности GL | опрос `/proc`, `rtp2.lock`, очереди `gl_reload_service` | `native_switch.py:670`, `pair_auto.TRANSIENT_START` |
| `DNS-001` на резерве во время возврата | эпизодически | DNS-проба попадает в окно перезапуска dnsmasq, который `rtp2.sh` делает в фоне | — |
| OpenVPN over TCP | частые переподключения | замечаем только через провал кворы | — |

Общий знаменатель: **мы угадываем «производитель закончил» по отсутствию активности в опросе**, вместо того чтобы слушать события, которые ядро и netifd/procd уже публикуют. Каждый опрос — это fork/exec (`iptables-save`, `ip`, `ubus`, `lua`) на двухъядерном A53, где fork+exec Python-процессом стоит десятки миллисекунд, а `iptables-save` при большой mangle — сотни.

---

## 2. Классы сигналов

1. **Push-события** (стоимость ≈0 в покое, задержка — миллисекунды): rtnetlink, `ubus listen`, `ubus subscribe`, `logread -f`, conntrack netlink, `nft monitor`, inotify, hotplug.
2. **Дешёвые pull-чтения** (без fork, микросекунды): `/sys/class/net/*/statistics`, `/proc/*` (loadavg, stat, net/snmp, net/tcp, locks, diskstats), `/sys/class/ubi`.
3. **Дорогие pull-чтения** (fork+exec, 10–500 мс): `iptables-save`, `ip -j`, `wg show`, `ubus call`, `uci`, `lua`.

Правило проектирования: **push для «что-то изменилось» → дешёвый pull для «каково состояние» → дорогой pull только при изменении или перед записью.**

---

## 3. Каталог

Обозначения колонки «Приоритет»: **P1** — прототипировать первым; **P2** — после P1; **P3** — справочно/позже. «Риск» — что может сломаться или ввести в заблуждение.

### 3.1 rtnetlink: link / addr / route / rule события (`ip monitor`)

- **Что даёт.** Мгновенные события `RTM_NEWLINK/DELLINK` (появление/исчезновение `wgclientN`/`tunN`, смена operstate/carrier), `RTM_NEWADDR/DELADDR`, `RTM_NEWROUTE/DELROUTE` (с номером таблицы и протоколом), `RTM_NEWRULE/DELRULE` (fwmark-правила туннелей). Ровно то, из чего состоят `device/mark/table/ifindex` в нашей привязке канала (`route_binding`, `VendorObserver._kernel`).
- **Как читать.** Отладка: `ip monitor link address route rule` (или `ip -ts monitor ...`). В резиденте — **без fork**: `socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)`, `bind((0, RTMGRP_LINK|RTMGRP_IPV4_IFADDR|RTMGRP_IPV4_ROUTE|RTMGRP_IPV4_RULE|RTMGRP_IPV6_ROUTE))` = `0x1|0x10|0x40|0x80|0x400`. Стандартный модуль `socket` Python 3.9 это умеет; заголовок `struct nlmsghdr` = `'=IHHII'`. Проба проверяет это на устройстве (`passive_events.rtnetlink`).
- **Стоимость.** ≈0 в покое; при пересборке `rtp2` — десятки–сотни сообщений, разбор в Python — миллисекунды.
- **Задержка.** < 1 мс от изменения в ядре.
- **Заменяет опрос?** Да, для маршрутов/правил/линков. **Не** видит iptables-legacy mangle (у xtables-legacy событий нет) — см. 3.10.
- **Ускорение.**
  - *Vendor-settling / wait_quiet:* «последнее route/rule/link-событие было > Q с назад» — объективный критерий окончания пересборки сетевой части. Сейчас `vendor_settled` ждёт два совпадения `kernel_fingerprint()` с шагом 3 с (минимум 3–6 с + 4 fork на выборку), а после обновления — 2 прохода монитора (до 120 с).
  - *Наблюдатель поколений:* эпоха привязки меняется только при событии по нашему device/table/rule. Нет события → привязка та же → `SETTLED` можно объявить сразу после первой полной проверки (2–4 мин → секунды).
  - *Обнаружение:* `DELLINK`/`operstate down` туннеля = мгновенное подозрение (сейчас ждём ближайшей кворы).
- **Приоритет: P1. Риск: низкий** (только чтение). Нюансы: при всплеске возможен `ENOBUFS` — тогда сбросить кэш и сделать один полный pull; события от WireGuard-хэндшейков не приходят (это не rtnetlink).

### 3.2 netifd через ubus: `network.interface` события и dump

- **Что даёт.** `ubus listen network.interface` → `{"action":"ifup"|"ifdown"|"ifupdate", "interface":"wgclient1"}`; `ubus call network.interface dump` → по каждому интерфейсу `up`, `pending`, `available`, `uptime`, `l3_device`, `route[]`, `dns-server[]`, `errors[]`. Поле **`uptime` сбрасывается при каждом переподключении** — это точный счётчик реконнектов OpenVPN/WireGuard-протоколов netifd без парсинга логов.
- **Как читать.** `ubus -t 0 listen network.interface` (резидентный дочерний процесс, одна строка JSON на событие); `ubus call network.interface dump` (один fork вместо N вызовов `network.interface.<name> status`, как сейчас в `mt3000_manual_platform.binding`). Также `ubus listen network.device` (если netifd его публикует — **проверить**).
- **Стоимость.** listen ≈0; dump — 1 fork (`cost_ms.ubus_interface_dump` в пробе), ответ единицы КБ.
- **Задержка.** 10–100 мс после действия netifd.
- **Заменяет опрос?** Частично: состояние up/pending/uptime по событию, полные данные — dump по событию.
- **Ускорение.** Подозрение отказа при `ifdown`/`ifup` туннеля — сразу; на возврате/переключении — «интерфейс резерва поднят и `uptime` монотонно растёт с момента X» вместо повторных `RESERVE-NOT-CONNECTED`; учёт реконнектов OpenVPN TCP по скачкам `uptime`.
- **Приоритет: P1. Риск: низкий.** `ubus listen` надо перезапускать при рестарте `ubusd` (редко; детект по EOF).

### 3.3 ubus: появление/исчезновение объектов (`ubus.object.add/remove`)

- **Что даёт.** Каждый демон, регистрирующий ubus-объект (dnsmasq → `dnsmasq`, netifd, rpcd-плагины, GL-демоны), при старте/падении публикует `ubus.object.add` / `ubus.object.remove` с именем объекта.
- **Как читать.** `ubus listen ubus.object.add ubus.object.remove` (или общий `ubus listen` с фильтром).
- **Ускорение.** **Конкретно против `DNS-001` на резерве во время возврата:** `rtp2.sh` перезапускает dnsmasq в фоне; DNS-пробу через резерв запускать только после `ubus.object.add dnsmasq` + ≈1 с (или после смены pid dnsmasq в `ubus call service list '{"name":"dnsmasq"}'`). Убирает ложные `DNS-001` и, как следствие, лишние ≈55 с подтверждения/отмены.
- **Приоритет: P1. Риск: низкий.** Проверить пробой, что dnsmasq на GL 4.11 собран с ubus (`ubus list` содержит `dnsmasq`; `ubus call dnsmasq metrics` отвечает).

### 3.4 procd: сервисы и экземпляры

- **Что даёт.** `ubus call service list` — каждый init-сервис: экземпляры, `running`, `pid`, `respawn`, `exit_code`, триггеры (`config.change`). Смена pid = перезапуск (firewall как сервис без процесса, dnsmasq, openvpn-экземпляры GL, `gl_*`).
- **События.** В procd есть уведомления объекта `service` (`ubus subscribe service`: `instance.start`, `instance.stop`/`instance.fail` — **проверить** на сборке GL 4.11; проба делает 15-секундный `ubus subscribe service`). Отдельно `ubus listen config.change` / событие `service` от `reload_config` — показывает, что кто-то сделал `uci commit` + `reload_config` и procd сейчас перезапустит связанные сервисы (а значит, скоро будет fw3/dnsmasq/network-активность).
- **Стоимость.** subscribe ≈0; `service list` — 1 fork, ответ 10–50 КБ (дороже dump).
- **Ускорение.** Точный конец «перезапуска сервиса», в т.ч. фоновых действий `rtp2.sh` (dnsmasq restart, firewall reload через `/etc/init.d/firewall`). Сейчас мы ищем имена процессов в `/proc` (`_workers`) — это видит только *идущий* процесс и дорого (полный скан `/proc`, `cmdline`+`stat`+`wchan` на каждый pid, дважды).
- **Приоритет: P2** (после подтверждения, что `subscribe service` работает). **Риск:** низкий; не вызывать `ubus call service event/set/delete` — это запись.

### 3.5 hotplug (`/etc/hotplug.d/iface`, `net`, `ntp`, `firewall`)

- **Что даёт.** procd запускает скрипты hotplug на `ifup/ifdown/ifupdate` интерфейсов (`ACTION`, `INTERFACE`, `DEVICE`), появление сетевых устройств (`net`), синхронизацию времени (`ntp`, `stratum`). Именно отсюда (по статическому аудиту) GL запускает failover-триггер и, вероятно, `rtp2.sh` при поднятии туннеля — проба перечисляет `/etc/hotplug.d/*` и ищет упоминания `rtp2`/`route_policy`/`tunnel-switch`.
- **Как использовать.** Вариант A (без изменений системы): косвенно — через 3.2. Вариант B: свой скрипт `/etc/hotplug.d/iface/99-homensai`, который делает только `ubus send homensai.hotplug '{...}'` (≈5 мс) — даёт **порядок** событий относительно GL-скриптов с меньшими номерами.
- **Ускорение.** Узнать момент, когда GL-скрипт hotplug (и его фоновые потомки) стартовал, — начало окна «производитель занят» без опроса.
- **Ntp.** `hotplug.d/ntp` (`ACTION=stratum`) — после синхронизации времени; полезно для старта: наши часы/истории валидны, `abs(wall-monotonic)` перестаёт скакать (см. `MT3000-COLLECTION-CLOCK-CHANGED`).
- **Приоритет: P2. Риск: средний** — скрипты hotplug выполняются **последовательно** в очереди procd; медленный скрипт задерживает все последующие, включая GL. Скрипт должен быть однострочным, без Python. Установка — новый файл в пакете (требует пересборки пакета, не прототип «на живую»).

### 3.6 GL-специфика: VPN-клиент, `rtp2.sh`, lock-файлы, очереди

- **Известно из нашего кода:** `/usr/bin/rtp2.sh` (SHA-256 закреплён), lock `/tmp/run/rtp2.lock` (pid внутри, EXIT-trap), `/var/run/tunnel-switch*.lock`, fw3-локи `/tmp/run/fw3.lock`, `/tmp/lock/procd_firewall.lock`, очереди `/var/run/gl_reload_service`, `/var/run/gl_restart_service`, процессы `fw3`, `gl_block_wan_access_exit`, `tunnel-switch.sh`, `vpn-failover-trigger.sh`, `vpn-failover-watcher.sh`, `wgclient.sh`, `ovpnclient.sh`, `hotplug-call`, include `gl_vpn_rules` в firewall.
- **Цепочка `rtp2`** (статический аудит + наблюдения): uci `route_policy` → `rtp2.sh` → flush mangle-цепочек → пересоздание секций firewall → маршруты/правила → DNS (`/tmp/resolv.conf.d`, `hosts.vpn`, dnsmasq restart **в фоне**) → `clean_conntrack` → `uci commit` (флеш) → firewall reload **в фоне**. Выход `rtp2.sh` ≠ конец работы — отсюда `wait_quiet`.
- **Что мониторить дополнительно.**
  1. **`/proc/locks` по inode** известных lock-файлов (уже делается в `_held_firewall_locks`) — дешевле полного скана `/proc`: одно чтение файла ≈1–3 КБ.
  2. **inotify** на `/tmp/run` (создание/удаление `rtp2.lock`, `tunnel-switch*.lock`, `fw3.lock`), `/var/run/gl_reload_service` (появление элементов очереди), `/etc/config` (запись `route_policy`, `firewall`, `network`), `/var/run/fw3.state`, `/tmp/resolv.conf.d`. Python 3.9 без сторонних модулей: `ctypes` → `inotify_init1/inotify_add_watch` из libc (**проверить наличие `python3-ctypes`**, проба: `platform.python_ctypes`); иначе `inotifywait` (обычно нет); иначе stat-опрос mtime раз в 0,25–0,5 с (≈мкс, без fork).
  3. **ubus-объекты GL** (`ubus list` — проба собирает имена и методы объектов с `gl`, `vpn`, `route`, `clients` в имени). Если у GL есть объект клиента VPN со статусом/событиями — это прямой источник «производитель переподключает туннель».
  4. **Процессы-потомки hotplug** — `ppid`-дерево от `procd` → `hotplug-call` → GL-скрипт; проба выдаёт `ppid`, `start_s_after_boot`, `wchan`.
- **Ускорение.** Конец работы `rtp2` = (lock снят) ∧ (нет route/rule-событий Q с) ∧ (хэш mangle стабилен) ∧ (dnsmasq снова в ubus) ∧ (очередь `gl_reload_service` пуста). Всё это push или ≤1 мс pull → `wait_quiet` укладывается в Q+δ (оценка 2–4 с) вместо 3–20 с опроса; `vendor_settled` — вместо 6–60 с.
- **Приоритет: P1 (inotify/locks), P2 (GL ubus-объекты — сперва узнать, что есть). Риск:** читать lock-файлы — безопасно; **никогда** не брать flock на их inode (заблокируем GL).

### 3.7 WireGuard: хэндшейки и счётчики

- **Что даёт.** На пира: `latest-handshake` (unix-время), `rx/tx bytes`, `endpoint`, `persistent-keepalive`. Протокол: при трафике ре-хэндшейк каждые 120 с (REKEY_AFTER_TIME); если хэндшейка нет > 180 с (REJECT_AFTER_TIME), сессия мертва и пакеты не шифруются; при попытке передачи без ответа — повторные инициации каждые 5 с (REKEY_TIMEOUT) до 90 с.
- **Как читать.** `wg show all dump` / `wg show <dev> latest-handshakes` / `transfer` (1 fork, мелкий вывод; в дампе есть **приватные ключи** — парсить, не логировать). Без fork: genetlink семейство `wireguard`, `WG_CMD_GET_DEVICE` с `NLM_F_DUMP` (разбор вложенных атрибутов вручную в Python — ≈150 строк). **Событий WireGuard через netlink нет** (у семейства нет multicast-групп — проба это проверяет `wireguard.genetlink.mcast_groups`), значит это pull, но дешёвый.
- **Стоимость.** fork ≈10–30 мс (`cost_ms.wg_show_all_latest_handshakes`); genetlink ≈0,1 мс.
- **Ускорение обнаружения.** Сигнал «`tx` растёт, `rx` не растёт ≥ 5–10 с при keepalive/трафике» или «handshake старше 135–180 с при росте tx» — сильное подозрение за **5–15 с** (сейчас 30–60 с + 55 с). Доказательство отказа остаётся кворой (принцип NEW-CORE §3.3), но запускается сразу и плотно.
- **Подтверждение переключения:** на целевом WG — `rx` растёт после коммита → туннель реально несёт трафик.
- **Приоритет: P1. Риск:** низкий; ложные подозрения при простое без keepalive (нет трафика → нет хэндшейков) — нужно условие «есть tx».

### 3.8 OpenVPN: management, status-файл, outer TCP-сокет, логи

- **Что даёт.** management (`--management <sock|ip port>`): `state` (CONNECTING/WAIT/AUTH/GET_CONFIG/ASSIGN_IP/CONNECTED/RECONNECTING/EXITING), `bytecount N` (push счётчиков), `>STATE:` real-time. status-файл (`--status file N`): байты TCP/UDP read/write, время обновления. **GL, по-видимому, management не включает — проверить** (проба читает cmdline и конфиг openvpn, только флаги/директивы, без содержимого).
- **Важно.** Management-интерфейс допускает **одного** клиента; подключение к сокету GL (если он есть) может отнять его у GL-демона. Проба **не подключается**.
- **Outer TCP-сокет (для proto tcp-client).** `/proc/net/tcp` строка сокета openvpn (найти по inode из `/proc/<pid>/fd`): `tx_queue` растёт, `retransmits`/`timer` = таймер ретрансмита → деградация пути до сервера видна **до** `ping-restart`/«Connection reset». `/proc/net/netstat TcpExt: TCPTimeouts, TCPLossProbes, TCPAbortOnTimeout` — общесистемно.
- **Логи** (`logread -f`, см. 3.15): `Initialization Sequence Completed` (готов), `SIGUSR1[soft,connection-reset]`/`ping-restart`/`Restart pause` (переподключение), `Inactivity timeout`, `TLS Error`. Позволяет считать частоту реконнектов TCP-туннелей и коррелировать с `keepalive`/`ping-restart` из конфига (проба отдаёт `ping_settings`).
- **Ускорение.** Подозрение для OpenVPN за 2–10 с (реконнект/рост очереди) вместо ожидания провала кворы. Для «OpenVPN over TCP переподключается часто» — данные для рекомендации владельцу (UDP-профиль, `keepalive 10 60`, `tcp-nodelay`) и для штрафа надёжности канала.
- **Приоритет: P1 (логи + uptime из 3.2 + outer TCP), P3 (management — только если GL его не использует и можно включить в своём профиле). Риск:** management — высокий (конфликт с GL); остальное низкий.

### 3.9 Счётчики интерфейсов `/sys/class/net/<dev>/statistics`

- **Что даёт.** `rx/tx_bytes`, `rx/tx_packets`, `*_errors`, `*_dropped`, а также `operstate`, `carrier_changes` (для tun/wg — счётчик открытий/закрытий), `ifindex`.
- **Стоимость.** ≈5–20 мкс на файл, без fork (`cost_ms.sysfs_read_x100` в пробе). Можно читать раз в 1 с для всех туннелей.
- **Ускорение.** (1) Подозрение «tx растёт, rx стоит» — для любого протокола (3.7/3.8). (2) **Подтверждение переключения по факту:** `br-lan rx` растёт и `tx_bytes` целевого туннеля растёт, а у исходного — падает → трафик LAN реально ушёл на новый канал (это в т.ч. частичное закрытие пробела `lan_path_verified=false`). (3) Выбор времени тяжёлых операций (speed-test, контрольные точки) при низком трафике.
- **Оговорка mtkhnat:** аппаратно выгруженные потоки WAN↔LAN могут не проходить через счётчики программных интерфейсов; трафик в wg/tun (шифрование на CPU) через PPE обычно не выгружается — **проверить** пробой (`offload`, `rate_1s` по `br-lan`/`eth*`/`wgclient*`).
- **Приоритет: P1. Риск:** низкий.

### 3.10 iptables / nftables: счётчики и обнаружение изменений правил

- **Что даёт.** `iptables-save -c -t mangle` — пакеты/байты по каждому правилу, включая `ROUTE_POLICY` → `TUNNELxx` jump и `MARK --set-xmark`. Рост счётчика jump'а целевого туннеля после коммита = **новые LAN-соединения действительно маркируются на новый туннель** (подтверждение на уровне пакетов LAN, а не только router-originated).
- **Обнаружение изменений.** У iptables-legacy событий нет. Варианты: (а) хэш вывода `iptables-save -t mangle` (fork, 30–300 мс — проба меряет `cost_ms.iptables_save_c_mangle`); (б) без fork — `getsockopt(IPT_SO_GET_INFO)` (возвращает `valid_hooks`, `num_entries`, `size`) раз в 1 с: изменение `size/num_entries` = изменение таблицы, затем `IPT_SO_GET_ENTRIES` и хэш blob'а только при изменении (предложено в NEW-CORE §2.2; в Python — через `socket.getsockopt(fd, IPPROTO_IP, 64, buflen)` на raw-сокете, **требует root, проверить**). Если `iptables -V` покажет `nf_tables` (iptables-nft), то `nft monitor ruleset` даёт **push-события** на любое изменение fw3 — проба это выясняет (`platform.iptables_version`).
- **nft.** Наш guard-стол (`inet homensai…`) — `nft monitor tables chains rules sets` (push). `nft list ruleset` целиком — только по событию.
- **Ускорение.** Конец пересборки mangle по стабильности `num_entries/size` (≈мкс) вместо 2× `iptables-save` каждые 3 с; подтверждение переключения по счётчикам за 1–3 с вместо повторной полной диагностики.
- **Приоритет: P1 (счётчики ROUTE_POLICY при подтверждении), P2 (getsockopt-хэш). Риск:** `iptables -L` берёт xtables-lock — **использовать только `iptables-save`** (не берёт lock); getsockopt — только чтение, но нужно аккуратно с размерами буфера.

### 3.11 conntrack: счётчики, per-mark распределение, события

- **Что даёт.** `/proc/sys/net/netfilter/nf_conntrack_count`/`_max`; `/proc/net/nf_conntrack` (если procfs включён) — каждая запись с `mark=` → распределение соединений по `ctmark & 0xf000` (маски туннелей GL). События: `NETLINK_NETFILTER`, группы `NFNLGRP_CONNTRACK_NEW/DESTROY` (`conntrack -E`, если утилита есть; в Python — сырой сокет), только при `nf_conntrack_events=1`.
- **Стоимость.** count — ≈мкс. Полный разбор `/proc/net/nf_conntrack` — пропорционально числу записей (сотни–тысячи → 10–200 мс, без fork; проба меряет `cost_ms.proc_nf_conntrack_parse`). События — высокий поток при активной LAN (сотни/с), включать **только** на окно подтверждения (5–10 с после коммита).
- **Ускорение.** (1) **Подтверждение переключения из перспективы LAN:** после коммита доля новых соединений с меткой целевого туннеля растёт (`CT_NEW` с нужной меткой за первые секунды) → COMMITTED можно подтвердить за 1–5 с. (2) Видеть, сколько «застряло» соединений на метке отказавшего туннеля (вопрос NEW-CORE §3.4 п.7 — удаление conntrack по метке). (3) Детект `clean_conntrack` GL: резкое падение count.
- **Приоритет: P2** (сначала проверить, что procfs/нетлинк доступны, `nf_conntrack_netlink` загружен). **Риск:** средний по CPU при постоянной подписке; удаление записей — это уже запись (вне каталога сигналов).

### 3.12 dnsmasq: upstream, кэш, перезапуски

- **Что даёт.** `/var/etc/dnsmasq.conf.*` (`server=` строки, в т.ч. `server=/domain/ip` для VPN), `/tmp/resolv.conf.d/resolv.conf.auto` (upstream от netifd), GL-файлы `/tmp/resolv.conf.vpn`/`hosts.vpn` (**проверить имена**), `ubus call dnsmasq metrics` (cache inserted/evicted, forwarded, auth answered и т.п. — **проверить** набор полей), логи `using nameserver …`, `started`, `read /tmp/hosts…`.
- **Как читать.** inotify/mtime на файлы конфигурации и resolv; pid/старт процесса (`/proc/<pid>/stat` поле 22) или `ubus.object.add dnsmasq`.
- **Ускорение.** (1) Против `DNS-001` во время возврата — см. 3.3: ждать «dnsmasq перечитал upstream» (mtime файла серверов < времени старта dnsmasq, объект в ubus) и только потом DNS-пробу. (2) Для быстрого пути переключения (NEW-CORE §3.4): знать, какой upstream привязан к какому туннелю, и проверять, что после коммита он указывает на целевой. (3) `metrics.forwarded` растёт, а ответы не приходят → подозрение на DNS-путь туннеля.
- **Приоритет: P1 (перезапуск dnsmasq как сигнал готовности DNS), P2 (metrics). Риск:** `killall -USR1 dnsmasq` (дамп статистики в лог) — это сигнал чужому процессу, **не использовать**; читать только ubus/файлы.

### 3.13 fw3: маркеры перезагрузки

- **Что даёт.** `/var/run/fw3.state` (mtime = последняя загрузка правил), `/tmp/run/fw3.lock` (fw3 держит flock во время работы — видно в `/proc/locks`), процесс `fw3` и `/etc/init.d/firewall`, лог `Reloading firewall`/`fw3`, include `/usr/bin/rtp2.sh` (секция `firewall.vpnclient`) — **каждый `fw3 reload` снова вызывает include**, т.е. может снова запускать пересборку GL.
- **Ускорение.** Точное окно «firewall перезагружается»: start = flock появился, end = flock снят ∧ `fw3.state` mtime обновлён. Push через inotify на `fw3.state`.
- **Приоритет: P1** (вместе с 3.6). **Риск:** низкий.

### 3.14 mtkhnat / flow offload

- **Что даёт.** Включён ли HW/SW offload (`uci firewall.@defaults[0].flow_offloading[_hw]`, `FLOWOFFLOAD` в filter FORWARD, модули `mtkhnat`/`nf_flow_table*`, debugfs `/sys/kernel/debug/hnat/*` при смонтированном debugfs), признаки `[OFFLOAD]`/`[HW_OFFLOAD]` в conntrack.
- **Зачем.** Выгруженные потоки (а) не проходят mangle → их маршрут не меняется после переключения до истечения flow; (б) не видны в программных счётчиках. Это влияет на интерпретацию 3.9–3.11 и на «сессии старого канала».
- **Приоритет: P2** (сначала факт из пробы). **Риск:** чтение debugfs безопасно, но **запись** в `hnat_setting`/`hnat_entry` недопустима; debugfs может быть не смонтирован — не монтировать.

### 3.15 logread / syslog

- **Что даёт.** Единый поток событий всех демонов: netifd (`Interface 'X' is now up/down`, `has lost the connection`), openvpn (3.8), dnsmasq (`started`, `using nameserver`), firewall/fw3, hotplug-скрипты GL (если пишут через `logger`), kernel (`link is up/down`, `nf_conntrack: table full`).
- **Как читать.** Резидентный `logread -f -l 1` (подписка на logd через ubus, ≈0 в покое; строка за ≈мс). Фильтр регулярками; **никогда** не сохранять строки dnsmasq `query[…]/reply` (приватность) и любые строки без редактирования IP/ключей.
- **Ускорение.** Временные метки начала/конца действий производителя и реконнектов OpenVPN с точностью до секунды без опроса; источник для причины сбоя (`TLS Error` vs `Inactivity timeout` vs `Connection refused`).
- **Приоритет: P1 (как дополнительный источник, не как доказательство). Риск:** формат логов не контракт (меняется между прошивками) — использовать как подсказку/подозрение, решения — по ядру/квору; при переполнении буфера logd строки теряются.

### 3.16 `/proc/net/*`: tcp, snmp, netstat, sockstat

- **Что даёт.** `/proc/net/snmp` (Tcp: `RetransSegs`, `AttemptFails`, `EstabResets`; Udp: `InErrors`, `RcvbufErrors`, `NoPorts`), `/proc/net/netstat TcpExt` (`TCPTimeouts`, `TCPLossProbes`, `TCPAbortOnTimeout`, `TCPSynRetrans`), `/proc/net/tcp` (по сокетам: очереди, таймеры, ретрансмиты), `sockstat` (число сокетов, память).
- **Ускорение.** Дельта `TCPSynRetrans`/`AttemptFails` во время наших HTTPS-проб и у outer-сокета OpenVPN TCP → различение «туннель мёртв» и «один сайт не отвечает»; плюс подсказка для 3.8. Дёшево (≈мкс, без fork).
- **Приоритет: P2. Риск:** низкий; глобальные счётчики смешивают весь трафик роутера.

### 3.17 Нагрузка: `/proc/stat`, `/proc/loadavg`, PSI, ctxt/forks

- **Что даёт.** Загрузка CPU по ядрам (user/system/iowait/softirq), `ctxt`/с, `processes` (форки/с), `procs_running/blocked`, `/proc/pressure/{cpu,io,memory}` (если ядро собрано с PSI — **проверить**; в 5.4 есть, но OpenWrt часто выключает).
- **Ускорение.** (1) **Адаптивные тайм-ауты:** наши пробы и `wait_quiet` растягиваются, когда A53 занят пересборкой GL/шифрованием; если softirq > 50 % или PSI cpu some > X — увеличить тайм-аут пробы вместо ложного провала (снижает ложные `VPN-003` и лишние подтверждения). (2) Метрика стоимости собственных опросов (forks/с при открытой странице — см. NEW-CORE §2.1). (3) «Занятость производителя» как вспомогательный признак: всплеск forks/с при `rtp2`.
- **Приоритет: P2. Риск:** низкий.

### 3.18 Флеш: `/proc/diskstats`, UBI, `/proc/<pid>/io`

- **Что даёт.** На MT3000 overlay — UBIFS на UBI на SPI-NAND; **UBIFS не блочное устройство**, поэтому в `/proc/diskstats` записи `mtdblockN` почти не отражают запись overlay. Реальные индикаторы: `/sys/class/ubi/ubiX/max_ec` (максимальный счётчик стираний; рост = износ), `mean_ec` (если есть), `bad_peb_count`, `avail_eraseblocks`; **`/proc/<pid>/io: write_bytes`** — сколько каждый процесс отправил на запись в блочный уровень/ФС (наш агент, `uci`, GL-демоны). `uci commit` в `rtp2.sh` — тоже запись.
- **Ускорение.** Не скорость, а ресурс: измерить, сколько пишем мы vs GL за сутки; выявить «скрытые» писатели. Позволяет обоснованно выбирать интервал контрольной точки (NEW-CORE §2.3).
- **Приоритет: P2. Риск:** низкий.

### 3.19 Прочее, что стоит иметь в виду

| Сигнал | Что даёт | Как | Прио/риск |
|---|---|---|---|
| `ubus call system info` | uptime, load, память — один fork | — | P3 / низкий |
| `/proc/locks` | кто держит flock на lock-файлах GL/fw3 (по inode) | чтение файла | P1 (уже есть) / низкий |
| `/proc/<pid>/wchan` | процесс ждёт lock (`locks_lock_inode_wait`) — признак очереди GL | чтение | P2 / низкий |
| `/etc/crontabs/root` | периодические GL-задачи, создающие активность в известное время | чтение | P3 / низкий |
| ARP/neigh (`RTMGRP_NEIGH`) | присутствие LAN-клиентов, их активность | rtnetlink | P3 / шумно, приватность (MAC) |
| `odhcpd`/`dnsmasq` DHCP leases | число активных клиентов (для «есть ли трафик») | `/tmp/dhcp.leases` | P3 / приватность |
| `nf_conntrack: table full` (kernel log) | переполнение таблицы → массовые обрывы | logread | P2 / низкий |

---

## 4. Сводная таблица

| # | Сигнал | Тип | Стоимость | Задержка | Заменяет опрос | Обнаружение | Подтверждение переключения | Vendor-settling | Старт | Прио | Риск |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.1 | rtnetlink link/addr/route/rule | push, без fork | ≈0 | <1 мс | да (кроме mangle) | подозрение (DELLINK) | привязка не изменилась | **да, главный** | да | P1 | низкий |
| 3.2 | ubus `network.interface` + dump/uptime | push + 1 fork | ≈0 / 1 fork | 10–100 мс | частично | да (ifdown, реконнект) | резерв up, uptime | да | да | P1 | низкий |
| 3.3 | ubus `object.add/remove` (dnsmasq) | push | ≈0 | <100 мс | да | — | DNS готов | да | да | P1 | низкий |
| 3.4 | procd `service` | push/1 fork | ≈0 / 10–50 КБ | <100 мс | частично | — | — | да | да | P2 | низкий |
| 3.5 | hotplug свой скрипт | push | ≈5 мс/событие | мс | да | да | — | да | да | P2 | средний (очередь procd) |
| 3.6 | GL locks/очереди inotify | push/≈мкс pull | ≈0 | мс | да | — | — | **да** | да | P1 | низкий |
| 3.7 | WireGuard handshake/transfer | pull | genl ≈0,1 мс / fork 10–30 мс | 1 с | — | **да** | rx растёт | — | — | P1 | низкий |
| 3.8 | OpenVPN логи/outer TCP/status | push+pull | ≈0 | 1 с | — | **да** | — | — | — | P1 | низкий (mgmt — высокий) |
| 3.9 | `/sys/class/net` counters | pull ≈мкс | ≈0 | 1 с | — | **да** | **да** | — | — | P1 | низкий |
| 3.10 | iptables counters / getsockopt хэш | pull | 1 fork / ≈мкс | 1 с | да (хэш) | — | **да** | **да** | — | P1/P2 | низкий |
| 3.11 | conntrack per-mark / события | pull/push | 10–200 мс / поток | мс | — | — | **да (LAN)** | — | — | P2 | средний (CPU) |
| 3.12 | dnsmasq файлы/metrics | push/pull | ≈0 | мс | — | DNS | DNS цели | да | — | P1/P2 | низкий |
| 3.13 | fw3 state/lock | push | ≈0 | мс | да | — | — | **да** | — | P1 | низкий |
| 3.14 | mtkhnat/offload | pull редкий | ≈0 | — | — | — | интерпретация | — | — | P2 | низкий (только чтение) |
| 3.15 | `logread -f` | push | ≈0 | ≈мс | частично | подсказка | — | подсказка | — | P1 | средний (формат не контракт) |
| 3.16 | `/proc/net/snmp,netstat,tcp` | pull ≈мкс | ≈0 | 1 с | — | детализация | — | — | — | P2 | низкий |
| 3.17 | CPU/PSI/forks | pull ≈мкс | ≈0 | 1 с | — | адаптивные тайм-ауты | — | — | — | P2 | низкий |
| 3.18 | UBI/pid io | pull редкий | ≈0 | — | — | — | — | — | — | P2 | низкий |

---

## 5. Что прототипировать первым и ожидаемый эффект

Все цифры — **оценки** до прототипа; проверять на выделенном MT3000 только в согласованном окне и по `private/ACTIVE-EXECUTOR.local.json`.

1. **«Vendor activity detector» = rtnetlink (3.1) + inotify/`/proc/locks` на lock-файлах GL/fw3 (3.6, 3.13) + `ubus.object.add dnsmasq` (3.3) + `size/num_entries` mangle (3.10б).** Критерий «производитель закончил»: lock снят ∧ Q=2–3 с без route/rule-событий ∧ mangle стабилен ∧ dnsmasq в ubus ∧ очередь `gl_reload_service` пуста. Заменяет `wait_quiet` (скан `/proc` каждые 0,75 с) и `vendor_settled` (`kernel_fingerprint` каждые 3 с).
   *Эффект:* переключение −8…−20 с (из 63 с), возврат −8…−15 с; блокеры `VENDOR-WORKER-BUSY` превращаются в точное ожидание события, а не повторную попытку. CPU в ожидании — с ≈сотен мс/с до ≈0.
2. **Поколения привязки по событиям (3.1 + 3.2) вместо «2 стабильных прохода монитора».** `SETTLED` = нет netlink/netifd-события по device/table/rule туннеля за Q с после первой полной проверки; состояние поколений переживает перезапуск монитора в `/var/run` (уже предложено в NEW-CORE фазе 1).
   *Эффект:* `VENDOR-SETTLING` после обновления пакета 2–4 мин → 10–40 с; меньше `OBSERVATION-STALE`.
3. **Пассивное подозрение отказа (3.7 WireGuard handshake/rx, 3.9 sysfs-счётчики, 3.8 OpenVPN логи/uptime/outer TCP, 3.2 ifdown).** Подозрение запускает плотное подтверждение (3 кворы с шагом 3 с), доказательство не меняется.
   *Эффект:* обнаружение+подтверждение ≈85–115 с → 15–30 с (оценка совпадает с NEW-CORE §3.3).
4. **Подтверждение переключения по факту LAN-трафика (3.10 счётчики `ROUTE_POLICY` + 3.9 + 3.11 per-mark).** Вместо повторных полных диагностик после `rtp2`: аттестация один раз по событию изменения mangle, затем 1–3 с наблюдения роста счётчиков целевого jump/туннеля.
   *Эффект:* −5…−10 с в хвосте переключения; дополнительное доказательство пути LAN (частично закрывает `lan_path_verified=false` — но не заменяет внешний LAN-тест).
5. **Готовность DNS после фонового рестарта dnsmasq (3.3 + 3.12).** DNS-пробу на резерве/цели не запускать, пока dnsmasq не перерегистрировался и не прочитал upstream.
   *Эффект:* исчезают ложные `DNS-001` на возврате и связанные с ними ≈55 с повторов.

Дополнительно, **без изменения логики**, сразу полезно: замер стоимости наших fork-команд (проба `command_costs`) — чтобы приоритизировать, какие опросы переводить на netlink/sysfs первыми.

**Рискованное (не делать без отдельного решения):** подключение к management-сокету OpenVPN GL; постоянная подписка на conntrack-события; собственные hotplug-скрипты с тяжёлой логикой; любые записи в debugfs hnat; `flock` на lock-файлах GL; сигналы чужим процессам (`USR1` dnsmasq). Логи — только как подсказка, не как доказательство.

**Архитектурная заметка.** Все push-источники требуют **резидентного** процесса (монитор уже резидентен — `agent.serve`). Прототип на Python 3.9 возможен целиком на stdlib: `socket.AF_NETLINK` (rtnetlink, genetlink, nfnetlink), `selectors` для мультиплексирования, `subprocess.Popen` для `ubus listen`/`logread -f`, `ctypes` для inotify (если пакет есть). Это же ложится в Go-ядро NEW-CORE (vishvananda/netlink, wgctrl, ti-mo/conntrack) без смены модели.

---

## 6. Проба `signals_probe.py`

Файл: `private/claude-beta1-install/signals_probe.py` (локальный, не публикуется).

- **Запуск (на роутере, через stdin):** `ssh root@<mt3000> 'python3 -' < signals_probe.py > signals-YYYYMMDD-HHMM.json` — только при наличии права на устройство по `private/ACTIVE-EXECUTOR.local.json`. Время ≈25–60 с (внутренний бюджет 75 с, лимит 120 с).
- **Гарантии read-only:** нет записи файлов (только stdout), нет `uci set/commit`, нет изменений nft/iptables (только `iptables-save`, `nft list`), нет перезапусков и сигналов чужим процессам (завершаются только собственные дочерние `ubus listen`/`logread -f` по тайм-ауту), нет подключения к management OpenVPN, netlink-подписки только пассивные; conntrack-подписка и genetlink-запрос WireGuard — только если соответствующий модуль уже загружен (чтобы не вызвать автозагрузку модуля).
- **Редактирование:** приватные ключи WireGuard не выводятся вовсе; длинные base64/hex-токены, `password=/token=/user=`-значения, e-mail, MAC, не-RFC1918 IPv4 (кроме 1.1.1.1/1.0.0.1/8.8.8.8/8.8.4.4/9.9.9.9/149.112.112.112), глобальные IPv6 и большинство FQDN заменяются стабильными метками (`<pub1>`, `<host2>`) в пределах одного прогона. Строки DNS-запросов dnsmasq отбрасываются. Перед сохранением/публикацией вывод всё равно просмотреть.
- **Разделы JSON:** `platform` (модули, бинарники, ctypes, PSI, версия iptables), `ubus` (объекты, методы GL/VPN-объектов, `dnsmasq metrics`), `interfaces` (dump с uptime), `procd_services`, `wireguard` (без ключей, возраст handshake, genetlink mcast-группы), `openvpn` (флаги, директивы, management/status наличие, outer TCP-сокеты), `routing`, `netfilter` (счётчики mangle по цепочкам, правила ROUTE_POLICY без адресов), `conntrack` (sysctl, распределение по `ctmark&0xf000`, offload), `offload`, `dns`, `vendor` (lock-файлы, hotplug.d, кто ссылается на `rtp2`, cron), `processes` (RSS, CPU, write_bytes, wchan), `logread` (200 последних отфильтрованных строк + счётчики шаблонов), `kernel_net_stats`, `net_counters` (+скорость за 1 с), `load` (CPU за 1 с, forks/с, PSI), `flash` (diskstats, UBI, топ писателей), `homensai`, `command_costs` (медианная стоимость fork-команд), `passive_events` (15-секундное окно `ubus listen`, `ubus subscribe service`, `logread -f`, rtnetlink, conntrack-события), `cost_ms`, `sections_failed`.
- **Рекомендуемая серия:** (1) в покое; (2) во время/сразу после ручного переключения (в согласованном окне) — `passive_events` покажет реальную последовательность событий `rtp2`; (3) сразу после обновления пакета — для `VENDOR-SETTLING`.

---

## 7. Открытые вопросы, которые закрывает проба

1. iptables на GL 4.11 — legacy или nft (`iptables -V`)? Если nft — `nft monitor` даёт push на изменения fw3.
2. Есть ли `python3-ctypes` (inotify без бинарников)?
3. Есть ли у WireGuard multicast-группы (ожидаем «нет»)?
4. Включены ли `nf_conntrack_events`, procfs conntrack, загружен ли `nf_conntrack_netlink`?
5. Публикует ли procd `instance.*` через `ubus subscribe service` на этой сборке?
6. Есть ли у GL ubus-объект VPN-клиента со статусом/уведомлениями?
7. Включает ли GL management/status у OpenVPN; какие `keepalive/ping-restart`?
8. Какие hotplug-скрипты и init-скрипты ссылаются на `rtp2.sh`/`route_policy`?
9. Включён ли HW/SW flow offload и попадают ли туннельные потоки в offload?
10. Реальная стоимость fork-команд на A53 (`command_costs`) — для приоритизации.
