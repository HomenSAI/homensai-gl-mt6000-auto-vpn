<!-- doc-role: current -->
# Channel/graph display contract

| Context | Meaning |
|---|---|
|Every channel lamp, every page|One rule: green = this channel carries your traffic; yellow = alive but not in use (only such a channel offers "switch to it") or a short check; red = proven failure; grey = waiting for the router.|
|Manual route control|Green is freshly confirmed selected; during a manual switch the destination card blinks green. A manual switch never turns Auto off. It is not a universal health color.|
|Auto button, traffic light, sidebar Auto lamp, live journal|Always one colour: green while Auto runs; yellow only during a real switch/start/stop and a short pulse around each scheduled check (1 s before, 3 s after); red only for a proven failure (selected channel failed, controller alarm, or no router answer for 90 s); dark when Auto is turned off.|
|Current VPN checks|Selected healthy is green; healthy standby yellow; failure red; missing evidence grey/unconfirmed.|
|M/R transition diagram|M main left, R reserve right; arrow gives direction. A switch in progress is yellow, confirmed selected green/other red.|
|Standalone failure/recovery event|Only the event-time role is colored failed/recovered; no switch/other health is invented.|
|Failure episode chart|Blue main/orange reserve, with old missing-role records disclosed separately rather than a third invented channel.|
|Pinned service monitor|Monitor/Auto first; working channel above waiting/failed, retaining role labels.|
|Role cards|Main always left/top, reserve right/bottom; this fixed role order differs from working-first tables.|

Freshness uses router-observed time plus elapsed browser time. Queue ACK is not completion; stale data expires. Two Connected tunnels do not prove two simultaneous selected common routes or external-client connectivity. [Event provenance](CHANNEL-ATTRIBUTION.md) · [Behavior](HOW-IT-WORKS.en.md).
