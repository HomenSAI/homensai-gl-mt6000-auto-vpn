# Telegram brief: explicit selection / Краткий отчёт по явному выбору

`setup_telegram(items="brief")` selects the Russian brief for interval, daily,
weekly and monthly reports. The settings selector and setup wizard expose it;
unset, empty and existing item selections keep their previous behaviour.
No router settings are changed by this source change.

The report groups retained FAILURE edges from `accounting.reliability.events`
and codes of BLOCKED/FAILED controller events by code (`×N`). Successful
controller codes and RECOVERY edges are omitted. The current alarm appears once
in the mandatory `Авария` line, including `Авария: нет` when absent. Error detail
is bounded separately so the alarm, switch count and reliability survive long
reports. Event periods use `[start, end)`.

Switches count retained, completed route changes (including restored returns),
deduplicated by attempt/outcome/destination. Trials, policy reapplications,
refusals and unchanged routes do not count. The label says `сохранённые события`:
public controller/reliability history is bounded, so this is not an unqualified
whole-week/month total. A failed controller-history read yields `нет данных`.

Handoff correction: `reliability.py` / `lua/reliability.lua` retain incident edges
and aggregate counters; they do not export per-channel percentages shown by the
page. The actual page function is `channel_guidance.inc.js:channelReliability`,
using `status.samples`. Brief uses the same population: time age -5..300 seconds
inclusive; minimum 6 checks; skip CHECK-001, CHECK-LIMIT, PROFILE-INACTIVE; pass
requires no code, DNS true, HTTPS success >=2. Reliability is 100 minus the page's
rounded failed-check percentage. It is labelled current five-minute reliability,
not uptime for the report period or LAN availability. Fewer than six checks means
`нет данных`. Current profile roles take priority over stale controller pair ids.

Regression evidence: `tests/fixtures/telegram_brief.json` exercises window edges,
minimum count, ignored checks, other profiles and mixed failures. Python compares
the actual JS function on these fixtures; Lua/Python report differential tests
reuse the fixtures and cover all calendar kinds. UI tests cover reopening brief,
explicit selection, review and actual save RPC; Lua save tests prove brief is
persisted and mixed/unknown selections are refused.

Полный CI, доставка в Telegram и приёмка на роутере остаются отдельными проверками.
