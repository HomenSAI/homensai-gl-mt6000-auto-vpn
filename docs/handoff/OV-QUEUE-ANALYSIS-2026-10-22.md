# OpenVPN queue investigation — 22 October 2026

Scope: offline inspection of previously captured vendor program sources. No physical call, firmware modification or fault-guard relaxation in this block.

## Observed on portable router

Physical trial03 reached fresh TLS/TUN at9.159s. Samples6→7→8 have aggregate firewall+RTP+flock+vendor counts1→3→7. The unchanged observer stops after two consecutive increases above baseline; therefore QUEUE-GROWTH-ABORT at10.629s is explained by its actual predicate. It does not by itself prove deadlock. The last sample includes two RELOAD queue entries: FIREWALL and OTHER; no recursion, retry workers or flock waiters. Data probe NOT-PERFORMED. Cleanup PASS.

## Source-supported call chain

Captured `etc__openvpn__scripts__ovpnclient-up` lines225–226 sends the interface update and writes connected BEFORE completion of subsequent hooks. For TUN, lines248–249 calls `rtp2.sh interface_status_change <interface> up`.

Captured `usr__bin__rtp2.sh` lines1993–1996 dispatches that event to `deal_interface_status_change` when route policy is enabled. Lines1603–1623 enables GL_SERVICE_QUEUE, processes interface policy and explicitly calls create_reload_service for `/etc/init.d/firewall` AND `/etc/init.d/network`, then reload_modified_service.

The previous classifier recognizes FIREWALL and DNSMASQ, with all remaining safe contents coded OTHER. NETWORK is consequently a source-supported candidate for physical03 OTHER, NOT its verified identity. Parent/child process counts and queued entries contribute to the aggregate, so normal startup fan-out can satisfy the conservative growth guard. That possibility does not prove safety, settling or absence of firmware recursion.

The interface_status_change branch bypasses the generic rtp2.lock waiting code in lines1998 onward. Do not infer generic-lock deadlock from two RTP processes or remove a lock based on this observation. Definitions/behavior of create_reload_service and reload_modified_service need further inspection before any policy revision.

## Diagnostic change and verification

Separate private directory `private/ov-queue-network-diagnostic-20261022` adds exact NETWORK classification only; original reviewed85efa harness and physical receipts remain frozen. Exact textual comparison proves no other harness delta. Core/source pins/package pins unchanged.

30 isolated Python3.9/Lua tests PASS, network none/read-only source. Initial old-test count mismatch is retained; final test explicitly requires OTHER1 and NETWORK1, plus a new test verifies unchanged count and no unknown filename leakage. Independent reviewer queue_callgraph_review approved diagnostic freeze; no further harness delta, observer/cleanup/counters/order/timers unchanged. This does not constitute device execution or Auto/manual/LAN acceptance.

## Next

1. Complete independent delta review and freeze hashes.
2. Inspect pinned queue producer/consumer implementations and source call paths; distinguish bounded startup fan-out from recursion or failure to settle.
3. Any observer-policy change needs a separate rationale, adversity tests and review. Never change thresholds solely to obtain PASS, and avoid another identical physical trial merely to classify NETWORK.
4. Real MT3000 application manual/Auto route adapter, external LAN validation and current alpha19 D/archive remain unfinished.


## Queue implementation provenance and semantics — 08:34 UTC block

Saved gl_util.sh SHA f4b8e053cedfdbbc90d1d304d6c6141508adcb4f19499bfc360bb0b79d458fb4 and vpn_func.sh SHA8adff4150d1360ac9163dc1bff2c39c1321ff8545430aa1a496c52a6aa4c97c6 exactly match the18 source pins checked by physical03 before activation. route_policy_func.sh pin also matches; lines3–5 imports gl_util/vpn_func. This closes the prior saved-copy provenance question, without identifying historical OTHER.

gl_util.sh2517–2525 writes one basename-keyed queue file containing service path when GL_SERVICE_QUEUE=1; otherwise invokes reload directly. vpn_func.sh162–175 lists queue entries, reads executable service path, calls reload synchronously and then removes the entry without checking its status. vpn_func.sh190–199 invokes reload then restart consumption through call_service_action. An entry can therefore represent in-progress work, not only pending work. A nonzero executable reload still removes its entry; empty queue cannot certify successful firewall/route completion. A nonexecutable target leaves its entry. No conclusion of actual concurrent consumption or firmware deadlock follows.

Three isolated tests of the exact pinned do_reload_service function, with queue path rerouted to tmpfs and a mock service, PASS. First attempt retained2fail1pass because noexec tmpfs made the mocked service nonexecutable; repeat with exec only for the isolated temporary fixture passed3/3. No router call/source mutation. Evidence private/ov-queue-consumer-20261022/receipt.json and qa-final.log.

Design requirement for next stage: use identity-aware bounded settling/progress and actual route/data evidence; queue count/connected flag alone cannot establish success or deadlock. Preserve existing recursion/retry/memory/deadline and cleanup protections until a separately reviewed policy exists.
