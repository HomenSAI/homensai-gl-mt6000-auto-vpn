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
