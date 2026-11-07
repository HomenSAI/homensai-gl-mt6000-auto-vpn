# CSP work note (plan item 55, finding F-77)

Branch fix/a9-csp-20261107 (base integ/a9-night-20261107, 81416c28). Goal: the page's own code works under a
Content-Security-Policy without 'unsafe-eval' and without inline style attributes; behaviour and appearance unchanged.

F-77 (FIX-PROMPT-ALL-FINDINGS.md): `new Function` in the Help retry (`router/lazy_help.inc.js:53`, shipped
`dashboard210.js`), 33 `style=` in an older dashboard210.js. Fix: a CSP-compatible loader; static styles out of attributes.

## What is shipped

`router/build_ipk.py` packages only the selected page module and the lazy modules it names:
`view/homensai-vpn/dashboard210.js`, `ui176.css`, `homensai-vpn/help210.js`, `homensai-vpn/pick210.js`.
The older `dashboard<N>.js`/`help<N>.js`/`pick<N>.js` files in the tree and `qa/legacy-page/dashboard.js` are not packaged
(history / test reference only).

## Inventory before (81416c28)

| pattern | dashboard210.js | help210.js | pick210.js |
|---|---|---|---|
| `new Function` | 1 (lazy Help retry) | 0 | 0 |
| `eval(` / string timers | 0 / 0 | 0 / 0 | 0 / 0 |
| `style="` in HTML strings | 0 (already removed on integ) | 0 | 0 |
| `'style'`/`style:` attribute in E()/SVG helpers (setAttribute) | 1 (AI repair prompt textarea) | 8 (diagnostic prompt textarea, 3 legend dots, 3 SVG diagrams, lesson progress bar) | 0 |
| `setAttribute('style',...)` | 0 | 2 (retention slider fill, room bar) | 0 |
| CSSOM `el.style.x=` (CSP-safe, kept) | 3 | 6 | 0 |
| `<style>` element | 1 (downloaded incident report: a standalone file with its own CSP meta) | 0 | 0 |

LuCI note: LuCI's own `L.require` compiles every view and module with `eval` (luci.js compileClass). A CSP on the whole
LuCI page therefore still needs 'unsafe-eval' for LuCI itself; this work removes the page's own eval and inline style
attributes so the page adds nothing beyond what LuCI needs.

## Done
- step 1: inventory (this file).
- step 2: lazy Help retry without `new Function` (`router/lazy_help.inc.js` lazyHelpRetryName/lazyHelpRequire). LuCI caches
  a rejected `L.require` per name, so Retry asks LuCI for the same pinned file under a fresh module name: first
  `homensai-vpn/help210` ('/' for '.'), later retries percent-encode letters of the file name (`homensai-vpn/%68elp210`, ...;
  128 distinct names), which the web server decodes to the same path (uhttpd url-decodes the request path). No text is
  evaluated by the page; the old `request.get(...?retry=N)` + `new Function` path is gone. Not verified on a router (no
  router in this task): the first retry name needs no decoding at all. Tests updated: test_lazy_help_ui.js,
  test_help_failure_ui.js, test_expert_ui.js (their L.require mocks keep the first name rejected like LuCI).

- step 3: no style attribute is ever set by the page. `hvCss(el,css)` (router/element_guard.inc.js) applies a declaration
  list through `style.setProperty` (custom properties and `!important` kept). The module-local `E` takes a `'style'`
  value out of the attributes it passes to LuCI and applies it with hvCss (same inline precedence as before, so the
  appearance is unchanged; the caller object is not modified). The help module SVG helpers `measureSvg`/`coreSvg`
  (measurements_help.inc.js, core_help.inc.js) and the retention slider fill / room bar (stats_page.inc.js) use hvCss
  instead of `setAttribute('style',...)`. hvCss reaches the help module through its context (lazy_help.inc.js,
  lazy_help_build.py binding). hvCss falls back to setAttribute only for test doubles without a CSSOM; every browser
  element has `style.setProperty`.
- step 4: router/tests/test_csp_ui.js scans the packaged files and checks the CSSOM paths.

## Inventory after

| pattern | dashboard210.js | help210.js | pick210.js |
|---|---|---|---|
| `new Function` / `eval(` / string timers | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| `style=` in HTML strings | 0 | 0 | 0 |
| `setAttribute('style',...)` | 1 (hvCss test-double fallback, allowlisted) | 0 | 0 |
| `'style'` values in E()/SVG helpers (now CSSOM) | 1 | 8 | 0 |
| `<style>` element | 1 (incident report file, allowlisted) | 0 | 0 |

Size: dashboard210.js 610 433 -> 610 912 B (bounds: 49 % of alpha51 = 615 658 B, 66 % of legacy).

## Next
- browser check under a real CSP header on a router (not in this task: no router); LuCI itself still needs 'unsafe-eval'.

## Tests
- baseline: 127 of 128 router/tests/*.js pass; known failure test_lazy_help_ui.js (size bound of the reference page).
- after: 128 of 129 pass (new test_csp_ui.js included); the same known failure test_lazy_help_ui.js, at the same
  reference-size assertion (its retry assertions before it pass). test_stats_mode_ui.js and test_stats_retention_ui.js
  load stats_page.inc.js alone and now also load hvCss from element_guard.inc.js. test_csp_ui.js fails on the base
  files (new Function at dashboard210.js:1251; setAttribute style at help210.js:1431,1463).
- python -m unittest router.tests.test_package: OK (8). scripts/sync-documentation.py --check: OK (manifest regenerated,
  generated docs unchanged). scripts/bump-version.py --check: OK, version 2.1.0-alpha9-1 unchanged.
