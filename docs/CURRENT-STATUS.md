# Current product status / Текущее состояние

As of23 October 2026: **HomenS.AI Auto VPN 0.9.0**, package `0.9.0-1`, experimental release under MIT. [Release notes](../releases/v0.9.0.md) · [exact release evidence](RELEASE-0.9.0.md).

| Area | Current result |
|---|---|
| Prepared GL-MT3000, firmware 4.11.0 / OpenWrt 21.02-SNAPSHOT | Continuous primary/reserve Auto tested with router-originated IPv4 DNS/twoHTTPS probes |
| Operator switching while Auto ON | Both directions tested; healthy preference retained; confirmed failure can release preference for recovery |
| Monitoring | Default-on/required before ordinary Auto Start; parallel VPN measurements, bounded faster startup polling |
| UI | Agreement → illustrated introduction → eight-step setup; EN/RU, help/examples, bottom skip, explicit channel roles, retained viewport/error state |
| History | Live + stored1–24h route graphs; seven-day detailed events, monthly aggregates and lifetime counters; export/retention limits explicit |
| MT6000 | Model support and historical tests recorded; current continuous-mode hardware acceptance not established |
| Restart | Monitoring/supervisor services recover; Auto requires a new explicit Start |
| Internet proof | Router-only IPv4 evidence; no independent LAN-client certification |
| Remaining acceptance | 24-hour traffic soak, physical power-cut, IPv6 failover and unrestricted multi-reserve hierarchy not established |

Обычный запуск Auto подключает только сохранённую разрешённую пару на подготовленном MT3000. Мониторинг сам не создаёт профили и не импортирует ключи. Оба штатных туннеля могут быть Connected; выбранный маршрут трафика при этом один. Зелёный выбранный исправный канал, резерв в списке ожидания и подключённый туннель — разные понятия.

Датированные отчёты сохраняют свои результаты, включая отказы и неудачные испытания. Они не переопределяют этот статус. Значения времени работы и счётчики относятся только к указанным наблюдениям, а не к доказанной непрерывной доступности внешнего клиента.
