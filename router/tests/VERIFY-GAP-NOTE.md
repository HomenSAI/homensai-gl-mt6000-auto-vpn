# Verify-gap (BLOCKED lamp flicker) - working note, branch fix/a9-flicker-20261107

Handoff note (owner rule 07.11.2026): keep it current until the fix is merged.

## Symptom
MT3000, 2.1.0-alpha8, controlled 120 s drop of wgclient1 (private/claude-a9-install/rt-cut-a8-cut1.json):
`native_failover.state` BLOCKED with reason None, `channel_path.active_profile_id` None, kernel_policy_verified False,
for 2-3 s, about 12 s after COMMITTED and about 27 s after the return to the primary. Then it came back by itself.

## Root cause (integ/a9-night-20261107 at a9b8ea49; alpha8 tag line numbers in brackets)
- `lua/pair.lua` reapply_missing_policy 1729-1734 [1359-1363]: publishes BLOCKED (no reason, readiness/kernel false)
  for ANY blocker from `env.backend.diagnostic()`. It runs on every pass, also on COMMITTED, before the committed decision.
- `lua/pair.lua` tick 1876-1890 [1493-1497]: the same, reason NULL, once the session is older than 180 s.
- The likely transient blocker is VENDOR-WORKER-BUSY (`lua/backend.lua:470`, GL tunnel-switch/rtp lock;
  `lua/pair.lua:35-36`: lock study 05.11.2026, episodes with only this blocker last at most 2.3 s). The other
  candidates are observation lags from diagnosis.resolve_pair and `backend.lua:419-439`.
- `lua/transaction.lua:311-319` drops channel_path to from_kernel(nil) for BLOCKED, so the page loses the channel.
- Python twin: `pair_auto.py` reapply_missing_policy 1932-1937, tick 2151-2158 (same logic).
- Not a read race: status files are written by rename. A failed read gives SERVICE-STOPPED or OBSERVATION-STALE,
  never a BLOCKED without a reason.

## Fix (done, commits 312f8033 WIP + a02137fa)
`pair.verify_gap` / `pair_auto.verify_gap` + `verify_gap_publish` are called before both BLOCKED publications.
They apply only when every blocker is in {VENDOR-WORKER-BUSY, VENDOR-SETTLING, OBSERVATION-STALE,
PROFILE-IDENTITY-CHANGED, VENDOR-IDENTITY-UNKNOWN, RESERVE-NOT-CONNECTED} and the previous publication is a confirmed
OBSERVING/COMMITTED with the session's roles. In that case the pass keeps that state with verifying=true,
verifying_since and verify_blockers. readiness_verified and kernel_policy_verified are set to false. The old kernel
proof keeps its original time, so the 15 s proof validity bounds the gap. Any other case publishes BLOCKED as before.
A gap pass takes no decision. Each gap writes one log line `PAIR-VERIFY-GAP`.

## Tests
- `router/tests/verify_gap_cases.json` (22 shared cases; 25 after IR-02), `test_verify_gap.py`, `lua/test_verify_gap.lua`.
- Both tick sequences fail without the fix and show exactly the router row.
- Passing: new tests (Py 4, Lua 3); all Lua test_*.lua files (test_sys.lua flaked once under parallel load, passes
  alone on both baseline and fix); targeted Python pair suites (121).
- Full `python3 -m unittest discover router/tests`: RUNNING when this note was written (see below).

## Remaining
- Full Python discover result to record here.
- Optional UI hint for `verifying` (not done on purpose; the lamp is already stable because the state is kept).
- Router confirmation (read-only): switch-history BLOCKED codes and a live watch, see the handback report
  (scratchpad router_flicker_check.py). Needs an install of the fixed build to verify on the device.
- The publish_failure path (`pair.lua:747-766`, BLOCKED without a reason for a refused pass) is NOT covered. It is a
  different mechanism (it writes HELD); look at it only if the history codes show PAIR-EXTERNAL-* for those rows.
