# HomenS.AI Auto VPN diagnostic codes

This is the product-level catalogue. Some codes are emitted by the native monitor; others describe planned/demo states. Do not assume that every catalogue code is implemented on the device. A code denotes an evidenced symptom or cause, not an unsupported inference.

| Code | Meaning | Required evidence |
|---|---|---|
| WAN-001 | External Internet unavailable through WAN | Independent WAN checks; one failed gateway is insufficient to blame the provider |
| DNS-001 | DNS fails while independent IP/HTTPS checks work | DNS probes and HTTPS with fixed IP/correct SNI |
| VPN-001 | VPN connection could not be established | Completed attempt plus timeout/client event; cause may remain unknown |
| VPN-002 | VPN authentication rejected | Explicit authentication rejection from VPN client |
| VPN-003 | Connected tunnel does not carry probe traffic | Up interface, verified probe path, repeated failed checks |
| VPN-004 | VPN endpoint name cannot resolve | Resolution failure for the actual endpoint name |
| TLS-001 | Certificate validation failed | Explicit TLS validation result; never disable validation automatically |
| ROUTE-001 | Actual route differs from selection | Verified route/counter evidence rather than generic timeout |
| CHECK-001 | Probe path unverified | Insufficient evidence; state unknown |
| SWITCH-001 | No ready reserve candidate | Verified candidate states and selection queue |
| SWITCH-002 | Internet not restored after switching | Apply confirmed, subsequent probes failed |
| SWITCH-003 | Route change could not be applied | Apply-adapter error, distinguished from SWITCH-002 |
| CONFIG-001 | Automation paused after manual edit | Confirmed operator change or explicit manual mode |
| SYSTEM-001 | Unsupported firmware or missing dependency | Version/ABI/tool checks |

Planned full event records contain stable event_id, recovery episode_id, timestamp, severity, code, channel_id/server_id, protocol, display names at event time, check evidence, action and result. Each attempt has an attempt_id while all attempts for one incident share its episode. The current bounded native history is a smaller implemented schema; see native_history.py.

Show current issue, last failure and history separately. Planned filters: code, channel, server, protocol and cause/result. Technical details must exclude passwords, keys, tokens, cookies and complete private configuration.

Wording must distinguish “symptom confirmed”, “cause confirmed” and “cause unknown”. VPN-003 does not automatically blame a server: routing or filtering may be responsible. Recovery never erases the original failure. Diagnostic descriptions and work-log entries are maintained in English.


## Implemented monitor lifecycle codes — 0.7.0-alpha2

| Code | Meaning | Operator action |
|---|---|---|
| MONITOR-START-REQUESTED | Own enabled flag saved and own init start returned successfully | Wait for advancing measurements/procd; not yet running proof |
| MONITOR-STOP-REQUESTED | Safe own-service stop requested | Verify process state; does not claim Internet recovery |
| MONITOR-STOP-AUTO-FIRST | Native on intent, transaction, retained reserve or guard prevents shutdown | Stop Auto and verify safe recovery; do not kill the supervisor |
| MONITOR-JOURNAL-UNVERIFIED | Native recovery journal is corrupt or unreadable | Preserve the service/data and diagnose; never delete the journal to force success |
| MONITOR-SAVE-FAILED | Own UCI writer did not confirm commit | Inspect the redacted error; no service command was issued |
| MONITOR-SERVICE-UNCONFIRMED | Configuration may be saved but own init action failed/timed out | Check actual process/status; do not show green |
| MONITOR-INVALID | Invalid typed request or extra fields | Correct request; nothing was written |
| MONITOR-RPC-UNCONFIRMED | Browser did not receive a confirmed response | Refresh status; do not infer the service stopped |
