# Current state - alpha10

Alpha10-1/dashboard40/ui21 fixes clipped sidebar navigation and direct Settings reload after stylesheet sizing. Available-height desktop panel, scrollable nav and whole-panel tiny fallback; wrapped mobile links; active entry remains visible after navigation/resize. No physical router, network, VPN or firewall changes.

Validated source 192220cf1828e6d66207d877610a1d81d0ce9914: 329 application + 30 QA tests per runtime, 13 UI suites. Browser 144 transitions across nine pages/eight sizes/EN-RU plus keyboard scroll and direct Settings reload PASS. Native zoom itself was not changed; the matrix includes a zoom-equivalent CSS viewport.

Artifact releases/homensai-auto-vpn_0.7.0-alpha10-1_all.ipk: 465422 bytes, SHA256 87c0cf97517b77d03caa549cc07f42824ae11c61a9b4f64140db0fe2f2171b16. Both immutable CI runtimes and local builder match. See docs/SIDEBAR-RESPONSIVE-ALPHA10.md, qa/ALPHA10-LOCAL-CI.json and qa/ui-review-alpha10. Prior alpha9 colours and native/hardware acceptance limits remain.

Local/Gitea first, reviewed public snapshots on existing GitHub ancestry. No old tag overwrite or router installation. Exact release publication verification is stored separately.
