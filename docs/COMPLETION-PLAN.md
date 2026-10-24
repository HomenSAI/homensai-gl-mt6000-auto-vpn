<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# HomenSAI Auto VPN — completion plan for approval

Prepared: 2026-10-15, Europe/Berlin.
Status: APPROVED by user on 2026-10-15. Work in progress; checkboxes require evidence.

## Current baseline — updated 2026-10-16

- Binding scope: LOCAL DEVELOPMENT ONLY. Do not connect to, deploy to, reconfigure or fault-test the router until the user authorizes a new device window.
- Last installed package recorded: 0.6.0-alpha5. Current local development candidate: 0.7.0-alpha6 (offline model/browser/container only; QEMU paused). Local code is not installed-device evidence.
- Atomic Auto intent, typed RPC/ACL checks and system-writer fixes have regression coverage. Positive system-wizard save was observed on alpha5; Telegram test delivery remains unconfirmed.
- Current local suite: 232 application Python tests plus 5 QA tests, including 256 hierarchy combinations within one parameterized test; Auto UI and setup/traffic UI regressions are separate Node checks.
- Native switching remains bounded and requires client certification. Full hierarchy selection is read-only recommendation logic; inactive-profile activation and unattended production are not accepted.
- Prior cable-helper failure and historical HTTP 403 root causes remain unresolved unless independently evidenced.

## 1. Recovery and operational safety — priority P0

- [ ] Capture sanitized baseline: package version, own configuration, controller state, policy identity, DNS, Kill Switch, acceleration state and LAN management reachability. Keep secret backups outside Git.
- [ ] Diagnose CLIENT-CABLE-NOT-LOCAL using timestamps, interface indices, source-bound routes and route changes. Do not infer a physical disconnect from an adapter state alone.
- [ ] Prove independent recovery after controller/executor failure; test stop requests during preparation, application, client confirmation and committed operation.
- [ ] Coordinate with GL.iNet workers/hotplug and operator edits. Refuse conflicting writes; never overwrite an externally changed policy silently.
- [ ] Validate IPv6 behavior independently. Keep unsupported configurations explicitly blocked until leak protection is proven.
- [ ] Verify startup after service restart and router reboot. A physical power-loss test is a separate agreed action, not a simulated crash result.
- [ ] Limit logs, flash writes, CPU, memory and retained history; detect clock changes and observation gaps.

Acceptance: LAN management remains reachable; original policy restoration or a deliberate healthy-reserve hold is independently verified; unsafe/unknown states cannot display success. No package removals or system Python replacement.

## 2. Main-page Auto mode control — priority P0

- [ ] Review and harden the existing button candidate, including concurrent Start/Stop requests, idempotence and failure between configuration writes.
- [x] Place one large power toggle on Overview: grey Off, yellow Starting/Stopping, green verified On, red Error; stale status cannot appear green.
- [x] Read actual controller state rather than changing the displayed state immediately on click. Support Stop during a transition.
- [ ] Implement explicit configuration intent and service state separately. Explain whether Start resumes a certified window or requires initial LAN verification.
- [x] Display deadline and required LAN helper while the implementation remains experimental. Do not silently remove certification or extend deadlines.
- [ ] Show a protocol/channel/server diagram with configured names, current selection, next eligible reserve and permitted arrows. Inactive automation shows broken arrows.
- [x] Display 'Control returned to router' only after confirmed safe handover. If a healthy reserve is retained, say so explicitly rather than claiming the original route was restored.
- [ ] Decide and document production enablement, reboot behavior and auto-start defaults after P0 recovery acceptance.

Acceptance: one click requests Start, another requests Stop; failed requests and rollback failures are visible; no false green state. Existing bounded-mode restrictions remain visible until production approval.

## 3. Interface and languages — priority P1

- [ ] Finish dark left navigation and light workspace using the pinned HomenSAI style core; preserve current LuCI navigation conventions.
- [x] Complete sections: Overview, Channels and servers, Statistics, Server ranking, Monthly traffic, Service monitor, Events and errors, Settings.
- [x] Link the robot/logo and developer attribution to https://homensai.com; show the running package version at top right.
- [ ] Sort cards by actual selected route and confirmed health: selected working server first, confirmed failed servers last; keep configured priority independent from visual order.
- [ ] Use green for verified health, red for confirmed failure, pale yellow for connecting/checking, grey for inactive/unknown. Connected alone is not Internet availability.
- [ ] Add column sorting, search and filters; retain operator choices across polling without moving focus unexpectedly.
- [ ] Verify English first-load default, Russian selection and persistence across reload, every section, validation messages and both desktop/mobile layouts.
- [ ] Keep generated diagnostics, causes, fixes and work logs in English in both locales. Preserve operator-entered names unchanged.
- [ ] Inspect actual installed LuCI in ordinary and private browser sessions; diagnose the historic 403 using server/session evidence, not assumptions about browser bans.

Acceptance: screenshots and interaction checks from the actual device; no clipped content, incorrect language selection, duplicate IDs or lost form input during refresh.

## 4. Configuration wizards — priority P1

- [ ] System wizard: discover existing registered VPN profiles without exporting keys; choose names, channel groups, primary/reserve order and supported protocol priorities.
- [ ] Include enable/disable logic, recovery preference, session interruption consent, failover thresholds, cooldown and return policy.
- [ ] Show a review page with supported and blocked options before applying; permit cancellation without partial configuration.
- [ ] Telegram channel wizard: private token input, channel destination, required bot permissions, deliberate test delivery and confirmed result.
- [ ] Allow reporting interval changes in monitoring settings: hourly, daily 07:00 Europe/Berlin, weekly and monthly summaries. Deduplicate reports and handle timezone/DST/restarts.
- [ ] Mask tokens after saving; exclude them from RPC status, exported logs, packages and public repositories.

Acceptance: fresh setup, editing existing setup, cancellation, invalid token/destination, denied channel permissions and successful delivery are checked. No message sent to an unapproved destination.

## 5. Failover hierarchy and operator tests — priority P1

- [ ] Implement eligible-server selection within a channel, then another channel, then another supported VPN protocol; treat Wi-Fi/Ethernet as uplinks, not VPN protocols.
- [ ] Add adapters for starting inactive profiles only after routes, DNS, Kill Switch and vendor-worker coexistence are verified.
- [x] Probe a recovery candidate before returning: endpoint reachability is only preliminary; require actual tunneled HTTPS/DNS and stable health before promotion.
- [ ] Investigate isolated parallel candidate testing with separate routing/marks or network namespaces. Block it where firmware/profile restrictions prevent isolation.
- [x] Add hysteresis, consecutive-failure/success thresholds, minimum dwell time, cooldown and backoff to prevent oscillation.
- [ ] Add an operator Forced Stop/fault page: choose server or channel, show scope, bounded timer and independent cleanup; distinguish simulated fault from actual stop.
- [ ] Keep switching within special destination policies isolated from general traffic; do not silently broaden routes or disable Kill Switch.

Acceptance: each supported transition and return is checked from a LAN client, including unavailable reserve, DNS failure, repeated failures, concurrent edits and safe cancellation. Unsupported combinations remain blocked and documented.

## 6. Measurements and statistics — priority P2

- [ ] Record server connections, disconnections, confirmed failures, recovery time and switches within/between channels and protocols without double-counting.
- [ ] Add daily/weekly/monthly grouped server histograms: healthy time green, failed time red, unobserved time grey; show connection and failure counts separately from duration.
- [ ] Preserve observation gaps, inactive reserves and partial periods explicitly; do not present inferred durations as exact measurements.
- [ ] Rank by current and period measurements; separate latency, availability and throughput. Show sample count, age and confidence limitations.
- [ ] Add selectable recommendations and explicit Apply priorities; no automatic priority rewrite merely because a ranking changed.
- [ ] Maintain calendar-month traffic from day 1 at 00:00 Europe/Berlin, persist across restart, handle counter reset and prevent counting the same interface twice.
- [ ] Show last reset, monitoring start, lost checkpoint interval and partial month where applicable; do not reconstruct unmeasured traffic.
- [ ] Add a compact service-status panel with time on the left, service, English status/error code and exportable details.

Acceptance: fixture calculations cover time boundaries, restarts, missing data and counter resets; real-device figures reconcile with captured interface counters within documented overhead/observation limits.

## 7. Optional VPN speed tests — priority P2

- [ ] Provide manual Test speed and optional test after a new server becomes connected; default off.
- [ ] Implement routed latency, HTTPS download and upload tests with bounded parallel streams, duration, byte budget and cancellation.
- [ ] Verify test traffic uses the selected VPN, not the current primary route; refuse measurements when isolation cannot be proven.
- [ ] Choose permitted test endpoints or a self-hosted service; do not copy proprietary Ookla code or claim Ookla-equivalent results.
- [ ] Skip/defer under high load, metered constraints or recovery; explain possible bandwidth impact before enabling.
- [ ] Store timestamp, server, measured rates, latency, byte consumption, endpoint and test errors; distinguish throughput from lightweight health probes.

Acceptance: interface-bound traffic and byte budget are verified, cancel cleans up, failures do not alter production routes, rankings label endpoint/method differences.

## 8. Release and acceptance — priority P0 at each release

- [ ] Update the timestamped English work log with exact failure, cause, fix, verification and unresolved limits for every change.
- [ ] Run relevant tests, privacy audit including nested packages, reproducible build and actual UI checks. Retain failed results honestly.
- [ ] Save a local Git commit and push to local Gitea first; publish the identical reviewed tree to GitHub second.
- [ ] Create an explicitly scoped GitHub release with IPK, SHA256, English notes and compatibility passport (full model, firmware, OpenWrt/LuCI versions).
- [ ] Update installation guides, AI installation prompts and public claims only to the extent demonstrated by evidence.
- [ ] Upgrade the router over the previous package while preserving settings/history; verify version, own service, UI, LAN access, DNS/HTTPS and rollback readiness.
- [ ] Run an agreed bounded live test first, then an agreed extended observation. Publish periodic meaningful results only when requested; do not recreate repetitive status automations.
- [ ] Enable unattended production mode only after its recovery and supported transition matrix pass. Document remaining limitations.

Recommended sequence: 1 → 2 → 3 → 4 → 5 → 6 → 7, with phase 8 checks for every deployable increment. Interface and backend releases can be separate so a UI improvement does not require premature production claims.

## Approval checkpoint

The user approved local implementation of the complete plan, then explicitly deferred router uploads and live tests. Continue local implementation, verification and local Git/Gitea. New GitHub publication requires separate permission under the later Git-process task; histories/tags must first be reconciled without overwrite. Hardware acceptance items remain open; approval of coding does not make their evidence complete.

## Local implementation evidence — 2026-10-16

- [x] Telegram wizard exposes interval/daily hour/weekly/monthly settings and loads saved public defaults without returning the token. Mock RPC tests cover validation, exact arguments and cancellation.
- [x] Daily WAN/VPN table distinguishes missing data from measured zero and warns that WAN/VPN must not be added together.
- [x] Current-month Overview cannot substitute a prior month. Histogram accepts aggregated RPC periods and excludes future-day samples.
- [x] Read-only hierarchy prioritizes eligible same-channel servers, then another channel with the same VPN protocol, then another VPN protocol. 256 health/binding/metadata combinations pass; this is not native application proof.
- [ ] Finish mobile layout acceptance; actual x86 VM LuCI desktop, EN -> RU -> EN, eight sidebar tabs and three wizard cancellations passed for alpha5.
- [x] Guarded monitor enable/disable RPC verified with actual OpenWrt procd; does not enable Auto.
- [x] Complete supported recovery settings wizard.
- [x] Explicit recommendation application and bounded operator fault control.
- [ ] Native hierarchy adapters, vendor-worker coordination, IPv6 and reboot/power-loss acceptance on device.

## Verified update — 2026-10-16 09:30 Europe/Berlin

- Alpha5: 202 Python tests pass in Debian and actual isolated OpenWrt (68.269 guest seconds); exact build hash reproduced. Five Node suites passed. Network/firewall exports unchanged; native Auto remains disabled.
- Actual VM UI evidence: qa/openwrt-alpha5-overview-en.png, qa/openwrt-alpha5-overview-ru.png and qa/openwrt-alpha5-navigation.json. System/Telegram/recovery wizards opened and cancelled without writes.
- Committed-reserve observation and stable verified-primary return added locally. Full multi-hop native execution and vendor arbitration remain open.
- Checked items above establish their local/VM implementation scope. They do not close device-specific acceptance conditions. Hardware criteria and unattended production remain unchecked.

## Latest approved offline subset — alpha6 completed

- [x] Full cascade on the pure model: server -> channel -> protocol, exhaustion, root return and per-hop rollback.
- [x] Algorithm protection on the model: delay, stale/unknown/bound evidence, RPC loss, external edits, worker contention, stop and explicit stopped-only restart reconciliation.
- [x] Mobile UI, stable sorting/filtering, verified health colors and EN/RU page coverage: 54 browser cases plus generated-text translation checks.
- [x] System/recovery/Telegram/priority wizard validation contracts, cancellation, review, save failure/retry and single-flight behavior.
- [x] Histogram/accounting boundaries, clock safety, duplicate idempotence, Berlin DST and 200 statistical sequences.
- [x] Nested-package privacy, shared SDK/IPK payloads, reproducible local build, exact-SHA Gitea save tooling, backup/release procedure and continuation documentation.

These checkboxes close the user's explicitly approved offline table, not the physical-device acceptance rows above. Exact results: ../qa/ALPHA6-LOCAL-REPORT.json. Full SDK compilation, hardware/vendor behavior and new GitHub migration remain separately unaccepted or approval-gated.
