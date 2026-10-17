# Current local state - alpha9

Alpha9-1, dashboard39/ui20: the overview now uses green only for a selected, freshly healthy plan route. Healthy unselected standby is neutral/ready; transition destination yellow; real failure red; stale/off/inactive neutral with explicit labels. No route, VPN, firewall or physical-router change.

Validated source 18be40f4d0504ffc25c815675f077859087fde47: 329 application tests + 30 QA tests per runtime, 12 UI suites, including 200 path-state combinations. Python 3.9/Lua zero skips; Python 3.11 control seven Lua skips. Four synthetic browser cases and EN/RU verified.

Artifact releases/homensai-auto-vpn_0.7.0-alpha9-1_all.ipk; SHA256 af820a3ea1937bbee11a2f20b7d60dcf5e24615f226d2e0e27dacd31ead78521. Matching immutable dual-runtime builds and host build verified. See docs/OVERVIEW-PATH-COLOURS.md, releases/v0.7.0-alpha9.md and qa/ALPHA9-LOCAL-CI.json.

Primary local Git/Gitea first; public snapshots retain GitHub ancestry and never merge unreviewed canonical history or overwrite old tags. Prior alpha8 release/download verification remains in qa/GITHUB-ALPHA8-PUBLICATION.json. Physical native multi-hop/vendor/LAN acceptance remains pending. No deployment instruction in this UI correction.
