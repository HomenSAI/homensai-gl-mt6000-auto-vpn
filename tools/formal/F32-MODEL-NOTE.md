# Formal model update for F-32 and T4-A (07.11.2026)

Branch `fix/a9-formal-f32-20261107`, based on `integ/a9-night-20261107` at 090d9f6c. Version stays 2.1.0-alpha9-1.
No product code, no router. Only `tools/formal/` and its unit tests.

## Why

The product changed and the model did not follow:

- **F-32** (b851db74): a RUNNING session adopts an outside change by itself only when `readopt_class` proves it touches
  nothing but `wireless`, `dhcp`, `gl-dns-v2` or the network outside the pair. Everything else is HELD
  (`PAIR-OUTSIDE-CHANGE-HELD`): the VPN profiles, the firewall, the pair's `route_policy` and its order, any other
  package, an unreadable or empty class. Only the owner's Start or Stop ends a hold.
- **T4-A** (c31d7332): the owner's Stop on such a hold ends it STOPPED (`end_hold_on_stop` ->
  `release_session(adopted_by='owner-stop')`). The guard is released, `owned=[]`, no profile is stopped and the
  readopt budget is neither checked nor spent. A Start while Auto is on keeps HELD. A Start after the Stop begins a
  new session on the changed configuration.

The old model adopted every outside change of a running session by itself (`tick_error`), and after the owner's Stop
it kept the hold HELD (`cl_fail` released only the guard). The trace conformance check showed it as 3 kinds of
non-conforming steps in both runtimes (`router/tests/T4A-NOTE.md`, "Remaining").

## What changed

Two new model switches, `F32` and `T4A`. They are listed in `expected.json` `"fixed"` (= the code), in `ALL_FIXES`
(`model.py`) and in `AllFixes` (`Supervisor.tla`).

`model.py`:

- `tick_error(s, cls, adopt=True)`. The readopt branch is now `can_readopt` + `readopt`. With `adopt=False` the
  catch goes on as for any other error: a session that ran stays HELD with the readopt code, Auto stays on, and
  outside_hold is not called while the request is current.
- F32, `TICK order check` (the pair's policy is foreign): always `adopt=False`. `POLICY-OR-ORDER` is never adopted.
- F32, `TICK identity changed` (`ext='net'`): the model cannot see which packages changed, so ADOPT and HOLD are both
  free choices. The ADOPT edge exists only when the adoption can succeed (3/900 s budget, journal settled). The env
  step and its `prep` are unchanged.
- T4A, `cl_fail`: under K9 (contexts `tick` and `rec`, journal settled, readopt code), with the Stop latch standing and
  Auto not on, the pass ends STOPPED (`code='-'`, `ran=False`, guard none). The readopt budget is not touched. This is
  one model step for `publish_failure` (HELD) and `end_hold_on_stop` (STOPPED). A kill between the two writes leaves
  the HELD record with the Stop latch, and the next pass ends it the same way. The `st` context is not covered, as
  for K9. Its HELD record ends on the next pass. This is an approximation of the same end state.
- New liveness check **stop-ends-hold** (`liveness_stop_hold`, CI signature `LIVENESS:stop-ends-hold`). It starts from
  every state with a HELD readopt record, a settled journal, the Stop latch and Auto off. Every fair run without an
  owner action and without faults must reach a terminal record. With the old rules (no `T4A`) the held profile
  violates it (52 bottom SCCs). With `T4A` it holds (7 296 start states, 48 bottom SCCs).

`Supervisor.tla`: `CanReadopt`, `Readopt`, `TickErrorHold` (`TickError` = readopt or hold), the F32 branches of the
order check and of `ext="net"`, and the T4A branch of `ClFail`. `gen_cfg.py` `ALL` and the cfg files are regenerated.
TLC does not compare liveness, so the new check is Python only, like the other liveness checks.

Unchanged: every safety invariant and transition assertion, the accepted list of `expected.json`, and the
Start rules (`release_for_start` / `request` still check and spend the budget).

## Results

| check | before (090d9f6c) | after |
|---|---|---|
| TLC (11 CI cfgs) | - | PASS, all EQUAL |
| ci_check | 11 profiles, 2 018 104 states, new=0 xpass=0 xfail=0 | 11 profiles, 1 986 968 states, new=0 xpass=0 xfail=0 (held 177 480 -> 160 360, glpower-net 353 344 -> 339 328, others equal; the same accepted signatures in the same profiles) |
| trace_check | python and lua each 7 non-conforming (3 kinds: `tick/IDLE` RUNNING->HELD after gl_pol, HELD->STOPPED after the Stop, HELD->STOPPED in random-022), parity 56/56, RED | python and lua 0 non-conforming, parity 56/56, selftest 3/3 rejected, GREEN; existing-tests triage unchanged (65 steps, 24 kinds) |

## Done / next

- [x] baseline ci_check and trace_check (Docker `homensai-vpn-python39:night`, `--network none`)
- [x] model.py, ci_check.py, expected.json, Supervisor.tla, gen_cfg.py + cfg, test_formal_ci.py
- [x] ci_check after the change (green)
- [x] trace_check after the change (green; trace_expected.json stays empty, only its comment says why)
- [x] TLC held-allfix: EQUAL (160 360 states, 972 552 transitions)
- [x] TLC cross-check of the 11 CI configurations (`tlc_check.py --py-image homensai-vpn-python39:night`, image
  `homensai-tlc:local`): PASS, all EQUAL (states, transitions, signatures, step pairs), 437 s; SHA256SUMS and the README
  table updated (held 160 360 / 972 552, glpower-net 339 328 / 2 374 092, keys 349 856 / 2 498 960; the old keys row was
  already stale before this change). `keys-blocker-allfix` (manual) not re-run.

Next (not done here): nothing required. Optional: run `keys-blocker-allfix` by name; the full profile `run_full.sh`.
