<!-- doc-role: technical-reference -->
# Отклик сайтов / Website response

The displayed response is one shared metric for every card, table, recommendation, graph and latency statistic. Each VPN has its own measurement of the same three HTTPS targets: Google (`www.google.com/generate_204`), Cloudflare (`www.cloudflare.com/cdn-cgi/trace`) and Wikipedia (`www.wikipedia.org/`).

For one complete measurement, **mean milliseconds = (Google milliseconds + Cloudflare milliseconds + Wikipedia milliseconds) / 3**. The timer includes DNS through that VPN, TCP connection, verified TLS and receipt of HTTP response headers. It stops before downloading a complete page, its images or scripts. This is a small active request from the router; it does not observe the owner's browsing or measure browser rendering.

Only a fresh identity-bound result with three successful targets supplies a number. A partial measurement shows its coverage and leaves a gap, never a zero or a mean of a different target set. Statistics over a selected period weight the complete measurements by their count. Older ICMP and health-probe HTTPS measurements are not imported into this series. Auto's existing DNS/HTTPS health quorum remains separate from the response display.

На всех карточках, в таблицах, рекомендациях, графиках и статистике задержек используется один показатель. Каждый VPN отдельно проверяет те же три сайта: Google, Cloudflare и Wikipedia.

Формула одного полного замера: **среднее, мс = (отклик Google + отклик Cloudflare + отклик Wikipedia) / 3**. Время включает DNS через этот VPN, подключение TCP, проверенный TLS и получение HTTP-заголовков. Полная страница с изображениями и скриптами не загружается. Это небольшие проверочные запросы роутера; личные запросы пользователя не просматриваются, время отрисовки браузера не измеряется.

Число появляется только после свежего полного замера трёх сайтов с подтверждённой привязкой к VPN. Если ответили не все сайты, показывается полнота замера, а на графике остаётся разрыв. Ошибка не считается нулём; среднее двух сайтов не выдаётся за среднее трёх. Среднее за период учитывает число полных замеров. Старая история ICMP и HTTPS-проверок здоровья с новой серией не смешивается. Решения Auto по прежнему опираются на отдельные проверки здоровья DNS/HTTPS.

The Google HTTPS target follows its [documented connectivity-check endpoints](https://support.google.com/chrome/a/answer/6334001). The response definition corresponds to elapsed time before transfer starts, rather than a raw ICMP round trip; see [curl's timing definitions](https://curl.se/docs/manpage.html). Wikipedia requests identify the application according to the [Wikimedia User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy).
