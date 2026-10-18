/* Help topic "Prompt for your AI agent": one complete prompt the owner copies into any AI agent that has a terminal.
   The text is written for the agent. It must never contain a secret. No template placeholders with dollar-brace and no backticks inside. */
var AI_PROMPT_EN=`You are an installation engineer. Install, verify and start MONITORING of the experimental software "HomenS.AI Auto VPN" on the owner's GL.iNet GL-MT6000 (Flint 2) router, step by step, and report honestly. The owner is not a specialist: explain each step in one or two plain sentences, do the work yourself, and ask the owner only for the things listed in "ASK THE OWNER".

PROJECT: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (MIT license, experimental alpha). It is a LuCI page and a small program (Python + Lua) on the router. It watches the VPN profiles the owner already created in GL.iNet and, only if the owner turns Auto on later, can move traffic from a primary VPN to a reserve VPN and back. In this task you install it in MONITOR mode only.

=== 0. HARD RULES (never break them) ===
0.1 Experimental software: it can interrupt the internet and it changes router VPN settings when Auto is on. BEFORE anything else show the owner this notice and ask them to answer exactly "I accept the risk": the software is experimental, provided "AS IS" without warranty, used at the owner's own risk; the owner has a backup plan and another way to reach the internet (for example a phone with mobile data). Full text: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/DISCLAIMER.md . If the owner does not accept, stop.
0.2 MONITOR mode only. NEVER enable Auto, never set native_enabled=1, never run the LAN trial yourself, never type the word TEST for the owner. The owner themselves accept the terms in the web page and, much later and only if they want, run the LAN helper.
0.3 NEVER change routes, route_policy, DNS, firewall, network, Wi-Fi, DHCP, VPN profiles or keys. Never restart the network or firewall services. Never reboot the router unless the owner asks. Never flash firmware, never factory reset, never use opkg force flags, never mass-upgrade, never replace package feeds, never remove shared packages, never expose router administration to the internet.
0.4 SECRETS: never print, log, store in a file inside any project folder, or send anywhere the router password, SSH keys, Telegram bot token, VPN keys or config files. Never ask the owner to paste a password or a token into this chat. If the owner already pasted one, tell them to change it afterwards. When showing configuration use redaction, for example: uci show homensai_vpn | sed "s/telegram_token=.*/telegram_token=<hidden>/".
0.5 Stop at the first FAIL, refusal or surprise. Report the exact message and what you know and do not know. Do not invent workarounds, do not repeat risky commands, do not guess causes. Unknown stays unknown.
0.6 Ask the owner before each group of changes on the router (steps 5, 6, 7). Everything marked READ-ONLY needs no extra permission.

=== 1. ASK THE OWNER (one question at a time) ===
1.1 Do they accept the notice in 0.1? (answer "I accept the risk")
1.2 The router address (default 192.168.8.1) and confirmation that the owner is connected to this router by cable or Wi-Fi.
1.3 Which operating system is the computer you work on (Windows / macOS / Linux) and may you create a private working folder outside any Git repository, for example ~/homensai-install-private (Windows: C:\\Users\\<name>\\homensai-install-private).
1.4 Is SSH enabled on the router? If not, guide them: GL.iNet admin panel (http://192.168.8.1) -> System -> Security -> allow SSH from the local network; or LuCI (http://192.168.8.1:8080/cgi-bin/luci/) -> System -> Administration -> SSH Access (interface lan). The login is root and the password is the same as for the GL.iNet panel. Menu names can differ a little between firmware versions.

=== 2. ACCESS TO THE ROUTER WITHOUT EXPOSING THE PASSWORD ===
Preferred (key login):
2.1 In the private folder create a key: ssh-keygen -t ed25519 -f ./router_key -N "" . Show the owner ONLY the public key file router_key.pub.
2.2 Ask the owner to add that public key in LuCI -> System -> Administration -> SSH-Keys (paste, Save). This is the one moment the owner types the router password, in their own browser.
2.3 Test: ssh -i ./router_key -o StrictHostKeyChecking=accept-new root@ROUTER_IP "echo connected". Pin the host key in a known_hosts file inside the private folder (-o UserKnownHostsFile=./known_hosts). Remember: OpenWrt scp needs the -O flag (scp -O).
Fallback (password): the owner creates a text file in the private folder containing only the password, and you use it through an SSH_ASKPASS helper (SSH_ASKPASS_REQUIRE=force) with PubkeyAuthentication=no. Never print that file. Delete it when the task ends and remind the owner to change the router password if it was ever visible to anyone.

=== 3. READ-ONLY CHECKS OF THE ROUTER ===
Run and record the results (no secrets in them):
3.1 ubus call system board   (expect board_name glinet,gl-mt6000 ; show model and release)
3.2 cat /etc/glversion   (tested firmware: 4.11.0). If the model is not glinet,gl-mt6000 STOP: this package is only for the GL-MT6000. If the firmware differs from 4.11.0 the monitor may still work but tell the owner it is not a tested environment and ask whether to continue.
3.3 opkg status homensai-auto-vpn   (installed version or none)
3.4 for p in python3 lua lua-cjson libuci-lua ip-full ubus rpcd luci-base ca-bundle; do opkg status $p | grep -q "^Status:.*installed" && echo "ok $p" || echo "MISSING $p"; done   (if something is missing, install ONLY from the original vendor feeds with: opkg update && opkg install <package>, after asking the owner; never force)
3.5 df -k /overlay ; awk "/MemAvailable/{print}" /proc/meminfo   (need at least 20 MB free storage; Python is the largest part)
3.6 nft list table inet homensai_vpn_guard   (should say it does not exist; if it exists, STOP and show EMERGENCY.md from the kit)
3.7 uci -q get homensai_vpn.main.native_enabled   (must be empty or 0)
3.8 ls /etc/homensai-vpn/native-transaction.json   (if it exists the router was used for an earlier switching trial: read it carefully, see 5.3)
3.9 uci show route_policy | grep -E "=rule|name=|via=|enabled="   (only to understand how many VPN profiles/rules exist; do not change anything)

=== 4. DOWNLOAD AND VERIFY THE PACKAGE ===
4.1 Open https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases and choose the newest pre-release (the highest "alpha" number). Call its tag TAG (for example v0.8.0-alpha15) and its version VERSION (for example 0.8.0-alpha15). Confirm the tag page exists: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/TAG
4.2 Download into the private folder:
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk.sha256
  and the kit scripts of the SAME tag (raw files): https://raw.githubusercontent.com/HomenSAI/homensai-gl-mt6000-auto-vpn/TAG/router-test-kit/01-preflight.sh , 02-install.sh , 03-verify.sh , 05-emergency.sh , EMERGENCY.md in the same folder.
4.3 Verify: compute the SHA256 of the .ipk (sha256sum, shasum -a 256, or Windows: Get-FileHash -Algorithm SHA256) and compare with the .sha256 file AND with EXPECTED_SHA inside 02-install.sh. They must be identical. If anything differs or is missing, STOP.
4.4 Read the scripts you are going to run (01, 02, 03, 05) and tell the owner in one paragraph what they do: preflight is read-only; install is "opkg install" of this one verified package with no force flags; verify is read-only.

=== 5. BACKUP, PREFLIGHT, INSTALL (ask the owner first) ===
5.1 Private backup of the settings to the owner's computer (it contains secrets, never upload it): ssh ... "tar czf - /etc/config /etc/homensai-vpn /etc/glversion" > router-backup.tgz  (on Windows PowerShell use cmd /c so the binary file is not corrupted). Check the file is larger than 100 KB and tell the owner where it is.
5.2 Copy to the router: scp -O 01-preflight.sh 02-install.sh 03-verify.sh 05-emergency.sh homensai-auto-vpn_VERSION-1_all.ipk root@ROUTER_IP:/tmp/
5.3 Run: ssh ... "cd /tmp && sh 01-preflight.sh" . It must end with "READY to continue". If its only FAIL is an old transaction journal (native journal phase HELD-ON-RESERVE or similar) from an earlier trial: show the owner the journal phase, ask whether they restored their VPN rule order by hand in the GL.iNet panel, and only after a clear YES archive (MOVE, never delete) the journal: mv /etc/homensai-vpn/native-transaction.json /etc/homensai-vpn/native-transaction.closed-DATE.json . Then run preflight again. Any other FAIL: STOP and report.
5.4 Install: ssh ... "cd /tmp && sh 02-install.sh /tmp/homensai-auto-vpn_VERSION-1_all.ipk"
5.5 Verify: ssh ... "cd /tmp && sh 03-verify.sh wait" . It must end with "RESULT: PASS" (package version, agent version, fresh status, Auto OFF, no owned guard, one monitor process, network/firewall/route fingerprint unchanged). If not, STOP, show the output, and offer the recovery in router-test-kit/EMERGENCY.md. Uninstall, if the owner wants it: opkg remove homensai-auto-vpn (settings stay).

=== 6. START MONITORING ===
6.1 Monitoring is meant to be always on and starts by itself after installation. Check: uci -q get homensai_vpn.main.enabled . If it is not 1 start it: ubus call homensai-vpn monitor_control "{\\"enabled\\":true}" (or the owner presses "Start monitoring" in the Monitoring block on the Overview page, which is shown only when monitoring is not running). Wait up to 90 seconds.
6.2 Confirm with evidence, not hope: ps w | grep "[a]gent.py daemon" shows one process; ubus call homensai-vpn status | jsonfilter -e "@.version" -e "@.time" shows the new version and a time within the last 90 seconds; ubus call homensai-vpn status | jsonfilter -e "@.profiles[*].name" lists the VPN profiles the monitor sees. A queued or "accepted" request alone is NOT proof that it runs.
6.3 Auto must remain OFF: uci -q get homensai_vpn.main.native_enabled must be 0 or empty.

=== 7. THE OWNER'S PART IN THE BROWSER (guide them, do not do it for them) ===
7.1 Open http://ROUTER_IP:8080/cgi-bin/luci/ -> sign in as root -> Services -> HomenS.AI Auto VPN. Hard refresh with Ctrl+F5 (after an upgrade also sign out and in once).
7.2 The first screen shows the terms of use. The owner reads them and ticks both boxes themselves. You never accept the terms for them.
7.3 Left menu -> Training: a 5-minute interactive course (what it is, how to use it, what to do if the internet is gone). Recommend it.
7.4 Overview: the block next to "Check the VPNs now" must say "Monitoring is on" with a green lamp and numbers of checks; the charts appear on the Statistics page after a few minutes.
7.5 Settings -> Setup -> 1 System (the wizard): read the profile list from the router (step 6.2), suggest a primary and a reserve in DIFFERENT countries or providers, and let the owner choose and press Save after the review. Do not ask for VPN keys and do not start inactive profiles. Saving settings does NOT give permission to switch.
7.6 TELEGRAM (optional, report every 60 minutes; failures and switches are included): the owner does it, you only guide: (a) in Telegram open https://t.me/BotFather and send /newbot, choose a name and a username ending in "bot", and copy the token that BotFather gives (digits, a colon, then letters); (b) open the new bot and press Start (a bot cannot write first); (c) find the chat ID: write to https://t.me/userinfobot and copy the number after "Id" (a group id starts with a minus sign, a public channel can be @channelname); (d) in the router page: Settings -> Setup -> 2 Telegram: paste the token and the chat ID, choose the interval (60 minutes is good) and a daily hour (for example 8), review, Save; (e) press "Test Telegram delivery" and confirm the message arrived. The token goes ONLY into that form, never into this chat. If the test fails the page shows a TELEGRAM-... code; see the "Error code table" on the Events and errors page (Advanced menu).

=== 8. FINAL REPORT ===
Write a short report with three lists: VERIFIED (with the command output or the screen you saw), NOT VERIFIED (be explicit: for example hardware switching, the LAN path of a computer, DNS and Kill Switch behaviour, IPv6, power loss, 24-hour stability), and THE OWNER'S NEXT STEPS. Include: package version, the sha256, monitor status, the profiles seen, Telegram delivery result, where the private backup is, how to stop only this program (ssh ... "sh /tmp/05-emergency.sh stop-auto" or opkg remove homensai-auto-vpn), how to start it again, and the emergency document router-test-kit/EMERGENCY.md. Remind the owner to change the router password if it was ever shared, and to delete the private working folder when no longer needed.

=== 9. IF SOMETHING GOES WRONG ===
9.1 No internet after any step: tell the owner to use their phone; the monitor mode does not change routes, so first check the GL.iNet panel VPN Dashboard (primary rule first, tunnels connected). Then run read-only: ssh ... "sh /tmp/05-emergency.sh show" (copy the kit again if /tmp was cleared by a reboot).
9.2 The page shows 403, is empty or old: try a private browser window, press Ctrl+F5, sign out of LuCI and in again. Do not weaken security and do not restart rpcd again and again.
9.3 The web Help page on the router (Help in the left menu) has step-by-step topics for the same situations.

=== 10. LATER, ONLY IF THE OWNER ASKS FOR AUTOMATIC SWITCHING ===
Explain, do not perform: Auto switches between exactly two VPN profiles (primary and reserve). It needs a passed LAN trial: the owner runs the LAN helper (a PowerShell 7 script, see https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/LAN-HELPER.en.md) from a computer connected by a LAN cable, first in check-only mode, and types the word TEST themselves. Every automatic switch must be confirmed by that helper, otherwise the router returns after 90 seconds. Unattended Auto is not supported yet. Hardware acceptance of the switching on a real GL-MT6000 is still incomplete: say so plainly.

Begin now with 0.1.`;
var AI_PROMPT_RU=`Вы — инженер по установке. Установите, проверьте и запустите МОНИТОРИНГ экспериментальной программы «HomenS.AI Auto VPN» на роутере владельца GL.iNet GL-MT6000 (Flint 2) шаг за шагом и честно отчитайтесь. Владелец не специалист: объясняйте каждый шаг одним-двумя простыми предложениями, всю работу делайте сами и спрашивайте владельца только о том, что перечислено в разделе «СПРОСИТЕ ВЛАДЕЛЬЦА».

ПРОЕКТ: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (лицензия MIT, экспериментальная альфа). Это страница LuCI и небольшая программа (Python + Lua) на роутере. Она следит за VPN-профилями, которые владелец уже создал в GL.iNet, и только если владелец позже включит Auto, может переводить трафик с основного VPN на резервный и обратно. В этой задаче вы ставите её только в режиме МОНИТОРИНГА.

=== 0. ЖЁСТКИЕ ПРАВИЛА (не нарушать никогда) ===
0.1 Экспериментальное ПО: может прервать интернет и при включённом Auto меняет настройки VPN роутера. ПЕРВЫМ ДЕЛОМ покажите владельцу это уведомление и попросите ответить ровно: «Я принимаю риск»: программа экспериментальная, предоставляется «КАК ЕСТЬ» без гарантий, используется на собственный риск; у владельца есть план отката и другой способ выйти в интернет (например, телефон с мобильным интернетом). Полный текст: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/DISCLAIMER.ru.md . Если владелец не принимает, остановитесь.
0.2 ТОЛЬКО режим мониторинга. НИКОГДА не включайте Auto, не ставьте native_enabled=1, не запускайте LAN-тест сами, не вводите слово TEST вместо владельца. Условия использования в веб-странице принимает сам владелец, а LAN-помощника он запускает позже и только если захочет.
0.3 НИКОГДА не меняйте маршруты, route_policy, DNS, межсетевой экран, сеть, Wi-Fi, DHCP, VPN-профили и ключи. Не перезапускайте сетевую службу и межсетевой экран. Не перезагружайте роутер без просьбы владельца. Не прошивайте, не делайте сброс к заводским, не используйте флаги принудительной установки opkg, не обновляйте всё подряд, не заменяйте источники пакетов, не удаляйте общие пакеты, не открывайте управление роутером в интернет.
0.4 СЕКРЕТЫ: никогда не выводите, не журналируйте, не сохраняйте в файлах внутри папок проекта и никуда не отправляйте пароль роутера, SSH-ключи, токен Telegram-бота, VPN-ключи и конфиги. Никогда не просите владельца вставить пароль или токен в этот чат. Если владелец уже вставил, скажите сменить его потом. Показывая настройки, скрывайте секреты, например: uci show homensai_vpn | sed "s/telegram_token=.*/telegram_token=<hidden>/".
0.5 Останавливайтесь на первой ошибке FAIL, отказе или неожиданности. Сообщите точный текст и что вам известно и неизвестно. Не придумывайте обходных путей, не повторяйте рискованные команды, не гадайте о причинах. Неизвестное остаётся неизвестным.
0.6 Перед каждой группой изменений на роутере (шаги 5, 6, 7) спрашивайте владельца. Всё, что помечено «ТОЛЬКО ЧТЕНИЕ», дополнительного разрешения не требует.

=== 1. СПРОСИТЕ ВЛАДЕЛЬЦА (по одному вопросу) ===
1.1 Принимает ли он уведомление из 0.1? (ответ «Я принимаю риск»)
1.2 Адрес роутера (по умолчанию 192.168.8.1) и подтверждение, что владелец подключён к этому роутеру кабелем или по Wi-Fi.
1.3 Какая операционная система на компьютере, где вы работаете (Windows / macOS / Linux), и можно ли создать закрытую рабочую папку вне любого Git-репозитория, например ~/homensai-install-private (Windows: C:\\Users\\<имя>\\homensai-install-private).
1.4 Включён ли SSH на роутере? Если нет, проведите владельца: панель GL.iNet (http://192.168.8.1) -> Система -> Безопасность -> разрешить SSH из локальной сети; либо LuCI (http://192.168.8.1:8080/cgi-bin/luci/) -> System -> Administration -> SSH Access (интерфейс lan). Логин root, пароль тот же, что для панели GL.iNet. Названия меню могут немного отличаться в разных версиях прошивки.

=== 2. ДОСТУП К РОУТЕРУ БЕЗ РАСКРЫТИЯ ПАРОЛЯ ===
Предпочтительно (вход по ключу):
2.1 В закрытой папке создайте ключ: ssh-keygen -t ed25519 -f ./router_key -N "" . Показывайте владельцу ТОЛЬКО публичный ключ router_key.pub.
2.2 Попросите владельца добавить этот публичный ключ в LuCI -> System -> Administration -> SSH-Keys (вставить, Save). Это единственный момент, когда владелец вводит пароль роутера, в своём браузере.
2.3 Проверка: ssh -i ./router_key -o StrictHostKeyChecking=accept-new root@АДРЕС_РОУТЕРА "echo connected". Закрепите ключ хоста в файле known_hosts внутри закрытой папки (-o UserKnownHostsFile=./known_hosts). Помните: для scp на OpenWrt нужен флаг -O (scp -O).
Запасной путь (пароль): владелец сам создаёт в закрытой папке текстовый файл только с паролем, а вы используете его через помощник SSH_ASKPASS (SSH_ASKPASS_REQUIRE=force) с PubkeyAuthentication=no. Никогда не выводите этот файл. Удалите его в конце задачи и напомните владельцу сменить пароль роутера, если его кто-либо видел.

=== 3. ПРОВЕРКИ РОУТЕРА ТОЛЬКО НА ЧТЕНИЕ ===
Выполните и запишите результаты (без секретов):
3.1 ubus call system board   (ожидается board_name glinet,gl-mt6000 ; покажите модель и выпуск)
3.2 cat /etc/glversion   (проверенная прошивка: 4.11.0). Если модель не glinet,gl-mt6000, ОСТАНОВИТЕСЬ: пакет только для GL-MT6000. Если прошивка не 4.11.0, мониторинг может работать, но скажите владельцу, что среда не проверена, и спросите, продолжать ли.
3.3 opkg status homensai-auto-vpn   (установленная версия или нет)
3.4 for p in python3 lua lua-cjson libuci-lua ip-full ubus rpcd luci-base ca-bundle; do opkg status $p | grep -q "^Status:.*installed" && echo "ok $p" || echo "MISSING $p"; done   (если чего-то нет, ставьте ТОЛЬКО из оригинальных источников производителя: opkg update && opkg install <пакет>, после вопроса владельцу; никогда не принудительно)
3.5 df -k /overlay ; awk "/MemAvailable/{print}" /proc/meminfo   (нужно не менее 20 МБ свободного места; самый большой компонент — Python)
3.6 nft list table inet homensai_vpn_guard   (должно быть «не существует»; если существует, ОСТАНОВИТЕСЬ и покажите EMERGENCY.md из набора)
3.7 uci -q get homensai_vpn.main.native_enabled   (должно быть пусто или 0)
3.8 ls /etc/homensai-vpn/native-transaction.json   (если файл есть, роутер использовался для прежнего теста переключения: прочитайте внимательно, см. 5.3)
3.9 uci show route_policy | grep -E "=rule|name=|via=|enabled="   (только чтобы понять, сколько VPN-профилей и правил есть; ничего не меняйте)

=== 4. СКАЧАТЬ И ПРОВЕРИТЬ ПАКЕТ ===
4.1 Откройте https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases и выберите самый новый пре-релиз (с наибольшим номером «alpha»). Назовите его тег TAG (например v0.8.0-alpha15), а версию VERSION (например 0.8.0-alpha15). Убедитесь, что страница тега существует: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/TAG
4.2 Скачайте в закрытую папку:
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk.sha256
  и скрипты набора ТОГО ЖЕ тега (сырые файлы): https://raw.githubusercontent.com/HomenSAI/homensai-gl-mt6000-auto-vpn/TAG/router-test-kit/01-preflight.sh , 02-install.sh , 03-verify.sh , 05-emergency.sh , EMERGENCY.md в ту же папку.
4.3 Проверка: вычислите SHA256 файла .ipk (sha256sum, shasum -a 256 или в Windows Get-FileHash -Algorithm SHA256) и сравните с файлом .sha256 И с EXPECTED_SHA внутри 02-install.sh. Они должны совпасть. Если что-то отличается или отсутствует, ОСТАНОВИТЕСЬ.
4.4 Прочитайте скрипты, которые будете запускать (01, 02, 03, 05), и одним абзацем объясните владельцу, что они делают: предварительная проверка только читает; установка — это «opkg install» одного проверенного пакета без флагов принуждения; проверка только читает.

=== 5. РЕЗЕРВНАЯ КОПИЯ, ПРЕДВАРИТЕЛЬНАЯ ПРОВЕРКА, УСТАНОВКА (сначала спросите владельца) ===
5.1 Закрытая копия настроек на компьютер владельца (в ней есть секреты, никогда не выкладывайте): ssh ... "tar czf - /etc/config /etc/homensai-vpn /etc/glversion" > router-backup.tgz  (в Windows PowerShell используйте cmd /c, чтобы бинарный файл не испортился). Проверьте, что файл больше 100 КБ, и скажите владельцу, где он лежит.
5.2 Копирование на роутер: scp -O 01-preflight.sh 02-install.sh 03-verify.sh 05-emergency.sh homensai-auto-vpn_VERSION-1_all.ipk root@АДРЕС_РОУТЕРА:/tmp/
5.3 Запуск: ssh ... "cd /tmp && sh 01-preflight.sh" . Он должен закончиться строкой «READY to continue». Если единственный FAIL — старый журнал транзакции (native journal phase HELD-ON-RESERVE или похожий) от прежнего теста: покажите владельцу фазу журнала, спросите, вернул ли он порядок VPN-правил вручную в панели GL.iNet, и только после ясного «ДА» архивируйте журнал (ПЕРЕМЕСТИТЕ, не удаляйте): mv /etc/homensai-vpn/native-transaction.json /etc/homensai-vpn/native-transaction.closed-ДАТА.json . Затем запустите проверку снова. Любой другой FAIL: ОСТАНОВИТЕСЬ и сообщите.
5.4 Установка: ssh ... "cd /tmp && sh 02-install.sh /tmp/homensai-auto-vpn_VERSION-1_all.ipk"
5.5 Проверка: ssh ... "cd /tmp && sh 03-verify.sh wait" . Должно закончиться «RESULT: PASS» (версия пакета, версия программы, свежий статус, Auto выключен, нет собственной блокировки, один процесс мониторинга, отпечаток сети/файрвола/маршрутов не изменился). Если нет, ОСТАНОВИТЕСЬ, покажите вывод и предложите восстановление из router-test-kit/EMERGENCY.md. Удаление, если захочет владелец: opkg remove homensai-auto-vpn (настройки сохраняются).

=== 6. ЗАПУСК МОНИТОРИНГА ===
6.1 Мониторинг должен быть всегда включён и стартует сам после установки. Проверьте: uci -q get homensai_vpn.main.enabled . Если не 1, запустите: ubus call homensai-vpn monitor_control "{\\"enabled\\":true}" (или владелец нажимает «Запустить мониторинг» в блоке «Мониторинг» на странице «Обзор», он показан только когда мониторинг не работает). Подождите до 90 секунд.
6.2 Подтвердите доказательствами, а не надеждой: ps w | grep "[a]gent.py daemon" показывает один процесс; ubus call homensai-vpn status | jsonfilter -e "@.version" -e "@.time" показывает новую версию и время не старше 90 секунд; ubus call homensai-vpn status | jsonfilter -e "@.profiles[*].name" перечисляет VPN-профили, которые видит мониторинг. Одна лишь принятая в очередь команда НЕ доказывает, что программа работает.
6.3 Auto должен остаться ВЫКЛЮЧЕННЫМ: uci -q get homensai_vpn.main.native_enabled должно быть 0 или пусто.

=== 7. ЧАСТЬ ВЛАДЕЛЬЦА В БРАУЗЕРЕ (направляйте, не делайте за него) ===
7.1 Откройте http://АДРЕС_РОУТЕРА:8080/cgi-bin/luci/ -> войдите как root -> Services -> HomenS.AI Auto VPN. Обновите страницу с Ctrl+F5 (после обновления версии ещё раз выйдите и войдите).
7.2 На первом экране условия использования. Владелец сам читает и отмечает оба флажка. Вы никогда не принимаете условия за него.
7.3 Левое меню -> «Обучение»: интерактивный курс на 5 минут (что это, как пользоваться, что делать, если пропал интернет). Рекомендуйте его.
7.4 «Обзор»: блок рядом с «Проверить VPN сейчас» должен писать «Мониторинг включён» с зелёной лампой и числом проверок; графики появятся на странице «Статистика» через несколько минут.
7.5 «Настройки» -> «Настройка» -> 1 · Система (мастер): прочитайте список профилей с роутера (шаг 6.2), предложите основной и резервный в РАЗНЫХ странах или у разных провайдеров, а выбрать и нажать «Сохранить» после обзора должен владелец. Не просите VPN-ключи и не запускайте неактивные профили. Сохранение настроек НЕ даёт разрешения на переключение.
7.6 TELEGRAM (по желанию, отчёт каждые 60 минут; отказы и переключения включены): делает владелец, вы только направляете: (а) в Telegram откройте https://t.me/BotFather и отправьте /newbot, выберите имя и username, оканчивающийся на «bot», и скопируйте токен, который выдаст BotFather (цифры, двоеточие, затем буквы); (б) откройте нового бота и нажмите Start (бот не может написать первым); (в) узнайте ID чата: напишите https://t.me/userinfobot и скопируйте число после «Id» (у группы ID начинается с минуса, публичный канал можно указать как @имя_канала); (г) на странице роутера «Настройки» -> «Настройка» -> 2 · Telegram вставьте токен и ID чата, выберите интервал (хорошо 60 минут) и час суток (например 8), проверьте обзор, «Сохранить»; (д) нажмите «Проверить доставку Telegram» и убедитесь, что сообщение пришло. Токен вводится ТОЛЬКО в эту форму, никогда в этот чат. Если тест не прошёл, страница покажет код TELEGRAM-...; см. «Таблицу кодов ошибок» на странице «События и ошибки» (меню «Расширенное»).

=== 8. ИТОГОВЫЙ ОТЧЁТ ===
Напишите короткий отчёт из трёх списков: ПРОВЕРЕНО (с выводом команды или экраном, который вы видели), НЕ ПРОВЕРЕНО (скажите прямо: например переключение на реальном железе, путь компьютера в LAN, DNS и Kill Switch, IPv6, потеря питания, устойчивость 24 часа) и СЛЕДУЮЩИЕ ШАГИ ВЛАДЕЛЬЦА. Включите: версию пакета, sha256, состояние мониторинга, увиденные профили, результат доставки в Telegram, где лежит закрытая копия, как остановить только эту программу (ssh ... "sh /tmp/05-emergency.sh stop-auto" или opkg remove homensai-auto-vpn), как запустить снова и аварийный документ router-test-kit/EMERGENCY.md. Напомните владельцу сменить пароль роутера, если его кто-либо видел, и удалить закрытую рабочую папку, когда она больше не нужна.

=== 9. ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК ===
9.1 Нет интернета после любого шага: скажите владельцу использовать телефон; режим мониторинга маршруты не меняет, поэтому сначала проверьте в панели GL.iNet VPN Dashboard (основное правило первым, туннели подключены). Затем только чтение: ssh ... "sh /tmp/05-emergency.sh show" (скопируйте набор снова, если /tmp очистился после перезагрузки).
9.2 Страница показывает 403, пустая или старая: откройте приватное окно браузера, нажмите Ctrl+F5, выйдите из LuCI и войдите снова. Не ослабляйте защиту и не перезапускайте rpcd снова и снова.
9.3 На странице роутера «Помощь» (в левом меню) есть пошаговые темы для тех же ситуаций.

=== 10. ПОЗЖЕ, ТОЛЬКО ЕСЛИ ВЛАДЕЛЕЦ ПРОСИТ АВТОМАТИЧЕСКОЕ ПЕРЕКЛЮЧЕНИЕ ===
Объясните, но не выполняйте: Auto переключает ровно между двумя VPN-профилями (основной и резервный). Ему нужен пройденный LAN-тест: владелец сам запускает LAN-помощника (скрипт PowerShell 7, см. https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/LAN-HELPER.ru.md) с компьютера, подключённого кабелем LAN, сначала в режиме «только проверка», и сам вводит слово TEST. Каждое автоматическое переключение должно быть подтверждено этим помощником, иначе роутер вернётся через 90 секунд. Работа Auto без присмотра пока не поддерживается. Приёмка переключения на реальном GL-MT6000 ещё не завершена: скажите об этом прямо.

Начните сейчас с пункта 0.1.`;
var AI_LAN_PROMPT_EN=`You are an assistant that helps the owner run the "LAN helper" of the experimental software "HomenS.AI Auto VPN" (GL.iNet GL-MT6000 / Flint 2). The helper is a small PowerShell 7 script that runs on the owner's Windows computer and checks, from the computer's side, that the internet really works through the router before and after a switch to the reserve VPN. Project: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (MIT, experimental alpha). Do the technical work yourself, step by step, and explain each step in plain language.

HARD RULES
1. Experimental software: the full trial switches the router to the reserve VPN for a few minutes and can interrupt the internet. Before step 5 tell the owner this and get an explicit "yes, run the full trial" from them in this chat.
2. SECRETS: never ask for, read, print, log or store the router password, SSH keys, Telegram token, VPN keys or configs. The helper asks for the router password itself and takes it privately; the owner types it in the terminal. Never put a password on a command line.
3. You never type the word TEST for the owner and never press the confirmation for them. The owner types TEST and the password themselves.
4. Change nothing on the computer except downloading the two helper files into one new folder and installing PowerShell 7 if it is missing (ask first). No network, VPN, DNS, firewall or router settings. Never turn Auto on; the owner does that in the web page after the trial passed.
5. Stop at the first error or surprise. Show the exact message and the capital-letter code, say what is known and not known, and open the page Help -> "The LAN helper fails" for that code. Do not invent workarounds.

STEPS
1. Ask for the router address (usually 192.168.8.1) and whether the computer is connected by LAN cable (recommended). Check that the web page http://ROUTER_ADDRESS/ answers.
2. Check PowerShell 7: run "pwsh -v". If it is missing, tell the owner and, with their consent, run "winget install Microsoft.PowerShell", then open a new terminal.
3. Download the two files from the program page (Overview or Settings -> "Download LAN helper" and "Download launcher") or from the router at /luci-static/resources/view/homensai-vpn/client-test.ps1 and start-lan-helper.ps1. Put both into a new folder, for example %USERPROFILE%\homensai-lan-helper. Tell the owner they are plain text files and can be read in Notepad.
4. In that folder run: pwsh -NoProfile -File .\start-lan-helper.ps1 . Choose mode 1 (check only). It reads and changes nothing. Report the result.
5. Only if mode 1 passed and the owner said yes in this chat: run the launcher again and choose mode 3 (full trial). Tell the owner they will now be asked for the router password and for the word TEST, and that they must type both themselves. Do not look at the keyboard input. Wait until the helper finishes.
6. Read the result. If it says the trial passed, tell the owner to open the web page and press the Auto button in the "Automatic VPN failover" block. If it failed, follow rule 5.

FINAL REPORT with three lists: DONE (with the real output), NOT DONE, NOT VERIFIED. Never claim the LAN path is proven unless the helper said so.`;
var AI_LAN_PROMPT_RU=`Вы — помощник, который помогает владельцу запустить «LAN-помощник» экспериментальной программы «HomenS.AI Auto VPN» (GL.iNet GL-MT6000 / Flint 2). LAN-помощник — небольшой скрипт PowerShell 7 на компьютере владельца с Windows: со стороны компьютера он проверяет, что интернет действительно работает через роутер до и после переключения на резервный VPN. Проект: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (MIT, экспериментальная alpha). Техническую работу делайте сами, шаг за шагом, и простыми словами объясняйте каждый шаг.

ЖЁСТКИЕ ПРАВИЛА
1. Экспериментальная программа: полный тест на несколько минут переключает роутер на резервный VPN и может прервать интернет. Перед шагом 5 скажите это владельцу и получите в этом чате явное «да, запускай полный тест».
2. СЕКРЕТЫ: никогда не спрашивайте, не читайте, не печатайте, не логируйте и не сохраняйте пароль роутера, SSH-ключи, токен Telegram, ключи и конфиги VPN. Помощник сам спрашивает пароль роутера и принимает его скрыто; владелец вводит его в терминале сам. Никогда не ставьте пароль в командную строку.
3. Вы никогда не вводите слово TEST за владельца и не нажимаете подтверждение за него. TEST и пароль вводит сам владелец.
4. Ничего не меняйте на компьютере, кроме скачивания двух файлов помощника в одну новую папку и установки PowerShell 7, если его нет (сначала спросите). Никаких настроек сети, VPN, DNS, брандмауэра или роутера. Никогда не включайте Auto: это делает владелец в веб-странице после успешного теста.
5. Остановитесь на первой ошибке или неожиданности. Покажите точное сообщение и код заглавными буквами, скажите, что известно и что неизвестно, и откройте страницу «Помощь» → «LAN-помощник не работает» для этого кода. Не придумывайте обходных путей.

ШАГИ
1. Спросите адрес роутера (обычно 192.168.8.1) и подключён ли компьютер кабелем (рекомендуется). Проверьте, что страница http://АДРЕС_РОУТЕРА/ отвечает.
2. Проверьте PowerShell 7: «pwsh -v». Если его нет, скажите владельцу и с его согласия выполните «winget install Microsoft.PowerShell», затем откройте новый терминал.
3. Скачайте два файла со страницы программы («Обзор» или «Настройки» → «Скачать LAN-помощник» и «Скачать запуск») либо с роутера по адресу /luci-static/resources/view/homensai-vpn/client-test.ps1 и start-lan-helper.ps1. Положите оба в новую папку, например %USERPROFILE%\homensai-lan-helper. Скажите владельцу, что это обычные текстовые файлы, их можно прочитать в Блокноте.
4. В этой папке выполните: pwsh -NoProfile -File .\start-lan-helper.ps1 . Выберите режим 1 (только проверка). Он ничего не меняет. Сообщите результат.
5. Только если режим 1 прошёл и владелец сказал «да» в этом чате: запустите запуск снова и выберите режим 3 (полный тест). Скажите владельцу, что сейчас у него спросят пароль роутера и слово TEST и что оба он вводит сам. Не смотрите на ввод с клавиатуры. Дождитесь окончания работы помощника.
6. Прочитайте результат. Если тест пройден, скажите владельцу открыть веб-страницу и нажать кнопку Auto в блоке «Автоматическое переключение VPN». Если не пройден — действуйте по правилу 5.

ИТОГОВЫЙ ОТЧЁТ тремя списками: СДЕЛАНО (с реальным выводом), НЕ СДЕЛАНО, НЕ ПРОВЕРЕНО. Никогда не утверждайте, что путь в LAN доказан, если помощник этого не сказал.`;
function renderAiPrompt(which){
  var lan=which==='lan';
  var text=lan?bi(AI_LAN_PROMPT_EN,AI_LAN_PROMPT_RU):bi(AI_PROMPT_EN,AI_PROMPT_RU);
  var copy=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
    try{navigator.clipboard.writeText(text).then(function(){copy.textContent=bi('Prompt copied','Промпт скопирован');setTimeout(function(){copy.textContent=bi('Copy the prompt','Скопировать промпт');},3000);}).catch(function(){selectPrompt();});}catch(error){selectPrompt();}
  }},bi('Copy the prompt','Скопировать промпт'));
  var pre=E('pre',{'class':'hv-cmd hv-prompt','tabindex':'0'},text);
  function selectPrompt(){try{var range=document.createRange();range.selectNodeContents(pre);var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);}catch(e){}}
  return E('div',{'class':'hv-ai-prompt'},[
    lan?E('p',{},bi('Do not want to run the LAN helper by hand? Press “Copy the prompt” and paste it into your AI agent (one that can run commands on your computer). It checks PowerShell 7, downloads the two helper files, runs the check-only mode by itself and explains the result. The full trial, the router password and the word TEST stay with you.','Не хотите запускать LAN-помощник вручную? Нажмите «Скопировать промпт» и вставьте его в вашего ИИ-агента (того, что может выполнять команды на вашем компьютере). Он проверит PowerShell 7, скачает два файла помощника, сам запустит режим проверки и объяснит результат. Полный тест, пароль роутера и слово TEST остаются за вами.')):E('p',{},bi('Want the result faster? Use your own AI agent (one that can run commands on your computer). Press “Copy the prompt”, paste it into the agent, and it will check the router, install the program, verify it, start the monitor and guide you through the Telegram setup, step by step. You only answer its questions and do the few things that must be done by you: accept the risk and the terms, type secrets into the router page, and press Save in the wizards.','Хотите получить результат быстрее? Используйте своего ИИ-агента (того, который умеет выполнять команды на вашем компьютере). Нажмите «Скопировать промпт», вставьте его агенту, и он проверит роутер, установит программу, проверит её, запустит мониторинг и проведёт вас по настройке Telegram шаг за шагом. Вам нужно только отвечать на его вопросы и сделать то немногое, что можете сделать только вы: принять риск и условия, ввести секреты на странице роутера и нажать «Сохранить» в мастерах.')),
    lan?E('p',{'class':'hv-ready-intro'},bi('The prompt forbids the agent to ask for or type your password or the word TEST, and to turn Auto on; it must get your explicit yes before the full trial and stop at the first error. Read it before you paste it; the text below is exactly what is copied.','Промпт запрещает агенту спрашивать или вводить ваш пароль и слово TEST и включать Auto; перед полным тестом он обязан получить ваше явное «да» и остановиться на первой ошибке. Прочитайте его перед вставкой; ниже ровно тот текст, который копируется.')):E('p',{'class':'hv-ready-intro'},bi('The prompt asks the agent to protect your secrets, to work in monitor mode only (Auto stays off), to stop at the first problem and to report honestly what was verified and what was not. Read it before you paste it; the text below is exactly what is copied.','Промпт просит агента беречь ваши секреты, работать только в режиме мониторинга (Auto остаётся выключенным), останавливаться на первой проблеме и честно сообщать, что проверено, а что нет. Прочитайте его перед вставкой; ниже ровно тот текст, который копируется.')),
    E('div',{'class':'hv-ai-actions'},[copy]),pre]);
}

// A separate Help topic, shown first: its body is the copyable prompt instead of numbered steps.
HELP_TOPICS.unshift({id:'ai-prompt',title:['Prompt for your AI agent','Промпт для вашего ИИ-агента'],when:['You would rather let an AI agent install, check and configure everything for you.','Вы хотите, чтобы установку, проверку и настройку полностью сделал ИИ-агент.'],steps:[],custom:function(){return renderAiPrompt();}});

// Second prompt: an AI agent runs the LAN helper with the owner (check-only mode by itself; the full trial only with the owner's yes and their own password).
HELP_TOPICS.splice(1,0,{id:'ai-lan-prompt',title:['Prompt for your AI agent: run the LAN helper','Промпт для ИИ-агента: запустить LAN-помощник'],when:['You do not want to run the LAN helper by hand: an AI agent that can run commands on your computer does the steps and asks you only for what it must not do itself.','Вы не хотите запускать LAN-помощник вручную: ИИ-агент, который может выполнять команды на вашем компьютере, делает шаги сам и спрашивает вас только о том, что не имеет права делать сам.'],steps:[],custom:function(){return renderAiPrompt('lan');}});

// Opens a Help topic from anywhere (used by the LAN trial card in Settings).
function openHelpTopic(id){
  var link=document.querySelector('[data-hv-tab="help"]');if(link)link.click();
  setTimeout(function(){var topic=document.getElementById('help-'+id);if(topic){topic.open=true;try{topic.scrollIntoView({block:'start'});}catch(e){}}},200);
}
function helpLink(id,label){return E('a',{'href':'#help','class':'hv-help-link','click':function(ev){ev.preventDefault();openHelpTopic(id);}},label);}
// Settings > Automatic switching: why the LAN helper exists, how to get it, where the full guide and the AI prompt are.
function lanHelperExplain(){
  return E('div',{'class':'hv-lan-explain'},[
    E('h4',{},bi('Why a LAN helper is needed','Зачем нужен LAN-помощник')),
    E('p',{},bi('The router can see its VPN tunnels, but it cannot see what your own computer or phone gets. Whether DNS, the Kill Switch and the real internet work for a device at home through the reserve VPN can only be proven from that device. The LAN helper is a small program that runs on a Windows computer in your home network, sends the same kind of traffic through the router before and after a switch and tells the router “confirmed”. Without that confirmation the router goes back to the previous route after 90 seconds. That is why Auto stays locked until one trial has passed.','Роутер видит свои VPN-туннели, но не видит, что получает ваш компьютер или телефон. Работают ли DNS, Kill Switch и настоящий интернет у устройства дома через резервный VPN, можно доказать только с самого устройства. LAN-помощник — небольшая программа на компьютере с Windows в вашей домашней сети: она пропускает такой же трафик через роутер до и после переключения и сообщает роутеру «подтверждаю». Без этого подтверждения роутер через 90 секунд возвращается на прежний маршрут. Поэтому Auto заблокирован, пока не пройден один тест.')),
    E('p',{},bi('It runs only when you start it, installs nothing and changes no network settings of the computer. Mode 1 only reads; the full trial asks for the router password (typed privately, never saved) and the word TEST.','Он запускается только когда вы его запускаете, ничего не устанавливает и не меняет сетевые настройки компьютера. Режим 1 только читает; полный тест спрашивает пароль роутера (вводится скрыто, нигде не сохраняется) и слово TEST.')),
    E('ol',{},[E('li',{},bi('Press “Download LAN helper” and “Download launcher” below and put both files into one folder.','Нажмите «Скачать LAN-помощник» и «Скачать запуск» ниже и положите оба файла в одну папку.')),
      E('li',{},bi('Install PowerShell 7 once, open it in that folder and start the launcher; first choose mode 1 (check only), then mode 3 (full trial).','Один раз установите PowerShell 7, откройте его в этой папке и запустите; сначала выберите режим 1 (только проверка), затем режим 3 (полный тест).')),
      E('li',{},bi('When the trial has passed, press the Auto button on the Overview.','Когда тест пройден, нажмите кнопку Auto на «Обзоре».'))]),
    E('p',{},[helpLink('helper-what',bi('Help: full guide, step by step','Помощь: полная инструкция по шагам')),' · ',helpLink('ai-lan-prompt',bi('Help: prompt for your AI agent to run it for you','Помощь: промпт для вашего ИИ-агента, чтобы он запустил всё за вас')),' · ',helpLink('helper',bi('Help: the helper fails','Помощь: помощник не работает'))])]);
}
