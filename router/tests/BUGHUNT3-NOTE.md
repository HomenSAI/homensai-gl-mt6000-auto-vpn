# Bug hunt third pass BH3-01..BH3-03 (07.11.2026) - working note

Branch fix/a9-bughunt3-20261107 (base integ/a9-night-20261107 @ 76b9c474). Source: private/bughunt-20261107/FINDINGS-3.md.
fix/a9-ci (lifecycle/integrity/status_server tests) and fix/a9-monitor-boot (init.d, monitor enable) belong to other
agents and are not touched here. Version stays 2.1.0-alpha9-1 (bump-version.py --fingerprint-only only). No push, no router.

## Status
- [done, commit 1] BH3-01: the module E wrapper (router/element_guard.inc.js, built into dashboard210.js and handed to the
  lazy help/pick modules as ctx.E) wraps a single scalar child (string/number/boolean), and a non-object 2nd argument
  (E(tag,'text')), as [String(x)], so LuCI's dom.append never takes its `innerHTML = '' + child` branch. Nodes, functions
  (LuCI calls them with the element), arrays and null keep their behaviour. server_pick_panel.inc.js (pick210.js, not
  shipped now) also passes the GL profile/server names as array children, safe even under a raw LuCI E.
  Test doubles: router/tests/luci_dom_model.js follows luci.js 21.02 E/dom.create/dom.append (scalar -> innerHTML, recorded
  in a sink list); approved_page.js (20 page tests), test_a11y_ui.js and test_design_views_ui.js use it, the last two
  assert no innerHTML at the end. Test: tests/test_luci_scalar_child_ui.js (model fidelity, wrapper rules, pre-fix wrapper is
  caught, shipped preparationNotice/collection notify with a payload code, approved page RU/EN every tab/settings/wizard
  with hostile names, pick module under raw LuCI E and through the wrapper). Fails on the base.
- [done, commit 2] BH3-02: rpcd dispatcher (files/usr/libexec/rpcd/homensai-vpn). A button (pair_manual, native_start,
  native_stop, fault_start, fault_cancel, speed_start, speed_cancel, telegram_retry) whose Lua outcome is unclear (ubus
  timeout rc 7, rc 0 + SYSTEM-001 after a failed reply write, any other rc) is no longer replayed through agent.py: the
  dispatcher removes the request/reply files (a late ubus delivery reads nothing -> RPC-BRIDGE-PATH, no action) and
  answers {accepted:false,queued:false,code/blockers:RPC-BRIDGE-UNCONFIRMED}. agent.py still answers when Lua did not
  read the request: fallback, object missing (rc 4), RPC-BRIDGE-PATH, RPC-UNKNOWN-METHOD, RPC-BRIDGE-STALE. Reads keep
  the agent.py fallback on any failure; setup_* keep SETUP-SAVE-UNCONFIRMED. The message carries "sent" (the
  /proc/uptime second); lua/rpc.lua bridge_call drops a message handled more than rpc.BRIDGE_STALE=12 s later
  (RPC-BRIDGE-STALE, request never read; no stamp/clock -> as before; policy sent=INT32). Page: ui/core.js rpcCall
  rejects on RPC-BRIDGE-UNCONFIRMED, so every button runs its lost-answer path (F-35 manualLost/autoLost: re-read,
  "done" or Retry with the same client id; fault/speed their UNCONFIRMED modals). Catalogue rows RPC-BRIDGE-UNCONFIRMED
  and RPC-BRIDGE-STALE (error_rows_extra.inc.js; docs/ERROR_CODES.md regenerated). The agent.py rpc list is unchanged.
  Tests: test_lua_monitor_item2 Dispatcher (buttons x fallback/missing/path/stale -> agent; buttons x timeout/system001/
  other rc -> RPC-BRIDGE-UNCONFIRMED, no agent, files gone; reads x unclear -> agent; message carries an int "sent"),
  lua/test_monitor_rpc.lua (stale drop boundary, a stale button never acts, removed file never acts, no stamp/clock),
  tests/test_bridge_unconfirmed_ui.js (manual: lost dialog + Retry same id, late action -> "done"; Auto Stop -> Retry;
  Auto Start reached -> "received/done").
- [done, commit 3] BH3-03: pair_auto.py / lua/pair.lua. Every charge also notes its /proc/uptime second and boot_id in
  RAM (RUNTIME/pair-budget-clock.json {boot, at:[[wall,uptime],...]}, ledger_charge -> clock_note; advisory, gone after a
  reboot; the persistent pair-auto-budget.json keeps its format). charge_clock(events, note, now, uptime, boot) gives the
  stamps budget() sees: a stamp noted in this boot is at least uptime-now minus uptime-then old; a stamp more than
  CLOCK_SKEW=120 s in the future without a note (another boot, an old ledger) counts as old as the current uptime (at most
  one cooldown from now; an earlier boot's stamp is at least that old anyway); the wall age wins when larger, so nothing
  waits longer than before and forward steps are unchanged. effective_events() feeds every budget() caller: charge_attempt,
  reapply (+ its dispatch charge), tick dwell/retry, ledger_hold, pair_manual controls/consume (Lua: ledger_events,
  ledger_hold, manual.lua x3, page_controls via the monitor's new `effective` dep). The next charge writes the stamps back
  on the current wall clock (self-healing). abort_stamps drops an abort stamp more than CLOCK_SKEW in the future instead
  of clamping it (clamped, it restarted the retry backoff on every call until the clock caught up). Without /proc or a
  boot id (memory-fs Lua fakes, Windows) the raw stamps are used as before.
  Known residue: 'others' (non-failover charges) are matched by value, so a stamp rewritten after a step counts as a
  failover for flap damping (longer return hold only - the safe direction).
  Tests: tests/budget_clock_cases.json (14 charge_clock vectors; timelines: same boot clock 3 h / 1 h / 30 s behind ->
  allowed exactly at one cooldown; after a reboot 3 h / 1 h -> at most one cooldown of uptime; 30 s inside the skew ->
  cooldown + 30 s), tests/test_budget_clock.py (13: cases, timelines, the raw clamp still blocks, real charge_attempt with a
  patched wall clock and /proc clock: 3 h step, reboot, foreign note, forward step, unreadable note/no /proc, abort drop) and
  tests/lua/test_budget_clock.lua (10, the same cases + charge_attempt integration).

## Tests
- BH3-01: node 24 local, all router/tests/test_*.js pass. Page 607 723 B (bound 615 658 B).
- BH3-02: node 24 local, all router/tests/test_*.js pass; page 608 526 B. docker homensai-vpn-python39:night:
  test_lua_monitor_item2 (21), lua/test_monitor_rpc.lua (8), lua/test_probe_target_log.lua, test_rpc_security,
  test_package, test_probe_target_log, test_lua_readiness pass; test_status_server.Signature fails identically on the
  base (agent.py rpc list hash; agent.py not touched here, fix/a9-ci owns it). sync-documentation --check clean.
- BH3-03 + full run (docker homensai-vpn-python39:night, every router/tests/test_*.py module and lua/test_*.lua, branch vs
  base 76b9c474): no new failure. Both sides share the pre-existing failures (test_status_server.Signature,
  test_agent_website_integration and the others in the base log); test_lua_speed_telegram's speed_cancel timeout
  expectation was updated for BH3-02 (now RPC-BRIDGE-UNCONFIRMED; speed_live keeps the agent fallback). New:
  test_budget_clock (13), lua/test_budget_clock.lua (10). Node: all router/tests/test_*.js pass.

## Commit procedure
`python scripts/bump-version.py --fingerprint-only`, stage VERSION.json, `git -c core.hooksPath=.githooks commit`.
