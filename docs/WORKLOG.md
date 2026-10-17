# Work log

All times are Europe/Berlin unless an entry explicitly states otherwise. Historical entries describe the evidence available at that time; later entries supersede readiness statements. Missing timestamps are explicitly marked rather than invented. Format: timestamp → error → confirmed cause → change → verification → remaining limits.

## 2026-10-15 · 10:33–11:45 Europe/Berlin

- The owner authorised automatic laboratory tests until 14:00 and requested automatic switching, subsequently allowing acceleration to be disabled if it interfered. Preserving the active remote-work connection then took priority; that later restriction prohibited intentional interruptions during remote work.
- An isolated repeated run of snapshot 386b4b3 was started until 14:00, niceness 15, new seeds each cycle, stopping at the first failure. The laboratory issued no router commands.
- Implemented native_switch.py, internal Lua inventory, a separate procd supervisor, checksummed/fsynced journal, recovery, bounded attempts/deadline, external confirmation and a scoped nft FORWARD guard. Scope: two adjacent catch-all policies using already connected VPN interfaces. This does not constitute complete coordination with all vendor writers.
- Internal 0.4 alpha1 installed the diagnostic adapter; a loaded accelerator module was found insufficient to prove either active or disabled acceleration.
- Internal alpha2 added runtime HNAT inspection and restart of only the own service on upgrades; an unchanged procd command could otherwise retain an older Python process.
- Internal alpha3 added explicit acceleration preparation, preservation of original parameters and bounded retries. Direct RPC commit was denied; set alone did not persist. Standard apply with rollback and confirm succeeded. Public files excluded secrets.
- Internal alpha4 stopped treating a nonzero stop result for an already stopped service as conclusive; runtime state was checked and diagnostic stages added. Three failures terminate preparation.
- Internal alpha5 used normal accelerator-only module removal, without force. Software shortcut_fe was unloaded; packages were retained. The new preparation procedure did not automatically mount debugfs.
- Internal alpha6 rejected unknown hook output as evidence of disabled acceleration. Only normal removal was allowed; the kernel refused removal of a busy module. mtkhnat remained loaded, with no claim of verified hardware disable.
- Internal alpha7 was installed. Limited reads returned an empty hook_toggle body; three active VPNs continued to pass probes. Preparation was stopped, the experiment explicitly disabled and the preparation request removed.
- Internal alpha8 remained a laboratory candidate: fresh kernel responses were inspected when debugfs returned no bytes. Old responses and “going to disable” were not accepted as proof. It was not installed during remote work.
- Fixed late policy changes during exit checks, trial replay after restart, orphaned children after shell failure, missing client ACK and corrupt journals. Tests and limits are documented in NATIVE-EXPERIMENTAL.md.
- 52 native monitor/package/controller tests and 9 laboratory contract tests passed. Intermediate baseline checkpoint: 21 cycles, 105 suite runs, 2,100 new seeds, 945,000 steps, 37,687,012 assertions and 420 own child-process crash cases, zero failures. These are neither router power failures nor tests of the new native adapter.
- External observations ran every 30 seconds until 14:00, with chat checks every five minutes. Scope was router-originated IPv4 HTTPS/DNS. The execution host gateway differed from the GL-MT6000; independent LAN verification had not passed. Automatic Internet recovery was not claimed.
- Local Git first: initial snapshot 0b8d9fe; final fixes/documentation were to be committed separately, followed by an exact GitHub export. Private configuration, device logs, addresses, tokens, passwords and temporary observations were excluded.
- Open at that time: prove HNAT disable, prepare an independent LAN client and trial wizard, test guard/apply/rollback in a separate window, coordinate hotplug/vendor writers, and test actual power/flash failures. The product remained monitor-first.

## 2026-10-15 · 11:46–11:50 Europe/Berlin

- Source snapshot ab28c58 was saved to local Gitea with tag v0.4.0-alpha8. The public tree was verified identical; GitHub commit 45e0ebb and prerelease v0.4.0-alpha8 with IPK/SHA256 were published. Published tags are not moved.
- A second independent isolated soak of ab28c58 started at 11:46 until 14:00, running 52 monitor/package/controller tests, 9 lab tests and separate seeds starting at 200001. The earlier 386b4b3 soak continued separately; scopes and counters were not combined.
- A separate process observed live router status every 30 seconds; secrets stayed in memory and sanitised records outside Git. Five-minute thread checks inspected freshness, both laboratory runs and failure evidence; healthy states were not repeatedly announced.
- Device state at publication: alpha7, native DISABLED, preparation request removed. shortcut_fe was unloaded; hardware disable remained unverified. Candidate alpha8 was not installed because the remote-work connection took priority. Automatic recovery was not considered tested.

## 2026-10-15 · 12:27–13:30 Europe/Berlin · candidate 0.5.0-alpha1

- Created TODO-WORKING-SYSTEM.md with acceptance gates. The owner confirmed a window until 14:00 and required neighbouring tasks to checkpoint/pause before interruption, followed by restoration and notification to resume. Cross-project messages were rejected by automatic approval review; clarification was requested. No pause acknowledgments had arrived, so no outage experiment was started.
- Added persistent checksummed history with a previous-good backup, bounds of 500 events/18 months, deduplication and monthly counters. History excludes transaction tokens, exit IP, passwords/tokens and kernel logs. Restart and four SIGKILL boundaries around atomic replacement were tested only on own child processes, not router power.
- Typed native_confirm/native_stop RPCs avoid UCI apply for ACK, which could restart the waiting controller. ACK requires a fresh matching transaction/exit and successful client DNS/HTTPS. Stop is trial-bound, persisted to flash and survives restart.
- Fixed missing error records, retained guard after normal stop/expiry, releasing a worker too late after a history failure, and missing candidate metadata after Stop. Added cooldown/attempt-limit regressions. Device settings and guard were not changed during this stage.
- Found an old test-harness defect: fake PID 123 could reach real killpg. Candidate soak ab28c58 was stopped after 18 completed cycles and its results retained. All such tests now mock the syscall. No damage to other processes was observed; the container tests did not control the router. Do not rerun the old alpha8 harness without that fix.
- Added a Windows LAN helper with private password entry and gateway/DNS/IPv6 checks. Offline SelfTest passed; CheckOnly correctly refused CLIENT-GATEWAY-MISMATCH on the execution host. That was a negative result, not successful LAN verification. Management/LAN addresses were checked, but a direct LAN path was unverified.
- Checked EN/RU UI on an isolated explicitly synthetic fixture: Stop button, instructions, history and monthly counters. The real LuCI settings form was omitted from that fixture and remained unverified. Mode wording and controls were adjusted using existing Style tokens.
- Telegram formatting now receives native state/history before delivery instead of unconditionally reporting switching disabled. Formatting was tested without live delivery, keeping trial/automatic results separate and excluding private fields.
- Stage checks: 76 Python tests PASS; Lua 5.1 syntax/inventory/credential exclusion PASS in a disposable container without changing the shared environment; PowerShell 7 SelfTest PASS; CheckOnly correctly failed. Positive device apply/rollback was not claimed. Device remained alpha7/monitor/native disabled.
- A later review identified unsafe return to an unhealthy source. finish_committed now restores the original order only after a fresh successful source check; otherwise it retains reserve, reports original_restored=false and does not call unknown connectivity restored. Committed state survives controller restart. Three regressions passed. The helper waits for Stop confirmation and verifies the final path; timeout cannot return success. ACK also checks the private checksummed WAIT-CLIENT journal. Total remained 76 tests PASS.

## 2026-10-15 — 0.5.0-alpha2: router startup compatibility
SSH log confirmed native controller crash: Python on device lacks time.tzset. Added libc fallback matching existing monitor and three regression cases. Before fix only monitor was running; stale native status must not be treated as live. No successful switching trial claimed. Credentials and device identifiers excluded.

## 0.5.0-alpha3 — HNAT diagnostic compatibility
Fresh on-device debugfs read emits exact kernel message value=0, hook is disabled now! Recognise this response only with fresh kernel timestamp and consistent value/state; reject stale or inconsistent messages. Controller startup confirmed after alpha2. Actual switch still not tested.

## 0.5.0-alpha4 — kernel readback freshness
On-device printk and Python monotonic timestamps differ; comparing their values falsely rejects new HNAT responses. Read kernel ring before/after the hook and parse only appended entries. Ring replacement or unavailable baseline remains unknown. No stale response accepted.

## 0.5.0-alpha5 — bounded kernel ring rollover
Device ring is full: new hook records replace oldest entries. Match the unique prior tail record and parse only following new records; absent/ambiguous marker refuses. Three regression methods cover rollover, stale reuse and lost/ambiguous baseline. Actual trial pending.

## 0.5.0-alpha6 — Windows deadline / Python 3.9
Device traceback confirmed Python 3.9 rejects seven fractional digits emitted by Windows DateTimeOffset. Normalise excess fractional digits only when a timezone is present; malformed/missing timezone remains refused. Three regressions. Live switch did not start before this correction.

## 2026-10-15 — chronological real-device preparation and first attempted trial

| Step | Evidence/action | Outcome |
|---|---|---|
| LAN | Windows selected router gateway; router DNS and IPv6 prerequisite checked | Passed; secondary Wi-Fi route observed earlier, not assumed absent |
| SSH | Owner accepted observed host fingerprint; password login succeeded | Diagnostic session works; permanent admin key addition rejected by approval review and NOT applied |
| alpha1 startup | Device log AttributeError: time.tzset absent | Native process crash loop; monitor continued; old native status was stale |
| alpha2 | libc tzset fallback; 79 tests | Installed; both own processes observed running |
| alpha3 | Recognise exact hook readback value=0, hook is disabled now! | Installed; freshness check still rejected response |
| alpha4 | Replace cross-clock comparison with before/after ring comparison | Installed; full ring rollover invalidated simple prefix assumption |
| alpha5 | Unique old-tail marker establishes new records despite rollover; 82 tests | Installed; HNAT hook disabled verified; original driver remains loaded |
| Windows orchestration | Initial credential override scope failed; diagnostic helper prints only exception type/line, no credentials | Corrected in-memory override; no VPN switch at this stage |
| deadline preflight | Python 3.9 rejects seven decimal fraction digits from Windows | Controller ValueError; no switch |
| alpha6 | Normalise timezone-qualified deadline precision; 85 tests | Installed; fresh status had empty blockers |
| outage window | Owner explicitly approved next 10 minutes with possible interruption | Earlier attempts rejected by automatic approval review were NOT executed |
| real trial attempt | Controller reached APPLYING then GUARD-INSTALL-FAILED | Client helper requested Stop; no success claimed |
| state verification | Live policy order/hash equals journal BEFORE; differs from AFTER | No VPN rule reorder verified; client DNS successful and HTTPS 200 |
| guard diagnosis | nft -c -f - reports missing /dev/stdin on device | Root cause identified; fixed-path private temporary batch input required; not yet fixed/tested |
| safe hold | Own native_enabled saved 0 | Automatic mode off; journal closure and guard fix pending |

All observations above distinguish executed checks from planned work. No router power cut, successful automatic failover or verified native rollback is claimed. Source code commits: alpha2 55d7be1, alpha3 a547e64, alpha4 baee33d, alpha5 a19da23, alpha6 08bc611. Each was pushed to local Gitea before an identical source-tree snapshot was pushed to GitHub. No credentials, host fingerprint, exit IP, chat IDs, profile IDs or private router configuration are included in this log.

## 0.5.0-alpha7 — nft batch compatibility
Use private mode-0600 runtime temporary batch file, nft check before apply, and unconditional removal. Avoid missing /dev/stdin without changing device nodes. Regression verifies file permissions, check/apply order, cleanup and no apply on rejected check. Pending live acceptance.

## Detailed incident history — 2026-10-15, Europe/Berlin (UTC+02:00)

Source timestamps are used where available. Reconstructed entries without a timestamp say so explicitly.

### 2026-10-15 16:47:09 — native-controller startup crash (router logread timestamp)

- Error: `AttributeError: module 'time' has no attribute 'tzset'`, native_switch.py line 527. procd reported six crashes; only agent.py daemon was running.
- Cause: router Python does not export time.tzset; the controller called it unconditionally before entering its loop. System Python was not reinstalled.
- Fix, alpha2: configure_timezone uses Python tzset if available, otherwise ctypes.CDLL(None).tzset(), matching the working monitor.
- Verification: three regressions cover native/libc paths and libc failure; 79 tests PASS. Both own processes were observed after installation. Exact installation time was not retained.

### 2026-10-15 — HNAT incorrectly UNKNOWN (exact diagnostic-read time not retained)

- Error: HARDWARE-ACCELERATOR-UNVERIFIED despite driver response `value=0, hook is disabled now!`.
- Cause 1: the parser did not recognise that exact driver format. Alpha3 added strict matching of consistent value/state; stale or contradictory responses remained rejected.
- Cause 2: Python monotonic was 64495.076409609 while the fresh printk response was 64494.965555; different clocks were compared. Alpha4 used kernel-ring snapshots before/after the hook read.
- Cause 3: the ring was full: 123214 bytes before and after, prefix=False. New records replaced oldest records, so alpha4 still returned UNKNOWN.
- Fix, alpha5: find the unique final record of the previous snapshot in the new ring and parse only following records. Missing/ambiguous markers return UNKNOWN without accepting stale evidence.
- Verification: 82 tests PASS. Fresh native-status reported hnat_runtime=disabled after installation. mtkhnat remained loaded; successful driver unload is not claimed.

### 2026-10-15 — Windows deadline parsing failure (exact detection time not retained)

- Error: `ValueError: Invalid isoformat string: '2026-10-15T17:20:32.0404034+02:00'`, deadline function line 76. This string is the requested deadline, not the incident timestamp.
- Cause: Windows DateTimeOffset emits seven fractional digits, rejected by device Python 3.9.
- Fix, alpha6: truncate excess precision to six digits only when a timezone is present; malformed/missing timezone remains refused.
- Verification: three regressions; 85 tests PASS. Fresh device status was DISABLED with blockers=[]; switching had not yet occurred.

### 2026-10-15 17:15:38 — first transaction failure (native-status timestamp)

- Error: GUARD-INSTALL-FAILED, journal APPLYING. The client reported CONTROLLER-STOPPED-OR-BLOCKED and requested Stop.
- Cause: device `nft -c -f -` returned `Could not open file "/dev/stdin": No such file or directory`. nft treated '-' as the missing node rather than the supplied pipe.
- Fix, alpha7: unique runtime batch file through mkstemp, mode 0600; nft check before atomic apply; unconditional removal in finally. Device nodes, vendor firewall and installed packages were not replaced.
- Laboratory verification: 87 tests PASS, covering check/apply order, permissions, cleanup and no apply after failed check. The older atomicity regression was adapted from stdin to a file while preserving FORWARD/IPv6 scope and prohibiting flush ruleset.
- Device checks after failure: order/hash matched BEFORE rather than AFTER; no guard table or child PID remained; client DNS passed and HTTPS returned 200. Auto was disabled.
- Only after these checks, the failed journal was closed as ROLLED-BACK/GUARD-FAILED-BEFORE-REORDER without route application. This proves no change occurred, not successful rollback of an applied switch.
- At this entry alpha7 was built/saved to Gitea; installation, live guard acceptance and automatic switching remained unconfirmed.

### 2026-10-15 17:24:53 — nftables 0.9.6 rejected guard syntax (native-status timestamp)

- Error: GUARD-CHECK-FAILED. `nft -c -f <temp>` returned `syntax error, unexpected end of file` for the one-line table.
- Cause identified during diagnosis: nftables 0.9.6 required table/chain blocks and closing delimiters to be separated by lines in this batch.
- Fix, alpha8: multiline nft batch, retaining check before apply, mode 0600, atomic owned-table replacement and cleanup.
- Planned verification at that point: laboratory tests and device nft -c. Routes had not changed because the guard failed its precheck. Later device guard installation/removal passed.

### 2026-10-15 — earlier Stop blocked repeated preflight (exact last-check time not retained)

- Error: CONTROLLER-STOPPED-OR-BLOCKED with STOPPED/CLIENT-STOP after helper start. VPN order/hash remained BEFORE.
- Cause addressed: the helper generated a new nonce only after preflight; a stored stop record still matched the previous configured trial.
- Fix, alpha9: generate/save a fresh nonce while native_enabled=0 before the first status check. Actual enable remains after successful preflight and explicit TEST.
- Verification at that entry: source inspection confirmed nonce-before-preflight; installation/live recheck remained pending. Later history also distinguished genuine guard failures followed by the helper's Stop from this stale-nonce issue.

### 2026-10-15 17:58:26 — cable Internet restored

- Symptom: the owner reported no Internet through GL-MT6000 after the latest attempt. TP-Link Wi-Fi preserved communication.
- SSH evidence: BLOCKED/EXTERNAL-POLICY-CHANGE-GUARD-RETAINED, journal APPLYING, owned guard present, current order/hash matching neither stored BEFORE nor AFTER, native_enabled=1.
- Confirmed cause: anonymous UCI aliases regenerated after reordering. VPN interfaces appeared under different cfg identifiers, so raw order/hash misclassified the controller's own change as external. The retained guard blocked client forwarding. This was an experimental-controller defect.
- Recovery: private policy/journal backups on device; native_enabled=0 and own service stopped. Primary OpenVPN restored before reserve WireGuard using actual interface identity, followed by vendor apply. Before removing guard, verified Kill Switch, disabled direct WAN, source health and equality of all other semantic policy fields with the pre-recovery snapshot. Removed only the owned nft table.
- Additional recovery error: firmware lacks nohup. The script was launched using subprocess.Popen(start_new_session=True), without replacing system components.
- Laptop confirmation: temporary /32 route to one HTTPS target through cable, source-bound client IPv4; router DNS returned 2 A records, cable HTTPS 200/curl exit 0; separate Wi-Fi HTTPS 200. Temporary route removed; Wi-Fi remained the Windows default path.
- Journal closed RECOVERED-BY-OWNER with a separate recovery hash. This was authorised manual recovery, not successful automatic rollback. Auto remained disabled pending anonymous-identity correction and a new verified trial.

### 2026-10-15 18:04:27 — alpha10: stable UCI identity and isolated cable probes

- Cause: raw .name of an anonymous section changes after UCI commit and is not a stable rule identity.
- Fix: derive anonymous identity from all semantic fields excluding .name/.index; named sections retain their names. Fingerprint checks all values; indistinguishable duplicates are refused. Resolve current UCI names before each reorder and verify stable order/fingerprint after commit.
- Cable helper: CableInterface creates only two temporary /32 HTTPS probe routes through router; DNS explicitly targets router and curl binds the cable IPv4. Wi-Fi default remains unchanged; routes are removed in finally. These are specific IPv4 probes, not verification of all user traffic.
- Checks: alias-regeneration, Kill Switch mutation and duplicate-identity regressions; Windows SelfTest and CableInterface CheckOnly passed. Positive alpha10 device application was pending at this entry.

### 2026-10-15 18:19:19 — Windows NordVPN DNS block

- Error: CLIENT-CHECK-FAILED before trial enable; Win32Exception in Resolve-DnsName. Router-local DNS and the VPN DNS port responded, but normal port-53 replies did not reach Windows.
- Confirmed cause: active WFP filter “NordVPN DNS Leak Protection — DNS block”, ALE_AUTH_RECV_ACCEPT_V4, BLOCK, remote port 53. After authorised service stop, LAN lookup immediately returned 2 A records.
- Action: the owner explicitly authorised temporary stop of nordvpn-service and restoration after testing. StopPending took time, then the trial continued. The finally block restarted it; Running was confirmed.

### 2026-10-15 18:21:20–18:22:03 — real alpha10 transition and return

- 18:21:20.447: APPLYING; actual reorder of the two connected catch-all VPN rules.
- 18:21:41.437: WAIT-CLIENT; client confirmed DNS and two IPv4 HTTPS probes through reserve with the expected exit.
- 18:22:03.164: ARMED/TRIAL-PASSED after original-path restoration. Helper confirmed original exit. Stable order/hash matched after commit despite regenerated anonymous aliases.
- Result: the first real transition and return passed. Wi-Fi default was preserved. Scope remains two already connected profiles, not arbitrary topologies.

### 2026-10-15 18:23:37–18:27:31 — automatic failover under controlled failure

- 18:23:37.651: separate temporary fault table blocked output/forwarded traffic only through primary VPN interface; the interface remained connected. An independent timer process ensured fault removal; vendor Kill Switch remained enabled.
- Monitor recorded VPN-003 on primary; reserve remained healthy and Wi-Fi HTTPS returned 200.
- 18:24:53.798: automatic APPLYING after failure streak/cooldown; approximately 76.15 seconds from fault-start to apply-start.
- 18:25:15.093: WAIT-CLIENT; 18:25:20.085: COMMITTED/CLIENT-CONFIRMED, approximately 102.43 seconds from fault-start. This is time to confirmation, not continuously measured application downtime.
- 18:26:07.807: independent timer removed fault; primary health was verified again.
- 18:27:26.002: independent controller completed ROLLED-BACK/TRIAL-ENDED; 18:27:31.821: STOPPED/CLIENT-STOP, guard removed.
- Helper completion error: CLIENT-CHECK-FAILED; the exact exception type for this attempt was not retained. Successful helper exit is NOT claimed. NordVPN was restored in finally.
- Separate final client check: router DNS returned 2 records; cable HTTPS passed and cable exit matched private baseline; stable UCI order/hash equalled BEFORE and guard was absent; Wi-Fi HTTPS 200. Network transition/rollback are therefore verified independently of the helper completion error.
- Alpha11 added bounded retries in the final 90-second window for network/DNS/HTTPS failures only; route/exit mismatch cannot become success. Duplicate TRIAL-PASSED output was removed. This improves resilience but does not prove the cause of the previous unspecified exception.


### 2026-10-15 19:21:12 Europe/Berlin — English documentation/reporting and alpha12 release preparation

- Request: publish diagnostic history, causes, fixes and error statistics in English, with English first-entry UI default. Optional Russian UI/installation guides remain separate; user-supplied names are preserved.
- Change: translated current work log, diagnostic catalogue, changelog, historical QA reports, validation, state, checklist and English guides. Historical timestamps and unverified outcomes were retained, not retroactively marked successful.
- Report formatter now generates English labels; six formatter/delivery tests passed without changing destination, token or reporting interval.
- Dashboard language selection no longer passes false as a selected attribute. The version badge reads agent version; dashboard16 is a cache-busting resource for the existing interface. Sidebar dashboard15/ui13 remains a local unshipped candidate.
- Additional packaging issue: after alpha11 installation, source declared alpha11 but imported agent.VERSION returned alpha10. Own bytecode cache contained files validated against reproducible unchanged mtime/size. Removing only five own .pyc files made a fresh import return alpha11. Alpha12 postinst clears only the application's own non-symlink .pyc files before restarting its service; no system Python/package replacement.
- Publication planned as an explicitly experimental prerelease with IPK/SHA256 and English notes. Source code and package must match, local Gitea first, identical GitHub tree second. Installation/asset verification is recorded only after it occurs.

### 2026-10-15 19:25:44 Europe/Berlin — alpha12 device-verification record before publication

- Package SHA256 was verified before opkg installation: 54df73497163ce7996ff8beab0904cf9ea53744b9839a706ed8f7ec2ee0f3372, 424895 bytes.
- Fresh device import reports 0.5.0-alpha12. Default empty-status Telegram report begins “HomenSAI Auto VPN · monitoring” and contains no Cyrillic. User-supplied names remain outside this language assertion.
- Device configuration native_enabled=0, journal ROLLED-BACK, owned guard absent. Client HTTPS returned 200. Existing private configuration was preserved by opkg.
- 90 Python tests, JavaScript syntax and reproducible rebuild passed. Publication privacy audit passed for 176 tracked files including nested IPK archives. Actual LuCI wizard/full sidebar acceptance is not claimed for this release.


### 2026-10-15 20:02 Europe/Berlin — sidebar UI release candidate

- Request: complete the dark left navigation and light workspace. Scope is UI only; pending auto-toggle code/RPC is preserved separately and excluded from this package.
- Added eight hash-addressed sections, live version badge, author robot/site link, EN/RU selection with URL/storage persistence, sortable tables and search. Confirmed navigation and language switching in the isolated synthetic fixture; fixture numbers are not router measurements.
- Search focus/caret is retained during polling; healthy cards precede failed cards, with confirmed failures marked red. Configured routing priorities are not changed by visual sorting.
- Build preparation errors: default container user could not rewrite root-owned files; root Git required a per-command safe.directory. Recovered the original backend directly from HEAD before editing the version. Moving pending files to /tmp initially failed with cross-device rename; used a copy-and-remove move and excluded the pending JS as well. No router changes during these preparation failures.
- Tests: 90 Python tests pass; dashboard18 JavaScript syntax passes. Initial build destination router/dist was unwritable; explicit releases destination builds successfully. Final package: 435022 bytes, SHA256 654887a23c77118c337997b91d76ada6e31d703311287cbaa52565e2389a5e8b.
- Device baseline: alpha12 installed, monitoring running, native_enabled=0. Installation and actual LuCI acceptance are still pending at this entry.


### 2026-10-15 20:12 Europe/Berlin — actual LuCI acceptance and final sidebar package

- Installed alpha13 over alpha12; opkg preserved the modified configuration and placed defaults in the -opkg file. Own monitor is running; native_enabled remains 0 and controller reports STOPPED. Three connected-profile probes were healthy.
- Actual LuCI navigation to all eight sections passed. English-to-Russian selection translated menu, headings and configuration labels. Diagnostic descriptions remain English; vendor LuCI controls may retain vendor language.
- Device-only UI defect: LuCI E() rendered an optional null child as literal text in Settings. Filtered null children before passing them to E(). Browser retained the earlier dashboard18 resource, so the final route uses dashboard19 for cache invalidation. Reinstalled only the application's candidate package, preserving its configuration. One intermediate own-service delete returned Not found; final service-running verification passed.
- Final package SHA256: e2812dd5ed3fdea29dacf8acfbbb9d4ff355005c18397bee6ca07d751daa6069; 448761 bytes. Earlier candidate hashes above are historical, not the final asset.
- Local Gitea push initially failed host-key verification because the container had no known-hosts file. Read the public ED25519 host key directly from local-gitea and used that verified key with StrictHostKeyChecking=yes; push then succeeded. No SSH verification bypass.
- Windows HTTPS check initially failed against sandbox proxy 127.0.0.1:9. Direct authorized HTTPS check outside that restricted proxy returned 200; this was an execution-environment proxy failure, not evidence of router Internet loss.
- This release does not add the pending Auto mode toggle, production unattended mode or new switching algorithms.


### 2026-10-15 20:16 Europe/Berlin — legacy theme header collision

- Actual-device screenshot showed that the vendor theme's generic header rule painted the application header black, making the title unreadable. Scoped background/position/size/shadow resets to .hv-app .hv-page-header and set an explicit select height.
- Final UI resource is dashboard20; CSS has a release-specific cache key. Rebuilt candidate alpha13 before creating its immutable release tag. Previous package hashes in this log refer to superseded acceptance candidates.
- Final asset: 463399 bytes; SHA256 e5f4407a491f6417967c8800b73281198d6ac4d137548fb0807b6c6e4531ac5f.


### 2026-10-15 20:18–20:43 Europe/Berlin — approved completion plan, control and setup increment

- User approved the entire completion plan. Current baseline: alpha13, monitoring running, native_enabled=0, journal ROLLED-BACK, HNAT hook disabled although the module remains loaded.
- Current client observation: Ethernet disconnected; Wi-Fi uses GL-MT6000 directly. This is not the earlier independent TP-Link Wi-Fi plus cable topology. Deliberate outages are deferred pending an independent management/client path; code and non-disruptive verification continue.
- Found unsafe partial-enable ordering in the unshipped button candidate: UCI enabled was committed before deleting Stop. Replaced it with a single atomic RAM intent, serialized Start/Stop, no native_enabled write, no new nonce/deadline and no deletion of the durable Stop latch. A newer Stop wins; stale/future/mismatched intents cannot enable a trial. UI starts do not survive reboot.
- Added real-state power control and primary/reserve protocol/channel/server diagram. Green requires fresh certified OBSERVING or client-confirmed COMMITTED. Unknown/stale states cannot display On. Original-policy handover is shown only with explicit controller verification; held reserves are distinguished.
- Helper defect: cable mode used the globally preferred route for its locality check. With two adapters on one subnet, that may select Wi-Fi despite a valid cable-specific path. Checks now constrain both InterfaceIndex and LocalIPAddress and report CLIENT-CABLE-LINK-DOWN separately. This corrects a reproducible logic defect but does not prove the historical failure's exact cause.
- Inspected vendor apply coordination: /usr/bin/rtp2.sh uses a lock-file wait then replacement, not a shared atomic flock contract. Full writer mutual exclusion remains unverified; it is not claimed solved by the application's private lock.
- Added three-step system/Telegram wizards with review/cancel/back, whitelisted own-config RPC, existing-profile metadata, private token entry, channel username/numeric destination and deliberate delivery test. Active transactions refuse configuration writes. Tokens travel only in authenticated request/stdin and existing private device config, not logs/status.
- UI checks found ambiguous accessible labels in wrapped select fields; explicit aria-label fixed automated selection and improves assistive access. Synthetic fixture verified system steps 1–3, Back/Cancel, Telegram review, RU entry and a refused Start without false green. These are not real device save/send results.
- 112 Python tests and 10 UI state invariants passed; PowerShell helper SelfTest passed. Reproducible candidate 0.6.0-alpha1: 491109 bytes, SHA256 4e77068512167256485fd1a9afd1fb7c6e9525ec24b36443e6dc33e55f651e32. Device installation/acceptance follows separately.


### 2026-10-15 20:47 Europe/Berlin — device RPC signature correction

- Alpha1 installed over alpha13, preserving private configuration; own service running and native mode not enabled.
- Actual ubus introspection exposed incorrect method signatures: exec-plugin list values such as "Integer"/"Boolean"/"Array" were themselves JSON strings, so interval, session_loss and servers were advertised as String. The plugin derives types from JSON values, as confirmed by OpenWrt rpcd/plugin.c rpc_plugin_parse_signature. Existing Python validators remained strict; this was an interface-schema defect, not authorization to bypass them.
- Changed list signatures to representative native JSON values (0, false, [] and strings), including native_confirm booleans. Added a signature-contract regression test. Package postinst reloads rpcd when the actual servers:Array schema is absent, rather than only checking method presence.
- Built separate alpha2 instead of rewriting an installed candidate: 113 Python tests and 10 UI state invariants pass; deterministic package 491756 bytes, SHA256 0e699996b473fe352ea53e167d6f8c7f0fa6ef75ab3468cb180f13aa4d65db4f. Actual setup save and live Start refusal are next acceptance checks.
- Reference: https://github.com/openwrt/rpcd/blob/master/plugin.c (signature uses blobmsg_type of each JSON value).


### 2026-10-15 20:52–20:56 Europe/Berlin — first-run wizard empty-array defect

- Alpha2 introspection now correctly advertises Integer, Boolean and Array. Actual Overview Start returned AUTO-START-REFUSED / BOUNDED-DEADLINE-REQUIRED for the expired window; indicator stayed Off and no new intent or route change was requested.
- Actual System setup click failed with TypeError custom.filter is not a function. Root cause: Lua cjson encoded the empty own server mapping as {}, while browser code expected an array. Normalized profiles/servers/native_candidates before filtering in Python inventory and defensively normalized wizard input in JS. Reject nonempty object profile arrays instead of iterating them.
- Added two first-run schema regressions and moved the actual power control before the overview diagnostics, keeping it visible near the top.
- Alpha3: 115 Python tests plus 10 UI state invariants passed; JS syntax passed; deterministic package 509466 bytes, SHA256 2ece9c506a518613cee46ffebd49fa8c4cd8213d2ddea036c860096a395e4337. Device save/acceptance remains pending until this corrected build is installed.


### 2026-10-15 20:59–21:07 Europe/Berlin — raw UCI writer compatibility

- Real system wizard review passed, but save failed. A bounded watcher verified config unchanged, token unchanged, primary/reserve unchanged, policy unchanged and native_enabled=0. Failed saves were not labelled successful.
- Sanitized Lua diagnostics identified writer line 20. Installed require('uci').cursor() exposes set/add but section=nil; section() belongs to a higher-level convenience API. Replaced named-section creation with the supported three-argument raw c:set(config, section, type).
- Exercised the corrected writer using the actual device Lua/libuci in a synthetic isolated /tmp config/delta directory. Named server creation and commit passed; production application config remained byte-identical. No token was copied into this test namespace.
- Added authenticated setup_check using that isolated installed-writer test before enabling the system wizard. A failed/unavailable check blocks saving. Async preflight respects Cancel and cannot reopen a cancelled wizard.
- Reference: https://github.com/openwrt/uci/blob/master/lua/uci.c, uci_lua_set three-argument section-type form.
- Alpha4 retains bounded experimental native operation. 115 Python tests, 10 UI state invariants and JS syntax checks passed; actual system save is rechecked after installing the corrected writer.


### 2026-10-15 21:12–21:18 Europe/Berlin — application ACL coverage defect

- Installed writer self-test passed through root ubus, but browser wizard preflight still failed. A fresh LuCI login alone did not resolve it. Actual installed ACL inspection showed only scan/native_confirm/native_stop/native_start; setup_system/setup_telegram/telegram_test/setup_check were absent.
- Root cause: an earlier string replacement assumed native_stop was the last ACL entry; native_start had already been appended, so the replacement silently made no change. Replaced text-based edits with structured JSON assignment of the explicit own-method allowlist.
- Added a regression requiring registered RPC methods to equal read/write ACL coverage, read scope limited to inventory/status/events, write scope limited to the application's ubus object, and no wildcard grants. Reload rpcd after package upgrade to load the new ACL; users with existing sessions may need to sign out/in.
- Alpha5: 116 Python tests plus 10 UI state invariants pass. Deterministic package 546598 bytes, SHA256 ea1ae9eca7f89eddd0d7bdc023080e5e4495912ee38b271934cf52967f273058. This fixes application RPC authorization; it is not proof of the historical browser HTTP 403 cause.

### 2026-10-16 06:08 Europe/Berlin — local v0.7 candidate verification

- Scope: local development only, as requested. No router connection, deployment, VPN changes or live fault injection in this run. Installed router version is not changed by this checkpoint.
- Added opt-in bound-interface speed measurements, conservative persistent payload quotas, owned-worker cancellation and timeout checks. Disabled by default; local tests do not demonstrate real server throughput.
- Added daily WAN/VPN accounting with explicit observation gaps and retention indicators. Found a missing WAN sampling hook after a text transformation; initialized the device list, restored the sampling call and added a one-loop integration regression.
- Added calendar Telegram scheduling and a checksummed delivery ledger. Unknown delivery outcomes remain unknown rather than being silently retried. Fixed local 07:00 calculation to use calendar time rather than midnight plus elapsed seconds; tests cover daylight-saving transitions and missing measurements. Telegram transport is mocked in these tests.
- Added monotonic transaction deadlines so wall-clock adjustments cannot extend the permitted experiment. Device validation remains pending.
- During development, a Windows default-encoding write produced an invalid Python source byte; the syntax check detected it. Rewrote affected sources as UTF-8 with LF line endings. No affected source was deployed.
- Verification: 158 Python tests passed. Interface rendering, complete wizard integration, hierarchical failover, operator fault control and hardware acceptance are still pending. This is a development checkpoint, not a production release.


### 2026-10-16 06:08–06:15 Europe/Berlin — local TODO completion increment

- Telegram calendar settings existed in the backend but the wizard sent only four arguments. Added schedule/hour/weekly/monthly fields, exact eight-argument RPC submission, saved non-secret defaults, review and validation. Stored token remains blank. Mock UI test verifies invalid hour rejection and cancellation without writes.
- Overview selected the lexicographically latest stored month, which could display a previous month's total as current. Changed lookup to the explicit current Europe/Berlin month; missing current-month observations remain absent.
- RPC retention can replace activity days with period aggregates; the histogram ignored those aggregates and displayed zero bars. Added period support and excluded future calendar dates. Added daily WAN/VPN rows with missing-versus-zero semantics, gap counts and retention warning; counters overlap and are not summed.
- Added a read-only hierarchy recommender with fresh two-success HTTPS/DNS admission and operator metadata priorities. Excluded unbound/disabled/unsupported profiles. Tested 256 combinations of failure, interface binding and metadata. Exposed recommendations in monitor status; no native executor behavior is changed by these recommendations.
- Local tests: 161 Python tests passed, plus 12 Auto UI invariants and separate wizard/traffic UI checks. Reproducible package tests passed. These use local fixtures/mocks; no router or Telegram delivery test occurred.
- The first privacy scan in the previous checkpoint ran as root and Git refused repository ownership. Retried as the repository user; privacy scan passed. No global safe.directory exception was added.
- Remaining: browser visual/language acceptance, fresh-install lifecycle, priority application, bounded operator fault feature and hardware-only acceptance. Updated completion plan baseline to remove stale alpha13/uncommitted candidate claims.


### 2026-10-16 06:17–06:55 Europe/Berlin — real OpenWrt virtual lab and alpha2 hardening

- Created an isolated Docker container running QEMU 7.2.22/TCG with the SHA256-verified official OpenWrt 21.02.7 x86 image. Guest kernel 5.4.238 and Python 3.9.16 booted; dependencies/IPK installed. No physical router, Windows interface, VPN route or user Telegram destination was changed.
- First SSH forwarding failed because QEMU's management user subnet did not match the guest's static LAN. Corrected only QEMU management networking; internal SSH then worked. Initial package update was slower than anticipated but ultimately passed signature checks and dependency configuration.
- Immediate RPC checks returned Not found. A hypothesized missing rpcd-mod-exec was disproved: that package does not exist here; exec plugins are built into rpcd. The object appeared after asynchronous startup. Acceptance now waits for actual readiness; no bogus dependency was added.
- First guest regression reported ten errors from absent time.tzset(), including a skipped test class. Reused libc timezone refresh through timezone_compat and added native/fallback regressions. A repeated stale run came from docker cp nesting router inside router-source; corrected to copy contents and exclude nested/pycache data. Subsequent full guest runs passed 165 and then 168 tests.
- Real UCI/RPC/procd acceptance passed 14 checks, including fixture metadata save, native Auto refusal, speed disabled, invalid Telegram token refusal without sending, monitor start/stop, actual process/fresh data and unchanged network/firewall/main IPv4 route. alpha1 → alpha2 kept the own-config marker.
- Long serial command exceeded BusyBox interactive line capacity and truncated the completion marker. The guest test succeeded but the helper timed out. Confirmed the saved JSON separately; changed helper to short safely quoted chunks. A first base64 helper failed because this BusyBox lacks base64; removed that dependency.
- Own monitor SIGKILL test confirmed exact argv before signalling. procd replaced it and fresh status resumed; 23.45 seconds were measured on the guest clock, not user Internet downtime. Native Auto stayed off and configuration/routes stayed equal.
- Warm reboot did not return management within 180 host seconds. QMP screen remained at Linux decompression before application start; root cause is unconfirmed. Preserved-disk cold startup retained the marker and restored the application. An alternate direct-kernel mode is being checked separately; retain the initial failure rather than declaring reboot accepted.
- Added monitor_control, writing only own enabled flag and starting/stopping only own init script. No route commands. Active/on-intent/retained-reserve/closed-guard/unknown journal states block shutdown; corrupt journals return MONITOR-JOURNAL-UNVERIFIED without invoking writer or service. UI says requested rather than claiming running.
- Browser fixture verified EN→RU→reload→EN and Telegram calendar fields. Overview at 390px had no horizontal overflow (document width 375). Found missing power glyph and replaced with CSS icon. These browser observations use synthetic data and omitted LuCI forms, not device UI acceptance.
- IPK contained retired dashboard/CSS files, including local untracked generated versions. Restricted current packaged UI to dashboard25/ui13; history remains in Git. Found Python 3.9/3.11 gzip OS-byte difference; normalized all nested gzip headers. Independent guest/host package hashes then matched before final journal hardening.
- Current local suite: 169 Python tests plus Auto/wizard/traffic Node checks PASS. Final candidate is 414714 bytes, SHA256 976a44f3f4dfab0cb75083b39de0257c71424b19a6a439e6230f1e5f31e6e789. See qa/OPENWRT-VIRTUAL-REPORT.md for scope and remaining failures. No production or full native hierarchy acceptance is claimed.


### 2026-10-16 06:55 Europe/Berlin — warm-reboot result retained

- Alternate checksum-verified direct-kernel mode also failed to return SSH within the 180-second host-clock deadline; QMP showed running but the screen remained at kernel decompression. This occurs before application initialization. The root cause is not established and is not labelled an application defect or a fixed emulator bug.
- Preserved both failed/unconfirmed JSON results. Restored only the private QEMU guest by a cold process restart with the same disk; started final package/regression verification. No third warm-reboot trial or physical-router restart.


### 2026-10-16 06:57 Europe/Berlin — final guest/host candidate parity

- Final cold-started guest completed all 169 Python tests after the monitor-journal hardening; Debian completed the same count. Both built the same 414714-byte package with SHA256 976a44f3f4dfab0cb75083b39de0257c71424b19a6a439e6230f1e5f31e6e789.
- Guest force-reinstall was restricted to this application's disposable VM package. opkg retained the modified own configuration and wrote the package default as an -opkg alternate; marker comparison passed. Early Command failed: Not found messages are retained as startup/readiness observations, not ignored as universal harmless errors; actual RPC/procd acceptance was verified separately.
- No physical deployment. Public guidance remains monitor-only. Updated installation/AI instructions and diagnostic codes for Start/Stop monitor, calendar scheduling and virtual-test limitations.

### 2026-10-16 07:03 Europe/Berlin — publication and final virtual health

- Final VM health: version 0.7.0-alpha2, own monitor running with fresh measurements, synthetic metadata retained, native Auto/speed/Telegram disabled. No physical-router query or deployment.
- Saved local/Gitea source commit fbdb0b9, then identical GitHub source commit d50f91f; compared tree 816a46404132e9dbdd73a33c355c93b93d3c36e6 before publication. Local release tag v0.7.0-alpha2 points to that source snapshot.
- Published GitHub prerelease v0.7.0-alpha2 with explicitly monitor-only guidance and unresolved VM warm-reboot limitations. GitHub asset metadata confirms 414714-byte IPK and SHA256 976a44f3f4dfab0cb75083b39de0257c71424b19a6a439e6230f1e5f31e6e789, matching the tested file. Privacy scan covered 246 tracked files including nested packages and passed.
- Historical untracked old IPKs/dashboard15/dashboard17 were preserved, not published or deleted; the current builder excludes retired dashboards from the IPK. Native GL.iNet/hardware acceptance remains open.

### 2026-10-16 07:30 Europe/Berlin — raised router-style Auto power button

- Requested visual change: match the GL.iNet round power control with a raised surface. Replaced the flat look with a 110px bevelled face, layered halo rings, inset highlights and contact shadow using the pinned style palette. Added hover lift, pressed recess and Start/Stop action caption; CSS icon has no font dependency.
- Retained confirmed-state logic and existing native_start/native_stop calls. Green requires fresh confirmed Auto state; pending amber, failure red, off/unknown neutral. No optimistic green on click. Keyboard focus and reduced-motion behavior are included.
- Local candidate version 0.7.0-alpha3; no physical-router connection, deployment or VPN operation. Preview is explicitly synthetic.
- Verification: JS syntax PASS; 12 Auto state invariants PASS; three package/reproducibility tests PASS. Browser checked on/off/pending/error styles; Overview at 390px has document width 375px and no horizontal overflow. Screenshot retained outside Git.

### 2026-10-16 07:30–08:09 Europe/Berlin — priorities, recovery, fault controls and real LuCI findings

- Added reviewed own-priority application with a SHA256 revision of profile/metadata state. Changed reviews, disabled/unknown/duplicate profiles and active/uncertain recovery refuse saving. Existing names/groups/enabled flags remain intact; no route application occurs.
- Added bounded recovery settings, monitoring preferences and explicit wizards. Controller thresholds/cooldown use saved values; return requires fresh HTTPS/DNS observations spanning the configured stable interval plus a fresh bound probe. Hold-reserve is explicit. Matching certification includes recovery settings.
- Relaxed only structural catchall validation from exactly two to 2–16 contiguous unrestricted rules with unique interfaces, leaving special policies ahead and Kill Switch/IPv6/offload/vendor guards intact. This does not complete automatic hierarchy or inactive-profile activation.
- Implemented an operator IPv4 traffic fault with a private nonce, separate watchdog and nft ifname-set timeout. Native prerequisites, observing certification, fresh source/reserve health and window bounds are checked before installation; INPUT and management routing are untouched. Cancellation and Auto Stop clean only the owned table. Fault history is independently bounded/checksummed.
- VM nftables 0.9.6 rejected the first script: `devices` is reserved; the remaining syntax errors were cascading parser errors. Renamed set/chain objects and used explicit block layout. Actual loopback kernel test then passed: drop observed, traffic resumed after set expiry without a watchdog, table removed, firewall configuration unchanged (9.2 guest seconds). No physical-device fault test.
- Opened actual VM LuCI through a loopback-only proxy/SSH tunnel; no cookie/body/session logging. Recovery wizard displayed and saved defaults; root readback showed original enabled flag/source and both fixture profiles preserved.
- Found that legacy raw UCI form could bypass the new configuration guard. Removed that form and app UCI ACL grants, replacing remaining controls with bounded own RPC preferences. Stored-token fields are no longer loaded by our page.
- Found an inventory load failure after VM-page reload: UI fell back to empty/default configuration while actual UCI was intact. LuCI RPC default numeric error handling contributed to this false state. Added reject:true, object-shape validation, bounded read-only retry and explicit RPC-INVENTORY-UNAVAILABLE; setup/start cannot save those fallback defaults. Stale transitions keep Stop available.
- Verification: 194 Python tests PASS plus inventory/recovery/setup/traffic/Auto Node suites. Final current artifact: 425313 bytes, SHA256 e8a285924cccd69374422d6fdce7ea9f41bf343842ee10a4a2985c9096ee16c7. Final browser revision, hierarchy cascade and hardware-only criteria remain open; see qa/ALPHA4-CHECKPOINT.md.
- Publication preference confirmed: each completed change goes to local Git/Gitea first, identical GitHub tree second and a new versioned release; existing tags/assets are immutable. Development snapshots remain prereleases and state their unverified scope.

### 2026-10-16 08:40–09:11 Europe/Berlin — Git workflow, VM fixture and reserve observation

- Git workflow is now integrated into primary main at 9b86926bfda7d28429ed1b292603c38a9be47a78. Feature/main SHA identity was verified directly in Gitea. Twenty workflow regression tests and the existing prototype checks passed during guarded integration. A verified post-change bundle was copied to independent restricted storage. GitHub publication is currently withheld under the later explicit instruction; earlier immediate-publication wording above is superseded.
- First commit failed with exit 128 because the task branch reflog was root-owned. Corrected exactly that branch ref/reflog ownership. First clean-main integration then found the helper absent on old main; added reviewed external configuration bootstrap. Root-owned copied test directories also prevented unlink during checkout; corrected task-owned directories, preserved the newline-equivalent leftover in private Git state, then integrated without forced updates or data deletion.
- VM validation initially failed three fixture checks because the transfer contained Python modules but omitted build_ipk.py and package ACL assets. Corrected the transfer to include all router source. Subsequent run hit the 240-second host timeout under container memory pressure. Measured QEMU RSS about 934 MiB within a 1 GiB cap; cgroup memory max events exceeded 154000, without an OOM kill. Raised only the disposable container cap to 2 GiB, leaving guest RAM at 256 MiB. Bounded future TCG translation cache to 128 MiB; installed QEMU accepted that flag in an empty paused machine. Performance after a fresh boot with the cache cap remains unverified.
- VM report collection incorrectly treated absent optional native_enabled as a failed read, although absence defaults to disabled. Corrected verification handling without writing guest settings. Another report write failed because the lab artifact directory was not writable to the runner; reran the bounded lab check with the proper container user. These reporting failures are not VPN failure evidence.
- Found an actual controller logic gap: after client-confirmed failover, the COMMITTED loop only repeated its status. Added reserve failure observation and verified-primary return after configured dwell/stability. Failure samples require a fresh negative reserve check before reporting degradation. Unknown live health is explicit. Returning still passes finish_committed's policy identity and fresh primary recovery checks. Operator hold-reserve never forces return.
- Added DEGRADED-ON-RESERVE with explicit reason, retained Stop even with stale status, and configuration blocking. This adds recovery observation only; full multi-hop hierarchy, inactive-profile activation and vendor-worker arbitration remain unfinished. No new production readiness claim.
- Full non-root Python run initially failed two monitor fixtures with missing capabilities/events. Exception tracing identified PermissionError from auto_control's default runtime paths; fixed the fixtures to isolate both runtime/persistence paths, retaining assertions. Then 201 Python tests passed. All five Node suites passed, including 15 Auto UI invariants.
- A Windows authoring attempt failed cp1251 decoding of localized UI. Repeated with explicit UTF-8; no partial UI edit was made by the failed attempt. Dashboard generation then exposed root ownership of its existing output; corrected that exact file owner and regenerated successfully.
- Physical router, Windows routes, actual VPN sessions and Telegram credentials were not changed. The recovery correction is an unreleased local candidate; published alpha4 package/tag stays unchanged.

### 2026-10-16 09:12–09:27 Europe/Berlin — final VM package and actual browser acceptance

- Final immutable alpha4 IPK installed in the isolated x86 guest and passed 194 tests in 66.163 guest seconds. Rebuilt hash matched e8a285924cccd69374422d6fdce7ea9f41bf343842ee10a4a2985c9096ee16c7; network/firewall exports unchanged, native_enabled absent/disabled. Receipt: qa/openwrt-vm-alpha4-final.json.
- Browser showed uci/get permission denied and remained on Loading view. Installed-file inspection confirmed no raw form/uci.load and reliable inventory present. Root account scope still had wildcard ACL selection; no credentials or session IDs were logged. Used new dashboard26 module URL and refreshed login in the isolated VM. Alpha5 then rendered successfully without adding UCI ACL grants. Cache/session cause is not isolated to one component.
- Added distinct alpha5 package/agent/SDK versions and new UI module address; found SDK Makefile still declared 0.5.0-alpha1. Aligned it with 0.7.0-alpha5 and added version/menu/package source checks. Old published alpha4 assets/tags remain untouched. All 202 local Python tests passed with reproducible candidate hash a14d1c6bae2be64eb398fa8873b2cabb53589d988655ce93cb93982fbb34cd6a.
- Actual browser accepted English -> Russian -> English; eight sidebar tabs changed to the expected headings. System, Telegram and recovery wizards opened and cancelled; no settings save or Telegram transmission. Blank token input verified. Screenshots and navigation evidence are from the isolated VM with inactive synthetic profiles.
- First alpha5 installation runner lacked its renamed test archive; transfer failed before installation. Supplied the complete archive and repeated. New output creation initially failed due to root-owned asset directory; corrected ownership of the exact generated-assets directory and regenerated. No user file deletion or broad permission change.

### 2026-10-16 09:30–09:45 Europe/Berlin — alpha5 final evidence, VM pause and handoff

- Actual alpha5 OpenWrt suite passed 202 tests in 68.269 guest seconds. Rebuild reproduced a14d1c6bae2be64eb398fa8873b2cabb53589d988655ce93cb93982fbb34cd6a; network/firewall unchanged and native Auto disabled. Detailed receipt saved separately from alpha4.
- A fresh QEMU process with tb-size=128 cold-booted the preserved disk; measured container memory about 295.4 MiB, versus approximately 1013 MiB before mitigation. Warm reboot again failed its 180-second readiness window. Cache mitigation is not recorded as a warm-reboot fix.
- User requested stopping virtual tests. Stopped the remaining cold-restoration runner, then QMP stop/query-status confirmed paused=true and running=false. Disk/RAM retained; final cold-restoration acceptance remains unconfirmed. No physical-router changes.
- The first staging command was not executed because automatic permission review timed out. The permitted single retry succeeded; nested publication audit then passed for 276 indexed files including the new alpha5 IPK. This was an approval-review timeout, not a Git or secret-detection failure.
- Git archive privacy was strengthened on its own branch: inspect staged nested TAR/IPK/ZIP before commit, bounded sizes/depth/counts, reject unsafe paths and encrypted members. 23 disposable-repository tests passed; primary Gitea checkpoint 40dabd0f851fd413dfe3301876c2a7af76591ea7. No GitHub upload.
- Prepared VS Code handoff documents with implemented/unimplemented scope, purpose, evidence, branches and continuation prompt. Offline test launcher uses a read-only current-checkout mount and no external network. PowerShell parser acceptance only; the new Windows bind-mount run is not claimed completed.

### 2026-10-16 10:09:31 Europe/Berlin — offline cascade model

- User authorized the complete offline completion matrix while physical device access and QEMU resume remain excluded. Created feature/local-completion-alpha6 in the approved Windows checkout.
- The Windows read-only bind-mount launcher actually passed 202 Python tests, five Node suites and the indexed publication audit. This closes its former syntax-only limitation without using the router VM.
- Added pure CascadeModel with immutable root-order intent, server/channel/protocol ranking, per-hop confirmation/rollback, original-root return, bound/fresh health, unknown-state refusal, RPC/external-policy/worker blocking, cooldown, attempt/window limits and checksummed restart refusal. It executes no commands and grants no native route permission.
- Sixteen focused tests passed, including 256 seeded eight-step failure/concurrency series. Full local suite subsequently passed 219 tests after the initial UI/wizard validation changes. Hardware adaptation remains separate.

### 2026-10-16T10:44:09+02:00 — local alpha6 completion and exact verification

- Added a tested pure multi-hop cascade and original-root/per-hop rollback distinction. Twenty focused model tests cover freshness, unbound/unknown probes, deadlines, RPC loss, worker contention, external predicted-order changes, stop, corrupt journal, retry budgets and stopped-only operator reconciliation. Reproducible 256-series report: 2048 steps, 493 synthetic commits, 195 hop rollbacks, zero invariant failures. No Linux command execution exists in the model.
- Windows primary push refused an unknown [127.0.0.1]:2223 host key before upload. Preserved strict checking; relayed the exact local commit bundle through the already verified Docker SSH transport. Model commit dab55d401765681a69a81edb510b75964214ac44 was confirmed in Gitea. Added a repeatable clean-branch/exact-SHA relay script without credentials, force updates or GitHub writes.
- Found statistical clock-regression baselines could move backwards and recount already observed intervals/bytes. Activity now keeps its forward baseline; traffic discards an invalid baseline and records a gap. Duplicate samples are idempotent. Seven boundary/property tests include month/year/leap-day rollover, Berlin 23/25-hour DST days, restart gaps and 200 sixty-step synthetic sequences.
- Connected-without-proof could display OK/green, and card ordering ignored confirmed selection. Added bound DNS/HTTPS/freshness state labels; selected healthy first, failures last, unknown/checking explicit. Operator priorities remain separate. Stable table identity preserves sort/filter through polling; browser fault/refresh controls verified both behaviors.
- System setup formerly allowed disabling or omitting its selected reserve. Backend and wizard now reject that review. Control-character names are refused; cancellation during a pending save cannot masquerade as rollback. Node coverage verifies readiness cancellation, ranges, disabled reserve, review-before-save, RPC failure/retry and single-flight writes.
- Actual generated UI tested on a labelled synthetic fixture: nine pages x EN/RU x 360/768/1280 = 54 checks, no page-wide horizontal overflow. Mobile modal/fields fit. English visible-text audit found no remaining Cyrillic labels on nine pages; static generated-code test covers 55 Russian literals and language persistence. Diagnostics intentionally remain English. Fixture RPC data is not router measurement evidence.
- SDK Makefile had copied all historical UI assets while custom IPK filtered them. Both now consume selected_files bytes/modes, with staging refusing nonempty trees. Two tests compare every actual IPK member with SDK staging, including modes. Host Python 3 required; a complete external SDK build is not claimed.
- Local test launcher shell sequencing could have hidden an earlier failure behind the final privacy command. Changed to set -eu and verified injected exit 17 propagates to PowerShell. All current offline checks pass: 232 application Python tests, 5 QA tests and 8 Node UI suites. Broader unchanged prototype/demo baseline: 30+4 Python, 33 model tests, 4096 boolean cases, 12 regressions and 5 soak/capacity tests (50000 ticks).
- Publication scan now inspects bounded nested TAR/IPK/ZIP without filesystem extraction, rejects traversal/encryption/invalid archives and never prints matched secret contents. Preview isolation tests reject POST, private paths and symlink escapes. Restarted only the loopback synthetic preview to apply its guard.
- Alpha6 uses dashboard27/ui14 and separate immutable release assets; restored retired dashboard26/ui13 source to their prior contents. Physical router untouched, QEMU remains paused, new GitHub publication still withheld. Full native adaptation remains subject to CASCADE-ADAPTER-CONTRACT.md and a future authorized device window.

### 2026-10-16 11:30:30 Europe/Berlin — verified primary publication and independent backup

- Exact source checkpoint c0616113362e430ab8abd638b3e80bddcb717950 and immutable annotated tag v0.7.0-alpha6 were saved/verified in primary Gitea by scripts/save-gitea.ps1. The script ran end-to-end successfully. Host tracking/default push now selects Gitea; GitHub ordinary push remains disabled. Working tree was clean.
- Published a local Gitea prerelease with the existing tag, English scope/limits and two attachments: IPK and SHA256. Release page resolved tag to c061611336. Uploaded IPK hash was independently checked on Gitea storage and matched 0cb57faa967f3cfc42caebb48be0f2bd9f31081eeb959692be6acf941ca1d85a. Browser upload took unusually long; publication was verified only after both attachments appeared and the release page showed them. No GitHub publication.
- Created an independent all-ref Git bundle and an official post-release Gitea dump including database/configuration/repositories/attachments in restricted D: storage. Existing snapshots were preserved. Git bundle verification passed.
- The first ZIP verification started before asynchronous docker cp completed and read a partial file, returning BadZipFile. Waited for copy completion, then CRC verification passed; this was a sequencing error, not a corrupt final backup.
- SQL dump contained 2213 statement separators and no explicit transaction. Initial isolated restore was slow; a separate fresh private destination restored the trusted dump within one explicit transaction. Both restores ultimately passed integrity_check=ok. The enhanced check additionally confirmed this repository, alpha6 release, two release attachments and the exact attached IPK hash. Live Gitea and its database were not modified by verification. Online dump is not claimed globally atomic across other agents' writes.
- Saved sanitized publication/backup proof in qa/. Actual backup ZIP/SQL, configuration and private database remain outside Git. Final Git-only audit documents this verification without moving the published tag or changing the installed application package. QEMU remained paused, its browser polling tab was closed, and physical-router settings were untouched.


## 2026-10-16 11:47:50 +02:00 — Complete next-stage backlog recorded

Request: preserve the entire next-stage list, including additional features, for VS Code continuation. Added docs/TODO-NEXT-STAGE.md with 24 unchecked tasks, priorities, dependencies and explicit acceptance criteria. Linked it from START-HERE.md and the handoff TODO. NEXT-16 through NEXT-20 cover the additional diagram, transition timeline, recovery analysis, CSV export and installation/AI guides. Existing alpha6 completion evidence remains unchanged. This change records planned work only: no VM resume, router changes, runtime changes or public publication. Validation: unique NEXT-01 through NEXT-24 identifiers, exactly 24 unchecked tasks, relative-link checks and git diff --check.


## 2026-10-16 12:00:56 +02:00 — Per-edge executor and inactive candidate contracts

Implemented isolated cascade_executor and candidate_runtime; see NEXT-STAGE-RESULTS.md for exact scope. Initial focused test failed with five CASCADE-CLOCK-REGRESSION errors: the repeated metadata fixture reused time 1 after time 2. Corrected the fixture to advance time; retained the runtime refusal. Review found recovery checked generation/order without all metadata or phase constraints; added hash/revision checks and PREPARED/WAIT-CONFIRM/COMMITTED/STOPPED order rules, plus regression tests. Added actual simulated process death before/after journal phase writes, lease contention, fresh bound proof, replay, corrupt journal, wrong-interface/exit witness and owned candidate cleanup tests. Full network-disabled Linux Docker run: 260 application tests, 5 QA tests and 8 UI suites PASS. No VM resume, host routing or physical-router changes. NEXT-02/03/04/07 complete only in their explicit offline/test-double scope; the remaining list stays open. Sandbox-only Docker inventory query was denied access to the engine; no router or service failure is inferred.


## 2026-10-16 12:54:23 +02:00 — Cascade path, recovery analysis and CSV (alpha7 development)

Added protocol/channel/server diagram with fresh-controller selection, hierarchy-ranked healthy suggestions and explicit uncertified edges. Added sequence-gap-aware retained-event transition analysis; day/week/month boundaries use Europe/Berlin including DST. Statistics expose sample denominators, unknown/pending outcomes, trial/automatic attempt counts, median/P95/worst phase recovery and consecutive failures grouped by server/channel/protocol. Four CSV exports whitelist columns, quote UTF-8 data and protect formula prefixes; real browser download of the synthetic transition export was verified. Browser matrix: EN/RU x overview/events x 360/1280px, eight cases, no document overflow. QA initially reused a cached alpha6 fixture JS; added explicit stub build query, verified alpha7 and populated marked synthetic transitions. Current asset names dashboard28/ui15 preserve dashboard27/ui14. Full tests passed 260 application + 5 QA + 9 UI suites before the final display/formula-prefix refinements; focused UI/privacy checks repeat below. NEXT-16/18/19 complete for retained-event scope; NEXT-17 remains partial because absent probe/client history cannot be reconstructed. No VM/router changes, no GitHub publication. Browser download verification completed after an unexpectedly long tool wait; no production traffic was tested.


## 2026-10-16 14:13:07 +02:00 — Runtime, migrations, witness, bounded evidence and CI checkpoint

Executed Python 3.9.15 from the official pinned image and Lua 5.1.5/CJSON 2.1.0 contracts with mocked UCI. Initial runtime image build failed exit 100: optional Git dependencies referenced Bullseye Security package URLs returning 404. Removed unnecessary Git from this image; Lua/CJSON installed normally, with signature checking unchanged. Subsequent full application run passed 281 tests before the final private-UCI conversion additions. Private migrations preserve names, priorities, statistics, synthetic secrets and existing section identities; deleted profiles stay disabled and Auto is cleared. Windows helper SelfTest passed source-bound DNS parsing and three sequential freshness/replay/interface/exit/DNS/HTTPS proof contracts, without networking. Native history now keeps safe sequential attempt/retry IDs, whitelisted streak evidence, phase timestamps and the original Refused cause code. Review found rich history could exceed the 512 KiB read bound; added a 400 KiB detail budget preserving aggregate counters and exposing truncation. New regression confirms phase logging failure does not prevent the existing restoration operation. Resource run: 2000 synthetic transitions, 256 retained write records, 17,196 KiB host process peak RSS, under 1,879 journal bytes; see hashes/limits in alpha7-load-report.json, not router benchmarks. Read-only Git plan found 9 tag collisions and preserved mappings; no history writes/public push. EN/RU installation and AI guides now describe actual boundaries. SDK matching vendor 4.11.0/mt7986 was not verified in checked official sources; NEXT-10 remains blocked. Isolated immutable CI launcher prepared; automatic Gitea runner is not activated. User's instruction to execute the entire TODO opens a new isolated virtual-copy phase after the code checkpoint; the old paused guest and physical router remain preserved. Exact immutable CI results follow in a later entry, not assumed here.


## 2026-10-16 15:27:47 +02:00 — Isolated cold/warm boot and package lifecycle corrections

Verified source QMP paused/running=false; copied raw disk and matching official kernel into private .git/handoff seed, and matched source/copy SHA256. Source disk 674ae659ebd245062d1a2abab50564a2cdccc01c781a17919973fd7b86c76120; kernel 4c5a50fe3de95b297308c27cf66a858be98fb14d9d85e8f302fa0f6d302fcfdd. New clone has network=none, no published ports/host mounts/devices/privileged mode, dropped capabilities, 768 MiB and 1 CPU limits. Cold recovery observed OpenWrt 21.02.7 r16847-f8282da11e x86/64, Linux 5.4.238, Python 3.9.16, installed alpha5 monitor active, native DISABLED, Telegram false. Initial probe exit 1 came from an absent optional native_enabled option, not a boot failure; its default is off. /tmp lab marker was correctly absent after boot and was recreated only after exact x86/version validation. Original source remains paused. Direct-kernel warm test passed in 83.788 host seconds: boot changed, configuration hash unchanged, monitor/fresh status confirmed and auto=off. This does not fix the old GRUB failure or certify hardware power loss.

Review of upgrade path found monitor Stop wrongly treated a historical on intent as current even after matching Stop/controller acknowledgement. Added shared lifecycle assessment requiring matching trial/time/verified stopped state and no active journal/closed guard. Package hooks now refuse active/unverified transactions, clear only own Auto scope on safe upgrade and propagate stop failures with set -eu; generated SDK/custom hook source is shared. Initial test run failed ModuleNotFoundError package_hooks because dynamic builder loading lacked the router import path; fixed explicit source directory import. Review found the new guard initially assumed /tmp instead of the real agent.RUNTIME /var/run path; corrected it and added a behavioral path regression. Updated full Python 3.9/Lua run: 294 tests PASS; installation on the clone is still pending. Synthetic lifecycle failure messages in those unit tests are expected mocked outcomes, not device operations. Immutable CI receipt for earlier b705aae passed separately and remains attributed to that exact source; these new lifecycle changes require a fresh committed-source CI.


## 2026-10-16 15:37:44 +02:00 — Immutable CI rejected a temporary executable test stub

Commit f5f83f9 CI failed PackageLifecycleTests: expected simulated stop exit 7, observed 126. The rootless hardened CI tmpfs has noexec, so the directly invoked temporary shell stub was refused. Corrected only the test harness to invoke both stubs through sh. Kept network=none/read-only root/dropped capabilities/noexec restrictions. No successful receipt was issued for the failed commit and no new package was installed in the clone. A new commit and CI repeat are required.


## 2026-10-16 16:51:02 +02:00 — Real package upgrade/rollback and opkg return-code discrepancy

Immutable CI for 15ab381 passed both runtimes with matching artifact a96aa7f785a78457fec48fadbcfda0c8e40074d72da787846e1b1f8f09e1cea4. On the isolated x86 copy, Alpha5→Alpha7 upgrade succeeded and the installed agent produced fresh Alpha7 status. The first acceptance script then failed because it assumed rejected prerm must make opkg return nonzero. Real opkg returned 0 while reporting LIFECYCLE-STOP-AUTO-FIRST, failed prerm and No packages removed. A dedicated probe confirmed agent bytes/inode/mtime were all unchanged. Do not use force-remove; no guard was bypassed. Corrected the acceptance harness to use guard output plus file postconditions and restore only the synthetic native_enabled flag in finally. Actual rollback to the verified Alpha5 checkpoint completed; its legacy postinst emitted Command failed: Not found, so no unqualified legacy-hook success is claimed. A repeated Alpha5→Alpha7 run then passed 13 real UCI/opkg/procd checks: private synthetic field, marker/name/priority/history retained, Auto scope off, guarded fault refused, code metadata unchanged, network/firewall/main route fingerprints preserved. Conffile mismatch kept the existing config and placed package defaults in an -opkg file. No physical router touched.

Kernel capability probe: namespace create/delete succeeded; TUN/WireGuard/OpenVPN/openssl/conntrack tools were absent. Official OpenWrt 21.02.7 x86 feed fetch initially could not resolve libc because it is provided by the installed base image, not that index. Added installed-image satisfaction and Provides resolution; 31 package files (2,442,353 bytes) passed official index SHA256 checks. Kernel ABI 5.4.238-1-5a722da41bc36de95a7195be6fce1b45 matches this x86 image. Guest signature verification/install is the next step; no physical feeds or unsigned-force options changed.

## 2026-10-16T17:26:04.3633100+02:00 — UCI pending-delta defect and user-requested pause
- Observed: isolated OpenWrt/libuci setup request reported OK while also committing a previous unrequested interval=99 delta. Reproducer: qa/alpha7-delta-probe.json.
- Cause: commit includes shared saved deltas. Prepared correction: refuse pending own-config deltas and propagate explicit refusal codes; do not discard operator changes. Draft only; no fix/retest success claimed.
- Evidence retained: 13 package acceptance checks, 11 UCI/procd checks, signed protocol-tool installation. Actual tunnel matrix not started; alpha7 reboot still unverified.
- User requested stop: both QEMU states verified paused/running=false; unverified drafts saved outside package inputs; NEXT-11/15 reopened. No physical router changes or public release. Resume gate: validate fix, immutable CI, package/VM acceptance before live failover.


## 2026-10-16T17:29:19.5245328+02:00 — Consolidate project workspace
- Cause: historical VPN staging/build/diagnostic files remained under an unrelated previous private output folder. Initial hash scan refused a locked vpn-vm-proxy-errors.log; no files had been moved.
- Correction: verified and stopped two own legacy openwrt_proxy.py processes and own port-18880 preview. Moved VPN output directories/artifacts to ignored private/workspace-transfer-2026-10-16 in canonical project; verified 6401 SHA256 hashes before/after. No existing source overwritten; unrelated documents retained.
- Status: pause retained. No test, physical deployment or public release started. Archived scripts contain historical paths and are not active entry points.


## 2026-10-16T17:30:12.3333358+02:00 — Preserve remaining historical VPN trees
- Found old non-Git gl-mt6000-alta-vpn source copy plus vpn-audit-2026-10-11 in workspace root. Moved both to ignored project-private archive, preserving directory structure/hidden files and verifying 1099 SHA256 hashes. Canonical source unchanged; no tests resumed.


## 2026-10-16T17:37:27.7433181+02:00 — Implement pending-UCI-delta refusal (validation pending)
- Observed defect: unrelated saved delta interval=99 was committed by setup_complete request. Correction: writer checks savedir pending own-config delta before writes/revert; fixed SETUP-PENDING-DELTA/SETUP-DELTA-UNVERIFIED codes propagate through setup/priority/monitor. Lifecycle refuses pending own-config changes before reset/commit.
- Added regressions for absent/empty/nonempty/unknown delta, caller code redaction and no service action after refusal. Package revision alpha7-2 preserves alpha7-1 identity.
- Development error: initial edit used Windows cp1251 default and failed reading Unicode tests. Repeated remaining edits with PYTHONUTF8=1; no source encoding conversion intended. Tests not yet claimed passed.
- Only isolated marked QEMU copy resumed; original VM paused, physical device untouched.


## 2026-10-16T17:38:27.1235058+02:00 — CI revision assertion corrected
- Exact-source CI 45e5232 failed: test_package expected builder version to always end in -1, while candidate correctly increments PKG_RELEASE to 2. 301 tests executed; one failure, seven Lua tests skipped in control runtime. No PASS receipt issued.
- Correction: assert builder version against agent version plus actual validated positive Makefile PKG_RELEASE; retain cross-file version alignment check. Full matrix rerun required.


## 2026-10-16T17:43:24.2026364+02:00 — Verified UCI correction and isolated package acceptance
- Immutable CI source 7c1a6f3: Python 3.9.15/Lua executes 301 application tests with zero skips; Python 3.11.2 control executes 301 with seven Lua skips; nine QA checks in each runtime; nine UI suites. Both reproducible artifacts match SHA256 9f8e952873dd236bbb6470bfffcbcb4e0daeb7501335f6ab2472cab6e19725ac, 452968 bytes, alpha7-2.
- Actual isolated OpenWrt: 15 pending-delta/upgrade checks PASS; old unrequested interval remains uncommitted, pending bytes preserved, clean retry saves only after explicit fixture discard. Lifecycle and opkg guard refuse pending writes; acceptance uses postconditions rather than opkg exit alone.
- Repeated readonly-save/commit plus own-monitor crash/respawn matrix: 11 PASS. Downgrade to alpha7-1 and reupgrade alpha7-2: 13 PASS, exact hashes/config/history/name/priority retained, Auto off, network/firewall/main route unchanged. Old revision used only as a rollback fixture, not recommended for deployment.
- Alpha7-2 warm reboot test started in isolated direct-kernel VM; outcome pending. Original guest and physical router unchanged.


## 2026-10-16T17:46:34.8839610+02:00 — Alpha7-2 warm reboot passed; stop at hardware gate
- Isolated direct-kernel OpenWrt reboot PASS: 82.6 host seconds, new boot, unchanged config, own monitor autostart/fresh samples, Auto off. Not a physical power cut or original GRUB repair.
- UCI pending-delta finding closed for reproduced interrupted-save scenario. Both virtual guests verified paused at completion. No physical router access, deployment, VPN/route/firewall changes, new public release or GitHub write.
- Remaining: full native protocol network matrix, vendor/LAN/DNS/Kill Switch/IPv6/offload acceptance, broader interruption matrix, verified SDK and restricted Gitea runner. Current state and precise next-step gate saved in docs/handoff/STATUS.md.


## 2026-10-16T18:53:54.0327526+02:00 — Physical read-only baseline and private backup
- Access: saved host key verified; SSH/source-bound Ethernet management succeeded. Fixed invalid local ubus command syntax and overly broad authentication-error classification; no router write used.
- Hardware remains installed/running 0.6.0-alpha5-1 / 0.6.0-alpha5, own services running, Auto off. Three of twelve active profiles pass recent router DNS/HTTPS. PROFILE-INACTIVE blocks stored source; journal ROLLED-BACK does not override original_restored=false.
- Backup streamed to Windows: 10,194,609 bytes, 1,413 members; archive parsed, nine critical config hashes match live, protected baseline unchanged. Contains private /etc and own code/LuCI/init/opkg metadata; excluded from Git, ACL restricted. No firmware image or live restore claim.
- HNAT runtime disabled; Ethernet DNS PASS; bound HTTPS Windows 10051 means client Internet unverified. Wi-Fi shares router gateway and is not independent recovery Internet.
- Local documentation attempt failed before execution due PowerShell double-quoted here-string interpreting a Markdown backtick-u. Rewrote documentation with literal here-strings; no partial router action occurred.
- Prepared gated trial/rollback/abort plan; no installation, Auto enable, route/VPN/firewall/service/Windows changes or outage injection.


## 2026-10-16T19:14:13.5975777+02:00 — Cable error corrected and active primary selected
- 2026-10-16T19:07:28.5038439+02:00 (pre-change snapshot): Ethernet IgnoreDefaultRoutes Enabled caused interface-bound Find-NetRoute network-unreachable and HTTPS Windows 10051. Changed only IgnoreDefaultRoutes Disabled in ActiveStore. Ethernet metrics 500 retained; normal default remains Wi-Fi interface 15. No route, DNS, weak-host, adapter or NordVPN action.
- 2026-10-16T19:08:36.7962487+02:00 (pre-change snapshot): selected inactive source. Under own lock and Auto-off/journal/pending/fresh-profile/generic-Kill-Switch checks, changed only plan_source to active generic OpenVPN; WireGuard reserve retained. Used private temporary UCI savedir; no VPN restart or policy reorder.
- Post-write exact export-text assertion returned UNEXPECTED-CONFIG-DIFF. Did not repeat mutation. Complete section/option semantic comparison confirmed exactly main.plan_source changed, Auto zero, other own settings unchanged; eight protected configs match original backup.
- 2026-10-16T19:11:29.0676280+02:00: source/interface-bound DNS and two TLS/HTTPS checks PASS (~375 ms each); same client exit matches selected primary. Native blockers empty/selection accepted; pending UCI empty; Auto not started.
- Local documentation command initially failed parsing a colon immediately after a PowerShell variable reference. Rewrote with literal placeholders; this was local documentation only, not a router failure or duplicate write.
- Hardware package remains 0.6.0-alpha5-1. Wi-Fi preferred but shares router gateway; independent recovery Internet still requires agreement before outage. See ROUTER-TEST-PREPARATION-2026-10-16.md and qa/router-preparation-2026-10-16.json.

## 2026-10-16T19:35:21.6658632+02:00 — Physical work deferred; isolated protocol lab development
- Owner requests at least two hours of local-only work and keeps physical Internet available. No physical package upload/install, restart, Auto enablement or switch occurred. Fresh pre-upgrade private backup was completed before deferral (10,249,353 bytes, 1,413 members), but hardware remains 0.6.0-alpha5-1. Later disruptive work starts only on owner's command.
- Resumed only the marked x86 QEMU copy; original guest remains paused. Container network none; synthetic network namespaces have no host/LAN bridge or real VPN credentials.
- Added four real local tunnels (two WireGuard, two static-key UDP OpenVPN) with generated TLS/DNS endpoints. Standalone lab selector is not the application's GL.iNet adapter; transport findings cannot certify production native cascade.
- Development failures: initial Python quote typo caught by py_compile; corrected before effective setup. Initial smoke failed OPENVPN-TUN-NOT-READY because --local conflicts with --nobind. Changed client to distinct local ports and persist-tun/persist-key; cleanup removed all owned namespaces/processes and root baseline remained unchanged.
- Second smoke: four real bound DNS/TLS endpoints PASS, then nft guard refused because OpenWrt nft -f - resolves missing /dev/stdin. Corrected to private owned staged file, nft syntax precheck/apply, finally unlink. Product fault_control already uses files; this was a new lab-harness error, not a router fix.
- Windows nested -c quoting also failed in status helper; replaced with a tracked Python host script to preserve exact code. Four offline DNS/scope/private-nft-file contracts passed. Failed smoke evidence preserved in qa/protocol-smoke1-failed.json and qa/protocol-smoke2-failed.json.
- Further smoke/soak acceptance pending. Reports distinguish guest event clock from host collection UTC and do not claim two completed hours before terminal evidence.

## 2026-10-16T19:45:22.8155293+02:00 — Owner requested current UI package on physical router
- Latest explicit instruction authorises installation for UI inspection while failover remains deferred. Installed exact previously verified alpha7-2 package, SHA256 9f8e952873dd236bbb6470bfffcbcb4e0daeb7501335f6ab2472cab6e19725ac; upload hash matched, opkg exit zero, independent package query confirms 0.7.0-alpha7-2 and fresh agent 0.7.0-alpha7.
- Fresh pre-upgrade backup retained privately. Eight critical network/VPN configs plus route/rule fingerprint unchanged. Own sections/names/other settings preserved; lifecycle cleared only native_until/native_trial, kept native_enabled zero. Three active profiles passed fresh router DNS/HTTPS, Auto off. No trial/switch was launched.
- Package hooks restarted only the own service, reloaded rpcd registration and invalidated LuCI index cache; no network/firewall/VPN restart. Existing browser tab held an old rendered view and an expired session; reloaded and authenticated through normal LuCI login. Visible live sidebar, raised START button, path diagram and v0.7.0-alpha7 badge verified.
- Visible UI finding to fix locally: cleared native_until='0' renders a misleading 01/01/2000 deadline. No false trial started; schedule display is a presentation issue. Record and test correction offline before any further deployment.
- Virtual protocol smoke4 failed a bounded helper-process timeout before initial checks; its owned namespaces/processes cleaned, root protected baseline unchanged. Captured qa/protocol-smoke4-result.json. Continue local diagnosis, not production error injection.

## 2026-10-16T19:54:50.5595466+02:00 — Offline UI deadline regression and conntrack lab preparation
- Installed UI language switch EN -> RU visibly translated own sidebar/headings/controls; switched back to EN. No Auto click or settings save. Physical installed package remains alpha7-2.
- Reproduced display defect: Date.parse('0') converts cleared native_until into 2000-01-01. Added display-only parser for positive numeric or explicitly timezone-qualified ISO deadlines; zero/empty/invalid become an em dash. Added regressions for sentinel/invalid/ISO/numeric/runtime values; focused Node tests PASS.
- Generated cache-distinct dashboard29 and local package revision alpha7-3; this local candidate is not installed or declared released. Full exact-source CI pending.
- Virtual smoke5: 15 transport/DNS/leak/return checks PASS, conntrack observation FAIL. No production conntrack was touched. New namespace did not explicitly activate conntrack expressions; added a separate non-dropping ct-state counter chain, pending real retest. Namespace cleanup and root protected baseline confirmed.
- Previous nft failures were independently reproduced: chain name out is reserved, and a chain closing brace needs a statement separator in this nft version. Safe lab_output plus separator passed nft -c before new smoke6. Helper-process timeout stage tracing added; network timeouts unchanged, subprocess bootstrap budget increased. Root/cleanup status fields now derive from checked postconditions, not unconditional booleans.

## 2026-10-16T20:13:41.4999989+02:00 — Real-transport smoke passed; immutable two-hour soak started
- Smoke6 terminal PASS: 22 checks, zero failed assertions; generated tunnel/DNS/TLS endpoints, same-protocol and cross-protocol routing, return, DNS refusal, direct-underlay leak blocking and scoped conntrack checks. Cleanup confirmed; protected root routes/config unchanged. Source and terminal evidence retained in qa/protocol-smoke6-result.json.
- Conntrack fix confirmed on the actual guest: explicitly register a non-dropping ct-state chain inside only the synthetic client namespace; after that TCP tuples appeared and targeted deletion left UDP control entries intact. No global flush or physical conntrack operation.
- Started 7,200-second run at 2026-10-16T17:59:19.359054Z, immutable source SHA256 ec5721dfcb7129c859c60c039ade52ec5a056d7294862c5f155720a5472b3a0f, marked clone only. Every 25 cycles repeats the validated failure/return series. Start receipt is not terminal proof. At latest intermediate capture 92 checks PASS, state RUNNING; no two-hour completion claimed.
- Initial starter template substituted ROOT inside an assertion label, causing generated-code syntax failure before launch. Replaced unique placeholder tokens and compile generated code before execution; successful start receipt independently confirmed PID/source/duration.
- Added cumulative evidence collector: deduplicates overlap, counts actual selected/standby proofs, reports retained-event gaps instead of inventing history. First startup remains within the producer's 200-event retained window. Parser/retention/reset/type and periodic-fault scheduling contracts passed locally. Collector is separate from immutable producer; no live algorithm patching.
- New local-only preview server binds 127.0.0.1, serves only fixture/public UI assets, blocks private/.git/traversal and restricts connect-src to self. It is synthetic, not a router proxy. Local cleared-window view shows em dash correctly; app candidate alpha7-3 exact-source CI PASS at ac2c0c0, physical package remains alpha7-2. Continue UI/wizard QA and virtual data collection.

## 2026-10-16T21:08:44.6057749+02:00 — Continued offline stress tests and wizard acknowledgement fixes
- Previous immutable 7,200-second protocol soak ended FAIL after 3,834.31 seconds / 212 cycles: 583 assertions passed, then HELPER-PROCESS-DEADLINE:BOOTSTRAP. Collector reports zero missing events and cleanup confirmed. This is NOT a completed two-hour PASS; real router was not accessed.
- Diagnosis limitation: old timeout trace saved only ip/netns/exec/namespace, omitting the actual helper. No probe-stage stderr was observed; BOOTSTRAP was an unsupported default label, not an established cause. Current post-failure guest memory/load do not prove conditions at failure. Preserve failed report; improve executable-prefix, timeout and load evidence; classify missing stage UNCLASSIFIED without increasing timeouts or retrying away failures.
- Fixed setup wizard navigation while RPC is pending: Back/Cancel/Save disabled, aria-busy and translated saving indicator; duplicate saves blocked. Require actual boolean saved/passed acknowledgements. Failure retains the draft and shows fixed error codes without private exception text. Review now includes edited aliases, channel, priority, monitoring and reconnect consent.
- Auto START/STOP now requires typed accepted/queued acknowledgements; unknown responses cannot claim success. Focused Node regressions PASS. Offline protocol/evidence tests: 12 PASS including observed-stage preservation and honest unclassified timeout reporting.
- Browser evidence: 36 page/language/viewport cases (EN/RU, 360/1280, nine sections) passed without document overflow. EN pending save/failure/cancel verified; RU mobile review and 64-character aliases fit without overflow. These use a synthetic local fixture, not physical configuration writes.
- IPv6 helper's prior failure came from missing /proc/PID/task/PID/children on this OpenWrt kernel. Replaced discovery with bounded numeric /proc stat parent-PID matching and explicit root/source/PID arguments. Actual positive-control retest remains pending. Do not claim physical IPv6 acceptance.
- Local candidate package revision 4 generated; installed physical router remains alpha7-2 with Auto OFF. No physical settings or routes changed during this work. Exact-source full CI and diagnostic repeat pending.

## 2026-10-16T21:12:24.2295647+02:00 — Visible route to the router VPN configuration
- Added persistent Configure VPN / Настроить VPN link in the page header on every section. Opens the router GL.iNet VPN Dashboard in a separate tab; uses current scheme/hostname and intentionally omits LuCI port 8080. No profile credentials or URL tokens are included.
- Overview explains that servers/keys/credentials are configured in VPN Client Profile; our application selects monitoring/groups/priorities. English label and destination visibly verified in local fixture; translation suite PASS. Physical router not updated by this change.
- Previous local candidate alpha7-4 exact-source CI PASS at 6873a5d830b8dc0cad8e13594c1625b2c69a727d, package SHA256 72ec37530b99e6f017f24053d2d418248dffb93127000d7addfbd475da37eba8. This link change is alpha7-5, pending separate exact-source CI.

## 2026-10-16T21:14:57.3583850+02:00 — VPN configuration control moved left
- Owner requested raised Configure VPN control above Connected VPN server. Removed small right-header link; added left-aligned circular gear link sharing the Auto power button depth/hover/focus style. Gear identifies configuration; it does not call start/stop RPC.
- Card appears on Overview and Channels. English/Russian labels and explanatory text retained; link opens GL.iNet VPN Dashboard in another tab. New cache-distinct dashboard32/ui16; candidate revision 6 remains local.
- First generator edit did not match an escaped replacement literal, so the Channels control was absent during browser QA. Corrected exact generated-source replacement and visibly rechecked: gear button left, Connected VPN server heading beneath, existing server cards below. No physical router deployment.


## 2026-10-16T21:18:06.4421142+02:00 — Animated evidence-based primary/reserve status diagram
- Added red failed, green healthy, pale-yellow checking and grey neutral cards with explicit state captions. Auto OFF, stale RPC/controller data and unacknowledged requests render neutral; no fabricated failure for a recovered healthy primary.
- Arrow animates only while fresh controller reports ARMED/APPLYING/WAIT-CLIENT/RESTORING. Return animation reverses direction; COMMITTED marks reserve selected without claiming success before confirmation. Reduced-motion preference disables movement; mobile vertical layout supported.
- Focused Node state regressions PASS; translation checks PASS. Browser synthetic APPLYING + failed source verified red RGB255/240/242, healthy reserve green RGB228/245/238, animation hv-transfer. No physical switches or deployment. Local candidate revision 7 / dashboard33 / ui17.


## 2026-10-16T21:27:23.2429697+02:00 — Correct localhost-to-router VPN link resolution
- Reproduced: preview used window.hostname, producing 127.0.0.1/#/vpndashboard. Replaced with explicit resolver: deployed LuCI uses its current hostname (supports changed IPv4, IPv6 and DNS names), strips only the separate LuCI port; localhost preview reads current private Ethernet-preferred Windows gateway via loopback-only runtime script. No machine-specific IP is embedded in public source.
- Missing/unsafe preview origins disable the link instead of falling back to localhost. Credentials, query tokens and non-HTTP origins refused. Local PowerShell startup exceeded initial five-second budget; bounded read budget corrected to 15 seconds and actual gateway discovery succeeded.
- Resolver Node tests PASS for multiple subnets, IPv6, hostname, HTTPS, port separation and invalid inputs. Browser visible href now actual router address. End-to-end opening NOT accepted: browser timed out, independent read-only TCP checks of router ports 80 and 8080 both timed out. No router reboot, routes, firewall or VPN settings changed.
- Local candidate alpha7-8 / dashboard34; package not installed on hardware. Preserve availability limitation separately from corrected URL generation.

## 2026-10-16T21:30:48.6830986+02:00 — Local adversarial security retest
- RPC duplicate fields/deep JSON were not explicitly refused; added strict bounded decoder and controlled ValueError for depth exhaustion. Nonfinite numbers and ambiguous keys now rejected before handlers.
- Preview Host/Origin were not constrained; added localhost listener-port allowlist and same-origin checks, CORP/nosniff. Actual loopback HTTP: 3 tests PASS, including rebinding-style Host, foreign Origin, traversal/private path denial.
- Added 256 deterministic hostile RPC subcases requiring zero writes/commands, ACL checks and session stripping. Full Linux CI pending; no WAN attack or physical configuration change. See SECURITY-RETEST-2026-10-16.md for scope and unverified hardware boundaries.

## 2026-10-16T21:32:09.8604643+02:00 — Security candidate exact-source CI passed
- Source a3da1397: 306 app / 24 QA per runtime, 11 UI suites; Python3.9/Lua zero skips. Package privacy/reproducibility PASS; receipt qa/ALPHA7-SECURITY-REVISION9-CI.json. Local preview protections applied. No physical deployment or external attack; current WAN exposure not certified.

## 2026-10-16T21:34:19.5089202+02:00 — Per-server heartbeat indicators
- Channels and servers now shows a labelled lamp on each configured profile card, including inactive profiles without starting them. Fresh DNS plus two HTTPS successes => green heartbeat; failed or inactive => steady red; checking => yellow; stale/unknown => grey. Reduced-motion preference disables blinking.
- Reuses existing profileHealth freshness/health logic; decorative pulse is a healthy-status indicator, not packet/activity telemetry. Auto OFF does not hide independent server health.
- Browser synthetic selected server: fault switched class to hv-lamp-failed with no animation; recovery switched to hv-lamp-healthy and hv-server-heartbeat. Existing health/order regressions PASS. Local candidate alpha7-10/dashboard35/ui18, physical router unchanged.

## 2026-10-16T21:46:46.3139269+02:00 — Expanded offline regression and protocol bootstrap diagnosis
- Repeated isolated model suite: 200 fault scenarios / 1737 assertions PASS; nine durable/process-crash tests and seven transaction replay/concurrency regressions PASS. These are models, not native hardware proofs.
- Actual guest startup benchmark: root minimal1.626s/imports4.612s, namespace minimal1.053s/imports3.463s; root routes unchanged, owned namespace removed. A quiet benchmark did not reproduce loaded startup delays.
- Added startup-stage tracing and a bounded faulthandler dump. Stack smoke captured more than20s spent importing mimetypes through http.server before DNS/TLS; full34s helper deadline then expired at TLS. Moved http.server import into serve only, leaving network2s deadlines unchanged.
- Lazy-import smoke then failed actual endpoint readiness: server bootstrap was still incomplete when probes started. Added a separate60s bounded endpoint startup barrier; still require real bound DNS/TLS success afterward. Retest running, not accepted yet. Initial Windows CRLF replacement changed no source; immutable-source-exists correctly refused duplicate launch; corrected via newline-normalised Python edit.
- Avoid extra guest Python cold starts for report reading: new bounded cat/host JSON collector. Earlier serial collector exceeded10s and is not evidence of VPN failure. Failed terminal smoke reports preserved separately.
- Browser inactive/stale tests found literal null interface and old latency shown as current. Corrected card interface label, suppress nonhealthy latency in cards/table, and count only fresh healthy profiles in current-OK metric. EN inactive lamp steadyred, RU stale lamp grey/no latency, mobile no overflow verified. No physical router access or changes.

## 2026-10-16T21:49:37.0683555+02:00 — Fixed package entrypoint/resource mismatch found by offline testing
- Actual builder still selected dashboard28.js/ui15.css while newer menu referenced dashboard29–36 and newer CSS. Earlier CI compared local source existence and SDK/IPK equality but not archive referential integrity; old hardcoded fixture masked the defect. No newer package was deployed on hardware.
- Builder now derives the exact dashboard from menu and its one referenced CSS, refuses missing/unsafe/symlink/ambiguous resources, and rejects legacy LuCI-controller mismatch. Generator synchronises legacy controller. New test opens actual nested data archive and follows menu->JS->CSS; checks current lamp/router-link code is present. Arbitrary dashboard997/ui997 fixture proves dynamic selection.
- Windows focused actual-package suite passed five tests before adding explicit missing/path/controller rejection matrix. New local candidate alpha7-12/dashboard37; older revision3–11 UI packages are superseded and must not be installed. Their prior PASS receipts still describe old narrower checks, not correct new-UI packaging.
- Corrected virtual endpoint startup barrier has reached18 real protocol assertions PASS; still RUNNING at181.39guest seconds, not terminal proof. All prior failed smoke reports remain preserved. No physical router access.

## 2026-10-16T21:55:33.0910928+02:00 — Corrected transport smoke, IPv6 guard and new long run
- Marked virtual smoke78ce2b2a terminal PASS:22 assertions,210.29 guest seconds, owned processes/namespaces cleaned, protected root unchanged. Real local WireGuard/OpenVPN DNS/TLS and scoped conntrack were exercised; not native GL.iNet acceptance.
- Synthetic IPv6 positive TLS control PASS, IPv6 route present, protected client attempt refused and guard counter increased2. No rule changes by this helper; not proof of GL.iNet forwarded IPv6 security. Earlier failed IPv6 evidence retained.
- New immutable7200-second guest-monotonic soak started at2026-10-16T19:50:44.532421Z, PID25685, root/tmp/homensai-protocol-lab-soakready20261016, source78ce2b2a9f8a0036c820714e827f6317ef87f7f669f518903967e3c677bde977. Source reuse requires matching hash/no symlink; no overwrite. It is RUNNING, not terminal PASS.
- Collector startup command exceeded20s serial response budget. Did not retry mutation: observed existing collector file, advancing series and zero missing events. Intermediate:19PASS at210.87guest seconds, complete coverage. Start-response timeout is not collector failure. No promise of wall-clock finish time from guest monotonic alone.
- Corrected package alpha7-12 exact-source CI PASS at0267eb063e7fbc462bdd2f960a2181cca9ff658b:308 application,24QA per runtime,11UI suites; Python3.9/Lua zero skips. SHA2561b44c36f27a82501be19bdf0e722658b2b1f5ddf1cc208c3a82cbbb8eed40244,456653bytes. Current JS/CSS and legacy controller are now actually inside IPK; no hardware upload.

## 2026-10-16T23:09:36.3917057+02:00 — Final-run observation and independent acceptance preparation
- Current immutable soak remains RUNNING:612PASS /225cycles, no event gaps; producer6s old/collector3s old. No physical router operations.
- Added terminal validator: rejects RUNNING/short guest or host duration, stale terminal collector counts, missing evidence, missing repeated fault/protocol coverage, cleanup failure and remaining owned processes/namespaces/keys. Two tests exercise19 adverse terminal mutations and one explicitly synthetic complete fixture; never substitutes fixture data for run evidence.
- Independent cleanup pre-check recorded8children,5server/client namespaces,7private test-key files and root route/rule/network/firewall fingerprint. After-check also scans all proc command lines for reparented cohort processes; no private key contents read/exported.
- Witness initial filename used17hash characters instead of16, causing FileNotFoundError before capture; changed to derive hash prefix, then pre-check succeeded. Added observation ages; stat command absent on this OpenWrt, so replaced read-only stat calls with minimal os.stat/time, without package installation.
- Added bounded read-only watcher; it never stops a failed producer, never changes immutable test, and never treats observation failure as PASS. Final acceptance still pending.

## 2026-10-16T23:15:11.5035498+02:00 — Report freshness and isolation checks
- Added strict final-observation freshness requirement (producer and collector ages0–90s); validator rejects stale snapshots. Two validator tests now cover21 adverse mutations plus explicit synthetic valid fixture. Generated report refuses to run before terminal evidence passes; report text distinguishes injected failures from failed assertions and selected-check counts from uptime.
- Container read-only inspection confirms network mode none, privileged false and no host mounts. Physical router remains untouched. Running producer source is unchanged; at latest observation651PASS /238cycles, complete coverage.
- Local report timezone dependency Europe/Berlin verified in bundled Python. Final report still pending the actual7200-second completion and independent cleanup audit.

## 2026-10-16T23:33:33.7074431+02:00 — Strict run failed; diagnostic correction and new exact-budget run
- Previous strict2s soak TERMINAL FAIL at5097.85guest seconds /243cycles:662PASS,1FAIL (soak-parallel-reserve-ova), no missing events. Preserve qa/protocol-ready-soak-terminal-failed.json; do not call this a two-hour PASS. Failed sample detail was not retained, so DNS/TLS/identity/timeout cause remains UNKNOWN; process logs show no OpenVPN restart before cleanup.
- Independent post-failure audit PASS for cleanup: zero owned processes/namespaces/private test keys, root checkpoint unchanged. Cleanup outcome is now separate from producer outcome; a failed test can have successful cleanup.
- Lab used2s sockets while shipped agent.bound_socket sets3s. Align lab default to3s and add actual application socket contract test. This is a proven test-budget mismatch, NOT proof that it caused the earlier failure. No retry masking; each unexpected sample still fails the run.
- Retain phase and complete sanitized DNS/HTTPS sample for every probe in bounded private JSONL; failed assertion now embeds its sample. Eight lab contract tests PASS, including failed TLS-detail preservation. No probe nonces, credentials or private key values exported.
- New immutable7200s run started2026-10-16T21:23:04.457035Z, source94376a1842bab35d37f1d9c67980f0c98cc5062e4a4a4ab88b8fb55d3c3a2513, PID4676, root/tmp/homensai-protocol-lab-final20261016. Collector PID5062 / source37500674553783b56ad81700a6d40b61bd99fffc4e39a2d8f57bbf9aac8bbafe. Helpers now bind to checked start-receipt metadata rather than stale hardcoded roots/PIDs. Current run not accepted until terminal evidence.
- Physical router untouched. No Internet-facing scan, firmware change or VPN setting change.

## 2026-10-17T01:31:25.1611719+02:00 — Final terminal acceptance and report
- Final source94376a1842bab35d37f1d9c67980f0c98cc5062e4a4a4ab88b8fb55d3c3a2513 TERMINAL PASS:7200.87guest seconds,7246.56host seconds,1335assertions,495cycles,zero failed assertions/missing events. Independent validator PASS; full report PROTOCOL-SOAK-FINAL-2026-10-17.md.
- Independent cleanup PASS before export and again after: no children/orphan cohort, no owned namespaces, zero private test-key files, root fingerprint unchanged. Marked VM QMP paused; no active soak/watcher. Physical router untouched.
- Raw archive1281records classified against exact scenario:495selected+495standby successes without retry,60injected negatives,7negative bounded restoration-wait samples;20restorations succeed. 67negative probes are not67unexpected outages. Preserve full CSV and archive.
- Evidence tar creation succeeded but first export failed because base64 utility is absent. Initial shell workflow lacked native-exit guards and reached pause despite failed export; no test result was accepted from that failure. Resumed only idle clone, used Python standard-library base64, added explicit exit guards, verified exact3-member archive and repeated cleanup before final pause. Archive SHA2563c3a7f1cd9eacd26183225a80cbbe7e07dad431a43a5a2112c5e0cd9fccae157.
- Rebuilt alpha7-12 privately:456653bytes, SHA2561b44c36f27a82501be19bdf0e722658b2b1f5ddf1cc208c3a82cbbb8eed40244 matches both exact CI runtimes. No deployment or new public release. Earlier strict2s failure remains FAIL with unknown original phase; corrected3s test is separately scoped.

## 2026-10-17T01:36:11.5220606+02:00 — Final evidence publication checks completed
- Exact final evidence snapshot e2bb3a7a2603695ba2691b69a48e77ea5d0d54b0 CI PASS:309application tests,27QA per runtime,11UI suites. Source and nested synthetic archive privacy audit PASS; reproducible package SHA256 remains1b44c36f27a82501be19bdf0e722658b2b1f5ddf1cc208c3a82cbbb8eed40244. Receipt qa/ALPHA7-FINAL-PUBLIC-EVIDENCE-CI.json.
- Both guests report QMP paused. Docker State.Paused=false describes the running wrapper container, not guest CPU state. Original QMP read initially returned PermissionError under its default user; read successfully as socket owner without changing ownership/ACL or guest state. Test copy remains paused, no soak/watch processes active.
- Report distinguishes7200.87s guest run from7246.56s host start-to-collection span. All failed earlier attempts retained; earlier2s standby failure cause remains unknown and is not retroactively declared fixed. No physical router operations or new GitHub publication.

## 2026-10-17 01:44 Europe/Berlin — bounded overnight virtual testing

- Request: continue local testing until morning. Deadline: 2026-10-17 07:00 Europe/Berlin. Physical router access, installation and network changes are excluded.
- Prepared two independent 7200-second runs of immutable protocol producer SHA256 `94376a1842bab35d37f1d9c67980f0c98cc5062e4a4a4ab88b8fb55d3c3a2513` in the marked, network-none QEMU clone. Each run uses a new root, receipt, independent cleanup witness and public evidence archive.
- Repeat-run blocker found during preparation: the collector previously rejected an existing producer-hash filename, and the exporter could reuse the previous fixed-name archive. Correction: immutable collector identified by its own content hash, verified before reuse and rejected if a symlink; per-run archive and per-run producer/collector logs. Historical evidence remains unchanged.
- Added `scripts/overnight-local.py`: exclusive lock, explicit timezone deadline, full-duration admission check with cleanup reserve, bounded subprocesses, three consecutive observation failures abort the transport sequence, cooperative owned STOP and independent cleanup. A failed or shortened run is never reported as PASS. QEMU is paused after cleanup. CPU-intensive offline suites run after the guest is paused.
- Added local regression checks: three tests PASS for deadline admission and repeat-run evidence isolation. Python compilation PASS. This is preparation evidence, not proof that the overnight runs have completed.
- Raw night output is written under ignored `private/overnight-*`; terminal summaries will be reviewed and copied into public project documentation without private keys. No provider credentials are used. Repeated offline suites are reported as repeated tests, not expanded unique coverage.
- GitHub publication remains gated by unrelated histories and colliding tags. No force push or tag replacement is authorized by this test request. Local Git and verified Gitea remain the saved source of truth.

## 2026-10-17 01:45 Europe/Berlin — preparation restart, stale-observation counter

- Preparation runner PID 91876 was stopped after identifying a control-flow defect: `errors=0` preceded freshness validation, so consecutive stale snapshots would repeatedly count as the first error. No stale snapshot occurred in the preparation run; this was found by code inspection.
- Correction: reset the consecutive-error counter only after a fresh snapshot passes validation. Preserve three consecutive failures as an abort condition.
- Requested cooperative STOP for the owned virtual producer only. Terminal result: STOPPED after 102.20 seconds, 22 passed assertions, zero missing events. This is not a completed soak or PASS.
- Independent cleanup PASS: no child/cohort processes, no owned namespaces, zero private key files, unchanged root network/firewall fingerprint. Clone QMP paused before the new launch. Prior evidence preserved under `private/overnight-20261016T234252Z`.
- Full preflight CI on source afdc4501e4f581738848d2453b0acd00275797a9: 309 application tests and 30 QA tests per runtime, 11 UI suites, package privacy and reproducibility PASS. Python 3.9/Lua zero skips; Python 3.11 control seven Lua skips. A new committed snapshot is checked before restarting the unattended runner.

## 2026-10-17 01:46 Europe/Berlin — verified restart and morning collection

- Corrected runner source: 19749ff091c5109ba3c4690110dfcc05f654a4d5; saved in local Git and verified Gitea. Full exact-snapshot offline CI PASS: 309 application tests, 30 QA tests per runtime, 11 UI suites; unchanged reproducible alpha7-12 package. No installation.
- New bounded runner PID 92336 started at 2026-10-16T23:45:52.351194Z (01:45:52 Europe/Berlin), deadline 07:00 Europe/Berlin. Output: `private/overnight-20261016T234552Z`. First producer and immutable collector have started in the isolated clone. This entry records RUNNING, not completion.
- Scheduled one morning result-collection follow-up for 05:05 UTC / 07:05 Europe/Berlin, expiring that morning. No periodic status messages. Initial scheduling calls were rejected for a missing thread destination and a UTC schedule outside its expiry; corrected explicit thread destination and UTC hour. Successful create/update confirmed by the app.
- Keep the Windows host and Docker running for the overnight process. Host sleep or shutdown interrupts observation and must be reported as a gap, not availability evidence.


## 2026-10-17 07:08:48 Europe/Berlin - overnight terminal evidence reviewed

- Corrected runner completed at 06:58:25 Europe/Berlin; PID 92336 no longer exists and lock is absent. Re-ran both acceptance verifiers and raw-probe classifiers against saved evidence: PASS with exact equality to prior receipts. QMP-only query confirmed marked clone paused; guest was not resumed.
- Run 1: 7,215.45 monotonic seconds, 1,364 assertions, 501 cycles, 21 fault rounds. Run 2: 7,207.10 seconds, 1,380 assertions, 509 cycles, 21 fault rounds. Zero failed assertions and missing events. All 2,624 records accounted for: 2,020 steady-state successes, 126 injected negatives, eight bounded restoration-wait negatives; all 42 restorations passed. Negative fault samples are not production outages.
- Independent cleanup PASS for both: zero private test keys/owned namespaces/cohort processes and unchanged root network/firewall fingerprint. Exact-snapshot CI on 28a347a9945d22c2e82135829e2d3377359c5933 PASS; 23 repeats of the same 200-case model suite PASS, not new unique coverage. No corrected-run runtime errors recorded.
- Morning unprivileged Win32_Process inspection returned access denied. Read-only elevated Get-Process confirmed PID absent; no process, ACL, device or network modification was needed.
- Morning report write failed with UnicodeDecodeError at legacy byte 0x97 in STATUS.md: earlier Windows default-encoding output had inserted CP1252 punctuation into UTF-8 text. Converted only undecodable legacy bytes through CP1252, preserving valid UTF-8; explicitly wrote STATUS/WORKLOG as UTF-8 and checked strict decoding. No test data was changed.
- Added English final report docs/OVERNIGHT-TEST-REPORT-2026-10-17.md and reviewed public aggregate qa/OVERNIGHT-2026-10-17.json. Preparation STOPPED and earlier unexplained strict two-second FAIL retained. Physical router untouched; virtual result does not certify native hardware behavior or WAN security.


## 2026-10-17 08:41:20 Europe/Berlin - requested algorithm/UI approval checklist

- Created docs/TODO-ALGORITHMS-UX-2026-10-17.md with 22 proposed items, priorities, acceptance criteria and offline/hardware boundaries. Added handoff pointer; prior completion evidence is preserved.
- Included clear VPN-check lifecycle, confirmed Auto states, router-settings navigation, separate speed/fault actions, brighter raised primary buttons, a proposed 16-18 px green health lamp, accessible state colours and placement of large actions. Algorithm items audit/reuse existing mechanisms before extending them.
- Status: awaiting user review. No product code, generated UI, package, virtual guest or physical router changes.


## 2026-10-17 09:13:02 Europe/Berlin - approved UX/algorithm implementation, alpha8 candidate

- User approved the full checklist for local execution. Physical router and VM remain unchanged. Added alpha8-1 candidate, dashboard38/ui19; prior dashboard37/ui18 retained. New asset URLs prevent stale browser cache from masking the changed UI.
- Cause: old Probe now queued a request and immediately read the previous status, without an operation identity. Added locked single-flight request IDs, QUEUED/RUNNING/COMPLETED/FAILED lifecycle, explicit published-measurement correlation, completed checked/failed counts and a retained manual result independent of later automatic rounds. No connected profiles yields an explicit empty result, never successful connectivity.
- Inspection found expiry races: a late completion could overwrite a replacement or throw inside the daemon; expired requests could repeatedly wake the loop. Corrections: ignore superseded completions, clear expired requests, reject overdue/corrupt state and preserve newer request identity. Added concurrent enqueue, late completion, expiry, corruption and stopped-service checks.
- Bright raised primary actions, confirmed Auto states, 18 px volumetric health lamps, reduced-motion support, mobile targets, explicit router settings navigation and server connection/health/selection/priority labels added. Dry-run detail moved to Diagnostics. Pointer-held redraw waits until click completion, and labelled keyboard focus is restored after redraw. Bright gradient endpoints adjusted for contrast instead of relying on colour alone.
- Added read-only failure diagnosis: only fresh explicit configured-uplink DOWN proof suppresses VPN cycling; link-up is not Internet proof. DNS, HTTPS, route mismatch, unverified path and stale observations remain distinct. Planner thresholds now use existing configured recovery policy rather than hardcoded 3/2. No direct-WAN fallback or route writes introduced in monitoring.
- Pure cascade model now uses capped exponential failed-hop quarantine and stronger probation, clears it after verified commit, preserves compatible old journals and rejects invalid counters. Native GL.iNet multi-hop/device acceptance is not claimed by this model extension.
- Preflight: 329 application tests PASS (Python 3.11 control has seven Lua skips), UI contract suites and 30 QA tests PASS on earlier focused selections; full immutable dual-runtime CI follows this commit. Browser verified synthetic queued/completed result, English/Russian section persistence, desktop no horizontal overflow, 18 px computed lamp size and active-first card order. No real network test was performed.


## 2026-10-17T09:20:09.409763+02:00 - alpha8 exact-source verification and local release candidate

- Immutable source aafdac37f0ed7a23364cd9f4f1e65bdefed32c91: both Python runtimes PASS, 329 application tests + 30 QA tests per runtime, 12 UI suites in development runtime. Python 3.9/Lua zero skips; Python 3.11 control seven Lua skips. Reproducibility and nested source/package privacy PASS.
- Built local alpha8-1 IPK, 463562 bytes, SHA256 da7f42716b3d35504be3f586a7ee1b18c8e75a8ec51c01e134dd24da3b182453; exact equality to both CI builds checked. No deployment. Prepared local release notes and reviewed CI receipt.
- Additional isolated model checks PASS: nine transaction/crash tests, seven transaction regressions, 200 scenarios / 1737 assertions. Native cascade/worker arbitration, inactive reserve isolation and LAN proof were audited against existing executor/runtime contracts and passing tests; real device proof remains blocked, not marked complete.
- Browser confirmation: all nine Russian sections at 414x896 have no root horizontal overflow; the connectivity action is Overview-only. A failed synthetic RPC displayed unavailable and enabled retry. English/Russian language switching preserved section. Bright text gradient endpoint contrast minimum 5.35:1; green power symbol minimum 3.49:1. Stored screenshot explicitly contains only synthetic data.
- Added item-by-item report with honest local/model/hardware states. No original VM, physical router, routes, services or credentials changed. New local release is not a GitHub release; unrelated-history/tag reconciliation remains unresolved.


## 2026-10-17T09:27:09.431921+02:00 - approved GitHub main publication preparation

- Verified public repository, authenticated HomenSAI account and fresh main SHA 51982dd249fb4ea96fbd1573f35e01bdd9c538d5. New public alpha8 tag absent (expected HTTP 404). Canonical/public histories are unrelated; existing historical tag collisions remain unchanged.
- Selected reviewed-snapshot publication with public main parent, keeping full canonical history in Gitea. No force/mirror/old-tag push. Refreshed current-state/publication README text and removed personal workspace context from two tracked Markdown files. Product/package bytes unchanged.
- Preparation approval does not authorize physical installation or native failover. Exact public commit must pass privacy and immutable-snapshot validation and be saved to Gitea before GitHub main push.


## 2026-10-17T09:31:46.597301+02:00 - GitHub main push independently confirmed

- Created public snapshot commit 5e9f23486e05fe7037624a404a905c9d615436b5, sole parent 51982dd249fb4ea96fbd1573f35e01bdd9c538d5, tree a972b8de20e111e204a02f81249ca8bf297138c3 exactly matching canonical source a514afa482792a6d630831dd8a822a18962fe47e. Full canonical history remains in Gitea.
- Saved exact public branch to Gitea, then immutable dual-runtime CI PASS with unchanged package hash. Ordinary Git push to GitHub main succeeded; GitHub API independently returned the expected public commit. No force or old-tag publication.
- Added documentation-only completion records and refreshed earlier GitHub-blocked statements. Preparing new prerelease on the public history; local canonical alpha8 tag is not bulk-pushed. Physical router untouched.


## 2026-10-17T09:33:33.360440+02:00 - release installation-document consistency

- Publication review found install examples still named alpha7-1 despite the new alpha8-1 artifact. Corrected EN/RU filenames/checksum examples and AI-install candidate label; retained monitor-first and separate hardware-window boundaries. Refreshed dated physical-checkpoint wording from the recorded alpha7-2 receipt, not a new router query.
- Product/package bytes unchanged. Follow-up contains documentation only and is saved to Gitea before normal GitHub main push. New public release tag will be created explicitly on the public commit, avoiding the same-named canonical tag's unrelated history.


## 2026-10-17T09:37:13.019621+02:00 - GitHub prerelease download verified and transport housekeeping corrected

- Created public lightweight tag v0.7.0-alpha8 explicitly on public commit a0fbd054f30e887b9b276399027d3ba31b33e21e via GitHub refs API, then prerelease using verify-tag. Canonical local/Gitea alpha8 tag remains 22b75b8500acc6bb13af302b0cbea0124f440a66; no canonical parent history or old tags were pushed.
- Downloaded both release assets from GitHub. IPK 463562 bytes, SHA256 da7f42716b3d35504be3f586a7ee1b18c8e75a8ec51c01e134dd24da3b182453; checksum match. All 13 historical public tag refs unchanged, remote commit tree matched local publication tree, prerelease true/draft false. Added public verification receipt.
- A prior local-codex bundle import emitted background Git auto-GC errors: node could not create a lock beside the preserved backup/recovered ref. Import, exact primary save and GitHub push still succeeded and were independently verified. Correction: disable automatic GC/maintenance only for that controlled transport-fetch command; preserve ownership/backup refs and do not change ACLs or global Git configuration. PowerShell parser and next actual primary-save verification check this change. Product/IPK unchanged.
- No router access, installation, route/firewall/VPN change or forced Git update. Final records are saved locally/Gitea before normal GitHub main follow-up.


## 2026-10-17T09:42:57.430883+02:00 - alpha9 overview selected-path colour correction

- User reported both Primary and Reserve constantly green. Cause: autoPathModel mapped each healthy tunnel to green independently of the controller-selected route. That conflated connectivity with traffic selection.
- Correction: green only for the fresh confirmed selected and healthy plan path; healthy unselected candidate is neutral/ready, confirmed failed probes red, destination awaiting transition confirmation yellow, stale/off/unknown neutral. Both tunnels may be connected; labels/legend describe the plan route, not every router policy or exclusive process connection. Degraded selected reserve remains visibly failed rather than pretending a healthy primary has already been selected.
- Added 200 controller/health-state combinations proving at most one green path and selected identity; updated transition/return expectations. Node regression and generated syntax checks PASS. Browser local Russian preview confirms neutral ready Primary and green active Reserve. Physical router unchanged.
- Prepared distinct alpha9-1, dashboard39/ui20 to preserve alpha8 release/assets and avoid cache confusion. Full immutable CI, package and publication follow after this source checkpoint.


## 2026-10-17T09:46:15.516980+02:00 - alpha9 path UI acceptance and package

- Immutable source 18be40f4d0504ffc25c815675f077859087fde47 dual-runtime CI PASS: 329 application tests, 30 QA tests per runtime, 12 UI suites including 200 path combinations. Python 3.9/Lua zero skips; Python 3.11 control seven Lua skips.
- Browser confirmed primary active/standby ready; primary failed/destination checking; primary failed/reserve active; recovered but unselected primary ready/reserve active. EN/RU labels and selected-only green verified. Screenshots explicitly synthetic; no real path trial.
- Built alpha9-1 and checked exact SHA256 equality to CI: af820a3ea1937bbee11a2f20b7d60dcf5e24615f226d2e0e27dacd31ead78521. New versioned UI assets preserve alpha8 and prevent stale-cache display. Local-first snapshot publication and new prerelease follow; no existing tag/asset or physical device is changed.


## 2026-10-17T07:49:38.478495+00:00 UTC - alpha9 publication independently verified

- Saved exact canonical and public snapshot branches in Gitea before normal GitHub main push. Public snapshot 2d3cd63d370fccf934424b9bf597ea21fa89e653 has canonical source 6bef4f5572a6ad8f97f1ce44849e23d51a9c7b08 tree; canonical history and alpha8 tag/assets retained. Exact public snapshot CI PASS with unchanged alpha9 package hash.
- Created separate public alpha9 tag on public history and prerelease with IPK/checksum. Downloaded both assets again: 464018 bytes, SHA256 af820a3ea1937bbee11a2f20b7d60dcf5e24615f226d2e0e27dacd31ead78521; checksum matches. Alpha8 public tag independently unchanged. Verification receipt qa/GITHUB-ALPHA9-PUBLICATION.json.
- This follow-up records publication only; overview UI was already verified in four synthetic browser scenarios and 200 state combinations. No router installation or routing/VPN/firewall change.


## 2026-10-17T10:00:49.104583+02:00 - alpha10 clipped navigation repair

- User screenshot showed Settings clipped below the viewport. Cause: sticky sidebar had fixed viewport-derived height plus min-height 620px, while branding, nine menu items, gaps and footer could exceed that height; the nav had no constrained vertical scroll area. A sticky fixture/header could also cover its top.
- Correction: compute available sidebar height from actual viewport/sidebar position and fixed/sticky external header; remove minimum height, give nav flex/min-height-zero and independent vertical scroll, retain nonshrinking brand/footer, and use whole-sidebar scroll for exceptionally short panels. At mobile widths all nine links wrap into a two-column grid. No routing, VPN or hardware behavior changed.
- Active menu entry is revealed on section change without moving the entire document; explicit focusable nav supports keyboard scrolling. Short-height spacing keeps the entire menu visible at the screenshot-sized 978x808 frame. Browser measured Settings inside the menu/viewport; sidebar bottom 795.2px at 808px height, no root horizontal overflow.
- Browser matrix PASS: 126 page transitions across seven viewport sizes (978x808, 1280x720, 1024x600, 800x480, 640x360, 414x896, 360x640) and EN/RU. The 640x360 case approximates the CSS area available at 200% zoom on a 1280x720 screen; native browser zoom itself was not changed. Keyboard Home/PageDown moved the constrained nav with focus retained. Synthetic screenshots/matrix saved under qa/ui-review-alpha10.
- Prepared alpha10-1/dashboard40/ui21 and geometric regression tests. Renewed only the owned loopback synthetic preview for two hours; original preview identity verified before replacement. Physical router/network unchanged. Immutable CI/package/publication follow the source checkpoint.


## 2026-10-17T10:04:03.316325+02:00 - extra short-window active-link inspection

The first alpha10 snapshot passed full CI. Inspection found the exceptionally short-panel fallback must reveal the active link in the whole-sidebar scroller, not the non-scrolling nav; resize must also reveal the current item. Corrected scroller selection and resize scheduling before final packaging. A 1280x300 browser case is added to the existing matrix; no product routing behavior changed. Final source CI is rerun after this correction.


## 2026-10-17T10:04:03.316325+02:00 - direct-link stylesheet timing correction

The added 1280x300 case exposed a real failure on direct Settings reload: active link bottom 543px while sidebar bottom 287px. Initial reveal ran before final stylesheet/menu sizing, and later observer updates did not reveal the current item. Corrected by observing nav dimensions and revealing after layout/header/resize changes. User-driven scrolling alone does not change dimensions, so it is not reset. Existing 126 transitions remain valid; direct reload is rechecked before final acceptance.


## 2026-10-17T10:06:20.173913+02:00 - final short-window browser result

Expanded matrix to 144 transitions (nine pages/eight sizes/EN-RU), all pass. Added 1280x300 whole-sidebar fallback. Direct Settings reload now places the link at 243.6-283.0px inside the sidebar 61.2-287.2px, scrollTop 260; the prior 543px bottom failure is corrected. Saved final synthetic screenshots and matrix. Final source gets its own immutable CI before packaging.


## 2026-10-17T10:07:54.555139+02:00 - alpha10 final source/package verified

Final source 192220cf1828e6d66207d877610a1d81d0ce9914 dual-runtime CI PASS: 329 application + 30 QA tests per runtime, 13 UI suites. Python 3.9/Lua zero skips; Python 3.11 control seven Lua skips. Host alpha10-1 build exactly matches both CI outputs: 465422 bytes, SHA256 87c0cf97517b77d03caa549cc07f42824ae11c61a9b4f64140db0fe2f2171b16. Final direct Settings reload and 144 transitions PASS. Release notes/receipt saved; physical router remains untouched.


## 2026-10-17T08:09:42.974788+00:00 UTC - alpha10 publication download verified

Canonical source ac9be28b9e0af828e880a516fd0aacd6ee7fa850 and public snapshot 45da054fc6732fc966ca4b936b17f69e3a4fbf42 trees match. Saved locally/Gitea before normal GitHub main publication; no force or historical tag overwrite. Created public alpha10 prerelease on its own public commit; downloaded both assets again: 465422 bytes, SHA256 87c0cf97517b77d03caa549cc07f42824ae11c61a9b4f64140db0fe2f2171b16, checksum matches. Alpha9 tag independently unchanged. Verification receipt qa/GITHUB-ALPHA10-PUBLICATION.json. This documentation-only follow-up preserves the product/package bytes; physical router/network unchanged.


## 2026-10-17T10:42:27.632332+02:00 - post-alpha10 approved execution preflight

User approved all feasible local/virtual checklist work and explicitly prohibited physical installation. Verified clean canonical checkout and marked QEMU clone paused: Docker network none, privileged false, no host mounts. Preparing private baseline disk checkpoint before virtual installation. Existing historical helpers target older fixed packages; they will not be blindly reused against alpha10. New acceptance receipts must identify exact installed package and preserve earlier evidence.


## 2026-10-17T09:22:14.034105+00:00 - isolated OpenWrt acceptance checkpoint

2026-10-17T09:22:14.034105+00:00. Scope: marked isolated x86 OpenWrt copy only. Physical router and host networking untouched.

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| Installed alpha10 verification | PASS, 15 checks | Actual opkg/runtime; not a second upgrade |
| Downgrade to alpha7-2 | PASS, 12 checks | Actual opkg, own configuration retained |
| Re-upgrade to alpha10-1 | PASS, 17 checks | Package SHA256 87c0cf97517b77d03caa549cc07f42824ae11c61a9b4f64140db0fe2f2171b16 |
| UCI failure injection | PASS, 11 checks | Read-only delta/config writes refused; no duplicate anonymous section |
| Own monitor process crash | PASS | New PID and measurement timestamp after crash required; not Internet recovery |
| Guest warm reboot | PASS | Configuration retained, monitor autostart, new measurements, Auto OFF |
| Actual LuCI desktop/narrow desktop | PASS | Nine pages at 1280x900 and 978x808 |
| Actual LuCI mobile | FAIL | Channels/ranking search content-box width overflows at 414px; correction pending |
| Native start on generic x86 | REFUSED as expected | Unsupported board/vendor and missing client/deadline guards; no real switching certified |

Initial synchronous acceptance harness returned FAIL after package installation; the exact failed subcommand was not retained, so its cause remains unknown. Installation was independently verified. The replacement detached job records exact failed steps and bounded progress. The earlier age-only monitor receipt was preliminary; final crash check requires a post-crash timestamp.

Guest time lagged host by roughly seven hours after a long pause. Only virtual guest clock/RTC were aligned; this is fixture maintenance, not proof of a production NTP fix. Warm reboot does not prove hardware power-loss/flash behavior or repair the original guest GRUB boot path. No connected VPN profiles were measured; zero checked servers is not Internet availability proof. Private raw receipts and disk backup remain excluded from publication.


## 2026-10-17T09:28:11.614245+00:00 - local 0.8.0-alpha1 candidate, no physical installation

Actual virtual LuCI exposed content-box search overflow on Channels and Ranking at 414px. Cause: vendor input sizing overrides the application's universal box-sizing rule. New immutable ui22/dashboard41 adds a scoped input border-box/max-width rule; old alpha10 files are preserved. Actual-browser acceptance follows package installation in the isolated clone; the source regression alone is not browser proof.

Added read-only system readiness: dependency checks, allowlisted actual board/firmware, measurement freshness and explicit unknown native permission. It does not authorize Auto or replace Start's certification/lease checks. Added shared recovery preset data, draft-only selection with existing review/save validation, incident detail and bounded escaped standalone HTML export for browser Print/Save as PDF. Missing retained evidence remains unknown; no fabricated root cause or LAN outage duration. No PDF runtime is added to the router.

Added reviewed snapshot publication helper: exact dual-runtime source/package receipts, clean current source, Gitea save before public parent/tree snapshot, normal explicit main push, immutable release tags and independent asset re-download/hash verification. No canonical history is pushed and no old tag is overwritten. Extended Gitea save to a named reviewed branch without switching the working checkout. Extended CI to explicit full-SHA immutable exports; uncommitted work remains excluded. Restricted jobs retain network/credential isolation. Gitea server-triggered CI activation and exact vendor SDK remain external prerequisites, documented separately.

Prepared bounded read-only virtual resource sampler (1-96 samples). It is not a 24-48h hardware/flash study. Existing native/cascade/lease/committed recovery/candidate suites are rerun as local contract checks, not device acceptance.


## 2026-10-17T09:32:10.149030+00:00 - actual LuCI dependency loader defect

Candidate alpha1-1 installed and passed 17 backend checks, but actual browser rendering FAILED with ReferenceError: rpc is not defined. Cause: generated RECOVERY_PRESETS variable was prepended before LuCI require directives, preventing loader dependency discovery; Node tests supplied rpc globally and missed this integration failure. Correction: preserve the directive prologue and inject preset data immediately before view.extend. Added directive-order regression. New immutable dashboard42/package alpha1-2 replaces the failed candidate in the isolated VM only. Backend installation PASS is not UI PASS.


## 2026-10-17T09:34:34.455677+00:00 - actual LuCI stale discovery cache after upgrade

After directive correction, actual LuCI still requested removed dashboard41.js and returned HTTP 404, although installed menu/controller selected dashboard42. Diagnosis found hashed luci-indexcache.<hash>.lua/json files and cached own controller under luci-modulecache. Old postinst removed only literal /tmp/luci-indexcache. Correction: bounded regular-file invalidation for LuCI discovery indices and only the exact own cached controller, refusing symlinks and preserving other module caches. Added selective/idempotent/symlink regressions; new package revision alpha1-3 retains earlier failures. This is virtual acceptance; physical browser 403 history is not attributed to this cache finding.


## 2026-10-17T09:40:09.478230+00:00 - readiness RPC overhead and timed-out acceptance

Alpha1-3 virtual acceptance FAILED at correlated scan completion after ubus returned 7. Later independent diagnostics found the exact request COMPLETED with matching measurement ID and zero connected profiles; monitor was running with a fresh snapshot. The original FAIL remains retained and is not relabelled PASS. Single status RPC took 3.458s. Inspection found readiness snapshot collection ran both in the daemon and in every status RPC, duplicating board/dependency subprocess work. Correction: RPC now returns the daemon-cached allowlisted readiness snapshot; no environment commands in the read handler. This reduces observed overhead; precise attribution of the original timeout to this duplication alone is not proven. Alpha1-4 is tested as a distinct package.


## 2026-10-17T10:05:37.019572+00:00 - alpha1-4 acceptance and retained limitations

Source 85aa212d760a80e20c570f80e477dc70ac1a56e6 dual-runtime CI PASS: 336 application + 32 QA tests each; Python 3.9/Lua zero skips, Python 3.11 seven Lua skips; 15 UI suites. Package 469212 bytes SHA256 4f4861a367940109022624d93e8dbd66d9aef2ba12ba81f71ca38735f58edfca matches both CI runtimes. Injected child exit 17 propagated as runner exit 1 with no PASS receipt.

Actual virtual alpha1-4 upgrade acceptance PASS 17, own settings/network/firewall preserved, Auto OFF, correlated scan COMPLETED with zero connected servers. Actual LuCI now loads current dashboard42 and correctly displays QEMU/OpenWrt 21.02.7, fresh monitor and native blockers. RU 30 transitions across 414x896, 978x808, 1280x300 passed; subsequent English switch visibly confirmed after a browser command timeout. Synthetic 400 long profiles: EN/RU 40 transitions at mobile/narrow desktop, no root overflow. Preset stability values, review and cancellation checked; incident detail HTML downloaded. Native browser zoom and actual Print-to-PDF dialog were not exercised.

Resource sampler initially hit CLONE-SERIAL-TIMEOUT at 20s. Retried with a bounded 60s transport limit and at most 256 process entries; no timeout cause beyond observed transport/load is claimed. Preliminary successful run incorrectly included observer RSS because its own command text contained the monitor path. Corrected to exact argv path + daemon argument and retained preliminary data privately; final sampling is separate. No physical resource/flash performance claim.

After guest reboot, /tmp/HOMENSAI_VIRTUAL_LAB marker was absent and candidate launcher correctly refused. Verified marked host clone and x86 guest before recreating only that temporary marker. One Windows nested-quote diagnostic command failed with SyntaxError before execution; replaced by stdin script, no device change. These are lab harness failures, not physical VPN failures.


## 2026-10-17T10:06:05.597789+00:00 - corrected virtual resource sample

Three bounded samples 10:04:55-10:05:20 UTC: exactly one own monitor daemon, RSS 22245376 bytes in each sample; MemAvailable 143093760 bytes and config free 58970112 bytes. These are short x86 virtual observations, not a soak, CPU benchmark, hardware RAM budget or flash-wear acceptance. Preliminary self-matching observer data is excluded from this result.


## 2026-10-17T10:09:28.710002+00:00 - reviewed GitHub publication and laboratory cleanup

Source 509d015c6fe4e10ae90fe383da593c651312e5bd was saved in Gitea, then identical tree 20defafcad2d3e8efc7b3b0274f87639c745bfc3 published as public commit 0ae27e089501d979985d8f5e7337994df52fa880 on existing public parent 6ea0af45b63d29115bea562c3fa18be40bbb666b. No canonical history merge, force push or old tag replacement. Prerelease v0.8.0-alpha1 created on the public commit. Package and checksum independently downloaded: 469212 bytes, SHA256 4f4861a367940109022624d93e8dbd66d9aef2ba12ba81f71ca38735f58edfca. Publication helper completed successfully.

Closed only verified own lab helpers PID14732/81316, removed clone HTTP forwarding and independently confirmed port8081 closed; QMP reports marked clone paused/running false. Original VM and physical router were not modified. Named-branch Gitea helper was corrected to avoid testing an unset/stale LASTEXITCODE when no native branch-read command ran; actual named-branch save succeeded.

Checklist remaining external work: exact vendor SDK provenance/build; server-triggered Gitea CI activation; physical vendor workers/cascade/LAN DNS/Kill Switch/IPv6/provider isolation and 24-48h hardware observation. Local/model checks do not certify these. No recurring automation or physical deployment was created.


## 2026-10-17T11:57:26.304678+00:00 - approved virtual hardening follow-up

User authorized the proposed eight additional tasks with physical router excluded. Prepare a paused-disk baseline before interrupted opkg trials. Existing alpha1-4 and its failed predecessors retain immutable receipts. New long run will identify the exact final candidate and report RUNNING until its deadline; short model repeats are not unique coverage.


## 2026-10-17T12:00:52.605886+00:00 - reproduced malformed accounting checkpoint defects

Scratch-only adversity tests reproduced four failing cases and two uncaught exceptions: top-level JSON array caused AttributeError at restore/raw.get; checksummed saved=1e300 caused OverflowError in datetime conversion; accounting array/wrong collection/negative gaps/non-numeric quality bucket were silently accepted. Checksum alone did not validate structure. Added bounded schema/numeric/calendar validation before restore and backup rotation. Corrupt current data must recover a known-good backup with STORAGE-RECOVERED; no good copy yields STORAGE-001. ENOSPC-before-replace and replace failure already preserved the known file and are retained as regressions. No physical state or real measurements were injected.


## 2026-10-17T12:02:44.670305+00:00 - interrupted virtual upgrade and local publication recovery

Three actual opkg --force-reinstall lifecycle interruptions completed: preinst, postinst, before RPC reload. The owned process group was killed only after the explicit private checkpoint marker; each ordinary alpha1-4 recovery install exited 0, own configuration and network/firewall/main-route fingerprint remained unchanged, monitor regained fresh measurements, Auto remained OFF. This is not a physical power-loss or mid-flash atomicity claim. Instrumented artifacts are private and never release assets.

Publication now retains planned release identity before remote effects and supports explicit --resume of the same private ledger/source/CI receipt. Reconciles main/tag/release/asset evidence before retry; wrong tag/hash/moved main/draft state refuses. Local fake remote tests interrupt after each of five mutations and resume without duplicate mutations; no synthetic GitHub releases were created. Added bounded external command timeouts. Chosen recovery preset remains selected across review/back; editing a value switches to Custom. Local cancellation issued zero writes. Candidate advanced to alpha2/dashboard43; old assets remain unchanged.


## 2026-10-17T12:19:46.425736+00:00 - virtual storage, wizard and report acceptance

Actual disposable 64KiB tmpfs retry passed six checks: ENOSPC preserved known checkpoint; freeing space restored writing; semantically invalid checksummed data recovered backup; corrupt current file could be replaced; backward/forward synthetic timestamps marked gaps without invented bytes; protected network/config fingerprint unchanged. Tmpfs unmounted. First helper FAIL (OSError, before any check) is retained; buffered filler close could retry the failed flush. Changed to unbuffered writes and bounded processing before retry; do not count first attempt as PASS.

Actual LuCI recovery wizard selected Stability visibly, saved failures=5, reopened with 5, returned through Back, restored original values and saved. System wizard refused identical primary/reserve, passed installed UCI self-test, reviewed metadata, saved and reopened existing virtual pair. Neither wizard enabled Auto or imported VPN credentials. Telegram field was empty; missing valid stored token correctly blocked Next, then cancellation; no token entered or message sent. Browser command failure/pending-save cases remain separately covered by local UI tests.

Downloaded synthetic incident HTML has no active elements/external resources. Converted it through isolated-profile LibreOffice, extracted expected incident text, checked no PDF JavaScript actions, rendered and visually reviewed one readable page. The in-app browser rejected file: URLs by security policy; no workaround attempted. Native browser Print remains unverified. Only virtual guest clock/RTC were aligned after pause-induced lag; host/physical clocks unchanged.

Browser sizing audit found prior qa/alpha0801-browser-matrix.json actual LuCI rows were all 414x896, despite requested three sizes; viewport control affects the selected tab, not a background tab. Prior WORKLOG/release text overstated distinct actual sizes. Mobile overflow correction remains demonstrated, but multi-size claim is withdrawn pending corrected selected-tab tests. New English 30 transitions completed; a Russian batched command timed out and its unfinished batch is not acceptance. Corrected method opens a dedicated visible virtual tab, verifies selected ID and actual innerWidth/innerHeight at each size, and records bounded chunks.


## 2026-10-17T12:24:30.709218+00:00 - corrected actual LuCI matrix complete

Corrected selected-tab method PASS: 60 transitions, 10 sections x EN/RU x measured 414x896, 978x808 and 1280x300. Every row asserts actual innerWidth/innerHeight; all visible pages fit root width. Saved raw measured rows, not requested sizes. Dedicated test tabs closed after viewport reset. This supersedes the previously overstated distinct-size claim; original receipt remains unchanged for audit.


## 2026-10-17T12:27:44.026313+00:00 - endurance runner smoke accepted

Immutable runner cb708e87da4bce942c808262a8e9ecf8c494c476 verified its frozen files against Git and all 34 installed code hashes against alpha2. Sixty-second smoke PASS: 2 samples, 0 failures, 0 gaps, maximum monitor RSS 22228992 bytes. Producer paused the clone; independent watchdog separately confirmed pause and then promoted MEASUREMENTS-PASS to PASS. This short smoke is not long-duration acceptance. The 12-hour run is prepared next with its own source, deadline and output directory.


## 2026-10-17T12:32:09.340822+00:00 - alpha2 publication and 12-hour observer started

Source 8ab8011e85647ed4179f69d02d9ffe7cb9f62af5 saved Gitea first; public snapshot 4c6bea35d87dbfda4f9bc46042555b0371d63d77 and prerelease v0.8.0-alpha2 verified. Package 470221 bytes SHA256 8de85658c568d3a2610ba545d263a190e218f5d2ba128a01969678087810c2c8 and checksum independently downloaded. Explicit --resume of the completed same operation preserved the public main commit and both remote asset IDs/bytes, with no duplicate publication. Alpha1 release notes corrected for the viewport sizing erratum; its tag/package remain unchanged.

Twelve-hour virtual monitor observer started 2026-10-17T12:29:35Z, deadline 2026-10-18T00:29:35Z (02:29 Europe/Berlin). Frozen source 8ab8011e85647ed4179f69d02d9ffe7cb9f62af5; package/code hashes pinned. First two samples had zero failures/gaps; this is only RUNNING/start evidence, never final PASS. Separate watchdog process was verified by exact frozen path/run directory. An unprivileged WMI read returned Access Denied; approved narrow own-process inspection succeeded. Status/events remain private/virtual-hardening-20261017/endurance-alpha2-12h; no repeating chat automation created. Physical router/network untouched. Do not run concurrent serial helpers or replace the guest package while the observer owns it.


## 2026-10-17T13:32:11.625385+00:00 - owner-requested stop and Claude audit handoff

Owner explicitly requested all current project tests stop and a review checkpoint be prepared. Verified run identity/source and created only its cooperative STOP file. Final STOPPED: started 2026-10-17T12:29:35Z, finished 2026-10-17T13:26:07Z, elapsed 3391.75/43200 seconds, 57 samples, 0 observed failures/gaps, max monitor RSS 22228992 bytes. Independent cleanup confirmed pause; recorded producer/watchdog identities no longer active; scoped project-runner inspection found zero additional test runners. Marked QEMU clone reports paused/running false, lab listeners 18900/18901 absent. STOPPED is not PASS and no reliability failure is inferred merely from the requested stop.

Created root CLAUDE.md with imports and .claude/handoff/ containing start guide, full state, all 50 proposed items with acceptance/initial assessment, evidence index, independent review prompt, result template and separate physical readiness gates. This does not launch Claude, grant device access, authorize implementation of the backlog or alter tool permissions. Corrected stale current state/TODO and labelled older handoffs/native notes historical.

Saved private paused-disk/kernel copy plus SHA256 manifest under private/claude-handoff-20261017; no RAM snapshot or clean cold-boot guarantee is claimed. Private disks, logs, sessions and full Git history are excluded from publication. Physical router and Windows network settings were not accessed/changed. Documentation-only checkpoint preserves the tested router tree/package; validate imports, references, 50-item completeness and privacy without restarting test suites at this pause boundary.


## 2026-10-17T13:39:06.267371+00:00 - explicit version policy and handoff release preparation

User requested a GitHub release and explicit versioning. Application code/package remain alpha2/alpha2-1; introduce independently versioned documentation handoff 1.0.0 with tag handoff-v1.0.0, VERSION.json, immutable release policy and read-only version agreement validation. Backfilled changelog links for previously published candidates without inventing new device acceptance. Release archive contains only sanitized review context, never private run/disk/session data or an installable router package. No long or product test suite restarted.


## 2026-10-17T13:43:26.311491+00:00 - handoff-v1.0.0 release independently verified

Canonical source 3fd94bd2e6777ccac24617912726a3da4a18c25b and exact public snapshot 9c8826ab955a8d0cd6c054e8c789bd882cf6ec8e saved to Gitea before normal GitHub main publication. Local/primary tag handoff-v1.0.0 targets canonical source; public tag targets its identical-tree public snapshot, mapped separately. Existing application tags/assets were not replaced.

Created experimental review prerelease handoff-v1.0.0. Downloaded all three assets again: context ZIP 21347 bytes SHA256 366b03e33933492a1b258b6935b5b3bdcd1e8bffe50961be52384812bb1cd4dd, VERSION.json and SHA256SUMS.txt; exact bytes/checksums match reviewed local assets. Archive has 14 allowlisted context files, no private backups/sessions/keys or ipk. Two independent local archive builds from the same committed source matched byte-for-byte. Read-only version agreement passed; three deliberate metadata mismatches refused. Application remains 0.8.0-alpha2/package alpha2-1/dashboard43/ui22. No product test suite, virtual workload or physical-router action was started. Publication receipt qa/HANDOFF-V1.0.0-PUBLICATION.json.


## 2026-10-17T17:00:00+02:00 - alpha3: Auto-start flow, copy and Settings regrouped; router test kit

- Owner request: a package in which the Auto button can be used on the GL-MT6000, tidier logic/text. The Auto button already worked as designed but refused with five explained codes out of about 47, which made it look broken. The refusal is intentional (LAN-certified trial first). Guards, ACL and native controller code are unchanged.
- Added autoReadiness/autoBlockerText (router/auto_panel.inc.js): ordered checklist and a bilingual explanation for every pre-start blocker; a Node test extracts the codes from native_switch.py/auto_control.py so a new code without text fails CI. Overview note and Telegram line simplified; Settings regrouped (build_sidebar_ui.py); recovery preset recognised on reopen (audit A35). dashboard44/ui23, package 0.8.0-alpha3-1.
- Viewed the generated UI in a headless Edge against the loopback synthetic fixture (screenshots outside Git); fixture data only, no router. Preview process stopped afterwards.
- router-test-kit/: preflight, install, verify, uninstall, emergency scripts and README (shell syntax checked only; never run on a router).
- Not done / still open from the audit: HELD-ON-RESERVE exit, client-confirmation authenticity, token deletion, endurance-harness gaps, hardware acceptance. Physical router untouched by this work.

## 2026-10-17T19:30:00+02:00 - first hardware LAN trial (alpha4), findings, alpha5/alpha6, GitHub release

- Router (GL-MT6000, 4.11.0) was upgraded 0.7.0-alpha7-2 -> alpha3 -> alpha4 by the kit (opkg, verify PASS each time; Auto OFF; network/firewall/main-route fingerprint unchanged). Backup streamed to the PC (private).
- Owner ran the unchanged LAN helper with -CableInterface 3. Real result: switch to the reserve confirmed from the LAN (exit address changed); the controller then ended in STOPPED-ON-RESERVE / SOURCE-NOT-VERIFIED / HELD-ON-RESERVE because the monitor (restarted by the install minutes earlier) had only 2 samples and the return rule needs 3 over 60 s. Audit finding D2 (no exit from the held state) confirmed on hardware.
- Later the owner changed VPN rules in the GL.iNet panel; the controller reported EXTERNAL-POLICY-CHANGE-GUARD-RETAINED and the owned nft guard became a full LAN block (iifname br-lan drop). LAN lost internet until the owner removed the guard by SSH (kit script). Not fixed by us at that time: cause = fail-closed guard retention; remedy implemented in alpha5.
- Permission system blocked: remote writes by the assistant, auto-supplying the helper confirmation, editing native_switch.py until the owner confirmed the safety change. None were bypassed.
- alpha5/alpha6: operator return (button + native_return), fresh-check return after a passed trial, release-on-outside-change, VPN-only fallback after an unverified rollback, 90 s independent release timer for a full block, test window options cleared, exit address in the authenticated UI, plain state texts, Help page with 12 topics, /usr/sbin/homensai-vpn-emergency in the package. 352 application tests + 15 UI suites + help-page test; isolated dual-runtime CI on 36af70f; package 2c7197b6.. (489866 bytes).
- GitHub: prerelease v0.8.0-alpha6 on public snapshot 094707ee (parent b7a0a81f), assets re-downloaded and verified. Local tags v0.8.0-alpha3/4/5 exist in Git and Gitea only.
- NOT done: alpha6 was never installed on the router (unreachable: PC on another network, cable unplugged); the stale HELD-ON-RESERVE journal on the router must be archived (homensai-vpn-emergency close-journal) before the upgrade, otherwise the lifecycle guard refuses. No physical acceptance of alpha5/alpha6 is claimed.

## 2026-10-17T19:42:00+02:00 - alpha5-alpha7 development without the router; virtual acceptance of alpha7

- Work done without router access: traffic-light status (button neutral), simplified navigation with a collapsed Advanced group, plainer texts, Help page, private trial number on LAN confirmations (helper -SelfTest PASS), Telegram token deletion, installed identity and mismatch notice, ranking confidence, endurance harness (sleep gap, lost producer). CI found one real defect (pid liveness raised OverflowError for out-of-range pids on Linux); fixed in 7089848.
- GitHub: prereleases v0.8.0-alpha6 and v0.8.0-alpha7 published on public snapshots 094707ee and 6b98a013 (assets re-downloaded and verified). Local tags alpha3-alpha5 stay in Git and Gitea only.
- Virtual acceptance (marked isolated x86 OpenWrt 21.02.7 clone, resumed for the check and paused again): upgrade alpha2 -> alpha7-1 PASS 17 checks (qa/alpha0807-virtual-upgrade.json); extra checks PASS 16 (qa/alpha0807-virtual-extra.json): status.package from opkg, new RPCs registered with the trial field, emergency helper installed and read-only show works, operator return refused without a held reserve, confirmation refused without a pending transaction, synthetic Telegram token saved, reported only as a flag, deleted, absent from config, no pending UCI delta. A second delete without a token returns SETUP-SAVE-FAILED (libuci refuses to delete a missing option); the wizard shows the button only when a token is stored.
- Not covered: GL.iNet workers, LAN DNS/Kill Switch/IPv6, held-reserve exit on hardware (modelled in tests only), power loss. The physical router still runs alpha4 and is unreachable from this PC at the moment.

## 2026-10-17T19:57:00+02:00 - experimental-software terms, first-run gate, virtual acceptance of alpha8

- Owner asked for installation docs, an "experimental, at your own risk" statement on GitHub and in the docs, and a first-run acceptance step. Found: install guides existed but carried no experimental/responsibility statement (only the MIT "AS IS" licence text); no acceptance screen. Added DISCLAIMER.md / DISCLAIMER.ru.md (seven points, not legal advice), banners in README (EN/RU), INSTALL (EN/RU), AI-INSTALL (EN/RU: the AI must show the terms and obtain explicit acceptance before touching a router), router-test-kit and LICENSING; install guides gained "First start" and "Installing with the router test kit".
- First-run gate (dashboard49): full-page terms with two required boxes, stored on the router (terms_version, terms_time) through the typed terms_accept RPC that accepts only the exact current version and uses the router clock. Until stored, the controller reports TERMS-NOT-ACCEPTED (nothing switches) and Auto start is refused; the terms stay on the Help page; a new version asks again. Existing installs (including the physical router) will ask on the first page open after the upgrade.
- Virtual acceptance of alpha8 (marked isolated clone, resumed and paused again): upgrade alpha7 -> alpha8 PASS 17 checks, extra PASS 27 checks including: terms not accepted initially, Auto refused with the terms blocker, three wrong versions refused without storing anything, current version accepted with router time, blocker gone afterwards, no pending UCI delta (qa/alpha0808-virtual-*.json). No physical-router access.

## 2026-10-17T20:40:00+02:00 - alpha9 UI release candidate (training, overview summary, simple/advanced settings, themes)

- Owner requests implemented: interactive training page with quiz/score; Overview summary card and getting-started checklist; "Step 1 check / Step 2 Auto" wording; country + protocol labels; Channels explanation; settings split into simple and advanced with per-step guides; monitor Start/Stop with a three-lamp light; Tests moved under Advanced; step-by-step Telegram help; HOW-IT-WORKS documents; one design layer and a light/dark/system theme switch.
- Verification: all JS suites PASS (new test_monitor_ui.js covers monitor light, guides, quiz scoring); isolated dual-image CI PASS on 8b8569fa; the first CI attempt FAILED the privacy scan because the Telegram token example in Help matched the token pattern (fixed by a non-token-shaped example). Container package build: 521747 bytes, SHA256 d5e2b6c6... equal to the CI hash.
- Not done: no physical-router test of alpha5-alpha9; no virtual-machine acceptance of alpha9; screenshots reviewed only for Overview, Training (first card), Channels, Statistics, Help, Settings on the synthetic fixture; Russian text not visually reviewed; no GitHub publication (needs the owner's permission).

## 2026-10-17T22:15:00+02:00 - alpha10: version line in the sidebar footer

- Owner asked for the program version in the lower-left corner of the page. The footer now reads "Version X · package Y · page Z" (program version first; falls back to the page's own version when the router does not answer). Since alpha9 was already published, this is a new version 0.8.0-alpha10-1 (dashboard51/ui29), not an edit of the published files.
- Verification: JS suites PASS; isolated dual-image CI PASS on 8e000caa; container package 521771 bytes, SHA256 5e764b6d... equals the CI hash. Not done: no physical-router test, no virtual acceptance of alpha10.
