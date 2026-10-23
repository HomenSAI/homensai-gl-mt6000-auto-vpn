# Active owner feedback / durable crash-resume point — 23 October 2026

Read [OWNER-IDEAS-2026-10-23.md](OWNER-IDEAS-2026-10-23.md) first. Owner explicitly requested recording later ideas without interrupting current Auto button/graph fixes, preserving the exact crash-resume state, then installing completed fixes on MT3000. Alpha38 is installed and Auto ON after62.73s verified Start; RPC registration required a second normal reload after upgrade. New source is uninstalled: three plotted graph levels and lock through RUNNING/PAIR-WAITING-PROBES. Bump alpha39 before next installation. Manual card-buttons, rounded whole-panel border, explicit selected route vs Internet health, labelled Step1 bars and missing Overview daily graph are queued, not completed. Last Gitea checkpoint a050116; later local commits/WIP need save after testing. Full resume order and evidence pointers are in the plan. Do not confuse older alpha37/38 success with these new UI requirements being accepted.

# Active Auto power-button transition lock — 23 October 2026

Owner reported repeat clicks during startup/Stop and requested locking the normal toggle for the entire operation. Alpha38 candidate adds correlated queued/STARTING/STOPPING backend display phases and retains a UI command lock beyond RPC ACK until a fresh completed controller observation. Redraw/reload keeps transition locking; Emergency Stop remains available during startup, repeated pending Stop is disabled. Focused JS duplicate-click/ACK/redraw/reload/completion checks PASS. Exact-source full CI, installation and fresh hardware Start/Stop confirmation are still pending; installed alpha37 Auto remains ON. Owner said another UI observation would follow; incorporate it into this active task. Dedicated MT3000 only.

# MT3000 alpha37 installed acceptance — 23 October 2026

The owner authorized complete tracked source plus current-task fixes to the existing Gitea repository and `feature/recovery-auto-20261023` only. Source c477c5d is already saved there; no GitHub/main/tag publication is claimed. Alpha37 is installed: 84 file/mode checks, protected configurations and actual served assets PASS. Exact-source dual-runtime CI PASS717app/107QA and37UI suites. Actual post-upgrade automatic cycle PASS133.01s with exact one automatic commit/one return; manual override/90s hold/primary/resume/bad-reserve refusal PASS181.84s. Weekly export and graceful service-restart persistence PASS8.43s. Known false pre-Start alpha36 records were corrected after daemon quiescence and verified after startup; the first overwritten correction is retained as a failed durability check.

Final retry Start PASS58.07s after one retained upstream AUTH_FAILED refusal; final37.42s/7sample acceptance PASS. Auto LEFT ON, primary selected, manual hold absent, both profiles DNS/twoHTTPS PASS, test fault tables removed, normal VPN-only guard valid. Final189entry encrypted/decrypt-read-verified export retained privately. Read [the consolidated report](../MT3000-AUTO-TEST-REPORT-2026-10-23.md) and [machine evidence](../../qa/MT3000-AUTO-MATRIX-2026-10-23.json). Dedicated MT3000 only; no Windows/primary MT6000 changes. Owner chose router-only evidence. External LAN, actual browser interaction, 24h soak, physical power-cut and unattended boot Auto resume remain unverified/unimplemented. Older entries below are chronological history.

# Active expanded MT3000 acceptance and UI/statistics work — 23 October 2026

Owner explicitly continued testing and added statistics/UI/manual requirements. Read [the current matrix and WIP checkpoint](AUTO-MATRIX-2026-10-23.md). Actual alpha35 nine-scenario/19m23s matrix PASS, 3 reserve commits/3 returns, test cleanup confirmed. Installed alpha35 Auto stays active. Unreleased alpha36 sources now contain statistics and UI fixes; full verification, manual Auto override, canonical build/installation and post-upgrade tests are still pending. Never install the earlier stale alpha36 artifact or call the WIP hardware accepted. Dedicated MT3000 only; no Windows or primary MT6000 changes.

# Owner-resumed crash recovery — 23 October 2026

Owner resumed and requested final automatic switching acceptance. Fresh results are in [the recovery report](RECOVERY-2026-10-23.md) and [machine-readable evidence](../../qa/AUTO-RECOVERY-2026-10-23.json). **Auto LEFT RUNNING on the dedicated MT3000**, alpha35, continuous-pair OBSERVING; final 66.64-second/7-sample read-only acceptance PASS. Two actual failover/return cycles (131.51/131.70 seconds), native crash recovery (20.18 seconds), Stop during startup and 80 installed file/mode checks passed. Exact original-source dual-runtime CI PASS681app/107QA per runtime/34UI; no product change/reinstall. One rapid startup received OpenVPN AUTH_FAILED and safely stopped; unchanged-config final retry after a pause PASS62.08seconds. This failure is retained. Automatic switching works in router-probed IPv4 scope; unattended production remains PARTIAL: external LAN, intermittent upstream rejection, boot auto-resume and long soak remain open. The application services/Auto remain active; old observers were not resumed. Primary MT6000 and Windows networking unchanged. Older entries below are historical.

# Active router-only completion — 22 October 2026

## Immediate Auto + chart handover completed

Alpha35 is installed and hardware-accepted on the dedicated MT3000 in router-probed IPv4 scope. Three complete actual cycles, ordinary/startup Stop, native crash recovery, settled reboot and postboot Start60.09s/final Stop14.07s passed. Last23state checks passed: Auto/clients off, services running, original policy/bridge/preparation retained, no fault/guard/fixture. Final189entry encrypted/decrypt-read-verified export is private/completion-20261022b/handover35-config.enc. No further hardware mutations are needed for this handover.

Immutable v0.9.0-alpha35 is published in GitHub and Gitea, with independently downloaded IPK/checksum verified SHA220261bbf1e876c2ca0429b491ab79b7a4f0d1e7ef3bfb34185370d484e07465,740585bytes. Canonical/local tagaa7eb85884a9da1b48f5544586e738f0a5944a13 and public tagea8d8e2668ca1220fce833f5e99ab5d7e6d8ad52 have identical trees. Both main histories contain the release; canonical protected mainb9ff460026cd275943b3a18ccfcb4c5732e70b9d passed all original checks after correcting only test fixture isolation. Exact b9ff dual-runtime CI PASS681app/107QA per runtime/34UI, package unchanged. Temporary Gitea authorization removed and absence verified. Publication facts: qa/ALPHA35-PUBLICATION.json. Final documentation-only synchronization follows without retagging/reinstalling.

Owner test: follow docs/AUTO-QUICKSTART.ru.md, refresh Ctrl+F5, then Start once and allow about one minute. Green/blue chart shows primary/reserve; Stop remains available. Independent external-LAN/MT6000 acceptance, full multireserve hierarchy, captive interception, broader stress/Telegram lab/server CI and long traffic soak remain explicitly unfinished in the eleven-item matrix. The later owner priority was working Auto today, not unrestricted scope growth. Older paragraphs below are chronological evidence, not the latest state.

20:41 UTC: alpha35 published in GitHub main/release publicea8d8e2668ca1220fce833f5e99ab5d7e6d8ad52 and Gitea release canonicalaa7eb85884a9da1b48f5544586e738f0a5944a13, exact identical release trees/package downloads verified; local canonical tag imported. Own temporary Gitea token removed and absence verified (UID1000 required with cap-drop; initial UID0 lacked DAC write permission). Postboot Start PASS60.09s and final Stop PASS14.07s; final23state checks and189entry encrypted export PASS, all hardware changes ended. Final aa7 full CI PASS;897 Git archive blobs/modes and complete20MB bundle verified. Protected Gitea main merge REFUSED on26 legacy test fixture errors: new pair helpers used unpatched agent.RUNTIME/PERSIST and touched container /var/run instead of each native fixture. Five test fixtures now share the same temporary paths across native/agent; no product/package/guard change. Repeat exact CI/protected merge pending. Public releases/tags remain immutable.

20:29 UTC release verification correction: final exact-HEAD CI refused stale install-kit SHA/size after the manifest hash was filled; fixed kit to canonical alpha35 SHA/740585bytes. Product/package bytes are unchanged. Complete Git bundle verification passed; first source-export blob comparison exposed Windows text=auto CRLF export despite core.autocrlf=false, not lost source. Exact LF archive correction/reverification and new final-HEAD CI follow. These failed checks are retained; publication has not started.

20:24 UTC: alpha35 physical acceptance complete within the defined router-probed IPv4 scope. Complete cycle PASS124.94s (plus two alpha34 cycles126.98/131.47s), Start64.08s; actual native SIGKILL recovery PASS20.21s, monitor unchanged/profiles off/guard absent/budget+certificate unchanged/revision revoked. Actual Stop during STARTING PASS: ACK1.33s, cleanup10.35s, stale Start rejected. Actual30sample auto_live RPC run PASS. Actual pinned HTTPS dashboard/styles equal canonical IPK. Reboot final23checks PASS at121s uptime; initial45s check failed only missing services, both services observed running by92s. Auto and clients remain off, original policy/preparation retained. Final backup/recovery and exact release-HEAD CI/publication in progress. See release notes and Russian quick start; deferred eleven-item backlog remains explicitly open.

20:15 UTC: second alpha34 cycle PASS131.47seconds in the same continuous session; ordinary Stop PASS16.1seconds, original owned profiles off and guard absent. Alpha35 exact sourcebeabca86d7a7106102284338a3d5a170e9b21709 complete CI PASS681 app/107QA per runtime/34UI; reproducible740585bytes SHA220261bbf1e876c2ca0429b491ab79b7a4f0d1e7ef3bfb34185370d484e07465. Fresh189-entry encrypted/decrypt-verified backup; actual install80files/modes/protected configurations PASS. Actual alpha35 Start PASS64.1seconds; its full fault/return test is RUNNING. Desktop and actual390px iframe synthetic graph layouts visually checked, readable/no cropped graph. Live read-only RPC captured reserve and primary at roughly2-3sec; collector exceeded its200sec transport budget before80iterations finished, so its overall run is PARTIAL, not PASS. Native crash recovery, Stop during startup, final receipts/publication remain pending.

20:08 UTC: first complete alpha34 continuous Auto hardware cycle PASS126.98seconds. Actual120sec bounded WG packet-drop -> SOURCE-FAILED/APPLYING -> COMMITTED on OpenVPN -> fault removal -> automatic original WG return/ROLLED-BACK -> OBSERVING. Both paths passed DNS/two HTTPS and matched their distinct pre-recorded exit hashes; actual rule order checked at reserve and restored primary. Proof scope router-probed-ipv4, external LAN false. Second cycle in the same session RUNNING; alpha35 full CI RUNNING. No broad completion or final release claim yet. Private pair34-failover-01.jsonl and receipt bind exact script/output/device.

20:05 UTC: alpha34 source86bd49beddaa1a1174e2b36a1b8af53fe0df4708 full CI PASS681 app/107QA per runtime,34UI; reproducible740412-byte IPK SHA0743c1312fd7d53b0de19dddf3aa4ff8aba60a2ab8520f5adf8eabce506fa00e installed80files/modes/protected configurations PASS. Exact derived-process via/mark synchronization passed actual isolated vendor Lua/UCI. Cold Start failed twice: the second run captured seven server AUTH_FAILED replies and repeated OpenVPN teardown/retry, while shared locks/queues were free. Owner confirms unchanged credentials. A later unchanged-config Start passed56.1s; transient authentication cause remains UNKNOWN. Actual failover/return with the atomic fix is RUNNING, not yet PASS. Source alpha35 also suppresses unrelated Wi-Fi setup via stock ifup -w (not a wait option), records RESTORING before automatic return, and adapts graph labels/width for small screens. Full CI/install of alpha35 pending. Public alpha27 remains the released baseline.

Latest actual state: alpha32 installed,80 files/modes and protected configs verified; new678 app/107QA per runtime/34UI matrix PASS. Actual Start58.1seconds PASS and Stop14.1seconds PASS, both owned profiles restored off/guard absent. Actual fault switching is NOT accepted: precise refusal POLICY-IDENTITY-CHANGED, rolled back; new module identity handling kept the session alive to observe/retry instead of the prior daemon crash. Synthetic isolated UCI reorder on actual vendor libuci PASS. Alpha33 source33df1ca1bedf792591331b011dc50a58ce243a7d adds sanitized apply failure location/derived-rule context; full CI/actual diagnosis pending. Graph is installed but actual visual/live acceptance remains pending. Do not report Auto ready yet.

18:11 UTC checkpoint: alpha31 source8282011dd2e1d88db696eb4e14f7e4b31fef35f9 full CI PASS (675 app+107QA per runtime/33UI), exact736330-byte IPK SHA4e624cb7938d0f6413274d0819cc03a8b332be87dd1308df42e468fed2d3a848 installed on actual MT3000;79 files/modes and protected configs verified. Fresh187-entry encrypted recovery export verified. Thirty-minute read-only resource baseline60samples/0failures completed; I/O counters unavailable in vendor kernel. Auto remains off pending physical Start/fault/return/Stop acceptance. See [pair operations](../PAIR-AUTO-OPERATIONS-2026-10-22.md). Older WIP state below is chronological history.

Immediate owner priority: usable two-channel Auto today, target 23:00 Europe/Berlin. The broader eleven-item list is retained but secondary. New source adds explicit continuous-pair control with automatic existing-profile startup, bounded per-transition native leases, a persistent rolling attempt budget, Stop/restart ownership recovery and router-probed-ipv4 scope. It never creates an external-LAN certificate. Twelve focused Linux tests and Auto/readiness Node tests pass; complete matrix, installation and physical acceptance are pending. Alpha27 remains installed and Auto off. Do not report the new mode working before actual acceptance.

Owner explicitly approved all eleven router-only completion items after alpha27 publication. Follow [the active completion matrix](ROUTER-ONLY-COMPLETION-2026-10-22.md). Fresh work starts at 1ec7bc5574c828a10d17d0b6c15536219605243f; alpha27 remains the immutable released baseline. Refresh identity/recovery before device writes. Preserve Windows networking and primary MT6000. External-LAN certification is excluded. Old completion/pause entries below describe earlier windows.

# Dual release publication — 22 October 2026

Owner requested release publication in both GitHub and primary Gitea. v0.9.0-alpha27 is now a published prerelease in both services, with the 728294-byte IPK independently downloaded and verified against SHA256 5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6. Each release includes its SHA256 text attachment. GitHub's checksum file uses CRLF and Gitea's uses LF; both name the same package and hash. No existing release or tag was overwritten.

Gitea and local Git canonical tag point to de9ab00a007816f5b723e112c3c75c2d393a71af; immutable GitHub tag points to a05018bee9c61379a140f2a59aaa2c8a03dbe686. Their complete source trees are identical. Main already contains the release in both histories; later documentation commits preserve the released package. See [publication receipt](../../qa/ALPHA27-PUBLICATION.json) and [release notes](../../releases/v0.9.0-alpha27.md). The temporary local release token was removed and its absence verified after Gitea refused API self-revocation; no secret was persisted. Only documentation bookkeeping follows; product, router and acceptance scope are unchanged.

# COMPLETE — alpha27 release and main verification, 22 October 2026

Released v0.9.0-alpha27: GitHub release/tag/source snapshot a05018bee9c61379a140f2a59aaa2c8a03dbe686; canonical Gitea main de9ab00a007816f5b723e112c3c75c2d393a71af verified through protected Gitflow checks and normal FF save. Public main/local main verified. Release IPK and checksum independently downloaded and checked; package SHA5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6,728294bytes. Later documentation-only main snapshots may descend from the release object without changing this package.

Actual MT3000 alpha27 acceptance completed:655 app+107 QA per runtime/33 Node UI,40 lab checks; actual calibration/Auto fault/reserve/recovery/Stop/manual operations, active native SIGKILL recovery, monitor off/on, final persistent reboot19 checks. Installed77 payload files and served HTTPS assets match canonical IPK. Auto and both clients off after tests, monitor/native supervisor running, default external-lan scope, no fault/guard/fixture. Native packet decisions were verified with ordinary router-hosted IPv4 client; external Windows forwarding remains unverified by the owner's no-host-changes instruction. No external certificate, MT6000 hardware requalification, six-hour traffic soak or power-cut acceptance is claimed.

Final187-entry encrypted/DPAPI-decrypt-read-verified configuration backup includes own state/preserved SFE autoload. Complete-history18MB Git bundle verification PASS. All882 source export files match canonical Git blobs after the configured Windows CRLF export normalization (405 text files); executable modes verified. The earlier tar assertion was a normalization mismatch, not lost files. Recovery receipts are private/acceptance-20261022/final-recovery-receipt.json and final-alpha27-config.receipt.json.

Physical work ended within the six-hour window; only Git publication bookkeeping followed. No automatic router/VM/fixture tests should resume. Old entries below are history. The owner can start a fresh task explicitly.

# Published release checkpoint — 22 October, 15:57 UTC

GitHub main and immutable v0.9.0-alpha27 are published at a05018bee9c61379a140f2a59aaa2c8a03dbe686. Exact canonical source de9ab00a007816f5b723e112c3c75c2d393a71af, final CI PASS, downloaded IPK/checksum verified SHA5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6. Local main fast-forward verified to the same public commit. Canonical source and publication branches saved to primary Gitea. Protected Gitea default-main synchronization is still finalizing after a local clone/working-system error; no force/protection bypass.

Physical six-hour window is CLOSED as completed testing, not an owner pause. No automated tests/fixtures/router changes should resume. MT3000 alpha27 installed; native happy path/fault/manual and active supervisor crash recovery passed in hosted IPv4 scope; monitor off/on and corrected reboot19 checks passed. Final Auto off, selected clients disabled/auto0, stock arbitration boot disabled, SFE autoload preserved/masked, HNAT disabled, services monitoring. Windows and primary MT6000 unchanged. External LAN remains unverified and hosted certificate cannot satisfy external scope.

Final supported backup187 entries encrypted and DPAPI-decrypt/read verified; own state and preserved autoload explicitly included. Complete-history source bundle verification PASS. Source tar export normalization verification is being reconciled; do not claim exact blob restoration from that tar yet. Git-only final bookkeeping remains; old entries below are history.

# Latest status — 22 October 2026, 15:33 UTC

Final product:0.9.0-alpha27-1, dashboard69/ui46. Exact CI655 app+107 QA per runtime/33 UI PASS; canonical728294-byte IPK SHA5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6 installed and77 payload files/modes plus actual HTTPS assets verified. Native calibration/Auto source fault/reserve/automatic return/Stop/manual reserve and return PASS in hosted IPv4 scope. Actual alpha27 SIGKILL during WAIT-CLIENT recovered without lease/quota reset or false certificate; original DNS/HTTPS passed. Monitor off/on5 checks PASS. Final main publication/ref/download verification is the remaining release step.

After reboot, stock clients came up and SFE core reloaded while app Auto stayed disabled. Authoritative SFE cause: /etc/modules.d/09-shortcut-fe, not shortcut-fe init (which skips when HNAT0). Under the explicit dedicated-router repair authority, preserved that exact file outside autoload, disabled competing stock VPN/SFE boot entries, set only selected clients disabled1/auto0 and used normal non-force accelerator stop/unload. Second reboot: all19 final checks PASS, both clients/Auto off, no guard/fault/fixture, source policy preserved, monitor/native supervisor running, HNAT disabled/SFE absent. See operations log for exact hashes/undo.

External Windows forwarding remains UNVERIFIED: owner refused host route/NIC changes. Hosted evidence is never an external certificate; default scope is external-lan, Auto off after tests. Primary MT6000/host Wi-Fi unchanged. No six-hour traffic soak or physical power-cut claim. Earlier entries below are chronological history, not current blockers.

# Current work — 22 October 2026

Owner resumed completion, full testing and the dedicated GL-MT3000 hardware window. Later instructions require saving critical/long operations to local Git and this current state, publishing the completed release on main, and offering MT6000/MT3000 model selection in setup/settings. This is active work, not a pause. Primary MT6000/host Wi-Fi and Windows network settings remain excluded from changes.

## Verified in this session

- Exact committed source a502a0a59ef1179ff78e1e72d2a5f9dcfe0775b2 passed canonical offline CI on Python 3.9/Lua and Python 3.11/Node. Each runtime ran 631 application and 106 QA tests; 33 Node suites ran on 3.11. Fifteen application Lua skips in 3.11 are covered on 3.9; fifteen QA environment skips in 3.9 are covered on 3.11. Reproducible IPK: 717313 bytes, SHA256 4d26c4a64611908f552d325e1b0712a50d57b1f7349218fa4ff15a3a89154700. Receipt: .git/handoff/ci-a502a0a59ef1179ff78e1e72d2a5f9dcfe0775b2-dcfea2eaef334883900bca2f66687a96.receipt.json.
- Initial cable attempt failed while Ethernet reported Disconnected; after owner confirmation, fresh Ethernet 1Gbps, ping 2/2 and pinned cable-only SSH succeeded. Actual board glinet,mt3000-snand. This supersedes the transient connection failure.
- Actual installed alpha19: all 73 program files/modes match the canonical package. Nine health checks pass: monitor-only, sole monitor instance, native/optional functions off, terms1, CalmB, no transaction/owned guard. Onboarding is still incomplete; no owner wizard choices were fabricated.
- Actual RPC 19/19 pass, including unsupported Auto/manual refusal, Stop/revision/replay/deduplication and no false path confirmation. No real channel transition occurred. Network/wireless/firewall/DHCP/route-policy/app config, kernel route/rule hashes and boot link unchanged.
- Actual monitor SIGTERM/procd recovery 8/8 pass in 7.5s, with fresh status from the replacement process. This is graceful monitor loss, not native transaction recovery/power-loss acceptance.
- Private readiness model now rejects malformed boolean/binding evidence and negative constructor time; 12 tests pass on Python3.9. Runtime witness9 tests pass. Diagnostic queue30 tests pass with root-owned isolated fixtures. The first non-root fixture run failed honestly because ownership validation returned UNVERIFIED. Extended consumer/lab batch stopped at missing /vendor fixture mount; it is incomplete, not PASS.

Private receipts and scripts: private/acceptance-20261022/. No credentials or raw profile configuration belong in Git. Earlier runtime-witness work and history remain in LIMIT-CHECKPOINT-2026-10-21.md.

## Active work and not done

### Checkpoint 09:47 UTC — model selection implemented, release not yet published

- Implemented Automatic/MT6000/MT3000 choice in first-run and Settings aggregate editor, actual hardware display, correct device attribution, reload persistence, backwards-compatible old callers and rejection of a mismatched model in both Python and the final Lua writer. Model preference does not grant controller capability. Native diagnostics also refuse mismatched preferences.
- Versioned WIP is alpha20/dashboard69/ui46. Focused Python3.9/Lua checks38/38 PASS; all33 Node UI suites PASS. Initial UI run stopped at the old diagnostic count39 after adding two explained codes; expected count41 and new request shape were corrected and full run repeated. Exact-commit full CI and canonical alpha20 package are NOT yet done.
- Additional offline checks completed: exact-source vendor consumer3/3, transaction engine9/9 (including200 fault combinations), isolated child process crash20/20, synthetic cascade256series/2048steps with0invariant failures. These are model/container tests, not physical switching.
- Owner now explicitly authorizes all necessary changes and real manual/automatic switches on the dedicated MT3000, and requires documentation plus the existing launch prompt to record prerequisites discovered. Work window is3–4hours; single executor claim until13:45UTC. Other heartbeat threads must defer. No successful physical switching claim is added by this checkpoint.
- Next: fresh encrypted recovery export; complete justified bounded OpenVPN settling/rollback path, physical channel tests with real traffic and application integration; update launch prompt and documentation. Final release/main publication follows final-source validation. Old failed/STOPPED results remain preserved.

### Recovery checkpoint 09:48 UTC

- New pre-switch supported configuration export completed on the actual MT3000:175 archive entries; required configuration/shadow entries and full archive reads verified. AES-GCM encrypt and independently DPAPI-decrypt/read comparison succeeded in memory; no plaintext backup persisted. Encrypted artifact SHA25612f35324594e417f9be08b10368845dac5514636125f9e4578feea0eed3f9938. Private receipt: private/acceptance-20261022/pre-switch-config.receipt.json. This is configuration recovery, not a full-flash/bootloader recovery proof.
- Owner explicitly grants full necessary control/remediation of the dedicated MT3000, including settings changes, switching and persona/error scenarios. Record each obstacle, why it mattered, exact fix and verification in documentation and the existing launch prompt. This supersedes earlier router-only mutation/unsaved-wizard restrictions within this active test window. It does not authorize changes to the primary MT6000/host Wi-Fi/network routes, secret publication or invented acceptance.
- No VPN activation or physical channel switch has occurred in the new session yet; preparation is complete and active trials follow.

### Acceleration checkpoint 09:52 UTC

- Actual MT3000 HNAT was enabled and shortcut_fe loaded. Inspected/pinned stock controls, then ran the exact installed preparation function under the owner's explicit remediation authority. HNAT config0/runtime disabled, SFE core absent;7/7 checks PASS. Protected/app config hashes, monitor-only and disabled clients preserved; management remains accessible. No forced removal or firewall restart. Persistent acceleration setting is intentionally retained for failover tests.
- Observations, mechanism, exact change and verification: [MT3000 operations log](../MT3000-OPERATIONS-2026-10-22.md). Reboot persistence and actual switching still open. Existing launch prompt will be updated with these prerequisites in the next code batch.
- Owner expanded the absence/work window to six hours. Single active interactive executor claim extends to15:55UTC; scheduler threads must defer while it is live. Work is active, not paused.

### Physical WG checkpoint 10:05 UTC

- Two real WG cycles completed: actual interface/fresh handshake,17 samples each, unchanged safety limits, independent cleanup/stock boot restoration PASS at about42s.19 isolated updated hash/version-pin regressions PASS. New4check parser/socket binding suite PASS. Acceleration remains disabled; fresh post-trial kernel/queue readback is clean.
- Physical Windows cable DNS/HTTPS did NOT pass. Synchronized second trial repeatedly returned TCP10051 and DNS timeout while router handshake was fresh. Preserve this as a real datapath failure, distinct from successful interface lifecycle/cleanup. Host Ethernet gateway exists and no Windows routes/NIC settings were changed.
- Next actual diagnostic must capture active marked route tables/DNS ports/counters; post-stop blackhole/2153 redirect alone cannot explain an active failure. Detailed evidence and interpretation are in the operations log. No real app manual/Auto acceptance yet. Product remains committed alpha20 WIP; installed device remains alpha19 monitor-only.

### Active-path / client prerequisite checkpoint 10:26 UTC

- Third real WG cycle: active route-get confirms marked LAN traffic chooses wgclient1/table1001; per-policy DNS listeners exist. Independent cleanup PASS; Windows client data still FAIL. Ethernet IgnoreDefaultRoutes is enabled; bound public Find-NetRoute returns1231. Owner explicitly REFUSED temporary host routes. The prepared route plan was Plan-only and never executed. Keep Windows network unchanged.
- Fixed the public LAN helper's hidden route writes (including former CheckOnly mutation): sockets now bind interface/source, HTTPS uses validated TLS and total deadlines, no New/Remove-NetRoute. Added read-only ProbeOnly and clearer route refusal. Native PowerShell self-tests, replay/DNS parsing and compiled HTTPS scope rejection PASS. External data acceptance is still not established.
- Updated the existing installation prompt, continuation prompt and helper documentation with both models, encrypted recovery, actual acceleration/FW3/queue requirements and host/hosted-witness boundaries. Code is alpha21 WIP; all33 Node UI suites and native PowerShell helper self-tests PASS. Final exact-commit CI/package/release remain pending; installed alpha19 is unchanged.
- Next: owned MT3000 namespace/veth forwarding client and cleanup, bounded OpenVPN lifecycle, reviewed real manual/Auto adapter. Hosted evidence must never be relabelled as an external-LAN certificate.

### Namespace lifecycle checkpoint 10:38 UTC

- Implemented lab/mt3000_lan_fixture.py;10 isolated scope/identity/cleanup regressions PASS. Exact physical board/subnet plus DHCP/reservation/lease/ARP checks passed. No host changes or existing VPN/profile edits.
- Actual45s MT3000 fixture: namespace/veth created, isolated client pinged LAN gateway, guardian cleanup PASS. Independent post-cleanup6/6 readback PASS: namespace/veth/active pointer absent, original bridge MAC/ifindex preserved. Live inspection arrived after expiry and remains INCOMPLETE. This proves fixture lifecycle/management preservation only, not forwarded DNS/HTTPS, process-loss recovery or external-LAN safety.
- Next: parent/guardian process-loss cleanup, then real VPN data through the hosted ordinary-LAN client and MT3000 adapter integration. No app Auto/manual transition has passed yet.

### Fixture owner-loss checkpoint 10:41 UTC

- Actual exact-owner SIGKILL test PASS: fresh live source/PID/start/namespace/MAC checks preceded the single owned-process kill. Expected foreground/controller exit=-1 retained. Independent guardian cleanup then independently verified7/7 PASS, including resource absence and unchanged bridge MAC/index. During active fixture memory208604KiB remained available.
- Added bounded reciprocal parent recovery for guardian death/stall; physical guardian-loss/stall validation is pending next. Native/Auto remains off and neither VPN was started in these fixture-only faults. Do not turn this result into native transaction or external-LAN acceptance.

### Fixture guardian-loss checkpoint 10:42 UTC

- Actual exact-guardian SIGKILL PASS: fresh PID/start/cmdline/source/namespace checks, then only that owned process killed. Live parent performed reciprocal cleanup; independent8/8 verification PASS including parent_recovery=true and unchanged bridge MAC/index. Evidence namespace-guardian-loss*. Foreground controller returned0 only for confirmed fixture cleanup; no data/switch PASS is implied.
- Next: hosted client DNS/HTTPS during real VPN startup, then OpenVPN lifecycle/actual app adapter. Both current VPN clients remain disabled outside bounded trials; native/Auto is still off.

### Combined data / startup-model checkpoint 11:03 UTC

- First combined hosted-client/WG run PARTIAL: old aggregate guard aborted7.724s after1→3→4 worker counts, disabled confirmed8.030s. Hosted probes ran later with no live tunnel, so they are NOT active-path failure/success proof. WG and fixture cleanup PASS plus independent6/6 cleanup/bridge verification PASS. Source/raw results and assessment retained in wg-namespace-d34d6998.
- Added ordinary unmarked namespace DNS/HTTPS client with fresh namespace/route/MAC/source and root epoch checks. It always states external_lan_verified=false/native_certificate=false. Collector explicitly reports absent tunnel; host driver now returns PARTIAL on missing data/forward acceptance.
- Added separate bounded startup-work model: known fresh worker identities/roles, reload queues, strict budgets/progress/quiet generation, unchanged hard fault cutoffs. All36 lab unit tests PASS (13 startup reducer scenarios). Model is NOT installed or physically integrated yet; ceilings are diagnostic engineering choices, no calibrated/production claim.
- Next: wire this reviewed-in-code model into a separately frozen bounded WG/OV test without changing independent25/30s actor/cleanup leases, then obtain actual in-window data and fix observed router faults. Native app/manual/Auto and final release remain incomplete.

### Progress-observer integration checkpoint 11:12 UTC

- New frozen hardware observer refused an unmatched startup worker at2.297s; this is PARTIAL, not successful forward/data operation. Both cleanup actors PASS and independent6/6 cleanup/bridge verification PASS. Hosted probes correctly report inactive tunnel. Raw evidence retained in wg-namespace-ea909701.
- Added allowlisted classification diagnosis (PID/start/kind/known-path booleans; no raw argv/env/profile).37 lab unit checks +6 integrated observer checks PASS. Guardian/cleanup/parent/dispatch/config-guard AST identity is verified against the prior harness;25s actor/30s cleanup/15s quiet unchanged.
- Next: identify the precise legitimate/unsafe unmatched worker, then correct only a source-supported classifier contract. Do not silently whitelist arbitrary work. Installed app is still alpha19 monitor-only, source alpha21 WIP; no native/manual/Auto or data acceptance yet.

### Actual hosted HTTPS checkpoint 11:22 UTC

- Narrow classifier correction now verifies relative netifd invocation CWD, live process identity and19 current vendor source hashes; arbitrary inline work still refuses.38 lab +6 integrated observer checks PASS.
- Actual wg-namespace-726e30d8 reached LINK-SETTLED with unchanged independent timer/cleanup. Hosted ordinary-LAN client twice passed2/2HTTPS while tunnel present and root epoch unchanged. DNS to LAN gateway still timed out twice: overall PARTIAL, not full data acceptance/certification. Independent6/6 cleanup/bridge verification PASS; both fixture and WG cleanup actors PASS.
- Next concrete blocker: stock DNS dispatcher/leak filter, with HTTPS forwarding now independently distinguished. Read-only source/config-key/service-schema inspection is underway. No Windows changes. App native/manual/Auto is still unimplemented for this target, installed19 monitor-only; final release remains pending.

### DNS-owner repair checkpoint 11:45 UTC

- Confirmed stale dnsmasq upstream127.0.0.1#3053 for all instances with no listener. Kernel rule resync was unchanged and did not fix it. Stock DNS API explicitly refused DNS_BUSY because AdGuardHome was configured enabled while DNS/process were inactive.
- Verified/pinned controls; disabled only inactive adguardhome owner, removed only its nonrunning procd record and saved auto DNS with override_vpn=false via stock API, parameters only in memory. Intended flag readback PASS; network/wireless/firewall/route-policy/app config bytes unchanged. Expected changed files: adguardhome,gl-dns-v2,dhcp. Actual data retest PENDING; do not mark DNS PASS yet.
- Evidence dns-owner-repair.json; prior failed/unchanged requests retained. Next: repeat hosted WG data under the now corrected stock DNS configuration, then proceed to OV and actual app switching. No Windows changes or external-LAN certificate.

### Verified DNS recovery checkpoint 11:56 UTC

- Actual wg-namespace-b7dc19b5 PASS within router-hosted forwarding scope: LINK-SETTLED, two real DNS+2/2HTTPS measurements, same exit hash, live tunnel and stable expanded DNS/network epoch. WG and fixture cleanup PASS; independent6/6 cleanup/bridge verification PASS. This closes the observed WG DNS-owner fault; no external-LAN/native certificate or actual app switch is implied.
- Existing UI installation prompt and continuation prompt updated with actual DNS_BUSY/inactive-owner diagnosis, correct remediation and preservation of working DNS owners.33 Node UI suites PASS. New source checkpoint is alpha22 WIP, device remains alpha19 monitor-only. Full final CI/canonical package/release still pending.
- Next: current PID-safe OpenVPN cold start/data/cleanup, then warm pair and application manual/Auto transitions. Windows remains unchanged; prior failures retained.

### OV preparation checkpoint 12:01 UTC

- Fresh exact dead OV PID residue quarantined without process kill: inode4450366/numeric7646 absent process;4/4 preservation checks PASS,8 config hashes unchanged and both VPNs disabled. Source script is single-inode/single-use. Evidence ov-current-pid-quarantine.json.
- Frozen OV progress wrapper6/6 unit checks PASS; guardian/cleanup/owned-probe cutoff/dispatch functions are AST-identical to reviewed old harness,25s actor/30s cleanup unchanged. Next real cold trial proves only marked router-originated OV lifecycle/data. Ordinary LAN fallback remains blocked by WG-first Kill Switch until an actual guarded policy transition is implemented/tested.

### OV first progress / next prep checkpoint 12:14 UTC

- Actual OV LINK-SETTLED and cleanup/boot restoration PASS45.2s; independent both-links-absent/queues0 readback PASS. Early-TLS marked probe hadHTTPS2 but DNSfalse while configuration work still ran, so channel data remains PARTIAL.
- Probe timing now requires quiet LINK-SETTLED, retaining25/30s guardian/cleanup;7 wrapper regressions PASS. Fresh new residue inode4869998/PID26992 was verified dead and quarantined without process kill/config changes. Next bounded trial verifies this timing fix; no app policy transition claimed yet.

1. Add validated model preference (automatic/MT6000/MT3000) to first-run setup and settings, reporting actual hardware separately. Preserve strict platform/native guards, existing installation choices and optional functions off.
2. Complete required focused/full/generated-UI/package checks on the final source; version/bundle exact code identity. Publish reviewed release to main with exact-source CI and downloaded artifact/ref verification. Owner explicitly authorized this publication; it has not happened yet.
3. MT3000 real manual/Auto adapter remains incomplete. Actual refusal includes unsupported board, monitor-only, unconfigured source/reserve, unverified accelerators and missing bounded LAN trial. Unit/RPC refusal passes do not close these blockers.
4. OpenVPN cold-start queue abort remains unresolved. Empty queues/connected flags do not prove reload success. Do not relax growth guard or repeat identical trials solely to obtain PASS. Current read-only witness is not installed or an apply permit.
5. Finish extended isolated consumer/lab tests with correct exact-source mount, and investigate a cable-bound LAN data witness without Windows route/NIC changes. Do not issue a native certificate from router-originated traffic.
6. After each critical/long result update this file and save a local Git checkpoint. Preserve failed runs, no private histories/secrets in publication. Final physical state/readback and restore-verified current archive remain required.

### OV second progress checkpoint 12:25 UTC

- Settled-only probe correctly did not run: actual trial refused STARTUP-WORK-UNVERIFIED after7 samples/9.266s. Both cleanup actors PASS33.8s; independent links-absent/queues0 readback PASS. This is PARTIAL, not OV data or app acceptance.
- Fresh dead residue inode4900341/PID7599 quarantined without process kill/config changes;4 preservation checks PASS. Added allowlisted service-action diagnosis without raw argv; next run will distinguish the exact rejected stock firewall action. Independent25/30s leases and guard remain unchanged.

### OV measured / pair preparation checkpoint 12:33 UTC

- Third bounded cold OV trial reached LINK-SETTLED and measured DNS=true/HTTPS2 with the same independent25/30s lease/cleanup. Both cleanup actors PASS44.9s; independent current readback confirms links absent and queues0. Evidence ov-physical-progress-03.jsonl, pre-pair-readiness.json. This closes marked router-originated OV data only; no ordinary LAN/app/Auto claim.
- Prepared separate two-warm-channel engineering qualification with independent180s cleanup actor, typed/owned command GO gate, stable normalized configuration identity, two-state policy order guard, bounded nft guard and exact original boot/client restoration. Source is private/uninstalled; new physical pair run is pending. Existing unsupported native guard is unchanged.

### Pair refusal / exact recovery checkpoint 12:38 UTC

- First pair probe refused CONFIG-IDENTITY during WG start; independent actor also correctly HOLD on unexpected config. No OV or policy swap occurred. Immediate encrypted-before/after comparison in memory identified only network.WG.disabled and four firewall WG-zone metadata fields.
- Separate exact-current-network-hash recovery restored original network bytes, stopped only owned WG, verified15s quiet/both links absent and restored stock boot link: PASS. Evidence pair01-recovered.json; no Windows changes.
- Pinned stock gl_block_wan_access_exit and its already-pinned RTP/route-policy callers prove exact automatic metadata declaration/removal (wan_like1/managed1/exit_id=interface/bridge_reject0, no device/before rule). Pair observer now normalizes only that complete exact record on the two selected zones; malformed/partial/other-zone changes still refuse. No global firewall restart or metadata deletion was used. Next pair rerun is pending.

### Pair02 checkpoint 12:42 UTC

- Narrow metadata identity regressions6/6 PASS; pair reached actual WG settling and began OV. Unknown FW3 work at26.05s again caused refusal; no policy exchange or data success claimed. Independent pair cleanup PASS51.94s, original policy/both links/boot/nft state restored. Separate readback confirms links absent/queues0 and dead PID residue.
- Added allowlisted FW3 argument-shape diagnosis (unknown tokens expose length only), not a classifier exception. Next run will identify the exact stock child shape; no safety threshold relaxed.

### Pair03 / provider refusal checkpoint 12:46 UTC

- Pair03 did not settle within its25s startup observation; independent cleanup PASS63.35s, exact policy/both links/boot/nft restoration. Separate readback confirms links absent/queues0/no stale PID. No manual/Auto switch occurred.
- Safe coded logread inspection found3 AUTH_FAILED server replies and corresponding retries during this pair run; prior isolated OV succeeded. The reason (rate/session/credentials/other) is UNKNOWN; no claim of provider limit or network fault. Stop repeated authentication retries while diagnosing and running offline checks. Pair02 intermittent FW3 unknown shape remains unresolved and preserved.
- Pre-pair supported backup175 entries encrypted and DPAPI-decrypt/read verified, plaintext never persisted; SHA5b672c001df127e5e4c6097fb83ce0fbc147d702ed2fab1621b9a01fa0226f6a.

### Pair04 / recovery / CI diagnostic checkpoint 12:55 UTC

- OV-first pair startup reached both channels settled and actual root DNS/2HTTPS on both; ordinary hosted client twice passed DNS/2HTTPS through WG with stable exit/epoch. No claim that startup order caused recovery: prior AUTH_FAILED reason remains UNKNOWN.
- Engineering callback then rejected its own staged UCI reorder before commit, leaving only cfg0692bd .type=4 in libuci delta; cleanup HOLD. Exact delta and unchanged policy file SHA verified independently. Reverted only this one verified own order marker, then guarded recovery restored original policy, both links absent, boot link and nft absence: PASS. Evidence pair04-pending-index.json / pair04-recovered.jsonl.
- Pair observer now accepts only staged order markers4/5 on the exact two selected rule sections with unchanged semantic policy and a two-state effective order; actor reverts only these verified own staged markers before cleanup. Forward reorder commands now also use the shared lease/typed command deadline. No foreign option delta is allowed.
- Full alpha22 exact-commit CI failed in QA before a receipt, so NOT PASS. Added exact failing command/exit diagnostics; found and corrected a separate import side effect: protocol lab installed a global20s faulthandler timer on import. New import regression pending full run; no test timeout/memory/safety threshold was relaxed.

### Full CI / exact query / Pair05 recovery checkpoint 13:02 UTC

- Exact source905c1b73a7cd80148824e6fb7e0b576de82dfef5 full CI PASS:636 application+107 QA per runtime,33 Node UI suites on3.11;3.11 Lua skips covered by3.9 (app0 skips),3.9 QA15 environment skips covered by3.11. Identical722340-byte alpha22 IPK SHA5ced27af123dbcbd0145408074122495c9a611dff960952b6c94fb517ee2b896. Receipt .git/handoff/ci-905c1b73a7cd80148824e6fb7e0b576de82dfef5-4ec246ef62ef4278a95b88debe89548d.receipt.json. No release/publication yet.
- Actual unknown FW3 child identified as exact /bin/sh /etc/rc.common /etc/init.d/firewall enabled. Source-pinned rc.common SHAebeeedc132a75942ce876465e4636a75f745e468c573fdf9ad058e57e58a0341 proves this checks a startup symlink only. Classifier now omits only this exact read-only tuple; enable/disable/extra args still refuse.39 lab tests PASS.
- Pair05 stopped on that query before WG start; actor HOLD on down of never-registered WG. Separate corrected cleanup stops only active OV and explicitly handles proven absent runtime+kernel for WG. Recovery PASS, both links/policy/boot/nft restored. Previous failed results retained; pair policy exchange is still pending.8 private order/identity guards PASS.

### Derived process binding / Pair06 recovery checkpoint 13:27 UTC

- Pair06 reached actual guarded policy application, then correctly stopped on unmodelled stock gl_process_vpn via/mark updates. No post-switch client data success claimed. Pinned RTP handle_always_vpn_policy sets this rule from the first enabled VPN rule and set_mark_from_via commits its mark. Encrypted comparison in memory verified only two client flags, exact BWA metadata, generic order and that derived process binding.
- Separate pinned/exact-file recovery restored the full original semantic policy hash/order; both clients then disabled and links removed. Earlier recovery stages/strict assertions were incomplete and are retained. Final independent15s quiet cleanup PASS at13:22UTC: original policy semantics/order, both clients disabled/links absent, stock boot restored, own nft absent and fixture absent (pair06-cleanup-finished.jsonl). Do not claim original raw network bytes until semantic export comparison; UCI serialization can change.
- Product WIP now binds the exact two selected interface/mark pairs into policy hash and journal. Only the known gl_process_vpn via/mark pair is derived; all other fields and foreign interfaces/marks remain identity guarded. Recovery reloads this exact journal context; post-apply requires the deterministic first enabled VPN rule binding.7 targeted Python3.9 tests PASS. Full new-source CI and physical policy data/recovery remain pending.

### Alpha23 CI / Pair07 checkpoint 13:40 UTC

- Full exact-source e234461103bcab83ba1697afbe77097eabe727ae CI PASS:643 app tests per runtime plus107 QA,33 Node UI suites; reproducible alpha23 IPK SHA57e95428d14c93269bc81a01da5de88f7e30cb8293be833c3fc9a8ad83ca1838 (723757bytes). Receipt .git/handoff/ci-e234461103bcab83ba1697afbe77097eabe727ae-3e500c186ae644efbb0219bb8445c4be.receipt.json. Initial direct app-only invocation had one missing /lab bind-mount import error; exact immutable full CI includes the lab and passed.
- Pair07 used frozen new policy methods in RAM, installed app remains19 monitor-only. Own config/hash guards survived policy application; post-policy observer refused stock DNSMASQ restart, not a data/Auto PASS. Independent automatic cleanup PASS95.18s; separate links absent/queues0 readback PASS.
- Source-pinned RTP line836 directly starts dnsmasq restart in background even with not_reload_network. Added explicit post-policy-only DNS restart contract, exact argv and DNS-init source pin; cold defaults/network/firewall restarts remain refused and all original timing/memory/process budgets unchanged.40 lab tests PASS. Next physical rerun must match actual hosted target exit to a fresh marked OV measurement and prove WG return, not merely distinct IP.

### Physical policy round trip PASS / new native integration WIP, 14:07 UTC

- Pair08 PASS: frozen alpha23 policy methods executed actual WG→OV→WG exchange. Six ordinary unmarked hosted-client measurements passed DNS+2HTTPS (two each phase); reserve exit exactly matched fresh marked OV root measurement and was distinct from source, return matched original WG. Original policy, both clients disabled/links absent, boot and own nft removal PASS111.9s. Separate fixture/bridge6 checks PASS. This is router-hosted forwarding, not external LAN certification or an installed native daemon test.
- New strict MT3000 live platform profile readback PASS with no blockers: glinet,mt3000-snand / GL.iNet GL-MT3000 / mediatek/mt7981 /5.4.211/aarch64 /4.11.0, exact stock hashes/FW3/include and quiet workers. It grants no rights by itself. Actual controller still installed alpha19 monitor-only.
- Source now adds MT3000 native service eligibility plus live source/FW3/worker guards (selected WG1/OV1 only), post-RTP quiet waiting, separate external-lan vs router-hosted-ipv4 confirmation/certificate/history/status, explicit test-only UI label, and nonce/revision-bound native_trial_start. A fresh private calibration can supersede an old Stop without erasing it or claiming a certificate; normal Auto Start still requires one. Public helper stays native_enabled0 and requests only RAM intent after TEST.
- Focused platform/proof/control/deployment tests and Windows helper SelfTest PASS; full new-source CI, package/install/served UI, real native calibration/manual/Auto/fault tests and main release remain pending. Existing AI prompt updated with exact prerequisites, derived process rule, asynchronous DNS and scoped proof limits.

### Native integration CI correction 14:16 UTC

- Alpha24 exact CI failed at Node auto blocker explanation coverage for newly exposed EXISTING-TUNNEL-BINDING-UNVERIFIED; no PASS receipt issued. Added plain EN/RU explanations for every additional MT3000 platform refusal. Fault-injection eligibility now also requires matching native/certificate proof scope, preventing hosted proof reuse in external mode. New final CI follows this checkpoint. Router remains19 monitor-only, both VPNs/fixture/guards restored after Pair08.

### UI coverage correction / canonical build preparation 14:26 UTC

- Alpha25 exact CI stopped at readable-name coverage after blocker explanations passed. Added bilingual short names for the same verified platform codes; all33 Node UI suites then PASS together. No alpha25 PASS receipt is claimed. Explicit fresh private calibration also now distinguishes an exhausted older bounded window from the current one; nonce replay and current-window quota still refuse. Next exact CI/canonical artifact covers the complete source.

### Installed native controller acceptance PASS, 14:49 UTC

- Alpha26 full exact CI PASS:655 app+107 QA per runtime,33 Node UI suites, complementary environment skips covered. Canonical Linux IPK727939bytes/SHA8ad6eda5287135b3b3b60e292d80b120da3cd03c984319a0a1d51c70e59bd624 matched both matrices.
- Actual install PASS opkg0,77 payload files/modes exact,7 protected config files byte-unchanged. Fresh175-entry supported backup encrypted and DPAPI-decrypt/read verified. Actual HTTPS dashboard69.js/ui46.css through pinned cable/certificate match canonical package exactly.
- Actual installed native_pilot01 PASS (458.1s): real native calibration with fresh scoped confirmation, actual bounded WG packet-drop fault, Auto reserve COMMITTED plus ordinary hosted DNS/2HTTPS, automatic primary recovery plus data, Stop, manual reserve held/confirmed plus data, manual primary return plus original WG exit. Wrong revision and manual-while-Auto refused. Shared quota used3 attempts; no external-LAN certificate claimed.
- Independent outer cleanup reports original policy restored, both links absent, stock boot restored, own nft removed, Auto stopped, default external scope restored and monitor restarted. Hosted certificate cannot satisfy default external mode. Separate final kernel/service readback and boot test follow.
- Observed minor status issue: after transient VENDOR-WORKER-BUSY clears, COMMITTED reused the prior warning list. Fixed only that stale list when current diagnostics are clear. Kit now accepts both actual boards and does not log private trial/preparation nonces or duplicate a token-bearing conffile in plaintext. Existing launch prompt records PID ownership repair. Final source CI/artifact/version/install and main publication pending after this checkpoint.

### Final installed/crash/boot checkpoint 15:33 UTC

- Alpha27 exact cde035f5727a482e670682696a083cdd71c904e0 CI PASS; installed77 payload files/modes and HTTPS assets match canonical SHA5357b80...acad6. New supported backup encrypted and DPAPI-decrypt/read verified.
- native-crash-27 PASS: own source/PID identity verified before SIGKILL in WAIT-CLIENT; procd respawned1770→9153, journal rolled back with SUPERVISOR-RECOVERY, ordinary hosted DNS/2HTTPS restored, monotonic lease unchanged, quota1 preserved, certificate bytes unchanged, duplicate nonce refused. Cleanup PASS.
- Actual monitor off/on5 checks PASS, protected config hashes unchanged and Auto not started.
- First reboot is PARTIAL for original all-off/acceleration state: app Auto stayed off, but stock profiles came up and SFE core loaded. SFE source identified exactly as /etc/modules.d/09-shortcut-fe SHA8aad0842bbf4de46c61719fba3237d3127cee632f4312807ff3b591d388b2f49. The init shortcut-fe source itself exits with HNAT0. Do not attribute the module load to that init action.
- Persistent dedicated-router fix: mask exact autoload file at /etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe; disable vpn-client/shortcut-fe boot entries, only WG1/OV1 disabled1/auto0, normal non-force accelerator preparation. Combined fix verified by second actual reboot:19 final checks PASS. HNAT remains0/runtime disabled, SFE absent; no owner PC/primary router changes. Current readback post-reboot27-persistent-state.json.
