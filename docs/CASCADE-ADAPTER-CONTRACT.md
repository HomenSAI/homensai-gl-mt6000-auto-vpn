<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Native adapter contract for the completed offline cascade model

The model performs no system writes. Its intents are not authorization for native execution. The currently shipped native controller remains the bounded, separately certified pair adapter.

## Required ownership boundary

A future executor must own a cooperative vendor lease for the entire prepare/apply/confirm/rollback interval, not just its Python lock. GL.iNet tunnel-switch/rtp2/hotplug and operator edits must participate in the same protocol or be provably quiescent under a reviewed integration. Existing PID marker checks are insufficient and must not be treated as mutual exclusion. Do not impersonate vendor process names to defeat stale-lock checks.

`worker_busy=False` in the model is an injected test fact. On hardware it must come from verified arbitration; unknown is blocked. Concurrency tests exercise the refusal/changed-generation semantics, not real vendor cooperation.

## Intent proof and phases

Each edge needs: exact source/target identities, immutable original root order, immediate pre-hop order, desired order, semantic policy generation/hash (including selectors, DNS and Kill Switch), metadata/recovery revision, fresh profile-bound HTTPS/DNS evidence, monotonic bounded deadline and unique transaction identity.

Before applying, recheck all proof under the vendor lease. PREPARED accepts only the pre-hop order; an externally produced predicted order is still external. APPLYING can observe before/after while the owned executor works. WAIT-CONFIRM requires the desired order. Never overwrite an unknown generation/order to force recovery.

A LAN-side witness must confirm DNS, HTTPS and expected exit for that exact transaction. Endpoint ICMP or a connected process is insufficient. Certificates for one pair cannot authorize another pair; full hierarchy requires per-edge certification and the appropriate policy/metadata revision. The model's Boolean client acknowledgement is explicitly simulated.

## Rollback and stopping

A failed hop restores its immediate pre-hop snapshot, preserving the independent original-root snapshot. Returning to the root requires stable bound health and a fresh check; a healthy current reserve may be retained when the root is not verified. If no path is verified, keep the guarded failure visible and do not invent a direct-WAN fallback.

Restart never resumes Auto from a journal automatically. Reconciliation requires exact known policy generation/order, fresh bound health and explicit client/operator confirmation, and ends stopped. A new unattended-enable policy requires its own acceptance.

An independent watchdog must survive executor failure and verify restoration or an explicit guarded hold. Linux event timing, offload, DNS, IPv6, conntrack and firmware worker behavior require later device tests. Do not remove the current firmware/board/IPv6/offload guards to connect this model prematurely.
