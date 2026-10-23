# Owner feedback and crash-resume plan — 23 October 2026

## Execution rule

Owner asked to persist every new idea in this plan and finish the current task first. Do not lose later messages after a crash. Finish the Auto button/three-level graph batch, then implement the queued manual/readiness/Overview fixes and install the verified final version on the dedicated MT3000. Do not claim local fixes are installed. Primary MT6000 and Windows networking remain excluded. No old observers or fault simulations resume automatically.

## Current work

- [ ] Auto toggle: lock immediately; keep locked after queued ACK and across redraw/reload until confirmed completion, including RUNNING supervisor while PAIR-WAITING-PROBES remains ARMED. Preserve independent Emergency Stop during startup and suppress duplicate pending Stop.
- [ ] Live and daily graphs: exactly three plotted levels — primary, reserve, off. No amber intermediate level. Hold the last confirmed selection through a contiguous transition; unknown/unobserved intervals remain gaps. Explain transition reason as text.
- [ ] Add regressions, freeze alpha39 (alpha38 has already been installed), canonical exact-source CI/build/hash, physical verification, installed/served-file verification, Git/Gitea checkpoint and final handover.

## Queued owner requirements (implement after current batch)

- [ ] Manual selection must work while Auto is running. Show which command is actually available and a concrete reason if it is refused. Earlier RPC hardware success does not resolve the owner's observed UI failure.
- [ ] Replace standalone "switch to reserve / primary" buttons with two channel cards that act as buttons and contain "Turn on" (Russian: "Включить"). Primary and reserve roles/protocol/country must be obvious. Selected manual channel green, unselected red, command pending yellow. Do not fabricate a selected route on ACK.
- [ ] Put the entire manual heading, two channel cards, actions and selection/Internet explanation inside its own rounded border; not merely a separator line or a border around the help text. Fix all applicable designs.
- [ ] Remove confusing default group information from the ordinary manual workflow (hide default or move optional group details out of the main card).
- [ ] Replace "No fresh path confirmation" as the primary manual status. State selected/unselected channel explicitly from verified router policy; show Internet verification separately. When actual selection cannot be read, say the router has not returned its selection and block an unsafe command rather than inventing one. Explain this exceptional condition clearly.
- [ ] Step 1 "Check VPNs now": label the two status/progress cells above as "Primary channel" and "Reserve channel". Health bars do not by themselves mean both carry common traffic.
- [ ] Ensure Overview actually contains the saved 24-hour chart directly beneath the live chart. Owner does not see it in the installed UI. Verify generated layout, not only existence of renderAutoDay. Keep live chart and viewport state.
- [ ] Install all completed fixes on MT3000, verify actual served version/assets and tell owner which version to refresh. Screenshots show alpha37/38 and old layout; do not dismiss this as cache without checking generated code.

- [ ] Remove the stale firmware warning on verified GL-MT3000 /4.11.0. Determine the actual displayed-condition bug; do not claim Auto unconfirmed when router-probed acceptance is verified. Keep actual diagnostic failures concrete.

## Verified installed state / recovery boundary

As of 12:51:03 UTC (14:51 Berlin): alpha38 installed on dedicated GL-MT3000; 84 immutable files/modes and protected configs PASS; pinned HTTPS served JS/CSS match package1197bfb214ae1ed2ce5a84be0dbc9ac881432b3a157a38e02d020161d19aa454,760107bytes. Auto startup PASS62.73s, final OBSERVING/PAIR-WATCHING/readiness_verified true, Auto left ON. Backend display phase changed STARTING -> RUNNING at30.58s while probes still pending; current source fixes this early UI unlock. RPC initially missing after package install despite own services running; direct plugin list valid, a second normal rpcd reload restored registration. Initial failed startup transports sent no Start and are retained. Current source includes uninstalled three-level graph and waiting-probe lock corrections. Do not reinstall an older alpha38 build.

Private evidence: private/auto-matrix-20261023T101626Z, marker private/AUTO-MATRIX-CURRENT.local.txt; active owner claim private/ACTIVE-EXECUTOR.local.json. Exact alpha38 source eeeb48192412a9531c0fde1e3f3437e11a588de1 CI PASS718app/107QA per runtime/38UI; canonical package prepared from same-product source431da30 and hash matched final receipt. Last Gitea checkpoint remains a050116 (alpha37 report); alpha38/39 batch publication still pending. Fresh189entry encrypted/decrypt-verified pre-upgrade backup retained. Never include private files/keys/backups in Git.

## Resume order

1. Read this plan, CURRENT, Git status and executor claim. Confirm no other active owner thread before writes/device actions.
2. Preserve and inspect current WIP; finish graph/button regressions and bump alpha39, then exact-source CI.
3. Implement queued manual/readiness/Overview changes after current work; preserve current verified Auto while doing local code. Install one completed, tested batch where possible to avoid repeated VPN reconnects.
4. Stop through ordinary RPC only before required installation; verify exact device/backup/protected configuration/files. Verify RPC registration after installation, then Start and actual available manual actions. Leave Auto ON after final checks unless owner says otherwise.
5. Save durable report, clean source commit and restore-verified bundle; authorized Gitea feature/recovery-auto-20261023 only. Report installed versus pending truthfully.

## Local implementation checkpoint, 13:12 UTC / 15:12 Berlin

All queued changes now exist in alpha39 WIP source, not installed: manual card-buttons inside a rounded whole-panel border, selected-policy state distinct from Internet checks, no default-group clutter, primary/reserve health-bar labels, verified daily/live graph subtree in generated A/B/C layouts, three-level plot projection with gaps for unknown data, control lock until actual readiness even after supervisor RUNNING. channel_path adds a read-only pair policy-order/hash snapshot; it does not bypass manual-health/Stop/budget guards or grant LAN acceptance. Firmware UI previously compared OpenWrt21.02 with GL.iNet4.11.0; backend now separates their fields and the stale speculative warning is removed. New dashboard70/ui47 paths prevent reusing the old cached dashboard69/ui46 files on page reload. Targeted Node regressions PASS. Full exact-source CI, canonical hash pins, install/RPC-registration check and actual manual cycle are pending. Installed alpha38 Auto is still ON. Full actual38 Stop phase test should be run only once immediately before final upgrade; final Start39 and manual cycle then leave Auto ON. No further fault matrix needed for this display-only batch.

## Installed alpha39 / final request-time correction, 13:23 UTC

Alpha39 installed,84files/modes/configs and pinned HTTPS plus actual user HTTP8080 dashboard70/ui47 hashes PASS. Exact e594824 CI PASS720app/107QA per runtime/38UI. Actual Stop38 PASS14.14s with STOPPING -> STOPPED. Alpha39 first Start received seven current OpenVPN AUTH_FAILED markers15:20:23..15:21:04 Berlin and safely cleaned up to STOPPED; its private observer still finishes its240s window and final Stop. Do not start a competing command before that observer completes. This exposed an additional button edge: auto_control.public_status included pair intent only while on, so after a failed Start its requested_at could revert to an old legacy Stop timestamp and keep the local latch locked. Source now includes pair off intent as well, preserving its current revision/timestamp, with a new failure-completion regression. Because alpha39 is already installed, bump alpha40 and rebuild/CI before installing this correction. Manual39 full-cycle test has not run yet. Keep the failure, update this plan after observer completes, then safely retry/upgrade; do not claim Auto ON while currently stopped. All earlier source39 UI requirements exist and passed generated DOM checks; no actual attached browser session.
