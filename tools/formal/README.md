# Formal model of the Auto supervisor / Формальная модель супервизора Auto

`model.py` is an exhaustive explicit-state model checker of the pair-mode supervisor (offline, standard library only,
Python 3.9+). Full analysis and the counterexamples К1–К10 are in [REPORT.ru.md](REPORT.ru.md) (snapshot of 03.11.2026;
the model was extended afterwards with the K11 leak family and the individually switchable fixes below).
`ci_check.py` runs reduced profiles of it in the offline CI and compares the result with `expected.json`.
Nothing here touches a router.

## What CI checks

`qa/run_offline_ci.py` runs `python3 tools/formal/ci_check.py` as a separate check (own 3600 s limit; it needs about
2–3 minutes with 2 CPUs and under 0.6 GB; the profiles run in 2 worker processes). It runs six profiles (each below 0.32 M states; the full profile has 4.7 M states, ~20 min,
~3 GB and stays a manual run: `sh tools/formal/run_full.sh`) of the variant `fix` =
the released code. Properties: P1 LAN traffic never leaves outside a VPN tunnel (leak families), P2 no two transactions,
P3 no route write after Stop, P6 no permanent HELD, P7 failover liveness, owner-Stop liveness, journal/kernel consistency.

The result is a set of *violated properties* (signatures such as `LEAK:k3-held-on-reserve-without-guard`,
`TRANSITION:RETURN-BEFORE-HOLD:cl-rec`). `expected.json` lists every signature that is allowed to occur:

| status | meaning | when CI is red |
|---|---|---|
| `xfail` + `"k": "K2"` | known counterexample, not fixed yet | the violation **disappears** (XPASS: flip it) |
| `accepted` | known, by design or a model artifact (comment says why) | never; an accepted signature may be absent |
| not listed | must not happen | the violation **appears** (new bug or regression of a fixed К) |

So CI is green now, turns red when a *new* violation appears, when a *fixed* К comes back, and when an `xfail` K starts
passing without being flipped (so a fixed К cannot stay unguarded).

## Current status of К1–К10

К1 fixed (58921e2f, in the model's baseline). Fixed and switched on in `expected.json` `"fixed"` (integ/alpha8, merge of
`fix/formal-k2-k5-20261103`, 04.11.2026): К1 tail (`K1T`), К2 (`RETURN-BEFORE-HOLD:*`), К3 (`LEAK:k3-…`), К4 (`LEAK:k4-…`,
`LEAK:other-running`), К5 (`COMMITTED-AFTER-STOP`), К9 (`LEAK:k9-…`) and К11 (`LEAK:k11-…`: the Start hand-over raced by
an in-flight cleanup pass; fix: `pair.cleanup` re-reads the record under the control lock before its STOPPING write and
ends without a write when the hand-over finished it - model switch `K11`, transition `CL0 superseded`). No xfail is
left. Accepted: К6 (`ROLLBACK-ONTO-DEAD-PRIMARY:*`), К7 (`EF-START` and stop-wins with
faults: ROLLBACK-GIVEN-UP needs the operator), К8 (`LIVENESS:stop-primary-down`), К10 (`INCONSISTENT`, faults-power only,
possibly a model artifact) and the by-design windows `begin-instant`, `recovery-window`, `after-the-owner-stop`.
The authoritative list is `expected.json`.

## How to flip an xfail when the fix lands

The model is a hand-written abstraction of the Lua/Python code, so a flip is two things in **one commit**:

1. The fix is merged in the code (e.g. `fix/formal-k2-k5-20261103`: К1-tail, К2, К3, К4, К5, К9).
2. In `expected.json` add the К to `"fixed"` (the model then runs with that fix: `model.py --variant fix --fixed K2`;
   valid names `K1T,K2,K3,K4,K5,K9,K11`) and **delete** the `xfail` entries with `"k": "K2"`.
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
