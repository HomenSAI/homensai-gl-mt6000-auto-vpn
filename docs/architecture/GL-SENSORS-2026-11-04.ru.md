<!-- doc-role: design -->
# Датчики по образцу GL 4.11: WAN или туннель, события WireGuard, «тихий» туннель, кворум целей, системные хуки / GL-based sensors

Дата: 04.11.2026. Ветка `feat/gl-sensors-20261104` от `a3591140` (интеграция 2.1.0-alpha8). Без работы с роутером, без
смены версии. Основание — исследование служб GL 4.11 на MT3000 (`private/gl-services-study/IDEAS.ru.html`, разделы 2–5;
копия файлов GL только для чтения) и волна-3 матисследований (`private/math/wave3/REPORT.ru.html`, исследование 2).
Обе среды (Lua по умолчанию, Python — запасная) решают одинаково: чистые функции — близнецы, общие случаи
`router/tests/gl_sensors_cases.json` (генерируются из Python `router/tests/gen_gl_sensors_cases.py`), проверка Lua —
`router/tests/lua/test_gl_sensors.lua`, Python — `router/tests/test_gl_sensors.py`.

Автор: Serhii Khomenko (HomenS.AI), реализация — Claude. Лицензия проекта — HomenSAI Personal & Commercial Source
License v1.0.

## 0. Коротко

| # | что | по умолчанию | меняет поведение Auto? |
|---|---|---|---|
| 1 | Диагноз «нет интернета у роутера (WAN)» или «упал туннель»: свой эхо-запрос через порт WAN мимо VPN, вердикт GL kmwan, флаг captive portal повторителя, линк WAN, пробы обоих каналов, события WireGuard → маленькая байесовская модель | `wan_sensor` вкл. | да: **WAN-DOWN** — не переключать, пока WAN доказанно лежит; **WAN-RECOVERING** — после возврата WAN ждать одну проверку основного (≤ 30 с); «WAN жив, основной упал, резерв жив» — сразу частые проверки основного |
| 2 | Хук `/etc/hotplug.d/wireguard/60-homensai`: REKEY-TIMEOUT / REKEY-GIVEUP / KEYPAIR-CREATED в файл в RAM | `wg_events` вкл. | только подозрение → частые проверки (никогда не доказательство отказа) |
| 3 | Пассивный датчик «tx растёт, rx стоит ≥ 3 с» по счётчикам sysfs и вето «rx течёт ≥ 10 кбит/с» для потерянных эхо пульса | `stall_sensor` вкл., `stall_veto` вкл. | только подозрение / отмена ложной тревоги пульса |
| 4 | Пульс k-из-n: 3 цели из пула 8 с ротацией, «потерян удар» = 2 из 3 без ответа | `heartbeat_quorum` **выкл.** | не лучше по всем метрикам (раздел 4) — только по желанию владельца |
| 5 | `keep.d` для sysupgrade, плановая перезагрузка GL ≠ отключение питания, сбой ядра ≠ отключение питания, диагностический пакет с маскированием | без настроек | нет (только коды запуска и файл по запросу) |

«Неизвестно» везде = прежнее поведение: без доказательств по WAN нет ни удержания, ни ускорения; без опций пульс работает
ровно по прежнему правилу (одна цель 1.1.1.1 / 8.8.8.8 по очереди, 2 потерянных удара подряд).

## 1. WAN лежит или туннель лежит (пункт 1)

### Как у GL и как было у нас

GL: kmwan в ядре пингует 4 цели на каждый WAN-член (`etc/config/kmwan`), вердикт читает `gl_led` как слово `online` в
`/proc/gl-kmwan/config` (`usr/bin/gl_led:72`); флаг captive portal — `ubus call repeater status` → `portal`
(`gl_led:73-78`). К VPN это не привязано. У нас: все пробы шли через туннели; при падении WAN оба канала «плохие»,
модель канала видит долгий обрыв, проверка резерва проваливается, Auto «BLOCKED/DEGRADED», причины «нет интернета у
роутера» не было (кроме `UPLINK-LINK-DOWN` — только когда линк всех WAN-интерфейсов выключен). Хуже всего — гонка после
возврата WAN: резерв (например, WireGuard) поднимается на секунды раньше основного (OpenVPN по TCP) и получает две
хорошие проверки, пока модель основного ещё «в отказе» → лишнее переключение туда и через `primary_stable` обратно.

### Датчики

* **Своё эхо через WAN** (`wan_diag.Underlay`, ввод-вывод — `lua/gl_sensors.lua`, `gl_sensors.py`): сырой ICMP-сокет с
  `SO_BINDTODEVICE` на устройство WAN (первое поднятое из зоны WAN, тот же список, что для счётчиков WAN), без метки
  туннеля; один эхо-запрос раз в 10 с, раз в 2 с — пока канал не отвечает или WAN под подозрением; цели по кругу 1.1.1.1,
  8.8.8.8, 9.9.9.9, 208.67.222.222 (цели kmwan GL). В Lua ответ читается на следующем такте без блокировки, в Python —
  блокирующее ожидание ≤ 1 с в цикле ожидания монитора.
  * `fail` только после **калибровки** (это устройство хотя бы раз ответило) и **3 неудач подряд по ≥ 2 разным целям**:
    провайдер или firewall, который никогда не пропускает наш ICMP, даёт «неизвестно», а не «WAN лежит».
  * `ok` — ответ не старше 30 с и после него неудач нет; старше 60 с — «неизвестно».
* **Вердикт kmwan** — чтение `/proc/gl-kmwan/config` раз за проход (ноль пакетов): слово `online` → online, иначе слово
  `offline` → offline, иначе неизвестно (формат файла GL не опубликован — проверить на роутере, раздел 7).
* **Captive portal** — `ubus call repeater status` (один форк за проход и только пока основной канал не проходит проверку).
* **Линк WAN** — существующий `status.uplink_observation` (`DOWN` / `LINK-UP`; «линк есть» — не доказательство интернета).
* **Пробы каналов** — новейшая свежая проба основного/резерва: `ok` (код пуст, DNS да, HTTPS ≥ 2), `bad`
  (VPN-001/VPN-003/VPN-MTU), `dns` (DNS-001), иначе неизвестно.
* **Событие WireGuard** основного устройства за 120 с (пункт 2).

### Модель (`wan_diag.posterior`, близнецы `wan_diag.py` / `lua/wan_diag.lua`)

Гипотезы: N (всё хорошо), TUNNEL (упал основной туннель/сервер, резерв жив), SERVER (туннель отвечает на рукопожатие, но
сервер ничего не пропускает), BOTH (оба VPN, WAN жив), WAN (нет интернета у роутера), DNS (DNS в обоих каналах).
Априори 0,968 / 0,012 / 0,004 / 0,004 / 0,010 / 0,002. Наивный Байес: произведение правдоподобий по доступным свидетельствам,
нормировка после каждого множителя (одинаковый порядок операций в обоих языках — одинаковые числа), ответ в промилле.

| свидетельство | N | TUNNEL | SERVER | BOTH | WAN | DNS |
|---|---|---|---|---|---|---|
| эхо WAN ok / fail | .98 / .02 | .98 / .02 | .98 / .02 | .97 / .03 | .02 / .98 | .97 / .03 |
| линк WAN up / down | .999 / .001 | … | … | … | .4 / .6 | .999 / .001 |
| kmwan online / offline | .99 / .01 | … | … | … | .1 / .9 | .99 / .01 |
| portal да / нет | .001 / .999 | … | … | … | .3 / .7 | … |
| основной ok / bad / dns | .97 / .02 / .01 | .03 / .95 / .02 | .03 / .9 / .07 | .03 / .95 / .02 | .01 / .97 / .02 | .05 / .1 / .85 |
| резерв ok / bad / dns | .97 / .02 / .01 | .95 / .03 / .02 | .95 / .03 / .02 | .03 / .95 / .02 | .01 / .97 / .02 | .05 / .1 / .85 |
| WG giveup / timeout / created | .001 / .01 / .05 | .3 / .4 / .01 | .01 / .02 / .3 | .3 / .4 / .01 | .3 / .4 / .01 | .001 / .01 / .05 |

Правила безопасности поверх апостериорной вероятности (никогда не одной вероятностью):

* **hold (WAN-DOWN)**: P(WAN) ≥ 0,95 **и** жёсткое доказательство WAN (эхо `fail`, или линк `down`, или kmwan `offline`)
  **и** основной `bad` **и** резерв не `ok`. Если резерв отвечает — никогда не удерживаем.
* **WAN-RECOVERING** (`wan_diag.Tracker`): после WAN-DOWN удержание продолжается, пока у основного нет здоровой пробы
  новее момента возврата, но не дольше `wan_recover_grace` с (по умолчанию 30, 0 — без ожидания). В проход возврата
  монитор сразу запускает новый проход (обе пары проверяются немедленно).
* **hasten**: WAN доказанно жив (эхо `ok` или kmwan `online`) **и** основной `bad` **и** резерв `ok` **и** P(WAN) ≤ 0,01
  → `Booster.suspect(..., reason 'wan-ok-tunnel-down')`: частые полные проверки основного начинаются сразу. Это
  «ускорение ухода» единственным безопасным рычагом — плотностью проверок; правило самого ухода (HMM, резерв, бюджет) не
  меняется. Одна неудачная проба по Байесу ещё «скорее N» (апостериорно ≈ 0,57), поэтому это просьба о пробах, не вывод.
* код в `status.wan_diagnosis.code`: WAN-DOWN / WAN-RECOVERING / при уверенности ≥ 0,8 DIAG-TUNNEL-DOWN,
  DIAG-VPN-SERVER, DIAG-VPN-BOTH-DOWN, DIAG-WAN-SUSPECT, DIAG-DNS-FAILED / иначе DIAG-UNSURE / null при N.

Как Auto это читает: `failure_diagnosis.diagnose` (Python) и `diagnosis.diagnose` (Lua) после `UPLINK-LINK-DOWN`
возвращают `{code: WAN-DOWN|WAN-RECOVERING, suppress_switch: true}`, если `status.wan_diagnosis.hold` истинно и запись
свежая (окно `observation_valid_for`). Этого достаточно: `pair.lua`/`pair_auto.py` уже не переключают при
`suppress_switch` и публикуют причину (`reason=WAN-DOWN`), ни попытка из бюджета, ни пауза, ни время удержания не
тратятся (бюджет списывается только при реальной отправке переключения). Файлы формальной модели (`pair.lua`,
`pair_auto.py`, `transaction.lua`, `native_switch.py`, `forward_resume`) **не менялись**. В Lua-супервизоре добавлен ключ
`wan_diagnosis` в белый список чтения `status.json` (`auto_control.lua STATUS_KEYS`).

Почему не в `resolve_pair` (как `UPLINK-LINK-DOWN`): тогда Auto показывал бы BLOCKED и отказывал ручным переключениям;
диагноз — повод не менять канал автоматически, а не запрет владельцу.

## 2. События ядра WireGuard (пункт 2)

GL: пропатченное ядро шлёт hotplug класса `wireguard` (`ACTION=KEYPAIR-CREATED|REKEY-TIMEOUT|REKEY-GIVEUP`, `ifname`);
`ifup.sh`/`ifdown.sh` GL ставят `connected`/`connecting` и по REKEY пересобирают туннель (это и есть «минутные
перестройки wgclient1» из soak 31.10). У нас был только опрос.

Наш слушатель `/etc/hotplug.d/wireguard/60-homensai` (hotplug-call выполняет каждый файл каталога в своём подшелле через
`.`, файлы GL работают как раньше): только если монитор создал `/var/run/homensai-vpn/wg-events.on` (опция `wg_events`),
дописывает строку `<uptime> <ACTION> <ifname>` в `/var/run/homensai-vpn/wg-events.log` (RAM; проверка ACTION и имени,
`read` из `/proc/uptime` без форка; при > 8 КБ остаются последние 60 строк). Если во флаге написано `ubus` — ещё
`ubus send homensai.wg {...}` (по умолчанию нет). Монитор раз в секунду делает один `lstat` файла и читает его только при
изменении (`wg_events.Reader`: первая чтение после старта только запоминает позицию — перезапуск ничего не повторяет; более
старый uptime = новая загрузка).

* REKEY-TIMEOUT / REKEY-GIVEUP устройства основного или резерва → `Booster.suspect(reason 'wg-rekey', evidence event)` —
  плотные проверки. **Никогда не доказательство**: одно событие бывает от одного потерянного пакета рукопожатия, а без
  трафика WireGuard молчит.
* KEYPAIR-CREATED — свидетельство `created` для модели (туннель ответил на рукопожатие → TUNNEL маловероятен, SERVER
  вероятнее) и снимает более старый REKEY.

## 3. «Тихий» туннель и вето (пункт 3)

GL/cake-autorate: «stall» только если нет ответов отражателей **и** скорость < 10 кбит/с; при трафике выше порога тревога
снимается (`cake-autorate.sh:1794-1810`). У нас (`stall.py` / `lua/stall.lua`, вызывает `fast_detect.lua` раз в секунду):

* два чтения sysfs на канал в секунду (`statistics/rx_bytes`, `statistics/tx_bytes`), без форков; из tx вычитаются байты
  своих эхо пульса (52 байта каждое), иначе собственный пульс выглядел бы как «трафик в тишину»;
* `stall`: rx не менялся ≥ 3 с, а tx с последнего движения rx вырос ≥ 300 байт → подозрение `rx-stall` (то же
  разоружение, что у пульса: одно на сбой);
* `flowing`: rx сдвинулся за последнюю секунду **и** вырос ≥ 3750 байт за последние 3 с (10 кбит/с) → **вето**
  (условие «за последнюю секунду» снимает вето в ту же секунду, когда rx остановился: настоящий обрыв нагруженного
  туннеля не задерживается): эхо пульса без ответа в этот удар не
  считается потерей (`vetoed`, серия потерь обнуляется). Отказ отправки (EPERM от firewall) и пропавшее устройство вето не
  отменяет. Аутентифицированные данные от пира прямо сейчас = туннель жив, а молчит фильтруемая цель ICMP.
* сброс при паузе > 5 с, уменьшении счётчика (новое устройство), паузе теста скорости.

Python-монитор пульса не имеет (как и раньше): там `suspicion.py` со своим правилом «tx растёт, rx стоит», и при
`stall_sensor` порог берётся 3 с из `stall.py` вместо 6 с (опрос раз в 2 с → срабатывание на 4-й секунде).

С включённым пульсом в Lua на настоящем мёртвом туннеле пульс (2 удара) почти всегда срабатывает раньше; датчик полезен,
когда эхо невозможно (нет raw-сокета → удары `unavailable`, не потери) и как независимое подтверждение. Главная польза
пункта — вето ложных тревог от фильтрации ICMP.

## 4. Пульс k-из-n с ротацией (пункт 4)

`quorum.py` / `lua/quorum.lua`, опция `heartbeat_quorum '1'`: пул 1.1.1.1, 8.8.8.8, 9.9.9.9, 208.67.222.222, 1.0.0.1,
8.8.4.4, 149.112.112.112, 208.67.220.220; на канал 3 активные цели со случайного места пула; каждый удар — эхо каждой из
трёх; удар потерян, если ≥ 2 из 3 без ответа (волна-3, исследование 2); цель, которая 3 раза за 60 с не ответила, пока
удар в целом был отвечен (туннель жив, отражатель нет), заменяется следующей из пула; потерянный удар не ротирует. Правило
подозрения прежнее (2 потерянных удара подряд).

Симулятор `router/tests/quorum_sim.py` (не роутер; 3 суток на сценарий, 400 обрывов; тест `QuorumStudy` проверяет
направление каждой разницы на 1 сутки):

| метрика | сейчас (1 цель, по очереди) | кворум 2 из 3 |
|---|---|---|
| эхо на удар (CPU, трафик) | 1 | **3** |
| ложных подозрений/сутки, потери 0,2 % | 0,33 | 0 |
| то же, 1 % | 6,3 | 0 |
| то же, 5 % | 210 | 6,3 |
| одна цель фильтруется полностью | 92 | 0 (уходит из пула) |
| одна цель теряет 30 % | 38 | 0 |
| полный обрыв: задержка | 2,0 с | 2,0 с |
| потеря 30 % в туннеле: средняя задержка / найдено за 10 с | 14,5 с / 51 % | **26,9 с / 26 %** |
| потеря 50 % | 6,0 с / 86 % | 5,5 с / 89 % |
| потеря 80 % | 2,7 с / 99,8 % | 2,4 с / 100 % |

Вывод: кворум резко снижает ложные плотные эпизоды, но **хуже** находит частичную потерю ~30 % и втрое дороже по эхо.
Не «строго лучше по каждой метрике» → поставляется выключенным; ложное подозрение и так стоит только плотных проверок
(не переключения), а случай фильтруемой цели закрывает вето (пункт 3). Включить: `uci set homensai_vpn.main.heartbeat_quorum='1'`.

## 5. Системные хуки (пункт 5)

### keep.d для sysupgrade

`/lib/upgrade/keep.d/homensai-vpn` (как `gl-sdk4-*` у GL) — ровно эти файлы `/etc/homensai-vpn/`: `checkpoint.json`,
`checkpoint.backup.json`, `native-history.json`, `native-history.backup.json`, `speed-history.json`,
`speed-history.backup.json`, `speed-quota.json`, `latency-history.json`, `ping-response-history.json`,
`website-response-history.json`, `response-compare.json`, `fault-history.json`, `switch-timing.json`,
`telegram-state.json`, `telegram-state.backup.json`, каталог `stats-archive/` (история, статистика, учёт отправок
Telegram без токена).

**Не сохраняем**: `/etc/config/homensai_vpn` (в нём токен Telegram; его уже сохраняет штатное правило sysupgrade для
изменённых conffiles пакета — мы не добавляем секретов сверх того, что GL сохраняет и так), `auto-resume.json`
(после перепрошивки и переустановки Auto не должен включиться сам), журналы и записи восстановления старой прошивки
(`native-transaction*`, `preparation-changes`, `session-recovery`, `native-stop.json`, `pair-auto-*`,
`native-certificate.json`, `pristine/`, `service-run.json`, `stock-derived-recovery.json`). Пакет после sysupgrade сам не
возвращается (его нет в прошивке): файлы ждут переустановки.

### Плановая перезагрузка ≠ отключение питания

GL превращает `gl_timer.reboot` (enable, hour, min, week) в строку cron `$min $hour * * $week reboot`
(`init.d/gl_timer:75-87`). Перезагрузка выполняет `K*`-скрипты с аргументом `shutdown`: наш `shutdown()` в
`/etc/init.d/homensai-vpn` ставит `HOMENSAI_SHUTDOWN=1` и вызывает `stop`; `stop_service` спрашивает
`lua boot_cause.lua shutdown-reason` (TZ из `/etc/TZ`; совпадение расписания с местным временем 0..3 мин после → 
`planned-reboot`, иначе `reboot`) и пишет в `service-run.json` `{"state":"stopped","time":…,"reason":…}`. При следующем
запуске `interruption.classify` даёт **RESTART-PLANNED-REBOOT** (свежая загрузка, `stopped`, причина planned-reboot);
обычная перезагрузка и остановка службы — как раньше `RESTART-CLEAN`.

### Сбой ядра ≠ отключение питания

GL: `gl_logread` (START=01) грузит mtdoops (записи паники прямо в MTD-раздел `log`), `gl_crash_log` (START=99) при
загрузке сливает `/sys/fs/pstore/dmesg-ramoops-*` в раздел, **удаляет pstore** и пишет `/tmp/log/crash_log` = `strings`
всего раздела (вместе со старыми записями). Наш сервис тоже START=99, но procd запускает S-скрипты по одному в порядке
имён: `S99gl_crash_log` завершается раньше `S99homensai-vpn`. `boot_cause.evaluate` (вызывается из
`interruption.start` только при первом запуске супервизора в этой загрузке):

1. в pstore ещё есть `dmesg-ramoops-N` (GL-скрипта нет или он позже) → сбой;
2. иначе «отпечаток» `crash_log` (длина + 32-битный хеш h=h·31+байт mod 2³², одинаковый в Lua/Python) отличается от
   запомненного в `/etc/homensai-vpn/boot-cause.json` при прошлой загрузке → сбой (новая запись слита или записана
   mtdoops);
3. запомненного нет (первая загрузка после установки) → неизвестно; пустой лог после обновления прошивки (раздел
   стирается) → не сбой.

Отпечаток записывается только при изменении (одна маленькая запись на загрузку) и обновляется ещё раз через 120 с
аптайма (`boot_cause.refresh` в секундном таймере монитора): слияние, случившееся после нашего старта, не будет принято за
сбой следующей загрузки. Код **RESTART-KERNEL-CRASH** стоит перед кодами `RESTART-INTERRUPTED-*` (этап журнала остаётся
в строке журнала); восстановление ведёт себя как после любого прерывания — меняется только диагноз.

### Диагностический пакет с маскированием

`/usr/sbin/homensai-vpn-diag` (Lua `diag_bundle.lua collect`, без Lua — `diag_bundle.py`): только чтение — `ip -4
rule/route table all/addr`, `nft list ruleset`, `iptables-save -t mangle`, `wg show all`, `tc -s qdisc show`,
`uci show route_policy|network|homensai_vpn|gl_timer|kmwan`, `/proc/gl-kmwan/config`, `ubus call repeater status`,
`logread -e homensai|wireguard`, `dmesg`, `/tmp/log/crash_log`, наши `status.json`, `native-status.json`,
`wg-events.log`, `service-run.json`, `boot-resume.json`, версии. Каждая строка маскируется (`diag_bundle.mask_line`,
общие случаи): значения опций/ключей JSON с частями имени private, preshared, password, passwd, passphrase, secret,
token, psk, key, auth, telegram_chat, endpoint, exit_ip, ssid, bssid → `***`; строки `wg show` private/preshared/public
key, peer, endpoint → `***`; любой 44-символьный base64-ключ → `<key>`; токен бота Telegram → `<token>`; MAC → первые три
октета + `xx:xx:xx`. Результат `/tmp/homensai-vpn-diag.tar.gz`, права 0600. Выдача — белый список GL
`/usr/share/gl-download.d/homensai-vpn` с единственной строкой `/tmp/homensai-vpn-diag.tar.gz$` (как `logread` у GL:
скачать может только вошедший в страницу GL; механизм `oui-download` в копии нет — проверить на роутере). Никакой
отправки, никакой загрузки в облако, ничего на роутере не меняется.

## 6. Настройки (`config main 'main'`, читает `inventory.lua`)

| опция | значения | по умолчанию | действие |
|---|---|---|---|
| `wan_sensor` | `'0'` выкл., иначе вкл. | вкл. | эхо через WAN, диагноз, WAN-DOWN/WAN-RECOVERING, hasten; `'0'` — прежнее поведение (диагноз всё равно публикуется с `enabled:false`, но без эха, удержания и ускорения) |
| `wan_recover_grace` | 0..120 с | 30 | WAN-RECOVERING: ожидание одной здоровой пробы основного после возврата WAN |
| `wg_events` | `'0'` выкл. | вкл. | флаг для hotplug-слушателя и чтение событий |
| `stall_sensor` | `'0'` выкл. | вкл. | датчик «tx растёт, rx стоит» (Lua-пульс; в Python — порог 3 с вместо 6 с) |
| `stall_veto` | `'0'` выкл. | вкл. (нужен `stall_sensor`) | вето потерь пульса при rx ≥ 10 кбит/с |
| `heartbeat_quorum` | `'1'` вкл. | **выкл.** | пульс 2 из 3 с ротацией |

Без UI: опции задаются через `uci set homensai_vpn.main.<опция>=…; uci commit homensai_vpn` (монитор перечитывает
настройки каждый проход). Страница получает новые поля статуса: `status.wan_diagnosis` (verdict, confidence,
code, hold, recovering, hasten, posterior, evidence, underlay), `status.fast_detect.{stall,veto,quorum}` и по каналу
`vetoed`, `flowing`, `stalled`, `quorum_targets`, `rotations`. Коды — в таблице ошибок (`router/error_rows_extra.inc.js`:
WAN-DOWN, WAN-RECOVERING, DIAG-*; `router/error_table.inc.js`: RESTART-PLANNED-REBOOT, RESTART-KERNEL-CRASH;
`docs/ERROR_CODES.md` пересобран). Цвет важности кодов в журнале (UI) не менялся — для UI-порта: RESTART-PLANNED-REBOOT
лучше «low», остальные новые — «medium» по умолчанию уже.

## 7. Цена CPU (оценка)

Замер в docker на ПК (хост нагружен другими контейнерами; `router/tests/lua/bench_fast_detect.lua 20000 lo lo
[опции]`, `router/tests/lua/bench_gl_sensors.lua`; поддельный сокет отвечает на каждое эхо). Для A53 MT3000 ориентир
×5–10 к числам ПК (по прежним замерам пульса); на роутере проверить тем же бенчем (раздел 9).

| что | ПК, на 2 канала | оценка MT3000 |
|---|---|---|
| пульс как раньше (без опций) | 271 мкс/с = 0,027 % ядра | 1,4–2,7 мс/с ≈ 0,14–0,27 % |
| + stall и вето (по умолчанию) | 474 мкс/с (+0,02 %) | +1–2 мс/с ≈ +0,1–0,2 % |
| + кворум 2 из 3 (выкл.) | 729 мкс/с (+0,046 %); со stall 842 | +2,3–4,6 мс/с; эхо 6 пакетов/с вместо 2 (+≈2,5 кбит/с) |
| `wan_diag.diagnose` | 30–42 мкс на проход | ≈ 0,2–0,4 мс на проход |
| `stall.feed` | 8 мкс на канал и удар | входит в строку stall |
| эхо через WAN | 1 пакет / 10 с (1 / 2 с при подозрении) | < 0,01 % |
| события WG | один `lstat` в секунду; хук — только на событие (`wc` при существующем файле) | пренебрежимо |
| отпечаток crash_log 256 КБ | 31 мс один раз за загрузку (после ускорения кусками по 256 байт; было 76 мс) | 0,15–0,3 с один раз за загрузку |
| `diag_bundle.mask` 0,5 МБ | 128 мс | ≈ 1 с на пакет, только по команде |

Форки: `ubus call repeater status` — один на проход и только пока основной не проходит проверку; Python-эхо WAN
блокирует цикл ожидания монитора не дольше 1 с раз в 10 с (2 с при подозрении).

## 8. Риски

* Эхо через WAN может не пройти из-за правил GL (утечка/killswitch) — тогда датчик никогда не калибруется и молчит
  («неизвестно» = прежнее поведение). Ложное «fail» после калибровки требует 3 неудач подряд на 2 целях и одновременно
  «плохие» оба канала — тогда переключение и так не помогло бы (резерв не проходит проверки).
* WAN-RECOVERING задерживает уход с основного, который не поднялся после возврата WAN, максимум на `wan_recover_grace`
  (30 с) — в обмен на отсутствие лишнего переключения при гонке туннелей после возврата WAN.
* Формат `/proc/gl-kmwan/config` не известен (`[?]`): учитываются только слова online/offline.
* Хук WireGuard — сторонний файл в каталоге GL; он ничего не меняет и выходит сразу без флага. Если GL сменит имена
  событий, датчик просто молчит.
* Вето под нагрузкой гасит и ранние подозрения пульса при частичной потере (туннель жив, но теряет часть пакетов):
  такие сбои по-прежнему находят полные проверки и модель HMM, теряется только раннее «уплотнение» проб. Выключить:
  `stall_veto '0'`.
* При обрыве WAN прошивка часто пересобирает туннели (REKEY), и Auto может показывать BLOCKED с блокерами
  VENDOR-SETTLING/OBSERVATION-STALE раньше, чем дойдёт до диагноза; тогда WAN-DOWN виден в `status.wan_diagnosis`, а
  переключения нет по другой причине.
* `shutdown()` в init-скрипте переопределяет функцию rc.common по умолчанию (которая только вызывает `stop`) — та же
  остановка плюс запись причины.
* Отпечаток crash_log считает сбоем любую смену содержимого раздела `log`, кроме стирания (например, ручную запись в
  раздел) — редкий и безопасный ложный «сбой ядра» только в коде запуска.

## 9. Проверка на роутере (только MT3000, только чтение, по правилам `CLAUDE.md`)

Перед работой: `private/ACTIVE-EXECUTOR.local.json`, согласие владельца; один исполнитель. Основной MT6000 и сеть
Windows владельца не трогать: тесты WAN — только на uplink самого MT3000 (Wi-Fi-повторитель `apcli0` на стенде),
никогда не выключать порт/сеть, от которой зависит основной MT6000.

Только чтение:

```sh
ls /proc/gl-kmwan && cat /proc/gl-kmwan/config            # формат вердикта kmwan
ubus call repeater status | jsonfilter -e '@.portal'      # флаг captive portal
ls /etc/hotplug.d/wireguard; logread | grep -i -E 'rekey|keypair' | tail -20
cat /var/run/homensai-vpn/wg-events.on /var/run/homensai-vpn/wg-events.log 2>/dev/null | tail
jsonfilter -i /var/run/homensai-vpn/status.json -e '@.wan_diagnosis' -e '@.fast_detect.stall' -e '@.fast_detect.veto'
cat /sys/class/net/wgclient1/statistics/rx_bytes /sys/class/net/wgclient1/statistics/tx_bytes
sysupgrade -l | grep -E 'homensai|vpn'                     # что сохранится (keep.d + conffiles)
cat /usr/share/gl-download.d/homensai-vpn; ls /usr/share/gl-download.d
uci -q show gl_timer.reboot; cat /proc/mtd | grep -i log; ls /sys/fs/pstore; head -c 300 /tmp/log/crash_log
cat /etc/homensai-vpn/service-run.json /etc/homensai-vpn/boot-cause.json
lua /usr/lib/homensai-vpn/lua/boot_cause.lua shutdown-reason     # печатает reboot / planned-reboot, ничего не пишет
lua /tmp/bench_gl_sensors.lua    # копия router/tests/lua/bench_gl_sensors.lua в RAM; модули берёт из /usr/lib/homensai-vpn/lua
top -bn1 | head -15
```

Испытания (отдельное разрешение владельца на каждое, по одному):

1. **WAN-обрыв MT3000** (не MT6000): отключить uplink MT3000 (например, выключить точку, к которой подключён его
   `apcli0`, или вынуть кабель WAN MT3000) на 60 с и 300 с при работающем Auto на основном. Ждём: `WAN-DOWN` в
   `status.wan_diagnosis`, причина Auto `WAN-DOWN`, **0 переключений**, после возврата — `WAN-RECOVERING`, внеочередной
   проход, без переключения на резерв, если основной поднялся за 30 с. Сравнить с `wan_sensor '0'` (ожидаемо лишнее
   переключение после возврата при «гонке»).
2. **Обрыв туннеля при живом WAN** (как в прежних soak: nft-blackhole основного): ждём `hasten`/`wan-ok-tunnel-down`
   или `heartbeat-lost`, решение Auto не медленнее прежних 26–28 с.
3. **Фильтрация цели пульса** (nft drop ICMP к 8.8.8.8 только через туннель) при загрузке LAN: ждём `vetoed` > 0 и нет
   плотных эпизодов по пульсу; с `heartbeat_quorum '1'` — ротация цели.
4. **REKEY-события**: `logread` при пересборках wgclient1 прошивкой → строки в `wg-events.log`, подозрение `wg-rekey`.
5. **Плановая перезагрузка**: включить `gl_timer.reboot` на ближайшую минуту (временная настройка владельца) → после
   загрузки код RESTART-PLANNED-REBOOT; вернуть таймер.
6. **Soak 24 ч** с настройками по умолчанию: число ложных `wg-rekey`/`rx-stall`/`wan-ok-tunnel-down` эпизодов в сутки,
   CPU монитора по `top` против alpha8; отдельный 24 ч с `heartbeat_quorum '1'` для сравнения ложных эпизодов.
7. `homensai-vpn-diag` → скачать архив со страницы GL по белому списку (проверить механизм `gl-download.d`), убедиться,
   что в нём нет ключей/паролей/токенов; удалить `/tmp/homensai-vpn-diag.tar.gz`.

Пункты «сбой ядра» и «sysupgrade с сохранением» на стенде не провоцировать без отдельного решения владельца (паника ядра
через sysrq — только с его разрешением; sysupgrade — отдельная процедура).

## 10. Файлы

Новые: `router/files/usr/lib/homensai-vpn/{wan_diag,stall,quorum,wg_events,boot_cause,diag_bundle,gl_sensors}.py`,
`router/files/usr/lib/homensai-vpn/lua/{wan_diag,stall,quorum,wg_events,boot_cause,diag_bundle,gl_sensors}.lua`,
`router/files/etc/hotplug.d/wireguard/60-homensai`, `router/files/lib/upgrade/keep.d/homensai-vpn`,
`router/files/usr/share/gl-download.d/homensai-vpn`, `router/files/usr/sbin/homensai-vpn-diag`; тесты
`router/tests/{test_gl_sensors,gen_gl_sensors_cases,quorum_sim,mutate_gl_sensors}.py`, `router/tests/gl_sensors_cases.json`,
`router/tests/lua/{test_gl_sensors,bench_gl_sensors}.lua`.
Изменены: `lua/fast_detect.lua` (stall/veto/quorum через опции), `lua/monitor.lua` (проход: `wan_diagnosis`, hasten,
внеочередной проход после возврата WAN; секундный таймер `gl_tick`), `lua/monitor_io.lua` (команда
`repeater_status`), `agent.py` (то же для Python), `suspicion.py` (порог stall из настройки), `failure_diagnosis.py` /
`lua/diagnosis.lua` (WAN-DOWN/WAN-RECOVERING), `lua/auto_control.lua` (ключ статуса), `probe_policy.py` /
`lua/probe_policy.lua` (причины `wg-rekey`, `wan-ok-tunnel-down`), `interruption.py` / `lua/interruption.lua` (коды
запуска), `inventory.lua` (опции), `etc/init.d/homensai-vpn` (`shutdown()` и причина), `build_ipk.py` / `Makefile`
(исполняемый `homensai-vpn-diag`), таблицы кодов и `docs/ERROR_CODES.md`.
