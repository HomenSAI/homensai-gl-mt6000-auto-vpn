# Executor, evidence and recovery review — alpha7

This is a manual threat/contract review by the implementing agent, separate from
the assertion that tests passed. It is not a third-party audit or device approval.

| Finding | Correction | Evidence / remaining limit |
|---|---|---|
| Existing journal directory could be public | Refuse POSIX directories not owned by this process or granting group/other access | Existing 0755 directory refusal test; Windows ACL/device acceptance separate |
| Rich phase details could exceed the history reader's 512 KiB limit | 400 KiB detailed-history budget, trim oldest events, retain aggregate counters; bound History limit to 1..500 | Byte-budget test preserves aggregate attempts and exposes truncation |
| Recovery checked too few dimensions | Validate policy hash, metadata/profile/recovery revision, boot identity and phase-specific order | Changed metadata and predicted external PREPARED order are blocked |
| Lost RPC response could hide a completed backend write | Journal APPLYING before apply; before/after-write timeout tests recover HELD without writes | No automatic enable/recovery; real RPC/vendor behavior still separate |
| Explicit DNS server did not guarantee client source binding | Bound UDP query and both HTTPS probes to the same selected IPv4; recheck interface/address and pending transaction | PowerShell no-network SelfTest; live LAN acceptance not claimed |
| Old client acknowledgement could be retried after later transitions | Freshness/deadline checks, unique transaction format, bounded consumed set and post-probe state re-read | Three sequential witness tests plus replay/changed-path refusals |
| Generic TRANSACTION-FAILED hid the cause | Persist only validated Refused codes, sanitized streak evidence and phase timestamps | Unknown arbitrary exceptions remain NATIVE-SYSTEM-001; no stderr/config dumps |
| Nonces/session fields must not enter public history | Public sequential attempt/retry identifiers; strict whitelist for probes/phases | Private-field sentinel and corrupt metadata tests; IDs are not security certificates |
| Restoration logging must not prevent restoration | Note RESTORING in memory; use the existing final journal write | Injected final journal failure still executes original restore operation |
| Profile labels could affect JS object prototypes | Null-prototype failure-streak map and prefixed grouping keys | __proto__ fixture test |
| Public/redacted inventory could erase secrets during migration | Full private own-UCI export shape required; preserve exact section names/anonymous flags | Round-trip private snapshot test; real UCI commit remains NEXT-24 |
| Polling reset the recovery period | Persist calendar selection independently of regenerated DOM | Source/Node checks and browser smoke; retained-data coverage remains explicit |
| CI bind of a full checkout could expose private .git/handoff data | Export exact committed tree, strict manifest, no .git mount, no network, UID 65534, no capabilities, read-only container root | Immutable CI launcher; restricted automated runner activation is separate |

Mandatory outstanding production boundaries: genuine vendor worker/hotplug/operator
arbitration, per-edge native certification, real client DNS/HTTPS/exit evidence,
source-bound Linux probes, IPv6/conntrack/offload and restart/power-failure behavior.
The new cascade executor deliberately accepts MemoryBackend only. No private PID
lock, green model result or source-code review grants production route ownership.

Measured load numbers are Linux/WSL host results for the hashes recorded in
`qa/alpha7-load-report.json`, not GL-MT6000 CPU/RAM/flash benchmarks. Later safety
checks do not retroactively turn those numbers into device measurements.


Additional lifecycle findings: Stop monitor falsely remained blocked by a historical on intent after a matched, controller-acknowledged Stop; corrected shared assessment with stale/wrong-trial/active-journal refusals. Old custom package hooks ignored stop failure and did not invalidate Auto scope on upgrade; new shared preinst/postinst/prerm guards reject active/unknown state, reset only own Auto options and propagate errors. The new guard initially used an assumed /tmp runtime path; corrected it to real agent.RUNTIME /var/run and added a behavioral path test. SDK/custom generated hook source parity is tested; full matching SDK compilation remains unverified. Real clone installation is the next acceptance step.
