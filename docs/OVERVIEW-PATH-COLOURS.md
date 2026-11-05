<!-- doc-role: current -->
# Channel/graph display contract

| Context | Meaning |
|---|---|
|Every channel lamp, both views (Simple and Console, page from 03 Nov 2026)|Green = the channel works; the chip "Traffic here" marks the one carrying traffic, "Standing by" the other; yellow = a check or a switch; red = not responding or tunnel off (with code); grey = no fresh data.|
|Manual route control|"Switch here" appears only on the card that does not carry traffic; the status shows the switch until the router confirms it. A manual switch never turns Auto off.|
|Big status lamp (Home hero / Console strip)|Green = VPN works on the primary; yellow = reserve in use, a switch or a check; red = the current channel or both fail; grey = no fresh data. The Auto switch states its own state in words (Auto is on / Turning Auto on… / Auto is off).|
|Current VPN checks|Healthy is green (selected or standby, told apart by the chip); failure red; missing evidence grey/unconfirmed.|
|M/R transition diagram (legacy page, tag ui-original-2.1.0-alpha6)|M main left, R reserve right; arrow gives direction. A switch in progress is yellow, confirmed selected green/other red.|
|Standalone failure/recovery event|Only the event-time role is colored failed/recovered; no switch/other health is invented.|
|Failure episode chart (legacy page)|Blue main/orange reserve, with old missing-role records disclosed separately rather than a third invented channel.|
|Pinned service monitor (legacy page)|Monitor/Auto first; working channel above waiting/failed, retaining role labels.|
|Role cards|Primary always left/top, reserve right/bottom, in both views.|

Freshness uses router-observed time plus elapsed browser time. Queue ACK is not completion; stale data expires. Two Connected tunnels do not prove two simultaneous selected common routes or external-client connectivity. [Event provenance](CHANNEL-ATTRIBUTION.md) · [Behavior](HOW-IT-WORKS.en.md).
