# Channel and graph display contract — 0.9.0

| Context | Display | Meaning |
|---|---|---|
|Manual card / sidebar channel lamp|Green, motion/blink|Fresh confirmed selected channel with successful Internet checks|
|Manual card|Red, static|Not selected or confirmed connection failure; exact error shown when known|
|Manual action|Turn on only on eligible inactive red card|A command can be requested; never claim completion from ACK|
|Pending manual command|Destination yellow/Switching; other red|Selection is not yet confirmed|
|VPN inventory/Channels|Green selected healthy; yellow healthy standby; red off/failure|Connected tunnel and selected common-traffic route are distinct|
|Monitoring/data error|Explicit unknown/checking/error message|Missing evidence is not fabricated as working|
|Live/stored graphs|Primary/reserve/off only|Contiguous transition holds last confirmed selection; missing observations leave gaps|

Current UI uses router-response time plus monotonic elapsed browser time, so PC clock skew does not falsely expire fresh probes. Stale data still expires. The manual inactive-red convention intentionally differs from healthy-standby-yellow in the inventory. Both stock tunnels may remain Connected; only one common-traffic route is selected.
