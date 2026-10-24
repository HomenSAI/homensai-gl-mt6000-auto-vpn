<!-- doc-role: current -->
# How to read verification

[Actual current state](CURRENT-STATUS.md) · [Detailed alpha13 report](VERIFICATION-ALPHA13-2026-10-24.md)

| Label | Meaning |
|---|---|
| PASS | The stated check ran successfully on the named source/environment |
| FAIL | A check ran and failed; retain its attempt even after a retry |
| PARTIAL | Only part of the named scope was exercised |
| SKIPPED / NOT RUN | The check did not run; this is not success |
| UNKNOWN / UNCONFIRMED | Available evidence does not establish the result |
| BLOCKED | A prerequisite prevented dependent work |

A valid report names source/version, artifact size/SHA256, environment, exact actions, preserved failures, final state and limitations. Distinguish package metadata, running code, served resources, browser rendering, router-originated probes and independent client traffic. A short sample is not a day-long soak; process tests are not physical power loss; prompt recipes are not autonomous ChatGPT/Claude execution.

For stored history, an observed outage episode is not the number of failed checks. A missing historical channel/result is not reconstructed from today's settings. [Storage](STATISTICS-RETENTION.md) · [Channel attribution](CHANNEL-ATTRIBUTION.md).
