<!-- doc-role: current -->
# Channel/graph display contract

| Context | Meaning |
|---|---|
|Manual route control|Green is freshly confirmed selected; red can mean not selected; yellow means pending/clarifying. It is not a universal health color.|
|Current VPN checks|Selected healthy is green; healthy standby yellow; off/failure red; missing evidence unconfirmed.|
|M/R transition diagram|M main left, R reserve right; arrow gives direction. Pending is yellow, confirmed selected green/other red.|
|Standalone failure/recovery event|Only the event-time role is colored failed/recovered; no switch/other health is invented.|
|Failure episode chart|Blue main/orange reserve, with old missing-role records disclosed separately rather than a third invented channel.|
|Pinned service monitor|Monitor/Auto first; working channel above waiting/failed, retaining role labels.|
|Role cards|Main always left/top, reserve right/bottom; this fixed role order differs from working-first tables.|

Freshness uses router-observed time plus elapsed browser time. Queue ACK is not completion; stale data expires. Two Connected tunnels do not prove two simultaneous selected common routes or external-client connectivity. [Event provenance](CHANNEL-ATTRIBUTION.md) · [Behavior](HOW-IT-WORKS.en.md).
