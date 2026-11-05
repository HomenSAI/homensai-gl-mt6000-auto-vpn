# DNS клиентов LAN через оба туннеля сразу / LAN DNS through both tunnels (03.11.2026)

HomenS.AI Auto VPN, ветка `feat/dns-both-tunnels-20261103` от `83e4f7cb` (2.1.0-alpha6). Опция владельца
`dns_dual`, по умолчанию **выключена**. Обе среды (Lua и Python) ведут себя одинаково; общие случаи —
`router/tests/dns_dual_cases.json`.

## Как DNS устроен в GL 4.11 (аудит прошивки, `/usr/bin/setup_instance`, `/etc/init.d/dnsmasq`)

- У каждого VPN-экземпляра свой dnsmasq: секция `dhcp.<экземпляр>`, порт `2053+100·N` (wgclientN) или `4053+100·N`
  (ovpnclientN), `conf-dir=/tmp/dnsmasq.d.<экземпляр>` с файлом `mark` (`mark=0x1000` для wgclient1, `mark=0xb000` для
  ovpnclient2), `resolv-file=/tmp/resolv.conf.d/resolv.conf.<экземпляр>` (DNS, который дал туннель) или, при
  `gl-dns-v2 override_vpn`, `no-resolv` и `server=` из основного dnsmasq. Сгенерированный файл —
  `/var/etc/dnsmasq.conf.<экземпляр>`.
- `mark=` (патч GL, «Specify the outgoing packet mark», строки бинарника dnsmasq 2.92) ставит метку на каждый сокет к
  вышестоящему DNS; `ip rule fwmark <метка>/0xf000 lookup <1000+N|1010+N>` (pref 6000) отправляет его в таблицу, где
  есть только маршрут в туннель и `blackhole` (метрика 254). Упавший туннель не уходит в WAN.
- Модуль `dns_mark` перенаправляет DNS клиента LAN на порт экземпляра активного туннеля (DNS-FOLLOWS-CHANNEL).
- dnsmasq запускается procd без ujail (ujail в прошивке нет). `conf-dir` читается только при старте экземпляра;
  `/etc/init.d/dnsmasq reload` (его зовёт ovpnclient-up) шлёт SIGHUP и не перезапускает экземпляр — строки `server=`
  из conf-dir при этом сохраняются. `/etc/init.d/dnsmasq restart <экземпляр>` (rc.common: `procd_kill` одного
  экземпляра и `add`) перезапускает только его.

## Что делает программа

Пока Auto работает (проверенный проход супервизора, `backend.dns_mark_follow` → `dns_dual_follow`), каждому
экземпляру пары кладётся файл `/tmp/dnsmasq.d.<экземпляр>/homensai-dns-dual.conf`:

```
# HomenS.AI Auto VPN: LAN DNS through both tunnels (dns_dual). Generated; removed when Auto stops.
all-servers
server=103.86.99.100@ovpnclient2
server=103.86.96.100@ovpnclient2
```

(в файле wgclient1 — серверы ovpnclient2, в файле ovpnclient2 — серверы wgclient1). dnsmasq экземпляра шлёт каждый
запрос к своим серверам через свой туннель (метка GL, без изменений) и к серверам другого туннеля через другой
туннель; клиенту уходит первый ответ (`all-servers`). При потерях или отказе активного туннеля ответ приходит через
второй, без ожидания решения Auto.

- Серверы другого туннеля: строки `server=` его `/var/etc/dnsmasq.conf.<экземпляр>` и, если нет `no-resolv`,
  `nameserver` его resolv-file — то, что настроил GL, у любого провайдера. Только IPv4 (одноадресный, не 0/8, 127/8,
  169.254/16, 224/4+), необязательный `#порт`, не больше 4. Локальный прокси роутера (`127.0.0.1#5453`) через туннель
  недостижим и пропускается.
- Туннель лежит (resolv-file пуст): остаются серверы, установленные в прошлый раз (взятые из своего же файла
  другого экземпляра), — никаких перезапусков dnsmasq из-за отказа.
- Экземпляр распознаётся только если его метка из графа ядра (`TUNNEL*_ROUTE_POLICY` → `--set-xmark`) совпадает с
  `mark=` в его conf-dir, а conf-dir в сгенерированном файле — ровно `/tmp/dnsmasq.d.<экземпляр>`. Меньше двух —
  ничего не меняется, `DNS-DUAL-UNAVAILABLE`.
- Изменённый файл: атомарная запись → `dnsmasq --test -C /var/etc/dnsmasq.conf.<экземпляр>` → `/etc/init.d/dnsmasq
  restart <экземпляр>` → procd показывает экземпляр запущенным (`ubus call service list`). Активный экземпляр
  (метка dns_mark) перезапускается последним. Ошибка на любом шаге — прежний файл назад (не было — конфигурация GL),
  при необходимости ещё один перезапуск, `DNS-DUAL-UNVERIFIED` в журнале (`DNS-DUAL-SYNC`), тот же текст не пробуется
  до перезапуска процесса/следующего Start. Маршрут трафика не трогается никогда.
- Выключение (`off`): опция выключена (каждый проход), Auto отпустил пару (`backend.unguard`, обе среды), удаление
  пакета (prerm). Каждый файл удаляется, экземпляр перезапускается — снова конфигурация GL. /tmp — RAM:
  перезагрузка убирает файлы сама; после перезагрузки Auto (если продолжает работу) ставит их снова.

## Почему DNS не уходит в WAN (во всех состояниях)

1. Свои серверы экземпляра: путь GL без изменений (метка → таблица туннеля с blackhole).
2. Серверы другого туннеля: `@устройство` — SO_BINDTODEVICE. Ядро для такого сокета ищет маршрут только через это
   устройство (oif): маршрут через другое устройство пропускается, а если подходящего нет (blackhole, нет маршрута),
   пакет считается «on link» этого устройства. Уйти через WAN сокет не может. Нет устройства (OpenVPN упал, tun
   удалён) — bind не проходит, запрос к этому серверу не отправляется. TCP-запросы dnsmasq к таким серверам тоже
   привязываются к устройству.
3. В файле только `all-servers` и `server=<IPv4>[#порт]@<wgclientN|ovpnclientN>` (тест «every written line is bound
   to another GL tunnel» в обеих средах). Основной dnsmasq (тот, что ходит в WAN) не трогается.
4. Во время перезапуска экземпляра (доли секунды) REDIRECT LAN-DNS на его порт никуда не переключается: клиент получает
   отказ порта и повторяет запрос, обхода через основной dnsmasq нет.
5. Auto выключен/остановлен: файлов нет — поведение GL без изменений. Оба туннеля лежат: ответов нет, как и раньше.
   IPv6: серверы IPv6 не пишутся; IPv6 LAN режет страж.

## Почему по умолчанию выключено

Нет доступа к роутеру в этой работе: не проверено на MT3000, что dnsmasq GL после сброса прав (пользователь
`dnsmasq_vpn`, ядро 5.4: SO_BINDTODEVICE требует CAP_NET_RAW) действительно привязывает сокет к устройству (по коду
dnsmasq 2.8x+ CAP_NET_RAW сохраняется, если у сервера есть `@interface` или включён ubus — у GL включён, но это
надо увидеть: нет строки `failed to bind server socket` и пакеты идут через второй туннель). Кроме того, включение
перезапускает оба экземпляра (короткий пропуск DNS при Start/Stop). После проверки на роутере (ниже) значение по
умолчанию можно поменять одной строкой (`enabled()` в обеих средах и общие случаи).

Включить: `uci set homensai_vpn.main.dns_dual='1'; uci commit homensai_vpn` (следующий проход Auto ставит файлы).
Выключить: `uci set homensai_vpn.main.dns_dual='0'; uci commit homensai_vpn` (следующий проход убирает).

## Проверка на роутере (координатор, выделенный MT3000)

1. Включить опцию, дождаться прохода Auto. `cat /tmp/dnsmasq.d.wgclient1/homensai-dns-dual.conf` и
   `.../ovpnclient2/...` — строки `server=…@ovpnclient2` / `@wgclient1`; `logread -e DNS-DUAL-SYNC` —
   `instances wgclient1+,ovpnclient2+`; `logread -e dnsmasq | grep -i 'bind server socket'` — пусто;
   `ubus call service list '{"name":"dnsmasq"}'` — оба экземпляра running.
2. Перекрёстный путь: `tcpdump -ni ovpnclient2 udp port 53` при запросе `nslookup hv$RANDOM.example.com 127.0.0.1 -port=2153`
   (или dig `@127.0.0.1 -p 2153`) — пакет к серверу ovpn идёт через ovpnclient2.
3. Утечка: LAN-кит (`private/lan-client-kit`, `--mode command`, `--streams`): счётчики `rdns_*` (DNS самого роутера
   через WAN, хук output) и `leak_*` = 0 весь прогон; дополнительно `tcpdump -ni <wan> port 53` — 0 пакетов.
4. Деградация: `tc qdisc add dev wgclient1 root netem loss 30%` на 120 с (`--mode command --command "…"`, уборка
   кита проверяет остаток netem), случайные имена DNS (`dns_random`), сравнить `dns_failed`/`dns_stall_s` и время
   ответа с `dns_dual=0` и `=1`. Ожидание: при `=1` DNS почти без отказов.
5. Отказ: режим `fault` (дроп wgclient1 на 60 с) — `dns_stall_s` при `=1` около 0 до и после ухода Auto на резерв
   (сейчас DNS стоит до перехода dns_mark).
6. Stop Auto: файлов `ls /tmp/dnsmasq.d.*/homensai-dns-dual.conf` нет, экземпляры перезапущены, `DNS-DUAL-SYNC …
   enabled false`. Опция `0` при работающем Auto — то же на следующем проходе.
