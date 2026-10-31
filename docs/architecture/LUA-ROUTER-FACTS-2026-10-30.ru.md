# Факты с роутера для Lua-ядра (MT3000, GL 4.11 / OpenWrt 21.02, 30.10.2026)

Проверено на живом роутере, только чтение и безвредные пробы.

| Возможность | Есть | Следствие для Lua |
|---|---|---|
| lua 5.1, uci (libuci-lua), ubus, uloop, nixio, nixio.fs (lstat), nixio.signal, nixio.nanosleep | да | цикл событий, ubus-объект, uci в процессе |
| nixio сокет: `bindtodevice` | да | пробы привязываются к устройству туннеля |
| nixio сокет: `SO_MARK` (`setopt('socket','mark')`) | **нет** | метка не нужна: см. ниже |
| nixio raw ICMP сокет | да | пинг без дочернего процесса |
| nixio.tls | **нет** | HTTPS-проверки через `curl --interface <dev>` дочерним процессом |
| nixio.crypto sha256 | **нет** | sha256 через `sha256sum` (уже в canon.lua) |
| flock, sha256sum, timeout, conntrack, curl, wget, uclient-fetch, ping | да | |

**Привязка к устройству без метки работает** (ядро при SO_BINDTODEVICE считает адрес на канале, если в таблице нет маршрута через устройство):
- `ping -I wgclient1 1.1.1.1` → 23 мс; `ping -I ovpnclient2 1.1.1.1` → 59 мс;
- `curl --interface wgclient1 https://1.1.1.1/cdn-cgi/trace` → `loc=DE` за 0,17 с; через `ovpnclient2` → `loc=UA` за 0,48 с;
- то есть DNS (UDP) и ICMP из Lua с `bindtodevice`, HTTPS через `curl --interface`, страна выхода проверяется по `cdn-cgi/trace`.

Чтение тех же данных переключения (uci, правила ядра, план, проверка ядра, журнал): Lua 0,08 с и 1,8 МБ, Python 1,9 с и 18,5 МБ. Журнал, записанный Python, Lua читает с совпадающим sha256.
