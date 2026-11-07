# T4-A regression: Stop after an outside change ended HELD (07.11.2026)

Branch `fix/a9-t4a-stop-20261107`, based on `integ/a9-night-20261107` at 38ed0981. Version stays 2.1.0-alpha9-1.

## Symptom

`test_trace_fixes.Scenarios.test_t4_a_stop_after_an_outside_change_ends_stopped` failed in both runtimes (Python
and Lua). The final `(sess, guard, readopt_code)` was `('HELD','none',True)`. The test expects
`('STOPPED','none',False)`.

## Culprit (found by bisect, this test only)

- e7b1666d and 374a245c pass. c794c0e6 (merge of fix/a9-foreign) and every later first-parent merge fail.
- First bad commit: **b851db74** `fix(pair): adopt an outside change by itself only for wireless/dhcp/gl-dns-v2
  and the network class; hold the rest (F-32)`.
- 9972ef95 (Telegram notice), 78daaf00 (rescue no-journal), a02137fa (verify_gap) and 02d90163 (owner decisions)
  came after the first failure and did not cause it.

## Root cause

- Before b851db74, `readopt_running` adopted every outside change by itself. The trace's `gl_pol` (a foreign
  route_policy) was readopted. The new session was RUNNING, and the later Stop ran a normal cleanup that ended
  STOPPED.
- b851db74 now classifies the change. A route_policy change gives `POLICY-OR-ORDER`, so the session is HELD with
  `PAIR-EXTERNAL-POLICY-CHANGE`. See `pair_auto.py:306` `readopt_running` -> `readopt_class`, and Lua
  `pair.lua:931`. The commit message says "only the owner's Start or Stop ends a hold". Only the Start half was
  implemented (`release_for_start` / `request` -> `release_session`).
- What a Stop did: Auto goes off, then `tick` -> `cleanup`. `held_unchanged` returns `PAIR-EXTERNAL-POLICY-CHANGE`
  because the live order no longer matches the session (`pair_auto.py:1771`; Lua `pair.lua:1405`). Then
  `publish_failure` writes HELD again. Then `outside_hold` -> `owner_stopped` (`pair_auto.py:1717`, Lua
  `pair.lua:1355`), which only released the K9 guard. The record stayed `HELD` with its readopt code on every
  later pass, until a Start.
- Owner rule: an outside change that is HELD stays held until the owner presses Stop and then Start, and the Stop
  must end STOPPED. So the product was wrong and the test expectation is right.

## Fix (Python + Lua twins)

- New `pair_auto.end_hold_on_stop(state)` (`pair_auto.py:280`) and its twin `pair.end_hold_on_stop(env,state)`
  (`pair.lua:1344`). It works under the control lock and re-reads the record. It acts only when all of these hold:
  - same session id;
  - phase HELD;
  - recovery_error is one of `READOPT_CODES`;
  - pair intent is not `on`;
  - `owner_stopped(current)`.

  It then retires the record exactly as the owner's Start does, through `release_session(..., adopted_by='owner-stop')`:
  - the record is archived to `session-recovery/pair-<id>-stop-<t>.json`;
  - phase becomes STOPPED, `owned=[]` (a profile is never stopped after an outside change) and
    `recovery_error=None`;
  - `operator_resolution` gets `adopted_by='owner-stop'` and `outside_change.decision='STOP'` /
    `why='OWNER-STOP'`;
  - the reason stays `AUTOMATIC-EXTERNAL-CHANGE-READOPT`, so the existing catalogue row and the orphan-guard rule
    still apply and no new code is added.
- `release_session` (`pair_auto.py:230`, `pair.lua:896`): for `owner-stop` it neither checks nor spends the 3/900 s
  adoption budget. A Stop adopts nothing.
- `outside_hold`, Stop branch (`pair_auto.py:1727`, `pair.lua:1367`): after releasing the guard it calls
  `end_hold_on_stop`. On success it publishes `STOPPED` (`original_restored: false`).
- What does not change:
  - no Stop: the hold and its VPN-only/full guard stay as before;
  - a Start while Auto is on is still refused and the session stays HELD;
  - a Start while Auto is off (`release_for_start`) works as before;
  - the next Start after a Stop begins a new session on the changed configuration.

## Tests

- `test_trace_fixes.Scenarios.test_t4_a_stop_after_an_outside_change_ends_stopped`: passes in both runtimes. The
  expectation is unchanged.
- New `test_trace_fixes.Scenarios.test_t4_a_an_outside_hold_ends_only_by_stop_then_start`, both runtimes:
  - a Start while Auto is on keeps HELD;
  - Stop gives STOPPED, guard none, readopt 0;
  - the next Start is accepted and the session is RUNNING with the VPN-only guard.
- New `test_formal_fixes.K9.test_owner_stop_ends_the_hold_stopped`: with the budget spent, the Stop ends STOPPED
  with the archive and spends no adoption. New `test_no_stop_no_end`: without a Stop, nothing is written.
- New Lua test `lua/test_formal_fixes.lua` "T4-A: the owner Stop ends the outside-change hold STOPPED and spends no
  adoption" (30 tests, was 29).
- Docker `homensai-vpn-python39:night` results:
  - Python, all OK, 234 tests: `test_trace_fixes`, `test_outside_change_policy`, `test_telegram_outside`,
    `test_rescue_no_journal`, `test_verify_gap`, `test_pair_auto`, `test_formal_fixes`,
    `test_held_start_handover`, `test_boot_held`, `test_key_gate`.
  - Lua, all OK: `test_formal_fixes`, `test_outside_change`, `test_telegram_outside`, `test_rescue_no_journal`,
    `test_verify_gap`, `test_auto_pair`, `test_control_request`.

- Full suites in the same container:
  - Lua: all 84 `lua/test_*.lua` files pass. `test_sys` and `test_vendor_retry` only failed inside a sequential
    loop because of a shared `/tmp` and the 120 s timeout. Each passes when run alone.
  - Python, `unittest discover`: the fix gives 2559 tests with failures=6 and errors=6. Baseline 38ed0981 gives 2556
    tests with failures=8 (the two T4-A failures) and errors=6.
  - The remaining failures and errors are the same on both commits. They come from the test archive, which leaves
    out `router-test-kit/` and the docs (`test_emergency_pending`, `test_probe_target_log`, `test_vendor_lock_rule`,
    and others). None of them is caused by this fix.

## Remaining (not in this fix)

- The formal model (`tools/formal/model.py`) still has the pre-F-32 behaviour:
  - `tick_error` readopts a RUNNING session on any READOPT code;
  - `cl_fail` keeps `sess=HELD` after the owner's Stop.

  The optional trace conformance (`run_offline_ci.py --trace-check`) will therefore show differences for
  `gl_pol` scenarios. Update the model together with `trace_expected.json` in a separate step.
- The Lua trace driver answers a Start refused by preparation with `FALLBACK`, while Python answers
  `PREPARATION-STOP-AUTO-FIRST`. This difference already existed and is not changed here.
