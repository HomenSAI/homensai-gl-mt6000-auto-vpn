# Formal model of the Auto supervisor / Формальная модель супервизора Auto

`model.py` is an exhaustive explicit-state model checker of the pair-mode supervisor (offline, standard library only,
Python 3.9+). Full analysis and the counterexamples К1–К10 are in [REPORT.ru.md](REPORT.ru.md) (snapshot of 03.11.2026;
the model was extended afterwards with the K11 leak family and the individually switchable fixes below).
`ci_check.py` runs reduced profiles of it in the offline CI and compares the result with `expected.json`.
Nothing here touches a router.

## What CI checks

`qa/run_offline_ci.py` runs `python3 tools/formal/ci_check.py` as a separate check (own 3600 s limit; it needs about
2–3 minutes with 2 CPUs and under 0.6 GB; the profiles run in 2 worker processes). It runs eleven profiles (`keys`: the option `--key-pin` below; `fast`, `fast-power`: the option `--fast-switch` of the fast end, docs/architecture/FAST-SWITCH-2026-11-04.ru.md: Auto may leave a primary that is alive, and a recheck beside the preparation may miss its recovery; each below 0.4 M states; the full profile has about 4.7 M states, ~20 min,
~3 GB and stays a manual run: `sh tools/formal/run_full.sh`) of the variant `fix` =
the released code. Properties: P1 LAN traffic never leaves outside a VPN tunnel (leak families), P2 no two transactions,
P3 no route write after Stop, P6 no permanent HELD, P7 failover liveness, owner-Stop liveness, return liveness (on the
reserve with a stably healthy primary, Auto on: eventually back on the primary, К12), stop-ends-hold liveness (an
outside-change hold with the owner's Stop, Auto off: eventually STOPPED, T4A), journal/kernel consistency.

The result is a set of *violated properties* (signatures such as `LEAK:k3-held-on-reserve-without-guard`,
`TRANSITION:RETURN-BEFORE-HOLD:cl-rec`). `expected.json` lists every signature that is allowed to occur:

| status | meaning | when CI is red |
|---|---|---|
| `xfail` + `"k": "K2"` | known counterexample, not fixed yet | the violation **disappears** (XPASS: flip it) |
| `accepted` | known, by design or a model artifact (comment says why) | never; an accepted signature may be absent |
| not listed | must not happen | the violation **appears** (new bug or regression of a fixed К) |

So CI is green now, turns red when a *new* violation appears, when a *fixed* К comes back, and when an `xfail` K starts
passing without being flipped (so a fixed К cannot stay unguarded).

Optional second check (host side, skipped when the docker image `homensai-tlc:local` is missing): TLC on the TLA+ re-statement
`tla/Supervisor.tla` must give exactly the same state/transition counts and violation signatures as `model.py` for every profile
above, so the two cannot drift apart. See [tla/README.md](tla/README.md).

## Current status of К1–К10

К1 fixed (58921e2f, in the model's baseline). Fixed and switched on in `expected.json` `"fixed"` (integ/alpha8, merge of
`fix/formal-k2-k5-20261103`, 04.11.2026): К1 tail (`K1T`), К2 (`RETURN-BEFORE-HOLD:*`), К3 (`LEAK:k3-…`), К4 (`LEAK:k4-…`,
`LEAK:other-running`), К5 (`COMMITTED-AFTER-STOP`), К9 (`LEAK:k9-…`) and К11 (`LEAK:k11-…`: the Start hand-over raced by
an in-flight cleanup pass; fix: `pair.cleanup` re-reads the record under the control lock before its STOPPING write and
ends without a write when the hand-over finished it - model switch `K11`, transition `CL0 superseded`) and К12
(`LIVENESS:return`, option `--rebuild`: the vendor rebuilt the carrying reserve; without the switch every pass held
RESERVE-IDENTITY-UNKNOWN, the router incident of 04.11.2026). No xfail is
left. Accepted: К6 (`ROLLBACK-ONTO-DEAD-PRIMARY:*`), К7 (`EF-START` and stop-wins with
faults: ROLLBACK-GIVEN-UP needs the operator), К8 (`LIVENESS:stop-primary-down`), К10 (`INCONSISTENT`, faults-power only,
possibly a model artifact) and the by-design windows `begin-instant`, `recovery-window`, `after-the-owner-stop`.
The authoritative list is `expected.json`.

F-32 and T4-A (07.11.2026, switches `F32`, `T4A`, in `"fixed"`; [F32-MODEL-NOTE.md](F32-MODEL-NOTE.md)): the running tick
holds a foreign route policy (never adopted by itself) and treats a network/config change as a free choice of ADOPT or
HOLD (the model cannot see which packages changed); the owner's Stop ends an outside-change hold STOPPED without
spending the readopt budget. Without `T4A` the new liveness check `LIVENESS:stop-ends-hold` fails.

## How to flip an xfail when the fix lands

The model is a hand-written abstraction of the Lua/Python code, so a flip is two things in **one commit**:

1. The fix is merged in the code (e.g. `fix/formal-k2-k5-20261103`: К1-tail, К2, К3, К4, К5, К9).
2. In `expected.json` add the К to `"fixed"` (the model then runs with that fix: `model.py --variant fix --fixed K2`;
   valid names `K1T,K2,K3,K4,K5,K9,K11,K12,F32,T4A`) and **delete** the `xfail` entries with `"k": "K2"`.
   Run `python3 tools/formal/ci_check.py` — it must be green. If it says `NEW VIOLATION`, the fixed model still shows a
   violation: the fix is incomplete (or the model switch does not cover it) — do not paper over it with an `xfail`.
   If it says `XPASS`, an entry for a К that is no longer violated is still listed — delete it.

Model coupling to know about: the K4 switch (VPN-only guard kept while the clients start) also removes the K3 signature, so
flip К3 and К4 together; the K5/K9 switches expose К11 in more profiles (its xfail entry is not profile-scoped, so that is fine).

When every fix is in, `"fixed"` equals all six names (this is the model variant `fix2`) and `known` only keeps
`accepted` entries. A new real finding gets an `xfail` entry with its К number (and a line in REPORT.ru.md);
`python3 tools/formal/ci_check.py --baseline` prints the observed signatures per profile.

## Local use

```
python3 tools/formal/ci_check.py                  # all profiles, 2 processes
python3 tools/formal/ci_check.py --profile held   # one profile, ~40 s
python3 tools/formal/model.py --variant fix --fixed K2,K3 --no-gl --json out.json --out out.txt
```

## Trace conformance: does the code only make the transitions the model allows?

`ci_check.py` proves properties of the *model*; `trace_check.py` (04.11.2026) compares the *code* with it. It is optional:
`python3 tools/formal/trace_check.py` (fast profile, 1-3 min) or `qa/run_offline_ci.py --trace-check`
(`scripts/offline-ci.ps1 -TraceCheck`); `--profile full` is a manual run of about 10 minutes. It needs Linux (`fcntl`) and
`lua5.1` for the Lua half. Nothing touches a router.

Three sources of steps:

| source | what runs | what is checked |
|---|---|---|
| `router/tests/trace_driver.py` | the real Python supervisor on the fake router of `test_forward_resume.py` | every step, invariants |
| `router/tests/lua/trace_driver.lua` | the real Lua supervisor on the fake router of `auto_harness.lua`, the same scenarios | every step, invariants, parity with Python |
| `router/tests/trace_record.py` | the unchanged tests `test_boot_held`, `test_formal_fixes`, `test_forward_resume` under a recorder | invariants gate; steps are reported for triage (a test arranges states the model may never reach) |

After every scenario event (`tick start stop resume crash power crash@N power@N p_down p_up r_down r_lost r_up gl_pol gl_net
busy wait wait_long`) the abstract state is read back from the product files (the mapping is at the top of `trace_check.py`).
One product event is many model steps, and the hidden model fields (program counter, time abstractions, Stop ghost) are
not readable, so the checker keeps the *set* of model states consistent with the trace and searches, per event, only
the successors of that event's kind. `crash@N`/`power@N` kill the pass after its N-th product write and nothing is written
afterwards; a kill between two writes of one model step counts as `split-step-kills`, not as a violation.
A mutation self-test runs every time, so the check cannot pass vacuously.

Limits. A pass may take any number of supervisor steps, so a wrong intermediate order inside one pass is not seen. A
missing step is a legal stutter: **liveness is not checked** (the running-session half of T3 was found by reading a trace).
The decision inputs are faked from the abstract health (`channel_failed`, `streak`, `return_ready`, `diagnose`,
`resolve_pair`, `preflight`, `auto_prepare`); server pick and manual switching are not driven. The Lua line's `FALLBACK` to agent.py is replaced by the Lua twins of the same two steps.

`trace_expected.json` lists every known non-conforming step with a verdict (`product-bug`, `candidate`, `model-gap`,
`consequence`) and the id of its explanation (T1-T4 code, G1-G7 model); a signature that is not listed fails the check.

Model rules that came from this check are marked G1-G7 in `model.py`. What the abstraction cannot see (which clients are
up, HANDOVER_WAIT, one attempt per boot, KEEP_SECONDS) is a free choice of the model, so the check cannot tell a wrong
choice there. The uptime window of the boot hand-over and of variant C is a state field (`--window`; `trace_check.py` always
uses it, CI profile `window`): it doubles the state space, so the other profiles keep the power-cut flag instead.

Server keys, option `--key-pin` (option `server_key_pin 'enforce'`, independent review of 71053c32, findings 1 and 2; CI profile
`keys`): `directional` is the code: a Start with an unaccepted key on the channel that carries the traffic after it (owner 05.11.2026, `key_on_carrying`: the live order) is refused before the session, the guard and the clients
(`pair.begin`, step `BEGIN0 SERVER-KEY-UNACCEPTED`, property `BEGIN-WITH-UNACCEPTED-KEY`), a key on the other channel lets it go (witness `begin_other_key` in the result), a key seen on the carrying channel while begin
runs waits at the first proof, a working pair refuses only a move onto the channel with the
unaccepted key, a rollback and a Stop do not depend on keys, property `MOVE-ONTO-UNACCEPTED-KEY`, and the failover and return
liveness are checked towards a clean channel whatever the key of the other one. `blocker` is the code before the fix, kept to
show what the fix removed: failover, return, stop-wins and EF-START all fail with it (`test_key_gate.py`). `Supervisor.tla` states
both variants (constant `KeyPin`). Trace conformance does not run `enforce`.

TLA+ (`tools/formal/tla/Supervisor.tla`) has these rules too, and TLC checks them in every CI profile.
