# Grey lamp "router not answering" (plan item 53) - working note

Branch fix/a9-grey-lamp-20261107 (from integ/a9-night-20261107). Owner rule: commit after every step, keep this note current.

## Done
- router/ui/core.js: routerSilence() (page-local, FAIL_WINDOW = 60 s, no extra timer: paintLive already ticks every 1 s).
  overall() and autoIndicator() return key 'silent', lamp 'n' (grey) with "последний ответ HH:MM:SS" / "last answer HH:MM:SS"
  (fmtTime, Europe/Berlin like the rest of the page). autoDetail() shows only that line.
- router/ui/views.js: refreshNow() stamps HV.answerAt on a good reply (not on rpc_error/error or a rejected call);
  boot() stamps HV.shownAt/HV.answerAt; the visibilitychange handler restarts the window (time in a hidden tab does not count).
- Grey lamps stay still (owner scheme: grey = no data = no blink); coloured lamps keep their blink and the prefers-reduced-motion rule (CSS unchanged).
- router/tests/test_grey_lamp_ui.js: answer present, 59 s unchanged, >=60 s grey RU+EN with time, answer returns, refreshNow stamping, hidden tab, never answered.
- Generated dashboard210.js rebuilt (build_sidebar_ui.py): 610 433 B, bound 49 % of alpha51 = 615 659 B.

## Next
- Nothing open for this item. No catalogue/help text changed (sync-documentation.py not needed).

## Tests
- node router/tests/test_grey_lamp_ui.js PASS; whole router/tests/test_*.js sweep: see commit message / hand-back.
- Known pre-existing failure: test_lazy_help_ui.js.
