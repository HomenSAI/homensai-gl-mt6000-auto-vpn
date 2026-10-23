# Saved failure and switching statistics

Alpha36 adds a persistent statistics section to Statistics / transition evidence. It shows lifetime observed counters, the last seven days and compact calendar-month summaries. Download weekly detail and monthly summaries (JSON) retrieves all retained pages, rather than only the last events rendered on screen. The authenticated read-only `statistics` RPC is also available:

```sh
ubus call homensai-vpn statistics '{"kind":"controller","after":0,"until":0}'
ubus call homensai-vpn statistics '{"kind":"failures","after":0,"until":0}'
```

For subsequent pages use `next_after` and the fixed `until` returned on the first page. Continue while `has_more` is true. Each page has at most 100 events and a byte bound. A download snapshot never imports newly created events beyond its first watermark. No configuration or network changes occur during export.

## Meaning of the counters

- Failed checks count individual observed VPN/DNS probe failures. An outage is one continuous observed failure episode on a canonical VPN profile. A new healthy result closes it; repeated failures and unknown samples do not create duplicate episodes. Idle profiles and unknown observations are not failures.
- Confirmed switches count a transaction's first COMMITTED observation once, even if the same transaction later alternates between COMMITTED and DEGRADED. Attempts, trials, rollbacks and confirmed healthy-primary returns have separate counters. A rollback of an unsuccessful attempt is not a successful return.
- Auto observed time includes only adjacent fresh active-controller observations. Missing intervals, clock reversals and downtime are never reconstructed as working time. VPN up/down time also uses only observed bounded intervals. Unknown spans have no exact outage duration.
- New failure/check/runtime counters begin with alpha36's first observations. Missing earlier probe history is not invented. New confirmed-return counters have an explicit `returns_since` timestamp.
- Old transition counters are rebuilt only when the complete original event sequence is retained. This corrects duplicate COMMITTED counts. If original history is incomplete, old totals remain explicitly labelled legacy partial; the system does not present a guessed correction as exact.

## Storage and recovery

Failure/recovery edges and controller transition details expire after seven rolling days. Their monthly and lifetime aggregates remain. Compact month maps support up to 1200 calendar months (100 years); lifetime counters survive any retired month. Controller day summaries are limited to the rolling week.

The files use the existing checksummed primary/previous-good checkpoint mechanisms. Failure/recovery edges request immediate monitor checkpointing; unchanged normal measurements use the configured checkpoint interval. An abrupt loss can lose uncheckpointed routine measurements; backup recovery and storage errors are reported. No claim of perfect physical power-loss durability is made.

To bound router storage under an event storm, failure detail has a 1 MiB / 10000-event ceiling and controller detail a 2 MiB / 10000-event ceiling. Aggregate counters are preserved. Explicit dropped-detail/truncated flags make overflow visible; an incomplete weekly total is not displayed as complete. Under ordinary operation the complete recorded week is retained; old unavailable history cannot be recreated.

Only profile identifiers, timestamps, diagnostic codes and observations are retained. No credentials, transaction nonces, raw configuration, session cookies or exit IP addresses are stored in these statistics. Router-originated proof is never promoted to an external-LAN certificate.
