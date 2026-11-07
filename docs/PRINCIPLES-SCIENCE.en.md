> **Alpha9 validation boundary.** The tables below retain historical simulator results. The alpha8 timing audit failed A1 (decision timing) and A2 (return timing with the registered settings). The 4.6–5.0 s dense-period range remains an assumption pending direct measurement. Alpha9 also enables absolute-grid probe spreading by default, which needs its own validation. Absolute detection/ride-out times and switch rates below are not validated properties of this release and do not authorize changing defaults.

> **Independent re-check of 2026-11-07.** The registered simulation re-checks run after this text was written (HMM pair, CUSUM pair, Kalman pair, ski-rental pair, survival, Pareto composite, phases) all ended CRITERIA_FAIL; none gave a completed positive result. For the Kalman pair (Kalman/PID probe-rate controller against the fixed level-5 baseline; a research arm, not the `rtt_watch` signal) a paired bootstrap of the 96 registered hypotheses showed: of the 66 point-PASS, 51 are supported at the old α allocation (53 at the IUT level); 9 delay non-inferiority claims (L30, L40, RAMP) are not supported; 6 (CREEP) are degenerate at the horizon. The method stays CRITERIA_FAIL: the delay-reduction branch fails in all 21 cells (nowhere at least 15 % faster). The point-PASS count is not a result. Figures marked `[simulator]` below are historical (older simulator, versions alpha6/alpha7/alpha8, small n) and were not reproduced by that check; sentences the re-check contradicts have been corrected in place. The defaults named in this document (HMM theta 0.8, return P(healthy) 0.90, `primary_stable` 120 s, `rescue_stable` 10 s, flap limit 2 per 60 min, Fibonacci retry pauses, probe phase spreading) are **experimental: chosen in simulation, not validated on hardware**.

<!-- doc-role: current -->
# Principles from the sciences in HomenS.AI Auto VPN: mathematics, physics, biology, cryptography, Fibonacci

[Русская версия](PRINCIPLES-SCIENCE.ru.md) · [How it works](HOW-IT-WORKS.en.md) · [Version and evidence](CURRENT-STATUS.md) · [Measurements](MEASUREMENTS.en.md)

Why this project has so much mathematics, physics and biology. These experiments exist because the author, Serhii Khomenko, has always loved these sciences, even though they never came easily to him. That is why every idea is tested honestly: compared with the previous method in the simulator and on the router, and only what is really better is kept.

State as of 04.11.2026. Author: Serhii Khomenko (HomenS.AI). The document describes methods; it does not promise a result on your router. It is a reference: it enables nothing and changes nothing in how the program works.

## 0. In short

For each bottleneck the program took a ready idea from a science, compared it head to head with the old method and kept the winner. Some ideas lost, and that is recorded as carefully as the wins.

| Science | What was taken | One-sentence result |
|---|---|---|
| Mathematics | a hidden Markov model instead of "3 in a row", Bayesian server pick, Markov availability model, exhaustive state search, honest statistics | old simulator figure: unneeded switches on a 15 s blip 100 % → 0.7 % (n=300; not reproduced by the registered re-check, where neither the HMM nor the simple rule leaves on 15 s while the HMM still leaves on 20–21 s). On a long outage the HMM leaves about 3–5 s later and costs more per day than the simple rule; it wins on flapping and heavy loss. Simulator only, not validated on the router |
| Physics | penalty decay with a half-life (RFC 2439), the square-root law, erasing the "memory" of a connection, the MTU black hole, Little's law | flap memory of 60 min instead of 15 min: cost −46…−49 % (simulator, not yet validated); square-root law: 46 % fewer probes for +0.76 % loss (simulator, not yet validated, not enabled) |
| Biology and evolution | a genetic algorithm versus simulated annealing for tuning settings; immune memory and homeostasis (ideas so far) | the algorithm exposed a discrepancy in the code (`rescue_stable`); the model matched the router on 22 of 23 points (on the same data it was fitted to); the GA-tuned values `primary_stable` = 120 and `rescue_stable` = 10 are not yet validated |
| Fibonacci and the golden ratio | Fibonacci retry pauses, probe phase spreading, golden-section search | Fibonacci pauses with a 15 s cap and jitter were 9–17 % cheaper than a fixed 5 s without jitter in the old simulation; they are the default but not proven better than a fixed 5 s + jitter (a herd of 30: 36 s versus 37 s, within noise; the checking analysis is blocked or pending); the golden-ratio phase layout failed against uniform spacing; Fibonacci in flap damping lost (+10 %) |
| Cryptography | pinned TLS roots and a one-time nonce, usign release signing with a hash chain, age encryption, server key pinning | 4–13 TLS roots per probe host instead of ≈140; signatures exchanged with real usign matched byte for byte (153 of 153 chain entries) |

The main honest warning: **almost everything is proven in the simulator and in tests, not on the router.** On the router (one GL-MT3000, IPv4) today there are only:

- fast detection of 6.3–7.9 s, late-switch recheck, flap damping, reserve-server change (samples n = 1–15, below the 59 rule);
- the first P95 from n ≥ 59 (section 7): 61 cycles of version 2.1.0-alpha7, traffic moved in 21.4 s (median), empirical P95 29.8 s (an estimate), maximum 84.2 s (the 95 % upper bound of the true P95, for independent cycles);
- a failure preserved as evidence: the MTU black-hole check did not work in alpha7 (0 of 5).

Not yet verified on the router: the HMM detector and the 0.90 return condition (in the alpha8 integration), Bayesian server pick, probe authenticity, SQM, release signing, age/TOFU, GL sensors.

## 1. How to read this document

### 1.1 Number provenance labels

| Label | Meaning |
|---|---|
| `[router]` | measured on the dedicated GL-MT3000 (soak logs, LAN client, test history) |
| `[simulator]` | computed by a model, a simulation or a tick simulator that runs the product code |
| `[tests]` | result of automated tests, mutation checks, state-space search, official test vectors |
| `[router, small n]` | measured on the router (soak logs) but with fewer than 59 events (the 59 rule): the number is an estimate with a wide confidence interval, not a guarantee |
| `[calculation]` | a formula or arithmetic (Wilson interval, the 59 rule, the square-root law) |
| `[no data]` | the sources have no value; no number is invented |

### 1.2 Statuses

| Status | Meaning |
|---|---|
| implemented | present in the integration code. "Implemented, default, not proven" means the code is on by default but its benefit is not validated (simulation only or an unfinished check). The last package verified on the router is 2.1.0-alpha7 |
| in a branch | code and tests exist in a separate git branch, not merged into the integration |
| research only | computed in the simulator, not in the product |
| not implemented | an idea in the plan, no code and no calculations |

### 1.3 Honest-statistics rules

These rules apply to every number below (details in section 2.3).

- **The 59 rule.** The maximum of n independent measurements is an upper 95 % bound of P95 only when n ≥ 59. Below that, "P95" is an estimate, and for n ≤ 19 it simply equals the maximum. At every n the empirical P95 itself is only an estimate: it covers the true P95 in just about 57 % of cases at n = 59, 35 % at n = 60, 38 % at n = 100 and 43 % at n = 300. The 95 % upper bound is a different, separately computed order statistic X_(s), the smallest rank with P(Binomial(n, 0.95) ≤ s−1) ≥ 0.95: the maximum for 59 ≤ n ≤ 92, X_(n−1) for 93 ≤ n ≤ 123, X_(99) at n = 100, X_(292) at n = 300. The 95 % holds for independent samples only; consecutive cycles of one bench are autocorrelated, which lowers the effective n and the real coverage. `[calculation]`
- **The logarithm form of the rule.** One needs n ≥ ln(1−C)/ln(q). For P95 at 95 % confidence: ln 0.05 / ln 0.95 = 58.4, so 59; for P99 it is 298.1, so 299. `[calculation]`
- **Wilson interval** for proportions "k of n" (95 %). "3 of 3" proves only a lower bound of 43.8 %.
- The label "n=… <59" is attached to every number with a sample smaller than 59.
- Different program versions are never pooled into one sample: pooling gave a P95 of 88 s instead of 38.5 s for current builds. `[calculation]`

## 2. Mathematics

### 2.1 Hidden Markov model (HMM) instead of "3 failures in a row"

**Problem (why it was taken).** The rule "3 failed checks in a row" leaves the channel during a 12–20 s blackout even though by the time of the switch (≈20 s of "price") the channel is already alive. On constant 10 % loss it switches ≈10 times a day, on 20 % ≈59 times (flapping). `[simulator]`

**Goal.** Move to the reserve only when the failure will probably last longer than the switching cost C = 20 s. Stay on a short failure and on a small loss.

**In plain words.** The program keeps six "versions" about the channel state: healthy, light loss, heavy loss, short blackout, long outage, dead DNS. Each version has a probability. Every check recomputes the probabilities (like a doctor refining a diagnosis after each test). The switch happens when the probability that "the failure will last at least 20 more seconds" reaches 0.8. A short blackout (about 4 s) hardly ever accumulates it, a long one does. The model finds out that the failure is long by how long it has already lasted.

**Formulas and details.**

- Six states {G, L, M, B, X, N}. Prediction over Δt: `g = e^(−ΛΔt)`, `π'_G = π_G·g + Σ_s π_s(1−e^(−Δt/dur_s))`, `π'_s = π_s·e^(−Δt/dur_s) + π_G·(λ_s/Λ)(1−g)`.
- Update by observation (O healthy, D DNS-001, H HTTPS failure): `π'_s ← π'_s · P(obs | s, rhythm)`, normalisation, probability floor 1e-9.
- Decision: `persist = Σ_{s∈{M,B,X,N}} π_s · e^(−C/dur_s) ≥ θ`, with θ = 0.8, C = 20 s, dur_B = 4 s. A short blackout contributes only e^(−5) = 0.7 % of its mass, a long outage 97.8 %.
- A dense probe (3 s wait) is 2–4 times more sensitive to loss than a normal one; the probe rhythm is part of the model.
- The return condition uses the same model: P(healthy) = π_G ≥ 0.90 (owner's decision of 03.11.2026; it was 0.95).

**Where in the program.** `channel_model.py` / `lua/channel_model.lua`; setting `failure_model = hmm` (default) | `hmm-fast` | `consecutive`. Status: **implemented** (alpha8 integration); the alpha7 package verified on the router does not have this model. Files: [channel_model.py](../router/files/usr/lib/homensai-vpn/channel_model.py), [channel_model.lua](../router/files/usr/lib/homensai-vpn/lua/channel_model.lua), description: [HMM-DETECTOR](architecture/HMM-DETECTOR-2026-11-03.ru.md) (Russian).

**Experiments.**

- Detection study: a packet-level channel model calibrated to the MT3000 (best k=6, rto=0.6 s), n = 300 runs per point, 295 usable log cycles. The reconstructed rule matched the router's decision in 38 of 38 phase-2/3 cycles. `[simulator]`
- Product tick simulator (runs the real functions), n = 200 per point. `[simulator]`
- Shared Lua = Python tests: 20 sequences, 29 `evaluate` cases, 8 probe streams; mutation check with 48 mutants (46 of 48 in the last run, the remaining two checked individually and killed). `[tests]`

**Results (n = 300, Wilson interval 95 %; lower bound rounded down, upper bound rounded up).**

| Metric | "3 in a row" (alpha6) | + recheck (alpha7) | HMM (alpha8) |
|---|---|---|---|
| 15 s blackout: unneeded switch | 100.0 % [98.7…100.0] | 10.0 % [7.0…14.0] | 0.7 % [0.1…2.4] |
| 20 s blackout: unneeded switch | 100.0 % [98.7…100.0] | 86.0 % [81.6…89.5] | 0.3 % [0.0…1.9] |
| 40 s blackout: traffic on reserve, median | 20.1 s (P95 21.7) | 20.1 s | 24.7 s (P95 25.8) |
| 20 % loss: switch within 150 s | 9.7 % [6.8…13.6] | 4.0 % [2.3…6.9] | 1.7 % [0.7…3.9] |
| 40 % loss: switch within 150 s | 97.7 % [95.2…98.9] | 93.0 % [89.5…95.4] | 99.7 % [98.1…100.0] |
| 40 % loss: traffic on reserve, median | 43.2 s (P95 115.6) | 42.6 s | 33.6 s (P95 90.6) |
| Constant 20 % loss: switches per day (3 days) | 59.0 | 38.3 | 0.33 (1 in 3 days, few events) |
| "Noisy" day: unneeded switches (10 days) | 10.8 | 0.80 | 0.60 |

All rows `[simulator]`. On the product tick simulator (n = 200) alpha7 → alpha8: 20 s blackout — a switch in 78 % of runs (20.3 s) versus 1 % (36.1 s); 40 % loss — 94 % (41.8 s) versus 99 % (29.0 s). `[simulator]`

**Old versus new.** The HMM wins on false switches in some scenarios (flapping, heavy loss), but it is not an overall winner. In the registered daily simulation (three dense-period settings) the HMM costs more per day than the simple consecutive rule (J +31…+61 per day, interval excludes 0), it leaves about 3 s later on long outages, and it is worse on constant partial loss. On blackouts of 15 s neither the HMM nor the simple rule leaves; on 20–21 s the HMM still leaves, noticeably less often than the rule but not rarely (roughly 0.4 unneeded leaves per event, derived from the cost formula); the claim about loss up to 20 % is unproven (5 and 10 % passed). Simulator only. Where it loses:

- on a real long outage traffic leaves later: +4.7 s (24.7 versus 20.1 s; n=300) and +3.3 s on the tick simulator (40 s blackout: 20.6 → 23.9 s; n=200). This is a deliberate price for "do not leave for a failure shorter than the switching cost";
- on "noisy" days the simulator gave +1 unneeded switch (one run, seed 9, n=1 <59). `[simulator]`

Rivals: Wald's sequential test (SPRT) is almost as good on false switches but slower at 40 % loss (median 58.1 versus 33.6 s); CUSUM gives 1.0 false switches a day on "noisy" days versus 0.60 for the HMM. At 30 % loss every detector flaps (HMM 33 a day); that is cured by the return condition. `[simulator]` CUSUM stays off: in the registered re-check (60 worlds) the false-alarm gate failed in several contexts, and with only 60 worlds it cannot be passed even with 0 alarms (the 95 % bound at 0 of 60 is still thousands a day), so the check is conservative; it is not validated on the router.

**Router.** The HMM itself has not been validated on the router `[no data]`; it is the default but labelled experimental: selected in simulation, not validated on hardware. Nearby things were tested: fast detection (1 Hz ICMP heartbeat + dense probes) gave 6.3–7.9 s `[router]`; alpha7 late-switch recheck: 15 s blackout — 0 switches of 3 [Wilson 0…56.2 %], 20 s blackout — 3 of 3 [43.8…100 %]; n=3 <59 `[router]`.

**CPU.** Per probe: counter 0.85 µs, SPRT 3.1 µs, HMM 19.6 µs (CPython on a PC, `[simulator]`); Lua 5.1 in a CI container 3.4–3.5 µs per step. MT3000 estimate (factor ×5–10, not measured on the router): ≈0.1–0.2 ms per probe, ≤3.5 s CPU a day = 0.004 % of a core. `[calculation]`

### 2.2 Binomial guarantees and k-of-n quorum

**Problem.** The rule "N losses in a row" was chosen by eye. It was unclear how many false alarms it gives per week, and what several independent sensors would give.

**Goal.** Choose N and the "k of n" rule from a given false-alarm budget, not by eye.

**In plain words.** If a check is lost randomly and independently, then N losses in a row is a rare event whose frequency a formula gives. If the answer comes from three sensors instead of one and the alarm is raised when at least two are silent, false alarms caused by **single-probe noise** become hundreds of times rarer. That is a guarantee against the noise of one probe only: it promises nothing against real short outages of the channel (see "Two numbers of the guarantee" below).

**Formulas and details.**

- Independent loss p. "N in a row": alarms per probe `(1−p)·p^N`. Probability of at least one in T probes ≈ `1 − exp(−T·(1−p)·p^N)`.
- Quorum of m sensors: a "bad moment" if ≥k of m are lost: `q = Σ_{j≥k} C(m,j)·p^j·(1−p)^(m−j)`; then N bad moments in a row: `(1−q)·q^N`.
- A sliding "k losses in a window of n" is computed with an exact Markov chain over the 2^n window states; Gilbert–Elliott bursts by the stationary distribution.

**Two numbers of the guarantee, not one.** The formula `p^k` (for a window `(1−p)·p^N`) describes **only the single-probe noise of one probe**. The second number is real short natural outages of the channel; it is 5–6 orders of magnitude larger than the first and is counted separately:

- The first number, `p^k`: the failing-probe rate p = 0.060 % (95 % CI 0.019…0.140 %; 8,361 probes, 23.2 channel-hours, 5 failing probes); three in a row give 2.1·10⁻¹⁰ per window, 1.9·10⁻⁶ a day per channel. `[router, small n]`
- The second number: failing probes come in runs, not independently. In the same 23.2 channel-hours there is 1 run of ≥3 failing probes in a row, that is **≈0.04 per hour per channel (95 % CI 0.001…0.24)**; by the `p³` formula 1.4·10⁻⁶ windows were expected in 6,601 windows, 2 were observed. The order of magnitude changes by 5–6 orders because these are not sensor noise but short (10–40 s) outages of the channel itself. `[router, small n]`
- The third: the **effective number of independent sensors in the quorum is ≈1.2–1.9** for path failures. All three HTTPS targets (1.1.1.1, 8.8.8.8, 9.9.9.9) share one tunnel and one WAN; when the path fails they fail together. Kish's correction `n_eff = n/(1+(n−1)ρ)` for three targets gives 1.88 at ρ = 0.3, 1.50 at ρ = 0.5 and 1.15 at ρ = 0.8 (at ρ → 1 it is one sensor). So the 2-of-3 quorum mainly protects against the failure of one target or one server, not against a path failure. `[calculation]` The range of ρ is a scenario, not a measurement (the earlier `[router, small n]` label did not apply to it): nothing was recorded per target in the soak logs, so the pairwise correlation of targets could not be measured. For a direct measurement a per-target log was added (`probe_target_log`, [PER-TARGET-PROBE-LOG](architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md), in Russian).

**Where in the program.** The N and quorum arithmetic is not in the product as a formula: the switch decision uses the HMM (2.1). The 2-of-3 quorum for the heartbeat is in the branch `feat/gl-sensors-20261104`, **off by default** (`heartbeat_quorum`). Status: **in a branch** (quorum), the formulas are **research only**. Study: `private/math/wave3` (section 2).

**Experiments.** 19 cases checked by simulation (independent losses, Gilbert–Elliott, sliding windows); 18 of 19 within ±2σ, the outlier (4 of 8, p=0.1; z=2.89) was recomputed on 12 million probes and agreed (2.062·10⁻³ versus 2.067·10⁻³). `[simulator]` For the sensors branch: a quorum simulator, 3 days per scenario, 400 outages. `[simulator]`

**Results.**

- With independent losses p = 5 %, N = 3: "1 of 1" gives 10.26 false alarms a day, "2 of 3" gives 0.033. `[calculation]` This is **against single-probe noise only**; against real short outages of the channel the number is different: ≈0.04 runs per hour per channel (95 % CI 0.001…0.24). `[router, small n]`
- The effective number of independent quorum sensors for path failures is ≈1.2–1.9 of three (a shared tunnel and WAN). `[router, small n]`
- For the same guarantee "≤1 a month" at p=5 % N=5 is needed versus N=3 with a quorum (2 s faster at 1 Hz). `[calculation]`
- Bursts break the guarantee by orders of magnitude: with 3–10 s bursts the same N=3 gives 75–105 alarms a day instead of 0.09 (900–1200 times more). That is why counting "in a row" alone is not used for the decision; dense probes and the HMM are needed. `[calculation]`
- The sensors branch (2-of-3 heartbeat with target rotation): false suspicions at 5 % loss 210 → 6.3 a day; but 30 % partial loss is found **worse** (mean 14.5 s and 51 % within 10 s → 26.9 s and 26 %) and costs three times the echoes (3 instead of 1 per beat). `[simulator]`

**Comparison.** The winner with independent sensors is a 2-of-3 quorum with N=3 (a false moment 7 times rarer: 0.0073 versus 0.05). It loses on: sensors must be independent (a shared tunnel failure correlates them: for path failures n_eff ≈1.2–1.9 instead of 3), it catches ~30 % loss more weakly, it costs more echoes. So in the branch it is **not strictly better** on every metric and ships off.

**Router.** The quorum itself has not been tested on the router `[no data]`. Background rates, runs of failing probes and the correlation correction come from the MT3000 soak logs (27 logs, 589 cycles, a strict sample of 23.2 channel-hours): `[router, small n]`, 5 failing probes in 2 runs; source — `private/math/sensor-correlation` (`REPORT.ru.html`). The quorum source: `docs/architecture/GL-SENSORS-2026-11-04.ru.md` in the branch `feat/gl-sensors-20261104` (the file is not in this tree yet).

### 2.3 Honest statistics: Wilson, the empirical P95 and its upper bound, the 59 rule, the logarithm form

**Problem.** Of 509 P95 values published in the test history, none rested on n ≥ 59, 507 were simply the sample maximum, the largest sample was 21. `[calculation]`

**Goal.** Never call an estimate a bound. Show how many measurements stand behind a number and what can be claimed from them.

**In plain words.** If you measured 4 times and the worst result was 47 seconds, you cannot say "in 95 % of cases faster than 47 s". You can only say "with 95 % confidence at least 47 % of cases are not slower than this maximum". A bound on the true P95 needs 59 measurements, and the P95 shown from them is still an estimate.

**Formulas and details.**

- The chance that all n measurements are below the true P95 is `0.95^n`. For n=59 it is 0.0485 < 0.05, for n=58 it is 0.0510. Hence `n ≥ ln(1−C)/ln(q)`: P95 — 59, P99 — 299. `[calculation]`
- The maximum of n measurements covers at least `100·0.05^(1/n)` % of cases with 95 % confidence: n=4 — 47.3 %; n=14 — 80.7 %; n=20 — 86.1 %; n=59 — 95.0 %; n=93 — 96.8 %. `[calculation]`
- Minimum n: maximum ≥ P95 — 59; a two-sided P95 interval with 2.5 % tails — 72; second largest ≥ P95 — 93; maximum ≥ P99 — 299; "failures < 5 %" with 0 failures — 59. `[calculation]`
- Wilson interval: `p = k/n, d = 1+z²/n, c = (p+z²/2n)/d, h = z·√(p(1−p)/n + z²/4n²)/d`, interval `c ± h`, z = 1.96. "3 of 3" → 43.8…100 %; "59 of 59" → 93.8…100 % (printed conservatively: the lower bound rounded down, the upper bound up to one decimal, so 43.85 % is shown as 43.8 %); "0 of 10" → 0…27.8 % (exact upper ≈ 3/n = 25.9 %). For "n of n" to guarantee success ≥ 80/90/95/99 %, n = 16/35/73/381 in a row are needed. `[calculation]`

**Where in the program.** PC test bench: `soak-24h/honest_stats.py` and `soak_report.py` (they print "P95≈X (n=…, too few samples: need ≥ 59)"). In the product and CI — the branch `feat/honest-p95-formal-ci-20261103`, **not merged** into alpha8. Status: **in a branch** (the bench already uses it).

**What the two numbers mean.** The printed P95 is the sample's own 95th percentile, an estimate at every n. For n = 60, 100 and 300 it covers the true P95 in only about 35 %, 38 % and 43 % of cases (57 % at n = 59). Over the whole range 59 ≤ n ≤ 300 this coverage stays between 35 % and 57 %, so the empirical P95 is never a 95 % upper bound. The 95 % upper bound is the separately computed order statistic (the maximum for n = 59…92, the 99th of 100 at n = 100, the 292nd of 300 at n = 300), valid for independent samples; repeated cycles of one bench are autocorrelated, so the effective n is smaller and the real coverage is lower than 95 % (rough heuristic n_eff = n(1−ρ)/(1+ρ): for n = 59–61 the maximum covers about 80 % at ρ = 0.3 and 64 % at ρ = 0.5). `[calculation]`

**Experiments and results.** Example from the availability report (`primary-drop`, traffic moved): n=20, median 35.9 s, P95 38.5 s, lower 95 % bound 37.2 s; an upper bound cannot be given (the maximum covers only P86). `[router]`, n=20 <59. Version mixing: P95 88 s versus 38.5 s. `[calculation]` The old print "P95 = 39.3 (n=15)" is now "P95≈39.3 (n=15, too few samples: need ≥ 59), with 95 % confidence ≥ 81 % of cases are not slower than the max". `[router]` The first P95 from n ≥ 59 on the router (with a separately computed upper bound) is in section 7.

**Comparison.** The new form is more honest, the figures are the same; the cost is bench time: ≈3.5–5.6 h for 59–93 cycles per fault type and version.

**Sources:** `private/math/availability/p95_honesty.json`, `private/soak-24h/honest_stats.py`, [MEASUREMENTS](MEASUREMENTS.en.md).

### 2.4 Bayesian server pick and the UCB bandit

> **Validation status (2026-11-07).** Not yet validated: the figures come from an older simulation (n = 40) and the registered re-check is pending. Bayesian pick is off; the default is the simple rule with 20 % hysteresis.

**Problem.** Inside a channel (for example a NordVPN pool) a server must be chosen from noisy latency measurements. The simple rule "switch if better by 20 %" with measurement noise σ≈0.39 gives ≈42 useless switches a day of an idle channel on two equal servers and extra flash writes. `[simulator]`

**Goal.** Change the server only when confident that the candidate is faster; measure less; do not wear the flash.

**In plain words.** For each server we store not one number but a "cloud of possible values": how fast and how reliable it is, adjusted for how many measurements exist. Old measurements are gradually "forgotten" (half-life 1 hour). The server changes only if the probability "the candidate is faster" is at least 0.95. To avoid getting stuck on a mediocre one, the program sometimes probes servers about which little is known: this is the "multi-armed bandit" idea.

**Formulas and details.**

- Latency: a normal-inverse-gamma posterior of log RTT. Availability: `Beta(answered+1, not answered+1)`.
- Forgetting: all data decay with a half-life `HALF_LIFE` = 1 h (measurement weight `2^(−Δt/3600)`).
- Switch: `P(candidate faster) ≥ 0.95` (z ≥ 1.645), the candidate answered in this round and has availability ≥ 80 %. If the current one did not answer, the best live one is taken.
- UCB bandit: each round measures the current server, servers without data, servers not measured for an hour, and those that may still be the best. Never more measurements than in the simple model.

**Where in the program.** `server_pick.py` / `lua/server_pick.lua`, function `bayes_round`; setting `server_pick_model = simple` (default) | `bayes`. Status: **implemented but off by default**, because it is not strictly better on every metric. Files: [server_pick.py](../router/files/usr/lib/homensai-vpn/server_pick.py), [server_pick.lua](../router/files/usr/lib/homensai-vpn/lua/server_pick.lua), [SERVER-PICK-DESIGN](architecture/SERVER-PICK-DESIGN-2026-11-02.ru.md) (Russian).

**Experiments.** The real `server_pick.py` code, 40 runs per point, noise σ 0.2–0.6, scenarios: two and four equal servers, better by 10 % and by 30 %, slow degradation, dead, six different. `[simulator]` Lua = Python tests on shared cases. `[tests]`

**Results (σ=0.39, n=40 <59, `[simulator]`).**

| Metric | Simple rule | Bayes |
|---|---|---|
| Useless switches a day, 2 equal servers | 41.94 | 0.59 |
| same, 4 equal | 69.30 | 1.35 |
| same, 6 different | 28.18 | 0.00 |
| Share of time on the best, better by 10 % | 0.624 | 0.791 |
| Share of time on the best, slow degradation | 0.898 | 0.883 (tie) |
| Time to find the best (better by 30 %), min | 4 | 46 |
| Time to find the best (better by 10 %), min | 13 | 251 |
| Measurements per hour, 6 servers | 108.0 | 64.0 |
| Settings rewrites a day, 4 equal | 95.9 | 32.9 |

**Comparison.** Bayes wins on useless switches (by tens of times), on measurements (−41…−51 % with six servers) and on flash wear; it **loses on the speed of finding the best** (46 versus 4 min) and on slow degradation (tie). So the simple rule stays the default. Reserve-server change done by Auto itself (not Bayesian): LAN client downtime 7.1 s (alpha1, n=4 runs) → 0.2 s (alpha2, n=2) `[router]`, n <59.

### 2.5 Exhaustive state search (formal model, K1–K11)

**Problem.** The Auto supervisor is a set of timers, locks, restarts and power cuts. Errors in rare event orders are not found by tests.

**Goal.** Find all reachable states and verify that dangerous ones never occur (LAN not bypassing the VPN, no eternal HELD, return only after the hold).

**In plain words.** A model of the program is "played" in all possible event orders: failure, restart, power cut, manual Stop. If a sequence leads to a bad state, it is returned as a counterexample. This is how protocols that cannot be checked by eye are verified in aircraft and clouds (AWS has described this approach since 2015).

**Formulas and details.** Explicit-state breadth-first search; invariants (P1 LAN not bypassing the VPN, P2 never two transactions at once, P3, P7, P9); the property "no eternal HELD" as `AG EF`; liveness over bottom strongly connected components under fairness. The checker is home-made in Python (no Java on the PC, so not TLA+/TLC).

**Where in the program.** An offline tool `private/math/formal/model.py`, not in the router. The K1 fix is merged; K2–K5, K9, K11 are in the branch `fix/formal-k2-k5-20261103`, **not merged**. Status: **implemented as a checking tool**, fixes — **in a branch**.

**Experiments.** Seven profiles, up to 4,718,088 states and 36,984,380 transitions (profile full, with fix 58921e2f); profile held without the fix — 67,400 states, with it — 149,768. `[tests]`

**Results.**

| No. | Finding | Status |
|---|---|---|
| K1 | eternal HELD after an edit in GL: violated in 29,440 states (held) and 1,311,552 (full); the same bug was observed on the router | fixed (58921e2f), merged |
| K2 | a restart resets the extended hold during flapping | branch, not merged |
| K3 | after a power cut in HELD-ON-RESERVE no VPN-only guard, LAN unprotected up to 600 s | branch, not merged |
| K4 | with a slow vendor the guard is released before clients are up (90 s versus ≈170 s) | branch, not merged |
| K5 | revision check and COMMITTED write are not under one lock (harmless) | branch, not merged |
| K6–K8 | rollback to a dead primary, ROLLBACK-GIVEN-UP, Stop with a dead primary | by design |
| K9 | an edit in GL, then power: LAN follows the GL configuration without VPN-only | owner's decision: keep the guard; branch |
| K10 | kernel reload failure during rollback (possibly a model artefact) | only under faults |
| K11 | the Start hand-over races an in-flight cleanup; found on the model with fixes, a real bug | fixed in the branch (not added to the model) |

`[tests]`. On the fixes branch: 16 + 16 counterexample tests, mutations 45 of 45 caught; after the fixes the K3, K4, K9 profiles show 0 violating states. `[tests]` K3–K9 not verified on the router.

**Comparison.** There is no "tests only" number for the old way; the search found K1 before it was fixed blindly, and K11 after the fixes. Weak spot: the home-made checker has not been independently cross-checked with TLC/SPIN.

**Sources:** `private/math/formal/REPORT.ru.md`; `docs/architecture/FORMAL-FIXES-2026-11-03.ru.md` in the branch `fix/formal-k2-k5-20261103` (the file is not in this tree yet).

### 2.6 Markov availability model

> **Validation status (2026-11-07).** Not yet validated: simulator only (the registered check is pending); the 287 → 29 min/month figure is a model, not a measurement.

**Problem.** How many minutes of downtime a month does each version give, and what can be improved at all: the seconds of switching or the independence of the reserve?

**Goal.** Convert switching seconds into monthly downtime minutes and show where the gain ends.

**In plain words.** The system is a few states (both channels alive, switching, running on the reserve, both down). Transitions between them happen at their own rates. From these, the share of time without connectivity is computed.

**Formulas and details.** A continuous Markov chain: U (both alive), D (detection and transfer window), R (on reserve), H (hold before return), B (return window), S (reserve down), XP/XR (both down), Y (reserve fell under traffic), C (common failure with share ρ). Windows are Erlang distributions with 40 phases (almost a fixed timer). Per failure `E = M·(1−e^(−T/M)) + e^(−T/M)·T_ret`; per month `D ≈ N·[(1−ρ)·E + ρ·M] + 43200·λP·λR·M²`.

**Where.** `private/math/availability/model.py`, an analysis tool, not in the router. Status: **research only**.

**Experiments.** Checked by event simulation, 20 series × 10 years: 29.0 versus 29.6 min [28.7; 30.6]. Parameters taken from router measurements (transfer 21.4–35.9 s, return 1.32 s, hold 53 s). `[simulator]`

**Results (one primary failure a day, ρ=0, server repair 30 min).**

| How it works | Packet downtime, min/month | For applications | "Nines" |
|---|---|---|---|
| No Auto, fix after 1 h | ≈768 | ≈769 | 1.75 |
| No Auto, fix after 10 min | ≈287 | ≈293 | 2.18 |
| 1.0.0 (auto 153 s, return 42 s) | ≈108 | ≈125 | 2.60 |
| 2.1.0 (transfer 21–36 s) | ≈29–36 | ≈47–54 | 3.1–3.2 |
| 2.1.0 + alpha7 (estimate) | ≈30 | ≈32 | 3.2 |

`[simulator]`. Of the 29 min/month of 2.1.0 only ≈11 min are switching windows, ≈18 min are both channels down. With 10 % common failures (ρ=0.1) downtime is ≈113–120 min: further gains come from the **independence of the reserve** (another provider, country, protocol), not from Auto's seconds. One failure a week: ≈2–3 min/month. `[simulator]`

**Comparison.** The new version wins 3–3.7 times against 1.0.0 and 8–10 times against a manual fix after 10 min. Limits: server failure rates are an assumption; partial failures (10–30 % loss, MTU, DNS only) are not modelled; alpha7 values are an estimate, not measured on the router.

### 2.7 Pareto front, the "master slider" and the nightly advisor (golden-section search)

**Problem.** The detector has many settings (threshold θ, "wait-out" dur_B, heartbeat loss count, return condition, `primary_stable`, `rescue_stable`), while the user needs one understandable knob "fast reaction ↔ no unneeded switches".

**Goal.** Find the set of best compromises, reduce them to one curve and give advice along it from the history of the user's own network.

**In plain words.** Every setting improves something and spoils something. We went through all combinations, kept only those that cannot be improved on two indicators at once (the "Pareto front"), and stretched them onto one slider from 0 to 1. At night the advisor "replays" past days at different slider positions and recommends the one with the lowest total cost. It looks for the best position by golden-section search: the interval shrinks by 1/φ ≈ 0.618 each step, so only about 9 evaluations are needed.

**Formulas and details.**

- Cost = user downtime + 20 s per unneeded switch (+ 1 % of seconds on reserve in the slider simulation).
- Golden section on [0, 1] to accuracy 0.02: trial points `b − (b−a)/φ` and `a + (b−a)/φ`, φ = (1+√5)/2 ≈ 1.618. If the cost over the 11 anchor points is not unimodal, the best anchor is taken.
- A shift is recommended only if the saving is ≥ 5 % and there are ≥ 5 events; the "Auto" mode moves at most one step (0.1) a day and never during a fault.

**Where in the program.** The curve and front: `private/math/master-slider` (simulation). The advisor (network journal + `advisor.py`, `lua/advisor.lua`, nightly run at 03:30 with nice 19) and the master slider (`router/ui/advisor.js`) are **in the product since alpha9**. Status: **implemented, default mode `advice` (a person decides), not proven**; the curve and its numbers come from the offline study (a simulation calibrated on the MT3000), not from measurements of the user's router. The independent Pareto check did not confirm a smooth monotone trade-off (see below). Document: `docs/architecture/NETWORK-ADVISOR-2026-11-04.ru.md` in the same working copy.

**Experiments.**

- A grid of 23,616 combinations (8 θ × 6 dur_B × 3 LOSSES × 4 P(G) × 41 `primary_stable`/`rescue_stable` pairs); the 2,661 best points were recomputed on 4 more scenario sets, anchor points and defaults on 10 fresh sets (20 repeats per scenario). `[simulator]`
- Model check: the step filter was compared with the product `channel_model.evaluate` on 15,600 random probes — decisions matched in 15,600 of 15,600, the largest probability difference 1.9·10⁻⁴. `[tests]`
- Run 1 (29,520 points) exposed a scenario-horizon error; the data were kept as is (`grid-run1.jsonl`), run 2 became the main one. `[simulator]`
- Advisor: 150 random event sets against a grid search with step 0.01. `[tests]`

**Results.**

| t | θ | dur_B, s | downtime, s/day | unneeded/day | leave on a 40 s blackout, s | waits out up to, s |
|---|---|---|---|---|---|---|
| 0.0 ("fast") | 0.60 | 3 | 218.8 | 0.468 | 21.7 | 15.3 |
| 0.5 | 0.60 | 5 | 223.9 | 0.176 | 25.6 | 21.0 |
| 1.0 ("calm") | 0.65 | 6 | 232.6 | 0.078 | 26.5 | 23.4 |

All rows `[simulator]`, n = 10 sets <59, the absolute confidence interval of downtime ≈ ±10 s/day (paired differences ≈ ±6 s).

- Independent check (registered Pareto composite, 2026-11-06): CRITERIA_FAIL; of 18 method branches 3 passed and 15 failed, the front is not monotonic (`monotone_tradeoff` = false) and several anchor positions, including t = 0.8 in some periods, are dominated by others. The curve is a guide, not a guarantee. The figures below are the older simulator study. `[simulator]`
- The front is short: losses on it change only from 234 to 244 s/day, while unneeded switches change 25 times (0.81 → 0.03). A real choice between goals exists in one knob: how long to wait out an outage (15 to 24 s): unneeded switches 0.47 → 0.07 a day, the price is leaving for the reserve ≈7 s later on a real outage (19 → 26 s).
- The alpha8 default lies near t = 0.8: the same unneeded switches within the CI (0.049 versus 0.073), downtime about 7 s/day higher, almost entirely from the scenario "an hour of constant 30 % loss". The independent check lists t = 0.8 among the dominated anchors in the 4.6, 4.8 and 5.0 s periods, so this default is not an optimum. No default change is proposed before router verification.
- The advisor on synthetic weeks: calm — "keep" (saving 0 %); blackouts of 22–28 s × 12 a day — shift to 0.40, downtime −55.5 s/day, unneeded −0.80/day, saving 20.6 %; 120 s outages × 6 and 40 % loss — shift to 0.20, −223.7 s/day, saving 8.4 %. `[tests]`
- Golden section versus the grid: of 150 sets in 140 it matched the grid minimum, in the rest it was no more than 0.1 % costlier (the test requires ≤ 0.5 %); the method was used in 94 of 150. `[tests]`

**Comparison.** The new approach (one curve + advice) replaces manual tuning of six settings; the price of a choice is expressed in seconds. Where it loses: the curve is computed in the simulator (a different scenario mix than in section 4.1), absolute numbers from different studies must not be compared; not verified on the router; the idea "tune a threshold from history" overlaps Cisco patents (US 11 574 241, US 11 032 181), which needs a separate remark before publication (not a legal assessment).

**Router.** `[no data]`.

### 2.8 Ski rental: how long to wait out an outage

> **Validation status (2026-11-07).** The 2.2 % / 2.4 % figures were not reproduced by the registered re-check (CRITERIA_FAIL, all operational gates failed); the conclusion "do not ship ski rental" is unchanged.

**Problem.** A classic problem: rent skis or buy them? You do not know how long you will ski. Here: wait out the outage or pay the switching cost C ≈ 20 s, not knowing how long it will last.

**Goal.** Check whether a simple rule with the proven guarantee "no worse than 2× the ideal" beats the HMM.

**In plain words.** Wait for the "switching cost" and then leave: then we never pay more than twice what an omniscient observer would. A random moment of leaving lowers the worst case to e/(e−1) ≈ 1.58.

**Formulas and details.** The ideal that knows the outage length D: `OPT(D) = min(D, L+C)`, L ≈ 5.8 s (transfer delay). The deterministic τ = B gives ratio 2, the randomised one with density `e^(t/B)/(B(e−1))` gives e/(e−1) = 1.582.

**Where.** Not implemented. Status: **research only** (conclusion: do not implement).

**Experiments.** Detection simulator, primary blackout, 22 lengths D, 300 repeats per point; three length distributions (D1 — simulator mix, D2 — the HMM's own model, D3 — 11 natural events). `[simulator]`

**Results (D1, mean cost per outage).**

| Rule | cost, s | vs ideal |
|---|---|---|
| 3 in a row (alpha7) | 9.13 | 1.193 |
| HMM (product) | 8.86 | 1.157 |
| ski rental deterministic τ=B=26 s | 9.05 | 1.182 |
| ski rental randomised | 9.07 | 1.185 |

`[simulator]`. Worst case over length: HMM 1.78; deterministic 2.19; randomised 1.83.

**Comparison.** The winner is the HMM (ski rental is worse by 2.2 % and 2.4 %). Randomisation is not needed on one router: there is no adversary to defend against, and the HMM uses more information. With long tails (≥ 20 % of outages ≥ 2 min) deciding at the 2nd–3rd probe is cheaper (D2: 10.64 versus 12.05 s), but this was verified only for a blackout; revision threshold: the share of outages ≥ 120 s in real data above ≈ 10 %. Router: `[no data]`.

### 2.9 Survival analysis of outage durations (Kaplan–Meier, Weibull, exponential mixture)

**Problem.** Can "how long to wait" be derived from the distribution of outage durations instead of an HMM with set parameters?

**Goal.** Compare rules derived from statistics with the HMM.

**In plain words.** If an outage has already lasted 20 s, how likely is it to last that much longer? For "lingering" failures the probability of continuing grows with age. It is computed from records of past failures.

**Formulas and details.** Expected cost of threshold τ: `J(τ) = ∫₀^(τ+L) S(u) du + C·S(τ)`; optimality condition `h(τ)·C = S(τ+L)/S(τ)`, h is the hazard rate. A mixture of two exponentials (the HMM structure: a "short" and a "long" failure) describes the data better than Weibull (lower AIC) for D1 and D2.

**Where.** Not implemented; Status: **research only**.

**Experiments.** There are 11 natural events in the soak logs (lengths ≈5, 5, 5, 5, 30, 30, 40, 50, 140, 170, 280 s; exposure ≈18 h, 6,621 probes); tester-injected (netem) failures cannot be used for survival. `[router]`, n=11 <59. Simulation: cross-validation "a rule trained on one distribution, tested on another". `[simulator]`

**Results.** On D1 the best derived rule gives 8.88 s versus 8.86 for the HMM — a tie within 0.2 %. On D3 with n=11 the models are indistinguishable (AIC 117 versus 118; k=0.75 indistinguishable from 1). `[simulator]`

**Comparison.** The winner is the HMM (no worse and it does not need to know the distribution). Caveat: the theoretical optimum τ* is not optimal in the simulator, because detection itself already "waits out" 10–19 s. What to deepen: collect natural data (n ≥ 100 events) and recompute quarterly (section 10).

### 2.10 Bayesian "WAN or tunnel" diagnosis, WireGuard events and the passive "silent tunnel" sensor

**Problem.** When the router's own internet fails, both channels look "bad": Auto may switch in vain. After the WAN returns, the reserve comes up seconds earlier than the primary and takes the traffic (an extra switch there and back). Pings through the tunnel cannot tell "the filtered target is silent" from "the tunnel is dead".

**Goal.** Do not switch while the router's internet is provably down; check the primary faster when the WAN is alive but the tunnel is down; do not treat missing echoes as an alarm if data flows through the tunnel.

**In plain words.** Several independent "witnesses" (an echo through the WAN port bypassing the VPN, the GL firmware verdict, the link state, checks of both channels, WireGuard events) vote, but not equally: each has its own reliability. The result is probabilities of six versions ("all good", "tunnel down", "server silent", "both VPNs", "no internet at the router", "DNS"). The passive sensor watches the network card counters: if transmitted bytes grow while received ones do not for ≥ 3 s — a suspicion; if inbound data flows at ≥ 10 kbit/s, a missing heartbeat echo is not counted as an alarm.

**Formulas and details.** Naive Bayes: posterior `∝ prior · Π_i P(evidence_i | hypothesis)`, normalisation after each factor (identical in Lua and Python). Priors 0.968 / 0.012 / 0.004 / 0.004 / 0.010 / 0.002. Safety rules on top of the probability: hold (WAN-DOWN) only if P(WAN) ≥ 0.95 **and** hard evidence **and** primary `bad` **and** reserve not `ok`; speeding up primary checks when WAN is `ok`, primary `bad`, reserve `ok`, P(WAN) ≤ 0.01. Sensor: stall — rx unchanged ≥ 3 s, tx grew ≥ 300 bytes; veto — rx grew ≥ 3750 bytes in 3 s (10 kbit/s).

**Where in the program.** Branch `feat/gl-sensors-20261104` (`fc395675`): `wan_diag.py`, `lua/wan_diag.lua`, `stall.py`, `lua/stall.lua`; settings `wan_sensor`, `wg_events`, `stall_sensor`, `stall_veto` are on, `heartbeat_quorum` is off. Status: **in a branch**, not merged into alpha8.

**Experiments.** Shared Lua = Python cases (`gl_sensors_cases.json`), Lua and Python tests; a quorum simulator (section 2.2). `[tests]` `[simulator]` CPU cost: heartbeat as before 0.027 % of a core on a PC, with stall and veto +0.02 %; MT3000 estimate ×5–10 (≈0.14–0.27 % and +0.1–0.2 %), not measured on the router. `[simulator]`

**Results.** There are no numeric before/after results on traces `[no data]`; there are only behaviour tests and the quorum simulation (2.2). An important honest conclusion of the branch: the quorum is kept off because it finds partial loss worse.

**Comparison.** Old: all probes go through the tunnels, there is no "no internet at the router" cause. New: the cause is visible, but "unknown" everywhere means the old behaviour (without evidence there is neither a hold nor a speed-up). A real router check is outside the data.

## 3. Physics

### 3.1 Flap damping: RFC 2439 half-life, doubling pause and Fibonacci

**Problem.** An unstable primary channel (flapping: down, up, down again) makes Auto swing back and forth, and each switch costs seconds of downtime.

**Goal.** Keep traffic on the reserve longer the more often the primary has recently let us down, without losing the ability to return.

**In plain words.** Each failure adds a "penalty", and the penalty itself melts over time like a radioactive substance with a half-life (the physics of decay). While the penalty is above a threshold, returning to the primary is not allowed. This has been done in internet routing since 1998 (RFC 2439). In our product the pause does not decay by a law, it doubles with each extra departure.

**Formulas and details.**

- The product today: return pause `s · 2^min(excess, 6)`, excess = (number of departures in the window) − limit + 1, cap 600 s; the defaults are limit 2 within a 60 min window (configuration options `recovery_flap_limit`, `recovery_flap_window`; the policy reads them as its internal fields `flap_limit`, `flap_window`), below the limit the pause is just `s`.
- Fibonacci: `s · F_excess`, F = 1, 1, 2, 3, 5, 8, 13, 21.
- Half-life penalty: +1000 per departure, decay `P(t) = P₀ · 2^(−t/H)`; with the penalty above suppress the pause is `s + H·log₂(P/reuse)` until the penalty falls below reuse; cap 600 s.
- Cost = downtime + 20·unneeded departures + 15·returns to a dead primary + w·seconds on reserve.

**Where in the program.** `pair_auto.return_hold` / `pair.lua M.return_hold`, configuration options `recovery_flap_model`, `recovery_flap_limit`, `recovery_flap_window` (and for the half-life penalty `recovery_flap_halflife`, `recovery_flap_suppress`, `recovery_flap_reuse`); inside the policy they are the fields `flap_model`, `flap_limit`, … without the prefix. The separate options `recovery_attempt_limit` and `recovery_attempt_window` are the failover budget, not the return pause. Status: doubling with the 60 min memory — **implemented, default, not yet validated**; half-life penalty — **implemented and selectable** (`recovery_flap_model` = `halflife`), not the default; the 60 min memory is the default window; Fibonacci for the return pause — **rejected**. Files: [pair_auto.py](../router/files/usr/lib/homensai-vpn/pair_auto.py), [pair.lua](../router/files/usr/lib/homensai-vpn/lua/pair.lua), [FLAP-DAMPING](architecture/FLAP-DAMPING-2026-11-02.ru.md) (Russian).

**Experiments.** The daily Auto simulator (alpha8 rules), 3 seed sets; the RFC parameters were chosen by searching 132 combinations on training seeds and verified on fresh ones; a set of flapping and control scenarios (60/120 × 10, 30/90 × 20, 60/200 × 10, 45/150 × 12, random flapping, single outages, reserve failure, a healthy hour). `[simulator]` Router: flapping 60/120 s × 10 on alpha5 and alpha6, n=1 cycle per version. `[router]`

**Results (cost, w = 0.01, n=3 sets <59, `[simulator]`).**

| Variant | Cost | vs current |
|---|---|---|
| Doubling, limit 3, 15 min window (product) | 1333 | reference |
| Fibonacci, limit 3 | 1470 | +10 % |
| Doubling, limit 2 (setting `attempt_limit` 3 → 2, no code) | 1112 | −17 % |
| Doubling, limit 2, 60 min window (the default `flap_limit` 2, `flap_window` 60 in `recovery_settings.py`; not proven) | 724 | −46 % |
| RFC 2439, tuned (H=1800 s, suppress 1200–1500, reuse 400–500) | 675 | −49 % |
| RFC 2439 simulator default (H=600, 2500/750) | 1229 | −8 % |

The RFC's gain comes not from the exponential shape but from a **long memory** (≈1 hour instead of 15 minutes) and early activation (from the 2nd departure): doubling with a 60 min memory nearly equals the tuned RFC (724 versus 675) and beats it when the reserve is expensive (w=0.2: 4042 versus 4311).

Router (alpha5 → alpha6, flapping 60/120 × 10): departures 6 → 8, uncovered outages 4 → 0 (n=1 per version <59); the event simulator predicted 6, 8 and 4 → 0. `[router]` The `primary_stable` = 120 s rule (result of section 4.1) in the simulator: departures 5 → 1 (tick, n=1), downtime 223.8 → 27.4 s (n=10). `[simulator]`

**Comparison.** The winner by number is the RFC with a long memory (−49 %), but doubling with limit 2 and a 60 min window (−46 %) is more practical: simpler and smoother when the reserve is expensive. Fibonacci lost: worse in 7 of 8 combinations. Where "new" loses: the longer the damping, the more seconds on the reserve (120.3 → 206.8 s a day at w=0.01); with `primary_stable` 120 the scenarios 60/120×10 and 30/90×20 do not trigger damping at all (the primary has no time to settle), differences show only when the "alive" window is ≥ 150 s. A limit from the literature: aggressive suppression harms availability (Mao et al., SIGCOMM 2002), so the 600 s cap is kept.

### 3.2 The square-root law for the probe budget

> **Validation status (2026-11-07).** Not yet validated: simulator only; it is not enabled (`reserve_probe_interval` = 0).

**Problem.** Each probe costs CPU, traffic and wear; the reserve and the primary are checked equally often (every 10 s), although a reserve failure "costs" the user less.

**Goal.** Distribute a fixed number of probes among objects so that total losses from undetected failures are minimal.

**In plain words.** The more often an object breaks and the more expensive a second of its downtime, the more often it should be checked, but not proportionally, by the square root. The reserve is fine with less frequent checks.

**Formulas and details.** Loss ≈ `λ·c·(k−½)·T` for an object with failure rate λ, cost per second c, probe period T, failure declared after k misses. With a limited total number of probes Σ1/T_i = R the Lagrange multiplier gives `r_i ∝ √(λ_i·c_i)`.

**Where.** A recommendation for `probe_policy.lua` and the monitor, not implemented. Status: **research only**.

**Experiments.** Monte Carlo of 18,000 h, Poisson failures: equal intervals 5.19 versus formula 5.12 s/h; square-root law 3.08 versus 3.03. `[simulator]`

**Results (primary stays at 10 s, reserve less often; `[simulator]`).**

| Reserve interval | Probes per hour | Probe saving | Loss, s/h | vs current |
|---|---|---|---|---|
| 10 s (now) | 720 | 0 % | 5.12 | 0 % |
| 40 s | 450 | 38 % | 5.15 | +0.55 % |
| 120 s | 390 | 46 % | 5.16 | +0.76 % |

Scenario A without limits: loss −40.7 % at the same number of probes; scenario B (with two spare servers): −65.4 % loss or 71 % fewer probes at the same loss. With the owner's hard limits 10…120 s an equal plan is already at the ceiling: the gain is only in saved probes.

**Comparison.** The winner is the square-root law, **but the result depends entirely on the assumption cR** (the cost of an undetected reserve failure); the optimal reserve interval ranges from 500 to 10 s as cR goes from 0.002 to 1 — this needs measuring. Auto requires fresh reserve probes to decide a switch, so a slow reserve must be combined with an extra probe on suspicion about the primary. Router: `[no data]`.

### 3.3 Erasing the "memory" of connections (conntrack) after a switch

> **Validation status (2026-11-07).** Not yet validated: the 54.8 → 23.6 s figure is an estimate (the router-side delay A ≈ 3 s was not measured), not a measurement on the router.

**Problem.** On the router after traffic moves, an old TCP connection of a LAN client hangs ≈20 s and dies only by the application timeout (a new connection comes ≈40 s after the switch). Reason: the connection table still holds a NAT entry with the old tunnel address, and the new server silently drops such packets. `[router]`, 3 LAN-client runs.

**Goal.** Applications learn about the break at once and reconnect.

**In plain words.** A connection has a "memory" of its path, and it is out of date. We erase only entries that went through the old tunnel; the next packet creates an entry along the new road, the server answers RST, the application reconnects within seconds.

**Formulas and details.** After a confirmed move A → B: `conntrack -D -f ipv4 --reply-dst <tunnel A address> --src-nat` (timeout 1 s). Router management, its own flows, incoming connections and flows of the new tunnel are not touched. An error does not roll back the switch.

**Where.** `transaction.attempt` / `native_switch.attempt`, helper `reset_old_flows`; `option flow_reset '0'` turns it off. Status: **implemented** (merged into alpha8). Description: [FLOW-RESET](architecture/FLOW-RESET-2026-11-03.ru.md) (Russian).

**Experiments and results.** Availability model: with a 15 s outage, application downtime per event 54.8 → 23.6 s (estimate, range 15–25 s); the assumption "A≈3 s after the reset" is not measured on the router. `[simulator]` Router: `[no data]` on the reset result. Comparison: without the reset an application waits for a timeout (≈20 s); with it — an estimated 3 s. Shared Lua = Python case tests. `[tests]`

### 3.4 The MTU black hole

**Problem.** Ordinary health checks send only small requests, while large packets are lost at a narrow spot. The primary channel looked healthy, there was no switch, large transfers hung. Found on the router (nft `meta length > 1300 drop` on a tunnel with MTU 1350). `[router]`

**Goal.** Detect such a "hole" and treat the channel as unhealthy.

**In plain words.** Like cargo that does not fit through a narrow door: small letters pass, parcels do not. Every 5 minutes we send a "parcel" the size of the tunnel's MTU through the tunnel and see whether it comes back.

**Formulas and details.** A 64-byte echo and two large echoes of the tunnel MTU length (up to 1500, below 576 is not checked), wait 1.5 s. Verdict `black-hole` if there is no large reply while the small one is alive; an arriving "fragmentation needed" (PMTUD works) is not a hole. Load: 6 ICMP packets per channel every 5 minutes. MSS clamping does not cure a hole below the tunnel MTU, and the GL firmware already installs `TCPMSS --clamp-mss-to-pmtu`.

**Where.** `mtu_check.py` / `lua/mtu_check.lua`, code VPN-MTU, diagnosis LARGE-PACKETS-FAILED. Status: **implemented** (alpha8, fix `fix/mtu-check-runtime`). Files: [mtu_check.py](../router/files/usr/lib/homensai-vpn/mtu_check.py), [mtu_check.lua](../router/files/usr/lib/homensai-vpn/lua/mtu_check.lua), [MTU-SQM](architecture/MTU-SQM-2026-11-03.ru.md) (Russian).

**Results.** **A failure preserved as evidence:** in alpha7 the check did not work on the router — 0 switches in 5 cycles (3 + 2 long ones of 450 s; Wilson 0…43.5 %), the VPN-MTU code is absent from the logs. The reason is a runtime error (a send refusal EPERM was not counted as loss); the fix is merged into alpha8, a router re-check is ahead. `[router]`, n=5 <59. The shared case tests `mtu_check_cases.json` pass. `[tests]`

**Comparison.** The old way (small requests only) does not see the hole; the new one should, but the router has so far shown the opposite. There is no winner until there is a successful run.

### 3.5 SQM and Little's law

**Problem.** When a channel saturates, buffer queues grow ("bufferbloat"), latency grows and all checks begin to fail.

**Goal.** Keep latency low with a shaper (SQM, the cake algorithm) at the tunnel output; in future choose the rate automatically.

**In plain words.** Little's law: the average number waiting = arrival rate × average waiting time (L = λW). If the rate is constant and the queue grows, the waiting time grows too. A shaper deliberately limits the rate slightly below the capacity so that the queue does not build up in a large provider buffer.

**Where.** `sqm.py` / `lua/sqm.lua`, `sqm_enabled` and `sqm_upload_kbit` — **off by default**, no button on the page. Status: SQM — **implemented** (alpha8), automatic rate by Little's law — **not implemented**; the owner sets the rate by hand. Files: [sqm.py](../router/files/usr/lib/homensai-vpn/sqm.py), [sqm.lua](../router/files/usr/lib/homensai-vpn/lua/sqm.lua).

**Experiments and results.** Tests with a fake `tc` (`sqm_cases.json`). `[tests]` There are no cake measurements on the router; the effect on latency and CPU is `[no data]`. Caveat: cake is a software shaper, a noticeable share of a core at hundreds of Mbit/s.

## 4. Biology and evolution

### 4.1 Genetic algorithm versus simulated annealing for settings

> **Validation status (2026-11-07).** The tuned values `primary_stable` = 120 s and `rescue_stable` = 10 s are not yet validated: the validation jobs are pending, and the "22 of 23" match with the router was computed on the data the model was fitted to. They are the defaults (the long window is conservative) and are labelled experimental: chosen in simulation, not validated on hardware.

**Problem.** Auto has many settings and their interaction is not obvious (for example, a long `primary_stable` helps with flapping but worsens the worst case when the reserve fails).

**Goal.** Find defaults that lower the total cost of a day, and compare two search methods.

**In plain words.** A genetic algorithm copies natural selection: a "population" of settings sets, the best are crossed and mutated, the worst die out. Simulated annealing comes from metallurgy: at first even bad steps are allowed ("hot" metal), then ever more strictly ("cooling"). Both run settings through a model of the router's day and look for the minimum "cost".

**Formulas and details.** Fitness `F = downtime (s/day) + 60·false + 20·unneeded + 30·(checks per hour/720) + 0.01·(s on reserve) + 100·(s of blocked leave)` over a mix of daily scenarios (outages 5–120 s, losses 5–80 %, Gilbert–Elliott bursts, flapping, DNS block, reserve failure under load, healthy days). The check interval is fixed at 10 s (owner's CPU decision).

**Where.** The optimiser and model code is `private/math/evolution`; the found settings went into the product: `recovery_rescue_stable` = 10 s (0 — the old rule), `primary_stable` 30 → 120 s, `fast_detect.LOSSES` 3 → 2. Status: **implemented** (alpha8). [RESCUE-STABLE](architecture/RESCUE-STABLE-2026-11-03.ru.md) (Russian).

**Experiments.** The model was checked against the router: **22 of 23 points matched** (outages 5…150 s, losses 5…80 %, DNS/HTTPS block, flapping 60/120 × 10 — alpha5: 6 departures and 4 uncovered; alpha6: 8 and 0 — exactly as on the router; LAN downtime on departure 23.0 versus 22.3 s; return with a failed reserve 194.8 versus 191.5 s). The point "10 % loss" did not match (router 1 of 2 cycles, model 1 %) — it is left as failed. `[simulator]` Optimiser comparison and totals on 10 fresh seed sets. `[simulator]`

**Results.**

- GA: 151.3 on training seeds after ≈350 evaluations; annealing: 151.8 after ≈470, one of four chains got stuck (155.2). On fresh seeds 149.41 ± 1.31 versus 149.82 ± 1.43 — the same region of solutions. `[simulator]`
- Repeated optimisations chose `rescue_stable` = 10 s and `LOSSES` = 2 in 8 of 8 runs. The GA exposed a discrepancy in the code: the alpha6 notes promised "returns at once", while with a failed reserve the code waited a full `primary_stable`.

| Per day (10 sets, n=10 <59) | alpha7 | implemented (120/10/LOSSES 2) | research variant (+DENSE 6, not shipped) |
|---|---|---|---|
| fitness (lower is better) | 155.9 ± 1.3 | 151.5 ± 1.0 (better in 10 of 10) | 149.3 ± 1.2 |
| user downtime, s | 121.1 | 115.4 | 116.9 |
| unneeded switches | 0.168 | 0.190 | 0.019 (−89 %) |
| flapping 60/120 × 10: departures / downtime, s | 7.97 / 224 | 1 / 27 | 1 / 30 |
| reserve failure ≥ 450 s: downtime, s | 182.8 | 163.9 | 165.6 |
| seconds on reserve | 120 | 207 | 182 |

All rows `[simulator]`.

**Comparison.** The winner is the pair 120 + `rescue_stable`: flapping almost disappears, a long reserve failure costs no more. Where it loses: slightly more unneeded switches (0.168 → 0.190), longer on the reserve (120 → 207 s). `primary_stable` 120 alone without `rescue_stable` worsens the worst case (183 → 276 s), so they change only together. The GA's second recommendation (`DENSE_INTERVAL` 4 → 6 s, unneeded −86…−89 %) is **not shipped**: every real outage loses another 1.5–2 s. Limits: scenario weights and frequencies are assumptions (the sign of the gain is stable across all 13 recomputation variants).

Router: `[no data]` (waits for alpha8 acceptance, phase 2 and 24 h).

### 4.2 Immune memory by time of day

**Idea.** An organism "remembers" infections it has met and reacts faster to a repeat. For the program: remember at which hours of day a channel or server is usually bad, and be more cautious about them in advance. The network journal (section 2.7) already stores RTT by hour of day for future use.

**Status: not implemented.** There are no code and no calculations, `[no data]`.

### 4.3 Entropy and homeostasis

**Idea.** Homeostasis is keeping a parameter near a set value by feedback (body temperature). Entropy measures uncertainty: the more uncertain the channel state, the more often it should be checked. Related mechanisms that already work: dense probes on the model's "suspicion" (2.1) and the UCB uncertainty bonus (2.4); but there are no separate "entropy probes" and no probe-rate regulator (Kalman, PID).

**Status: not implemented.** `[no data]`.

## 5. Fibonacci and the golden ratio

The Fibonacci numbers 1, 1, 2, 3, 5, 8, 13… grow about φ = (1+√5)/2 ≈ 1.618 times per step (the "golden ratio"). It is the most "even" irrational proportion: the points `i·φ mod 1` overlap each other as rarely as possible. Of the four uses in the project, one is a clear winner, one is in a branch, one is equivalent to a simple scheme and one lost.

### 5.1 Fibonacci retry pauses with a cap and jitter (the simulation's pick, not proven)

**Problem.** With repeated attempts (tunnel bring-up, server pick) a fixed 5 s pause without spread makes 30 clients rush at once after a server restart (the "herd"), and a pause ladder too long without a cap is wasted.

**Goal.** Cheaper in terms of "time + number of attempts".

**In plain words.** After each failure we wait longer (2, 2, 4, 6, 10, 15 s and then 15), but each time a random time from 0 up to that limit so that clients do not coincide.

**Formulas and details.** The pause after the n-th failure `b_n = min(15, 2·F_n)` = 2, 2, 4, 6, 10, 15, 15…; the pause itself = `U(0, b_n)` ("full jitter"). Cost `J = time + w·number of attempts` (w = 0.5/2/5 s per attempt).

**Where.** Recommendation: a function `retry_pause(n)` in `native_switch.py` / `server_pick.py`; leave attempt limits and cooldown alone. Status: **implemented, default, not proven** (`retry_policy.py`, Fibonacci 2, 2, 4, 6, 10, 15 s with full jitter; option `retry_backoff` = `fixed` keeps the former 5 s). Experimental: chosen in simulation, not validated on hardware; the checking analysis is blocked (corrected) or pending (original).

**Experiments.** 30,000 runs per cell, common random numbers; failure models: independent success q = 0.2/0.5/0.8, "server unavailable for Y s" (exponential 20 and 120 s, lognormal, fixed 45 s), a "herd" of 30 clients. `[simulator]` The assumption "now — a fixed 5 s without jitter" comes from reading the code; which loops exactly are retries was not verified.

**Results (`[simulator]`).** The herd of 30 clients: 68 s (now) → 37 s (Fibonacci 2→15 + jitter); a fixed 5 s + jitter gives 36 s, which is within noise of 37 s: the default is not proven better than a fixed 5 s + jitter. Mean cost relative to the best policy: Fibonacci 2→15 + jitter ×1.060 (maximum ×1.16 at w=2); cheaper than a fixed 5 s (without jitter) by 17/13/9 % (w = 0.5/2/5); 2.3/2.0/1.6 times cheaper than doubling 2→60 s. Three effects in descending order: jitter, cap, shape (Fibonacci ≥ doubling with the same cap — a difference of a few percent).

**Comparison.** Fibonacci 2→15 + full jitter was the simulation's pick, but it is statistically indistinguishable from doubling with the same cap and from a fixed 5 s with jitter; the benefit comes from jitter and the cap, not from the Fibonacci shape. For one router the herd effect is small; it matters on a mass server restart. Router: `[no data]`.

### 5.2 Probe phase spreading (golden ratio and even i·T/K)

**Problem.** If the primary and reserve check passes start at the same time, up to 11 `curl` processes run at once, the CPU "jumps" and the checks interfere with each other.

**Goal.** Spread probe starts across the period.

**In plain words.** Like placing points on a circle so that they interfere as little as possible. For a known number of tasks K it is best to place them evenly (`i·T/K`, for two passes — a half-period shift). If tasks are added without retuning the old ones, the golden angle is better: each new point lands in the biggest gap.

**Formulas and details.** The phase of the i-th task: `φ_i = (i·φ⁻¹ mod 1)·T`, φ⁻¹ = 0.618…; even — `i·T/K`. The share of starts when another probe is already running (lower is better); the Fano number = variance/mean of starts per 1 s.

**Where.** Recommendation: shift the start of the reserve pass by `interval/2` in `probe_policy.lua`/the monitor and schedule by absolute time (start + n·T). Status: **implemented, default, not proven** (`probe_plan.py`, option `probe_spread`, an absolute grid with phases; uniform spacing `i·T/K` with a step capped at 3 s is what runs, not the golden ratio). Independent check (registered phases analysis, original): CRITERIA_FAIL; the golden-ratio layout is worse than uniform spacing in some cells (K = 2, no drift, duration 3: 1.44 versus 1.00, about 44 % worse). Experimental: not validated on hardware; the process peak on the MT3000 is not measured.

**Experiments.** A "processes in a window" model: primary and reserve passes (10 s, 0.6 s, 4 curl processes), two 1 s heartbeats, the 2 s Auto tick; K = 2, 4, 8 tasks, timer drift 0 and 50 ms. `[simulator]`

**Results (`[simulator]`).**

| Phase layout | Overlap of the two passes | Peak processes | p99 processes |
|---|---|---|---|
| all together | 0.50 | 11.0 | 9.0 |
| random phases (mean of 30 draws) | 0.07 | 5.7 | 5.1 |
| only reserve shifted by T/2 | 0.00 | 7.0 | 5.0 |
| golden ratio | 0.00 | 5.0 | 4.0 |

**Comparison.** The winner is even `i·T/K` for a known K (K=2: a 5 s shift); the golden ratio — when the number of tasks grows; coprime periods are no better than random (0.07–0.34) and change the probe rate, so they were rejected. With a timer drift of 50 ms/cycle the gain of phases blurs over tens of minutes (K=8: 0.2 versus 0), so scheduling must follow an absolute grid. Router: `[no data]`.

### 5.3 Golden-section search in the slider advisor

Described in 2.7. In short: golden-section search (the limiting case of Fibonacci search) found the slider position of minimum cost in ≈9 evaluations instead of a grid search with step 0.01 (≈100); it matched the grid in 140 of 150 cases and was no more than 0.1 % costlier in the rest. `[tests]` Status: **implemented in `advisor.py` since alpha9** (golden-section search over the slider); it is a unit-tested search, not a proven benefit on the router.

### 5.4 Fibonacci in flap damping (rejected)

Described in 3.1: Fibonacci (cost 1470) is worse than the current doubling (1333) by 10 %, worse in 7 of 8 combinations, rejected. `[simulator]`

## 6. Cryptography

### 6.1 Probe authenticity: pinned TLS roots and a one-time nonce

**Problem.** The channel check trusted the whole system certificate store (≈140 roots). Any wrongly issuing CA (in 2025 one issued certificates for 1.1.1.1) made a forgery "genuine". The `/cdn-cgi/trace` page is not tied to the request, a caching intermediary could return an old one. A portal certificate, a redirect to a portal and an ordinary break looked the same.

**Goal.** Make the alive or dead look of a tunnel impossible to forge on the path.

**In plain words.** For each of the three probed sites we trust not "any CA in the world" but only the 4–13 root certificates that the site actually uses. Into each request we put a one-time random number (128 bits); a genuine answer must return it, otherwise it is an old page.

**Formulas and details.** Pinning at the anchor level: SHA-256 of the root's SubjectPublicKeyInfo in `pins.json`, TLS checked only against `probe-anchors/<host>.pem`. Freshness: `User-Agent: HomenSAI-probe/<32 hex>` must come back as `uag=`; without it `ts` within ±60 s; a clock jump > 2 s — the check is not counted. If the anchor file is missing, the system store is used (the alpha7 check, not no check). Distrust reasons: `untrusted-certificate`, `portal-redirect`, `nonce-mismatch`, `stale-response`, `clock-jump`. The 2-of-3 quorum is kept.

**Where.** `probe_trust.py` / `lua/probe_trust.lua`; option `probe_dns = doh` (off by default). Status: **implemented** (alpha8). Files: [probe_trust.py](../router/files/usr/lib/homensai-vpn/probe_trust.py), [probe_trust.lua](../router/files/usr/lib/homensai-vpn/lua/probe_trust.lua), [PROBE-AUTHENTICITY](architecture/PROBE-AUTHENTICITY-2026-11-03.ru.md) (Russian).

**Experiments.** A handshake with the real servers from a PC (`openssl s_client -CAfile`): each host passes with its own root file; one.one.one.one fails with the Google and Quad9 files, dns.google and dns.quad9.net with foreign ones (`unable to get local issuer certificate`); the SPKIs in `pins.json` matched `openssl x509 -pubkey | openssl dgst -sha256`. Shared cases `probe_trust_cases.json`, tests with real TLS, a rotation-expiry test. `[tests]`

**Results.** Trusted roots 4–13 per host instead of ≈140 `[calculation]`; the Cloudflare set is deliberately wider (1.1.1.1 changed its CA from DigiCert to SSL.com). A real router check: `[no data]`.

**Comparison.** The new approach strictly limits trust and adds freshness; the price is a package update when a site changes its CA. Not covered by cryptography: DNS over UDP (the DoH option moves the check into HTTPS); for the dns.google JSON API freshness rests only on the pinned roots. A known idea from active-measurement standards (RFC 4656 OWAMP, RFC 5357 TWAMP: authenticated/encrypted modes), not found for home failover scripts.

### 6.2 usign release signing, a hash chain and OpenTimestamps

**Problem.** A substituted or damaged `.ipk` package on GitHub, Gitea or a flash drive; a "silent rollback" to an old package; the need to prove a release existed on a date.

**Goal.** The router installs only packages signed by the owner's key and only those that continue the verified history.

**In plain words.** Each release is signed with a secret key (Ed25519, the usign format from OpenWrt). Each history record includes the hash of the previous one, so history cannot be rewritten unnoticed. The record's hash is "nailed" to the Bitcoin blockchain by the OpenTimestamps service, which proves the date. Signing is possible only with a code from the phone.

**Formulas and details.** Ed25519 signature (RFC 8032 vectors); `CHAIN.jsonl`: each record stores the hash of the previous one; two keys (main and reserve), revocation `<key>:<record number>`; TOTP ±1 step (30 s), a repeated code is rejected, 5 wrong in a row — a 10 minute lockout. Keys live in `/etc/homensai-vpn/keys`, not in `/etc/opkg/keys` (so as not to gain the right to sign other feeds). The pure-Python Ed25519 is not constant-time and runs only on the owner's PC.

**Where.** Branch `feat/usign-signing-20261103` (`339e17c1`): `scripts/signing/`, `releases/CHAIN.jsonl`, `homensai-vpn-trust-key`. Status: **in a branch**, not merged into alpha8.

**Experiments.** Compatibility with real usign from the OpenWrt 21.02.7 SDK in both directions: signatures match byte for byte, all 153 entries of the real chain verified; all 26 install-path tests passed with real usign, with a Python stand-in and under BusyBox ash/sed (alpine 3.20); mutations: 18 of 18 killed. `[tests]` OpenTimestamps: the chain head stamp was sent, all 4 calendars answered, status "pending confirmation". `[tests]`

**Results.** Router: the install path was not verified `[no data]`; the first check will come when the first signed release is installed with the owner present. Not covered: the first installation (the kit's keys could be foreign, fingerprints must be compared), TOTP is a procedural protection (the seed is under the same Windows DPAPI), and without an external transparency log with independent monitors protection against "different views for different people" is weaker.

**Comparison.** Before: a SHA-256 beside a file that is replaced together with the package. Now: a signature that cannot be made without the secret key. All elements are known (TUF, Sigstore, Go checksum database, OpenTimestamps); the rare part is all of them together in a small home project.

### 6.3 Encrypted age backups and pinning of server keys (TOFU)

**Problem.** The project's secrets on the PC are protected only by Windows DPAPI: if the PC burns, the router access keys and all encrypted exports are lost. A separate threat: the router trusts what is in the GL config; a substituted VPN server looks healthy.

**Goal.** (1) Secrets survive the loss of the PC; (2) a substitution of a VPN server under the same name is visible.

**In plain words.** age is a simple file-encryption format: the secrets archive is encrypted to the owner's public key and lies safely on a flash drive; any PC with the private key from a password manager can decrypt it. TOFU ("trust on first use", as in SSH): at the first successful check of a server we remember its key; if the same server (by name) suddenly shows a different key — alarm.

**Formulas and details.** age v1: X25519, ChaCha20-Poly1305 in 64 KiB blocks, the header protected by HMAC. TOFU: identity = profile + host name (never the IP); WireGuard — the peer public key from `wg show endpoints`; OpenVPN — SHA-256 of the DER CA certificates; states `pinned → changed → accepted/forgotten`; "changed" is sticky. Mode `server_key_pin`: `warn` (default) | `enforce` | `off`; with `enforce` Auto does not use a channel with a changed key. The NordVPN pool does not break: another host name is just a new first use.

**Where.** Branch `feat/age-tofu-20261104` (`724d9fb0`): `scripts/backupcrypt/`, `server_pin.py`, `lua/server_pin.lua`. Status: **in a branch** (in progress), not merged into alpha8.

**Experiments.** Official C2SP/CCTV test vectors: 147, of which 129 verified (all matched), 18 — post-quantum identity, out of scope; the real `age` utility 1.1.1: 32 of 32 mutual checks; 18 tool tests; a mutation check of 76 mutants, 76 killed (the first run, 65 of 74, found 9 holes in the tests — closed). A 21 MB archive (811 files, 208 DPAPI keys) encrypts in ≈6–8 s in pure Python. `[tests]`

**Results.** Not verified on the router `[no data]` (needed: `wg show endpoints` for a NordVPN profile, the real `--config`/`--cd` path of GL 4.11 OpenVPN). It does not protect against compromise of the PC itself and against a keylogger.

**Comparison.** Before: losing the PC = losing all secrets; a substituted server is invisible. Now: restore on any PC and a warning (by default it does not block). Weak spot: the owner's steps (creating the identity, TOTP) have not been done yet.

## 7. The first P95 from n ≥ 59 on the router (alpha7, n = 61) and the 84 s bug it found

**What was measured.** A 59-cycle `primary-drop` run on the dedicated MT3000 (the primary channel is cut for 150 s), version 2.1.0-alpha7, 03.11.2026 20:49 UTC — 04.11.2026 02:14 UTC. The log holds 63 cycles: 61 counted, 2 skipped (`NOT-ON-PRIMARY`, traffic was not on the primary channel), 0 bench errors. Data: `private/soak-24h/report-a7-honest63`. All numbers `[router]`.

| Indicator | n | Median | P95 (point estimate) | Upper 95 % bound of P95 = maximum |
|---|---|---|---|---|
| Traffic moved to the reserve, s | 61 | 21.4 | 29.8 | 84.2 |
| Detection, s | 61 | 7.0 | 7.47 | 9.64 |
| Return to the primary, s | 55 (<59) | 234.1 | ≈244.6 (estimate) | 247.6 |

Here n = 61 ≥ 59: the 58th smallest of 61 values (ascending order) gives the empirical P95 = 29.8 s, which is an estimate (it covers the true P95 in only about 36 % of cases), and the maximum 84.2 s is the 95 % upper bound of the true P95 (95 % confidence, for independent samples; cycles of one bench are correlated, so the real coverage of this bound is lower). For the return n = 55 < 59: the numbers are shown as estimates.

The rest: all 61 cycles ended with a switch (61 of 61; Wilson 94…100 %); 55 of 61 cycles ended with a return to the primary (Wilson 80.1…95.5 %), 6 did not (cycles 28, 29, 48, 49, 50, 55; the report does not analyse the reason); short `BLOCKED vendor` episodes in 16 of 61 cycles (Wilson 16.8…38.5 %, median 2.7 s, maximum 6.8 s); rate limiting in 53 cycles.

**The bug this sample found.** Cycle 28: traffic moved to the reserve in **84.2 s** instead of 20–35 s, while detection was normal (7.06 s). Cause: the dispatched switch (APPLYING, budget charged) was aborted by the vendor firmware (`VENDOR-WORKER-QUIET-UNVERIFIED`), the transaction rolled back before any switch, but the charged budget stayed, and the next attempt waited `max(cooldown, min_dwell)` = 60 s (`PAIR-RATE-LIMIT`, the primary still failed). One outlier out of 61 pushed the maximum almost three times above P95. The fix `a3591140`: a switch refused by a transient vendor state and verifiably rolled back is not counted as a switch, the budget is refunded, and the retry waits 5, 10, 20, 40 s, then `max(cooldown, min_dwell)` after each consecutive refusal (never a "hot" retry); a completed switch ends the series; all vendor gates are unchanged. The fix was checked with Python/Lua twins on shared cases (including a simulation of cycle 28) `[tests]`, there is no repeated router run yet `[no data]`.

**Comparison with before.** The previous publication: 2.0.0-beta4, n = 15, median 36.1 s, "P95 = 39.3" (in fact the maximum of 15 samples: neither a P95 from n ≥ 59 nor any upper bound). Now n=61: P95 = 29.8 s. The versions differ (beta4 and alpha7), so they are not pooled into one sample and an "improvement" cannot be derived from these two numbers.

## 8. Cross-comparison of all principles

The effect size is given for the main metric; the label and sample are in brackets. "Router" — whether there is a measurement of this very principle on the router. Status as in section 1.2.

| Principle | Science | Main effect | Simulator / tests | Router | CPU / load | Status |
|---|---|---|---|---|---|---|
| HMM detector | M | old figure: unneeded switches on a 15 s blackout 100 % → 0.7 % (`[simulator]`, n=300; not reproduced by the registered re-check, which is CRITERIA_FAIL: costlier per day than the simple rule, about 3 s later on a long outage, better on flapping and heavy loss) | yes / yes | no data | ≈0.1–0.2 ms per probe (estimate), 0.004 % of a core | implemented, default, experimental |
| Return condition P(healthy) ≥ 0.90 | M | return after a 40 s blackout at `primary_stable` 30 s: 67.2 → 57.3 s (`[simulator]`, n=100; not validated, the registered pair used the same return gate in both arms) | yes / yes | no data | no data | implemented, default, not proven |
| Binomial guarantees, 2-of-3 quorum | M | false alarms 10.26 → 0.033 a day (`[calculation]`, p=5 %) — against single-probe noise only; real short outages ≈0.04 per hour per channel, n_eff ≈1.2–1.9 (`[router, small n]`); catches 30 % partial loss worse | yes (19 cases) / yes | partly: `[router, small n]` | echo ×3 | formulas: research; quorum: in a branch, off |
| Honest statistics (Wilson, 59) | M | 0 of 509 earlier P95 had n ≥ 59 (`[calculation]`); the empirical P95 stays an estimate, the upper bound is separate | yes / yes | first P95 from n ≥ 59 (section 7) | no effect | bench: applied; product: in a branch |
| Bayesian server pick + UCB | M | useless switches 41.94 → 0.59 a day (`[simulator]`, n=40, older simulation; not yet validated, the new check is pending); finds the best later: 46 versus 4 min | yes / yes | no data | measurements −41…−51 %, flash −66 % | implemented, off |
| Exhaustive state search (K1–K11) | M | 4.7 million states; K1 (eternal HELD) found and confirmed on the router | no / yes | partly (K1) | offline ≈17 min, ≈3 GB | tool: implemented; K2–K5, K9, K11: in a branch |
| Markov availability | M | downtime 287 → 29 min/month (`[simulator]`) | yes / yes | no data (parameters from measurements) | not in the router | research only |
| Pareto front + slider | M | losses 234 → 244 s/day, unneeded 25× fewer (`[simulator]`, n=10; the independent check did not confirm a monotone trade-off: 15 of 18 branches FAIL) | yes / yes | no data | no data | advisor implemented (`advice` mode), curve not proven |
| Ski rental | M | HMM better by 2.2 % / 2.4 % (`[simulator]`) | yes / no | no data | — | research (do not ship) |
| Survival analysis | M | tie ±0.2 % with the HMM; natural events n=11 | yes / no | n=11 | — | research (do not ship) |
| WAN/tunnel diagnosis + stall sensor | M/P | quorum: 210 → 6.3 false suspicions a day at p=5 % (`[simulator]`) | yes / yes | no data | +0.02…0.2 % of a core (estimate) | in a branch |
| RFC 2439 penalty decay / 60 min memory | P | flap cost 1333 → 675 / 724 (`[simulator]`, n=3; not yet validated) | yes / yes | no data | — | 60 min memory (`flap_limit` 2): implemented, default, not proven; half-life penalty: selectable |
| Square-root law for probes | P | probes −38…−46 % for +0.6…0.76 % loss (`[simulator]`) | yes / no | no data | −38…−46 % probes | research only |
| conntrack flow reset | P | application downtime 54.8 → 23.6 s (an estimate, not measured on the router, not yet validated; `[simulator]`) | yes / yes | no data | 1 `conntrack` call | implemented |
| MTU black hole | P | the router check failed: 0 of 5 (`[router]`) | no / yes | failure | 6 ICMP every 5 min per channel | implemented (fixed in alpha8) |
| SQM / Little's law | P | no data | no / yes | no data | noticeable at hundreds of Mbit/s | SQM implemented (off); auto rate not implemented |
| Genetic algorithm vs annealing | B | fitness 155.9 → 151.5; flapping 224 → 27 s (`[simulator]`, n=10; the tuned values are not yet validated, the validation jobs are pending) | yes (22 of 23 with the router) / yes | no data | — | implemented |
| Immune memory | B | no data | no | no | — | not implemented |
| Entropy / homeostasis | B | no data | no | no | — | not implemented |
| Fibonacci retry pauses | Fib. | cost −9…−17 % against a fixed 5 s without jitter, herd 68 → 37 s (`[simulator]`); a fixed 5 s + jitter gives 36 s, within noise; the checking analysis is blocked/pending | yes / no | no data | — | implemented, default, not proven |
| Phase spreading (golden ratio / T/2) | Fib. | peak processes 11 → 5 (`[simulator]`); the independent check failed (CRITERIA_FAIL), the golden ratio is worse than uniform in some cells | yes / no | no data | −55 % peak (not measured on the MT3000) | implemented (uniform spacing, cap 3 s), default, not proven |
| Golden section in the advisor | Fib. | ≈9 evaluations instead of ≈100; equal to the grid in 140 of 150 (`[tests]`) | yes / yes | no data | at night, nice 19 | implemented (`advisor.py`) |
| Fibonacci in flap damping | Fib. | cost +10 % over current — a loss (`[simulator]`) | yes / no | — | — | rejected |
| Probe authenticity (SPKI, nonce) | C | 4–13 roots instead of ≈140 (`[calculation]`) | no / yes | no data | no data | implemented |
| usign signing + chain + OTS | C | 153 of 153 chain entries verified by real usign (`[tests]`) | no / yes | no data | not in the router (PC) | in a branch |
| age + TOFU | C | 76 of 76 mutants killed; 32 of 32 checks with real `age` (`[tests]`) | no / yes | no data | 21 MB archive ≈6–8 s on a PC | in a branch |
| First P95 from n ≥ 59 on the router | M | median 21.4 s, empirical P95 29.8 s (an estimate), maximum 84.2 s (upper bound; `[router]`, n=61, alpha7) | — | yes | — | measured; the 84 s bug found |

Sciences: M — mathematics, P — physics, B — biology, Fib. — Fibonacci and the golden ratio, C — cryptography.

## 9. Leaders by science

| Science | Leader (by effect size and quality of evidence) | Losers or ties | Main caveat |
|---|---|---|---|
| Mathematics | the HMM detector only on flapping, 20–21 s blackouts and heavy loss (the old 100 % → 0.7 % figure was not reproduced; overall it costs more per day than the simple rule); the Markov model (287 → 29 min/month, not yet validated); honest statistics (the only one with a real n ≥ 59 on the router) | ski rental (worse by 2.2 %), survival analysis (tie), CUSUM, SPRT at 40 % loss; the quorum at 30 % loss | the HMM leaves about 3–5 s later on a real outage; the HMM itself has not been validated on the router |
| Physics | a 60 min flap memory (−46…−49 % cost); the square-root law (−46 % probes at +0.76 % loss); flow reset (54.8 → 23.6 s, estimate) | Fibonacci in flapping (+10 %); the MTU check on the router (failure) | everything except MTU is unverified on the router; the square-root law depends on the assumption cR |
| Biology and evolution | the genetic algorithm versus annealing (GA faster: ≈350 versus ≈470 evaluations; `rescue_stable` found; model = router on 22 of 23, on the data it was fitted to); Fibonacci pauses (−9…−17 % against a fixed 5 s without jitter; not proven better than fixed + jitter); phase spreading (11 → 5; the golden ratio failed against uniform) | annealing (one of four chains got stuck); immune memory and homeostasis not yet tried | the price of GA settings: unneeded 0.168 → 0.190, longer on the reserve |
| Fibonacci and the golden ratio | retry pauses (the simulation's pick, not proven better than a fixed 5 s + jitter); golden-section search (≈9 evaluations) | Fibonacci flap damping (+10 %) | even `i·T/K` for a known K is no worse than the golden ratio |
| Cryptography | usign signing (153 of 153, byte for byte); age (32 of 32 with real `age`); pinned TLS roots (4–13 instead of ≈140) | — | none of the three is verified on the router; usign and age are not merged yet |

Overall conclusion on evidence quality: on the router one quantity has been measured with n ≥ 59 (section 7). The rest is simulator, tests and calculation. Any "×N better" number in this table must be read as "in the model" until router acceptance.

## 10. What is still unverified and how to deepen it

Sources: the prior-art search `private/research/PRIOR-ART-2026-11-04.ru.html`, the study reports, the final report.

1. **One bench.** Everything is calibrated on one MT3000, one home network, one pair of providers. Run the bench in at least 3 independent networks (wired and mobile), publish the loss traces as a dataset. MT6000, IPv6 at the provider, an external LAN client, a 24-hour soak and a power cut on alpha8 are separate items.
2. **Little data on the router.** For each fault type and version 59–93 cycles are needed (≈3.5–5.6 h); for thresholds — the switch share with a Wilson interval over 20–59 cycles. The alpha8 run (HMM, return condition 0.90, `rescue_stable`, flow reset) on the router has not been obtained yet.
3. **Calibration and checking on the same logs.** "22 of 23" was obtained on the same data the model was fitted to. Split the data: fit on some sessions, test on others and on other hardware. The "10 % loss" point did not match and is left as is.
4. **Baselines from the literature.** The detector was compared only with "3 in a row" and the late-switch recheck (and SPRT, CUSUM). Add φ-accrual (Hayashibara et al., 2004), the Chen–Toueg–Aguilera adaptive detector, Jacobson's RTO estimate; report Chen's metrics (detection time, time between false alarms, mistake duration) with confidence intervals.
5. **A home-made state checker.** Port a small profile to TLA+/TLC or Promela/SPIN and compare the state counts and counterexamples; a mutation check of the checker itself; trace validation of the real code against router logs. The model lacks the K11 fix and must be extended; K3, K4, K9 must be checked on the router.
6. **Sensor independence in the quorum.** Measure sensor correlation on own traces and give a false-alarm bound corrected for correlation (effective n). The per-target log `probe_target_log` (the result and latency of each target in every probe, the heartbeat misses per target) was added for exactly this; no router data have been collected yet, ρ remains a scenario.
7. **Outage durations.** There are only 11 natural failures; ≥ 100 are needed, with censoring accounted for; check the tail shape on open data (FCC Measuring Broadband America).
8. **Assumptions without measurement.** The cost of a second on the reserve (c ≈ 0.01), the switching cost C = 20 s, A≈3 s after the flow reset, the HMM CPU estimate ×5–10, server failure rates, the distribution of blackout lengths, the reserve cR for the square-root law.
9. **Pareto front: the "simulator → reality" gap.** Check several front points on the bench (t = 0, 0.5, 1) with 59+ repeats and confirm the order of the points is preserved; seven days of advisor verification on the router before the "Auto" mode.
10. **MTU check and SQM.** Repeat the black-hole check after the EPERM fix (alpha8); measure cake on the router (latency, CPU); automatic rate by Little's law.
11. **Cryptography on the router.** The first real signature check when the first signed release is installed; TOFU — `wg show endpoints`, the `--config`/`--cd` path of OpenVPN; compare the probe threat model with OWAMP/TWAMP; an external transparency log with independent monitors; the owner's age steps (creating the identity, TOTP).
12. **Not implemented from the plan:** MDP for the return decision, Kalman/PID for the probe rate (a Kalman filter exists only as the soft RTT signal `rtt_watch`, off; CUSUM only as the dense trigger `cusum_trigger`, off, it never decides), covering arrays for the test matrix, immune memory by time of day, entropy probes and homeostasis, SQM by Little's law, server scoring by Mahalanobis distance, drift by Kullback–Leibler divergence, periodicity by FFT, a flash-wear formula, signed test reports.
13. **Peer review and replication.** There are no external reviewers; the source licence is not open source. Prepare a reproduction artefact (scripts, seeds, data) and a preprint (arXiv cs.NI). The idea "tune a threshold from history" overlaps Cisco patents (US 11 574 241, US 11 032 181): before publication describe the differences (on-device, a different model).
14. **A caveat on the prior-art search.** The search used open abstracts (≈45 queries); "not found" means "did not appear in the results". Novelty of individual methods is not claimed: no method is new, what is rare is their combination in one small product verified on real hardware.

## 11. Sources and reproduction

- The final report (generator): `private/final-report` (`REPORT.ru.html`, `data/*.json`; each number carries `kind`, `src`, `n` fields).
- Studies: `private/math/detection`, `availability`, `evolution`, `bayes-pick`, `wave3`, `master-slider`, `formal`; the prior-art search — `private/research`; the honest run — `private/soak-24h/report-a7-honest63`.
- Architecture documents (Russian): [HMM-DETECTOR](architecture/HMM-DETECTOR-2026-11-03.ru.md), [RESCUE-STABLE](architecture/RESCUE-STABLE-2026-11-03.ru.md), [FLAP-DAMPING](architecture/FLAP-DAMPING-2026-11-02.ru.md), [LATE-SWITCH-RECHECK](architecture/LATE-SWITCH-RECHECK-2026-11-03.ru.md), [SERVER-PICK-DESIGN](architecture/SERVER-PICK-DESIGN-2026-11-02.ru.md), [FLOW-RESET](architecture/FLOW-RESET-2026-11-03.ru.md), [MTU-SQM](architecture/MTU-SQM-2026-11-03.ru.md), [PROBE-AUTHENTICITY](architecture/PROBE-AUTHENTICITY-2026-11-03.ru.md); in branches: GL-SENSORS (`feat/gl-sensors-20261104`), SIGNING (`feat/usign-signing-20261103`), AGE-TOFU (`feat/age-tofu-20261104`), FORMAL-FIXES (`fix/formal-k2-k5-20261103`); NETWORK-ADVISOR — in the working copy of `feat/network-advisor-20261104`, not in git.
- All studies are reproducible with scripts next to the reports (seeds are fixed). Every number in this document is taken from the sources listed; where a value is absent, "no data" is written.
