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

## Daily route graph and interface state

The original two-second live graph is unchanged. A separate graph below it shows the last 24 hours from compact observed intervals retained in the monitor checkpoint. Adjacent intervals of the same state coalesce. It records primary/reserve/transition/off/unknown rather than raw per-second samples; missing periods are unknown. The first day fills from installation; no earlier hours are fabricated. The 4096-interval safety ceiling reports any dropped detail.

Status redraws preserve the viewport anchor, expanded sections and current error-table description. Each visited page remembers its position; full document reload uses bounded session-only UI state. No secret fields or form values are saved by viewport persistence. The traffic WAN/VPN selector has its own smaller font. Known selected healthy traffic is green, healthy standby yellow, confirmed disconnected/failed red and stale/unverified grey.

## Manual commands while continuous Auto is enabled

Manual controls are a separate bordered card. The authenticated `pair_manual` writing RPC accepts only `primary`, `reserve` or `resume` plus the current Stop revision. Its RAM queue is claimed once by the existing native supervisor. An ACK is not a switch confirmation. Process recovery marks pending work unconfirmed rather than replaying it.

Manual reserve uses the same rolling three-attempt budget, cooldown, profile/policy/vendor/Stop fences, bounded native transaction and router-bound DNS/HTTPS proof as continuous Auto. Manual primary return is correlated to the exact journal and restored live order. It never creates a LAN certificate. A successful operator choice keeps that healthy channel preferred until another channel is chosen or confirmed failure requires recovery; Auto remains enabled. The ordinary UI has only the primary/reserve channel cards and no separate Resume action. A confirmed channel failure can release the hold so normal guarded recovery can proceed; no automatic return onto an unverified primary is introduced. Emergency Stop always revokes the shared revision.

Lifetime/monthly totals distinguish automatic and manual commits; a repeated COMMITTED status or change from manual hold to automatic observation does not count another switch. History badges mark 1 → 2 for a confirmed reserve switch and 2 → 1 for a confirmed restored primary; attempts remain visually unconfirmed.

## Current operator presentation (alpha41)

Live/daily route plots have exactly three levels: primary, reserve and off. A contiguous transition retains the last confirmed selection until a new route is confirmed; missing observations leave a gap. Raw transition/unknown history is retained and not rewritten as invented off time. The manual cards show selected Internet-working primary/reserve separately from the inactive card's not-in-use label and Turn on action. Profile probe health never becomes working from an ACK alone. Sidebar primary/reserve lamps reflect the same confirmed selection and observed health. Auto power is bright green/red; exceptional Stop remains inside Technical actions. Monitoring is required and its stopped/error state is red with a restoration action.

Status RPC includes its response server_time. The UI anchors age calculations to that router time and elapsed monotonic browser time, rather than comparing router timestamps directly to an operator PC clock. Old observations still expire, and RPC failures remain visible. Process-read uncertainty while waiting for MT3000 post-apply quiet resets the required verified quiet streak within the original deadline; persistent uncertainty/busy queues still refuse.
