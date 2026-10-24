<!-- doc-role: current -->
# Stored observations and statistics

[User settings](HISTORY-RETENTION.md) · [Current state](CURRENT-STATUS.md) · [Event roles](CHANNEL-ATTRIBUTION.md)

## Scope and limits

Live observations1–2000 limits the browser buffer; it is not a promise that server incident files also contain only that many rows. Detailed retention1–7days applies to persisted failure/recovery/controller events, probe/quality/activity detail and speed results during normal processing/checkpoints. Route/latency charts retain their separate1–24h view. Deleted detail cannot be restored by increasing retention.

Failure detail also has a1MiB/10000event ceiling and controller detail a2MiB/10000event ceiling. Public status gives a bounded tail, not all retained events. Dropped/truncated flags are explicit. Calendar-day/hour buckets are aggregates, not exact continuous uptime. Monthly/lifetime counters remain separately retained; month maps are bounded to1200months. Speed quota ledgers are not cleared to create new test budget.

## Read-only export

```sh
ubus call homensai-vpn statistics '{"kind":"controller","after":0,"until":0}'
ubus call homensai-vpn statistics '{"kind":"failures","after":0,"until":0}'
```

Keep the first response's `until` watermark and continue with `next_after` while `has_more`. Each page has at most100events and a byte bound. The snapshot excludes newer events beyond its watermark; search/export cannot create missing data. `detail_days` describes the retained window, not a guarantee of uninterrupted complete recording.

Saved Events initially shows20latest rows. Disclosure/search loads the retained snapshot, with pagination for large results and sorting across that snapshot. The separate read-week button is removed. Live rows are newest-first; consecutive equal states share an observed range/count, but A→B→A stays distinct.

## Counter meanings

An outage is one observed failure episode, not every failed probe. Fresh recovery closes it; unknown/disabled periods and observation gaps are different. Source/target roles are captured at each event, including recovery after a pair change; later settings never relabel history. New valid-pair data is explicit, old missing-role archive is not guessed into the chart.

A transaction's first confirmed COMMITTED is counted once. Requests, attempts, test passes, held outcomes, rollbacks and verified returns are different. A failed rollback request is not restored traffic. Auto observed time covers only adjacent verified intervals; missing/clock-reversed/power-off spans are not filled in as successful time.

Primary/previous-good checkpoints use checksums and validation. A corrupt recovery journal can block switching; neither deletion nor automatic reset is a valid green-status repair. Failure/recovery edges request early checkpointing; routine data can remain uncheckpointed until the selected interval. Sudden power loss can lose that routine tail and is not certified away by a unit test. Shorter-retention cleanup also applies to the preserved backup at normal save points.

Periods such as calendar month select only available retained detail. With1day of detail, a monthly speed average is not a full month; missing tests are not zeros. [Verification boundaries](VERIFICATION.md).
