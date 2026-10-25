<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Failure analysis addendum — 0.9.0-alpha3

Date: 2026-10-18. Continues [FAILURE-ANALYSIS-0.9.0-alpha2.md](FAILURE-ANALYSIS-0.9.0-alpha2.md). Offline only: simulated router backend, synthetic UI fixture in headless Edge, isolated Linux container. The physical router was not accessed and Auto was not enabled anywhere. This is evidence about code behaviour under injected faults, not a certification of a real device.

## 1. Owner decisions implemented (risks R1 and R2 of alpha2)

| Risk | Decision (owner questionnaire, 18 Oct 2026) | Implementation | Tests |
| --- | --- | --- | --- |
| R1: damaged switch journal at supervisor start | Block the LAN once, then only the VPN-only guard; Auto stays off; alarm | The first start installs the timed full block and writes `native-journal-alarm.json`; every later start uses only the VPN-only guard (`give_up`). The state is `BLOCKED` with `alarm: JOURNAL-INTEGRITY-FAILED`; the Telegram report adds an `ALARM:` line. The alarm ends when the journal is archived (emergency `close-journal`). | `test_corrupt_journal_blocks_the_lan_once_then_only_vpn_only`, `test_alarm_ends_when_the_journal_is_closed…` |
| R2: rollback fails again and again | Stop after the second failed rollback | `rollback_counted` stores `rollback_failures` in the journal; the third start does not roll back, installs no full block, keeps the VPN-only guard, latches Stop and publishes `ROLLBACK-GIVEN-UP`. | `test_rollback_that_fails_twice_is_given_up_without_new_full_blocks`, `test_one_failed_rollback_still_recovers_on_the_next_start` |

## 2. Independent review of the alpha3 diff (a separate read-only reviewer)

Every finding was checked by hand before acting; all accepted ones are fixed and covered by a test.

| # | Finding | Verdict | Fix |
| --- | --- | --- | --- |
| 1 | After `give_up` with an empty journal the stop latch named no trial, so Auto could resume after the operator deleted the journal if uci options could not be cleared | Real, medium | The latch names the configured trial; a failed option reset is reported as `AUTO-OPTIONS-NOT-CLEARED` (new error row). Test: `effective_intent` returns `(False, True)` after `give_up`. |
| 2 | An unreadable alarm marker made `serve()` die before `give_up` | Real | Unreadable marker counts as "already blocked once". |
| 3 | An OS error while reading the journal escaped `serve()` | Real | Mapped to `JOURNAL-INTEGRITY-FAILED`. |
| 4 | The status claimed a VPN-only guard even when installing it failed | Real | The published `guard` text reflects the real result. |
| 5 | `rollback_counted` counted `SystemExit` as a rollback failure | Real, theoretical | `except Exception`. |
| 7 | A router-supplied code with quotes could throw inside the error-table selector | Real, low | Codes are validated before linking and before `querySelector`. |
| 8 | Plain-object lookups with router-supplied keys such as `constructor` | Real, low | `ownGet` (own properties only). |
| 9 | `Array.prototype.flat` in ES5-style code for old LuCI web views | Real, low | Removed. |
| 11 | Tests ran `serve()` only with `STOP=True` and never checked the stop latch | Real gap | Four new tests (latch, marker, OS error, guard claim) and hostile-value tests for the page. |

Reviewer checked and found no defect in: failure counting, at most two full blocks per incident, the `give_up` loop respecting `STOP`, no `innerHTML` anywhere, the error-code linker not looping, nothing starting Auto by itself.

## 3. Page work covered by tests

- New tests: `test_error_coverage_ui.js` (every code string emitted by the Python/Lua sources has a row or a documented family: 711 references, 374 rows, 20 families), `test_a11y_ui.js`, extended `test_design_views_ui.js`, `test_attribution_ui.js`, `test_auto_ui.js`.
- Browser scenarios (`qa/ui-probe/scenarios.js`): 44 steps per design, now including the fixture failure scenario normal → primary fails (primary red, reserve green, “Return to primary” offered) → primary recovered. A and B passed in the full run; C failed once under four parallel browsers (picker not rendered in time) and passed 44/44 alone.
- Publication gate: `scripts/ui-probe.ps1` (24 cases: 3 designs × 4 pages × 2 widths) runs on the host because the CI container has no browser; it passed on the alpha3 candidate.

## 4. Remaining risks

| ID | Risk | Next step |
| --- | --- | --- |
| R3 | `serve()` still catches a fixed list of exception types; any other type ends the process (procd respawns) | One final `Exception` handler mapped to `NATIVE-SYSTEM-001` |
| R5 | Nothing here proves real-device behaviour (vendor `rtp2.sh`, Kill Switch, DNS of LAN clients, power loss) | Bounded physical trial only after the owner’s direct instruction |
| R6 | The forecast list of eight checks stays grey in this version (dry run); only the controller’s audit can confirm them | Feed verified items from the controller status into the list |
| R7 | Screen-reader behaviour was checked structurally (names, roles, focus, headings), not with a real screen reader; real zoom and a real phone were not tested | Manual pass with NVDA and a phone |
