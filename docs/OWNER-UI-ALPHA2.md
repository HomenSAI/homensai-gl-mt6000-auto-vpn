# Owner interface follow-up: 0.9.1-alpha2

This candidate follows the installed alpha1. It does not replace the published 0.9.0 release. The current acceptance state is in [the recovery checklist](handoff/OWNER-UI-TODO-2026-10-23.md).

Primary is always first (left, or above on a narrow screen); reserve is second. Selection and latency never reorder those roles. Overview, Channels and the traffic-path explanation initially show the selected pair; other profiles are collapsed. Speed results initially show the five most recent tested profiles. Native dropdowns have enough height for their selected text. Ordinary attribution retains the application version and developer, without package/page/style implementation labels.

The server line reports an observed current kernel peer address and port, bound to the profile/interface and a fresh settled observation. Missing or ambiguous peer evidence stays “not observed”; a saved country/profile name is not substituted for the actual connected address. Inactive profiles may therefore have no observed current peer.

Channels includes a recommendation based on fresh successful **HTTPS** delays for both profiles. It names the lower-delay profile; it does not change priorities or routes. These are not ICMP ping measurements. The graph has a 1–24 hour window and a history slider. Primary is solid, reserve dashed; green is the selected route, yellow standby, grey unconfirmed. Failures and missing samples create gaps. History begins with actual recording; an update cannot reconstruct the previous day.

The live terminal pins monitor/Auto/primary/reserve status above a separate scrollback. A labelled one-second screen heartbeat moves the log without changing the router's probe interval. Scrollback is bounded to 2,000 lines, preserves an older reading position and offers return to live. The screen heartbeat is not written to flash as a router event.

Events and errors is the stored counterpart: ten initial rows, expand/collapse, date/state ordering and search over the full downloaded weekly snapshot. It reuses controller transitions and incident edges, rather than creating a competing journal. Reading an expanded snapshot remains stable during polling; “Read saved week” refreshes it. Storage warnings and dropped detail are explicitly reported.

| Data | Retention and bound | Persistence |
|---|---|---|
| Controller transitions | Rolling seven days, up to 10,000 records, 2 MiB encoded model | Existing atomic history/backup on real transitions |
| Failure/recovery detail | Rolling seven days, up to 10,000 records, 1 MiB detail | Existing accounting checkpoint; incident edges request a checkpoint |
| HTTPS delay | Last observed day, at most 1,441 minute aggregates and 32 pair identities; 256 KiB file budget | Existing configured checkpoint interval; no one-second flash writes |
| Live terminal | Up to 2,000 screen lines | Browser memory, not durable weekly storage |

The limits can discard older detail before seven days during unusually heavy activity. Unobserved intervals remain unknown. Monthly/lifetime counters are separate from detailed event retention. Atomic replacement/backups temporarily require additional space; the bounds above are not a guarantee of total filesystem consumption or flash lifetime. Corrupt latency files are retained for diagnosis and reported unavailable instead of silently overwritten.

Each Help topic includes a short copyable read-only diagnostic prompt; there is also a general unknown-cause prompt. The complete installation prompt and eight dependency-repair prompts remain separate. Diagnosis itself does not start Auto, accept terms, send messages or authorize a repair. A chat needs tools and access to carry out installation. See [the executed prompt validation report](PROMPT-VALIDATION-2026-10-23.md).
