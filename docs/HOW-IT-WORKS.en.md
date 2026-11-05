<!-- doc-role: current -->
# How the system works

[Current version/evidence](CURRENT-STATUS.md) · [Full guide](CURRENT-STATE.en.md)

**License:** [HomenSAI Personal & Commercial Source License v1.0](../LICENSE) — source-available, not open source.

## Roles, clients and traffic

Main and reserve are roles, not WireGuard/OpenVPN names. Stock firmware owns provider profiles, credentials and server selection within a tunnel. The application observes exact protocol/interface/profile generations and coordinates the saved pair of distinct clients. A country/display group such as `default` is metadata, not proof of channel membership.

The configured profile, connected tunnel, healthy router probe and selected common traffic route are different states. Both clients can be connected while one route is selected. Saving the pair edits application metadata; explicit prepared Auto Start can enable managed clients and select their policy. Normal Stop restores the managed baseline when verified, otherwise exposes the retained/unconfirmed outcome.

## Continuous Auto

The qualified prepared MT3000/4.11.0 path uses fresh router IPv4 DNS/HTTPS evidence, stable identity, policy/worker/ownership checks and bounded recovery. Consecutive-failure/success thresholds, cooldown, dwell and budgets prevent an immediate switch on every noisy sample. A low response time is a recommendation, not permission to move traffic.

Manual selection is an explicit command with a confirmed result, not an immediate lamp change on queue ACK. A manual switch never turns Auto off: Auto keeps watching the chosen channel and moves traffic to the other one if it fails, and after an Auto restart or package upgrade it returns to the primary when that is healthy. Automatic return follows saved policy and readiness; a hold-reserve policy does not promise return just because primary recovers. A deliberate bounded fault test is separately labelled and can test both directions without changing the saved preference.

## Runtime layers and switching time

The router part runs on layers that share the same files and rules. Python 3.9 is the base and the last fallback. On top of it, in the 2.0.0-alpha line, Lua 5.1 runs the monitor and Auto as two services (an optional single process `hv-core` exists); a C module `canon_c.so` does the canonical JSON inside Lua, and if it fails to load or fails its self-probe the same code runs in pure Lua by itself (`HOMENSAI_CANON_C=0` forces Lua). If the Lua services fail repeatedly, Auto falls back to the Python supervisor (`LUA-AUTO-FALLBACK`). The switch history is an append-only journal.

Fast detection is on by default since alpha24 (`option lua_fast_detect '0'` turns it off): a 1 s heartbeat of both Auto channels starts a dense confirmation within about 2 s of an outage (two lost beats in a row since 03.11.2026, was three); the failure count (3 failed checks), the live reserve and the firmware checks are unchanged. Measured on the MT3000: a manual switch is done in about 0.7 s; the automatic decision comes 26-28 s after an outage (58-88 s without fast detection) and traffic moves 1.3-1.6 s after it. [Numbers per layer](MEASUREMENTS.en.md#8-runtime-pyramid-and-switch-times).

## Other proof modes

A client-confirmed trial uses the Windows helper; its DNS/HTTPS/exit evidence comes from that real client. Router-hosted namespace and router-probed evidence are not external-client proof. CheckOnly is prerequisite inspection; ProbeOnly sends bound data probes; a full trial can change router traffic. None changes PC routes/NIC/DNS automatically.

## Display and history

Role cards keep main left/top and reserve right/bottom. Current-check tables and pinned service rows put the working channel first. M/R direction and green/red in a confirmed transition describe route selection; a standalone red failure marks only its observed channel. Event-time roles cannot be rewritten using today's pair.

Only blue main/orange reserve failure episodes are charted. Legacy records without a saved role are disclosed outside those series. Consecutive equal log states share a time range; A→B→A remains three runs. Saved history begins with 20 rows, and the full downloaded retained snapshot supports search/sort.

[Storage limits](HISTORY-RETENTION.md) · [Control/setup](CONTROL-AND-SETUP.md) · [Helper](LAN-HELPER.en.md) · [Recovery](../router-test-kit/EMERGENCY.md).
