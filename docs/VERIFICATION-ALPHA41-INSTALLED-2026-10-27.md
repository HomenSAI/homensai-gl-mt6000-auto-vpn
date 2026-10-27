# Alpha41: channel reliability indicator

The dedicated MT3000 runs 0.9.1-alpha41-1 (source aa98015, package SHA256 13060528...). Exact dual-runtime CI passed and two isolated builds equal the CI hash. A channel whose router checks failed in at least 20% of the cycles over five minutes is labelled "Reliability problem: check loss N% (X of Y checks in 5 min)" with the catalogue code CHANNEL-UNRELIABLE; the Tests recommendation is computed from loss statistics. The installed page bundle contains the feature (HTTP/RPC check passed). The page was not driven in a native browser.

Installation used the ordinary Stop (held on the reserve because the primary was unhealthy), after which the supervisor restored the primary order by itself, then a normal Start. Auto is RUNNING and, because the primary lost 56-70% of test packets, switched to the working reserve (COMMITTED). Pair not held; network identity and protected configurations unchanged. Pre/post encrypted backups were independently read. [Receipt](../qa/MT3000-ALPHA41-2026-10-27.json).

# Альфа41: индикатор надёжности канала

На выделенном MT3000 работает 0.9.1-alpha41-1. Канал с долей непройденных проверок от 20% за 5 минут подписан «Проблема с надёжностью: потери проверок N%», код CHANNEL-UNRELIABLE, рекомендация считается по статистике потерь. Auto включён и работает на резерве, потому что основной теряет 56–70% тестовых пакетов. Страница в браузере не открывалась.
