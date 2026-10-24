<!-- doc-role: current -->
# How the system works

[Current version/evidence](CURRENT-STATUS.md) · [Full guide](CURRENT-STATE.en.md)

## Roles, clients and traffic

Main and reserve are roles, not WireGuard/OpenVPN names. Stock firmware owns provider profiles, credentials and server selection within a tunnel. The application observes exact protocol/interface/profile generations and coordinates the saved pair of distinct clients. A country/display group such as `default` is metadata, not proof of channel membership.

The configured profile, connected tunnel, healthy router probe and selected common traffic route are different states. Both clients can be connected while one route is selected. Saving the pair edits application metadata; explicit prepared Auto Start can enable managed clients and select their policy. Normal Stop restores the managed baseline when verified, otherwise exposes the retained/unconfirmed outcome.

## Continuous Auto

The qualified prepared MT3000/4.11.0 path uses fresh router IPv4 DNS/HTTPS evidence, stable identity, policy/worker/ownership checks and bounded recovery. Consecutive-failure/success thresholds, cooldown, dwell, budgets and operator hold prevent an immediate switch on every noisy sample. A low HTTPS delay is a recommendation, not permission to move traffic.

Manual selection is an explicit command with a confirmed result, not an immediate lamp change on queue ACK. Automatic return follows saved policy and readiness; manual reserve hold does not promise return just because primary recovers. A deliberate bounded fault test is separately labelled and can test both directions without changing the saved preference.

## Other proof modes

A client-confirmed trial uses the Windows helper; its DNS/HTTPS/exit evidence comes from that real client. Router-hosted namespace and router-probed evidence are not external-client proof. CheckOnly is prerequisite inspection; ProbeOnly sends bound data probes; a full trial can change router traffic. None changes PC routes/NIC/DNS automatically.

## Display and history

Role cards keep main left/top and reserve right/bottom. Current-check tables and pinned service rows put the working channel first. M/R direction and green/red in a confirmed transition describe route selection; a standalone red failure marks only its observed channel. Event-time roles cannot be rewritten using today's pair.

Only blue main/orange reserve failure episodes are charted. Legacy records without a saved role are disclosed outside those series. Consecutive equal log states share a time range; A→B→A remains three runs. Saved history begins with 20 rows, and the full downloaded retained snapshot supports search/sort.

[Storage limits](HISTORY-RETENTION.md) · [Control/setup](CONTROL-AND-SETUP.md) · [Helper](LAN-HELPER.en.md) · [Recovery](../router-test-kit/EMERGENCY.md).
