<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Failure analysis and test report — 0.9.0-alpha2

Date: 2026-10-18. Scope: the router program (switching supervisor, Auto buttons, rollback, settings writers, RPC) and the LuCI page in designs A/B/C. Everything here was done **offline**: a simulated router backend in unit tests, the synthetic UI fixture in headless Microsoft Edge, and the isolated Linux container (`network none`). The physical GL-MT6000 was not accessed, Auto was not enabled anywhere, no endurance test was started.

This is evidence about the code's behaviour under injected faults. It is not a certification of the real device, the GL.iNet vendor worker, real power loss or real client DNS/Kill Switch behaviour.

## 1. Method

| Area | How it was tested | Where |
| --- | --- | --- |
| Switching, rollback, supervisor restart, buttons | New failure matrix: one injected fault per test against a simulated policy/nft/process backend | `router/tests/test_failure_matrix.py` (26 tests) |
| Existing controller/model coverage | Whole suite in the Linux container | `router/tests` (386 tests, 9 Lua-dependent skips in that image; Lua runs in offline CI), `qa` (39) |
| Page logic | JS suites, including the new design views | `router/tests/test_*ui*.js` |
| Pages in every design | Page probe: 3 designs × 12 sections (light, EN, 1440 px) plus dark, Russian, 900 px and 390 px on 5 key sections | `qa/ui-probe/` |
| Clicks and persistence | Scenario probe: every section link, design picker (apply, store, redraw, reload), keys | `qa/ui-probe/scenarios.js` |

## 2. Fault matrix results

All rows PASS on the 0.9.0-alpha2 code. "Before" shows the result on 0.9.0-alpha1 when the row exposed a defect.

| Injected fault | Expected safe outcome | Before | After |
| --- | --- | --- | --- |
| Vendor apply hangs (process never exits) | Process group killed, original order restored, `ROLLED-BACK` with `NATIVE-SYSTEM-001` | PASS | PASS |
| No LAN client confirmation until the deadline | Rollback, `CLIENT-CONFIRMATION-TIMEOUT`, no certificate | PASS | PASS |
| Stop pressed while waiting for the client | Rollback, `CLIENT-STOP` | PASS | PASS |
| Service stop signal (SIGTERM) during the wait | Rollback, never a commit | PASS | PASS |
| Confirmation with wrong tx / exit / DNS / HTTPS / stale / future time (6 cases) | Never accepted; rollback at the deadline | PASS | PASS |
| Exit address changes at confirmation | Rollback, `EXIT-CHANGED` | PASS | PASS |
| New blocker appears after apply | Rollback with that blocker | PASS | PASS |
| Reserve DNS/HTTPS fails after apply | Rollback | PASS | PASS |
| Correct confirmation | Commit, VPN-only guard, journal `COMMITTED` | PASS | PASS |
| Rollback's reorder fails | Journal keeps the unfinished phase; restarted supervisor restores the original order | PASS | PASS |
| Rollback cannot be verified | Falls back to the VPN-only guard, never a closed LAN | PASS | PASS |
| Supervisor restart in ARMED / APPLYING / WAIT-CLIENT / RESTORING | Original order restored, `ROLLED-BACK` | PASS | PASS |
| Restart after commit with a foreign policy change | Guard released, `STOPPED`, `original_restored:false` | PASS | PASS |
| Corrupt / truncated journal | `JOURNAL-INTEGRITY-FAILED`, never treated as success (see risk R1) | PASS | PASS |
| Exit trace: no `ip=`, IPv6, binary, private IP, HTTP 500, cut reply, bad status line | Coded refusal `EXIT-*` | **FAIL** (KeyError, AddressValueError, UnicodeDecodeError, IncompleteRead, BadStatusLine escaped) | PASS |
| Stop when router settings cannot be read (Lua/UCI failure) | Stop latch still written for the current trial | **FAIL** (exception, no latch) | PASS |
| Stop fails while a failure-simulation test runs | Fault test still cleaned up; reply `STOP-UNCONFIRMED` | **FAIL** (exception before cleanup) | PASS |
| Stop pressed repeatedly | One durable write | PASS | PASS |
| Start while any switch step is open (6 phases) | `TRANSACTION-IN-PROGRESS` | PASS | PASS |
| Start with unreadable journal | No start intent written | PASS | PASS |
| Return button outside held/committed reserve | Refused | PASS | PASS |
| Settings writer hangs or is missing | Coded answer `SETUP-SAVE-UNCONFIRMED` | **FAIL** (raw timeout to RPC) | PASS |
| Settings writer refuses (pending delta) | Code passed to the page | PASS | PASS |
| Change profiles while a switch is open (6 phases) | `SETUP-STOP-FIRST`, writer never called | PASS | PASS |
| Monitor off while Auto active / journal unreadable / writer hangs | Refused with a code, writer not called when refused | partly FAIL (hang) | PASS |

## 3. Defects found and fixed

| ID | Defect | Effect before | Fix |
| --- | --- | --- | --- |
| F1 | `trace()` turned malformed exit replies into uncaught `KeyError`/`ValueError`/`UnicodeDecodeError`/`http.client.HTTPException`; `HTTPException` was outside the supervisor's error list | During a trial the supervisor process could end and be respawned by procd instead of reporting a coded refusal | Parse errors become `EXIT-TRACE-FAILED`; the supervisor also catches `HTTPException` |
| F2 | `auto_control.stop()` needed the router settings to name the trial | A broken Lua/UCI read made the Stop button fail without writing the stop latch | Falls back to the trial of the current start request and reports `settings_unverified` |
| F3 | `native_stop` RPC ran the fault-test cleanup only after a successful stop | A failing Stop left a running failure-simulation test until its own timer | Stop errors become `STOP-UNCONFIRMED`; cleanup always runs |
| F4 | Settings writers (setup, monitor on/off, priorities) let a hung or missing writer escape as a raw exception | The page got no coded answer | `SETUP-SAVE-UNCONFIRMED` (the change may or may not be written) |
| U1 | With browser storage blocked, choosing a design applied the layout but the next redraw used design A | Mixed layout/view after the next status refresh | The choice is kept for the page session (`currentDesign`) |
| U2 | Check marks, step chips and profile details had contrast 2.0–2.9:1 in dark themes and design C | Hard to read | Theme-aware colours in all designs |

New codes are in the error table: `EXIT-TRACE-FAILED`, `STOP-UNCONFIRMED`, `SETUP-SAVE-UNCONFIRMED`.

## 4. Remaining risks (not changed in this release)

| ID | Risk | Why it stays | Suggested next step |
| --- | --- | --- | --- |
| R1 | A corrupt transaction journal at supervisor start installs the timed full LAN block on every start; procd respawns up to 5 times per hour | Fail-closed by design: an unreadable journal means the route state is unknown | Decide with the owner: keep the block, or block once and then publish `BLOCKED` without re-blocking; document the emergency command in Help |
| R2 | A rollback that fails every time loops through supervisor restarts, each with a 90 s full block | Bounded by procd retries; each block has its own release timer | Count recovery attempts in the journal and switch to the VPN-only guard plus an operator alert after the second failure |
| R3 | `serve()` catches a fixed list of exception types; any other type still ends the process | Respawn is the designed recovery | Consider one final `Exception` handler that maps to `NATIVE-SYSTEM-001` |
| R4 | The fixture's "Mark selected failed" button did not change the overview state in the probe | The fixture marks a profile, not the controller state | Extend the fixture so failure/recovery visibly drive the Auto states |
| R5 | Nothing here proves real-device behaviour (vendor `rtp2.sh`, Kill Switch, DNS of LAN clients, power loss) | Offline scope | Bounded physical trial only after the owner's direct instruction (see ROUTER-READINESS gates) |

## 5. Page results

- Matrix: 36 pages (3 designs × 12 sections) plus 60 condition runs. After fixes there is no horizontal overflow at 390 px in a fully loaded page, every page shows the owner attributes (attribution line, author footer, version badge), and there are no `DESIGN-VIEW-ERROR`s or script errors.
- Scenarios: 34/34 steps PASS for A, B and C: every section link opens its page (B hides Statistics/Help/Training from its menu by design and links them on the page), key 2 opens Channels only in C, the picker applies, stores, redraws and survives a reload.
- Probe limits: the contrast rule reports false positives on gradient buttons and the gear symbol; a run whose stylesheet did not load within 30 s reports unstyled overflow. Each such case was rerun alone or checked on a screenshot.

## 6. What to improve next (ordered)

1. Decide R1/R2 (journal corruption and repeated failed rollback) with the owner: these are the only paths found where the LAN can be blocked repeatedly.
2. Show the new codes on the Auto button: today a `STOP-UNCONFIRMED` reply is shown as the generic `AUTO-CONTROL-UNVERIFIED`.
3. Make the fixture drive real Auto states (R4), then add probe scenarios for failure → reserve → return on the page.
4. Accessibility: keyboard focus order and screen-reader labels of the new A/B/C views (not covered by the probe).
5. Real native browser zoom (125/150/200 %) and a real 390 px phone, which headless Edge cannot reproduce.
6. Put the page probe into offline CI with a retry for slow stylesheet loads, so the attribute and overflow checks run on every commit.
