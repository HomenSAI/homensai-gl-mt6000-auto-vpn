# Security retest — 2026-10-16T21:30:48.6830986+02:00

Scope: local application source, isolated RPC calls, synthetic HTTP server and package privacy. No WAN scan, brute-force, flooding, real fault injection or router settings changes. Physical router admin TCP ports were unavailable during the preceding URL verification. This report does not certify Internet-facing firmware security.

| Area | Finding / correction | Evidence / limitation |
| --- | --- | --- |
| RPC JSON | Duplicate object keys were silently accepted; deep objects could raise uncaught RecursionError. Strict decoder now refuses duplicate keys, nonfinite/overflow numbers, nesting beyond 64, more than 10,000 values and input over 64 KiB. | New hostile-input suite; state writes/process execution mocked and must remain untouched. These are authenticated input-hardening findings, not evidence of anonymous remote code execution. |
| Session fields | rpcd session field is stripped before handlers. | Session sentinel test; never echoed or persisted. This does not replace rpcd authentication. |
| Authorization surface | ACL grants only named own ubus methods; no wildcard UCI/file/shell grants. Mutating methods reside in write ACL. | Static ACL assertion; actual unauthenticated HTTP/RPC access is NOT tested on unavailable hardware. |
| Shell/nft injection | Setup names remain data; fault interface/nonce/scope whitelist and private nft staging exist. | Existing focused regression suites, plus 256 deterministic hostile RPC cases; no real firewall commands executed. |
| Local preview | Arbitrary Host and cross-origin requests were not explicitly rejected. Added Host allowlist tied to listener port, same-origin Origin check, CORP same-origin and nosniff. | Actual loopback HTTP requests test rebinding-style Host, foreign Origin, traversal/private paths. Not the GL.iNet web server. |
| Secret distribution | Existing manifest and nested-package secret audit retained. | Full exact-source CI pending for this snapshot. No real credentials in new fixtures. |
| WAN exposure | Not currently verified. Historical UI had remote access enabled; do not treat that older screenshot as current configuration. | Must inspect current input firewall, uhttpd/rpcd binding and allowed source addresses on the physical router. A LAN TCP timeout says nothing about WAN exposure. |
| DoS / firmware exploits | No high-load or destructive tests executed. | Loopback bounds and mocked application inputs do not prove resistance to resource exhaustion, kernel/GL.iNet flaws or Internet DDoS. |

Package revision 9 is local only. Physical router still has the previously installed package; these protections are not yet deployed there.
## Verified results — 2026-10-16T21:32:09.8604643+02:00
Exact source a3da1397f0f3f9f92fe21f45e40bbe7552abf52d: 306 application tests, 24 QA tests in each runtime; Python 3.9/Lua zero skips, Python 3.11 control seven Lua skips; 11 JavaScript UI suites. Security suite includes 256 deterministic hostile RPC subcases. Reproducible package SHA256 be1c654dc2fcb342d2b78551efb9eb3b454e948ab049b4627025f21a84c6b166, 453560 bytes; source/nested-package privacy checks PASS. Local preview restarted to apply Host/Origin protections. Hardware/WAN security remains unverified.
