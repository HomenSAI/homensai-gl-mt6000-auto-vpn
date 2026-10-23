<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../CURRENT-STATUS.md) · [documentation index](../DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Latest: alpha43 installed and accepted

All later owner UI items and animation1 installed; adaptive startup polling included. See [complete owner checklist and measured results](OWNER-STATUS-2026-10-23.md) and [alpha43 machine evidence](../../qa/MT3000-ALPHA43-ACCEPTANCE.json). Prior41 facts below are historical. Final43 AutoON reserve restored,17:29Berlin; source85211db, fullCI724app/107QA per runtime/39UI PASS;84installed files/protected configs and served HTTPS/HTTP8080 PASS. Start59.81s, manual cycle144.52s, owner reserve restoration34.67s. Actual43 frame replay verifies health-dependent motion and error presentation.

# Operator controls and status visibility — 23 October 2026

## Installed package and scope

Alpha41 (`0.9.0-alpha41-1`) is installed on the dedicated GL-MT3000, firmware4.11.0. Canonical source `8239552a1120ceecace2f205e520ac5e1b34cc9d`; package763381bytes, SHA256 `2a961726dce0b46296facc0453afaa841bbd2926425b5d73214df1742bcf5e7d`. Installation verified84 immutable files/modes and protected router configurations. Actual dashboard71.js/ui48.css match the canonical package over pinned HTTPS and the user's HTTP8080 endpoint. Primary MT6000 and Windows networking were not changed.

This is router-probed IPv4 acceptance. It does not create an external-LAN certificate. No physical power-cut, new boot Auto-resume implementation or completed24h traffic soak is claimed. Browser tools have no attached surface; UI verification uses generated DOM/model tests and actual served bytes, with real router status frames for the final replay.

## Owner requirements implemented

| Owner issue | Final behavior |
|---|---|
| Repeat Auto clicks during startup/Stop | Main toggle locks immediately, survives redraw/reload and waits beyond queued ACK until the operation really completes. Supervisor RUNNING while PAIR-WAITING-PROBES is still ARMED remains locked. Failed-start completion retains the latest off-intent timestamp and releases the latch. |
| Ambiguous intermediate graph level | Live and stored daily graphs have exactly primary/reserve/off levels. A contiguous transition retains the last confirmed selection; unobserved intervals are gaps. Raw history is retained without inventing off periods. |
| Missing daily graph | Generated complete A/B/C control trees explicitly include the daily graph directly after the live graph. |
| Manual controls mixed with Auto | Whole manual section has its own rounded border and two channel-card buttons, each with Turn on. No default-group clutter or separate primary/reserve action buttons. |
| Forced operator selection while Auto is on | Existing fenced pair_manual RPC is used. Auto stays enabled while the operator chooses reserve or primary. Healthy operator preference remains protected; confirmed failure can release it for recovery. No separate Resume control or “automatic control active” line is needed in the panel. |
| Vague manual labels | A healthy selected card says Internet works: primary/reserve channel. The other says Internet: channel not in use, with the Turn on hint. More saturated green/red fills; pending/real data-unavailable states stay explicit. A queue ACK never proves Internet works. |
| Grey working VPN list | Confirmed live-policy selection is separate from DNS/HTTPS health. Router response time plus monotonic elapsed browser time controls freshness, so a PC clock offset cannot grey out fresh probes. Old data still expires. Vague missing-confirmation copy is replaced by specific status/data errors. |
| Two unlabelled check cells | Primary/reserve labels are above their actual corresponding health cells; working cells are not sorted ahead of failed ones. |
| Stale firmware warning | GL.iNet firmware and OpenWrt release are separate fields. The old comparison of OpenWrt21.02 with GL.iNet4.11.0 and speculative Auto warning is removed. |
| Power/Stop/monitor presentation | Power is bright green/red. Exceptional Stop is inside Technical actions, available for cancellation while the ordinary toggle is locked. Monitoring remains required/default-on; a stopped/error state is red with a restoration action and prevents ordinary Start. |
| Persistent operator overview | Sidebar footer contains labelled primary/reserve lamps: selected healthy channel blinks green, unselected blinks red, with matching selection/error hints. Attribution and version remain visible. |

## Software and installation evidence

Exact product-source CI passed723 application tests and107 QA tests per Python3.11/3.9 runtime, plus39 UI suites. Complementary environment skips are retained: Lua coverage runs under3.9, additional QA tooling under3.11. Tests cover client clock skew while still expiring stale observations, both footer route directions, complete generated layouts, typed manual RPC and duplicate-click/late-callback/failure-completion behavior.

Quiet-state collection now restarts the verified continuous-quiet streak after a transient process/queue-read error, within the same bounded deadline. Unknown samples never count as quiet; persistent uncertainty, busy workers and nonempty queues still refuse. Tests cover recovery after transient reads and refusal at the original deadline. No rate limits, Stop fences, rollback or device/profile checks are bypassed.

## Retained failures and physical observations

- Alpha38 install initially had no registered RPC object despite own services running; direct plugin list was valid, and a second normal rpcd reload restored registration. Every later installation explicitly verified RPC before Start.
- Repeated fast OpenVPN startup received AUTH_FAILED. Alpha39's refused startup safely cleaned up (244.48-second observation/cleanup run); earlier evidence is retained. Credentials were unchanged. Alpha40 Start passed62.34seconds after a pause. Alpha41 installation uses a pause before reconnecting; its final result is recorded below.
- First actual alpha40 manual reserve request was accepted/claimed, then refused VENDOR-WORKER-QUIET-UNVERIFIED after47.60seconds. Rollback restored original order; Auto stayed on the healthy primary. This is not counted as a confirmed switch. The exact underlying transient read is not proven from that failure.
- A second actual alpha40 reserve/primary cycle passed58.31seconds with Auto RUNNING throughout. Concurrent read-only trace recorded90 verified worker samples, no read errors and maximum busy0. It ended on primary with the operator preference retained. The failure and success are separate records; attempt budget was not reset.
- Actual pre-alpha41 Stop passed14.16seconds and showed STOPPING → STOPPED, both owned profiles restored off and guard removed.

## Final installed alpha41 acceptance

Final Start PASS60.36seconds. Actual operator reserve/90-second hold/primary cycle PASS151.65seconds with Auto RUNNING throughout, exactly one manual commit and one confirmed return, zero automatic commits during that cycle, and no Resume command. Both source and target pass DNS/two HTTPS probes; certificate unchanged. Generated actual installed41 UI replay on three sanitized real router frames PASS: primary/reserve/primary cards and sidebar match selection,2of2 VPNs working, unconnected profiles red, even with a simulated five-minute PC clock offset. This is DOM/model replay, not a browser screenshot claim.

Subsequent live operator activity selected the reserve. A primary-only final observer assertion was inappropriate for that permitted selection and failed; the final selection-aware snapshot PASS at14:39UTC found Auto RUNNING on the reserve, both VPN checks healthy, monitor age5.15s, confirmed live policy, no test faults or temporary full-block guard. The operator's choice was preserved. GL.iNet4.11.0 and OpenWrt21.02-SNAPSHOT are now distinct actual fields.

Final observed lifetime controller counters (all retained sessions, not this test alone):23attempts,15commits (11automatic/4manual),4new-model returns,10rollbacks. Failed/refused attempts are distinct from successful switches. Reliability:1598checks,29failed checks,14observed episodes and302.84 summed profile-down seconds, including controlled tests/start/Stop transitions; these are not14unexpected provider outages.

## Recovery and publication

Full owner feedback and chronological crash-resume steps are in [the saved plan](OWNER-IDEAS-2026-10-23.md). Private evidence namespace: private/auto-matrix-20261023T101626Z, with encrypted/decrypt-read-verified configuration exports and source recovery bundles. Raw data, credentials and private backups are excluded from Git. Product source8239552 is saved in the owner-authorized Gitea feature/recovery-auto-20261023 branch. No main/tag/GitHub publication is claimed. Final evidence/documentation save follows after physical acceptance.

## Next UI review batch (alpha42 WIP, not installed)

Owner added a1–24h bottom slider, equal channel-card heights, Turn on only on an eligible inactive red card, shorter selected/not-in-use copy, and yellow Switching only on the destination during a command (other card red with no status message). These source changes are prepared locally with targeted UI tests; alpha41 remains installed. The owner explicitly requested four computer→router→VPN-server animation alternatives before choosing. The four interactive previews are task-owned response content, not installed app code. No animation is selected or integrated yet. Batch42 requires that choice, then canonical build/full CI/installation and actual UI verification. Do not install this WIP as accepted or report the new refinements as already deployed.
