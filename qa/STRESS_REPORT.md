<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../docs/CURRENT-STATUS.md) · [documentation index](../docs/DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# HomenSAI Auto VPN model tests

Historical report dated 2026-10-14. Target: local JavaScript demo/model.js and demonstration UI. These tests neither connected to the router nor changed VPN settings.

## Results after fixes

| Suite | Scope | Result |
|---|---|---|
| Generated scenarios, seeds 1–600 | 600 sequences × 300 steps | 600 passed; stress-1.json |
| Independent scenarios, seeds 1001–1600 | 600 sequences × 600 steps | 600 passed; stress-2.json |
| Full 12-boolean matrix | 4096 combinations × 3 steps | 4096 passed |
| Targeted regressions | 12 defect scenarios | 12 passed |
| Endurance/capacity | 5 checks, including 50,000 uninterrupted steps and 400 profiles | 5 passed |
| Earlier JS-model tests | 33 scenarios | 33 passed |
| Python controller and HTTP server | 30 + 4 tests | All passed |

The generated groups contain 1200 distinct initial seeds and 540,000 total steps of five model seconds each. Replaying a seed is not another unique scenario. Adjacent JSON reports hold assertion counts and detailed numeric results.

## Variations

Each scenario starts with one to six channels, each with one to seven servers, then adds profiles/channels. There are 22 action kinds: tunnel failure, blackhole, DNS, unknown path, WAN, all-VPN failure, recovery, manual selection, automation/failback/WAN-fallback settings, failed apply, renaming, protocol changes, archiving, priorities and ranking acceptance.

Initial dates cover ordinary days, January/October/December boundaries and DST transitions. Tests check monthly counter monotonicity within a month and agreement with an independent interval calculation. Unknown time is excluded from availability and measurement completeness.

The matrix exhausts four primary-health flags, four reserve-health flags and WAN/automation/availability-priority/WAN-permission flags: exactly 4096 combinations, not every possible system sequence.

## Defects found and fixed in the model

1. Revoking WAN permission left an already selected bypass active. Permission is now withdrawn immediately without waiting for VPN recovery.
2. WAN failure retained primary-recovery confidence. Successful probes must now accumulate again.
3. Ranking trusted an old success after failure, during WAN loss or after freshness expiry. Candidates must be healthy now, with verified results no older than 60 model seconds.
4. Monthly traffic depended on short chart history and could decrease after eviction. A separate calendar-month accumulator retains up to 18 months in model RAM.
5. Recovery always showed 15 seconds despite failed attempts/retry delay. It now spans known-failure start to successful recovery.
6. Retries for one incident received different episode_id values. The recovery chain now retains one episode.
7. Healthy manual switching counted as downtime recovery. recovery=null prevents distortion of recovery-time averages.
8. Direct WAN could remain selected for five minutes after a VPN became ready. Leaving WAN now waits for candidate readiness and a short cooldown rather than VPN failback hold time.
9. Adding a profile could select VPN over usingWan. Profile creation no longer changes active exit.
10. Trimming bounded logs decreased switch counts. Separate eight-day aggregates preserve statistics; the log is limited to 1000 rows.

Retry backoff after repeated apply failures is 30, 60, 120, 240, then at most 300 seconds. A 30-model-minute permanent-failure case produced nine attempts instead of retrying every 30 seconds.

The first ten targeted checks failed before fixes. A 100-scenario pilot found a profile-creation/WAN-reserve conflict in 30 sequences. Initial diagnostic failures are retained separately; final results refer to reruns after correction.

## Reproduction

From repository root with Node.js 22 and Python 3:

```sh
node demo/test_model.js
node demo/test_regressions.js
node demo/test_matrix.js
node demo/test_soak.js
node demo/stress_model.js
ALTA_SEED_START=1001 ALTA_RUNS=600 ALTA_STEPS=600 node demo/stress_model.js
python -m unittest discover -s demo -q
python -m unittest discover -s prototype -q
```

stress_model.js accepts a JSON-report path as its first argument. ALTA_RUNS, ALTA_STEPS and ALTA_SEED_START control sequence count, length and seed range; errors retain seed and recent actions in JSON.

## Practical limits

This proves model logic. Real VPN servers, Linux delays, device power loss, flash, IPv6, conntrack, GL.iNet writers, RPC failures and actual device apply/rollback are outside this run. 400 profiles were tested in desktop Node.js, not proven as router capacity.

Model accumulators live in page RAM; refresh recreates synthetic data. The separate monthly accumulator survives chart trimming but not browser/device restart. Persistent router storage and independent native tests remained required. At the historical checkpoint, changes were in feature/dashboard-prototype and no new commit/Gitea push occurred during that stage.
