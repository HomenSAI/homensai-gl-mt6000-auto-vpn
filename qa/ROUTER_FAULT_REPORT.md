# Router fault and transaction recovery tests

Historical report dated 2026-10-14. Target: the separate lab/router_sim.js simulator, not the GL.iNet device adapter. Neither the running demonstration nor real router was connected to this laboratory.

## Results

- 200 combinations across ten categories, 20 per category: all passed, 1737 assertions.
- Seven additional regressions passed: RPC-result persistence after restart, old-request replay after a newer operation, conflicting IDs, live worker lock, corrupt journal, external edit after commit and stale configuration generation.
- 20 actual SIGKILL terminations of own Python child processes in Linux Docker checked completed JSON files, durable intent, write/fsync/replace/directory-fsync and rollback decisions. Results: process-crash.json.

After two simulated restarts, 195 cases produced a consistent verified VPN exit; five remained blocked because both journal copies were corrupt. Every case requires LAN management to remain available in the model. PASS includes expected safe blocking when data is unrecoverable; it does not require impossible Internet recovery.

## The 200-case categories

| Category | Model injection |
|---|---|
| Linux delays | Virtual stage delays and total-deadline overrun |
| Power loss | Stops between lock, intent, IPv4, IPv6, conntrack, verify, config, commit and release |
| Flash errors | ENOSPC, EROFS and EIO in model write stages; some persistent until storage recovery |
| Incomplete journal | Interruption before/after durable write, torn records, corruption of both copies |
| RPC | Failure, timeout before apply, timeout after apply with unknown outcome |
| IPv6 | Divergent family routes, IPv6 loss, attempted WAN route; coherent VPN or blocking required |
| Conntrack | Scoped shared-route cleanup, cleanup failure, vendor global flush |
| Workers | Live/dead lock owner; cooperative writer or independent configuration change |
| Combinations | Concurrent timeout, power, WAN and write errors |
| Repeated requests | Deduplication, unknown reply, recovery and repeated restart |

router-faults.json contains stage details, synthetic primary/backup/operator profiles and model events only.

## Transaction model

Read/verify configuration generation, acquire lock and persist durable intent with the prior profile. Close forwarding while route families change, preserving LAN management. Change IPv4/IPv6, clean only shared conntrack, verify actual path/health, write configuration and commit; reopen forwarding only after rechecking.

After interruption, reread durable state and actual routes. Restore an incomplete owned change; never overwrite a newer external edit. Retain blocking if state cannot be verified. Do not steal a live worker lock or close healthy forwarding merely because the lock is busy.

A timeout after apply does not prove no operation occurred. The model verifies observable state and persists the last 64 completed transaction IDs. Replay does not reapply; it reports the current profile separately from the original target. Reusing an ID with a different target is rejected. A native API should require expectedGeneration; the simulator validates it when supplied. IDs outside the retention window need explicit expiry policy rather than unlimited deduplication.

## Defects clarified or corrected

Restart clears RAM; successful results recover from the durable journal. Fixed blocking healthy traffic on a busy lock and mislabelling late commit/external edits as rollback. Successful recovery, rollback, preserved external edits and safe blocking are distinct outcomes.

In two cases, simulated vendor global conntrack flush also removed a banking/special session. This is expected global-flush behaviour, not proof such sessions can be preserved. Scoped cleanup preserves them only in the model adapter path.

## Evidence limits

Flash is a model of checked writes/backup, delays are virtual, RPC/conntrack operate on model state. Forwarding-gate control and external configuration-generation detection are assumptions. Real UCI, firewall reload and GL.iNet writers were not established by these tests.

The 20 SIGKILL cases really terminated own Docker children and used Linux files. They did not cut host power, flush hardware cache, reproduce flash wear/controllers, modify iptables/ip rule or invoke router RPC. kernel.json describes simulated routes, not live kernel state.

Device apply/rollback, IPv6 capture, actual power loss and vendor-worker compatibility required separate acceptance. Prepare a concrete adapter, private backup, independent LAN/management path and recovery plan before that test. No router settings changed in this historical stage.

## Reproduction

```sh
node lab/test_transaction_regressions.js
node lab/test_router_faults.js /tmp/router-faults.json
python3 lab/test_process_crash.py /tmp/process-crash.json
```

Run the final command only in Linux container: it kills only its own children and removes only its temporary directories. At the historical checkpoint these changes were in feature/dashboard-prototype without a new commit/push.
