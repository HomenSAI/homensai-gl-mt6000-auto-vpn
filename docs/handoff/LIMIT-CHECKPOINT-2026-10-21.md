<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../CURRENT-STATUS.md) · [documentation index](../DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Active checkpoint before possible usage limit - 21 October 2026

SINGLE ACTIVE EXECUTOR 22 October 09:41–15:55 UTC: owner-authorized interactive thread 01a162e9-6703-7b41-8334-561a48debe2c is completing release/model/hardware work. Read private/ACTIVE-EXECUTOR.local.json and docs/handoff/CURRENT.md. Other heartbeat threads MUST DEFER without edits, tests, agents or router calls while the claim is live. This prevents overlapping executors; it is not an owner pause.

The owner requests saving current state immediately, continuing work, and a15-minute recurring attempt to resume useful work after limits reset. This is NOT a pause. A scheduler cannot reset quota; scheduler setup/verification is a separate pending action until a real receipt exists. Do not claim a timer was created from this document alone. Avoid overlapping executors or repeating physical mutations merely to check model availability.

## Current source and installed state

- Local source HEAD6be804c2fce9f2c680c562e7572aa1254ecd42cb, feature/checkpoint-alpha17-wip-20261020; clean product worktree at this checkpoint before this new document. Alpha19 canonical IPK717313bytes, SHA2564d26c4a64611908f552d325e1b0712a50d57b1f7349218fa4ff15a3a89154700.
- Exact-source CI PASS:631application tests,106QA and33Node UI suites; Python3.9 covers the15Lua skips in3.11. Receipt `.git/handoff/ci-6be804c2fce9f2c680c562e7572aa1254ecd42cb-1a3fd11efc5a4f3d856a014f4b8577fb.receipt.json`.
- Alpha19-1 is installed monitor-only on portable GL-MT3000.73program files match IPK; actual HTTPS-served dashboard68 and ui45 match canonical hashes. Protected network/wireless/firewall/DHCP and app config bytes survived upgrade. CalmB default and owner terms1 preserved; onboarding still incomplete. No agent completed the owner's wizard.
- Actual installed RPC checks19/19PASS: unsupported Auto/manual requests refused, Stop acknowledged, stale revisions refused, duplicate Stop deduplicated, no false selected path. This is NOT a real channel-transition PASS. Own durable Stop remains in place.
- Actual own-monitor SIGTERM/procd recovery8/8PASS in7.223s; monitorPID842 at that checkpoint. This is graceful process loss, not power loss or native transition recovery.
- Exact canonical-IPK synthetic Edge UI6/6PASS138checks acrossA/B/Cdesktop/mobile, sourceSHA/HEAD recorded; actual browser cleanup independently confirmed. Evidence `private/manual-ui-alpha19-20261021/run-8a3d88d601/` plus `cleanup-verified-launchers.json`. Oldfailed/earlierpasses retained.
- Public GitHub main remains alpha16 snapshotae00e444af5f324e2612687db58c141d18d5e64b; last approved public WIP is9a7ab758/source8febc9d. Alpha19 is not published. Local commits after8feb/d947 are not automatically remote publication proof.

## Scope and recovery

Owner explicitly allows extensive tests of the dedicated portable MT3000. Wi-Fi PC uses primary MT6000/gateway8.1; management cable uses portable11.1, independently rechecked after reboot. Never change PC Wi-Fi/routes/adapters or the primary router. Owner again chose router-only tests, no separate client. No real LAN/IPv6/Kill Switch/native Auto acceptance may be invented.

Fresh encrypted pretests export has175entries and was independently DPAPI/AES-GCM decrypted/read in memory; no plaintext persisted. Cipher SHA51a7758feb76d25c001ef78602212974707228c7c1e57c21f2353dcac9928aa0. Private key/cipher files stay outside Git/public source.

Dbackup completed:23files179747433bytes,9ZIP CRC/1871entries/67internal hashes checked in a new folder under intended D project archives. Receipt `private/backup-D-resume-20261021T053217Z-34cdde/copy-receipt.json`. This backup covers oldalpha16/17WIP/supplements/urgentstop, NOT the later alpha19 batch; final current-source archive/Dcopy still needed.

Oldalpha12 observer is STOPPED,83samples/9871.142s, not12hPASS; never resume that old run just because its VM/container exists.

## OpenVPN lifecycle investigation - precise current facts

Independent private OV harness sourceFA9CDC917F6C6367ACD0D95E014333365EB32E3C00A14C859BA3BDE18BB4F231, reviewed core74a504...,18source pins,19isolated tests PASS. It is a fixed-profile bounded router-local test, NOT the application manual/native adapter. Unchanged25s actor/20s observation/30s cleanup/15squiet limits. No global OpenVPN/firewall restart, vendor patch, host-network mutation or credential/profile rewrite.

Separate identity-guarded preparations were executed and recorded:

1. Dead OV PIDfile inode34341 quarantined at `/tmp/homensai-ov-maintenance-3v5vwu1u`; `/tmp/ovpnclient` tightened0755->0700. No VPN/UCI/route write.
2. `/etc/openvpn` root:root inode4642 tightened0775->0755 to remove group-write. Preserve root write and existing read/traverse; config-file bytes unchanged. Do not casually restore unsafe permissions or replace path guards with exceptions.

Attempt01: REFUSED before ARM due PROFILE-PARENT-UNSAFE; cleanupNOT-NEEDED, noflags/gateactivation. Evidence `bounded-ov-trial-physical-01.jsonl` and actor result in private portable directory.

Attempt02: ARM0.816s, stockifup-w dispatch0.966s, freshTLS+TUNUP at9.143s. Observation ABORTED10.494s with QUEUE-GROWTH-ABORT: vendor work1->2->4, firewall peak3, RTP2, queued services2; recursive/retry/flock0, RAMmin209708KiB. This is an observed conservative abort, not proven firmware deadlock or a completed forward test. Independent SSH data probe missed the brief window and returned PROFILE-INACTIVE; NO cold-start data success claimed.

Cleanup02 PASS: persisted OVdisabled1 at10.815s BEFORE identity-verified stock down11.078s; daemon/TUN/routes gone,15squiet and exact boot-gate restoration at34.122s. Roothost request returnedexit0 only because cleanupPASS; do not equate that exit code to forward success. Stock leaves a stale per-interface PIDfile due its wrong-filename teardown bug. Do not blindly delete/kill using it. Both VPNs expected disabled1 and S95 startup link restored; refresh actual post-quiet state before any new trial.

## Immediate next work - do not lose this order

1. Complete actual scheduler setup/verification for the owner's15-minute request if supported; record real task ID/action/schedule/overlap policy. Never claim quota reset or a running timer without proof. Keep checkpoint intact if quota runs out.
2. Read code/events for OVattempt02. Determine actual queued service types (allowlisted coded classification, no rawenv/syslog) before proposing any fault-guard changes. Do NOT weaken the queue-growth predicate just to get PASS or relabel the abort.
3. Backup/platform agent is creating a NEW instrumentation revision only: preserve oldFA9/sourcepins/receipt, classify queues and start an owned read-only bound data-probe child at first verifiedfreshTLSUP so it can finish before cleanup; no timing/fault-order changes. Late/profile/route/daemon drift remains UNCONFIRMED. Independent hardening review required before another physical trial.
4. After all actor activity is terminal, refresh own physical state: both clients disabled, daemon/TUNgone, stockqueues/workersquiet, completeFW3state, bootlinkexact, monitoronly/native0, config/routes compared. Do not use old PIDs or scope paths as fresh authority.
5. If a new trial needs removal of the new stale PID residue, prepare a NEW identity-pinned dead-PID quarantine; the first prep script pins the OLD inode/mode and must not be rerun blindly. No global stop, arbitrary processkill, lockunlink or permission-guard weakening.
6. The real MT3000 manual route-write adapter remains unimplemented/uncertified. Auto/manual application requests still fail platform/monitor/client-proof gates. Actual VM/model/RPC/OVlifecycle tests do not close this. Continue substantive adapter work and independent recovery tests before claiming it works.
7. Read-only feasibility found network namespaces, veth module/file and TUN present on portable router. An isolated onboard software client might enable router-hosted forwarding tests within owner router-only scope. This is only a feasibility observation: NO namespace, veth, bridge port, DHCP client or policy rule was created. Any implementation needs independent cleanup, namespace/interface identity, no bridge-MAC/management change, no host-resolver mutation and honest proof_scope; never forge an external LAN certificate from it.
8. Update final physical report/TODO/current state, save exact-source Git checkpoint, restore-verified archive and current Dcopy. A future release/publication needs concrete approval if automatic review requires it; prior approvals named different payloads. Preserve all failed/STOPPED evidence.

## Worker state

Root owns physical calls/install/checks. Backup_platform owns private OV instrumentation, no physical calls. Hardening_review independently reviews it, no physical calls. UI agent finished canonical138-check browser acceptance and confirmed cleanup; validation agent finished corrected full snapshot. Product source remains unchanged since exact CI6be804c; private harness edits are not part of that released-package proof. Use `collaboration.list_agents` and actual receipts to refresh live status; this file is point-in-time evidence.

Primary references: CONTINUATION-2026-10-21.md and RESUME-TODO.md; private CURRENT.local.json needs refreshing from this newer checkpoint. The urgent user request was SAVE AND CONTINUE, not STOP.


## Continuation scheduler attempt 2026-10-21T06:13Z

Owner clarified: periodically attempt work after a possible natural quota reset; no quota reset/bypass requested. Created native heartbeat TOML at C:/Users/hosePC/.codex/automations/homensai-vpn-resume-15m/automation.toml for current thread 01a1586e-010e-76a2-9044-ab4332e779d8, FREQ=MINUTELY;INTERVAL=15. File hash AE9B96051EB14D170AB20707CA8389B85F3F98DAD7561DB32A072311CC8F4CC9. Read-only native scheduler DB check returned no matching automation row/next_run_at: REGISTRATION NOT CONFIRMED, do not describe timer as active. Receipt private/continuation-15m-20261021/registration-check.json. Need finish registration via supported scheduler or reviewed Windows Task Scheduler fallback; do not edit internal SQLite. No model/quota probe, no duplicate executor, no network change was performed. OV instrumentation worker continues isolated checks, no new physical trial.


## Delivered heartbeat 22 October 2026, 07:30 UTC

Native automation `homensai-vpn-resume-15m` delivered this scheduled turn: registration/delivery now CONFIRMED by the actual heartbeat, superseding the earlier unconfirmed status. This proves this attempt reached the model, not that all future attempts succeed or when quota resets. No replacement timer or extra executor created.

No child agents were running; elevated read-only host process inventory found no Python/SSH executor. Exact frozen instrumentation hashes (6/6) match independently reviewed receipt: harness `85efa0cbc31edcfa05b8bd271b1e255e5b2d1f8831f899c0db8db8346b726713`. Reran all 29 isolated checks: PASS, 0 failures/skips, 1.285s tests; cached Python3.9 Docker, network none/read-only source, no device calls. Receipt `private/continuation-15m-20261021/heartbeat-20261022-0730.json`.

Next: fresh portable-only read-only state/identity checks, review and quarantine the NEW dead PID residue only if verified, then root-owned bounded instrumentation trial. Keep unchanged fault thresholds. Real MT3000 application manual/Auto adapter remains incomplete; no physical/LAN transition PASS added. Private CURRENT.local.json is still historical alpha16 and must not be used as fresh device truth.


## Physical read-only heartbeat 22 October 2026, 07:49 UTC

No parallel agents or host Python/SSH executor. PC cable still ifIndex3/source192.168.11.228/gateway11.1, Wi-Fi ifIndex16/source192.168.8.100/gateway8.1; no network changes. Initial controller failed before connection because default Python is now3.15.1 while private CFFI bindings are cp314. Explicit `py -3.14 -X utf8` succeeded; use this runtime for controller going forward.

Pinned physical MT3000 identity confirmed, alpha19 health9/9PASS, monitorPID842 running, monitor-only/native0/optional0/terms1/CalmB; onboarding still incomplete. Both clients disabled1; stock startup link exact. Both selected kernel links absent, reload/restart queues0. Stale OV PIDfile still exists: dev17/inode2609073/root0644/nlink1/size5/mtime_ns1792562453609178696, refers to PID7698 with no /proc entry at read time. This is fresh preparation evidence only: NO deletion/quarantine/activation performed. Do not use old inode34341 script.

Refreshed private CURRENT.local.json from fresh alpha19 receipts and preserved old alpha16 CURRENT verbatim as CURRENT.historical-alpha16-before-20261022.json. Evidence: heartbeat-20261022-0749-health.json (SHAff338ca2d84309b5be461290dbd057023e009eaaf1642154577eb1bd3f5073c4) and heartbeat-20261022-0749-readiness.json (SHA29eae7543437f1a47b2b76b82414b1b1ba63f2d0ac41fd8b6e4cad8f3fec4f50). Next bounded block: new independently reviewed dead-PID quarantine with fresh identity/proc checks, then recheck full prerequisites and run reviewed instrumentation. No Auto/manual or LAN acceptance claimed.


## Physical OV instrumentation trial03 - heartbeat 22 October 2026, 08:04 UTC

One independent agent pid_quarantine_review reviewed new preparation SHA744d7f3c2b860b63a730a5ce3e4c6684ca66387fa04dadc83238293270d0fa06, GO single-executor/no concurrent operator startup. Root freshly checked cable/Wi-Fi addresses and no host Python/SSH executors. Exact dead PIDinode2609073 quarantined to /tmp/homensai-ov-maintenance-newpid-5cypadea, config hashes unchanged, NO existing-directory chmod or VPN activation in preparation. Receipt ov-newpid-quarantine-20261022.json SHA667da1f977b9818d355b96e95dc59a557d6f606c3d50bc7f5e21b1e1e461188d. Do not rerun this inode-pinned script.

Root executed frozen independently reviewed instrumentation85efa0cb once. Scope /tmp/homensai-ov-trial-cusccxv5. FreshTLS+TUNUP9.159s, owned probe dispatched9.171s. Existing unchanged fault guard QUEUE-GROWTH-ABORT10.629s,8samples. New diagnosis:2 queued RELOAD entries coded FIREWALL and OTHER; vendor work1->2->4, RTP2, firewall1 at abort, no recursion/retry/flock; minRAM185952KiB. This is NOT proven firmware deadlock or forward PASS.

Independent cleanup PASS: OVdisabled1 confirmed10.949s before exactdaemonstockdown11.208s; ownprobe terminated11.434s; continuous15quiet and exact startup restoration35.166s. Probe NOT-PERFORMED, no data/LAN proof; exit0 only reflects cleanupPASS. Logs bounded-ov-trial-physical-03.jsonl SHA1507149b9ab3354c09498f666c19497bed0436a28f01bd472ff9a64c21cc91b0. Fresh posttrialhealth9/9PASS: monitor842, bothdisabled1, exact stockstartup. Evidence heartbeat-20261022-0804-post-trial-health.json SHA14bcda3daf53a7fe2b856fadfeaee94fc3b8665382d89464ce244b3ca0bf8194. Wi-Fi/primaryrouter unchanged.

Next useful block: analyze pinned stock source call graph for FIREWALL/OTHER reload and normal worker burst before proposing predicate changes; do NOT weaken guard or repeat identical trial just to get PASS. Stock again leaves stalePID: fresh inode/proc evidence required. Actual MT3000 application manual/Auto adapter still incomplete. Receipt private/continuation-15m-20261021/heartbeat-20261022-0804.json; private CURRENT refreshed. Current alpha19 archive/Dcopy still open.


## Offline queue call graph - heartbeat22 October2026 08:19UTC

No active parallel physical executor or router call in this block. Root plus one independent review agent. Captured OVup225-226 marks connected BEFORE RTP249 completes; RTP1603-1623 explicitly queues FIREWALL and NETWORK reloads. Physical03 OTHER is consistent with NETWORK but remains unidentified. Aggregate samples6->7->8=1->3->7 directly explains unchanged two-growth abort; no proof of deadlock, recursion or successful settling.

Separate diagnostic candidate private/ov-queue-network-diagnostic-20261022 frozen at harnessSHA0f3d2ad5fb557aea24b0e03cc9f8c4649f31a90c0e9e26bddacb2f91545e6243. ONLY exact NETWORK enum added; observer/cleanup/counters/order/timers unchanged and original85efa preserved. All30isolated testsPASS. First expectation failure retained. Independent queue_callgraph_review GO for diagnostic freeze only, no physical acceptance. Receipt.json and docs/handoff/OV-QUEUE-ANALYSIS-2026-10-22.md saved.

Next: inspect queue producer/consumer pinned implementation and expected bounded startup fan-out, not another identical physical test or threshold relaxation. Agent found older rtp-libraries/gl_util.sh2517-2525 queue producer copy, provenance/current matching must be checked before using it as physical03 proof. Actual application manual/Auto adapter and current alpha19 archive/Dcopy still open. All router state remains as verified aftertrial03; no fresh live health asserted this offline block.


## Queue consumer provenance — heartbeat22October2026 08:34UTC

Read saved source only; no physical calls or threshold changes. gl_util.sh, vpn_func.sh, route_policy_func.sh hashes match trial03 source pins exactly. Producer writes basename-keyed service file. Consumer keeps file during synchronous reload and removes it even after nonzero return; nonexecutable target retains entry. Queue empty is NOT reload-success proof, and aggregate count includes running work.3 isolated exact-function testsPASS; initial noexec-fixture failures retained and corrected by isolated exec tmpfs only. Detailed lines/hashes in OV-QUEUE-ANALYSIS-2026-10-22.md and private/ov-queue-consumer-20261022/receipt.json. One independent reviewer requested, pending verdict. Next: identity-aware bounded settling design plus adversity tests/review before observer-policy changes; avoid identical physical retests and retain all hard fault/cleanup limits. Actual Auto/manual adapter and final alpha19 backup remain open.

Independent queue_callgraph_review confirmed exact-source consumer semantics and3 narrow shell tests. No mutex in producer/consumer permits a potential duplicate-consumption race, but actual physical concurrency is NOT proven. First log alone cannot prove noexec root cause; both actual tmpfs argument sets now recorded in private receipt. No child agent remains active for this block.


## Offline readiness model — heartbeat22October2026 08:49UTC

Root plus one independent reviewer; no physical calls/observer-policy changes. Separate private/ov-settling-model-20261022 implements point-in-time readiness model, NOT installed or connected to collector: samegeneration/route, quiet3seconds>=4samples with maxgap1.5s, route/reload effect verification, fresh samebound DNS+HTTPS probe. READY is revocable nextsample; generation/hardfault/deadline/reordered invalidtime gives stickyHOLD; route drift resets WAIT window.

Independent initial review7/7PASS found missing probe-start bound and strict input handling. Fixed both with9testsPASS: probe start/end inside stable window, matching identity/route at both ends, malformed/nonfinite timesHOLD. Initial receipt/test log preserved. Final delta review pending. Evidence receipt.json/qa-reviewfix.log, design docs/handoff/OV-SETTLING-DESIGN-2026-10-22.md.

BLOCKER: actual collector does not yet prove reloads_verified/currentliveness; never set true merely from empty queue or connected flag. Model cannot override unchanged growthabort. Next: review finaldelta and implement genuine collector contract with pre/post identity/route proof and bounded timestamps; then separately review integration. Physical state unchanged since trial03 health; no new live facts asserted. Real app Auto/manual, current alpha19 Git/archive/Dcopy remain open.


## Collector contract and verified D archive — heartbeat22October2026 09:04UTC

No physical calls or observer-policy changes. One independent reviewer reran9testsPASS and found huge integer timestamp overflow plus untyped generation constructor; root fixed both,10testsPASS, latest2fix delta awaits independent review. Receipt private/ov-settling-model-20261022/receipt.json.

Key design correction: actual agent route_binding/probe plus harness pre/post profile/daemon/ifindex can prove narrower router-originated marked DNS/HTTPS forwarding. This cannot recover stock reload exit status or certify LAN rules. Keep reloads_verified UNKNOWN/false. Current readiness model cannot progress to READY without real reload proof; future separate runtime-effects verdict/collector must explicitly state this narrower scope. Design doc updated.

Created current alpha19 local checkpoint private/alpha19-current-checkpoint-20261022-0904: HEAD source zip24738884bytes/SHAa37e2a7f3348bd18ff8753215c23a3a07bfabeed32bdce834b5838e4cbe839bd;26-entry overlay780739bytes/SHA087d1a39ea768e66a4f4e4d80e1109931a38be7bb47de86e7ba09f501fe39b5c; later readiness fix overlay5820bytes/SHA89931f586ed52abd64052fb6c40f4b649b5b00be192231346dfd456a6296ae08. ZIP CRC and overlay entry hashes/content verified. Apply HEAD then checkpoint overlay then reviewfix overlay. Snapshot includes IPK/docs/explicit own diagnostics; excludes SSH/DPAPI/config/profile/browser secrets, not full private device restore.

Dcopy completed in NEW D:/homensai/homensai-gl-mt6000-auto-vpn/archives/20261022T0904Z-alpha19-current-checkpoint, exact volume6ef539ac-f72b-4eee-86b9-46b8a94a943c. Four files25626329bytes individually SHA256 verified after copy; receipt private/alpha19-current-checkpoint-20261022-0904/D-copy-receipt.json. Archive predates this final checkpoint appendix; no remote Git publication/commit done.

Next: review latest model fixes; implement separate runtime-effects collector contract with pre/post identity and same-route bounded probe; retain all fault/cleanup safeguards and explicit missing reload/LAN proof. Save tracked handoff Git checkpoint locally and remote only within concrete authorization. Real MT3000 app manual/Auto adapter remains incomplete.


## Runtime forwarding witness — heartbeat22October2026 09:19UTC

Read-only injected collector private/ov-runtime-witness-20261022/witness.py added; no physical calls, observer changes or installation. Trusted snapshot/route_binding/probe callbacks must gather fresh same boot/profile/daemonPID-start/ifindex and same device/mark/table before/after bounded DNS+HTTPS measurement. Output only point-in-time ROUTER_MARKED_DNS_HTTPS_OBSERVED with identity/route hashes and monotonic times; reloadUNKNOWN/LANfalse/policyfalse. No rawIP or exceptiontext persisted. Not a settling/activation permit and not integrated. Caller lifetime/deadline enforcement and actual snapshot adapter remain required.

Independent queue_callgraph_review reran witness7/readiness10 testsPASS and found witness schema gaps allowing impossible HTTPS99, malformed hash and PID1. Root tightened bootUUID/hash64ASCII/PID>1/startpositive/ifindexexactint/ASCII-tableuint32 and quorum2..3; witness9tests nowPASS. Final schema delta not independently reviewed yet. Initial logs preserved, receipt/hash/qa-reviewfix.log saved. Readiness10 final fixes independently confirmed.

Saved earlier3handoff documents in local Git commit a502a0a59ef1179ff78e1e72d2a5f9dcfe0775b2 (a502a0a). Commit hook VERSION-CURRENTalpha19 confirms product unchanged. Exact product CI still belongs to6be804c, no new exact-HEADCI claim; no push/publication. This appendix is newer than that commit and Darchive.

Next: independent final collector-schema review, real fresh snapshot adapter to existing reviewed harness and installed agent with source pins, adversity coverage, then separate integration review. Do not replace growthabort with collector result or relabel reloadUNKNOWN. Actual MT3000 app manual/Auto adapter remains incomplete.


## Read-only trial bridge — heartbeat22October2026 09:34UTC

No physical calls/install/observer changes. Root plus one independent reviewer. private/ov-runtime-witness-20261022/trial_adapter.py bridges existing reviewed Device.snapshot/observation + probe_identity/eligible to installed agent route_binding/probe.13tests independentlyPASS, strict witness schema fixes confirmed. Reviewer reproduced close during final route read yielding performedTrue. Root fixed eligibility AFTER binding/probe and before return, new finalbinding-close regression;14testsPASS. Logs initial13 and final14/receipt hashes preserved. Final newdelta not independently reviewed.

Integration HOLD: publisher must preserve original guardian lease/close/cutoff fence; import agent from pinned file rather than trust arbitrary passed object; freeze own request bound to scope manifest/phase; bind boot to initial trial manifest; independent guardian still required to bound hung callbacks. Existing model/bridge is offline and cannot authorize activation or relax queue-growth protection. ReloadUNKNOWN/LANfalse remain. Next bounded block should close these concrete integration boundaries, then independent review, rather than perform another identical physical trial. Current hardware remains last observed trial03 health; no new live state claimed. Local source docscheckpoint a502a0a, latest appendices/private bridge newer than Darchive and that commit.
