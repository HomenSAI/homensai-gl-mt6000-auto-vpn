# Changelog

## 0.5.0-alpha1 — persistent history and client trial workflow

- Expiry/stop no longer blindly returns to a failed source: retain the reserve with explicit partial-result status, await actual client stop verification, and preserve committed state over restart.
- Added bounded, checksummed persistent controller history with previous-good backup, monthly counters and deduplication across restart; no transaction tokens, exit IP or kernel logs persisted there.
- Added typed authenticated native_confirm/native_stop RPCs. ACK no longer requires UCI apply, which could restart the waiting supervisor. Stop is durably latched across restart; a new explicit trial nonce is required to resume.
- Added Windows PowerShell 7 LAN helper: gateway/DNS/IPv6 checks, explicit router DNS and HTTPS verification, strict exit match, no-proxy/no-redirect router login, private password input and stop-on-exit. Wrong gateway refuses before login.
- Added EN/RU trial guidance, helper download, restore request, persistent history/monthly counters and explanatory blocker text. Telegram reports use actual controller state and scoped history rather than unconditional disabled text.
- Fixed history gating before releasing the worker, expiry/stop guard cleanup, late error reporting, and fake PID test syscall mocking. 76 Python tests, Lua 5.1 inventory checks and PowerShell SelfTest pass; four own-process history crash boundaries tested.
- Native switching, HNAT verification and positive LAN acceptance remain unverified on the real device. No outage test before neighbouring tasks confirm checkpoint/pause. See TODO-WORKING-SYSTEM.md.


## 0.4.0-alpha8 — experimental native controller candidate

- Added a real, narrowly scoped existing-rule adapter, independent supervisor, checksummed journal, guarded apply/rollback and mandatory external client confirmation. Defaults disabled; production switching not validated.
- Added explicit, bounded acceleration preparation and strict runtime verification. Device alpha7: shortcut_fe unloaded, HNAT disable remains unverified. No force unload or package removal.
- Fixed own-service upgrade restart, late external changes, orphan child cleanup, trial replay and unconfirmed client timeouts. 52 package/monitor/controller tests and 9 lab tests pass.
- Owner remote-work priority: device stays alpha7/monitor with native disabled; alpha8 is not installed. No live VPN switch/guard/rollback test claimed.
- See docs/NATIVE-EXPERIMENTAL.md and docs/WORKLOG.md for actual results, internal alpha1–alpha7 revisions and limits.


## Licensing revision — 2026-10-15

- Selected MIT with author website in the mandatory copyright notice.
- Added project-specific MIT permission for bundled author-owned Style assets; IBM font licences remain unchanged.
- Added licence files for future package builds. Existing release archives and installed router package were not replaced. Runtime version remains 0.3.0-alpha1.


## 0.3.0-alpha1 — read-only failover planning

- Studied mwan3/OpenWrt 21.02, VPN Guardian rollback and the statically audited GL.iNet worker/route/DNS/conntrack paths; no third-party code copied.
- Added native monitor-backed dry-run plans, explicit source/reserve selection, 3-failure/2-success gates and blocking prerequisites; no apply RPC or VPN write path.
- Added an executable Python transaction contract to the lab: durable intent, independent-watchdog prerequisite, scoped gate, ownership checks, verify/commit/rollback/recover. No native GL.iNet adapter is supplied.
- 36 monitor/package tests and 9 transaction tests passed; 200 synthetic combinations include 60 simulated crash cases. Initial late-gate rollback defect was found and fixed. See docs/FAILOVER-RESEARCH.md.
- No live VPN/network/firewall/DNS mutation; operation mode remains unavailable.


## Documentation revision · 15.10.2026

- Added EN/RU passports of the exact router/firmware/LuCI configuration, read live from the device, plus a redacted JSON snapshot.
- Distinguished LuCI base/UI version from metapackage/module versions, and GL.iNet panel Update Time from an unverified firmware build date.
- Recorded actual installed package 0.2.0-alpha2-1 and running agent 0.2.0-alpha2; linked the evidence from README, installation and validation guides.
- Documentation-only change: application/package version and binary unchanged. No serial, device ID, MAC, network addresses, tokens or private profile names published.


## 0.2.0-alpha2 — HomenS.AI Style

- Repositories renamed to `homensai-gl-mt6000-auto-vpn`, local Gitea first, GitHub second.
- Embedded selected HomenS.AI Style 1.14.3 resources: Nordic tokens, original animated robot, author footer and local IBM Plex fonts with notices.
- Version shown top right, author robot in header, English/Russian UI retained. No private style repository history is copied.
- ipk builder preserves binary font bytes; regression added. 33 unit tests passed, EN/RU visual checks on an isolated synthetic fixture.
- Installed on GL-MT6000: agent version, three healthy active paths, 12 activity profiles and hourly Telegram settings verified. Full live LuCI UI verification remains limited by the browser-session issue.
- Native automatic VPN switching remains unavailable. Live disruption tests need an agreed window and rollback plan; none were performed for this release.


## 0.2.0-alpha1 — public alpha

- English UI by default, English/Russian selector, developer link and version badge.
- Persistent daily activity accounting: healthy/failed/unknown/idle durations, observed connections and distinct failure episodes. Grouped OpenVPN/WireGuard histograms: today, seven calendar days, current calendar month. History starts with this version.
- Bilingual installation guides and copyable ChatGPT/Claude installation prompts; verified author/book links and local-first publication policy.
- 32 unit tests, JavaScript syntax check and English/Russian visual fixture checks passed. Visual fixture uses explicitly synthetic data and omits the real LuCI settings form.
- Monitor mode only; operation/automatic failover remains unavailable. No weekly/monthly device soak or live switch/rollback validation is claimed.
- Versions through alpha9 were installed and measured on the GL-MT6000; this public version has not yet completed device installation/UI validation.


## 0.1.0-alpha9 — prepared; installation unconfirmed

- Version appears top right; agent, Makefile and package versions agree.
- Added initial Telegram setup wizard and separate reconfiguration button. Stored token is never prefilled; an empty reconfiguration field preserves it.
- Latest probe time appears on the left in service monitor; inactive profiles without measurements show a dash.
- Upgrading an already registered RPC plugin avoids rpcd reload/session expiry. Initial installation still registers the plugin.
- JavaScript syntax and 28 unit tests passed. Device design/wizard check remained pending because the browser returned ERR_BLOCKED_BY_CLIENT on LuCI. Last confirmed installed version was alpha8.

## 0.1.0-alpha8 — 15.10.2026

- Added page styling, connected-server cards, four summary metrics, SVG chart of real HTTPS measurements and responsive layout.
- Moved settings into an expandable panel; inactive profiles display neutrally.
- Chart shows the latest available hour without joining gaps over 90 seconds. Values are HTTPS latency, not download speed.
- JavaScript syntax and 28 unit tests passed; package installed. Upgrade expired an RPC session; fix planned for alpha9.

## 0.1.0-alpha7 — 15.10.2026

- Installed and started monitoring on GL-MT6000, GL.iNet 4.11.0 / OpenWrt 21.02.
- Real HTTPS/DNS probes verified three connected profiles: two OpenVPN and one WireGuard; 12 profiles discovered overall.
- Unique VPN-interface traffic accumulates; the current month is partial, beginning with monitoring.
- Added Telegram reporting, enable flag, interval 5–10080 minutes, Chat ID and hidden token field in LuCI. Device delivery was verified with a 60-minute interval.
- Token is excluded from RPC inventory, status, reports and errors; service configuration is mode 0600. It remains in device UCI accessible to administrator and may be included in configuration backups.
- Fixed IPK tar directories, rpcd session argument handling, missing Python time.tzset on OpenWrt and consistency of both LuCI menus.
- Verified 28 local unit tests, actual installation, real measurements and successful device Telegram delivery status.

### Limitations

- Automatic VPN switching disabled. LAN path and IPv6 unverified. Inactive profiles are not started automatically.
- Interface still uses LuCI tables; local-prototype styling and charts had not been ported.
- Telegram sends current state and in-memory changes, not complete archived weekly/monthly downtime statistics. Events may be lost on restart; monthly counters/aggregates use checkpoints.
- First report sends on enable; subsequent reports follow the configured interval after successful delivery, rounded to an observation cycle. Retry after five minutes on error; network loss can delay delivery.
- RPC reload on installation may require LuCI login again. Old-browser 403 remained under investigation; an IP ban was not confirmed.

### Intermediate builds

- alpha2: RPC check after local build.
- alpha3: fixed missing IPK directories.
- alpha4: OpenWrt time compatibility; first successful startup.
- alpha5: Telegram and reporting settings.
- alpha6: versioned UI resource to avoid stale cache.
- alpha7: aligned legacy controller and menu.d.

## 0.5.0-alpha2
Fix native supervisor startup on router Python without time.tzset using libc fallback. Three regression tests. Device acceptance pending.

## 0.5.0-alpha3
Recognise fresh GL-MT6000 HNAT hook readback; stale/inconsistent responses remain unknown.

## 0.5.0-alpha4
Use before/after kernel-ring evidence for HNAT readback rather than comparing different kernel clocks.

## 0.5.0-alpha5
Handle bounded kernel-ring rollover without reusing stale HNAT evidence.

## 0.5.0-alpha6
Accept timezone-qualified Windows deadline precision on router Python 3.9.

## 0.5.0-alpha7
Use checked private nft batch file on firmware lacking /dev/stdin.

## 0.5.0-alpha8
Format nft batch for OpenWrt nftables 0.9.6; retain syntax check before apply.


## 0.5.0-alpha9
Refresh trial nonce in disabled preflight before evaluating an older latched Stop.


## 0.5.0-alpha10
Use semantic identities for anonymous UCI rules; resolve current names on reorder. Add isolated cable probe mode preserving Wi-Fi connectivity.

## 0.5.0-alpha11
Bound retries for transient final client checks; avoid duplicate trial-pass messages. Real alpha10 trial, automatic failure transition and independent rollback confirmed; original helper final error documented separately.

## 0.5.0-alpha12 — English diagnostics and verified-failover prerelease

- Work log, incident causes/fixes, diagnostic catalogue, validation and historical QA reports are maintained in English with original timestamps and evidence boundaries preserved.
- Telegram-generated report text is English by default; operator-supplied profile/channel names remain unchanged. Six formatter/delivery tests passed; live delivery is governed by the existing configured schedule.
- Fixed language-option selected attributes and version badge in the existing dashboard, with a new resource path to avoid stale browser code. The sidebar 0.6 candidate and complete configuration wizards are not part of this release.
- Clear only this application's Python bytecode cache on update: reproducible source mtimes plus equal file sizes had allowed an older imported version to remain cached. System Python and unrelated caches are retained.
- Native engine scope remains two connected catch-all profiles. Real alpha10 automatic transition/independent rollback passed; previous helper errors and production limits remain documented. Do not treat this prerelease as broad unattended-production acceptance.


## 0.5.0-alpha13 — sidebar interface

- Dark HomenSAI left navigation, light workspace, eight sections and live version badge.
- Author robot/site link; persistent English/Russian language selection.
- Sortable tables, server search, healthy-first cards and polling-safe search focus.
- UI-only release: native switching restrictions and existing settings are unchanged. New Auto mode toggle remains a separate pending change.
