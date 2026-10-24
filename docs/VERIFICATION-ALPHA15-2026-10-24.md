<!-- doc-role: versioned-evidence -->
# Speed button and graph —0.9.1-alpha15

## Исправлено

Кнопка была недоступна из-за выключенной настройки. Теперь она открывает проверку: выбранные подключённые серверы, лимит трафика и явное «Включить и запустить», если тесты выключены. Подтверждённое сохранение включает ручные тесты с текущими лимитами и оставляет авто-тесты выключенными. Ошибка сохранения не вызываетspeed_start. Занятое задание блокирует повторный запуск; причины отказа показаны рядом. Серверные проверки нагрузки, квот, паузы и маршрута не изменены.

Под таблицей серверов — график скачивания и отдачи с выбором сервера и существующего периода. Показаны реальные завершённые измерения, первая точка и дальнейшая история; ошибки разделяют линии, а не становятся нулём. Это история выборочных HTTPS-замеров, а не непрерывная скорость интерфейса.

## Проверка

Точныйa60971e61cecb5a870aa2dc500c96d260f203f5f прошёл двеCI:771application/112QA в каждой среде,47UI в основной; пропуски указаны в квитанциях. КаноническийIPK831752байт,SHA256`98e8ff51ab77e895a693ef08f519d51062e3d6fab41afa78ba7c10ed6c78dab0`. НоваяUI-регрессия проверяетобзор/подтверждение/порядокsave→start/отказсохранения/CPUbusy/дубли/выборсервера/разрывыграфикаRU/EN.

НаMT3000/4.11.0: свежая192-entryшифрованнаякопия с независимым чтением →Stop →opkg15 →87файлов/прав/RPC/реальныеHTTP8080+pinnedHTTPS →обычныйStart67.125с →резерв41.203с. Предыдущие двазамера сохранены; на15 выполнены ещё два с16МиБ полезного трафика. WireGuard30.463/17.930Мбит/с;OpenVPN14.570/10.378Мбит/с. Всего4успешные записи. AutoRUNNING/резерв и обаVPNDNS+2HTTPS подтверждены. Условия1 и пользовательские настройки сохранены; после —независимо расшифрованная193-entryкопия. СетьWindows/MT6000/маршруты/VPN-профили не менялись.

## English and limits

Reviewed enabling/manual launch and measured download/upload history are implemented below the server table. Existing backend guards remain. Exact-source dual-runtimeCI47UI and actualMT3000 upgrade/served files/RPC/two post-install measurements/preserved history/settings/terms/backups passed. Auto remainsON/reserve. [QA](../qa/SPEED-ALPHA15-2026-10-24.json) · [Physical receipt](../qa/MT3000-ALPHA15-2026-10-24.json).

Native-browser visual acceptance is NOT VERIFIED: ComputerUse stopped before capture because it could not confidently identify the browserURL; no more UI input issued. Native UIwas not claimed from HTTP/DOM tests. Independent externalLAN/IPv6/KillSwitch and full line-capacity acceptance remain outside these bounded samples. No newVM exercise was required for this UI-only feature; prioralpha14VM evidence remains version-scoped.

## Publication

Published actual non-draft prereleases: [GitHub alpha15](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha15) · [Gitea alpha15](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha15). Four assets/server downloaded andSHA256verified. Canonicaltag/source`7591d37f26a10d60df38c77e3f041fca8e54e012`,publictag/source`292eb5000933a17de9d0ed75ba9b8dd293ad529e`,identicaltree`bd3c50c139433fbf6e2cdb0e9b3aeebdb71429a2`. Bothmainrefs/stable0.9.0/oldtags/assets preserved. Product unchanged froma60971e; a documentation-only closure follows.
