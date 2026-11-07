# Telegram notice when an outside-change HOLD ends by the owner (07.11.2026)

Branch `fix/a9-tg-release-20261107`, based on `integ/a9-night-20261107`. Version stays 2.1.0-alpha9-1.

## Owner decision

When a HOLD (`PAIR-OUTSIDE-CHANGE-HELD`) is ended by the owner, Telegram tells it, bilingual, EN then RU, like the other
outside-change notices:

- owner Stop: "hold ended: owner Stop";
- owner Start: "hold ended: owner Start, new configuration accepted".

## What changed

- New ring class `RELEASE` (ring `RUNTIME/telegram-outside-change.json`) next to `HOLD` and `ADOPT`. A RELEASE item has
  `decision='RELEASE'` and `release='STOP'|'START'`; an item without one of these two kinds is dropped by both twins.
  Its key is `RELEASE-<kind>:<trigger>:<time>` (a Stop and a Start of one instant are different decisions).
- Same privacy rules as before: validated codes and package NAMES only (trigger = the held code, class = `OWNER-STOP` /
  `OWNER-START`, packages = the hold's classification). No value, key, endpoint or token.
- Its own rate-limit bucket: at most one message per class every 600 s (`OUTSIDE_INTERVAL`), 6 h staleness by the
  monotonic clock (BH-05), exactly as HOLD and ADOPT. A RELEASE message never holds back a HOLD or ADOPT message.
- Message code `PAIR-OUTSIDE-CHANGE-RELEASED`; texts in `telegram_report.OUTSIDE_HEAD/OUTSIDE_TODO` (`RELEASE_STOP`,
  `RELEASE_START`) and the Lua twin `telegram.lua`.
- The record is made inside `release_session` (Python `pair_auto.py`, Lua `pair.lua`), the one place both release paths
  go through: the owner's Stop (`end_hold_on_stop`, T4-A) and the owner's Start (`release_for_start` / `request`, in Lua
  the control_request fallback to Python). The automatic adoption (`adopted_by='automatic'`) still records only its
  ADOPT in `readopt_running`; it records no RELEASE. The existing `operator_resolution` verdict (`STOP` / `ADOPT`) is
  unchanged.
- One local RAM write, never the network, never raises (same hook as HOLD/ADOPT).

## Tests

- `test_telegram_outside.py`: RELEASE ring entries, invalid kinds dropped, texts, own rate-limit bucket, Python vs Lua
  entry and text parity (`test_same_release_item_and_text`), and the pair paths (`ReleaseNotice`: owner Stop records
  STOP once, owner Start records START, automatic adoption records none, a failing write never stops the release).
- `test_telegram_outside_ties.py`: mixed ring (HOLD, ADOPT, RELEASE with equal times) gives the same messages in both
  twins.
- `lua/test_telegram_outside.lua`: the same cases on the Lua side, including `pair.release_session`.
- `lua/test_formal_fixes.lua` (T4-A): the owner Stop records a RELEASE, a refused `end_hold_on_stop` records none.
