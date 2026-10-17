# Approved post-alpha10 completion checklist

Approved by the user on 17 October 2026: execute everything possible without the physical router, begin with virtual OpenWrt, journal exact failures/corrections and save local Git -> verified Gitea -> reviewed GitHub snapshots. Physical installation, configuration and traffic interruption are excluded.

| ID | Priority | Work | Scope / acceptance | Status |
| --- | --- | --- | --- | --- |
| POST-01 | P0 | Install current alpha10 in isolated OpenWrt; test LuCI, RPC, service and settings. | Preserve paused disk checkpoint; verify real opkg/runtime and unchanged guest network/firewall. | VIRTUAL PASS; ACTUAL MOBILE CSS CORRECTED |
| POST-02 | P0 | Upgrade/downgrade and interrupted own-config writes. | Actual virtual opkg/UCI/procd, restart/recovery and private field/history preservation; never call this hardware flash proof. | VIRTUAL PASS; hardware power-loss/flash not certified |
| POST-03 | P0 | Native full cascade and verified return/rollback. | Recheck local contracts/models; real vendor device test DEFERRED. | LOCAL CONTRACT SUITES RERUN / DEVICE DEFERRED |
| POST-04 | P0 | LAN DNS/HTTPS/exit, IPv6, Kill Switch confirmation. | Local/virtual proof and witness contracts; actual hardware client test DEFERRED. | LOCAL CONTRACT SUITES RERUN / DEVICE DEFERRED |
| POST-05 | P0 | Vendor worker/manual-edit arbitration. | Test refusal/exact generation/lease contracts locally; actual GL.iNet worker proof DEFERRED. | LOCAL CONTRACT SUITES RERUN / DEVICE DEFERRED |
| POST-06 | P0 | Isolated reserve testing and inactive-profile startup. | Validate local adapter contracts and VM isolation; real provider tests DEFERRED. | LOCAL CONTRACT SUITES RERUN / DEVICE DEFERRED |
| POST-07 | P1 | Locate/verify matching SDK and standard package build. | Official provenance and exact target/revision; do not mislabel generic SDK parity as matched vendor build. | BLOCKED: exact vendor SDK provenance |
| POST-08 | P1 | Automate reviewed local-first public snapshots/releases. | Prepare/verify/publish stages, parent/tree/hash/secret guards, no canonical history leak/force/old-tag overwrite. | PASS: GITEA FIRST / GITHUB SNAPSHOT / RELEASE DOWNLOAD HASH |
| POST-09 | P1 | Restricted primary-Gitea CI runner. | Trusted parent orchestration, isolated credential-free jobs, exact SHA receipts; deliberately failing check blocks release. | ISOLATED LOCAL RUNNER PRESENT; GITEA SERVER ACTIVATION BLOCKED |
| POST-10 | P1 | System readiness page. | Explain compatibility, dependencies, monitor freshness and each Auto blocker; unknown never means ready. | PASS: VM READINESS / UNKNOWN AND STALE GUARDS |
| POST-11 | P1 | Incident detail card. | Correlate reason, attempts, evidence gaps, recovery and final outcome; retain unknowns and redact secrets. | PASS: INCIDENT CARD / BROWSER DOWNLOAD |
| POST-12 | P1 | Browser stress/responsiveness and actual virtual LuCI styles. | Long names/big tables/keyboard/short windows/languages, distinguish actual zoom from CSS-area equivalence. | PASS: ACTUAL LUCI 30 + SYNTHETIC STRESS 40 TRANSITIONS |
| POST-13 | P1 | 24-48h actual hardware resource/flash observation. | Prepare local measurement/retention tooling; hardware run DEFERRED, no automatic start. | BOUNDED VIRTUAL SAMPLE PASS / DEVICE 24-48H DEFERRED |
| POST-14 | P2 | Reviewed recovery presets. | Stability/fast recovery/hold reserve map to bounded settings with review; no automatic enablement or guard weakening. | PASS: BOUNDS / PRESET REVIEW / CANCELLATION |
| POST-15 | P2 | Human-readable incident HTML/print-PDF export. | Browser rendering/print, no router PDF engine; secret-safe escaping, clear gaps/scope. | PASS: ESCAPING / REDACTION / BROWSER HTML DOWNLOAD |

Old completed work is reused. This checklist does not reopen previously accepted offline features or claim hardware acceptance. Updates below and in WORKLOG carry exact evidence; BLOCKED means a real external prerequisite, not simulated success. No repeated chat-status automation is created.
